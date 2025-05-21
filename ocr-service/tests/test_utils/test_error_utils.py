#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the error_utils module.

This module contains tests for error object creation, error classification,
error context enrichment, retry eligibility determination, and error serialization
to ensure consistent error handling across the OCR service.
"""

import json
import logging
import pytest
from unittest.mock import MagicMock, patch

from src.utils.error_utils import (
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    OCRServiceError,
    classify_exception,
    create_error,
    create_error_from_exception,
    enrich_error_context,
    format_error_for_message,
    format_error_for_response,
    generate_error_code,
    is_retry_eligible,
    setup_global_exception_handler
)


# Fixtures
@pytest.fixture
def sample_error_context():
    """Create a sample error context for testing."""
    return ErrorContext(
        document_id="doc123",
        request_id="req456",
        operation="test_operation",
        component="test_component",
        additional_info={"test_key": "test_value"}
    )


@pytest.fixture
def sample_error(sample_error_context):
    """Create a sample error for testing."""
    return OCRServiceError(
        message="Test error message",
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.ERROR,
        error_code="PROC001",
        context=sample_error_context,
        retry_eligible=True,
        max_retries=3
    )


@pytest.fixture
def mock_logger():
    """Create a mock logger for testing."""
    return MagicMock(spec=logging.Logger)


# Test Error Object Creation
class TestErrorObjectCreation:
    """Tests for error object creation functions."""

    def test_create_error_with_all_parameters(self, sample_error_context):
        """Test creating an error with all parameters specified."""
        error = create_error(
            message="Test error",
            error_code="PROC001",
            category=ErrorCategory.PROCESSING,
            severity=ErrorSeverity.ERROR,
            context=sample_error_context,
            retry_eligible=True,
            max_retries=5
        )

        assert error.message == "Test error"
        assert error.error_code == "PROC001"
        assert error.category == ErrorCategory.PROCESSING
        assert error.severity == ErrorSeverity.ERROR
        assert error.context == sample_error_context
        assert error.retry_eligible is True
        assert error.max_retries == 5
        assert error.retry_count == 0

    def test_create_error_with_minimal_parameters(self):
        """Test creating an error with only required parameters."""
        error = create_error(
            message="Minimal error",
            error_code="VAL001"
        )

        assert error.message == "Minimal error"
        assert error.error_code == "VAL001"
        assert error.category == ErrorCategory.VALIDATION
        assert error.severity == ErrorSeverity.ERROR
        assert isinstance(error.context, ErrorContext)
        assert error.retry_eligible is False  # VAL001 is not retry eligible

    def test_create_error_from_exception(self):
        """Test creating an error from an exception."""
        exception = ValueError("Invalid value")
        error = create_error_from_exception(
            exception=exception,
            operation="test_operation",
            component="test_component",
            document_id="doc123",
            request_id="req456"
        )

        assert error.message == "Invalid value"
        assert error.category == ErrorCategory.VALIDATION
        assert error.exception is exception
        assert error.context.operation == "test_operation"
        assert error.context.component == "test_component"
        assert error.context.document_id == "doc123"
        assert error.context.request_id == "req456"

    def test_post_init_captures_traceback(self):
        """Test that __post_init__ captures traceback from exception."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            error = OCRServiceError(
                message="Error with exception",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                error_code="VAL001",
                exception=e
            )

        assert error.traceback is not None
        assert "ValueError: Test exception" in error.traceback


# Test Error Classification
class TestErrorClassification:
    """Tests for error classification functions."""

    def test_classify_exception(self):
        """Test classifying different exception types."""
        assert classify_exception(ValueError()) == ErrorCategory.VALIDATION
        assert classify_exception(ConnectionError()) == ErrorCategory.CONNECTION
        assert classify_exception(FileNotFoundError()) == ErrorCategory.STORAGE
        assert classify_exception(PermissionError()) == ErrorCategory.SECURITY
        assert classify_exception(MemoryError()) == ErrorCategory.SYSTEM
        assert classify_exception(Exception()) == ErrorCategory.UNKNOWN

    def test_generate_error_code(self):
        """Test generating error codes from categories."""
        assert generate_error_code(ErrorCategory.VALIDATION) == "VAL001"
        assert generate_error_code(ErrorCategory.CONNECTION) == "CONN001"
        assert generate_error_code(ErrorCategory.PROCESSING, 2) == "PROC002"
        assert generate_error_code(ErrorCategory.STORAGE, 3) == "STOR003"
        assert generate_error_code(ErrorCategory.UNKNOWN) == "UNK001"

    def test_is_retry_eligible(self):
        """Test determining retry eligibility based on error code and category."""
        # Non-retryable error codes
        assert is_retry_eligible("VAL001", ErrorCategory.VALIDATION) is False
        assert is_retry_eligible("PROC002", ErrorCategory.PROCESSING) is False
        assert is_retry_eligible("SEC001", ErrorCategory.SECURITY) is False

        # Retryable error codes
        assert is_retry_eligible("CONN003", ErrorCategory.CONNECTION) is True
        assert is_retry_eligible("PROC001", ErrorCategory.PROCESSING) is True
        assert is_retry_eligible("STOR001", ErrorCategory.STORAGE) is True
        assert is_retry_eligible("MSG001", ErrorCategory.MESSAGING) is True


