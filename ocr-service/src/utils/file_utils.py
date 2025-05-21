#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
File handling utilities for the OCR Service.

This module provides utility functions for file operations, MIME type detection,
content type validation, file size formatting, and temporary file management.
It's essential for processing documents and preparing them for OCR extraction and storage.
"""

import os
import re
import tempfile
import mimetypes
import logging
import hashlib
import uuid
import datetime
from typing import Dict, List, Optional, Set, Tuple, Union, Any, BinaryIO, Iterator
from pathlib import Path
from functools import wraps
import shutil
import io
import math

# Import custom types
from ..types.documents import DocumentMetadata, DocumentType, DocumentContent
from ..types.errors import ServiceError

# Configure logger
logger = logging.getLogger(__name__)

# Constants for file operations
BUFFER_SIZE = 65536  # 64KB buffer size for file operations

# Constants for MIME type detection
DEFAULT_MIME_TYPE = 'application/octet-stream'

# Supported MIME types and their corresponding file extensions
SUPPORTED_MIME_TYPES = {
    # PDF documents
    'application/pdf': ['.pdf'],
    
    # TIFF images
    'image/tiff': ['.tiff', '.tif'],
    
    # JPEG images
    'image/jpeg': ['.jpg', '.jpeg'],
    
    # PNG images
    'image/png': ['.png']
}

# Flat list of all supported file extensions
SUPPORTED_EXTENSIONS = [ext for exts in SUPPORTED_MIME_TYPES.values() for ext in exts]

# Document type to MIME type mapping
DOCUMENT_TYPE_MIME_MAPPING = {
    DocumentType.APPLICATION.value: ['application/pdf'],
    DocumentType.TAX_RETURN.value: ['application/pdf', 'image/tiff'],
    DocumentType.BANK_STATEMENT.value: ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
    DocumentType.PAY_STUB.value: ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
    DocumentType.ID_DOCUMENT.value: ['application/pdf', 'image/tiff', 'image/jpeg', 'image/png'],
    DocumentType.OTHER.value: list(SUPPORTED_MIME_TYPES.keys())
}

# OCR processing type to MIME type mapping
OCR_PROCESSING_TYPE_MIME_MAPPING = {
    'TYPED': list(SUPPORTED_MIME_TYPES.keys()),  # All supported MIME types can contain typed text
    'HANDWRITTEN': list(SUPPORTED_MIME_TYPES.keys()),  # All supported MIME types can contain handwritten text
    'HYBRID': list(SUPPORTED_MIME_TYPES.keys())  # All supported MIME types can contain hybrid text
}

# File size units for formatting
SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

# Temporary file settings
TEMP_DIR = tempfile.gettempdir()
TEMP_PREFIX = 'mca_ocr_'


def file_operation_decorator(func):
    """
    Decorator for file operation functions to handle exceptions and log errors.
    
    Args:
        func: The file operation function to decorate
        
    Returns:
        Callable: Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"File operation error in {func.__name__}: {str(e)}")
            raise ServiceError(f"File operation error: {str(e)}")
    return wrapper


@file_operation_decorator
def get_file_size(file_path: str) -> int:
    """
    Get the size of a file in bytes.
    
    Args:
        file_path: Path to the file
        
    Returns:
        int: Size of the file in bytes
    """
    return os.path.getsize(file_path)


@file_operation_decorator
def get_file_size_from_buffer(buffer: bytes) -> int:
    """
    Get the size of a file buffer in bytes.
    
    Args:
        buffer: File content as bytes
        
    Returns:
        int: Size of the buffer in bytes
    """
    return len(buffer)


