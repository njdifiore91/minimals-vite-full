#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Document Service Test Configuration Package

This package contains test configurations, fixtures, and utilities for testing
the Document Service. It provides a centralized location for test configuration
and shared test utilities that can be imported across test files.

The test_config module enables:
    - Consistent test configuration across all test modules
    - Shared test fixtures and factory functions
    - Mock configurations for external dependencies
    - Test environment setup and teardown utilities
    - Test data generation and validation helpers

Usage:
    from tests.test_config import get_test_config
    from tests.test_config import create_test_document
    from tests.test_config import mock_s3_client
    from tests.test_config import setup_test_environment
"""

# Package version for tracking test configuration changes
__version__ = '0.1.0'

# Import and re-export test configuration components as they're developed
# For example:
# from .test_app_config import get_test_app_config
# from .test_rabbitmq_config import get_test_rabbitmq_config
# from .test_s3_config import get_test_s3_client, mock_s3_client
# from .test_model_config import get_test_model_config
# from .test_fixtures import create_test_document, create_test_classification

# Define package exports
__all__ = [
    # Add exported functions, classes, and variables here as they're developed
    # 'get_test_app_config',
    # 'get_test_rabbitmq_config',
    # 'get_test_s3_client',
    # 'mock_s3_client',
    # 'get_test_model_config',
    # 'create_test_document',
    # 'create_test_classification',
]