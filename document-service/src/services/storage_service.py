#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Storage Service for Document Service Microservice

This module provides a service class for interacting with S3-compatible storage,
handling document retrieval, storage, and management with secure AES-256 encryption.
It builds on the utility functions in s3_utils.py to provide a higher-level interface
for the Document Service's storage needs.

The service implements the following key features:
- S3 client connection with appropriate authentication
- Document download functionality from specified buckets
- AES-256 encryption for document storage
- Error handling and retry logic for storage operations
- Document metadata extraction for classification context

As specified in section 0.2.5 of the technical specification, all document storage
uses AES-256 encryption and appropriate buckets for different environments:
- 'mca-documents-production'
- 'mca-documents-staging'
"""

import logging
import os
import time
from typing import Dict, Optional, Union, BinaryIO, Tuple, List, Any, cast
from functools import wraps

import boto3
from botocore.exceptions import ClientError

from config import s3_config
from utils import s3_utils, retry_utils, security_utils
from types.storage import (
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult,
    StorageKey,
    PresignedUrlOptions,
    StorageError,
    StorageErrorCode,
    EncryptionType,
    DocumentType
)
from types.documents import Document, DocumentMetadata

# Configure logging
logger = logging.getLogger(__name__)


def handle_s3_errors(func):
    """
    Decorator to handle S3 client errors and convert them to StorageError exceptions.
    
    This decorator wraps storage service methods to provide consistent error handling
    and logging for S3 operations.
    
    Args:
        func: The function to wrap
        
    Returns:
        The wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Map AWS error codes to our error codes
            storage_error_code = StorageErrorCode.STORAGE_ERROR
            if error_code == 'NoSuchBucket':
                storage_error_code = StorageErrorCode.BUCKET_NOT_FOUND
            elif error_code == 'NoSuchKey':
                storage_error_code = StorageErrorCode.OBJECT_NOT_FOUND
            elif error_code == 'AccessDenied':
                storage_error_code = StorageErrorCode.PERMISSION_DENIED
            elif error_code == 'InvalidAccessKeyId' or error_code == 'SignatureDoesNotMatch':
                storage_error_code = StorageErrorCode.AUTHENTICATION_ERROR
            elif error_code == 'RequestTimeout':
                storage_error_code = StorageErrorCode.TIMEOUT_ERROR
            
            logger.error(f"S3 operation failed: {error_message} (Code: {error_code})")
            
            # Create a StorageError with the mapped code and original error details
            details = {
                'aws_error_code': error_code,
                'request_id': e.response.get('ResponseMetadata', {}).get('RequestId'),
                'operation': func.__name__
            }
            raise StorageError(error_message, storage_error_code, details)
        except Exception as e:
            logger.error(f"Unexpected error in storage operation: {str(e)}")
            raise StorageError(str(e), StorageErrorCode.STORAGE_ERROR, {
                'operation': func.__name__,
                'exception_type': type(e).__name__
            })
    return wrapper


