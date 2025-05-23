#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the logging_utils module.

This module contains tests for the logging utilities used in the OCR service,
including structured logging, log level filtering, error logging with stack traces,
request ID tracking, and log formatting.
"""

import json
import logging
import re
import time
from unittest.mock import MagicMock, patch, call

import pytest

from src.utils.logging_utils import (
    get_logger,
    generate_request_id,
    with_request_context,
    log_with_context,
    log_debug,
    log_info,
    log_warning,
    log_error,
    log_critical,
    log_exception,
    format_exception,
    log_function_entry_exit,
    log_performance,
    log_method_calls,
    sanitize_log_data,
    log_structured_data,
    configure_logger_for_module,
    log_ocr_result,
    log_ocr_error
)


# Test basic logger functionality
def test_get_logger():
    """Test that get_logger returns a logger with the correct name."""
    with patch('logging.getLogger') as mock_get_logger:
        logger = get_logger('test_module')
        mock_get_logger.assert_called_once_with('test_module')


def test_generate_request_id():
    """Test that generate_request_id returns a valid UUID string."""
    request_id = generate_request_id()
    # Check that it's a valid UUID format
    assert re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', request_id)


# Test request context management
def test_with_request_context_decorator():
    """Test that with_request_context decorator sets and clears request context."""
    # Mock the context variables and functions
    with patch('src.utils.logging_utils.set_request_context') as mock_set_context, \
         patch('src.utils.logging_utils.clear_request_context') as mock_clear_context, \
         patch('src.utils.logging_utils.generate_request_id', return_value='test-id'):
        
        # Define a function with the decorator
        @with_request_context()
        def test_func():
            return "test result"
        
        # Call the function
        result = test_func()
        
        # Check that context was set and cleared
        mock_set_context.assert_called_once_with('test-id', None)
        mock_clear_context.assert_called_once()
        assert result == "test result"


def test_with_request_context_with_provided_ids():
    """Test with_request_context with provided request_id and user_id."""
    with patch('src.utils.logging_utils.set_request_context') as mock_set_context, \
         patch('src.utils.logging_utils.clear_request_context') as mock_clear_context:
        
        @with_request_context(request_id='custom-id', user_id='user123')
        def test_func():
            return "test result"
        
        result = test_func()
        
        mock_set_context.assert_called_once_with('custom-id', 'user123')
        mock_clear_context.assert_called_once()
        assert result == "test result"


# Test logging functions
def test_log_with_context(mock_logger):
    """Test that log_with_context adds context to log messages."""
    log_with_context(mock_logger, logging.INFO, "Test message", document_id="doc123")
    
    # Check that logger.log was called with the correct arguments
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.INFO
    assert args[1] == "Test message"
    assert kwargs.get('extra', {}).get('document_id') == "doc123"


def test_log_with_context_with_exception(mock_logger):
    """Test that log_with_context handles exceptions correctly."""
    exception = ValueError("Test error")
    log_with_context(mock_logger, logging.ERROR, "Error occurred", exc_info=exception)
    
    # Check that logger.log was called with exc_info
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.ERROR
    assert args[1] == "Error occurred"
    assert kwargs.get('exc_info') == exception


def test_log_level_functions(mock_logger):
    """Test all log level functions (debug, info, warning, error, critical)."""
    # Test debug
    log_debug(mock_logger, "Debug message", key="value")
    mock_logger.log.assert_called_with(logging.DEBUG, "Debug message", exc_info=None, stack_info=False, extra={'key': 'value'})
    mock_logger.log.reset_mock()
    
    # Test info
    log_info(mock_logger, "Info message", key="value")
    mock_logger.log.assert_called_with(logging.INFO, "Info message", exc_info=None, stack_info=False, extra={'key': 'value'})
    mock_logger.log.reset_mock()
    
    # Test warning
    log_warning(mock_logger, "Warning message", key="value")
    mock_logger.log.assert_called_with(logging.WARNING, "Warning message", exc_info=None, stack_info=False, extra={'key': 'value'})
    mock_logger.log.reset_mock()
    
    # Test error
    log_error(mock_logger, "Error message", key="value")
    mock_logger.log.assert_called_with(logging.ERROR, "Error message", exc_info=None, stack_info=False, extra={'key': 'value'})
    mock_logger.log.reset_mock()
    
    # Test critical
    log_critical(mock_logger, "Critical message", key="value")
    mock_logger.log.assert_called_with(logging.CRITICAL, "Critical message", exc_info=None, stack_info=False, extra={'key': 'value'})


def test_log_exception(mock_logger):
    """Test that log_exception logs with exception info."""
    try:
        raise ValueError("Test exception")
    except ValueError:
        log_exception(mock_logger, "Exception occurred", document_id="doc123")
    
    # Check that logger.log was called with exc_info=True
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.ERROR
    assert args[1] == "Exception occurred"
    assert kwargs.get('exc_info') is True
    assert kwargs.get('extra', {}).get('document_id') == "doc123"


def test_format_exception():
    """Test that format_exception formats exception information correctly."""
    try:
        raise ValueError("Test format exception")
    except ValueError as e:
        # Format the exception
        formatted = format_exception(e)
        
        # Check that the formatted string contains the exception information
        assert "ValueError" in formatted
        assert "Test format exception" in formatted
        assert "test_logging_utils.py" in formatted  # Should include this file in the traceback


# Test decorators and context managers
def test_log_function_entry_exit(mock_logger):
    """Test that log_function_entry_exit decorator logs function entry and exit."""
    # Define a function with the decorator
    @log_function_entry_exit(mock_logger)
    def test_func(arg1, arg2=None):
        return arg1 + (arg2 or 0)
    
    # Call the function
    result = test_func(5, 10)
    
    # Check that logger.log was called for entry and exit
    assert mock_logger.log.call_count == 2
    
    # Check entry log
    entry_call = mock_logger.log.call_args_list[0]
    assert entry_call[0][0] == logging.DEBUG
    assert "Entering test_func" in entry_call[0][1]
    assert "arg1=5" in entry_call[0][1]
    assert "arg2=10" in entry_call[0][1]
    
    # Check exit log
    exit_call = mock_logger.log.call_args_list[1]
    assert exit_call[0][0] == logging.DEBUG
    assert "Exiting test_func" in exit_call[0][1]
    assert "returned 15" in exit_call[0][1]
    assert result == 15


def test_log_function_entry_exit_with_exception(mock_logger):
    """Test that log_function_entry_exit handles exceptions correctly."""
    # Define a function with the decorator that raises an exception
    @log_function_entry_exit(mock_logger)
    def test_func_error():
        raise ValueError("Test error in function")
    
    # Call the function and expect an exception
    with pytest.raises(ValueError, match="Test error in function"):
        test_func_error()
    
    # Check that logger.log was called for entry and error
    assert mock_logger.log.call_count == 2
    
    # Check entry log
    entry_call = mock_logger.log.call_args_list[0]
    assert entry_call[0][0] == logging.DEBUG
    assert "Entering test_func_error" in entry_call[0][1]
    
    # Check error log
    error_call = mock_logger.log.call_args_list[1]
    assert error_call[0][0] == logging.ERROR
    assert "Exception in test_func_error" in error_call[0][1]
    assert "Test error in function" in error_call[0][1]


def test_log_performance_as_decorator(mock_logger):
    """Test log_performance as a decorator."""
    # Define a function with the decorator
    @log_performance(mock_logger, "test_operation")
    def test_func():
        time.sleep(0.01)  # Small delay to ensure measurable time
        return "result"
    
    # Call the function
    result = test_func()
    
    # Check that logger.log was called once for the performance log
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.DEBUG
    assert "test_operation completed in" in args[1]
    assert result == "result"


def test_log_performance_as_context_manager(mock_logger):
    """Test log_performance as a context manager."""
    # Use as a context manager
    with log_performance(mock_logger, "test_operation", level=logging.INFO):
        time.sleep(0.01)  # Small delay to ensure measurable time
    
    # Check that logger.log was called once for the performance log
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.INFO
    assert "test_operation completed in" in args[1]


def test_log_performance_with_exception(mock_logger):
    """Test log_performance when an exception occurs."""
    # Use as a context manager with an exception
    with pytest.raises(ValueError, match="Test error in operation"):
        with log_performance(mock_logger, "test_operation"):
            time.sleep(0.01)  # Small delay to ensure measurable time
            raise ValueError("Test error in operation")
    
    # Check that logger.log was called once for the performance log with error
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.ERROR
    assert "test_operation failed after" in args[1]
    assert "Test error in operation" in args[1]
    assert kwargs.get('exc_info') is not None


def test_log_method_calls(mock_logger):
    """Test that log_method_calls decorator logs all method calls for a class."""
    # Define a class with the decorator
    @log_method_calls(mock_logger)
    class TestClass:
        def method1(self):
            return "result1"
        
        def method2(self, arg):
            return f"result2: {arg}"
        
        def __private_method(self):
            return "private result"
    
    # Create an instance and call methods
    instance = TestClass()
    result1 = instance.method1()
    result2 = instance.method2("test")
    private_result = instance._TestClass__private_method()
    
    # Check that logger.log was called for each public method entry and exit
    assert mock_logger.log.call_count == 4  # 2 methods x 2 logs each (entry and exit)
    
    # Check method1 logs
    method1_entry = mock_logger.log.call_args_list[0]
    assert method1_entry[0][0] == logging.DEBUG
    assert "Entering method1" in method1_entry[0][1]
    
    method1_exit = mock_logger.log.call_args_list[1]
    assert method1_exit[0][0] == logging.DEBUG
    assert "Exiting method1" in method1_exit[0][1]
    assert "returned 'result1'" in method1_exit[0][1]
    
    # Check method2 logs
    method2_entry = mock_logger.log.call_args_list[2]
    assert method2_entry[0][0] == logging.DEBUG
    assert "Entering method2" in method2_entry[0][1]
    assert "arg='test'" in method2_entry[0][1]
    
    method2_exit = mock_logger.log.call_args_list[3]
    assert method2_exit[0][0] == logging.DEBUG
    assert "Exiting method2" in method2_exit[0][1]
    assert "returned 'result2: test'" in method2_exit[0][1]
    
    # Check results
    assert result1 == "result1"
    assert result2 == "result2: test"
    assert private_result == "private result"  # Private method should not be logged


# Test data sanitization and structured logging
def test_sanitize_log_data():
    """Test that sanitize_log_data masks sensitive information."""
    # Create test data with sensitive information
    test_data = {
        "user": "test_user",
        "password": "secret123",
        "api_key": "abcdef123456",
        "document": {
            "id": "doc123",
            "content": "test content",
            "access_token": "xyz789"
        },
        "credit_card": "4111-1111-1111-1111",
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2", "secret": "hidden"}
        ]
    }
    
    # Sanitize the data
    sanitized = sanitize_log_data(test_data)
    
    # Check that sensitive fields are masked
    assert sanitized["user"] == "test_user"  # Not sensitive
    assert sanitized["password"] == "********"  # Masked
    assert sanitized["api_key"] == "********"  # Masked
    assert sanitized["document"]["id"] == "doc123"  # Not sensitive
    assert sanitized["document"]["content"] == "test content"  # Not sensitive
    assert sanitized["document"]["access_token"] == "********"  # Masked
    assert sanitized["credit_card"] == "********"  # Masked
    assert sanitized["items"][0]["id"] == 1  # Not sensitive
    assert sanitized["items"][1]["secret"] == "********"  # Masked


def test_sanitize_log_data_with_custom_keys():
    """Test sanitize_log_data with custom sensitive keys."""
    # Create test data
    test_data = {
        "user": "test_user",
        "custom_sensitive": "secret value",
        "another_field": "not sensitive"
    }
    
    # Sanitize with custom sensitive keys
    sanitized = sanitize_log_data(test_data, sensitive_keys=["custom_sensitive"])
    
    # Check that only the custom sensitive field is masked
    assert sanitized["user"] == "test_user"  # Not in custom list
    assert sanitized["custom_sensitive"] == "********"  # In custom list
    assert sanitized["another_field"] == "not sensitive"  # Not in custom list


def test_log_structured_data(mock_logger):
    """Test that log_structured_data logs structured data correctly."""
    # Create test data
    test_data = {
        "document_id": "doc123",
        "status": "processed",
        "confidence": 0.95,
        "password": "secret123"  # Sensitive field
    }
    
    # Log structured data
    log_structured_data(mock_logger, logging.INFO, "Document processed", test_data)
    
    # Check that logger.log was called with sanitized data
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.INFO
    assert args[1] == "Document processed"
    
    # Check that data was added to extra and sensitive fields were masked
    extra_data = kwargs.get('extra', {}).get('data', {})
    assert extra_data["document_id"] == "doc123"
    assert extra_data["status"] == "processed"
    assert extra_data["confidence"] == 0.95
    assert extra_data["password"] == "********"  # Should be masked


def test_log_structured_data_without_sanitization(mock_logger):
    """Test log_structured_data without sanitization."""
    # Create test data
    test_data = {
        "document_id": "doc123",
        "password": "secret123"  # Sensitive field
    }
    
    # Log structured data without sanitization
    log_structured_data(mock_logger, logging.INFO, "Document processed", test_data, sanitize=False)
    
    # Check that logger.log was called with unsanitized data
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    # Check that data was added to extra and sensitive fields were not masked
    extra_data = kwargs.get('extra', {}).get('data', {})
    assert extra_data["document_id"] == "doc123"
    assert extra_data["password"] == "secret123"  # Should not be masked


# Test OCR-specific logging functions
def test_configure_logger_for_module():
    """Test that configure_logger_for_module returns a logger with the correct name."""
    with patch('logging.getLogger') as mock_get_logger:
        logger = configure_logger_for_module('test_module')
        mock_get_logger.assert_called_once_with('test_module')


def test_log_ocr_result(mock_logger):
    """Test that log_ocr_result logs OCR results correctly."""
    # Log OCR result
    log_ocr_result(
        mock_logger,
        document_id="doc123",
        confidence=0.95,
        extracted_text="This is a test document with some extracted text.",
        processing_time=1.25,
        document_type="invoice"
    )
    
    # Check that logger.log was called with the correct arguments
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.INFO
    assert "OCR processing completed for document doc123" == args[1]
    
    # Check that structured data was logged correctly
    extra_data = kwargs.get('extra', {}).get('data', {})
    assert extra_data["document_id"] == "doc123"
    assert extra_data["confidence"] == 0.95
    assert extra_data["processing_time"] == 1.25
    assert extra_data["document_type"] == "invoice"
    assert "extracted_text_preview" in extra_data
    assert extra_data["extracted_text_length"] > 0


def test_log_ocr_error(mock_logger):
    """Test that log_ocr_error logs OCR errors correctly."""
    # Create a test error
    error = ValueError("Failed to process document")
    
    # Log OCR error
    log_ocr_error(
        mock_logger,
        document_id="doc123",
        error=error,
        processing_time=0.75,
        document_type="invoice"
    )
    
    # Check that logger.log was called with the correct arguments
    mock_logger.log.assert_called_once()
    args, kwargs = mock_logger.log.call_args
    
    assert args[0] == logging.ERROR
    assert "OCR processing failed for document doc123: Failed to process document" == args[1]
    
    # Check that structured data was logged correctly
    extra_data = kwargs.get('extra', {}).get('data', {})
    assert extra_data["document_id"] == "doc123"
    assert extra_data["error_type"] == "ValueError"
    assert extra_data["error_message"] == "Failed to process document"
    assert extra_data["processing_time"] == 0.75
    assert extra_data["document_type"] == "invoice"
    
    # Check that exception info was included
    assert kwargs.get('exc_info') == error


# Test log level filtering based on environment
def test_log_level_filtering():
    """Test that log level filtering works based on environment."""
    # This test requires manipulating environment variables and logger configuration,
    # which is typically done in the logging_config.py module. We'll mock the relevant parts.
    
    # Test development environment (DEBUG level)
    with patch('os.environ.get', return_value="development"), \
         patch('logging.getLogger') as mock_get_logger:
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Import would trigger setup_logging, so we mock that too
        with patch('src.config.logging_config.setup_logging'):
            # Re-import to trigger environment-based configuration
            from importlib import reload
            import src.config.logging_config
            reload(src.config.logging_config)
            
            # Check that the log level is set to DEBUG for development
            assert src.config.logging_config.LOG_LEVEL == logging.DEBUG
    
    # Test production environment (INFO level)
    with patch('os.environ.get', return_value="production"), \
         patch('logging.getLogger') as mock_get_logger:
        
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Import would trigger setup_logging, so we mock that too
        with patch('src.config.logging_config.setup_logging'):
            # Re-import to trigger environment-based configuration
            from importlib import reload
            import src.config.logging_config
            reload(src.config.logging_config)
            
            # Check that the log level is set to INFO for production
            assert src.config.logging_config.LOG_LEVEL == logging.INFO


# Test request ID tracking for distributed tracing
def test_request_id_tracking():
    """Test that request ID is tracked across function calls."""
    # Mock the context variables
    with patch('src.utils.logging_utils.request_id_var') as mock_request_id_var, \
         patch('src.utils.logging_utils.user_id_var') as mock_user_id_var, \
         patch('src.utils.logging_utils.set_request_context') as mock_set_context, \
         patch('src.utils.logging_utils.clear_request_context') as mock_clear_context:
        
        # Set up the mock context variables
        mock_request_id_var.get.return_value = 'test-request-id'
        mock_user_id_var.get.return_value = 'test-user-id'
        
        # Define a function with the decorator
        @with_request_context(request_id='test-request-id', user_id='test-user-id')
        def test_func():
            # This would normally access the context variables
            return mock_request_id_var.get(), mock_user_id_var.get()
        
        # Call the function
        request_id, user_id = test_func()
        
        # Check that context was set and cleared
        mock_set_context.assert_called_once_with('test-request-id', 'test-user-id')
        mock_clear_context.assert_called_once()
        
        # Check that the context variables were accessed
        mock_request_id_var.get.assert_called()
        mock_user_id_var.get.assert_called()
        
        # Check the returned values
        assert request_id == 'test-request-id'
        assert user_id == 'test-user-id'


# Test log formatting for machine-readable output
def test_log_formatting():
    """Test that logs are formatted correctly for machine readability."""
    # This test requires the JsonFormatter from logging_config.py
    # We'll create a simple test to verify it formats logs as expected
    
    from src.config.logging_config import JsonFormatter
    
    # Create a formatter
    formatter = JsonFormatter()
    
    # Create a log record
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=123,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Add some extra attributes
    record.request_id = "test-request-id"
    record.document_id = "test-document-id"
    
    # Format the record
    formatted = formatter.format(record)
    
    # Parse the JSON
    log_data = json.loads(formatted)
    
    # Check the formatted output
    assert log_data["service"] == "ocr-service"
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["logger"] == "test_logger"
    assert log_data["path"] == "test_file.py"
    assert log_data["line"] == 123
    assert log_data["request_id"] == "test-request-id"
    assert log_data["document_id"] == "test-document-id"
    assert "timestamp" in log_data  # Should have a timestamp