#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for error handling type definitions in the Document Service.

This module contains tests for ServiceError, ErrorDetails, LogEntry, ErrorCategory,
MonitoringAlert, and Result types to ensure they correctly validate inputs,
handle edge cases, and provide appropriate error context.
"""

import unittest
import pytest
import datetime
import json
from typing import Dict, Any, Optional, List
from unittest.mock import patch, MagicMock

# Import the types module from the document service
try:
    from document_service.types.errors import (
        ErrorCategory,
        ErrorDetails,
        LogEntry,
        MonitoringAlert,
        ServiceError,
        ValidationError,
        ClassificationError,
        ExtractionError,
        IntegrationError,
        SecurityError,
        MessagingError,
        Result
    )
except ImportError:
    # Alternative import path if the module structure is different
    from document_service.src.types.errors import (
        ErrorCategory,
        ErrorDetails,
        LogEntry,
        MonitoringAlert,
        ServiceError,
        ValidationError,
        ClassificationError,
        ExtractionError,
        IntegrationError,
        SecurityError,
        MessagingError,
        Result
    )


# ===== ErrorCategory Tests =====

class TestErrorCategory(unittest.TestCase):
    """Tests for the ErrorCategory enum."""

    def test_error_category_values(self):
        """Test that ErrorCategory enum has the expected values."""
        # Verify all expected categories exist
        self.assertTrue(hasattr(ErrorCategory, "CRITICAL"))
        self.assertTrue(hasattr(ErrorCategory, "ERROR"))
        self.assertTrue(hasattr(ErrorCategory, "WARNING"))
        self.assertTrue(hasattr(ErrorCategory, "VALIDATION"))
        self.assertTrue(hasattr(ErrorCategory, "SECURITY"))
        self.assertTrue(hasattr(ErrorCategory, "INTEGRATION"))
        self.assertTrue(hasattr(ErrorCategory, "CLASSIFICATION"))
        self.assertTrue(hasattr(ErrorCategory, "EXTRACTION"))
        self.assertTrue(hasattr(ErrorCategory, "MESSAGING"))

    def test_error_category_comparison(self):
        """Test that ErrorCategory enum values can be compared."""
        self.assertNotEqual(ErrorCategory.CRITICAL, ErrorCategory.ERROR)
        self.assertNotEqual(ErrorCategory.ERROR, ErrorCategory.WARNING)
        self.assertNotEqual(ErrorCategory.VALIDATION, ErrorCategory.SECURITY)

    def test_error_category_in_error_details(self):
        """Test that ErrorCategory can be used in ErrorDetails."""
        details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            capture_stack_trace=False
        )
        self.assertEqual(details.category, ErrorCategory.VALIDATION)
        self.assertEqual(details.to_dict()["category"], "VALIDATION")


# ===== ErrorDetails Tests =====

class TestErrorDetails(unittest.TestCase):
    """Tests for the ErrorDetails class."""

    def test_error_details_initialization(self):
        """Test that ErrorDetails can be initialized with minimal arguments."""
        details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.ERROR,
            capture_stack_trace=False
        )
        self.assertEqual(details.message, "Test error")
        self.assertEqual(details.category, ErrorCategory.ERROR)
        self.assertIsNone(details.exception)
        self.assertIsInstance(details.context, dict)
        self.assertIsInstance(details.timestamp, datetime.datetime)
        self.assertEqual(details.service_name, "document-service")
        self.assertIsNone(details.stack_trace)

    def test_error_details_with_exception(self):
        """Test that ErrorDetails captures exception information."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            details = ErrorDetails(
                message="Error occurred",
                category=ErrorCategory.ERROR,
                exception=e
            )
            self.assertEqual(details.message, "Error occurred")
            self.assertEqual(details.exception, e)
            self.assertIsNotNone(details.stack_trace)
            self.assertIn("ValueError: Test exception", details.stack_trace)

    def test_error_details_with_context(self):
        """Test that ErrorDetails captures context information."""
        context = {"document_id": "123", "operation": "classification"}
        details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.CLASSIFICATION,
            context=context,
            capture_stack_trace=False
        )
        self.assertEqual(details.context, context)
        self.assertEqual(details.to_dict()["context"], context)

    def test_error_details_to_dict(self):
        """Test that ErrorDetails can be converted to a dictionary."""
        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.ERROR,
            timestamp=timestamp,
            capture_stack_trace=False
        )
        result = details.to_dict()
        self.assertEqual(result["message"], "Test error")
        self.assertEqual(result["category"], "ERROR")
        self.assertIsNone(result["exception_type"])
        self.assertIsNone(result["exception_message"])
        self.assertEqual(result["timestamp"], timestamp.isoformat())
        self.assertEqual(result["service_name"], "document-service")

    def test_error_details_with_custom_service_name(self):
        """Test that ErrorDetails accepts a custom service name."""
        details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.ERROR,
            service_name="custom-service",
            capture_stack_trace=False
        )
        self.assertEqual(details.service_name, "custom-service")
        self.assertEqual(details.to_dict()["service_name"], "custom-service")

    def test_error_details_without_stack_trace(self):
        """Test that ErrorDetails can be created without a stack trace."""
        details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.ERROR,
            capture_stack_trace=False
        )
        self.assertIsNone(details.stack_trace)


