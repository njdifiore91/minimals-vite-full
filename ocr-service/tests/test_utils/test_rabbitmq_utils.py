#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the rabbitmq_utils.py module.

This module contains tests for RabbitMQ connection management, message publishing with retry logic,
message consumption and acknowledgment, channel and connection error handling, and message
serialization to ensure reliable messaging in the OCR Service.
"""

import json
import os
import pytest
import ssl
import sys
from unittest.mock import MagicMock, patch, call, ANY

import pika
from pika.exceptions import (
    AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker,
    StreamLostError, ChannelClosedByBroker, ChannelWrongStateError
)

# Add the src directory to the path so we can import the modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from utils import rabbitmq_utils
from utils.rabbitmq_utils import (
    RabbitMQClient, RabbitMQConnectionError, RabbitMQChannelError,
    serialize_message, deserialize_message, create_rabbitmq_client_from_env,
    setup_ocr_queues, create_ocr_result_message, publish_ocr_result,
    DEFAULT_EXCHANGE, DEFAULT_OCR_REQUEST_QUEUE, DEFAULT_PROCESSING_QUEUE
)


# ===== RabbitMQClient Initialization Tests =====

class TestRabbitMQClientInitialization:
    """Tests for RabbitMQClient initialization and connection setup."""

    def test_init_with_default_values(self):
        """Test initialization with default values."""
        client = RabbitMQClient(host="localhost")
        
        assert client.host == "localhost"
        assert client.port == 5672
        assert client.virtual_host == "/"
        assert client.username == "guest"
        assert client.password == "guest"
        assert client.exchange == "mca.documents"
        assert client.exchange_type == "topic"
        assert client.prefetch_count == 10
        assert client.connection is None
        assert client.channel is None
        assert client.is_connected is False
        assert client.ssl_options is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        client = RabbitMQClient(
            host="rabbitmq.example.com",
            port=5673,
            virtual_host="/test",
            username="test_user",
            password="test_password",
            connection_attempts=5,
            retry_delay=3,
            heartbeat=30,
            blocked_connection_timeout=200,
            exchange="test.exchange",
            exchange_type="direct",
            prefetch_count=20
        )
        
        assert client.host == "rabbitmq.example.com"
        assert client.port == 5673
        assert client.virtual_host == "/test"
        assert client.username == "test_user"
        assert client.password == "test_password"
        assert client.connection_attempts == 5
        assert client.retry_delay == 3
        assert client.heartbeat == 30
        assert client.blocked_connection_timeout == 200
        assert client.exchange == "test.exchange"
        assert client.exchange_type == "direct"
        assert client.prefetch_count == 20

    def test_setup_ssl_context_from_env_vars(self):
        """Test SSL context setup from environment variables."""
        with patch.dict(os.environ, {
            "RABBITMQ_USE_TLS": "true",
            "RABBITMQ_VERIFY_SSL": "true",
            "RABBITMQ_CA_CERT": "/path/to/ca.crt",
            "RABBITMQ_CLIENT_CERT": "/path/to/client.crt",
            "RABBITMQ_CLIENT_KEY": "/path/to/client.key"
        }), patch("os.path.exists", return_value=True), \
        patch("ssl.SSLContext") as mock_ssl_context:
            # Configure the mock SSL context
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            
            client = RabbitMQClient(host="localhost")
            
            # Verify SSL context was created with TLS 1.2
            mock_ssl_context.assert_called_once_with(ssl.PROTOCOL_TLSv1_2)
            
            # Verify cipher configuration
            mock_context.set_ciphers.assert_called_once_with("ECDHE+AESGCM:!ECDSA")
            
            # Verify certificate verification mode
            assert mock_context.verify_mode == ssl.CERT_REQUIRED
            
            # Verify CA certificate loading
            mock_context.load_verify_locations.assert_called_once_with(cafile="/path/to/ca.crt")
            
            # Verify client certificate loading
            mock_context.load_cert_chain.assert_called_once_with(
                "/path/to/client.crt", "/path/to/client.key"
            )
            
            # Verify SSL options were created
            assert client.ssl_options is not None

    def test_setup_ssl_context_with_verify_disabled(self):
        """Test SSL context setup with certificate verification disabled."""
        with patch.dict(os.environ, {
            "RABBITMQ_USE_TLS": "true",
            "RABBITMQ_VERIFY_SSL": "false"
        }), patch("ssl.SSLContext") as mock_ssl_context:
            # Configure the mock SSL context
            mock_context = MagicMock()
            mock_ssl_context.return_value = mock_context
            
            client = RabbitMQClient(host="localhost")
            
            # Verify verification mode is set to CERT_NONE
            assert mock_context.verify_mode == ssl.CERT_NONE


# ===== RabbitMQClient Connection Tests =====

class TestRabbitMQClientConnection:
    """Tests for RabbitMQClient connection management."""

    def test_connect_success(self, mock_pika_blocking_connection):
        """Test successful connection to RabbitMQ."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Verify connection was established
        assert client.is_connected is True
        assert client.connection is not None
        assert client.channel is not None
        
        # Verify connection parameters
        pika.ConnectionParameters.assert_called_once_with(
            host="localhost",
            port=5672,
            virtual_host="/",
            credentials=ANY,
            connection_attempts=3,
            retry_delay=2,
            heartbeat=60,
            blocked_connection_timeout=300,
            ssl_options=None
        )
        
        # Verify channel setup
        client.channel.basic_qos.assert_called_once_with(prefetch_count=10)
        client.channel.exchange_declare.assert_called_once_with(
            exchange="mca.documents",
            exchange_type="topic",
            durable=True
        )

    def test_connect_already_connected(self, mock_pika_blocking_connection):
        """Test connect when already connected."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Reset mocks to verify they're not called again
        mock_pika_blocking_connection.reset_mock()
        client.channel.reset_mock()
        
        # Call connect again
        client.connect()
        
        # Verify no new connection was created
        mock_pika_blocking_connection.assert_not_called()
        client.channel.exchange_declare.assert_not_called()

    def test_connect_failure(self):
        """Test connection failure."""
        with patch("pika.BlockingConnection", side_effect=AMQPConnectionError("Connection refused")), \
             patch("pika.ConnectionParameters"):
            client = RabbitMQClient(host="localhost")
            
            with pytest.raises(RabbitMQConnectionError) as excinfo:
                client.connect()
            
            assert "Failed to connect to RabbitMQ" in str(excinfo.value)
            assert client.is_connected is False
            assert client.connection is None
            assert client.channel is None

    def test_ensure_connection_when_not_connected(self):
        """Test ensure_connection when not connected."""
        with patch.object(RabbitMQClient, "connect") as mock_connect:
            client = RabbitMQClient(host="localhost")
            client.is_connected = False
            
            client.ensure_connection()
            
            mock_connect.assert_called_once()

    def test_ensure_connection_when_connected(self, mock_pika_blocking_connection):
        """Test ensure_connection when already connected."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        with patch.object(RabbitMQClient, "connect") as mock_connect:
            client.ensure_connection()
            
            mock_connect.assert_not_called()

    def test_close_connection(self, mock_pika_blocking_connection):
        """Test closing the connection."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        client.close()
        
        # Verify channel and connection were closed
        client.channel.close.assert_called_once()
        client.connection.close.assert_called_once()
        
        # Verify state was reset
        assert client.is_connected is False
        assert client.channel is None
        assert client.connection is None

    def test_close_connection_with_error(self, mock_pika_blocking_connection):
        """Test closing the connection when an error occurs."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Make channel.close raise an exception
        client.channel.close.side_effect = Exception("Failed to close channel")
        
        client.close()
        
        # Verify connection was still closed
        client.connection.close.assert_called_once()
        
        # Verify state was reset despite the error
        assert client.is_connected is False
        assert client.channel is None
        assert client.connection is None


