#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest fixtures and utilities for testing OCR Service configuration modules.

This module provides fixtures for mocking environment variables, configuration objects,
and helper functions for testing configuration loading, validation, and defaults.
It enables consistent test environments across all configuration test modules.

Fixtures:
    - env_vars: Mock environment variables for testing
    - clear_env_vars: Clear specific environment variables
    - dev_env_vars: Environment variables for development environment
    - staging_env_vars: Environment variables for staging environment
    - prod_env_vars: Environment variables for production environment
    - mock_app_config: Mock AppConfig object for testing
    - mock_rabbitmq_config: Mock RabbitMQ configuration for testing
    - mock_s3_config: Mock S3 configuration for testing
    - mock_tensorflow_config: Mock TensorFlow configuration for testing
    - mock_logging_config: Mock logging configuration for testing
    - config_validator: Helper for testing configuration validation
    - config_defaults: Helper for testing configuration defaults
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Optional, Callable
import json
from pathlib import Path

# Import configuration classes for type hints
from src.config.app_config import AppConfig, Environment, LogLevel


# ===== Environment Variable Fixtures =====

@pytest.fixture
def env_vars(monkeypatch) -> Dict[str, str]:
    """
    Fixture to set and manage environment variables for testing.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
        
    Returns:
        A dictionary of environment variables that were set
        
    Example:
        def test_config_loading(env_vars):
            env_vars['RABBITMQ_HOST'] = 'test-host'
            # Test code that uses RABBITMQ_HOST
    """
    test_env_vars = {}
    
    def _set_env_var(name: str, value: str) -> None:
        test_env_vars[name] = value
        monkeypatch.setenv(name, value)
    
    # Create a dictionary with a custom __setitem__ method
    # to automatically call monkeypatch.setenv
    class EnvVarDict(dict):
        def __setitem__(self, key, value):
            _set_env_var(key, value)
            super().__setitem__(key, value)
    
    return EnvVarDict()


@pytest.fixture
def clear_env_vars(monkeypatch) -> Callable[[List[str]], None]:
    """
    Fixture to clear specific environment variables for testing.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
        
    Returns:
        A function that clears the specified environment variables
        
    Example:
        def test_missing_env_var(clear_env_vars):
            clear_env_vars(['RABBITMQ_HOST'])
            # Test code that should handle missing RABBITMQ_HOST
    """
    def _clear_vars(var_names: List[str]) -> None:
        for name in var_names:
            monkeypatch.delenv(name, raising=False)
    
    return _clear_vars


@pytest.fixture
def dev_env_vars(env_vars) -> Dict[str, str]:
    """
    Fixture to set environment variables for development environment.
    
    Args:
        env_vars: The env_vars fixture
        
    Returns:
        A dictionary of environment variables for development
    """
    # Set development environment
    env_vars['ENVIRONMENT'] = 'development'
    
    # Server settings
    env_vars['HOST'] = 'localhost'
    env_vars['PORT'] = '8080'
    
    # RabbitMQ settings
    env_vars['RABBITMQ_HOST'] = 'localhost'
    env_vars['RABBITMQ_PORT'] = '5672'
    env_vars['RABBITMQ_USERNAME'] = 'guest'
    env_vars['RABBITMQ_PASSWORD'] = 'guest'
    env_vars['RABBITMQ_VHOST'] = '/'
    env_vars['RABBITMQ_EXCHANGE'] = 'mca.documents'
    env_vars['RABBITMQ_QUEUE'] = 'data-extraction'
    env_vars['RABBITMQ_USE_TLS'] = 'false'
    
    # S3 settings
    env_vars['S3_ENDPOINT'] = 'localhost:4566'
    env_vars['S3_REGION'] = 'us-east-1'
    env_vars['S3_ACCESS_KEY'] = 'test'
    env_vars['S3_SECRET_KEY'] = 'test'
    env_vars['S3_BUCKET'] = 'mca-documents-development'
    env_vars['S3_USE_SSL'] = 'false'
    env_vars['S3_VERIFY_SSL'] = 'false'
    
    # TensorFlow settings
    env_vars['TF_MODEL_PATH'] = './models'
    env_vars['TF_USE_GPU'] = 'false'
    env_vars['TF_CONFIDENCE_THRESHOLD'] = '0.75'
    
    # Logging settings
    env_vars['LOG_LEVEL'] = 'DEBUG'
    env_vars['LOG_FORMAT'] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Performance settings
    env_vars['BATCH_SIZE'] = '10'
    env_vars['MAX_WORKERS'] = '4'
    env_vars['PROCESSING_TIMEOUT'] = '300'
    
    return env_vars


