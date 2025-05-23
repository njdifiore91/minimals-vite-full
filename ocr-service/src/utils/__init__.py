#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Utilities Package

This package provides utility functions for the OCR Service, including:
- Time and date handling
- File operations and MIME type detection
- Validation utilities
- Error handling
- Logging
- RabbitMQ integration
- Text processing
- Image processing
- TensorFlow utilities

All utility functions are exposed at the package level for easy importing.
"""

__version__ = '1.0.0'

# Import utilities in dependency order to prevent circular imports

# First, import basic utilities that don't depend on other modules
from .time_utils import (
    # Date validation and conversion
    is_valid_date,
    to_datetime,
    
    # Current time functions
    get_current_timestamp,
    get_utc_timestamp,
    get_timestamp_ms,
    get_log_timestamp,
    
    # Formatting functions
    format_datetime,
    format_date,
    format_time,
    format_iso8601,
    format_date_range,
    
    # Date comparison functions
    is_between,
    is_after,
    is_same,
    
    # Time calculation functions
    add_time,
    subtract_time,
    calculate_duration,
    calculate_processing_time,
    calculate_age,
    
    # Document metadata
    get_document_processing_metadata,
    
    # Constants
    FORMAT_PATTERNS
)

from .file_utils import (
    # MIME type detection
    get_mime_type,
    get_mime_type_from_content,
    is_supported_document_type,
    get_file_extension,
    get_content_type_for_s3,
    
    # File size utilities
    get_file_size,
    format_file_size,
    
    # Temporary file management
    create_temp_file,
    create_temp_directory,
    cleanup_temp_file,
    cleanup_temp_directory,
    
    # File conversion utilities
    bytes_to_file,
    file_to_bytes,
    stream_to_bytes,
    bytes_to_stream,
    
    # File system utilities
    ensure_directory_exists,
    is_valid_file,
    get_safe_filename,
    
    # Constants
    SUPPORTED_MIME_TYPES,
    EXTENSION_TO_MIME
)

from .validation_utils import (
    # Document validation
    validate_document_type,
    validate_document_size,
    validate_document_content,
    
    # Data validation
    validate_message_schema,
    validate_extracted_data,
    validate_confidence_scores,
    
    # Input validation
    validate_input_parameters,
    validate_processing_request,
    
    # Schema validation
    get_schema_for_document_type
)

from .error_utils import (
    # Error creation
    create_error,
    format_error_message,
    
    # Error classification
    is_retriable_error,
    classify_error,
    
    # Error handling
    handle_processing_error,
    handle_connection_error,
    
    # Error context
    enrich_error_context,
    
    # Error serialization
    serialize_error_for_logging,
    serialize_error_for_message
)

from .logging_utils import (
    # Log creation
    create_log_entry,
    log_with_context,
    
    # Log formatting
    format_log_message,
    
    # Specialized logging
    log_processing_start,
    log_processing_end,
    log_processing_error,
    log_extraction_results,
    
    # Request tracking
    get_request_id,
    set_request_context
)

from .rabbitmq_utils import (
    # Connection management
    create_connection,
    create_channel,
    close_connection,
    close_channel,
    
    # Message operations
    publish_message,
    publish_message_with_retry,
    consume_messages,
    acknowledge_message,
    reject_message,
    
    # Message serialization
    serialize_message,
    deserialize_message,
    
    # Queue management
    declare_queue,
    declare_exchange,
    bind_queue
)

from .text_utils import (
    # Text cleaning
    clean_text,
    normalize_text,
    remove_noise,
    
    # Text extraction
    extract_key_value_pairs,
    extract_structured_data,
    extract_tables,
    
    # Text validation
    validate_extracted_text,
    calculate_text_confidence,
    
    # Text formatting
    format_extracted_data,
    generate_json_schema
)

from .image_utils import (
    # Image preprocessing
    preprocess_image,
    normalize_image,
    enhance_image,
    
    # Image segmentation
    segment_document,
    detect_regions,
    detect_tables,
    detect_forms,
    
    # Image conversion
    convert_to_grayscale,
    convert_to_binary,
    
    # Image quality
    assess_image_quality,
    calculate_dpi,
    is_suitable_for_ocr
)

from .tensorflow_utils import (
    # Model management
    load_model,
    get_model_for_document_type,
    get_model_version,
    
    # Inference
    run_inference,
    run_text_detection,
    run_text_recognition,
    
    # GPU management
    configure_gpu,
    get_available_gpus,
    set_memory_growth,
    
    # Performance
    calculate_inference_metrics,
    calculate_confidence_scores,
    
    # Model utilities
    preprocess_for_model,
    postprocess_model_output
)

# Define what's available for import with 'from utils import *'
__all__ = [
    # Time utilities
    'is_valid_date', 'to_datetime', 'get_current_timestamp', 'get_utc_timestamp',
    'get_timestamp_ms', 'get_log_timestamp', 'format_datetime', 'format_date',
    'format_time', 'format_iso8601', 'format_date_range', 'is_between',
    'is_after', 'is_same', 'add_time', 'subtract_time', 'calculate_duration',
    'calculate_processing_time', 'calculate_age', 'get_document_processing_metadata',
    'FORMAT_PATTERNS',
    
    # File utilities
    'get_mime_type', 'get_mime_type_from_content', 'is_supported_document_type',
    'get_file_extension', 'get_content_type_for_s3', 'get_file_size',
    'format_file_size', 'create_temp_file', 'create_temp_directory',
    'cleanup_temp_file', 'cleanup_temp_directory', 'bytes_to_file',
    'file_to_bytes', 'stream_to_bytes', 'bytes_to_stream',
    'ensure_directory_exists', 'is_valid_file', 'get_safe_filename',
    'SUPPORTED_MIME_TYPES', 'EXTENSION_TO_MIME',
    
    # Validation utilities
    'validate_document_type', 'validate_document_size', 'validate_document_content',
    'validate_message_schema', 'validate_extracted_data', 'validate_confidence_scores',
    'validate_input_parameters', 'validate_processing_request', 'get_schema_for_document_type',
    
    # Error utilities
    'create_error', 'format_error_message', 'is_retriable_error', 'classify_error',
    'handle_processing_error', 'handle_connection_error', 'enrich_error_context',
    'serialize_error_for_logging', 'serialize_error_for_message',
    
    # Logging utilities
    'create_log_entry', 'log_with_context', 'format_log_message',
    'log_processing_start', 'log_processing_end', 'log_processing_error',
    'log_extraction_results', 'get_request_id', 'set_request_context',
    
    # RabbitMQ utilities
    'create_connection', 'create_channel', 'close_connection', 'close_channel',
    'publish_message', 'publish_message_with_retry', 'consume_messages',
    'acknowledge_message', 'reject_message', 'serialize_message',
    'deserialize_message', 'declare_queue', 'declare_exchange', 'bind_queue',
    
    # Text utilities
    'clean_text', 'normalize_text', 'remove_noise', 'extract_key_value_pairs',
    'extract_structured_data', 'extract_tables', 'validate_extracted_text',
    'calculate_text_confidence', 'format_extracted_data', 'generate_json_schema',
    
    # Image utilities
    'preprocess_image', 'normalize_image', 'enhance_image', 'segment_document',
    'detect_regions', 'detect_tables', 'detect_forms', 'convert_to_grayscale',
    'convert_to_binary', 'assess_image_quality', 'calculate_dpi', 'is_suitable_for_ocr',
    
    # TensorFlow utilities
    'load_model', 'get_model_for_document_type', 'get_model_version', 'run_inference',
    'run_text_detection', 'run_text_recognition', 'configure_gpu', 'get_available_gpus',
    'set_memory_growth', 'calculate_inference_metrics', 'calculate_confidence_scores',
    'preprocess_for_model', 'postprocess_model_output'
]