# ===== RabbitMQClient Queue and Exchange Tests =====

class TestRabbitMQClientQueueOperations:
    """Tests for RabbitMQClient queue and exchange operations."""

    def test_declare_queue_success(self, mock_pika_blocking_connection):
        """Test successful queue declaration."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        client.declare_queue(
            queue_name="test-queue",
            durable=True,
            exclusive=False,
            auto_delete=False,
            arguments={"x-message-ttl": 60000}
        )
        
        # Verify queue was declared
        client.channel.queue_declare.assert_called_once_with(
            queue="test-queue",
            durable=True,
            exclusive=False,
            auto_delete=False,
            arguments={"x-message-ttl": 60000}
        )

    def test_declare_queue_failure(self, mock_pika_blocking_connection):
        """Test queue declaration failure."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Make queue_declare raise an exception
        client.channel.queue_declare.side_effect = AMQPChannelError("Queue already exists")
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.declare_queue(queue_name="test-queue")
        
        assert "Failed to declare queue test-queue" in str(excinfo.value)

    def test_bind_queue_success(self, mock_pika_blocking_connection):
        """Test successful queue binding."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        client.bind_queue(
            queue_name="test-queue",
            exchange="test-exchange",
            routing_key="test.routing.key"
        )
        
        # Verify queue was bound
        client.channel.queue_bind.assert_called_once_with(
            queue="test-queue",
            exchange="test-exchange",
            routing_key="test.routing.key"
        )

    def test_bind_queue_with_default_exchange(self, mock_pika_blocking_connection):
        """Test queue binding with default exchange."""
        client = RabbitMQClient(host="localhost", exchange="default-exchange")
        client.connect()
        
        client.bind_queue(
            queue_name="test-queue",
            routing_key="test.routing.key"
        )
        
        # Verify queue was bound to default exchange
        client.channel.queue_bind.assert_called_once_with(
            queue="test-queue",
            exchange="default-exchange",
            routing_key="test.routing.key"
        )

    def test_bind_queue_failure(self, mock_pika_blocking_connection):
        """Test queue binding failure."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Make queue_bind raise an exception
        client.channel.queue_bind.side_effect = AMQPChannelError("Exchange not found")
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.bind_queue(
                queue_name="test-queue",
                exchange="non-existent-exchange"
            )
        
        assert "Failed to bind queue test-queue to exchange non-existent-exchange" in str(excinfo.value)


