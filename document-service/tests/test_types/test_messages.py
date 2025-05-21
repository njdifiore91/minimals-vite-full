"""Unit tests for RabbitMQ message type definitions in the Document Service.

This module contains tests for MessagePayload, MessageHeaders, ExchangeConfig,
QueueConfig, PublishOptions, and ConsumeOptions types to ensure they correctly
handle message queue operations.
"""

import pytest
import json
from datetime import datetime
import uuid
from unittest.mock import patch, MagicMock

from src.types.messages import (
    MessagePayload, MessageHeaders, ExchangeConfig, QueueConfig,
    PublishOptions, ConsumeOptions, DeliveryMode, ExchangeType,
    BindingConfig, ConnectionConfig
)
from src.types.documents import Document, DocumentType, ProcessingStatus
from src.types.errors import MessagingError


class TestMessagePayload:
    """Tests for the MessagePayload class."""
    
    def test_create_from_document(self):
        """Test creating a payload from a document."""
        # Create a mock document
        mock_document = MagicMock(spec=Document)
        mock_document.to_dict.return_value = {
            "metadata": {
                "id": "doc123",
                "filename": "test.pdf",
                "size": 12345,
                "mime_type": "application/pdf"
            },
            "status": "received"
        }
        
        # Create payload from document
        payload = MessagePayload.from_document(mock_document)
        
        # Verify payload contains document data
        assert payload["metadata"]["id"] == "doc123"
        assert payload["metadata"]["filename"] == "test.pdf"
        assert payload["status"] == "received"
        
        # Test with include_content=True
        mock_document.content = b"test content"
        payload = MessagePayload.from_document(mock_document, include_content=True)
        
        # Verify content is included and base64 encoded
        assert "content_base64" in payload
        assert isinstance(payload["content_base64"], str)
    
    def test_create_classification_result(self):
        """Test creating a classification result payload."""
        # Create classification result payload
        payload = MessagePayload.create_classification_result(
            document_id="doc123",
            document_type=DocumentType.APPLICATION,
            confidence=0.95,
            confidence_scores={
                "application": 0.95,
                "tax_return": 0.03,
                "bank_statement": 0.01,
                "pay_stub": 0.005,
                "id_document": 0.004,
                "other": 0.001
            },
            requires_review=False,
            model_version="1.0.0",
            features_used=["text_content", "layout", "metadata"]
        )
        
        # Verify payload contains classification data
        assert payload["document_id"] == "doc123"
        assert payload["document_type"] == "application"
        assert payload["confidence"] == 0.95
        assert payload["confidence_scores"]["application"] == 0.95
        assert payload["requires_review"] is False
        assert payload["model_version"] == "1.0.0"
        assert "text_content" in payload["features_used"]
        assert "classified_at" in payload
        assert isinstance(payload["metadata"], dict)
    
    def test_to_json(self):
        """Test converting a payload to JSON."""
        # Create a payload with a datetime
        now = datetime.utcnow()
        payload = MessagePayload({
            "document_id": "doc123",
            "timestamp": now,
            "status": "received"
        })
        
        # Convert to JSON
        json_str = payload.to_json()
        
        # Verify JSON is valid and contains expected data
        parsed = json.loads(json_str)
        assert parsed["document_id"] == "doc123"
        assert parsed["status"] == "received"
        assert "timestamp" in parsed

    def test_from_json(self):
        """Test creating a payload from JSON."""
        # Create a JSON string
        json_str = '{"document_id": "doc123", "status": "received", "metadata": {"id": "doc123"}}'
        
        # Parse JSON to payload
        payload = MessagePayload.from_json(json_str)
        
        # Verify payload contains expected data
        assert payload["document_id"] == "doc123"
        assert payload["status"] == "received"
        assert payload["metadata"]["id"] == "doc123"
        
        # Test with invalid JSON
        with pytest.raises(MessagingError):
            MessagePayload.from_json("invalid json")


