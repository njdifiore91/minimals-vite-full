import os
import json
import pytest
import tempfile
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Mock imports to avoid requiring actual dependencies in test environment
pytest.importorskip("tensorflow")
pytest.importorskip("boto3")
pytest.importorskip("pika")

# Constants for test configuration
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TYPED_DOCS_DIR = TEST_DATA_DIR / "typed_documents"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MIXED_DOCS_DIR = TEST_DATA_DIR / "mixed_documents"
TABLES_DIR = TEST_DATA_DIR / "tables"


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


# ===== Storage Fixtures =====

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
                f.write(storage_dict[Key])
        else:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": f"The specified key {Key} does not exist."}}, "GetObject")
    
    # Mock upload_file method
    def mock_upload_file(Filename, Bucket, Key, ExtraArgs=None):
        with open(Filename, 'rb') as f:
            storage_dict[Key] = f.read()
        return {"ETag": "mock-etag"}
    
    # Mock get_object method
    def mock_get_object(Bucket, Key):
        if Key in storage_dict:
            from io import BytesIO
            return {"Body": BytesIO(storage_dict[Key]), "ContentLength": len(storage_dict[Key])}
        else:
            from botocore.exceptions import ClientError
            raise ClientError({"Error": {"Code": "NoSuchKey", "Message": f"The specified key {Key} does not exist."}}, "GetObject")
    
    # Assign mock methods
    mock_client.download_file.side_effect = mock_download_file
    mock_client.upload_file.side_effect = mock_upload_file
    mock_client.get_object.side_effect = mock_get_object
    
    return mock_client


@pytest.fixture
def mock_s3_resource(mock_s3_client):
    """Creates a mock S3 resource for testing document storage operations."""
    mock_resource = MagicMock()
    mock_bucket = MagicMock()
    mock_object = MagicMock()
    
    # Link the mock client to the resource
    mock_resource.meta.client = mock_s3_client
    mock_resource.Bucket.return_value = mock_bucket
    mock_bucket.Object.return_value = mock_object
    
    return mock_resource


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
            "body": body,
            "properties": properties
        })
    
    # Mock basic_consume method
    def mock_basic_consume(queue, on_message_callback, auto_ack=False):
        # Store the callback for later use
        mock_channel._on_message_callback = on_message_callback
        return "mock-consumer-tag"
    
    # Method to simulate message receipt for testing
    def simulate_message_received(body, delivery_tag="mock-tag"):
        mock_method = MagicMock()
        mock_method.delivery_tag = delivery_tag
        mock_properties = MagicMock()
        mock_channel._on_message_callback(mock_channel, mock_method, mock_properties, body)
    
    # Assign mock methods
    mock_channel.basic_publish.side_effect = mock_basic_publish
    mock_channel.basic_consume.side_effect = mock_basic_consume
    mock_channel.simulate_message_received = simulate_message_received
    mock_channel.message_storage = message_storage
    
    return mock_connection


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """Returns the mock RabbitMQ channel from the mock connection."""
    return mock_rabbitmq_connection.channel()


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
    return mock_session


@pytest.fixture
def mock_tensorflow_gpu():
    """Mocks TensorFlow GPU configuration for testing."""
    mock_gpu_options = MagicMock()
    mock_gpu_options.per_process_gpu_memory_fraction = 0.5
    mock_gpu_options.allow_growth = True
    
    mock_config = MagicMock()
    mock_config.gpu_options = mock_gpu_options
    
    return mock_config


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
    return mock_model


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
def mock_ocr_service():
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
    return mock_service


@pytest.fixture
def mock_queue_service():
    """Creates a mock queue service for testing message operations."""
    mock_service = MagicMock()
    
    # Message storage for testing
    message_storage = []
    
    # Mock publish method
    def mock_publish(exchange, routing_key, message):
        message_storage.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "message": message
        })
        return True
    
    # Mock consume method
    def mock_consume(queue, callback):
        # Store the callback for later use
        mock_service._callback = callback
        return "mock-consumer-tag"
    
    # Method to simulate message receipt for testing
    def simulate_message_received(message):
        mock_service._callback(message)
    
    # Assign mock methods
    mock_service.publish.side_effect = mock_publish
    mock_service.consume.side_effect = mock_consume
    mock_service.simulate_message_received = simulate_message_received
    mock_service.message_storage = message_storage
    
    return mock_service


@pytest.fixture
def mock_storage_service():
    """Creates a mock storage service for testing document storage operations."""
    mock_service = MagicMock()
    
    # Storage dictionary for testing
    storage_dict = {}
    
    # Mock upload method
    def mock_upload(file_path, key, metadata=None):
        with open(file_path, 'rb') as f:
            storage_dict[key] = {
                "content": f.read(),
                "metadata": metadata or {}
            }
        return {
            "key": key,
            "size": len(storage_dict[key]["content"]),
            "metadata": metadata or {}
        }
    
    # Mock download method
    def mock_download(key, destination_path):
        if key in storage_dict:
            with open(destination_path, 'wb') as f:
                f.write(storage_dict[key]["content"])
            return {
                "key": key,
                "size": len(storage_dict[key]["content"]),
                "metadata": storage_dict[key]["metadata"]
            }
        else:
            raise FileNotFoundError(f"Key {key} not found in storage")
    
    # Mock get_metadata method
    def mock_get_metadata(key):
        if key in storage_dict:
            return storage_dict[key]["metadata"]
        else:
            raise FileNotFoundError(f"Key {key} not found in storage")
    
    # Assign mock methods
    mock_service.upload.side_effect = mock_upload
    mock_service.download.side_effect = mock_download
    mock_service.get_metadata.side_effect = mock_get_metadata
    mock_service.storage_dict = storage_dict
    
    return mock_service


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
    
    return mock_service


