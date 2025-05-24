"""Tests for the health check endpoints in the OCR Service.

This module contains tests for the health check endpoints used by Kubernetes
to determine if the service is running correctly and ready to accept traffic.
It tests both the liveness and readiness probe endpoints, as well as the
dependency checks for RabbitMQ, S3, and GPU availability.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

# Import the health module to access the functions directly for mocking
from src.api.health import check_rabbitmq_connection, check_s3_connection, check_gpu_availability
from src.config import app_config, tensorflow_config


@pytest.mark.asyncio
async def test_liveness_probe(client):
    """Test the liveness probe endpoint.
    
    This test verifies that the liveness probe endpoint correctly reports
    that the service is running.
    
    Args:
        client: FastAPI TestClient fixture
    """
    # Make a request to the liveness probe endpoint
    response = client.get("/health/liveness")
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_readiness_probe_all_healthy(client, mock_rabbitmq, mock_s3, mock_gpu_available):
    """Test the readiness probe endpoint when all dependencies are healthy.
    
    This test verifies that the readiness probe endpoint correctly reports
    that the service is ready to accept traffic when all dependencies
    (RabbitMQ, S3, GPU) are available.
    
    Args:
        client: FastAPI TestClient fixture
        mock_rabbitmq: Mock RabbitMQ connection fixture
        mock_s3: Mock S3 storage fixture
        mock_gpu_available: Mock GPU availability fixture
    """
    # Configure mocks to return healthy status
    mock_rabbitmq.channel.return_value.queue_declare.return_value = True
    mock_s3.head_bucket.return_value = {"ResponseMetadata": {"HTTPStatusCode": 200}}
    
    # Make a request to the readiness probe endpoint
    response = client.get("/health/readiness")
    
    # Verify the response
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "up"
    assert "service" in data
    assert "version" in data
    assert "timestamp" in data
    
    # Verify dependency statuses
    dependencies = data["dependencies"]
    assert dependencies["rabbitmq"]["status"] == "up"
    assert dependencies["s3"]["status"] == "up"
    assert dependencies["gpu"]["status"] == "up"


@pytest.mark.asyncio
async def test_readiness_probe_rabbitmq_unhealthy(client, mock_s3, mock_gpu_available):
    """Test the readiness probe endpoint when RabbitMQ is unhealthy.
    
    This test verifies that the readiness probe endpoint correctly reports
    that the service is not ready to accept traffic when RabbitMQ is unavailable.
    
    Args:
        client: FastAPI TestClient fixture
        mock_s3: Mock S3 storage fixture
        mock_gpu_available: Mock GPU availability fixture
    """
    # Mock the check_rabbitmq_connection function to return unhealthy status
    async def mock_check_rabbitmq_unhealthy():
        return {
            "status": "down",
            "details": {
                "connected": False,
                "error": "Connection refused",
                "exchange": app_config.RABBITMQ_EXCHANGE,
                "queue": app_config.RABBITMQ_QUEUE
            }
        }
    
    # Apply the patch
    with patch("src.api.health.check_rabbitmq_connection", side_effect=mock_check_rabbitmq_unhealthy):
        # Make a request to the readiness probe endpoint
        response = client.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["status"] == "down"
        
        # Verify dependency statuses
        dependencies = data["dependencies"]
        assert dependencies["rabbitmq"]["status"] == "down"
        assert dependencies["s3"]["status"] == "up"
        assert dependencies["gpu"]["status"] == "up"


@pytest.mark.asyncio
async def test_readiness_probe_s3_unhealthy(client, mock_rabbitmq, mock_gpu_available):
    """Test the readiness probe endpoint when S3 is unhealthy.
    
    This test verifies that the readiness probe endpoint correctly reports
    that the service is not ready to accept traffic when S3 is unavailable.
    
    Args:
        client: FastAPI TestClient fixture
        mock_rabbitmq: Mock RabbitMQ connection fixture
        mock_gpu_available: Mock GPU availability fixture
    """
    # Mock the check_s3_connection function to return unhealthy status
    async def mock_check_s3_unhealthy():
        return {
            "status": "down",
            "details": {
                "connected": False,
                "error": "Connection refused",
                "bucket": app_config.S3_BUCKET,
                "endpoint": app_config.S3_ENDPOINT
            }
        }
    
    # Apply the patch
    with patch("src.api.health.check_s3_connection", side_effect=mock_check_s3_unhealthy):
        # Make a request to the readiness probe endpoint
        response = client.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["status"] == "down"
        
        # Verify dependency statuses
        dependencies = data["dependencies"]
        assert dependencies["rabbitmq"]["status"] == "up"
        assert dependencies["s3"]["status"] == "down"
        assert dependencies["gpu"]["status"] == "up"


@pytest.mark.asyncio
async def test_readiness_probe_gpu_unhealthy(client, mock_rabbitmq, mock_s3):
    """Test the readiness probe endpoint when GPU is unhealthy.
    
    This test verifies that the readiness probe endpoint correctly reports
    that the service is not ready to accept traffic when GPU is unavailable.
    
    Args:
        client: FastAPI TestClient fixture
        mock_rabbitmq: Mock RabbitMQ connection fixture
        mock_s3: Mock S3 storage fixture
    """
    # Mock the check_gpu_availability function to return unhealthy status
    def mock_check_gpu_unhealthy():
        return {
            "status": "down",
            "details": {
                "gpu_available": False,
                "error": "No GPU devices found",
                "min_vram_required_mb": tensorflow_config.MIN_GPU_MEMORY_MB
            }
        }
    
    # Apply the patch
    with patch("src.api.health.check_gpu_availability", side_effect=mock_check_gpu_unhealthy):
        # Make a request to the readiness probe endpoint
        response = client.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["status"] == "down"
        
        # Verify dependency statuses
        dependencies = data["dependencies"]
        assert dependencies["rabbitmq"]["status"] == "up"
        assert dependencies["s3"]["status"] == "up"
        assert dependencies["gpu"]["status"] == "down"


@pytest.mark.asyncio
async def test_readiness_probe_all_unhealthy(client):
    """Test the readiness probe endpoint when all dependencies are unhealthy.
    
    This test verifies that the readiness probe endpoint correctly reports
    that the service is not ready to accept traffic when all dependencies
    (RabbitMQ, S3, GPU) are unavailable.
    
    Args:
        client: FastAPI TestClient fixture
    """
    # Mock all dependency check functions to return unhealthy status
    async def mock_check_rabbitmq_unhealthy():
        return {
            "status": "down",
            "details": {
                "connected": False,
                "error": "Connection refused",
                "exchange": app_config.RABBITMQ_EXCHANGE,
                "queue": app_config.RABBITMQ_QUEUE
            }
        }
    
    async def mock_check_s3_unhealthy():
        return {
            "status": "down",
            "details": {
                "connected": False,
                "error": "Connection refused",
                "bucket": app_config.S3_BUCKET,
                "endpoint": app_config.S3_ENDPOINT
            }
        }
    
    def mock_check_gpu_unhealthy():
        return {
            "status": "down",
            "details": {
                "gpu_available": False,
                "error": "No GPU devices found",
                "min_vram_required_mb": tensorflow_config.MIN_GPU_MEMORY_MB
            }
        }
    
    # Apply the patches
    with patch("src.api.health.check_rabbitmq_connection", side_effect=mock_check_rabbitmq_unhealthy), \
         patch("src.api.health.check_s3_connection", side_effect=mock_check_s3_unhealthy), \
         patch("src.api.health.check_gpu_availability", side_effect=mock_check_gpu_unhealthy):
        # Make a request to the readiness probe endpoint
        response = client.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == 503  # Service Unavailable
        data = response.json()
        assert data["status"] == "down"
        
        # Verify dependency statuses
        dependencies = data["dependencies"]
        assert dependencies["rabbitmq"]["status"] == "down"
        assert dependencies["s3"]["status"] == "down"
        assert dependencies["gpu"]["status"] == "down"


@pytest.mark.asyncio
async def test_rabbitmq_connection_check_exception():
    """Test the RabbitMQ connection check function when an exception occurs.
    
    This test verifies that the RabbitMQ connection check function correctly
    handles exceptions and returns an appropriate error response.
    """
    # Mock the queue_service.check_connection function to raise an exception
    with patch("src.services.queue_service.check_connection", side_effect=Exception("Test exception")):
        # Call the function directly
        result = await check_rabbitmq_connection()
        
        # Verify the result
        assert result["status"] == "down"
        assert result["details"]["connected"] == False
        assert "error" in result["details"]
        assert "Test exception" in result["details"]["error"]


@pytest.mark.asyncio
async def test_s3_connection_check_exception():
    """Test the S3 connection check function when an exception occurs.
    
    This test verifies that the S3 connection check function correctly
    handles exceptions and returns an appropriate error response.
    """
    # Mock the storage_service.check_connection function to raise an exception
    with patch("src.services.storage_service.check_connection", side_effect=Exception("Test exception")):
        # Call the function directly
        result = await check_s3_connection()
        
        # Verify the result
        assert result["status"] == "down"
        assert result["details"]["connected"] == False
        assert "error" in result["details"]
        assert "Test exception" in result["details"]["error"]


def test_gpu_availability_check_exception():
    """Test the GPU availability check function when an exception occurs.
    
    This test verifies that the GPU availability check function correctly
    handles exceptions and returns an appropriate error response.
    """
    # Mock the tf.config.list_physical_devices function to raise an exception
    with patch("tensorflow.config.list_physical_devices", side_effect=Exception("Test exception")):
        # Call the function directly
        result = check_gpu_availability()
        
        # Verify the result
        assert result["status"] == "down"
        assert result["details"]["gpu_available"] == False
        assert "error" in result["details"]
        assert "Test exception" in result["details"]["error"]


@pytest.mark.asyncio
async def test_gpu_availability_insufficient_memory():
    """Test the GPU availability check function when GPU memory is insufficient.
    
    This test verifies that the GPU availability check function correctly
    reports that the GPU is unavailable when it has insufficient memory.
    """
    # Mock the tf.config.list_physical_devices function to return a GPU device
    mock_device = MagicMock()
    mock_device.name = "/device:GPU:0"
    mock_device.device_type = "GPU"
    
    # Mock the tf.config.experimental.get_device_details function to return insufficient memory
    mock_device_details = {
        "memory_limit": 1024 * 1024 * 1024,  # 1 GB (less than required)
        "compute_capability": "7.5"
    }
    
    with patch("tensorflow.config.list_physical_devices", return_value=[mock_device]), \
         patch("tensorflow.config.experimental.get_device_details", return_value=mock_device_details), \
         patch("src.config.tensorflow_config.MIN_GPU_MEMORY_MB", 8192):  # 8 GB required
        # Call the function directly
        result = check_gpu_availability()
        
        # Verify the result
        assert result["status"] == "down"
        assert result["details"]["gpu_available"] == True
        assert result["details"]["meets_requirements"] == False
        assert result["details"]["min_vram_required_mb"] == 8192