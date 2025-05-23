#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Storage Service for OCR Service

This module provides S3-compatible storage operations for the OCR Service microservice.
It handles document retrieval, storage of OCR results, and management of document metadata
with secure AES-256 encryption. The service ensures that all documents are stored securely
and can be retrieved efficiently for OCR processing.

Key features:
1. S3 client connection with appropriate authentication
2. Document download functionality from specified buckets
3. AES-256 encryption for document storage
4. Error handling and retry logic for storage operations
5. Document metadata extraction and updating functionality
6. Versioning support for document history tracking
"""

import os
import logging
import hashlib
import json
from datetime import datetime
from typing import Dict, List, Optional, Union, BinaryIO, Tuple, Any, cast
from pathlib import Path
import tempfile
import time
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

from ..config.s3_config import (
    S3_CLIENT_CONFIG,
    S3_BOTO_CONFIG,
    DOCUMENT_BUCKET,
    EXTRACTED_DATA_BUCKET,
    DEFAULT_STORAGE_OPTIONS,
    SIGNED_URL_EXPIRATION,
    MULTIPART_THRESHOLD,
    MULTIPART_CHUNKSIZE,
    get_bucket_name,
    get_s3_client_config,
    get_storage_options
)
from ..types.storage import (
    StorageResult,
    StorageMetadata,
    StorageOptions,
    StorageErrorCode,
    StorageKey,
    SignedUrlOptions
)
from ..utils.error_utils import handle_boto_error
from ..utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)


class StorageService:
    """Service for S3-compatible storage operations.
    
    This class provides methods for interacting with S3-compatible storage,
    including document retrieval, storage of OCR results, and management of
    document metadata with secure AES-256 encryption.
    
    Attributes:
        s3_client: Boto3 S3 client for storage operations
        document_bucket: Bucket name for document storage
        extracted_data_bucket: Bucket name for extracted data storage
    """
    
    def __init__(self):
        """Initialize the storage service with S3 client."""
        try:
            # Get S3 client configuration
            client_config = get_s3_client_config()
            
            # Create S3 client with retry configuration
            self.s3_client = boto3.client('s3', config=S3_BOTO_CONFIG, **client_config)
            
            # Set bucket names
            self.document_bucket = DOCUMENT_BUCKET
            self.extracted_data_bucket = EXTRACTED_DATA_BUCKET
            
            logger.info(f"Initialized StorageService with document bucket: {self.document_bucket}")
            logger.info(f"Extracted data bucket: {self.extracted_data_bucket}")
            
        except (ClientError, BotoCoreError) as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise
    
    def download_document(self, key: str, local_path: Optional[str] = None) -> StorageResult[str]:
        """Download a document from S3 storage.
        
        Args:
            key: S3 object key
            local_path: Local path to save the document (optional)
            
        Returns:
            StorageResult containing the local path to the downloaded document
        """
        if not local_path:
            # Create a temporary file if no local path is provided
            fd, local_path = tempfile.mkstemp(suffix=Path(key).suffix)
            os.close(fd)
        
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Downloading document from {self.document_bucket}/{key} to {local_path}")
                
                # Download the file
                self.s3_client.download_file(
                    Bucket=self.document_bucket,
                    Key=key,
                    Filename=local_path
                )
                
                logger.info(f"Successfully downloaded document to {local_path}")
                return StorageResult.success_result(local_path)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying download after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to download document: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error downloading document: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def upload_document(self, 
                       local_path: str, 
                       key: str, 
                       metadata: Optional[Dict[str, str]] = None,
                       content_type: Optional[str] = None) -> StorageResult[str]:
        """Upload a document to S3 storage with AES-256 encryption.
        
        Args:
            local_path: Local path to the document
            key: S3 object key
            metadata: Document metadata (optional)
            content_type: Content type of the document (optional)
            
        Returns:
            StorageResult containing the S3 object key
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        # Get storage options with AES-256 encryption
        storage_options = get_storage_options(content_type, metadata)
        
        while retry_count < max_retries:
            try:
                logger.info(f"Uploading document from {local_path} to {self.document_bucket}/{key}")
                
                # Check if file size exceeds multipart threshold
                file_size = os.path.getsize(local_path)
                
                if file_size > MULTIPART_THRESHOLD:
                    # Use multipart upload for large files
                    transfer_config = boto3.s3.transfer.TransferConfig(
                        multipart_threshold=MULTIPART_THRESHOLD,
                        multipart_chunksize=MULTIPART_CHUNKSIZE
                    )
                    
                    # Create transfer manager
                    s3_transfer = boto3.s3.transfer.S3Transfer(
                        client=self.s3_client,
                        config=transfer_config
                    )
                    
                    # Upload file with multipart
                    s3_transfer.upload_file(
                        filename=local_path,
                        bucket=self.document_bucket,
                        key=key,
                        extra_args=storage_options
                    )
                else:
                    # Use regular upload for smaller files
                    with open(local_path, 'rb') as file_data:
                        self.s3_client.upload_fileobj(
                            Fileobj=file_data,
                            Bucket=self.document_bucket,
                            Key=key,
                            ExtraArgs=storage_options
                        )
                
                logger.info(f"Successfully uploaded document to {self.document_bucket}/{key}")
                return StorageResult.success_result(key)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying upload after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to upload document: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error uploading document: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def upload_extracted_data(self, 
                             data: Dict[str, Any], 
                             key: str, 
                             metadata: Optional[Dict[str, str]] = None) -> StorageResult[str]:
        """Upload extracted OCR data to S3 storage with AES-256 encryption.
        
        Args:
            data: Extracted OCR data as dictionary
            key: S3 object key
            metadata: Document metadata (optional)
            
        Returns:
            StorageResult containing the S3 object key
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        # Get storage options with AES-256 encryption
        storage_options = get_storage_options('application/json', metadata)
        
        while retry_count < max_retries:
            try:
                logger.info(f"Uploading extracted data to {self.extracted_data_bucket}/{key}")
                
                # Convert data to JSON string
                json_data = json.dumps(data, ensure_ascii=False, indent=2)
                
                # Upload JSON data
                self.s3_client.put_object(
                    Body=json_data.encode('utf-8'),
                    Bucket=self.extracted_data_bucket,
                    Key=key,
                    ContentType='application/json',
                    **storage_options
                )
                
                logger.info(f"Successfully uploaded extracted data to {self.extracted_data_bucket}/{key}")
                return StorageResult.success_result(key)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying upload after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to upload extracted data: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error uploading extracted data: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def get_document_metadata(self, key: str) -> StorageResult[StorageMetadata]:
        """Get metadata for a document in S3 storage.
        
        Args:
            key: S3 object key
            
        Returns:
            StorageResult containing the document metadata
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Getting metadata for document {self.document_bucket}/{key}")
                
                # Get object metadata
                response = self.s3_client.head_object(
                    Bucket=self.document_bucket,
                    Key=key
                )
                
                # Extract metadata from response
                metadata = response.get('Metadata', {})
                content_type = response.get('ContentType', 'application/octet-stream')
                size_bytes = response.get('ContentLength', 0)
                last_modified = response.get('LastModified', datetime.now())
                version_id = response.get('VersionId')
                etag = response.get('ETag', '').strip('"')  # Remove quotes from ETag
                
                # Parse key components
                key_components = StorageKey.parse_key(key)
                
                # Create StorageMetadata object
                storage_metadata = StorageMetadata(
                    document_id=metadata.get('document-id', key_components.get('document_id', '')),
                    application_id=metadata.get('application-id', key_components.get('application_id', '')),
                    document_type=metadata.get('document-type', key_components.get('document_type', '')),
                    content_type=content_type,
                    original_filename=metadata.get('original-filename', Path(key).name),
                    size_bytes=size_bytes,
                    md5_hash=etag,
                    created_at=datetime.fromisoformat(metadata.get('created-at', last_modified.isoformat())),
                    updated_at=last_modified,
                    version_id=version_id,
                    extraction_status=metadata.get('extraction-status'),
                    extraction_confidence=float(metadata.get('extraction-confidence', 0)) if metadata.get('extraction-confidence') else None,
                    tags={},
                    custom_metadata={k.replace('custom-', ''): v for k, v in metadata.items() if k.startswith('custom-')}
                )
                
                logger.info(f"Successfully retrieved metadata for document {key}")
                return StorageResult.success_result(storage_metadata)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying metadata retrieval after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to get document metadata: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error getting document metadata: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def update_document_metadata(self, 
                               key: str, 
                               metadata_updates: Dict[str, str]) -> StorageResult[bool]:
        """Update metadata for a document in S3 storage.
        
        Args:
            key: S3 object key
            metadata_updates: Metadata updates to apply
            
        Returns:
            StorageResult indicating success or failure
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Updating metadata for document {self.document_bucket}/{key}")
                
                # Get current metadata
                metadata_result = self.get_document_metadata(key)
                if not metadata_result.success:
                    return StorageResult.error_result(
                        metadata_result.error_code or StorageErrorCode.UNKNOWN_ERROR,
                        metadata_result.error_message or "Failed to get current metadata",
                        retry_count
                    )
                
                current_metadata = metadata_result.data
                if not current_metadata:
                    return StorageResult.error_result(
                        StorageErrorCode.RESOURCE_NOT_FOUND,
                        f"Document {key} not found",
                        retry_count
                    )
                
                # Update metadata
                s3_metadata = current_metadata.to_s3_metadata()
                s3_metadata.update(metadata_updates)
                
                # Copy object to itself with new metadata
                self.s3_client.copy_object(
                    CopySource={'Bucket': self.document_bucket, 'Key': key},
                    Bucket=self.document_bucket,
                    Key=key,
                    Metadata=s3_metadata,
                    MetadataDirective='REPLACE',
                    ServerSideEncryption='AES256'
                )
                
                logger.info(f"Successfully updated metadata for document {key}")
                return StorageResult.success_result(True)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying metadata update after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to update document metadata: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error updating document metadata: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def update_extraction_status(self, 
                               key: str, 
                               status: str, 
                               confidence: Optional[float] = None) -> StorageResult[bool]:
        """Update extraction status and confidence for a document.
        
        Args:
            key: S3 object key
            status: Extraction status (e.g., 'completed', 'failed', 'processing')
            confidence: Extraction confidence score (0.0-1.0)
            
        Returns:
            StorageResult indicating success or failure
        """
        metadata_updates = {'extraction-status': status}
        
        if confidence is not None:
            metadata_updates['extraction-confidence'] = str(confidence)
        
        return self.update_document_metadata(key, metadata_updates)
    
    def get_document_versions(self, key: str) -> StorageResult[List[Dict[str, Any]]]:
        """Get version history for a document in S3 storage.
        
        Args:
            key: S3 object key
            
        Returns:
            StorageResult containing list of document versions
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Getting version history for document {self.document_bucket}/{key}")
                
                # List object versions
                response = self.s3_client.list_object_versions(
                    Bucket=self.document_bucket,
                    Prefix=key
                )
                
                versions = []
                for version in response.get('Versions', []):
                    if version.get('Key') == key:
                        versions.append({
                            'version_id': version.get('VersionId'),
                            'last_modified': version.get('LastModified'),
                            'size_bytes': version.get('Size'),
                            'is_latest': version.get('IsLatest', False),
                            'etag': version.get('ETag', '').strip('"')
                        })
                
                logger.info(f"Found {len(versions)} versions for document {key}")
                return StorageResult.success_result(versions)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying version history retrieval after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to get document versions: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error getting document versions: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def get_document_version(self, 
                           key: str, 
                           version_id: str, 
                           local_path: Optional[str] = None) -> StorageResult[str]:
        """Get a specific version of a document from S3 storage.
        
        Args:
            key: S3 object key
            version_id: Version ID
            local_path: Local path to save the document (optional)
            
        Returns:
            StorageResult containing the local path to the downloaded document
        """
        if not local_path:
            # Create a temporary file if no local path is provided
            fd, local_path = tempfile.mkstemp(suffix=Path(key).suffix)
            os.close(fd)
        
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Downloading document version {version_id} from {self.document_bucket}/{key} to {local_path}")
                
                # Download the specific version
                self.s3_client.download_file(
                    Bucket=self.document_bucket,
                    Key=key,
                    Filename=local_path,
                    ExtraArgs={'VersionId': version_id}
                )
                
                logger.info(f"Successfully downloaded document version {version_id} to {local_path}")
                return StorageResult.success_result(local_path)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying version download after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to download document version: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error downloading document version: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def generate_presigned_url(self, 
                              key: str, 
                              options: Optional[SignedUrlOptions] = None) -> StorageResult[str]:
        """Generate a presigned URL for accessing a document.
        
        Args:
            key: S3 object key
            options: Signed URL options (optional)
            
        Returns:
            StorageResult containing the presigned URL
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        # Default options if not provided
        if not options:
            options = SignedUrlOptions()
        
        while retry_count < max_retries:
            try:
                logger.info(f"Generating presigned URL for {self.document_bucket}/{key}")
                
                # Generate presigned URL
                url = self.s3_client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={
                        'Bucket': self.document_bucket,
                        'Key': key,
                        **({k: v for k, v in options.response_headers.items()} if options.response_headers else {})
                    },
                    ExpiresIn=options.expiration
                )
                
                logger.info(f"Successfully generated presigned URL for {key} (expires in {options.expiration} seconds)")
                return StorageResult.success_result(url)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying URL generation after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to generate presigned URL: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error generating presigned URL: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def check_document_exists(self, key: str) -> StorageResult[bool]:
        """Check if a document exists in S3 storage.
        
        Args:
            key: S3 object key
            
        Returns:
            StorageResult indicating whether the document exists
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Checking if document exists: {self.document_bucket}/{key}")
                
                # Check if object exists
                self.s3_client.head_object(
                    Bucket=self.document_bucket,
                    Key=key
                )
                
                logger.info(f"Document exists: {self.document_bucket}/{key}")
                return StorageResult.success_result(True)
                
            except ClientError as e:
                # If the error is 404, the object doesn't exist
                if e.response['Error']['Code'] == '404':
                    logger.info(f"Document does not exist: {self.document_bucket}/{key}")
                    return StorageResult.success_result(False)
                
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying existence check after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to check if document exists: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error checking if document exists: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def list_documents(self, 
                      prefix: str, 
                      max_keys: int = 1000) -> StorageResult[List[Dict[str, Any]]]:
        """List documents in S3 storage with the given prefix.
        
        Args:
            prefix: S3 object key prefix
            max_keys: Maximum number of keys to return
            
        Returns:
            StorageResult containing list of document information
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Listing documents with prefix: {self.document_bucket}/{prefix}")
                
                # List objects with the given prefix
                response = self.s3_client.list_objects_v2(
                    Bucket=self.document_bucket,
                    Prefix=prefix,
                    MaxKeys=max_keys
                )
                
                documents = []
                for obj in response.get('Contents', []):
                    documents.append({
                        'key': obj.get('Key'),
                        'size_bytes': obj.get('Size'),
                        'last_modified': obj.get('LastModified'),
                        'etag': obj.get('ETag', '').strip('"')
                    })
                
                logger.info(f"Found {len(documents)} documents with prefix {prefix}")
                return StorageResult.success_result(documents)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying document listing after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to list documents: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error listing documents: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def delete_document(self, key: str) -> StorageResult[bool]:
        """Delete a document from S3 storage.
        
        Args:
            key: S3 object key
            
        Returns:
            StorageResult indicating success or failure
        """
        retry_count = 0
        max_retries = 3
        retry_delay = 1  # seconds
        
        while retry_count < max_retries:
            try:
                logger.info(f"Deleting document: {self.document_bucket}/{key}")
                
                # Delete the object
                self.s3_client.delete_object(
                    Bucket=self.document_bucket,
                    Key=key
                )
                
                logger.info(f"Successfully deleted document: {self.document_bucket}/{key}")
                return StorageResult.success_result(True)
                
            except ClientError as e:
                error_code, error_message = handle_boto_error(e)
                retry_count += 1
                
                if retry_count < max_retries and error_code in [
                    StorageErrorCode.CONNECTION_ERROR,
                    StorageErrorCode.TIMEOUT
                ]:
                    logger.warning(
                        f"Retrying document deletion after error: {error_message}. "
                        f"Retry {retry_count}/{max_retries}"
                    )
                    time.sleep(retry_delay * (2 ** (retry_count - 1)))  # Exponential backoff
                else:
                    logger.error(f"Failed to delete document: {error_message}")
                    return StorageResult.error_result(
                        error_code, error_message, retry_count
                    )
            except Exception as e:
                logger.error(f"Unexpected error deleting document: {str(e)}")
                return StorageResult.error_result(
                    StorageErrorCode.UNKNOWN_ERROR, str(e), retry_count
                )
        
        # This should not be reached due to the return statements in the loop
        return StorageResult.error_result(
            StorageErrorCode.UNKNOWN_ERROR, 
            "Maximum retries exceeded", 
            retry_count
        )
    
    def calculate_md5(self, file_path: str) -> str:
        """Calculate MD5 hash for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            MD5 hash as hexadecimal string
        """
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()
    
    def health_check(self) -> bool:
        """Perform a health check on the storage service.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Check if we can list buckets
            self.s3_client.list_buckets()
            return True
        except Exception as e:
            logger.error(f"Storage service health check failed: {str(e)}")
            return False