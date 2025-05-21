#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the RabbitMQ message handling service.

This module contains tests for the QueueService class, which provides functionality for
connecting to RabbitMQ, consuming messages from the 'ocr.request' queue, and publishing
extraction results to downstream services. It tests connection management, message
consumption, publishing operations, and error handling.
"""

import json
import ssl
import time
import pytest
from unittest.mock import MagicMock, patch, call, ANY

from pika.exceptions import AMQPConnectionError, AMQPChannelError, AMQPError
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel

from ocr_service.src.services.queue_service import QueueService
from ocr_service.src.types.messages import MessagePayload, MessageHeaders
from ocr_service.src.types.errors import ServiceError, ErrorCategory, Result


# ===== Test QueueService Initialization =====

@patch('ocr_service.src.services.queue_service.pika.BlockingConnection')
@patch('ocr_service.src.services.queue_service.ssl.create_default_context')
def test_queue_service_init_success(mock_ssl_context, mock_connection, mock_rabbitmq_connection):
    """Test successful initialization of QueueService with TLS."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    mock_connection.return_value = connection
    
    # Create SSL context mock
    ssl_context = MagicMock()
    mock_ssl_context.return_value = ssl_context
    
    # Initialize QueueService
    queue_service = QueueService()
    
    # Verify SSL context was created with correct parameters
    mock_ssl_context.assert_called_once()
    ssl_context.load_cert_chain.assert_called_once()
    assert ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert ssl_context.check_hostname is True
    
    # Verify connection was established with correct parameters
    mock_connection.assert_called_once()
    assert queue_service.connected is True
    assert queue_service.connection is not None
    assert queue_service.channel is not None
    
    # Verify exchange and queues were declared
    channel.exchange_declare.assert_called_with(
        exchange=queue_service.exchange_name,
        exchange_type=queue_service.exchange_type,
        durable=True
    )
    
    # Verify queues were declared
    assert channel.queue_declare.call_count == 2
    channel.queue_declare.assert_any_call(
        queue=queue_service.ocr_request_queue,
        durable=True
    )
    channel.queue_declare.assert_any_call(
        queue=queue_service.data_processing_queue,
        durable=True
    )
    
    # Verify queues were bound to exchange
    assert channel.queue_bind.call_count == 2
    channel.queue_bind.assert_any_call(
        queue=queue_service.ocr_request_queue,
        exchange=queue_service.exchange_name,
        routing_key='ocr.request'
    )
    channel.queue_bind.assert_any_call(
        queue=queue_service.data_processing_queue,
        exchange=queue_service.exchange_name,
        routing_key='data.processing'
    )
    
    # Verify QoS was set
    channel.basic_qos.assert_called_once_with(
        prefetch_count=queue_service.config.prefetch_count
    )


@patch('ocr_service.src.services.queue_service.pika.BlockingConnection')
def test_queue_service_init_connection_error(mock_connection):
    """Test QueueService initialization with connection error."""
    # Configure the mock to raise an exception
    mock_connection.side_effect = AMQPConnectionError("Connection refused")
    
    # Verify that ServiceError is raised with correct category
    with pytest.raises(ServiceError) as excinfo:
        QueueService()
    
    # Verify error details
    assert excinfo.value.category == ErrorCategory.CONNECTION
    assert "Connection refused" in str(excinfo.value)


# ===== Test Connection Decorator =====

def test_with_connection_decorator_reconnect(mock_rabbitmq_connection):
    """Test that the with_connection decorator reconnects if connection is closed."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Mock a closed connection scenario
    queue_service.connected = False
    queue_service.connection.is_closed = True
    
    # Create a test method decorated with with_connection
    @QueueService.with_connection
    def test_method(self):
        return "success"
    
    # Call the test method
    result = test_method(queue_service)
    
    # Verify that reconnection was attempted
    assert queue_service.connected is True
    assert result == "success"


def test_with_connection_decorator_error(mock_rabbitmq_connection):
    """Test that the with_connection decorator handles connection errors."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a test method that raises an AMQPConnectionError
    @QueueService.with_connection
    def test_method(self):
        raise AMQPConnectionError("Connection lost")
    
    # Call the test method and verify that ServiceError is raised
    with pytest.raises(ServiceError) as excinfo:
        test_method(queue_service)
    
    # Verify error details
    assert excinfo.value.category == ErrorCategory.CONNECTION
    assert "Connection lost" in str(excinfo.value)
    assert queue_service.connected is False


# ===== Test Retry Decorator =====

