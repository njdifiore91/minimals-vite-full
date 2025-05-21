#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest fixtures for document service tests.

This module provides shared test fixtures for the document service tests, including
mocks for RabbitMQ connections, S3 storage, classification models, and document routing.
These fixtures are used across multiple test files to ensure consistent test setup
and reduce code duplication.

The fixtures in this file support testing the Document Service's ability to:
1. Connect to RabbitMQ with the 'mca.documents' exchange as specified in section 0.1.3
2. Access documents in S3-compatible storage as specified in section 0.1.2
3. Validate service functionality in isolation as specified in section 6.6
4. Maintain 99% data extraction accuracy as specified in section 0.2.6
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union, Callable
from unittest.mock import MagicMock, patch, PropertyMock

import boto3
import pytest
from botocore.exceptions import ClientError
from pika.exceptions import AMQPConnectionError, AMQPChannelError

# Import types and models from the document service
from document_service.types.classification import ClassificationResult, ConfidenceScore, DocumentType
from document_service.types.documents import Document, DocumentMetadata, ProcessingStatus
from document_service.types.messages import MessagePayload
from document_service.types.errors import Result, ServiceError, ErrorCategory


# ===== RabbitMQ Fixtures =====

@pytest.fixture
def mock_rabbitmq_connection():
    """
    Mock RabbitMQ connection for testing.
    
    This fixture provides a mock RabbitMQ connection that can be configured
    to simulate different connection scenarios.
    """
    with patch('pika.BlockingConnection') as mock_connection:
        # Setup mock connection properties
        mock_connection.is_open = True
        mock_connection.is_closed = False
        
        # Mock close method
        mock_connection.close = MagicMock()
        
        yield mock_connection


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """
    Mock RabbitMQ channel for testing.
    
    This fixture provides a mock RabbitMQ channel that can be configured
    to simulate different channel scenarios.
    """
    mock_channel = MagicMock()
    mock_channel.is_open = True
    mock_channel.is_closed = False
    
    # Mock channel methods
    mock_channel.exchange_declare = MagicMock()
    mock_channel.queue_declare = MagicMock(return_value=MagicMock(method=MagicMock(queue='test_queue')))
    mock_channel.queue_bind = MagicMock()
    mock_channel.basic_publish = MagicMock()
    mock_channel.basic_consume = MagicMock()
    mock_channel.basic_ack = MagicMock()
    mock_channel.basic_nack = MagicMock()
    mock_channel.basic_reject = MagicMock()
    mock_channel.close = MagicMock()
    
    # Configure connection to return this channel
    mock_rabbitmq_connection.channel.return_value = mock_channel
    
    yield mock_channel


@pytest.fixture
def mock_rabbitmq_utils():
    """
    Mock RabbitMQ utilities for testing.
    
    This fixture patches the rabbitmq_utils module to provide mock implementations
    of its functions for testing.
    """
    with patch('document_service.utils.rabbitmq_utils') as mock_utils:
        # Mock utility functions
        mock_utils.create_connection = MagicMock()
        mock_utils.create_channel = MagicMock()
        mock_utils.setup_exchange = MagicMock()
        mock_utils.setup_queue = MagicMock()
        mock_utils.bind_queue = MagicMock()
        mock_utils.publish_message = MagicMock(return_value=Result.success(True))
        mock_utils.consume_messages = MagicMock()
        mock_utils.acknowledge_message = MagicMock()
        mock_utils.reject_message = MagicMock()
        mock_utils.close_channel = MagicMock()
        mock_utils.close_connection = MagicMock()
        mock_utils.serialize_message = MagicMock(side_effect=lambda m: json.dumps(m).encode('utf-8'))
        mock_utils.deserialize_message = MagicMock(side_effect=lambda m: json.loads(m.decode('utf-8')))
        
        yield mock_utils


