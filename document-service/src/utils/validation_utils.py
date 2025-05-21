#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation utilities for the Document Service.

This module provides functions for validating document types, formats, sizes,
and other input data. It's essential for ensuring data integrity and preventing
processing of invalid or malicious content.
"""

import os
import re
import json
import magic
import logging
import hashlib
from typing import Dict, List, Optional, Set, Tuple, Union, Any, Callable
from pathlib import Path
from functools import wraps

# Import custom types
from ..types.documents import DocumentMetadata, DocumentType, DocumentContent
from ..types.messages import MessagePayload
from ..types.errors import ServiceError

# Configure logger
logger = logging.getLogger(__name__)

# Constants for document validation
MAX_DOCUMENT_SIZE_MB = 25  # Maximum document size in MB
MIN_DOCUMENT_SIZE_KB = 1   # Minimum document size in KB

# Supported MIME types and their corresponding file extensions
SUPPORTED_MIME_TYPES = {
    # PDF documents
    'application/pdf': ['.pdf'],
    
    # TIFF images
    'image/tiff': ['.tiff', '.tif'],
    
    # JPEG images
    'image/jpeg': ['.jpg', '.jpeg'],
    
    # PNG images
    'image/png': ['.png']
}

# Flat list of all supported file extensions
SUPPORTED_EXTENSIONS = [ext for exts in SUPPORTED_MIME_TYPES.values() for ext in exts]

# Suspicious patterns that might indicate malicious content
SUSPICIOUS_PATTERNS = [
    rb'<%[\s]*eval',      # ASP/PHP code execution
    rb'<script[\s>]',     # JavaScript
    rb'function\(\)',     # JavaScript function
    rb'\beval\s*\(',     # JavaScript eval
    rb'ExecuteGlobal',    # VBScript code execution
    rb'ShellExecute',     # Windows API for executing programs
    rb'cmd\.exe',         # Windows command shell
    rb'/bin/sh',          # Unix shell
    rb'/bin/bash',        # Bash shell
    rb'document\.write',  # JavaScript document manipulation
    rb'\bping\s',         # Network commands
    rb'\bnmap\s',         # Network scanning
    rb'\btelnet\s',       # Network access
    rb'\bssh\s',          # SSH commands
]

# Document type to MIME type mapping for validation
DOCUMENT_TYPE_MIME_MAPPING = {
    DocumentType.APPLICATION.name: ['application/pdf'],
    DocumentType.TAX_RETURN.name: ['application/pdf', 'image/tiff'],
    DocumentType.BANK_STATEMENT.name: ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
    DocumentType.PAY_STUB.name: ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
    DocumentType.ID_DOCUMENT.name: ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
    DocumentType.OTHER.name: list(SUPPORTED_MIME_TYPES.keys())
}


def validation_decorator(func: Callable) -> Callable:
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
        except Exception as e:
            logger.error(f"Validation error in {func.__name__}: {str(e)}")
            # Return validation failure with error message
            if func.__annotations__.get('return') == bool:
                return False
            else:
                return False, f"Validation error: {str(e)}"
    return wrapper


@validation_decorator
def is_valid_document_size(file_size: int) -> bool:
    """
    Validate if the document size is within acceptable limits.
    
    Args:
        file_size: Size of the file in bytes
        
    Returns:
        bool: True if the file size is valid, False otherwise
    """
    # Convert limits to bytes for comparison
    max_size_bytes = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
    min_size_bytes = MIN_DOCUMENT_SIZE_KB * 1024
    
    if file_size > max_size_bytes:
        logger.warning(f"Document size {file_size} bytes exceeds maximum limit of {max_size_bytes} bytes")
        return False
    
    if file_size < min_size_bytes:
        logger.warning(f"Document size {file_size} bytes is below minimum limit of {min_size_bytes} bytes")
        return False
    
    return True


@validation_decorator
def get_mime_type(file_path: str) -> str:
    """
    Detect the MIME type of a file using python-magic.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Detected MIME type
    """
    try:
        mime = magic.Magic(mime=True)
        return mime.from_file(file_path)
    except Exception as e:
        logger.error(f"Failed to detect MIME type for {file_path}: {str(e)}")
        raise ServiceError(f"MIME type detection failed: {str(e)}")


@validation_decorator
def get_mime_type_from_buffer(buffer: bytes) -> str:
    """
    Detect the MIME type from a bytes buffer using python-magic.
    
    Args:
        buffer: File content as bytes
        
    Returns:
        str: Detected MIME type
    """
    try:
        mime = magic.Magic(mime=True)
        return mime.from_buffer(buffer)
    except Exception as e:
        logger.error(f"Failed to detect MIME type from buffer: {str(e)}")
        raise ServiceError(f"MIME type detection failed: {str(e)}")


@validation_decorator
def is_supported_mime_type(mime_type: str) -> bool:
    """
    Check if the MIME type is in the list of supported types.
    
    Args:
        mime_type: MIME type to check
        
    Returns:
        bool: True if supported, False otherwise
    """
    return mime_type in SUPPORTED_MIME_TYPES


@validation_decorator
def is_supported_file_extension(file_path: str) -> bool:
    """
    Check if the file has a supported extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if the extension is supported, False otherwise
    """
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


@validation_decorator
def validate_document_metadata(metadata: DocumentMetadata) -> Tuple[bool, Optional[str]]:
    """
    Validate document metadata for required fields and valid values.
    
    Args:
        metadata: DocumentMetadata object to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not metadata.filename:
        return False, "Filename is required"
    
    if not metadata.mime_type:
        return False, "MIME type is required"
    
    if not is_supported_mime_type(metadata.mime_type):
        return False, f"Unsupported MIME type: {metadata.mime_type}"
    
    if not is_valid_document_size(metadata.size):
        return False, f"Invalid document size: {metadata.size} bytes"
    
    return True, None


