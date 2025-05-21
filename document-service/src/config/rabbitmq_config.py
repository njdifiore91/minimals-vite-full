"""
RabbitMQ Configuration for Document Service

This module provides configuration for RabbitMQ connections and messaging settings
for the Document Service. It defines connection parameters, exchange and queue
configurations, message consumption options, and security settings.

The configuration enables the service to:
- Consume messages from the Email Service
- Publish classification results to the OCR Service
- Implement secure TLS connections with client certificate authentication
- Handle connection errors and recovery
- Ensure consistent message serialization in JSON format
"""

import os
import ssl
import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Union

import pika
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

# Configure logger
logger = logging.getLogger(__name__)

# RabbitMQ Connection Settings
RABBITMQ_HOST = os.environ.get('RABBITMQ_HOST', 'localhost')
RABBITMQ_PORT = int(os.environ.get('RABBITMQ_PORT', '5671'))
RABBITMQ_VHOST = os.environ.get('RABBITMQ_VHOST', '/')
RABBITMQ_HEARTBEAT = int(os.environ.get('RABBITMQ_HEARTBEAT', '60'))
RABBITMQ_CONNECTION_TIMEOUT = int(os.environ.get('RABBITMQ_CONNECTION_TIMEOUT', '30'))
RABBITMQ_BLOCKED_CONNECTION_TIMEOUT = int(os.environ.get('RABBITMQ_BLOCKED_CONNECTION_TIMEOUT', '300'))

# TLS Certificate Paths
CA_CERT_PATH = os.environ.get('RABBITMQ_CA_CERT', '/etc/rabbitmq/certs/ca_certificate.pem')
CLIENT_CERT_PATH = os.environ.get('RABBITMQ_CLIENT_CERT', '/etc/rabbitmq/certs/client_certificate.pem')
CLIENT_KEY_PATH = os.environ.get('RABBITMQ_CLIENT_KEY', '/etc/rabbitmq/certs/client_key.pem')

# Exchange and Queue Settings
EXCHANGE_NAME = 'mca.documents'
EXCHANGE_TYPE = 'fanout'
QUEUE_NAME = 'document-processing'
DEAD_LETTER_EXCHANGE = 'mca.dead-letter'
DEAD_LETTER_QUEUE = 'document-processing-dead-letter'

# Retry Settings
MAX_RETRIES = int(os.environ.get('RABBITMQ_MAX_RETRIES', '5'))
INITIAL_RETRY_DELAY = float(os.environ.get('RABBITMQ_INITIAL_RETRY_DELAY', '0.5'))
MAX_RETRY_DELAY = float(os.environ.get('RABBITMQ_MAX_RETRY_DELAY', '30.0'))

# Message Settings
CONTENT_TYPE = 'application/json'
DELIVERY_MODE = 2  # Persistent

# Prefetch Settings
PREFETCH_COUNT = int(os.environ.get('RABBITMQ_PREFETCH_COUNT', '10'))


def create_ssl_context() -> ssl.SSLContext:
    """
    Create an SSL context for RabbitMQ connection with client certificate authentication.
    
    Returns:
        ssl.SSLContext: Configured SSL context for TLS connection
        
    Raises:
        FileNotFoundError: If certificate files cannot be found
        ssl.SSLError: If there are issues with the certificates
    """
    try:
        # Create SSL context with TLS 1.2
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Require certificate verification
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Load CA certificate for server verification
        context.load_verify_locations(cafile=CA_CERT_PATH)
        
        # Load client certificate and key for client authentication
        context.load_cert_chain(certfile=CLIENT_CERT_PATH, keyfile=CLIENT_KEY_PATH)
        
        # Set TLS version to 1.2 minimum
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        
        # Disable insecure cipher suites
        context.set_ciphers('HIGH:!aNULL:!MD5:!RC4')
        
        return context
    except (FileNotFoundError, ssl.SSLError) as e:
        logger.error(f"Failed to load certificate files: {str(e)}")
        raise


def get_connection_parameters() -> ConnectionParameters:
    """
    Create connection parameters for RabbitMQ with TLS configuration.
    
    Returns:
        pika.ConnectionParameters: Configured connection parameters
    """
    # Create SSL context
    ssl_context = create_ssl_context()
    
    # Create SSL options with the context and server hostname
    ssl_options = SSLOptions(ssl_context, RABBITMQ_HOST)
    
    # Use external credentials for client certificate authentication
    credentials = ExternalCredentials()
    
    # Create and return connection parameters
    return ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        ssl_options=ssl_options,
        heartbeat=RABBITMQ_HEARTBEAT,
        blocked_connection_timeout=RABBITMQ_BLOCKED_CONNECTION_TIMEOUT,
        connection_attempts=3,
        retry_delay=1.0,
        socket_timeout=RABBITMQ_CONNECTION_TIMEOUT
    )


