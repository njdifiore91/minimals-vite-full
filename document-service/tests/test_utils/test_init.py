# -*- coding: utf-8 -*-
"""Unit tests for the Document Service utilities package initialization.

This module contains tests to verify that the utils package is properly initialized,
all utility functions are correctly exposed, and imports work as expected.
"""

import unittest
import re
import importlib
import inspect
import sys
from unittest.mock import patch

# Import the utils package to test
import document_service.src.utils as utils


class TestUtilsInit(unittest.TestCase):
    """Test case for the Document Service utilities package initialization."""

    def test_version_exists(self):
        """Test that the __version__ attribute exists and is a valid version string."""
        self.assertTrue(hasattr(utils, '__version__'))
        self.assertIsInstance(utils.__version__, str)
        # Verify version follows semantic versioning (MAJOR.MINOR.PATCH)
        version_pattern = r'^\d+\.\d+\.\d+$'
        self.assertTrue(re.match(version_pattern, utils.__version__))

    def test_all_list_exists(self):
        """Test that the __all__ list exists and contains expected items."""
        self.assertTrue(hasattr(utils, '__all__'))
        self.assertIsInstance(utils.__all__, list)
        # Verify __all__ contains at least some expected utility functions
        expected_items = [
            '__version__',
            'format_timestamp',
            'validate_document_type',
            'setup_logger',
            'encrypt_data',
            'retry_with_backoff',
            'initialize_s3_client',
            'initialize_rabbitmq',
            'load_classification_model'
        ]
        for item in expected_items:
            self.assertIn(item, utils.__all__)

    def test_all_items_importable(self):
        """Test that all items listed in __all__ are actually importable."""
        for item in utils.__all__:
            if item == '__version__':
                continue  # Skip version as it's not an importable function
            self.assertTrue(hasattr(utils, item))
            # Verify the item is either a function, class, or module
            attr = getattr(utils, item)
            is_valid = (inspect.isfunction(attr) or 
                        inspect.isclass(attr) or 
                        inspect.ismodule(attr))
            self.assertTrue(is_valid, f"{item} is not a function, class, or module")

    def test_import_order_prevents_circular_dependencies(self):
        """Test that the import order prevents circular dependencies."""
        # This test simulates reloading the module to check for import errors
        with patch('sys.modules') as mock_modules:
            # Remove the utils module from sys.modules to force a reload
            original_modules = sys.modules.copy()
            mock_modules.return_value = original_modules
            
            # Try to reload the module
            try:
                importlib.reload(utils)
                import_succeeded = True
            except ImportError:
                import_succeeded = False
            
            self.assertTrue(import_succeeded, "Circular dependency detected in utils package")

    def test_module_has_docstring(self):
        """Test that the utils package has a proper docstring."""
        self.assertTrue(utils.__doc__ is not None)
        self.assertIsInstance(utils.__doc__, str)
        self.assertTrue(len(utils.__doc__) > 0)
        
        # Check that the docstring contains expected sections
        docstring = utils.__doc__
        self.assertIn("Document Service", docstring)
        self.assertIn("Example:", docstring)

    def test_utility_modules_have_consistent_structure(self):
        """Test that all utility modules have a consistent structure."""
        # Get all modules imported in utils
        modules = [getattr(utils, name) for name in dir(utils) 
                  if inspect.ismodule(getattr(utils, name))]
        
        # Skip empty list (no modules found)
        if not modules:
            self.skipTest("No modules found in utils package")
        
        for module in modules:
            # Check that each module has a docstring
            self.assertTrue(module.__doc__ is not None, 
                           f"Module {module.__name__} has no docstring")
            
            # Check that each module has a __all__ list
            self.assertTrue(hasattr(module, '__all__'), 
                           f"Module {module.__name__} has no __all__ list")

    def test_time_utils_functions_exposed(self):
        """Test that time utility functions are properly exposed."""
        time_functions = [
            'format_timestamp',
            'get_current_timestamp',
            'calculate_duration',
            'compare_dates',
            'format_iso8601',
            'parse_iso8601',
            'get_processing_time'
        ]
        for func in time_functions:
            self.assertTrue(hasattr(utils, func))
            self.assertIn(func, utils.__all__)

    def test_file_utils_functions_exposed(self):
        """Test that file utility functions are properly exposed."""
        file_functions = [
            'get_file_extension',
            'get_mime_type',
            'calculate_file_size',
            'format_file_size',
            'create_temp_file',
            'cleanup_temp_files',
            'is_supported_document_type'
        ]
        for func in file_functions:
            self.assertTrue(hasattr(utils, func))
            self.assertIn(func, utils.__all__)

    def test_s3_utils_functions_exposed(self):
        """Test that S3 utility functions are properly exposed."""
        s3_functions = [
            'initialize_s3_client',
            'upload_document',
            'download_document',
            'generate_presigned_url',
            'get_document_metadata_from_s3',
            'list_documents',
            'delete_document'
        ]
        for func in s3_functions:
            self.assertTrue(hasattr(utils, func))
            self.assertIn(func, utils.__all__)

    def test_rabbitmq_utils_functions_exposed(self):
        """Test that RabbitMQ utility functions are properly exposed."""
        rabbitmq_functions = [
            'initialize_rabbitmq',
            'create_channel',
            'publish_message',
            'consume_messages',
            'acknowledge_message',
            'reject_message',
            'close_connection'
        ]
        for func in rabbitmq_functions:
            self.assertTrue(hasattr(utils, func))
            self.assertIn(func, utils.__all__)

    def test_ml_utils_functions_exposed(self):
        """Test that machine learning utility functions are properly exposed."""
        ml_functions = [
            'load_classification_model',
            'extract_features',
            'classify_document',
            'get_confidence_score',
            'update_model_metrics',
            'get_model_version',
            'validate_model_performance'
        ]
        for func in ml_functions:
            self.assertTrue(hasattr(utils, func))
            self.assertIn(func, utils.__all__)


if __name__ == '__main__':
    unittest.main()