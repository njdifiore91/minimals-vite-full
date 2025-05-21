from fastapi import APIRouter, status, Response
import tensorflow as tf
import logging
from typing import Dict, Any, List, Optional

from ..services import queue_service, storage_service
from ..utils import error_utils, logging_utils, tensorflow_utils
from ..config import app_config, rabbitmq_config, s3_config

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create a FastAPI router for health check endpoints
health_router = APIRouter(tags=["health"])


@health_router.get("/liveness", summary="Kubernetes liveness probe endpoint")
async def liveness_check(response: Response) -> Dict[str, Any]:
    """
    Liveness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is running correctly.
    It returns a 200 OK status if the application is alive.
    
    Returns:
        Dict[str, Any]: A JSON response with the health status
    """
    try:
        # Log the liveness check
        logging_utils.log_info(logger, "Liveness check initiated", {"endpoint": "/health/liveness"})
        
        # Basic check - if we can execute this code, the application is alive
        return {
            "status": "ok",
            "service": app_config.SERVICE_NAME,
            "version": app_config.SERVICE_VERSION,
            "timestamp": logging_utils.get_current_timestamp()
        }
    except Exception as e:
        # Log the error
        logging_utils.log_error(
            logger, 
            "Liveness check failed", 
            {"error": str(e), "endpoint": "/health/liveness"}
        )
        
        # Return a 500 error
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": "error",
            "message": "Liveness check failed",
            "details": {"error": str(e)},
            "timestamp": logging_utils.get_current_timestamp()
        }


