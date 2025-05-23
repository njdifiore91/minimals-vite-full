#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Application Configuration Module for OCR Service

This module defines and exports the core application configuration for the OCR Service microservice.
It centralizes environment variables, application settings, and environment-specific configurations
(development, staging, production).

The configuration is loaded from environment variables with validation to ensure required values
are present. Different settings are provided for development, staging, and production environments.

Typical usage:
    from config import app_config
    
    # Access configuration values
    service_name = app_config.SERVICE.name
    rabbitmq_host = app_config.RABBITMQ.host
    s3_bucket = app_config.S3.bucket
"""

import os
import sys
import logging
from enum import Enum
from typing import Dict, Any, Optional, cast

# Import type definitions
from types.config import (
    ConfigDict,
    ServiceConfig,
    TensorFlowConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig
)

# Set up module logger
logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Enum representing the possible deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Get environment variable with validation.
    
    Args:
        key: The environment variable name
        default: Default value if not found
        required: Whether the variable is required
        
    Returns:
        The environment variable value or default
        
    Raises:
        ValueError: If the variable is required but not found
    """
    value = os.environ.get(key, default)
    if required and value is None:
        logger.error(f"Required environment variable {key} is not set")
        raise ValueError(f"Required environment variable {key} is not set")
    return value if value is not None else ""


def get_current_environment() -> Environment:
    """
    Determine the current environment based on environment variables.
    
    Returns:
        The current environment (development, staging, or production)
    """
    env = get_env_var("OCR_SERVICE_ENV", Environment.DEVELOPMENT.value)
    try:
        return Environment(env.lower())
    except ValueError:
        logger.warning(
            f"Invalid environment '{env}', defaulting to {Environment.DEVELOPMENT.value}"
        )
        return Environment.DEVELOPMENT


def load_service_config() -> ServiceConfig:
    """
    Load service configuration from environment variables.
    
    Returns:
        ServiceConfig object with service settings
    """
    return ServiceConfig(
        name=get_env_var("OCR_SERVICE_NAME", "ocr-service"),
        version=get_env_var("OCR_SERVICE_VERSION", "1.0.0"),
        port=int(get_env_var("OCR_SERVICE_PORT", "8080")),
        environment=get_current_environment(),
        debug=get_env_var("OCR_SERVICE_DEBUG", "false").lower() == "true",
        correlation_id_header=get_env_var("OCR_CORRELATION_ID_HEADER", "X-Correlation-ID"),
        max_workers=int(get_env_var("OCR_SERVICE_MAX_WORKERS", "4")),
        shutdown_timeout=int(get_env_var("OCR_SERVICE_SHUTDOWN_TIMEOUT", "30")),
    )


def load_tensorflow_config() -> TensorFlowConfig:
    """
    Load TensorFlow configuration from environment variables.
    
    Returns:
        TensorFlowConfig object with TensorFlow settings
    """
    return TensorFlowConfig(
        models_path=get_env_var("OCR_MODELS_PATH", "/app/models"),
        typed_model_name=get_env_var("OCR_TYPED_MODEL_NAME", "typed_text_model"),
        handwritten_model_name=get_env_var("OCR_HANDWRITTEN_MODEL_NAME", "handwritten_text_model"),
        hybrid_model_name=get_env_var("OCR_HYBRID_MODEL_NAME", "hybrid_text_model"),
        confidence_threshold=float(get_env_var("OCR_CONFIDENCE_THRESHOLD", "0.85")),
        low_confidence_threshold=float(get_env_var("OCR_LOW_CONFIDENCE_THRESHOLD", "0.60")),
        gpu_memory_limit=int(get_env_var("OCR_GPU_MEMORY_LIMIT", "0")),  # 0 means no limit
        use_gpu=get_env_var("OCR_USE_GPU", "true").lower() == "true",
        batch_size=int(get_env_var("OCR_BATCH_SIZE", "4")),
        model_version=get_env_var("OCR_MODEL_VERSION", "1.0.0"),
        enable_optimization=get_env_var("OCR_ENABLE_OPTIMIZATION", "true").lower() == "true",
    )


