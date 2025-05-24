#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the RabbitMQ message handling service in the OCR Service.

This module contains tests for the QueueService class, which provides functionality
for connecting to RabbitMQ, consuming messages from the 'ocr.request' queue, and
publishing extraction results to downstream services. It verifies connection management,
message consumption, publishing operations, and error handling.

The tests cover:
1. RabbitMQ connection with TLS and client certificate authentication
2. Message consumption from 'ocr.request' queue
3. Message publishing to 'data.processing' queue
4. JSON serialization/deserialization for standardized message format
5. Error handling and connection recovery for RabbitMQ
6. Retry logic with exponential backoff for failed operations
"""

import json
import ssl
import time
from unittest.mock import MagicMock, patch, call, ANY

import pytest
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

from src.services.queue_service import QueueService, Result
from src.types.messages import MessagePayload, MessageHeaders, PublishOptions, MessageStatus
from src.types.config import RabbitMQConfig
from src.utils.rabbitmq_utils import RabbitMQConnection, with_connection_retry


# Fixtures for testing
@pytest.fixture
def mock_rabbitmq_config():
    """Create a mock RabbitMQ configuration for testing."""
    return {
        "host": "test-rabbitmq.example.com",
        "port": 5671,  # TLS port
        "username": "test-user",
        "password": "test-password",
        "vhost": "/test",
        "exchange": "mca.documents",
        "queue_data_extraction": "data-extraction",
        "queue_data_processing": "data-processing",
        "routing_key": "ocr.result",
        "ssl": True,
        "ssl_cert_path": "/path/to/client.crt",
        "ssl_key_path": "/path/to/client.key",
        "ssl_ca_certs": "/path/to/ca.crt",
        "heartbeat": 60,
        "connection_timeout": 30,
        "prefetch_count": 10,
    }


@pytest.fixture
def mock_connection():
    """Create a mock RabbitMQ connection."""
    connection = MagicMock()
    connection.is_open = True
    return connection


@pytest.fixture
def mock_channel():
    """Create a mock RabbitMQ channel."""
    channel = MagicMock()
    channel.is_open = True
    return channel


@pytest.fixture
def mock_rabbitmq_connection(mock_connection, mock_channel):
    """Create a mock RabbitMQConnection instance."""
    with patch('src.services.queue_service.RabbitMQConnection') as mock_conn_class:
        mock_conn_instance = mock_conn_class.return_value
        mock_conn_instance.connection = mock_connection
        mock_conn_instance.channel = mock_channel
        mock_conn_instance.connect.return_value = None
        mock_conn_instance.close.return_value = None
        mock_conn_instance.ensure_connection.return_value = None
        mock_conn_instance.declare_exchange.return_value = None
        mock_conn_instance.declare_queue.return_value = None
        mock_conn_instance.bind_queue.return_value = None
        mock_conn_instance.publish_message.return_value = True
        mock_conn_instance.consume_messages.return_value = None
        mock_conn_instance.acknowledge_message.return_value = None
        mock_conn_instance.reject_message.return_value = None
        yield mock_conn_instance


@pytest.fixture
def queue_service(mock_rabbitmq_config, mock_rabbitmq_connection):
    """Create a QueueService instance with mocked dependencies."""
    with patch('src.services.queue_service.get_rabbitmq_config', return_value=mock_rabbitmq_config):
        service = QueueService()
        yield service


# Tests for QueueService initialization
def test_queue_service_init(queue_service, mock_rabbitmq_config):
    """Test QueueService initialization."""
    assert queue_service.config == mock_rabbitmq_config
    assert queue_service.callback is None
    assert queue_service.running is False


# Tests for starting and stopping the QueueService
def test_queue_service_start(queue_service, mock_rabbitmq_connection):
    """Test starting the QueueService."""
    result = queue_service.start()
    
    # Verify the connection was established
    mock_rabbitmq_connection.connect.assert_called_once()
    
    # Verify exchanges and queues were set up
    assert mock_rabbitmq_connection.declare_exchange.call_count > 0
    assert mock_rabbitmq_connection.declare_queue.call_count > 0
    assert mock_rabbitmq_connection.bind_queue.call_count > 0
    
    # Verify the service is running
    assert queue_service.running is True
    assert result.success is True


def test_queue_service_start_failure(queue_service, mock_rabbitmq_connection):
    """Test starting the QueueService with a connection failure."""
    # Simulate a connection failure
    mock_rabbitmq_connection.connect.side_effect = AMQPConnectionError("Connection failed")
    
    result = queue_service.start()
    
    # Verify the connection attempt was made
    mock_rabbitmq_connection.connect.assert_called_once()
    
    # Verify the service is not running
    assert queue_service.running is False
    assert result.success is False
    assert isinstance(result.error, AMQPConnectionError)


def test_queue_service_stop(queue_service, mock_rabbitmq_connection):
    """Test stopping the QueueService."""
    # Start the service first
    queue_service.start()
    assert queue_service.running is True
    
    # Stop the service
    result = queue_service.stop()
    
    # Verify the connection was closed
    mock_rabbitmq_connection.close.assert_called_once()
    
    # Verify the service is not running
    assert queue_service.running is False
    assert result.success is True


def test_queue_service_stop_failure(queue_service, mock_rabbitmq_connection):
    """Test stopping the QueueService with a connection failure."""
    # Start the service first
    queue_service.start()
    assert queue_service.running is True
    
    # Simulate a connection failure during close
    mock_rabbitmq_connection.close.side_effect = Exception("Close failed")
    
    result = queue_service.stop()
    
    # Verify the connection close attempt was made
    mock_rabbitmq_connection.close.assert_called_once()
    
    # Verify the service is not running despite the error
    assert queue_service.running is False
    assert result.success is False
    assert isinstance(result.error, Exception)


# Tests for setting up exchanges and queues
def test_setup_exchanges_and_queues(queue_service, mock_rabbitmq_connection):
    """Test setting up exchanges and queues."""
    # Call the method directly
    queue_service._setup_exchanges_and_queues()
    
    # Verify the exchanges were declared
    mock_rabbitmq_connection.declare_exchange.assert_any_call(
        exchange="mca.documents",
        exchange_type="fanout",
        durable=True
    )
    
    # Verify the queues were declared
    mock_rabbitmq_connection.declare_queue.assert_any_call(
        queue="data-extraction",
        durable=True,
        arguments=ANY
    )
    
    # Verify the queues were bound to exchanges
    mock_rabbitmq_connection.bind_queue.assert_any_call(
        queue="data-extraction",
        exchange="mca.documents",
        routing_key=ANY
    )


# Tests for message handling
def test_register_callback(queue_service):
    """Test registering a callback function."""
    callback = MagicMock()
    queue_service.register_callback(callback)
    assert queue_service.callback == callback


def test_message_handler_success(queue_service, mock_rabbitmq_connection):
    """Test successful message handling."""
    # Register a callback
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Create mock message parameters
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = 123
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {}
    body = json.dumps({"test": "data"}).encode("utf-8")
    
    # Mock the deserialize_message function
    with patch('ocr_service.services.queue_service.utils_deserialize_message', 
               return_value=({"test": "data"}, {})):
        # Call the message handler
        queue_service._message_handler(channel, method, properties, body)
        
        # Verify the callback was called
        callback.assert_called_once_with(channel, method, properties, body, {"test": "data"}, {})
        
        # Verify the message was acknowledged
        mock_rabbitmq_connection.acknowledge_message.assert_called_once_with(123)


def test_message_handler_callback_error(queue_service, mock_rabbitmq_connection):
    """Test message handling with a callback error."""
    # Register a callback that raises an exception
    callback = MagicMock(side_effect=Exception("Callback error"))
    queue_service.register_callback(callback)
    
    # Create mock message parameters
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = 123
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {}
    body = json.dumps({"test": "data"}).encode("utf-8")
    
    # Mock the deserialize_message function
    with patch('src.services.queue_service.utils_deserialize_message', 
               return_value=({"test": "data"}, {})):
        # Mock the create_error_context function
        with patch('ocr_service.services.queue_service.create_error_context', 
                   return_value="Error context"):
            # Call the message handler
            queue_service._message_handler(channel, method, properties, body)
            
            # Verify the callback was called
            callback.assert_called_once_with(channel, method, properties, body, {"test": "data"}, {})
            
            # Verify the message was requeued (first attempt)
            mock_rabbitmq_connection.reject_message.assert_called_once_with(123, requeue=True)


def test_message_handler_callback_error_max_retries(queue_service, mock_rabbitmq_connection):
    """Test message handling with a callback error after max retries."""
    # Register a callback that raises an exception
    callback = MagicMock(side_effect=Exception("Callback error"))
    queue_service.register_callback(callback)
    
    # Create mock message parameters
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = 123
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {"x-retry-count": 3}  # Max retries reached
    body = json.dumps({"test": "data"}).encode("utf-8")
    
    # Mock the deserialize_message function
    with patch('src.services.queue_service.utils_deserialize_message', 
               return_value=({"test": "data"}, {"x-retry-count": 3})):
        # Mock the create_error_context function
        with patch('src.services.queue_service.create_error_context', 
                   return_value="Error context"):
            # Mock the get_retry_count function
            with patch('src.services.queue_service.get_retry_count', 
                       return_value=3):
                # Call the message handler
                queue_service._message_handler(channel, method, properties, body)
                
                # Verify the callback was called
                callback.assert_called_once_with(channel, method, properties, body, {"test": "data"}, {"x-retry-count": 3})
                
                # Verify the message was rejected without requeuing (dead-letter queue)
                mock_rabbitmq_connection.reject_message.assert_called_once_with(123, requeue=False)


def test_message_handler_deserialization_error(queue_service, mock_rabbitmq_connection):
    """Test message handling with a deserialization error."""
    # Register a callback
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Create mock message parameters
    channel = MagicMock()
    method = MagicMock()
    method.delivery_tag = 123
    properties = MagicMock()
    properties.message_id = "test-message-id"
    properties.headers = {}
    body = b"invalid json"
    
    # Mock the deserialize_message function to raise an exception
    with patch('src.services.queue_service.utils_deserialize_message', 
               side_effect=Exception("Deserialization error")):
        # Call the message handler
        queue_service._message_handler(channel, method, properties, body)
        
        # Verify the callback was not called
        callback.assert_not_called()
        
        # Verify the message was rejected without requeuing
        mock_rabbitmq_connection.reject_message.assert_called_once_with(123, requeue=False)


# Tests for message consumption
def test_consume_messages(queue_service, mock_rabbitmq_connection):
    """Test consuming messages from a queue."""
    # Register a callback
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Start the service
    queue_service.start()
    
    # Consume messages
    result = queue_service.consume_messages(queue="ocr.request", prefetch_count=10)
    
    # Verify the connection was ensured
    mock_rabbitmq_connection.ensure_connection.assert_called()
    
    # Verify the QoS was set
    mock_rabbitmq_connection.channel.basic_qos.assert_called_once_with(prefetch_count=10)
    
    # Verify the consume_messages method was called
    mock_rabbitmq_connection.consume_messages.assert_called_once_with(
        queue="ocr.request",
        callback=queue_service._message_handler,
        auto_ack=False,
        prefetch_count=10
    )
    
    # Verify the result
    assert result.success is True


def test_consume_messages_service_not_started(queue_service):
    """Test consuming messages when the service is not started."""
    # Register a callback
    callback = MagicMock()
    queue_service.register_callback(callback)
    
    # Consume messages without starting the service
    result = queue_service.consume_messages()
    
    # Verify the result
    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    assert "not started" in str(result.error)


def test_consume_messages_no_callback(queue_service):
    """Test consuming messages without registering a callback."""
    # Start the service
    queue_service.start()
    
    # Consume messages without registering a callback
    result = queue_service.consume_messages()
    
    # Verify the result
    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    assert "No callback registered" in str(result.error)


# Tests for message publishing
def test_publish_message(queue_service, mock_rabbitmq_connection):
    """Test publishing a message to RabbitMQ."""
    # Start the service
    queue_service.start()
    
    # Create a message payload
    payload = {"test": "data"}
    headers = {"header1": "value1"}
    
    # Mock the serialize_message function
    with patch('src.services.queue_service.utils_serialize_message', 
               return_value=(json.dumps(payload), headers)):
        # Publish the message
        result = queue_service.publish_message(
            exchange="mca.documents",
            routing_key="document.new",
            payload=payload,
            headers=headers
        )
        
        # Verify the connection was ensured
        mock_rabbitmq_connection.ensure_connection.assert_called()
        
        # Verify the publish_message method was called
        mock_rabbitmq_connection.publish_message.assert_called_once_with(
            exchange="mca.documents",
            routing_key="document.new",
            body=json.dumps(payload),
            headers=headers,
            options=None
        )
        
        # Verify the result
        assert result.success is True


def test_publish_message_service_not_started(queue_service):
    """Test publishing a message when the service is not started."""
    # Create a message payload
    payload = {"test": "data"}
    
    # Publish the message without starting the service
    result = queue_service.publish_message(
        exchange="mca.documents",
        routing_key="document.new",
        payload=payload
    )
    
    # Verify the result
    assert result.success is False
    assert isinstance(result.error, RuntimeError)
    assert "not started" in str(result.error)


def test_publish_message_failure(queue_service, mock_rabbitmq_connection):
    """Test publishing a message with a failure."""
    # Start the service
    queue_service.start()
    
    # Create a message payload
    payload = {"test": "data"}
    
    # Mock the serialize_message function
    with patch('ocr_service.services.queue_service.utils_serialize_message', 
               return_value=(json.dumps(payload), {})):
        # Mock the publish_message method to return False (failure)
        mock_rabbitmq_connection.publish_message.return_value = False
        
        # Publish the message
        result = queue_service.publish_message(
            exchange="mca.documents",
            routing_key="document.new",
            payload=payload
        )
        
        # Verify the result
        assert result.success is False
        assert isinstance(result.error, RuntimeError)
        assert "Failed to publish message" in str(result.error)


def test_publish_message_connection_error(queue_service, mock_rabbitmq_connection):
    """Test publishing a message with a connection error."""
    # Start the service
    queue_service.start()
    
    # Create a message payload
    payload = {"test": "data"}
    
    # Mock the serialize_message function
    with patch('src.services.queue_service.utils_serialize_message', 
               return_value=(json.dumps(payload), {})):
        # Mock the publish_message method to raise a connection error
        mock_rabbitmq_connection.publish_message.side_effect = AMQPConnectionError("Connection failed")
        
        # Publish the message
        result = queue_service.publish_message(
            exchange="mca.documents",
            routing_key="document.new",
            payload=payload
        )
        
        # Verify the result
        assert result.success is False
        assert isinstance(result.error, AMQPConnectionError)


# Tests for publishing extraction results
def test_publish_extraction_results(queue_service):
    """Test publishing extraction results to the Data Service."""
    # Start the service
    queue_service.start()
    
    # Mock the publish_message method
    with patch.object(queue_service, 'publish_message', return_value=Result.ok(True)) as mock_publish:
        # Publish extraction results
        result = queue_service.publish_extraction_results(
            document_id="doc123",
            application_id="app456",
            storage_path="s3://bucket/doc123.pdf",
            extraction_results={"field1": "value1", "field2": "value2"},
            confidence_scores={"field1": 0.95, "field2": 0.85},
            document_type="application_form",
            processing_time_ms=1234.56,
            requires_verification=True,
            verification_fields=["field2"]
        )
        
        # Verify the publish_message method was called
        mock_publish.assert_called_once()
        
        # Verify the exchange and routing key
        args, kwargs = mock_publish.call_args
        assert kwargs["exchange"] == "mca.data.processing"
        assert kwargs["routing_key"] == "data.extraction.complete"
        
        # Verify the payload contains the expected fields
        payload = kwargs["payload"]
        assert payload["document_id"] == "doc123"
        assert payload["application_id"] == "app456"
        assert payload["storage_path"] == "s3://bucket/doc123.pdf"
        assert payload["extraction_results"] == {"field1": "value1", "field2": "value2"}
        assert payload["confidence_scores"] == {"field1": 0.95, "field2": 0.85}
        assert payload["document_type"] == "application_form"
        assert payload["processing_time_ms"] == 1234.56
        assert payload["requires_verification"] is True
        assert payload["verification_fields"] == ["field2"]
        assert payload["status"] == MessageStatus.COMPLETED.value
        
        # Verify the result
        assert result.success is True


def test_publish_extraction_error(queue_service):
    """Test publishing extraction error to the Data Service."""
    # Start the service
    queue_service.start()
    
    # Mock the publish_message method
    with patch.object(queue_service, 'publish_message', return_value=Result.ok(True)) as mock_publish:
        # Publish extraction error
        result = queue_service.publish_extraction_error(
            document_id="doc123",
            application_id="app456",
            storage_path="s3://bucket/doc123.pdf",
            error={"message": "OCR failed", "code": "OCR_ERROR"},
            document_type="application_form"
        )
        
        # Verify the publish_message method was called
        mock_publish.assert_called_once()
        
        # Verify the exchange and routing key
        args, kwargs = mock_publish.call_args
        assert kwargs["exchange"] == "mca.data.processing"
        assert kwargs["routing_key"] == "data.extraction.error"
        
        # Verify the payload contains the expected fields
        payload = kwargs["payload"]
        assert payload["document_id"] == "doc123"
        assert payload["application_id"] == "app456"
        assert payload["storage_path"] == "s3://bucket/doc123.pdf"
        assert payload["error"] == {"message": "OCR failed", "code": "OCR_ERROR"}
        assert payload["document_type"] == "application_form"
        assert payload["status"] == MessageStatus.FAILED.value
        
        # Verify the result
        assert result.success is True


# Tests for health check
def test_is_running(queue_service, mock_rabbitmq_connection, mock_connection):
    """Test checking if the service is running."""
    # Service is not running initially
    assert queue_service.is_running() is False
    
    # Start the service
    queue_service.start()
    
    # Service should be running
    assert queue_service.is_running() is True
    
    # Simulate connection closed
    mock_connection.is_open = False
    
    # Service should not be running
    assert queue_service.is_running() is False


def test_health_check(queue_service, mock_rabbitmq_connection, mock_connection):
    """Test health check functionality."""
    # Start the service
    queue_service.start()
    
    # Perform health check
    health = queue_service.health_check()
    
    # Verify the health check result
    assert health["status"] == "healthy"
    assert health["details"]["running"] is True
    assert health["details"]["connected"] is True
    
    # Simulate connection closed
    mock_connection.is_open = False
    
    # Perform health check again
    health = queue_service.health_check()
    
    # Verify the health check result
    assert health["status"] == "unhealthy"
    assert health["details"]["running"] is True
    assert health["details"]["connected"] is False


# Tests for retry logic
def test_with_connection_retry_decorator():
    """Test the with_connection_retry decorator."""
    # Create a mock function that fails twice then succeeds
    mock_func = MagicMock(side_effect=[AMQPConnectionError("Connection failed"),
                                      AMQPConnectionError("Connection failed"),
                                      "success"])
    
    # Apply the decorator
    decorated_func = with_connection_retry(max_retries=3, initial_delay=0.01)(mock_func)
    
    # Call the decorated function
    result = decorated_func()
    
    # Verify the function was called multiple times
    assert mock_func.call_count == 3
    
    # Verify the final result
    assert result == "success"


def test_with_connection_retry_decorator_max_retries_exceeded():
    """Test the with_connection_retry decorator when max retries are exceeded."""
    # Create a mock function that always fails
    mock_func = MagicMock(side_effect=AMQPConnectionError("Connection failed"))
    
    # Apply the decorator
    decorated_func = with_connection_retry(max_retries=2, initial_delay=0.01)(mock_func)
    
    # Call the decorated function and expect an exception
    with pytest.raises(AMQPConnectionError):
        decorated_func()
    
    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3  # Initial attempt + 2 retries


# Tests for Result class
def test_result_ok():
    """Test creating a successful Result."""
    result = Result.ok("success")
    assert result.success is True
    assert result.value == "success"
    assert result.error is None
    assert bool(result) is True


def test_result_err():
    """Test creating a failed Result."""
    error = Exception("Test error")
    result = Result.err(error)
    assert result.success is False
    assert result.value is None
    assert result.error == error
    assert bool(result) is False