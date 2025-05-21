#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Diagnostic endpoints for the Document Service.

This module provides API endpoints for retrieving logs, checking configuration,
and performing diagnostic tests. These endpoints are used by operations staff
to troubleshoot issues with the service and verify its configuration.
"""

import logging
import os
import platform
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Import application dependencies
from app import get_application
from config import app_config
from utils.logging_utils import get_logs, log_with_context
from utils.security_utils import validate_token, check_permissions
from utils.error_utils import create_error_response
from utils.time_utils import format_timestamp
from utils.s3_utils import test_s3_connection
from utils.rabbitmq_utils import test_rabbitmq_connection
from utils.ml_utils import get_model_info

# Set up logger
logger = logging.getLogger(__name__)

# Set up security
security = HTTPBearer()

# Create router
diagnostics_router = APIRouter(
    tags=["diagnostics"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    },
)


# Define response models
class LogEntry(BaseModel):
    """Model for a log entry."""
    timestamp: str = Field(..., description="Timestamp of the log entry")
    level: str = Field(..., description="Log level (ERROR, WARN, INFO, DEBUG)")
    message: str = Field(..., description="Log message")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context information")


class LogsResponse(BaseModel):
    """Response model for logs endpoint."""
    logs: List[LogEntry] = Field(..., description="List of log entries")
    count: int = Field(..., description="Total number of log entries returned")
    start_time: Optional[str] = Field(None, description="Start time filter")
    end_time: Optional[str] = Field(None, description="End time filter")
    level: Optional[str] = Field(None, description="Log level filter")


class ConfigValue(BaseModel):
    """Model for a configuration value."""
    name: str = Field(..., description="Configuration parameter name")
    value: Any = Field(..., description="Configuration parameter value")
    source: str = Field(..., description="Source of the configuration (env, default, etc.)")
    sensitive: bool = Field(False, description="Whether the value is sensitive")


class ConfigResponse(BaseModel):
    """Response model for configuration endpoint."""
    service: Dict[str, Any] = Field(..., description="Service configuration")
    rabbitmq: Dict[str, Any] = Field(..., description="RabbitMQ configuration")
    s3: Dict[str, Any] = Field(..., description="S3 storage configuration")
    model: Dict[str, Any] = Field(..., description="Model configuration")
    environment: str = Field(..., description="Current environment")


class ConnectionStatus(BaseModel):
    """Model for connection status."""
    connected: bool = Field(..., description="Whether the connection is established")
    latency_ms: Optional[float] = Field(None, description="Connection latency in milliseconds")
    details: Optional[str] = Field(None, description="Additional details")
    error: Optional[str] = Field(None, description="Error message if connection failed")


class ModelStatus(BaseModel):
    """Model for ML model status."""
    loaded: bool = Field(..., description="Whether the model is loaded")
    version: str = Field(..., description="Model version")
    accuracy: float = Field(..., description="Model accuracy")
    last_trained: str = Field(..., description="When the model was last trained")
    document_types: List[str] = Field(..., description="Supported document types")


class DiagnosticTestResponse(BaseModel):
    """Response model for diagnostic test endpoint."""
    timestamp: str = Field(..., description="Timestamp of the test")
    system: Dict[str, Any] = Field(..., description="System information")
    rabbitmq: ConnectionStatus = Field(..., description="RabbitMQ connection status")
    s3: ConnectionStatus = Field(..., description="S3 connection status")
    model: ModelStatus = Field(..., description="Model status")
    overall_status: str = Field(..., description="Overall service status")


# Helper functions
async def check_admin_permissions(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Check if the user has admin permissions.
    
    Args:
        credentials: The HTTP authorization credentials
        
    Returns:
        dict: The decoded token payload if valid
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't have admin permissions
    """
    try:
        token = credentials.credentials
        payload = await validate_token(token)
        
        # Check if user has admin role
        if not check_permissions(payload, ["System Admin"]):
            logger.warning(f"User {payload.get('sub')} attempted to access diagnostics without admin permissions")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin permissions required"
            )
        
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


async def check_operations_permissions(credentials: HTTPAuthorizationCredentials = Security(security)):
    """Check if the user has operations staff permissions.
    
    Args:
        credentials: The HTTP authorization credentials
        
    Returns:
        dict: The decoded token payload if valid
        
    Raises:
        HTTPException: If the token is invalid or the user doesn't have operations permissions
    """
    try:
        token = credentials.credentials
        payload = await validate_token(token)
        
        # Check if user has operations staff or admin role
        if not check_permissions(payload, ["Operations Staff", "System Admin"]):
            logger.warning(f"User {payload.get('sub')} attempted to access diagnostics without operations permissions")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Operations Staff or Admin permissions required"
            )
        
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )


