"""Pytest fixtures and utilities for OCR Service integration tests.

This module provides shared test fixtures and utilities for testing the integration
between different components of the OCR Service. It includes fixtures for mocking
external dependencies (RabbitMQ, S3), test documents, and helper functions for
verifying OCR results and confidence scores.

Fixtures:
    mock_rabbitmq_connection: Mock RabbitMQ connection for testing message queue operations
    mock_s3_client: Mock S3 client for testing document storage operations
    mock_storage_service: Mock storage service for testing document storage operations
    mock_queue_service: Mock queue service for testing message operations
    mock_ocr_service: Mock OCR service for testing text extraction
    mock_field_extraction_service: Mock field extraction service for testing field extraction
    mock_confidence_service: Mock confidence service for testing confidence scoring
    mock_document_processing_pipeline: Mock document processing pipeline for integration testing
    mock_message_handler: Mock message handler for testing message processing
    sample_document_paths: Paths to sample documents for testing
    sample_document_metadata: Metadata for sample documents used in testing
    create_test_document: Factory fixture to create temporary test documents for OCR testing
    verify_ocr_result: Function to verify OCR results against expected values
    wait_for_message: Function to wait for a message to be published to a queue
    setup_test_document: Function to set up a test document in S3 storage
    setup_ocr_pipeline: Sets up the complete OCR pipeline for integration testing

Example:
    def test_document_processing_pipeline(setup_ocr_pipeline, setup_test_document, verify_ocr_result):
        # Set up a test document
        document = setup_test_document(document_type="typed")
        
        # Process the document
        result = setup_ocr_pipeline["document_processing_pipeline"].process_document(
            document["document_path"], document["document_type"]
        )
        
        # Verify the result
        expected = {
            "document_type": "application_form",
            "expected_fields": {
                "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                "tax_id": {"value": "12-3456789", "confidence": 0.97},
                "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
            }
        }
        assert verify_ocr_result(result, expected)
"""

import os
import json
import time
import pytest
import tempfile
import logging
import uuid
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple, Optional, Union

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants for test configuration
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
TYPED_DOCS_DIR = TEST_DATA_DIR / "typed_documents"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MIXED_DOCS_DIR = TEST_DATA_DIR / "mixed_documents"
TABLES_DIR = TEST_DATA_DIR / "tables"

# Test timeout and retry settings
TEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1  # seconds


# ===== Configuration Fixtures =====

@pytest.fixture
def app_config():
    """Provides a test configuration for the OCR service."""
    return {
        "service": {
            "name": "ocr-service",
            "version": "1.0.0",
            "port": 8080,
            "environment": "test"
        },
        "tensorflow": {
            "gpu_memory_limit": 1024,  # MB
            "allow_growth": True,
            "per_process_gpu_memory_fraction": 0.5,
            "model_path": str(TEST_DATA_DIR / "models"),
            "confidence_threshold": 0.75
        },
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
            "exchange": "mca.documents",
            "queue": "data-extraction",
            "routing_key": "ocr",
            "ssl": False,  # Disabled for testing
            "prefetch_count": 10
        },
        "s3": {
            "endpoint_url": "http://localhost:9000",
            "region_name": "us-east-1",
            "bucket": "mca-documents-test",
            "use_ssl": False,  # Disabled for testing
            "encryption": {
                "algorithm": "AES256",
                "enabled": True
            }
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }


@pytest.fixture
def env_vars(monkeypatch):
    """Sets up environment variables for testing."""
    test_vars = {
        "OCR_SERVICE_PORT": "8080",
        "TENSORFLOW_GPU_MEMORY_LIMIT": "1024",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "guest",
        "RABBITMQ_PASSWORD": "guest",
        "RABBITMQ_EXCHANGE": "mca.documents",
        "RABBITMQ_QUEUE": "data-extraction",
        "S3_ENDPOINT_URL": "http://localhost:9000",
        "S3_REGION_NAME": "us-east-1",
        "S3_BUCKET": "mca-documents-test",
        "LOG_LEVEL": "DEBUG"
    }
    
    for key, value in test_vars.items():
        monkeypatch.setenv(key, value)
    
    return test_vars


# ===== RabbitMQ Fixtures =====

