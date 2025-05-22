#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Service Configuration Package

This package serves as the central entry point for all configuration components
of the Document Service. It imports and re-exports all configuration modules to
present a single, cohesive API surface, simplifying configuration imports throughout
the service and ensuring consistent configuration usage.

Imported Modules:
    - app_config: Core application configuration
    - rabbitmq_config: RabbitMQ connection and messaging settings
    - s3_config: S3-compatible storage client configuration
    - model_config: Machine learning model configuration
    - logging_config: Logging system configuration

Usage:
    from config import app_config
    from config import rabbitmq_config
    from config import s3_config
    from config import model_config
    from config import logging_config
    
    # Or import specific components
    from config import create_s3_client, get_logger
"""

# Import and re-export app_config module
from .app_config import (
    AppConfig,
    get_app_config,
    validate_config,
    ENV,
    SERVICE_NAME,
    SERVICE_VERSION
)

# Import and re-export rabbitmq_config module
from .rabbitmq_config import (
    create_rabbitmq_connection,
    create_channel,
    setup_exchanges_and_queues,
    publish_message,
    start_consuming,
    EXCHANGE_NAME,
    QUEUE_NAME,
    ROUTING_KEY
)

# Import and re-export s3_config module
from .s3_config import (
    create_s3_client,
    create_s3_resource,
    upload_file_with_encryption,
    download_file,
    check_bucket_exists,
    create_bucket_if_not_exists,
    get_bucket_name,
    s3_client,
    s3_resource
)

# Import and re-export model_config module
from .model_config import (
    MODEL_TYPES,
    MODEL_HYPERPARAMETERS,
    FEATURE_EXTRACTION_PARAMS,
    CLASSIFICATION_THRESHOLDS,
    MODEL_PATHS,
    get_model_path,
    get_model_hyperparameters
)

# Import and re-export logging_config module
from .logging_config import (
    configure_logging,
    get_logger,
    LoggingContext,
    DEFAULT_LOG_LEVEL,
    SERVICE_NAME as LOGGING_SERVICE_NAME
)

# Initialize logging when this package is imported
configure_logging()

__all__ = [
    # app_config exports
    'AppConfig', 'get_app_config', 'validate_config', 'ENV', 'SERVICE_NAME', 'SERVICE_VERSION',
    
    # rabbitmq_config exports
    'create_rabbitmq_connection', 'create_channel', 'setup_exchanges_and_queues',
    'publish_message', 'start_consuming', 'EXCHANGE_NAME', 'QUEUE_NAME', 'ROUTING_KEY',
    
    # s3_config exports
    'create_s3_client', 'create_s3_resource', 'upload_file_with_encryption',
    'download_file', 'check_bucket_exists', 'create_bucket_if_not_exists',
    'get_bucket_name', 's3_client', 's3_resource',
    
    # model_config exports
    'MODEL_TYPES', 'MODEL_HYPERPARAMETERS', 'FEATURE_EXTRACTION_PARAMS',
    'CLASSIFICATION_THRESHOLDS', 'MODEL_PATHS', 'get_model_path', 'get_model_hyperparameters',
    
    # logging_config exports
    'configure_logging', 'get_logger', 'LoggingContext', 'DEFAULT_LOG_LEVEL', 'LOGGING_SERVICE_NAME'
]