#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's rabbitmq_config.py module.

These tests verify that RabbitMQ configuration correctly sets up connection parameters,
exchange and queue configurations, message consumption options, and security settings.
The tests ensure that messaging works correctly for OCR processing with proper security
and reliability features.
"""

import os
import ssl
import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Optional

# Import Environment enum from conftest
from conftest import Environment

# Import the module under test
from src.config.rabbitmq_config import (
    get_rabbitmq_config,
    get_rabbitmq_connection_parameters,
    get_rabbitmq_exchange_config,
    get_rabbitmq_queue_config,
    get_rabbitmq_consumer_config,
    get_rabbitmq_publisher_config,
    get_rabbitmq_retry_config,
    get_message_serializer,
    get_message_deserializer,
    create_ocr_result_message,
    DEFAULT_RABBITMQ_CONFIG
)


class TestRabbitMQConfig:
    """Test suite for the RabbitMQ configuration module."""

    def test_default_config_values(self):
        """Test that default configuration values are set correctly when no environment variables are provided."""
        # Clear all relevant environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Get the default configuration
            config = get_rabbitmq_config()
            
            # Check default values
            assert config["host"] == "localhost"
            assert config["port"] == 5671  # Default to TLS port
            assert config["username"] == "guest"
            assert config["password"] == "guest"
            assert config["vhost"] == "/"
            assert config["exchange"] == "mca.documents"
            assert config["queue_data_extraction"] == "data-extraction"
            assert config["queue_data_processing"] == "data-processing"
            assert config["routing_key"] == "ocr.result"
            assert config["ssl"] is True  # Default to enabled
            assert config["heartbeat"] == 60
            assert config["connection_timeout"] == 30
            assert config["prefetch_count"] == 10

    def test_config_from_environment_variables(self, mock_env_vars):
        """Test that configuration values are correctly loaded from environment variables."""
        # Set environment variables
        env_vars = {
            "RABBITMQ_HOST": "rabbitmq.test",
            "RABBITMQ_PORT": "5672",
            "RABBITMQ_USERNAME": "test-user",
            "RABBITMQ_PASSWORD": "test-password",
            "RABBITMQ_VHOST": "/test",
            "RABBITMQ_EXCHANGE": "test-exchange",
            "RABBITMQ_QUEUE_DATA_EXTRACTION": "test-extraction",
            "RABBITMQ_QUEUE_DATA_PROCESSING": "test-processing",
            "RABBITMQ_ROUTING_KEY": "test.result",
            "RABBITMQ_SSL": "false",
            "RABBITMQ_HEARTBEAT": "30",
            "RABBITMQ_CONNECTION_TIMEOUT": "15",
            "RABBITMQ_PREFETCH_COUNT": "5"
        }
        mock_env_vars(env_vars)
        
        # Get the configuration
        config = get_rabbitmq_config()
        
        # Check that values match environment variables
        assert config["host"] == "rabbitmq.test"
        assert config["port"] == 5672
        assert config["username"] == "test-user"
        assert config["password"] == "test-password"
        assert config["vhost"] == "/test"
        assert config["exchange"] == "test-exchange"
        assert config["queue_data_extraction"] == "test-extraction"
        assert config["queue_data_processing"] == "test-processing"
        assert config["routing_key"] == "test.result"
        assert config["ssl"] is False
        assert config["heartbeat"] == 30
        assert config["connection_timeout"] == 15
        assert config["prefetch_count"] == 5

    def test_ssl_validation(self):
        """Test that SSL validation works correctly when SSL is enabled but certificate paths are not configured."""
        # Create a configuration with SSL enabled but no certificate paths
        config = DEFAULT_RABBITMQ_CONFIG.copy()
        config["ssl"] = True
        config["ssl_cert_path"] = None
        config["ssl_key_path"] = None
        config["ssl_ca_certs"] = None
        
        # Validation should fail
        with pytest.raises(ValueError, match="SSL is enabled but certificate paths are not properly configured"):
            # Use a lambda to call the function with our custom config
            with patch("src.config.rabbitmq_config.DEFAULT_RABBITMQ_CONFIG", config):
                get_rabbitmq_config()

    def test_connection_parameters_without_ssl(self):
        """Test that connection parameters are correctly configured without SSL."""
        # Create a configuration with SSL disabled
        config = {
            "host": "rabbitmq.test",
            "port": 5672,
            "vhost": "/test",
            "username": "test-user",
            "password": "test-password",
            "heartbeat": 30,
            "connection_timeout": 15,
            "ssl": False
        }
        
        # Get connection parameters
        params = get_rabbitmq_connection_parameters(config)
        
        # Check connection parameters
        assert params["host"] == "rabbitmq.test"
        assert params["port"] == 5672
        assert params["virtual_host"] == "/test"
        assert params["credentials"]["username"] == "test-user"
        assert params["credentials"]["password"] == "test-password"
        assert params["heartbeat"] == 30
        assert params["connection_timeout"] == 15
        assert "ssl_options" not in params
        assert params["client_properties"]["connection_name"] == "ocr-service"

    def test_connection_parameters_with_ssl(self):
        """Test that connection parameters are correctly configured with SSL."""
        # Create a configuration with SSL enabled
        config = {
            "host": "rabbitmq.test",
            "port": 5671,
            "vhost": "/test",
            "username": "test-user",
            "password": "test-password",
            "heartbeat": 30,
            "connection_timeout": 15,
            "ssl": True,
            "ssl_cert_path": "/path/to/cert.pem",
            "ssl_key_path": "/path/to/key.pem",
            "ssl_ca_certs": "/path/to/ca.pem"
        }
        
        # Mock ssl.create_default_context and ssl.SSLContext
        mock_ssl_context = MagicMock()
        with patch("ssl.create_default_context", return_value=mock_ssl_context) as mock_create_context:
            # Get connection parameters
            params = get_rabbitmq_connection_parameters(config)
            
            # Check that SSL context was created correctly
            mock_create_context.assert_called_once_with(cafile=config["ssl_ca_certs"])
            mock_ssl_context.load_cert_chain.assert_called_once_with(
                certfile=config["ssl_cert_path"],
                keyfile=config["ssl_key_path"]
            )
            assert mock_ssl_context.check_hostname is True
            assert mock_ssl_context.verify_mode == ssl.CERT_REQUIRED
            
            # Check connection parameters
            assert params["host"] == "rabbitmq.test"
            assert params["port"] == 5671
            assert params["virtual_host"] == "/test"
            assert params["credentials"]["username"] == "test-user"
            assert params["credentials"]["password"] == "test-password"
            assert params["heartbeat"] == 30
            assert params["connection_timeout"] == 15
            assert params["ssl_options"]["context"] == mock_ssl_context

    def test_exchange_config(self):
        """Test that exchange configuration is correctly set up."""
        # Create a configuration
        config = {
            "exchange": "test-exchange"
        }
        
        # Get exchange configuration
        exchange_config = get_rabbitmq_exchange_config(config)
        
        # Check exchange configuration
        assert exchange_config["exchange"] == "test-exchange"
        assert exchange_config["exchange_type"] == "fanout"  # As specified in the technical spec
        assert exchange_config["durable"] is True
        assert exchange_config["auto_delete"] is False

    def test_queue_config(self):
        """Test that queue configuration is correctly set up."""
        # Create a configuration
        config = {
            "exchange": "test-exchange",
            "queue_data_extraction": "test-extraction",
            "queue_data_processing": "test-processing"
        }
        
        # Get queue configuration
        queue_config = get_rabbitmq_queue_config(config)
        
        # Check data extraction queue configuration
        data_extraction = queue_config["data_extraction"]
        assert data_extraction["queue"] == "test-extraction"
        assert data_extraction["durable"] is True
        assert data_extraction["exclusive"] is False
        assert data_extraction["auto_delete"] is False
        assert "x-dead-letter-exchange" in data_extraction["arguments"]
        assert data_extraction["arguments"]["x-dead-letter-exchange"] == "test-exchange.dlx"
        assert "x-message-ttl" in data_extraction["arguments"]
        assert data_extraction["arguments"]["x-message-ttl"] == 1000 * 60 * 60 * 24  # 24 hours
        
        # Check data processing queue configuration
        data_processing = queue_config["data_processing"]
        assert data_processing["queue"] == "test-processing"
        assert data_processing["durable"] is True
        assert data_processing["exclusive"] is False
        assert data_processing["auto_delete"] is False
        assert "x-dead-letter-exchange" in data_processing["arguments"]
        assert data_processing["arguments"]["x-dead-letter-exchange"] == "test-exchange.dlx"
        assert "x-message-ttl" in data_processing["arguments"]
        assert data_processing["arguments"]["x-message-ttl"] == 1000 * 60 * 60 * 24  # 24 hours

    def test_consumer_config(self):
        """Test that consumer configuration is correctly set up."""
        # Create a configuration
        config = {
            "prefetch_count": 5
        }
        
        # Get consumer configuration
        consumer_config = get_rabbitmq_consumer_config(config)
        
        # Check consumer configuration
        assert consumer_config["prefetch_count"] == 5
        assert consumer_config["no_ack"] is False  # Require explicit acknowledgement

    def test_publisher_config(self):
        """Test that publisher configuration is correctly set up."""
        # Create a configuration
        config = {}
        
        # Get publisher configuration
        publisher_config = get_rabbitmq_publisher_config(config)
        
        # Check publisher configuration
        assert publisher_config["mandatory"] is True
        assert publisher_config["properties"]["delivery_mode"] == 2  # Persistent
        assert publisher_config["properties"]["content_type"] == "application/json"

    def test_retry_config(self):
        """Test that retry configuration is correctly set up."""
        # Set environment variables
        with patch.dict(os.environ, {
            "RABBITMQ_MAX_RETRIES": "10",
            "RABBITMQ_INITIAL_DELAY": "2.0",
            "RABBITMQ_MAX_DELAY": "60.0",
            "RABBITMQ_BACKOFF_FACTOR": "3.0"
        }):
            # Get retry configuration
            retry_config = get_rabbitmq_retry_config()
            
            # Check retry configuration
            assert retry_config["max_retries"] == 10
            assert retry_config["initial_delay"] == 2.0
            assert retry_config["max_delay"] == 60.0
            assert retry_config["backoff_factor"] == 3.0

    def test_message_serializer(self):
        """Test that message serializer correctly serializes Python objects to JSON bytes."""
        # Get message serializer
        serializer = get_message_serializer()
        
        # Create a test message
        message = {
            "document_id": "doc-123",
            "extracted_data": {"field1": "value1", "field2": "value2"},
            "confidence_scores": {"field1": 0.95, "field2": 0.85},
            "low_confidence_fields": ["field2"],
            "requires_review": True
        }
        
        # Serialize the message
        serialized = serializer(message)
        
        # Check that the result is bytes
        assert isinstance(serialized, bytes)
        
        # Check that the serialized message can be deserialized back to the original message
        deserialized = json.loads(serialized.decode('utf-8'))
        assert deserialized == message

    def test_message_deserializer(self):
        """Test that message deserializer correctly deserializes JSON bytes to Python objects."""
        # Get message deserializer
        deserializer = get_message_deserializer()
        
        # Create a test message
        message = {
            "document_id": "doc-123",
            "extracted_data": {"field1": "value1", "field2": "value2"},
            "confidence_scores": {"field1": 0.95, "field2": 0.85},
            "low_confidence_fields": ["field2"],
            "requires_review": True
        }
        
        # Serialize the message to JSON bytes
        serialized = json.dumps(message).encode('utf-8')
        
        # Deserialize the message
        deserialized = deserializer(serialized)
        
        # Check that the deserialized message matches the original message
        assert deserialized == message
        
        # Test with invalid JSON
        with pytest.raises(json.JSONDecodeError):
            deserializer(b'invalid json')

    def test_create_ocr_result_message(self):
        """Test that create_ocr_result_message creates a standardized OCR result message."""
        # Create test data
        document_id = "doc-123"
        extracted_data = {"field1": "value1", "field2": "value2"}
        confidence_scores = {"field1": 0.95, "field2": 0.85}
        low_confidence_fields = ["field2"]
        
        # Create OCR result message
        message = create_ocr_result_message(
            document_id=document_id,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores,
            low_confidence_fields=low_confidence_fields
        )
        
        # Check message structure
        assert message["document_id"] == document_id
        assert message["extracted_data"] == extracted_data
        assert message["confidence_scores"] == confidence_scores
        assert message["low_confidence_fields"] == low_confidence_fields
        assert message["requires_review"] is True
        assert "processing_timestamp" in message
        
        # Test with no low confidence fields
        message = create_ocr_result_message(
            document_id=document_id,
            extracted_data=extracted_data,
            confidence_scores=confidence_scores
        )
        
        assert message["low_confidence_fields"] == []
        assert message["requires_review"] is False


class TestRabbitMQConfigWithFixtures:
    """Test suite for RabbitMQ configuration using pytest fixtures."""

    def test_development_environment(self, env_vars):
        """Test RabbitMQ configuration in development environment."""
        # Get the configuration
        config = get_rabbitmq_config()
        
        # Check environment-specific values
        assert config["host"] == "localhost"
        assert config["port"] == 5672  # Non-TLS port in development
        assert config["ssl"] is False  # SSL disabled in development

    @pytest.mark.parametrize("env_vars", [Environment.STAGING], indirect=True)
    def test_staging_environment(self, env_vars):
        """Test RabbitMQ configuration in staging environment."""
        # Get the configuration
        config = get_rabbitmq_config()
        
        # Check environment-specific values
        assert config["host"] == "rabbitmq.staging"
        assert config["port"] == 5671  # TLS port in staging
        assert config["ssl"] is True  # SSL enabled in staging
        assert config["ssl_cert_path"] == "/app/certs/client.pem"
        assert config["ssl_key_path"] == "/app/certs/client.key"
        assert config["ssl_ca_certs"] == "/app/certs/ca.pem"

    @pytest.mark.parametrize("env_vars", [Environment.PRODUCTION], indirect=True)
    def test_production_environment(self, env_vars):
        """Test RabbitMQ configuration in production environment."""
        # Get the configuration
        config = get_rabbitmq_config()
        
        # Check environment-specific values
        assert config["host"] == "rabbitmq.production"
        assert config["port"] == 5671  # TLS port in production
        assert config["ssl"] is True  # SSL enabled in production
        assert config["ssl_cert_path"] == "/app/certs/client.pem"
        assert config["ssl_key_path"] == "/app/certs/client.key"
        assert config["ssl_ca_certs"] == "/app/certs/ca.pem"
        assert config["prefetch_count"] == 20  # Higher prefetch in production

    def test_connection_error_handling(self):
        """Test that connection error handling is correctly configured."""
        # Get retry configuration
        retry_config = get_rabbitmq_retry_config()
        
        # Check retry configuration
        assert "max_retries" in retry_config
        assert "initial_delay" in retry_config
        assert "max_delay" in retry_config
        assert "backoff_factor" in retry_config
        
        # Check that retry values are reasonable
        assert retry_config["max_retries"] > 0
        assert retry_config["initial_delay"] > 0
        assert retry_config["max_delay"] > retry_config["initial_delay"]
        assert retry_config["backoff_factor"] > 1.0

    def test_message_serialization_with_complex_types(self):
        """Test that message serializer correctly handles complex Python types."""
        # Get message serializer
        serializer = get_message_serializer()
        
        # Create a test message with complex types
        from datetime import datetime, date
        from decimal import Decimal
        
        message = {
            "document_id": "doc-123",
            "timestamp": datetime.now(),
            "date": date.today(),
            "amount": Decimal("123.45"),
            "nested": {
                "timestamp": datetime.now(),
                "date": date.today(),
                "amount": Decimal("678.90")
            }
        }
        
        # Serialize the message
        serialized = serializer(message)
        
        # Check that the result is bytes
        assert isinstance(serialized, bytes)
        
        # Check that the serialized message can be deserialized
        deserialized = json.loads(serialized.decode('utf-8'))
        
        # Check that complex types were converted to strings
        assert isinstance(deserialized["timestamp"], str)
        assert isinstance(deserialized["date"], str)
        assert isinstance(deserialized["amount"], str)
        assert isinstance(deserialized["nested"]["timestamp"], str)
        assert isinstance(deserialized["nested"]["date"], str)
        assert isinstance(deserialized["nested"]["amount"], str)