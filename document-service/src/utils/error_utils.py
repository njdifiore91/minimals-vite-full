#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error handling utilities for the Document Service.

This module provides standardized error handling utilities for the Document Service,
including error classification, structured error objects, error context enrichment,
retry eligibility determination, and error serialization for logging and message publishing.
"""

import json
import logging
import traceback
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union

# Configure logger
logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Enumeration of error types for classification."""
    VALIDATION = auto()       # Input validation errors
    CONNECTION = auto()       # Connection errors (RabbitMQ, S3, etc.)
    PROCESSING = auto()       # Document processing errors
    CLASSIFICATION = auto()   # Document classification errors
    STORAGE = auto()          # Storage-related errors (S3, etc.)
    CONFIGURATION = auto()    # Configuration errors
    INTERNAL = auto()         # Internal service errors
    UNKNOWN = auto()          # Unknown errors


class ErrorSeverity(Enum):
    """Enumeration of error severity levels."""
    INFO = auto()        # Informational, non-critical errors
    WARNING = auto()     # Warning, potentially problematic but non-blocking
    ERROR = auto()       # Error, operation failed but service can continue
    CRITICAL = auto()    # Critical, service operation is compromised


class RetryStrategy(Enum):
    """Enumeration of retry strategies for different error types."""
    NO_RETRY = auto()             # Do not retry
    IMMEDIATE_RETRY = auto()      # Retry immediately
    EXPONENTIAL_BACKOFF = auto()  # Retry with exponential backoff
    LINEAR_BACKOFF = auto()       # Retry with linear backoff


