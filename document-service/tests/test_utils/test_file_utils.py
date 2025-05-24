#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for file_utils.py in the Document Service.

This module contains tests for the file handling utilities, including:
- MIME type detection and validation
- File size calculation and formatting
- Temporary file management
- Buffer handling and conversion
- Content type mapping for document formats
- File hashing and unique filename generation
"""

import os
import io
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path

# Import the module to test
from document_service.src.utils import file_utils


class TestFileUtils(unittest.TestCase):
    """Test cases for file_utils.py"""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Create a temporary directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create sample test files
        self.pdf_content = b'%PDF-1.5\n%Test PDF content'
        self.pdf_file = os.path.join(self.test_dir, 'test.pdf')
        with open(self.pdf_file, 'wb') as f:
            f.write(self.pdf_content)
            
        self.txt_content = b'This is a plain text file.'
        self.txt_file = os.path.join(self.test_dir, 'test.txt')
        with open(self.txt_file, 'wb') as f:
            f.write(self.txt_content)
            
        self.jpg_content = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06'
        self.jpg_file = os.path.join(self.test_dir, 'test.jpg')
        with open(self.jpg_file, 'wb') as f:
            f.write(self.jpg_content)
            
        # Create a large file that exceeds the maximum size
        self.large_content = b'X' * (file_utils.MAX_FILE_SIZE + 1000)
        self.large_file = os.path.join(self.test_dir, 'large_file.txt')
        with open(self.large_file, 'wb') as f:
            f.write(self.large_content)

    def tearDown(self):
        """Tear down test fixtures after each test method."""
        # Remove the temporary directory and its contents
        shutil.rmtree(self.test_dir)

    def test_get_mime_type_from_file_path(self):
        """Test get_mime_type with a file path."""
        # Mock the magic.from_file function to return a known MIME type
        with mock.patch('magic.from_file', return_value='application/pdf'):
            mime_type = file_utils.get_mime_type(self.pdf_file)
            self.assertEqual(mime_type, 'application/pdf')

    def test_get_mime_type_from_bytes(self):
        """Test get_mime_type with a bytes object."""
        # Mock the magic.from_buffer function to return a known MIME type
        with mock.patch('magic.from_buffer', return_value='application/pdf'):
            mime_type = file_utils.get_mime_type(self.pdf_content)
            self.assertEqual(mime_type, 'application/pdf')

    def test_get_mime_type_from_file_object(self):
        """Test get_mime_type with a file-like object."""
        # Mock the magic.from_buffer function to return a known MIME type
        with mock.patch('magic.from_buffer', return_value='application/pdf'):
            file_obj = io.BytesIO(self.pdf_content)
            mime_type = file_utils.get_mime_type(file_obj)
            self.assertEqual(mime_type, 'application/pdf')
            # Verify that the file position was reset
            self.assertEqual(file_obj.tell(), 0)

    def test_get_mime_type_error(self):
        """Test get_mime_type with an error condition."""
        # Mock the magic.from_file function to raise an exception
        with mock.patch('magic.from_file', side_effect=Exception('Test error')):
            with self.assertRaises(ValueError):
                file_utils.get_mime_type(self.pdf_file)

    def test_is_supported_mime_type(self):
        """Test is_supported_mime_type function."""
        # Test with supported MIME types
        self.assertTrue(file_utils.is_supported_mime_type('application/pdf'))
        self.assertTrue(file_utils.is_supported_mime_type('image/jpeg'))
        self.assertTrue(file_utils.is_supported_mime_type('image/png'))
        
        # Test with unsupported MIME types
        self.assertFalse(file_utils.is_supported_mime_type('application/x-executable'))
        self.assertFalse(file_utils.is_supported_mime_type('video/mp4'))
        self.assertFalse(file_utils.is_supported_mime_type('audio/mpeg'))

    def test_get_extension_for_mime_type(self):
        """Test get_extension_for_mime_type function."""
        # Test with supported MIME types
        self.assertEqual(file_utils.get_extension_for_mime_type('application/pdf'), '.pdf')
        self.assertEqual(file_utils.get_extension_for_mime_type('image/jpeg'), '.jpg')
        self.assertEqual(file_utils.get_extension_for_mime_type('image/png'), '.png')
        
        # Test with unsupported MIME types
        self.assertIsNone(file_utils.get_extension_for_mime_type('application/x-executable'))
        self.assertIsNone(file_utils.get_extension_for_mime_type('video/mp4'))

    def test_get_mime_type_for_extension(self):
        """Test get_mime_type_for_extension function."""
        # Test with supported extensions
        self.assertEqual(file_utils.get_mime_type_for_extension('.pdf'), 'application/pdf')
        self.assertEqual(file_utils.get_mime_type_for_extension('pdf'), 'application/pdf')
        self.assertEqual(file_utils.get_mime_type_for_extension('.jpg'), 'image/jpeg')
        self.assertEqual(file_utils.get_mime_type_for_extension('jpg'), 'image/jpeg')
        
        # Test with unsupported extensions
        self.assertIsNone(file_utils.get_mime_type_for_extension('.exe'))
        self.assertIsNone(file_utils.get_mime_type_for_extension('mp4'))

    def test_validate_file_type_valid(self):
        """Test validate_file_type with valid file types."""
        # Mock get_mime_type to return a supported MIME type
        with mock.patch('document_service.src.utils.file_utils.get_mime_type', return_value='application/pdf'):
            is_valid, mime_type = file_utils.validate_file_type(self.pdf_file)
            self.assertTrue(is_valid)
            self.assertEqual(mime_type, 'application/pdf')

    def test_validate_file_type_invalid(self):
        """Test validate_file_type with invalid file types."""
        # Mock get_mime_type to return an unsupported MIME type
        with mock.patch('document_service.src.utils.file_utils.get_mime_type', return_value='application/x-executable'):
            is_valid, mime_type = file_utils.validate_file_type(self.pdf_file)
            self.assertFalse(is_valid)
            self.assertEqual(mime_type, 'application/x-executable')

    def test_validate_file_type_error(self):
        """Test validate_file_type with an error condition."""
        # Mock get_mime_type to raise a ValueError
        with mock.patch('document_service.src.utils.file_utils.get_mime_type', side_effect=ValueError('Test error')):
            is_valid, mime_type = file_utils.validate_file_type(self.pdf_file)
            self.assertFalse(is_valid)
            self.assertEqual(mime_type, "")

    def test_calculate_file_size_from_path(self):
        """Test calculate_file_size with a file path."""
        # Create a file with known size
        test_content = b'X' * 1024  # 1KB
        test_file = os.path.join(self.test_dir, 'size_test.txt')
        with open(test_file, 'wb') as f:
            f.write(test_content)
            
        size = file_utils.calculate_file_size(test_file)
        self.assertEqual(size, 1024)

    def test_calculate_file_size_from_bytes(self):
        """Test calculate_file_size with a bytes object."""
        test_content = b'X' * 2048  # 2KB
        size = file_utils.calculate_file_size(test_content)
        self.assertEqual(size, 2048)

    def test_calculate_file_size_from_file_object(self):
        """Test calculate_file_size with a file-like object."""
        test_content = b'X' * 4096  # 4KB
        file_obj = io.BytesIO(test_content)
        size = file_utils.calculate_file_size(file_obj)
        self.assertEqual(size, 4096)
        # Verify that the file position was reset
        self.assertEqual(file_obj.tell(), 0)

    def test_calculate_file_size_error(self):
        """Test calculate_file_size with an error condition."""
        # Test with a non-existent file
        non_existent_file = os.path.join(self.test_dir, 'non_existent.txt')
        with self.assertRaises(ValueError):
            file_utils.calculate_file_size(non_existent_file)

    def test_format_file_size(self):
        """Test format_file_size function."""
        # Test with various file sizes
        self.assertEqual(file_utils.format_file_size(0), "0 bytes")
        self.assertEqual(file_utils.format_file_size(1023), "1023.00 bytes")
        self.assertEqual(file_utils.format_file_size(1024), "1.00 KB")
        self.assertEqual(file_utils.format_file_size(1536), "1.50 KB")
        self.assertEqual(file_utils.format_file_size(1048576), "1.00 MB")
        self.assertEqual(file_utils.format_file_size(1073741824), "1.00 GB")

    def test_is_file_size_valid(self):
        """Test is_file_size_valid function."""
        # Test with a file smaller than the maximum size
        small_content = b'X' * 1024  # 1KB
        small_file = os.path.join(self.test_dir, 'small_file.txt')
        with open(small_file, 'wb') as f:
            f.write(small_content)
            
        self.assertTrue(file_utils.is_file_size_valid(small_file))
        self.assertTrue(file_utils.is_file_size_valid(small_content))
        
        # Test with a file larger than the maximum size
        self.assertFalse(file_utils.is_file_size_valid(self.large_file))
        self.assertFalse(file_utils.is_file_size_valid(self.large_content))

    def test_is_file_size_valid_error(self):
        """Test is_file_size_valid with an error condition."""
        # Mock calculate_file_size to raise a ValueError
        with mock.patch('document_service.src.utils.file_utils.calculate_file_size', side_effect=ValueError('Test error')):
            self.assertFalse(file_utils.is_file_size_valid(self.pdf_file))

    def test_calculate_file_hash(self):
        """Test calculate_file_hash function."""
        # Create a file with known content
        test_content = b'test content for hashing'
        test_file = os.path.join(self.test_dir, 'hash_test.txt')
        with open(test_file, 'wb') as f:
            f.write(test_content)
            
        # Calculate expected hash
        import hashlib
        expected_hash = hashlib.sha256(test_content).hexdigest()
        
        # Test with file path
        hash_from_path = file_utils.calculate_file_hash(test_file)
        self.assertEqual(hash_from_path, expected_hash)
        
        # Test with bytes
        hash_from_bytes = file_utils.calculate_file_hash(test_content)
        self.assertEqual(hash_from_bytes, expected_hash)
        
        # Test with file-like object
        file_obj = io.BytesIO(test_content)
        hash_from_obj = file_utils.calculate_file_hash(file_obj)
        self.assertEqual(hash_from_obj, expected_hash)
        # Verify that the file position was reset
        self.assertEqual(file_obj.tell(), 0)
        
        # Test with different algorithm
        md5_hash = file_utils.calculate_file_hash(test_content, algorithm='md5')
        expected_md5 = hashlib.md5(test_content).hexdigest()
        self.assertEqual(md5_hash, expected_md5)

    def test_calculate_file_hash_error(self):
        """Test calculate_file_hash with an error condition."""
        # Test with a non-existent file
        non_existent_file = os.path.join(self.test_dir, 'non_existent.txt')
        with self.assertRaises(ValueError):
            file_utils.calculate_file_hash(non_existent_file)
            
        # Test with an invalid algorithm
        with self.assertRaises(ValueError):
            file_utils.calculate_file_hash(self.pdf_content, algorithm='invalid_algorithm')

    def test_create_temp_file(self):
        """Test create_temp_file context manager."""
        # Test with string content
        with file_utils.create_temp_file("test content") as temp_file:
            self.assertTrue(os.path.exists(temp_file))
            with open(temp_file, 'r') as f:
                content = f.read()
                self.assertEqual(content, "test content")
                
        # Verify that the file was deleted after the context
        self.assertFalse(os.path.exists(temp_file))
        
        # Test with bytes content and suffix
        with file_utils.create_temp_file(b"test bytes", suffix=".txt") as temp_file:
            self.assertTrue(os.path.exists(temp_file))
            self.assertTrue(temp_file.endswith(".txt"))
            with open(temp_file, 'rb') as f:
                content = f.read()
                self.assertEqual(content, b"test bytes")
                
        # Verify that the file was deleted after the context
        self.assertFalse(os.path.exists(temp_file))

    def test_create_temp_directory(self):
        """Test create_temp_directory context manager."""
        with file_utils.create_temp_directory() as temp_dir:
            self.assertTrue(os.path.exists(temp_dir))
            self.assertTrue(os.path.isdir(temp_dir))
            
            # Create a file in the temporary directory
            test_file = os.path.join(temp_dir, 'test.txt')
            with open(test_file, 'w') as f:
                f.write("test content")
                
            self.assertTrue(os.path.exists(test_file))
            
        # Verify that the directory and its contents were deleted after the context
        self.assertFalse(os.path.exists(temp_dir))

    def test_ensure_directory_exists(self):
        """Test ensure_directory_exists function."""
        # Test with a non-existent directory
        test_dir = os.path.join(self.test_dir, 'new_directory')
        self.assertFalse(os.path.exists(test_dir))
        
        file_utils.ensure_directory_exists(test_dir)
        self.assertTrue(os.path.exists(test_dir))
        self.assertTrue(os.path.isdir(test_dir))
        
        # Test with an existing directory (should not raise an error)
        file_utils.ensure_directory_exists(test_dir)
        self.assertTrue(os.path.exists(test_dir))
        
        # Test with nested directories
        nested_dir = os.path.join(self.test_dir, 'parent/child/grandchild')
        self.assertFalse(os.path.exists(nested_dir))
        
        file_utils.ensure_directory_exists(nested_dir)
        self.assertTrue(os.path.exists(nested_dir))
        self.assertTrue(os.path.isdir(nested_dir))

    def test_get_document_category_for_mime_type(self):
        """Test get_document_category_for_mime_type function."""
        # Test with MIME types that have categories
        self.assertEqual(file_utils.get_document_category_for_mime_type('application/pdf'), 'loan_application')
        self.assertEqual(file_utils.get_document_category_for_mime_type('image/jpeg'), 'bank_statement')
        
        # Test with a MIME type that doesn't have a specific category
        self.assertIsNone(file_utils.get_document_category_for_mime_type('application/x-executable'))

    def test_bytes_to_file_and_file_to_bytes(self):
        """Test bytes_to_file and file_to_bytes functions."""
        # Test bytes_to_file
        test_content = b"test content for conversion"
        test_file = os.path.join(self.test_dir, 'conversion_test.txt')
        
        file_utils.bytes_to_file(test_content, test_file)
        self.assertTrue(os.path.exists(test_file))
        
        # Test file_to_bytes
        content = file_utils.file_to_bytes(test_file)
        self.assertEqual(content, test_content)
        
        # Test with nested directory structure
        nested_file = os.path.join(self.test_dir, 'nested/path/file.txt')
        file_utils.bytes_to_file(test_content, nested_file)
        self.assertTrue(os.path.exists(nested_file))
        
        content = file_utils.file_to_bytes(nested_file)
        self.assertEqual(content, test_content)

    def test_get_safe_filename(self):
        """Test get_safe_filename function."""
        # Test with a safe filename
        safe_name = "safe_filename.txt"
        result = file_utils.get_safe_filename(safe_name)
        self.assertEqual(result, safe_name)
        
        # Test with unsafe characters
        unsafe_name = "unsafe/file:name?.txt"
        result = file_utils.get_safe_filename(unsafe_name)
        self.assertEqual(result, "unsafe_file_name_.txt")
        
        # Test with a very long filename
        long_name = "a" * 300 + ".txt"
        result = file_utils.get_safe_filename(long_name)
        self.assertEqual(len(result), 255)
        self.assertTrue(result.endswith(".txt"))

    def test_generate_unique_filename(self):
        """Test generate_unique_filename function."""
        # Test with a filename and content
        original_name = "test_file.txt"
        content = b"test content for unique filename"
        
        # Mock calculate_file_hash to return a known hash
        with mock.patch('document_service.src.utils.file_utils.calculate_file_hash', return_value="abcdef1234567890"):
            unique_name = file_utils.generate_unique_filename(original_name, content)
            self.assertEqual(unique_name, "test_file_abcdef12.txt")
            
        # Test with unsafe characters in the filename
        unsafe_name = "unsafe/file:name?.txt"
        with mock.patch('document_service.src.utils.file_utils.calculate_file_hash', return_value="abcdef1234567890"):
            unique_name = file_utils.generate_unique_filename(unsafe_name, content)
            self.assertEqual(unique_name, "unsafe_file_name__abcdef12.txt")


if __name__ == '__main__':
    unittest.main()