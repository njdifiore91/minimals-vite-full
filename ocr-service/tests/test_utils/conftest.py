"""Pytest fixtures and configuration for testing the utils package.

This module provides common test data, mocks, and setup/teardown functionality
to support all utility module tests in the OCR service.
"""

import os
import tempfile
import json
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import boto3
import numpy as np
import tensorflow as tf
from moto import mock_s3
from PIL import Image

# Constants for test configuration
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
TEST_BUCKET_NAME = "mca-documents-testing"
TEST_DOCUMENT_TYPES = ["invoice", "bank_statement", "id_document", "business_license"]


# ===== Environment Setup Fixtures =====

@pytest.fixture(scope="session")
def test_env_setup():
    """Set up test environment variables for the test session."""
    # Store original environment variables
    original_env = {}
    test_env_vars = {
        "OCR_SERVICE_ENV": "test",
        "S3_ENDPOINT_URL": "http://localhost:4566",
        "S3_BUCKET_NAME": TEST_BUCKET_NAME,
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "guest",
        "RABBITMQ_PASSWORD": "guest",
        "RABBITMQ_EXCHANGE": "mca.documents.test",
        "RABBITMQ_QUEUE": "data-extraction-test",
        "TF_FORCE_GPU_ALLOW_GROWTH": "true",
        "TF_CPP_MIN_LOG_LEVEL": "3",  # Suppress TensorFlow logging
    }
    
    # Save original environment variables and set test ones
    for key, value in test_env_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
    
    yield
    
    # Restore original environment variables
    for key in test_env_vars.keys():
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]


@pytest.fixture(scope="session")
def test_config(test_env_setup):
    """Create a test configuration object."""
    return {
        "environment": "test",
        "service_name": "ocr-service",
        "log_level": "DEBUG",
        "s3": {
            "bucket_name": TEST_BUCKET_NAME,
            "endpoint_url": os.environ.get("S3_ENDPOINT_URL"),
            "region_name": "us-east-1"
        },
        "rabbitmq": {
            "host": os.environ.get("RABBITMQ_HOST"),
            "port": int(os.environ.get("RABBITMQ_PORT")),
            "username": os.environ.get("RABBITMQ_USERNAME"),
            "password": os.environ.get("RABBITMQ_PASSWORD"),
            "exchange": os.environ.get("RABBITMQ_EXCHANGE"),
            "queue": os.environ.get("RABBITMQ_QUEUE")
        },
        "tensorflow": {
            "model_path": str(TEST_DATA_DIR / "models"),
            "confidence_threshold": 0.75,
            "use_gpu": False
        }
    }


# ===== File and Directory Fixtures =====

@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        file_path = Path(tmp_file.name)
        yield file_path
        # Clean up the file after the test
        if file_path.exists():
            file_path.unlink()


@pytest.fixture
def sample_image_file(temp_dir):
    """Create a sample image file for testing OCR."""
    # Create a simple image with text for OCR testing
    img_path = temp_dir / "sample_text.png"
    img = Image.new('RGB', (300, 100), color='white')
    # We're not actually creating text here as PIL doesn't have simple text rendering
    # In a real implementation, you might want to use PIL.ImageDraw to add text
    img.save(str(img_path))
    return img_path


@pytest.fixture
def sample_pdf_file(temp_dir):
    """Create a path for a sample PDF file (mock)."""
    # In a real implementation, you might want to create an actual PDF
    # For testing purposes, we'll just create a mock file path
    pdf_path = temp_dir / "sample_document.pdf"
    # Create an empty file
    pdf_path.touch()
    return pdf_path


@pytest.fixture
def sample_json_data():
    """Create sample JSON data for testing."""
    return {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "extracted_fields": {
            "invoice_number": {
                "value": "INV-001",
                "confidence": 0.95
            },
            "date": {
                "value": "2025-05-23",
                "confidence": 0.92
            },
            "total_amount": {
                "value": "1250.00",
                "confidence": 0.88
            },
            "vendor_name": {
                "value": "ABC Corporation",
                "confidence": 0.85
            }
        },
        "processing_time": 1.25,
        "timestamp": "2025-05-23T10:15:30Z"
    }


@pytest.fixture
def sample_json_file(temp_dir, sample_json_data):
    """Create a sample JSON file with test data."""
    json_path = temp_dir / "sample_data.json"
    with open(json_path, 'w') as f:
        json.dump(sample_json_data, f)
    return json_path


# ===== S3 Mock Fixtures =====

