#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's app_config.py module.

These tests verify that application configuration correctly loads from environment variables,
validates required settings, and provides appropriate defaults for development, staging, and
production environments.

Test coverage includes:
- Loading configuration from environment variables
- Validating required configuration settings
- Environment-specific configuration (development, staging, production)
- Configuration defaults when environment variables are missing
- Configuration validation error handling
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module to test
from src.config.app_config import (
    load_environment_config,
    create_app_config,
    validate_config,
    get_app_config,
    AppConfig,
    Environment
)

# Import configuration types
from src.types.config import ServiceConfig, ModelConfig, RabbitMQConfig, S3Config, LoggingConfig


# ===== Test Environment Configuration Loading =====

@pytest.mark.parametrize(
    "environment,expected_debug,expected_log_level,expected_bucket,expected_threshold",
    [
        ("development", True, "DEBUG", "mca-documents-development", 0.6),
        ("dev", True, "DEBUG", "mca-documents-development", 0.6),
        ("staging", False, "INFO", "mca-documents-staging", 0.75),
        ("stage", False, "INFO", "mca-documents-staging", 0.75),
        ("production", False, "INFO", "mca-documents-production", 0.85),
        ("prod", False, "INFO", "mca-documents-production", 0.85),
        # Test fallback to development for unknown environment
        ("unknown", True, "DEBUG", "mca-documents-development", 0.6),
    ],
)
def test_load_environment_config(environment, expected_debug, expected_log_level, expected_bucket, expected_threshold):
    """Test that environment-specific configuration is loaded correctly."""
    with patch.dict(os.environ, {"ENVIRONMENT": environment}):
        config = load_environment_config()
        
        # Verify common configuration values
        assert config["debug"] == expected_debug
        assert config["log_level"] == expected_log_level
        
        # Verify S3 configuration
        assert config["s3"]["bucket_name"] == expected_bucket
        
        # Verify model configuration
        assert config["model"]["confidence_threshold"] == expected_threshold
        
        # Verify environment-specific RabbitMQ configuration
        if environment in ("development", "dev", "unknown"):
            assert config["rabbitmq"]["host"] == "localhost"
            assert config["rabbitmq"]["port"] == 5672
            assert config["rabbitmq"]["ssl"] is False
        else:
            assert config["rabbitmq"]["ssl"] is True
            assert config["rabbitmq"]["port"] == 5671


