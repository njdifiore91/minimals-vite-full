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
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module to test
from src.utils import validation_utils
from src.types.messages import MessagePayload
from src.types.errors import ServiceError, ErrorCategory


# ===== Document Type Validation Tests =====

def test_is_valid_document_type_with_valid_types():
    """Test is_valid_document_type with valid document types."""
    # Test all supported document types
    assert validation_utils.is_valid_document_type('pdf') is True
    assert validation_utils.is_valid_document_type('tiff') is True
    assert validation_utils.is_valid_document_type('tif') is True
    assert validation_utils.is_valid_document_type('png') is True
    assert validation_utils.is_valid_document_type('jpg') is True
    assert validation_utils.is_valid_document_type('jpeg') is True


def test_is_valid_document_type_with_invalid_types():
    """Test is_valid_document_type with invalid document types."""
    assert validation_utils.is_valid_document_type('doc') is False
    assert validation_utils.is_valid_document_type('docx') is False
    assert validation_utils.is_valid_document_type('xls') is False
    assert validation_utils.is_valid_document_type('xlsx') is False
    assert validation_utils.is_valid_document_type('txt') is False
    assert validation_utils.is_valid_document_type('') is False


def test_is_valid_document_type_case_insensitivity():
    """Test is_valid_document_type is case insensitive."""
    assert validation_utils.is_valid_document_type('PDF') is True
    assert validation_utils.is_valid_document_type('TIFF') is True
    assert validation_utils.is_valid_document_type('Png') is True
    assert validation_utils.is_valid_document_type('Jpeg') is True


# ===== MIME Type Validation Tests =====

def test_is_valid_mime_type_with_valid_types():
    """Test is_valid_mime_type with valid MIME types."""
    assert validation_utils.is_valid_mime_type('application/pdf') is True
    assert validation_utils.is_valid_mime_type('image/tiff') is True
    assert validation_utils.is_valid_mime_type('image/png') is True
    assert validation_utils.is_valid_mime_type('image/jpeg') is True


def test_is_valid_mime_type_with_invalid_types():
    """Test is_valid_mime_type with invalid MIME types."""
    assert validation_utils.is_valid_mime_type('application/msword') is False
    assert validation_utils.is_valid_mime_type('application/vnd.openxmlformats-officedocument.wordprocessingml.document') is False
    assert validation_utils.is_valid_mime_type('text/plain') is False
    assert validation_utils.is_valid_mime_type('application/octet-stream') is False
    assert validation_utils.is_valid_mime_type('') is False


# ===== Document Size Validation Tests =====

def test_is_valid_document_size_with_valid_sizes():
    """Test is_valid_document_size with valid document sizes."""
    # Minimum size (1KB)
    assert validation_utils.is_valid_document_size(1024) is True
    # Medium size (10MB)
    assert validation_utils.is_valid_document_size(10 * 1024 * 1024) is True
    # Maximum size (50MB)
    assert validation_utils.is_valid_document_size(50 * 1024 * 1024) is True


def test_is_valid_document_size_with_invalid_sizes():
    """Test is_valid_document_size with invalid document sizes."""
    # Too small (less than 1KB)
    assert validation_utils.is_valid_document_size(1023) is False
    # Too large (more than 50MB)
    assert validation_utils.is_valid_document_size(50 * 1024 * 1024 + 1) is False
    # Zero size
    assert validation_utils.is_valid_document_size(0) is False
    # Negative size (invalid input)
    assert validation_utils.is_valid_document_size(-1) is False


# ===== Image Dimensions Validation Tests =====

def test_is_valid_image_dimensions_with_valid_dimensions():
    """Test is_valid_image_dimensions with valid image dimensions."""
    # Minimum dimensions
    assert validation_utils.is_valid_image_dimensions(100, 100) is True
    # Medium dimensions
    assert validation_utils.is_valid_image_dimensions(1000, 1000) is True
    # Maximum dimensions
    assert validation_utils.is_valid_image_dimensions(8000, 8000) is True
    # Mixed dimensions within range
    assert validation_utils.is_valid_image_dimensions(800, 600) is True
    assert validation_utils.is_valid_image_dimensions(4000, 3000) is True


