#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for error handling utilities in the Document Service.

This module contains tests for the error_utils.py module, which provides
standardized error handling utilities for the Document Service, including
error classification, structured error objects, error context enrichment,
retry eligibility determination, and error serialization.
"""

import json
import time
import pytest
import logging
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.utils.error_utils import (
    ErrorType,
    ErrorSeverity,
    RetryStrategy,
    DocumentServiceError,
    ValidationError,
    ConnectionError,
    ProcessingError,
    ClassificationError,
    StorageError,
    create_error,
    create_validation_error,
    create_connection_error,
    create_processing_error,
    create_classification_error,
    create_storage_error,
    enrich_error_context,
    is_retriable_error,
    get_retry_delay,
    log_error,
    format_error_for_rabbitmq,
    handle_exception,
    retry_operation
)


# ============================================================================
# Test Error Enums
# ============================================================================

class TestErrorEnums:
    """Tests for error enumeration classes."""

    def test_error_type_enum(self):
        """Test that ErrorType enum has all required error types."""
        # Verify all expected error types are defined
        assert hasattr(ErrorType, 'VALIDATION')
        assert hasattr(ErrorType, 'CONNECTION')
        assert hasattr(ErrorType, 'PROCESSING')
        assert hasattr(ErrorType, 'CLASSIFICATION')
        assert hasattr(ErrorType, 'STORAGE')
        assert hasattr(ErrorType, 'CONFIGURATION')
        assert hasattr(ErrorType, 'INTERNAL')
        assert hasattr(ErrorType, 'UNKNOWN')
        
        # Verify enum values are unique
        error_types = [ErrorType.VALIDATION, ErrorType.CONNECTION, ErrorType.PROCESSING,
                      ErrorType.CLASSIFICATION, ErrorType.STORAGE, ErrorType.CONFIGURATION,
                      ErrorType.INTERNAL, ErrorType.UNKNOWN]
        assert len(set(error_types)) == len(error_types)

    def test_error_severity_enum(self):
        """Test that ErrorSeverity enum has all required severity levels."""
        # Verify all expected severity levels are defined
        assert hasattr(ErrorSeverity, 'INFO')
        assert hasattr(ErrorSeverity, 'WARNING')
        assert hasattr(ErrorSeverity, 'ERROR')
        assert hasattr(ErrorSeverity, 'CRITICAL')
        
        # Verify enum values are unique
        severity_levels = [ErrorSeverity.INFO, ErrorSeverity.WARNING, 
                          ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]
        assert len(set(severity_levels)) == len(severity_levels)

    def test_retry_strategy_enum(self):
        """Test that RetryStrategy enum has all required retry strategies."""
        # Verify all expected retry strategies are defined
        assert hasattr(RetryStrategy, 'NO_RETRY')
        assert hasattr(RetryStrategy, 'IMMEDIATE_RETRY')
        assert hasattr(RetryStrategy, 'EXPONENTIAL_BACKOFF')
        assert hasattr(RetryStrategy, 'LINEAR_BACKOFF')
        
        # Verify enum values are unique
        retry_strategies = [RetryStrategy.NO_RETRY, RetryStrategy.IMMEDIATE_RETRY,
                           RetryStrategy.EXPONENTIAL_BACKOFF, RetryStrategy.LINEAR_BACKOFF]
        assert len(set(retry_strategies)) == len(retry_strategies)


# ============================================================================
# Test Base Error Class
# ============================================================================

class TestDocumentServiceError:
    """Tests for the DocumentServiceError base class."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        error = DocumentServiceError("Test error message")
        
        assert error.message == "Test error message"
        assert error.error_type == ErrorType.UNKNOWN
        assert error.severity == ErrorSeverity.ERROR
        assert error.retry_strategy == RetryStrategy.NO_RETRY
        assert isinstance(error.context, dict)
        assert error.context == {}
        assert error.cause is None
        assert error.retry_count == 0
        assert error.max_retries == 3
        assert error.traceback is None

    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        cause = ValueError("Original error")
        context = {"key": "value"}
        
        error = DocumentServiceError(
            message="Custom error message",
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.WARNING,
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            context=context,
            cause=cause,
            retry_count=1,
            max_retries=5
        )
        
        assert error.message == "Custom error message"
        assert error.error_type == ErrorType.VALIDATION
        assert error.severity == ErrorSeverity.WARNING
        assert error.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert error.context == {"key": "value"}
        assert error.cause == cause
        assert error.retry_count == 1
        assert error.max_retries == 5
        assert error.traceback is not None

    def test_to_dict_basic(self):
        """Test conversion to dictionary with basic error."""
        error = DocumentServiceError("Test error message")
        error_dict = error.to_dict()
        
        assert error_dict["message"] == "Test error message"
        assert error_dict["error_type"] == "UNKNOWN"
        assert error_dict["severity"] == "ERROR"
        assert error_dict["retry_strategy"] == "NO_RETRY"
        assert error_dict["context"] == {}
        assert "timestamp" in error_dict
        assert error_dict["retry_count"] == 0
        assert error_dict["max_retries"] == 3
        assert "cause" not in error_dict
        assert "traceback" not in error_dict

    def test_to_dict_with_cause_and_traceback(self):
        """Test conversion to dictionary with cause and traceback."""
        cause = ValueError("Original error")
        error = DocumentServiceError(
            message="Error with cause",
            cause=cause,
            severity=ErrorSeverity.CRITICAL
        )
        
        error_dict = error.to_dict()
        
        assert error_dict["message"] == "Error with cause"
        assert "cause" in error_dict
        assert error_dict["cause"] == str(cause)
        assert "traceback" in error_dict

    def test_to_json(self):
        """Test conversion to JSON string."""
        error = DocumentServiceError("Test error message")
        json_str = error.to_json()
        
        # Verify it's a valid JSON string
        error_dict = json.loads(json_str)
        
        assert error_dict["message"] == "Test error message"
        assert error_dict["error_type"] == "UNKNOWN"

    def test_is_retriable_no_retry(self):
        """Test is_retriable with NO_RETRY strategy."""
        error = DocumentServiceError(
            message="Non-retriable error",
            retry_strategy=RetryStrategy.NO_RETRY
        )
        
        assert not error.is_retriable()

    def test_is_retriable_with_retry_under_limit(self):
        """Test is_retriable with retry strategy and under max retries."""
        error = DocumentServiceError(
            message="Retriable error",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_count=2,
            max_retries=3
        )
        
        assert error.is_retriable()

    def test_is_retriable_with_retry_at_limit(self):
        """Test is_retriable with retry strategy at max retries."""
        error = DocumentServiceError(
            message="Retriable error at limit",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_count=3,
            max_retries=3
        )
        
        assert not error.is_retriable()

    def test_increment_retry(self):
        """Test incrementing retry count."""
        error = DocumentServiceError(
            message="Retriable error",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_count=1,
            max_retries=3
        )
        
        result = error.increment_retry()
        
        assert error.retry_count == 2
        assert result is error  # Should return self for chaining

    def test_with_context(self):
        """Test adding context to error."""
        error = DocumentServiceError("Test error message")
        
        # Add initial context
        result = error.with_context(key1="value1", key2="value2")
        
        assert error.context == {"key1": "value1", "key2": "value2"}
        assert result is error  # Should return self for chaining
        
        # Add more context, should merge with existing
        error.with_context(key3="value3", key2="updated")
        
        assert error.context == {
            "key1": "value1", 
            "key2": "updated",  # Should update existing key
            "key3": "value3"    # Should add new key
        }


