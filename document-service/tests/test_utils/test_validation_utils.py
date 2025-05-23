#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for validation utilities in the Document Service.

This module contains tests for the validation_utils.py module, which provides
utility functions for validating document types, formats, sizes, and other input data.
These tests ensure that document validation works correctly and prevents processing
of invalid or malicious content.
"""

import os
import json
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module to test
from document_service.utils.validation_utils import (
    validate_file_size,
    validate_buffer_size,
    validate_document_type,
    validate_document_extension,
    validate_document_content,
    validate_buffer_content,
    validate_document,
    validate_json_schema,
    validate_document_message,
    validate_classification_result_message,
    validate_ocr_request_message,
    validate_message_size,
    validate_metadata,
    is_potentially_malicious,
    validate_document_for_processing,
    validate_email_source,
    validate_upload_source,
    validate_api_source,
    validate_source_information,
    validate_document_hash,
    validation_decorator,
    DOCUMENT_MESSAGE_SCHEMA,
    CLASSIFICATION_RESULT_SCHEMA,
    OCR_REQUEST_SCHEMA,
    MAX_FILE_SIZE,
    MIN_FILE_SIZE,
    MAX_MESSAGE_SIZE,
    MALICIOUS_EXTENSIONS,
    MALICIOUS_MIME_TYPES
)

# Import types
from document_service.types.documents import DocumentType
from document_service.types.errors import ValidationError, Result


# ===== Test Fixtures =====

@pytest.fixture
def valid_document_file():
    """Create a temporary valid document file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        # Create a file with valid size
        temp_file.write(b'%PDF-1.4\n' + b'x' * 2000)
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def small_document_file():
    """Create a temporary document file that is too small for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        # Create a file smaller than MIN_FILE_SIZE
        temp_file.write(b'%PDF-1.4\n' + b'x' * 500)
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def large_document_file():
    """Create a temporary document file that is too large for testing."""
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        # Create a file larger than MAX_FILE_SIZE (mock it to avoid creating huge files)
        temp_file.write(b'%PDF-1.4\n' + b'x' * 10000)
        temp_file_path = temp_file.name
        
        # Mock the file size check to simulate a large file
        with patch('document_service.utils.file_utils.get_file_size', return_value=MAX_FILE_SIZE + 1000):
            yield temp_file_path
    
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def malicious_document_file():
    """Create a temporary malicious document file for testing."""
    with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as temp_file:
        # Create a file with malicious extension
        temp_file.write(b'MZ' + b'x' * 2000)  # MZ header for executable
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def unsupported_document_file():
    """Create a temporary document file with unsupported extension for testing."""
    with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as temp_file:
        # Create a file with unsupported extension
        temp_file.write(b'Test file with unsupported extension')
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def valid_document_buffer():
    """Create a valid document buffer for testing."""
    return b'%PDF-1.4\n' + b'x' * 2000


@pytest.fixture
def small_document_buffer():
    """Create a document buffer that is too small for testing."""
    return b'%PDF-1.4\n' + b'x' * 500


@pytest.fixture
def large_document_buffer():
    """Create a document buffer that is too large for testing."""
    # Just create a small buffer, we'll mock the size check
    return b'%PDF-1.4\n' + b'x' * 10000


@pytest.fixture
def valid_document_metadata():
    """Create valid document metadata for testing."""
    return {
        'filename': 'test_document.pdf',
        'size': 2048,
        'mime_type': 'application/pdf',
        'classification_confidence': 0.95,
        'ocr_confidence': 0.85,
        'page_count': 5
    }


@pytest.fixture
def invalid_document_metadata():
    """Create invalid document metadata for testing."""
    return {
        'filename': 'test_document.pdf',
        'size': -1,  # Invalid size
        'mime_type': 'application/pdf'
    }


@pytest.fixture
def valid_document_message():
    """Create a valid document message for testing."""
    return {
        'document_id': '12345678-1234-5678-1234-567812345678',
        'metadata': {
            'filename': 'test_document.pdf',
            'size': 2048,
            'mime_type': 'application/pdf',
            'created_at': '2023-05-01T12:34:56Z',
            'updated_at': '2023-05-01T12:34:56Z',
            'classification_confidence': 0.95,
            'ocr_confidence': 0.85,
            'page_count': 5,
            'tags': ['test', 'document']
        },
        'source': {
            'source_type': 'email',
            'email_id': 'email-12345',
            'email_sender': 'test@example.com',
            'email_subject': 'Test Document',
            'email_received_at': '2023-05-01T12:30:00Z',
            'received_at': '2023-05-01T12:34:56Z'
        },
        'content_reference': 's3://test-bucket/documents/test_document.pdf',
        'document_type': 'application',
        'status': 'received'
    }


@pytest.fixture
def invalid_document_message():
    """Create an invalid document message for testing."""
    return {
        'document_id': '12345678-1234-5678-1234-567812345678',
        # Missing required 'metadata' field
        'source': {
            'source_type': 'email',
            'email_id': 'email-12345',
            'email_sender': 'test@example.com',
            'received_at': '2023-05-01T12:34:56Z'
        },
        'status': 'received'
    }


@pytest.fixture
def valid_classification_result_message():
    """Create a valid classification result message for testing."""
    return {
        'document_id': '12345678-1234-5678-1234-567812345678',
        'document_type': 'application',
        'confidence': 0.95,
        'confidence_scores': {
            'application': 0.95,
            'tax_return': 0.03,
            'bank_statement': 0.02
        },
        'features_used': ['text_content', 'layout', 'keywords'],
        'model_version': '1.0.0',
        'classified_at': '2023-05-01T12:34:56Z',
        'requires_review': False
    }


@pytest.fixture
def invalid_classification_result_message():
    """Create an invalid classification result message for testing."""
    return {
        'document_id': '12345678-1234-5678-1234-567812345678',
        'document_type': 'application',
        'confidence': 1.5,  # Invalid confidence (> 1.0)
        'confidence_scores': {
            'application': 0.95,
            'tax_return': 0.03,
            'bank_statement': 0.02
        },
        'model_version': '1.0.0',
        'classified_at': '2023-05-01T12:34:56Z'
        # Missing required 'features_used' field
    }


@pytest.fixture
def valid_ocr_request_message():
    """Create a valid OCR request message for testing."""
    return {
        'document_id': '12345678-1234-5678-1234-567812345678',
        'document_type': 'application',
        'storage_path': 's3://test-bucket/documents/test_document.pdf',
        'metadata': {
            'filename': 'test_document.pdf',
            'size': 2048,
            'mime_type': 'application/pdf',
            'page_count': 5,
            'classification_confidence': 0.95
        },
        'processing_options': {
            'extract_tables': True,
            'extract_signatures': True,
            'extract_handwriting': False,
            'confidence_threshold': 0.7
        }
    }


@pytest.fixture
def invalid_ocr_request_message():
    """Create an invalid OCR request message for testing."""
    return {
        'document_id': '12345678-1234-5678-1234-567812345678',
        'document_type': 'invalid_type',  # Invalid document type
        'storage_path': 's3://test-bucket/documents/test_document.pdf'
        # Missing required 'metadata' field
    }


@pytest.fixture
def valid_email_source():
    """Create a valid email source for testing."""
    return {
        'source_type': 'email',
        'email_id': 'email-12345',
        'email_sender': 'test@example.com',
        'email_subject': 'Test Document',
        'email_received_at': '2023-05-01T12:30:00Z',
        'received_at': '2023-05-01T12:34:56Z'
    }


@pytest.fixture
def invalid_email_source():
    """Create an invalid email source for testing."""
    return {
        'source_type': 'email',
        'email_id': 'email-12345',
        'email_sender': 'invalid-email',  # Invalid email format
        'email_received_at': '2023-05-01T12:30:00Z',
        'received_at': '2023-05-01T12:34:56Z'
    }


@pytest.fixture
def valid_upload_source():
    """Create a valid upload source for testing."""
    return {
        'source_type': 'upload',
        'upload_user_id': 'user-12345',
        'upload_ip': '192.168.1.1',
        'received_at': '2023-05-01T12:34:56Z'
    }


@pytest.fixture
def invalid_upload_source():
    """Create an invalid upload source for testing."""
    return {
        'source_type': 'upload',
        'upload_ip': '192.168.1.1',  # Missing required 'upload_user_id' field
        'received_at': '2023-05-01T12:34:56Z'
    }


@pytest.fixture
def valid_api_source():
    """Create a valid API source for testing."""
    return {
        'source_type': 'api',
        'api_client_id': 'client-12345',
        'received_at': '2023-05-01T12:34:56Z'
    }


@pytest.fixture
def invalid_api_source():
    """Create an invalid API source for testing."""
    return {
        'source_type': 'api',
        # Missing required 'api_client_id' field
        'received_at': '2023-05-01T12:34:56Z'
    }


# ===== Test Functions =====

# Tests for file size validation

def test_validate_file_size_valid(valid_document_file):
    """Test that validate_file_size accepts files with valid size."""
    # Should not raise an exception
    assert validate_file_size(valid_document_file) is True


def test_validate_file_size_too_small(small_document_file):
    """Test that validate_file_size rejects files that are too small."""
    with pytest.raises(ValidationError) as excinfo:
        validate_file_size(small_document_file)
    assert "File size too small" in str(excinfo.value)


def test_validate_file_size_too_large(large_document_file):
    """Test that validate_file_size rejects files that are too large."""
    with pytest.raises(ValidationError) as excinfo:
        validate_file_size(large_document_file)
    assert "File size too large" in str(excinfo.value)


def test_validate_file_size_custom_limits(valid_document_file):
    """Test that validate_file_size respects custom size limits."""
    # Set custom limits that make the valid file too small
    with pytest.raises(ValidationError) as excinfo:
        validate_file_size(valid_document_file, min_size=5000)
    assert "File size too small" in str(excinfo.value)
    
    # Set custom limits that make the valid file too large
    with pytest.raises(ValidationError) as excinfo:
        validate_file_size(valid_document_file, max_size=1000)
    assert "File size too large" in str(excinfo.value)


# Tests for buffer size validation

def test_validate_buffer_size_valid(valid_document_buffer):
    """Test that validate_buffer_size accepts buffers with valid size."""
    # Should not raise an exception
    assert validate_buffer_size(valid_document_buffer) is True


def test_validate_buffer_size_too_small(small_document_buffer):
    """Test that validate_buffer_size rejects buffers that are too small."""
    with pytest.raises(ValidationError) as excinfo:
        validate_buffer_size(small_document_buffer)
    assert "Buffer size too small" in str(excinfo.value)


def test_validate_buffer_size_too_large():
    """Test that validate_buffer_size rejects buffers that are too large."""
    # Create a buffer larger than MAX_FILE_SIZE
    large_buffer = b'x' * (MAX_FILE_SIZE + 1000)
    
    with pytest.raises(ValidationError) as excinfo:
        validate_buffer_size(large_buffer)
    assert "Buffer size too large" in str(excinfo.value)


# Tests for document type validation

def test_validate_document_type_valid(valid_document_file):
    """Test that validate_document_type accepts files with valid types."""
    # Mock the MIME type detection
    with patch('document_service.utils.file_utils.get_mime_type', return_value='application/pdf'):
        with patch('document_service.utils.file_utils.is_supported_mime_type', return_value=True):
            # Should not raise an exception
            doc_type = validate_document_type(valid_document_file)
            assert isinstance(doc_type, DocumentType)


def test_validate_document_type_unsupported(unsupported_document_file):
    """Test that validate_document_type rejects files with unsupported types."""
    # Mock the MIME type detection
    with patch('document_service.utils.file_utils.get_mime_type', return_value='application/octet-stream'):
        with patch('document_service.utils.file_utils.is_supported_mime_type', return_value=False):
            with pytest.raises(ValidationError) as excinfo:
                validate_document_type(unsupported_document_file)
            assert "Unsupported MIME type" in str(excinfo.value)


def test_validate_document_type_with_allowed_types(valid_document_file):
    """Test that validate_document_type respects allowed types."""
    # Mock the MIME type detection and compatibility check
    with patch('document_service.utils.file_utils.get_mime_type', return_value='application/pdf'):
        with patch('document_service.utils.file_utils.is_supported_mime_type', return_value=True):
            # Mock the document type compatibility mapping
            with patch('document_service.utils.file_utils.DOCUMENT_TYPE_MIME_MAPPING', {
                'application': ['application/pdf'],
                'tax_return': ['application/vnd.ms-excel']
            }):
                # Should return the compatible document type
                doc_type = validate_document_type(valid_document_file, allowed_types=[DocumentType.APPLICATION])
                assert doc_type == DocumentType.APPLICATION


def test_validate_document_type_incompatible(valid_document_file):
    """Test that validate_document_type rejects files incompatible with allowed types."""
    # Mock the MIME type detection and compatibility check
    with patch('document_service.utils.file_utils.get_mime_type', return_value='application/pdf'):
        with patch('document_service.utils.file_utils.is_supported_mime_type', return_value=True):
            # Mock the document type compatibility mapping
            with patch('document_service.utils.file_utils.DOCUMENT_TYPE_MIME_MAPPING', {
                'application': ['application/vnd.ms-word'],
                'tax_return': ['application/vnd.ms-excel']
            }):
                with pytest.raises(ValidationError) as excinfo:
                    validate_document_type(valid_document_file, allowed_types=[DocumentType.APPLICATION, DocumentType.TAX_RETURN])
                assert "not compatible with allowed document types" in str(excinfo.value)


# Tests for document extension validation

def test_validate_document_extension_valid(valid_document_file):
    """Test that validate_document_extension accepts files with valid extensions."""
    # Mock the extension check
    with patch('document_service.utils.file_utils.is_supported_file_extension', return_value=True):
        # Should not raise an exception
        assert validate_document_extension(valid_document_file) is True


def test_validate_document_extension_unsupported(unsupported_document_file):
    """Test that validate_document_extension rejects files with unsupported extensions."""
    # Mock the extension check
    with patch('document_service.utils.file_utils.is_supported_file_extension', return_value=False):
        with pytest.raises(ValidationError) as excinfo:
            validate_document_extension(unsupported_document_file)
        assert "Unsupported file extension" in str(excinfo.value)


# Tests for document content validation

def test_validate_document_content_valid(valid_document_file):
    """Test that validate_document_content accepts files with valid content."""
    # Mock the MIME type detection
    with patch('magic.Magic.from_file', return_value='application/pdf'):
        # Should not raise an exception
        assert validate_document_content(valid_document_file) is True


def test_validate_document_content_malicious_extension(malicious_document_file):
    """Test that validate_document_content rejects files with malicious extensions."""
    with pytest.raises(ValidationError) as excinfo:
        validate_document_content(malicious_document_file)
    assert "Potentially malicious file extension" in str(excinfo.value)


def test_validate_document_content_malicious_mime_type(valid_document_file):
    """Test that validate_document_content rejects files with malicious MIME types."""
    # Mock the MIME type detection
    with patch('magic.Magic.from_file', return_value='application/x-msdownload'):
        with pytest.raises(ValidationError) as excinfo:
            validate_document_content(valid_document_file)
        assert "Potentially malicious MIME type" in str(excinfo.value)


# Tests for buffer content validation

def test_validate_buffer_content_valid(valid_document_buffer):
    """Test that validate_buffer_content accepts buffers with valid content."""
    # Mock the MIME type detection
    with patch('magic.Magic.from_buffer', return_value='application/pdf'):
        # Should not raise an exception
        assert validate_buffer_content(valid_document_buffer) is True


def test_validate_buffer_content_malicious_mime_type(valid_document_buffer):
    """Test that validate_buffer_content rejects buffers with malicious MIME types."""
    # Mock the MIME type detection
    with patch('magic.Magic.from_buffer', return_value='application/x-msdownload'):
        with pytest.raises(ValidationError) as excinfo:
            validate_buffer_content(valid_document_buffer)
        assert "Potentially malicious MIME type" in str(excinfo.value)


# Tests for comprehensive document validation

def test_validate_document_success(valid_document_file):
    """Test that validate_document succeeds for valid documents."""
    # Mock all the validation functions
    with patch('document_service.utils.validation_utils.validate_file_size', return_value=True):
        with patch('document_service.utils.validation_utils.validate_document_extension', return_value=True):
            with patch('document_service.utils.validation_utils.validate_document_content', return_value=True):
                with patch('document_service.utils.validation_utils.validate_document_type', return_value=DocumentType.APPLICATION):
                    result = validate_document(valid_document_file)
                    assert result.is_success
                    assert result.value == DocumentType.APPLICATION


def test_validate_document_failure(valid_document_file):
    """Test that validate_document fails when a validation check fails."""
    # Mock the validation functions to make one fail
    with patch('document_service.utils.validation_utils.validate_file_size', side_effect=ValidationError("Test error")):
        result = validate_document(valid_document_file)
        assert result.is_failure
        assert isinstance(result.error, ValidationError)


# Tests for JSON schema validation

def test_validate_json_schema_valid():
    """Test that validate_json_schema accepts valid JSON data."""
    schema = {
        "type": "object",
        "required": ["name", "age"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        }
    }
    
    data = {"name": "John Doe", "age": 30}
    
    # Should not raise an exception
    assert validate_json_schema(data, schema) is True
    
    # Test with JSON string
    json_str = json.dumps(data)
    assert validate_json_schema(json_str, schema) is True


def test_validate_json_schema_invalid():
    """Test that validate_json_schema rejects invalid JSON data."""
    schema = {
        "type": "object",
        "required": ["name", "age"],
        "properties": {
            "name": {"type": "string"},
            "age": {"type": "integer", "minimum": 0}
        }
    }
    
    # Missing required field
    data1 = {"name": "John Doe"}
    with pytest.raises(ValidationError) as excinfo:
        validate_json_schema(data1, schema)
    assert "JSON schema validation failed" in str(excinfo.value)
    
    # Invalid field type
    data2 = {"name": "John Doe", "age": "thirty"}
    with pytest.raises(ValidationError) as excinfo:
        validate_json_schema(data2, schema)
    assert "JSON schema validation failed" in str(excinfo.value)
    
    # Invalid JSON string
    json_str = "{"name": "John Doe", "age": 30"
    with pytest.raises(ValidationError) as excinfo:
        validate_json_schema(json_str, schema)
    assert "Invalid JSON format" in str(excinfo.value)


# Tests for document message validation

def test_validate_document_message_valid(valid_document_message):
    """Test that validate_document_message accepts valid document messages."""
    # Should not raise an exception
    assert validate_document_message(valid_document_message) is True


def test_validate_document_message_invalid(invalid_document_message):
    """Test that validate_document_message rejects invalid document messages."""
    with pytest.raises(ValidationError) as excinfo:
        validate_document_message(invalid_document_message)
    assert "JSON schema validation failed" in str(excinfo.value)


# Tests for classification result message validation

def test_validate_classification_result_message_valid(valid_classification_result_message):
    """Test that validate_classification_result_message accepts valid classification result messages."""
    # Should not raise an exception
    assert validate_classification_result_message(valid_classification_result_message) is True


def test_validate_classification_result_message_invalid(invalid_classification_result_message):
    """Test that validate_classification_result_message rejects invalid classification result messages."""
    with pytest.raises(ValidationError) as excinfo:
        validate_classification_result_message(invalid_classification_result_message)
    assert "JSON schema validation failed" in str(excinfo.value)


# Tests for OCR request message validation

def test_validate_ocr_request_message_valid(valid_ocr_request_message):
    """Test that validate_ocr_request_message accepts valid OCR request messages."""
    # Should not raise an exception
    assert validate_ocr_request_message(valid_ocr_request_message) is True


def test_validate_ocr_request_message_invalid(invalid_ocr_request_message):
    """Test that validate_ocr_request_message rejects invalid OCR request messages."""
    with pytest.raises(ValidationError) as excinfo:
        validate_ocr_request_message(invalid_ocr_request_message)
    assert "JSON schema validation failed" in str(excinfo.value)


# Tests for message size validation

def test_validate_message_size_valid():
    """Test that validate_message_size accepts messages with valid size."""
    # Create a message smaller than MAX_MESSAGE_SIZE
    message = "x" * 1000
    
    # Should not raise an exception
    assert validate_message_size(message) is True


def test_validate_message_size_too_large():
    """Test that validate_message_size rejects messages that are too large."""
    # Create a message larger than MAX_MESSAGE_SIZE
    message = "x" * (MAX_MESSAGE_SIZE + 1000)
    
    with pytest.raises(ValidationError) as excinfo:
        validate_message_size(message)
    assert "Message size too large" in str(excinfo.value)


# Tests for metadata validation

def test_validate_metadata_valid(valid_document_metadata):
    """Test that validate_metadata accepts valid metadata."""
    # Mock the MIME type check
    with patch('document_service.utils.file_utils.is_supported_mime_type', return_value=True):
        # Should not raise an exception
        assert validate_metadata(valid_document_metadata) is True


def test_validate_metadata_missing_required_field():
    """Test that validate_metadata rejects metadata with missing required fields."""
    # Missing required 'mime_type' field
    metadata = {
        'filename': 'test_document.pdf',
        'size': 2048
    }
    
    with pytest.raises(ValidationError) as excinfo:
        validate_metadata(metadata)
    assert "Missing required metadata field" in str(excinfo.value)


def test_validate_metadata_invalid_size(valid_document_metadata):
    """Test that validate_metadata rejects metadata with invalid size."""
    # Set invalid size
    metadata = valid_document_metadata.copy()
    metadata['size'] = -1
    
    with pytest.raises(ValidationError) as excinfo:
        validate_metadata(metadata)
    assert "Invalid size value" in str(excinfo.value)


def test_validate_metadata_unsupported_mime_type(valid_document_metadata):
    """Test that validate_metadata rejects metadata with unsupported MIME type."""
    # Mock the MIME type check
    with patch('document_service.utils.file_utils.is_supported_mime_type', return_value=False):
        with pytest.raises(ValidationError) as excinfo:
            validate_metadata(valid_document_metadata)
        assert "Unsupported MIME type" in str(excinfo.value)


def test_validate_metadata_invalid_confidence(valid_document_metadata):
    """Test that validate_metadata rejects metadata with invalid confidence scores."""
    # Set invalid confidence score
    metadata = valid_document_metadata.copy()
    metadata['classification_confidence'] = 1.5
    
    with pytest.raises(ValidationError) as excinfo:
        validate_metadata(metadata)
    assert "Invalid classification_confidence value" in str(excinfo.value)


def test_validate_metadata_invalid_page_count(valid_document_metadata):
    """Test that validate_metadata rejects metadata with invalid page count."""
    # Set invalid page count
    metadata = valid_document_metadata.copy()
    metadata['page_count'] = 0
    
    with pytest.raises(ValidationError) as excinfo:
        validate_metadata(metadata)
    assert "Invalid page_count value" in str(excinfo.value)


# Tests for malicious file detection

def test_is_potentially_malicious_extension(malicious_document_file):
    """Test that is_potentially_malicious detects files with malicious extensions."""
    assert is_potentially_malicious(malicious_document_file) is True


def test_is_potentially_malicious_mime_type(valid_document_file):
    """Test that is_potentially_malicious detects files with malicious MIME types."""
    # Mock the MIME type detection
    with patch('magic.Magic.from_file', return_value='application/x-msdownload'):
        assert is_potentially_malicious(valid_document_file) is True


def test_is_potentially_malicious_safe_file(valid_document_file):
    """Test that is_potentially_malicious returns False for safe files."""
    # Mock the MIME type detection
    with patch('magic.Magic.from_file', return_value='application/pdf'):
        assert is_potentially_malicious(valid_document_file) is False


# Tests for document processing validation

def test_validate_document_for_processing_valid(valid_document_file):
    """Test that validate_document_for_processing accepts valid documents."""
    # Mock the validation functions
    with patch('document_service.utils.validation_utils.validate_file_size', return_value=True):
        with patch('document_service.utils.validation_utils.validate_document_content', return_value=True):
            with patch('document_service.utils.file_utils.is_valid_document_for_type', return_value=True):
                with patch('document_service.utils.file_utils.get_mime_type', return_value='application/pdf'):
                    # Should not raise an exception
                    assert validate_document_for_processing(valid_document_file, DocumentType.APPLICATION) is True


def test_validate_document_for_processing_incompatible(valid_document_file):
    """Test that validate_document_for_processing rejects incompatible documents."""
    # Mock the validation functions
    with patch('document_service.utils.validation_utils.validate_file_size', return_value=True):
        with patch('document_service.utils.validation_utils.validate_document_content', return_value=True):
            with patch('document_service.utils.file_utils.is_valid_document_for_type', return_value=False):
                with patch('document_service.utils.file_utils.get_mime_type', return_value='application/pdf'):
                    with pytest.raises(ValidationError) as excinfo:
                        validate_document_for_processing(valid_document_file, DocumentType.APPLICATION)
                    assert "not compatible with file type" in str(excinfo.value)


# Tests for source information validation

def test_validate_email_source_valid(valid_email_source):
    """Test that validate_email_source accepts valid email sources."""
    # Should not raise an exception
    assert validate_email_source(valid_email_source) is True


def test_validate_email_source_invalid(invalid_email_source):
    """Test that validate_email_source rejects invalid email sources."""
    with pytest.raises(ValidationError) as excinfo:
        validate_email_source(invalid_email_source)
    assert "Invalid email format" in str(excinfo.value)


def test_validate_upload_source_valid(valid_upload_source):
    """Test that validate_upload_source accepts valid upload sources."""
    # Should not raise an exception
    assert validate_upload_source(valid_upload_source) is True


def test_validate_upload_source_invalid(invalid_upload_source):
    """Test that validate_upload_source rejects invalid upload sources."""
    with pytest.raises(ValidationError) as excinfo:
        validate_upload_source(invalid_upload_source)
    assert "Missing required upload source field" in str(excinfo.value)


def test_validate_api_source_valid(valid_api_source):
    """Test that validate_api_source accepts valid API sources."""
    # Should not raise an exception
    assert validate_api_source(valid_api_source) is True


def test_validate_api_source_invalid(invalid_api_source):
    """Test that validate_api_source rejects invalid API sources."""
    with pytest.raises(ValidationError) as excinfo:
        validate_api_source(invalid_api_source)
    assert "Missing required API source field" in str(excinfo.value)


def test_validate_source_information_valid(valid_email_source, valid_upload_source, valid_api_source):
    """Test that validate_source_information accepts valid sources of different types."""
    # Should not raise an exception for any valid source type
    assert validate_source_information(valid_email_source) is True
    assert validate_source_information(valid_upload_source) is True
    assert validate_source_information(valid_api_source) is True


def test_validate_source_information_missing_type():
    """Test that validate_source_information rejects sources with missing type."""
    source = {
        'received_at': '2023-05-01T12:34:56Z'
        # Missing 'source_type' field
    }
    
    with pytest.raises(ValidationError) as excinfo:
        validate_source_information(source)
    assert "Missing source_type" in str(excinfo.value)


def test_validate_source_information_missing_received_at():
    """Test that validate_source_information rejects sources with missing received_at."""
    source = {
        'source_type': 'email'
        # Missing 'received_at' field
    }
    
    with pytest.raises(ValidationError) as excinfo:
        validate_source_information(source)
    assert "Missing received_at" in str(excinfo.value)


def test_validate_source_information_invalid_type():
    """Test that validate_source_information rejects sources with invalid type."""
    source = {
        'source_type': 'invalid',
        'received_at': '2023-05-01T12:34:56Z'
    }
    
    with pytest.raises(ValidationError) as excinfo:
        validate_source_information(source)
    assert "Invalid source_type" in str(excinfo.value)


# Tests for document hash validation

def test_validate_document_hash_valid(valid_document_file):
    """Test that validate_document_hash accepts documents with matching hash."""
    # Mock the hash calculation
    with patch('document_service.utils.file_utils.calculate_file_hash', return_value='abc123'):
        # Should not raise an exception
        assert validate_document_hash(valid_document_file, 'abc123') is True


def test_validate_document_hash_mismatch(valid_document_file):
    """Test that validate_document_hash rejects documents with mismatched hash."""
    # Mock the hash calculation
    with patch('document_service.utils.file_utils.calculate_file_hash', return_value='abc123'):
        with pytest.raises(ValidationError) as excinfo:
            validate_document_hash(valid_document_file, 'def456')
        assert "Document hash mismatch" in str(excinfo.value)


# Tests for validation decorator

def test_validation_decorator():
    """Test that the validation_decorator properly handles exceptions."""
    # Define a test function that raises different types of exceptions
    @validation_decorator
    def test_func(raise_validation_error=False, raise_other_error=False):
        if raise_validation_error:
            raise ValidationError("Test validation error")
        if raise_other_error:
            raise ValueError("Test other error")
        return True
    
    # Should not raise an exception
    assert test_func() is True
    
    # Should re-raise ValidationError
    with pytest.raises(ValidationError) as excinfo:
        test_func(raise_validation_error=True)
    assert "Test validation error" in str(excinfo.value)
    
    # Should wrap other exceptions in ValidationError
    with pytest.raises(ValidationError) as excinfo:
        test_func(raise_other_error=True)
    assert "Validation error: Test other error" in str(excinfo.value)