def test_with_retry_decorator_success(mock_rabbitmq_connection):
    """Test that the with_retry decorator returns successful results."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a test method decorated with with_retry
    @QueueService.with_retry
    def test_method(self):
        return Result(success=True, data="success")
    
    # Call the test method
    result = test_method(queue_service)
    
    # Verify result
    assert result.success is True
    assert result.value == "success"


def test_with_retry_decorator_eventual_success(mock_rabbitmq_connection):
    """Test that the with_retry decorator retries until success."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
        # Set a short retry delay for faster tests
        queue_service.retry_delay = 0.01
    
    # Create a counter to track retry attempts
    attempt_counter = {'count': 0}
    
    # Create a test method that fails twice then succeeds
    @QueueService.with_retry
    def test_method(self):
        attempt_counter['count'] += 1
        if attempt_counter['count'] <= 2:
            return Result(success=False, error=ServiceError(
                message="Temporary error",
                category=ErrorCategory.MESSAGING
            ))
        return Result(success=True, data="success after retry")
    
    # Call the test method
    result = test_method(queue_service)
    
    # Verify result
    assert result.success is True
    assert result.value == "success after retry"
    assert attempt_counter['count'] == 3  # Initial attempt + 2 retries


def test_with_retry_decorator_max_retries_exceeded(mock_rabbitmq_connection):
    """Test that the with_retry decorator gives up after max retries."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
        # Set a short retry delay for faster tests
        queue_service.retry_delay = 0.01
        queue_service.max_retries = 3
    
    # Create a test method that always fails
    @QueueService.with_retry
    def test_method(self):
        return Result(success=False, error=ServiceError(
            message="Persistent error",
            category=ErrorCategory.MESSAGING
        ))
    
    # Call the test method
    result = test_method(queue_service)
    
    # Verify result
    assert result.success is False
    assert "Persistent error" in str(result.error)


# ===== Test Message Publishing =====

def test_publish_message_success(mock_rabbitmq_connection):
    """Test successful message publishing."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a test message payload
    payload = {
        "document_id": "doc-12345",
        "storage_path": "mca-documents-staging/applications/doc-12345.pdf",
        "document_type": "APPLICATION",
        "extraction_results": {
            "fields": [],
            "confidence": 0.95,
            "processing_time": 1.5
        }
    }
    
    # Create test headers
    headers = {"source": "ocr-service"}
    
    # Publish the message
    result = queue_service.publish_message(
        payload=payload,
        routing_key="data.processing",
        headers=headers
    )
    
    # Verify result
    assert result.success is True
    
    # Verify that basic_publish was called with correct parameters
    channel.basic_publish.assert_called_once_with(
        exchange=queue_service.exchange_name,
        routing_key="data.processing",
        body=json.dumps(payload).encode('utf-8'),
        properties=ANY
    )
    
    # Verify properties
    properties = channel.basic_publish.call_args[1]['properties']
    assert properties.delivery_mode == 2  # Persistent message
    assert properties.content_type == 'application/json'
    assert properties.headers == headers


def test_publish_message_channel_error(mock_rabbitmq_connection):
    """Test message publishing with channel error."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Configure the channel to raise an exception on basic_publish
    channel.basic_publish.side_effect = AMQPChannelError("Channel closed")
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
        # Disable retries for this test
        queue_service.max_retries = 0
    
    # Create a test message payload
    payload = {"document_id": "doc-12345"}
    
    # Publish the message and verify that it fails
    result = queue_service.publish_message(
        payload=payload,
        routing_key="data.processing"
    )
    
    # Verify result
    assert result.success is False
    assert result.error.category == ErrorCategory.MESSAGING
    assert "Channel closed" in str(result.error)


# ===== Test Message Consumption =====

def test_start_consuming(mock_rabbitmq_connection):
    """Test starting message consumption."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Start consuming messages
    queue_service.start_consuming(callback)
    
    # Verify that basic_consume was called with correct parameters
    channel.basic_consume.assert_called_once_with(
        queue=queue_service.ocr_request_queue,
        on_message_callback=ANY,
        auto_ack=False
    )
    
    # Verify that start_consuming was called
    channel.start_consuming.assert_called_once()


