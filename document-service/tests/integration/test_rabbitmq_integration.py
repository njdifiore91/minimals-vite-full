import json
import os
import pytest
import ssl
import threading
import time
from unittest import mock

import pika
from pika.credentials import ExternalCredentials
from pika.connection import ConnectionParameters
from pika.adapters.blocking_connection import BlockingConnection

# Import the Document Service RabbitMQ client
# Assuming the client is in src/services/rabbitmq_client.py
from document_service.services.rabbitmq_client import RabbitMQClient
from document_service.config.settings import Settings


@pytest.fixture
def rabbitmq_settings():
    """Fixture to provide RabbitMQ connection settings for tests."""
    return {
        "host": os.environ.get("RABBITMQ_HOST", "localhost"),
        "port": int(os.environ.get("RABBITMQ_PORT", 5672)),
        "virtual_host": os.environ.get("RABBITMQ_VHOST", "/"),
        "exchange": "mca.documents",
        "document_processing_queue": "document-processing",
        "data_extraction_queue": "data-extraction",
        "use_tls": os.environ.get("RABBITMQ_USE_TLS", "False").lower() == "true",
        "cert_path": os.environ.get("RABBITMQ_CERT_PATH", "/certs/client.pem"),
        "key_path": os.environ.get("RABBITMQ_KEY_PATH", "/certs/client.key"),
        "ca_path": os.environ.get("RABBITMQ_CA_PATH", "/certs/ca.pem"),
    }


@pytest.fixture
def rabbitmq_connection(rabbitmq_settings):
    """Fixture to create a RabbitMQ connection for tests.
    
    This creates a real connection to RabbitMQ for integration testing.
    """
    # Configure SSL context if TLS is enabled
    ssl_options = None
    if rabbitmq_settings["use_tls"]:
        ssl_context = ssl.create_default_context(cafile=rabbitmq_settings["ca_path"])
        ssl_context.load_cert_chain(
            rabbitmq_settings["cert_path"],
            rabbitmq_settings["key_path"]
        )
        ssl_context.check_hostname = True
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_options = pika.SSLOptions(ssl_context)
        credentials = ExternalCredentials()
    else:
        credentials = pika.PlainCredentials('guest', 'guest')
    
    # Create connection parameters
    params = ConnectionParameters(
        host=rabbitmq_settings["host"],
        port=rabbitmq_settings["port"],
        virtual_host=rabbitmq_settings["virtual_host"],
        credentials=credentials,
        ssl_options=ssl_options
    )
    
    # Create connection
    connection = BlockingConnection(params)
    
    # Setup exchange and queues for testing
    channel = connection.channel()
    channel.exchange_declare(
        exchange=rabbitmq_settings["exchange"],
        exchange_type='fanout',
        durable=True
    )
    
    # Declare queues
    channel.queue_declare(
        queue=rabbitmq_settings["document_processing_queue"],
        durable=True
    )
    channel.queue_declare(
        queue=rabbitmq_settings["data_extraction_queue"],
        durable=True
    )
    
    # Bind queues to exchange
    channel.queue_bind(
        exchange=rabbitmq_settings["exchange"],
        queue=rabbitmq_settings["document_processing_queue"]
    )
    channel.queue_bind(
        exchange=rabbitmq_settings["exchange"],
        queue=rabbitmq_settings["data_extraction_queue"]
    )
    
    # Purge queues to ensure clean state
    channel.queue_purge(rabbitmq_settings["document_processing_queue"])
    channel.queue_purge(rabbitmq_settings["data_extraction_queue"])
    
    yield connection
    
    # Cleanup
    channel = connection.channel()
    channel.queue_purge(rabbitmq_settings["document_processing_queue"])
    channel.queue_purge(rabbitmq_settings["data_extraction_queue"])
    connection.close()


@pytest.fixture
def rabbitmq_client(rabbitmq_settings):
    """Fixture to create a RabbitMQ client for testing."""
    # Create a Settings object with the test settings
    settings = Settings()
    settings.RABBITMQ_HOST = rabbitmq_settings["host"]
    settings.RABBITMQ_PORT = rabbitmq_settings["port"]
    settings.RABBITMQ_VHOST = rabbitmq_settings["virtual_host"]
    settings.RABBITMQ_EXCHANGE = rabbitmq_settings["exchange"]
    settings.RABBITMQ_DOCUMENT_PROCESSING_QUEUE = rabbitmq_settings["document_processing_queue"]
    settings.RABBITMQ_DATA_EXTRACTION_QUEUE = rabbitmq_settings["data_extraction_queue"]
    settings.RABBITMQ_USE_TLS = rabbitmq_settings["use_tls"]
    settings.RABBITMQ_CERT_PATH = rabbitmq_settings["cert_path"]
    settings.RABBITMQ_KEY_PATH = rabbitmq_settings["key_path"]
    settings.RABBITMQ_CA_PATH = rabbitmq_settings["ca_path"]
    
    # Create the client
    client = RabbitMQClient(settings)
    
    yield client
    
    # Cleanup
    if hasattr(client, '_connection') and client._connection and client._connection.is_open:
        client._connection.close()


