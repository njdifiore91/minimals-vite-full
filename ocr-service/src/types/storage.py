"""Type definitions for S3-compatible storage operations used by the OCR Service.

This module provides type hints for S3 client configuration, storage operations,
bucket configurations, and document metadata. These types ensure type safety
for all storage operations in the OCR Service.

The OCR Service uses S3-compatible storage with AES-256 encryption to securely
store and retrieve documents for processing.
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Union, TypeVar, Generic, Any, Callable
from datetime import datetime, timedelta
import os
from pathlib import Path

# Bucket configurations for different environments
BUCKET_CONFIGS = {
    'development': {
        'name': 'mca-documents-development',
        'region': 'us-east-1',
        'versioning_enabled': True,
        'lifecycle_rules': [
            {
                'ID': 'Delete old versions',
                'Status': 'Enabled',
                'NoncurrentVersionExpiration': {'NoncurrentDays': 90}
            }
        ],
        'cors_rules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ],
        'encryption': 'AES256'
    },
    'staging': {
        'name': 'mca-documents-staging',
        'region': 'us-east-1',
        'versioning_enabled': True,
        'lifecycle_rules': [
            {
                'ID': 'Delete old versions',
                'Status': 'Enabled',
                'NoncurrentVersionExpiration': {'NoncurrentDays': 90}
            }
        ],
        'cors_rules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ],
        'encryption': 'AES256'
    },
    'production': {
        'name': 'mca-documents-production',
        'region': 'us-east-1',
        'versioning_enabled': True,
        'lifecycle_rules': [
            {
                'ID': 'Archive old versions',
                'Status': 'Enabled',
                'NoncurrentVersionTransition': {
                    'NoncurrentDays': 30,
                    'StorageClass': 'STANDARD_IA'
                },
                'NoncurrentVersionExpiration': {'NoncurrentDays': 2555}  # 7 years retention
            }
        ],
        'cors_rules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedOrigins': ['*'],
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ],
        'encryption': 'AES256'
    }
}


class StorageErrorCode(Enum):
    """Error codes for storage operations."""
    CONNECTION_ERROR = auto()
    AUTHENTICATION_ERROR = auto()
    PERMISSION_DENIED = auto()
    RESOURCE_NOT_FOUND = auto()
    BUCKET_NOT_FOUND = auto()
    OBJECT_NOT_FOUND = auto()
    INVALID_REQUEST = auto()
    TIMEOUT = auto()
    INTERNAL_ERROR = auto()
    UNKNOWN_ERROR = auto()


class EncryptionType(Enum):
    """Encryption types for S3 storage."""
    NONE = "NONE"
    AES256 = "AES256"  # Server-side encryption with Amazon S3-managed keys
    KMS = "aws:kms"    # Server-side encryption with AWS KMS-managed keys


class StorageClass(Enum):
    """Storage classes for S3 objects."""
    STANDARD = "STANDARD"
    REDUCED_REDUNDANCY = "REDUCED_REDUNDANCY"
    STANDARD_IA = "STANDARD_IA"  # Infrequent Access
    ONEZONE_IA = "ONEZONE_IA"    # One Zone Infrequent Access
    INTELLIGENT_TIERING = "INTELLIGENT_TIERING"
    GLACIER = "GLACIER"
    DEEP_ARCHIVE = "DEEP_ARCHIVE"


@dataclass
class S3Credentials:
    """Credentials for S3 authentication.
    
    Attributes:
        access_key: AWS access key ID
        secret_key: AWS secret access key
        session_token: AWS session token (optional)
    """
    access_key: str
    secret_key: str
    session_token: Optional[str] = None


@dataclass
class S3ClientConfig:
    """Configuration for S3 client.
    
    Attributes:
        endpoint_url: S3 endpoint URL
        region: AWS region
        credentials: S3 credentials
        verify_ssl: Whether to verify SSL certificates
        use_path_style: Whether to use path-style addressing
        max_pool_connections: Maximum number of connections in the connection pool
        timeout: Connection timeout in seconds
        retries: Maximum number of retries for failed operations
    """
    endpoint_url: str
    region: str
    credentials: S3Credentials
    verify_ssl: bool = True
    use_path_style: bool = False
    max_pool_connections: int = 10
    timeout: int = 60
    retries: int = 3


@dataclass
class StorageOptions:
    """Options for storage operations.
    
    Attributes:
        encryption: Encryption type to use
        storage_class: Storage class for the object
        metadata: Custom metadata to attach to the object
        content_type: Content type of the object
        content_disposition: Content disposition of the object
        cache_control: Cache control directives for the object
        tags: Tags to attach to the object
        acl: Access control list for the object
    """
    encryption: EncryptionType = EncryptionType.AES256
    storage_class: StorageClass = StorageClass.STANDARD
    metadata: Dict[str, str] = field(default_factory=dict)
    content_type: Optional[str] = None
    content_disposition: Optional[str] = None
    cache_control: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    acl: Optional[str] = None


@dataclass
class SignedUrlOptions:
    """Options for generating signed URLs.
    
    Attributes:
        expiration: Expiration time in seconds
        http_method: HTTP method for the URL
        content_type: Content type for PUT/POST requests
        content_disposition: Content disposition for PUT/POST requests
        response_headers: Response headers to override
    """
    expiration: int = 3600  # 1 hour default
    http_method: str = 'GET'
    content_type: Optional[str] = None
    content_disposition: Optional[str] = None
    response_headers: Dict[str, str] = field(default_factory=dict)


@dataclass
class BucketConfig:
    """Configuration for S3 bucket.
    
    Attributes:
        name: Bucket name
        region: AWS region for the bucket
        versioning_enabled: Whether versioning is enabled
        lifecycle_rules: Lifecycle rules for the bucket
        cors_rules: CORS rules for the bucket
        encryption: Default encryption for the bucket
    """
    name: str
    region: str
    versioning_enabled: bool = True
    lifecycle_rules: List[Dict[str, Any]] = field(default_factory=list)
    cors_rules: List[Dict[str, Any]] = field(default_factory=list)
    encryption: EncryptionType = EncryptionType.AES256


@dataclass
class StorageMetadata:
    """Metadata for stored documents.
    
    Attributes:
        document_id: Unique identifier for the document
        application_id: ID of the application this document belongs to
        document_type: Type of the document
        content_type: MIME type of the document
        original_filename: Original filename of the document
        size_bytes: Size of the document in bytes
        md5_hash: MD5 hash of the document content
        created_at: Timestamp when the document was created
        updated_at: Timestamp when the document was last updated
        version_id: S3 version ID if versioning is enabled
        extraction_status: Status of OCR extraction
        extraction_confidence: Overall confidence score of extraction
        tags: Custom tags for the document
        custom_metadata: Additional custom metadata
    """
    document_id: str
    application_id: str
    document_type: str
    content_type: str
    original_filename: str
    size_bytes: int
    md5_hash: str
    created_at: datetime
    updated_at: datetime
    version_id: Optional[str] = None
    extraction_status: Optional[str] = None
    extraction_confidence: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    custom_metadata: Dict[str, str] = field(default_factory=dict)
    
    def to_s3_metadata(self) -> Dict[str, str]:
        """Convert to S3 metadata format.
        
        Returns:
            Dict[str, str]: Metadata in S3 format
        """
        metadata = {
            'document-id': self.document_id,
            'application-id': self.application_id,
            'document-type': self.document_type,
            'original-filename': self.original_filename,
            'size-bytes': str(self.size_bytes),
            'md5-hash': self.md5_hash,
            'created-at': self.created_at.isoformat(),
            'updated-at': self.updated_at.isoformat(),
        }
        
        if self.version_id:
            metadata['version-id'] = self.version_id
            
        if self.extraction_status:
            metadata['extraction-status'] = self.extraction_status
            
        if self.extraction_confidence is not None:
            metadata['extraction-confidence'] = str(self.extraction_confidence)
            
        # Add custom metadata
        for key, value in self.custom_metadata.items():
            metadata[f'custom-{key}'] = value
            
        return metadata


T = TypeVar('T')  # Generic type for StorageResult


@dataclass
class StorageResult(Generic[T]):
    """Result of a storage operation.
    
    Attributes:
        success: Whether the operation was successful
        data: Result data if successful
        error_code: Error code if unsuccessful
        error_message: Error message if unsuccessful
        retry_count: Number of retries performed
        timestamp: Timestamp of the operation
    """
    success: bool
    data: Optional[T] = None
    error_code: Optional[StorageErrorCode] = None
    error_message: Optional[str] = None
    retry_count: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    
    @classmethod
    def success_result(cls, data: T) -> 'StorageResult[T]':
        """Create a successful result.
        
        Args:
            data: Result data
            
        Returns:
            StorageResult[T]: Successful result
        """
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, 
                    error_code: StorageErrorCode, 
                    error_message: str, 
                    retry_count: int = 0) -> 'StorageResult[T]':
        """Create an error result.
        
        Args:
            error_code: Error code
            error_message: Error message
            retry_count: Number of retries performed
            
        Returns:
            StorageResult[T]: Error result
        """
        return cls(
            success=False, 
            error_code=error_code, 
            error_message=error_message,
            retry_count=retry_count
        )


class StorageKey:
    """Utility class for generating and parsing storage keys."""
    
    @staticmethod
    def generate_key(application_id: str, document_id: str, document_type: str, 
                    filename: str) -> str:
        """Generate a storage key for a document.
        
        Args:
            application_id: Application ID
            document_id: Document ID
            document_type: Document type
            filename: Original filename
            
        Returns:
            str: Storage key
        """
        # Sanitize filename to remove problematic characters
        safe_filename = Path(filename).name
        
        # Format: applications/{application_id}/documents/{document_id}/{document_type}/{filename}
        return f"applications/{application_id}/documents/{document_id}/{document_type}/{safe_filename}"
    
    @staticmethod
    def parse_key(key: str) -> Dict[str, str]:
        """Parse a storage key into its components.
        
        Args:
            key: Storage key
            
        Returns:
            Dict[str, str]: Key components
        """
        parts = key.split('/')
        if len(parts) < 5 or parts[0] != 'applications' or parts[2] != 'documents':
            raise ValueError(f"Invalid storage key format: {key}")
            
        return {
            'application_id': parts[1],
            'document_id': parts[3],
            'document_type': parts[4],
            'filename': '/'.join(parts[5:]) if len(parts) > 5 else ''
        }
    
    @staticmethod
    def get_prefix(application_id: str, document_id: Optional[str] = None, 
                  document_type: Optional[str] = None) -> str:
        """Generate a prefix for listing objects.
        
        Args:
            application_id: Application ID
            document_id: Document ID (optional)
            document_type: Document type (optional)
            
        Returns:
            str: Prefix for listing objects
        """
        prefix = f"applications/{application_id}/"
        
        if document_id:
            prefix += f"documents/{document_id}/"
            
            if document_type:
                prefix += f"{document_type}/"
                
        return prefix