def test_is_valid_image_dimensions_with_invalid_dimensions():
    """Test is_valid_image_dimensions with invalid image dimensions."""
    # Too small width
    assert validation_utils.is_valid_image_dimensions(99, 100) is False
    # Too small height
    assert validation_utils.is_valid_image_dimensions(100, 99) is False
    # Too large width
    assert validation_utils.is_valid_image_dimensions(8001, 100) is False
    # Too large height
    assert validation_utils.is_valid_image_dimensions(100, 8001) is False
    # Both too small
    assert validation_utils.is_valid_image_dimensions(50, 50) is False
    # Both too large
    assert validation_utils.is_valid_image_dimensions(9000, 9000) is False
    # Zero dimensions
    assert validation_utils.is_valid_image_dimensions(0, 0) is False
    # Negative dimensions
    assert validation_utils.is_valid_image_dimensions(-100, -100) is False


# ===== Message Schema Validation Tests =====

def test_validate_message_schema_with_valid_message():
    """Test validate_message_schema with a valid message."""
    valid_message = {
        'document_id': 'doc-12345',
        'document_type': 'invoice',
        'storage_path': 'documents/invoices/invoice-12345.pdf',
        'classification': 'typed'
    }
    is_valid, error_message = validation_utils.validate_message_schema(valid_message)
    assert is_valid is True
    assert error_message is None


def test_validate_message_schema_with_missing_fields():
    """Test validate_message_schema with missing required fields."""
    # Missing document_id
    message = {
        'document_type': 'invoice',
        'storage_path': 'documents/invoices/invoice-12345.pdf',
        'classification': 'typed'
    }
    is_valid, error_message = validation_utils.validate_message_schema(message)
    assert is_valid is False
    assert 'Missing required field: document_id' in error_message

    # Missing document_type
    message = {
        'document_id': 'doc-12345',
        'storage_path': 'documents/invoices/invoice-12345.pdf',
        'classification': 'typed'
    }
    is_valid, error_message = validation_utils.validate_message_schema(message)
    assert is_valid is False
    assert 'Missing required field: document_type' in error_message

    # Missing storage_path
    message = {
        'document_id': 'doc-12345',
        'document_type': 'invoice',
        'classification': 'typed'
    }
    is_valid, error_message = validation_utils.validate_message_schema(message)
    assert is_valid is False
    assert 'Missing required field: storage_path' in error_message

    # Missing classification
    message = {
        'document_id': 'doc-12345',
        'document_type': 'invoice',
        'storage_path': 'documents/invoices/invoice-12345.pdf'
    }
    is_valid, error_message = validation_utils.validate_message_schema(message)
    assert is_valid is False
    assert 'Missing required field: classification' in error_message


def test_validate_message_schema_with_invalid_document_type():
    """Test validate_message_schema with an invalid document type."""
    message = {
        'document_id': 'doc-12345',
        'document_type': 'invoice',
        'storage_path': 'documents/invoices/invoice-12345.docx',  # Invalid extension
        'classification': 'typed'
    }
    is_valid, error_message = validation_utils.validate_message_schema(message)
    assert is_valid is False
    assert 'Unsupported document type' in error_message


def test_validate_message_schema_with_invalid_classification():
    """Test validate_message_schema with an invalid classification."""
    message = {
        'document_id': 'doc-12345',
        'document_type': 'invoice',
        'storage_path': 'documents/invoices/invoice-12345.pdf',
        'classification': 'invalid_classification'  # Invalid classification
    }
    is_valid, error_message = validation_utils.validate_message_schema(message)
    assert is_valid is False
    assert 'Invalid classification' in error_message


# ===== Document Format Validation Tests =====

