#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest configuration file for OCR service tests.

This file defines fixtures and setup/teardown functions for OCR service tests.
It provides shared test resources including mock data, test documents, and service mocks
to avoid duplication across test files.
"""

import os
import json
import pytest
import tempfile
import numpy as np
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Tuple, Optional, Generator

# Import types from the OCR service
from ocr_service.src.types.documents import DocumentMetadata, DocumentContent, DocumentType, Document
from ocr_service.src.types.models import OCRModelType, ModelParameters, ModelResult
from ocr_service.src.types.extraction import ExtractedField, ConfidenceScore, ExtractedData
from ocr_service.src.types.storage import S3ClientConfig, StorageOptions, StorageMetadata
from ocr_service.src.types.messages import MessagePayload, MessageHeaders, ExchangeConfig, QueueConfig
from ocr_service.src.types.config import ServiceConfig, TensorFlowConfig

# Import services for mocking
from ocr_service.src.services.ocr_service import OCRService
from ocr_service.src.services.field_extraction_service import FieldExtractionService
from ocr_service.src.services.confidence_service import ConfidenceService
from ocr_service.src.services.storage_service import StorageService
from ocr_service.src.services.queue_service import QueueService

# Import models for mocking
from ocr_service.src.models.base_model import BaseModel
from ocr_service.src.models.typed_text_model import TypedTextModel
from ocr_service.src.models.handwritten_text_model import HandwrittenTextModel
from ocr_service.src.models.hybrid_recognition_model import HybridRecognitionModel
from ocr_service.src.models.model_factory import ModelFactory

# Constants for test configuration
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
TYPED_DOCS_DIR = TEST_DATA_DIR / "typed_documents"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MIXED_DOCS_DIR = TEST_DATA_DIR / "mixed_documents"
FORMS_DIR = TEST_DATA_DIR / "forms"
TABLES_DIR = TEST_DATA_DIR / "tables"
IMAGES_DIR = TEST_DATA_DIR / "images"

# Ensure test directories exist
for directory in [TEST_DATA_DIR, TYPED_DOCS_DIR, HANDWRITTEN_DOCS_DIR, MIXED_DOCS_DIR, 
                 FORMS_DIR, TABLES_DIR, IMAGES_DIR]:
    directory.mkdir(exist_ok=True, parents=True)


# ===== Pytest Configuration =====

def pytest_configure(config):
    """
Configure pytest for OCR service tests.

This function sets up custom markers and configures test coverage reporting.
    """
    # Register custom markers
    config.addinivalue_line("markers", "gpu: marks tests that require GPU (deselect with '-m "not gpu"')")
    config.addinivalue_line("markers", "integration: marks integration tests (deselect with '-m "not integration"')")
    config.addinivalue_line("markers", "slow: marks tests that are slow to execute (deselect with '-m "not slow"')")
    
    # Configure test coverage reporting
    config.option.cov_report = {"term-missing": True}
    config.option.cov_config = ".coveragerc"


# ===== Mock Data Fixtures =====

@pytest.fixture
def sample_document_metadata() -> DocumentMetadata:
    """
Provide sample document metadata for testing.
    """
    return DocumentMetadata(
        document_id="doc-12345",
        filename="sample_application.pdf",
        file_size=1024 * 1024,  # 1MB
        mime_type="application/pdf",
        created_at="2023-01-01T12:00:00Z",
        classification=DocumentType.APPLICATION,
        page_count=3
    )


@pytest.fixture
def sample_document_content() -> DocumentContent:
    """
Provide sample document content for testing.

This fixture creates a small PDF-like byte array for testing document processing
without requiring actual document files.
    """
    # Create a mock PDF-like byte array
    return DocumentContent(
        content=b"%PDF-1.5\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n"
    )


@pytest.fixture
def sample_document(sample_document_metadata, sample_document_content) -> Document:
    """
