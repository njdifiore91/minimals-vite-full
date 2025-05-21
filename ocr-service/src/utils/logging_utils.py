#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Logging utilities for the OCR Service.

This module provides utility functions for structured logging in the OCR Service.
It exports functions for creating contextual log entries, formatting log messages,
and handling different log levels. It's essential for consistent logging across
the service and integrates with the logger configuration.
"""

import json
import logging
import os
import sys
import threading
import traceback
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Union

# Define log levels
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Thread-local storage for request context
_request_context = threading.local()


class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs logs in JSON format for machine readability."""

    def __init__(self, **kwargs):
        """Initialize the JSON formatter with optional fields to include."""
        self.default_fields = kwargs
        super().__init__()

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string.

        Args:
            record: The log record to format

        Returns:
            A JSON string representation of the log record
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": record.process,
            "thread_id": record.thread,
            "service": "ocr-service",
        }

        # Add request_id if available
        request_id = get_request_id()
        if request_id:
            log_data["request_id"] = request_id

        # Add default fields
        log_data.update(self.default_fields)

        # Add extra fields from the record
        if hasattr(record, "extra") and record.extra:
            log_data.update(record.extra)

        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": self.formatException(record.exc_info),
            }

        # Add stack info if available
        if record.stack_info:
            log_data["stack_info"] = self.formatStack(record.stack_info)

        return json.dumps(log_data)


class ContextAdapter(logging.LoggerAdapter):
    """Logger adapter that adds context information to log records."""

    def process(self, msg, kwargs):
        """Process the log message and add context information.

        Args:
            msg: The log message
            kwargs: Additional keyword arguments

        Returns:
            Tuple of (msg, kwargs) with context information added
        """
        # Ensure 'extra' exists in kwargs
        if "extra" not in kwargs:
            kwargs["extra"] = {}

        # Add request_id to extra if available
        request_id = get_request_id()
        if request_id:
            kwargs["extra"]["request_id"] = request_id

        # Add any additional context from the adapter
        if hasattr(self, "extra") and self.extra:
            kwargs["extra"].update(self.extra)

        return msg, kwargs


def get_request_id() -> Optional[str]:
    """Get the current request ID from thread-local storage.

    Returns:
        The current request ID or None if not set
    """
    return getattr(_request_context, "request_id", None)


def set_request_id(request_id: Optional[str] = None) -> str:
    """Set the request ID in thread-local storage.

    Args:
        request_id: The request ID to set, or None to generate a new one

    Returns:
        The request ID that was set
    """
    if request_id is None:
        request_id = str(uuid.uuid4())
    _request_context.request_id = request_id
    return request_id


def clear_request_id() -> None:
    """Clear the request ID from thread-local storage."""
    if hasattr(_request_context, "request_id"):
        delattr(_request_context, "request_id")


@contextmanager
def request_context(request_id: Optional[str] = None) -> None:
    """Context manager for setting and clearing request ID.

    Args:
        request_id: The request ID to set, or None to generate a new one

    Yields:
        None
    """
    previous_id = get_request_id()
    try:
        set_request_id(request_id)
        yield
    finally:
        if previous_id:
            set_request_id(previous_id)
        else:
            clear_request_id()


def configure_logger(
    name: str,
    level: Union[str, int] = "INFO",
    json_format: bool = True,
    console_output: bool = True,
    log_file: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None,
) -> logging.Logger:
    """Configure a logger with the specified settings.

    Args:
        name: The name of the logger
        level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Whether to use JSON formatting
        console_output: Whether to output logs to the console
        log_file: Path to a log file, or None for no file output
        extra_fields: Additional fields to include in every log entry

    Returns:
        A configured logger instance
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = LOG_LEVEL_MAP.get(level.upper(), logging.INFO)

    # Get or create the logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Clear existing handlers
    for handler in logger.handlers[:]:  # Make a copy of the list
        logger.removeHandler(handler)

    # Create formatter
    if json_format:
        formatter = JsonFormatter(**(extra_fields or {}))
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    # Add console handler if requested
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Add file handler if requested
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Wrap logger with context adapter
    return ContextAdapter(logger, extra_fields or {})


def get_logger(
    name: str, extra_context: Optional[Dict[str, Any]] = None
) -> logging.LoggerAdapter:
    """Get a logger with the specified name and context.

    This is a convenience function that gets a logger from the logging system
    and wraps it with a ContextAdapter to add context information.

    Args:
        name: The name of the logger
        extra_context: Additional context to include in log entries

    Returns:
        A logger adapter with context information
    """
    logger = logging.getLogger(name)
    return ContextAdapter(logger, extra_context or {})


def log_exception(
    logger: Union[logging.Logger, logging.LoggerAdapter],
    message: str,
    exc_info: Optional[tuple] = None,
    level: int = logging.ERROR,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Log an exception with full traceback.

    Args:
        logger: The logger to use
        message: The log message
        exc_info: Exception info tuple from sys.exc_info(), or None to use current exception
        level: The log level to use
        extra: Additional context to include in the log entry
    """
    if exc_info is None:
        exc_info = sys.exc_info()

    if extra is None:
        extra = {}

    # Add exception details to extra
    if exc_info and exc_info[0] is not None:
        extra["exception_type"] = exc_info[0].__name__
        extra["exception_message"] = str(exc_info[1])

    # Log with exception info
    logger.log(level, message, exc_info=exc_info, extra=extra)


