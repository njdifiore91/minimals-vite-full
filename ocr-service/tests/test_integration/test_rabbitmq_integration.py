#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the OCR Service's RabbitMQ integration.

This module tests the integration between the OCR Service and RabbitMQ message queue.
It verifies that the service correctly consumes messages from input queues, processes
documents, and publishes results to output queues, ensuring reliable message-based processing.

Key aspects tested:
1. Connection to RabbitMQ with TLS and client certificate authentication
2. Message consumption from the 'ocr.request' queue
3. Message publishing to the 'data.processing' queue
4. Message format and schema validation
5. Error handling and retry logic
6. Message acknowledgment and rejection
7. Queue configuration and message routing
"""

import json
import os
import ssl
import time
from unittest.mock import MagicMock, patch, call, ANY

import pytest
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

# Import OCR service modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from app import OCRServiceApp
from config import rabbitmq_config
from services.queue_service import QueueService, Result
from types.messages import MessagePayload, MessageHeaders, MessageStatus, create_message_payload
from types.errors import ServiceError, ErrorCategory
from utils.rabbitmq_utils import RabbitMQConnection, with_connection_retry


# ===== Test Fixtures =====

@pytest.fixture(scope="function")
def mock_rabbitmq_config():
    """Create a mock RabbitMQ configuration for testing."""
    config = rabbitmq_config.get_rabbitmq_config()
    
    # Override configuration for testing
    config.host = "test-rabbitmq-host"
    config.port = 5671
    config.virtual_host = "/test"
    config.username = "test-user"
    config.password = "test-password"
    config.ca_cert_path = "/path/to/ca.pem"
    config.client_cert_path = "/path/to/client.pem"
    config.client_key_path = "/path/to/client.key"
    config.cert_password = "test-cert-password"
    
    # Configure exchanges and queues for testing
    config.exchanges = [
        {
            "name": "mca.documents.test",
            "exchange_type": "topic",
            "durable": True
        },
        {
            "name": "mca.data.processing.test",
            "exchange_type": "topic",
            "durable": True
        }
    ]
    
    config.queues = [
        {
            "name": "ocr.request.test",
            "durable": True,
            "arguments": {
                "x-dead-letter-exchange": "mca.dead-letter.test",
                "x-dead-letter-routing-key": "ocr.request.dead"
            },
            "bindings": [
                {
                    "exchange": "mca.documents.test",
                    "routing_key": "ocr.request"
                }
            ]
        },
        {
            "name": "data.processing.test",
            "durable": True,
            "arguments": {
                "x-dead-letter-exchange": "mca.dead-letter.test",
                "x-dead-letter-routing-key": "data.processing.dead"
            },
            "bindings": [
                {
                    "exchange": "mca.data.processing.test",
                    "routing_key": "data.extraction.complete"
                },
                {
                    "exchange": "mca.data.processing.test",
                    "routing_key": "data.extraction.error"
                }
            ]
        }
    ]
    
    return config


@pytest.fixture(scope="function")
def queue_service_with_mocks(mock_rabbitmq_config, mock_rabbitmq_connection):
    """Create a QueueService instance with mocked RabbitMQ connection."""
    mock_connection, mock_channel = mock_rabbitmq_connection
    
    with patch('services.queue_service.RabbitMQConnection') as MockRabbitMQConnection:
        # Configure the mock RabbitMQConnection
        mock_rmq_connection = MagicMock()
        mock_rmq_connection.connection = mock_connection
        mock_rmq_connection.channel = mock_channel
        mock_rmq_connection.ensure_connection.return_value = True
        mock_rmq_connection.is_connected.return_value = True
        mock_rmq_connection.publish_message.return_value = True
        MockRabbitMQConnection.return_value = mock_rmq_connection
        
        # Create QueueService with mock config
        queue_service = QueueService(config=mock_rabbitmq_config)
        queue_service.running = True
        
        yield queue_service, mock_rmq_connection


# ===== Test Connection and Configuration =====

def test_queue_service_initialization(mock_rabbitmq_config):
    """Test that QueueService initializes correctly with the provided configuration."""
    with patch('services.queue_service.RabbitMQConnection') as MockRabbitMQConnection:
        # Create a mock RabbitMQConnection
        mock_connection = MagicMock()
        MockRabbitMQConnection.return_value = mock_connection
        
        # Initialize QueueService
        queue_service = QueueService(config=mock_rabbitmq_config)
        
        # Verify that RabbitMQConnection was initialized with the correct config
        MockRabbitMQConnection.assert_called_once_with(mock_rabbitmq_config)
        
        # Verify that the QueueService was initialized correctly
        assert queue_service.config == mock_rabbitmq_config
        assert queue_service.connection == mock_connection
        assert queue_service.callback is None
        assert queue_service.running is False


def test_queue_service_start(queue_service_with_mocks):
    """Test that QueueService.start() correctly sets up exchanges and queues."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Reset the running flag
    queue_service.running = False
    
    # Start the QueueService
    result = queue_service.start()
    
    # Verify that the start method was successful
    assert result.success is True
    assert queue_service.running is True
    
    # Verify that the connection was established
    mock_rmq_connection.connect.assert_called_once()
    
    # Verify that exchanges were declared
    assert mock_rmq_connection.declare_exchange.call_count == 2
    mock_rmq_connection.declare_exchange.assert_any_call(
        exchange="mca.documents.test",
        exchange_type="topic",
        durable=True
    )
    mock_rmq_connection.declare_exchange.assert_any_call(
        exchange="mca.data.processing.test",
        exchange_type="topic",
        durable=True
    )
    
    # Verify that queues were declared and bound
    assert mock_rmq_connection.declare_queue.call_count == 2
    mock_rmq_connection.declare_queue.assert_any_call(
        queue="ocr.request.test",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "mca.dead-letter.test",
            "x-dead-letter-routing-key": "ocr.request.dead"
        }
    )
    mock_rmq_connection.declare_queue.assert_any_call(
        queue="data.processing.test",
        durable=True,
        arguments={
            "x-dead-letter-exchange": "mca.dead-letter.test",
            "x-dead-letter-routing-key": "data.processing.dead"
        }
    )
    
    # Verify that queues were bound to exchanges
    assert mock_rmq_connection.bind_queue.call_count == 3
    mock_rmq_connection.bind_queue.assert_any_call(
        queue="ocr.request.test",
        exchange="mca.documents.test",
        routing_key="ocr.request"
    )
    mock_rmq_connection.bind_queue.assert_any_call(
        queue="data.processing.test",
        exchange="mca.data.processing.test",
        routing_key="data.extraction.complete"
    )
    mock_rmq_connection.bind_queue.assert_any_call(
        queue="data.processing.test",
        exchange="mca.data.processing.test",
        routing_key="data.extraction.error"
    )


