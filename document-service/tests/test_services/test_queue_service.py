import pytest
import json
import ssl
import time
from unittest.mock import MagicMock, patch, call, PropertyMock
from pika.exceptions import AMQPConnectionError, AMQPChannelError, ConnectionClosedByBroker

from src.services.queue_service import QueueService
from src.types.messages import (
    MessagePayload, MessageHeaders, PublishOptions, ConsumeOptions,
    ExchangeConfig, QueueConfig, BindingConfig, DeliveryMode
)
from src.types.documents import Document, DocumentType
from src.types.errors import ServiceError, MessagingError
from src.config import rabbitmq_config


class TestQueueService:
    """Test suite for the QueueService class.
    
    These tests verify that the QueueService correctly connects to RabbitMQ,
    consumes messages from the 'document-processing' queue, publishes classification
    results to the 'data-extraction' queue, and handles connection errors.
    """
    
    def test_init(self, rabbitmq_config_fixture):
        """Test QueueService initialization with configuration."""
        # Arrange & Act
        service = QueueService(rabbitmq_config_fixture)
        
        # Assert
        assert service.connection is None
        assert service.channel is None
        assert service.is_connected is False
        assert service.config == rabbitmq_config_fixture
    
    @patch('ssl.create_default_context')
    @patch('pika.ConnectionParameters')
    def test_setup_connection_params_with_tls(self, mock_connection_params, mock_ssl_context, rabbitmq_config_fixture):
        """Test that connection parameters are set up correctly with TLS."""
        # Arrange
        mock_ssl_context_instance = MagicMock()
        mock_ssl_context.return_value = mock_ssl_context_instance
        mock_ssl_options = MagicMock()
        
        with patch('pika.SSLOptions', return_value=mock_ssl_options) as mock_ssl_options_class:
            # Act
            service = QueueService(rabbitmq_config_fixture)
            
            # Assert
            mock_ssl_context.assert_called_once()
            mock_ssl_context_instance.verify_mode = ssl.CERT_REQUIRED
            mock_ssl_context_instance.load_cert_chain.assert_called_once()
            mock_ssl_options_class.assert_called_once()
            mock_connection_params.assert_called_once()
            assert service._connection_params is not None
    
    def test_setup_connection_params_error(self, rabbitmq_config_fixture):
        """Test error handling during connection parameter setup."""
        # Arrange
        with patch('ssl.create_default_context', side_effect=Exception('SSL error')):
            # Act & Assert
            with pytest.raises(ServiceError) as excinfo:
                QueueService(rabbitmq_config_fixture)
            
            assert 'RabbitMQ connection setup failed' in str(excinfo.value)
    
    @patch('pika.BlockingConnection')
    def test_connect_success(self, mock_blocking_connection, rabbitmq_config_fixture):
        """Test successful connection to RabbitMQ."""
        # Arrange
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_connection.channel.return_value = mock_channel
        mock_blocking_connection.return_value = mock_connection
        
        service = QueueService(rabbitmq_config_fixture)
        service._connection_params = MagicMock()
        
        # Act
        result = service.connect()
        
        # Assert
        assert result is True
        assert service.is_connected is True
        mock_blocking_connection.assert_called_once_with(service._connection_params)
        mock_connection.channel.assert_called_once()
        
        # Verify exchange and queue declarations
        assert mock_channel.exchange_declare.call_count == 1
        assert mock_channel.queue_declare.call_count == 2
        assert mock_channel.queue_bind.call_count == 2
        
        # Verify exchange declaration
        exchange_call = mock_channel.exchange_declare.call_args
        assert exchange_call[1]['exchange'] == 'mca.documents'
        
        # Verify queue declarations
        queue_calls = mock_channel.queue_declare.call_args_list
        assert queue_calls[0][1]['queue'] == 'document-processing'
        assert queue_calls[1][1]['queue'] == 'classification-results'
        
        # Verify queue bindings
        binding_calls = mock_channel.queue_bind.call_args_list
        assert binding_calls[0][1]['exchange'] == 'mca.documents'
        assert binding_calls[0][1]['queue'] == 'document-processing'
        assert binding_calls[1][1]['exchange'] == 'mca.classification'
        assert binding_calls[1][1]['queue'] == 'classification-results'
    
    @patch('pika.BlockingConnection')
    def test_connect_already_connected(self, mock_blocking_connection, rabbitmq_config_fixture):
        """Test connect when already connected."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.is_connected = True
        
        # Act
        result = service.connect()
        
        # Assert
        assert result is True
        mock_blocking_connection.assert_not_called()
    
    @patch('pika.BlockingConnection')
    def test_connect_failure(self, mock_blocking_connection, rabbitmq_config_fixture):
        """Test connection failure handling."""
        # Arrange
        mock_blocking_connection.side_effect = AMQPConnectionError('Connection refused')
        
        service = QueueService(rabbitmq_config_fixture)
        service._connection_params = MagicMock()
        
        # Act & Assert
        with pytest.raises(ServiceError) as excinfo:
            service.connect()
        
        assert 'RabbitMQ connection failed' in str(excinfo.value)
        assert service.is_connected is False
    
    def test_disconnect(self, rabbitmq_config_fixture):
        """Test disconnection from RabbitMQ."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connection = MagicMock()
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure mocks
        service.connection.is_open = True
        service.channel.is_open = True
        
        # Act
        service.disconnect()
        
        # Assert
        service.channel.close.assert_called_once()
        service.connection.close.assert_called_once()
        assert service.connection is None
        assert service.channel is None
        assert service.is_connected is False
    
    def test_disconnect_with_errors(self, rabbitmq_config_fixture):
        """Test disconnection with errors."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connection = MagicMock()
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure mocks to raise exceptions
        service.connection.is_open = True
        service.channel.is_open = True
        service.channel.close.side_effect = Exception('Channel close error')
        service.connection.close.side_effect = Exception('Connection close error')
        
        # Act
        service.disconnect()
        
        # Assert
        service.channel.close.assert_called_once()
        service.connection.close.assert_called_once()
        assert service.connection is None
        assert service.channel is None
        assert service.is_connected is False
    
    def test_consume_messages(self, rabbitmq_config_fixture):
        """Test consuming messages from the queue."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        callback = MagicMock()
        options = ConsumeOptions.for_document_processing(prefetch_count=10)
        
        # Act
        service.consume_messages(callback, options)
        
        # Assert
        service.connect.assert_called_once()
        service.channel.basic_qos.assert_called_once_with(prefetch_count=10)
        service.channel.basic_consume.assert_called_once()
        service.channel.start_consuming.assert_called_once()
        
        # Verify consume arguments
        consume_call = service.channel.basic_consume.call_args
        assert consume_call[1]['queue'] == 'document-processing'
        assert consume_call[1]['on_message_callback'] is not None
        assert consume_call[1]['auto_ack'] is False
    
    def test_consume_messages_not_connected(self, rabbitmq_config_fixture):
        """Test consuming messages when not connected."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = False
        
        callback = MagicMock()
        
        # Act
        service.consume_messages(callback)
        
        # Assert
        service.connect.assert_called_once()
    
    def test_consume_messages_channel_error(self, rabbitmq_config_fixture):
        """Test error handling during message consumption."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure mock to raise exception
        service.channel.basic_consume.side_effect = AMQPChannelError('Channel error')
        
        callback = MagicMock()
        options = ConsumeOptions.for_document_processing()
        
        # Act & Assert
        with pytest.raises(ServiceError) as excinfo:
            service.consume_messages(callback, options)
        
        assert 'RabbitMQ channel error' in str(excinfo.value)
    
    def test_message_handler_success(self, rabbitmq_config_fixture):
        """Test successful message handling in the consume callback."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        callback = MagicMock()
        options = ConsumeOptions.for_document_processing()
        
        # Capture the message handler function
        service.consume_messages(callback, options)
        message_handler = service.channel.basic_consume.call_args[1]['on_message_callback']
        
        # Create test message
        ch = MagicMock()
        method = MagicMock(delivery_tag='test-tag')
        properties = MagicMock(headers={'test': 'header'})
        body = json.dumps({'test': 'message'}).encode('utf-8')
        
        # Act
        message_handler(ch, method, properties, body)
        
        # Assert
        callback.assert_called_once()
        ch.basic_ack.assert_called_once_with(delivery_tag='test-tag')
    
    def test_message_handler_json_error(self, rabbitmq_config_fixture):
        """Test JSON decoding error in message handler."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        callback = MagicMock()
        options = ConsumeOptions.for_document_processing()
        
        # Capture the message handler function
        service.consume_messages(callback, options)
        message_handler = service.channel.basic_consume.call_args[1]['on_message_callback']
        
        # Create invalid JSON message
        ch = MagicMock()
        method = MagicMock(delivery_tag='test-tag')
        properties = MagicMock(headers={'test': 'header'})
        body = b'invalid json'
        
        # Act
        message_handler(ch, method, properties, body)
        
        # Assert
        callback.assert_not_called()
        ch.basic_reject.assert_called_once_with(delivery_tag='test-tag', requeue=False)
    
    def test_message_handler_processing_error(self, rabbitmq_config_fixture):
        """Test processing error in message handler."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure callback to raise exception
        callback = MagicMock(side_effect=Exception('Processing error'))
        options = ConsumeOptions.for_document_processing()
        
        # Capture the message handler function
        service.consume_messages(callback, options)
        message_handler = service.channel.basic_consume.call_args[1]['on_message_callback']
        
        # Create test message
        ch = MagicMock()
        method = MagicMock(delivery_tag='test-tag')
        properties = MagicMock(headers={'test': 'header'})
        body = json.dumps({'test': 'message'}).encode('utf-8')
        
        # Act
        message_handler(ch, method, properties, body)
        
        # Assert
        callback.assert_called_once()
        ch.basic_reject.assert_called_once_with(delivery_tag='test-tag', requeue=True)
    
    def test_publish_message(self, rabbitmq_config_fixture):
        """Test publishing a message to the queue."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        message = MessagePayload({'test': 'message'})
        options = PublishOptions.for_classification_result()
        
        # Act
        result = service.publish_message(message, options)
        
        # Assert
        assert result is True
        service.connect.assert_not_called()  # Already connected
        service.channel.basic_publish.assert_called_once()
        
        # Verify publish arguments
        publish_call = service.channel.basic_publish.call_args
        assert publish_call[1]['exchange'] == 'mca.classification'
        assert publish_call[1]['routing_key'] == 'classification.results'
        assert publish_call[1]['body'] == json.dumps({'test': 'message'}).encode('utf-8')
        assert publish_call[1]['mandatory'] is True
    
    def test_publish_message_not_connected(self, rabbitmq_config_fixture):
        """Test publishing a message when not connected."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = False
        
        message = MessagePayload({'test': 'message'})
        options = PublishOptions.for_classification_result()
        
        # Act
        result = service.publish_message(message, options)
        
        # Assert
        assert result is True
        service.connect.assert_called_once()
    
    def test_publish_message_dict(self, rabbitmq_config_fixture):
        """Test publishing a dictionary message."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        message = {'test': 'message'}
        options = PublishOptions.for_classification_result()
        
        # Act
        result = service.publish_message(message, options)
        
        # Assert
        assert result is True
        service.channel.basic_publish.assert_called_once()
    
    def test_publish_message_channel_error_with_reconnect(self, rabbitmq_config_fixture):
        """Test channel error during publish with successful reconnect."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure first publish to fail, reconnect to succeed
        service.channel.basic_publish.side_effect = [
            AMQPChannelError('Channel error'),
            None  # Success on retry
        ]
        service.reconnect = MagicMock(return_value=True)
        
        message = MessagePayload({'test': 'message'})
        options = PublishOptions.for_classification_result()
        
        # Act
        result = service.publish_message(message, options)
        
        # Assert
        assert result is True
        assert service.channel.basic_publish.call_count == 2
        service.reconnect.assert_called_once()
    
    def test_publish_message_channel_error_reconnect_fails(self, rabbitmq_config_fixture):
        """Test channel error during publish with failed reconnect."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure publish to fail and reconnect to fail
        service.channel.basic_publish.side_effect = AMQPChannelError('Channel error')
        service.reconnect = MagicMock(return_value=False)
        
        message = MessagePayload({'test': 'message'})
        options = PublishOptions.for_classification_result()
        
        # Act & Assert
        with pytest.raises(MessagingError) as excinfo:
            service.publish_message(message, options)
        
        assert 'Failed to reconnect for message republishing' in str(excinfo.value)
        service.reconnect.assert_called_once()
    
    def test_publish_message_other_error(self, rabbitmq_config_fixture):
        """Test other error during publish."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.channel = MagicMock()
        service.is_connected = True
        
        # Configure publish to fail with a different error
        service.channel.basic_publish.side_effect = Exception('Unknown error')
        
        message = MessagePayload({'test': 'message'})
        options = PublishOptions.for_classification_result()
        
        # Act & Assert
        with pytest.raises(MessagingError) as excinfo:
            service.publish_message(message, options)
        
        assert 'Message publishing failed' in str(excinfo.value)
    
    def test_publish_classification_result(self, rabbitmq_config_fixture):
        """Test publishing a classification result."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.publish_message = MagicMock(return_value=True)
        
        message = MessagePayload.create_classification_result(
            document_id='test-doc-123',
            document_type=DocumentType.APPLICATION,
            confidence=0.95,
            confidence_scores={'APPLICATION': 0.95, 'OTHER': 0.05},
            requires_review=False,
            model_version='1.0.0',
            features_used=['text_length', 'keyword_matches']
        )
        correlation_id = 'test-correlation-id'
        
        # Act
        result = service.publish_classification_result(message, correlation_id)
        
        # Assert
        assert result is True
        service.publish_message.assert_called_once()
        
        # Verify the options passed to publish_message
        options = service.publish_message.call_args[0][1]
        assert options.exchange == 'mca.classification'
        assert options.routing_key == 'classification.results'
        assert options.headers.get('correlation_id') == correlation_id
    
    def test_reconnect_success(self, rabbitmq_config_fixture):
        """Test successful reconnection after failure."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.disconnect = MagicMock()
        service.connect = MagicMock(return_value=True)
        
        # Act
        result = service.reconnect()
        
        # Assert
        assert result is True
        service.disconnect.assert_called_once()
        service.connect.assert_called_once()
    
    def test_reconnect_failure(self, rabbitmq_config_fixture):
        """Test failed reconnection attempts."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.disconnect = MagicMock()
        service.connect = MagicMock(side_effect=ServiceError('Connection failed'))
        service.config = {'reconnect_attempts': 3, 'retry_delay': 0.01}  # Fast retry for testing
        
        # Act
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = service.reconnect()
        
        # Assert
        assert result is False
        service.disconnect.assert_called_once()
        assert service.connect.call_count == 3  # Tried 3 times
    
    def test_context_manager(self, rabbitmq_config_fixture):
        """Test using QueueService as a context manager."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.disconnect = MagicMock()
        
        # Act
        with service as s:
            # Assert in context
            assert s is service
            service.connect.assert_called_once()
        
        # Assert after context
        service.disconnect.assert_called_once()
    
    def test_context_manager_with_exception(self, rabbitmq_config_fixture):
        """Test context manager with exception."""
        # Arrange
        service = QueueService(rabbitmq_config_fixture)
        service.connect = MagicMock(return_value=True)
        service.disconnect = MagicMock()
        
        # Act & Assert
        try:
            with service:
                service.connect.assert_called_once()
                raise ValueError('Test exception')
        except ValueError:
            pass
        
        # Assert disconnect was called despite exception
        service.disconnect.assert_called_once()