@pytest.fixture
def mock_rabbitmq_connection():
    """Creates a mock RabbitMQ connection for testing message queue operations."""
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_connection.channel.return_value = mock_channel
    
    # Message storage for testing
    message_storage = []
    
    # Mock basic_publish method
    def mock_basic_publish(exchange, routing_key, body, properties=None):
        message_storage.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "body": body if isinstance(body, dict) else json.loads(body) if isinstance(body, (str, bytes)) else body,
            "properties": properties
        })
        logger.debug(f"Message published to {exchange}/{routing_key}: {body}")
    
    # Mock basic_consume method
    def mock_basic_consume(queue, on_message_callback, auto_ack=False):
        # Store the callback for later use
        mock_channel._on_message_callback = on_message_callback
        return "mock-consumer-tag"
    
    # Method to simulate message receipt for testing
    def simulate_message_received(body, delivery_tag="mock-tag", properties=None):
        mock_method = MagicMock()
        mock_method.delivery_tag = delivery_tag
        
        if properties is None:
            properties = MagicMock()
            properties.content_type = "application/json"
            properties.correlation_id = str(uuid.uuid4())
        
        # Convert dict to JSON string if needed
        if isinstance(body, dict):
            body = json.dumps(body).encode()
        elif isinstance(body, str):
            body = body.encode()
        
        logger.debug(f"Simulating message received: {body}")
        mock_channel._on_message_callback(mock_channel, mock_method, properties, body)
    
    # Assign mock methods
    mock_channel.basic_publish.side_effect = mock_basic_publish
    mock_channel.basic_consume.side_effect = mock_basic_consume
    mock_channel.simulate_message_received = simulate_message_received
    mock_channel.message_storage = message_storage
    
    # Apply patch and yield the mock
    with patch("src.services.queue_service.get_rabbitmq_connection", return_value=mock_connection):
        yield mock_connection


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """Returns the mock RabbitMQ channel from the mock connection."""
    return mock_rabbitmq_connection.channel()


@pytest.fixture
def mock_queue_service(mock_rabbitmq_connection):
    """Creates a mock queue service for testing message operations."""
    mock_service = MagicMock()
    
    # Message storage for testing
    message_storage = []
    
    # Mock publish method
    def mock_publish(exchange, routing_key, message, correlation_id=None):
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        message_storage.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "message": message,
            "correlation_id": correlation_id
        })
        logger.debug(f"Message published to {exchange}/{routing_key}: {message}")
        return True
    
    # Mock consume method
    def mock_consume(queue, callback):
        # Store the callback for later use
        mock_service._callback = callback
        return "mock-consumer-tag"
    
    # Method to simulate message receipt for testing
    def simulate_message_received(message, correlation_id=None):
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        logger.debug(f"Simulating message received: {message}")
        mock_service._callback(message, correlation_id)
    
    # Assign mock methods
    mock_service.publish.side_effect = mock_publish
    mock_service.consume.side_effect = mock_consume
    mock_service.simulate_message_received = simulate_message_received
    mock_service.message_storage = message_storage
    
    # Apply patch and yield the mock
    with patch("src.services.queue_service.QueueService", return_value=mock_service):
        yield mock_service


# ===== S3 Storage Fixtures =====

@pytest.fixture
def mock_s3_client():
    """Creates a mock S3 client for testing document storage operations."""
    mock_client = MagicMock()
    
    # Mock storage dictionary to simulate S3 storage
    storage_dict = {}
    
    # Mock download_file method
    def mock_download_file(Bucket, Key, Filename):
        if Key in storage_dict:
            with open(Filename, 'wb') as f:
                f.write(storage_dict[Key]["content"])
        else:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": f"The specified key {Key} does not exist."}}, "GetObject")
    
    # Mock upload_file method
    def mock_upload_file(Filename, Bucket, Key, ExtraArgs=None):
        with open(Filename, 'rb') as f:
            content = f.read()
        
        metadata = {}
        if ExtraArgs and "Metadata" in ExtraArgs:
            metadata = ExtraArgs["Metadata"]
        
        storage_dict[Key] = {
            "content": content,
            "metadata": metadata,
            "bucket": Bucket
        }
        
        logger.debug(f"File uploaded to {Bucket}/{Key}: {len(content)} bytes")
        return {"ETag": "mock-etag"}
    
    # Mock get_object method
    def mock_get_object(Bucket, Key):
        if Key in storage_dict:
            from io import BytesIO
            return {
                "Body": BytesIO(storage_dict[Key]["content"]),
                "ContentLength": len(storage_dict[Key]["content"]),
                "Metadata": storage_dict[Key]["metadata"]
            }
        else:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": f"The specified key {Key} does not exist."}}, "GetObject")
    
    # Mock put_object method
    def mock_put_object(Bucket, Key, Body, Metadata=None, **kwargs):
        if Metadata is None:
            Metadata = {}
        
        if isinstance(Body, (str, bytes)):
            content = Body if isinstance(Body, bytes) else Body.encode()
        else:
            # Handle file-like objects
            content = Body.read()
            if hasattr(Body, 'seek'):
                Body.seek(0)
        
        storage_dict[Key] = {
            "content": content,
            "metadata": Metadata,
            "bucket": Bucket
        }
        
        logger.debug(f"Object put to {Bucket}/{Key}: {len(content)} bytes")
        return {"ETag": "mock-etag"}
    
    # Assign mock methods
    mock_client.download_file.side_effect = mock_download_file
    mock_client.upload_file.side_effect = mock_upload_file
    mock_client.get_object.side_effect = mock_get_object
    mock_client.put_object.side_effect = mock_put_object
    
    # Add storage dictionary to mock for direct access in tests
    mock_client.storage_dict = storage_dict
    
    # Apply patch and yield the mock
    with patch("src.services.storage_service.get_s3_client", return_value=mock_client):
        yield mock_client