# ===== LogEntry Tests =====

class TestLogEntry(unittest.TestCase):
    """Tests for the LogEntry class."""

    def test_log_entry_initialization(self):
        """Test that LogEntry can be initialized with minimal arguments."""
        entry = LogEntry(message="Test log message")
        self.assertEqual(entry.message, "Test log message")
        self.assertEqual(entry.level, "INFO")  # Default level
        self.assertIsInstance(entry.context, dict)
        self.assertIsInstance(entry.timestamp, datetime.datetime)
        self.assertEqual(entry.service_name, "document-service")
        self.assertIsNone(entry.correlation_id)
        self.assertIsNone(entry.document_id)
        self.assertIsNone(entry.operation)

    def test_log_entry_with_all_fields(self):
        """Test that LogEntry accepts all fields."""
        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        context = {"user_id": "123", "request_path": "/api/documents"}
        entry = LogEntry(
            message="Test log message",
            level="ERROR",
            context=context,
            timestamp=timestamp,
            service_name="custom-service",
            correlation_id="corr-123",
            document_id="doc-456",
            operation="classification"
        )
        self.assertEqual(entry.message, "Test log message")
        self.assertEqual(entry.level, "ERROR")
        self.assertEqual(entry.context, context)
        self.assertEqual(entry.timestamp, timestamp)
        self.assertEqual(entry.service_name, "custom-service")
        self.assertEqual(entry.correlation_id, "corr-123")
        self.assertEqual(entry.document_id, "doc-456")
        self.assertEqual(entry.operation, "classification")

    def test_log_entry_to_dict(self):
        """Test that LogEntry can be converted to a dictionary."""
        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        context = {"user_id": "123"}
        entry = LogEntry(
            message="Test log message",
            level="WARN",
            context=context,
            timestamp=timestamp,
            correlation_id="corr-123",
            document_id="doc-456",
            operation="classification"
        )
        result = entry.to_dict()
        self.assertEqual(result["message"], "Test log message")
        self.assertEqual(result["level"], "WARN")
        self.assertEqual(result["context"], context)
        self.assertEqual(result["timestamp"], timestamp.isoformat())
        self.assertEqual(result["service_name"], "document-service")
        self.assertEqual(result["correlation_id"], "corr-123")
        self.assertEqual(result["document_id"], "doc-456")
        self.assertEqual(result["operation"], "classification")

    def test_log_entry_json_serialization(self):
        """Test that LogEntry can be serialized to JSON."""
        entry = LogEntry(
            message="Test log message",
            level="INFO",
            correlation_id="corr-123",
            document_id="doc-456",
            operation="classification"
        )
        json_str = json.dumps(entry.to_dict())
        # Verify it's valid JSON
        parsed = json.loads(json_str)
        self.assertEqual(parsed["message"], "Test log message")
        self.assertEqual(parsed["level"], "INFO")

    def test_log_entry_with_different_log_levels(self):
        """Test that LogEntry accepts different log levels."""
        levels = ["ERROR", "WARN", "INFO", "DEBUG"]
        for level in levels:
            entry = LogEntry(message=f"Test {level} message", level=level)
            self.assertEqual(entry.level, level)
            self.assertEqual(entry.to_dict()["level"], level)


