"""Pytest fixtures and utilities for OCR Service API tests.

This module provides shared test fixtures and utilities for testing the OCR Service API endpoints.
It includes fixtures for the FastAPI TestClient, mocks for dependencies (RabbitMQ, S3, GPU),
and helper functions for validating response schemas against OpenAPI specifications.

Fixtures:
    app: FastAPI application instance for testing
    client: TestClient for making requests to the API
    mock_rabbitmq: Mock RabbitMQ connection for testing message queue integration
    mock_s3: Mock S3 storage client for testing document storage
    mock_gpu_available: Mock GPU availability for testing readiness checks
    auth_token: JWT token for testing secured endpoints
    validate_response: Helper function for validating response schemas

Example:
    def test_health_endpoint(client):
        response = client.get("/health/liveness")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
"""

import json
import os
import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Union
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import validate, ValidationError
import jwt

# Import the main application and router
# We'll use a try/except block to handle potential import errors during testing
try:
    from src.main import app as ocr_app
except ImportError:
    # For tests, we'll create a minimal FastAPI app if the main app can't be imported
    from fastapi import FastAPI
    from src.api.router import router
    
    ocr_app = FastAPI(title="OCR Service", description="OCR Service API", version="1.0.0")
    ocr_app.include_router(router)

# Path to OpenAPI schema files for validation
OPENAPI_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), "../test_data/schemas")

# Ensure the schema directory exists
os.makedirs(OPENAPI_SCHEMA_DIR, exist_ok=True)

# Mock configuration values for testing
TEST_CONFIG = {
    "app": {
        "name": "ocr-service",
        "version": "1.0.0",
        "environment": "test",
        "debug": True,
        "port": 8000,
    },
    "rabbitmq": {
        "host": "localhost",
        "port": 5672,
        "username": "guest",
        "password": "guest",
        "exchange": "mca.documents",
        "queue": "data-extraction",
        "routing_key": "ocr",
        "use_tls": True,
    },
    "s3": {
        "endpoint": "http://localhost:9000",
        "bucket": "mca-documents-test",
        "region": "us-east-1",
        "access_key": "test-access-key",
        "secret_key": "test-secret-key",
        "use_ssl": True,
        "encryption": "AES256",
    },
    "tensorflow": {
        "model_path": "/models",
        "gpu_memory_limit": 4096,
        "confidence_threshold": 0.75,
        "use_gpu": True,
    },
    "logging": {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    },
}

# Sample document types for testing
DOCUMENT_TYPES = [
    "APPLICATION",
    "TAX_RETURN",
    "BANK_STATEMENT",
    "PAY_STUB",
    "ID_DOCUMENT",
    "OTHER",
]

# Sample OCR model types for testing
MODEL_TYPES = [
    "TYPED",
    "HANDWRITTEN",
    "HYBRID",
]

# Sample processing statuses for testing
PROCESSING_STATUSES = [
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    "NEEDS_REVIEW",
]


