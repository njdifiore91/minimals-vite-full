#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the validation_utils module.

This module contains tests for document type validation, format validation,
size validation, MIME type detection, and message schema validation to ensure
data integrity and prevent processing of invalid content.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from jsonschema import ValidationError

from src.utils import validation_utils
from src.types.documents import DocumentType
from src.types.errors import ServiceError, ErrorCategory


# ===== Document Type Validation Tests =====

def test_is_valid_document_type_with_valid_types():
    """Test is_valid_document_type with valid document types."""
    # Test all valid document types from the DocumentType enum
    for doc_type in DocumentType:
        assert validation_utils.is_valid_document_type(doc_type.name) is True


def test_is_valid_document_type_with_invalid_types():
    """Test is_valid_document_type with invalid document types."""
    invalid_types = ["INVALID_TYPE", "PDF", "JPEG", "UNKNOWN", "", None, 123]
    for doc_type in invalid_types:
        assert validation_utils.is_valid_document_type(doc_type) is False


# ===== MIME Type Validation Tests =====

def test_is_valid_mime_type_with_valid_types():
    """Test is_valid_mime_type with valid MIME types."""
    valid_mime_types = [
        "application/pdf",
        "image/tiff",
        "image/jpeg",
        "image/png",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ]
    for mime_type in valid_mime_types:
        assert validation_utils.is_valid_mime_type(mime_type) is True


def test_is_valid_mime_type_with_invalid_types():
    """Test is_valid_mime_type with invalid MIME types."""
    invalid_mime_types = [
        "text/plain",
        "application/json",
        "application/xml",
        "image/gif",
        "image/webp",
        "application/zip",
        "",
        None
    ]
    for mime_type in invalid_mime_types:
        assert validation_utils.is_valid_mime_type(mime_type) is False


# ===== MIME Type Detection Tests =====

def test_get_mime_type(binary_content):
    """Test get_mime_type with various binary content."""
    with patch('magic.Magic') as mock_magic:
        # Configure the mock to return specific MIME types
        mock_magic_instance = MagicMock()
        mock_magic.return_value = mock_magic_instance
        
        # Test PDF detection
        mock_magic_instance.from_buffer.return_value = "application/pdf"
        assert validation_utils.get_mime_type(binary_content["pdf"]) == "application/pdf"
        
        # Test TIFF detection
        mock_magic_instance.from_buffer.return_value = "image/tiff"
        assert validation_utils.get_mime_type(binary_content["tiff"]) == "image/tiff"
        
        # Test PNG detection
        mock_magic_instance.from_buffer.return_value = "image/png"
        assert validation_utils.get_mime_type(binary_content["png"]) == "image/png"
        
        # Test JPEG detection
        mock_magic_instance.from_buffer.return_value = "image/jpeg"
        assert validation_utils.get_mime_type(binary_content["jpeg"]) == "image/jpeg"


def test_get_mime_type_with_exception():
    """Test get_mime_type when an exception occurs."""
    with patch('magic.Magic') as mock_magic:
        # Configure the mock to raise an exception
        mock_magic_instance = MagicMock()
        mock_magic.return_value = mock_magic_instance
        mock_magic_instance.from_buffer.side_effect = Exception("Test exception")
        
        # Should return the default fallback MIME type
        assert validation_utils.get_mime_type(b"test content") == "application/octet-stream"


# ===== File Extension Tests =====

def test_get_file_extension():
    """Test get_file_extension with various filenames."""
    test_cases = [
        ("document.pdf", ".pdf"),
        ("image.jpg", ".jpg"),
        ("image.jpeg", ".jpeg"),
        ("document.PDF", ".pdf"),  # Should be lowercase
        ("file.with.multiple.dots.txt", ".txt"),
        ("no_extension", ""),
        (".hidden_file", ""),
        ("path/to/document.pdf", ".pdf"),
        ("C:\\Windows\\file.docx", ".docx")
    ]
    
    for filename, expected_ext in test_cases:
        assert validation_utils.get_file_extension(filename) == expected_ext