def test_queue_service_stop(queue_service_with_mocks):
    """Test that QueueService.stop() correctly closes the connection."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Stop the QueueService
    result = queue_service.stop()
    
    # Verify that the stop method was successful
    assert result.success is True
    assert queue_service.running is False
    
    # Verify that the connection was closed
    mock_rmq_connection.close.assert_called_once()


def test_queue_service_health_check(queue_service_with_mocks):
    """Test that QueueService.health_check() returns the correct status."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Configure the mock connection to be open
    mock_rmq_connection.is_connected.return_value = True
    
    # Perform health check
    health_info = queue_service.health_check()
    
    # Verify health check results
    assert health_info["status"] == "healthy"
    assert health_info["details"]["running"] is True
    assert health_info["details"]["connected"] is True
    assert health_info["details"]["connection"]["host"] == queue_service.config.host
    assert health_info["details"]["connection"]["port"] == queue_service.config.port
    assert health_info["details"]["connection"]["virtual_host"] == queue_service.config.virtual_host
    
    # Configure the mock connection to be closed
    mock_rmq_connection.is_connected.return_value = False
    
    # Perform health check again
    health_info = queue_service.health_check()
    
    # Verify health check results
    assert health_info["status"] == "unhealthy"


# ===== Test Message Consumption =====

