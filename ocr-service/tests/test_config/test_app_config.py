#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service app_config module.

These tests verify that the application configuration correctly loads from environment
variables, validates required settings, and provides appropriate defaults for development,
staging, and production environments.
"""

import os
import unittest
from unittest import mock
import pytest

# Import the module to test
from config.app_config import (
    AppConfig,
    Environment,
    get_env_var,
    get_current_environment,
    load_service_config,
    load_tensorflow_config,
    load_rabbitmq_config,
    load_s3_config,
    load_logging_config
)


class TestGetEnvVar(unittest.TestCase):
    """Tests for the get_env_var function."""

    def test_get_existing_env_var(self):
        """Test retrieving an existing environment variable."""
        with mock.patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            value = get_env_var("TEST_VAR")
            self.assertEqual(value, "test_value")

    def test_get_nonexistent_env_var_with_default(self):
        """Test retrieving a non-existent environment variable with a default value."""
        with mock.patch.dict(os.environ, {}, clear=True):
            value = get_env_var("NONEXISTENT_VAR", default="default_value")
            self.assertEqual(value, "default_value")

    def test_get_nonexistent_env_var_without_default(self):
        """Test retrieving a non-existent environment variable without a default value."""
        with mock.patch.dict(os.environ, {}, clear=True):
            value = get_env_var("NONEXISTENT_VAR")
            self.assertEqual(value, "")

    def test_get_required_env_var_that_exists(self):
        """Test retrieving a required environment variable that exists."""
        with mock.patch.dict(os.environ, {"REQUIRED_VAR": "required_value"}):
            value = get_env_var("REQUIRED_VAR", required=True)
            self.assertEqual(value, "required_value")

    def test_get_required_env_var_that_does_not_exist(self):
        """Test retrieving a required environment variable that does not exist."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                get_env_var("REQUIRED_VAR", required=True)


class TestGetCurrentEnvironment(unittest.TestCase):
    """Tests for the get_current_environment function."""

    def test_get_development_environment(self):
        """Test retrieving development environment."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "development"}):
            env = get_current_environment()
            self.assertEqual(env, Environment.DEVELOPMENT)

    def test_get_staging_environment(self):
        """Test retrieving staging environment."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "staging"}):
            env = get_current_environment()
            self.assertEqual(env, Environment.STAGING)

    def test_get_production_environment(self):
        """Test retrieving production environment."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "production"}):
            env = get_current_environment()
            self.assertEqual(env, Environment.PRODUCTION)

    def test_get_default_environment(self):
        """Test retrieving default environment when not specified."""
        with mock.patch.dict(os.environ, {}, clear=True):
            env = get_current_environment()
            self.assertEqual(env, Environment.DEVELOPMENT)

    def test_get_invalid_environment(self):
        """Test retrieving default environment when an invalid environment is specified."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "invalid"}):
            env = get_current_environment()
            self.assertEqual(env, Environment.DEVELOPMENT)