@validation_decorator
def validate_document_content(content: DocumentContent, metadata: DocumentMetadata) -> Tuple[bool, Optional[str]]:
    """
    Validate document content against its metadata and check for malicious content.
    
    Args:
        content: Document content as bytes
        metadata: Document metadata
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not content:
        return False, "Document content is empty"
    
    # Verify the actual size matches the metadata
    actual_size = len(content)
    if actual_size != metadata.size:
        return False, f"Content size {actual_size} doesn't match metadata size {metadata.size}"
    
    # Verify the actual MIME type matches the metadata
    try:
        actual_mime_type = get_mime_type_from_buffer(content)
        if actual_mime_type != metadata.mime_type:
            return False, f"Content MIME type {actual_mime_type} doesn't match metadata MIME type {metadata.mime_type}"
    except ServiceError:
        return False, "Failed to detect content MIME type"
    
    # Check for malicious content
    if contains_malicious_content(content):
        return False, "Document contains potentially malicious content"
    
    return True, None


@validation_decorator
def contains_malicious_content(content: bytes) -> bool:
    """
    Check if the document contains potentially malicious content.
    
    Args:
        content: Document content as bytes
        
    Returns:
        bool: True if suspicious patterns are found, False otherwise
    """
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, content, re.IGNORECASE):
            logger.warning(f"Suspicious pattern detected: {pattern}")
            return True
    
    return False


@validation_decorator
def validate_message_schema(message: Dict[str, Any], schema_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a message against a predefined JSON schema.
    
    Args:
        message: Message dictionary to validate
        schema_type: Type of schema to validate against (e.g., 'document', 'classification')
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Load the appropriate schema based on schema_type
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'schemas', f"{schema_type}.json")
    
    try:
        with open(schema_path, 'r') as f:
            schema = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Failed to load schema {schema_type}: {str(e)}")
        return False, f"Schema validation error: {str(e)}"
    
    try:
        # Use jsonschema for validation if available, otherwise do basic validation
        try:
            import jsonschema
            jsonschema.validate(message, schema)
            return True, None
        except ImportError:
            # Fallback to basic validation if jsonschema is not available
            return basic_schema_validation(message, schema)
    except Exception as e:
        return False, f"Schema validation error: {str(e)}"


@validation_decorator
def basic_schema_validation(message: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Basic schema validation without using jsonschema library.
    
    Args:
        message: Message dictionary to validate
        schema: Schema dictionary to validate against
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Check required properties
    required = schema.get('required', [])
    for prop in required:
        if prop not in message:
            return False, f"Missing required property: {prop}"
    
    # Check property types for properties that exist in the message
    properties = schema.get('properties', {})
    for prop, value in message.items():
        if prop in properties:
            prop_schema = properties[prop]
            prop_type = prop_schema.get('type')
            
            if prop_type == 'string' and not isinstance(value, str):
                return False, f"Property {prop} should be a string"
            elif prop_type == 'number' and not isinstance(value, (int, float)):
                return False, f"Property {prop} should be a number"
            elif prop_type == 'integer' and not isinstance(value, int):
                return False, f"Property {prop} should be an integer"
            elif prop_type == 'boolean' and not isinstance(value, bool):
                return False, f"Property {prop} should be a boolean"
            elif prop_type == 'array' and not isinstance(value, list):
                return False, f"Property {prop} should be an array"
            elif prop_type == 'object' and not isinstance(value, dict):
                return False, f"Property {prop} should be an object"
    
    return True, None


@validation_decorator
def validate_document_type(document_type: str) -> bool:
    """
    Validate if the document type is one of the supported types.
    
    Args:
        document_type: Document type to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        # Check if the document_type is a valid DocumentType enum value
        DocumentType[document_type]
        return True
    except (KeyError, ValueError):
        logger.warning(f"Invalid document type: {document_type}")
        return False


