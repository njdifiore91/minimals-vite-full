#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging utilities for the Document Service.

This module provides utility functions for structured logging in the Document Service.
It includes functions for creating contextual log entries, formatting log messages,
and handling different log levels (ERROR, WARN, INFO, DEBUG).
"""

import json
import logging
import os
import sys
import traceback
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, Union

# Configure the default logger
logger = logging.getLogger("document_service")

# Define log levels
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARN": logging.WARNING,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}

# Default log level based on environment
DEFAULT_LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()


def configure_logging(level: Optional[str] = None) -> None:
    """
    Configure the logging system for the Document Service.
    
    Args:
        level: The log level to use. If not provided, uses the LOG_LEVEL environment
              variable or defaults to INFO.
    """
    log_level = level.upper() if level else DEFAULT_LOG_LEVEL
    numeric_level = LOG_LEVEL_MAP.get(log_level, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:  
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    
    # Create formatter
    formatter = JsonFormatter()
    console_handler.setFormatter(formatter)
    
    # Add handler to logger
    root_logger.addHandler(console_handler)
    
    logger.debug(
        "Logging configured", 
        extra={
            "log_level": log_level,
            "numeric_level": numeric_level
        }
    )


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    """
    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record as a JSON string.
        
        Args:
            record: The log record to format.
            
        Returns:
            A JSON string representation of the log record.
        """
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "document_service",
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add extra fields if they exist
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        # Add any extra context from the record
        if hasattr(record, "_extra"):
            for key, value in record._extra.items():
                log_data[key] = value
                
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": traceback.format_exception(*record.exc_info)
            }
            
        return json.dumps(log_data)


class RequestIdFilter(logging.Filter):
    """
    Filter that adds request_id to all log records.
    """
    def __init__(self, request_id: Optional[str] = None):
        super().__init__()
        self.request_id = request_id or str(uuid.uuid4())
        
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add request_id to the log record.
        
        Args:
            record: The log record to modify.
            
        Returns:
            Always returns True to include the record in the log output.
        """
        record.request_id = self.request_id
        return True


class ContextLogger:
    """
    Logger class that adds context to log messages.
    """
    def __init__(self, logger_name: str = "document_service", request_id: Optional[str] = None):
        """
        Initialize a new ContextLogger.
        
        Args:
            logger_name: The name of the logger to use.
            request_id: An optional request ID to include in all logs.
        """
        self.logger = logging.getLogger(logger_name)
        self.request_id = request_id or str(uuid.uuid4())
        self.context = {}
        
    def add_context(self, **kwargs) -> None:
        """
        Add context data to be included in all subsequent log messages.
        
        Args:
            **kwargs: Key-value pairs to add to the context.
        """
        self.context.update(kwargs)
        
    def remove_context(self, *keys) -> None:
        """
        Remove context data from the logger.
        
        Args:
            *keys: Keys to remove from the context.
        """
        for key in keys:
            self.context.pop(key, None)
            
    def _log(self, level: int, msg: str, *args, **kwargs) -> None:
        """
        Internal method to log a message with context.
        
        Args:
            level: The log level to use.
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        extra = kwargs.pop("extra", {})
        extra.update(self.context)
        
        # Add request_id to extra if not already present
        if "request_id" not in extra:
            extra["request_id"] = self.request_id
            
        # Store extra in a special attribute to avoid conflicts
        record_extra = {"_extra": extra}
        
        self.logger.log(level, msg, *args, extra=record_extra, **kwargs)
        
    def debug(self, msg: str, *args, **kwargs) -> None:
        """
        Log a debug message with context.
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self._log(logging.DEBUG, msg, *args, **kwargs)
        
    def info(self, msg: str, *args, **kwargs) -> None:
        """
        Log an info message with context.
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self._log(logging.INFO, msg, *args, **kwargs)
        
    def warning(self, msg: str, *args, **kwargs) -> None:
        """
        Log a warning message with context.
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self._log(logging.WARNING, msg, *args, **kwargs)
        
    def warn(self, msg: str, *args, **kwargs) -> None:
        """
        Alias for warning().
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self.warning(msg, *args, **kwargs)
        
    def error(self, msg: str, *args, **kwargs) -> None:
        """
        Log an error message with context.
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self._log(logging.ERROR, msg, *args, **kwargs)
        
    def critical(self, msg: str, *args, **kwargs) -> None:
        """
        Log a critical message with context.
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self._log(logging.CRITICAL, msg, *args, **kwargs)
        
    def exception(self, msg: str, *args, exc_info: bool = True, **kwargs) -> None:
        """
        Log an exception message with context and stack trace.
        
        Args:
            msg: The message to log.
            *args: Arguments to format the message with.
            exc_info: Whether to include exception info. Defaults to True.
            **kwargs: Additional keyword arguments to include in the log.
        """
        self._log(logging.ERROR, msg, *args, exc_info=exc_info, **kwargs)


def get_logger(name: Optional[str] = None, request_id: Optional[str] = None) -> ContextLogger:
    """
    Get a logger with context support.
    
    Args:
        name: The name of the logger. If not provided, uses the caller's module name.
        request_id: An optional request ID to include in all logs.
        
    Returns:
        A ContextLogger instance.
    """
    if name is None:
        # Get the caller's module name
        import inspect
        frame = inspect.currentframe()
        if frame:
            try:
                frame = frame.f_back
                if frame:
                    name = frame.f_globals.get("__name__")
            finally:
                del frame
    
    return ContextLogger(name or "document_service", request_id)


def with_request_id(func: Callable) -> Callable:
    """
    Decorator to add request_id to the function's logger.
    
    Args:
        func: The function to decorate.
        
    Returns:
        The decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        request_id = kwargs.pop("request_id", None) or str(uuid.uuid4())
        logger = get_logger(func.__module__, request_id)
        
        # Add the logger to the function's globals
        func.__globals__["logger"] = logger
        
        return func(*args, **kwargs)
    
    return wrapper


