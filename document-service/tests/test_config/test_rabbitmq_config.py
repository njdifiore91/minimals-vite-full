import os
import ssl
import json
import pytest
import time
from unittest.mock import patch, MagicMock, call
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters, SSLOptions
from pika.credentials import ExternalCredentials
from pika.exceptions import (
    AMQPConnectionError,
    ConnectionClosed,
    ConnectionClosedByBroker,
    ConnectionBlockedTimeout,
    ChannelClosed,
    ChannelClosedByBroker
)

# Import the module to test
from src.config import rabbitmq_config


# ===== Test SSL Context Creation =====

@patch('ssl.create_default_context')
@patch('ssl.SSLContext.load_verify_locations')
@patch('ssl.SSLContext.load_cert_chain')
@patch('ssl.SSLContext.set_ciphers')
def test_create_ssl_context(mock_set_ciphers, mock_load_cert_chain, 
                           mock_load_verify_locations, mock_create_default_context):
    """Test that create_ssl_context creates a properly configured SSL context."""
    # Setup mock context
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    
    # Call the function
    context = rabbitmq_config.create_ssl_context()
    
    # Verify the context was created correctly
    mock_create_default_context.assert_called_once_with(ssl.Purpose.SERVER_AUTH)
    assert mock_context.verify_mode == ssl.CERT_REQUIRED
    mock_load_verify_locations.assert_called_once_with(cafile=rabbitmq_config.CA_CERT_PATH)
    mock_load_cert_chain.assert_called_once_with(
        certfile=rabbitmq_config.CLIENT_CERT_PATH, 
        keyfile=rabbitmq_config.CLIENT_KEY_PATH
    )
    assert mock_context.minimum_version == ssl.TLSVersion.TLSv1_2
    mock_set_ciphers.assert_called_once_with('HIGH:!aNULL:!MD5:!RC4')
    
    # Verify the context is returned
    assert context == mock_context


@patch('ssl.create_default_context')
def test_create_ssl_context_file_not_found(mock_create_default_context):
    """Test that create_ssl_context handles FileNotFoundError correctly."""
    # Setup mock to raise FileNotFoundError
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_context.load_verify_locations.side_effect = FileNotFoundError("Certificate file not found")
    
    # Call the function and check that it raises the exception
    with pytest.raises(FileNotFoundError) as excinfo:
        rabbitmq_config.create_ssl_context()
    
    # Verify the exception message
    assert "Certificate file not found" in str(excinfo.value)


@patch('ssl.create_default_context')
def test_create_ssl_context_ssl_error(mock_create_default_context):
    """Test that create_ssl_context handles SSLError correctly."""
    # Setup mock to raise SSLError
    mock_context = MagicMock()
    mock_create_default_context.return_value = mock_context
    mock_context.load_cert_chain.side_effect = ssl.SSLError("Invalid certificate")
    
    # Call the function and check that it raises the exception
    with pytest.raises(ssl.SSLError) as excinfo:
        rabbitmq_config.create_ssl_context()
    
    # Verify the exception message
    assert "Invalid certificate" in str(excinfo.value)


# ===== Test Connection Parameters =====

@patch('src.config.rabbitmq_config.create_ssl_context')
def test_get_connection_parameters(mock_create_ssl_context):
    """Test that get_connection_parameters returns correctly configured parameters."""
    # Setup mock SSL context
    mock_context = MagicMock()
    mock_create_ssl_context.return_value = mock_context
    
    # Call the function
    params = rabbitmq_config.get_connection_parameters()
    
    # Verify the parameters
    assert isinstance(params, ConnectionParameters)
    assert params.host == rabbitmq_config.RABBITMQ_HOST
    assert params.port == rabbitmq_config.RABBITMQ_PORT
    assert params.virtual_host == rabbitmq_config.RABBITMQ_VHOST
    assert isinstance(params.credentials, ExternalCredentials)
    assert isinstance(params.ssl_options, SSLOptions)
    assert params.heartbeat == rabbitmq_config.RABBITMQ_HEARTBEAT
    assert params.blocked_connection_timeout == rabbitmq_config.RABBITMQ_BLOCKED_CONNECTION_TIMEOUT
    assert params.connection_attempts == 3
    assert params.retry_delay == 1.0
    assert params.socket_timeout == rabbitmq_config.RABBITMQ_CONNECTION_TIMEOUT


