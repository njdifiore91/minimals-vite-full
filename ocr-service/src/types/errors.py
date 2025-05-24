#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Error Type Definitions for OCR Service

This module defines Python type hints for error handling, logging, and monitoring used by the OCR Service.
It provides type definitions for standardized error structures, logging formats, and error classification.

These types ensure consistent error handling and logging across the service, making troubleshooting
and monitoring more effective. They are used by the error_utils and logging_utils modules to provide
a robust error handling and logging system.

Typical usage example:

    from typing import Optional
    from types.errors import Result, ErrorDetails, ErrorCategory
    
    def process_document(document_id: str) -> Result[dict, ErrorDetails]:
        try:
            # Process the document
            result = {...}  # Document processing result
            return Result.success(result)
        except Exception as e:
            error_details = ErrorDetails(
                message="Failed to process document",
                category=ErrorCategory.PROCESSING,
                context={"document_id": document_id},
                exception=e
            )
            return Result.failure(error_details)
"""

import enum
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, Generic, List, Optional, TypeVar, Union, Callable


# Type variable for generic Result type
T = TypeVar('T')
E = TypeVar('E')


class ErrorCategory(Enum):
    """
    Enum representing different categories of errors in the OCR service.
    
    These categories help classify errors for better troubleshooting and monitoring.
    They are used in error handling, logging, and alerting systems.
    """
    VALIDATION = auto()  # Input validation errors (e.g., invalid document format)
    CONNECTION = auto()  # Connection errors (e.g., RabbitMQ, S3)
    PROCESSING = auto()  # Document processing errors (e.g., OCR extraction failures)
    SYSTEM = auto()      # System-level errors (e.g., out of memory)
    UNKNOWN = auto()     # Uncategorized errors


class ErrorSeverity(Enum):
    """
    Enum representing the severity of errors.
    
    The severity level helps determine the appropriate response to an error,
    such as whether to retry, alert, or simply log the error.
    """
    LOW = auto()      # Non-critical errors that don't affect processing
    MEDIUM = auto()   # Errors that affect current processing but can be recovered
    HIGH = auto()     # Critical errors that require immediate attention
    FATAL = auto()    # Errors that cause system failure


class MonitoringLevel(Enum):
    """
    Enum representing different monitoring levels for alerts.
    
    These levels determine how alerts are handled by the monitoring system,
    such as whether they trigger notifications or are just logged.
    """
    INFO = auto()      # Informational alerts
    WARNING = auto()   # Warning alerts that may require attention
    ERROR = auto()     # Error alerts that require attention
    CRITICAL = auto()  # Critical alerts that require immediate attention


@dataclass
class ErrorDetails:
    """
    Data class for capturing error context and stack traces.
    
    This class provides a standardized structure for error details, including
    the error message, category, severity, context, and stack trace.
    
    Attributes:
        message: A human-readable error message.
        category: The category of the error (validation, connection, etc.).
        severity: The severity of the error (low, medium, high, fatal).
        context: Additional context information about the error.
        exception: The original exception that caused this error.
        timestamp: When the error occurred.
        trace: Stack trace information.
    """
    message: str
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    context: Dict[str, Any] = field(default_factory=dict)
    exception: Optional[Exception] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    trace: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """
        Initialize trace if not provided and an exception is available.
        """
        if not self.trace and self.exception:
            self.trace = traceback.format_exception(
                type(self.exception), 
                self.exception, 
                self.exception.__traceback__
            )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the error details to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the error details.
        """
        return {
            "message": self.message,
            "category": self.category.name,
            "severity": self.severity.name,
            "context": self.context,
            "exception": str(self.exception) if self.exception else None,
            "timestamp": self.timestamp,
            "trace": self.trace
        }


@dataclass
class LogEntry:
    """
    Data class for structured logging with timestamp and context.
    
    This class provides a standardized structure for log entries, including
    the log message, level, timestamp, and context information.
    
    Attributes:
        message: The log message.
        level: The log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        timestamp: When the log entry was created.
        service: The name of the service generating the log.
        request_id: The ID of the request being processed.
        context: Additional context information for the log entry.
    """
    message: str
    level: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    service: str = "ocr-service"
    request_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the log entry to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the log entry.
        """
        return {
            "message": self.message,
            "level": self.level,
            "timestamp": self.timestamp,
            "service": self.service,
            "request_id": self.request_id,
            "context": self.context
        }


@dataclass
class MonitoringAlert:
    """
    Data class for critical error alerting.
    
    This class provides a standardized structure for monitoring alerts,
    which can be sent to monitoring systems for alerting and dashboards.
    
    Attributes:
        title: The alert title.
        message: The alert message.
        level: The monitoring level (INFO, WARNING, ERROR, CRITICAL).
        timestamp: When the alert was created.
        service: The name of the service generating the alert.
        context: Additional context information for the alert.
        error_details: Detailed error information if this is an error alert.
    """
    title: str
    message: str
    level: MonitoringLevel
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    service: str = "ocr-service"
    context: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[ErrorDetails] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the monitoring alert to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the monitoring alert.
        """
        result = {
            "title": self.title,
            "message": self.message,
            "level": self.level.name,
            "timestamp": self.timestamp,
            "service": self.service,
            "context": self.context
        }
        
        if self.error_details:
            result["error_details"] = self.error_details.to_dict()
            
        return result