# ===== Integration Fixtures =====

@pytest.fixture
def mock_document_processing_pipeline():
    """Creates a mock document processing pipeline for integration testing."""
    mock_pipeline = MagicMock()
    
    # Mock process_document method
    def mock_process_document(document_path, document_type=None):
        # Auto-detect document type if not provided
        if document_type is None:
            if "typed" in document_path:
                document_type = "typed"
            elif "handwritten" in document_path:
                document_type = "handwritten"
            elif "mixed" in document_path:
                document_type = "mixed"
            elif "table" in document_path:
                document_type = "table"
            else:
                document_type = "typed"  # Default
        
        # Return different results based on document type
        if document_type == "typed":
            return {
                "document_id": "doc-typed-123",
                "document_type": "application_form",
                "extraction_results": {
                    "text": "ABC Corporation\n12-3456789\n123 Main St, Anytown, USA",
                    "fields": {
                        "business_name": {"value": "ABC Corporation", "confidence": 0.98},
                        "tax_id": {"value": "12-3456789", "confidence": 0.97},
                        "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.95}
                    }
                },
                "overall_confidence": 0.97,
                "processing_time": 0.75,
                "requires_review": False
            }
        elif document_type == "handwritten":
            return {
                "document_id": "doc-handwritten-456",
                "document_type": "application_form",
                "extraction_results": {
                    "text": "John Smith\nJohn Smith\n2023-01-15",
                    "fields": {
                        "owner_name": {"value": "John Smith", "confidence": 0.85},
                        "signature": {"value": "John Smith", "confidence": 0.80},
                        "date": {"value": "2023-01-15", "confidence": 0.82}
                    }
                },
                "overall_confidence": 0.82,
                "processing_time": 1.25,
                "requires_review": False
            }
        elif document_type == "mixed":
            return {
                "document_id": "doc-mixed-789",
                "document_type": "application_form",
                "extraction_results": {
                    "text": "XYZ Industries\n98-7654321\nJane Doe",
                    "fields": {
                        "business_name": {"value": "XYZ Industries", "confidence": 0.96},
                        "tax_id": {"value": "98-7654321", "confidence": 0.95},
                        "owner_signature": {"value": "Jane Doe", "confidence": 0.82}
                    }
                },
                "overall_confidence": 0.91,
                "processing_time": 1.5,
                "requires_review": False
            }
        elif document_type == "table":
            return {
                "document_id": "doc-table-101",
                "document_type": "financial_statement",
                "extraction_results": {
                    "text": "Date Description Amount\n2023-01-01 Opening Balance $10,000.00\n2023-01-15 Invoice #12345 $5,250.75\n2023-01-31 Closing Balance $15,250.75",
                    "table": {
                        "headers": ["Date", "Description", "Amount"],
                        "rows": [
                            ["2023-01-01", "Opening Balance", "$10,000.00"],
                            ["2023-01-15", "Invoice #12345", "$5,250.75"],
                            ["2023-01-31", "Closing Balance", "$15,250.75"]
                        ]
                    }
                },
                "overall_confidence": 0.94,
                "processing_time": 2.0,
                "requires_review": False
            }
        else:
            return {
                "document_id": "doc-unknown-999",
                "document_type": "unknown",
                "extraction_results": {
                    "text": "Unknown document type",
                    "fields": {}
                },
                "overall_confidence": 0.5,
                "processing_time": 1.0,
                "requires_review": True
            }
    
    mock_pipeline.process_document.side_effect = mock_process_document
    return mock_pipeline


@pytest.fixture
def mock_message_handler():
    """Creates a mock message handler for testing message processing."""
    mock_handler = MagicMock()
    
    # Message processing results for testing
    processing_results = []
    
    # Mock handle_message method
    def mock_handle_message(message):
        # Parse message and process document
        try:
            if isinstance(message, str):
                message_data = json.loads(message)
            else:
                message_data = message
            
            document_id = message_data.get("document_id", "unknown-doc")
            document_type = message_data.get("document_type", "typed")
            document_path = message_data.get("document_path", "/tmp/sample.pdf")
            
            # Simulate document processing
            result = {
                "document_id": document_id,
                "document_type": document_type,
                "extraction_results": {
                    "fields": {
                        "field1": {"value": "Sample Value 1", "confidence": 0.95},
                        "field2": {"value": "Sample Value 2", "confidence": 0.92}
                    }
                },
                "overall_confidence": 0.93,
                "processing_time": 1.2,
                "requires_review": False
            }
            
            # Store result for testing
            processing_results.append(result)
            
            return result
        except Exception as e:
            # Store error for testing
            processing_results.append({"error": str(e)})
            raise
    
    mock_handler.handle_message.side_effect = mock_handle_message
    mock_handler.processing_results = processing_results
    
    return mock_handler