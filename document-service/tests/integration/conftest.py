import os
import json
import uuid
import pytest
import tempfile
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple, Optional, Callable
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer

# Import moto for S3 mocking
from moto import mock_s3
import boto3

# Import pika for RabbitMQ testing
import pika
from pika.exceptions import AMQPConnectionError

# Import application components
from document_service.app import create_app
from document_service.config import app_config, rabbitmq_config, s3_config, model_config
from document_service.models import DocumentClassifier, SVMClassifier, RandomForestClassifier as DocRFClassifier
from document_service.services import QueueService, StorageService, ClassificationService, DocumentRoutingService
from document_service.types import ClassificationResult, ConfidenceScore, StorageMetadata


# ============================================================================
# Constants and Test Data
# ============================================================================

TEST_EXCHANGE = "test.mca.documents"
TEST_QUEUE = "test.document-processing"
TEST_RESULT_QUEUE = "test.data-extraction"
TEST_BUCKET = "test-mca-documents"
TEST_DOCUMENT_TYPES = [
    "application_form",
    "bank_statement",
    "tax_return",
    "identity_document",
    "business_license",
    "utility_bill",
    "financial_statement",
    "invoice",
    "unknown"
]


# ============================================================================
# Fixture Utilities
# ============================================================================

def generate_test_document_content(doc_type: str) -> bytes:
    """Generate test document content based on document type."""
    # In a real implementation, this would generate more realistic document content
    # For testing purposes, we'll just create text with keywords related to the document type
    content = f"Test document of type {doc_type}\n\n"
    
    if doc_type == "application_form":
        content += "MERCHANT CASH ADVANCE APPLICATION\n"
        content += "Business Name: Test Business LLC\n"
        content += "Owner: John Smith\n"
        content += "Tax ID: 12-3456789\n"
        content += "Requested Amount: $50,000\n"
    elif doc_type == "bank_statement":
        content += "BANK STATEMENT\n"
        content += "Account: 123456789\n"
        content += "Period: 01/01/2023 - 01/31/2023\n"
        content += "Opening Balance: $10,000.00\n"
        content += "Closing Balance: $15,000.00\n"
    elif doc_type == "tax_return":
        content += "FORM 1120 - U.S. CORPORATION INCOME TAX RETURN\n"
        content += "Tax Year: 2022\n"
        content += "Business Name: Test Business LLC\n"
        content += "EIN: 12-3456789\n"
        content += "Total Income: $500,000\n"
    elif doc_type == "identity_document":
        content += "DRIVER LICENSE\n"
        content += "Name: John Smith\n"
        content += "DOB: 01/01/1980\n"
        content += "ID Number: D1234567\n"
        content += "Expiration: 01/01/2025\n"
    elif doc_type == "business_license":
        content += "BUSINESS LICENSE\n"
        content += "License Number: BL-12345\n"
        content += "Business Name: Test Business LLC\n"
        content += "Issue Date: 01/01/2023\n"
        content += "Expiration Date: 12/31/2023\n"
    elif doc_type == "utility_bill":
        content += "UTILITY BILL\n"
        content += "Service Address: 123 Main St\n"
        content += "Account Number: 987654321\n"
        content += "Service Period: 01/01/2023 - 01/31/2023\n"
        content += "Amount Due: $150.00\n"
    elif doc_type == "financial_statement":
        content += "FINANCIAL STATEMENT\n"
        content += "Business Name: Test Business LLC\n"
        content += "Period: Q4 2022\n"
        content += "Revenue: $250,000\n"
        content += "Expenses: $200,000\n"
        content += "Net Income: $50,000\n"
    elif doc_type == "invoice":
        content += "INVOICE\n"
        content += "Invoice Number: INV-12345\n"
        content += "Date: 01/15/2023\n"
        content += "Customer: Sample Customer\n"
        content += "Amount: $1,500.00\n"
    else:  # unknown
        content += "MISCELLANEOUS DOCUMENT\n"
        content += "This document contains miscellaneous information\n"
        content += "that doesn't match any specific document type.\n"
    
    return content.encode('utf-8')