@pytest.fixture
def app() -> FastAPI:
    """Fixture that provides the FastAPI application for testing.
    
    Returns:
        FastAPI: The FastAPI application instance.
    """
    # Apply test configuration patches
    with patch("src.config.app_config.get_config", return_value=TEST_CONFIG):
        # Return the FastAPI app instance
        return ocr_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Fixture that provides a FastAPI TestClient for making requests to the API.
    
    Args:
        app: The FastAPI application instance.
        
    Returns:
        TestClient: A TestClient instance for making requests to the API.
    """
    return TestClient(app)


@pytest.fixture
def mock_rabbitmq():
    """Fixture that provides a mock RabbitMQ connection for testing message queue integration.
    
    This mock simulates the behavior of the RabbitMQ connection, allowing tests to verify
    that messages are published and consumed correctly without requiring a real RabbitMQ instance.
    
    Returns:
        MagicMock: A mock RabbitMQ connection with methods for publishing and consuming messages.
    """
    # Create a mock RabbitMQ connection
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_connection.channel.return_value = mock_channel
    
    # Mock the basic_publish method to track published messages
    published_messages = []
    
    def mock_basic_publish(exchange, routing_key, body, properties=None):
        published_messages.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "body": json.loads(body) if isinstance(body, (str, bytes)) else body,
            "properties": properties,
        })
    
    mock_channel.basic_publish.side_effect = mock_basic_publish
    
    # Add the published messages to the mock for assertion in tests
    mock_connection.published_messages = published_messages
    
    # Mock the basic_consume method
    def mock_basic_consume(queue, on_message_callback, auto_ack=False):
        mock_connection.consume_callback = on_message_callback
        return "consumer_tag"
    
    mock_channel.basic_consume.side_effect = mock_basic_consume
    
    # Add a method to simulate receiving a message
    def simulate_message(body, properties=None, delivery_tag="test_delivery_tag"):
        method = MagicMock()
        method.delivery_tag = delivery_tag
        
        if properties is None:
            properties = MagicMock()
            properties.content_type = "application/json"
        
        # Convert dict to JSON string if needed
        if isinstance(body, dict):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        
        mock_connection.consume_callback(mock_channel, method, properties, body)
    
    mock_connection.simulate_message = simulate_message
    
    # Apply the patch and yield the mock
    with patch("src.services.rabbitmq_service.get_connection", return_value=mock_connection):
        yield mock_connection


@pytest.fixture
def mock_s3():
    """Fixture that provides a mock S3 storage client for testing document storage.
    
    This mock simulates the behavior of the S3 client, allowing tests to verify that
    documents are stored and retrieved correctly without requiring a real S3 instance.
    
    Returns:
        MagicMock: A mock S3 client with methods for storing and retrieving documents.
    """
    # Create a mock S3 client
    mock_client = MagicMock()
    
    # Create an in-memory storage for objects
    storage = {}
    
    # Mock the put_object method
    def mock_put_object(Bucket, Key, Body, **kwargs):
        storage[(Bucket, Key)] = {
            "Body": Body,
            "Metadata": kwargs.get("Metadata", {}),
            "ContentType": kwargs.get("ContentType", "application/octet-stream"),
            "ServerSideEncryption": kwargs.get("ServerSideEncryption"),
        }
        return {"ETag": f"\"{uuid.uuid4()}\"", "VersionId": str(uuid.uuid4())}
    
    mock_client.put_object.side_effect = mock_put_object
    
    # Mock the get_object method
    def mock_get_object(Bucket, Key, **kwargs):
        if (Bucket, Key) not in storage:
            # Simulate NoSuchKey error
            error = Exception("NoSuchKey")
            error.response = {"Error": {"Code": "NoSuchKey"}}
            raise error
        
        obj = storage[(Bucket, Key)]
        
        # Create a file-like object for the Body
        body = MagicMock()
        body.read.return_value = obj["Body"]
        
        return {
            "Body": body,
            "Metadata": obj["Metadata"],
            "ContentType": obj["ContentType"],
            "ServerSideEncryption": obj["ServerSideEncryption"],
        }
    
    mock_client.get_object.side_effect = mock_get_object
    
    # Mock the list_objects_v2 method
    def mock_list_objects_v2(Bucket, Prefix=None, **kwargs):
        keys = []
        for (bucket, key) in storage.keys():
            if bucket == Bucket and (Prefix is None or key.startswith(Prefix)):
                keys.append({"Key": key})
        
        return {"Contents": keys}
    
    mock_client.list_objects_v2.side_effect = mock_list_objects_v2
    
    # Mock the delete_object method
    def mock_delete_object(Bucket, Key, **kwargs):
        if (Bucket, Key) in storage:
            del storage[(Bucket, Key)]
        return {}
    
    mock_client.delete_object.side_effect = mock_delete_object
    
    # Add the storage to the mock for direct access in tests
    mock_client.storage = storage
    
    # Apply the patch and yield the mock
    with patch("src.services.s3_service.get_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_gpu_available():
    """Fixture that provides a mock for GPU availability testing.
    
    This mock simulates the availability of a GPU for TensorFlow processing,
    allowing tests to verify that the readiness probe correctly checks for GPU availability.
    
    Returns:
        bool: True if GPU is available, False otherwise.
    """
    # By default, simulate that GPU is available
    gpu_available = True
    
    # Apply the patch and yield the mock
    with patch("src.services.tensorflow_service.is_gpu_available", return_value=gpu_available):
        yield gpu_available


@pytest.fixture
def mock_gpu_unavailable():
    """Fixture that provides a mock for GPU unavailability testing.
    
    This mock simulates the unavailability of a GPU for TensorFlow processing,
    allowing tests to verify that the readiness probe correctly handles GPU unavailability.
    
    Returns:
        bool: False to indicate GPU is not available.
    """
    # Simulate that GPU is not available
    gpu_available = False
    
    # Apply the patch and yield the mock
    with patch("src.services.tensorflow_service.is_gpu_available", return_value=gpu_available):
        yield gpu_available


@pytest.fixture
def auth_token(request):
    """Fixture that provides a JWT token for testing secured endpoints.
    
    This fixture generates a valid JWT token with the specified role for testing
    endpoints that require authentication and authorization.
    
    Args:
        request: The pytest request object, which can include a 'role' parameter.
        
    Returns:
        str: A valid JWT token for the specified role.
    """
    # Get the role from the request or default to 'operations_staff'
    role = getattr(request, "param", "operations_staff")
    
    # Define the token payload
    payload = {
        "sub": f"test-user-{uuid.uuid4()}",
        "name": "Test User",
        "email": "test@dollarfunding.com",
        "roles": [role],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    
    # Generate the token with a test secret key
    token = jwt.encode(payload, "test-secret-key", algorithm="HS256")
    
    # Apply the patch to the JWT verification function
    with patch("src.services.auth_service.verify_token", return_value=payload):
        yield token


@pytest.fixture
def sample_document():
    """Fixture that provides a sample document for testing OCR processing.
    
    This fixture creates a sample document with metadata and content for testing
    OCR processing endpoints.
    
    Returns:
        dict: A sample document with metadata and content.
    """
    return {
        "document_id": str(uuid.uuid4()),
        "application_id": str(uuid.uuid4()),
        "filename": "test_document.pdf",
        "content_type": "application/pdf",
        "size": 12345,
        "document_type": "APPLICATION",
        "upload_date": datetime.utcnow().isoformat(),
        "status": "PENDING",
        "metadata": {
            "pages": 2,
            "has_signature": True,
            "is_complete": True,
        },
    }


@pytest.fixture
def sample_ocr_result():
    """Fixture that provides a sample OCR result for testing.
    
    This fixture creates a sample OCR result with extracted fields and confidence scores
    for testing OCR processing endpoints.
    
    Returns:
        dict: A sample OCR result with extracted fields and confidence scores.
    """
    return {
        "document_id": str(uuid.uuid4()),
        "processing_time": 1.23,
        "model_type": "TYPED",
        "extracted_data": {
            "fields": {
                "business_name": {
                    "value": "Acme Corporation",
                    "confidence": 0.98,
                    "location": {"page": 1, "top": 100, "left": 100, "width": 200, "height": 30},
                },
                "tax_id": {
                    "value": "12-3456789",
                    "confidence": 0.95,
                    "location": {"page": 1, "top": 150, "left": 100, "width": 150, "height": 30},
                },
                "address": {
                    "value": "123 Main St, Anytown, CA 12345",
                    "confidence": 0.92,
                    "location": {"page": 1, "top": 200, "left": 100, "width": 300, "height": 30},
                },
                "requested_amount": {
                    "value": "50000",
                    "confidence": 0.97,
                    "location": {"page": 1, "top": 250, "left": 100, "width": 100, "height": 30},
                },
                "signature": {
                    "value": "John Smith",
                    "confidence": 0.85,
                    "location": {"page": 2, "top": 500, "left": 400, "width": 200, "height": 50},
                },
            },
            "tables": [
                {
                    "name": "revenue_table",
                    "location": {"page": 1, "top": 300, "left": 100, "width": 400, "height": 200},
                    "confidence": 0.90,
                    "data": [
                        ["Month", "Revenue", "Expenses", "Profit"],
                        ["January", "10000", "8000", "2000"],
                        ["February", "12000", "9000", "3000"],
                        ["March", "15000", "10000", "5000"],
                    ],
                }
            ],
        },
        "needs_review": False,
        "low_confidence_fields": [],
        "processing_status": "COMPLETED",
        "completion_time": datetime.utcnow().isoformat(),
    }


@pytest.fixture
def sample_ocr_result_with_low_confidence():
    """Fixture that provides a sample OCR result with low confidence fields for testing.
    
    This fixture creates a sample OCR result with some fields having low confidence scores,
    which should trigger a review by a human operator.
    
    Returns:
        dict: A sample OCR result with low confidence fields.
    """
    return {
        "document_id": str(uuid.uuid4()),
        "processing_time": 1.45,
        "model_type": "HYBRID",
        "extracted_data": {
            "fields": {
                "business_name": {
                    "value": "Acme Corporation",
                    "confidence": 0.98,
                    "location": {"page": 1, "top": 100, "left": 100, "width": 200, "height": 30},
                },
                "tax_id": {
                    "value": "12-3456789",
                    "confidence": 0.65,  # Low confidence
                    "location": {"page": 1, "top": 150, "left": 100, "width": 150, "height": 30},
                },
                "address": {
                    "value": "123 Main St, Anytown, CA 12345",
                    "confidence": 0.92,
                    "location": {"page": 1, "top": 200, "left": 100, "width": 300, "height": 30},
                },
                "requested_amount": {
                    "value": "50000",
                    "confidence": 0.97,
                    "location": {"page": 1, "top": 250, "left": 100, "width": 100, "height": 30},
                },
                "signature": {
                    "value": "John Smith",
                    "confidence": 0.55,  # Low confidence
                    "location": {"page": 2, "top": 500, "left": 400, "width": 200, "height": 50},
                },
            },
            "tables": [
                {
                    "name": "revenue_table",
                    "location": {"page": 1, "top": 300, "left": 100, "width": 400, "height": 200},
                    "confidence": 0.90,
                    "data": [
                        ["Month", "Revenue", "Expenses", "Profit"],
                        ["January", "10000", "8000", "2000"],
                        ["February", "12000", "9000", "3000"],
                        ["March", "15000", "10000", "5000"],
                    ],
                }
            ],
        },
        "needs_review": True,
        "low_confidence_fields": ["tax_id", "signature"],
        "processing_status": "NEEDS_REVIEW",
        "completion_time": datetime.utcnow().isoformat(),
    }


def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load an OpenAPI schema from the schema directory.
    
    Args:
        schema_name: The name of the schema file to load.
        
    Returns:
        Dict[str, Any]: The loaded schema as a dictionary.
        
    Raises:
        FileNotFoundError: If the schema file does not exist.
    """
    schema_path = os.path.join(OPENAPI_SCHEMA_DIR, f"{schema_name}.json")
    
    # If the schema file doesn't exist, create a minimal schema for testing
    if not os.path.exists(schema_path):
        # Create a directory for the schema if it doesn't exist
        os.makedirs(os.path.dirname(schema_path), exist_ok=True)
        
        # Create a minimal schema based on the schema name
        if schema_name == "health":
            schema = {
                "type": "object",
                "required": ["status"],
                "properties": {
                    "status": {"type": "string", "enum": ["ok", "error"]},
                    "details": {"type": "object"},
                    "timestamp": {"type": "string", "format": "date-time"},
                },
            }
        elif schema_name == "ocr_result":
            schema = {
                "type": "object",
                "required": ["document_id", "extracted_data", "processing_status"],
                "properties": {
                    "document_id": {"type": "string", "format": "uuid"},
                    "processing_time": {"type": "number"},
                    "model_type": {"type": "string", "enum": MODEL_TYPES},
                    "extracted_data": {"type": "object"},
                    "needs_review": {"type": "boolean"},
                    "low_confidence_fields": {"type": "array", "items": {"type": "string"}},
                    "processing_status": {"type": "string", "enum": PROCESSING_STATUSES},
                    "completion_time": {"type": "string", "format": "date-time"},
                },
            }
        elif schema_name == "document":
            schema = {
                "type": "object",
                "required": ["document_id", "filename", "document_type", "status"],
                "properties": {
                    "document_id": {"type": "string", "format": "uuid"},
                    "application_id": {"type": "string", "format": "uuid"},
                    "filename": {"type": "string"},
                    "content_type": {"type": "string"},
                    "size": {"type": "integer"},
                    "document_type": {"type": "string", "enum": DOCUMENT_TYPES},
                    "upload_date": {"type": "string", "format": "date-time"},
                    "status": {"type": "string", "enum": PROCESSING_STATUSES},
                    "metadata": {"type": "object"},
                },
            }
        elif schema_name == "metrics":
            schema = {
                "type": "object",
                "required": ["metrics"],
                "properties": {
                    "metrics": {
                        "type": "object",
                        "properties": {
                            "ocr_accuracy": {"type": "number"},
                            "processing_time_avg": {"type": "number"},
                            "queue_depth": {"type": "integer"},
                            "documents_processed": {"type": "integer"},
                            "documents_pending": {"type": "integer"},
                            "documents_failed": {"type": "integer"},
                            "cpu_usage": {"type": "number"},
                            "gpu_usage": {"type": "number"},
                            "memory_usage": {"type": "number"},
                        },
                    },
                    "timestamp": {"type": "string", "format": "date-time"},
                },
            }
        else:
            # Generic schema for unknown schema names
            schema = {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                },
            }
        
        # Write the schema to the file
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
    
    # Load the schema from the file
    with open(schema_path, "r") as f:
        return json.load(f)


