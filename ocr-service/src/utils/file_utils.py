#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File handling utilities for the OCR Service.

This module provides utility functions for file operations, MIME type detection,
content type validation, file size calculation, and temporary file management.
It's essential for processing documents and preparing them for OCR extraction and storage.
"""

import os
import io
import mimetypes
import tempfile
import shutil
import logging
from pathlib import Path
from typing import Union, Optional, Dict, List, Tuple, BinaryIO, Any

# Initialize mimetypes database
mimetypes.init()

# Configure logger
logger = logging.getLogger(__name__)

# Define supported document types and their MIME types
SUPPORTED_MIME_TYPES = {
    'application/pdf': ['.pdf'],
    'image/tiff': ['.tiff', '.tif'],
    'image/jpeg': ['.jpg', '.jpeg', '.jpe'],
    'image/png': ['.png']
}

# Reverse mapping from extension to MIME type
EXTENSION_TO_MIME = {}
for mime_type, extensions in SUPPORTED_MIME_TYPES.items():
    for ext in extensions:
        EXTENSION_TO_MIME[ext.lower()] = mime_type


def get_mime_type(file_path: Union[str, Path]) -> Optional[str]:
    """
    Determine the MIME type of a file based on its extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        MIME type string or None if it cannot be determined
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    return mime_type


def get_mime_type_from_content(file_path: Union[str, Path, bytes, BinaryIO]) -> Optional[str]:
    """
    Determine the MIME type of a file based on its content using python-magic.
    This is more accurate than extension-based detection.
    
    Args:
        file_path: Path to the file, bytes content, or file-like object
        
    Returns:
        MIME type string or None if it cannot be determined
    """
    try:
        import magic
        mime = magic.Magic(mime=True)
        
        if isinstance(file_path, (str, Path)):
            return mime.from_file(str(file_path))
        elif isinstance(file_path, bytes):
            return mime.from_buffer(file_path)
        elif hasattr(file_path, 'read'):
            # Handle file-like objects
            position = file_path.tell()
            content = file_path.read(8192)  # Read first 8KB for MIME detection
            file_path.seek(position)  # Reset file position
            return mime.from_buffer(content)
        else:
            logger.error(f"Unsupported file_path type: {type(file_path)}")
            return None
    except ImportError:
        logger.warning("python-magic not installed, falling back to extension-based detection")
        if isinstance(file_path, (str, Path)):
            return get_mime_type(file_path)
        else:
            logger.error("Cannot determine MIME type without python-magic for non-path inputs")
            return None
    except Exception as e:
        logger.error(f"Error determining MIME type: {str(e)}")
        return None


def is_supported_document_type(file_path: Union[str, Path, bytes, BinaryIO]) -> bool:
    """
    Check if the file is a supported document type for OCR processing.
    
    Args:
        file_path: Path to the file, bytes content, or file-like object
        
    Returns:
        True if the file is a supported document type, False otherwise
    """
    mime_type = get_mime_type_from_content(file_path)
    if not mime_type:
        mime_type = get_mime_type(file_path) if isinstance(file_path, (str, Path)) else None
    
    return mime_type in SUPPORTED_MIME_TYPES


def get_file_extension(file_path: Union[str, Path]) -> str:
    """
    Get the file extension from a file path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File extension including the dot (e.g., '.pdf')
    """
    return os.path.splitext(str(file_path))[1].lower()


def get_file_size(file_path: Union[str, Path, BinaryIO]) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file or file-like object
        
    Returns:
        File size in bytes
    """
    if isinstance(file_path, (str, Path)):
        return os.path.getsize(str(file_path))
    elif hasattr(file_path, 'seek') and hasattr(file_path, 'tell'):
        # Handle file-like objects
        current_position = file_path.tell()
        file_path.seek(0, os.SEEK_END)
        size = file_path.tell()
        file_path.seek(current_position)  # Reset file position
        return size
    else:
        raise TypeError(f"Unsupported file_path type: {type(file_path)}")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in a human-readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string (e.g., '2.5 MB')
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def create_temp_file(prefix: str = 'ocr_', suffix: str = '') -> Tuple[str, Any]:
    """
    Create a temporary file for document processing.
    
    Args:
        prefix: Prefix for the temporary file name
        suffix: Suffix for the temporary file name (e.g., '.pdf')
        
    Returns:
        Tuple of (file path, file object)
    """
    fd, temp_path = tempfile.mkstemp(prefix=prefix, suffix=suffix)
    return temp_path, os.fdopen(fd, 'wb+')


def create_temp_directory(prefix: str = 'ocr_') -> str:
    """
    Create a temporary directory for document processing.
    
    Args:
        prefix: Prefix for the temporary directory name
        
    Returns:
        Path to the temporary directory
    """
    return tempfile.mkdtemp(prefix=prefix)


def cleanup_temp_file(temp_path: str) -> None:
    """
    Clean up a temporary file after processing.
    
    Args:
        temp_path: Path to the temporary file
    """
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    except Exception as e:
        logger.error(f"Error cleaning up temporary file {temp_path}: {str(e)}")


def cleanup_temp_directory(temp_dir: str) -> None:
    """
    Clean up a temporary directory after processing.
    
    Args:
        temp_dir: Path to the temporary directory
    """
    try:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
    except Exception as e:
        logger.error(f"Error cleaning up temporary directory {temp_dir}: {str(e)}")


def bytes_to_file(data: bytes, file_path: str) -> None:
    """
    Write bytes data to a file.
    
    Args:
        data: Bytes data to write
        file_path: Path to the output file
    """
    with open(file_path, 'wb') as f:
        f.write(data)


def file_to_bytes(file_path: Union[str, Path]) -> bytes:
    """
    Read a file into bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        File content as bytes
    """
    with open(str(file_path), 'rb') as f:
        return f.read()


def stream_to_bytes(stream: BinaryIO) -> bytes:
    """
    Read a stream into bytes.
    
    Args:
        stream: File-like object to read from
        
    Returns:
        Stream content as bytes
    """
    position = stream.tell()
    stream.seek(0)
    content = stream.read()
    stream.seek(position)  # Reset stream position
    return content


def bytes_to_stream(data: bytes) -> BinaryIO:
    """
    Convert bytes to a file-like object (BytesIO).
    
    Args:
        data: Bytes data to convert
        
    Returns:
        BytesIO object containing the data
    """
    return io.BytesIO(data)


def ensure_directory_exists(directory_path: Union[str, Path]) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
    """
    os.makedirs(str(directory_path), exist_ok=True)


def get_content_type_for_s3(file_path: Union[str, Path]) -> str:
    """
    Get the content type (MIME type) for S3 storage based on file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Content type string for S3 (defaults to 'application/octet-stream' if unknown)
    """
    extension = get_file_extension(file_path)
    return EXTENSION_TO_MIME.get(extension, 'application/octet-stream')


def is_valid_file(file_path: Union[str, Path]) -> bool:
    """
    Check if a file exists and is accessible.
    
    Args:
        file_path: Path to the file
        
    Returns:
        True if the file exists and is accessible, False otherwise
    """
    try:
        return os.path.isfile(str(file_path)) and os.access(str(file_path), os.R_OK)
    except Exception:
        return False


def get_safe_filename(filename: str) -> str:
    """
    Convert a filename to a safe version that can be used as a filename on any platform.
    
    Args:
        filename: Original filename
        
    Returns:
        Safe filename
    """
    # Replace spaces with underscores and remove other unsafe characters
    safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in filename)
    return safe_name.replace(" ", "_")