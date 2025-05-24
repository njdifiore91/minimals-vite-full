#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service Main Entry Point

This module serves as the main entry point for the Document Service microservice.
It initializes the application, sets up error handling, connects to required services
(RabbitMQ, S3), loads ML models, and starts the document classification process.

The Document Service is responsible for classifying incoming documents with 99% accuracy
using scikit-learn models (SVM and Random Forest) and routing them to appropriate OCR processors.
"""

import os
import sys
import logging
import traceback
import signal
import time
from typing import NoReturn

# Import the application instance from app.py
from app import app_instance

# Import configuration modules
from config import app_config

# Set up root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Create logger for this module
logger = logging.getLogger("document_service.main")


def setup_global_exception_handler() -> None:
    """
    Set up a global exception handler for uncaught exceptions.
    
    This ensures that all uncaught exceptions are properly logged before the application exits.
    """
    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            # Don't log keyboard interrupt (Ctrl+C) as an error
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
            
        logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        logger.critical("Application will now exit due to an unhandled exception")
        
    # Set the excepthook to our handler
    sys.excepthook = handle_exception


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        bool: True if all required environment variables are set, False otherwise
    """
    required_vars = [
        "RABBITMQ_HOST",
        "RABBITMQ_PORT",
        "RABBITMQ_USER",
        "RABBITMQ_PASSWORD",
        "S3_ENDPOINT",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_BUCKET_NAME",
        "MODEL_PATH"
    ]
    
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
        
    return True


def main() -> NoReturn:
    """
    Main entry point for the Document Service.
    
    This function initializes the application, connects to required services,
    loads ML models, and starts the document classification process.
    """
    try:
        # Set up global exception handler
        setup_global_exception_handler()
        
        # Log startup information
        logger.info("Starting Document Service")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
        
        # Validate environment variables
        if not validate_environment():
            logger.error("Environment validation failed. Exiting.")
            sys.exit(1)
        
        # Load configuration
        logger.info("Loading configuration")
        config = app_config.load_config()
        logger.info(f"Configuration loaded for environment: {config.environment}")
        
        # Start the application
        logger.info("Starting Document Service application")
        app_instance.start()
        
        # Keep the main thread alive while the application is running
        logger.info("Document Service is running. Press CTRL+C to exit.")
        while app_instance.is_running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt. Shutting down...")
        app_instance.stop()
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Fatal error in main thread: {str(e)}")
        logger.critical(traceback.format_exc())
        app_instance.stop()
        sys.exit(1)


if __name__ == "__main__":
    main()