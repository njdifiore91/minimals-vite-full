import os
import sys
import logging
import logging.config
import json
from datetime import datetime
import uuid
from typing import Dict, Any, Optional

# Define the service name for logging
SERVICE_NAME = "ocr-service"

# Get environment or default to development
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").lower()

# Define log levels based on environment
LOG_LEVELS = {
    "development": logging.DEBUG,
    "staging": logging.INFO,
    "production": logging.INFO
}

# Default log level if environment is not recognized
DEFAULT_LOG_LEVEL = logging.INFO

# Get the appropriate log level for the current environment
LOG_LEVEL = LOG_LEVELS.get(ENVIRONMENT, DEFAULT_LOG_LEVEL)

# Define log directory for file handlers
LOG_DIR = os.environ.get("LOG_DIR", "/var/log/ocr-service")

# Ensure log directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Custom JSON formatter for structured logging
class JsonFormatter(logging.Formatter):
    """Custom formatter that outputs logs as JSON objects for better parsing"""
    
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "service": SERVICE_NAME,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "path": record.pathname,
            "function": record.funcName,
            "line": record.lineno,
            "environment": ENVIRONMENT
        }
        
        # Add exception info if available
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        # Add any extra contextual information
        if hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id
            
        if hasattr(record, "document_id"):
            log_record["document_id"] = record.document_id
            
        if hasattr(record, "application_id"):
            log_record["application_id"] = record.application_id
            
        if hasattr(record, "processing_time"):
            log_record["processing_time_ms"] = record.processing_time
            
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            for key, value in record.extra.items():
                log_record[key] = value
                
        return json.dumps(log_record)

# Define the logging configuration dictionary
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()" : JsonFormatter
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": LOG_LEVEL,
            "formatter": "standard" if ENVIRONMENT == "development" else "json",
            "stream": sys.stdout
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": LOG_LEVEL,
            "formatter": "json",
            "filename": f"{LOG_DIR}/{SERVICE_NAME}.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": logging.ERROR,
            "formatter": "json",
            "filename": f"{LOG_DIR}/{SERVICE_NAME}_error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10
        }
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console"],
            "level": LOG_LEVEL,
            "propagate": True
        },
        "ocr_service": {
            "handlers": ["console", "file", "error_file"] if ENVIRONMENT != "development" else ["console"],
            "level": LOG_LEVEL,
            "propagate": False
        },
        "ocr_service.api": {
            "handlers": ["console", "file", "error_file"] if ENVIRONMENT != "development" else ["console"],
            "level": LOG_LEVEL,
            "propagate": False
        },
        "ocr_service.models": {
            "handlers": ["console", "file", "error_file"] if ENVIRONMENT != "development" else ["console"],
            "level": LOG_LEVEL,
            "propagate": False
        },
        "ocr_service.services": {
            "handlers": ["console", "file", "error_file"] if ENVIRONMENT != "development" else ["console"],
            "level": LOG_LEVEL,
            "propagate": False
        },
        "tensorflow": {
            "handlers": ["console", "file"] if ENVIRONMENT != "development" else ["console"],
            "level": logging.WARNING,  # Reduce TensorFlow verbosity
            "propagate": False
        }
    }
}

# Configure additional handlers for production environment
if ENVIRONMENT == "production":
    # Add Datadog handler if available
    try:
        import datadog_logger
        LOGGING_CONFIG["handlers"]["datadog"] = {
            "class": "datadog_logger.DatadogLogHandler",
            "level": LOG_LEVEL,
            "formatter": "json",
            "service": SERVICE_NAME,
            "tags": [f"env:{ENVIRONMENT}", f"service:{SERVICE_NAME}"]
        }
        # Add datadog handler to all loggers
        for logger in LOGGING_CONFIG["loggers"].values():
            if "datadog" not in logger["handlers"]:
                logger["handlers"].append("datadog")
    except ImportError:
        pass

# Function to initialize logging
def setup_logging():
    """Initialize the logging configuration"""
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.info(f"{SERVICE_NAME} logging initialized with level {logging.getLevelName(LOG_LEVEL)} for {ENVIRONMENT} environment")

# Context manager for request tracking
class LogContext:
    """Context manager for adding request context to logs"""
    
    def __init__(self, logger, **context):
        self.logger = logger
        self.context = context
        self.old_context = {}
        
    def __enter__(self):
        # Generate request_id if not provided
        if "request_id" not in self.context:
            self.context["request_id"] = str(uuid.uuid4())
            
        # Save old context and set new context
        for handler in self.logger.handlers:
            old_context = getattr(handler, "_context", {})
            self.old_context[handler] = old_context.copy()
            
            # Create or update context
            if not hasattr(handler, "_context"):
                handler._context = {}
            handler._context.update(self.context)
            
        return self.context.get("request_id")
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore old context
        for handler in self.logger.handlers:
            if handler in self.old_context:
                handler._context = self.old_context[handler]

# Function to get a logger with context enrichment
def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name and context enrichment"""
    logger = logging.getLogger(name)
    
    # Add context method to logger
    def context(self, **kwargs) -> LogContext:
        return LogContext(self, **kwargs)
    
    # Add the context method to the logger
    logger.context = context.__get__(logger)
    
    return logger

# Function to add context to a log record
def add_context_to_record(record: logging.LogRecord, context: Dict[str, Any]) -> None:
    """Add context information to a log record"""
    for key, value in context.items():
        setattr(record, key, value)

# Custom filter to add context from handler to records
class ContextFilter(logging.Filter):
    """Filter that adds context from handler to log records"""
    
    def filter(self, record):
        # Add context from handler if available
        handler = getattr(record, "handler", None)
        if handler and hasattr(handler, "_context"):
            add_context_to_record(record, handler._context)
        return True

# Apply context filter to all handlers
def apply_context_filter():
    """Apply context filter to all handlers"""
    context_filter = ContextFilter()
    for handler in logging.root.handlers:
        handler.addFilter(context_filter)
        
    # Also apply to all named loggers
    for name in logging.root.manager.loggerDict:
        logger = logging.getLogger(name)
        for handler in logger.handlers:
            handler.addFilter(context_filter)

# Initialize logging when this module is imported
setup_logging()
apply_context_filter()