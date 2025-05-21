#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Pytest fixtures and utilities for testing Document Service configuration modules.

This module provides fixtures and helper functions for testing configuration loading,
validation, and defaults. It ensures consistent test environments across all
configuration test modules.

Fixtures:
    - mock_env: Mock environment variables for testing
    - mock_env_development: Mock environment variables for development environment
    - mock_env_staging: Mock environment variables for staging environment
    - mock_env_production: Mock environment variables for production environment
    - mock_app_config: Mock application configuration object
    - mock_service_config: Mock service configuration object
    - mock_model_config: Mock model configuration object
    - mock_rabbitmq_config: Mock RabbitMQ configuration object
    - mock_s3_config: Mock S3 configuration object
    - mock_logging_config: Mock logging configuration object

Utilities:
    - validate_config_defaults: Validate configuration defaults
    - validate_env_override: Validate environment variable overrides
    - validate_required_config: Validate required configuration values
"""

import os
import sys
import json
import pytest
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Iterator, List
from unittest.mock import patch, MagicMock

# Add the src directory to the Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import configuration types
from src.types.config import (
    AppConfig,
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
    Environment,
    ConfigDict,
    LogLevel
)


# Environment variable fixture
@pytest.fixture
def mock_env(monkeypatch) -> Callable[[Dict[str, str]], None]:
    """
    Fixture to mock environment variables for testing.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        
    Returns:
        Function to set environment variables
    """
    def _set_env(env_vars: Dict[str, str]) -> None:
        """
        Set environment variables for testing.
        
        Args:
            env_vars: Dictionary of environment variables to set
        """
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
    
    return _set_env


# Environment-specific fixtures
@pytest.fixture
def mock_env_development(mock_env) -> None:
    """
    Fixture to mock environment variables for development environment.
    
    Args:
        mock_env: Fixture to set environment variables
    """
    mock_env({
        "ENVIRONMENT": "development",
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "SERVICE_PORT": "8000",
        "SERVICE_DEBUG": "true",
        "MODEL_TYPE": "random_forest",
        "MODEL_VERSION": "1.0.0",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "guest",
        "RABBITMQ_PASSWORD": "guest",
        "RABBITMQ_VHOST": "/",
        "RABBITMQ_SSL": "false",
        "S3_ENDPOINT_URL": "http://localhost:4566",  # LocalStack endpoint
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key",
        "S3_BUCKET": "mca-documents-development",
        "S3_USE_SSL": "false",
        "S3_VERIFY": "false",
        "LOG_LEVEL": "DEBUG",
        "LOG_CONSOLE": "true",
        "LOG_JSON": "false",  # Plain text logs for development
    })


@pytest.fixture
def mock_env_staging(mock_env) -> None:
    """
    Fixture to mock environment variables for staging environment.
    
    Args:
        mock_env: Fixture to set environment variables
    """
    mock_env({
        "ENVIRONMENT": "staging",
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "SERVICE_PORT": "8000",
        "SERVICE_DEBUG": "false",
        "MODEL_TYPE": "random_forest",
        "MODEL_VERSION": "1.0.0",
        "RABBITMQ_HOST": "rabbitmq.staging",
        "RABBITMQ_PORT": "5671",
        "RABBITMQ_USERNAME": "mca-service",
        "RABBITMQ_PASSWORD": "staging-password",
        "RABBITMQ_VHOST": "/",
        "RABBITMQ_SSL": "true",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "staging-access-key",
        "S3_SECRET_KEY": "staging-secret-key",
        "S3_BUCKET": "mca-documents-staging",
        "S3_USE_SSL": "true",
        "S3_VERIFY": "true",
        "LOG_LEVEL": "INFO",
        "LOG_CONSOLE": "true",
        "LOG_JSON": "true",
    })


@pytest.fixture
def mock_env_production(mock_env) -> None:
    """
    Fixture to mock environment variables for production environment.
    
    Args:
        mock_env: Fixture to set environment variables
    """
    mock_env({
        "ENVIRONMENT": "production",
        "SERVICE_NAME": "document-service",
        "SERVICE_VERSION": "1.0.0",
        "SERVICE_PORT": "8000",
        "SERVICE_DEBUG": "false",
        "MODEL_TYPE": "random_forest",
        "MODEL_VERSION": "1.0.0",
        "RABBITMQ_HOST": "rabbitmq.production",
        "RABBITMQ_PORT": "5671",
        "RABBITMQ_USERNAME": "mca-service",
        "RABBITMQ_PASSWORD": "production-password",
        "RABBITMQ_VHOST": "/",
        "RABBITMQ_SSL": "true",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "production-access-key",
        "S3_SECRET_KEY": "production-secret-key",
        "S3_BUCKET": "mca-documents-production",
        "S3_USE_SSL": "true",
        "S3_VERIFY": "true",
        "LOG_LEVEL": "INFO",
        "LOG_CONSOLE": "true",
        "LOG_JSON": "true",
        "LOG_FILE_PATH": "/var/log/document-service/app.log",
    })


# Configuration object fixtures
@pytest.fixture
def mock_service_config() -> ServiceConfig:
    """
    Fixture to create a mock service configuration object.
    
    Returns:
        ServiceConfig: Mock service configuration
    """
    return ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.DEVELOPMENT,
        debug=True,
        base_path=Path("/app")
    )


@pytest.fixture
def mock_model_config() -> ModelConfig:
    """
    Fixture to create a mock model configuration object.
    
    Returns:
        ModelConfig: Mock model configuration
    """
    return ModelConfig(
        model_type="random_forest",
        parameters={
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42
        },
        confidence_threshold=0.75,
        version="1.0.0",
        description="Document classification model for testing"
    )


@pytest.fixture
def mock_rabbitmq_config() -> RabbitMQConfig:
    """
    Fixture to create a mock RabbitMQ configuration object.
    
    Returns:
        RabbitMQConfig: Mock RabbitMQ configuration
    """
    return RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        virtual_host="/",
        ssl=False,
        heartbeat=60,
        connection_attempts=3,
        retry_delay=5
    )


@pytest.fixture
def mock_s3_config() -> S3Config:
    """
    Fixture to create a mock S3 configuration object.
    
    Returns:
        S3Config: Mock S3 configuration
    """
    return {
        "endpoint_url": "http://localhost:4566",
        "region_name": "us-east-1",
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "use_ssl": False,
        "verify": False,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-development",
        "encryption": "AES256"
    }


@pytest.fixture
def mock_logging_config() -> LoggingConfig:
    """
    Fixture to create a mock logging configuration object.
    
    Returns:
        LoggingConfig: Mock logging configuration
    """
    return LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        date_format="%Y-%m-%d %H:%M:%S",
        file_path=None,
        console_output=True,
        json_format=False,
        include_correlation_id=True,
        include_document_id=True
    )


@pytest.fixture
def mock_app_config(
    mock_service_config,
    mock_model_config,
    mock_rabbitmq_config,
    mock_s3_config,
    mock_logging_config
) -> AppConfig:
    """
    Fixture to create a mock application configuration object.
    
    Args:
        mock_service_config: Mock service configuration
        mock_model_config: Mock model configuration
        mock_rabbitmq_config: Mock RabbitMQ configuration
        mock_s3_config: Mock S3 configuration
        mock_logging_config: Mock logging configuration
        
    Returns:
        AppConfig: Mock application configuration
    """
    return AppConfig(
        service=mock_service_config,
        model=mock_model_config,
        rabbitmq=mock_rabbitmq_config,
        s3=mock_s3_config,
        logging=mock_logging_config
    )


# Patch fixtures for mocking imports
@pytest.fixture
def patch_app_config(monkeypatch, mock_app_config) -> None:
    """
    Fixture to patch the app_config module.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_app_config: Mock application configuration
    """
    # Create a mock module
    mock_module = MagicMock()
    mock_module.app_config = mock_app_config
    mock_module.get_app_config.return_value = mock_app_config
    
    # Patch the module
    monkeypatch.setattr("src.config.app_config", mock_module)
    monkeypatch.setattr("src.config.app_config.app_config", mock_app_config)
    monkeypatch.setattr("src.config.app_config.get_app_config", lambda: mock_app_config)


# Context manager for temporarily setting environment variables
class EnvironmentVarContext:
    """
    Context manager for temporarily setting environment variables.
    
    This class provides a context manager that sets environment variables
    for the duration of the context and restores the original values
    when the context exits.
    
    Example:
        with EnvironmentVarContext({"ENVIRONMENT": "production"}):
            # Code that uses the environment variables
    """
    def __init__(self, env_vars: Dict[str, str]):
        self.env_vars = env_vars
        self.original_vars = {}
        
    def __enter__(self):
        # Save original environment variables
        for key, value in self.env_vars.items():
            self.original_vars[key] = os.environ.get(key)
            os.environ[key] = value
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original environment variables
        for key, value in self.original_vars.items():
            if value is None:
                if key in os.environ:
                    del os.environ[key]
            else:
                os.environ[key] = value


# Utility functions for testing configuration
def validate_config_defaults(config: Any, defaults: Dict[str, Any]) -> None:
    """
    Validate that configuration correctly applies defaults.
    
    Args:
        config: Configuration object to validate
        defaults: Dictionary of expected default values
        
    Raises:
        AssertionError: If any default value is not correctly applied
    """
    for key, expected_value in defaults.items():
        if hasattr(config, key):
            actual_value = getattr(config, key)
            assert actual_value == expected_value, f"Default value for {key} is incorrect. Expected {expected_value}, got {actual_value}"
        elif isinstance(config, dict):
            assert key in config, f"Key {key} not found in configuration"
            actual_value = config[key]
            assert actual_value == expected_value, f"Default value for {key} is incorrect. Expected {expected_value}, got {actual_value}"
        else:
            raise ValueError(f"Cannot validate default for {key} in {type(config).__name__}")


def validate_env_override(config_factory: Callable, env_vars: Dict[str, str], expected_values: Dict[str, Any]) -> None:
    """
    Validate that environment variables correctly override configuration defaults.
    
    Args:
        config_factory: Function that creates a configuration object
        env_vars: Dictionary of environment variables to set
        expected_values: Dictionary of expected values after override
        
    Raises:
        AssertionError: If any environment variable override is not correctly applied
    """
    with EnvironmentVarContext(env_vars):
        config = config_factory()
        
        for key, expected_value in expected_values.items():
            if hasattr(config, key):
                actual_value = getattr(config, key)
                assert actual_value == expected_value, f"Environment override for {key} is incorrect. Expected {expected_value}, got {actual_value}"
            elif isinstance(config, dict):
                assert key in config, f"Key {key} not found in configuration"
                actual_value = config[key]
                assert actual_value == expected_value, f"Environment override for {key} is incorrect. Expected {expected_value}, got {actual_value}"
            else:
                raise ValueError(f"Cannot validate override for {key} in {type(config).__name__}")


def validate_required_config(config: Any, required_keys: List[str]) -> None:
    """
    Validate that configuration contains all required keys.
    
    Args:
        config: Configuration object to validate
        required_keys: List of required keys
        
    Raises:
        AssertionError: If any required key is missing
    """
    for key in required_keys:
        if hasattr(config, key):
            assert getattr(config, key) is not None, f"Required key {key} is None"
        elif isinstance(config, dict):
            assert key in config, f"Required key {key} is missing"
            assert config[key] is not None, f"Required key {key} is None"
        else:
            raise ValueError(f"Cannot validate required key {key} in {type(config).__name__}")


# Fixtures for testing with different model types
@pytest.fixture(params=["random_forest", "svm"])
def model_type(request) -> str:
    """
    Fixture to parameterize tests with different model types.
    
    Args:
        request: pytest request object
        
    Returns:
        str: Model type
    """
    return request.param


@pytest.fixture
def mock_model_config_with_type(model_type) -> ModelConfig:
    """
    Fixture to create a mock model configuration with a specific model type.
    
    Args:
        model_type: Model type
        
    Returns:
        ModelConfig: Mock model configuration
    """
    parameters = {}
    
    if model_type == "random_forest":
        parameters = {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42
        }
    elif model_type == "svm":
        parameters = {
            "C": 1.0,
            "kernel": "rbf",
            "gamma": "scale",
            "probability": True,
            "random_state": 42
        }
    
    return ModelConfig(
        model_type=model_type,
        parameters=parameters,
        confidence_threshold=0.75,
        version="1.0.0",
        description=f"{model_type.upper()} model for document classification"
    )


# Fixtures for testing with different environments
@pytest.fixture(params=[Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION])
def environment(request) -> Environment:
    """
    Fixture to parameterize tests with different environments.
    
    Args:
        request: pytest request object
        
    Returns:
        Environment: Environment enum value
    """
    return request.param


@pytest.fixture
def mock_service_config_with_env(environment) -> ServiceConfig:
    """
    Fixture to create a mock service configuration with a specific environment.
    
    Args:
        environment: Environment enum value
        
    Returns:
        ServiceConfig: Mock service configuration
    """
    debug = environment == Environment.DEVELOPMENT
    
    return ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=environment,
        debug=debug,
        base_path=Path("/app")
    )


# Fixtures for testing with different S3 bucket configurations
@pytest.fixture(params=["mca-documents-development", "mca-documents-staging", "mca-documents-production"])
def s3_bucket(request) -> str:
    """
    Fixture to parameterize tests with different S3 bucket names.
    
    Args:
        request: pytest request object
        
    Returns:
        str: S3 bucket name
    """
    return request.param


@pytest.fixture
def mock_s3_config_with_bucket(s3_bucket) -> S3Config:
    """
    Fixture to create a mock S3 configuration with a specific bucket.
    
    Args:
        s3_bucket: S3 bucket name
        
    Returns:
        S3Config: Mock S3 configuration
    """
    # Determine environment from bucket name
    use_ssl = "development" not in s3_bucket
    verify = "development" not in s3_bucket
    endpoint_url = "http://localhost:4566" if "development" in s3_bucket else "https://s3.amazonaws.com"
    
    return {
        "endpoint_url": endpoint_url,
        "region_name": "us-east-1",
        "aws_access_key_id": "test-access-key",
        "aws_secret_access_key": "test-secret-key",
        "use_ssl": use_ssl,
        "verify": verify,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": s3_bucket,
        "encryption": "AES256"
    }


# Fixtures for mocking configuration loading functions
@pytest.fixture
def mock_load_environment_config(monkeypatch) -> MagicMock:
    """
    Fixture to mock the load_environment_config function.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        
    Returns:
        MagicMock: Mock function
    """
    mock_func = MagicMock()
    mock_func.return_value = {
        "debug": True,
        "log_level": "DEBUG",
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "ssl": False,
        },
        "s3": {
            "endpoint_url": "http://localhost:4566",
            "bucket_name": "mca-documents-development",
            "use_ssl": False,
            "verify": False,
        },
        "model": {
            "confidence_threshold": 0.75,
        }
    }
    
    monkeypatch.setattr("src.config.app_config.load_environment_config", mock_func)
    return mock_func


@pytest.fixture
def mock_create_app_config(monkeypatch, mock_app_config) -> MagicMock:
    """
    Fixture to mock the create_app_config function.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        mock_app_config: Mock application configuration
        
    Returns:
        MagicMock: Mock function
    """
    mock_func = MagicMock()
    mock_func.return_value = mock_app_config
    
    monkeypatch.setattr("src.config.app_config.create_app_config", mock_func)
    return mock_func


# Fixtures for testing configuration validation
@pytest.fixture
def mock_validate_config(monkeypatch) -> MagicMock:
    """
    Fixture to mock the validate_config function.
    
    Args:
        monkeypatch: pytest monkeypatch fixture
        
    Returns:
        MagicMock: Mock function
    """
    mock_func = MagicMock()
    
    monkeypatch.setattr("src.config.app_config.validate_config", mock_func)
    return mock_func


@pytest.fixture
def invalid_app_config(mock_app_config) -> AppConfig:
    """
    Fixture to create an invalid application configuration for testing validation.
    
    Args:
        mock_app_config: Mock application configuration
        
    Returns:
        AppConfig: Invalid application configuration
    """
    # Create a copy of the mock configuration with invalid values
    invalid_config = AppConfig(
        service=ServiceConfig(
            name="",  # Invalid: empty name
            version="1.0.0",
            port=8000,
            environment=Environment.DEVELOPMENT,
            debug=True,
            base_path=Path("/app")
        ),
        model=ModelConfig(
            model_type="",  # Invalid: empty model type
            parameters={},
            confidence_threshold=2.0,  # Invalid: confidence threshold > 1
            version="1.0.0",
            description="Invalid model configuration"
        ),
        rabbitmq=RabbitMQConfig(
            host="",  # Invalid: empty host
            port=5672,
            username="guest",
            password="guest",
            virtual_host="/",
            ssl=False,
            heartbeat=60,
            connection_attempts=3,
            retry_delay=5
        ),
        s3={
            "endpoint_url": "http://localhost:4566",
            "region_name": "us-east-1",
            "aws_access_key_id": "",  # Invalid: empty access key
            "aws_secret_access_key": "",  # Invalid: empty secret key
            "use_ssl": False,
            "verify": False,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-development",
            "encryption": "AES256"
        },
        logging=mock_app_config.logging
    )
    
    return invalid_config


# Helper functions for testing configuration loading
@pytest.fixture
def config_from_env_vars() -> Callable[[Dict[str, str]], AppConfig]:
    """
    Fixture to create a configuration object from environment variables.
    
    Returns:
        Callable: Function to create a configuration object from environment variables
    """
    def _create_config(env_vars: Dict[str, str]) -> AppConfig:
        """
        Create a configuration object from environment variables.
        
        Args:
            env_vars: Dictionary of environment variables
            
        Returns:
            AppConfig: Configuration object
        """
        with EnvironmentVarContext(env_vars):
            # Import here to ensure environment variables are set before import
            from src.config.app_config import create_app_config
            return create_app_config()
    
    return _create_config


# Fixtures for testing with different confidence thresholds
@pytest.fixture(params=[0.6, 0.75, 0.85])
def confidence_threshold(request) -> float:
    """
    Fixture to parameterize tests with different confidence thresholds.
    
    Args:
        request: pytest request object
        
    Returns:
        float: Confidence threshold
    """
    return request.param


@pytest.fixture
def mock_model_config_with_threshold(confidence_threshold) -> ModelConfig:
    """
    Fixture to create a mock model configuration with a specific confidence threshold.
    
    Args:
        confidence_threshold: Confidence threshold
        
    Returns:
        ModelConfig: Mock model configuration
    """
    return ModelConfig(
        model_type="random_forest",
        parameters={
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "random_state": 42
        },
        confidence_threshold=confidence_threshold,
        version="1.0.0",
        description=f"Model with {confidence_threshold} confidence threshold"
    )