# ===== Test Connection Creation =====

@patch('src.config.rabbitmq_config.get_connection_parameters')
@patch('pika.adapters.blocking_connection.BlockingConnection')
def test_create_rabbitmq_connection(mock_blocking_connection, mock_get_connection_parameters):
    """Test that create_rabbitmq_connection creates a connection correctly."""
    # Setup mocks
    mock_params = MagicMock()
    mock_get_connection_parameters.return_value = mock_params
    mock_connection = MagicMock()
    mock_blocking_connection.return_value = mock_connection
    
    # Call the function
    connection = rabbitmq_config.create_rabbitmq_connection()
    
    # Verify the connection was created correctly
    mock_get_connection_parameters.assert_called_once()
    mock_blocking_connection.assert_called_once_with(mock_params)
    assert connection == mock_connection


@patch('src.config.rabbitmq_config.get_connection_parameters')
@patch('pika.adapters.blocking_connection.BlockingConnection')
@patch('time.sleep')
def test_create_rabbitmq_connection_with_retry(mock_sleep, mock_blocking_connection, 
                                              mock_get_connection_parameters):
    """Test that create_rabbitmq_connection retries on connection failure."""
    # Setup mocks
    mock_params = MagicMock()
    mock_get_connection_parameters.return_value = mock_params
    mock_connection = MagicMock()
    
    # Make the first attempt fail, then succeed
    mock_blocking_connection.side_effect = [
        AMQPConnectionError("Connection refused"),
        mock_connection
    ]
    
    # Call the function
    connection = rabbitmq_config.create_rabbitmq_connection()
    
    # Verify the connection was created correctly after retry
    assert mock_get_connection_parameters.call_count == 2
    assert mock_blocking_connection.call_count == 2
    mock_sleep.assert_called_once_with(rabbitmq_config.INITIAL_RETRY_DELAY)
    assert connection == mock_connection


@patch('src.config.rabbitmq_config.get_connection_parameters')
@patch('pika.adapters.blocking_connection.BlockingConnection')
@patch('time.sleep')
def test_create_rabbitmq_connection_max_retries(mock_sleep, mock_blocking_connection, 
                                               mock_get_connection_parameters):
    """Test that create_rabbitmq_connection raises exception after max retries."""
    # Setup mocks
    mock_params = MagicMock()
    mock_get_connection_parameters.return_value = mock_params
    
    # Make all connection attempts fail
    error = AMQPConnectionError("Connection refused")
    mock_blocking_connection.side_effect = [error] * (rabbitmq_config.MAX_RETRIES + 1)
    
    # Call the function and check that it raises the exception
    with pytest.raises(AMQPConnectionError) as excinfo:
        rabbitmq_config.create_rabbitmq_connection()
    
    # Verify the retry behavior
    assert mock_get_connection_parameters.call_count == rabbitmq_config.MAX_RETRIES + 1
    assert mock_blocking_connection.call_count == rabbitmq_config.MAX_RETRIES + 1
    assert mock_sleep.call_count == rabbitmq_config.MAX_RETRIES
    
    # Verify the exception message
    assert "Connection refused" in str(excinfo.value)


# ===== Test Channel Setup =====

