"""Type definitions for error handling, logging, and monitoring used by the OCR Service.

This module provides type hints for standardized error structures, logging formats,
and error classification. It ensures consistent error handling and logging throughout
the OCR processing pipeline, making troubleshooting and monitoring more effective.
"""

from __future__ import annotations

import enum
import json
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Generic, List, Optional, Tuple, TypedDict, TypeVar, Union, cast


class LogLevel(enum.Enum):
    """Log levels for the OCR Service.
    
    These log levels correspond to the standard logging levels used throughout
    the OCR Service, as specified in section 0.2.5 of the technical specification.
    """
    
    ERROR = "ERROR"  # Processing failures
    WARN = "WARN"    # Potential issues
    INFO = "INFO"    # Normal operations
    DEBUG = "DEBUG"  # Troubleshooting (development only)


class ErrorCategory(enum.Enum):
    """Categories of errors that can occur in the OCR Service.
    
    These categories help classify errors for better troubleshooting,
    monitoring, and reporting.
    """
    
    VALIDATION = "validation"          # Input validation errors
    PROCESSING = "processing"          # Document processing errors
    EXTRACTION = "extraction"          # Text extraction errors
    STORAGE = "storage"                # Document storage errors
    MESSAGING = "messaging"            # Message queue errors
    CONFIGURATION = "configuration"    # Configuration errors
    AUTHENTICATION = "authentication"  # Authentication errors
    AUTHORIZATION = "authorization"    # Authorization errors
    NETWORK = "network"                # Network-related errors
    DATABASE = "database"              # Database-related errors
    TIMEOUT = "timeout"                # Timeout errors
    RESOURCE = "resource"              # Resource allocation errors
    DEPENDENCY = "dependency"          # External dependency errors
    UNKNOWN = "unknown"                # Unclassified errors


class ErrorDetails(TypedDict):
    """Detailed information about an error.
    
    This type captures detailed information about an error, including
    the error message, stack trace, and additional context.
    """
    
    message: str                  # Error message
    error_type: str               # Type of error (exception class name)
    timestamp: datetime           # When the error occurred
    stack_trace: str              # Stack trace as a string
    context: Dict[str, Any]       # Additional context information
    service_name: str             # Name of the service where the error occurred
    document_id: Optional[str]    # ID of the document being processed (if applicable)
    request_id: Optional[str]     # ID of the request being processed (if applicable)


