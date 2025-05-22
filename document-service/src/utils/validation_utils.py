#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation utilities for the Document Service.

This module provides utility functions for validating document types, formats,
sizes, and other input data. It's essential for ensuring data integrity and
preventing processing of invalid or malicious content.
"""

import os
import re
import json
import logging
import hashlib
import magic
from typing import Dict, List, Optional, Set, Tuple, Union, Any, BinaryIO, Iterator
from pathlib import Path
from functools import wraps
import jsonschema
from jsonschema import validate, ValidationError as JsonSchemaValidationError

# Import custom types
from ..types.documents import DocumentType, DocumentMetadata, DocumentContent
from ..types.errors import ValidationError, ServiceError, Result

# Import file utilities
from .file_utils import (
    get_file_size, get_file_size_from_buffer, get_mime_type, 
    get_mime_type_from_buffer, is_supported_mime_type, 
    is_supported_file_extension, SUPPORTED_MIME_TYPES
)

# Configure logger
logger = logging.getLogger(__name__)

# Constants for document validation
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB maximum file size
MIN_FILE_SIZE = 1024  # 1 KB minimum file size
MAX_PAGE_COUNT = 100  # Maximum number of pages in a document

# Constants for security validation
MALICIOUS_EXTENSIONS = [
    '.exe', '.dll', '.bat', '.cmd', '.sh', '.js', '.vbs', '.ps1', 
    '.msi', '.com', '.scr', '.pif', '.hta', '.cpl', '.msc', '.jar'
]

# Constants for MIME type validation
MALICIOUS_MIME_TYPES = [
    'application/x-msdownload',
    'application/x-executable',
    'application/x-dosexec',
    'application/x-msdos-program',
    'application/x-msi',
    'application/x-ms-shortcut',
    'application/x-sh',
    'application/javascript',
    'application/x-javascript',
    'text/javascript',
    'application/java-archive'
]

# Constants for message validation
MAX_MESSAGE_SIZE = 1 * 1024 * 1024  # 1 MB maximum message size

# JSON Schema for document message validation
DOCUMENT_MESSAGE_SCHEMA = {
    "type": "object",
    "required": ["document_id", "metadata", "source"],
    "properties": {
        "document_id": {"type": "string", "format": "uuid"},
        "metadata": {
            "type": "object",
            "required": ["filename", "size", "mime_type"],
            "properties": {
                "filename": {"type": "string"},
                "size": {"type": "integer", "minimum": 0},
                "mime_type": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "updated_at": {"type": "string", "format": "date-time"},
                "classification_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                "ocr_confidence": {"type": ["number", "null"], "minimum": 0, "maximum": 1},
                "application_id": {"type": ["string", "null"]},
                "storage_path": {"type": ["string", "null"]},
                "checksum": {"type": ["string", "null"]},
                "page_count": {"type": ["integer", "null"], "minimum": 1},
                "tags": {"type": "array", "items": {"type": "string"}}
            }
        },
        "source": {
            "type": "object",
            "required": ["source_type", "received_at"],
            "properties": {
                "source_type": {"type": "string", "enum": ["email", "upload", "api"]},
                "email_id": {"type": ["string", "null"]},
                "email_sender": {"type": ["string", "null"]},
                "email_subject": {"type": ["string", "null"]},
                "email_received_at": {"type": ["string", "null"], "format": "date-time"},
                "upload_user_id": {"type": ["string", "null"]},
                "upload_ip": {"type": ["string", "null"]},
                "api_client_id": {"type": ["string", "null"]},
                "submission_id": {"type": ["string", "null"]},
                "received_at": {"type": "string", "format": "date-time"}
            }
        },
        "content_reference": {"type": ["string", "null"]},
        "document_type": {"type": ["string", "null"], "enum": [dt.value for dt in DocumentType] + [None]},
        "status": {"type": "string", "enum": ["received", "classifying", "classified", "processing", "processed", "error", "review", "completed"]}
    }
}

# JSON Schema for classification result message validation
CLASSIFICATION_RESULT_SCHEMA = {
    "type": "object",
    "required": ["document_id", "document_type", "confidence", "confidence_scores", "model_version", "classified_at"],
    "properties": {
        "document_id": {"type": "string", "format": "uuid"},
        "document_type": {"type": "string", "enum": [dt.value for dt in DocumentType]},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "confidence_scores": {
            "type": "object",
            "additionalProperties": {"type": "number", "minimum": 0, "maximum": 1}
        },
        "features_used": {"type": "array", "items": {"type": "string"}},
        "model_version": {"type": "string"},
        "classified_at": {"type": "string", "format": "date-time"},
        "requires_review": {"type": "boolean"}
    }
}

# JSON Schema for OCR request message validation
OCR_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["document_id", "document_type", "storage_path"],
    "properties": {
        "document_id": {"type": "string", "format": "uuid"},
        "document_type": {"type": "string", "enum": [dt.value for dt in DocumentType]},
        "storage_path": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "size": {"type": "integer", "minimum": 0},
                "mime_type": {"type": "string"},
                "page_count": {"type": ["integer", "null"], "minimum": 1},
                "classification_confidence": {"type": "number", "minimum": 0, "maximum": 1}
            }
        },
        "processing_options": {
            "type": "object",
            "properties": {
                "extract_tables": {"type": "boolean"},
                "extract_signatures": {"type": "boolean"},
                "extract_handwriting": {"type": "boolean"},
                "confidence_threshold": {"type": "number", "minimum": 0, "maximum": 1}
            }
        }
    }
}


def validation_decorator(func):
    """
    Decorator for validation functions to handle exceptions and log errors.
    
    Args:
        func: The validation function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {str(e)}")
            raise e
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {str(e)}")
            raise ValidationError(f"Validation error: {str(e)}", context={"function": func.__name__})
    return wrapper


