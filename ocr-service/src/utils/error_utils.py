# error_utils.py

"""
Error handling utilities for the OCR Service.

This module provides standardized error handling functions for the OCR Service,
including error classification, context enrichment, retry eligibility determination,
and error serialization for logging and message publishing.

Typical usage example:

    try:
        result = process_document(document)
    except Exception as e:
        error = create_service_error(e, ErrorCategory.PROCESSING)
        log_error(error)
        if is_retry_eligible(error):
            schedule_retry(document)
        else:
            send_to_dead_letter_queue(document, error)
"""

import inspect
import json
import logging
import sys
import traceback
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Type, Union

# Setup module logger
logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Enum representing different categories of errors in the OCR service."""
    VALIDATION = auto()  # Input validation errors
    CONNECTION = auto()  # Connection errors (RabbitMQ, S3, etc.)
    PROCESSING = auto()  # Document processing errors
    SYSTEM = auto()      # System-level errors
    UNKNOWN = auto()     # Uncategorized errors


class ErrorSeverity(Enum):
    """Enum representing the severity of errors."""
    LOW = auto()      # Non-critical errors that don't affect processing
    MEDIUM = auto()   # Errors that affect current processing but can be recovered
    HIGH = auto()     # Critical errors that require immediate attention
    FATAL = auto()    # Errors that cause system failure


class RetryStrategy(Enum):
    """Enum representing different retry strategies for errors."""
    NONE = auto()           # No retry
    IMMEDIATE = auto()      # Retry immediately
    EXPONENTIAL = auto()    # Retry with exponential backoff
    LINEAR = auto()         # Retry with linear backoff
    CUSTOM = auto()         # Custom retry strategy


class ServiceError(Exception):
    """Custom exception class for OCR service errors.
    
    Attributes:
        message: A human-readable error message.
        category: The category of the error (validation, connection, etc.).
        severity: The severity of the error (low, medium, high, fatal).
        retry_strategy: The recommended retry strategy for this error.
        original_exception: The original exception that caused this error.
        details: Additional details about the error context.
        timestamp: When the error occurred.
        trace: Stack trace information.
    """
    
    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        retry_strategy: RetryStrategy = RetryStrategy.NONE,
        original_exception: Optional[Exception] = None,
        details: Optional[Dict[str, Any]] = None,
        trace: Optional[List[str]] = None
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.retry_strategy = retry_strategy
        self.original_exception = original_exception
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()
        self.trace = trace or traceback.format_stack()[:-1]
        
        # Call the base class constructor
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the error to a dictionary for serialization.
        
        Returns:
            A dictionary representation of the error.
        """
        return {
            "message": self.message,
            "category": self.category.name,
            "severity": self.severity.name,
            "retry_strategy": self.retry_strategy.name,
            "original_exception": str(self.original_exception) if self.original_exception else None,
            "details": self.details,
            "timestamp": self.timestamp,
            "trace": self.trace
        }
    
    def to_json(self) -> str:
        """Convert the error to a JSON string for serialization.
        
        Returns:
            A JSON string representation of the error.
        """
        return json.dumps(self.to_dict())


def create_service_error(
    exception: Exception,
    category: ErrorCategory = ErrorCategory.UNKNOWN,
    severity: Optional[ErrorSeverity] = None,
    retry_strategy: Optional[RetryStrategy] = None,
    details: Optional[Dict[str, Any]] = None
) -> ServiceError:
    """Create a ServiceError from an exception.
    
    Args:
        exception: The original exception.
        category: The category of the error.
        severity: The severity of the error. If None, it will be determined automatically.
        retry_strategy: The retry strategy for this error. If None, it will be determined automatically.
        details: Additional details about the error context.
        
    Returns:
        A ServiceError instance.
    """
    # Determine severity if not provided
    if severity is None:
        severity = _determine_severity(exception, category)
    
    # Determine retry strategy if not provided
    if retry_strategy is None:
        retry_strategy = _determine_retry_strategy(exception, category, severity)
    
    # Get stack trace
    trace = traceback.format_exception(type(exception), exception, exception.__traceback__)
    
    # Create and return the ServiceError
    return ServiceError(
        message=str(exception),
        category=category,
        severity=severity,
        retry_strategy=retry_strategy,
        original_exception=exception,
        details=details,
        trace=trace
    )


