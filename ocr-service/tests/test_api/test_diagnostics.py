#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the diagnostic endpoints of the OCR Service.

This module contains tests for the diagnostic endpoints that provide troubleshooting
capabilities for the OCR Service. These endpoints allow operations staff to retrieve logs,
check configuration, run diagnostic tests, and manage OCR models.

The tests verify that:
1. Diagnostic endpoints correctly provide logs, configuration, and test capabilities
2. Authentication and authorization are properly enforced for sensitive endpoints
3. Error handling is implemented correctly for diagnostic endpoint failures
4. Loaded OCR models can be checked and reloaded when necessary
5. System diagnostic information is properly provided and sanitized

These tests ensure that operations staff can effectively troubleshoot issues with the
OCR Service through the diagnostic API endpoints.
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import status
from io import BytesIO

# Import testing utilities
from ..conftest import (
    client,
    app,
    auth_token,
    mock_rabbitmq,
    mock_s3,
    mock_gpu_available,
    mock_gpu_unavailable,
    validate_response,
    mock_tensorflow_service,
    mock_metrics_service,
)


@pytest.mark.parametrize(
    "level,hours,service,limit,expected_status",
    [
        ("INFO", 24, None, 1000, status.HTTP_200_OK),
        ("DEBUG", 12, "ocr", 500, status.HTTP_200_OK),
        ("ERROR", 48, None, 100, status.HTTP_200_OK),
        ("INVALID", 24, None, 1000, status.HTTP_400_BAD_REQUEST),
    ],
)
def test_get_logs(client, auth_token, level, hours, service, limit, expected_status):
    """Test the /diagnostics/logs endpoint with various parameters."""
    # Prepare query parameters
    params = {"level": level, "hours": hours, "limit": limit}
    if service:
        params["service"] = service

    # Make request with authentication
    response = client.get(
        "/diagnostics/logs",
        params=params,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response status
    assert response.status_code == expected_status

    # For successful responses, validate the structure
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "status" in data
        assert "count" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)
        assert "start_time" in data
        assert "end_time" in data
        assert "level" in data
        assert data["level"] == level


def test_get_logs_unauthorized(client):
    """Test that the /diagnostics/logs endpoint requires authentication."""
    response = client.get("/diagnostics/logs", params={"level": "INFO", "hours": 24})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"].lower()


