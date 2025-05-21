#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Error handling utilities for the OCR Service.

This module provides standardized error handling utilities for creating structured error objects,
classifying errors, and formatting error messages. It enables consistent error handling across
the OCR service and facilitates proper error tracking and troubleshooting.
"""

import enum
import json
import logging
import sys
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

# Configure module logger
logger = logging.getLogger(__name__)


class ErrorCategory(enum.Enum):
    """Enumeration of error categories for classification."""
    VALIDATION = "validation"  # Input validation errors
    CONNECTION = "connection"  # Connection/network errors
    PROCESSING = "processing"  # Document processing errors
    STORAGE = "storage"        # Storage-related errors
    MESSAGING = "messaging"    # Message queue errors
    SECURITY = "security"      # Security-related errors
    SYSTEM = "system"          # System/environment errors
    UNKNOWN = "unknown"        # Unclassified errors


class ErrorSeverity(enum.Enum):
    """Enumeration of error severity levels."""
    CRITICAL = "critical"  # Service cannot continue, requires immediate attention
    ERROR = "error"        # Operation failed, but service can continue
    WARNING = "warning"    # Potential issue that doesn't prevent operation
    INFO = "info"          # Informational message about an error condition


@dataclass
class ErrorContext:
    """Context information for an error."""
    document_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    additional_info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OCRServiceError:
    """Standardized error object for OCR Service."""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    error_code: str
    context: ErrorContext = field(default_factory=ErrorContext)
    exception: Optional[Exception] = None
    traceback: Optional[str] = None
    retry_eligible: bool = False
    retry_count: int = 0
    max_retries: int = 3

    def __post_init__(self):
        """Initialize derived fields after instance creation."""
        # Capture traceback if exception is provided but traceback isn't
        if self.exception and not self.traceback:
            self.traceback = ''.join(traceback.format_exception(
                type(self.exception), self.exception, self.exception.__traceback__))

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for serialization.

        Returns:
            Dict[str, Any]: Dictionary representation of the error
        """
        error_dict = asdict(self)
        
        # Convert enum values to strings
        error_dict['category'] = self.category.value
        error_dict['severity'] = self.severity.value
        
        # Remove exception object as it's not serializable
        error_dict.pop('exception', None)
        
        return error_dict

    def to_json(self) -> str:
        """Convert error to JSON string.

        Returns:
            str: JSON representation of the error
        """
        return json.dumps(self.to_dict())

    def log(self, logger_instance: Optional[logging.Logger] = None) -> None:
        """Log the error with appropriate severity level.

        Args:
            logger_instance (Optional[logging.Logger]): Logger to use, defaults to module logger
        """
        log = logger_instance or logger
        
        # Determine log level based on severity
        if self.severity == ErrorSeverity.CRITICAL:
            log_method = log.critical
        elif self.severity == ErrorSeverity.ERROR:
            log_method = log.error
        elif self.severity == ErrorSeverity.WARNING:
            log_method = log.warning
        else:  # INFO or any other
            log_method = log.info
        
        # Log the error with context
        log_method(
            f"[{self.error_code}] {self.message}",
            extra={
                "error_category": self.category.value,
                "error_code": self.error_code,
                "document_id": self.context.document_id,
                "request_id": self.context.request_id,
                "operation": self.context.operation,
                "component": self.context.component,
                "retry_eligible": self.retry_eligible,
                "retry_count": self.retry_count
            }
        )
        
        # Log traceback for ERROR and CRITICAL levels
        if self.traceback and self.severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            log.debug(f"Traceback for error {self.error_code}:\n{self.traceback}")

    def increment_retry(self) -> bool:
        """Increment retry count and check if max retries reached.

        Returns:
            bool: True if retry is still possible, False if max retries reached
        """
        if not self.retry_eligible:
            return False
            
        self.retry_count += 1
        return self.retry_count <= self.max_retries


# Error code prefixes by category
ERROR_CODE_PREFIXES = {
    ErrorCategory.VALIDATION: "VAL",
    ErrorCategory.CONNECTION: "CONN",
    ErrorCategory.PROCESSING: "PROC",
    ErrorCategory.STORAGE: "STOR",
    ErrorCategory.MESSAGING: "MSG",
    ErrorCategory.SECURITY: "SEC",
    ErrorCategory.SYSTEM: "SYS",
    ErrorCategory.UNKNOWN: "UNK"
}

