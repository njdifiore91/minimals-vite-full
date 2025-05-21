# -*- coding: utf-8 -*-
"""
Document Service Utilities Package

This package provides a comprehensive set of utility functions for the Document Service,
including file operations, S3 storage, RabbitMQ messaging, machine learning, logging,
error handling, validation, retry logic, security, and time utilities.

The utilities are organized into modules by functionality, but can be imported directly
from the utils package for convenience.

Example:
    from document_service.src.utils import validate_document_type, store_document_in_s3

    if validate_document_type(document):
        document_url = store_document_in_s3(document)
"""

__version__ = '1.0.0'

# Import basic utilities first to avoid circular dependencies
from .time_utils import (
    format_timestamp,
    get_current_timestamp,
    calculate_duration,
    compare_dates,
    format_iso8601,
    parse_iso8601,
    get_processing_time
)

from .file_utils import (
    get_file_extension,
    get_mime_type,
    calculate_file_size,
    format_file_size,
    create_temp_file,
    cleanup_temp_files,
    is_supported_document_type
)

# Import logging and error utilities
from .logging_utils import (
    setup_logger,
    get_logger,
    log_with_context,
    log_error,
    log_warning,
    log_info,
    log_debug
)

from .error_utils import (
    DocumentServiceError,
    ValidationError,
    ConnectionError,
    ProcessingError,
    create_error_context,
    is_retriable_error,
    format_error_message
)

from .validation_utils import (
    validate_document_type,
    validate_document_size,
    validate_document_format,
    validate_message_schema,
    validate_mime_type,
    get_document_metadata
)

# Import security and retry utilities
from .security_utils import (
    encrypt_data,
    decrypt_data,
    generate_hmac,
    verify_hmac,
    secure_random_string,
    configure_tls
)

from .retry_utils import (
    retry_with_backoff,
    exponential_backoff,
    add_jitter,
    retry_async,
    is_retry_eligible
)

# Import complex utilities that may depend on others
from .s3_utils import (
    initialize_s3_client,
    upload_document,
    download_document,
    generate_presigned_url,
    get_document_metadata_from_s3,
    list_documents,
    delete_document
)

from .rabbitmq_utils import (
    initialize_rabbitmq,
    create_channel,
    publish_message,
    consume_messages,
    acknowledge_message,
    reject_message,
    close_connection
)

from .ml_utils import (
    load_classification_model,
    extract_features,
    classify_document,
    get_confidence_score,
    update_model_metrics,
    get_model_version,
    validate_model_performance
)

# Define __all__ to explicitly specify what is exported
__all__ = [
    # Version
    '__version__',
    
    # Time utilities
    'format_timestamp',
    'get_current_timestamp',
    'calculate_duration',
    'compare_dates',
    'format_iso8601',
    'parse_iso8601',
    'get_processing_time',
    
    # File utilities
    'get_file_extension',
    'get_mime_type',
    'calculate_file_size',
    'format_file_size',
    'create_temp_file',
    'cleanup_temp_files',
    'is_supported_document_type',
    
    # Logging utilities
    'setup_logger',
    'get_logger',
    'log_with_context',
    'log_error',
    'log_warning',
    'log_info',
    'log_debug',
    
    # Error utilities
    'DocumentServiceError',
    'ValidationError',
    'ConnectionError',
    'ProcessingError',
    'create_error_context',
    'is_retriable_error',
    'format_error_message',
    
    # Validation utilities
    'validate_document_type',
    'validate_document_size',
    'validate_document_format',
    'validate_message_schema',
    'validate_mime_type',
    'get_document_metadata',
    
    # Security utilities
    'encrypt_data',
    'decrypt_data',
    'generate_hmac',
    'verify_hmac',
    'secure_random_string',
    'configure_tls',
    
    # Retry utilities
    'retry_with_backoff',
    'exponential_backoff',
    'add_jitter',
    'retry_async',
    'is_retry_eligible',
    
    # S3 utilities
    'initialize_s3_client',
    'upload_document',
    'download_document',
    'generate_presigned_url',
    'get_document_metadata_from_s3',
    'list_documents',
    'delete_document',
    
    # RabbitMQ utilities
    'initialize_rabbitmq',
    'create_channel',
    'publish_message',
    'consume_messages',
    'acknowledge_message',
    'reject_message',
    'close_connection',
    
    # Machine learning utilities
    'load_classification_model',
    'extract_features',
    'classify_document',
    'get_confidence_score',
    'update_model_metrics',
    'get_model_version',
    'validate_model_performance'
]