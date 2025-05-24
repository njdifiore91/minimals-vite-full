#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RabbitMQ message handling service for the Document Service microservice.

This module provides functionality for connecting to RabbitMQ, consuming messages
from the 'document-processing' queue, and publishing classification results to
downstream services. It serves as the messaging interface for the Document Service.

The service handles:
- Secure connection to RabbitMQ with TLS and client certificate authentication
- Consumption of document messages from the Email Service
- Publishing of classification results to the OCR Service
- Error handling and connection recovery
- Standardized message format validation and transformation
"""

import logging
import time
import uuid
from typing import Dict, Any, Callable, Optional, List, Union

# Import configuration
from config.rabbitmq_config import (
    rabbitmq_client, get_rabbitmq_client, consume_messages,
    deserialize_message, serialize_message, EXCHANGE_NAME
)

# Configure logger
logger = logging.getLogger(__name__)


class QueueService:
    """
    Service for handling RabbitMQ message queue operations.
    
    This service provides high-level methods for consuming messages from the
    document-processing queue and publishing classification results to the
    data-extraction queue for OCR processing.
    """
    
    def __init__(self):
        """
        Initialize the QueueService with a RabbitMQ client.
        """
        self.client = get_rabbitmq_client()
        self.processing_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
    
    def register_document_handler(self, handler: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a handler function for processing document messages.
        
        Args:
            handler: Function that processes document messages. Should accept a message
                    dictionary as its argument.
        """
        self.processing_handlers['document_processing'] = handler
        logger.info("Document processing handler registered")
    
    def start_consuming(self) -> None:
        """
        Start consuming messages from the document-processing queue.
        
        This method starts a blocking consumer that processes messages using the
        registered document handler. It automatically handles reconnection and
        error recovery.
        
        Raises:
            RuntimeError: If no document handler is registered
        """
        if 'document_processing' not in self.processing_handlers:
            raise RuntimeError("No document processing handler registered")
        
        logger.info("Starting to consume messages from document-processing queue")
        
        def message_callback(message: Dict[str, Any], method: Any, properties: Any) -> None:
            """
            Process incoming messages and route to appropriate handler.
            
            Args:
                message: Deserialized message content
                method: RabbitMQ delivery information
                properties: RabbitMQ message properties
            """
            try:
                # Log message receipt
                correlation_id = properties.correlation_id or str(uuid.uuid4())
                logger.info(f"Received message with correlation ID: {correlation_id}")
                
                # Validate message format
                if not self._validate_message(message):
                    logger.error(f"Invalid message format: {message}")
                    return
                
                # Add correlation ID if not present
                if 'correlation_id' not in message:
                    message['correlation_id'] = correlation_id
                
                # Add processing timestamp
                message['processing_timestamp'] = int(time.time())
                
                # Process message with registered handler
                start_time = time.time()
                self.processing_handlers['document_processing'](message)
                processing_time = time.time() - start_time
                
                logger.info(f"Processed message in {processing_time:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}", exc_info=True)
                # Message will be negatively acknowledged by the wrapped_callback in rabbitmq_config
        
        # Start consuming with the callback
        consume_messages(message_callback)
    
    def publish_classification_result(self, result: Dict[str, Any], routing_key: str = 'data-extraction') -> bool:
        """
        Publish classification result to the OCR Service for data extraction.
        
        Args:
            result: Classification result dictionary
            routing_key: Routing key for the message (default: 'data-extraction')
            
        Returns:
            bool: True if message was published successfully, False otherwise
            
        Raises:
            ValueError: If result is missing required fields
        """
        # Validate required fields
        required_fields = ['document_id', 'document_type', 'confidence', 'correlation_id']
        for field in required_fields:
            if field not in result:
                raise ValueError(f"Missing required field in classification result: {field}")
        
        # Add metadata
        result['source'] = 'document-service'
        result['timestamp'] = int(time.time())
        result['message_type'] = 'classification_result'
        
        try:
            # Publish message
            self.client.publish(result, routing_key)
            logger.info(f"Published classification result for document {result['document_id']} "
                       f"with type {result['document_type']} and confidence {result['confidence']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish classification result: {str(e)}", exc_info=True)
            return False
    
    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """
        Validate incoming message format.
        
        Args:
            message: Message to validate
            
        Returns:
            bool: True if message is valid, False otherwise
        """
        # Check for required fields
        required_fields = ['document_id', 'document_url', 'metadata']
        for field in required_fields:
            if field not in message:
                logger.error(f"Missing required field in message: {field}")
                return False
        
        # Validate metadata structure if present
        if 'metadata' in message and not isinstance(message['metadata'], dict):
            logger.error("Metadata must be a dictionary")
            return False
        
        return True


class MessageSchema:
    """
    Defines the standard message schemas for document processing.
    
    This class provides static methods for creating properly formatted messages
    for different stages of the document processing pipeline.
    """
    
    @staticmethod
    def create_classification_result(document_id: str, document_type: str, 
                                    confidence: float, needs_review: bool,
                                    probabilities: Dict[str, float],
                                    metadata: Dict[str, Any],
                                    correlation_id: str) -> Dict[str, Any]:
        """
        Create a standardized classification result message.
        
        Args:
            document_id: Unique identifier for the document
            document_type: Classified document type
            confidence: Classification confidence score (0.0 to 1.0)
            needs_review: Whether the document needs manual review
            probabilities: Dictionary of class probabilities
            metadata: Additional metadata about the document
            correlation_id: Correlation ID for request tracing
            
        Returns:
            Dict[str, Any]: Formatted classification result message
        """
        return {
            'document_id': document_id,
            'document_type': document_type,
            'confidence': confidence,
            'needs_review': needs_review,
            'probabilities': probabilities,
            'metadata': metadata,
            'correlation_id': correlation_id,
            'timestamp': int(time.time()),
            'source': 'document-service',
            'message_type': 'classification_result'
        }
    
    @staticmethod
    def validate_incoming_document(message: Dict[str, Any]) -> List[str]:
        """
        Validate an incoming document message and return any validation errors.
        
        Args:
            message: Document message to validate
            
        Returns:
            List[str]: List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        required_fields = ['document_id', 'document_url', 'metadata']
        for field in required_fields:
            if field not in message:
                errors.append(f"Missing required field: {field}")
        
        # Validate field types
        if 'document_id' in message and not isinstance(message['document_id'], str):
            errors.append("document_id must be a string")
            
        if 'document_url' in message and not isinstance(message['document_url'], str):
            errors.append("document_url must be a string")
            
        if 'metadata' in message and not isinstance(message['metadata'], dict):
            errors.append("metadata must be a dictionary")
        
        # Validate metadata fields if present
        if 'metadata' in message and isinstance(message['metadata'], dict):
            metadata = message['metadata']
            
            # Check for email metadata if source is email
            if metadata.get('source') == 'email':
                if 'email_id' not in metadata:
                    errors.append("Missing email_id in metadata for email source")
                if 'sender' not in metadata:
                    errors.append("Missing sender in metadata for email source")
                if 'received_at' not in metadata:
                    errors.append("Missing received_at in metadata for email source")
        
        return errors


# Create a singleton instance for use throughout the application
queue_service = QueueService()


def get_queue_service() -> QueueService:
    """
    Get the QueueService singleton instance.
    
    Returns:
        QueueService: Singleton instance of the QueueService
    """
    return queue_service