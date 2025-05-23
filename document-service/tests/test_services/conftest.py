import os
import json
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Optional, Tuple, Callable
import io
import uuid
from datetime import datetime

# Import types from the document service
from src.types.classification import (
    ClassificationResult,
    ConfidenceScore,
    ClassificationModel
)
from src.types.storage import (
    S3ClientConfig,
    StorageMetadata,
    StorageResult
)
from src.types.config import ConfigDict

# Import services for patching
from src.services.queue_service import QueueService
from src.services.storage_service import StorageService
from src.services.classification_service import ClassificationService
from src.services.document_routing_service import DocumentRoutingService

# Import models for mocking
from src.models.document_classifier import DocumentClassifier

# Test constants
TEST_EXCHANGE = "mca.documents"
TEST_QUEUE = "document-processing"
TEST_ROUTING_KEY = "document.classify"
TEST_S3_BUCKET = "mca-documents-test"
TEST_DOCUMENT_TYPES = ["invoice", "bank_statement", "id_document", "tax_form", "business_license"]


@pytest.fixture
def mock_config() -> ConfigDict:
    """Fixture that provides a mock configuration dictionary for testing."""
    return {
        "app": {
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
            "exchange": TEST_EXCHANGE,
            "queue": TEST_QUEUE,
            "routing_key": TEST_ROUTING_KEY,
            "ssl": True,
            "ssl_options": {
                "cert_reqs": 2,  # ssl.CERT_REQUIRED
                "ca_certs": "/path/to/ca_certificate.pem",
                "keyfile": "/path/to/key.pem",
                "certfile": "/path/to/cert.pem"
            },
            "connection_attempts": 3,
            "retry_delay": 5
        },
        "s3": {
            "endpoint_url": "http://localhost:4566",
            "region_name": "us-east-1",
            "bucket_name": TEST_S3_BUCKET,
            "access_key_id": "test",
            "secret_access_key": "test",
            "encryption": {
                "algorithm": "AES256",
                "kms_key_id": None
            }
        },
        "model": {
            "svm": {
                "C": 1.0,
                "kernel": "linear",
                "probability": True
            },
            "random_forest": {
                "n_estimators": 100,
                "max_depth": 10,
                "random_state": 42
            },
            "confidence_threshold": 0.85,
            "low_confidence_threshold": 0.60,
            "model_path": "/tmp/models",
            "feature_extraction": {
                "max_features": 5000,
                "ngram_range": [1, 2]
            }
        }
    }


# RabbitMQ Fixtures
@pytest.fixture
def mock_rabbitmq_connection():
    """Fixture that provides a mock RabbitMQ connection."""
    connection = MagicMock()
    connection.is_open = True
    return connection


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """Fixture that provides a mock RabbitMQ channel."""
    channel = MagicMock()
    mock_rabbitmq_connection.channel.return_value = channel
    return channel


@pytest.fixture
def mock_queue_service(mock_rabbitmq_connection, mock_rabbitmq_channel, mock_config):
    """Fixture that provides a mock QueueService with configurable behavior."""
    with patch('src.services.queue_service.pika.ConnectionParameters'), \
         patch('src.services.queue_service.pika.BlockingConnection',
               return_value=mock_rabbitmq_connection):
        
        service = QueueService(config=mock_config)
        service._channel = mock_rabbitmq_channel
        service._connection = mock_rabbitmq_connection
        
        # Configure the mock channel for common operations
        mock_rabbitmq_channel.exchange_declare.return_value = None
        mock_rabbitmq_channel.queue_declare.return_value = MagicMock(method=MagicMock(queue=TEST_QUEUE))
        mock_rabbitmq_channel.queue_bind.return_value = None
        mock_rabbitmq_channel.basic_consume.return_value = None
        mock_rabbitmq_channel.basic_publish.return_value = None
        mock_rabbitmq_channel.basic_ack.return_value = None
        
        return service


@pytest.fixture
def mock_message_callback():
    """Fixture that provides a mock message callback function."""
    return MagicMock()