@validation_decorator
def validate_document_type_mime_compatibility(document_type: str, mime_type: str) -> bool:
    """
    Validate if the document type is compatible with the MIME type.
    
    Args:
        document_type: Document type to validate
        mime_type: MIME type to check compatibility with
        
    Returns:
        bool: True if compatible, False otherwise
    """
    if not validate_document_type(document_type):
        return False
    
    if not is_supported_mime_type(mime_type):
        return False
    
    compatible_mime_types = DOCUMENT_TYPE_MIME_MAPPING.get(document_type, [])
    return mime_type in compatible_mime_types


@validation_decorator
def validate_message_payload(payload: MessagePayload) -> Tuple[bool, Optional[str]]:
    """
    Validate a RabbitMQ message payload for required fields and valid values.
    
    Args:
        payload: MessagePayload object to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not payload.message_id:
        return False, "Message ID is required"
    
    if not payload.document_id:
        return False, "Document ID is required"
    
    if not payload.timestamp:
        return False, "Timestamp is required"
    
    # Additional payload-specific validations can be added here
    
    return True, None


@validation_decorator
def validate_email_sender(sender: str, allowed_domains: List[str]) -> bool:
    """
    Validate if the email sender is from an allowed domain.
    
    Args:
        sender: Email address of the sender
        allowed_domains: List of allowed email domains
        
    Returns:
        bool: True if the sender is from an allowed domain, False otherwise
    """
    if not sender or '@' not in sender:
        return False
    
    domain = sender.split('@')[-1].lower()
    return domain in allowed_domains


@validation_decorator
def validate_file_hash(file_hash: str, expected_hash: str) -> bool:
    """
    Validate if the file hash matches the expected hash.
    
    Args:
        file_hash: Calculated hash of the file
        expected_hash: Expected hash value
        
    Returns:
        bool: True if the hashes match, False otherwise
    """
    return file_hash == expected_hash


@validation_decorator
def calculate_file_hash(content: bytes, algorithm: str = 'sha256') -> str:
    """
    Calculate a hash for the given file content.
    
    Args:
        content: File content as bytes
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        str: Calculated hash value
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    elif algorithm == 'sha512':
        hash_obj = hashlib.sha512()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    hash_obj.update(content)
    return hash_obj.hexdigest()