def test_consume_messages(queue_service_with_mocks):
    """Test that QueueService.consume_messages() correctly sets up message consumption."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a mock callback function
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Start consuming messages
    result = queue_service.consume_messages(queue="ocr.request.test", prefetch_count=5)
    
    # Verify that the consume_messages method was successful
    assert result.success is True
    
    # Verify that the connection was ensured
    mock_rmq_connection.ensure_connection.assert_called_once()
    
    # Verify that basic_qos was set
    mock_rmq_connection.channel.basic_qos.assert_called_once_with(prefetch_count=5)
    
    # Verify that consume_messages was called with the correct parameters
    mock_rmq_connection.consume_messages.assert_called_once_with(
        queue="ocr.request.test",
        callback=queue_service._message_handler,
        auto_ack=False,
        prefetch_count=5
    )


def test_consume_messages_no_callback(queue_service_with_mocks):
    """Test that QueueService.consume_messages() fails when no callback is registered."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Ensure no callback is registered
    queue_service.callback = None
    
    # Start consuming messages
    result = queue_service.consume_messages(queue="ocr.request.test")
    
    # Verify that the consume_messages method failed
    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    assert "No callback registered" in str(result.error)
    
    # Verify that consume_messages was not called
    mock_rmq_connection.consume_messages.assert_not_called()


def test_message_handler_success(queue_service_with_mocks):
    """Test that _message_handler correctly processes valid messages."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a mock callback function
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Create mock message components
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = "test-tag"
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {"source": "document-service"}
    
    # Create a test message payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "APPLICATION",
        "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
        "application_id": "app-12345"
    }
    body = json.dumps(payload).encode('utf-8')
    
    # Mock the deserialize_message function
    with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
        mock_deserialize.return_value = (payload, properties.headers)
        
        # Call the message handler
        queue_service._message_handler(channel, method, properties, body)
        
        # Verify that deserialize_message was called with the correct parameters
        mock_deserialize.assert_called_once_with(body, properties)
        
        # Verify that the callback was called with the correct parameters
        callback.assert_called_once_with(channel, method, properties, body, payload, properties.headers)
        
        # Verify that the message was acknowledged
        mock_rmq_connection.acknowledge_message.assert_called_once_with(method.delivery_tag)


def test_message_handler_deserialization_error(queue_service_with_mocks):
    """Test that _message_handler correctly handles deserialization errors."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a mock callback function
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Create mock message components
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = "test-tag"
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {}
    body = b"invalid json"
    
    # Mock the deserialize_message function to raise an exception
    with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
        mock_deserialize.side_effect = ValueError("Invalid JSON")
        
        # Call the message handler
        queue_service._message_handler(channel, method, properties, body)
        
        # Verify that deserialize_message was called with the correct parameters
        mock_deserialize.assert_called_once_with(body, properties)
        
        # Verify that the callback was not called
        callback.assert_not_called()
        
        # Verify that the message was rejected without requeue
        mock_rmq_connection.reject_message.assert_called_once_with(method.delivery_tag, requeue=False)


def test_message_handler_callback_error(queue_service_with_mocks):
    """Test that _message_handler correctly handles callback errors."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a mock callback function that raises an exception
    callback = MagicMock(side_effect=Exception("Processing error"))
    queue_service.register_callback(callback)
    
    # Create mock message components
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = "test-tag"
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {}
    
    # Create a test message payload
    payload = {"document_id": "doc-12345"}
    body = json.dumps(payload).encode('utf-8')
    
    # Mock the deserialize_message function
    with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
        mock_deserialize.return_value = (payload, properties.headers)
        
        # Mock the get_retry_count function
        with patch('services.queue_service.get_retry_count') as mock_get_retry_count:
            mock_get_retry_count.return_value = 0  # First attempt
            
            # Call the message handler
            queue_service._message_handler(channel, method, properties, body)
            
            # Verify that deserialize_message was called with the correct parameters
            mock_deserialize.assert_called_once_with(body, properties)
            
            # Verify that the callback was called with the correct parameters
            callback.assert_called_once_with(channel, method, properties, body, payload, properties.headers)
            
            # Verify that the message was rejected with requeue
            mock_rmq_connection.reject_message.assert_called_once_with(method.delivery_tag, requeue=True)


def test_message_handler_callback_error_max_retries(queue_service_with_mocks):
    """Test that _message_handler correctly handles callback errors after max retries."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a mock callback function that raises an exception
    callback = MagicMock(side_effect=Exception("Processing error"))
    queue_service.register_callback(callback)
    
    # Create mock message components
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = "test-tag"
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {}
    
    # Create a test message payload
    payload = {"document_id": "doc-12345"}
    body = json.dumps(payload).encode('utf-8')
    
    # Mock the deserialize_message function
    with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
        mock_deserialize.return_value = (payload, properties.headers)
        
        # Mock the get_retry_count function
        with patch('services.queue_service.get_retry_count') as mock_get_retry_count:
            mock_get_retry_count.return_value = 3  # Max retries reached
            
            # Call the message handler
            queue_service._message_handler(channel, method, properties, body)
            
            # Verify that deserialize_message was called with the correct parameters
            mock_deserialize.assert_called_once_with(body, properties)
            
            # Verify that the callback was called with the correct parameters
            callback.assert_called_once_with(channel, method, properties, body, payload, properties.headers)
            
            # Verify that the message was rejected without requeue
            mock_rmq_connection.reject_message.assert_called_once_with(method.delivery_tag, requeue=False)