@pytest.fixture
def mock_rabbitmq_config():
    """
    Mock RabbitMQ configuration for testing.
    
    This fixture provides a mock RabbitMQ configuration with test values.
    """
    with patch('document_service.config.rabbitmq_config') as mock_config:
        # Set configuration values
        mock_config.HOST = 'localhost'
        mock_config.PORT = 5672
        mock_config.VIRTUAL_HOST = '/'
        mock_config.USERNAME = 'guest'
        mock_config.PASSWORD = 'guest'
        mock_config.HEARTBEAT = 600
        mock_config.CONNECTION_ATTEMPTS = 3
        mock_config.RETRY_DELAY = 2
        mock_config.USE_SSL = False
        mock_config.SSL_OPTIONS = None
        mock_config.PREFETCH_COUNT = 10
        
        # Set exchange and queue names
        mock_config.EXCHANGE = 'mca.documents'
        mock_config.EXCHANGE_TYPE = 'fanout'
        mock_config.QUEUES = {
            'document_processing': 'document-processing',
            'data_extraction': 'data-extraction',
            'notification': 'notification'
        }
        
        yield mock_config


@pytest.fixture
def mock_rabbitmq_connection_error():
    """
    Mock RabbitMQ connection that raises an error.
    
    This fixture provides a mock RabbitMQ connection that raises an AMQPConnectionError
    when attempting to connect, useful for testing error handling.
    """
    with patch('pika.BlockingConnection') as mock_connection:
        mock_connection.side_effect = AMQPConnectionError('Connection refused')
        yield mock_connection


@pytest.fixture
def mock_rabbitmq_channel_error(mock_rabbitmq_connection):
    """
    Mock RabbitMQ channel that raises an error.
    
    This fixture provides a mock RabbitMQ connection that raises an AMQPChannelError
    when attempting to create a channel, useful for testing error handling.
    """
    mock_rabbitmq_connection.channel.side_effect = AMQPChannelError('Channel closed')
    yield mock_rabbitmq_connection


# ===== S3 Storage Fixtures =====

@pytest.fixture
def mock_s3_client():
    """
    Mock S3 client for testing.
    
    This fixture provides a mock S3 client that can be configured
    to simulate different S3 operations.
    """
    with patch('boto3.client') as mock_client:
        # Create a MagicMock instance for the client
        s3_client = MagicMock()
        
        # Configure boto3.client to return our mock
        mock_client.return_value = s3_client
        
        # Mock S3 methods
        s3_client.put_object = MagicMock(return_value={'ETag': '"mock-etag"'})
        s3_client.get_object = MagicMock(return_value={
            'Body': MagicMock(read=MagicMock(return_value=b'mock document content')),
            'ContentType': 'application/pdf',
            'ContentLength': 100,
            'LastModified': datetime.now(),
            'ETag': '"mock-etag"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {}
        })
        s3_client.head_object = MagicMock(return_value={
            'ContentType': 'application/pdf',
            'ContentLength': 100,
            'LastModified': datetime.now(),
            'ETag': '"mock-etag"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {}
        })
        s3_client.list_objects_v2 = MagicMock(return_value={
            'Contents': [
                {
                    'Key': 'document1.pdf',
                    'Size': 100,
                    'LastModified': datetime.now(),
                    'ETag': '"mock-etag-1"',
                    'StorageClass': 'STANDARD'
                },
                {
                    'Key': 'document2.pdf',
                    'Size': 200,
                    'LastModified': datetime.now(),
                    'ETag': '"mock-etag-2"',
                    'StorageClass': 'STANDARD'
                }
            ]
        })
        s3_client.copy_object = MagicMock(return_value={'CopyObjectResult': {'ETag': '"mock-etag"'}})
        s3_client.delete_object = MagicMock(return_value={})
        s3_client.generate_presigned_url = MagicMock(return_value='https://mock-presigned-url.com')
        s3_client.generate_presigned_post = MagicMock(return_value={
            'url': 'https://mock-bucket.s3.amazonaws.com',
            'fields': {'key': 'mock-key'}
        })
        
        # Add meta attribute for endpoint and region
        s3_client.meta = MagicMock()
        s3_client.meta.endpoint_url = 'https://s3.amazonaws.com'
        s3_client.meta.region_name = 'us-east-1'
        
        yield s3_client