class TestRabbitMQConnection:
    """Test RabbitMQ connection functionality."""
    
    def test_connection_with_tls(self, monkeypatch):
        """Test that the client can connect to RabbitMQ with TLS and client certificate authentication."""
        # Set environment variables for TLS
        monkeypatch.setenv("RABBITMQ_USE_TLS", "True")
        monkeypatch.setenv("RABBITMQ_CERT_PATH", "/certs/client.pem")
        monkeypatch.setenv("RABBITMQ_KEY_PATH", "/certs/client.key")
        monkeypatch.setenv("RABBITMQ_CA_PATH", "/certs/ca.pem")
        
        # Mock SSL context and connection
        with mock.patch('ssl.create_default_context') as mock_ssl_context, \
             mock.patch('pika.adapters.blocking_connection.BlockingConnection') as mock_connection:
            
            # Setup mock SSL context
            mock_ssl_context.return_value = mock.MagicMock()
            
            # Setup mock connection
            mock_connection_instance = mock.MagicMock()
            mock_connection.return_value = mock_connection_instance
            mock_channel = mock.MagicMock()
            mock_connection_instance.channel.return_value = mock_channel
            
            # Create settings
            settings = Settings()
            
            # Create client
            client = RabbitMQClient(settings)
            client.connect()
            
            # Verify SSL context was created with correct parameters
            mock_ssl_context.assert_called_once()
            mock_ssl_context.return_value.load_cert_chain.assert_called_once_with(
                "/certs/client.pem", "/certs/client.key")
            
            # Verify connection was created with SSL options
            mock_connection.assert_called_once()
            call_args = mock_connection.call_args[0][0]
            assert call_args.ssl_options is not None
            
            # Verify exchange declaration
            mock_channel.exchange_declare.assert_called_once()
            exchange_args = mock_channel.exchange_declare.call_args[1]
            assert exchange_args['exchange'] == settings.RABBITMQ_EXCHANGE
            
            # Cleanup
            client.disconnect()


