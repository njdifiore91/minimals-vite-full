import os
import json
import pytest
import logging
import tempfile
import datetime
from unittest.mock import MagicMock, patch
from pathlib import Path
from typing import Dict, List, Any, Generator, Callable

# Import scikit-learn components for mocking
import numpy as np
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline

# Set up logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config() -> Dict[str, Any]:
    """Provides a test configuration dictionary with all required settings."""
    return {
        "app": {
            "name": "document-service",
            "version": "1.0.0",
            "environment": "test",
            "log_level": "INFO"
        },
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "username": "test_user",
            "password": "test_password",
            "vhost": "/",
            "exchange": "mca.documents",
            "queue": "document-processing",
            "use_tls": False,
            "cert_path": None,
            "retry_attempts": 3,
            "retry_delay": 1.0
        },
        "s3": {
            "endpoint_url": "http://localhost:9000",
            "region": "us-east-1",
            "access_key": "test_access_key",
            "secret_key": "test_secret_key",
            "bucket": "mca-documents-test",
            "use_ssl": True,
            "encryption": "AES256"
        },
        "model": {
            "path": "models/document_classifier.pkl",
            "version": "1.0.0",
            "confidence_threshold": 0.85,
            "supported_document_types": [
                "application_form",
                "bank_statement",
                "tax_return",
                "identity_document",
                "business_license",
                "utility_bill",
                "other"
            ]
        }
    }


@pytest.fixture
def test_env_vars(monkeypatch) -> None:
    """Sets up environment variables for testing."""
    env_vars = {
        "APP_NAME": "document-service",
        "APP_VERSION": "1.0.0",
        "APP_ENVIRONMENT": "test",
        "LOG_LEVEL": "INFO",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "test_user",
        "RABBITMQ_PASSWORD": "test_password",
        "RABBITMQ_VHOST": "/",
        "RABBITMQ_EXCHANGE": "mca.documents",
        "RABBITMQ_QUEUE": "document-processing",
        "RABBITMQ_USE_TLS": "False",
        "RABBITMQ_RETRY_ATTEMPTS": "3",
        "RABBITMQ_RETRY_DELAY": "1.0",
        "S3_ENDPOINT_URL": "http://localhost:9000",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test_access_key",
        "S3_SECRET_KEY": "test_secret_key",
        "S3_BUCKET": "mca-documents-test",
        "S3_USE_SSL": "True",
        "S3_ENCRYPTION": "AES256",
        "MODEL_PATH": "models/document_classifier.pkl",
        "MODEL_VERSION": "1.0.0",
        "MODEL_CONFIDENCE_THRESHOLD": "0.85"
    }
    
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)


# ============================================================================
# Mock Fixtures for External Dependencies
# ============================================================================

