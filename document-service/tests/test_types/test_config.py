#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for configuration type definitions in the Document Service.

This module validates that ConfigDict, ServiceConfig, ModelConfig, RabbitMQConfig,
S3Config, and LoggingConfig types correctly handle service configuration and settings.
These tests ensure type safety for configuration access throughout the service.
"""

import os
import pytest
from typing import Dict, Any, cast, Optional
from pathlib import Path

# Import the configuration types to test
from document_service.src.types.config import (
    ConfigDict,
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
    AppConfig,
    validate_config,
    EnvironmentType
)


class TestConfigDict:
    """Test cases for the ConfigDict type."""

    def test_config_dict_basic(self):
        """Test that ConfigDict can be used as a basic dictionary."""
        config: ConfigDict = {"key": "value"}
        assert config["key"] == "value"

    def test_config_dict_nested(self):
        """Test that ConfigDict can handle nested dictionaries."""
        config: ConfigDict = {
            "outer": {
                "inner": "value"
            }
        }
        assert config["outer"]["inner"] == "value"

    def test_config_dict_with_various_types(self):
        """Test that ConfigDict can handle various value types."""
        config: ConfigDict = {
            "string": "value",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "list": [1, 2, 3],
            "dict": {"key": "value"},
            "none": None
        }
        
        assert config["string"] == "value"
        assert config["integer"] == 42
        assert config["float"] == 3.14
        assert config["boolean"] is True
        assert config["list"] == [1, 2, 3]
        assert config["dict"]["key"] == "value"
        assert config["none"] is None

    def test_config_dict_type_annotation(self):
        """Test that ConfigDict works with type annotations."""
        def get_value(config: ConfigDict, key: str) -> Any:
            return config[key]
        
        config: ConfigDict = {"key": "value"}
        assert get_value(config, "key") == "value"


class TestServiceConfig:
    """Test cases for the ServiceConfig type."""

    def test_service_config_valid(self):
        """Test that ServiceConfig accepts valid configuration."""
        config: ServiceConfig = {
            "name": "document-service",
            "version": "1.0.0",
            "environment": "development",
            "host": "0.0.0.0",
            "port": 8000,
            "debug": True,
            "api_prefix": "/api/v1",
            "allowed_origins": ["http://localhost:3000"]
        }
        
        assert config["name"] == "document-service"
        assert config["version"] == "1.0.0"
        assert config["environment"] == "development"
        assert config["host"] == "0.0.0.0"
        assert config["port"] == 8000
        assert config["debug"] is True
        assert config["api_prefix"] == "/api/v1"
        assert config["allowed_origins"] == ["http://localhost:3000"]

    def test_service_config_environment_types(self):
        """Test that ServiceConfig accepts valid environment types."""
        # Test development environment
        config: ServiceConfig = {
            "name": "document-service",
            "version": "1.0.0",
            "environment": "development",
            "host": "0.0.0.0",
            "port": 8000,
            "debug": True,
            "api_prefix": "/api/v1",
            "allowed_origins": ["http://localhost:3000"]
        }
        assert config["environment"] == "development"
        
        # Test staging environment
        config["environment"] = "staging"
        assert config["environment"] == "staging"
        
        # Test production environment
        config["environment"] = "production"
        assert config["environment"] == "production"

    def test_service_config_with_empty_allowed_origins(self):
        """Test that ServiceConfig accepts empty allowed_origins list."""
        config: ServiceConfig = {
            "name": "document-service",
            "version": "1.0.0",
            "environment": "development",
            "host": "0.0.0.0",
            "port": 8000,
            "debug": True,
            "api_prefix": "/api/v1",
            "allowed_origins": []
        }
        assert config["allowed_origins"] == []


class TestModelConfig:
    """Test cases for the ModelConfig type."""

    def test_model_config_valid(self):
        """Test that ModelConfig accepts valid configuration."""
        config: ModelConfig = {
            "model_path": "/models/random_forest_classifier_1.0.0.pkl",
            "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
            "min_confidence_threshold": 0.75,
            "supported_document_types": ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
            "batch_size": 10,
            "max_document_size_mb": 10,
            "gpu_acceleration": False,
            "memory_limit_mb": 16384  # 16GB as per spec
        }
        
        assert config["model_path"] == "/models/random_forest_classifier_1.0.0.pkl"
        assert config["vectorizer_path"] == "/models/tfidf_vectorizer_1.0.0.pkl"
        assert config["min_confidence_threshold"] == 0.75
        assert "APPLICATION" in config["supported_document_types"]
        assert config["batch_size"] == 10
        assert config["max_document_size_mb"] == 10
        assert config["gpu_acceleration"] is False
        assert config["memory_limit_mb"] == 16384

    def test_model_config_confidence_threshold_range(self):
        """Test that ModelConfig accepts valid confidence threshold values."""
        config: ModelConfig = {
            "model_path": "/models/random_forest_classifier_1.0.0.pkl",
            "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
            "min_confidence_threshold": 0.0,  # Minimum value
            "supported_document_types": ["APPLICATION"],
            "batch_size": 10,
            "max_document_size_mb": 10,
            "gpu_acceleration": False,
            "memory_limit_mb": 16384
        }
        assert config["min_confidence_threshold"] == 0.0
        
        config["min_confidence_threshold"] = 1.0  # Maximum value
        assert config["min_confidence_threshold"] == 1.0
        
        config["min_confidence_threshold"] = 0.5  # Middle value
        assert config["min_confidence_threshold"] == 0.5

    def test_model_config_with_gpu_acceleration(self):
        """Test that ModelConfig accepts GPU acceleration setting."""
        config: ModelConfig = {
            "model_path": "/models/random_forest_classifier_1.0.0.pkl",
            "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
            "min_confidence_threshold": 0.75,
            "supported_document_types": ["APPLICATION"],
            "batch_size": 10,
            "max_document_size_mb": 10,
            "gpu_acceleration": True,  # Enable GPU acceleration
            "memory_limit_mb": 16384
        }
        assert config["gpu_acceleration"] is True


class TestRabbitMQConfig:
    """Test cases for the RabbitMQConfig type."""

    def test_rabbitmq_config_valid(self):
        """Test that RabbitMQConfig accepts valid configuration."""
        config: RabbitMQConfig = {
            "host": "localhost",
            "port": 5671,  # TLS port
            "username": "guest",
            "password": "guest",
            "vhost": "/",
            "exchange": "mca.documents",
            "queue_document_processing": "document-processing",
            "queue_data_extraction": "data-extraction",
            "routing_key": "document.new",
            "ssl": True,
            "ssl_cert_path": "/certs/client.crt",
            "ssl_key_path": "/certs/client.key",
            "ssl_ca_certs": "/certs/ca.crt",
            "heartbeat": 60,
            "connection_timeout": 30,
            "prefetch_count": 10
        }
        
        assert config["host"] == "localhost"
        assert config["port"] == 5671
        assert config["username"] == "guest"
        assert config["password"] == "guest"
        assert config["vhost"] == "/"
        assert config["exchange"] == "mca.documents"
        assert config["queue_document_processing"] == "document-processing"
        assert config["queue_data_extraction"] == "data-extraction"
        assert config["routing_key"] == "document.new"
        assert config["ssl"] is True
        assert config["ssl_cert_path"] == "/certs/client.crt"
        assert config["ssl_key_path"] == "/certs/client.key"
        assert config["ssl_ca_certs"] == "/certs/ca.crt"
        assert config["heartbeat"] == 60
        assert config["connection_timeout"] == 30
        assert config["prefetch_count"] == 10

    def test_rabbitmq_config_without_ssl(self):
        """Test that RabbitMQConfig accepts configuration without SSL."""
        config: RabbitMQConfig = {
            "host": "localhost",
            "port": 5672,  # Non-TLS port
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
            "prefetch_count": 10
        }
        
        assert config["ssl"] is False
        assert config["ssl_cert_path"] is None
        assert config["ssl_key_path"] is None
        assert config["ssl_ca_certs"] is None

    def test_rabbitmq_config_with_optional_ssl_paths(self):
        """Test that RabbitMQConfig accepts optional SSL paths."""
        # SSL enabled but with optional paths
        config: RabbitMQConfig = {
            "host": "localhost",
            "port": 5671,
            "username": "guest",
            "password": "guest",
            "vhost": "/",
            "exchange": "mca.documents",
            "queue_document_processing": "document-processing",
            "queue_data_extraction": "data-extraction",
            "routing_key": "document.new",
            "ssl": True,
            "ssl_cert_path": None,  # Optional when SSL is True
            "ssl_key_path": None,   # Optional when SSL is True
            "ssl_ca_certs": None,   # Optional when SSL is True
            "heartbeat": 60,
            "connection_timeout": 30,
            "prefetch_count": 10
        }
        
        assert config["ssl"] is True
        assert config["ssl_cert_path"] is None
        assert config["ssl_key_path"] is None
        assert config["ssl_ca_certs"] is None


class TestS3Config:
    """Test cases for the S3Config type."""

    def test_s3_config_valid(self):
        """Test that S3Config accepts valid configuration."""
        config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "bucket_name": "mca-documents-production",
            "use_ssl": True,
            "verify": True,
            "encryption": "AES256",
            "presigned_url_expiration": 3600,
            "max_pool_connections": 10
        }
        
        assert config["endpoint_url"] == "https://s3.amazonaws.com"
        assert config["region_name"] == "us-east-1"
        assert config["access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert config["secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert config["bucket_name"] == "mca-documents-production"
        assert config["use_ssl"] is True
        assert config["verify"] is True
        assert config["encryption"] == "AES256"
        assert config["presigned_url_expiration"] == 3600
        assert config["max_pool_connections"] == 10

    def test_s3_config_with_custom_endpoint(self):
        """Test that S3Config accepts custom S3-compatible endpoints."""
        config: S3Config = {
            "endpoint_url": "https://minio.example.com",  # Custom S3-compatible endpoint
            "region_name": "us-east-1",
            "access_key_id": "minioadmin",
            "secret_access_key": "minioadmin",
            "bucket_name": "mca-documents-development",
            "use_ssl": True,
            "verify": False,  # Skip SSL verification for self-signed certs
            "encryption": "AES256",
            "presigned_url_expiration": 3600,
            "max_pool_connections": 10
        }
        
        assert config["endpoint_url"] == "https://minio.example.com"
        assert config["verify"] is False

    def test_s3_config_encryption_type(self):
        """Test that S3Config accepts only AES256 encryption as per spec."""
        config: S3Config = {
            "endpoint_url": "https://s3.amazonaws.com",
            "region_name": "us-east-1",
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "bucket_name": "mca-documents-production",
            "use_ssl": True,
            "verify": True,
            "encryption": "AES256",  # Only AES256 is allowed as per spec
            "presigned_url_expiration": 3600,
            "max_pool_connections": 10
        }
        
        assert config["encryption"] == "AES256"


class TestLoggingConfig:
    """Test cases for the LoggingConfig type."""

    def test_logging_config_valid(self):
        """Test that LoggingConfig accepts valid configuration."""
        config: LoggingConfig = {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "file_path": "/var/log/document-service/app.log",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5,
            "json_format": True,
            "include_correlation_id": True
        }
        
        assert config["level"] == "INFO"
        assert config["format"] == "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        assert config["date_format"] == "%Y-%m-%d %H:%M:%S"
        assert config["file_path"] == "/var/log/document-service/app.log"
        assert config["max_bytes"] == 10485760
        assert config["backup_count"] == 5
        assert config["json_format"] is True
        assert config["include_correlation_id"] is True

    def test_logging_config_with_different_levels(self):
        """Test that LoggingConfig accepts different log levels."""
        config: LoggingConfig = {
            "level": "DEBUG",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "file_path": "/var/log/document-service/app.log",
            "max_bytes": 10485760,
            "backup_count": 5,
            "json_format": True,
            "include_correlation_id": True
        }
        assert config["level"] == "DEBUG"
        
        # Test other log levels
        config["level"] = "INFO"
        assert config["level"] == "INFO"
        
        config["level"] = "WARNING"
        assert config["level"] == "WARNING"
        
        config["level"] = "ERROR"
        assert config["level"] == "ERROR"
        
        config["level"] = "CRITICAL"
        assert config["level"] == "CRITICAL"

    def test_logging_config_without_file_path(self):
        """Test that LoggingConfig accepts None for file_path (console logging only)."""
        config: LoggingConfig = {
            "level": "INFO",
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "date_format": "%Y-%m-%d %H:%M:%S",
            "file_path": None,  # Console logging only
            "max_bytes": 10485760,
            "backup_count": 5,
            "json_format": False,
            "include_correlation_id": False
        }
        
        assert config["file_path"] is None
        assert config["json_format"] is False
        assert config["include_correlation_id"] is False


class TestAppConfig:
    """Test cases for the AppConfig type."""

    def test_app_config_valid(self):
        """Test that AppConfig accepts valid configuration with all required sections."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "development",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 0.75,
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 16384
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,
                "ssl_cert_path": "/certs/client.crt",
                "ssl_key_path": "/certs/client.key",
                "ssl_ca_certs": "/certs/ca.crt",
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "AES256",
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        # Test that all sections are present
        assert "service" in config
        assert "model" in config
        assert "rabbitmq" in config
        assert "s3" in config
        assert "logging" in config
        
        # Test that sections have correct types
        assert config["service"]["name"] == "document-service"
        assert config["model"]["min_confidence_threshold"] == 0.75
        assert config["rabbitmq"]["exchange"] == "mca.documents"
        assert config["s3"]["encryption"] == "AES256"
        assert config["logging"]["level"] == "INFO"


