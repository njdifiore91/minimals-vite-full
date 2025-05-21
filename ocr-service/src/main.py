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
import traceback
import time

# Configure TensorFlow to use GPU
os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
os.environ['TF_GPU_ALLOCATOR'] = 'cuda_malloc_async'

# Import TensorFlow after setting environment variables
import tensorflow as tf

# Import application modules
from app import OCRServiceApp
from config import app_config, logging_config
from utils.logging_utils import setup_logger
from utils.error_utils import log_exception
from utils.tensorflow_utils import check_gpu_memory

# Initialize logger
logger = logging.getLogger(__name__)

# Global application instance
app_instance = None


def verify_gpu_availability():
    """
    Verify that GPU is available for TensorFlow processing.
    Raises RuntimeError if no GPU is available or if VRAM is insufficient.
    """
    gpus = tf.config.list_physical_devices('GPU')
    if not gpus:
        raise RuntimeError("No GPU found. OCR Service requires CUDA-compatible GPU acceleration.")
    
    logger.info(f"Found {len(gpus)} GPU(s): {gpus}")
    
    # Configure TensorFlow to use memory growth to avoid allocating all VRAM at once
    for gpu in gpus:
        try:
            tf.config.experimental.set_memory_growth(gpu, True)
            logger.info(f"Enabled memory growth for GPU: {gpu}")
        except Exception as e:
            logger.warning(f"Error setting memory growth for GPU {gpu}: {str(e)}")
    
    # Check GPU memory to ensure at least 8GB VRAM is available
    try:
        # Use utility function to check GPU memory
        available_memory = check_gpu_memory()
        required_memory = 8 * 1024  # 8GB in MB
        
        if available_memory < required_memory:
            raise RuntimeError(
                f"Insufficient GPU memory. OCR Service requires at least 8GB VRAM, "
                f"but only {available_memory/1024:.2f}GB is available."
            )
            
        logger.info(f"GPU memory check passed: {available_memory/1024:.2f}GB available")
        
        # Create a small tensor to force GPU initialization
        with tf.device('/GPU:0'):
            tf.random.normal([1000, 1000])
        logger.info("GPU initialization successful")
    except Exception as e:
        logger.error(f"GPU initialization failed: {str(e)}")
        raise RuntimeError(f"GPU initialization failed: {str(e)}")


def setup_signal_handlers():
    """
    Set up signal handlers for graceful shutdown.
    """
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        shutdown()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal
    
    logger.info("Signal handlers registered for graceful shutdown")


def shutdown():
    """
    Perform graceful shutdown of the application.
    Close all connections and release resources.
    """
    global app_instance
    if app_instance:
        logger.info("Stopping OCR Service application...")
        try:
            # Stop the application (this will close RabbitMQ and S3 connections)
            app_instance.stop()
            
            # Release GPU resources explicitly
            try:
                tf.keras.backend.clear_session()
                logger.info("TensorFlow session cleared, GPU resources released")
            except Exception as gpu_error:
                logger.warning(f"Error releasing GPU resources: {str(gpu_error)}")
            
            logger.info("OCR Service application stopped successfully")
        except Exception as e:
            logger.error(f"Error during application shutdown: {str(e)}")
            logger.debug(traceback.format_exc())
    else:
        logger.warning("Application instance not found during shutdown")


def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for uncaught exceptions.
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Call original handler for KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    log_exception(logger, "Uncaught exception", exc_value, exc_traceback)
    shutdown()
    sys.exit(1)


def main():
    """
    Main entry point for the OCR Service.
    Initializes the application and starts processing.
    """
    global app_instance
    
    try:
        # Set up logging
        setup_logger(logging_config)
        logger.info(f"Starting OCR Service v{app_config.VERSION}")
        logger.info(f"Environment: {app_config.ENVIRONMENT}")
        
        # Register global exception handler
        sys.excepthook = handle_uncaught_exception
        logger.info("Global exception handler registered")
        
        # Set up signal handlers for graceful shutdown
        setup_signal_handlers()
        
        # Verify GPU availability
        verify_gpu_availability()
        
        # Create and initialize application
        logger.info("Initializing OCR Service application...")
        app_instance = OCRServiceApp()
        
        # Start the application
        logger.info("Starting OCR Service application...")
        app_instance.start()
        
        # Log startup success with performance expectations
        logger.info("OCR Service started successfully")
        logger.info("Performance targets: 99% extraction accuracy, processing in under 5 minutes")
        
        # Keep the main thread alive
        logger.info("OCR Service is running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
            
    except Exception as e:
        logger.critical(f"Failed to start OCR Service: {str(e)}")
        logger.debug(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()