class TestRabbitMQMessageConsumption:
    """Test RabbitMQ message consumption functionality."""
    
    def test_consume_message_from_queue(self, rabbitmq_connection, rabbitmq_settings):
        """Test that the client can consume messages from the document-processing queue."""
        # Create a test message
        test_message = {
            "document_id": "test-doc-123",
            "file_type": "pdf",
            "sender": "test@example.com",
            "subject": "Test Document",
            "timestamp": "2023-01-01T12:00:00Z",
            "message_id": "msg-123",
            "metadata": {"source": "test"}
        }
        
        # Create a flag to signal message receipt
        message_received = threading.Event()
        received_message = [None]
        
        # Define a callback function to process the message
        def message_callback(ch, method, properties, body):
            received_message[0] = json.loads(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            message_received.set()
        
        # Create a channel and publish a message
        channel = rabbitmq_connection.channel()
        channel.basic_publish(
            exchange=rabbitmq_settings["exchange"],
            routing_key='',  # Using fanout exchange, so routing key is ignored
            body=json.dumps(test_message).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )
        
        # Start consuming in a separate thread
        consume_thread = threading.Thread(target=lambda: channel.basic_consume(
            queue=rabbitmq_settings["document_processing_queue"],
            on_message_callback=message_callback
        ))
        consume_thread.daemon = True
        consume_thread.start()
        
        # Start consuming
        channel.start_consuming()
        
        # Wait for message to be received (with timeout)
        assert message_received.wait(timeout=5), "Message was not received within timeout"
        
        # Stop consuming
        channel.stop_consuming()
        
        # Verify the message content
        assert received_message[0] == test_message

    def test_message_acknowledgment(self, rabbitmq_connection, rabbitmq_settings):
        """Test that messages are properly acknowledged after processing."""
        # Create a test message
        test_message = {"test": "acknowledgment"}
        
        # Create a flag to signal message acknowledgment
        ack_received = threading.Event()
        
        # Define a callback function that verifies acknowledgment
        def message_callback(ch, method, properties, body):
            # Acknowledge the message
            ch.basic_ack(delivery_tag=method.delivery_tag)
            ack_received.set()
        
        # Create a channel and publish a message
        channel = rabbitmq_connection.channel()
        channel.basic_publish(
            exchange=rabbitmq_settings["exchange"],
            routing_key='',
            body=json.dumps(test_message).encode('utf-8')
        )
        
        # Start consuming in a separate thread
        consume_thread = threading.Thread(target=lambda: channel.basic_consume(
            queue=rabbitmq_settings["document_processing_queue"],
            on_message_callback=message_callback
        ))
        consume_thread.daemon = True
        consume_thread.start()
        
        # Start consuming
        channel.start_consuming()
        
        # Wait for acknowledgment (with timeout)
        assert ack_received.wait(timeout=5), "Acknowledgment was not received within timeout"
        
        # Stop consuming
        channel.stop_consuming()
        
        # Verify the queue is empty (message was acknowledged and removed)
        method_frame = channel.basic_get(rabbitmq_settings["document_processing_queue"])
        assert method_frame[0] is None, "Queue should be empty after acknowledgment"

    def test_message_rejection(self, rabbitmq_connection, rabbitmq_settings):
        """Test that messages can be rejected and requeued."""
        # Create a test message
        test_message = {"test": "rejection"}
        
        # Create flags to signal message events
        first_delivery = threading.Event()
        second_delivery = threading.Event()
        delivery_count = [0]
        
        # Define a callback function that rejects the first delivery and accepts the second
        def message_callback(ch, method, properties, body):
            delivery_count[0] += 1
            
            if delivery_count[0] == 1:
                # Reject and requeue on first delivery
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
                first_delivery.set()
            else:
                # Acknowledge on second delivery
                ch.basic_ack(delivery_tag=method.delivery_tag)
                second_delivery.set()
        
        # Create a channel and publish a message
        channel = rabbitmq_connection.channel()
        channel.basic_publish(
            exchange=rabbitmq_settings["exchange"],
            routing_key='',
            body=json.dumps(test_message).encode('utf-8')
        )
        
        # Start consuming in a separate thread
        consume_thread = threading.Thread(target=lambda: channel.basic_consume(
            queue=rabbitmq_settings["document_processing_queue"],
            on_message_callback=message_callback
        ))
        consume_thread.daemon = True
        consume_thread.start()
        
        # Start consuming
        channel.start_consuming()
        
        # Wait for first delivery and rejection (with timeout)
        assert first_delivery.wait(timeout=5), "First delivery was not processed within timeout"
        
        # Wait for second delivery and acknowledgment (with timeout)
        assert second_delivery.wait(timeout=5), "Second delivery was not processed within timeout"
        
        # Stop consuming
        channel.stop_consuming()
        
        # Verify the message was processed twice
        assert delivery_count[0] == 2, "Message should have been delivered twice"


class TestRabbitMQMessagePublishing:
    """Test RabbitMQ message publishing functionality."""
    
    def test_publish_message_to_queue(self, rabbitmq_connection, rabbitmq_settings):
        """Test that the client can publish messages to the data-extraction queue."""
        # Create a test message
        test_message = {
            "document_id": "test-doc-456",
            "classification": "invoice",
            "confidence": 0.95,
            "s3_path": "s3://mca-documents-staging/test-doc-456.pdf",
            "metadata": {"pages": 2, "source": "test"}
        }
        
        # Create a flag to signal message receipt
        message_received = threading.Event()
        received_message = [None]
        
        # Define a callback function to process the message
        def message_callback(ch, method, properties, body):
            received_message[0] = json.loads(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            message_received.set()
        
        # Create a channel
        channel = rabbitmq_connection.channel()
        
        # Start consuming from the data-extraction queue
        channel.basic_consume(
            queue=rabbitmq_settings["data_extraction_queue"],
            on_message_callback=message_callback
        )
        
        # Start consuming in a separate thread
        consume_thread = threading.Thread(target=channel.start_consuming)
        consume_thread.daemon = True
        consume_thread.start()
        
        # Publish a message to the exchange
        channel2 = rabbitmq_connection.channel()
        channel2.basic_publish(
            exchange=rabbitmq_settings["exchange"],
            routing_key='',  # Using fanout exchange, so routing key is ignored
            body=json.dumps(test_message).encode('utf-8'),
            properties=pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json'
            )
        )
        
        # Wait for message to be received (with timeout)
        assert message_received.wait(timeout=5), "Message was not received within timeout"
        
        # Stop consuming
        channel.stop_consuming()
        
        # Verify the message content
        assert received_message[0] == test_message

    def test_message_serialization(self, rabbitmq_connection, rabbitmq_settings):
        """Test that messages are properly serialized in JSON format."""
        # Create a test message with various data types
        test_message = {
            "string": "test",
            "integer": 123,
            "float": 123.45,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"}
        }
        
        # Create a flag to signal message receipt
        message_received = threading.Event()
        received_message = [None]
        received_content_type = [None]
        
        # Define a callback function to process the message
        def message_callback(ch, method, properties, body):
            received_message[0] = json.loads(body)
            received_content_type[0] = properties.content_type
            ch.basic_ack(delivery_tag=method.delivery_tag)
            message_received.set()
        
        # Create a channel
        channel = rabbitmq_connection.channel()
        
        # Start consuming from the data-extraction queue
        channel.basic_consume(
            queue=rabbitmq_settings["data_extraction_queue"],
            on_message_callback=message_callback
        )
        
        # Start consuming in a separate thread
        consume_thread = threading.Thread(target=channel.start_consuming)
        consume_thread.daemon = True
        consume_thread.start()
        
        # Publish a message to the exchange
        channel2 = rabbitmq_connection.channel()
        channel2.basic_publish(
            exchange=rabbitmq_settings["exchange"],
            routing_key='',
            body=json.dumps(test_message).encode('utf-8'),
            properties=pika.BasicProperties(
                content_type='application/json'
            )
        )
        
        # Wait for message to be received (with timeout)
        assert message_received.wait(timeout=5), "Message was not received within timeout"
        
        # Stop consuming
        channel.stop_consuming()
        
        # Verify the message content and content type
        assert received_message[0] == test_message
        assert received_content_type[0] == 'application/json'


class TestRabbitMQErrorHandling:
    """Test RabbitMQ error handling and recovery functionality."""
    
    def test_connection_error_handling(self):
        """Test that the client handles connection errors and attempts to reconnect."""
        # Mock the pika connection to simulate connection errors
        with mock.patch('pika.adapters.blocking_connection.BlockingConnection') as mock_connection:
            # Setup mock connection to raise an exception on first attempt, then succeed
            mock_connection.side_effect = [
                pika.exceptions.AMQPConnectionError("Connection refused"),
                mock.MagicMock()  # Successful connection on second attempt
            ]
            
            # Create a mock channel
            mock_channel = mock.MagicMock()
            mock_connection.return_value.channel.return_value = mock_channel
            
            # Create settings
            settings = Settings()
            settings.RABBITMQ_RECONNECT_ATTEMPTS = 3
            settings.RABBITMQ_RECONNECT_DELAY = 0.1  # Short delay for testing
            
            # Create client
            client = RabbitMQClient(settings)
            
            # Connect should succeed after retry
            client.connect()
            
            # Verify connection was attempted twice
            assert mock_connection.call_count == 2
            
            # Cleanup
            client.disconnect()
    
    def test_channel_error_handling(self):
        """Test that the client handles channel errors and attempts to recover."""
        # Mock the pika connection and channel
        with mock.patch('pika.adapters.blocking_connection.BlockingConnection') as mock_connection:
            # Setup mock connection
            mock_connection_instance = mock.MagicMock()
            mock_connection.return_value = mock_connection_instance
            
            # Setup mock channel to raise an exception on first attempt, then succeed
            mock_channel1 = mock.MagicMock()
            mock_channel1.exchange_declare.side_effect = pika.exceptions.ChannelClosedByBroker(404, "Not found")
            
            mock_channel2 = mock.MagicMock()
            
            mock_connection_instance.channel.side_effect = [mock_channel1, mock_channel2]
            
            # Create settings
            settings = Settings()
            settings.RABBITMQ_RECONNECT_ATTEMPTS = 3
            settings.RABBITMQ_RECONNECT_DELAY = 0.1  # Short delay for testing
            
            # Create client
            client = RabbitMQClient(settings)
            
            # Connect should succeed after channel recovery
            client.connect()
            
            # Verify channel was created twice
            assert mock_connection_instance.channel.call_count == 2
            
            # Verify exchange declaration was attempted on both channels
            mock_channel1.exchange_declare.assert_called_once()
            mock_channel2.exchange_declare.assert_called_once()
            
            # Cleanup
            client.disconnect()
    
    def test_publish_retry_logic(self):
        """Test that the client retries failed message publishing."""
        # Mock the pika connection and channel
        with mock.patch('pika.adapters.blocking_connection.BlockingConnection') as mock_connection:
            # Setup mock connection
            mock_connection_instance = mock.MagicMock()
            mock_connection.return_value = mock_connection_instance
            
            # Setup mock channel
            mock_channel = mock.MagicMock()
            mock_connection_instance.channel.return_value = mock_channel
            
            # Make basic_publish fail on first attempt, then succeed
            mock_channel.basic_publish.side_effect = [
                pika.exceptions.UnroutableError([mock.MagicMock()]),
                None  # Success on second attempt
            ]
            
            # Create settings
            settings = Settings()
            settings.RABBITMQ_PUBLISH_RETRY_ATTEMPTS = 3
            settings.RABBITMQ_PUBLISH_RETRY_DELAY = 0.1  # Short delay for testing
            
            # Create client
            client = RabbitMQClient(settings)
            client.connect()
            
            # Publish a message
            test_message = {"test": "retry"}
            client.publish_message("data-extraction", test_message)
            
            # Verify basic_publish was called twice
            assert mock_channel.basic_publish.call_count == 2
            
            # Cleanup
            client.disconnect()


class TestRabbitMQClientIntegration:
    """Test the RabbitMQ client integration with the Document Service."""
    
    def test_client_consume_and_process(self, rabbitmq_client, rabbitmq_connection, rabbitmq_settings):
        """Test that the client can consume and process messages from the document-processing queue."""
        # Create a test message
        test_message = {
            "document_id": "test-doc-789",
            "file_type": "pdf",
            "sender": "test@example.com",
            "subject": "Test Document",
            "timestamp": "2023-01-01T12:00:00Z",
            "message_id": "msg-789",
            "metadata": {"source": "test"}
        }
        
        # Create a flag to signal message processing
        message_processed = threading.Event()
        processed_message = [None]
        
        # Mock the document processing function
        def mock_process_document(message):
            processed_message[0] = message
            message_processed.set()
            return True
        
        # Start the client with the mock processing function
        rabbitmq_client.start_consuming("document-processing", mock_process_document)
        
        # Publish a test message
        channel = rabbitmq_connection.channel()
        channel.basic_publish(
            exchange=rabbitmq_settings["exchange"],
            routing_key='',
            body=json.dumps(test_message).encode('utf-8'),
            properties=pika.BasicProperties(
                content_type='application/json'
            )
        )
        
        # Wait for message to be processed (with timeout)
        assert message_processed.wait(timeout=5), "Message was not processed within timeout"
        
        # Stop consuming
        rabbitmq_client.stop_consuming()
        
        # Verify the message was processed correctly
        assert processed_message[0] == test_message
    
    def test_client_publish_to_data_extraction(self, rabbitmq_client, rabbitmq_connection, rabbitmq_settings):
        """Test that the client can publish messages to the data-extraction queue."""
        # Create a test message
        test_message = {
            "document_id": "test-doc-101112",
            "classification": "invoice",
            "confidence": 0.95,
            "s3_path": "s3://mca-documents-staging/test-doc-101112.pdf",
            "metadata": {"pages": 2, "source": "test"}
        }
        
        # Create a flag to signal message receipt
        message_received = threading.Event()
        received_message = [None]
        
        # Define a callback function to process the message
        def message_callback(ch, method, properties, body):
            received_message[0] = json.loads(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            message_received.set()
        
        # Create a channel
        channel = rabbitmq_connection.channel()
        
        # Start consuming from the data-extraction queue
        channel.basic_consume(
            queue=rabbitmq_settings["data_extraction_queue"],
            on_message_callback=message_callback
        )
        
        # Start consuming in a separate thread
        consume_thread = threading.Thread(target=channel.start_consuming)
        consume_thread.daemon = True
        consume_thread.start()
        
        # Connect the client
        rabbitmq_client.connect()
        
        # Publish a message using the client
        rabbitmq_client.publish_message("data-extraction", test_message)
        
        # Wait for message to be received (with timeout)
        assert message_received.wait(timeout=5), "Message was not received within timeout"
        
        # Stop consuming
        channel.stop_consuming()
        
        # Disconnect the client
        rabbitmq_client.disconnect()
        
        # Verify the message content
        assert received_message[0] == test_message