# ============================================================================
# Test Specific Error Classes
# ============================================================================

class TestSpecificErrorClasses:
    """Tests for specific error classes derived from DocumentServiceError."""

    def test_validation_error(self):
        """Test ValidationError initialization and properties."""
        error = ValidationError(
            message="Invalid input",
            field="username",
            value="a",  # Too short
            cause=ValueError("Value too short")
        )
        
        assert error.message == "Invalid input"
        assert error.error_type == ErrorType.VALIDATION
        assert error.severity == ErrorSeverity.WARNING
        assert error.retry_strategy == RetryStrategy.NO_RETRY
        assert error.context["field"] == "username"
        assert error.context["value"] == "a"
        assert isinstance(error.cause, ValueError)

    def test_connection_error(self):
        """Test ConnectionError initialization and properties."""
        error = ConnectionError(
            message="Failed to connect",
            service="RabbitMQ",
            cause=TimeoutError("Connection timed out")
        )
        
        assert error.message == "Failed to connect"
        assert error.error_type == ErrorType.CONNECTION
        assert error.severity == ErrorSeverity.ERROR
        assert error.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert error.context["service"] == "RabbitMQ"
        assert isinstance(error.cause, TimeoutError)
        assert error.max_retries == 3

    def test_processing_error(self):
        """Test ProcessingError initialization and properties."""
        error = ProcessingError(
            message="Failed to process document",
            document_id="doc-123",
            processing_stage="classification"
        )
        
        assert error.message == "Failed to process document"
        assert error.error_type == ErrorType.PROCESSING
        assert error.severity == ErrorSeverity.ERROR
        assert error.retry_strategy == RetryStrategy.LINEAR_BACKOFF
        assert error.context["document_id"] == "doc-123"
        assert error.context["processing_stage"] == "classification"
        assert error.max_retries == 2

    def test_classification_error(self):
        """Test ClassificationError initialization and properties."""
        error = ClassificationError(
            message="Failed to classify document",
            document_id="doc-456",
            confidence_score=0.3
        )
        
        assert error.message == "Failed to classify document"
        assert error.error_type == ErrorType.CLASSIFICATION
        assert error.severity == ErrorSeverity.ERROR
        assert error.retry_strategy == RetryStrategy.IMMEDIATE_RETRY
        assert error.context["document_id"] == "doc-456"
        assert error.context["confidence_score"] == 0.3
        assert error.max_retries == 1

    def test_storage_error(self):
        """Test StorageError initialization and properties."""
        error = StorageError(
            message="Failed to store document",
            storage_type="S3",
            operation="upload"
        )
        
        assert error.message == "Failed to store document"
        assert error.error_type == ErrorType.STORAGE
        assert error.severity == ErrorSeverity.ERROR
        assert error.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
        assert error.context["storage_type"] == "S3"
        assert error.context["operation"] == "upload"
        assert error.max_retries == 3