def test_validate_document_format_with_valid_document(temp_dir):
    """Test validate_document_format with a valid document."""
    # Create a valid PDF file
    pdf_path = temp_dir / "valid_document.pdf"
    pdf_path.touch()
    
    # Mock the file size to be valid (10MB)
    with patch('os.path.getsize', return_value=10 * 1024 * 1024):
        # Mock mimetypes.guess_type to return a valid MIME type
        with patch('mimetypes.guess_type', return_value=('application/pdf', None)):
            is_valid, error_message = validation_utils.validate_document_format(str(pdf_path))
            assert is_valid is True
            assert error_message is None


def test_validate_document_format_with_nonexistent_file():
    """Test validate_document_format with a nonexistent file."""
    is_valid, error_message = validation_utils.validate_document_format(
        '/path/to/nonexistent/file.pdf'
    )
    assert is_valid is False
    assert 'File does not exist' in error_message


def test_validate_document_format_with_invalid_extension(temp_dir):
    """Test validate_document_format with an invalid file extension."""
    # Create a file with an invalid extension
    doc_path = temp_dir / "invalid_document.doc"
    doc_path.touch()
    
    is_valid, error_message = validation_utils.validate_document_format(str(doc_path))
    assert is_valid is False
    assert 'Unsupported document type' in error_message


def test_validate_document_format_with_invalid_size(temp_dir):
    """Test validate_document_format with an invalid file size."""
    # Create a valid PDF file
    pdf_path = temp_dir / "oversized_document.pdf"
    pdf_path.touch()
    
    # Mock the file size to be too large (100MB)
    with patch('os.path.getsize', return_value=100 * 1024 * 1024):
        is_valid, error_message = validation_utils.validate_document_format(str(pdf_path))
        assert is_valid is False
        assert 'Invalid document size' in error_message


def test_validate_document_format_with_invalid_mime_type(temp_dir):
    """Test validate_document_format with an invalid MIME type."""
    # Create a file with a valid extension but invalid MIME type
    pdf_path = temp_dir / "invalid_mime.pdf"
    pdf_path.touch()
    
    # Mock the file size to be valid
    with patch('os.path.getsize', return_value=10 * 1024 * 1024):
        # Mock mimetypes.guess_type to return an invalid MIME type
        with patch('mimetypes.guess_type', return_value=('application/octet-stream', None)):
            is_valid, error_message = validation_utils.validate_document_format(str(pdf_path))
            assert is_valid is False
            assert 'Invalid or unsupported MIME type' in error_message


# ===== Document Content Validation Tests =====

def test_validate_document_content_with_valid_pdf(temp_dir):
    """Test validate_document_content with a valid PDF document."""
    # Create a valid PDF file
    pdf_path = temp_dir / "valid_document.pdf"
    pdf_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PyPDF2.PdfReader
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.is_encrypted = False
        mock_pdf_reader.pages = [MagicMock(), MagicMock()]  # Mock 2 pages
        
        with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
            is_valid, error_message = validation_utils.validate_document_content(
                str(pdf_path), 'pdf'
            )
            assert is_valid is True
            assert error_message is None


def test_validate_document_content_with_encrypted_pdf(temp_dir):
    """Test validate_document_content with an encrypted PDF document."""
    # Create a PDF file
    pdf_path = temp_dir / "encrypted_document.pdf"
    pdf_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PyPDF2.PdfReader with encrypted PDF
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.is_encrypted = True
        
        with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
            is_valid, error_message = validation_utils.validate_document_content(
                str(pdf_path), 'pdf'
            )
            assert is_valid is False
            assert 'PDF is password protected' in error_message


def test_validate_document_content_with_empty_pdf(temp_dir):
    """Test validate_document_content with an empty PDF document."""
    # Create a PDF file
    pdf_path = temp_dir / "empty_document.pdf"
    pdf_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PyPDF2.PdfReader with empty PDF
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.is_encrypted = False
        mock_pdf_reader.pages = []  # Empty pages list
        
        with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
            is_valid, error_message = validation_utils.validate_document_content(
                str(pdf_path), 'pdf'
            )
            assert is_valid is False
            assert 'PDF has no pages' in error_message