@pytest.fixture
def mock_s3_bucket(mock_s3_client):
    """
    Mock S3 bucket for testing.
    
    This fixture provides a mock S3 bucket configuration for testing.
    """
    return {
        'name': 'mock-bucket',
        'region': 'us-east-1',
        'endpoint_url': 'https://s3.amazonaws.com',
        'access_key': 'mock-access-key',
        'secret_key': 'mock-secret-key'
    }


@pytest.fixture
def mock_s3_error_client():
    """
    Mock S3 client that raises errors for testing error handling.
    
    This fixture provides a mock S3 client that raises ClientError exceptions
    for various operations, useful for testing error handling.
    """
    with patch('boto3.client') as mock_client:
        # Create a MagicMock instance for the client
        s3_client = MagicMock()
        
        # Configure boto3.client to return our mock
        mock_client.return_value = s3_client
        
        # Create a ClientError response
        error_response = {'Error': {'Code': '500', 'Message': 'Internal Server Error'}}
        client_error = ClientError(error_response, 'operation_name')
        
        # Mock S3 methods to raise errors
        s3_client.put_object.side_effect = client_error
        s3_client.get_object.side_effect = client_error
        s3_client.head_object.side_effect = client_error
        s3_client.list_objects_v2.side_effect = client_error
        s3_client.copy_object.side_effect = client_error
        s3_client.delete_object.side_effect = client_error
        s3_client.generate_presigned_url.side_effect = client_error
        s3_client.generate_presigned_post.side_effect = client_error
        
        yield s3_client


@pytest.fixture
def mock_s3_utils(mock_s3_client, mock_s3_bucket):
    """
    Mock S3 utilities for testing.
    
    This fixture patches the s3_utils module to provide mock implementations
    of its functions for testing.
    """
    with patch('document_service.utils.s3_utils') as mock_utils:
        # Mock utility functions
        mock_utils.get_s3_client = MagicMock(return_value=mock_s3_client)
        mock_utils.get_default_s3_client = MagicMock(return_value=mock_s3_client)
        mock_utils.upload_document = MagicMock(return_value={'ETag': '"mock-etag"'})
        mock_utils.download_document = MagicMock(return_value=Result.success(b'mock document content'))
        mock_utils.get_document_metadata = MagicMock(return_value={
            'ContentType': 'application/pdf',
            'ContentLength': 100,
            'LastModified': datetime.now(),
            'ETag': '"mock-etag"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {}
        })
        mock_utils.update_document_metadata = MagicMock(return_value={'CopyObjectResult': {'ETag': '"mock-etag"'}})
        mock_utils.generate_presigned_url = MagicMock(return_value='https://mock-presigned-url.com')
        mock_utils.document_exists = MagicMock(return_value=True)
        mock_utils.get_mime_type = MagicMock(return_value='application/pdf')
        
        yield mock_utils


@pytest.fixture
def mock_s3_config():
    """
    Mock S3 configuration for testing.
    
    This fixture provides a mock S3 configuration with test values.
    """
    with patch('document_service.config.s3_config') as mock_config:
        # Set configuration values
        mock_config.S3_REGION_NAME = 'us-east-1'
        mock_config.S3_ENDPOINT_URL = 'https://s3.amazonaws.com'
        mock_config.S3_ACCESS_KEY_ID = 'mock-access-key'
        mock_config.S3_SECRET_ACCESS_KEY = 'mock-secret-key'
        mock_config.S3_BUCKET_NAME = 'mca-documents-staging'
        mock_config.S3_ENCRYPTION_ENABLED = True
        
        yield mock_config


# ===== Classification Model Fixtures =====

