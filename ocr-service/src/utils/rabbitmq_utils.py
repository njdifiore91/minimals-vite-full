"""
RabbitMQ Utilities for OCR Service.

This module provides utility functions for connecting to RabbitMQ, publishing messages,
consuming messages, and handling message acknowledgments. These utilities are essential
for the OCR Service's integration with the message queue system.
"""

import json
import logging
import os
import socket
import ssl
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union, cast

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import (AMQPConnectionError, AMQPChannelError, 
                            ConnectionClosedByBroker, StreamLostError,
                            ChannelClosedByBroker, ChannelWrongStateError)
from pika.spec import Basic, BasicProperties

# Import from relative paths to avoid circular imports
from .retry_utils import (retry, retry_rabbitmq_operation, 
                         async_retry_rabbitmq_operation, calculate_backoff)

# Configure logger
logger = logging.getLogger(__name__)

# Type variables for callback functions
T = TypeVar('T')
MessageCallback = Callable[[BlockingChannel, Basic.Deliver, BasicProperties, bytes], None]

# Default RabbitMQ configuration
DEFAULT_CONNECTION_ATTEMPTS = 3
DEFAULT_RETRY_DELAY = 2
DEFAULT_HEARTBEAT = 60
DEFAULT_BLOCKED_CONNECTION_TIMEOUT = 300
DEFAULT_PREFETCH_COUNT = 10
DEFAULT_EXCHANGE_TYPE = 'topic'
DEFAULT_DELIVERY_MODE = 2  # Persistent messages

# Default exchange and queue names based on technical specification
DEFAULT_EXCHANGE = 'mca.documents'
DEFAULT_OCR_REQUEST_QUEUE = 'ocr.request'
DEFAULT_PROCESSING_QUEUE = 'data.processing'


class RabbitMQConnectionError(Exception):
    """Exception raised for RabbitMQ connection errors."""
    pass


class RabbitMQChannelError(Exception):
    """Exception raised for RabbitMQ channel errors."""
    pass