# ============================================================================
# Test Error Creation Functions
# ============================================================================

class TestErrorCreationFunctions:
    """Tests for error creation utility functions."""

    def test_create_error(self):
        """Test create_error function."""
        error = create_error(
            message="Generic error",
            error_type=ErrorType.INTERNAL,
            severity=ErrorSeverity.CRITICAL,
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            context={"service": "test"},
            cause=RuntimeError("Test error"),
            retry_count=1,
            max_retries=5
        )
        
        assert isinstance(error, DocumentServiceError)
        assert error.message == "Generic error"
        assert error.error_type == ErrorType.INTERNAL
        assert error.severity == ErrorSeverity.CRITICAL
        assert error.retry_strategy == RetryStrategy.LINEAR_BACKOFF
        assert error.context == {"service": "test"}
        assert isinstance(error.cause, RuntimeError)
        assert error.retry_count == 1
        assert error.max_retries == 5

    def test_create_validation_error(self):
        """Test create_validation_error function."""
        error = create_validation_error(
            message="Invalid input",
            field="email",
            value="invalid-email",
            context={"form": "registration"},
            cause=ValueError("Invalid email format")
        )
        
        assert isinstance(error, ValidationError)
        assert error.message == "Invalid input"
        assert error.context["field"] == "email"
        assert error.context["value"] == "invalid-email"
        assert error.context["form"] == "registration"
        assert isinstance(error.cause, ValueError)

    def test_create_connection_error(self):
        """Test create_connection_error function."""
        error = create_connection_error(
            message="Connection failed",
            service="PostgreSQL",
            context={"host": "localhost", "port": 5432},
            retry_count=2
        )
        
        assert isinstance(error, ConnectionError)
        assert error.message == "Connection failed"
        assert error.context["service"] == "PostgreSQL"
        assert error.context["host"] == "localhost"
        assert error.context["port"] == 5432
        assert error.retry_count == 2

    def test_create_processing_error(self):
        """Test create_processing_error function."""
        error = create_processing_error(
            message="Processing failed",
            document_id="doc-789",
            processing_stage="extraction"
        )
        
        assert isinstance(error, ProcessingError)
        assert error.message == "Processing failed"
        assert error.context["document_id"] == "doc-789"
        assert error.context["processing_stage"] == "extraction"

    def test_create_classification_error(self):
        """Test create_classification_error function."""
        error = create_classification_error(
            message="Classification failed",
            document_id="doc-101112",
            confidence_score=0.4
        )
        
        assert isinstance(error, ClassificationError)
        assert error.message == "Classification failed"
        assert error.context["document_id"] == "doc-101112"
        assert error.context["confidence_score"] == 0.4

    def test_create_storage_error(self):
        """Test create_storage_error function."""
        error = create_storage_error(
            message="Storage operation failed",
            storage_type="S3",
            operation="download",
            context={"bucket": "test-bucket", "key": "test-key"}
        )
        
        assert isinstance(error, StorageError)
        assert error.message == "Storage operation failed"
        assert error.context["storage_type"] == "S3"
        assert error.context["operation"] == "download"
        assert error.context["bucket"] == "test-bucket"
        assert error.context["key"] == "test-key"


