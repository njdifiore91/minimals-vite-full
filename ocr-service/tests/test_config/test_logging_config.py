#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's logging_config.py module.

These tests verify that logging configuration correctly sets up log levels, formats,
handlers, and context enrichment based on the environment. The tests ensure that
logging works correctly for monitoring, debugging, and troubleshooting.
"""

import os
import sys
import json
import logging
import pytest
from unittest.mock import patch, MagicMock, call
from datetime import datetime
import uuid
import importlib
from typing import Dict, Any, Optional

# Import test fixtures
from conftest import Environment

# Import the module under test
from src.config.logging_config import (
    SERVICE_NAME,
    LOG_LEVEL,
    LOG_LEVELS,
    DEFAULT_LOG_LEVEL,
    JsonFormatter,
    LOGGING_CONFIG,
    setup_logging,
    LogContext,
    get_logger,
    add_context_to_record,
    ContextFilter,
    apply_context_filter
)


class TestLogLevelConfiguration:
    """Test suite for log level configuration."""

    def test_log_levels_by_environment(self):
        """Test that the correct log level is set for each environment."""
        assert LOG_LEVELS["development"] == logging.DEBUG
        assert LOG_LEVELS["staging"] == logging.INFO
        assert LOG_LEVELS["production"] == logging.INFO

    def test_default_log_level(self):
        """Test that the default log level is set correctly."""
        assert DEFAULT_LOG_LEVEL == logging.INFO

    @pytest.mark.parametrize("env_vars", [Environment.DEVELOPMENT], indirect=True)
    def test_development_log_level(self, env_vars):
        """Test that the log level is set to DEBUG in development environment."""
        with patch("src.config.logging_config.ENVIRONMENT", "development"):
            from src.config.logging_config import LOG_LEVEL
            assert LOG_LEVEL == logging.DEBUG

    @pytest.mark.parametrize("env_vars", [Environment.STAGING], indirect=True)
    def test_staging_log_level(self, env_vars):
        """Test that the log level is set to INFO in staging environment."""
        with patch("src.config.logging_config.ENVIRONMENT", "staging"):
            from src.config.logging_config import LOG_LEVEL
            assert LOG_LEVEL == logging.INFO

    @pytest.mark.parametrize("env_vars", [Environment.PRODUCTION], indirect=True)
    def test_production_log_level(self, env_vars):
        """Test that the log level is set to INFO in production environment."""
        with patch("src.config.logging_config.ENVIRONMENT", "production"):
            from src.config.logging_config import LOG_LEVEL
            assert LOG_LEVEL == logging.INFO

    def test_unknown_environment_log_level(self):
        """Test that the default log level is used for unknown environments."""
        with patch("src.config.logging_config.ENVIRONMENT", "unknown"):
            from src.config.logging_config import LOG_LEVEL
            assert LOG_LEVEL == DEFAULT_LOG_LEVEL


class TestJsonFormatter:
    """Test suite for the JsonFormatter class."""

    def test_basic_format(self):
        """Test that the formatter correctly formats a basic log record."""
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
        log_dict = json.loads(formatted)

        # Check basic fields
        assert "timestamp" in log_dict
        assert log_dict["service"] == SERVICE_NAME
        assert log_dict["level"] == "INFO"
        assert log_dict["message"] == "Test message"
        assert log_dict["logger"] == "test_logger"
        assert log_dict["path"] == "test_file.py"
        assert log_dict["function"] == "?"
        assert log_dict["line"] == 42

    def test_format_with_exception(self):
        """Test that the formatter correctly formats a log record with an exception."""
        formatter = JsonFormatter()
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test_file.py",
            lineno=42,
            msg="Exception occurred",
            args=(),
            exc_info=exc_info
        )

        formatted = formatter.format(record)
        log_dict = json.loads(formatted)

        # Check exception field
        assert "exception" in log_dict
        assert "ValueError: Test exception" in log_dict["exception"]

    def test_format_with_context(self):
        """Test that the formatter correctly includes context information."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message with context",
            args=(),
            exc_info=None
        )

        # Add context attributes
        record.request_id = "test-request-id"
        record.document_id = "test-document-id"
        record.application_id = "test-application-id"
        record.processing_time = 123
        record.extra = {"custom_field": "custom_value"}

        formatted = formatter.format(record)
        log_dict = json.loads(formatted)

        # Check context fields
        assert log_dict["request_id"] == "test-request-id"
        assert log_dict["document_id"] == "test-document-id"
        assert log_dict["application_id"] == "test-application-id"
        assert log_dict["processing_time_ms"] == 123
        assert log_dict["custom_field"] == "custom_value"


