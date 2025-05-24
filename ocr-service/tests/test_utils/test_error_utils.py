#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the error_utils module.

This module contains tests for the error handling utilities in the OCR Service,
including error classification, context enrichment, retry eligibility determination,
and error serialization for logging and message publishing.

These tests ensure that the OCR Service can properly handle errors in various scenarios:
1. Error handling for unreadable documents or processing failures (section 4.1.8)
2. Connection error handling and recovery strategies (section 4.1.8)
3. Retry logic for RabbitMQ message publishing (section 4.1.8)

The test suite validates:
- Standardized error handling functions
- Error classification (validation, connection, processing)
- Error context enrichment functions
- Retry eligibility determination based on error type
- Error serialization for logging and message publishing
"""

import json
import logging
import sys
import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

# Import the error_utils module - adjust the import path as needed for your project structure
from src.utils.error_utils import (
    ErrorCategory,
    ErrorSeverity,
    RetryStrategy,
    ServiceError,
    calculate_retry_delay,
    categorize_exception,
    create_service_error,
    enrich_error_context,
    format_error_for_logging,
    format_error_for_publishing,
    get_caller_info,
    handle_boto_error,
    handle_uncaught_exception,
    increment_retry_count,
    is_retry_eligible,
    safe_execute,
    set_global_exception_handler,
)

# Import StorageErrorCode - handle the case where it might not be available
try:
    from src.types.storage import StorageErrorCode
except ImportError:
    # Define a fallback if the import fails, matching the fallback in error_utils.py
    from enum import Enum, auto
    class StorageErrorCode(Enum):
        CONNECTION_ERROR = auto()
        AUTHENTICATION_ERROR = auto()
        PERMISSION_DENIED = auto()
        RESOURCE_NOT_FOUND = auto()
        BUCKET_NOT_FOUND = auto()
        OBJECT_NOT_FOUND = auto()
        INVALID_REQUEST = auto()
        TIMEOUT = auto()
        INTERNAL_ERROR = auto()
        UNKNOWN_ERROR = auto()


# Fixtures
@pytest.fixture
def sample_exception():
    """Return a sample exception for testing."""
    return ValueError("Invalid document format")


@pytest.fixture
def connection_exception():
    """Return a connection exception for testing."""
    return ConnectionError("Failed to connect to RabbitMQ")


@pytest.fixture
def system_exception():
    """Return a system exception for testing."""
    return MemoryError("Out of memory")


@pytest.fixture
def service_error():
    """Return a sample ServiceError for testing."""
    return ServiceError(
        message="Test error",
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.MEDIUM,
        retry_strategy=RetryStrategy.EXPONENTIAL,
        details={"document_id": "doc123", "retry_count": 0},
    )


@pytest.fixture
def boto3_client_error():
    """Return a mocked boto3 ClientError for testing."""
    error_response = {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}}
    return MagicMock(
        response=error_response,
        __str__=lambda self: "An error occurred (NoSuchKey) when calling the GetObject operation: The specified key does not exist."
    )


# Test ServiceError class
class TestServiceError:
    """Tests for the ServiceError class."""

    def test_init(self):
        """Test ServiceError initialization."""
        error = ServiceError(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            retry_strategy=RetryStrategy.NONE,
            details={"test": "value"},
        )

        assert error.message == "Test error"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.retry_strategy == RetryStrategy.NONE
        assert error.details == {"test": "value"}
        assert error.original_exception is None
        assert isinstance(error.timestamp, str)
        assert isinstance(error.trace, list)

    def test_to_dict(self, service_error):
        """Test conversion to dictionary."""
        error_dict = service_error.to_dict()

        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "PROCESSING"
        assert error_dict["severity"] == "MEDIUM"
        assert error_dict["retry_strategy"] == "EXPONENTIAL"
        assert error_dict["details"] == {"document_id": "doc123", "retry_count": 0}
        assert error_dict["original_exception"] is None
        assert isinstance(error_dict["timestamp"], str)
        assert isinstance(error_dict["trace"], list)

    def test_to_json(self, service_error):
        """Test conversion to JSON."""
        error_json = service_error.to_json()
        error_dict = json.loads(error_json)

        assert error_dict["message"] == "Test error"
        assert error_dict["category"] == "PROCESSING"
        assert error_dict["severity"] == "MEDIUM"
        assert error_dict["retry_strategy"] == "EXPONENTIAL"
        assert error_dict["details"] == {"document_id": "doc123", "retry_count": 0}


# Test create_service_error function
class TestCreateServiceError:
    """Tests for the create_service_error function."""

    def test_create_with_defaults(self, sample_exception):
        """Test creating a ServiceError with default values."""
        error = create_service_error(sample_exception)

        assert error.message == str(sample_exception)
        assert error.category == ErrorCategory.UNKNOWN
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.retry_strategy == RetryStrategy.NONE
        assert error.original_exception == sample_exception
        assert error.details == {}

    def test_create_with_custom_values(self, sample_exception):
        """Test creating a ServiceError with custom values."""
        error = create_service_error(
            sample_exception,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.LOW,
            retry_strategy=RetryStrategy.IMMEDIATE,
            details={"test": "value"},
        )

        assert error.message == str(sample_exception)
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.LOW
        assert error.retry_strategy == RetryStrategy.IMMEDIATE
        assert error.original_exception == sample_exception
        assert error.details == {"test": "value"}

    def test_create_with_auto_severity(self, connection_exception):
        """Test automatic severity determination."""
        error = create_service_error(
            connection_exception,
            category=ErrorCategory.CONNECTION,
        )

        assert error.severity == ErrorSeverity.HIGH

    def test_create_with_auto_retry_strategy(self, connection_exception):
        """Test automatic retry strategy determination."""
        error = create_service_error(
            connection_exception,
            category=ErrorCategory.CONNECTION,
        )

        assert error.retry_strategy == RetryStrategy.EXPONENTIAL
        
    def test_document_processing_failure_handling(self):
        """Test error handling for unreadable documents or processing failures.
        
        This test verifies the error handling for document processing failures
        as required in section 4.1.8 of the technical specification.
        """
        # Define custom OCR processing exceptions
        class OCRProcessingError(Exception):
            pass
            
        class DocumentUnreadableError(Exception):
            pass
            
        class LowQualityDocumentError(Exception):
            pass
        
        # Test various document processing error scenarios
        processing_errors = [
            # Unreadable document errors
            DocumentUnreadableError("Document is completely unreadable"),
            OCRProcessingError("Failed to extract text from document"),
            LowQualityDocumentError("Document quality too low for accurate OCR"),
            
            # Processing failures
            ValueError("Invalid document format for OCR processing"),
            TypeError("Document type not supported for OCR"),
            RuntimeError("OCR engine failed during text extraction")
        ]
        
        for exception in processing_errors:
            # Create service error with PROCESSING category
            error = create_service_error(
                exception,
                category=ErrorCategory.PROCESSING,
                details={
                    "document_id": "doc-123",
                    "document_type": "application_form",
                    "ocr_engine": "tensorflow-ocr-v2",
                    "processing_stage": "text_extraction"
                }
            )
            
            # Verify error properties
            assert error.category == ErrorCategory.PROCESSING
            
            # Check if severity is appropriate (MEDIUM for most processing errors)
            assert error.severity in [ErrorSeverity.MEDIUM, ErrorSeverity.HIGH]
            
            # Verify document context is included
            assert "document_id" in error.details
            assert "document_type" in error.details
            assert "ocr_engine" in error.details
            assert "processing_stage" in error.details
            
            # Format for logging and verify document context is preserved
            log_format = format_error_for_logging(error)
            assert "error_details" in log_format
            assert log_format["error_details"]["document_id"] == "doc-123"
            assert log_format["error_details"]["document_type"] == "application_form"
            
            # Format for publishing and verify sensitive details are handled appropriately
            publish_format = format_error_for_publishing(error)
            assert "error" in publish_format
            assert "details" in publish_format["error"]
            assert publish_format["error"]["details"]["document_id"] == "doc-123"
            
            # Verify retry eligibility based on error type
            if isinstance(exception, (ValueError, TypeError)):
                # Data validation errors should not be retried
                assert not is_retry_eligible(error)
            elif isinstance(exception, (RuntimeError, OCRProcessingError)):
                # Processing errors might be retried
                if error.retry_strategy != RetryStrategy.NONE:
                    assert is_retry_eligible(error)
                    
            # For low quality documents, we might want to flag for human review
            if isinstance(exception, LowQualityDocumentError):
                # Enrich with flag for human review
                error = enrich_error_context(error, {"requires_human_review": True})
                assert error.details["requires_human_review"] is True


# Test categorize_exception function
class TestCategorizeException:
    """Tests for the categorize_exception function."""

    def test_connection_error(self):
        """Test categorizing connection errors."""
        exceptions = [
            ConnectionError("Connection failed"),
            TimeoutError("Connection timed out"),
            ConnectionRefusedError("Connection refused"),
            ConnectionResetError("Connection reset"),
        ]

        for exception in exceptions:
            assert categorize_exception(exception) == ErrorCategory.CONNECTION

    def test_validation_error(self):
        """Test categorizing validation errors."""
        exceptions = [
            ValueError("Invalid value"),
            TypeError("Invalid type"),
            KeyError("Missing key"),
            AttributeError("Missing attribute"),
        ]

        for exception in exceptions:
            assert categorize_exception(exception) == ErrorCategory.VALIDATION

    def test_system_error(self):
        """Test categorizing system errors."""
        exceptions = [
            MemoryError("Out of memory"),
            OSError("OS error"),
            IOError("IO error"),
            SystemError("System error"),
        ]

        for exception in exceptions:
            assert categorize_exception(exception) == ErrorCategory.SYSTEM

    def test_processing_error(self):
        """Test categorizing processing errors."""
        class OCRError(Exception):
            pass

        class DocumentError(Exception):
            pass

        exceptions = [
            OCRError("OCR failed"),
            DocumentError("Document processing failed"),
        ]

        for exception in exceptions:
            assert categorize_exception(exception) == ErrorCategory.PROCESSING

    def test_unknown_error(self):
        """Test categorizing unknown errors."""
        class CustomError(Exception):
            pass

        exception = CustomError("Custom error")
        assert categorize_exception(exception) == ErrorCategory.UNKNOWN
        
    def test_connection_error_recovery_strategy(self):
        """Test connection error handling and recovery strategy determination.
        
        This test verifies the error handling for connection errors and the
        determination of appropriate recovery strategies as required in
        section 4.1.8 of the technical specification.
        """
        # Test various connection error scenarios
        connection_errors = [
            # RabbitMQ connection errors
            ConnectionRefusedError("Connection refused to RabbitMQ server"),
            ConnectionResetError("Connection reset by RabbitMQ server"),
            TimeoutError("Connection to RabbitMQ timed out"),
            
            # S3 connection errors
            ConnectionError("Failed to connect to S3 storage"),
            TimeoutError("S3 operation timed out"),
            
            # Generic connection errors
            ConnectionError("Network connection interrupted")
        ]
        
        for exception in connection_errors:
            # Create service error from the exception
            error = create_service_error(exception)
            
            # Verify error is categorized correctly
            assert error.category == ErrorCategory.CONNECTION
            
            # Connection errors should have HIGH severity
            assert error.severity == ErrorSeverity.HIGH
            
            # Connection errors should use exponential backoff
            assert error.retry_strategy == RetryStrategy.EXPONENTIAL
            
            # Verify error is eligible for retry
            assert is_retry_eligible(error)
            
            # Verify error context can be enriched with connection-specific details
            connection_context = {
                "host": "test-server",
                "port": 5672,
                "attempt": 1,
                "last_connected": "2023-01-01T00:00:00Z"
            }
            
            enriched_error = enrich_error_context(error, connection_context)
            assert enriched_error.details["host"] == "test-server"
            assert enriched_error.details["port"] == 5672
            
            # Verify error can be formatted for logging with connection details
            log_format = format_error_for_logging(enriched_error)
            assert "error_category" in log_format
            assert log_format["error_category"] == "CONNECTION"
            assert "error_details" in log_format
            assert log_format["error_details"]["host"] == "test-server"


# Test enrich_error_context function
class TestEnrichErrorContext:
    """Tests for the enrich_error_context function."""

    def test_enrich_empty_context(self, service_error):
        """Test enriching with an empty context."""
        original_details = service_error.details.copy()
        enriched_error = enrich_error_context(service_error, {})

        assert enriched_error is service_error  # Should return the same object
        assert enriched_error.details == original_details

    def test_enrich_new_context(self, service_error):
        """Test enriching with new context data."""
        original_details = service_error.details.copy()
        new_context = {"process_id": 12345, "timestamp": "2023-01-01T12:00:00Z"}

        enriched_error = enrich_error_context(service_error, new_context)

        assert enriched_error is service_error  # Should return the same object
        assert enriched_error.details != original_details
        assert enriched_error.details["document_id"] == "doc123"  # Original data preserved
        assert enriched_error.details["retry_count"] == 0  # Original data preserved
        assert enriched_error.details["process_id"] == 12345  # New data added
        assert enriched_error.details["timestamp"] == "2023-01-01T12:00:00Z"  # New data added

    def test_enrich_overwrite_context(self, service_error):
        """Test enriching with context that overwrites existing data."""
        new_context = {"document_id": "new_doc456", "new_field": "value"}

        enriched_error = enrich_error_context(service_error, new_context)

        assert enriched_error.details["document_id"] == "new_doc456"  # Overwritten
        assert enriched_error.details["retry_count"] == 0  # Original data preserved
        assert enriched_error.details["new_field"] == "value"  # New data added


# Test is_retry_eligible function
class TestIsRetryEligible:
    """Tests for the is_retry_eligible function."""

    def test_retry_strategy_none(self):
        """Test retry eligibility with RetryStrategy.NONE."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.NONE,
        )

        assert not is_retry_eligible(error)

    def test_retry_count_exceeded(self):
        """Test retry eligibility with retry count exceeded."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.EXPONENTIAL,
            details={"retry_count": 3},
        )

        assert not is_retry_eligible(error, max_retries=3)
        assert is_retry_eligible(error, max_retries=4)

    def test_fatal_severity(self):
        """Test retry eligibility with fatal severity."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.EXPONENTIAL,
            severity=ErrorSeverity.FATAL,
        )

        assert not is_retry_eligible(error)

    def test_eligible_for_retry(self):
        """Test retry eligibility for a retry-eligible error."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.EXPONENTIAL,
            severity=ErrorSeverity.MEDIUM,
            details={"retry_count": 1},
        )

        assert is_retry_eligible(error, max_retries=3)


# Test increment_retry_count function
class TestIncrementRetryCount:
    """Tests for the increment_retry_count function."""

    def test_increment_existing_count(self):
        """Test incrementing an existing retry count."""
        error = ServiceError(
            message="Test error",
            details={"retry_count": 2},
        )

        updated_error = increment_retry_count(error)

        assert updated_error is error  # Should return the same object
        assert updated_error.details["retry_count"] == 3

    def test_increment_missing_count(self):
        """Test incrementing a missing retry count."""
        error = ServiceError(
            message="Test error",
            details={},
        )

        updated_error = increment_retry_count(error)

        assert updated_error.details["retry_count"] == 1


# Test calculate_retry_delay function
class TestCalculateRetryDelay:
    """Tests for the calculate_retry_delay function."""

    def test_immediate_strategy(self):
        """Test delay calculation with immediate strategy."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.IMMEDIATE,
            details={"retry_count": 2},
        )

        delay = calculate_retry_delay(error)

        assert delay == 0.0

    def test_exponential_strategy(self):
        """Test delay calculation with exponential strategy."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.EXPONENTIAL,
            details={"retry_count": 2},
        )

        delay = calculate_retry_delay(error, base_delay=1.0)

        assert delay == 4.0  # 1.0 * (2^2)

    def test_linear_strategy(self):
        """Test delay calculation with linear strategy."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.LINEAR,
            details={"retry_count": 3},
        )

        delay = calculate_retry_delay(error, base_delay=2.0)

        assert delay == 6.0  # 2.0 * 3

    def test_custom_strategy(self):
        """Test delay calculation with custom strategy."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.CUSTOM,
            details={"retry_count": 2, "custom_delay": 5.5},
        )

        delay = calculate_retry_delay(error)

        assert delay == 5.5

    def test_custom_strategy_missing_delay(self):
        """Test delay calculation with custom strategy but missing custom_delay."""
        error = ServiceError(
            message="Test error",
            retry_strategy=RetryStrategy.CUSTOM,
            details={"retry_count": 2},  # No custom_delay
        )

        delay = calculate_retry_delay(error, base_delay=3.0)

        assert delay == 3.0  # Falls back to base_delay
        
    def test_rabbitmq_publishing_retry_scenario(self):
        """Test a realistic RabbitMQ publishing retry scenario.
        
        This test simulates the retry logic for RabbitMQ message publishing
        as required in section 4.1.8 of the technical specification.
        """
        # Create a connection error that would occur during RabbitMQ publishing
        exception = ConnectionResetError("Connection reset by peer during message publish")
        
        # Create a service error with appropriate category
        error = create_service_error(
            exception,
            category=ErrorCategory.CONNECTION
        )
        
        # Verify the error is classified correctly
        assert error.category == ErrorCategory.CONNECTION
        assert error.severity == ErrorSeverity.HIGH
        assert error.retry_strategy == RetryStrategy.EXPONENTIAL
        
        # Simulate retry logic
        retry_count = 0
        max_retries = 3
        base_delay = 0.5  # 500ms
        
        # Initial check if retry is eligible
        assert is_retry_eligible(error, max_retries=max_retries)
        
        # Simulate retry loop
        while is_retry_eligible(error, max_retries=max_retries) and retry_count < 5:  # 5 is a safety limit
            # Calculate delay for this retry attempt
            delay = calculate_retry_delay(error, base_delay=base_delay)
            
            # For a connection error with exponential backoff, verify delay increases exponentially
            expected_delay = base_delay * (2 ** retry_count)
            assert delay == expected_delay
            
            # Increment retry count
            error = increment_retry_count(error)
            retry_count += 1
        
        # Verify we stopped at the right retry count
        assert retry_count == max_retries
        assert error.details["retry_count"] == max_retries
        assert not is_retry_eligible(error, max_retries=max_retries)


# Test format_error_for_logging function
class TestFormatErrorForLogging:
    """Tests for the format_error_for_logging function."""

    def test_format_complete_error(self, service_error):
        """Test formatting a complete error for logging."""
        formatted = format_error_for_logging(service_error)

        assert formatted["error_message"] == "Test error"
        assert formatted["error_category"] == "PROCESSING"
        assert formatted["error_severity"] == "MEDIUM"
        assert isinstance(formatted["error_timestamp"], str)
        assert formatted["error_details"] == {"document_id": "doc123", "retry_count": 0}
        assert formatted["original_exception"] is None
        assert isinstance(formatted["trace_excerpt"], list)

    def test_format_with_original_exception(self):
        """Test formatting an error with an original exception."""
        original_exception = ValueError("Original error")
        error = ServiceError(
            message="Test error",
            original_exception=original_exception,
        )

        formatted = format_error_for_logging(error)

        assert formatted["original_exception"] == str(original_exception)

    def test_format_with_no_trace(self):
        """Test formatting an error with no trace."""
        error = ServiceError(
            message="Test error",
            trace=None,
        )

        formatted = format_error_for_logging(error)

        assert formatted["trace_excerpt"] is None


# Test format_error_for_publishing function
class TestFormatErrorForPublishing:
    """Tests for the format_error_for_publishing function."""

    def test_format_for_publishing(self, service_error):
        """Test formatting an error for publishing."""
        formatted = format_error_for_publishing(service_error)

        assert "error" in formatted
        assert formatted["error"]["message"] == "Test error"
        assert formatted["error"]["category"] == "PROCESSING"
        assert formatted["error"]["severity"] == "MEDIUM"
        assert isinstance(formatted["error"]["timestamp"], str)
        assert formatted["error"]["details"] == {"document_id": "doc123", "retry_count": 0}
        
        # These should be excluded for security
        assert "trace" not in formatted["error"]
        assert "original_exception" not in formatted["error"]


# Test get_caller_info function
class TestGetCallerInfo:
    """Tests for the get_caller_info function."""

    def test_get_caller_info(self):
        """Test getting caller information."""
        def caller_function():
            return get_caller_info()

        caller_info = caller_function()

        assert "module" in caller_info
        assert "function" in caller_info
        assert "line" in caller_info
        assert caller_info["function"] == "test_get_caller_info"

    @patch("inspect.currentframe", return_value=None)
    def test_get_caller_info_no_frame(self, mock_currentframe):
        """Test getting caller information when no frame is available."""
        caller_info = get_caller_info()

        assert caller_info == {"module": "unknown", "function": "unknown", "line": 0}


# Test safe_execute function
class TestSafeExecute:
    """Tests for the safe_execute function."""

    def test_successful_execution(self):
        """Test safe execution of a successful function."""
        def test_func(a, b):
            return a + b

        result = safe_execute(test_func, 1, 2)

        assert result == 3

    def test_failed_execution(self):
        """Test safe execution of a failing function."""
        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func)

        assert result is None

    def test_failed_execution_with_default(self):
        """Test safe execution of a failing function with a default value."""
        def test_func():
            raise ValueError("Test error")

        result = safe_execute(test_func, default="default_value")

        assert result == "default_value"


# Test handle_boto_error function
class TestHandleBotoError:
    """Tests for the handle_boto_error function."""

    def test_handle_no_such_key(self, boto3_client_error):
        """Test handling a NoSuchKey error."""
        error_code, error_message = handle_boto_error(boto3_client_error)

        assert error_code == StorageErrorCode.OBJECT_NOT_FOUND
        assert error_message == "The specified key does not exist."

    def test_handle_access_denied(self):
        """Test handling an AccessDenied error."""
        error_response = {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}}
        boto_error = MagicMock(
            response=error_response,
            __str__=lambda self: "An error occurred (AccessDenied) when calling the GetObject operation: Access Denied"
        )

        error_code, error_message = handle_boto_error(boto_error)

        assert error_code == StorageErrorCode.PERMISSION_DENIED
        assert error_message == "Access Denied"

    def test_handle_connection_error(self):
        """Test handling a connection error."""
        connection_error = Exception("Connection timed out")

        error_code, error_message = handle_boto_error(connection_error)

        assert error_code == StorageErrorCode.CONNECTION_ERROR
        assert error_message == "Connection timed out"

    def test_handle_unknown_error(self):
        """Test handling an unknown error."""
        unknown_error = Exception("Unknown error")

        error_code, error_message = handle_boto_error(unknown_error)

        assert error_code == StorageErrorCode.UNKNOWN_ERROR
        assert error_message == "Unknown error"


# Test handle_uncaught_exception function
class TestHandleUncaughtException:
    """Tests for the handle_uncaught_exception function."""

    @patch("sys.stderr.write")
    @patch("logging.critical")
    def test_handle_regular_exception(self, mock_log_critical, mock_stderr_write):
        """Test handling a regular exception."""
        exc_type = ValueError
        exc_value = ValueError("Test error")
        exc_traceback = None

        handle_uncaught_exception(exc_type, exc_value, exc_traceback)

        # Check that logging.critical was called
        mock_log_critical.assert_called_once()
        # Check that sys.stderr.write was called
        mock_stderr_write.assert_called_once()

    @patch("sys.__excepthook__")
    def test_handle_keyboard_interrupt(self, mock_sys_excepthook):
        """Test handling a KeyboardInterrupt exception."""
        exc_type = KeyboardInterrupt
        exc_value = KeyboardInterrupt()
        exc_traceback = None

        handle_uncaught_exception(exc_type, exc_value, exc_traceback)

        # Check that sys.__excepthook__ was called for KeyboardInterrupt
        mock_sys_excepthook.assert_called_once_with(exc_type, exc_value, exc_traceback)


# Test set_global_exception_handler function
class TestSetGlobalExceptionHandler:
    """Tests for the set_global_exception_handler function."""

    def test_set_global_exception_handler(self):
        """Test setting the global exception handler."""
        original_excepthook = sys.excepthook

        try:
            set_global_exception_handler()
            assert sys.excepthook == handle_uncaught_exception
        finally:
            # Restore the original excepthook to avoid affecting other tests
            sys.excepthook = original_excepthook