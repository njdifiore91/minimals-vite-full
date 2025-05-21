import os
import json
import pytest
import tempfile
import boto3
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from moto import mock_s3
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# Import Document Service modules
# These imports will be available when the actual service is implemented
try:
    from src.config import app_config, s3_config, rabbitmq_config, model_config
    from src.models import DocumentClassifier, SVMClassifier, RandomForestClassifier
    from src.services import QueueService, StorageService, ClassificationService
    from src.types import Document, DocumentType, DocumentMetadata, ClassificationResult
    from src.app import Application
except ImportError:
    # Create mock classes for testing when imports aren't available
    class MockConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    app_config = MockConfig(service_name="document-service", version="1.0.0")
    s3_config = MockConfig(bucket_name="mca-documents-test", endpoint_url="http://localhost:4566")
    rabbitmq_config = MockConfig(host="localhost", port=5672, exchange="mca.documents", queue="document-processing")
    model_config = MockConfig(model_path="./models", confidence_threshold=0.8)

    class DocumentType:
        APPLICATION = "APPLICATION"
        TAX_RETURN = "TAX_RETURN"
        BANK_STATEMENT = "BANK_STATEMENT"
        PAY_STUB = "PAY_STUB"
        ID_DOCUMENT = "ID_DOCUMENT"
        OTHER = "OTHER"

    class Document:
        def __init__(self, id, content, metadata, doc_type=None):
            self.id = id
            self.content = content
            self.metadata = metadata
            self.doc_type = doc_type

    class DocumentMetadata:
        def __init__(self, filename, size, content_type, created_at=None):
            self.filename = filename
            self.size = size
            self.content_type = content_type
            self.created_at = created_at

    class ClassificationResult:
        def __init__(self, doc_type, confidence, features=None):
            self.doc_type = doc_type
            self.confidence = confidence
            self.features = features or {}


# ===== Configuration Fixtures =====

@pytest.fixture
def test_config():
    """Provides a test configuration with predefined values."""
    return {
        "service": {
            "name": "document-service-test",
            "version": "1.0.0-test",
            "port": 8080,
            "environment": "test"
        },
        "s3": {
            "endpoint_url": "http://localhost:4566",
            "bucket_name": "mca-documents-test",
            "region": "us-east-1",
            "use_ssl": False,
            "encryption": "AES256"
        },
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "username": "guest",
            "password": "guest",
            "exchange": "mca.documents.test",
            "queue": "document-processing-test",
            "routing_key": "document.classify",
            "use_tls": False
        },
        "model": {
            "model_path": "./test_models",
            "confidence_threshold": 0.8,
            "feature_extraction": {
                "max_features": 1000,
                "ngram_range": [1, 2]
            },
            "svm": {
                "C": 1.0,
                "kernel": "linear",
                "probability": True
            },
            "random_forest": {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            }
        },
        "logging": {
            "level": "DEBUG",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    }


@pytest.fixture
def app_config_fixture(test_config):
    """Creates a mock application configuration for testing."""
    with patch("src.config.app_config", create=True) as mock_config:
        for key, value in test_config["service"].items():
            setattr(mock_config, key, value)
        yield mock_config


@pytest.fixture
def s3_config_fixture(test_config):
    """Creates a mock S3 configuration for testing."""
    with patch("src.config.s3_config", create=True) as mock_config:
        for key, value in test_config["s3"].items():
            setattr(mock_config, key, value)
        yield mock_config


@pytest.fixture
def rabbitmq_config_fixture(test_config):
    """Creates a mock RabbitMQ configuration for testing."""
    with patch("src.config.rabbitmq_config", create=True) as mock_config:
        for key, value in test_config["rabbitmq"].items():
            setattr(mock_config, key, value)
        yield mock_config


@pytest.fixture
def model_config_fixture(test_config):
    """Creates a mock model configuration for testing."""
    with patch("src.config.model_config", create=True) as mock_config:
        for key, value in test_config["model"].items():
            setattr(mock_config, key, value)
        yield mock_config


# ===== S3 Storage Fixtures =====