class StorageService:
    """
    Service for interacting with S3-compatible storage.
    
    This service provides methods for storing, retrieving, and managing documents
    in S3-compatible storage with AES-256 encryption. It handles environment-specific
    bucket configurations, error handling, and retry logic.
    
    As specified in section 0.2.5 of the technical specification, all document storage
    uses AES-256 encryption and appropriate buckets for different environments.
    """
    
    def __init__(self, config: Optional[S3ClientConfig] = None):
        """
        Initialize the storage service with the specified configuration.
        
        Args:
            config: Optional S3 client configuration. If not provided, the configuration
                   will be loaded from the s3_config module or environment variables.
        """
        self.config = config or self._load_config()
        self.s3_client = self._initialize_s3_client()
        self.bucket_config = self._initialize_bucket_config()
        
        # Ensure the bucket has encryption enabled
        self._ensure_bucket_encryption()
        
        logger.info(f"StorageService initialized with bucket: {self.bucket_config.name}")
    
    def _load_config(self) -> S3ClientConfig:
        """
        Load S3 client configuration from the s3_config module or environment variables.
        
        Returns:
            S3ClientConfig: The loaded configuration
        """
        # Create S3ClientConfig from s3_config module or environment variables
        return S3ClientConfig(
            endpoint_url=s3_config.S3_ENDPOINT_URL or os.environ.get('S3_ENDPOINT_URL', ''),
            region_name=s3_config.S3_REGION_NAME or os.environ.get('S3_REGION_NAME', 'us-east-1'),
            aws_access_key_id=s3_config.S3_ACCESS_KEY_ID or os.environ.get('S3_ACCESS_KEY_ID', ''),
            aws_secret_access_key=s3_config.S3_SECRET_ACCESS_KEY or os.environ.get('S3_SECRET_ACCESS_KEY', ''),
            use_ssl=True,  # Always use SSL for security
            verify=True,   # Always verify SSL certificates
            max_pool_connections=10,
            timeout=30,
            retries=3
        )
    
    def _initialize_s3_client(self) -> boto3.client:
        """
        Initialize the S3 client with the configured parameters.
        
        Returns:
            boto3.client: The initialized S3 client
        """
        return s3_utils.get_s3_client(
            region_name=self.config['region_name'],
            endpoint_url=self.config['endpoint_url'],
            aws_access_key_id=self.config['aws_access_key_id'],
            aws_secret_access_key=self.config['aws_secret_access_key']
        )
    
    def _initialize_bucket_config(self) -> BucketConfig:
        """
        Initialize the bucket configuration based on the environment.
        
        As specified in section 0.2.5, the system uses the following buckets:
        - 'mca-documents-production'
        - 'mca-documents-staging'
        
        Returns:
            BucketConfig: The initialized bucket configuration
        """
        # Determine environment (production, staging, development)
        environment = os.environ.get('ENVIRONMENT', 'development').lower()
        
        # Select bucket based on environment
        if environment == 'production':
            bucket_name = s3_config.S3_PRODUCTION_BUCKET or 'mca-documents-production'
        elif environment == 'staging':
            bucket_name = s3_config.S3_STAGING_BUCKET or 'mca-documents-staging'
        else:
            # Development environment
            bucket_name = s3_config.S3_DEVELOPMENT_BUCKET or 'mca-documents-development'
        
        # Create bucket configuration
        return BucketConfig(
            name=bucket_name,
            region=self.config['region_name'],
            encryption=EncryptionType.AES256,  # Always use AES-256 encryption as per section 0.2.5
            versioning=True,  # Enable versioning for document history tracking
            public_access_blocked=True  # Block public access for security
        )
    
    def _ensure_bucket_encryption(self) -> None:
        """
        Ensure that the configured bucket has AES-256 encryption enabled.
        
        As specified in section 0.2.5, all document storage must use AES-256 encryption.
        """
        try:
            # Check if bucket encryption is enabled
            has_encryption = s3_utils.check_bucket_encryption(self.s3_client, self.bucket_config.name)
            
            # If encryption is not enabled, enable it
            if not has_encryption and s3_config.S3_ENCRYPTION_ENABLED:
                logger.info(f"Enabling AES-256 encryption for bucket {self.bucket_config.name}")
                s3_utils.enable_bucket_encryption(self.s3_client, self.bucket_config.name)
        except Exception as e:
            # Log the error but don't fail initialization
            # This allows the service to work with buckets where we don't have permission to check/set encryption
            logger.warning(f"Could not verify/enable bucket encryption: {str(e)}")
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def download_document(self, document_key: str) -> StorageResult[Tuple[bytes, Dict[str, Any]]]:
        """
        Download a document from S3 storage.
        
        Args:
            document_key: The key (path) of the document in S3
            
        Returns:
            StorageResult: Result containing the document content and metadata if successful
        """
        try:
            logger.info(f"Downloading document: {document_key}")
            
            # Download the document
            content, metadata = s3_utils.download_document(
                self.s3_client,
                self.bucket_config.name,
                document_key
            )
            
            # Verify encryption
            if metadata.get('ServerSideEncryption') != 'AES256' and s3_config.S3_ENCRYPTION_ENABLED:
                logger.warning(f"Document {document_key} is not encrypted with AES-256")
            
            return StorageResult(True, (content, metadata))
        except Exception as e:
            logger.error(f"Failed to download document {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def download_document_to_file(self, document_key: str, file_path: str) -> StorageResult[Dict[str, Any]]:
        """
        Download a document from S3 storage directly to a file.
        
        Args:
            document_key: The key (path) of the document in S3
            file_path: The local path to save the document
            
        Returns:
            StorageResult: Result containing the document metadata if successful
        """
        try:
            logger.info(f"Downloading document to file: {document_key} -> {file_path}")
            
            # Download the document to file
            metadata = s3_utils.download_document_to_file(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                file_path
            )
            
            # Verify encryption
            if metadata.get('ServerSideEncryption') != 'AES256' and s3_config.S3_ENCRYPTION_ENABLED:
                logger.warning(f"Document {document_key} is not encrypted with AES-256")
            
            return StorageResult(True, metadata)
        except Exception as e:
            logger.error(f"Failed to download document to file {file_path}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def upload_document(self, 
                       document_key: str, 
                       file_obj: Union[BinaryIO, bytes],
                       metadata: Optional[Dict[str, str]] = None,
                       content_type: Optional[str] = None,
                       document_classification: Optional[str] = None,
                       classification_confidence: Optional[float] = None) -> StorageResult[Dict[str, Any]]:
        """
        Upload a document to S3 storage with AES-256 encryption.
        
        Args:
            document_key: The key (path) to store the document in S3
            file_obj: The file object or bytes to upload
            metadata: Optional metadata to attach to the document
            content_type: The MIME type of the document
            document_classification: The classification of the document
            classification_confidence: The confidence score of the classification
            
        Returns:
            StorageResult: Result containing the upload response if successful
        """
        try:
            logger.info(f"Uploading document: {document_key}")
            
            # Upload the document with AES-256 encryption
            response = s3_utils.upload_document(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                file_obj,
                metadata,
                content_type,
                document_classification,
                classification_confidence
            )
            
            return StorageResult(True, response)
        except Exception as e:
            logger.error(f"Failed to upload document {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def upload_document_from_file(self,
                                document_key: str,
                                file_path: str,
                                metadata: Optional[Dict[str, str]] = None,
                                content_type: Optional[str] = None,
                                document_classification: Optional[str] = None,
                                classification_confidence: Optional[float] = None) -> StorageResult[Dict[str, Any]]:
        """
        Upload a document from a file to S3 storage with AES-256 encryption.
        
        This method is optimized for large file uploads with multipart support.
        
        Args:
            document_key: The key (path) to store the document in S3
            file_path: The path to the file to upload
            metadata: Optional metadata to attach to the document
            content_type: The MIME type of the document
            document_classification: The classification of the document
            classification_confidence: The confidence score of the classification
            
        Returns:
            StorageResult: Result containing the upload response if successful
        """
        try:
            logger.info(f"Uploading document from file: {file_path} -> {document_key}")
            
            # Upload the document with AES-256 encryption using transfer manager
            response = s3_utils.upload_document_with_transfer_manager(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                file_path,
                metadata,
                content_type,
                document_classification,
                classification_confidence
            )
            
            return StorageResult(True, response)
        except Exception as e:
            logger.error(f"Failed to upload document from file {file_path}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def update_document_classification(self,
                                     document_key: str,
                                     document_classification: str,
                                     classification_confidence: float) -> StorageResult[Dict[str, Any]]:
        """
        Update the classification and confidence score for a document in S3.
        
        Args:
            document_key: The key (path) of the document in S3
            document_classification: The classification of the document
            classification_confidence: The confidence score of the classification
            
        Returns:
            StorageResult: Result containing the update response if successful
        """
        try:
            logger.info(f"Updating document classification: {document_key} -> {document_classification} ({classification_confidence})")
            
            # Update the document classification
            response = s3_utils.update_document_classification(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                document_classification,
                classification_confidence
            )
            
            return StorageResult(True, response)
        except Exception as e:
            logger.error(f"Failed to update document classification for {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def update_document_metadata(self,
                               document_key: str,
                               metadata: Dict[str, str]) -> StorageResult[Dict[str, Any]]:
        """
        Update metadata for an existing document in S3.
        
        Args:
            document_key: The key (path) of the document in S3
            metadata: The new metadata to set
            
        Returns:
            StorageResult: Result containing the update response if successful
        """
        try:
            logger.info(f"Updating document metadata: {document_key}")
            
            # Update the document metadata
            response = s3_utils.update_document_metadata(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                metadata
            )
            
            return StorageResult(True, response)
        except Exception as e:
            logger.error(f"Failed to update document metadata for {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def get_document_metadata(self, document_key: str) -> StorageResult[Dict[str, Any]]:
        """
        Get metadata for a document in S3 without downloading the content.
        
        Args:
            document_key: The key (path) of the document in S3
            
        Returns:
            StorageResult: Result containing the document metadata if successful
        """
        try:
            logger.info(f"Getting document metadata: {document_key}")
            
            # Get the document metadata
            metadata = s3_utils.get_document_metadata(
                self.s3_client,
                self.bucket_config.name,
                document_key
            )
            
            return StorageResult(True, metadata)
        except Exception as e:
            logger.error(f"Failed to get document metadata for {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def get_document_classification(self, document_key: str) -> StorageResult[Tuple[Optional[str], Optional[float]]]:
        """
        Get the classification and confidence score for a document in S3.
        
        Args:
            document_key: The key (path) of the document in S3
            
        Returns:
            StorageResult: Result containing the document classification and confidence score if successful
        """
        try:
            logger.info(f"Getting document classification: {document_key}")
            
            # Get the document classification
            classification, confidence = s3_utils.get_document_classification(
                self.s3_client,
                self.bucket_config.name,
                document_key
            )
            
            return StorageResult(True, (classification, confidence))
        except Exception as e:
            logger.error(f"Failed to get document classification for {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    @retry_utils.retry(retries=3, backoff_factor=1.5)
    def delete_document(self, document_key: str) -> StorageResult[Dict[str, Any]]:
        """
        Delete a document from S3.
        
        Args:
            document_key: The key (path) of the document in S3
            
        Returns:
            StorageResult: Result containing the delete response if successful
        """
        try:
            logger.info(f"Deleting document: {document_key}")
            
            # Delete the document
            response = s3_utils.delete_document(
                self.s3_client,
                self.bucket_config.name,
                document_key
            )
            
            return StorageResult(True, response)
        except Exception as e:
            logger.error(f"Failed to delete document {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def generate_presigned_url(self,
                             document_key: str,
                             expiration: int = 3600,
                             http_method: str = 'GET') -> StorageResult[str]:
        """
        Generate a presigned URL for secure access to a document in S3.
        
        As specified in section 3.5.3, the system uses signed URLs with short expiration times
        for secure document access.
        
        Args:
            document_key: The key (path) of the document in S3
            expiration: The expiration time in seconds (default: 1 hour)
            http_method: The HTTP method for the URL ('GET' or 'PUT')
            
        Returns:
            StorageResult: Result containing the presigned URL if successful
        """
        try:
            logger.info(f"Generating presigned URL for {document_key} (expires in {expiration} seconds)")
            
            # Generate the presigned URL
            url = s3_utils.generate_presigned_url(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                expiration,
                http_method
            )
            
            return StorageResult(True, url)
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def generate_presigned_post(self,
                              document_key: str,
                              fields: Optional[Dict[str, str]] = None,
                              conditions: Optional[List[Any]] = None,
                              expiration: int = 3600) -> StorageResult[Dict[str, Any]]:
        """
        Generate a presigned POST policy for uploading documents directly to S3.
        
        This is the recommended way to allow clients to upload files directly to S3.
        
        Args:
            document_key: The key (path) of the document in S3
            fields: Additional form fields to include
            conditions: Conditions to include in the policy
            expiration: The expiration time in seconds (default: 1 hour)
            
        Returns:
            StorageResult: Result containing the presigned POST data if successful
        """
        try:
            logger.info(f"Generating presigned POST for {document_key} (expires in {expiration} seconds)")
            
            # Generate the presigned POST
            post_data = s3_utils.generate_presigned_post(
                self.s3_client,
                self.bucket_config.name,
                document_key,
                fields,
                conditions,
                expiration
            )
            
            return StorageResult(True, post_data)
        except Exception as e:
            logger.error(f"Failed to generate presigned POST for {document_key}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def document_exists(self, document_key: str) -> StorageResult[bool]:
        """
        Check if a document exists in S3.
        
        Args:
            document_key: The key (path) of the document in S3
            
        Returns:
            StorageResult: Result containing True if the document exists, False otherwise
        """
        try:
            logger.debug(f"Checking if document exists: {document_key}")
            
            # Check if the document exists
            exists = s3_utils.document_exists(
                self.s3_client,
                self.bucket_config.name,
                document_key
            )
            
            return StorageResult(True, exists)
        except Exception as e:
            logger.error(f"Failed to check if document {document_key} exists: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def list_documents(self,
                     prefix: Optional[str] = None,
                     max_keys: int = 1000) -> StorageResult[List[Dict[str, Any]]]:
        """
        List documents in the S3 bucket with optional prefix filtering.
        
        Args:
            prefix: Optional prefix to filter objects (e.g., 'folder/')
            max_keys: Maximum number of keys to return
            
        Returns:
            StorageResult: Result containing the list of documents if successful
        """
        try:
            logger.info(f"Listing documents with prefix: {prefix or 'None'}")
            
            # List the documents
            documents = s3_utils.list_documents(
                self.s3_client,
                self.bucket_config.name,
                prefix,
                max_keys
            )
            
            return StorageResult(True, documents)
        except Exception as e:
            logger.error(f"Failed to list documents with prefix {prefix or 'None'}: {str(e)}")
            return StorageResult(False, error=e)
    
    @handle_s3_errors
    def list_documents_by_classification(self,
                                       classification: str,
                                       prefix: Optional[str] = None,
                                       max_keys: int = 1000) -> StorageResult[List[Dict[str, Any]]]:
        """
        List documents in the S3 bucket with a specific classification.
        
        Args:
            classification: Document classification to filter by
            prefix: Optional prefix to filter objects (e.g., 'folder/')
            max_keys: Maximum number of keys to return
            
        Returns:
            StorageResult: Result containing the list of documents if successful
        """
        try:
            logger.info(f"Listing documents with classification: {classification}")
            
            # List the documents by classification
            documents = s3_utils.list_documents_by_classification(
                self.s3_client,
                self.bucket_config.name,
                classification,
                prefix,
                max_keys
            )
            
            return StorageResult(True, documents)
        except Exception as e:
            logger.error(f"Failed to list documents with classification {classification}: {str(e)}")
            return StorageResult(False, error=e)
    
    def create_storage_key(self,
                         application_id: str,
                         document_id: str,
                         document_type: Union[str, DocumentType],
                         version: str = 'v1') -> str:
        """
        Create a storage key for a document.
        
        This method generates a consistent key for document storage, following the pattern:
        {application_id}/{document_type}/{document_id}/{version}
        
        Args:
            application_id: ID of the application
            document_id: ID of the document
            document_type: Type of document (string or DocumentType enum)
            version: Version of the document (default: 'v1')
            
        Returns:
            str: The generated storage key
        """
        # Convert DocumentType enum to string if needed
        doc_type = document_type.name.lower() if isinstance(document_type, DocumentType) else document_type.lower()
        
        # Create a StorageKey object
        storage_key = StorageKey(
            application_id=application_id,
            document_id=document_id,
            document_type=doc_type,
            version=version
        )
        
        # Convert to string
        return storage_key.to_string()
    
    def parse_storage_key(self, key_string: str) -> StorageKey:
        """
        Parse a storage key string into a StorageKey object.
        
        Args:
            key_string: The storage key string to parse
            
        Returns:
            StorageKey: The parsed storage key
            
        Raises:
            ValueError: If the key string has an invalid format
        """
        return StorageKey.from_string(key_string)
    
    def store_document(self, document: Document) -> StorageResult[str]:
        """
        Store a document in S3 with its metadata and classification.
        
        This is a high-level method that combines document key generation and upload.
        
        Args:
            document: The document to store, including content and metadata
            
        Returns:
            StorageResult: Result containing the storage key if successful
        """
        try:
            # Generate a storage key for the document
            storage_key = self.create_storage_key(
                application_id=document.metadata.application_id,
                document_id=document.metadata.document_id,
                document_type=document.document_type.name.lower() if document.document_type else 'unknown',
                version='v1'  # Initial version
            )
            
            # Prepare metadata
            metadata = {
                'document_id': document.metadata.document_id,
                'application_id': document.metadata.application_id,
                'original_filename': document.metadata.original_filename,
                'upload_timestamp': document.metadata.upload_timestamp.isoformat() if document.metadata.upload_timestamp else '',
                'size_bytes': str(document.metadata.size_bytes) if document.metadata.size_bytes else '0'
            }
            
            # Upload the document
            upload_result = self.upload_document(
                document_key=storage_key,
                file_obj=document.content,
                metadata=metadata,
                content_type=document.metadata.content_type,
                document_classification=document.document_type.name.lower() if document.document_type else None,
                classification_confidence=document.classification_confidence
            )
            
            if not upload_result.success:
                return StorageResult(False, error=upload_result.error)
            
            return StorageResult(True, storage_key)
        except Exception as e:
            logger.error(f"Failed to store document: {str(e)}")
            return StorageResult(False, error=e)
    
    def retrieve_document(self, storage_key: str) -> StorageResult[Document]:
        """
        Retrieve a document from S3 with its metadata and classification.
        
        This is a high-level method that combines document download and metadata retrieval.
        
        Args:
            storage_key: The storage key of the document to retrieve
            
        Returns:
            StorageResult: Result containing the document if successful
        """
        try:
            # Download the document
            download_result = self.download_document(storage_key)
            if not download_result.success:
                return StorageResult(False, error=download_result.error)
            
            content, s3_metadata = download_result.data
            
            # Get document classification
            classification_result = self.get_document_classification(storage_key)
            if not classification_result.success:
                return StorageResult(False, error=classification_result.error)
            
            doc_classification, confidence = classification_result.data
            
            # Parse the storage key to get application_id, document_id, and document_type
            try:
                key_parts = self.parse_storage_key(storage_key)
                application_id = key_parts.application_id
                document_id = key_parts.document_id
                document_type_str = key_parts.document_type
            except ValueError:
                # If the key doesn't follow our format, use metadata or defaults
                metadata = s3_metadata.get('Metadata', {})
                application_id = metadata.get('application_id', '')
                document_id = metadata.get('document_id', '')
                document_type_str = doc_classification or 'unknown'
            
            # Map document_type string to DocumentType enum
            try:
                document_type = DocumentType[document_type_str.upper()]
            except (KeyError, AttributeError):
                document_type = DocumentType.OTHER
            
            # Create document metadata
            metadata = s3_metadata.get('Metadata', {})
            doc_metadata = DocumentMetadata(
                document_id=document_id,
                application_id=application_id,
                original_filename=metadata.get('original_filename', ''),
                content_type=s3_metadata.get('ContentType', 'application/octet-stream'),
                size_bytes=s3_metadata.get('ContentLength', 0)
            )
            
            # Create document
            document = Document(
                metadata=doc_metadata,
                content=content,
                document_type=document_type,
                classification_confidence=float(confidence) if confidence is not None else None
            )
            
            return StorageResult(True, document)
        except Exception as e:
            logger.error(f"Failed to retrieve document {storage_key}: {str(e)}")
            return StorageResult(False, error=e)