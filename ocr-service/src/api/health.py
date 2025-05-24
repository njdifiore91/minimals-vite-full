"""Health check endpoints for Kubernetes probes in the OCR Service.

This module provides liveness and readiness probe endpoints that Kubernetes uses to determine
if the service is running correctly and ready to accept traffic. The liveness probe verifies
that the application is running, while the readiness probe checks that all dependencies
(RabbitMQ, S3, GPU) are available.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, status, Response
import tensorflow as tf

from services import queue_service, storage_service
from config import app_config, tensorflow_config
from utils import error_utils, logging_utils

# Set up logger
logger = logging.getLogger(__name__)

# Create router
health_router = APIRouter(tags=["health"])


async def check_rabbitmq_connection() -> Dict[str, Any]:
    """Check if RabbitMQ connection is available.
    
    Returns:
        Dict[str, Any]: Status of RabbitMQ connection with details
    """
    try:
        # Attempt to check RabbitMQ connection
        is_connected = await queue_service.check_connection()
        return {
            "status": "up" if is_connected else "down",
            "details": {
                "connected": is_connected,
                "exchange": app_config.RABBITMQ_EXCHANGE,
                "queue": app_config.RABBITMQ_QUEUE
            }
        }
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"RabbitMQ health check failed: {error}")
        return {
            "status": "down",
            "details": {
                "connected": False,
                "error": str(error),
                "exchange": app_config.RABBITMQ_EXCHANGE,
                "queue": app_config.RABBITMQ_QUEUE
            }
        }


async def check_s3_connection() -> Dict[str, Any]:
    """Check if S3 storage connection is available.
    
    Returns:
        Dict[str, Any]: Status of S3 connection with details
    """
    try:
        # Attempt to check S3 connection
        is_connected = await storage_service.check_connection()
        return {
            "status": "up" if is_connected else "down",
            "details": {
                "connected": is_connected,
                "bucket": app_config.S3_BUCKET,
                "endpoint": app_config.S3_ENDPOINT
            }
        }
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"S3 health check failed: {error}")
        return {
            "status": "down",
            "details": {
                "connected": False,
                "error": str(error),
                "bucket": app_config.S3_BUCKET,
                "endpoint": app_config.S3_ENDPOINT
            }
        }


def check_gpu_availability() -> Dict[str, Any]:
    """Check if GPU is available for TensorFlow processing.
    
    Returns:
        Dict[str, Any]: Status of GPU availability with details
    """
    try:
        # Check if TensorFlow can access GPU
        gpu_devices = tf.config.list_physical_devices('GPU')
        gpu_available = len(gpu_devices) > 0
        
        # Get GPU details if available
        gpu_details = []
        if gpu_available:
            for device in gpu_devices:
                # Get device details
                device_details = tf.config.experimental.get_device_details(device)
                gpu_details.append({
                    "name": device.name,
                    "device_type": device.device_type,
                    "memory": device_details.get("memory_limit", "unknown"),
                    "compute_capability": device_details.get("compute_capability", "unknown")
                })
        
        # Check if GPU meets minimum requirements
        min_vram_required = tensorflow_config.MIN_GPU_MEMORY_MB
        meets_requirements = False
        
        if gpu_available and gpu_details:
            # Check if any GPU has sufficient memory
            for gpu in gpu_details:
                if gpu.get("memory", 0) >= min_vram_required * 1024 * 1024:  # Convert MB to bytes
                    meets_requirements = True
                    break
        
        return {
            "status": "up" if (gpu_available and meets_requirements) else "down",
            "details": {
                "gpu_available": gpu_available,
                "gpu_count": len(gpu_devices),
                "gpu_devices": gpu_details,
                "meets_requirements": meets_requirements,
                "min_vram_required_mb": min_vram_required
            }
        }
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"GPU health check failed: {error}")
        return {
            "status": "down",
            "details": {
                "gpu_available": False,
                "error": str(error),
                "min_vram_required_mb": tensorflow_config.MIN_GPU_MEMORY_MB
            }
        }


@health_router.get("/health/liveness", summary="Liveness probe for Kubernetes")
async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is running and responsive.
    It does not check dependencies, only that the service itself is running.
    
    Returns:
        Dict[str, Any]: Health status with service information
    """
    return {
        "status": "up",
        "service": app_config.SERVICE_NAME,
        "version": app_config.SERVICE_VERSION,
        "timestamp": logging_utils.get_current_timestamp()
    }


@health_router.get("/health/readiness", summary="Readiness probe for Kubernetes")
async def readiness_probe(response: Response) -> Dict[str, Any]:
    """Readiness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is ready to accept traffic by verifying
    that all dependencies (RabbitMQ, S3, GPU) are available and properly configured.
    
    Args:
        response (Response): FastAPI response object for setting status code
        
    Returns:
        Dict[str, Any]: Health status with dependency information
    """
    # Check all dependencies
    rabbitmq_status = await check_rabbitmq_connection()
    s3_status = await check_s3_connection()
    gpu_status = check_gpu_availability()
    
    # Determine overall status
    all_healthy = (
        rabbitmq_status["status"] == "up" and
        s3_status["status"] == "up" and
        gpu_status["status"] == "up"
    )
    
    # Set response status code based on health
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    # Build response
    result = {
        "status": "up" if all_healthy else "down",
        "service": app_config.SERVICE_NAME,
        "version": app_config.SERVICE_VERSION,
        "timestamp": logging_utils.get_current_timestamp(),
        "dependencies": {
            "rabbitmq": rabbitmq_status,
            "s3": s3_status,
            "gpu": gpu_status
        }
    }
    
    # Log health check results
    log_level = logging.INFO if all_healthy else logging.WARNING
    logger.log(log_level, f"Health check result: {result['status']}")
    
    return result