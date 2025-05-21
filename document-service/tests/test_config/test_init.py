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
        
        # Set up mock exports for each module
        self.mock_modules['config.app_config'].app_config = 'app_config_mock'
        self.mock_modules['config.app_config'].get_app_config = 'get_app_config_mock'
        self.mock_modules['config.app_config'].AppConfig = 'AppConfig_mock'
        self.mock_modules['config.app_config'].Environment = 'Environment_mock'
        
        self.mock_modules['config.rabbitmq_config'].rabbitmq_client = 'rabbitmq_client_mock'
        self.mock_modules['config.rabbitmq_config'].get_rabbitmq_client = 'get_rabbitmq_client_mock'
        self.mock_modules['config.rabbitmq_config'].consume_messages = 'consume_messages_mock'
        self.mock_modules['config.rabbitmq_config'].RabbitMQClient = 'RabbitMQClient_mock'
        
        self.mock_modules['config.s3_config'].s3_client = 's3_client_mock'
        self.mock_modules['config.s3_config'].get_s3_client = 'get_s3_client_mock'
        self.mock_modules['config.s3_config'].upload_document = 'upload_document_mock'
        self.mock_modules['config.s3_config'].download_document = 'download_document_mock'
        
        self.mock_modules['config.model_config'].model_config = 'model_config_mock'
        self.mock_modules['config.model_config'].get_model_config = 'get_model_config_mock'
        self.mock_modules['config.model_config'].load_model = 'load_model_mock'
        
        self.mock_modules['config.logging_config'].configure_logging = 'configure_logging_mock'
        self.mock_modules['config.logging_config'].get_logger = 'get_logger_mock'
        
        # Add mock modules to sys.modules
        for module_name, module_mock in self.mock_modules.items():
            sys.modules[module_name] = module_mock
    
    def tearDown(self):
        """Clean up test environment after each test."""
        # Remove mock modules from sys.modules
        for module_name in self.mock_modules:
            if module_name in sys.modules:
                del sys.modules[module_name]
        
        # Remove the config module if it was imported
        if 'config' in sys.modules:
            del sys.modules['config']
    
    def test_all_exports(self):
        """Test that __all__ contains all expected exports."""
        # Import the config module
        import config
        
        # Expected exports
        expected_exports = [
            # App configuration
            'app_config',
            'get_app_config',
            'AppConfig',
            'Environment',
            
            # RabbitMQ configuration
            'rabbitmq_client',
            'get_rabbitmq_client',
            'consume_messages',
            'RabbitMQClient',
            
            # S3 configuration
            's3_client',
            'get_s3_client',
            'upload_document',
            'download_document',
            
            # Model configuration
            'model_config',
            'get_model_config',
            'load_model',
            
            # Logging configuration
            'configure_logging',
            'get_logger'
        ]
        
        # Check that __all__ contains all expected exports
        self.assertEqual(sorted(config.__all__), sorted(expected_exports))
    
    def test_app_config_exports(self):
        """Test that app_config exports are correctly re-exported."""
        # Import the config module
        import config
        
        # Check that app_config exports are correctly re-exported
        self.assertEqual(config.app_config, 'app_config_mock')
        self.assertEqual(config.get_app_config, 'get_app_config_mock')
        self.assertEqual(config.AppConfig, 'AppConfig_mock')
        self.assertEqual(config.Environment, 'Environment_mock')
    
    def test_rabbitmq_config_exports(self):
        """Test that rabbitmq_config exports are correctly re-exported."""
        # Import the config module
        import config
        
        # Check that rabbitmq_config exports are correctly re-exported
        self.assertEqual(config.rabbitmq_client, 'rabbitmq_client_mock')
        self.assertEqual(config.get_rabbitmq_client, 'get_rabbitmq_client_mock')
        self.assertEqual(config.consume_messages, 'consume_messages_mock')
        self.assertEqual(config.RabbitMQClient, 'RabbitMQClient_mock')
    
    def test_s3_config_exports(self):
        """Test that s3_config exports are correctly re-exported."""
        # Import the config module
        import config
        
        # Check that s3_config exports are correctly re-exported
        self.assertEqual(config.s3_client, 's3_client_mock')
        self.assertEqual(config.get_s3_client, 'get_s3_client_mock')
        self.assertEqual(config.upload_document, 'upload_document_mock')
        self.assertEqual(config.download_document, 'download_document_mock')
    
    def test_model_config_exports(self):
        """Test that model_config exports are correctly re-exported."""
        # Import the config module
        import config
        
        # Check that model_config exports are correctly re-exported
        self.assertEqual(config.model_config, 'model_config_mock')
        self.assertEqual(config.get_model_config, 'get_model_config_mock')
        self.assertEqual(config.load_model, 'load_model_mock')
    
    def test_logging_config_exports(self):
        """Test that logging_config exports are correctly re-exported."""
        # Import the config module
        import config
        
        # Check that logging_config exports are correctly re-exported
        self.assertEqual(config.configure_logging, 'configure_logging_mock')
        self.assertEqual(config.get_logger, 'get_logger_mock')
    
    def test_clean_import_paths(self):
        """Test that clean import paths work as expected."""
        # These imports should work without errors
        from config import app_config
        from config import get_app_config
        from config import AppConfig
        from config import Environment
        
        from config import rabbitmq_client
        from config import get_rabbitmq_client
        from config import consume_messages
        from config import RabbitMQClient
        
        from config import s3_client
        from config import get_s3_client
        from config import upload_document
        from config import download_document
        
        from config import model_config
        from config import get_model_config
        from config import load_model
        
        from config import configure_logging
        from config import get_logger
        
        # Verify that the imports match the expected values
        self.assertEqual(app_config, 'app_config_mock')
        self.assertEqual(rabbitmq_client, 'rabbitmq_client_mock')
        self.assertEqual(s3_client, 's3_client_mock')
        self.assertEqual(model_config, 'model_config_mock')
        self.assertEqual(configure_logging, 'configure_logging_mock')
    
    def test_import_all(self):
        """Test that importing * works as expected."""
        # Create a clean namespace
        namespace = {}
        
        # Execute the import in the namespace
        exec('from config import *', namespace)
        
        # Check that all expected exports are in the namespace
        self.assertEqual(namespace['app_config'], 'app_config_mock')
        self.assertEqual(namespace['get_app_config'], 'get_app_config_mock')
        self.assertEqual(namespace['AppConfig'], 'AppConfig_mock')
        self.assertEqual(namespace['Environment'], 'Environment_mock')
        
        self.assertEqual(namespace['rabbitmq_client'], 'rabbitmq_client_mock')
        self.assertEqual(namespace['get_rabbitmq_client'], 'get_rabbitmq_client_mock')
        self.assertEqual(namespace['consume_messages'], 'consume_messages_mock')
        self.assertEqual(namespace['RabbitMQClient'], 'RabbitMQClient_mock')
        
        self.assertEqual(namespace['s3_client'], 's3_client_mock')
        self.assertEqual(namespace['get_s3_client'], 'get_s3_client_mock')
        self.assertEqual(namespace['upload_document'], 'upload_document_mock')
        self.assertEqual(namespace['download_document'], 'download_document_mock')
        
        self.assertEqual(namespace['model_config'], 'model_config_mock')
        self.assertEqual(namespace['get_model_config'], 'get_model_config_mock')
        self.assertEqual(namespace['load_model'], 'load_model_mock')
        
        self.assertEqual(namespace['configure_logging'], 'configure_logging_mock')
        self.assertEqual(namespace['get_logger'], 'get_logger_mock')
    
    def test_module_structure(self):
        """Test that the module structure is intact."""
        # Import the config module
        import config
        
        # Check that the module has the expected attributes
        self.assertTrue(hasattr(config, '__all__'))
        self.assertTrue(hasattr(config, '__doc__'))
        
        # Check that the module docstring is not empty
        self.assertIsNotNone(config.__doc__)
        self.assertGreater(len(config.__doc__), 0)


if __name__ == '__main__':
    unittest.main()