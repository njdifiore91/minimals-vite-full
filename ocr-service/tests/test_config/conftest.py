#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest fixtures and utilities for testing OCR Service configuration modules.

This module provides fixtures and helper functions for testing configuration loading,
validation, and defaults across different environments. It includes fixtures for
mocking environment variables, creating sample configuration objects, and simulating
different deployment environments.

These fixtures ensure that configuration tests can run independently without external
dependencies and provide a consistent test environment across all configuration test modules.
"""

import os
import pytest
from typing import Dict, Any, Optional, List, Callable
from enum import Enum

# Import configuration types
from types.config import (
    ConfigDict,
    ServiceConfig,
    TensorFlowConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
    EnvironmentType,
    LogLevel
)


# Environment variable sets for different deployment environments
DEV_ENV_VARS = {
    # Service configuration
    "OCR_SERVICE_ENV": "development",
    "OCR_SERVICE_NAME": "ocr-service",
    "OCR_SERVICE_VERSION": "1.0.0",
    "OCR_SERVICE_PORT": "8080",
    "OCR_SERVICE_DEBUG": "true",
    "OCR_CORRELATION_ID_HEADER": "X-Correlation-ID",
    "OCR_SERVICE_MAX_WORKERS": "4",
    "OCR_SERVICE_SHUTDOWN_TIMEOUT": "30",
    
    # TensorFlow configuration
    "OCR_MODELS_PATH": "/app/models",
    "OCR_TYPED_MODEL_NAME": "typed_text_model",
    "OCR_HANDWRITTEN_MODEL_NAME": "handwritten_text_model",
    "OCR_HYBRID_MODEL_NAME": "hybrid_text_model",
    "OCR_CONFIDENCE_THRESHOLD": "0.85",
    "OCR_LOW_CONFIDENCE_THRESHOLD": "0.60",
    "OCR_GPU_MEMORY_LIMIT": "0",
    "OCR_USE_GPU": "false",  # Disabled in development
    "OCR_BATCH_SIZE": "4",
    "OCR_MODEL_VERSION": "1.0.0",
    "OCR_ENABLE_OPTIMIZATION": "false",  # Disabled in development
    
    # RabbitMQ configuration
    "RABBITMQ_HOST": "localhost",
    "RABBITMQ_PORT": "5672",
    "RABBITMQ_USERNAME": "guest",
    "RABBITMQ_PASSWORD": "guest",
    "RABBITMQ_VHOST": "/",
    "RABBITMQ_EXCHANGE": "mca.documents",
    "RABBITMQ_QUEUE": "data-extraction",
    "RABBITMQ_ROUTING_KEY": "",
    "RABBITMQ_USE_TLS": "false",  # Disabled in development
    "RABBITMQ_CERT_PATH": "/app/certs/client.pem",
    "RABBITMQ_KEY_PATH": "/app/certs/client.key",
    "RABBITMQ_CA_PATH": "/app/certs/ca.pem",
    "RABBITMQ_PREFETCH_COUNT": "10",
    "RABBITMQ_CONNECTION_ATTEMPTS": "3",
    "RABBITMQ_RETRY_DELAY": "5",
    "RABBITMQ_HEARTBEAT": "60",
    
    # S3 configuration
    "S3_ENDPOINT": "http://localhost:9000",
    "S3_REGION": "us-east-1",
    "S3_BUCKET": "mca-documents-staging",
    "S3_ACCESS_KEY": "minioadmin",
    "S3_SECRET_KEY": "minioadmin",
    "S3_USE_SSL": "false",  # Disabled in development
    "S3_VERIFY_SSL": "false",  # Disabled in development
    "S3_ENCRYPTION": "AES256",
    "S3_PRESIGNED_URL_EXPIRY": "3600",
    "S3_MAX_POOL_CONNECTIONS": "10",
    "S3_CONNECT_TIMEOUT": "5",
    "S3_READ_TIMEOUT": "60",
    
    # Logging configuration
    "OCR_LOG_LEVEL": "DEBUG",
    "OCR_LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "OCR_LOG_FILE": "",  # Empty means log to console only
    "OCR_LOG_MAX_BYTES": "10485760",
    "OCR_LOG_BACKUP_COUNT": "5",
    "OCR_LOG_JSON": "false",
    "OCR_LOG_INCLUDE_CORRELATION_ID": "true"
}

STAGING_ENV_VARS = {
    # Service configuration
    "OCR_SERVICE_ENV": "staging",
    "OCR_SERVICE_NAME": "ocr-service",
    "OCR_SERVICE_VERSION": "1.0.0",
    "OCR_SERVICE_PORT": "8080",
    "OCR_SERVICE_DEBUG": "false",
    "OCR_CORRELATION_ID_HEADER": "X-Correlation-ID",
    "OCR_SERVICE_MAX_WORKERS": "8",
    "OCR_SERVICE_SHUTDOWN_TIMEOUT": "30",
    
    # TensorFlow configuration
    "OCR_MODELS_PATH": "/app/models",
    "OCR_TYPED_MODEL_NAME": "typed_text_model",
    "OCR_HANDWRITTEN_MODEL_NAME": "handwritten_text_model",
    "OCR_HYBRID_MODEL_NAME": "hybrid_text_model",
    "OCR_CONFIDENCE_THRESHOLD": "0.80",  # Lower threshold for staging
    "OCR_LOW_CONFIDENCE_THRESHOLD": "0.60",
    "OCR_GPU_MEMORY_LIMIT": "4096",
    "OCR_USE_GPU": "true",
    "OCR_BATCH_SIZE": "8",
    "OCR_MODEL_VERSION": "1.0.0",
    "OCR_ENABLE_OPTIMIZATION": "true",
    
    # RabbitMQ configuration
    "RABBITMQ_HOST": "rabbitmq.staging",
    "RABBITMQ_PORT": "5671",
    "RABBITMQ_USERNAME": "ocr-service",
    "RABBITMQ_PASSWORD": "password",
    "RABBITMQ_VHOST": "/mca",
    "RABBITMQ_EXCHANGE": "mca.documents",
    "RABBITMQ_QUEUE": "data-extraction",
    "RABBITMQ_ROUTING_KEY": "",
    "RABBITMQ_USE_TLS": "true",
    "RABBITMQ_CERT_PATH": "/app/certs/client.pem",
    "RABBITMQ_KEY_PATH": "/app/certs/client.key",
    "RABBITMQ_CA_PATH": "/app/certs/ca.pem",
    "RABBITMQ_PREFETCH_COUNT": "10",
    "RABBITMQ_CONNECTION_ATTEMPTS": "3",
    "RABBITMQ_RETRY_DELAY": "5",
    "RABBITMQ_HEARTBEAT": "60",
    
    # S3 configuration
    "S3_ENDPOINT": "https://s3.staging.dollarfunding.com",
    "S3_REGION": "us-east-1",
    "S3_BUCKET": "mca-documents-staging",
    "S3_ACCESS_KEY": "ocr-service-staging",
    "S3_SECRET_KEY": "password",
    "S3_USE_SSL": "true",
    "S3_VERIFY_SSL": "true",
    "S3_ENCRYPTION": "AES256",
    "S3_PRESIGNED_URL_EXPIRY": "3600",
    "S3_MAX_POOL_CONNECTIONS": "10",
    "S3_CONNECT_TIMEOUT": "5",
    "S3_READ_TIMEOUT": "60",
    
    # Logging configuration
    "OCR_LOG_LEVEL": "INFO",
    "OCR_LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "OCR_LOG_FILE": "/var/log/ocr-service/service.log",
    "OCR_LOG_MAX_BYTES": "10485760",
    "OCR_LOG_BACKUP_COUNT": "5",
    "OCR_LOG_JSON": "true",
    "OCR_LOG_INCLUDE_CORRELATION_ID": "true"
}

PRODUCTION_ENV_VARS = {
    # Service configuration
    "OCR_SERVICE_ENV": "production",
    "OCR_SERVICE_NAME": "ocr-service",
    "OCR_SERVICE_VERSION": "1.0.0",
    "OCR_SERVICE_PORT": "8080",
    "OCR_SERVICE_DEBUG": "false",
    "OCR_CORRELATION_ID_HEADER": "X-Correlation-ID",
    "OCR_SERVICE_MAX_WORKERS": "16",
    "OCR_SERVICE_SHUTDOWN_TIMEOUT": "30",
    
    # TensorFlow configuration
    "OCR_MODELS_PATH": "/app/models",
    "OCR_TYPED_MODEL_NAME": "typed_text_model",
    "OCR_HANDWRITTEN_MODEL_NAME": "handwritten_text_model",
    "OCR_HYBRID_MODEL_NAME": "hybrid_text_model",
    "OCR_CONFIDENCE_THRESHOLD": "0.90",  # Higher threshold for production
    "OCR_LOW_CONFIDENCE_THRESHOLD": "0.70",
    "OCR_GPU_MEMORY_LIMIT": "8192",
    "OCR_USE_GPU": "true",
    "OCR_BATCH_SIZE": "16",
    "OCR_MODEL_VERSION": "1.0.0",
    "OCR_ENABLE_OPTIMIZATION": "true",
    
    # RabbitMQ configuration
    "RABBITMQ_HOST": "rabbitmq.production",
    "RABBITMQ_PORT": "5671",
    "RABBITMQ_USERNAME": "ocr-service",
    "RABBITMQ_PASSWORD": "password",
    "RABBITMQ_VHOST": "/mca",
    "RABBITMQ_EXCHANGE": "mca.documents",
    "RABBITMQ_QUEUE": "data-extraction",
    "RABBITMQ_ROUTING_KEY": "",
    "RABBITMQ_USE_TLS": "true",
    "RABBITMQ_CERT_PATH": "/app/certs/client.pem",
    "RABBITMQ_KEY_PATH": "/app/certs/client.key",
    "RABBITMQ_CA_PATH": "/app/certs/ca.pem",
    "RABBITMQ_PREFETCH_COUNT": "20",  # Higher prefetch for production
    "RABBITMQ_CONNECTION_ATTEMPTS": "5",
    "RABBITMQ_RETRY_DELAY": "5",
    "RABBITMQ_HEARTBEAT": "60",
    
    # S3 configuration
    "S3_ENDPOINT": "https://s3.dollarfunding.com",
    "S3_REGION": "us-east-1",
    "S3_BUCKET": "mca-documents-production",
    "S3_ACCESS_KEY": "ocr-service-production",
    "S3_SECRET_KEY": "password",
    "S3_USE_SSL": "true",
    "S3_VERIFY_SSL": "true",
    "S3_ENCRYPTION": "AES256",
    "S3_PRESIGNED_URL_EXPIRY": "3600",
    "S3_MAX_POOL_CONNECTIONS": "20",
    "S3_CONNECT_TIMEOUT": "5",
    "S3_READ_TIMEOUT": "60",
    
    # Logging configuration
    "OCR_LOG_LEVEL": "WARNING",
    "OCR_LOG_FORMAT": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "OCR_LOG_FILE": "/var/log/ocr-service/service.log",
    "OCR_LOG_MAX_BYTES": "10485760",
    "OCR_LOG_BACKUP_COUNT": "10",
    "OCR_LOG_JSON": "true",
    "OCR_LOG_INCLUDE_CORRELATION_ID": "true"
}


# Environment fixture for different deployment environments
class Environment(Enum):
    """Test environments for configuration testing."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    EMPTY = "empty"  # For testing defaults
    CUSTOM = "custom"  # For custom environment variables


