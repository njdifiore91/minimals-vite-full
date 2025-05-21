#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest fixtures and configuration for testing the utils package.

This module provides fixtures specifically designed for testing utility functions,
including mocks for external dependencies, test data generators, and environment setup.
It complements the main conftest.py in the parent directory while providing more
specialized fixtures for utility testing.
"""

import json
import os
import pytest
import tempfile
import logging
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Generator, Tuple, Optional, Callable

# Import for AWS mocking
from moto import mock_s3

# Import for RabbitMQ mocking
import pika

# Import for TensorFlow mocking
import numpy as np
import tensorflow as tf

# Constants for testing
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
TYPED_DOCS_DIR = TEST_DATA_DIR / "typed_documents"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MIXED_DOCS_DIR = TEST_DATA_DIR / "mixed_documents"
IMAGES_DIR = TEST_DATA_DIR / "images"
TABLES_DIR = TEST_DATA_DIR / "tables"
FORMS_DIR = TEST_DATA_DIR / "forms"

# Test bucket name for S3 testing
TEST_BUCKET_NAME = "mca-documents-test"

# Test exchange and queue names for RabbitMQ testing
TEST_EXCHANGE_NAME = "mca.documents.test"
TEST_QUEUE_NAME = "data-extraction-test"
TEST_ROUTING_KEY = "ocr.test"


# ===== Utility-Specific Test Fixtures =====

@pytest.fixture
def utils_logger() -> logging.Logger:
    """Provides a logger configured for testing utility functions."""
    logger = logging.getLogger("ocr-service-utils-test")
    logger.setLevel(logging.DEBUG)
    
    # Create a console handler for test output
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    
    # Add the handler to the logger
    logger.addHandler(console_handler)
    
    return logger


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Creates a temporary directory for testing file operations."""
    temp_path = Path(tempfile.mkdtemp(prefix="ocr_utils_test_"))
    yield temp_path
    
    # Cleanup after test
    if temp_path.exists():
        shutil.rmtree(temp_path)