# ===== RabbitMQClient Message Publishing Tests =====

class TestRabbitMQClientPublishing:
    """Tests for RabbitMQClient message publishing."""

    def test_publish_dict_message_success(self, mock_pika_blocking_connection):
        """Test successful publishing of a dictionary message."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to return True (success)
        client.channel.basic_publish.return_value = True
        
        message = {"key": "value", "nested": {"data": [1, 2, 3]}}
        result = client.publish(
            message=message,
            routing_key="test.routing.key"
        )
        
        # Verify message was published
        assert result is True
        client.channel.basic_publish.assert_called_once_with(
            exchange="mca.documents",
            routing_key="test.routing.key",
            body=json.dumps(message).encode('utf-8'),
            properties=ANY,
            mandatory=False
        )
        
        # Verify properties
        properties = client.channel.basic_publish.call_args[1]["properties"]
        assert properties.content_type == "application/json"
        assert properties.delivery_mode == 2  # Persistent

    def test_publish_string_message_success(self, mock_pika_blocking_connection):
        """Test successful publishing of a string message."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to return True (success)
        client.channel.basic_publish.return_value = True
        
        message = "Test message"
        result = client.publish(
            message=message,
            routing_key="test.routing.key"
        )
        
        # Verify message was published
        assert result is True
        client.channel.basic_publish.assert_called_once_with(
            exchange="mca.documents",
            routing_key="test.routing.key",
            body=message.encode('utf-8'),
            properties=ANY,
            mandatory=False
        )
        
        # Verify properties
        properties = client.channel.basic_publish.call_args[1]["properties"]
        assert properties.content_type == "text/plain"

    def test_publish_bytes_message_success(self, mock_pika_blocking_connection):
        """Test successful publishing of a bytes message."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to return True (success)
        client.channel.basic_publish.return_value = True
        
        message = b"Test binary message"
        result = client.publish(
            message=message,
            routing_key="test.routing.key"
        )
        
        # Verify message was published
        assert result is True
        client.channel.basic_publish.assert_called_once_with(
            exchange="mca.documents",
            routing_key="test.routing.key",
            body=message,
            properties=ANY,
            mandatory=False
        )

    def test_publish_with_custom_properties(self, mock_pika_blocking_connection):
        """Test publishing with custom message properties."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to return True (success)
        client.channel.basic_publish.return_value = True
        
        message = {"key": "value"}
        properties = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2,
            message_id="test-message-id",
            correlation_id="test-correlation-id",
            headers={"source": "test"}
        )
        
        result = client.publish(
            message=message,
            routing_key="test.routing.key",
            properties=properties
        )
        
        # Verify message was published with custom properties
        assert result is True
        client.channel.basic_publish.assert_called_once_with(
            exchange="mca.documents",
            routing_key="test.routing.key",
            body=json.dumps(message).encode('utf-8'),
            properties=properties,
            mandatory=False
        )

    def test_publish_with_custom_exchange(self, mock_pika_blocking_connection):
        """Test publishing to a custom exchange."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to return True (success)
        client.channel.basic_publish.return_value = True
        
        message = {"key": "value"}
        result = client.publish(
            message=message,
            exchange="custom-exchange",
            routing_key="test.routing.key"
        )
        
        # Verify message was published to custom exchange
        assert result is True
        client.channel.basic_publish.assert_called_once_with(
            exchange="custom-exchange",
            routing_key="test.routing.key",
            body=json.dumps(message).encode('utf-8'),
            properties=ANY,
            mandatory=False
        )

    def test_publish_with_connection_error_and_retry(self, mock_pika_blocking_connection):
        """Test publishing with a connection error that triggers a retry."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to fail with connection error on first call, then succeed
        client.channel.basic_publish.side_effect = [
            ConnectionClosedByBroker(0, "Connection closed"),
            True
        ]
        
        # Mock close and connect methods
        with patch.object(client, "close") as mock_close, \
             patch.object(client, "connect") as mock_connect:
            
            message = {"key": "value"}
            result = client.publish(
                message=message,
                routing_key="test.routing.key"
            )
            
            # Verify connection was closed and reopened
            mock_close.assert_called_once()
            mock_connect.assert_called_once()
            
            # Verify message was published successfully on retry
            assert result is True
            assert client.channel.basic_publish.call_count == 2

    def test_publish_with_channel_error_and_retry(self, mock_pika_blocking_connection):
        """Test publishing with a channel error that triggers a retry."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_publish to fail with channel error on first call, then succeed
        client.channel.basic_publish.side_effect = [
            ChannelClosedByBroker(0, "Channel closed"),
            True
        ]
        
        # Mock connection.channel method to return a new channel
        new_channel = MagicMock()
        client.connection.channel.return_value = new_channel
        new_channel.basic_publish.return_value = True
        
        message = {"key": "value"}
        result = client.publish(
            message=message,
            routing_key="test.routing.key"
        )
        
        # Verify a new channel was created
        assert client.connection.channel.call_count == 2  # Initial + retry
        
        # Verify message was published successfully on retry
        assert result is True


# ===== RabbitMQClient Message Consumption Tests =====

class TestRabbitMQClientConsumption:
    """Tests for RabbitMQClient message consumption."""

    def test_consume_success(self, mock_pika_blocking_connection):
        """Test successful message consumption."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Mock callback function
        callback = MagicMock()
        
        client.consume(
            queue_name="test-queue",
            callback=callback,
            auto_ack=False,
            exclusive=False
        )
        
        # Verify basic_consume was called
        client.channel.basic_consume.assert_called_once_with(
            queue="test-queue",
            on_message_callback=callback,
            auto_ack=False,
            exclusive=False
        )
        
        # Verify start_consuming was called
        client.channel.start_consuming.assert_called_once()

    def test_consume_with_connection_error(self, mock_pika_blocking_connection):
        """Test consumption with a connection error."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure start_consuming to raise a connection error
        client.channel.start_consuming.side_effect = ConnectionClosedByBroker(0, "Connection closed")
        
        # Mock callback function
        callback = MagicMock()
        
        with pytest.raises(RabbitMQConnectionError) as excinfo:
            client.consume(
                queue_name="test-queue",
                callback=callback
            )
        
        assert "Connection error while consuming messages" in str(excinfo.value)
        
        # Verify close was called
        client.connection.close.assert_called_once()

    def test_consume_with_channel_error(self, mock_pika_blocking_connection):
        """Test consumption with a channel error."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure start_consuming to raise a channel error
        client.channel.start_consuming.side_effect = ChannelClosedByBroker(0, "Channel closed")
        
        # Mock callback function
        callback = MagicMock()
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.consume(
                queue_name="test-queue",
                callback=callback
            )
        
        assert "Channel error while consuming messages" in str(excinfo.value)

    def test_consume_with_keyboard_interrupt(self, mock_pika_blocking_connection):
        """Test consumption with a keyboard interrupt."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure start_consuming to raise a keyboard interrupt
        client.channel.start_consuming.side_effect = KeyboardInterrupt()
        
        # Mock callback function
        callback = MagicMock()
        
        # Should not raise an exception
        client.consume(
            queue_name="test-queue",
            callback=callback
        )
        
        # Verify stop_consuming and close were called
        client.channel.stop_consuming.assert_called_once()
        client.connection.close.assert_called_once()

    def test_consume_with_retry(self, mock_pika_blocking_connection):
        """Test consumption with retry on connection error."""
        client = RabbitMQClient(host="localhost")
        
        # Mock consume method to fail once, then succeed
        with patch.object(client, "consume") as mock_consume, \
             patch("time.sleep") as mock_sleep:
            
            mock_consume.side_effect = [
                RabbitMQConnectionError("Connection error"),
                None  # Success
            ]
            
            # Mock callback function
            callback = MagicMock()
            
            client.consume_with_retry(
                queue_name="test-queue",
                callback=callback,
                max_retries=3
            )
            
            # Verify consume was called twice
            assert mock_consume.call_count == 2
            
            # Verify sleep was called once
            mock_sleep.assert_called_once()

    def test_consume_with_max_retries_exceeded(self, mock_pika_blocking_connection):
        """Test consumption with max retries exceeded."""
        client = RabbitMQClient(host="localhost")
        
        # Mock consume method to always fail
        with patch.object(client, "consume") as mock_consume, \
             patch("time.sleep") as mock_sleep, \
             patch.object(client, "connect") as mock_connect:
            
            mock_consume.side_effect = RabbitMQConnectionError("Connection error")
            
            # Mock callback function
            callback = MagicMock()
            
            with pytest.raises(RabbitMQConnectionError) as excinfo:
                client.consume_with_retry(
                    queue_name="test-queue",
                    callback=callback,
                    max_retries=2
                )
            
            # Verify consume was called 3 times (initial + 2 retries)
            assert mock_consume.call_count == 3
            
            # Verify sleep was called twice
            assert mock_sleep.call_count == 2
            
            # Verify connect was called for each retry
            assert mock_connect.call_count == 2

    def test_get_message_success(self, mock_pika_blocking_connection):
        """Test successful message retrieval."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_get to return a message
        method_frame = MagicMock()
        header_frame = MagicMock()
        body = b'{"key": "value"}'
        client.channel.basic_get.return_value = (method_frame, header_frame, body)
        
        result = client.get_message(queue_name="test-queue")
        
        # Verify basic_get was called
        client.channel.basic_get.assert_called_once_with(
            queue="test-queue",
            auto_ack=False
        )
        
        # Verify result
        assert result == (method_frame, header_frame, body)

    def test_get_message_empty_queue(self, mock_pika_blocking_connection):
        """Test message retrieval from an empty queue."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_get to return None (empty queue)
        client.channel.basic_get.return_value = (None, None, None)
        
        result = client.get_message(queue_name="test-queue")
        
        # Verify result is None
        assert result is None

    def test_get_message_with_connection_error(self, mock_pika_blocking_connection):
        """Test message retrieval with a connection error."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_get to raise a connection error
        client.channel.basic_get.side_effect = ConnectionClosedByBroker(0, "Connection closed")
        
        with pytest.raises(RabbitMQConnectionError) as excinfo:
            client.get_message(queue_name="test-queue")
        
        assert "Connection error while getting message" in str(excinfo.value)
        
        # Verify close and connect were called
        client.connection.close.assert_called_once()


