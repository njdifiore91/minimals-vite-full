#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RabbitMQ message handling service for the OCR Service microservice.

This module provides functionality for connecting to RabbitMQ, consuming messages
from the 'ocr.request' queue, and publishing extraction results to downstream services.
It implements TLS with client certificate authentication, error handling with connection
recovery, and retry logic with exponential backoff for failed operations.

Key features:
1. Secure RabbitMQ connection with TLS and client certificate authentication
2. Message consumption from 'ocr.request' queue
3. Message publishing to 'data.processing' queue for Data Service
4. JSON serialization/deserialization for standardized message format
5. Error handling and connection recovery for RabbitMQ
6. Retry logic with exponential backoff for failed operations
"""

import json
import logging
import time
import uuid
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union, TypeVar, Generic

import pika
from pika import spec
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

from ..config.rabbitmq_config import (
    get_rabbitmq_config, get_connection_parameters, get_consumer_options,
    get_publisher_options, serialize_message, deserialize_message
)
from ..types.config import RabbitMQConfig
from ..types.messages import (
    MessagePayload, MessageHeaders, PublishOptions, ConsumeOptions,
    ExchangeConfig, QueueConfig, create_message_payload, MessageStatus
)
from ..utils.error_utils import create_error_context
from ..utils.logging_utils import get_logger
from ..utils.rabbitmq_utils import (
    RabbitMQConnection, with_connection_retry, serialize_message as utils_serialize_message,
    deserialize_message as utils_deserialize_message, create_retry_policy,
    get_retry_delay, get_retry_count, increment_retry_count
)

# Configure logger
logger = get_logger(__name__)

# Type variable for generic result handling
T = TypeVar('T')


class Result(Generic[T]):
    """Generic result class for operations that may fail.
    
    This class represents the result of an operation that may succeed or fail,
    providing access to the result value or error information.
    
    Attributes:
        value: The result value if successful
        error: Error information if failed
        success: Whether the operation was successful
    """
    
    def __init__(self, value: Optional[T] = None, error: Optional[Exception] = None):
        self.value = value
        self.error = error
        self.success = error is None
    
    @classmethod
    def ok(cls, value: T) -> 'Result[T]':
        """Create a successful result with the given value.
        
        Args:
            value: The result value
            
        Returns:
            Result: A successful result with the given value
        """
        return cls(value=value)
    
    @classmethod
    def err(cls, error: Exception) -> 'Result[T]':
        """Create a failed result with the given error.
        
        Args:
            error: The error that occurred
            
        Returns:
            Result: A failed result with the given error
        """
        return cls(error=error)
    
    def __bool__(self) -> bool:
        """Convert to boolean, returning True if successful.
        
        Returns:
            bool: True if successful, False if failed
        """
        return self.success


class QueueService:
    """RabbitMQ message handling service for the OCR Service.
    
    This class provides functionality for connecting to RabbitMQ, consuming messages
    from the 'ocr.request' queue, and publishing extraction results to the Data Service.
    It implements TLS with client certificate authentication, error handling with connection
    recovery, and retry logic with exponential backoff for failed operations.
    
    Attributes:
        config: RabbitMQ configuration
        connection: RabbitMQ connection manager
        callback: Callback function for processing messages
        running: Whether the service is running
    """
    
    def __init__(self, config: Optional[RabbitMQConfig] = None):
        """Initialize the QueueService with the given configuration.
        
        Args:
            config: RabbitMQ configuration (optional, loaded from environment if not provided)
        """
        self.config = config or get_rabbitmq_config()
        self.connection = RabbitMQConnection(self.config)
        self.callback: Optional[Callable] = None
        self.running = False
        
        logger.info("Initialized QueueService with RabbitMQ configuration")
    
    def start(self) -> Result[bool]:
        """Start the QueueService, connecting to RabbitMQ and setting up exchanges and queues.
        
        Returns:
            Result: Success or failure of the operation
        """
        try:
            logger.info("Starting QueueService")
            
            # Connect to RabbitMQ
            self.connection.connect()
            
            # Set up exchanges and queues
            self._setup_exchanges_and_queues()
            
            self.running = True
            logger.info("QueueService started successfully")
            return Result.ok(True)
        except Exception as e:
            logger.error(f"Failed to start QueueService: {str(e)}")
            return Result.err(e)
    
    def stop(self) -> Result[bool]:
        """Stop the QueueService, closing the RabbitMQ connection.
        
        Returns:
            Result: Success or failure of the operation
        """
        try:
            logger.info("Stopping QueueService")
            
            # Close the RabbitMQ connection
            self.connection.close()
            
            self.running = False
            logger.info("QueueService stopped successfully")
            return Result.ok(True)
        except Exception as e:
            logger.error(f"Failed to stop QueueService: {str(e)}")
            return Result.err(e)
    
    def _setup_exchanges_and_queues(self) -> None:
        """Set up exchanges and queues based on configuration.
        
        This method declares the exchanges and queues specified in the configuration,
        and binds the queues to the exchanges with the appropriate routing keys.
        """
        logger.info("Setting up exchanges and queues")
        
        # Declare exchanges
        for exchange_config in self.config.exchanges:
            self.connection.declare_exchange(
                exchange=exchange_config.name,
                exchange_type=exchange_config.exchange_type,
                durable=exchange_config.durable
            )
        
        # Declare queues and bind to exchanges
        for queue_config in self.config.queues:
            self.connection.declare_queue(
                queue=queue_config.name,
                durable=queue_config.durable,
                arguments=queue_config.arguments
            )
            
            # Bind queue to exchanges
            for binding in queue_config.bindings:
                self.connection.bind_queue(
                    queue=queue_config.name,
                    exchange=binding['exchange'],
                    routing_key=binding.get('routing_key', '')
                )
    
    def register_callback(self, callback: Callable) -> None:
        """Register a callback function for processing messages.
        
        The callback function should accept the following parameters:
        - channel: The RabbitMQ channel
        - method: The delivery method
        - properties: The message properties
        - body: The message body
        
        Args:
            callback: Callback function for processing messages
        """
        self.callback = callback
        logger.debug("Registered message processing callback")
    
    def _message_handler(self, channel: BlockingChannel, method: spec.Basic.Deliver,
                        properties: spec.BasicProperties, body: bytes) -> None:
        """Handle incoming messages from RabbitMQ.
        
        This method is called when a message is received from RabbitMQ. It deserializes
        the message, calls the registered callback function, and acknowledges or rejects
        the message based on the result.
        
        Args:
            channel: The RabbitMQ channel
            method: The delivery method
            properties: The message properties
            body: The message body
        """
        message_id = properties.message_id or "unknown"
        delivery_tag = method.delivery_tag
        
        logger.info(f"Received message {message_id} with delivery tag {delivery_tag}")
        
        try:
            # Deserialize the message
            payload, headers = utils_deserialize_message(body, properties)
            
            # Call the callback function if registered
            if self.callback:
                try:
                    self.callback(channel, method, properties, body, payload, headers)
                    
                    # Acknowledge the message
                    self.connection.acknowledge_message(delivery_tag)
                    logger.debug(f"Acknowledged message {message_id}")
                except Exception as e:
                    # Log the error
                    error_context = create_error_context(e, {
                        'message_id': message_id,
                        'delivery_tag': delivery_tag
                    })
                    logger.error(f"Error processing message: {error_context}")
                    
                    # Check if the message should be requeued
                    retry_count = get_retry_count(properties.headers or {})
                    max_retries = 3  # Maximum number of retries
                    
                    if retry_count < max_retries:
                        # Reject the message and requeue it
                        self.connection.reject_message(delivery_tag, requeue=True)
                        logger.warning(f"Requeued message {message_id} for retry (attempt {retry_count + 1})")
                    else:
                        # Reject the message without requeuing (send to dead-letter queue)
                        self.connection.reject_message(delivery_tag, requeue=False)
                        logger.warning(f"Rejected message {message_id} after {retry_count} retries")
            else:
                # No callback registered, acknowledge the message
                self.connection.acknowledge_message(delivery_tag)
                logger.warning(f"No callback registered, acknowledged message {message_id}")
        except Exception as e:
            # Error deserializing the message
            logger.error(f"Error deserializing message {message_id}: {str(e)}")
            
            # Reject the message without requeuing (send to dead-letter queue)
            self.connection.reject_message(delivery_tag, requeue=False)
            logger.warning(f"Rejected message {message_id} due to deserialization error")
    
    def consume_messages(self, queue: str = "ocr.request", auto_ack: bool = False,
                        prefetch_count: int = 10) -> Result[bool]:
        """Start consuming messages from the specified queue.
        
        This method starts consuming messages from the specified queue, calling the
        registered callback function for each message received. It implements error
        handling and connection recovery for RabbitMQ.
        
        Args:
            queue: Queue to consume from (default: 'ocr.request')
            auto_ack: Whether to automatically acknowledge messages (default: False)
            prefetch_count: Number of messages to prefetch (default: 10)
            
        Returns:
            Result: Success or failure of the operation
        """
        if not self.running:
            return Result.err(RuntimeError("QueueService not started"))
        
        if not self.callback:
            return Result.err(RuntimeError("No callback registered"))
        
        try:
            logger.info(f"Starting to consume messages from queue '{queue}'")
            
            # Ensure connection is established
            self.connection.ensure_connection()
            
            # Set QoS (prefetch count)
            self.connection.channel.basic_qos(prefetch_count=prefetch_count)
            
            # Start consuming
            self.connection.consume_messages(
                queue=queue,
                callback=self._message_handler,
                auto_ack=auto_ack,
                prefetch_count=prefetch_count
            )
            
            return Result.ok(True)
        except Exception as e:
            logger.error(f"Failed to consume messages from queue '{queue}': {str(e)}")
            return Result.err(e)
    
    @with_connection_retry(max_retries=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0)
    def publish_message(self, exchange: str, routing_key: str, payload: MessagePayload,
                       headers: Optional[Dict[str, Any]] = None,
                       options: Optional[PublishOptions] = None) -> Result[bool]:
        """Publish a message to RabbitMQ with retry logic.
        
        This method publishes a message to RabbitMQ with retry logic for handling
        connection failures. It serializes the message payload to JSON and applies
        the specified headers and options.
        
        Args:
            exchange: Exchange to publish to
            routing_key: Routing key for the message
            payload: Message payload
            headers: Message headers (optional)
            options: Publishing options (optional)
            
        Returns:
            Result: Success or failure of the operation
        """
        if not self.running:
            return Result.err(RuntimeError("QueueService not started"))
        
        try:
            logger.info(f"Publishing message to exchange '{exchange}' with routing key '{routing_key}'")
            
            # Ensure connection is established
            self.connection.ensure_connection()
            
            # Serialize the message payload
            serialized_payload, headers_dict = utils_serialize_message(payload, headers)
            
            # Publish the message
            result = self.connection.publish_message(
                exchange=exchange,
                routing_key=routing_key,
                body=serialized_payload,
                headers=headers_dict,
                options=options
            )
            
            if result:
                logger.debug(f"Successfully published message to exchange '{exchange}'")
                return Result.ok(True)
            else:
                logger.warning(f"Failed to publish message to exchange '{exchange}'")
                return Result.err(RuntimeError("Failed to publish message"))
        except Exception as e:
            logger.error(f"Error publishing message to exchange '{exchange}': {str(e)}")
            return Result.err(e)
    
    def publish_extraction_results(self, document_id: str, application_id: str,
                                 storage_path: str, extraction_results: Dict[str, Any],
                                 confidence_scores: Dict[str, float],
                                 document_type: str, processing_time_ms: float,
                                 requires_verification: bool = False,
                                 verification_fields: Optional[List[str]] = None) -> Result[bool]:
        """Publish extraction results to the Data Service.
        
        This method creates a standardized message payload with the extraction results
        and publishes it to the Data Service via RabbitMQ. It includes confidence scores,
        processing time, and verification flags.
        
        Args:
            document_id: ID of the document
            application_id: ID of the application
            storage_path: S3 storage path for the document
            extraction_results: OCR extraction results
            confidence_scores: Confidence scores for extracted fields
            document_type: Type of document
            processing_time_ms: Processing time in milliseconds
            requires_verification: Whether human verification is required
            verification_fields: Fields requiring verification
            
        Returns:
            Result: Success or failure of the operation
        """
        try:
            # Create the message payload
            payload = create_message_payload(
                document_id=document_id,
                document_type=document_type,
                application_id=application_id,
                storage_path=storage_path,
                content_type="application/json",
                source_service="ocr-service",
                status=MessageStatus.COMPLETED.value,
                extraction_results=extraction_results,
                confidence_scores=confidence_scores,
                processing_time_ms=processing_time_ms,
                requires_verification=requires_verification,
                verification_fields=verification_fields
            )
            
            # Create publish options
            options = PublishOptions.for_data_service(document_id)
            
            # Publish the message
            return self.publish_message(
                exchange="mca.data.processing",
                routing_key="data.extraction.complete",
                payload=payload,
                options=options
            )
        except Exception as e:
            logger.error(f"Error publishing extraction results for document {document_id}: {str(e)}")
            return Result.err(e)
    
    def publish_extraction_error(self, document_id: str, application_id: str,
                               storage_path: str, error: Dict[str, Any],
                               document_type: str) -> Result[bool]:
        """Publish extraction error to the Data Service.
        
        This method creates a standardized message payload with the extraction error
        and publishes it to the Data Service via RabbitMQ.
        
        Args:
            document_id: ID of the document
            application_id: ID of the application
            storage_path: S3 storage path for the document
            error: Error information
            document_type: Type of document
            
        Returns:
            Result: Success or failure of the operation
        """
        try:
            # Create the message payload
            payload = create_message_payload(
                document_id=document_id,
                document_type=document_type,
                application_id=application_id,
                storage_path=storage_path,
                content_type="application/json",
                source_service="ocr-service",
                status=MessageStatus.FAILED.value,
                error=error
            )
            
            # Create publish options
            options = PublishOptions.for_data_service(document_id, routing_key="data.extraction.error")
            
            # Publish the message
            return self.publish_message(
                exchange="mca.data.processing",
                routing_key="data.extraction.error",
                payload=payload,
                options=options
            )
        except Exception as e:
            logger.error(f"Error publishing extraction error for document {document_id}: {str(e)}")
            return Result.err(e)
    
    def is_running(self) -> bool:
        """Check if the QueueService is running.
        
        Returns:
            bool: True if the service is running, False otherwise
        """
        return self.running and self.connection.connection is not None and self.connection.connection.is_open
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a health check on the QueueService.
        
        This method checks the status of the RabbitMQ connection and returns
        a dictionary with health check information.
        
        Returns:
            Dict[str, Any]: Health check information
        """
        is_running = self.is_running()
        
        return {
            "status": "healthy" if is_running else "unhealthy",
            "details": {
                "running": self.running,
                "connected": is_running,
                "connection": {
                    "host": self.config.host,
                    "port": self.config.port,
                    "virtual_host": self.config.virtual_host
                }
            }
        }