def format_file_size(size_in_bytes: int, decimal_places: int = 2) -> str:
    """
    Format file size in human-readable format (e.g., KB, MB, GB).
    
    Args:
        size_in_bytes: Size of the file in bytes
        decimal_places: Number of decimal places to include in the formatted size
        
    Returns:
        str: Human-readable file size
    """
    if size_in_bytes == 0:
        return "0 bytes"
    
    # Calculate the appropriate unit index (0=B, 1=KB, 2=MB, etc.)
    unit_index = min(int(math.log(size_in_bytes, 1024)), len(SIZE_UNITS) - 1)
    
    # Calculate the size in the appropriate unit
    size_in_unit = size_in_bytes / (1024 ** unit_index)
    
    # Format the size with the specified number of decimal places
    formatted_size = f"{size_in_unit:.{decimal_places}f}"
    
    # Remove trailing zeros and decimal point if not needed
    if '.' in formatted_size:
        formatted_size = formatted_size.rstrip('0').rstrip('.') if '.' in formatted_size else formatted_size
    
    return f"{formatted_size} {SIZE_UNITS[unit_index]}"


def convert_size_to_bytes(size: float, unit: str) -> int:
    """
    Convert a file size from a specific unit to bytes.
    
    Args:
        size: Size value to convert
        unit: Unit to convert from (B, KB, MB, GB, etc.)
        
    Returns:
        int: Size in bytes
    """
    unit = unit.upper()
    if unit not in SIZE_UNITS:
        raise ValueError(f"Invalid size unit: {unit}. Must be one of {SIZE_UNITS}")
    
    unit_index = SIZE_UNITS.index(unit)
    return int(size * (1024 ** unit_index))


@file_operation_decorator
def get_mime_type(file_path: str) -> str:
    """
    Detect the MIME type of a file based on its extension and content.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Detected MIME type
    """
    # First try to detect MIME type using python-magic if available
    try:
        import magic
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_file(file_path)
        if detected_mime:
            return detected_mime
    except ImportError:
        logger.warning("python-magic not available, falling back to mimetypes module")
    except Exception as e:
        logger.warning(f"Error detecting MIME type with python-magic: {str(e)}")
    
    # Fall back to mimetypes module (less accurate, based on extension only)
    mime_type, encoding = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type
    
    # If all else fails, try to determine based on file extension
    ext = Path(file_path).suffix.lower()
    for mime, extensions in SUPPORTED_MIME_TYPES.items():
        if ext in extensions:
            return mime
    
    # Default MIME type if detection fails
    return DEFAULT_MIME_TYPE


@file_operation_decorator
def get_mime_type_from_buffer(buffer: bytes) -> str:
    """
    Detect the MIME type from a bytes buffer.
    
    Args:
        buffer: File content as bytes
        
    Returns:
        str: Detected MIME type
    """
    # Try to detect MIME type using python-magic if available
    try:
        import magic
        mime = magic.Magic(mime=True)
        detected_mime = mime.from_buffer(buffer)
        if detected_mime:
            return detected_mime
    except ImportError:
        logger.warning("python-magic not available for buffer MIME type detection")
    except Exception as e:
        logger.warning(f"Error detecting MIME type from buffer with python-magic: {str(e)}")
    
    # If python-magic is not available, we can't reliably detect MIME type from buffer
    # Return default MIME type
    return DEFAULT_MIME_TYPE


@file_operation_decorator
def get_mime_type_from_filename(filename: str) -> str:
    """
    Detect the MIME type based on filename or extension.
    
    Args:
        filename: Filename or path
        
    Returns:
        str: Detected MIME type
    """
    mime_type, encoding = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type
    
    # Try to determine based on file extension
    ext = Path(filename).suffix.lower()
    for mime, extensions in SUPPORTED_MIME_TYPES.items():
        if ext in extensions:
            return mime
    
    # Default MIME type if detection fails
    return DEFAULT_MIME_TYPE


def is_supported_mime_type(mime_type: str) -> bool:
    """
    Check if the MIME type is in the list of supported types.
    
    Args:
        mime_type: MIME type to check
        
    Returns:
        bool: True if supported, False otherwise
    """
    return mime_type in SUPPORTED_MIME_TYPES


def is_supported_file_extension(file_path: str) -> bool:
    """
    Check if the file has a supported extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        bool: True if the extension is supported, False otherwise
    """
    ext = Path(file_path).suffix.lower()
    return ext in SUPPORTED_EXTENSIONS


def get_file_extension(file_path: str) -> str:
    """
    Get the file extension from a file path.
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: File extension (including the dot)
    """
    return Path(file_path).suffix.lower()