@pytest.fixture
def env_vars(request, monkeypatch) -> Dict[str, str]:
    """
    Fixture to set environment variables for testing.
    
    Args:
        request: Pytest request object with the environment parameter
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Dictionary of environment variables that were set
    """
    # Get the environment from the test parameter or default to development
    env = getattr(request, "param", Environment.DEVELOPMENT)
    
    # Clear existing environment variables that might affect tests
    for key in os.environ.keys():
        if key.startswith(("OCR_", "RABBITMQ_", "S3_")):
            monkeypatch.delenv(key, raising=False)
    
    # Set environment variables based on the requested environment
    env_var_dict = {}
    
    if env == Environment.DEVELOPMENT:
        env_var_dict = DEV_ENV_VARS
    elif env == Environment.STAGING:
        env_var_dict = STAGING_ENV_VARS
    elif env == Environment.PRODUCTION:
        env_var_dict = PRODUCTION_ENV_VARS
    elif env == Environment.EMPTY:
        # Empty environment for testing defaults
        return {}
    elif env == Environment.CUSTOM:
        # Custom environment variables provided by the test
        env_var_dict = getattr(request, "param", {})
        if isinstance(env_var_dict, Environment):
            env_var_dict = {}
    
    # Set the environment variables
    for key, value in env_var_dict.items():
        monkeypatch.setenv(key, value)
    
    return env_var_dict