@dataclass
class ServiceError(Exception):
    """Standardized error for the OCR Service.
    
    This class extends Exception to provide a standardized error structure
    with additional context and categorization.
    """
    
    message: str  # Error message
    category: ErrorCategory  # Error category
    details: Optional[Dict[str, Any]] = None  # Detailed error information
    status_code: Optional[int] = None  # HTTP status code if applicable
    
    def __post_init__(self):
        """Initialize the exception with the error message."""
        super().__init__(self.message)
    
    @classmethod
    def from_exception(cls, exception: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                      context: Dict[str, Any] = None, status_code: Optional[int] = None) -> 'ServiceError':
        """Create a ServiceError from an exception.
        
        Args:
            exception: The original exception
            category: Error category
            context: Additional context information
            status_code: HTTP status code if applicable
            
        Returns:
            A new ServiceError instance
        """
        if context is None:
            context = {}
            
        error_details = {
            "message": str(exception),
            "error_type": exception.__class__.__name__,
            "timestamp": datetime.now(),
            "stack_trace": traceback.format_exc(),
            "context": context,
            "service_name": "ocr-service",
            "document_id": context.get("document_id"),
            "request_id": context.get("request_id")
        }
        
        return cls(
            message=str(exception),
            category=category,
            details=error_details,
            status_code=status_code
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of service error
        """
        result = {
            "message": self.message,
            "category": self.category.value,
            "status_code": self.status_code
        }
        
        if self.details:
            result["details"] = self.details
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON string representation of service error
        """
        return json.dumps(self.to_dict())


@dataclass
class LogEntry:
    """Structured log entry for the OCR Service.
    
    This class provides a standardized structure for log entries,
    including timestamp, level, message, and context information.
    """
    
    message: str  # Log message
    level: LogLevel  # Log level
    service_name: str = "ocr-service"  # Name of the service
    timestamp: datetime = field(default_factory=datetime.now)  # When the log entry was created
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
    error: Optional[Dict[str, Any]] = None  # Error details if applicable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of log entry
        """
        result = {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "message": self.message,
            "service_name": self.service_name,
            "context": self.context
        }
        
        if self.error:
            result["error"] = self.error
            
        return result
    
    def to_json(self) -> str:
        """Convert log entry to JSON string.
        
        Returns:
            JSON string representation of log entry
        """
        return json.dumps(self.to_dict())


@dataclass
class MonitoringAlert:
    """Alert for monitoring systems.
    
    This class provides a standardized structure for alerts that can be
    sent to monitoring systems for critical errors.
    """
    
    title: str  # Alert title
    message: str  # Alert message
    severity: str  # Alert severity (critical, warning, info)
    service_name: str = "ocr-service"  # Name of the service
    timestamp: datetime = field(default_factory=datetime.now)  # When the alert was created
    error: Optional[Dict[str, Any]] = None  # Error details if applicable
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of monitoring alert
        """
        result = {
            "title": self.title,
            "message": self.message,
            "severity": self.severity,
            "service_name": self.service_name,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }
        
        if self.error:
            result["error"] = self.error
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON string representation of monitoring alert
        """
        return json.dumps(self.to_dict())


# Generic type for operation results
T = TypeVar('T')


@dataclass
class Result(Generic[T]):
    """Generic result type for operations that may fail.
    
    This class provides a standardized way to handle operation results,
    including success/failure status, result value, and error information.
    """
    
    success: bool  # Whether the operation was successful
    value: Optional[T] = None  # Result value if successful
    error: Optional[ServiceError] = None  # Error information if failed
    
    @classmethod
    def ok(cls, value: T) -> 'Result[T]':
        """Create a successful result with a value.
        
        Args:
            value: The result value
            
        Returns:
            A successful Result instance with the provided value
        """
        return cls(success=True, value=value)
    
    @classmethod
    def fail(cls, error: ServiceError) -> 'Result[T]':
        """Create a failed result with an error.
        
        Args:
            error: The error that caused the failure
            
        Returns:
            A failed Result instance with the provided error
        """
        return cls(success=False, error=error)
    
    @classmethod
    def from_exception(cls, exception: Exception, category: ErrorCategory = ErrorCategory.UNKNOWN, 
                      context: Dict[str, Any] = None) -> 'Result[T]':
        """Create a failed result from an exception.
        
        Args:
            exception: The exception that caused the failure
            category: Error category
            context: Additional context information
            
        Returns:
            A failed Result instance with a ServiceError created from the exception
        """
        error = ServiceError.from_exception(exception, category, context)
        return cls.fail(error)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation.
        
        Returns:
            Dictionary representation of result
        """
        result = {"success": self.success}
        
        if self.success and self.value is not None:
            # Handle different types of values
            if hasattr(self.value, 'to_dict'):
                result["value"] = self.value.to_dict()
            elif isinstance(self.value, dict):
                result["value"] = self.value
            elif isinstance(self.value, list):
                # Handle list of objects with to_dict method
                if all(hasattr(item, 'to_dict') for item in self.value):
                    result["value"] = [item.to_dict() for item in self.value]
                else:
                    result["value"] = self.value
            else:
                # Try to convert to a serializable value
                try:
                    json.dumps({"test": self.value})
                    result["value"] = self.value
                except (TypeError, OverflowError):
                    # If not JSON serializable, convert to string
                    result["value"] = str(self.value)
        
        if not self.success and self.error:
            result["error"] = self.error.to_dict()
            
        return result
    
    def to_json(self) -> str:
        """Convert to JSON string.
        
        Returns:
            JSON string representation of result
        """
        return json.dumps(self.to_dict())