# Predefined error codes
ERROR_CODES = {
    # Validation errors
    "VAL001": "Invalid document format",
    "VAL002": "Unsupported document type",
    "VAL003": "Document size exceeds limit",
    "VAL004": "Invalid message format",
    "VAL005": "Missing required field",
    
    # Connection errors
    "CONN001": "Failed to connect to RabbitMQ",
    "CONN002": "Failed to connect to S3 storage",
    "CONN003": "Connection timeout",
    "CONN004": "Connection refused",
    "CONN005": "SSL/TLS error",
    
    # Processing errors
    "PROC001": "OCR processing failed",
    "PROC002": "Document unreadable",
    "PROC003": "Low confidence extraction",
    "PROC004": "Model inference error",
    "PROC005": "GPU resource unavailable",
    
    # Storage errors
    "STOR001": "Failed to download document from S3",
    "STOR002": "Failed to upload results to S3",
    "STOR003": "Document not found in storage",
    "STOR004": "Storage access denied",
    "STOR005": "Storage quota exceeded",
    
    # Messaging errors
    "MSG001": "Failed to publish message",
    "MSG002": "Failed to consume message",
    "MSG003": "Message acknowledgment failed",
    "MSG004": "Queue not found",
    "MSG005": "Exchange not found",
    
    # Security errors
    "SEC001": "Authentication failed",
    "SEC002": "Authorization failed",
    "SEC003": "Invalid credentials",
    "SEC004": "Token expired",
    "SEC005": "Encryption error",
    
    # System errors
    "SYS001": "Out of memory",
    "SYS002": "File system error",
    "SYS003": "Environment configuration error",
    "SYS004": "Dependency missing",
    "SYS005": "Unexpected system error",
    
    # Unknown errors
    "UNK001": "Unknown error"
}


# Map of error types to categories for automatic classification
ERROR_TYPE_CATEGORIES = {
    "ConnectionError": ErrorCategory.CONNECTION,
    "TimeoutError": ErrorCategory.CONNECTION,
    "SSLError": ErrorCategory.CONNECTION,
    "FileNotFoundError": ErrorCategory.STORAGE,
    "PermissionError": ErrorCategory.SECURITY,
    "ValueError": ErrorCategory.VALIDATION,
    "TypeError": ErrorCategory.VALIDATION,
    "KeyError": ErrorCategory.VALIDATION,
    "IndexError": ErrorCategory.VALIDATION,
    "MemoryError": ErrorCategory.SYSTEM,
    "ImportError": ErrorCategory.SYSTEM,
    "ModuleNotFoundError": ErrorCategory.SYSTEM,
    "RuntimeError": ErrorCategory.PROCESSING,
    "Exception": ErrorCategory.UNKNOWN
}


# Map of error categories to default severity levels
DEFAULT_SEVERITY = {
    ErrorCategory.VALIDATION: ErrorSeverity.ERROR,
    ErrorCategory.CONNECTION: ErrorSeverity.ERROR,
    ErrorCategory.PROCESSING: ErrorSeverity.ERROR,
    ErrorCategory.STORAGE: ErrorSeverity.ERROR,
    ErrorCategory.MESSAGING: ErrorSeverity.ERROR,
    ErrorCategory.SECURITY: ErrorSeverity.CRITICAL,
    ErrorCategory.SYSTEM: ErrorSeverity.CRITICAL,
    ErrorCategory.UNKNOWN: ErrorSeverity.ERROR
}


# Map of error categories to retry eligibility
RETRY_ELIGIBLE_CATEGORIES = {
    ErrorCategory.VALIDATION: False,
    ErrorCategory.CONNECTION: True,
    ErrorCategory.PROCESSING: True,
    ErrorCategory.STORAGE: True,
    ErrorCategory.MESSAGING: True,
    ErrorCategory.SECURITY: False,
    ErrorCategory.SYSTEM: False,
    ErrorCategory.UNKNOWN: False
}


