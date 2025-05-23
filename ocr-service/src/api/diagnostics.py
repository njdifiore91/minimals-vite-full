"""Diagnostic endpoints for troubleshooting the OCR Service.

This module provides endpoints for retrieving logs, checking configuration,
and performing diagnostic tests on OCR models. These endpoints are used by
operations staff to troubleshoot issues with the service, verify its
configuration, and test OCR functionality.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query, Body, File, UploadFile
from pydantic import BaseModel

from ..config import app_config, tensorflow_config, logging_config
from ..services import ocr_service
from ..models import model_factory
from ..utils import error_utils, logging_utils
from ..auth.jwt_auth import validate_api_key, validate_admin_role

# Initialize logger
logger = logging.getLogger(__name__)

# Create router
diagnostics_router = APIRouter(tags=["diagnostics"])


# Define request models
class DiagnosticTestRequest(BaseModel):
    """Request model for diagnostic tests."""
    test_type: str
    parameters: Optional[Dict[str, Any]] = None


class ModelReloadRequest(BaseModel):
    """Request model for model reloading."""
    model_ids: Optional[List[str]] = None
    force: bool = False


@diagnostics_router.get("/logs", summary="Retrieve recent logs", dependencies=[Depends(validate_api_key)])
async def get_logs(
    level: str = Query("INFO", description="Minimum log level to retrieve"),
    hours: int = Query(24, description="Number of hours of logs to retrieve"),
    service: Optional[str] = Query(None, description="Filter logs by service component"),
    limit: int = Query(1000, description="Maximum number of log entries to return")
) -> Dict[str, Any]:
    """Retrieve recent logs from the OCR Service.
    
    This endpoint allows operations staff to retrieve and filter logs for troubleshooting.
    
    Args:
        level: Minimum log level to retrieve (DEBUG, INFO, WARN, ERROR)
        hours: Number of hours of logs to retrieve
        service: Filter logs by service component
        limit: Maximum number of log entries to return
        
    Returns:
        Dict[str, Any]: A dictionary containing filtered logs
    """
    try:
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        if level not in valid_levels:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid log level. Must be one of: {', '.join(valid_levels)}"
            )
        
        # Get numeric log level
        numeric_level = getattr(logging, level)
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Get log file path from config
        log_file = logging_config.LOG_FILE
        
        # Check if log file exists
        if not os.path.exists(log_file):
            return {
                "status": "error",
                "message": f"Log file not found: {log_file}",
                "logs": []
            }
        
        # Parse and filter logs
        logs = []
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    # Parse log entry
                    log_entry = logging_utils.parse_log_entry(line)
                    
                    # Apply filters
                    if log_entry:
                        # Filter by level
                        if getattr(logging, log_entry.get("level", "INFO")) < numeric_level:
                            continue
                        
                        # Filter by time
                        log_time = datetime.fromisoformat(log_entry.get("timestamp", "").replace('Z', '+00:00'))
                        if log_time < start_time or log_time > end_time:
                            continue
                        
                        # Filter by service
                        if service and log_entry.get("service") != service:
                            continue
                        
                        logs.append(log_entry)
                        
                        # Limit number of logs
                        if len(logs) >= limit:
                            break
                except Exception as e:
                    # Skip malformed log entries
                    continue
        
        return {
            "status": "success",
            "count": len(logs),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "level": level,
            "service_filter": service,
            "logs": logs
        }
    
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"Error retrieving logs: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving logs: {str(e)}"
        )


@diagnostics_router.get("/config", summary="Check current configuration", dependencies=[Depends(validate_api_key)])
async def get_config() -> Dict[str, Any]:
    """Retrieve the current configuration of the OCR Service.
    
    This endpoint allows operations staff to check the current configuration
    settings of the service for troubleshooting purposes.
    
    Returns:
        Dict[str, Any]: A dictionary containing configuration settings
    """
    try:
        # Create sanitized configuration object
        # Remove sensitive information like credentials
        sanitized_config = {
            "app": {
                "service_name": app_config.SERVICE_NAME,
                "version": app_config.SERVICE_VERSION,
                "environment": app_config.ENVIRONMENT,
                "debug_mode": app_config.DEBUG_MODE,
                "api_base_path": app_config.API_BASE_PATH,
                "host": app_config.HOST,
                "port": app_config.PORT,
            },
            "tensorflow": {
                "model_path": tensorflow_config.MODEL_PATH,
                "model_version": tensorflow_config.MODEL_VERSION,
                "gpu_enabled": tensorflow_config.GPU_ENABLED,
                "min_gpu_memory_mb": tensorflow_config.MIN_GPU_MEMORY_MB,
                "confidence_threshold": tensorflow_config.CONFIDENCE_THRESHOLD,
                "batch_size": tensorflow_config.BATCH_SIZE,
                "supported_document_types": tensorflow_config.SUPPORTED_DOCUMENT_TYPES,
            },
            "rabbitmq": {
                "host": app_config.RABBITMQ_HOST,
                "port": app_config.RABBITMQ_PORT,
                "exchange": app_config.RABBITMQ_EXCHANGE,
                "queue": app_config.RABBITMQ_QUEUE,
                "routing_key": app_config.RABBITMQ_ROUTING_KEY,
                "prefetch_count": app_config.RABBITMQ_PREFETCH_COUNT,
                # Credentials are intentionally omitted
            },
            "s3": {
                "endpoint": app_config.S3_ENDPOINT,
                "region": app_config.S3_REGION,
                "bucket": app_config.S3_BUCKET,
                "use_ssl": app_config.S3_USE_SSL,
                # Credentials are intentionally omitted
            },
            "logging": {
                "level": logging_config.LOG_LEVEL,
                "format": logging_config.LOG_FORMAT,
                "file": logging_config.LOG_FILE,
                "max_size_mb": logging_config.LOG_MAX_SIZE_MB,
                "backup_count": logging_config.LOG_BACKUP_COUNT,
            }
        }
        
        return {
            "status": "success",
            "config": sanitized_config
        }
    
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"Error retrieving configuration: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving configuration: {str(e)}"
        )


@diagnostics_router.post("/test", summary="Run diagnostic tests", dependencies=[Depends(validate_api_key)])
async def run_diagnostic_test(
    test_request: DiagnosticTestRequest = Body(...),
    test_file: Optional[UploadFile] = File(None)
) -> Dict[str, Any]:
    """Run diagnostic tests on the OCR Service.
    
    This endpoint allows operations staff to run various diagnostic tests
    to verify the functionality of the OCR Service.
    
    Args:
        test_request: Test configuration including test type and parameters
        test_file: Optional test file for OCR processing tests
        
    Returns:
        Dict[str, Any]: A dictionary containing test results
    """
    try:
        # Validate test type
        valid_test_types = ["ocr", "connectivity", "performance", "model"]
        if test_request.test_type not in valid_test_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid test type. Must be one of: {', '.join(valid_test_types)}"
            )
        
        # Initialize test results
        test_results = {
            "test_type": test_request.test_type,
            "timestamp": datetime.now().isoformat(),
            "parameters": test_request.parameters or {},
            "results": {},
            "status": "pending"
        }
        
        # Run the appropriate test based on test type
        if test_request.test_type == "ocr":
            # Validate test file for OCR test
            if not test_file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Test file is required for OCR tests"
                )
            
            # Process test file with OCR
            test_results["results"] = await ocr_service.run_diagnostic_ocr(
                test_file,
                test_request.parameters
            )
            
        elif test_request.test_type == "connectivity":
            # Test connectivity to dependencies
            test_results["results"] = await ocr_service.test_connectivity()
            
        elif test_request.test_type == "performance":
            # Run performance tests
            test_results["results"] = await ocr_service.run_performance_test(
                test_request.parameters
            )
            
        elif test_request.test_type == "model":
            # Test model loading and inference
            test_results["results"] = await ocr_service.test_model(
                test_request.parameters
            )
        
        # Update test status
        test_results["status"] = "success"
        
        return test_results
    
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"Error running diagnostic test: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error running diagnostic test: {str(e)}"
        )


@diagnostics_router.get("/models", summary="Check loaded OCR models", dependencies=[Depends(validate_api_key)])
async def get_models() -> Dict[str, Any]:
    """Retrieve information about currently loaded OCR models.
    
    This endpoint allows operations staff to check which OCR models are
    currently loaded and their status.
    
    Returns:
        Dict[str, Any]: A dictionary containing model information
    """
    try:
        # Get model information from model factory
        models_info = await model_factory.get_models_info()
        
        return {
            "status": "success",
            "models": models_info
        }
    
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"Error retrieving model information: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving model information: {str(e)}"
        )


@diagnostics_router.post("/models/reload", summary="Reload OCR models", dependencies=[Depends(validate_admin_role)])
async def reload_models(reload_request: ModelReloadRequest = Body(...)) -> Dict[str, Any]:
    """Reload OCR models used by the service.
    
    This endpoint allows administrators to reload OCR models, either
    specific models or all models.
    
    Args:
        reload_request: Model reload configuration
        
    Returns:
        Dict[str, Any]: A dictionary containing reload results
    """
    try:
        # Log the reload request
        logger.info(f"Model reload requested by admin. Force: {reload_request.force}, Models: {reload_request.model_ids or 'all'}")
        
        # Reload models
        reload_results = await model_factory.reload_models(
            model_ids=reload_request.model_ids,
            force=reload_request.force
        )
        
        return {
            "status": "success",
            "message": "Models reloaded successfully",
            "results": reload_results
        }
    
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"Error reloading models: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error reloading models: {str(e)}"
        )


@diagnostics_router.get("/system", summary="Get system diagnostics", dependencies=[Depends(validate_api_key)])
async def get_system_diagnostics() -> Dict[str, Any]:
    """Retrieve system diagnostic information.
    
    This endpoint provides detailed system information for troubleshooting,
    including environment variables, Python version, and installed packages.
    
    Returns:
        Dict[str, Any]: A dictionary containing system diagnostic information
    """
    try:
        import sys
        import platform
        import pkg_resources
        
        # Get system information
        system_info = {
            "python": {
                "version": sys.version,
                "executable": sys.executable,
                "platform": platform.platform(),
            },
            "packages": [
                {"name": pkg.key, "version": pkg.version}
                for pkg in pkg_resources.working_set
            ],
            "environment": {
                # Filter environment variables to exclude sensitive information
                key: value for key, value in os.environ.items()
                if not any(sensitive in key.lower() for sensitive in [
                    "key", "secret", "password", "token", "credential"
                ])
            }
        }
        
        return {
            "status": "success",
            "system": system_info
        }
    
    except Exception as e:
        error = error_utils.format_exception(e)
        logger.error(f"Error retrieving system diagnostics: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving system diagnostics: {str(e)}"
        )