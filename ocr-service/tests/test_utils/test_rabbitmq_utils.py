#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the rabbitmq_utils module.

This module contains tests for RabbitMQ connection management, message publishing,
message consumption, error handling, and message serialization/deserialization.
"""

import json
import time
import uuid
from unittest.mock import MagicMock, patch, call, ANY

import pytest
import pika
from pika import spec
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

from ocr_service.src.utils.rabbitmq_utils import (
    RabbitMQConnection,
    with_connection_retry,
    serialize_message,
    deserialize_message,
    create_retry_policy,
    get_retry_delay,
    get_retry_count,
    increment_retry_count
)
from ocr_service.src.types.messages import MessagePayload, MessageHeaders, PublishOptions
from ocr_service.src.types.config import RabbitMQConfig


# Fix the import paths for testing
patch.dict('sys.modules', {
    'ocr_service.src.utils.rabbitmq_utils': __import__('src.utils.rabbitmq_utils', fromlist=['*']),
    'ocr_service.src.types.messages': __import__('src.types.messages', fromlist=['*']),
    'ocr_service.src.types.config': __import__('src.types.config', fromlist=['*']),
    'ocr_service.src.utils.error_utils': __import__('src.utils.error_utils', fromlist=['*']),
    'ocr_service.src.utils.logging_utils': __import__('src.utils.logging_utils', fromlist=['*'])
}).start()


# ===== Test Connection Retry Decorator =====

def test_with_connection_retry_success():
    """Test that the connection retry decorator works when the function succeeds."""
    # Create a mock function that succeeds
    mock_func = MagicMock(return_value="success")
    decorated_func = with_connection_retry()(mock_func)
    
    # Call the decorated function
    result = decorated_func("arg1", kwarg1="value1")
    
    # Verify the function was called once with the correct arguments
    mock_func.assert_called_once_with("arg1", kwarg1="value1")
    assert result == "success"


def test_with_connection_retry_failure_and_retry():
    """Test that the connection retry decorator retries on connection failures."""
    # Create a mock function that fails with a connection error twice, then succeeds
    mock_func = MagicMock(side_effect=[
        AMQPConnectionError("Connection error 1"),
        AMQPConnectionError("Connection error 2"),
        "success"
    ])
    
    # Create the decorated function with a small delay for testing
    decorated_func = with_connection_retry(
        max_retries=3,
        initial_delay=0.01,
        max_delay=0.05,
        backoff_factor=2.0
    )(mock_func)
    
    # Call the decorated function
    result = decorated_func("arg1", kwarg1="value1")
    
    # Verify the function was called three times with the correct arguments
    assert mock_func.call_count == 3
    mock_func.assert_has_calls([
        call("arg1", kwarg1="value1"),
        call("arg1", kwarg1="value1"),
        call("arg1", kwarg1="value1")
    ])
    assert result == "success"


def test_with_connection_retry_max_retries_exceeded():
    """Test that the connection retry decorator raises an exception after max retries."""
    # Create a mock function that always fails with a connection error
    mock_func = MagicMock(side_effect=AMQPConnectionError("Connection error"))
    
    # Create the decorated function with a small delay for testing
    decorated_func = with_connection_retry(
        max_retries=2,
        initial_delay=0.01,
        max_delay=0.05,
        backoff_factor=2.0
    )(mock_func)
    
    # Call the decorated function and expect an exception
    with pytest.raises(AMQPConnectionError, match="Connection error"):
        decorated_func("arg1", kwarg1="value1")
    
    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3  # Initial attempt + 2 retries


def test_with_connection_retry_different_exceptions():
    """Test that the connection retry decorator handles different connection exceptions."""
    # Create a mock function that fails with different connection errors
    mock_func = MagicMock(side_effect=[
        AMQPConnectionError("Connection error"),
        ConnectionClosedByBroker(320, "Connection closed"),
        AMQPChannelError("Channel error"),
        "success"
    ])
    
    # Create the decorated function with a small delay for testing
    decorated_func = with_connection_retry(
        max_retries=3,
        initial_delay=0.01,
        max_delay=0.05,
        backoff_factor=2.0
    )(mock_func)
    
    # Call the decorated function
    result = decorated_func("arg1", kwarg1="value1")
    
    # Verify the function was called four times with the correct arguments
    assert mock_func.call_count == 4
    assert result == "success"


# ===== Test RabbitMQConnection Class =====

@pytest.fixture
def rabbitmq_config():
    """Create a RabbitMQConfig instance for testing."""
    return RabbitMQConfig(
        host="localhost",
        port=5672,
        virtual_host="/",
        username="guest",
        password="guest",
        use_tls=False,
        ca_cert=None,
        client_cert=None,
        client_key=None
    )


def test_rabbitmq_connection_init(rabbitmq_config):
    """Test RabbitMQConnection initialization."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    
    # Verify the connection parameters were set correctly
    assert connection.config == rabbitmq_config
    assert connection.connection is None
    assert connection.channel is None
    assert connection.consuming is False
    
    # Verify connection parameters were initialized
    assert connection.connection_params.host == "localhost"
    assert connection.connection_params.port == 5672
    assert connection.connection_params.virtual_host == "/"
    assert connection.connection_params.credentials.username == "guest"
    assert connection.connection_params.credentials.password == "guest"
    assert connection.connection_params.ssl_options is None