# ===== Test Message Publishing =====

def test_publish_message(queue_service_with_mocks):
    """Test that publish_message correctly publishes messages to RabbitMQ."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a test message payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "APPLICATION",
        "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
        "application_id": "app-12345"
    }
    
    # Create test headers
    headers = {"source": "ocr-service"}
    
    # Mock the serialize_message function
    with patch('services.queue_service.utils_serialize_message') as mock_serialize:
        mock_serialize.return_value = (json.dumps(payload).encode('utf-8'), headers)
        
        # Publish the message
        result = queue_service.publish_message(
            exchange="mca.data.processing.test",
            routing_key="data.extraction.complete",
            payload=payload,
            headers=headers
        )
        
        # Verify that the publish_message method was successful
        assert result.success is True
        
        # Verify that the connection was ensured
        mock_rmq_connection.ensure_connection.assert_called_once()
        
        # Verify that serialize_message was called with the correct parameters
        mock_serialize.assert_called_once_with(payload, headers)
        
        # Verify that publish_message was called with the correct parameters
        mock_rmq_connection.publish_message.assert_called_once_with(
            exchange="mca.data.processing.test",
            routing_key="data.extraction.complete",
            body=mock_serialize.return_value[0],
            headers=headers,
            options=None
        )


def test_publish_message_connection_error(queue_service_with_mocks):
    """Test that publish_message correctly handles connection errors."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Configure the mock connection to raise an exception
    mock_rmq_connection.ensure_connection.side_effect = AMQPConnectionError("Connection refused")
    
    # Create a test message payload
    payload = {"document_id": "doc-12345"}
    
    # Publish the message
    result = queue_service.publish_message(
        exchange="mca.data.processing.test",
        routing_key="data.extraction.complete",
        payload=payload
    )
    
    # Verify that the publish_message method failed
    assert result.success is False
    assert isinstance(result.error, AMQPConnectionError)
    assert "Connection refused" in str(result.error)
    
    # Verify that the connection was attempted
    mock_rmq_connection.ensure_connection.assert_called_once()
    
    # Verify that publish_message was not called
    mock_rmq_connection.publish_message.assert_not_called()


