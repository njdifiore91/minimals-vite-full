#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's logging_config.py module.

These tests verify that logging configuration correctly sets up log levels,
formats, handlers, and context enrichment based on the environment.
Ensures that logging works correctly for monitoring, debugging, and troubleshooting.
"""

import os
import sys
import json
import logging
import pytest
from unittest.mock import patch, MagicMock, call
from io import StringIO
from logging.handlers import RotatingFileHandler
from datetime import datetime

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
    ENVIRONMENT,
    DEFAULT_LOG_LEVELS,
    DEFAULT_LOG_LEVEL
)


# ===== Fixtures =====

@pytest.fixture
def mock_environment():
    """Fixture to mock environment variables for testing."""
    original_environ = os.environ.copy()
    os.environ["ENVIRONMENT"] = "test"
    os.environ["LOG_DIR"] = "/tmp/document-service-test-logs"
    yield
    os.environ.clear()
    os.environ.update(original_environ)


@pytest.fixture
def mock_log_dir(tmpdir):
    """Fixture to create a temporary log directory for testing."""
    log_dir = tmpdir.mkdir("logs")
    with patch("src.config.logging_config.LOG_DIR", str(log_dir)):
        yield str(log_dir)


@pytest.fixture
def captured_logs():
    """Fixture to capture log output for testing."""
    handler = StringIO()
    logger = logging.getLogger()
    original_handlers = logger.handlers.copy()
    original_level = logger.level
    
    # Remove existing handlers and add our test handler
    for h in logger.handlers:
        logger.removeHandler(h)
    
    stream_handler = logging.StreamHandler(handler)
    logger.addHandler(stream_handler)
    logger.setLevel(logging.DEBUG)
    
    yield handler
    
    # Restore original handlers and level
    for h in logger.handlers:
        logger.removeHandler(h)
    
    for h in original_handlers:
        logger.addHandler(h)
    
    logger.setLevel(original_level)


@pytest.fixture
def environment_patches():
    """Fixture to patch environment-specific settings for testing."""
    patches = {
        "development": patch("src.config.logging_config.ENVIRONMENT", "development"),
        "staging": patch("src.config.logging_config.ENVIRONMENT", "staging"),
        "production": patch("src.config.logging_config.ENVIRONMENT", "production"),
        "test": patch("src.config.logging_config.ENVIRONMENT", "test")
    }
    
    yield patches


# ===== Tests for Constants and Environment Settings =====

def test_service_name_constant():
    """Test that the SERVICE_NAME constant is correctly defined."""
    assert SERVICE_NAME == "document-service"
    assert isinstance(SERVICE_NAME, str)


def test_log_dir_default():
    """Test that the LOG_DIR has a default value if not set in environment."""
    with patch.dict(os.environ, {}, clear=True):
        # Re-import to reset constants
        from importlib import reload
        from src.config import logging_config
        reload(logging_config)
        
        assert logging_config.LOG_DIR == "/var/log/document-service"


def test_environment_default():
    """Test that the ENVIRONMENT has a default value if not set in environment."""
    with patch.dict(os.environ, {}, clear=True):
        # Re-import to reset constants
        from importlib import reload
        from src.config import logging_config
        reload(logging_config)
        
        assert logging_config.ENVIRONMENT == "development"


def test_default_log_levels():
    """Test that DEFAULT_LOG_LEVELS contains correct log levels for each environment."""
    assert DEFAULT_LOG_LEVELS["development"] == logging.DEBUG
    assert DEFAULT_LOG_LEVELS["staging"] == logging.INFO
    assert DEFAULT_LOG_LEVELS["production"] == logging.INFO
    
    # Verify the default log level is set correctly based on environment
    with patch("src.config.logging_config.ENVIRONMENT", "development"):
        from importlib import reload
        from src.config import logging_config
        reload(logging_config)
        assert logging_config.DEFAULT_LOG_LEVEL == logging.DEBUG
    
    with patch("src.config.logging_config.ENVIRONMENT", "staging"):
        from importlib import reload
        from src.config import logging_config
        reload(logging_config)
        assert logging_config.DEFAULT_LOG_LEVEL == logging.INFO
    
    with patch("src.config.logging_config.ENVIRONMENT", "production"):
        from importlib import reload
        from src.config import logging_config
        reload(logging_config)
        assert logging_config.DEFAULT_LOG_LEVEL == logging.INFO


# ===== Tests for ContextFilter =====

def test_context_filter_initialization():
    """Test that ContextFilter is initialized with the correct service name."""
    context_filter = ContextFilter("test-service")
    assert context_filter.service_name == "test-service"


def test_context_filter_adds_service_name():
    """Test that ContextFilter adds service name to log records."""
    context_filter = ContextFilter("test-service")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    context_filter.filter(record)
    
    # Check that service name was added
    assert hasattr(record, "service")
    assert record.service == "test-service"


def test_context_filter_adds_environment():
    """Test that ContextFilter adds environment to log records."""
    with patch("src.config.logging_config.ENVIRONMENT", "test-env"):
        context_filter = ContextFilter("test-service")
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        # Apply the filter
        context_filter.filter(record)
        
        # Check that environment was added
        assert hasattr(record, "environment")
        assert record.environment == "test-env"


def test_context_filter_adds_correlation_id():
    """Test that ContextFilter adds correlation ID to log records if available."""
    context_filter = ContextFilter("test-service")
    
    # Create a record with correlation_id
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.correlation_id = "test-correlation-id"
    
    # Apply the filter
    context_filter.filter(record)
    
    # Check that correlation_id was preserved
    assert record.correlation_id == "test-correlation-id"
    
    # Create a record without correlation_id
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    context_filter.filter(record)
    
    # Check that default correlation_id was added
    assert record.correlation_id == "-"


def test_context_filter_adds_request_id():
    """Test that ContextFilter adds request ID to log records if available."""
    context_filter = ContextFilter("test-service")
    
    # Create a record with request_id
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.request_id = "test-request-id"
    
    # Apply the filter
    context_filter.filter(record)
    
    # Check that request_id was preserved
    assert record.request_id == "test-request-id"
    
    # Create a record without request_id
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Apply the filter
    context_filter.filter(record)
    
    # Check that default request_id was added
    assert record.request_id == "-"


# ===== Tests for CustomJsonFormatter =====

def test_custom_json_formatter_initialization():
    """Test that CustomJsonFormatter is initialized correctly."""
    formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(message)s")
    assert isinstance(formatter, CustomJsonFormatter)


def test_custom_json_formatter_adds_timestamp():
    """Test that CustomJsonFormatter adds timestamp to log records."""
    formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Format the record
    log_record = {}
    formatter.add_fields(log_record, record, {})
    
    # Check that timestamp was added
    assert "timestamp" in log_record
    # Verify timestamp format (ISO 8601)
    try:
        datetime.fromisoformat(log_record["timestamp"])
        timestamp_valid = True
    except ValueError:
        timestamp_valid = False
    assert timestamp_valid


def test_custom_json_formatter_adds_level():
    """Test that CustomJsonFormatter adds log level to log records."""
    formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    
    # Format the record
    log_record = {}
    formatter.add_fields(log_record, record, {})
    
    # Check that level was added
    assert "level" in log_record
    assert log_record["level"] == "INFO"


def test_custom_json_formatter_adds_service():
    """Test that CustomJsonFormatter adds service name to log records."""
    formatter = CustomJsonFormatter("%(timestamp)s %(level)s %(service)s %(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.service = "test-service"
    
    # Format the record
    log_record = {}
    formatter.add_fields(log_record, record, {})
    
    # Check that service was added
    assert "service" in log_record
    assert log_record["service"] == "test-service"


def test_custom_json_formatter_adds_context_fields():
    """Test that CustomJsonFormatter adds all context fields to log records."""
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(service)s %(environment)s "
        "%(correlation_id)s %(request_id)s %(message)s"
    )
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Test message",
        args=(),
        exc_info=None
    )
    record.service = "test-service"
    record.environment = "test-env"
    record.correlation_id = "test-correlation-id"
    record.request_id = "test-request-id"
    
    # Format the record
    log_record = {}
    formatter.add_fields(log_record, record, {})
    
    # Check that all context fields were added
    assert "service" in log_record
    assert log_record["service"] == "test-service"
    assert "environment" in log_record
    assert log_record["environment"] == "test-env"
    assert "correlation_id" in log_record
    assert log_record["correlation_id"] == "test-correlation-id"
    assert "request_id" in log_record
    assert log_record["request_id"] == "test-request-id"
    
    # Check that process and thread info was added
    assert "pid" in log_record
    assert "thread" in log_record


# ===== Tests for Handler Functions =====

def test_get_console_handler():
    """Test that get_console_handler returns a properly configured console handler."""
    with patch("src.config.logging_config.get_formatter") as mock_get_formatter:
        mock_formatter = MagicMock()
        mock_get_formatter.return_value = mock_formatter
        
        handler = get_console_handler()
        
        # Check that handler is a StreamHandler
        assert isinstance(handler, logging.StreamHandler)
        
        # Check that formatter was set
        assert handler.formatter == mock_formatter
        
        # Check that handler outputs to stdout
        assert handler.stream == sys.stdout


def test_get_file_handler(mock_log_dir):
    """Test that get_file_handler returns a properly configured file handler."""
    with patch("src.config.logging_config.get_formatter") as mock_get_formatter:
        mock_formatter = MagicMock()
        mock_get_formatter.return_value = mock_formatter
        
        handler = get_file_handler()
        
        # Check that handler is a RotatingFileHandler
        assert isinstance(handler, RotatingFileHandler)
        
        # Check that formatter was set
        assert handler.formatter == mock_formatter
        
        # Check that handler has correct file path
        expected_path = os.path.join(mock_log_dir, f"{SERVICE_NAME}.log")
        assert handler.baseFilename == expected_path
        
        # Check rotation settings
        assert handler.maxBytes == 10 * 1024 * 1024  # 10MB
        assert handler.backupCount == 5


def test_get_formatter():
    """Test that get_formatter returns a properly configured JSON formatter."""
    formatter = get_formatter()
    
    # Check that formatter is a CustomJsonFormatter
    assert isinstance(formatter, CustomJsonFormatter)
    
    # Check that formatter has the correct format string
    expected_format = (
        '%(timestamp)s %(level)s %(name)s %(service)s '
        '%(environment)s %(correlation_id)s %(request_id)s '
        '%(message)s %(pathname)s %(lineno)d'
    )
    assert formatter._fmt == expected_format


# ===== Tests for get_logger Function =====

def test_get_logger_creates_new_logger():
    """Test that get_logger creates a new logger with the correct name."""
    with patch("src.config.logging_config.get_console_handler") as mock_get_console_handler, \
         patch("src.config.logging_config.get_file_handler") as mock_get_file_handler, \
         patch("src.config.logging_config.ContextFilter") as mock_context_filter_class:
        
        # Set up mocks
        mock_console_handler = MagicMock()
        mock_get_console_handler.return_value = mock_console_handler
        
        mock_file_handler = MagicMock()
        mock_get_file_handler.return_value = mock_file_handler
        
        mock_context_filter = MagicMock()
        mock_context_filter_class.return_value = mock_context_filter
        
        # Call the function
        logger = get_logger("test_logger")
        
        # Check that logger has the correct name
        assert logger.name == "test_logger"
        
        # Check that logger has the correct level
        assert logger.level == DEFAULT_LOG_LEVEL
        
        # Check that context filter was added
        mock_context_filter_class.assert_called_once_with(SERVICE_NAME)
        logger.addFilter.assert_called_once_with(mock_context_filter)
        
        # Check that console handler was added
        mock_get_console_handler.assert_called_once()
        logger.addHandler.assert_any_call(mock_console_handler)
        
        # Check that propagation is disabled
        assert logger.propagate is False


def test_get_logger_adds_file_handler_in_non_development():
    """Test that get_logger adds a file handler in non-development environments."""
    environments = ["staging", "production", "test"]
    
    for env in environments:
        with patch("src.config.logging_config.ENVIRONMENT", env), \
             patch("src.config.logging_config.get_console_handler") as mock_get_console_handler, \
             patch("src.config.logging_config.get_file_handler") as mock_get_file_handler, \
             patch("src.config.logging_config.ContextFilter") as mock_context_filter_class:
            
            # Set up mocks
            mock_console_handler = MagicMock()
            mock_get_console_handler.return_value = mock_console_handler
            
            mock_file_handler = MagicMock()
            mock_get_file_handler.return_value = mock_file_handler
            
            mock_context_filter = MagicMock()
            mock_context_filter_class.return_value = mock_context_filter
            
            # Call the function
            logger = get_logger(f"test_logger_{env}")
            
            # Check that file handler was added
            mock_get_file_handler.assert_called_once()
            logger.addHandler.assert_any_call(mock_file_handler)


def test_get_logger_skips_file_handler_in_development():
    """Test that get_logger skips adding a file handler in development environment."""
    with patch("src.config.logging_config.ENVIRONMENT", "development"), \
         patch("src.config.logging_config.get_console_handler") as mock_get_console_handler, \
         patch("src.config.logging_config.get_file_handler") as mock_get_file_handler, \
         patch("src.config.logging_config.ContextFilter") as mock_context_filter_class:
        
        # Set up mocks
        mock_console_handler = MagicMock()
        mock_get_console_handler.return_value = mock_console_handler
        
        mock_context_filter = MagicMock()
        mock_context_filter_class.return_value = mock_context_filter
        
        # Call the function
        logger = get_logger("test_logger_dev")
        
        # Check that file handler was not added
        mock_get_file_handler.assert_not_called()
        
        # Check that only console handler was added
        assert logger.addHandler.call_count == 1
        logger.addHandler.assert_called_once_with(mock_console_handler)


def test_get_logger_reuses_existing_logger():
    """Test that get_logger reuses an existing logger if it already has handlers."""
    # Create a logger with handlers
    logger_name = "test_logger_reuse"
    existing_logger = logging.getLogger(logger_name)
    existing_logger.addHandler(logging.NullHandler())
    
    with patch("src.config.logging_config.get_console_handler") as mock_get_console_handler, \
         patch("src.config.logging_config.get_file_handler") as mock_get_file_handler, \
         patch("src.config.logging_config.ContextFilter") as mock_context_filter_class:
        
        # Call the function
        logger = get_logger(logger_name)
        
        # Check that no new handlers or filters were added
        mock_get_console_handler.assert_not_called()
        mock_get_file_handler.assert_not_called()
        mock_context_filter_class.assert_not_called()
        
        # Check that the existing logger was returned
        assert logger is existing_logger
    
    # Clean up
    existing_logger.handlers = []


# ===== Tests for configure_logging Function =====

def test_configure_logging_applies_dict_config():
    """Test that configure_logging applies the correct logging configuration."""
    with patch("logging.config.dictConfig") as mock_dict_config, \
         patch("src.config.logging_config.get_logger") as mock_get_logger:
        
        # Set up mocks
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Call the function
        configure_logging()
        
        # Check that dictConfig was called with the correct configuration
        mock_dict_config.assert_called_once()
        config = mock_dict_config.call_args[0][0]
        
        # Check basic structure of the configuration
        assert config["version"] == 1
        assert config["disable_existing_loggers"] is False
        assert "formatters" in config
        assert "filters" in config
        assert "handlers" in config
        assert "loggers" in config
        
        # Check formatters
        assert "json" in config["formatters"]
        assert "standard" in config["formatters"]
        
        # Check filters
        assert "context_filter" in config["filters"]
        
        # Check handlers
        assert "console" in config["handlers"]
        assert "file" in config["handlers"]
        assert "error_file" in config["handlers"]
        
        # Check loggers
        assert "" in config["loggers"]  # Root logger
        assert "document_service" in config["loggers"]
        
        # Check that startup message was logged
        mock_get_logger.assert_called_once_with("src.config.logging_config")
        mock_logger.info.assert_called_once()


def test_configure_logging_sets_environment_specific_handlers():
    """Test that configure_logging sets environment-specific handlers."""
    environments = {
        "development": ["console"],
        "staging": ["console", "file", "error_file"],
        "production": ["console", "file", "error_file"]
    }
    
    for env, expected_handlers in environments.items():
        with patch("src.config.logging_config.ENVIRONMENT", env), \
             patch("logging.config.dictConfig") as mock_dict_config, \
             patch("src.config.logging_config.get_logger"):
            
            # Call the function
            configure_logging()
            
            # Check that dictConfig was called with the correct configuration
            config = mock_dict_config.call_args[0][0]
            
            # Check that document_service logger has the correct handlers
            if env == "development":
                assert config["loggers"]["document_service"]["handlers"] == ["console"]
            else:
                assert set(config["loggers"]["document_service"]["handlers"]) == set(["console", "file", "error_file"])


# ===== Tests for LoggingContext =====

def test_logging_context_initialization():
    """Test that LoggingContext is initialized with the correct context data."""
    context_data = {"correlation_id": "test-correlation-id", "request_id": "test-request-id"}
    context = LoggingContext(**context_data)
    
    # Check that context data was stored
    assert context.context_data == context_data
    assert context.old_context == {}


def test_logging_context_enter_exit():
    """Test that LoggingContext correctly sets and restores context on enter/exit."""
    # Create a class with a logger attribute to simulate a class using the context manager
    class TestClass:
        def __init__(self):
            self.logger = MagicMock()
            self.logger.correlation_id = "old-correlation-id"
            self.logger.request_id = "old-request-id"
    
    # Create an instance of the test class
    test_instance = TestClass()
    
    # Create a context with new values
    context_data = {"correlation_id": "new-correlation-id", "request_id": "new-request-id"}
    
    # Use the context manager
    with patch("sys._getframe") as mock_getframe:
        # Mock the frame to return our test instance
        mock_frame = MagicMock()
        mock_frame.f_locals = {"self": test_instance}
        mock_frame.f_back = None
        mock_getframe.return_value = mock_frame
        
        # Enter the context
        with LoggingContext(**context_data):
            # Check that context was set
            assert test_instance.logger.correlation_id == "new-correlation-id"
            assert test_instance.logger.request_id == "new-request-id"
        
        # Check that context was restored on exit
        assert test_instance.logger.correlation_id == "old-correlation-id"
        assert test_instance.logger.request_id == "old-request-id"


def test_logging_context_with_new_attributes():
    """Test that LoggingContext correctly handles attributes that don't exist yet."""
    # Create a class with a logger attribute to simulate a class using the context manager
    class TestClass:
        def __init__(self):
            self.logger = MagicMock()
            # No existing attributes
    
    # Create an instance of the test class
    test_instance = TestClass()
    
    # Create a context with new values
    context_data = {"correlation_id": "new-correlation-id", "request_id": "new-request-id"}
    
    # Use the context manager
    with patch("sys._getframe") as mock_getframe:
        # Mock the frame to return our test instance
        mock_frame = MagicMock()
        mock_frame.f_locals = {"self": test_instance}
        mock_frame.f_back = None
        mock_getframe.return_value = mock_frame
        
        # Enter the context
        with LoggingContext(**context_data):
            # Check that context was set
            assert test_instance.logger.correlation_id == "new-correlation-id"
            assert test_instance.logger.request_id == "new-request-id"
        
        # Check that attributes were removed on exit
        assert not hasattr(test_instance.logger, "correlation_id")
        assert not hasattr(test_instance.logger, "request_id")


