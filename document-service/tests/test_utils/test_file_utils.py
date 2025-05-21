#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for file_utils.py module.

This module contains comprehensive tests for the file handling utilities in the Document Service.
It verifies that file operations, MIME type detection, content type validation, file size formatting,
and temporary file management functions work correctly. These tests ensure that document processing
and preparation for classification and storage work as expected.

The tests cover:
1. File operations and buffer handling functions
2. MIME type detection and validation
3. File size calculation and formatting
4. Content type mapping for different document formats
5. Temporary file management for document processing

These tests are critical for ensuring the Document Service can properly handle various document
types (PDF, TIFF, JPEG, PNG) as specified in the MCA Application Processing System requirements.
"""

import os
import io
import tempfile
import pytest
import shutil
import hashlib
from unittest import mock
from pathlib import Path

# Import the module to test
from src.utils import file_utils
from src.types.documents import DocumentType
from src.types.errors import ServiceError


# Fixtures for test files
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after tests
    shutil.rmtree(temp_dir)


@pytest.fixture
def pdf_test_file(temp_dir):
    """Create a temporary PDF test file."""
    file_path = os.path.join(temp_dir, "test.pdf")
    # Create a simple PDF-like content
    with open(file_path, "wb") as f:
        f.write(b"%PDF-1.5\nTest PDF content")
    yield file_path


@pytest.fixture
def jpeg_test_file(temp_dir):
    """Create a temporary JPEG test file."""
    file_path = os.path.join(temp_dir, "test.jpg")
    # Create a simple JPEG-like content
    with open(file_path, "wb") as f:
        f.write(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00Test JPEG content")
    yield file_path


@pytest.fixture
def png_test_file(temp_dir):
    """Create a temporary PNG test file."""
    file_path = os.path.join(temp_dir, "test.png")
    # Create a simple PNG-like content
    with open(file_path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n\x00Test PNG content")
    yield file_path


@pytest.fixture
def tiff_test_file(temp_dir):
    """Create a temporary TIFF test file."""
    file_path = os.path.join(temp_dir, "test.tiff")
    # Create a simple TIFF-like content
    with open(file_path, "wb") as f:
        f.write(b"II*\x00\x08\x00\x00\x00Test TIFF content")
    yield file_path


@pytest.fixture
def unsupported_test_file(temp_dir):
    """Create a temporary unsupported file type."""
    file_path = os.path.join(temp_dir, "test.xyz")
    with open(file_path, "wb") as f:
        f.write(b"Unsupported file content")
    yield file_path


@pytest.fixture
def test_buffer():
    """Create a test buffer."""
    return b"Test buffer content"


# Tests for file operations and buffer handling
class TestFileOperations:
    """Tests for file operations and buffer handling functions."""

    def test_get_file_size(self, pdf_test_file):
        """Test getting file size in bytes."""
        size = file_utils.get_file_size(pdf_test_file)
        assert size > 0
        assert size == os.path.getsize(pdf_test_file)

    def test_get_file_size_from_buffer(self, test_buffer):
        """Test getting size from a buffer."""
        size = file_utils.get_file_size_from_buffer(test_buffer)
        assert size == len(test_buffer)

    def test_read_file_to_buffer(self, pdf_test_file):
        """Test reading a file into a buffer."""
        buffer = file_utils.read_file_to_buffer(pdf_test_file)
        assert isinstance(buffer, bytes)
        with open(pdf_test_file, "rb") as f:
            expected = f.read()
        assert buffer == expected

    def test_write_buffer_to_file(self, temp_dir, test_buffer):
        """Test writing a buffer to a file."""
        file_path = os.path.join(temp_dir, "buffer_test.txt")
        file_utils.write_buffer_to_file(test_buffer, file_path)
        assert os.path.exists(file_path)
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == test_buffer

    def test_read_file_in_chunks(self, pdf_test_file):
        """Test reading a file in chunks."""
        chunks = list(file_utils.read_file_in_chunks(pdf_test_file, chunk_size=5))
        assert len(chunks) > 0
        # Reconstruct the file content from chunks
        reconstructed = b"".join(chunks)
        with open(pdf_test_file, "rb") as f:
            expected = f.read()
        assert reconstructed == expected

    def test_copy_file(self, pdf_test_file, temp_dir):
        """Test copying a file."""
        dest_path = os.path.join(temp_dir, "copied_file.pdf")
        file_utils.copy_file(pdf_test_file, dest_path)
        assert os.path.exists(dest_path)
        # Verify content is the same
        with open(pdf_test_file, "rb") as f1, open(dest_path, "rb") as f2:
            assert f1.read() == f2.read()

    def test_ensure_directory_exists(self, temp_dir):
        """Test ensuring a directory exists."""
        new_dir = os.path.join(temp_dir, "new_directory")
        file_utils.ensure_directory_exists(new_dir)
        assert os.path.exists(new_dir)
        assert os.path.isdir(new_dir)
        # Test idempotence - should not raise an error if directory already exists
        file_utils.ensure_directory_exists(new_dir)

    def test_remove_file(self, temp_dir):
        """Test removing a file."""
        file_path = os.path.join(temp_dir, "to_remove.txt")
        with open(file_path, "w") as f:
            f.write("Test content")
        assert os.path.exists(file_path)
        file_utils.remove_file(file_path)
        assert not os.path.exists(file_path)
        # Should not raise an error if file doesn't exist
        file_utils.remove_file(file_path)

    def test_remove_directory(self, temp_dir):
        """Test removing a directory."""
        dir_path = os.path.join(temp_dir, "dir_to_remove")
        os.makedirs(dir_path)
        nested_dir = os.path.join(dir_path, "nested")
        os.makedirs(nested_dir)
        with open(os.path.join(nested_dir, "test.txt"), "w") as f:
            f.write("Test content")

        assert os.path.exists(dir_path)
        file_utils.remove_directory(dir_path)
        assert not os.path.exists(dir_path)

        # Test non-recursive removal
        empty_dir = os.path.join(temp_dir, "empty_dir")
        os.makedirs(empty_dir)
        file_utils.remove_directory(empty_dir, recursive=False)
        assert not os.path.exists(empty_dir)

    def test_buffer_to_stream(self, test_buffer):
        """Test converting a buffer to a BytesIO stream."""
        stream = file_utils.buffer_to_stream(test_buffer)
        assert isinstance(stream, io.BytesIO)
        assert stream.getvalue() == test_buffer

    def test_stream_to_buffer(self):
        """Test converting a BytesIO stream to a buffer."""
        test_data = b"Test stream data"
        stream = io.BytesIO(test_data)
        # Move the position to simulate some operations
        stream.seek(5)
        buffer = file_utils.stream_to_buffer(stream)
        assert buffer == test_data
        # Verify the stream position is restored
        assert stream.tell() == 5

    def test_calculate_file_hash(self, pdf_test_file):
        """Test calculating file hash."""
        # Calculate expected hash
        with open(pdf_test_file, "rb") as f:
            content = f.read()
        expected_hash = hashlib.sha256(content).hexdigest()

        # Test the function
        file_hash = file_utils.calculate_file_hash(pdf_test_file)
        assert file_hash == expected_hash

        # Test with different algorithms
        md5_hash = file_utils.calculate_file_hash(pdf_test_file, algorithm="md5")
        assert md5_hash == hashlib.md5(content).hexdigest()

    def test_calculate_buffer_hash(self, test_buffer):
        """Test calculating buffer hash."""
        expected_hash = hashlib.sha256(test_buffer).hexdigest()
        buffer_hash = file_utils.calculate_buffer_hash(test_buffer)
        assert buffer_hash == expected_hash

        # Test with different algorithms
        md5_hash = file_utils.calculate_buffer_hash(test_buffer, algorithm="md5")
        assert md5_hash == hashlib.md5(test_buffer).hexdigest()

    def test_get_file_metadata(self, pdf_test_file):
        """Test getting file metadata."""
        metadata = file_utils.get_file_metadata(pdf_test_file)
        assert "file_name" in metadata
        assert "file_path" in metadata
        assert "file_size" in metadata
        assert "file_size_formatted" in metadata
        assert "mime_type" in metadata
        assert "file_extension" in metadata
        assert "created_at" in metadata
        assert "modified_at" in metadata
        assert "accessed_at" in metadata

        assert metadata["file_name"] == os.path.basename(pdf_test_file)
        assert metadata["file_path"] == pdf_test_file
        assert metadata["file_size"] > 0
        assert metadata["file_extension"] == ".pdf"

    def test_file_operation_decorator_error_handling(self):
        """Test error handling in file operation decorator."""
        # Create a function that will raise an exception
        @file_utils.file_operation_decorator
        def failing_function():
            raise IOError("Test error")

        # The decorator should catch the exception and raise a ServiceError
        with pytest.raises(ServiceError) as excinfo:
            failing_function()
        assert "Test error" in str(excinfo.value)


# Tests for MIME type detection and validation
class TestMimeTypeOperations:
    """Tests for MIME type detection and validation functions."""

    def test_get_mime_type(self, pdf_test_file, jpeg_test_file, png_test_file, tiff_test_file):
        """Test MIME type detection from file path."""
        # Test with different file types
        assert file_utils.get_mime_type(pdf_test_file) == "application/pdf"
        assert file_utils.get_mime_type(jpeg_test_file) == "image/jpeg"
        assert file_utils.get_mime_type(png_test_file) == "image/png"
        assert file_utils.get_mime_type(tiff_test_file) == "image/tiff"

    def test_get_mime_type_fallback(self, pdf_test_file):
        """Test MIME type detection fallback when python-magic is not available."""
        # Mock ImportError for python-magic
        with mock.patch.dict("sys.modules", {"magic": None}):
            with mock.patch("importlib.import_module", side_effect=ImportError):
                mime_type = file_utils.get_mime_type(pdf_test_file)
                assert mime_type == "application/pdf"

    def test_get_mime_type_from_buffer(self, test_buffer):
        """Test MIME type detection from buffer."""
        # This is harder to test without actual file content
        # Just verify it returns something and doesn't crash
        mime_type = file_utils.get_mime_type_from_buffer(test_buffer)
        assert isinstance(mime_type, str)

    def test_get_mime_type_from_filename(self):
        """Test MIME type detection from filename."""
        assert file_utils.get_mime_type_from_filename("test.pdf") == "application/pdf"
        assert file_utils.get_mime_type_from_filename("test.jpg") == "image/jpeg"
        assert file_utils.get_mime_type_from_filename("test.png") == "image/png"
        assert file_utils.get_mime_type_from_filename("test.tiff") == "image/tiff"
        assert file_utils.get_mime_type_from_filename("test.unknown") == "application/octet-stream"

    def test_is_supported_mime_type(self):
        """Test checking if a MIME type is supported."""
        assert file_utils.is_supported_mime_type("application/pdf")
        assert file_utils.is_supported_mime_type("image/jpeg")
        assert file_utils.is_supported_mime_type("image/png")
        assert file_utils.is_supported_mime_type("image/tiff")
        assert not file_utils.is_supported_mime_type("text/plain")
        assert not file_utils.is_supported_mime_type("application/zip")

    def test_is_supported_file_extension(self):
        """Test checking if a file extension is supported."""
        assert file_utils.is_supported_file_extension("test.pdf")
        assert file_utils.is_supported_file_extension("test.jpg")
        assert file_utils.is_supported_file_extension("test.jpeg")
        assert file_utils.is_supported_file_extension("test.png")
        assert file_utils.is_supported_file_extension("test.tiff")
        assert file_utils.is_supported_file_extension("test.tif")
        assert not file_utils.is_supported_file_extension("test.txt")
        assert not file_utils.is_supported_file_extension("test.docx")

    def test_get_file_extension(self):
        """Test getting file extension from path."""
        assert file_utils.get_file_extension("/path/to/file.pdf") == ".pdf"
        assert file_utils.get_file_extension("file.jpg") == ".jpg"
        assert file_utils.get_file_extension("file") == ""
        assert file_utils.get_file_extension("/path/to/file.with.multiple.dots.png") == ".png"

    def test_get_file_extension_from_mime_type(self):
        """Test getting file extension from MIME type."""
        assert file_utils.get_file_extension_from_mime_type("application/pdf") == ".pdf"
        assert file_utils.get_file_extension_from_mime_type("image/jpeg") == ".jpg"
        assert file_utils.get_file_extension_from_mime_type("image/png") == ".png"
        assert file_utils.get_file_extension_from_mime_type("image/tiff") == ".tiff"
        # Test with unsupported MIME type
        ext = file_utils.get_file_extension_from_mime_type("text/plain")
        # This might return .txt or None depending on the system's mimetypes database
        assert ext is None or ext.startswith(".")

    def test_is_valid_document_for_type(self, pdf_test_file, jpeg_test_file, tiff_test_file):
        """Test validating document type compatibility."""
        # APPLICATION documents should only be PDF
        assert file_utils.is_valid_document_for_type(pdf_test_file, DocumentType.APPLICATION.value)
        assert not file_utils.is_valid_document_for_type(jpeg_test_file, DocumentType.APPLICATION.value)

        # TAX_RETURN documents can be PDF or TIFF
        assert file_utils.is_valid_document_for_type(pdf_test_file, DocumentType.TAX_RETURN.value)
        assert file_utils.is_valid_document_for_type(tiff_test_file, DocumentType.TAX_RETURN.value)
        assert not file_utils.is_valid_document_for_type(jpeg_test_file, DocumentType.TAX_RETURN.value)

        # BANK_STATEMENT, PAY_STUB, and ID_DOCUMENT can be any supported format
        assert file_utils.is_valid_document_for_type(pdf_test_file, DocumentType.BANK_STATEMENT.value)
        assert file_utils.is_valid_document_for_type(jpeg_test_file, DocumentType.BANK_STATEMENT.value)
        assert file_utils.is_valid_document_for_type(tiff_test_file, DocumentType.BANK_STATEMENT.value)

        # Test with invalid document type
        assert not file_utils.is_valid_document_for_type(pdf_test_file, "invalid_type")


# Tests for file size formatting
class TestFileSizeFormatting:
    """Tests for file size formatting functions."""

    def test_format_file_size(self):
        """Test formatting file size in human-readable format."""
        assert file_utils.format_file_size(0) == "0 B"
        assert file_utils.format_file_size(1024) == "1 KB"
        assert file_utils.format_file_size(1536) == "1.5 KB"
        assert file_utils.format_file_size(1048576) == "1 MB"
        assert file_utils.format_file_size(1073741824) == "1 GB"
        assert file_utils.format_file_size(1099511627776) == "1 TB"

        # Test with different decimal places
        assert file_utils.format_file_size(1500, decimal_places=0) == "1 KB"
        assert file_utils.format_file_size(1500, decimal_places=1) == "1.5 KB"
        assert file_utils.format_file_size(1500, decimal_places=3) == "1.465 KB"

    def test_convert_size_to_bytes(self):
        """Test converting size from specific unit to bytes."""
        assert file_utils.convert_size_to_bytes(1, "B") == 1
        assert file_utils.convert_size_to_bytes(1, "KB") == 1024
        assert file_utils.convert_size_to_bytes(1.5, "KB") == 1536
        assert file_utils.convert_size_to_bytes(1, "MB") == 1048576
        assert file_utils.convert_size_to_bytes(1, "GB") == 1073741824
        assert file_utils.convert_size_to_bytes(1, "TB") == 1099511627776

        # Test with invalid unit
        with pytest.raises(ValueError):
            file_utils.convert_size_to_bytes(1, "XB")


# Tests for temporary file management
class TestTempFileManagement:
    """Tests for temporary file management functions."""

    def test_create_temp_file(self):
        """Test creating a temporary file."""
        path, file_obj = file_utils.create_temp_file(suffix=".txt")
        try:
            assert os.path.exists(path)
            assert path.endswith(".txt")
            assert file_obj.mode == "wb"
            # Write some data to the file
            file_obj.write(b"Test content")
            file_obj.close()
            # Verify the content was written
            with open(path, "rb") as f:
                assert f.read() == b"Test content"
        finally:
            # Clean up
            if os.path.exists(path):
                os.remove(path)

    def test_create_named_temp_file(self):
        """Test creating a named temporary file."""
        temp_file = file_utils.create_named_temp_file(suffix=".txt")
        try:
            assert os.path.exists(temp_file.name)
            assert temp_file.name.endswith(".txt")
            # Write some data to the file
            temp_file.write(b"Test content")
            temp_file.flush()
            # Verify the content was written
            with open(temp_file.name, "rb") as f:
                assert f.read() == b"Test content"
        finally:
            # Clean up
            temp_file.close()

    def test_create_temp_directory(self):
        """Test creating a temporary directory."""
        dir_path = file_utils.create_temp_directory()
        try:
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
            # Create a file in the directory
            test_file = os.path.join(dir_path, "test.txt")
            with open(test_file, "w") as f:
                f.write("Test content")
            assert os.path.exists(test_file)
        finally:
            # Clean up
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)

    def test_temp_file_manager(self):
        """Test TempFileManager context manager."""
        with file_utils.TempFileManager(suffix=".txt") as manager:
            # Create a temporary file
            file_path = manager.create_temp_file(b"Test content")
            assert os.path.exists(file_path)
            assert file_path.endswith(".txt")
            # Verify the content was written
            with open(file_path, "rb") as f:
                assert f.read() == b"Test content"

            # Create a temporary directory
            dir_path = manager.create_temp_directory()
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)

            # Remember paths for checking cleanup
            temp_file_path = file_path
            temp_dir_path = dir_path

        # After the context manager exits, files should be cleaned up
        assert not os.path.exists(temp_file_path)
        assert not os.path.exists(temp_dir_path)

    def test_temp_file_manager_cleanup(self):
        """Test TempFileManager cleanup method."""
        manager = file_utils.TempFileManager()
        file_path = manager.create_temp_file()
        dir_path = manager.create_temp_directory()

        assert os.path.exists(file_path)
        assert os.path.exists(dir_path)

        # Manually call cleanup
        manager.cleanup()

        assert not os.path.exists(file_path)
        assert not os.path.exists(dir_path)

    def test_spooled_temp_file_manager(self):
        """Test SpooledTempFileManager context manager."""
        with file_utils.SpooledTempFileManager(max_size=1024) as manager:
            # Create a spooled temporary file
            temp_file = manager.create_spooled_temp_file()
            assert temp_file is not None

            # Write some data to the file
            temp_file.write(b"Test content")
            temp_file.flush()

            # Verify the content was written
            temp_file.seek(0)
            assert temp_file.read() == b"Test content"

            # Remember the file for checking cleanup
            spooled_file = temp_file

        # After the context manager exits, the file should be closed
        with pytest.raises(ValueError):
            # This should raise an error because the file is closed
            spooled_file.write(b"More content")

    def test_get_document_page_count(self, pdf_test_file, jpeg_test_file):
        """Test getting document page count."""
        # Mock PyPDF2 for PDF page count
        with mock.patch("src.utils.file_utils.PdfReader") as mock_pdf_reader:
            mock_pdf_reader.return_value.pages = [None, None, None]  # 3 pages
            page_count = file_utils.get_document_page_count(pdf_test_file)
            assert page_count == 3

        # For JPEG, it should return 1
        assert file_utils.get_document_page_count(jpeg_test_file) == 1

    def test_split_pdf_into_pages(self, pdf_test_file, temp_dir):
        """Test splitting PDF into pages."""
        # Mock PyPDF2 for PDF splitting
        with mock.patch("src.utils.file_utils.PdfReader") as mock_pdf_reader, \
             mock.patch("src.utils.file_utils.PdfWriter") as mock_pdf_writer:
            # Mock 3 pages in the PDF
            mock_pdf_reader.return_value.pages = [mock.MagicMock(), mock.MagicMock(), mock.MagicMock()]
            
            # Call the function
            output_dir = os.path.join(temp_dir, "pdf_pages")
            page_paths = file_utils.split_pdf_into_pages(pdf_test_file, output_dir)
            
            # Verify the results
            assert len(page_paths) == 3
            for i, path in enumerate(page_paths):
                assert path == os.path.join(output_dir, f"page_{i + 1}.pdf")

    def test_create_document_metadata(self, pdf_test_file):
        """Test creating document metadata."""
        metadata = file_utils.create_document_metadata(pdf_test_file)
        assert "id" in metadata
        assert "filename" in metadata
        assert "size" in metadata
        assert "mime_type" in metadata
        assert "created_at" in metadata
        assert "updated_at" in metadata
        assert "checksum" in metadata
        
        assert metadata["filename"] == os.path.basename(pdf_test_file)
        assert metadata["mime_type"] == "application/pdf"
        assert metadata["size"] > 0