@validation_decorator
def validate_document_structure(content: bytes, document_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validate the document structure based on its type.
    
    Args:
        content: Document content as bytes
        document_type: Type of document to validate structure for
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not validate_document_type(document_type):
        return False, f"Invalid document type: {document_type}"
    
    # Detect MIME type
    mime_type = get_mime_type_from_buffer(content)
    
    # Check if the document type is compatible with the MIME type
    if not validate_document_type_mime_compatibility(document_type, mime_type):
        return False, f"Document type {document_type} is not compatible with MIME type {mime_type}"
    
    # Perform document type-specific structure validation
    if document_type == DocumentType.APPLICATION.name:
        # Application forms should be PDF and have certain characteristics
        if mime_type != 'application/pdf':
            return False, "Application forms must be in PDF format"
        
        # Additional application form validation logic can be added here
        # For example, check for required form fields or page count
        
    elif document_type == DocumentType.TAX_RETURN.name:
        # Tax returns should be PDF or TIFF and have certain characteristics
        if mime_type not in ['application/pdf', 'image/tiff']:
            return False, "Tax returns must be in PDF or TIFF format"
        
        # Additional tax return validation logic can be added here
        
    # Add more document type-specific validations as needed
    
    return True, None


@validation_decorator
def validate_document_page_count(content: bytes, mime_type: str, min_pages: int = 1, max_pages: int = 100) -> Tuple[bool, Optional[str]]:
    """
    Validate the document page count is within acceptable limits.
    
    Args:
        content: Document content as bytes
        mime_type: MIME type of the document
        min_pages: Minimum acceptable number of pages
        max_pages: Maximum acceptable number of pages
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # For PDF documents, use PyPDF2 to count pages if available
    if mime_type == 'application/pdf':
        try:
            import io
            from PyPDF2 import PdfReader
            
            pdf_file = io.BytesIO(content)
            pdf_reader = PdfReader(pdf_file)
            page_count = len(pdf_reader.pages)
            
            if page_count < min_pages:
                return False, f"Document has {page_count} pages, which is less than the minimum of {min_pages}"
            
            if page_count > max_pages:
                return False, f"Document has {page_count} pages, which exceeds the maximum of {max_pages}"
            
            return True, None
        except ImportError:
            logger.warning("PyPDF2 not available for page count validation")
            return True, None  # Skip validation if PyPDF2 is not available
        except Exception as e:
            return False, f"Failed to validate PDF page count: {str(e)}"
    
    # For TIFF images, use PIL/Pillow to count pages if available
    elif mime_type == 'image/tiff':
        try:
            import io
            from PIL import Image
            
            tiff_file = io.BytesIO(content)
            img = Image.open(tiff_file)
            
            # Count frames in the TIFF file
            page_count = 0
            try:
                while True:
                    page_count += 1
                    img.seek(img.tell() + 1)
            except EOFError:
                pass  # End of frames
            
            if page_count < min_pages:
                return False, f"Document has {page_count} pages, which is less than the minimum of {min_pages}"
            
            if page_count > max_pages:
                return False, f"Document has {page_count} pages, which exceeds the maximum of {max_pages}"
            
            return True, None
        except ImportError:
            logger.warning("PIL/Pillow not available for TIFF page count validation")
            return True, None  # Skip validation if PIL is not available
        except Exception as e:
            return False, f"Failed to validate TIFF page count: {str(e)}"
    
    # For other formats, assume single page
    return True, None


@validation_decorator
def validate_document_resolution(content: bytes, mime_type: str, min_dpi: int = 200) -> Tuple[bool, Optional[str]]:
    """
    Validate the document resolution is sufficient for OCR processing.
    
    Args:
        content: Document content as bytes
        mime_type: MIME type of the document
        min_dpi: Minimum acceptable resolution in DPI
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # Only validate resolution for image formats
    if mime_type in ['image/jpeg', 'image/png', 'image/tiff']:
        try:
            import io
            from PIL import Image
            
            img_file = io.BytesIO(content)
            img = Image.open(img_file)
            
            # Get DPI information if available
            dpi_info = img.info.get('dpi')
            
            if dpi_info:
                # DPI info is usually a tuple of (x_dpi, y_dpi)
                x_dpi, y_dpi = dpi_info
                min_dimension_dpi = min(x_dpi, y_dpi)
                
                if min_dimension_dpi < min_dpi:
                    return False, f"Document resolution {min_dimension_dpi} DPI is below minimum of {min_dpi} DPI"
            else:
                # If DPI info is not available, estimate from image dimensions
                # This is a rough estimate and may not be accurate
                width, height = img.size
                if width < 1000 or height < 1000:  # Rough estimate for low resolution
                    logger.warning(f"Document may have low resolution: {width}x{height} pixels")
            
            return True, None
        except ImportError:
            logger.warning("PIL/Pillow not available for resolution validation")
            return True, None  # Skip validation if PIL is not available
        except Exception as e:
            return False, f"Failed to validate document resolution: {str(e)}"
    
    # For non-image formats, skip resolution validation
    return True, None


@validation_decorator
def validate_document_against_rules(document: Dict[str, Any], rules: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
    """
    Validate a document against a set of configurable rules.
    
    Args:
        document: Document dictionary with metadata and content information
        rules: List of rule dictionaries with conditions and actions
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    for rule in rules:
        rule_name = rule.get('name', 'Unnamed rule')
        conditions = rule.get('conditions', [])
        action = rule.get('action', {})
        
        # Check if all conditions match
        conditions_match = True
        for condition in conditions:
            field = condition.get('field')
            operator = condition.get('operator')
            value = condition.get('value')
            
            if not field or not operator:
                continue
            
            # Get the field value from the document
            field_value = document.get(field)
            
            # Apply the operator
            if operator == 'equals' and field_value != value:
                conditions_match = False
                break
            elif operator == 'not_equals' and field_value == value:
                conditions_match = False
                break
            elif operator == 'contains' and (not isinstance(field_value, str) or value not in field_value):
                conditions_match = False
                break
            elif operator == 'not_contains' and (isinstance(field_value, str) and value in field_value):
                conditions_match = False
                break
            elif operator == 'greater_than' and (not isinstance(field_value, (int, float)) or field_value <= value):
                conditions_match = False
                break
            elif operator == 'less_than' and (not isinstance(field_value, (int, float)) or field_value >= value):
                conditions_match = False
                break
            elif operator == 'in' and field_value not in value:
                conditions_match = False
                break
            elif operator == 'not_in' and field_value in value:
                conditions_match = False
                break
        
        # If all conditions match, apply the action
        if conditions_match:
            action_type = action.get('type')
            
            if action_type == 'reject':
                reason = action.get('reason', f"Rejected by rule: {rule_name}")
                return False, reason
            elif action_type == 'flag':
                # Flagging doesn't reject the document, but logs a warning
                reason = action.get('reason', f"Flagged by rule: {rule_name}")
                logger.warning(f"Document flagged: {reason}")
    
    # If no rules rejected the document, it's valid
    return True, None