def create_test_message(doc_type: str, doc_id: str = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """Create a test message for document processing."""
    if doc_id is None:
        doc_id = str(uuid.uuid4())
        
    if metadata is None:
        metadata = {}
        
    return {
        "document_id": doc_id,
        "storage_path": f"documents/{doc_id}.pdf",
        "file_name": f"{doc_type}_{doc_id}.pdf",
        "content_type": "application/pdf",
        "size_bytes": 1024 * 10,  # 10KB
        "upload_timestamp": "2023-01-15T12:00:00Z",
        "source": "test",
        "metadata": {
            "original_file_name": f"original_{doc_type}.pdf",
            "email_subject": "Test Document Submission",
            "email_from": "test@example.com",
            "email_received": "2023-01-15T11:55:00Z",
            **metadata
        }
    }


def validate_classification_result(result: Dict[str, Any], doc_type: str = None) -> bool:
    """Validate a classification result message."""
    required_fields = [
        "document_id", "classification", "confidence", "storage_path", 
        "processing_timestamp", "metadata"
    ]
    
    # Check required fields
    for field in required_fields:
        if field not in result:
            return False
    
    # Check classification structure
    if not isinstance(result["classification"], dict):
        return False
        
    if "document_type" not in result["classification"]:
        return False
        
    # Check confidence structure
    if not isinstance(result["confidence"], dict):
        return False
        
    if "score" not in result["confidence"] or not (0 <= result["confidence"]["score"] <= 1):
        return False
        
    # Check specific document type if provided
    if doc_type and result["classification"]["document_type"] != doc_type:
        return False
        
    return True


# ============================================================================
# RabbitMQ Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def rabbitmq_config_test():
    """Return test RabbitMQ configuration."""
    # Override the RabbitMQ configuration for testing
    config = rabbitmq_config.copy()
    config.host = os.environ.get("TEST_RABBITMQ_HOST", "localhost")
    config.port = int(os.environ.get("TEST_RABBITMQ_PORT", "5672"))
    config.username = os.environ.get("TEST_RABBITMQ_USERNAME", "guest")
    config.password = os.environ.get("TEST_RABBITMQ_PASSWORD", "guest")
    config.exchange = TEST_EXCHANGE
    config.queue = TEST_QUEUE
    config.result_queue = TEST_RESULT_QUEUE
    config.use_tls = False  # Disable TLS for testing
    return config


@pytest.fixture
def rabbitmq_connection(rabbitmq_config_test):
    """Create a RabbitMQ connection for testing."""
    # Create connection parameters
    credentials = pika.PlainCredentials(
        rabbitmq_config_test.username,
        rabbitmq_config_test.password
    )
    parameters = pika.ConnectionParameters(
        host=rabbitmq_config_test.host,
        port=rabbitmq_config_test.port,
        credentials=credentials,
        heartbeat=rabbitmq_config_test.heartbeat,
        virtual_host=rabbitmq_config_test.virtual_host,
    )
    
    # Try to establish connection
    try:
        connection = pika.BlockingConnection(parameters)
        yield connection
        connection.close()
    except AMQPConnectionError:
        # If we can't connect to RabbitMQ, use a mock connection instead
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        yield mock_connection


@pytest.fixture
def rabbitmq_channel(rabbitmq_connection):
    """Create a RabbitMQ channel for testing."""
    channel = rabbitmq_connection.channel()
    
    # Declare test exchange and queues
    channel.exchange_declare(
        exchange=TEST_EXCHANGE,
        exchange_type='fanout',
        durable=True
    )
    
    channel.queue_declare(
        queue=TEST_QUEUE,
        durable=True
    )
    
    channel.queue_declare(
        queue=TEST_RESULT_QUEUE,
        durable=True
    )
    
    channel.queue_bind(
        queue=TEST_QUEUE,
        exchange=TEST_EXCHANGE,
        routing_key=''
    )
    
    channel.queue_bind(
        queue=TEST_RESULT_QUEUE,
        exchange=TEST_EXCHANGE,
        routing_key=''
    )
    
    # Purge queues to ensure clean state
    channel.queue_purge(queue=TEST_QUEUE)
    channel.queue_purge(queue=TEST_RESULT_QUEUE)
    
    yield channel


@pytest.fixture
def queue_service(rabbitmq_config_test, rabbitmq_connection):
    """Create a QueueService instance for testing."""
    service = QueueService(rabbitmq_config_test)
    
    # Patch the connection method to return our test connection
    original_connect = service.connect
    service.connect = lambda: rabbitmq_connection
    
    yield service
    
    # Restore original connect method
    service.connect = original_connect


@pytest.fixture
def publish_test_message(rabbitmq_channel):
    """Fixture to publish a test message to the test queue."""
    def _publish(message: Dict[str, Any]):
        rabbitmq_channel.basic_publish(
            exchange=TEST_EXCHANGE,
            routing_key='',
            body=json.dumps(message).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=2,  # make message persistent
                content_type='application/json'
            )
        )
    return _publish