def test_setup_rabbitmq_channel():
    """Test that setup_rabbitmq_channel configures the channel correctly."""
    # Setup mock connection and channel
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_connection.channel.return_value = mock_channel
    
    # Call the function
    channel = rabbitmq_config.setup_rabbitmq_channel(mock_connection)
    
    # Verify the channel was set up correctly
    mock_connection.channel.assert_called_once()
    mock_channel.basic_qos.assert_called_once_with(prefetch_count=rabbitmq_config.PREFETCH_COUNT)
    
    # Verify dead letter exchange setup
    mock_channel.exchange_declare.assert_any_call(
        exchange=rabbitmq_config.DEAD_LETTER_EXCHANGE,
        exchange_type='direct',
        durable=True
    )
    
    # Verify dead letter queue setup
    mock_channel.queue_declare.assert_any_call(
        queue=rabbitmq_config.DEAD_LETTER_QUEUE,
        durable=True
    )
    
    # Verify dead letter binding
    mock_channel.queue_bind.assert_any_call(
        queue=rabbitmq_config.DEAD_LETTER_QUEUE,
        exchange=rabbitmq_config.DEAD_LETTER_EXCHANGE,
        routing_key=rabbitmq_config.QUEUE_NAME
    )
    
    # Verify main exchange setup
    mock_channel.exchange_declare.assert_any_call(
        exchange=rabbitmq_config.EXCHANGE_NAME,
        exchange_type=rabbitmq_config.EXCHANGE_TYPE,
        durable=True
    )
    
    # Verify main queue setup with dead letter configuration
    mock_channel.queue_declare.assert_any_call(
        queue=rabbitmq_config.QUEUE_NAME,
        durable=True,
        arguments={
            'x-dead-letter-exchange': rabbitmq_config.DEAD_LETTER_EXCHANGE,
            'x-dead-letter-routing-key': rabbitmq_config.QUEUE_NAME,
            'x-message-ttl': 1000 * 60 * 60 * 24  # 24 hours in milliseconds
        }
    )
    
    # Verify main binding
    mock_channel.queue_bind.assert_any_call(
        queue=rabbitmq_config.QUEUE_NAME,
        exchange=rabbitmq_config.EXCHANGE_NAME
    )
    
    # Verify the channel is returned
    assert channel == mock_channel


def test_setup_rabbitmq_channel_error():
    """Test that setup_rabbitmq_channel handles channel errors correctly."""
    # Setup mock connection and channel
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_connection.channel.return_value = mock_channel
    
    # Make the channel setup fail
    mock_channel.exchange_declare.side_effect = ChannelClosed("Channel closed")
    
    # Call the function and check that it raises the exception
    with pytest.raises(ChannelClosed) as excinfo:
        rabbitmq_config.setup_rabbitmq_channel(mock_connection)
    
    # Verify the exception message
    assert "Channel closed" in str(excinfo.value)


# ===== Test Message Serialization =====

def test_serialize_message():
    """Test that serialize_message correctly converts a dictionary to JSON bytes."""
    # Test message
    message = {
        "document_id": "test-123",
        "metadata": {
            "filename": "test.pdf",
            "size": 1024,
            "content_type": "application/pdf"
        },
        "status": "received"
    }
    
    # Call the function
    serialized = rabbitmq_config.serialize_message(message)
    
    # Verify the result is bytes
    assert isinstance(serialized, bytes)
    
    # Verify the content is correct by deserializing
    deserialized = json.loads(serialized.decode('utf-8'))
    assert deserialized == message


def test_serialize_message_with_unicode():
    """Test that serialize_message handles Unicode characters correctly."""
    # Test message with Unicode
    message = {
        "document_id": "test-123",
        "metadata": {
            "filename": "test_üñíçødé.pdf",
            "size": 1024,
            "content_type": "application/pdf"
        },
        "status": "received"
    }
    
    # Call the function
    serialized = rabbitmq_config.serialize_message(message)
    
    # Verify the result is bytes
    assert isinstance(serialized, bytes)
    
    # Verify the content is correct by deserializing
    deserialized = json.loads(serialized.decode('utf-8'))
    assert deserialized == message
    assert deserialized["metadata"]["filename"] == "test_üñíçødé.pdf"


def test_serialize_message_error():
    """Test that serialize_message handles serialization errors correctly."""
    # Create a message that can't be serialized (contains a function)
    message = {
        "document_id": "test-123",
        "callback": lambda x: x  # Functions can't be serialized to JSON
    }
    
    # Call the function and check that it raises the exception
    with pytest.raises(TypeError) as excinfo:
        rabbitmq_config.serialize_message(message)
    
    # Verify the exception message indicates a serialization error
    assert "not JSON serializable" in str(excinfo.value)


