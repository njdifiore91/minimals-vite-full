#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service Application Module

This module provides the main application class for the Document Service microservice.
It initializes all required components, loads configuration, and manages the service lifecycle.

The Document Service is responsible for classifying incoming documents with 99% accuracy
using scikit-learn models (SVM and Random Forest) and routing them to appropriate OCR processors.
"""

import logging
import os
import signal
import sys
from typing import Dict, Optional, Any

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import configuration modules
from config import app_config, rabbitmq_config, model_config
from config.app_config import AppConfig

# Import service components
from services.classification_service import ClassificationService
from services.queue_service import QueueService
from services.storage_service import StorageService
from services.document_routing_service import DocumentRoutingService

# Import API routers
from api import router as api_router


class DocumentServiceApp:
    """
    Main application class for the Document Service microservice.
    
    This class manages the lifecycle of the Document Service, including initialization,
    configuration loading, service creation, and graceful shutdown.
    """
    
    def __init__(self):
        """
        Initialize the Document Service application.
        
        Sets up logging, loads configuration, and creates service instances.
        """
        self.logger = self._setup_logging()
        self.logger.info("Initializing Document Service application")
        
        # Load configuration
        self.config = self._load_config()
        self.logger.info(f"Loaded configuration for environment: {self.config.environment}")
        
        # Create FastAPI application
        self.app = self._create_fastapi_app()
        
        # Initialize services
        self.queue_service = None
        self.storage_service = None
        self.classification_service = None
        self.document_routing_service = None
        
        # Flag to track if the application is running
        self.is_running = False
    
    def _setup_logging(self) -> logging.Logger:
        """
        Set up logging configuration for the application.
        
        Returns:
            logging.Logger: Configured logger instance
        """
        log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        # Configure root logger
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        # Create and return application logger
        logger = logging.getLogger("document_service")
        logger.setLevel(getattr(logging, log_level))
        
        return logger
    
    def _load_config(self) -> AppConfig:
        """
        Load and validate application configuration from environment variables.
        
        Returns:
            AppConfig: Validated application configuration
        """
        try:
            config = app_config.load_config()
            return config
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise
    
    def _create_fastapi_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application instance.
        
        Returns:
            FastAPI: Configured FastAPI application
        """
        app = FastAPI(
            title="Document Service API",
            description="API for the Document Service microservice",
            version=self.config.version,
            docs_url="/api/docs" if self.config.environment != "production" else None,
            redoc_url="/api/redoc" if self.config.environment != "production" else None,
        )
        
        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Restrict in production
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Include API router
        app.include_router(api_router, prefix="/api")
        
        # Add health check endpoints directly to the app
        @app.get("/health/liveness", tags=["Health"])
        async def liveness_check():
            """
            Kubernetes liveness probe endpoint.
            
            Returns:
                dict: Status indicating the service is running
            """
            return {"status": "alive", "service": "document-service"}
        
        @app.get("/health/readiness", tags=["Health"])
        async def readiness_check():
            """
            Kubernetes readiness probe endpoint.
            
            Checks if all required services (RabbitMQ, S3) are available.
            
            Returns:
                dict: Status indicating the service is ready to accept requests
            """
            status = {"status": "ready", "service": "document-service"}
            checks = {}
            
            # Check RabbitMQ connection
            if self.queue_service:
                try:
                    rabbitmq_status = self.queue_service.check_connection()
                    checks["rabbitmq"] = {"status": "up" if rabbitmq_status else "down"}
                except Exception as e:
                    self.logger.error(f"RabbitMQ health check failed: {str(e)}")
                    checks["rabbitmq"] = {"status": "down", "error": str(e)}
            else:
                checks["rabbitmq"] = {"status": "not_initialized"}
            
            # Check S3 connection
            if self.storage_service:
                try:
                    s3_status = self.storage_service.check_connection()
                    checks["s3"] = {"status": "up" if s3_status else "down"}
                except Exception as e:
                    self.logger.error(f"S3 health check failed: {str(e)}")
                    checks["s3"] = {"status": "down", "error": str(e)}
            else:
                checks["s3"] = {"status": "not_initialized"}
            
            # Add checks to status response
            status["checks"] = checks
            
            # If any check is down, return 503 Service Unavailable
            if any(check.get("status") == "down" for check in checks.values()):
                status["status"] = "not_ready"
                return status, 503
            
            return status
        
        return app
    
    def _initialize_services(self):
        """
        Initialize all required services for the Document Service.
        
        Creates instances of QueueService, StorageService, ClassificationService,
        and DocumentRoutingService with appropriate configuration.
        """
        self.logger.info("Initializing services")
        
        try:
            # Initialize storage service
            self.logger.info("Initializing storage service")
            self.storage_service = StorageService(self.config.s3_config)
            
            # Initialize queue service
            self.logger.info("Initializing queue service")
            self.queue_service = QueueService(self.config.rabbitmq_config)
            
            # Initialize classification service
            self.logger.info("Initializing classification service")
            self.classification_service = ClassificationService(
                self.config.model_config,
                self.storage_service
            )
            
            # Initialize document routing service
            self.logger.info("Initializing document routing service")
            self.document_routing_service = DocumentRoutingService(
                self.classification_service,
                self.queue_service
            )
            
            self.logger.info("All services initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {str(e)}")
            raise
    
    def start(self):
        """
        Start the Document Service application.
        
        Initializes all services and sets up signal handlers for graceful shutdown.
        """
        if self.is_running:
            self.logger.warning("Application is already running")
            return
        
        self.logger.info("Starting Document Service application")
        
        try:
            # Initialize services
            self._initialize_services()
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
            
            # Start consuming messages from RabbitMQ
            if self.queue_service:
                self.queue_service.start_consuming(
                    callback=self._process_document_message
                )
            
            self.is_running = True
            self.logger.info("Document Service application started successfully")
        except Exception as e:
            self.logger.error(f"Failed to start application: {str(e)}")
            self.stop()
            raise
    
    def stop(self):
        """
        Stop the Document Service application.
        
        Gracefully shuts down all services and releases resources.
        """
        self.logger.info("Stopping Document Service application")
        
        # Stop queue service
        if self.queue_service:
            try:
                self.logger.info("Stopping queue service")
                self.queue_service.stop_consuming()
                self.queue_service.close_connection()
            except Exception as e:
                self.logger.error(f"Error stopping queue service: {str(e)}")
        
        # Close storage service connections
        if self.storage_service:
            try:
                self.logger.info("Closing storage service connections")
                self.storage_service.close()
            except Exception as e:
                self.logger.error(f"Error closing storage service: {str(e)}")
        
        self.is_running = False
        self.logger.info("Document Service application stopped")
    
    def _signal_handler(self, sig, frame):
        """
        Handle termination signals for graceful shutdown.
        
        Args:
            sig: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {sig}, shutting down")
        self.stop()
        sys.exit(0)
    
    def _process_document_message(self, message: Dict[str, Any]):
        """
        Process a document message from the queue.
        
        This is the main callback for processing incoming document messages.
        It orchestrates the document classification and routing process.
        
        Args:
            message: Document message from RabbitMQ
        """
        try:
            self.logger.info(f"Processing document message: {message.get('document_id')}")
            
            # Classify document
            classification_result = self.classification_service.classify_document(message)
            
            # Route document based on classification
            self.document_routing_service.route_document(message, classification_result)
            
            self.logger.info(f"Document processed successfully: {message.get('document_id')}")
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}")
            # Handle error based on application policy
            # For example, publish to error queue or retry


# Create a singleton instance of the application
app_instance = DocumentServiceApp()

# Export FastAPI app for ASGI servers
app = app_instance.app


def get_app_instance() -> DocumentServiceApp:
    """
    Get the singleton instance of the DocumentServiceApp.
    
    This function is used as a FastAPI dependency to access the app instance.
    
    Returns:
        DocumentServiceApp: The singleton application instance
    """
    return app_instance