@pytest.fixture
def consume_test_message(rabbitmq_channel):
    """Fixture to consume a test message from the result queue."""
    def _consume(timeout: int = 5):
        method_frame, header_frame, body = rabbitmq_channel.basic_get(
            queue=TEST_RESULT_QUEUE,
            auto_ack=True
        )
        
        if method_frame:
            return json.loads(body.decode('utf-8'))
        return None
    return _consume


# ============================================================================
# S3 Storage Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def s3_mock():
    """Create a mocked S3 service."""
    with mock_s3():
        yield boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )


@pytest.fixture
def s3_bucket(s3_mock):
    """Create a test S3 bucket."""
    s3_mock.create_bucket(Bucket=TEST_BUCKET)
    return TEST_BUCKET


@pytest.fixture
def s3_config_test(s3_bucket):
    """Return test S3 configuration."""
    # Override the S3 configuration for testing
    config = s3_config.copy()
    config.endpoint_url = None  # Use moto's endpoint
    config.region = 'us-east-1'
    config.bucket = s3_bucket
    config.access_key_id = 'test'
    config.secret_access_key = 'test'
    config.use_ssl = False
    return config


@pytest.fixture
def storage_service(s3_config_test, s3_mock):
    """Create a StorageService instance for testing."""
    service = StorageService(s3_config_test)
    
    # Patch the client creation to use our mocked S3 client
    service._client = s3_mock
    
    return service


@pytest.fixture
def upload_test_document(storage_service):
    """Fixture to upload a test document to S3."""
    def _upload(doc_type: str, doc_id: str = None, metadata: Dict[str, Any] = None) -> Tuple[str, str]:
        if doc_id is None:
            doc_id = str(uuid.uuid4())
            
        if metadata is None:
            metadata = {}
            
        content = generate_test_document_content(doc_type)
        storage_path = f"documents/{doc_id}.pdf"
        
        storage_service.upload_document(
            storage_path=storage_path,
            content=content,
            content_type="application/pdf",
            metadata={
                "document_type": doc_type,
                "test": "true",
                **metadata
            }
        )
        
        return doc_id, storage_path
    return _upload


# ============================================================================
# Classification Model Fixtures
# ============================================================================

@pytest.fixture
def mock_svm_classifier():
    """Create a mock SVM classifier for testing."""
    classifier = MagicMock(spec=SVMClassifier)
    
    # Configure the mock to return predictable results
    def predict_mock(document, **kwargs):
        # Extract document type from the document content or metadata
        doc_type = "unknown"
        for t in TEST_DOCUMENT_TYPES:
            if t in str(document).lower():
                doc_type = t
                break
                
        return doc_type
        
    def predict_proba_mock(document, **kwargs):
        doc_type = predict_mock(document)
        
        # Create a probability distribution with high confidence for the predicted type
        probas = {t: 0.01 for t in TEST_DOCUMENT_TYPES}
        probas[doc_type] = 0.92  # 92% confidence for the predicted type
        
        return probas
    
    classifier.predict.side_effect = predict_mock
    classifier.predict_proba.side_effect = predict_proba_mock
    
    return classifier


@pytest.fixture
def mock_rf_classifier():
    """Create a mock Random Forest classifier for testing."""
    classifier = MagicMock(spec=DocRFClassifier)
    
    # Configure the mock to return predictable results
    def predict_mock(document, **kwargs):
        # Extract document type from the document content or metadata
        doc_type = "unknown"
        for t in TEST_DOCUMENT_TYPES:
            if t in str(document).lower():
                doc_type = t
                break
                
        return doc_type
        
    def predict_proba_mock(document, **kwargs):
        doc_type = predict_mock(document)
        
        # Create a probability distribution with high confidence for the predicted type
        probas = {t: 0.01 for t in TEST_DOCUMENT_TYPES}
        probas[doc_type] = 0.95  # 95% confidence for the predicted type
        
        return probas
    
    classifier.predict.side_effect = predict_mock
    classifier.predict_proba.side_effect = predict_proba_mock
    
    return classifier


