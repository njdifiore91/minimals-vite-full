#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Service Configuration Package

This package provides centralized configuration for the Document Service microservice.
It imports and re-exports all configuration components to present a single, cohesive
API surface, simplifying configuration imports throughout the service.

Components:
    - app_config: Core application configuration
    - rabbitmq_config: RabbitMQ connection and messaging settings
    - s3_config: S3-compatible storage configuration
    - model_config: Machine learning model configuration
    - logging_config: Logging system configuration
"""

# Import and re-export configuration modules
from .app_config import app_config, get_app_config, AppConfig, Environment
from .rabbitmq_config import (
    rabbitmq_client, 
    get_rabbitmq_client, 
    consume_messages,
    create_rabbitmq_connection,
    setup_rabbitmq_channel,
    publish_message,
    serialize_message,
    deserialize_message
)
from .s3_config import (
    create_s3_client,
    create_s3_resource,
    upload_file_with_encryption,
    download_file,
    check_bucket_exists,
    create_bucket_if_not_exists,
    get_bucket_name
)
from .model_config import (
    get_model_config,
    get_model_path,
    get_confidence_threshold,
    get_model_hyperparameters,
    MODEL_CONFIG
)
from .logging_config import (
    configure_logging,
    get_logger,
    LoggingContext
)

# Configure logging when this package is imported
configure_logging()

# Export all configuration components
__all__ = [
    # App config
    'app_config', 'get_app_config', 'AppConfig', 'Environment',
    
    # RabbitMQ config
    'rabbitmq_client', 'get_rabbitmq_client', 'consume_messages',
    'create_rabbitmq_connection', 'setup_rabbitmq_channel',
    'publish_message', 'serialize_message', 'deserialize_message',
    
    # S3 config
    'create_s3_client', 'create_s3_resource', 'upload_file_with_encryption',
    'download_file', 'check_bucket_exists', 'create_bucket_if_not_exists',
    'get_bucket_name',
    
    # Model config
    'get_model_config', 'get_model_path', 'get_confidence_threshold',
    'get_model_hyperparameters', 'MODEL_CONFIG',
    
    # Logging config
    'configure_logging', 'get_logger', 'LoggingContext'
]