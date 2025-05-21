"""
Storage Service for OCR Service microservice.

This module provides S3-compatible storage operations for the OCR Service,
handling document retrieval, storage of OCR results, and management of document
metadata with secure AES-256 encryption.

The service implements the following key requirements:
1. S3 client connection with appropriate authentication
2. Document download functionality from specified buckets
3. AES-256 encryption for document storage
4. Error handling and retry logic for storage operations
5. Document metadata extraction and updating functionality
6. Versioning support for document history tracking
"""

import os
import json
import logging
import time
import hashlib
from typing import Dict, List, Optional, Union, BinaryIO, Tuple, Any
from datetime import datetime
from functools import wraps

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, ConnectionError, EndpointConnectionError

# Import type definitions
from ocr_service.types.storage import (
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult
)
from ocr_service.types.documents import DocumentMetadata
from ocr_service.types.errors import ServiceError

# Import configuration
from ocr_service.config import app_config, s3_config

# Configure logger
logger = logging.getLogger(__name__)


def with_retry(max_retries=3, base_delay=1.0, max_delay=30.0):
    """Decorator for implementing retry logic with exponential backoff.
    
    This decorator adds retry capability to storage operations that might
    fail due to transient network issues or service unavailability.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        
    Returns:
        Decorated function with retry capability
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except (ConnectionError, EndpointConnectionError) as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}: {str(e)}")
                        raise
                    
                    # Calculate delay with exponential backoff and jitter
                    delay = min(base_delay * (2 ** (retries - 1)), max_delay)
                    jitter = delay * 0.2 * (time.time() % 1)  # Add up to 20% jitter
                    sleep_time = delay + jitter
                    
                    logger.warning(f"Retry {retries}/{max_retries} for {func.__name__} after {sleep_time:.2f}s: {str(e)}")
                    time.sleep(sleep_time)
        return wrapper
    return decorator


class StorageService:
    """Service for handling S3-compatible storage operations.

    This service provides functionality for securely storing and retrieving
    documents from S3-compatible storage with AES-256 encryption, versioning
    support, and robust error handling.
    
    Key features:
    - AES-256 encryption for all stored documents
    - Versioning support for document history tracking
    - Robust error handling with exponential backoff retry logic
    - Environment-specific bucket configuration
    - Secure credential management
    - Document metadata management
    """

    def __init__(self, config: Optional[S3ClientConfig] = None):
        """Initialize the StorageService with the provided configuration.

        Args:
            config: Optional S3 client configuration. If not provided,
                   the default configuration from s3_config will be used.
        """
        self.config = config or s3_config.get_client_config()
        self.client = self._initialize_client()
        self.bucket_name = self._get_bucket_name()
        
    def _initialize_client(self):
        """Initialize the S3 client with appropriate configuration.
        
        Configures the S3 client with retry settings, timeouts, and credentials.
        Uses adaptive retry mode with exponential backoff for resilience.

        Returns:
            Configured boto3 S3 client
        """
        # Configure retry settings with exponential backoff
        boto_config = Config(
            retries={
                'max_attempts': self.config.max_retries,
                'mode': 'adaptive'  # Uses exponential backoff with rate limiting
            },
            connect_timeout=self.config.connect_timeout,
            read_timeout=self.config.read_timeout
        )
        
        # Initialize the S3 client with the configuration
        try:
            return boto3.client(
                's3',
                endpoint_url=self.config.endpoint_url,
                aws_access_key_id=self.config.access_key,
                aws_secret_access_key=self.config.secret_key,
                region_name=self.config.region,
                config=boto_config
            )
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise ServiceError(f"S3 client initialization failed: {str(e)}")
    
    def _get_bucket_name(self) -> str:
        """Get the appropriate bucket name based on the environment.
        
        Uses environment-specific bucket names from configuration:
        - Production: 'mca-documents-production'
        - Staging: 'mca-documents-staging'
        - Development: Development bucket name from config

        Returns:
            str: The bucket name for the current environment
        """
        env = app_config.ENVIRONMENT.lower()
        if env == 'production':
            return s3_config.PRODUCTION_BUCKET
        elif env == 'staging':
            return s3_config.STAGING_BUCKET
        else:
            return s3_config.DEVELOPMENT_BUCKET
    
    @with_retry(max_retries=5, base_delay=1.0, max_delay=30.0)
    def download_document(self, key: str, version_id: Optional[str] = None) -> StorageResult:
        """Download a document from S3 storage.

        Args:
            key: The document key in S3
            version_id: Optional version ID for retrieving a specific version

        Returns:
            StorageResult containing the document data and metadata
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            # Add version ID if specified for versioned retrieval
            if version_id:
                params['VersionId'] = version_id
                
            response = self.client.get_object(**params)
            
            # Extract document content and metadata
            content = response['Body'].read()
            metadata = self._extract_metadata(response)
            
            logger.info(f"Successfully downloaded document: {key}")
            return StorageResult(
                success=True,
                data=content,
                metadata=metadata,
                version_id=response.get('VersionId')
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to download document {key}: {error_code} - {error_message}")
            return StorageResult(
                success=False,
                error=f"S3 client error: {error_code} - {error_message}"
            )
        except ConnectionError as e:
            logger.error(f"Connection error while downloading document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"S3 connection error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while downloading document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    @with_retry(max_retries=5, base_delay=1.0, max_delay=30.0)
    def upload_document(self, key: str, data: Union[bytes, BinaryIO], 
                       metadata: Optional[Dict[str, str]] = None,
                       options: Optional[StorageOptions] = None) -> StorageResult:
        """Upload a document to S3 storage with AES-256 encryption.

        Args:
            key: The document key in S3
            data: The document data as bytes or file-like object
            metadata: Optional metadata to store with the document
            options: Optional storage options

        Returns:
            StorageResult indicating success or failure
        """
        try:
            # Prepare upload parameters with AES-256 encryption
            params = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': data,
                'ServerSideEncryption': 'AES256'  # Enable AES-256 encryption
            }
            
            # Add metadata if provided
            if metadata:
                params['Metadata'] = metadata
                
            # Add content type if provided in options
            if options and options.content_type:
                params['ContentType'] = options.content_type
                
            # Upload the document
            response = self.client.put_object(**params)
            
            logger.info(f"Successfully uploaded document: {key}")
            return StorageResult(
                success=True,
                version_id=response.get('VersionId'),
                etag=response.get('ETag')
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to upload document {key}: {error_code} - {error_message}")
            return StorageResult(
                success=False,
                error=f"S3 client error: {error_code} - {error_message}"
            )
        except ConnectionError as e:
            logger.error(f"Connection error while uploading document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"S3 connection error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while uploading document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    @with_retry(max_retries=5, base_delay=1.0, max_delay=30.0)
    def upload_extraction_results(self, document_key: str, extraction_data: Dict[str, Any],
                                confidence_scores: Dict[str, float]) -> StorageResult:
        """Upload OCR extraction results to S3 storage.

        Args:
            document_key: The original document key
            extraction_data: The extracted data from OCR processing
            confidence_scores: Confidence scores for extracted fields

        Returns:
            StorageResult indicating success or failure
        """
        # Generate a results key based on the original document key
        results_key = f"{document_key.rsplit('.', 1)[0]}_results.json"
        
        # Prepare the results data with metadata
        results = {
            "document_key": document_key,
            "extraction_timestamp": datetime.utcnow().isoformat(),
            "extracted_data": extraction_data,
            "confidence_scores": confidence_scores,
            "version": app_config.VERSION
        }
        
        # Convert to JSON and upload
        try:
            json_data = json.dumps(results).encode('utf-8')
            metadata = {
                "content-type": "application/json",
                "extraction-service": "ocr-service",
                "extraction-timestamp": datetime.utcnow().isoformat()
            }
            
            return self.upload_document(
                key=results_key,
                data=json_data,
                metadata=metadata,
                options=StorageOptions(content_type="application/json")
            )
        except Exception as e:
            logger.error(f"Failed to upload extraction results for {document_key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"Failed to upload extraction results: {str(e)}"
            )
    
    @with_retry(max_retries=3, base_delay=1.0, max_delay=15.0)
    def get_document_versions(self, key: str) -> StorageResult:
        """Get all versions of a document for audit purposes.

        Args:
            key: The document key in S3

        Returns:
            StorageResult containing a list of document versions
        """
        try:
            response = self.client.list_object_versions(
                Bucket=self.bucket_name,
                Prefix=key
            )
            
            versions = []
            if 'Versions' in response:
                for version in response['Versions']:
                    if version['Key'] == key:  # Filter to exact key match
                        versions.append({
                            'version_id': version['VersionId'],
                            'last_modified': version['LastModified'].isoformat(),
                            'is_latest': version['IsLatest'],
                            'size': version['Size']
                        })
            
            logger.info(f"Retrieved {len(versions)} versions for document: {key}")
            return StorageResult(
                success=True,
                data=versions
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to get versions for document {key}: {error_code} - {error_message}")
            return StorageResult(
                success=False,
                error=f"S3 client error: {error_code} - {error_message}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while getting versions for document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    @with_retry(max_retries=3, base_delay=1.0, max_delay=15.0)
    def update_document_metadata(self, key: str, metadata: Dict[str, str],
                               version_id: Optional[str] = None) -> StorageResult:
        """Update metadata for a document in S3 storage.

        Args:
            key: The document key in S3
            metadata: The metadata to update
            version_id: Optional version ID for updating a specific version

        Returns:
            StorageResult indicating success or failure
        """
        try:
            # First, get the current object to preserve its content
            get_params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            if version_id:
                get_params['VersionId'] = version_id
                
            current_object = self.client.get_object(**get_params)
            content = current_object['Body'].read()
            
            # Prepare the copy parameters with updated metadata
            params = {
                'Bucket': self.bucket_name,
                'Key': key,
                'Body': content,
                'Metadata': metadata,
                'MetadataDirective': 'REPLACE',
                'ServerSideEncryption': 'AES256'  # Maintain encryption
            }
            
            # Copy content type if it exists
            if 'ContentType' in current_object:
                params['ContentType'] = current_object['ContentType']
            
            # Upload the object with updated metadata
            response = self.client.put_object(**params)
            
            logger.info(f"Successfully updated metadata for document: {key}")
            return StorageResult(
                success=True,
                version_id=response.get('VersionId')
            )
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to update metadata for document {key}: {error_code} - {error_message}")
            return StorageResult(
                success=False,
                error=f"S3 client error: {error_code} - {error_message}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while updating metadata for document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    @with_retry(max_retries=3, base_delay=1.0, max_delay=15.0)
    def delete_document(self, key: str, version_id: Optional[str] = None) -> StorageResult:
        """Delete a document from S3 storage.

        Args:
            key: The document key in S3
            version_id: Optional version ID for deleting a specific version

        Returns:
            StorageResult indicating success or failure
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            # Add version ID if specified for versioned deletion
            if version_id:
                params['VersionId'] = version_id
                
            self.client.delete_object(**params)
            
            logger.info(f"Successfully deleted document: {key}")
            return StorageResult(success=True)
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"Failed to delete document {key}: {error_code} - {error_message}")
            return StorageResult(
                success=False,
                error=f"S3 client error: {error_code} - {error_message}"
            )
        except Exception as e:
            logger.error(f"Unexpected error while deleting document {key}: {str(e)}")
            return StorageResult(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )
    
    @with_retry(max_retries=3, base_delay=1.0, max_delay=10.0)
    def check_bucket_versioning(self) -> bool:
        """Check if versioning is enabled on the bucket.

        Returns:
            bool: True if versioning is enabled, False otherwise
        """
        try:
            response = self.client.get_bucket_versioning(
                Bucket=self.bucket_name
            )
            
            # Check if versioning is enabled
            status = response.get('Status', '').lower()
            return status == 'enabled'
            
        except Exception as e:
            logger.error(f"Failed to check bucket versioning: {str(e)}")
            return False
    
    @with_retry(max_retries=3, base_delay=1.0, max_delay=10.0)
    def enable_bucket_versioning(self) -> bool:
        """Enable versioning on the bucket if not already enabled.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if versioning is already enabled
            if self.check_bucket_versioning():
                logger.info(f"Versioning already enabled on bucket: {self.bucket_name}")
                return True
                
            # Enable versioning
            self.client.put_bucket_versioning(
                Bucket=self.bucket_name,
                VersioningConfiguration={
                    'Status': 'Enabled'
                }
            )
            
            logger.info(f"Successfully enabled versioning on bucket: {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable bucket versioning: {str(e)}")
            return False
    
    def _extract_metadata(self, response: Dict[str, Any]) -> StorageMetadata:
        """Extract metadata from an S3 object response.

        Args:
            response: The S3 API response

        Returns:
            StorageMetadata containing the extracted metadata
        """
        metadata = StorageMetadata(
            content_type=response.get('ContentType', 'application/octet-stream'),
            content_length=response.get('ContentLength', 0),
            last_modified=response.get('LastModified'),
            etag=response.get('ETag', '').strip('"'),
            version_id=response.get('VersionId'),
            server_side_encryption=response.get('ServerSideEncryption'),
            metadata=response.get('Metadata', {})
        )
        
        return metadata
    
    @with_retry(max_retries=2, base_delay=0.5, max_delay=5.0)
    def generate_presigned_url(self, key: str, expiration: int = 3600,
                             version_id: Optional[str] = None) -> Optional[str]:
        """Generate a presigned URL for temporary access to a document.

        Args:
            key: The document key in S3
            expiration: URL expiration time in seconds (default: 1 hour)
            version_id: Optional version ID for accessing a specific version

        Returns:
            str: Presigned URL or None if generation failed
        """
        try:
            params = {
                'Bucket': self.bucket_name,
                'Key': key
            }
            
            # Add version ID if specified
            if version_id:
                params['VersionId'] = version_id
                
            url = self.client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expiration
            )
            
            logger.info(f"Generated presigned URL for document: {key}")
            return url
            
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for document {key}: {str(e)}")
            return None
    
    @with_retry(max_retries=3, base_delay=0.5, max_delay=5.0)
    def document_exists(self, key: str) -> bool:
        """Check if a document exists in S3 storage.

        Args:
            key: The document key in S3

        Returns:
            bool: True if the document exists, False otherwise
        """
        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=key
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            else:
                logger.error(f"Error checking if document exists: {str(e)}")
                return False
        except Exception as e:
            logger.error(f"Unexpected error checking if document exists: {str(e)}")
            return False