#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging Utilities for OCR Service

This module provides utility functions for structured logging in the OCR Service.
It exports functions for creating contextual log entries, formatting log messages,
and handling different log levels. These utilities ensure consistent logging
across the service and integrate with the logger configuration.

Features:
- Contextual logging with request ID tracking
- Structured log formatting for machine readability
- Error logging with stack traces
- Log level filtering based on environment
- Performance logging utilities

Usage:
    from utils.logging_utils import get_logger, log_info, log_error
    
    # Get a logger for the current module
    logger = get_logger(__name__)
    
    # Log an informational message
    log_info(logger, "Processing document", document_id="doc123")
    
    # Log an error with exception information
    try:
        process_document("doc123")
    except Exception as e:
        log_error(logger, "Failed to process document", document_id="doc123", exc_info=e)
"""

import inspect
import json
import logging
import sys
import time
import traceback
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

# Import context variables from logging_config
try:
    from ..config.logging_config import request_id_var, user_id_var, set_request_context, clear_request_context
except ImportError:
    # Fallback if config module is not available
    from contextvars import ContextVar
    request_id_var: ContextVar[str] = ContextVar('request_id', default='')
    user_id_var: ContextVar[str] = ContextVar('user_id', default='')
    
    def set_request_context(request_id: str, user_id: Optional[str] = None) -> None:
        request_id_var.set(request_id)
        if user_id:
            user_id_var.set(user_id)
    
    def clear_request_context() -> None:
        request_id_var.set('')
        user_id_var.set('')


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    This is a convenience function that wraps logging.getLogger() to ensure
    consistent logger naming throughout the application.
    
    Args:
        name: The name of the logger, typically __name__ of the calling module
        
    Returns:
        logging.Logger: The logger instance
    """
    return logging.getLogger(name)


def generate_request_id() -> str:
    """
    Generate a unique request ID for tracking requests across the system.
    
    Returns:
        str: A unique request ID
    """
    return str(uuid.uuid4())


def with_request_context(request_id: Optional[str] = None, user_id: Optional[str] = None) -> Callable:
    """
    Decorator to set request context for the duration of a function call.
    
    This decorator sets the request_id and user_id in the context variables
    for the duration of the decorated function, and clears them afterward.
    
    Args:
        request_id: The request ID to set, or None to generate a new one
        user_id: The user ID to set, or None if not available
        
    Returns:
        Callable: A decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate or use provided request ID
            _request_id = request_id or generate_request_id()
            
            # Set request context
            set_request_context(_request_id, user_id)
            
            try:
                # Call the decorated function
                return func(*args, **kwargs)
            finally:
                # Clear request context
                clear_request_context()
                
        return wrapper
    return decorator


def log_with_context(logger: logging.Logger, level: int, msg: str, *args, **kwargs) -> None:
    """
    Log a message with the specified level and additional context information.
    
    This function adds context information to the log message, including
    the request ID, user ID, and any additional keyword arguments.
    
    Args:
        logger: The logger to use
        level: The log level (e.g., logging.INFO, logging.ERROR)
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
        
    Keyword Args:
        exc_info: Exception information to include in the log
        stack_info: Whether to include stack information
        extra: Additional context information
    """
    # Extract special keyword arguments
    exc_info = kwargs.pop('exc_info', None)
    stack_info = kwargs.pop('stack_info', False)
    extra = kwargs.pop('extra', {})
    
    # Add remaining keyword arguments to extra context
    for key, value in kwargs.items():
        extra[key] = value
    
    # Log the message with context
    logger.log(level, msg, *args, exc_info=exc_info, stack_info=stack_info, extra=extra)


def log_debug(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log a DEBUG level message with context information.
    
    Args:
        logger: The logger to use
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
    """
    log_with_context(logger, logging.DEBUG, msg, *args, **kwargs)


