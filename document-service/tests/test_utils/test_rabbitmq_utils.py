#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the RabbitMQ utilities in the Document Service.

This module contains tests for RabbitMQ connection management, message publishing,
message consumption, and acknowledgment functions. It ensures that retry logic
is properly implemented for message publishing.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, call

import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

# Import the module to test
from document_service.utils import rabbitmq_utils


# ============================================================================
# Serialization Tests
# ============================================================================

class TestSerialization:
    """Tests for message serialization and deserialization functions."""

    def test_serialize_message_valid(self):
        """Test that a valid message is properly serialized to JSON bytes."""
        # Arrange
        message = {"key": "value", "number": 123, "nested": {"inner": "data"}}
        
        # Act
        result = rabbitmq_utils.serialize_message(message)
        
        # Assert
        assert isinstance(result, bytes)
        assert json.loads(result.decode('utf-8')) == message

    def test_serialize_message_invalid(self):
        """Test that an invalid message raises an exception during serialization."""
        # Arrange
        # Create an object that can't be JSON serialized
        class UnserializableObject:
            pass
        
        message = {"key": UnserializableObject()}
        
        # Act & Assert
        with pytest.raises((TypeError, ValueError)):
            rabbitmq_utils.serialize_message(message)

    def test_deserialize_message_valid(self):
        """Test that valid JSON bytes are properly deserialized to a dictionary."""
        # Arrange
        original_message = {"key": "value", "number": 123, "nested": {"inner": "data"}}
        serialized_message = json.dumps(original_message).encode('utf-8')
        
        # Act
        result = rabbitmq_utils.deserialize_message(serialized_message)
        
        # Assert
        assert result == original_message

    def test_deserialize_message_invalid_json(self):
        """Test that invalid JSON bytes raise an exception during deserialization."""
        # Arrange
        invalid_json = b'{"key": "value", "invalid": }'
        
        # Act & Assert
        with pytest.raises(json.JSONDecodeError):
            rabbitmq_utils.deserialize_message(invalid_json)

    def test_deserialize_message_invalid_encoding(self):
        """Test that bytes with invalid encoding raise an exception during deserialization."""
        # Arrange
        # Create bytes that aren't valid UTF-8
        invalid_encoding = b'\xff\xfe\xfd'
        
        # Act & Assert
        with pytest.raises(UnicodeDecodeError):
            rabbitmq_utils.deserialize_message(invalid_encoding)


# ============================================================================
# Connection Tests
# ============================================================================