@validation_decorator
def validate_file_size(file_path: str, min_size: int = MIN_FILE_SIZE, max_size: int = MAX_FILE_SIZE) -> bool:
    """
    Validate that a file's size is within acceptable limits.
    
    Args:
        file_path: Path to the file to validate
        min_size: Minimum acceptable file size in bytes
        max_size: Maximum acceptable file size in bytes
        
    Returns:
        bool: True if the file size is valid
        
    Raises:
        ValidationError: If the file size is outside acceptable limits
    """
    file_size = get_file_size(file_path)
    
    if file_size < min_size:
        raise ValidationError(
            f"File size too small: {file_size} bytes (minimum: {min_size} bytes)",
            context={"file_path": file_path, "file_size": file_size, "min_size": min_size}
        )
    
    if file_size > max_size:
        raise ValidationError(
            f"File size too large: {file_size} bytes (maximum: {max_size} bytes)",
            context={"file_path": file_path, "file_size": file_size, "max_size": max_size}
        )
    
    return True


@validation_decorator
def validate_buffer_size(buffer: bytes, min_size: int = MIN_FILE_SIZE, max_size: int = MAX_FILE_SIZE) -> bool:
    """
    Validate that a buffer's size is within acceptable limits.
    
    Args:
        buffer: Bytes buffer to validate
        min_size: Minimum acceptable buffer size in bytes
        max_size: Maximum acceptable buffer size in bytes
        
    Returns:
        bool: True if the buffer size is valid
        
    Raises:
        ValidationError: If the buffer size is outside acceptable limits
    """
    buffer_size = len(buffer)
    
    if buffer_size < min_size:
        raise ValidationError(
            f"Buffer size too small: {buffer_size} bytes (minimum: {min_size} bytes)",
            context={"buffer_size": buffer_size, "min_size": min_size}
        )
    
    if buffer_size > max_size:
        raise ValidationError(
            f"Buffer size too large: {buffer_size} bytes (maximum: {max_size} bytes)",
            context={"buffer_size": buffer_size, "max_size": max_size}
        )
    
    return True