@pytest.fixture
def aws_credentials():
    """Mock AWS credentials for testing."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


@pytest.fixture
def s3_mock(aws_credentials):
    """Create a mocked S3 service using moto."""
    with mock_s3():
        # Create the test bucket
        s3_client = boto3.client("s3", region_name="us-east-1")
        s3_client.create_bucket(Bucket=TEST_BUCKET_NAME)
        yield s3_client


@pytest.fixture
def s3_resource(aws_credentials):
    """Create a mocked S3 resource using moto."""
    with mock_s3():
        # Create the test bucket
        s3 = boto3.resource("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=TEST_BUCKET_NAME)
        yield s3


@pytest.fixture
def s3_bucket_with_files(s3_resource, sample_image_file, sample_pdf_file, sample_json_file):
    """Set up an S3 bucket with sample files for testing."""
    bucket = s3_resource.Bucket(TEST_BUCKET_NAME)
    
    # Upload sample files to the bucket
    bucket.upload_file(
        str(sample_image_file),
        f"documents/images/{sample_image_file.name}"
    )
    bucket.upload_file(
        str(sample_pdf_file),
        f"documents/pdfs/{sample_pdf_file.name}"
    )
    bucket.upload_file(
        str(sample_json_file),
        f"results/{sample_json_file.name}"
    )
    
    return bucket


# ===== RabbitMQ Mock Fixtures =====

@pytest.fixture
def rabbitmq_connection_mock():
    """Mock RabbitMQ connection for testing."""
    with patch("pika.BlockingConnection") as mock_connection:
        # Create mock channel
        mock_channel = MagicMock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        # Mock basic methods
        mock_channel.exchange_declare = MagicMock()
        mock_channel.queue_declare = MagicMock(return_value=MagicMock(method=MagicMock(queue="test-queue")))
        mock_channel.queue_bind = MagicMock()
        mock_channel.basic_publish = MagicMock()
        mock_channel.basic_consume = MagicMock()
        mock_channel.start_consuming = MagicMock()
        mock_channel.basic_ack = MagicMock()
        
        yield mock_connection


@pytest.fixture
def rabbitmq_channel_mock(rabbitmq_connection_mock):
    """Mock RabbitMQ channel for testing."""
    return rabbitmq_connection_mock.return_value.channel.return_value


@pytest.fixture
def rabbitmq_message_mock():
    """Create a mock RabbitMQ message for testing."""
    mock_method = MagicMock()
    mock_method.delivery_tag = "test-tag"
    
    mock_properties = MagicMock()
    mock_properties.correlation_id = "test-correlation-id"
    
    message_body = json.dumps({
        "document_id": "doc-12345",
        "document_type": "invoice",
        "s3_path": f"s3://{TEST_BUCKET_NAME}/documents/pdfs/sample_document.pdf",
        "request_id": "req-67890"
    }).encode('utf-8')
    
    return mock_method, mock_properties, message_body


# ===== TensorFlow Mock Fixtures =====

@pytest.fixture
def tf_model_mock():
    """Mock TensorFlow model for testing OCR without requiring GPU."""
    with patch("tensorflow.keras.models.load_model") as mock_load_model:
        # Create a mock model that returns predictable outputs
        mock_model = MagicMock()
        
        # Mock predict method to return a simple prediction
        def mock_predict(images, **kwargs):
            # Return a simple prediction array based on input shape
            if isinstance(images, np.ndarray):
                batch_size = images.shape[0]
                # For text recognition, return character probabilities
                # This is a simplified mock - real models would return more complex outputs
                return np.random.rand(batch_size, 50, 94)  # 94 characters in charset
            return np.random.rand(1, 50, 94)
        
        mock_model.predict = MagicMock(side_effect=mock_predict)
        mock_load_model.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def tf_session_mock():
    """Mock TensorFlow session for testing."""
    with patch("tensorflow.compat.v1.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance
        mock_session_instance.__enter__.return_value = mock_session_instance
        
        # Mock run method to return predictable outputs
        def mock_run(fetches, feed_dict=None):
            # Return simple outputs based on the fetches
            if isinstance(fetches, list):
                return [np.random.rand(1, 10) for _ in fetches]
            return np.random.rand(1, 10)
        
        mock_session_instance.run = MagicMock(side_effect=mock_run)
        
        yield mock_session_instance


@pytest.fixture
def disable_gpu():
    """Disable GPU usage for TensorFlow tests."""
    original_visible_devices = os.environ.get("CUDA_VISIBLE_DEVICES", None)
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # Disable GPU
    
    # Configure TensorFlow to use CPU
    tf_config = tf.compat.v1.ConfigProto(device_count={'GPU': 0})
    sess = tf.compat.v1.Session(config=tf_config)
    tf.compat.v1.keras.backend.set_session(sess)
    
    yield
    
    # Restore original setting
    if original_visible_devices is not None:
        os.environ["CUDA_VISIBLE_DEVICES"] = original_visible_devices
    else:
        del os.environ["CUDA_VISIBLE_DEVICES"]


# ===== Logging Fixtures =====

@pytest.fixture
def mock_logger():
    """Mock logger for testing logging utilities."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_logger_instance = MagicMock()
        mock_get_logger.return_value = mock_logger_instance
        
        # Mock logging methods
        mock_logger_instance.debug = MagicMock()
        mock_logger_instance.info = MagicMock()
        mock_logger_instance.warning = MagicMock()
        mock_logger_instance.error = MagicMock()
        mock_logger_instance.critical = MagicMock()
        
        yield mock_logger_instance


# ===== Error Handling Fixtures =====

@pytest.fixture
def sample_exceptions():
    """Provide sample exceptions for error handling testing."""
    return {
        "validation": ValueError("Invalid document format"),
        "connection": ConnectionError("Failed to connect to S3"),
        "processing": RuntimeError("Failed to process document"),
        "not_found": FileNotFoundError("Document not found"),
        "permission": PermissionError("No permission to access document")
    }


# ===== Document Processing Fixtures =====

@pytest.fixture
def sample_document_metadata():
    """Create sample document metadata for testing."""
    return {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "filename": "invoice_abc_corp.pdf",
        "upload_timestamp": "2025-05-23T10:15:30Z",
        "size_bytes": 1024567,
        "mime_type": "application/pdf",
        "pages": 3,
        "status": "pending_extraction"
    }


@pytest.fixture
def sample_extraction_result():
    """Create sample extraction result for testing."""
    return {
        "document_id": "doc-12345",
        "status": "completed",
        "extracted_fields": {
            "invoice_number": {
                "value": "INV-001",
                "confidence": 0.95,
                "bounding_box": [100, 100, 200, 120]
            },
            "date": {
                "value": "2025-05-23",
                "confidence": 0.92,
                "bounding_box": [300, 100, 400, 120]
            },
            "total_amount": {
                "value": "1250.00",
                "confidence": 0.88,
                "bounding_box": [500, 400, 600, 420]
            }
        },
        "processing_time_seconds": 1.25,
        "completion_timestamp": "2025-05-23T10:15:35Z"
    }