@patch("os.path.exists")
@patch("builtins.open", new_callable=MagicMock)
def test_get_logs_file_handling(mock_open, mock_exists, client, auth_token):
    """Test log file handling in the /diagnostics/logs endpoint."""
    # Test when log file exists
    mock_exists.return_value = True
    mock_file = MagicMock()
    mock_file.__enter__.return_value = [
        "2023-01-01T12:00:00Z - ocr-service - INFO - Processing document doc123\n",
        "2023-01-01T12:01:00Z - ocr-service - ERROR - Failed to process document doc456\n",
        "2023-01-01T12:02:00Z - ocr-service - DEBUG - Model loaded: typed_text\n",
        "2023-01-01T12:03:00Z - ocr-service - WARN - Low confidence score: 0.65 for field 'tax_id'\n",
    ]
    mock_open.return_value = mock_file

    response = client.get(
        "/diagnostics/logs",
        params={"level": "INFO", "hours": 24},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert len(data["logs"]) > 0

    # Test when log file doesn't exist
    mock_exists.return_value = False

    response = client.get(
        "/diagnostics/logs",
        params={"level": "INFO", "hours": 24},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "error"
    assert "Log file not found" in data["message"]
    assert data["logs"] == []


def test_get_config(client, auth_token):
    """Test the /diagnostics/config endpoint."""
    response = client.get(
        "/diagnostics/config",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "config" in data

    # Verify config structure
    config = data["config"]
    assert "app" in config
    assert "tensorflow" in config
    assert "rabbitmq" in config
    assert "s3" in config
    assert "logging" in config

    # Verify sensitive information is not exposed
    assert "password" not in json.dumps(config["rabbitmq"])
    assert "credentials" not in json.dumps(config["rabbitmq"])
    assert "access_key" not in json.dumps(config["s3"])
    assert "secret_key" not in json.dumps(config["s3"])


def test_get_config_unauthorized(client):
    """Test that the /diagnostics/config endpoint requires authentication."""
    response = client.get("/diagnostics/config")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "test_type,parameters,include_file,expected_status,expected_message",
    [
        ("ocr", {"confidence_threshold": 0.8}, True, status.HTTP_200_OK, None),
        ("connectivity", {}, False, status.HTTP_200_OK, None),
        ("performance", {"duration": 10}, False, status.HTTP_200_OK, None),
        ("model", {"model_id": "typed_text"}, False, status.HTTP_200_OK, None),
        ("invalid", {}, False, status.HTTP_400_BAD_REQUEST, "Invalid test type"),
        ("ocr", {}, False, status.HTTP_400_BAD_REQUEST, "Test file is required"),  # OCR test without file
    ],
)
def test_run_diagnostic_test(client, auth_token, test_type, parameters, include_file, expected_status, expected_message):
    """Test the /diagnostics/test endpoint with various test types."""
    # Prepare request data
    data = {"test_type": test_type, "parameters": parameters}
    files = None

    # Add test file if needed
    if include_file:
        test_file_content = b"This is a test document for OCR processing."
        files = {"test_file": ("test.pdf", BytesIO(test_file_content), "application/pdf")}

    # Make request with authentication
    response = client.post(
        "/diagnostics/test",
        data={"test_request": json.dumps(data)},
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response status
    assert response.status_code == expected_status
    
    # Check error message for error responses
    if expected_status != status.HTTP_200_OK and expected_message:
        assert expected_message in response.json()["detail"]

    # For successful responses, validate the structure
    if response.status_code == status.HTTP_200_OK:
        data = response.json()
        assert "test_type" in data
        assert data["test_type"] == test_type
        assert "timestamp" in data
        assert "parameters" in data
        assert "results" in data
        assert "status" in data
        assert data["status"] == "success"


def test_run_diagnostic_test_unauthorized(client):
    """Test that the /diagnostics/test endpoint requires authentication."""
    data = {"test_type": "connectivity", "parameters": {}}
    response = client.post("/diagnostics/test", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"].lower()


@patch("src.services.ocr_service.run_diagnostic_ocr")
def test_run_ocr_diagnostic(mock_run_diagnostic_ocr, client, auth_token):
    """Test the OCR diagnostic test functionality."""
    # Mock the OCR diagnostic function
    mock_run_diagnostic_ocr.return_value = {
        "confidence": 0.95,
        "processing_time": 1.23,
        "extracted_text": "Sample extracted text",
        "model_used": "typed_text",
        "field_confidences": {
            "business_name": 0.98,
            "tax_id": 0.95,
            "address": 0.92,
            "requested_amount": 0.97,
        },
        "document_type": "APPLICATION",
    }

    # Prepare request data
    data = {"test_type": "ocr", "parameters": {"confidence_threshold": 0.8}}
    test_file_content = b"This is a test document for OCR processing."
    files = {"test_file": ("test.pdf", BytesIO(test_file_content), "application/pdf")}

    # Make request with authentication
    response = client.post(
        "/diagnostics/test",
        data={"test_request": json.dumps(data)},
        files=files,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["results"]["confidence"] == 0.95
    assert result["results"]["extracted_text"] == "Sample extracted text"
    assert result["results"]["model_used"] == "typed_text"
    assert result["results"]["document_type"] == "APPLICATION"
    assert "field_confidences" in result["results"]
    assert result["results"]["field_confidences"]["business_name"] == 0.98

    # Verify the mock was called with correct parameters
    mock_run_diagnostic_ocr.assert_called_once()
    args, kwargs = mock_run_diagnostic_ocr.call_args
    assert kwargs["parameters"] == {"confidence_threshold": 0.8}


@patch("src.models.model_factory.get_models_info")
def test_get_models(mock_get_models_info, client, auth_token):
    """Test the /diagnostics/models endpoint."""
    # Mock the models info function
    mock_get_models_info.return_value = [
        {
            "id": "typed_text",
            "type": "TYPED",
            "version": "1.0.0",
            "loaded": True,
            "last_loaded": datetime.now().isoformat(),
            "memory_usage_mb": 1024,
            "supported_document_types": ["APPLICATION", "TAX_RETURN"],
        },
        {
            "id": "handwritten_text",
            "type": "HANDWRITTEN",
            "version": "1.0.0",
            "loaded": True,
            "last_loaded": datetime.now().isoformat(),
            "memory_usage_mb": 2048,
            "supported_document_types": ["ID_DOCUMENT"],
        },
    ]

    # Make request with authentication
    response = client.get(
        "/diagnostics/models",
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "models" in data
    assert len(data["models"]) == 2
    assert data["models"][0]["id"] == "typed_text"
    assert data["models"][1]["id"] == "handwritten_text"


def test_get_models_unauthorized(client):
    """Test that the /diagnostics/models endpoint requires authentication."""
    response = client.get("/diagnostics/models")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"].lower()


@patch("src.models.model_factory.reload_models")
def test_reload_models(mock_reload_models, client, auth_token):
    """Test the /diagnostics/models/reload endpoint."""
    # Mock the reload models function
    mock_reload_models.return_value = {
        "typed_text": {"status": "reloaded", "success": True},
        "handwritten_text": {"status": "reloaded", "success": True},
    }

    # Make request with admin authentication
    response = client.post(
        "/diagnostics/models/reload",
        json={"model_ids": ["typed_text", "handwritten_text"], "force": True},
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "status" in data
    assert data["status"] == "success"
    assert "message" in data
    assert "results" in data
    assert "typed_text" in data["results"]
    assert "handwritten_text" in data["results"]

    # Verify the mock was called with correct parameters
    mock_reload_models.assert_called_once_with(
        model_ids=["typed_text", "handwritten_text"], force=True
    )


def test_reload_models_unauthorized(client):
    """Test that the /diagnostics/models/reload endpoint requires authentication."""
    response = client.post(
        "/diagnostics/models/reload",
        json={"model_ids": ["typed_text"], "force": True},
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"].lower()


@pytest.mark.parametrize(
    "role,expected_status",
    [
        ("operations_staff", status.HTTP_403_FORBIDDEN),
        ("system_admin", status.HTTP_200_OK),
    ],
)
def test_reload_models_authorization(client, role, expected_status):
    """Test that the /diagnostics/models/reload endpoint requires admin role."""
    # Create a token with the specified role
    with patch("src.services.auth_service.verify_token", return_value={
        "sub": "test-user",
        "name": "Test User",
        "email": "test@dollarfunding.com",
        "roles": [role],
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=1),
    }):
        # Make request with the token
        response = client.post(
            "/diagnostics/models/reload",
            json={"model_ids": ["typed_text"], "force": True},
            headers={"Authorization": f"Bearer test-token-{role}"},
        )

        # Check response status
        assert response.status_code == expected_status


def test_get_system_diagnostics(client, auth_token):
    """Test the /diagnostics/system endpoint."""
    # Set some environment variables for testing
    original_env = os.environ.copy()
    try:
        os.environ["OCR_TEST_VAR"] = "test_value"
        os.environ["OCR_PASSWORD"] = "secret_password"
        os.environ["OCR_API_KEY"] = "api-key-value"
        os.environ["OCR_SECRET"] = "secret-value"

        # Make request with authentication
        response = client.get(
            "/diagnostics/system",
            headers={"Authorization": f"Bearer {auth_token}"},
        )

        # Check response
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"
        assert "system" in data

        # Verify system info structure
        system = data["system"]
        assert "python" in system
        assert "packages" in system
        assert "environment" in system

        # Verify sensitive environment variables are not exposed
        assert "OCR_TEST_VAR" in system["environment"]
        assert "OCR_PASSWORD" not in system["environment"]
        assert "OCR_API_KEY" not in system["environment"]
        assert "OCR_SECRET" not in system["environment"]
    finally:
        # Restore original environment
        os.environ.clear()
        os.environ.update(original_env)


def test_get_system_diagnostics_unauthorized(client):
    """Test that the /diagnostics/system endpoint requires authentication."""
    response = client.get("/diagnostics/system")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Not authenticated" in response.json()["detail"].lower()


@patch("src.utils.error_utils.format_exception")
def test_error_handling(mock_format_exception, client, auth_token):
    """Test error handling in diagnostic endpoints."""
    # Mock the error formatting function to simulate an error
    mock_format_exception.side_effect = Exception("Test error")

    # Test error handling in logs endpoint
    response = client.get(
        "/diagnostics/logs",
        params={"level": "INFO", "hours": 24},
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Error retrieving logs" in response.json()["detail"]

    # Test error handling in config endpoint
    response = client.get(
        "/diagnostics/config",
        headers={"Authorization": f"Bearer {auth_token}"},
    )
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Error retrieving configuration" in response.json()["detail"]


@patch("src.services.ocr_service.test_connectivity")
def test_connectivity_diagnostic(mock_test_connectivity, client, auth_token):
    """Test the connectivity diagnostic test functionality."""
    # Mock the connectivity test function
    mock_test_connectivity.return_value = {
        "rabbitmq": {"status": "connected", "latency_ms": 15},
        "s3": {"status": "connected", "latency_ms": 45},
        "gpu": {"status": "available", "memory_mb": 8192},
    }

    # Prepare request data
    data = {"test_type": "connectivity", "parameters": {}}

    # Make request with authentication
    response = client.post(
        "/diagnostics/test",
        json=data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["test_type"] == "connectivity"
    assert "rabbitmq" in result["results"]
    assert "s3" in result["results"]
    assert "gpu" in result["results"]
    assert result["results"]["rabbitmq"]["status"] == "connected"


@patch("src.services.ocr_service.run_performance_test")
def test_performance_diagnostic(mock_run_performance_test, client, auth_token):
    """Test the performance diagnostic test functionality."""
    # Mock the performance test function
    mock_run_performance_test.return_value = {
        "cpu_benchmark": {"score": 85, "time_ms": 120},
        "gpu_benchmark": {"score": 95, "time_ms": 45},
        "memory_benchmark": {"read_mbps": 1200, "write_mbps": 950},
        "model_inference": {
            "typed_text": {"time_ms": 75, "throughput": 13.3},
            "handwritten_text": {"time_ms": 120, "throughput": 8.3},
        },
    }

    # Prepare request data
    data = {"test_type": "performance", "parameters": {"duration": 5}}

    # Make request with authentication
    response = client.post(
        "/diagnostics/test",
        json=data,
        headers={"Authorization": f"Bearer {auth_token}"},
    )

    # Check response
    assert response.status_code == status.HTTP_200_OK
    result = response.json()
    assert result["test_type"] == "performance"
    assert "cpu_benchmark" in result["results"]
    assert "gpu_benchmark" in result["results"]
    assert "memory_benchmark" in result["results"]
    assert "model_inference" in result["results"]
    assert "typed_text" in result["results"]["model_inference"]
    assert "handwritten_text" in result["results"]["model_inference"]