@validation_decorator
def validate_document_type(file_path: str, allowed_types: Optional[List[DocumentType]] = None) -> DocumentType:
    """
    Validate that a file's MIME type is compatible with allowed document types.
    
    Args:
        file_path: Path to the file to validate
        allowed_types: List of allowed document types (if None, all types are allowed)
        
    Returns:
        DocumentType: The most appropriate document type for the file
        
    Raises:
        ValidationError: If the file type is not compatible with allowed document types
    """
    mime_type = get_mime_type(file_path)
    
    # Check if the MIME type is supported at all
    if not is_supported_mime_type(mime_type):
        raise ValidationError(
            f"Unsupported MIME type: {mime_type}",
            context={"file_path": file_path, "mime_type": mime_type, "supported_types": list(SUPPORTED_MIME_TYPES.keys())}
        )
    
    # If no specific allowed types are provided, any supported type is valid
    if allowed_types is None:
        # Return a default document type based on MIME type
        for doc_type in DocumentType:
            if mime_type in SUPPORTED_MIME_TYPES:
                return doc_type
        return DocumentType.OTHER
    
    # Check if the MIME type is compatible with any of the allowed document types
    from ..utils.file_utils import DOCUMENT_TYPE_MIME_MAPPING
    
    compatible_types = []
    for doc_type in allowed_types:
        compatible_mime_types = DOCUMENT_TYPE_MIME_MAPPING.get(doc_type.value, [])
        if mime_type in compatible_mime_types:
            compatible_types.append(doc_type)
    
    if not compatible_types:
        raise ValidationError(
            f"File type {mime_type} is not compatible with allowed document types",
            context={
                "file_path": file_path, 
                "mime_type": mime_type, 
                "allowed_types": [dt.value for dt in allowed_types]
            }
        )
    
    # Return the first compatible document type
    return compatible_types[0]


@validation_decorator
def validate_document_extension(file_path: str) -> bool:
    """
    Validate that a file has a supported extension.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        bool: True if the file extension is supported
        
    Raises:
        ValidationError: If the file extension is not supported
    """
    if not is_supported_file_extension(file_path):
        ext = Path(file_path).suffix.lower()
        raise ValidationError(
            f"Unsupported file extension: {ext}",
            context={"file_path": file_path, "extension": ext, "supported_extensions": list(SUPPORTED_MIME_TYPES.values())}
        )
    
    return True


@validation_decorator
def validate_document_content(file_path: str) -> bool:
    """
    Validate document content for security issues.
    
    Args:
        file_path: Path to the file to validate
        
    Returns:
        bool: True if the document content is valid and safe
        
    Raises:
        ValidationError: If the document content is invalid or potentially malicious
    """
    # Check for malicious file extensions
    ext = Path(file_path).suffix.lower()
    if ext in MALICIOUS_EXTENSIONS:
        raise ValidationError(
            f"Potentially malicious file extension: {ext}",
            context={"file_path": file_path, "extension": ext}
        )
    
    # Check for malicious MIME types using libmagic
    try:
        mime_type = magic.Magic(mime=True).from_file(file_path)
        if mime_type in MALICIOUS_MIME_TYPES:
            raise ValidationError(
                f"Potentially malicious MIME type detected: {mime_type}",
                context={"file_path": file_path, "mime_type": mime_type}
            )
    except ImportError:
        logger.warning("python-magic not available for content validation, falling back to extension check only")
    except Exception as e:
        logger.warning(f"Error during content validation with python-magic: {str(e)}")
    
    # Additional content validation could be added here, such as:
    # - Virus scanning
    # - File structure validation
    # - Content analysis for suspicious patterns
    
    return True


@validation_decorator
def validate_buffer_content(buffer: bytes) -> bool:
    """
    Validate buffer content for security issues.
    
    Args:
        buffer: Bytes buffer to validate
        
    Returns:
        bool: True if the buffer content is valid and safe
        
    Raises:
        ValidationError: If the buffer content is invalid or potentially malicious
    """
    # Check for malicious MIME types using libmagic
    try:
        mime_type = magic.Magic(mime=True).from_buffer(buffer)
        if mime_type in MALICIOUS_MIME_TYPES:
            raise ValidationError(
                f"Potentially malicious MIME type detected: {mime_type}",
                context={"mime_type": mime_type}
            )
    except ImportError:
        logger.warning("python-magic not available for content validation")
    except Exception as e:
        logger.warning(f"Error during content validation with python-magic: {str(e)}")
    
    # Additional content validation could be added here
    
    return True


