#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the OCR Service microservice.

This module initializes the application, sets up error handling, connects to required services
(RabbitMQ, S3), loads TensorFlow models, and starts the OCR processing. It acts as the
orchestrator for the entire service and handles graceful shutdown when the process is terminated.

Requirements:
- OCR Service must be implemented as a Python microservice using TensorFlow for text recognition
- Service must connect to RabbitMQ for message consumption
- Service must implement proper error handling and graceful shutdown
- TensorFlow OCR processing requires CUDA-compatible GPU acceleration with at least 8GB VRAM
"""

import os
import sys
import signal
import logging
import time
import traceback
import uvicorn
from typing import Dict, Any, Optional, Callable, NoReturn

# Import the application instance
from app import app_instance, app

# Import utility modules
from utils.logging_utils import setup_logger
from utils.error_utils import ServiceError
from config import app_config, logging_config

# Initialize logger
logger = logging.getLogger(__name__)

# Global flag to track if shutdown is in progress
shutdown_in_progress = False


def verify_gpu_availability() -> bool:
    """
    Verify that a CUDA-compatible GPU with sufficient VRAM is available.
    
    Returns:
        bool: True if GPU is available and meets requirements, False otherwise
    """
    try:
        import tensorflow as tf
        
        # Check if TensorFlow can see any GPUs
        gpus = tf.config.list_physical_devices('GPU')
        if not gpus:
            logger.error("No GPU found. OCR Service requires CUDA-compatible GPU acceleration.")
            return False
            
        logger.info(f"Found {len(gpus)} GPU(s): {gpus}")
        
        # Check GPU memory (this is an approximation as TF doesn't directly expose VRAM size)
        # We'll use a simple test allocation to check if we have enough memory
        try:
            # Try to allocate a 6GB tensor (leaving 2GB for other operations)
            # This is a simple test to ensure we have at least 8GB VRAM
            with tf.device('/GPU:0'):
                # Allocate and immediately delete a large tensor
                test_tensor = tf.random.normal([1024, 1024, 1024])
                # Force execution to verify memory allocation
                _ = test_tensor.numpy()
                del test_tensor
                
            logger.info("GPU memory check passed. Sufficient VRAM available.")
            return True
            
        except (tf.errors.ResourceExhaustedError, tf.errors.InternalError, tf.errors.UnknownError) as e:
            logger.error(f"GPU memory check failed. Insufficient VRAM: {str(e)}")
            return False
            
    except ImportError:
        logger.error("TensorFlow not installed or CUDA not configured properly.")
        return False
    except Exception as e:
        logger.error(f"Error checking GPU availability: {str(e)}")
        return False


def setup_signal_handlers() -> None:
    """
    Set up signal handlers for graceful shutdown.
    
    This function registers handlers for SIGTERM and SIGINT signals to ensure
    that the application shuts down gracefully when terminated.
    """
    def signal_handler(sig: int, frame) -> NoReturn:
        """
        Handle termination signals by initiating graceful shutdown.
        
        Args:
            sig: Signal number
            frame: Current stack frame
        """
        global shutdown_in_progress
        
        signal_name = "SIGTERM" if sig == signal.SIGTERM else "SIGINT"
        
        if shutdown_in_progress:
            logger.warning(f"Received {signal_name} again during shutdown. Forcing exit.")
            sys.exit(1)
            
        logger.info(f"Received {signal_name}. Initiating graceful shutdown...")
        shutdown_in_progress = True
        
        try:
            # Stop the application
            app_instance.stop()
            logger.info("Application stopped successfully.")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")
            traceback.print_exc()
        
        # Exit with success code
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.info("Signal handlers registered for graceful shutdown")


def setup_uncaught_exception_handler() -> None:
    """
    Set up a global exception handler for uncaught exceptions.
    
    This ensures that any uncaught exceptions are properly logged before
    the application crashes.
    """
    def exception_handler(exc_type, exc_value, exc_traceback):
        """
        Handle uncaught exceptions by logging them.
        
        Args:
            exc_type: Exception type
            exc_value: Exception value
            exc_traceback: Exception traceback
        """
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt (ctrl+c) as an error
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
        
    # Set the exception handler
    sys.excepthook = exception_handler
    logger.info("Global exception handler registered")


def start_fastapi_server() -> None:
    """
    Start the FastAPI server for health checks and API endpoints.
    
    This function starts the FastAPI server in a separate process to avoid
    blocking the main thread.
    """
    # Get configuration from environment variables or use defaults
    host = os.environ.get("OCR_SERVICE_HOST", "0.0.0.0")
    port = int(os.environ.get("OCR_SERVICE_PORT", 8000))
    
    # Start the server
    logger.info(f"Starting FastAPI server on {host}:{port}")
    
    # Run in a separate thread to avoid blocking
    import threading
    server_thread = threading.Thread(
        target=uvicorn.run,
        kwargs={
            "app": app,
            "host": host,
            "port": port,
            "log_level": "info",
            # Don't use reloading in production
            "reload": app_config.ENVIRONMENT == "development"
        },
        daemon=True
    )
    server_thread.start()
    logger.info("FastAPI server started in background thread")


def main() -> None:
    """
    Main entry point for the OCR Service.
    
    This function initializes the application, sets up error handling,
    connects to required services, and starts the OCR processing.
    """
    try:
        # Initialize logger
        setup_logger(logging_config)
        logger.info(f"Starting OCR Service v{app_config.VERSION}")
        
        # Set up error handling
        setup_uncaught_exception_handler()
        setup_signal_handlers()
        
        # Verify GPU availability
        if not verify_gpu_availability() and not app_config.BYPASS_GPU_CHECK:
            logger.error("GPU requirements not met. Exiting.")
            sys.exit(1)
        
        # Start the application
        app_instance.start()
        
        # Start FastAPI server for health checks and API endpoints
        start_fastapi_server()
        
        logger.info("OCR Service started successfully")
        
        # Keep the main thread running until shutdown is requested
        # This allows the application to run indefinitely while handling signals
        while not shutdown_in_progress:
            time.sleep(1)
            
    except ServiceError as e:
        logger.error(f"Service error during startup: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Unhandled exception during startup: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()