#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the logging utilities in the Document Service.

This module contains tests for the structured logging, log level filtering,
error logging, and log formatting functions in the logging_utils module.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch, call

import pytest

from src.utils.logging_utils import (
    JsonFormatter,
    RequestIdFilter,
    ContextLogger,
    LogContext,
    configure_logging,
    get_logger,
    log_error,
    with_request_id,
    log_function_call,
    log_document_processing,
    log_classification_result,
    log_processing_time,
    log_document_extraction_result,
    log_document_processing_error,
    log_api_request,
    log_message_queue_event,
    log_model_prediction,
    log_document_storage_operation,
    sanitize_log_data,
    set_log_level,
    create_request_context,
    format_exception,
    get_environment,
    is_production,
    is_debug_enabled,
    with_context
)


# ============================================================================
# Test JsonFormatter
# ============================================================================

def test_json_formatter_basic_fields():
    """Test that JsonFormatter includes all basic fields in the formatted output."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    formatted = formatter.format(record)
    log_data = json.loads(formatted)
    
    # Check basic fields
    assert "timestamp" in log_data
    assert log_data["service"] == "document_service"
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["logger"] == "test_logger"
    assert log_data["module"] == "test_file"
    assert log_data["line"] == 42


def test_json_formatter_with_request_id():
    """Test that JsonFormatter includes request_id when available."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Add request_id to the record
    request_id = str(uuid.uuid4())
    record.request_id = request_id
    
    formatted = formatter.format(record)
    log_data = json.loads(formatted)
    
    assert log_data["request_id"] == request_id


