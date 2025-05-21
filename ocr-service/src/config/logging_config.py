#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging Configuration for OCR Service

This module configures the logging system for the OCR Service. It defines log levels,
formats, handlers, and context enrichment to enable comprehensive logging for monitoring,
debugging, and troubleshooting the service's operation.

The configuration supports different environments (development, staging, production)
and ensures that all processing failures, potential issues, and normal operations are
properly recorded with appropriate context information.

Features:
- Environment-specific log levels
- Structured logging with consistent formats
- Console and file handlers with appropriate configuration
- Request context enrichment with correlation IDs
- Log rotation to prevent disk space issues
"""

import os
import sys
import json
import logging
import logging.config
import logging.handlers
from datetime import datetime
from typing import Dict, Any, Optional

# Import contextvars for storing request-specific context
from contextvars import ContextVar

# Try to import app_config, but don't fail if it's not available yet
try:
    from .app_config import app_config
except ImportError:
    # Default configuration if app_config is not available
    app_config = {
        "service": {
            "name": "ocr-service",
            "version": "1.0.0"
        },
        "environment": os.getenv("ENVIRONMENT", "development")
    }

# Context variables for request tracking
request_id_var: ContextVar[str] = ContextVar('request_id', default='')
user_id_var: ContextVar[str] = ContextVar('user_id', default='')

# Define log levels based on environment
LOG_LEVELS = {
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.INFO
}

# Default log level if environment is not recognized
DEFAULT_LOG_LEVEL = logging.INFO

# Log directory for file logs
LOG_DIR = os.getenv("LOG_DIR", "/var/log/ocr-service")

# Maximum log file size for rotation (10 MB)
MAX_LOG_SIZE_BYTES = 10 * 1024 * 1024

# Number of backup log files to keep
BACKUP_COUNT = 10

# Log format with timestamp, service name, log level, and message
LOG_FORMAT = "%(asctime)s [%(levelname)s] [%(service)s] [%(request_id)s] %(name)s - %(message)s"

# Date format for logs
DATE_FORMAT = "%Y-%m-%d %H:%M:%S.%f"


class ContextEnricher(logging.Filter):
    """
    Filter that enriches log records with context information.
    
    This filter adds request_id, user_id, service name, and other context
    information to each log record for better traceability.
    """
    
    def __init__(self):
        super().__init__()
    
    def filter(self, record):
        # Add request_id from context or use default
        record.request_id = request_id_var.get() or 'no-request-id'
        
        # Add user_id from context if available
        user_id = user_id_var.get()
        if user_id:
            record.user_id = user_id
        else:
            record.user_id = 'no-user-id'
        
        # Add service information
        record.service = f"{app_config['service']['name']}-{app_config['service']['version']}"
        
        # Add environment information
        record.environment = app_config['environment']
        
        return True


class JsonFormatter(logging.Formatter):
    """
    Custom formatter that outputs log records as JSON.
    
    This formatter converts log records to JSON format for easier parsing
    and analysis by log aggregation tools.
    """
    
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": getattr(record, 'service', app_config['service']['name']),
            "request_id": getattr(record, 'request_id', 'no-request-id'),
            "name": record.name,
            "message": record.getMessage(),
            "environment": getattr(record, 'environment', app_config['environment'])
        }
        
        # Add user_id if available
        if hasattr(record, 'user_id'):
            log_data["user_id"] = record.user_id
        
        # Add exception info if available
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add any extra attributes
        for key, value in record.__dict__.items():
            if key not in ["args", "asctime", "created", "exc_info", "exc_text", "filename",
                          "funcName", "id", "levelname", "levelno", "lineno", "module",
                          "msecs", "message", "msg", "name", "pathname", "process",
                          "processName", "relativeCreated", "stack_info", "thread", "threadName",
                          "service", "request_id", "user_id", "environment"] and not key.startswith("_"):
                log_data[key] = value
        
        return json.dumps(log_data)


def set_request_context(request_id: str, user_id: Optional[str] = None) -> None:
    """
    Set the request context for the current execution context.
    
    This function should be called at the beginning of each request processing
    to set the request_id and user_id for all subsequent log messages.
    
    Args:
        request_id: The unique identifier for the current request
        user_id: The identifier of the user making the request (if available)
    """
    request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)


def clear_request_context() -> None:
    """
    Clear the request context after request processing is complete.
    
    This function should be called at the end of each request processing
    to clear the request_id and user_id from the context.
    """
    request_id_var.set('')
    user_id_var.set('')


def get_logging_config() -> Dict[str, Any]:
    """
    Get the logging configuration dictionary.
    
    This function returns a dictionary with the logging configuration
    that can be used with logging.config.dictConfig().
    
    Returns:
        Dict[str, Any]: The logging configuration dictionary
    """
    # Determine log level based on environment
    environment = app_config['environment']
    log_level = LOG_LEVELS.get(environment, DEFAULT_LOG_LEVEL)
    
    # Ensure log directory exists for file handler
    os.makedirs(LOG_DIR, exist_ok=True)
    
    # Define handlers based on environment
    handlers = ["console"]
    if environment in ["staging", "production"]:
        handlers.append("file")
        handlers.append("error_file")
    
    # Define logging configuration
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": LOG_FORMAT,
                "datefmt": DATE_FORMAT
            },
            "json": {
                "()" : JsonFormatter,
                "datefmt": DATE_FORMAT
            }
        },
        "filters": {
            "context_enricher": {
                "()" : ContextEnricher
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "standard" if environment == "development" else "json",
                "filters": ["context_enricher"],
                "stream": "ext://sys.stdout"
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "json",
                "filters": ["context_enricher"],
                "filename": f"{LOG_DIR}/ocr-service.log",
                "maxBytes": MAX_LOG_SIZE_BYTES,
                "backupCount": BACKUP_COUNT,
                "encoding": "utf8"
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "json",
                "filters": ["context_enricher"],
                "filename": f"{LOG_DIR}/ocr-service-error.log",
                "maxBytes": MAX_LOG_SIZE_BYTES,
                "backupCount": BACKUP_COUNT,
                "encoding": "utf8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "level": log_level,
                "handlers": handlers,
                "propagate": True
            },
            "ocr-service": {
                "level": log_level,
                "handlers": handlers,
                "propagate": False
            },
            # Add specific loggers for different components
            "ocr-service.api": {
                "level": log_level,
                "handlers": handlers,
                "propagate": False
            },
            "ocr-service.models": {
                "level": log_level,
                "handlers": handlers,
                "propagate": False
            },
            "ocr-service.services": {
                "level": log_level,
                "handlers": handlers,
                "propagate": False
            },
            # Reduce log level for noisy third-party libraries
            "tensorflow": {
                "level": "WARNING",
                "handlers": handlers,
                "propagate": False
            },
            "pika": {
                "level": "WARNING",
                "handlers": handlers,
                "propagate": False
            },
            "boto3": {
                "level": "WARNING",
                "handlers": handlers,
                "propagate": False
            },
            "botocore": {
                "level": "WARNING",
                "handlers": handlers,
                "propagate": False
            }
        }
    }
    
    return config


def configure_logging() -> None:
    """
    Configure the logging system for the OCR Service.
    
    This function configures the logging system using the configuration
    returned by get_logging_config().
    """
    try:
        # Get logging configuration
        config = get_logging_config()
        
        # Configure logging
        logging.config.dictConfig(config)
        
        # Log successful configuration
        logger = logging.getLogger("ocr-service")
        logger.info("Logging configured successfully", extra={"config_type": "logging"})
        
    except Exception as e:
        # If logging configuration fails, set up a basic configuration
        # and log the error to stderr
        logging.basicConfig(
            level=logging.INFO,
            format=LOG_FORMAT,
            datefmt=DATE_FORMAT,
            stream=sys.stderr
        )
        logger = logging.getLogger("ocr-service")
        logger.error(f"Failed to configure logging: {str(e)}", exc_info=True)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    This function returns a logger with the specified name, which will
    inherit the configuration from the root logger.
    
    Args:
        name: The name of the logger
        
    Returns:
        logging.Logger: The logger instance
    """
    return logging.getLogger(name)


# Configure logging when this module is imported
configure_logging()