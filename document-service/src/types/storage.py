"""
Type definitions for S3-compatible storage operations used by the Document Service.

This module provides type hints for securely storing classified documents in S3-compatible storage
with AES-256 encryption. It includes types for S3 client configuration, storage operations,
document metadata, and error handling.

Example usage:
    ```python
    from document_service.types.storage import S3ClientConfig, StorageOptions, StorageMetadata
    
    # Configure S3 client
    config: S3ClientConfig = {
        'endpoint_url': 'https://s3.amazonaws.com',
        'region_name': 'us-east-1',
        'credentials': {
            'access_key': 'ACCESS_KEY',
            'secret_key': 'SECRET_KEY',
            'session_token': None
        },
        'verify': True
    }
    
    # Configure storage options with AES-256 encryption
    options: StorageOptions = {
        'encryption': {
            'algorithm': 'AES256',
            'kms_key_id': None
        },
        'content_type': 'application/pdf',
        'metadata': {
            'application-id': '12345',
            'document-type': 'invoice'
        }
    }
    ```

All storage operations should use these type definitions to ensure type safety
and consistent handling of storage-related operations throughout the Document Service.
"""

from typing import Dict, List, Optional, TypedDict, Union, Any, Literal, Protocol, Callable
from datetime import datetime
from pathlib import Path
from io import BufferedReader, BytesIO


class S3Credentials(TypedDict):
    """Type definition for S3 credentials."""
    access_key: str
    secret_key: str
    session_token: Optional[str]


class S3ClientConfig(TypedDict):
    """
    Type definition for S3 client configuration parameters.
    
    Used to establish connection to S3-compatible storage service.
    """
    endpoint_url: str
    region_name: str
    credentials: S3Credentials
    verify: Union[bool, str]  # Can be a boolean or path to CA bundle


class EncryptionConfig(TypedDict):
    """
    Type definition for S3 encryption configuration.
    
    Supports AES-256 encryption as required in the technical specification.
    """
    algorithm: Literal['AES256']
    kms_key_id: Optional[str]  # Only used with KMS encryption


class StorageOptions(TypedDict, total=False):
    """
    Type definition for S3 storage options.
    
    Controls encryption, access permissions, and other storage parameters.
    The 'total=False' indicates all fields are optional.
    """
    encryption: EncryptionConfig
    content_type: str
    metadata: Dict[str, str]
    acl: str  # e.g., 'private', 'public-read'
    storage_class: str  # e.g., 'STANDARD', 'STANDARD_IA'
    cache_control: str
    content_disposition: str
    content_encoding: str
    content_language: str
    website_redirect_location: str
    tagging: str  # URL-encoded tag set


class DocumentClassification(TypedDict):
    """Type definition for document classification metadata."""
    category: str  # e.g., 'invoice', 'application_form', 'id_document'
    confidence: float  # Classification confidence score (0.0-1.0)
    model_version: str  # Version of the classification model used
    sub_categories: Optional[List[str]]  # Optional sub-categories
    classification_date: datetime  # When the document was classified
    classifier_id: str  # Identifier for the classifier used


class StorageMetadata(TypedDict):
    """
    Type definition for document storage metadata.
    
    Includes document classification, processing status, and timestamps.
    """
    document_id: str
    application_id: str
    filename: str
    file_size: int
    content_type: str
    classification: DocumentClassification
    upload_timestamp: datetime
    last_modified: datetime
    md5_hash: str
    processing_status: str  # e.g., 'pending', 'processed', 'failed'
    tags: Dict[str, str]
    custom_metadata: Dict[str, str]
    ocr_status: Optional[str]  # Status of OCR processing if applicable
    ocr_confidence: Optional[float]  # Overall OCR confidence score
    page_count: Optional[int]  # Number of pages in the document
    encryption_status: str  # e.g., 'encrypted', 'unencrypted'
    encryption_type: str  # e.g., 'AES256'
    storage_class: str  # e.g., 'STANDARD', 'STANDARD_IA'
    retention_period: Optional[int]  # Retention period in days
    legal_hold: bool  # Whether the document is under legal hold


class LifecycleTransition(TypedDict):
    """
    Type definition for S3 lifecycle transition rules.
    
    Controls when objects transition to different storage classes.
    """
    days: int  # Days after object creation
    storage_class: str  # Target storage class


class LifecycleExpiration(TypedDict):
    """
    Type definition for S3 lifecycle expiration rules.
    
    Controls when objects expire and are deleted.
    """
    days: int  # Days after object creation
    expired_object_delete_marker: bool