@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Creates a mock S3 client for testing."""
    mock_client = MagicMock()
    
    # Mock common S3 operations
    mock_client.upload_file.return_value = None
    mock_client.download_file.return_value = None
    mock_client.get_object.return_value = {
        'Body': MagicMock(),
        'ContentType': 'application/pdf',
        'Metadata': {
            'document_type': 'application_form',
            'confidence': '0.95',
            'processed_at': datetime.datetime.now().isoformat()
        }
    }
    mock_client.list_objects_v2.return_value = {
        'Contents': [
            {'Key': 'document1.pdf', 'Size': 1024, 'LastModified': datetime.datetime.now()},
            {'Key': 'document2.pdf', 'Size': 2048, 'LastModified': datetime.datetime.now()}
        ]
    }
    mock_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/document.pdf?signature=abc123'
    
    return mock_client


@pytest.fixture
def mock_rabbitmq_connection() -> MagicMock:
    """Creates a mock RabbitMQ connection for testing."""
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    
    # Set up the channel mock
    mock_connection.channel.return_value = mock_channel
    mock_channel.basic_publish.return_value = None
    mock_channel.basic_consume.return_value = None
    mock_channel.basic_ack.return_value = None
    mock_channel.basic_nack.return_value = None
    mock_channel.queue_declare.return_value = MagicMock(method=MagicMock(queue='test_queue'))
    mock_channel.exchange_declare.return_value = None
    mock_channel.queue_bind.return_value = None
    
    # Mock the consumer callback mechanism
    def mock_start_consuming():
        # This doesn't actually consume, just pretends to start the process
        pass
    
    mock_channel.start_consuming = mock_start_consuming
    
    return mock_connection


@pytest.fixture
def mock_svm_classifier() -> MagicMock:
    """Creates a mock SVM classifier for testing."""
    mock_classifier = MagicMock(spec=SVC)
    
    # Mock the predict and predict_proba methods
    mock_classifier.predict.return_value = np.array(['application_form'])
    mock_classifier.predict_proba.return_value = np.array([[0.05, 0.1, 0.05, 0.05, 0.05, 0.7]])
    
    return mock_classifier


@pytest.fixture
def mock_random_forest_classifier() -> MagicMock:
    """Creates a mock Random Forest classifier for testing."""
    mock_classifier = MagicMock(spec=RandomForestClassifier)
    
    # Mock the predict and predict_proba methods
    mock_classifier.predict.return_value = np.array(['application_form'])
    mock_classifier.predict_proba.return_value = np.array([[0.05, 0.05, 0.05, 0.05, 0.05, 0.75]])
    
    return mock_classifier


@pytest.fixture
def mock_ml_pipeline() -> MagicMock:
    """Creates a mock scikit-learn pipeline for testing."""
    mock_pipeline = MagicMock(spec=Pipeline)
    
    # Mock the predict and predict_proba methods
    mock_pipeline.predict.return_value = np.array(['application_form'])
    mock_pipeline.predict_proba.return_value = np.array([[0.05, 0.05, 0.05, 0.05, 0.05, 0.75]])
    
    # Mock the classes_ attribute
    mock_pipeline.classes_ = np.array([
        'bank_statement', 'tax_return', 'identity_document', 
        'business_license', 'utility_bill', 'application_form'
    ])
    
    return mock_pipeline


@pytest.fixture
def mock_model_loader(mock_ml_pipeline) -> MagicMock:
    """Creates a mock model loader function for testing."""
    mock_loader = MagicMock()
    mock_loader.return_value = mock_ml_pipeline
    return mock_loader


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_document_path() -> Generator[Path, None, None]:
    """Creates a temporary PDF file for testing document processing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        # Write some dummy PDF content
        temp_file.write(b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n')
    
    # Create a Path object for the temporary file
    pdf_path = Path(temp_file.name)
    
    yield pdf_path
    
    # Clean up the temporary file
    if pdf_path.exists():
        os.unlink(pdf_path)


@pytest.fixture
def sample_document_bytes() -> bytes:
    """Provides sample document bytes for testing."""
    return b'%PDF-1.4\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n2 0 obj\n<</Type/Pages/Kids[3 0 R]/Count 1>>\nendobj\n3 0 obj\n<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer\n<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF\n'


@pytest.fixture
def sample_document_metadata() -> Dict[str, Any]:
    """Provides sample document metadata for testing."""
    return {
        'document_id': 'doc-123456',
        'original_filename': 'application.pdf',
        'file_size': 1024,
        'mime_type': 'application/pdf',
        'upload_timestamp': datetime.datetime.now().isoformat(),
        'classification': {
            'document_type': 'application_form',
            'confidence': 0.95,
            'alternative_types': [
                {'type': 'utility_bill', 'confidence': 0.03},
                {'type': 'bank_statement', 'confidence': 0.02}
            ]
        },
        'storage_path': 's3://mca-documents-test/doc-123456.pdf',
        'processing_status': 'classified',
        'metadata': {
            'page_count': 3,
            'has_signature': True,
            'is_complete': True
        }
    }


@pytest.fixture
def sample_rabbitmq_message() -> Dict[str, Any]:
    """Provides a sample RabbitMQ message for testing."""
    return {
        'message_id': 'msg-123456',
        'timestamp': datetime.datetime.now().isoformat(),
        'document': {
            'document_id': 'doc-123456',
            'original_filename': 'application.pdf',
            'file_size': 1024,
            'mime_type': 'application/pdf',
            'storage_path': 's3://mca-documents-test/doc-123456.pdf'
        },
        'source': 'email-service',
        'correlation_id': 'corr-123456'
    }


@pytest.fixture
def document_factory() -> Callable[[str, str, int], Dict[str, Any]]:
    """Factory function for creating test document metadata with customizable properties."""
    def _create_document(doc_type='application_form', filename='document.pdf', size=1024):
        doc_id = f'doc-{datetime.datetime.now().timestamp():.0f}'
        return {
            'document_id': doc_id,
            'original_filename': filename,
            'file_size': size,
            'mime_type': 'application/pdf' if filename.endswith('.pdf') else 'image/jpeg',
            'upload_timestamp': datetime.datetime.now().isoformat(),
            'classification': {
                'document_type': doc_type,
                'confidence': 0.95,
                'alternative_types': [
                    {'type': 'utility_bill', 'confidence': 0.03},
                    {'type': 'bank_statement', 'confidence': 0.02}
                ]
            },
            'storage_path': f's3://mca-documents-test/{doc_id}.pdf',
            'processing_status': 'classified',
            'metadata': {
                'page_count': 3,
                'has_signature': True,
                'is_complete': True
            }
        }
    
    return _create_document


# ============================================================================
# Setup and Teardown Functions
# ============================================================================

@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Sets up the test environment before all tests run."""
    logger.info("Setting up test environment for document-service utils tests")
    
    # Create any necessary directories for test artifacts
    os.makedirs('test_output', exist_ok=True)
    
    yield
    
    # Clean up test artifacts
    logger.info("Tearing down test environment for document-service utils tests")


@pytest.fixture(autouse=True)
def setup_test_patches():
    """Sets up patches for external dependencies that should be applied to all tests."""
    # Patch the boto3 client to prevent actual AWS calls
    with patch('boto3.client'):
        # Patch the pika connection to prevent actual RabbitMQ connections
        with patch('pika.BlockingConnection'):
            # Patch the joblib.load function to prevent actual model loading
            with patch('joblib.load'):
                yield


# ============================================================================
# Test Coverage Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with coverage settings."""
    config.option.cov_report = {
        'xml': 'coverage.xml',
        'html': 'htmlcov',
        'term-missing': True
    }
    config.option.cov_source = ['document_service']
    config.option.cov_branch = True


def pytest_sessionstart(session):
    """Called after the Session object has been created and before tests are collected."""
    logger.info(f"Starting test session: {session.name}")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished, right before returning the exit status."""
    logger.info(f"Test session finished with status: {exitstatus}")


def pytest_runtest_setup(item):
    """Called before each test is run."""
    logger.debug(f"Setting up test: {item.name}")


def pytest_runtest_teardown(item):
    """Called after each test is run."""
    logger.debug(f"Tearing down test: {item.name}")