@pytest.fixture
def create_test_message():
    """Factory fixture that creates test RabbitMQ messages with configurable content."""
    def _create_message(document_id: str = None, 
                       document_type: str = None, 
                       source_path: str = None,
                       metadata: Dict[str, Any] = None) -> Tuple[MagicMock, Dict[str, Any]]:
        
        document_id = document_id or str(uuid.uuid4())
        document_type = document_type or "unknown"
        source_path = source_path or f"s3://{TEST_S3_BUCKET}/{document_id}.pdf"
        
        message_body = {
            "document_id": document_id,
            "document_type": document_type,
            "source_path": source_path,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {
                "filename": f"{document_id}.pdf",
                "size": 1024,
                "content_type": "application/pdf",
                "pages": 1
            }
        }
        
        # Create a mock message object
        message = MagicMock()
        message.body = json.dumps(message_body).encode('utf-8')
        message.delivery_tag = 1
        
        return message, message_body
    
    return _create_message


# S3 Storage Fixtures
@pytest.fixture
def mock_s3_client():
    """Fixture that provides a mock S3 client."""
    client = MagicMock()
    
    # Configure common S3 operations
    client.get_object.return_value = {
        'Body': io.BytesIO(b'test document content'),
        'ContentLength': 20,
        'ContentType': 'application/pdf',
        'Metadata': {'document_type': 'invoice'}
    }
    
    client.put_object.return_value = {
        'ETag': '"1234567890abcdef"',
        'VersionId': '1'
    }
    
    client.list_objects_v2.return_value = {
        'Contents': [
            {
                'Key': 'test-document-1.pdf',
                'Size': 1024,
                'LastModified': datetime.now()
            }
        ],
        'KeyCount': 1,
        'MaxKeys': 1000,
        'IsTruncated': False
    }
    
    return client


@pytest.fixture
def mock_storage_service(mock_s3_client, mock_config):
    """Fixture that provides a mock StorageService with configurable behavior."""
    with patch('src.services.storage_service.boto3.client', return_value=mock_s3_client):
        service = StorageService(config=mock_config)
        service._s3_client = mock_s3_client
        return service


@pytest.fixture
def create_test_document():
    """Factory fixture that creates test document content with configurable properties."""
    def _create_document(document_id: str = None,
                        document_type: str = None,
                        content: bytes = None,
                        metadata: Dict[str, Any] = None) -> Tuple[bytes, Dict[str, Any]]:
        
        document_id = document_id or str(uuid.uuid4())
        document_type = document_type or "invoice"
        content = content or f"Test document content for {document_id}".encode('utf-8')
        
        doc_metadata = {
            "document_id": document_id,
            "document_type": document_type,
            "filename": f"{document_id}.pdf",
            "content_type": "application/pdf",
            "size": len(content),
            "created_at": datetime.now().isoformat(),
            "pages": 1
        }
        
        if metadata:
            doc_metadata.update(metadata)
        
        return content, doc_metadata
    
    return _create_document


# Classification Fixtures
@pytest.fixture
def mock_document_classifier():
    """Fixture that provides a mock DocumentClassifier with configurable behavior."""
    classifier = MagicMock(spec=DocumentClassifier)
    
    # Configure predict method to return a classification result
    def mock_predict(document_content, **kwargs):
        doc_type = kwargs.get('document_type', 'invoice')
        confidence = kwargs.get('confidence', 0.95)
        
        return {
            'document_type': doc_type,
            'confidence': confidence,
            'features': {
                'text_length': len(document_content) if isinstance(document_content, bytes) else 0,
                'has_tables': True,
                'has_signatures': False
            }
        }
    
    classifier.predict.side_effect = mock_predict
    return classifier


@pytest.fixture
def mock_classification_service(mock_document_classifier, mock_config):
    """Fixture that provides a mock ClassificationService with configurable behavior."""
    service = MagicMock(spec=ClassificationService)
    service.classify_document.return_value = {
        'document_type': 'invoice',
        'confidence': 0.95,
        'classification_time': 0.1,
        'features': {
            'text_length': 1000,
            'has_tables': True,
            'has_signatures': False
        }
    }
    
    # Allow configuring the classification result
    def configure_classification_result(document_type: str, confidence: float):
        service.classify_document.return_value = {
            'document_type': document_type,
            'confidence': confidence,
            'classification_time': 0.1,
            'features': {
                'text_length': 1000,
                'has_tables': True,
                'has_signatures': False
            }
        }
    
    service.configure = configure_classification_result
    return service