def test_json_formatter_with_extra_context():
    """Test that JsonFormatter includes extra context when available."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Add extra context to the record
    record._extra = {
        "document_id": "doc-123",
        "document_type": "application_form",
        "processing_time_ms": 150
    }
    
    formatted = formatter.format(record)
    log_data = json.loads(formatted)
    
    assert log_data["document_id"] == "doc-123"
    assert log_data["document_type"] == "application_form"
    assert log_data["processing_time_ms"] == 150


def test_json_formatter_with_exception():
    """Test that JsonFormatter includes exception information when available."""
    formatter = JsonFormatter()
    
    try:
        # Generate an exception
        raise ValueError("Test exception")
    except ValueError as e:
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test_file.py",
            lineno=42,
            msg="Exception occurred",
            args=(),
            exc_info=(type(e), e, e.__traceback__)
        )
    
    formatted = formatter.format(record)
    log_data = json.loads(formatted)
    
    assert "exception" in log_data
    assert log_data["exception"]["type"] == "ValueError"
    assert log_data["exception"]["message"] == "Test exception"
    assert isinstance(log_data["exception"]["traceback"], list)
    assert len(log_data["exception"]["traceback"]) > 0


# ============================================================================
# Test RequestIdFilter
# ============================================================================

def test_request_id_filter_with_provided_id():
    """Test that RequestIdFilter adds the provided request_id to log records."""
    request_id = "test-request-id"
    filter_instance = RequestIdFilter(request_id)
    
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    result = filter_instance.filter(record)
    
    assert result is True  # Filter should always return True
    assert hasattr(record, "request_id")
    assert record.request_id == request_id


def test_request_id_filter_with_generated_id():
    """Test that RequestIdFilter generates a UUID when no request_id is provided."""
    filter_instance = RequestIdFilter()
    
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="test_file.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    result = filter_instance.filter(record)
    
    assert result is True  # Filter should always return True
    assert hasattr(record, "request_id")
    
    # Verify that the generated request_id is a valid UUID
    try:
        uuid.UUID(record.request_id)
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False
    
    assert is_valid_uuid


# ============================================================================
# Test ContextLogger
# ============================================================================

def test_context_logger_initialization():
    """Test that ContextLogger initializes with correct defaults."""
    logger = ContextLogger()
    
    assert logger.logger.name == "document_service"
    assert isinstance(logger.request_id, str)
    assert logger.context == {}
    
    # Test with custom name and request_id
    custom_request_id = "custom-request-id"
    custom_logger = ContextLogger("custom_logger", custom_request_id)
    
    assert custom_logger.logger.name == "custom_logger"
    assert custom_logger.request_id == custom_request_id


def test_context_logger_add_context():
    """Test that ContextLogger.add_context adds context data correctly."""
    logger = ContextLogger()
    
    # Add context data
    logger.add_context(document_id="doc-123", document_type="application_form")
    
    assert "document_id" in logger.context
    assert logger.context["document_id"] == "doc-123"
    assert "document_type" in logger.context
    assert logger.context["document_type"] == "application_form"
    
    # Add more context data
    logger.add_context(processing_time_ms=150)
    
    assert "processing_time_ms" in logger.context
    assert logger.context["processing_time_ms"] == 150


def test_context_logger_remove_context():
    """Test that ContextLogger.remove_context removes context data correctly."""
    logger = ContextLogger()
    
    # Add context data
    logger.add_context(
        document_id="doc-123",
        document_type="application_form",
        processing_time_ms=150
    )
    
    # Remove some context data
    logger.remove_context("document_type", "processing_time_ms")
    
    assert "document_id" in logger.context
    assert "document_type" not in logger.context
    assert "processing_time_ms" not in logger.context
    
    # Test removing non-existent keys (should not raise an error)
    logger.remove_context("non_existent_key")


def test_context_logger_log_methods():
    """Test that ContextLogger log methods call the underlying logger correctly."""
    with patch("logging.Logger.log") as mock_log:
        logger = ContextLogger()
        logger.add_context(document_id="doc-123")
        
        # Test debug method
        logger.debug("Debug message")
        # Test info method
        logger.info("Info message")
        # Test warning method
        logger.warning("Warning message")
        # Test warn method (alias for warning)
        logger.warn("Warn message")
        # Test error method
        logger.error("Error message")
        # Test critical method
        logger.critical("Critical message")
        
        # Verify that the underlying logger was called with the correct arguments
        assert mock_log.call_count == 6
        
        # Check that context was included in all calls
        for call_args in mock_log.call_args_list:
            args, kwargs = call_args
            assert "extra" in kwargs
            assert "_extra" in kwargs["extra"]
            assert kwargs["extra"]["_extra"]["document_id"] == "doc-123"
            assert "request_id" in kwargs["extra"]["_extra"]


def test_context_logger_exception_method():
    """Test that ContextLogger.exception includes exception info."""
    with patch("logging.Logger.log") as mock_log:
        logger = ContextLogger()
        
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            logger.exception("Exception occurred")
        
        # Verify that the underlying logger was called with exc_info=True
        assert mock_log.call_count == 1
        args, kwargs = mock_log.call_args
        assert kwargs["exc_info"] is True


# ============================================================================
# Test LogContext context manager
# ============================================================================

def test_log_context_manager():
    """Test that LogContext context manager adds and removes context correctly."""
    logger = ContextLogger()
    logger.add_context(permanent_key="permanent_value")
    
    # Use the context manager to add temporary context
    with LogContext(logger, temporary_key="temporary_value"):
        assert "permanent_key" in logger.context
        assert logger.context["permanent_key"] == "permanent_value"
        assert "temporary_key" in logger.context
        assert logger.context["temporary_key"] == "temporary_value"
    
    # After exiting the context manager, the temporary context should be removed
    assert "permanent_key" in logger.context
    assert logger.context["permanent_key"] == "permanent_value"
    assert "temporary_key" not in logger.context


def test_log_context_manager_with_existing_keys():
    """Test that LogContext context manager preserves existing values when exiting."""
    logger = ContextLogger()
    logger.add_context(key1="original_value", key2="value2")
    
    # Use the context manager to temporarily override an existing key
    with LogContext(logger, key1="temporary_value", key3="value3"):
        assert logger.context["key1"] == "temporary_value"
        assert logger.context["key2"] == "value2"
        assert logger.context["key3"] == "value3"
    
    # After exiting, the original value should be restored
    assert logger.context["key1"] == "original_value"
    assert logger.context["key2"] == "value2"
    assert "key3" not in logger.context


def test_with_context_helper():
    """Test that with_context helper function creates a LogContext instance."""
    logger = ContextLogger()
    
    # Use the with_context helper
    context_manager = with_context(logger, test_key="test_value")
    
    assert isinstance(context_manager, LogContext)
    
    # Use the context manager
    with context_manager:
        assert "test_key" in logger.context
        assert logger.context["test_key"] == "test_value"
    
    assert "test_key" not in logger.context


# ============================================================================
# Test utility functions
# ============================================================================

def test_get_logger():
    """Test that get_logger returns a ContextLogger instance."""
    # Test with default parameters
    logger = get_logger()
    assert isinstance(logger, ContextLogger)
    
    # Test with custom name
    named_logger = get_logger("custom_name")
    assert isinstance(named_logger, ContextLogger)
    assert named_logger.logger.name == "custom_name"
    
    # Test with custom request_id
    request_id = "custom-request-id"
    request_logger = get_logger(request_id=request_id)
    assert isinstance(request_logger, ContextLogger)
    assert request_logger.request_id == request_id


def test_with_request_id_decorator():
    """Test that with_request_id decorator adds request_id to the function's logger."""
    # Define a function with the decorator
    @with_request_id
    def test_function():
        # The decorator adds a logger to the function's globals
        return logger
    
    # Call the function and get the logger
    result = test_function()
    
    assert isinstance(result, ContextLogger)
    assert hasattr(result, "request_id")
    
    # Test with a provided request_id
    request_id = "custom-request-id"
    result = test_function(request_id=request_id)
    
    assert result.request_id == request_id