Provide a complete sample document for testing.
    """
    return Document(
        metadata=sample_document_metadata,
        content=sample_document_content
    )


@pytest.fixture
def sample_extracted_fields() -> List[ExtractedField]:
    """
Provide sample extracted fields with confidence scores for testing.
    """
    return [
        ExtractedField(
            field_name="business_name",
            field_value="Acme Corporation",
            confidence=ConfidenceScore(0.95),
            field_type="text",
            page=1,
            location={"x": 100, "y": 200, "width": 300, "height": 30}
        ),
        ExtractedField(
            field_name="tax_id",
            field_value="12-3456789",
            confidence=ConfidenceScore(0.88),
            field_type="text",
            page=1,
            location={"x": 400, "y": 200, "width": 150, "height": 30}
        ),
        ExtractedField(
            field_name="address",
            field_value="123 Main St, Anytown, CA 90210",
            confidence=ConfidenceScore(0.92),
            field_type="text",
            page=1,
            location={"x": 100, "y": 250, "width": 400, "height": 30}
        ),
        ExtractedField(
            field_name="requested_amount",
            field_value="50000",
            confidence=ConfidenceScore(0.97),
            field_type="currency",
            page=2,
            location={"x": 300, "y": 400, "width": 100, "height": 30}
        ),
        ExtractedField(
            field_name="signature",
            field_value="John Smith",
            confidence=ConfidenceScore(0.75),  # Lower confidence for handwritten text
            field_type="signature",
            page=3,
            location={"x": 400, "y": 700, "width": 200, "height": 50}
        )
    ]


@pytest.fixture
def sample_extracted_data(sample_extracted_fields) -> ExtractedData:
    """
Provide sample extracted data for testing.
    """
    return ExtractedData(
        document_id="doc-12345",
        fields=sample_extracted_fields,
        document_type=DocumentType.APPLICATION,
        overall_confidence=0.89,  # Average confidence across all fields
        processing_time=2.34,  # seconds
        extraction_timestamp="2023-01-01T12:05:00Z",
        metadata={
            "model_version": "v1.2.3",
            "processor_id": "ocr-worker-01"
        }
    )


@pytest.fixture
def sample_message_payload(sample_document_metadata) -> MessagePayload:
    """
Provide sample RabbitMQ message payload for testing.
    """
    return MessagePayload(
        document_id=sample_document_metadata.document_id,
        storage_path="mca-documents-staging/applications/doc-12345.pdf",
        document_type=DocumentType.APPLICATION,
        priority="high",
        metadata={
            "source": "email",
            "customer_id": "cust-6789",
            "application_id": "app-5678"
        }
    )


@pytest.fixture
def sample_message_headers() -> MessageHeaders:
    """
Provide sample RabbitMQ message headers for testing.
    """
    return MessageHeaders(
        correlation_id="corr-12345",
        message_id="msg-67890",
        timestamp="2023-01-01T12:00:00Z",
        reply_to="data.processing",
        content_type="application/json",
        content_encoding="utf-8"
    )


@pytest.fixture
def sample_s3_config() -> S3ClientConfig:
    """
Provide sample S3 client configuration for testing.
    """
    return S3ClientConfig(
        endpoint_url="https://s3.example.com",
        region_name="us-east-1",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        bucket_name="mca-documents-staging",
        use_ssl=True
    )


@pytest.fixture
def sample_storage_options() -> StorageOptions:
    """
Provide sample storage options for testing.
    """
    return StorageOptions(
        encryption={
            "algorithm": "AES-256",
            "key_id": "test-key-id"
        },
        content_type="application/pdf",
        metadata={
            "document_type": "application",
            "customer_id": "cust-6789"
        },
        storage_class="STANDARD"
    )


@pytest.fixture
def sample_tensorflow_config() -> TensorFlowConfig:
    """
Provide sample TensorFlow configuration for testing.
    """
    return TensorFlowConfig(
        model_path="/models/ocr",
        gpu_memory_fraction=0.5,
        use_gpu=False,  # Disable GPU for tests
        precision="float32",
        batch_size=1,
        num_threads=2
    )


@pytest.fixture
def sample_model_parameters() -> ModelParameters:
    """