def test_validate_document_content_with_corrupted_pdf(temp_dir):
    """Test validate_document_content with a corrupted PDF document."""
    # Create a PDF file
    pdf_path = temp_dir / "corrupted_document.pdf"
    pdf_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PyPDF2.PdfReader to raise PdfReadError
        with patch('PyPDF2.PdfReader', side_effect=Exception('PDF is corrupted')):
            is_valid, error_message = validation_utils.validate_document_content(
                str(pdf_path), 'pdf'
            )
            assert is_valid is False
            assert 'PDF is corrupted or invalid' in error_message


def test_validate_document_content_with_valid_image(temp_dir):
    """Test validate_document_content with a valid image document."""
    # Create a valid image file
    img_path = temp_dir / "valid_image.png"
    img_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PIL.Image.open
        mock_image = MagicMock()
        mock_image.size = (1000, 800)  # Valid dimensions
        
        with patch('PIL.Image.open', return_value=mock_image):
            is_valid, error_message = validation_utils.validate_document_content(
                str(img_path), 'png'
            )
            assert is_valid is True
            assert error_message is None


def test_validate_document_content_with_invalid_image_dimensions(temp_dir):
    """Test validate_document_content with invalid image dimensions."""
    # Create an image file
    img_path = temp_dir / "small_image.png"
    img_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PIL.Image.open with small image
        mock_image = MagicMock()
        mock_image.size = (50, 50)  # Too small dimensions
        
        with patch('PIL.Image.open', return_value=mock_image):
            is_valid, error_message = validation_utils.validate_document_content(
                str(img_path), 'png'
            )
            assert is_valid is False
            assert 'Invalid image dimensions' in error_message


def test_validate_document_content_with_corrupted_image(temp_dir):
    """Test validate_document_content with a corrupted image document."""
    # Create an image file
    img_path = temp_dir / "corrupted_image.png"
    img_path.touch()
    
    # Mock validate_document_format to return valid
    with patch('src.utils.validation_utils.validate_document_format', 
               return_value=(True, None)):
        # Mock PIL.Image.open to raise an exception
        with patch('PIL.Image.open', side_effect=Exception('Image is corrupted')):
            is_valid, error_message = validation_utils.validate_document_content(
                str(img_path), 'png'
            )
            assert is_valid is False
            assert 'Image is corrupted or invalid' in error_message


# ===== Extraction Request Validation Tests =====

def test_validate_extraction_request_with_valid_request():
    """Test validate_extraction_request with a valid request."""
    valid_request = {
        'message_id': 'msg-12345',
        'document_id': 'doc-12345',
        'document_type': 'invoice',
        'storage_path': 'documents/invoices/invoice-12345.pdf',
        'classification': 'typed'
    }
    
    # Mock validate_message_schema to return valid
    with patch('src.utils.validation_utils.validate_message_schema', 
               return_value=(True, None)):
        is_valid, error = validation_utils.validate_extraction_request(valid_request)
        assert is_valid is True
        assert error is None


def test_validate_extraction_request_with_invalid_request():
    """Test validate_extraction_request with an invalid request."""
    invalid_request = {
        'message_id': 'msg-12345',
        'document_id': 'doc-12345',
        # Missing required fields
    }
    
    # Mock validate_message_schema to return invalid
    with patch('src.utils.validation_utils.validate_message_schema', 
               return_value=(False, 'Missing required fields')):
        is_valid, error = validation_utils.validate_extraction_request(invalid_request)
        assert is_valid is False
        assert isinstance(error, ServiceError)
        assert error.category == ErrorCategory.VALIDATION
        assert 'Missing required fields' in error.message


def test_validate_extraction_request_with_exception():
    """Test validate_extraction_request with an exception during validation."""
    request = {
        'message_id': 'msg-12345',
        'document_id': 'doc-12345',
    }
    
    # Mock validate_message_schema to raise an exception
    with patch('src.utils.validation_utils.validate_message_schema', 
               side_effect=Exception('Validation error')):
        is_valid, error = validation_utils.validate_extraction_request(request)
        assert is_valid is False
        assert isinstance(error, ServiceError)
        assert error.category == ErrorCategory.SYSTEM
        assert 'Failed to validate extraction request' in error.message


