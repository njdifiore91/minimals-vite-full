"""
Unit tests for error handling type definitions in the Document Service.

This module contains tests for the error handling types defined in document_service.src.types.errors,
including ServiceError, ErrorDetails, LogEntry, ErrorCategory, MonitoringAlert, and Result.
These tests ensure that error handling is consistent and provides appropriate context throughout the service.
"""

import pytest
from datetime import datetime, timedelta
import json
from enum import Enum
from typing import Dict, Any, Optional

# Fix the import path to match the actual module structure
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


class TestErrorCategory:
    """Tests for the ErrorCategory enum."""
    
    def test_error_category_values(self):
        """Test that ErrorCategory enum has the expected values."""
        assert ErrorCategory.CRITICAL.name == "CRITICAL"
        assert ErrorCategory.ERROR.name == "ERROR"
        assert ErrorCategory.WARNING.name == "WARNING"
        assert ErrorCategory.VALIDATION.name == "VALIDATION"
        assert ErrorCategory.SECURITY.name == "SECURITY"
        assert ErrorCategory.INTEGRATION.name == "INTEGRATION"
        assert ErrorCategory.CLASSIFICATION.name == "CLASSIFICATION"
        assert ErrorCategory.EXTRACTION.name == "EXTRACTION"
        assert ErrorCategory.MESSAGING.name == "MESSAGING"
    
    def test_error_category_comparison(self):
        """Test that ErrorCategory enum values can be compared."""
        assert ErrorCategory.CRITICAL != ErrorCategory.ERROR
        assert ErrorCategory.ERROR != ErrorCategory.WARNING
        assert ErrorCategory.VALIDATION != ErrorCategory.SECURITY
        
        # Test that the same enum values are equal
        critical1 = ErrorCategory.CRITICAL
        critical2 = ErrorCategory.CRITICAL
        assert critical1 == critical2
        
    def test_error_category_in_context(self):
        """Test using ErrorCategory in a dictionary context."""
        error_map = {
            ErrorCategory.CRITICAL: "Critical system failure",
            ErrorCategory.ERROR: "Standard error",
            ErrorCategory.WARNING: "Warning condition"
        }
        
        assert error_map[ErrorCategory.CRITICAL] == "Critical system failure"
        assert error_map[ErrorCategory.ERROR] == "Standard error"
        assert error_map[ErrorCategory.WARNING] == "Warning condition"


class TestErrorDetails:
    """Tests for the ErrorDetails class."""
    
    def test_error_details_initialization(self):
        """Test that ErrorDetails can be initialized with basic parameters."""
        error_details = ErrorDetails(
            message="Test error message",
            category=ErrorCategory.ERROR,
            capture_stack_trace=False
        )
        
        assert error_details.message == "Test error message"
        assert error_details.category == ErrorCategory.ERROR
        assert error_details.exception is None
        assert isinstance(error_details.context, dict)
        assert error_details.context == {}
        assert isinstance(error_details.timestamp, datetime)
        assert error_details.service_name == "document-service"
        assert error_details.stack_trace is None  # No stack trace captured
    
    def test_error_details_with_exception(self):
        """Test that ErrorDetails captures exception information."""
        try:
            # Generate an exception
            1 / 0
        except Exception as e:
            error_details = ErrorDetails(
                message="Division by zero",
                category=ErrorCategory.ERROR,
                exception=e,
                capture_stack_trace=True
            )
            
            assert error_details.message == "Division by zero"
            assert error_details.exception is e
            assert "ZeroDivisionError" in error_details.stack_trace
    
    def test_error_details_with_context(self):
        """Test that ErrorDetails captures context information."""
        context = {
            "document_id": "doc123",
            "operation": "classification",
            "user_id": "user456"
        }
        
        error_details = ErrorDetails(
            message="Context test",
            category=ErrorCategory.ERROR,
            context=context,
            capture_stack_trace=False
        )
        
        assert error_details.context == context
        assert error_details.context["document_id"] == "doc123"
        assert error_details.context["operation"] == "classification"
    
    def test_error_details_to_dict(self):
        """Test that ErrorDetails can be converted to a dictionary."""
        timestamp = datetime.utcnow()
        error_details = ErrorDetails(
            message="Serialization test",
            category=ErrorCategory.VALIDATION,
            context={"field": "amount", "value": "invalid"},
            timestamp=timestamp,
            capture_stack_trace=False
        )
        
        result = error_details.to_dict()
        
        assert result["message"] == "Serialization test"
        assert result["category"] == "VALIDATION"
        assert result["context"] == {"field": "amount", "value": "invalid"}
        assert result["timestamp"] == timestamp.isoformat()
        assert result["service_name"] == "document-service"
        assert result["exception_type"] is None
        
    def test_error_details_with_custom_service_name(self):
        """Test that ErrorDetails accepts a custom service name."""
        error_details = ErrorDetails(
            message="Custom service",
            category=ErrorCategory.ERROR,
            service_name="custom-service",
            capture_stack_trace=False
        )
        
        assert error_details.service_name == "custom-service"
        result = error_details.to_dict()
        assert result["service_name"] == "custom-service"