class TestMessageHeaders:
    """Tests for the MessageHeaders class."""
    
    def test_create_default_headers(self):
        """Test creating default headers."""
        # Create default headers
        headers = MessageHeaders.create()
        
        # Verify default values
        assert "message_id" in headers
        assert headers["content_type"] == "application/json"
        assert headers["content_encoding"] == "utf-8"
        assert headers["delivery_mode"] == DeliveryMode.PERSISTENT.value
        assert headers["priority"] == 0
        assert headers["app_id"] == "document-service"
        assert "timestamp" in headers
    
    def test_create_custom_headers(self):
        """Test creating headers with custom values."""
        # Create custom headers
        message_id = str(uuid.uuid4())
        correlation_id = str(uuid.uuid4())
        reply_to = "reply-queue"
        now = datetime.utcnow()
        
        headers = MessageHeaders.create(
            message_id=message_id,
            correlation_id=correlation_id,
            reply_to=reply_to,
            content_type="application/xml",
            content_encoding="ascii",
            delivery_mode=DeliveryMode.NON_PERSISTENT,
            priority=5,
            app_id="test-app",
            timestamp=now,
            custom_header="custom-value"
        )
        
        # Verify custom values
        assert headers["message_id"] == message_id
        assert headers["correlation_id"] == correlation_id
        assert headers["reply_to"] == reply_to
        assert headers["content_type"] == "application/xml"
        assert headers["content_encoding"] == "ascii"
        assert headers["delivery_mode"] == DeliveryMode.NON_PERSISTENT.value
        assert headers["priority"] == 5
        assert headers["app_id"] == "test-app"
        assert headers["timestamp"] == int(now.timestamp())
        assert headers["custom_header"] == "custom-value"


class TestExchangeConfig:
    """Tests for the ExchangeConfig class."""
    
    def test_init(self):
        """Test initializing an exchange configuration."""
        # Create exchange config
        exchange = ExchangeConfig(
            name="test-exchange",
            exchange_type=ExchangeType.TOPIC,
            durable=False,
            auto_delete=True,
            arguments={"alternate-exchange": "alt-exchange"}
        )
        
        # Verify attributes
        assert exchange.name == "test-exchange"
        assert exchange.exchange_type == ExchangeType.TOPIC
        assert exchange.durable is False
        assert exchange.auto_delete is True
        assert exchange.arguments["alternate-exchange"] == "alt-exchange"
    
    def test_document_exchange(self):
        """Test creating the standard document exchange."""
        # Create document exchange
        exchange = ExchangeConfig.document_exchange()
        
        # Verify standard configuration
        assert exchange.name == "mca.documents"
        assert exchange.exchange_type == ExchangeType.FANOUT
        assert exchange.durable is True
        assert exchange.auto_delete is False
    
    def test_classification_exchange(self):
        """Test creating the standard classification exchange."""
        # Create classification exchange
        exchange = ExchangeConfig.classification_exchange()
        
        # Verify standard configuration
        assert exchange.name == "mca.classification"
        assert exchange.exchange_type == ExchangeType.DIRECT
        assert exchange.durable is True
        assert exchange.auto_delete is False
    
    def test_to_dict(self):
        """Test converting exchange config to dictionary."""
        # Create exchange config
        exchange = ExchangeConfig(
            name="test-exchange",
            exchange_type=ExchangeType.TOPIC,
            durable=True,
            auto_delete=False,
            arguments={"alternate-exchange": "alt-exchange"}
        )
        
        # Convert to dict
        config_dict = exchange.to_dict()
        
        # Verify dict contains expected values
        assert config_dict["name"] == "test-exchange"
        assert config_dict["exchange_type"] == "topic"
        assert config_dict["durable"] is True
        assert config_dict["auto_delete"] is False
        assert config_dict["arguments"]["alternate-exchange"] == "alt-exchange"