# ===== RabbitMQClient Message Acknowledgment Tests =====

class TestRabbitMQClientAcknowledgment:
    """Tests for RabbitMQClient message acknowledgment."""

    def test_acknowledge_success(self, mock_pika_blocking_connection):
        """Test successful message acknowledgment."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        client.acknowledge(delivery_tag=123)
        
        # Verify basic_ack was called
        client.channel.basic_ack.assert_called_once_with(delivery_tag=123)

    def test_acknowledge_with_closed_channel(self):
        """Test acknowledgment with a closed channel."""
        client = RabbitMQClient(host="localhost")
        # Don't connect, so channel is None
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.acknowledge(delivery_tag=123)
        
        assert "Channel is not open" in str(excinfo.value)

    def test_acknowledge_with_channel_error(self, mock_pika_blocking_connection):
        """Test acknowledgment with a channel error."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_ack to raise a channel error
        client.channel.basic_ack.side_effect = AMQPChannelError("Channel error")
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.acknowledge(delivery_tag=123)
        
        assert "Failed to acknowledge message" in str(excinfo.value)

    def test_reject_success(self, mock_pika_blocking_connection):
        """Test successful message rejection."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        client.reject(delivery_tag=123, requeue=True)
        
        # Verify basic_reject was called
        client.channel.basic_reject.assert_called_once_with(delivery_tag=123, requeue=True)

    def test_reject_with_closed_channel(self):
        """Test rejection with a closed channel."""
        client = RabbitMQClient(host="localhost")
        # Don't connect, so channel is None
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.reject(delivery_tag=123)
        
        assert "Channel is not open" in str(excinfo.value)

    def test_reject_with_channel_error(self, mock_pika_blocking_connection):
        """Test rejection with a channel error."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Configure basic_reject to raise a channel error
        client.channel.basic_reject.side_effect = AMQPChannelError("Channel error")
        
        with pytest.raises(RabbitMQChannelError) as excinfo:
            client.reject(delivery_tag=123)
        
        assert "Failed to reject message" in str(excinfo.value)


