#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Queue Service for OCR Service microservice.

This module provides functionality for connecting to RabbitMQ, consuming messages from the
'ocr.request' queue, and publishing extraction results to downstream services. It implements
TLS with client certificate authentication, error handling, connection recovery, and retry
logic with exponential backoff.
"""

import json
import logging
import ssl
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union, cast

import pika
from pika import credentials, connection, channel, spec
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection
from pika.exceptions import AMQPConnectionError, AMQPChannelError, AMQPError

from ..types.messages import MessagePayload, MessageHeaders, ExchangeConfig, QueueConfig, PublishOptions, ConsumeOptions
from ..types.errors import ServiceError, ErrorCategory, Result
from ..config import rabbitmq_config, app_config, logging_config

# Type variable for generic function return types
T = TypeVar('T')

# Configure logger
logger = logging.getLogger(__name__)


class QueueService:
    """
    Service for handling RabbitMQ message queue operations.
    
    This service provides functionality for connecting to RabbitMQ, consuming messages
    from the 'ocr.request' queue, and publishing extraction results to the Data Service.
    It implements TLS with client certificate authentication, error handling, connection
    recovery, and retry logic with exponential backoff.
    """
    
    def __init__(self):
        """
        Initialize the QueueService with RabbitMQ configuration.
        """
        self.config = rabbitmq_config
        self.connection: Optional[BlockingConnection] = None
        self.channel: Optional[BlockingChannel] = None
        self.connected = False
        self.consumer_tag: Optional[str] = None
        self.max_retries = self.config.max_retries
        self.retry_delay = self.config.retry_delay
        self.exchange_name = self.config.exchange_name
        self.exchange_type = self.config.exchange_type
        self.ocr_request_queue = self.config.ocr_request_queue
        self.data_processing_queue = self.config.data_processing_queue
        
        # Initialize connection
        self._initialize_connection()
    
    def _initialize_connection(self) -> None:
        """
        Initialize the RabbitMQ connection with TLS and client certificate authentication.
        """
        try:
            # Set up SSL context for TLS
            ssl_context = ssl.create_default_context(cafile=self.config.ca_cert_path)
            ssl_context.load_cert_chain(
                certfile=self.config.client_cert_path,
                keyfile=self.config.client_key_path,
                password=self.config.cert_password
            )
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = True
            
            # Set up credentials
            credentials_obj = credentials.ExternalCredentials() if self.config.use_cert_auth else \
                credentials.PlainCredentials(self.config.username, self.config.password)
            
            # Set up connection parameters with TLS
            conn_params = pika.ConnectionParameters(
                host=self.config.host,
                port=self.config.port,
                virtual_host=self.config.virtual_host,
                credentials=credentials_obj,
                ssl_options=pika.SSLOptions(context=ssl_context),
                heartbeat=self.config.heartbeat,
                blocked_connection_timeout=self.config.connection_timeout,
                retry_delay=self.config.retry_delay,
                connection_attempts=self.config.connection_attempts
            )
            
            # Establish connection
            self.connection = pika.BlockingConnection(conn_params)
            self.channel = self.connection.channel()
            
            # Declare exchange
            self.channel.exchange_declare(
                exchange=self.exchange_name,
                exchange_type=self.exchange_type,
                durable=True
            )
            
            # Declare queues
            self.channel.queue_declare(
                queue=self.ocr_request_queue,
                durable=True
            )
            
            self.channel.queue_declare(
                queue=self.data_processing_queue,
                durable=True
            )
            
            # Bind queues to exchange
            self.channel.queue_bind(
                queue=self.ocr_request_queue,
                exchange=self.exchange_name,
                routing_key='ocr.request'
            )
            
            self.channel.queue_bind(
                queue=self.data_processing_queue,
                exchange=self.exchange_name,
                routing_key='data.processing'
            )
            
            # Set QoS prefetch count
            self.channel.basic_qos(prefetch_count=self.config.prefetch_count)
            
            self.connected = True
            logger.info(f"Successfully connected to RabbitMQ at {self.config.host}:{self.config.port}")
            
        except (AMQPConnectionError, AMQPChannelError, AMQPError) as e:
            logger.error(f"Failed to initialize RabbitMQ connection: {str(e)}")
            self.connected = False
            raise ServiceError(
                message=f"Failed to initialize RabbitMQ connection: {str(e)}",
                category=ErrorCategory.CONNECTION,
                details={"host": self.config.host, "port": self.config.port}
            )
    
    def with_connection(func: Callable) -> Callable:
        """
        Decorator to ensure a valid RabbitMQ connection before executing a function.
        Implements connection recovery if the connection is lost.
        
        Args:
            func: The function to wrap with connection handling.
            
        Returns:
            The wrapped function with connection handling.
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if not self.connected or not self.connection or self.connection.is_closed or \
               not self.channel or self.channel.is_closed:
                logger.warning("RabbitMQ connection is not established or was closed. Attempting to reconnect...")
                try:
                    self._initialize_connection()
                except ServiceError as e:
                    logger.error(f"Failed to reconnect to RabbitMQ: {str(e)}")
                    raise
            
            try:
                return func(self, *args, **kwargs)
            except (AMQPConnectionError, AMQPChannelError, AMQPError) as e:
                logger.error(f"RabbitMQ operation failed: {str(e)}")
                self.connected = False
                raise ServiceError(
                    message=f"RabbitMQ operation failed: {str(e)}",
                    category=ErrorCategory.CONNECTION,
                    details={"function": func.__name__, "args": args, "kwargs": kwargs}
                )
        
        return wrapper
    
    def with_retry(func: Callable[..., Result[T]]) -> Callable[..., Result[T]]:
        """
        Decorator to implement retry logic with exponential backoff for RabbitMQ operations.
        
        Args:
            func: The function to wrap with retry logic.
            
        Returns:
            The wrapped function with retry logic.
        """
        @wraps(func)
        def wrapper(self, *args, **kwargs) -> Result[T]:
            retries = 0
            last_error = None
            
            while retries <= self.max_retries:
                try:
                    result = func(self, *args, **kwargs)
                    if result.success:
                        if retries > 0:
                            logger.info(f"Operation succeeded after {retries} retries")
                        return result
                    else:
                        last_error = result.error
                except ServiceError as e:
                    last_error = e
                
                retries += 1
                if retries <= self.max_retries:
                    # Calculate exponential backoff with jitter
                    delay = min(self.config.max_delay, self.retry_delay * (2 ** (retries - 1)))
                    logger.warning(f"Retrying operation after {delay:.2f}s (attempt {retries}/{self.max_retries})")
                    time.sleep(delay)
            
            logger.error(f"Operation failed after {self.max_retries} retries: {str(last_error)}")
            return Result(success=False, error=last_error)
        
        return wrapper
    
    @with_connection
    @with_retry
    def publish_message(self, payload: MessagePayload, routing_key: str, 
                       headers: Optional[MessageHeaders] = None,
                       options: Optional[PublishOptions] = None) -> Result[bool]:
        """
        Publish a message to the RabbitMQ exchange with the specified routing key.
        
        Args:
            payload: The message payload to publish.
            routing_key: The routing key for the message.
            headers: Optional headers for the message.
            options: Optional publishing options.
            
        Returns:
            Result indicating success or failure of the operation.
        """
        try:
            if not self.channel:
                return Result(success=False, error=ServiceError(
                    message="Channel not initialized",
                    category=ErrorCategory.CONNECTION
                ))
            
            # Serialize payload to JSON
            message_body = json.dumps(payload).encode('utf-8')
            
            # Set up message properties
            properties = pika.BasicProperties(
                delivery_mode=2,  # Make message persistent
                content_type='application/json',
                content_encoding='utf-8',
                headers=headers or {},
                app_id=app_config.service_name,
                timestamp=int(time.time()),
                message_id=payload.get('id', ''),
                correlation_id=payload.get('correlation_id', ''),
                **({} if not options else options)
            )
            
            # Publish message
            self.channel.basic_publish(
                exchange=self.exchange_name,
                routing_key=routing_key,
                body=message_body,
                properties=properties
            )
            
            logger.info(f"Published message to exchange '{self.exchange_name}' with routing key '{routing_key}'")
            return Result(success=True, data=True)
            
        except (AMQPConnectionError, AMQPChannelError, AMQPError) as e:
            logger.error(f"Failed to publish message: {str(e)}")
            return Result(success=False, error=ServiceError(
                message=f"Failed to publish message: {str(e)}",
                category=ErrorCategory.MESSAGING,
                details={"exchange": self.exchange_name, "routing_key": routing_key}
            ))
        except Exception as e:
            logger.error(f"Unexpected error publishing message: {str(e)}")
            return Result(success=False, error=ServiceError(
                message=f"Unexpected error publishing message: {str(e)}",
                category=ErrorCategory.UNKNOWN,
                details={"exchange": self.exchange_name, "routing_key": routing_key}
            ))
    
    @with_connection
    def start_consuming(self, callback: Callable[[MessagePayload, MessageHeaders, BlockingChannel, spec.Basic.Deliver], None],
                      options: Optional[ConsumeOptions] = None) -> None:
        """
        Start consuming messages from the OCR request queue.
        
        Args:
            callback: The callback function to process received messages.
            options: Optional consumption options.
        """
        if not self.channel:
            raise ServiceError(
                message="Channel not initialized",
                category=ErrorCategory.CONNECTION
            )
        
        def _message_handler(ch: BlockingChannel, method: spec.Basic.Deliver, 
                           properties: spec.BasicProperties, body: bytes) -> None:
            """
            Internal message handler that deserializes the message and calls the user callback.
            
            Args:
                ch: The channel object.
                method: The delivery method.
                properties: The message properties.
                body: The message body.
            """
            try:
                # Deserialize message body
                payload = json.loads(body.decode('utf-8'))
                headers = properties.headers or {}
                
                # Log message receipt
                logger.info(f"Received message from queue '{self.ocr_request_queue}' with routing key '{method.routing_key}'")
                
                # Call user callback
                callback(payload, headers, ch, method)
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode message: {str(e)}")
                # Reject the message without requeue if it's not valid JSON
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                # Reject the message with requeue to try again later
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
        
        # Start consuming from the queue
        self.consumer_tag = self.channel.basic_consume(
            queue=self.ocr_request_queue,
            on_message_callback=_message_handler,
            auto_ack=False  # Manual acknowledgment
        )
        
        logger.info(f"Started consuming messages from queue '{self.ocr_request_queue}'")
        
        try:
            # Start consuming loop
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Stopping consumer due to keyboard interrupt")
            self.stop_consuming()
        except Exception as e:
            logger.error(f"Error in consumer: {str(e)}")
            self.stop_consuming()
            raise ServiceError(
                message=f"Error in consumer: {str(e)}",
                category=ErrorCategory.MESSAGING
            )
    
    @with_connection
    def stop_consuming(self) -> None:
        """
        Stop consuming messages from the queue.
        """
        if self.channel and self.consumer_tag:
            try:
                self.channel.basic_cancel(self.consumer_tag)
                logger.info("Stopped consuming messages")
            except (AMQPConnectionError, AMQPChannelError, AMQPError) as e:
                logger.error(f"Error stopping consumer: {str(e)}")
            finally:
                self.consumer_tag = None
    
    @with_connection
    def acknowledge_message(self, delivery_tag: int) -> None:
        """
        Acknowledge a message as successfully processed.
        
        Args:
            delivery_tag: The delivery tag of the message to acknowledge.
        """
        if self.channel:
            self.channel.basic_ack(delivery_tag=delivery_tag)
            logger.debug(f"Acknowledged message with delivery tag {delivery_tag}")
    
    @with_connection
    def reject_message(self, delivery_tag: int, requeue: bool = False) -> None:
        """
        Reject a message as failed to process.
        
        Args:
            delivery_tag: The delivery tag of the message to reject.
            requeue: Whether to requeue the message for later processing.
        """
        if self.channel:
            self.channel.basic_reject(delivery_tag=delivery_tag, requeue=requeue)
            logger.debug(f"Rejected message with delivery tag {delivery_tag}, requeue={requeue}")
    
    def close(self) -> None:
        """
        Close the RabbitMQ connection and channel.
        """
        if self.consumer_tag:
            self.stop_consuming()
        
        if self.channel and not self.channel.is_closed:
            try:
                self.channel.close()
                logger.debug("Closed RabbitMQ channel")
            except Exception as e:
                logger.warning(f"Error closing channel: {str(e)}")
        
        if self.connection and not self.connection.is_closed:
            try:
                self.connection.close()
                logger.info("Closed RabbitMQ connection")
            except Exception as e:
                logger.warning(f"Error closing connection: {str(e)}")
        
        self.connected = False
        self.channel = None
        self.connection = None
    
    def __enter__(self):
        """
        Context manager entry point.
        
        Returns:
            The QueueService instance.
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit point.
        
        Args:
            exc_type: The exception type, if any.
            exc_val: The exception value, if any.
            exc_tb: The exception traceback, if any.
        """
        self.close()


