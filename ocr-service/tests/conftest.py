#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shared pytest fixtures for the OCR Service test suite.

This module provides reusable test components such as mocked S3 clients,
RabbitMQ connections, TensorFlow models, and document samples.
It enables consistent test setup across all test modules and reduces code duplication.
"""

import json
import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Generator, Tuple

# Moto for AWS mocking
from moto import mock_s3

# For TensorFlow mocking
import numpy as np
import tensorflow as tf

# Import application modules
from src.types.config import ServiceConfig, TensorFlowConfig, RabbitMQConfig, S3Config, LoggingConfig
from src.types.documents import DocumentType, DocumentMetadata, Document, ProcessingStatus
from src.types.models import OCRModelType, ModelParameters
from src.types.extraction import ExtractedField, ConfidenceScore, ExtractedData
from src.types.messages import MessagePayload, MessageHeaders
from src.types.storage import S3ClientConfig, StorageOptions

# Import services for mocking
from src.services.ocr_service import OCRService
from src.services.queue_service import QueueService
from src.services.storage_service import StorageService
from src.services.confidence_service import ConfidenceService
from src.services.field_extraction_service import FieldExtractionService

# Import app for testing
from src.app import Application


# Constants for testing
TEST_DATA_DIR = Path(__file__).parent / "test_data"
TYPED_DOCS_DIR = TEST_DATA_DIR / "typed_documents"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MIXED_DOCS_DIR = TEST_DATA_DIR / "mixed_documents"
IMAGES_DIR = TEST_DATA_DIR / "images"
TABLES_DIR = TEST_DATA_DIR / "tables"
FORMS_DIR = TEST_DATA_DIR / "forms"

# Test bucket names
TEST_BUCKET_NAME = "mca-documents-test"


# ===== Configuration Fixtures =====

@pytest.fixture
def test_config() -> ServiceConfig:
    """Provides a test configuration for the OCR Service."""
    return ServiceConfig(
        service_name="ocr-service-test",
        version="1.0.0-test",
        environment="test",
        port=8080,
        debug=True
    )


@pytest.fixture
def test_tensorflow_config() -> TensorFlowConfig:
    """Provides a test TensorFlow configuration."""
    return TensorFlowConfig(
        model_path="/tmp/models",
        typed_model_name="typed_model",
        handwritten_model_name="handwritten_model",
        hybrid_model_name="hybrid_model",
        gpu_memory_limit=1024,  # Small limit for testing
        confidence_threshold=0.75,
        use_gpu=False  # Disable GPU for testing
    )


@pytest.fixture
def test_rabbitmq_config() -> RabbitMQConfig:
    """Provides a test RabbitMQ configuration."""
    return RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        vhost="/",
        exchange="mca.documents.test",
        queue="data-extraction-test",
        routing_key="ocr.test",
        use_tls=False,  # Disable TLS for testing
        cert_path=None,
        reconnect_attempts=3,
        reconnect_delay=1
    )


@pytest.fixture
def test_s3_config() -> S3Config:
    """Provides a test S3 configuration."""
    return S3Config(
        endpoint_url="http://localhost:4566",  # LocalStack endpoint
        region="us-east-1",
        bucket=TEST_BUCKET_NAME,
        access_key="test",
        secret_key="test",
        use_ssl=False,  # Disable SSL for testing
        encryption_key="test-encryption-key",
        timeout=5
    )


@pytest.fixture
def test_logging_config() -> LoggingConfig:
    """Provides a test logging configuration."""
    return LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        file_path=None  # No file logging for tests
    )


@pytest.fixture
def app_config(test_config, test_tensorflow_config, test_rabbitmq_config, 
              test_s3_config, test_logging_config) -> Dict[str, Any]:
    """Provides a complete application configuration for testing."""
    return {
        "service": test_config,
        "tensorflow": test_tensorflow_config,
        "rabbitmq": test_rabbitmq_config,
        "s3": test_s3_config,
        "logging": test_logging_config
    }


# ===== Mock Service Fixtures =====

@pytest.fixture
def mock_ocr_service() -> MagicMock:
    """Provides a mocked OCR service."""
    mock_service = MagicMock(spec=OCRService)
    
    # Configure the mock to return predictable results
    mock_service.process_document.return_value = {
        "text": "Sample extracted text for testing",
        "confidence": 0.95
    }
    
    return mock_service


@pytest.fixture
def mock_queue_service() -> MagicMock:
    """Provides a mocked queue service."""
    mock_service = MagicMock(spec=QueueService)
    
    # Configure the mock to simulate message handling
    mock_service.connect.return_value = True
    mock_service.disconnect.return_value = True
    mock_service.publish_message.return_value = True
    
    return mock_service


@pytest.fixture
def mock_storage_service() -> MagicMock:
    """Provides a mocked storage service."""
    mock_service = MagicMock(spec=StorageService)
    
    # Configure the mock to simulate storage operations
    mock_service.connect.return_value = True
    mock_service.disconnect.return_value = True
    mock_service.download_document.return_value = b"test document content"
    mock_service.upload_extracted_data.return_value = "s3://test-bucket/extracted/test.json"
    
    return mock_service


@pytest.fixture
def mock_confidence_service() -> MagicMock:
    """Provides a mocked confidence service."""
    mock_service = MagicMock(spec=ConfidenceService)
    
    # Configure the mock to return predictable confidence scores
    mock_service.evaluate_confidence.return_value = {
        "overall_confidence": 0.92,
        "fields": {
            "field1": 0.98,
            "field2": 0.85,
            "field3": 0.93
        },
        "requires_verification": False
    }
    
    return mock_service


@pytest.fixture
def mock_field_extraction_service() -> MagicMock:
    """Provides a mocked field extraction service."""
    mock_service = MagicMock(spec=FieldExtractionService)
    
    # Configure the mock to return predictable extracted fields
    mock_service.extract_fields.return_value = {
        "fields": {
            "name": {"value": "John Doe", "confidence": 0.98},
            "address": {"value": "123 Main St", "confidence": 0.92},
            "phone": {"value": "555-123-4567", "confidence": 0.89}
        },
        "metadata": {
            "document_type": "application_form",
            "processing_time": 0.45
        }
    }
    
    return mock_service


@pytest.fixture
def mock_application(mock_ocr_service, mock_queue_service, mock_storage_service,
                   mock_confidence_service, mock_field_extraction_service, 
                   app_config) -> Application:
    """Provides a mocked application with all services."""
    app = Application(config=app_config)
    
    # Replace real services with mocks
    app.ocr_service = mock_ocr_service
    app.queue_service = mock_queue_service
    app.storage_service = mock_storage_service
    app.confidence_service = mock_confidence_service
    app.field_extraction_service = mock_field_extraction_service
    
    return app


# ===== S3 Mock Fixtures =====

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
def s3_client_config() -> S3ClientConfig:
    """Provides S3 client configuration for testing."""
    return S3ClientConfig(
        endpoint_url="http://localhost:4566",
        region="us-east-1",
        bucket=TEST_BUCKET_NAME,
        access_key="test",
        secret_key="test"
    )


@pytest.fixture
def s3_storage_options() -> StorageOptions:
    """Provides S3 storage options for testing."""
    return StorageOptions(
        encryption_key="test-encryption-key",
        use_encryption=True,
        content_type="application/json",
        metadata={
            "service": "ocr-service-test",
            "version": "1.0.0-test"
        }
    )


# ===== TensorFlow Mock Fixtures =====

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
def mock_gpu_device():
    """Mocks TensorFlow GPU device availability."""
    with patch('tensorflow.config.list_physical_devices') as mock_devices:
        # Simulate one GPU being available
        mock_devices.return_value = ['/device:GPU:0']
        yield


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


# ===== Document Fixtures =====

@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """Provides sample document metadata for testing."""
    return DocumentMetadata(
        filename="test_document.pdf",
        content_type="application/pdf",
        size=12345,
        created_at="2023-01-01T12:00:00Z",
        updated_at="2023-01-01T12:00:00Z",
        document_id="doc-123456",
        application_id="app-789012"
    )


@pytest.fixture
def sample_document_content() -> bytes:
    """Provides sample document content for testing."""
    # Create a simple PDF-like content for testing
    return b"%PDF-1.5\nSample document content for testing OCR\n%%EOF"


@pytest.fixture
def sample_document(sample_document_metadata, sample_document_content) -> Document:
    """Provides a sample document for testing."""
    return Document(
        metadata=sample_document_metadata,
        content=sample_document_content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    )


@pytest.fixture
def typed_document() -> Document:
    """Provides a sample typed document for testing."""
    metadata = DocumentMetadata(
        filename="typed_application.pdf",
        content_type="application/pdf",
        size=23456,
        created_at="2023-01-02T12:00:00Z",
        updated_at="2023-01-02T12:00:00Z",
        document_id="doc-typed-123",
        application_id="app-789012"
    )
    
    # Use a real test file if available, otherwise use dummy content
    content = b"%PDF-1.5\nTyped document content for OCR testing\n%%EOF"
    typed_path = TYPED_DOCS_DIR / "application_forms" / "typed_application.pdf"
    if typed_path.exists():
        with open(typed_path, "rb") as f:
            content = f.read()
    
    return Document(
        metadata=metadata,
        content=content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    )


@pytest.fixture
def handwritten_document() -> Document:
    """Provides a sample handwritten document for testing."""
    metadata = DocumentMetadata(
        filename="handwritten_form.pdf",
        content_type="application/pdf",
        size=34567,
        created_at="2023-01-03T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        document_id="doc-handwritten-123",
        application_id="app-789012"
    )
    
    # Use a real test file if available, otherwise use dummy content
    content = b"%PDF-1.5\nHandwritten document content for OCR testing\n%%EOF"
    handwritten_path = HANDWRITTEN_DOCS_DIR / "handwritten_form.pdf"
    if handwritten_path.exists():
        with open(handwritten_path, "rb") as f:
            content = f.read()
    
    return Document(
        metadata=metadata,
        content=content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    )


@pytest.fixture
def mixed_document() -> Document:
    """Provides a sample document with mixed typed and handwritten content."""
    metadata = DocumentMetadata(
        filename="mixed_document.pdf",
        content_type="application/pdf",
        size=45678,
        created_at="2023-01-04T12:00:00Z",
        updated_at="2023-01-04T12:00:00Z",
        document_id="doc-mixed-123",
        application_id="app-789012"
    )
    
    # Use a real test file if available, otherwise use dummy content
    content = b"%PDF-1.5\nMixed typed and handwritten content for OCR testing\n%%EOF"
    mixed_path = MIXED_DOCS_DIR / "mixed_document.pdf"
    if mixed_path.exists():
        with open(mixed_path, "rb") as f:
            content = f.read()
    
    return Document(
        metadata=metadata,
        content=content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    )


@pytest.fixture
def document_collection() -> List[Document]:
    """Provides a collection of different document types for testing."""
    # This fixture depends on the individual document fixtures
    # but pytest doesn't support direct fixture dependencies in return values,
    # so we recreate similar documents here
    
    documents = []
    
    # Add a typed document
    typed_metadata = DocumentMetadata(
        filename="typed_application.pdf",
        content_type="application/pdf",
        size=23456,
        created_at="2023-01-02T12:00:00Z",
        updated_at="2023-01-02T12:00:00Z",
        document_id="doc-typed-123",
        application_id="app-789012"
    )
    typed_content = b"%PDF-1.5\nTyped document content for OCR testing\n%%EOF"
    documents.append(Document(
        metadata=typed_metadata,
        content=typed_content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    ))
    
    # Add a handwritten document
    handwritten_metadata = DocumentMetadata(
        filename="handwritten_form.pdf",
        content_type="application/pdf",
        size=34567,
        created_at="2023-01-03T12:00:00Z",
        updated_at="2023-01-03T12:00:00Z",
        document_id="doc-handwritten-123",
        application_id="app-789012"
    )
    handwritten_content = b"%PDF-1.5\nHandwritten document content for OCR testing\n%%EOF"
    documents.append(Document(
        metadata=handwritten_metadata,
        content=handwritten_content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    ))
    
    # Add a mixed document
    mixed_metadata = DocumentMetadata(
        filename="mixed_document.pdf",
        content_type="application/pdf",
        size=45678,
        created_at="2023-01-04T12:00:00Z",
        updated_at="2023-01-04T12:00:00Z",
        document_id="doc-mixed-123",
        application_id="app-789012"
    )
    mixed_content = b"%PDF-1.5\nMixed typed and handwritten content for OCR testing\n%%EOF"
    documents.append(Document(
        metadata=mixed_metadata,
        content=mixed_content,
        document_type=DocumentType.APPLICATION,
        status=ProcessingStatus.PENDING
    ))
    
    # Add a bank statement document
    bank_metadata = DocumentMetadata(
        filename="bank_statement.pdf",
        content_type="application/pdf",
        size=56789,
        created_at="2023-01-05T12:00:00Z",
        updated_at="2023-01-05T12:00:00Z",
        document_id="doc-bank-123",
        application_id="app-789012"
    )
    bank_content = b"%PDF-1.5\nBank statement content for OCR testing\n%%EOF"
    documents.append(Document(
        metadata=bank_metadata,
        content=bank_content,
        document_type=DocumentType.BANK_STATEMENT,
        status=ProcessingStatus.PENDING
    ))
    
    return documents


# ===== Message Fixtures =====

@pytest.fixture
def sample_message_payload() -> MessagePayload:
    """Provides a sample message payload for testing."""
    return MessagePayload(
        document_id="doc-123456",
        application_id="app-789012",
        storage_path="s3://mca-documents-test/documents/doc-123456.pdf",
        document_type="application",
        priority="high",
        metadata={
            "filename": "application.pdf",
            "content_type": "application/pdf",
            "size": 12345
        }
    )


@pytest.fixture
def sample_message_headers() -> MessageHeaders:
    """Provides sample message headers for testing."""
    return MessageHeaders(
        message_id="msg-123456",
        timestamp="2023-01-01T12:00:00Z",
        correlation_id="corr-123456",
        reply_to="ocr.response",
        content_type="application/json",
        content_encoding="utf-8"
    )


# ===== Extraction Result Fixtures =====

@pytest.fixture
def sample_extracted_fields() -> Dict[str, ExtractedField]:
    """Provides sample extracted fields for testing."""
    return {
        "name": ExtractedField(
            value="John Doe",
            confidence=ConfidenceScore(0.98),
            location={"page": 1, "top": 100, "left": 200, "width": 300, "height": 30}
        ),
        "address": ExtractedField(
            value="123 Main St, Anytown, USA 12345",
            confidence=ConfidenceScore(0.92),
            location={"page": 1, "top": 150, "left": 200, "width": 400, "height": 30}
        ),
        "phone": ExtractedField(
            value="555-123-4567",
            confidence=ConfidenceScore(0.89),
            location={"page": 1, "top": 200, "left": 200, "width": 200, "height": 30}
        ),
        "email": ExtractedField(
            value="john.doe@example.com",
            confidence=ConfidenceScore(0.95),
            location={"page": 1, "top": 250, "left": 200, "width": 350, "height": 30}
        ),
        "business_name": ExtractedField(
            value="Acme Corporation",
            confidence=ConfidenceScore(0.97),
            location={"page": 1, "top": 300, "left": 200, "width": 300, "height": 30}
        ),
        "tax_id": ExtractedField(
            value="12-3456789",
            confidence=ConfidenceScore(0.85),
            location={"page": 1, "top": 350, "left": 200, "width": 200, "height": 30}
        )
    }


@pytest.fixture
def sample_extracted_data(sample_extracted_fields) -> ExtractedData:
    """Provides sample extracted data for testing."""
    return ExtractedData(
        document_id="doc-123456",
        application_id="app-789012",
        document_type=DocumentType.APPLICATION,
        fields=sample_extracted_fields,
        overall_confidence=ConfidenceScore(0.93),
        requires_verification=False,
        processing_time=1.25,
        extraction_timestamp="2023-01-01T12:01:25Z",
        model_version="1.0.0"
    )


# ===== Temporary File Fixtures =====

@pytest.fixture
def temp_pdf_file() -> Generator[Tuple[str, bytes], None, None]:
    """Creates a temporary PDF file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        content = b"%PDF-1.5\nTemporary PDF file for testing\n%%EOF"
        tmp.write(content)
        tmp.flush()
        yield tmp.name, content
    
    # Cleanup after test
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def temp_image_file() -> Generator[Tuple[str, bytes], None, None]:
    """Creates a temporary image file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        # Create a simple PNG header for testing
        content = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        tmp.write(content)
        tmp.flush()
        yield tmp.name, content
    
    # Cleanup after test
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


# ===== Test Metadata Fixtures =====

@pytest.fixture
def test_metadata() -> Dict[str, Any]:
    """Loads test metadata from the metadata.json file."""
    metadata_path = TEST_DATA_DIR / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, "r") as f:
            return json.load(f)
    else:
        # Return a minimal metadata structure if file doesn't exist
        return {
            "documents": {
                "typed_application.pdf": {
                    "type": "application",
                    "content_type": "typed",
                    "expected_fields": {
                        "name": "John Doe",
                        "address": "123 Main St, Anytown, USA 12345",
                        "phone": "555-123-4567"
                    },
                    "expected_confidence": 0.95
                },
                "handwritten_form.pdf": {
                    "type": "application",
                    "content_type": "handwritten",
                    "expected_fields": {
                        "name": "Jane Smith",
                        "address": "456 Oak Ave, Othertown, USA 67890",
                        "phone": "555-987-6543"
                    },
                    "expected_confidence": 0.85
                }
            }
        }


# ===== Model Parameters Fixtures =====

@pytest.fixture
def typed_model_parameters() -> ModelParameters:
    """Provides parameters for typed text OCR model."""
    return ModelParameters(
        model_type=OCRModelType.TYPED,
        confidence_threshold=0.75,
        batch_size=1,
        image_size=(1024, 768),
        channels=3,
        use_gpu=False,  # Disable GPU for testing
        preprocessing_steps=["resize", "normalize"],
        language="en"
    )


@pytest.fixture
def handwritten_model_parameters() -> ModelParameters:
    """Provides parameters for handwritten text OCR model."""
    return ModelParameters(
        model_type=OCRModelType.HANDWRITTEN,
        confidence_threshold=0.65,  # Lower threshold for handwritten text
        batch_size=1,
        image_size=(1024, 768),
        channels=3,
        use_gpu=False,  # Disable GPU for testing
        preprocessing_steps=["resize", "normalize", "enhance_contrast"],
        language="en"
    )


@pytest.fixture
def hybrid_model_parameters() -> ModelParameters:
    """Provides parameters for hybrid (mixed) text OCR model."""
    return ModelParameters(
        model_type=OCRModelType.HYBRID,
        confidence_threshold=0.70,  # Balanced threshold for mixed content
        batch_size=1,
        image_size=(1024, 768),
        channels=3,
        use_gpu=False,  # Disable GPU for testing
        preprocessing_steps=["resize", "normalize", "adaptive_threshold"],
        language="en"
    )