@pytest.fixture
def sample_files(temp_dir) -> Dict[str, Path]:
    """Creates a set of sample files with different formats for testing."""
    files = {}
    
    # Create a PDF file
    pdf_path = temp_dir / "sample.pdf"
    with open(pdf_path, "wb") as f:
        f.write(b"%PDF-1.5\nSample PDF content for testing\n%%EOF")
    files["pdf"] = pdf_path
    
    # Create a TIFF file
    tiff_path = temp_dir / "sample.tiff"
    with open(tiff_path, "wb") as f:
        f.write(b"II*\0\x08\0\0\0\x10\0\0\1\x03\0\0\0\x01\0\0\0\x01")
    files["tiff"] = tiff_path
    
    # Create a PNG file
    png_path = temp_dir / "sample.png"
    with open(png_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    files["png"] = png_path
    
    # Create a JPEG file
    jpeg_path = temp_dir / "sample.jpg"
    with open(jpeg_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01" + b"\x00" * 100)
    files["jpeg"] = jpeg_path
    
    # Create a text file
    text_path = temp_dir / "sample.txt"
    with open(text_path, "w") as f:
        f.write("Sample text content for testing")
    files["text"] = text_path
    
    # Create a JSON file
    json_path = temp_dir / "sample.json"
    with open(json_path, "w") as f:
        json.dump({"key": "value", "nested": {"data": [1, 2, 3]}}, f)
    files["json"] = json_path
    
    # Create an empty file
    empty_path = temp_dir / "empty.txt"
    empty_path.touch()
    files["empty"] = empty_path
    
    return files


@pytest.fixture
def binary_content() -> Dict[str, bytes]:
    """Provides sample binary content for different file types."""
    return {
        "pdf": b"%PDF-1.5\nSample PDF content for testing\n%%EOF",
        "tiff": b"II*\0\x08\0\0\0\x10\0\0\1\x03\0\0\0\x01\0\0\0\x01",
        "png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 100,
        "jpeg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01" + b"\x00" * 100,
        "empty": b""
    }


@pytest.fixture
def text_content() -> Dict[str, str]:
    """Provides sample text content for different scenarios."""
    return {
        "plain": "Sample text content for testing",
        "with_numbers": "Sample text with numbers: 123-456-7890",
        "with_dates": "Date: 2023-01-15 and another date: 01/15/2023",
        "with_currency": "Price: $1,234.56 and another price: €789.10",
        "with_special_chars": "Special characters: !@#$%^&*()_+-=[]{}|;':,.<>?/\\",
        "multiline": "Line 1\nLine 2\nLine 3\nLine 4\nLine 5",
        "json_string": '{"key": "value", "nested": {"data": [1, 2, 3]}}',
        "empty": ""
    }


@pytest.fixture
def sample_timestamps() -> Dict[str, str]:
    """Provides sample timestamps in different formats for testing."""
    return {
        "iso8601": "2023-01-15T14:30:45Z",
        "iso8601_with_ms": "2023-01-15T14:30:45.123Z",
        "iso8601_with_timezone": "2023-01-15T14:30:45+02:00",
        "rfc2822": "Sun, 15 Jan 2023 14:30:45 +0000",
        "unix_timestamp": "1673792445",
        "date_only": "2023-01-15",
        "time_only": "14:30:45",
        "custom_format": "15/01/2023 14:30:45",
        "invalid": "not-a-timestamp"
    }


@pytest.fixture
def sample_errors() -> Dict[str, Exception]:
    """Provides sample exceptions for testing error handling."""
    return {
        "value_error": ValueError("Invalid value"),
        "type_error": TypeError("Invalid type"),
        "key_error": KeyError("Missing key"),
        "file_not_found": FileNotFoundError("File not found"),
        "permission_error": PermissionError("Permission denied"),
        "connection_error": ConnectionError("Connection failed"),
        "timeout_error": TimeoutError("Operation timed out"),
        "os_error": OSError("Operating system error"),
        "io_error": IOError("Input/output error"),
        "runtime_error": RuntimeError("Runtime error")
    }


# ===== S3 Utility Testing Fixtures =====

@pytest.fixture
def s3_mock():
    """Provides a mocked S3 environment using moto."""
    with mock_s3():
        import boto3
        s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test',
            endpoint_url='http://localhost:4566'
        )
        
        # Create test bucket
        s3_client.create_bucket(Bucket=TEST_BUCKET_NAME)
        
        yield s3_client


@pytest.fixture
def s3_test_files(s3_mock, binary_content) -> Dict[str, str]:
    """Uploads test files to the mock S3 bucket and returns their keys."""
    keys = {}
    
    # Upload each binary content type to S3
    for content_type, content in binary_content.items():
        key = f"test-files/{content_type}_sample.{content_type}"
        s3_mock.put_object(
            Bucket=TEST_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType=f"application/{content_type}"
        )
        keys[content_type] = key
    
    # Add a few more specific test files
    s3_mock.put_object(
        Bucket=TEST_BUCKET_NAME,
        Key="documents/application_123.pdf",
        Body=binary_content["pdf"],
        ContentType="application/pdf",
        Metadata={
            "document_id": "doc-123",
            "application_id": "app-456",
            "document_type": "application"
        }
    )
    keys["application"] = "documents/application_123.pdf"
    
    s3_mock.put_object(
        Bucket=TEST_BUCKET_NAME,
        Key="documents/bank_statement_789.pdf",
        Body=binary_content["pdf"],
        ContentType="application/pdf",
        Metadata={
            "document_id": "doc-789",
            "application_id": "app-456",
            "document_type": "bank_statement"
        }
    )
    keys["bank_statement"] = "documents/bank_statement_789.pdf"
    
    return keys


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Provides a mocked boto3 S3 client for testing without actual S3 access."""
    mock_client = MagicMock()
    
    # Configure common operations
    mock_client.get_object.return_value = {
        "Body": MagicMock(
            read=lambda: b"%PDF-1.5\nMock PDF content\n%%EOF"
        ),
        "ContentType": "application/pdf",
        "Metadata": {
            "document_id": "doc-123",
            "application_id": "app-456"
        }
    }
    
    mock_client.put_object.return_value = {
        "ETag": "\"mock-etag\"",
        "VersionId": "mock-version-id"
    }
    
    mock_client.list_objects_v2.return_value = {
        "Contents": [
            {"Key": "documents/doc1.pdf", "Size": 1234, "LastModified": "2023-01-15T14:30:45Z"},
            {"Key": "documents/doc2.pdf", "Size": 5678, "LastModified": "2023-01-16T10:20:30Z"}
        ],
        "KeyCount": 2,
        "MaxKeys": 1000,
        "IsTruncated": False
    }
    
    mock_client.generate_presigned_url.return_value = "https://example.com/presigned-url"
    
    return mock_client


# ===== RabbitMQ Utility Testing Fixtures =====

@pytest.fixture
def mock_rabbitmq_connection() -> MagicMock:
    """Provides a mocked RabbitMQ connection for testing."""
    mock_conn = MagicMock()
    mock_conn.is_open = True
    mock_conn.is_closed = False
    
    # Mock the channel creation
    mock_channel = MagicMock()
    mock_conn.channel.return_value = mock_channel
    
    # Configure the channel methods
    mock_channel.exchange_declare.return_value = None
    mock_channel.queue_declare.return_value = pika.frame.Method(
        1, pika.spec.Queue.DeclareOk(TEST_QUEUE_NAME, 0, 0)
    )
    mock_channel.queue_bind.return_value = None
    mock_channel.basic_publish.return_value = True
    mock_channel.basic_consume.return_value = "consumer_tag"
    mock_channel.basic_ack.return_value = None
    mock_channel.basic_nack.return_value = None
    
    return mock_conn


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection) -> MagicMock:
    """Provides a mocked RabbitMQ channel for testing."""
    return mock_rabbitmq_connection.channel()


@pytest.fixture
def mock_rabbitmq_message() -> MagicMock:
    """Provides a mocked RabbitMQ message for testing."""
    mock_method = MagicMock()
    mock_method.delivery_tag = "test-delivery-tag"
    
    mock_properties = MagicMock()
    mock_properties.message_id = "msg-123456"
    mock_properties.correlation_id = "corr-123456"
    mock_properties.timestamp = 1673792445
    mock_properties.content_type = "application/json"
    mock_properties.headers = {"source": "document-service", "priority": "high"}
    
    mock_body = json.dumps({
        "document_id": "doc-123456",
        "application_id": "app-789012",
        "storage_path": f"s3://{TEST_BUCKET_NAME}/documents/doc-123456.pdf",
        "document_type": "application",
        "priority": "high",
        "metadata": {
            "filename": "application.pdf",
            "content_type": "application/pdf",
            "size": 12345
        }
    }).encode('utf-8')
    
    return (mock_method, mock_properties, mock_body)


@pytest.fixture
def mock_pika_connection_parameters() -> MagicMock:
    """Provides mocked connection parameters for RabbitMQ."""
    mock_params = MagicMock(spec=pika.ConnectionParameters)
    mock_params.host = "localhost"
    mock_params.port = 5672
    mock_params.virtual_host = "/"
    mock_params.credentials = pika.PlainCredentials("guest", "guest")
    return mock_params


@pytest.fixture
def mock_pika_blocking_connection() -> MagicMock:
    """Provides a mocked pika BlockingConnection for testing."""
    with patch('pika.BlockingConnection') as mock_connection_class:
        mock_connection = MagicMock()
        mock_connection_class.return_value = mock_connection
        
        # Mock the channel
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        # Configure channel methods
        mock_channel.exchange_declare.return_value = None
        mock_channel.queue_declare.return_value = pika.frame.Method(
            1, pika.spec.Queue.DeclareOk(TEST_QUEUE_NAME, 0, 0)
        )
        mock_channel.queue_bind.return_value = None
        mock_channel.basic_publish.return_value = True
        
        yield mock_connection


# ===== Security Utility Testing Fixtures =====

@pytest.fixture
def encryption_key() -> bytes:
    """Provides a test encryption key for AES-256."""
    return b"\x01" * 32  # 32 bytes for AES-256


@pytest.fixture
def hmac_key() -> bytes:
    """Provides a test HMAC key."""
    return b"\x02" * 32


@pytest.fixture
def sensitive_data() -> Dict[str, Any]:
    """Provides sample sensitive data for encryption testing."""
    return {
        "plain_text": "This is sensitive information that should be encrypted",
        "structured_data": {
            "ssn": "123-45-6789",
            "credit_card": "4111-1111-1111-1111",
            "expiration": "12/25",
            "cvv": "123"
        },
        "binary_data": b"\x03\x04\x05\x06\x07\x08\x09\x0a"
    }


# ===== Retry Utility Testing Fixtures =====

@pytest.fixture
def mock_retriable_function() -> Tuple[MagicMock, Callable]:
    """Provides a mock function that can be configured to fail and succeed for retry testing."""
    mock_func = MagicMock()
    
    # Create a wrapper that can be configured to fail a certain number of times
    def configure_failures(num_failures: int, exception_type: Optional[Exception] = None):
        if exception_type is None:
            exception_type = ConnectionError("Simulated connection error")
            
        # Reset the mock
        mock_func.reset_mock()
        
        # Configure side effects
        side_effects = [exception_type] * num_failures + ["success"]
        mock_func.side_effect = side_effects
    
    return mock_func, configure_failures


@pytest.fixture
def mock_async_retriable_function() -> Tuple[MagicMock, Callable]:
    """Provides a mock async function that can be configured to fail and succeed for retry testing."""
    mock_func = MagicMock()
    
    # Create a wrapper that can be configured to fail a certain number of times
    def configure_failures(num_failures: int, exception_type: Optional[Exception] = None):
        if exception_type is None:
            exception_type = ConnectionError("Simulated connection error")
            
        # Reset the mock
        mock_func.reset_mock()
        
        # Configure side effects for async function
        async def async_side_effect(*args, **kwargs):
            side_effect = mock_func.side_effect.pop(0) if mock_func.side_effect else "success"
            if side_effect == "success":
                return "success"
            else:
                raise side_effect
                
        mock_func.side_effect = [exception_type] * num_failures + ["success"]
        mock_func.__call__ = async_side_effect
    
    return mock_func, configure_failures


# ===== Validation Utility Testing Fixtures =====

@pytest.fixture
def sample_document_types() -> Dict[str, Dict[str, Any]]:
    """Provides sample document types with validation rules."""
    return {
        "application": {
            "mime_types": ["application/pdf", "image/tiff", "image/jpeg", "image/png"],
            "max_size": 10 * 1024 * 1024,  # 10 MB
            "required_fields": ["name", "address", "phone"],
            "optional_fields": ["email", "business_name", "tax_id"],
            "validation_rules": {
                "name": {"type": "string", "min_length": 2, "max_length": 100},
                "address": {"type": "string", "min_length": 5, "max_length": 200},
                "phone": {"type": "string", "pattern": "^[0-9\-\+\(\)\s]{10,20}$"},
                "email": {"type": "string", "pattern": "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"},
                "business_name": {"type": "string", "min_length": 2, "max_length": 100},
                "tax_id": {"type": "string", "pattern": "^[0-9\-]{9,12}$"}
            }
        },
        "bank_statement": {
            "mime_types": ["application/pdf", "image/tiff"],
            "max_size": 20 * 1024 * 1024,  # 20 MB
            "required_fields": ["bank_name", "account_number", "statement_date", "balance"],
            "optional_fields": ["account_holder", "transactions"],
            "validation_rules": {
                "bank_name": {"type": "string", "min_length": 2, "max_length": 100},
                "account_number": {"type": "string", "pattern": "^[0-9\-\*]{4,20}$"},
                "statement_date": {"type": "string", "pattern": "^\d{4}-\d{2}-\d{2}$"},
                "balance": {"type": "number", "min": -1000000, "max": 1000000},
                "account_holder": {"type": "string", "min_length": 2, "max_length": 100},
                "transactions": {"type": "array", "min_items": 0, "max_items": 1000}
            }
        },
        "tax_return": {
            "mime_types": ["application/pdf"],
            "max_size": 15 * 1024 * 1024,  # 15 MB
            "required_fields": ["tax_year", "taxpayer_name", "taxpayer_id", "total_income"],
            "optional_fields": ["filing_status", "deductions", "tax_due"],
            "validation_rules": {
                "tax_year": {"type": "string", "pattern": "^\d{4}$"},
                "taxpayer_name": {"type": "string", "min_length": 2, "max_length": 100},
                "taxpayer_id": {"type": "string", "pattern": "^[0-9\-]{9,12}$"},
                "total_income": {"type": "number", "min": 0, "max": 10000000},
                "filing_status": {"type": "string", "enum": ["single", "married_joint", "married_separate", "head_of_household"]},
                "deductions": {"type": "number", "min": 0, "max": 1000000},
                "tax_due": {"type": "number", "min": -100000, "max": 1000000}
            }
        }
    }


@pytest.fixture
def sample_message_schemas() -> Dict[str, Dict[str, Any]]:
    """Provides sample message schemas for validation testing."""
    return {
        "document_request": {
            "type": "object",
            "required": ["document_id", "application_id", "storage_path", "document_type"],
            "properties": {
                "document_id": {"type": "string", "pattern": "^doc-[0-9a-f]{6,12}$"},
                "application_id": {"type": "string", "pattern": "^app-[0-9a-f]{6,12}$"},
                "storage_path": {"type": "string", "pattern": "^s3://[\w.-]+/[\w.-/]+$"},
                "document_type": {"type": "string", "enum": ["application", "bank_statement", "tax_return", "id_document", "pay_stub", "other"]},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content_type": {"type": "string"},
                        "size": {"type": "integer", "minimum": 0}
                    }
                }
            }
        },
        "extraction_result": {
            "type": "object",
            "required": ["document_id", "application_id", "document_type", "fields", "overall_confidence"],
            "properties": {
                "document_id": {"type": "string", "pattern": "^doc-[0-9a-f]{6,12}$"},
                "application_id": {"type": "string", "pattern": "^app-[0-9a-f]{6,12}$"},
                "document_type": {"type": "string", "enum": ["application", "bank_statement", "tax_return", "id_document", "pay_stub", "other"]},
                "fields": {"type": "object"},
                "overall_confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "requires_verification": {"type": "boolean"},
                "processing_time": {"type": "number", "minimum": 0},
                "extraction_timestamp": {"type": "string", "format": "date-time"},
                "model_version": {"type": "string"}
            }
        }
    }


# ===== Logging Utility Testing Fixtures =====

@pytest.fixture
def capture_logs() -> Generator[List[Dict[str, Any]], None, None]:
    """Captures logs during a test for verification."""
    captured_logs = []
    
    class TestLogHandler(logging.Handler):
        def emit(self, record):
            captured_logs.append({
                "level": record.levelname,
                "message": record.getMessage(),
                "logger": record.name,
                "timestamp": record.created,
                "pathname": record.pathname,
                "lineno": record.lineno,
                "exc_info": record.exc_info
            })
    
    # Create and add the handler
    handler = TestLogHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    # Store the original level to restore it later
    original_level = root_logger.level
    root_logger.setLevel(logging.DEBUG)
    
    yield captured_logs
    
    # Clean up
    root_logger.removeHandler(handler)
    root_logger.setLevel(original_level)


@pytest.fixture
def log_context() -> Dict[str, Any]:
    """Provides a sample log context for testing structured logging."""
    return {
        "request_id": "req-123456",
        "correlation_id": "corr-123456",
        "document_id": "doc-123456",
        "application_id": "app-789012",
        "service": "ocr-service",
        "component": "utils",
        "environment": "test"
    }


# ===== Text Utility Testing Fixtures =====

@pytest.fixture
def sample_ocr_text() -> Dict[str, str]:
    """Provides sample OCR-extracted text for testing text processing utilities."""
    return {
        "clean": "John Doe\n123 Main St\nAnytown, CA 12345\nPhone: 555-123-4567\nEmail: john.doe@example.com",
        "noisy": "J0hn D0e\n123 Ma1n St\nAnytown, CA 12345\nPhone: 555-l23-4567\nEmai1: john.doe@examp1e.com",
        "with_confidence": "John[0.98] Doe[0.97]\n123[0.99] Main[0.95] St[0.94]\nAnytown[0.92], CA[0.98] 12345[0.99]",
        "form_fields": "Name: John Doe\nAddress: 123 Main St\nCity: Anytown\nState: CA\nZIP: 12345\nPhone: 555-123-4567",
        "table": "Date | Description | Amount\n01/15/2023 | Deposit | $1,000.00\n01/20/2023 | Withdrawal | $500.00\n01/25/2023 | Interest | $2.50",
        "mixed_format": "INVOICE\nDate: 01/15/2023\nInvoice #: INV-12345\n\nBill To:\nAcme Corp\n123 Business St\nCorporate City, CA 54321\n\nItem | Quantity | Price | Total\nWidget A | 5 | $10.00 | $50.00\nWidget B | 10 | $15.00 | $150.00\n\nSubtotal: $200.00\nTax (8%): $16.00\nTotal: $216.00"
    }


@pytest.fixture
def key_value_pairs() -> Dict[str, Dict[str, str]]:
    """Provides sample key-value pairs extracted from documents."""
    return {
        "application": {
            "name": "John Doe",
            "address": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345",
            "phone": "555-123-4567",
            "email": "john.doe@example.com",
            "business_name": "Acme Corporation",
            "tax_id": "12-3456789"
        },
        "bank_statement": {
            "bank_name": "First National Bank",
            "account_number": "****1234",
            "statement_date": "2023-01-31",
            "opening_balance": "$5,000.00",
            "closing_balance": "$5,502.50",
            "total_deposits": "$1,000.00",
            "total_withdrawals": "$500.00",
            "interest_earned": "$2.50"
        },
        "invoice": {
            "invoice_number": "INV-12345",
            "date": "2023-01-15",
            "due_date": "2023-02-15",
            "customer_name": "Acme Corp",
            "subtotal": "$200.00",
            "tax": "$16.00",
            "total": "$216.00"
        }
    }


# ===== Image Utility Testing Fixtures =====

@pytest.fixture
def mock_image() -> np.ndarray:
    """Provides a mock image as a numpy array for testing image processing utilities."""
    # Create a simple 100x100 grayscale image
    return np.random.randint(0, 256, (100, 100), dtype=np.uint8)


@pytest.fixture
def mock_color_image() -> np.ndarray:
    """Provides a mock color image as a numpy array for testing image processing utilities."""
    # Create a simple 100x100 RGB image
    return np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def mock_document_image() -> np.ndarray:
    """Provides a mock document image with simulated text regions."""
    # Create a white background
    image = np.ones((1000, 800), dtype=np.uint8) * 255
    
    # Add simulated text lines (dark rectangles)
    # Header
    image[50:80, 100:700] = 50
    
    # Address block
    image[120:140, 100:400] = 60
    image[150:170, 100:350] = 60
    image[180:200, 100:300] = 60
    
    # Form fields (label + value pairs)
    image[250:270, 100:200] = 40  # Label
    image[250:270, 220:500] = 50  # Value
    
    image[300:320, 100:200] = 40  # Label
    image[300:320, 220:450] = 50  # Value
    
    image[350:370, 100:200] = 40  # Label
    image[350:370, 220:400] = 50  # Value
    
    # Table
    table_top = 450
    for i in range(5):  # 5 rows
        row_top = table_top + i * 40
        # Header or data row
        image[row_top:row_top+30, 100:250] = 45  # Column 1
        image[row_top:row_top+30, 260:450] = 45  # Column 2
        image[row_top:row_top+30, 460:650] = 45  # Column 3
    
    # Signature area
    image[700:740, 500:700] = 30
    
    return image


@pytest.fixture
def mock_tensorflow_image_processing():
    """Mocks TensorFlow image processing functions."""
    with patch('tensorflow.image.decode_jpeg') as mock_decode_jpeg, \
         patch('tensorflow.image.decode_png') as mock_decode_png, \
         patch('tensorflow.image.resize') as mock_resize, \
         patch('tensorflow.image.rgb_to_grayscale') as mock_rgb_to_gray:
        
        # Configure mocks
        mock_decode_jpeg.return_value = tf.random.uniform((100, 100, 3))
        mock_decode_png.return_value = tf.random.uniform((100, 100, 3))
        mock_resize.return_value = tf.random.uniform((224, 224, 3))
        mock_rgb_to_gray.return_value = tf.random.uniform((224, 224, 1))
        
        yield


# ===== TensorFlow Utility Testing Fixtures =====

@pytest.fixture
def mock_tensorflow_model():
    """Provides a mocked TensorFlow model for testing."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Create a mock model that returns predictable outputs
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([[0.1, 0.2, 0.7]])
        mock_load_model.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def mock_tensorflow_session():
    """Provides a mocked TensorFlow session for testing."""
    with patch('tensorflow.compat.v1.Session') as mock_session:
        # Configure the mock session
        session_instance = MagicMock()
        mock_session.return_value.__enter__.return_value = session_instance
        
        # Mock the run method to return predictable results
        session_instance.run.return_value = {
            "output": np.random.rand(10, 20),
            "confidence": np.random.rand(10)
        }
        
        yield session_instance


@pytest.fixture
def mock_tensorflow_config():
    """Mocks TensorFlow configuration functions."""
    with patch('tensorflow.config.list_physical_devices') as mock_list_devices, \
         patch('tensorflow.config.experimental.set_memory_growth') as mock_set_memory_growth, \
         patch('tensorflow.config.experimental.set_virtual_device_configuration') as mock_set_config:
        
        # Configure mocks
        mock_gpu = MagicMock()
        mock_gpu.name = '/device:GPU:0'
        mock_list_devices.return_value = [mock_gpu]
        mock_set_memory_growth.return_value = None
        mock_set_config.return_value = None
        
        yield


@pytest.fixture
def mock_ocr_model_output() -> Dict[str, Any]:
    """Provides mock OCR model output for testing."""
    return {
        "text": "John Doe\n123 Main St\nAnytown, CA 12345",
        "confidence": 0.92,
        "bounding_boxes": [
            {"text": "John Doe", "box": [0.1, 0.1, 0.5, 0.15], "confidence": 0.98},
            {"text": "123 Main St", "box": [0.1, 0.2, 0.6, 0.25], "confidence": 0.95},
            {"text": "Anytown, CA 12345", "box": [0.1, 0.3, 0.7, 0.35], "confidence": 0.90}
        ],
        "processing_time": 0.45
    }