def log_function_call(func: Callable) -> Callable:
    """
    Decorator to log function calls with arguments and return values.
    
    Args:
        func: The function to decorate.
        
    Returns:
        The decorated function.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        
        # Log function call with arguments
        arg_str = ", ".join([repr(a) for a in args])
        kwarg_str = ", ".join([f"{k}={repr(v)}" for k, v in kwargs.items()])
        all_args = ", ".join(filter(None, [arg_str, kwarg_str]))
        
        logger.debug(f"Calling {func.__name__}({all_args})")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"{func.__name__} returned {repr(result)}")
            return result
        except Exception as e:
            logger.exception(f"{func.__name__} raised exception", exc_info=True)
            raise
    
    return wrapper


def log_error(msg: str, exc_info: Optional[Exception] = None, **kwargs) -> None:
    """
    Log an error message with stack trace.
    
    Args:
        msg: The message to log.
        exc_info: The exception to include in the log. If not provided, uses sys.exc_info().
        **kwargs: Additional keyword arguments to include in the log.
    """
    logger = get_logger()
    if exc_info:
        logger.error(msg, exc_info=exc_info, **kwargs)
    else:
        logger.error(msg, exc_info=True, **kwargs)


# Initialize logging with default configuration
configure_logging()


def set_log_level(level: str) -> None:
    """
    Set the log level for the Document Service.
    
    Args:
        level: The log level to set (DEBUG, INFO, WARN, ERROR, CRITICAL).
    """
    configure_logging(level)


def create_request_context(request_id: Optional[str] = None) -> Dict[str, str]:
    """
    Create a context dictionary with request information.
    
    Args:
        request_id: An optional request ID. If not provided, a new UUID will be generated.
        
    Returns:
        A dictionary with request context information.
    """
    return {
        "request_id": request_id or str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat()
    }


def format_exception(exc: Exception) -> Dict[str, Any]:
    """
    Format an exception for logging.
    
    Args:
        exc: The exception to format.
        
    Returns:
        A dictionary with formatted exception information.
    """
    return {
        "exception_type": exc.__class__.__name__,
        "exception_message": str(exc),
        "traceback": traceback.format_exception(type(exc), exc, exc.__traceback__)
    }


def get_environment() -> str:
    """
    Get the current environment (development, staging, production).
    
    Returns:
        The current environment name.
    """
    return os.environ.get("ENVIRONMENT", "development").lower()


def is_production() -> bool:
    """
    Check if the current environment is production.
    
    Returns:
        True if the current environment is production, False otherwise.
    """
    return get_environment() == "production"


def is_debug_enabled() -> bool:
    """
    Check if debug logging is enabled.
    
    Returns:
        True if debug logging is enabled, False otherwise.
    """
    return logger.isEnabledFor(logging.DEBUG)


class LogContext:
    """
    Context manager for adding temporary context to logs.
    """
    def __init__(self, logger: ContextLogger, **context):
        """
        Initialize a new LogContext.
        
        Args:
            logger: The logger to add context to.
            **context: Key-value pairs to add to the context.
        """
        self.logger = logger
        self.context = context
        self.previous_context = {}
        
    def __enter__(self) -> ContextLogger:
        """
        Add context to the logger when entering the context manager.
        
        Returns:
            The logger with added context.
        """
        # Save previous context values if they exist
        for key, value in self.context.items():
            if key in self.logger.context:
                self.previous_context[key] = self.logger.context[key]
                
        # Add new context
        self.logger.add_context(**self.context)
        return self.logger
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Restore previous context when exiting the context manager.
        
        Args:
            exc_type: The exception type, if an exception was raised.
            exc_val: The exception value, if an exception was raised.
            exc_tb: The exception traceback, if an exception was raised.
        """
        # Remove added context
        for key in self.context.keys():
            if key not in self.previous_context:
                self.logger.remove_context(key)
            else:
                # Restore previous value
                self.logger.add_context(**{key: self.previous_context[key]})


