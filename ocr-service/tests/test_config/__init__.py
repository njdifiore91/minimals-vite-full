#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Test Configuration Package

This package contains test utilities and fixtures for testing the OCR Service's
configuration modules. It makes the test module discoverable by pytest and enables
importing test utilities across test files.

The test_config module provides specialized test fixtures and utilities for verifying
that the OCR Service configuration correctly handles:
- Environment variable loading and validation
- TensorFlow model configuration with GPU acceleration
- S3 storage configuration with encryption settings
- RabbitMQ connection and queue configuration
- Logging setup across different environments

Example usage in test files:
    from tests.test_config import mock_environment_variables
    from tests.test_config import create_test_config
    from tests.test_config import TEST_MODEL_PATHS
    
    def test_tensorflow_config_loading(mock_environment_variables):
        # Test implementation using the imported fixtures
        ...
"""

# Package version for tracking test compatibility with implementation
__version__ = '0.1.0'

# Test environment constants that can be imported by test modules
TEST_ENVIRONMENTS = ['development', 'staging', 'production']
TEST_LOG_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR']

# Define what should be imported with 'from tests.test_config import *'
__all__ = [
    # Version information
    '__version__',
    
    # Test environment constants
    'TEST_ENVIRONMENTS',
    'TEST_LOG_LEVELS',
    
    # The package doesn't export any fixtures directly as they should be
    # imported from conftest.py by pytest automatically
]