# ============================================================================
# Test Error Utility Functions
# ============================================================================

class TestErrorUtilityFunctions:
    """Tests for error utility functions."""

    def test_enrich_error_context(self):
        """Test enrich_error_context function."""
        error = DocumentServiceError("Test error")
        
        enriched_error = enrich_error_context(
            error,
            request_id="req-123",
            user_id="user-456"
        )
        
        assert enriched_error is error  # Should return the same error instance
        assert error.context["request_id"] == "req-123"
        assert error.context["user_id"] == "user-456"

    def test_is_retriable_error_with_document_service_error(self):
        """Test is_retriable_error with DocumentServiceError instances."""
        # Retriable error
        error1 = DocumentServiceError(
            message="Retriable error",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_count=0,
            max_retries=3
        )
        
        # Non-retriable error (NO_RETRY strategy)
        error2 = DocumentServiceError(
            message="Non-retriable error",
            retry_strategy=RetryStrategy.NO_RETRY
        )
        
        # Non-retriable error (max retries reached)
        error3 = DocumentServiceError(
            message="Max retries reached",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_count=3,
            max_retries=3
        )
        
        assert is_retriable_error(error1) is True
        assert is_retriable_error(error2) is False
        assert is_retriable_error(error3) is False

    def test_is_retriable_error_with_standard_exceptions(self):
        """Test is_retriable_error with standard Python exceptions."""
        # Retriable standard exceptions
        assert is_retriable_error(ConnectionResetError()) is True
        assert is_retriable_error(TimeoutError()) is True
        assert is_retriable_error(BrokenPipeError()) is True
        
        # Non-retriable standard exceptions
        assert is_retriable_error(ValueError()) is False
        assert is_retriable_error(TypeError()) is False
        assert is_retriable_error(KeyError()) is False

    def test_get_retry_delay(self):
        """Test get_retry_delay function."""
        base_delay = 1.0
        
        # IMMEDIATE_RETRY strategy
        error1 = DocumentServiceError(
            message="Immediate retry",
            retry_strategy=RetryStrategy.IMMEDIATE_RETRY,
            retry_count=1
        )
        
        # LINEAR_BACKOFF strategy
        error2 = DocumentServiceError(
            message="Linear backoff",
            retry_strategy=RetryStrategy.LINEAR_BACKOFF,
            retry_count=2
        )
        
        # EXPONENTIAL_BACKOFF strategy
        error3 = DocumentServiceError(
            message="Exponential backoff",
            retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
            retry_count=3
        )
        
        # NO_RETRY strategy
        error4 = DocumentServiceError(
            message="No retry",
            retry_strategy=RetryStrategy.NO_RETRY
        )
        
        # Standard exception (not DocumentServiceError)
        error5 = ValueError("Standard exception")
        
        assert get_retry_delay(error1, base_delay) == 0.0
        assert get_retry_delay(error2, base_delay) == 3.0  # base_delay * (retry_count + 1)
        assert get_retry_delay(error3, base_delay) == 8.0  # base_delay * (2 ** retry_count)
        assert get_retry_delay(error4, base_delay) == 0.0
        assert get_retry_delay(error5, base_delay) == 1.0  # base_delay for non-DocumentServiceError

    def test_log_error(self, caplog):
        """Test log_error function with different severity levels."""
        caplog.set_level(logging.DEBUG)
        
        # INFO severity
        error_info = DocumentServiceError(
            message="Info message",
            severity=ErrorSeverity.INFO
        )
        
        # WARNING severity
        error_warning = DocumentServiceError(
            message="Warning message",
            severity=ErrorSeverity.WARNING
        )
        
        # ERROR severity
        error_error = DocumentServiceError(
            message="Error message",
            severity=ErrorSeverity.ERROR
        )
        
        # CRITICAL severity
        error_critical = DocumentServiceError(
            message="Critical message",
            severity=ErrorSeverity.CRITICAL
        )
        
        # Standard exception
        std_error = ValueError("Standard error")
        
        # Create a mock logger
        mock_logger = MagicMock()
        
        # Log errors with mock logger
        log_error(error_info, mock_logger)
        log_error(error_warning, mock_logger)
        log_error(error_error, mock_logger)
        log_error(error_critical, mock_logger)
        log_error(std_error, mock_logger)
        
        # Verify correct logging methods were called with appropriate messages
        assert mock_logger.info.call_count == 1
        assert "Info message" in mock_logger.info.call_args[0][0]
        
        assert mock_logger.warning.call_count == 1
        assert "Warning message" in mock_logger.warning.call_args[0][0]
        
        assert mock_logger.error.call_count == 2  # One for error_error, one for std_error
        assert "Error message" in mock_logger.error.call_args_list[0][0][0]
        assert "Standard error" in mock_logger.error.call_args_list[1][0][0]
        
        assert mock_logger.critical.call_count == 1
        assert "Critical message" in mock_logger.critical.call_args[0][0]

    def test_format_error_for_rabbitmq(self):
        """Test format_error_for_rabbitmq function."""
        error = DocumentServiceError(
            message="Test error for RabbitMQ",
            error_type=ErrorType.PROCESSING,
            context={"document_id": "doc-123"}
        )
        
        formatted_error = format_error_for_rabbitmq(error)
        
        assert formatted_error["message"] == "Test error for RabbitMQ"
        assert formatted_error["error_type"] == "PROCESSING"
        assert formatted_error["context"]["document_id"] == "doc-123"
        assert formatted_error["service"] == "document-service"  # Added by format_error_for_rabbitmq
        assert "error_id" in formatted_error  # Should have generated an error ID
        assert formatted_error["error_id"].startswith("doc-svc-err-")