def with_context(logger: ContextLogger, **context):
    """
    Create a context manager for adding temporary context to logs.
    
    Args:
        logger: The logger to add context to.
        **context: Key-value pairs to add to the context.
        
    Returns:
        A context manager that adds the specified context to logs.
    """
    return LogContext(logger, **context)


def log_document_processing(logger: ContextLogger, document_id: str, document_type: str) -> ContextLogger:
    """
    Add document processing context to a logger.
    
    Args:
        logger: The logger to add context to.
        document_id: The ID of the document being processed.
        document_type: The type of the document being processed.
        
    Returns:
        The logger with added document context.
    """
    logger.add_context(
        document_id=document_id,
        document_type=document_type,
        processing_started=datetime.utcnow().isoformat()
    )
    return logger


def log_classification_result(logger: ContextLogger, classification: str, confidence: float) -> None:
    """
    Log a document classification result.
    
    Args:
        logger: The logger to use.
        classification: The classification result.
        confidence: The confidence score of the classification.
    """
    logger.info(
        f"Document classified as {classification}",
        extra={
            "classification": classification,
            "confidence": confidence,
            "classification_time": datetime.utcnow().isoformat()
        }
    )


def log_processing_time(logger: ContextLogger, operation: str, start_time: datetime, end_time: Optional[datetime] = None) -> None:
    """
    Log the processing time for an operation.
    
    Args:
        logger: The logger to use.
        operation: The name of the operation.
        start_time: The start time of the operation.
        end_time: The end time of the operation. If not provided, uses the current time.
    """
    if end_time is None:
        end_time = datetime.utcnow()
        
    duration_ms = (end_time - start_time).total_seconds() * 1000
    
    logger.info(
        f"{operation} completed in {duration_ms:.2f}ms",
        extra={
            "operation": operation,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_ms": duration_ms
        }
    )


def log_document_extraction_result(logger: ContextLogger, extracted_fields: Dict[str, Any], confidence_scores: Dict[str, float]) -> None:
    """
    Log the result of document data extraction.
    
    Args:
        logger: The logger to use.
        extracted_fields: The fields extracted from the document.
        confidence_scores: The confidence scores for each extracted field.
    """
    logger.info(
        f"Extracted {len(extracted_fields)} fields from document",
        extra={
            "extracted_fields": list(extracted_fields.keys()),
            "confidence_scores": confidence_scores,
            "extraction_time": datetime.utcnow().isoformat()
        }
    )