def test_message_handler_success(mock_rabbitmq_connection):
    """Test successful message handling."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Get the message handler function
    # We need to extract the internal message handler from the start_consuming method
    with patch.object(queue_service.channel, 'basic_consume') as mock_basic_consume:
        queue_service.start_consuming(callback)
        # Extract the message handler from the call arguments
        message_handler = mock_basic_consume.call_args[1]['on_message_callback']
    
    # Create mock message components
    method = MagicMock(spec=spec.Basic.Deliver)
    method.delivery_tag = "tag-12345"
    method.routing_key = "ocr.request"
    
    properties = MagicMock(spec=spec.BasicProperties)
    properties.headers = {"source": "document-service"}
    
    body = json.dumps({
        "document_id": "doc-12345",
        "storage_path": "mca-documents-staging/applications/doc-12345.pdf"
    }).encode('utf-8')
    
    # Call the message handler
    message_handler(channel, method, properties, body)
    
    # Verify that the callback was called with correct parameters
    callback.assert_called_once()
    callback_args = callback.call_args[0]
    assert callback_args[0]["document_id"] == "doc-12345"  # payload
    assert callback_args[1] == {"source": "document-service"}  # headers
    assert callback_args[2] == channel  # channel
    assert callback_args[3] == method  # method


def test_message_handler_json_error(mock_rabbitmq_connection):
    """Test message handling with JSON decode error."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Get the message handler function
    with patch.object(queue_service.channel, 'basic_consume') as mock_basic_consume:
        queue_service.start_consuming(callback)
        message_handler = mock_basic_consume.call_args[1]['on_message_callback']
    
    # Create mock message components with invalid JSON
    method = MagicMock(spec=spec.Basic.Deliver)
    method.delivery_tag = "tag-12345"
    properties = MagicMock(spec=spec.BasicProperties)
    properties.headers = {}
    body = b"invalid json"
    
    # Call the message handler
    message_handler(channel, method, properties, body)
    
    # Verify that the callback was NOT called
    callback.assert_not_called()
    
    # Verify that basic_reject was called with requeue=False
    channel.basic_reject.assert_called_once_with(
        delivery_tag=method.delivery_tag,
        requeue=False
    )


def test_message_handler_processing_error(mock_rabbitmq_connection):
    """Test message handling with processing error."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Create a mock callback function that raises an exception
    callback = MagicMock(side_effect=Exception("Processing error"))
    
    # Get the message handler function
    with patch.object(queue_service.channel, 'basic_consume') as mock_basic_consume:
        queue_service.start_consuming(callback)
        message_handler = mock_basic_consume.call_args[1]['on_message_callback']
    
    # Create mock message components
    method = MagicMock(spec=spec.Basic.Deliver)
    method.delivery_tag = "tag-12345"
    properties = MagicMock(spec=spec.BasicProperties)
    properties.headers = {}
    body = json.dumps({"document_id": "doc-12345"}).encode('utf-8')
    
    # Call the message handler
    message_handler(channel, method, properties, body)
    
    # Verify that the callback was called
    callback.assert_called_once()
    
    # Verify that basic_reject was called with requeue=True
    channel.basic_reject.assert_called_once_with(
        delivery_tag=method.delivery_tag,
        requeue=True
    )


# ===== Test Message Acknowledgment and Rejection =====

def test_acknowledge_message(mock_rabbitmq_connection):
    """Test acknowledging a message."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Acknowledge a message
    queue_service.acknowledge_message("tag-12345")
    
    # Verify that basic_ack was called with correct parameters
    channel.basic_ack.assert_called_once_with(delivery_tag="tag-12345")


def test_reject_message(mock_rabbitmq_connection):
    """Test rejecting a message."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Reject a message without requeue
    queue_service.reject_message("tag-12345", requeue=False)
    
    # Verify that basic_reject was called with correct parameters
    channel.basic_reject.assert_called_once_with(
        delivery_tag="tag-12345",
        requeue=False
    )
    
    # Reset the mock
    channel.basic_reject.reset_mock()
    
    # Reject a message with requeue
    queue_service.reject_message("tag-67890", requeue=True)
    
    # Verify that basic_reject was called with correct parameters
    channel.basic_reject.assert_called_once_with(
        delivery_tag="tag-67890",
        requeue=True
    )


# ===== Test Stop Consuming and Close =====

def test_stop_consuming(mock_rabbitmq_connection):
    """Test stopping message consumption."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Set a consumer tag
    queue_service.consumer_tag = "consumer-12345"
    
    # Stop consuming
    queue_service.stop_consuming()
    
    # Verify that basic_cancel was called with correct parameters
    channel.basic_cancel.assert_called_once_with("consumer-12345")
    
    # Verify that consumer_tag was reset
    assert queue_service.consumer_tag is None


def test_close(mock_rabbitmq_connection):
    """Test closing the connection."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
    
    # Set a consumer tag
    queue_service.consumer_tag = "consumer-12345"
    
    # Close the connection
    queue_service.close()
    
    # Verify that stop_consuming was called
    channel.basic_cancel.assert_called_once_with("consumer-12345")
    
    # Verify that channel and connection were closed
    channel.close.assert_called_once()
    connection.close.assert_called_once()
    
    # Verify that connection state was reset
    assert queue_service.connected is False
    assert queue_service.channel is None
    assert queue_service.connection is None


# ===== Test Context Manager =====

def test_context_manager(mock_rabbitmq_connection):
    """Test using QueueService as a context manager."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        # Use QueueService as a context manager
        with QueueService() as queue_service:
            # Verify that connection was established
            assert queue_service.connected is True
            assert queue_service.connection is not None
            assert queue_service.channel is not None
            
            # Publish a test message
            queue_service.publish_message(
                payload={"test": "message"},
                routing_key="test.routing.key"
            )
        
        # Verify that connection was closed after exiting the context
        channel.close.assert_called_once()
        connection.close.assert_called_once()