def create_rabbitmq_connection() -> BlockingConnection:
    """
    Create a connection to RabbitMQ with error handling and retry logic.
    
    Returns:
        pika.BlockingConnection: Established connection to RabbitMQ
        
    Raises:
        AMQPConnectionError: If connection cannot be established after retries
    """
    retry_count = 0
    retry_delay = INITIAL_RETRY_DELAY
    
    while retry_count <= MAX_RETRIES:
        try:
            # Get connection parameters
            parameters = get_connection_parameters()
            
            # Establish connection
            logger.info(f"Connecting to RabbitMQ at {RABBITMQ_HOST}:{RABBITMQ_PORT}")
            connection = BlockingConnection(parameters)
            logger.info("Successfully connected to RabbitMQ")
            
            return connection
            
        except AMQPConnectionError as e:
            retry_count += 1
            if retry_count > MAX_RETRIES:
                logger.error(f"Failed to connect to RabbitMQ after {MAX_RETRIES} attempts: {str(e)}")
                raise
            
            logger.warning(f"Connection attempt {retry_count} failed: {str(e)}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            
            # Implement exponential backoff with a maximum delay
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)


def setup_rabbitmq_channel(connection: BlockingConnection) -> pika.channel.Channel:
    """
    Set up a RabbitMQ channel with the required exchanges and queues.
    
    Args:
        connection: Established RabbitMQ connection
        
    Returns:
        pika.channel.Channel: Configured RabbitMQ channel
        
    Raises:
        ChannelClosed: If channel setup fails
    """
    try:
        # Create channel
        channel = connection.channel()
        
        # Set QoS prefetch count
        channel.basic_qos(prefetch_count=PREFETCH_COUNT)
        
        # Declare dead letter exchange
        channel.exchange_declare(
            exchange=DEAD_LETTER_EXCHANGE,
            exchange_type='direct',
            durable=True
        )
        
        # Declare dead letter queue
        channel.queue_declare(
            queue=DEAD_LETTER_QUEUE,
            durable=True
        )
        
        # Bind dead letter queue to dead letter exchange
        channel.queue_bind(
            queue=DEAD_LETTER_QUEUE,
            exchange=DEAD_LETTER_EXCHANGE,
            routing_key=QUEUE_NAME
        )
        
        # Declare main exchange
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE,
            durable=True
        )
        
        # Declare main queue with dead letter configuration
        channel.queue_declare(
            queue=QUEUE_NAME,
            durable=True,
            arguments={
                'x-dead-letter-exchange': DEAD_LETTER_EXCHANGE,
                'x-dead-letter-routing-key': QUEUE_NAME,
                'x-message-ttl': 1000 * 60 * 60 * 24  # 24 hours in milliseconds
            }
        )
        
        # Bind main queue to main exchange
        channel.queue_bind(
            queue=QUEUE_NAME,
            exchange=EXCHANGE_NAME
        )
        
        logger.info(f"Successfully set up RabbitMQ channel with exchange '{EXCHANGE_NAME}' and queue '{QUEUE_NAME}'")
        return channel
        
    except (ChannelClosed, ChannelClosedByBroker) as e:
        logger.error(f"Failed to set up RabbitMQ channel: {str(e)}")
        raise


def serialize_message(message: Dict[str, Any]) -> bytes:
    """
    Serialize a message to JSON format.
    
    Args:
        message: Dictionary containing message data
        
    Returns:
        bytes: JSON-serialized message as bytes
    """
    try:
        return json.dumps(message, ensure_ascii=False).encode('utf-8')
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize message: {str(e)}")
        raise


