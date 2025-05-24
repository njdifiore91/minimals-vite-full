#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's logging_config.py module.

These tests verify that logging configuration correctly sets up log levels,
formats, handlers, and context enrichment based on the environment. This ensures
that logging works correctly for monitoring, debugging, and troubleshooting.

Test coverage includes:
- Log level configuration based on environment
- Log format configuration with timestamp and context information
- Console and file handler setup
- Context enrichment for request tracking
- Logging configuration validation
"""

import os
import sys
import json
import logging
import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
from io import StringIO

# Import the module to test
from src.config.logging_config import (
    configure_logging,
    get_logger,
    get_console_handler,
    get_file_handler,
    get_formatter,
    ContextFilter,
    CustomJsonFormatter,
    LoggingContext,
    SERVICE_NAME,
    LOG_DIR,
    DEFAULT_LOG_LEVELS,
    DEFAULT_LOG_LEVEL
)


# ===== Test Environment-Based Log Level Configuration =====

@pytest.mark.parametrize(
    "environment,expected_level",
    [
        ("development", logging.DEBUG),
        ("staging", logging.INFO),
        ("production", logging.INFO),
        # Test fallback to INFO for unknown environment
        ("unknown", logging.INFO),
    ],
)
def test_default_log_levels(environment, expected_level):
    """Test that log levels are correctly set based on environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": environment}):
        # Reload the module to apply environment changes
        import importlib
        import src.config.logging_config
        importlib.reload(src.config.logging_config)
        
        # Verify the default log level
        assert src.config.logging_config.DEFAULT_LOG_LEVEL == expected_level


# ===== Test Logger Creation =====

def test_get_logger_development():
    """Test that get_logger correctly configures a logger in development environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
        # Mock the handlers to avoid actual logging
        with patch("src.config.logging_config.get_console_handler") as mock_console_handler, \
             patch("src.config.logging_config.get_file_handler") as mock_file_handler:
            
            # Create mock handlers
            mock_console = MagicMock()
            mock_console_handler.return_value = mock_console
            mock_file = MagicMock()
            mock_file_handler.return_value = mock_file
            
            # Get a logger
            logger = get_logger("test_logger")
            
            # Verify logger configuration
            assert logger.level == logging.DEBUG
            assert logger.propagate is False
            
            # Verify handlers
            mock_console_handler.assert_called_once()
            logger.addHandler.assert_called_with(mock_console)
            
            # Verify file handler is not added in development
            mock_file_handler.assert_not_called()


def test_get_logger_production():
    """Test that get_logger correctly configures a logger in production environment."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
        # Mock the handlers to avoid actual logging
        with patch("src.config.logging_config.get_console_handler") as mock_console_handler, \
             patch("src.config.logging_config.get_file_handler") as mock_file_handler:
            
            # Create mock handlers
            mock_console = MagicMock()
            mock_console_handler.return_value = mock_console
            mock_file = MagicMock()
            mock_file_handler.return_value = mock_file
            
            # Get a logger
            logger = get_logger("test_logger")
            
            # Verify logger configuration
            assert logger.level == logging.INFO
            assert logger.propagate is False
            
            # Verify handlers
            mock_console_handler.assert_called_once()
            mock_file_handler.assert_called_once()
            
            # Verify both handlers are added
            assert logger.addHandler.call_count == 2
            logger.addHandler.assert_has_calls([
                call(mock_console),
                call(mock_file)
            ], any_order=True)


def test_get_logger_already_configured():
    """Test that get_logger doesn't reconfigure an already configured logger."""
    # Create a logger with a handler
    logger_name = "test_already_configured"
    logger = logging.getLogger(logger_name)
    handler = logging.StreamHandler()
    logger.addHandler(handler)
    
    # Call get_logger
    with patch("src.config.logging_config.get_console_handler") as mock_console_handler, \
         patch("src.config.logging_config.get_file_handler") as mock_file_handler:
        
        result_logger = get_logger(logger_name)
        
        # Verify that the logger wasn't reconfigured
        assert result_logger is logger
        mock_console_handler.assert_not_called()
        mock_file_handler.assert_not_called()


# ===== Test Handler Configuration =====

def test_get_console_handler():
    """Test that get_console_handler correctly configures a console handler."""
    with patch("src.config.logging_config.get_formatter") as mock_get_formatter:
        # Create a mock formatter
        mock_formatter = MagicMock()
        mock_get_formatter.return_value = mock_formatter
        
        # Get a console handler
        handler = get_console_handler()
        
        # Verify handler configuration
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stdout
        mock_get_formatter.assert_called_once()
        assert handler.formatter == mock_formatter