Provide sample model parameters for testing.
    """
    return ModelParameters(
        model_type=OCRModelType.TYPED,
        confidence_threshold=0.7,
        language="en",
        dpi=300,
        max_text_length=100,
        preprocessing={
            "denoise": True,
            "deskew": True,
            "contrast_enhancement": True
        }
    )


# ===== Mock Test Document Fixtures =====

@pytest.fixture
def create_test_image():
    """
Create a test image for OCR testing.

This fixture provides a function that creates a simple image with text
for testing OCR functionality without requiring actual document files.
    """
    def _create_image(text: str, size: Tuple[int, int] = (800, 600), 
                     bg_color: Tuple[int, int, int] = (255, 255, 255),
                     text_color: Tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
        """
        Create a simple image with text for testing.
        
        Args:
            text: The text to render in the image
            size: The size of the image (width, height)
            bg_color: Background color as RGB tuple
            text_color: Text color as RGB tuple
            
        Returns:
            A numpy array representing the image
        """
        try:
            # Try to import PIL only when needed to avoid dependency issues
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a blank image with background color
            image = Image.new('RGB', size, color=bg_color)
            draw = ImageDraw.Draw(image)
            
            # Use a default font or try to load a system font
            try:
                font = ImageFont.truetype("Arial", 24)
            except IOError:
                font = ImageFont.load_default()
            
            # Draw the text in the center of the image
            text_width, text_height = draw.textsize(text, font=font)
            position = ((size[0] - text_width) // 2, (size[1] - text_height) // 2)
            draw.text(position, text, fill=text_color, font=font)
            
            # Convert to numpy array
            return np.array(image)
        except ImportError:
            # If PIL is not available, create a simple numpy array
            # This is a fallback for environments without PIL
            image = np.ones((size[1], size[0], 3), dtype=np.uint8) * np.array(bg_color, dtype=np.uint8)
            # Return the image without text (can't render text without PIL)
            return image
    
    return _create_image


@pytest.fixture
def typed_text_document(create_test_image) -> Path:
    """
Create a test document with typed text for OCR testing.
    """
    # Create a simple image with typed text
    image = create_test_image(
        "Acme Corporation\n123 Main Street\nAnytown, CA 90210\nTax ID: 12-3456789"
    )
    
    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=TYPED_DOCS_DIR) as tmp:
        try:
            from PIL import Image
            Image.fromarray(image).save(tmp.name)
        except ImportError:
            # Fallback if PIL is not available
            np.save(tmp.name, image)
        
        return Path(tmp.name)


@pytest.fixture
def handwritten_text_document(create_test_image) -> Path:
    """
Create a test document with simulated handwritten text for OCR testing.
    """
    # Create a simple image with text (in a real implementation, this would be handwritten)
    image = create_test_image(
        "John Smith\nSignature: ___________\nDate: 01/01/2023"
    )
    
    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=HANDWRITTEN_DOCS_DIR) as tmp:
        try:
            from PIL import Image
            Image.fromarray(image).save(tmp.name)
        except ImportError:
            # Fallback if PIL is not available
            np.save(tmp.name, image)
        
        return Path(tmp.name)


@pytest.fixture
def form_document(create_test_image) -> Path:
    """
Create a test form document for OCR testing.
    """
    # Create a simple image with form-like text
    image = create_test_image(
        "MERCHANT CASH ADVANCE APPLICATION\n\n" +
        "Business Name: ___________________\n" +
        "Tax ID: ___________________\n" +
        "Address: ___________________\n" +
        "Requested Amount: $___________________\n" +
        "Owner Name: ___________________\n" +
        "Phone: ___________________\n" +
        "Email: ___________________\n\n" +
        "Signature: ___________________  Date: ___________________"
    )
    
    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=FORMS_DIR) as tmp:
        try:
            from PIL import Image
            Image.fromarray(image).save(tmp.name)
        except ImportError:
            # Fallback if PIL is not available
            np.save(tmp.name, image)
        
        return Path(tmp.name)


@pytest.fixture
def table_document(create_test_image) -> Path:
    """