# ===== MonitoringAlert Tests =====

class TestMonitoringAlert(unittest.TestCase):
    """Tests for the MonitoringAlert class."""

    def test_monitoring_alert_initialization(self):
        """Test that MonitoringAlert can be initialized with minimal arguments."""
        alert = MonitoringAlert(
            title="Test Alert",
            message="This is a test alert"
        )
        self.assertEqual(alert.title, "Test Alert")
        self.assertEqual(alert.message, "This is a test alert")
        self.assertEqual(alert.severity, "critical")  # Default severity
        self.assertIsNone(alert.error_details)
        self.assertIsInstance(alert.timestamp, datetime.datetime)
        self.assertEqual(alert.service_name, "document-service")
        self.assertEqual(alert.alert_tags, [])
        self.assertEqual(alert.notification_channels, ["default"])

    def test_monitoring_alert_with_all_fields(self):
        """Test that MonitoringAlert accepts all fields."""
        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        error_details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.CRITICAL,
            capture_stack_trace=False
        )
        alert_tags = ["production", "document-service", "critical"]
        notification_channels = ["email", "slack"]

        alert = MonitoringAlert(
            title="Critical Error",
            message="A critical error occurred",
            severity="critical",
            error_details=error_details,
            timestamp=timestamp,
            service_name="custom-service",
            alert_tags=alert_tags,
            notification_channels=notification_channels
        )

        self.assertEqual(alert.title, "Critical Error")
        self.assertEqual(alert.message, "A critical error occurred")
        self.assertEqual(alert.severity, "critical")
        self.assertEqual(alert.error_details, error_details)
        self.assertEqual(alert.timestamp, timestamp)
        self.assertEqual(alert.service_name, "custom-service")
        self.assertEqual(alert.alert_tags, alert_tags)
        self.assertEqual(alert.notification_channels, notification_channels)

    def test_monitoring_alert_to_dict(self):
        """Test that MonitoringAlert can be converted to a dictionary."""
        timestamp = datetime.datetime(2023, 1, 1, 12, 0, 0)
        error_details = ErrorDetails(
            message="Test error",
            category=ErrorCategory.CRITICAL,
            capture_stack_trace=False
        )
        alert = MonitoringAlert(
            title="Test Alert",
            message="This is a test alert",
            severity="warning",
            error_details=error_details,
            timestamp=timestamp
        )

        result = alert.to_dict()
        self.assertEqual(result["title"], "Test Alert")
        self.assertEqual(result["message"], "This is a test alert")
        self.assertEqual(result["severity"], "warning")
        self.assertEqual(result["timestamp"], timestamp.isoformat())
        self.assertEqual(result["service_name"], "document-service")
        self.assertIn("error_details", result)
        self.assertEqual(result["error_details"]["message"], "Test error")

    def test_monitoring_alert_without_error_details(self):
        """Test that MonitoringAlert can be created without error details."""
        alert = MonitoringAlert(
            title="Test Alert",
            message="This is a test alert"
        )
        result = alert.to_dict()
        self.assertNotIn("error_details", result)

    def test_monitoring_alert_with_different_severities(self):
        """Test that MonitoringAlert accepts different severity levels."""
        severities = ["critical", "error", "warning", "info"]
        for severity in severities:
            alert = MonitoringAlert(
                title=f"Test {severity.capitalize()} Alert",
                message=f"This is a test {severity} alert",
                severity=severity
            )
            self.assertEqual(alert.severity, severity)
            self.assertEqual(alert.to_dict()["severity"], severity)


