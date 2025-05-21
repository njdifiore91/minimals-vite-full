# OCR Service Utility Functions Package
# Version: 1.0.0
# Python 3.9+ Required
# TensorFlow 2.15.0 Required for OCR functionality
"""
OCR Service Utilities

This package provides utility functions for the OCR Service, a Python/TensorFlow-based
microservice that extracts data from documents using machine learning models with GPU acceleration.

The utility modules include:

- time_utils: Date and time utilities for timestamp generation, formatting, and duration calculation
- file_utils: File handling utilities for operations, MIME type detection, and content validation
- security_utils: Security utilities for AES-256 encryption, HMAC signatures, and credential management
- retry_utils: Retry logic with exponential backoff for handling temporary failures
- validation_utils: Validation utilities for document types, formats, and input data
- error_utils: Standardized error handling, classification, and formatting
- logging_utils: Structured logging with context information and level filtering
- rabbitmq_utils: RabbitMQ connection, publishing, and consumption utilities
- s3_utils: S3-compatible storage integration with encryption for document storage
- text_utils: Post-OCR text processing, normalization, and structured data extraction
- image_utils: Image preprocessing, enhancement, and segmentation for OCR
- tensorflow_utils: TensorFlow model loading, inference, and GPU resource management

All utility modules are imported and exposed here for clean imports throughout the application,
following a similar pattern to barrel files in TypeScript.

Examples:
    # Import specific utility modules
    from ocr_service.utils import time_utils, file_utils
    
    # Use utility functions
    timestamp = time_utils.get_current_timestamp()
    mime_type = file_utils.detect_mime_type(file_path)
    
    # Or import all utilities at once
    from ocr_service.utils import *
    
    # Then use any utility function
    log_entry = logging_utils.create_log_entry("Processing document", "INFO")
    encrypted_data = security_utils.encrypt_data(sensitive_data, encryption_key)
"""

# Version information
__version__ = '1.0.0'
__author__ = 'Dollar Funding OCR Team'
__email__ = 'ocr-service@dollarfunding.com'
__status__ = 'Production'

# Import utility modules in dependency order to prevent circular imports

# Core utilities with no internal dependencies
# These utilities have minimal dependencies and are used by other utility modules
from . import logging_utils  # Logging should be first to enable logging during import
from . import error_utils    # Error handling is used by most other modules
from . import time_utils     # Time utilities are used by logging and other modules
from . import validation_utils  # Validation is used by most processing modules

# File and security utilities
# These utilities handle file operations and security concerns
from . import file_utils     # File operations for document handling
from . import security_utils  # Security functions for encryption and authentication

# External service integration utilities
# These utilities handle integration with external services and include retry logic
from . import retry_utils    # Retry logic used by service integration modules
from . import s3_utils       # S3 storage integration for document storage
from . import rabbitmq_utils  # RabbitMQ integration for message processing

# OCR processing utilities
# These utilities handle the core OCR functionality
from . import image_utils    # Image preprocessing for OCR
from . import text_utils     # Text processing after OCR
from . import tensorflow_utils  # TensorFlow model management and inference

# Utility Function Dependencies and Usage Patterns
"""
Utility Module Dependencies:

1. Core Utilities:
   - logging_utils: No internal dependencies
   - error_utils: Depends on logging_utils
   - time_utils: No internal dependencies
   - validation_utils: Depends on error_utils

2. File and Security Utilities:
   - file_utils: Depends on error_utils, logging_utils, validation_utils
   - security_utils: Depends on error_utils, logging_utils

3. Service Integration Utilities:
   - retry_utils: Depends on error_utils, logging_utils, time_utils
   - s3_utils: Depends on error_utils, logging_utils, file_utils, security_utils, retry_utils
   - rabbitmq_utils: Depends on error_utils, logging_utils, retry_utils

4. OCR Processing Utilities:
   - image_utils: Depends on error_utils, logging_utils, file_utils
   - text_utils: Depends on error_utils, logging_utils, validation_utils
   - tensorflow_utils: Depends on error_utils, logging_utils, file_utils, image_utils

Common Usage Patterns:

1. Document Processing Pipeline:
   file_utils → validation_utils → image_utils → tensorflow_utils → text_utils → s3_utils

2. Message Processing Pipeline:
   rabbitmq_utils → validation_utils → s3_utils → processing → rabbitmq_utils

3. Error Handling Pattern:
   try → error_utils → logging_utils → retry_utils
"""

# Export all modules for easy access
# This allows importing all utilities with: from ocr_service.utils import *
__all__ = [
    # Core utilities
    'logging_utils',   # Structured logging with context
    'error_utils',     # Standardized error handling
    'time_utils',      # Date and time utilities
    'validation_utils', # Input validation
    
    # File and security utilities
    'file_utils',      # File operations and MIME detection
    'security_utils',  # Encryption and security
    
    # Service integration
    'retry_utils',     # Retry logic with backoff
    's3_utils',        # S3 storage with encryption
    'rabbitmq_utils',  # Message queue integration
    
    # OCR processing
    'image_utils',     # Image preprocessing
    'text_utils',      # Text extraction and normalization
    'tensorflow_utils', # ML model management
]