def test_deserialize_message():
    """Test that deserialize_message correctly converts JSON bytes to a dictionary."""
    # Test message
    message = {
        "document_id": "test-123",
        "metadata": {
            "filename": "test.pdf",
            "size": 1024,
            "content_type": "application/pdf"
        },
        "status": "received"
    }
    
    # Serialize the message
    serialized = json.dumps(message).encode('utf-8')
    
    # Call the function
    deserialized = rabbitmq_config.deserialize_message(serialized)
    
    # Verify the result is a dictionary
    assert isinstance(deserialized, dict)
    
    # Verify the content is correct
    assert deserialized == message


def test_deserialize_message_with_unicode():
    """Test that deserialize_message handles Unicode characters correctly."""
    # Test message with Unicode
    message = {
        "document_id": "test-123",
        "metadata": {
            "filename": "test_üñíçødé.pdf",
            "size": 1024,
            "content_type": "application/pdf"
        },
        "status": "received"
    }
    
    # Serialize the message
    serialized = json.dumps(message).encode('utf-8')
    
    # Call the function
    deserialized = rabbitmq_config.deserialize_message(serialized)
    
    # Verify the result is a dictionary
    assert isinstance(deserialized, dict)
    
    # Verify the content is correct
    assert deserialized == message
    assert deserialized["metadata"]["filename"] == "test_üñíçødé.pdf"


def test_deserialize_message_invalid_json():
    """Test that deserialize_message handles invalid JSON correctly."""
    # Create invalid JSON
    invalid_json = b'{"document_id": "test-123", invalid}'  # Missing quotes around 'invalid'
    
    # Call the function and check that it raises the exception
    with pytest.raises(ValueError) as excinfo:
        rabbitmq_config.deserialize_message(invalid_json)
    
    # Verify the exception message indicates a deserialization error
    assert "Invalid message format" in str(excinfo.value)


def test_deserialize_message_invalid_encoding():
    """Test that deserialize_message handles invalid encoding correctly."""
    # Create bytes with invalid UTF-8 encoding
    invalid_bytes = b'\x80\x81\x82'  # Invalid UTF-8 bytes
    
    # Call the function and check that it raises the exception
    with pytest.raises(ValueError) as excinfo:
        rabbitmq_config.deserialize_message(invalid_bytes)
    
    # Verify the exception message indicates a deserialization error
    assert "Invalid message format" in str(excinfo.value)


# ===== Test Message Publishing =====

def test_publish_message():
    """Test that publish_message correctly publishes a message to RabbitMQ."""
    # Setup mock channel
    mock_channel = MagicMock()
    
    # Test message
    message = {
        "document_id": "test-123",
        "metadata": {
            "filename": "test.pdf",
            "size": 1024,
            "content_type": "application/pdf"
        },
        "status": "received"
    }
    
    # Call the function
    rabbitmq_config.publish_message(mock_channel, message)
    
    # Verify the message was published correctly
    mock_channel.basic_publish.assert_called_once()
    call_args = mock_channel.basic_publish.call_args[1]
    
    # Verify exchange and routing key
    assert call_args["exchange"] == rabbitmq_config.EXCHANGE_NAME
    assert call_args["routing_key"] == ''  # Default for fanout exchange
    
    # Verify the body is serialized correctly
    body = call_args["body"]
    assert isinstance(body, bytes)
    deserialized = json.loads(body.decode('utf-8'))
    assert deserialized == message
    
    # Verify the properties
    properties = call_args["properties"]
    assert properties.content_type == rabbitmq_config.CONTENT_TYPE
    assert properties.delivery_mode == rabbitmq_config.DELIVERY_MODE
    assert properties.app_id == 'document-service'


def test_publish_message_with_routing_key():
    """Test that publish_message uses the provided routing key."""
    # Setup mock channel
    mock_channel = MagicMock()
    
    # Test message
    message = {"test": "message"}
    routing_key = "test.routing.key"
    
    # Call the function
    rabbitmq_config.publish_message(mock_channel, message, routing_key)
    
    # Verify the routing key was used
    mock_channel.basic_publish.assert_called_once()
    assert mock_channel.basic_publish.call_args[1]["routing_key"] == routing_key


