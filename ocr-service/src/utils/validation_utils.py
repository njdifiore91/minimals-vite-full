#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation utilities for the OCR Service.

This module provides functions for validating document types, formats, sizes,
and other input data. It's essential for ensuring data integrity and preventing
processing of invalid or malicious content.

Functions:
    is_valid_document_type: Validates if a document is of a supported type
    is_valid_document_size: Validates if a document size is within limits
    is_valid_mime_type: Validates if a MIME type is supported
    validate_message_schema: Validates RabbitMQ message schema
    validate_document: Comprehensive document validation
    get_mime_type: Detects MIME type from file content
    get_file_extension: Extracts file extension from filename
    is_valid_file_extension: Validates if a file extension is supported
"""

import os
import json
import logging
import mimetypes
import magic
from typing import Dict, List, Optional, Union, Any, Tuple, BinaryIO
from jsonschema import validate, ValidationError

from ..types.documents import DocumentType, DocumentMetadata
from ..types.messages import MessagePayload
from ..types.errors import ServiceError, ErrorCategory
from ..config import app_config

# Configure logger
logger = logging.getLogger(__name__)

# Constants for document validation
SUPPORTED_MIME_TYPES = {
    'application/pdf': DocumentType.APPLICATION,
    'image/tiff': DocumentType.APPLICATION,
    'image/jpeg': DocumentType.APPLICATION,
    'image/png': DocumentType.APPLICATION,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': DocumentType.BANK_STATEMENT,
    'application/vnd.ms-excel': DocumentType.BANK_STATEMENT,
    'application/msword': DocumentType.APPLICATION,
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': DocumentType.APPLICATION
}

SUPPORTED_FILE_EXTENSIONS = {
    '.pdf': 'application/pdf',
    '.tiff': 'image/tiff',
    '.tif': 'image/tiff',
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    '.xls': 'application/vnd.ms-excel',
    '.doc': 'application/msword',
    '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

# Default size limits in bytes
DEFAULT_MIN_SIZE = 1024  # 1KB
DEFAULT_MAX_SIZE = 20 * 1024 * 1024  # 20MB

# Message schema definitions
OCR_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["document_id", "document_type", "storage_path", "metadata"],
    "properties": {
        "document_id": {"type": "string"},
        "document_type": {"type": "string", "enum": [t.name for t in DocumentType]},
        "storage_path": {"type": "string"},
        "metadata": {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "size": {"type": "integer"},
                "mime_type": {"type": "string"},
                "created_at": {"type": "string", "format": "date-time"},
                "classification": {"type": "object"}
            },
            "required": ["filename", "size", "mime_type"]
        },
        "processing_options": {"type": "object"}
    }
}


def is_valid_document_type(document_type: str) -> bool:
    """
    Validates if a document type is supported.
    
    Args:
        document_type: The document type to validate
        
    Returns:
        bool: True if the document type is supported, False otherwise
    """
    try:
        # Check if the document type is a valid enum value
        DocumentType[document_type]
        return True
    except (KeyError, ValueError):
        logger.warning(f"Unsupported document type: {document_type}")
        return False


def is_valid_mime_type(mime_type: str) -> bool:
    """
    Validates if a MIME type is supported for OCR processing.
    
    Args:
        mime_type: The MIME type to validate
        
    Returns:
        bool: True if the MIME type is supported, False otherwise
    """
    if mime_type in SUPPORTED_MIME_TYPES:
        return True
    
    logger.warning(f"Unsupported MIME type: {mime_type}")
    return False


def get_mime_type(file_content: bytes) -> str:
    """
    Detects MIME type from file content using python-magic.
    
    Args:
        file_content: The file content as bytes
        
    Returns:
        str: The detected MIME type
    """
    try:
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(file_content)
        logger.debug(f"Detected MIME type: {detected_mime}")
        return detected_mime
    except Exception as e:
        logger.error(f"Error detecting MIME type: {str(e)}")
        return "application/octet-stream"  # Default fallback


def get_file_extension(filename: str) -> str:
    """
    Extracts file extension from filename.
    
    Args:
        filename: The filename to extract extension from
        
    Returns:
        str: The file extension (lowercase with dot)
    """
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_valid_file_extension(filename: str) -> bool:
    """
    Validates if a file extension is supported.
    
    Args:
        filename: The filename to validate
        
    Returns:
        bool: True if the file extension is supported, False otherwise
    """
    ext = get_file_extension(filename)
    if ext in SUPPORTED_FILE_EXTENSIONS:
        return True
    
    logger.warning(f"Unsupported file extension: {ext}")
    return False


def is_valid_document_size(size: int, min_size: int = DEFAULT_MIN_SIZE, max_size: int = DEFAULT_MAX_SIZE) -> bool:
    """
    Validates if a document size is within acceptable limits.
    
    Args:
        size: The document size in bytes
        min_size: Minimum acceptable size in bytes (default: 1KB)
        max_size: Maximum acceptable size in bytes (default: 20MB)
        
    Returns:
        bool: True if the size is within limits, False otherwise
    """
    if size < min_size:
        logger.warning(f"Document size too small: {size} bytes (minimum: {min_size} bytes)")
        return False
    
    if size > max_size:
        logger.warning(f"Document size too large: {size} bytes (maximum: {max_size} bytes)")
        return False
    
    return True


def validate_message_schema(message: Dict[str, Any], schema: Dict[str, Any] = OCR_REQUEST_SCHEMA) -> Tuple[bool, Optional[str]]:
    """
    Validates a message against a JSON schema.
    
    Args:
        message: The message to validate
        schema: The JSON schema to validate against (default: OCR_REQUEST_SCHEMA)
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    try:
        validate(instance=message, schema=schema)
        return True, None
    except ValidationError as e:
        error_message = f"Schema validation error: {str(e)}"
        logger.error(error_message)
        return False, error_message