def test_load_environment_config_with_custom_rabbitmq_host():
    """Test that RabbitMQ host can be overridden with environment variables."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "staging",
        "RABBITMQ_HOST": "custom-rabbitmq.staging"
    }):
        config = load_environment_config()
        assert config["rabbitmq"]["host"] == "custom-rabbitmq.staging"


# ===== Test AppConfig Creation =====

def test_create_app_config_development():
    """Test creating AppConfig for development environment."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "development",
        "SERVICE_NAME": "test-document-service",
        "SERVICE_VERSION": "1.2.3",
        "SERVICE_PORT": "9000",
        "SERVICE_DEBUG": "true",
        "MODEL_TYPE": "svm",
        "MODEL_VERSION": "2.0.0",
        "RABBITMQ_USERNAME": "test-user",
        "RABBITMQ_PASSWORD": "test-password",
        "RABBITMQ_VHOST": "/test",
        "RABBITMQ_HEARTBEAT": "30",
        "RABBITMQ_CONNECTION_ATTEMPTS": "5",
        "RABBITMQ_RETRY_DELAY": "10",
        "S3_ENDPOINT_URL": "http://custom-s3:4566",
        "S3_REGION": "us-west-2",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key",
        "S3_MAX_POOL_CONNECTIONS": "20",
        "S3_TIMEOUT": "30",
        "S3_RETRIES": "5",
        "S3_BUCKET": "custom-bucket",
        "S3_ENCRYPTION": "aws:kms",
        "LOG_FORMAT": "custom-format",
        "LOG_DATE_FORMAT": "custom-date-format",
        "LOG_FILE_PATH": "/var/log/document-service.log",
        "LOG_CONSOLE": "false",
        "LOG_JSON": "false",
        "LOG_CORRELATION_ID": "false",
        "LOG_DOCUMENT_ID": "false"
    }):
        config = create_app_config()
        
        # Verify service configuration
        assert config.service.name == "test-document-service"
        assert config.service.version == "1.2.3"
        assert config.service.port == 9000
        assert config.service.environment == Environment.DEVELOPMENT
        assert config.service.debug is True
        
        # Verify model configuration
        assert config.model.model_type == "svm"
        assert config.model.version == "2.0.0"
        assert config.model.confidence_threshold == 0.6  # From development config
        
        # Verify RabbitMQ configuration
        assert config.rabbitmq.host == "localhost"  # From development config
        assert config.rabbitmq.port == 5672  # From development config
        assert config.rabbitmq.username == "test-user"
        assert config.rabbitmq.password == "test-password"
        assert config.rabbitmq.virtual_host == "/test"
        assert config.rabbitmq.ssl is False  # From development config
        assert config.rabbitmq.heartbeat == 30
        assert config.rabbitmq.connection_attempts == 5
        assert config.rabbitmq.retry_delay == 10
        
        # Verify S3 configuration
        assert config.s3["endpoint_url"] == "http://custom-s3:4566"
        assert config.s3["region_name"] == "us-west-2"
        assert config.s3["aws_access_key_id"] == "test-access-key"
        assert config.s3["aws_secret_access_key"] == "test-secret-key"
        assert config.s3["use_ssl"] is False  # From development config
        assert config.s3["verify"] is False  # From development config
        assert config.s3["max_pool_connections"] == 20
        assert config.s3["timeout"] == 30
        assert config.s3["retries"] == 5
        assert config.s3["bucket_name"] == "custom-bucket"
        assert config.s3["encryption"] == "aws:kms"
        
        # Verify logging configuration
        assert config.logging.level == "DEBUG"  # From development config
        assert config.logging.format == "custom-format"
        assert config.logging.date_format == "custom-date-format"
        assert config.logging.file_path == "/var/log/document-service.log"
        assert config.logging.console_output is False
        assert config.logging.json_format is False
        assert config.logging.include_correlation_id is False
        assert config.logging.include_document_id is False


def test_create_app_config_production():
    """Test creating AppConfig for production environment."""
    with patch.dict(os.environ, {
        "ENVIRONMENT": "production",
        "SERVICE_NAME": "document-service-prod",
        "SERVICE_VERSION": "1.0.0",
        "SERVICE_PORT": "8080",
        "SERVICE_DEBUG": "false",
        "MODEL_TYPE": "random_forest",
        "MODEL_VERSION": "1.0.0",
        "RABBITMQ_HOST": "rabbitmq-prod.example.com",
        "RABBITMQ_PORT": "5671",
        "RABBITMQ_USERNAME": "prod-user",
        "RABBITMQ_PASSWORD": "prod-password",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "prod-access-key",
        "S3_SECRET_KEY": "prod-secret-key",
        "S3_BUCKET": "mca-documents-production-custom"
    }):
        config = create_app_config()
        
        # Verify service configuration
        assert config.service.name == "document-service-prod"
        assert config.service.version == "1.0.0"
        assert config.service.port == 8080
        assert config.service.environment == Environment.PRODUCTION
        assert config.service.debug is False
        
        # Verify model configuration
        assert config.model.model_type == "random_forest"
        assert config.model.confidence_threshold == 0.85  # From production config
        
        # Verify RabbitMQ configuration
        assert config.rabbitmq.host == "rabbitmq-prod.example.com"
        assert config.rabbitmq.port == 5671
        assert config.rabbitmq.username == "prod-user"
        assert config.rabbitmq.password == "prod-password"
        assert config.rabbitmq.ssl is True  # From production config
        
        # Verify S3 configuration
        assert config.s3["region_name"] == "us-east-1"
        assert config.s3["aws_access_key_id"] == "prod-access-key"
        assert config.s3["aws_secret_access_key"] == "prod-secret-key"
        assert config.s3["use_ssl"] is True  # From production config
        assert config.s3["verify"] is True  # From production config
        assert config.s3["bucket_name"] == "mca-documents-production-custom"