class TestLogEntry:
    """Tests for the LogEntry class."""
    
    def test_log_entry_initialization(self):
        """Test that LogEntry can be initialized with basic parameters."""
        log_entry = LogEntry(
            message="Test log message",
            level="INFO"
        )
        
        assert log_entry.message == "Test log message"
        assert log_entry.level == "INFO"
        assert isinstance(log_entry.context, dict)
        assert log_entry.context == {}
        assert isinstance(log_entry.timestamp, datetime)
        assert log_entry.service_name == "document-service"
        assert log_entry.correlation_id is None
        assert log_entry.document_id is None
        assert log_entry.operation is None
    
    def test_log_entry_with_all_fields(self):
        """Test that LogEntry can be initialized with all fields."""
        timestamp = datetime.utcnow()
        log_entry = LogEntry(
            message="Complete log entry",
            level="ERROR",
            context={"error_code": "E123", "source": "classification_service"},
            timestamp=timestamp,
            service_name="document-service",
            correlation_id="corr-123",
            document_id="doc-456",
            operation="classify_document"
        )
        
        assert log_entry.message == "Complete log entry"
        assert log_entry.level == "ERROR"
        assert log_entry.context == {"error_code": "E123", "source": "classification_service"}
        assert log_entry.timestamp == timestamp
        assert log_entry.service_name == "document-service"
        assert log_entry.correlation_id == "corr-123"
        assert log_entry.document_id == "doc-456"
        assert log_entry.operation == "classify_document"
    
    def test_log_entry_to_dict(self):
        """Test that LogEntry can be converted to a dictionary."""
        timestamp = datetime.utcnow()
        log_entry = LogEntry(
            message="Serialization test",
            level="WARN",
            context={"warning_code": "W123"},
            timestamp=timestamp,
            correlation_id="corr-789",
            document_id="doc-101112",
            operation="validate_document"
        )
        
        result = log_entry.to_dict()
        
        assert result["message"] == "Serialization test"
        assert result["level"] == "WARN"
        assert result["context"] == {"warning_code": "W123"}
        assert result["timestamp"] == timestamp.isoformat()
        assert result["service_name"] == "document-service"
        assert result["correlation_id"] == "corr-789"
        assert result["document_id"] == "doc-101112"
        assert result["operation"] == "validate_document"
    
    def test_log_entry_with_different_log_levels(self):
        """Test that LogEntry accepts different log levels."""
        # Test with all specified log levels from section 0.2.5
        error_log = LogEntry("Error message", level="ERROR")
        warn_log = LogEntry("Warning message", level="WARN")
        info_log = LogEntry("Info message", level="INFO")
        debug_log = LogEntry("Debug message", level="DEBUG")
        
        assert error_log.level == "ERROR"
        assert warn_log.level == "WARN"
        assert info_log.level == "INFO"
        assert debug_log.level == "DEBUG"
        
        # Verify serialization of different log levels
        assert error_log.to_dict()["level"] == "ERROR"
        assert warn_log.to_dict()["level"] == "WARN"
        assert info_log.to_dict()["level"] == "INFO"
        assert debug_log.to_dict()["level"] == "DEBUG"


