#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's rabbitmq_config.py module.

This module contains tests that verify the RabbitMQ configuration correctly sets up
connection parameters, exchange and queue configurations, message consumption options,
and security settings. It ensures that messaging works correctly for OCR processing.
"""

import os
import ssl
import json
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the module under test
from src.config import rabbitmq_config
from src.types.messages import (
    ExchangeType, ExchangeConfig, QueueConfig, ConnectionConfig,
    RetryConfig, MessagePayload, MessageHeaders, MessageSerializer
)
from src.types.config import RabbitMQConfig


# ===== Test Environment Variable Loading =====

def test_environment_variables_loading(env_vars):
    """
    Test that environment variables are correctly loaded into configuration.
    """
    # Set environment variables
    env_vars['RABBITMQ_HOST'] = 'test-host'
    env_vars['RABBITMQ_PORT'] = '5673'
    env_vars['RABBITMQ_VIRTUAL_HOST'] = '/test'
    env_vars['RABBITMQ_USERNAME'] = 'test-user'
    env_vars['RABBITMQ_PASSWORD'] = 'test-password'
    env_vars['RABBITMQ_EXCHANGE_NAME'] = 'test-exchange'
    env_vars['RABBITMQ_QUEUE_NAME'] = 'test-queue'
    
    # Reload the module to apply environment variables
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_PORT', 5673), \
         patch.object(rabbitmq_config, 'RABBITMQ_VHOST', '/test'), \
         patch.object(rabbitmq_config, 'RABBITMQ_USER', 'test-user'), \
         patch.object(rabbitmq_config, 'RABBITMQ_PASS', 'test-password'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'):
        
        # Get connection parameters
        params = rabbitmq_config.get_connection_parameters()
        
        # Verify parameters
        assert params['host'] == 'test-host'
        assert params['port'] == 5673
        assert params['virtual_host'] == '/test'
        assert params['credentials']['username'] == 'test-user'
        assert params['credentials']['password'] == 'test-password'


def test_default_values(clear_env_vars):
    """
    Test that default values are used when environment variables are not set.
    """
    # Clear relevant environment variables
    clear_env_vars([
        'RABBITMQ_HOST',
        'RABBITMQ_PORT',
        'RABBITMQ_VIRTUAL_HOST',
        'RABBITMQ_USERNAME',
        'RABBITMQ_PASSWORD',
        'RABBITMQ_EXCHANGE_NAME',
        'RABBITMQ_QUEUE_NAME'
    ])
    
    # Reload the module to apply default values
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', rabbitmq_config.DEFAULT_HOST), \
         patch.object(rabbitmq_config, 'RABBITMQ_PORT', rabbitmq_config.DEFAULT_PORT), \
         patch.object(rabbitmq_config, 'RABBITMQ_VHOST', rabbitmq_config.DEFAULT_VHOST), \
         patch.object(rabbitmq_config, 'RABBITMQ_USER', rabbitmq_config.DEFAULT_USER), \
         patch.object(rabbitmq_config, 'RABBITMQ_PASS', rabbitmq_config.DEFAULT_PASS), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', rabbitmq_config.DEFAULT_EXCHANGE), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', rabbitmq_config.DEFAULT_QUEUE):
        
        # Get connection parameters
        params = rabbitmq_config.get_connection_parameters()
        
        # Verify default parameters
        assert params['host'] == rabbitmq_config.DEFAULT_HOST
        assert params['port'] == rabbitmq_config.DEFAULT_PORT
        assert params['virtual_host'] == rabbitmq_config.DEFAULT_VHOST
        assert params['credentials']['username'] == rabbitmq_config.DEFAULT_USER
        assert params['credentials']['password'] == rabbitmq_config.DEFAULT_PASS


# ===== Test SSL/TLS Configuration =====

def test_ssl_context_creation_with_ssl_enabled(env_vars):
    """
    Test that SSL context is correctly created when SSL is enabled.
    """
    # Set SSL environment variables
    env_vars['RABBITMQ_USE_SSL'] = 'true'
    env_vars['RABBITMQ_SSL_VERIFY'] = 'true'
    env_vars['RABBITMQ_SSL_CERT_PATH'] = '/path/to/cert.pem'
    env_vars['RABBITMQ_SSL_KEY_PATH'] = '/path/to/key.pem'
    env_vars['RABBITMQ_SSL_CA_CERTS'] = '/path/to/ca.pem'
    
    # Mock SSL context creation
    mock_context = MagicMock(spec=ssl.SSLContext)
    
    with patch('ssl.create_default_context', return_value=mock_context), \
         patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_VERIFY', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_CERT', '/path/to/cert.pem'), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_KEY', '/path/to/key.pem'), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_CA', '/path/to/ca.pem'):
        
        # Get SSL context
        context = rabbitmq_config.get_ssl_context()
        
        # Verify context configuration
        assert context is not None
        mock_context.load_verify_locations.assert_called_once_with(cafile='/path/to/ca.pem')
        mock_context.load_cert_chain.assert_called_once_with('/path/to/cert.pem', '/path/to/key.pem')
        assert mock_context.verify_mode == ssl.CERT_REQUIRED
        assert mock_context.minimum_version == ssl.TLSVersion.TLSv1_2


def test_ssl_context_creation_with_ssl_disabled(env_vars):
    """
    Test that SSL context is not created when SSL is disabled.
    """
    # Set SSL environment variables
    env_vars['RABBITMQ_USE_SSL'] = 'false'
    
    with patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', False):
        # Get SSL context
        context = rabbitmq_config.get_ssl_context()
        
        # Verify context is None
        assert context is None


def test_ssl_context_with_verification_disabled(env_vars):
    """
    Test SSL context creation with certificate verification disabled.
    """
    # Set SSL environment variables
    env_vars['RABBITMQ_USE_SSL'] = 'true'
    env_vars['RABBITMQ_SSL_VERIFY'] = 'false'
    
    # Mock SSL context creation
    mock_context = MagicMock(spec=ssl.SSLContext)
    
    with patch('ssl.create_default_context', return_value=mock_context), \
         patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_VERIFY', False):
        
        # Get SSL context
        context = rabbitmq_config.get_ssl_context()
        
        # Verify context configuration
        assert context is not None
        assert mock_context.verify_mode == ssl.CERT_NONE
        assert mock_context.check_hostname is False


# ===== Test Exchange and Queue Configuration =====

def test_exchange_configuration():
    """
    Test that exchange configuration is correctly set up.
    """
    # Verify exchange configuration
    assert rabbitmq_config.EXCHANGE_CONFIG['name'] == rabbitmq_config.RABBITMQ_EXCHANGE
    assert rabbitmq_config.EXCHANGE_CONFIG['type'] == ExchangeType.FANOUT.value
    assert rabbitmq_config.EXCHANGE_CONFIG['durable'] is True
    assert rabbitmq_config.EXCHANGE_CONFIG['auto_delete'] is False


def test_queue_configuration():
    """
    Test that queue configuration is correctly set up.
    """
    # Verify queue configuration
    assert rabbitmq_config.QUEUE_CONFIG['name'] == rabbitmq_config.RABBITMQ_QUEUE
    assert rabbitmq_config.QUEUE_CONFIG['durable'] is True
    assert rabbitmq_config.QUEUE_CONFIG['exclusive'] is False
    assert rabbitmq_config.QUEUE_CONFIG['auto_delete'] is False
    assert 'x-message-ttl' in rabbitmq_config.QUEUE_CONFIG['arguments']
    assert 'x-dead-letter-exchange' in rabbitmq_config.QUEUE_CONFIG['arguments']
    assert 'x-dead-letter-routing-key' in rabbitmq_config.QUEUE_CONFIG['arguments']
    assert rabbitmq_config.QUEUE_CONFIG['prefetch_count'] == 10
    assert rabbitmq_config.QUEUE_CONFIG['consumer_tag'] == rabbitmq_config.DEFAULT_CONSUMER_TAG


def test_dead_letter_configuration():
    """
    Test that dead letter exchange and queue configuration is correctly set up.
    """
    # Verify dead letter exchange configuration
    assert rabbitmq_config.DEAD_LETTER_EXCHANGE_CONFIG['name'] == f"{rabbitmq_config.RABBITMQ_EXCHANGE}-dlx"
    assert rabbitmq_config.DEAD_LETTER_EXCHANGE_CONFIG['type'] == ExchangeType.DIRECT.value
    assert rabbitmq_config.DEAD_LETTER_EXCHANGE_CONFIG['durable'] is True
    assert rabbitmq_config.DEAD_LETTER_EXCHANGE_CONFIG['auto_delete'] is False
    
    # Verify dead letter queue configuration
    assert rabbitmq_config.DEAD_LETTER_QUEUE_CONFIG['name'] == f"{rabbitmq_config.RABBITMQ_QUEUE}-dlq"
    assert rabbitmq_config.DEAD_LETTER_QUEUE_CONFIG['durable'] is True
    assert rabbitmq_config.DEAD_LETTER_QUEUE_CONFIG['exclusive'] is False
    assert rabbitmq_config.DEAD_LETTER_QUEUE_CONFIG['auto_delete'] is False
    assert 'x-message-ttl' in rabbitmq_config.DEAD_LETTER_QUEUE_CONFIG['arguments']
    assert rabbitmq_config.DEAD_LETTER_QUEUE_CONFIG['arguments']['x-message-ttl'] == 604800000  # 7 days


# ===== Test Connection Parameters =====

def test_connection_parameters():
    """
    Test that connection parameters are correctly configured.
    """
    # Verify connection configuration
    assert rabbitmq_config.CONNECTION_CONFIG['host'] == rabbitmq_config.RABBITMQ_HOST
    assert rabbitmq_config.CONNECTION_CONFIG['port'] == rabbitmq_config.RABBITMQ_PORT
    assert rabbitmq_config.CONNECTION_CONFIG['virtual_host'] == rabbitmq_config.RABBITMQ_VHOST
    assert rabbitmq_config.CONNECTION_CONFIG['username'] == rabbitmq_config.RABBITMQ_USER
    assert rabbitmq_config.CONNECTION_CONFIG['password'] == rabbitmq_config.RABBITMQ_PASS
    assert rabbitmq_config.CONNECTION_CONFIG['heartbeat'] == 60
    assert rabbitmq_config.CONNECTION_CONFIG['blocked_connection_timeout'] == 300
    assert rabbitmq_config.CONNECTION_CONFIG['connection_attempts'] == 5
    assert rabbitmq_config.CONNECTION_CONFIG['retry_delay'] == 1.0
    assert rabbitmq_config.CONNECTION_CONFIG['ssl'] == rabbitmq_config.RABBITMQ_USE_SSL


def test_get_connection_parameters():
    """
    Test that get_connection_parameters returns the correct parameters.
    """
    # Get connection parameters
    params = rabbitmq_config.get_connection_parameters()
    
    # Verify parameters
    assert params['host'] == rabbitmq_config.RABBITMQ_HOST
    assert params['port'] == rabbitmq_config.RABBITMQ_PORT
    assert params['virtual_host'] == rabbitmq_config.RABBITMQ_VHOST
    assert params['credentials']['username'] == rabbitmq_config.RABBITMQ_USER
    assert params['credentials']['password'] == rabbitmq_config.RABBITMQ_PASS
    assert params['heartbeat'] == rabbitmq_config.CONNECTION_CONFIG['heartbeat']
    assert params['blocked_connection_timeout'] == rabbitmq_config.CONNECTION_CONFIG['blocked_connection_timeout']
    assert params['connection_attempts'] == rabbitmq_config.CONNECTION_CONFIG['connection_attempts']
    assert params['retry_delay'] == rabbitmq_config.CONNECTION_CONFIG['retry_delay']
    
    # Check SSL options if SSL is enabled
    if rabbitmq_config.RABBITMQ_USE_SSL:
        assert 'ssl_options' in params


# ===== Test Consumer and Publisher Options =====

def test_get_consumer_options():
    """
    Test that get_consumer_options returns the correct options.
    """
    # Get consumer options
    options = rabbitmq_config.get_consumer_options()
    
    # Verify options
    assert options['queue'] == rabbitmq_config.QUEUE_CONFIG['name']
    assert options['consumer_tag'] == rabbitmq_config.QUEUE_CONFIG['consumer_tag']
    assert options['exclusive'] == rabbitmq_config.QUEUE_CONFIG['exclusive']
    assert options['arguments'] == rabbitmq_config.QUEUE_CONFIG.get('arguments', {})


def test_get_publisher_options():
    """
    Test that get_publisher_options returns the correct options.
    """
    # Get publisher options
    options = rabbitmq_config.get_publisher_options()
    
    # Verify options
    assert options['exchange'] == rabbitmq_config.EXCHANGE_CONFIG['name']
    assert options['routing_key'] == ''  # Empty for fanout exchange
    assert options['mandatory'] is True
    assert options['properties'] == rabbitmq_config.DEFAULT_MESSAGE_PROPERTIES


# ===== Test Message Serialization =====

def test_serialize_message():
    """
    Test that serialize_message correctly serializes a message payload to JSON bytes.
    """
    # Create a test payload
    payload = {
        'document_id': 'test-doc-123',
        'application_id': 'test-app-456',
        'document_type': 'application_form',
        'storage_path': 's3://mca-documents-test/test-doc-123.pdf',
        'mime_type': 'application/pdf',
        'file_name': 'test-doc-123.pdf',
        'file_size': 1024,
        'created_at': '2023-01-01T12:00:00Z',
        'metadata': {'source': 'test'},
        'classification': {'type': 'application_form', 'confidence': 0.95}
    }
    
    # Serialize the payload
    serialized = rabbitmq_config.serialize_message(payload)
    
    # Verify serialization
    assert isinstance(serialized, bytes)
    deserialized = json.loads(serialized.decode('utf-8'))
    assert deserialized == payload


def test_deserialize_message():
    """
    Test that deserialize_message correctly deserializes JSON bytes to a message payload.
    """
    # Create a test payload
    payload = {
        'document_id': 'test-doc-123',
        'application_id': 'test-app-456',
        'document_type': 'application_form',
        'storage_path': 's3://mca-documents-test/test-doc-123.pdf',
        'mime_type': 'application/pdf',
        'file_name': 'test-doc-123.pdf',
        'file_size': 1024,
        'created_at': '2023-01-01T12:00:00Z',
        'metadata': {'source': 'test'},
        'classification': {'type': 'application_form', 'confidence': 0.95}
    }
    
    # Serialize and then deserialize the payload
    serialized = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    deserialized = rabbitmq_config.deserialize_message(serialized)
    
    # Verify deserialization
    assert deserialized == payload


# ===== Test Configuration Validation =====

def test_validate_rabbitmq_configuration_valid():
    """
    Test that validate_rabbitmq_configuration returns True for valid configuration.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'), \
         patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', False):
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is True