@pytest.fixture
def mock_storage_service(mock_s3_client):
    """Creates a mock storage service for testing document storage operations."""
    mock_service = MagicMock()
    
    # Mock upload method
    def mock_upload(file_path, key, metadata=None):
        if metadata is None:
            metadata = {}
        
        # Use the mock S3 client to upload the file
        if isinstance(file_path, (str, Path)):
            mock_s3_client.upload_file(
                str(file_path),
                "mca-documents-test",
                key,
                ExtraArgs={"Metadata": metadata}
            )
        else:
            # Handle file-like objects
            mock_s3_client.put_object(
                Bucket="mca-documents-test",
                Key=key,
                Body=file_path,
                Metadata=metadata
            )
        
        return {
            "key": key,
            "bucket": "mca-documents-test",
            "metadata": metadata
        }
    
    # Mock download method
    def mock_download(key, destination_path):
        try:
            # Use the mock S3 client to download the file
            mock_s3_client.download_file(
                "mca-documents-test",
                key,
                str(destination_path)
            )
            
            # Get metadata
            obj = mock_s3_client.get_object(
                Bucket="mca-documents-test",
                Key=key
            )
            
            return {
                "key": key,
                "bucket": "mca-documents-test",
                "metadata": obj["Metadata"],
                "size": obj["ContentLength"]
            }
        except Exception as e:
            logger.error(f"Error downloading file {key}: {str(e)}")
            raise
    
    # Mock get_metadata method
    def mock_get_metadata(key):
        try:
            obj = mock_s3_client.get_object(
                Bucket="mca-documents-test",
                Key=key
            )
            return obj["Metadata"]
        except Exception as e:
            logger.error(f"Error getting metadata for {key}: {str(e)}")
            raise
    
    # Assign mock methods
    mock_service.upload.side_effect = mock_upload
    mock_service.download.side_effect = mock_download
    mock_service.get_metadata.side_effect = mock_get_metadata
    
    # Apply patch and yield the mock
    with patch("src.services.storage_service.StorageService", return_value=mock_service):
        yield mock_service


# ===== TensorFlow Fixtures =====

@pytest.fixture
def mock_tensorflow_session():
    """Creates a mock TensorFlow session for testing model operations."""
    mock_session = MagicMock()
    mock_graph = MagicMock()
    mock_session.graph = mock_graph
    
    # Mock run method to return predictable results
    def mock_run(fetches, feed_dict=None):
        # Simple mock implementation that returns random values
        # In a real test, this would return more realistic values based on the input
        if isinstance(fetches, list):
            return [np.random.random((10, 10)) for _ in fetches]
        else:
            return np.random.random((10, 10))
    
    mock_session.run.side_effect = mock_run
    
    # Apply patch and yield the mock
    with patch("tensorflow.compat.v1.Session", return_value=mock_session):
        yield mock_session


@pytest.fixture
def mock_tensorflow_model():
    """Creates a mock TensorFlow model for testing OCR operations."""
    mock_model = MagicMock()
    
    # Mock predict method to return predictable results
    def mock_predict(image, **kwargs):
        # Return a dictionary with mock OCR results
        return {
            "text": "Sample OCR text for testing",
            "confidence": 0.95,
            "bounding_boxes": [
                [0.1, 0.1, 0.9, 0.9]  # x1, y1, x2, y2 normalized
            ]
        }
    
    mock_model.predict.side_effect = mock_predict
    
    # Apply patch and yield the mock
    with patch("src.models.base_model.BaseModel", return_value=mock_model):
        yield mock_model