@health_router.get("/readiness", summary="Kubernetes readiness probe endpoint")
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Readiness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is ready to accept traffic by verifying
    that all dependencies (RabbitMQ, S3, GPU) are available and functioning correctly.
    
    Args:
        response (Response): FastAPI response object for setting status code
    
    Returns:
        Dict[str, Any]: A JSON response with the detailed health status of all dependencies
    """
    # Initialize health status
    health_status = {
        "status": "ok",
        "service": app_config.SERVICE_NAME,
        "version": app_config.SERVICE_VERSION,
        "timestamp": logging_utils.get_current_timestamp(),
        "dependencies": {}
    }
    
    # Track overall health status
    is_healthy = True
    
    try:
        # Log the readiness check
        logging_utils.log_info(logger, "Readiness check initiated", {"endpoint": "/health/readiness"})
        
        # Check RabbitMQ connection
        rabbitmq_status = await check_rabbitmq_health()
        health_status["dependencies"]["rabbitmq"] = rabbitmq_status
        is_healthy = is_healthy and rabbitmq_status["status"] == "ok"
        
        # Check S3 connection
        s3_status = await check_s3_health()
        health_status["dependencies"]["s3"] = s3_status
        is_healthy = is_healthy and s3_status["status"] == "ok"
        
        # Check GPU availability
        gpu_status = check_gpu_health()
        health_status["dependencies"]["gpu"] = gpu_status
        is_healthy = is_healthy and gpu_status["status"] == "ok"
        
        # Update overall status
        if not is_healthy:
            health_status["status"] = "degraded"
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        
        return health_status
    except Exception as e:
        # Log the error
        logging_utils.log_error(
            logger, 
            "Readiness check failed", 
            {"error": str(e), "endpoint": "/health/readiness"}
        )
        
        # Return a 500 error
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "status": "error",
            "message": "Readiness check failed",
            "details": {"error": str(e)},
            "timestamp": logging_utils.get_current_timestamp()
        }


async def check_rabbitmq_health() -> Dict[str, Any]:
    """
    Check the health of the RabbitMQ connection.
    
    This function attempts to connect to RabbitMQ and verify that the
    required exchanges and queues are available.
    
    Returns:
        Dict[str, Any]: A dictionary containing the health status of RabbitMQ
    """
    try:
        # Attempt to connect to RabbitMQ and check connection
        connection_status = await queue_service.check_connection()
        
        # Check if required exchanges and queues exist
        exchange_name = rabbitmq_config.EXCHANGE_NAME
        queue_name = rabbitmq_config.QUEUE_NAME
        
        exchange_exists = await queue_service.check_exchange_exists(exchange_name)
        queue_exists = await queue_service.check_queue_exists(queue_name)
        
        if connection_status and exchange_exists and queue_exists:
            return {
                "status": "ok",
                "details": {
                    "connection": "connected",
                    "exchange": exchange_name,
                    "queue": queue_name
                }
            }
        else:
            # Determine what's missing
            details = {
                "connection": "connected" if connection_status else "disconnected",
                "exchange": "available" if exchange_exists else "unavailable",
                "queue": "available" if queue_exists else "unavailable"
            }
            
            return {
                "status": "error",
                "details": details,
                "message": "RabbitMQ dependency check failed"
            }
    except Exception as e:
        # Log the error
        logging_utils.log_error(
            logger, 
            "RabbitMQ health check failed", 
            {"error": str(e)}
        )
        
        return {
            "status": "error",
            "details": {"error": str(e)},
            "message": "RabbitMQ connection failed"
        }


async def check_s3_health() -> Dict[str, Any]:
    """
    Check the health of the S3 storage connection.
    
    This function attempts to connect to the S3-compatible storage and verify
    that the required buckets are accessible.
    
    Returns:
        Dict[str, Any]: A dictionary containing the health status of S3 storage
    """
    try:
        # Attempt to connect to S3 and check connection
        connection_status = await storage_service.check_connection()
        
        # Check if required bucket exists and is accessible
        bucket_name = s3_config.BUCKET_NAME
        bucket_exists = await storage_service.check_bucket_exists(bucket_name)
        
        if connection_status and bucket_exists:
            return {
                "status": "ok",
                "details": {
                    "connection": "connected",
                    "bucket": bucket_name,
                    "encryption": "AES-256"
                }
            }
        else:
            # Determine what's missing
            details = {
                "connection": "connected" if connection_status else "disconnected",
                "bucket": "accessible" if bucket_exists else "inaccessible",
                "encryption": "AES-256"
            }
            
            return {
                "status": "error",
                "details": details,
                "message": "S3 storage dependency check failed"
            }
    except Exception as e:
        # Log the error
        logging_utils.log_error(
            logger, 
            "S3 health check failed", 
            {"error": str(e)}
        )
        
        return {
            "status": "error",
            "details": {"error": str(e)},
            "message": "S3 storage connection failed"
        }


def check_gpu_health() -> Dict[str, Any]:
    """
    Check the availability and health of GPU resources for TensorFlow.
    
    This function verifies that TensorFlow can access GPU resources and that
    there is sufficient GPU memory available for OCR processing.
    
    Returns:
        Dict[str, Any]: A dictionary containing the health status of GPU resources
    """
    try:
        # Check if TensorFlow can see any GPUs
        gpu_devices = tensorflow_utils.get_available_gpus()
        gpu_count = len(gpu_devices)
        
        if gpu_count == 0:
            return {
                "status": "error",
                "details": {"gpu_count": 0},
                "message": "No GPU devices available for TensorFlow"
            }
        
        # Check GPU memory - we need at least 8GB VRAM as per requirements
        gpu_memory = tensorflow_utils.get_gpu_memory()
        required_memory_gb = 8
        
        # Convert memory to GB for comparison
        available_memory_gb = gpu_memory / 1024  # Assuming memory is in MB
        
        if available_memory_gb < required_memory_gb:
            return {
                "status": "error",
                "details": {
                    "gpu_count": gpu_count,
                    "available_memory_gb": available_memory_gb,
                    "required_memory_gb": required_memory_gb
                },
                "message": f"Insufficient GPU memory: {available_memory_gb}GB available, {required_memory_gb}GB required"
            }
        
        # Check if TensorFlow can actually use the GPU
        gpu_available = tensorflow_utils.check_gpu_tensorflow_compatibility()
        
        if not gpu_available:
            return {
                "status": "error",
                "details": {
                    "gpu_count": gpu_count,
                    "available_memory_gb": available_memory_gb,
                    "tensorflow_gpu_enabled": False
                },
                "message": "TensorFlow cannot use available GPUs"
            }
        
        # All checks passed
        return {
            "status": "ok",
            "details": {
                "gpu_count": gpu_count,
                "available_memory_gb": available_memory_gb,
                "tensorflow_gpu_enabled": True,
                "cuda_version": tensorflow_utils.get_cuda_version()
            }
        }
    except Exception as e:
        # Log the error
        logging_utils.log_error(
            logger, 
            "GPU health check failed", 
            {"error": str(e)}
        )
        
        return {
            "status": "error",
            "details": {"error": str(e)},
            "message": "GPU health check failed"
        }