class TestMonitoringAlert:
    """Tests for the MonitoringAlert class."""
    
    def test_monitoring_alert_initialization(self):
        """Test that MonitoringAlert can be initialized with basic parameters."""
        alert = MonitoringAlert(
            title="Test Alert",
            message="This is a test alert"
        )
        
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test alert"
        assert alert.severity == "critical"  # Default severity
        assert alert.error_details is None
        assert isinstance(alert.timestamp, datetime)
        assert alert.service_name == "document-service"
        assert alert.alert_tags == []
        assert alert.notification_channels == ["default"]
    
    def test_monitoring_alert_with_error_details(self):
        """Test that MonitoringAlert can include ErrorDetails."""
        error_details = ErrorDetails(
            message="Underlying error",
            category=ErrorCategory.CRITICAL,
            capture_stack_trace=False
        )
        
        alert = MonitoringAlert(
            title="Critical System Error",
            message="A critical error occurred in the document classification system",
            severity="critical",
            error_details=error_details,
            alert_tags=["classification", "critical", "production"]
        )
        
        assert alert.title == "Critical System Error"
        assert alert.error_details is error_details
        assert alert.alert_tags == ["classification", "critical", "production"]
    
    def test_monitoring_alert_with_different_severity_levels(self):
        """Test that MonitoringAlert accepts different severity levels."""
        critical_alert = MonitoringAlert("Critical Alert", "Critical message", severity="critical")
        error_alert = MonitoringAlert("Error Alert", "Error message", severity="error")
        warning_alert = MonitoringAlert("Warning Alert", "Warning message", severity="warning")
        info_alert = MonitoringAlert("Info Alert", "Info message", severity="info")
        
        assert critical_alert.severity == "critical"
        assert error_alert.severity == "error"
        assert warning_alert.severity == "warning"
        assert info_alert.severity == "info"
    
    def test_monitoring_alert_to_dict(self):
        """Test that MonitoringAlert can be converted to a dictionary."""
        timestamp = datetime.utcnow()
        alert = MonitoringAlert(
            title="Serialization Test",
            message="Testing alert serialization",
            severity="warning",
            timestamp=timestamp,
            service_name="test-service",
            alert_tags=["test", "serialization"],
            notification_channels=["email", "slack"]
        )
        
        result = alert.to_dict()
        
        assert result["title"] == "Serialization Test"
        assert result["message"] == "Testing alert serialization"
        assert result["severity"] == "warning"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["service_name"] == "test-service"
        assert result["alert_tags"] == ["test", "serialization"]
        assert result["notification_channels"] == ["email", "slack"]
        assert "error_details" not in result  # No error details provided
    
    def test_monitoring_alert_with_error_details_serialization(self):
        """Test that MonitoringAlert serializes included ErrorDetails."""
        error_details = ErrorDetails(
            message="Database connection failed",
            category=ErrorCategory.CRITICAL,
            context={"host": "db.example.com", "port": 5432},
            capture_stack_trace=False
        )
        
        alert = MonitoringAlert(
            title="Database Error",
            message="Failed to connect to the database",
            error_details=error_details
        )
        
        result = alert.to_dict()
        
        assert "error_details" in result
        assert result["error_details"]["message"] == "Database connection failed"
        assert result["error_details"]["category"] == "CRITICAL"
        assert result["error_details"]["context"] == {"host": "db.example.com", "port": 5432}