class Result(Generic[T, E]):
    """
    Generic type for operation results and error handling.
    
    This class provides a standardized way to return either a successful result
    or an error from a function, similar to Rust's Result type or Haskell's Either.
    
    It helps avoid raising exceptions for expected error conditions and makes
    error handling more explicit and type-safe.
    
    Attributes:
        _is_success: Whether the result is a success or failure.
        _value: The success value (if _is_success is True).
        _error: The error value (if _is_success is False).
    """
    
    def __init__(self, is_success: bool, value: Optional[T] = None, error: Optional[E] = None):
        """
        Initialize a Result instance.
        
        Args:
            is_success: Whether the result is a success or failure.
            value: The success value (if is_success is True).
            error: The error value (if is_success is False).
        """
        self._is_success = is_success
        self._value = value
        self._error = error
    
    @classmethod
    def success(cls, value: T) -> 'Result[T, E]':
        """
        Create a successful result with the given value.
        
        Args:
            value: The success value.
            
        Returns:
            A Result instance representing a successful operation.
        """
        return cls(True, value=value)
    
    @classmethod
    def failure(cls, error: E) -> 'Result[T, E]':
        """
        Create a failure result with the given error.
        
        Args:
            error: The error value.
            
        Returns:
            A Result instance representing a failed operation.
        """
        return cls(False, error=error)
    
    def is_success(self) -> bool:
        """
        Check if the result is a success.
        
        Returns:
            True if the result is a success, False otherwise.
        """
        return self._is_success
    
    def is_failure(self) -> bool:
        """
        Check if the result is a failure.
        
        Returns:
            True if the result is a failure, False otherwise.
        """
        return not self._is_success
    
    def value(self) -> T:
        """
        Get the success value.
        
        Raises:
            ValueError: If the result is a failure.
            
        Returns:
            The success value.
        """
        if not self._is_success:
            raise ValueError("Cannot get value from a failure result")
        return self._value
    
    def error(self) -> E:
        """
        Get the error value.
        
        Raises:
            ValueError: If the result is a success.
            
        Returns:
            The error value.
        """
        if self._is_success:
            raise ValueError("Cannot get error from a success result")
        return self._error
    
    def map(self, f: Callable[[T], Any]) -> 'Result[Any, E]':
        """
        Apply a function to the success value if the result is a success.
        
        Args:
            f: The function to apply to the success value.
            
        Returns:
            A new Result with the function applied to the success value,
            or the original error if the result is a failure.
        """
        if self._is_success:
            return Result.success(f(self._value))
        return Result.failure(self._error)
    
    def map_error(self, f: Callable[[E], Any]) -> 'Result[T, Any]':
        """
        Apply a function to the error value if the result is a failure.
        
        Args:
            f: The function to apply to the error value.
            
        Returns:
            A new Result with the function applied to the error value,
            or the original success value if the result is a success.
        """
        if self._is_success:
            return Result.success(self._value)
        return Result.failure(f(self._error))
    
    def and_then(self, f: Callable[[T], 'Result[Any, E]']) -> 'Result[Any, E]':
        """
        Apply a function that returns a Result to the success value if the result is a success.
        
        This is similar to flatMap or bind in other languages.
        
        Args:
            f: The function to apply to the success value.
            
        Returns:
            The result of applying the function to the success value,
            or the original error if the result is a failure.
        """
        if self._is_success:
            return f(self._value)
        return Result.failure(self._error)
    
    def or_else(self, f: Callable[[E], 'Result[T, Any]']) -> 'Result[T, Any]':
        """
        Apply a function that returns a Result to the error value if the result is a failure.
        
        Args:
            f: The function to apply to the error value.
            
        Returns:
            The result of applying the function to the error value,
            or the original success value if the result is a success.
        """
        if self._is_success:
            return Result.success(self._value)
        return f(self._error)
    
    def unwrap_or(self, default: T) -> T:
        """
        Get the success value or a default value if the result is a failure.
        
        Args:
            default: The default value to return if the result is a failure.
            
        Returns:
            The success value or the default value.
        """
        if self._is_success:
            return self._value
        return default
    
    def unwrap_or_else(self, f: Callable[[E], T]) -> T:
        """
        Get the success value or the result of applying a function to the error value.
        
        Args:
            f: The function to apply to the error value.
            
        Returns:
            The success value or the result of applying the function to the error value.
        """
        if self._is_success:
            return self._value
        return f(self._error)


# Type alias for a Result with ErrorDetails as the error type
OperationResult = TypeVar('OperationResult')
ErrorResult = Result[OperationResult, ErrorDetails]