@pytest.fixture
def mock_model_factory():
    """Creates a mock model factory for testing model selection."""
    mock_factory = MagicMock()
    
    # Mock get_model method to return appropriate model based on document type
    def mock_get_model(document_type=None, text_type=None):
        if text_type == "handwritten" or document_type == "handwritten":
            model = MagicMock()
            model.model_type = "handwritten"
            
            def predict_handwritten(image, **kwargs):
                return {
                    "text": "John Smith\nJohn Smith\n2023-01-15",
                    "confidence": 0.85,
                    "fields": {
                        "owner_name": {"value": "John Smith", "confidence": 0.85},
                        "signature": {"value": "John Smith", "confidence": 0.80},
                        "date": {"value": "2023-01-15", "confidence": 0.82}
                    }
                }
            
            model.predict.side_effect = predict_handwritten
            return model
        
        elif text_type == "mixed" or document_type == "mixed":
            model = MagicMock()
            model.model_type = "hybrid"
            
            def predict_mixed(image, **kwargs):
                return {
                    "text": "XYZ Industries\n98-7654321\nJane Doe",
                    "confidence": 0.91,
                    "fields": {
                        "business_name": {"value": "XYZ Industries", "confidence": 0.96},
                        "tax_id": {"value": "98-7654321", "confidence": 0.95},
                        "owner_signature": {"value": "Jane Doe", "confidence": 0.82}
                    }
                }
            
            model.predict.side_effect = predict_mixed
            return model
        
        else:  # Default to typed text model
            model = MagicMock()
            model.model_type = "typed"
            
            def predict_typed(image, **kwargs):
                return {
                    "text": "ABC Corporation\n12-3456789\n123 Main St, Anytown, USA",
                    "confidence": 0.97,
                    "fields": {
                        "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                        "tax_id": {"value": "12-3456789", "confidence": 0.97},
                        "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
                    }
                }
            
            model.predict.side_effect = predict_typed
            return model
    
    mock_factory.get_model.side_effect = mock_get_model
    
    # Apply patch and yield the mock
    with patch("src.models.model_factory.ModelFactory", return_value=mock_factory):
        yield mock_factory


# ===== Document Fixtures =====

@pytest.fixture
def sample_document_paths():
    """Returns paths to sample documents for testing."""
    return {
        "typed": list(TYPED_DOCS_DIR.glob("*.pdf")) or [TYPED_DOCS_DIR / "sample_typed.pdf"],
        "handwritten": list(HANDWRITTEN_DOCS_DIR.glob("*.pdf")) or [HANDWRITTEN_DOCS_DIR / "sample_handwritten.pdf"],
        "mixed": list(MIXED_DOCS_DIR.glob("*.pdf")) or [MIXED_DOCS_DIR / "sample_mixed.pdf"],
        "tables": list(TABLES_DIR.glob("*.pdf")) or [TABLES_DIR / "sample_table.pdf"]
    }


@pytest.fixture
def create_test_document():
    """Factory fixture to create temporary test documents for OCR testing."""
    temp_files = []
    
    def _create_document(content_type="typed", content="Sample test document", filename=None):
        # Create a temporary file
        if filename is None:
            suffix = ".pdf"  # Default to PDF
            if content_type == "image":
                suffix = ".png"
            
            temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            filename = temp_file.name
            temp_files.append(filename)
        
        # For a real implementation, this would create actual document files
        # For testing, we'll just create text files with the content
        with open(filename, 'w') as f:
            f.write(content)
        
        return filename
    
    yield _create_document
    
    # Cleanup temporary files
    for file in temp_files:
        if os.path.exists(file):
            os.unlink(file)