@pytest.fixture
def mock_document_classifier():
    """
    Mock document classifier for testing.
    
    This fixture provides a mock document classifier that can be configured
    to return specific classification results.
    """
    with patch('document_service.models.DocumentClassifier') as mock_classifier_class:
        # Create a MagicMock instance for the classifier
        mock_classifier = MagicMock()
        
        # Configure the class to return our mock instance
        mock_classifier_class.return_value = mock_classifier
        
        # Mock classifier methods
        mock_classifier.classify = MagicMock(return_value=(
            DocumentType.APPLICATION,
            ConfidenceScore(score=0.95, model_name='ensemble', details={'svm': 0.94, 'random_forest': 0.96})
        ))
        mock_classifier.classify_document = MagicMock(return_value=ClassificationResult(
            document_id='mock-doc-id',
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.95, model_name='ensemble', details={'svm': 0.94, 'random_forest': 0.96}),
            requires_review=False,
            prediction_time=datetime.now(),
            feature_importance={}
        ))
        mock_classifier.get_routing_info = MagicMock(return_value={
            'document_id': 'mock-doc-id',
            'document_type': 'APPLICATION',
            'confidence': 0.95,
            'requires_review': False,
            'ocr_pipeline': 'application_form',
            'priority': 'high'
        })
        mock_classifier.extract_features = MagicMock(return_value={})
        
        yield mock_classifier


@pytest.fixture
def configurable_document_classifier():
    """
    Configurable document classifier for testing.
    
    This fixture provides a mock document classifier that can be configured
    to return different classification results based on test requirements.
    """
    with patch('document_service.models.DocumentClassifier') as mock_classifier_class:
        # Create a MagicMock instance for the classifier
        mock_classifier = MagicMock()
        
        # Configure the class to return our mock instance
        mock_classifier_class.return_value = mock_classifier
        
        # Create configurable classification results
        classification_results = {}
        confidence_scores = {}
        routing_info = {}
        
        # Define a function to configure the classifier
        def configure_classifier(document_id, document_type, confidence_score, requires_review=None, routing=None):
            if requires_review is None:
                requires_review = confidence_score < 0.75
                
            # Create confidence score object
            confidence = ConfidenceScore(
                score=confidence_score,
                model_name='ensemble',
                details={'svm': confidence_score - 0.01, 'random_forest': confidence_score + 0.01}
            )
            
            # Store classification result
            classification_results[document_id] = ClassificationResult(
                document_id=document_id,
                document_type=document_type,
                confidence=confidence,
                requires_review=requires_review,
                prediction_time=datetime.now(),
                feature_importance={}
            )
            
            # Store confidence score
            confidence_scores[document_id] = (document_type, confidence)
            
            # Store routing info
            routing_info[document_id] = routing or {
                'document_id': document_id,
                'document_type': document_type.value,
                'confidence': confidence_score,
                'requires_review': requires_review,
                'ocr_pipeline': f'{document_type.value.lower()}_form',
                'priority': 'high' if document_type == DocumentType.APPLICATION else 'normal'
            }
        
        # Configure default classification
        configure_classifier(
            'default',
            DocumentType.APPLICATION,
            0.95,
            False
        )
        
        # Mock classifier methods to use our configurable results
        def mock_classify(document):
            doc_id = getattr(document, 'document_id', getattr(document.metadata, 'document_id', 'default'))
            return confidence_scores.get(doc_id, confidence_scores['default'])
        
        def mock_classify_document(document):
            doc_id = getattr(document, 'document_id', getattr(document.metadata, 'document_id', 'default'))
            return classification_results.get(doc_id, classification_results['default'])
        
        def mock_get_routing_info(document):
            doc_id = getattr(document, 'document_id', getattr(document.metadata, 'document_id', 'default'))
            return routing_info.get(doc_id, routing_info['default'])
        
        mock_classifier.classify = MagicMock(side_effect=mock_classify)
        mock_classifier.classify_document = MagicMock(side_effect=mock_classify_document)
        mock_classifier.get_routing_info = MagicMock(side_effect=mock_get_routing_info)
        mock_classifier.extract_features = MagicMock(return_value={})
        
        # Attach the configuration function to the mock
        mock_classifier.configure = configure_classifier
        
        yield mock_classifier