class TestQueueConfig:
    """Tests for the QueueConfig class."""
    
    def test_init(self):
        """Test initializing a queue configuration."""
        # Create queue config
        queue = QueueConfig(
            name="test-queue",
            durable=True,
            exclusive=True,
            auto_delete=False,
            arguments={"x-message-ttl": 60000}
        )
        
        # Verify attributes
        assert queue.name == "test-queue"
        assert queue.durable is True
        assert queue.exclusive is True
        assert queue.auto_delete is False
        assert queue.arguments["x-message-ttl"] == 60000
    
    def test_document_processing_queue(self):
        """Test creating the standard document processing queue."""
        # Create document processing queue
        queue = QueueConfig.document_processing_queue()
        
        # Verify standard configuration
        assert queue.name == "document-processing"
        assert queue.durable is True
        assert queue.exclusive is False
        assert queue.auto_delete is False
        assert "x-dead-letter-exchange" in queue.arguments
        assert queue.arguments["x-dead-letter-exchange"] == "mca.dead-letter"
        assert "x-dead-letter-routing-key" in queue.arguments
        assert "x-message-ttl" in queue.arguments
    
    def test_classification_results_queue(self):
        """Test creating the standard classification results queue."""
        # Create classification results queue
        queue = QueueConfig.classification_results_queue()
        
        # Verify standard configuration
        assert queue.name == "classification-results"
        assert queue.durable is True
        assert queue.exclusive is False
        assert queue.auto_delete is False
        assert "x-dead-letter-exchange" in queue.arguments
        assert queue.arguments["x-dead-letter-exchange"] == "mca.dead-letter"
        assert "x-dead-letter-routing-key" in queue.arguments
        assert "x-message-ttl" in queue.arguments
    
    def test_to_dict(self):
        """Test converting queue config to dictionary."""
        # Create queue config
        queue = QueueConfig(
            name="test-queue",
            durable=True,
            exclusive=False,
            auto_delete=False,
            arguments={"x-message-ttl": 60000}
        )
        
        # Convert to dict
        config_dict = queue.to_dict()
        
        # Verify dict contains expected values
        assert config_dict["name"] == "test-queue"
        assert config_dict["durable"] is True
        assert config_dict["exclusive"] is False
        assert config_dict["auto_delete"] is False
        assert config_dict["arguments"]["x-message-ttl"] == 60000


class TestBindingConfig:
    """Tests for the BindingConfig class."""
    
    def test_init_with_strings(self):
        """Test initializing a binding configuration with string names."""
        # Create binding config with strings
        binding = BindingConfig(
            exchange="test-exchange",
            queue="test-queue",
            routing_key="test.key",
            arguments={"x-match": "all"}
        )
        
        # Verify attributes
        assert binding.exchange == "test-exchange"
        assert binding.queue == "test-queue"
        assert binding.routing_key == "test.key"
        assert binding.arguments["x-match"] == "all"
    
    def test_init_with_configs(self):
        """Test initializing a binding configuration with config objects."""
        # Create exchange and queue configs
        exchange = ExchangeConfig(name="test-exchange")
        queue = QueueConfig(name="test-queue")
        
        # Create binding with configs
        binding = BindingConfig(
            exchange=exchange,
            queue=queue,
            routing_key="test.key"
        )
        
        # Verify attributes
        assert binding.exchange == "test-exchange"
        assert binding.queue == "test-queue"
        assert binding.routing_key == "test.key"
    
    def test_document_processing_binding(self):
        """Test creating the standard document processing binding."""
        # Create document processing binding
        binding = BindingConfig.document_processing_binding()
        
        # Verify standard configuration
        assert binding.exchange == "mca.documents"
        assert binding.queue == "document-processing"
        assert binding.routing_key == ""
    
    def test_classification_results_binding(self):
        """Test creating the standard classification results binding."""
        # Create classification results binding
        binding = BindingConfig.classification_results_binding()
        
        # Verify standard configuration
        assert binding.exchange == "mca.classification"
        assert binding.queue == "classification-results"
        assert binding.routing_key == "classification.results"
    
    def test_to_dict(self):
        """Test converting binding config to dictionary."""
        # Create binding config
        binding = BindingConfig(
            exchange="test-exchange",
            queue="test-queue",
            routing_key="test.key",
            arguments={"x-match": "all"}
        )
        
        # Convert to dict
        config_dict = binding.to_dict()
        
        # Verify dict contains expected values
        assert config_dict["exchange"] == "test-exchange"
        assert config_dict["queue"] == "test-queue"
        assert config_dict["routing_key"] == "test.key"
        assert config_dict["arguments"]["x-match"] == "all"


