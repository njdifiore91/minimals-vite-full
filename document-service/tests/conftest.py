import os
import json
import pytest
import tempfile
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta

# Mock imports for dependencies that might not be available during testing
pytest.importorskip("boto3")
pytest.importorskip("scikit-learn")
pytest.importorskip("pika")


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def app_config():
    """Fixture that provides a test configuration for the application."""
    return {
        "service": {
            "name": "document-service",
            "version": "1.0.0",
            "environment": "test",
            "log_level": "DEBUG"
        },
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
            "exchange": "mca.documents",
            "queue": "document-processing",
            "routing_key": "document.classify",
            "use_tls": False,
            "cert_path": None,
            "reconnect_attempts": 3,
            "reconnect_delay": 5
        },
        "s3": {
            "endpoint_url": "http://localhost:4566",  # LocalStack endpoint
            "region_name": "us-east-1",
            "bucket_name": "mca-documents-test",
            "use_ssl": True,
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": None
            },
            "access_key_id": "test",
            "secret_access_key": "test"
        },
        "model": {
            "svm": {
                "C": 1.0,
                "kernel": "linear",
                "probability": True,
                "class_weight": "balanced"
            },
            "random_forest": {
                "n_estimators": 100,
                "max_depth": 10,
                "min_samples_split": 2,
                "min_samples_leaf": 1,
                "class_weight": "balanced"
            },
            "confidence_threshold": 0.85,
            "feature_extraction": {
                "max_features": 5000,
                "ngram_range": (1, 2),
                "min_df": 2,
                "max_df": 0.95
            },
            "model_path": "/tmp/models"
        }
    }


@pytest.fixture
def env_vars(app_config):
    """Fixture that sets up environment variables for testing."""
    original_environ = os.environ.copy()
    
    # Flatten the nested config into environment variables
    os.environ["SERVICE_NAME"] = app_config["service"]["name"]
    os.environ["SERVICE_VERSION"] = app_config["service"]["version"]
    os.environ["SERVICE_ENVIRONMENT"] = app_config["service"]["environment"]
    os.environ["LOG_LEVEL"] = app_config["service"]["log_level"]
    
    os.environ["RABBITMQ_HOST"] = app_config["rabbitmq"]["host"]
    os.environ["RABBITMQ_PORT"] = str(app_config["rabbitmq"]["port"])
    os.environ["RABBITMQ_USERNAME"] = app_config["rabbitmq"]["username"]
    os.environ["RABBITMQ_PASSWORD"] = app_config["rabbitmq"]["password"]
    os.environ["RABBITMQ_EXCHANGE"] = app_config["rabbitmq"]["exchange"]
    os.environ["RABBITMQ_QUEUE"] = app_config["rabbitmq"]["queue"]
    
    os.environ["S3_ENDPOINT_URL"] = app_config["s3"]["endpoint_url"]
    os.environ["S3_REGION_NAME"] = app_config["s3"]["region_name"]
    os.environ["S3_BUCKET_NAME"] = app_config["s3"]["bucket_name"]
    os.environ["S3_ACCESS_KEY_ID"] = app_config["s3"]["access_key_id"]
    os.environ["S3_SECRET_ACCESS_KEY"] = app_config["s3"]["secret_access_key"]
    
    yield os.environ
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_environ)


# ============================================================================
# S3 Storage Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """Fixture that provides a mocked S3 client."""
    with patch("boto3.client") as mock_client:
        s3_client = MagicMock()
        mock_client.return_value = s3_client
        
        # Mock common S3 methods
        s3_client.upload_fileobj = MagicMock()
        s3_client.download_fileobj = MagicMock()
        s3_client.head_object = MagicMock(return_value={
            "ContentLength": 12345,
            "LastModified": datetime.now(),
            "Metadata": {"document-type": "application_form"}
        })
        s3_client.list_objects_v2 = MagicMock(return_value={
            "Contents": [
                {"Key": "documents/doc1.pdf", "Size": 12345, "LastModified": datetime.now()},
                {"Key": "documents/doc2.pdf", "Size": 23456, "LastModified": datetime.now()}
            ]
        })
        s3_client.generate_presigned_url = MagicMock(return_value="https://example.com/presigned-url")
        
        yield s3_client


@pytest.fixture
def mock_s3_bucket(mock_s3_client, app_config):
    """Fixture that provides a mocked S3 bucket with test documents."""
    bucket_name = app_config["s3"]["bucket_name"]
    
    # Mock bucket existence check
    mock_s3_client.head_bucket = MagicMock()
    
    # Mock bucket creation
    mock_s3_client.create_bucket = MagicMock()
    
    # Return bucket name for convenience
    return bucket_name