def _determine_severity(exception: Exception, category: ErrorCategory) -> ErrorSeverity:
    """Determine the severity of an error based on the exception and category.
    
    Args:
        exception: The original exception.
        category: The category of the error.
        
    Returns:
        The determined severity level.
    """
    # Connection errors are typically high severity
    if category == ErrorCategory.CONNECTION:
        return ErrorSeverity.HIGH
    
    # Validation errors are typically medium severity
    if category == ErrorCategory.VALIDATION:
        return ErrorSeverity.MEDIUM
    
    # System errors are typically high or fatal severity
    if category == ErrorCategory.SYSTEM:
        return ErrorSeverity.HIGH
    
    # Processing errors depend on the specific exception
    if category == ErrorCategory.PROCESSING:
        # Check for specific processing error types
        if isinstance(exception, (ValueError, TypeError)):
            return ErrorSeverity.MEDIUM
        if isinstance(exception, (MemoryError, RuntimeError)):
            return ErrorSeverity.HIGH
    
    # Default to medium severity for unknown errors
    return ErrorSeverity.MEDIUM


def _determine_retry_strategy(
    exception: Exception,
    category: ErrorCategory,
    severity: ErrorSeverity
) -> RetryStrategy:
    """Determine the retry strategy for an error based on the exception, category, and severity.
    
    Args:
        exception: The original exception.
        category: The category of the error.
        severity: The severity of the error.
        
    Returns:
        The determined retry strategy.
    """
    # Fatal errors should not be retried
    if severity == ErrorSeverity.FATAL:
        return RetryStrategy.NONE
    
    # Connection errors typically use exponential backoff
    if category == ErrorCategory.CONNECTION:
        return RetryStrategy.EXPONENTIAL
    
    # Validation errors typically should not be retried
    if category == ErrorCategory.VALIDATION:
        return RetryStrategy.NONE
    
    # Processing errors may be retried depending on the exception
    if category == ErrorCategory.PROCESSING:
        # Temporary processing issues can be retried
        if isinstance(exception, (TimeoutError, ConnectionResetError)):
            return RetryStrategy.EXPONENTIAL
        # Data-related errors should not be retried
        if isinstance(exception, (ValueError, TypeError, KeyError)):
            return RetryStrategy.NONE
    
    # System errors may be retried with linear backoff
    if category == ErrorCategory.SYSTEM:
        return RetryStrategy.LINEAR
    
    # Default to no retry for unknown errors
    return RetryStrategy.NONE


def enrich_error_context(
    error: ServiceError,
    context: Dict[str, Any]
) -> ServiceError:
    """Enrich an error with additional context information.
    
    Args:
        error: The ServiceError to enrich.
        context: Additional context information to add to the error.
        
    Returns:
        The enriched ServiceError.
    """
    # Update the error details with the new context
    error.details.update(context)
    return error


def is_retry_eligible(error: ServiceError, max_retries: int = 3) -> bool:
    """Determine if an error is eligible for retry based on its retry strategy and other factors.
    
    Args:
        error: The ServiceError to check.
        max_retries: The maximum number of retries allowed.
        
    Returns:
        True if the error is eligible for retry, False otherwise.
    """
    # Check if the error has a retry strategy
    if error.retry_strategy == RetryStrategy.NONE:
        return False
    
    # Check if the error has already been retried too many times
    current_retries = error.details.get("retry_count", 0)
    if current_retries >= max_retries:
        return False
    
    # Check if the error is too severe to retry
    if error.severity == ErrorSeverity.FATAL:
        return False
    
    # Default to allowing retry
    return True


def increment_retry_count(error: ServiceError) -> ServiceError:
    """Increment the retry count for an error.
    
    Args:
        error: The ServiceError to update.
        
    Returns:
        The updated ServiceError.
    """
    current_retries = error.details.get("retry_count", 0)
    error.details["retry_count"] = current_retries + 1
    return error


def calculate_retry_delay(error: ServiceError, base_delay: float = 1.0) -> float:
    """Calculate the delay before the next retry based on the error's retry strategy.
    
    Args:
        error: The ServiceError to calculate the delay for.
        base_delay: The base delay in seconds.
        
    Returns:
        The calculated delay in seconds.
    """
    retry_count = error.details.get("retry_count", 0)
    
    if error.retry_strategy == RetryStrategy.IMMEDIATE:
        return 0.0
    
    if error.retry_strategy == RetryStrategy.EXPONENTIAL:
        # Exponential backoff: base_delay * 2^retry_count
        return base_delay * (2 ** retry_count)
    
    if error.retry_strategy == RetryStrategy.LINEAR:
        # Linear backoff: base_delay * retry_count
        return base_delay * retry_count
    
    if error.retry_strategy == RetryStrategy.CUSTOM:
        # Custom backoff strategy defined in the error details
        custom_delay = error.details.get("custom_delay")
        if custom_delay is not None:
            return float(custom_delay)
    
    # Default to base delay
    return base_delay