# ===== ServiceError Tests =====

class TestServiceError(unittest.TestCase):
    """Tests for the ServiceError class."""

    def test_service_error_initialization(self):
        """Test that ServiceError can be initialized with minimal arguments."""
        error = ServiceError(message="Test error")
        self.assertEqual(str(error), "Test error")
        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.category, ErrorCategory.ERROR)  # Default category
        self.assertIsNone(error.original_exception)
        self.assertIsInstance(error.context, dict)
        self.assertIsNone(error.http_status_code)
        self.assertIsInstance(error.error_details, ErrorDetails)

    def test_service_error_with_all_fields(self):
        """Test that ServiceError accepts all fields."""
        original_exception = ValueError("Original error")
        context = {"document_id": "123", "operation": "classification"}

        error = ServiceError(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            original_exception=original_exception,
            context=context,
            http_status_code=400
        )

        self.assertEqual(error.message, "Test error")
        self.assertEqual(error.category, ErrorCategory.VALIDATION)
        self.assertEqual(error.original_exception, original_exception)
        self.assertEqual(error.context, context)
        self.assertEqual(error.http_status_code, 400)
        self.assertEqual(error.error_details.message, "Test error")
        self.assertEqual(error.error_details.category, ErrorCategory.VALIDATION)
        self.assertEqual(error.error_details.exception, original_exception)
        self.assertEqual(error.error_details.context, context)

    def test_service_error_to_dict(self):
        """Test that ServiceError can be converted to a dictionary."""
        error = ServiceError(
            message="Test error",
            category=ErrorCategory.ERROR,
            http_status_code=500
        )

        result = error.to_dict()
        self.assertIn("error", result)
        self.assertEqual(result["error"]["message"], "Test error")
        self.assertEqual(result["error"]["category"], "ERROR")
        self.assertEqual(result["error"]["http_status_code"], 500)
        self.assertIn("details", result["error"])

    def test_service_error_to_api_response(self):
        """Test that ServiceError can be converted to an API response."""
        context = {"document_id": "123", "operation": "classification"}
        error = ServiceError(
            message="Test error",
            category=ErrorCategory.VALIDATION,
            context=context,
            http_status_code=400
        )

        result = error.to_api_response()
        self.assertFalse(result["success"])
        self.assertIn("error", result)
        self.assertEqual(result["error"]["message"], "Test error")
        self.assertEqual(result["error"]["code"], "validation.400")
        self.assertEqual(result["error"]["details"], context)

    def test_service_error_inheritance(self):
        """Test that ServiceError inherits from Exception."""
        error = ServiceError(message="Test error")
        self.assertIsInstance(error, Exception)

        # Test that it can be raised and caught
        try:
            raise error
            self.fail("Exception was not raised")
        except ServiceError as e:
            self.assertEqual(e, error)
        except Exception:
            self.fail("Wrong exception type caught")


# ===== Specific Error Types Tests =====