def load_rabbitmq_config() -> RabbitMQConfig:
    """
    Load RabbitMQ configuration from environment variables.
    
    Returns:
        RabbitMQConfig object with RabbitMQ settings
    """
    return RabbitMQConfig(
        host=get_env_var("RABBITMQ_HOST", "localhost", required=True),
        port=int(get_env_var("RABBITMQ_PORT", "5672")),
        username=get_env_var("RABBITMQ_USERNAME", "guest", required=True),
        password=get_env_var("RABBITMQ_PASSWORD", "guest", required=True),
        vhost=get_env_var("RABBITMQ_VHOST", "/"),
        exchange=get_env_var("RABBITMQ_EXCHANGE", "mca.documents"),
        queue=get_env_var("RABBITMQ_QUEUE", "data-extraction"),
        routing_key=get_env_var("RABBITMQ_ROUTING_KEY", ""),
        use_tls=get_env_var("RABBITMQ_USE_TLS", "true").lower() == "true",
        cert_path=get_env_var("RABBITMQ_CERT_PATH", "/app/certs/client.pem"),
        key_path=get_env_var("RABBITMQ_KEY_PATH", "/app/certs/client.key"),
        ca_path=get_env_var("RABBITMQ_CA_PATH", "/app/certs/ca.pem"),
        prefetch_count=int(get_env_var("RABBITMQ_PREFETCH_COUNT", "10")),
        connection_attempts=int(get_env_var("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
        retry_delay=int(get_env_var("RABBITMQ_RETRY_DELAY", "5")),
        heartbeat=int(get_env_var("RABBITMQ_HEARTBEAT", "60")),
    )


def load_s3_config() -> S3Config:
    """
    Load S3 configuration from environment variables.
    
    Returns:
        S3Config object with S3 settings
    """
    environment = get_current_environment()
    bucket_suffix = "-production" if environment == Environment.PRODUCTION else "-staging"
    
    return S3Config(
        endpoint=get_env_var("S3_ENDPOINT", "http://localhost:9000", required=True),
        region=get_env_var("S3_REGION", "us-east-1"),
        bucket=get_env_var("S3_BUCKET", f"mca-documents{bucket_suffix}"),
        access_key=get_env_var("S3_ACCESS_KEY", "", required=True),
        secret_key=get_env_var("S3_SECRET_KEY", "", required=True),
        use_ssl=get_env_var("S3_USE_SSL", "true").lower() == "true",
        verify_ssl=get_env_var("S3_VERIFY_SSL", "true").lower() == "true",
        encryption=get_env_var("S3_ENCRYPTION", "AES256"),
        presigned_url_expiry=int(get_env_var("S3_PRESIGNED_URL_EXPIRY", "3600")),
        max_pool_connections=int(get_env_var("S3_MAX_POOL_CONNECTIONS", "10")),
        connect_timeout=int(get_env_var("S3_CONNECT_TIMEOUT", "5")),
        read_timeout=int(get_env_var("S3_READ_TIMEOUT", "60")),
    )


def load_logging_config() -> LoggingConfig:
    """
    Load logging configuration from environment variables.
    
    Returns:
        LoggingConfig object with logging settings
    """
    environment = get_current_environment()
    
    # Set default log level based on environment
    default_log_level = "INFO"
    if environment == Environment.DEVELOPMENT:
        default_log_level = "DEBUG"
    elif environment == Environment.PRODUCTION:
        default_log_level = "WARNING"
    
    return LoggingConfig(
        level=get_env_var("OCR_LOG_LEVEL", default_log_level),
        format=get_env_var(
            "OCR_LOG_FORMAT", 
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ),
        file_path=get_env_var("OCR_LOG_FILE", ""),  # Empty means log to console only
        max_bytes=int(get_env_var("OCR_LOG_MAX_BYTES", "10485760")),  # 10MB
        backup_count=int(get_env_var("OCR_LOG_BACKUP_COUNT", "5")),
        json_format=get_env_var("OCR_LOG_JSON", "false").lower() == "true",
        include_correlation_id=get_env_var("OCR_LOG_INCLUDE_CORRELATION_ID", "true").lower() == "true",
    )


class AppConfig:
    """
    Application configuration class that holds all configuration components.
    
    This class centralizes all configuration components and provides a single
    access point for configuration values throughout the application.
    """
    
    def __init__(self):
        """
        Initialize the application configuration with all components.
        """
        self.SERVICE = load_service_config()
        self.TENSORFLOW = load_tensorflow_config()
        self.RABBITMQ = load_rabbitmq_config()
        self.S3 = load_s3_config()
        self.LOGGING = load_logging_config()
        
        # Environment-specific overrides
        self._apply_environment_overrides()
        
        # Validate configuration
        self._validate_configuration()
        
        # Log configuration summary
        self._log_configuration_summary()
    
    def _apply_environment_overrides(self) -> None:
        """
        Apply environment-specific configuration overrides.
        """
        environment = self.SERVICE.environment
        
        if environment == Environment.DEVELOPMENT:
            # Development-specific overrides
            self.TENSORFLOW.use_gpu = False  # Disable GPU in development by default
            self.TENSORFLOW.enable_optimization = False  # Disable optimization for faster loading
            
        elif environment == Environment.STAGING:
            # Staging-specific overrides
            self.TENSORFLOW.confidence_threshold = 0.80  # Lower threshold for testing
            
        elif environment == Environment.PRODUCTION:
            # Production-specific overrides
            self.TENSORFLOW.confidence_threshold = 0.90  # Higher threshold for production
            self.RABBITMQ.prefetch_count = 20  # Higher prefetch for production throughput
    
    def _validate_configuration(self) -> None:
        """
        Validate the configuration to ensure it meets requirements.
        
        Raises:
            ValueError: If configuration validation fails
        """
        # Validate TensorFlow configuration
        if self.TENSORFLOW.use_gpu and self.TENSORFLOW.gpu_memory_limit < 0:
            raise ValueError("GPU memory limit must be >= 0 when GPU is enabled")
        
        # Validate RabbitMQ configuration
        if self.RABBITMQ.use_tls:
            if not os.path.exists(self.RABBITMQ.cert_path):
                logger.warning(f"RabbitMQ certificate file not found: {self.RABBITMQ.cert_path}")
            if not os.path.exists(self.RABBITMQ.key_path):
                logger.warning(f"RabbitMQ key file not found: {self.RABBITMQ.key_path}")
            if not os.path.exists(self.RABBITMQ.ca_path):
                logger.warning(f"RabbitMQ CA file not found: {self.RABBITMQ.ca_path}")
        
        # Validate S3 configuration
        if not self.S3.bucket:
            raise ValueError("S3 bucket name is required")
    
    def _log_configuration_summary(self) -> None:
        """
        Log a summary of the configuration for debugging purposes.
        """
        if self.SERVICE.debug:
            logger.info(f"OCR Service Configuration Summary:")
            logger.info(f"Environment: {self.SERVICE.environment}")
            logger.info(f"Service Name: {self.SERVICE.name}")
            logger.info(f"Service Version: {self.SERVICE.version}")
            logger.info(f"TensorFlow Models Path: {self.TENSORFLOW.models_path}")
            logger.info(f"Using GPU: {self.TENSORFLOW.use_gpu}")
            logger.info(f"RabbitMQ Host: {self.RABBITMQ.host}")
            logger.info(f"RabbitMQ Exchange: {self.RABBITMQ.exchange}")
            logger.info(f"RabbitMQ Queue: {self.RABBITMQ.queue}")
            logger.info(f"S3 Endpoint: {self.S3.endpoint}")
            logger.info(f"S3 Bucket: {self.S3.bucket}")
            logger.info(f"Log Level: {self.LOGGING.level}")


# Create and export the application configuration
app_config = AppConfig()