class RabbitMQClient:
    """Client for interacting with RabbitMQ.
    
    This class provides methods for connecting to RabbitMQ, publishing messages,
    and consuming messages with automatic reconnection and error handling.
    """
    
    def __init__(self, 
                 host: str,
                 port: int = 5672,
                 virtual_host: str = '/',
                 username: str = 'guest',
                 password: str = 'guest',
                 connection_attempts: int = DEFAULT_CONNECTION_ATTEMPTS,
                 retry_delay: int = DEFAULT_RETRY_DELAY,
                 heartbeat: int = DEFAULT_HEARTBEAT,
                 blocked_connection_timeout: int = DEFAULT_BLOCKED_CONNECTION_TIMEOUT,
                 ssl_options: Optional[Dict[str, Any]] = None,
                 exchange: str = DEFAULT_EXCHANGE,
                 exchange_type: str = DEFAULT_EXCHANGE_TYPE,
                 prefetch_count: int = DEFAULT_PREFETCH_COUNT):
        """
        Initialize the RabbitMQ client.
        
        Args:
            host: RabbitMQ server hostname or IP address
            port: RabbitMQ server port
            virtual_host: RabbitMQ virtual host
            username: RabbitMQ username
            password: RabbitMQ password
            connection_attempts: Number of connection attempts
            retry_delay: Delay between connection attempts in seconds
            heartbeat: Heartbeat interval in seconds
            blocked_connection_timeout: Timeout for blocked connections in seconds
            ssl_options: SSL/TLS options for secure connections
            exchange: Default exchange name
            exchange_type: Default exchange type
            prefetch_count: Number of messages to prefetch
        """
        self.host = host
        self.port = port
        self.virtual_host = virtual_host
        self.username = username
        self.password = password
        self.connection_attempts = connection_attempts
        self.retry_delay = retry_delay
        self.heartbeat = heartbeat
        self.blocked_connection_timeout = blocked_connection_timeout
        self.ssl_options = ssl_options
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.prefetch_count = prefetch_count
        
        # Initialize connection and channel as None
        self.connection = None
        self.channel = None
        
        # Track connection state
        self.is_connected = False
        
        # Set up SSL context if needed
        self._setup_ssl_context()
    
    def _setup_ssl_context(self) -> None:
        """Set up SSL context for secure connections if SSL options are provided."""
        if self.ssl_options is None:
            # Check if environment variables indicate TLS should be used
            rabbitmq_use_tls = os.environ.get('RABBITMQ_USE_TLS', 'false').lower() == 'true'
            
            if rabbitmq_use_tls:
                # Create default SSL context with TLS 1.2
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                ssl_context.set_ciphers('ECDHE+AESGCM:!ECDSA')
                
                # Set verify mode based on environment variable
                verify_mode = os.environ.get('RABBITMQ_VERIFY_SSL', 'true').lower() == 'true'
                ssl_context.verify_mode = ssl.CERT_REQUIRED if verify_mode else ssl.CERT_NONE
                
                # Load CA certificate if provided
                ca_cert_path = os.environ.get('RABBITMQ_CA_CERT')
                if ca_cert_path and os.path.exists(ca_cert_path):
                    ssl_context.load_verify_locations(cafile=ca_cert_path)
                
                # Load client certificate and key if provided
                cert_path = os.environ.get('RABBITMQ_CLIENT_CERT')
                key_path = os.environ.get('RABBITMQ_CLIENT_KEY')
                if cert_path and key_path and os.path.exists(cert_path) and os.path.exists(key_path):
                    ssl_context.load_cert_chain(cert_path, key_path)
                
                self.ssl_options = pika.SSLOptions(context=ssl_context)
    
    def connect(self) -> None:
        """Connect to RabbitMQ server with retry logic."""
        if self.is_connected and self.connection and self.connection.is_open:
            return
        
        try:
            # Set up credentials
            credentials = pika.PlainCredentials(self.username, self.password)
            
            # Set up connection parameters
            params = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                virtual_host=self.virtual_host,
                credentials=credentials,
                connection_attempts=self.connection_attempts,
                retry_delay=self.retry_delay,
                heartbeat=self.heartbeat,
                blocked_connection_timeout=self.blocked_connection_timeout,
                ssl_options=self.ssl_options
            )
            
            logger.info(f"Connecting to RabbitMQ at {self.host}:{self.port}/{self.virtual_host}")
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()
            
            # Set QoS prefetch count
            self.channel.basic_qos(prefetch_count=self.prefetch_count)
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange,
                exchange_type=self.exchange_type,
                durable=True
            )
            
            self.is_connected = True
            logger.info("Successfully connected to RabbitMQ")
        
        except (AMQPConnectionError, socket.gaierror, ConnectionRefusedError) as e:
            self.is_connected = False
            logger.error(f"Failed to connect to RabbitMQ: {str(e)}")
            raise RabbitMQConnectionError(f"Failed to connect to RabbitMQ: {str(e)}") from e
    
    def ensure_connection(self) -> None:
        """Ensure that the connection to RabbitMQ is established."""
        if not self.is_connected or not self.connection or not self.connection.is_open:
            self.connect()
    
    def close(self) -> None:
        """Close the RabbitMQ connection and channel."""
        try:
            if self.channel and self.channel.is_open:
                logger.info("Closing RabbitMQ channel")
                self.channel.close()
            
            if self.connection and self.connection.is_open:
                logger.info("Closing RabbitMQ connection")
                self.connection.close()
        except Exception as e:
            logger.warning(f"Error while closing RabbitMQ connection: {str(e)}")
        finally:
            self.is_connected = False
            self.channel = None
            self.connection = None
    
    def declare_queue(self, queue_name: str, durable: bool = True, 
                     exclusive: bool = False, auto_delete: bool = False,
                     arguments: Optional[Dict[str, Any]] = None) -> None:
        """Declare a queue with the specified parameters.
        
        Args:
            queue_name: Name of the queue to declare
            durable: Whether the queue should survive broker restarts
            exclusive: Whether the queue is exclusive to this connection
            auto_delete: Whether the queue should be deleted when no longer used
            arguments: Additional arguments for queue declaration
        """
        self.ensure_connection()
        
        try:
            self.channel.queue_declare(
                queue=queue_name,
                durable=durable,
                exclusive=exclusive,
                auto_delete=auto_delete,
                arguments=arguments
            )
            logger.info(f"Declared queue: {queue_name}")
        except (AMQPChannelError, ChannelClosedByBroker) as e:
            logger.error(f"Failed to declare queue {queue_name}: {str(e)}")
            raise RabbitMQChannelError(f"Failed to declare queue {queue_name}: {str(e)}") from e
    
    def bind_queue(self, queue_name: str, exchange: Optional[str] = None, 
                  routing_key: str = '#') -> None:
        """Bind a queue to an exchange with the specified routing key.
        
        Args:
            queue_name: Name of the queue to bind
            exchange: Name of the exchange to bind to (defaults to self.exchange)
            routing_key: Routing key for the binding
        """
        self.ensure_connection()
        exchange_name = exchange or self.exchange
        
        try:
            self.channel.queue_bind(
                queue=queue_name,
                exchange=exchange_name,
                routing_key=routing_key
            )
            logger.info(f"Bound queue {queue_name} to exchange {exchange_name} with routing key {routing_key}")
        except (AMQPChannelError, ChannelClosedByBroker) as e:
            logger.error(f"Failed to bind queue {queue_name} to exchange {exchange_name}: {str(e)}")
            raise RabbitMQChannelError(f"Failed to bind queue {queue_name} to exchange {exchange_name}: {str(e)}") from e
    
    @retry_rabbitmq_operation
    def publish(self, message: Union[Dict[str, Any], List[Any], str, bytes], 
               exchange: Optional[str] = None, routing_key: str = '',
               properties: Optional[BasicProperties] = None,
               mandatory: bool = False) -> bool:
        """Publish a message to RabbitMQ with retry logic.
        
        Args:
            message: Message to publish (dict, list, string, or bytes)
            exchange: Exchange to publish to (defaults to self.exchange)
            routing_key: Routing key for the message
            properties: Message properties
            mandatory: Whether to raise an exception if the message cannot be routed
            
        Returns:
            bool: True if the message was published successfully
        """
        self.ensure_connection()
        exchange_name = exchange or self.exchange
        
        # Convert message to bytes if it's not already
        if isinstance(message, (dict, list)):
            message_bytes = json.dumps(message).encode('utf-8')
        elif isinstance(message, str):
            message_bytes = message.encode('utf-8')
        else:
            message_bytes = message
        
        # Set default properties if not provided
        if properties is None:
            properties = pika.BasicProperties(
                delivery_mode=DEFAULT_DELIVERY_MODE,  # Persistent message
                content_type='application/json' if isinstance(message, (dict, list)) else 'text/plain',
                timestamp=int(time.time())
            )
        
        try:
            self.channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,
                body=message_bytes,
                properties=properties,
                mandatory=mandatory
            )
            logger.debug(f"Published message to exchange {exchange_name} with routing key {routing_key}")
            return True
        except (AMQPConnectionError, ConnectionClosedByBroker, StreamLostError) as e:
            logger.warning(f"Connection error while publishing message: {str(e)}")
            # Reconnect and retry (handled by retry decorator)
            self.close()
            self.connect()
            raise
        except (AMQPChannelError, ChannelClosedByBroker, ChannelWrongStateError) as e:
            logger.warning(f"Channel error while publishing message: {str(e)}")
            # Recreate channel and retry (handled by retry decorator)
            if self.connection and self.connection.is_open:
                self.channel = self.connection.channel()
                self.channel.basic_qos(prefetch_count=self.prefetch_count)
            else:
                self.close()
                self.connect()
            raise
    
    def consume(self, queue_name: str, callback: MessageCallback, 
                auto_ack: bool = False, exclusive: bool = False) -> None:
        """Start consuming messages from a queue.
        
        Args:
            queue_name: Name of the queue to consume from
            callback: Callback function to handle messages
            auto_ack: Whether to automatically acknowledge messages
            exclusive: Whether to request exclusive consumer access
        """
        self.ensure_connection()
        
        try:
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=auto_ack,
                exclusive=exclusive
            )
            logger.info(f"Started consuming from queue: {queue_name}")
            self.channel.start_consuming()
        except (AMQPConnectionError, ConnectionClosedByBroker, StreamLostError) as e:
            logger.warning(f"Connection error while consuming messages: {str(e)}")
            self.close()
            raise RabbitMQConnectionError(f"Connection error while consuming messages: {str(e)}") from e
        except (AMQPChannelError, ChannelClosedByBroker) as e:
            logger.warning(f"Channel error while consuming messages: {str(e)}")
            if self.connection and self.connection.is_open:
                self.channel = self.connection.channel()
                self.channel.basic_qos(prefetch_count=self.prefetch_count)
            else:
                self.close()
            raise RabbitMQChannelError(f"Channel error while consuming messages: {str(e)}") from e
        except KeyboardInterrupt:
            logger.info("Stopping consumer due to keyboard interrupt")
            self.channel.stop_consuming()
            self.close()
    
    def consume_with_retry(self, queue_name: str, callback: MessageCallback,
                          auto_ack: bool = False, exclusive: bool = False,
                          max_retries: int = 5) -> None:
        """Consume messages with automatic reconnection on failure.
        
        Args:
            queue_name: Name of the queue to consume from
            callback: Callback function to handle messages
            auto_ack: Whether to automatically acknowledge messages
            exclusive: Whether to request exclusive consumer access
            max_retries: Maximum number of reconnection attempts
        """
        retries = 0
        
        while retries <= max_retries:
            try:
                self.consume(queue_name, callback, auto_ack, exclusive)
                # If we get here, consuming has stopped normally
                break
            except (RabbitMQConnectionError, RabbitMQChannelError) as e:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Failed to consume messages after {max_retries} retries: {str(e)}")
                    raise
                
                backoff_time = calculate_backoff(
                    attempt=retries - 1,
                    initial_backoff=1.0,
                    max_backoff=30.0,
                    backoff_factor=2.0,
                    jitter_factor=0.1
                )
                
                logger.warning(
                    f"Error consuming messages, retrying in {backoff_time:.2f}s "
                    f"(attempt {retries}/{max_retries}): {str(e)}"
                )
                
                time.sleep(backoff_time)
                self.connect()  # Ensure we have a fresh connection
    
    def get_message(self, queue_name: str, auto_ack: bool = False) -> Optional[Tuple[Basic.Deliver, BasicProperties, bytes]]:
        """Get a single message from a queue.
        
        Args:
            queue_name: Name of the queue to get a message from
            auto_ack: Whether to automatically acknowledge the message
            
        Returns:
            Optional[Tuple[Basic.Deliver, BasicProperties, bytes]]: Message tuple or None if no message is available
        """
        self.ensure_connection()
        
        try:
            method_frame, header_frame, body = self.channel.basic_get(queue=queue_name, auto_ack=auto_ack)
            if method_frame:
                logger.debug(f"Got message from queue {queue_name}")
                return method_frame, header_frame, body
            return None
        except (AMQPConnectionError, ConnectionClosedByBroker, StreamLostError) as e:
            logger.warning(f"Connection error while getting message: {str(e)}")
            self.close()
            self.connect()
            raise RabbitMQConnectionError(f"Connection error while getting message: {str(e)}") from e
        except (AMQPChannelError, ChannelClosedByBroker) as e:
            logger.warning(f"Channel error while getting message: {str(e)}")
            if self.connection and self.connection.is_open:
                self.channel = self.connection.channel()
                self.channel.basic_qos(prefetch_count=self.prefetch_count)
            else:
                self.close()
                self.connect()
            raise RabbitMQChannelError(f"Channel error while getting message: {str(e)}") from e
    
    def acknowledge(self, delivery_tag: int) -> None:
        """Acknowledge a message.
        
        Args:
            delivery_tag: Delivery tag of the message to acknowledge
        """
        if not self.channel or not self.channel.is_open:
            raise RabbitMQChannelError("Channel is not open")
        
        try:
            self.channel.basic_ack(delivery_tag=delivery_tag)
            logger.debug(f"Acknowledged message with delivery tag {delivery_tag}")
        except (AMQPChannelError, ChannelClosedByBroker) as e:
            logger.warning(f"Failed to acknowledge message: {str(e)}")
            raise RabbitMQChannelError(f"Failed to acknowledge message: {str(e)}") from e
    
    def reject(self, delivery_tag: int, requeue: bool = True) -> None:
        """Reject a message.
        
        Args:
            delivery_tag: Delivery tag of the message to reject
            requeue: Whether to requeue the message
        """
        if not self.channel or not self.channel.is_open:
            raise RabbitMQChannelError("Channel is not open")
        
        try:
            self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
            logger.debug(f"Rejected message with delivery tag {delivery_tag}, requeue={requeue}")
        except (AMQPChannelError, ChannelClosedByBroker) as e:
            logger.warning(f"Failed to reject message: {str(e)}")
            raise RabbitMQChannelError(f"Failed to reject message: {str(e)}") from e