class TestLoggingConfig:
    """Test suite for the LOGGING_CONFIG dictionary."""

    def test_formatters_config(self):
        """Test that formatters are correctly configured."""
        assert "json" in LOGGING_CONFIG["formatters"]
        assert "standard" in LOGGING_CONFIG["formatters"]
        assert LOGGING_CONFIG["formatters"]["json"]["()"] == JsonFormatter
        assert "format" in LOGGING_CONFIG["formatters"]["standard"]
        assert "datefmt" in LOGGING_CONFIG["formatters"]["standard"]

    def test_console_handler_config(self):
        """Test that the console handler is correctly configured."""
        assert "console" in LOGGING_CONFIG["handlers"]
        console_handler = LOGGING_CONFIG["handlers"]["console"]
        assert console_handler["class"] == "logging.StreamHandler"
        assert console_handler["level"] == LOG_LEVEL
        assert console_handler["stream"] == sys.stdout

    def test_file_handler_config(self):
        """Test that the file handler is correctly configured."""
        assert "file" in LOGGING_CONFIG["handlers"]
        file_handler = LOGGING_CONFIG["handlers"]["file"]
        assert file_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert file_handler["level"] == LOG_LEVEL
        assert file_handler["formatter"] == "json"
        assert SERVICE_NAME in file_handler["filename"]
        assert file_handler["maxBytes"] == 10485760  # 10MB
        assert file_handler["backupCount"] == 10

    def test_error_file_handler_config(self):
        """Test that the error file handler is correctly configured."""
        assert "error_file" in LOGGING_CONFIG["handlers"]
        error_handler = LOGGING_CONFIG["handlers"]["error_file"]
        assert error_handler["class"] == "logging.handlers.RotatingFileHandler"
        assert error_handler["level"] == logging.ERROR
        assert error_handler["formatter"] == "json"
        assert SERVICE_NAME in error_handler["filename"]
        assert "_error" in error_handler["filename"]
        assert error_handler["maxBytes"] == 10485760  # 10MB
        assert error_handler["backupCount"] == 10

    def test_root_logger_config(self):
        """Test that the root logger is correctly configured."""
        assert "" in LOGGING_CONFIG["loggers"]
        root_logger = LOGGING_CONFIG["loggers"][""]
        assert "console" in root_logger["handlers"]
        assert root_logger["level"] == LOG_LEVEL
        assert root_logger["propagate"] is True

    def test_service_loggers_config(self):
        """Test that service-specific loggers are correctly configured."""
        service_loggers = ["ocr_service", "ocr_service.api", "ocr_service.models", "ocr_service.services"]
        for logger_name in service_loggers:
            assert logger_name in LOGGING_CONFIG["loggers"]
            logger_config = LOGGING_CONFIG["loggers"][logger_name]
            assert logger_config["level"] == LOG_LEVEL
            assert logger_config["propagate"] is False

            # Check handlers based on environment
            with patch("src.config.logging_config.ENVIRONMENT", "development"):
                assert logger_config["handlers"] == ["console"]

            with patch("src.config.logging_config.ENVIRONMENT", "production"):
                assert set(logger_config["handlers"]) == {"console", "file", "error_file"}

    def test_tensorflow_logger_config(self):
        """Test that the TensorFlow logger is correctly configured."""
        assert "tensorflow" in LOGGING_CONFIG["loggers"]
        tf_logger = LOGGING_CONFIG["loggers"]["tensorflow"]
        assert tf_logger["level"] == logging.WARNING  # Reduced verbosity
        assert tf_logger["propagate"] is False