# Test Error Context Enrichment
class TestErrorContextEnrichment:
    """Tests for error context enrichment functions."""

    def test_enrich_error_context(self, sample_error):
        """Test enriching an error with additional context."""
        # Original context
        assert sample_error.context.document_id == "doc123"
        assert sample_error.context.request_id == "req456"
        
        # Enrich with new values
        enriched_error = enrich_error_context(
            error=sample_error,
            document_id="new_doc_id",
            request_id="new_req_id",
            operation="new_operation",
            component="new_component",
            additional_info={"new_key": "new_value"}
        )
        
        # Check that context was updated
        assert enriched_error.context.document_id == "new_doc_id"
        assert enriched_error.context.request_id == "new_req_id"
        assert enriched_error.context.operation == "new_operation"
        assert enriched_error.context.component == "new_component"
        assert enriched_error.context.additional_info["test_key"] == "test_value"  # Original value preserved
        assert enriched_error.context.additional_info["new_key"] == "new_value"  # New value added
        
        # Verify it's the same error object (modified in place)
        assert enriched_error is sample_error

    def test_enrich_error_context_partial_update(self, sample_error):
        """Test enriching an error with partial context update."""
        # Only update some fields
        enriched_error = enrich_error_context(
            error=sample_error,
            operation="partial_update"
        )
        
        # Check that only specified fields were updated
        assert enriched_error.context.document_id == "new_doc_id"  # From previous test
        assert enriched_error.context.request_id == "new_req_id"  # From previous test
        assert enriched_error.context.operation == "partial_update"  # Updated
        assert enriched_error.context.component == "new_component"  # From previous test


# Test Error Serialization
class TestErrorSerialization:
    """Tests for error serialization functions."""

    def test_to_dict(self, sample_error):
        """Test converting an error to a dictionary."""
        error_dict = sample_error.to_dict()
        
        # Check that the dictionary contains expected keys
        assert "message" in error_dict
        assert "category" in error_dict
        assert "severity" in error_dict
        assert "error_code" in error_dict
        assert "context" in error_dict
        assert "traceback" in error_dict
        assert "retry_eligible" in error_dict
        assert "retry_count" in error_dict
        assert "max_retries" in error_dict
        
        # Check that enum values are converted to strings
        assert error_dict["category"] == ErrorCategory.PROCESSING.value
        assert error_dict["severity"] == ErrorSeverity.ERROR.value
        
        # Check that exception is removed
        assert "exception" not in error_dict

    def test_to_json(self, sample_error):
        """Test converting an error to JSON."""
        error_json = sample_error.to_json()
        
        # Check that the result is valid JSON
        error_dict = json.loads(error_json)
        
        # Check that the JSON contains expected keys
        assert "message" in error_dict
        assert "category" in error_dict
        assert "severity" in error_dict
        assert "error_code" in error_dict

    def test_format_error_for_response(self, sample_error):
        """Test formatting an error for API response."""
        response = format_error_for_response(sample_error)
        
        # Check that the response has the expected structure
        assert "error" in response
        assert "code" in response["error"]
        assert "message" in response["error"]
        assert "category" in response["error"]
        assert "timestamp" in response["error"]
        assert "request_id" in response["error"]
        
        # Check specific values
        assert response["error"]["code"] == sample_error.error_code
        assert response["error"]["message"] == sample_error.message
        assert response["error"]["category"] == sample_error.category.value
        assert response["error"]["request_id"] == sample_error.context.request_id

    def test_format_error_for_message(self, sample_error):
        """Test formatting an error for RabbitMQ message."""
        message = format_error_for_message(sample_error)
        
        # Check that the message has the expected structure
        assert "error" in message
        assert "code" in message["error"]
        assert "message" in message["error"]
        assert "category" in message["error"]
        assert "severity" in message["error"]
        assert "document_id" in message["error"]
        assert "request_id" in message["error"]
        assert "operation" in message["error"]
        assert "component" in message["error"]
        assert "timestamp" in message["error"]
        assert "retry_count" in message["error"]
        assert "additional_info" in message["error"]
        
        # Check specific values
        assert message["error"]["code"] == sample_error.error_code
        assert message["error"]["message"] == sample_error.message
        assert message["error"]["category"] == sample_error.category.value
        assert message["error"]["severity"] == sample_error.severity.value
        assert message["error"]["document_id"] == sample_error.context.document_id
        assert message["error"]["request_id"] == sample_error.context.request_id
        assert message["error"]["operation"] == sample_error.context.operation
        assert message["error"]["component"] == sample_error.context.component
        assert message["error"]["retry_count"] == sample_error.retry_count