class TestSpecificErrorTypes(unittest.TestCase):
    """Tests for specific error types that extend ServiceError."""

    def test_validation_error(self):
        """Test ValidationError initialization and properties."""
        error = ValidationError(message="Invalid document format")
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.message, "Invalid document format")
        self.assertEqual(error.category, ErrorCategory.VALIDATION)
        self.assertEqual(error.http_status_code, 400)

    def test_classification_error(self):
        """Test ClassificationError initialization and properties."""
        error = ClassificationError(message="Failed to classify document")
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.message, "Failed to classify document")
        self.assertEqual(error.category, ErrorCategory.CLASSIFICATION)
        self.assertEqual(error.http_status_code, 422)

    def test_extraction_error(self):
        """Test ExtractionError initialization and properties."""
        error = ExtractionError(message="Failed to extract data")
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.message, "Failed to extract data")
        self.assertEqual(error.category, ErrorCategory.EXTRACTION)
        self.assertEqual(error.http_status_code, 422)

    def test_integration_error(self):
        """Test IntegrationError initialization and properties."""
        error = IntegrationError(message="Failed to connect to external service")
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.message, "Failed to connect to external service")
        self.assertEqual(error.category, ErrorCategory.INTEGRATION)
        self.assertEqual(error.http_status_code, 502)

    def test_security_error(self):
        """Test SecurityError initialization and properties."""
        error = SecurityError(message="Unauthorized access")
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.message, "Unauthorized access")
        self.assertEqual(error.category, ErrorCategory.SECURITY)
        self.assertEqual(error.http_status_code, 403)

    def test_messaging_error(self):
        """Test MessagingError initialization and properties."""
        error = MessagingError(message="Failed to publish message")
        self.assertIsInstance(error, ServiceError)
        self.assertEqual(error.message, "Failed to publish message")
        self.assertEqual(error.category, ErrorCategory.MESSAGING)
        self.assertEqual(error.http_status_code, 500)

    def test_error_with_context_and_original_exception(self):
        """Test specific errors with context and original exception."""
        original_exception = ConnectionError("Connection refused")
        context = {"service": "external-api", "endpoint": "/data"}

        error = IntegrationError(
            message="Failed to connect to external service",
            context=context,
            original_exception=original_exception
        )

        self.assertEqual(error.message, "Failed to connect to external service")
        self.assertEqual(error.original_exception, original_exception)
        self.assertEqual(error.context, context)
        self.assertEqual(error.error_details.exception, original_exception)
        self.assertEqual(error.error_details.context, context)


# ===== Result Tests =====