class TestConnection:
    """Tests for RabbitMQ connection management functions."""

    @patch('pika.BlockingConnection')
    @patch('pika.ConnectionParameters')
    def test_create_connection_success(self, mock_connection_params, mock_blocking_connection):
        """Test successful RabbitMQ connection creation."""
        # Arrange
        mock_connection = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_params = MagicMock()
        mock_connection_params.return_value = mock_params
        
        # Act
        result = rabbitmq_utils.create_connection()
        
        # Assert
        mock_connection_params.assert_called_once()
        mock_blocking_connection.assert_called_once_with(mock_params)
        assert result == mock_connection

    @patch('pika.BlockingConnection')
    @patch('pika.ConnectionParameters')
    @patch('time.sleep')
    def test_create_connection_retry_success(self, mock_sleep, mock_connection_params, mock_blocking_connection):
        """Test RabbitMQ connection creation with retry that eventually succeeds."""
        # Arrange
        mock_connection = MagicMock()
        mock_params = MagicMock()
        mock_connection_params.return_value = mock_params
        
        # Configure BlockingConnection to fail twice then succeed
        mock_blocking_connection.side_effect = [
            AMQPConnectionError("Connection error 1"),
            AMQPConnectionError("Connection error 2"),
            mock_connection
        ]
        
        # Act
        result = rabbitmq_utils.create_connection(max_retries=5, retry_delay=0)
        
        # Assert
        assert mock_blocking_connection.call_count == 3
        assert mock_sleep.call_count == 2
        assert result == mock_connection

    @patch('pika.BlockingConnection')
    @patch('pika.ConnectionParameters')
    @patch('time.sleep')
    def test_create_connection_retry_failure(self, mock_sleep, mock_connection_params, mock_blocking_connection):
        """Test RabbitMQ connection creation with retry that ultimately fails."""
        # Arrange
        mock_params = MagicMock()
        mock_connection_params.return_value = mock_params
        
        # Configure BlockingConnection to always fail
        error = AMQPConnectionError("Persistent connection error")
        mock_blocking_connection.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPConnectionError) as excinfo:
            rabbitmq_utils.create_connection(max_retries=3, retry_delay=0)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error
        
        # Verify we tried the correct number of times
        assert mock_blocking_connection.call_count == 3
        assert mock_sleep.call_count == 2

    @patch('rabbitmq_utils.create_connection')
    def test_with_rabbitmq_connection_decorator(self, mock_create_connection):
        """Test the with_rabbitmq_connection decorator."""
        # Arrange
        mock_connection = MagicMock()
        mock_create_connection.return_value = mock_connection
        
        # Define a function to decorate
        @rabbitmq_utils.with_rabbitmq_connection
        def test_func(connection, arg1, arg2=None):
            assert connection == mock_connection
            return f"{arg1}-{arg2}"
        
        # Act
        result = test_func("value1", arg2="value2")
        
        # Assert
        assert result == "value1-value2"
        mock_create_connection.assert_called_once()
        mock_connection.close.assert_called_once()

    @patch('rabbitmq_utils.create_connection')
    def test_with_rabbitmq_connection_decorator_exception(self, mock_create_connection):
        """Test the with_rabbitmq_connection decorator when the function raises an exception."""
        # Arrange
        mock_connection = MagicMock()
        mock_create_connection.return_value = mock_connection
        
        # Define a function to decorate that raises an exception
        @rabbitmq_utils.with_rabbitmq_connection
        def test_func(connection):
            raise ValueError("Test exception")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Test exception"):
            test_func()
        
        # Verify connection is still closed
        mock_connection.close.assert_called_once()


# ============================================================================
# Channel Tests
# ============================================================================

