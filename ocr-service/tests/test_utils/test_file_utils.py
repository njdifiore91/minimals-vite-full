#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the file_utils.py module.

This module contains tests for file operations, MIME type detection, content type validation,
file size calculation, and temporary file management to ensure proper document processing and storage.
"""

import os
import tempfile
import pytest
import shutil
import io
import math
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.utils import file_utils
from src.types.documents import DocumentType
from src.types.errors import ServiceError


class TestFileOperations:
    """Tests for basic file operations."""

    def test_get_file_size(self, sample_files):
        """Test getting file size from a file path."""
        # Test with a non-empty file
        pdf_path = sample_files["pdf"]
        size = file_utils.get_file_size(pdf_path)
        assert size > 0
        assert isinstance(size, int)

        # Test with an empty file
        empty_path = sample_files["empty"]
        size = file_utils.get_file_size(empty_path)
        assert size == 0

    def test_get_file_size_from_buffer(self, binary_content):
        """Test getting file size from a buffer."""
        # Test with non-empty buffer
        pdf_buffer = binary_content["pdf"]
        size = file_utils.get_file_size_from_buffer(pdf_buffer)
        assert size > 0
        assert isinstance(size, int)
        assert size == len(pdf_buffer)

        # Test with empty buffer
        empty_buffer = binary_content["empty"]
        size = file_utils.get_file_size_from_buffer(empty_buffer)
        assert size == 0

    def test_format_file_size(self):
        """Test formatting file size in human-readable format."""
        # Test bytes
        assert file_utils.format_file_size(0) == "0 bytes"
        assert file_utils.format_file_size(100) == "100 B"

        # Test kilobytes
        assert file_utils.format_file_size(1024) == "1 KB"
        assert file_utils.format_file_size(1536) == "1.5 KB"

        # Test megabytes
        assert file_utils.format_file_size(1048576) == "1 MB"
        assert file_utils.format_file_size(2097152) == "2 MB"

        # Test gigabytes
        assert file_utils.format_file_size(1073741824) == "1 GB"

        # Test with different decimal places
        assert file_utils.format_file_size(1234567, decimal_places=0) == "1 MB"
        assert file_utils.format_file_size(1234567, decimal_places=1) == "1.2 MB"
        assert file_utils.format_file_size(1234567, decimal_places=3) == "1.177 MB"

    def test_convert_size_to_bytes(self):
        """Test converting size from specific unit to bytes."""
        assert file_utils.convert_size_to_bytes(1, "B") == 1
        assert file_utils.convert_size_to_bytes(1, "KB") == 1024
        assert file_utils.convert_size_to_bytes(1, "MB") == 1048576
        assert file_utils.convert_size_to_bytes(1, "GB") == 1073741824
        assert file_utils.convert_size_to_bytes(1.5, "KB") == 1536

        # Test with invalid unit
        with pytest.raises(ValueError):
            file_utils.convert_size_to_bytes(1, "XB")

    def test_read_write_buffer_to_file(self, temp_dir, binary_content):
        """Test writing a buffer to a file and reading it back."""
        test_file_path = os.path.join(temp_dir, "test_buffer.pdf")
        test_content = binary_content["pdf"]

        # Write buffer to file
        file_utils.write_buffer_to_file(test_content, test_file_path)
        assert os.path.exists(test_file_path)
        assert os.path.getsize(test_file_path) == len(test_content)

        # Read file back to buffer
        read_content = file_utils.read_file_to_buffer(test_file_path)
        assert read_content == test_content

    def test_read_file_in_chunks(self, temp_dir, binary_content):
        """Test reading a file in chunks."""
        test_file_path = os.path.join(temp_dir, "test_chunks.pdf")
        test_content = binary_content["pdf"]

        # Write test content to file
        with open(test_file_path, "wb") as f:
            f.write(test_content)

        # Read file in chunks
        chunks = list(file_utils.read_file_in_chunks(test_file_path, chunk_size=10))
        assert len(chunks) > 0
        # Reconstruct the content from chunks
        reconstructed = b"".join(chunks)
        assert reconstructed == test_content

    def test_copy_file(self, temp_dir, sample_files):
        """Test copying a file from source to destination."""
        source_path = sample_files["pdf"]
        dest_path = os.path.join(temp_dir, "copied_file.pdf")

        file_utils.copy_file(source_path, dest_path)
        assert os.path.exists(dest_path)
        assert os.path.getsize(source_path) == os.path.getsize(dest_path)

        # Verify content is the same
        with open(source_path, "rb") as src, open(dest_path, "rb") as dst:
            assert src.read() == dst.read()

    def test_ensure_directory_exists(self, temp_dir):
        """Test ensuring a directory exists."""
        test_dir = os.path.join(temp_dir, "test_dir")
        assert not os.path.exists(test_dir)

        file_utils.ensure_directory_exists(test_dir)
        assert os.path.exists(test_dir)
        assert os.path.isdir(test_dir)

        # Test with existing directory (should not raise)
        file_utils.ensure_directory_exists(test_dir)
        assert os.path.exists(test_dir)

    def test_remove_file(self, temp_dir):
        """Test removing a file."""
        test_file = os.path.join(temp_dir, "test_remove.txt")
        with open(test_file, "w") as f:
            f.write("test content")

        assert os.path.exists(test_file)
        file_utils.remove_file(test_file)
        assert not os.path.exists(test_file)

        # Test with non-existent file (should not raise)
        file_utils.remove_file(test_file)

    def test_remove_directory(self, temp_dir):
        """Test removing a directory."""
        # Test with empty directory
        empty_dir = os.path.join(temp_dir, "empty_dir")
        os.makedirs(empty_dir)
        assert os.path.exists(empty_dir)

        file_utils.remove_directory(empty_dir, recursive=False)
        assert not os.path.exists(empty_dir)

        # Test with non-empty directory
        non_empty_dir = os.path.join(temp_dir, "non_empty_dir")
        os.makedirs(non_empty_dir)
        with open(os.path.join(non_empty_dir, "test.txt"), "w") as f:
            f.write("test content")

        # Should fail without recursive=True
        with pytest.raises(OSError):
            file_utils.remove_directory(non_empty_dir, recursive=False)

        # Should succeed with recursive=True
        file_utils.remove_directory(non_empty_dir, recursive=True)
        assert not os.path.exists(non_empty_dir)

        # Test with non-existent directory (should not raise)
        file_utils.remove_directory(non_empty_dir, recursive=True)

    def test_file_operation_decorator(self):
        """Test the file operation decorator for error handling."""
        # Create a function that will raise an exception
        @file_utils.file_operation_decorator
        def failing_function():
            raise IOError("Test error")

        # The decorator should catch the exception and raise a ServiceError
        with pytest.raises(ServiceError) as excinfo:
            failing_function()

        assert "Test error" in str(excinfo.value)

    def test_calculate_file_hash(self, sample_files):
        """Test calculating file hash."""
        pdf_path = sample_files["pdf"]

        # Test with different algorithms
        sha256_hash = file_utils.calculate_file_hash(pdf_path, algorithm="sha256")
        assert isinstance(sha256_hash, str)
        assert len(sha256_hash) == 64  # SHA-256 produces 64 hex characters

        md5_hash = file_utils.calculate_file_hash(pdf_path, algorithm="md5")
        assert isinstance(md5_hash, str)
        assert len(md5_hash) == 32  # MD5 produces 32 hex characters

        # Test with invalid algorithm
        with pytest.raises(ValueError):
            file_utils.calculate_file_hash(pdf_path, algorithm="invalid")

    def test_calculate_buffer_hash(self, binary_content):
        """Test calculating buffer hash."""
        pdf_buffer = binary_content["pdf"]

        # Test with different algorithms
        sha256_hash = file_utils.calculate_buffer_hash(pdf_buffer, algorithm="sha256")
        assert isinstance(sha256_hash, str)
        assert len(sha256_hash) == 64  # SHA-256 produces 64 hex characters

        md5_hash = file_utils.calculate_buffer_hash(pdf_buffer, algorithm="md5")
        assert isinstance(md5_hash, str)
        assert len(md5_hash) == 32  # MD5 produces 32 hex characters

        # Test with invalid algorithm
        with pytest.raises(ValueError):
            file_utils.calculate_buffer_hash(pdf_buffer, algorithm="invalid")

    def test_buffer_to_stream_and_back(self, binary_content):
        """Test converting buffer to stream and back."""
        pdf_buffer = binary_content["pdf"]

        # Convert buffer to stream
        stream = file_utils.buffer_to_stream(pdf_buffer)
        assert isinstance(stream, io.BytesIO)

        # Convert stream back to buffer
        buffer = file_utils.stream_to_buffer(stream)
        assert buffer == pdf_buffer

        # Test with stream position not at start
        stream = file_utils.buffer_to_stream(pdf_buffer)
        stream.seek(10)  # Move position to 10
        buffer = file_utils.stream_to_buffer(stream)
        assert buffer == pdf_buffer
        assert stream.tell() == 10  # Position should be preserved


class TestMimeTypeDetection:
    """Tests for MIME type detection and validation."""

    def test_get_mime_type(self, sample_files):
        """Test detecting MIME type from file path."""
        # Test with PDF file
        pdf_path = sample_files["pdf"]
        mime_type = file_utils.get_mime_type(pdf_path)
        assert mime_type == "application/pdf"

        # Test with TIFF file
        tiff_path = sample_files["tiff"]
        mime_type = file_utils.get_mime_type(tiff_path)
        assert mime_type == "image/tiff"

        # Test with PNG file
        png_path = sample_files["png"]
        mime_type = file_utils.get_mime_type(png_path)
        assert mime_type == "image/png"

        # Test with JPEG file
        jpeg_path = sample_files["jpeg"]
        mime_type = file_utils.get_mime_type(jpeg_path)
        assert mime_type == "image/jpeg"

        # Test with text file (unsupported type)
        text_path = sample_files["text"]
        mime_type = file_utils.get_mime_type(text_path)
        assert mime_type not in file_utils.SUPPORTED_MIME_TYPES

    def test_get_mime_type_from_buffer(self, binary_content):
        """Test detecting MIME type from buffer."""
        # Mock python-magic for consistent testing
        with patch("importlib.import_module") as mock_import:
            # Configure the mock to simulate python-magic being available
            mock_magic = MagicMock()
            mock_magic_instance = MagicMock()
            mock_magic.Magic.return_value = mock_magic_instance
            mock_import.return_value = mock_magic

            # Test with PDF buffer
            pdf_buffer = binary_content["pdf"]
            mock_magic_instance.from_buffer.return_value = "application/pdf"
            mime_type = file_utils.get_mime_type_from_buffer(pdf_buffer)
            assert mime_type == "application/pdf"

            # Test with TIFF buffer
            tiff_buffer = binary_content["tiff"]
            mock_magic_instance.from_buffer.return_value = "image/tiff"
            mime_type = file_utils.get_mime_type_from_buffer(tiff_buffer)
            assert mime_type == "image/tiff"

        # Test fallback when python-magic is not available
        with patch("importlib.import_module", side_effect=ImportError):
            mime_type = file_utils.get_mime_type_from_buffer(pdf_buffer)
            assert mime_type == file_utils.DEFAULT_MIME_TYPE

    def test_get_mime_type_from_filename(self):
        """Test detecting MIME type from filename."""
        # Test with PDF filename
        mime_type = file_utils.get_mime_type_from_filename("document.pdf")
        assert mime_type == "application/pdf"

        # Test with TIFF filename
        mime_type = file_utils.get_mime_type_from_filename("image.tiff")
        assert mime_type == "image/tiff"

        # Test with PNG filename
        mime_type = file_utils.get_mime_type_from_filename("image.png")
        assert mime_type == "image/png"

        # Test with JPEG filename
        mime_type = file_utils.get_mime_type_from_filename("image.jpg")
        assert mime_type == "image/jpeg"

        # Test with unsupported extension
        mime_type = file_utils.get_mime_type_from_filename("document.docx")
        assert mime_type not in file_utils.SUPPORTED_MIME_TYPES

        # Test with no extension
        mime_type = file_utils.get_mime_type_from_filename("document")
        assert mime_type == file_utils.DEFAULT_MIME_TYPE

    def test_is_supported_mime_type(self):
        """Test checking if MIME type is supported."""
        # Test with supported MIME types
        assert file_utils.is_supported_mime_type("application/pdf")
        assert file_utils.is_supported_mime_type("image/tiff")
        assert file_utils.is_supported_mime_type("image/jpeg")
        assert file_utils.is_supported_mime_type("image/png")

        # Test with unsupported MIME types
        assert not file_utils.is_supported_mime_type("application/msword")
        assert not file_utils.is_supported_mime_type("text/plain")
        assert not file_utils.is_supported_mime_type("application/zip")

    def test_is_supported_file_extension(self):
        """Test checking if file extension is supported."""
        # Test with supported extensions
        assert file_utils.is_supported_file_extension("document.pdf")
        assert file_utils.is_supported_file_extension("image.tiff")
        assert file_utils.is_supported_file_extension("image.tif")
        assert file_utils.is_supported_file_extension("image.jpg")
        assert file_utils.is_supported_file_extension("image.jpeg")
        assert file_utils.is_supported_file_extension("image.png")

        # Test with unsupported extensions
        assert not file_utils.is_supported_file_extension("document.docx")
        assert not file_utils.is_supported_file_extension("document.txt")
        assert not file_utils.is_supported_file_extension("archive.zip")

        # Test with no extension
        assert not file_utils.is_supported_file_extension("document")

    def test_get_file_extension(self):
        """Test getting file extension from file path."""
        assert file_utils.get_file_extension("document.pdf") == ".pdf"
        assert file_utils.get_file_extension("image.tiff") == ".tiff"
        assert file_utils.get_file_extension("image.jpg") == ".jpg"
        assert file_utils.get_file_extension("path/to/image.png") == ".png"
        assert file_utils.get_file_extension("document") == ""

    def test_get_file_extension_from_mime_type(self):
        """Test getting file extension from MIME type."""
        assert file_utils.get_file_extension_from_mime_type("application/pdf") == ".pdf"
        assert file_utils.get_file_extension_from_mime_type("image/tiff") == ".tiff"
        assert file_utils.get_file_extension_from_mime_type("image/jpeg") == ".jpg"
        assert file_utils.get_file_extension_from_mime_type("image/png") == ".png"

        # Test with unsupported MIME type
        assert file_utils.get_file_extension_from_mime_type("application/msword") is None


class TestDocumentValidation:
    """Tests for document validation functions."""

    def test_is_valid_document_for_ocr(self, sample_files):
        """Test checking if a document is valid for OCR processing."""
        # Test with supported document types
        assert file_utils.is_valid_document_for_ocr(sample_files["pdf"])
        assert file_utils.is_valid_document_for_ocr(sample_files["tiff"])
        assert file_utils.is_valid_document_for_ocr(sample_files["png"])
        assert file_utils.is_valid_document_for_ocr(sample_files["jpeg"])

        # Test with unsupported document type
        assert not file_utils.is_valid_document_for_ocr(sample_files["text"])

        # Test with OCR processing type
        assert file_utils.is_valid_document_for_ocr(sample_files["pdf"], ocr_processing_type="TYPED")
        assert file_utils.is_valid_document_for_ocr(sample_files["tiff"], ocr_processing_type="HANDWRITTEN")
        assert file_utils.is_valid_document_for_ocr(sample_files["png"], ocr_processing_type="HYBRID")

        # Test with invalid OCR processing type
        assert not file_utils.is_valid_document_for_ocr(sample_files["pdf"], ocr_processing_type="INVALID")

    def test_is_valid_document_for_type(self, sample_files):
        """Test checking if a document is valid for a specific document type."""
        # Test with valid document types
        assert file_utils.is_valid_document_for_type(sample_files["pdf"], DocumentType.APPLICATION.value)
        assert file_utils.is_valid_document_for_type(sample_files["tiff"], DocumentType.TAX_RETURN.value)
        assert file_utils.is_valid_document_for_type(sample_files["png"], DocumentType.BANK_STATEMENT.value)
        assert file_utils.is_valid_document_for_type(sample_files["jpeg"], DocumentType.PAY_STUB.value)

        # Test with invalid document type
        assert not file_utils.is_valid_document_for_type(sample_files["text"], DocumentType.APPLICATION.value)

        # Test with invalid document type string
        assert not file_utils.is_valid_document_for_type(sample_files["pdf"], "INVALID_TYPE")

    def test_create_document_metadata(self, sample_files):
        """Test creating document metadata for a file."""
        # Test with PDF file
        metadata = file_utils.create_document_metadata(sample_files["pdf"])
        assert metadata["filename"] == os.path.basename(sample_files["pdf"])
        assert metadata["size"] > 0
        assert metadata["mime_type"] == "application/pdf"
        assert "id" in metadata
        assert "checksum" in metadata

        # Test with document type
        metadata = file_utils.create_document_metadata(sample_files["pdf"], DocumentType.APPLICATION.value)
        assert metadata["filename"] == os.path.basename(sample_files["pdf"])

    @patch("src.utils.file_utils.get_document_page_count")
    def test_get_document_page_count(self, mock_get_page_count, sample_files):
        """Test getting document page count."""
        # Mock the page count for PDF
        mock_get_page_count.return_value = 5
        page_count = file_utils.get_document_page_count(sample_files["pdf"])
        assert page_count == 5

        # Test with PyPDF2 available (mocked)
        with patch("importlib.import_module") as mock_import:
            mock_pdf_reader = MagicMock()
            mock_pdf_reader.pages = [1, 2, 3]  # 3 pages
            mock_pypdf2 = MagicMock()
            mock_pypdf2.PdfReader.return_value = mock_pdf_reader
            mock_import.return_value = mock_pypdf2

            # Reset the mock to test our implementation
            mock_get_page_count.reset_mock()
            mock_get_page_count.side_effect = lambda x: file_utils.get_document_page_count(x)

            # Test with PDF file
            with patch("src.utils.file_utils.get_mime_type", return_value="application/pdf"):
                page_count = file_utils.get_document_page_count(sample_files["pdf"])
                assert page_count == 3

        # Test with PIL available for TIFF (mocked)
        with patch("importlib.import_module") as mock_import:
            mock_image = MagicMock()
            # Configure the seek method to raise EOFError after 4 calls (4 pages)
            mock_image.tell.side_effect = [0, 1, 2, 3]
            mock_image.seek.side_effect = [None, None, None, EOFError()]
            mock_pil = MagicMock()
            mock_pil.Image.open.return_value.__enter__.return_value = mock_image
            mock_import.return_value = mock_pil

            # Test with TIFF file
            with patch("src.utils.file_utils.get_mime_type", return_value="image/tiff"):
                page_count = file_utils.get_document_page_count(sample_files["tiff"])
                assert page_count == 4

        # Test with JPEG file (should be 1 page)
        with patch("src.utils.file_utils.get_mime_type", return_value="image/jpeg"):
            page_count = file_utils.get_document_page_count(sample_files["jpeg"])
            assert page_count == 1

        # Test with unsupported file type
        with patch("src.utils.file_utils.get_mime_type", return_value="text/plain"):
            page_count = file_utils.get_document_page_count(sample_files["text"])
            assert page_count is None


class TestTempFileManagement:
    """Tests for temporary file management."""

    def test_create_temp_file(self):
        """Test creating a temporary file."""
        path, file_obj = file_utils.create_temp_file(suffix=".pdf")
        try:
            assert os.path.exists(path)
            assert path.endswith(".pdf")
            assert file_obj.mode == "wb"
            # Write some data to the file
            file_obj.write(b"test content")
            file_obj.close()
            # Verify the data was written
            with open(path, "rb") as f:
                assert f.read() == b"test content"
        finally:
            # Clean up
            if os.path.exists(path):
                os.remove(path)

    def test_create_named_temp_file(self):
        """Test creating a named temporary file."""
        temp_file = file_utils.create_named_temp_file(suffix=".pdf")
        try:
            assert os.path.exists(temp_file.name)
            assert temp_file.name.endswith(".pdf")
            # Write some data to the file
            temp_file.write(b"test content")
            temp_file.flush()
            # Verify the data was written
            with open(temp_file.name, "rb") as f:
                assert f.read() == b"test content"
        finally:
            # Clean up
            temp_file.close()

    def test_create_temp_directory(self):
        """Test creating a temporary directory."""
        temp_dir = file_utils.create_temp_directory()
        try:
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)
            # Create a file in the directory
            test_file = os.path.join(temp_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test content")
            assert os.path.exists(test_file)
        finally:
            # Clean up
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

    def test_temp_file_manager(self):
        """Test the TempFileManager context manager."""
        with file_utils.TempFileManager(suffix=".pdf") as manager:
            # Create a temp file with content
            temp_file = manager.create_temp_file(content=b"test content")
            assert os.path.exists(temp_file)
            assert os.path.isfile(temp_file)
            with open(temp_file, "rb") as f:
                assert f.read() == b"test content"

            # Create a temp directory
            temp_dir = manager.create_temp_directory()
            assert os.path.exists(temp_dir)
            assert os.path.isdir(temp_dir)

            # Remember paths for checking cleanup
            temp_file_path = temp_file
            temp_dir_path = temp_dir

        # After context manager exits, files should be cleaned up
        assert not os.path.exists(temp_file_path)
        assert not os.path.exists(temp_dir_path)

    def test_spooled_temp_file_manager(self):
        """Test the SpooledTempFileManager context manager."""
        with file_utils.SpooledTempFileManager(max_size=1024) as manager:
            # Create a spooled temp file
            temp_file = manager.create_spooled_temp_file()
            assert temp_file is not None

            # Write data below the spooling threshold
            temp_file.write(b"small content")
            temp_file.flush()
            assert not temp_file._rolled  # Should not have rolled to disk

            # Write data above the spooling threshold
            temp_file.write(b"x" * 1024)
            temp_file.flush()
            assert temp_file._rolled  # Should have rolled to disk

        # After context manager exits, files should be closed
        assert temp_file.closed


class TestS3Integration:
    """Tests for S3 integration functions."""

    def test_create_s3_key_for_document(self):
        """Test creating an S3 key for storing a document."""
        # Test with PDF file
        key = file_utils.create_s3_key_for_document(
            "doc-123", DocumentType.APPLICATION.value, "application.pdf"
        )
        assert key == "documents/application/doc-123.pdf"

        # Test with TIFF file
        key = file_utils.create_s3_key_for_document(
            "doc-456", DocumentType.TAX_RETURN.value, "tax_return.tiff"
        )
        assert key == "documents/tax_return/doc-456.tiff"

    def test_create_s3_key_for_extracted_data(self):
        """Test creating an S3 key for storing extracted data."""
        # Test with application document
        key = file_utils.create_s3_key_for_extracted_data(
            "doc-123", DocumentType.APPLICATION.value
        )
        assert key == "extracted/application/doc-123.json"

        # Test with tax return document
        key = file_utils.create_s3_key_for_extracted_data(
            "doc-456", DocumentType.TAX_RETURN.value
        )
        assert key == "extracted/tax_return/doc-456.json"


class TestDocumentProcessing:
    """Tests for document processing functions."""

    @patch("src.utils.file_utils.split_pdf_into_pages")
    def test_split_pdf_into_pages(self, mock_split, temp_dir):
        """Test splitting a PDF document into individual pages."""
        # Mock the PyPDF2 import and functionality
        mock_split.return_value = [
            os.path.join(temp_dir, "page_1.pdf"),
            os.path.join(temp_dir, "page_2.pdf"),
            os.path.join(temp_dir, "page_3.pdf"),
        ]

        # Test splitting a PDF
        pages = file_utils.split_pdf_into_pages("test.pdf", temp_dir)
        assert len(pages) == 3
        assert all(page.endswith(".pdf") for page in pages)

        # Test with ImportError
        mock_split.side_effect = ImportError("PyPDF2 not available")
        with pytest.raises(ServiceError) as excinfo:
            file_utils.split_pdf_into_pages("test.pdf", temp_dir)
        assert "PyPDF2 not available" in str(excinfo.value)

        # Test with other error
        mock_split.side_effect = Exception("Error splitting PDF")
        with pytest.raises(ServiceError) as excinfo:
            file_utils.split_pdf_into_pages("test.pdf", temp_dir)
        assert "Error splitting PDF" in str(excinfo.value)

    @patch("src.utils.file_utils.extract_images_from_pdf")
    def test_extract_images_from_pdf(self, mock_extract, temp_dir):
        """Test extracting images from a PDF document."""
        # Mock the PyMuPDF import and functionality
        mock_extract.return_value = [
            os.path.join(temp_dir, "page_1_img_1.png"),
            os.path.join(temp_dir, "page_1_img_2.jpg"),
            os.path.join(temp_dir, "page_2_img_1.png"),
        ]

        # Test extracting images
        images = file_utils.extract_images_from_pdf("test.pdf", temp_dir)
        assert len(images) == 3
        assert any(image.endswith(".png") for image in images)
        assert any(image.endswith(".jpg") for image in images)

        # Test with ImportError
        mock_extract.side_effect = ImportError("PyMuPDF not available")
        with pytest.raises(ServiceError) as excinfo:
            file_utils.extract_images_from_pdf("test.pdf", temp_dir)
        assert "PyMuPDF not available" in str(excinfo.value)

        # Test with other error
        mock_extract.side_effect = Exception("Error extracting images")
        with pytest.raises(ServiceError) as excinfo:
            file_utils.extract_images_from_pdf("test.pdf", temp_dir)
        assert "Error extracting images" in str(excinfo.value)

    @patch("src.utils.file_utils.convert_pdf_to_images")
    def test_convert_pdf_to_images(self, mock_convert, temp_dir):
        """Test converting a PDF document to images."""
        # Mock the pdf2image import and functionality
        mock_convert.return_value = [
            os.path.join(temp_dir, "page_1.png"),
            os.path.join(temp_dir, "page_2.png"),
            os.path.join(temp_dir, "page_3.png"),
        ]

        # Test converting PDF to images
        images = file_utils.convert_pdf_to_images("test.pdf", temp_dir)
        assert len(images) == 3
        assert all(image.endswith(".png") for image in images)

        # Test with ImportError
        mock_convert.side_effect = ImportError("pdf2image not available")
        with pytest.raises(ServiceError) as excinfo:
            file_utils.convert_pdf_to_images("test.pdf", temp_dir)
        assert "pdf2image not available" in str(excinfo.value)

        # Test with other error
        mock_convert.side_effect = Exception("Error converting PDF")
        with pytest.raises(ServiceError) as excinfo:
            file_utils.convert_pdf_to_images("test.pdf", temp_dir)
        assert "Error converting PDF" in str(excinfo.value)

    @patch("src.utils.file_utils.prepare_document_for_ocr")
    def test_prepare_document_for_ocr(self, mock_prepare, temp_dir, sample_files):
        """Test preparing a document for OCR processing."""
        # Mock the preparation function
        mock_prepare.return_value = [
            os.path.join(temp_dir, "prepared_1.png"),
            os.path.join(temp_dir, "prepared_2.png"),
        ]

        # Test preparing a document for OCR
        prepared_files = file_utils.prepare_document_for_ocr(sample_files["pdf"], temp_dir)
        assert len(prepared_files) == 2
        assert all(os.path.basename(f).startswith("prepared_") for f in prepared_files)

        # Test with PDF file (mocked conversion)
        with patch("src.utils.file_utils.get_mime_type", return_value="application/pdf"):
            with patch("src.utils.file_utils.convert_pdf_to_images", return_value=["img1.png", "img2.png"]):
                prepared_files = file_utils.prepare_document_for_ocr(sample_files["pdf"], temp_dir)
                assert len(prepared_files) == 2

            # Test with conversion error, falling back to splitting
            with patch("src.utils.file_utils.convert_pdf_to_images", side_effect=Exception("Conversion error")), \
                 patch("src.utils.file_utils.split_pdf_into_pages", return_value=["page1.pdf", "page2.pdf"]):
                prepared_files = file_utils.prepare_document_for_ocr(sample_files["pdf"], temp_dir)
                assert len(prepared_files) == 2

        # Test with multi-page TIFF file (mocked)
        with patch("src.utils.file_utils.get_mime_type", return_value="image/tiff"):
            with patch("importlib.import_module") as mock_import:
                # Mock PIL.Image for TIFF handling
                mock_image = MagicMock()
                # Configure to simulate a 2-page TIFF
                mock_image.tell.side_effect = [0, 1]
                mock_image.seek.side_effect = [None, EOFError()]
                mock_pil = MagicMock()
                mock_pil.Image.open.return_value.__enter__.return_value = mock_image
                mock_import.return_value = mock_pil

                # Should try to split the TIFF
                prepared_files = file_utils.prepare_document_for_ocr(sample_files["tiff"], temp_dir)
                # Since we're mocking, we don't actually get real files back

            # Test with PIL import error
            with patch("importlib.import_module", side_effect=ImportError()), \
                 patch("src.utils.file_utils.copy_file") as mock_copy:
                file_utils.prepare_document_for_ocr(sample_files["tiff"], temp_dir)
                # Should fall back to copying the file
                assert mock_copy.called

        # Test with JPEG file (should just copy)
        with patch("src.utils.file_utils.get_mime_type", return_value="image/jpeg"), \
             patch("src.utils.file_utils.copy_file") as mock_copy:
            file_utils.prepare_document_for_ocr(sample_files["jpeg"], temp_dir)
            assert mock_copy.called

    def test_save_and_load_json_data(self, temp_dir):
        """Test saving and loading JSON data."""
        # Test data
        test_data = {
            "document_id": "doc-123",
            "fields": {
                "name": "John Doe",
                "address": "123 Main St",
                "phone": "555-1234"
            },
            "confidence": 0.95
        }

        # Save JSON data
        json_path = os.path.join(temp_dir, "test_data.json")
        file_utils.save_extracted_data_as_json(test_data, json_path)
        assert os.path.exists(json_path)

        # Load JSON data
        loaded_data = file_utils.load_json_data(json_path)
        assert loaded_data == test_data


class TestFileMetadata:
    """Tests for file metadata functions."""

    def test_get_file_metadata(self, sample_files):
        """Test getting metadata for a file."""
        # Test with PDF file
        metadata = file_utils.get_file_metadata(sample_files["pdf"])
        assert metadata["file_name"] == os.path.basename(sample_files["pdf"])
        assert metadata["file_path"] == sample_files["pdf"]
        assert metadata["file_size"] > 0
        assert metadata["mime_type"] == "application/pdf"
        assert metadata["file_extension"] == ".pdf"
        assert "created_at" in metadata
        assert "modified_at" in metadata
        assert "accessed_at" in metadata
        assert "file_size_formatted" in metadata

        # Test with empty file
        metadata = file_utils.get_file_metadata(sample_files["empty"])
        assert metadata["file_size"] == 0
        assert metadata["file_size_formatted"] == "0 bytes"