# Endpoints
@diagnostics_router.get(
    "/logs",
    response_model=LogsResponse,
    summary="Retrieve recent logs",
    description="Retrieve recent logs from the Document Service with optional filtering by time range and log level."
)
async def get_recent_logs(
    limit: int = Query(100, description="Maximum number of log entries to return", ge=1, le=1000),
    level: Optional[str] = Query(None, description="Filter by log level (ERROR, WARN, INFO, DEBUG)"),
    hours: Optional[int] = Query(None, description="Filter logs from the last N hours", ge=1, le=72),
    start_time: Optional[str] = Query(None, description="Filter logs starting from this time (ISO format)"),
    end_time: Optional[str] = Query(None, description="Filter logs until this time (ISO format)"),
    _: Dict = Depends(check_operations_permissions)
):
    """Retrieve recent logs from the Document Service.
    
    Args:
        limit: Maximum number of log entries to return
        level: Filter by log level (ERROR, WARN, INFO, DEBUG)
        hours: Filter logs from the last N hours
        start_time: Filter logs starting from this time (ISO format)
        end_time: Filter logs until this time (ISO format)
        _: Dependency to check operations permissions
        
    Returns:
        LogsResponse: The log entries matching the criteria
    """
    try:
        log_with_context(logger.info, "Retrieving recent logs", {
            "limit": limit,
            "level": level,
            "hours": hours,
            "start_time": start_time,
            "end_time": end_time
        })
        
        # Calculate time range if hours is provided
        if hours is not None:
            end = datetime.now()
            start = end - timedelta(hours=hours)
            start_time = start.isoformat() if start_time is None else start_time
            end_time = end.isoformat() if end_time is None else end_time
        
        # Get logs
        logs = await get_logs(limit=limit, level=level, start_time=start_time, end_time=end_time)
        
        return LogsResponse(
            logs=logs,
            count=len(logs),
            start_time=start_time,
            end_time=end_time,
            level=level
        )
    except Exception as e:
        log_with_context(logger.error, f"Error retrieving logs: {str(e)}", {"error": str(e)})
        return create_error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@diagnostics_router.get(
    "/config",
    response_model=ConfigResponse,
    summary="Get current configuration",
    description="Retrieve the current configuration of the Document Service with sensitive values masked."
)
async def get_current_config(_: Dict = Depends(check_admin_permissions)):
    """Get the current configuration of the Document Service.
    
    Args:
        _: Dependency to check admin permissions
        
    Returns:
        ConfigResponse: The current configuration
    """
    try:
        log_with_context(logger.info, "Retrieving current configuration")
        
        # Get configuration
        config = app_config.load_config()
        
        # Mask sensitive values
        masked_rabbitmq = {
            k: "*****" if k in ["username", "password", "client_cert", "client_key"] else v
            for k, v in config.rabbitmq.__dict__.items()
        }
        
        masked_s3 = {
            k: "*****" if k in ["access_key", "secret_key", "encryption_key"] else v
            for k, v in config.s3.__dict__.items()
        }
        
        # Return masked configuration
        return ConfigResponse(
            service={
                "name": config.service_name,
                "version": config.version,
                "port": config.port,
                "host": config.host,
                "debug": config.debug
            },
            rabbitmq=masked_rabbitmq,
            s3=masked_s3,
            model=config.model.__dict__,
            environment=config.environment
        )
    except Exception as e:
        log_with_context(logger.error, f"Error retrieving configuration: {str(e)}", {"error": str(e)})
        return create_error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@diagnostics_router.get(
    "/test",
    response_model=DiagnosticTestResponse,
    summary="Run diagnostic tests",
    description="Run diagnostic tests to verify the Document Service is functioning correctly."
)
async def run_diagnostic_tests(_: Dict = Depends(check_operations_permissions)):
    """Run diagnostic tests to verify the Document Service is functioning correctly.
    
    Args:
        _: Dependency to check operations permissions
        
    Returns:
        DiagnosticTestResponse: The results of the diagnostic tests
    """
    try:
        log_with_context(logger.info, "Running diagnostic tests")
        
        # Get application instance
        app = get_application()
        
        # System information
        system_info = {
            "python_version": sys.version,
            "platform": platform.platform(),
            "hostname": platform.node(),
            "cpu_count": os.cpu_count(),
            "memory_info": {"available": "N/A"},  # Would use psutil in a real implementation
            "uptime_seconds": int(time.time() - app.start_time) if hasattr(app, 'start_time') else 0
        }
        
        # Test RabbitMQ connection
        rabbitmq_status = await test_rabbitmq_connection(app.queue_service)
        
        # Test S3 connection
        s3_status = await test_s3_connection(app.storage_service)
        
        # Get model information
        model_info = await get_model_info(app.classification_service)
        
        # Determine overall status
        if rabbitmq_status["connected"] and s3_status["connected"] and model_info["loaded"]:
            overall_status = "healthy"
        elif not rabbitmq_status["connected"] or not s3_status["connected"]:
            overall_status = "critical"
        else:
            overall_status = "degraded"
        
        return DiagnosticTestResponse(
            timestamp=format_timestamp(datetime.now()),
            system=system_info,
            rabbitmq=ConnectionStatus(
                connected=rabbitmq_status["connected"],
                latency_ms=rabbitmq_status.get("latency_ms"),
                details=rabbitmq_status.get("details"),
                error=rabbitmq_status.get("error")
            ),
            s3=ConnectionStatus(
                connected=s3_status["connected"],
                latency_ms=s3_status.get("latency_ms"),
                details=s3_status.get("details"),
                error=s3_status.get("error")
            ),
            model=ModelStatus(
                loaded=model_info["loaded"],
                version=model_info["version"],
                accuracy=model_info["accuracy"],
                last_trained=model_info["last_trained"],
                document_types=model_info["document_types"]
            ),
            overall_status=overall_status
        )
    except Exception as e:
        log_with_context(logger.error, f"Error running diagnostic tests: {str(e)}", {"error": str(e)})
        return create_error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@diagnostics_router.post(
    "/test/rabbitmq",
    response_model=ConnectionStatus,
    summary="Test RabbitMQ connection",
    description="Test the connection to RabbitMQ and verify message publishing."
)
async def test_rabbitmq(_: Dict = Depends(check_operations_permissions)):
    """Test the connection to RabbitMQ and verify message publishing.
    
    Args:
        _: Dependency to check operations permissions
        
    Returns:
        ConnectionStatus: The status of the RabbitMQ connection
    """
    try:
        log_with_context(logger.info, "Testing RabbitMQ connection")
        
        # Get application instance
        app = get_application()
        
        # Test RabbitMQ connection
        status = await test_rabbitmq_connection(app.queue_service, test_publish=True)
        
        return ConnectionStatus(
            connected=status["connected"],
            latency_ms=status.get("latency_ms"),
            details=status.get("details"),
            error=status.get("error")
        )
    except Exception as e:
        log_with_context(logger.error, f"Error testing RabbitMQ connection: {str(e)}", {"error": str(e)})
        return create_error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@diagnostics_router.post(
    "/test/s3",
    response_model=ConnectionStatus,
    summary="Test S3 connection",
    description="Test the connection to S3 storage and verify read/write operations."
)
async def test_s3(_: Dict = Depends(check_operations_permissions)):
    """Test the connection to S3 storage and verify read/write operations.
    
    Args:
        _: Dependency to check operations permissions
        
    Returns:
        ConnectionStatus: The status of the S3 connection
    """
    try:
        log_with_context(logger.info, "Testing S3 connection")
        
        # Get application instance
        app = get_application()
        
        # Test S3 connection
        status = await test_s3_connection(app.storage_service, test_write=True)
        
        return ConnectionStatus(
            connected=status["connected"],
            latency_ms=status.get("latency_ms"),
            details=status.get("details"),
            error=status.get("error")
        )
    except Exception as e:
        log_with_context(logger.error, f"Error testing S3 connection: {str(e)}", {"error": str(e)})
        return create_error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@diagnostics_router.post(
    "/test/model",
    response_model=ModelStatus,
    summary="Test classification model",
    description="Test the document classification model and verify it's functioning correctly."
)
async def test_model(_: Dict = Depends(check_operations_permissions)):
    """Test the document classification model and verify it's functioning correctly.
    
    Args:
        _: Dependency to check operations permissions
        
    Returns:
        ModelStatus: The status of the classification model
    """
    try:
        log_with_context(logger.info, "Testing classification model")
        
        # Get application instance
        app = get_application()
        
        # Test model
        model_info = await get_model_info(app.classification_service, run_test=True)
        
        return ModelStatus(
            loaded=model_info["loaded"],
            version=model_info["version"],
            accuracy=model_info["accuracy"],
            last_trained=model_info["last_trained"],
            document_types=model_info["document_types"]
        )
    except Exception as e:
        log_with_context(logger.error, f"Error testing classification model: {str(e)}", {"error": str(e)})
        return create_error_response(str(e), status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)