def test_log_function_call_decorator():
    """Test that log_function_call decorator logs function calls and returns."""
    # Mock the get_logger function
    with patch("document_service.utils.logging_utils.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Define a function with the decorator
        @log_function_call
        def test_function(arg1, arg2=None):
            return f"{arg1}-{arg2}"
        
        # Call the function
        result = test_function("value1", arg2="value2")
        
        # Verify the result
        assert result == "value1-value2"
        
        # Verify that the logger was called correctly
        assert mock_logger.debug.call_count == 2
        
        # Check the first call (function call logging)
        first_call_args = mock_logger.debug.call_args_list[0][0][0]
        assert "Calling test_function" in first_call_args
        assert "value1" in first_call_args
        assert "arg2=" in first_call_args
        assert "value2" in first_call_args
        
        # Check the second call (function return logging)
        second_call_args = mock_logger.debug.call_args_list[1][0][0]
        assert "test_function returned" in second_call_args
        assert "value1-value2" in second_call_args


def test_log_function_call_decorator_with_exception():
    """Test that log_function_call decorator logs exceptions."""
    # Mock the get_logger function
    with patch("document_service.utils.logging_utils.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Define a function with the decorator that raises an exception
        @log_function_call
        def test_function():
            raise ValueError("Test exception")
        
        # Call the function and catch the exception
        with pytest.raises(ValueError):
            test_function()
        
        # Verify that the logger was called correctly
        assert mock_logger.debug.call_count == 1  # Only the function call should be logged
        assert mock_logger.exception.call_count == 1  # The exception should be logged
        
        # Check the exception logging call
        exception_call_args = mock_logger.exception.call_args_list[0][0][0]
        assert "test_function raised exception" in exception_call_args
        
        # Verify that exc_info was set to True
        exception_call_kwargs = mock_logger.exception.call_args_list[0][1]
        assert exception_call_kwargs["exc_info"] is True


def test_log_error():
    """Test that log_error logs errors with stack traces."""
    # Mock the get_logger function
    with patch("src.utils.logging_utils.get_logger") as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call log_error without an exception
        log_error("Error message")
        
        # Verify that the logger was called correctly
        assert mock_logger.error.call_count == 1
        mock_logger.error.assert_called_with("Error message", exc_info=True)
        
        # Reset the mock
        mock_logger.reset_mock()
        
        # Call log_error with an exception
        exception = ValueError("Test exception")
        log_error("Error with exception", exc_info=exception)
        
        # Verify that the logger was called correctly
        assert mock_logger.error.call_count == 1
        mock_logger.error.assert_called_with("Error with exception", exc_info=exception)


# ============================================================================
# Test log level configuration
# ============================================================================

def test_configure_logging_default_level():
    """Test that configure_logging sets the default log level correctly."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger
        
        # Call configure_logging with default parameters
        configure_logging()
        
        # Verify that the root logger was configured correctly
        mock_root_logger.setLevel.assert_called_once()
        # Default level should be INFO
        assert mock_root_logger.setLevel.call_args[0][0] == logging.INFO


def test_configure_logging_custom_level():
    """Test that configure_logging sets a custom log level correctly."""
    with patch("logging.getLogger") as mock_get_logger:
        mock_root_logger = MagicMock()
        mock_get_logger.return_value = mock_root_logger
        
        # Call configure_logging with a custom level
        configure_logging("DEBUG")
        
        # Verify that the root logger was configured correctly
        mock_root_logger.setLevel.assert_called_once()
        # Level should be DEBUG
        assert mock_root_logger.setLevel.call_args[0][0] == logging.DEBUG


def test_set_log_level():
    """Test that set_log_level calls configure_logging with the correct level."""
    with patch("document_service.utils.logging_utils.configure_logging") as mock_configure_logging:
        # Call set_log_level
        set_log_level("DEBUG")
        
        # Verify that configure_logging was called correctly
        mock_configure_logging.assert_called_once_with("DEBUG")


def test_is_debug_enabled():
    """Test that is_debug_enabled returns the correct value."""
    with patch("document_service.utils.logging_utils.logger.isEnabledFor") as mock_is_enabled_for:
        # Test when debug is enabled
        mock_is_enabled_for.return_value = True
        assert is_debug_enabled() is True
        
        # Test when debug is disabled
        mock_is_enabled_for.return_value = False
        assert is_debug_enabled() is False
        
        # Verify that isEnabledFor was called with DEBUG level
        mock_is_enabled_for.assert_called_with(logging.DEBUG)


# ============================================================================
# Test environment functions
# ============================================================================

def test_get_environment(monkeypatch):
    """Test that get_environment returns the correct environment."""
    # Test default environment (development)
    assert get_environment() == "development"
    
    # Test with environment variable set
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert get_environment() == "production"
    
    # Test with different case
    monkeypatch.setenv("ENVIRONMENT", "STAGING")
    assert get_environment() == "staging"  # Should be lowercase


def test_is_production(monkeypatch):
    """Test that is_production returns the correct value."""
    # Test default (not production)
    assert is_production() is False
    
    # Test with production environment
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert is_production() is True
    
    # Test with different case
    monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
    assert is_production() is True  # Should be case-insensitive


# ============================================================================
# Test document-specific logging functions
# ============================================================================

def test_log_document_processing():
    """Test that log_document_processing adds document context to the logger."""
    logger = ContextLogger()
    
    # Call log_document_processing
    result = log_document_processing(logger, "doc-123", "application_form")
    
    # Verify that the context was added
    assert result is logger  # Should return the same logger
    assert "document_id" in logger.context
    assert logger.context["document_id"] == "doc-123"
    assert "document_type" in logger.context
    assert logger.context["document_type"] == "application_form"
    assert "processing_started" in logger.context
    
    # Verify that processing_started is a valid ISO 8601 timestamp
    timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
    assert re.match(timestamp_pattern, logger.context["processing_started"])


def test_log_classification_result():
    """Test that log_classification_result logs classification results correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Call log_classification_result
    log_classification_result(logger, "application_form", 0.95)
    
    # Verify that the logger was called correctly
    logger.info.assert_called_once()
    
    # Check the message
    message = logger.info.call_args[0][0]
    assert "Document classified as application_form" in message
    
    # Check the extra data
    extra = logger.info.call_args[1]["extra"]
    assert extra["classification"] == "application_form"
    assert extra["confidence"] == 0.95
    assert "classification_time" in extra


def test_log_processing_time():
    """Test that log_processing_time logs processing time correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Create start and end times
    start_time = datetime.now()
    end_time = datetime.now()
    
    # Call log_processing_time with both start and end times
    log_processing_time(logger, "document_classification", start_time, end_time)
    
    # Verify that the logger was called correctly
    logger.info.assert_called_once()
    
    # Check the message
    message = logger.info.call_args[0][0]
    assert "document_classification completed in" in message
    
    # Check the extra data
    extra = logger.info.call_args[1]["extra"]
    assert extra["operation"] == "document_classification"
    assert extra["start_time"] == start_time.isoformat()
    assert extra["end_time"] == end_time.isoformat()
    assert "duration_ms" in extra
    
    # Reset the mock
    logger.reset_mock()
    
    # Call log_processing_time with only start time (end time should be generated)
    log_processing_time(logger, "document_classification", start_time)
    
    # Verify that the logger was called correctly
    logger.info.assert_called_once()
    
    # Check the extra data
    extra = logger.info.call_args[1]["extra"]
    assert extra["operation"] == "document_classification"
    assert extra["start_time"] == start_time.isoformat()
    assert "end_time" in extra
    assert "duration_ms" in extra


def test_log_document_extraction_result():
    """Test that log_document_extraction_result logs extraction results correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Create test data
    extracted_fields = {
        "name": "John Doe",
        "address": "123 Main St",
        "phone": "555-1234"
    }
    confidence_scores = {
        "name": 0.95,
        "address": 0.85,
        "phone": 0.90
    }
    
    # Call log_document_extraction_result
    log_document_extraction_result(logger, extracted_fields, confidence_scores)
    
    # Verify that the logger was called correctly
    logger.info.assert_called_once()
    
    # Check the message
    message = logger.info.call_args[0][0]
    assert "Extracted 3 fields from document" in message
    
    # Check the extra data
    extra = logger.info.call_args[1]["extra"]
    assert set(extra["extracted_fields"]) == {"name", "address", "phone"}
    assert extra["confidence_scores"] == confidence_scores
    assert "extraction_time" in extra


def test_log_document_processing_error():
    """Test that log_document_processing_error logs errors correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Create a test exception
    error = ValueError("Failed to process document")
    
    # Call log_document_processing_error
    log_document_processing_error(logger, error, "doc-123", "classification")
    
    # Verify that the logger was called correctly
    logger.error.assert_called_once()
    
    # Check the message
    message = logger.error.call_args[0][0]
    assert "Error processing document doc-123 at stage classification" in message
    assert "Failed to process document" in message
    
    # Check the extra data
    extra = logger.error.call_args[1]["extra"]
    assert extra["document_id"] == "doc-123"
    assert extra["processing_stage"] == "classification"
    assert "error_time" in extra
    assert "error_details" in extra
    assert extra["error_details"]["exception_type"] == "ValueError"
    assert extra["error_details"]["exception_message"] == "Failed to process document"
    
    # Verify that exc_info was included
    assert logger.error.call_args[1]["exc_info"] == error


# ============================================================================
# Test API and message queue logging functions
# ============================================================================

def test_log_api_request():
    """Test that log_api_request logs API requests correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Call log_api_request with a successful status code
    log_api_request(logger, "GET", "/api/documents", 200, 150.5)
    
    # Verify that the logger was called correctly with INFO level
    logger._log.assert_called_once()
    assert logger._log.call_args[0][0] == logging.INFO
    
    # Check the message
    message = logger._log.call_args[0][1]
    assert "GET /api/documents 200" in message
    assert "150.50ms" in message
    
    # Check the extra data
    extra = logger._log.call_args[1]["extra"]
    assert extra["http_method"] == "GET"
    assert extra["path"] == "/api/documents"
    assert extra["status_code"] == 200
    assert extra["duration_ms"] == 150.5
    assert "request_time" in extra
    
    # Reset the mock
    logger.reset_mock()
    
    # Call log_api_request with an error status code
    log_api_request(logger, "POST", "/api/documents", 500, 250.75)
    
    # Verify that the logger was called correctly with ERROR level
    logger._log.assert_called_once()
    assert logger._log.call_args[0][0] == logging.ERROR


def test_log_message_queue_event():
    """Test that log_message_queue_event logs message queue events correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Call log_message_queue_event
    log_message_queue_event(logger, "mca.documents", "document.classified", "classification_result")
    
    # Verify that the logger was called correctly
    logger.info.assert_called_once()
    
    # Check the message
    message = logger.info.call_args[0][0]
    assert "Message queue event: classification_result" in message
    
    # Check the extra data
    extra = logger.info.call_args[1]["extra"]
    assert extra["exchange"] == "mca.documents"
    assert extra["routing_key"] == "document.classified"
    assert extra["message_type"] == "classification_result"
    assert "event_time" in extra


def test_log_model_prediction():
    """Test that log_model_prediction logs model predictions correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Call log_model_prediction
    log_model_prediction(logger, "document_classifier", "(1, 1024)", "application_form", 75.5)
    
    # Verify that the logger was called correctly
    logger.info.assert_called_once()
    
    # Check the message
    message = logger.info.call_args[0][0]
    assert "Model document_classifier prediction completed in 75.50ms" in message
    
    # Check the extra data
    extra = logger.info.call_args[1]["extra"]
    assert extra["model_name"] == "document_classifier"
    assert extra["input_shape"] == "(1, 1024)"
    assert extra["prediction_type"] == "str"
    assert extra["duration_ms"] == 75.5
    assert "prediction_time" in extra


def test_log_document_storage_operation():
    """Test that log_document_storage_operation logs storage operations correctly."""
    logger = MagicMock(spec=ContextLogger)
    
    # Call log_document_storage_operation with success=True
    log_document_storage_operation(
        logger, "upload", "doc-123", "s3://mca-documents-test/doc-123.pdf", True
    )
    
    # Verify that the logger was called correctly with INFO level
    logger._log.assert_called_once()
    assert logger._log.call_args[0][0] == logging.INFO
    
    # Check the message
    message = logger._log.call_args[0][1]
    assert "Document storage operation upload succeeded for document doc-123" in message
    
    # Check the extra data
    extra = logger._log.call_args[1]["extra"]
    assert extra["operation"] == "upload"
    assert extra["document_id"] == "doc-123"
    assert extra["storage_path"] == "s3://mca-documents-test/doc-123.pdf"
    assert extra["success"] is True
    assert "operation_time" in extra
    
    # Reset the mock
    logger.reset_mock()
    
    # Call log_document_storage_operation with success=False
    log_document_storage_operation(
        logger, "download", "doc-123", "s3://mca-documents-test/doc-123.pdf", False
    )
    
    # Verify that the logger was called correctly with ERROR level
    logger._log.assert_called_once()
    assert logger._log.call_args[0][0] == logging.ERROR
    
    # Check the message
    message = logger._log.call_args[0][1]
    assert "Document storage operation download failed for document doc-123" in message


# ============================================================================
# Test helper functions
# ============================================================================

def test_create_request_context():
    """Test that create_request_context creates a context dictionary correctly."""
    # Call create_request_context without a request_id
    context = create_request_context()
    
    assert "request_id" in context
    assert "timestamp" in context
    
    # Verify that the generated request_id is a valid UUID
    try:
        uuid.UUID(context["request_id"])
        is_valid_uuid = True
    except ValueError:
        is_valid_uuid = False
    
    assert is_valid_uuid
    
    # Verify that the timestamp is a valid ISO 8601 timestamp
    timestamp_pattern = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+'
    assert re.match(timestamp_pattern, context["timestamp"])
    
    # Call create_request_context with a request_id
    request_id = "custom-request-id"
    context = create_request_context(request_id)
    
    assert context["request_id"] == request_id


def test_format_exception():
    """Test that format_exception formats exceptions correctly."""
    try:
        # Generate an exception
        raise ValueError("Test exception")
    except ValueError as e:
        # Format the exception
        formatted = format_exception(e)
    
    assert "exception_type" in formatted
    assert formatted["exception_type"] == "ValueError"
    assert "exception_message" in formatted
    assert formatted["exception_message"] == "Test exception"
    assert "traceback" in formatted
    assert isinstance(formatted["traceback"], list)
    assert len(formatted["traceback"]) > 0


def test_sanitize_log_data():
    """Test that sanitize_log_data sanitizes sensitive data correctly."""
    # Create test data with sensitive fields
    data = {
        "document_id": "doc-123",
        "password": "secret",
        "api_key": "api-key-123",
        "user": {
            "name": "John Doe",
            "credit_card": "1234-5678-9012-3456",
            "ssn": "123-45-6789"
        },
        "business": {
            "name": "Acme Inc.",
            "ein": "12-3456789"
        },
        "metadata": {
            "source": "email",
            "token": "jwt-token-123"
        }
    }
    
    # Sanitize the data
    sanitized = sanitize_log_data(data)
    
    # Verify that sensitive fields were redacted
    assert sanitized["document_id"] == "doc-123"  # Non-sensitive field should be unchanged
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["user"]["name"] == "John Doe"  # Non-sensitive field should be unchanged
    assert sanitized["user"]["credit_card"] == "[REDACTED]"
    assert sanitized["user"]["ssn"] == "[REDACTED]"
    assert sanitized["business"]["name"] == "Acme Inc."  # Non-sensitive field should be unchanged
    assert sanitized["business"]["ein"] == "[REDACTED]"
    assert sanitized["metadata"]["source"] == "email"  # Non-sensitive field should be unchanged
    assert sanitized["metadata"]["token"] == "[REDACTED]"
    
    # Verify that the original data was not modified
    assert data["password"] == "secret"
    assert data["api_key"] == "api-key-123"
    assert data["user"]["credit_card"] == "1234-5678-9012-3456"
    assert data["user"]["ssn"] == "123-45-6789"
    assert data["business"]["ein"] == "12-3456789"
    assert data["metadata"]["token"] == "jwt-token-123"