# Utility functions for working with RabbitMQ messages

def serialize_message(message: Dict[str, Any]) -> bytes:
    """Serialize a message to JSON and encode as bytes.
    
    Args:
        message: Message dictionary to serialize
        
    Returns:
        bytes: Serialized message as bytes
    """
    return json.dumps(message).encode('utf-8')


def deserialize_message(message_body: bytes) -> Dict[str, Any]:
    """Deserialize a message from bytes to a dictionary.
    
    Args:
        message_body: Message body as bytes
        
    Returns:
        Dict[str, Any]: Deserialized message as a dictionary
    """
    return json.loads(message_body.decode('utf-8'))


def create_rabbitmq_client_from_env() -> RabbitMQClient:
    """Create a RabbitMQ client from environment variables.
    
    Returns:
        RabbitMQClient: Configured RabbitMQ client
    """
    host = os.environ.get('RABBITMQ_HOST', 'localhost')
    port = int(os.environ.get('RABBITMQ_PORT', '5672'))
    virtual_host = os.environ.get('RABBITMQ_VHOST', '/')
    username = os.environ.get('RABBITMQ_USERNAME', 'guest')
    password = os.environ.get('RABBITMQ_PASSWORD', 'guest')
    exchange = os.environ.get('RABBITMQ_EXCHANGE', DEFAULT_EXCHANGE)
    prefetch_count = int(os.environ.get('RABBITMQ_PREFETCH_COUNT', str(DEFAULT_PREFETCH_COUNT)))
    
    return RabbitMQClient(
        host=host,
        port=port,
        virtual_host=virtual_host,
        username=username,
        password=password,
        exchange=exchange,
        prefetch_count=prefetch_count
    )