@pytest.fixture
def s3_client():
    """Creates a mocked S3 client using moto."""
    with mock_s3():
        s3 = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="test",
            aws_secret_access_key="test",
            endpoint_url="http://localhost:4566"
        )
        # Create the test bucket
        s3.create_bucket(Bucket="mca-documents-test")
        yield s3


@pytest.fixture
def storage_service(s3_client, s3_config_fixture):
    """Creates a mocked StorageService instance for testing."""
    try:
        service = StorageService(s3_config_fixture)
        # Override the S3 client with our mocked one
        service._client = s3_client
        yield service
    except NameError:
        # If StorageService is not available, create a mock
        mock_service = MagicMock()
        mock_service.download_document.return_value = b"test document content"
        mock_service.upload_document.return_value = "s3://mca-documents-test/test-document.pdf"
        mock_service.get_document_metadata.return_value = {
            "filename": "test-document.pdf",
            "size": 1024,
            "content_type": "application/pdf",
            "created_at": "2023-01-01T00:00:00Z"
        }
        yield mock_service


@pytest.fixture
def upload_test_documents(s3_client):
    """Uploads test documents to the mocked S3 bucket."""
    test_documents = {
        "application.pdf": (b"test application content", "application/pdf", DocumentType.APPLICATION),
        "tax_return.pdf": (b"test tax return content", "application/pdf", DocumentType.TAX_RETURN),
        "bank_statement.pdf": (b"test bank statement content", "application/pdf", DocumentType.BANK_STATEMENT),
        "pay_stub.pdf": (b"test pay stub content", "application/pdf", DocumentType.PAY_STUB),
        "id_document.jpg": (b"test id document content", "image/jpeg", DocumentType.ID_DOCUMENT),
        "unknown.txt": (b"test unknown content", "text/plain", DocumentType.OTHER)
    }
    
    uploaded_docs = {}
    for filename, (content, content_type, doc_type) in test_documents.items():
        s3_client.put_object(
            Bucket="mca-documents-test",
            Key=filename,
            Body=content,
            ContentType=content_type,
            Metadata={"document_type": doc_type}
        )
        uploaded_docs[filename] = {
            "content": content,
            "content_type": content_type,
            "document_type": doc_type,
            "s3_key": filename
        }
    
    return uploaded_docs


# ===== RabbitMQ Fixtures =====

@pytest.fixture
def rabbitmq_connection():
    """Creates a mocked RabbitMQ connection for testing."""
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_connection.channel.return_value = mock_channel
    
    # Configure the mock channel to simulate RabbitMQ behavior
    mock_channel.exchange_declare.return_value = None
    mock_channel.queue_declare.return_value = MagicMock(method=MagicMock(queue="document-processing-test"))
    mock_channel.queue_bind.return_value = None
    
    return mock_connection


@pytest.fixture
def queue_service(rabbitmq_connection, rabbitmq_config_fixture):
    """Creates a mocked QueueService instance for testing."""
    try:
        with patch("pika.BlockingConnection", return_value=rabbitmq_connection):
            service = QueueService(rabbitmq_config_fixture)
            yield service
    except NameError:
        # If QueueService is not available, create a mock
        mock_service = MagicMock()
        mock_service.connection = rabbitmq_connection
        mock_service.channel = rabbitmq_connection.channel()
        
        # Configure the mock service to simulate message handling
        def publish_message(message, routing_key):
            return True
        
        def consume_messages(callback, queue_name=None):
            # Simulate message consumption by calling the callback with a test message
            test_message = {
                "document_id": "test-doc-123",
                "s3_key": "application.pdf",
                "metadata": {
                    "filename": "application.pdf",
                    "size": 1024,
                    "content_type": "application/pdf"
                }
            }
            callback(test_message)
            return True
        
        mock_service.publish_message.side_effect = publish_message
        mock_service.consume_messages.side_effect = consume_messages
        yield mock_service


# ===== Document Classification Model Fixtures =====