def test_rabbitmq_connection_init_with_tls(rabbitmq_config):
    """Test RabbitMQConnection initialization with TLS enabled."""
    # Update config to use TLS
    rabbitmq_config.use_tls = True
    
    # Mock the SSL context creation
    with patch("ssl.create_default_context") as mock_create_context:
        mock_context = MagicMock()
        mock_create_context.return_value = mock_context
        
        # Create a RabbitMQConnection instance
        connection = RabbitMQConnection(rabbitmq_config)
        
        # Verify SSL context was created
        mock_create_context.assert_called_once()
        assert mock_context.verify_mode == __import__("ssl").CERT_REQUIRED
        
        # Verify connection parameters include SSL options
        assert connection.connection_params.ssl_options is not None


def test_rabbitmq_connect(rabbitmq_connection_mock, rabbitmq_config):
    """Test RabbitMQConnection connect method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    
    # Call the connect method
    connection.connect()
    
    # Verify the connection was established
    rabbitmq_connection_mock.assert_called_once_with(connection.connection_params)
    assert connection.connection is not None
    assert connection.channel is not None
    
    # Verify channel confirm_delivery was called
    connection.channel.confirm_delivery.assert_called_once()


def test_rabbitmq_connect_already_connected(rabbitmq_connection_mock, rabbitmq_config):
    """Test RabbitMQConnection connect method when already connected."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    
    # Set up the connection and channel
    mock_connection = MagicMock()
    mock_connection.is_open = True
    connection.connection = mock_connection
    
    # Call the connect method
    connection.connect()
    
    # Verify no new connection was established
    rabbitmq_connection_mock.assert_not_called()


def test_rabbitmq_close(rabbitmq_config):
    """Test RabbitMQConnection close method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    
    # Set up mock connection and channel
    mock_connection = MagicMock()
    mock_connection.is_open = True
    mock_channel = MagicMock()
    mock_channel.is_open = True
    
    connection.connection = mock_connection
    connection.channel = mock_channel
    connection.consuming = True
    
    # Call the close method
    connection.close()
    
    # Verify stop_consuming was called if consuming
    mock_channel.stop_consuming.assert_called_once()
    
    # Verify channel and connection were closed
    mock_channel.close.assert_called_once()
    mock_connection.close.assert_called_once()
    
    # Verify connection and channel were reset
    assert connection.channel is None
    assert connection.connection is None
    assert connection.consuming is False


def test_rabbitmq_close_with_exceptions(rabbitmq_config):
    """Test RabbitMQConnection close method with exceptions."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    
    # Set up mock connection and channel that raise exceptions
    mock_connection = MagicMock()
    mock_connection.is_open = True
    mock_connection.close.side_effect = Exception("Connection close error")
    
    mock_channel = MagicMock()
    mock_channel.is_open = True
    mock_channel.stop_consuming.side_effect = Exception("Stop consuming error")
    mock_channel.close.side_effect = Exception("Channel close error")
    
    connection.connection = mock_connection
    connection.channel = mock_channel
    connection.consuming = True
    
    # Call the close method
    connection.close()
    
    # Verify connection and channel were reset despite exceptions
    assert connection.channel is None
    assert connection.connection is None
    assert connection.consuming is False