# ============================================================================
# Test Exception Handling Functions
# ============================================================================

class TestExceptionHandlingFunctions:
    """Tests for exception handling functions."""

    def test_handle_exception_success(self):
        """Test handle_exception with successful function execution."""
        def successful_function(a, b):
            return a + b
        
        success, result, error = handle_exception(
            successful_function,
            1, 2,
            error_message="Failed to add numbers",
            error_type=ErrorType.PROCESSING
        )
        
        assert success is True
        assert result == 3
        assert error is None

    def test_handle_exception_with_document_service_error(self):
        """Test handle_exception with function that raises DocumentServiceError."""
        def failing_function():
            raise ValidationError("Invalid input")
        
        success, result, error = handle_exception(
            failing_function,
            error_message="Function failed",
            error_type=ErrorType.PROCESSING
        )
        
        assert success is False
        assert result is None
        assert isinstance(error, ValidationError)
        assert error.message == "Invalid input"  # Original error message preserved

    def test_handle_exception_with_standard_exception(self):
        """Test handle_exception with function that raises standard exception."""
        def failing_function():
            raise ValueError("Something went wrong")
        
        success, result, error = handle_exception(
            failing_function,
            error_message="Custom error message",
            error_type=ErrorType.INTERNAL
        )
        
        assert success is False
        assert result is None
        assert isinstance(error, DocumentServiceError)
        assert error.message == "Custom error message"  # Uses provided message
        assert error.error_type == ErrorType.INTERNAL
        assert isinstance(error.cause, ValueError)

    def test_retry_operation_success_first_try(self):
        """Test retry_operation with function that succeeds on first try."""
        mock_function = MagicMock(return_value="success")
        mock_on_retry = MagicMock()
        
        success, result, error = retry_operation(
            mock_function,
            "arg1", "arg2",
            kwarg1="value1",
            max_retries=3,
            on_retry=mock_on_retry
        )
        
        assert success is True
        assert result == "success"
        assert error is None
        assert mock_function.call_count == 1
        mock_function.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        assert mock_on_retry.call_count == 0  # Should not be called for successful operation

    def test_retry_operation_success_after_retries(self):
        """Test retry_operation with function that succeeds after retries."""
        # Function that fails twice then succeeds
        side_effects = [ConnectionError("Failed", "RabbitMQ"), 
                        ConnectionError("Failed again", "RabbitMQ"), 
                        "success"]
        mock_function = MagicMock(side_effect=side_effects)
        mock_on_retry = MagicMock()
        
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            success, result, error = retry_operation(
                mock_function,
                max_retries=3,
                base_delay=0.1,
                on_retry=mock_on_retry
            )
        
        assert success is True
        assert result == "success"
        assert error is None
        assert mock_function.call_count == 3
        assert mock_on_retry.call_count == 2  # Called for each retry
        assert mock_sleep.call_count == 2  # Sleep called for each retry

    def test_retry_operation_failure_after_max_retries(self):
        """Test retry_operation with function that always fails."""
        # Function that always raises ConnectionError
        mock_function = MagicMock(side_effect=ConnectionError("Always fails", "RabbitMQ"))
        mock_on_retry = MagicMock()
        
        with patch('time.sleep') as mock_sleep:  # Patch sleep to avoid waiting
            success, result, error = retry_operation(
                mock_function,
                max_retries=2,
                base_delay=0.1,
                error_message="Operation failed after retries",
                error_type=ErrorType.CONNECTION,
                on_retry=mock_on_retry
            )
        
        assert success is False
        assert result is None
        assert isinstance(error, ConnectionError)
        assert mock_function.call_count == 3  # Initial try + 2 retries
        assert mock_on_retry.call_count == 2  # Called for each retry
        assert mock_sleep.call_count == 2  # Sleep called for each retry

    def test_retry_operation_non_retriable_error(self):
        """Test retry_operation with function that raises non-retriable error."""
        # Function that raises ValidationError (non-retriable)
        mock_function = MagicMock(side_effect=ValidationError("Invalid input"))
        mock_on_retry = MagicMock()
        
        success, result, error = retry_operation(
            mock_function,
            max_retries=3,
            on_retry=mock_on_retry
        )
        
        assert success is False
        assert result is None
        assert isinstance(error, ValidationError)
        assert mock_function.call_count == 1  # Should only try once for non-retriable error
        assert mock_on_retry.call_count == 0  # Should not be called for non-retriable error