@pytest.fixture
def mock_env_var(monkeypatch) -> Callable[[str, str], None]:
    """
    Fixture that provides a function to set individual environment variables.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Function to set an environment variable
    """
    def _set_env_var(key: str, value: str) -> None:
        """
        Set an environment variable for testing.
        
        Args:
            key: Environment variable name
            value: Environment variable value
        """
        monkeypatch.setenv(key, value)
    
    return _set_env_var


@pytest.fixture
def mock_env_vars(monkeypatch) -> Callable[[Dict[str, str]], None]:
    """
    Fixture that provides a function to set multiple environment variables.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Function to set multiple environment variables
    """
    def _set_env_vars(env_vars: Dict[str, str]) -> None:
        """
        Set multiple environment variables for testing.
        
        Args:
            env_vars: Dictionary of environment variables
        """
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
    
    return _set_env_vars


@pytest.fixture
def clear_env_vars(monkeypatch) -> Callable[[Optional[List[str]]], None]:
    """
    Fixture that provides a function to clear environment variables.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        
    Returns:
        Function to clear environment variables
    """
    def _clear_env_vars(prefixes: Optional[List[str]] = None) -> None:
        """
        Clear environment variables with specified prefixes.
        
        Args:
            prefixes: List of environment variable prefixes to clear
                     If None, clears OCR_, RABBITMQ_, and S3_ variables
        """
        if prefixes is None:
            prefixes = ["OCR_", "RABBITMQ_", "S3_"]
        
        for key in list(os.environ.keys()):
            if any(key.startswith(prefix) for prefix in prefixes):
                monkeypatch.delenv(key, raising=False)
    
    return _clear_env_vars


