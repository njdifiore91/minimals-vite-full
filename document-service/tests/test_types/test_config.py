"""
Unit tests for configuration type definitions in the Document Service.

This module contains tests for the configuration types defined in
document-service/src/types/config.py, including ConfigDict, ServiceConfig,
ModelConfig, RabbitMQConfig, S3Config, and LoggingConfig.

These tests ensure that the configuration types correctly handle service
configuration and settings, and provide type safety for configuration
access throughout the service.
"""

import os
import unittest
from unittest import mock
from pathlib import Path
import pytest
from typing import Dict, Any

from src.types.config import (
    ConfigDict,
    Environment,
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    get_s3_config_from_env,
    LogLevel,
    LoggingConfig,
    AppConfig
)


class TestConfigDict:
    """Tests for the ConfigDict type alias.
    
    ConfigDict is a type alias for Dict[str, Any] used for configuration dictionaries.
    These tests verify that ConfigDict can be used for various configuration scenarios.
    """
    
    def test_empty_config_dict(self):
        """Test that an empty ConfigDict can be created."""
        config: ConfigDict = {}
        assert isinstance(config, dict)
        assert len(config) == 0
    
    def test_string_values_config_dict(self):
        """Test ConfigDict with string values."""
        config: ConfigDict = {
            "name": "document-service",
            "version": "1.0.0",
            "environment": "production"
        }
        assert isinstance(config, dict)
        assert config["name"] == "document-service"
        assert config["version"] == "1.0.0"
        assert config["environment"] == "production"
    
    def test_mixed_values_config_dict(self):
        """Test ConfigDict with mixed value types."""
        config: ConfigDict = {
            "name": "document-service",
            "port": 8000,
            "debug": True,
            "tags": ["document", "classification"],
            "model_params": {
                "n_estimators": 100,
                "max_depth": 10
            }
        }
        assert isinstance(config, dict)
        assert config["name"] == "document-service"
        assert config["port"] == 8000
        assert config["debug"] is True
        assert isinstance(config["tags"], list)
        assert len(config["tags"]) == 2
        assert isinstance(config["model_params"], dict)
        assert config["model_params"]["n_estimators"] == 100
    
    def test_nested_config_dict(self):
        """Test ConfigDict with nested dictionaries."""
        config: ConfigDict = {
            "service": {
                "name": "document-service",
                "version": "1.0.0"
            },
            "model": {
                "type": "random_forest",
                "params": {
                    "n_estimators": 100,
                    "max_depth": 10
                }
            },
            "logging": {
                "level": "INFO",
                "format": "json"
            }
        }
        assert isinstance(config, dict)
        assert isinstance(config["service"], dict)
        assert config["service"]["name"] == "document-service"
        assert isinstance(config["model"], dict)
        assert isinstance(config["model"]["params"], dict)
        assert config["model"]["params"]["n_estimators"] == 100
        assert config["logging"]["level"] == "INFO"