class TestChannel:
    """Tests for RabbitMQ channel management functions."""

    def test_create_channel_success(self):
        """Test successful RabbitMQ channel creation."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        # Act
        result = rabbitmq_utils.create_channel(mock_connection)
        
        # Assert
        mock_connection.channel.assert_called_once()
        assert result == mock_channel

    def test_create_channel_failure(self):
        """Test RabbitMQ channel creation failure."""
        # Arrange
        mock_connection = MagicMock()
        error = AMQPChannelError("Channel error")
        mock_connection.channel.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.create_channel(mock_connection)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error

    def test_with_rabbitmq_channel_decorator(self):
        """Test the with_rabbitmq_channel decorator."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        # Define a function to decorate
        @rabbitmq_utils.with_rabbitmq_channel
        def test_func(channel, arg1, arg2=None):
            assert channel == mock_channel
            return f"{arg1}-{arg2}"
        
        # Act
        result = test_func(mock_connection, "value1", arg2="value2")
        
        # Assert
        assert result == "value1-value2"
        mock_connection.channel.assert_called_once()
        mock_channel.close.assert_called_once()

    def test_with_rabbitmq_channel_decorator_exception(self):
        """Test the with_rabbitmq_channel decorator when the function raises an exception."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        
        # Define a function to decorate that raises an exception
        @rabbitmq_utils.with_rabbitmq_channel
        def test_func(channel):
            raise ValueError("Test exception")
        
        # Act & Assert
        with pytest.raises(ValueError, match="Test exception"):
            test_func(mock_connection)
        
        # Verify channel is still closed
        mock_channel.close.assert_called_once()

    def test_with_rabbitmq_decorator(self):
        """Test the with_rabbitmq decorator that handles both connection and channel."""
        # Arrange
        with patch('rabbitmq_utils.create_connection') as mock_create_connection:
            mock_connection = MagicMock()
            mock_channel = MagicMock()
            mock_create_connection.return_value = mock_connection
            mock_connection.channel.return_value = mock_channel
            
            # Define a function to decorate
            @rabbitmq_utils.with_rabbitmq
            def test_func(channel, arg1, arg2=None):
                assert channel == mock_channel
                return f"{arg1}-{arg2}"
            
            # Act
            result = test_func("value1", arg2="value2")
            
            # Assert
            assert result == "value1-value2"
            mock_create_connection.assert_called_once()
            mock_connection.channel.assert_called_once()
            mock_channel.close.assert_called_once()
            mock_connection.close.assert_called_once()


# ============================================================================
# Exchange and Queue Tests
# ============================================================================

class TestExchangeAndQueue:
    """Tests for RabbitMQ exchange and queue management functions."""

    def test_setup_exchange_success(self):
        """Test successful exchange declaration."""
        # Arrange
        mock_channel = MagicMock()
        exchange_name = "test_exchange"
        exchange_type = "fanout"
        
        # Act
        rabbitmq_utils.setup_exchange(mock_channel, exchange_name, exchange_type)
        
        # Assert
        mock_channel.exchange_declare.assert_called_once_with(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=True
        )

    def test_setup_exchange_failure(self):
        """Test exchange declaration failure."""
        # Arrange
        mock_channel = MagicMock()
        error = AMQPChannelError("Exchange error")
        mock_channel.exchange_declare.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.setup_exchange(mock_channel, "test_exchange", "fanout")
        
        # Verify the exception is the same one we created
        assert excinfo.value == error

    def test_setup_queue_success(self):
        """Test successful queue declaration."""
        # Arrange
        mock_channel = MagicMock()
        queue_name = "test_queue"
        mock_result = MagicMock()
        mock_channel.queue_declare.return_value = mock_result
        
        # Act
        result = rabbitmq_utils.setup_queue(mock_channel, queue_name)
        
        # Assert
        mock_channel.queue_declare.assert_called_once_with(
            queue=queue_name,
            durable=True
        )
        assert result == mock_result

    def test_setup_queue_failure(self):
        """Test queue declaration failure."""
        # Arrange
        mock_channel = MagicMock()
        error = AMQPChannelError("Queue error")
        mock_channel.queue_declare.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.setup_queue(mock_channel, "test_queue")
        
        # Verify the exception is the same one we created
        assert excinfo.value == error

    def test_bind_queue_success(self):
        """Test successful queue binding to exchange."""
        # Arrange
        mock_channel = MagicMock()
        queue_name = "test_queue"
        exchange_name = "test_exchange"
        routing_key = "test.routing.key"
        
        # Act
        rabbitmq_utils.bind_queue(mock_channel, queue_name, exchange_name, routing_key)
        
        # Assert
        mock_channel.queue_bind.assert_called_once_with(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )

    def test_bind_queue_failure(self):
        """Test queue binding failure."""
        # Arrange
        mock_channel = MagicMock()
        error = AMQPChannelError("Binding error")
        mock_channel.queue_bind.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.bind_queue(mock_channel, "test_queue", "test_exchange", "test.key")
        
        # Verify the exception is the same one we created
        assert excinfo.value == error


# ============================================================================
# Message Publishing Tests
# ============================================================================

class TestMessagePublishing:
    """Tests for RabbitMQ message publishing functions."""

    @patch('rabbitmq_utils.serialize_message')
    def test_publish_message_success(self, mock_serialize):
        """Test successful message publishing."""
        # Arrange
        mock_channel = MagicMock()
        exchange = "test_exchange"
        routing_key = "test.routing.key"
        message = {"key": "value"}
        serialized_message = b'{"key": "value"}'
        mock_serialize.return_value = serialized_message
        
        # Act
        result = rabbitmq_utils.publish_message(mock_channel, exchange, routing_key, message)
        
        # Assert
        mock_serialize.assert_called_once_with(message)
        mock_channel.basic_publish.assert_called_once()
        args, kwargs = mock_channel.basic_publish.call_args
        assert kwargs['exchange'] == exchange
        assert kwargs['routing_key'] == routing_key
        assert kwargs['body'] == serialized_message
        assert isinstance(kwargs['properties'], pika.BasicProperties)
        assert kwargs['properties'].delivery_mode == 2  # Persistent message
        assert kwargs['properties'].content_type == 'application/json'
        assert result is True

    @patch('rabbitmq_utils.serialize_message')
    @patch('time.sleep')
    def test_publish_message_retry_success(self, mock_sleep, mock_serialize):
        """Test message publishing with retry that eventually succeeds."""
        # Arrange
        mock_channel = MagicMock()
        exchange = "test_exchange"
        routing_key = "test.routing.key"
        message = {"key": "value"}
        serialized_message = b'{"key": "value"}'
        mock_serialize.return_value = serialized_message
        
        # Configure basic_publish to fail twice then succeed
        mock_channel.basic_publish.side_effect = [
            AMQPConnectionError("Connection error 1"),
            AMQPChannelError("Channel error"),
            None  # Success
        ]
        
        # Act
        result = rabbitmq_utils.publish_message(
            mock_channel, exchange, routing_key, message, max_retries=5, retry_delay=0
        )
        
        # Assert
        assert mock_channel.basic_publish.call_count == 3
        assert mock_sleep.call_count == 2
        assert result is True

    @patch('rabbitmq_utils.serialize_message')
    @patch('time.sleep')
    def test_publish_message_retry_failure(self, mock_sleep, mock_serialize):
        """Test message publishing with retry that ultimately fails."""
        # Arrange
        mock_channel = MagicMock()
        exchange = "test_exchange"
        routing_key = "test.routing.key"
        message = {"key": "value"}
        serialized_message = b'{"key": "value"}'
        mock_serialize.return_value = serialized_message
        
        # Configure basic_publish to always fail
        error = AMQPConnectionError("Persistent connection error")
        mock_channel.basic_publish.side_effect = error
        
        # Act
        result = rabbitmq_utils.publish_message(
            mock_channel, exchange, routing_key, message, max_retries=3, retry_delay=0
        )
        
        # Assert
        assert mock_channel.basic_publish.call_count == 3
        assert mock_sleep.call_count == 2
        assert result is False

    @patch('rabbitmq_utils.serialize_message')
    def test_publish_message_with_custom_properties(self, mock_serialize):
        """Test message publishing with custom properties."""
        # Arrange
        mock_channel = MagicMock()
        exchange = "test_exchange"
        routing_key = "test.routing.key"
        message = {"key": "value"}
        serialized_message = b'{"key": "value"}'
        mock_serialize.return_value = serialized_message
        
        custom_properties = pika.BasicProperties(
            content_type='application/json',
            delivery_mode=2,
            message_id='test-message-id',
            correlation_id='test-correlation-id',
            headers={'custom': 'header'}
        )
        
        # Act
        result = rabbitmq_utils.publish_message(
            mock_channel, exchange, routing_key, message, properties=custom_properties
        )
        
        # Assert
        mock_serialize.assert_called_once_with(message)
        mock_channel.basic_publish.assert_called_once()
        args, kwargs = mock_channel.basic_publish.call_args
        assert kwargs['properties'] == custom_properties
        assert result is True


# ============================================================================
# Message Consumption Tests
# ============================================================================

class TestMessageConsumption:
    """Tests for RabbitMQ message consumption functions."""

    @patch('rabbitmq_utils.deserialize_message')
    def test_consume_messages_success(self, mock_deserialize):
        """Test successful message consumption setup."""
        # Arrange
        mock_channel = MagicMock()
        queue = "test_queue"
        callback = MagicMock()
        
        # Mock the deserialization of a message
        deserialized_message = {"key": "value"}
        mock_deserialize.return_value = deserialized_message
        
        # Act
        rabbitmq_utils.consume_messages(mock_channel, queue, callback)
        
        # Assert
        mock_channel.basic_qos.assert_called_once()
        mock_channel.basic_consume.assert_called_once()
        args, kwargs = mock_channel.basic_consume.call_args
        assert kwargs['queue'] == queue
        assert 'on_message_callback' in kwargs
        assert kwargs['auto_ack'] is False
        mock_channel.start_consuming.assert_called_once()
        
        # Test the wrapper callback
        wrapper_callback = kwargs['on_message_callback']
        mock_method = MagicMock()
        mock_method.delivery_tag = "test-tag"
        mock_properties = MagicMock()
        mock_body = b'{"key": "value"}'
        
        # Call the wrapper callback
        wrapper_callback(mock_channel, mock_method, mock_properties, mock_body)
        
        # Verify deserialization and callback
        mock_deserialize.assert_called_once_with(mock_body)
        callback.assert_called_once_with(
            deserialized_message, mock_channel, mock_method, mock_properties
        )

    @patch('rabbitmq_utils.deserialize_message')
    def test_consume_messages_deserialization_error(self, mock_deserialize):
        """Test message consumption with deserialization error."""
        # Arrange
        mock_channel = MagicMock()
        queue = "test_queue"
        callback = MagicMock()
        
        # Mock a deserialization error
        mock_deserialize.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        
        # Act
        rabbitmq_utils.consume_messages(mock_channel, queue, callback)
        
        # Get the wrapper callback
        args, kwargs = mock_channel.basic_consume.call_args
        wrapper_callback = kwargs['on_message_callback']
        
        # Call the wrapper callback with invalid JSON
        mock_method = MagicMock()
        mock_method.delivery_tag = "test-tag"
        mock_properties = MagicMock()
        mock_body = b'invalid json'
        
        # Call the wrapper callback
        wrapper_callback(mock_channel, mock_method, mock_properties, mock_body)
        
        # Verify deserialization was attempted and callback was not called
        mock_deserialize.assert_called_once_with(mock_body)
        callback.assert_not_called()
        mock_channel.basic_nack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag, requeue=True
        )

    @patch('rabbitmq_utils.deserialize_message')
    def test_consume_messages_callback_error(self, mock_deserialize):
        """Test message consumption with callback error."""
        # Arrange
        mock_channel = MagicMock()
        queue = "test_queue"
        callback = MagicMock(side_effect=Exception("Callback error"))
        
        # Mock the deserialization of a message
        deserialized_message = {"key": "value"}
        mock_deserialize.return_value = deserialized_message
        
        # Act
        rabbitmq_utils.consume_messages(mock_channel, queue, callback)
        
        # Get the wrapper callback
        args, kwargs = mock_channel.basic_consume.call_args
        wrapper_callback = kwargs['on_message_callback']
        
        # Call the wrapper callback
        mock_method = MagicMock()
        mock_method.delivery_tag = "test-tag"
        mock_properties = MagicMock()
        mock_body = b'{"key": "value"}'
        
        # Call the wrapper callback
        wrapper_callback(mock_channel, mock_method, mock_properties, mock_body)
        
        # Verify deserialization and callback
        mock_deserialize.assert_called_once_with(mock_body)
        callback.assert_called_once()
        mock_channel.basic_nack.assert_called_once_with(
            delivery_tag=mock_method.delivery_tag, requeue=True
        )

    def test_consume_messages_channel_error(self):
        """Test message consumption with channel error."""
        # Arrange
        mock_channel = MagicMock()
        queue = "test_queue"
        callback = MagicMock()
        
        # Mock a channel error during start_consuming
        error = AMQPChannelError("Channel error")
        mock_channel.start_consuming.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.consume_messages(mock_channel, queue, callback)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error

    def test_consume_messages_connection_error(self):
        """Test message consumption with connection error."""
        # Arrange
        mock_channel = MagicMock()
        queue = "test_queue"
        callback = MagicMock()
        
        # Mock a connection error during start_consuming
        error = AMQPConnectionError("Connection error")
        mock_channel.start_consuming.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPConnectionError) as excinfo:
            rabbitmq_utils.consume_messages(mock_channel, queue, callback)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error

    def test_consume_messages_broker_closed_error(self):
        """Test message consumption with broker closed error."""
        # Arrange
        mock_channel = MagicMock()
        queue = "test_queue"
        callback = MagicMock()
        
        # Mock a broker closed error during start_consuming
        error = ConnectionClosedByBroker(320, "Connection closed by broker")
        mock_channel.start_consuming.side_effect = error
        
        # Act & Assert
        with pytest.raises(ConnectionClosedByBroker) as excinfo:
            rabbitmq_utils.consume_messages(mock_channel, queue, callback)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error


# ============================================================================
# Message Acknowledgment Tests
# ============================================================================

class TestMessageAcknowledgment:
    """Tests for RabbitMQ message acknowledgment functions."""

    def test_acknowledge_message_success(self):
        """Test successful message acknowledgment."""
        # Arrange
        mock_channel = MagicMock()
        delivery_tag = 123
        
        # Act
        rabbitmq_utils.acknowledge_message(mock_channel, delivery_tag)
        
        # Assert
        mock_channel.basic_ack.assert_called_once_with(delivery_tag=delivery_tag)

    def test_acknowledge_message_failure(self):
        """Test message acknowledgment failure."""
        # Arrange
        mock_channel = MagicMock()
        delivery_tag = 123
        error = AMQPChannelError("Ack error")
        mock_channel.basic_ack.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.acknowledge_message(mock_channel, delivery_tag)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error

    def test_reject_message_success(self):
        """Test successful message rejection."""
        # Arrange
        mock_channel = MagicMock()
        delivery_tag = 123
        
        # Act - test with default requeue=True
        rabbitmq_utils.reject_message(mock_channel, delivery_tag)
        
        # Assert
        mock_channel.basic_reject.assert_called_once_with(
            delivery_tag=delivery_tag, requeue=True
        )
        
        # Reset mock
        mock_channel.reset_mock()
        
        # Act - test with requeue=False
        rabbitmq_utils.reject_message(mock_channel, delivery_tag, requeue=False)
        
        # Assert
        mock_channel.basic_reject.assert_called_once_with(
            delivery_tag=delivery_tag, requeue=False
        )

    def test_reject_message_failure(self):
        """Test message rejection failure."""
        # Arrange
        mock_channel = MagicMock()
        delivery_tag = 123
        error = AMQPChannelError("Reject error")
        mock_channel.basic_reject.side_effect = error
        
        # Act & Assert
        with pytest.raises(AMQPChannelError) as excinfo:
            rabbitmq_utils.reject_message(mock_channel, delivery_tag)
        
        # Verify the exception is the same one we created
        assert excinfo.value == error


# ============================================================================
# Cleanup Tests
# ============================================================================

class TestCleanup:
    """Tests for RabbitMQ cleanup functions."""

    def test_close_channel_success(self):
        """Test successful channel closing."""
        # Arrange
        mock_channel = MagicMock()
        mock_channel.is_open = True
        
        # Act
        rabbitmq_utils.close_channel(mock_channel)
        
        # Assert
        mock_channel.close.assert_called_once()

    def test_close_channel_not_open(self):
        """Test channel closing when channel is not open."""
        # Arrange
        mock_channel = MagicMock()
        mock_channel.is_open = False
        
        # Act
        rabbitmq_utils.close_channel(mock_channel)
        
        # Assert
        mock_channel.close.assert_not_called()

    def test_close_channel_exception(self):
        """Test channel closing with exception."""
        # Arrange
        mock_channel = MagicMock()
        mock_channel.is_open = True
        mock_channel.close.side_effect = Exception("Close error")
        
        # Act - should not raise exception
        rabbitmq_utils.close_channel(mock_channel)
        
        # Assert
        mock_channel.close.assert_called_once()

    def test_close_connection_success(self):
        """Test successful connection closing."""
        # Arrange
        mock_connection = MagicMock()
        mock_connection.is_open = True
        
        # Act
        rabbitmq_utils.close_connection(mock_connection)
        
        # Assert
        mock_connection.close.assert_called_once()

    def test_close_connection_not_open(self):
        """Test connection closing when connection is not open."""
        # Arrange
        mock_connection = MagicMock()
        mock_connection.is_open = False
        
        # Act
        rabbitmq_utils.close_connection(mock_connection)
        
        # Assert
        mock_connection.close.assert_not_called()

    def test_close_connection_exception(self):
        """Test connection closing with exception."""
        # Arrange
        mock_connection = MagicMock()
        mock_connection.is_open = True
        mock_connection.close.side_effect = Exception("Close error")
        
        # Act - should not raise exception
        rabbitmq_utils.close_connection(mock_connection)
        
        # Assert
        mock_connection.close.assert_called_once()