def test_validate_rabbitmq_configuration_missing_host():
    """
    Test that validate_rabbitmq_configuration returns False when host is missing.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', ''), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'), \
         patch.object(rabbitmq_config, 'logger') as mock_logger:
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is False
        mock_logger.error.assert_called_with("RabbitMQ host not configured")


def test_validate_rabbitmq_configuration_missing_exchange():
    """
    Test that validate_rabbitmq_configuration returns False when exchange is missing.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', ''), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'), \
         patch.object(rabbitmq_config, 'logger') as mock_logger:
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is False
        mock_logger.error.assert_called_with("RabbitMQ exchange not configured")


def test_validate_rabbitmq_configuration_missing_queue():
    """
    Test that validate_rabbitmq_configuration returns False when queue is missing.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', ''), \
         patch.object(rabbitmq_config, 'logger') as mock_logger:
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is False
        mock_logger.error.assert_called_with("RabbitMQ queue not configured")


def test_validate_rabbitmq_configuration_ssl_cert_without_key():
    """
    Test that validate_rabbitmq_configuration returns False when SSL certificate is provided without key.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'), \
         patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_CERT', '/path/to/cert.pem'), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_KEY', None), \
         patch.object(rabbitmq_config, 'logger') as mock_logger:
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is False
        mock_logger.error.assert_called_with("SSL certificate provided but key is missing")