def test_publish_message_connection_closed():
    """Test that publish_message handles connection closed errors correctly."""
    # Setup mock channel
    mock_channel = MagicMock()
    mock_channel.basic_publish.side_effect = ConnectionClosed("Connection closed")
    
    # Test message
    message = {"test": "message"}
    
    # Call the function and check that it raises the exception
    with pytest.raises(ConnectionClosed) as excinfo:
        rabbitmq_config.publish_message(mock_channel, message)
    
    # Verify the exception message
    assert "Connection closed" in str(excinfo.value)


# ===== Test RabbitMQ Client =====

def test_rabbitmq_client_init():
    """Test that RabbitMQClient initializes correctly."""
    # Create a client
    client = rabbitmq_config.RabbitMQClient()
    
    # Verify the initial state
    assert client.connection is None
    assert client.channel is None


@patch('src.config.rabbitmq_config.create_rabbitmq_connection')
@patch('src.config.rabbitmq_config.setup_rabbitmq_channel')
def test_rabbitmq_client_connect(mock_setup_channel, mock_create_connection):
    """Test that RabbitMQClient.connect establishes a connection and channel."""
    # Setup mocks
    mock_connection = MagicMock()
    mock_channel = MagicMock()
    mock_create_connection.return_value = mock_connection
    mock_setup_channel.return_value = mock_channel
    
    # Create a client and connect
    client = rabbitmq_config.RabbitMQClient()
    client.connect()
    
    # Verify the connection was established
    mock_create_connection.assert_called_once()
    mock_setup_channel.assert_called_once_with(mock_connection)
    assert client.connection == mock_connection
    assert client.channel == mock_channel


@patch('src.config.rabbitmq_config.create_rabbitmq_connection')
@patch('src.config.rabbitmq_config.setup_rabbitmq_channel')
def test_rabbitmq_client_connect_already_connected(mock_setup_channel, mock_create_connection):
    """Test that RabbitMQClient.connect doesn't reconnect if already connected."""
    # Setup mocks
    mock_connection = MagicMock()
    mock_connection.is_closed = False
    mock_channel = MagicMock()
    
    # Create a client with an existing connection
    client = rabbitmq_config.RabbitMQClient()
    client.connection = mock_connection
    client.channel = mock_channel
    
    # Connect again
    client.connect()
    
    # Verify no new connection was created
    mock_create_connection.assert_not_called()
    mock_setup_channel.assert_not_called()
    assert client.connection == mock_connection
    assert client.channel == mock_channel


@patch('src.config.rabbitmq_config.create_rabbitmq_connection')
@patch('src.config.rabbitmq_config.setup_rabbitmq_channel')
def test_rabbitmq_client_connect_closed_connection(mock_setup_channel, mock_create_connection):
    """Test that RabbitMQClient.connect reconnects if the connection is closed."""
    # Setup mocks
    old_connection = MagicMock()
    old_connection.is_closed = True
    old_channel = MagicMock()
    
    new_connection = MagicMock()
    new_connection.is_closed = False
    new_channel = MagicMock()
    
    mock_create_connection.return_value = new_connection
    mock_setup_channel.return_value = new_channel
    
    # Create a client with a closed connection
    client = rabbitmq_config.RabbitMQClient()
    client.connection = old_connection
    client.channel = old_channel
    
    # Connect again
    client.connect()
    
    # Verify a new connection was created
    mock_create_connection.assert_called_once()
    mock_setup_channel.assert_called_once_with(new_connection)
    assert client.connection == new_connection
    assert client.channel == new_channel


def test_rabbitmq_client_close():
    """Test that RabbitMQClient.close closes the connection and channel correctly."""
    # Setup mock connection and channel
    mock_connection = MagicMock()
    mock_connection.is_open = True
    mock_channel = MagicMock()
    mock_channel.is_open = True
    
    # Create a client with an open connection
    client = rabbitmq_config.RabbitMQClient()
    client.connection = mock_connection
    client.channel = mock_channel
    
    # Close the connection
    client.close()
    
    # Verify the channel and connection were closed
    mock_channel.close.assert_called_once()
    mock_connection.close.assert_called_once()


