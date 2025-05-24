#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Logging Configuration for Document Service

This module configures the logging system for the Document Service. It defines log levels,
formats, handlers, and context enrichment to ensure comprehensive logging for monitoring,
debugging, and troubleshooting the service's operation.

Log Levels:
    - ERROR: Processing failures
    - WARN: Potential issues
    - INFO: Normal operations
    - DEBUG: Troubleshooting (development only)

Features:
    - Environment-specific configuration
    - Structured JSON logging
    - Request context enrichment
    - Log rotation
    - Console and file handlers
"""

import os
import sys
import json
import logging
import logging.config
from logging.handlers import RotatingFileHandler
from datetime import datetime
from pythonjsonlogger import jsonlogger

# Constants
SERVICE_NAME = "document-service"
LOG_DIR = os.environ.get("LOG_DIR", "/var/log/document-service")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Define log levels based on environment
DEFAULT_LOG_LEVELS = {
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.INFO
}

DEFAULT_LOG_LEVEL = DEFAULT_LOG_LEVELS.get(ENVIRONMENT, logging.INFO)


class ContextFilter(logging.Filter):
    """Filter that injects contextual information into log records."""
    
    def __init__(self, service_name):
        super().__init__()
        self.service_name = service_name
        
    def filter(self, record):
        # Add service name
        record.service = self.service_name
        
        # Add environment
        record.environment = ENVIRONMENT
        
        # Add correlation ID if available from context
        record.correlation_id = getattr(record, 'correlation_id', '-')
        
        # Add request ID if available from context
        record.request_id = getattr(record, 'request_id', '-')
        
        return True


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""
    
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat()
        
        # Add log level
        log_record['level'] = record.levelname
        
        # Add service name
        log_record['service'] = getattr(record, 'service', ENVIRONMENT)
        
        # Add environment
        log_record['environment'] = getattr(record, 'environment', ENVIRONMENT)
        
        # Add correlation ID for request tracking
        log_record['correlation_id'] = getattr(record, 'correlation_id', '-')
        
        # Add request ID for request tracking
        log_record['request_id'] = getattr(record, 'request_id', '-')
        
        # Add process ID
        log_record['pid'] = record.process
        
        # Add thread name
        log_record['thread'] = record.threadName


def get_console_handler():
    """Create and return a console handler for logging."""
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(get_formatter())
    return console_handler


def get_file_handler():
    """Create and return a file handler with rotation for logging."""
    log_file = os.path.join(LOG_DIR, f"{SERVICE_NAME}.log")
    
    # Set up log rotation: 10MB per file, keep 5 backup files
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setFormatter(get_formatter())
    return file_handler


def get_formatter():
    """Create and return a JSON formatter for structured logging."""
    return CustomJsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(service)s '
        '%(environment)s %(correlation_id)s %(request_id)s '
        '%(message)s %(pathname)s %(lineno)d'
    )


def get_logger(name):
    """Create and return a logger with the specified name.
    
    Args:
        name (str): The name of the logger, typically __name__
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    
    # Only configure if not already configured
    if not logger.handlers:
        # Set log level based on environment
        logger.setLevel(DEFAULT_LOG_LEVEL)
        
        # Add context filter
        logger.addFilter(ContextFilter(SERVICE_NAME))
        
        # Add handlers
        logger.addHandler(get_console_handler())
        
        # Add file handler in non-development environments
        if ENVIRONMENT != "development":
            logger.addHandler(get_file_handler())
        
        # Prevent propagation to root logger
        logger.propagate = False
    
    return logger


def configure_logging():
    """Configure the logging system for the entire application.
    
    This function should be called at the start of the application to ensure
    all modules use the same logging configuration.
    """
    # Define logging configuration dictionary
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'json': {
                '()': CustomJsonFormatter,
                'format': '%(timestamp)s %(level)s %(name)s %(service)s '
                         '%(environment)s %(correlation_id)s %(request_id)s '
                         '%(message)s %(pathname)s %(lineno)d'
            },
            'standard': {
                'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            },
        },
        'filters': {
            'context_filter': {
                '()': ContextFilter,
                'service_name': SERVICE_NAME
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'DEBUG',
                'formatter': 'standard' if ENVIRONMENT == 'development' else 'json',
                'filters': ['context_filter'],
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'INFO',
                'formatter': 'json',
                'filters': ['context_filter'],
                'filename': os.path.join(LOG_DIR, f"{SERVICE_NAME}.log"),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'json',
                'filters': ['context_filter'],
                'filename': os.path.join(LOG_DIR, f"{SERVICE_NAME}_error.log"),
                'maxBytes': 10 * 1024 * 1024,  # 10MB
                'backupCount': 5,
                'encoding': 'utf8'
            }
        },
        'loggers': {
            '': {  # Root logger
                'handlers': ['console'],
                'level': DEFAULT_LOG_LEVEL,
                'propagate': True
            },
            'document_service': {
                'handlers': ['console', 'file', 'error_file'] if ENVIRONMENT != 'development' else ['console'],
                'level': DEFAULT_LOG_LEVEL,
                'propagate': False
            },
            # Third-party loggers
            'scikit-learn': {
                'handlers': ['console', 'file'] if ENVIRONMENT != 'development' else ['console'],
                'level': logging.WARNING,
                'propagate': False
            },
            'pika': {
                'handlers': ['console', 'file'] if ENVIRONMENT != 'development' else ['console'],
                'level': logging.WARNING,
                'propagate': False
            },
            'requests': {
                'handlers': ['console', 'file'] if ENVIRONMENT != 'development' else ['console'],
                'level': logging.WARNING,
                'propagate': False
            }
        }
    }
    
    # Apply configuration
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = get_logger(__name__)
    logger.info(f"Logging configured for {SERVICE_NAME} in {ENVIRONMENT} environment")


# Set up context variables for request tracking
class LoggingContext:
    """Context manager for enriching logs with request-specific information.
    
    Example:
        with LoggingContext(correlation_id='abc-123', request_id='req-456'):
            logger.info('Processing request')
    """
    
    def __init__(self, **context_data):
        self.context_data = context_data
        self.old_context = {}
    
    def __enter__(self):
        # Store old context and set new context
        frame = sys._getframe(1)
        while frame:
            if 'self' in frame.f_locals and hasattr(frame.f_locals['self'], 'logger'):
                logger = frame.f_locals['self'].logger
                for key, value in self.context_data.items():
                    if hasattr(logger, key):
                        self.old_context[key] = getattr(logger, key)
                    setattr(logger, key, value)
                break
            frame = frame.f_back
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context
        frame = sys._getframe(1)
        while frame:
            if 'self' in frame.f_locals and hasattr(frame.f_locals['self'], 'logger'):
                logger = frame.f_locals['self'].logger
                for key, value in self.old_context.items():
                    setattr(logger, key, value)
                break
            frame = frame.f_back


# Initialize logging when this module is imported
if __name__ != "__main__":
    configure_logging()