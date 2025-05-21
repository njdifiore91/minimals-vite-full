import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, patch

import boto3
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from moto import mock_s3
from pika.exceptions import AMQPConnectionError

from src.api.router import router as api_router
from src.models.base_model import BaseModel
from src.models.document_classifier import DocumentClassifier
from src.models.random_forest_classifier import RandomForestClassifier
from src.models.svm_classifier import SVMClassifier
from src.services.classification_service import ClassificationService
from src.services.document_routing_service import DocumentRoutingService
from src.services.queue_service import QueueService
from src.services.storage_service import StorageService
from src.types.classification import ClassificationResult, ConfidenceScore
from src.types.documents import Document, DocumentMetadata, DocumentType, ProcessingStatus
from src.types.messages import MessagePayload
from src.types.storage import S3ClientConfig, StorageMetadata


# ============================================================================
# API Test Client Fixtures
# ============================================================================

@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI test application with the API router mounted."""
    app = FastAPI(title="Document Service API Test")
    app.include_router(api_router)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


# ============================================================================
# S3 Storage Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """Create a mocked S3 client using moto."""
    with mock_s3():
        s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        # Create test buckets
        s3_client.create_bucket(Bucket='mca-documents-test')
        yield s3_client


@pytest.fixture
def mock_storage_service(mock_s3_client):
    """Create a mocked StorageService with the mock S3 client."""
    config = S3ClientConfig(
        endpoint="http://localhost:4566",
        bucket="mca-documents-test",
        region="us-east-1",
        access_key="test",
        secret_key="test"
    )
    
    storage_service = StorageService(config)
    storage_service._client = mock_s3_client
    return storage_service


@pytest.fixture
def upload_test_document(mock_storage_service):
    """Helper fixture to upload a test document to the mock S3 storage."""
    def _upload_document(document_id: str, content: bytes, metadata: Dict[str, Any]) -> str:
        key = f"documents/{document_id}.pdf"
        mock_storage_service._client.put_object(
            Bucket="mca-documents-test",
            Key=key,
            Body=content,
            Metadata=metadata
        )
        return key
    
    return _upload_document


# ============================================================================
# RabbitMQ Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_rabbitmq_channel():
    """Create a mocked RabbitMQ channel."""
    channel = MagicMock()
    channel.basic_publish = MagicMock()
    channel.basic_consume = MagicMock()
    channel.basic_ack = MagicMock()
    channel.basic_nack = MagicMock()
    channel.queue_declare = MagicMock(return_value=MagicMock(method=MagicMock(queue="test-queue")))
    return channel


@pytest.fixture
def mock_rabbitmq_connection(mock_rabbitmq_channel):
    """Create a mocked RabbitMQ connection."""
    connection = MagicMock()
    connection.channel = MagicMock(return_value=mock_rabbitmq_channel)
    connection.is_closed = False
    connection.is_open = True
    
    # Add method to simulate connection failure
    def close_connection():
        connection.is_closed = True
        connection.is_open = False
    
    connection.close_connection = close_connection
    return connection


@pytest.fixture
def mock_queue_service(mock_rabbitmq_connection, mock_rabbitmq_channel):
    """Create a mocked QueueService with the mock RabbitMQ connection."""
    with patch('src.services.queue_service.pika.BlockingConnection', 
               return_value=mock_rabbitmq_connection):
        queue_service = QueueService()
        queue_service._connection = mock_rabbitmq_connection
        queue_service._channel = mock_rabbitmq_channel
        queue_service._is_connected = True
        
        # Mock the publish method
        original_publish = queue_service.publish
        
        def mock_publish(message: Dict[str, Any], routing_key: str):
            if not queue_service._is_connected:
                raise AMQPConnectionError("Connection is closed")
            return original_publish(message, routing_key)
        
        queue_service.publish = mock_publish
        
        yield queue_service


@pytest.fixture
def simulate_rabbitmq_message():
    """Helper fixture to simulate receiving a RabbitMQ message."""
    def _create_message(document_id: str, document_type: str, content: bytes = b"test content") -> MessagePayload:
        return MessagePayload(
            document_id=document_id,
            application_id=f"app-{uuid.uuid4()}",
            document_type=document_type,
            source="email",
            received_at=datetime.now().isoformat(),
            metadata={
                "filename": f"{document_type.lower().replace('_', '-')}.pdf",
                "size": len(content),
                "content_type": "application/pdf",
                "sender": "test@example.com"
            }
        )
    
    return _create_message


# ============================================================================
# Document Classification Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_svm_classifier():
    """Create a mocked SVM classifier."""
    classifier = MagicMock(spec=SVMClassifier)
    classifier.predict.return_value = DocumentType.APPLICATION
    classifier.predict_proba.return_value = {
        DocumentType.APPLICATION: 0.85,
        DocumentType.BANK_STATEMENT: 0.05,
        DocumentType.TAX_RETURN: 0.05,
        DocumentType.PAY_STUB: 0.03,
        DocumentType.ID_DOCUMENT: 0.02
    }
    return classifier


@pytest.fixture
def mock_random_forest_classifier():
    """Create a mocked Random Forest classifier."""
    classifier = MagicMock(spec=RandomForestClassifier)
    classifier.predict.return_value = DocumentType.APPLICATION
    classifier.predict_proba.return_value = {
        DocumentType.APPLICATION: 0.90,
        DocumentType.BANK_STATEMENT: 0.04,
        DocumentType.TAX_RETURN: 0.03,
        DocumentType.PAY_STUB: 0.02,
        DocumentType.ID_DOCUMENT: 0.01
    }
    return classifier


@pytest.fixture
def mock_document_classifier(mock_svm_classifier, mock_random_forest_classifier):
    """Create a mocked DocumentClassifier with configurable accuracy."""
    classifier = MagicMock(spec=DocumentClassifier)
    classifier.svm_classifier = mock_svm_classifier
    classifier.random_forest_classifier = mock_random_forest_classifier
    
    def classify_with_confidence(document: Document, confidence: float = 0.95) -> ClassificationResult:
        doc_type = DocumentType.APPLICATION
        confidence_scores = {
            DocumentType.APPLICATION: confidence,
            DocumentType.BANK_STATEMENT: (1.0 - confidence) * 0.4,
            DocumentType.TAX_RETURN: (1.0 - confidence) * 0.3,
            DocumentType.PAY_STUB: (1.0 - confidence) * 0.2,
            DocumentType.ID_DOCUMENT: (1.0 - confidence) * 0.1
        }
        return ClassificationResult(
            document_id=document.metadata.document_id,
            document_type=doc_type,
            confidence=ConfidenceScore(
                overall=confidence,
                scores=confidence_scores
            ),
            metadata={
                "classifier": "ensemble",
                "processing_time_ms": 120,
                "feature_count": 1024
            }
        )
    
    classifier.classify.side_effect = classify_with_confidence
    return classifier


@pytest.fixture
def mock_classification_service(mock_document_classifier):
    """Create a mocked ClassificationService with the mock document classifier."""
    service = MagicMock(spec=ClassificationService)
    service._classifier = mock_document_classifier
    
    def classify_document(document: Document, min_confidence: float = 0.7) -> ClassificationResult:
        return mock_document_classifier.classify(document)
    
    service.classify_document.side_effect = classify_document
    return service


@pytest.fixture
def mock_document_routing_service():
    """Create a mocked DocumentRoutingService."""
    service = MagicMock(spec=DocumentRoutingService)
    
    def route_document(classification_result: ClassificationResult) -> Dict[str, Any]:
        return {
            "document_id": classification_result.document_id,
            "document_type": classification_result.document_type,
            "confidence": classification_result.confidence.overall,
            "routing": {
                "queue": "data-extraction",
                "processor": "ocr-service",
                "priority": "high" if classification_result.confidence.overall > 0.9 else "normal"
            }
        }
    
    service.route_document.side_effect = route_document
    return service


# ============================================================================
# Test Document Generation Fixtures
# ============================================================================

@pytest.fixture
def create_test_document():
    """Helper fixture to create test Document objects with various types."""
    def _create_document(doc_type: Union[DocumentType, str] = DocumentType.APPLICATION, 
                        content: bytes = b"test content",
                        processing_status: ProcessingStatus = ProcessingStatus.RECEIVED) -> Document:
        if isinstance(doc_type, str):
            doc_type = DocumentType(doc_type)
            
        document_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        
        metadata = DocumentMetadata(
            document_id=document_id,
            application_id=application_id,
            filename=f"{doc_type.name.lower().replace('_', '-')}.pdf",
            content_type="application/pdf",
            size=len(content),
            upload_date=datetime.now().isoformat(),
            source="test",
            md5_hash="test-hash-value"
        )
        
        return Document(
            metadata=metadata,
            content=content,
            processing_status=processing_status,
            classification=None  # Will be filled by classification service
        )
    
    return _create_document


@pytest.fixture
def create_test_documents():
    """Helper fixture to create multiple test documents of various types."""
    def _create_documents(count: int = 5) -> List[Document]:
        documents = []
        doc_types = list(DocumentType)
        
        for i in range(count):
            doc_type = doc_types[i % len(doc_types)]
            content = f"test content for document {i}".encode()
            documents.append(create_test_document()(doc_type, content))
            
        return documents
    
    return _create_documents


# ============================================================================
# API Request and Response Validation Fixtures
# ============================================================================

@pytest.fixture
def validate_response_schema():
    """Helper fixture to validate API response schemas."""
    def _validate_schema(response_data: Dict[str, Any], expected_schema: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors = []
        
        def _validate_object(data, schema, path=""):
            for key, expected_type in schema.items():
                current_path = f"{path}.{key}" if path else key
                
                if key not in data:
                    errors.append(f"Missing required field: {current_path}")
                    continue
                    
                if isinstance(expected_type, dict):
                    if not isinstance(data[key], dict):
                        errors.append(f"Field {current_path} should be an object but got {type(data[key]).__name__}")
                    else:
                        _validate_object(data[key], expected_type, current_path)
                elif isinstance(expected_type, list) and len(expected_type) == 1:
                    if not isinstance(data[key], list):
                        errors.append(f"Field {current_path} should be an array but got {type(data[key]).__name__}")
                    else:
                        for i, item in enumerate(data[key]):
                            _validate_object({"item": item}, {"item": expected_type[0]}, f"{current_path}[{i}]")
                else:
                    if not isinstance(data[key], expected_type):
                        errors.append(
                            f"Field {current_path} should be {expected_type.__name__} "
                            f"but got {type(data[key]).__name__}"
                        )
        
        _validate_object(response_data, expected_schema)
        return len(errors) == 0, errors
    
    return _validate_schema


@pytest.fixture
def api_request():
    """Helper fixture to make API requests with proper error handling."""
    def _make_request(client: TestClient, method: str, url: str, 
                     json_data: Optional[Dict[str, Any]] = None,
                     headers: Optional[Dict[str, str]] = None,
                     expected_status_code: int = 200) -> Dict[str, Any]:
        methods = {
            "get": client.get,
            "post": client.post,
            "put": client.put,
            "delete": client.delete,
            "patch": client.patch
        }
        
        if method.lower() not in methods:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
        request_method = methods[method.lower()]
        response = request_method(url, json=json_data, headers=headers)
        
        assert response.status_code == expected_status_code, \
            f"Expected status code {expected_status_code} but got {response.status_code}. Response: {response.text}"
            
        if response.status_code != 204:  # No content
            return response.json()
        return {}
    
    return _make_request


# ============================================================================
# Authentication Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_auth_token():
    """Generate a mock JWT auth token for testing authenticated endpoints."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJuYW1lIjoiVGVzdCBVc2VyIiwicm9sZXMiOlsiT3BlcmF0aW9ucyBTdGFmZiJdLCJpYXQiOjE2MTYxNjI4MDAsImV4cCI6MTYxNjE2NjQwMH0.8Nis5cjJQz8cgQUQgS7JYDQjRGxnlZPZ1_WY-J-YWWQ"


@pytest.fixture
def auth_headers(mock_auth_token):
    """Create authorization headers with the mock JWT token."""
    return {"Authorization": f"Bearer {mock_auth_token}"}