class TestResult(unittest.TestCase):
    """Tests for the Result generic type."""

    def test_result_success(self):
        """Test creating a successful Result."""
        result = Result.success("test value")
        self.assertTrue(result.is_success)
        self.assertFalse(result.is_failure)
        self.assertEqual(result.value, "test value")

        # Accessing error on a success result should raise ValueError
        with self.assertRaises(ValueError):
            _ = result.error

    def test_result_failure(self):
        """Test creating a failed Result."""
        error = ValueError("Test error")
        result = Result.failure(error)
        self.assertFalse(result.is_success)
        self.assertTrue(result.is_failure)
        self.assertEqual(result.error, error)

        # Accessing value on a failure result should raise ValueError
        with self.assertRaises(ValueError):
            _ = result.value

    def test_result_on_success(self):
        """Test the on_success callback."""
        success_called = False

        def on_success(value):
            nonlocal success_called
            success_called = True
            self.assertEqual(value, "test value")

        result = Result.success("test value")
        returned_result = result.on_success(on_success)

        self.assertTrue(success_called)
        self.assertIs(returned_result, result)  # Should return self for chaining

        # on_success should not be called for failure results
        success_called = False
        error_result = Result.failure(ValueError("Test error"))
        error_result.on_success(on_success)
        self.assertFalse(success_called)

    def test_result_on_failure(self):
        """Test the on_failure callback."""
        failure_called = False
        test_error = ValueError("Test error")

        def on_failure(error):
            nonlocal failure_called
            failure_called = True
            self.assertEqual(error, test_error)

        result = Result.failure(test_error)
        returned_result = result.on_failure(on_failure)

        self.assertTrue(failure_called)
        self.assertIs(returned_result, result)  # Should return self for chaining

        # on_failure should not be called for success results
        failure_called = False
        success_result = Result.success("test value")
        success_result.on_failure(on_failure)
        self.assertFalse(failure_called)

    def test_result_map(self):
        """Test the map function for transforming success values."""
        result = Result.success(5)
        mapped_result = result.map(lambda x: x * 2)

        self.assertTrue(mapped_result.is_success)
        self.assertEqual(mapped_result.value, 10)

        # map should not transform failure results
        error = ValueError("Test error")
        error_result = Result.failure(error)
        mapped_error_result = error_result.map(lambda x: x * 2)

        self.assertFalse(mapped_error_result.is_success)
        self.assertEqual(mapped_error_result.error, error)

    def test_result_flat_map(self):
        """Test the flat_map function for chaining Results."""
        result = Result.success(5)

        def double_and_wrap(x):
            return Result.success(x * 2)

        flat_mapped_result = result.flat_map(double_and_wrap)

        self.assertTrue(flat_mapped_result.is_success)
        self.assertEqual(flat_mapped_result.value, 10)

        # flat_map should not transform failure results
        error = ValueError("Test error")
        error_result = Result.failure(error)
        flat_mapped_error_result = error_result.flat_map(double_and_wrap)

        self.assertFalse(flat_mapped_error_result.is_success)
        self.assertEqual(flat_mapped_error_result.error, error)

    def test_result_recover(self):
        """Test the recover function for handling errors."""
        error = ValueError("Test error")
        result = Result.failure(error)

        def recover_func(err):
            self.assertEqual(err, error)
            return "recovered value"

        recovered_value = result.recover(recover_func)
        self.assertEqual(recovered_value, "recovered value")

        # recover should return the original value for success results
        success_result = Result.success("original value")
        recovered_success = success_result.recover(recover_func)
        self.assertEqual(recovered_success, "original value")

    def test_result_unwrap_or(self):
        """Test the unwrap_or function for providing default values."""
        # For success results, should return the value
        success_result = Result.success("test value")
        self.assertEqual(success_result.unwrap_or("default"), "test value")

        # For failure results, should return the default
        error_result = Result.failure(ValueError("Test error"))
        self.assertEqual(error_result.unwrap_or("default"), "default")

    def test_result_unwrap_or_else(self):
        """Test the unwrap_or_else function for computing default values."""
        error = ValueError("Test error")

        # For success results, should return the value
        success_result = Result.success("test value")
        self.assertEqual(success_result.unwrap_or_else(lambda e: f"Error: {str(e)}"), "test value")

        # For failure results, should compute and return the default
        error_result = Result.failure(error)
        self.assertEqual(error_result.unwrap_or_else(lambda e: f"Error: {str(e)}"), "Error: Test error")

    def test_result_with_service_error(self):
        """Test Result with ServiceError."""
        error = ServiceError(
            message="Test service error",
            category=ErrorCategory.VALIDATION,
            http_status_code=400
        )
        result = Result.failure(error)

        self.assertTrue(result.is_failure)
        self.assertEqual(result.error, error)
        self.assertEqual(result.error.message, "Test service error")
        self.assertEqual(result.error.category, ErrorCategory.VALIDATION)

    def test_result_chaining(self):
        """Test chaining multiple Result operations."""
        result = Result.success(5)

        # Chain multiple operations
        final_result = (result
            .map(lambda x: x * 2)  # 10
            .flat_map(lambda x: Result.success(x + 5))  # 15
            .on_success(lambda x: None)  # No-op, just for chaining
            .map(lambda x: str(x))  # "15"
        )

        self.assertTrue(final_result.is_success)
        self.assertEqual(final_result.value, "15")

        # Chain with a failure in the middle
        error_result = Result.success(5)
        final_error_result = (error_result
            .map(lambda x: x * 2)  # 10
            .flat_map(lambda x: Result.failure(ValueError(f"Error with {x}")))  # Failure
            .map(lambda x: x + 5)  # Should not be executed
        )

        self.assertFalse(final_error_result.is_success)
        self.assertEqual(str(final_error_result.error), "Error with 10")


if __name__ == "__main__":
    unittest.main()