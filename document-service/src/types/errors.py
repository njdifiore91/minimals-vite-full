"""
Type definitions for error handling, logging, and monitoring in the Document Service.

This module provides standardized type definitions for error structures, logging formats,
and error classification used throughout the Document Service. These types ensure
consistent error handling and logging, making troubleshooting and monitoring more
effective.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, TypeVar, Generic, Any, Union, Callable
from datetime import datetime
import traceback
import sys


class ErrorCategory(Enum):
    """Enumeration of error categories for classification and monitoring.
    
    These categories help with error filtering, reporting, and alerting based on severity.
    """
    # System-level errors that require immediate attention
    CRITICAL = auto()
    # Errors that affect functionality but don't crash the system
    ERROR = auto()
    # Potential issues that don't immediately affect functionality
    WARNING = auto()
    # Validation errors from document processing
    VALIDATION = auto()
    # Authentication and authorization errors
    SECURITY = auto()
    # Errors related to external service communication
    INTEGRATION = auto()
    # Errors related to document classification
    CLASSIFICATION = auto()
    # Errors related to data extraction
    EXTRACTION = auto()
    # Errors related to message queue operations
    MESSAGING = auto()


class ErrorDetails:
    """Container for detailed error information including context and stack traces.
    
    This class captures comprehensive error details to aid in debugging and
    troubleshooting, including the original exception, stack trace, and contextual
    information about where and when the error occurred.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory,
        exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        service_name: str = "document-service",
        capture_stack_trace: bool = True
    ):
        """
        Initialize error details with comprehensive information.
        
        Args:
            message: Human-readable error message
            category: Error category for classification
            exception: Original exception that was raised, if any
            context: Additional contextual information about the error
            timestamp: When the error occurred (defaults to now)
            service_name: Name of the service where the error occurred
            capture_stack_trace: Whether to capture the stack trace
        """
        self.message = message
        self.category = category
        self.exception = exception
        self.context = context or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.service_name = service_name
        self.stack_trace = None
        
        if capture_stack_trace:
            if exception:
                self.stack_trace = ''.join(traceback.format_exception(
                    type(exception), exception, exception.__traceback__))
            else:
                self.stack_trace = ''.join(traceback.format_stack())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error details to a dictionary for serialization.
        
        Returns:
            Dictionary representation of error details
        """
        return {
            "message": self.message,
            "category": self.category.name,
            "exception_type": type(self.exception).__name__ if self.exception else None,
            "exception_message": str(self.exception) if self.exception else None,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "service_name": self.service_name,
            "stack_trace": self.stack_trace
        }


class LogEntry:
    """Structured log entry for consistent logging across the service.
    
    This class provides a standardized format for log entries, ensuring that all logs
    contain necessary context for troubleshooting and monitoring.
    """
    
    def __init__(
        self,
        message: str,
        level: str = "INFO",
        context: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        service_name: str = "document-service",
        correlation_id: Optional[str] = None,
        document_id: Optional[str] = None,
        operation: Optional[str] = None
    ):
        """
        Initialize a log entry with structured information.
        
        Args:
            message: Log message content
            level: Log level (ERROR, WARN, INFO, DEBUG)
            context: Additional contextual information
            timestamp: When the log was created (defaults to now)
            service_name: Name of the service generating the log
            correlation_id: Request correlation ID for tracing
            document_id: ID of the document being processed, if applicable
            operation: Name of the operation being performed
        """
        self.message = message
        self.level = level
        self.context = context or {}
        self.timestamp = timestamp or datetime.utcnow()
        self.service_name = service_name
        self.correlation_id = correlation_id
        self.document_id = document_id
        self.operation = operation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to a dictionary for serialization.
        
        Returns:
            Dictionary representation of log entry
        """
        return {
            "message": self.message,
            "level": self.level,
            "context": self.context,
            "timestamp": self.timestamp.isoformat(),
            "service_name": self.service_name,
            "correlation_id": self.correlation_id,
            "document_id": self.document_id,
            "operation": self.operation
        }


