#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the __init__.py module of the utils package.

This module contains tests for proper module initialization, import functionality,
version tracking, import order to prevent circular dependencies, and API surface
consistency to ensure the utility package works correctly as a whole.
"""

import sys
import importlib
import inspect
import re
from unittest.mock import patch, MagicMock

import pytest

# Import the utils package to test
import ocr_service.utils as utils


class TestPackageInitialization:
    """Tests for proper initialization of the utils package."""

    def test_package_exists(self):
        """Test that the utils package exists and can be imported."""
        assert 'ocr_service.utils' in sys.modules
        assert utils is not None

    def test_package_docstring(self):
        """Test that the utils package has a proper docstring."""
        assert utils.__doc__ is not None
        assert "OCR Service Utilities Package" in utils.__doc__
        assert "This package provides utility functions" in utils.__doc__

    def test_package_attributes(self):
        """Test that the utils package has the expected attributes."""
        assert hasattr(utils, '__version__')
        assert hasattr(utils, '__all__')


class TestVersionTracking:
    """Tests for version tracking in the utils package."""

    def test_version_format(self):
        """Test that the version follows semantic versioning format (X.Y.Z)."""
        version_pattern = r'^\d+\.\d+\.\d+$'
        assert re.match(version_pattern, utils.__version__) is not None

    def test_version_is_string(self):
        """Test that the version is a string."""
        assert isinstance(utils.__version__, str)

    def test_version_is_not_empty(self):
        """Test that the version is not empty."""
        assert utils.__version__ != ""


class TestImportFunctionality:
    """Tests for proper import functionality of the utils package."""

    def test_time_utils_imports(self):
        """Test that time utility functions are properly imported."""
        # Test a sample of time utility functions
        assert hasattr(utils, 'get_current_timestamp')
        assert hasattr(utils, 'format_datetime')
        assert hasattr(utils, 'calculate_processing_time')
        assert callable(utils.get_current_timestamp)
        assert callable(utils.format_datetime)
        assert callable(utils.calculate_processing_time)

    def test_file_utils_imports(self):
        """Test that file utility functions are properly imported."""
        # Test a sample of file utility functions
        assert hasattr(utils, 'get_mime_type')
        assert hasattr(utils, 'create_temp_file')
        assert hasattr(utils, 'get_file_size')
        assert callable(utils.get_mime_type)
        assert callable(utils.create_temp_file)
        assert callable(utils.get_file_size)

    def test_validation_utils_imports(self):
        """Test that validation utility functions are properly imported."""
        # Test a sample of validation utility functions
        assert hasattr(utils, 'validate_document_type')
        assert hasattr(utils, 'validate_message_schema')
        assert callable(utils.validate_document_type)
        assert callable(utils.validate_message_schema)

    def test_error_utils_imports(self):
        """Test that error utility functions are properly imported."""
        # Test a sample of error utility functions
        assert hasattr(utils, 'create_error')
        assert hasattr(utils, 'is_retriable_error')
        assert callable(utils.create_error)
        assert callable(utils.is_retriable_error)

    def test_logging_utils_imports(self):
        """Test that logging utility functions are properly imported."""
        # Test a sample of logging utility functions
        assert hasattr(utils, 'create_log_entry')
        assert hasattr(utils, 'log_processing_start')
        assert callable(utils.create_log_entry)
        assert callable(utils.log_processing_start)

    def test_rabbitmq_utils_imports(self):
        """Test that RabbitMQ utility functions are properly imported."""
        # Test a sample of RabbitMQ utility functions
        assert hasattr(utils, 'create_connection')
        assert hasattr(utils, 'publish_message')
        assert callable(utils.create_connection)
        assert callable(utils.publish_message)

    def test_text_utils_imports(self):
        """Test that text utility functions are properly imported."""
        # Test a sample of text utility functions
        assert hasattr(utils, 'clean_text')
        assert hasattr(utils, 'extract_key_value_pairs')
        assert callable(utils.clean_text)
        assert callable(utils.extract_key_value_pairs)

    def test_image_utils_imports(self):
        """Test that image utility functions are properly imported."""
        # Test a sample of image utility functions
        assert hasattr(utils, 'preprocess_image')
        assert hasattr(utils, 'detect_regions')
        assert callable(utils.preprocess_image)
        assert callable(utils.detect_regions)

    def test_tensorflow_utils_imports(self):
        """Test that TensorFlow utility functions are properly imported."""
        # Test a sample of TensorFlow utility functions
        assert hasattr(utils, 'load_model')
        assert hasattr(utils, 'run_inference')
        assert callable(utils.load_model)
        assert callable(utils.run_inference)

    def test_constants_imports(self):
        """Test that constants are properly imported."""
        # Test a sample of constants
        assert hasattr(utils, 'SUPPORTED_MIME_TYPES')
        assert hasattr(utils, 'FORMAT_PATTERNS')


class TestImportOrder:
    """Tests for proper import order to prevent circular dependencies."""

    @patch('importlib.import_module')
    def test_import_order(self, mock_import_module):
        """Test that imports are done in the correct order to prevent circular dependencies."""
        # Create a mock for tracking import order
        mock_modules = {}
        
        def side_effect(name, *args, **kwargs):
            mock_modules[name] = len(mock_modules) + 1
            mock = MagicMock()
            return mock
        
        mock_import_module.side_effect = side_effect
        
        # Reload the utils package to trigger imports
        importlib.reload(utils)
        
        # Check that basic utilities are imported before dependent ones
        if 'ocr_service.utils.time_utils' in mock_modules and 'ocr_service.utils.logging_utils' in mock_modules:
            assert mock_modules['ocr_service.utils.time_utils'] < mock_modules['ocr_service.utils.logging_utils']
        
        if 'ocr_service.utils.file_utils' in mock_modules and 'ocr_service.utils.image_utils' in mock_modules:
            assert mock_modules['ocr_service.utils.file_utils'] < mock_modules['ocr_service.utils.image_utils']

    def test_no_circular_imports(self):
        """Test that there are no circular imports in the utils package."""
        # This is a basic test that would fail if circular imports caused an ImportError
        try:
            importlib.reload(utils)
            assert True
        except ImportError:
            assert False, "Circular import detected in utils package"


class TestAPISurfaceConsistency:
    """Tests for API surface consistency in the utils package."""

    def test_all_list_matches_exports(self):
        """Test that the __all__ list matches the actual exported functions."""
        # Get all public attributes (not starting with _)
        public_attrs = [attr for attr in dir(utils) if not attr.startswith('_')]
        
        # Check that all items in __all__ exist as attributes
        for item in utils.__all__:
            assert item in public_attrs, f"{item} is in __all__ but not exported"

    def test_all_exports_are_in_all_list(self):
        """Test that all exported functions are in the __all__ list."""
        # Get all public callable attributes and constants (not starting with _)
        public_callables = [attr for attr in dir(utils) 
                           if not attr.startswith('_') and 
                           (callable(getattr(utils, attr)) or 
                            isinstance(getattr(utils, attr), (str, int, float, list, dict, tuple)))]
        
        # Exclude modules and classes
        excluded_types = (type, type(sys))
        public_callables = [attr for attr in public_callables 
                           if not isinstance(getattr(utils, attr), excluded_types)]
        
        # Check that all public callables are in __all__
        for item in public_callables:
            assert item in utils.__all__, f"{item} is exported but not in __all__"

    def test_function_signatures(self):
        """Test that function signatures are consistent with their documentation."""
        # Test a sample of functions
        functions_to_test = [
            'get_current_timestamp',
            'validate_document_type',
            'create_error',
            'publish_message',
            'preprocess_image',
            'load_model'
        ]
        
        for func_name in functions_to_test:
            if hasattr(utils, func_name) and callable(getattr(utils, func_name)):
                func = getattr(utils, func_name)
                # Check that the function has a docstring
                assert func.__doc__ is not None, f"{func_name} is missing a docstring"
                
                # Check that the function signature matches the docstring
                # This is a basic check that would need to be expanded for a real implementation
                signature = inspect.signature(func)
                assert str(signature) in func.__doc__ or func_name in func.__doc__, \
                    f"{func_name} signature does not match its docstring"


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])