#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Configuration Package

This package provides a centralized configuration system for the OCR Service.
It imports and re-exports all configuration components to present a single,
cohesive API surface, simplifying configuration imports throughout the service
and ensuring consistent configuration usage.

The configuration is organized into several modules:

- app_config: Core application configuration
- rabbitmq_config: RabbitMQ connection and messaging settings
- s3_config: S3-compatible storage client configuration
- tensorflow_config: TensorFlow models configuration
- logging_config: Logging system configuration

Example usage:
    from config import app_config
    
    # Access application configuration
    service_name = app_config.SERVICE_NAME
    
    # Access RabbitMQ configuration
    from config import get_rabbitmq_config
    rabbitmq_config = get_rabbitmq_config()
    
    # Access S3 configuration
    from config import get_s3_client_config
    s3_client_config = get_s3_client_config()
    
    # Access TensorFlow configuration
    from config import get_tensorflow_config
    tensorflow_config = get_tensorflow_config()
    
    # Access logging configuration
    from config import configure_logging, get_logger
    logger = get_logger(__name__)
"""

# Import and re-export app_config
from .app_config import app_config, AppConfig, Environment, LogLevel, get_config

# Import and re-export rabbitmq_config
from .rabbitmq_config import (
    get_rabbitmq_config,
    get_ssl_context,
    validate_rabbitmq_configuration,
    get_connection_parameters,
    get_consumer_options,
    get_publisher_options,
    serialize_message,
    deserialize_message,
    CONNECTION_CONFIG,
    EXCHANGE_CONFIG,
    QUEUE_CONFIG,
    RETRY_CONFIG,
    DEFAULT_MESSAGE_PROPERTIES
)

# Import and re-export s3_config
from .s3_config import (
    get_bucket_name,
    get_s3_client_config,
    validate_s3_configuration,
    get_storage_options,
    S3_CLIENT_CONFIG,
    S3_BOTO_CONFIG,
    DEFAULT_STORAGE_OPTIONS,
    BUCKETS,
    DOCUMENT_PATH_PREFIX,
    EXTRACTED_DATA_PATH_PREFIX,
    THUMBNAIL_PATH_PREFIX
)

# Import and re-export tensorflow_config
from .tensorflow_config import (
    get_tensorflow_config,
    get_model_config,
    get_model_path,
    get_model_type_for_document,
    get_model_type_for_field,
    get_gpu_optimization_settings,
    get_model_versioning_settings,
    get_performance_monitoring_settings,
    log_tensorflow_config,
    MODEL_ARCHITECTURES,
    DOCUMENT_TYPE_MODEL_MAPPING,
    FIELD_TYPE_MODEL_MAPPING,
    TENSORFLOW_VERSION,
    USE_GPU,
    GPU_MEMORY_LIMIT,
    CONFIDENCE_THRESHOLD
)

# Import and re-export logging_config
from .logging_config import (
    configure_logging,
    get_logger,
    set_request_context,
    clear_request_context,
    get_logging_config,
    ContextEnricher,
    JsonFormatter,
    LOG_LEVELS,
    LOG_FORMAT,
    DATE_FORMAT
)

# Version of the config package
__version__ = '1.0.0'

# Package metadata
__author__ = 'Dollar Funding OCR Team'
__email__ = 'ocr-team@dollarfunding.com'
__description__ = 'Configuration package for the OCR Service'

# Initialize logging when the package is imported
configure_logging()

# Log configuration information
logger = get_logger(__name__)
logger.info(f"OCR Service Configuration loaded (version {__version__})")
logger.info(f"Environment: {app_config.ENVIRONMENT}")
logger.info(f"Service: {app_config.SERVICE_NAME} v{app_config.SERVICE_VERSION}")