@pytest.fixture
def mock_service_config() -> ServiceConfig:
    """
    Fixture that provides a sample ServiceConfig for testing.
    
    Returns:
        Sample ServiceConfig object
    """
    return {
        "name": "ocr-service",
        "version": "1.0.0",
        "port": 8080,
        "environment": EnvironmentType.DEVELOPMENT,
        "debug": True,
        "correlation_id_header": "X-Correlation-ID",
        "max_workers": 4,
        "shutdown_timeout": 30
    }


@pytest.fixture
def mock_tensorflow_config() -> TensorFlowConfig:
    """
    Fixture that provides a sample TensorFlowConfig for testing.
    
    Returns:
        Sample TensorFlowConfig object
    """
    return {
        "models_path": "/app/models",
        "typed_model_name": "typed_text_model",
        "handwritten_model_name": "handwritten_text_model",
        "hybrid_model_name": "hybrid_text_model",
        "confidence_threshold": 0.85,
        "low_confidence_threshold": 0.60,
        "gpu_memory_limit": 0,
        "use_gpu": False,
        "batch_size": 4,
        "model_version": "1.0.0",
        "enable_optimization": False
    }


@pytest.fixture
def mock_rabbitmq_config() -> RabbitMQConfig:
    """
    Fixture that provides a sample RabbitMQConfig for testing.
    
    Returns:
        Sample RabbitMQConfig object
    """
    return {
        "host": "localhost",
        "port": 5672,
        "username": "guest",
        "password": "guest",
        "vhost": "/",
        "exchange": "mca.documents",
        "queue": "data-extraction",
        "routing_key": "",
        "use_tls": False,
        "cert_path": "/app/certs/client.pem",
        "key_path": "/app/certs/client.key",
        "ca_path": "/app/certs/ca.pem",
        "prefetch_count": 10,
        "connection_attempts": 3,
        "retry_delay": 5,
        "heartbeat": 60
    }