@pytest.fixture
def mock_classification_service(configurable_document_classifier):
    """
    Mock classification service for testing.
    
    This fixture provides a mock classification service that uses the
    configurable document classifier for testing.
    """
    with patch('document_service.services.classification_service.ClassificationService') as mock_service_class:
        # Create a MagicMock instance for the service
        mock_service = MagicMock()
        
        # Configure the class to return our mock instance
        mock_service_class.return_value = mock_service
        
        # Set the classifier
        mock_service.classifier = configurable_document_classifier
        
        # Mock service methods
        async def mock_classify_document(document):
            doc_id = getattr(document, 'document_id', getattr(document.metadata, 'document_id', 'default'))
            result = configurable_document_classifier.classify_document(document)
            return Result.success(result)
        
        async def mock_classify_from_message(message):
            doc_id = getattr(message, 'document_id', 'default')
            document = Document(
                metadata=DocumentMetadata(
                    document_id=doc_id,
                    filename=f"{doc_id}.pdf",
                    mime_type="application/pdf",
                    size_bytes=100,
                    page_count=1,
                    source="test",
                    created_at=datetime.now().isoformat(),
                    storage_path=f"documents/{doc_id}.pdf"
                ),
                content=b'mock document content',
                status=ProcessingStatus.PENDING_CLASSIFICATION
            )
            result = configurable_document_classifier.classify_document(document)
            return Result.success(result)
        
        async def mock_publish_classification_result(result):
            return Result.success(True)
        
        mock_service.classify_document = MagicMock(side_effect=mock_classify_document)
        mock_service.classify_from_message = MagicMock(side_effect=mock_classify_from_message)
        mock_service.publish_classification_result = MagicMock(side_effect=mock_publish_classification_result)
        
        # Add metrics
        mock_service.classification_metrics = {
            "total_documents": 100,
            "successful_classifications": 95,
            "low_confidence_classifications": 5,
            "failed_classifications": 0,
            "average_confidence": 0.92,
            "average_processing_time": 0.15,
            "document_type_counts": {
                "APPLICATION": 50,
                "BANK_STATEMENT": 20,
                "TAX_RETURN": 15,
                "PAY_STUB": 10,
                "ID_DOCUMENT": 5
            }
        }
        
        # Add get_metrics method
        mock_service.get_metrics = MagicMock(return_value=mock_service.classification_metrics)
        
        yield mock_service


# ===== Document Routing Fixtures =====

@pytest.fixture
def mock_document_router():
    """
    Mock document router for testing.
    
    This fixture provides a mock document router that can be configured
    to return specific routing decisions.
    """
    with patch('document_service.services.document_router.DocumentRouter') as mock_router_class:
        # Create a MagicMock instance for the router
        mock_router = MagicMock()
        
        # Configure the class to return our mock instance
        mock_router_class.return_value = mock_router
        
        # Mock router methods
        async def mock_route_document(document, classification_result):
            doc_type = classification_result.document_type
            confidence = classification_result.confidence.score
            requires_review = classification_result.requires_review
            
            # Determine routing based on document type and confidence
            if doc_type == DocumentType.APPLICATION:
                pipeline = 'application_form'
                priority = 'high'
            elif doc_type == DocumentType.BANK_STATEMENT:
                pipeline = 'bank_statement'
                priority = 'normal'
            elif doc_type == DocumentType.TAX_RETURN:
                pipeline = 'tax_document'
                priority = 'normal'
            elif doc_type == DocumentType.PAY_STUB:
                pipeline = 'pay_stub'
                priority = 'normal'
            elif doc_type == DocumentType.ID_DOCUMENT:
                pipeline = 'identity_document'
                priority = 'high'
            else:
                pipeline = 'standard'
                priority = 'low'
            
            # Add review suffix for low confidence
            if requires_review:
                pipeline += '_review'
            
            routing_result = {
                'document_id': classification_result.document_id,
                'document_type': doc_type.value,
                'confidence': confidence,
                'requires_review': requires_review,
                'ocr_pipeline': pipeline,
                'priority': priority,
                'routing_timestamp': datetime.now().isoformat()
            }
            
            return Result.success(routing_result)
        
        mock_router.route_document = MagicMock(side_effect=mock_route_document)
        
        yield mock_router


