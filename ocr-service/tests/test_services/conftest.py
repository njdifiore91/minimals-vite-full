"""Pytest configuration file for OCR service tests.

This module provides fixtures and setup/teardown functions for OCR service tests.
It includes mock data, test documents, and service mocks to avoid duplication across
test files and ensure tests are isolated from external dependencies.

The fixtures in this file enable testing without GPU requirements, making them
suitable for CI/CD pipelines. They also provide consistent test data and mock
services to ensure reliable test execution.

Key fixtures include:
- Mock TensorFlow models to avoid GPU requirements
- Mock S3 storage to avoid external dependencies
- Mock RabbitMQ connections for message queue testing
- Sample documents and expected extraction results
- Environment configuration for different deployment stages

Usage:
    Import fixtures directly in test files:
    ```python
    def test_ocr_extraction(mock_ocr_service, sample_typed_document):
        # Test implementation using fixtures
    ```
"""

import json
import os
import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import OCR service modules
from config import app_config, tensorflow_config
from models.base_model import BaseModel
from models.typed_text_model import TypedTextModel
from models.handwritten_text_model import HandwrittenTextModel
from models.hybrid_recognition_model import HybridRecognitionModel
from models.structure_recognition_model import StructureRecognitionModel
from services.ocr_service import OCRService
from services.storage_service import StorageService
from services.queue_service import QueueService
from services.field_extraction_service import FieldExtractionService
from services.confidence_service import ConfidenceService
from types.models import OCRModelType, ModelParameters
from types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from types.storage import S3ClientConfig, StorageOptions
from types.messages import MessagePayload, MessageHeaders

# Constants for test configuration
TEST_DATA_DIR = Path(__file__).parent.parent / 'test_data'
TYPED_DOCS_DIR = TEST_DATA_DIR / 'typed_documents'
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / 'handwritten_documents'
MIXED_DOCS_DIR = TEST_DATA_DIR / 'mixed_documents'
TABLES_DIR = TEST_DATA_DIR / 'tables'

# Test bucket names
TEST_BUCKET_NAME = 'mca-documents-test'
STAGING_BUCKET_NAME = 'mca-documents-staging'
PRODUCTION_BUCKET_NAME = 'mca-documents-production'

# Sample document paths
SAMPLE_TYPED_DOC = 'sample_application.pdf'
SAMPLE_HANDWRITTEN_DOC = 'sample_notes.pdf'
SAMPLE_MIXED_DOC = 'sample_form_with_signature.pdf'
SAMPLE_TABLE_DOC = 'sample_financial_statement.pdf'

# Test environment configuration
TEST_ENV = {
    'development': {
        'bucket': TEST_BUCKET_NAME,
        'confidence_threshold': 0.6,  # Lower threshold for development
        'use_gpu': False
    },
    'staging': {
        'bucket': STAGING_BUCKET_NAME,
        'confidence_threshold': 0.7,
        'use_gpu': True
    },
    'production': {
        'bucket': PRODUCTION_BUCKET_NAME,
        'confidence_threshold': 0.8,  # Higher threshold for production
        'use_gpu': True
    }
}


