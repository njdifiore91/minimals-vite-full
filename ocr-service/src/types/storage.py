"""
Type definitions for S3-compatible storage operations used by the OCR Service.

This module provides type hints for securely storing OCR results and accessing 
documents in the S3-compatible storage with AES-256 encryption. It includes types 
for S3 client configuration, storage operations, and document metadata.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Generic, List, Literal, Optional, TypedDict, TypeVar, Union


class S3ClientConfig(TypedDict):
    """
    Configuration parameters for S3 client connection.
    
    All parameters are required for establishing a connection to the S3-compatible storage.
    """
    
    endpoint_url: str  # The endpoint URL of the S3-compatible storage service
    region_name: str  # AWS region name (e.g., 'us-east-1')
    aws_access_key_id: str  # Access key ID for authentication
    aws_secret_access_key: str  # Secret access key for authentication
    use_ssl: bool  # Whether to use SSL for the connection (should be True in production)
    verify: Union[bool, str]  # SSL certificate verification (True, False, or path to CA bundle)
    signature_version: str  # S3 signature version (e.g., 's3v4')


class StorageOptions(TypedDict, total=False):
    """
    Configuration options for S3 storage operations.
    
    These options control encryption, access controls, and other storage-specific settings.
    The 'total=False' parameter indicates that all fields are optional.
    """
    
    ServerSideEncryption: Literal['AES256', 'aws:kms']  # Server-side encryption algorithm
    SSEKMSKeyId: Optional[str]  # KMS key ID for aws:kms encryption
    ContentType: str  # MIME type of the stored object
    ContentDisposition: str  # Content disposition header
    CacheControl: str  # Cache control header
    Metadata: Dict[str, str]  # User-defined metadata for the object
    ACL: str  # Access control list (e.g., 'private', 'public-read')
    StorageClass: str  # Storage class (e.g., 'STANDARD', 'REDUCED_REDUNDANCY')


class StorageMetadata(TypedDict):
    """
    Metadata for documents stored in S3.
    
    This metadata is stored alongside the document in S3 and can be used for searching,
    filtering, and tracking document processing status.
    """
    
    document_id: str  # Unique identifier for the document
    application_id: str  # ID of the application this document belongs to
    document_type: str  # Type of document (e.g., 'application', 'tax_return')
    content_type: str  # MIME type of the document
    original_filename: str  # Original filename of the document
    upload_timestamp: str  # ISO 8601 timestamp of when the document was uploaded
    processing_status: str  # Status of OCR processing (e.g., 'pending', 'completed')
    confidence_score: float  # Overall confidence score of OCR extraction (0.0-1.0)
    page_count: int  # Number of pages in the document
    file_size: int  # Size of the document in bytes


class BucketConfig(TypedDict):
    """
    Configuration for S3 buckets in different environments.
    
    This type defines the bucket names and configurations for different environments
    (development, staging, production) to ensure consistent bucket naming and settings.
    """
    
    name: str  # Bucket name (e.g., 'mca-documents-production')
    region: str  # AWS region for the bucket
    encryption: Literal['AES256', 'aws:kms']  # Default encryption for the bucket
    kms_key_id: Optional[str]  # KMS key ID for aws:kms encryption
    versioning: bool  # Whether versioning is enabled for the bucket
    lifecycle_rules: List[Dict[str, Any]]  # Lifecycle rules for the bucket
    cors_rules: List[Dict[str, Any]]  # CORS rules for the bucket
    public_access_blocked: bool  # Whether public access is blocked for the bucket


# Define a generic type variable for the result value
T = TypeVar('T')


@dataclass
class StorageResult(Generic[T]):
    """
    Result of a storage operation with error handling.
    
    This class provides a standardized way to handle the results of storage operations,
    including success/failure status, error messages, and retry information.
    """
    
    success: bool  # Whether the operation was successful
    value: Optional[T]  # The result value if successful, None otherwise
    error: Optional[Exception]  # The exception if an error occurred, None otherwise
    error_message: Optional[str]  # Human-readable error message if an error occurred
    retry_count: int = 0  # Number of retry attempts made
    max_retries: int = 3  # Maximum number of retry attempts
    retry_after: Optional[float] = None  # Seconds to wait before retrying
    
    @property
    def should_retry(self) -> bool:
        """
        Determine if the operation should be retried.
        
        Returns:
            bool: True if the operation should be retried, False otherwise
        """
        return not self.success and self.retry_count < self.max_retries


class StorageErrorType(enum.Enum):
    """
    Types of storage errors that can occur during S3 operations.
    
    These error types help categorize and handle different types of storage errors
    in a consistent way throughout the application.
    """
    
    CONNECTION_ERROR = "connection_error"  # Error connecting to S3
    AUTHENTICATION_ERROR = "authentication_error"  # Authentication failed
    PERMISSION_ERROR = "permission_error"  # Insufficient permissions
    NOT_FOUND_ERROR = "not_found_error"  # Object or bucket not found
    ALREADY_EXISTS_ERROR = "already_exists_error"  # Object or bucket already exists
    ENCRYPTION_ERROR = "encryption_error"  # Error with encryption/decryption
    VALIDATION_ERROR = "validation_error"  # Invalid input or configuration
    TIMEOUT_ERROR = "timeout_error"  # Operation timed out
    THROTTLING_ERROR = "throttling_error"  # Request throttled by S3
    INTERNAL_ERROR = "internal_error"  # Internal server error
    UNKNOWN_ERROR = "unknown_error"  # Unknown error


class DocumentType(enum.Enum):
    """
    Types of documents that can be stored in S3.
    
    These document types are used for organizing documents in S3 and for
    determining the appropriate OCR processing pipeline.
    """
    
    APPLICATION = "application"  # Loan application documents
    TAX_RETURN = "tax_return"  # Tax return documents
    BANK_STATEMENT = "bank_statement"  # Bank statement documents
    PAY_STUB = "pay_stub"  # Pay stub documents
    ID_DOCUMENT = "id_document"  # ID documents (driver's license, passport, etc.)
    BUSINESS_LICENSE = "business_license"  # Business license documents
    UTILITY_BILL = "utility_bill"  # Utility bill documents
    OTHER = "other"  # Other documents


class StorageKey:
    """
    Utility class for generating consistent storage keys for S3 objects.
    
    This class provides methods for generating storage keys with consistent
    naming conventions based on document type, application ID, and timestamp.
    """
    
    @staticmethod
    def generate(document_type: Union[DocumentType, str], application_id: str, 
                document_id: str, timestamp: Optional[datetime] = None) -> str:
        """
        Generate a storage key for an S3 object.
        
        Args:
            document_type: Type of document (DocumentType enum or string)
            application_id: ID of the application this document belongs to
            document_id: Unique identifier for the document
            timestamp: Optional timestamp to include in the key
            
        Returns:
            A formatted storage key string
        """
        if timestamp is None:
            timestamp = datetime.now()
            
        date_str = timestamp.strftime('%Y/%m/%d')
        
        # Convert DocumentType enum to string if needed
        if isinstance(document_type, DocumentType):
            document_type = document_type.value
            
        return f"{document_type}/{date_str}/{application_id}/{document_id}"
    
    @staticmethod
    def generate_ocr_result_key(document_key: str) -> str:
        """
        Generate a storage key for OCR results based on the original document key.
        
        Args:
            document_key: The storage key of the original document
            
        Returns:
            A storage key for the OCR results
        """
        return f"{document_key}/ocr_results.json"
    
    @staticmethod
    def generate_thumbnail_key(document_key: str, page: int = 1) -> str:
        """
        Generate a storage key for a document thumbnail based on the original document key.
        
        Args:
            document_key: The storage key of the original document
            page: The page number to generate a thumbnail for
            
        Returns:
            A storage key for the thumbnail
        """
        return f"{document_key}/thumbnails/page_{page}.jpg"


# Default storage options with AES-256 encryption
DEFAULT_STORAGE_OPTIONS: StorageOptions = {
    'ServerSideEncryption': 'AES256',
    'ContentType': 'application/octet-stream',
    'ACL': 'private',
}


# Environment-specific bucket configurations
BUCKET_CONFIGS: Dict[str, BucketConfig] = {
    'development': {
        'name': 'mca-documents-development',
        'region': 'us-east-1',
        'encryption': 'AES256',
        'kms_key_id': None,
        'versioning': True,
        'lifecycle_rules': [],
        'cors_rules': [],
        'public_access_blocked': True,
    },
    'staging': {
        'name': 'mca-documents-staging',
        'region': 'us-east-1',
        'encryption': 'AES256',
        'kms_key_id': None,
        'versioning': True,
        'lifecycle_rules': [],
        'cors_rules': [],
        'public_access_blocked': True,
    },
    'production': {
        'name': 'mca-documents-production',
        'region': 'us-east-1',
        'encryption': 'AES256',
        'kms_key_id': None,
        'versioning': True,
        'lifecycle_rules': [],
        'cors_rules': [],
        'public_access_blocked': True,
    },
}