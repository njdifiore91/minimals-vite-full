#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RabbitMQ Configuration for OCR Service

This module configures the RabbitMQ connection and messaging settings for the OCR Service.
It defines connection parameters, exchange and queue configurations, message consumption options,
and security settings. The configuration enables the service to consume classification results
from the Document Service and publish extraction results to the Data Service.

Key features:
1. TLS/SSL configuration with client certificate authentication
2. Exchange and queue setup for document processing
3. Connection error handling and recovery strategies
4. Message serialization for consistent JSON format
5. Environment-specific configuration options
"""

import os
import logging
import ssl
from typing import Dict, Optional, Any, List

from ..types.messages import (
    ExchangeType, ExchangeConfig, QueueConfig, ConnectionConfig,
    RetryConfig, MessagePayload, MessageHeaders, MessageSerializer
)
from ..types.config import RabbitMQConfig

# Configure logging
logger = logging.getLogger(__name__)

# Environment variable names
ENV_VAR_ENVIRONMENT = 'OCR_ENVIRONMENT'
ENV_VAR_RABBITMQ_HOST = 'RABBITMQ_HOST'
ENV_VAR_RABBITMQ_PORT = 'RABBITMQ_PORT'
ENV_VAR_RABBITMQ_VHOST = 'RABBITMQ_VIRTUAL_HOST'
ENV_VAR_RABBITMQ_USER = 'RABBITMQ_USERNAME'
ENV_VAR_RABBITMQ_PASS = 'RABBITMQ_PASSWORD'
ENV_VAR_RABBITMQ_USE_SSL = 'RABBITMQ_USE_SSL'
ENV_VAR_RABBITMQ_SSL_VERIFY = 'RABBITMQ_SSL_VERIFY'
ENV_VAR_RABBITMQ_SSL_CERT = 'RABBITMQ_SSL_CERT_PATH'
ENV_VAR_RABBITMQ_SSL_KEY = 'RABBITMQ_SSL_KEY_PATH'
ENV_VAR_RABBITMQ_SSL_CA = 'RABBITMQ_SSL_CA_CERTS'
ENV_VAR_RABBITMQ_EXCHANGE = 'RABBITMQ_EXCHANGE_NAME'
ENV_VAR_RABBITMQ_QUEUE = 'RABBITMQ_QUEUE_NAME'

# Default values
DEFAULT_ENVIRONMENT = 'development'
DEFAULT_HOST = 'rabbitmq'
DEFAULT_PORT = 5672
DEFAULT_VHOST = '/'
DEFAULT_USER = 'guest'
DEFAULT_PASS = 'guest'
DEFAULT_EXCHANGE = 'mca.documents'
DEFAULT_QUEUE = 'data-extraction'
DEFAULT_CONSUMER_TAG = 'ocr-service'

# Get current environment
ENVIRONMENT = os.environ.get(ENV_VAR_ENVIRONMENT, DEFAULT_ENVIRONMENT)

# RabbitMQ connection configuration
RABBITMQ_HOST = os.environ.get(ENV_VAR_RABBITMQ_HOST, DEFAULT_HOST)
RABBITMQ_PORT = int(os.environ.get(ENV_VAR_RABBITMQ_PORT, str(DEFAULT_PORT)))
RABBITMQ_VHOST = os.environ.get(ENV_VAR_RABBITMQ_VHOST, DEFAULT_VHOST)
RABBITMQ_USER = os.environ.get(ENV_VAR_RABBITMQ_USER, DEFAULT_USER)
RABBITMQ_PASS = os.environ.get(ENV_VAR_RABBITMQ_PASS, DEFAULT_PASS)

# SSL/TLS configuration (required as per section 3.2.3)
RABBITMQ_USE_SSL = os.environ.get(ENV_VAR_RABBITMQ_USE_SSL, 'true').lower() == 'true'
RABBITMQ_SSL_VERIFY = os.environ.get(ENV_VAR_RABBITMQ_SSL_VERIFY, 'true').lower() == 'true'
RABBITMQ_SSL_CERT = os.environ.get(ENV_VAR_RABBITMQ_SSL_CERT)
RABBITMQ_SSL_KEY = os.environ.get(ENV_VAR_RABBITMQ_SSL_KEY)
RABBITMQ_SSL_CA = os.environ.get(ENV_VAR_RABBITMQ_SSL_CA)

# Exchange and queue configuration
RABBITMQ_EXCHANGE = os.environ.get(ENV_VAR_RABBITMQ_EXCHANGE, DEFAULT_EXCHANGE)
RABBITMQ_QUEUE = os.environ.get(ENV_VAR_RABBITMQ_QUEUE, DEFAULT_QUEUE)

# Connection configuration
CONNECTION_CONFIG: ConnectionConfig = {
    'host': RABBITMQ_HOST,
    'port': RABBITMQ_PORT,
    'virtual_host': RABBITMQ_VHOST,
    'username': RABBITMQ_USER,
    'password': RABBITMQ_PASS,
    'heartbeat': 60,  # Heartbeat interval in seconds
    'blocked_connection_timeout': 300,  # Timeout for blocked connections
    'connection_attempts': 5,  # Number of connection attempts
    'retry_delay': 1.0,  # Delay between connection attempts
    'ssl': RABBITMQ_USE_SSL,  # Use SSL/TLS
}

# SSL/TLS options if enabled
if RABBITMQ_USE_SSL:
    ssl_options: Dict[str, Any] = {
        'cert_reqs': ssl.CERT_REQUIRED if RABBITMQ_SSL_VERIFY else ssl.CERT_NONE,
        'ssl_version': ssl.PROTOCOL_TLSv1_2,  # TLS 1.2+ as required in section 3.2.3
    }
    
    # Add client certificate if provided
    if RABBITMQ_SSL_CERT and RABBITMQ_SSL_KEY:
        ssl_options['certfile'] = RABBITMQ_SSL_CERT
        ssl_options['keyfile'] = RABBITMQ_SSL_KEY
    
    # Add CA certificate if provided
    if RABBITMQ_SSL_CA:
        ssl_options['ca_certs'] = RABBITMQ_SSL_CA
    
    CONNECTION_CONFIG['ssl_options'] = ssl_options

# Exchange configuration (fanout as specified in section 0.2.1.2)
EXCHANGE_CONFIG: ExchangeConfig = {
    'name': RABBITMQ_EXCHANGE,
    'type': ExchangeType.FANOUT.value,
    'durable': True,  # Survive broker restart
    'auto_delete': False,  # Don't delete when no queues bound
}

# Queue configuration
QUEUE_CONFIG: QueueConfig = {
    'name': RABBITMQ_QUEUE,
    'durable': True,  # Survive broker restart
    'exclusive': False,  # Not exclusive to this connection
    'auto_delete': False,  # Don't delete when consumer disconnects
    'arguments': {
        'x-message-ttl': 86400000,  # 24 hours in milliseconds
        'x-dead-letter-exchange': f"{RABBITMQ_EXCHANGE}-dlx",  # Dead letter exchange
        'x-dead-letter-routing-key': f"{RABBITMQ_QUEUE}-dlq",  # Dead letter routing key
    },
    'prefetch_count': 10,  # Maximum unacknowledged messages
    'consumer_tag': DEFAULT_CONSUMER_TAG,  # Consumer identifier
}

# Dead letter exchange and queue configuration for error handling
DEAD_LETTER_EXCHANGE_CONFIG: ExchangeConfig = {
    'name': f"{RABBITMQ_EXCHANGE}-dlx",
    'type': ExchangeType.DIRECT.value,
    'durable': True,
    'auto_delete': False,
}

DEAD_LETTER_QUEUE_CONFIG: QueueConfig = {
    'name': f"{RABBITMQ_QUEUE}-dlq",
    'durable': True,
    'exclusive': False,
    'auto_delete': False,
    'arguments': {
        'x-message-ttl': 604800000,  # 7 days in milliseconds
    },
}

# Retry configuration for connection and channel errors
RETRY_CONFIG: RetryConfig = {
    'max_retries': 5,  # Maximum number of retries
    'initial_delay': 1.0,  # Initial delay in seconds
    'max_delay': 30.0,  # Maximum delay in seconds
    'backoff_factor': 2.0,  # Backoff factor for exponential backoff
    'retry_on_exceptions': [
        'ConnectionError',
        'ChannelError',
        'AMQPError',
        'TimeoutError',
    ],
}

# Default message properties
DEFAULT_MESSAGE_PROPERTIES: MessageHeaders = {
    'content_type': 'application/json',
    'content_encoding': 'utf-8',
    'delivery_mode': 2,  # 2 = persistent
    'app_id': 'ocr-service',
}


def get_rabbitmq_config() -> RabbitMQConfig:
    """
    Get the RabbitMQ configuration from environment variables.
    
    Returns:
        RabbitMQConfig: Configuration object for RabbitMQ
    """
    return RabbitMQConfig.from_env()


def get_ssl_context() -> Optional[ssl.SSLContext]:
    """
    Create an SSL context for RabbitMQ connection if SSL is enabled.
    
    This function creates an SSL context with the appropriate certificate
    verification and client certificate settings based on the configuration.
    
    Returns:
        Optional[ssl.SSLContext]: SSL context for RabbitMQ connection, or None if SSL is disabled
    """
    if not RABBITMQ_USE_SSL:
        return None
    
    # Create SSL context with TLS 1.2 or higher
    context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    
    # Set certificate verification mode
    if RABBITMQ_SSL_VERIFY:
        context.verify_mode = ssl.CERT_REQUIRED
    else:
        context.verify_mode = ssl.CERT_NONE
        context.check_hostname = False
    
    # Load CA certificate if provided
    if RABBITMQ_SSL_CA:
        context.load_verify_locations(cafile=RABBITMQ_SSL_CA)
    
    # Load client certificate if provided
    if RABBITMQ_SSL_CERT and RABBITMQ_SSL_KEY:
        context.load_cert_chain(RABBITMQ_SSL_CERT, RABBITMQ_SSL_KEY)
    
    return context


def validate_rabbitmq_configuration() -> bool:
    """
    Validate the RabbitMQ configuration.
    
    This function checks that the required configuration is available and valid.
    It logs warnings for any issues found.
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    valid = True
    
    # Check if host is configured
    if not RABBITMQ_HOST:
        logger.error("RabbitMQ host not configured")
        valid = False
    
    # Check if exchange is configured
    if not RABBITMQ_EXCHANGE:
        logger.error("RabbitMQ exchange not configured")
        valid = False
    
    # Check if queue is configured
    if not RABBITMQ_QUEUE:
        logger.error("RabbitMQ queue not configured")
        valid = False
    
    # Check SSL configuration if enabled
    if RABBITMQ_USE_SSL:
        # Check if client certificate authentication is properly configured
        if RABBITMQ_SSL_VERIFY and not RABBITMQ_SSL_CA:
            logger.warning("SSL verification enabled but CA certificate not provided")
        
        # Check if client certificate is properly configured
        if RABBITMQ_SSL_CERT and not RABBITMQ_SSL_KEY:
            logger.error("SSL certificate provided but key is missing")
            valid = False
        elif RABBITMQ_SSL_KEY and not RABBITMQ_SSL_CERT:
            logger.error("SSL key provided but certificate is missing")
            valid = False
    
    return valid


