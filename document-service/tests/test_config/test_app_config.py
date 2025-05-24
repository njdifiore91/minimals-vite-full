#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's app_config.py module.

This module contains tests to verify that application configuration correctly loads
from environment variables, validates required settings, and provides appropriate
defaults for development, staging, and production environments.
"""

import os
import pytest
from unittest.mock import patch
from pathlib import Path

# Import the module under test
from src.config.app_config import (
    AppConfig,
    EnvironmentType,
    get_app_config,
    app_config
)


class TestEnvironmentType:
    """Tests for the EnvironmentType enum."""

    def test_environment_type_values(self):
        """Test that EnvironmentType enum has the expected values."""
        assert EnvironmentType.DEVELOPMENT == "development"
        assert EnvironmentType.STAGING == "staging"
        assert EnvironmentType.PRODUCTION == "production"


class TestAppConfigDefaults:
    """Tests for AppConfig default values."""

    def test_default_values(self):
        """Test that AppConfig has the expected default values."""
        config = AppConfig()
        
        # Service information
        assert config.SERVICE_NAME == "document-service"
        assert config.SERVICE_VERSION == "1.0.0"
        
        # Environment configuration
        assert config.ENVIRONMENT == EnvironmentType.DEVELOPMENT
        
        # Server configuration
        assert config.HOST == "0.0.0.0"
        assert config.PORT == 8000
        
        # API configuration
        assert config.API_PREFIX == "/api/v1"
        
        # Logging configuration
        assert config.LOG_LEVEL == "INFO"
        assert config.LOG_FORMAT == "json"
        
        # Document classification confidence thresholds
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.75
        assert config.HIGH_CONFIDENCE_THRESHOLD == 0.95
        
        # Performance settings
        assert config.WORKER_THREADS == 4
        assert config.BATCH_SIZE == 10
        
        # Timeout settings
        assert config.REQUEST_TIMEOUT_SECONDS == 30
        assert config.PROCESSING_TIMEOUT_SECONDS == 300
        
        # Feature flags
        assert config.ENABLE_GPU_ACCELERATION is False
        
        # Model settings
        assert config.MODEL_PATH == "./models"
        
        # Health check settings
        assert config.HEALTH_CHECK_INTERVAL_SECONDS == 60
        
        # Metrics settings
        assert config.ENABLE_METRICS is True
        assert config.METRICS_PORT == 9090


class TestAppConfigEnvironmentOverrides:
    """Tests for environment variable overrides in AppConfig."""

    def test_environment_variable_overrides(self, monkeypatch):
        """Test that environment variables override default values."""
        # Set environment variables
        env_vars = {
            "SERVICE_NAME": "custom-document-service",
            "PORT": "9000",
            "LOG_LEVEL": "DEBUG",
            "MIN_CONFIDENCE_THRESHOLD": "0.85",
            "WORKER_THREADS": "8",
            "ENABLE_GPU_ACCELERATION": "true",
            "MODEL_PATH": "/custom/models",
        }
        
        for key, value in env_vars.items():
            monkeypatch.setenv(key, value)
        
        # Create config with environment variables
        config = AppConfig()
        
        # Check that environment variables override defaults
        assert config.SERVICE_NAME == "custom-document-service"
        assert config.PORT == 9000
        assert config.LOG_LEVEL == "DEBUG"
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.85
        assert config.WORKER_THREADS == 8
        assert config.ENABLE_GPU_ACCELERATION is True
        assert config.MODEL_PATH == "/custom/models"

    def test_boolean_environment_variable_parsing(self, monkeypatch):
        """Test that boolean environment variables are parsed correctly."""
        # Test various boolean string representations
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
        ]
        
        for value_str, expected_bool in test_cases:
            monkeypatch.setenv("ENABLE_GPU_ACCELERATION", value_str)
            config = AppConfig()
            assert config.ENABLE_GPU_ACCELERATION is expected_bool, \
                f"Failed to parse '{value_str}' as {expected_bool}"

    def test_numeric_environment_variable_parsing(self, monkeypatch):
        """Test that numeric environment variables are parsed correctly."""
        # Test integer parsing
        monkeypatch.setenv("PORT", "9999")
        monkeypatch.setenv("WORKER_THREADS", "16")
        config = AppConfig()
        assert config.PORT == 9999
        assert config.WORKER_THREADS == 16
        
        # Test float parsing
        monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.95")
        monkeypatch.setenv("HIGH_CONFIDENCE_THRESHOLD", "0.99")
        config = AppConfig()
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.95
        assert config.HIGH_CONFIDENCE_THRESHOLD == 0.99


class TestAppConfigValidation:
    """Tests for AppConfig validation."""

    def test_log_level_validation(self, monkeypatch):
        """Test that LOG_LEVEL is validated correctly."""
        # Valid log levels
        valid_levels = ["ERROR", "WARN", "INFO", "DEBUG"]
        
        for level in valid_levels:
            monkeypatch.setenv("LOG_LEVEL", level)
            config = AppConfig()
            assert config.LOG_LEVEL == level
        
        # Invalid log level should raise ValueError
        monkeypatch.setenv("LOG_LEVEL", "INVALID")
        with pytest.raises(ValueError) as excinfo:
            AppConfig()
        assert "Log level must be one of" in str(excinfo.value)

    def test_log_level_case_insensitivity(self, monkeypatch):
        """Test that LOG_LEVEL validation is case-insensitive."""
        # Test with lowercase
        monkeypatch.setenv("LOG_LEVEL", "debug")
        config = AppConfig()
        assert config.LOG_LEVEL == "DEBUG"
        
        # Test with mixed case
        monkeypatch.setenv("LOG_LEVEL", "InFo")
        config = AppConfig()
        assert config.LOG_LEVEL == "INFO"


class TestEnvironmentSpecificSettings:
    """Tests for environment-specific settings."""

    def test_development_environment_settings(self, monkeypatch):
        """Test that development environment settings are applied correctly."""
        monkeypatch.setenv("ENVIRONMENT", "development")
        config = AppConfig()
        
        # Check development-specific settings
        assert config.LOG_LEVEL == "DEBUG"
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.6
        assert config.ENABLE_GPU_ACCELERATION is False
        assert config.WORKER_THREADS == 2
        assert config.BATCH_SIZE == 5

    def test_staging_environment_settings(self, monkeypatch):
        """Test that staging environment settings are applied correctly."""
        monkeypatch.setenv("ENVIRONMENT", "staging")
        config = AppConfig()
        
        # Check staging-specific settings
        assert config.LOG_LEVEL == "INFO"
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.7
        assert config.ENABLE_GPU_ACCELERATION is True
        assert config.WORKER_THREADS == 4
        assert config.BATCH_SIZE == 10

    def test_production_environment_settings(self, monkeypatch):
        """Test that production environment settings are applied correctly."""
        monkeypatch.setenv("ENVIRONMENT", "production")
        config = AppConfig()
        
        # Check production-specific settings
        assert config.LOG_LEVEL == "INFO"
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.75
        assert config.ENABLE_GPU_ACCELERATION is True
        assert config.WORKER_THREADS == 8
        assert config.BATCH_SIZE == 20

    def test_environment_specific_settings_override_env_vars(self, monkeypatch):
        """Test that environment-specific settings override environment variables."""
        # Set environment variables
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        monkeypatch.setenv("MIN_CONFIDENCE_THRESHOLD", "0.99")
        monkeypatch.setenv("WORKER_THREADS", "16")
        
        config = AppConfig()
        
        # Environment-specific settings should override environment variables
        assert config.LOG_LEVEL == "DEBUG"  # From development settings
        assert config.MIN_CONFIDENCE_THRESHOLD == 0.6  # From development settings
        assert config.WORKER_THREADS == 2  # From development settings


class TestAppConfigSingleton:
    """Tests for AppConfig singleton pattern."""

    def test_get_app_config_returns_singleton(self):
        """Test that get_app_config() returns a singleton instance."""
        config1 = get_app_config()
        config2 = get_app_config()
        
        # Both calls should return the same instance
        assert config1 is config2

    def test_app_config_singleton_exported(self):
        """Test that app_config is a singleton instance."""
        # app_config should be the same instance as returned by get_app_config()
        assert app_config is get_app_config()

    def test_singleton_with_environment_changes(self, monkeypatch):
        """Test singleton behavior with environment changes."""
        # Get initial singleton
        initial_config = get_app_config()
        
        # Change environment and get new instance
        with patch("src.config.app_config.AppConfig") as mock_config:
            mock_instance = mock_config.return_value
            new_config = get_app_config()
            
            # Should return the initial singleton, not create a new instance
            assert new_config is initial_config
            mock_config.assert_not_called()


class TestAppConfigWithFiles:
    """Tests for AppConfig with file paths."""

    def test_model_path_resolution(self, monkeypatch, tmp_path):
        """Test that MODEL_PATH is resolved correctly."""
        # Create a temporary directory for models
        models_dir = tmp_path / "models"
        models_dir.mkdir()
        
        # Set MODEL_PATH to the temporary directory
        monkeypatch.setenv("MODEL_PATH", str(models_dir))
        
        config = AppConfig()
        assert config.MODEL_PATH == str(models_dir)


class TestAppConfigIntegration:
    """Integration tests for AppConfig."""

    def test_config_with_env_file(self, monkeypatch, tmp_path):
        """Test that AppConfig loads from .env file."""
        # Create a temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text("""
        SERVICE_NAME=env-file-service
        PORT=7000
        LOG_LEVEL=WARN
        MIN_CONFIDENCE_THRESHOLD=0.8
        ENABLE_GPU_ACCELERATION=true
        """)
        
        # Set the env_file path in Pydantic settings
        with patch("src.config.app_config.AppConfig.model_config", {"env_file": str(env_file)}), \
             patch.object(Path, "exists", return_value=True):
            config = AppConfig()
            
            # Check that values from .env file are used
            assert config.SERVICE_NAME == "env-file-service"
            assert config.PORT == 7000
            assert config.LOG_LEVEL == "WARN"
            assert config.MIN_CONFIDENCE_THRESHOLD == 0.8
            assert config.ENABLE_GPU_ACCELERATION is True