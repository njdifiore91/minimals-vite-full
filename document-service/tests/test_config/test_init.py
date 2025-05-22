#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's config/__init__.py module.

These tests verify that the package initialization correctly imports and re-exports
all configuration components, providing a clean API surface for configuration imports
throughout the service.
"""

import unittest
import importlib
import sys
from unittest import mock


class TestConfigInit(unittest.TestCase):
    """Test cases for the config package initialization."""

    def setUp(self):
        """Set up test environment before each test."""
        # Create mock modules to avoid actual imports during testing
        self.mock_modules = {
            'config.app_config': mock.MagicMock(),
            'config.rabbitmq_config': mock.MagicMock(),
            'config.s3_config': mock.MagicMock(),
            'config.model_config': mock.MagicMock(),
            'config.logging_config': mock.MagicMock(),
        }
        
        # Set up mock attributes for each module
        self.mock_modules['config.app_config'].AppConfig = 'AppConfig'
        self.mock_modules['config.app_config'].get_app_config = 'get_app_config'
        self.mock_modules['config.app_config'].validate_config = 'validate_config'
        self.mock_modules['config.app_config'].ENV = 'ENV'
        self.mock_modules['config.app_config'].SERVICE_NAME = 'SERVICE_NAME'
        self.mock_modules['config.app_config'].SERVICE_VERSION = 'SERVICE_VERSION'
        
        self.mock_modules['config.rabbitmq_config'].create_rabbitmq_connection = 'create_rabbitmq_connection'
        self.mock_modules['config.rabbitmq_config'].create_channel = 'create_channel'
        self.mock_modules['config.rabbitmq_config'].setup_exchanges_and_queues = 'setup_exchanges_and_queues'
        self.mock_modules['config.rabbitmq_config'].publish_message = 'publish_message'
        self.mock_modules['config.rabbitmq_config'].start_consuming = 'start_consuming'
        self.mock_modules['config.rabbitmq_config'].EXCHANGE_NAME = 'EXCHANGE_NAME'
        self.mock_modules['config.rabbitmq_config'].QUEUE_NAME = 'QUEUE_NAME'
        self.mock_modules['config.rabbitmq_config'].ROUTING_KEY = 'ROUTING_KEY'
        
        self.mock_modules['config.s3_config'].create_s3_client = 'create_s3_client'
        self.mock_modules['config.s3_config'].create_s3_resource = 'create_s3_resource'
        self.mock_modules['config.s3_config'].upload_file_with_encryption = 'upload_file_with_encryption'
        self.mock_modules['config.s3_config'].download_file = 'download_file'
        self.mock_modules['config.s3_config'].check_bucket_exists = 'check_bucket_exists'
        self.mock_modules['config.s3_config'].create_bucket_if_not_exists = 'create_bucket_if_not_exists'
        self.mock_modules['config.s3_config'].get_bucket_name = 'get_bucket_name'
        self.mock_modules['config.s3_config'].s3_client = 's3_client'
        self.mock_modules['config.s3_config'].s3_resource = 's3_resource'
        
        self.mock_modules['config.model_config'].MODEL_TYPES = 'MODEL_TYPES'
        self.mock_modules['config.model_config'].MODEL_HYPERPARAMETERS = 'MODEL_HYPERPARAMETERS'
        self.mock_modules['config.model_config'].FEATURE_EXTRACTION_PARAMS = 'FEATURE_EXTRACTION_PARAMS'
        self.mock_modules['config.model_config'].CLASSIFICATION_THRESHOLDS = 'CLASSIFICATION_THRESHOLDS'
        self.mock_modules['config.model_config'].MODEL_PATHS = 'MODEL_PATHS'
        self.mock_modules['config.model_config'].get_model_path = 'get_model_path'
        self.mock_modules['config.model_config'].get_model_hyperparameters = 'get_model_hyperparameters'
        
        self.mock_modules['config.logging_config'].configure_logging = 'configure_logging'
        self.mock_modules['config.logging_config'].get_logger = 'get_logger'
        self.mock_modules['config.logging_config'].LoggingContext = 'LoggingContext'
        self.mock_modules['config.logging_config'].DEFAULT_LOG_LEVEL = 'DEFAULT_LOG_LEVEL'
        self.mock_modules['config.logging_config'].SERVICE_NAME = 'LOGGING_SERVICE_NAME'
        
        # Apply the mocks
        self.patches = []
        for module_name, mock_module in self.mock_modules.items():
            patch = mock.patch(module_name, mock_module)
            patch.start()
            self.patches.append(patch)
        
        # Import the config module after patching
        if 'config' in sys.modules:
            del sys.modules['config']
        import config
        self.config = config

    def tearDown(self):
        """Clean up after each test."""
        # Stop all patches
        for patch in self.patches:
            patch.stop()
        
        # Remove the imported module
        if 'config' in sys.modules:
            del sys.modules['config']

    def test_app_config_imports(self):
        """Test that app_config components are correctly imported and exposed."""
        self.assertEqual(self.config.AppConfig, 'AppConfig')
        self.assertEqual(self.config.get_app_config, 'get_app_config')
        self.assertEqual(self.config.validate_config, 'validate_config')
        self.assertEqual(self.config.ENV, 'ENV')
        self.assertEqual(self.config.SERVICE_NAME, 'SERVICE_NAME')
        self.assertEqual(self.config.SERVICE_VERSION, 'SERVICE_VERSION')

    def test_rabbitmq_config_imports(self):
        """Test that rabbitmq_config components are correctly imported and exposed."""
        self.assertEqual(self.config.create_rabbitmq_connection, 'create_rabbitmq_connection')
        self.assertEqual(self.config.create_channel, 'create_channel')
        self.assertEqual(self.config.setup_exchanges_and_queues, 'setup_exchanges_and_queues')
        self.assertEqual(self.config.publish_message, 'publish_message')
        self.assertEqual(self.config.start_consuming, 'start_consuming')
        self.assertEqual(self.config.EXCHANGE_NAME, 'EXCHANGE_NAME')
        self.assertEqual(self.config.QUEUE_NAME, 'QUEUE_NAME')
        self.assertEqual(self.config.ROUTING_KEY, 'ROUTING_KEY')

    def test_s3_config_imports(self):
        """Test that s3_config components are correctly imported and exposed."""
        self.assertEqual(self.config.create_s3_client, 'create_s3_client')
        self.assertEqual(self.config.create_s3_resource, 'create_s3_resource')
        self.assertEqual(self.config.upload_file_with_encryption, 'upload_file_with_encryption')
        self.assertEqual(self.config.download_file, 'download_file')
        self.assertEqual(self.config.check_bucket_exists, 'check_bucket_exists')
        self.assertEqual(self.config.create_bucket_if_not_exists, 'create_bucket_if_not_exists')
        self.assertEqual(self.config.get_bucket_name, 'get_bucket_name')
        self.assertEqual(self.config.s3_client, 's3_client')
        self.assertEqual(self.config.s3_resource, 's3_resource')

    def test_model_config_imports(self):
        """Test that model_config components are correctly imported and exposed."""
        self.assertEqual(self.config.MODEL_TYPES, 'MODEL_TYPES')
        self.assertEqual(self.config.MODEL_HYPERPARAMETERS, 'MODEL_HYPERPARAMETERS')
        self.assertEqual(self.config.FEATURE_EXTRACTION_PARAMS, 'FEATURE_EXTRACTION_PARAMS')
        self.assertEqual(self.config.CLASSIFICATION_THRESHOLDS, 'CLASSIFICATION_THRESHOLDS')
        self.assertEqual(self.config.MODEL_PATHS, 'MODEL_PATHS')
        self.assertEqual(self.config.get_model_path, 'get_model_path')
        self.assertEqual(self.config.get_model_hyperparameters, 'get_model_hyperparameters')

    def test_logging_config_imports(self):
        """Test that logging_config components are correctly imported and exposed."""
        self.assertEqual(self.config.configure_logging, 'configure_logging')
        self.assertEqual(self.config.get_logger, 'get_logger')
        self.assertEqual(self.config.LoggingContext, 'LoggingContext')
        self.assertEqual(self.config.DEFAULT_LOG_LEVEL, 'DEFAULT_LOG_LEVEL')
        self.assertEqual(self.config.LOGGING_SERVICE_NAME, 'LOGGING_SERVICE_NAME')

    def test_all_variable_completeness(self):
        """Test that __all__ contains all expected exports."""
        expected_exports = [
            # app_config exports
            'AppConfig', 'get_app_config', 'validate_config', 'ENV', 'SERVICE_NAME', 'SERVICE_VERSION',
            
            # rabbitmq_config exports
            'create_rabbitmq_connection', 'create_channel', 'setup_exchanges_and_queues',
            'publish_message', 'start_consuming', 'EXCHANGE_NAME', 'QUEUE_NAME', 'ROUTING_KEY',
            
            # s3_config exports
            'create_s3_client', 'create_s3_resource', 'upload_file_with_encryption',
            'download_file', 'check_bucket_exists', 'create_bucket_if_not_exists',
            'get_bucket_name', 's3_client', 's3_resource',
            
            # model_config exports
            'MODEL_TYPES', 'MODEL_HYPERPARAMETERS', 'FEATURE_EXTRACTION_PARAMS',
            'CLASSIFICATION_THRESHOLDS', 'MODEL_PATHS', 'get_model_path', 'get_model_hyperparameters',
            
            # logging_config exports
            'configure_logging', 'get_logger', 'LoggingContext', 'DEFAULT_LOG_LEVEL', 'LOGGING_SERVICE_NAME'
        ]
        
        # Check that all expected exports are in __all__
        for export in expected_exports:
            self.assertIn(export, self.config.__all__, f"{export} should be in __all__")
        
        # Check that __all__ doesn't contain unexpected exports
        self.assertEqual(len(self.config.__all__), len(expected_exports),
                         "__all__ should contain exactly the expected exports")

    def test_clean_import_paths(self):
        """Test that configuration components can be imported cleanly."""
        with mock.patch.dict('sys.modules'):
            # Remove any existing imports
            for module_name in list(sys.modules.keys()):
                if module_name.startswith('config'):
                    del sys.modules[module_name]
            
            # Test direct imports from config
            with mock.patch('config.app_config'):
                from config import AppConfig, get_app_config, ENV
                # No assertions needed; if the import works, the test passes
            
            with mock.patch('config.rabbitmq_config'):
                from config import create_rabbitmq_connection, EXCHANGE_NAME
                # No assertions needed; if the import works, the test passes
            
            with mock.patch('config.s3_config'):
                from config import create_s3_client, s3_client
                # No assertions needed; if the import works, the test passes
            
            with mock.patch('config.model_config'):
                from config import MODEL_TYPES, get_model_path
                # No assertions needed; if the import works, the test passes
            
            with mock.patch('config.logging_config'):
                from config import get_logger, LoggingContext
                # No assertions needed; if the import works, the test passes

    def test_logging_initialization(self):
        """Test that logging is configured when the config package is imported."""
        # Reset the mock to clear any previous calls
        self.mock_modules['config.logging_config'].configure_logging.reset_mock()
        
        # Re-import the config module
        if 'config' in sys.modules:
            del sys.modules['config']
        import config
        
        # Check that configure_logging was called
        self.mock_modules['config.logging_config'].configure_logging.assert_called_once()


if __name__ == '__main__':
    unittest.main()