class LifecycleRule(TypedDict):
    """
    Type definition for S3 lifecycle rules.
    
    Controls object lifecycle management in S3 buckets.
    """
    id: str  # Rule identifier
    prefix: str  # Object key prefix
    status: Literal['Enabled', 'Disabled']
    transitions: List[LifecycleTransition]
    expiration: Optional[LifecycleExpiration]
    noncurrent_version_transitions: Optional[List[LifecycleTransition]]
    noncurrent_version_expiration: Optional[LifecycleExpiration]


class BucketConfig(TypedDict):
    """
    Type definition for environment-specific bucket configuration.
    
    Includes bucket names for different environments and default encryption settings.
    """
    name: str  # Bucket name
    region: str  # AWS region
    encryption: EncryptionConfig
    versioning_enabled: bool
    lifecycle_rules: List[LifecycleRule]
    cors_enabled: bool
    logging_enabled: bool
    logging_target_bucket: Optional[str]
    logging_target_prefix: Optional[str]
    public_access_blocked: bool
    object_lock_enabled: bool
    replication_enabled: bool
    replication_target: Optional[str]


class EnvironmentBuckets(TypedDict):
    """Type definition for environment-specific bucket configurations."""
    production: BucketConfig
    staging: BucketConfig
    development: BucketConfig


class StorageErrorDetail(TypedDict, total=False):
    """Type definition for detailed storage error information."""
    service: str  # Service that generated the error
    status_code: int  # HTTP status code
    operation: str  # Operation that failed
    sender_fault: bool  # True if the error was caused by the sender
    retry_attempts: int  # Number of retry attempts made


class StorageError(TypedDict):
    """Type definition for storage operation errors."""
    code: str  # Error code
    message: str  # Error message
    request_id: Optional[str]  # AWS request ID for tracing
    resource: Optional[str]  # Resource that caused the error
    details: Optional[StorageErrorDetail]  # Detailed error information
    timestamp: datetime  # When the error occurred
    recoverable: bool  # Whether the error is recoverable with a retry


class StorageResult(TypedDict):
    """
    Type definition for storage operation results.
    
    Includes success status, error information, and operation metadata.
    """
    success: bool
    error: Optional[StorageError]
    etag: Optional[str]  # Entity tag for the stored object
    version_id: Optional[str]  # Version ID if versioning is enabled
    storage_class: Optional[str]  # Storage class used
    metadata: Optional[Dict[str, str]]  # Object metadata
    encryption_status: Optional[str]  # Encryption status information


class StorageKey(TypedDict):
    """
    Type definition for generating consistent storage keys.
    
    Used to create deterministic paths for storing documents in S3.
    """
    application_id: str
    document_id: str
    document_type: str
    timestamp: str  # ISO format timestamp
    extension: str  # File extension


class RetryConfig(TypedDict):
    """
    Type definition for storage operation retry configuration.
    
    Controls retry behavior for failed storage operations.
    """
    max_attempts: int
    initial_delay_ms: int
    max_delay_ms: int
    backoff_factor: float  # Exponential backoff multiplier
    retryable_errors: List[str]  # Error codes that should trigger a retry


class StorageOperations(Protocol):
    """
    Protocol defining the interface for storage operations.
    
    Implementations must provide methods for uploading, downloading, and managing objects.
    """
    def upload_file(self, local_path: Union[str, Path], storage_key: str, 
                   options: Optional[StorageOptions] = None) -> StorageResult: ...
    
    def upload_fileobj(self, fileobj: Union[BufferedReader, BytesIO], storage_key: str,
                      options: Optional[StorageOptions] = None) -> StorageResult: ...
    
    def download_file(self, storage_key: str, local_path: Union[str, Path]) -> StorageResult: ...
    
    def download_fileobj(self, storage_key: str, fileobj: Union[BufferedReader, BytesIO]) -> StorageResult: ...
    
    def delete_file(self, storage_key: str) -> StorageResult: ...
    
    def copy_file(self, source_key: str, dest_key: str, 
                 options: Optional[StorageOptions] = None) -> StorageResult: ...
    
    def get_metadata(self, storage_key: str) -> Union[StorageMetadata, StorageResult]: ...
    
    def update_metadata(self, storage_key: str, metadata: Dict[str, str]) -> StorageResult: ...
    
    def generate_presigned_url(self, storage_key: str, expiration: int = 3600) -> str: ...


class StorageKeyGenerator(Protocol):
    """
    Protocol defining the interface for storage key generation.
    
    Implementations must provide a method for generating storage keys based on document metadata.
    """
    def generate_key(self, metadata: Dict[str, Any]) -> str: ...


# Type aliases for common storage operations
UploadFileCallback = Callable[[str, int, int], None]  # key, bytes_transferred, total_bytes
DownloadFileCallback = Callable[[str, int, int], None]  # key, bytes_transferred, total_bytes