@pytest.fixture
def configurable_document_router():
    """
    Configurable document router for testing.
    
    This fixture provides a mock document router that can be configured
    to return different routing decisions based on test requirements.
    """
    with patch('document_service.services.document_router.DocumentRouter') as mock_router_class:
        # Create a MagicMock instance for the router
        mock_router = MagicMock()
        
        # Configure the class to return our mock instance
        mock_router_class.return_value = mock_router
        
        # Create configurable routing results
        routing_results = {}
        
        # Define a function to configure the router
        def configure_router(document_id, document_type, confidence_score, requires_review=None, pipeline=None, priority=None):
            if requires_review is None:
                requires_review = confidence_score < 0.75
                
            if pipeline is None:
                if document_type == DocumentType.APPLICATION:
                    pipeline = 'application_form'
                elif document_type == DocumentType.BANK_STATEMENT:
                    pipeline = 'bank_statement'
                elif document_type == DocumentType.TAX_RETURN:
                    pipeline = 'tax_document'
                elif document_type == DocumentType.PAY_STUB:
                    pipeline = 'pay_stub'
                elif document_type == DocumentType.ID_DOCUMENT:
                    pipeline = 'identity_document'
                else:
                    pipeline = 'standard'
                    
                # Add review suffix for low confidence
                if requires_review:
                    pipeline += '_review'
            
            if priority is None:
                if document_type in [DocumentType.APPLICATION, DocumentType.ID_DOCUMENT]:
                    priority = 'high'
                else:
                    priority = 'normal'
            
            # Store routing result
            routing_results[document_id] = {
                'document_id': document_id,
                'document_type': document_type.value,
                'confidence': confidence_score,
                'requires_review': requires_review,
                'ocr_pipeline': pipeline,
                'priority': priority,
                'routing_timestamp': datetime.now().isoformat()
            }
        
        # Configure default routing
        configure_router(
            'default',
            DocumentType.APPLICATION,
            0.95,
            False
        )
        
        # Mock router methods to use our configurable results
        async def mock_route_document(document, classification_result):
            doc_id = classification_result.document_id
            return Result.success(routing_results.get(doc_id, routing_results['default']))
        
        mock_router.route_document = MagicMock(side_effect=mock_route_document)
        
        # Attach the configuration function to the mock
        mock_router.configure = configure_router
        
        yield mock_router


# ===== Test Data Generation Fixtures =====

@pytest.fixture
def create_test_document():
    """
    Factory function to create test documents.
    
    This fixture provides a function to create test Document objects
    with configurable properties for testing.
    """
    def _create_document(document_id=None, document_type=None, content=None, metadata=None, status=None):
        # Generate a random document ID if not provided
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Create default metadata if not provided
        if metadata is None:
            metadata = DocumentMetadata(
                document_id=document_id,
                filename=f"{document_id}.pdf",
                mime_type="application/pdf",
                size_bytes=100,
                page_count=1,
                source="test",
                created_at=datetime.now().isoformat(),
                storage_path=f"documents/{document_id}.pdf"
            )
        
        # Use provided content or generate default
        if content is None:
            content = f"Test document content for {document_id}".encode('utf-8')
        
        # Use provided status or default
        if status is None:
            status = ProcessingStatus.PENDING_CLASSIFICATION
        
        # Create and return the document
        document = Document(
            metadata=metadata,
            content=content,
            status=status
        )
        
        # Set document type if provided
        if document_type is not None:
            document.document_type = document_type
        
        return document
    
    return _create_document