def test_rabbitmq_reconnect(rabbitmq_config):
    """Test RabbitMQConnection reconnect method."""
    # Create a RabbitMQConnection instance with mocked methods
    connection = RabbitMQConnection(rabbitmq_config)
    connection.close = MagicMock()
    connection.connect = MagicMock()
    
    # Call the reconnect method
    connection.reconnect()
    
    # Verify close and connect were called
    connection.close.assert_called_once()
    connection.connect.assert_called_once()


def test_rabbitmq_ensure_connection(rabbitmq_config):
    """Test RabbitMQConnection ensure_connection method."""
    # Create a RabbitMQConnection instance with mocked methods
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect = MagicMock()
    
    # Case 1: No connection
    connection.connection = None
    connection.ensure_connection()
    connection.connect.assert_called_once()
    connection.connect.reset_mock()
    
    # Case 2: Connection not open
    mock_connection = MagicMock()
    mock_connection.is_open = False
    connection.connection = mock_connection
    connection.ensure_connection()
    connection.connect.assert_called_once()
    connection.connect.reset_mock()
    
    # Case 3: Connection open but no channel
    mock_connection.is_open = True
    connection.channel = None
    connection.ensure_connection()
    mock_connection.channel.assert_called_once()
    connection.connect.assert_not_called()
    mock_connection.channel.reset_mock()
    
    # Case 4: Connection and channel open
    mock_channel = MagicMock()
    mock_channel.is_open = True
    connection.channel = mock_channel
    connection.ensure_connection()
    connection.connect.assert_not_called()
    mock_connection.channel.assert_not_called()