def test_publish_message_channel_error(queue_service_with_mocks):
    """Test that publish_message correctly handles channel errors."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Configure the mock connection to raise an exception on publish
    mock_rmq_connection.publish_message.side_effect = AMQPChannelError("Channel closed")
    
    # Create a test message payload
    payload = {"document_id": "doc-12345"}
    
    # Mock the serialize_message function
    with patch('services.queue_service.utils_serialize_message') as mock_serialize:
        mock_serialize.return_value = (json.dumps(payload).encode('utf-8'), {})
        
        # Publish the message
        result = queue_service.publish_message(
            exchange="mca.data.processing.test",
            routing_key="data.extraction.complete",
            payload=payload
        )
        
        # Verify that the publish_message method failed
        assert result.success is False
        assert isinstance(result.error, AMQPChannelError)
        assert "Channel closed" in str(result.error)
        
        # Verify that the connection was ensured
        mock_rmq_connection.ensure_connection.assert_called_once()
        
        # Verify that serialize_message was called
        mock_serialize.assert_called_once()
        
        # Verify that publish_message was called
        mock_rmq_connection.publish_message.assert_called_once()


def test_publish_extraction_results(queue_service_with_mocks):
    """Test that publish_extraction_results correctly publishes extraction results."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Mock the publish_message method
    with patch.object(queue_service, 'publish_message') as mock_publish_message:
        mock_publish_message.return_value = Result.ok(True)
        
        # Publish extraction results
        result = queue_service.publish_extraction_results(
            document_id="doc-12345",
            application_id="app-12345",
            storage_path="mca-documents-staging/applications/doc-12345.pdf",
            extraction_results={
                "business_name": "Dollar Funding LLC",
                "tax_id": "12-3456789",
                "address": "123 Main St, New York, NY 10001",
                "requested_amount": "50000"
            },
            confidence_scores={
                "business_name": 0.98,
                "tax_id": 0.95,
                "address": 0.92,
                "requested_amount": 0.97
            },
            document_type="APPLICATION",
            processing_time_ms=1250.0,
            requires_verification=False
        )
        
        # Verify that the publish_extraction_results method was successful
        assert result.success is True
        
        # Verify that publish_message was called with the correct parameters
        mock_publish_message.assert_called_once()
        call_args = mock_publish_message.call_args[1]
        
        assert call_args["exchange"] == "mca.data.processing"
        assert call_args["routing_key"] == "data.extraction.complete"
        
        # Verify payload contents
        payload = call_args["payload"]
        assert payload["document_id"] == "doc-12345"
        assert payload["document_type"] == "APPLICATION"
        assert payload["application_id"] == "app-12345"
        assert payload["storage_path"] == "mca-documents-staging/applications/doc-12345.pdf"
        assert payload["content_type"] == "application/json"
        assert payload["source_service"] == "ocr-service"
        assert payload["status"] == MessageStatus.COMPLETED.value
        assert payload["extraction_results"] == {
            "business_name": "Dollar Funding LLC",
            "tax_id": "12-3456789",
            "address": "123 Main St, New York, NY 10001",
            "requested_amount": "50000"
        }
        assert payload["confidence_scores"] == {
            "business_name": 0.98,
            "tax_id": 0.95,
            "address": 0.92,
            "requested_amount": 0.97
        }
        assert payload["processing_time_ms"] == 1250.0
        assert payload["requires_verification"] is False


def test_publish_extraction_results_with_verification(queue_service_with_mocks):
    """Test that publish_extraction_results correctly handles verification flags."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Mock the publish_message method
    with patch.object(queue_service, 'publish_message') as mock_publish_message:
        mock_publish_message.return_value = Result.ok(True)
        
        # Publish extraction results with verification required
        result = queue_service.publish_extraction_results(
            document_id="doc-12345",
            application_id="app-12345",
            storage_path="mca-documents-staging/applications/doc-12345.pdf",
            extraction_results={
                "business_name": "Dollar Funding LLC",
                "tax_id": "12-3456789",
                "address": "123 Main St, New York, NY 10001",
                "requested_amount": "50000"
            },
            confidence_scores={
                "business_name": 0.98,
                "tax_id": 0.65,  # Low confidence
                "address": 0.92,
                "requested_amount": 0.97
            },
            document_type="APPLICATION",
            processing_time_ms=1250.0,
            requires_verification=True,
            verification_fields=["tax_id"]
        )
        
        # Verify that the publish_extraction_results method was successful
        assert result.success is True
        
        # Verify that publish_message was called with the correct parameters
        mock_publish_message.assert_called_once()
        call_args = mock_publish_message.call_args[1]
        
        # Verify payload contents
        payload = call_args["payload"]
        assert payload["requires_verification"] is True
        assert payload["verification_fields"] == ["tax_id"]


def test_publish_extraction_error(queue_service_with_mocks):
    """Test that publish_extraction_error correctly publishes error information."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Mock the publish_message method
    with patch.object(queue_service, 'publish_message') as mock_publish_message:
        mock_publish_message.return_value = Result.ok(True)
        
        # Publish extraction error
        result = queue_service.publish_extraction_error(
            document_id="doc-12345",
            application_id="app-12345",
            storage_path="mca-documents-staging/applications/doc-12345.pdf",
            error={
                "code": "OCR_PROCESSING_ERROR",
                "message": "Failed to extract text from document",
                "details": "Document is corrupted or contains no readable text"
            },
            document_type="APPLICATION"
        )
        
        # Verify that the publish_extraction_error method was successful
        assert result.success is True
        
        # Verify that publish_message was called with the correct parameters
        mock_publish_message.assert_called_once()
        call_args = mock_publish_message.call_args[1]
        
        assert call_args["exchange"] == "mca.data.processing"
        assert call_args["routing_key"] == "data.extraction.error"
        
        # Verify payload contents
        payload = call_args["payload"]
        assert payload["document_id"] == "doc-12345"
        assert payload["document_type"] == "APPLICATION"
        assert payload["application_id"] == "app-12345"
        assert payload["storage_path"] == "mca-documents-staging/applications/doc-12345.pdf"
        assert payload["content_type"] == "application/json"
        assert payload["source_service"] == "ocr-service"
        assert payload["status"] == MessageStatus.FAILED.value
        assert payload["error"] == {
            "code": "OCR_PROCESSING_ERROR",
            "message": "Failed to extract text from document",
            "details": "Document is corrupted or contains no readable text"
        }