def categorize_exception(exception: Exception) -> ErrorCategory:
    """Categorize an exception into an ErrorCategory.
    
    Args:
        exception: The exception to categorize.
        
    Returns:
        The determined ErrorCategory.
    """
    # Connection-related exceptions
    if isinstance(exception, (ConnectionError, TimeoutError, ConnectionRefusedError, ConnectionResetError)):
        return ErrorCategory.CONNECTION
    
    # Validation-related exceptions
    if isinstance(exception, (ValueError, TypeError, KeyError, AttributeError)):
        return ErrorCategory.VALIDATION
    
    # System-related exceptions
    if isinstance(exception, (MemoryError, OSError, IOError, SystemError)):
        return ErrorCategory.SYSTEM
    
    # Processing-related exceptions (more specific to OCR service)
    processing_error_types = (
        "ProcessingError",
        "OCRError",
        "DocumentError",
        "ExtractionError",
        "ModelError"
    )
    if any(error_type in exception.__class__.__name__ for error_type in processing_error_types):
        return ErrorCategory.PROCESSING
    
    # Default to unknown category
    return ErrorCategory.UNKNOWN


def format_error_for_logging(error: ServiceError) -> Dict[str, Any]:
    """Format an error for logging purposes.
    
    Args:
        error: The ServiceError to format.
        
    Returns:
        A dictionary suitable for logging.
    """
    return {
        "error_message": error.message,
        "error_category": error.category.name,
        "error_severity": error.severity.name,
        "error_timestamp": error.timestamp,
        "error_details": error.details,
        "original_exception": str(error.original_exception) if error.original_exception else None,
        # Include only the first 5 lines of the trace for brevity
        "trace_excerpt": error.trace[:5] if error.trace else None
    }


def format_error_for_publishing(error: ServiceError) -> Dict[str, Any]:
    """Format an error for publishing to message queues.
    
    Args:
        error: The ServiceError to format.
        
    Returns:
        A dictionary suitable for message publishing.
    """
    return {
        "error": {
            "message": error.message,
            "category": error.category.name,
            "severity": error.severity.name,
            "timestamp": error.timestamp,
            "details": error.details,
            # Exclude stack traces and original exception for security
        }
    }


def get_caller_info() -> Dict[str, Any]:
    """Get information about the caller of a function.
    
    Returns:
        A dictionary with information about the caller.
    """
    # Get the current frame and go back 2 frames to get the caller
    frame = inspect.currentframe()
    if frame is None:
        return {"module": "unknown", "function": "unknown", "line": 0}
    
    caller_frame = frame.f_back
    if caller_frame is None:
        return {"module": "unknown", "function": "unknown", "line": 0}
    
    # Get caller information
    caller_info = inspect.getframeinfo(caller_frame)
    return {
        "module": caller_info.filename,
        "function": caller_info.function,
        "line": caller_info.lineno
    }


def safe_execute(func, *args, default=None, **kwargs):
    """Safely execute a function and return a default value if it fails.
    
    Args:
        func: The function to execute.
        *args: Positional arguments to pass to the function.
        default: The default value to return if the function fails.
        **kwargs: Keyword arguments to pass to the function.
        
    Returns:
        The result of the function or the default value if it fails.
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Error executing function {func.__name__}: {str(e)}")
        return default


def handle_uncaught_exception(exc_type: Type[Exception], exc_value: Exception, exc_traceback) -> None:
    """Global exception handler for uncaught exceptions.
    
    Args:
        exc_type: The type of the exception.
        exc_value: The exception instance.
        exc_traceback: The traceback object.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't handle keyboard interrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Create a service error from the uncaught exception
    error = create_service_error(
        exc_value,
        category=categorize_exception(exc_value),
        details={"uncaught": True}
    )
    
    # Log the error
    logger.critical(f"Uncaught exception: {error.message}", extra=format_error_for_logging(error))
    
    # You might want to send this to a monitoring service or perform other actions
    # For now, just print to stderr
    sys.stderr.write(f"CRITICAL ERROR: {error.to_json()}\n")


# Set the global exception handler
def set_global_exception_handler():
    """Set the global exception handler for uncaught exceptions."""
    sys.excepthook = handle_uncaught_exception