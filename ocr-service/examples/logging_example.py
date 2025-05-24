#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example script demonstrating how to use the logging utilities in the OCR service.

This script shows how to configure and use the logging utilities for structured
logging, request ID tracking, and error handling in the OCR service.
"""

import os
import sys
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logging_utils import (
    configure_logger,
    get_logger,
    log_exception,
    log_with_context,
    set_request_id,
    get_request_id,
    clear_request_id,
    request_context,
    log_function_call,
    log_execution_time,
    log_critical_error,
)


def main():
    """Main function demonstrating logging utilities."""
    # Configure the root logger
    logger = configure_logger(
        "ocr_service",
        level="DEBUG",
        json_format=True,
        console_output=True,
    )

    # Basic logging
    logger.info("Starting OCR service example")
    logger.debug("Debug message")
    logger.warning("Warning message")

    # Logging with context
    log_with_context(
        logger,
        level=20,  # INFO level
        message="Processing document",
        context={
            "document_id": "doc-123",
            "document_type": "application_form",
            "page_count": 5,
        },
    )

    # Using request ID for distributed tracing
    with request_context("req-abc-123"):
        logger.info("Processing request with ID tracking")
        
        # Nested processing with the same request ID
        process_document("doc-123")

    # Demonstrate error logging
    try:
        # Simulate an error
        result = 1 / 0
    except Exception as e:
        log_exception(logger, "Error during processing", extra={"operation": "division"})

    # Demonstrate critical error logging
    try:
        # Simulate a critical error
        raise RuntimeError("Database connection failed")
    except Exception as e:
        log_critical_error(logger, "Critical system error", extra={"component": "database"})

    # Demonstrate function call logging
    calculate_checksum("doc-123", algorithm="sha256")

    # Demonstrate execution time logging
    process_image("image-123.jpg")

    logger.info("OCR service example completed")


# Example functions with logging decorators
@log_function_call(get_logger("ocr_service.document"))
def process_document(document_id):
    """Process a document with the given ID."""
    logger = get_logger("ocr_service.document")
    logger.info(f"Processing document {document_id}")
    # Simulate document processing
    time.sleep(0.1)
    return {"status": "processed", "document_id": document_id}


@log_function_call(get_logger("ocr_service.checksum"))
def calculate_checksum(document_id, algorithm="md5"):
    """Calculate a checksum for the document."""
    logger = get_logger("ocr_service.checksum")
    logger.info(f"Calculating {algorithm} checksum for {document_id}")
    # Simulate checksum calculation
    time.sleep(0.2)
    return f"{algorithm}:12345abcde"


@log_execution_time(get_logger("ocr_service.image"))
def process_image(image_path):
    """Process an image with OCR."""
    logger = get_logger("ocr_service.image")
    logger.info(f"Processing image {image_path}")
    # Simulate image processing
    time.sleep(0.3)
    return {"text": "Extracted text from image", "confidence": 0.95}


if __name__ == "__main__":
    main()