# Document Routing Fixtures
@pytest.fixture
def mock_document_routing_service(mock_config):
    """Fixture that provides a mock DocumentRoutingService with configurable behavior."""
    service = MagicMock(spec=DocumentRoutingService)
    
    # Default routing decision
    service.route_document.return_value = {
        'ocr_service': 'standard',
        'priority': 'normal',
        'extraction_config': {
            'extract_tables': True,
            'extract_text': True,
            'extract_signatures': False
        },
        'confidence': 0.95,
        'routing_time': 0.05
    }
    
    # Allow configuring the routing decision
    def configure_routing_decision(document_type: str, confidence: float, ocr_service: str = 'standard'):
        service.route_document.return_value = {
            'ocr_service': ocr_service,
            'priority': 'high' if confidence > 0.9 else 'normal',
            'extraction_config': {
                'extract_tables': document_type in ['invoice', 'bank_statement', 'tax_form'],
                'extract_text': True,
                'extract_signatures': document_type in ['id_document', 'business_license']
            },
            'confidence': confidence,
            'routing_time': 0.05
        }
    
    service.configure = configure_routing_decision
    return service


# Helper Functions
@pytest.fixture
def create_classification_result():
    """Factory fixture that creates classification results with configurable properties."""
    def _create_result(document_id: str = None,
                      document_type: str = None,
                      confidence: float = None,
                      features: Dict[str, Any] = None) -> Dict[str, Any]:
        
        document_id = document_id or str(uuid.uuid4())
        document_type = document_type or "invoice"
        confidence = confidence or 0.95
        
        result = {
            'document_id': document_id,
            'document_type': document_type,
            'confidence': confidence,
            'classification_time': 0.1,
            'timestamp': datetime.now().isoformat(),
            'features': features or {
                'text_length': 1000,
                'has_tables': True,
                'has_signatures': False
            }
        }
        
        return result
    
    return _create_result


@pytest.fixture
def create_routing_result():
    """Factory fixture that creates routing results with configurable properties."""
    def _create_result(document_id: str = None,
                      document_type: str = None,
                      confidence: float = None,
                      ocr_service: str = None) -> Dict[str, Any]:
        
        document_id = document_id or str(uuid.uuid4())
        document_type = document_type or "invoice"
        confidence = confidence or 0.95
        ocr_service = ocr_service or "standard"
        
        result = {
            'document_id': document_id,
            'document_type': document_type,
            'ocr_service': ocr_service,
            'priority': 'high' if confidence > 0.9 else 'normal',
            'extraction_config': {
                'extract_tables': document_type in ['invoice', 'bank_statement', 'tax_form'],
                'extract_text': True,
                'extract_signatures': document_type in ['id_document', 'business_license']
            },
            'confidence': confidence,
            'routing_time': 0.05,
            'timestamp': datetime.now().isoformat()
        }
        
        return result
    
    return _create_result


# Integration Test Fixtures
@pytest.fixture
def mock_document_processing_pipeline(mock_queue_service, mock_storage_service, 
                                      mock_classification_service, mock_document_routing_service):
    """Fixture that provides a complete mock document processing pipeline for integration tests."""
    pipeline = {
        'queue_service': mock_queue_service,
        'storage_service': mock_storage_service,
        'classification_service': mock_classification_service,
        'routing_service': mock_document_routing_service
    }
    
    # Configure the pipeline for a successful flow
    def configure_pipeline_flow(document_type: str = 'invoice', 
                              confidence: float = 0.95,
                              ocr_service: str = 'standard',
                              should_fail: bool = False,
                              failure_stage: str = None):
        
        if should_fail and failure_stage == 'queue':
            mock_queue_service.publish_message.side_effect = Exception("Queue connection error")
        else:
            mock_queue_service.publish_message.return_value = True
        
        if should_fail and failure_stage == 'storage':
            mock_storage_service.get_document.side_effect = Exception("S3 access error")
        else:
            mock_storage_service.get_document.return_value = (b'test document content', {
                'document_type': document_type,
                'filename': 'test.pdf',
                'content_type': 'application/pdf'
            })
        
        if should_fail and failure_stage == 'classification':
            mock_classification_service.classify_document.side_effect = Exception("Classification error")
        else:
            mock_classification_service.configure(document_type, confidence)
        
        if should_fail and failure_stage == 'routing':
            mock_document_routing_service.route_document.side_effect = Exception("Routing error")
        else:
            mock_document_routing_service.configure(document_type, confidence, ocr_service)
    
    pipeline['configure'] = configure_pipeline_flow
    return pipeline