Create a test document with a table for OCR testing.
    """
    # Create a simple image with table-like text
    image = create_test_image(
        "MONTHLY REVENUE SUMMARY\n\n" +
        "Month | Revenue | Expenses | Profit\n" +
        "----------------------------------\n" +
        "Jan   | $50,000 | $30,000  | $20,000\n" +
        "Feb   | $55,000 | $32,000  | $23,000\n" +
        "Mar   | $60,000 | $35,000  | $25,000\n" +
        "----------------------------------\n" +
        "Total | $165,000| $97,000  | $68,000"
    )
    
    # Save the image to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False, dir=TABLES_DIR) as tmp:
        try:
            from PIL import Image
            Image.fromarray(image).save(tmp.name)
        except ImportError:
            # Fallback if PIL is not available
            np.save(tmp.name, image)
        
        return Path(tmp.name)


# ===== Mock Service Fixtures =====

@pytest.fixture
def mock_tensorflow():
    """
Mock TensorFlow to avoid GPU requirements in tests.

This fixture patches TensorFlow to return predictable results without
requiring actual GPU hardware or model loading.
    """
    with patch("tensorflow.keras.models.load_model") as mock_load_model:
        # Create a mock model that returns predictable results
        mock_model = MagicMock()
        mock_model.predict.return_value = np.random.rand(1, 10, 20)
        mock_load_model.return_value = mock_model
        
        # Mock other TensorFlow functions as needed
        with patch("tensorflow.config.experimental.set_memory_growth") as mock_set_memory_growth:
            mock_set_memory_growth.return_value = None
            
            with patch("tensorflow.config.list_physical_devices") as mock_list_devices:
                # Simulate no GPUs available for testing
                mock_list_devices.return_value = []
                
                yield


@pytest.fixture
def mock_s3_client():
    """
Mock S3 client to avoid external dependencies in tests.
    """
    with patch("boto3.client") as mock_client:
        s3_client = MagicMock()
        
        # Mock S3 operations
        s3_client.get_object.return_value = {
            "Body": MagicMock(read=lambda: b"%PDF-1.5\nTest document content"),
            "ContentType": "application/pdf",
            "Metadata": {"document-type": "application"}
        }
        
        s3_client.put_object.return_value = {
            "ETag": "\"mock-etag\"",
            "VersionId": "mock-version-id"
        }
        
        s3_client.list_objects_v2.return_value = {
            "Contents": [
                {"Key": "applications/doc-12345.pdf", "Size": 1024, "LastModified": "2023-01-01T12:00:00Z"},
                {"Key": "applications/doc-67890.pdf", "Size": 2048, "LastModified": "2023-01-02T12:00:00Z"}
            ]
        }
        
        mock_client.return_value = s3_client
        yield s3_client


@pytest.fixture
def mock_rabbitmq_connection():
    """
Mock RabbitMQ connection to avoid external dependencies in tests.
    """
    with patch("pika.BlockingConnection") as mock_connection:
        connection = MagicMock()
        channel = MagicMock()
        
        # Mock channel operations
        channel.basic_publish.return_value = None
        channel.basic_consume.return_value = None
        channel.queue_declare.return_value = MagicMock(method=MagicMock(queue="test-queue"))
        channel.exchange_declare.return_value = None
        
        # Set up the connection to return our mock channel
        connection.channel.return_value = channel
        mock_connection.return_value = connection
        
        yield connection, channel


@pytest.fixture
def mock_ocr_service(mock_tensorflow):
    """
