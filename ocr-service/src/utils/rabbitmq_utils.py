#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RabbitMQ utilities for the OCR Service.

This module provides functions for connecting to RabbitMQ, publishing messages,
consuming messages, and handling message acknowledgments. It implements retry logic
for publishing messages and connection recovery for handling network failures.
"""

import json
import logging
import time
import uuid
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pika
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

from ..types.config import RabbitMQConfig
from ..types.messages import MessageHeaders, MessagePayload, PublishOptions
from ..utils.error_utils import create_error_context
from ..utils.logging_utils import get_logger

# Configure logger
logger = get_logger(__name__)


def with_connection_retry(max_retries: int = 5, initial_delay: float = 1.0,
                          max_delay: float = 30.0, backoff_factor: float = 2.0) -> Callable:
    """
    Decorator for functions that require a RabbitMQ connection, implementing retry logic
    with exponential backoff for connection failures.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor by which the delay increases with each retry
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay
            
            for retry in range(max_retries + 1):  # +1 to include the initial attempt
                try:
                    return func(*args, **kwargs)
                except (AMQPConnectionError, ConnectionClosedByBroker, AMQPChannelError) as e:
                    last_exception = e
                    if retry == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    logger.warning(f"Connection error on attempt {retry + 1}/{max_retries + 1}: {str(e)}. "
                                  f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            # This should never be reached due to the raise in the loop
            raise last_exception if last_exception else RuntimeError("Unexpected error in retry logic")
        
        return wrapper
    return decorator


class RabbitMQConnection:
    """
    Manages RabbitMQ connection and provides methods for publishing and consuming messages.
    Implements connection recovery and retry logic for handling network failures.
    """
    
    def __init__(self, config: RabbitMQConfig):
        """
        Initialize RabbitMQ connection manager with the provided configuration.
        
        Args:
            config: RabbitMQ connection configuration
        """
        self.config = config
        self.connection: Optional[BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        self.consuming = False
        self._initialize_connection_params()
    
    def _initialize_connection_params(self) -> None:
        """
        Initialize connection parameters based on configuration.
        Sets up SSL context if TLS is enabled.
        """
        credentials = pika.PlainCredentials(
            username=self.config.username,
            password=self.config.password
        )
        
        # Configure SSL parameters if TLS is enabled
        ssl_options = None
        if self.config.use_tls:
            ssl_options = pika.SSLOptions(
                context=self._create_ssl_context(),
                server_hostname=self.config.host
            )
        
        self.connection_params = pika.ConnectionParameters(
            host=self.config.host,
            port=self.config.port,
            virtual_host=self.config.virtual_host,
            credentials=credentials,
            ssl_options=ssl_options,
            connection_attempts=3,
            retry_delay=2,
            socket_timeout=5,
            heartbeat=60
        )
    
    def _create_ssl_context(self):
        """
        Create SSL context for TLS connections.
        
        Returns:
            SSL context configured with client certificates if provided
        """
        import ssl
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Load CA certificate
        if self.config.ca_cert:
            context.load_verify_locations(cafile=self.config.ca_cert)
        
        # Load client certificate and key if provided
        if self.config.client_cert and self.config.client_key:
            context.load_cert_chain(
                certfile=self.config.client_cert,
                keyfile=self.config.client_key
            )
        
        return context
    
    @with_connection_retry()
    def connect(self) -> None:
        """
        Establish connection to RabbitMQ server and create a channel.
        Implements retry logic for connection failures.
        
        Raises:
            AMQPConnectionError: If connection cannot be established after retries
        """
        if self.connection is not None and self.connection.is_open:
            logger.debug("Connection already established")
            return
        
        logger.info(f"Connecting to RabbitMQ at {self.config.host}:{self.config.port}")
        self.connection = pika.BlockingConnection(self.connection_params)
        self.channel = self.connection.channel()
        
        # Enable publisher confirms
        self.channel.confirm_delivery()
        
        logger.info("Successfully connected to RabbitMQ")
    
    def close(self) -> None:
        """
        Close the RabbitMQ channel and connection.
        """
        logger.info("Closing RabbitMQ connection")
        
        if self.channel is not None and self.channel.is_open:
            try:
                if self.consuming:
                    self.channel.stop_consuming()
                    self.consuming = False
                self.channel.close()
            except Exception as e:
                logger.warning(f"Error closing channel: {str(e)}")
            finally:
                self.channel = None
        
        if self.connection is not None and self.connection.is_open:
            try:
                self.connection.close()
            except Exception as e:
                logger.warning(f"Error closing connection: {str(e)}")
            finally:
                self.connection = None
    
    def reconnect(self) -> None:
        """
        Reconnect to RabbitMQ server after a connection failure.
        """
        logger.info("Reconnecting to RabbitMQ")
        self.close()
        self.connect()
    
    def ensure_connection(self) -> None:
        """
        Ensure that connection and channel are open, reconnecting if necessary.
        """
        if self.connection is None or not self.connection.is_open:
            self.connect()
            return
        
        if self.channel is None or not self.channel.is_open:
            self.channel = self.connection.channel()
            self.channel.confirm_delivery()
    
    @with_connection_retry()
    def declare_exchange(self, exchange: str, exchange_type: str = 'topic',
                         durable: bool = True) -> None:
        """
        Declare a RabbitMQ exchange.
        
        Args:
            exchange: Exchange name
            exchange_type: Exchange type (direct, topic, fanout, headers)
            durable: Whether the exchange should survive broker restarts
            
        Raises:
            AMQPChannelError: If exchange declaration fails
        """
        self.ensure_connection()
        self.channel.exchange_declare(
            exchange=exchange,
            exchange_type=exchange_type,
            durable=durable
        )
        logger.debug(f"Declared exchange '{exchange}' of type '{exchange_type}'")
    
    @with_connection_retry()
    def declare_queue(self, queue: str, durable: bool = True,
                      arguments: Optional[Dict[str, Any]] = None) -> None:
        """
        Declare a RabbitMQ queue.
        
        Args:
            queue: Queue name
            durable: Whether the queue should survive broker restarts
            arguments: Additional queue arguments
            
        Raises:
            AMQPChannelError: If queue declaration fails
        """
        self.ensure_connection()
        self.channel.queue_declare(
            queue=queue,
            durable=durable,
            arguments=arguments
        )
        logger.debug(f"Declared queue '{queue}'")
    
    @with_connection_retry()
    def bind_queue(self, queue: str, exchange: str, routing_key: str) -> None:
        """
        Bind a queue to an exchange with the specified routing key.
        
        Args:
            queue: Queue name
            exchange: Exchange name
            routing_key: Routing key for binding
            
        Raises:
            AMQPChannelError: If queue binding fails
        """
        self.ensure_connection()
        self.channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key
        )
        logger.debug(f"Bound queue '{queue}' to exchange '{exchange}' with routing key '{routing_key}'")
    
    @with_connection_retry(max_retries=3, initial_delay=0.5)
    def publish_message(self, exchange: str, routing_key: str, body: Union[Dict, str],
                        headers: Optional[Dict] = None, options: Optional[PublishOptions] = None) -> bool:
        """
        Publish a message to RabbitMQ with retry logic.
        
        Args:
            exchange: Exchange name
            routing_key: Routing key for message
            body: Message body (dict will be converted to JSON)
            headers: Message headers
            options: Additional publishing options
            
        Returns:
            True if message was published successfully, False otherwise
            
        Raises:
            AMQPConnectionError: If connection fails after retries
            AMQPChannelError: If channel operation fails after retries
        """
        self.ensure_connection()
        
        # Convert dict to JSON string if necessary
        if isinstance(body, dict):
            body = json.dumps(body)
        
        # Prepare message properties
        properties = pika.BasicProperties(
            delivery_mode=2,  # Persistent message
            content_type='application/json',
            headers=headers or {},
            message_id=str(uuid.uuid4()),
            timestamp=int(time.time()),
            app_id='ocr-service'
        )
        
        # Apply additional options if provided
        if options:
            if options.expiration:
                properties.expiration = str(options.expiration)
            if options.priority is not None:
                properties.priority = options.priority
            if options.correlation_id:
                properties.correlation_id = options.correlation_id
        
        try:
            # Publish with confirmation
            result = self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body.encode('utf-8') if isinstance(body, str) else body,
                properties=properties,
                mandatory=True
            )
            
            if result:
                logger.debug(f"Message published to exchange '{exchange}' with routing key '{routing_key}'")
            else:
                logger.warning(f"Failed to publish message to exchange '{exchange}' with routing key '{routing_key}'")
            
            return result
        except Exception as e:
            error_context = create_error_context(e, {
                'exchange': exchange,
                'routing_key': routing_key,
                'message_id': properties.message_id
            })
            logger.error(f"Error publishing message: {error_context}")
            raise
    
    def consume_messages(self, queue: str, callback: Callable[[BlockingChannel, spec.Basic.Deliver, spec.BasicProperties, bytes], None],
                         auto_ack: bool = False, prefetch_count: int = 1) -> None:
        """
        Start consuming messages from a queue.
        
        Args:
            queue: Queue name
            callback: Function to call when a message is received
            auto_ack: Whether to automatically acknowledge messages
            prefetch_count: Number of messages to prefetch
            
        Raises:
            AMQPConnectionError: If connection fails
            AMQPChannelError: If channel operation fails
        """
        self.ensure_connection()
        
        # Set QoS (prefetch count)
        self.channel.basic_qos(prefetch_count=prefetch_count)
        
        # Start consuming
        self.channel.basic_consume(
            queue=queue,
            on_message_callback=callback,
            auto_ack=auto_ack
        )
        
        logger.info(f"Started consuming from queue '{queue}'")
        self.consuming = True
        
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, stopping consumption")
            self.channel.stop_consuming()
            self.consuming = False
        except Exception as e:
            logger.error(f"Error during message consumption: {str(e)}")
            self.consuming = False
            raise
    
    def acknowledge_message(self, delivery_tag: int) -> None:
        """
        Acknowledge a message.
        
        Args:
            delivery_tag: Delivery tag of the message to acknowledge
        """
        if self.channel is not None and self.channel.is_open:
            self.channel.basic_ack(delivery_tag=delivery_tag)
            logger.debug(f"Acknowledged message with delivery tag {delivery_tag}")
    
    def reject_message(self, delivery_tag: int, requeue: bool = False) -> None:
        """
        Reject a message.
        
        Args:
            delivery_tag: Delivery tag of the message to reject
            requeue: Whether to requeue the message
        """
        if self.channel is not None and self.channel.is_open:
            self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
            logger.debug(f"Rejected message with delivery tag {delivery_tag}, requeue={requeue}")
    
    def nack_message(self, delivery_tag: int, multiple: bool = False, requeue: bool = False) -> None:
        """
        Negative acknowledgment of a message.
        
        Args:
            delivery_tag: Delivery tag of the message to nack
            multiple: Whether to nack all messages up to this delivery tag
            requeue: Whether to requeue the message(s)
        """
        if self.channel is not None and self.channel.is_open:
            self.channel.basic_nack(delivery_tag=delivery_tag, multiple=multiple, requeue=requeue)
            logger.debug(f"Nacked message with delivery tag {delivery_tag}, multiple={multiple}, requeue={requeue}")


