"""Health check endpoints for Kubernetes probes in the Document Service.

This module provides liveness and readiness probe endpoints that Kubernetes uses to determine
if the service is running correctly and ready to accept traffic. The liveness probe verifies
that the application is running, while the readiness probe checks that all dependencies
(RabbitMQ, S3) are available.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, status, Response

from ..services.queue_service import QueueService
from ..services.storage_service import StorageService
from ..utils.logging_utils import get_logger
from ..utils.time_utils import get_current_timestamp

# Initialize logger
logger = get_logger(__name__)

# Create router
health_router = APIRouter(tags=["Health"])


@health_router.get("/liveness", summary="Liveness probe for Kubernetes")
async def liveness_probe() -> Dict[str, Any]:
    """Liveness probe endpoint for Kubernetes.
    
    This endpoint verifies that the application is running and responsive.
    It does not check dependencies, only that the service itself is operational.
    
    Returns:
        Dict[str, Any]: Health status information with timestamp
    """
    logger.debug("Liveness probe called")
    
    return {
        "status": "UP",
        "timestamp": get_current_timestamp(),
        "service": "document-service",
        "details": {
            "message": "Service is running"
        }
    }


async def check_rabbitmq_connection(queue_service: QueueService) -> Dict[str, Any]:
    """Check RabbitMQ connection status.
    
    Args:
        queue_service (QueueService): The queue service instance
        
    Returns:
        Dict[str, Any]: Connection status information
    """
    try:
        is_connected = await queue_service.check_connection()
        return {
            "status": "UP" if is_connected else "DOWN",
            "details": {
                "connected": is_connected,
                "message": "Connected to RabbitMQ" if is_connected else "Not connected to RabbitMQ"
            }
        }
    except Exception as e:
        logger.error(f"Error checking RabbitMQ connection: {str(e)}")
        return {
            "status": "DOWN",
            "details": {
                "connected": False,
                "message": f"Error checking RabbitMQ connection: {str(e)}"
            }
        }


async def check_s3_connection(storage_service: StorageService) -> Dict[str, Any]:
    """Check S3 connection status.
    
    Args:
        storage_service (StorageService): The storage service instance
        
    Returns:
        Dict[str, Any]: Connection status information
    """
    try:
        is_connected = await storage_service.check_connection()
        return {
            "status": "UP" if is_connected else "DOWN",
            "details": {
                "connected": is_connected,
                "message": "Connected to S3" if is_connected else "Not connected to S3"
            }
        }
    except Exception as e:
        logger.error(f"Error checking S3 connection: {str(e)}")
        return {
            "status": "DOWN",
            "details": {
                "connected": False,
                "message": f"Error checking S3 connection: {str(e)}"
            }
        }


@health_router.get("/readiness", summary="Readiness probe for Kubernetes")
async def readiness_probe(
    response: Response,
    queue_service: QueueService = Depends(),
    storage_service: StorageService = Depends()
) -> Dict[str, Any]:
    """Readiness probe endpoint for Kubernetes.
    
    This endpoint verifies that the application is ready to accept traffic by checking
    that all dependencies (RabbitMQ, S3) are available and properly connected.
    
    Args:
        response (Response): FastAPI response object for setting status code
        queue_service (QueueService): The queue service instance
        storage_service (StorageService): The storage service instance
        
    Returns:
        Dict[str, Any]: Health status information with dependency details
    """
    logger.debug("Readiness probe called")
    
    # Check dependencies
    rabbitmq_status = await check_rabbitmq_connection(queue_service)
    s3_status = await check_s3_connection(storage_service)
    
    # Determine overall status
    overall_status = "UP"
    if rabbitmq_status["status"] == "DOWN" or s3_status["status"] == "DOWN":
        overall_status = "DOWN"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": overall_status,
        "timestamp": get_current_timestamp(),
        "service": "document-service",
        "dependencies": {
            "rabbitmq": rabbitmq_status,
            "s3": s3_status
        }
    }


@health_router.get("/", summary="General health check endpoint")
async def health_check(
    response: Response,
    queue_service: QueueService = Depends(),
    storage_service: StorageService = Depends()
) -> Dict[str, Any]:
    """General health check endpoint that combines liveness and readiness information.
    
    This endpoint provides comprehensive health information about the service and its
    dependencies, suitable for manual health checks and monitoring systems.
    
    Args:
        response (Response): FastAPI response object for setting status code
        queue_service (QueueService): The queue service instance
        storage_service (StorageService): The storage service instance
        
    Returns:
        Dict[str, Any]: Comprehensive health status information
    """
    logger.info("Health check called")
    
    # Check dependencies
    rabbitmq_status = await check_rabbitmq_connection(queue_service)
    s3_status = await check_s3_connection(storage_service)
    
    # Get service information
    service_info = {
        "name": "document-service",
        "version": "1.0.0",  # This should be retrieved from a version file or environment variable
        "description": "Document classification service for MCA processing"
    }
    
    # Determine overall status
    overall_status = "UP"
    if rabbitmq_status["status"] == "DOWN" or s3_status["status"] == "DOWN":
        overall_status = "DOWN"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return {
        "status": overall_status,
        "timestamp": get_current_timestamp(),
        "service": service_info,
        "dependencies": {
            "rabbitmq": rabbitmq_status,
            "s3": s3_status
        },
        "details": {
            "uptime": "Not implemented",  # This should be implemented to track service uptime
            "memory_usage": "Not implemented",  # This should be implemented to track memory usage
            "cpu_usage": "Not implemented"  # This should be implemented to track CPU usage
        }
    }