Mock OCR service to return predictable results in tests.
    """
    with patch("ocr_service.src.services.ocr_service.OCRService") as MockOCRService:
        service = MagicMock()
        
        # Mock OCR processing to return predictable results
        service.process_document.return_value = {
            "text": "Acme Corporation\n123 Main Street\nAnytown, CA 90210\nTax ID: 12-3456789",
            "confidence": 0.95,
            "processing_time": 1.23
        }
        
        MockOCRService.return_value = service
        yield service


@pytest.fixture
def mock_field_extraction_service():
    """
Mock field extraction service to return predictable results in tests.
    """
    with patch("ocr_service.src.services.field_extraction_service.FieldExtractionService") as MockService:
        service = MagicMock()
        
        # Mock field extraction to return predictable results
        service.extract_fields.return_value = [
            {
                "field_name": "business_name",
                "field_value": "Acme Corporation",
                "confidence": 0.95,
                "field_type": "text",
                "page": 1,
                "location": {"x": 100, "y": 200, "width": 300, "height": 30}
            },
            {
                "field_name": "tax_id",
                "field_value": "12-3456789",
                "confidence": 0.88,
                "field_type": "text",
                "page": 1,
                "location": {"x": 400, "y": 200, "width": 150, "height": 30}
            }
        ]
        
        MockService.return_value = service
        yield service


@pytest.fixture
def mock_confidence_service():
    """
Mock confidence service to return predictable results in tests.
    """
    with patch("ocr_service.src.services.confidence_service.ConfidenceService") as MockService:
        service = MagicMock()
        
        # Mock confidence evaluation to return predictable results
        service.evaluate_confidence.return_value = 0.92
        service.flag_low_confidence_fields.return_value = []
        
        MockService.return_value = service
        yield service


@pytest.fixture
def mock_storage_service(mock_s3_client):
    """
Mock storage service to return predictable results in tests.
    """
    with patch("ocr_service.src.services.storage_service.StorageService") as MockService:
        service = MagicMock()
        
        # Mock storage operations to return predictable results
        service.get_document.return_value = Document(
            metadata=DocumentMetadata(
                document_id="doc-12345",
                filename="sample_application.pdf",
                file_size=1024,
                mime_type="application/pdf",
                created_at="2023-01-01T12:00:00Z",
                classification=DocumentType.APPLICATION,
                page_count=3
            ),
            content=DocumentContent(content=b"%PDF-1.5\nTest document content")
        )
        
        service.store_extraction_results.return_value = "mca-documents-staging/results/doc-12345.json"
        
        MockService.return_value = service
        yield service


@pytest.fixture
def mock_queue_service(mock_rabbitmq_connection):
    """
Mock queue service to return predictable results in tests.
    """
    with patch("ocr_service.src.services.queue_service.QueueService") as MockService:
        service = MagicMock()
        
        # Mock queue operations to return predictable results
        service.publish_message.return_value = True
        service.consume_messages.return_value = None  # This would normally start consuming
        
        # Create a method to simulate message receipt
        def simulate_message_receipt(callback):
            """
Simulate receiving a message and calling the callback.
            """
            # Create a mock message
            message = {
                "document_id": "doc-12345",
                "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
                "document_type": "APPLICATION",
                "priority": "high",
                "metadata": {
                    "source": "email",
                    "customer_id": "cust-6789",
                    "application_id": "app-5678"
                }
            }
            
            # Create mock delivery info
            delivery_info = {
                "delivery_tag": "tag-12345",
                "exchange": "mca.documents",
                "routing_key": "ocr.request"
            }
            
            # Create mock properties
            properties = {
                "correlation_id": "corr-12345",
                "message_id": "msg-67890",
                "timestamp": "2023-01-01T12:00:00Z",
                "reply_to": "data.processing",
                "content_type": "application/json",
                "content_encoding": "utf-8"
            }
            
            # Call the callback with the mock message
            callback(delivery_info, properties, json.dumps(message).encode('utf-8'))
        
        # Add the simulation method to the mock service
        service.simulate_message_receipt = simulate_message_receipt
        
        MockService.return_value = service
        yield service


@pytest.fixture
def mock_model_factory(mock_tensorflow):
    """
