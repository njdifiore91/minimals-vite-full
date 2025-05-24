"""
Unit tests for the RabbitMQ utilities in the Document Service.

This module contains tests for the RabbitMQ connection management, message publishing,
message consumption, and acknowledgment functions in the Document Service.
It verifies that retry logic is properly implemented for message publishing and
that error handling works correctly for channel and connection errors.
"""

import json
import time
from unittest.mock import MagicMock, patch, call, ANY

import pytest
import pika
from pika.exceptions import (
    AMQPConnectionError,
    ConnectionClosed,
    ConnectionClosedByBroker,
    ConnectionBlockedTimeout,
    ChannelClosed,
    ChannelClosedByBroker
)

from document_service.utils.rabbitmq_utils import (
    rabbitmq_channel,
    publish_message_with_retry,
    publish_to_ocr_service,
    MessageHandler,
    DocumentMessageHandler,
    PublishResult,
    ack_message,
    nack_message,
    reject_message
)
from document_service.config.rabbitmq_config import (
    EXCHANGE_NAME,
    QUEUE_NAME,
    MAX_RETRIES,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
    serialize_message,
    deserialize_message
)


class TestRabbitMQChannel:
    """Tests for the rabbitmq_channel context manager."""

    def test_channel_create_new(self, mock_rabbitmq_client):
        """Test that a new connection and channel are created if none exist."""
        # Configure mock client with no connection or channel
        mock_rabbitmq_client.connection = None
        mock_rabbitmq_client.channel = None
        
        # Use the context manager
        with rabbitmq_channel() as channel:
            assert channel is mock_rabbitmq_client.connection.channel.return_value
        
        # Verify that connection and channel were created
        assert mock_rabbitmq_client.connect.called
        assert mock_rabbitmq_client.connection.channel.called

    def test_channel_reuse_existing(self, mock_rabbitmq_client):
        """Test that existing connection and channel are reused if available."""
        # Configure mock client with open connection and channel
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.is_closed = False
        mock_channel.is_closed = False
        mock_rabbitmq_client.connection = mock_connection
        mock_rabbitmq_client.channel = mock_channel
        
        # Use the context manager
        with rabbitmq_channel() as channel:
            assert channel is mock_channel
        
        # Verify that no new connection or channel was created
        assert not mock_rabbitmq_client.connect.called
        assert not mock_connection.channel.called

    def test_channel_reconnect_closed_connection(self, mock_rabbitmq_client):
        """Test that the context manager recreates the connection if it's closed."""
        # Configure mock client with closed connection
        mock_connection = MagicMock()
        mock_connection.is_closed = True
        mock_rabbitmq_client.connection = mock_connection
        mock_rabbitmq_client.channel = MagicMock()
        
        # Use the context manager
        with rabbitmq_channel() as channel:
            assert channel is mock_rabbitmq_client.connection.channel.return_value
        
        # Verify that a new connection was created
        assert mock_rabbitmq_client.connect.called

    def test_channel_recreate_closed_channel(self, mock_rabbitmq_client):
        """Test that the context manager recreates the channel if it's closed."""
        # Configure mock client with open connection but closed channel
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.is_closed = False
        mock_channel.is_closed = True
        mock_rabbitmq_client.connection = mock_connection
        mock_rabbitmq_client.channel = mock_channel
        
        # Use the context manager
        with rabbitmq_channel() as channel:
            assert channel is mock_rabbitmq_client.connection.channel.return_value
        
        # Verify that a new channel was created but not a new connection
        assert not mock_rabbitmq_client.connect.called
        assert mock_connection.channel.called

    def test_channel_connection_error_during_operation(self, mock_rabbitmq_client):
        """Test that connection errors during operation are handled correctly."""
        # Configure mock client with open connection and channel
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.is_closed = False
        mock_channel.is_closed = False
        mock_rabbitmq_client.connection = mock_connection
        mock_rabbitmq_client.channel = mock_channel
        
        # Configure channel to raise ConnectionClosed during operation
        mock_channel.__enter__ = MagicMock(side_effect=ConnectionClosed(0, 'Test connection closed'))
        
        # Use the context manager and expect exception to be raised
        with pytest.raises(ConnectionClosed):
            with rabbitmq_channel() as channel:
                pass
        
        # Verify that the channel was reset
        assert mock_rabbitmq_client.connection is not None
        assert mock_rabbitmq_client.channel is None