class DocumentServiceError(Exception):
    """Base exception class for Document Service errors."""
    
    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        retry_strategy: RetryStrategy = RetryStrategy.NO_RETRY,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        super().__init__(message)
        self.message = message
        self.error_type = error_type
        self.severity = severity
        self.retry_strategy = retry_strategy
        self.context = context or {}
        self.cause = cause
        self.timestamp = datetime.utcnow().isoformat()
        self.retry_count = retry_count
        self.max_retries = max_retries
        self.traceback = traceback.format_exc() if cause else None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization."""
        error_dict = {
            "message": self.message,
            "error_type": self.error_type.name,
            "severity": self.severity.name,
            "retry_strategy": self.retry_strategy.name,
            "context": self.context,
            "timestamp": self.timestamp,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }
        
        if self.cause:
            error_dict["cause"] = str(self.cause)
            
        if self.traceback and self.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            error_dict["traceback"] = self.traceback
            
        return error_dict
    
    def to_json(self) -> str:
        """Convert error to JSON string for logging or message publishing."""
        return json.dumps(self.to_dict())
    
    def is_retriable(self) -> bool:
        """Determine if the error is eligible for retry."""
        return (
            self.retry_strategy != RetryStrategy.NO_RETRY and 
            self.retry_count < self.max_retries
        )
    
    def increment_retry(self) -> 'DocumentServiceError':
        """Increment retry count and return self for chaining."""
        self.retry_count += 1
        return self
    
    def with_context(self, **kwargs) -> 'DocumentServiceError':
        """Add additional context to the error and return self for chaining."""
        self.context.update(kwargs)
        return self


# Specific error classes for common error types
class ValidationError(DocumentServiceError):
    """Error raised when input validation fails."""
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        field: Optional[str] = None,
        value: Optional[Any] = None,
    ):
        context = context or {}
        if field is not None:
            context["field"] = field
        if value is not None:
            context["value"] = str(value)
            
        super().__init__(
            message=message,
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.WARNING,
            retry_strategy=RetryStrategy.NO_RETRY,
            context=context,
            cause=cause,
        )


class ConnectionError(DocumentServiceError):
    """Error raised when a connection to an external service fails."""
    
    def __init__(
        self,
        message: str,
        service: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        context = context or {}
        context["service"] = service
        
        super().__init__(
            message=message,
            error_type=ErrorType.CONNECTION,
            severity=ErrorSeverity.ERROR,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            context=context,
            cause=cause,
            retry_count=retry_count,
            max_retries=max_retries,
        )


class ProcessingError(DocumentServiceError):
    """Error raised when document processing fails."""
    
    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        processing_stage: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 2,
    ):
        context = context or {}
        if document_id is not None:
            context["document_id"] = document_id
        if processing_stage is not None:
            context["processing_stage"] = processing_stage
            
        super().__init__(
            message=message,
            error_type=ErrorType.PROCESSING,
            severity=ErrorSeverity.ERROR,
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            context=context,
            cause=cause,
            retry_count=retry_count,
            max_retries=max_retries,
        )


class ClassificationError(DocumentServiceError):
    """Error raised when document classification fails."""
    
    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        confidence_score: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 1,
    ):
        context = context or {}
        if document_id is not None:
            context["document_id"] = document_id
        if confidence_score is not None:
            context["confidence_score"] = confidence_score
            
        super().__init__(
            message=message,
            error_type=ErrorType.CLASSIFICATION,
            severity=ErrorSeverity.ERROR,
            retry_strategy=RetryStrategy.IMMEDIATE_RETRY,
            context=context,
            cause=cause,
            retry_count=retry_count,
            max_retries=max_retries,
        )


class StorageError(DocumentServiceError):
    """Error raised when storage operations fail."""
    
    def __init__(
        self,
        message: str,
        storage_type: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        retry_count: int = 0,
        max_retries: int = 3,
    ):
        context = context or {}
        context["storage_type"] = storage_type
        context["operation"] = operation
        
        super().__init__(
            message=message,
            error_type=ErrorType.STORAGE,
            severity=ErrorSeverity.ERROR,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            context=context,
            cause=cause,
            retry_count=retry_count,
            max_retries=max_retries,
        )


# Utility functions for error handling
def create_error(
    message: str,
    error_type: ErrorType,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    retry_strategy: RetryStrategy = RetryStrategy.NO_RETRY,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
    retry_count: int = 0,
    max_retries: int = 3,
) -> DocumentServiceError:
    """Create a DocumentServiceError with the specified parameters.
    
    Args:
        message: Error message
        error_type: Type of error
        severity: Error severity level
        retry_strategy: Strategy for retrying operations
        context: Additional context information
        cause: Original exception that caused this error
        retry_count: Current retry attempt count
        max_retries: Maximum number of retry attempts
        
    Returns:
        DocumentServiceError: Configured error object
    """
    return DocumentServiceError(
        message=message,
        error_type=error_type,
        severity=severity,
        retry_strategy=retry_strategy,
        context=context,
        cause=cause,
        retry_count=retry_count,
        max_retries=max_retries,
    )


def create_validation_error(
    message: str,
    field: Optional[str] = None,
    value: Optional[Any] = None,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
) -> ValidationError:
    """Create a ValidationError for input validation failures.
    
    Args:
        message: Error message
        field: Name of the field that failed validation
        value: Invalid value that caused the validation failure
        context: Additional context information
        cause: Original exception that caused this error
        
    Returns:
        ValidationError: Configured validation error
    """
    return ValidationError(
        message=message,
        field=field,
        value=value,
        context=context,
        cause=cause,
    )


def create_connection_error(
    message: str,
    service: str,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
    retry_count: int = 0,
    max_retries: int = 3,
) -> ConnectionError:
    """Create a ConnectionError for external service connection failures.
    
    Args:
        message: Error message
        service: Name of the service that failed to connect
        context: Additional context information
        cause: Original exception that caused this error
        retry_count: Current retry attempt count
        max_retries: Maximum number of retry attempts
        
    Returns:
        ConnectionError: Configured connection error
    """
    return ConnectionError(
        message=message,
        service=service,
        context=context,
        cause=cause,
        retry_count=retry_count,
        max_retries=max_retries,
    )


def create_processing_error(
    message: str,
    document_id: Optional[str] = None,
    processing_stage: Optional[str] = None,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
    retry_count: int = 0,
    max_retries: int = 2,
) -> ProcessingError:
    """Create a ProcessingError for document processing failures.
    
    Args:
        message: Error message
        document_id: ID of the document being processed
        processing_stage: Stage of processing where the error occurred
        context: Additional context information
        cause: Original exception that caused this error
        retry_count: Current retry attempt count
        max_retries: Maximum number of retry attempts
        
    Returns:
        ProcessingError: Configured processing error
    """
    return ProcessingError(
        message=message,
        document_id=document_id,
        processing_stage=processing_stage,
        context=context,
        cause=cause,
        retry_count=retry_count,
        max_retries=max_retries,
    )


def create_classification_error(
    message: str,
    document_id: Optional[str] = None,
    confidence_score: Optional[float] = None,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
    retry_count: int = 0,
    max_retries: int = 1,
) -> ClassificationError:
    """Create a ClassificationError for document classification failures.
    
    Args:
        message: Error message
        document_id: ID of the document being classified
        confidence_score: Confidence score of the classification
        context: Additional context information
        cause: Original exception that caused this error
        retry_count: Current retry attempt count
        max_retries: Maximum number of retry attempts
        
    Returns:
        ClassificationError: Configured classification error
    """
    return ClassificationError(
        message=message,
        document_id=document_id,
        confidence_score=confidence_score,
        context=context,
        cause=cause,
        retry_count=retry_count,
        max_retries=max_retries,
    )


def create_storage_error(
    message: str,
    storage_type: str,
    operation: str,
    context: Optional[Dict[str, Any]] = None,
    cause: Optional[Exception] = None,
    retry_count: int = 0,
    max_retries: int = 3,
) -> StorageError:
    """Create a StorageError for storage operation failures.
    
    Args:
        message: Error message
        storage_type: Type of storage (S3, etc.)
        operation: Operation that failed (read, write, etc.)
        context: Additional context information
        cause: Original exception that caused this error
        retry_count: Current retry attempt count
        max_retries: Maximum number of retry attempts
        
    Returns:
        StorageError: Configured storage error
    """
    return StorageError(
        message=message,
        storage_type=storage_type,
        operation=operation,
        context=context,
        cause=cause,
        retry_count=retry_count,
        max_retries=max_retries,
    )


def enrich_error_context(
    error: DocumentServiceError,
    **kwargs
) -> DocumentServiceError:
    """Enrich an error with additional context information.
    
    Args:
        error: The error to enrich
        **kwargs: Additional context key-value pairs
        
    Returns:
        DocumentServiceError: The enriched error
    """
    return error.with_context(**kwargs)


def is_retriable_error(error: Exception) -> bool:
    """Determine if an error is eligible for retry.
    
    Args:
        error: The error to check
        
    Returns:
        bool: True if the error is retriable, False otherwise
    """
    if isinstance(error, DocumentServiceError):
        return error.is_retriable()
    
    # Default retry behavior for standard exceptions
    retriable_exceptions = (
        ConnectionResetError,
        TimeoutError,
        BrokenPipeError,
    )
    
    return isinstance(error, retriable_exceptions)


def get_retry_delay(error: DocumentServiceError, base_delay: float = 1.0) -> float:
    """Calculate the retry delay based on the error's retry strategy.
    
    Args:
        error: The error to calculate delay for
        base_delay: Base delay in seconds
        
    Returns:
        float: Delay in seconds before the next retry
    """
    if not isinstance(error, DocumentServiceError):
        return base_delay
    
    if error.retry_strategy == RetryStrategy.IMMEDIATE_RETRY:
        return 0.0
    
    if error.retry_strategy == RetryStrategy.LINEAR_BACKOFF:
        return base_delay * (error.retry_count + 1)
    
    if error.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
        return base_delay * (2 ** error.retry_count)
    
    return 0.0  # No retry


def log_error(error: Union[DocumentServiceError, Exception], logger: logging.Logger = logger) -> None:
    """Log an error with appropriate severity level.
    
    Args:
        error: The error to log
        logger: Logger to use (defaults to module logger)
    """
    if isinstance(error, DocumentServiceError):
        error_dict = error.to_dict()
        error_json = json.dumps(error_dict)
        
        if error.severity == ErrorSeverity.INFO:
            logger.info(f"INFO: {error.message} - {error_json}")
        elif error.severity == ErrorSeverity.WARNING:
            logger.warning(f"WARNING: {error.message} - {error_json}")
        elif error.severity == ErrorSeverity.ERROR:
            logger.error(f"ERROR: {error.message} - {error_json}")
        elif error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"CRITICAL: {error.message} - {error_json}")
    else:
        logger.error(f"Unhandled exception: {str(error)}\n{traceback.format_exc()}")


def format_error_for_rabbitmq(error: DocumentServiceError) -> Dict[str, Any]:
    """Format an error for publishing to RabbitMQ.
    
    Args:
        error: The error to format
        
    Returns:
        Dict[str, Any]: Formatted error message for RabbitMQ
    """
    error_dict = error.to_dict()
    
    # Add additional fields for RabbitMQ message
    error_dict["service"] = "document-service"
    error_dict["error_id"] = f"doc-svc-err-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
    
    return error_dict


def handle_exception(
    func: callable,
    *args,
    error_message: str = "An error occurred during operation",
    error_type: ErrorType = ErrorType.UNKNOWN,
    **kwargs
) -> Tuple[bool, Any, Optional[DocumentServiceError]]:
    """Execute a function and handle any exceptions.
    
    Args:
        func: Function to execute
        *args: Arguments to pass to the function
        error_message: Message to use if an exception occurs
        error_type: Type of error to create if an exception occurs
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple[bool, Any, Optional[DocumentServiceError]]: 
            - Success flag
            - Result of the function if successful, None otherwise
            - Error object if an error occurred, None otherwise
    """
    try:
        result = func(*args, **kwargs)
        return True, result, None
    except DocumentServiceError as e:
        log_error(e)
        return False, None, e
    except Exception as e:
        error = create_error(
            message=error_message,
            error_type=error_type,
            cause=e,
        )
        log_error(error)
        return False, None, error


def retry_operation(
    operation: callable,
    *args,
    max_retries: int = 3,
    base_delay: float = 1.0,
    error_message: str = "Operation failed",
    error_type: ErrorType = ErrorType.UNKNOWN,
    on_retry: Optional[callable] = None,
    **kwargs
) -> Tuple[bool, Any, Optional[DocumentServiceError]]:
    """Retry an operation with exponential backoff.
    
    Args:
        operation: Function to execute
        *args: Arguments to pass to the function
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        error_message: Message to use if all retries fail
        error_type: Type of error to create if all retries fail
        on_retry: Callback function to execute before each retry
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple[bool, Any, Optional[DocumentServiceError]]: 
            - Success flag
            - Result of the function if successful, None otherwise
            - Error object if all retries failed, None otherwise
    """
    import time
    
    retry_count = 0
    last_error = None
    
    while retry_count <= max_retries:
        try:
            result = operation(*args, **kwargs)
            return True, result, None
        except Exception as e:
            retry_count += 1
            
            if isinstance(e, DocumentServiceError):
                error = e.increment_retry()
            else:
                error = create_error(
                    message=error_message,
                    error_type=error_type,
                    cause=e,
                    retry_count=retry_count,
                    max_retries=max_retries,
                )
            
            last_error = error
            log_error(error)
            
            if retry_count <= max_retries and is_retriable_error(error):
                delay = get_retry_delay(error, base_delay) if isinstance(error, DocumentServiceError) else base_delay
                
                logger.info(f"Retrying operation (attempt {retry_count}/{max_retries}) after {delay:.2f}s delay")
                
                if on_retry is not None:
                    on_retry(error, retry_count, max_retries)
                    
                time.sleep(delay)
            else:
                break
    
    return False, None, last_error