# ===== Test TLS Configuration =====

@patch('ocr_service.src.services.queue_service.pika.BlockingConnection')
@patch('ocr_service.src.services.queue_service.ssl.create_default_context')
def test_tls_configuration(mock_ssl_context, mock_connection, mock_rabbitmq_connection):
    """Test TLS configuration for RabbitMQ connection."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    mock_connection.return_value = connection
    
    # Create SSL context mock
    ssl_context = MagicMock()
    mock_ssl_context.return_value = ssl_context
    
    # Initialize QueueService
    queue_service = QueueService()
    
    # Verify SSL context was created with correct parameters
    mock_ssl_context.assert_called_once_with(cafile=queue_service.config.ca_cert_path)
    
    # Verify client certificate was loaded
    ssl_context.load_cert_chain.assert_called_once_with(
        certfile=queue_service.config.client_cert_path,
        keyfile=queue_service.config.client_key_path,
        password=queue_service.config.cert_password
    )
    
    # Verify SSL verification settings
    assert ssl_context.verify_mode == ssl.CERT_REQUIRED
    assert ssl_context.check_hostname is True


# ===== Test Exponential Backoff =====

def test_exponential_backoff(mock_rabbitmq_connection):
    """Test exponential backoff in retry logic."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Create a QueueService instance with mocked connection
    with patch('ocr_service.src.services.queue_service.pika.BlockingConnection', return_value=connection):
        queue_service = QueueService()
        # Configure retry parameters
        queue_service.max_retries = 3
        queue_service.retry_delay = 0.1  # 100ms initial delay
    
    # Mock time.sleep to avoid actual delays
    with patch('time.sleep') as mock_sleep:
        # Create a counter to track retry attempts
        attempt_counter = {'count': 0}
        
        # Create a test method that always fails
        @QueueService.with_retry
        def test_method(self):
            attempt_counter['count'] += 1
            return Result(success=False, error=ServiceError(
                message=f"Attempt {attempt_counter['count']} failed",
                category=ErrorCategory.MESSAGING
            ))
        
        # Call the test method
        result = test_method(queue_service)
        
        # Verify result
        assert result.success is False
        assert attempt_counter['count'] == 4  # Initial attempt + 3 retries
        
        # Verify exponential backoff delays
        assert mock_sleep.call_count == 3  # 3 retries
        mock_sleep.assert_has_calls([
            # First retry: base_delay * (2^0) = 0.1
            call(0.1),
            # Second retry: base_delay * (2^1) = 0.2
            call(0.2),
            # Third retry: base_delay * (2^2) = 0.4
            call(0.4)
        ])


# ===== Test Integration with Example Callback =====

def test_example_callback_integration(mock_rabbitmq_connection):
    """Test integration with the example callback function."""
    # Unpack the mock_rabbitmq_connection fixture
    connection, channel = mock_rabbitmq_connection
    
    # Import the example callback
    from ocr_service.src.services.queue_service import example_callback
    
    # Create mock message components
    method = MagicMock(spec=spec.Basic.Deliver)
    method.delivery_tag = "tag-12345"
    
    # Create a test payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "APPLICATION",
        "s3_path": "mca-documents-staging/applications/doc-12345.pdf",
        "correlation_id": "corr-12345"
    }
    
    # Create a mock QueueService for the callback to use
    with patch('ocr_service.src.services.queue_service.QueueService') as MockQueueService:
        mock_queue_service = MagicMock()
        mock_queue_service.publish_message.return_value = Result(success=True, data=True)
        MockQueueService.return_value = mock_queue_service
        
        # Call the example callback
        example_callback(payload, {}, channel, method)
        
        # Verify that the message was acknowledged
        channel.basic_ack.assert_called_once_with(delivery_tag=method.delivery_tag)
        
        # Verify that a result message was published
        mock_queue_service.publish_message.assert_called_once()
        publish_args = mock_queue_service.publish_message.call_args[1]
        
        # Verify the published message
        assert publish_args['routing_key'] == 'data.processing'
        assert publish_args['headers'] == {'source': 'ocr-service'}
        assert publish_args['payload']['document_id'] == 'doc-12345'
        assert publish_args['payload']['document_type'] == 'APPLICATION'
        assert publish_args['payload']['s3_path'] == 'mca-documents-staging/applications/doc-12345.pdf'
        assert 'extraction_results' in publish_args['payload']
        assert 'correlation_id' in publish_args['payload']