@pytest.fixture
def staging_env_vars(env_vars) -> Dict[str, str]:
    """
    Fixture to set environment variables for staging environment.
    
    Args:
        env_vars: The env_vars fixture
        
    Returns:
        A dictionary of environment variables for staging
    """
    # Set staging environment
    env_vars['ENVIRONMENT'] = 'staging'
    
    # Server settings
    env_vars['HOST'] = '0.0.0.0'
    env_vars['PORT'] = '8080'
    
    # RabbitMQ settings
    env_vars['RABBITMQ_HOST'] = 'rabbitmq.staging'
    env_vars['RABBITMQ_PORT'] = '5671'
    env_vars['RABBITMQ_USERNAME'] = 'mca-service'
    env_vars['RABBITMQ_PASSWORD'] = 'staging-password'
    env_vars['RABBITMQ_VHOST'] = '/mca'
    env_vars['RABBITMQ_EXCHANGE'] = 'mca.documents'
    env_vars['RABBITMQ_QUEUE'] = 'data-extraction'
    env_vars['RABBITMQ_USE_TLS'] = 'true'
    env_vars['RABBITMQ_CLIENT_CERT'] = '/etc/rabbitmq/certs/client.pem'
    env_vars['RABBITMQ_CLIENT_KEY'] = '/etc/rabbitmq/certs/client.key'
    env_vars['RABBITMQ_CA_CERT'] = '/etc/rabbitmq/certs/ca.pem'
    
    # S3 settings
    env_vars['S3_ENDPOINT'] = 's3.amazonaws.com'
    env_vars['S3_REGION'] = 'us-east-1'
    env_vars['S3_ACCESS_KEY'] = 'staging-access-key'
    env_vars['S3_SECRET_KEY'] = 'staging-secret-key'
    env_vars['S3_BUCKET'] = 'mca-documents-staging'
    env_vars['S3_USE_SSL'] = 'true'
    env_vars['S3_VERIFY_SSL'] = 'true'
    
    # TensorFlow settings
    env_vars['TF_MODEL_PATH'] = '/models'
    env_vars['TF_USE_GPU'] = 'true'
    env_vars['TF_GPU_MEMORY_LIMIT'] = '8192'
    env_vars['TF_CONFIDENCE_THRESHOLD'] = '0.85'
    
    # Logging settings
    env_vars['LOG_LEVEL'] = 'INFO'
    env_vars['LOG_FORMAT'] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    env_vars['LOG_FILE'] = '/var/log/ocr-service/service.log'
    
    # Performance settings
    env_vars['BATCH_SIZE'] = '20'
    env_vars['MAX_WORKERS'] = '8'
    env_vars['PROCESSING_TIMEOUT'] = '300'
    
    return env_vars


