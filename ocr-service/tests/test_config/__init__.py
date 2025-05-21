#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Test Configuration Package

This package provides testing utilities and fixtures for the OCR Service configuration modules.
It makes the test module discoverable by pytest and enables importing test utilities across test files.

The test_config package contains tests for all configuration components:

- test_app_config: Tests for core application configuration
- test_rabbitmq_config: Tests for RabbitMQ connection and messaging settings
- test_s3_config: Tests for S3-compatible storage client configuration
- test_tensorflow_config: Tests for TensorFlow models configuration
- test_logging_config: Tests for logging system configuration
- test_init: Tests for the configuration package structure itself

This package also provides shared fixtures and utilities through conftest.py that can be used
across all test modules to ensure consistent testing environments.

Example usage in test files:
    from tests.test_config import get_mock_environment_variables
    
    def test_something():
        # Use shared test utilities
        mock_env_vars = get_mock_environment_variables('development')
        with mock_env_vars:
            # Test with mocked environment variables
            ...
"""

# Import and re-export shared test utilities and fixtures from conftest.py
from .conftest import (
    mock_environment,
    get_mock_environment_variables,
    mock_tensorflow_config,
    mock_s3_config,
    mock_rabbitmq_config,
    mock_app_config,
    mock_logging_config
)

# Version of the test_config package - should match the version of the package being tested
__version__ = '1.0.0'

# Package metadata
__author__ = 'Dollar Funding OCR Team'
__email__ = 'ocr-team@dollarfunding.com'
__description__ = 'Test configuration package for the OCR Service'