class TestProductionLoggingConfig:
    """Test suite for production-specific logging configuration."""

    @patch("src.config.logging_config.ENVIRONMENT", "production")
    def test_datadog_handler_not_available(self):
        """Test that Datadog handler is not added when the module is not available."""
        with patch("importlib.import_module", side_effect=ImportError):
            # Re-import to trigger the production-specific code
            import importlib
            importlib.reload(sys.modules["src.config.logging_config"])
            from src.config.logging_config import LOGGING_CONFIG

            # Datadog handler should not be added
            assert "datadog" not in LOGGING_CONFIG["handlers"]

    @patch("src.config.logging_config.ENVIRONMENT", "production")
    def test_datadog_handler_available(self):
        """Test that Datadog handler is added when the module is available."""
        # Mock the datadog_logger module
        mock_datadog_module = MagicMock()
        mock_datadog_module.DatadogLogHandler = "DatadogLogHandler"

        with patch.dict("sys.modules", {"datadog_logger": mock_datadog_module}):
            # Re-import to trigger the production-specific code
            importlib.reload(sys.modules["src.config.logging_config"])
            from src.config.logging_config import LOGGING_CONFIG

            # Datadog handler should be added
            assert "datadog" in LOGGING_CONFIG["handlers"]
            datadog_handler = LOGGING_CONFIG["handlers"]["datadog"]
            assert datadog_handler["class"] == "datadog_logger.DatadogLogHandler"
            assert datadog_handler["level"] == LOG_LEVEL
            assert datadog_handler["formatter"] == "json"
            assert datadog_handler["service"] == SERVICE_NAME
            assert "env:production" in datadog_handler["tags"]
            assert f"service:{SERVICE_NAME}" in datadog_handler["tags"]

            # Check that datadog handler is added to all loggers
            for logger_name, logger_config in LOGGING_CONFIG["loggers"].items():
                assert "datadog" in logger_config["handlers"]


class TestSetupLogging:
    """Test suite for the setup_logging function."""

    def test_setup_logging(self):
        """Test that setup_logging correctly configures logging."""
        with patch("logging.config.dictConfig") as mock_dict_config, \
             patch("logging.info") as mock_info:
            setup_logging()

            # Check that dictConfig was called with the correct configuration
            mock_dict_config.assert_called_once_with(LOGGING_CONFIG)

            # Check that an info message was logged
            mock_info.assert_called_once()
            assert SERVICE_NAME in mock_info.call_args[0][0]
            assert "logging initialized" in mock_info.call_args[0][0]
            assert logging.getLevelName(LOG_LEVEL) in mock_info.call_args[0][0]


class TestLogContext:
    """Test suite for the LogContext class."""

    def test_context_manager_with_request_id(self):
        """Test that LogContext correctly adds context with a provided request_id."""
        logger = logging.getLogger("test_logger")
        request_id = "test-request-id"

        # Create a handler with a _context attribute
        handler = logging.StreamHandler()
        handler._context = {}
        logger.addHandler(handler)

        # Use the context manager with a request_id
        with LogContext(logger, request_id=request_id, document_id="test-doc") as ctx_request_id:
            # Check that the context was set on the handler
            assert handler._context["request_id"] == request_id
            assert handler._context["document_id"] == "test-doc"
            # Check that the context manager returns the request_id
            assert ctx_request_id == request_id

        # Check that the context was restored after exiting
        assert handler._context == {}

    def test_context_manager_without_request_id(self):
        """Test that LogContext generates a request_id if not provided."""
        logger = logging.getLogger("test_logger")

        # Create a handler with a _context attribute
        handler = logging.StreamHandler()
        handler._context = {}
        logger.addHandler(handler)

        # Use the context manager without a request_id
        with LogContext(logger, document_id="test-doc") as ctx_request_id:
            # Check that a request_id was generated
            assert "request_id" in handler._context
            assert uuid.UUID(handler._context["request_id"])  # Valid UUID
            assert handler._context["document_id"] == "test-doc"
            # Check that the context manager returns the generated request_id
            assert ctx_request_id == handler._context["request_id"]

        # Check that the context was restored after exiting
        assert handler._context == {}

    def test_context_manager_with_existing_context(self):
        """Test that LogContext correctly preserves and restores existing context."""
        logger = logging.getLogger("test_logger")

        # Create a handler with existing context
        handler = logging.StreamHandler()
        handler._context = {"existing_key": "existing_value"}
        logger.addHandler(handler)

        # Use the context manager
        with LogContext(logger, request_id="test-request-id"):
            # Check that the new context was added without removing existing context
            assert handler._context["existing_key"] == "existing_value"
            assert handler._context["request_id"] == "test-request-id"

        # Check that the original context was restored after exiting
        assert handler._context == {"existing_key": "existing_value"}