@pytest.fixture
def document_classifier(mock_svm_classifier, mock_rf_classifier):
    """Create a DocumentClassifier instance for testing."""
    classifier = MagicMock(spec=DocumentClassifier)
    
    # Configure the mock to return predictable results
    def classify_mock(document_content, metadata=None, **kwargs):
        # Extract document type from the document content or metadata
        doc_type = "unknown"
        content_str = document_content.decode('utf-8') if isinstance(document_content, bytes) else str(document_content)
        
        for t in TEST_DOCUMENT_TYPES:
            if t in content_str.lower():
                doc_type = t
                break
                
        # If metadata contains document_type, use that instead
        if metadata and "document_type" in metadata:
            doc_type = metadata["document_type"]
            
        # Create a classification result with high confidence
        confidence = ConfidenceScore(
            score=0.98,  # 98% confidence
            model="ensemble",
            threshold=0.7,
            details={
                "svm_confidence": 0.92,
                "rf_confidence": 0.95,
                "ensemble_weight": 0.5
            }
        )
        
        result = ClassificationResult(
            document_type=doc_type,
            confidence=confidence,
            metadata={
                "page_count": 1,
                "has_signature": True if "application_form" in doc_type else False,
                "processing_time_ms": 150,
                "feature_count": 1024
            }
        )
        
        return result
    
    classifier.classify.side_effect = classify_mock
    
    return classifier


@pytest.fixture
def classification_service(document_classifier, storage_service):
    """Create a ClassificationService instance for testing."""
    service = ClassificationService(
        classifier=document_classifier,
        storage_service=storage_service
    )
    return service


@pytest.fixture
def document_routing_service():
    """Create a DocumentRoutingService instance for testing."""
    service = DocumentRoutingService()
    return service


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def app():
    """Create a test application instance."""
    return create_app(testing=True)


@pytest.fixture
def api_client(app):
    """Create a test client for the API."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers for API requests."""
    return {
        "Authorization": "Bearer test_token",
        "Content-Type": "application/json"
    }


# ============================================================================
# Test Document Fixtures
# ============================================================================

@pytest.fixture
def test_document_factory():
    """Factory fixture to create test documents of various types."""
    def _create_document(doc_type: str, content: str = None) -> Tuple[str, bytes]:
        doc_id = str(uuid.uuid4())
        
        if content is None:
            content = generate_test_document_content(doc_type)
        elif isinstance(content, str):
            content = content.encode('utf-8')
            
        return doc_id, content
    return _create_document


@pytest.fixture
def test_documents():
    """Create a set of test documents for all document types."""
    documents = {}
    for doc_type in TEST_DOCUMENT_TYPES:
        doc_id = f"test-{doc_type}-{uuid.uuid4()}"
        content = generate_test_document_content(doc_type)
        documents[doc_type] = (doc_id, content)
    return documents


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def integration_test_setup(rabbitmq_channel, s3_bucket, upload_test_document, publish_test_message, consume_test_message):
    """Set up a complete integration test environment."""
    # Create a dictionary to hold all the test components
    test_env = {
        "rabbitmq_channel": rabbitmq_channel,
        "s3_bucket": s3_bucket,
        "upload_document": upload_test_document,
        "publish_message": publish_test_message,
        "consume_message": consume_test_message,
        "documents": {}
    }
    
    # Upload test documents for each document type
    for doc_type in TEST_DOCUMENT_TYPES:
        doc_id, storage_path = upload_test_document(doc_type)
        test_env["documents"][doc_type] = {
            "id": doc_id,
            "path": storage_path,
            "type": doc_type
        }
    
    return test_env


@pytest.fixture
def complete_service_setup(queue_service, storage_service, classification_service, document_routing_service):
    """Set up all services for integration testing."""
    return {
        "queue_service": queue_service,
        "storage_service": storage_service,
        "classification_service": classification_service,
        "document_routing_service": document_routing_service
    }