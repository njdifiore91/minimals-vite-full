#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the OCR Service diagnostic endpoints.

This module contains tests for the diagnostic endpoints of the OCR Service API,
which provide operations staff with tools to troubleshoot and monitor the service.
These tests verify that the endpoints correctly provide logs, configuration information,
and diagnostic test capabilities.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the router to test
from src.api.diagnostics import router, verify_admin_access
from src.types.models import OCRModelType
from src.types.errors import ErrorCategory
from src.utils import logging_utils, tensorflow_utils, error_utils


# Create a test FastAPI app with the diagnostics router
@pytest.fixture
def test_app():
    """Create a test FastAPI app with the diagnostics router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI app."""
    return TestClient(test_app)


# Mock the admin access verification to allow tests to run
@pytest.fixture(autouse=True)
def mock_admin_access():
    """Mock the admin access verification to allow tests to run."""
    with patch("src.api.diagnostics.verify_admin_access", return_value=True):
        yield


# Mock the logging utilities
@pytest.fixture
def mock_logging_utils():
    """Mock the logging utilities."""
    with patch("src.api.diagnostics.logging_utils") as mock:
        # Configure the mock to return sample log entries
        mock.get_log_level.return_value = 20  # INFO level
        mock.get_log_entries.return_value = [
            {
                "timestamp": "2023-01-01T12:00:00Z",
                "level": "INFO",
                "message": "Sample log message 1",
                "service": "ocr-service",
                "context": {"request_id": "req-123"}
            },
            {
                "timestamp": "2023-01-01T12:01:00Z",
                "level": "ERROR",
                "message": "Sample error message",
                "service": "ocr-service",
                "context": {"request_id": "req-123"},
                "error": {
                    "message": "Test error",
                    "stack_trace": "Traceback: ..."
                }
            }
        ]
        yield mock


# Mock the TensorFlow utilities
@pytest.fixture
def mock_tensorflow_utils():
    """Mock the TensorFlow utilities."""
    with patch("src.api.diagnostics.tensorflow_utils") as mock:
        # Configure the mock to return sample diagnostic information
        mock.check_cpu_info.return_value = {
            "cores": 8,
            "model": "Intel(R) Core(TM) i7-10700K CPU @ 3.80GHz",
            "usage": 25.5
        }
        mock.check_memory_info.return_value = {
            "total": 16384,  # MB
            "available": 8192,  # MB
            "used": 8192,  # MB
            "percent": 50.0
        }
        mock.check_disk_info.return_value = {
            "total": 512000,  # MB
            "available": 256000,  # MB
            "used": 256000,  # MB
            "percent": 50.0
        }
        mock.check_python_info.return_value = {
            "version": "3.9.7",
            "implementation": "CPython",
            "compiler": "GCC 9.3.0"
        }
        mock.check_gpu_info.return_value = {
            "available": True,
            "devices": [
                {
                    "name": "NVIDIA GeForce RTX 3080",
                    "memory_total": 10240,  # MB
                    "memory_used": 2048,  # MB
                    "compute_capability": "8.6"
                }
            ]
        }
        mock.check_loaded_models.return_value = [
            {
                "name": "typed_text_ocr",
                "version": "1.0.0",
                "type": "TYPED",
                "loaded_at": "2023-01-01T12:00:00Z"
            },
            {
                "name": "handwritten_text_ocr",
                "version": "1.0.0",
                "type": "HANDWRITTEN",
                "loaded_at": "2023-01-01T12:00:00Z"
            }
        ]
        mock.check_model_performance.return_value = {
            "typed_text_ocr": {
                "inference_time": 0.125,  # seconds
                "accuracy": 0.98,
                "memory_usage": 1024  # MB
            },
            "handwritten_text_ocr": {
                "inference_time": 0.250,  # seconds
                "accuracy": 0.92,
                "memory_usage": 2048  # MB
            }
        }
        mock.check_rabbitmq_connectivity.return_value = {
            "connected": True,
            "latency": 0.015  # seconds
        }
        mock.check_s3_connectivity.return_value = {
            "connected": True,
            "latency": 0.025  # seconds
        }
        yield mock


