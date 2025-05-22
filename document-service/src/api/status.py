#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Status API endpoints for the Document Service.

This module provides status endpoints for monitoring the Document Service.
It includes endpoints for checking service status, retrieving metrics, and
monitoring document processing statistics. These endpoints are used by
monitoring systems like Datadog to track service performance and health.

Endpoints:
    - GET /status: Get overall service status
    - GET /status/metrics: Get Prometheus-compatible metrics
    - GET /status/stats: Get detailed document processing statistics

Security:
    The /status endpoint is public, but /status/metrics and /status/stats
    require a valid JWT token with appropriate permissions.
"""

import os
import time
import json
import logging
import datetime
import platform
import psutil
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

# Import Prometheus client for metrics
from prometheus_client import (
    Counter, Gauge, Histogram, Summary, 
    REGISTRY, CONTENT_TYPE_LATEST, generate_latest
)

# Import service-specific modules
from ..config import app_config
from ..utils.validation_utils import validate_jwt_token
from ..utils.logging_utils import get_logger
from ..services.document_service import DocumentService
from ..services.queue_service import QueueService

# Set up logger
logger = get_logger(__name__)

# Create router
router = APIRouter(
    tags=["status"],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal Server Error"}
    }
)

# Security scheme
security = HTTPBearer()

# Define Prometheus metrics

# Document processing metrics
DOCUMENT_PROCESSED_TOTAL = Counter(
    'document_service_documents_processed_total',
    'Total number of documents processed',
    ['status', 'document_type']
)

DOCUMENT_PROCESSING_TIME = Histogram(
    'document_service_processing_seconds',
    'Time spent processing documents',
    ['document_type'],
    buckets=(0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, 15.0, 30.0, 60.0)
)

DOCUMENT_CLASSIFICATION_ACCURACY = Gauge(
    'document_service_classification_accuracy',
    'Document classification accuracy percentage',
    ['model_type']
)

# Queue metrics
QUEUE_DEPTH = Gauge(
    'document_service_queue_depth',
    'Current depth of the document processing queue',
    ['queue_name']
)

QUEUE_PROCESSING_RATE = Gauge(
    'document_service_queue_processing_rate',
    'Rate of document processing per minute',
    ['queue_name']
)

# System metrics
CPU_USAGE = Gauge(
    'document_service_cpu_usage_percent',
    'CPU usage percentage'
)

MEMORY_USAGE = Gauge(
    'document_service_memory_usage_bytes',
    'Memory usage in bytes'
)

DISK_USAGE = Gauge(
    'document_service_disk_usage_percent',
    'Disk usage percentage'
)

OPEN_CONNECTIONS = Gauge(
    'document_service_open_connections',
    'Number of open connections'
)

# API metrics
API_REQUESTS_TOTAL = Counter(
    'document_service_api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status']
)

API_REQUEST_DURATION = Histogram(
    'document_service_api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Models for request/response
class SystemStatus(BaseModel):
    """Model representing system status information."""
    cpu_usage_percent: float = Field(..., description="CPU usage percentage")
    memory_usage_bytes: int = Field(..., description="Memory usage in bytes")
    memory_usage_percent: float = Field(..., description="Memory usage percentage")
    disk_usage_percent: float = Field(..., description="Disk usage percentage")
    open_connections: int = Field(..., description="Number of open connections")
    open_file_descriptors: int = Field(..., description="Number of open file descriptors")


class QueueStatus(BaseModel):
    """Model representing queue status information."""
    queue_name: str = Field(..., description="Name of the queue")
    depth: int = Field(..., description="Current queue depth")
    processing_rate: float = Field(..., description="Processing rate per minute")
    consumers: int = Field(..., description="Number of active consumers")


class DocumentStats(BaseModel):
    """Model representing document processing statistics."""
    total_processed: int = Field(..., description="Total number of documents processed")
    successful: int = Field(..., description="Number of successfully processed documents")
    failed: int = Field(..., description="Number of failed documents")
    avg_processing_time: float = Field(..., description="Average processing time in seconds")
    classification_accuracy: float = Field(..., description="Classification accuracy percentage")
    documents_by_type: Dict[str, int] = Field(..., description="Document count by type")


class StatusResponse(BaseModel):
    """Response model for status endpoint."""
    status: str = Field(..., description="Overall service status (UP, DEGRADED, DOWN)")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Current environment")
    timestamp: str = Field(..., description="Current timestamp in ISO format")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    system: SystemStatus = Field(..., description="System status information")
    queues: List[QueueStatus] = Field(..., description="Queue status information")
    document_stats: DocumentStats = Field(..., description="Document processing statistics")


# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify JWT token and check if user has appropriate role.
    
    Args:
        credentials: HTTP Authorization credentials containing the JWT token
        
    Returns:
        dict: Decoded token payload if valid
        
    Raises:
        HTTPException: If token is invalid or user doesn't have required role
    """
    try:
        token = credentials.credentials
        payload = validate_jwt_token(token)
        
        # Check if user has Operations Staff or System Admin role
        if "roles" not in payload or not any(role in payload["roles"] for role in ["operations_staff", "system_admin"]):
            logger.warning(f"User {payload.get('sub', 'unknown')} attempted to access status metrics without proper role")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Operations Staff or System Admin role required."
            )
        
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/", response_model=StatusResponse, summary="Get service status")
async def get_status():
    """
    Get overall service status.
    
    This endpoint provides a comprehensive overview of the Document Service status,
    including system metrics, queue information, and document processing statistics.
    This endpoint is public and does not require authentication.
    
    Returns:
        StatusResponse: Comprehensive service status information
    """
    try:
        logger.info("Retrieving service status")
        
        # Get service information
        version = os.environ.get("SERVICE_VERSION", "1.0.0")
        environment = os.environ.get("ENVIRONMENT", "development")
        start_time = app_config.get_start_time()
        uptime_seconds = int(time.time() - start_time)
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        connections = len(psutil.net_connections())
        open_files = len(psutil.Process().open_files())
        
        # Update Prometheus metrics
        CPU_USAGE.set(cpu_percent)
        MEMORY_USAGE.set(memory.used)
        DISK_USAGE.set(disk.percent)
        OPEN_CONNECTIONS.set(connections)
        
        # Get queue information
        queue_service = QueueService()
        queues = await queue_service.get_queue_stats()
        
        # Update queue metrics
        for queue in queues:
            QUEUE_DEPTH.labels(queue_name=queue.queue_name).set(queue.depth)
            QUEUE_PROCESSING_RATE.labels(queue_name=queue.queue_name).set(queue.processing_rate)
        
        # Get document processing statistics
        document_service = DocumentService()
        doc_stats = await document_service.get_processing_stats()
        
        # Determine overall status
        overall_status = "UP"
        if cpu_percent > 90 or memory.percent > 90 or disk.percent > 90:
            overall_status = "DEGRADED"
        
        # Check if any queues are backed up
        for queue in queues:
            if queue.depth > 1000:  # Threshold for queue backup
                overall_status = "DEGRADED"
        
        # Create response
        response = StatusResponse(
            status=overall_status,
            version=version,
            environment=environment,
            timestamp=datetime.datetime.now().isoformat(),
            uptime_seconds=uptime_seconds,
            system=SystemStatus(
                cpu_usage_percent=cpu_percent,
                memory_usage_bytes=memory.used,
                memory_usage_percent=memory.percent,
                disk_usage_percent=disk.percent,
                open_connections=connections,
                open_file_descriptors=open_files
            ),
            queues=queues,
            document_stats=doc_stats
        )
        
        logger.info(f"Service status: {overall_status}")
        return response
    
    except Exception as e:
        logger.error(f"Error retrieving service status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving service status: {str(e)}"
        )