def test_rabbitmq_client_close_no_connection():
    """Test that RabbitMQClient.close handles the case when there is no connection."""
    # Create a client with no connection
    client = rabbitmq_config.RabbitMQClient()
    client.connection = None
    client.channel = None
    
    # Close the connection (should not raise an exception)
    client.close()


def test_rabbitmq_client_close_closed_connection():
    """Test that RabbitMQClient.close handles the case when the connection is already closed."""
    # Setup mock connection that is already closed
    mock_connection = MagicMock()
    mock_connection.is_open = False
    
    # Create a client with a closed connection
    client = rabbitmq_config.RabbitMQClient()
    client.connection = mock_connection
    client.channel = None
    
    # Close the connection (should not try to close it again)
    client.close()
    
    # Verify the connection was not closed again
    mock_connection.close.assert_not_called()


def test_rabbitmq_client_close_error():
    """Test that RabbitMQClient.close handles errors during closing."""
    # Setup mock connection that raises an exception when closed
    mock_connection = MagicMock()
    mock_connection.is_open = True
    mock_connection.close.side_effect = Exception("Error closing connection")
    
    mock_channel = MagicMock()
    mock_channel.is_open = True
    mock_channel.close.side_effect = Exception("Error closing channel")
    
    # Create a client with a problematic connection
    client = rabbitmq_config.RabbitMQClient()
    client.connection = mock_connection
    client.channel = mock_channel
    
    # Close the connection (should not raise an exception)
    client.close()
    
    # Verify close was attempted
    mock_channel.close.assert_called_once()
    mock_connection.close.assert_called_once()


@patch.object(rabbitmq_config.RabbitMQClient, 'connect')
@patch('src.config.rabbitmq_config.publish_message')
def test_rabbitmq_client_publish(mock_publish_message, mock_connect):
    """Test that RabbitMQClient.publish correctly publishes a message."""
    # Setup mocks
    mock_channel = MagicMock()
    
    # Create a client with a channel
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Test message
    message = {"test": "message"}
    routing_key = "test.routing.key"
    
    # Publish a message
    client.publish(message, routing_key)
    
    # Verify the connection was established and the message was published
    mock_connect.assert_called_once()
    mock_publish_message.assert_called_once_with(mock_channel, message, routing_key)


@patch.object(rabbitmq_config.RabbitMQClient, 'connect')
@patch('src.config.rabbitmq_config.publish_message')
def test_rabbitmq_client_publish_connection_error(mock_publish_message, mock_connect):
    """Test that RabbitMQClient.publish handles connection errors correctly."""
    # Setup mocks
    mock_channel = MagicMock()
    
    # Make the first publish attempt fail, then succeed
    mock_publish_message.side_effect = [
        ConnectionClosed("Connection closed"),
        None  # Success
    ]
    
    # Create a client with a channel
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Test message
    message = {"test": "message"}
    
    # Publish a message
    client.publish(message)
    
    # Verify the connection was established twice and the message was published twice
    assert mock_connect.call_count == 2
    assert mock_publish_message.call_count == 2
    assert client.connection is None  # Connection should be reset for reconnection


@patch.object(rabbitmq_config.RabbitMQClient, 'connect')
def test_rabbitmq_client_consume(mock_connect):
    """Test that RabbitMQClient.consume correctly sets up message consumption."""
    # Setup mock channel
    mock_channel = MagicMock()
    
    # Create a client with a channel
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Test callback
    def test_callback(message, method, properties):
        pass
    
    # Start consuming
    client.consume(test_callback)
    
    # Verify the connection was established and consumption was set up
    mock_connect.assert_called_once()
    mock_channel.basic_consume.assert_called_once()
    mock_channel.start_consuming.assert_called_once()
    
    # Verify the queue name
    assert mock_channel.basic_consume.call_args[1]["queue"] == rabbitmq_config.QUEUE_NAME


