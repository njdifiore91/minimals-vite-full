#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Validation utilities for the OCR Service.

This module provides functions for validating document types, formats, sizes,
and other input data. It's essential for ensuring data integrity and preventing
processing of invalid or malicious content.

Functions:
    is_valid_document_type: Validates if a document type is supported
    is_valid_document_size: Validates if a document size is within limits
    is_valid_mime_type: Validates if a MIME type is supported
    validate_message_schema: Validates RabbitMQ message schema
    validate_document_format: Validates document format and structure
    validate_document_content: Validates document content for processing
    validate_extraction_request: Validates OCR extraction request
    get_document_validation_rules: Gets document validation rules
    apply_validation_rules: Applies validation rules to a document
"""

import os
import json
import logging
import mimetypes
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from pathlib import Path

# Import custom types
from ..types.messages import MessagePayload
from ..types.errors import ServiceError, ErrorCategory
from ..types.config import ConfigDict

# Setup logger
logger = logging.getLogger(__name__)

# Constants for document validation
SUPPORTED_DOCUMENT_TYPES = {
    'pdf': 'application/pdf',
    'tiff': 'image/tiff',
    'tif': 'image/tiff',
    'png': 'image/png',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg'
}

# Maximum document size (50MB)
MAX_DOCUMENT_SIZE_BYTES = 50 * 1024 * 1024

# Minimum document size (1KB)
MIN_DOCUMENT_SIZE_BYTES = 1024

# Maximum image dimensions
MAX_IMAGE_DIMENSIONS = (8000, 8000)  # Width, Height

# Minimum image dimensions for reliable OCR
MIN_IMAGE_DIMENSIONS = (100, 100)  # Width, Height


def is_valid_document_type(file_extension: str) -> bool:
    """
    Validates if a document type is supported based on file extension.
    
    Args:
        file_extension: The file extension to validate (without the dot)
        
    Returns:
        bool: True if the document type is supported, False otherwise
    """
    return file_extension.lower() in SUPPORTED_DOCUMENT_TYPES


def is_valid_mime_type(mime_type: str) -> bool:
    """
    Validates if a MIME type is supported for OCR processing.
    
    Args:
        mime_type: The MIME type to validate
        
    Returns:
        bool: True if the MIME type is supported, False otherwise
    """
    return mime_type in SUPPORTED_DOCUMENT_TYPES.values()


def is_valid_document_size(file_size: int) -> bool:
    """
    Validates if a document size is within acceptable limits.
    
    Args:
        file_size: The file size in bytes
        
    Returns:
        bool: True if the document size is valid, False otherwise
    """
    return MIN_DOCUMENT_SIZE_BYTES <= file_size <= MAX_DOCUMENT_SIZE_BYTES


def is_valid_image_dimensions(width: int, height: int) -> bool:
    """
    Validates if image dimensions are within acceptable limits for OCR processing.
    
    Args:
        width: Image width in pixels
        height: Image height in pixels
        
    Returns:
        bool: True if the dimensions are valid, False otherwise
    """
    return (MIN_IMAGE_DIMENSIONS[0] <= width <= MAX_IMAGE_DIMENSIONS[0] and
            MIN_IMAGE_DIMENSIONS[1] <= height <= MAX_IMAGE_DIMENSIONS[1])


def validate_message_schema(message: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validates the schema of a RabbitMQ message for OCR processing.
    
    Args:
        message: The message payload to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    required_fields = ['document_id', 'document_type', 'storage_path', 'classification']
    
    # Check for required fields
    for field in required_fields:
        if field not in message:
            return False, f"Missing required field: {field}"
    
    # Validate document_type
    if not is_valid_document_type(Path(message['storage_path']).suffix.lstrip('.')):
        return False, f"Unsupported document type: {message['document_type']}"
    
    # Validate classification
    valid_classifications = ['typed', 'handwritten', 'mixed', 'unknown']
    if message['classification'] not in valid_classifications:
        return False, f"Invalid classification: {message['classification']}"
    
    return True, None


def validate_document_format(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the format and structure of a document.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    
    # Get file extension and validate
    file_extension = Path(file_path).suffix.lstrip('.')
    if not is_valid_document_type(file_extension):
        return False, f"Unsupported document type: {file_extension}"
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if not is_valid_document_size(file_size):
        return False, f"Invalid document size: {file_size} bytes"
    
    # Detect MIME type and validate
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type is None or not is_valid_mime_type(mime_type):
        return False, f"Invalid or unsupported MIME type: {mime_type}"
    
    return True, None


def validate_document_content(file_path: str, document_type: str) -> Tuple[bool, Optional[str]]:
    """
    Validates the content of a document for OCR processing.
    
    This function performs deeper validation of document content beyond basic format checks.
    It checks for document corruption, password protection, and other issues that might
    prevent successful OCR processing.
    
    Args:
        file_path: Path to the document file
        document_type: Type of the document (pdf, tiff, etc.)
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # First validate format
    is_valid, error_message = validate_document_format(file_path)
    if not is_valid:
        return False, error_message
    
    # Additional validation based on document type
    if document_type.lower() == 'pdf':
        # Check for password protection or corruption in PDF
        try:
            import PyPDF2
            with open(file_path, 'rb') as pdf_file:
                try:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    if pdf_reader.is_encrypted:
                        return False, "PDF is password protected"
                    # Check if PDF has pages
                    if len(pdf_reader.pages) == 0:
                        return False, "PDF has no pages"
                except PyPDF2.errors.PdfReadError:
                    return False, "PDF is corrupted or invalid"
        except ImportError:
            logger.warning("PyPDF2 not available, skipping detailed PDF validation")
    
    elif document_type.lower() in ['tiff', 'tif', 'png', 'jpg', 'jpeg']:
        # Check image properties for image-based documents
        try:
            from PIL import Image
            try:
                with Image.open(file_path) as img:
                    width, height = img.size
                    if not is_valid_image_dimensions(width, height):
                        return False, f"Invalid image dimensions: {width}x{height}"
                    
                    # Check if image is empty or corrupted
                    img.load()
            except Exception as e:
                return False, f"Image is corrupted or invalid: {str(e)}"
        except ImportError:
            logger.warning("PIL not available, skipping detailed image validation")
    
    return True, None