@pytest.fixture
def sample_document_metadata():
    """Returns metadata for sample documents used in testing."""
    metadata_path = TEST_DATA_DIR / "metadata.json"
    
    # Create default metadata if file doesn't exist
    if not metadata_path.exists():
        default_metadata = {
            "typed": {
                "sample_typed.pdf": {
                    "document_type": "application_form",
                    "expected_fields": {
                        "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                        "tax_id": {"value": "12-3456789", "confidence": 0.97},
                        "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
                    }
                }
            },
            "handwritten": {
                "sample_handwritten.pdf": {
                    "document_type": "application_form",
                    "expected_fields": {
                        "owner_name": {"value": "John Smith", "confidence": 0.85},
                        "signature": {"value": "John Smith", "confidence": 0.80},
                        "date": {"value": "2023-01-15", "confidence": 0.82}
                    }
                }
            },
            "mixed": {
                "sample_mixed.pdf": {
                    "document_type": "application_form",
                    "expected_fields": {
                        "business_name": {"value": "XYZ Industries", "confidence": 0.96},
                        "tax_id": {"value": "98-7654321", "confidence": 0.95},
                        "owner_signature": {"value": "Jane Doe", "confidence": 0.82}
                    }
                }
            },
            "tables": {
                "sample_table.pdf": {
                    "document_type": "financial_statement",
                    "expected_table": {
                        "headers": ["Date", "Description", "Amount"],
                        "rows": [
                            ["2023-01-01", "Opening Balance", "$10,000.00"],
                            ["2023-01-15", "Invoice #12345", "$5,250.75"],
                            ["2023-01-31", "Closing Balance", "$15,250.75"]
                        ],
                        "confidence": 0.94
                    }
                }
            }
        }
        
        # Write default metadata for testing
        with open(metadata_path, 'w') as f:
            json.dump(default_metadata, f, indent=2)
    
    # Read metadata from file
    with open(metadata_path, 'r') as f:
        return json.load(f)


# ===== Service Mocks =====

@pytest.fixture
def mock_ocr_service(mock_model_factory):
    """Creates a mock OCR service for testing."""
    mock_service = MagicMock()
    
    # Mock extract_text method
    def mock_extract_text(document_path, document_type="typed"):
        # Return different results based on document type
        if document_type == "typed":
            return {
                "text": "ABC Corporation\n12-3456789\n123 Main St, Anytown, USA",
                "fields": {
                    "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                    "tax_id": {"value": "12-3456789", "confidence": 0.97},
                    "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
                },
                "confidence": 0.97,
                "processing_time": 0.75
            }
        elif document_type == "handwritten":
            return {
                "text": "John Smith\nJohn Smith\n2023-01-15",
                "fields": {
                    "owner_name": {"value": "John Smith", "confidence": 0.85},
                    "signature": {"value": "John Smith", "confidence": 0.80},
                    "date": {"value": "2023-01-15", "confidence": 0.82}
                },
                "confidence": 0.82,
                "processing_time": 1.25
            }
        elif document_type == "mixed":
            return {
                "text": "XYZ Industries\n98-7654321\nJane Doe",
                "fields": {
                    "business_name": {"value": "XYZ Industries", "confidence": 0.96},
                    "tax_id": {"value": "98-7654321", "confidence": 0.95},
                    "owner_signature": {"value": "Jane Doe", "confidence": 0.82}
                },
                "confidence": 0.91,
                "processing_time": 1.5
            }
        elif document_type == "table":
            return {
                "text": "Date Description Amount\n2023-01-01 Opening Balance $10,000.00\n2023-01-15 Invoice #12345 $5,250.75\n2023-01-31 Closing Balance $15,250.75",
                "table": {
                    "headers": ["Date", "Description", "Amount"],
                    "rows": [
                        ["2023-01-01", "Opening Balance", "$10,000.00"],
                        ["2023-01-15", "Invoice #12345", "$5,250.75"],
                        ["2023-01-31", "Closing Balance", "$15,250.75"]
                    ]
                },
                "confidence": 0.94,
                "processing_time": 2.0
            }
        else:
            return {
                "text": "Unknown document type",
                "fields": {},
                "confidence": 0.5,
                "processing_time": 1.0
            }
    
    mock_service.extract_text.side_effect = mock_extract_text
    
    # Apply patch and yield the mock
    with patch("src.services.ocr_service.OCRService", return_value=mock_service):
        yield mock_service


