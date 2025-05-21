#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
RabbitMQ utilities for the Document Service.

This module provides functions for connecting to RabbitMQ, publishing messages,
consuming messages, and handling message acknowledgments. It's essential for the
service's integration with the message queue system.
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

import pika
from pika.adapters.blocking_connection import BlockingChannel
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

# Import configuration
from config import rabbitmq_config, logging_config

# Configure logger
logger = logging.getLogger(__name__)


def serialize_message(message: Dict[str, Any]) -> bytes:
    """
    Serialize a message to JSON and encode as bytes.
    
    Args:
        message: Dictionary containing the message data
        
    Returns:
        Serialized message as bytes
    """
    try:
        return json.dumps(message).encode('utf-8')
    except (TypeError, ValueError) as e:
        logger.error(f"Failed to serialize message: {e}")
        raise


def deserialize_message(message: bytes) -> Dict[str, Any]:
    """
    Deserialize a message from bytes to a dictionary.
    
    Args:
        message: Serialized message as bytes
        
    Returns:
        Deserialized message as dictionary
    """
    try:
        return json.loads(message.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to deserialize message: {e}")
        raise


def create_connection(max_retries: int = 5, retry_delay: int = 2) -> pika.BlockingConnection:
    """
    Create a connection to RabbitMQ with retry logic.
    
    Args:
        max_retries: Maximum number of connection attempts
        retry_delay: Delay between retries in seconds
        
    Returns:
        A BlockingConnection to RabbitMQ
        
    Raises:
        AMQPConnectionError: If connection cannot be established after retries
    """
    connection_params = pika.ConnectionParameters(
        host=rabbitmq_config.HOST,
        port=rabbitmq_config.PORT,
        virtual_host=rabbitmq_config.VIRTUAL_HOST,
        credentials=pika.PlainCredentials(
            username=rabbitmq_config.USERNAME,
            password=rabbitmq_config.PASSWORD
        ),
        heartbeat=rabbitmq_config.HEARTBEAT,
        connection_attempts=rabbitmq_config.CONNECTION_ATTEMPTS,
        retry_delay=rabbitmq_config.RETRY_DELAY,
        ssl_options=rabbitmq_config.SSL_OPTIONS if rabbitmq_config.USE_SSL else None,
        client_properties={'connection_name': 'document-service'}
    )
    
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            logger.info(f"Attempting to connect to RabbitMQ at {rabbitmq_config.HOST}:{rabbitmq_config.PORT}")
            connection = pika.BlockingConnection(connection_params)
            logger.info("Successfully connected to RabbitMQ")
            return connection
        except AMQPConnectionError as e:
            retry_count += 1
            last_exception = e
            logger.warning(f"Failed to connect to RabbitMQ (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    logger.error(f"Failed to connect to RabbitMQ after {max_retries} attempts")
    raise last_exception or AMQPConnectionError("Failed to connect to RabbitMQ")


def create_channel(connection: pika.BlockingConnection) -> BlockingChannel:
    """
    Create a channel from a RabbitMQ connection.
    
    Args:
        connection: A BlockingConnection to RabbitMQ
        
    Returns:
        A BlockingChannel for publishing and consuming messages
        
    Raises:
        AMQPChannelError: If channel cannot be created
    """
    try:
        channel = connection.channel()
        logger.info("Successfully created RabbitMQ channel")
        return channel
    except AMQPChannelError as e:
        logger.error(f"Failed to create RabbitMQ channel: {e}")
        raise


def setup_exchange(channel: BlockingChannel, exchange_name: str, exchange_type: str = 'fanout') -> None:
    """
    Declare an exchange on the RabbitMQ server.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        exchange_name: Name of the exchange to declare
        exchange_type: Type of exchange (direct, fanout, topic, headers)
        
    Raises:
        AMQPChannelError: If exchange cannot be declared
    """
    try:
        channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=True
        )
        logger.info(f"Declared exchange '{exchange_name}' of type '{exchange_type}'")
    except AMQPChannelError as e:
        logger.error(f"Failed to declare exchange '{exchange_name}': {e}")
        raise


def setup_queue(channel: BlockingChannel, queue_name: str) -> None:
    """
    Declare a queue on the RabbitMQ server.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        queue_name: Name of the queue to declare
        
    Returns:
        Queue declaration result
        
    Raises:
        AMQPChannelError: If queue cannot be declared
    """
    try:
        result = channel.queue_declare(
            queue=queue_name,
            durable=True
        )
        logger.info(f"Declared queue '{queue_name}'")
        return result
    except AMQPChannelError as e:
        logger.error(f"Failed to declare queue '{queue_name}': {e}")
        raise


def bind_queue(channel: BlockingChannel, queue_name: str, exchange_name: str, routing_key: str = '') -> None:
    """
    Bind a queue to an exchange with a routing key.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        queue_name: Name of the queue to bind
        exchange_name: Name of the exchange to bind to
        routing_key: Routing key for the binding
        
    Raises:
        AMQPChannelError: If queue cannot be bound to exchange
    """
    try:
        channel.queue_bind(
            queue=queue_name,
            exchange=exchange_name,
            routing_key=routing_key
        )
        logger.info(f"Bound queue '{queue_name}' to exchange '{exchange_name}' with routing key '{routing_key}'")
    except AMQPChannelError as e:
        logger.error(f"Failed to bind queue '{queue_name}' to exchange '{exchange_name}': {e}")
        raise


def publish_message(
    channel: BlockingChannel,
    exchange: str,
    routing_key: str,
    message: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: int = 1,
    properties: Optional[pika.BasicProperties] = None
) -> bool:
    """
    Publish a message to RabbitMQ with retry logic.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        exchange: Name of the exchange to publish to
        routing_key: Routing key for the message
        message: Dictionary containing the message data
        max_retries: Maximum number of publish attempts
        retry_delay: Delay between retries in seconds
        properties: Message properties
        
    Returns:
        True if message was published successfully, False otherwise
        
    Raises:
        AMQPConnectionError: If connection is lost and cannot be re-established
    """
    if properties is None:
        properties = pika.BasicProperties(
            delivery_mode=2,  # Make message persistent
            content_type='application/json'
        )
    
    serialized_message = serialize_message(message)
    retry_count = 0
    last_exception = None
    
    while retry_count < max_retries:
        try:
            channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=serialized_message,
                properties=properties
            )
            logger.info(f"Published message to exchange '{exchange}' with routing key '{routing_key}'")
            return True
        except (AMQPConnectionError, AMQPChannelError) as e:
            retry_count += 1
            last_exception = e
            logger.warning(f"Failed to publish message (attempt {retry_count}/{max_retries}): {e}")
            if retry_count < max_retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
    
    logger.error(f"Failed to publish message after {max_retries} attempts: {last_exception}")
    return False


