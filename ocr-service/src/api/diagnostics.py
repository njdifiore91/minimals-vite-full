from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Dict, List, Optional, Any
import logging
import os
import time
from datetime import datetime, timedelta

# Import from local modules
from ..config import app_config, tensorflow_config, logging_config
from ..services import ocr_service
from ..types.models import OCRModelType, ModelMetrics
from ..types.errors import ServiceError, ErrorCategory
from ..utils import logging_utils, tensorflow_utils, error_utils

# Create router with prefix
router = APIRouter(
    prefix="/diagnostics",
    tags=["diagnostics"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Unauthorized"},
        status.HTTP_403_FORBIDDEN: {"description": "Forbidden"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal Server Error"},
    },
)

# Logger for this module
logger = logging.getLogger(__name__)


# Authentication dependency
async def verify_admin_access():
    """Verify that the user has admin access for diagnostics endpoints.
    
    This is a placeholder for actual authentication logic that would be implemented
    based on the authentication system used (JWT, API key, etc.)
    
    Raises:
        HTTPException: If authentication fails or user lacks required permissions
    """
    # TODO: Implement actual authentication check
    # For now, this is a placeholder that allows access
    # In production, this would verify JWT tokens or API keys
    return True


@router.get("/logs", summary="Retrieve recent logs")
async def get_logs(
    level: str = Query("INFO", description="Log level filter (ERROR, WARN, INFO, DEBUG)"),
    hours: int = Query(24, description="Hours of logs to retrieve", ge=1, le=72),
    service: Optional[str] = Query(None, description="Filter logs by service component"),
    limit: int = Query(100, description="Maximum number of log entries to return", ge=10, le=1000),
    _: bool = Depends(verify_admin_access),
) -> Dict[str, Any]:
    """Retrieve recent logs from the OCR service.
    
    This endpoint allows operations staff to view recent logs for troubleshooting.
    Logs can be filtered by level, time range, and service component.
    
    Args:
        level: Minimum log level to include (ERROR, WARN, INFO, DEBUG)
        hours: Number of hours of logs to retrieve (1-72)
        service: Optional service component filter
        limit: Maximum number of log entries to return (10-1000)
        _: Admin access verification dependency
        
    Returns:
        Dict containing log entries and metadata
    """
    try:
        logger.info(f"Retrieving logs with level={level}, hours={hours}, service={service}, limit={limit}")
        
        # Convert level string to logging level
        numeric_level = logging_utils.get_log_level(level)
        if not numeric_level:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid log level: {level}. Must be one of ERROR, WARN, INFO, DEBUG"
            )
        
        # Calculate time range
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=hours)
        
        # Retrieve logs from the logging system
        # This implementation will depend on how logs are stored
        # (file, database, external service, etc.)
        log_entries = logging_utils.get_log_entries(
            start_time=start_time,
            end_time=end_time,
            level=numeric_level,
            service=service,
            limit=limit
        )
        
        return {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "hours": hours,
            "service": service,
            "count": len(log_entries),
            "logs": log_entries
        }
    except Exception as e:
        error = error_utils.format_exception(e, ErrorCategory.SYSTEM)
        logger.error(f"Error retrieving logs: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logs: {str(e)}"
        )


@router.get("/config", summary="Get current configuration")
async def get_config(_: bool = Depends(verify_admin_access)) -> Dict[str, Any]:
    """Retrieve the current configuration of the OCR service.
    
    This endpoint returns the current configuration settings for the OCR service,
    excluding sensitive information like credentials.
    
    Args:
        _: Admin access verification dependency
        
    Returns:
        Dict containing configuration settings
    """
    try:
        logger.info("Retrieving current configuration")
        
        # Get configuration but exclude sensitive information
        config = app_config.get_sanitized_config()
        
        # Add TensorFlow configuration
        tf_config = tensorflow_config.get_sanitized_config()
        
        # Add logging configuration
        log_config = logging_config.get_sanitized_config()
        
        # Add environment information
        env_info = {
            "environment": os.environ.get("ENVIRONMENT", "development"),
            "python_version": os.environ.get("PYTHON_VERSION", "unknown"),
            "hostname": os.environ.get("HOSTNAME", "unknown"),
            "service_version": os.environ.get("SERVICE_VERSION", "unknown"),
        }
        
        return {
            "timestamp": datetime.now().isoformat(),
            "app_config": config,
            "tensorflow_config": tf_config,
            "logging_config": log_config,
            "environment": env_info
        }
    except Exception as e:
        error = error_utils.format_exception(e, ErrorCategory.SYSTEM)
        logger.error(f"Error retrieving configuration: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve configuration: {str(e)}"
        )


