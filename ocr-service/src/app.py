#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Core application setup module for the OCR Service.

This module configures the OCR Service components and provides the main application instance.
It initializes logger, loads configuration, and creates service instances for OCR processing,
queue management, and storage. This file is the central hub that connects all service
components together.

Requirements:
- OCR Service must be implemented as a Python microservice using TensorFlow
- Service must implement consistent health check endpoints for Kubernetes probes
- Configuration must be loaded from environment variables for containerized deployment
- Service must extract data from documents with 99% accuracy
"""

import logging
import threading
import time
from typing import Dict, Any, Optional

import fastapi
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

# Import configuration modules
from config import app_config, rabbitmq_config, s3_config, tensorflow_config, logging_config

# Import service modules
from services import OCRService, QueueService, StorageService, FieldExtractionService, ConfidenceService

# Import API routers
from api import router as api_router

# Import utility modules
from utils.logging_utils import setup_logger
from utils.error_utils import ServiceError

# Initialize logger
logger = logging.getLogger(__name__)


class OCRServiceApp:
    """
    Main application class for the OCR Service.
    
    This class initializes and manages all components of the OCR Service,
    including FastAPI for health checks, service instances for OCR processing,
    queue management, and storage operations.
    """
    
    def __init__(self):
        """
        Initialize the OCR Service application.
        
        Sets up logging, loads configuration, and creates service instances.
        Does not start any services or connections until start() is called.
        """
        # Initialize logger
        setup_logger(logging_config)
        logger.info(f"Initializing OCR Service v{app_config.VERSION}")
        
        # Create FastAPI application
        self.app = FastAPI(
            title="OCR Service",
            description="Merchant Cash Advance OCR Service for document data extraction",
            version=app_config.VERSION,
            docs_url="/docs" if app_config.ENVIRONMENT != "production" else None,
            redoc_url="/redoc" if app_config.ENVIRONMENT != "production" else None,
        )
        
        # Configure CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Restrict in production
            allow_credentials=True,
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        # Initialize service instances (but don't connect yet)
        self._init_services()
        
        # Include API routers
        self.app.include_router(api_router)
        
        # Add application state
        self.app.state.ocr_service = self.ocr_service
        self.app.state.queue_service = self.queue_service
        self.app.state.storage_service = self.storage_service
        self.app.state.field_extraction_service = self.field_extraction_service
        self.app.state.confidence_service = self.confidence_service
        self.app.state.is_healthy = False
        self.app.state.is_ready = False
        
        # Initialize threading event for stopping the application
        self._stop_event = threading.Event()
        
        # Initialize processing thread
        self._processing_thread = None
        
        logger.info("OCR Service application initialized")
    
    def _init_services(self):
        """
        Initialize service instances.
        
        Creates instances of all required services but does not start them.
        Services are started in the start() method.
        """
        logger.info("Initializing service instances...")
        
        try:
            # Initialize storage service for S3 document access
            self.storage_service = StorageService(
                s3_config=s3_config,
                environment=app_config.ENVIRONMENT
            )
            logger.info("Storage service initialized")
            
            # Initialize OCR service for document processing
            self.ocr_service = OCRService(
                tensorflow_config=tensorflow_config,
                environment=app_config.ENVIRONMENT
            )
            logger.info("OCR service initialized")
            
            # Initialize field extraction service
            self.field_extraction_service = FieldExtractionService()
            logger.info("Field extraction service initialized")
            
            # Initialize confidence service
            self.confidence_service = ConfidenceService()
            logger.info("Confidence service initialized")
            
            # Initialize queue service for RabbitMQ messaging
            self.queue_service = QueueService(
                rabbitmq_config=rabbitmq_config,
                environment=app_config.ENVIRONMENT,
                message_handler=self._process_message
            )
            logger.info("Queue service initialized")
            
        except Exception as e:
            logger.error(f"Error initializing services: {str(e)}")
            raise ServiceError("Failed to initialize services", str(e))
    
    def start(self):
        """
        Start the OCR Service application.
        
        Connects to required services (RabbitMQ, S3), loads OCR models,
        and starts the message processing thread.
        """
        logger.info("Starting OCR Service application...")
        
        try:
            # Connect to S3 storage
            logger.info("Connecting to S3 storage...")
            self.storage_service.connect()
            logger.info("Connected to S3 storage")
            
            # Load OCR models
            logger.info("Loading OCR models...")
            self.ocr_service.load_models()
            logger.info("OCR models loaded successfully")
            
            # Connect to RabbitMQ
            logger.info("Connecting to RabbitMQ...")
            self.queue_service.connect()
            logger.info("Connected to RabbitMQ")
            
            # Start message processing thread
            self._stop_event.clear()
            self._processing_thread = threading.Thread(
                target=self._message_processing_loop,
                daemon=True
            )
            self._processing_thread.start()
            logger.info("Message processing thread started")
            
            # Update application state
            self.app.state.is_healthy = True
            self.app.state.is_ready = True
            
            logger.info("OCR Service application started successfully")
            
        except Exception as e:
            logger.error(f"Error starting application: {str(e)}")
            self.stop()
            raise ServiceError("Failed to start application", str(e))
    
    def stop(self):
        """
        Stop the OCR Service application.
        
        Closes connections to RabbitMQ and S3, stops the message processing thread,
        and releases resources.
        """
        logger.info("Stopping OCR Service application...")
        
        # Update application state
        self.app.state.is_healthy = False
        self.app.state.is_ready = False
        
        # Signal processing thread to stop
        self._stop_event.set()
        
        # Wait for processing thread to finish (with timeout)
        if self._processing_thread and self._processing_thread.is_alive():
            logger.info("Waiting for message processing thread to finish...")
            self._processing_thread.join(timeout=5.0)
            if self._processing_thread.is_alive():
                logger.warning("Message processing thread did not finish in time")
        
        # Close RabbitMQ connection
        try:
            if hasattr(self, 'queue_service'):
                logger.info("Closing RabbitMQ connection...")
                self.queue_service.disconnect()
                logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {str(e)}")
        
        # Close S3 connection
        try:
            if hasattr(self, 'storage_service'):
                logger.info("Closing S3 connection...")
                self.storage_service.disconnect()
                logger.info("S3 connection closed")
        except Exception as e:
            logger.error(f"Error closing S3 connection: {str(e)}")
        
        # Unload OCR models to free GPU memory
        try:
            if hasattr(self, 'ocr_service'):
                logger.info("Unloading OCR models...")
                self.ocr_service.unload_models()
                logger.info("OCR models unloaded")
        except Exception as e:
            logger.error(f"Error unloading OCR models: {str(e)}")
        
        logger.info("OCR Service application stopped")
    
    def _message_processing_loop(self):
        """
        Main message processing loop.
        
        Runs in a separate thread and processes messages from RabbitMQ.
        Continues until stop_event is set.
        """
        logger.info("Message processing loop started")
        
        while not self._stop_event.is_set():
            try:
                # Start consuming messages (this will block until a message is received)
                self.queue_service.start_consuming()
                
                # Sleep briefly to prevent CPU spinning if consumption fails
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in message processing loop: {str(e)}")
                # Sleep before retrying to prevent rapid reconnection attempts
                time.sleep(5.0)
                
                # Try to reconnect if connection was lost
                try:
                    self.queue_service.reconnect()
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect to RabbitMQ: {str(reconnect_error)}")
        
        logger.info("Message processing loop stopped")
    
    def _process_message(self, message: Dict[str, Any]) -> bool:
        """
        Process a message from RabbitMQ.
        
        This is the main document processing function that orchestrates the OCR pipeline:
        1. Download document from S3
        2. Extract text using OCR
        3. Extract structured fields
        4. Calculate confidence scores
        5. Publish results to RabbitMQ
        
        Args:
            message: The message payload from RabbitMQ
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        document_id = message.get('document_id')
        logger.info(f"Processing document: {document_id}")
        
        try:
            # 1. Download document from S3
            document = self.storage_service.download_document(document_id)
            logger.info(f"Downloaded document {document_id} from S3")
            
            # 2. Extract text using OCR
            ocr_result = self.ocr_service.process_document(document)
            logger.info(f"OCR processing completed for document {document_id}")
            
            # 3. Extract structured fields
            extracted_data = self.field_extraction_service.extract_fields(
                ocr_result, 
                document_type=message.get('document_type')
            )
            logger.info(f"Field extraction completed for document {document_id}")
            
            # 4. Calculate confidence scores
            scored_data = self.confidence_service.calculate_confidence(extracted_data)
            logger.info(f"Confidence scoring completed for document {document_id}")
            
            # 5. Upload results to S3
            result_key = self.storage_service.upload_extraction_result(
                document_id, 
                scored_data
            )
            logger.info(f"Extraction results uploaded to S3 for document {document_id}")
            
            # 6. Publish results to RabbitMQ
            result_message = {
                'document_id': document_id,
                'extraction_result_key': result_key,
                'confidence_score': scored_data.get('overall_confidence', 0.0),
                'processing_time': scored_data.get('processing_time', 0.0),
                'requires_review': scored_data.get('requires_review', False),
                'timestamp': time.time()
            }
            
            self.queue_service.publish_result(result_message)
            logger.info(f"Published extraction results for document {document_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            
            # Publish error message
            error_message = {
                'document_id': document_id,
                'error': str(e),
                'timestamp': time.time()
            }
            
            try:
                self.queue_service.publish_error(error_message)
                logger.info(f"Published error message for document {document_id}")
            except Exception as publish_error:
                logger.error(f"Failed to publish error message: {str(publish_error)}")
            
            return False


# Create a single application instance
app_instance = OCRServiceApp()

# Export FastAPI app for ASGI servers
app = app_instance.app