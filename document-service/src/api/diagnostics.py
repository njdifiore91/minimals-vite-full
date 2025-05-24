#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Diagnostic API endpoints for the Document Service.

This module provides diagnostic endpoints for troubleshooting the Document Service.
It includes endpoints for retrieving logs, checking configuration, and performing
diagnostic tests. These endpoints are secured with JWT authentication and are
intended for use by operations staff.

Endpoints:
    - GET /diagnostics/logs: Retrieve recent logs with filtering options
    - GET /diagnostics/config: Check current service configuration
    - POST /diagnostics/test: Run diagnostic tests on the service

Security:
    All endpoints require a valid JWT token with appropriate permissions.
    Operations Staff role is required for access to these endpoints.
"""

import os
import json
import logging
import datetime
from typing import Dict, List, Optional, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# Import service-specific modules
from ..config import app_config, logging_config
from ..utils.validation_utils import validate_jwt_token

# Set up logger
logger = logging_config.get_logger(__name__)

# Create router
router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
    dependencies=[],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
        500: {"description": "Internal Server Error"}
    }
)

# Security scheme
security = HTTPBearer()


# Models for request/response
class LogEntry(BaseModel):
    """Model representing a log entry."""
    timestamp: str = Field(..., description="Log timestamp in ISO format")
    level: str = Field(..., description="Log level (ERROR, WARN, INFO, DEBUG)")
    service: str = Field(..., description="Service name")
    message: str = Field(..., description="Log message")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for request tracking")
    request_id: Optional[str] = Field(None, description="Request ID")
    environment: str = Field(..., description="Environment (development, staging, production)")
    additional_data: Optional[Dict[str, Any]] = Field(None, description="Additional log data")


class LogsResponse(BaseModel):
    """Response model for logs endpoint."""
    logs: List[LogEntry] = Field(..., description="List of log entries")
    total_count: int = Field(..., description="Total number of log entries matching filter")
    filtered_count: int = Field(..., description="Number of log entries returned after pagination")


class ConfigResponse(BaseModel):
    """Response model for configuration endpoint."""
    app_config: Dict[str, Any] = Field(..., description="Application configuration")
    environment: str = Field(..., description="Current environment")
    version: str = Field(..., description="Service version")
    dependencies: Dict[str, str] = Field(..., description="Dependency versions")


class DiagnosticTestRequest(BaseModel):
    """Request model for diagnostic test endpoint."""
    test_type: str = Field(..., description="Type of diagnostic test to run")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Test parameters")


class DiagnosticTestResult(BaseModel):
    """Model representing a diagnostic test result."""
    test_name: str = Field(..., description="Name of the test")
    status: str = Field(..., description="Test status (success, warning, failure)")
    message: str = Field(..., description="Test result message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional test details")


class DiagnosticTestResponse(BaseModel):
    """Response model for diagnostic test endpoint."""
    test_results: List[DiagnosticTestResult] = Field(..., description="List of test results")
    overall_status: str = Field(..., description="Overall test status")
    execution_time: float = Field(..., description="Test execution time in seconds")


# Authentication dependency
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verify JWT token and check if user has Operations Staff role.
    
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
        
        # Check if user has Operations Staff role
        if "roles" not in payload or "operations_staff" not in payload["roles"]:
            logger.warning(f"User {payload.get('sub', 'unknown')} attempted to access diagnostics without proper role")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions. Operations Staff role required."
            )
        
        return payload
    except Exception as e:
        logger.error(f"Authentication error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get("/logs", response_model=LogsResponse, summary="Retrieve recent logs")
async def get_logs(
    request: Request,
    level: Optional[str] = Query(None, description="Filter by log level"),
    start_time: Optional[str] = Query(None, description="Start time in ISO format"),
    end_time: Optional[str] = Query(None, description="End time in ISO format"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation ID"),
    limit: int = Query(100, description="Maximum number of logs to return"),
    offset: int = Query(0, description="Number of logs to skip"),
    token_payload: Dict = Depends(verify_token)
):
    """
    Retrieve recent logs with filtering options.
    
    This endpoint allows operations staff to retrieve and filter logs for troubleshooting.
    Logs can be filtered by level, time range, and correlation ID.
    
    Args:
        level: Filter logs by level (ERROR, WARN, INFO, DEBUG)
        start_time: Filter logs after this time (ISO format)
        end_time: Filter logs before this time (ISO format)
        correlation_id: Filter logs by correlation ID
        limit: Maximum number of logs to return
        offset: Number of logs to skip (for pagination)
        token_payload: JWT token payload from authentication
        
    Returns:
        LogsResponse: Filtered logs with pagination information
    """
    try:
        logger.info(
            f"Retrieving logs with filters: level={level}, "
            f"start_time={start_time}, end_time={end_time}, "
            f"correlation_id={correlation_id}, limit={limit}, offset={offset}"
        )
        
        # Get log file path
        log_dir = os.environ.get("LOG_DIR", "/var/log/document-service")
        log_file = os.path.join(log_dir, "document-service.log")
        
        # Check if log file exists
        if not os.path.exists(log_file):
            logger.warning(f"Log file not found: {log_file}")
            return LogsResponse(logs=[], total_count=0, filtered_count=0)
        
        # Parse and filter logs
        logs = []
        total_count = 0
        
        # Convert time strings to datetime objects if provided
        start_datetime = None
        end_datetime = None
        
        if start_time:
            start_datetime = datetime.datetime.fromisoformat(start_time)
        
        if end_time:
            end_datetime = datetime.datetime.fromisoformat(end_time)
        
        # Read log file and filter entries
        with open(log_file, "r") as f:
            for line in f:
                try:
                    # Parse JSON log entry
                    log_entry = json.loads(line)
                    total_count += 1
                    
                    # Apply filters
                    if level and log_entry.get("level") != level:
                        continue
                    
                    if correlation_id and log_entry.get("correlation_id") != correlation_id:
                        continue
                    
                    if start_datetime:
                        log_time = datetime.datetime.fromisoformat(log_entry.get("timestamp", ""))
                        if log_time < start_datetime:
                            continue
                    
                    if end_datetime:
                        log_time = datetime.datetime.fromisoformat(log_entry.get("timestamp", ""))
                        if log_time > end_datetime:
                            continue
                    
                    # Add to filtered logs (respecting pagination)
                    if len(logs) < limit and total_count > offset:
                        # Extract standard fields
                        standard_fields = {
                            "timestamp", "level", "service", "message", 
                            "correlation_id", "request_id", "environment"
                        }
                        
                        # Create log entry with standard fields
                        entry = {
                            key: log_entry.get(key, "") 
                            for key in standard_fields 
                            if key in log_entry
                        }
                        
                        # Add remaining fields as additional_data
                        additional_data = {
                            key: value 
                            for key, value in log_entry.items() 
                            if key not in standard_fields
                        }
                        
                        if additional_data:
                            entry["additional_data"] = additional_data
                        
                        logs.append(LogEntry(**entry))
                    
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue
                except Exception as e:
                    logger.error(f"Error parsing log entry: {str(e)}")
                    continue
        
        logger.info(f"Retrieved {len(logs)} logs out of {total_count} total entries")
        return LogsResponse(
            logs=logs,
            total_count=total_count,
            filtered_count=len(logs)
        )
    
    except Exception as e:
        logger.error(f"Error retrieving logs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving logs: {str(e)}"
        )


@router.get("/config", response_model=ConfigResponse, summary="Get service configuration")
async def get_config(token_payload: Dict = Depends(verify_token)):
    """
    Retrieve current service configuration.
    
    This endpoint returns the current configuration of the Document Service,
    including environment settings, version information, and dependency versions.
    Sensitive information like credentials and keys are redacted.
    
    Args:
        token_payload: JWT token payload from authentication
        
    Returns:
        ConfigResponse: Current service configuration
    """
    try:
        logger.info("Retrieving service configuration")
        
        # Get configuration (excluding sensitive information)
        config_dict = app_config.get_safe_config()
        
        # Get environment
        environment = os.environ.get("ENVIRONMENT", "development")
        
        # Get service version
        version = os.environ.get("SERVICE_VERSION", "unknown")
        
        # Get dependency versions
        dependencies = {
            "scikit-learn": _get_package_version("scikit-learn"),
            "fastapi": _get_package_version("fastapi"),
            "pydantic": _get_package_version("pydantic"),
            "pika": _get_package_version("pika"),
            "boto3": _get_package_version("boto3"),
            "python": _get_python_version()
        }
        
        logger.info(f"Retrieved configuration for environment: {environment}, version: {version}")
        return ConfigResponse(
            app_config=config_dict,
            environment=environment,
            version=version,
            dependencies=dependencies
        )
    
    except Exception as e:
        logger.error(f"Error retrieving configuration: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving configuration: {str(e)}"
        )


@router.post("/test", response_model=DiagnosticTestResponse, summary="Run diagnostic tests")
async def run_diagnostic_tests(
    request: DiagnosticTestRequest,
    token_payload: Dict = Depends(verify_token)
):
    """
    Run diagnostic tests on the Document Service.
    
    This endpoint allows operations staff to run diagnostic tests on the service
    to verify its functionality and connectivity to dependencies.
    
    Available test types:
    - "all": Run all available tests
    - "rabbitmq": Test RabbitMQ connectivity
    - "s3": Test S3 storage connectivity
    - "model": Test document classification models
    - "system": Test system resources (CPU, memory, disk)
    
    Args:
        request: Test request containing test type and parameters
        token_payload: JWT token payload from authentication
        
    Returns:
        DiagnosticTestResponse: Results of the diagnostic tests
    """
    try:
        test_type = request.test_type.lower()
        parameters = request.parameters or {}
        
        logger.info(f"Running diagnostic tests of type: {test_type} with parameters: {parameters}")
        
        # Start timer for execution time measurement
        start_time = datetime.datetime.now()
        
        # Initialize test results
        test_results = []
        
        # Run requested tests
        if test_type == "all" or test_type == "rabbitmq":
            rabbitmq_result = _test_rabbitmq_connection(parameters)
            test_results.append(rabbitmq_result)
        
        if test_type == "all" or test_type == "s3":
            s3_result = _test_s3_connection(parameters)
            test_results.append(s3_result)
        
        if test_type == "all" or test_type == "model":
            model_result = _test_classification_models(parameters)
            test_results.append(model_result)
        
        if test_type == "all" or test_type == "system":
            system_result = _test_system_resources(parameters)
            test_results.append(system_result)
        
        # Calculate execution time
        end_time = datetime.datetime.now()
        execution_time = (end_time - start_time).total_seconds()
        
        # Determine overall status
        if any(result.status == "failure" for result in test_results):
            overall_status = "failure"
        elif any(result.status == "warning" for result in test_results):
            overall_status = "warning"
        else:
            overall_status = "success"
        
        logger.info(
            f"Completed {len(test_results)} diagnostic tests with overall status: {overall_status} "
            f"in {execution_time:.2f} seconds"
        )
        
        return DiagnosticTestResponse(
            test_results=test_results,
            overall_status=overall_status,
            execution_time=execution_time
        )
    
    except Exception as e:
        logger.error(f"Error running diagnostic tests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running diagnostic tests: {str(e)}"
        )


# Helper functions
def _get_package_version(package_name: str) -> str:
    """
    Get the version of an installed Python package.
    
    Args:
        package_name: Name of the package
        
    Returns:
        str: Package version or "not installed" if not found
    """
    try:
        import importlib.metadata
        return importlib.metadata.version(package_name)
    except (ImportError, importlib.metadata.PackageNotFoundError):
        try:
            # Fallback for Python < 3.8
            import pkg_resources
            return pkg_resources.get_distribution(package_name).version
        except (ImportError, pkg_resources.DistributionNotFound):
            return "not installed"


def _get_python_version() -> str:
    """
    Get the current Python version.
    
    Returns:
        str: Python version
    """
    import sys
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def _test_rabbitmq_connection(parameters: Dict[str, Any]) -> DiagnosticTestResult:
    """
    Test RabbitMQ connection and functionality.
    
    Args:
        parameters: Test parameters
        
    Returns:
        DiagnosticTestResult: Test result
    """
    try:
        from ..utils.rabbitmq_utils import test_connection
        
        # Test connection with timeout
        timeout = parameters.get("timeout", 5)  # Default 5 seconds timeout
        connection_result = test_connection(timeout=timeout)
        
        if connection_result["connected"]:
            return DiagnosticTestResult(
                test_name="RabbitMQ Connection",
                status="success",
                message="Successfully connected to RabbitMQ",
                details=connection_result
            )
        else:
            return DiagnosticTestResult(
                test_name="RabbitMQ Connection",
                status="failure",
                message=f"Failed to connect to RabbitMQ: {connection_result['error']}",
                details=connection_result
            )
    
    except Exception as e:
        logger.error(f"Error testing RabbitMQ connection: {str(e)}")
        return DiagnosticTestResult(
            test_name="RabbitMQ Connection",
            status="failure",
            message=f"Error testing RabbitMQ connection: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )


def _test_s3_connection(parameters: Dict[str, Any]) -> DiagnosticTestResult:
    """
    Test S3 storage connection and functionality.
    
    Args:
        parameters: Test parameters
        
    Returns:
        DiagnosticTestResult: Test result
    """
    try:
        from ..utils.s3_utils import test_connection
        
        # Test connection with timeout
        timeout = parameters.get("timeout", 5)  # Default 5 seconds timeout
        connection_result = test_connection(timeout=timeout)
        
        if connection_result["connected"]:
            return DiagnosticTestResult(
                test_name="S3 Storage Connection",
                status="success",
                message="Successfully connected to S3 storage",
                details=connection_result
            )
        else:
            return DiagnosticTestResult(
                test_name="S3 Storage Connection",
                status="failure",
                message=f"Failed to connect to S3 storage: {connection_result['error']}",
                details=connection_result
            )
    
    except Exception as e:
        logger.error(f"Error testing S3 connection: {str(e)}")
        return DiagnosticTestResult(
            test_name="S3 Storage Connection",
            status="failure",
            message=f"Error testing S3 connection: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )


def _test_classification_models(parameters: Dict[str, Any]) -> DiagnosticTestResult:
    """
    Test document classification models.
    
    Args:
        parameters: Test parameters
        
    Returns:
        DiagnosticTestResult: Test result
    """
    try:
        from ..utils.ml_utils import test_models
        
        # Test models with sample data if provided
        sample_data = parameters.get("sample_data", None)
        model_result = test_models(sample_data=sample_data)
        
        if model_result["loaded"] and model_result["functional"]:
            return DiagnosticTestResult(
                test_name="Classification Models",
                status="success",
                message="Classification models loaded and functional",
                details=model_result
            )
        elif model_result["loaded"] and not model_result["functional"]:
            return DiagnosticTestResult(
                test_name="Classification Models",
                status="warning",
                message="Classification models loaded but test prediction failed",
                details=model_result
            )
        else:
            return DiagnosticTestResult(
                test_name="Classification Models",
                status="failure",
                message="Failed to load classification models",
                details=model_result
            )
    
    except Exception as e:
        logger.error(f"Error testing classification models: {str(e)}")
        return DiagnosticTestResult(
            test_name="Classification Models",
            status="failure",
            message=f"Error testing classification models: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )


def _test_system_resources(parameters: Dict[str, Any]) -> DiagnosticTestResult:
    """
    Test system resources (CPU, memory, disk).
    
    Args:
        parameters: Test parameters
        
    Returns:
        DiagnosticTestResult: Test result
    """
    try:
        import psutil
        import os
        
        # Get CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Get disk usage for the log directory
        log_dir = os.environ.get("LOG_DIR", "/var/log/document-service")
        disk = psutil.disk_usage(log_dir)
        disk_percent = disk.percent
        
        # Get open file descriptors
        open_files = len(psutil.Process().open_files())
        
        # Check if any resource is above warning threshold
        cpu_warning = parameters.get("cpu_warning_threshold", 80)
        memory_warning = parameters.get("memory_warning_threshold", 80)
        disk_warning = parameters.get("disk_warning_threshold", 80)
        
        details = {
            "cpu": {
                "percent": cpu_percent,
                "warning_threshold": cpu_warning
            },
            "memory": {
                "percent": memory_percent,
                "total_gb": memory.total / (1024 ** 3),
                "available_gb": memory.available / (1024 ** 3),
                "warning_threshold": memory_warning
            },
            "disk": {
                "percent": disk_percent,
                "total_gb": disk.total / (1024 ** 3),
                "free_gb": disk.free / (1024 ** 3),
                "path": log_dir,
                "warning_threshold": disk_warning
            },
            "open_files": open_files
        }
        
        # Determine status based on thresholds
        if cpu_percent > cpu_warning or memory_percent > memory_warning or disk_percent > disk_warning:
            status = "warning"
            message = "System resources approaching critical levels"
        else:
            status = "success"
            message = "System resources within normal parameters"
        
        return DiagnosticTestResult(
            test_name="System Resources",
            status=status,
            message=message,
            details=details
        )
    
    except Exception as e:
        logger.error(f"Error testing system resources: {str(e)}")
        return DiagnosticTestResult(
            test_name="System Resources",
            status="failure",
            message=f"Error testing system resources: {str(e)}",
            details={"error": str(e), "error_type": type(e).__name__}
        )