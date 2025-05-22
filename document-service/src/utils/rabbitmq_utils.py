"""
RabbitMQ Utilities for Document Service

This module provides utility functions for working with RabbitMQ in the Document Service.
It builds on top of the configuration in rabbitmq_config.py and provides simplified
interfaces for common RabbitMQ operations such as:

- Connection management with automatic reconnection
- Message publishing with retry logic
- Message consumption with error handling
- Message acknowledgment
- Message serialization and deserialization

These utilities are essential for the Document Service's integration with the
message queue system, enabling reliable communication with other microservices.
"""

import json
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Union, Tuple, NamedTuple
from contextlib import contextmanager

import pika
from pika.adapters.blocking_connection import BlockingConnection
from pika.channel import Channel
from pika.exceptions import (
    AMQPConnectionError,
    ConnectionClosed,
    ConnectionClosedByBroker,
    ConnectionBlockedTimeout,
    ChannelClosed,
    ChannelClosedByBroker
)

from ..config.rabbitmq_config import (
    EXCHANGE_NAME,
    QUEUE_NAME,
    DEAD_LETTER_EXCHANGE,
    DEAD_LETTER_QUEUE,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
    CONTENT_TYPE,
    DELIVERY_MODE,
    rabbitmq_client,
    get_rabbitmq_client,
    serialize_message,
    deserialize_message
)

# Configure logger
logger = logging.getLogger(__name__)


class PublishResult(NamedTuple):
    """Result of a message publish operation with retry information."""
    success: bool
    retry_count: int
    error: Optional[Exception] = None


@contextmanager
def rabbitmq_channel() -> Channel:
    """
    Context manager for obtaining and using a RabbitMQ channel.
    Automatically handles connection and channel setup/teardown.
    
    Yields:
        pika.channel.Channel: An open RabbitMQ channel
        
    Example:
        >>> with rabbitmq_channel() as channel:
        >>>     channel.basic_publish(...)
    """
    client = get_rabbitmq_client()
    
    # Ensure connection is established
    if client.connection is None or client.connection.is_closed:
        client.connect()
    
    # Create channel if needed
    if client.channel is None or client.channel.is_closed:
        client.channel = client.connection.channel()
    
    try:
        yield client.channel
    except (ConnectionClosed, ConnectionClosedByBroker) as e:
        logger.warning(f"Connection lost during channel operation: {str(e)}")
        # Force reconnection on next use
        client.connection = None
        client.channel = None
        raise
    except (ChannelClosed, ChannelClosedByBroker) as e:
        logger.warning(f"Channel closed during operation: {str(e)}")
        # Force channel recreation on next use
        client.channel = None
        raise


