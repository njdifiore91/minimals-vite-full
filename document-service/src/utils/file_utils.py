#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File handling utilities for the Document Service.

This module provides utility functions for file operations, MIME type detection,
and content type validation used in the Document Service. These utilities are
essential for processing documents and preparing them for classification and storage.

The module includes functions for:
- MIME type detection and validation
- File size calculation and formatting
- Temporary file management
- Buffer handling and conversion
- Content type mapping for document formats
- File hashing and unique filename generation

Dependencies:
- python-magic: Requires libmagic to be installed on the system
  - On Linux: Install libmagic using the system package manager (e.g., apt-get install libmagic1)
  - On macOS: Install libmagic using Homebrew (brew install libmagic)
  - On Windows: Use python-magic-bin package or follow instructions at https://github.com/ahupp/python-magic
"""

import os
import tempfile
import mimetypes
import hashlib
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO, Tuple
from contextlib import contextmanager

# Try to import magic, with fallback for different package names
try:
    import magic
except ImportError:
    try:
        # Try python-magic-bin as an alternative
        import magic
    except ImportError:
        raise ImportError(
            "Failed to import magic module. Please install python-magic or python-magic-bin. "
            "See module docstring for installation instructions."
        )

# Set up logger
logger = logging.getLogger(__name__)

# Initialize mimetypes
mimetypes.init()

# Define supported document types and their MIME types
SUPPORTED_MIME_TYPES = {
    # PDF documents
    'application/pdf': '.pdf',
    
    # Image formats
    'image/jpeg': '.jpg',
    'image/png': '.png',
    'image/tiff': '.tiff',
    'image/tif': '.tif',
    
    # Microsoft Office formats
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
    'application/vnd.ms-excel': '.xls',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
    
    # Plain text
    'text/plain': '.txt',
    
    # Rich text format
    'application/rtf': '.rtf',
    
    # Open document formats
    'application/vnd.oasis.opendocument.text': '.odt',
    'application/vnd.oasis.opendocument.spreadsheet': '.ods'
}

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

# Document categories for classification
DOCUMENT_CATEGORIES = {
    'loan_application': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
    'tax_return': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'],
    'bank_statement': ['application/pdf', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'image/jpeg', 'image/png'],
    'pay_stub': ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'],
    'identity_document': ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff'],
    'other': ['application/pdf', 'image/jpeg', 'image/png', 'text/plain']
}


def get_mime_type(file_path_or_bytes: Union[str, bytes, BinaryIO]) -> str:
    """
    Detect MIME type of a file or bytes object using python-magic.
    
    Args:
        file_path_or_bytes: Path to file, bytes object, or file-like object
        
    Returns:
        str: Detected MIME type
        
    Raises:
        ValueError: If the file cannot be read or MIME type cannot be detected
    """
    try:
        if isinstance(file_path_or_bytes, str):
            # It's a file path
            logger.debug(f"Detecting MIME type for file: {file_path_or_bytes}")
            mime = magic.from_file(file_path_or_bytes, mime=True)
        elif isinstance(file_path_or_bytes, bytes):
            # It's a bytes object
            logger.debug(f"Detecting MIME type from bytes object of length: {len(file_path_or_bytes)}")
            mime = magic.from_buffer(file_path_or_bytes, mime=True)
        else:
            # Assume it's a file-like object
            logger.debug("Detecting MIME type from file-like object")
            position = file_path_or_bytes.tell()
            file_path_or_bytes.seek(0)
            content = file_path_or_bytes.read(2048)  # Read first 2KB for MIME detection
            file_path_or_bytes.seek(position)  # Reset position
            mime = magic.from_buffer(content, mime=True)
            
        logger.debug(f"Detected MIME type: {mime}")
        return mime
    except Exception as e:
        logger.error(f"Failed to detect MIME type: {str(e)}")
        raise ValueError(f"Failed to detect MIME type: {str(e)}")


def is_supported_mime_type(mime_type: str) -> bool:
    """
    Check if the MIME type is supported by the Document Service.
    
    Args:
        mime_type: MIME type to check
        
    Returns:
        bool: True if supported, False otherwise
    """
    return mime_type in SUPPORTED_MIME_TYPES


def get_extension_for_mime_type(mime_type: str) -> Optional[str]:
    """
    Get the file extension for a given MIME type.
    
    Args:
        mime_type: MIME type
        
    Returns:
        Optional[str]: File extension including the dot, or None if not supported
    """
    return SUPPORTED_MIME_TYPES.get(mime_type)


def get_mime_type_for_extension(extension: str) -> Optional[str]:
    """
    Get the MIME type for a given file extension.
    
    Args:
        extension: File extension (with or without the dot)
        
    Returns:
        Optional[str]: MIME type or None if not found
    """
    if not extension.startswith('.'):
        extension = f'.{extension}'
        
    for mime_type, ext in SUPPORTED_MIME_TYPES.items():
        if ext == extension:
            return mime_type
    return None


def validate_file_type(file_path_or_bytes: Union[str, bytes, BinaryIO]) -> Tuple[bool, str]:
    """
    Validate if a file is of a supported type.
    
    Args:
        file_path_or_bytes: Path to file, bytes object, or file-like object
        
    Returns:
        Tuple[bool, str]: (is_valid, mime_type)
    """
    try:
        mime_type = get_mime_type(file_path_or_bytes)
        is_valid = is_supported_mime_type(mime_type)
        
        if is_valid:
            logger.info(f"Validated file with MIME type: {mime_type}")
        else:
            logger.warning(f"Unsupported MIME type detected: {mime_type}")
            
        return is_valid, mime_type
    except ValueError as e:
        logger.error(f"File validation failed: {str(e)}")
        return False, ""


def calculate_file_size(file_path_or_bytes: Union[str, bytes, BinaryIO]) -> int:
    """
    Calculate the size of a file in bytes.
    
    Args:
        file_path_or_bytes: Path to file, bytes object, or file-like object
        
    Returns:
        int: File size in bytes
        
    Raises:
        ValueError: If the file size cannot be determined
    """
    try:
        if isinstance(file_path_or_bytes, str):
            # It's a file path
            size = os.path.getsize(file_path_or_bytes)
            logger.debug(f"File size for {file_path_or_bytes}: {size} bytes")
            return size
        elif isinstance(file_path_or_bytes, bytes):
            # It's a bytes object
            size = len(file_path_or_bytes)
            logger.debug(f"Bytes object size: {size} bytes")
            return size
        else:
            # Assume it's a file-like object
            position = file_path_or_bytes.tell()
            file_path_or_bytes.seek(0, os.SEEK_END)
            size = file_path_or_bytes.tell()
            file_path_or_bytes.seek(position)  # Reset position
            logger.debug(f"File-like object size: {size} bytes")
            return size
    except Exception as e:
        logger.error(f"Failed to calculate file size: {str(e)}")
        raise ValueError(f"Failed to calculate file size: {str(e)}")


def format_file_size(size_in_bytes: int) -> str:
    """
    Format file size in a human-readable format.
    
    Args:
        size_in_bytes: File size in bytes
        
    Returns:
        str: Formatted file size (e.g., "2.5 MB")
    """
    if size_in_bytes == 0:
        return "0 bytes"
        
    units = ['bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
    i = 0
    while size_in_bytes >= 1024 and i < len(units) - 1:
        size_in_bytes /= 1024.0
        i += 1
        
    formatted = f"{size_in_bytes:.2f} {units[i]}"
    return formatted


def is_file_size_valid(file_path_or_bytes: Union[str, bytes, BinaryIO]) -> bool:
    """
    Check if the file size is within the allowed limit.
    
    Args:
        file_path_or_bytes: Path to file, bytes object, or file-like object
        
    Returns:
        bool: True if the file size is valid, False otherwise
    """
    try:
        size = calculate_file_size(file_path_or_bytes)
        is_valid = size <= MAX_FILE_SIZE
        
        if not is_valid:
            formatted_size = format_file_size(size)
            max_formatted = format_file_size(MAX_FILE_SIZE)
            logger.warning(f"File size {formatted_size} exceeds maximum allowed size of {max_formatted}")
            
        return is_valid
    except ValueError as e:
        logger.error(f"Failed to validate file size: {str(e)}")
        return False


def calculate_file_hash(file_path_or_bytes: Union[str, bytes, BinaryIO], algorithm: str = 'sha256') -> str:
    """
    Calculate a hash of the file contents.
    
    Args:
        file_path_or_bytes: Path to file, bytes object, or file-like object
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        str: Hexadecimal hash digest
        
    Raises:
        ValueError: If the hash cannot be calculated
    """
    try:
        hash_obj = hashlib.new(algorithm)
        
        if isinstance(file_path_or_bytes, str):
            # It's a file path
            with open(file_path_or_bytes, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_obj.update(chunk)
        elif isinstance(file_path_or_bytes, bytes):
            # It's a bytes object
            hash_obj.update(file_path_or_bytes)
        else:
            # Assume it's a file-like object
            position = file_path_or_bytes.tell()
            file_path_or_bytes.seek(0)
            for chunk in iter(lambda: file_path_or_bytes.read(4096), b""):
                hash_obj.update(chunk)
            file_path_or_bytes.seek(position)  # Reset position
            
        return hash_obj.hexdigest()
    except Exception as e:
        raise ValueError(f"Failed to calculate file hash: {str(e)}")


@contextmanager
def create_temp_file(content: Union[str, bytes], suffix: Optional[str] = None) -> str:
    """
    Create a temporary file with the given content.
    
    Args:
        content: File content (string or bytes)
        suffix: Optional file suffix/extension
        
    Yields:
        str: Path to the temporary file
        
    Notes:
        The temporary file is automatically deleted when the context is exited.
    """
    temp_file = None
    try:
        # Create a temporary file
        fd, temp_file = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        
        logger.debug(f"Created temporary file: {temp_file}")
        
        # Write content to the file
        mode = 'wb' if isinstance(content, bytes) else 'w'
        with open(temp_file, mode) as f:
            f.write(content)
            
        logger.debug(f"Wrote content to temporary file: {temp_file}")
        yield temp_file
    finally:
        # Clean up the temporary file
        if temp_file and os.path.exists(temp_file):
            logger.debug(f"Cleaning up temporary file: {temp_file}")
            os.unlink(temp_file)


@contextmanager
def create_temp_directory() -> str:
    """
    Create a temporary directory for document processing.
    
    Yields:
        str: Path to the temporary directory
        
    Notes:
        The temporary directory is automatically deleted when the context is exited.
    """
    temp_dir = None
    try:
        temp_dir = tempfile.mkdtemp()
        logger.debug(f"Created temporary directory: {temp_dir}")
        yield temp_dir
    finally:
        # Clean up the temporary directory
        if temp_dir and os.path.exists(temp_dir):
            logger.debug(f"Cleaning up temporary directory: {temp_dir}")
            shutil.rmtree(temp_dir)


def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
    """
    os.makedirs(directory_path, exist_ok=True)