class TestPublishOptions:
    """Tests for the PublishOptions class."""
    
    def test_init_with_string(self):
        """Test initializing publish options with string exchange."""
        # Create publish options with string exchange
        options = PublishOptions(
            exchange="test-exchange",
            routing_key="test.key",
            mandatory=True,
            priority=5
        )
        
        # Verify attributes
        assert options.exchange == "test-exchange"
        assert options.routing_key == "test.key"
        assert options.mandatory is True
        assert options.headers["priority"] == 5
    
    def test_init_with_config(self):
        """Test initializing publish options with exchange config."""
        # Create exchange config
        exchange = ExchangeConfig(name="test-exchange")
        
        # Create publish options with exchange config
        options = PublishOptions(
            exchange=exchange,
            routing_key="test.key"
        )
        
        # Verify attributes
        assert options.exchange == "test-exchange"
        assert options.routing_key == "test.key"
    
    def test_init_with_headers(self):
        """Test initializing publish options with custom headers."""
        # Create custom headers
        headers = MessageHeaders.create(
            correlation_id="corr-123",
            reply_to="reply-queue",
            priority=5
        )
        
        # Create publish options with custom headers
        options = PublishOptions(
            exchange="test-exchange",
            routing_key="test.key",
            headers=headers
        )
        
        # Verify headers are used
        assert options.headers["correlation_id"] == "corr-123"
        assert options.headers["reply_to"] == "reply-queue"
        assert options.headers["priority"] == 5
    
    def test_init_with_expiration(self):
        """Test initializing publish options with expiration."""
        # Create publish options with expiration
        options = PublishOptions(
            exchange="test-exchange",
            expiration=60000  # 60 seconds
        )
        
        # Verify expiration is set in headers
        assert options.headers["expiration"] == "60000"
    
    def test_for_classification_result(self):
        """Test creating publish options for classification results."""
        # Create classification result publish options
        options = PublishOptions.for_classification_result(
            correlation_id="corr-123",
            priority=5
        )
        
        # Verify standard configuration
        assert options.exchange == "mca.classification"
        assert options.routing_key == "classification.results"
        assert options.headers["correlation_id"] == "corr-123"
        assert options.headers["priority"] == 5
    
    def test_to_dict(self):
        """Test converting publish options to dictionary."""
        # Create publish options
        options = PublishOptions(
            exchange="test-exchange",
            routing_key="test.key",
            mandatory=True,
            correlation_id="corr-123",
            priority=5
        )
        
        # Convert to dict
        options_dict = options.to_dict()
        
        # Verify dict contains expected values
        assert options_dict["exchange"] == "test-exchange"
        assert options_dict["routing_key"] == "test.key"
        assert options_dict["mandatory"] is True
        assert "properties" in options_dict
        assert options_dict["properties"]["correlation_id"] == "corr-123"
        assert options_dict["properties"]["priority"] == 5


class TestConsumeOptions:
    """Tests for the ConsumeOptions class."""
    
    def test_init_with_string(self):
        """Test initializing consume options with string queue."""
        # Create consume options with string queue
        options = ConsumeOptions(
            queue="test-queue",
            consumer_tag="consumer-1",
            exclusive=True,
            no_ack=True,
            prefetch_count=20
        )
        
        # Verify attributes
        assert options.queue == "test-queue"
        assert options.consumer_tag == "consumer-1"
        assert options.exclusive is True
        assert options.no_ack is True
        assert options.prefetch_count == 20
    
    def test_init_with_config(self):
        """Test initializing consume options with queue config."""
        # Create queue config
        queue = QueueConfig(name="test-queue")
        
        # Create consume options with queue config
        options = ConsumeOptions(
            queue=queue,
            prefetch_count=20
        )
        
        # Verify attributes
        assert options.queue == "test-queue"
        assert options.prefetch_count == 20
    
    def test_auto_consumer_tag(self):
        """Test auto-generated consumer tag."""
        # Create consume options without consumer tag
        options = ConsumeOptions(queue="test-queue")
        
        # Verify consumer tag is auto-generated
        assert options.consumer_tag.startswith("document-service-")
        assert len(options.consumer_tag) > 16  # Includes UUID
    
    def test_for_document_processing(self):
        """Test creating consume options for document processing."""
        # Create document processing consume options
        options = ConsumeOptions.for_document_processing(prefetch_count=15)
        
        # Verify standard configuration
        assert options.queue == "document-processing"
        assert options.prefetch_count == 15
        assert options.no_ack is False
    
    def test_to_dict(self):
        """Test converting consume options to dictionary."""
        # Create consume options with fixed consumer tag for testing
        options = ConsumeOptions(
            queue="test-queue",
            consumer_tag="test-consumer",
            exclusive=True,
            no_local=True,
            no_ack=False,
            arguments={"x-priority": 10}
        )
        
        # Convert to dict
        options_dict = options.to_dict()
        
        # Verify dict contains expected values
        assert options_dict["queue"] == "test-queue"
        assert options_dict["consumer_tag"] == "test-consumer"
        assert options_dict["exclusive"] is True
        assert options_dict["no_local"] is True
        assert options_dict["no_ack"] is False
        assert options_dict["arguments"]["x-priority"] == 10