def publish_message_with_retry(
    message: Dict[str, Any],
    routing_key: str = '',
    exchange: str = EXCHANGE_NAME,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_RETRY_DELAY,
    max_delay: float = MAX_RETRY_DELAY
) -> PublishResult:
    """
    Publish a message to RabbitMQ with retry logic for handling temporary failures.
    
    Args:
        message: Dictionary containing message data to publish
        routing_key: Routing key to publish to (default is empty string for fanout exchange)
        exchange: Exchange to publish to (default is the main exchange)
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        
    Returns:
        PublishResult: Result of the publish operation
        
    Example:
        >>> result = publish_message_with_retry({
        >>>     'document_id': '12345',
        >>>     'classification': 'loan_application',
        >>>     'confidence': 0.95
        >>> })
        >>> if result.success:
        >>>     print(f"Message published successfully after {result.retry_count} retries")
        >>> else:
        >>>     print(f"Failed to publish message: {result.error}")
    """
    retry_count = 0
    retry_delay = initial_delay
    
    while retry_count <= max_retries:
        try:
            with rabbitmq_channel() as channel:
                # Serialize message
                body = serialize_message(message)
                
                # Publish message with persistent delivery mode
                channel.basic_publish(
                    exchange=exchange,
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
                
                logger.debug(f"Published message to exchange '{exchange}' with routing key '{routing_key}'")
                return PublishResult(success=True, retry_count=retry_count)
                
        except (ConnectionClosed, ConnectionClosedByBroker, ChannelClosed, ChannelClosedByBroker) as e:
            retry_count += 1
            
            if retry_count > max_retries:
                logger.error(f"Failed to publish message after {max_retries} attempts: {str(e)}")
                return PublishResult(success=False, retry_count=retry_count, error=e)
            
            logger.warning(f"Publish attempt {retry_count} failed: {str(e)}. Retrying in {retry_delay} seconds...")
            time.sleep(retry_delay)
            
            # Implement exponential backoff with a maximum delay
            retry_delay = min(retry_delay * 2, max_delay)
        
        except Exception as e:
            logger.error(f"Unexpected error publishing message: {str(e)}")
            return PublishResult(success=False, retry_count=retry_count, error=e)


def publish_to_ocr_service(
    document_id: str,
    document_type: str,
    s3_path: str,
    metadata: Dict[str, Any],
    confidence: float
) -> PublishResult:
    """
    Publish a document classification result to the OCR service for processing.
    
    Args:
        document_id: Unique identifier for the document
        document_type: Classified document type (e.g., 'loan_application', 'tax_return')
        s3_path: Path to the document in S3 storage
        metadata: Additional metadata about the document
        confidence: Classification confidence score (0.0 to 1.0)
        
    Returns:
        PublishResult: Result of the publish operation
        
    Example:
        >>> result = publish_to_ocr_service(
        >>>     document_id='doc-12345',
        >>>     document_type='loan_application',
        >>>     s3_path='mca-documents-production/doc-12345.pdf',
        >>>     metadata={'sender': 'example@example.com', 'received_at': '2023-05-01T12:00:00Z'},
        >>>     confidence=0.95
        >>> )
    """
    # Prepare message for OCR service
    message = {
        'document_id': document_id,
        'document_type': document_type,
        's3_path': s3_path,
        'metadata': metadata,
        'confidence': confidence,
        'classification_timestamp': int(time.time()),
        'service': 'document-service',
        'requires_review': confidence < 0.75  # Flag for human review if confidence is low
    }
    
    # Determine routing key based on document type
    routing_key = f"ocr.{document_type.lower().replace(' ', '_')}"
    
    # Publish message to OCR service
    logger.info(f"Publishing document {document_id} to OCR service with type {document_type}")
    return publish_message_with_retry(message, routing_key=routing_key)


class MessageHandler:
    """
    Base class for RabbitMQ message handlers with common functionality.
    
    This class provides a foundation for implementing message handlers with
    consistent error handling, acknowledgment, and retry logic.
    
    Example:
        >>> class DocumentHandler(MessageHandler):
        >>>     def process_message(self, message, delivery_info, properties):
        >>>         # Process document message
        >>>         document_id = message.get('document_id')
        >>>         print(f"Processing document {document_id}")
        >>>         return True  # Success
        >>> 
        >>> handler = DocumentHandler()
        >>> handler.start_consuming()
    """
    
    def __init__(self, queue_name: str = QUEUE_NAME, prefetch_count: int = 10):
        """
        Initialize the message handler.
        
        Args:
            queue_name: Name of the queue to consume from
            prefetch_count: Number of messages to prefetch
        """
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.should_stop = False
    
    def process_message(self, message: Dict[str, Any], delivery_info: pika.spec.Basic.Deliver, 
                        properties: pika.spec.BasicProperties) -> bool:
        """
        Process a message from the queue. Must be implemented by subclasses.
        
        Args:
            message: Deserialized message content
            delivery_info: Delivery information from RabbitMQ
            properties: Message properties
            
        Returns:
            bool: True if message was processed successfully, False otherwise
        """
        raise NotImplementedError("Subclasses must implement process_message")
    
    def handle_message(self, ch: Channel, method: pika.spec.Basic.Deliver, 
                      properties: pika.spec.BasicProperties, body: bytes) -> None:
        """
        Handle a message from the queue, including deserialization and error handling.
        
        Args:
            ch: RabbitMQ channel
            method: Delivery method
            properties: Message properties
            body: Raw message body
        """
        try:
            # Deserialize message
            message = deserialize_message(body)
            
            # Process message
            success = self.process_message(message, method, properties)
            
            if success:
                # Acknowledge message
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.debug(f"Message acknowledged: {method.delivery_tag}")
            else:
                # Negative acknowledge and requeue
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                logger.warning(f"Message processing failed, requeued: {method.delivery_tag}")
                
        except ValueError as e:
            # Deserialization error - reject without requeue
            logger.error(f"Message deserialization failed: {str(e)}")
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            # Unexpected error - log and requeue
            logger.error(f"Unexpected error processing message: {str(e)}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(self) -> None:
        """
        Start consuming messages from the queue with automatic reconnection.
        """
        self.should_stop = False
        retry_count = 0
        retry_delay = INITIAL_RETRY_DELAY
        
        while not self.should_stop:
            try:
                with rabbitmq_channel() as channel:
                    # Set QoS prefetch count
                    channel.basic_qos(prefetch_count=self.prefetch_count)
                    
                    # Start consuming
                    channel.basic_consume(
                        queue=self.queue_name,
                        on_message_callback=self.handle_message
                    )
                    
                    logger.info(f"Started consuming from queue '{self.queue_name}'")
                    
                    # Reset retry count on successful connection
                    retry_count = 0
                    retry_delay = INITIAL_RETRY_DELAY
                    
                    # Start consuming loop
                    channel.start_consuming()
                    
            except (ConnectionClosed, ConnectionClosedByBroker, ChannelClosed, ChannelClosedByBroker) as e:
                if self.should_stop:
                    logger.info("Stopping consumer as requested")
                    break
                    
                retry_count += 1
                logger.warning(f"Connection lost, retry attempt {retry_count}: {str(e)}")
                time.sleep(retry_delay)
                
                # Implement exponential backoff with a maximum delay
                retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
                
            except KeyboardInterrupt:
                logger.info("Stopping consumer due to keyboard interrupt")
                self.should_stop = True
                break
                
            except Exception as e:
                logger.error(f"Unexpected error in consumer: {str(e)}", exc_info=True)
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, MAX_RETRY_DELAY)
    
    def stop_consuming(self) -> None:
        """
        Signal the consumer to stop consuming messages.
        """
        self.should_stop = True
        logger.info("Consumer stop requested")


class DocumentMessageHandler(MessageHandler):
    """
    Handler for document messages from the Email Service.
    
    This class processes incoming document messages, classifies them using ML models,
    and routes them to the appropriate OCR service for further processing.
    
    Example:
        >>> handler = DocumentMessageHandler(document_classifier)
        >>> handler.start_consuming()
    """
    
    def __init__(self, document_classifier, storage_service, queue_name: str = QUEUE_NAME, prefetch_count: int = 10):
        """
        Initialize the document message handler.
        
        Args:
            document_classifier: Classifier for document type detection
            storage_service: Service for storing documents in S3
            queue_name: Name of the queue to consume from
            prefetch_count: Number of messages to prefetch
        """
        super().__init__(queue_name, prefetch_count)
        self.document_classifier = document_classifier
        self.storage_service = storage_service
    
    def process_message(self, message: Dict[str, Any], delivery_info: pika.spec.Basic.Deliver, 
                        properties: pika.spec.BasicProperties) -> bool:
        """
        Process a document message from the queue.
        
        Args:
            message: Deserialized message content
            delivery_info: Delivery information from RabbitMQ
            properties: Message properties
            
        Returns:
            bool: True if message was processed successfully, False otherwise
        """
        try:
            # Extract document information
            document_id = message.get('document_id')
            document_binary = message.get('document_binary')
            metadata = message.get('metadata', {})
            
            if not document_id or not document_binary:
                logger.error(f"Missing required fields in message: {message.keys()}")
                return False
            
            logger.info(f"Processing document {document_id}")
            
            # Store document in S3
            s3_path = self.storage_service.store_document(document_id, document_binary)
            
            # Classify document
            document_type, confidence = self.document_classifier.classify(document_binary)
            
            logger.info(f"Classified document {document_id} as {document_type} with confidence {confidence:.2f}")
            
            # Update metadata with classification results
            metadata.update({
                'classification': document_type,
                'confidence': confidence,
                'classified_at': int(time.time())
            })
            
            # Store metadata in S3
            self.storage_service.update_metadata(document_id, metadata)
            
            # Publish to OCR service
            result = publish_to_ocr_service(
                document_id=document_id,
                document_type=document_type,
                s3_path=s3_path,
                metadata=metadata,
                confidence=confidence
            )
            
            if not result.success:
                logger.error(f"Failed to publish document {document_id} to OCR service: {result.error}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing document message: {str(e)}", exc_info=True)
            return False


# Utility functions for simplified message acknowledgment

def ack_message(channel: Channel, delivery_tag: int) -> None:
    """
    Acknowledge a message with the given delivery tag.
    
    Args:
        channel: RabbitMQ channel
        delivery_tag: Message delivery tag
    """
    try:
        channel.basic_ack(delivery_tag=delivery_tag)
        logger.debug(f"Message acknowledged: {delivery_tag}")
    except (ConnectionClosed, ChannelClosed) as e:
        logger.error(f"Failed to acknowledge message {delivery_tag}: {str(e)}")
        raise


def nack_message(channel: Channel, delivery_tag: int, requeue: bool = True) -> None:
    """
    Negatively acknowledge a message with the given delivery tag.
    
    Args:
        channel: RabbitMQ channel
        delivery_tag: Message delivery tag
        requeue: Whether to requeue the message
    """
    try:
        channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
        logger.debug(f"Message negatively acknowledged: {delivery_tag}, requeue={requeue}")
    except (ConnectionClosed, ChannelClosed) as e:
        logger.error(f"Failed to negatively acknowledge message {delivery_tag}: {str(e)}")
        raise


def reject_message(channel: Channel, delivery_tag: int, requeue: bool = False) -> None:
    """
    Reject a message with the given delivery tag.
    
    Args:
        channel: RabbitMQ channel
        delivery_tag: Message delivery tag
        requeue: Whether to requeue the message
    """
    try:
        channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
        logger.debug(f"Message rejected: {delivery_tag}, requeue={requeue}")
    except (ConnectionClosed, ChannelClosed) as e:
        logger.error(f"Failed to reject message {delivery_tag}: {str(e)}")
        raise