@patch.object(rabbitmq_config.RabbitMQClient, 'connect')
@patch.object(rabbitmq_config.RabbitMQClient, 'close')
def test_rabbitmq_client_consume_keyboard_interrupt(mock_close, mock_connect):
    """Test that RabbitMQClient.consume handles keyboard interrupts correctly."""
    # Setup mock channel
    mock_channel = MagicMock()
    mock_channel.start_consuming.side_effect = KeyboardInterrupt()
    
    # Create a client with a channel
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Test callback
    def test_callback(message, method, properties):
        pass
    
    # Start consuming (should handle the KeyboardInterrupt)
    client.consume(test_callback)
    
    # Verify the connection was established and consumption was set up
    mock_connect.assert_called_once()
    mock_channel.basic_consume.assert_called_once()
    mock_channel.start_consuming.assert_called_once()
    mock_channel.stop_consuming.assert_called_once()
    mock_close.assert_called_once()


@patch.object(rabbitmq_config.RabbitMQClient, 'connect')
def test_rabbitmq_client_consume_connection_closed(mock_connect):
    """Test that RabbitMQClient.consume handles connection closed errors correctly."""
    # Setup mock channel
    mock_channel = MagicMock()
    mock_channel.start_consuming.side_effect = ConnectionClosed("Connection closed")
    
    # Create a client with a channel
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Test callback
    def test_callback(message, method, properties):
        pass
    
    # Start consuming (should raise the ConnectionClosed exception)
    with pytest.raises(ConnectionClosed) as excinfo:
        client.consume(test_callback)
    
    # Verify the exception message
    assert "Connection closed" in str(excinfo.value)
    
    # Verify the connection was established and consumption was set up
    mock_connect.assert_called_once()
    mock_channel.basic_consume.assert_called_once()
    mock_channel.start_consuming.assert_called_once()


# ===== Test Callback Wrapper =====

def test_consume_callback_wrapper():
    """Test that the callback wrapper in consume correctly processes messages."""
    # Setup mock channel, method, and properties
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "test-tag"
    mock_properties = MagicMock()
    
    # Test message
    message_dict = {"test": "message"}
    message_body = json.dumps(message_dict).encode('utf-8')
    
    # Test callback that records the received message
    received_messages = []
    def test_callback(message, method, properties):
        received_messages.append((message, method, properties))
    
    # Create a client and get the wrapped callback
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Extract the wrapped callback from the consume method
    with patch.object(client.channel, 'basic_consume') as mock_basic_consume:
        client.consume(test_callback)
        wrapped_callback = mock_basic_consume.call_args[1]['on_message_callback']
    
    # Call the wrapped callback
    wrapped_callback(mock_channel, mock_method, mock_properties, message_body)
    
    # Verify the original callback was called with the correct arguments
    assert len(received_messages) == 1
    received_message, received_method, received_properties = received_messages[0]
    assert received_message == message_dict
    assert received_method == mock_method
    assert received_properties == mock_properties
    
    # Verify the message was acknowledged
    mock_channel.basic_ack.assert_called_once_with(delivery_tag=mock_method.delivery_tag)


def test_consume_callback_wrapper_deserialization_error():
    """Test that the callback wrapper handles deserialization errors correctly."""
    # Setup mock channel, method, and properties
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "test-tag"
    mock_properties = MagicMock()
    
    # Invalid message body
    invalid_body = b'{"test": invalid}'  # Missing quotes around 'invalid'
    
    # Test callback that should not be called
    def test_callback(message, method, properties):
        pytest.fail("Callback should not be called with invalid message")
    
    # Create a client and get the wrapped callback
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Extract the wrapped callback from the consume method
    with patch.object(client.channel, 'basic_consume') as mock_basic_consume:
        client.consume(test_callback)
        wrapped_callback = mock_basic_consume.call_args[1]['on_message_callback']
    
    # Call the wrapped callback with invalid message
    wrapped_callback(mock_channel, mock_method, mock_properties, invalid_body)
    
    # Verify the message was rejected without requeuing
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=False)


