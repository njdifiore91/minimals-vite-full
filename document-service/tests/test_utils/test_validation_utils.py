#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the validation utilities in the Document Service.

This module contains tests for document type validation, format validation,
size validation, and MIME type detection functions. It ensures that only valid
documents are processed by the service and malicious files are properly detected.
"""

import os
import io
import json
import pytest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime

# Import the module to test
from src.utils.validation_utils import (
    is_valid_document_size,
    get_mime_type,
    get_mime_type_from_buffer,
    is_supported_mime_type,
    is_supported_file_extension,
    validate_document_metadata,
    validate_document_content,
    contains_malicious_content,
    validate_message_schema,
    basic_schema_validation,
    validate_document_type,
    validate_document_type_mime_compatibility,
    validate_message_payload,
    validate_email_sender,
    validate_file_hash,
    calculate_file_hash,
    validate_document_structure,
    validate_document_page_count,
    validate_document_resolution,
    validate_document_against_rules,
    SUPPORTED_MIME_TYPES,
    SUPPORTED_EXTENSIONS,
    MAX_DOCUMENT_SIZE_MB,
    MIN_DOCUMENT_SIZE_KB,
    SUSPICIOUS_PATTERNS
)

# Import custom types
from src.types.documents import DocumentMetadata, DocumentType, DocumentContent
from src.types.messages import MessagePayload
from src.types.errors import ServiceError


# Test fixtures
@pytest.fixture
def sample_document_metadata():
    """Create a sample document metadata for testing."""
    return {
        'id': '12345',
        'filename': 'test_document.pdf',
        'size': 1024 * 100,  # 100 KB
        'mime_type': 'application/pdf',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'classification_confidence': 0.95,
        'ocr_confidence': 0.90,
        'application_id': 'app-123',
        'storage_path': 's3://bucket/documents/test_document.pdf',
        'checksum': 'abcdef1234567890',
        'page_count': 3,
        'tags': ['application', 'loan']
    }


@pytest.fixture
def sample_document_content():
    """Create a sample document content for testing."""
    return b'%PDF-1.5\nSample PDF content for testing'


@pytest.fixture
def malicious_document_content():
    """Create a sample malicious document content for testing."""
    return b'%PDF-1.5\nSample PDF content with <script>alert("malicious");</script>'


@pytest.fixture
def sample_message_payload():
    """Create a sample message payload for testing."""
    return {
        'message_id': 'msg-123',
        'document_id': 'doc-123',
        'timestamp': datetime.utcnow().isoformat(),
        'metadata': {
            'source': 'email',
            'priority': 'high'
        }
    }


@pytest.fixture
def sample_schema():
    """Create a sample JSON schema for testing."""
    return {
        'type': 'object',
        'required': ['message_id', 'document_id', 'timestamp'],
        'properties': {
            'message_id': {'type': 'string'},
            'document_id': {'type': 'string'},
            'timestamp': {'type': 'string'},
            'metadata': {
                'type': 'object',
                'properties': {
                    'source': {'type': 'string'},
                    'priority': {'type': 'string'}
                }
            }
        }
    }


# Tests for document size validation
class TestDocumentSizeValidation:
    """Tests for document size validation functions."""

    def test_valid_document_size(self):
        """Test that a document with a valid size passes validation."""
        # Test a document with a size between the min and max limits
        valid_size = 1024 * 100  # 100 KB
        assert is_valid_document_size(valid_size) is True

    def test_document_too_small(self):
        """Test that a document that is too small fails validation."""
        # Test a document smaller than the minimum size
        too_small = MIN_DOCUMENT_SIZE_KB * 1024 - 1  # 1 byte less than minimum
        assert is_valid_document_size(too_small) is False

    def test_document_too_large(self):
        """Test that a document that is too large fails validation."""
        # Test a document larger than the maximum size
        too_large = MAX_DOCUMENT_SIZE_MB * 1024 * 1024 + 1  # 1 byte more than maximum
        assert is_valid_document_size(too_large) is False

    def test_document_at_min_size(self):
        """Test that a document at the minimum size passes validation."""
        min_size = MIN_DOCUMENT_SIZE_KB * 1024
        assert is_valid_document_size(min_size) is True

    def test_document_at_max_size(self):
        """Test that a document at the maximum size passes validation."""
        max_size = MAX_DOCUMENT_SIZE_MB * 1024 * 1024
        assert is_valid_document_size(max_size) is True


# Tests for MIME type detection and validation
class TestMimeTypeValidation:
    """Tests for MIME type detection and validation functions."""

    @patch('magic.Magic')
    def test_get_mime_type(self, mock_magic):
        """Test that MIME type detection works correctly for files."""
        # Setup the mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.return_value = 'application/pdf'
        mock_magic.return_value = mock_magic_instance

        # Test the function
        mime_type = get_mime_type('test_document.pdf')
        assert mime_type == 'application/pdf'
        mock_magic_instance.from_file.assert_called_once_with('test_document.pdf')

    @patch('magic.Magic')
    def test_get_mime_type_error(self, mock_magic):
        """Test that MIME type detection handles errors correctly."""
        # Setup the mock to raise an exception
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_file.side_effect = Exception('MIME detection failed')
        mock_magic.return_value = mock_magic_instance

        # Test the function
        mime_type = get_mime_type('test_document.pdf')
        assert mime_type is False  # The validation_decorator should return False on exception

    @patch('magic.Magic')
    def test_get_mime_type_from_buffer(self, mock_magic):
        """Test that MIME type detection works correctly for buffers."""
        # Setup the mock
        mock_magic_instance = MagicMock()
        mock_magic_instance.from_buffer.return_value = 'application/pdf'
        mock_magic.return_value = mock_magic_instance

        # Test the function
        content = b'%PDF-1.5\nSample PDF content for testing'
        mime_type = get_mime_type_from_buffer(content)
        assert mime_type == 'application/pdf'
        mock_magic_instance.from_buffer.assert_called_once_with(content)

    def test_is_supported_mime_type(self):
        """Test that supported MIME types are correctly identified."""
        # Test with supported MIME types
        for mime_type in SUPPORTED_MIME_TYPES.keys():
            assert is_supported_mime_type(mime_type) is True

        # Test with unsupported MIME type
        assert is_supported_mime_type('application/unsupported') is False

    def test_is_supported_file_extension(self):
        """Test that supported file extensions are correctly identified."""
        # Test with supported file extensions
        for ext in SUPPORTED_EXTENSIONS:
            assert is_supported_file_extension(f'test_document{ext}') is True

        # Test with unsupported file extension
        assert is_supported_file_extension('test_document.unsupported') is False


# Tests for document metadata validation
class TestDocumentMetadataValidation:
    """Tests for document metadata validation functions."""

    def test_validate_document_metadata_valid(self, sample_document_metadata):
        """Test that valid document metadata passes validation."""
        is_valid, error_message = validate_document_metadata(sample_document_metadata)
        assert is_valid is True
        assert error_message is None

    def test_validate_document_metadata_missing_filename(self, sample_document_metadata):
        """Test that document metadata without a filename fails validation."""
        # Remove the filename
        sample_document_metadata['filename'] = ''
        is_valid, error_message = validate_document_metadata(sample_document_metadata)
        assert is_valid is False
        assert 'Filename is required' in error_message

    def test_validate_document_metadata_missing_mime_type(self, sample_document_metadata):
        """Test that document metadata without a MIME type fails validation."""
        # Remove the MIME type
        sample_document_metadata['mime_type'] = ''
        is_valid, error_message = validate_document_metadata(sample_document_metadata)
        assert is_valid is False
        assert 'MIME type is required' in error_message

    def test_validate_document_metadata_unsupported_mime_type(self, sample_document_metadata):
        """Test that document metadata with an unsupported MIME type fails validation."""
        # Set an unsupported MIME type
        sample_document_metadata['mime_type'] = 'application/unsupported'
        is_valid, error_message = validate_document_metadata(sample_document_metadata)
        assert is_valid is False
        assert 'Unsupported MIME type' in error_message

    def test_validate_document_metadata_invalid_size(self, sample_document_metadata):
        """Test that document metadata with an invalid size fails validation."""
        # Set an invalid size (too large)
        sample_document_metadata['size'] = MAX_DOCUMENT_SIZE_MB * 1024 * 1024 + 1
        is_valid, error_message = validate_document_metadata(sample_document_metadata)
        assert is_valid is False
        assert 'Invalid document size' in error_message


# Tests for document content validation
class TestDocumentContentValidation:
    """Tests for document content validation functions."""

    @patch('src.utils.validation_utils.get_mime_type_from_buffer')
    def test_validate_document_content_valid(self, mock_get_mime_type, sample_document_metadata, sample_document_content):
        """Test that valid document content passes validation."""
        # Setup the mock
        mock_get_mime_type.return_value = 'application/pdf'

        # Set the size in metadata to match the content
        sample_document_metadata['size'] = len(sample_document_content)

        is_valid, error_message = validate_document_content(sample_document_content, sample_document_metadata)
        assert is_valid is True
        assert error_message is None

    def test_validate_document_content_empty(self, sample_document_metadata):
        """Test that empty document content fails validation."""
        is_valid, error_message = validate_document_content(b'', sample_document_metadata)
        assert is_valid is False
        assert 'Document content is empty' in error_message

    def test_validate_document_content_size_mismatch(self, sample_document_metadata, sample_document_content):
        """Test that document content with a size mismatch fails validation."""
        # Set a different size in metadata
        sample_document_metadata['size'] = len(sample_document_content) + 100

        is_valid, error_message = validate_document_content(sample_document_content, sample_document_metadata)
        assert is_valid is False
        assert 'Content size' in error_message
        assert 'doesn\'t match metadata size' in error_message

    @patch('src.utils.validation_utils.get_mime_type_from_buffer')
    def test_validate_document_content_mime_type_mismatch(self, mock_get_mime_type, sample_document_metadata, sample_document_content):
        """Test that document content with a MIME type mismatch fails validation."""
        # Setup the mock to return a different MIME type
        mock_get_mime_type.return_value = 'image/jpeg'

        # Set the size in metadata to match the content
        sample_document_metadata['size'] = len(sample_document_content)

        is_valid, error_message = validate_document_content(sample_document_content, sample_document_metadata)
        assert is_valid is False
        assert 'Content MIME type' in error_message
        assert 'doesn\'t match metadata MIME type' in error_message

    @patch('src.utils.validation_utils.get_mime_type_from_buffer')
    @patch('src.utils.validation_utils.contains_malicious_content')
    def test_validate_document_content_malicious(self, mock_contains_malicious, mock_get_mime_type, sample_document_metadata, sample_document_content):
        """Test that document content with malicious content fails validation."""
        # Setup the mocks
        mock_get_mime_type.return_value = 'application/pdf'
        mock_contains_malicious.return_value = True

        # Set the size in metadata to match the content
        sample_document_metadata['size'] = len(sample_document_content)

        is_valid, error_message = validate_document_content(sample_document_content, sample_document_metadata)
        assert is_valid is False
        assert 'Document contains potentially malicious content' in error_message


# Tests for malicious content detection
class TestMaliciousContentDetection:
    """Tests for malicious content detection functions."""

    def test_contains_malicious_content_clean(self, sample_document_content):
        """Test that clean document content passes malicious content detection."""
        assert contains_malicious_content(sample_document_content) is False

    def test_contains_malicious_content_malicious(self, malicious_document_content):
        """Test that malicious document content is detected."""
        assert contains_malicious_content(malicious_document_content) is True

    def test_contains_malicious_content_patterns(self):
        """Test that all suspicious patterns are detected."""
        for pattern in SUSPICIOUS_PATTERNS:
            # Create a document with the suspicious pattern
            content = b'%PDF-1.5\nSample PDF content with ' + pattern + b' for testing'
            assert contains_malicious_content(content) is True


# Tests for message schema validation
class TestMessageSchemaValidation:
    """Tests for message schema validation functions."""

    @patch('os.path.join')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_validate_message_schema_valid(self, mock_json_load, mock_open_file, mock_path_join, sample_message_payload, sample_schema):
        """Test that a valid message passes schema validation."""
        # Setup the mocks
        mock_path_join.return_value = '/path/to/schema.json'
        mock_json_load.return_value = sample_schema

        # Test with jsonschema available
        with patch('src.utils.validation_utils.jsonschema') as mock_jsonschema:
            is_valid, error_message = validate_message_schema(sample_message_payload, 'document')
            assert is_valid is True
            assert error_message is None
            mock_jsonschema.validate.assert_called_once_with(sample_message_payload, sample_schema)

    @patch('os.path.join')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    def test_validate_message_schema_invalid(self, mock_json_load, mock_open_file, mock_path_join, sample_message_payload, sample_schema):
        """Test that an invalid message fails schema validation."""
        # Setup the mocks
        mock_path_join.return_value = '/path/to/schema.json'
        mock_json_load.return_value = sample_schema

        # Test with jsonschema available
        with patch('src.utils.validation_utils.jsonschema') as mock_jsonschema:
            # Make jsonschema.validate raise a ValidationError
            from jsonschema import ValidationError
            mock_jsonschema.validate.side_effect = ValidationError('Schema validation failed')

            is_valid, error_message = validate_message_schema(sample_message_payload, 'document')
            assert is_valid is False
            assert 'Schema validation error' in error_message

    @patch('os.path.join')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    @patch('src.utils.validation_utils.jsonschema', None)  # Simulate jsonschema not available
    @patch('src.utils.validation_utils.basic_schema_validation')
    def test_validate_message_schema_fallback(self, mock_basic_validation, mock_json_load, mock_open_file, mock_path_join, sample_message_payload, sample_schema):
        """Test that schema validation falls back to basic validation when jsonschema is not available."""
        # Setup the mocks
        mock_path_join.return_value = '/path/to/schema.json'
        mock_json_load.return_value = sample_schema
        mock_basic_validation.return_value = (True, None)

        is_valid, error_message = validate_message_schema(sample_message_payload, 'document')
        assert is_valid is True
        assert error_message is None
        mock_basic_validation.assert_called_once_with(sample_message_payload, sample_schema)

    @patch('os.path.join')
    @patch('builtins.open')
    def test_validate_message_schema_file_not_found(self, mock_open_file, mock_path_join, sample_message_payload):
        """Test that schema validation handles file not found errors."""
        # Setup the mocks
        mock_path_join.return_value = '/path/to/schema.json'
        mock_open_file.side_effect = FileNotFoundError('Schema file not found')

        is_valid, error_message = validate_message_schema(sample_message_payload, 'document')
        assert is_valid is False
        assert 'Schema validation error' in error_message

    def test_basic_schema_validation_valid(self, sample_message_payload, sample_schema):
        """Test that basic schema validation works correctly for valid messages."""
        is_valid, error_message = basic_schema_validation(sample_message_payload, sample_schema)
        assert is_valid is True
        assert error_message is None

    def test_basic_schema_validation_missing_required(self, sample_message_payload, sample_schema):
        """Test that basic schema validation detects missing required properties."""
        # Remove a required property
        del sample_message_payload['document_id']

        is_valid, error_message = basic_schema_validation(sample_message_payload, sample_schema)
        assert is_valid is False
        assert 'Missing required property' in error_message

    def test_basic_schema_validation_wrong_type(self, sample_message_payload, sample_schema):
        """Test that basic schema validation detects wrong property types."""
        # Change a property to the wrong type
        sample_message_payload['document_id'] = 123  # Should be a string

        is_valid, error_message = basic_schema_validation(sample_message_payload, sample_schema)
        assert is_valid is False
        assert 'should be a string' in error_message


# Tests for document type validation
class TestDocumentTypeValidation:
    """Tests for document type validation functions."""

    def test_validate_document_type_valid(self):
        """Test that valid document types pass validation."""
        for doc_type in DocumentType.__members__.keys():
            assert validate_document_type(doc_type) is True

    def test_validate_document_type_invalid(self):
        """Test that invalid document types fail validation."""
        assert validate_document_type('INVALID_TYPE') is False

    def test_validate_document_type_mime_compatibility_valid(self):
        """Test that valid document type and MIME type combinations pass validation."""
        # Test each document type with its compatible MIME types
        for doc_type, mime_types in {
            'APPLICATION': ['application/pdf'],
            'TAX_RETURN': ['application/pdf', 'image/tiff'],
            'BANK_STATEMENT': ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
            'PAY_STUB': ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
            'ID_DOCUMENT': ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
            'OTHER': list(SUPPORTED_MIME_TYPES.keys())
        }.items():
            for mime_type in mime_types:
                assert validate_document_type_mime_compatibility(doc_type, mime_type) is True

    def test_validate_document_type_mime_compatibility_invalid_type(self):
        """Test that invalid document types fail MIME compatibility validation."""
        assert validate_document_type_mime_compatibility('INVALID_TYPE', 'application/pdf') is False

    def test_validate_document_type_mime_compatibility_invalid_mime(self):
        """Test that invalid MIME types fail compatibility validation."""
        assert validate_document_type_mime_compatibility('APPLICATION', 'application/unsupported') is False

    def test_validate_document_type_mime_compatibility_incompatible(self):
        """Test that incompatible document type and MIME type combinations fail validation."""
        # APPLICATION type should only be compatible with PDF
        assert validate_document_type_mime_compatibility('APPLICATION', 'image/jpeg') is False


# Tests for message payload validation
class TestMessagePayloadValidation:
    """Tests for message payload validation functions."""

    def test_validate_message_payload_valid(self, sample_message_payload):
        """Test that a valid message payload passes validation."""
        payload = MessagePayload(sample_message_payload)
        is_valid, error_message = validate_message_payload(payload)
        assert is_valid is True
        assert error_message is None

    def test_validate_message_payload_missing_message_id(self, sample_message_payload):
        """Test that a message payload without a message ID fails validation."""
        payload = MessagePayload(sample_message_payload)
        payload['message_id'] = ''
        is_valid, error_message = validate_message_payload(payload)
        assert is_valid is False
        assert 'Message ID is required' in error_message

    def test_validate_message_payload_missing_document_id(self, sample_message_payload):
        """Test that a message payload without a document ID fails validation."""
        payload = MessagePayload(sample_message_payload)
        payload['document_id'] = ''
        is_valid, error_message = validate_message_payload(payload)
        assert is_valid is False
        assert 'Document ID is required' in error_message

    def test_validate_message_payload_missing_timestamp(self, sample_message_payload):
        """Test that a message payload without a timestamp fails validation."""
        payload = MessagePayload(sample_message_payload)
        payload['timestamp'] = ''
        is_valid, error_message = validate_message_payload(payload)
        assert is_valid is False
        assert 'Timestamp is required' in error_message


# Tests for email sender validation
class TestEmailSenderValidation:
    """Tests for email sender validation functions."""

    def test_validate_email_sender_valid(self):
        """Test that valid email senders from allowed domains pass validation."""
        allowed_domains = ['example.com', 'test.org']
        assert validate_email_sender('user@example.com', allowed_domains) is True
        assert validate_email_sender('another.user@test.org', allowed_domains) is True

    def test_validate_email_sender_invalid_domain(self):
        """Test that email senders from disallowed domains fail validation."""
        allowed_domains = ['example.com', 'test.org']
        assert validate_email_sender('user@invalid-domain.com', allowed_domains) is False

    def test_validate_email_sender_invalid_format(self):
        """Test that email senders with invalid format fail validation."""
        allowed_domains = ['example.com', 'test.org']
        assert validate_email_sender('invalid-email', allowed_domains) is False
        assert validate_email_sender('', allowed_domains) is False


# Tests for file hash validation
class TestFileHashValidation:
    """Tests for file hash validation functions."""

    def test_calculate_file_hash(self, sample_document_content):
        """Test that file hash calculation works correctly."""
        # Calculate hash with different algorithms
        sha256_hash = calculate_file_hash(sample_document_content, 'sha256')
        md5_hash = calculate_file_hash(sample_document_content, 'md5')
        sha1_hash = calculate_file_hash(sample_document_content, 'sha1')

        # Verify the hashes are not empty and have the correct format
        assert sha256_hash and len(sha256_hash) == 64  # SHA-256 is 64 hex chars
        assert md5_hash and len(md5_hash) == 32  # MD5 is 32 hex chars
        assert sha1_hash and len(sha1_hash) == 40  # SHA-1 is 40 hex chars

    def test_calculate_file_hash_invalid_algorithm(self, sample_document_content):
        """Test that file hash calculation handles invalid algorithms correctly."""
        # The validation_decorator should return False on exception
        assert calculate_file_hash(sample_document_content, 'invalid_algorithm') is False

    def test_validate_file_hash_valid(self):
        """Test that valid file hashes pass validation."""
        file_hash = 'abcdef1234567890'
        expected_hash = 'abcdef1234567890'
        assert validate_file_hash(file_hash, expected_hash) is True

    def test_validate_file_hash_invalid(self):
        """Test that invalid file hashes fail validation."""
        file_hash = 'abcdef1234567890'
        expected_hash = '0987654321fedcba'
        assert validate_file_hash(file_hash, expected_hash) is False


# Tests for document structure validation
class TestDocumentStructureValidation:
    """Tests for document structure validation functions."""

    @patch('src.utils.validation_utils.validate_document_type')
    @patch('src.utils.validation_utils.get_mime_type_from_buffer')
    @patch('src.utils.validation_utils.validate_document_type_mime_compatibility')
    def test_validate_document_structure_valid(self, mock_compatibility, mock_mime_type, mock_validate_type, sample_document_content):
        """Test that valid document structures pass validation."""
        # Setup the mocks
        mock_validate_type.return_value = True
        mock_mime_type.return_value = 'application/pdf'
        mock_compatibility.return_value = True

        is_valid, error_message = validate_document_structure(sample_document_content, 'APPLICATION')
        assert is_valid is True
        assert error_message is None

    @patch('src.utils.validation_utils.validate_document_type')
    def test_validate_document_structure_invalid_type(self, mock_validate_type, sample_document_content):
        """Test that document structures with invalid types fail validation."""
        # Setup the mock
        mock_validate_type.return_value = False

        is_valid, error_message = validate_document_structure(sample_document_content, 'INVALID_TYPE')
        assert is_valid is False
        assert 'Invalid document type' in error_message

    @patch('src.utils.validation_utils.validate_document_type')
    @patch('src.utils.validation_utils.get_mime_type_from_buffer')
    @patch('src.utils.validation_utils.validate_document_type_mime_compatibility')
    def test_validate_document_structure_incompatible_mime(self, mock_compatibility, mock_mime_type, mock_validate_type, sample_document_content):
        """Test that document structures with incompatible MIME types fail validation."""
        # Setup the mocks
        mock_validate_type.return_value = True
        mock_mime_type.return_value = 'image/jpeg'
        mock_compatibility.return_value = False

        is_valid, error_message = validate_document_structure(sample_document_content, 'APPLICATION')
        assert is_valid is False
        assert 'not compatible with MIME type' in error_message


# Tests for document page count validation
class TestDocumentPageCountValidation:
    """Tests for document page count validation functions."""

    @patch('io.BytesIO')
    @patch('PyPDF2.PdfReader')
    def test_validate_document_page_count_pdf_valid(self, mock_pdf_reader, mock_bytesio, sample_document_content):
        """Test that PDF documents with valid page counts pass validation."""
        # Setup the mocks
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [1, 2, 3]  # 3 pages
        mock_pdf_reader.return_value = mock_reader_instance

        is_valid, error_message = validate_document_page_count(sample_document_content, 'application/pdf', 1, 10)
        assert is_valid is True
        assert error_message is None

    @patch('io.BytesIO')
    @patch('PyPDF2.PdfReader')
    def test_validate_document_page_count_pdf_too_few(self, mock_pdf_reader, mock_bytesio, sample_document_content):
        """Test that PDF documents with too few pages fail validation."""
        # Setup the mocks
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [1]  # 1 page
        mock_pdf_reader.return_value = mock_reader_instance

        is_valid, error_message = validate_document_page_count(sample_document_content, 'application/pdf', 2, 10)
        assert is_valid is False
        assert 'less than the minimum' in error_message

    @patch('io.BytesIO')
    @patch('PyPDF2.PdfReader')
    def test_validate_document_page_count_pdf_too_many(self, mock_pdf_reader, mock_bytesio, sample_document_content):
        """Test that PDF documents with too many pages fail validation."""
        # Setup the mocks
        mock_reader_instance = MagicMock()
        mock_reader_instance.pages = [1, 2, 3, 4, 5, 6]  # 6 pages
        mock_pdf_reader.return_value = mock_reader_instance

        is_valid, error_message = validate_document_page_count(sample_document_content, 'application/pdf', 1, 5)
        assert is_valid is False
        assert 'exceeds the maximum' in error_message

    @patch('io.BytesIO')
    @patch('PIL.Image.open')
    def test_validate_document_page_count_tiff_valid(self, mock_image_open, mock_bytesio, sample_document_content):
        """Test that TIFF documents with valid page counts pass validation."""
        # Setup the mocks
        mock_image_instance = MagicMock()
        # Make the image have 3 frames by having it raise EOFError after 3 seeks
        mock_image_instance.tell.side_effect = [0, 1, 2]
        mock_image_instance.seek.side_effect = [None, None, EOFError()]
        mock_image_open.return_value = mock_image_instance

        is_valid, error_message = validate_document_page_count(sample_document_content, 'image/tiff', 1, 10)
        assert is_valid is True
        assert error_message is None

    @patch('io.BytesIO')
    @patch('PIL.Image.open')
    def test_validate_document_page_count_import_error(self, mock_image_open, mock_bytesio, sample_document_content):
        """Test that page count validation handles import errors correctly."""
        # Setup the mocks to simulate ImportError
        mock_image_open.side_effect = ImportError('PIL not available')

        # Should return True when PIL is not available (skip validation)
        is_valid, error_message = validate_document_page_count(sample_document_content, 'image/tiff', 1, 10)
        assert is_valid is True
        assert error_message is None


# Tests for document resolution validation
class TestDocumentResolutionValidation:
    """Tests for document resolution validation functions."""

    @patch('io.BytesIO')
    @patch('PIL.Image.open')
    def test_validate_document_resolution_valid(self, mock_image_open, mock_bytesio, sample_document_content):
        """Test that documents with valid resolution pass validation."""
        # Setup the mocks
        mock_image_instance = MagicMock()
        mock_image_instance.info = {'dpi': (300, 300)}  # 300 DPI
        mock_image_open.return_value = mock_image_instance

        is_valid, error_message = validate_document_resolution(sample_document_content, 'image/jpeg', 200)
        assert is_valid is True
        assert error_message is None

    @patch('io.BytesIO')
    @patch('PIL.Image.open')
    def test_validate_document_resolution_too_low(self, mock_image_open, mock_bytesio, sample_document_content):
        """Test that documents with too low resolution fail validation."""
        # Setup the mocks
        mock_image_instance = MagicMock()
        mock_image_instance.info = {'dpi': (150, 150)}  # 150 DPI
        mock_image_open.return_value = mock_image_instance

        is_valid, error_message = validate_document_resolution(sample_document_content, 'image/jpeg', 200)
        assert is_valid is False
        assert 'below minimum' in error_message

    @patch('io.BytesIO')
    @patch('PIL.Image.open')
    def test_validate_document_resolution_no_dpi_info(self, mock_image_open, mock_bytesio, sample_document_content):
        """Test that documents without DPI information are handled correctly."""
        # Setup the mocks
        mock_image_instance = MagicMock()
        mock_image_instance.info = {}  # No DPI info
        mock_image_instance.size = (2000, 3000)  # Large enough dimensions
        mock_image_open.return_value = mock_image_instance

        # Should pass validation based on dimensions
        is_valid, error_message = validate_document_resolution(sample_document_content, 'image/jpeg', 200)
        assert is_valid is True
        assert error_message is None

    @patch('io.BytesIO')
    @patch('PIL.Image.open')
    def test_validate_document_resolution_small_dimensions(self, mock_image_open, mock_bytesio, sample_document_content):
        """Test that documents with small dimensions are handled correctly."""
        # Setup the mocks
        mock_image_instance = MagicMock()
        mock_image_instance.info = {}  # No DPI info
        mock_image_instance.size = (500, 700)  # Small dimensions
        mock_image_open.return_value = mock_image_instance

        # Should still pass but log a warning
        with patch('src.utils.validation_utils.logger.warning') as mock_logger:
            is_valid, error_message = validate_document_resolution(sample_document_content, 'image/jpeg', 200)
            assert is_valid is True
            assert error_message is None
            mock_logger.assert_called_once()

    def test_validate_document_resolution_non_image(self, sample_document_content):
        """Test that non-image documents skip resolution validation."""
        # Should pass for non-image formats
        is_valid, error_message = validate_document_resolution(sample_document_content, 'application/pdf', 200)
        assert is_valid is True
        assert error_message is None


# Tests for document rule validation
class TestDocumentRuleValidation:
    """Tests for document rule validation functions."""

    def test_validate_document_against_rules_no_match(self):
        """Test that documents that don't match any rules pass validation."""
        document = {
            'mime_type': 'application/pdf',
            'size': 1024 * 100,
            'filename': 'test_document.pdf'
        }

        rules = [
            {
                'name': 'Reject large images',
                'conditions': [
                    {'field': 'mime_type', 'operator': 'equals', 'value': 'image/jpeg'},
                    {'field': 'size', 'operator': 'greater_than', 'value': 1024 * 1024 * 10}
                ],
                'action': {'type': 'reject', 'reason': 'Image too large'}
            }
        ]

        is_valid, error_message = validate_document_against_rules(document, rules)
        assert is_valid is True
        assert error_message is None

    def test_validate_document_against_rules_match_reject(self):
        """Test that documents that match rejection rules fail validation."""
        document = {
            'mime_type': 'image/jpeg',
            'size': 1024 * 1024 * 20,  # 20 MB
            'filename': 'large_image.jpg'
        }

        rules = [
            {
                'name': 'Reject large images',
                'conditions': [
                    {'field': 'mime_type', 'operator': 'equals', 'value': 'image/jpeg'},
                    {'field': 'size', 'operator': 'greater_than', 'value': 1024 * 1024 * 10}
                ],
                'action': {'type': 'reject', 'reason': 'Image too large'}
            }
        ]

        is_valid, error_message = validate_document_against_rules(document, rules)
        assert is_valid is False
        assert 'Image too large' in error_message

    def test_validate_document_against_rules_match_flag(self):
        """Test that documents that match flag rules pass validation but log a warning."""
        document = {
            'mime_type': 'application/pdf',
            'size': 1024 * 1024 * 5,  # 5 MB
            'filename': 'suspicious_document.pdf'
        }

        rules = [
            {
                'name': 'Flag suspicious PDFs',
                'conditions': [
                    {'field': 'mime_type', 'operator': 'equals', 'value': 'application/pdf'},
                    {'field': 'filename', 'operator': 'contains', 'value': 'suspicious'}
                ],
                'action': {'type': 'flag', 'reason': 'Suspicious filename'}
            }
        ]

        with patch('src.utils.validation_utils.logger.warning') as mock_logger:
            is_valid, error_message = validate_document_against_rules(document, rules)
            assert is_valid is True
            assert error_message is None
            mock_logger.assert_called_once()

    def test_validate_document_against_rules_multiple_operators(self):
        """Test that rules with different operators work correctly."""
        document = {
            'mime_type': 'application/pdf',
            'size': 1024 * 100,
            'filename': 'test_document.pdf',
            'tags': ['confidential', 'financial']
        }

        rules = [
            {
                'name': 'Flag confidential documents',
                'conditions': [
                    {'field': 'tags', 'operator': 'contains', 'value': 'confidential'}
                ],
                'action': {'type': 'flag', 'reason': 'Confidential document'}
            },
            {
                'name': 'Reject specific file',
                'conditions': [
                    {'field': 'filename', 'operator': 'equals', 'value': 'specific_file.pdf'}
                ],
                'action': {'type': 'reject', 'reason': 'Specific file rejected'}
            },
            {
                'name': 'Flag documents with specific tags',
                'conditions': [
                    {'field': 'tags', 'operator': 'in', 'value': ['financial', 'tax']}
                ],
                'action': {'type': 'flag', 'reason': 'Financial document'}
            }
        ]

        with patch('src.utils.validation_utils.logger.warning') as mock_logger:
            is_valid, error_message = validate_document_against_rules(document, rules)
            assert is_valid is True
            assert error_message is None
            # Should be called twice (once for each matching flag rule)
            assert mock_logger.call_count == 2