def test_is_valid_file_extension():
    """Test is_valid_file_extension with various filenames."""
    valid_filenames = [
        "document.pdf",
        "image.jpg",
        "image.jpeg",
        "image.png",
        "document.tiff",
        "document.tif",
        "spreadsheet.xlsx",
        "spreadsheet.xls",
        "document.doc",
        "document.docx",
        "DOCUMENT.PDF"  # Should be case-insensitive
    ]
    
    invalid_filenames = [
        "document.txt",
        "image.gif",
        "archive.zip",
        "no_extension",
        ".hidden_file",
        "document.invalid"
    ]
    
    for filename in valid_filenames:
        assert validation_utils.is_valid_file_extension(filename) is True
        
    for filename in invalid_filenames:
        assert validation_utils.is_valid_file_extension(filename) is False


# ===== Document Size Validation Tests =====

def test_is_valid_document_size():
    """Test is_valid_document_size with various sizes."""
    # Default limits: min=1KB (1024 bytes), max=20MB (20971520 bytes)
    valid_sizes = [
        1024,  # Minimum size
        2048,  # 2KB
        1048576,  # 1MB
        10485760,  # 10MB
        20971520  # Maximum size
    ]
    
    too_small_sizes = [
        0,
        512,  # 512 bytes
        1023  # Just below minimum
    ]
    
    too_large_sizes = [
        20971521,  # Just above maximum
        52428800,  # 50MB
        104857600  # 100MB
    ]
    
    for size in valid_sizes:
        assert validation_utils.is_valid_document_size(size) is True
        
    for size in too_small_sizes:
        assert validation_utils.is_valid_document_size(size) is False
        
    for size in too_large_sizes:
        assert validation_utils.is_valid_document_size(size) is False


def test_is_valid_document_size_with_custom_limits():
    """Test is_valid_document_size with custom size limits."""
    # Custom limits: min=500 bytes, max=5MB (5242880 bytes)
    min_size = 500
    max_size = 5242880
    
    valid_sizes = [
        500,  # Minimum size
        1024,  # 1KB
        1048576,  # 1MB
        5242880  # Maximum size
    ]
    
    too_small_sizes = [
        0,
        499  # Just below minimum
    ]
    
    too_large_sizes = [
        5242881,  # Just above maximum
        10485760  # 10MB
    ]
    
    for size in valid_sizes:
        assert validation_utils.is_valid_document_size(size, min_size, max_size) is True
        
    for size in too_small_sizes:
        assert validation_utils.is_valid_document_size(size, min_size, max_size) is False
        
    for size in too_large_sizes:
        assert validation_utils.is_valid_document_size(size, min_size, max_size) is False


# ===== Message Schema Validation Tests =====

def test_validate_message_schema_with_valid_message():
    """Test validate_message_schema with a valid message."""
    valid_message = {
        "document_id": "doc-123456",
        "document_type": "APPLICATION",
        "storage_path": "s3://bucket/path/to/document.pdf",
        "metadata": {
            "filename": "document.pdf",
            "size": 1048576,
            "mime_type": "application/pdf",
            "created_at": "2023-01-15T14:30:45Z"
        }
    }
    
    is_valid, error_message = validation_utils.validate_message_schema(valid_message)
    assert is_valid is True
    assert error_message is None


def test_validate_message_schema_with_invalid_message():
    """Test validate_message_schema with an invalid message."""
    # Missing required fields
    invalid_message_missing_fields = {
        "document_id": "doc-123456",
        # Missing document_type
        "storage_path": "s3://bucket/path/to/document.pdf"
        # Missing metadata
    }
    
    is_valid, error_message = validation_utils.validate_message_schema(invalid_message_missing_fields)
    assert is_valid is False
    assert error_message is not None
    assert "'document_type' is a required property" in error_message
    
    # Invalid document_type value
    invalid_message_wrong_type = {
        "document_id": "doc-123456",
        "document_type": "INVALID_TYPE",  # Not in enum
        "storage_path": "s3://bucket/path/to/document.pdf",
        "metadata": {
            "filename": "document.pdf",
            "size": 1048576,
            "mime_type": "application/pdf"
        }
    }
    
    is_valid, error_message = validation_utils.validate_message_schema(invalid_message_wrong_type)
    assert is_valid is False
    assert error_message is not None
    assert "'INVALID_TYPE' is not one of" in error_message