class TestLoadServiceConfig(unittest.TestCase):
    """Tests for the load_service_config function."""

    def test_load_service_config_with_defaults(self):
        """Test loading service configuration with default values."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = load_service_config()
            self.assertEqual(config["name"], "ocr-service")
            self.assertEqual(config["version"], "1.0.0")
            self.assertEqual(config["port"], 8080)
            self.assertEqual(config["environment"], Environment.DEVELOPMENT)
            self.assertEqual(config["debug"], False)
            self.assertEqual(config["correlation_id_header"], "X-Correlation-ID")
            self.assertEqual(config["max_workers"], 4)
            self.assertEqual(config["shutdown_timeout"], 30)

    def test_load_service_config_with_custom_values(self):
        """Test loading service configuration with custom environment variables."""
        env_vars = {
            "OCR_SERVICE_NAME": "custom-ocr-service",
            "OCR_SERVICE_VERSION": "2.0.0",
            "OCR_SERVICE_PORT": "9090",
            "OCR_SERVICE_ENV": "production",
            "OCR_SERVICE_DEBUG": "true",
            "OCR_CORRELATION_ID_HEADER": "X-Custom-Correlation-ID",
            "OCR_SERVICE_MAX_WORKERS": "8",
            "OCR_SERVICE_SHUTDOWN_TIMEOUT": "60"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_service_config()
            self.assertEqual(config["name"], "custom-ocr-service")
            self.assertEqual(config["version"], "2.0.0")
            self.assertEqual(config["port"], 9090)
            self.assertEqual(config["environment"], Environment.PRODUCTION)
            self.assertEqual(config["debug"], True)
            self.assertEqual(config["correlation_id_header"], "X-Custom-Correlation-ID")
            self.assertEqual(config["max_workers"], 8)
            self.assertEqual(config["shutdown_timeout"], 60)


class TestLoadTensorFlowConfig(unittest.TestCase):
    """Tests for the load_tensorflow_config function."""

    def test_load_tensorflow_config_with_defaults(self):
        """Test loading TensorFlow configuration with default values."""
        with mock.patch.dict(os.environ, {}, clear=True):
            config = load_tensorflow_config()
            self.assertEqual(config["models_path"], "/app/models")
            self.assertEqual(config["typed_model_name"], "typed_text_model")
            self.assertEqual(config["handwritten_model_name"], "handwritten_text_model")
            self.assertEqual(config["hybrid_model_name"], "hybrid_text_model")
            self.assertEqual(config["confidence_threshold"], 0.85)
            self.assertEqual(config["low_confidence_threshold"], 0.60)
            self.assertEqual(config["gpu_memory_limit"], 0)
            self.assertEqual(config["use_gpu"], True)
            self.assertEqual(config["batch_size"], 4)
            self.assertEqual(config["model_version"], "1.0.0")
            self.assertEqual(config["enable_optimization"], True)

    def test_load_tensorflow_config_with_custom_values(self):
        """Test loading TensorFlow configuration with custom environment variables."""
        env_vars = {
            "OCR_MODELS_PATH": "/custom/models",
            "OCR_TYPED_MODEL_NAME": "custom_typed_model",
            "OCR_HANDWRITTEN_MODEL_NAME": "custom_handwritten_model",
            "OCR_HYBRID_MODEL_NAME": "custom_hybrid_model",
            "OCR_CONFIDENCE_THRESHOLD": "0.95",
            "OCR_LOW_CONFIDENCE_THRESHOLD": "0.70",
            "OCR_GPU_MEMORY_LIMIT": "4096",
            "OCR_USE_GPU": "false",
            "OCR_BATCH_SIZE": "8",
            "OCR_MODEL_VERSION": "2.0.0",
            "OCR_ENABLE_OPTIMIZATION": "false"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_tensorflow_config()
            self.assertEqual(config["models_path"], "/custom/models")
            self.assertEqual(config["typed_model_name"], "custom_typed_model")
            self.assertEqual(config["handwritten_model_name"], "custom_handwritten_model")
            self.assertEqual(config["hybrid_model_name"], "custom_hybrid_model")
            self.assertEqual(config["confidence_threshold"], 0.95)
            self.assertEqual(config["low_confidence_threshold"], 0.70)
            self.assertEqual(config["gpu_memory_limit"], 4096)
            self.assertEqual(config["use_gpu"], False)
            self.assertEqual(config["batch_size"], 8)
            self.assertEqual(config["model_version"], "2.0.0")
            self.assertEqual(config["enable_optimization"], False)


class TestLoadRabbitMQConfig(unittest.TestCase):
    """Tests for the load_rabbitmq_config function."""

    def test_load_rabbitmq_config_with_defaults(self):
        """Test loading RabbitMQ configuration with default values."""
        # We need to set required values even for the "default" test
        env_vars = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_rabbitmq_config()
            self.assertEqual(config["host"], "localhost")
            self.assertEqual(config["port"], 5672)
            self.assertEqual(config["username"], "guest")
            self.assertEqual(config["password"], "guest")
            self.assertEqual(config["vhost"], "/")
            self.assertEqual(config["exchange"], "mca.documents")
            self.assertEqual(config["queue"], "data-extraction")
            self.assertEqual(config["routing_key"], "")
            self.assertEqual(config["use_tls"], True)
            self.assertEqual(config["cert_path"], "/app/certs/client.pem")
            self.assertEqual(config["key_path"], "/app/certs/client.key")
            self.assertEqual(config["ca_path"], "/app/certs/ca.pem")
            self.assertEqual(config["prefetch_count"], 10)
            self.assertEqual(config["connection_attempts"], 3)
            self.assertEqual(config["retry_delay"], 5)
            self.assertEqual(config["heartbeat"], 60)

    def test_load_rabbitmq_config_with_custom_values(self):
        """Test loading RabbitMQ configuration with custom environment variables."""
        env_vars = {
            "RABBITMQ_HOST": "rabbitmq.example.com",
            "RABBITMQ_PORT": "5673",
            "RABBITMQ_USERNAME": "custom_user",
            "RABBITMQ_PASSWORD": "custom_password",
            "RABBITMQ_VHOST": "/custom",
            "RABBITMQ_EXCHANGE": "custom.exchange",
            "RABBITMQ_QUEUE": "custom-queue",
            "RABBITMQ_ROUTING_KEY": "custom.routing.key",
            "RABBITMQ_USE_TLS": "false",
            "RABBITMQ_CERT_PATH": "/custom/certs/client.pem",
            "RABBITMQ_KEY_PATH": "/custom/certs/client.key",
            "RABBITMQ_CA_PATH": "/custom/certs/ca.pem",
            "RABBITMQ_PREFETCH_COUNT": "20",
            "RABBITMQ_CONNECTION_ATTEMPTS": "5",
            "RABBITMQ_RETRY_DELAY": "10",
            "RABBITMQ_HEARTBEAT": "30"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_rabbitmq_config()
            self.assertEqual(config["host"], "rabbitmq.example.com")
            self.assertEqual(config["port"], 5673)
            self.assertEqual(config["username"], "custom_user")
            self.assertEqual(config["password"], "custom_password")
            self.assertEqual(config["vhost"], "/custom")
            self.assertEqual(config["exchange"], "custom.exchange")
            self.assertEqual(config["queue"], "custom-queue")
            self.assertEqual(config["routing_key"], "custom.routing.key")
            self.assertEqual(config["use_tls"], False)
            self.assertEqual(config["cert_path"], "/custom/certs/client.pem")
            self.assertEqual(config["key_path"], "/custom/certs/client.key")
            self.assertEqual(config["ca_path"], "/custom/certs/ca.pem")
            self.assertEqual(config["prefetch_count"], 20)
            self.assertEqual(config["connection_attempts"], 5)
            self.assertEqual(config["retry_delay"], 10)
            self.assertEqual(config["heartbeat"], 30)

    def test_load_rabbitmq_config_missing_required_values(self):
        """Test loading RabbitMQ configuration with missing required values."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                load_rabbitmq_config()


