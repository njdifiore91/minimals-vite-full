#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for error handling utilities in the Document Service.

This module contains tests for the error_utils.py module, which provides
standardized error handling utilities for the Document Service, including
error classification, structured error objects, error context enrichment,
retry eligibility determination, and error serialization for logging and
message publishing.
"""

import json
import time
import pytest
from unittest.mock import MagicMock, patch

from document_service.utils.error_utils import (
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


# ===== Test Error Enums =====

def test_error_type_enum():
    """Test that ErrorType enum has all required error types."""
    assert ErrorType.VALIDATION is not None
    assert ErrorType.CONNECTION is not None
    assert ErrorType.PROCESSING is not None
    assert ErrorType.CLASSIFICATION is not None
    assert ErrorType.STORAGE is not None
    assert ErrorType.CONFIGURATION is not None
    assert ErrorType.INTERNAL is not None
    assert ErrorType.UNKNOWN is not None


def test_error_severity_enum():
    """Test that ErrorSeverity enum has all required severity levels."""
    assert ErrorSeverity.INFO is not None
    assert ErrorSeverity.WARNING is not None
    assert ErrorSeverity.ERROR is not None
    assert ErrorSeverity.CRITICAL is not None


def test_retry_strategy_enum():
    """Test that RetryStrategy enum has all required retry strategies."""
    assert RetryStrategy.NO_RETRY is not None
    assert RetryStrategy.IMMEDIATE_RETRY is not None
    assert RetryStrategy.EXPONENTIAL_BACKOFF is not None
    assert RetryStrategy.LINEAR_BACKOFF is not None


# ===== Test Base Error Class =====

def test_document_service_error_init():
    """Test initialization of DocumentServiceError."""
    error = DocumentServiceError(
        message="Test error",
        error_type=ErrorType.VALIDATION,
        severity=ErrorSeverity.WARNING,
        retry_strategy=RetryStrategy.NO_RETRY,
        context={"test": "value"},
        cause=ValueError("Original error"),
        retry_count=1,
        max_retries=3
    )
    
    assert error.message == "Test error"
    assert error.error_type == ErrorType.VALIDATION
    assert error.severity == ErrorSeverity.WARNING
    assert error.retry_strategy == RetryStrategy.NO_RETRY
    assert error.context == {"test": "value"}
    assert isinstance(error.cause, ValueError)
    assert error.retry_count == 1
    assert error.max_retries == 3
    assert error.timestamp is not None
    assert error.traceback is not None


def test_document_service_error_to_dict():
    """Test conversion of DocumentServiceError to dictionary."""
    error = DocumentServiceError(
        message="Test error",
        error_type=ErrorType.VALIDATION,
        severity=ErrorSeverity.WARNING,
        context={"test": "value"},
        cause=ValueError("Original error")
    )
    
    error_dict = error.to_dict()
    
    assert error_dict["message"] == "Test error"
    assert error_dict["error_type"] == "VALIDATION"
    assert error_dict["severity"] == "WARNING"
    assert error_dict["retry_strategy"] == "NO_RETRY"
    assert error_dict["context"] == {"test": "value"}
    assert "cause" in error_dict
    assert "timestamp" in error_dict
    assert "retry_count" in error_dict
    assert "max_retries" in error_dict
    assert "traceback" in error_dict


def test_document_service_error_to_json():
    """Test conversion of DocumentServiceError to JSON string."""
    error = DocumentServiceError(
        message="Test error",
        error_type=ErrorType.VALIDATION,
        severity=ErrorSeverity.WARNING,
        context={"test": "value"}
    )
    
    error_json = error.to_json()
    error_dict = json.loads(error_json)
    
    assert error_dict["message"] == "Test error"
    assert error_dict["error_type"] == "VALIDATION"
    assert error_dict["severity"] == "WARNING"
    assert error_dict["context"] == {"test": "value"}


def test_document_service_error_is_retriable():
    """Test retriable determination of DocumentServiceError."""
    # Non-retriable error
    error1 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.NO_RETRY,
        retry_count=0,
        max_retries=3
    )
    assert not error1.is_retriable()
    
    # Retriable error with retries remaining
    error2 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_count=1,
        max_retries=3
    )
    assert error2.is_retriable()
    
    # Retriable error with no retries remaining
    error3 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_count=3,
        max_retries=3
    )
    assert not error3.is_retriable()


def test_document_service_error_increment_retry():
    """Test retry count increment of DocumentServiceError."""
    error = DocumentServiceError(
        message="Test error",
        retry_count=1,
        max_retries=3
    )
    
    error.increment_retry()
    assert error.retry_count == 2
    
    error.increment_retry()
    assert error.retry_count == 3


def test_document_service_error_with_context():
    """Test context enrichment of DocumentServiceError."""
    error = DocumentServiceError(
        message="Test error",
        context={"initial": "value"}
    )
    
    error.with_context(additional="context", more="info")
    
    assert error.context == {
        "initial": "value",
        "additional": "context",
        "more": "info"
    }


# ===== Test Specific Error Classes =====

def test_validation_error():
    """Test ValidationError initialization and properties."""
    error = ValidationError(
        message="Invalid input",
        field="username",
        value="",
        context={"request_id": "12345"}
    )
    
    assert error.message == "Invalid input"
    assert error.error_type == ErrorType.VALIDATION
    assert error.severity == ErrorSeverity.WARNING
    assert error.retry_strategy == RetryStrategy.NO_RETRY
    assert error.context["field"] == "username"
    assert error.context["value"] == ""
    assert error.context["request_id"] == "12345"


def test_connection_error():
    """Test ConnectionError initialization and properties."""
    error = ConnectionError(
        message="Failed to connect",
        service="RabbitMQ",
        context={"host": "localhost"},
        retry_count=0,
        max_retries=5
    )
    
    assert error.message == "Failed to connect"
    assert error.error_type == ErrorType.CONNECTION
    assert error.severity == ErrorSeverity.ERROR
    assert error.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
    assert error.context["service"] == "RabbitMQ"
    assert error.context["host"] == "localhost"
    assert error.retry_count == 0
    assert error.max_retries == 5


def test_processing_error():
    """Test ProcessingError initialization and properties."""
    error = ProcessingError(
        message="Processing failed",
        document_id="doc-12345",
        processing_stage="classification",
        context={"attempt": 2}
    )
    
    assert error.message == "Processing failed"
    assert error.error_type == ErrorType.PROCESSING
    assert error.severity == ErrorSeverity.ERROR
    assert error.retry_strategy == RetryStrategy.LINEAR_BACKOFF
    assert error.context["document_id"] == "doc-12345"
    assert error.context["processing_stage"] == "classification"
    assert error.context["attempt"] == 2


def test_classification_error():
    """Test ClassificationError initialization and properties."""
    error = ClassificationError(
        message="Classification failed",
        document_id="doc-12345",
        confidence_score=0.3,
        context={"model": "random_forest"}
    )
    
    assert error.message == "Classification failed"
    assert error.error_type == ErrorType.CLASSIFICATION
    assert error.severity == ErrorSeverity.ERROR
    assert error.retry_strategy == RetryStrategy.IMMEDIATE_RETRY
    assert error.context["document_id"] == "doc-12345"
    assert error.context["confidence_score"] == 0.3
    assert error.context["model"] == "random_forest"


def test_storage_error():
    """Test StorageError initialization and properties."""
    error = StorageError(
        message="Storage operation failed",
        storage_type="S3",
        operation="upload",
        context={"bucket": "test-bucket"}
    )
    
    assert error.message == "Storage operation failed"
    assert error.error_type == ErrorType.STORAGE
    assert error.severity == ErrorSeverity.ERROR
    assert error.retry_strategy == RetryStrategy.EXPONENTIAL_BACKOFF
    assert error.context["storage_type"] == "S3"
    assert error.context["operation"] == "upload"
    assert error.context["bucket"] == "test-bucket"


# ===== Test Error Creation Functions =====

def test_create_error():
    """Test create_error function."""
    error = create_error(
        message="Test error",
        error_type=ErrorType.INTERNAL,
        severity=ErrorSeverity.CRITICAL,
        retry_strategy=RetryStrategy.LINEAR_BACKOFF,
        context={"test": "value"},
        cause=ValueError("Original error"),
        retry_count=1,
        max_retries=5
    )
    
    assert isinstance(error, DocumentServiceError)
    assert error.message == "Test error"
    assert error.error_type == ErrorType.INTERNAL
    assert error.severity == ErrorSeverity.CRITICAL
    assert error.retry_strategy == RetryStrategy.LINEAR_BACKOFF
    assert error.context == {"test": "value"}
    assert isinstance(error.cause, ValueError)
    assert error.retry_count == 1
    assert error.max_retries == 5


def test_create_validation_error():
    """Test create_validation_error function."""
    error = create_validation_error(
        message="Invalid input",
        field="username",
        value="",
        context={"request_id": "12345"},
        cause=ValueError("Original error")
    )
    
    assert isinstance(error, ValidationError)
    assert error.message == "Invalid input"
    assert error.context["field"] == "username"
    assert error.context["value"] == ""
    assert error.context["request_id"] == "12345"
    assert isinstance(error.cause, ValueError)


def test_create_connection_error():
    """Test create_connection_error function."""
    error = create_connection_error(
        message="Failed to connect",
        service="RabbitMQ",
        context={"host": "localhost"},
        cause=ConnectionRefusedError(),
        retry_count=1,
        max_retries=5
    )
    
    assert isinstance(error, ConnectionError)
    assert error.message == "Failed to connect"
    assert error.context["service"] == "RabbitMQ"
    assert error.context["host"] == "localhost"
    assert isinstance(error.cause, ConnectionRefusedError)
    assert error.retry_count == 1
    assert error.max_retries == 5


def test_create_processing_error():
    """Test create_processing_error function."""
    error = create_processing_error(
        message="Processing failed",
        document_id="doc-12345",
        processing_stage="classification",
        context={"attempt": 2},
        cause=RuntimeError("Process error"),
        retry_count=1,
        max_retries=2
    )
    
    assert isinstance(error, ProcessingError)
    assert error.message == "Processing failed"
    assert error.context["document_id"] == "doc-12345"
    assert error.context["processing_stage"] == "classification"
    assert error.context["attempt"] == 2
    assert isinstance(error.cause, RuntimeError)
    assert error.retry_count == 1
    assert error.max_retries == 2


def test_create_classification_error():
    """Test create_classification_error function."""
    error = create_classification_error(
        message="Classification failed",
        document_id="doc-12345",
        confidence_score=0.3,
        context={"model": "random_forest"},
        cause=ValueError("Model error"),
        retry_count=0,
        max_retries=1
    )
    
    assert isinstance(error, ClassificationError)
    assert error.message == "Classification failed"
    assert error.context["document_id"] == "doc-12345"
    assert error.context["confidence_score"] == 0.3
    assert error.context["model"] == "random_forest"
    assert isinstance(error.cause, ValueError)
    assert error.retry_count == 0
    assert error.max_retries == 1


def test_create_storage_error():
    """Test create_storage_error function."""
    error = create_storage_error(
        message="Storage operation failed",
        storage_type="S3",
        operation="upload",
        context={"bucket": "test-bucket"},
        cause=IOError("I/O error"),
        retry_count=2,
        max_retries=3
    )
    
    assert isinstance(error, StorageError)
    assert error.message == "Storage operation failed"
    assert error.context["storage_type"] == "S3"
    assert error.context["operation"] == "upload"
    assert error.context["bucket"] == "test-bucket"
    assert isinstance(error.cause, IOError)
    assert error.retry_count == 2
    assert error.max_retries == 3


# ===== Test Error Context Enrichment =====

def test_enrich_error_context():
    """Test enrich_error_context function."""
    error = DocumentServiceError(
        message="Test error",
        context={"initial": "value"}
    )
    
    enriched_error = enrich_error_context(
        error,
        additional="context",
        more="info"
    )
    
    assert enriched_error is error  # Should return the same object
    assert error.context == {
        "initial": "value",
        "additional": "context",
        "more": "info"
    }


# ===== Test Retry Eligibility Determination =====

def test_is_retriable_error_with_document_service_error():
    """Test is_retriable_error function with DocumentServiceError."""
    # Non-retriable error
    error1 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.NO_RETRY
    )
    assert not is_retriable_error(error1)
    
    # Retriable error with retries remaining
    error2 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_count=1,
        max_retries=3
    )
    assert is_retriable_error(error2)
    
    # Retriable error with no retries remaining
    error3 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_count=3,
        max_retries=3
    )
    assert not is_retriable_error(error3)


def test_is_retriable_error_with_standard_exceptions():
    """Test is_retriable_error function with standard exceptions."""
    # Retriable standard exceptions
    assert is_retriable_error(ConnectionResetError())
    assert is_retriable_error(TimeoutError())
    assert is_retriable_error(BrokenPipeError())
    
    # Non-retriable standard exceptions
    assert not is_retriable_error(ValueError())
    assert not is_retriable_error(TypeError())
    assert not is_retriable_error(KeyError())


def test_get_retry_delay():
    """Test get_retry_delay function."""
    # Immediate retry
    error1 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.IMMEDIATE_RETRY,
        retry_count=1
    )
    assert get_retry_delay(error1, base_delay=1.0) == 0.0
    
    # Linear backoff
    error2 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.LINEAR_BACKOFF,
        retry_count=2
    )
    assert get_retry_delay(error2, base_delay=1.0) == 3.0  # 1.0 * (2 + 1)
    
    # Exponential backoff
    error3 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        retry_count=2
    )
    assert get_retry_delay(error3, base_delay=1.0) == 4.0  # 1.0 * (2^2)
    
    # No retry
    error4 = DocumentServiceError(
        message="Test error",
        retry_strategy=RetryStrategy.NO_RETRY
    )
    assert get_retry_delay(error4, base_delay=1.0) == 0.0
    
    # Standard exception (default behavior)
    assert get_retry_delay(ValueError(), base_delay=1.0) == 1.0


# ===== Test Error Logging =====

def test_log_error_with_document_service_error(mock_logger):
    """Test log_error function with DocumentServiceError."""
    # INFO severity
    error1 = DocumentServiceError(
        message="Info message",
        severity=ErrorSeverity.INFO
    )
    log_error(error1, logger=mock_logger)
    mock_logger.info.assert_called_once()
    mock_logger.warning.assert_not_called()
    mock_logger.error.assert_not_called()
    mock_logger.critical.assert_not_called()
    mock_logger.reset_mock()
    
    # WARNING severity
    error2 = DocumentServiceError(
        message="Warning message",
        severity=ErrorSeverity.WARNING
    )
    log_error(error2, logger=mock_logger)
    mock_logger.info.assert_not_called()
    mock_logger.warning.assert_called_once()
    mock_logger.error.assert_not_called()
    mock_logger.critical.assert_not_called()
    mock_logger.reset_mock()
    
    # ERROR severity
    error3 = DocumentServiceError(
        message="Error message",
        severity=ErrorSeverity.ERROR
    )
    log_error(error3, logger=mock_logger)
    mock_logger.info.assert_not_called()
    mock_logger.warning.assert_not_called()
    mock_logger.error.assert_called_once()
    mock_logger.critical.assert_not_called()
    mock_logger.reset_mock()
    
    # CRITICAL severity
    error4 = DocumentServiceError(
        message="Critical message",
        severity=ErrorSeverity.CRITICAL
    )
    log_error(error4, logger=mock_logger)
    mock_logger.info.assert_not_called()
    mock_logger.warning.assert_not_called()
    mock_logger.error.assert_not_called()
    mock_logger.critical.assert_called_once()


def test_log_error_with_standard_exception(mock_logger):
    """Test log_error function with standard exception."""
    error = ValueError("Standard error")
    log_error(error, logger=mock_logger)
    mock_logger.error.assert_called_once()


# ===== Test Error Serialization =====

def test_format_error_for_rabbitmq():
    """Test format_error_for_rabbitmq function."""
    error = DocumentServiceError(
        message="Test error",
        error_type=ErrorType.PROCESSING,
        context={"document_id": "doc-12345"}
    )
    
    formatted_error = format_error_for_rabbitmq(error)
    
    assert formatted_error["message"] == "Test error"
    assert formatted_error["error_type"] == "PROCESSING"
    assert formatted_error["context"]["document_id"] == "doc-12345"
    assert "service" in formatted_error
    assert formatted_error["service"] == "document-service"
    assert "error_id" in formatted_error
    assert formatted_error["error_id"].startswith("doc-svc-err-")


# ===== Test Exception Handling =====

def test_handle_exception_success():
    """Test handle_exception function with successful execution."""
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


def test_handle_exception_document_service_error():
    """Test handle_exception function with DocumentServiceError."""
    def failing_function():
        raise ValidationError("Invalid input", field="test")
    
    success, result, error = handle_exception(
        failing_function,
        error_message="Operation failed",
        error_type=ErrorType.PROCESSING
    )
    
    assert success is False
    assert result is None
    assert isinstance(error, ValidationError)
    assert error.message == "Invalid input"
    assert error.context["field"] == "test"


def test_handle_exception_standard_exception():
    """Test handle_exception function with standard exception."""
    def failing_function():
        raise ValueError("Something went wrong")
    
    success, result, error = handle_exception(
        failing_function,
        error_message="Operation failed",
        error_type=ErrorType.PROCESSING
    )
    
    assert success is False
    assert result is None
    assert isinstance(error, DocumentServiceError)
    assert error.message == "Operation failed"
    assert error.error_type == ErrorType.PROCESSING
    assert isinstance(error.cause, ValueError)


# ===== Test Retry Operations =====

def test_retry_operation_success_first_attempt():
    """Test retry_operation function with success on first attempt."""
    mock_function = MagicMock(return_value="success")
    
    success, result, error = retry_operation(
        mock_function,
        max_retries=3,
        error_message="Operation failed",
        error_type=ErrorType.PROCESSING
    )
    
    assert success is True
    assert result == "success"
    assert error is None
    mock_function.assert_called_once()


def test_retry_operation_success_after_retries():
    """Test retry_operation function with success after retries."""
    # Function that fails twice then succeeds
    side_effects = [ValueError("Fail 1"), ValueError("Fail 2"), "success"]
    mock_function = MagicMock(side_effect=side_effects)
    
    with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
        success, result, error = retry_operation(
            mock_function,
            max_retries=3,
            base_delay=0.1,
            error_message="Operation failed",
            error_type=ErrorType.PROCESSING
        )
    
    assert success is True
    assert result == "success"
    assert error is None
    assert mock_function.call_count == 3
    assert mock_sleep.call_count == 2  # Sleep called twice for retries


def test_retry_operation_document_service_error():
    """Test retry_operation function with DocumentServiceError."""
    # Function that raises a retriable DocumentServiceError
    error = ConnectionError(
        message="Connection failed",
        service="RabbitMQ",
        retry_strategy=RetryStrategy.EXPONENTIAL_BACKOFF
    )
    mock_function = MagicMock(side_effect=[error, error, "success"])
    
    with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
        success, result, error = retry_operation(
            mock_function,
            max_retries=3,
            base_delay=0.1,
            error_message="Operation failed",
            error_type=ErrorType.PROCESSING
        )
    
    assert success is True
    assert result == "success"
    assert error is None
    assert mock_function.call_count == 3
    assert mock_sleep.call_count == 2  # Sleep called twice for retries


def test_retry_operation_max_retries_exceeded():
    """Test retry_operation function with max retries exceeded."""
    # Function that always fails
    mock_function = MagicMock(side_effect=ValueError("Always fails"))
    
    with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
        success, result, error = retry_operation(
            mock_function,
            max_retries=2,
            base_delay=0.1,
            error_message="Operation failed",
            error_type=ErrorType.PROCESSING
        )
    
    assert success is False
    assert result is None
    assert isinstance(error, DocumentServiceError)
    assert error.message == "Operation failed"
    assert error.error_type == ErrorType.PROCESSING
    assert mock_function.call_count == 3  # Initial attempt + 2 retries
    assert mock_sleep.call_count == 2  # Sleep called twice for retries


def test_retry_operation_with_on_retry_callback():
    """Test retry_operation function with on_retry callback."""
    # Function that fails twice then succeeds
    side_effects = [ValueError("Fail 1"), ValueError("Fail 2"), "success"]
    mock_function = MagicMock(side_effect=side_effects)
    
    # Callback function to track retries
    on_retry_mock = MagicMock()
    
    with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
        success, result, error = retry_operation(
            mock_function,
            max_retries=3,
            base_delay=0.1,
            error_message="Operation failed",
            error_type=ErrorType.PROCESSING,
            on_retry=on_retry_mock
        )
    
    assert success is True
    assert result == "success"
    assert error is None
    assert mock_function.call_count == 3
    assert on_retry_mock.call_count == 2  # Callback called twice for retries
    assert mock_sleep.call_count == 2  # Sleep called twice for retries


# ===== Test with S3 Client Errors =====

def test_handle_s3_client_error(s3_client_error_factory):
    """Test handling of S3 client errors."""
    # Create an S3 NoSuchKey error
    s3_error = s3_client_error_factory(error_code="NoSuchKey", operation_name="GetObject")
    
    # Function that raises the S3 error
    def failing_function():
        raise s3_error
    
    success, result, error = handle_exception(
        failing_function,
        error_message="Failed to get object from S3",
        error_type=ErrorType.STORAGE
    )
    
    assert success is False
    assert result is None
    assert isinstance(error, DocumentServiceError)
    assert error.message == "Failed to get object from S3"
    assert error.error_type == ErrorType.STORAGE
    assert error.cause == s3_error


# ===== Test with RabbitMQ Exceptions =====

def test_handle_rabbitmq_exception(rabbitmq_exception_factory):
    """Test handling of RabbitMQ exceptions."""
    # Create a RabbitMQ ConnectionClosed error
    rabbitmq_error = rabbitmq_exception_factory(
        exception_type="ConnectionClosed",
        reply_code=320,
        reply_text="Connection closed by user"
    )
    
    # Function that raises the RabbitMQ error
    def failing_function():
        raise rabbitmq_error
    
    success, result, error = handle_exception(
        failing_function,
        error_message="Failed to publish message to RabbitMQ",
        error_type=ErrorType.CONNECTION
    )
    
    assert success is False
    assert result is None
    assert isinstance(error, DocumentServiceError)
    assert error.message == "Failed to publish message to RabbitMQ"
    assert error.error_type == ErrorType.CONNECTION
    assert error.cause == rabbitmq_error


# ===== Integration Tests =====

def test_error_handling_integration():
    """Test integration of error handling components."""
    # Create a specific error
    error = create_connection_error(
        message="Failed to connect to RabbitMQ",
        service="RabbitMQ",
        context={"host": "localhost", "port": 5672},
        cause=ConnectionRefusedError("Connection refused")
    )
    
    # Enrich error context
    enriched_error = enrich_error_context(
        error,
        attempt=1,
        timestamp=time.time()
    )
    
    # Check if error is retriable
    assert is_retriable_error(enriched_error)
    
    # Get retry delay
    delay = get_retry_delay(enriched_error, base_delay=1.0)
    assert delay > 0
    
    # Format error for RabbitMQ
    formatted_error = format_error_for_rabbitmq(enriched_error)
    assert "service" in formatted_error
    assert "error_id" in formatted_error
    
    # Increment retry count
    enriched_error.increment_retry()
    assert enriched_error.retry_count == 1
    
    # Convert to JSON
    error_json = enriched_error.to_json()
    error_dict = json.loads(error_json)
    assert error_dict["message"] == "Failed to connect to RabbitMQ"
    assert error_dict["error_type"] == "CONNECTION"
    assert error_dict["context"]["service"] == "RabbitMQ"
    assert error_dict["context"]["attempt"] == 1


def test_retry_operation_integration():
    """Test integration of retry operation with error handling."""
    # Create a function that fails with different errors then succeeds
    call_count = [0]
    
    def test_function():
        call_count[0] += 1
        if call_count[0] == 1:
            # First call: ConnectionError (retriable)
            raise ConnectionError(
                message="Failed to connect",
                service="RabbitMQ"
            )
        elif call_count[0] == 2:
            # Second call: Standard exception (retriable)
            raise ConnectionResetError("Connection reset")
        elif call_count[0] == 3:
            # Third call: ValidationError (non-retriable, but we'll succeed)
            return "success"
    
    with patch('time.sleep') as mock_sleep:  # Mock sleep to speed up test
        success, result, error = retry_operation(
            test_function,
            max_retries=3,
            base_delay=0.1,
            error_message="Operation failed",
            error_type=ErrorType.PROCESSING
        )
    
    assert success is True
    assert result == "success"
    assert error is None
    assert call_count[0] == 3
    assert mock_sleep.call_count == 2  # Sleep called twice for retries