@router.get("/test", summary="Run diagnostic tests")
async def run_diagnostics(
    test_type: str = Query("basic", description="Type of diagnostic test to run (basic, full, gpu, models)"),
    _: bool = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Run diagnostic tests on the OCR service.
    
    This endpoint runs various diagnostic tests to verify the health and functionality
    of the OCR service components.
    
    Args:
        test_type: Type of diagnostic test to run (basic, full, gpu, models)
        _: Admin access verification dependency
        
    Returns:
        Dict containing test results
    """
    try:
        logger.info(f"Running diagnostic tests: {test_type}")
        start_time = time.time()
        results = {}
        
        # Basic system diagnostics
        if test_type in ["basic", "full"]:
            results["system"] = {
                "cpu": tensorflow_utils.check_cpu_info(),
                "memory": tensorflow_utils.check_memory_info(),
                "disk": tensorflow_utils.check_disk_info(),
                "python": tensorflow_utils.check_python_info(),
            }
        
        # GPU diagnostics
        if test_type in ["gpu", "full"]:
            results["gpu"] = tensorflow_utils.check_gpu_info()
        
        # Model diagnostics
        if test_type in ["models", "full"]:
            results["models"] = {
                "loaded": tensorflow_utils.check_loaded_models(),
                "performance": tensorflow_utils.check_model_performance(),
            }
        
        # Service connectivity tests
        if test_type == "full":
            results["connectivity"] = {
                "rabbitmq": tensorflow_utils.check_rabbitmq_connectivity(),
                "s3": tensorflow_utils.check_s3_connectivity(),
            }
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        return {
            "timestamp": datetime.now().isoformat(),
            "test_type": test_type,
            "execution_time": execution_time,
            "results": results
        }
    except Exception as e:
        error = error_utils.format_exception(e, ErrorCategory.SYSTEM)
        logger.error(f"Error running diagnostics: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run diagnostics: {str(e)}"
        )


@router.get("/models", summary="Get information about loaded OCR models")
async def get_models(_: bool = Depends(verify_admin_access)) -> Dict[str, Any]:
    """Retrieve information about the currently loaded OCR models.
    
    This endpoint returns details about the OCR models currently loaded in the service,
    including model types, versions, and performance metrics.
    
    Args:
        _: Admin access verification dependency
        
    Returns:
        Dict containing model information
    """
    try:
        logger.info("Retrieving model information")
        
        # Get information about loaded models
        models_info = ocr_service.get_models_info()
        
        # Get model performance metrics
        performance_metrics = ocr_service.get_model_metrics()
        
        # Get model usage statistics
        usage_stats = ocr_service.get_model_usage_stats()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "models": models_info,
            "performance": performance_metrics,
            "usage": usage_stats
        }
    except Exception as e:
        error = error_utils.format_exception(e, ErrorCategory.SYSTEM)
        logger.error(f"Error retrieving model information: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve model information: {str(e)}"
        )


@router.post("/models/reload", summary="Reload OCR models")
async def reload_models(
    model_type: Optional[OCRModelType] = Query(None, description="Specific model type to reload (TYPED, HANDWRITTEN, HYBRID)"),
    _: bool = Depends(verify_admin_access)
) -> Dict[str, Any]:
    """Reload OCR models used by the service.
    
    This endpoint triggers a reload of the specified OCR models or all models if
    no specific type is provided. This is useful for updating models without
    restarting the service.
    
    Args:
        model_type: Optional specific model type to reload
        _: Admin access verification dependency
        
    Returns:
        Dict containing reload status and information
    """
    try:
        if model_type:
            logger.info(f"Reloading OCR model: {model_type}")
            # Reload specific model type
            result = ocr_service.reload_model(model_type)
        else:
            logger.info("Reloading all OCR models")
            # Reload all models
            result = ocr_service.reload_all_models()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "model_type": model_type.value if model_type else "all",
            "success": result["success"],
            "message": result["message"],
            "models": result["models"]
        }
    except Exception as e:
        error = error_utils.format_exception(e, ErrorCategory.SYSTEM)
        logger.error(f"Error reloading models: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reload models: {str(e)}"
        )


@router.get("/health", summary="Check diagnostics subsystem health")
async def check_health() -> Dict[str, Any]:
    """Check the health of the diagnostics subsystem.
    
    This endpoint verifies that the diagnostics subsystem is functioning correctly.
    It does not require admin access as it's used for basic health monitoring.
    
    Returns:
        Dict containing health status information
    """
    try:
        # Perform basic health check of diagnostics subsystem
        return {
            "timestamp": datetime.now().isoformat(),
            "status": "healthy",
            "message": "Diagnostics subsystem is functioning correctly"
        }
    except Exception as e:
        logger.error(f"Diagnostics health check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagnostics health check failed: {str(e)}"
        )