class MonitoringAlert:
    """Alert structure for critical errors that require immediate attention.
    
    This class defines the structure for alerts that should be sent to monitoring
    systems when critical errors occur.
    """
    
    def __init__(
        self,
        title: str,
        message: str,
        severity: str = "critical",
        error_details: Optional[ErrorDetails] = None,
        timestamp: Optional[datetime] = None,
        service_name: str = "document-service",
        alert_tags: Optional[List[str]] = None,
        notification_channels: Optional[List[str]] = None
    ):
        """
        Initialize a monitoring alert with detailed information.
        
        Args:
            title: Short alert title
            message: Detailed alert message
            severity: Alert severity (critical, error, warning, info)
            error_details: Associated error details if available
            timestamp: When the alert was created (defaults to now)
            service_name: Name of the service generating the alert
            alert_tags: Tags for alert categorization
            notification_channels: Channels to notify (email, slack, etc.)
        """
        self.title = title
        self.message = message
        self.severity = severity
        self.error_details = error_details
        self.timestamp = timestamp or datetime.utcnow()
        self.service_name = service_name
        self.alert_tags = alert_tags or []
        self.notification_channels = notification_channels or ["default"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the alert
        """
        result = {
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "service_name": self.service_name,
            "alert_tags": self.alert_tags,
            "notification_channels": self.notification_channels
        }
        
        if self.error_details:
            result["error_details"] = self.error_details.to_dict()
            
        return result


class ServiceError(Exception):
    """Base exception class for Document Service errors.
    
    This class extends the standard Exception class to include structured error
    details for better error handling, logging, and monitoring.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.ERROR,
        original_exception: Optional[Exception] = None,
        context: Optional[Dict[str, Any]] = None,
        http_status_code: Optional[int] = None
    ):
        """
        Initialize a service error with detailed information.
        
        Args:
            message: Human-readable error message
            category: Error category for classification
            original_exception: Original exception that caused this error
            context: Additional contextual information
            http_status_code: HTTP status code if this error is exposed via API
        """
        super().__init__(message)
        self.message = message
        self.category = category
        self.original_exception = original_exception
        self.context = context or {}
        self.http_status_code = http_status_code
        self.error_details = ErrorDetails(
            message=message,
            category=category,
            exception=original_exception,
            context=context
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert service error to a dictionary for serialization.
        
        Returns:
            Dictionary representation of the error
        """
        return {
            "error": {
                "message": self.message,
                "category": self.category.name,
                "details": self.error_details.to_dict(),
                "http_status_code": self.http_status_code
            }
        }
    
    def to_api_response(self) -> Dict[str, Any]:
        """Convert service error to an API response format.
        
        Returns:
            API-friendly error response
        """
        return {
            "success": False,
            "error": {
                "message": self.message,
                "code": f"{self.category.name.lower()}.{self.http_status_code or 500}",
                "details": self.context
            }
        }


# Define specific error types for common scenarios
class ValidationError(ServiceError):
    """Error raised when document validation fails."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.VALIDATION, original_exception, context, 400)


class ClassificationError(ServiceError):
    """Error raised when document classification fails."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.CLASSIFICATION, original_exception, context, 422)


class ExtractionError(ServiceError):
    """Error raised when data extraction from a document fails."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.EXTRACTION, original_exception, context, 422)


class IntegrationError(ServiceError):
    """Error raised when integration with external services fails."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.INTEGRATION, original_exception, context, 502)


class SecurityError(ServiceError):
    """Error raised for security-related issues."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.SECURITY, original_exception, context, 403)


class MessagingError(ServiceError):
    """Error raised when message queue operations fail."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, original_exception: Optional[Exception] = None):
        super().__init__(message, ErrorCategory.MESSAGING, original_exception, context, 500)


# Generic Result type for operation results with error handling
T = TypeVar('T')  # Success type
E = TypeVar('E', bound=Exception)  # Error type


class Result(Generic[T, E]):
    """Generic result type for operations that may succeed or fail.
    
    This class provides a standardized way to handle operation results and errors,
    inspired by the Result pattern from languages like Rust and Swift.
    """
    
    def __init__(self, value: Optional[T] = None, error: Optional[E] = None):
        """
        Initialize a result with either a success value or an error.
        
        Args:
            value: The success value if the operation succeeded
            error: The error if the operation failed
        """
        self._value = value
        self._error = error
        self._is_success = error is None
    
    @classmethod
    def success(cls, value: T) -> 'Result[T, E]':
        """Create a successful result with the given value.
        
        Args:
            value: The success value
            
        Returns:
            A successful Result instance
        """
        return cls(value=value)
    
    @classmethod
    def failure(cls, error: E) -> 'Result[T, E]':
        """Create a failed result with the given error.
        
        Args:
            error: The error that occurred
            
        Returns:
            A failed Result instance
        """
        return cls(error=error)
    
    @property
    def is_success(self) -> bool:
        """Check if the result is successful.
        
        Returns:
            True if the operation succeeded, False otherwise
        """
        return self._is_success
    
    @property
    def is_failure(self) -> bool:
        """Check if the result is a failure.
        
        Returns:
            True if the operation failed, False otherwise
        """
        return not self._is_success
    
    @property
    def value(self) -> T:
        """Get the success value.
        
        Raises:
            ValueError: If the result is a failure
            
        Returns:
            The success value
        """
        if not self._is_success:
            raise ValueError("Cannot get value from a failed result")
        return self._value
    
    @property
    def error(self) -> E:
        """Get the error.
        
        Raises:
            ValueError: If the result is a success
            
        Returns:
            The error
        """
        if self._is_success:
            raise ValueError("Cannot get error from a successful result")
        return self._error
    
    def on_success(self, callback: Callable[[T], Any]) -> 'Result[T, E]':
        """Execute a callback if the result is successful.
        
        Args:
            callback: Function to call with the success value
            
        Returns:
            Self for method chaining
        """
        if self._is_success:
            callback(self._value)
        return self
    
    def on_failure(self, callback: Callable[[E], Any]) -> 'Result[T, E]':
        """Execute a callback if the result is a failure.
        
        Args:
            callback: Function to call with the error
            
        Returns:
            Self for method chaining
        """
        if not self._is_success:
            callback(self._error)
        return self
    
    def map(self, mapper: Callable[[T], Any]) -> 'Result[Any, E]':
        """Transform the success value using the given function.
        
        Args:
            mapper: Function to transform the success value
            
        Returns:
            A new Result with the transformed value or the original error
        """
        if self._is_success:
            return Result.success(mapper(self._value))
        return Result.failure(self._error)
    
    def flat_map(self, mapper: Callable[[T], 'Result[Any, E]']) -> 'Result[Any, E]':
        """Transform the success value using a function that returns a Result.
        
        Args:
            mapper: Function that transforms the value into another Result
            
        Returns:
            The Result returned by the mapper function or the original error
        """
        if self._is_success:
            return mapper(self._value)
        return Result.failure(self._error)
    
    def recover(self, recovery_func: Callable[[E], T]) -> T:
        """Recover from a failure by transforming the error into a success value.
        
        Args:
            recovery_func: Function to transform the error into a success value
            
        Returns:
            The original success value or the recovered value
        """
        if self._is_success:
            return self._value
        return recovery_func(self._error)
    
    def unwrap_or(self, default: T) -> T:
        """Get the success value or a default value if the result is a failure.
        
        Args:
            default: Default value to return if the result is a failure
            
        Returns:
            The success value or the default value
        """
        if self._is_success:
            return self._value
        return default
    
    def unwrap_or_else(self, default_func: Callable[[E], T]) -> T:
        """Get the success value or compute a default value if the result is a failure.
        
        Args:
            default_func: Function to compute a default value from the error
            
        Returns:
            The success value or the computed default value
        """
        if self._is_success:
            return self._value
        return default_func(self._error)