# ===== Document Validation Rules Tests =====

def test_get_document_validation_rules_for_pdf_typed():
    """Test get_document_validation_rules for PDF with typed classification."""
    rules = validation_utils.get_document_validation_rules('pdf', 'typed')
    
    # Check base rules
    assert rules['max_size_bytes'] == validation_utils.MAX_DOCUMENT_SIZE_BYTES
    assert rules['min_size_bytes'] == validation_utils.MIN_DOCUMENT_SIZE_BYTES
    
    # Check PDF-specific rules
    assert rules['max_pages'] == 200
    assert rules['allow_scanned'] is True
    assert rules['require_text_content'] is False
    
    # Check typed-specific rules
    assert rules['min_confidence'] == 0.75
    assert rules['ocr_model'] == 'typed_text_model'


def test_get_document_validation_rules_for_tiff_handwritten():
    """Test get_document_validation_rules for TIFF with handwritten classification."""
    rules = validation_utils.get_document_validation_rules('tiff', 'handwritten')
    
    # Check base rules
    assert rules['max_size_bytes'] == validation_utils.MAX_DOCUMENT_SIZE_BYTES
    assert rules['min_size_bytes'] == validation_utils.MIN_DOCUMENT_SIZE_BYTES
    
    # Check TIFF-specific rules
    assert rules['max_pages'] == 50
    assert rules['min_dpi'] == 200
    assert rules['require_text_content'] is False
    
    # Check handwritten-specific rules
    assert rules['min_confidence'] == 0.60
    assert rules['ocr_model'] == 'handwritten_text_model'


def test_get_document_validation_rules_for_png_mixed():
    """Test get_document_validation_rules for PNG with mixed classification."""
    rules = validation_utils.get_document_validation_rules('png', 'mixed')
    
    # Check base rules
    assert rules['max_size_bytes'] == validation_utils.MAX_DOCUMENT_SIZE_BYTES
    assert rules['min_size_bytes'] == validation_utils.MIN_DOCUMENT_SIZE_BYTES
    
    # Check PNG-specific rules
    assert rules['max_pages'] == 1
    assert rules['min_dpi'] == 150
    assert rules['require_text_content'] is False
    
    # Check mixed-specific rules
    assert rules['min_confidence'] == 0.65
    assert rules['ocr_model'] == 'hybrid_text_model'


def test_get_document_validation_rules_for_unknown_type_and_classification():
    """Test get_document_validation_rules with unknown type and classification."""
    # Unknown document type but known classification
    rules = validation_utils.get_document_validation_rules('unknown', 'typed')
    assert rules['min_confidence'] == 0.75
    assert rules['ocr_model'] == 'typed_text_model'
    assert rules['max_pages'] == 100  # Default from base rules
    
    # Known document type but unknown classification
    rules = validation_utils.get_document_validation_rules('pdf', 'unknown')
    assert rules['min_confidence'] == 0.70  # Default for unknown
    assert rules['ocr_model'] == 'hybrid_text_model'  # Default for unknown
    assert rules['max_pages'] == 200  # PDF-specific
    
    # Both unknown
    rules = validation_utils.get_document_validation_rules('unknown', 'unknown')
    assert rules['min_confidence'] == 0.70  # Default for unknown
    assert rules['ocr_model'] == 'hybrid_text_model'  # Default for unknown
    assert rules['max_pages'] == 100  # Default from base rules


# ===== Apply Validation Rules Tests =====

