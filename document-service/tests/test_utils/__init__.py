# -*- coding: utf-8 -*-
"""
Document Service Test Utilities Package

This package contains test modules for the Document Service utility functions. It provides
comprehensive test coverage for all utility modules, including file operations, S3 storage,
RabbitMQ messaging, machine learning, logging, error handling, validation, retry logic,
security, and time utilities.

The test modules are organized to match the structure of the utility modules they test,
making it easy to locate tests for specific functionality.

Example:
    # Running all tests in the package
    pytest document-service/tests/test_utils
    
    # Running tests for a specific module
    pytest document-service/tests/test_utils/test_file_utils.py
"""

__version__ = '1.0.0'
__test_framework__ = 'pytest'

# Import test modules to make them discoverable
from . import (
    test_file_utils,
    test_time_utils,
    test_logging_utils,
    test_error_utils,
    test_validation_utils,
    test_security_utils,
    test_retry_utils,
    test_s3_utils,
    test_rabbitmq_utils,
    test_ml_utils
)

# Define __all__ to explicitly specify what is exported
__all__ = [
    # Version and framework info
    '__version__',
    '__test_framework__',
    
    # Test modules
    'test_file_utils',
    'test_time_utils',
    'test_logging_utils',
    'test_error_utils',
    'test_validation_utils',
    'test_security_utils',
    'test_retry_utils',
    'test_s3_utils',
    'test_rabbitmq_utils',
    'test_ml_utils'
]