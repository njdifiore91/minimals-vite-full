#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's rabbitmq_config.py module.

These tests verify that RabbitMQ configuration correctly sets up connection parameters,
exchange and queue configurations, message consumption options, and security settings.
Ensures that messaging works correctly for document processing.

Test coverage includes:
- RabbitMQ connection configuration with TLS
- Exchange and queue configuration
- Message consumption option configuration
- Connection error handling and recovery configuration
- Message serialization configuration
"""

import os
import json
import ssl
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module to test
from src.config.rabbitmq_config import (
    get_rabbitmq_config,
    get_rabbitmq_connection_parameters,
    get_rabbitmq_exchange_config,
    get_rabbitmq_queue_config,
    get_rabbitmq_consumer_config,
    get_rabbitmq_publisher_config,
    get_rabbitmq_retry_config,
    get_message_serializer,
    get_message_deserializer
)

# Import configuration types
from src.types.config import RabbitMQConfig


# ===== Test RabbitMQ Configuration Loading =====

def test_get_rabbitmq_config_defaults():
    """Test that default RabbitMQ configuration is loaded correctly."""
    with patch.dict(os.environ, {}, clear=True):
        config = get_rabbitmq_config()
        
        # Verify default values
        assert config["host"] == "localhost"
        assert config["port"] == 5671  # Default to TLS port
        assert config["username"] == "guest"
        assert config["password"] == "guest"
        assert config["vhost"] == "/"
        assert config["exchange"] == "mca.documents"
        assert config["queue_document_processing"] == "document-processing"
        assert config["queue_data_extraction"] == "data-extraction"
        assert config["routing_key"] == "document.new"
        assert config["ssl"] is True  # Default to enabled
        assert config["heartbeat"] == 60
        assert config["connection_timeout"] == 30
        assert config["prefetch_count"] == 10


def test_get_rabbitmq_config_with_env_vars():
    """Test that RabbitMQ configuration can be overridden with environment variables."""
    with patch.dict(os.environ, {
        "RABBITMQ_HOST": "rabbitmq.example.com",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "test-user",
        "RABBITMQ_PASSWORD": "test-password",
        "RABBITMQ_VHOST": "/test",
        "RABBITMQ_EXCHANGE": "test-exchange",
        "RABBITMQ_QUEUE_DOCUMENT_PROCESSING": "test-document-processing",
        "RABBITMQ_QUEUE_DATA_EXTRACTION": "test-data-extraction",
        "RABBITMQ_ROUTING_KEY": "test.document.new",
        "RABBITMQ_SSL": "false",
        "RABBITMQ_HEARTBEAT": "30",
        "RABBITMQ_CONNECTION_TIMEOUT": "15",
        "RABBITMQ_PREFETCH_COUNT": "5"
    }):
        config = get_rabbitmq_config()
        
        # Verify overridden values
        assert config["host"] == "rabbitmq.example.com"
        assert config["port"] == 5672
        assert config["username"] == "test-user"
        assert config["password"] == "test-password"
        assert config["vhost"] == "/test"
        assert config["exchange"] == "test-exchange"
        assert config["queue_document_processing"] == "test-document-processing"
        assert config["queue_data_extraction"] == "test-data-extraction"
        assert config["routing_key"] == "test.document.new"
        assert config["ssl"] is False
        assert config["heartbeat"] == 30
        assert config["connection_timeout"] == 15
        assert config["prefetch_count"] == 5


def test_get_rabbitmq_config_ssl_validation():
    """Test that SSL configuration is validated correctly."""
    # Test with SSL enabled but missing certificate paths
    with patch.dict(os.environ, {
        "RABBITMQ_SSL": "true",
        "RABBITMQ_SSL_CERT_PATH": "",
        "RABBITMQ_SSL_KEY_PATH": "",
        "RABBITMQ_SSL_CA_CERTS": ""
    }):
        with pytest.raises(ValueError, match="SSL is enabled but certificate paths are not properly configured"):
            get_rabbitmq_config()
    
    # Test with SSL enabled and valid certificate paths
    with patch.dict(os.environ, {
        "RABBITMQ_SSL": "true",
        "RABBITMQ_SSL_CERT_PATH": "/path/to/cert.pem",
        "RABBITMQ_SSL_KEY_PATH": "/path/to/key.pem",
        "RABBITMQ_SSL_CA_CERTS": "/path/to/ca.pem"
    }):
        config = get_rabbitmq_config()
        assert config["ssl"] is True
        assert config["ssl_cert_path"] == "/path/to/cert.pem"
        assert config["ssl_key_path"] == "/path/to/key.pem"
        assert config["ssl_ca_certs"] == "/path/to/ca.pem"


# ===== Test RabbitMQ Connection Parameters =====

def test_get_rabbitmq_connection_parameters_without_ssl():
    """Test that connection parameters are correctly configured without SSL."""
    config = {
        "host": "localhost",
        "port": 5672,
        "vhost": "/",
        "username": "guest",
        "password": "guest",
        "ssl": False,
        "heartbeat": 60,
        "connection_timeout": 30
    }
    
    params = get_rabbitmq_connection_parameters(config)
    
    # Verify connection parameters
    assert params["host"] == "localhost"
    assert params["port"] == 5672
    assert params["virtual_host"] == "/"
    assert params["credentials"]["username"] == "guest"
    assert params["credentials"]["password"] == "guest"
    assert params["heartbeat"] == 60
    assert params["connection_timeout"] == 30
    assert "client_properties" in params
    assert params["client_properties"]["connection_name"] == "document-service"
    assert "ssl_options" not in params


def test_get_rabbitmq_connection_parameters_with_ssl():
    """Test that connection parameters are correctly configured with SSL."""
    # Mock SSL context
    mock_ssl_context = MagicMock(spec=ssl.SSLContext)
    
    with patch("ssl.create_default_context", return_value=mock_ssl_context) as mock_create_context:
        config = {
            "host": "rabbitmq.example.com",
            "port": 5671,
            "vhost": "/",
            "username": "test-user",
            "password": "test-password",
            "ssl": True,
            "ssl_cert_path": "/path/to/cert.pem",
            "ssl_key_path": "/path/to/key.pem",
            "ssl_ca_certs": "/path/to/ca.pem",
            "heartbeat": 60,
            "connection_timeout": 30
        }
        
        params = get_rabbitmq_connection_parameters(config)
        
        # Verify connection parameters
        assert params["host"] == "rabbitmq.example.com"
        assert params["port"] == 5671
        assert params["virtual_host"] == "/"
        assert params["credentials"]["username"] == "test-user"
        assert params["credentials"]["password"] == "test-password"
        assert params["heartbeat"] == 60
        assert params["connection_timeout"] == 30
        assert "client_properties" in params
        assert params["client_properties"]["connection_name"] == "document-service"
        
        # Verify SSL options
        assert "ssl_options" in params
        assert params["ssl_options"]["context"] == mock_ssl_context
        
        # Verify SSL context configuration
        mock_create_context.assert_called_once_with(cafile="/path/to/ca.pem")
        mock_ssl_context.load_cert_chain.assert_called_once_with(
            certfile="/path/to/cert.pem",
            keyfile="/path/to/key.pem"
        )
        assert mock_ssl_context.check_hostname is True
        assert mock_ssl_context.verify_mode == ssl.CERT_REQUIRED


# ===== Test RabbitMQ Exchange Configuration =====

def test_get_rabbitmq_exchange_config():
    """Test that exchange configuration is correctly configured."""
    config = {
        "exchange": "mca.documents"
    }
    
    exchange_config = get_rabbitmq_exchange_config(config)
    
    # Verify exchange configuration
    assert exchange_config["exchange"] == "mca.documents"
    assert exchange_config["exchange_type"] == "fanout"  # As specified in the technical spec
    assert exchange_config["durable"] is True
    assert exchange_config["auto_delete"] is False


def test_get_rabbitmq_exchange_config_custom():
    """Test that exchange configuration can be customized."""
    config = {
        "exchange": "custom.exchange"
    }
    
    exchange_config = get_rabbitmq_exchange_config(config)
    
    # Verify exchange configuration
    assert exchange_config["exchange"] == "custom.exchange"
    assert exchange_config["exchange_type"] == "fanout"
    assert exchange_config["durable"] is True
    assert exchange_config["auto_delete"] is False


# ===== Test RabbitMQ Queue Configuration =====

def test_get_rabbitmq_queue_config():
    """Test that queue configuration is correctly configured."""
    config = {
        "exchange": "mca.documents",
        "queue_document_processing": "document-processing",
        "queue_data_extraction": "data-extraction"
    }
    
    queue_config = get_rabbitmq_queue_config(config)
    
    # Verify document processing queue configuration
    assert "document_processing" in queue_config
    assert queue_config["document_processing"]["queue"] == "document-processing"
    assert queue_config["document_processing"]["durable"] is True
    assert queue_config["document_processing"]["exclusive"] is False
    assert queue_config["document_processing"]["auto_delete"] is False
    assert "arguments" in queue_config["document_processing"]
    assert queue_config["document_processing"]["arguments"]["x-dead-letter-exchange"] == "mca.documents.dlx"
    assert queue_config["document_processing"]["arguments"]["x-message-ttl"] == 1000 * 60 * 60 * 24  # 24 hours
    
    # Verify data extraction queue configuration
    assert "data_extraction" in queue_config
    assert queue_config["data_extraction"]["queue"] == "data-extraction"
    assert queue_config["data_extraction"]["durable"] is True
    assert queue_config["data_extraction"]["exclusive"] is False
    assert queue_config["data_extraction"]["auto_delete"] is False
    assert "arguments" in queue_config["data_extraction"]
    assert queue_config["data_extraction"]["arguments"]["x-dead-letter-exchange"] == "mca.documents.dlx"
    assert queue_config["data_extraction"]["arguments"]["x-message-ttl"] == 1000 * 60 * 60 * 24  # 24 hours


def test_get_rabbitmq_queue_config_custom():
    """Test that queue configuration can be customized."""
    config = {
        "exchange": "custom.exchange",
        "queue_document_processing": "custom-document-processing",
        "queue_data_extraction": "custom-data-extraction"
    }
    
    queue_config = get_rabbitmq_queue_config(config)
    
    # Verify document processing queue configuration
    assert queue_config["document_processing"]["queue"] == "custom-document-processing"
    assert queue_config["document_processing"]["arguments"]["x-dead-letter-exchange"] == "custom.exchange.dlx"
    
    # Verify data extraction queue configuration
    assert queue_config["data_extraction"]["queue"] == "custom-data-extraction"
    assert queue_config["data_extraction"]["arguments"]["x-dead-letter-exchange"] == "custom.exchange.dlx"


# ===== Test RabbitMQ Consumer Configuration =====

def test_get_rabbitmq_consumer_config():
    """Test that consumer configuration is correctly configured."""
    config = {
        "prefetch_count": 10
    }
    
    consumer_config = get_rabbitmq_consumer_config(config)
    
    # Verify consumer configuration
    assert consumer_config["prefetch_count"] == 10
    assert consumer_config["no_ack"] is False  # Require explicit acknowledgement


def test_get_rabbitmq_consumer_config_custom():
    """Test that consumer configuration can be customized."""
    config = {
        "prefetch_count": 20
    }
    
    consumer_config = get_rabbitmq_consumer_config(config)
    
    # Verify consumer configuration
    assert consumer_config["prefetch_count"] == 20
    assert consumer_config["no_ack"] is False


# ===== Test RabbitMQ Publisher Configuration =====

def test_get_rabbitmq_publisher_config():
    """Test that publisher configuration is correctly configured."""
    config = {}
    
    publisher_config = get_rabbitmq_publisher_config(config)
    
    # Verify publisher configuration
    assert publisher_config["mandatory"] is True  # Raise exception if message cannot be routed
    assert "properties" in publisher_config
    assert publisher_config["properties"]["delivery_mode"] == 2  # Persistent
    assert publisher_config["properties"]["content_type"] == "application/json"  # JSON serialization


# ===== Test RabbitMQ Retry Configuration =====

def test_get_rabbitmq_retry_config_defaults():
    """Test that retry configuration defaults are correctly configured."""
    with patch.dict(os.environ, {}, clear=True):
        retry_config = get_rabbitmq_retry_config()
        
        # Verify retry configuration defaults
        assert retry_config["max_retries"] == 5
        assert retry_config["initial_delay"] == 1.0
        assert retry_config["max_delay"] == 30.0
        assert retry_config["backoff_factor"] == 2.0


def test_get_rabbitmq_retry_config_with_env_vars():
    """Test that retry configuration can be overridden with environment variables."""
    with patch.dict(os.environ, {
        "RABBITMQ_MAX_RETRIES": "10",
        "RABBITMQ_INITIAL_DELAY": "2.0",
        "RABBITMQ_MAX_DELAY": "60.0",
        "RABBITMQ_BACKOFF_FACTOR": "3.0"
    }):
        retry_config = get_rabbitmq_retry_config()
        
        # Verify overridden values
        assert retry_config["max_retries"] == 10
        assert retry_config["initial_delay"] == 2.0
        assert retry_config["max_delay"] == 60.0
        assert retry_config["backoff_factor"] == 3.0


# ===== Test Message Serialization =====

def test_get_message_serializer():
    """Test that message serializer correctly serializes messages to JSON bytes."""
    serializer = get_message_serializer()
    
    # Test with a simple message
    message = {"id": "123", "type": "invoice", "metadata": {"pages": 2}}
    serialized = serializer(message)
    
    # Verify serialization
    assert isinstance(serialized, bytes)
    assert json.loads(serialized.decode("utf-8")) == message
    
    # Test with a message containing non-serializable objects
    message_with_date = {"id": "123", "created_at": MagicMock()}
    serialized = serializer(message_with_date)
    
    # Verify serialization (should convert non-serializable objects to strings)
    assert isinstance(serialized, bytes)
    deserialized = json.loads(serialized.decode("utf-8"))
    assert deserialized["id"] == "123"
    assert isinstance(deserialized["created_at"], str)


def test_get_message_deserializer():
    """Test that message deserializer correctly deserializes JSON bytes to Python objects."""
    deserializer = get_message_deserializer()
    
    # Test with a simple message
    message = {"id": "123", "type": "invoice", "metadata": {"pages": 2}}
    serialized = json.dumps(message).encode("utf-8")
    deserialized = deserializer(serialized)
    
    # Verify deserialization
    assert deserialized == message
    
    # Test with invalid JSON
    with pytest.raises(json.JSONDecodeError):
        deserializer(b"invalid json")


# ===== Test Integration Between Serializer and Deserializer =====

def test_serializer_deserializer_integration():
    """Test that serializer and deserializer work together correctly."""
    serializer = get_message_serializer()
    deserializer = get_message_deserializer()
    
    # Test with various message types
    messages = [
        {"id": "123", "type": "invoice"},
        {"id": "456", "type": "bank_statement", "metadata": {"pages": 5, "account": "12345"}},
        [1, 2, 3, 4, 5],
        "simple string",
        123,
        True,
        None
    ]
    
    for message in messages:
        serialized = serializer(message)
        deserialized = deserializer(serialized)
        assert deserialized == message