# ===== Integration Tests =====

def test_logging_integration(captured_logs, mock_log_dir):
    """Test that logging works correctly in an integrated way."""
    # Configure logging
    with patch("src.config.logging_config.ENVIRONMENT", "test"):
        configure_logging()
    
    # Get a logger
    logger = get_logger("test_integration")
    
    # Log messages at different levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Check that messages were logged
    log_output = captured_logs.getvalue()
    assert "Debug message" in log_output
    assert "Info message" in log_output
    assert "Warning message" in log_output
    assert "Error message" in log_output


def test_logging_with_context(captured_logs):
    """Test that logging works correctly with context enrichment."""
    # Configure logging
    with patch("src.config.logging_config.ENVIRONMENT", "test"):
        configure_logging()
    
    # Create a class that uses the LoggingContext
    class TestService:
        def __init__(self):
            self.logger = get_logger("test_service")
        
        def process_request(self, correlation_id, request_id):
            with LoggingContext(correlation_id=correlation_id, request_id=request_id):
                self.logger.info("Processing request")
    
    # Create an instance and process a request
    service = TestService()
    
    # Use the context manager
    with patch("sys._getframe") as mock_getframe:
        # Mock the frame to return our test instance in the context manager
        def side_effect(depth):
            frame = MagicMock()
            frame.f_locals = {"self": service}
            frame.f_back = None
            return frame
        
        mock_getframe.side_effect = side_effect
        
        # Process a request with context
        service.process_request("test-correlation-id", "test-request-id")
    
    # Check that the log message includes the context
    log_output = captured_logs.getvalue()
    assert "Processing request" in log_output
    assert "test-correlation-id" in log_output
    assert "test-request-id" in log_output