def test_create_app_config_with_defaults():
    """Test creating AppConfig with default values when environment variables are missing."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}, clear=True):
        config = create_app_config()
        
        # Verify service configuration defaults
        assert config.service.name == "document-service"
        assert config.service.version == "1.0.0"
        assert config.service.port == 8000
        assert config.service.environment == Environment.DEVELOPMENT
        assert config.service.debug is True
        
        # Verify model configuration defaults
        assert config.model.model_type == "random_forest"
        assert config.model.confidence_threshold == 0.6  # From development config
        
        # Verify RabbitMQ configuration defaults
        assert config.rabbitmq.host == "localhost"
        assert config.rabbitmq.port == 5672
        assert config.rabbitmq.username == "guest"
        assert config.rabbitmq.password == "guest"
        assert config.rabbitmq.virtual_host == "/"
        assert config.rabbitmq.ssl is False  # From development config
        assert config.rabbitmq.heartbeat == 60
        assert config.rabbitmq.connection_attempts == 3
        assert config.rabbitmq.retry_delay == 5
        
        # Verify S3 configuration defaults
        assert config.s3["endpoint_url"] == "http://localhost:4566"  # From development config
        assert config.s3["region_name"] == "us-east-1"
        assert config.s3["aws_access_key_id"] == ""
        assert config.s3["aws_secret_access_key"] == ""
        assert config.s3["use_ssl"] is False  # From development config
        assert config.s3["verify"] is False  # From development config
        assert config.s3["bucket_name"] == "mca-documents-development"


# ===== Test Configuration Validation =====

def test_validate_config_valid_development():
    """Test validating a valid development configuration."""
    # Create a valid development configuration
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.DEVELOPMENT,
        debug=True
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=0.6
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        ssl=False
    )
    
    s3_config = {
        "endpoint_url": "http://localhost:4566",
        "region_name": "us-east-1",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "use_ssl": False,
        "verify": False,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-development",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should not raise any exceptions
    validate_config(app_config)


def test_validate_config_valid_production():
    """Test validating a valid production configuration."""
    # Create a valid production configuration
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.PRODUCTION,
        debug=False
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=0.85
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="rabbitmq.production",
        port=5671,
        username="prod-user",
        password="prod-password",
        ssl=True
    )
    
    s3_config = {
        "endpoint_url": "https://s3.amazonaws.com",
        "region_name": "us-east-1",
        "aws_access_key_id": "prod-key",
        "aws_secret_access_key": "prod-secret",
        "use_ssl": True,
        "verify": True,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-production",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should not raise any exceptions
    validate_config(app_config)


def test_validate_config_missing_s3_credentials_production():
    """Test validation fails when S3 credentials are missing in production."""
    # Create a production configuration with missing S3 credentials
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.PRODUCTION,
        debug=False
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=0.85
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="rabbitmq.production",
        port=5671,
        username="prod-user",
        password="prod-password",
        ssl=True
    )
    
    s3_config = {
        "endpoint_url": "https://s3.amazonaws.com",
        "region_name": "us-east-1",
        "aws_access_key_id": "",  # Missing credential
        "aws_secret_access_key": "",  # Missing credential
        "use_ssl": True,
        "verify": True,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-production",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should raise ValueError
    with pytest.raises(ValueError, match="S3 credentials are required in production"):
        validate_config(app_config)


def test_validate_config_missing_rabbitmq_host():
    """Test validation fails when RabbitMQ host is missing."""
    # Create a configuration with missing RabbitMQ host
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.DEVELOPMENT,
        debug=True
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=0.6
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="",  # Missing host
        port=5672,
        username="guest",
        password="guest",
        ssl=False
    )
    
    s3_config = {
        "endpoint_url": "http://localhost:4566",
        "region_name": "us-east-1",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "use_ssl": False,
        "verify": False,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-development",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should raise ValueError
    with pytest.raises(ValueError, match="RabbitMQ host is required"):
        validate_config(app_config)


def test_validate_config_missing_rabbitmq_credentials_production():
    """Test validation fails when RabbitMQ credentials are missing in production."""
    # Create a production configuration with missing RabbitMQ credentials
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.PRODUCTION,
        debug=False
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=0.85
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="rabbitmq.production",
        port=5671,
        username="",  # Missing username
        password="",  # Missing password
        ssl=True
    )
    
    s3_config = {
        "endpoint_url": "https://s3.amazonaws.com",
        "region_name": "us-east-1",
        "aws_access_key_id": "prod-key",
        "aws_secret_access_key": "prod-secret",
        "use_ssl": True,
        "verify": True,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-production",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="INFO",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should raise ValueError
    with pytest.raises(ValueError, match="RabbitMQ credentials are required in production"):
        validate_config(app_config)


def test_validate_config_missing_service_name():
    """Test validation fails when service name is missing."""
    # Create a configuration with missing service name
    service_config = ServiceConfig(
        name="",  # Missing name
        version="1.0.0",
        port=8000,
        environment=Environment.DEVELOPMENT,
        debug=True
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=0.6
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        ssl=False
    )
    
    s3_config = {
        "endpoint_url": "http://localhost:4566",
        "region_name": "us-east-1",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "use_ssl": False,
        "verify": False,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-development",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should raise ValueError
    with pytest.raises(ValueError, match="Service name and version are required"):
        validate_config(app_config)


def test_validate_config_missing_model_type():
    """Test validation fails when model type is missing."""
    # Create a configuration with missing model type
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.DEVELOPMENT,
        debug=True
    )
    
    model_config = ModelConfig(
        model_type="",  # Missing model type
        confidence_threshold=0.6
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        ssl=False
    )
    
    s3_config = {
        "endpoint_url": "http://localhost:4566",
        "region_name": "us-east-1",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "use_ssl": False,
        "verify": False,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-development",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should raise ValueError
    with pytest.raises(ValueError, match="Model type is required"):
        validate_config(app_config)


def test_validate_config_invalid_confidence_threshold():
    """Test validation fails when model confidence threshold is invalid."""
    # Create a configuration with invalid confidence threshold
    service_config = ServiceConfig(
        name="document-service",
        version="1.0.0",
        port=8000,
        environment=Environment.DEVELOPMENT,
        debug=True
    )
    
    model_config = ModelConfig(
        model_type="random_forest",
        confidence_threshold=1.5  # Invalid threshold (> 1)
    )
    
    rabbitmq_config = RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        ssl=False
    )
    
    s3_config = {
        "endpoint_url": "http://localhost:4566",
        "region_name": "us-east-1",
        "aws_access_key_id": "test-key",
        "aws_secret_access_key": "test-secret",
        "use_ssl": False,
        "verify": False,
        "max_pool_connections": 10,
        "timeout": 60,
        "retries": 3,
        "bucket_name": "mca-documents-development",
        "encryption": "AES256"
    }
    
    logging_config = LoggingConfig(
        level="DEBUG",
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    app_config = AppConfig(
        service=service_config,
        model=model_config,
        rabbitmq=rabbitmq_config,
        s3=s3_config,
        logging=logging_config
    )
    
    # Validation should raise ValueError
    with pytest.raises(ValueError, match="Model confidence threshold must be between 0 and 1"):
        validate_config(app_config)


# ===== Test Singleton Instance =====

def test_get_app_config():
    """Test that get_app_config returns the singleton instance."""
    # Mock the app_config global variable
    mock_config = MagicMock(spec=AppConfig)
    
    with patch("src.config.app_config.app_config", mock_config):
        config = get_app_config()
        assert config is mock_config


# ===== Test Error Handling =====

def test_app_config_creation_error_handling():
    """Test that errors during app_config creation are properly handled."""
    # Mock create_app_config to raise an exception
    with patch("src.config.app_config.create_app_config", side_effect=ValueError("Test error")), \
         patch("src.config.app_config.logger") as mock_logger, \
         patch("src.config.app_config.sys.exit") as mock_exit:
        
        # Import the module to trigger the exception
        import importlib
        importlib.reload(sys.modules["src.config.app_config"])
        
        # Verify that the error is logged and sys.exit is called
        mock_logger.error.assert_called_once()
        mock_exit.assert_called_once_with(1)