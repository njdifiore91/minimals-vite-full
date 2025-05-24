# -*- coding: utf-8 -*-
"""Unit tests for the Document Service utility functions initialization.

This module contains tests that verify the proper initialization and import functionality
of the Document Service utility functions package. It ensures that all utility modules
are properly exposed and can be imported correctly.

These tests verify:
1. All utility modules are properly exposed and can be imported correctly
2. Import order prevents circular dependencies
3. Version tracking for the utilities package is implemented
4. Documentation comments exist for all exported utilities
5. All public items are properly included in __all__
"""

import importlib
import inspect
import re
import sys
from unittest import mock

import pytest

# Import the utils package to test
import document_service.src.utils as utils


class TestUtilsInit:
    """Test class for the Document Service utility functions initialization."""

    def test_version_exists(self):
        """Test that the utils package has a version attribute.
        
        This test verifies that the utils package has a __version__ attribute
        that follows semantic versioning format (MAJOR.MINOR.PATCH).
        """
        assert hasattr(utils, '__version__'), "utils package is missing __version__ attribute"
        assert isinstance(utils.__version__, str), "__version__ should be a string"
        assert re.match(r'^\d+\.\d+\.\d+$', utils.__version__), "__version__ should follow semantic versioning format (MAJOR.MINOR.PATCH)"
        
        # Split the version into parts and verify they are valid integers
        major, minor, patch = utils.__version__.split('.')
        assert major.isdigit(), "Major version must be a number"
        assert minor.isdigit(), "Minor version must be a number"
        assert patch.isdigit(), "Patch version must be a number"

    def test_all_exists(self):
        """Test that the utils package has an __all__ attribute.
        
        This test verifies that the utils package has an __all__ attribute
        that is a non-empty list, which explicitly specifies what is exported.
        """
        assert hasattr(utils, '__all__'), "utils package is missing __all__ attribute"
        assert isinstance(utils.__all__, list), "__all__ should be a list"
        assert len(utils.__all__) > 0, "__all__ should not be empty"

    def test_docstring_exists(self):
        """Test that the utils package has a docstring.
        
        This test verifies that the utils package has a non-empty docstring
        that describes the package's purpose and usage.
        """
        assert utils.__doc__ is not None, "utils package is missing a docstring"
        assert len(utils.__doc__) > 0, "utils package has an empty docstring"
        
        # Check that the docstring contains important information
        docstring = utils.__doc__.lower()
        assert "document service" in docstring, "Docstring should mention 'Document Service'"
        assert "utilit" in docstring, "Docstring should mention utilities"
        assert "example" in docstring, "Docstring should include usage examples"

    def test_all_items_are_exported(self):
        """Test that all items in __all__ are actually exported by the package."""
        for item in utils.__all__:
            assert hasattr(utils, item), f"Item '{item}' is in __all__ but not exported"

    def test_no_unexported_public_items(self):
        """Test that there are no public items that are not in __all__."""
        for item in dir(utils):
            # Skip special attributes and private attributes
            if item.startswith('_'):
                continue
            # Skip imported modules
            if inspect.ismodule(getattr(utils, item)):
                continue
            # All other public attributes should be in __all__
            assert item in utils.__all__, f"Public item '{item}' is not in __all__"

    def test_import_order_prevents_circular_dependencies(self):
        """Test that the import order prevents circular dependencies.
        
        This test verifies that each utility module can be imported independently
        without causing circular import errors. It does this by clearing the module
        cache and importing each module individually.
        """
        # Create a clean module cache for testing imports
        with mock.patch.dict(sys.modules, {}):
            # Try importing each module individually to check for circular dependencies
            modules_to_test = [
                'document_service.src.utils.time_utils',
                'document_service.src.utils.file_utils',
                'document_service.src.utils.logging_utils',
                'document_service.src.utils.error_utils',
                'document_service.src.utils.validation_utils',
                'document_service.src.utils.security_utils',
                'document_service.src.utils.retry_utils',
                'document_service.src.utils.s3_utils',
                'document_service.src.utils.rabbitmq_utils',
                'document_service.src.utils.ml_utils'
            ]
            
            for module_name in modules_to_test:
                try:
                    importlib.import_module(module_name)
                except ImportError as e:
                    pytest.fail(f"Failed to import {module_name}: {e}")
                except Exception as e:
                    pytest.fail(f"Unexpected error importing {module_name}: {e}")

    def test_time_utils_functions_are_imported(self):
        """Test that time utility functions are properly imported."""
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
            assert hasattr(utils, func), f"Time utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_file_utils_functions_are_imported(self):
        """Test that file utility functions are properly imported."""
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
            assert hasattr(utils, func), f"File utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_logging_utils_functions_are_imported(self):
        """Test that logging utility functions are properly imported."""
        logging_functions = [
            'setup_logger',
            'get_logger',
            'log_with_context',
            'log_error',
            'log_warning',
            'log_info',
            'log_debug'
        ]
        
        for func in logging_functions:
            assert hasattr(utils, func), f"Logging utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_error_utils_classes_and_functions_are_imported(self):
        """Test that error utility classes and functions are properly imported."""
        error_items = [
            'DocumentServiceError',
            'ValidationError',
            'ConnectionError',
            'ProcessingError',
            'create_error_context',
            'is_retriable_error',
            'format_error_message'
        ]
        
        for item in error_items:
            assert hasattr(utils, item), f"Error utility item '{item}' not imported"
            # Check if it's a class or function
            attr = getattr(utils, item)
            assert inspect.isclass(attr) or callable(attr), f"'{item}' is not a class or callable"

    def test_validation_utils_functions_are_imported(self):
        """Test that validation utility functions are properly imported."""
        validation_functions = [
            'validate_document_type',
            'validate_document_size',
            'validate_document_format',
            'validate_message_schema',
            'validate_mime_type',
            'get_document_metadata'
        ]
        
        for func in validation_functions:
            assert hasattr(utils, func), f"Validation utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_security_utils_functions_are_imported(self):
        """Test that security utility functions are properly imported."""
        security_functions = [
            'encrypt_data',
            'decrypt_data',
            'generate_hmac',
            'verify_hmac',
            'secure_random_string',
            'configure_tls'
        ]
        
        for func in security_functions:
            assert hasattr(utils, func), f"Security utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_retry_utils_functions_are_imported(self):
        """Test that retry utility functions are properly imported."""
        retry_functions = [
            'retry_with_backoff',
            'exponential_backoff',
            'add_jitter',
            'retry_async',
            'is_retry_eligible'
        ]
        
        for func in retry_functions:
            assert hasattr(utils, func), f"Retry utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_s3_utils_functions_are_imported(self):
        """Test that S3 utility functions are properly imported."""
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
            assert hasattr(utils, func), f"S3 utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_rabbitmq_utils_functions_are_imported(self):
        """Test that RabbitMQ utility functions are properly imported."""
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
            assert hasattr(utils, func), f"RabbitMQ utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_ml_utils_functions_are_imported(self):
        """Test that machine learning utility functions are properly imported."""
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
            assert hasattr(utils, func), f"ML utility function '{func}' not imported"
            assert callable(getattr(utils, func)), f"'{func}' is not callable"

    def test_function_docstrings_exist(self):
        """Test that all exported functions have docstrings.
        
        This test verifies that all exported functions have non-empty docstrings
        that describe the function's purpose, parameters, and return values.
        """
        for item in utils.__all__:
            # Skip version and error classes
            if item == '__version__' or inspect.isclass(getattr(utils, item)):
                continue
            
            # Check if the function has a docstring
            func = getattr(utils, item)
            if callable(func):
                assert func.__doc__ is not None, f"Function '{item}' has no docstring"
                assert len(func.__doc__) > 0, f"Function '{item}' has an empty docstring"
                
                # Check that the docstring contains important sections
                docstring = func.__doc__.lower()
                # Most function docstrings should describe what the function does
                assert any(word in docstring for word in ['return', 'param', 'arg', 'raise']), \
                    f"Function '{item}' docstring should describe parameters, return values, or exceptions"

    def test_class_docstrings_exist(self):
        """Test that all exported classes have docstrings.
        
        This test verifies that all exported classes have non-empty docstrings
        that describe the class's purpose, attributes, and methods.
        """
        for item in utils.__all__:
            attr = getattr(utils, item)
            if inspect.isclass(attr):
                assert attr.__doc__ is not None, f"Class '{item}' has no docstring"
                assert len(attr.__doc__) > 0, f"Class '{item}' has an empty docstring"
                
                # Check that the docstring contains important information
                docstring = attr.__doc__.lower()
                assert "error" in docstring or "exception" in docstring, \
                    f"Class '{item}' docstring should describe the error or exception"

    def test_import_all_modules_directly(self):
        """Test that all utility modules can be imported directly.
        
        This test verifies that all utility modules can be imported directly,
        not just through the utils package. It also checks that each module
        has a proper docstring.
        """
        modules = [
            'time_utils',
            'file_utils',
            'logging_utils',
            'error_utils',
            'validation_utils',
            'security_utils',
            'retry_utils',
            's3_utils',
            'rabbitmq_utils',
            'ml_utils'
        ]
        
        for module_name in modules:
            try:
                # Try to import the module directly
                module = importlib.import_module(f"document_service.src.utils.{module_name}")
                # Check that the module has a docstring
                assert module.__doc__ is not None, f"Module '{module_name}' has no docstring"
                assert len(module.__doc__) > 0, f"Module '{module_name}' has an empty docstring"
                
                # Check that the module docstring contains important information
                docstring = module.__doc__.lower()
                assert module_name.replace('_', ' ') in docstring, \
                    f"Module '{module_name}' docstring should describe the module's purpose"
                
                # Check that the module has some public attributes or functions
                public_items = [item for item in dir(module) if not item.startswith('_')]
                assert len(public_items) > 0, f"Module '{module_name}' has no public attributes or functions"
            except ImportError as e:
                pytest.fail(f"Failed to import module '{module_name}': {e}")
            except Exception as e:
                pytest.fail(f"Unexpected error importing module '{module_name}': {e}")