# ============================================================================
# Integration Tests
# ============================================================================

class TestErrorUtilsIntegration:
    """Integration tests for error_utils module."""

    def test_error_creation_and_handling_flow(self):
        """Test complete flow of error creation, enrichment, and handling."""
        # Create an error
        error = create_connection_error(
            message="Failed to connect to RabbitMQ",
            service="RabbitMQ",
            context={"host": "localhost", "port": 5672}
        )
        
        # Enrich with additional context
        enriched_error = enrich_error_context(
            error,
            request_id="req-abc123",
            correlation_id="corr-xyz789"
        )
        
        # Check if retriable and get delay
        is_retriable = is_retriable_error(enriched_error)
        retry_delay = get_retry_delay(enriched_error, base_delay=0.5)
        
        # Format for RabbitMQ
        rabbitmq_payload = format_error_for_rabbitmq(enriched_error)
        
        # Verify the flow
        assert enriched_error is error  # Same object reference
        assert error.context["request_id"] == "req-abc123"
        assert error.context["correlation_id"] == "corr-xyz789"
        assert is_retriable is True
        assert retry_delay > 0  # Should have a positive delay for exponential backoff
        assert rabbitmq_payload["service"] == "document-service"
        assert rabbitmq_payload["context"]["request_id"] == "req-abc123"

    def test_retry_operation_with_exponential_backoff(self):
        """Test retry_operation with exponential backoff."""
        # Create a function that fails with retriable error a few times then succeeds
        call_count = 0
        retry_times = []
        
        def test_function():
            nonlocal call_count
            call_count += 1
            
            if call_count <= 3:  # Fail first 3 times
                retry_times.append(time.time())
                raise ConnectionError(
                    message=f"Failure {call_count}",
                    service="Test",
                    retry_count=call_count - 1
                )
            
            # Succeed on 4th attempt
            retry_times.append(time.time())
            return "success"
        
        # Mock time.sleep to avoid actual waiting but still record timestamps
        original_sleep = time.sleep
        
        def mock_sleep(seconds):
            # Just record the time without sleeping
            pass
        
        # Patch time.sleep for the test
        with patch('time.sleep', side_effect=mock_sleep):
            start_time = time.time()
            success, result, error = retry_operation(
                test_function,
                max_retries=5,
                base_delay=0.1,
                error_message="Test function failed"
            )
            end_time = time.time()
        
        assert success is True
        assert result == "success"
        assert error is None
        assert call_count == 4  # Initial attempt + 3 retries before success
        
        # Test completed quickly since we mocked sleep
        assert end_time - start_time < 1.0