class TestServiceError:
    """Tests for the ServiceError class."""
    
    def test_service_error_initialization(self):
        """Test that ServiceError can be initialized with basic parameters."""
        error = ServiceError(
            message="Test service error",
            category=ErrorCategory.ERROR
        )
        
        assert error.message == "Test service error"
        assert error.category == ErrorCategory.ERROR
        assert error.original_exception is None
        assert isinstance(error.context, dict)
        assert error.context == {}
        assert error.http_status_code is None
        assert isinstance(error.error_details, ErrorDetails)
        assert error.error_details.message == "Test service error"
        assert error.error_details.category == ErrorCategory.ERROR
    
    def test_service_error_with_http_status(self):
        """Test that ServiceError can include HTTP status code."""
        error = ServiceError(
            message="Not found",
            category=ErrorCategory.ERROR,
            http_status_code=404
        )
        
        assert error.message == "Not found"
        assert error.http_status_code == 404
        
        # Test API response format
        api_response = error.to_api_response()
        assert api_response["success"] == False
        assert api_response["error"]["message"] == "Not found"
        assert api_response["error"]["code"] == "ERROR.404"
    
    def test_service_error_with_original_exception(self):
        """Test that ServiceError can wrap an original exception."""
        original_exception = ValueError("Invalid value")
        error = ServiceError(
            message="Validation failed",
            category=ErrorCategory.VALIDATION,
            original_exception=original_exception,
            http_status_code=400
        )
        
        assert error.message == "Validation failed"
        assert error.original_exception is original_exception
        assert error.http_status_code == 400
        assert error.error_details.exception is original_exception
    
    def test_service_error_to_dict(self):
        """Test that ServiceError can be converted to a dictionary."""
        error = ServiceError(
            message="Serialization test",
            category=ErrorCategory.INTEGRATION,
            context={"service": "database", "operation": "query"},
            http_status_code=502
        )
        
        result = error.to_dict()
        
        assert "error" in result
        assert result["error"]["message"] == "Serialization test"
        assert result["error"]["category"] == "INTEGRATION"
        assert result["error"]["http_status_code"] == 502
        assert "details" in result["error"]
        assert result["error"]["details"]["context"] == {"service": "database", "operation": "query"}
    
    def test_specific_error_types(self):
        """Test specific error type subclasses."""
        validation_error = ValidationError("Invalid input")
        classification_error = ClassificationError("Classification failed")
        extraction_error = ExtractionError("Data extraction failed")
        integration_error = IntegrationError("Service integration failed")
        security_error = SecurityError("Authentication failed")
        messaging_error = MessagingError("Message queue operation failed")
        
        # Check that each error has the correct category
        assert validation_error.category == ErrorCategory.VALIDATION
        assert classification_error.category == ErrorCategory.CLASSIFICATION
        assert extraction_error.category == ErrorCategory.EXTRACTION
        assert integration_error.category == ErrorCategory.INTEGRATION
        assert security_error.category == ErrorCategory.SECURITY
        assert messaging_error.category == ErrorCategory.MESSAGING
        
        # Check that each error has the correct HTTP status code
        assert validation_error.http_status_code == 400
        assert classification_error.http_status_code == 422
        assert extraction_error.http_status_code == 422
        assert integration_error.http_status_code == 502
        assert security_error.http_status_code == 403
        assert messaging_error.http_status_code == 500