# Mock the OCR service
@pytest.fixture
def mock_ocr_service():
    """Mock the OCR service."""
    with patch("src.api.diagnostics.ocr_service") as mock:
        # Configure the mock to return sample model information
        mock.get_models_info.return_value = [
            {
                "name": "typed_text_ocr",
                "version": "1.0.0",
                "type": OCRModelType.TYPED.value,
                "path": "/models/typed_text_ocr",
                "loaded_at": "2023-01-01T12:00:00Z",
                "parameters": {
                    "input_shape": [768, 768, 3],
                    "max_text_length": 512,
                    "confidence_threshold": 0.7
                }
            },
            {
                "name": "handwritten_text_ocr",
                "version": "1.0.0",
                "type": OCRModelType.HANDWRITTEN.value,
                "path": "/models/handwritten_text_ocr",
                "loaded_at": "2023-01-01T12:00:00Z",
                "parameters": {
                    "input_shape": [1024, 1024, 3],
                    "max_text_length": 512,
                    "confidence_threshold": 0.6
                }
            }
        ]
        mock.get_model_metrics.return_value = {
            "typed_text_ocr": {
                "accuracy": 0.98,
                "character_error_rate": 0.02,
                "word_error_rate": 0.05,
                "processing_time": 0.125,
                "confidence_score": 0.95
            },
            "handwritten_text_ocr": {
                "accuracy": 0.92,
                "character_error_rate": 0.08,
                "word_error_rate": 0.12,
                "processing_time": 0.250,
                "confidence_score": 0.85
            }
        }
        mock.get_model_usage_stats.return_value = {
            "typed_text_ocr": {
                "total_invocations": 1250,
                "successful_invocations": 1240,
                "failed_invocations": 10,
                "average_processing_time": 0.125,
                "total_documents_processed": 1250
            },
            "handwritten_text_ocr": {
                "total_invocations": 750,
                "successful_invocations": 735,
                "failed_invocations": 15,
                "average_processing_time": 0.250,
                "total_documents_processed": 750
            }
        }
        mock.reload_model.return_value = {
            "success": True,
            "message": "Model reloaded successfully",
            "models": [
                {
                    "name": "typed_text_ocr",
                    "version": "1.0.0",
                    "type": OCRModelType.TYPED.value,
                    "loaded_at": "2023-01-01T12:30:00Z"
                }
            ]
        }
        mock.reload_all_models.return_value = {
            "success": True,
            "message": "All models reloaded successfully",
            "models": [
                {
                    "name": "typed_text_ocr",
                    "version": "1.0.0",
                    "type": OCRModelType.TYPED.value,
                    "loaded_at": "2023-01-01T12:30:00Z"
                },
                {
                    "name": "handwritten_text_ocr",
                    "version": "1.0.0",
                    "type": OCRModelType.HANDWRITTEN.value,
                    "loaded_at": "2023-01-01T12:30:00Z"
                }
            ]
        }
        yield mock


# Mock the configuration modules
@pytest.fixture
def mock_config_modules():
    """Mock the configuration modules."""
    with patch("src.api.diagnostics.app_config") as app_config_mock, \
         patch("src.api.diagnostics.tensorflow_config") as tf_config_mock, \
         patch("src.api.diagnostics.logging_config") as logging_config_mock:
        
        # Configure the app config mock
        app_config_mock.get_sanitized_config.return_value = {
            "service_name": "ocr-service",
            "version": "1.0.0",
            "environment": "test",
            "max_processing_time_seconds": 5.0
        }
        
        # Configure the TensorFlow config mock
        tf_config_mock.get_sanitized_config.return_value = {
            "model_path": "/models",
            "confidence_threshold": 0.7,
            "use_gpu": True,
            "gpu_memory_limit": 4096
        }
        
        # Configure the logging config mock
        logging_config_mock.get_sanitized_config.return_value = {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "log_to_file": True,
            "log_file_path": "/var/log/ocr-service.log"
        }
        
        yield app_config_mock, tf_config_mock, logging_config_mock


# Tests for /diagnostics/logs endpoint