def deserialize_message(body: bytes) -> Dict[str, Any]:
    """
    Deserialize a JSON message from bytes.
    
    Args:
        body: Byte string containing JSON data
        
    Returns:
        Dict[str, Any]: Deserialized message as dictionary
        
    Raises:
        ValueError: If message cannot be deserialized
    """
    try:
        return json.loads(body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to deserialize message: {str(e)}")
        raise ValueError(f"Invalid message format: {str(e)}")


def publish_message(channel: pika.channel.Channel, message: Dict[str, Any], routing_key: str = '') -> None:
    """
    Publish a message to the RabbitMQ exchange with error handling.
    
    Args:
        channel: RabbitMQ channel
        message: Dictionary containing message data
        routing_key: Optional routing key (default is empty string for fanout exchange)
        
    Raises:
        ConnectionClosed: If connection is lost during publishing
    """
    try:
        # Serialize message
        body = serialize_message(message)
        
        # Publish message with persistent delivery mode
        channel.basic_publish(
            exchange=EXCHANGE_NAME,
            routing_key=routing_key,
            body=body,
            properties=pika.BasicProperties(
                content_type=CONTENT_TYPE,
                delivery_mode=DELIVERY_MODE,
                timestamp=int(time.time()),
                message_id=str(time.time()),
                app_id='document-service'
            )
        )
        logger.debug(f"Published message to exchange '{EXCHANGE_NAME}' with routing key '{routing_key}'")
        
    except (ConnectionClosed, ConnectionClosedByBroker) as e:
        logger.error(f"Failed to publish message: {str(e)}")
        raise


class RabbitMQClient:
    """
    Client for RabbitMQ operations with connection management and error handling.
    """
    
    def __init__(self):
        """
        Initialize the RabbitMQ client.
        """
        self.connection = None
        self.channel = None
    
    def connect(self) -> None:
        """
        Establish connection to RabbitMQ and set up channel.
        
        Raises:
            AMQPConnectionError: If connection cannot be established
            ChannelClosed: If channel setup fails
        """
        if self.connection is None or self.connection.is_closed:
            self.connection = create_rabbitmq_connection()
            self.channel = setup_rabbitmq_channel(self.connection)
    
    def close(self) -> None:
        """
        Close the RabbitMQ connection and channel safely.
        """
        if self.connection and self.connection.is_open:
            try:
                if self.channel and self.channel.is_open:
                    self.channel.close()
                self.connection.close()
                logger.info("RabbitMQ connection closed")
            except Exception as e:
                logger.warning(f"Error while closing RabbitMQ connection: {str(e)}")
    
    def publish(self, message: Dict[str, Any], routing_key: str = '') -> None:
        """
        Publish a message to RabbitMQ with automatic reconnection.
        
        Args:
            message: Dictionary containing message data
            routing_key: Optional routing key
            
        Raises:
            AMQPConnectionError: If connection cannot be re-established after retries
        """
        try:
            # Ensure connection is established
            self.connect()
            
            # Publish message
            publish_message(self.channel, message, routing_key)
            
        except (ConnectionClosed, ConnectionClosedByBroker) as e:
            logger.warning(f"Connection lost during publish: {str(e)}. Attempting to reconnect...")
            
            # Try to reconnect and publish again
            self.connection = None  # Force reconnection
            self.connect()
            publish_message(self.channel, message, routing_key)
    
    def consume(self, callback: Callable[[Dict[str, Any], pika.spec.Basic.Deliver, pika.spec.BasicProperties], None]) -> None:
        """
        Start consuming messages from the queue with the provided callback.
        
        Args:
            callback: Function to call when a message is received. Should accept message content,
                      delivery info, and properties as arguments.
                      
        Raises:
            AMQPConnectionError: If connection cannot be established
        """
        def wrapped_callback(ch, method, properties, body):
            """
            Wrapper for the user callback that handles message deserialization and exceptions.
            """
            try:
                # Deserialize message
                message = deserialize_message(body)
                
                # Call user callback
                callback(message, method, properties)
                
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                
                # Reject message and requeue if it's not a deserialization error
                if not isinstance(e, ValueError):
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                else:
                    # For deserialization errors, don't requeue
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        
        # Ensure connection is established
        self.connect()
        
        # Start consuming
        self.channel.basic_consume(
            queue=QUEUE_NAME,
            on_message_callback=wrapped_callback
        )
        
        logger.info(f"Started consuming from queue '{QUEUE_NAME}'")
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            self.channel.stop_consuming()
            self.close()
        except (ConnectionClosed, ConnectionClosedByBroker) as e:
            logger.warning(f"Connection lost during consumption: {str(e)}")
            raise


# Create a singleton instance for use throughout the application
rabbitmq_client = RabbitMQClient()


# Helper functions for simplified usage
def get_rabbitmq_client() -> RabbitMQClient:
    """
    Get the RabbitMQ client singleton instance.
    
    Returns:
        RabbitMQClient: Singleton instance of the RabbitMQ client
    """
    return rabbitmq_client


def consume_messages(callback: Callable[[Dict[str, Any], pika.spec.Basic.Deliver, pika.spec.BasicProperties], None]) -> None:
    """
    Start consuming messages with automatic reconnection.
    
    Args:
        callback: Function to call when a message is received
    """
    retry_count = 0
    retry_delay = INITIAL_RETRY_DELAY
    
    while True:
        try:
            # Get client and start consuming
            client = get_rabbitmq_client()
            client.consume(callback)
            
            # Reset retry count on successful connection
            retry_count = 0
            retry_delay = INITIAL_RETRY_DELAY
            
        except (AMQPConnectionError, ConnectionClosed, ConnectionClosedByBroker) as e:
            retry_count += 1
            
            logger.warning(f"Connection lost, retry attempt {retry_count}: {str(e)}")
            time.sleep(retry_delay)
            
            # Implement exponential backoff with a maximum delay
            retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
            
            # Force reconnection
            rabbitmq_client.connection = None
        
        except KeyboardInterrupt:
            logger.info("Stopping consumer due to keyboard interrupt")
            break
        
        except Exception as e:
            logger.error(f"Unexpected error in consumer: {str(e)}")
            raise