@pytest.fixture
def mock_field_extraction_service():
    """Creates a mock field extraction service for testing."""
    mock_service = MagicMock()
    
    # Mock extract_fields method
    def mock_extract_fields(text, document_type=None):
        # Return different fields based on document type
        if document_type == "application_form":
            return {
                "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                "tax_id": {"value": "12-3456789", "confidence": 0.97},
                "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
            }
        elif document_type == "financial_statement":
            return {
                "table": {
                    "headers": ["Date", "Description", "Amount"],
                    "rows": [
                        ["2023-01-01", "Opening Balance", "$10,000.00"],
                        ["2023-01-15", "Invoice #12345", "$5,250.75"],
                        ["2023-01-31", "Closing Balance", "$15,250.75"]
                    ],
                    "confidence": 0.94
                }
            }
        elif document_type == "id_document":
            return {
                "name": {"value": "John Smith", "confidence": 0.85},
                "id_number": {"value": "X123456", "confidence": 0.80},
                "expiration_date": {"value": "2025-01-15", "confidence": 0.82}
            }
        else:
            # Try to extract common fields based on text content
            fields = {}
            if "Corporation" in text or "Industries" in text:
                fields["business_name"] = {"value": text.split("\n")[0], "confidence": 0.90}
            if any(c.isdigit() for c in text):
                # Extract something that looks like a tax ID
                import re
                tax_id_match = re.search(r'\d{2}-\d{7}', text)
                if tax_id_match:
                    fields["tax_id"] = {"value": tax_id_match.group(), "confidence": 0.85}
            
            return fields
    
    mock_service.extract_fields.side_effect = mock_extract_fields
    
    # Apply patch and yield the mock
    with patch("src.services.field_extraction_service.FieldExtractionService", return_value=mock_service):
        yield mock_service


@pytest.fixture
def mock_confidence_service():
    """Creates a mock confidence scoring service for testing."""
    mock_service = MagicMock()
    
    # Mock calculate_confidence method
    def mock_calculate_confidence(text, field_type=None):
        # Return different confidence scores based on text and field type
        if field_type == "business_name":
            return 0.98
        elif field_type == "tax_id":
            return 0.97
        elif field_type == "address":
            return 0.95
        elif field_type == "owner_name":
            return 0.85
        elif field_type == "signature":
            return 0.80
        elif field_type == "date":
            return 0.82
        elif field_type == "table":
            return 0.94
        else:
            # Default confidence based on text length and complexity
            base_confidence = 0.75
            if text and len(text) > 5:
                base_confidence += 0.1
            if text and any(c.isdigit() for c in text):
                base_confidence += 0.05
            return min(base_confidence, 0.99)  # Cap at 0.99
    
    # Mock is_confident method
    def mock_is_confident(confidence, threshold=0.75):
        return confidence >= threshold
    
    # Assign mock methods
    mock_service.calculate_confidence.side_effect = mock_calculate_confidence
    mock_service.is_confident.side_effect = mock_is_confident
    
    # Apply patch and yield the mock
    with patch("src.services.confidence_service.ConfidenceService", return_value=mock_service):
        yield mock_service


# ===== Integration Fixtures =====

@pytest.fixture
def mock_document_processing_pipeline(
    mock_ocr_service,
    mock_field_extraction_service,
    mock_confidence_service,
    mock_storage_service
):
    """Creates a mock document processing pipeline for integration testing."""
    mock_pipeline = MagicMock()
    
    # Mock process_document method
    def mock_process_document(document_path, document_type=None):
        # Auto-detect document type if not provided
        if document_type is None:
            if "typed" in str(document_path):
                document_type = "typed"
            elif "handwritten" in str(document_path):
                document_type = "handwritten"
            elif "mixed" in str(document_path):
                document_type = "mixed"
            elif "table" in str(document_path):
                document_type = "table"
            else:
                document_type = "typed"  # Default
        
        # Extract text using OCR service
        ocr_result = mock_ocr_service.extract_text(document_path, document_type)
        
        # Determine document classification
        if document_type == "table":
            doc_classification = "financial_statement"
        else:
            doc_classification = "application_form"
        
        # Extract fields using field extraction service
        if "fields" in ocr_result:
            fields = ocr_result["fields"]
        else:
            fields = mock_field_extraction_service.extract_fields(ocr_result["text"], doc_classification)
        
        # Calculate overall confidence
        if "confidence" in ocr_result:
            overall_confidence = ocr_result["confidence"]
        else:
            # Average confidence of all fields
            confidences = [field["confidence"] for field in fields.values() if "confidence" in field]
            overall_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        # Determine if human review is needed
        requires_review = not mock_confidence_service.is_confident(overall_confidence)
        
        # Identify low confidence fields
        low_confidence_fields = [
            field_name for field_name, field in fields.items()
            if "confidence" in field and not mock_confidence_service.is_confident(field["confidence"])
        ]
        
        # Generate a unique document ID
        document_id = f"doc-{document_type}-{uuid.uuid4().hex[:8]}"
        
        # Return the processing result
        return {
            "document_id": document_id,
            "document_type": doc_classification,
            "extraction_results": {
                "text": ocr_result.get("text", ""),
                "fields": fields,
                "tables": ocr_result.get("table", None)
            },
            "overall_confidence": overall_confidence,
            "processing_time": ocr_result.get("processing_time", 1.0),
            "requires_review": requires_review,
            "low_confidence_fields": low_confidence_fields
        }
    
    mock_pipeline.process_document.side_effect = mock_process_document
    
    # Apply patch and yield the mock
    with patch("src.services.document_processing_pipeline.process_document", side_effect=mock_process_document):
        yield mock_pipeline