@pytest.fixture
def prod_env_vars(env_vars) -> Dict[str, str]:
    """
    Fixture to set environment variables for production environment.
    
    Args:
        env_vars: The env_vars fixture
        
    Returns:
        A dictionary of environment variables for production
    """
    # Set production environment
    env_vars['ENVIRONMENT'] = 'production'
    
    # Server settings
    env_vars['HOST'] = '0.0.0.0'
    env_vars['PORT'] = '8080'
    
    # RabbitMQ settings
    env_vars['RABBITMQ_HOST'] = 'rabbitmq.production'
    env_vars['RABBITMQ_PORT'] = '5671'
    env_vars['RABBITMQ_USERNAME'] = 'mca-service'
    env_vars['RABBITMQ_PASSWORD'] = 'production-password'
    env_vars['RABBITMQ_VHOST'] = '/mca'
    env_vars['RABBITMQ_EXCHANGE'] = 'mca.documents'
    env_vars['RABBITMQ_QUEUE'] = 'data-extraction'
    env_vars['RABBITMQ_USE_TLS'] = 'true'
    env_vars['RABBITMQ_CLIENT_CERT'] = '/etc/rabbitmq/certs/client.pem'
    env_vars['RABBITMQ_CLIENT_KEY'] = '/etc/rabbitmq/certs/client.key'
    env_vars['RABBITMQ_CA_CERT'] = '/etc/rabbitmq/certs/ca.pem'
    
    # S3 settings
    env_vars['S3_ENDPOINT'] = 's3.amazonaws.com'
    env_vars['S3_REGION'] = 'us-east-1'
    env_vars['S3_ACCESS_KEY'] = 'production-access-key'
    env_vars['S3_SECRET_KEY'] = 'production-secret-key'
    env_vars['S3_BUCKET'] = 'mca-documents-production'
    env_vars['S3_USE_SSL'] = 'true'
    env_vars['S3_VERIFY_SSL'] = 'true'
    
    # TensorFlow settings
    env_vars['TF_MODEL_PATH'] = '/models'
    env_vars['TF_USE_GPU'] = 'true'
    env_vars['TF_GPU_MEMORY_LIMIT'] = '16384'
    env_vars['TF_CONFIDENCE_THRESHOLD'] = '0.90'
    
    # Logging settings
    env_vars['LOG_LEVEL'] = 'INFO'
    env_vars['LOG_FORMAT'] = '%(asctime)s - %(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s'
    env_vars['LOG_FILE'] = '/var/log/ocr-service/service.log'
    
    # Performance settings
    env_vars['BATCH_SIZE'] = '30'
    env_vars['MAX_WORKERS'] = '16'
    env_vars['PROCESSING_TIMEOUT'] = '300'
    
    return env_vars


# ===== Mock Configuration Fixtures =====

@pytest.fixture
def mock_app_config() -> AppConfig:
    """
    Fixture to provide a mock AppConfig object for testing.
    
    Returns:
        A mock AppConfig object with test values
    """
    config = MagicMock(spec=AppConfig)
    
    # Service information
    config.SERVICE_NAME = 'ocr-service-test'
    config.SERVICE_VERSION = '1.0.0-test'
    
    # Environment
    config.ENVIRONMENT = Environment.DEVELOPMENT
    
    # Server settings
    config.HOST = 'localhost'
    config.PORT = 8080
    
    # RabbitMQ configuration
    config.RABBITMQ_HOST = 'localhost'
    config.RABBITMQ_PORT = 5672
    config.RABBITMQ_USERNAME = 'guest'
    config.RABBITMQ_PASSWORD = 'guest'
    config.RABBITMQ_VHOST = '/'
    config.RABBITMQ_EXCHANGE = 'mca.documents'
    config.RABBITMQ_QUEUE = 'data-extraction'
    config.RABBITMQ_USE_TLS = False
    config.RABBITMQ_CLIENT_CERT = None
    config.RABBITMQ_CLIENT_KEY = None
    config.RABBITMQ_CA_CERT = None
    
    # S3 configuration
    config.S3_ENDPOINT = 'localhost:4566'
    config.S3_REGION = 'us-east-1'
    config.S3_ACCESS_KEY = 'test'
    config.S3_SECRET_KEY = 'test'
    config.S3_BUCKET = 'mca-documents-development'
    config.S3_USE_SSL = False
    config.S3_VERIFY_SSL = False
    
    # TensorFlow configuration
    config.TF_MODEL_PATH = './models'
    config.TF_USE_GPU = False
    config.TF_GPU_MEMORY_LIMIT = None
    config.TF_CONFIDENCE_THRESHOLD = 0.75
    
    # Logging configuration
    config.LOG_LEVEL = LogLevel.DEBUG
    config.LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    config.LOG_FILE = None
    
    # Performance settings
    config.BATCH_SIZE = 10
    config.MAX_WORKERS = 4
    config.PROCESSING_TIMEOUT = 300
    
    # Mock methods
    config.as_dict.return_value = {
        'SERVICE_NAME': 'ocr-service-test',
        'SERVICE_VERSION': '1.0.0-test',
        'ENVIRONMENT': Environment.DEVELOPMENT,
        'HOST': 'localhost',
        'PORT': 8080,
        'RABBITMQ_HOST': 'localhost',
        'RABBITMQ_PORT': 5672,
        'RABBITMQ_USERNAME': 'guest',
        'RABBITMQ_PASSWORD': 'guest',
        'RABBITMQ_VHOST': '/',
        'RABBITMQ_EXCHANGE': 'mca.documents',
        'RABBITMQ_QUEUE': 'data-extraction',
        'RABBITMQ_USE_TLS': False,
        'RABBITMQ_CLIENT_CERT': None,
        'RABBITMQ_CLIENT_KEY': None,
        'RABBITMQ_CA_CERT': None,
        'S3_ENDPOINT': 'localhost:4566',
        'S3_REGION': 'us-east-1',
        'S3_ACCESS_KEY': 'test',
        'S3_SECRET_KEY': 'test',
        'S3_BUCKET': 'mca-documents-development',
        'S3_USE_SSL': False,
        'S3_VERIFY_SSL': False,
        'TF_MODEL_PATH': './models',
        'TF_USE_GPU': False,
        'TF_GPU_MEMORY_LIMIT': None,
        'TF_CONFIDENCE_THRESHOLD': 0.75,
        'LOG_LEVEL': LogLevel.DEBUG,
        'LOG_FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'LOG_FILE': None,
        'BATCH_SIZE': 10,
        'MAX_WORKERS': 4,
        'PROCESSING_TIMEOUT': 300
    }
    
    return config