class TestValidateConfig:
    """Test cases for the validate_config function."""

    def test_validate_config_valid(self):
        """Test that validate_config accepts valid configuration."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "development",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 0.75,
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 16384  # 16GB as per spec
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,
                "ssl_cert_path": "/certs/client.crt",
                "ssl_key_path": "/certs/client.key",
                "ssl_ca_certs": "/certs/ca.crt",
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "AES256",
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        # Should not raise any exceptions
        validated_config = validate_config(config)
        assert validated_config == config

    def test_validate_config_invalid_environment(self):
        """Test that validate_config rejects invalid environment."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "invalid",  # Invalid environment
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 0.75,
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 16384
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,
                "ssl_cert_path": "/certs/client.crt",
                "ssl_key_path": "/certs/client.key",
                "ssl_ca_certs": "/certs/ca.crt",
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "AES256",
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        with pytest.raises(ValueError, match="Invalid environment"):
            validate_config(config)

    def test_validate_config_invalid_confidence_threshold(self):
        """Test that validate_config rejects invalid confidence threshold."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "development",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 1.5,  # Invalid: > 1.0
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 16384
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,
                "ssl_cert_path": "/certs/client.crt",
                "ssl_key_path": "/certs/client.key",
                "ssl_ca_certs": "/certs/ca.crt",
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "AES256",
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        with pytest.raises(ValueError, match="Invalid confidence threshold"):
            validate_config(config)

        # Test with negative value
        config["model"]["min_confidence_threshold"] = -0.1  # Invalid: < 0.0
        with pytest.raises(ValueError, match="Invalid confidence threshold"):
            validate_config(config)

    def test_validate_config_invalid_memory_limit(self):
        """Test that validate_config rejects memory limit below 16GB requirement."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "development",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 0.75,
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 8192  # Invalid: < 16GB (16384MB)
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,
                "ssl_cert_path": "/certs/client.crt",
                "ssl_key_path": "/certs/client.key",
                "ssl_ca_certs": "/certs/ca.crt",
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "AES256",
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        with pytest.raises(ValueError, match="Memory limit below required 16GB"):
            validate_config(config)

    def test_validate_config_invalid_encryption_type(self):
        """Test that validate_config rejects non-AES256 encryption types."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "development",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 0.75,
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 16384
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,
                "ssl_cert_path": "/certs/client.crt",
                "ssl_key_path": "/certs/client.key",
                "ssl_ca_certs": "/certs/ca.crt",
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "KMS",  # Invalid: not AES256
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        with pytest.raises(ValueError, match="Invalid encryption type"):
            validate_config(config)

    def test_validate_config_ssl_without_certs(self):
        """Test that validate_config rejects SSL without certificate paths."""
        config: AppConfig = {
            "service": {
                "name": "document-service",
                "version": "1.0.0",
                "environment": "development",
                "host": "0.0.0.0",
                "port": 8000,
                "debug": True,
                "api_prefix": "/api/v1",
                "allowed_origins": ["http://localhost:3000"]
            },
            "model": {
                "model_path": "/models/random_forest_classifier_1.0.0.pkl",
                "vectorizer_path": "/models/tfidf_vectorizer_1.0.0.pkl",
                "min_confidence_threshold": 0.75,
                "supported_document_types": ["APPLICATION", "TAX_RETURN"],
                "batch_size": 10,
                "max_document_size_mb": 10,
                "gpu_acceleration": False,
                "memory_limit_mb": 16384
            },
            "rabbitmq": {
                "host": "localhost",
                "port": 5671,
                "username": "guest",
                "password": "guest",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue_document_processing": "document-processing",
                "queue_data_extraction": "data-extraction",
                "routing_key": "document.new",
                "ssl": True,  # SSL enabled
                "ssl_cert_path": None,  # But no cert path
                "ssl_key_path": None,   # But no key path
                "ssl_ca_certs": None,   # But no CA certs
                "heartbeat": 60,
                "connection_timeout": 30,
                "prefetch_count": 10
            },
            "s3": {
                "endpoint_url": "https://s3.amazonaws.com",
                "region_name": "us-east-1",
                "access_key_id": "AKIAIOSFODNN7EXAMPLE",
                "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                "bucket_name": "mca-documents-production",
                "use_ssl": True,
                "verify": True,
                "encryption": "AES256",
                "presigned_url_expiration": 3600,
                "max_pool_connections": 10
            },
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "date_format": "%Y-%m-%d %H:%M:%S",
                "file_path": "/var/log/document-service/app.log",
                "max_bytes": 10485760,
                "backup_count": 5,
                "json_format": True,
                "include_correlation_id": True
            }
        }
        
        with pytest.raises(ValueError, match="SSL is enabled but certificate paths are not properly configured"):
            validate_config(config)


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])