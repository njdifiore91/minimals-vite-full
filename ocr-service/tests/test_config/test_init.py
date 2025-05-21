#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's config/__init__.py module.

These tests verify that the package initialization correctly imports and re-exports
all configuration components, providing a clean API surface for configuration imports
throughout the service.
"""

import pytest
from unittest.mock import patch, MagicMock
import importlib
import sys


# Test that all expected modules are imported and re-exported
def test_all_modules_imported():
    """
    Test that all expected configuration modules are imported and re-exported.
    """
    # Import the config package
    import src.config as config
    
    # Check that all expected modules are imported and re-exported
    assert hasattr(config, 'app_config'), "app_config not imported"
    assert hasattr(config, 'get_rabbitmq_config'), "rabbitmq_config functions not imported"
    assert hasattr(config, 'get_s3_client_config'), "s3_config functions not imported"
    assert hasattr(config, 'get_tensorflow_config'), "tensorflow_config functions not imported"
    assert hasattr(config, 'configure_logging'), "logging_config functions not imported"


# Test that all expected classes are imported and re-exported
def test_all_classes_imported():
    """
    Test that all expected configuration classes are imported and re-exported.
    """
    # Import the config package
    import src.config as config
    
    # Check that all expected classes are imported and re-exported
    assert hasattr(config, 'AppConfig'), "AppConfig class not imported"
    assert hasattr(config, 'Environment'), "Environment enum not imported"
    assert hasattr(config, 'LogLevel'), "LogLevel enum not imported"
    assert hasattr(config, 'ContextEnricher'), "ContextEnricher class not imported"
    assert hasattr(config, 'JsonFormatter'), "JsonFormatter class not imported"


# Test that all expected constants are imported and re-exported
def test_all_constants_imported():
    """
    Test that all expected configuration constants are imported and re-exported.
    """
    # Import the config package
    import src.config as config
    
    # Check that all expected constants are imported and re-exported
    
    # App config constants
    assert hasattr(config, 'get_config'), "get_config function not imported"
    
    # RabbitMQ config constants
    assert hasattr(config, 'CONNECTION_CONFIG'), "CONNECTION_CONFIG not imported"
    assert hasattr(config, 'EXCHANGE_CONFIG'), "EXCHANGE_CONFIG not imported"
    assert hasattr(config, 'QUEUE_CONFIG'), "QUEUE_CONFIG not imported"
    assert hasattr(config, 'RETRY_CONFIG'), "RETRY_CONFIG not imported"
    assert hasattr(config, 'DEFAULT_MESSAGE_PROPERTIES'), "DEFAULT_MESSAGE_PROPERTIES not imported"
    
    # S3 config constants
    assert hasattr(config, 'S3_CLIENT_CONFIG'), "S3_CLIENT_CONFIG not imported"
    assert hasattr(config, 'S3_BOTO_CONFIG'), "S3_BOTO_CONFIG not imported"
    assert hasattr(config, 'DEFAULT_STORAGE_OPTIONS'), "DEFAULT_STORAGE_OPTIONS not imported"
    assert hasattr(config, 'BUCKETS'), "BUCKETS not imported"
    assert hasattr(config, 'DOCUMENT_PATH_PREFIX'), "DOCUMENT_PATH_PREFIX not imported"
    assert hasattr(config, 'EXTRACTED_DATA_PATH_PREFIX'), "EXTRACTED_DATA_PATH_PREFIX not imported"
    assert hasattr(config, 'THUMBNAIL_PATH_PREFIX'), "THUMBNAIL_PATH_PREFIX not imported"
    
    # TensorFlow config constants
    assert hasattr(config, 'MODEL_ARCHITECTURES'), "MODEL_ARCHITECTURES not imported"
    assert hasattr(config, 'DOCUMENT_TYPE_MODEL_MAPPING'), "DOCUMENT_TYPE_MODEL_MAPPING not imported"
    assert hasattr(config, 'FIELD_TYPE_MODEL_MAPPING'), "FIELD_TYPE_MODEL_MAPPING not imported"
    assert hasattr(config, 'TENSORFLOW_VERSION'), "TENSORFLOW_VERSION not imported"
    assert hasattr(config, 'USE_GPU'), "USE_GPU not imported"
    assert hasattr(config, 'GPU_MEMORY_LIMIT'), "GPU_MEMORY_LIMIT not imported"
    assert hasattr(config, 'CONFIDENCE_THRESHOLD'), "CONFIDENCE_THRESHOLD not imported"
    
    # Logging config constants
    assert hasattr(config, 'LOG_LEVELS'), "LOG_LEVELS not imported"
    assert hasattr(config, 'LOG_FORMAT'), "LOG_FORMAT not imported"
    assert hasattr(config, 'DATE_FORMAT'), "DATE_FORMAT not imported"


# Test that all expected functions are imported and re-exported
def test_all_functions_imported():
    """
    Test that all expected configuration functions are imported and re-exported.
    """
    # Import the config package
    import src.config as config
    
    # Check that all expected functions are imported and re-exported
    
    # RabbitMQ config functions
    assert hasattr(config, 'get_ssl_context'), "get_ssl_context function not imported"
    assert hasattr(config, 'validate_rabbitmq_configuration'), "validate_rabbitmq_configuration function not imported"
    assert hasattr(config, 'get_connection_parameters'), "get_connection_parameters function not imported"
    assert hasattr(config, 'get_consumer_options'), "get_consumer_options function not imported"
    assert hasattr(config, 'get_publisher_options'), "get_publisher_options function not imported"
    assert hasattr(config, 'serialize_message'), "serialize_message function not imported"
    assert hasattr(config, 'deserialize_message'), "deserialize_message function not imported"
    
    # S3 config functions
    assert hasattr(config, 'get_bucket_name'), "get_bucket_name function not imported"
    assert hasattr(config, 'validate_s3_configuration'), "validate_s3_configuration function not imported"
    assert hasattr(config, 'get_storage_options'), "get_storage_options function not imported"
    
    # TensorFlow config functions
    assert hasattr(config, 'get_model_config'), "get_model_config function not imported"
    assert hasattr(config, 'get_model_path'), "get_model_path function not imported"
    assert hasattr(config, 'get_model_type_for_document'), "get_model_type_for_document function not imported"
    assert hasattr(config, 'get_model_type_for_field'), "get_model_type_for_field function not imported"
    assert hasattr(config, 'get_gpu_optimization_settings'), "get_gpu_optimization_settings function not imported"
    assert hasattr(config, 'get_model_versioning_settings'), "get_model_versioning_settings function not imported"
    assert hasattr(config, 'get_performance_monitoring_settings'), "get_performance_monitoring_settings function not imported"
    assert hasattr(config, 'log_tensorflow_config'), "log_tensorflow_config function not imported"
    
    # Logging config functions
    assert hasattr(config, 'get_logger'), "get_logger function not imported"
    assert hasattr(config, 'set_request_context'), "set_request_context function not imported"
    assert hasattr(config, 'clear_request_context'), "clear_request_context function not imported"
    assert hasattr(config, 'get_logging_config'), "get_logging_config function not imported"


# Test that package metadata is correctly defined
def test_package_metadata():
    """
    Test that package metadata is correctly defined.
    """
    # Import the config package
    import src.config as config
    
    # Check that package metadata is correctly defined
    assert hasattr(config, '__version__'), "__version__ not defined"
    assert config.__version__ == '1.0.0', "__version__ has incorrect value"
    
    assert hasattr(config, '__author__'), "__author__ not defined"
    assert config.__author__ == 'Dollar Funding OCR Team', "__author__ has incorrect value"
    
    assert hasattr(config, '__email__'), "__email__ not defined"
    assert config.__email__ == 'ocr-team@dollarfunding.com', "__email__ has incorrect value"
    
    assert hasattr(config, '__description__'), "__description__ not defined"
    assert config.__description__ == 'Configuration package for the OCR Service', "__description__ has incorrect value"


# Test that logging is configured when the package is imported
@patch('src.config.logging_config.configure_logging')
def test_logging_configured_on_import(mock_configure_logging):
    """
    Test that logging is configured when the package is imported.
    """
    # Remove the config module from sys.modules if it's already imported
    if 'src.config' in sys.modules:
        del sys.modules['src.config']
    
    # Import the config package
    importlib.import_module('src.config')
    
    # Check that configure_logging was called
    mock_configure_logging.assert_called_once()


# Test that logging information is logged when the package is imported
@patch('src.config.get_logger')
def test_logging_info_on_import(mock_get_logger):
    """
    Test that logging information is logged when the package is imported.
    """
    # Create a mock logger
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    
    # Remove the config module from sys.modules if it's already imported
    if 'src.config' in sys.modules:
        del sys.modules['src.config']
    
    # Import the config package
    importlib.import_module('src.config')
    
    # Check that get_logger was called with the correct module name
    mock_get_logger.assert_called_once_with('src.config')
    
    # Check that logger.info was called with the correct messages
    assert mock_logger.info.call_count >= 3, "logger.info not called enough times"
    
    # Check the content of the log messages
    log_messages = [call.args[0] for call in mock_logger.info.call_args_list]
    assert any('OCR Service Configuration loaded' in msg for msg in log_messages), "Configuration loaded message not logged"
    assert any('Environment:' in msg for msg in log_messages), "Environment message not logged"
    assert any('Service:' in msg for msg in log_messages), "Service message not logged"


# Test that clean imports work as expected
def test_clean_imports():
    """
    Test that clean imports work as expected throughout the service.
    """
    # Test importing app_config directly
    from src.config import app_config
    assert app_config is not None, "Failed to import app_config directly"
    
    # Test importing get_rabbitmq_config directly
    from src.config import get_rabbitmq_config
    assert get_rabbitmq_config is not None, "Failed to import get_rabbitmq_config directly"
    
    # Test importing get_s3_client_config directly
    from src.config import get_s3_client_config
    assert get_s3_client_config is not None, "Failed to import get_s3_client_config directly"
    
    # Test importing get_tensorflow_config directly
    from src.config import get_tensorflow_config
    assert get_tensorflow_config is not None, "Failed to import get_tensorflow_config directly"
    
    # Test importing configure_logging directly
    from src.config import configure_logging
    assert configure_logging is not None, "Failed to import configure_logging directly"
    
    # Test importing get_logger directly
    from src.config import get_logger
    assert get_logger is not None, "Failed to import get_logger directly"


# Test that package structure is intact
def test_package_structure():
    """
    Test that package structure is intact.
    """
    # Import the config package
    import src.config as config
    
    # Check that the package has the expected structure
    assert hasattr(config, 'app_config'), "app_config module not found"
    assert hasattr(config, 'get_rabbitmq_config'), "rabbitmq_config module not properly imported"
    assert hasattr(config, 'get_s3_client_config'), "s3_config module not properly imported"
    assert hasattr(config, 'get_tensorflow_config'), "tensorflow_config module not properly imported"
    assert hasattr(config, 'configure_logging'), "logging_config module not properly imported"
    
    # Check that the package doesn't have unexpected attributes
    assert not hasattr(config, '_private_function'), "Package has unexpected private attribute"
    assert not hasattr(config, 'internal_function'), "Package has unexpected internal attribute"


# Test that the package can be imported without errors
def test_package_import():
    """
    Test that the package can be imported without errors.
    """
    try:
        import src.config
    except ImportError as e:
        pytest.fail(f"Failed to import config package: {e}")
    except Exception as e:
        pytest.fail(f"Error importing config package: {e}")