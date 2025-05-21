#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core application setup module for the Document Service microservice.

This module configures the Document Service components and provides the main application instance.
It initializes the logger, loads configuration, and creates service instances for document classification,
queue management, and storage. This file is the central hub that connects all service components together.
"""

import logging
import os
import signal
import sys
from typing import Optional

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import configuration modules
from config import app_config, logging_config

# Import service modules
from services import QueueService, StorageService, ClassificationService, DocumentRoutingService

# Import utility modules
from utils.logging_utils import setup_logger, log_with_context


class Application:
    """
    Main application class for the Document Service microservice.
    
    This class manages the lifecycle of the Document Service, including initialization,
    startup, and shutdown. It creates and configures all required service components
    and provides a FastAPI application instance for health check endpoints.
    """
    
    def __init__(self):
        """
        Initialize the Document Service application.
        
        Sets up logging, loads configuration, and creates service instances.
        Does not start any services or connections - use start() for that.
        """
        # Initialize logger first for proper logging during startup
        self.logger = setup_logger()
        self.logger.info("Initializing Document Service application")
        
        # Load configuration
        self.config = app_config.load_config()
        self.logger.info(f"Loaded configuration for environment: {self.config.environment}")
        
        # Initialize FastAPI application
        self.app = self._create_fastapi_app()
        
        # Initialize services (but don't start connections yet)
        self.queue_service = QueueService(self.config.rabbitmq)
        self.storage_service = StorageService(self.config.s3)
        self.classification_service = ClassificationService(self.config.model)
        self.document_routing_service = DocumentRoutingService()
        
        # Set initialized flag
        self.initialized = True
        self.running = False
        
        self.logger.info("Document Service application initialized successfully")
    
    def _create_fastapi_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application instance.
        
        Returns:
            FastAPI: Configured FastAPI application instance
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
        
        # Add health check endpoints for Kubernetes probes
        from api.health import health_router
        app.include_router(health_router, prefix="/health")
        
        # Add status endpoints for monitoring
        from api.status import status_router
        app.include_router(status_router, prefix="/status")
        
        # Only include API documentation in non-production environments
        if self.config.environment != "production":
            # Add diagnostic endpoints
            from api.diagnostics import diagnostics_router
            app.include_router(diagnostics_router, prefix="/diagnostics")
        
        # Add document endpoints
        from api.documents import documents_router
        app.include_router(documents_router, prefix="/documents")
        
        return app
    
    async def start(self):
        """
        Start the Document Service application.
        
        Initializes connections to external services (RabbitMQ, S3) and
        starts the document classification process.
        """
        if not self.initialized:
            raise RuntimeError("Application must be initialized before starting")
        
        if self.running:
            self.logger.warning("Application is already running")
            return
        
        self.logger.info("Starting Document Service application")
        
        try:
            # Connect to RabbitMQ
            await self.queue_service.connect()
            self.logger.info("Connected to RabbitMQ successfully")
            
            # Connect to S3 storage
            await self.storage_service.connect()
            self.logger.info("Connected to S3 storage successfully")
            
            # Initialize classification service
            await self.classification_service.initialize()
            self.logger.info("Classification service initialized successfully")
            
            # Start consuming messages from RabbitMQ
            await self.queue_service.start_consuming(self._process_document)
            self.logger.info("Started consuming messages from RabbitMQ")
            
            # Set running flag
            self.running = True
            self.logger.info("Document Service application started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start Document Service application: {str(e)}")
            # Attempt to clean up any connections that were established
            await self.stop()
            raise
    
    async def _process_document(self, message):
        """
        Process a document message from RabbitMQ.
        
        This is the main document processing function that orchestrates the
        classification workflow.
        
        Args:
            message: The message from RabbitMQ containing document information
        """
        try:
            self.logger.info(f"Processing document: {message.get('document_id', 'unknown')}")
            
            # Download document from S3
            document = await self.storage_service.download_document(message)
            
            # Classify document
            classification_result = await self.classification_service.classify_document(document)
            
            # Determine routing based on classification
            routing_result = self.document_routing_service.route_document(classification_result)
            
            # Publish classification result to OCR Service
            await self.queue_service.publish_classification_result(routing_result)
            
            self.logger.info(f"Document processed successfully: {message.get('document_id', 'unknown')}")
            
        except Exception as e:
            self.logger.error(f"Error processing document: {str(e)}")
            # Handle error based on type (retry, dead-letter, etc.)
            await self.queue_service.handle_processing_error(message, str(e))
    
    async def stop(self):
        """
        Stop the Document Service application.
        
        Closes connections to external services and performs cleanup.
        """
        self.logger.info("Stopping Document Service application")
        
        # Stop consuming messages
        if hasattr(self, 'queue_service'):
            try:
                await self.queue_service.stop_consuming()
                self.logger.info("Stopped consuming messages from RabbitMQ")
            except Exception as e:
                self.logger.error(f"Error stopping queue consumption: {str(e)}")
        
        # Close RabbitMQ connection
        if hasattr(self, 'queue_service'):
            try:
                await self.queue_service.disconnect()
                self.logger.info("Disconnected from RabbitMQ")
            except Exception as e:
                self.logger.error(f"Error disconnecting from RabbitMQ: {str(e)}")
        
        # Close S3 connection
        if hasattr(self, 'storage_service'):
            try:
                await self.storage_service.disconnect()
                self.logger.info("Disconnected from S3 storage")
            except Exception as e:
                self.logger.error(f"Error disconnecting from S3: {str(e)}")
        
        # Clean up classification service
        if hasattr(self, 'classification_service'):
            try:
                await self.classification_service.cleanup()
                self.logger.info("Cleaned up classification service")
            except Exception as e:
                self.logger.error(f"Error cleaning up classification service: {str(e)}")
        
        # Set running flag
        self.running = False
        self.logger.info("Document Service application stopped successfully")
    
    def setup_signal_handlers(self):
        """
        Set up signal handlers for graceful shutdown.
        
        This ensures that the application shuts down properly when it
        receives a SIGTERM or SIGINT signal.
        """
        def signal_handler(sig, frame):
            self.logger.info(f"Received signal {sig}, shutting down...")
            import asyncio
            loop = asyncio.get_event_loop()
            loop.create_task(self.stop())
            # Give the stop method some time to complete
            loop.call_later(5, lambda: sys.exit(0))
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        self.logger.info("Signal handlers set up for graceful shutdown")


# Create a global application instance
app_instance: Optional[Application] = None


def get_app() -> Application:
    """
    Get or create the global Application instance.
    
    Returns:
        Application: The global Application instance
    """
    global app_instance
    if app_instance is None:
        app_instance = Application()
    return app_instance


# Create a FastAPI dependency for accessing the application
def get_application():
    """
    FastAPI dependency for accessing the Application instance.
    
    Returns:
        Application: The global Application instance
    """
    return get_app()


# Export the FastAPI application instance for ASGI servers
app = get_app().app