@pytest.fixture
def s3_document_metadata():
    """Fixture that provides sample document metadata as stored in S3."""
    return {
        "application_form": {
            "document-type": "application_form",
            "confidence-score": "0.95",
            "page-count": "3",
            "processed-at": datetime.now().isoformat(),
            "application-id": "APP-12345"
        },
        "bank_statement": {
            "document-type": "bank_statement",
            "confidence-score": "0.92",
            "page-count": "2",
            "processed-at": datetime.now().isoformat(),
            "application-id": "APP-12345",
            "institution": "Example Bank"
        },
        "tax_return": {
            "document-type": "tax_return",
            "confidence-score": "0.97",
            "page-count": "5",
            "processed-at": datetime.now().isoformat(),
            "application-id": "APP-12345",
            "tax-year": "2023"
        },
        "identity_document": {
            "document-type": "identity_document",
            "confidence-score": "0.94",
            "page-count": "1",
            "processed-at": datetime.now().isoformat(),
            "application-id": "APP-12345",
            "id-type": "drivers_license"
        },
        "business_license": {
            "document-type": "business_license",
            "confidence-score": "0.91",
            "page-count": "1",
            "processed-at": datetime.now().isoformat(),
            "application-id": "APP-12345",
            "expiration-date": (datetime.now() + timedelta(days=365)).isoformat()
        }
    }


# ============================================================================
# RabbitMQ Fixtures
# ============================================================================

@pytest.fixture
def mock_rabbitmq_connection():
    """Fixture that provides a mocked RabbitMQ connection."""
    with patch("pika.BlockingConnection") as mock_connection:
        connection = MagicMock()
        mock_connection.return_value = connection
        
        # Mock connection methods
        connection.is_open = True
        connection.is_closed = False
        connection.close = MagicMock()
        
        yield connection


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """Fixture that provides a mocked RabbitMQ channel."""
    channel = MagicMock()
    mock_rabbitmq_connection.channel.return_value = channel
    
    # Mock channel methods
    channel.exchange_declare = MagicMock()
    channel.queue_declare = MagicMock(return_value=MagicMock(method=MagicMock(queue="document-processing")))
    channel.queue_bind = MagicMock()
    channel.basic_publish = MagicMock()
    channel.basic_consume = MagicMock()
    channel.basic_ack = MagicMock()
    channel.basic_nack = MagicMock()
    channel.start_consuming = MagicMock()
    channel.stop_consuming = MagicMock()
    
    yield channel


@pytest.fixture
def rabbitmq_message_factory():
    """Fixture that provides a factory function for creating RabbitMQ messages."""
    def _create_message(document_type: str, application_id: str, s3_key: str) -> Dict[str, Any]:
        return {
            "document": {
                "id": f"doc-{document_type}-{application_id}",
                "application_id": application_id,
                "s3_key": s3_key,
                "filename": f"{document_type}.pdf",
                "content_type": "application/pdf",
                "size": 12345,
                "uploaded_at": datetime.now().isoformat(),
                "metadata": {}
            },
            "request_id": f"req-{application_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.now().isoformat()
        }
    
    return _create_message


@pytest.fixture
def mock_rabbitmq_message():
    """Fixture that provides a mocked RabbitMQ message."""
    message = MagicMock()
    
    # Create a sample message body
    message_body = json.dumps({
        "document": {
            "id": "doc-123",
            "application_id": "APP-12345",
            "s3_key": "documents/application_form.pdf",
            "filename": "application_form.pdf",
            "content_type": "application/pdf",
            "size": 12345,
            "uploaded_at": datetime.now().isoformat(),
            "metadata": {}
        },
        "request_id": "req-12345",
        "timestamp": datetime.now().isoformat()
    })
    
    # Mock message properties and methods
    message.delivery_tag = 1
    message.body = message_body.encode('utf-8')
    
    yield message


# ============================================================================
# Document Classification Model Fixtures
# ============================================================================

@pytest.fixture
def mock_svm_classifier():
    """Fixture that provides a mocked SVM classifier."""
    classifier = MagicMock()
    
    # Mock classifier methods
    classifier.fit = MagicMock(return_value=classifier)
    classifier.predict = MagicMock(return_value=["application_form"])
    classifier.predict_proba = MagicMock(return_value=[[0.05, 0.95, 0.0, 0.0, 0.0]])  # High confidence for application_form
    classifier.score = MagicMock(return_value=0.95)
    
    yield classifier


@pytest.fixture
def mock_random_forest_classifier():
    """Fixture that provides a mocked Random Forest classifier."""
    classifier = MagicMock()
    
    # Mock classifier methods
    classifier.fit = MagicMock(return_value=classifier)
    classifier.predict = MagicMock(return_value=["application_form"])
    classifier.predict_proba = MagicMock(return_value=[[0.03, 0.97, 0.0, 0.0, 0.0]])  # High confidence for application_form
    classifier.score = MagicMock(return_value=0.97)
    
    yield classifier