class TestResult:
    """Tests for the Result generic type."""
    
    def test_result_success(self):
        """Test creating a successful Result."""
        result = Result.success("success value")
        
        assert result.is_success is True
        assert result.is_failure is False
        assert result.value == "success value"
        
        # Accessing error on a success should raise ValueError
        with pytest.raises(ValueError):
            error = result.error
    
    def test_result_failure(self):
        """Test creating a failed Result."""
        error = ValueError("test error")
        result = Result.failure(error)
        
        assert result.is_success is False
        assert result.is_failure is True
        assert result.error is error
        
        # Accessing value on a failure should raise ValueError
        with pytest.raises(ValueError):
            value = result.value
    
    def test_result_on_success_callback(self):
        """Test the on_success callback."""
        callback_called = False
        callback_value = None
        
        def success_callback(value):
            nonlocal callback_called, callback_value
            callback_called = True
            callback_value = value
        
        # Test with a success result
        result = Result.success("success data")
        result.on_success(success_callback)
        
        assert callback_called is True
        assert callback_value == "success data"
        
        # Test with a failure result - callback should not be called
        callback_called = False
        callback_value = None
        error_result = Result.failure(Exception("test error"))
        error_result.on_success(success_callback)
        
        assert callback_called is False
        assert callback_value is None
    
    def test_result_on_failure_callback(self):
        """Test the on_failure callback."""
        callback_called = False
        callback_error = None
        
        def failure_callback(error):
            nonlocal callback_called, callback_error
            callback_called = True
            callback_error = error
        
        # Test with a failure result
        error = ValueError("test error")
        result = Result.failure(error)
        result.on_failure(failure_callback)
        
        assert callback_called is True
        assert callback_error is error
        
        # Test with a success result - callback should not be called
        callback_called = False
        callback_error = None
        success_result = Result.success("success data")
        success_result.on_failure(failure_callback)
        
        assert callback_called is False
        assert callback_error is None
    
    def test_result_map(self):
        """Test the map function for transforming success values."""
        # Test with a success result
        result = Result.success(5)
        mapped_result = result.map(lambda x: x * 2)
        
        assert mapped_result.is_success is True
        assert mapped_result.value == 10
        
        # Test with a failure result - should pass through the error
        error = ValueError("test error")
        error_result = Result.failure(error)
        mapped_error_result = error_result.map(lambda x: x * 2)
        
        assert mapped_error_result.is_success is False
        assert mapped_error_result.error is error
    
    def test_result_flat_map(self):
        """Test the flat_map function for chaining Results."""
        # Test with a success result
        result = Result.success(5)
        flat_mapped_result = result.flat_map(lambda x: Result.success(x * 2))
        
        assert flat_mapped_result.is_success is True
        assert flat_mapped_result.value == 10
        
        # Test with a success result that maps to a failure
        result = Result.success(5)
        error = ValueError("mapped error")
        flat_mapped_error_result = result.flat_map(lambda x: Result.failure(error))
        
        assert flat_mapped_error_result.is_success is False
        assert flat_mapped_error_result.error is error
        
        # Test with a failure result - should pass through the error
        original_error = ValueError("original error")
        error_result = Result.failure(original_error)
        flat_mapped_error_result = error_result.flat_map(lambda x: Result.success(x * 2))
        
        assert flat_mapped_error_result.is_success is False
        assert flat_mapped_error_result.error is original_error
    
    def test_result_recover(self):
        """Test the recover function for handling errors."""
        # Test with a success result - should return the original value
        result = Result.success("original value")
        recovered_value = result.recover(lambda e: "recovered value")
        
        assert recovered_value == "original value"
        
        # Test with a failure result - should return the recovered value
        error_result = Result.failure(ValueError("test error"))
        recovered_value = error_result.recover(lambda e: "recovered value")
        
        assert recovered_value == "recovered value"
    
    def test_result_unwrap_or(self):
        """Test the unwrap_or function for providing default values."""
        # Test with a success result - should return the original value
        result = Result.success("original value")
        unwrapped_value = result.unwrap_or("default value")
        
        assert unwrapped_value == "original value"
        
        # Test with a failure result - should return the default value
        error_result = Result.failure(ValueError("test error"))
        unwrapped_value = error_result.unwrap_or("default value")
        
        assert unwrapped_value == "default value"
    
    def test_result_unwrap_or_else(self):
        """Test the unwrap_or_else function for computing default values."""
        # Test with a success result - should return the original value
        result = Result.success("original value")
        unwrapped_value = result.unwrap_or_else(lambda e: f"Error: {str(e)}")
        
        assert unwrapped_value == "original value"
        
        # Test with a failure result - should return the computed default value
        error = ValueError("test error")
        error_result = Result.failure(error)
        unwrapped_value = error_result.unwrap_or_else(lambda e: f"Error: {str(e)}")
        
        assert unwrapped_value == "Error: test error"
    