@validation_decorator
def validate_document(file_path: str, allowed_types: Optional[List[DocumentType]] = None) -> Result[DocumentType, ValidationError]:
    """
    Perform comprehensive validation on a document file.
    
    Args:
        file_path: Path to the file to validate
        allowed_types: List of allowed document types (if None, all types are allowed)
        
    Returns:
        Result[DocumentType, ValidationError]: Result containing the document type if successful
        
    Raises:
        ValidationError: If any validation check fails
    """
    try:
        # Validate file size
        validate_file_size(file_path)
        
        # Validate file extension
        validate_document_extension(file_path)
        
        # Validate document content for security
        validate_document_content(file_path)
        
        # Validate document type
        doc_type = validate_document_type(file_path, allowed_types)
        
        return Result.success(doc_type)
    except ValidationError as e:
        return Result.failure(e)


@validation_decorator
def validate_json_schema(json_data: Union[str, Dict], schema: Dict) -> bool:
    """
    Validate JSON data against a JSON schema.
    
    Args:
        json_data: JSON data as string or dictionary
        schema: JSON schema to validate against
        
    Returns:
        bool: True if the JSON data is valid according to the schema
        
    Raises:
        ValidationError: If the JSON data does not conform to the schema
    """
    # Parse JSON string if necessary
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"Invalid JSON format: {str(e)}",
                context={"error_position": e.pos, "error_message": e.msg}
            )
    else:
        data = json_data
    
    # Validate against schema
    try:
        validate(instance=data, schema=schema)
        return True
    except JsonSchemaValidationError as e:
        raise ValidationError(
            f"JSON schema validation failed: {str(e)}",
            context={"validation_error": str(e), "schema_path": e.schema_path, "json_path": e.path}
        )


@validation_decorator
def validate_document_message(message: Union[str, Dict]) -> bool:
    """
    Validate a document message against the document message schema.
    
    Args:
        message: Document message as string or dictionary
        
    Returns:
        bool: True if the message is valid
        
    Raises:
        ValidationError: If the message does not conform to the schema
    """
    return validate_json_schema(message, DOCUMENT_MESSAGE_SCHEMA)


@validation_decorator
def validate_classification_result_message(message: Union[str, Dict]) -> bool:
    """
    Validate a classification result message against the classification result schema.
    
    Args:
        message: Classification result message as string or dictionary
        
    Returns:
        bool: True if the message is valid
        
    Raises:
        ValidationError: If the message does not conform to the schema
    """
    return validate_json_schema(message, CLASSIFICATION_RESULT_SCHEMA)


@validation_decorator
def validate_ocr_request_message(message: Union[str, Dict]) -> bool:
    """
    Validate an OCR request message against the OCR request schema.
    
    Args:
        message: OCR request message as string or dictionary
        
    Returns:
        bool: True if the message is valid
        
    Raises:
        ValidationError: If the message does not conform to the schema
    """
    return validate_json_schema(message, OCR_REQUEST_SCHEMA)


@validation_decorator
def validate_message_size(message: str, max_size: int = MAX_MESSAGE_SIZE) -> bool:
    """
    Validate that a message's size is within acceptable limits.
    
    Args:
        message: Message string to validate
        max_size: Maximum acceptable message size in bytes
        
    Returns:
        bool: True if the message size is valid
        
    Raises:
        ValidationError: If the message size exceeds the maximum
    """
    message_size = len(message.encode('utf-8'))
    
    if message_size > max_size:
        raise ValidationError(
            f"Message size too large: {message_size} bytes (maximum: {max_size} bytes)",
            context={"message_size": message_size, "max_size": max_size}
        )
    
    return True