def get_file_extension_from_mime_type(mime_type: str) -> Optional[str]:
    """
    Get the default file extension for a MIME type.
    
    Args:
        mime_type: MIME type
        
    Returns:
        Optional[str]: File extension (including the dot) or None if not found
    """
    if mime_type in SUPPORTED_MIME_TYPES:
        return SUPPORTED_MIME_TYPES[mime_type][0]  # Return the first extension in the list
    
    # Try using mimetypes module as fallback
    ext = mimetypes.guess_extension(mime_type)
    if ext:
        return ext
    
    return None


@file_operation_decorator
def create_temp_file(prefix: str = TEMP_PREFIX, suffix: str = '', dir: str = TEMP_DIR) -> Tuple[str, BinaryIO]:
    """
    Create a temporary file and return its path and file object.
    
    Args:
        prefix: Prefix for the temporary file name
        suffix: Suffix for the temporary file name (e.g., file extension)
        dir: Directory where the temporary file will be created
        
    Returns:
        Tuple[str, BinaryIO]: Tuple containing the file path and file object
    """
    fd, path = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=dir)
    return path, os.fdopen(fd, 'wb')


@file_operation_decorator
def create_named_temp_file(prefix: str = TEMP_PREFIX, suffix: str = '', dir: str = TEMP_DIR, delete: bool = True) -> tempfile._TemporaryFileWrapper:
    """
    Create a named temporary file using NamedTemporaryFile.
    
    Args:
        prefix: Prefix for the temporary file name
        suffix: Suffix for the temporary file name (e.g., file extension)
        dir: Directory where the temporary file will be created
        delete: Whether to delete the file when closed (default: True)
        
    Returns:
        tempfile._TemporaryFileWrapper: Temporary file object with a visible name
    """
    return tempfile.NamedTemporaryFile(mode='wb', prefix=prefix, suffix=suffix, dir=dir, delete=delete)


@file_operation_decorator
def create_temp_directory(prefix: str = TEMP_PREFIX, dir: str = TEMP_DIR) -> str:
    """
    Create a temporary directory and return its path.
    
    Args:
        prefix: Prefix for the temporary directory name
        dir: Parent directory where the temporary directory will be created
        
    Returns:
        str: Path to the created temporary directory
    """
    return tempfile.mkdtemp(prefix=prefix, dir=dir)


@file_operation_decorator
def write_buffer_to_file(buffer: bytes, file_path: str) -> None:
    """
    Write a bytes buffer to a file.
    
    Args:
        buffer: Bytes buffer to write
        file_path: Path to the file to write to
        
    Returns:
        None
    """
    with open(file_path, 'wb') as f:
        f.write(buffer)


@file_operation_decorator
def read_file_to_buffer(file_path: str) -> bytes:
    """
    Read a file into a bytes buffer.
    
    Args:
        file_path: Path to the file to read
        
    Returns:
        bytes: File content as bytes
    """
    with open(file_path, 'rb') as f:
        return f.read()


@file_operation_decorator
def read_file_in_chunks(file_path: str, chunk_size: int = BUFFER_SIZE) -> Iterator[bytes]:
    """
    Read a file in chunks to avoid loading large files into memory.
    
    Args:
        file_path: Path to the file to read
        chunk_size: Size of each chunk in bytes
        
    Returns:
        Iterator[bytes]: Iterator yielding file chunks
    """
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            yield chunk


@file_operation_decorator
def copy_file(source_path: str, dest_path: str) -> None:
    """
    Copy a file from source to destination.
    
    Args:
        source_path: Path to the source file
        dest_path: Path to the destination file
        
    Returns:
        None
    """
    shutil.copy2(source_path, dest_path)


@file_operation_decorator
def ensure_directory_exists(directory_path: str) -> None:
    """
    Ensure that a directory exists, creating it if necessary.
    
    Args:
        directory_path: Path to the directory
        
    Returns:
        None
    """
    os.makedirs(directory_path, exist_ok=True)


@file_operation_decorator
def remove_file(file_path: str) -> None:
    """
    Remove a file if it exists.
    
    Args:
        file_path: Path to the file to remove
        
    Returns:
        None
    """
    if os.path.exists(file_path):
        os.remove(file_path)


