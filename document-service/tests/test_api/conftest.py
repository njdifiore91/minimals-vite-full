import os
import json
import pytest
import io
import uuid
import random
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Callable, Union, BytesIO
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import necessary modules from the document service
# Use relative imports since we're in the tests directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.api.router import router as api_router
from src.types.classification import (
    DocumentType,
    ClassificationModel,
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters
)
from src.types.storage import (
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult,
    StorageError
)
from src.types.config import (
    ConfigDict,
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config
)

# Constants for testing
TEST_BUCKET_NAME = "mca-documents-test"
TEST_DOCUMENT_TYPES = [
    "LOAN_APPLICATION",
    "TAX_RETURN",
    "BANK_STATEMENT",
    "PAY_STUB",
    "IDENTITY_DOCUMENT",
    "BUSINESS_LICENSE",
    "UTILITY_BILL",
    "INSURANCE_DOCUMENT",
    "OTHER"
]
TEST_FILE_FORMATS = ["pdf", "png", "jpg", "tiff", "txt"]

# ============================================================================
# S3 Storage Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """
    Creates a mock S3 client for testing document storage operations.
    
    Returns:
        MagicMock: A mock S3 client with methods for upload, download, list, and delete.
    """
    mock_client = MagicMock()
    
    # Mock storage for documents
    storage_dict = {}
    
    # Mock upload_fileobj method
    def mock_upload_fileobj(fileobj, bucket, key, **kwargs):
        storage_dict[f"{bucket}/{key}"] = {
            "content": fileobj.read(),
            "metadata": kwargs.get("Metadata", {}),
            "encryption": kwargs.get("ServerSideEncryption", None)
        }
        fileobj.seek(0)  # Reset file position
        return {}
    
    # Mock download_fileobj method
    def mock_download_fileobj(bucket, key, fileobj, **kwargs):
        if f"{bucket}/{key}" in storage_dict:
            content = storage_dict[f"{bucket}/{key}"]["content"]
            fileobj.write(content)
            fileobj.seek(0)  # Reset file position
            return {}
        else:
            # Simulate NoSuchKey error
            error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}
            raise Exception(error_response)
    
    # Mock list_objects_v2 method
    def mock_list_objects_v2(Bucket, Prefix=None, **kwargs):
        results = []
        for key in storage_dict:
            if key.startswith(f"{Bucket}/"):
                doc_key = key.split("/", 1)[1]
                if Prefix is None or doc_key.startswith(Prefix):
                    results.append({"Key": doc_key})
        return {"Contents": results}
    
    # Mock delete_object method
    def mock_delete_object(Bucket, Key, **kwargs):
        key = f"{Bucket}/{Key}"
        if key in storage_dict:
            del storage_dict[key]
        return {}
    
    # Mock head_object method
    def mock_head_object(Bucket, Key, **kwargs):
        key = f"{Bucket}/{Key}"
        if key in storage_dict:
            return {
                "Metadata": storage_dict[key]["metadata"],
                "ContentLength": len(storage_dict[key]["content"]),
                "LastModified": datetime.now(),
                "ServerSideEncryption": storage_dict[key]["encryption"]
            }
        else:
            # Simulate NoSuchKey error
            error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}
            raise Exception(error_response)
    
    # Assign mock methods to the mock client
    mock_client.upload_fileobj.side_effect = mock_upload_fileobj
    mock_client.download_fileobj.side_effect = mock_download_fileobj
    mock_client.list_objects_v2.side_effect = mock_list_objects_v2
    mock_client.delete_object.side_effect = mock_delete_object
    mock_client.head_object.side_effect = mock_head_object
    
    return mock_client

@pytest.fixture
def mock_s3_config():
    """
    Creates a mock S3 configuration for testing.
    
    Returns:
        Dict: A mock S3 configuration dictionary.
    """
    return {
        "endpoint_url": "https://test-s3-endpoint.example.com",
        "region_name": "us-test-1",
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "bucket_name": TEST_BUCKET_NAME,
        "encryption": "AES256",
        "storage_class": "STANDARD"
    }

@pytest.fixture
def mock_s3_storage(mock_s3_client, mock_s3_config):
    """
    Creates a mock S3 storage utility for testing document storage operations.
    
    Args:
        mock_s3_client: The mock S3 client fixture.
        mock_s3_config: The mock S3 configuration fixture.
    
    Returns:
        MagicMock: A mock S3 storage utility with methods for document operations.
    """
    mock_storage = MagicMock()
    mock_storage.client = mock_s3_client
    mock_storage.config = mock_s3_config
    
    # Mock upload_document method
    def mock_upload_document(document_data, document_key, metadata=None):
        if metadata is None:
            metadata = {}
        
        fileobj = BytesIO(document_data)
        mock_s3_client.upload_fileobj(
            fileobj,
            mock_s3_config["bucket_name"],
            document_key,
            Metadata=metadata,
            ServerSideEncryption=mock_s3_config["encryption"]
        )
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": metadata,
            "encryption_status": "encrypted"
        }
    
    # Mock download_document method
    def mock_download_document(document_key):
        fileobj = BytesIO()
        try:
            mock_s3_client.download_fileobj(
                mock_s3_config["bucket_name"],
                document_key,
                fileobj
            )
            return {
                "success": True,
                "error": None,
                "etag": f"\"{uuid.uuid4()}\"",
                "version_id": str(uuid.uuid4()),
                "storage_class": "STANDARD",
                "metadata": mock_s3_client.head_object(
                    Bucket=mock_s3_config["bucket_name"],
                    Key=document_key
                ).get("Metadata", {}),
                "encryption_status": "encrypted",
                "data": fileobj.getvalue(),
                "size": len(fileobj.getvalue())
            }
        except Exception as e:
            error_detail = {
                "service": "S3",
                "status_code": 404,
                "operation": "download_fileobj",
                "sender_fault": False,
                "retry_attempts": 3
            }
            
            error = {
                "code": "NoSuchKey",
                "message": str(e),
                "request_id": str(uuid.uuid4()),
                "resource": document_key,
                "details": error_detail,
                "timestamp": datetime.now(),
                "recoverable": False
            }
            
            return {
                "success": False,
                "error": error,
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": {},
                "encryption_status": None,
                "data": None,
                "size": 0
            }
    
    # Mock delete_document method
    def mock_delete_document(document_key):
        try:
            mock_s3_client.delete_object(
                Bucket=mock_s3_config["bucket_name"],
                Key=document_key
            )
            return {
                "success": True,
                "error": None,
                "etag": f"\"{uuid.uuid4()}\"",
                "version_id": str(uuid.uuid4()),
                "storage_class": "STANDARD",
                "metadata": {},
                "encryption_status": "encrypted"
            }
        except Exception as e:
            error_detail = {
                "service": "S3",
                "status_code": 500,
                "operation": "delete_object",
                "sender_fault": False,
                "retry_attempts": 3
            }
            
            error = {
                "code": "InternalError",
                "message": str(e),
                "request_id": str(uuid.uuid4()),
                "resource": document_key,
                "details": error_detail,
                "timestamp": datetime.now(),
                "recoverable": True
            }
            
            return {
                "success": False,
                "error": error,
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": {},
                "encryption_status": None
            }
    
    # Mock list_documents method
    def mock_list_documents(prefix=None):
        try:
            response = mock_s3_client.list_objects_v2(
                Bucket=mock_s3_config["bucket_name"],
                Prefix=prefix
            )
            documents = [item["Key"] for item in response.get("Contents", [])]
            return {
                "success": True,
                "error": None,
                "keys": documents,
                "storage_class": "STANDARD",
                "encryption_status": "encrypted"
            }
        except Exception as e:
            error_detail = {
                "service": "S3",
                "status_code": 500,
                "operation": "list_objects_v2",
                "sender_fault": False,
                "retry_attempts": 3
            }
            
            error = {
                "code": "InternalError",
                "message": str(e),
                "request_id": str(uuid.uuid4()),
                "resource": prefix or "",
                "details": error_detail,
                "timestamp": datetime.now(),
                "recoverable": True
            }
            
            return {
                "success": False,
                "error": error,
                "keys": [],
                "storage_class": None,
                "encryption_status": None
            }
    
    # Assign mock methods to the mock storage utility
    mock_storage.upload_document.side_effect = mock_upload_document
    mock_storage.download_document.side_effect = mock_download_document
    mock_storage.delete_document.side_effect = mock_delete_document
    mock_storage.list_documents.side_effect = mock_list_documents
    
    return mock_storage

# ============================================================================
# RabbitMQ Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_rabbitmq_config():
    """
    Creates a mock RabbitMQ configuration for testing.
    
    Returns:
        Dict: A mock RabbitMQ configuration dictionary.
    """
    return {
        "host": "test-rabbitmq-host.example.com",
        "port": 5671,  # TLS port
        "virtual_host": "mca",
        "username": "test-user",
        "password": "test-password",
        "exchange": "mca.documents",
        "exchange_type": "fanout",
        "queue": "document-processing",
        "routing_key": "",  # Empty for fanout exchange
        "ssl": True,
        "ssl_options": {
            "cert_reqs": 2,  # ssl.CERT_REQUIRED
            "ca_certs": "/path/to/ca_certificate.pem",
            "certfile": "/path/to/client_certificate.pem",
            "keyfile": "/path/to/client_key.pem"
        }
    }

@pytest.fixture
def mock_rabbitmq_connection():
    """
    Creates a mock RabbitMQ connection for testing.
    
    Returns:
        MagicMock: A mock RabbitMQ connection.
    """
    mock_connection = MagicMock()
    mock_connection.is_open = True
    return mock_connection

@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """
    Creates a mock RabbitMQ channel for testing.
    
    Args:
        mock_rabbitmq_connection: The mock RabbitMQ connection fixture.
    
    Returns:
        MagicMock: A mock RabbitMQ channel.
    """
    mock_channel = MagicMock()
    mock_channel.is_open = True
    mock_channel.connection = mock_rabbitmq_connection
    
    # Message storage for testing
    message_storage = []
    
    # Mock basic_publish method
    def mock_basic_publish(exchange, routing_key, body, properties=None):
        message_storage.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "body": body,
            "properties": properties
        })
        return None
    
    # Mock basic_consume method
    def mock_basic_consume(queue, on_message_callback, auto_ack=False):
        # Store the callback for later use in tests
        mock_channel._on_message_callback = on_message_callback
        mock_channel._auto_ack = auto_ack
        return None
    
    # Mock basic_ack method
    def mock_basic_ack(delivery_tag):
        return None
    
    # Helper method to simulate message delivery
    def deliver_message(body, delivery_tag=1):
        # Create a mock method frame
        method = MagicMock()
        method.delivery_tag = delivery_tag
        
        # Create mock properties
        properties = MagicMock()
        
        # Call the stored callback
        if hasattr(mock_channel, "_on_message_callback"):
            mock_channel._on_message_callback(mock_channel, method, properties, body)
            
            # Auto-acknowledge if enabled
            if getattr(mock_channel, "_auto_ack", False):
                mock_basic_ack(method.delivery_tag)
    
    # Assign mock methods to the mock channel
    mock_channel.basic_publish.side_effect = mock_basic_publish
    mock_channel.basic_consume.side_effect = mock_basic_consume
    mock_channel.basic_ack.side_effect = mock_basic_ack
    
    # Add helper methods and storage to the mock channel
    mock_channel.deliver_message = deliver_message
    mock_channel.message_storage = message_storage
    
    return mock_channel

@pytest.fixture
def mock_rabbitmq_client(mock_rabbitmq_connection, mock_rabbitmq_channel, mock_rabbitmq_config):
    """
    Creates a mock RabbitMQ client for testing message queue operations.
    
    Args:
        mock_rabbitmq_connection: The mock RabbitMQ connection fixture.
        mock_rabbitmq_channel: The mock RabbitMQ channel fixture.
        mock_rabbitmq_config: The mock RabbitMQ configuration fixture.
    
    Returns:
        MagicMock: A mock RabbitMQ client with methods for publishing and consuming messages.
    """
    mock_client = MagicMock()
    mock_client.connection = mock_rabbitmq_connection
    mock_client.channel = mock_rabbitmq_channel
    mock_client.config = mock_rabbitmq_config
    
    # Mock connect method
    def mock_connect():
        return mock_rabbitmq_connection, mock_rabbitmq_channel
    
    # Mock publish_message method
    def mock_publish_message(message, routing_key=None):
        if routing_key is None:
            routing_key = mock_rabbitmq_config["routing_key"]
        
        # Convert message to JSON if it's a dict
        if isinstance(message, dict):
            message_body = json.dumps(message).encode("utf-8")
        elif isinstance(message, str):
            message_body = message.encode("utf-8")
        else:
            message_body = message
        
        mock_rabbitmq_channel.basic_publish(
            exchange=mock_rabbitmq_config["exchange"],
            routing_key=routing_key,
            body=message_body
        )
        
        return True
    
    # Mock consume_messages method
    def mock_consume_messages(callback, queue=None):
        if queue is None:
            queue = mock_rabbitmq_config["queue"]
        
        def wrapper_callback(ch, method, properties, body):
            # Parse JSON message if it's JSON
            try:
                message = json.loads(body.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                message = body
            
            # Call the original callback
            callback(message, method.delivery_tag)
        
        mock_rabbitmq_channel.basic_consume(
            queue=queue,
            on_message_callback=wrapper_callback,
            auto_ack=False
        )
        
        return True
    
    # Mock acknowledge_message method
    def mock_acknowledge_message(delivery_tag):
        mock_rabbitmq_channel.basic_ack(delivery_tag=delivery_tag)
        return True
    
    # Assign mock methods to the mock client
    mock_client.connect.side_effect = mock_connect
    mock_client.publish_message.side_effect = mock_publish_message
    mock_client.consume_messages.side_effect = mock_consume_messages
    mock_client.acknowledge_message.side_effect = mock_acknowledge_message
    
    return mock_client

# ============================================================================
# Document Classification Model Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_model_config():
    """
    Creates a mock model configuration for testing.
    
    Returns:
        Dict: A mock model configuration dictionary.
    """
    return {
        "svm": {
            "C": 1.0,
            "kernel": "linear",
            "probability": True,
            "class_weight": "balanced",
            "random_state": 42
        },
        "random_forest": {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "class_weight": "balanced",
            "random_state": 42
        },
        "feature_extraction": {
            "max_features": 5000,
            "min_df": 2,
            "max_df": 0.95,
            "ngram_range": [1, 2]
        },
        "confidence_thresholds": {
            "high": 0.9,
            "medium": 0.7,
            "low": 0.5
        },
        "document_types": TEST_DOCUMENT_TYPES,
        "model_path": "/path/to/models",
        "model_version": "1.0.0"
    }

@pytest.fixture
def mock_classification_model(mock_model_config):
    """
    Creates a mock document classification model for testing.
    
    Args:
        mock_model_config: The mock model configuration fixture.
    
    Returns:
        MagicMock: A mock document classification model with configurable accuracy.
    """
    mock_model = MagicMock()
    mock_model.config = mock_model_config
    
    # Default accuracy is high (99%)
    mock_model.accuracy = 0.99
    
    # Mock predict method
    def mock_predict(features):
        # Randomly select a document type based on accuracy
        if random.random() < mock_model.accuracy:
            # Correct prediction (based on document type in features metadata)
            if hasattr(features, "metadata") and "document_type" in features.metadata:
                return features.metadata["document_type"]
            else:
                # Default to a random document type if no metadata
                return random.choice(mock_model_config["document_types"])
        else:
            # Incorrect prediction (random document type)
            return random.choice(mock_model_config["document_types"])
    
    # Mock predict_proba method
    def mock_predict_proba(features):
        # Get the predicted class
        predicted_class = mock_predict(features)
        
        # Create probabilities for all classes
        probabilities = {}
        remaining_prob = 1.0 - mock_model.accuracy
        
        # Distribute remaining probability among other classes
        other_classes = [c for c in mock_model_config["document_types"] if c != predicted_class]
        prob_per_class = remaining_prob / len(other_classes) if other_classes else 0
        
        # Assign probabilities
        for doc_type in mock_model_config["document_types"]:
            if doc_type == predicted_class:
                probabilities[doc_type] = mock_model.accuracy
            else:
                probabilities[doc_type] = prob_per_class
        
        return probabilities
    
    # Mock classify method
    def mock_classify(document_data, document_metadata=None):
        # Create a feature vector from the document data
        features = MagicMock()
        features.data = document_data
        features.metadata = document_metadata or {}
        
        # Get the predicted class and probabilities
        predicted_class = mock_predict(features)
        probabilities = mock_predict_proba(features)
        
        # Calculate confidence score
        confidence = probabilities[predicted_class]
        confidence_level = "high"
        if confidence < mock_model_config["confidence_thresholds"]["high"]:
            confidence_level = "medium"
        if confidence < mock_model_config["confidence_thresholds"]["medium"]:
            confidence_level = "low"
        
        # Create classification result
        result = ClassificationResult(
            document_type=DocumentType[predicted_class.upper()] if predicted_class.upper() in DocumentType.__members__ else DocumentType.OTHER,
            confidence=confidence,  # ConfidenceScore is just a float in the actual implementation
            probabilities={DocumentType[k.upper()] if k.upper() in DocumentType.__members__ else DocumentType.OTHER: v for k, v in probabilities.items()},
            needs_review=confidence < mock_model_config["confidence_thresholds"]["medium"],
            feature_importance={"feature1": 0.5, "feature2": 0.3, "feature3": 0.2},
            processing_time_ms=random.randint(10, 100)
        )
        
        return result
    
    # Assign mock methods to the mock model
    mock_model.predict.side_effect = mock_predict
    mock_model.predict_proba.side_effect = mock_predict_proba
    mock_model.classify.side_effect = mock_classify
    
    # Method to set accuracy for testing different scenarios
    def set_accuracy(accuracy):
        mock_model.accuracy = accuracy
    
    mock_model.set_accuracy = set_accuracy
    
    return mock_model

# ============================================================================
# Test Document Generation Utilities
# ============================================================================

@pytest.fixture
def generate_test_document():
    """
    Creates a function for generating test documents of various types and formats.
    
    Returns:
        Callable: A function that generates test documents.
    """
    def _generate_document(document_type=None, file_format=None, content=None, metadata=None):
        """
        Generates a test document with specified parameters.
        
        Args:
            document_type (str, optional): The type of document to generate.
                Defaults to a random type from TEST_DOCUMENT_TYPES.
            file_format (str, optional): The file format of the document.
                Defaults to a random format from TEST_FILE_FORMATS.
            content (bytes, optional): The content of the document.
                Defaults to random content based on document type.
            metadata (Dict, optional): Additional metadata for the document.
                Defaults to generated metadata based on document type.
        
        Returns:
            Tuple[bytes, Dict]: A tuple containing the document content and metadata.
        """
        # Set default document type and file format if not provided
        if document_type is None:
            document_type = random.choice(TEST_DOCUMENT_TYPES)
        
        if file_format is None:
            file_format = random.choice(TEST_FILE_FORMATS)
        
        # Generate default content if not provided
        if content is None:
            # Generate different content based on document type
            if document_type == "LOAN_APPLICATION":
                content = b"This is a test application form for MCA funding."
            elif document_type == "BANK_STATEMENT":
                content = b"BANK STATEMENT\nAccount: 123456789\nBalance: $10,000.00"
            elif document_type == "TAX_RETURN":
                content = b"TAX RETURN\nTax Year: 2023\nIncome: $500,000.00"
            elif document_type == "IDENTITY_DOCUMENT":
                content = b"DRIVER LICENSE\nName: John Doe\nDOB: 01/01/1980"
            elif document_type == "BUSINESS_LICENSE":
                content = b"BUSINESS LICENSE\nBusiness Name: ABC Corp\nExpiration: 12/31/2025"
            elif document_type == "PAY_STUB":
                content = b"PAY STUB\nEmployee: John Doe\nPay Period: 01/01/2023 - 01/15/2023\nGross Pay: $5,000.00"
            elif document_type == "UTILITY_BILL":
                content = b"UTILITY BILL\nAccount: 987654321\nAmount Due: $150.00\nDue Date: 01/31/2023"
            elif document_type == "INSURANCE_DOCUMENT":
                content = b"INSURANCE POLICY\nPolicy Number: INS-12345\nCoverage: $1,000,000\nExpiration: 12/31/2023"
            else:  # OTHER
                content = f"Test document content for {document_type}".encode("utf-8")
        
        # Generate default metadata if not provided
        if metadata is None:
            metadata = {
                "document_type": document_type,
                "file_format": file_format,
                "created_at": datetime.now().isoformat(),
                "document_id": str(uuid.uuid4()),
                "application_id": str(uuid.uuid4()),
                "size": len(content)
            }
        
        return content, metadata
    
    return _generate_document

@pytest.fixture
def generate_test_documents(generate_test_document):
    """
    Creates a function for generating multiple test documents.
    
    Args:
        generate_test_document: The generate_test_document fixture.
    
    Returns:
        Callable: A function that generates multiple test documents.
    """
    def _generate_documents(count=5, document_types=None, file_formats=None):
        """
        Generates multiple test documents with specified parameters.
        
        Args:
            count (int, optional): The number of documents to generate.
                Defaults to 5.
            document_types (List[str], optional): The types of documents to generate.
                Defaults to all types in TEST_DOCUMENT_TYPES.
            file_formats (List[str], optional): The file formats of the documents.
                Defaults to all formats in TEST_FILE_FORMATS.
        
        Returns:
            List[Tuple[bytes, Dict]]: A list of tuples containing document content and metadata.
        """
        # Set default document types and file formats if not provided
        if document_types is None:
            document_types = TEST_DOCUMENT_TYPES
        
        if file_formats is None:
            file_formats = TEST_FILE_FORMATS
        
        # Generate documents
        documents = []
        for _ in range(count):
            document_type = random.choice(document_types)
            file_format = random.choice(file_formats)
            content, metadata = generate_test_document(document_type, file_format)
            documents.append((content, metadata))
        
        return documents
    
    return _generate_documents

# ============================================================================
# API Testing Utilities
# ============================================================================

@pytest.fixture
def test_app():
    """
    Creates a FastAPI test application for API testing.
    
    Returns:
        FastAPI: A FastAPI test application.
    """
    app = FastAPI(title="Document Service API Test")
    app.include_router(api_router)
    return app

@pytest.fixture
def test_client(test_app):
    """
    Creates a TestClient for making requests to the test application.
    
    Args:
        test_app: The FastAPI test application fixture.
    
    Returns:
        TestClient: A TestClient for making requests to the test application.
    """
    return TestClient(test_app)

@pytest.fixture
def validate_response():
    """
    Creates a function for validating API responses against expected schemas.
    
    Returns:
        Callable: A function that validates API responses.
    """
    def _validate_response(response, expected_status_code=200, expected_schema=None):
        """
        Validates an API response against expected status code and schema.
        
        Args:
            response: The API response to validate.
            expected_status_code (int, optional): The expected HTTP status code.
                Defaults to 200.
            expected_schema (Dict, optional): The expected response schema.
                Defaults to None.
        
        Returns:
            bool: True if the response is valid, False otherwise.
        """
        # Validate status code
        assert response.status_code == expected_status_code, \
            f"Expected status code {expected_status_code}, got {response.status_code}"
        
        # Validate response content type
        assert response.headers.get("content-type") == "application/json", \
            "Expected content type 'application/json'"
        
        # Validate response schema if provided
        if expected_schema is not None:
            response_json = response.json()
            
            # Validate schema keys
            for key in expected_schema:
                assert key in response_json, f"Expected key '{key}' in response"
                
                # Validate value type if specified
                if expected_schema[key] is not None:
                    assert isinstance(response_json[key], expected_schema[key]), \
                        f"Expected type {expected_schema[key]} for key '{key}', got {type(response_json[key])}"
        
        return True
    
    return _validate_response

@pytest.fixture
def mock_auth_token():
    """
    Creates a mock JWT authentication token for API testing.
    
    Returns:
        str: A mock JWT authentication token.
    """
    # This is a mock token, not a real JWT
    return "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJuYW1lIjoiVGVzdCBVc2VyIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjIsInJvbGVzIjpbIm9wZXJhdGlvbnMiXX0.signature"

@pytest.fixture
def mock_auth_headers(mock_auth_token):
    """
    Creates mock authentication headers for API testing.
    
    Args:
        mock_auth_token: The mock JWT authentication token fixture.
    
    Returns:
        Dict: Mock authentication headers.
    """
    return {"Authorization": f"Bearer {mock_auth_token}"}