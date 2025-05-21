#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the health check endpoints in the OCR Service API.

This module contains tests for the liveness and readiness probe endpoints
that Kubernetes uses to determine if the service is running correctly and
ready to accept traffic. It verifies that the endpoints correctly check
dependencies (RabbitMQ, S3, GPU) and return appropriate status codes.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the health router to test
from src.api.health import health_router
from src.utils import tensorflow_utils


# Create a test FastAPI app with the health router
@pytest.fixture
def test_app():
    """Create a test FastAPI app with the health router."""
    app = FastAPI()
    app.include_router(health_router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test app."""
    return TestClient(test_app)


# Tests for the liveness endpoint
class TestLivenessEndpoint:
    """Tests for the /health/liveness endpoint."""

    def test_liveness_success(self, test_client):
        """Test that the liveness endpoint returns 200 OK when the service is running."""
        # Make a request to the liveness endpoint
        response = test_client.get("/liveness")
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data
        assert "timestamp" in data

    def test_liveness_error_handling(self, test_client):
        """Test that the liveness endpoint handles errors appropriately."""
        # Mock an exception during the liveness check
        with patch("src.api.health.logging_utils.get_current_timestamp", side_effect=Exception("Test error")):
            response = test_client.get("/liveness")
            
            # Check the response
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
            assert "message" in data
            assert "details" in data
            assert "timestamp" in data


# Tests for the readiness endpoint
class TestReadinessEndpoint:
    """Tests for the /health/readiness endpoint."""

    def test_readiness_all_healthy(self, test_client):
        """Test that the readiness endpoint returns 200 OK when all dependencies are healthy."""
        # Mock all dependency checks to return healthy status
        with patch("src.api.health.check_rabbitmq_health", return_value={"status": "ok"}):
            with patch("src.api.health.check_s3_health", return_value={"status": "ok"}):
                with patch("src.api.health.check_gpu_health", return_value={"status": "ok"}):
                    response = test_client.get("/readiness")
                    
                    # Check the response
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "ok"
                    assert "dependencies" in data
                    assert "rabbitmq" in data["dependencies"]
                    assert "s3" in data["dependencies"]
                    assert "gpu" in data["dependencies"]
                    assert data["dependencies"]["rabbitmq"]["status"] == "ok"
                    assert data["dependencies"]["s3"]["status"] == "ok"
                    assert data["dependencies"]["gpu"]["status"] == "ok"

    def test_readiness_rabbitmq_unhealthy(self, test_client):
        """Test that the readiness endpoint returns 503 when RabbitMQ is unhealthy."""
        # Mock RabbitMQ check to return unhealthy status
        with patch("src.api.health.check_rabbitmq_health", return_value={"status": "error", "message": "RabbitMQ connection failed"}):
            with patch("src.api.health.check_s3_health", return_value={"status": "ok"}):
                with patch("src.api.health.check_gpu_health", return_value={"status": "ok"}):
                    response = test_client.get("/readiness")
                    
                    # Check the response
                    assert response.status_code == 503
                    data = response.json()
                    assert data["status"] == "degraded"
                    assert data["dependencies"]["rabbitmq"]["status"] == "error"
                    assert data["dependencies"]["s3"]["status"] == "ok"
                    assert data["dependencies"]["gpu"]["status"] == "ok"

    def test_readiness_s3_unhealthy(self, test_client):
        """Test that the readiness endpoint returns 503 when S3 is unhealthy."""
        # Mock S3 check to return unhealthy status
        with patch("src.api.health.check_rabbitmq_health", return_value={"status": "ok"}):
            with patch("src.api.health.check_s3_health", return_value={"status": "error", "message": "S3 connection failed"}):
                with patch("src.api.health.check_gpu_health", return_value={"status": "ok"}):
                    response = test_client.get("/readiness")
                    
                    # Check the response
                    assert response.status_code == 503
                    data = response.json()
                    assert data["status"] == "degraded"
                    assert data["dependencies"]["rabbitmq"]["status"] == "ok"
                    assert data["dependencies"]["s3"]["status"] == "error"
                    assert data["dependencies"]["gpu"]["status"] == "ok"

    def test_readiness_gpu_unhealthy(self, test_client):
        """Test that the readiness endpoint returns 503 when GPU is unhealthy."""
        # Mock GPU check to return unhealthy status
        with patch("src.api.health.check_rabbitmq_health", return_value={"status": "ok"}):
            with patch("src.api.health.check_s3_health", return_value={"status": "ok"}):
                with patch("src.api.health.check_gpu_health", return_value={"status": "error", "message": "No GPU devices available"}):
                    response = test_client.get("/readiness")
                    
                    # Check the response
                    assert response.status_code == 503
                    data = response.json()
                    assert data["status"] == "degraded"
                    assert data["dependencies"]["rabbitmq"]["status"] == "ok"
                    assert data["dependencies"]["s3"]["status"] == "ok"
                    assert data["dependencies"]["gpu"]["status"] == "error"

    def test_readiness_all_unhealthy(self, test_client):
        """Test that the readiness endpoint returns 503 when all dependencies are unhealthy."""
        # Mock all dependency checks to return unhealthy status
        with patch("src.api.health.check_rabbitmq_health", return_value={"status": "error", "message": "RabbitMQ connection failed"}):
            with patch("src.api.health.check_s3_health", return_value={"status": "error", "message": "S3 connection failed"}):
                with patch("src.api.health.check_gpu_health", return_value={"status": "error", "message": "No GPU devices available"}):
                    response = test_client.get("/readiness")
                    
                    # Check the response
                    assert response.status_code == 503
                    data = response.json()
                    assert data["status"] == "degraded"
                    assert data["dependencies"]["rabbitmq"]["status"] == "error"
                    assert data["dependencies"]["s3"]["status"] == "error"
                    assert data["dependencies"]["gpu"]["status"] == "error"

    def test_readiness_error_handling(self, test_client):
        """Test that the readiness endpoint handles errors appropriately."""
        # Mock an exception during the readiness check
        with patch("src.api.health.check_rabbitmq_health", side_effect=Exception("Test error")):
            response = test_client.get("/readiness")
            
            # Check the response
            assert response.status_code == 500
            data = response.json()
            assert data["status"] == "error"
            assert "message" in data
            assert "details" in data
            assert "timestamp" in data


# Tests for the individual health check functions
class TestHealthCheckFunctions:
    """Tests for the individual health check functions."""

    @pytest.mark.asyncio
    async def test_check_rabbitmq_health_success(self, mock_queue_service):
        """Test that check_rabbitmq_health returns healthy status when RabbitMQ is available."""
        # Mock the queue service functions
        with patch("src.api.health.queue_service.check_connection", return_value=True):
            with patch("src.api.health.queue_service.check_exchange_exists", return_value=True):
                with patch("src.api.health.queue_service.check_queue_exists", return_value=True):
                    # Import the function here to ensure mocks are applied
                    from src.api.health import check_rabbitmq_health
                    
                    # Call the function
                    result = await check_rabbitmq_health()
                    
                    # Check the result
                    assert result["status"] == "ok"
                    assert "details" in result
                    assert result["details"]["connection"] == "connected"
                    assert "exchange" in result["details"]
                    assert "queue" in result["details"]

    @pytest.mark.asyncio
    async def test_check_rabbitmq_health_connection_failure(self):
        """Test that check_rabbitmq_health returns unhealthy status when RabbitMQ connection fails."""
        # Mock the queue service functions
        with patch("src.api.health.queue_service.check_connection", return_value=False):
            with patch("src.api.health.queue_service.check_exchange_exists", return_value=False):
                with patch("src.api.health.queue_service.check_queue_exists", return_value=False):
                    # Import the function here to ensure mocks are applied
                    from src.api.health import check_rabbitmq_health
                    
                    # Call the function
                    result = await check_rabbitmq_health()
                    
                    # Check the result
                    assert result["status"] == "error"
                    assert "details" in result
                    assert result["details"]["connection"] == "disconnected"
                    assert result["details"]["exchange"] == "unavailable"
                    assert result["details"]["queue"] == "unavailable"

    @pytest.mark.asyncio
    async def test_check_rabbitmq_health_exception(self):
        """Test that check_rabbitmq_health handles exceptions appropriately."""
        # Mock the queue service functions to raise an exception
        with patch("src.api.health.queue_service.check_connection", side_effect=Exception("Test error")):
            # Import the function here to ensure mocks are applied
            from src.api.health import check_rabbitmq_health
            
            # Call the function
            result = await check_rabbitmq_health()
            
            # Check the result
            assert result["status"] == "error"
            assert "details" in result
            assert "error" in result["details"]
            assert "message" in result

    @pytest.mark.asyncio
    async def test_check_s3_health_success(self):
        """Test that check_s3_health returns healthy status when S3 is available."""
        # Mock the storage service functions
        with patch("src.api.health.storage_service.check_connection", return_value=True):
            with patch("src.api.health.storage_service.check_bucket_exists", return_value=True):
                # Import the function here to ensure mocks are applied
                from src.api.health import check_s3_health
                
                # Call the function
                result = await check_s3_health()
                
                # Check the result
                assert result["status"] == "ok"
                assert "details" in result
                assert result["details"]["connection"] == "connected"
                assert "bucket" in result["details"]
                assert "encryption" in result["details"]

    @pytest.mark.asyncio
    async def test_check_s3_health_connection_failure(self):
        """Test that check_s3_health returns unhealthy status when S3 connection fails."""
        # Mock the storage service functions
        with patch("src.api.health.storage_service.check_connection", return_value=False):
            with patch("src.api.health.storage_service.check_bucket_exists", return_value=False):
                # Import the function here to ensure mocks are applied
                from src.api.health import check_s3_health
                
                # Call the function
                result = await check_s3_health()
                
                # Check the result
                assert result["status"] == "error"
                assert "details" in result
                assert result["details"]["connection"] == "disconnected"
                assert result["details"]["bucket"] == "inaccessible"

    @pytest.mark.asyncio
    async def test_check_s3_health_exception(self):
        """Test that check_s3_health handles exceptions appropriately."""
        # Mock the storage service functions to raise an exception
        with patch("src.api.health.storage_service.check_connection", side_effect=Exception("Test error")):
            # Import the function here to ensure mocks are applied
            from src.api.health import check_s3_health
            
            # Call the function
            result = await check_s3_health()
            
            # Check the result
            assert result["status"] == "error"
            assert "details" in result
            assert "error" in result["details"]
            assert "message" in result

    def test_check_gpu_health_success(self):
        """Test that check_gpu_health returns healthy status when GPU is available."""
        # Mock the tensorflow_utils functions
        with patch("src.api.health.tensorflow_utils.get_available_gpus", return_value=['/device:GPU:0']):
            with patch("src.api.health.tensorflow_utils.get_gpu_memory", return_value=10240):  # 10GB
                with patch("src.api.health.tensorflow_utils.check_gpu_tensorflow_compatibility", return_value=True):
                    with patch("src.api.health.tensorflow_utils.get_cuda_version", return_value="11.2"):
                        # Import the function here to ensure mocks are applied
                        from src.api.health import check_gpu_health
                        
                        # Call the function
                        result = check_gpu_health()
                        
                        # Check the result
                        assert result["status"] == "ok"
                        assert "details" in result
                        assert result["details"]["gpu_count"] == 1
                        assert result["details"]["available_memory_gb"] == 10
                        assert result["details"]["tensorflow_gpu_enabled"] == True
                        assert result["details"]["cuda_version"] == "11.2"

    def test_check_gpu_health_no_gpu(self):
        """Test that check_gpu_health returns unhealthy status when no GPU is available."""
        # Mock the tensorflow_utils functions
        with patch("src.api.health.tensorflow_utils.get_available_gpus", return_value=[]):
            # Import the function here to ensure mocks are applied
            from src.api.health import check_gpu_health
            
            # Call the function
            result = check_gpu_health()
            
            # Check the result
            assert result["status"] == "error"
            assert "details" in result
            assert result["details"]["gpu_count"] == 0
            assert "message" in result

    def test_check_gpu_health_insufficient_memory(self):
        """Test that check_gpu_health returns unhealthy status when GPU memory is insufficient."""
        # Mock the tensorflow_utils functions
        with patch("src.api.health.tensorflow_utils.get_available_gpus", return_value=['/device:GPU:0']):
            with patch("src.api.health.tensorflow_utils.get_gpu_memory", return_value=4096):  # 4GB (less than required 8GB)
                # Import the function here to ensure mocks are applied
                from src.api.health import check_gpu_health
                
                # Call the function
                result = check_gpu_health()
                
                # Check the result
                assert result["status"] == "error"
                assert "details" in result
                assert result["details"]["gpu_count"] == 1
                assert result["details"]["available_memory_gb"] == 4
                assert result["details"]["required_memory_gb"] == 8
                assert "message" in result

    def test_check_gpu_health_tensorflow_incompatible(self):
        """Test that check_gpu_health returns unhealthy status when TensorFlow cannot use GPU."""
        # Mock the tensorflow_utils functions
        with patch("src.api.health.tensorflow_utils.get_available_gpus", return_value=['/device:GPU:0']):
            with patch("src.api.health.tensorflow_utils.get_gpu_memory", return_value=10240):  # 10GB
                with patch("src.api.health.tensorflow_utils.check_gpu_tensorflow_compatibility", return_value=False):
                    # Import the function here to ensure mocks are applied
                    from src.api.health import check_gpu_health
                    
                    # Call the function
                    result = check_gpu_health()
                    
                    # Check the result
                    assert result["status"] == "error"
                    assert "details" in result
                    assert result["details"]["gpu_count"] == 1
                    assert result["details"]["available_memory_gb"] == 10
                    assert result["details"]["tensorflow_gpu_enabled"] == False
                    assert "message" in result

    def test_check_gpu_health_exception(self):
        """Test that check_gpu_health handles exceptions appropriately."""
        # Mock the tensorflow_utils functions to raise an exception
        with patch("src.api.health.tensorflow_utils.get_available_gpus", side_effect=Exception("Test error")):
            # Import the function here to ensure mocks are applied
            from src.api.health import check_gpu_health
            
            # Call the function
            result = check_gpu_health()
            
            # Check the result
            assert result["status"] == "error"
            assert "details" in result
            assert "error" in result["details"]
            assert "message" in result