class TestLoadS3Config(unittest.TestCase):
    """Tests for the load_s3_config function."""

    def test_load_s3_config_with_defaults_development(self):
        """Test loading S3 configuration with default values in development environment."""
        # We need to set required values even for the "default" test
        env_vars = {
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "OCR_SERVICE_ENV": "development"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_s3_config()
            self.assertEqual(config["endpoint"], "http://localhost:9000")
            self.assertEqual(config["region"], "us-east-1")
            self.assertEqual(config["bucket"], "mca-documents-staging")
            self.assertEqual(config["access_key"], "test_access_key")
            self.assertEqual(config["secret_key"], "test_secret_key")
            self.assertEqual(config["use_ssl"], True)
            self.assertEqual(config["verify_ssl"], True)
            self.assertEqual(config["encryption"], "AES256")
            self.assertEqual(config["presigned_url_expiry"], 3600)
            self.assertEqual(config["max_pool_connections"], 10)
            self.assertEqual(config["connect_timeout"], 5)
            self.assertEqual(config["read_timeout"], 60)

    def test_load_s3_config_with_defaults_production(self):
        """Test loading S3 configuration with default values in production environment."""
        # We need to set required values even for the "default" test
        env_vars = {
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "OCR_SERVICE_ENV": "production"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_s3_config()
            self.assertEqual(config["bucket"], "mca-documents-production")

    def test_load_s3_config_with_custom_values(self):
        """Test loading S3 configuration with custom environment variables."""
        env_vars = {
            "S3_ENDPOINT": "https://s3.example.com",
            "S3_REGION": "us-west-2",
            "S3_BUCKET": "custom-bucket",
            "S3_ACCESS_KEY": "custom_access_key",
            "S3_SECRET_KEY": "custom_secret_key",
            "S3_USE_SSL": "false",
            "S3_VERIFY_SSL": "false",
            "S3_ENCRYPTION": "custom-encryption",
            "S3_PRESIGNED_URL_EXPIRY": "7200",
            "S3_MAX_POOL_CONNECTIONS": "20",
            "S3_CONNECT_TIMEOUT": "10",
            "S3_READ_TIMEOUT": "120"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_s3_config()
            self.assertEqual(config["endpoint"], "https://s3.example.com")
            self.assertEqual(config["region"], "us-west-2")
            self.assertEqual(config["bucket"], "custom-bucket")
            self.assertEqual(config["access_key"], "custom_access_key")
            self.assertEqual(config["secret_key"], "custom_secret_key")
            self.assertEqual(config["use_ssl"], False)
            self.assertEqual(config["verify_ssl"], False)
            self.assertEqual(config["encryption"], "custom-encryption")
            self.assertEqual(config["presigned_url_expiry"], 7200)
            self.assertEqual(config["max_pool_connections"], 20)
            self.assertEqual(config["connect_timeout"], 10)
            self.assertEqual(config["read_timeout"], 120)

    def test_load_s3_config_missing_required_values(self):
        """Test loading S3 configuration with missing required values."""
        with mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                load_s3_config()


class TestLoadLoggingConfig(unittest.TestCase):
    """Tests for the load_logging_config function."""

    def test_load_logging_config_with_defaults_development(self):
        """Test loading logging configuration with default values in development environment."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "development"}):
            config = load_logging_config()
            self.assertEqual(config["level"], "DEBUG")
            self.assertEqual(config["format"], "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            self.assertEqual(config["file_path"], "")
            self.assertEqual(config["max_bytes"], 10485760)
            self.assertEqual(config["backup_count"], 5)
            self.assertEqual(config["json_format"], False)
            self.assertEqual(config["include_correlation_id"], True)

    def test_load_logging_config_with_defaults_staging(self):
        """Test loading logging configuration with default values in staging environment."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "staging"}):
            config = load_logging_config()
            self.assertEqual(config["level"], "INFO")

    def test_load_logging_config_with_defaults_production(self):
        """Test loading logging configuration with default values in production environment."""
        with mock.patch.dict(os.environ, {"OCR_SERVICE_ENV": "production"}):
            config = load_logging_config()
            self.assertEqual(config["level"], "WARNING")

    def test_load_logging_config_with_custom_values(self):
        """Test loading logging configuration with custom environment variables."""
        env_vars = {
            "OCR_LOG_LEVEL": "ERROR",
            "OCR_LOG_FORMAT": "custom-format",
            "OCR_LOG_FILE": "/var/log/ocr-service.log",
            "OCR_LOG_MAX_BYTES": "20971520",
            "OCR_LOG_BACKUP_COUNT": "10",
            "OCR_LOG_JSON": "true",
            "OCR_LOG_INCLUDE_CORRELATION_ID": "false"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = load_logging_config()
            self.assertEqual(config["level"], "ERROR")
            self.assertEqual(config["format"], "custom-format")
            self.assertEqual(config["file_path"], "/var/log/ocr-service.log")
            self.assertEqual(config["max_bytes"], 20971520)
            self.assertEqual(config["backup_count"], 10)
            self.assertEqual(config["json_format"], True)
            self.assertEqual(config["include_correlation_id"], False)


class TestAppConfig(unittest.TestCase):
    """Tests for the AppConfig class."""

    def test_app_config_initialization(self):
        """Test initialization of AppConfig with default values."""
        # We need to set required values for initialization
        env_vars = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = AppConfig()
            # Verify that all configuration components are initialized
            self.assertIsNotNone(config.SERVICE)
            self.assertIsNotNone(config.TENSORFLOW)
            self.assertIsNotNone(config.RABBITMQ)
            self.assertIsNotNone(config.S3)
            self.assertIsNotNone(config.LOGGING)

    def test_app_config_environment_overrides_development(self):
        """Test environment-specific overrides for development environment."""
        env_vars = {
            "OCR_SERVICE_ENV": "development",
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = AppConfig()
            # Verify development-specific overrides
            self.assertEqual(config.SERVICE.environment, Environment.DEVELOPMENT)
            self.assertEqual(config.TENSORFLOW.use_gpu, False)  # Disabled in development
            self.assertEqual(config.TENSORFLOW.enable_optimization, False)  # Disabled in development

    def test_app_config_environment_overrides_staging(self):
        """Test environment-specific overrides for staging environment."""
        env_vars = {
            "OCR_SERVICE_ENV": "staging",
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = AppConfig()
            # Verify staging-specific overrides
            self.assertEqual(config.SERVICE.environment, Environment.STAGING)
            self.assertEqual(config.TENSORFLOW.confidence_threshold, 0.80)  # Lower threshold for testing

    def test_app_config_environment_overrides_production(self):
        """Test environment-specific overrides for production environment."""
        env_vars = {
            "OCR_SERVICE_ENV": "production",
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key"
        }
        with mock.patch.dict(os.environ, env_vars):
            config = AppConfig()
            # Verify production-specific overrides
            self.assertEqual(config.SERVICE.environment, Environment.PRODUCTION)
            self.assertEqual(config.TENSORFLOW.confidence_threshold, 0.90)  # Higher threshold for production
            self.assertEqual(config.RABBITMQ.prefetch_count, 20)  # Higher prefetch for production throughput

    @mock.patch('os.path.exists')
    def test_app_config_validation_success(self, mock_exists):
        """Test successful validation of configuration."""
        # Mock os.path.exists to return True for certificate paths
        mock_exists.return_value = True
        
        env_vars = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "OCR_USE_GPU": "true",
            "OCR_GPU_MEMORY_LIMIT": "1024"
        }
        with mock.patch.dict(os.environ, env_vars):
            # This should not raise any exceptions
            config = AppConfig()
            self.assertIsNotNone(config)

    def test_app_config_validation_failure_gpu_memory_limit(self):
        """Test validation failure for invalid GPU memory limit."""
        env_vars = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "OCR_USE_GPU": "true",
            "OCR_GPU_MEMORY_LIMIT": "-1"  # Invalid value
        }
        with mock.patch.dict(os.environ, env_vars):
            with self.assertRaises(ValueError):
                AppConfig()

    def test_app_config_validation_failure_missing_s3_bucket(self):
        """Test validation failure for missing S3 bucket."""
        env_vars = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "S3_BUCKET": ""  # Empty bucket name
        }
        with mock.patch.dict(os.environ, env_vars):
            with self.assertRaises(ValueError):
                AppConfig()

    @mock.patch('logging.Logger.info')
    @mock.patch('logging.Logger.warning')
    def test_app_config_logging(self, mock_warning, mock_info):
        """Test that configuration logging works correctly."""
        env_vars = {
            "RABBITMQ_HOST": "localhost",
            "RABBITMQ_USERNAME": "guest",
            "RABBITMQ_PASSWORD": "guest",
            "S3_ENDPOINT": "http://localhost:9000",
            "S3_ACCESS_KEY": "test_access_key",
            "S3_SECRET_KEY": "test_secret_key",
            "OCR_SERVICE_DEBUG": "true",  # Enable debug mode to trigger logging
            "RABBITMQ_USE_TLS": "true"  # Enable TLS to test certificate path warnings
        }
        
        # Mock certificate paths to not exist
        with mock.patch('os.path.exists', return_value=False):
            with mock.patch.dict(os.environ, env_vars):
                AppConfig()
                # Verify that warning logs were called for missing certificate files
                self.assertTrue(mock_warning.called)
                # Verify that info logs were called for configuration summary
                self.assertTrue(mock_info.called)


if __name__ == "__main__":
    unittest.main()