def consume_messages(
    channel: BlockingChannel,
    queue: str,
    callback: Callable[[Dict[str, Any], BlockingChannel, pika.spec.Basic.Deliver, pika.BasicProperties], None],
    auto_ack: bool = False
) -> None:
    """
    Start consuming messages from a queue.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        queue: Name of the queue to consume from
        callback: Function to call when a message is received
        auto_ack: Whether to automatically acknowledge messages
        
    Raises:
        AMQPChannelError: If consumption cannot be started
    """
    def wrapper_callback(ch, method, properties, body):
        try:
            message = deserialize_message(body)
            callback(message, ch, method, properties)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            if not auto_ack:
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    try:
        channel.basic_qos(prefetch_count=rabbitmq_config.PREFETCH_COUNT)
        channel.basic_consume(
            queue=queue,
            on_message_callback=wrapper_callback,
            auto_ack=auto_ack
        )
        logger.info(f"Started consuming messages from queue '{queue}'")
        channel.start_consuming()
    except (AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker) as e:
        logger.error(f"Error consuming messages: {e}")
        raise


def acknowledge_message(channel: BlockingChannel, delivery_tag: int) -> None:
    """
    Acknowledge a message.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        delivery_tag: Delivery tag of the message to acknowledge
        
    Raises:
        AMQPChannelError: If message cannot be acknowledged
    """
    try:
        channel.basic_ack(delivery_tag=delivery_tag)
        logger.debug(f"Acknowledged message with delivery tag {delivery_tag}")
    except AMQPChannelError as e:
        logger.error(f"Failed to acknowledge message with delivery tag {delivery_tag}: {e}")
        raise


def reject_message(channel: BlockingChannel, delivery_tag: int, requeue: bool = True) -> None:
    """
    Reject a message.
    
    Args:
        channel: A BlockingChannel for publishing and consuming messages
        delivery_tag: Delivery tag of the message to reject
        requeue: Whether to requeue the message
        
    Raises:
        AMQPChannelError: If message cannot be rejected
    """
    try:
        channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
        logger.debug(f"Rejected message with delivery tag {delivery_tag}, requeue={requeue}")
    except AMQPChannelError as e:
        logger.error(f"Failed to reject message with delivery tag {delivery_tag}: {e}")
        raise


def close_channel(channel: BlockingChannel) -> None:
    """
    Close a RabbitMQ channel.
    
    Args:
        channel: A BlockingChannel to close
    """
    try:
        if channel.is_open:
            channel.close()
            logger.info("Closed RabbitMQ channel")
    except Exception as e:
        logger.warning(f"Error closing RabbitMQ channel: {e}")


def close_connection(connection: pika.BlockingConnection) -> None:
    """
    Close a RabbitMQ connection.
    
    Args:
        connection: A BlockingConnection to close
    """
    try:
        if connection.is_open:
            connection.close()
            logger.info("Closed RabbitMQ connection")
    except Exception as e:
        logger.warning(f"Error closing RabbitMQ connection: {e}")


def with_rabbitmq_connection(func):
    """
    Decorator to handle RabbitMQ connection creation and cleanup.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that handles RabbitMQ connection
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        connection = None
        try:
            connection = create_connection()
            return func(connection, *args, **kwargs)
        finally:
            if connection:
                close_connection(connection)
    return wrapper


def with_rabbitmq_channel(func):
    """
    Decorator to handle RabbitMQ channel creation and cleanup.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that handles RabbitMQ channel
    """
    @wraps(func)
    def wrapper(connection, *args, **kwargs):
        channel = None
        try:
            channel = create_channel(connection)
            return func(channel, *args, **kwargs)
        finally:
            if channel:
                close_channel(channel)
    return wrapper


def with_rabbitmq(func):
    """
    Decorator to handle both RabbitMQ connection and channel creation and cleanup.
    
    Args:
        func: Function to wrap
        
    Returns:
        Wrapped function that handles RabbitMQ connection and channel
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        connection = None
        channel = None
        try:
            connection = create_connection()
            channel = create_channel(connection)
            return func(channel, *args, **kwargs)
        finally:
            if channel:
                close_channel(channel)
            if connection:
                close_connection(connection)
    return wrapper