@pytest.fixture
def mock_message_handler(mock_document_processing_pipeline, mock_queue_service, mock_storage_service):
    """Creates a mock message handler for testing message processing."""
    mock_handler = MagicMock()
    
    # Message processing results for testing
    processing_results = []
    
    # Mock handle_message method
    def mock_handle_message(message, correlation_id=None):
        # Parse message and process document
        try:
            if isinstance(message, str):
                message_data = json.loads(message)
            else:
                message_data = message
            
            document_id = message_data.get("document_id", f"doc-{uuid.uuid4().hex[:8]}")
            document_type = message_data.get("document_type", "typed")
            document_path = message_data.get("document_path", "/tmp/sample.pdf")
            
            # Create a temporary file for testing if the document path doesn't exist
            if not os.path.exists(document_path):
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                    temp_file.write(b"Sample document content")
                    document_path = temp_file.name
            
            # Process the document
            result = mock_document_processing_pipeline.process_document(document_path, document_type)
            
            # Add document_id from the message
            result["document_id"] = document_id
            
            # Store result for testing
            processing_results.append(result)
            
            # Publish result to the output queue
            mock_queue_service.publish(
                "mca.documents",
                "data.processing",
                {
                    "document_id": document_id,
                    "extraction_results": result["extraction_results"],
                    "confidence": result["overall_confidence"],
                    "requires_review": result["requires_review"]
                },
                correlation_id
            )
            
            return result
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            # Store error for testing
            processing_results.append({"error": str(e)})
            raise
    
    mock_handler.handle_message.side_effect = mock_handle_message
    mock_handler.processing_results = processing_results
    
    # Apply patch and yield the mock
    with patch("src.services.message_handler.handle_message", side_effect=mock_handle_message):
        yield mock_handler


# ===== Helper Functions =====

@pytest.fixture
def verify_ocr_result():
    """Provides a function to verify OCR results against expected values."""
    def _verify_ocr_result(result, expected):
        """Verify that OCR result matches expected values.
        
        Args:
            result: The OCR result to verify
            expected: The expected values
            
        Returns:
            bool: True if the result matches the expected values, False otherwise
        """
        # Check document type
        if "document_type" in expected and result.get("document_type") != expected["document_type"]:
            logger.error(f"Document type mismatch: {result.get('document_type')} != {expected['document_type']}")
            return False
        
        # Check fields
        if "expected_fields" in expected:
            for field_name, expected_field in expected["expected_fields"].items():
                # Check if field exists in result
                if "fields" not in result.get("extraction_results", {}):
                    logger.error(f"No fields in extraction results")
                    return False
                
                if field_name not in result["extraction_results"]["fields"]:
                    logger.error(f"Field {field_name} not found in result")
                    return False
                
                # Check field value
                result_field = result["extraction_results"]["fields"][field_name]
                if result_field.get("value") != expected_field["value"]:
                    logger.error(f"Field {field_name} value mismatch: {result_field.get('value')} != {expected_field['value']}")
                    return False
                
                # Check confidence (with tolerance)
                if abs(result_field.get("confidence", 0) - expected_field.get("confidence", 0)) > 0.1:
                    logger.error(f"Field {field_name} confidence mismatch: {result_field.get('confidence')} != {expected_field.get('confidence')}")
                    return False
        
        # Check table
        if "expected_table" in expected:
            if "tables" not in result.get("extraction_results", {}) and "table" not in result.get("extraction_results", {}):
                logger.error(f"No table in extraction results")
                return False
            
            # Get the table from the result (handle both formats)
            result_table = result["extraction_results"].get("table", result["extraction_results"].get("tables", [{}])[0])
            
            # Check headers
            if "headers" in expected["expected_table"]:
                if "headers" not in result_table:
                    logger.error(f"No headers in result table")
                    return False
                
                if result_table["headers"] != expected["expected_table"]["headers"]:
                    logger.error(f"Table headers mismatch: {result_table['headers']} != {expected['expected_table']['headers']}")
                    return False
            
            # Check rows
            if "rows" in expected["expected_table"]:
                if "rows" not in result_table and "data" not in result_table:
                    logger.error(f"No rows in result table")
                    return False
                
                result_rows = result_table.get("rows", result_table.get("data", []))
                expected_rows = expected["expected_table"]["rows"]
                
                if len(result_rows) != len(expected_rows):
                    logger.error(f"Table row count mismatch: {len(result_rows)} != {len(expected_rows)}")
                    return False
                
                for i, (result_row, expected_row) in enumerate(zip(result_rows, expected_rows)):
                    if result_row != expected_row:
                        logger.error(f"Table row {i} mismatch: {result_row} != {expected_row}")
                        return False
            
            # Check confidence (with tolerance)
            if "confidence" in expected["expected_table"]:
                if abs(result_table.get("confidence", 0) - expected["expected_table"].get("confidence", 0)) > 0.1:
                    logger.error(f"Table confidence mismatch: {result_table.get('confidence')} != {expected['expected_table'].get('confidence')}")
                    return False
        
        return True
    
    return _verify_ocr_result


