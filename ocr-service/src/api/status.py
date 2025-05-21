"""Status API endpoints for the OCR Service.

This module provides endpoints for monitoring the OCR Service, including:
- Overall service status
- Prometheus-compatible metrics
- OCR processing statistics
- Queue depth monitoring
- Resource usage metrics (CPU, GPU, memory)

These endpoints are used by monitoring systems like Datadog to track service
performance, accuracy metrics, and processing throughput over time.
"""

import os
import time
import psutil
from typing import Dict, Any, Optional

import GPUtil
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.security import APIKeyHeader
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, 
    generate_latest, REGISTRY, CONTENT_TYPE_LATEST
)

from ..config import app_config
from ..services import OCRService, QueueService
from ..utils.logging_utils import get_logger
from ..utils.error_utils import ServiceError

# Initialize logger
logger = get_logger(__name__)

# Create router
status_router = APIRouter()

# API Key security for sensitive endpoints
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Define Prometheus metrics

# OCR Processing metrics
OCR_REQUESTS_TOTAL = Counter(
    "ocr_requests_total", 
    "Total number of OCR processing requests",
    ["document_type", "status"]
)

OCR_PROCESSING_TIME = Histogram(
    "ocr_processing_time_seconds", 
    "Time spent processing OCR requests",
    ["document_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf"))
)

OCR_ACCURACY = Gauge(
    "ocr_accuracy_percent", 
    "OCR extraction accuracy percentage",
    ["document_type"]
)

OCR_CONFIDENCE_SCORES = Histogram(
    "ocr_confidence_scores", 
    "Distribution of OCR confidence scores",
    ["document_type"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0)
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    "rabbitmq_queue_depth", 
    "Number of messages in RabbitMQ queue",
    ["queue_name"]
)

QUEUE_PROCESSING_RATE = Gauge(
    "rabbitmq_processing_rate", 
    "Rate of message processing per minute",
    ["queue_name"]
)

# Resource usage metrics
CPU_USAGE = Gauge("cpu_usage_percent", "CPU usage percentage")
MEMORY_USAGE = Gauge("memory_usage_bytes", "Memory usage in bytes")
GPU_USAGE = Gauge("gpu_usage_percent", "GPU usage percentage", ["gpu_id"])
GPU_MEMORY_USAGE = Gauge("gpu_memory_usage_bytes", "GPU memory usage in bytes", ["gpu_id"])

# Service status metrics
SERVICE_UPTIME = Gauge("service_uptime_seconds", "Service uptime in seconds")
SERVICE_INFO = Gauge(
    "service_info", 
    "Service information",
    ["version", "environment"]
)

# Record start time for uptime calculation
START_TIME = time.time()

# Set service info metric (constant)
SERVICE_INFO.labels(
    version=app_config.VERSION,
    environment=app_config.ENVIRONMENT
).set(1)


def verify_api_key(api_key: Optional[str] = Depends(API_KEY_HEADER)) -> bool:
    """Verify the API key for protected endpoints.
    
    Args:
        api_key: The API key from the request header
        
    Returns:
        bool: True if the API key is valid
        
    Raises:
        HTTPException: If the API key is invalid or missing
    """
    if app_config.METRICS_API_KEY and (not api_key or api_key != app_config.METRICS_API_KEY):
        logger.warning("Unauthorized access attempt to metrics endpoint")
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    return True


def update_resource_metrics() -> None:
    """Update resource usage metrics (CPU, memory, GPU)."""
    # Update CPU and memory metrics
    CPU_USAGE.set(psutil.cpu_percent())
    MEMORY_USAGE.set(psutil.Process(os.getpid()).memory_info().rss)
    
    # Update GPU metrics if available
    try:
        gpus = GPUtil.getGPUs()
        for i, gpu in enumerate(gpus):
            GPU_USAGE.labels(gpu_id=str(i)).set(gpu.load * 100)
            GPU_MEMORY_USAGE.labels(gpu_id=str(i)).set(gpu.memoryUsed * 1024 * 1024)
    except Exception as e:
        logger.warning(f"Failed to update GPU metrics: {str(e)}")


def update_queue_metrics(queue_service: QueueService) -> None:
    """Update RabbitMQ queue metrics.
    
    Args:
        queue_service: The QueueService instance to get queue information
    """
    try:
        # Get queue depths
        queue_info = queue_service.get_queue_info()
        for queue_name, info in queue_info.items():
            QUEUE_DEPTH.labels(queue_name=queue_name).set(info.get("message_count", 0))
            QUEUE_PROCESSING_RATE.labels(queue_name=queue_name).set(info.get("processing_rate", 0))
    except Exception as e:
        logger.warning(f"Failed to update queue metrics: {str(e)}")