@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory."""
    return TEST_DATA_DIR


@pytest.fixture(scope="session")
def test_metadata():
    """Load test metadata for all test documents."""
    metadata_path = TEST_DATA_DIR / 'metadata.json'
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="session")
def typed_docs_metadata():
    """Load metadata for typed document tests."""
    metadata_path = TYPED_DOCS_DIR / 'sample_manifest.json'
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="session")
def handwritten_docs_metadata():
    """Load metadata for handwritten document tests."""
    metadata_path = HANDWRITTEN_DOCS_DIR / 'sample_manifest.json'
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="session")
def mixed_docs_metadata():
    """Load metadata for mixed document tests."""
    metadata_path = MIXED_DOCS_DIR / 'sample_manifest.json'
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return {}


@pytest.fixture(scope="session")
def tables_metadata():
    """Load metadata for table document tests."""
    metadata_path = TABLES_DIR / 'sample_manifest.json'
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return {}


@pytest.fixture
def sample_typed_document():
    """Create a sample typed document for testing."""
    # This would normally be a real document, but for testing we'll create a mock
    return {
        'document_id': 'typed-doc-001',
        'document_type': 'application_form',
        'content_type': 'typed',
        'path': f'{TYPED_DOCS_DIR}/{SAMPLE_TYPED_DOC}',
        'expected_fields': {
            'business_name': 'Acme Corporation',
            'tax_id': '12-3456789',
            'address': '123 Main St, Anytown, USA 12345',
            'phone': '(555) 123-4567',
            'email': 'contact@acmecorp.com'
        },
        'expected_confidence': 0.95
    }


@pytest.fixture
def sample_handwritten_document():
    """Create a sample handwritten document for testing."""
    return {
        'document_id': 'handwritten-doc-001',
        'document_type': 'notes',
        'content_type': 'handwritten',
        'path': f'{HANDWRITTEN_DOCS_DIR}/{SAMPLE_HANDWRITTEN_DOC}',
        'expected_fields': {
            'name': 'John Smith',
            'date': '01/15/2023',
            'notes': 'Discussed funding options for Q2 expansion',
            'signature': 'John Smith'
        },
        'expected_confidence': 0.85
    }


@pytest.fixture
def sample_mixed_document():
    """Create a sample document with both typed and handwritten content."""
    return {
        'document_id': 'mixed-doc-001',
        'document_type': 'application_with_signature',
        'content_type': 'mixed',
        'path': f'{MIXED_DOCS_DIR}/{SAMPLE_MIXED_DOC}',
        'expected_fields': {
            'business_name': 'XYZ Enterprises',
            'tax_id': '98-7654321',
            'address': '456 Oak Ave, Somewhere, USA 54321',
            'signature': 'Jane Doe',
            'date': '03/22/2023'
        },
        'expected_confidence': 0.90
    }


@pytest.fixture
def sample_table_document():
    """Create a sample document with tabular data."""
    return {
        'document_id': 'table-doc-001',
        'document_type': 'financial_statement',
        'content_type': 'table',
        'path': f'{TABLES_DIR}/{SAMPLE_TABLE_DOC}',
        'expected_table': {
            'headers': ['Month', 'Revenue', 'Expenses', 'Profit'],
            'rows': [
                ['January', '$10,000', '$7,500', '$2,500'],
                ['February', '$12,000', '$8,000', '$4,000'],
                ['March', '$15,000', '$9,000', '$6,000']
            ]
        },
        'expected_confidence': 0.92
    }


@pytest.fixture
def mock_document_bytes():
    """Create mock document bytes for testing."""
    # This would normally be actual document bytes, but for testing we'll use a placeholder
    return b'Mock PDF document content'


@pytest.fixture
def mock_image_bytes():
    """Create mock image bytes for testing."""
    # This would normally be actual image bytes, but for testing we'll use a placeholder
    return b'Mock image content'


@pytest.fixture
def temp_document_file():
    """Create a temporary document file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
        tmp.write(b'Mock PDF document content')
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Cleanup after test
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def mock_tensorflow_config():
    """Mock TensorFlow configuration to avoid GPU requirements in tests."""
    config = MagicMock()
    config.model_path = '/path/to/models'
    config.use_gpu = False
    config.confidence_threshold = 0.7
    config.batch_size = 1
    config.memory_limit = 1024
    return config


@pytest.fixture
def mock_base_model():
    """Create a mock base OCR model."""
    model = MagicMock(spec=BaseModel)
    model.model_type = OCRModelType.TYPED
    model.extract_text.return_value = {
        'text': 'Sample extracted text',
        'confidence': 0.95
    }
    return model


@pytest.fixture
def mock_typed_text_model():
    """Create a mock typed text OCR model."""
    model = MagicMock(spec=TypedTextModel)
    model.model_type = OCRModelType.TYPED
    model.extract_text.return_value = {
        'text': 'Sample typed text',
        'confidence': 0.95
    }
    model.extract_fields.return_value = {
        'business_name': {'value': 'Acme Corporation', 'confidence': 0.98},
        'tax_id': {'value': '12-3456789', 'confidence': 0.97},
        'address': {'value': '123 Main St, Anytown, USA 12345', 'confidence': 0.95},
        'phone': {'value': '(555) 123-4567', 'confidence': 0.96},
        'email': {'value': 'contact@acmecorp.com', 'confidence': 0.94}
    }
    return model