def validate_document_metadata(metadata: Dict[str, Any]) -> Tuple[bool, Optional[ServiceError]]:
    """
    Validates document metadata for completeness and correctness.
    
    Args:
        metadata: The document metadata to validate
        
    Returns:
        Tuple[bool, Optional[ServiceError]]: (is_valid, error)
    """
    required_fields = ["filename", "size", "mime_type"]
    
    # Check for required fields
    for field in required_fields:
        if field not in metadata:
            error = ServiceError(
                message=f"Missing required metadata field: {field}",
                category=ErrorCategory.VALIDATION,
                details={"metadata": metadata}
            )
            return False, error
    
    # Validate MIME type
    if not is_valid_mime_type(metadata["mime_type"]):
        error = ServiceError(
            message=f"Unsupported MIME type: {metadata['mime_type']}",
            category=ErrorCategory.VALIDATION,
            details={"metadata": metadata}
        )
        return False, error
    
    # Validate file extension
    if not is_valid_file_extension(metadata["filename"]):
        error = ServiceError(
            message=f"Unsupported file extension: {get_file_extension(metadata['filename'])}",
            category=ErrorCategory.VALIDATION,
            details={"metadata": metadata}
        )
        return False, error
    
    # Validate size
    if not is_valid_document_size(metadata["size"]):
        error = ServiceError(
            message=f"Invalid document size: {metadata['size']} bytes",
            category=ErrorCategory.VALIDATION,
            details={"metadata": metadata}
        )
        return False, error
    
    return True, None


def validate_document_content(content: bytes, metadata: Dict[str, Any]) -> Tuple[bool, Optional[ServiceError]]:
    """
    Validates document content against its metadata.
    
    Args:
        content: The document content as bytes
        metadata: The document metadata
        
    Returns:
        Tuple[bool, Optional[ServiceError]]: (is_valid, error)
    """
    # Validate actual size matches metadata
    actual_size = len(content)
    if actual_size != metadata["size"]:
        error = ServiceError(
            message=f"Document size mismatch: metadata={metadata['size']}, actual={actual_size}",
            category=ErrorCategory.VALIDATION,
            details={"metadata_size": metadata["size"], "actual_size": actual_size}
        )
        return False, error
    
    # Validate MIME type matches content
    detected_mime = get_mime_type(content)
    if detected_mime != metadata["mime_type"]:
        # Some flexibility for similar MIME types (e.g., image/jpg vs image/jpeg)
        if detected_mime.split('/')[0] != metadata["mime_type"].split('/')[0]:
            error = ServiceError(
                message=f"MIME type mismatch: metadata={metadata['mime_type']}, detected={detected_mime}",
                category=ErrorCategory.VALIDATION,
                details={"metadata_mime": metadata["mime_type"], "detected_mime": detected_mime}
            )
            return False, error
    
    return True, None