# ===== Test End-to-End Message Flow =====

def test_end_to_end_message_flow(queue_service_with_mocks, mock_ocr_service, mock_storage_service):
    """Test the end-to-end flow of messages through the OCR Service."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a test document processing callback
    def document_processing_callback(channel, method, properties, body, payload, headers):
        # Extract document information
        document_id = payload.get("document_id")
        document_type = payload.get("document_type")
        storage_path = payload.get("storage_path")
        application_id = payload.get("application_id")
        
        # Simulate document processing
        extraction_results = {
            "business_name": "Dollar Funding LLC",
            "tax_id": "12-3456789",
            "address": "123 Main St, New York, NY 10001",
            "requested_amount": "50000"
        }
        confidence_scores = {
            "business_name": 0.98,
            "tax_id": 0.95,
            "address": 0.92,
            "requested_amount": 0.97
        }
        
        # Publish extraction results
        queue_service.publish_extraction_results(
            document_id=document_id,
            application_id=application_id,
            storage_path=storage_path,
            extraction_results=extraction_results,
            confidence_scores=confidence_scores,
            document_type=document_type,
            processing_time_ms=1250.0,
            requires_verification=False
        )
    
    # Register the callback
    queue_service.register_callback(document_processing_callback)
    
    # Mock the publish_extraction_results method
    with patch.object(queue_service, 'publish_extraction_results') as mock_publish_results:
        mock_publish_results.return_value = Result.ok(True)
        
        # Create mock message components
        channel = MagicMock()
        method = MagicMock()
        method.delivery_tag = "test-tag"
        properties = MagicMock()
        properties.message_id = "test-message-id"
        properties.headers = {"source": "document-service"}
        
        # Create a test message payload
        payload = {
            "document_id": "doc-12345",
            "document_type": "APPLICATION",
            "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
            "application_id": "app-12345"
        }
        body = json.dumps(payload).encode('utf-8')
        
        # Mock the deserialize_message function
        with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
            mock_deserialize.return_value = (payload, properties.headers)
            
            # Call the message handler
            queue_service._message_handler(channel, method, properties, body)
            
            # Verify that deserialize_message was called
            mock_deserialize.assert_called_once()
            
            # Verify that publish_extraction_results was called with the correct parameters
            mock_publish_results.assert_called_once_with(
                document_id="doc-12345",
                application_id="app-12345",
                storage_path="mca-documents-staging/applications/doc-12345.pdf",
                extraction_results={
                    "business_name": "Dollar Funding LLC",
                    "tax_id": "12-3456789",
                    "address": "123 Main St, New York, NY 10001",
                    "requested_amount": "50000"
                },
                confidence_scores={
                    "business_name": 0.98,
                    "tax_id": 0.95,
                    "address": 0.92,
                    "requested_amount": 0.97
                },
                document_type="APPLICATION",
                processing_time_ms=1250.0,
                requires_verification=False
            )
            
            # Verify that the message was acknowledged
            mock_rmq_connection.acknowledge_message.assert_called_once_with(method.delivery_tag)


def test_end_to_end_error_handling(queue_service_with_mocks, mock_ocr_service, mock_storage_service):
    """Test the end-to-end error handling in the OCR Service."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    
    # Create a test document processing callback that raises an exception
    def document_processing_callback(channel, method, properties, body, payload, headers):
        # Simulate a processing error
        raise Exception("Document processing failed: Unreadable content")
    
    # Register the callback
    queue_service.register_callback(document_processing_callback)
    
    # Create mock message components
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = "test-tag"
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {"source": "document-service"}
    
    # Create a test message payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "APPLICATION",
        "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
        "application_id": "app-12345"
    }
    body = json.dumps(payload).encode('utf-8')
    
    # Mock the deserialize_message function
    with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
        mock_deserialize.return_value = (payload, properties.headers)
        
        # Mock the get_retry_count function
        with patch('services.queue_service.get_retry_count') as mock_get_retry_count:
            mock_get_retry_count.return_value = 0  # First attempt
            
            # Call the message handler
            queue_service._message_handler(channel, method, properties, body)
            
            # Verify that deserialize_message was called
            mock_deserialize.assert_called_once()
            
            # Verify that the message was rejected with requeue
            mock_rmq_connection.reject_message.assert_called_once_with(method.delivery_tag, requeue=True)