@pytest.fixture
def validate_response():
    """Fixture that provides a function for validating response schemas against OpenAPI specifications.
    
    This fixture returns a function that validates a response against a schema,
    making it easy to verify that API responses conform to the expected format.
    
    Returns:
        Callable: A function for validating response schemas.
    """
    def _validate_response(response_data: Dict[str, Any], schema_name: str) -> bool:
        """Validate a response against an OpenAPI schema.
        
        Args:
            response_data: The response data to validate.
            schema_name: The name of the schema to validate against.
            
        Returns:
            bool: True if the response is valid, False otherwise.
            
        Raises:
            ValidationError: If the response does not conform to the schema.
        """
        schema = load_schema(schema_name)
        validate(instance=response_data, schema=schema)
        return True
    
    return _validate_response


@pytest.fixture
def mock_tensorflow_service():
    """Fixture that provides a mock TensorFlow service for testing OCR processing.
    
    This mock simulates the behavior of the TensorFlow service, allowing tests to verify
    that OCR processing works correctly without requiring a real TensorFlow instance.
    
    Returns:
        MagicMock: A mock TensorFlow service with methods for OCR processing.
    """
    # Create a mock TensorFlow service
    mock_service = MagicMock()
    
    # Mock the process_document method
    def mock_process_document(document_id, document_type, content):
        # Return a sample OCR result based on the document type
        if document_type == "APPLICATION":
            return {
                "document_id": document_id,
                "processing_time": 1.23,
                "model_type": "TYPED",
                "extracted_data": {
                    "fields": {
                        "business_name": {
                            "value": "Acme Corporation",
                            "confidence": 0.98,
                        },
                        "tax_id": {
                            "value": "12-3456789",
                            "confidence": 0.95,
                        },
                    },
                },
                "needs_review": False,
                "low_confidence_fields": [],
                "processing_status": "COMPLETED",
            }
        elif document_type == "ID_DOCUMENT":
            return {
                "document_id": document_id,
                "processing_time": 1.45,
                "model_type": "HYBRID",
                "extracted_data": {
                    "fields": {
                        "name": {
                            "value": "John Smith",
                            "confidence": 0.92,
                        },
                        "id_number": {
                            "value": "X123456",
                            "confidence": 0.65,  # Low confidence
                        },
                    },
                },
                "needs_review": True,
                "low_confidence_fields": ["id_number"],
                "processing_status": "NEEDS_REVIEW",
            }
        else:
            return {
                "document_id": document_id,
                "processing_time": 1.0,
                "model_type": "TYPED",
                "extracted_data": {
                    "fields": {},
                },
                "needs_review": False,
                "low_confidence_fields": [],
                "processing_status": "COMPLETED",
            }
    
    mock_service.process_document.side_effect = mock_process_document
    
    # Apply the patch and yield the mock
    with patch("src.services.tensorflow_service.process_document", side_effect=mock_process_document):
        yield mock_service


