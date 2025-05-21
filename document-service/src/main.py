#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main entry point for the Document Service microservice.

This module initializes the application, sets up error handling, connects to required services
(RabbitMQ, S3), loads ML models, and starts the document classification process. It acts as the
orchestrator for the entire service and handles graceful shutdown when the process is terminated.
"""

import asyncio
import logging
import os
import signal
import sys
import traceback
from typing import Optional

# Import the Application class from app.py
from app import get_app, Application

# Import configuration modules
from config import logging_config
from utils.logging_utils import log_with_context

# Set up the logger
logger = logging.getLogger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback):
    """
    Global exception handler for uncaught exceptions.
    
    Args:
        exc_type: The exception type
        exc_value: The exception value
        exc_traceback: The exception traceback
    """
    if issubclass(exc_type, KeyboardInterrupt):
        # Don't log keyboard interrupt (ctrl+c) as an error
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Format the exception
    exception_details = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    
    # Log the exception
    logger.critical(f"Uncaught exception: {exception_details}")
    
    # Exit with error code
    sys.exit(1)


async def main():
    """
    Main entry point for the Document Service.
    
    Initializes the application, starts all services, and handles graceful shutdown.
    """
    # Get the application instance
    app: Application = get_app()
    
    try:
        # Set up signal handlers for graceful shutdown
        app.setup_signal_handlers()
        
        # Start the application
        await app.start()
        
        # Keep the application running
        logger.info("Document Service is running. Press Ctrl+C to exit.")
        
        # Run forever until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {str(e)}")
        traceback.print_exc()
    finally:
        # Ensure the application is stopped properly
        await app.stop()
        logger.info("Document Service shutdown complete")


def run_service():
    """
    Run the Document Service in an asyncio event loop.
    """
    # Set up global exception handler
    sys.excepthook = handle_exception
    
    # Get or create the event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        # If no event loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        # Run the main function
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received in event loop, shutting down...")
    finally:
        # Close the event loop
        loop.close()
        logger.info("Event loop closed")


if __name__ == "__main__":
    # Initialize logging before anything else
    logging_config.configure_logging()
    
    # Log startup information
    logger.info("Starting Document Service")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Running in directory: {os.getcwd()}")
    
    # Run the service
    run_service()