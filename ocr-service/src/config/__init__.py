#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Configuration Package

This package provides a centralized configuration system for the OCR Service.
It imports and re-exports all configuration components to present a single,
cohesive API surface, simplifying configuration imports throughout the service
and ensuring consistent configuration usage.

Example usage:
    from config import app_config
    
    # Access application configuration
    service_name = app_config.SERVICE.name
    
    # Access TensorFlow configuration
    model_config = get_model_config('typed_text')
    
    # Access S3 configuration
    bucket_name = get_bucket_name()
    
    # Access RabbitMQ configuration
    rabbitmq_config = get_rabbitmq_config()
    
    # Access logging utilities
    logger = get_logger(__name__)
"""

# Import and re-export app_config
from .app_config import app_config

# Import and re-export RabbitMQ configuration functions
from .rabbitmq_config import (
    get_rabbitmq_config,
    get_rabbitmq_connection_parameters,
    get_rabbitmq_exchange_config,
    get_rabbitmq_queue_config,
    get_rabbitmq_consumer_config,
    get_rabbitmq_publisher_config,
    get_rabbitmq_retry_config,
    get_message_serializer,
    get_message_deserializer,
    create_ocr_result_message
)

# Import and re-export S3 configuration functions
from .s3_config import (
    get_bucket_name,
    get_s3_client_config,
    get_storage_options,
    validate_s3_configuration,
    DOCUMENT_BUCKET,
    EXTRACTED_DATA_BUCKET,
    DEFAULT_STORAGE_OPTIONS
)

# Import and re-export TensorFlow configuration functions
from .tensorflow_config import (
    get_session_config,
    get_model_config,
    get_confidence_threshold,
    initialize_tensorflow,
    GPU_CONFIG,
    MODEL_PATHS,
    MODEL_HYPERPARAMS,
    CONFIDENCE_THRESHOLDS,
    MODEL_ARCHITECTURES,
    TF_OPTIMIZATION
)

# Import and re-export logging configuration functions
from .logging_config import (
    setup_logging,
    get_logger,
    LogContext,
    add_context_to_record,
    SERVICE_NAME,
    ENVIRONMENT,
    LOG_LEVEL
)

# Define what should be imported with 'from config import *'
__all__ = [
    # Application configuration
    'app_config',
    
    # RabbitMQ configuration
    'get_rabbitmq_config',
    'get_rabbitmq_connection_parameters',
    'get_rabbitmq_exchange_config',
    'get_rabbitmq_queue_config',
    'get_rabbitmq_consumer_config',
    'get_rabbitmq_publisher_config',
    'get_rabbitmq_retry_config',
    'get_message_serializer',
    'get_message_deserializer',
    'create_ocr_result_message',
    
    # S3 configuration
    'get_bucket_name',
    'get_s3_client_config',
    'get_storage_options',
    'validate_s3_configuration',
    'DOCUMENT_BUCKET',
    'EXTRACTED_DATA_BUCKET',
    'DEFAULT_STORAGE_OPTIONS',
    
    # TensorFlow configuration
    'get_session_config',
    'get_model_config',
    'get_confidence_threshold',
    'initialize_tensorflow',
    'GPU_CONFIG',
    'MODEL_PATHS',
    'MODEL_HYPERPARAMS',
    'CONFIDENCE_THRESHOLDS',
    'MODEL_ARCHITECTURES',
    'TF_OPTIMIZATION',
    
    # Logging configuration
    'setup_logging',
    'get_logger',
    'LogContext',
    'add_context_to_record',
    'SERVICE_NAME',
    'ENVIRONMENT',
    'LOG_LEVEL'
]