@pytest.fixture
def mock_metrics_service():
    """Fixture that provides a mock metrics service for testing status endpoints.
    
    This mock simulates the behavior of the metrics service, allowing tests to verify
    that status endpoints correctly report service metrics.
    
    Returns:
        MagicMock: A mock metrics service with methods for retrieving metrics.
    """
    # Create a mock metrics service
    mock_service = MagicMock()
    
    # Mock the get_metrics method
    def mock_get_metrics():
        return {
            "ocr_accuracy": 0.99,  # 99% accuracy as specified in section 0.1.1
            "processing_time_avg": 1.5,  # Average processing time in seconds
            "queue_depth": 5,  # Current queue depth
            "documents_processed": 1000,  # Total documents processed
            "documents_pending": 10,  # Documents pending processing
            "documents_failed": 5,  # Documents that failed processing
            "cpu_usage": 45.2,  # CPU usage percentage
            "gpu_usage": 78.5,  # GPU usage percentage
            "memory_usage": 62.3,  # Memory usage percentage
        }
    
    mock_service.get_metrics.side_effect = mock_get_metrics
    
    # Apply the patch and yield the mock
    with patch("src.services.metrics_service.get_metrics", side_effect=mock_get_metrics):
        yield mock_service


# Helper functions for tests

def create_test_document(document_type: str = "APPLICATION") -> Dict[str, Any]:
    """Create a test document with the specified document type.
    
    Args:
        document_type: The type of document to create.
        
    Returns:
        Dict[str, Any]: A test document with the specified document type.
    """
    return {
        "document_id": str(uuid.uuid4()),
        "application_id": str(uuid.uuid4()),
        "filename": f"test_{document_type.lower()}.pdf",
        "content_type": "application/pdf",
        "size": 12345,
        "document_type": document_type,
        "upload_date": datetime.utcnow().isoformat(),
        "status": "PENDING",
        "metadata": {
            "pages": 2,
            "has_signature": True,
            "is_complete": True,
        },
    }