def test_rabbitmq_declare_exchange(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection declare_exchange method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the declare_exchange method
    connection.declare_exchange("test-exchange", "topic", True)
    
    # Verify exchange_declare was called with the correct arguments
    rabbitmq_channel_mock.exchange_declare.assert_called_once_with(
        exchange="test-exchange",
        exchange_type="topic",
        durable=True
    )


def test_rabbitmq_declare_queue(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection declare_queue method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the declare_queue method
    arguments = {"x-message-ttl": 60000}
    connection.declare_queue("test-queue", True, arguments)
    
    # Verify queue_declare was called with the correct arguments
    rabbitmq_channel_mock.queue_declare.assert_called_once_with(
        queue="test-queue",
        durable=True,
        arguments=arguments
    )


def test_rabbitmq_bind_queue(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection bind_queue method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the bind_queue method
    connection.bind_queue("test-queue", "test-exchange", "test.routing.key")
    
    # Verify queue_bind was called with the correct arguments
    rabbitmq_channel_mock.queue_bind.assert_called_once_with(
        queue="test-queue",
        exchange="test-exchange",
        routing_key="test.routing.key"
    )


def test_rabbitmq_publish_message(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection publish_message method."""
    # Configure the channel mock to return success
    rabbitmq_channel_mock.basic_publish.return_value = True
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the publish_message method with a dict body
    body = {"key": "value"}
    headers = {"header1": "value1"}
    result = connection.publish_message("test-exchange", "test.routing.key", body, headers)
    
    # Verify basic_publish was called with the correct arguments
    rabbitmq_channel_mock.basic_publish.assert_called_once()
    call_args = rabbitmq_channel_mock.basic_publish.call_args[1]
    assert call_args["exchange"] == "test-exchange"
    assert call_args["routing_key"] == "test.routing.key"
    assert call_args["body"] == json.dumps(body).encode('utf-8')
    assert call_args["mandatory"] is True
    
    # Verify properties were set correctly
    properties = call_args["properties"]
    assert properties.delivery_mode == 2  # Persistent
    assert properties.content_type == "application/json"
    assert properties.headers == headers
    assert properties.app_id == "ocr-service"
    
    # Verify result
    assert result is True


def test_rabbitmq_publish_message_with_string_body(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection publish_message method with a string body."""
    # Configure the channel mock to return success
    rabbitmq_channel_mock.basic_publish.return_value = True
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the publish_message method with a string body
    body = "test message"
    result = connection.publish_message("test-exchange", "test.routing.key", body)
    
    # Verify basic_publish was called with the correct arguments
    rabbitmq_channel_mock.basic_publish.assert_called_once()
    call_args = rabbitmq_channel_mock.basic_publish.call_args[1]
    assert call_args["body"] == body.encode('utf-8')
    
    # Verify result
    assert result is True


def test_rabbitmq_publish_message_with_options(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection publish_message method with PublishOptions."""
    # Configure the channel mock to return success
    rabbitmq_channel_mock.basic_publish.return_value = True
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Create PublishOptions
    options = PublishOptions(
        expiration=60000,
        priority=8,
        correlation_id="test-correlation-id"
    )
    
    # Call the publish_message method with options
    body = {"key": "value"}
    result = connection.publish_message("test-exchange", "test.routing.key", body, options=options)
    
    # Verify basic_publish was called with the correct arguments
    rabbitmq_channel_mock.basic_publish.assert_called_once()
    call_args = rabbitmq_channel_mock.basic_publish.call_args[1]
    
    # Verify properties were set correctly
    properties = call_args["properties"]
    assert properties.expiration == "60000"
    assert properties.priority == 8
    assert properties.correlation_id == "test-correlation-id"
    
    # Verify result
    assert result is True


def test_rabbitmq_publish_message_failure(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection publish_message method when publishing fails."""
    # Configure the channel mock to raise an exception
    rabbitmq_channel_mock.basic_publish.side_effect = AMQPChannelError("Channel error")
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the publish_message method and expect an exception
    with pytest.raises(AMQPChannelError, match="Channel error"):
        connection.publish_message("test-exchange", "test.routing.key", {"key": "value"})


def test_rabbitmq_consume_messages(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection consume_messages method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Call the consume_messages method
    connection.consume_messages("test-queue", callback, auto_ack=False, prefetch_count=10)
    
    # Verify basic_qos was called with the correct arguments
    rabbitmq_channel_mock.basic_qos.assert_called_once_with(prefetch_count=10)
    
    # Verify basic_consume was called with the correct arguments
    rabbitmq_channel_mock.basic_consume.assert_called_once_with(
        queue="test-queue",
        on_message_callback=callback,
        auto_ack=False
    )
    
    # Verify start_consuming was called
    rabbitmq_channel_mock.start_consuming.assert_called_once()
    
    # Verify consuming flag was set
    assert connection.consuming is True


def test_rabbitmq_consume_messages_keyboard_interrupt(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection consume_messages method with KeyboardInterrupt."""
    # Configure the channel mock to raise KeyboardInterrupt
    rabbitmq_channel_mock.start_consuming.side_effect = KeyboardInterrupt()
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Call the consume_messages method
    connection.consume_messages("test-queue", callback)
    
    # Verify stop_consuming was called
    rabbitmq_channel_mock.stop_consuming.assert_called_once()
    
    # Verify consuming flag was reset
    assert connection.consuming is False


def test_rabbitmq_consume_messages_exception(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection consume_messages method with an exception."""
    # Configure the channel mock to raise an exception
    rabbitmq_channel_mock.start_consuming.side_effect = Exception("Consumption error")
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Call the consume_messages method and expect an exception
    with pytest.raises(Exception, match="Consumption error"):
        connection.consume_messages("test-queue", callback)
    
    # Verify consuming flag was reset
    assert connection.consuming is False


def test_rabbitmq_acknowledge_message(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection acknowledge_message method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the acknowledge_message method
    connection.acknowledge_message(123)
    
    # Verify basic_ack was called with the correct arguments
    rabbitmq_channel_mock.basic_ack.assert_called_once_with(delivery_tag=123)


def test_rabbitmq_reject_message(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection reject_message method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the reject_message method
    connection.reject_message(123, requeue=True)
    
    # Verify basic_reject was called with the correct arguments
    rabbitmq_channel_mock.basic_reject.assert_called_once_with(delivery_tag=123, requeue=True)


def test_rabbitmq_nack_message(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test RabbitMQConnection nack_message method."""
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Call the nack_message method
    connection.nack_message(123, multiple=True, requeue=False)
    
    # Verify basic_nack was called with the correct arguments
    rabbitmq_channel_mock.basic_nack.assert_called_once_with(
        delivery_tag=123,
        multiple=True,
        requeue=False
    )


# ===== Test Message Serialization Functions =====

def test_serialize_message():
    """Test serialize_message function."""
    # Create a message payload and headers
    payload = {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }
    
    headers = {
        "correlation_id": "corr-12345",
        "source_service": "ocr-service"
    }
    
    # Serialize the message
    serialized_payload, headers_dict = serialize_message(payload, headers)
    
    # Verify the serialized payload is a JSON string
    assert isinstance(serialized_payload, str)
    assert json.loads(serialized_payload) == payload
    
    # Verify the headers dict
    assert headers_dict == headers


def test_serialize_message_without_headers():
    """Test serialize_message function without headers."""
    # Create a message payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }
    
    # Serialize the message without headers
    serialized_payload, headers_dict = serialize_message(payload)
    
    # Verify the serialized payload is a JSON string
    assert isinstance(serialized_payload, str)
    assert json.loads(serialized_payload) == payload
    
    # Verify the headers dict is empty
    assert headers_dict == {}


def test_deserialize_message():
    """Test deserialize_message function."""
    # Create a message body and properties
    body = json.dumps({
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }).encode('utf-8')
    
    properties = MagicMock()
    properties.headers = {
        "correlation_id": "corr-12345",
        "source_service": "ocr-service"
    }
    
    # Deserialize the message
    payload, headers = deserialize_message(body, properties)
    
    # Verify the deserialized payload
    assert payload == {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }
    
    # Verify the headers
    assert headers == properties.headers


def test_deserialize_message_invalid_json():
    """Test deserialize_message function with invalid JSON."""
    # Create an invalid JSON body
    body = b"invalid json"
    
    properties = MagicMock()
    properties.headers = {"correlation_id": "corr-12345"}
    
    # Deserialize the message
    payload, headers = deserialize_message(body, properties)
    
    # Verify the payload is an empty dict
    assert payload == {}
    
    # Verify the headers
    assert headers == properties.headers


def test_deserialize_message_without_headers():
    """Test deserialize_message function without headers."""
    # Create a message body and properties without headers
    body = json.dumps({
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }).encode('utf-8')
    
    properties = MagicMock()
    properties.headers = None
    
    # Deserialize the message
    payload, headers = deserialize_message(body, properties)
    
    # Verify the deserialized payload
    assert payload == {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }
    
    # Verify the headers is an empty dict
    assert headers == {}


# ===== Test Retry Policy Functions =====

def test_create_retry_policy():
    """Test create_retry_policy function."""
    # Create a retry policy with default values
    policy = create_retry_policy()
    
    # Verify the policy
    assert policy == {
        "max_retries": 3,
        "initial_delay": 1000,
        "backoff_factor": 2.0
    }
    
    # Create a retry policy with custom values
    policy = create_retry_policy(max_retries=5, initial_delay=500, backoff_factor=1.5)
    
    # Verify the policy
    assert policy == {
        "max_retries": 5,
        "initial_delay": 500,
        "backoff_factor": 1.5
    }


def test_get_retry_delay():
    """Test get_retry_delay function."""
    # Calculate retry delays for different retry counts
    delay0 = get_retry_delay(0, 1000, 2.0)  # Initial attempt
    delay1 = get_retry_delay(1, 1000, 2.0)  # First retry
    delay2 = get_retry_delay(2, 1000, 2.0)  # Second retry
    
    # Verify the delays follow exponential backoff
    assert delay0 == 1000
    assert delay1 == 2000  # 1000 * 2^1
    assert delay2 == 4000  # 1000 * 2^2
    
    # Test with different parameters
    delay = get_retry_delay(3, 500, 1.5)
    assert delay == int(500 * (1.5 ** 3))  # 500 * 1.5^3


def test_get_retry_count():
    """Test get_retry_count function."""
    # Test with retry count in headers
    headers = {"x-retry-count": 3}
    assert get_retry_count(headers) == 3
    
    # Test without retry count in headers
    headers = {}
    assert get_retry_count(headers) == 0


def test_increment_retry_count():
    """Test increment_retry_count function."""
    # Test with existing retry count
    headers = {"x-retry-count": 3}
    updated_headers = increment_retry_count(headers)
    assert updated_headers["x-retry-count"] == 4
    assert headers is updated_headers  # Should modify in place
    
    # Test without existing retry count
    headers = {}
    updated_headers = increment_retry_count(headers)
    assert updated_headers["x-retry-count"] == 1
    assert headers is updated_headers  # Should modify in place


# ===== Integration Tests =====

def test_integration_publish_and_consume(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test publishing and consuming messages together."""
    # Configure the channel mock
    rabbitmq_channel_mock.basic_publish.return_value = True
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    connection.connect()
    
    # Declare exchange and queue
    connection.declare_exchange("test-exchange", "topic")
    connection.declare_queue("test-queue")
    connection.bind_queue("test-queue", "test-exchange", "test.routing.key")
    
    # Create a message payload
    payload = {
        "document_id": "doc-12345",
        "document_type": "invoice",
        "status": "processing"
    }
    
    # Publish the message
    result = connection.publish_message("test-exchange", "test.routing.key", payload)
    assert result is True
    
    # Create a mock callback function
    callback = MagicMock()
    
    # Configure the channel to call the callback when consuming
    def side_effect(*args, **kwargs):
        # Simulate a message delivery
        method = MagicMock()
        method.delivery_tag = 123
        
        properties = MagicMock()
        properties.headers = {}
        
        body = json.dumps(payload).encode('utf-8')
        
        # Call the callback with the message
        callback(rabbitmq_channel_mock, method, properties, body)
        
        # Raise KeyboardInterrupt to stop consuming
        raise KeyboardInterrupt()
    
    rabbitmq_channel_mock.start_consuming.side_effect = side_effect
    
    # Consume messages
    connection.consume_messages("test-queue", callback)
    
    # Verify the callback was called with the correct arguments
    callback.assert_called_once()
    call_args = callback.call_args[0]
    assert call_args[0] == rabbitmq_channel_mock
    assert call_args[1].delivery_tag == 123
    assert json.loads(call_args[3].decode('utf-8')) == payload


def test_integration_with_retry_logic(rabbitmq_connection_mock, rabbitmq_channel_mock, rabbitmq_config):
    """Test retry logic for publishing messages."""
    # Configure the channel mock to fail twice, then succeed
    rabbitmq_channel_mock.basic_publish.side_effect = [
        AMQPChannelError("Channel error 1"),
        AMQPChannelError("Channel error 2"),
        True
    ]
    
    # Create a RabbitMQConnection instance
    connection = RabbitMQConnection(rabbitmq_config)
    
    # Create a decorated publish method with retry logic
    @with_connection_retry(max_retries=3, initial_delay=0.01)
    def publish_with_retry():
        connection.ensure_connection()
        return connection.channel.basic_publish(
            exchange="test-exchange",
            routing_key="test.routing.key",
            body=json.dumps({"key": "value"}).encode('utf-8'),
            properties=pika.BasicProperties(),
            mandatory=True
        )
    
    # Call the decorated method
    result = publish_with_retry()
    
    # Verify the method was called three times
    assert rabbitmq_channel_mock.basic_publish.call_count == 3
    assert result is True