@pytest.fixture
def mock_rabbitmq_config() -> Dict[str, Any]:
    """
    Fixture to provide mock RabbitMQ configuration for testing.
    
    Returns:
        A dictionary with RabbitMQ configuration values
    """
    return {
        'host': 'localhost',
        'port': 5672,
        'username': 'guest',
        'password': 'guest',
        'vhost': '/',
        'exchange': 'mca.documents',
        'queue': 'data-extraction',
        'routing_key': 'ocr.extraction',
        'use_tls': False,
        'client_cert': None,
        'client_key': None,
        'ca_cert': None,
        'connection_attempts': 3,
        'retry_delay': 5,
        'heartbeat': 60
    }


@pytest.fixture
def mock_s3_config() -> Dict[str, Any]:
    """
    Fixture to provide mock S3 configuration for testing.
    
    Returns:
        A dictionary with S3 configuration values
    """
    return {
        'endpoint': 'localhost:4566',
        'region': 'us-east-1',
        'access_key': 'test',
        'secret_key': 'test',
        'bucket': 'mca-documents-development',
        'use_ssl': False,
        'verify_ssl': False,
        'encryption_key': 'test-encryption-key',
        'timeout': 30,
        'max_retries': 3,
        'retry_mode': 'standard'
    }


@pytest.fixture
def mock_tensorflow_config() -> Dict[str, Any]:
    """
    Fixture to provide mock TensorFlow configuration for testing.
    
    Returns:
        A dictionary with TensorFlow configuration values
    """
    return {
        'model_path': './models',
        'use_gpu': False,
        'gpu_memory_limit': None,
        'confidence_threshold': 0.75,
        'typed_model': 'typed_model_v1',
        'handwritten_model': 'handwritten_model_v1',
        'hybrid_model': 'hybrid_model_v1',
        'batch_size': 10,
        'image_size': (1024, 768),
        'channels': 3,
        'preprocessing_steps': ['resize', 'normalize'],
        'language': 'en'
    }


@pytest.fixture
def mock_logging_config() -> Dict[str, Any]:
    """
    Fixture to provide mock logging configuration for testing.
    
    Returns:
        A dictionary with logging configuration values
    """
    return {
        'level': 'DEBUG',
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file': None,
        'console': True,
        'json_format': False,
        'include_correlation_id': False,
        'include_request_id': False,
        'include_timestamp': True
    }


# ===== Configuration Testing Utilities =====