def setup_ocr_queues(client: RabbitMQClient) -> None:
    """Set up the queues required for OCR processing.
    
    Args:
        client: RabbitMQ client to use for queue setup
    """
    # Declare OCR request queue
    client.declare_queue(
        queue_name=DEFAULT_OCR_REQUEST_QUEUE,
        durable=True,
        exclusive=False,
        auto_delete=False
    )
    
    # Bind OCR request queue to exchange
    client.bind_queue(
        queue_name=DEFAULT_OCR_REQUEST_QUEUE,
        routing_key='document.ocr.request'
    )
    
    # Declare processing queue for OCR results
    client.declare_queue(
        queue_name=DEFAULT_PROCESSING_QUEUE,
        durable=True,
        exclusive=False,
        auto_delete=False
    )
    
    # Bind processing queue to exchange
    client.bind_queue(
        queue_name=DEFAULT_PROCESSING_QUEUE,
        routing_key='document.ocr.result'
    )


# Example message handler function
def example_message_handler(channel: BlockingChannel, method: Basic.Deliver, 
                           properties: BasicProperties, body: bytes) -> None:
    """Example message handler function.
    
    Args:
        channel: RabbitMQ channel
        method: Message delivery information
        properties: Message properties
        body: Message body
    """
    try:
        # Deserialize message
        message = deserialize_message(body)
        logger.info(f"Received message: {message}")
        
        # Process message
        # ...
        
        # Acknowledge message
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        # Reject message and requeue
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=True)