# Specific error codes that are not retry-eligible despite their category
NON_RETRYABLE_ERROR_CODES = [
    "VAL001", "VAL002", "VAL003", "VAL004", "VAL005",  # All validation errors
    "PROC002", "PROC003",  # Unreadable document, low confidence
    "STOR003", "STOR004", "STOR005",  # Document not found, access denied, quota exceeded
    "MSG004", "MSG005",  # Queue not found, exchange not found
    "SEC001", "SEC002", "SEC003", "SEC004", "SEC005",  # All security errors
    "SYS001", "SYS002", "SYS003", "SYS004", "SYS005",  # All system errors
    "UNK001"  # Unknown error
]


def classify_exception(exception: Exception) -> ErrorCategory:
    """Classify an exception into an error category.

    Args:
        exception (Exception): The exception to classify

    Returns:
        ErrorCategory: The classified error category
    """
    exception_type = type(exception).__name__
    return ERROR_TYPE_CATEGORIES.get(exception_type, ErrorCategory.UNKNOWN)


def generate_error_code(category: ErrorCategory, specific_code: Optional[int] = None) -> str:
    """Generate an error code based on category and specific code.

    Args:
        category (ErrorCategory): The error category
        specific_code (Optional[int]): Specific code number within the category

    Returns:
        str: The generated error code
    """
    prefix = ERROR_CODE_PREFIXES.get(category, "UNK")
    
    if specific_code is not None:
        return f"{prefix}{specific_code:03d}"
    
    # If no specific code provided, use the first code for the category
    for code in ERROR_CODES:
        if code.startswith(prefix):
            return code
    
    # Fallback to unknown error
    return "UNK001"


def is_retry_eligible(error_code: str, category: ErrorCategory) -> bool:
    """Determine if an error is eligible for retry based on its code and category.

    Args:
        error_code (str): The error code
        category (ErrorCategory): The error category

    Returns:
        bool: True if the error is retry-eligible, False otherwise
    """
    # Check if the error code is in the non-retryable list
    if error_code in NON_RETRYABLE_ERROR_CODES:
        return False
    
    # Otherwise, use the category's default retry eligibility
    return RETRY_ELIGIBLE_CATEGORIES.get(category, False)


def create_error(
    message: str,
    error_code: str,
    category: Optional[ErrorCategory] = None,
    severity: Optional[ErrorSeverity] = None,
    exception: Optional[Exception] = None,
    context: Optional[ErrorContext] = None,
    retry_eligible: Optional[bool] = None,
    max_retries: int = 3
) -> OCRServiceError:
    """Create a standardized OCR service error.

    Args:
        message (str): Error message
        error_code (str): Error code
        category (Optional[ErrorCategory]): Error category, derived from error_code if None
        severity (Optional[ErrorSeverity]): Error severity, derived from category if None
        exception (Optional[Exception]): Original exception if any
        context (Optional[ErrorContext]): Error context information
        retry_eligible (Optional[bool]): Whether the error is eligible for retry
        max_retries (int): Maximum number of retries for this error

    Returns:
        OCRServiceError: Standardized error object
    """
    # If category not provided, derive it from error code prefix
    if category is None:
        prefix = error_code[:3] if len(error_code) >= 3 else "UNK"
        category_found = False
        
        for cat, cat_prefix in ERROR_CODE_PREFIXES.items():
            if prefix == cat_prefix:
                category = cat
                category_found = True
                break
        
        if not category_found:
            category = ErrorCategory.UNKNOWN
    
    # If severity not provided, use default for the category
    if severity is None:
        severity = DEFAULT_SEVERITY.get(category, ErrorSeverity.ERROR)
    
    # If retry_eligible not provided, determine based on error code and category
    if retry_eligible is None:
        retry_eligible = is_retry_eligible(error_code, category)
    
    # Create context if not provided
    if context is None:
        context = ErrorContext()
    
    # Create the error object
    return OCRServiceError(
        message=message,
        category=category,
        severity=severity,
        error_code=error_code,
        context=context,
        exception=exception,
        retry_eligible=retry_eligible,
        max_retries=max_retries
    )