@pytest.fixture
def mock_svm_classifier():
    """Creates a mocked SVM classifier for testing."""
    try:
        with patch.object(SVMClassifier, "__init__", return_value=None):
            classifier = SVMClassifier()
            classifier.fit = MagicMock(return_value=classifier)
            classifier.predict = MagicMock(return_value=[DocumentType.APPLICATION])
            classifier.predict_proba = MagicMock(return_value=np.array([[0.1, 0.8, 0.1, 0.0, 0.0, 0.0]]))
            yield classifier
    except NameError:
        # If SVMClassifier is not available, create a mock
        mock_classifier = MagicMock()
        mock_classifier.fit.return_value = mock_classifier
        mock_classifier.predict.return_value = [DocumentType.APPLICATION]
        mock_classifier.predict_proba.return_value = np.array([[0.1, 0.8, 0.1, 0.0, 0.0, 0.0]])
        yield mock_classifier


@pytest.fixture
def mock_random_forest_classifier():
    """Creates a mocked Random Forest classifier for testing."""
    try:
        with patch.object(RandomForestClassifier, "__init__", return_value=None):
            classifier = RandomForestClassifier()
            classifier.fit = MagicMock(return_value=classifier)
            classifier.predict = MagicMock(return_value=[DocumentType.APPLICATION])
            classifier.predict_proba = MagicMock(return_value=np.array([[0.05, 0.85, 0.1, 0.0, 0.0, 0.0]]))
            yield classifier
    except NameError:
        # If RandomForestClassifier is not available, create a mock
        mock_classifier = MagicMock()
        mock_classifier.fit.return_value = mock_classifier
        mock_classifier.predict.return_value = [DocumentType.APPLICATION]
        mock_classifier.predict_proba.return_value = np.array([[0.05, 0.85, 0.1, 0.0, 0.0, 0.0]])
        yield mock_classifier


@pytest.fixture
def document_classifier(mock_svm_classifier, mock_random_forest_classifier, model_config_fixture):
    """Creates a mocked DocumentClassifier instance for testing."""
    try:
        with patch.object(DocumentClassifier, "__init__", return_value=None):
            classifier = DocumentClassifier()
            classifier.svm_classifier = mock_svm_classifier
            classifier.rf_classifier = mock_random_forest_classifier
            classifier.classify_document = MagicMock(return_value=ClassificationResult(
                doc_type=DocumentType.APPLICATION,
                confidence=0.85,
                features={"text_length": 1024, "keyword_matches": 5}
            ))
            yield classifier
    except NameError:
        # If DocumentClassifier is not available, create a mock
        mock_classifier = MagicMock()
        mock_classifier.classify_document.return_value = MagicMock(
            doc_type=DocumentType.APPLICATION,
            confidence=0.85,
            features={"text_length": 1024, "keyword_matches": 5}
        )
        yield mock_classifier


@pytest.fixture
def classification_service(document_classifier, storage_service):
    """Creates a mocked ClassificationService instance for testing."""
    try:
        service = ClassificationService(document_classifier, storage_service)
        yield service
    except NameError:
        # If ClassificationService is not available, create a mock
        mock_service = MagicMock()
        mock_service.classify_document.return_value = ClassificationResult(
            doc_type=DocumentType.APPLICATION,
            confidence=0.85,
            features={"text_length": 1024, "keyword_matches": 5}
        )
        yield mock_service


# ===== Test Document Fixtures =====