def get_connection_parameters() -> Dict[str, Any]:
    """
    Get connection parameters for RabbitMQ client.
    
    This function returns a dictionary of connection parameters suitable for
    use with the pika library to connect to RabbitMQ.
    
    Returns:
        Dict[str, Any]: Connection parameters for RabbitMQ client
    """
    params = {
        'host': RABBITMQ_HOST,
        'port': RABBITMQ_PORT,
        'virtual_host': RABBITMQ_VHOST,
        'credentials': {
            'username': RABBITMQ_USER,
            'password': RABBITMQ_PASS,
        },
        'heartbeat': CONNECTION_CONFIG['heartbeat'],
        'blocked_connection_timeout': CONNECTION_CONFIG['blocked_connection_timeout'],
        'connection_attempts': CONNECTION_CONFIG['connection_attempts'],
        'retry_delay': CONNECTION_CONFIG['retry_delay'],
    }
    
    # Add SSL context if SSL is enabled
    if RABBITMQ_USE_SSL:
        params['ssl_options'] = get_ssl_context()
    
    return params


def get_consumer_options() -> Dict[str, Any]:
    """
    Get consumer options for RabbitMQ client.
    
    This function returns a dictionary of consumer options suitable for
    use with the pika library to consume messages from RabbitMQ.
    
    Returns:
        Dict[str, Any]: Consumer options for RabbitMQ client
    """
    return {
        'queue': QUEUE_CONFIG['name'],
        'consumer_tag': QUEUE_CONFIG['consumer_tag'],
        'exclusive': QUEUE_CONFIG['exclusive'],
        'arguments': QUEUE_CONFIG.get('arguments', {}),
    }