@pytest.fixture
def mock_document_classifier(mock_svm_classifier, mock_random_forest_classifier):
    """Fixture that provides a mocked document classifier."""
    classifier = MagicMock()
    
    # Set up the classifiers
    classifier.svm_classifier = mock_svm_classifier
    classifier.rf_classifier = mock_random_forest_classifier
    
    # Mock classifier methods
    classifier.classify = MagicMock(return_value=("application_form", 0.96, {
        "svm_confidence": 0.95,
        "rf_confidence": 0.97,
        "ensemble_confidence": 0.96
    }))
    classifier.get_confidence_scores = MagicMock(return_value={
        "application_form": 0.96,
        "bank_statement": 0.02,
        "tax_return": 0.01,
        "identity_document": 0.01,
        "business_license": 0.0
    })
    
    yield classifier


@pytest.fixture
def mock_feature_extractor():
    """Fixture that provides a mocked feature extractor."""
    extractor = MagicMock()
    
    # Mock extractor methods
    extractor.extract_features = MagicMock(return_value={
        "text_features": [1.0, 0.0, 0.5, 0.2, 0.8],
        "metadata_features": [0.3, 0.7, 0.1]
    })
    extractor.vectorize = MagicMock(return_value=[[1.0, 0.0, 0.5, 0.2, 0.8, 0.3, 0.7, 0.1]])
    
    yield extractor


# ============================================================================
# Test Document Fixtures
# ============================================================================

@pytest.fixture
def test_document_factory():
    """Fixture that provides a factory function for creating test documents."""
    def _create_document(document_type: str, content: Optional[bytes] = None) -> Tuple[str, bytes]:
        if content is None:
            # Generate some dummy content based on document type
            if document_type == "application_form":
                content = b"%PDF-1.5\nApplication Form\nName: John Doe\nBusiness: Acme Inc\nAmount Requested: $50,000"
            elif document_type == "bank_statement":
                content = b"%PDF-1.5\nBank Statement\nAccount: 12345\nBalance: $10,000\nTransactions: 25"
            elif document_type == "tax_return":
                content = b"%PDF-1.5\nTax Return\nTax Year: 2023\nIncome: $120,000\nTax Paid: $30,000"
            elif document_type == "identity_document":
                content = b"%PDF-1.5\nDriver's License\nName: John Doe\nID: DL12345\nExpiration: 2025-01-01"
            elif document_type == "business_license":
                content = b"%PDF-1.5\nBusiness License\nBusiness: Acme Inc\nLicense: BL12345\nExpiration: 2024-12-31"
            else:
                content = b"%PDF-1.5\nGeneric Document\nContent: Test content"
        
        # Create a temporary file with the content
        with tempfile.NamedTemporaryFile(suffix=f".pdf", delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        return temp_file_path, content
    
    return _create_document


@pytest.fixture
def test_application_form(test_document_factory):
    """Fixture that provides a test application form document."""
    file_path, content = test_document_factory("application_form")
    yield file_path, content
    # Clean up the temporary file
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def test_bank_statement(test_document_factory):
    """Fixture that provides a test bank statement document."""
    file_path, content = test_document_factory("bank_statement")
    yield file_path, content
    # Clean up the temporary file
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def test_tax_return(test_document_factory):
    """Fixture that provides a test tax return document."""
    file_path, content = test_document_factory("tax_return")
    yield file_path, content
    # Clean up the temporary file
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def test_identity_document(test_document_factory):
    """Fixture that provides a test identity document."""
    file_path, content = test_document_factory("identity_document")
    yield file_path, content
    # Clean up the temporary file
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def test_business_license(test_document_factory):
    """Fixture that provides a test business license document."""
    file_path, content = test_document_factory("business_license")
    yield file_path, content
    # Clean up the temporary file
    if os.path.exists(file_path):
        os.unlink(file_path)


@pytest.fixture
def test_documents(test_application_form, test_bank_statement, test_tax_return, 
                  test_identity_document, test_business_license):
    """Fixture that provides all test documents."""
    return {
        "application_form": test_application_form,
        "bank_statement": test_bank_statement,
        "tax_return": test_tax_return,
        "identity_document": test_identity_document,
        "business_license": test_business_license
    }


# ============================================================================
# Miscellaneous Fixtures
# ============================================================================

@pytest.fixture
def mock_logger():
    """Fixture that provides a mocked logger."""
    with patch("logging.getLogger") as mock_get_logger:
        logger = MagicMock()
        mock_get_logger.return_value = logger
        
        # Mock logger methods
        logger.debug = MagicMock()
        logger.info = MagicMock()
        logger.warning = MagicMock()
        logger.error = MagicMock()
        logger.critical = MagicMock()
        
        yield logger


@pytest.fixture
def mock_time():
    """Fixture that provides a mocked time function for deterministic testing."""
    with patch("time.time") as mock_time:
        mock_time.return_value = 1609459200.0  # 2021-01-01 00:00:00 UTC
        yield mock_time


@pytest.fixture
def mock_uuid():
    """Fixture that provides a mocked uuid function for deterministic testing."""
    with patch("uuid.uuid4") as mock_uuid:
        mock_uuid.return_value = "00000000-0000-0000-0000-000000000000"
        yield mock_uuid