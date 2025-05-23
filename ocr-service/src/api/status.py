"""Status endpoints for monitoring the OCR Service.

This module provides endpoints for checking service status, retrieving metrics,
and monitoring OCR processing statistics. These endpoints are used by monitoring
systems like Datadog to track service performance, accuracy metrics, and processing
throughput over time.
"""

import os
import time
import psutil
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from prometheus_client import Counter, Gauge, Histogram, REGISTRY
from prometheus_client.openmetrics.exposition import generate_latest, CONTENT_TYPE_LATEST

from ..config import app_config, rabbitmq_config
from ..services import ocr_service, queue_service
from ..utils.logging_utils import get_logger
from ..utils.tensorflow_utils import get_gpu_utilization
from ..auth.jwt_auth import validate_api_key

# Initialize logger
logger = get_logger(__name__)

# Create router
status_router = APIRouter()

# Define Prometheus metrics
# OCR processing metrics
OCR_PROCESSING_TOTAL = Counter(
    'ocr_processing_total',
    'Total number of documents processed by OCR',
    ['document_type', 'status']
)

OCR_PROCESSING_DURATION = Histogram(
    'ocr_processing_duration_seconds',
    'Time spent processing documents with OCR',
    ['document_type'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0]
)

OCR_ACCURACY = Gauge(
    'ocr_accuracy_percentage',
    'OCR extraction accuracy percentage',
    ['document_type']
)

OCR_CONFIDENCE_SCORE = Histogram(
    'ocr_confidence_score',
    'Distribution of confidence scores for OCR extractions',
    ['document_type', 'field_type'],
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    'rabbitmq_queue_depth',
    'Number of messages in RabbitMQ queue',
    ['queue_name']
)

QUEUE_PROCESSING_TIME = Histogram(
    'rabbitmq_processing_time_seconds',
    'Time spent processing messages from RabbitMQ',
    ['queue_name'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0]
)

# Resource usage metrics
CPU_USAGE = Gauge('cpu_usage_percentage', 'CPU usage percentage')
MEMORY_USAGE = Gauge('memory_usage_bytes', 'Memory usage in bytes')
GPU_USAGE = Gauge('gpu_usage_percentage', 'GPU usage percentage', ['gpu_id'])
GPU_MEMORY_USAGE = Gauge('gpu_memory_usage_bytes', 'GPU memory usage in bytes', ['gpu_id'])


@status_router.get("/", summary="Get OCR service status")
async def get_status(request: Request) -> Dict[str, Any]:
    """Get the current status of the OCR service.
    
    Returns:
        Dict[str, Any]: A dictionary containing service status information.
    """
    try:
        # Get basic service information
        service_info = {
            "service": "OCR Service",
            "version": app_config.VERSION,
            "environment": app_config.ENVIRONMENT,
            "status": "healthy",
            "uptime_seconds": int(time.time() - psutil.Process(os.getpid()).create_time()),
        }
        
        # Add OCR processing statistics
        service_info["ocr_stats"] = {
            "processed_total": sum(OCR_PROCESSING_TOTAL.collect()[0].samples[0].value 
                               for sample in OCR_PROCESSING_TOTAL.collect()[0].samples),
            "average_accuracy": OCR_ACCURACY._value.get({"document_type": "all"}, 99.0),
            "average_processing_time": OCR_PROCESSING_DURATION._sum.get({"document_type": "all"}, 0) / 
                                      max(OCR_PROCESSING_DURATION._count.get({"document_type": "all"}, 1), 1)
        }
        
        # Add queue information
        service_info["queue_stats"] = {
            "queue_depth": {
                queue: QUEUE_DEPTH._value.get({"queue_name": queue}, 0)
                for queue in rabbitmq_config.QUEUE_NAMES
            },
            "messages_processed": sum(QUEUE_PROCESSING_TIME._count.values())
        }
        
        # Add resource usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory_info = psutil.Process(os.getpid()).memory_info()
        
        service_info["resource_usage"] = {
            "cpu_percent": cpu_percent,
            "memory_bytes": memory_info.rss,
            "gpu": get_gpu_utilization()
        }
        
        # Update metrics
        CPU_USAGE.set(cpu_percent)
        MEMORY_USAGE.set(memory_info.rss)
        
        # Update GPU metrics if available
        gpu_stats = get_gpu_utilization()
        if gpu_stats:
            for gpu_id, stats in gpu_stats.items():
                GPU_USAGE.labels(gpu_id=gpu_id).set(stats["utilization"])
                GPU_MEMORY_USAGE.labels(gpu_id=gpu_id).set(stats["memory_used"])
        
        return service_info
    
    except Exception as e:
        logger.error(f"Error getting service status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting service status: {str(e)}"
        )