# OCR-specific message handling functions

def create_ocr_result_message(document_id: str, extracted_data: Dict[str, Any], 
                             confidence_scores: Dict[str, float], 
                             processing_time_ms: int) -> Dict[str, Any]:
    """Create a message with OCR extraction results.
    
    Args:
        document_id: ID of the processed document
        extracted_data: Extracted data from the document
        confidence_scores: Confidence scores for extracted fields
        processing_time_ms: Processing time in milliseconds
        
    Returns:
        Dict[str, Any]: Formatted OCR result message
    """
    return {
        'document_id': document_id,
        'timestamp': int(time.time()),
        'extracted_data': extracted_data,
        'confidence_scores': confidence_scores,
        'processing_time_ms': processing_time_ms,
        'service': 'ocr-service',
        'status': 'completed'
    }


def publish_ocr_result(client: RabbitMQClient, document_id: str, 
                      extracted_data: Dict[str, Any], confidence_scores: Dict[str, float], 
                      processing_time_ms: int) -> bool:
    """Publish OCR extraction results to the processing queue.
    
    Args:
        client: RabbitMQ client to use for publishing
        document_id: ID of the processed document
        extracted_data: Extracted data from the document
        confidence_scores: Confidence scores for extracted fields
        processing_time_ms: Processing time in milliseconds
        
    Returns:
        bool: True if the message was published successfully
    """
    message = create_ocr_result_message(
        document_id=document_id,
        extracted_data=extracted_data,
        confidence_scores=confidence_scores,
        processing_time_ms=processing_time_ms
    )
    
    properties = pika.BasicProperties(
        delivery_mode=DEFAULT_DELIVERY_MODE,
        content_type='application/json',
        timestamp=int(time.time()),
        message_id=f"ocr-result-{document_id}-{int(time.time())}",
        headers={
            'document_id': document_id,
            'service': 'ocr-service'
        }
    )
    
    return client.publish(
        message=message,
        routing_key='document.ocr.result',
        properties=properties
    )


# Example usage

'''
# Example 1: Creating a RabbitMQ client and connecting
client = RabbitMQClient(
    host='localhost',
    port=5672,
    virtual_host='/',
    username='guest',
    password='guest',
    exchange='mca.documents',
    exchange_type='topic'
)

client.connect()

# Example 2: Setting up queues
setup_ocr_queues(client)

# Example 3: Publishing a message
client.publish(
    message={'document_id': '123', 'status': 'processed'},
    routing_key='document.ocr.result'
)

# Example 4: Consuming messages
client.consume(
    queue_name='ocr.request',
    callback=example_message_handler,
    auto_ack=False
)

# Example 5: Getting a single message
message = client.get_message(queue_name='ocr.request', auto_ack=False)
if message:
    method, properties, body = message
    # Process message
    client.acknowledge(method.delivery_tag)

# Example 6: Publishing OCR results
publish_ocr_result(
    client=client,
    document_id='123',
    extracted_data={'field1': 'value1', 'field2': 'value2'},
    confidence_scores={'field1': 0.95, 'field2': 0.87},
    processing_time_ms=1500
)

# Example 7: Closing the connection
client.close()
'''