def test_get_logs_success(client, mock_logging_utils):
    """Test successful retrieval of logs."""
    response = client.get("/diagnostics/logs")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timestamp" in data
    assert "level" in data
    assert "hours" in data
    assert "count" in data
    assert "logs" in data
    
    # Verify default parameters
    assert data["level"] == "INFO"
    assert data["hours"] == 24
    assert len(data["logs"]) == 2
    
    # Verify log entries
    assert data["logs"][0]["message"] == "Sample log message 1"
    assert data["logs"][1]["level"] == "ERROR"
    
    # Verify the logging utils were called with correct parameters
    mock_logging_utils.get_log_level.assert_called_once_with("INFO")
    mock_logging_utils.get_log_entries.assert_called_once()
    call_args = mock_logging_utils.get_log_entries.call_args[1]
    assert call_args["level"] == 20  # INFO level
    assert call_args["limit"] == 100


def test_get_logs_with_filters(client, mock_logging_utils):
    """Test log retrieval with filters."""
    response = client.get("/diagnostics/logs?level=ERROR&hours=12&service=ocr-service&limit=50")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify filtered parameters
    assert data["level"] == "ERROR"
    assert data["hours"] == 12
    assert data["service"] == "ocr-service"
    
    # Verify the logging utils were called with correct parameters
    mock_logging_utils.get_log_level.assert_called_once_with("ERROR")
    mock_logging_utils.get_log_entries.assert_called_once()
    call_args = mock_logging_utils.get_log_entries.call_args[1]
    assert call_args["service"] == "ocr-service"
    assert call_args["limit"] == 50


def test_get_logs_invalid_level(client, mock_logging_utils):
    """Test log retrieval with invalid log level."""
    # Configure the mock to return None for invalid level
    mock_logging_utils.get_log_level.return_value = None
    
    response = client.get("/diagnostics/logs?level=INVALID")
    
    assert response.status_code == 400
    data = response.json()
    
    # Verify error message
    assert "Invalid log level" in data["detail"]
    assert "INVALID" in data["detail"]


def test_get_logs_error_handling(client, mock_logging_utils):
    """Test error handling in log retrieval."""
    # Configure the mock to raise an exception
    mock_logging_utils.get_log_entries.side_effect = Exception("Test error")
    
    response = client.get("/diagnostics/logs")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error message
    assert "Failed to retrieve logs" in data["detail"]
    assert "Test error" in data["detail"]


# Tests for /diagnostics/config endpoint

def test_get_config_success(client, mock_config_modules):
    """Test successful retrieval of configuration."""
    response = client.get("/diagnostics/config")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timestamp" in data
    assert "app_config" in data
    assert "tensorflow_config" in data
    assert "logging_config" in data
    assert "environment" in data
    
    # Verify configuration values
    assert data["app_config"]["service_name"] == "ocr-service"
    assert data["app_config"]["version"] == "1.0.0"
    assert data["tensorflow_config"]["confidence_threshold"] == 0.7
    assert data["logging_config"]["level"] == "INFO"
    
    # Verify environment information
    assert "environment" in data["environment"]
    assert "python_version" in data["environment"]
    assert "hostname" in data["environment"]
    assert "service_version" in data["environment"]


def test_get_config_error_handling(client, mock_config_modules):
    """Test error handling in configuration retrieval."""
    # Configure the mock to raise an exception
    app_config_mock, _, _ = mock_config_modules
    app_config_mock.get_sanitized_config.side_effect = Exception("Test error")
    
    response = client.get("/diagnostics/config")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error message
    assert "Failed to retrieve configuration" in data["detail"]
    assert "Test error" in data["detail"]


# Tests for /diagnostics/test endpoint

def test_run_diagnostics_basic(client, mock_tensorflow_utils):
    """Test running basic diagnostics."""
    response = client.get("/diagnostics/test")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timestamp" in data
    assert "test_type" in data
    assert "execution_time" in data
    assert "results" in data
    
    # Verify test type and results
    assert data["test_type"] == "basic"
    assert "system" in data["results"]
    assert "cpu" in data["results"]["system"]
    assert "memory" in data["results"]["system"]
    assert "disk" in data["results"]["system"]
    assert "python" in data["results"]["system"]
    
    # Verify TensorFlow utils were called
    mock_tensorflow_utils.check_cpu_info.assert_called_once()
    mock_tensorflow_utils.check_memory_info.assert_called_once()
    mock_tensorflow_utils.check_disk_info.assert_called_once()
    mock_tensorflow_utils.check_python_info.assert_called_once()