# Test Logging Functionality
class TestLoggingFunctionality:
    """Tests for error logging functions."""

    def test_log_error_severity(self, sample_error, mock_logger):
        """Test logging errors with different severity levels."""
        # Test ERROR severity
        sample_error.severity = ErrorSeverity.ERROR
        sample_error.log(mock_logger)
        mock_logger.error.assert_called_once()
        mock_logger.reset_mock()
        
        # Test CRITICAL severity
        sample_error.severity = ErrorSeverity.CRITICAL
        sample_error.log(mock_logger)
        mock_logger.critical.assert_called_once()
        mock_logger.reset_mock()
        
        # Test WARNING severity
        sample_error.severity = ErrorSeverity.WARNING
        sample_error.log(mock_logger)
        mock_logger.warning.assert_called_once()
        mock_logger.reset_mock()
        
        # Test INFO severity
        sample_error.severity = ErrorSeverity.INFO
        sample_error.log(mock_logger)
        mock_logger.info.assert_called_once()

    def test_log_with_traceback(self, mock_logger):
        """Test logging errors with traceback."""
        try:
            raise ValueError("Test exception for traceback")
        except ValueError as e:
            error = create_error_from_exception(
                exception=e,
                operation="test_operation"
            )
        
        # Log the error
        error.log(mock_logger)
        
        # For ERROR and CRITICAL severity, traceback should be logged
        mock_logger.debug.assert_called_once()
        call_args = mock_logger.debug.call_args[0][0]
        assert "Traceback for error" in call_args

    @patch('src.utils.error_utils.logger')
    def test_log_with_default_logger(self, default_logger, sample_error):
        """Test logging with the default module logger."""
        sample_error.log()  # No logger provided
        default_logger.error.assert_called_once()


# Test Retry Functionality
class TestRetryFunctionality:
    """Tests for error retry functions."""

    def test_increment_retry(self, sample_error):
        """Test incrementing retry count."""
        # Initial state
        assert sample_error.retry_count == 0
        assert sample_error.retry_eligible is True
        assert sample_error.max_retries == 3
        
        # First retry
        result = sample_error.increment_retry()
        assert result is True  # Still eligible for retry
        assert sample_error.retry_count == 1
        
        # Second retry
        result = sample_error.increment_retry()
        assert result is True  # Still eligible for retry
        assert sample_error.retry_count == 2
        
        # Third retry
        result = sample_error.increment_retry()
        assert result is True  # Still eligible for retry
        assert sample_error.retry_count == 3
        
        # Fourth retry (exceeds max_retries)
        result = sample_error.increment_retry()
        assert result is False  # No longer eligible for retry
        assert sample_error.retry_count == 4

    def test_retry_not_eligible(self):
        """Test retry for non-eligible errors."""
        error = create_error(
            message="Non-retryable error",
            error_code="VAL001",  # Validation errors are not retry-eligible
            retry_eligible=False
        )
        
        # Attempt to retry
        result = error.increment_retry()
        assert result is False  # Not eligible for retry
        assert error.retry_count == 0  # Count not incremented

    def test_custom_max_retries(self):
        """Test custom max_retries setting."""
        error = create_error(
            message="Custom retry error",
            error_code="CONN001",
            retry_eligible=True,
            max_retries=5
        )
        
        # Perform 5 retries (should all be eligible)
        for i in range(5):
            result = error.increment_retry()
            assert result is True
            assert error.retry_count == i + 1
        
        # Sixth retry (exceeds max_retries)
        result = error.increment_retry()
        assert result is False
        assert error.retry_count == 6


# Test Global Exception Handler
class TestGlobalExceptionHandler:
    """Tests for the global exception handler."""

    @patch('src.utils.error_utils.sys.__excepthook__')
    @patch('src.utils.error_utils.create_error_from_exception')
    def test_handle_uncaught_exception(self, mock_create_error, mock_excepthook):
        """Test handling of uncaught exceptions."""
        # Create a mock error
        mock_error = MagicMock(spec=OCRServiceError)
        mock_create_error.return_value = mock_error
        
        # Call the handler with a test exception
        exc_type = ValueError
        exc_value = ValueError("Test uncaught exception")
        exc_traceback = None
        
        from src.utils.error_utils import handle_uncaught_exception
        handle_uncaught_exception(exc_type, exc_value, exc_traceback)
        
        # Verify that error was created and logged
        mock_create_error.assert_called_once_with(
            exception=exc_value,
            operation="uncaught_exception",
            component="global_exception_handler"
        )
        mock_error.log.assert_called_once()
        
        # Verify that original excepthook was called
        mock_excepthook.assert_called_once_with(exc_type, exc_value, exc_traceback)

    @patch('src.utils.error_utils.sys')
    def test_setup_global_exception_handler(self, mock_sys):
        """Test setting up the global exception handler."""
        from src.utils.error_utils import handle_uncaught_exception, setup_global_exception_handler
        
        # Call the setup function
        setup_global_exception_handler()
        
        # Verify that sys.excepthook was set
        mock_sys.excepthook = handle_uncaught_exception