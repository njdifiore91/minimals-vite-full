#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the logging utilities in the Document Service.

This module contains tests for the structured logging, log level filtering,
error logging, and log formatting functions in the Document Service.
"""

import json
import logging
import os
import re
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Import the logging utilities from the correct path
from src.utils.logging_utils import (
    JsonFormatter,
    RequestIdFilter,
    ContextLogger,
    configure_logging,
    get_logger,
    log_error,
    log_function_call,
    with_request_id,
    set_log_level,
    create_request_context,
    format_exception,
    get_environment,
    is_production,
    is_debug_enabled,
    LogContext,
    with_context,
    log_document_processing,
    log_classification_result,
    log_processing_time,
    log_document_extraction_result,
    log_document_processing_error,
    log_api_request,
    log_message_queue_event,
    log_model_prediction,
    log_document_storage_operation,
    sanitize_log_data
)


@pytest.fixture
def reset_logging():
    """Reset logging configuration before and after each test."""
    # Store original handlers
    root_logger = logging.getLogger()
    original_handlers = root_logger.handlers.copy()
    original_level = root_logger.level
    
    # Reset logging before test
    for handler in root_logger.handlers[:]:  
        root_logger.removeHandler(handler)
    
    yield
    
    # Reset logging after test
    for handler in root_logger.handlers[:]:  
        root_logger.removeHandler(handler)
    
    # Restore original handlers and level
    for handler in original_handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(original_level)


@pytest.fixture
def mock_environment():
    """Mock environment variables for testing."""
    original_env = os.environ.copy()
    
    # Set default test environment variables
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["ENVIRONMENT"] = "development"
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""
    
    def test_format_basic_record(self):
        """Test formatting a basic log record as JSON."""
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
        
        # Verify basic fields
        assert log_data["service"] == "document_service"
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test_logger"
        assert log_data["module"] == "test_file"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
        
    def test_format_with_request_id(self):
        """Test formatting a log record with request_id."""
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
        record.request_id = "test-request-id"
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["request_id"] == "test-request-id"
        
    def test_format_with_extra_context(self):
        """Test formatting a log record with extra context."""
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
        record._extra = {
            "user_id": "user123",
            "action": "login",
            "duration_ms": 150.5
        }
        
        formatted = formatter.format(record)
        log_data = json.loads(formatted)
        
        assert log_data["user_id"] == "user123"
        assert log_data["action"] == "login"
        assert log_data["duration_ms"] == 150.5
        
    def test_format_with_exception(self):
        """Test formatting a log record with exception information."""
        formatter = JsonFormatter()
        try:
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


class TestRequestIdFilter:
    """Tests for the RequestIdFilter class."""
    
    def test_filter_adds_request_id(self):
        """Test that the filter adds a request_id to log records."""
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
        
        # Verify the filter returns True (to include the record)
        assert result is True
        # Verify the request_id was added to the record
        assert hasattr(record, "request_id")
        assert record.request_id == request_id
    
    def test_filter_generates_uuid_if_not_provided(self):
        """Test that the filter generates a UUID if request_id is not provided."""
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
        filter_instance.filter(record)
        
        # Verify a UUID was generated
        assert hasattr(record, "request_id")
        # Validate UUID format using regex
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(record.request_id)


class TestConfigureLogging:
    """Tests for the configure_logging function."""
    
    def test_configure_logging_default_level(self, reset_logging, mock_environment):
        """Test configuring logging with default level from environment."""
        # Set environment variable
        os.environ["LOG_LEVEL"] = "INFO"
        
        # Configure logging
        configure_logging()
        
        # Verify root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
        
        # Verify handler was added
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.level == logging.INFO
        
        # Verify formatter
        assert isinstance(handler.formatter, JsonFormatter)
    
    def test_configure_logging_explicit_level(self, reset_logging):
        """Test configuring logging with explicitly provided level."""
        # Configure logging with explicit level
        configure_logging("DEBUG")
        
        # Verify root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG
        
        # Verify handler level
        handler = root_logger.handlers[0]
        assert handler.level == logging.DEBUG
    
    def test_configure_logging_invalid_level(self, reset_logging):
        """Test configuring logging with invalid level falls back to INFO."""
        # Configure logging with invalid level
        configure_logging("INVALID_LEVEL")
        
        # Verify root logger level defaults to INFO
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
    
    def test_configure_logging_removes_existing_handlers(self, reset_logging):
        """Test that configure_logging removes existing handlers to avoid duplicates."""
        # Add a handler to the root logger
        root_logger = logging.getLogger()
        original_handler = logging.StreamHandler()
        root_logger.addHandler(original_handler)
        
        # Verify handler was added
        assert len(root_logger.handlers) == 1
        assert root_logger.handlers[0] == original_handler
        
        # Configure logging
        configure_logging()
        
        # Verify original handler was removed and new one was added
        assert len(root_logger.handlers) == 1
        assert root_logger.handlers[0] != original_handler


class TestContextLogger:
    """Tests for the ContextLogger class."""
    
    def test_init_with_default_values(self):
        """Test initializing ContextLogger with default values."""
        logger = ContextLogger()
        
        assert logger.logger.name == "document_service"
        assert isinstance(logger.request_id, str)
        assert logger.context == {}
        
        # Validate UUID format
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(logger.request_id)
    
    def test_init_with_custom_values(self):
        """Test initializing ContextLogger with custom values."""
        logger_name = "custom_logger"
        request_id = "custom-request-id"
        
        logger = ContextLogger(logger_name, request_id)
        
        assert logger.logger.name == logger_name
        assert logger.request_id == request_id
        assert logger.context == {}
    
    def test_add_context(self):
        """Test adding context to the logger."""
        logger = ContextLogger()
        
        # Add context
        logger.add_context(user_id="user123", action="login")
        
        # Verify context was added
        assert logger.context == {"user_id": "user123", "action": "login"}
        
        # Add more context
        logger.add_context(session_id="session456")
        
        # Verify context was updated
        assert logger.context == {
            "user_id": "user123", 
            "action": "login", 
            "session_id": "session456"
        }
    
    def test_remove_context(self):
        """Test removing context from the logger."""
        logger = ContextLogger()
        
        # Add context
        logger.add_context(
            user_id="user123", 
            action="login", 
            session_id="session456"
        )
        
        # Remove some context
        logger.remove_context("action", "non_existent_key")
        
        # Verify context was updated
        assert logger.context == {
            "user_id": "user123", 
            "session_id": "session456"
        }
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_log_with_context(self, mock_log):
        """Test logging a message with context."""
        logger = ContextLogger("test_logger", "test-request-id")
        logger.add_context(user_id="user123")
        
        # Log a message
        logger.info("Test message", extra={"action": "login"})
        
        # Verify the log method was called with correct arguments
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        
        # Check log level and message
        assert args[0] == logging.INFO
        assert args[1] == "Test message"
        
        # Check extra context
        assert "extra" in kwargs
        assert "_extra" in kwargs["extra"]
        extra = kwargs["extra"]["_extra"]
        
        assert extra["user_id"] == "user123"
        assert extra["action"] == "login"
        assert extra["request_id"] == "test-request-id"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_debug_method(self, mock_log):
        """Test the debug method."""
        logger = ContextLogger()
        logger.debug("Debug message")
        
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[0] == logging.DEBUG
        assert args[1] == "Debug message"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_info_method(self, mock_log):
        """Test the info method."""
        logger = ContextLogger()
        logger.info("Info message")
        
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[0] == logging.INFO
        assert args[1] == "Info message"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_warning_method(self, mock_log):
        """Test the warning method."""
        logger = ContextLogger()
        logger.warning("Warning message")
        
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[0] == logging.WARNING
        assert args[1] == "Warning message"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_warn_method(self, mock_log):
        """Test the warn method (alias for warning)."""
        logger = ContextLogger()
        logger.warn("Warn message")
        
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[0] == logging.WARNING
        assert args[1] == "Warn message"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_error_method(self, mock_log):
        """Test the error method."""
        logger = ContextLogger()
        logger.error("Error message")
        
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[0] == logging.ERROR
        assert args[1] == "Error message"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_critical_method(self, mock_log):
        """Test the critical method."""
        logger = ContextLogger()
        logger.critical("Critical message")
        
        mock_log.assert_called_once()
        args, _ = mock_log.call_args
        assert args[0] == logging.CRITICAL
        assert args[1] == "Critical message"
    
    @patch("src.utils.logging_utils.logging.Logger.log")
    def test_exception_method(self, mock_log):
        """Test the exception method."""
        logger = ContextLogger()
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception message")
        
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.ERROR
        assert args[1] == "Exception message"
        assert kwargs["exc_info"] is True


class TestGetLogger:
    """Tests for the get_logger function."""
    
    def test_get_logger_with_name(self):
        """Test getting a logger with a specified name."""
        logger = get_logger("test_logger")
        
        assert isinstance(logger, ContextLogger)
        assert logger.logger.name == "test_logger"
    
    def test_get_logger_with_request_id(self):
        """Test getting a logger with a specified request_id."""
        request_id = "test-request-id"
        logger = get_logger("test_logger", request_id)
        
        assert isinstance(logger, ContextLogger)
        assert logger.request_id == request_id
    
    def test_get_logger_without_name(self):
        """Test getting a logger without specifying a name."""
        logger = get_logger()
        
        assert isinstance(logger, ContextLogger)
        # The name should be either the caller's module name or "document_service"
        assert logger.logger.name in [__name__, "document_service"]


class TestDecorators:
    """Tests for the decorator functions."""
    
    def test_with_request_id_decorator(self):
        """Test the with_request_id decorator."""
        @with_request_id
        def test_function():
            return logger  # logger is injected by the decorator
        
        # Call the decorated function
        result = test_function()
        
        # Verify the result is a ContextLogger with a request_id
        assert isinstance(result, ContextLogger)
        assert hasattr(result, "request_id")
        
        # Validate UUID format
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(result.request_id)
    
    def test_with_request_id_decorator_custom_id(self):
        """Test the with_request_id decorator with a custom request_id."""
        @with_request_id
        def test_function():
            return logger  # logger is injected by the decorator
        
        # Call the decorated function with a custom request_id
        result = test_function(request_id="custom-request-id")
        
        # Verify the result is a ContextLogger with the custom request_id
        assert isinstance(result, ContextLogger)
        assert result.request_id == "custom-request-id"
    
    @patch("src.utils.logging_utils.get_logger")
    def test_log_function_call_decorator(self, mock_get_logger):
        """Test the log_function_call decorator."""
        # Create a mock logger
        mock_logger = MagicMock(spec=ContextLogger)
        mock_get_logger.return_value = mock_logger
        
        # Define a decorated function
        @log_function_call
        def test_function(arg1, arg2, kwarg1="default"):
            return f"{arg1}-{arg2}-{kwarg1}"
        
        # Call the decorated function
        result = test_function("value1", "value2", kwarg1="custom")
        
        # Verify the function was called and returned the expected result
        assert result == "value1-value2-custom"
        
        # Verify the logger was called to log the function call
        mock_logger.debug.assert_any_call(
            "Calling test_function('value1', 'value2', kwarg1='custom')"
        )
        
        # Verify the logger was called to log the function return
        mock_logger.debug.assert_any_call(
            "test_function returned 'value1-value2-custom'"
        )
    
    @patch("src.utils.logging_utils.get_logger")
    def test_log_function_call_decorator_with_exception(self, mock_get_logger):
        """Test the log_function_call decorator when the function raises an exception."""
        # Create a mock logger
        mock_logger = MagicMock(spec=ContextLogger)
        mock_get_logger.return_value = mock_logger
        
        # Define a decorated function that raises an exception
        @log_function_call
        def test_function():
            raise ValueError("Test exception")
        
        # Call the decorated function and expect an exception
        with pytest.raises(ValueError, match="Test exception"):
            test_function()
        
        # Verify the logger was called to log the function call
        mock_logger.debug.assert_called_once_with("Calling test_function()")
        
        # Verify the logger was called to log the exception
        mock_logger.exception.assert_called_once()
        args, kwargs = mock_logger.exception.call_args
        assert "test_function raised exception" in args[0]
        assert kwargs["exc_info"] is True


class TestErrorLogging:
    """Tests for the error logging functions."""
    
    @patch("src.utils.logging_utils.get_logger")
    def test_log_error_with_message(self, mock_get_logger):
        """Test logging an error with just a message."""
        # Create a mock logger
        mock_logger = MagicMock(spec=ContextLogger)
        mock_get_logger.return_value = mock_logger
        
        # Log an error
        log_error("Test error message")
        
        # Verify the logger was called to log the error
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert args[0] == "Test error message"
        assert kwargs["exc_info"] is True
    
    @patch("src.utils.logging_utils.get_logger")
    def test_log_error_with_exception(self, mock_get_logger):
        """Test logging an error with an exception."""
        # Create a mock logger
        mock_logger = MagicMock(spec=ContextLogger)
        mock_get_logger.return_value = mock_logger
        
        # Create an exception
        exception = ValueError("Test exception")
        
        # Log an error with the exception
        log_error("Test error message", exc_info=exception)
        
        # Verify the logger was called to log the error
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert args[0] == "Test error message"
        assert kwargs["exc_info"] == exception
    
    @patch("src.utils.logging_utils.get_logger")
    def test_log_error_with_extra_context(self, mock_get_logger):
        """Test logging an error with extra context."""
        # Create a mock logger
        mock_logger = MagicMock(spec=ContextLogger)
        mock_get_logger.return_value = mock_logger
        
        # Log an error with extra context
        log_error(
            "Test error message", 
            document_id="doc123", 
            operation="processing"
        )
        
        # Verify the logger was called to log the error
        mock_logger.error.assert_called_once()
        args, kwargs = mock_logger.error.call_args
        assert args[0] == "Test error message"
        assert kwargs["exc_info"] is True
        assert kwargs["document_id"] == "doc123"
        assert kwargs["operation"] == "processing"


class TestEnvironmentFunctions:
    """Tests for the environment-related functions."""
    
    def test_get_environment(self, mock_environment):
        """Test getting the current environment."""
        # Set environment variable
        os.environ["ENVIRONMENT"] = "staging"
        
        # Get the environment
        env = get_environment()
        
        # Verify the environment
        assert env == "staging"
    
    def test_get_environment_default(self, mock_environment):
        """Test getting the default environment when not set."""
        # Remove environment variable if it exists
        if "ENVIRONMENT" in os.environ:
            del os.environ["ENVIRONMENT"]
        
        # Get the environment
        env = get_environment()
        
        # Verify the default environment
        assert env == "development"
    
    def test_is_production_true(self, mock_environment):
        """Test is_production returns True in production environment."""
        # Set environment variable
        os.environ["ENVIRONMENT"] = "production"
        
        # Check if production
        result = is_production()
        
        # Verify the result
        assert result is True
    
    def test_is_production_false(self, mock_environment):
        """Test is_production returns False in non-production environment."""
        # Set environment variable
        os.environ["ENVIRONMENT"] = "staging"
        
        # Check if production
        result = is_production()
        
        # Verify the result
        assert result is False
    
    @patch("src.utils.logging_utils.logger.isEnabledFor")
    def test_is_debug_enabled(self, mock_is_enabled_for):
        """Test is_debug_enabled function."""
        # Configure mock
        mock_is_enabled_for.return_value = True
        
        # Check if debug is enabled
        result = is_debug_enabled()
        
        # Verify the result
        assert result is True
        mock_is_enabled_for.assert_called_once_with(logging.DEBUG)


class TestLogContext:
    """Tests for the LogContext class and with_context function."""
    
    def test_log_context_enter_exit(self):
        """Test the LogContext context manager."""
        # Create a logger
        logger = ContextLogger()
        logger.add_context(existing_key="existing_value")
        
        # Use the context manager
        with LogContext(logger, temp_key="temp_value", existing_key="new_value") as ctx_logger:
            # Verify the context was added
            assert ctx_logger.context["temp_key"] == "temp_value"
            assert ctx_logger.context["existing_key"] == "new_value"
        
        # Verify the context was restored after exiting
        assert "temp_key" not in logger.context
        assert logger.context["existing_key"] == "existing_value"
    
    def test_with_context_function(self):
        """Test the with_context function."""
        # Create a logger
        logger = ContextLogger()
        logger.add_context(existing_key="existing_value")
        
        # Use the with_context function
        with with_context(logger, temp_key="temp_value", existing_key="new_value") as ctx_logger:
            # Verify the context was added
            assert ctx_logger.context["temp_key"] == "temp_value"
            assert ctx_logger.context["existing_key"] == "new_value"
        
        # Verify the context was restored after exiting
        assert "temp_key" not in logger.context
        assert logger.context["existing_key"] == "existing_value"
    
    def test_log_context_with_exception(self):
        """Test the LogContext context manager when an exception occurs."""
        # Create a logger
        logger = ContextLogger()
        logger.add_context(existing_key="existing_value")
        
        # Use the context manager with an exception
        try:
            with LogContext(logger, temp_key="temp_value"):
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # Verify the context was restored after exiting
        assert "temp_key" not in logger.context
        assert logger.context["existing_key"] == "existing_value"


class TestSpecializedLoggingFunctions:
    """Tests for the specialized logging functions."""
    
    def test_log_document_processing(self):
        """Test the log_document_processing function."""
        # Create a logger
        logger = ContextLogger()
        
        # Add document processing context
        result = log_document_processing(logger, "doc123", "invoice")
        
        # Verify the context was added
        assert result is logger
        assert logger.context["document_id"] == "doc123"
        assert logger.context["document_type"] == "invoice"
        assert "processing_started" in logger.context
    
    @patch.object(ContextLogger, "info")
    def test_log_classification_result(self, mock_info):
        """Test the log_classification_result function."""
        # Create a logger
        logger = ContextLogger()
        
        # Log classification result
        log_classification_result(logger, "invoice", 0.95)
        
        # Verify the logger was called
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert args[0] == "Document classified as invoice"
        assert "extra" in kwargs
        assert kwargs["extra"]["classification"] == "invoice"
        assert kwargs["extra"]["confidence"] == 0.95
        assert "classification_time" in kwargs["extra"]
    
    @patch.object(ContextLogger, "info")
    def test_log_processing_time(self, mock_info):
        """Test the log_processing_time function."""
        # Create a logger
        logger = ContextLogger()
        
        # Create start and end times
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = datetime(2023, 1, 1, 12, 0, 1)  # 1 second later
        
        # Log processing time
        log_processing_time(logger, "document_classification", start_time, end_time)
        
        # Verify the logger was called
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert "document_classification completed in" in args[0]
        assert "1000.00ms" in args[0]  # 1 second = 1000ms
        assert "extra" in kwargs
        assert kwargs["extra"]["operation"] == "document_classification"
        assert kwargs["extra"]["start_time"] == start_time.isoformat()
        assert kwargs["extra"]["end_time"] == end_time.isoformat()
        assert kwargs["extra"]["duration_ms"] == 1000.0
    
    @patch.object(ContextLogger, "info")
    def test_log_processing_time_default_end_time(self, mock_info):
        """Test the log_processing_time function with default end time."""
        # Create a logger
        logger = ContextLogger()
        
        # Create start time
        start_time = datetime.utcnow()
        
        # Log processing time with default end time
        log_processing_time(logger, "document_classification", start_time)
        
        # Verify the logger was called
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert "document_classification completed in" in args[0]
        assert "extra" in kwargs
        assert kwargs["extra"]["operation"] == "document_classification"
        assert kwargs["extra"]["start_time"] == start_time.isoformat()
        assert "end_time" in kwargs["extra"]
        assert "duration_ms" in kwargs["extra"]
    
    @patch.object(ContextLogger, "info")
    def test_log_document_extraction_result(self, mock_info):
        """Test the log_document_extraction_result function."""
        # Create a logger
        logger = ContextLogger()
        
        # Create extracted fields and confidence scores
        extracted_fields = {
            "invoice_number": "INV-123",
            "date": "2023-01-01",
            "amount": "100.00"
        }
        confidence_scores = {
            "invoice_number": 0.95,
            "date": 0.90,
            "amount": 0.85
        }
        
        # Log extraction result
        log_document_extraction_result(logger, extracted_fields, confidence_scores)
        
        # Verify the logger was called
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert "Extracted 3 fields from document" in args[0]
        assert "extra" in kwargs
        assert set(kwargs["extra"]["extracted_fields"]) == set(["invoice_number", "date", "amount"])
        assert kwargs["extra"]["confidence_scores"] == confidence_scores
        assert "extraction_time" in kwargs["extra"]
    
    @patch.object(ContextLogger, "error")
    def test_log_document_processing_error(self, mock_error):
        """Test the log_document_processing_error function."""
        # Create a logger
        logger = ContextLogger()
        
        # Create an error
        error = ValueError("Test error")
        
        # Log document processing error
        log_document_processing_error(logger, error, "doc123", "classification")
        
        # Verify the logger was called
        mock_error.assert_called_once()
        args, kwargs = mock_error.call_args
        assert "Error processing document doc123 at stage classification" in args[0]
        assert kwargs["exc_info"] == error
        assert "extra" in kwargs
        assert kwargs["extra"]["document_id"] == "doc123"
        assert kwargs["extra"]["processing_stage"] == "classification"
        assert "error_time" in kwargs["extra"]
        assert "error_details" in kwargs["extra"]
        assert kwargs["extra"]["error_details"]["exception_type"] == "ValueError"
        assert kwargs["extra"]["error_details"]["exception_message"] == "Test error"
    
    @patch.object(ContextLogger, "_log")
    def test_log_api_request_success(self, mock_log):
        """Test the log_api_request function for a successful request."""
        # Create a logger
        logger = ContextLogger()
        
        # Log API request
        log_api_request(logger, "GET", "/api/documents", 200, 150.5)
        
        # Verify the logger was called
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.INFO  # Success status code uses INFO level
        assert "GET /api/documents 200" in args[1]
        assert "150.50ms" in args[1]
        assert "extra" in kwargs
        assert kwargs["extra"]["http_method"] == "GET"
        assert kwargs["extra"]["path"] == "/api/documents"
        assert kwargs["extra"]["status_code"] == 200
        assert kwargs["extra"]["duration_ms"] == 150.5
        assert "request_time" in kwargs["extra"]
    
    @patch.object(ContextLogger, "_log")
    def test_log_api_request_error(self, mock_log):
        """Test the log_api_request function for a failed request."""
        # Create a logger
        logger = ContextLogger()
        
        # Log API request with error status
        log_api_request(logger, "POST", "/api/documents", 500, 250.5)
        
        # Verify the logger was called
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.ERROR  # Error status code uses ERROR level
        assert "POST /api/documents 500" in args[1]
        assert "250.50ms" in args[1]
    
    @patch.object(ContextLogger, "info")
    def test_log_message_queue_event(self, mock_info):
        """Test the log_message_queue_event function."""
        # Create a logger
        logger = ContextLogger()
        
        # Log message queue event
        log_message_queue_event(logger, "mca.documents", "document.classified", "classification_result")
        
        # Verify the logger was called
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert "Message queue event: classification_result" in args[0]
        assert "extra" in kwargs
        assert kwargs["extra"]["exchange"] == "mca.documents"
        assert kwargs["extra"]["routing_key"] == "document.classified"
        assert kwargs["extra"]["message_type"] == "classification_result"
        assert "event_time" in kwargs["extra"]
    
    @patch.object(ContextLogger, "info")
    def test_log_model_prediction(self, mock_info):
        """Test the log_model_prediction function."""
        # Create a logger
        logger = ContextLogger()
        
        # Log model prediction
        log_model_prediction(logger, "document_classifier", (1, 1024), ["invoice", 0.95], 75.5)
        
        # Verify the logger was called
        mock_info.assert_called_once()
        args, kwargs = mock_info.call_args
        assert "Model document_classifier prediction completed in 75.50ms" in args[0]
        assert "extra" in kwargs
        assert kwargs["extra"]["model_name"] == "document_classifier"
        assert kwargs["extra"]["input_shape"] == "(1, 1024)"
        assert kwargs["extra"]["prediction_type"] == "list"
        assert kwargs["extra"]["duration_ms"] == 75.5
        assert "prediction_time" in kwargs["extra"]
    
    @patch.object(ContextLogger, "_log")
    def test_log_document_storage_operation_success(self, mock_log):
        """Test the log_document_storage_operation function for a successful operation."""
        # Create a logger
        logger = ContextLogger()
        
        # Log document storage operation
        log_document_storage_operation(
            logger, "upload", "doc123", "s3://bucket/documents/doc123.pdf", True
        )
        
        # Verify the logger was called
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.INFO  # Success uses INFO level
        assert "Document storage operation upload succeeded for document doc123" in args[1]
        assert "extra" in kwargs
        assert kwargs["extra"]["operation"] == "upload"
        assert kwargs["extra"]["document_id"] == "doc123"
        assert kwargs["extra"]["storage_path"] == "s3://bucket/documents/doc123.pdf"
        assert kwargs["extra"]["success"] is True
        assert "operation_time" in kwargs["extra"]
    
    @patch.object(ContextLogger, "_log")
    def test_log_document_storage_operation_failure(self, mock_log):
        """Test the log_document_storage_operation function for a failed operation."""
        # Create a logger
        logger = ContextLogger()
        
        # Log document storage operation failure
        log_document_storage_operation(
            logger, "download", "doc123", "s3://bucket/documents/doc123.pdf", False
        )
        
        # Verify the logger was called
        mock_log.assert_called_once()
        args, kwargs = mock_log.call_args
        assert args[0] == logging.ERROR  # Failure uses ERROR level
        assert "Document storage operation download failed for document doc123" in args[1]


class TestSanitizeLogData:
    """Tests for the sanitize_log_data function."""
    
    def test_sanitize_log_data_basic(self):
        """Test sanitizing log data with basic sensitive fields."""
        # Create log data with sensitive fields
        data = {
            "user_id": "user123",
            "password": "secret123",
            "message": "Login attempt",
            "timestamp": "2023-01-01T12:00:00Z"
        }
        
        # Sanitize the data
        sanitized = sanitize_log_data(data)
        
        # Verify sensitive fields were redacted
        assert sanitized["user_id"] == "user123"  # Not sensitive
        assert sanitized["password"] == "[REDACTED]"  # Sensitive
        assert sanitized["message"] == "Login attempt"  # Not sensitive
        assert sanitized["timestamp"] == "2023-01-01T12:00:00Z"  # Not sensitive
    
    def test_sanitize_log_data_nested(self):
        """Test sanitizing log data with nested sensitive fields."""
        # Create log data with nested sensitive fields
        data = {
            "user": {
                "id": "user123",
                "api_key": "api_key_123",
                "profile": {
                    "name": "John Doe",
                    "ssn": "123-45-6789"
                }
            },
            "request": {
                "method": "POST",
                "path": "/api/login",
                "headers": {
                    "Authorization": "Bearer token123",
                    "Content-Type": "application/json"
                }
            }
        }
        
        # Sanitize the data
        sanitized = sanitize_log_data(data)
        
        # Verify sensitive fields were redacted
        assert sanitized["user"]["id"] == "user123"  # Not sensitive
        assert sanitized["user"]["api_key"] == "[REDACTED]"  # Sensitive
        assert sanitized["user"]["profile"]["name"] == "John Doe"  # Not sensitive
        assert sanitized["user"]["profile"]["ssn"] == "[REDACTED]"  # Sensitive
        assert sanitized["request"]["method"] == "POST"  # Not sensitive
        assert sanitized["request"]["headers"]["Authorization"] == "[REDACTED]"  # Sensitive
        assert sanitized["request"]["headers"]["Content-Type"] == "application/json"  # Not sensitive
    
    def test_sanitize_log_data_with_lists(self):
        """Test sanitizing log data with lists containing sensitive fields."""
        # Create log data with lists containing sensitive fields
        data = {
            "users": [
                {"id": "user1", "credit_card": "4111-1111-1111-1111"},
                {"id": "user2", "credit_card": "5555-5555-5555-4444"}
            ],
            "transactions": [
                {"id": "tx1", "amount": 100.00},
                {"id": "tx2", "amount": 200.00}
            ]
        }
        
        # Sanitize the data
        sanitized = sanitize_log_data(data)
        
        # Verify sensitive fields were redacted
        assert sanitized["users"][0]["id"] == "user1"  # Not sensitive
        assert sanitized["users"][0]["credit_card"] == "[REDACTED]"  # Sensitive
        assert sanitized["users"][1]["id"] == "user2"  # Not sensitive
        assert sanitized["users"][1]["credit_card"] == "[REDACTED]"  # Sensitive
        assert sanitized["transactions"][0]["id"] == "tx1"  # Not sensitive
        assert sanitized["transactions"][0]["amount"] == 100.00  # Not sensitive
    
    def test_sanitize_log_data_with_various_sensitive_fields(self):
        """Test sanitizing log data with various sensitive field names."""
        # Create log data with various sensitive field names
        data = {
            "password": "secret123",
            "token": "token123",
            "api_key": "api_key_123",
            "secret": "secret_value",
            "credential": "credential_value",
            "ssn": "123-45-6789",
            "social_security": "987-65-4321",
            "credit_card": "4111-1111-1111-1111",
            "card_number": "5555-5555-5555-4444",
            "ein": "12-3456789",
            "tax_id": "98-7654321"
        }
        
        # Sanitize the data
        sanitized = sanitize_log_data(data)
        
        # Verify all sensitive fields were redacted
        for key, value in sanitized.items():
            assert value == "[REDACTED]", f"Field '{key}' should be redacted"
    
    def test_sanitize_log_data_does_not_modify_original(self):
        """Test that sanitize_log_data does not modify the original data."""
        # Create log data with sensitive fields
        data = {
            "user_id": "user123",
            "password": "secret123"
        }
        
        # Make a copy of the original data
        original = data.copy()
        
        # Sanitize the data
        sanitized = sanitize_log_data(data)
        
        # Verify the original data was not modified
        assert data == original
        assert sanitized != original
        assert sanitized["password"] == "[REDACTED]"
        assert data["password"] == "secret123"


class TestMiscFunctions:
    """Tests for miscellaneous utility functions."""
    
    @patch("src.utils.logging_utils.configure_logging")
    def test_set_log_level(self, mock_configure_logging):
        """Test the set_log_level function."""
        # Set log level
        set_log_level("DEBUG")
        
        # Verify configure_logging was called with the correct level
        mock_configure_logging.assert_called_once_with("DEBUG")
    
    def test_create_request_context(self):
        """Test the create_request_context function with a provided request_id."""
        # Create request context with a specific request_id
        request_id = "test-request-id"
        context = create_request_context(request_id)
        
        # Verify the context
        assert context["request_id"] == request_id
        assert "timestamp" in context
    
    def test_create_request_context_generates_uuid(self):
        """Test the create_request_context function generates a UUID if not provided."""
        # Create request context without a request_id
        context = create_request_context()
        
        # Verify a UUID was generated
        assert "request_id" in context
        # Validate UUID format using regex
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(context["request_id"])
        assert "timestamp" in context
    
    def test_format_exception(self):
        """Test the format_exception function."""
        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            # Format the exception
            formatted = format_exception(e)
        
        # Verify the formatted exception
        assert formatted["exception_type"] == "ValueError"
        assert formatted["exception_message"] == "Test exception"
        assert isinstance(formatted["traceback"], list)
        assert len(formatted["traceback"]) > 0


class TestIntegration:
    """Integration tests for the logging utilities."""
    
    def test_end_to_end_logging(self, reset_logging, caplog):
        """Test end-to-end logging flow with all components."""
        # Configure logging to use a basic formatter for easier testing
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(levelname)s:%(name)s:%(message)s')
        handler.setFormatter(formatter)
        
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        root_logger.addHandler(handler)
        
        # Create a context logger
        logger = get_logger("test_integration")
        
        # Add context
        logger.add_context(user_id="user123")
        
        # Log messages at different levels
        with caplog.at_level(logging.DEBUG):
            logger.debug("Debug message")
            logger.info("Info message")
            logger.warning("Warning message")
            logger.error("Error message")
            
            # Log with additional context
            with with_context(logger, action="login"):
                logger.info("User login")
            
            # Log an exception
            try:
                raise ValueError("Test exception")
            except ValueError as e:
                logger.exception("Exception occurred")
        
        # Verify log messages were captured
        assert "Debug message" in caplog.text
        assert "Info message" in caplog.text
        assert "Warning message" in caplog.text
        assert "Error message" in caplog.text
        assert "User login" in caplog.text
        assert "Exception occurred" in caplog.text
        assert "ValueError: Test exception" in caplog.text
        
        # Verify log levels
        assert "DEBUG:test_integration:Debug message" in caplog.text
        assert "INFO:test_integration:Info message" in caplog.text
        assert "WARNING:test_integration:Warning message" in caplog.text
        assert "ERROR:test_integration:Error message" in caplog.text