def get_document_category_for_mime_type(mime_type: str) -> Optional[str]:
    """
    Get the potential document category based on MIME type.
    
    Args:
        mime_type: MIME type of the document
        
    Returns:
        Optional[str]: Potential document category or None if not found
    """
    for category, mime_types in DOCUMENT_CATEGORIES.items():
        if mime_type in mime_types:
            logger.debug(f"Document with MIME type {mime_type} categorized as: {category}")
            return category
            
    logger.warning(f"No category found for MIME type: {mime_type}")
    return None


def bytes_to_file(content: bytes, file_path: str) -> None:
    """
    Write bytes content to a file.
    
    Args:
        content: Bytes content to write
        file_path: Path to the output file
        
    Raises:
        IOError: If the file cannot be written
    """
    # Ensure the directory exists
    directory = os.path.dirname(file_path)
    if directory:
        ensure_directory_exists(directory)
        
    # Write the content
    with open(file_path, 'wb') as f:
        f.write(content)


def file_to_bytes(file_path: str) -> bytes:
    """
    Read a file into bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bytes: File content as bytes
        
    Raises:
        IOError: If the file cannot be read
    """
    with open(file_path, 'rb') as f:
        return f.read()


def get_safe_filename(filename: str) -> str:
    """
    Convert a filename to a safe version that is filesystem-friendly.
    
    Args:
        filename: Original filename
        
    Returns:
        str: Safe filename
    """
    # Replace problematic characters
    safe_name = "".join([c if c.isalnum() or c in "._- " else "_" for c in filename])
    
    # Ensure the filename is not too long (max 255 characters)
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255 - len(ext)] + ext
        
    if safe_name != filename:
        logger.debug(f"Converted filename '{filename}' to safe version '{safe_name}'")
        
    return safe_name


def generate_unique_filename(original_filename: str, content: Union[str, bytes, BinaryIO]) -> str:
    """
    Generate a unique filename based on the original filename and content hash.
    
    Args:
        original_filename: Original filename
        content: File content for hash calculation
        
    Returns:
        str: Unique filename
    """
    # Get a safe version of the original filename
    safe_name = get_safe_filename(original_filename)
    name, ext = os.path.splitext(safe_name)
    
    # Calculate a hash of the content
    content_hash = calculate_file_hash(content)[:8]  # Use first 8 characters of hash
    
    # Combine name, hash, and extension
    unique_name = f"{name}_{content_hash}{ext}"
    logger.debug(f"Generated unique filename: {unique_name} from original: {original_filename}")
    
    return unique_name