class TestGetLogger:
    """Test suite for the get_logger function."""

    def test_get_logger_returns_logger_with_context_method(self):
        """Test that get_logger returns a logger with a context method."""
        logger = get_logger("test_logger")

        # Check that the logger has a context method
        assert hasattr(logger, "context")
        assert callable(logger.context)

        # Check that the context method returns a LogContext instance
        context = logger.context(request_id="test-request-id")
        assert isinstance(context, LogContext)

    def test_logger_context_method_works(self):
        """Test that the context method on the logger works correctly."""
        logger = get_logger("test_logger")

        # Create a handler with a _context attribute
        handler = logging.StreamHandler()
        handler._context = {}
        logger.addHandler(handler)

        # Use the context method
        with logger.context(request_id="test-request-id", document_id="test-doc"):
            # Check that the context was set on the handler
            assert handler._context["request_id"] == "test-request-id"
            assert handler._context["document_id"] == "test-doc"

        # Check that the context was restored after exiting
        assert handler._context == {}


class TestContextFilter:
    """Test suite for the ContextFilter class."""

    def test_add_context_to_record(self):
        """Test that add_context_to_record correctly adds context to a log record."""
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        context = {
            "request_id": "test-request-id",
            "document_id": "test-doc",
            "application_id": "test-app"
        }

        add_context_to_record(record, context)

        # Check that context was added to the record
        assert record.request_id == "test-request-id"
        assert record.document_id == "test-doc"
        assert record.application_id == "test-app"

    def test_context_filter(self):
        """Test that ContextFilter correctly adds context from handler to log records."""
        # Create a filter
        context_filter = ContextFilter()

        # Create a record with a handler that has context
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )

        # Create a handler with context
        handler = logging.StreamHandler()
        handler._context = {
            "request_id": "test-request-id",
            "document_id": "test-doc"
        }

        # Add handler to record
        record.handler = handler

        # Apply filter
        context_filter.filter(record)

        # Check that context was added to the record
        assert record.request_id == "test-request-id"
        assert record.document_id == "test-doc"

    def test_apply_context_filter(self):
        """Test that apply_context_filter adds the filter to all handlers."""
        with patch("logging.root.handlers", [MagicMock(), MagicMock()]), \
             patch("logging.root.manager.loggerDict", {
                 "logger1": MagicMock(handlers=[MagicMock()]),
                 "logger2": MagicMock(handlers=[MagicMock(), MagicMock()])
             }), \
             patch("logging.getLogger") as mock_get_logger:
            # Mock the loggers returned by getLogger
            mock_loggers = {
                "logger1": MagicMock(handlers=[MagicMock()]),
                "logger2": MagicMock(handlers=[MagicMock(), MagicMock()])
            }
            mock_get_logger.side_effect = lambda name: mock_loggers[name]

            # Call apply_context_filter
            apply_context_filter()

            # Check that addFilter was called on all handlers
            for handler in logging.root.handlers:
                handler.addFilter.assert_called_once()
                # Check that a ContextFilter was added
                filter_arg = handler.addFilter.call_args[0][0]
                assert isinstance(filter_arg, ContextFilter)

            # Check named loggers
            for logger_name, logger in mock_loggers.items():
                for handler in logger.handlers:
                    handler.addFilter.assert_called_once()
                    # Check that a ContextFilter was added
                    filter_arg = handler.addFilter.call_args[0][0]
                    assert isinstance(filter_arg, ContextFilter)