def test_apply_validation_rules_with_valid_pdf(temp_dir):
    """Test apply_validation_rules with a valid PDF document."""
    # Create a valid PDF file
    pdf_path = temp_dir / "valid_document.pdf"
    pdf_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024,
        'max_pages': 200,
        'require_text_content': False,
        'allow_scanned': True
    }
    
    # Mock file size
    with patch('os.path.getsize', return_value=10 * 1024 * 1024):
        # Mock PyPDF2.PdfReader
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.is_encrypted = False
        mock_pdf_reader.pages = [MagicMock(), MagicMock()]  # Mock 2 pages
        
        with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
            is_valid, error_message = validation_utils.apply_validation_rules(
                str(pdf_path), rules
            )
            assert is_valid is True
            assert error_message is None


def test_apply_validation_rules_with_nonexistent_file():
    """Test apply_validation_rules with a nonexistent file."""
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024
    }
    
    is_valid, error_message = validation_utils.apply_validation_rules(
        '/path/to/nonexistent/file.pdf', rules
    )
    assert is_valid is False
    assert 'File does not exist' in error_message


def test_apply_validation_rules_with_too_small_file(temp_dir):
    """Test apply_validation_rules with a file that's too small."""
    # Create a PDF file
    pdf_path = temp_dir / "small_document.pdf"
    pdf_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024
    }
    
    # Mock file size to be too small
    with patch('os.path.getsize', return_value=500):
        is_valid, error_message = validation_utils.apply_validation_rules(
            str(pdf_path), rules
        )
        assert is_valid is False
        assert 'Document too small' in error_message


def test_apply_validation_rules_with_too_large_file(temp_dir):
    """Test apply_validation_rules with a file that's too large."""
    # Create a PDF file
    pdf_path = temp_dir / "large_document.pdf"
    pdf_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024
    }
    
    # Mock file size to be too large
    with patch('os.path.getsize', return_value=100 * 1024 * 1024):
        is_valid, error_message = validation_utils.apply_validation_rules(
            str(pdf_path), rules
        )
        assert is_valid is False
        assert 'Document too large' in error_message


def test_apply_validation_rules_with_encrypted_pdf(temp_dir):
    """Test apply_validation_rules with an encrypted PDF document."""
    # Create a PDF file
    pdf_path = temp_dir / "encrypted_document.pdf"
    pdf_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024,
        'max_pages': 200
    }
    
    # Mock file size
    with patch('os.path.getsize', return_value=10 * 1024 * 1024):
        # Mock PyPDF2.PdfReader with encrypted PDF
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.is_encrypted = True
        
        with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
            is_valid, error_message = validation_utils.apply_validation_rules(
                str(pdf_path), rules
            )
            assert is_valid is False
            assert 'PDF is password protected' in error_message


def test_apply_validation_rules_with_too_many_pages(temp_dir):
    """Test apply_validation_rules with a PDF that has too many pages."""
    # Create a PDF file
    pdf_path = temp_dir / "many_pages_document.pdf"
    pdf_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024,
        'max_pages': 10
    }
    
    # Mock file size
    with patch('os.path.getsize', return_value=10 * 1024 * 1024):
        # Mock PyPDF2.PdfReader with many pages
        mock_pdf_reader = MagicMock()
        mock_pdf_reader.is_encrypted = False
        mock_pdf_reader.pages = [MagicMock() for _ in range(20)]  # 20 pages
        
        with patch('PyPDF2.PdfReader', return_value=mock_pdf_reader):
            is_valid, error_message = validation_utils.apply_validation_rules(
                str(pdf_path), rules
            )
            assert is_valid is False
            assert 'PDF has too many pages' in error_message


def test_apply_validation_rules_with_valid_image(temp_dir):
    """Test apply_validation_rules with a valid image document."""
    # Create a valid image file
    img_path = temp_dir / "valid_image.png"
    img_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024,
        'min_dpi': 150
    }
    
    # Mock file size
    with patch('os.path.getsize', return_value=1 * 1024 * 1024):
        # Mock PIL.Image.open
        mock_image = MagicMock()
        mock_image.size = (1000, 800)  # Valid dimensions
        mock_image.info = {'dpi': (300, 300)}  # Valid DPI
        
        with patch('PIL.Image.open', return_value=mock_image):
            is_valid, error_message = validation_utils.apply_validation_rules(
                str(img_path), rules
            )
            assert is_valid is True
            assert error_message is None