def log_with_context(
    logger: Union[logging.Logger, logging.LoggerAdapter],
    level: int,
    message: str,
    context: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a message with additional context.

    Args:
        logger: The logger to use
        level: The log level to use
        message: The log message
        context: Additional context to include in the log entry
    """
    logger.log(level, message, extra=context)


def get_environment_log_level() -> int:
    """Get the log level from the environment or default to INFO.

    Returns:
        The log level as an integer
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    return LOG_LEVEL_MAP.get(log_level, logging.INFO)


def setup_root_logger(
    level: Optional[Union[str, int]] = None,
    json_format: bool = True,
    service_name: str = "ocr-service",
) -> logging.Logger:
    """Set up the root logger with the specified configuration.

    Args:
        level: The log level to use, or None to use the environment log level
        json_format: Whether to use JSON formatting
        service_name: The name of the service to include in log entries

    Returns:
        The configured root logger
    """
    if level is None:
        level = get_environment_log_level()

    return configure_logger(
        name="root",
        level=level,
        json_format=json_format,
        console_output=True,
        extra_fields={"service": service_name},
    )


def log_function_call(
    logger: Union[logging.Logger, logging.LoggerAdapter],
    level: int = logging.DEBUG,
) -> Callable:
    """Decorator to log function calls with arguments and return values.

    Args:
        logger: The logger to use
        level: The log level to use

    Returns:
        A decorator function
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            module_name = func.__module__

            # Log function call with arguments
            arg_str = ", ".join(
                [str(arg) for arg in args]
                + [f"{k}={v}" for k, v in kwargs.items()]
            )
            logger.log(
                level,
                f"Calling {module_name}.{func_name}({arg_str})",
                extra={"function_call": {"name": func_name, "module": module_name}},
            )

            try:
                # Call the function
                result = func(*args, **kwargs)

                # Log the result
                logger.log(
                    level,
                    f"{module_name}.{func_name} returned: {result}",
                    extra={
                        "function_return": {
                            "name": func_name,
                            "module": module_name,
                            "result": str(result),
                        }
                    },
                )

                return result
            except Exception as e:
                # Log the exception
                log_exception(
                    logger,
                    f"{module_name}.{func_name} raised exception: {str(e)}",
                    extra={
                        "function_exception": {
                            "name": func_name,
                            "module": module_name,
                        }
                    },
                )
                raise

        return wrapper

    return decorator


def log_execution_time(
    logger: Union[logging.Logger, logging.LoggerAdapter],
    level: int = logging.DEBUG,
) -> Callable:
    """Decorator to log function execution time.

    Args:
        logger: The logger to use
        level: The log level to use

    Returns:
        A decorator function
    """
    import time

    def decorator(func):
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            module_name = func.__module__

            # Record start time
            start_time = time.time()

            try:
                # Call the function
                result = func(*args, **kwargs)

                # Calculate execution time
                execution_time = time.time() - start_time

                # Log execution time
                logger.log(
                    level,
                    f"{module_name}.{func_name} executed in {execution_time:.6f} seconds",
                    extra={
                        "execution_time": {
                            "name": func_name,
                            "module": module_name,
                            "seconds": execution_time,
                        }
                    },
                )

                return result
            except Exception as e:
                # Calculate execution time even for exceptions
                execution_time = time.time() - start_time

                # Log execution time with exception
                logger.log(
                    logging.ERROR,
                    f"{module_name}.{func_name} failed after {execution_time:.6f} seconds: {str(e)}",
                    extra={
                        "execution_time": {
                            "name": func_name,
                            "module": module_name,
                            "seconds": execution_time,
                            "error": str(e),
                        }
                    },
                )
                raise

        return wrapper

    return decorator


def format_stack_trace(stack_trace: List[str]) -> str:
    """Format a stack trace for logging.

    Args:
        stack_trace: The stack trace as a list of strings

    Returns:
        A formatted stack trace string
    """
    return "\n".join(stack_trace)


def get_current_stack_trace() -> str:
    """Get the current stack trace as a formatted string.

    Returns:
        A formatted stack trace string
    """
    stack = traceback.format_stack()
    # Remove the last two frames (this function and its caller)
    return format_stack_trace(stack[:-2])


def log_critical_error(
    logger: Union[logging.Logger, logging.LoggerAdapter],
    message: str,
    exc_info: Optional[tuple] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Log a critical error with full context and notify monitoring systems.

    Args:
        logger: The logger to use
        message: The log message
        exc_info: Exception info tuple from sys.exc_info(), or None to use current exception
        extra: Additional context to include in the log entry
    """
    if exc_info is None and sys.exc_info()[0] is not None:
        exc_info = sys.exc_info()

    if extra is None:
        extra = {}

    # Add alert flag for monitoring systems
    extra["alert"] = True
    extra["stack_trace"] = get_current_stack_trace()

    # Log with exception info
    logger.critical(message, exc_info=exc_info, extra=extra)

    # Here you could add additional alerting mechanisms
    # such as sending an email, SMS, or calling a webhook