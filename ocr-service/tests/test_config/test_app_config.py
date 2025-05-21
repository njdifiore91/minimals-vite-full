#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's app_config.py module.

These tests verify that application configuration correctly loads from environment variables,
validates required settings, and provides appropriate defaults for development, staging, and
production environments. The tests ensure that the service can be properly configured for
different deployment scenarios.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the module under test
from src.config.app_config import AppConfig, Environment, LogLevel, get_config


class TestAppConfig:
    """Test suite for the AppConfig class."""

    def test_default_config_values(self):
        """Test that default configuration values are set correctly when no environment variables are provided."""
        # Clear all relevant environment variables
        with patch.dict(os.environ, {}, clear=True):
            # Set only the required environment variables to avoid validation errors
            os.environ['ENVIRONMENT'] = 'development'
            
            # Create a new config instance
            config = AppConfig()
            
            # Check default values
            assert config.SERVICE_NAME == 'ocr-service'
            assert config.SERVICE_VERSION == '1.0.0'
            assert config.ENVIRONMENT == Environment.DEVELOPMENT
            assert config.HOST == '0.0.0.0'
            assert config.PORT == 8080
            assert config.RABBITMQ_HOST == 'localhost'
            assert config.RABBITMQ_PORT == 5672
            assert config.RABBITMQ_USERNAME == 'guest'
            assert config.RABBITMQ_PASSWORD == 'guest'
            assert config.RABBITMQ_VHOST == '/'
            assert config.RABBITMQ_EXCHANGE == 'mca.documents'
            assert config.RABBITMQ_QUEUE == 'data-extraction'
            assert config.S3_ENDPOINT == 's3.amazonaws.com'
            assert config.S3_REGION == 'us-east-1'
            assert config.S3_BUCKET == 'mca-documents-development'
            assert config.TF_MODEL_PATH == './models'
            assert config.TF_CONFIDENCE_THRESHOLD == 0.85
            assert config.LOG_LEVEL == LogLevel.DEBUG
            assert config.BATCH_SIZE == 10
            assert config.MAX_WORKERS == 4
            assert config.PROCESSING_TIMEOUT == 300

    def test_environment_from_string(self):
        """Test that Environment.from_string correctly converts string values to Environment enum."""
        assert Environment.from_string('development') == Environment.DEVELOPMENT
        assert Environment.from_string('DEVELOPMENT') == Environment.DEVELOPMENT
        assert Environment.from_string('staging') == Environment.STAGING
        assert Environment.from_string('STAGING') == Environment.STAGING
        assert Environment.from_string('production') == Environment.PRODUCTION
        assert Environment.from_string('PRODUCTION') == Environment.PRODUCTION
        
        # Test fallback to default for invalid values
        assert Environment.from_string('invalid') == Environment.DEVELOPMENT
        assert Environment.from_string('') == Environment.DEVELOPMENT

    def test_get_env_with_default(self):
        """Test that _get_env correctly returns default values when environment variables are not set."""
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            
            # Test with a non-None default
            value = config._get_env('TEST_VAR', 'default_value')
            assert value == 'default_value'
            
            # Test with a None default (should raise ValueError)
            with pytest.raises(ValueError, match="Required environment variable 'REQUIRED_VAR' is not set"):
                config._get_env('REQUIRED_VAR', None)

    def test_get_env_bool(self):
        """Test that _get_env_bool correctly converts string values to boolean."""
        with patch.dict(os.environ, {}, clear=True):
            config = AppConfig()
            
            # Test true values
            os.environ['BOOL_TRUE_1'] = 'true'
            os.environ['BOOL_TRUE_2'] = 'True'
            os.environ['BOOL_TRUE_3'] = '1'
            os.environ['BOOL_TRUE_4'] = 'yes'
            os.environ['BOOL_TRUE_5'] = 'y'
            
            assert config._get_env_bool('BOOL_TRUE_1') is True
            assert config._get_env_bool('BOOL_TRUE_2') is True
            assert config._get_env_bool('BOOL_TRUE_3') is True
            assert config._get_env_bool('BOOL_TRUE_4') is True
            assert config._get_env_bool('BOOL_TRUE_5') is True
            
            # Test false values
            os.environ['BOOL_FALSE_1'] = 'false'
            os.environ['BOOL_FALSE_2'] = 'False'
            os.environ['BOOL_FALSE_3'] = '0'
            os.environ['BOOL_FALSE_4'] = 'no'
            os.environ['BOOL_FALSE_5'] = 'n'
            os.environ['BOOL_FALSE_6'] = 'anything else'
            
            assert config._get_env_bool('BOOL_FALSE_1') is False
            assert config._get_env_bool('BOOL_FALSE_2') is False
            assert config._get_env_bool('BOOL_FALSE_3') is False
            assert config._get_env_bool('BOOL_FALSE_4') is False
            assert config._get_env_bool('BOOL_FALSE_5') is False
            assert config._get_env_bool('BOOL_FALSE_6') is False
            
            # Test default values
            assert config._get_env_bool('NOT_SET', True) is True
            assert config._get_env_bool('NOT_SET', False) is False

    def test_get_default_bucket(self):
        """Test that _get_default_bucket returns the correct bucket name based on the environment."""
        with patch.dict(os.environ, {}, clear=True):
            # Test development environment
            os.environ['ENVIRONMENT'] = 'development'
            config = AppConfig()
            assert config._get_default_bucket() == 'mca-documents-development'
            
            # Test staging environment
            os.environ['ENVIRONMENT'] = 'staging'
            config = AppConfig()
            assert config._get_default_bucket() == 'mca-documents-staging'
            
            # Test production environment
            os.environ['ENVIRONMENT'] = 'production'
            config = AppConfig()
            assert config._get_default_bucket() == 'mca-documents-production'

    def test_get_default_log_level(self):
        """Test that _get_default_log_level returns the correct log level based on the environment."""
        with patch.dict(os.environ, {}, clear=True):
            # Test development environment
            os.environ['ENVIRONMENT'] = 'development'
            config = AppConfig()
            assert config._get_default_log_level() == LogLevel.DEBUG.value
            
            # Test staging environment
            os.environ['ENVIRONMENT'] = 'staging'
            config = AppConfig()
            assert config._get_default_log_level() == LogLevel.INFO.value
            
            # Test production environment
            os.environ['ENVIRONMENT'] = 'production'
            config = AppConfig()
            assert config._get_default_log_level() == LogLevel.INFO.value

    def test_validate_configuration_development(self):
        """Test that configuration validation passes for development environment with minimal settings."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'development'
            
            # Create config and validate (should not raise exceptions)
            config = AppConfig()
            config._validate_configuration()

    def test_validate_configuration_staging_missing_certs(self):
        """Test that configuration validation fails for staging environment with missing TLS certificates."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'staging'
            os.environ['RABBITMQ_USE_TLS'] = 'true'
            os.environ['S3_ACCESS_KEY'] = 'test-key'
            os.environ['S3_SECRET_KEY'] = 'test-secret'
            
            # Create config
            config = AppConfig()
            
            # Validation should fail due to missing client cert
            with pytest.raises(ValueError, match="RABBITMQ_CLIENT_CERT is required when TLS is enabled in staging/production"):
                config._validate_configuration()
            
            # Add client cert but not client key
            os.environ['RABBITMQ_CLIENT_CERT'] = '/path/to/cert'
            config = AppConfig()
            with pytest.raises(ValueError, match="RABBITMQ_CLIENT_KEY is required when TLS is enabled in staging/production"):
                config._validate_configuration()
            
            # Add client key but not CA cert
            os.environ['RABBITMQ_CLIENT_KEY'] = '/path/to/key'
            config = AppConfig()
            with pytest.raises(ValueError, match="RABBITMQ_CA_CERT is required when TLS is enabled in staging/production"):
                config._validate_configuration()

    def test_validate_configuration_staging_missing_s3_credentials(self):
        """Test that configuration validation fails for staging environment with missing S3 credentials."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'staging'
            os.environ['RABBITMQ_USE_TLS'] = 'false'  # Disable TLS to focus on S3 validation
            
            # Create config
            config = AppConfig()
            
            # Validation should fail due to missing S3 access key
            with pytest.raises(ValueError, match="S3_ACCESS_KEY is required in staging/production"):
                config._validate_configuration()
            
            # Add access key but not secret key
            os.environ['S3_ACCESS_KEY'] = 'test-key'
            config = AppConfig()
            with pytest.raises(ValueError, match="S3_SECRET_KEY is required in staging/production"):
                config._validate_configuration()

    def test_validate_configuration_production_gpu_memory(self):
        """Test that configuration validation fails for production environment with insufficient GPU memory."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'production'
            os.environ['RABBITMQ_USE_TLS'] = 'true'
            os.environ['RABBITMQ_CLIENT_CERT'] = '/path/to/cert'
            os.environ['RABBITMQ_CLIENT_KEY'] = '/path/to/key'
            os.environ['RABBITMQ_CA_CERT'] = '/path/to/ca'
            os.environ['S3_ACCESS_KEY'] = 'test-key'
            os.environ['S3_SECRET_KEY'] = 'test-secret'
            os.environ['TF_USE_GPU'] = 'true'
            
            # Create config
            config = AppConfig()
            
            # Validation should fail due to missing GPU memory limit
            with pytest.raises(ValueError, match="TF_GPU_MEMORY_LIMIT must be at least 8GB \(8192MB\) for production use"):
                config._validate_configuration()
            
            # Set insufficient GPU memory
            os.environ['TF_GPU_MEMORY_LIMIT'] = '4096'
            config = AppConfig()
            with pytest.raises(ValueError, match="TF_GPU_MEMORY_LIMIT must be at least 8GB \(8192MB\) for production use"):
                config._validate_configuration()
            
            # Set sufficient GPU memory
            os.environ['TF_GPU_MEMORY_LIMIT'] = '8192'
            config = AppConfig()
            # Should not raise an exception
            config._validate_configuration()

    def test_as_dict(self):
        """Test that as_dict returns a dictionary with all configuration values."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'development'
            
            config = AppConfig()
            config_dict = config.as_dict()
            
            # Check that the dictionary contains all expected keys
            expected_keys = [
                'SERVICE_NAME', 'SERVICE_VERSION', 'ENVIRONMENT', 'HOST', 'PORT',
                'RABBITMQ_HOST', 'RABBITMQ_PORT', 'RABBITMQ_USERNAME', 'RABBITMQ_PASSWORD',
                'RABBITMQ_VHOST', 'RABBITMQ_EXCHANGE', 'RABBITMQ_QUEUE', 'RABBITMQ_USE_TLS',
                'RABBITMQ_CLIENT_CERT', 'RABBITMQ_CLIENT_KEY', 'RABBITMQ_CA_CERT',
                'S3_ENDPOINT', 'S3_REGION', 'S3_ACCESS_KEY', 'S3_SECRET_KEY',
                'S3_BUCKET', 'S3_USE_SSL', 'S3_VERIFY_SSL',
                'TF_MODEL_PATH', 'TF_USE_GPU', 'TF_GPU_MEMORY_LIMIT', 'TF_CONFIDENCE_THRESHOLD',
                'LOG_LEVEL', 'LOG_FORMAT', 'LOG_FILE',
                'BATCH_SIZE', 'MAX_WORKERS', 'PROCESSING_TIMEOUT'
            ]
            
            for key in expected_keys:
                assert key in config_dict, f"Key '{key}' missing from config_dict"

    def test_str_representation(self):
        """Test that __str__ returns a string representation of the configuration."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'development'
            
            config = AppConfig()
            config_str = str(config)
            
            assert "AppConfig" in config_str
            assert "environment=Environment.DEVELOPMENT" in config_str
            assert "service=ocr-service" in config_str
            assert "version=1.0.0" in config_str

    def test_get_config_singleton(self):
        """Test that get_config returns a singleton instance of AppConfig."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ['ENVIRONMENT'] = 'development'
            
            # Get the config instance twice
            config1 = get_config()
            config2 = get_config()
            
            # Check that they are the same instance
            assert config1 is config2


class TestAppConfigWithFixtures:
    """Test suite for AppConfig using pytest fixtures."""

    def test_development_environment(self, dev_env_vars):
        """Test configuration with development environment variables."""
        config = AppConfig()
        
        # Check environment-specific values
        assert config.ENVIRONMENT == Environment.DEVELOPMENT
        assert config.RABBITMQ_HOST == 'localhost'
        assert config.RABBITMQ_USE_TLS is False
        assert config.S3_ENDPOINT == 'localhost:4566'
        assert config.S3_USE_SSL is False
        assert config.TF_USE_GPU is False
        assert config.LOG_LEVEL == LogLevel.DEBUG

    def test_staging_environment(self, staging_env_vars):
        """Test configuration with staging environment variables."""
        config = AppConfig()
        
        # Check environment-specific values
        assert config.ENVIRONMENT == Environment.STAGING
        assert config.RABBITMQ_HOST == 'rabbitmq.staging'
        assert config.RABBITMQ_USE_TLS is True
        assert config.RABBITMQ_CLIENT_CERT == '/etc/rabbitmq/certs/client.pem'
        assert config.S3_ENDPOINT == 's3.amazonaws.com'
        assert config.S3_USE_SSL is True
        assert config.TF_USE_GPU is True
        assert config.TF_GPU_MEMORY_LIMIT == 8192
        assert config.LOG_LEVEL == LogLevel.INFO

    def test_production_environment(self, prod_env_vars):
        """Test configuration with production environment variables."""
        config = AppConfig()
        
        # Check environment-specific values
        assert config.ENVIRONMENT == Environment.PRODUCTION
        assert config.RABBITMQ_HOST == 'rabbitmq.production'
        assert config.RABBITMQ_USE_TLS is True
        assert config.RABBITMQ_CLIENT_CERT == '/etc/rabbitmq/certs/client.pem'
        assert config.S3_ENDPOINT == 's3.amazonaws.com'
        assert config.S3_USE_SSL is True
        assert config.TF_USE_GPU is True
        assert config.TF_GPU_MEMORY_LIMIT == 16384
        assert config.LOG_LEVEL == LogLevel.INFO
        assert config.TF_CONFIDENCE_THRESHOLD == 0.90

    def test_missing_required_env_vars(self, env_vars, clear_env_vars):
        """Test that missing required environment variables raise appropriate errors."""
        # Set minimal environment
        env_vars['ENVIRONMENT'] = 'production'
        env_vars['RABBITMQ_USE_TLS'] = 'true'
        
        # Clear specific variables to test validation
        clear_env_vars(['RABBITMQ_CLIENT_CERT', 'RABBITMQ_CLIENT_KEY', 'RABBITMQ_CA_CERT',
                        'S3_ACCESS_KEY', 'S3_SECRET_KEY'])
        
        # Create config and validate
        config = AppConfig()
        
        # Validation should fail due to missing required variables
        with pytest.raises(ValueError):
            config._validate_configuration()

    def test_override_defaults(self, env_vars):
        """Test that environment variables override default values."""
        # Set custom values
        env_vars['HOST'] = 'custom-host'
        env_vars['PORT'] = '9090'
        env_vars['RABBITMQ_HOST'] = 'custom-rabbitmq'
        env_vars['RABBITMQ_PORT'] = '5673'
        env_vars['S3_BUCKET'] = 'custom-bucket'
        env_vars['TF_MODEL_PATH'] = '/custom/models'
        env_vars['LOG_LEVEL'] = 'ERROR'
        env_vars['BATCH_SIZE'] = '50'
        
        # Create config
        config = AppConfig()
        
        # Check custom values
        assert config.HOST == 'custom-host'
        assert config.PORT == 9090
        assert config.RABBITMQ_HOST == 'custom-rabbitmq'
        assert config.RABBITMQ_PORT == 5673
        assert config.S3_BUCKET == 'custom-bucket'
        assert config.TF_MODEL_PATH == '/custom/models'
        assert config.LOG_LEVEL == LogLevel.ERROR
        assert config.BATCH_SIZE == 50

    def test_config_validation_with_fixtures(self, config_validator, mock_app_config):
        """Test configuration validation using the config_validator fixture."""
        # Get config as dictionary
        config_dict = mock_app_config.as_dict()
        
        # Validate required fields
        required_fields = [
            'SERVICE_NAME', 'ENVIRONMENT', 'HOST', 'PORT',
            'RABBITMQ_HOST', 'RABBITMQ_PORT', 'RABBITMQ_EXCHANGE', 'RABBITMQ_QUEUE',
            'S3_ENDPOINT', 'S3_REGION', 'S3_BUCKET',
            'TF_MODEL_PATH', 'TF_CONFIDENCE_THRESHOLD',
            'LOG_LEVEL', 'LOG_FORMAT',
            'BATCH_SIZE', 'MAX_WORKERS', 'PROCESSING_TIMEOUT'
        ]
        
        config_validator(config_dict, required_fields)

    def test_config_defaults_with_fixtures(self, config_defaults, mock_app_config):
        """Test configuration defaults using the config_defaults fixture."""
        # Get config as dictionary
        config_dict = mock_app_config.as_dict()
        
        # Check default values
        expected_defaults = {
            'SERVICE_NAME': 'ocr-service-test',
            'SERVICE_VERSION': '1.0.0-test',
            'ENVIRONMENT': Environment.DEVELOPMENT,
            'HOST': 'localhost',
            'PORT': 8080,
            'RABBITMQ_HOST': 'localhost',
            'RABBITMQ_PORT': 5672,
            'RABBITMQ_VHOST': '/',
            'RABBITMQ_EXCHANGE': 'mca.documents',
            'RABBITMQ_QUEUE': 'data-extraction',
            'S3_BUCKET': 'mca-documents-development',
            'TF_MODEL_PATH': './models',
            'TF_CONFIDENCE_THRESHOLD': 0.75,
            'LOG_LEVEL': LogLevel.DEBUG,
            'BATCH_SIZE': 10,
            'MAX_WORKERS': 4,
            'PROCESSING_TIMEOUT': 300
        }
        
        config_defaults(config_dict, expected_defaults)