class TestConnectionConfig:
    """Tests for the ConnectionConfig class."""
    
    def test_init(self):
        """Test initializing a connection configuration."""
        # Create connection config
        config = ConnectionConfig(
            host="rabbitmq.example.com",
            port=5672,
            virtual_host="/test",
            username="test-user",
            password="test-pass",
            heartbeat=30,
            connection_attempts=5,
            retry_delay=2,
            ssl=True,
            ssl_options={"ca_certs": "/path/to/ca.pem"},
            client_properties={"connection_name": "test-connection"}
        )
        
        # Verify attributes
        assert config.host == "rabbitmq.example.com"
        assert config.port == 5672
        assert config.virtual_host == "/test"
        assert config.username == "test-user"
        assert config.password == "test-pass"
        assert config.heartbeat == 30
        assert config.connection_attempts == 5
        assert config.retry_delay == 2
        assert config.ssl is True
        assert config.ssl_options["ca_certs"] == "/path/to/ca.pem"
        assert config.client_properties["connection_name"] == "test-connection"
    
    @patch("os.environ.get")
    def test_from_env(self, mock_env_get):
        """Test creating connection config from environment variables."""
        # Mock environment variables
        mock_env_get.side_effect = lambda key, default: {
            "RABBITMQ_HOST": "env-rabbitmq.example.com",
            "RABBITMQ_PORT": "5673",
            "RABBITMQ_VHOST": "/env-test",
            "RABBITMQ_USERNAME": "env-user",
            "RABBITMQ_PASSWORD": "env-pass",
            "RABBITMQ_HEARTBEAT": "45",
            "RABBITMQ_SSL": "false"
        }.get(key, default)
        
        # Create connection config from env
        config = ConnectionConfig.from_env()
        
        # Verify environment values are used
        assert config.host == "env-rabbitmq.example.com"
        assert config.port == 5673
        assert config.virtual_host == "/env-test"
        assert config.username == "env-user"
        assert config.password == "env-pass"
        assert config.heartbeat == 45
        assert config.ssl is False
    
    def test_to_dict(self):
        """Test converting connection config to dictionary."""
        # Create connection config
        config = ConnectionConfig(
            host="rabbitmq.example.com",
            port=5672,
            virtual_host="/test",
            username="test-user",
            password="test-pass",
            ssl_options={"ca_certs": "/path/to/ca.pem"}
        )
        
        # Convert to dict
        config_dict = config.to_dict()
        
        # Verify dict contains expected values
        assert config_dict["host"] == "rabbitmq.example.com"
        assert config_dict["port"] == 5672
        assert config_dict["virtual_host"] == "/test"
        assert config_dict["credentials"]["username"] == "test-user"
        assert config_dict["credentials"]["password"] == "*****"  # Password is masked
        assert "ssl_options" in config_dict
        assert "ca_certs" in config_dict["ssl_options"]
    
    def test_get_connection_parameters(self):
        """Test getting connection parameters for pika."""
        # Create connection config
        config = ConnectionConfig(
            host="rabbitmq.example.com",
            port=5672,
            virtual_host="/test",
            username="test-user",
            password="test-pass",
            ssl=True,
            ssl_options={"ca_certs": "/path/to/ca.pem"}
        )
        
        # Get connection parameters
        params = config.get_connection_parameters()
        
        # Verify parameters contain expected values
        assert params["host"] == "rabbitmq.example.com"
        assert params["port"] == 5672
        assert params["virtual_host"] == "/test"
        assert params["credentials"]["username"] == "test-user"
        assert params["credentials"]["password"] == "test-pass"  # Actual password in params
        assert params["ssl"] is True
        assert params["ssl_options"]["ca_certs"] == "/path/to/ca.pem"