def validate_extraction_request(message: MessagePayload) -> Tuple[bool, Optional[ServiceError]]:
    """
    Validates an OCR extraction request message.
    
    This function performs comprehensive validation of an OCR extraction request,
    including message schema, document access, and processing eligibility.
    
    Args:
        message: The OCR extraction request message
        
    Returns:
        Tuple[bool, Optional[ServiceError]]: (is_valid, error)
    """
    try:
        # Validate message schema
        is_valid, error_message = validate_message_schema(message)
        if not is_valid:
            return False, ServiceError(
                message=error_message,
                category=ErrorCategory.VALIDATION,
                details={
                    "message_id": message.get("message_id", "unknown"),
                    "document_id": message.get("document_id", "unknown")
                }
            )
        
        # Additional validation logic can be added here
        # For example, checking if the document is already processed,
        # or if it meets specific business rules for processing
        
        return True, None
    
    except Exception as e:
        logger.error(f"Error validating extraction request: {str(e)}")
        return False, ServiceError(
            message="Failed to validate extraction request",
            category=ErrorCategory.SYSTEM,
            details={
                "message_id": message.get("message_id", "unknown"),
                "document_id": message.get("document_id", "unknown"),
                "error": str(e)
            }
        )


def get_document_validation_rules(document_type: str, classification: str) -> Dict[str, Any]:
    """
    Gets the validation rules for a specific document type and classification.
    
    Args:
        document_type: The document type (pdf, tiff, etc.)
        classification: The document classification (typed, handwritten, mixed)
        
    Returns:
        Dict[str, Any]: Validation rules for the document
    """
    # Base validation rules for all document types
    base_rules = {
        "max_size_bytes": MAX_DOCUMENT_SIZE_BYTES,
        "min_size_bytes": MIN_DOCUMENT_SIZE_BYTES,
        "max_pages": 100,  # Default max pages
        "require_text_content": True,  # Default to requiring text content
    }
    
    # Document type specific rules
    type_rules = {
        "pdf": {
            "max_pages": 200,  # PDFs can have more pages
            "allow_scanned": True,
            "require_text_content": False,  # PDFs might be scanned without text
        },
        "tiff": {
            "max_pages": 50,  # Multi-page TIFFs
            "min_dpi": 200,  # Minimum DPI for TIFF
            "require_text_content": False,  # TIFFs are images
        },
        "png": {
            "max_pages": 1,  # PNGs are single page
            "min_dpi": 150,  # Minimum DPI for PNG
            "require_text_content": False,  # PNGs are images
        },
        "jpg": {
            "max_pages": 1,  # JPGs are single page
            "min_dpi": 150,  # Minimum DPI for JPG
            "require_text_content": False,  # JPGs are images
        },
        "jpeg": {
            "max_pages": 1,  # JPEGs are single page
            "min_dpi": 150,  # Minimum DPI for JPEG
            "require_text_content": False,  # JPEGs are images
        }
    }
    
    # Classification specific rules
    classification_rules = {
        "typed": {
            "min_confidence": 0.75,  # Higher confidence for typed text
            "ocr_model": "typed_text_model",
        },
        "handwritten": {
            "min_confidence": 0.60,  # Lower confidence threshold for handwritten
            "ocr_model": "handwritten_text_model",
        },
        "mixed": {
            "min_confidence": 0.65,  # Balanced confidence for mixed content
            "ocr_model": "hybrid_text_model",
        },
        "unknown": {
            "min_confidence": 0.70,  # Default confidence threshold
            "ocr_model": "hybrid_text_model",  # Use hybrid model for unknown
        }
    }
    
    # Combine rules
    rules = base_rules.copy()
    
    # Add document type specific rules
    if document_type.lower() in type_rules:
        rules.update(type_rules[document_type.lower()])
    
    # Add classification specific rules
    if classification.lower() in classification_rules:
        rules.update(classification_rules[classification.lower()])
    
    return rules