def create_error_from_exception(
    exception: Exception,
    operation: Optional[str] = None,
    component: Optional[str] = None,
    document_id: Optional[str] = None,
    request_id: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    max_retries: int = 3
) -> OCRServiceError:
    """Create a standardized error from an exception.

    Args:
        exception (Exception): The exception to convert
        operation (Optional[str]): Operation being performed when the error occurred
        component (Optional[str]): Component where the error occurred
        document_id (Optional[str]): ID of the document being processed
        request_id (Optional[str]): ID of the request being processed
        additional_info (Optional[Dict[str, Any]]): Additional context information
        max_retries (int): Maximum number of retries for this error

    Returns:
        OCRServiceError: Standardized error object
    """
    # Classify the exception
    category = classify_exception(exception)
    
    # Generate an error code based on the category
    error_code = generate_error_code(category)
    
    # Determine if the error is retry-eligible
    retry_eligible = is_retry_eligible(error_code, category)
    
    # Create context
    context = ErrorContext(
        document_id=document_id,
        request_id=request_id,
        operation=operation,
        component=component,
        additional_info=additional_info or {}
    )
    
    # Create the error object
    return OCRServiceError(
        message=str(exception),
        category=category,
        severity=DEFAULT_SEVERITY.get(category, ErrorSeverity.ERROR),
        error_code=error_code,
        context=context,
        exception=exception,
        retry_eligible=retry_eligible,
        max_retries=max_retries
    )


def enrich_error_context(
    error: OCRServiceError,
    document_id: Optional[str] = None,
    request_id: Optional[str] = None,
    operation: Optional[str] = None,
    component: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None
) -> OCRServiceError:
    """Enrich an error with additional context information.

    Args:
        error (OCRServiceError): The error to enrich
        document_id (Optional[str]): ID of the document being processed
        request_id (Optional[str]): ID of the request being processed
        operation (Optional[str]): Operation being performed when the error occurred
        component (Optional[str]): Component where the error occurred
        additional_info (Optional[Dict[str, Any]]): Additional context information

    Returns:
        OCRServiceError: The enriched error
    """
    # Update context fields if provided
    if document_id is not None:
        error.context.document_id = document_id
    
    if request_id is not None:
        error.context.request_id = request_id
    
    if operation is not None:
        error.context.operation = operation
    
    if component is not None:
        error.context.component = component
    
    # Update additional info if provided
    if additional_info is not None:
        error.context.additional_info.update(additional_info)
    
    return error


def format_error_for_response(error: OCRServiceError) -> Dict[str, Any]:
    """Format an error for API response.

    Args:
        error (OCRServiceError): The error to format

    Returns:
        Dict[str, Any]: Formatted error response
    """
    return {
        "error": {
            "code": error.error_code,
            "message": error.message,
            "category": error.category.value,
            "timestamp": error.context.timestamp,
            "request_id": error.context.request_id
        }
    }


def format_error_for_message(error: OCRServiceError) -> Dict[str, Any]:
    """Format an error for inclusion in a RabbitMQ message.

    Args:
        error (OCRServiceError): The error to format

    Returns:
        Dict[str, Any]: Formatted error for message
    """
    return {
        "error": {
            "code": error.error_code,
            "message": error.message,
            "category": error.category.value,
            "severity": error.severity.value,
            "document_id": error.context.document_id,
            "request_id": error.context.request_id,
            "operation": error.context.operation,
            "component": error.context.component,
            "timestamp": error.context.timestamp,
            "retry_count": error.retry_count,
            "additional_info": error.context.additional_info
        }
    }


def handle_uncaught_exception(exc_type: Type[Exception], exc_value: Exception, exc_traceback: Any) -> None:
    """Global exception handler for uncaught exceptions.

    Args:
        exc_type (Type[Exception]): Exception type
        exc_value (Exception): Exception value
        exc_traceback (Any): Exception traceback
    """
    # Don't handle KeyboardInterrupt
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Create a standardized error
    error = create_error_from_exception(
        exception=exc_value,
        operation="uncaught_exception",
        component="global_exception_handler"
    )
    
    # Log the error
    error.log()
    
    # Call the original exception handler
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def setup_global_exception_handler() -> None:
    """Set up the global exception handler for uncaught exceptions."""
    sys.excepthook = handle_uncaught_exception