@pytest.fixture
def wait_for_message():
    """Provides a function to wait for a message to be published to a queue."""
    def _wait_for_message(queue_service, exchange, routing_key, timeout=5, check_interval=0.1):
        """Wait for a message to be published to a queue.
        
        Args:
            queue_service: The queue service to check
            exchange: The exchange to check
            routing_key: The routing key to check
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            
        Returns:
            dict: The message if found, None otherwise
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if a message has been published
            for message in queue_service.message_storage:
                if message["exchange"] == exchange and message["routing_key"] == routing_key:
                    return message
            
            # Wait before checking again
            time.sleep(check_interval)
        
        # Timeout reached without finding a message
        return None
    
    return _wait_for_message


@pytest.fixture
def setup_test_document(create_test_document, mock_storage_service):
    """Provides a function to set up a test document in S3 storage."""
    def _setup_test_document(document_type="typed", content=None, metadata=None):
        """Set up a test document in S3 storage.
        
        Args:
            document_type: The type of document to create
            content: The content of the document
            metadata: Metadata to attach to the document
            
        Returns:
            dict: Information about the created document
        """
        # Create default content based on document type
        if content is None:
            if document_type == "typed":
                content = "ABC Corporation\n12-3456789\n123 Main St, Anytown, USA"
            elif document_type == "handwritten":
                content = "John Smith\nJohn Smith\n2023-01-15"
            elif document_type == "mixed":
                content = "XYZ Industries\n98-7654321\nJane Doe"
            elif document_type == "table":
                content = "Date Description Amount\n2023-01-01 Opening Balance $10,000.00\n2023-01-15 Invoice #12345 $5,250.75\n2023-01-31 Closing Balance $15,250.75"
            else:
                content = f"Sample {document_type} document"
        
        # Create default metadata
        if metadata is None:
            metadata = {
                "document_type": document_type,
                "upload_time": datetime.utcnow().isoformat(),
                "content_type": "application/pdf"
            }
        
        # Create the document
        document_path = create_test_document(document_type, content)
        
        # Generate a key for S3 storage
        document_id = f"doc-{document_type}-{uuid.uuid4().hex[:8]}"
        key = f"documents/{document_id}.pdf"
        
        # Upload to S3
        upload_result = mock_storage_service.upload(document_path, key, metadata)
        
        return {
            "document_id": document_id,
            "document_path": document_path,
            "document_type": document_type,
            "key": key,
            "metadata": metadata,
            "content": content
        }
    
    return _setup_test_document


@pytest.fixture
def setup_ocr_pipeline(
    mock_ocr_service,
    mock_field_extraction_service,
    mock_confidence_service,
    mock_storage_service,
    mock_queue_service,
    mock_document_processing_pipeline,
    mock_message_handler
):
    """Sets up the complete OCR pipeline for integration testing."""
    # This fixture doesn't need to do anything special since all the mocks
    # are already set up by their respective fixtures. It just serves as a
    # convenient way to ensure all the necessary mocks are in place.
    return {
        "ocr_service": mock_ocr_service,
        "field_extraction_service": mock_field_extraction_service,
        "confidence_service": mock_confidence_service,
        "storage_service": mock_storage_service,
        "queue_service": mock_queue_service,
        "document_processing_pipeline": mock_document_processing_pipeline,
        "message_handler": mock_message_handler
    }