def test_get_file_handler():
    """Test that get_file_handler correctly configures a file handler."""
    with patch("src.config.logging_config.get_formatter") as mock_get_formatter, \
         patch("src.config.logging_config.os.path.join") as mock_join, \
         patch("logging.handlers.RotatingFileHandler") as mock_handler_class:
        
        # Create mocks
        mock_formatter = MagicMock()
        mock_get_formatter.return_value = mock_formatter
        mock_join.return_value = "/var/log/document-service/document-service.log"
        mock_handler = MagicMock()
        mock_handler_class.return_value = mock_handler
        
        # Get a file handler
        handler = get_file_handler()
        
        # Verify handler configuration
        mock_join.assert_called_once_with(LOG_DIR, f"{SERVICE_NAME}.log")
        mock_handler_class.assert_called_once_with(
            "/var/log/document-service/document-service.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        mock_get_formatter.assert_called_once()
        mock_handler.setFormatter.assert_called_once_with(mock_formatter)
        assert handler == mock_handler


def test_get_formatter():
    """Test that get_formatter correctly creates a JSON formatter."""
    # Get a formatter
    formatter = get_formatter()
    
    # Verify formatter configuration
    assert isinstance(formatter, CustomJsonFormatter)
    assert '%(timestamp)s %(level)s %(name)s %(service)s' in formatter._fmt
    assert '%(environment)s %(correlation_id)s %(request_id)s' in formatter._fmt
    assert '%(message)s %(pathname)s %(lineno)d' in formatter._fmt


# ===== Test Context Filter =====

def test_context_filter():
    """Test that ContextFilter correctly adds context to log records."""
    # Create a context filter
    filter_instance = ContextFilter("test-service")
    
    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    with patch.dict(os.environ, {"ENVIRONMENT": "testing"}):
        result = filter_instance.filter(record)
    
    # Verify filter result and record modifications
    assert result is True
    assert record.service == "test-service"
    assert record.environment == "testing"
    assert record.correlation_id == "-"
    assert record.request_id == "-"


def test_context_filter_with_existing_context():
    """Test that ContextFilter preserves existing context in log records."""
    # Create a context filter
    filter_instance = ContextFilter("test-service")
    
    # Create a log record with existing context
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.correlation_id = "test-correlation-id"
    record.request_id = "test-request-id"
    
    # Apply the filter
    result = filter_instance.filter(record)
    
    # Verify filter result and record modifications
    assert result is True
    assert record.service == "test-service"
    assert record.correlation_id == "test-correlation-id"  # Preserved
    assert record.request_id == "test-request-id"  # Preserved


# ===== Test Custom JSON Formatter =====

def test_custom_json_formatter():
    """Test that CustomJsonFormatter correctly formats log records as JSON."""
    # Create a formatter
    formatter = CustomJsonFormatter()
    
    # Create a log record
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.service = "test-service"
    record.environment = "testing"
    record.correlation_id = "test-correlation-id"
    record.request_id = "test-request-id"
    
    # Format the record
    formatted = formatter.format(record)
    
    # Parse the JSON
    log_data = json.loads(formatted)
    
    # Verify JSON fields
    assert log_data["level"] == "INFO"
    assert log_data["message"] == "Test message"
    assert log_data["service"] == "test-service"
    assert log_data["environment"] == "testing"
    assert log_data["correlation_id"] == "test-correlation-id"
    assert log_data["request_id"] == "test-request-id"
    assert "timestamp" in log_data
    assert "pid" in log_data
    assert "thread" in log_data


# ===== Test Logging Context Manager =====

def test_logging_context():
    """Test that LoggingContext correctly sets and restores context."""
    # Create a class with a logger
    class TestClass:
        def __init__(self):
            self.logger = MagicMock()
    
    # Create an instance
    test_instance = TestClass()
    
    # Use the context manager
    with patch("sys._getframe") as mock_getframe:
        # Mock the frame to return our test instance
        mock_frame = MagicMock()
        mock_frame.f_locals = {"self": test_instance}
        mock_frame.f_back = None
        mock_getframe.return_value = mock_frame
        
        # Use the context manager
        with LoggingContext(correlation_id="test-correlation-id", request_id="test-request-id"):
            # Verify context is set
            assert test_instance.logger.correlation_id == "test-correlation-id"
            assert test_instance.logger.request_id == "test-request-id"
        
        # Verify context is restored
        assert not hasattr(test_instance.logger, "correlation_id")
        assert not hasattr(test_instance.logger, "request_id")


def test_logging_context_with_existing_values():
    """Test that LoggingContext correctly restores existing context values."""
    # Create a class with a logger
    class TestClass:
        def __init__(self):
            self.logger = MagicMock()
            self.logger.correlation_id = "original-correlation-id"
            self.logger.request_id = "original-request-id"
    
    # Create an instance
    test_instance = TestClass()
    
    # Use the context manager
    with patch("sys._getframe") as mock_getframe:
        # Mock the frame to return our test instance
        mock_frame = MagicMock()
        mock_frame.f_locals = {"self": test_instance}
        mock_frame.f_back = None
        mock_getframe.return_value = mock_frame
        
        # Use the context manager
        with LoggingContext(correlation_id="test-correlation-id", request_id="test-request-id"):
            # Verify context is set
            assert test_instance.logger.correlation_id == "test-correlation-id"
            assert test_instance.logger.request_id == "test-request-id"
        
        # Verify context is restored to original values
        assert test_instance.logger.correlation_id == "original-correlation-id"
        assert test_instance.logger.request_id == "original-request-id"


# ===== Test Configure Logging =====

def test_configure_logging():
    """Test that configure_logging correctly sets up the logging system."""
    with patch("logging.config.dictConfig") as mock_dict_config, \
         patch("src.config.logging_config.get_logger") as mock_get_logger:
        
        # Create a mock logger
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call configure_logging
        configure_logging()
        
        # Verify logging configuration
        mock_dict_config.assert_called_once()
        config_dict = mock_dict_config.call_args[0][0]
        
        # Verify configuration structure
        assert config_dict["version"] == 1
        assert config_dict["disable_existing_loggers"] is False
        assert "formatters" in config_dict
        assert "filters" in config_dict
        assert "handlers" in config_dict
        assert "loggers" in config_dict
        
        # Verify formatters
        assert "json" in config_dict["formatters"]
        assert "standard" in config_dict["formatters"]
        
        # Verify filters
        assert "context_filter" in config_dict["filters"]
        assert config_dict["filters"]["context_filter"]["service_name"] == SERVICE_NAME
        
        # Verify handlers
        assert "console" in config_dict["handlers"]
        assert "file" in config_dict["handlers"]
        assert "error_file" in config_dict["handlers"]
        
        # Verify loggers
        assert "" in config_dict["loggers"]  # Root logger
        assert "document_service" in config_dict["loggers"]
        assert "scikit-learn" in config_dict["loggers"]
        assert "pika" in config_dict["loggers"]
        assert "requests" in config_dict["loggers"]
        
        # Verify startup message
        mock_get_logger.assert_called_once_with("src.config.logging_config")
        mock_logger.info.assert_called_once()


def test_configure_logging_development():
    """Test that configure_logging correctly sets up development logging."""
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
         patch("logging.config.dictConfig") as mock_dict_config:
        
        # Call configure_logging
        configure_logging()
        
        # Verify logging configuration
        mock_dict_config.assert_called_once()
        config_dict = mock_dict_config.call_args[0][0]
        
        # Verify development-specific configuration
        assert config_dict["handlers"]["console"]["formatter"] == "standard"
        assert config_dict["loggers"]["document_service"]["handlers"] == ["console"]
        assert config_dict["loggers"]["document_service"]["level"] == "DEBUG"


def test_configure_logging_production():
    """Test that configure_logging correctly sets up production logging."""
    with patch.dict(os.environ, {"ENVIRONMENT": "production"}), \
         patch("logging.config.dictConfig") as mock_dict_config:
        
        # Call configure_logging
        configure_logging()
        
        # Verify logging configuration
        mock_dict_config.assert_called_once()
        config_dict = mock_dict_config.call_args[0][0]
        
        # Verify production-specific configuration
        assert config_dict["handlers"]["console"]["formatter"] == "json"
        assert config_dict["loggers"]["document_service"]["handlers"] == ["console", "file", "error_file"]
        assert config_dict["loggers"]["document_service"]["level"] == "INFO"


# ===== Test Log Directory Creation =====

def test_log_directory_creation():
    """Test that the log directory is created if it doesn't exist."""
    with patch("os.makedirs") as mock_makedirs:
        # Reload the module to trigger directory creation
        import importlib
        import src.config.logging_config
        importlib.reload(src.config.logging_config)
        
        # Verify directory creation
        mock_makedirs.assert_called_once_with(LOG_DIR, exist_ok=True)


# ===== Test Integration =====

def test_logging_integration():
    """Test that the logging system works correctly end-to-end."""
    # Capture log output
    log_output = StringIO()
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    
    # Get a logger and log a message
    with patch.dict(os.environ, {"ENVIRONMENT": "development"}), \
         patch("src.config.logging_config.get_console_handler", return_value=MagicMock()), \
         patch("src.config.logging_config.get_file_handler", return_value=MagicMock()):
        
        logger = get_logger("test_integration")
        logger.info("Test message")
    
    # Verify log output
    log_output.seek(0)
    log_content = log_output.read()
    assert "INFO:test_integration:Test message" in log_content
    
    # Clean up
    root_logger.removeHandler(handler)