@status_router.get("/health", summary="Health check endpoint")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint for load balancers and monitoring systems.
    
    Returns:
        Dict[str, str]: A dictionary with status information.
    """
    return {"status": "healthy"}


@status_router.get("/metrics", summary="Get Prometheus metrics")
async def metrics(request: Request, response: Response) -> Response:
    """Get Prometheus metrics for the OCR service.
    
    This endpoint exposes all Prometheus metrics in the OpenMetrics format,
    which can be scraped by Prometheus.
    
    Args:
        request: The FastAPI request object.
        response: The FastAPI response object.
    
    Returns:
        Response: A response containing Prometheus metrics.
    """
    # Update queue depth metrics
    try:
        queue_depths = await queue_service.get_queue_depths()
        for queue_name, depth in queue_depths.items():
            QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)
    except Exception as e:
        logger.warning(f"Failed to update queue depth metrics: {str(e)}")
    
    # Generate metrics output
    response.headers["Content-Type"] = CONTENT_TYPE_LATEST
    return Response(content=generate_latest(REGISTRY), media_type=CONTENT_TYPE_LATEST)


@status_router.get("/metrics/ocr", summary="Get OCR-specific metrics", dependencies=[Depends(validate_api_key)])
async def ocr_metrics() -> Dict[str, Any]:
    """Get detailed OCR-specific metrics.
    
    This endpoint requires authentication and provides detailed metrics about
    OCR processing, including accuracy by document type, confidence scores,
    and processing times.
    
    Returns:
        Dict[str, Any]: A dictionary containing OCR metrics.
    """
    try:
        # Get OCR metrics from the OCR service
        ocr_metrics = await ocr_service.get_metrics()
        
        # Update Prometheus metrics based on the retrieved data
        for doc_type, stats in ocr_metrics["accuracy"].items():
            OCR_ACCURACY.labels(document_type=doc_type).set(stats["percentage"])
        
        # Return the detailed metrics
        return ocr_metrics
    
    except Exception as e:
        logger.error(f"Error getting OCR metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting OCR metrics: {str(e)}"
        )


@status_router.get("/metrics/queue", summary="Get queue metrics", dependencies=[Depends(validate_api_key)])
async def queue_metrics() -> Dict[str, Any]:
    """Get detailed queue metrics.
    
    This endpoint requires authentication and provides detailed metrics about
    RabbitMQ queues, including queue depths, processing times, and error rates.
    
    Returns:
        Dict[str, Any]: A dictionary containing queue metrics.
    """
    try:
        # Get queue metrics from the queue service
        queue_metrics = await queue_service.get_metrics()
        
        # Update Prometheus metrics based on the retrieved data
        for queue_name, depth in queue_metrics["queue_depths"].items():
            QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)
        
        # Return the detailed metrics
        return queue_metrics
    
    except Exception as e:
        logger.error(f"Error getting queue metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting queue metrics: {str(e)}"
        )


@status_router.get("/metrics/resource", summary="Get resource usage metrics", dependencies=[Depends(validate_api_key)])
async def resource_metrics() -> Dict[str, Any]:
    """Get detailed resource usage metrics.
    
    This endpoint requires authentication and provides detailed metrics about
    resource usage, including CPU, memory, and GPU utilization.
    
    Returns:
        Dict[str, Any]: A dictionary containing resource usage metrics.
    """
    try:
        # Get CPU and memory usage
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory_info = psutil.Process(os.getpid()).memory_info()
        
        # Get GPU utilization if available
        gpu_stats = get_gpu_utilization()
        
        # Update Prometheus metrics
        CPU_USAGE.set(cpu_percent)
        MEMORY_USAGE.set(memory_info.rss)
        
        if gpu_stats:
            for gpu_id, stats in gpu_stats.items():
                GPU_USAGE.labels(gpu_id=gpu_id).set(stats["utilization"])
                GPU_MEMORY_USAGE.labels(gpu_id=gpu_id).set(stats["memory_used"])
        
        # Return detailed resource metrics
        return {
            "cpu": {
                "usage_percent": cpu_percent,
                "core_count": psutil.cpu_count(),
                "load_average": os.getloadavg(),
            },
            "memory": {
                "total_bytes": psutil.virtual_memory().total,
                "available_bytes": psutil.virtual_memory().available,
                "used_bytes": memory_info.rss,
                "percent": psutil.virtual_memory().percent,
            },
            "gpu": gpu_stats or {},
        }
    
    except Exception as e:
        logger.error(f"Error getting resource metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting resource metrics: {str(e)}"
        )