@file_operation_decorator
def remove_directory(directory_path: str, recursive: bool = True) -> None:
    """
    Remove a directory if it exists.
    
    Args:
        directory_path: Path to the directory to remove
        recursive: Whether to remove the directory recursively (default: True)
        
    Returns:
        None
    """
    if os.path.exists(directory_path):
        if recursive:
            shutil.rmtree(directory_path)
        else:
            os.rmdir(directory_path)


@file_operation_decorator
def calculate_file_hash(file_path: str, algorithm: str = 'sha256', buffer_size: int = BUFFER_SIZE) -> str:
    """
    Calculate a hash for the given file.
    
    Args:
        file_path: Path to the file
        algorithm: Hash algorithm to use (default: sha256)
        buffer_size: Size of the buffer for reading the file
        
    Returns:
        str: Calculated hash value
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    elif algorithm == 'sha512':
        hash_obj = hashlib.sha512()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(buffer_size)
            if not data:
                break
            hash_obj.update(data)
    
    return hash_obj.hexdigest()


@file_operation_decorator
def calculate_buffer_hash(buffer: bytes, algorithm: str = 'sha256') -> str:
    """
    Calculate a hash for the given buffer.
    
    Args:
        buffer: Bytes buffer to hash
        algorithm: Hash algorithm to use (default: sha256)
        
    Returns:
        str: Calculated hash value
    """
    if algorithm == 'md5':
        hash_obj = hashlib.md5()
    elif algorithm == 'sha1':
        hash_obj = hashlib.sha1()
    elif algorithm == 'sha256':
        hash_obj = hashlib.sha256()
    elif algorithm == 'sha512':
        hash_obj = hashlib.sha512()
    else:
        raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    hash_obj.update(buffer)
    return hash_obj.hexdigest()


class TempFileManager:
    """
    Context manager for temporary file operations.
    
    This class provides a context manager for creating and managing temporary files,
    ensuring they are properly cleaned up when operations are complete.
    """
    
    def __init__(self, prefix: str = TEMP_PREFIX, suffix: str = '', dir: str = TEMP_DIR):
        """
        Initialize the TempFileManager.
        
        Args:
            prefix: Prefix for the temporary file name
            suffix: Suffix for the temporary file name (e.g., file extension)
            dir: Directory where the temporary file will be created
        """
        self.prefix = prefix
        self.suffix = suffix
        self.dir = dir
        self.temp_files = []
        self.temp_dirs = []
    
    def create_temp_file(self, content: Optional[bytes] = None) -> str:
        """
        Create a temporary file and optionally write content to it.
        
        Args:
            content: Optional bytes content to write to the file
            
        Returns:
            str: Path to the created temporary file
        """
        fd, path = tempfile.mkstemp(prefix=self.prefix, suffix=self.suffix, dir=self.dir)
        self.temp_files.append(path)
        
        if content is not None:
            with os.fdopen(fd, 'wb') as f:
                f.write(content)
        else:
            os.close(fd)
        
        return path
    
    def create_temp_directory(self) -> str:
        """
        Create a temporary directory.
        
        Returns:
            str: Path to the created temporary directory
        """
        path = tempfile.mkdtemp(prefix=self.prefix, dir=self.dir)
        self.temp_dirs.append(path)
        return path
    
    def cleanup(self) -> None:
        """
        Clean up all temporary files and directories created by this manager.
        """
        # Clean up temporary files
        for path in self.temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {path}: {str(e)}")
        
        # Clean up temporary directories
        for path in self.temp_dirs:
            try:
                if os.path.exists(path):
                    shutil.rmtree(path)
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {path}: {str(e)}")
        
        # Clear the lists
        self.temp_files = []
        self.temp_dirs = []
    
    def __enter__(self) -> 'TempFileManager':
        """
        Enter the context manager.
        
        Returns:
            TempFileManager: This instance
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager and clean up temporary files and directories.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        self.cleanup()


