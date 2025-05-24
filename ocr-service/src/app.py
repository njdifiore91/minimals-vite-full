#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core application setup module for the OCR Service.

This module configures the OCR Service components and provides the main application instance.
It initializes the logger, loads configuration, and creates service instances for OCR processing,
queue management, and storage. This file is the central hub that connects all service components together.
"""

import logging
import os
import sys
from typing import Dict, Optional, Any

import fastapi
from fastapi import FastAPI, Depends, HTTPException, status

# Import configuration modules
from config import app_config, logging_config, rabbitmq_config, s3_config, tensorflow_config

# Import service modules
from services import OCRService, QueueService, StorageService
from services.confidence_service import ConfidenceService
from services.field_extraction_service import FieldExtractionService

# Import API routers
from api import router as api_router

# Import type definitions
from types.config import ServiceConfig
from types.errors import ServiceError, ErrorCategory


class OCRApplication:
    """
    Main application class for the OCR Service.
    
    This class manages the lifecycle of the OCR Service, including initialization,
    startup, and shutdown. It creates and configures all required service components
    and provides the FastAPI application instance.
    """
    
    def __init__(self):
        """
        Initialize the OCR Application.
        
        Sets up logging, loads configuration, and creates service instances.
        Does not start any services or connections - use start() for that.
        """
        self.logger = self._setup_logging()
        self.logger.info("Initializing OCR Service application")
        
        # Load and validate configuration
        self.config = self._load_config()
        self.logger.info(f"Loaded configuration for environment: {self.config.environment}")
        
        # Create FastAPI application
        self.app = self._create_fastapi_app()
        
        # Initialize service instances (but don't start connections yet)
        self.storage_service = None
        self.queue_service = None
        self.ocr_service = None
        self.field_extraction_service = None
        self.confidence_service = None
        
        self.logger.info("OCR Service application initialized")
    
    def _setup_logging(self) -> logging.Logger:
        """
        Set up the logging system for the OCR Service.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        # Get log level from environment or use default
        log_level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_name, logging.INFO)
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format=logging_config.LOG_FORMAT,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Create and return logger for this module
        logger = logging.getLogger("ocr_service")
        logger.setLevel(log_level)
        
        return logger
    
    def _load_config(self) -> ServiceConfig:
        """
        Load and validate configuration from environment variables.
        
        Returns:
            ServiceConfig: Validated configuration object
        
        Raises:
            ServiceError: If required configuration is missing or invalid
        """
        try:
            # Load application configuration
            config = app_config.load_config()
            
            # Validate required configuration
            self._validate_config(config)
            
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise ServiceError(
                message="Failed to load configuration",
                category=ErrorCategory.CONFIGURATION,
                details={"error": str(e)}
            )
    
    def _validate_config(self, config: ServiceConfig) -> None:
        """
        Validate that all required configuration is present and valid.
        
        Args:
            config: ServiceConfig object to validate
        
        Raises:
            ServiceError: If required configuration is missing or invalid
        """
        # Check for required TensorFlow configuration
        if not config.tensorflow or not config.tensorflow.model_path:
            raise ServiceError(
                message="TensorFlow model path not configured",
                category=ErrorCategory.CONFIGURATION,
                details={"missing": "tensorflow.model_path"}
            )
        
        # Check for required RabbitMQ configuration
        if not config.rabbitmq or not config.rabbitmq.host:
            raise ServiceError(
                message="RabbitMQ host not configured",
                category=ErrorCategory.CONFIGURATION,
                details={"missing": "rabbitmq.host"}
            )
        
        # Check for required S3 configuration
        if not config.s3 or not config.s3.endpoint:
            raise ServiceError(
                message="S3 endpoint not configured",
                category=ErrorCategory.CONFIGURATION,
                details={"missing": "s3.endpoint"}
            )
    
    def _create_fastapi_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application.
        
        Returns:
            FastAPI: Configured FastAPI application instance
        """
        app = FastAPI(
            title="OCR Service",
            description="Merchant Cash Advance OCR Service for document data extraction",
            version="1.0.0",
            docs_url="/docs" if os.environ.get("ENVIRONMENT", "development") != "production" else None,
            redoc_url="/redoc" if os.environ.get("ENVIRONMENT", "development") != "production" else None,
        )
        
        # Add API router
        app.include_router(api_router)
        
        # Add startup and shutdown event handlers
        app.add_event_handler("startup", self.start)
        app.add_event_handler("shutdown", self.stop)
        
        # Add exception handlers
        app.add_exception_handler(ServiceError, self._handle_service_error)
        app.add_exception_handler(Exception, self._handle_general_exception)
        
        return app
    
    async def _handle_service_error(self, request: fastapi.Request, exc: ServiceError) -> fastapi.responses.JSONResponse:
        """
        Handle ServiceError exceptions and return appropriate HTTP responses.
        
        Args:
            request: FastAPI request object
            exc: ServiceError exception
        
        Returns:
            JSONResponse: Formatted error response
        """
        self.logger.error(f"Service error: {exc.message}", extra={"details": exc.details, "category": exc.category})
        
        # Map error categories to HTTP status codes
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        if exc.category == ErrorCategory.VALIDATION:
            status_code = status.HTTP_400_BAD_REQUEST
        elif exc.category == ErrorCategory.AUTHENTICATION:
            status_code = status.HTTP_401_UNAUTHORIZED
        elif exc.category == ErrorCategory.AUTHORIZATION:
            status_code = status.HTTP_403_FORBIDDEN
        elif exc.category == ErrorCategory.NOT_FOUND:
            status_code = status.HTTP_404_NOT_FOUND
        
        return fastapi.responses.JSONResponse(
            status_code=status_code,
            content={
                "error": exc.message,
                "category": exc.category,
                "details": exc.details
            }
        )
    
    async def _handle_general_exception(self, request: fastapi.Request, exc: Exception) -> fastapi.responses.JSONResponse:
        """
        Handle general exceptions and return appropriate HTTP responses.
        
        Args:
            request: FastAPI request object
            exc: Exception instance
        
        Returns:
            JSONResponse: Formatted error response
        """
        self.logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
        
        return fastapi.responses.JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "details": str(exc) if os.environ.get("ENVIRONMENT", "development") != "production" else None
            }
        )
    
    async def start(self) -> None:
        """
        Start the OCR Service and initialize all connections.
        
        This method is called during FastAPI startup and initializes all service
        components, including storage, queue, and OCR processing services.
        """
        self.logger.info("Starting OCR Service")
        
        try:
            # Initialize storage service
            self.logger.info("Initializing storage service")
            self.storage_service = StorageService(
                config=s3_config.get_s3_config(self.config),
                logger=logging.getLogger("ocr_service.storage")
            )
            await self.storage_service.connect()
            
            # Initialize queue service
            self.logger.info("Initializing queue service")
            self.queue_service = QueueService(
                config=rabbitmq_config.get_rabbitmq_config(self.config),
                logger=logging.getLogger("ocr_service.queue")
            )
            await self.queue_service.connect()
            
            # Initialize confidence service
            self.logger.info("Initializing confidence service")
            self.confidence_service = ConfidenceService(
                config=self.config,
                logger=logging.getLogger("ocr_service.confidence")
            )
            
            # Initialize field extraction service
            self.logger.info("Initializing field extraction service")
            self.field_extraction_service = FieldExtractionService(
                config=self.config,
                logger=logging.getLogger("ocr_service.field_extraction")
            )
            
            # Initialize OCR service
            self.logger.info("Initializing OCR service")
            self.ocr_service = OCRService(
                config=tensorflow_config.get_tensorflow_config(self.config),
                storage_service=self.storage_service,
                queue_service=self.queue_service,
                confidence_service=self.confidence_service,
                field_extraction_service=self.field_extraction_service,
                logger=logging.getLogger("ocr_service.ocr")
            )
            await self.ocr_service.initialize()
            
            # Start processing
            self.logger.info("Starting OCR processing")
            await self.ocr_service.start_processing()
            
            self.logger.info("OCR Service started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start OCR Service: {str(e)}", exc_info=True)
            # Re-raise to prevent FastAPI from starting with incomplete initialization
            raise
    
    async def stop(self) -> None:
        """
        Stop the OCR Service and close all connections.
        
        This method is called during FastAPI shutdown and ensures that all
        connections are properly closed and resources are released.
        """
        self.logger.info("Stopping OCR Service")
        
        # Stop services in reverse order of initialization
        if self.ocr_service:
            self.logger.info("Stopping OCR service")
            try:
                await self.ocr_service.stop_processing()
            except Exception as e:
                self.logger.error(f"Error stopping OCR service: {str(e)}")
        
        if self.queue_service:
            self.logger.info("Closing queue connection")
            try:
                await self.queue_service.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting from queue: {str(e)}")
        
        if self.storage_service:
            self.logger.info("Closing storage connection")
            try:
                await self.storage_service.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting from storage: {str(e)}")
        
        self.logger.info("OCR Service stopped")


# Create the application instance
app_instance = OCRApplication()

# Export the FastAPI app for ASGI servers
app = app_instance.app


# Health check endpoints for Kubernetes probes
@app.get("/health/liveness", tags=["health"])
async def liveness_probe():
    """
    Liveness probe for Kubernetes.
    
    This endpoint verifies that the application is running and responsive.
    It does not check dependencies, only that the application itself is alive.
    
    Returns:
        dict: Status information
    """
    return {"status": "alive", "service": "ocr-service"}


@app.get("/health/readiness", tags=["health"])
async def readiness_probe():
    """
    Readiness probe for Kubernetes.
    
    This endpoint verifies that the application is ready to accept traffic.
    It checks that all dependencies (RabbitMQ, S3, GPU) are available and
    the service is fully initialized.
    
    Returns:
        dict: Status information with dependency checks
    
    Raises:
        HTTPException: If the service is not ready
    """
    # Check if services are initialized
    if not app_instance.ocr_service or not app_instance.queue_service or not app_instance.storage_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service is starting up"
        )
    
    # Check service health
    health_status = {
        "status": "ready",
        "service": "ocr-service",
        "dependencies": {
            "rabbitmq": "healthy" if app_instance.queue_service.is_connected() else "unhealthy",
            "storage": "healthy" if app_instance.storage_service.is_connected() else "unhealthy",
            "gpu": "healthy" if app_instance.ocr_service.is_gpu_available() else "unhealthy"
        }
    }
    
    # If any dependency is unhealthy, return 503
    if any(status != "healthy" for status in health_status["dependencies"].values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    return health_status