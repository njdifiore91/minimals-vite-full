#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's config/__init__.py module.

These tests verify that the package initialization correctly imports and re-exports
all configuration components, providing a clean API surface for configuration imports
throughout the service.
"""

import importlib
import inspect
import pytest
from types import ModuleType
from typing import List, Dict, Any, Callable

# Import the module under test
import src.config as config


class TestConfigInit:
    """Test suite for the config/__init__.py module."""

    def test_module_imports(self):
        """Test that all expected configuration modules are imported."""
        # Check that the module imports all expected submodules
        assert hasattr(config, 'app_config'), "app_config module not imported"
        assert hasattr(config, 'rabbitmq_config'), "rabbitmq_config module not imported"
        assert hasattr(config, 's3_config'), "s3_config module not imported"
        assert hasattr(config, 'tensorflow_config'), "tensorflow_config module not imported"
        assert hasattr(config, 'logging_config'), "logging_config module not imported"

    def test_app_config_exports(self):
        """Test that app_config exports are correctly re-exported."""
        # Check that app_config is correctly re-exported
        assert hasattr(config, 'app_config'), "app_config not exported"
        
        # Check that app_config is the expected object
        from src.config.app_config import app_config as original_app_config
        assert config.app_config is original_app_config, "app_config is not the original object"

    def test_rabbitmq_config_exports(self):
        """Test that rabbitmq_config exports are correctly re-exported."""
        # Check that all expected rabbitmq_config functions are re-exported
        expected_rabbitmq_exports = [
            'get_rabbitmq_config',
            'get_rabbitmq_connection_parameters',
            'get_rabbitmq_exchange_config',
            'get_rabbitmq_queue_config',
            'get_rabbitmq_consumer_config',
            'get_rabbitmq_publisher_config',
            'get_rabbitmq_retry_config',
            'get_message_serializer',
            'get_message_deserializer',
            'create_ocr_result_message'
        ]
        
        for export_name in expected_rabbitmq_exports:
            assert hasattr(config, export_name), f"{export_name} not exported"
            
            # Check that the exported function is the original function
            original_module = importlib.import_module('src.config.rabbitmq_config')
            original_func = getattr(original_module, export_name)
            exported_func = getattr(config, export_name)
            
            assert exported_func is original_func, f"{export_name} is not the original function"

    def test_s3_config_exports(self):
        """Test that s3_config exports are correctly re-exported."""
        # Check that all expected s3_config functions and constants are re-exported
        expected_s3_exports = [
            'get_bucket_name',
            'get_s3_client_config',
            'get_storage_options',
            'validate_s3_configuration',
            'DOCUMENT_BUCKET',
            'EXTRACTED_DATA_BUCKET',
            'DEFAULT_STORAGE_OPTIONS'
        ]
        
        for export_name in expected_s3_exports:
            assert hasattr(config, export_name), f"{export_name} not exported"
            
            # Check that the exported item is the original item
            original_module = importlib.import_module('src.config.s3_config')
            original_item = getattr(original_module, export_name)
            exported_item = getattr(config, export_name)
            
            assert exported_item is original_item, f"{export_name} is not the original item"

    def test_tensorflow_config_exports(self):
        """Test that tensorflow_config exports are correctly re-exported."""
        # Check that all expected tensorflow_config functions and constants are re-exported
        expected_tf_exports = [
            'get_session_config',
            'get_model_config',
            'get_confidence_threshold',
            'initialize_tensorflow',
            'GPU_CONFIG',
            'MODEL_PATHS',
            'MODEL_HYPERPARAMS',
            'CONFIDENCE_THRESHOLDS',
            'MODEL_ARCHITECTURES',
            'TF_OPTIMIZATION'
        ]
        
        for export_name in expected_tf_exports:
            assert hasattr(config, export_name), f"{export_name} not exported"
            
            # Check that the exported item is the original item
            original_module = importlib.import_module('src.config.tensorflow_config')
            original_item = getattr(original_module, export_name)
            exported_item = getattr(config, export_name)
            
            assert exported_item is original_item, f"{export_name} is not the original item"

    def test_logging_config_exports(self):
        """Test that logging_config exports are correctly re-exported."""
        # Check that all expected logging_config functions and constants are re-exported
        expected_logging_exports = [
            'setup_logging',
            'get_logger',
            'LogContext',
            'add_context_to_record',
            'SERVICE_NAME',
            'ENVIRONMENT',
            'LOG_LEVEL'
        ]
        
        for export_name in expected_logging_exports:
            assert hasattr(config, export_name), f"{export_name} not exported"
            
            # Check that the exported item is the original item
            original_module = importlib.import_module('src.config.logging_config')
            original_item = getattr(original_module, export_name)
            exported_item = getattr(config, export_name)
            
            assert exported_item is original_item, f"{export_name} is not the original item"

    def test_all_variable(self):
        """Test that __all__ contains all expected exports."""
        # Check that __all__ is defined
        assert hasattr(config, '__all__'), "__all__ not defined"
        
        # Check that __all__ is a list of strings
        assert isinstance(config.__all__, list), "__all__ is not a list"
        assert all(isinstance(item, str) for item in config.__all__), "__all__ contains non-string items"
        
        # Check that __all__ contains all expected exports
        expected_exports = [
            # Application configuration
            'app_config',
            
            # RabbitMQ configuration
            'get_rabbitmq_config',
            'get_rabbitmq_connection_parameters',
            'get_rabbitmq_exchange_config',
            'get_rabbitmq_queue_config',
            'get_rabbitmq_consumer_config',
            'get_rabbitmq_publisher_config',
            'get_rabbitmq_retry_config',
            'get_message_serializer',
            'get_message_deserializer',
            'create_ocr_result_message',
            
            # S3 configuration
            'get_bucket_name',
            'get_s3_client_config',
            'get_storage_options',
            'validate_s3_configuration',
            'DOCUMENT_BUCKET',
            'EXTRACTED_DATA_BUCKET',
            'DEFAULT_STORAGE_OPTIONS',
            
            # TensorFlow configuration
            'get_session_config',
            'get_model_config',
            'get_confidence_threshold',
            'initialize_tensorflow',
            'GPU_CONFIG',
            'MODEL_PATHS',
            'MODEL_HYPERPARAMS',
            'CONFIDENCE_THRESHOLDS',
            'MODEL_ARCHITECTURES',
            'TF_OPTIMIZATION',
            
            # Logging configuration
            'setup_logging',
            'get_logger',
            'LogContext',
            'add_context_to_record',
            'SERVICE_NAME',
            'ENVIRONMENT',
            'LOG_LEVEL'
        ]
        
        for export_name in expected_exports:
            assert export_name in config.__all__, f"{export_name} not in __all__"
        
        # Check that __all__ doesn't contain unexpected exports
        for export_name in config.__all__:
            assert export_name in expected_exports, f"{export_name} in __all__ but not expected"

    def test_import_from_config(self):
        """Test that imports from config work as expected."""
        # Test importing app_config
        from src.config import app_config
        assert app_config is not None, "Failed to import app_config"
        
        # Test importing RabbitMQ functions
        from src.config import get_rabbitmq_config, get_message_serializer
        assert callable(get_rabbitmq_config), "get_rabbitmq_config is not callable"
        assert callable(get_message_serializer), "get_message_serializer is not callable"
        
        # Test importing S3 functions
        from src.config import get_bucket_name, get_s3_client_config
        assert callable(get_bucket_name), "get_bucket_name is not callable"
        assert callable(get_s3_client_config), "get_s3_client_config is not callable"
        
        # Test importing TensorFlow functions
        from src.config import get_model_config, initialize_tensorflow
        assert callable(get_model_config), "get_model_config is not callable"
        assert callable(initialize_tensorflow), "initialize_tensorflow is not callable"
        
        # Test importing logging functions
        from src.config import get_logger, setup_logging
        assert callable(get_logger), "get_logger is not callable"
        assert callable(setup_logging), "setup_logging is not callable"

    def test_module_docstring(self):
        """Test that the module has a proper docstring."""
        # Check that the module has a docstring
        assert config.__doc__ is not None, "Module does not have a docstring"
        
        # Check that the docstring contains expected information
        docstring = config.__doc__.lower()
        assert "ocr service" in docstring, "Docstring does not mention OCR Service"
        assert "configuration" in docstring, "Docstring does not mention configuration"
        assert "example" in docstring, "Docstring does not include example usage"

    def test_example_usage_in_docstring(self):
        """Test that the example usage in the docstring is valid."""
        # Extract example code from docstring
        docstring = config.__doc__
        example_start = docstring.find("Example usage:")
        assert example_start != -1, "Docstring does not contain 'Example usage:'"
        
        example_code = docstring[example_start:].split('\n\n')[0]
        example_lines = [line.strip() for line in example_code.split('\n')[1:] if line.strip()]
        
        # Check that the example code mentions key imports and functions
        example_text = '\n'.join(example_lines)
        assert "from config import app_config" in example_text, "Example does not show importing app_config"
        assert "service_name = app_config.SERVICE.name" in example_text, "Example does not show using app_config"
        assert "model_config = get_model_config" in example_text, "Example does not show using get_model_config"
        assert "bucket_name = get_bucket_name" in example_text, "Example does not show using get_bucket_name"
        assert "rabbitmq_config = get_rabbitmq_config" in example_text, "Example does not show using get_rabbitmq_config"
        assert "logger = get_logger" in example_text, "Example does not show using get_logger"

    def test_no_private_exports(self):
        """Test that no private functions or variables are exported."""
        # Check that no exported names start with an underscore
        for name in dir(config):
            if not name.startswith('_'):  # Skip built-in attributes
                assert not getattr(config, name).__name__.startswith('_') if callable(getattr(config, name)) else True, \
                    f"Private function {getattr(config, name).__name__} is exported as {name}"

    def test_function_signatures_preserved(self):
        """Test that function signatures are preserved when re-exported."""
        # Test a sample of functions to ensure signatures are preserved
        functions_to_test = [
            'get_rabbitmq_config',
            'get_s3_client_config',
            'get_model_config',
            'get_logger'
        ]
        
        for func_name in functions_to_test:
            # Get the original function
            module_name = next(mod_name for mod_name in ['rabbitmq_config', 's3_config', 'tensorflow_config', 'logging_config'] 
                              if hasattr(importlib.import_module(f'src.config.{mod_name}'), func_name))
            original_module = importlib.import_module(f'src.config.{module_name}')
            original_func = getattr(original_module, func_name)
            
            # Get the exported function
            exported_func = getattr(config, func_name)
            
            # Check that the signatures match
            original_sig = inspect.signature(original_func)
            exported_sig = inspect.signature(exported_func)
            
            assert str(original_sig) == str(exported_sig), \
                f"Signature mismatch for {func_name}: original {original_sig}, exported {exported_sig}"


class TestConfigImportPaths:
    """Test suite for config import paths."""

    def test_direct_import(self):
        """Test that direct imports from config work."""
        # Test direct import
        import src.config
        assert isinstance(src.config, ModuleType), "Failed to import src.config"

    def test_from_import(self):
        """Test that from imports from config work."""
        # Test from import for a sample of exports
        from src.config import app_config, get_rabbitmq_config, get_bucket_name, get_model_config, get_logger
        
        assert app_config is not None, "Failed to import app_config"
        assert callable(get_rabbitmq_config), "get_rabbitmq_config is not callable"
        assert callable(get_bucket_name), "get_bucket_name is not callable"
        assert callable(get_model_config), "get_model_config is not callable"
        assert callable(get_logger), "get_logger is not callable"

    def test_import_star(self):
        """Test that 'from config import *' works as expected."""
        # Create a new namespace
        namespace = {}
        
        # Execute 'from src.config import *' in the namespace
        exec('from src.config import *', namespace)
        
        # Check that all items in __all__ are in the namespace
        for export_name in config.__all__:
            assert export_name in namespace, f"{export_name} not imported with 'from config import *'"

    def test_submodule_imports(self):
        """Test that submodule imports work."""
        # Test importing submodules
        import src.config.app_config
        import src.config.rabbitmq_config
        import src.config.s3_config
        import src.config.tensorflow_config
        import src.config.logging_config
        
        assert isinstance(src.config.app_config, ModuleType), "Failed to import src.config.app_config"
        assert isinstance(src.config.rabbitmq_config, ModuleType), "Failed to import src.config.rabbitmq_config"
        assert isinstance(src.config.s3_config, ModuleType), "Failed to import src.config.s3_config"
        assert isinstance(src.config.tensorflow_config, ModuleType), "Failed to import src.config.tensorflow_config"
        assert isinstance(src.config.logging_config, ModuleType), "Failed to import src.config.logging_config"


class TestConfigPackageStructure:
    """Test suite for config package structure."""

    def test_package_is_importable(self):
        """Test that the config package is importable."""
        # Test importing the package
        import src.config
        assert isinstance(src.config, ModuleType), "Failed to import src.config"

    def test_submodules_are_importable(self):
        """Test that all submodules are importable."""
        # Test importing all submodules
        submodules = ['app_config', 'rabbitmq_config', 's3_config', 'tensorflow_config', 'logging_config']
        
        for submodule in submodules:
            module = importlib.import_module(f'src.config.{submodule}')
            assert isinstance(module, ModuleType), f"Failed to import src.config.{submodule}"

    def test_package_has_init(self):
        """Test that the config package has an __init__.py file."""
        # Check that the package has an __init__.py file
        import src.config
        assert hasattr(src.config, '__file__'), "src.config does not have __file__ attribute"
        assert '__init__.py' in src.config.__file__, "src.config.__file__ does not point to __init__.py"

    def test_package_version(self):
        """Test that the package has a version."""
        # Check that the package has a version
        import src.config
        assert hasattr(src.config, '__version__') or hasattr(src.config.app_config, 'VERSION'), \
            "Neither src.config nor src.config.app_config has a version attribute"