def test_consume_callback_wrapper_processing_error():
    """Test that the callback wrapper handles processing errors correctly."""
    # Setup mock channel, method, and properties
    mock_channel = MagicMock()
    mock_method = MagicMock()
    mock_method.delivery_tag = "test-tag"
    mock_properties = MagicMock()
    
    # Test message
    message_dict = {"test": "message"}
    message_body = json.dumps(message_dict).encode('utf-8')
    
    # Test callback that raises an exception
    def test_callback(message, method, properties):
        raise RuntimeError("Processing error")
    
    # Create a client and get the wrapped callback
    client = rabbitmq_config.RabbitMQClient()
    client.channel = mock_channel
    
    # Extract the wrapped callback from the consume method
    with patch.object(client.channel, 'basic_consume') as mock_basic_consume:
        client.consume(test_callback)
        wrapped_callback = mock_basic_consume.call_args[1]['on_message_callback']
    
    # Call the wrapped callback
    wrapped_callback(mock_channel, mock_method, mock_properties, message_body)
    
    # Verify the message was rejected with requeuing
    mock_channel.basic_nack.assert_called_once_with(delivery_tag=mock_method.delivery_tag, requeue=True)


# ===== Test Helper Functions =====

def test_get_rabbitmq_client():
    """Test that get_rabbitmq_client returns the singleton instance."""
    # Get the client
    client1 = rabbitmq_config.get_rabbitmq_client()
    client2 = rabbitmq_config.get_rabbitmq_client()
    
    # Verify it's the same instance
    assert client1 is client2
    assert isinstance(client1, rabbitmq_config.RabbitMQClient)


@patch.object(rabbitmq_config.RabbitMQClient, 'consume')
@patch('src.config.rabbitmq_config.get_rabbitmq_client')
@patch('time.sleep')
def test_consume_messages(mock_sleep, mock_get_client, mock_consume):
    """Test that consume_messages correctly sets up message consumption with retry logic."""
    # Setup mocks
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Make the first consume attempt fail, then succeed, then raise KeyboardInterrupt
    mock_consume.side_effect = [
        ConnectionClosed("Connection closed"),
        None,  # Success
        KeyboardInterrupt()
    ]
    
    # Test callback
    def test_callback(message, method, properties):
        pass
    
    # Start consuming
    rabbitmq_config.consume_messages(test_callback)
    
    # Verify the client was retrieved and consume was called multiple times
    assert mock_get_client.call_count == 3
    assert mock_consume.call_count == 3
    
    # Verify sleep was called after the connection error
    mock_sleep.assert_called_once_with(rabbitmq_config.INITIAL_RETRY_DELAY)


@patch.object(rabbitmq_config.RabbitMQClient, 'consume')
@patch('src.config.rabbitmq_config.get_rabbitmq_client')
@patch('time.sleep')
def test_consume_messages_unexpected_error(mock_sleep, mock_get_client, mock_consume):
    """Test that consume_messages handles unexpected errors correctly."""
    # Setup mocks
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    
    # Make consume raise an unexpected error
    mock_consume.side_effect = RuntimeError("Unexpected error")
    
    # Test callback
    def test_callback(message, method, properties):
        pass
    
    # Start consuming (should raise the unexpected error)
    with pytest.raises(RuntimeError) as excinfo:
        rabbitmq_config.consume_messages(test_callback)
    
    # Verify the exception message
    assert "Unexpected error" in str(excinfo.value)
    
    # Verify the client was retrieved and consume was called
    mock_get_client.assert_called_once()
    mock_consume.assert_called_once()
    
    # Verify sleep was not called
    mock_sleep.assert_not_called()


# ===== Test Module Initialization =====

def test_module_initialization():
    """Test that the module initializes the RabbitMQ client singleton correctly."""
    # Verify the singleton instance was created
    assert isinstance(rabbitmq_config.rabbitmq_client, rabbitmq_config.RabbitMQClient)
    
    # Verify the helper function returns the singleton
    client = rabbitmq_config.get_rabbitmq_client()
    assert client is rabbitmq_config.rabbitmq_client