def test_run_diagnostics_gpu(client, mock_tensorflow_utils):
    """Test running GPU diagnostics."""
    response = client.get("/diagnostics/test?test_type=gpu")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify test type and results
    assert data["test_type"] == "gpu"
    assert "gpu" in data["results"]
    assert data["results"]["gpu"]["available"] == True
    assert len(data["results"]["gpu"]["devices"]) == 1
    assert data["results"]["gpu"]["devices"][0]["name"] == "NVIDIA GeForce RTX 3080"
    
    # Verify TensorFlow utils were called
    mock_tensorflow_utils.check_gpu_info.assert_called_once()


def test_run_diagnostics_models(client, mock_tensorflow_utils):
    """Test running model diagnostics."""
    response = client.get("/diagnostics/test?test_type=models")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify test type and results
    assert data["test_type"] == "models"
    assert "models" in data["results"]
    assert "loaded" in data["results"]["models"]
    assert "performance" in data["results"]["models"]
    
    # Verify loaded models
    assert len(data["results"]["models"]["loaded"]) == 2
    assert data["results"]["models"]["loaded"][0]["name"] == "typed_text_ocr"
    assert data["results"]["models"]["loaded"][1]["name"] == "handwritten_text_ocr"
    
    # Verify model performance
    assert "typed_text_ocr" in data["results"]["models"]["performance"]
    assert "handwritten_text_ocr" in data["results"]["models"]["performance"]
    assert data["results"]["models"]["performance"]["typed_text_ocr"]["accuracy"] == 0.98
    
    # Verify TensorFlow utils were called
    mock_tensorflow_utils.check_loaded_models.assert_called_once()
    mock_tensorflow_utils.check_model_performance.assert_called_once()


def test_run_diagnostics_full(client, mock_tensorflow_utils):
    """Test running full diagnostics."""
    response = client.get("/diagnostics/test?test_type=full")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify test type and results
    assert data["test_type"] == "full"
    assert "system" in data["results"]
    assert "gpu" in data["results"]
    assert "models" in data["results"]
    assert "connectivity" in data["results"]
    
    # Verify connectivity results
    assert "rabbitmq" in data["results"]["connectivity"]
    assert "s3" in data["results"]["connectivity"]
    assert data["results"]["connectivity"]["rabbitmq"]["connected"] == True
    assert data["results"]["connectivity"]["s3"]["connected"] == True
    
    # Verify all TensorFlow utils were called
    mock_tensorflow_utils.check_cpu_info.assert_called_once()
    mock_tensorflow_utils.check_memory_info.assert_called_once()
    mock_tensorflow_utils.check_disk_info.assert_called_once()
    mock_tensorflow_utils.check_python_info.assert_called_once()
    mock_tensorflow_utils.check_gpu_info.assert_called_once()
    mock_tensorflow_utils.check_loaded_models.assert_called_once()
    mock_tensorflow_utils.check_model_performance.assert_called_once()
    mock_tensorflow_utils.check_rabbitmq_connectivity.assert_called_once()
    mock_tensorflow_utils.check_s3_connectivity.assert_called_once()


def test_run_diagnostics_error_handling(client, mock_tensorflow_utils):
    """Test error handling in diagnostics."""
    # Configure the mock to raise an exception
    mock_tensorflow_utils.check_cpu_info.side_effect = Exception("Test error")
    
    response = client.get("/diagnostics/test")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error message
    assert "Failed to run diagnostics" in data["detail"]
    assert "Test error" in data["detail"]


# Tests for /diagnostics/models endpoint