@router.get("/metrics", summary="Get Prometheus metrics")
async def get_metrics(request: Request, token_payload: Dict = Depends(verify_token)):
    """
    Get Prometheus-compatible metrics.
    
    This endpoint returns metrics in Prometheus format for scraping by monitoring systems.
    It requires authentication with Operations Staff or System Admin role.
    
    Args:
        request: FastAPI request object
        token_payload: JWT token payload from authentication
        
    Returns:
        Response: Prometheus-formatted metrics
    """
    try:
        logger.debug("Retrieving Prometheus metrics")
        
        # Update system metrics before returning
        CPU_USAGE.set(psutil.cpu_percent(interval=0.1))
        memory = psutil.virtual_memory()
        MEMORY_USAGE.set(memory.used)
        DISK_USAGE.set(psutil.disk_usage("/").percent)
        OPEN_CONNECTIONS.set(len(psutil.net_connections()))
        
        # Generate metrics in Prometheus format
        metrics_data = generate_latest(REGISTRY)
        
        return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)
    
    except Exception as e:
        logger.error(f"Error retrieving metrics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving metrics: {str(e)}"
        )


@router.get("/stats", summary="Get detailed document processing statistics")
async def get_document_stats(token_payload: Dict = Depends(verify_token)):
    """
    Get detailed document processing statistics.
    
    This endpoint provides detailed statistics about document processing,
    including throughput, accuracy, and processing times by document type.
    It requires authentication with Operations Staff or System Admin role.
    
    Args:
        token_payload: JWT token payload from authentication
        
    Returns:
        Dict[str, Any]: Detailed document processing statistics
    """
    try:
        logger.info("Retrieving detailed document processing statistics")
        
        # Get document service
        document_service = DocumentService()
        
        # Get detailed statistics
        stats = await document_service.get_detailed_stats()
        
        logger.info(f"Retrieved detailed statistics for {len(stats.get('document_types', []))} document types")
        return stats
    
    except Exception as e:
        logger.error(f"Error retrieving document statistics: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving document statistics: {str(e)}"
        )


# Middleware for tracking API metrics
@router.middleware("http")
async def track_api_metrics(request: Request, call_next):
    """
    Middleware to track API metrics for monitoring.
    
    This middleware tracks request counts and durations for all API endpoints.
    
    Args:
        request: FastAPI request object
        call_next: Next middleware or endpoint handler
        
    Returns:
        Response: FastAPI response object
    """
    # Extract request information
    method = request.method
    endpoint = request.url.path
    
    # Record start time
    start_time = time.time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Update metrics
    API_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
    API_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
    
    return response