#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Application Configuration for Document Service

This module defines and exports the core application configuration for the Document Service
microservice. It centralizes environment variables, application settings, and environment-specific
configurations (development, staging, production).

The configuration is loaded from environment variables with appropriate defaults and validation.
It provides a unified interface for accessing all configuration settings throughout the service.

Features:
    - Environment-specific configuration (development, staging, production)
    - Environment variable loading with validation
    - Centralized configuration object
    - Type-safe configuration access
    - Integration with other configuration modules
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

# Import configuration types
from ..types.config import (
    AppConfig, 
    ServiceConfig, 
    ModelConfig, 
    RabbitMQConfig, 
    S3Config, 
    LoggingConfig,
    Environment,
    ConfigDict
)

# Set up basic logging until proper logging is configured
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Base directory of the application
BASE_DIR = Path(__file__).parent.parent.parent

# Environment variables
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "document-service")
SERVICE_VERSION = os.environ.get("SERVICE_VERSION", "1.0.0")
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8000"))
SERVICE_DEBUG = os.environ.get("SERVICE_DEBUG", "false").lower() in ("true", "1", "yes")


def load_environment_config() -> Dict[str, Any]:
    """
    Load environment-specific configuration.
    
    Returns:
        Dict[str, Any]: Environment-specific configuration dictionary
    """
    env_config: Dict[str, Any] = {}
    
    # Development environment configuration
    if ENVIRONMENT.lower() in ("dev", "development"):
        env_config = {
            "debug": True,
            "log_level": "DEBUG",
            "rabbitmq": {
                "host": "localhost",
                "port": 5672,
                "ssl": False,
            },
            "s3": {
                "endpoint_url": "http://localhost:4566",  # LocalStack endpoint
                "bucket_name": "mca-documents-development",
                "use_ssl": False,
                "verify": False,
            },
            "model": {
                "confidence_threshold": 0.6,  # Lower threshold for development
            }
        }
    
    # Staging environment configuration
    elif ENVIRONMENT.lower() in ("stage", "staging"):
        env_config = {
            "debug": False,
            "log_level": "INFO",
            "rabbitmq": {
                "host": os.environ.get("RABBITMQ_HOST", "rabbitmq.staging"),
                "port": int(os.environ.get("RABBITMQ_PORT", "5671")),
                "ssl": True,
            },
            "s3": {
                "bucket_name": "mca-documents-staging",
                "use_ssl": True,
                "verify": True,
            },
            "model": {
                "confidence_threshold": 0.75,  # Medium threshold for staging
            }
        }
    
    # Production environment configuration
    elif ENVIRONMENT.lower() in ("prod", "production"):
        env_config = {
            "debug": False,
            "log_level": "INFO",
            "rabbitmq": {
                "host": os.environ.get("RABBITMQ_HOST", "rabbitmq.production"),
                "port": int(os.environ.get("RABBITMQ_PORT", "5671")),
                "ssl": True,
            },
            "s3": {
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
            },
            "model": {
                "confidence_threshold": 0.85,  # Higher threshold for production
            }
        }
    
    # Default to development if environment is not recognized
    else:
        logger.warning(f"Unknown environment: {ENVIRONMENT}. Using development configuration.")
        return load_environment_config()  # Recursively call with default environment
    
    return env_config