@pytest.fixture
def mock_handwritten_text_model():
    """Create a mock handwritten text OCR model."""
    model = MagicMock(spec=HandwrittenTextModel)
    model.model_type = OCRModelType.HANDWRITTEN
    model.extract_text.return_value = {
        'text': 'Sample handwritten text',
        'confidence': 0.85
    }
    model.extract_fields.return_value = {
        'name': {'value': 'John Smith', 'confidence': 0.88},
        'date': {'value': '01/15/2023', 'confidence': 0.86},
        'notes': {'value': 'Discussed funding options for Q2 expansion', 'confidence': 0.82},
        'signature': {'value': 'John Smith', 'confidence': 0.84}
    }
    return model


@pytest.fixture
def mock_hybrid_recognition_model():
    """Create a mock hybrid recognition OCR model."""
    model = MagicMock(spec=HybridRecognitionModel)
    model.model_type = OCRModelType.HYBRID
    model.extract_text.return_value = {
        'text': 'Sample mixed content text',
        'confidence': 0.90
    }
    model.extract_fields.return_value = {
        'business_name': {'value': 'XYZ Enterprises', 'confidence': 0.95},
        'tax_id': {'value': '98-7654321', 'confidence': 0.94},
        'address': {'value': '456 Oak Ave, Somewhere, USA 54321', 'confidence': 0.93},
        'signature': {'value': 'Jane Doe', 'confidence': 0.85},
        'date': {'value': '03/22/2023', 'confidence': 0.87}
    }
    return model


@pytest.fixture
def mock_structure_recognition_model():
    """Create a mock structure recognition model."""
    model = MagicMock(spec=StructureRecognitionModel)
    model.extract_structure.return_value = {
        'tables': [
            {
                'headers': ['Month', 'Revenue', 'Expenses', 'Profit'],
                'rows': [
                    ['January', '$10,000', '$7,500', '$2,500'],
                    ['February', '$12,000', '$8,000', '$4,000'],
                    ['March', '$15,000', '$9,000', '$6,000']
                ],
                'confidence': 0.92
            }
        ],
        'forms': [
            {
                'fields': [
                    {'name': 'business_name', 'value': 'Acme Corporation', 'confidence': 0.98},
                    {'name': 'tax_id', 'value': '12-3456789', 'confidence': 0.97}
                ],
                'confidence': 0.95
            }
        ],
        'confidence': 0.94
    }
    return model


@pytest.fixture
def mock_model_parameters():
    """Create mock model parameters for testing."""
    return ModelParameters(
        model_type=OCRModelType.TYPED,
        confidence_threshold=0.7,
        batch_size=1,
        use_gpu=False
    )