class TestEnvironment:
    """Tests for the Environment enum.
    
    Environment is an enumeration of deployment environments (development, staging, production).
    These tests verify that Environment enum values can be correctly created and compared.
    """
    
    def test_environment_values(self):
        """Test that Environment enum has the expected values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
    
    def test_environment_comparison(self):
        """Test that Environment enum values can be compared."""
        assert Environment.DEVELOPMENT != Environment.STAGING
        assert Environment.STAGING != Environment.PRODUCTION
        assert Environment.DEVELOPMENT != Environment.PRODUCTION
    
    def test_environment_from_string_exact_match(self):
        """Test conversion from exact string matches to Environment enum."""
        assert Environment.from_string("development") == Environment.DEVELOPMENT
        assert Environment.from_string("staging") == Environment.STAGING
        assert Environment.from_string("production") == Environment.PRODUCTION
    
    def test_environment_from_string_case_insensitive(self):
        """Test case-insensitive conversion from strings to Environment enum."""
        assert Environment.from_string("DEVELOPMENT") == Environment.DEVELOPMENT
        assert Environment.from_string("Staging") == Environment.STAGING
        assert Environment.from_string("Production") == Environment.PRODUCTION
    
    def test_environment_from_string_with_whitespace(self):
        """Test conversion from strings with whitespace to Environment enum."""
        assert Environment.from_string(" development ") == Environment.DEVELOPMENT
        assert Environment.from_string("staging ") == Environment.STAGING
        assert Environment.from_string(" production") == Environment.PRODUCTION
    
    def test_environment_from_string_aliases(self):
        """Test conversion from alias strings to Environment enum."""
        assert Environment.from_string("dev") == Environment.DEVELOPMENT
        assert Environment.from_string("stage") == Environment.STAGING
        assert Environment.from_string("prod") == Environment.PRODUCTION
    
    def test_environment_from_string_invalid(self):
        """Test that invalid strings raise ValueError."""
        with pytest.raises(ValueError):
            Environment.from_string("invalid")
        with pytest.raises(ValueError):
            Environment.from_string("")
        with pytest.raises(ValueError):
            Environment.from_string("test")


class TestServiceConfig:
    """Tests for the ServiceConfig class.
    
    ServiceConfig represents application-wide settings for the Document Service.
    These tests verify that ServiceConfig instances can be correctly created and configured.
    """
    
    def test_service_config_defaults(self):
        """Test that ServiceConfig has the expected default values."""
        config = ServiceConfig()
        assert config.name == "document-service"
        assert config.version == "1.0.0"
        assert config.port == 8000
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug is False
        assert isinstance(config.base_path, Path)
    
    def test_service_config_custom_values(self):
        """Test ServiceConfig with custom values."""
        config = ServiceConfig(
            name="custom-service",
            version="2.0.0",
            port=9000,
            environment=Environment.PRODUCTION,
            debug=True
        )
        assert config.name == "custom-service"
        assert config.version == "2.0.0"
        assert config.port == 9000
        assert config.environment == Environment.PRODUCTION
        assert config.debug is True
    
    @mock.patch.dict(os.environ, {
        "SERVICE_NAME": "env-service",
        "SERVICE_VERSION": "3.0.0",
        "SERVICE_PORT": "7000",
        "SERVICE_ENV": "staging",
        "SERVICE_DEBUG": "true"
    })
    def test_service_config_from_env(self):
        """Test creating ServiceConfig from environment variables."""
        config = ServiceConfig.from_env()
        assert config.name == "env-service"
        assert config.version == "3.0.0"
        assert config.port == 7000
        assert config.environment == Environment.STAGING
        assert config.debug is True
    
    @mock.patch.dict(os.environ, {
        "SERVICE_PORT": "invalid"
    })
    def test_service_config_from_env_invalid_port(self):
        """Test that invalid port in environment variables raises ValueError."""
        with pytest.raises(ValueError):
            ServiceConfig.from_env()
    
    @mock.patch.dict(os.environ, {
        "SERVICE_ENV": "invalid"
    })
    def test_service_config_from_env_invalid_environment(self):
        """Test that invalid environment in environment variables raises ValueError."""
        with pytest.raises(ValueError):
            ServiceConfig.from_env()


class TestModelConfig:
    """Tests for the ModelConfig class.
    
    ModelConfig represents configuration for scikit-learn classification models.
    These tests verify that ModelConfig instances can be correctly created and converted.
    """
    
    def test_model_config_defaults(self):
        """Test that ModelConfig has the expected default values."""
        config = ModelConfig()
        assert config.model_type == "random_forest"
        assert config.parameters == {}
        assert config.confidence_threshold == 0.75
        assert config.version == "1.0.0"
        assert config.description == ""
    
    def test_model_config_custom_values(self):
        """Test ModelConfig with custom values."""
        parameters = {
            "n_estimators": 100,
            "max_depth": 10,
            "min_samples_split": 2
        }
        config = ModelConfig(
            model_type="svm",
            parameters=parameters,
            confidence_threshold=0.85,
            version="2.0.0",
            description="SVM classifier for document types"
        )
        assert config.model_type == "svm"
        assert config.parameters == parameters
        assert config.confidence_threshold == 0.85
        assert config.version == "2.0.0"
        assert config.description == "SVM classifier for document types"
    
    def test_model_config_from_dict(self):
        """Test creating ModelConfig from a dictionary."""
        config_dict: ConfigDict = {
            "model_type": "svm",
            "parameters": {
                "kernel": "rbf",
                "C": 1.0,
                "gamma": "scale"
            },
            "confidence_threshold": 0.9,
            "version": "2.1.0",
            "description": "SVM classifier with RBF kernel"
        }
        config = ModelConfig.from_dict(config_dict)
        assert config.model_type == "svm"
        assert config.parameters["kernel"] == "rbf"
        assert config.parameters["C"] == 1.0
        assert config.parameters["gamma"] == "scale"
        assert config.confidence_threshold == 0.9
        assert config.version == "2.1.0"
        assert config.description == "SVM classifier with RBF kernel"
    
    def test_model_config_from_dict_partial(self):
        """Test creating ModelConfig from a partial dictionary."""
        config_dict: ConfigDict = {
            "model_type": "svm",
            "confidence_threshold": 0.9
        }
        config = ModelConfig.from_dict(config_dict)
        assert config.model_type == "svm"
        assert config.parameters == {}
        assert config.confidence_threshold == 0.9
        assert config.version == "1.0.0"
        assert config.description == ""
    
    def test_model_config_to_dict(self):
        """Test converting ModelConfig to a dictionary."""
        parameters = {
            "n_estimators": 100,
            "max_depth": 10
        }
        config = ModelConfig(
            model_type="random_forest",
            parameters=parameters,
            confidence_threshold=0.8,
            version="1.5.0",
            description="Random Forest classifier"
        )
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["model_type"] == "random_forest"
        assert config_dict["parameters"] == parameters
        assert config_dict["confidence_threshold"] == 0.8
        assert config_dict["version"] == "1.5.0"
        assert config_dict["description"] == "Random Forest classifier"


class TestRabbitMQConfig:
    """Tests for the RabbitMQConfig class.
    
    RabbitMQConfig represents configuration for RabbitMQ connection and exchanges.
    These tests verify that RabbitMQConfig instances can be correctly created and configured.
    """
    
    def test_rabbitmq_config_defaults(self):
        """Test that RabbitMQConfig has the expected default values."""
        config = RabbitMQConfig()
        assert config.host == "localhost"
        assert config.port == 5672
        assert config.username == "guest"
        assert config.password == "guest"
        assert config.virtual_host == "/"
        assert config.ssl is True
        assert config.heartbeat == 60
        assert config.connection_attempts == 3
        assert config.retry_delay == 5
        
        # Check exchange configuration
        assert config.document_exchange["name"] == "mca.documents"
        assert config.document_exchange["type"] == "fanout"
        assert config.document_exchange["durable"] is True
        
        # Check queue configuration
        assert config.document_processing_queue["name"] == "document-processing"
        assert config.document_processing_queue["durable"] is True
        assert "x-dead-letter-exchange" in config.document_processing_queue["arguments"]
    
    def test_rabbitmq_config_custom_values(self):
        """Test RabbitMQConfig with custom values."""
        config = RabbitMQConfig(
            host="rabbitmq.example.com",
            port=5673,
            username="user",
            password="pass",
            virtual_host="/vhost",
            ssl=False,
            heartbeat=30,
            connection_attempts=5,
            retry_delay=10
        )
        assert config.host == "rabbitmq.example.com"
        assert config.port == 5673
        assert config.username == "user"
        assert config.password == "pass"
        assert config.virtual_host == "/vhost"
        assert config.ssl is False
        assert config.heartbeat == 30
        assert config.connection_attempts == 5
        assert config.retry_delay == 10
    
    @mock.patch.dict(os.environ, {
        "RABBITMQ_HOST": "rabbitmq-env.example.com",
        "RABBITMQ_PORT": "5674",
        "RABBITMQ_USERNAME": "env-user",
        "RABBITMQ_PASSWORD": "env-pass",
        "RABBITMQ_VHOST": "/env-vhost",
        "RABBITMQ_SSL": "false",
        "RABBITMQ_HEARTBEAT": "45",
        "RABBITMQ_CONNECTION_ATTEMPTS": "4",
        "RABBITMQ_RETRY_DELAY": "7"
    })
    def test_rabbitmq_config_from_env(self):
        """Test creating RabbitMQConfig from environment variables."""
        config = RabbitMQConfig.from_env()
        assert config.host == "rabbitmq-env.example.com"
        assert config.port == 5674
        assert config.username == "env-user"
        assert config.password == "env-pass"
        assert config.virtual_host == "/env-vhost"
        assert config.ssl is False
        assert config.heartbeat == 45
        assert config.connection_attempts == 4
        assert config.retry_delay == 7
    
    @mock.patch.dict(os.environ, {
        "RABBITMQ_PORT": "invalid"
    })
    def test_rabbitmq_config_from_env_invalid_port(self):
        """Test that invalid port in environment variables raises ValueError."""
        with pytest.raises(ValueError):
            RabbitMQConfig.from_env()


class TestS3Config:
    """Tests for the S3Config class.
    
    S3Config represents configuration for S3-compatible storage.
    These tests verify that S3Config instances can be correctly created and configured.
    """
    
    def test_s3_config_type(self):
        """Test that S3Config is a TypedDict."""
        # Create a valid S3Config
        config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-production",
            "encryption": "AES256"
        }
        assert isinstance(config, dict)
        assert config["endpoint_url"] == "https://s3.amazonaws.com"
        assert config["region_name"] == "us-east-1"
        assert config["aws_access_key_id"] == "access-key"
        assert config["aws_secret_access_key"] == "secret-key"
        assert config["use_ssl"] is True
        assert config["verify"] is True
        assert config["max_pool_connections"] == 10
        assert config["timeout"] == 60
        assert config["retries"] == 3
        assert config["bucket_name"] == "mca-documents-production"
        assert config["encryption"] == "AES256"
    
    @mock.patch.dict(os.environ, {
        "SERVICE_ENV": "production",
        "S3_ENDPOINT_URL": "https://custom-s3.example.com",
        "S3_REGION": "eu-west-1",
        "S3_ACCESS_KEY": "env-access-key",
        "S3_SECRET_KEY": "env-secret-key",
        "S3_USE_SSL": "true",
        "S3_VERIFY": "true",
        "S3_MAX_POOL_CONNECTIONS": "20",
        "S3_TIMEOUT": "120",
        "S3_RETRIES": "5",
        "S3_BUCKET": "custom-bucket",
        "S3_ENCRYPTION": "AES256"
    })
    def test_s3_config_from_env_production(self):
        """Test creating S3Config from environment variables in production environment."""
        config = get_s3_config_from_env()
        assert config["endpoint_url"] == "https://custom-s3.example.com"
        assert config["region_name"] == "eu-west-1"
        assert config["aws_access_key_id"] == "env-access-key"
        assert config["aws_secret_access_key"] == "env-secret-key"
        assert config["use_ssl"] is True
        assert config["verify"] is True
        assert config["max_pool_connections"] == 20
        assert config["timeout"] == 120
        assert config["retries"] == 5
        assert config["bucket_name"] == "custom-bucket"
        assert config["encryption"] == "AES256"
    
    @mock.patch.dict(os.environ, {
        "SERVICE_ENV": "staging",
        "S3_BUCKET": "mca-documents"
    })
    def test_s3_config_from_env_staging(self):
        """Test creating S3Config from environment variables in staging environment."""
        config = get_s3_config_from_env()
        assert config["bucket_name"] == "mca-documents"
    
    @mock.patch.dict(os.environ, {
        "SERVICE_ENV": "development",
        "S3_BUCKET": "mca-documents"
    })
    def test_s3_config_from_env_development(self):
        """Test creating S3Config from environment variables in development environment."""
        config = get_s3_config_from_env()
        assert config["bucket_name"] == "mca-documents"
    
    @mock.patch.dict(os.environ, {
        "S3_MAX_POOL_CONNECTIONS": "invalid"
    })
    def test_s3_config_from_env_invalid_max_pool_connections(self):
        """Test that invalid max_pool_connections in environment variables raises ValueError."""
        with pytest.raises(ValueError):
            get_s3_config_from_env()


class TestLogLevel:
    """Tests for the LogLevel enum.
    
    LogLevel is an enumeration of log levels (ERROR, WARN, INFO, DEBUG).
    These tests verify that LogLevel enum values can be correctly created and compared.
    """
    
    def test_log_level_values(self):
        """Test that LogLevel enum has the expected values."""
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.WARN.value == "WARN"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.DEBUG.value == "DEBUG"
    
    def test_log_level_comparison(self):
        """Test that LogLevel enum values can be compared."""
        assert LogLevel.ERROR != LogLevel.WARN
        assert LogLevel.WARN != LogLevel.INFO
        assert LogLevel.INFO != LogLevel.DEBUG


class TestLoggingConfig:
    """Tests for the LoggingConfig class.
    
    LoggingConfig represents configuration for structured logging.
    These tests verify that LoggingConfig instances can be correctly created and configured.
    """
    
    def test_logging_config_defaults(self):
        """Test that LoggingConfig has the expected default values."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert config.date_format == "%Y-%m-%d %H:%M:%S"
        assert config.file_path is None
        assert config.console_output is True
        assert config.json_format is True
        assert config.include_correlation_id is True
        assert config.include_document_id is True
    
    def test_logging_config_custom_values(self):
        """Test LoggingConfig with custom values."""
        config = LoggingConfig(
            level=LogLevel.DEBUG,
            format="%(levelname)s - %(message)s",
            date_format="%H:%M:%S",
            file_path="/var/log/document-service.log",
            console_output=False,
            json_format=False,
            include_correlation_id=False,
            include_document_id=False
        )
        assert config.level == LogLevel.DEBUG
        assert config.format == "%(levelname)s - %(message)s"
        assert config.date_format == "%H:%M:%S"
        assert config.file_path == "/var/log/document-service.log"
        assert config.console_output is False
        assert config.json_format is False
        assert config.include_correlation_id is False
        assert config.include_document_id is False
    
    @mock.patch.dict(os.environ, {
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "%(levelname)s - %(message)s",
        "LOG_DATE_FORMAT": "%H:%M:%S",
        "LOG_FILE_PATH": "/var/log/document-service.log",
        "LOG_CONSOLE": "false",
        "LOG_JSON": "false",
        "LOG_CORRELATION_ID": "false",
        "LOG_DOCUMENT_ID": "false"
    })
    def test_logging_config_from_env(self):
        """Test creating LoggingConfig from environment variables."""
        config = LoggingConfig.from_env()
        assert config.level == LogLevel.DEBUG
        assert config.format == "%(levelname)s - %(message)s"
        assert config.date_format == "%H:%M:%S"
        assert config.file_path == "/var/log/document-service.log"
        assert config.console_output is False
        assert config.json_format is False
        assert config.include_correlation_id is False
        assert config.include_document_id is False
    
    @mock.patch.dict(os.environ, {
        "LOG_LEVEL": "INVALID"
    })
    def test_logging_config_from_env_invalid_level(self):
        """Test that invalid log level in environment variables defaults to INFO."""
        config = LoggingConfig.from_env()
        assert config.level == LogLevel.INFO