def serialize_message(payload: MessagePayload, headers: Optional[MessageHeaders] = None) -> Tuple[str, Dict]:
    """
    Serialize a message payload and headers for publishing.
    
    Args:
        payload: Message payload
        headers: Message headers
        
    Returns:
        Tuple of (serialized payload, headers dict)
    """
    serialized_payload = json.dumps(payload)
    headers_dict = {}
    
    if headers:
        headers_dict = headers.dict()
    
    return serialized_payload, headers_dict


def deserialize_message(body: bytes, properties: spec.BasicProperties) -> Tuple[Dict, Dict]:
    """
    Deserialize a message body and headers.
    
    Args:
        body: Message body as bytes
        properties: Message properties
        
    Returns:
        Tuple of (deserialized payload, headers dict)
    """
    try:
        payload = json.loads(body.decode('utf-8'))
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode message body: {str(e)}")
        payload = {}
    
    headers = properties.headers or {}
    
    return payload, headers


def create_retry_policy(max_retries: int = 3, initial_delay: int = 1000,
                        backoff_factor: float = 2.0) -> Dict[str, Any]:
    """
    Create a retry policy for message publishing.
    
    Args:
        max_retries: Maximum number of retries
        initial_delay: Initial delay in milliseconds
        backoff_factor: Factor by which the delay increases with each retry
        
    Returns:
        Retry policy as a dict
    """
    return {
        'max_retries': max_retries,
        'initial_delay': initial_delay,
        'backoff_factor': backoff_factor
    }


def get_retry_delay(retry_count: int, initial_delay: int, backoff_factor: float) -> int:
    """
    Calculate the delay for a retry attempt using exponential backoff.
    
    Args:
        retry_count: Current retry attempt (0-based)
        initial_delay: Initial delay in milliseconds
        backoff_factor: Factor by which the delay increases with each retry
        
    Returns:
        Delay in milliseconds for the current retry attempt
    """
    return int(initial_delay * (backoff_factor ** retry_count))


def get_retry_count(headers: Dict) -> int:
    """
    Get the current retry count from message headers.
    
    Args:
        headers: Message headers
        
    Returns:
        Current retry count (0 if not present)
    """
    return headers.get('x-retry-count', 0)


def increment_retry_count(headers: Dict) -> Dict:
    """
    Increment the retry count in message headers.
    
    Args:
        headers: Message headers
        
    Returns:
        Updated headers with incremented retry count
    """
    headers['x-retry-count'] = get_retry_count(headers) + 1
    return headers