def test_validate_rabbitmq_configuration_ssl_key_without_cert():
    """
    Test that validate_rabbitmq_configuration returns False when SSL key is provided without certificate.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'), \
         patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_CERT', None), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_KEY', '/path/to/key.pem'), \
         patch.object(rabbitmq_config, 'logger') as mock_logger:
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is False
        mock_logger.error.assert_called_with("SSL key provided but certificate is missing")


def test_validate_rabbitmq_configuration_ssl_verify_without_ca():
    """
    Test that validate_rabbitmq_configuration logs a warning when SSL verification is enabled but CA certificate is not provided.
    """
    with patch.object(rabbitmq_config, 'RABBITMQ_HOST', 'test-host'), \
         patch.object(rabbitmq_config, 'RABBITMQ_EXCHANGE', 'test-exchange'), \
         patch.object(rabbitmq_config, 'RABBITMQ_QUEUE', 'test-queue'), \
         patch.object(rabbitmq_config, 'RABBITMQ_USE_SSL', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_VERIFY', True), \
         patch.object(rabbitmq_config, 'RABBITMQ_SSL_CA', None), \
         patch.object(rabbitmq_config, 'logger') as mock_logger:
        
        # Validate configuration
        valid = rabbitmq_config.validate_rabbitmq_configuration()
        
        # Verify validation result
        assert valid is True  # Still valid, but with a warning
        mock_logger.warning.assert_called_with("SSL verification enabled but CA certificate not provided")


# ===== Test Connection Error Handling and Recovery =====

def test_retry_configuration():
    """
    Test that retry configuration is correctly set up.
    """
    # Verify retry configuration
    assert rabbitmq_config.RETRY_CONFIG['max_retries'] == 5
    assert rabbitmq_config.RETRY_CONFIG['initial_delay'] == 1.0
    assert rabbitmq_config.RETRY_CONFIG['max_delay'] == 30.0
    assert rabbitmq_config.RETRY_CONFIG['backoff_factor'] == 2.0
    assert 'ConnectionError' in rabbitmq_config.RETRY_CONFIG['retry_on_exceptions']
    assert 'ChannelError' in rabbitmq_config.RETRY_CONFIG['retry_on_exceptions']
    assert 'AMQPError' in rabbitmq_config.RETRY_CONFIG['retry_on_exceptions']
    assert 'TimeoutError' in rabbitmq_config.RETRY_CONFIG['retry_on_exceptions']


# ===== Test RabbitMQConfig Class =====

def test_rabbitmq_config_from_env(env_vars):
    """
    Test that RabbitMQConfig.from_env correctly loads configuration from environment variables.
    """
    # Set environment variables
    env_vars['RABBITMQ_HOST'] = 'test-host'
    env_vars['RABBITMQ_PORT'] = '5673'
    env_vars['RABBITMQ_VIRTUAL_HOST'] = '/test'
    env_vars['RABBITMQ_USERNAME'] = 'test-user'
    env_vars['RABBITMQ_PASSWORD'] = 'test-password'
    env_vars['RABBITMQ_USE_SSL'] = 'true'
    env_vars['RABBITMQ_SSL_VERIFY'] = 'true'
    env_vars['RABBITMQ_SSL_CERT_PATH'] = '/path/to/cert.pem'
    env_vars['RABBITMQ_SSL_KEY_PATH'] = '/path/to/key.pem'
    env_vars['RABBITMQ_SSL_CA_CERTS'] = '/path/to/ca.pem'
    env_vars['RABBITMQ_EXCHANGE_NAME'] = 'test-exchange'
    env_vars['RABBITMQ_QUEUE_NAME'] = 'test-queue'
    env_vars['RABBITMQ_PREFETCH_COUNT'] = '20'
    
    # Mock the from_env method
    with patch('src.types.config.RabbitMQConfig.from_env') as mock_from_env:
        # Create a mock config object
        mock_config = MagicMock(spec=RabbitMQConfig)
        mock_config.host = 'test-host'
        mock_config.port = 5673
        mock_config.virtual_host = '/test'
        mock_config.username = 'test-user'
        mock_config.password = 'test-password'
        mock_config.use_ssl = True
        mock_config.ssl_verify = True
        mock_config.ssl_cert_path = '/path/to/cert.pem'
        mock_config.ssl_key_path = '/path/to/key.pem'
        mock_config.ssl_ca_certs = '/path/to/ca.pem'
        mock_config.exchange_name = 'test-exchange'
        mock_config.queue_name = 'test-queue'
        mock_config.prefetch_count = 20
        
        # Set the return value of from_env
        mock_from_env.return_value = mock_config
        
        # Get RabbitMQ config
        config = rabbitmq_config.get_rabbitmq_config()
        
        # Verify config
        assert config.host == 'test-host'
        assert config.port == 5673
        assert config.virtual_host == '/test'
        assert config.username == 'test-user'
        assert config.password == 'test-password'
        assert config.use_ssl is True
        assert config.ssl_verify is True
        assert config.ssl_cert_path == '/path/to/cert.pem'
        assert config.ssl_key_path == '/path/to/key.pem'
        assert config.ssl_ca_certs == '/path/to/ca.pem'
        assert config.exchange_name == 'test-exchange'
        assert config.queue_name == 'test-queue'
        assert config.prefetch_count == 20