def test_get_models_success(client, mock_ocr_service):
    """Test successful retrieval of model information."""
    response = client.get("/diagnostics/models")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timestamp" in data
    assert "models" in data
    assert "performance" in data
    assert "usage" in data
    
    # Verify models information
    assert len(data["models"]) == 2
    assert data["models"][0]["name"] == "typed_text_ocr"
    assert data["models"][1]["name"] == "handwritten_text_ocr"
    
    # Verify performance metrics
    assert "typed_text_ocr" in data["performance"]
    assert "handwritten_text_ocr" in data["performance"]
    assert data["performance"]["typed_text_ocr"]["accuracy"] == 0.98
    assert data["performance"]["handwritten_text_ocr"]["accuracy"] == 0.92
    
    # Verify usage statistics
    assert "typed_text_ocr" in data["usage"]
    assert "handwritten_text_ocr" in data["usage"]
    assert data["usage"]["typed_text_ocr"]["total_invocations"] == 1250
    assert data["usage"]["handwritten_text_ocr"]["total_invocations"] == 750
    
    # Verify OCR service methods were called
    mock_ocr_service.get_models_info.assert_called_once()
    mock_ocr_service.get_model_metrics.assert_called_once()
    mock_ocr_service.get_model_usage_stats.assert_called_once()


def test_get_models_error_handling(client, mock_ocr_service):
    """Test error handling in model information retrieval."""
    # Configure the mock to raise an exception
    mock_ocr_service.get_models_info.side_effect = Exception("Test error")
    
    response = client.get("/diagnostics/models")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error message
    assert "Failed to retrieve model information" in data["detail"]
    assert "Test error" in data["detail"]


# Tests for /diagnostics/models/reload endpoint

def test_reload_models_all(client, mock_ocr_service):
    """Test reloading all models."""
    response = client.post("/diagnostics/models/reload")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timestamp" in data
    assert "model_type" in data
    assert "success" in data
    assert "message" in data
    assert "models" in data
    
    # Verify reload results
    assert data["model_type"] == "all"
    assert data["success"] == True
    assert "All models reloaded successfully" in data["message"]
    assert len(data["models"]) == 2
    
    # Verify OCR service method was called
    mock_ocr_service.reload_all_models.assert_called_once()
    mock_ocr_service.reload_model.assert_not_called()


def test_reload_models_specific(client, mock_ocr_service):
    """Test reloading a specific model type."""
    response = client.post("/diagnostics/models/reload?model_type=TYPED")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify reload results
    assert data["model_type"] == "TYPED"
    assert data["success"] == True
    assert "Model reloaded successfully" in data["message"]
    assert len(data["models"]) == 1
    assert data["models"][0]["type"] == "TYPED"
    
    # Verify OCR service method was called with correct model type
    mock_ocr_service.reload_model.assert_called_once()
    mock_ocr_service.reload_all_models.assert_not_called()


def test_reload_models_error_handling(client, mock_ocr_service):
    """Test error handling in model reloading."""
    # Configure the mock to raise an exception
    mock_ocr_service.reload_all_models.side_effect = Exception("Test error")
    
    response = client.post("/diagnostics/models/reload")
    
    assert response.status_code == 500
    data = response.json()
    
    # Verify error message
    assert "Failed to reload models" in data["detail"]
    assert "Test error" in data["detail"]


# Tests for /diagnostics/health endpoint

def test_check_health_success(client):
    """Test successful health check."""
    response = client.get("/diagnostics/health")
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "timestamp" in data
    assert "status" in data
    assert "message" in data
    
    # Verify health status
    assert data["status"] == "healthy"
    assert "Diagnostics subsystem is functioning correctly" in data["message"]


def test_check_health_error_handling(client):
    """Test error handling in health check."""
    # Use a context manager to patch datetime.now to raise an exception
    with patch("src.api.diagnostics.datetime") as mock_datetime:
        mock_datetime.now.side_effect = Exception("Test error")
        
        response = client.get("/diagnostics/health")
        
        assert response.status_code == 500
        data = response.json()
        
        # Verify error message
        assert "Diagnostics health check failed" in data["detail"]
        assert "Test error" in data["detail"]


# Tests for authentication

def test_authentication_required(client):
    """Test that authentication is required for sensitive endpoints."""
    # Remove the autouse fixture for this test
    with patch("src.api.diagnostics.verify_admin_access", side_effect=Exception("Unauthorized")):        
        # Try to access a sensitive endpoint
        response = client.get("/diagnostics/logs")
        
        assert response.status_code == 500
        data = response.json()
        
        # Verify error message
        assert "Unauthorized" in data["detail"]