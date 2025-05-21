#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility functions for the OCR Service.

This package provides various utility functions used throughout the OCR Service,
including logging, file handling, security, retry logic, validation, error handling,
RabbitMQ operations, S3 storage, text processing, image processing, and TensorFlow utilities.
"""

# Import and re-export logging utilities
from .logging_utils import (
    configure_logger,
    get_logger,
    log_exception,
    log_with_context,
    setup_root_logger,
    get_request_id,
    set_request_id,
    clear_request_id,
    request_context,
    log_function_call,
    log_execution_time,
    log_critical_error,
)

# Other utility imports will be added as they are implemented

__all__ = [
    # Logging utilities
    "configure_logger",
    "get_logger",
    "log_exception",
    "log_with_context",
    "setup_root_logger",
    "get_request_id",
    "set_request_id",
    "clear_request_id",
    "request_context",
    "log_function_call",
    "log_execution_time",
    "log_critical_error",
    # Other utilities will be added here
]