@validation_decorator
def validate_metadata(metadata: Dict) -> bool:
    """
    Validate document metadata for required fields and value constraints.
    
    Args:
        metadata: Document metadata dictionary
        
    Returns:
        bool: True if the metadata is valid
        
    Raises:
        ValidationError: If the metadata is invalid
    """
    required_fields = ['filename', 'size', 'mime_type']
    for field in required_fields:
        if field not in metadata:
            raise ValidationError(
                f"Missing required metadata field: {field}",
                context={"metadata": metadata, "missing_field": field}
            )
    
    # Validate size is non-negative
    if metadata['size'] < 0:
        raise ValidationError(
            f"Invalid size value: {metadata['size']} (must be non-negative)",
            context={"metadata": metadata, "size": metadata['size']}
        )
    
    # Validate MIME type is supported
    if not is_supported_mime_type(metadata['mime_type']):
        raise ValidationError(
            f"Unsupported MIME type: {metadata['mime_type']}",
            context={"metadata": metadata, "mime_type": metadata['mime_type'], "supported_types": list(SUPPORTED_MIME_TYPES.keys())}
        )
    
    # Validate confidence scores are between 0 and 1 if present
    for confidence_field in ['classification_confidence', 'ocr_confidence']:
        if confidence_field in metadata and metadata[confidence_field] is not None:
            confidence = metadata[confidence_field]
            if not (0 <= confidence <= 1):
                raise ValidationError(
                    f"Invalid {confidence_field} value: {confidence} (must be between 0 and 1)",
                    context={"metadata": metadata, confidence_field: confidence}
                )
    
    # Validate page count is positive if present
    if 'page_count' in metadata and metadata['page_count'] is not None:
        page_count = metadata['page_count']
        if page_count <= 0:
            raise ValidationError(
                f"Invalid page_count value: {page_count} (must be positive)",
                context={"metadata": metadata, "page_count": page_count}
            )
        
        # Check if page count exceeds maximum
        if page_count > MAX_PAGE_COUNT:
            raise ValidationError(
                f"Page count too high: {page_count} (maximum: {MAX_PAGE_COUNT})",
                context={"metadata": metadata, "page_count": page_count, "max_page_count": MAX_PAGE_COUNT}
            )
    
    return True


@validation_decorator
def is_potentially_malicious(file_path: str) -> bool:
    """
    Check if a file is potentially malicious based on extension and content.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        bool: True if the file is potentially malicious, False otherwise
    """
    # Check extension
    ext = Path(file_path).suffix.lower()
    if ext in MALICIOUS_EXTENSIONS:
        logger.warning(f"Potentially malicious file extension detected: {ext}")
        return True
    
    # Check MIME type
    try:
        mime_type = magic.Magic(mime=True).from_file(file_path)
        if mime_type in MALICIOUS_MIME_TYPES:
            logger.warning(f"Potentially malicious MIME type detected: {mime_type}")
            return True
    except ImportError:
        logger.warning("python-magic not available for malicious file detection")
    except Exception as e:
        logger.warning(f"Error during malicious file detection: {str(e)}")
    
    # Additional checks could be added here
    
    return False


@validation_decorator
def validate_document_for_processing(file_path: str, document_type: DocumentType) -> bool:
    """
    Validate that a document is suitable for processing based on its type.
    
    Args:
        file_path: Path to the file to validate
        document_type: Expected document type
        
    Returns:
        bool: True if the document is valid for processing
        
    Raises:
        ValidationError: If the document is not valid for processing
    """
    # Validate file size
    validate_file_size(file_path)
    
    # Validate document content for security
    validate_document_content(file_path)
    
    # Check if the document type is compatible with the file
    from ..utils.file_utils import is_valid_document_for_type
    
    if not is_valid_document_for_type(file_path, document_type.value):
        mime_type = get_mime_type(file_path)
        raise ValidationError(
            f"Document type {document_type.value} is not compatible with file type {mime_type}",
            context={"file_path": file_path, "document_type": document_type.value, "mime_type": mime_type}
        )
    
    return True


@validation_decorator
def validate_email_source(source: Dict) -> bool:
    """
    Validate email source information for required fields and format.
    
    Args:
        source: Source information dictionary
        
    Returns:
        bool: True if the source information is valid
        
    Raises:
        ValidationError: If the source information is invalid
    """
    if source.get('source_type') != 'email':
        raise ValidationError(
            f"Invalid source type for email validation: {source.get('source_type')}",
            context={"source": source}
        )
    
    # Check required email fields
    required_fields = ['email_id', 'email_sender', 'email_received_at']
    for field in required_fields:
        if field not in source or not source[field]:
            raise ValidationError(
                f"Missing required email source field: {field}",
                context={"source": source, "missing_field": field}
            )
    
    # Validate email format
    email_sender = source['email_sender']
    email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    if not email_pattern.match(email_sender):
        raise ValidationError(
            f"Invalid email format: {email_sender}",
            context={"source": source, "email_sender": email_sender}
        )
    
    return True