class TestAppConfig:
    """Tests for the AppConfig class.
    
    AppConfig combines all configuration components into a single configuration object.
    These tests verify that AppConfig instances can be correctly created and validated.
    """
    
    def test_app_config_creation(self):
        """Test creating AppConfig with custom components."""
        service_config = ServiceConfig(
            name="test-service",
            version="1.0.0",
            port=8000,
            environment=Environment.DEVELOPMENT,
            debug=True
        )
        model_config = ModelConfig(
            model_type="random_forest",
            parameters={"n_estimators": 100},
            confidence_threshold=0.8,
            version="1.0.0",
            description="Test model"
        )
        rabbitmq_config = RabbitMQConfig(
            host="localhost",
            port=5672,
            username="guest",
            password="guest"
        )
        s3_config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-development",
            "encryption": "AES256"
        }
        logging_config = LoggingConfig(
            level=LogLevel.INFO,
            format="%(levelname)s - %(message)s",
            date_format="%H:%M:%S",
            file_path=None,
            console_output=True,
            json_format=True,
            include_correlation_id=True,
            include_document_id=True
        )
        
        app_config = AppConfig(
            service=service_config,
            model=model_config,
            rabbitmq=rabbitmq_config,
            s3=s3_config,
            logging=logging_config
        )
        
        assert app_config.service == service_config
        assert app_config.model == model_config
        assert app_config.rabbitmq == rabbitmq_config
        assert app_config.s3 == s3_config
        assert app_config.logging == logging_config
    
    @mock.patch.dict(os.environ, {
        "SERVICE_NAME": "env-service",
        "SERVICE_VERSION": "1.0.0",
        "SERVICE_PORT": "8000",
        "SERVICE_ENV": "development",
        "SERVICE_DEBUG": "true",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_USERNAME": "guest",
        "RABBITMQ_PASSWORD": "guest",
        "S3_ENDPOINT_URL": "https://s3.amazonaws.com",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "access-key",
        "S3_SECRET_KEY": "secret-key",
        "S3_BUCKET": "mca-documents-development",
        "LOG_LEVEL": "INFO"
    })
    def test_app_config_from_env(self):
        """Test creating AppConfig from environment variables."""
        app_config = AppConfig.from_env()
        
        assert app_config.service.name == "env-service"
        assert app_config.service.version == "1.0.0"
        assert app_config.service.port == 8000
        assert app_config.service.environment == Environment.DEVELOPMENT
        assert app_config.service.debug is True
        
        assert app_config.model.model_type == "random_forest"
        
        assert app_config.rabbitmq.host == "localhost"
        assert app_config.rabbitmq.port == 5672
        assert app_config.rabbitmq.username == "guest"
        assert app_config.rabbitmq.password == "guest"
        
        assert app_config.s3["endpoint_url"] == "https://s3.amazonaws.com"
        assert app_config.s3["region_name"] == "us-east-1"
        assert app_config.s3["aws_access_key_id"] == "access-key"
        assert app_config.s3["aws_secret_access_key"] == "secret-key"
        assert app_config.s3["bucket_name"] == "mca-documents-development"
        
        assert app_config.logging.level == LogLevel.INFO
    
    def test_app_config_validate_valid(self):
        """Test validating a valid AppConfig."""
        service_config = ServiceConfig(
            name="test-service",
            version="1.0.0"
        )
        model_config = ModelConfig()
        rabbitmq_config = RabbitMQConfig(
            host="localhost",
            username="guest",
            password="guest"
        )
        s3_config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-development",
            "encryption": "AES256"
        }
        logging_config = LoggingConfig()
        
        app_config = AppConfig(
            service=service_config,
            model=model_config,
            rabbitmq=rabbitmq_config,
            s3=s3_config,
            logging=logging_config
        )
        
        # Should not raise any exceptions
        app_config.validate()
    
    def test_app_config_validate_missing_s3_credentials(self):
        """Test validating AppConfig with missing S3 credentials."""
        service_config = ServiceConfig()
        model_config = ModelConfig()
        rabbitmq_config = RabbitMQConfig(
            host="localhost",
            username="guest",
            password="guest"
        )
        s3_config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "",  # Missing access key
            "aws_secret_access_key": "secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-development",
            "encryption": "AES256"
        }
        logging_config = LoggingConfig()
        
        app_config = AppConfig(
            service=service_config,
            model=model_config,
            rabbitmq=rabbitmq_config,
            s3=s3_config,
            logging=logging_config
        )
        
        with pytest.raises(ValueError, match="S3 credentials are required"):
            app_config.validate()
    
    def test_app_config_validate_missing_rabbitmq_credentials(self):
        """Test validating AppConfig with missing RabbitMQ credentials."""
        service_config = ServiceConfig()
        model_config = ModelConfig()
        rabbitmq_config = RabbitMQConfig(
            host="localhost",
            username="",  # Missing username
            password="guest"
        )
        s3_config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-development",
            "encryption": "AES256"
        }
        logging_config = LoggingConfig()
        
        app_config = AppConfig(
            service=service_config,
            model=model_config,
            rabbitmq=rabbitmq_config,
            s3=s3_config,
            logging=logging_config
        )
        
        with pytest.raises(ValueError, match="RabbitMQ connection parameters are required"):
            app_config.validate()
    
    def test_app_config_validate_missing_service_name(self):
        """Test validating AppConfig with missing service name."""
        service_config = ServiceConfig(
            name="",  # Missing name
            version="1.0.0"
        )
        model_config = ModelConfig()
        rabbitmq_config = RabbitMQConfig(
            host="localhost",
            username="guest",
            password="guest"
        )
        s3_config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "aws_access_key_id": "access-key",
            "aws_secret_access_key": "secret-key",
            "use_ssl": True,
            "verify": True,
            "max_pool_connections": 10,
            "timeout": 60,
            "retries": 3,
            "bucket_name": "mca-documents-development",
            "encryption": "AES256"
        }
        logging_config = LoggingConfig()
        
        app_config = AppConfig(
            service=service_config,
            model=model_config,
            rabbitmq=rabbitmq_config,
            s3=s3_config,
            logging=logging_config
        )
        
        with pytest.raises(ValueError, match="Service name and version are required"):
            app_config.validate()