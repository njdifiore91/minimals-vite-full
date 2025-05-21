#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Service Configuration Package

This package provides a centralized configuration system for the Document Service microservice.
It imports and re-exports all configuration components to present a single, cohesive API surface,
simplifying configuration imports throughout the service and ensuring consistent configuration usage.

Imported modules:
    - app_config: Core application configuration
    - rabbitmq_config: RabbitMQ connection and messaging settings
    - s3_config: S3-compatible storage client configuration
    - model_config: Machine learning model configuration
    - logging_config: Logging system configuration

Usage:
    from config import app_config
    from config import rabbitmq_client
    from config import s3_client
    from config import model_config
    from config import configure_logging
"""

# Import configuration modules
from .app_config import app_config, get_app_config, AppConfig, Environment
from .rabbitmq_config import rabbitmq_client, get_rabbitmq_client, consume_messages, RabbitMQClient
from .s3_config import s3_client, get_s3_client, upload_document, download_document
from .model_config import model_config, get_model_config, load_model
from .logging_config import configure_logging, get_logger

# Re-export all configuration components
__all__ = [
    # App configuration
    'app_config',
    'get_app_config',
    'AppConfig',
    'Environment',
    
    # RabbitMQ configuration
    'rabbitmq_client',
    'get_rabbitmq_client',
    'consume_messages',
    'RabbitMQClient',
    
    # S3 configuration
    's3_client',
    'get_s3_client',
    'upload_document',
    'download_document',
    
    # Model configuration
    'model_config',
    'get_model_config',
    'load_model',
    
    # Logging configuration
    'configure_logging',
    'get_logger'
]