@pytest.fixture
def mock_s3_config() -> S3Config:
    """
    Fixture that provides a sample S3Config for testing.
    
    Returns:
        Sample S3Config object
    """
    return {
        "endpoint": "http://localhost:9000",
        "region": "us-east-1",
        "bucket": "mca-documents-staging",
        "access_key": "minioadmin",
        "secret_key": "minioadmin",
        "use_ssl": False,
        "verify_ssl": False,
        "encryption": "AES256",
        "presigned_url_expiry": 3600,
        "max_pool_connections": 10,
        "connect_timeout": 5,
        "read_timeout": 60
    }


@pytest.fixture
def mock_logging_config() -> LoggingConfig:
    """
    Fixture that provides a sample LoggingConfig for testing.
    
    Returns:
        Sample LoggingConfig object
    """
    return {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file_path": "",
        "max_bytes": 10485760,
        "backup_count": 5,
        "json_format": False,
        "include_correlation_id": True
    }


# Helper functions for testing configuration validation

def assert_env_var_loaded(config_value: Any, env_var_value: str, converter: Callable = None) -> None:
    """
    Assert that an environment variable was correctly loaded into a configuration value.
    
    Args:
        config_value: The configuration value to check
        env_var_value: The environment variable value to compare against
        converter: Optional function to convert the environment variable value
                  to the expected type
    """
    if converter:
        expected_value = converter(env_var_value)
    else:
        expected_value = env_var_value
    
    assert config_value == expected_value, f"Expected {expected_value}, got {config_value}"


def assert_default_applied(config_value: Any, default_value: Any) -> None:
    """
    Assert that a default value was correctly applied to a configuration value.
    
    Args:
        config_value: The configuration value to check
        default_value: The default value to compare against
    """
    assert config_value == default_value, f"Expected default {default_value}, got {config_value}"


def assert_env_specific_override(config_value: Any, expected_value: Any, env: str) -> None:
    """
    Assert that an environment-specific override was correctly applied.
    
    Args:
        config_value: The configuration value to check
        expected_value: The expected value after the override
        env: The environment name for error messages
    """
    assert config_value == expected_value, f"Expected {expected_value} for {env}, got {config_value}"


# Utility class for testing configuration validation errors
class ValidationError(Exception):
    """Exception raised for configuration validation errors."""
    pass


@pytest.fixture
def expect_validation_error() -> Callable[[Callable, str], None]:
    """
    Fixture that provides a function to test for validation errors.
    
    Returns:
        Function to test for validation errors
    """
    def _expect_validation_error(func: Callable, expected_message: str) -> None:
        """
        Test that a function raises a ValueError with the expected message.
        
        Args:
            func: Function that should raise a ValueError
            expected_message: Expected error message
        """
        with pytest.raises(ValueError) as excinfo:
            func()
        
        assert expected_message in str(excinfo.value), f"Expected error message '{expected_message}', got '{str(excinfo.value)}'"
    
    return _expect_validation_error