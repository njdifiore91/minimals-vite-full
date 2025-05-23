#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the file_utils.py module.

This module contains tests for file operations, MIME type detection, content type validation,
file size calculation, and temporary file management to ensure proper document processing and storage.
"""

import os
import io
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils import file_utils


class TestMimeTypeDetection:
    """Tests for MIME type detection functions."""

    def test_get_mime_type(self, temp_dir):
        """Test determining MIME type based on file extension."""
        # Create test files with different extensions
        pdf_path = temp_dir / "test.pdf"
        pdf_path.touch()
        
        jpg_path = temp_dir / "test.jpg"
        jpg_path.touch()
        
        tiff_path = temp_dir / "test.tiff"
        tiff_path.touch()
        
        png_path = temp_dir / "test.png"
        png_path.touch()
        
        unknown_path = temp_dir / "test.unknown"
        unknown_path.touch()
        
        # Test MIME type detection for each file
        assert file_utils.get_mime_type(pdf_path) == "application/pdf"
        assert file_utils.get_mime_type(jpg_path) == "image/jpeg"
        assert file_utils.get_mime_type(tiff_path) == "image/tiff"
        assert file_utils.get_mime_type(png_path) == "image/png"
        assert file_utils.get_mime_type(unknown_path) is None
        
        # Test with string paths
        assert file_utils.get_mime_type(str(pdf_path)) == "application/pdf"
        
        # Test with non-existent file (should still work based on extension)
        non_existent = temp_dir / "non_existent.pdf"
        assert file_utils.get_mime_type(non_existent) == "application/pdf"

    def test_get_mime_type_from_content(self, temp_dir, sample_pdf_file, sample_image_file):
        """Test determining MIME type based on file content using python-magic."""
        # Test with file path
        with patch('magic.Magic') as mock_magic:
            mock_instance = MagicMock()
            mock_magic.return_value = mock_instance
            mock_instance.from_file.return_value = "application/pdf"
            
            mime_type = file_utils.get_mime_type_from_content(sample_pdf_file)
            assert mime_type == "application/pdf"
            mock_instance.from_file.assert_called_once_with(str(sample_pdf_file))
        
        # Test with bytes content
        with patch('magic.Magic') as mock_magic:
            mock_instance = MagicMock()
            mock_magic.return_value = mock_instance
            mock_instance.from_buffer.return_value = "image/png"
            
            content = b"PNG file content"
            mime_type = file_utils.get_mime_type_from_content(content)
            assert mime_type == "image/png"
            mock_instance.from_buffer.assert_called_once_with(content)
        
        # Test with file-like object
        with patch('magic.Magic') as mock_magic:
            mock_instance = MagicMock()
            mock_magic.return_value = mock_instance
            mock_instance.from_buffer.return_value = "image/jpeg"
            
            file_obj = io.BytesIO(b"JPEG file content")
            mime_type = file_utils.get_mime_type_from_content(file_obj)
            assert mime_type == "image/jpeg"
            mock_instance.from_buffer.assert_called_once()
        
        # Test with unsupported type
        with patch('magic.Magic') as mock_magic:
            mock_instance = MagicMock()
            mock_magic.return_value = mock_instance
            
            mime_type = file_utils.get_mime_type_from_content(123)  # Integer is not supported
            assert mime_type is None
        
        # Test with ImportError (fallback to extension-based detection)
        with patch('magic.Magic', side_effect=ImportError("No module named 'magic'")):
            with patch('src.utils.file_utils.get_mime_type') as mock_get_mime_type:
                mock_get_mime_type.return_value = "application/pdf"
                
                mime_type = file_utils.get_mime_type_from_content(sample_pdf_file)
                assert mime_type == "application/pdf"
                mock_get_mime_type.assert_called_once_with(sample_pdf_file)
        
        # Test with exception during detection
        with patch('magic.Magic') as mock_magic:
            mock_instance = MagicMock()
            mock_magic.return_value = mock_instance
            mock_instance.from_file.side_effect = Exception("Error detecting MIME type")
            
            mime_type = file_utils.get_mime_type_from_content(sample_pdf_file)
            assert mime_type is None


class TestDocumentTypeValidation:
    """Tests for document type validation functions."""

    def test_is_supported_document_type(self, temp_dir, sample_pdf_file, sample_image_file):
        """Test checking if a file is a supported document type for OCR processing."""
        # Test with supported file types
        with patch('src.utils.file_utils.get_mime_type_from_content') as mock_get_mime:
            # Test PDF
            mock_get_mime.return_value = "application/pdf"
            assert file_utils.is_supported_document_type(sample_pdf_file) is True
            
            # Test JPEG
            mock_get_mime.return_value = "image/jpeg"
            assert file_utils.is_supported_document_type(sample_image_file) is True
            
            # Test PNG
            mock_get_mime.return_value = "image/png"
            assert file_utils.is_supported_document_type("test.png") is True
            
            # Test TIFF
            mock_get_mime.return_value = "image/tiff"
            assert file_utils.is_supported_document_type("test.tiff") is True
        
        # Test with unsupported file type
        with patch('src.utils.file_utils.get_mime_type_from_content') as mock_get_mime:
            mock_get_mime.return_value = "text/plain"
            assert file_utils.is_supported_document_type("test.txt") is False
        
        # Test with unknown MIME type, fallback to extension-based detection
        with patch('src.utils.file_utils.get_mime_type_from_content') as mock_get_mime:
            mock_get_mime.return_value = None
            
            with patch('src.utils.file_utils.get_mime_type') as mock_get_mime_ext:
                # Test with supported extension
                mock_get_mime_ext.return_value = "application/pdf"
                assert file_utils.is_supported_document_type("test.pdf") is True
                
                # Test with unsupported extension
                mock_get_mime_ext.return_value = "text/plain"
                assert file_utils.is_supported_document_type("test.txt") is False
                
                # Test with unknown extension
                mock_get_mime_ext.return_value = None
                assert file_utils.is_supported_document_type("test.unknown") is False

    def test_is_valid_file(self, temp_dir):
        """Test checking if a file exists and is accessible."""
        # Create a test file
        test_file = temp_dir / "test_file.txt"
        test_file.touch()
        
        # Test with existing file
        assert file_utils.is_valid_file(test_file) is True
        assert file_utils.is_valid_file(str(test_file)) is True
        
        # Test with non-existent file
        non_existent = temp_dir / "non_existent.txt"
        assert file_utils.is_valid_file(non_existent) is False
        
        # Test with directory (not a file)
        assert file_utils.is_valid_file(temp_dir) is False
        
        # Test with permission error
        with patch('os.access', return_value=False):
            assert file_utils.is_valid_file(test_file) is False
        
        # Test with exception
        with patch('os.path.isfile', side_effect=Exception("Test exception")):
            assert file_utils.is_valid_file(test_file) is False


class TestFileOperations:
    """Tests for file operation functions."""

    def test_get_file_extension(self):
        """Test getting the file extension from a file path."""
        # Test with various file paths
        assert file_utils.get_file_extension("/path/to/file.pdf") == ".pdf"
        assert file_utils.get_file_extension("file.jpg") == ".jpg"
        assert file_utils.get_file_extension("path/to/file.tar.gz") == ".gz"  # Gets the last extension
        assert file_utils.get_file_extension("file_without_extension") == ""
        assert file_utils.get_file_extension("/path/with.dots/file.txt") == ".txt"
        
        # Test with Path objects
        assert file_utils.get_file_extension(Path("/path/to/file.pdf")) == ".pdf"
        assert file_utils.get_file_extension(Path("file_without_extension")) == ""
        
        # Test case sensitivity (should return lowercase)
        assert file_utils.get_file_extension("file.PDF") == ".pdf"
        assert file_utils.get_file_extension("file.JPG") == ".jpg"

    def test_get_file_size(self, temp_dir):
        """Test getting the size of a file in bytes."""
        # Create a test file with known content
        test_file = temp_dir / "test_file.txt"
        content = b"Test content for file size calculation"
        test_file.write_bytes(content)
        
        # Test with file path
        assert file_utils.get_file_size(test_file) == len(content)
        assert file_utils.get_file_size(str(test_file)) == len(content)
        
        # Test with file-like object
        file_obj = io.BytesIO(content)
        assert file_utils.get_file_size(file_obj) == len(content)
        
        # Test that file position is preserved
        file_obj.seek(5)
        assert file_utils.get_file_size(file_obj) == len(content)
        assert file_obj.tell() == 5  # Position should be preserved
        
        # Test with unsupported type
        with pytest.raises(TypeError):
            file_utils.get_file_size(123)  # Integer is not supported

    def test_format_file_size(self):
        """Test formatting file size in a human-readable format."""
        # Test various file sizes
        assert file_utils.format_file_size(500) == "500 bytes"
        assert file_utils.format_file_size(1024) == "1.0 KB"
        assert file_utils.format_file_size(1536) == "1.5 KB"
        assert file_utils.format_file_size(1048576) == "1.0 MB"  # 1 MB
        assert file_utils.format_file_size(1572864) == "1.5 MB"  # 1.5 MB
        assert file_utils.format_file_size(1073741824) == "1.0 GB"  # 1 GB
        assert file_utils.format_file_size(1610612736) == "1.5 GB"  # 1.5 GB


class TestTemporaryFileManagement:
    """Tests for temporary file management functions."""

    def test_create_temp_file(self):
        """Test creating a temporary file for document processing."""
        # Test with default parameters
        temp_path, file_obj = file_utils.create_temp_file()
        try:
            assert os.path.exists(temp_path)
            assert temp_path.startswith(tempfile.gettempdir())
            assert os.path.basename(temp_path).startswith("ocr_")
            assert hasattr(file_obj, 'write')  # Should be a file object
            assert hasattr(file_obj, 'read')
        finally:
            file_obj.close()
            os.remove(temp_path)
        
        # Test with custom prefix and suffix
        temp_path, file_obj = file_utils.create_temp_file(prefix="test_", suffix=".pdf")
        try:
            assert os.path.exists(temp_path)
            assert os.path.basename(temp_path).startswith("test_")
            assert temp_path.endswith(".pdf")
        finally:
            file_obj.close()
            os.remove(temp_path)

    def test_create_temp_directory(self):
        """Test creating a temporary directory for document processing."""
        # Test with default prefix
        temp_dir = file_utils.create_temp_directory()
        try:
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            assert temp_dir.startswith(tempfile.gettempdir())
            assert os.path.basename(temp_dir).startswith("ocr_")
        finally:
            shutil.rmtree(temp_dir)
        
        # Test with custom prefix
        temp_dir = file_utils.create_temp_directory(prefix="test_")
        try:
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            assert os.path.basename(temp_dir).startswith("test_")
        finally:
            shutil.rmtree(temp_dir)

    def test_cleanup_temp_file(self):
        """Test cleaning up a temporary file after processing."""
        # Create a temporary file
        fd, temp_path = tempfile.mkstemp()
        os.close(fd)
        
        # Verify file exists
        assert os.path.exists(temp_path)
        
        # Clean up the file
        file_utils.cleanup_temp_file(temp_path)
        
        # Verify file no longer exists
        assert not os.path.exists(temp_path)
        
        # Test with non-existent file (should not raise exception)
        file_utils.cleanup_temp_file("non_existent_file.txt")
        
        # Test with exception during removal
        with patch('os.remove', side_effect=Exception("Test exception")):
            with patch('src.utils.file_utils.logger') as mock_logger:
                file_utils.cleanup_temp_file(temp_path)
                mock_logger.error.assert_called_once()

    def test_cleanup_temp_directory(self):
        """Test cleaning up a temporary directory after processing."""
        # Create a temporary directory
        temp_dir = tempfile.mkdtemp()
        
        # Verify directory exists
        assert os.path.exists(temp_dir)
        
        # Clean up the directory
        file_utils.cleanup_temp_directory(temp_dir)
        
        # Verify directory no longer exists
        assert not os.path.exists(temp_dir)
        
        # Test with non-existent directory (should not raise exception)
        file_utils.cleanup_temp_directory("non_existent_dir")
        
        # Test with exception during removal
        with patch('shutil.rmtree', side_effect=Exception("Test exception")):
            with patch('src.utils.file_utils.logger') as mock_logger:
                file_utils.cleanup_temp_directory(temp_dir)
                mock_logger.error.assert_called_once()


class TestFileConversionUtilities:
    """Tests for file conversion utility functions."""

    def test_bytes_to_file(self, temp_dir):
        """Test writing bytes data to a file."""
        # Create test data
        test_data = b"Test bytes data for file conversion"
        output_path = temp_dir / "output_file.txt"
        
        # Write bytes to file
        file_utils.bytes_to_file(test_data, str(output_path))
        
        # Verify file was created with correct content
        assert output_path.exists()
        assert output_path.read_bytes() == test_data

    def test_file_to_bytes(self, temp_dir):
        """Test reading a file into bytes."""
        # Create a test file with known content
        test_file = temp_dir / "test_file.txt"
        test_data = b"Test file content for bytes conversion"
        test_file.write_bytes(test_data)
        
        # Read file to bytes
        result = file_utils.file_to_bytes(test_file)
        assert result == test_data
        
        # Test with string path
        result = file_utils.file_to_bytes(str(test_file))
        assert result == test_data

    def test_stream_to_bytes(self):
        """Test reading a stream into bytes."""
        # Create a BytesIO object with test data
        test_data = b"Test stream content for bytes conversion"
        stream = io.BytesIO(test_data)
        
        # Read stream to bytes
        result = file_utils.stream_to_bytes(stream)
        assert result == test_data
        
        # Verify stream position is reset
        assert stream.tell() == 0
        
        # Test with stream at non-zero position
        stream.seek(5)
        result = file_utils.stream_to_bytes(stream)
        assert result == test_data
        assert stream.tell() == 5  # Position should be preserved

    def test_bytes_to_stream(self):
        """Test converting bytes to a file-like object (BytesIO)."""
        # Create test data
        test_data = b"Test bytes data for stream conversion"
        
        # Convert bytes to stream
        stream = file_utils.bytes_to_stream(test_data)
        
        # Verify stream contains correct data
        assert isinstance(stream, io.BytesIO)
        assert stream.getvalue() == test_data
        assert stream.tell() == 0  # Stream position should be at start


class TestDirectoryOperations:
    """Tests for directory operation functions."""

    def test_ensure_directory_exists(self, temp_dir):
        """Test ensuring that a directory exists, creating it if necessary."""
        # Test with non-existent directory
        new_dir = temp_dir / "new_directory"
        assert not new_dir.exists()
        
        file_utils.ensure_directory_exists(new_dir)
        assert new_dir.exists()
        assert new_dir.is_dir()
        
        # Test with existing directory (should not raise exception)
        file_utils.ensure_directory_exists(new_dir)
        assert new_dir.exists()
        
        # Test with string path
        another_dir = temp_dir / "another_directory"
        file_utils.ensure_directory_exists(str(another_dir))
        assert another_dir.exists()
        
        # Test with nested directory
        nested_dir = temp_dir / "parent" / "child" / "grandchild"
        file_utils.ensure_directory_exists(nested_dir)
        assert nested_dir.exists()


class TestS3Utilities:
    """Tests for S3-related utility functions."""

    def test_get_content_type_for_s3(self):
        """Test getting the content type (MIME type) for S3 storage based on file extension."""
        # Test with supported file types
        assert file_utils.get_content_type_for_s3("/path/to/file.pdf") == "application/pdf"
        assert file_utils.get_content_type_for_s3("file.jpg") == "image/jpeg"
        assert file_utils.get_content_type_for_s3("file.jpeg") == "image/jpeg"
        assert file_utils.get_content_type_for_s3("file.png") == "image/png"
        assert file_utils.get_content_type_for_s3("file.tiff") == "image/tiff"
        assert file_utils.get_content_type_for_s3("file.tif") == "image/tiff"
        
        # Test with unsupported file type (should return default)
        assert file_utils.get_content_type_for_s3("file.txt") == "application/octet-stream"
        assert file_utils.get_content_type_for_s3("file_without_extension") == "application/octet-stream"
        
        # Test with Path objects
        assert file_utils.get_content_type_for_s3(Path("/path/to/file.pdf")) == "application/pdf"
        assert file_utils.get_content_type_for_s3(Path("file.jpg")) == "image/jpeg"
        
        # Test case sensitivity (should handle uppercase extensions)
        assert file_utils.get_content_type_for_s3("file.PDF") == "application/pdf"
        assert file_utils.get_content_type_for_s3("file.JPG") == "image/jpeg"


class TestFilenameUtilities:
    """Tests for filename utility functions."""

    def test_get_safe_filename(self):
        """Test converting a filename to a safe version that can be used as a filename on any platform."""
        # Test with spaces
        assert file_utils.get_safe_filename("file with spaces.pdf") == "file_with_spaces.pdf"
        
        # Test with special characters
        assert file_utils.get_safe_filename("file*with?special<chars>.pdf") == "file_with_special_chars_.pdf"
        
        # Test with path separators
        assert file_utils.get_safe_filename("path/to/file.pdf") == "path_to_file.pdf"
        assert file_utils.get_safe_filename("path\\to\\file.pdf") == "path_to_file.pdf"
        
        # Test with Unicode characters
        assert file_utils.get_safe_filename("résumé.pdf") == "résumé.pdf"  # Unicode letters are preserved
        
        # Test with leading/trailing spaces
        assert file_utils.get_safe_filename(" leading_space.pdf ") == "_leading_space.pdf_"
        
        # Test with empty string
        assert file_utils.get_safe_filename("") == ""
        
        # Test with only special characters
        assert file_utils.get_safe_filename("!@#$%^&*()") == "__________"