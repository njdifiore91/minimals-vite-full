#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the logging_utils.py module.

This module contains comprehensive tests for the logging utilities used in the OCR Service,
including structured logging, log level filtering, error logging with stack traces,
request ID tracking for distributed tracing, and log formatting for machine-readable output.

The tests cover the following key requirements from the technical specification:
1. Comprehensive logging with specified log levels (ERROR, WARN, INFO, DEBUG)
2. Logs must include timestamp, service name, and context information
3. Service must support error tracking and troubleshooting
4. Request ID tracking for distributed tracing
5. Machine-readable log formatting for automated log analysis

The tests are organized into the following classes:
- TestJsonFormatter: Tests for the JSON log formatter
- TestContextAdapter: Tests for the context adapter that adds context to logs
- TestRequestIdManagement: Tests for request ID management functions
- TestLoggerConfiguration: Tests for logger configuration functions
- TestLoggingUtilityFunctions: Tests for utility functions like log_exception
- TestLoggingDecorators: Tests for logging decorators
- TestLoggingIntegration: Integration tests for the logging system
- TestEnvironmentSpecificLogging: Tests for environment-specific configurations
- TestUseCasesAndEdgeCases: Tests for specific use cases and edge cases
- TestTechnicalSpecificationRequirements: Tests for requirements from the spec
"""

import json
import logging
import os
import pytest
import re
import sys
from unittest.mock import MagicMock, patch
from contextlib import contextmanager
from typing import Dict, List, Any, Generator

# Import the module to test
try:
    # Try the package import first
    from ocr_service.src.utils.logging_utils import (
        JsonFormatter,
        ContextAdapter,
        get_request_id,
        set_request_id,
        clear_request_id,
        request_context,
        configure_logger,
        get_logger,
        log_exception,
        log_with_context,
        get_environment_log_level,
        setup_root_logger,
        log_function_call,
        log_execution_time,
        format_stack_trace,
        get_current_stack_trace,
        log_critical_error,
        LOG_LEVEL_MAP
    )
except ImportError:
    # Fall back to relative import
    try:
        from src.utils.logging_utils import (
            JsonFormatter,
            ContextAdapter,
            get_request_id,
            set_request_id,
            clear_request_id,
            request_context,
            configure_logger,
            get_logger,
            log_exception,
            log_with_context,
            get_environment_log_level,
            setup_root_logger,
            log_function_call,
            log_execution_time,
            format_stack_trace,
            get_current_stack_trace,
            log_critical_error,
            LOG_LEVEL_MAP
        )
    except ImportError:
        # Last resort, try a direct import
        import sys
        import os
        sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/utils')))
        from logging_utils import (
            JsonFormatter,
            ContextAdapter,
            get_request_id,
            set_request_id,
            clear_request_id,
            request_context,
            configure_logger,
            get_logger,
            log_exception,
            log_with_context,
            get_environment_log_level,
            setup_root_logger,
            log_function_call,
            log_execution_time,
            format_stack_trace,
            get_current_stack_trace,
            log_critical_error,
            LOG_LEVEL_MAP
        )


class TestJsonFormatter:
    """Tests for the JsonFormatter class."""

    def test_format_basic_log_record(self):
        """Test that the formatter correctly formats a basic log record as JSON."""
        # Create a formatter
        formatter = JsonFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_data = json.loads(formatted)

        # Check the basic fields
        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["logger"] == "test_logger"
        assert log_data["module"] == "test_file"
        assert log_data["line"] == 42
        assert "timestamp" in log_data
        assert "service" in log_data
        assert log_data["service"] == "ocr-service"

    def test_format_with_extra_fields(self):
        """Test that the formatter includes extra fields in the output."""
        # Create a formatter with extra fields
        formatter = JsonFormatter(environment="test", version="1.0.0")

        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Add extra fields to the record
        record.extra = {
            "request_id": "req-123456",
            "document_id": "doc-789012"
        }

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_data = json.loads(formatted)

        # Check the extra fields
        assert log_data["environment"] == "test"
        assert log_data["version"] == "1.0.0"
        assert log_data["request_id"] == "req-123456"
        assert log_data["document_id"] == "doc-789012"

    def test_format_with_exception_info(self):
        """Test that the formatter correctly includes exception information."""
        # Create a formatter
        formatter = JsonFormatter()

        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        # Create a log record with exception info
        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test_file.py",
            lineno=42,
            msg="Exception occurred",
            args=(),
            exc_info=exc_info
        )

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_data = json.loads(formatted)

        # Check the exception info
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"
        assert "traceback" in log_data["exception"]

    def test_format_with_stack_info(self):
        """Test that the formatter correctly includes stack information."""
        # Create a formatter
        formatter = JsonFormatter()

        # Create a log record with stack info
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Stack trace",
            args=(),
            exc_info=None
        )
        record.stack_info = "  File \"test_file.py\", line 42, in test_function\n    some_code()\n"

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_data = json.loads(formatted)

        # Check the stack info
        assert "stack_info" in log_data
        assert "test_file.py" in log_data["stack_info"]

    def test_format_with_request_id(self, monkeypatch):
        """Test that the formatter includes the request ID if available."""
        # Mock the get_request_id function
        monkeypatch.setattr("ocr_service.src.utils.logging_utils.get_request_id", lambda: "req-123456")
        # Also patch the fallback import path
        monkeypatch.setattr("src.utils.logging_utils.get_request_id", lambda: "req-123456", raising=False)
        # Also patch the direct import
        monkeypatch.setattr("logging_utils.get_request_id", lambda: "req-123456", raising=False)

        # Create a formatter
        formatter = JsonFormatter()

        # Create a log record
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Format the record
        formatted = formatter.format(record)

        # Parse the JSON
        log_data = json.loads(formatted)

        # Check the request ID
        assert log_data["request_id"] == "req-123456"


class TestContextAdapter:
    """Tests for the ContextAdapter class."""

    def test_process_adds_context(self):
        """Test that the adapter adds context information to log records."""
        # Create a mock logger
        logger = MagicMock(spec=logging.Logger)

        # Create an adapter with context
        adapter = ContextAdapter(logger, {"service": "ocr-service", "component": "test"})

        # Process a message
        msg, kwargs = adapter.process("Test message", {})

        # Check that the context was added
        assert "extra" in kwargs
        assert kwargs["extra"]["service"] == "ocr-service"
        assert kwargs["extra"]["component"] == "test"

    def test_process_preserves_existing_extra(self):
        """Test that the adapter preserves existing extra information."""
        # Create a mock logger
        logger = MagicMock(spec=logging.Logger)

        # Create an adapter with context
        adapter = ContextAdapter(logger, {"service": "ocr-service"})

        # Process a message with existing extra
        msg, kwargs = adapter.process("Test message", {"extra": {"component": "test"}})

        # Check that both contexts were preserved
        assert "extra" in kwargs
        assert kwargs["extra"]["service"] == "ocr-service"
        assert kwargs["extra"]["component"] == "test"

    def test_process_adds_request_id(self, monkeypatch):
        """Test that the adapter adds the request ID if available."""
        # Mock the get_request_id function
        monkeypatch.setattr("ocr_service.src.utils.logging_utils.get_request_id", lambda: "req-123456")
        # Also patch the fallback import path
        monkeypatch.setattr("src.utils.logging_utils.get_request_id", lambda: "req-123456", raising=False)
        # Also patch the direct import
        monkeypatch.setattr("logging_utils.get_request_id", lambda: "req-123456", raising=False)

        # Create a mock logger
        logger = MagicMock(spec=logging.Logger)

        # Create an adapter
        adapter = ContextAdapter(logger, {})

        # Process a message
        msg, kwargs = adapter.process("Test message", {})

        # Check that the request ID was added
        assert "extra" in kwargs
        assert kwargs["extra"]["request_id"] == "req-123456"

    def test_log_methods_pass_through(self):
        """Test that log methods pass through to the underlying logger."""
        # Create a mock logger
        logger = MagicMock(spec=logging.Logger)

        # Create an adapter
        adapter = ContextAdapter(logger, {"service": "ocr-service"})

        # Call various log methods
        adapter.debug("Debug message")
        adapter.info("Info message")
        adapter.warning("Warning message")
        adapter.error("Error message")
        adapter.critical("Critical message")

        # Check that the logger methods were called
        logger.debug.assert_called_once()
        logger.info.assert_called_once()
        logger.warning.assert_called_once()
        logger.error.assert_called_once()
        logger.critical.assert_called_once()


class TestRequestIdManagement:
    """Tests for request ID management functions."""

    def test_get_request_id_returns_none_when_not_set(self):
        """Test that get_request_id returns None when no request ID is set."""
        # Clear any existing request ID
        clear_request_id()

        # Check that get_request_id returns None
        assert get_request_id() is None

    def test_set_request_id_with_explicit_value(self):
        """Test setting an explicit request ID."""
        # Set a specific request ID
        request_id = "req-123456"
        result = set_request_id(request_id)

        # Check that the function returned the same ID
        assert result == request_id

        # Check that get_request_id returns the same ID
        assert get_request_id() == request_id

        # Clean up
        clear_request_id()

    def test_set_request_id_generates_uuid_when_none(self):
        """Test that set_request_id generates a UUID when no ID is provided."""
        # Set a request ID with None
        result = set_request_id(None)

        # Check that a UUID was generated (UUID format validation)
        uuid_pattern = re.compile(
            r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        )
        assert uuid_pattern.match(result)

        # Check that get_request_id returns the same ID
        assert get_request_id() == result

        # Clean up
        clear_request_id()

    def test_clear_request_id(self):
        """Test that clear_request_id removes the request ID."""
        # Set a request ID
        set_request_id("req-123456")

        # Clear it
        clear_request_id()

        # Check that it's gone
        assert get_request_id() is None

    def test_request_context_manager_sets_and_clears_id(self):
        """Test that the request_context context manager sets and clears the request ID."""
        # Clear any existing request ID
        clear_request_id()

        # Use the context manager with an explicit ID
        with request_context("req-123456"):
            assert get_request_id() == "req-123456"

        # Check that the ID is cleared after the context
        assert get_request_id() is None

    def test_request_context_manager_generates_id_when_none(self):
        """Test that the request_context generates a UUID when no ID is provided."""
        # Clear any existing request ID
        clear_request_id()

        # Use the context manager without an ID
        with request_context():
            request_id = get_request_id()
            assert request_id is not None
            # Validate UUID format
            uuid_pattern = re.compile(
                r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            )
            assert uuid_pattern.match(request_id)

        # Check that the ID is cleared after the context
        assert get_request_id() is None

    def test_request_context_manager_restores_previous_id(self):
        """Test that the request_context restores the previous ID after nested contexts."""
        # Set an initial request ID
        set_request_id("req-outer")

        # Use a nested context
        with request_context("req-inner"):
            assert get_request_id() == "req-inner"

        # Check that the original ID is restored
        assert get_request_id() == "req-outer"

        # Clean up
        clear_request_id()


class TestLoggerConfiguration:
    """Tests for logger configuration functions."""

    def test_configure_logger_basic(self):
        """Test basic logger configuration."""
        # Configure a logger
        logger = configure_logger("test_logger", level="INFO")

        # Check that it's a ContextAdapter
        assert isinstance(logger, ContextAdapter)

        # Check the underlying logger
        assert logger.logger.name == "test_logger"
        assert logger.logger.level == logging.INFO

        # Check that it has at least one handler
        assert len(logger.logger.handlers) > 0

    def test_configure_logger_with_json_format(self):
        """Test logger configuration with JSON formatting."""
        # Configure a logger with JSON formatting
        logger = configure_logger("test_json_logger", json_format=True)

        # Check that the handler has a JsonFormatter
        for handler in logger.logger.handlers:
            assert isinstance(handler.formatter, JsonFormatter)

    def test_configure_logger_with_text_format(self):
        """Test logger configuration with text formatting."""
        # Configure a logger with text formatting
        logger = configure_logger("test_text_logger", json_format=False)

        # Check that the handler has a standard Formatter
        for handler in logger.logger.handlers:
            assert isinstance(handler.formatter, logging.Formatter)
            assert not isinstance(handler.formatter, JsonFormatter)

    def test_configure_logger_with_file_output(self, temp_dir):
        """Test logger configuration with file output."""
        # Create a log file path
        log_file = str(temp_dir / "test.log")

        # Configure a logger with file output
        logger = configure_logger(
            "test_file_logger",
            console_output=False,
            log_file=log_file
        )

        # Check that the logger has a FileHandler
        has_file_handler = False
        for handler in logger.logger.handlers:
            if isinstance(handler, logging.FileHandler):
                has_file_handler = True
                assert handler.baseFilename == log_file

        assert has_file_handler

    def test_configure_logger_with_extra_fields(self):
        """Test logger configuration with extra fields."""
        # Configure a logger with extra fields
        extra_fields = {"environment": "test", "version": "1.0.0"}
        logger = configure_logger(
            "test_extra_fields_logger",
            extra_fields=extra_fields
        )

        # Check that the extra fields are in the adapter
        assert logger.extra == extra_fields

    def test_get_logger(self):
        """Test the get_logger function."""
        # Get a logger
        logger = get_logger("test_get_logger")

        # Check that it's a ContextAdapter
        assert isinstance(logger, ContextAdapter)

        # Check the underlying logger
        assert logger.logger.name == "test_get_logger"

    def test_get_logger_with_context(self):
        """Test the get_logger function with context."""
        # Get a logger with context
        context = {"component": "test", "module": "logging"}
        logger = get_logger("test_context_logger", context)

        # Check that the context is in the adapter
        assert logger.extra == context

    def test_get_environment_log_level_default(self, monkeypatch):
        """Test that get_environment_log_level returns INFO by default."""
        # Remove any existing LOG_LEVEL environment variable
        monkeypatch.delenv("LOG_LEVEL", raising=False)

        # Get the log level
        level = get_environment_log_level()

        # Check that it's INFO
        assert level == logging.INFO

    def test_get_environment_log_level_from_env(self, monkeypatch):
        """Test that get_environment_log_level returns the level from the environment."""
        # Set the LOG_LEVEL environment variable
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")

        # Get the log level
        level = get_environment_log_level()

        # Check that it's DEBUG
        assert level == logging.DEBUG

    def test_setup_root_logger(self):
        """Test the setup_root_logger function."""
        # Set up the root logger
        logger = setup_root_logger(level="WARNING")

        # Check that it's a ContextAdapter
        assert isinstance(logger, ContextAdapter)

        # Check the underlying logger
        assert logger.logger.name == "root"
        assert logger.logger.level == logging.WARNING

        # Check that it has at least one handler
        assert len(logger.logger.handlers) > 0


class TestLoggingUtilityFunctions:
    """Tests for logging utility functions."""

    def test_log_exception(self, capture_logs):
        """Test the log_exception function."""
        # Create a logger
        logger = logging.getLogger("test_log_exception")
        logger.setLevel(logging.ERROR)

        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Log the exception
            log_exception(logger, "An error occurred")

        # Check that the exception was logged
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]
        assert log_entry["level"] == "ERROR"
        assert log_entry["message"] == "An error occurred"
        assert log_entry["exc_info"] is not None

    def test_log_exception_with_custom_level(self, capture_logs):
        """Test the log_exception function with a custom level."""
        # Create a logger
        logger = logging.getLogger("test_log_exception_level")
        logger.setLevel(logging.WARNING)

        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Log the exception with a custom level
            log_exception(logger, "A warning occurred", level=logging.WARNING)

        # Check that the exception was logged at the right level
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]
        assert log_entry["level"] == "WARNING"
        assert log_entry["message"] == "A warning occurred"
        assert log_entry["exc_info"] is not None

    def test_log_exception_with_extra(self, capture_logs):
        """Test the log_exception function with extra context."""
        # Create a logger
        logger = logging.getLogger("test_log_exception_extra")
        logger.setLevel(logging.ERROR)

        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Log the exception with extra context
            log_exception(
                logger,
                "An error occurred",
                extra={"component": "test", "operation": "validation"}
            )

        # Check that the exception was logged with the extra context
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]
        assert log_entry["level"] == "ERROR"
        assert log_entry["message"] == "An error occurred"
        assert log_entry["exc_info"] is not None

    def test_log_with_context(self, capture_logs):
        """Test the log_with_context function."""
        # Create a logger
        logger = logging.getLogger("test_log_with_context")
        logger.setLevel(logging.INFO)

        # Log a message with context
        log_with_context(
            logger,
            logging.INFO,
            "Test message",
            context={"component": "test", "operation": "validation"}
        )

        # Check that the message was logged with the context
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]
        assert log_entry["level"] == "INFO"
        assert log_entry["message"] == "Test message"

    def test_log_critical_error(self, capture_logs):
        """Test the log_critical_error function."""
        # Create a logger
        logger = logging.getLogger("test_log_critical_error")
        logger.setLevel(logging.CRITICAL)

        # Log a critical error
        log_critical_error(logger, "A critical error occurred")

        # Check that the error was logged
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]
        assert log_entry["level"] == "CRITICAL"
        assert log_entry["message"] == "A critical error occurred"

    def test_log_critical_error_with_exception(self, capture_logs):
        """Test the log_critical_error function with an exception."""
        # Create a logger
        logger = logging.getLogger("test_log_critical_error_exception")
        logger.setLevel(logging.CRITICAL)

        # Create an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            # Log the critical error with the exception
            log_critical_error(logger, "A critical error occurred")

        # Check that the error was logged with the exception
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]
        assert log_entry["level"] == "CRITICAL"
        assert log_entry["message"] == "A critical error occurred"
        assert log_entry["exc_info"] is not None

    def test_format_stack_trace(self):
        """Test the format_stack_trace function."""
        # Create a stack trace
        stack_trace = [
            "  File \"test_file.py\", line 42, in test_function\n",
            "    some_code()\n",
            "  File \"another_file.py\", line 21, in another_function\n",
            "    more_code()\n"
        ]

        # Format the stack trace
        formatted = format_stack_trace(stack_trace)

        # Check the formatting
        assert "test_file.py" in formatted
        assert "another_file.py" in formatted
        assert formatted.count("\n") == 3  # 4 lines, 3 newlines

    def test_get_current_stack_trace(self):
        """Test the get_current_stack_trace function."""
        # Get the current stack trace
        stack_trace = get_current_stack_trace()

        # Check that it contains this test function
        assert "test_get_current_stack_trace" in stack_trace
        assert "TestLoggingUtilityFunctions" in stack_trace


class TestLoggingDecorators:
    """Tests for logging decorator functions."""

    def test_log_function_call_decorator(self, capture_logs):
        """Test the log_function_call decorator."""
        # Create a logger
        logger = logging.getLogger("test_log_function_call")
        logger.setLevel(logging.DEBUG)

        # Define a function with the decorator
        @log_function_call(logger)
        def test_function(arg1, arg2, kwarg1=None, kwarg2=None):
            return f"{arg1}-{arg2}-{kwarg1}-{kwarg2}"

        # Call the function
        result = test_function("a", "b", kwarg1="c", kwarg2="d")

        # Check the result
        assert result == "a-b-c-d"

        # Check that the function call was logged
        assert len(capture_logs) >= 2  # At least entry and exit logs
        entry_log = capture_logs[-2]
        exit_log = capture_logs[-1]

        assert entry_log["level"] == "DEBUG"
        assert "Calling" in entry_log["message"]
        assert "test_function" in entry_log["message"]
        assert "a" in entry_log["message"]
        assert "b" in entry_log["message"]
        assert "kwarg1=c" in entry_log["message"]
        assert "kwarg2=d" in entry_log["message"]

        assert exit_log["level"] == "DEBUG"
        assert "returned" in exit_log["message"]
        assert "test_function" in exit_log["message"]
        assert result in exit_log["message"]

    def test_log_function_call_decorator_with_exception(self, capture_logs):
        """Test the log_function_call decorator with an exception."""
        # Create a logger
        logger = logging.getLogger("test_log_function_call_exception")
        logger.setLevel(logging.DEBUG)

        # Define a function with the decorator that raises an exception
        @log_function_call(logger)
        def test_function_with_exception():
            raise ValueError("Test exception")

        # Call the function and catch the exception
        try:
            test_function_with_exception()
            assert False, "Exception was not raised"
        except ValueError:
            pass

        # Check that the exception was logged
        assert len(capture_logs) >= 2  # At least entry and exception logs
        entry_log = capture_logs[-2]
        exception_log = capture_logs[-1]

        assert entry_log["level"] == "DEBUG"
        assert "Calling" in entry_log["message"]
        assert "test_function_with_exception" in entry_log["message"]

        assert exception_log["level"] == "ERROR"
        assert "raised exception" in exception_log["message"]
        assert "test_function_with_exception" in exception_log["message"]
        assert "Test exception" in exception_log["message"]

    def test_log_execution_time_decorator(self, capture_logs):
        """Test the log_execution_time decorator."""
        # Create a logger
        logger = logging.getLogger("test_log_execution_time")
        logger.setLevel(logging.DEBUG)

        # Define a function with the decorator
        @log_execution_time(logger)
        def test_function():
            # Simulate some work
            import time
            time.sleep(0.01)
            return "result"

        # Call the function
        result = test_function()

        # Check the result
        assert result == "result"

        # Check that the execution time was logged
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]

        assert log_entry["level"] == "DEBUG"
        assert "executed in" in log_entry["message"]
        assert "test_function" in log_entry["message"]
        assert "seconds" in log_entry["message"]

    def test_log_execution_time_decorator_with_exception(self, capture_logs):
        """Test the log_execution_time decorator with an exception."""
        # Create a logger
        logger = logging.getLogger("test_log_execution_time_exception")
        logger.setLevel(logging.DEBUG)

        # Define a function with the decorator that raises an exception
        @log_execution_time(logger)
        def test_function_with_exception():
            # Simulate some work
            import time
            time.sleep(0.01)
            raise ValueError("Test exception")

        # Call the function and catch the exception
        try:
            test_function_with_exception()
            assert False, "Exception was not raised"
        except ValueError:
            pass

        # Check that the execution time was logged with the exception
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]

        assert log_entry["level"] == "ERROR"
        assert "failed after" in log_entry["message"]
        assert "test_function_with_exception" in log_entry["message"]
        assert "seconds" in log_entry["message"]
        assert "Test exception" in log_entry["message"]


class TestLoggingIntegration:
    """Integration tests for the logging system."""

    def test_structured_logging_with_context(self, capture_logs, temp_dir):
        """Test structured logging with context information."""
        # Create a log file path
        log_file = str(temp_dir / "integration.log")

        # Configure a logger with JSON formatting and file output
        logger = configure_logger(
            "test_integration",
            level="DEBUG",
            json_format=True,
            console_output=True,
            log_file=log_file,
            extra_fields={"service": "ocr-service", "environment": "test"}
        )

        # Set a request ID
        with request_context("req-integration-test"):
            # Log messages at different levels with context
            log_with_context(
                logger,
                logging.DEBUG,
                "Debug message",
                context={"component": "test", "operation": "integration"}
            )

            log_with_context(
                logger,
                logging.INFO,
                "Info message",
                context={"component": "test", "operation": "integration"}
            )

            log_with_context(
                logger,
                logging.WARNING,
                "Warning message",
                context={"component": "test", "operation": "integration"}
            )

            try:
                raise ValueError("Integration test exception")
            except ValueError:
                log_exception(
                    logger,
                    "Error message",
                    extra={"component": "test", "operation": "integration"}
                )

            log_critical_error(
                logger,
                "Critical message",
                extra={"component": "test", "operation": "integration"}
            )

        # Check that the logs were captured
        assert len(capture_logs) >= 5  # At least 5 log entries

        # Check that the log file was created and contains JSON entries
        with open(log_file, "r") as f:
            log_lines = f.readlines()

        assert len(log_lines) >= 5

        # Parse the JSON entries
        for line in log_lines:
            log_entry = json.loads(line)
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry
            assert "service" in log_entry
            assert log_entry["service"] == "ocr-service"
            assert "environment" in log_entry
            assert log_entry["environment"] == "test"
            assert "request_id" in log_entry
            assert log_entry["request_id"] == "req-integration-test"
            assert "component" in log_entry
            assert log_entry["component"] == "test"
            assert "operation" in log_entry
            assert log_entry["operation"] == "integration"

    def test_log_level_filtering(self, temp_dir):
        """Test log level filtering based on environment."""
        # Create log file paths
        debug_log_file = str(temp_dir / "debug.log")
        info_log_file = str(temp_dir / "info.log")
        warning_log_file = str(temp_dir / "warning.log")

        # Configure loggers with different levels
        debug_logger = configure_logger(
            "test_debug",
            level="DEBUG",
            console_output=False,
            log_file=debug_log_file
        )

        info_logger = configure_logger(
            "test_info",
            level="INFO",
            console_output=False,
            log_file=info_log_file
        )

        warning_logger = configure_logger(
            "test_warning",
            level="WARNING",
            console_output=False,
            log_file=warning_log_file
        )

        # Log messages at different levels
        debug_logger.debug("Debug message")
        debug_logger.info("Info message")
        debug_logger.warning("Warning message")

        info_logger.debug("Debug message")
        info_logger.info("Info message")
        info_logger.warning("Warning message")

        warning_logger.debug("Debug message")
        warning_logger.warning("Warning message")
        warning_logger.error("Error message")

        # Check the log files
        with open(debug_log_file, "r") as f:
            debug_lines = f.readlines()

        with open(info_log_file, "r") as f:
            info_lines = f.readlines()

        with open(warning_log_file, "r") as f:
            warning_lines = f.readlines()

        # Debug logger should log all levels
        assert len(debug_lines) == 3
        assert "Debug message" in debug_lines[0]
        assert "Info message" in debug_lines[1]
        assert "Warning message" in debug_lines[2]

        # Info logger should log INFO and above
        assert len(info_lines) == 2
        assert "Info message" in info_lines[0]
        assert "Warning message" in info_lines[1]

        # Warning logger should log WARNING and above
        assert len(warning_lines) == 2
        assert "Warning message" in warning_lines[0]
        assert "Error message" in warning_lines[1]

    def test_distributed_tracing_with_request_id(self, capture_logs):
        """Test request ID tracking for distributed tracing."""
        # Configure a logger
        logger = configure_logger("test_tracing", level="DEBUG")

        # Define a function that logs with the current request ID
        def log_with_current_request_id(message):
            log_with_context(
                logger,
                logging.INFO,
                message,
                context={"operation": "tracing"}
            )

        # Simulate a request flow with nested contexts
        with request_context("req-parent"):
            log_with_current_request_id("Parent request started")

            # Simulate a child request
            with request_context("req-child-1"):
                log_with_current_request_id("Child request 1 processing")

            # Back to parent context
            log_with_current_request_id("Parent request continuing")

            # Another child request
            with request_context("req-child-2"):
                log_with_current_request_id("Child request 2 processing")

            # Back to parent context again
            log_with_current_request_id("Parent request completed")

        # Check the logs
        assert len(capture_logs) >= 5

        # Extract the request IDs from the logs
        request_ids = []
        for log in capture_logs:
            if "Parent request started" in log["message"]:
                request_ids.append((log["message"], "req-parent"))
            elif "Child request 1 processing" in log["message"]:
                request_ids.append((log["message"], "req-child-1"))
            elif "Parent request continuing" in log["message"]:
                request_ids.append((log["message"], "req-parent"))
            elif "Child request 2 processing" in log["message"]:
                request_ids.append((log["message"], "req-child-2"))
            elif "Parent request completed" in log["message"]:
                request_ids.append((log["message"], "req-parent"))

        # Check that the request IDs match the expected pattern
        assert len(request_ids) == 5
        for message, expected_id in request_ids:
            log_entry = next(log for log in capture_logs if log["message"] == message)
            assert "request_id" in log_entry
            assert log_entry["request_id"] == expected_id

    def test_machine_readable_log_formatting(self, temp_dir):
        """Test log formatting for machine-readable output."""
        # Create a log file path
        log_file = str(temp_dir / "machine_readable.log")

        # Configure a logger with JSON formatting
        logger = configure_logger(
            "test_machine_readable",
            level="INFO",
            json_format=True,
            console_output=False,
            log_file=log_file
        )

        # Log various types of messages
        logger.info("Simple message")
        logger.warning("Message with %s", "formatting")
        logger.error("Message with multiple %s and %d", "parameters", 42)

        # Log with extra context
        logger.info(
            "Message with context",
            extra={"context_key": "context_value", "numeric_value": 123}
        )

        # Log an exception
        try:
            raise ValueError("Test exception")
        except ValueError:
            logger.exception("Exception occurred")

        # Read the log file
        with open(log_file, "r") as f:
            log_lines = f.readlines()

        # Check that all lines are valid JSON
        for line in log_lines:
            log_entry = json.loads(line)
            assert isinstance(log_entry, dict)

        # Parse each log entry
        log_entries = [json.loads(line) for line in log_lines]

        # Check the simple message
        simple_entry = next(entry for entry in log_entries if entry["message"] == "Simple message")
        assert simple_entry["level"] == "INFO"

        # Check the formatted message
        formatted_entry = next(entry for entry in log_entries if "formatting" in entry["message"])
        assert formatted_entry["level"] == "WARNING"
        assert formatted_entry["message"] == "Message with formatting"

        # Check the message with multiple parameters
        multi_param_entry = next(entry for entry in log_entries if "parameters" in entry["message"])
        assert multi_param_entry["level"] == "ERROR"
        assert multi_param_entry["message"] == "Message with multiple parameters and 42"

        # Check the message with context
        context_entry = next(entry for entry in log_entries if entry["message"] == "Message with context")
        assert context_entry["level"] == "INFO"
        assert "context_key" in context_entry
        assert context_entry["context_key"] == "context_value"
        assert "numeric_value" in context_entry
        assert context_entry["numeric_value"] == 123

        # Check the exception message
        exception_entry = next(entry for entry in log_entries if entry["message"] == "Exception occurred")
        assert exception_entry["level"] == "ERROR"
        assert "exception" in exception_entry
        assert exception_entry["exception"]["type"] == "ValueError"
        assert exception_entry["exception"]["message"] == "Test exception"


class TestEnvironmentSpecificLogging:
    """Tests for environment-specific logging configurations."""

    def test_development_environment_logging(self, monkeypatch):
        """Test logging configuration in development environment."""
        # Set environment variables for development
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        monkeypatch.setenv("ENVIRONMENT", "development")

        # Get the environment log level
        level = get_environment_log_level()
        assert level == logging.DEBUG

        # Configure a logger
        logger = configure_logger(
            "test_dev_env",
            level=level,
            json_format=False,  # Text format for development
            extra_fields={"environment": "development"}
        )

        # Check the logger configuration
        assert logger.logger.level == logging.DEBUG
        for handler in logger.logger.handlers:
            assert not isinstance(handler.formatter, JsonFormatter)

    def test_production_environment_logging(self, monkeypatch):
        """Test logging configuration in production environment."""
        # Set environment variables for production
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        monkeypatch.setenv("ENVIRONMENT", "production")

        # Get the environment log level
        level = get_environment_log_level()
        assert level == logging.WARNING

        # Configure a logger
        logger = configure_logger(
            "test_prod_env",
            level=level,
            json_format=True,  # JSON format for production
            extra_fields={"environment": "production"}
        )

        # Check the logger configuration
        assert logger.logger.level == logging.WARNING
        for handler in logger.logger.handlers:
            assert isinstance(handler.formatter, JsonFormatter)

    def test_log_level_constants(self):
        """Test the LOG_LEVEL_MAP constants."""
        # Check that all standard log levels are mapped correctly
        assert LOG_LEVEL_MAP["DEBUG"] == logging.DEBUG
        assert LOG_LEVEL_MAP["INFO"] == logging.INFO
        assert LOG_LEVEL_MAP["WARNING"] == logging.WARNING
        assert LOG_LEVEL_MAP["ERROR"] == logging.ERROR
        assert LOG_LEVEL_MAP["CRITICAL"] == logging.CRITICAL


class TestUseCasesAndEdgeCases:
    """Tests for specific use cases and edge cases."""

    def test_ocr_processing_logging_flow(self, capture_logs):
        """Test logging during a simulated OCR processing flow."""
        # Configure a logger
        logger = configure_logger("ocr_processing", level="DEBUG")

        # Simulate an OCR processing flow with request context
        with request_context("req-doc-123456"):
            # Log the start of processing
            logger.info(
                "Starting OCR processing for document",
                extra={"document_id": "doc-123456", "document_type": "application"}
            )

            # Log preprocessing step
            logger.debug(
                "Preprocessing document",
                extra={"operation": "preprocess", "document_id": "doc-123456"}
            )

            # Log OCR extraction
            logger.info(
                "Extracting text from document",
                extra={"operation": "extract", "document_id": "doc-123456"}
            )

            # Log post-processing
            logger.debug(
                "Post-processing extracted text",
                extra={"operation": "postprocess", "document_id": "doc-123456"}
            )

            # Log completion
            logger.info(
                "OCR processing completed",
                extra={
                    "document_id": "doc-123456",
                    "processing_time": 1.23,
                    "confidence": 0.95
                }
            )

        # Check the logs
        assert len(capture_logs) >= 5

        # Check that all logs have the request ID
        for log in capture_logs:
            if "ocr_processing" in log["logger"]:
                assert "request_id" in log
                assert log["request_id"] == "req-doc-123456"

    def test_error_handling_with_retry(self, capture_logs):
        """Test logging during error handling with retry."""
        # Configure a logger
        logger = configure_logger("error_handling", level="DEBUG")

        # Simulate a function with retry logic
        def process_with_retry(max_retries=3):
            for attempt in range(1, max_retries + 1):
                try:
                    if attempt < max_retries:  # Succeed on the last attempt
                        logger.info(
                            f"Attempt {attempt} of {max_retries}",
                            extra={"attempt": attempt, "max_retries": max_retries}
                        )
                        raise ConnectionError(f"Simulated failure on attempt {attempt}")
                    else:
                        logger.info(
                            f"Succeeded on attempt {attempt}",
                            extra={"attempt": attempt, "max_retries": max_retries}
                        )
                        return "success"
                except ConnectionError as e:
                    log_exception(
                        logger,
                        f"Failed on attempt {attempt}, retrying...",
                        exc_info=sys.exc_info(),
                        extra={"attempt": attempt, "max_retries": max_retries}
                    )

        # Call the function
        result = process_with_retry()
        assert result == "success"

        # Check the logs
        assert len(capture_logs) >= 5  # 2 attempts + 2 exceptions + 1 success

        # Check the sequence of logs
        attempt1_log = next(log for log in capture_logs if "Attempt 1 of 3" in log["message"])
        assert attempt1_log["level"] == "INFO"

        failure1_log = next(log for log in capture_logs if "Failed on attempt 1" in log["message"])
        assert failure1_log["level"] == "ERROR"
        assert failure1_log["exc_info"] is not None

        attempt2_log = next(log for log in capture_logs if "Attempt 2 of 3" in log["message"])
        assert attempt2_log["level"] == "INFO"

        failure2_log = next(log for log in capture_logs if "Failed on attempt 2" in log["message"])
        assert failure2_log["level"] == "ERROR"
        assert failure2_log["exc_info"] is not None

        success_log = next(log for log in capture_logs if "Succeeded on attempt 3" in log["message"])
        assert success_log["level"] == "INFO"

    def test_concurrent_request_contexts(self):
        """Test that request contexts are isolated between threads."""
        import threading
        import queue

        # Create a queue to collect results
        results = queue.Queue()

        # Define a function that runs in a thread with its own request context
        def thread_func(thread_id):
            with request_context(f"req-thread-{thread_id}"):
                # Get the request ID and put it in the results queue
                request_id = get_request_id()
                results.put((thread_id, request_id))

                # Sleep to allow other threads to run
                import time
                time.sleep(0.01)

                # Check that the request ID is still the same
                assert get_request_id() == request_id
                results.put((thread_id, get_request_id()))

        # Create and start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=thread_func, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check the results
        thread_results = {}
        while not results.empty():
            thread_id, request_id = results.get()
            if thread_id not in thread_results:
                thread_results[thread_id] = []
            thread_results[thread_id].append(request_id)

        # Check that each thread had its own consistent request ID
        for thread_id, request_ids in thread_results.items():
            assert len(request_ids) == 2  # Two measurements per thread
            assert request_ids[0] == request_ids[1]  # Same ID throughout the thread
            assert request_ids[0] == f"req-thread-{thread_id}"  # Correct ID format

        # Check that all threads had different request IDs
        all_ids = [ids[0] for ids in thread_results.values()]
        assert len(all_ids) == len(set(all_ids))  # All IDs are unique

    def test_edge_case_empty_logger_name(self):
        """Test configuring a logger with an empty name."""
        # Configure a logger with an empty name
        logger = configure_logger("", level="INFO")

        # Check that it still works
        assert logger is not None
        assert isinstance(logger, ContextAdapter)
        assert logger.logger.name == ""

    def test_edge_case_invalid_log_level(self, monkeypatch):
        """Test handling of invalid log level strings."""
        # Set an invalid log level
        monkeypatch.setenv("LOG_LEVEL", "INVALID_LEVEL")

        # Get the environment log level
        level = get_environment_log_level()

        # Check that it defaults to INFO
        assert level == logging.INFO

        # Configure a logger with an invalid level string
        logger = configure_logger("test_invalid_level", level="INVALID_LEVEL")

        # Check that it defaults to INFO
        assert logger.logger.level == logging.INFO


class TestTechnicalSpecificationRequirements:
    """Tests for requirements from the technical specification."""

    def test_comprehensive_logging_with_specified_levels(self, capture_logs):
        """Test comprehensive logging with specified log levels (ERROR, WARN, INFO, DEBUG)."""
        # Configure a logger
        logger = configure_logger("test_levels", level="DEBUG")

        # Log messages at different levels
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        # Check that all levels were logged
        log_levels = [log["level"] for log in capture_logs if log["logger"] == "test_levels"]
        assert "DEBUG" in log_levels
        assert "INFO" in log_levels
        assert "WARNING" in log_levels
        assert "ERROR" in log_levels
        assert "CRITICAL" in log_levels

    def test_logs_include_timestamp_service_name_and_context(self, temp_dir):
        """Test that logs include timestamp, service name, and context information."""
        # Create a log file path
        log_file = str(temp_dir / "context.log")

        # Configure a logger with JSON formatting
        logger = configure_logger(
            "test_context",
            level="INFO",
            json_format=True,
            console_output=False,
            log_file=log_file,
            extra_fields={"service": "ocr-service"}
        )

        # Set a request ID
        with request_context("req-context-test"):
            # Log a message with context
            logger.info(
                "Test message",
                extra={"component": "test", "operation": "validation"}
            )

        # Read the log file
        with open(log_file, "r") as f:
            log_lines = f.readlines()

        # Parse the JSON entry
        log_entry = json.loads(log_lines[0])

        # Check required fields
        assert "timestamp" in log_entry
        assert "service" in log_entry
        assert log_entry["service"] == "ocr-service"
        assert "request_id" in log_entry
        assert log_entry["request_id"] == "req-context-test"
        assert "component" in log_entry
        assert log_entry["component"] == "test"
        assert "operation" in log_entry
        assert log_entry["operation"] == "validation"

    def test_error_tracking_and_troubleshooting(self, capture_logs):
        """Test support for error tracking and troubleshooting."""
        # Configure a logger
        logger = configure_logger("test_error_tracking", level="ERROR")

        # Log a critical error
        try:
            raise ValueError("Critical error for tracking")
        except ValueError:
            log_critical_error(
                logger,
                "A critical error occurred that requires attention",
                extra={"component": "test", "operation": "critical_operation"}
            )

        # Check the log
        assert len(capture_logs) > 0
        log_entry = capture_logs[-1]

        # Check required fields for error tracking
        assert log_entry["level"] == "CRITICAL"
        assert "A critical error occurred" in log_entry["message"]
        assert log_entry["exc_info"] is not None
        assert "alert" in log_entry
        assert log_entry["alert"] is True
        assert "stack_trace" in log_entry
        assert "component" in log_entry
        assert log_entry["component"] == "test"
        assert "operation" in log_entry
        assert log_entry["operation"] == "critical_operation"

    def test_ocr_service_specific_logging(self, capture_logs):
        """Test OCR service-specific logging requirements."""
        # Configure a logger
        logger = configure_logger(
            "ocr_service",
            level="INFO",
            extra_fields={"service": "ocr-service"}
        )

        # Simulate OCR processing with confidence scores
        with request_context("req-ocr-123456"):
            # Log the start of processing
            logger.info(
                "Processing document with TensorFlow OCR",
                extra={
                    "document_id": "doc-123456",
                    "document_type": "application",
                    "model": "tensorflow-ocr-v2"
                }
            )

            # Log extraction results with confidence scores
            logger.info(
                "Text extraction completed",
                extra={
                    "document_id": "doc-123456",
                    "processing_time": 2.34,
                    "overall_confidence": 0.92,
                    "field_confidences": {
                        "name": 0.98,
                        "address": 0.95,
                        "phone": 0.89,
                        "email": 0.94
                    }
                }
            )

        # Check the logs
        assert len(capture_logs) >= 2

        # Check the processing log
        processing_log = next(log for log in capture_logs if "Processing document" in log["message"])
        assert processing_log["level"] == "INFO"
        assert "document_id" in processing_log
        assert processing_log["document_id"] == "doc-123456"
        assert "model" in processing_log
        assert processing_log["model"] == "tensorflow-ocr-v2"

        # Check the results log with confidence scores
        results_log = next(log for log in capture_logs if "Text extraction completed" in log["message"])
        assert results_log["level"] == "INFO"
        assert "document_id" in results_log
        assert results_log["document_id"] == "doc-123456"
        assert "processing_time" in results_log
        assert results_log["processing_time"] == 2.34
        assert "overall_confidence" in results_log
        assert results_log["overall_confidence"] == 0.92
        assert "field_confidences" in results_log
        assert "name" in results_log["field_confidences"]
        assert results_log["field_confidences"]["name"] == 0.98


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])