# ===== Utility Function Tests =====

class TestRabbitMQUtilityFunctions:
    """Tests for RabbitMQ utility functions."""

    def test_serialize_message(self):
        """Test message serialization."""
        message = {"key": "value", "nested": {"data": [1, 2, 3]}}
        result = serialize_message(message)
        
        # Verify result is bytes
        assert isinstance(result, bytes)
        
        # Verify content
        expected = json.dumps(message).encode('utf-8')
        assert result == expected

    def test_deserialize_message(self):
        """Test message deserialization."""
        message = {"key": "value", "nested": {"data": [1, 2, 3]}}
        message_bytes = json.dumps(message).encode('utf-8')
        
        result = deserialize_message(message_bytes)
        
        # Verify result is dict
        assert isinstance(result, dict)
        
        # Verify content
        assert result == message

    def test_create_rabbitmq_client_from_env(self):
        """Test creating a RabbitMQ client from environment variables."""
        with patch.dict(os.environ, {
            "RABBITMQ_HOST": "rabbitmq.example.com",
            "RABBITMQ_PORT": "5673",
            "RABBITMQ_VHOST": "/test",
            "RABBITMQ_USERNAME": "test_user",
            "RABBITMQ_PASSWORD": "test_password",
            "RABBITMQ_EXCHANGE": "test.exchange",
            "RABBITMQ_PREFETCH_COUNT": "20"
        }):
            client = create_rabbitmq_client_from_env()
            
            # Verify client configuration
            assert client.host == "rabbitmq.example.com"
            assert client.port == 5673
            assert client.virtual_host == "/test"
            assert client.username == "test_user"
            assert client.password == "test_password"
            assert client.exchange == "test.exchange"
            assert client.prefetch_count == 20

    def test_create_rabbitmq_client_from_env_with_defaults(self):
        """Test creating a RabbitMQ client with default environment variables."""
        # Clear relevant environment variables
        with patch.dict(os.environ, {}, clear=True):
            client = create_rabbitmq_client_from_env()
            
            # Verify default configuration
            assert client.host == "localhost"
            assert client.port == 5672
            assert client.virtual_host == "/"
            assert client.username == "guest"
            assert client.password == "guest"
            assert client.exchange == DEFAULT_EXCHANGE
            assert client.prefetch_count == 10

    def test_setup_ocr_queues(self, mock_pika_blocking_connection):
        """Test setting up OCR queues."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Mock client methods
        with patch.object(client, "declare_queue") as mock_declare_queue, \
             patch.object(client, "bind_queue") as mock_bind_queue:
            
            setup_ocr_queues(client)
            
            # Verify queues were declared
            assert mock_declare_queue.call_count == 2
            mock_declare_queue.assert_has_calls([
                call(
                    queue_name=DEFAULT_OCR_REQUEST_QUEUE,
                    durable=True,
                    exclusive=False,
                    auto_delete=False
                ),
                call(
                    queue_name=DEFAULT_PROCESSING_QUEUE,
                    durable=True,
                    exclusive=False,
                    auto_delete=False
                )
            ])
            
            # Verify queues were bound
            assert mock_bind_queue.call_count == 2
            mock_bind_queue.assert_has_calls([
                call(
                    queue_name=DEFAULT_OCR_REQUEST_QUEUE,
                    routing_key="document.ocr.request"
                ),
                call(
                    queue_name=DEFAULT_PROCESSING_QUEUE,
                    routing_key="document.ocr.result"
                )
            ])

    def test_create_ocr_result_message(self):
        """Test creating an OCR result message."""
        document_id = "doc-123456"
        extracted_data = {"field1": "value1", "field2": "value2"}
        confidence_scores = {"field1": 0.95, "field2": 0.87}
        processing_time_ms = 1500
        
        result = create_ocr_result_message(
            document_id=document_id,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores,
            processing_time_ms=processing_time_ms
        )
        
        # Verify message structure
        assert result["document_id"] == document_id
        assert result["extracted_data"] == extracted_data
        assert result["confidence_scores"] == confidence_scores
        assert result["processing_time_ms"] == processing_time_ms
        assert result["service"] == "ocr-service"
        assert result["status"] == "completed"
        assert "timestamp" in result

    def test_publish_ocr_result(self, mock_pika_blocking_connection):
        """Test publishing an OCR result."""
        client = RabbitMQClient(host="localhost")
        client.connect()
        
        # Mock client.publish
        with patch.object(client, "publish", return_value=True) as mock_publish:
            document_id = "doc-123456"
            extracted_data = {"field1": "value1", "field2": "value2"}
            confidence_scores = {"field1": 0.95, "field2": 0.87}
            processing_time_ms = 1500
            
            result = publish_ocr_result(
                client=client,
                document_id=document_id,
                extracted_data=extracted_data,
                confidence_scores=confidence_scores,
                processing_time_ms=processing_time_ms
            )
            
            # Verify result
            assert result is True
            
            # Verify publish was called
            mock_publish.assert_called_once()
            
            # Verify message and routing key
            args, kwargs = mock_publish.call_args
            assert kwargs["routing_key"] == "document.ocr.result"
            
            # Verify message content
            message = kwargs["message"]
            assert message["document_id"] == document_id
            assert message["extracted_data"] == extracted_data
            assert message["confidence_scores"] == confidence_scores
            assert message["processing_time_ms"] == processing_time_ms
            
            # Verify properties
            properties = kwargs["properties"]
            assert properties.content_type == "application/json"
            assert properties.delivery_mode == 2  # Persistent
            assert properties.message_id.startswith(f"ocr-result-{document_id}")
            assert properties.headers["document_id"] == document_id
            assert properties.headers["service"] == "ocr-service"


# ===== Example Message Handler Tests =====

class TestExampleMessageHandler:
    """Tests for the example message handler function."""

    def test_example_message_handler_success(self, mock_rabbitmq_channel, mock_rabbitmq_message):
        """Test successful message handling."""
        from utils.rabbitmq_utils import example_message_handler
        
        method, properties, body = mock_rabbitmq_message
        
        # Call the handler
        example_message_handler(mock_rabbitmq_channel, method, properties, body)
        
        # Verify message was acknowledged
        mock_rabbitmq_channel.basic_ack.assert_called_once_with(
            delivery_tag=method.delivery_tag
        )

    def test_example_message_handler_error(self, mock_rabbitmq_channel, mock_rabbitmq_message):
        """Test message handling with an error."""
        from utils.rabbitmq_utils import example_message_handler
        
        method, properties, body = mock_rabbitmq_message
        
        # Make deserialize_message raise an exception
        with patch("utils.rabbitmq_utils.deserialize_message", 
                  side_effect=ValueError("Invalid JSON")):
            
            # Call the handler
            example_message_handler(mock_rabbitmq_channel, method, properties, body)
            
            # Verify message was rejected and requeued
            mock_rabbitmq_channel.basic_reject.assert_called_once_with(
                delivery_tag=method.delivery_tag,
                requeue=True
            )