class TestLoggingConfigWithFixtures:
    """Test suite for logging configuration using pytest fixtures."""

    @pytest.mark.parametrize("env_vars", [Environment.DEVELOPMENT], indirect=True)
    def test_development_logging_config(self, env_vars, monkeypatch):
        """Test logging configuration in development environment."""
        # Set environment variable
        monkeypatch.setenv("ENVIRONMENT", "development")
        
        # Reload the module to apply the environment variable
        importlib.reload(sys.modules["src.config.logging_config"])
        from src.config.logging_config import LOG_LEVEL, LOGGING_CONFIG
        
        # Check log level
        assert LOG_LEVEL == logging.DEBUG
        
        # Check console formatter in development (should be standard, not JSON)
        assert LOGGING_CONFIG["handlers"]["console"]["formatter"] == "standard"
        
        # Check that file handlers are not used for service loggers in development
        service_logger = LOGGING_CONFIG["loggers"]["ocr_service"]
        assert service_logger["handlers"] == ["console"]

    @pytest.mark.parametrize("env_vars", [Environment.STAGING], indirect=True)
    def test_staging_logging_config(self, env_vars, monkeypatch):
        """Test logging configuration in staging environment."""
        # Set environment variable
        monkeypatch.setenv("ENVIRONMENT", "staging")
        
        # Reload the module to apply the environment variable
        importlib.reload(sys.modules["src.config.logging_config"])
        from src.config.logging_config import LOG_LEVEL, LOGGING_CONFIG
        
        # Check log level
        assert LOG_LEVEL == logging.INFO
        
        # Check console formatter in staging (should be JSON)
        assert LOGGING_CONFIG["handlers"]["console"]["formatter"] == "json"
        
        # Check that file handlers are used for service loggers in staging
        service_logger = LOGGING_CONFIG["loggers"]["ocr_service"]
        assert set(service_logger["handlers"]) == {"console", "file", "error_file"}

    @pytest.mark.parametrize("env_vars", [Environment.PRODUCTION], indirect=True)
    def test_production_logging_config(self, env_vars, monkeypatch):
        """Test logging configuration in production environment."""
        # Set environment variable
        monkeypatch.setenv("ENVIRONMENT", "production")
        
        # Reload the module to apply the environment variable
        importlib.reload(sys.modules["src.config.logging_config"])
        from src.config.logging_config import LOG_LEVEL, LOGGING_CONFIG
        
        # Check log level
        assert LOG_LEVEL == logging.INFO
        
        # Check console formatter in production (should be JSON)
        assert LOGGING_CONFIG["handlers"]["console"]["formatter"] == "json"
        
        # Check that file handlers are used for service loggers in production
        service_logger = LOGGING_CONFIG["loggers"]["ocr_service"]
        assert set(service_logger["handlers"]) == {"console", "file", "error_file"}
        
        # Check that TensorFlow logger is set to WARNING level
        tf_logger = LOGGING_CONFIG["loggers"]["tensorflow"]
        assert tf_logger["level"] == logging.WARNING

    def test_log_format_configuration(self):
        """Test log format configuration."""
        # Check standard formatter format string
        standard_format = LOGGING_CONFIG["formatters"]["standard"]["format"]
        assert "%(asctime)s" in standard_format
        assert "%(levelname)s" in standard_format
        assert "%(name)s" in standard_format
        
        # Check that JSON formatter is used for non-development environments
        with patch("src.config.logging_config.ENVIRONMENT", "development"):
            importlib.reload(sys.modules["src.config.logging_config"])
            from src.config.logging_config import LOGGING_CONFIG as DEV_CONFIG
            assert DEV_CONFIG["handlers"]["console"]["formatter"] == "standard"
        
        with patch("src.config.logging_config.ENVIRONMENT", "production"):
            importlib.reload(sys.modules["src.config.logging_config"])
            from src.config.logging_config import LOGGING_CONFIG as PROD_CONFIG
            assert PROD_CONFIG["handlers"]["console"]["formatter"] == "json"