#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for RabbitMQ messaging in the OCR Service.

This module tests the integration between the OCR Service and RabbitMQ message queue,
verifying that the service correctly consumes messages from input queues, processes documents,
and publishes results to output queues, ensuring reliable message-based processing.

Key test areas:
1. Message consumption from the 'ocr.request' queue
2. Message publishing to the 'data.processing' queue
3. Message format and schema validation
4. Error handling and retry logic for message processing
5. Message acknowledgment and rejection
6. Queue configuration and message routing
7. TLS with client certificate authentication
"""

import json
import os
import pytest
import ssl
from unittest.mock import patch, MagicMock, call
from typing import Dict, List, Any, Tuple, Optional

# Import pika for RabbitMQ testing
import pika
from pika.exceptions import AMQPConnectionError, AMQPChannelError, AMQPError

# Import application modules
from src.services.queue_service import QueueService
from src.services.ocr_service import OCRService
from src.services.storage_service import StorageService
from src.types.messages import MessagePayload, MessageHeaders, ExchangeConfig, QueueConfig, MessageResult
from src.types.errors import ServiceError, ErrorCategory, Result
from src.types.documents import DocumentType, ProcessingStatus


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


# ===== RabbitMQ Test Fixtures =====

@pytest.fixture
def mock_pika_connection(mock_rabbitmq_connection, mock_rabbitmq_channel):
    """Mock pika connection for RabbitMQ testing."""
    with patch('pika.BlockingConnection') as mock_connection:
        # Set the return value to our mock connection
        mock_connection.return_value = mock_rabbitmq_connection
        
        # Return the mocks for testing
        yield mock_connection, mock_rabbitmq_channel


@pytest.fixture
def mock_ssl_context():
    """Mock SSL context for RabbitMQ TLS testing."""
    with patch('ssl.create_default_context') as mock_context:
        mock_ssl_context = MagicMock(spec=ssl.SSLContext)
        mock_context.return_value = mock_ssl_context
        mock_ssl_context.load_cert_chain = MagicMock()
        yield mock_ssl_context


@pytest.fixture
def queue_service(mock_pika_connection, integration_test_rabbitmq_config):
    """Create a QueueService instance with mocked RabbitMQ connection."""
    with patch('src.services.queue_service.rabbitmq_config', integration_test_rabbitmq_config):
        service = QueueService()
        # Force the service to use our mocked connection
        mock_conn, mock_channel = mock_pika_connection
        service.connection = mock_rabbitmq_connection
        service.channel = mock_channel
        service.connected = True
        service.consumer_tag = None
        
        # Set service properties from config
        service.exchange_name = integration_test_rabbitmq_config.exchange_name
        service.exchange_type = integration_test_rabbitmq_config.exchange_type
        service.ocr_request_queue = integration_test_rabbitmq_config.ocr_request_queue
        service.data_processing_queue = integration_test_rabbitmq_config.data_processing_queue
        service.max_retries = integration_test_rabbitmq_config.max_retries
        service.retry_delay = integration_test_rabbitmq_config.retry_delay
        
        yield service


@pytest.fixture
def sample_ocr_response_message(sample_rabbitmq_message) -> MessagePayload:
    """Create a sample OCR response message for testing."""
    request_payload, _ = sample_rabbitmq_message
    
    return {
        "document_id": request_payload["document_id"],
        "application_id": request_payload["application_id"],
        "document_type": request_payload["document_type"],
        "storage_path": request_payload["storage_path"],
        "extraction_results": {
            "fields": {
                "business_name": {
                    "value": "ACME Corporation",
                    "confidence": 0.95
                },
                "tax_id": {
                    "value": "12-3456789",
                    "confidence": 0.85
                },
                "address": {
                    "value": "123 Main St, Anytown, USA 12345",
                    "confidence": 0.92
                }
            },
            "overall_confidence": 0.91,
            "requires_verification": False
        },
        "processing_time_ms": 1500,
        "correlation_id": request_payload.get("correlation_id", ""),
        "timestamp": "2023-01-01T12:01:30Z"
    }


@pytest.fixture
def mock_ocr_service():
    """Mock OCR service for testing message processing."""
    mock_service = MagicMock(spec=OCRService)
    
    # Configure the mock to return predictable results
    mock_service.process_document.return_value = {
        "fields": {
            "business_name": {"value": "ACME Corporation", "confidence": 0.95},
            "tax_id": {"value": "12-3456789", "confidence": 0.85},
            "address": {"value": "123 Main St, Anytown, USA 12345", "confidence": 0.92}
        },
        "overall_confidence": 0.91,
        "requires_verification": False
    }
    
    return mock_service


@pytest.fixture
def mock_storage_service():
    """Mock storage service for testing document retrieval."""
    mock_service = MagicMock(spec=StorageService)
    
    # Configure the mock to return predictable results
    mock_service.download_document.return_value = Result(
        success=True,
        data=b"Sample document content for testing",
        metadata={
            "document_id": "doc-123456",
            "content_type": "application/pdf"
        }
    )
    
    return mock_service


# ===== RabbitMQ Integration Tests =====

class TestRabbitMQIntegration:
    """Test suite for RabbitMQ integration with the OCR Service."""
    
    def test_rabbitmq_connection_initialization(self, mock_pika_connection, mock_ssl_context):
        """Test that the QueueService correctly initializes the RabbitMQ connection with TLS.
        
        This test verifies that the connection is established with the correct parameters,
        including TLS configuration with client certificate authentication as required by
        the technical specification.
        """
        # Initialize QueueService to trigger connection setup
        with patch('ssl.create_default_context', return_value=mock_ssl_context):
            service = QueueService()
        
        # Verify connection was attempted with correct parameters
        mock_conn, _ = mock_pika_connection
        mock_conn.assert_called_once()
        
        # Get the connection parameters from the call
        conn_params = mock_conn.call_args[0][0]
        
        # Verify connection parameters
        assert conn_params.host == service.config.host
        assert conn_params.port == service.config.port
        assert conn_params.virtual_host == service.config.virtual_host
        
        # Verify SSL options if TLS is enabled
        if service.config.use_tls:
            assert conn_params.ssl_options is not None
            # Verify SSL context was created and configured
            mock_ssl_context.load_cert_chain.assert_called_once()
            assert mock_ssl_context.verify_mode == ssl.CERT_REQUIRED
            assert mock_ssl_context.check_hostname is True
    
    def test_exchange_and_queue_declaration(self, queue_service):
        """Test that the QueueService correctly declares exchanges and queues.
        
        This test verifies that the exchange and queues are declared with the correct
        parameters as specified in the technical specification.
        """
        # Get the mock channel
        channel = queue_service.channel
        
        # Verify exchange declaration
        channel.exchange_declare.assert_called_with(
            exchange=queue_service.exchange_name,
            exchange_type=queue_service.exchange_type,
            durable=True
        )
        
        # Verify queue declarations
        assert channel.queue_declare.call_count >= 2
        
        # Verify queue bindings
        assert channel.queue_bind.call_count >= 2
        
        # Verify specific queue bindings
        ocr_request_binding_call = call(
            queue=queue_service.ocr_request_queue,
            exchange=queue_service.exchange_name,
            routing_key='ocr.request'
        )
        data_processing_binding_call = call(
            queue=queue_service.data_processing_queue,
            exchange=queue_service.exchange_name,
            routing_key='data.processing'
        )
        
        assert ocr_request_binding_call in channel.queue_bind.call_args_list
        assert data_processing_binding_call in channel.queue_bind.call_args_list
        
        # Verify QoS setting
        channel.basic_qos.assert_called_once()
    
    def test_message_publishing(self, queue_service, sample_ocr_response_message):
        """Test that messages are correctly published to RabbitMQ.
        
        This test verifies that the QueueService correctly publishes messages to the
        appropriate exchange with the correct routing key and message properties.
        """
        # Publish a message
        result = queue_service.publish_message(
            payload=sample_ocr_response_message,
            routing_key='data.processing',
            headers={"source": "ocr-service"}
        )
        
        # Verify publish was successful
        assert result.success is True
        
        # Verify basic_publish was called with correct parameters
        queue_service.channel.basic_publish.assert_called_once()
        call_args = queue_service.channel.basic_publish.call_args[1]
        
        # Verify exchange and routing key
        assert call_args["exchange"] == queue_service.exchange_name
        assert call_args["routing_key"] == 'data.processing'
        
        # Verify message body is JSON serialized
        body = call_args["body"]
        assert isinstance(body, bytes)
        deserialized = json.loads(body.decode('utf-8'))
        assert deserialized["document_id"] == sample_ocr_response_message["document_id"]
        
        # Verify message properties
        properties = call_args["properties"]
        assert properties.content_type == 'application/json'
        assert properties.content_encoding == 'utf-8'
        assert properties.delivery_mode == 2  # Persistent
        assert properties.headers["source"] == "ocr-service"
    
    def test_message_consumption(self, queue_service, sample_rabbitmq_message, sample_rabbitmq_method, sample_rabbitmq_properties):
        """Test that messages are correctly consumed from RabbitMQ.
        
        This test verifies that the QueueService correctly sets up message consumption
        from the ocr.request queue and processes messages with the provided callback.
        """
        # Create a mock callback function
        mock_callback = MagicMock()
        
        # Start consuming in a separate thread to avoid blocking
        with patch('src.services.queue_service.QueueService.start_consuming') as mock_start_consuming:
            queue_service.start_consuming(mock_callback)
            
            # Verify basic_consume was called with correct parameters
            queue_service.channel.basic_consume.assert_called_once()
            call_args = queue_service.channel.basic_consume.call_args[1]
            
            # Verify queue and auto_ack
            assert call_args["queue"] == queue_service.ocr_request_queue
            assert call_args["auto_ack"] is False  # Manual acknowledgment
            
            # Get the message handler function
            message_handler = call_args["on_message_callback"]
            
            # Get payload and headers from fixture
            payload, headers = sample_rabbitmq_message
            
            # Create message body
            message_body = json.dumps(payload).encode('utf-8')
            
            # Call the message handler
            message_handler(queue_service.channel, sample_rabbitmq_method, sample_rabbitmq_properties, message_body)
            
            # Verify callback was called with correct parameters
            mock_callback.assert_called_once()
            callback_args = mock_callback.call_args[0]
            
            # Verify payload and headers
            assert callback_args[0] == payload
            assert callback_args[1] == sample_rabbitmq_properties.headers
            assert callback_args[2] == queue_service.channel
            assert callback_args[3] == sample_rabbitmq_method
    
    def test_message_acknowledgment(self, queue_service):
        """Test that messages are correctly acknowledged after processing.
        
        This test verifies that the QueueService correctly acknowledges messages
        after successful processing.
        """
        # Acknowledge a message
        delivery_tag = 123
        queue_service.acknowledge_message(delivery_tag)
        
        # Verify basic_ack was called with correct parameters
        queue_service.channel.basic_ack.assert_called_once_with(delivery_tag=delivery_tag)
    
    def test_message_rejection(self, queue_service):
        """Test that messages are correctly rejected when processing fails.
        
        This test verifies that the QueueService correctly rejects messages
        when processing fails, with the option to requeue for retry.
        """
        # Reject a message without requeue
        delivery_tag = 123
        queue_service.reject_message(delivery_tag, requeue=False)
        
        # Verify basic_reject was called with correct parameters
        queue_service.channel.basic_reject.assert_called_once_with(
            delivery_tag=delivery_tag, requeue=False)
        
        # Reset mock
        queue_service.channel.basic_reject.reset_mock()
        
        # Reject a message with requeue
        queue_service.reject_message(delivery_tag, requeue=True)
        
        # Verify basic_reject was called with correct parameters
        queue_service.channel.basic_reject.assert_called_once_with(
            delivery_tag=delivery_tag, requeue=True)
    
    def test_message_format_validation(self, queue_service, sample_rabbitmq_method):
        """Test that message format is validated before processing.
        
        This test verifies that the QueueService validates message format and rejects
        invalid messages without requeuing them.
        """
        # Create a mock callback function
        mock_callback = MagicMock()
        
        # Get the message handler function
        queue_service.channel.basic_consume.reset_mock()
        queue_service.start_consuming(mock_callback)
        call_args = queue_service.channel.basic_consume.call_args[1]
        message_handler = call_args["on_message_callback"]
        
        # Create mock properties with empty headers
        mock_properties = MagicMock()
        mock_properties.headers = {}
        
        # Test with invalid JSON
        invalid_body = b"This is not valid JSON"
        
        # Reset the reject mock
        queue_service.channel.basic_reject.reset_mock()
        
        # Call the message handler
        message_handler(queue_service.channel, sample_rabbitmq_method, mock_properties, invalid_body)
        
        # Verify callback was not called
        mock_callback.assert_not_called()
        
        # Verify message was rejected without requeue
        queue_service.channel.basic_reject.assert_called_once_with(
            delivery_tag=sample_rabbitmq_method.delivery_tag, requeue=False)
    
    def test_connection_error_handling(self, mock_pika_connection):
        """Test that connection errors are properly handled.
        
        This test verifies that the QueueService correctly handles connection errors
        and implements retry logic with exponential backoff.
        """
        # Configure mock connection to raise error on first attempt
        mock_conn, _ = mock_pika_connection
        mock_conn.side_effect = [AMQPConnectionError("Connection refused"), MagicMock()]
        
        # Patch the retry delay to speed up the test
        with patch('src.services.queue_service.QueueService.retry_delay', 0.01):
            # Initialize QueueService - should retry and succeed
            with patch('time.sleep'):  # Avoid actual sleep in tests
                service = QueueService()
            
            # Verify connection was attempted twice
            assert mock_conn.call_count == 2
    
    def test_channel_error_handling(self, queue_service, sample_ocr_response_message):
        """Test that channel errors are properly handled.
        
        This test verifies that the QueueService correctly handles channel errors
        and implements retry logic with exponential backoff.
        """
        # Configure mock channel to raise error on publish attempt
        queue_service.channel.basic_publish.side_effect = AMQPChannelError("Channel closed")
        
        # Patch the retry decorator to use a real implementation with short delays
        with patch('src.services.queue_service.QueueService.with_retry', 
                  lambda func: func):  # Disable retry for this test
            # Patch the connection check to avoid reconnection attempts
            with patch('src.services.queue_service.QueueService.with_connection', 
                      lambda func: func):  # Disable connection check
                # Attempt to publish - should raise an error
                with pytest.raises(ServiceError) as excinfo:
                    queue_service.publish_message(
                        payload=sample_ocr_response_message,
                        routing_key='data.processing'
                    )
                
                # Verify error category
                assert excinfo.value.category == ErrorCategory.CONNECTION
    
    def test_retry_logic(self, queue_service, sample_ocr_response_message):
        """Test that retry logic is correctly implemented for RabbitMQ operations.
        
        This test verifies that the QueueService implements retry logic with exponential
        backoff for RabbitMQ operations, as required by the technical specification.
        """
        # Configure mock channel to fail twice then succeed
        queue_service.channel.basic_publish.side_effect = [
            AMQPChannelError("Channel closed"),
            AMQPChannelError("Channel closed"),
            None  # Success on third attempt
        ]
        
        # Create a simplified retry decorator for testing
        def test_retry_decorator(func):
            def wrapper(*args, **kwargs):
                retries = 0
                max_retries = 3
                last_error = None
                
                while retries <= max_retries:
                    try:
                        result = func(*args, **kwargs)
                        if isinstance(result, Result) and not result.success:
                            last_error = result.error
                            retries += 1
                            if retries <= max_retries:
                                continue  # Retry without delay in tests
                            return result
                        return Result(success=True, data=True)
                    except Exception as e:
                        last_error = e
                        retries += 1
                        if retries <= max_retries:
                            continue  # Retry without delay in tests
                
                return Result(success=False, error=last_error)
            return wrapper
        
        # Apply the test retry decorator
        with patch('src.services.queue_service.QueueService.with_retry', 
                  lambda func: test_retry_decorator(func)):
            # Patch the connection check to avoid reconnection attempts
            with patch('src.services.queue_service.QueueService.with_connection', 
                      lambda func: func):
                # Attempt to publish - should succeed after retries
                result = queue_service.publish_message(
                    payload=sample_ocr_response_message,
                    routing_key='data.processing'
                )
                
                # Verify publish was successful after retries
                assert result.success is True
                
                # Verify basic_publish was called three times
                assert queue_service.channel.basic_publish.call_count == 3
    
    def test_end_to_end_message_processing(self, queue_service, mock_ocr_service, 
                                         mock_storage_service, sample_rabbitmq_message,
                                         sample_rabbitmq_method, sample_rabbitmq_properties):
        """Test the end-to-end message processing flow.
        
        This test verifies the complete flow of message processing, from consumption
        to document retrieval, OCR processing, and result publishing.
        """
        # Create a message processing callback that simulates the OCR pipeline
        def process_message(payload, headers, channel, method):
            try:
                # Extract document information
                document_id = payload.get('document_id')
                storage_path = payload.get('storage_path')
                document_type = payload.get('document_type')
                
                # Download document from storage
                download_result = mock_storage_service.download_document(storage_path)
                if not download_result.success:
                    raise ServiceError("Failed to download document", ErrorCategory.STORAGE)
                
                # Process document with OCR
                ocr_result = mock_ocr_service.process_document(
                    download_result.data, document_type)
                
                # Prepare result message
                result_payload = {
                    "document_id": document_id,
                    "document_type": document_type,
                    "storage_path": storage_path,
                    "extraction_results": ocr_result,
                    "processing_time_ms": 1500,
                    "correlation_id": payload.get("correlation_id", ""),
                    "timestamp": "2023-01-01T12:01:30Z"
                }
                
                # Publish result
                publish_result = queue_service.publish_message(
                    payload=result_payload,
                    routing_key='data.processing',
                    headers={"source": "ocr-service"}
                )
                
                if not publish_result.success:
                    raise ServiceError("Failed to publish result", ErrorCategory.MESSAGING)
                
                # Acknowledge the message
                channel.basic_ack(delivery_tag=method.delivery_tag)
                
                return True
            except Exception as e:
                # Reject the message with requeue for retriable errors
                if isinstance(e, ServiceError) and e.category in [
                    ErrorCategory.CONNECTION, ErrorCategory.TEMPORARY]:
                    channel.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
                else:
                    # Don't requeue for non-retriable errors
                    channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                
                return False
        
        # Get the message handler function
        queue_service.channel.basic_consume.reset_mock()
        queue_service.start_consuming(process_message)
        call_args = queue_service.channel.basic_consume.call_args[1]
        message_handler = call_args["on_message_callback"]
        
        # Get payload and headers from fixture
        payload, headers = sample_rabbitmq_message
        
        # Create message body
        message_body = json.dumps(payload).encode('utf-8')
        
        # Reset mocks
        queue_service.channel.basic_publish.reset_mock()
        queue_service.channel.basic_ack.reset_mock()
        
        # Call the message handler
        message_handler(queue_service.channel, sample_rabbitmq_method, sample_rabbitmq_properties, message_body)
        
        # Verify document was downloaded
        mock_storage_service.download_document.assert_called_once_with(payload["storage_path"])
        
        # Verify OCR processing was performed
        mock_ocr_service.process_document.assert_called_once()
        
        # Verify result was published
        queue_service.channel.basic_publish.assert_called_once()
        
        # Verify message was acknowledged
        queue_service.channel.basic_ack.assert_called_once_with(delivery_tag=sample_rabbitmq_method.delivery_tag)
    
    def test_graceful_shutdown(self, queue_service):
        """Test that the QueueService shuts down gracefully.
        
        This test verifies that the QueueService properly closes the RabbitMQ connection
        and channel when shutting down, to prevent resource leaks.
        """
        # Set up consumer tag
        queue_service.consumer_tag = "test-consumer"
        
        # Close the service
        queue_service.close()
        
        # Verify consumer was canceled
        queue_service.channel.basic_cancel.assert_called_once_with("test-consumer")
        
        # Verify channel was closed
        queue_service.channel.close.assert_called_once()
        
        # Verify connection was closed
        queue_service.connection.close.assert_called_once()
        
        # Verify state was reset
        assert queue_service.connected is False
        assert queue_service.channel is None
        assert queue_service.connection is None
        assert queue_service.consumer_tag is None


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])