def log_document_processing_error(logger: ContextLogger, error: Exception, document_id: str, stage: str) -> None:
    """
    Log an error that occurred during document processing.
    
    Args:
        logger: The logger to use.
        error: The error that occurred.
        document_id: The ID of the document being processed.
        stage: The processing stage where the error occurred.
    """
    logger.error(
        f"Error processing document {document_id} at stage {stage}: {str(error)}",
        exc_info=error,
        extra={
            "document_id": document_id,
            "processing_stage": stage,
            "error_time": datetime.utcnow().isoformat(),
            "error_details": format_exception(error)
        }
    )


def log_api_request(logger: ContextLogger, method: str, path: str, status_code: int, duration_ms: float) -> None:
    """
    Log an API request.
    
    Args:
        logger: The logger to use.
        method: The HTTP method of the request.
        path: The path of the request.
        status_code: The HTTP status code of the response.
        duration_ms: The duration of the request in milliseconds.
    """
    log_level = logging.INFO if 200 <= status_code < 400 else logging.ERROR
    
    logger._log(
        log_level,
        f"{method} {path} {status_code} ({duration_ms:.2f}ms)",
        extra={
            "http_method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_time": datetime.utcnow().isoformat()
        }
    )


def log_message_queue_event(logger: ContextLogger, exchange: str, routing_key: str, message_type: str) -> None:
    """
    Log a message queue event.
    
    Args:
        logger: The logger to use.
        exchange: The message exchange.
        routing_key: The routing key.
        message_type: The type of message.
    """
    logger.info(
        f"Message queue event: {message_type}",
        extra={
            "exchange": exchange,
            "routing_key": routing_key,
            "message_type": message_type,
            "event_time": datetime.utcnow().isoformat()
        }
    )


def log_model_prediction(logger: ContextLogger, model_name: str, input_shape: Any, prediction: Any, duration_ms: float) -> None:
    """
    Log a model prediction.
    
    Args:
        logger: The logger to use.
        model_name: The name of the model.
        input_shape: The shape of the input data.
        prediction: The prediction result.
        duration_ms: The duration of the prediction in milliseconds.
    """
    logger.info(
        f"Model {model_name} prediction completed in {duration_ms:.2f}ms",
        extra={
            "model_name": model_name,
            "input_shape": str(input_shape),
            "prediction_type": type(prediction).__name__,
            "duration_ms": duration_ms,
            "prediction_time": datetime.utcnow().isoformat()
        }
    )


def log_document_storage_operation(logger: ContextLogger, operation: str, document_id: str, storage_path: str, success: bool) -> None:
    """
    Log a document storage operation.
    
    Args:
        logger: The logger to use.
        operation: The storage operation (e.g., 'upload', 'download', 'delete').
        document_id: The ID of the document.
        storage_path: The storage path of the document.
        success: Whether the operation was successful.
    """
    log_level = logging.INFO if success else logging.ERROR
    status = "succeeded" if success else "failed"
    
    logger._log(
        log_level,
        f"Document storage operation {operation} {status} for document {document_id}",
        extra={
            "operation": operation,
            "document_id": document_id,
            "storage_path": storage_path,
            "success": success,
            "operation_time": datetime.utcnow().isoformat()
        }
    )


def sanitize_log_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize sensitive data from log entries.
    
    Args:
        data: The data to sanitize.
        
    Returns:
        The sanitized data.
    """
    # Make a copy to avoid modifying the original
    sanitized = data.copy()
    
    # List of sensitive field names to mask
    sensitive_fields = [
        "password", "token", "api_key", "secret", "credential", "ssn", 
        "social_security", "credit_card", "card_number", "ein", "tax_id"
    ]
    
    # Recursively sanitize the data
    def _sanitize(obj):
        if isinstance(obj, dict):
            for key, value in list(obj.items()):
                if any(sensitive in key.lower() for sensitive in sensitive_fields):
                    obj[key] = "[REDACTED]"
                else:
                    obj[key] = _sanitize(value)
            return obj
        elif isinstance(obj, list):
            return [_sanitize(item) for item in obj]
        else:
            return obj
    
    return _sanitize(sanitized)