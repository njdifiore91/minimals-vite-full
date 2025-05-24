#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the RabbitMQ message handling service.

This module contains tests that verify the queue service correctly connects to RabbitMQ,
consumes messages from the 'document-processing' queue, publishes classification results
to the 'data-extraction' queue, and handles connection errors.

These tests validate that the Document Service can:
1. Connect to RabbitMQ with the 'mca.documents' exchange as specified in section 0.1.3
2. Consume messages from the 'document-processing' queue as specified in section 0.2.1.4
3. Publish classification results to the 'data-extraction' queue
4. Handle connection errors and recover from them
5. Properly serialize and deserialize messages in the standardized JSON format
"""

import json
import time
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest
from pika.exceptions import AMQPConnectionError, AMQPChannelError

# Import the QueueService and MessageSchema classes
from src.services.queue_service import QueueService, MessageSchema
from src.types.classification import DocumentType, ConfidenceScore


class TestQueueService:
    """Test suite for the QueueService class."""

    def test_init(self, mock_rabbitmq_utils):
        """Test that QueueService initializes correctly."""
        # Create a QueueService instance
        service = QueueService()
        
        # Verify that the client is initialized
        assert service.client is not None
        
        # Verify that the processing handlers dictionary is initialized
        assert service.processing_handlers == {}

    def test_register_document_handler(self, mock_rabbitmq_utils):
        """Test that document handlers can be registered."""
        # Create a QueueService instance
        service = QueueService()
        
        # Create a mock handler function
        mock_handler = MagicMock()
        
        # Register the handler
        service.register_document_handler(mock_handler)
        
        # Verify that the handler was registered
        assert 'document_processing' in service.processing_handlers
        assert service.processing_handlers['document_processing'] == mock_handler

    def test_start_consuming_no_handler(self, mock_rabbitmq_utils):
        """Test that start_consuming raises an error if no handler is registered."""
        # Create a QueueService instance
        service = QueueService()
        
        # Verify that start_consuming raises a RuntimeError
        with pytest.raises(RuntimeError, match="No document processing handler registered"):
            service.start_consuming()

    def test_start_consuming(self, mock_rabbitmq_utils):
        """Test that start_consuming calls the consume_messages function."""
        # Create a QueueService instance
        service = QueueService()
        
        # Register a mock handler
        mock_handler = MagicMock()
        service.register_document_handler(mock_handler)
        
        # Start consuming messages
        service.start_consuming()
        
        # Verify that consume_messages was called
        mock_rabbitmq_utils.consume_messages.assert_called_once()

    def test_message_callback(self, mock_rabbitmq_utils):
        """Test that the message callback processes messages correctly."""
        # Create a QueueService instance
        service = QueueService()
        
        # Register a mock handler
        mock_handler = MagicMock()
        service.register_document_handler(mock_handler)
        
        # Create a test message
        test_message = {
            'document_id': 'test-doc-id',
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': {
                'source': 'email',
                'email_id': 'test-email-id',
                'sender': 'test@example.com',
                'received_at': '2023-01-01T00:00:00Z'
            }
        }
        
        # Create mock method and properties
        mock_method = MagicMock()
        mock_properties = MagicMock(correlation_id='test-correlation-id')
        
        # Get the message callback function
        # We need to start consuming to get the callback registered
        with patch('src.config.rabbitmq_config.consume_messages') as mock_consume:
            service.start_consuming()
            # Extract the callback function that was passed to consume_messages
            callback_func = mock_consume.call_args[0][0]
        
        # Call the callback function with our test message
        callback_func(test_message, mock_method, mock_properties)
        
        # Verify that the handler was called with the message
        mock_handler.assert_called_once()
        # Verify that the message was passed to the handler
        handler_call_args = mock_handler.call_args[0][0]
        assert handler_call_args['document_id'] == 'test-doc-id'
        assert handler_call_args['document_url'] == 'https://example.com/test-doc.pdf'
        assert 'correlation_id' in handler_call_args
        assert handler_call_args['correlation_id'] == 'test-correlation-id'
        assert 'processing_timestamp' in handler_call_args

    def test_message_callback_invalid_message(self, mock_rabbitmq_utils):
        """Test that the message callback handles invalid messages correctly."""
        # Create a QueueService instance
        service = QueueService()
        
        # Register a mock handler
        mock_handler = MagicMock()
        service.register_document_handler(mock_handler)
        
        # Create an invalid test message (missing required fields)
        test_message = {
            'document_id': 'test-doc-id',
            # Missing 'document_url'
            # Missing 'metadata'
        }
        
        # Create mock method and properties
        mock_method = MagicMock()
        mock_properties = MagicMock(correlation_id='test-correlation-id')
        
        # Get the message callback function
        with patch('document_service.config.rabbitmq_config.consume_messages') as mock_consume:
            service.start_consuming()
            callback_func = mock_consume.call_args[0][0]
        
        # Call the callback function with our invalid test message
        callback_func(test_message, mock_method, mock_properties)
        
        # Verify that the handler was not called
        mock_handler.assert_not_called()

    def test_message_callback_handler_exception(self, mock_rabbitmq_utils):
        """Test that the message callback handles exceptions from the handler."""
        # Create a QueueService instance
        service = QueueService()
        
        # Register a mock handler that raises an exception
        mock_handler = MagicMock(side_effect=Exception("Test exception"))
        service.register_document_handler(mock_handler)
        
        # Create a test message
        test_message = {
            'document_id': 'test-doc-id',
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': {
                'source': 'email',
                'email_id': 'test-email-id',
                'sender': 'test@example.com',
                'received_at': '2023-01-01T00:00:00Z'
            }
        }
        
        # Create mock method and properties
        mock_method = MagicMock()
        mock_properties = MagicMock(correlation_id='test-correlation-id')
        
        # Get the message callback function
        with patch('src.config.rabbitmq_config.consume_messages') as mock_consume:
            service.start_consuming()
            callback_func = mock_consume.call_args[0][0]
        
        # Call the callback function with our test message
        # This should not raise an exception outside the callback
        callback_func(test_message, mock_method, mock_properties)
        
        # Verify that the handler was called
        mock_handler.assert_called_once()

    def test_publish_classification_result(self, mock_rabbitmq_utils):
        """Test that publish_classification_result publishes messages correctly."""
        # Create a QueueService instance
        service = QueueService()
        
        # Create a test classification result
        test_result = {
            'document_id': 'test-doc-id',
            'document_type': 'APPLICATION',
            'confidence': 0.95,
            'correlation_id': 'test-correlation-id'
        }
        
        # Publish the result
        result = service.publish_classification_result(test_result)
        
        # Verify that the result is True (success)
        assert result is True
        
        # Verify that publish_message was called with the correct arguments
        mock_rabbitmq_utils.publish_message.assert_called_once()
        # Check that the message contains the required fields
        published_message = mock_rabbitmq_utils.publish_message.call_args[0][0]
        assert published_message['document_id'] == 'test-doc-id'
        assert published_message['document_type'] == 'APPLICATION'
        assert published_message['confidence'] == 0.95
        assert published_message['correlation_id'] == 'test-correlation-id'
        assert 'source' in published_message
        assert published_message['source'] == 'document-service'
        assert 'timestamp' in published_message
        assert 'message_type' in published_message
        assert published_message['message_type'] == 'classification_result'

    def test_publish_classification_result_missing_fields(self, mock_rabbitmq_utils):
        """Test that publish_classification_result validates required fields."""
        # Create a QueueService instance
        service = QueueService()
        
        # Create a test classification result with missing fields
        test_result = {
            'document_id': 'test-doc-id',
            # Missing 'document_type'
            'confidence': 0.95,
            'correlation_id': 'test-correlation-id'
        }
        
        # Verify that publish_classification_result raises a ValueError
        with pytest.raises(ValueError, match="Missing required field in classification result: document_type"):
            service.publish_classification_result(test_result)
        
        # Verify that publish_message was not called
        mock_rabbitmq_utils.publish_message.assert_not_called()

    def test_publish_classification_result_publish_error(self, mock_rabbitmq_utils):
        """Test that publish_classification_result handles publish errors."""
        # Create a QueueService instance
        service = QueueService()
        
        # Configure publish_message to raise an exception
        mock_rabbitmq_utils.publish_message.side_effect = Exception("Test exception")
        
        # Create a test classification result
        test_result = {
            'document_id': 'test-doc-id',
            'document_type': 'APPLICATION',
            'confidence': 0.95,
            'correlation_id': 'test-correlation-id'
        }
        
        # Publish the result
        result = service.publish_classification_result(test_result)
        
        # Verify that the result is False (failure)
        assert result is False

    def test_validate_message(self, mock_rabbitmq_utils):
        """Test that _validate_message correctly validates messages."""
        # Create a QueueService instance
        service = QueueService()
        
        # Test a valid message
        valid_message = {
            'document_id': 'test-doc-id',
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': {
                'source': 'email',
                'email_id': 'test-email-id',
                'sender': 'test@example.com',
                'received_at': '2023-01-01T00:00:00Z'
            }
        }
        assert service._validate_message(valid_message) is True
        
        # Test a message with missing required fields
        invalid_message_1 = {
            'document_id': 'test-doc-id',
            # Missing 'document_url'
            'metadata': {}
        }
        assert service._validate_message(invalid_message_1) is False
        
        # Test a message with invalid metadata
        invalid_message_2 = {
            'document_id': 'test-doc-id',
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': 'not-a-dict'  # Should be a dict
        }
        assert service._validate_message(invalid_message_2) is False

    def test_connection_error_handling(self, mock_rabbitmq_connection_error, mock_rabbitmq_utils):
        """Test that the QueueService handles connection errors."""
        # Configure rabbitmq_utils.get_rabbitmq_client to raise an AMQPConnectionError
        mock_rabbitmq_utils.get_rabbitmq_client.side_effect = AMQPConnectionError("Connection refused")
        
        # Create a QueueService instance
        # This should not raise an exception outside the constructor
        service = QueueService()
        
        # Register a mock handler
        mock_handler = MagicMock()
        service.register_document_handler(mock_handler)
        
        # Start consuming messages
        # This should not raise an exception outside the method
        service.start_consuming()
        
        # Verify that consume_messages was called
        mock_rabbitmq_utils.consume_messages.assert_called_once()

    def test_channel_error_handling(self, mock_rabbitmq_channel_error, mock_rabbitmq_utils):
        """Test that the QueueService handles channel errors."""
        # Configure rabbitmq_utils.create_channel to raise an AMQPChannelError
        mock_rabbitmq_utils.create_channel.side_effect = AMQPChannelError("Channel closed")
        
        # Create a QueueService instance
        service = QueueService()
        
        # Register a mock handler
        mock_handler = MagicMock()
        service.register_document_handler(mock_handler)
        
        # Start consuming messages
        # This should not raise an exception outside the method
        service.start_consuming()
        
        # Verify that consume_messages was called
        mock_rabbitmq_utils.consume_messages.assert_called_once()


class TestMessageSchema:
    """Test suite for the MessageSchema class."""

    def test_create_classification_result(self):
        """Test that create_classification_result creates properly formatted messages."""
        # Create a test classification result
        document_id = 'test-doc-id'
        document_type = 'APPLICATION'
        confidence = 0.95
        needs_review = False
        probabilities = {'APPLICATION': 0.95, 'BANK_STATEMENT': 0.03, 'TAX_RETURN': 0.02}
        metadata = {'filename': 'test-doc.pdf', 'mime_type': 'application/pdf'}
        correlation_id = 'test-correlation-id'
        
        # Create the message
        message = MessageSchema.create_classification_result(
            document_id=document_id,
            document_type=document_type,
            confidence=confidence,
            needs_review=needs_review,
            probabilities=probabilities,
            metadata=metadata,
            correlation_id=correlation_id
        )
        
        # Verify that the message contains all required fields
        assert message['document_id'] == document_id
        assert message['document_type'] == document_type
        assert message['confidence'] == confidence
        assert message['needs_review'] == needs_review
        assert message['probabilities'] == probabilities
        assert message['metadata'] == metadata
        assert message['correlation_id'] == correlation_id
        assert 'timestamp' in message
        assert 'source' in message
        assert message['source'] == 'document-service'
        assert 'message_type' in message
        assert message['message_type'] == 'classification_result'

    def test_validate_incoming_document(self):
        """Test that validate_incoming_document correctly validates messages."""
        # Test a valid message
        valid_message = {
            'document_id': 'test-doc-id',
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': {
                'source': 'email',
                'email_id': 'test-email-id',
                'sender': 'test@example.com',
                'received_at': '2023-01-01T00:00:00Z'
            }
        }
        errors = MessageSchema.validate_incoming_document(valid_message)
        assert len(errors) == 0
        
        # Test a message with missing required fields
        invalid_message_1 = {
            'document_id': 'test-doc-id',
            # Missing 'document_url'
            'metadata': {}
        }
        errors = MessageSchema.validate_incoming_document(invalid_message_1)
        assert len(errors) > 0
        assert "Missing required field: document_url" in errors
        
        # Test a message with invalid field types
        invalid_message_2 = {
            'document_id': 123,  # Should be a string
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': {}
        }
        errors = MessageSchema.validate_incoming_document(invalid_message_2)
        assert len(errors) > 0
        assert "document_id must be a string" in errors
        
        # Test a message with missing email metadata
        invalid_message_3 = {
            'document_id': 'test-doc-id',
            'document_url': 'https://example.com/test-doc.pdf',
            'metadata': {
                'source': 'email',
                # Missing 'email_id'
                'sender': 'test@example.com',
                'received_at': '2023-01-01T00:00:00Z'
            }
        }
        errors = MessageSchema.validate_incoming_document(invalid_message_3)
        assert len(errors) > 0
        assert "Missing email_id in metadata for email source" in errors


@pytest.mark.integration
class TestQueueServiceIntegration:
    """Integration tests for the QueueService class.
    
    These tests require a running RabbitMQ instance and are marked with the
    'integration' marker to be skipped by default.
    """

    def test_tls_connection(self):
        """Test that the QueueService can connect to RabbitMQ with TLS."""
        # This test requires a running RabbitMQ instance with TLS enabled
        # and client certificate authentication configured.
        # It is marked with the 'integration' marker to be skipped by default.
        
        # Configure environment variables for TLS connection
        with patch.dict('os.environ', {
            'RABBITMQ_SSL': 'True',
            'RABBITMQ_SSL_CERT_PATH': '/path/to/client.crt',
            'RABBITMQ_SSL_KEY_PATH': '/path/to/client.key',
            'RABBITMQ_SSL_CA_CERTS': '/path/to/ca.crt'
        }):
            # Create a QueueService instance
            service = QueueService()
            
            # Register a mock handler
            mock_handler = MagicMock()
            service.register_document_handler(mock_handler)
            
            # Start consuming messages
            # This would fail if TLS connection fails
            with patch('src.config.rabbitmq_config.consume_messages'):
                service.start_consuming()

    def test_end_to_end_message_flow(self, create_test_classification_result):
        """Test the end-to-end message flow from consumption to publishing."""
        # This test requires a running RabbitMQ instance and is marked with the
        # 'integration' marker to be skipped by default.
        
        # Create a QueueService instance
        service = QueueService()
        
        # Create a test classification result
        classification_result = create_test_classification_result()
        
        # Create a handler that publishes the classification result
        def test_handler(message):
            # Create a classification result from the message
            result = {
                'document_id': message['document_id'],
                'document_type': 'APPLICATION',
                'confidence': 0.95,
                'correlation_id': message.get('correlation_id', 'test-correlation-id')
            }
            # Publish the result
            service.publish_classification_result(result)
        
        # Register the handler
        service.register_document_handler(test_handler)
        
        # Mock the consume_messages function to call our handler directly
        with patch('src.config.rabbitmq_config.consume_messages') as mock_consume:
            # Define a function that calls the handler with a test message
            def call_handler(callback):
                # Create a test message
                test_message = {
                    'document_id': 'test-doc-id',
                    'document_url': 'https://example.com/test-doc.pdf',
                    'metadata': {
                        'source': 'email',
                        'email_id': 'test-email-id',
                        'sender': 'test@example.com',
                        'received_at': '2023-01-01T00:00:00Z'
                    }
                }
                # Create mock method and properties
                mock_method = MagicMock()
                mock_properties = MagicMock(correlation_id='test-correlation-id')
                # Call the callback
                callback(test_message, mock_method, mock_properties)
            
            # Configure mock_consume to call our function
            mock_consume.side_effect = call_handler
            
            # Start consuming messages
            with patch('src.config.rabbitmq_config.publish_message') as mock_publish:
                service.start_consuming()
                
                # Verify that publish_message was called with the correct arguments
                mock_publish.assert_called_once()
                # Check that the message contains the required fields
                published_message = mock_publish.call_args[0][0]
                assert published_message['document_id'] == 'test-doc-id'
                assert published_message['document_type'] == 'APPLICATION'
                assert published_message['confidence'] == 0.95
                assert published_message['correlation_id'] == 'test-correlation-id'
                assert 'source' in published_message
                assert published_message['source'] == 'document-service'
                assert 'timestamp' in published_message
                assert 'message_type' in published_message
                assert published_message['message_type'] == 'classification_result'