def get_publisher_options() -> Dict[str, Any]:
    """
    Get publisher options for RabbitMQ client.
    
    This function returns a dictionary of publisher options suitable for
    use with the pika library to publish messages to RabbitMQ.
    
    Returns:
        Dict[str, Any]: Publisher options for RabbitMQ client
    """
    return {
        'exchange': EXCHANGE_CONFIG['name'],
        'routing_key': '',  # Empty for fanout exchange
        'mandatory': True,  # Return message if it can't be routed
        'properties': DEFAULT_MESSAGE_PROPERTIES,
    }


def serialize_message(payload: MessagePayload) -> bytes:
    """
    Serialize a message payload to JSON bytes.
    
    Args:
        payload: Message payload to serialize
        
    Returns:
        bytes: Serialized message payload
    """
    return MessageSerializer.serialize(payload)


def deserialize_message(body: bytes) -> MessagePayload:
    """
    Deserialize JSON bytes to a message payload.
    
    Args:
        body: Serialized message payload
        
    Returns:
        MessagePayload: Deserialized message payload
    """
    return MessageSerializer.deserialize(body)


# Validate configuration on module import
if not validate_rabbitmq_configuration():
    logger.warning("RabbitMQ configuration validation failed")


# Log configuration summary
logger.info(f"RabbitMQ Configuration: Environment={ENVIRONMENT}, Host={RABBITMQ_HOST}, Port={RABBITMQ_PORT}")
logger.info(f"Exchange: {RABBITMQ_EXCHANGE} (type: {EXCHANGE_CONFIG['type']})")
logger.info(f"Queue: {RABBITMQ_QUEUE}")
logger.info(f"SSL/TLS: {'Enabled' if RABBITMQ_USE_SSL else 'Disabled'}")
if RABBITMQ_USE_SSL:
    logger.info(f"SSL Verification: {'Enabled' if RABBITMQ_SSL_VERIFY else 'Disabled'}")
    logger.info(f"Client Certificate: {'Configured' if RABBITMQ_SSL_CERT and RABBITMQ_SSL_KEY else 'Not configured'}")