@status_router.get("/", summary="Get OCR Service status")
async def get_status(request: Request, _: bool = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get the current status of the OCR Service.
    
    Returns:
        Dict containing service status information including:
        - Service uptime
        - Version information
        - Resource usage (CPU, memory, GPU)
        - Queue depths
        - Processing statistics
    """
    try:
        # Get service instances from app state
        ocr_service = request.app.state.ocr_service
        queue_service = request.app.state.queue_service
        
        # Update resource metrics
        update_resource_metrics()
        update_queue_metrics(queue_service)
        
        # Calculate uptime
        uptime_seconds = time.time() - START_TIME
        SERVICE_UPTIME.set(uptime_seconds)
        
        # Get OCR statistics
        ocr_stats = ocr_service.get_statistics()
        
        # Prepare response
        return {
            "status": "healthy",
            "version": app_config.VERSION,
            "environment": app_config.ENVIRONMENT,
            "uptime_seconds": uptime_seconds,
            "resource_usage": {
                "cpu_percent": psutil.cpu_percent(),
                "memory_bytes": psutil.Process(os.getpid()).memory_info().rss,
                "gpu": [
                    {
                        "id": i,
                        "name": gpu.name,
                        "load_percent": gpu.load * 100,
                        "memory_used_bytes": gpu.memoryUsed * 1024 * 1024,
                        "memory_total_bytes": gpu.memoryTotal * 1024 * 1024,
                    }
                    for i, gpu in enumerate(GPUtil.getGPUs())
                ] if GPUtil.getGPUs() else []
            },
            "queue_info": queue_service.get_queue_info(),
            "ocr_statistics": ocr_stats
        }
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting service status: {str(e)}")


@status_router.get("/metrics", summary="Get Prometheus metrics")
async def metrics(request: Request, _: bool = Depends(verify_api_key)) -> Response:
    """Get Prometheus-compatible metrics.
    
    Returns:
        Response with Prometheus metrics in the OpenMetrics format
    """
    try:
        # Get service instances from app state
        ocr_service = request.app.state.ocr_service
        queue_service = request.app.state.queue_service
        
        # Update resource metrics
        update_resource_metrics()
        update_queue_metrics(queue_service)
        
        # Calculate uptime
        uptime_seconds = time.time() - START_TIME
        SERVICE_UPTIME.set(uptime_seconds)
        
        # Get OCR statistics and update metrics
        ocr_stats = ocr_service.get_statistics()
        
        # Update OCR metrics based on statistics
        for doc_type, stats in ocr_stats.get("by_document_type", {}).items():
            # Update accuracy metrics
            if "accuracy" in stats:
                OCR_ACCURACY.labels(document_type=doc_type).set(stats["accuracy"] * 100)
            
            # Update confidence score distributions if available
            if "confidence_distribution" in stats:
                for confidence_range, count in stats["confidence_distribution"].items():
                    # Convert range string to float for histogram bucket
                    # Example: "0.9-1.0" -> use midpoint 0.95
                    if "-" in confidence_range:
                        low, high = map(float, confidence_range.split("-"))
                        midpoint = (low + high) / 2
                        # Add to histogram by observing the midpoint value 'count' times
                        for _ in range(int(count)):
                            OCR_CONFIDENCE_SCORES.labels(document_type=doc_type).observe(midpoint)
        
        # Generate and return metrics in Prometheus format
        return Response(generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)
    except Exception as e:
        logger.error(f"Error generating metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating metrics: {str(e)}")


@status_router.get("/health", summary="Health check endpoint")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint that doesn't require authentication.
    
    This endpoint is used by Kubernetes liveness probes.
    
    Returns:
        Dict with status information
    """
    return {"status": "healthy"}


@status_router.get("/statistics", summary="Get detailed OCR statistics")
async def get_statistics(request: Request, _: bool = Depends(verify_api_key)) -> Dict[str, Any]:
    """Get detailed OCR processing statistics.
    
    Returns:
        Dict containing detailed OCR statistics including:
        - Processing counts by document type
        - Accuracy metrics
        - Processing times
        - Confidence score distributions
    """
    try:
        # Get OCR service from app state
        ocr_service = request.app.state.ocr_service
        
        # Get detailed statistics
        return ocr_service.get_statistics()
    except Exception as e:
        logger.error(f"Error getting OCR statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting OCR statistics: {str(e)}")