@pytest.fixture
def config_validator() -> Callable[[Dict[str, Any], List[str]], None]:
    """
    Fixture to provide a helper function for testing configuration validation.
    
    Returns:
        A function that validates configuration against required fields
        
    Example:
        def test_config_validation(config_validator, mock_rabbitmq_config):
            config_validator(mock_rabbitmq_config, ['host', 'port', 'username'])
    """
    def _validate_config(config: Dict[str, Any], required_fields: List[str]) -> None:
        """
        Validate that a configuration dictionary contains all required fields.
        
        Args:
            config: The configuration dictionary to validate
            required_fields: List of field names that must be present
            
        Raises:
            AssertionError: If any required field is missing
        """
        for field in required_fields:
            assert field in config, f"Required field '{field}' is missing from configuration"
            assert config[field] is not None, f"Required field '{field}' is None"
    
    return _validate_config


@pytest.fixture
def config_defaults() -> Callable[[Dict[str, Any], Dict[str, Any]], None]:
    """
    Fixture to provide a helper function for testing configuration defaults.
    
    Returns:
        A function that checks if configuration values match expected defaults
        
    Example:
        def test_config_defaults(config_defaults, mock_rabbitmq_config):
            expected_defaults = {'host': 'localhost', 'port': 5672}
            config_defaults(mock_rabbitmq_config, expected_defaults)
    """
    def _check_defaults(config: Dict[str, Any], expected_defaults: Dict[str, Any]) -> None:
        """
        Check if configuration values match expected defaults.
        
        Args:
            config: The configuration dictionary to check
            expected_defaults: Dictionary of expected default values
            
        Raises:
            AssertionError: If any default value doesn't match
        """
        for key, expected_value in expected_defaults.items():
            assert key in config, f"Expected default field '{key}' is missing from configuration"
            assert config[key] == expected_value, f"Default value for '{key}' is {config[key]}, expected {expected_value}"
    
    return _check_defaults


@pytest.fixture
def env_var_setter(monkeypatch) -> Callable[[Dict[str, str]], None]:
    """
    Fixture to provide a helper function for setting multiple environment variables at once.
    
    Args:
        monkeypatch: pytest's monkeypatch fixture
        
    Returns:
        A function that sets multiple environment variables
        
    Example:
        def test_env_vars(env_var_setter):
            env_var_setter({'RABBITMQ_HOST': 'test-host', 'RABBITMQ_PORT': '1234'})
            # Test code that uses these environment variables
    """
    def _set_env_vars(env_vars: Dict[str, str]) -> None:
        """
        Set multiple environment variables at once.
        
        Args:
            env_vars: Dictionary of environment variable names and values
        """
        for name, value in env_vars.items():
            monkeypatch.setenv(name, value)
    
    return _set_env_vars


@pytest.fixture
def env_file_creator() -> Callable[[Dict[str, str], Path], Path]:
    """
    Fixture to provide a helper function for creating .env files for testing.
    
    Returns:
        A function that creates a .env file with specified variables
        
    Example:
        def test_env_file_loading(env_file_creator, tmp_path):
            env_file = env_file_creator({'RABBITMQ_HOST': 'test-host'}, tmp_path)
            # Test code that loads from this .env file
    """
    def _create_env_file(env_vars: Dict[str, str], directory: Path) -> Path:
        """
        Create a .env file with specified variables.
        
        Args:
            env_vars: Dictionary of environment variable names and values
            directory: Directory where the .env file should be created
            
        Returns:
            Path to the created .env file
        """
        env_file = directory / ".env"
        with open(env_file, "w") as f:
            for name, value in env_vars.items():
                f.write(f"{name}={value}\n")
        return env_file
    
    return _create_env_file


@pytest.fixture
def config_file_creator() -> Callable[[Dict[str, Any], Path, str], Path]:
    """
    Fixture to provide a helper function for creating configuration files for testing.
    
    Returns:
        A function that creates a configuration file with specified values
        
    Example:
        def test_config_file_loading(config_file_creator, tmp_path):
            config_file = config_file_creator({'rabbitmq': {'host': 'test-host'}}, tmp_path, 'config.json')
            # Test code that loads from this config file
    """
    def _create_config_file(config: Dict[str, Any], directory: Path, filename: str) -> Path:
        """
        Create a configuration file with specified values.
        
        Args:
            config: Dictionary of configuration values
            directory: Directory where the config file should be created
            filename: Name of the config file
            
        Returns:
            Path to the created config file
        """
        config_file = directory / filename
        with open(config_file, "w") as f:
            json.dump(config, f, indent=2)
        return config_file
    
    return _create_config_file