@validation_decorator
def validate_upload_source(source: Dict) -> bool:
    """
    Validate upload source information for required fields and format.
    
    Args:
        source: Source information dictionary
        
    Returns:
        bool: True if the source information is valid
        
    Raises:
        ValidationError: If the source information is invalid
    """
    if source.get('source_type') != 'upload':
        raise ValidationError(
            f"Invalid source type for upload validation: {source.get('source_type')}",
            context={"source": source}
        )
    
    # Check required upload fields
    required_fields = ['upload_user_id']
    for field in required_fields:
        if field not in source or not source[field]:
            raise ValidationError(
                f"Missing required upload source field: {field}",
                context={"source": source, "missing_field": field}
            )
    
    # Validate IP format if present
    if 'upload_ip' in source and source['upload_ip']:
        ip_address = source['upload_ip']
        # Simple IPv4 pattern
        ipv4_pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
        # Simple IPv6 pattern
        ipv6_pattern = re.compile(r'^[0-9a-fA-F:]+$')
        
        if not (ipv4_pattern.match(ip_address) or ipv6_pattern.match(ip_address)):
            raise ValidationError(
                f"Invalid IP address format: {ip_address}",
                context={"source": source, "upload_ip": ip_address}
            )
    
    return True


@validation_decorator
def validate_api_source(source: Dict) -> bool:
    """
    Validate API source information for required fields and format.
    
    Args:
        source: Source information dictionary
        
    Returns:
        bool: True if the source information is valid
        
    Raises:
        ValidationError: If the source information is invalid
    """
    if source.get('source_type') != 'api':
        raise ValidationError(
            f"Invalid source type for API validation: {source.get('source_type')}",
            context={"source": source}
        )
    
    # Check required API fields
    required_fields = ['api_client_id']
    for field in required_fields:
        if field not in source or not source[field]:
            raise ValidationError(
                f"Missing required API source field: {field}",
                context={"source": source, "missing_field": field}
            )
    
    return True


@validation_decorator
def validate_source_information(source: Dict) -> bool:
    """
    Validate source information based on source type.
    
    Args:
        source: Source information dictionary
        
    Returns:
        bool: True if the source information is valid
        
    Raises:
        ValidationError: If the source information is invalid
    """
    if 'source_type' not in source:
        raise ValidationError(
            "Missing source_type in source information",
            context={"source": source}
        )
    
    if 'received_at' not in source:
        raise ValidationError(
            "Missing received_at in source information",
            context={"source": source}
        )
    
    source_type = source['source_type']
    
    if source_type == 'email':
        return validate_email_source(source)
    elif source_type == 'upload':
        return validate_upload_source(source)
    elif source_type == 'api':
        return validate_api_source(source)
    else:
        raise ValidationError(
            f"Invalid source_type: {source_type}",
            context={"source": source, "valid_types": ['email', 'upload', 'api']}
        )


@validation_decorator
def validate_document_hash(file_path: str, expected_hash: str, algorithm: str = 'sha256') -> bool:
    """
    Validate a document's hash against an expected value.
    
    Args:
        file_path: Path to the file to validate
        expected_hash: Expected hash value
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        bool: True if the document hash matches the expected value
        
    Raises:
        ValidationError: If the document hash does not match the expected value
    """
    from .file_utils import calculate_file_hash
    
    actual_hash = calculate_file_hash(file_path, algorithm)
    
    if actual_hash.lower() != expected_hash.lower():
        raise ValidationError(
            f"Document hash mismatch: expected {expected_hash}, got {actual_hash}",
            context={
                "file_path": file_path, 
                "expected_hash": expected_hash, 
                "actual_hash": actual_hash,
                "algorithm": algorithm
            }
        )
    
    return True