def apply_validation_rules(file_path: str, rules: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Applies validation rules to a document.
    
    Args:
        file_path: Path to the document file
        rules: Validation rules to apply
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    if not os.path.exists(file_path):
        return False, f"File does not exist: {file_path}"
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size < rules.get("min_size_bytes", MIN_DOCUMENT_SIZE_BYTES):
        return False, f"Document too small: {file_size} bytes"
    
    if file_size > rules.get("max_size_bytes", MAX_DOCUMENT_SIZE_BYTES):
        return False, f"Document too large: {file_size} bytes"
    
    # Get file extension
    file_extension = Path(file_path).suffix.lstrip('.')
    
    # Additional validation based on document type
    if file_extension.lower() == 'pdf':
        try:
            import PyPDF2
            with open(file_path, 'rb') as pdf_file:
                try:
                    pdf_reader = PyPDF2.PdfReader(pdf_file)
                    
                    # Check if PDF is encrypted
                    if pdf_reader.is_encrypted:
                        return False, "PDF is password protected"
                    
                    # Check page count
                    page_count = len(pdf_reader.pages)
                    if page_count > rules.get("max_pages", 100):
                        return False, f"PDF has too many pages: {page_count}"
                    
                    # Check for text content if required
                    if rules.get("require_text_content", False):
                        # Check first page for text
                        first_page = pdf_reader.pages[0]
                        text = first_page.extract_text()
                        if not text.strip():
                            # If no text found and scanned PDFs are not allowed
                            if not rules.get("allow_scanned", True):
                                return False, "PDF appears to be scanned without text content"
                except PyPDF2.errors.PdfReadError:
                    return False, "PDF is corrupted or invalid"
        except ImportError:
            logger.warning("PyPDF2 not available, skipping detailed PDF validation")
    
    elif file_extension.lower() in ['tiff', 'tif', 'png', 'jpg', 'jpeg']:
        try:
            from PIL import Image
            try:
                with Image.open(file_path) as img:
                    # Check image dimensions
                    width, height = img.size
                    if not is_valid_image_dimensions(width, height):
                        return False, f"Invalid image dimensions: {width}x{height}"
                    
                    # Check DPI if available
                    if 'dpi' in img.info:
                        dpi = img.info['dpi']
                        min_dpi = rules.get("min_dpi", 0)
                        if dpi[0] < min_dpi or dpi[1] < min_dpi:
                            return False, f"Image DPI too low: {dpi}"
                    
                    # Check number of frames for multi-page formats (TIFF)
                    if hasattr(img, 'n_frames'):
                        if img.n_frames > rules.get("max_pages", 1):
                            return False, f"Image has too many pages/frames: {img.n_frames}"
            except Exception as e:
                return False, f"Image is corrupted or invalid: {str(e)}"
        except ImportError:
            logger.warning("PIL not available, skipping detailed image validation")
    
    return True, None


def validate_document_for_ocr(file_path: str, document_type: str, classification: str) -> Tuple[bool, Optional[str]]:
    """
    Performs comprehensive validation of a document for OCR processing.
    
    This function combines format validation, content validation, and rule-based validation
    to determine if a document is suitable for OCR processing.
    
    Args:
        file_path: Path to the document file
        document_type: Type of the document (pdf, tiff, etc.)
        classification: Document classification (typed, handwritten, mixed)
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
    """
    # First validate format and content
    is_valid, error_message = validate_document_content(file_path, document_type)
    if not is_valid:
        return False, error_message
    
    # Get and apply validation rules
    rules = get_document_validation_rules(document_type, classification)
    is_valid, error_message = apply_validation_rules(file_path, rules)
    if not is_valid:
        return False, error_message
    
    return True, None