def test_apply_validation_rules_with_low_dpi_image(temp_dir):
    """Test apply_validation_rules with an image that has low DPI."""
    # Create an image file
    img_path = temp_dir / "low_dpi_image.png"
    img_path.touch()
    
    # Define validation rules
    rules = {
        'min_size_bytes': 1024,
        'max_size_bytes': 50 * 1024 * 1024,
        'min_dpi': 300
    }
    
    # Mock file size
    with patch('os.path.getsize', return_value=1 * 1024 * 1024):
        # Mock PIL.Image.open with low DPI
        mock_image = MagicMock()
        mock_image.size = (1000, 800)  # Valid dimensions
        mock_image.info = {'dpi': (150, 150)}  # Low DPI
        
        with patch('PIL.Image.open', return_value=mock_image):
            is_valid, error_message = validation_utils.apply_validation_rules(
                str(img_path), rules
            )
            assert is_valid is False
            assert 'Image DPI too low' in error_message


# ===== Comprehensive Document Validation Tests =====

def test_validate_document_for_ocr_with_valid_document(temp_dir):
    """Test validate_document_for_ocr with a valid document."""
    # Create a valid PDF file
    pdf_path = temp_dir / "valid_document.pdf"
    pdf_path.touch()
    
    # Mock validate_document_content to return valid
    with patch('ocr_service.src.utils.validation_utils.validate_document_content', 
               return_value=(True, None)):
        # Mock get_document_validation_rules to return rules
        mock_rules = {
            'min_size_bytes': 1024,
            'max_size_bytes': 50 * 1024 * 1024,
            'max_pages': 200,
            'require_text_content': False,
            'allow_scanned': True
        }
        with patch('ocr_service.src.utils.validation_utils.get_document_validation_rules', 
                   return_value=mock_rules):
            # Mock apply_validation_rules to return valid
            with patch('src.utils.validation_utils.apply_validation_rules', 
                       return_value=(True, None)):
                is_valid, error_message = validation_utils.validate_document_for_ocr(
                    str(pdf_path), 'pdf', 'typed'
                )
                assert is_valid is True
                assert error_message is None


def test_validate_document_for_ocr_with_invalid_content(temp_dir):
    """Test validate_document_for_ocr with invalid document content."""
    # Create a PDF file
    pdf_path = temp_dir / "invalid_content.pdf"
    pdf_path.touch()
    
    # Mock validate_document_content to return invalid
    with patch('src.utils.validation_utils.validate_document_content', 
               return_value=(False, 'Invalid document content')):
        is_valid, error_message = validation_utils.validate_document_for_ocr(
            str(pdf_path), 'pdf', 'typed'
        )
        assert is_valid is False
        assert 'Invalid document content' in error_message


def test_validate_document_for_ocr_with_invalid_rules(temp_dir):
    """Test validate_document_for_ocr with document that fails validation rules."""
    # Create a PDF file
    pdf_path = temp_dir / "fails_rules.pdf"
    pdf_path.touch()
    
    # Mock validate_document_content to return valid
    with patch('src.utils.validation_utils.validate_document_content', 
               return_value=(True, None)):
        # Mock get_document_validation_rules to return rules
        mock_rules = {
            'min_size_bytes': 1024,
            'max_size_bytes': 50 * 1024 * 1024,
            'max_pages': 10
        }
        with patch('src.utils.validation_utils.get_document_validation_rules', 
                   return_value=mock_rules):
            # Mock apply_validation_rules to return invalid
            with patch('src.utils.validation_utils.apply_validation_rules', 
                       return_value=(False, 'Document fails validation rules')):
                is_valid, error_message = validation_utils.validate_document_for_ocr(
                    str(pdf_path), 'pdf', 'typed'
                )
                assert is_valid is False
                assert 'Document fails validation rules' in error_message