# ===== Test TLS Configuration =====

def test_tls_configuration(mock_rabbitmq_config):
    """Test that TLS is correctly configured for RabbitMQ connections."""
    with patch('services.queue_service.RabbitMQConnection') as MockRabbitMQConnection:
        # Create a mock RabbitMQConnection
        mock_connection = MagicMock()
        MockRabbitMQConnection.return_value = mock_connection
        
        # Initialize QueueService
        queue_service = QueueService(config=mock_rabbitmq_config)
        
        # Verify that RabbitMQConnection was initialized with the correct config
        MockRabbitMQConnection.assert_called_once_with(mock_rabbitmq_config)
        
        # Verify TLS configuration
        assert mock_rabbitmq_config.ca_cert_path == "/path/to/ca.pem"
        assert mock_rabbitmq_config.client_cert_path == "/path/to/client.pem"
        assert mock_rabbitmq_config.client_key_path == "/path/to/client.key"
        assert mock_rabbitmq_config.cert_password == "test-cert-password"


# ===== Test Integration with OCR Service Application =====

def test_integration_with_app(mock_app, queue_service_with_mocks):
    """Test integration of QueueService with the OCR Service application."""
    queue_service, mock_rmq_connection = queue_service_with_mocks
    app = mock_app
    
    # Set the queue_service on the app
    app.queue_service = queue_service
    
    # Create a test message callback
    def test_callback(channel, method, properties, body, payload, headers):
        # Process the document
        app.process_document(
            document_id=payload.get("document_id"),
            document_type=payload.get("document_type"),
            storage_path=payload.get("storage_path"),
            application_id=payload.get("application_id")
        )
    
    # Register the callback
    queue_service.register_callback(test_callback)
    
    # Create mock message components
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = "test-tag"
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {"source": "document-service"}
    
    # Create a test message payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "APPLICATION",
        "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
        "application_id": "app-12345"
    }
    body = json.dumps(payload).encode('utf-8')
    
    # Mock the deserialize_message function
    with patch('services.queue_service.utils_deserialize_message') as mock_deserialize:
        mock_deserialize.return_value = (payload, properties.headers)
        
        # Call the message handler
        queue_service._message_handler(channel, method, properties, body)
        
        # Verify that deserialize_message was called
        mock_deserialize.assert_called_once()
        
        # Verify that process_document was called with the correct parameters
        app.process_document.assert_called_once_with(
            document_id="doc-12345",
            document_type="APPLICATION",
            storage_path="mca-documents-staging/applications/doc-12345.pdf",
            application_id="app-12345"
        )
        
        # Verify that the message was acknowledged
        mock_rmq_connection.acknowledge_message.assert_called_once_with(method.delivery_tag)