def test_validate_message_schema_with_custom_schema():
    """Test validate_message_schema with a custom schema."""
    custom_schema = {
        "type": "object",
        "required": ["id", "name"],
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        }
    }
    
    valid_message = {
        "id": "123",
        "name": "John Doe",
        "age": 30
    }
    
    invalid_message = {
        "id": "123",
        "name": "John Doe",
        "age": -5  # Below minimum
    }
    
    is_valid, error_message = validation_utils.validate_message_schema(valid_message, custom_schema)
    assert is_valid is True
    assert error_message is None
    
    is_valid, error_message = validation_utils.validate_message_schema(invalid_message, custom_schema)
    assert is_valid is False
    assert error_message is not None
    assert "minimum" in error_message


# ===== Document Metadata Validation Tests =====

def test_validate_document_metadata_with_valid_metadata():
    """Test validate_document_metadata with valid metadata."""
    valid_metadata = {
        "filename": "document.pdf",
        "size": 1048576,  # 1MB
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_metadata(valid_metadata)
    assert is_valid is True
    assert error is None


def test_validate_document_metadata_with_missing_fields():
    """Test validate_document_metadata with missing required fields."""
    # Missing filename
    missing_filename = {
        "size": 1048576,
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_metadata(missing_filename)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "filename" in error.message
    
    # Missing size
    missing_size = {
        "filename": "document.pdf",
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_metadata(missing_size)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "size" in error.message
    
    # Missing mime_type
    missing_mime_type = {
        "filename": "document.pdf",
        "size": 1048576
    }
    
    is_valid, error = validation_utils.validate_document_metadata(missing_mime_type)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "mime_type" in error.message


def test_validate_document_metadata_with_invalid_values():
    """Test validate_document_metadata with invalid field values."""
    # Invalid MIME type
    invalid_mime_type = {
        "filename": "document.pdf",
        "size": 1048576,
        "mime_type": "text/plain"  # Not supported
    }
    
    is_valid, error = validation_utils.validate_document_metadata(invalid_mime_type)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "MIME type" in error.message
    
    # Invalid file extension
    invalid_extension = {
        "filename": "document.txt",  # Not supported
        "size": 1048576,
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_metadata(invalid_extension)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "file extension" in error.message
    
    # Invalid size (too small)
    invalid_size_small = {
        "filename": "document.pdf",
        "size": 100,  # Too small
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_metadata(invalid_size_small)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "size" in error.message
    
    # Invalid size (too large)
    invalid_size_large = {
        "filename": "document.pdf",
        "size": 100 * 1024 * 1024,  # 100MB, too large
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_metadata(invalid_size_large)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "size" in error.message


# ===== Document Content Validation Tests =====

def test_validate_document_content_with_valid_content(binary_content):
    """Test validate_document_content with valid content."""
    # Valid PDF content
    pdf_content = binary_content["pdf"]
    pdf_metadata = {
        "filename": "document.pdf",
        "size": len(pdf_content),
        "mime_type": "application/pdf"
    }
    
    with patch('src.utils.validation_utils.get_mime_type') as mock_get_mime_type:
        mock_get_mime_type.return_value = "application/pdf"
        is_valid, error = validation_utils.validate_document_content(pdf_content, pdf_metadata)
        assert is_valid is True
        assert error is None


def test_validate_document_content_with_size_mismatch(binary_content):
    """Test validate_document_content with size mismatch."""
    pdf_content = binary_content["pdf"]
    pdf_metadata = {
        "filename": "document.pdf",
        "size": len(pdf_content) + 100,  # Incorrect size
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document_content(pdf_content, pdf_metadata)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "size mismatch" in error.message


def test_validate_document_content_with_mime_type_mismatch(binary_content):
    """Test validate_document_content with MIME type mismatch."""
    pdf_content = binary_content["pdf"]
    pdf_metadata = {
        "filename": "document.pdf",
        "size": len(pdf_content),
        "mime_type": "application/pdf"
    }
    
    with patch('src.utils.validation_utils.get_mime_type') as mock_get_mime_type:
        # Return a different MIME type than expected
        mock_get_mime_type.return_value = "application/xml"
        is_valid, error = validation_utils.validate_document_content(pdf_content, pdf_metadata)
        assert is_valid is False
        assert isinstance(error, ServiceError)
        assert error.category == ErrorCategory.VALIDATION
        assert "MIME type mismatch" in error.message


def test_validate_document_content_with_similar_mime_types(binary_content):
    """Test validate_document_content with similar but not identical MIME types."""
    jpeg_content = binary_content["jpeg"]
    jpeg_metadata = {
        "filename": "image.jpg",
        "size": len(jpeg_content),
        "mime_type": "image/jpeg"
    }
    
    with patch('src.utils.validation_utils.get_mime_type') as mock_get_mime_type:
        # Return a similar MIME type (same major type)
        mock_get_mime_type.return_value = "image/jpg"  # Slightly different
        is_valid, error = validation_utils.validate_document_content(jpeg_content, jpeg_metadata)
        # Should pass because both are image/* types
        assert is_valid is True
        assert error is None


# ===== Comprehensive Document Validation Tests =====

def test_validate_document_with_valid_document(binary_content):
    """Test validate_document with a valid document."""
    pdf_content = binary_content["pdf"]
    pdf_metadata = {
        "filename": "document.pdf",
        "size": len(pdf_content),
        "mime_type": "application/pdf"
    }
    
    with patch('src.utils.validation_utils.get_mime_type') as mock_get_mime_type:
        mock_get_mime_type.return_value = "application/pdf"
        is_valid, error = validation_utils.validate_document(pdf_content, pdf_metadata)
        assert is_valid is True
        assert error is None


def test_validate_document_with_invalid_metadata(binary_content):
    """Test validate_document with invalid metadata but valid content."""
    pdf_content = binary_content["pdf"]
    invalid_metadata = {
        "filename": "document.txt",  # Invalid extension
        "size": len(pdf_content),
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document(pdf_content, invalid_metadata)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "file extension" in error.message


def test_validate_document_with_invalid_content(binary_content):
    """Test validate_document with valid metadata but invalid content."""
    pdf_content = binary_content["pdf"]
    pdf_metadata = {
        "filename": "document.pdf",
        "size": len(pdf_content) + 100,  # Size mismatch
        "mime_type": "application/pdf"
    }
    
    is_valid, error = validation_utils.validate_document(pdf_content, pdf_metadata)
    assert is_valid is False
    assert isinstance(error, ServiceError)
    assert error.category == ErrorCategory.VALIDATION
    assert "size mismatch" in error.message


# ===== OCR Request Validation Tests =====

def test_validate_ocr_request_with_valid_request():
    """Test validate_ocr_request with a valid OCR request."""
    valid_request = {
        "document_id": "doc-123456",
        "document_type": "APPLICATION",
        "storage_path": "s3://bucket/path/to/document.pdf",
        "metadata": {
            "filename": "document.pdf",
            "size": 1048576,
            "mime_type": "application/pdf"
        }
    }
    
    with patch('src.utils.validation_utils.validate_message_schema') as mock_validate_schema, \
         patch('src.utils.validation_utils.validate_document_metadata') as mock_validate_metadata:
        
        mock_validate_schema.return_value = (True, None)
        mock_validate_metadata.return_value = (True, None)
        
        is_valid, error = validation_utils.validate_ocr_request(valid_request)
        assert is_valid is True
        assert error is None


def test_validate_ocr_request_with_invalid_schema():
    """Test validate_ocr_request with an invalid message schema."""
    invalid_request = {
        "document_id": "doc-123456",
        # Missing required fields
    }
    
    with patch('src.utils.validation_utils.validate_message_schema') as mock_validate_schema:
        mock_validate_schema.return_value = (False, "Schema validation error: 'document_type' is a required property")
        
        is_valid, error = validation_utils.validate_ocr_request(invalid_request)
        assert is_valid is False
        assert isinstance(error, ServiceError)
        assert error.category == ErrorCategory.VALIDATION
        assert "Schema validation error" in error.message


def test_validate_ocr_request_with_invalid_document_type():
    """Test validate_ocr_request with an invalid document type."""
    invalid_request = {
        "document_id": "doc-123456",
        "document_type": "INVALID_TYPE",  # Invalid type
        "storage_path": "s3://bucket/path/to/document.pdf",
        "metadata": {
            "filename": "document.pdf",
            "size": 1048576,
            "mime_type": "application/pdf"
        }
    }
    
    with patch('src.utils.validation_utils.validate_message_schema') as mock_validate_schema, \
         patch('src.utils.validation_utils.is_valid_document_type') as mock_is_valid_document_type:
        
        mock_validate_schema.return_value = (True, None)
        mock_is_valid_document_type.return_value = False
        
        is_valid, error = validation_utils.validate_ocr_request(invalid_request)
        assert is_valid is False
        assert isinstance(error, ServiceError)
        assert error.category == ErrorCategory.VALIDATION
        assert "document type" in error.message


def test_validate_ocr_request_with_invalid_metadata():
    """Test validate_ocr_request with invalid metadata."""
    invalid_request = {
        "document_id": "doc-123456",
        "document_type": "APPLICATION",
        "storage_path": "s3://bucket/path/to/document.pdf",
        "metadata": {
            "filename": "document.txt",  # Invalid extension
            "size": 1048576,
            "mime_type": "application/pdf"
        }
    }
    
    with patch('src.utils.validation_utils.validate_message_schema') as mock_validate_schema, \
         patch('src.utils.validation_utils.is_valid_document_type') as mock_is_valid_document_type, \
         patch('src.utils.validation_utils.validate_document_metadata') as mock_validate_metadata:
        
        mock_validate_schema.return_value = (True, None)
        mock_is_valid_document_type.return_value = True
        
        metadata_error = ServiceError(
            message="Unsupported file extension: .txt",
            category=ErrorCategory.VALIDATION,
            details={"metadata": invalid_request["metadata"]}
        )
        mock_validate_metadata.return_value = (False, metadata_error)
        
        is_valid, error = validation_utils.validate_ocr_request(invalid_request)
        assert is_valid is False
        assert error is metadata_error


# ===== Document Filtering Tests =====

def test_apply_document_filters_with_passing_document():
    """Test apply_document_filters with a document that passes all filters."""
    document_metadata = {
        "document_type": "APPLICATION",
        "mime_type": "application/pdf",
        "size": 1048576,  # 1MB
        "filename": "application_form.pdf",
        "classification": {"confidence": 0.95}
    }
    
    filters = {
        "document_types": ["APPLICATION", "TAX_RETURN"],
        "mime_types": ["application/pdf", "image/tiff"],
        "min_size": 1024,  # 1KB
        "max_size": 10485760,  # 10MB
        "filename_patterns": [r".*_form\.pdf$"],
        "min_confidence": 0.8
    }
    
    assert validation_utils.apply_document_filters(document_metadata, filters) is True


def test_apply_document_filters_with_failing_document():
    """Test apply_document_filters with documents that fail different filters."""
    # Base metadata that would pass all filters
    base_metadata = {
        "document_type": "APPLICATION",
        "mime_type": "application/pdf",
        "size": 1048576,  # 1MB
        "filename": "application_form.pdf",
        "classification": {"confidence": 0.95}
    }
    
    filters = {
        "document_types": ["APPLICATION", "TAX_RETURN"],
        "mime_types": ["application/pdf", "image/tiff"],
        "min_size": 1024,  # 1KB
        "max_size": 10485760,  # 10MB
        "filename_patterns": [r".*_form\.pdf$"],
        "min_confidence": 0.8
    }
    
    # Test document type filter
    wrong_type_metadata = base_metadata.copy()
    wrong_type_metadata["document_type"] = "INVALID_TYPE"
    assert validation_utils.apply_document_filters(wrong_type_metadata, filters) is False
    
    # Test MIME type filter
    wrong_mime_metadata = base_metadata.copy()
    wrong_mime_metadata["mime_type"] = "text/plain"
    assert validation_utils.apply_document_filters(wrong_mime_metadata, filters) is False
    
    # Test minimum size filter
    too_small_metadata = base_metadata.copy()
    too_small_metadata["size"] = 512  # 512 bytes
    assert validation_utils.apply_document_filters(too_small_metadata, filters) is False
    
    # Test maximum size filter
    too_large_metadata = base_metadata.copy()
    too_large_metadata["size"] = 20971520  # 20MB
    assert validation_utils.apply_document_filters(too_large_metadata, filters) is False
    
    # Test filename pattern filter
    wrong_filename_metadata = base_metadata.copy()
    wrong_filename_metadata["filename"] = "application.pdf"
    assert validation_utils.apply_document_filters(wrong_filename_metadata, filters) is False
    
    # Test confidence filter
    low_confidence_metadata = base_metadata.copy()
    low_confidence_metadata["classification"] = {"confidence": 0.7}
    assert validation_utils.apply_document_filters(low_confidence_metadata, filters) is False


def test_apply_document_filters_with_partial_filters():
    """Test apply_document_filters with only some filters specified."""
    document_metadata = {
        "document_type": "APPLICATION",
        "mime_type": "application/pdf",
        "size": 1048576,  # 1MB
        "filename": "application.pdf"
    }
    
    # Only specify document type filter
    type_only_filter = {
        "document_types": ["APPLICATION", "TAX_RETURN"]
    }
    assert validation_utils.apply_document_filters(document_metadata, type_only_filter) is True
    
    # Only specify size filters
    size_only_filter = {
        "min_size": 1024,  # 1KB
        "max_size": 10485760  # 10MB
    }
    assert validation_utils.apply_document_filters(document_metadata, size_only_filter) is True
    
    # Empty filters should pass all documents
    empty_filter = {}
    assert validation_utils.apply_document_filters(document_metadata, empty_filter) is True


def test_get_document_filters():
    """Test get_document_filters retrieves filters from configuration."""
    # Mock the app_config with document filters
    mock_config = MagicMock()
    mock_config.DOCUMENT_FILTERS = {
        "document_types": ["APPLICATION", "TAX_RETURN"],
        "mime_types": ["application/pdf", "image/tiff"],
        "min_size": 2048,  # 2KB
        "max_size": 5242880  # 5MB
    }
    
    with patch('src.utils.validation_utils.app_config', mock_config):
        filters = validation_utils.get_document_filters()
        assert filters == mock_config.DOCUMENT_FILTERS


def test_get_document_filters_with_defaults():
    """Test get_document_filters applies defaults for missing values."""
    # Mock the app_config with partial document filters
    mock_config = MagicMock()
    mock_config.DOCUMENT_FILTERS = {
        "document_types": ["APPLICATION", "TAX_RETURN"],
        # Missing min_size and max_size
    }
    
    with patch('src.utils.validation_utils.app_config', mock_config):
        filters = validation_utils.get_document_filters()
        assert filters["document_types"] == ["APPLICATION", "TAX_RETURN"]
        assert filters["min_size"] == validation_utils.DEFAULT_MIN_SIZE
        assert filters["max_size"] == validation_utils.DEFAULT_MAX_SIZE


def test_get_document_filters_with_no_config():
    """Test get_document_filters when no filters are configured."""
    # Mock the app_config with no document filters
    mock_config = MagicMock()
    mock_config.DOCUMENT_FILTERS = {}
    
    with patch('src.utils.validation_utils.app_config', mock_config):
        filters = validation_utils.get_document_filters()
        assert filters["min_size"] == validation_utils.DEFAULT_MIN_SIZE
        assert filters["max_size"] == validation_utils.DEFAULT_MAX_SIZE