def log_info(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log an INFO level message with context information.
    
    Args:
        logger: The logger to use
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
    """
    log_with_context(logger, logging.INFO, msg, *args, **kwargs)


def log_warning(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log a WARNING level message with context information.
    
    Args:
        logger: The logger to use
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
    """
    log_with_context(logger, logging.WARNING, msg, *args, **kwargs)


def log_error(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log an ERROR level message with context information.
    
    Args:
        logger: The logger to use
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
        
    Keyword Args:
        exc_info: Exception information to include in the log. If True, the current exception
                 information is used. If an exception, that exception's information is used.
    """
    log_with_context(logger, logging.ERROR, msg, *args, **kwargs)


def log_critical(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log a CRITICAL level message with context information.
    
    Args:
        logger: The logger to use
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
        
    Keyword Args:
        exc_info: Exception information to include in the log. If True, the current exception
                 information is used. If an exception, that exception's information is used.
    """
    log_with_context(logger, logging.CRITICAL, msg, *args, **kwargs)


def log_exception(logger: logging.Logger, msg: str, *args, **kwargs) -> None:
    """
    Log an exception with context information.
    
    This function logs an ERROR level message with the current exception information.
    It should be called from an exception handler.
    
    Args:
        logger: The logger to use
        msg: The log message
        *args: Additional positional arguments for the log message
        **kwargs: Additional keyword arguments to include in the log context
    """
    kwargs['exc_info'] = True
    log_error(logger, msg, *args, **kwargs)


def format_exception(exc_info: Optional[Union[bool, BaseException, tuple]] = None) -> str:
    """
    Format exception information as a string.
    
    Args:
        exc_info: Exception information to format. If None or True, the current exception
                 information is used. If an exception, that exception's information is used.
                 
    Returns:
        str: The formatted exception information
    """
    if exc_info is None or exc_info is True:
        exc_info = sys.exc_info()
    elif isinstance(exc_info, BaseException):
        exc_info = (type(exc_info), exc_info, exc_info.__traceback__)
        
    if exc_info and exc_info[0] is not None:
        return ''.join(traceback.format_exception(*exc_info))
    return ''


def log_function_entry_exit(logger: logging.Logger, level: int = logging.DEBUG) -> Callable:
    """
    Decorator to log function entry and exit with parameters and return value.
    
    This decorator logs when a function is called and when it returns or raises an exception.
    It includes the function parameters and return value in the log messages.
    
    Args:
        logger: The logger to use
        level: The log level to use for entry and exit logs
        
    Returns:
        Callable: A decorator function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get function signature
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # Format arguments for logging, excluding self/cls for methods
            arg_str = ', '.join(f"{k}={repr(v)}" for k, v in bound_args.arguments.items()
                               if k not in ('self', 'cls'))
            
            # Log function entry
            log_with_context(logger, level, f"Entering {func.__name__}({arg_str})")
            
            start_time = time.time()
            try:
                # Call the function
                result = func(*args, **kwargs)
                
                # Log function exit with result
                elapsed = time.time() - start_time
                log_with_context(logger, level, 
                               f"Exiting {func.__name__}: returned {repr(result)} in {elapsed:.6f}s")
                
                return result
            except Exception as e:
                # Log function exit with exception
                elapsed = time.time() - start_time
                log_with_context(logger, logging.ERROR,
                               f"Exception in {func.__name__} after {elapsed:.6f}s: {str(e)}",
                               exc_info=e)
                raise
                
        return wrapper
    return decorator


def log_performance(logger: logging.Logger, operation_name: str, level: int = logging.DEBUG) -> Callable:
    """
    Context manager and decorator for logging the performance of an operation.
    
    This can be used as a context manager or a decorator to log the time taken
    by an operation or function.
    
    Args:
        logger: The logger to use
        operation_name: The name of the operation being timed
        level: The log level to use for the performance log
        
    Returns:
        Callable: A decorator function when used as a decorator
        
    Example as context manager:
        with log_performance(logger, "document_processing"):
            process_document(doc)
            
    Example as decorator:
        @log_performance(logger, "document_processing")
        def process_document(doc):
            # Process the document
    """
    class LogPerformanceContext:
        def __init__(self):
            self.start_time = None
            
        def __enter__(self):
            self.start_time = time.time()
            return self
            
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed = time.time() - self.start_time
            if exc_type is not None:
                # Operation failed
                log_with_context(logger, logging.ERROR,
                               f"{operation_name} failed after {elapsed:.6f}s: {str(exc_val)}",
                               exc_info=(exc_type, exc_val, exc_tb))
            else:
                # Operation succeeded
                log_with_context(logger, level,
                               f"{operation_name} completed in {elapsed:.6f}s")
            return False  # Don't suppress exceptions
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with LogPerformanceContext():
                return func(*args, **kwargs)
        return wrapper
    
    # When used as a decorator
    if callable(operation_name):
        func = operation_name
        operation_name = func.__name__
        return decorator(func)
    
    # When used as a context manager
    return LogPerformanceContext()


def log_method_calls(logger: logging.Logger, level: int = logging.DEBUG) -> Callable:
    """
    Class decorator to log all method calls for a class.
    
    This decorator applies the log_function_entry_exit decorator to all methods
    of a class, excluding special methods (those starting with '__').
    
    Args:
        logger: The logger to use
        level: The log level to use for method call logs
        
    Returns:
        Callable: A decorator function
        
    Example:
        @log_method_calls(logger)
        class DocumentProcessor:
            def process(self, document):
                # Process the document
    """
    def decorator(cls: type) -> type:
        for name, method in inspect.getmembers(cls, inspect.isfunction):
            # Skip special methods
            if not name.startswith('__'):
                setattr(cls, name, log_function_entry_exit(logger, level)(method))
        return cls
    return decorator


def sanitize_log_data(data: Dict[str, Any], sensitive_keys: List[str] = None) -> Dict[str, Any]:
    """
    Sanitize log data by removing or masking sensitive information.
    
    Args:
        data: The data to sanitize
        sensitive_keys: A list of keys to mask in the data. If None, a default list is used.
        
    Returns:
        Dict[str, Any]: The sanitized data
    """
    if sensitive_keys is None:
        sensitive_keys = [
            'password', 'token', 'api_key', 'secret', 'credential',
            'ssn', 'social_security', 'credit_card', 'card_number',
            'authorization', 'access_token', 'refresh_token'
        ]
    
    # Create a copy of the data to avoid modifying the original
    sanitized = {}
    
    for key, value in data.items():
        # Check if the key is sensitive
        is_sensitive = any(sk.lower() in key.lower() for sk in sensitive_keys)
        
        if is_sensitive:
            # Mask sensitive values
            if isinstance(value, str):
                sanitized[key] = '********'
            else:
                sanitized[key] = '[REDACTED]'
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_log_data(value, sensitive_keys)
        elif isinstance(value, list):
            # Sanitize lists of dictionaries
            if value and isinstance(value[0], dict):
                sanitized[key] = [sanitize_log_data(item, sensitive_keys) if isinstance(item, dict) else item
                                for item in value]
            else:
                sanitized[key] = value
        else:
            # Pass through non-sensitive values
            sanitized[key] = value
    
    return sanitized


def log_structured_data(logger: logging.Logger, level: int, msg: str, data: Dict[str, Any],
                      sanitize: bool = True, sensitive_keys: List[str] = None, **kwargs) -> None:
    """
    Log structured data with the specified level.
    
    This function logs a message with structured data, optionally sanitizing
    sensitive information before logging.
    
    Args:
        logger: The logger to use
        level: The log level
        msg: The log message
        data: The structured data to log
        sanitize: Whether to sanitize sensitive information
        sensitive_keys: A list of keys to mask in the data
        **kwargs: Additional keyword arguments to include in the log context
    """
    # Sanitize data if requested
    if sanitize:
        data = sanitize_log_data(data, sensitive_keys)
    
    # Add data to extra context
    extra = kwargs.pop('extra', {})
    extra['data'] = data
    
    # Log the message with structured data
    log_with_context(logger, level, msg, extra=extra, **kwargs)


def configure_logger_for_module(module_name: str) -> logging.Logger:
    """
    Configure and return a logger for a specific module.
    
    This function configures a logger with the appropriate name and returns it.
    It's a convenience function for modules to get a properly configured logger.
    
    Args:
        module_name: The name of the module, typically __name__
        
    Returns:
        logging.Logger: The configured logger
    """
    # Get the logger
    logger = logging.getLogger(module_name)
    
    # Return the configured logger
    return logger


def log_ocr_result(logger: logging.Logger, document_id: str, confidence: float,
                 extracted_text: str, processing_time: float, **kwargs) -> None:
    """
    Log OCR processing result with structured data.
    
    This function logs the result of OCR processing with structured data,
    including document ID, confidence score, and processing time.
    
    Args:
        logger: The logger to use
        document_id: The ID of the processed document
        confidence: The confidence score of the OCR result
        extracted_text: The extracted text (may be truncated for logging)
        processing_time: The time taken to process the document in seconds
        **kwargs: Additional keyword arguments to include in the log context
    """
    # Prepare structured data
    data = {
        'document_id': document_id,
        'confidence': confidence,
        'extracted_text_length': len(extracted_text),
        'extracted_text_preview': extracted_text[:100] + '...' if len(extracted_text) > 100 else extracted_text,
        'processing_time': processing_time
    }
    
    # Add additional data
    data.update(kwargs)
    
    # Log the result
    log_structured_data(logger, logging.INFO, f"OCR processing completed for document {document_id}",
                       data=data)


def log_ocr_error(logger: logging.Logger, document_id: str, error: Exception,
                processing_time: float = None, **kwargs) -> None:
    """
    Log OCR processing error with structured data.
    
    This function logs an error that occurred during OCR processing with
    structured data, including document ID and error details.
    
    Args:
        logger: The logger to use
        document_id: The ID of the processed document
        error: The error that occurred
        processing_time: The time taken before the error occurred in seconds
        **kwargs: Additional keyword arguments to include in the log context
    """
    # Prepare structured data
    data = {
        'document_id': document_id,
        'error_type': type(error).__name__,
        'error_message': str(error)
    }
    
    # Add processing time if available
    if processing_time is not None:
        data['processing_time'] = processing_time
    
    # Add additional data
    data.update(kwargs)
    
    # Log the error
    log_structured_data(logger, logging.ERROR,
                       f"OCR processing failed for document {document_id}: {str(error)}",
                       data=data, exc_info=error)