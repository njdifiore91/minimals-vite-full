"""
Health check endpoints for Kubernetes probes in the Document Service.

This module provides liveness and readiness probe endpoints that Kubernetes uses to determine
if the service is running correctly and ready to accept traffic. The liveness probe verifies
that the application is running, while the readiness probe checks that all dependencies
(RabbitMQ, S3) are available.
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, status, Response
from pydantic import BaseModel

from services import QueueService, StorageService

# Configure logger
logger = logging.getLogger(__name__)

# Create router
health_router = APIRouter(tags=["health"])


class HealthStatus(BaseModel):
    """Model for health check response data."""
    status: str
    version: str
    details: Dict[str, Any]


async def get_queue_service() -> QueueService:
    """Dependency to get the queue service instance."""
    # In a real implementation, this would be retrieved from a dependency injection system
    # For this example, we'll assume it's available through app state
    from app import get_app
    return get_app().queue_service


async def get_storage_service() -> StorageService:
    """Dependency to get the storage service instance."""
    # In a real implementation, this would be retrieved from a dependency injection system
    # For this example, we'll assume it's available through app state
    from app import get_app
    return get_app().storage_service


@health_router.get("/health/liveness", response_model=HealthStatus)
async def liveness_check() -> HealthStatus:
    """
    Liveness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is running and responsive.
    It does not check dependencies, only that the service itself is operational.
    
    Returns:
        HealthStatus: Health check response with status and details
    """
    logger.debug("Liveness check requested")
    
    # If this endpoint is reachable, the service is alive
    return HealthStatus(
        status="UP",
        version="1.0.0",  # This should be retrieved from app config in a real implementation
        details={
            "service": "document-service",
            "status": "operational"
        }
    )


@health_router.get("/health/readiness", response_model=HealthStatus)
async def readiness_check(
    response: Response,
    queue_service: QueueService = Depends(get_queue_service),
    storage_service: StorageService = Depends(get_storage_service)
) -> HealthStatus:
    """
    Readiness probe endpoint for Kubernetes.
    
    This endpoint checks if the application is ready to accept traffic by verifying
    that all dependencies (RabbitMQ, S3) are available and properly connected.
    
    Args:
        response: FastAPI Response object for setting status code
        queue_service: RabbitMQ queue service instance
        storage_service: S3 storage service instance
        
    Returns:
        HealthStatus: Health check response with status and details
    """
    logger.debug("Readiness check requested")
    
    # Initialize health details
    health_details = {
        "service": "document-service",
        "dependencies": {
            "rabbitmq": {"status": "DOWN", "details": None},
            "s3": {"status": "DOWN", "details": None}
        }
    }
    
    # Check RabbitMQ connection
    rabbitmq_status = "DOWN"
    rabbitmq_details = None
    try:
        if queue_service.is_connected():
            rabbitmq_status = "UP"
            rabbitmq_details = {
                "connection": "established",
                "exchange": "mca.documents",
                "queue": "document-processing"
            }
        else:
            rabbitmq_details = {"error": "Connection not established"}
    except Exception as e:
        logger.error(f"Error checking RabbitMQ connection: {str(e)}")
        rabbitmq_details = {"error": str(e)}
    
    health_details["dependencies"]["rabbitmq"] = {
        "status": rabbitmq_status,
        "details": rabbitmq_details
    }
    
    # Check S3 connection
    s3_status = "DOWN"
    s3_details = None
    try:
        if storage_service.is_connected():
            s3_status = "UP"
            s3_details = {
                "connection": "established",
                "bucket": storage_service.get_bucket_name()
            }
        else:
            s3_details = {"error": "Connection not established"}
    except Exception as e:
        logger.error(f"Error checking S3 connection: {str(e)}")
        s3_details = {"error": str(e)}
    
    health_details["dependencies"]["s3"] = {
        "status": s3_status,
        "details": s3_details
    }
    
    # Determine overall status
    overall_status = "UP" if (rabbitmq_status == "UP" and s3_status == "UP") else "DOWN"
    
    # Set appropriate HTTP status code
    if overall_status == "DOWN":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return HealthStatus(
        status=overall_status,
        version="1.0.0",  # This should be retrieved from app config in a real implementation
        details=health_details
    )