def create_app_config() -> AppConfig:
    """
    Create and return the application configuration.
    
    This function loads configuration from environment variables and environment-specific
    settings, then creates a unified AppConfig object.
    
    Returns:
        AppConfig: The complete application configuration
    """
    # Load environment-specific configuration
    env_config = load_environment_config()
    
    # Create service configuration
    service_config = ServiceConfig(
        name=SERVICE_NAME,
        version=SERVICE_VERSION,
        port=SERVICE_PORT,
        environment=Environment.from_string(ENVIRONMENT),
        debug=env_config.get("debug", False),
        base_path=BASE_DIR
    )
    
    # Create model configuration
    model_config = ModelConfig(
        model_type=os.environ.get("MODEL_TYPE", "random_forest"),
        parameters={},  # Will be loaded from model_config.py
        confidence_threshold=env_config.get("model", {}).get("confidence_threshold", 0.75),
        version=os.environ.get("MODEL_VERSION", "1.0.0"),
        description="Document classification model for MCA application processing"
    )
    
    # Create RabbitMQ configuration
    rabbitmq_config = RabbitMQConfig(
        host=env_config.get("rabbitmq", {}).get("host", "localhost"),
        port=env_config.get("rabbitmq", {}).get("port", 5672),
        username=os.environ.get("RABBITMQ_USERNAME", "guest"),
        password=os.environ.get("RABBITMQ_PASSWORD", "guest"),
        virtual_host=os.environ.get("RABBITMQ_VHOST", "/"),
        ssl=env_config.get("rabbitmq", {}).get("ssl", True),
        heartbeat=int(os.environ.get("RABBITMQ_HEARTBEAT", "60")),
        connection_attempts=int(os.environ.get("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
        retry_delay=int(os.environ.get("RABBITMQ_RETRY_DELAY", "5"))
    )
    
    # Create S3 configuration
    s3_config: S3Config = {
        "endpoint_url": env_config.get("s3", {}).get("endpoint_url", os.environ.get("S3_ENDPOINT_URL", "https://s3.amazonaws.com")),
        "region_name": os.environ.get("S3_REGION", "us-east-1"),
        "aws_access_key_id": os.environ.get("S3_ACCESS_KEY", ""),
        "aws_secret_access_key": os.environ.get("S3_SECRET_KEY", ""),
        "use_ssl": env_config.get("s3", {}).get("use_ssl", True),
        "verify": env_config.get("s3", {}).get("verify", True),
        "max_pool_connections": int(os.environ.get("S3_MAX_POOL_CONNECTIONS", "10")),
        "timeout": int(os.environ.get("S3_TIMEOUT", "60")),
        "retries": int(os.environ.get("S3_RETRIES", "3")),
        "bucket_name": env_config.get("s3", {}).get("bucket_name", os.environ.get("S3_BUCKET", f"mca-documents-{ENVIRONMENT.lower()}")),
        "encryption": os.environ.get("S3_ENCRYPTION", "AES256")
    }
    
    # Create logging configuration
    logging_config = LoggingConfig(
        level=env_config.get("log_level", "INFO"),
        format=os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
        date_format=os.environ.get("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
        file_path=os.environ.get("LOG_FILE_PATH"),
        console_output=os.environ.get("LOG_CONSOLE", "true").lower() in ("true", "1", "yes"),
        json_format=os.environ.get("LOG_JSON", "true").lower() in ("true", "1", "yes"),
        include_correlation_id=os.environ.get("LOG_CORRELATION_ID", "true").lower() in ("true", "1", "yes"),
        include_document_id=os.environ.get("LOG_DOCUMENT_ID", "true").lower() in ("true", "1", "yes")
    )
    
    # Create complete application configuration
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    return app_config


def validate_config(config: AppConfig) -> None:
    """
    Validate the application configuration.
    
    This function checks that all required configuration values are present and valid.
    It raises ValueError if any validation fails.
    
    Args:
        config: The application configuration to validate
        
    Raises:
        ValueError: If any configuration validation fails
    """
    # Validate S3 configuration in production and staging
    if config.service.environment in (Environment.PRODUCTION, Environment.STAGING):
        if not config.s3["aws_access_key_id"] or not config.s3["aws_secret_access_key"]:
            raise ValueError("S3 credentials are required in production and staging environments")
    
    # Validate RabbitMQ configuration in all environments
    if not config.rabbitmq.host:
        raise ValueError("RabbitMQ host is required")
    
    # In production and staging, validate RabbitMQ credentials
    if config.service.environment in (Environment.PRODUCTION, Environment.STAGING):
        if not config.rabbitmq.username or not config.rabbitmq.password:
            raise ValueError("RabbitMQ credentials are required in production and staging environments")
    
    # Validate service configuration
    if not config.service.name or not config.service.version:
        raise ValueError("Service name and version are required")
    
    # Validate model configuration
    if not config.model.model_type:
        raise ValueError("Model type is required")
    
    # Validate confidence threshold is between 0 and 1
    if not 0 <= config.model.confidence_threshold <= 1:
        raise ValueError(f"Model confidence threshold must be between 0 and 1, got {config.model.confidence_threshold}")
    
    logger.info(f"Configuration validated for {config.service.name} v{config.service.version} in {config.service.environment.value} environment")


# Create and validate the application configuration
try:
    app_config = create_app_config()
    validate_config(app_config)
except Exception as e:
    logger.error(f"Failed to create or validate application configuration: {str(e)}")
    sys.exit(1)


def get_app_config() -> AppConfig:
    """
    Get the application configuration.
    
    This function returns the singleton instance of the application configuration.
    
    Returns:
        AppConfig: The application configuration
    """
    return app_config


# Export the configuration object
__all__ = ["app_config", "get_app_config", "AppConfig", "Environment"]