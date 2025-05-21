"""Status API endpoints for the Document Service.

This module provides endpoints for checking service status, retrieving metrics,
and monitoring document processing statistics. These endpoints are used by
monitoring systems like Datadog to track service performance and health over time.
"""

import os
import time
import psutil
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, Request, Response
from prometheus_client import Counter, Histogram, Gauge, REGISTRY, generate_latest
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST

from ..config import app_config
from ..services import queue_service
from ..utils import logging_utils

# Create router
router = APIRouter(tags=["status"])

# Define Prometheus metrics
DOCUMENT_PROCESSED_COUNTER = Counter(
    "document_service_documents_processed_total",
    "Total number of documents processed",
    ["document_type", "status"]
)

DOCUMENT_PROCESSING_TIME = Histogram(
    "document_service_processing_time_seconds",
    "Time spent processing documents",
    ["document_type"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0)
)

CLASSIFICATION_ACCURACY = Gauge(
    "document_service_classification_accuracy",
    "Classification accuracy percentage",
    ["model_type"]
)

QUEUE_DEPTH = Gauge(
    "document_service_queue_depth",
    "Current depth of the document processing queue",
    ["queue_name"]
)

CPU_USAGE = Gauge(
    "document_service_cpu_usage_percent",
    "CPU usage percentage"
)

MEMORY_USAGE = Gauge(
    "document_service_memory_usage_bytes",
    "Memory usage in bytes"
)

ACTIVE_CONNECTIONS = Gauge(
    "document_service_active_connections",
    "Number of active connections",
    ["connection_type"]
)


@router.get("/")
async def get_status() -> Dict[str, Any]:
    """Get the current status of the Document Service.
    
    Returns:
        Dict[str, Any]: Service status information including uptime, version,
                        and health indicators.
    """
    process = psutil.Process(os.getpid())
    
    # Update resource metrics
    CPU_USAGE.set(process.cpu_percent())
    MEMORY_USAGE.set(process.memory_info().rss)
    
    # Get queue depth
    try:
        queue_depth = await queue_service.get_queue_depth("document-processing")
        QUEUE_DEPTH.labels(queue_name="document-processing").set(queue_depth)
    except Exception as e:
        logging_utils.log_error("Failed to get queue depth", error=str(e))
        queue_depth = -1
    
    # Get connection counts
    try:
        rabbitmq_connections = await queue_service.get_connection_count()
        ACTIVE_CONNECTIONS.labels(connection_type="rabbitmq").set(rabbitmq_connections)
    except Exception as e:
        logging_utils.log_error("Failed to get RabbitMQ connection count", error=str(e))
        rabbitmq_connections = -1
    
    return {
        "status": "operational",
        "service": "document-service",
        "version": app_config.VERSION,
        "uptime_seconds": time.time() - process.create_time(),
        "environment": app_config.ENVIRONMENT,
        "resources": {
            "cpu_percent": process.cpu_percent(),
            "memory_usage_bytes": process.memory_info().rss,
            "thread_count": process.num_threads()
        },
        "queue": {
            "document_processing_depth": queue_depth
        },
        "connections": {
            "rabbitmq": rabbitmq_connections
        }
    }


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Simple health check endpoint for load balancers and monitoring systems.
    
    Returns:
        Dict[str, str]: Simple health status
    """
    return {"status": "healthy"}


@router.get("/metrics")
async def metrics(request: Request) -> Response:
    """Expose Prometheus metrics for scraping.
    
    This endpoint exposes all registered Prometheus metrics in the OpenMetrics format,
    which can be scraped by Prometheus monitoring systems.
    
    Args:
        request: The incoming request
        
    Returns:
        Response: Prometheus metrics in OpenMetrics format
    """
    # Update resource metrics before returning
    process = psutil.Process(os.getpid())
    CPU_USAGE.set(process.cpu_percent())
    MEMORY_USAGE.set(process.memory_info().rss)
    
    # Try to update queue depth
    try:
        queue_depth = await queue_service.get_queue_depth("document-processing")
        QUEUE_DEPTH.labels(queue_name="document-processing").set(queue_depth)
    except Exception as e:
        logging_utils.log_error("Failed to update queue depth for metrics", error=str(e))
    
    # Generate metrics in OpenMetrics format
    return Response(generate_latest(REGISTRY), headers={"Content-Type": CONTENT_TYPE_LATEST})


@router.get("/stats")
async def get_processing_stats() -> Dict[str, Any]:
    """Get detailed document processing statistics.
    
    Returns:
        Dict[str, Any]: Detailed processing statistics including throughput,
                        accuracy, and error rates.
    """
    # This would typically be retrieved from a database or cache
    # For now, we'll return some sample statistics
    return {
        "throughput": {
            "documents_per_minute": 42.5,
            "documents_processed_today": 3240,
            "documents_processed_total": 1245678
        },
        "accuracy": {
            "overall_percent": 99.2,
            "by_model": {
                "svm": 98.7,
                "random_forest": 99.4
            },
            "by_document_type": {
                "application": 99.5,
                "tax_return": 98.9,
                "bank_statement": 99.3,
                "pay_stub": 99.1,
                "id_document": 99.7,
                "other": 97.8
            }
        },
        "errors": {
            "error_rate_percent": 0.8,
            "most_common_errors": [
                {"type": "low_confidence", "count": 156, "percent": 0.4},
                {"type": "invalid_format", "count": 89, "percent": 0.2},
                {"type": "processing_timeout", "count": 45, "percent": 0.1},
                {"type": "other", "count": 32, "percent": 0.1}
            ]
        },
        "queue_status": {
            "current_depth": 15,
            "average_wait_time_seconds": 3.2,
            "max_wait_time_seconds": 12.5
        }
    }


# Helper functions to update metrics from other parts of the application

def record_document_processed(document_type: str, status: str) -> None:
    """Record a processed document in the metrics.
    
    Args:
        document_type: The type of document processed
        status: The processing status (success, error, etc.)
    """
    DOCUMENT_PROCESSED_COUNTER.labels(document_type=document_type, status=status).inc()


def record_processing_time(document_type: str, processing_time: float) -> None:
    """Record document processing time in the metrics.
    
    Args:
        document_type: The type of document processed
        processing_time: The time taken to process the document in seconds
    """
    DOCUMENT_PROCESSING_TIME.labels(document_type=document_type).observe(processing_time)


def update_classification_accuracy(model_type: str, accuracy: float) -> None:
    """Update the classification accuracy metric.
    
    Args:
        model_type: The type of classification model (svm, random_forest, etc.)
        accuracy: The accuracy percentage (0-100)
    """
    CLASSIFICATION_ACCURACY.labels(model_type=model_type).set(accuracy)


def update_queue_depth(queue_name: str, depth: int) -> None:
    """Update the queue depth metric.
    
    Args:
        queue_name: The name of the queue
        depth: The current depth of the queue
    """
    QUEUE_DEPTH.labels(queue_name=queue_name).set(depth)