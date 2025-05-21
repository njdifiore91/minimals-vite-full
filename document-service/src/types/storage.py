"""
Type definitions for S3-compatible storage operations in the Document Service.

This module provides type hints for S3 client configuration, storage operations,
bucket configurations, and document metadata for the Document Service. These types
ensure type safety when interacting with the S3-compatible storage for storing
classified documents.

The module includes:
- S3ClientConfig: Type for S3 connection parameters
- StorageOptions: Type for configuring encryption and access controls
- StorageMetadata: Type for document storage metadata
- BucketConfig: Type for environment-specific bucket configurations
- StorageResult: Type for operation results and error handling
- StorageKey: Type for generating consistent storage keys
- PresignedUrlOptions: Type for generating presigned URLs for secure document access

These type definitions support the Document Service's requirement to store documents
in S3-compatible storage with AES-256 encryption and proper metadata for classification.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Dict, List, Optional, TypedDict, Union, Generic, TypeVar

# Type variable for generic result type
T = TypeVar('T')


class EncryptionType(Enum):
    """Encryption types supported for S3 storage.
    
    As specified in section 0.2.5, AES-256 encryption is required for document storage.
    """
    AES256 = 'AES256'  # Default encryption type as per technical specification
    AWS_KMS = 'aws:kms'
    NONE = 'none'


class StorageClass(Enum):
    """Storage classes available for S3 objects."""
    STANDARD = 'STANDARD'
    REDUCED_REDUNDANCY = 'REDUCED_REDUNDANCY'
    STANDARD_IA = 'STANDARD_IA'
    ONEZONE_IA = 'ONEZONE_IA'
    INTELLIGENT_TIERING = 'INTELLIGENT_TIERING'
    GLACIER = 'GLACIER'
    DEEP_ARCHIVE = 'DEEP_ARCHIVE'


class S3ClientConfig(TypedDict):
    """
    Configuration for S3 client connection.
    
    This configuration is used to establish a connection to the S3-compatible storage
    service for storing and retrieving documents. It includes authentication credentials,
    connection parameters, and retry settings.
    
    Attributes:
        endpoint_url: The S3-compatible storage endpoint URL
        region_name: AWS region name
        aws_access_key_id: AWS access key ID
        aws_secret_access_key: AWS secret access key
        use_ssl: Whether to use SSL for the connection (should be True for security)
        verify: Path to a CA bundle or False to disable verification
        max_pool_connections: Maximum number of connections to keep in the connection pool
        timeout: Connection timeout in seconds
        retries: Number of times to retry failed requests (as per section 0.2.3 retry logic)
    """
    endpoint_url: str
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    use_ssl: bool
    verify: Union[bool, str]
    max_pool_connections: int
    timeout: int
    retries: int


class StorageOptions(TypedDict, total=False):
    """
    Options for S3 storage operations.
    
    These options configure how documents are stored in the S3-compatible storage.
    As specified in section 0.2.5, documents must use AES-256 encryption.
    
    Attributes:
        encryption: Encryption type to use for the object (should be AES256 as per section 0.2.5)
        kms_key_id: KMS key ID to use for encryption (if encryption is AWS_KMS)
        storage_class: Storage class to use for the object
        metadata: User-defined metadata for the object, including classification metadata
        content_type: Content type of the object
        content_disposition: Content disposition of the object
        cache_control: Cache control directives for the object
        content_encoding: Content encoding of the object
        content_language: Content language of the object
        expires: Expiration date for the object
        website_redirect_location: Website redirect location for the object
        tagging: Object tags as a URL-encoded string
        acl: Canned ACL to apply to the object (should restrict access appropriately)
    """
    encryption: EncryptionType
    kms_key_id: Optional[str]
    storage_class: StorageClass
    metadata: Dict[str, str]
    content_type: str
    content_disposition: str
    cache_control: str
    content_encoding: str
    content_language: str
    expires: str
    website_redirect_location: str
    tagging: str
    acl: str


class DocumentType(Enum):
    """Types of documents that can be processed by the Document Service."""
    APPLICATION = auto()
    TAX_RETURN = auto()
    BANK_STATEMENT = auto()
    PAY_STUB = auto()
    ID_DOCUMENT = auto()
    BUSINESS_LICENSE = auto()
    FINANCIAL_STATEMENT = auto()
    UTILITY_BILL = auto()
    LEASE_AGREEMENT = auto()
    INSURANCE_POLICY = auto()
    OTHER = auto()


class StorageMetadata(TypedDict):
    """
    Metadata for documents stored in S3.
    
    As specified in section 0.1.3, documents must be stored with classification metadata.
    This type provides the structure for that metadata.
    
    Attributes:
        document_id: Unique identifier for the document
        application_id: ID of the application this document belongs to
        document_type: Type of document (e.g., application, tax_return)
        classification_confidence: Confidence score of the document classification (0.0-1.0)
        content_type: MIME type of the document
        original_filename: Original filename of the document
        upload_timestamp: Timestamp when the document was uploaded (ISO 8601 format)
        size_bytes: Size of the document in bytes
        version: Version of the document
        checksum: MD5 checksum of the document
        encrypted: Whether the document is encrypted (should always be True with AES-256)
        classification_model: Model used for document classification (e.g., 'svm', 'random_forest')
        classification_model_version: Version of the classification model
        review_required: Whether human review is required based on confidence threshold
    """
    document_id: str
    application_id: str
    document_type: str
    classification_confidence: float
    content_type: str
    original_filename: str
    upload_timestamp: str
    size_bytes: int
    version: str
    checksum: str
    encrypted: bool
    classification_model: str
    classification_model_version: str
    review_required: bool


@dataclass
class BucketConfig:
    """
    Configuration for S3 buckets.
    
    As specified in section 0.2.5, the system uses the following buckets:
    - 'mca-documents-production'
    - 'mca-documents-staging'
    
    Attributes:
        name: Name of the bucket
        region: AWS region where the bucket is located
        encryption: Default encryption configuration for the bucket (AES-256 as per section 0.2.5)
        versioning: Whether versioning is enabled for the bucket
        lifecycle_rules: Lifecycle rules for the bucket
        cors_rules: CORS rules for the bucket
        public_access_blocked: Whether public access is blocked for the bucket (should be True for security)
    """
    name: str
    region: str
    encryption: EncryptionType = EncryptionType.AES256
    versioning: bool = True
    lifecycle_rules: Optional[List[Dict[str, Any]]] = None
    cors_rules: Optional[List[Dict[str, Any]]] = None
    public_access_blocked: bool = True


class StorageErrorCode(Enum):
    """Error codes for storage operations."""
    CONNECTION_ERROR = 'CONNECTION_ERROR'
    AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR'
    PERMISSION_DENIED = 'PERMISSION_DENIED'
    BUCKET_NOT_FOUND = 'BUCKET_NOT_FOUND'
    OBJECT_NOT_FOUND = 'OBJECT_NOT_FOUND'
    INVALID_KEY = 'INVALID_KEY'
    ENCRYPTION_ERROR = 'ENCRYPTION_ERROR'
    UPLOAD_ERROR = 'UPLOAD_ERROR'
    DOWNLOAD_ERROR = 'DOWNLOAD_ERROR'
    DELETE_ERROR = 'DELETE_ERROR'
    TIMEOUT_ERROR = 'TIMEOUT_ERROR'
    STORAGE_ERROR = 'STORAGE_ERROR'  # Generic error


class StorageError(Exception):
    """Base exception for storage-related errors.
    
    This exception class provides structured error information for storage operations,
    including an error code, message, and additional details for troubleshooting.
    """
    def __init__(self, 
                 message: str, 
                 code: Union[StorageErrorCode, str] = StorageErrorCode.STORAGE_ERROR, 
                 details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code if isinstance(code, str) else code.value
        self.details = details or {}
        super().__init__(message)


class StorageResult(Generic[T]):
    """
    Result of a storage operation.
    
    As specified in section 0.2.3, the service must handle storage errors and implement retry logic.
    This class provides a standardized way to handle operation results and track retry attempts.
    
    Attributes:
        success: Whether the operation was successful
        data: Result data if the operation was successful
        error: Error information if the operation failed
        retry_count: Number of retries performed for the operation
    """
    def __init__(
        self, 
        success: bool, 
        data: Optional[T] = None, 
        error: Optional[Union[StorageError, Exception]] = None,
        retry_count: int = 0
    ):
        self.success = success
        self.data = data
        self.error = error
        self.retry_count = retry_count

    @property
    def failed(self) -> bool:
        """Returns True if the operation failed."""
        return not self.success


class StorageKey:
    """
    Utility class for generating and parsing S3 storage keys.
    
    This class ensures consistent key generation for document storage, following the pattern:
    {application_id}/{document_type}/{document_id}/{version}
    
    This hierarchical structure allows for efficient organization and retrieval of documents
    based on application ID and document type.
    
    Attributes:
        application_id: ID of the application
        document_id: ID of the document
        document_type: Type of document
        version: Version of the document
    """
    def __init__(
        self,
        application_id: str,
        document_id: str,
        document_type: str,
        version: str = 'v1'
    ):
        self.application_id = application_id
        self.document_id = document_id
        self.document_type = document_type
        self.version = version

    def to_string(self) -> str:
        """Convert the storage key to a string."""
        return f"{self.application_id}/{self.document_type}/{self.document_id}/{self.version}"

    @classmethod
    def from_string(cls, key_string: str) -> 'StorageKey':
        """Create a StorageKey from a string."""
        parts = key_string.split('/')
        if len(parts) != 4:
            raise ValueError(f"Invalid storage key format: {key_string}")
        
        return cls(
            application_id=parts[0],
            document_type=parts[1],
            document_id=parts[2],
            version=parts[3]
        )


class PresignedUrlOptions(TypedDict, total=False):
    """
    Options for generating presigned URLs.
    
    As specified in section 3.5.3, the system uses signed URLs with short expiration times
    for secure document access. This type provides configuration options for those URLs.
    
    Attributes:
        expires_in: Expiration time in seconds (should be short for security)
        response_content_type: Content type to return in the response
        response_content_disposition: Content disposition to return in the response
        response_content_language: Content language to return in the response
        response_content_encoding: Content encoding to return in the response
        response_cache_control: Cache control to return in the response
        response_expires: Expiration date to return in the response
    """
    expires_in: int
    response_content_type: str
    response_content_disposition: str
    response_content_language: str
    response_content_encoding: str
    response_cache_control: str
    response_expires: str