def validate_document(content: bytes, metadata: Dict[str, Any]) -> Tuple[bool, Optional[ServiceError]]:
    """
    Performs comprehensive document validation.
    
    Args:
        content: The document content as bytes
        metadata: The document metadata
        
    Returns:
        Tuple[bool, Optional[ServiceError]]: (is_valid, error)
    """
    # First validate metadata
    is_valid, error = validate_document_metadata(metadata)
    if not is_valid:
        return False, error
    
    # Then validate content against metadata
    is_valid, error = validate_document_content(content, metadata)
    if not is_valid:
        return False, error
    
    return True, None


def validate_ocr_request(message: Dict[str, Any]) -> Tuple[bool, Optional[ServiceError]]:
    """
    Validates an OCR request message from RabbitMQ.
    
    Args:
        message: The OCR request message
        
    Returns:
        Tuple[bool, Optional[ServiceError]]: (is_valid, error)
    """
    # Validate message schema
    is_valid, error_message = validate_message_schema(message)
    if not is_valid:
        error = ServiceError(
            message=error_message or "Invalid message schema",
            category=ErrorCategory.VALIDATION,
            details={"message": message}
        )
        return False, error
    
    # Validate document type
    if not is_valid_document_type(message["document_type"]):
        error = ServiceError(
            message=f"Unsupported document type: {message['document_type']}",
            category=ErrorCategory.VALIDATION,
            details={"message": message}
        )
        return False, error
    
    # Validate metadata
    is_valid, error = validate_document_metadata(message["metadata"])
    if not is_valid:
        return False, error
    
    return True, None


def apply_document_filters(metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
    """
    Applies configurable filters to document metadata.
    
    Args:
        metadata: The document metadata
        filters: The filters to apply
        
    Returns:
        bool: True if the document passes all filters, False otherwise
    """
    # Filter by document type
    if "document_types" in filters and filters["document_types"]:
        document_type = metadata.get("document_type")
        if document_type not in filters["document_types"]:
            logger.info(f"Document filtered out by document type: {document_type}")
            return False
    
    # Filter by MIME type
    if "mime_types" in filters and filters["mime_types"]:
        mime_type = metadata.get("mime_type")
        if mime_type not in filters["mime_types"]:
            logger.info(f"Document filtered out by MIME type: {mime_type}")
            return False
    
    # Filter by size
    if "min_size" in filters and metadata.get("size", 0) < filters["min_size"]:
        logger.info(f"Document filtered out by minimum size: {metadata.get('size')}")
        return False
    
    if "max_size" in filters and metadata.get("size", 0) > filters["max_size"]:
        logger.info(f"Document filtered out by maximum size: {metadata.get('size')}")
        return False
    
    # Filter by filename pattern
    if "filename_patterns" in filters and filters["filename_patterns"]:
        import re
        filename = metadata.get("filename", "")
        if not any(re.search(pattern, filename) for pattern in filters["filename_patterns"]):
            logger.info(f"Document filtered out by filename pattern: {filename}")
            return False
    
    # Filter by classification confidence
    if "min_confidence" in filters and filters["min_confidence"] > 0:
        classification = metadata.get("classification", {})
        confidence = classification.get("confidence", 0)
        if confidence < filters["min_confidence"]:
            logger.info(f"Document filtered out by classification confidence: {confidence}")
            return False
    
    return True


def get_document_filters() -> Dict[str, Any]:
    """
    Retrieves document filters from configuration.
    
    Returns:
        Dict[str, Any]: The document filters
    """
    # Get filters from configuration
    filters = getattr(app_config, "DOCUMENT_FILTERS", {})
    
    # Apply defaults if not specified
    if "min_size" not in filters:
        filters["min_size"] = DEFAULT_MIN_SIZE
    
    if "max_size" not in filters:
        filters["max_size"] = DEFAULT_MAX_SIZE
    
    return filters