class SpooledTempFileManager:
    """
    Context manager for spooled temporary file operations.
    
    This class provides a context manager for creating and managing spooled temporary files,
    which store data in memory until a size threshold is reached, then switch to disk storage.
    """
    
    def __init__(self, max_size: int = 1024*1024, prefix: str = TEMP_PREFIX, suffix: str = '', dir: str = TEMP_DIR):
        """
        Initialize the SpooledTempFileManager.
        
        Args:
            max_size: Maximum size in bytes before spooling to disk (default: 1MB)
            prefix: Prefix for the temporary file name
            suffix: Suffix for the temporary file name (e.g., file extension)
            dir: Directory where the temporary file will be created if spooled to disk
        """
        self.max_size = max_size
        self.prefix = prefix
        self.suffix = suffix
        self.dir = dir
        self.temp_files = []
    
    def create_spooled_temp_file(self) -> tempfile.SpooledTemporaryFile:
        """
        Create a spooled temporary file.
        
        Returns:
            tempfile.SpooledTemporaryFile: Spooled temporary file object
        """
        temp_file = tempfile.SpooledTemporaryFile(
            max_size=self.max_size,
            prefix=self.prefix,
            suffix=self.suffix,
            dir=self.dir,
            mode='wb+'
        )
        self.temp_files.append(temp_file)
        return temp_file
    
    def cleanup(self) -> None:
        """
        Clean up all spooled temporary files created by this manager.
        """
        for temp_file in self.temp_files:
            try:
                temp_file.close()
            except Exception as e:
                logger.warning(f"Failed to close spooled temporary file: {str(e)}")
        
        # Clear the list
        self.temp_files = []
    
    def __enter__(self) -> 'SpooledTempFileManager':
        """
        Enter the context manager.
        
        Returns:
            SpooledTempFileManager: This instance
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Exit the context manager and clean up spooled temporary files.
        
        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        self.cleanup()


@file_operation_decorator
def buffer_to_stream(buffer: bytes) -> io.BytesIO:
    """
    Convert a bytes buffer to a BytesIO stream.
    
    Args:
        buffer: Bytes buffer to convert
        
    Returns:
        io.BytesIO: BytesIO stream containing the buffer data
    """
    return io.BytesIO(buffer)


@file_operation_decorator
def stream_to_buffer(stream: io.BytesIO) -> bytes:
    """
    Convert a BytesIO stream to a bytes buffer.
    
    Args:
        stream: BytesIO stream to convert
        
    Returns:
        bytes: Bytes buffer containing the stream data
    """
    # Save the current position
    current_pos = stream.tell()
    
    # Seek to the beginning of the stream
    stream.seek(0)
    
    # Read the entire stream into a buffer
    buffer = stream.read()
    
    # Restore the original position
    stream.seek(current_pos)
    
    return buffer


@file_operation_decorator
def get_file_metadata(file_path: str) -> Dict[str, Any]:
    """
    Get metadata for a file.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict[str, Any]: Dictionary containing file metadata
    """
    stat_result = os.stat(file_path)
    file_size = stat_result.st_size
    mime_type = get_mime_type(file_path)
    file_extension = get_file_extension(file_path)
    file_name = os.path.basename(file_path)
    
    return {
        'file_name': file_name,
        'file_path': file_path,
        'file_size': file_size,
        'file_size_formatted': format_file_size(file_size),
        'mime_type': mime_type,
        'file_extension': file_extension,
        'created_at': stat_result.st_ctime,
        'modified_at': stat_result.st_mtime,
        'accessed_at': stat_result.st_atime
    }


@file_operation_decorator
def is_valid_document_for_ocr(file_path: str, ocr_processing_type: Optional[str] = None) -> bool:
    """
    Check if a file is valid for OCR processing.
    
    Args:
        file_path: Path to the file
        ocr_processing_type: Optional OCR processing type (TYPED, HANDWRITTEN, HYBRID)
        
    Returns:
        bool: True if the file is valid for OCR processing, False otherwise
    """
    # Get the MIME type of the file
    mime_type = get_mime_type(file_path)
    
    # Check if the MIME type is supported
    if not is_supported_mime_type(mime_type):
        logger.warning(f"MIME type {mime_type} is not supported for OCR processing")
        return False
    
    # If OCR processing type is specified, check if the MIME type is compatible
    if ocr_processing_type is not None:
        if ocr_processing_type not in OCR_PROCESSING_TYPE_MIME_MAPPING:
            logger.warning(f"Invalid OCR processing type: {ocr_processing_type}")
            return False
        
        compatible_mime_types = OCR_PROCESSING_TYPE_MIME_MAPPING.get(ocr_processing_type, [])
        if mime_type not in compatible_mime_types:
            logger.warning(f"MIME type {mime_type} is not compatible with OCR processing type {ocr_processing_type}")
            return False
    
    return True


@file_operation_decorator
def is_valid_document_for_type(file_path: str, document_type: str) -> bool:
    """
    Check if a file is valid for a specific document type.
    
    Args:
        file_path: Path to the file
        document_type: Document type to validate against
        
    Returns:
        bool: True if the file is valid for the document type, False otherwise
    """
    # Check if the document type is valid
    if document_type not in [dt.value for dt in DocumentType]:
        logger.warning(f"Invalid document type: {document_type}")
        return False
    
    # Get the MIME type of the file
    mime_type = get_mime_type(file_path)
    
    # Check if the MIME type is supported for the document type
    compatible_mime_types = DOCUMENT_TYPE_MIME_MAPPING.get(document_type, [])
    if mime_type not in compatible_mime_types:
        logger.warning(f"MIME type {mime_type} is not compatible with document type {document_type}")
        return False
    
    return True


@file_operation_decorator
def create_document_metadata(file_path: str, document_type: Optional[str] = None) -> DocumentMetadata:
    """
    Create document metadata for a file.
    
    Args:
        file_path: Path to the file
        document_type: Optional document type
        
    Returns:
        DocumentMetadata: Document metadata object
    """
    metadata = get_file_metadata(file_path)
    
    # Create DocumentMetadata object
    document_metadata = {
        'id': str(uuid.uuid4()),
        'filename': metadata['file_name'],
        'size': metadata['file_size'],
        'mime_type': metadata['mime_type'],
        'created_at': datetime.datetime.fromtimestamp(metadata['created_at']),
        'updated_at': datetime.datetime.fromtimestamp(metadata['modified_at']),
        'classification_confidence': None,
        'ocr_confidence': None,
        'application_id': None,
        'storage_path': None,
        'checksum': calculate_file_hash(file_path),
        'page_count': get_document_page_count(file_path),
        'tags': []
    }
    
    return document_metadata


@file_operation_decorator
def get_document_page_count(file_path: str) -> Optional[int]:
    """
    Get the number of pages in a document.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Optional[int]: Number of pages in the document, or None if unable to determine
    """
    mime_type = get_mime_type(file_path)
    
    # For PDF documents, use PyPDF2 to count pages if available
    if mime_type == 'application/pdf':
        try:
            from PyPDF2 import PdfReader
            
            with open(file_path, 'rb') as f:
                pdf_reader = PdfReader(f)
                return len(pdf_reader.pages)
        except ImportError:
            logger.warning("PyPDF2 not available for page count detection")
        except Exception as e:
            logger.warning(f"Error detecting PDF page count: {str(e)}")
    
    # For TIFF images, use PIL/Pillow to count pages if available
    elif mime_type == 'image/tiff':
        try:
            from PIL import Image
            
            with Image.open(file_path) as img:
                # Count frames in the TIFF file
                page_count = 0
                try:
                    while True:
                        page_count += 1
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass  # End of frames
                
                return page_count
        except ImportError:
            logger.warning("PIL/Pillow not available for TIFF page count detection")
        except Exception as e:
            logger.warning(f"Error detecting TIFF page count: {str(e)}")
    
    # For other image formats, assume single page
    elif mime_type in ['image/jpeg', 'image/png']:
        return 1
    
    # Unable to determine page count
    return None


@file_operation_decorator
def split_pdf_into_pages(pdf_path: str, output_dir: str) -> List[str]:
    """
    Split a PDF document into individual pages.
    
    Args:
        pdf_path: Path to the PDF document
        output_dir: Directory to save the individual pages
        
    Returns:
        List[str]: List of paths to the individual page files
    """
    try:
        from PyPDF2 import PdfReader, PdfWriter
        
        # Ensure the output directory exists
        ensure_directory_exists(output_dir)
        
        # Open the PDF file
        with open(pdf_path, 'rb') as f:
            pdf_reader = PdfReader(f)
            page_count = len(pdf_reader.pages)
            
            # Create a list to store the paths to the individual page files
            page_paths = []
            
            # Extract each page and save it as a separate PDF file
            for page_num in range(page_count):
                pdf_writer = PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[page_num])
                
                # Generate a filename for the page
                page_filename = f"page_{page_num + 1}.pdf"
                page_path = os.path.join(output_dir, page_filename)
                
                # Save the page to a file
                with open(page_path, 'wb') as page_file:
                    pdf_writer.write(page_file)
                
                page_paths.append(page_path)
            
            return page_paths
    except ImportError:
        logger.warning("PyPDF2 not available for PDF splitting")
        raise ServiceError("PyPDF2 not available for PDF splitting")
    except Exception as e:
        logger.error(f"Error splitting PDF: {str(e)}")
        raise ServiceError(f"Error splitting PDF: {str(e)}")


@file_operation_decorator
def extract_images_from_pdf(pdf_path: str, output_dir: str) -> List[str]:
    """
    Extract images from a PDF document.
    
    Args:
        pdf_path: Path to the PDF document
        output_dir: Directory to save the extracted images
        
    Returns:
        List[str]: List of paths to the extracted image files
    """
    try:
        import fitz  # PyMuPDF
        
        # Ensure the output directory exists
        ensure_directory_exists(output_dir)
        
        # Open the PDF file
        pdf_document = fitz.open(pdf_path)
        
        # Create a list to store the paths to the extracted image files
        image_paths = []
        
        # Extract images from each page
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            
            # Get the images on the page
            image_list = page.get_images(full=True)
            
            # Process each image
            for img_index, img in enumerate(image_list):
                xref = img[0]  # Image reference number
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                
                # Generate a filename for the image
                image_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                image_path = os.path.join(output_dir, image_filename)
                
                # Save the image to a file
                with open(image_path, 'wb') as img_file:
                    img_file.write(image_bytes)
                
                image_paths.append(image_path)
        
        return image_paths
    except ImportError:
        logger.warning("PyMuPDF not available for PDF image extraction")
        raise ServiceError("PyMuPDF not available for PDF image extraction")
    except Exception as e:
        logger.error(f"Error extracting images from PDF: {str(e)}")
        raise ServiceError(f"Error extracting images from PDF: {str(e)}")


@file_operation_decorator
def convert_pdf_to_images(pdf_path: str, output_dir: str, dpi: int = 300, format: str = 'png') -> List[str]:
    """
    Convert a PDF document to a series of images.
    
    Args:
        pdf_path: Path to the PDF document
        output_dir: Directory to save the converted images
        dpi: Resolution in dots per inch (default: 300)
        format: Output image format (default: png)
        
    Returns:
        List[str]: List of paths to the converted image files
    """
    try:
        from pdf2image import convert_from_path
        
        # Ensure the output directory exists
        ensure_directory_exists(output_dir)
        
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi)
        
        # Create a list to store the paths to the converted image files
        image_paths = []
        
        # Save each image
        for i, image in enumerate(images):
            # Generate a filename for the image
            image_filename = f"page_{i + 1}.{format}"
            image_path = os.path.join(output_dir, image_filename)
            
            # Save the image to a file
            image.save(image_path, format.upper())
            
            image_paths.append(image_path)
        
        return image_paths
    except ImportError:
        logger.warning("pdf2image not available for PDF to image conversion")
        raise ServiceError("pdf2image not available for PDF to image conversion")
    except Exception as e:
        logger.error(f"Error converting PDF to images: {str(e)}")
        raise ServiceError(f"Error converting PDF to images: {str(e)}")


@file_operation_decorator
def prepare_document_for_ocr(file_path: str, temp_dir: str) -> List[str]:
    """
    Prepare a document for OCR processing by converting it to a format suitable for OCR.
    
    Args:
        file_path: Path to the document file
        temp_dir: Directory to store temporary files
        
    Returns:
        List[str]: List of paths to the prepared files
    """
    # Get the MIME type of the file
    mime_type = get_mime_type(file_path)
    
    # Create a temporary directory for the prepared files
    prep_dir = os.path.join(temp_dir, f"ocr_prep_{uuid.uuid4().hex}")
    ensure_directory_exists(prep_dir)
    
    # Process based on MIME type
    if mime_type == 'application/pdf':
        # For PDFs, convert to images for better OCR results
        try:
            return convert_pdf_to_images(file_path, prep_dir)
        except Exception as e:
            logger.warning(f"Error converting PDF to images: {str(e)}. Falling back to PDF splitting.")
            return split_pdf_into_pages(file_path, prep_dir)
    
    elif mime_type == 'image/tiff':
        # For multi-page TIFF, split into individual pages
        try:
            from PIL import Image
            
            # Open the TIFF file
            with Image.open(file_path) as img:
                # Count frames in the TIFF file
                page_count = 0
                try:
                    while True:
                        page_count += 1
                        img.seek(img.tell() + 1)
                except EOFError:
                    pass  # End of frames
            
            # If it's a multi-page TIFF, split it
            if page_count > 1:
                # Create a list to store the paths to the individual page files
                page_paths = []
                
                # Open the TIFF file again
                with Image.open(file_path) as img:
                    # Extract each page
                    for i in range(page_count):
                        img.seek(i)
                        
                        # Generate a filename for the page
                        page_filename = f"page_{i + 1}.tiff"
                        page_path = os.path.join(prep_dir, page_filename)
                        
                        # Save the page to a file
                        img.save(page_path)
                        
                        page_paths.append(page_path)
                
                return page_paths
            else:
                # If it's a single-page TIFF, just copy it
                dest_path = os.path.join(prep_dir, os.path.basename(file_path))
                copy_file(file_path, dest_path)
                return [dest_path]
        except ImportError:
            logger.warning("PIL/Pillow not available for TIFF splitting")
            # If PIL/Pillow is not available, just copy the file
            dest_path = os.path.join(prep_dir, os.path.basename(file_path))
            copy_file(file_path, dest_path)
            return [dest_path]
        except Exception as e:
            logger.warning(f"Error splitting TIFF: {str(e)}. Using original file.")
            # If there's an error, just copy the file
            dest_path = os.path.join(prep_dir, os.path.basename(file_path))
            copy_file(file_path, dest_path)
            return [dest_path]
    
    else:
        # For other image formats, just copy the file
        dest_path = os.path.join(prep_dir, os.path.basename(file_path))
        copy_file(file_path, dest_path)
        return [dest_path]


@file_operation_decorator
def save_extracted_data_as_json(data: Dict[str, Any], output_path: str) -> None:
    """
    Save extracted OCR data as a JSON file.
    
    Args:
        data: Extracted data to save
        output_path: Path to save the JSON file
        
    Returns:
        None
    """
    import json
    
    # Ensure the directory exists
    ensure_directory_exists(os.path.dirname(output_path))
    
    # Save the data as JSON
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@file_operation_decorator
def load_json_data(file_path: str) -> Dict[str, Any]:
    """
    Load JSON data from a file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dict[str, Any]: Loaded JSON data
    """
    import json
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


@file_operation_decorator
def create_s3_key_for_document(document_id: str, document_type: str, filename: str) -> str:
    """
    Create an S3 key for storing a document.
    
    Args:
        document_id: Document ID
        document_type: Document type
        filename: Original filename
        
    Returns:
        str: S3 key for the document
    """
    # Get the file extension
    ext = get_file_extension(filename)
    
    # Create a key in the format: documents/{document_type}/{document_id}{ext}
    return f"documents/{document_type}/{document_id}{ext}"


@file_operation_decorator
def create_s3_key_for_extracted_data(document_id: str, document_type: str) -> str:
    """
    Create an S3 key for storing extracted data.
    
    Args:
        document_id: Document ID
        document_type: Document type
        
    Returns:
        str: S3 key for the extracted data
    """
    # Create a key in the format: extracted/{document_type}/{document_id}.json
    return f"extracted/{document_type}/{document_id}.json"