Mock model factory to return predictable models in tests.
    """
    with patch("ocr_service.src.models.model_factory.ModelFactory") as MockFactory:
        factory = MagicMock()
        
        # Create mock models
        typed_model = MagicMock()
        typed_model.process_image.return_value = {
            "text": "Acme Corporation\n123 Main Street\nAnytown, CA 90210\nTax ID: 12-3456789",
            "confidence": 0.95,
            "processing_time": 1.23
        }
        
        handwritten_model = MagicMock()
        handwritten_model.process_image.return_value = {
            "text": "John Smith\nSignature: John Smith\nDate: 01/01/2023",
            "confidence": 0.85,
            "processing_time": 1.45
        }
        
        hybrid_model = MagicMock()
        hybrid_model.process_image.return_value = {
            "text": "Acme Corporation\nSignature: John Smith\nDate: 01/01/2023",
            "confidence": 0.90,
            "processing_time": 1.67
        }
        
        # Configure the factory to return appropriate models
        factory.get_model.side_effect = lambda model_type, **kwargs: {
            OCRModelType.TYPED: typed_model,
            OCRModelType.HANDWRITTEN: handwritten_model,
            OCRModelType.HYBRID: hybrid_model
        }.get(model_type, typed_model)
        
        MockFactory.return_value = factory
        yield factory


# ===== Test Environment Fixtures =====

@pytest.fixture(scope="session")
def test_env_vars():
    """
Set up environment variables for testing.

This fixture ensures that tests run with consistent environment variables
regardless of the actual environment configuration.
    """
    # Store original environment variables
    original_env = {}
    test_vars = {
        "OCR_SERVICE_ENV": "test",
        "OCR_SERVICE_PORT": "8080",
        "OCR_SERVICE_LOG_LEVEL": "INFO",
        "OCR_SERVICE_S3_ENDPOINT": "https://s3.example.com",
        "OCR_SERVICE_S3_REGION": "us-east-1",
        "OCR_SERVICE_S3_BUCKET": "mca-documents-staging",
        "OCR_SERVICE_RABBITMQ_HOST": "localhost",
        "OCR_SERVICE_RABBITMQ_PORT": "5672",
        "OCR_SERVICE_RABBITMQ_EXCHANGE": "mca.documents",
        "OCR_SERVICE_RABBITMQ_QUEUE": "ocr.request",
        "OCR_SERVICE_MODEL_PATH": "/models/ocr",
        "OCR_SERVICE_USE_GPU": "false"
    }
    
    # Save original values and set test values
    for key, value in test_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
    
    yield
    
    # Restore original environment variables
    for key in test_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]


@pytest.fixture
def temp_output_dir():
    """
Provide a temporary directory for test outputs.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def temp_config_file():
    """
Provide a temporary configuration file for testing.
    """
    config = {
        "service": {
            "name": "ocr-service",
            "version": "1.0.0",
            "port": 8080,
            "log_level": "INFO"
        },
        "tensorflow": {
            "model_path": "/models/ocr",
            "use_gpu": False,
            "gpu_memory_fraction": 0.5,
            "precision": "float32",
            "batch_size": 1,
            "num_threads": 2
        },
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "exchange": "mca.documents",
            "queue": "ocr.request",
            "use_tls": True,
            "cert_path": "/certs/client.pem",
            "key_path": "/certs/client.key",
            "ca_path": "/certs/ca.pem"
        },
        "s3": {
            "endpoint_url": "https://s3.example.com",
            "region_name": "us-east-1",
            "bucket_name": "mca-documents-staging",
            "use_ssl": True,
            "encryption": {
                "algorithm": "AES-256",
                "key_id": "test-key-id"
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tmp:
        json.dump(config, tmp)
        tmp_path = Path(tmp.name)
    
    yield tmp_path
    
    # Clean up the temporary file
    if tmp_path.exists():
        tmp_path.unlink()