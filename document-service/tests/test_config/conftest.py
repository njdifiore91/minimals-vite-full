#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest fixtures and utilities for testing Document Service configuration modules.

This module provides fixtures and utilities for testing configuration loading,
validation, and defaults. It includes:

1. Fixtures for mocking environment variables
2. Mock configuration objects for testing
3. Helper functions for testing configuration validation
4. Fixtures for simulating different deployment environments
5. Utility functions for testing configuration defaults

These fixtures ensure tests run independently without external dependencies
and can simulate different deployment environments (development, staging, production).
"""

import os
import json
import pytest
from typing import Dict, Any, Optional, List, Callable, Union, cast
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import types from the application
from src.types.config import (
    ConfigDict,
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
    AppConfig,
    EnvironmentType
)

# Constants for test environments
TEST_ENVIRONMENTS = {
    "development": "development",
    "staging": "staging",
    "production": "production"
}

# Default test paths for configuration files and models
TEST_MODEL_BASE_DIR = "/tmp/document-service/models"
TEST_LOGS_DIR = "/tmp/document-service/logs"


# ============================================================================
# Environment Variable Fixtures
# ============================================================================

@pytest.fixture
def mock_env_vars():
    """
    Fixture to mock environment variables for testing.
    
    This fixture provides a clean environment for each test by removing
    any existing environment variables that might affect configuration loading.
    
    Returns:
        function: A function to set environment variables for testing
    """
    # Store original environment variables
    original_env = os.environ.copy()
    
    # Helper function to set environment variables
    def _set_env_vars(env_vars: Dict[str, str]) -> None:
        """
        Set environment variables for testing.
        
        Args:
            env_vars: Dictionary of environment variables to set
        """
        for key, value in env_vars.items():
            os.environ[key] = str(value)
    
    # Yield the helper function
    yield _set_env_vars
    
    # Restore original environment variables
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_env_development(mock_env_vars):
    """
    Fixture to mock environment variables for development environment.
    
    Args:
        mock_env_vars: Fixture to set environment variables
        
    Returns:
        Dict[str, str]: Dictionary of environment variables for development
    """
    env_vars = {
        "ENVIRONMENT": "development",
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "LOG_LEVEL": "DEBUG",
        "MIN_CONFIDENCE_THRESHOLD": "0.6",
        "ENABLE_GPU_ACCELERATION": "False",
        "WORKER_THREADS": "2",
        "BATCH_SIZE": "5",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "guest",
        "RABBITMQ_PASSWORD": "guest",
        "RABBITMQ_VHOST": "/",
        "RABBITMQ_EXCHANGE": "mca.documents.dev",
        "RABBITMQ_SSL": "False",
        "S3_ENDPOINT_URL": "http://localhost:9000",
        "S3_REGION_NAME": "us-east-1",
        "S3_ACCESS_KEY_ID": "minioadmin",
        "S3_SECRET_ACCESS_KEY": "minioadmin",
        "S3_BUCKET_NAME": "mca-documents-development",
        "S3_USE_SSL": "False",
        "MODEL_PATH": f"{TEST_MODEL_BASE_DIR}/development",
    }
    
    mock_env_vars(env_vars)
    return env_vars


@pytest.fixture
def mock_env_staging(mock_env_vars):
    """
    Fixture to mock environment variables for staging environment.
    
    Args:
        mock_env_vars: Fixture to set environment variables
        
    Returns:
        Dict[str, str]: Dictionary of environment variables for staging
    """
    env_vars = {
        "ENVIRONMENT": "staging",
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "LOG_LEVEL": "INFO",
        "MIN_CONFIDENCE_THRESHOLD": "0.7",
        "ENABLE_GPU_ACCELERATION": "True",
        "WORKER_THREADS": "4",
        "BATCH_SIZE": "10",
        "RABBITMQ_HOST": "rabbitmq.staging",
        "RABBITMQ_PORT": "5671",
        "RABBITMQ_USERNAME": "mca_service",
        "RABBITMQ_PASSWORD": "password123",
        "RABBITMQ_VHOST": "/mca",
        "RABBITMQ_EXCHANGE": "mca.documents.staging",
        "RABBITMQ_SSL": "True",
        "RABBITMQ_SSL_CERT_PATH": "/etc/ssl/certs/client.crt",
        "RABBITMQ_SSL_KEY_PATH": "/etc/ssl/private/client.key",
        "RABBITMQ_SSL_CA_CERTS": "/etc/ssl/certs/ca.crt",
        "S3_ENDPOINT_URL": "https://s3.staging.example.com",
        "S3_REGION_NAME": "us-east-1",
        "S3_ACCESS_KEY_ID": "staging_access_key",
        "S3_SECRET_ACCESS_KEY": "staging_secret_key",
        "S3_BUCKET_NAME": "mca-documents-staging",
        "S3_USE_SSL": "True",
        "S3_VERIFY": "True",
        "S3_ENCRYPTION": "AES256",
        "MODEL_PATH": f"{TEST_MODEL_BASE_DIR}/staging",
    }
    
    mock_env_vars(env_vars)
    return env_vars


@pytest.fixture
def mock_env_production(mock_env_vars):
    """
    Fixture to mock environment variables for production environment.
    
    Args:
        mock_env_vars: Fixture to set environment variables
        
    Returns:
        Dict[str, str]: Dictionary of environment variables for production
    """
    env_vars = {
        "ENVIRONMENT": "production",
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        "LOG_LEVEL": "INFO",
        "MIN_CONFIDENCE_THRESHOLD": "0.75",
        "ENABLE_GPU_ACCELERATION": "True",
        "WORKER_THREADS": "8",
        "BATCH_SIZE": "20",
        "RABBITMQ_HOST": "rabbitmq.production",
        "RABBITMQ_PORT": "5671",
        "RABBITMQ_USERNAME": "mca_service",
        "RABBITMQ_PASSWORD": "strong_password_123",
        "RABBITMQ_VHOST": "/mca",
        "RABBITMQ_EXCHANGE": "mca.documents",
        "RABBITMQ_SSL": "True",
        "RABBITMQ_SSL_CERT_PATH": "/etc/ssl/certs/client.crt",
        "RABBITMQ_SSL_KEY_PATH": "/etc/ssl/private/client.key",
        "RABBITMQ_SSL_CA_CERTS": "/etc/ssl/certs/ca.crt",
        "S3_ENDPOINT_URL": "https://s3.amazonaws.com",
        "S3_REGION_NAME": "us-east-1",
        "S3_ACCESS_KEY_ID": "production_access_key",
        "S3_SECRET_ACCESS_KEY": "production_secret_key",
        "S3_BUCKET_NAME": "mca-documents-production",
        "S3_USE_SSL": "True",
        "S3_VERIFY": "True",
        "S3_ENCRYPTION": "AES256",
        "MODEL_PATH": f"{TEST_MODEL_BASE_DIR}/production",
    }
    
    mock_env_vars(env_vars)
    return env_vars


@pytest.fixture
def mock_env_missing_required(mock_env_vars):
    """
    Fixture to mock environment variables with missing required values.
    
    This fixture is useful for testing configuration validation when required
    environment variables are missing.
    
    Args:
        mock_env_vars: Fixture to set environment variables
        
    Returns:
        Dict[str, str]: Dictionary of environment variables with missing required values
    """
    env_vars = {
        "ENVIRONMENT": "development",
        # Missing SERVICE_NAME
        "SERVICE_VERSION": "1.0.0",
        "HOST": "0.0.0.0",
        "PORT": "8000",
        # Missing RABBITMQ_HOST
        "RABBITMQ_PORT": "5672",
        # Missing S3_BUCKET_NAME
        "S3_ENDPOINT_URL": "http://localhost:9000",
    }
    
    mock_env_vars(env_vars)
    return env_vars


@pytest.fixture
def mock_env_invalid_values(mock_env_vars):
    """
    Fixture to mock environment variables with invalid values.
    
    This fixture is useful for testing configuration validation when environment
    variables have invalid values.
    
    Args:
        mock_env_vars: Fixture to set environment variables
        
    Returns:
        Dict[str, str]: Dictionary of environment variables with invalid values
    """
    env_vars = {
        "ENVIRONMENT": "invalid_environment",  # Invalid environment type
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "HOST": "0.0.0.0",
        "PORT": "invalid_port",  # Invalid port
        "LOG_LEVEL": "TRACE",  # Invalid log level
        "MIN_CONFIDENCE_THRESHOLD": "2.0",  # Invalid threshold (> 1.0)
        "RABBITMQ_SSL": "True",
        # Missing SSL cert paths when SSL is enabled
        "S3_ENCRYPTION": "invalid_encryption",  # Invalid encryption type
    }
    
    mock_env_vars(env_vars)
    return env_vars


# ============================================================================
# Mock Configuration Objects
# ============================================================================

@pytest.fixture
def mock_service_config() -> ServiceConfig:
    """
    Fixture to create a mock service configuration.
    
    Returns:
        ServiceConfig: Mock service configuration
    """
    return {
        "name": "document-service",
        "version": "1.0.0",
        "environment": "development",
        "host": "0.0.0.0",
        "port": 8000,
        "debug": True,
        "api_prefix": "/api/v1",
        "allowed_origins": ["http://localhost:3000", "https://app.example.com"],
    }


@pytest.fixture
def mock_model_config() -> ModelConfig:
    """
    Fixture to create a mock model configuration.
    
    Returns:
        ModelConfig: Mock model configuration
    """
    return {
        "model_path": f"{TEST_MODEL_BASE_DIR}/random_forest_classifier_1.0.0.pkl",
        "vectorizer_path": f"{TEST_MODEL_BASE_DIR}/tfidf_vectorizer_1.0.0.pkl",
        "min_confidence_threshold": 0.75,
        "supported_document_types": [
            "APPLICATION",
            "TAX_RETURN",
            "BANK_STATEMENT",
            "PROFIT_LOSS",
            "BALANCE_SHEET",
            "BUSINESS_LICENSE",
            "IDENTITY_DOCUMENT",
            "UTILITY_BILL",
            "CREDIT_CARD_STATEMENT",
            "LEASE_AGREEMENT",
            "INSURANCE_DOCUMENT",
            "INVOICE",
            "OTHER"
        ],
        "batch_size": 10,
        "max_document_size_mb": 10,
        "gpu_acceleration": False,
        "memory_limit_mb": 16384,  # 16GB as per spec
    }


@pytest.fixture
def mock_rabbitmq_config() -> RabbitMQConfig:
    """
    Fixture to create a mock RabbitMQ configuration.
    
    Returns:
        RabbitMQConfig: Mock RabbitMQ configuration
    """
    return {
        "host": "localhost",
        "port": 5672,
        "username": "guest",
        "password": "guest",
        "vhost": "/",
        "exchange": "mca.documents",
        "queue_document_processing": "document-processing",
        "queue_data_extraction": "data-extraction",
        "routing_key": "document.new",
        "ssl": False,
        "ssl_cert_path": None,
        "ssl_key_path": None,
        "ssl_ca_certs": None,
        "heartbeat": 60,
        "connection_timeout": 30,
        "prefetch_count": 10,
    }


@pytest.fixture
def mock_rabbitmq_config_ssl() -> RabbitMQConfig:
    """
    Fixture to create a mock RabbitMQ configuration with SSL enabled.
    
    Returns:
        RabbitMQConfig: Mock RabbitMQ configuration with SSL
    """
    return {
        "host": "rabbitmq.production",
        "port": 5671,
        "username": "mca_service",
        "password": "strong_password_123",
        "vhost": "/mca",
        "exchange": "mca.documents",
        "queue_document_processing": "document-processing",
        "queue_data_extraction": "data-extraction",
        "routing_key": "document.new",
        "ssl": True,
        "ssl_cert_path": "/etc/ssl/certs/client.crt",
        "ssl_key_path": "/etc/ssl/private/client.key",
        "ssl_ca_certs": "/etc/ssl/certs/ca.crt",
        "heartbeat": 60,
        "connection_timeout": 30,
        "prefetch_count": 10,
    }


@pytest.fixture
def mock_s3_config() -> S3Config:
    """
    Fixture to create a mock S3 configuration.
    
    Returns:
        S3Config: Mock S3 configuration
    """
    return {
        "endpoint_url": "http://localhost:9000",
        "region_name": "us-east-1",
        "access_key_id": "minioadmin",
        "secret_access_key": "minioadmin",
        "bucket_name": "mca-documents-development",
        "use_ssl": False,
        "verify": True,
        "encryption": "AES256",
        "presigned_url_expiration": 3600,  # 1 hour
        "max_pool_connections": 10,
    }


@pytest.fixture
def mock_logging_config() -> LoggingConfig:
    """
    Fixture to create a mock logging configuration.
    
    Returns:
        LoggingConfig: Mock logging configuration
    """
    return {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "file_path": f"{TEST_LOGS_DIR}/document-service.log",
        "max_bytes": 10485760,  # 10MB
        "backup_count": 5,
        "json_format": True,
        "include_correlation_id": True,
    }


@pytest.fixture
def mock_app_config(mock_service_config, mock_model_config, mock_rabbitmq_config, mock_s3_config, mock_logging_config) -> AppConfig:
    """
    Fixture to create a mock application configuration.
    
    Args:
        mock_service_config: Mock service configuration
        mock_model_config: Mock model configuration
        mock_rabbitmq_config: Mock RabbitMQ configuration
        mock_s3_config: Mock S3 configuration
        mock_logging_config: Mock logging configuration
        
    Returns:
        AppConfig: Mock application configuration
    """
    return {
        "service": mock_service_config,
        "model": mock_model_config,
        "rabbitmq": mock_rabbitmq_config,
        "s3": mock_s3_config,
        "logging": mock_logging_config,
    }


# ============================================================================
# Helper Functions for Testing Configuration Validation
# ============================================================================

@pytest.fixture
def config_validator():
    """
    Fixture to provide a configuration validator function.
    
    This fixture returns a function that validates a configuration object
    against a schema and returns validation errors.
    
    Returns:
        function: A function to validate configuration objects
    """
    def _validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
        """
        Validate a configuration object against a schema.
        
        Args:
            config: Configuration object to validate
            schema: Schema to validate against
            
        Returns:
            List of validation error messages, or empty list if valid
        """
        errors = []
        
        # Check required fields
        for field, field_schema in schema.items():
            if field_schema.get("required", False) and field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Check field types and constraints
        for field, value in config.items():
            if field in schema:
                field_schema = schema[field]
                field_type = field_schema.get("type")
                
                # Type validation
                if field_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {field} must be a string")
                elif field_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field {field} must be an integer")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be a number")
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field {field} must be a boolean")
                elif field_type == "array" and not isinstance(value, list):
                    errors.append(f"Field {field} must be an array")
                elif field_type == "object" and not isinstance(value, dict):
                    errors.append(f"Field {field} must be an object")
                
                # Constraint validation
                if field_type in ["integer", "number"]:
                    if "minimum" in field_schema and value < field_schema["minimum"]:
                        errors.append(f"Field {field} must be >= {field_schema['minimum']}")
                    if "maximum" in field_schema and value > field_schema["maximum"]:
                        errors.append(f"Field {field} must be <= {field_schema['maximum']}")
                
                if field_type == "string":
                    if "enum" in field_schema and value not in field_schema["enum"]:
                        errors.append(f"Field {field} must be one of {field_schema['enum']}")
                    if "pattern" in field_schema:
                        import re
                        if not re.match(field_schema["pattern"], value):
                            errors.append(f"Field {field} must match pattern {field_schema['pattern']}")
                
                if field_type == "array":
                    if "minItems" in field_schema and len(value) < field_schema["minItems"]:
                        errors.append(f"Field {field} must have at least {field_schema['minItems']} items")
                    if "maxItems" in field_schema and len(value) > field_schema["maxItems"]:
                        errors.append(f"Field {field} must have at most {field_schema['maxItems']} items")
        
        return errors
    
    return _validate_config


@pytest.fixture
def assert_config_valid():
    """
    Fixture to provide a function that asserts a configuration is valid.
    
    This fixture returns a function that validates a configuration object
    and raises an assertion error if it's invalid.
    
    Returns:
        function: A function to assert configuration validity
    """
    def _assert_valid(config: Dict[str, Any], schema: Dict[str, Any]) -> None:
        """
        Assert that a configuration object is valid against a schema.
        
        Args:
            config: Configuration object to validate
            schema: Schema to validate against
            
        Raises:
            AssertionError: If the configuration is invalid
        """
        errors = []
        
        # Check required fields
        for field, field_schema in schema.items():
            if field_schema.get("required", False) and field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Check field types and constraints
        for field, value in config.items():
            if field in schema:
                field_schema = schema[field]
                field_type = field_schema.get("type")
                
                # Type validation
                if field_type == "string" and not isinstance(value, str):
                    errors.append(f"Field {field} must be a string")
                elif field_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field {field} must be an integer")
                elif field_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field {field} must be a number")
                elif field_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field {field} must be a boolean")
                elif field_type == "array" and not isinstance(value, list):
                    errors.append(f"Field {field} must be an array")
                elif field_type == "object" and not isinstance(value, dict):
                    errors.append(f"Field {field} must be an object")
                
                # Constraint validation
                if field_type in ["integer", "number"]:
                    if "minimum" in field_schema and value < field_schema["minimum"]:
                        errors.append(f"Field {field} must be >= {field_schema['minimum']}")
                    if "maximum" in field_schema and value > field_schema["maximum"]:
                        errors.append(f"Field {field} must be <= {field_schema['maximum']}")
                
                if field_type == "string":
                    if "enum" in field_schema and value not in field_schema["enum"]:
                        errors.append(f"Field {field} must be one of {field_schema['enum']}")
                    if "pattern" in field_schema:
                        import re
                        if not re.match(field_schema["pattern"], value):
                            errors.append(f"Field {field} must match pattern {field_schema['pattern']}")
                
                if field_type == "array":
                    if "minItems" in field_schema and len(value) < field_schema["minItems"]:
                        errors.append(f"Field {field} must have at least {field_schema['minItems']} items")
                    if "maxItems" in field_schema and len(value) > field_schema["maxItems"]:
                        errors.append(f"Field {field} must have at most {field_schema['maxItems']} items")
        
        assert not errors, f"Configuration validation failed: {', '.join(errors)}"
    
    return _assert_valid


# ============================================================================
# Utility Functions for Testing Configuration Defaults
# ============================================================================

@pytest.fixture
def check_config_defaults():
    """
    Fixture to provide a function that checks if configuration defaults are applied.
    
    This fixture returns a function that checks if default values are correctly
    applied to a configuration object when values are missing.
    
    Returns:
        function: A function to check configuration defaults
    """
    def _check_defaults(config: Dict[str, Any], defaults: Dict[str, Any]) -> List[str]:
        """
        Check if default values are correctly applied to a configuration object.
        
        Args:
            config: Configuration object to check
            defaults: Default values to check against
            
        Returns:
            List of error messages, or empty list if all defaults are correctly applied
        """
        errors = []
        
        for field, default_value in defaults.items():
            if field not in config:
                errors.append(f"Default value for {field} not applied")
            elif config[field] != default_value:
                errors.append(f"Default value for {field} incorrect: expected {default_value}, got {config[field]}")
        
        return errors
    
    return _check_defaults


@pytest.fixture
def assert_config_defaults():
    """
    Fixture to provide a function that asserts configuration defaults are applied.
    
    This fixture returns a function that asserts default values are correctly
    applied to a configuration object when values are missing.
    
    Returns:
        function: A function to assert configuration defaults
    """
    def _assert_defaults(config: Dict[str, Any], defaults: Dict[str, Any]) -> None:
        """
        Assert that default values are correctly applied to a configuration object.
        
        Args:
            config: Configuration object to check
            defaults: Default values to check against
            
        Raises:
            AssertionError: If defaults are not correctly applied
        """
        for field, default_value in defaults.items():
            assert field in config, f"Default value for {field} not applied"
            assert config[field] == default_value, f"Default value for {field} incorrect: expected {default_value}, got {config[field]}"
    
    return _assert_defaults


# ============================================================================
# Patching Utilities
# ============================================================================

@pytest.fixture
def patch_config_module():
    """
    Fixture to provide a function that patches a configuration module.
    
    This fixture returns a function that patches a configuration module
    with mock values for testing.
    
    Returns:
        function: A function to patch a configuration module
    """
    def _patch_module(module_path: str, **kwargs) -> MagicMock:
        """
        Patch a configuration module with mock values.
        
        Args:
            module_path: Path to the module to patch
            **kwargs: Mock values to patch into the module
            
        Returns:
            MagicMock: Mock object for the patched module
        """
        patcher = patch(module_path, **kwargs)
        mock_module = patcher.start()
        pytest.addFinalizer(patcher.stop)
        return mock_module
    
    return _patch_module


@pytest.fixture
def patch_env_var():
    """
    Fixture to provide a function that patches a single environment variable.
    
    This fixture returns a function that patches a single environment variable
    for testing and restores it after the test.
    
    Returns:
        function: A function to patch an environment variable
    """
    original_values = {}
    
    def _patch_env_var(var_name: str, value: str) -> None:
        """
        Patch a single environment variable.
        
        Args:
            var_name: Name of the environment variable to patch
            value: Value to set for the environment variable
        """
        if var_name in os.environ:
            original_values[var_name] = os.environ[var_name]
        os.environ[var_name] = value
    
    yield _patch_env_var
    
    # Restore original environment variables
    for var_name, value in original_values.items():
        os.environ[var_name] = value