@pytest.fixture
def mock_extracted_data():
    """Create mock extracted data for testing."""
    # Using a function to create a new instance each time to avoid shared state
    def _create_extracted_data():
        return ExtractedData(
            document_id='doc-001',
            fields={
                'business_name': ExtractedField(value='Acme Corporation', confidence=ConfidenceScore(0.98)),
                'tax_id': ExtractedField(value='12-3456789', confidence=ConfidenceScore(0.97)),
                'address': ExtractedField(value='123 Main St, Anytown, USA 12345', confidence=ConfidenceScore(0.95))
            },
            metadata={
                'document_type': 'application_form',
                'processing_time': 1.25,
                'model_type': 'TYPED'
            },
            overall_confidence=ConfidenceScore(0.95)
        )
    
    return _create_extracted_data


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client for testing."""
    s3_client = MagicMock()
    
    # Mock download_file method
    def mock_download_file(bucket, key, filename):
        with open(filename, 'wb') as f:
            f.write(b'Mock document content')
        return True
    
    s3_client.download_file.side_effect = mock_download_file
    
    # Mock upload_file method
    s3_client.upload_file.return_value = True
    
    # Mock get_object method
    s3_client.get_object.return_value = {
        'Body': MagicMock(read=lambda: b'Mock document content'),
        'ContentLength': 100,
        'ContentType': 'application/pdf',
        'Metadata': {
            'document_id': 'doc-001',
            'document_type': 'application_form'
        }
    }
    
    return s3_client


@pytest.fixture
def mock_s3_config():
    """Create mock S3 configuration for testing."""
    return S3ClientConfig(
        endpoint='http://localhost:9000',
        bucket=TEST_BUCKET_NAME,
        region='us-east-1',
        access_key='test-access-key',
        secret_key='test-secret-key',
        options=StorageOptions(
            encryption='AES256',
            acl='private'
        )
    )


@pytest.fixture
def mock_storage_service(mock_s3_client, mock_s3_config):
    """Create a mock storage service for testing."""
    with patch('services.storage_service.boto3.client', return_value=mock_s3_client):
        service = StorageService(config=mock_s3_config)
        yield service


@pytest.fixture
def mock_rabbitmq_connection():
    """Create a mock RabbitMQ connection for testing."""
    connection = MagicMock()
    channel = MagicMock()
    connection.channel.return_value = channel
    
    # Mock basic_publish method
    channel.basic_publish.return_value = None
    
    # Mock basic_consume method
    def mock_basic_consume(queue, on_message_callback, auto_ack):
        # Simulate message delivery
        on_message_callback(channel, MagicMock(), MagicMock(), b'{"document_id": "doc-001", "bucket": "test-bucket", "key": "test-key"}')
        return None
    
    channel.basic_consume.side_effect = mock_basic_consume
    
    return connection


@pytest.fixture
def mock_queue_service(mock_rabbitmq_connection):
    """Create a mock queue service for testing."""
    with patch('services.queue_service.pika.BlockingConnection', return_value=mock_rabbitmq_connection):
        service = QueueService(
            host='localhost',
            port=5672,
            username='guest',
            password='guest',
            exchange='mca.documents',
            queue='data-extraction'
        )
        yield service


@pytest.fixture
def mock_message_payload():
    """Create a mock message payload for testing."""
    return MessagePayload(
        document_id='doc-001',
        bucket=TEST_BUCKET_NAME,
        key='documents/application_form.pdf',
        document_type='application_form',
        content_type='typed'
    )


@pytest.fixture
def mock_message_headers():
    """Create mock message headers for testing."""
    return MessageHeaders(
        correlation_id='corr-001',
        message_id='msg-001',
        timestamp='2023-05-23T10:15:30Z',
        content_type='application/json'
    )


@pytest.fixture
def mock_field_extraction_service():
    """Create a mock field extraction service for testing."""
    service = MagicMock(spec=FieldExtractionService)
    service.extract_fields.return_value = {
        'business_name': ExtractedField(value='Acme Corporation', confidence=ConfidenceScore(0.98)),
        'tax_id': ExtractedField(value='12-3456789', confidence=ConfidenceScore(0.97)),
        'address': ExtractedField(value='123 Main St, Anytown, USA 12345', confidence=ConfidenceScore(0.95))
    }
    return service


@pytest.fixture
def mock_confidence_service():
    """Create a mock confidence service for testing."""
    service = MagicMock(spec=ConfidenceService)
    service.evaluate_confidence.return_value = ConfidenceScore(0.95)
    service.flag_low_confidence_fields.return_value = []
    return service


@pytest.fixture
def mock_ocr_service(mock_typed_text_model, mock_handwritten_text_model, mock_hybrid_recognition_model, mock_extracted_data):
    """Create a mock OCR service for testing."""
    service = MagicMock(spec=OCRService)
    
    # Configure the mock to return different models based on document type
    def get_model_for_document(document_type, content_type):
        if content_type == 'typed':
            return mock_typed_text_model
        elif content_type == 'handwritten':
            return mock_handwritten_text_model
        elif content_type == 'mixed':
            return mock_hybrid_recognition_model
        else:
            return mock_typed_text_model
    
    service.get_model_for_document.side_effect = get_model_for_document
    
    # Configure process_document to return extracted data
    service.process_document.return_value = mock_extracted_data()
    
    return service


@pytest.fixture(autouse=True)
def disable_gpu():
    """Disable GPU usage for all tests to ensure they run in CI environments."""
    # Set environment variables to disable GPU
    env_vars = {
        'CUDA_VISIBLE_DEVICES': '-1',
        'TF_FORCE_GPU_ALLOW_GROWTH': 'false',
        'TF_CPP_MIN_LOG_LEVEL': '3'  # Suppress TensorFlow logging
    }
    
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def enable_coverage_report():
    """Enable coverage reporting for tests."""
    # This fixture can be used to configure coverage reporting
    # It doesn't need to do anything as pytest-cov handles this
    # based on configuration, but it serves as a marker for tests
    # that should be included in coverage reports
    pass


@pytest.fixture
def mock_environment(request):
    """Configure the test environment (development, staging, production)."""
    # Default to development environment
    env_name = getattr(request, 'param', 'development')
    
    # Get environment configuration
    env_config = TEST_ENV.get(env_name, TEST_ENV['development'])
    
    # Apply environment configuration
    with patch.dict(os.environ, {
        'OCR_ENVIRONMENT': env_name,
        'OCR_BUCKET_NAME': env_config['bucket'],
        'OCR_CONFIDENCE_THRESHOLD': str(env_config['confidence_threshold']),
        'OCR_USE_GPU': str(env_config['use_gpu']).lower()
    }):
        yield env_name, env_config


@pytest.fixture(autouse=True)
def mock_tensorflow_import():
    """Mock TensorFlow import to avoid requiring GPU in test environments."""
    tensorflow_mock = MagicMock()
    # Configure the mock to simulate TensorFlow behavior
    tensorflow_mock.config.experimental.set_memory_growth.return_value = None
    tensorflow_mock.config.experimental.list_physical_devices.return_value = []
    
    # Mock TensorFlow model loading and prediction
    model_mock = MagicMock()
    model_mock.predict.return_value = [[[0.95, 0.05], [0.98, 0.02]], [[0.85, 0.15], [0.78, 0.22]]]
    tensorflow_mock.keras.models.load_model.return_value = model_mock
    
    # Mock TensorFlow image processing
    tensorflow_mock.image.decode_image.return_value = MagicMock()
    tensorflow_mock.image.resize.return_value = MagicMock()
    
    # Mock TensorFlow data processing
    tensorflow_mock.data.Dataset.from_tensor_slices.return_value = MagicMock()
    tensorflow_mock.data.Dataset.batch.return_value = MagicMock()
    
    with patch.dict('sys.modules', {'tensorflow': tensorflow_mock}):
        yield tensorflow_mock


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "gpu: mark test as requiring GPU"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture
def mock_document_classification():
    """Create mock document classification results for testing."""
    return {
        'document_type': 'application_form',
        'content_type': 'typed',
        'confidence': 0.95,
        'page_count': 2,
        'has_tables': True,
        'has_forms': True,
        'has_handwriting': False
    }


@pytest.fixture
def mock_document_with_low_confidence():
    """Create a mock document with low confidence extraction results."""
    return {
        'document_id': 'low-conf-doc-001',
        'document_type': 'invoice',
        'content_type': 'typed',
        'path': f'{TYPED_DOCS_DIR}/low_quality_invoice.pdf',
        'expected_fields': {
            'invoice_number': 'INV-2023-0456',
            'date': '04/15/2023',
            'amount': '$1,234.56',
            'vendor': 'Supplier Co Ltd'
        },
        'expected_confidence': 0.65,  # Low confidence
        'expected_low_confidence_fields': ['vendor', 'amount']
    }


@pytest.fixture
def mock_processing_error():
    """Create a mock processing error for testing error handling."""
    class OCRProcessingError(Exception):
        def __init__(self, message, document_id, error_code):
            self.message = message
            self.document_id = document_id
            self.error_code = error_code
            super().__init__(self.message)
    
    return OCRProcessingError(
        message="Failed to process document due to poor image quality",
        document_id="error-doc-001",
        error_code="OCR_QUALITY_ERROR"
    )