class TestPublishMessageWithRetry:
    """Tests for the publish_message_with_retry function."""

    def test_publish_success_first_attempt(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test successful message publishing on the first attempt."""
        # Configure mock channel for successful publish
        mock_rabbitmq_channel.basic_publish.return_value = None
        
        # Call the function
        message = {'test': 'message'}
        result = publish_message_with_retry(message)
        
        # Verify the result
        assert result.success is True
        assert result.retry_count == 0
        assert result.error is None
        
        # Verify that basic_publish was called with the correct arguments
        mock_rabbitmq_channel.basic_publish.assert_called_once()
        call_args = mock_rabbitmq_channel.basic_publish.call_args
        assert call_args[1]['exchange'] == EXCHANGE_NAME
        assert call_args[1]['routing_key'] == ''
        assert call_args[1]['body'] == serialize_message(message)
        assert call_args[1]['properties'].content_type == 'application/json'
        assert call_args[1]['properties'].delivery_mode == 2
        assert call_args[1]['properties'].timestamp == 1620000000
        assert call_args[1]['properties'].app_id == 'document-service'

    def test_publish_success_after_retry(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test successful message publishing after a retry."""
        # Configure mock channel to fail on first attempt, succeed on second
        mock_rabbitmq_channel.basic_publish.side_effect = [
            ConnectionClosed(0, 'Test connection closed'),
            None
        ]
        
        # Call the function
        message = {'test': 'message'}
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            result = publish_message_with_retry(message)
        
        # Verify the result
        assert result.success is True
        assert result.retry_count == 1
        assert result.error is None
        
        # Verify that basic_publish was called twice
        assert mock_rabbitmq_channel.basic_publish.call_count == 2
        
        # Verify that sleep was called with the initial retry delay
        mock_sleep.assert_called_once_with(INITIAL_RETRY_DELAY)

    def test_publish_failure_max_retries(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test message publishing failure after maximum retries."""
        # Configure mock channel to always fail with ConnectionClosed
        error = ConnectionClosed(0, 'Test connection closed')
        mock_rabbitmq_channel.basic_publish.side_effect = error
        
        # Call the function
        message = {'test': 'message'}
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            result = publish_message_with_retry(message, max_retries=3)
        
        # Verify the result
        assert result.success is False
        assert result.retry_count == 4  # Initial attempt + 3 retries
        assert result.error is error
        
        # Verify that basic_publish was called the expected number of times
        assert mock_rabbitmq_channel.basic_publish.call_count == 4
        
        # Verify that sleep was called with increasing delays (exponential backoff)
        assert mock_sleep.call_count == 3
        assert mock_sleep.call_args_list[0][0][0] == INITIAL_RETRY_DELAY
        assert mock_sleep.call_args_list[1][0][0] == INITIAL_RETRY_DELAY * 2
        assert mock_sleep.call_args_list[2][0][0] == INITIAL_RETRY_DELAY * 4

    def test_publish_unexpected_error(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test handling of unexpected errors during message publishing."""
        # Configure mock channel to raise an unexpected error
        error = Exception('Unexpected error')
        mock_rabbitmq_channel.basic_publish.side_effect = error
        
        # Call the function
        message = {'test': 'message'}
        result = publish_message_with_retry(message)
        
        # Verify the result
        assert result.success is False
        assert result.retry_count == 0
        assert result.error is error
        
        # Verify that basic_publish was called once
        mock_rabbitmq_channel.basic_publish.assert_called_once()

    def test_publish_with_custom_parameters(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test message publishing with custom exchange and routing key."""
        # Configure mock channel for successful publish
        mock_rabbitmq_channel.basic_publish.return_value = None
        
        # Call the function with custom parameters
        message = {'test': 'message'}
        custom_exchange = 'custom.exchange'
        custom_routing_key = 'custom.routing.key'
        result = publish_message_with_retry(
            message,
            routing_key=custom_routing_key,
            exchange=custom_exchange
        )
        
        # Verify the result
        assert result.success is True
        
        # Verify that basic_publish was called with custom parameters
        call_args = mock_rabbitmq_channel.basic_publish.call_args
        assert call_args[1]['exchange'] == custom_exchange
        assert call_args[1]['routing_key'] == custom_routing_key


class TestPublishToOCRService:
    """Tests for the publish_to_ocr_service function."""

    def test_publish_to_ocr_service_success(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test successful publishing to OCR service."""
        # Configure mock channel for successful publish
        mock_rabbitmq_channel.basic_publish.return_value = None
        
        # Call the function
        document_id = 'doc-12345'
        document_type = 'loan_application'
        s3_path = 'test-mca-documents/documents/loan_application/doc-12345.pdf'
        metadata = {'sender': 'test@example.com', 'received_at': '2023-05-01T12:34:56Z'}
        confidence = 0.95
        
        result = publish_to_ocr_service(
            document_id=document_id,
            document_type=document_type,
            s3_path=s3_path,
            metadata=metadata,
            confidence=confidence
        )
        
        # Verify the result
        assert result.success is True
        assert result.retry_count == 0
        
        # Verify that basic_publish was called with the correct message
        call_args = mock_rabbitmq_channel.basic_publish.call_args
        assert call_args[1]['routing_key'] == f'ocr.{document_type}'
        
        # Deserialize the message body and verify its contents
        message = deserialize_message(call_args[1]['body'])
        assert message['document_id'] == document_id
        assert message['document_type'] == document_type
        assert message['s3_path'] == s3_path
        assert message['metadata'] == metadata
        assert message['confidence'] == confidence
        assert message['classification_timestamp'] == 1620000000
        assert message['service'] == 'document-service'
        assert message['requires_review'] is False  # confidence > 0.75

    def test_publish_to_ocr_service_low_confidence(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test publishing to OCR service with low confidence score."""
        # Configure mock channel for successful publish
        mock_rabbitmq_channel.basic_publish.return_value = None
        
        # Call the function with low confidence
        document_id = 'doc-12345'
        document_type = 'loan_application'
        s3_path = 'test-mca-documents/documents/loan_application/doc-12345.pdf'
        metadata = {'sender': 'test@example.com', 'received_at': '2023-05-01T12:34:56Z'}
        confidence = 0.7  # Below 0.75 threshold
        
        result = publish_to_ocr_service(
            document_id=document_id,
            document_type=document_type,
            s3_path=s3_path,
            metadata=metadata,
            confidence=confidence
        )
        
        # Verify the result
        assert result.success is True
        
        # Deserialize the message body and verify requires_review flag
        message = deserialize_message(mock_rabbitmq_channel.basic_publish.call_args[1]['body'])
        assert message['requires_review'] is True  # confidence < 0.75

    def test_publish_to_ocr_service_failure(self, mock_rabbitmq_client, mock_rabbitmq_channel, mock_time):
        """Test handling of publishing failure to OCR service."""
        # Configure mock channel to fail with ConnectionClosed
        error = ConnectionClosed(0, 'Test connection closed')
        mock_rabbitmq_channel.basic_publish.side_effect = error
        
        # Call the function
        document_id = 'doc-12345'
        document_type = 'loan_application'
        s3_path = 'test-mca-documents/documents/loan_application/doc-12345.pdf'
        metadata = {'sender': 'test@example.com', 'received_at': '2023-05-01T12:34:56Z'}
        confidence = 0.95
        
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            result = publish_to_ocr_service(
                document_id=document_id,
                document_type=document_type,
                s3_path=s3_path,
                metadata=metadata,
                confidence=confidence
            )
        
        # Verify the result
        assert result.success is False
        assert result.error is error


class TestMessageHandler:
    """Tests for the MessageHandler base class."""

    class TestHandler(MessageHandler):
        """Test implementation of MessageHandler for testing."""
        def __init__(self, queue_name=QUEUE_NAME, prefetch_count=10):
            super().__init__(queue_name, prefetch_count)
            self.processed_messages = []
            self.process_result = True
        
        def process_message(self, message, delivery_info, properties):
            self.processed_messages.append((message, delivery_info, properties))
            return self.process_result

    def test_message_handler_init(self):
        """Test MessageHandler initialization."""
        handler = self.TestHandler('test-queue', 5)
        assert handler.queue_name == 'test-queue'
        assert handler.prefetch_count == 5
        assert handler.should_stop is False

    def test_handle_message_success(self, mock_rabbitmq_channel, sample_rabbitmq_message, 
                                   mock_pika_basic_deliver, mock_pika_properties):
        """Test successful message handling."""
        # Create handler with successful processing
        handler = self.TestHandler()
        handler.process_result = True
        
        # Serialize message
        message_body = serialize_message(sample_rabbitmq_message)
        
        # Call handle_message
        handler.handle_message(
            mock_rabbitmq_channel,
            mock_pika_basic_deliver,
            mock_pika_properties,
            message_body
        )
        
        # Verify that the message was processed
        assert len(handler.processed_messages) == 1
        processed_message, delivery_info, properties = handler.processed_messages[0]
        assert processed_message == sample_rabbitmq_message
        assert delivery_info is mock_pika_basic_deliver
        assert properties is mock_pika_properties
        
        # Verify that the message was acknowledged
        mock_rabbitmq_channel.basic_ack.assert_called_once_with(
            delivery_tag=mock_pika_basic_deliver.delivery_tag
        )

    def test_handle_message_processing_failure(self, mock_rabbitmq_channel, sample_rabbitmq_message,
                                              mock_pika_basic_deliver, mock_pika_properties):
        """Test message handling when processing fails."""
        # Create handler with failed processing
        handler = self.TestHandler()
        handler.process_result = False
        
        # Serialize message
        message_body = serialize_message(sample_rabbitmq_message)
        
        # Call handle_message
        handler.handle_message(
            mock_rabbitmq_channel,
            mock_pika_basic_deliver,
            mock_pika_properties,
            message_body
        )
        
        # Verify that the message was processed
        assert len(handler.processed_messages) == 1
        
        # Verify that the message was negatively acknowledged and requeued
        mock_rabbitmq_channel.basic_nack.assert_called_once_with(
            delivery_tag=mock_pika_basic_deliver.delivery_tag,
            requeue=True
        )

    def test_handle_message_deserialization_error(self, mock_rabbitmq_channel,
                                                mock_pika_basic_deliver, mock_pika_properties):
        """Test message handling when deserialization fails."""
        # Create handler
        handler = self.TestHandler()
        
        # Invalid JSON message
        message_body = b'invalid json'
        
        # Call handle_message
        handler.handle_message(
            mock_rabbitmq_channel,
            mock_pika_basic_deliver,
            mock_pika_properties,
            message_body
        )
        
        # Verify that no message was processed
        assert len(handler.processed_messages) == 0
        
        # Verify that the message was rejected without requeue
        mock_rabbitmq_channel.basic_reject.assert_called_once_with(
            delivery_tag=mock_pika_basic_deliver.delivery_tag,
            requeue=False
        )

    def test_handle_message_unexpected_error(self, mock_rabbitmq_channel, sample_rabbitmq_message,
                                           mock_pika_basic_deliver, mock_pika_properties):
        """Test message handling when an unexpected error occurs."""
        # Create handler with process_message that raises an exception
        handler = self.TestHandler()
        handler.process_message = MagicMock(side_effect=Exception('Unexpected error'))
        
        # Serialize message
        message_body = serialize_message(sample_rabbitmq_message)
        
        # Call handle_message
        handler.handle_message(
            mock_rabbitmq_channel,
            mock_pika_basic_deliver,
            mock_pika_properties,
            message_body
        )
        
        # Verify that the message was negatively acknowledged and requeued
        mock_rabbitmq_channel.basic_nack.assert_called_once_with(
            delivery_tag=mock_pika_basic_deliver.delivery_tag,
            requeue=True
        )

    def test_start_consuming(self, mock_rabbitmq_client, mock_rabbitmq_channel):
        """Test starting the consumer."""
        # Create handler
        handler = self.TestHandler('test-queue', 5)
        
        # Mock channel.start_consuming to set should_stop and return
        def mock_start_consuming():
            handler.should_stop = True
        mock_rabbitmq_channel.start_consuming.side_effect = mock_start_consuming
        
        # Call start_consuming
        handler.start_consuming()
        
        # Verify that basic_qos and basic_consume were called
        mock_rabbitmq_channel.basic_qos.assert_called_once_with(prefetch_count=5)
        mock_rabbitmq_channel.basic_consume.assert_called_once_with(
            queue='test-queue',
            on_message_callback=handler.handle_message
        )
        mock_rabbitmq_channel.start_consuming.assert_called_once()

    def test_start_consuming_with_connection_error(self, mock_rabbitmq_client, mock_rabbitmq_channel):
        """Test consumer handling of connection errors."""
        # Create handler
        handler = self.TestHandler()
        
        # Configure channel to raise ConnectionClosed on first call to start_consuming
        # then set should_stop on second call
        mock_rabbitmq_channel.start_consuming.side_effect = [
            ConnectionClosed(0, 'Test connection closed'),
            lambda: setattr(handler, 'should_stop', True)
        ]
        
        # Patch time.sleep to avoid waiting
        with patch('time.sleep') as mock_sleep:
            handler.start_consuming()
        
        # Verify that start_consuming was called twice
        assert mock_rabbitmq_channel.start_consuming.call_count == 2
        
        # Verify that sleep was called with the initial retry delay
        mock_sleep.assert_called_once_with(INITIAL_RETRY_DELAY)

    def test_stop_consuming(self):
        """Test stopping the consumer."""
        # Create handler
        handler = self.TestHandler()
        assert handler.should_stop is False
        
        # Call stop_consuming
        handler.stop_consuming()
        
        # Verify that should_stop was set to True
        assert handler.should_stop is True


class TestDocumentMessageHandler:
    """Tests for the DocumentMessageHandler class."""

    def test_document_handler_init(self, mock_document_classifier):
        """Test DocumentMessageHandler initialization."""
        storage_service = MagicMock()
        handler = DocumentMessageHandler(
            mock_document_classifier,
            storage_service,
            'test-queue',
            5
        )
        
        assert handler.document_classifier is mock_document_classifier
        assert handler.storage_service is storage_service
        assert handler.queue_name == 'test-queue'
        assert handler.prefetch_count == 5

    def test_process_message_success(self, mock_document_classifier, sample_rabbitmq_message,
                                    mock_pika_basic_deliver, mock_pika_properties):
        """Test successful document message processing."""
        # Create mocks
        storage_service = MagicMock()
        storage_service.store_document.return_value = 's3://test-bucket/document.pdf'
        
        # Configure document classifier
        mock_document_classifier.classify.return_value = ('loan_application', 0.95)
        
        # Create handler
        handler = DocumentMessageHandler(mock_document_classifier, storage_service)
        
        # Patch publish_to_ocr_service to return success
        with patch('document_service.utils.rabbitmq_utils.publish_to_ocr_service') as mock_publish:
            mock_publish.return_value = PublishResult(success=True, retry_count=0)
            
            # Call process_message
            result = handler.process_message(
                sample_rabbitmq_message,
                mock_pika_basic_deliver,
                mock_pika_properties
            )
        
        # Verify the result
        assert result is True
        
        # Verify that store_document was called
        storage_service.store_document.assert_called_once_with(
            sample_rabbitmq_message['document_id'],
            sample_rabbitmq_message.get('document_binary')
        )
        
        # Verify that classify was called
        mock_document_classifier.classify.assert_called_once()
        
        # Verify that update_metadata was called
        storage_service.update_metadata.assert_called_once()
        
        # Verify that publish_to_ocr_service was called
        mock_publish.assert_called_once()

    def test_process_message_missing_fields(self, mock_document_classifier):
        """Test document message processing with missing required fields."""
        # Create mocks
        storage_service = MagicMock()
        
        # Create handler
        handler = DocumentMessageHandler(mock_document_classifier, storage_service)
        
        # Create message with missing fields
        message = {'metadata': {}}
        
        # Call process_message
        result = handler.process_message(
            message,
            MagicMock(),
            MagicMock()
        )
        
        # Verify the result
        assert result is False
        
        # Verify that no methods were called
        storage_service.store_document.assert_not_called()
        mock_document_classifier.classify.assert_not_called()
        storage_service.update_metadata.assert_not_called()

    def test_process_message_publish_failure(self, mock_document_classifier, sample_rabbitmq_message):
        """Test document message processing with OCR publish failure."""
        # Create mocks
        storage_service = MagicMock()
        storage_service.store_document.return_value = 's3://test-bucket/document.pdf'
        
        # Configure document classifier
        mock_document_classifier.classify.return_value = ('loan_application', 0.95)
        
        # Create handler
        handler = DocumentMessageHandler(mock_document_classifier, storage_service)
        
        # Patch publish_to_ocr_service to return failure
        with patch('document_service.utils.rabbitmq_utils.publish_to_ocr_service') as mock_publish:
            mock_publish.return_value = PublishResult(
                success=False,
                retry_count=3,
                error=ConnectionClosed(0, 'Test connection closed')
            )
            
            # Call process_message
            result = handler.process_message(
                sample_rabbitmq_message,
                MagicMock(),
                MagicMock()
            )
        
        # Verify the result
        assert result is False

    def test_process_message_unexpected_error(self, mock_document_classifier, sample_rabbitmq_message):
        """Test document message processing with unexpected error."""
        # Create mocks
        storage_service = MagicMock()
        storage_service.store_document.side_effect = Exception('Unexpected error')
        
        # Create handler
        handler = DocumentMessageHandler(mock_document_classifier, storage_service)
        
        # Call process_message
        result = handler.process_message(
            sample_rabbitmq_message,
            MagicMock(),
            MagicMock()
        )
        
        # Verify the result
        assert result is False


class TestMessageAcknowledgment:
    """Tests for the message acknowledgment utility functions."""

    def test_ack_message(self, mock_rabbitmq_channel):
        """Test acknowledging a message."""
        delivery_tag = 123
        ack_message(mock_rabbitmq_channel, delivery_tag)
        
        mock_rabbitmq_channel.basic_ack.assert_called_once_with(delivery_tag=delivery_tag)

    def test_ack_message_with_error(self, mock_rabbitmq_channel):
        """Test error handling when acknowledging a message."""
        # Configure channel to raise ConnectionClosed
        mock_rabbitmq_channel.basic_ack.side_effect = ConnectionClosed(0, 'Test connection closed')
        
        # Call ack_message and expect exception to be raised
        with pytest.raises(ConnectionClosed):
            ack_message(mock_rabbitmq_channel, 123)

    def test_nack_message(self, mock_rabbitmq_channel):
        """Test negatively acknowledging a message."""
        delivery_tag = 123
        requeue = True
        nack_message(mock_rabbitmq_channel, delivery_tag, requeue)
        
        mock_rabbitmq_channel.basic_nack.assert_called_once_with(
            delivery_tag=delivery_tag,
            requeue=requeue
        )

    def test_nack_message_no_requeue(self, mock_rabbitmq_channel):
        """Test negatively acknowledging a message without requeuing."""
        delivery_tag = 123
        requeue = False
        nack_message(mock_rabbitmq_channel, delivery_tag, requeue)
        
        mock_rabbitmq_channel.basic_nack.assert_called_once_with(
            delivery_tag=delivery_tag,
            requeue=requeue
        )

    def test_nack_message_with_error(self, mock_rabbitmq_channel):
        """Test error handling when negatively acknowledging a message."""
        # Configure channel to raise ConnectionClosed
        mock_rabbitmq_channel.basic_nack.side_effect = ConnectionClosed(0, 'Test connection closed')
        
        # Call nack_message and expect exception to be raised
        with pytest.raises(ConnectionClosed):
            nack_message(mock_rabbitmq_channel, 123)

    def test_reject_message(self, mock_rabbitmq_channel):
        """Test rejecting a message."""
        delivery_tag = 123
        requeue = False  # Default
        reject_message(mock_rabbitmq_channel, delivery_tag)
        
        mock_rabbitmq_channel.basic_reject.assert_called_once_with(
            delivery_tag=delivery_tag,
            requeue=requeue
        )

    def test_reject_message_with_requeue(self, mock_rabbitmq_channel):
        """Test rejecting a message with requeuing."""
        delivery_tag = 123
        requeue = True
        reject_message(mock_rabbitmq_channel, delivery_tag, requeue)
        
        mock_rabbitmq_channel.basic_reject.assert_called_once_with(
            delivery_tag=delivery_tag,
            requeue=requeue
        )

    def test_reject_message_with_error(self, mock_rabbitmq_channel):
        """Test error handling when rejecting a message."""
        # Configure channel to raise ConnectionClosed
        mock_rabbitmq_channel.basic_reject.side_effect = ConnectionClosed(0, 'Test connection closed')
        
        # Call reject_message and expect exception to be raised
        with pytest.raises(ConnectionClosed):
            reject_message(mock_rabbitmq_channel, 123)