@pytest.fixture
def test_documents():
    """Provides a set of test documents with different types."""
    documents = {
        "application": Document(
            id="test-app-123",
            content=b"This is a merchant cash advance application form.",
            metadata=DocumentMetadata(
                filename="application.pdf",
                size=1024,
                content_type="application/pdf"
            ),
            doc_type=DocumentType.APPLICATION
        ),
        "tax_return": Document(
            id="test-tax-123",
            content=b"This is a tax return document with financial information.",
            metadata=DocumentMetadata(
                filename="tax_return.pdf",
                size=2048,
                content_type="application/pdf"
            ),
            doc_type=DocumentType.TAX_RETURN
        ),
        "bank_statement": Document(
            id="test-bank-123",
            content=b"This is a bank statement showing transaction history.",
            metadata=DocumentMetadata(
                filename="bank_statement.pdf",
                size=1536,
                content_type="application/pdf"
            ),
            doc_type=DocumentType.BANK_STATEMENT
        ),
        "pay_stub": Document(
            id="test-pay-123",
            content=b"This is a pay stub showing salary information.",
            metadata=DocumentMetadata(
                filename="pay_stub.pdf",
                size=512,
                content_type="application/pdf"
            ),
            doc_type=DocumentType.PAY_STUB
        ),
        "id_document": Document(
            id="test-id-123",
            content=b"This is an identification document with personal information.",
            metadata=DocumentMetadata(
                filename="id_document.jpg",
                size=768,
                content_type="image/jpeg"
            ),
            doc_type=DocumentType.ID_DOCUMENT
        ),
        "unknown": Document(
            id="test-unknown-123",
            content=b"This is an unknown document type.",
            metadata=DocumentMetadata(
                filename="unknown.txt",
                size=256,
                content_type="text/plain"
            ),
            doc_type=DocumentType.OTHER
        )
    }
    return documents


@pytest.fixture
def test_document_files(tmpdir):
    """Creates temporary document files for testing."""
    document_files = {}
    
    # Create test files with different content types
    document_types = {
        "application.pdf": (b"This is a merchant cash advance application form.", "application/pdf"),
        "tax_return.pdf": (b"This is a tax return document with financial information.", "application/pdf"),
        "bank_statement.pdf": (b"This is a bank statement showing transaction history.", "application/pdf"),
        "pay_stub.pdf": (b"This is a pay stub showing salary information.", "application/pdf"),
        "id_document.jpg": (b"This is an identification document with personal information.", "image/jpeg"),
        "unknown.txt": (b"This is an unknown document type.", "text/plain")
    }
    
    for filename, (content, content_type) in document_types.items():
        file_path = tmpdir.join(filename)
        with open(file_path, "wb") as f:
            f.write(content)
        document_files[filename] = {
            "path": str(file_path),
            "content": content,
            "content_type": content_type
        }
    
    return document_files


# ===== Application Fixtures =====

@pytest.fixture
def mock_application(app_config_fixture, queue_service, storage_service, classification_service):
    """Creates a mocked Application instance for testing."""
    try:
        app = Application(app_config_fixture)
        app.queue_service = queue_service
        app.storage_service = storage_service
        app.classification_service = classification_service
        yield app
    except NameError:
        # If Application is not available, create a mock
        mock_app = MagicMock()
        mock_app.queue_service = queue_service
        mock_app.storage_service = storage_service
        mock_app.classification_service = classification_service
        mock_app.start = MagicMock(return_value=True)
        mock_app.stop = MagicMock(return_value=True)
        yield mock_app


# ===== Message Fixtures =====

@pytest.fixture
def test_messages():
    """Provides a set of test messages for RabbitMQ testing."""
    messages = {
        "document_received": {
            "document_id": "test-doc-123",
            "s3_key": "application.pdf",
            "metadata": {
                "filename": "application.pdf",
                "size": 1024,
                "content_type": "application/pdf",
                "received_at": "2023-01-01T00:00:00Z"
            }
        },
        "classification_result": {
            "document_id": "test-doc-123",
            "s3_key": "application.pdf",
            "classification": {
                "document_type": DocumentType.APPLICATION,
                "confidence": 0.85,
                "features": {
                    "text_length": 1024,
                    "keyword_matches": 5
                }
            },
            "metadata": {
                "filename": "application.pdf",
                "size": 1024,
                "content_type": "application/pdf",
                "received_at": "2023-01-01T00:00:00Z",
                "classified_at": "2023-01-01T00:00:05Z"
            }
        },
        "error_message": {
            "document_id": "test-doc-456",
            "s3_key": "corrupted.pdf",
            "error": {
                "code": "CLASSIFICATION_ERROR",
                "message": "Failed to classify document: Invalid file format",
                "timestamp": "2023-01-01T00:00:10Z"
            },
            "metadata": {
                "filename": "corrupted.pdf",
                "size": 512,
                "content_type": "application/pdf",
                "received_at": "2023-01-01T00:00:08Z"
            }
        }
    }
    return messages