@pytest.fixture
def create_test_message():
    """
    Factory function to create test messages.
    
    This fixture provides a function to create test MessagePayload objects
    with configurable properties for testing.
    """
    def _create_message(document_id=None, storage_path=None, document_content=None, metadata=None):
        # Generate a random document ID if not provided
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Generate a default storage path if not provided
        if storage_path is None:
            storage_path = f"documents/{document_id}.pdf"
        
        # Create the message payload
        message = MessagePayload(
            message_id=str(uuid.uuid4()),
            document_id=document_id,
            storage_path=storage_path,
            filename=os.path.basename(storage_path),
            mime_type="application/pdf",
            source="test",
            created_at=datetime.now().isoformat(),
            document_content=document_content,
            page_count=1
        )
        
        # Add additional metadata if provided
        if metadata is not None:
            for key, value in metadata.items():
                setattr(message, key, value)
        
        return message
    
    return _create_message


@pytest.fixture
def create_test_classification_result():
    """
    Factory function to create test classification results.
    
    This fixture provides a function to create test ClassificationResult objects
    with configurable properties for testing.
    """
    def _create_classification_result(document_id=None, document_type=None, confidence=None, requires_review=None):
        # Generate a random document ID if not provided
        if document_id is None:
            document_id = str(uuid.uuid4())
        
        # Use provided document type or default
        if document_type is None:
            document_type = DocumentType.APPLICATION
        
        # Use provided confidence or default
        if confidence is None:
            confidence = ConfidenceScore(
                score=0.95,
                model_name='ensemble',
                details={'svm': 0.94, 'random_forest': 0.96}
            )
        elif isinstance(confidence, (int, float)):
            confidence = ConfidenceScore(
                score=confidence,
                model_name='ensemble',
                details={'svm': confidence - 0.01, 'random_forest': confidence + 0.01}
            )
        
        # Determine if review is required based on confidence if not specified
        if requires_review is None:
            requires_review = confidence.score < 0.75
        
        # Create and return the classification result
        return ClassificationResult(
            document_id=document_id,
            document_type=document_type,
            confidence=confidence,
            requires_review=requires_review,
            prediction_time=datetime.now(),
            processing_time=0.15,
            features_used=['text_features', 'metadata_features'],
            timestamp=datetime.now().isoformat(),
            metadata={
                'filename': f"{document_id}.pdf",
                'mime_type': 'application/pdf',
                'size_bytes': 100,
                'page_count': 1,
                'classification_version': '1.0.0'
            }
        )
    
    return _create_classification_result


# ===== App Configuration Fixtures =====

@pytest.fixture
def mock_app_config():
    """
    Mock application configuration for testing.
    
    This fixture provides a mock application configuration with test values.
    """
    with patch('document_service.config.app_config') as mock_config:
        # Set configuration values
        mock_config.SERVICE_NAME = 'document-service'
        mock_config.SERVICE_VERSION = '1.0.0'
        mock_config.LOG_LEVEL = 'INFO'
        mock_config.ENVIRONMENT = 'test'
        
        yield mock_config


@pytest.fixture
def mock_model_config():
    """
    Mock model configuration for testing.
    
    This fixture provides a mock model configuration with test values.
    """
    with patch('document_service.config.model_config') as mock_config:
        # Set configuration values
        mock_config.MODEL_PATH = '/tmp/models'
        mock_config.REQUIRED_MODEL_VERSION = '1.0.0'
        mock_config.DEFAULT_CONFIDENCE_THRESHOLD = 0.75
        mock_config.CONFIDENCE_THRESHOLDS = {
            DocumentType.APPLICATION: 0.75,
            DocumentType.BANK_STATEMENT: 0.80,
            DocumentType.TAX_RETURN: 0.85,
            DocumentType.PAY_STUB: 0.75,
            DocumentType.ID_DOCUMENT: 0.90,
            DocumentType.OTHER: 0.75,
            DocumentType.UNKNOWN: 0.75
        }
        mock_config.FEATURE_EXTRACTION = {
            'use_text_features': True,
            'use_metadata_features': True,
            'use_image_features': False
        }
        mock_config.MODEL_PARAMETERS = {
            'svm': {
                'C': 1.0,
                'kernel': 'linear',
                'probability': True
            },
            'random_forest': {
                'n_estimators': 100,
                'max_depth': 10,
                'random_state': 42
            }
        }
        mock_config.RECENT_RESULTS_CACHE_SIZE = 100
        
        yield mock_config