# Example usage
def example_callback(payload: MessagePayload, headers: MessageHeaders, 
                    channel: BlockingChannel, method: spec.Basic.Deliver) -> None:
    """
    Example callback function for processing OCR request messages.
    
    Args:
        payload: The message payload.
        headers: The message headers.
        channel: The RabbitMQ channel.
        method: The delivery method.
    """
    try:
        # Process the message
        document_id = payload.get('document_id')
        document_type = payload.get('document_type')
        s3_path = payload.get('s3_path')
        
        logger.info(f"Processing document {document_id} of type {document_type} from {s3_path}")
        
        # TODO: Implement OCR processing logic
        
        # Acknowledge the message as processed
        channel.basic_ack(delivery_tag=method.delivery_tag)
        
        # Prepare result message for Data Service
        result_payload = {
            'document_id': document_id,
            'document_type': document_type,
            's3_path': s3_path,
            'extraction_results': {
                'fields': [],
                'confidence': 0.95,
                'processing_time': 1.5
            },
            'correlation_id': payload.get('correlation_id', ''),
            'timestamp': time.time()
        }
        
        # Create queue service instance
        queue_service = QueueService()
        
        # Publish result to Data Service
        result = queue_service.publish_message(
            payload=result_payload,
            routing_key='data.processing',
            headers={'source': 'ocr-service'}
        )
        
        if not result.success:
            logger.error(f"Failed to publish result: {result.error}")
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        # Reject the message with requeue
        channel.basic_reject(delivery_tag=method.delivery_tag, requeue=True)


# Main entry point for testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create queue service
    queue_service = QueueService()
    
    try:
        # Start consuming messages
        queue_service.start_consuming(example_callback)
    except KeyboardInterrupt:
        print("Interrupted by user, shutting down...")
    finally:
        # Close connection
        queue_service.close()