#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
S3 Storage Utilities for Document Service

This module provides utility functions for interacting with S3-compatible storage,
including connecting to S3, uploading and downloading documents, managing document
metadata, and generating signed URLs for secure access.

All document storage uses AES-256 encryption for data at rest as required by the
system security specifications in section 0.2.5 and 3.2.3.

This module is used by the Document Service to store classified documents in S3
with appropriate metadata as described in section 4.1.7 of the technical specification.
"""

import logging
import os
import json
from typing import Dict, Optional, Union, BinaryIO, Tuple, List, Any
from urllib.parse import urlparse

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError

# Try to import from local config, fall back to environment variables if not available
try:
    from config.s3_config import (
        S3_REGION_NAME,
        S3_ENDPOINT_URL,
        S3_ACCESS_KEY_ID,
        S3_SECRET_ACCESS_KEY,
        S3_BUCKET_NAME,
        S3_ENCRYPTION_ENABLED
    )
except ImportError:
    # Fall back to environment variables
    S3_REGION_NAME = os.environ.get('S3_REGION_NAME')
    S3_ENDPOINT_URL = os.environ.get('S3_ENDPOINT_URL')
    S3_ACCESS_KEY_ID = os.environ.get('S3_ACCESS_KEY_ID')
    S3_SECRET_ACCESS_KEY = os.environ.get('S3_SECRET_ACCESS_KEY')
    S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME')
    S3_ENCRYPTION_ENABLED = os.environ.get('S3_ENCRYPTION_ENABLED', 'true').lower() == 'true'

# Configure logging
logger = logging.getLogger(__name__)

# Default expiration time for signed URLs (1 hour)
DEFAULT_EXPIRATION = 3600

# Document classification metadata key
CLASSIFICATION_METADATA_KEY = 'document-classification'

# Document confidence score metadata key
CONFIDENCE_SCORE_METADATA_KEY = 'classification-confidence'

# Default S3 client configuration
DEFAULT_S3_CONFIG = Config(
    signature_version='s3v4',  # Use signature version 4 for enhanced security
    retries={
        'max_attempts': 3,      # Retry failed operations up to 3 times
        'mode': 'standard'      # Use standard retry mode
    }
)

# Transfer configuration for multipart uploads
TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,  # 8MB
    max_concurrency=10,
    multipart_chunksize=8 * 1024 * 1024,  # 8MB
    use_threads=True
)


def get_s3_client(region_name: Optional[str] = None,
                  endpoint_url: Optional[str] = None,
                  aws_access_key_id: Optional[str] = None,
                  aws_secret_access_key: Optional[str] = None,
                  config: Optional[Config] = None) -> boto3.client:
    """
    Create and return an S3 client with the specified configuration.
    
    Args:
        region_name: AWS region name (e.g., 'us-east-1')
        endpoint_url: URL for S3-compatible storage endpoint
        aws_access_key_id: AWS access key ID
        aws_secret_access_key: AWS secret access key
        config: Boto3 client configuration
        
    Returns:
        boto3.client: Configured S3 client
    """
    try:
        # Use provided config or default
        client_config = config or DEFAULT_S3_CONFIG
        
        # Create S3 client with provided credentials or use environment/instance profile
        s3_client = boto3.client(
            's3',
            region_name=region_name,
            endpoint_url=endpoint_url,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            config=client_config
        )
        
        logger.debug("S3 client created successfully")
        return s3_client
    
    except Exception as e:
        logger.error(f"Failed to create S3 client: {str(e)}")
        raise


def upload_document(s3_client: boto3.client,
                   bucket_name: str,
                   object_key: str,
                   file_obj: Union[BinaryIO, bytes],
                   metadata: Optional[Dict[str, str]] = None,
                   content_type: Optional[str] = None,
                   document_classification: Optional[str] = None,
                   classification_confidence: Optional[float] = None) -> Dict[str, Any]:
    """
    Upload a document to S3 with AES-256 encryption.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        file_obj: File object or bytes to upload
        metadata: Optional metadata to attach to the object
        content_type: MIME type of the document
        document_classification: Classification of the document (e.g., 'loan_application', 'tax_return')
        classification_confidence: Confidence score of the classification (0.0 to 1.0)
        
    Returns:
        Dict: Response from S3 put_object operation
    
    Raises:
        ClientError: If upload fails
    """
    try:
        # Prepare metadata with classification if provided
        upload_metadata = metadata or {}
        
        if document_classification:
            upload_metadata[CLASSIFICATION_METADATA_KEY] = document_classification
            
        if classification_confidence is not None:
            upload_metadata[CONFIDENCE_SCORE_METADATA_KEY] = str(classification_confidence)
        
        # Prepare upload parameters
        upload_args = {
            'Bucket': bucket_name,
            'Key': object_key,
            'Body': file_obj,
            # Enable AES-256 server-side encryption
            'ServerSideEncryption': 'AES256',
            'Metadata': upload_metadata
        }
        
        # Add content type if provided
        if content_type:
            upload_args['ContentType'] = content_type
        
        # Upload the file with multipart support for large files
        response = s3_client.put_object(**upload_args)
        
        logger.info(f"Document uploaded successfully to {bucket_name}/{object_key}")
        logger.debug(f"Upload response: {response}")
        
        return response
    
    except ClientError as e:
        logger.error(f"Failed to upload document to {bucket_name}/{object_key}: {str(e)}")
        raise


def upload_document_with_transfer_manager(s3_client: boto3.client,
                                         bucket_name: str,
                                         object_key: str,
                                         file_path: str,
                                         metadata: Optional[Dict[str, str]] = None,
                                         content_type: Optional[str] = None,
                                         document_classification: Optional[str] = None,
                                         classification_confidence: Optional[float] = None) -> Dict[str, Any]:
    """
    Upload a large document to S3 using the transfer manager with AES-256 encryption.
    
    This method is optimized for large file uploads with multipart support.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        file_path: Path to the file to upload
        metadata: Optional metadata to attach to the object
        content_type: MIME type of the document
        document_classification: Classification of the document (e.g., 'loan_application', 'tax_return')
        classification_confidence: Confidence score of the classification (0.0 to 1.0)
        
    Returns:
        Dict: Response from S3 upload operation
    
    Raises:
        ClientError: If upload fails
    """
    try:
        # Create S3 resource from client for transfer manager
        s3_resource = boto3.resource('s3', 
                                    region_name=s3_client.meta.region_name,
                                    endpoint_url=s3_client.meta.endpoint_url)
        
        # Prepare metadata with classification if provided
        upload_metadata = metadata or {}
        
        if document_classification:
            upload_metadata[CLASSIFICATION_METADATA_KEY] = document_classification
            
        if classification_confidence is not None:
            upload_metadata[CONFIDENCE_SCORE_METADATA_KEY] = str(classification_confidence)
        
        # Prepare extra arguments including encryption
        extra_args = {
            'ServerSideEncryption': 'AES256',
            'Metadata': upload_metadata
        }
        
        # Add content type if provided
        if content_type:
            extra_args['ContentType'] = content_type
        
        # Upload the file with transfer manager
        response = s3_resource.meta.client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=object_key,
            ExtraArgs=extra_args,
            Config=TRANSFER_CONFIG
        )
        
        logger.info(f"Large document uploaded successfully to {bucket_name}/{object_key}")
        
        # Return object metadata as confirmation
        return s3_client.head_object(Bucket=bucket_name, Key=object_key)
    
    except ClientError as e:
        logger.error(f"Failed to upload large document to {bucket_name}/{object_key}: {str(e)}")
        raise


def download_document(s3_client: boto3.client,
                     bucket_name: str,
                     object_key: str) -> Tuple[bytes, Dict[str, Any]]:
    """
    Download a document from S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        
    Returns:
        Tuple[bytes, Dict]: Document content and metadata
    
    Raises:
        ClientError: If download fails
    """
    try:
        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        
        # Read the object content
        content = response['Body'].read()
        
        # Extract metadata
        metadata = {
            'ContentType': response.get('ContentType', 'application/octet-stream'),
            'ContentLength': response.get('ContentLength', 0),
            'LastModified': response.get('LastModified'),
            'ETag': response.get('ETag'),
            'ServerSideEncryption': response.get('ServerSideEncryption'),
            'Metadata': response.get('Metadata', {})
        }
        
        logger.info(f"Document downloaded successfully from {bucket_name}/{object_key}")
        logger.debug(f"Document size: {len(content)} bytes")
        
        return content, metadata
    
    except ClientError as e:
        logger.error(f"Failed to download document from {bucket_name}/{object_key}: {str(e)}")
        raise


def download_document_to_file(s3_client: boto3.client,
                             bucket_name: str,
                             object_key: str,
                             file_path: str) -> Dict[str, Any]:
    """
    Download a document from S3 directly to a file.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        file_path: Local path to save the file
        
    Returns:
        Dict: Object metadata
    
    Raises:
        ClientError: If download fails
    """
    try:
        # Create S3 resource from client for transfer manager
        s3_resource = boto3.resource('s3', 
                                    region_name=s3_client.meta.region_name,
                                    endpoint_url=s3_client.meta.endpoint_url)
        
        # Download the file with transfer manager
        s3_resource.meta.client.download_file(
            Bucket=bucket_name,
            Key=object_key,
            Filename=file_path,
            Config=TRANSFER_CONFIG
        )
        
        # Get object metadata
        metadata = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        
        logger.info(f"Document downloaded successfully to {file_path}")
        
        return metadata
    
    except ClientError as e:
        logger.error(f"Failed to download document to file {file_path}: {str(e)}")
        raise


def get_document_classification(s3_client: boto3.client,
                               bucket_name: str,
                               object_key: str) -> Tuple[Optional[str], Optional[float]]:
    """
    Get the classification and confidence score for a document in S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        
    Returns:
        Tuple[Optional[str], Optional[float]]: Document classification and confidence score
        
    Raises:
        ClientError: If operation fails
    """
    try:
        # Get object metadata
        metadata = get_document_metadata(s3_client, bucket_name, object_key)
        
        # Extract classification and confidence score
        classification = metadata.get('Metadata', {}).get(CLASSIFICATION_METADATA_KEY)
        
        # Convert confidence score to float if present
        confidence_str = metadata.get('Metadata', {}).get(CONFIDENCE_SCORE_METADATA_KEY)
        confidence = float(confidence_str) if confidence_str else None
        
        return classification, confidence
    
    except ClientError as e:
        logger.error(f"Failed to get classification for {bucket_name}/{object_key}: {str(e)}")
        raise


def get_document_metadata(s3_client: boto3.client,
                         bucket_name: str,
                         object_key: str) -> Dict[str, Any]:
    """
    Get metadata for a document in S3 without downloading the content.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        
    Returns:
        Dict: Object metadata
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Get object metadata
        response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
        
        # Extract and format metadata
        metadata = {
            'ContentType': response.get('ContentType', 'application/octet-stream'),
            'ContentLength': response.get('ContentLength', 0),
            'LastModified': response.get('LastModified'),
            'ETag': response.get('ETag'),
            'ServerSideEncryption': response.get('ServerSideEncryption'),
            'Metadata': response.get('Metadata', {})
        }
        
        logger.debug(f"Retrieved metadata for {bucket_name}/{object_key}")
        
        return metadata
    
    except ClientError as e:
        logger.error(f"Failed to get metadata for {bucket_name}/{object_key}: {str(e)}")
        raise


def update_document_classification(s3_client: boto3.client,
                                 bucket_name: str,
                                 object_key: str,
                                 document_classification: str,
                                 classification_confidence: float) -> Dict[str, Any]:
    """
    Update the classification and confidence score for a document in S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        document_classification: Classification of the document
        classification_confidence: Confidence score of the classification (0.0 to 1.0)
        
    Returns:
        Dict: Response from S3 copy_object operation
        
    Raises:
        ClientError: If operation fails
    """
    try:
        # Prepare metadata update
        metadata_update = {
            CLASSIFICATION_METADATA_KEY: document_classification,
            CONFIDENCE_SCORE_METADATA_KEY: str(classification_confidence)
        }
        
        # Update document metadata
        return update_document_metadata(s3_client, bucket_name, object_key, metadata_update)
    
    except ClientError as e:
        logger.error(f"Failed to update classification for {bucket_name}/{object_key}: {str(e)}")
        raise


def update_document_metadata(s3_client: boto3.client,
                            bucket_name: str,
                            object_key: str,
                            metadata: Dict[str, str]) -> Dict[str, Any]:
    """
    Update metadata for an existing document in S3.
    
    Note: This creates a copy of the object with new metadata as S3 doesn't allow
    direct metadata updates.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        metadata: New metadata to set
        
    Returns:
        Dict: Response from S3 copy_object operation
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Get current object metadata to preserve non-updated fields
        current_metadata = get_document_metadata(s3_client, bucket_name, object_key)
        
        # Merge current metadata with new metadata
        merged_metadata = {**current_metadata.get('Metadata', {}), **metadata}
        
        # Copy object to itself with new metadata
        response = s3_client.copy_object(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': object_key},
            Key=object_key,
            Metadata=merged_metadata,
            MetadataDirective='REPLACE',
            ServerSideEncryption='AES256'  # Maintain encryption
        )
        
        logger.info(f"Updated metadata for {bucket_name}/{object_key}")
        logger.debug(f"New metadata: {merged_metadata}")
        
        return response
    
    except ClientError as e:
        logger.error(f"Failed to update metadata for {bucket_name}/{object_key}: {str(e)}")
        raise


def generate_presigned_url(s3_client: boto3.client,
                          bucket_name: str,
                          object_key: str,
                          expiration: int = DEFAULT_EXPIRATION,
                          http_method: str = 'GET') -> str:
    """
    Generate a presigned URL for secure access to an S3 object.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        expiration: URL expiration time in seconds (default: 1 hour)
        http_method: HTTP method for the URL ('GET' or 'PUT')
        
    Returns:
        str: Presigned URL
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Validate HTTP method
        if http_method not in ['GET', 'PUT']:
            raise ValueError(f"Unsupported HTTP method: {http_method}. Use 'GET' or 'PUT'.")
        
        # Map HTTP method to S3 client method
        client_method = 'get_object' if http_method == 'GET' else 'put_object'
        
        # Generate presigned URL
        url = s3_client.generate_presigned_url(
            ClientMethod=client_method,
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated presigned URL for {bucket_name}/{object_key} (expires in {expiration} seconds)")
        
        return url
    
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {bucket_name}/{object_key}: {str(e)}")
        raise


def get_default_s3_client() -> boto3.client:
    """
    Get a default S3 client using configuration from environment or config module.
    
    Returns:
        boto3.client: Configured S3 client
    """
    return get_s3_client(
        region_name=S3_REGION_NAME,
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY
    )


def generate_presigned_post(s3_client: boto3.client,
                           bucket_name: str,
                           object_key: str,
                           fields: Optional[Dict[str, str]] = None,
                           conditions: Optional[List[Any]] = None,
                           expiration: int = DEFAULT_EXPIRATION) -> Dict[str, Any]:
    """
    Generate a presigned POST policy for uploading objects to S3.
    
    This is the recommended way to allow clients to upload files directly to S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        fields: Additional form fields to include
        conditions: Conditions to include in the policy
        expiration: URL expiration time in seconds (default: 1 hour)
        
    Returns:
        Dict: Presigned POST data including URL and fields
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Prepare fields with encryption requirement
        post_fields = fields or {}
        post_fields['x-amz-server-side-encryption'] = 'AES256'
        
        # Prepare conditions with encryption requirement
        post_conditions = conditions or []
        post_conditions.append({'x-amz-server-side-encryption': 'AES256'})
        
        # Generate presigned POST
        presigned_post = s3_client.generate_presigned_post(
            Bucket=bucket_name,
            Key=object_key,
            Fields=post_fields,
            Conditions=post_conditions,
            ExpiresIn=expiration
        )
        
        logger.info(f"Generated presigned POST for {bucket_name}/{object_key} (expires in {expiration} seconds)")
        
        return presigned_post
    
    except ClientError as e:
        logger.error(f"Failed to generate presigned POST for {bucket_name}/{object_key}: {str(e)}")
        raise


def check_bucket_encryption(s3_client: boto3.client, bucket_name: str) -> bool:
    """
    Check if a bucket has default encryption enabled.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        
    Returns:
        bool: True if bucket has AES-256 encryption enabled, False otherwise
    """
    try:
        # Get bucket encryption configuration
        response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        
        # Check if AES-256 encryption is enabled
        rules = response.get('ServerSideEncryptionConfiguration', {}).get('Rules', [])
        for rule in rules:
            default_encryption = rule.get('ApplyServerSideEncryptionByDefault', {})
            if default_encryption.get('SSEAlgorithm') == 'AES256':
                logger.info(f"Bucket {bucket_name} has AES-256 encryption enabled")
                return True
        
        logger.warning(f"Bucket {bucket_name} does not have AES-256 encryption enabled")
        return False
    
    except ClientError as e:
        if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
            logger.warning(f"Bucket {bucket_name} does not have default encryption configured")
            return False
        else:
            logger.error(f"Failed to check encryption for bucket {bucket_name}: {str(e)}")
            raise


def enable_bucket_encryption(s3_client: boto3.client, bucket_name: str) -> Dict[str, Any]:
    """
    Enable AES-256 encryption for a bucket.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        
    Returns:
        Dict: Response from S3 put_bucket_encryption operation
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Configure AES-256 encryption for the bucket
        response = s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        )
        
        logger.info(f"Enabled AES-256 encryption for bucket {bucket_name}")
        
        return response
    
    except ClientError as e:
        logger.error(f"Failed to enable encryption for bucket {bucket_name}: {str(e)}")
        raise


def delete_document(s3_client: boto3.client, bucket_name: str, object_key: str) -> Dict[str, Any]:
    """
    Delete a document from S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        
    Returns:
        Dict: Response from S3 delete_object operation
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Delete the object
        response = s3_client.delete_object(Bucket=bucket_name, Key=object_key)
        
        logger.info(f"Deleted document {bucket_name}/{object_key}")
        
        return response
    
    except ClientError as e:
        logger.error(f"Failed to delete document {bucket_name}/{object_key}: {str(e)}")
        raise


def list_documents_by_classification(s3_client: boto3.client,
                                   bucket_name: str,
                                   classification: str,
                                   prefix: Optional[str] = None,
                                   max_keys: int = 1000) -> List[Dict[str, Any]]:
    """
    List documents in an S3 bucket with a specific classification.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        classification: Document classification to filter by
        prefix: Optional prefix to filter objects (e.g., 'folder/')
        max_keys: Maximum number of keys to return
        
    Returns:
        List[Dict]: List of document metadata
        
    Raises:
        ClientError: If operation fails
    """
    try:
        # List all documents with the given prefix
        all_documents = list_documents(s3_client, bucket_name, prefix, max_keys)
        
        # Filter documents by classification
        classified_documents = []
        for doc in all_documents:
            # Get document classification
            doc_key = doc.get('Key')
            try:
                doc_classification, _ = get_document_classification(s3_client, bucket_name, doc_key)
                if doc_classification == classification:
                    classified_documents.append(doc)
            except ClientError:
                # Skip documents that can't be accessed
                continue
        
        logger.info(f"Found {len(classified_documents)} documents with classification '{classification}'")
        
        return classified_documents
    
    except ClientError as e:
        logger.error(f"Failed to list documents by classification '{classification}': {str(e)}")
        raise


def list_documents(s3_client: boto3.client, 
                  bucket_name: str, 
                  prefix: Optional[str] = None, 
                  max_keys: int = 1000) -> List[Dict[str, Any]]:
    """
    List documents in an S3 bucket with optional prefix filtering.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        prefix: Optional prefix to filter objects (e.g., 'folder/')
        max_keys: Maximum number of keys to return
        
    Returns:
        List[Dict]: List of document metadata
    
    Raises:
        ClientError: If operation fails
    """
    try:
        # Prepare list parameters
        list_params = {
            'Bucket': bucket_name,
            'MaxKeys': max_keys
        }
        
        if prefix:
            list_params['Prefix'] = prefix
        
        # List objects
        response = s3_client.list_objects_v2(**list_params)
        
        # Extract document information
        documents = []
        for obj in response.get('Contents', []):
            documents.append({
                'Key': obj.get('Key'),
                'Size': obj.get('Size'),
                'LastModified': obj.get('LastModified'),
                'ETag': obj.get('ETag'),
                'StorageClass': obj.get('StorageClass')
            })
        
        logger.info(f"Listed {len(documents)} documents in {bucket_name}/{prefix if prefix else ''}")
        
        return documents
    
    except ClientError as e:
        logger.error(f"Failed to list documents in {bucket_name}/{prefix if prefix else ''}: {str(e)}")
        raise


def get_document_url(s3_client: boto3.client, bucket_name: str, object_key: str) -> str:
    """
    Get a direct URL to a document in S3 (not presigned, requires proper authentication).
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        
    Returns:
        str: URL to the document
    """
    # Get the region from the client if not explicitly provided
    region = s3_client.meta.region_name
    
    # Check if using a custom endpoint
    endpoint_url = s3_client.meta.endpoint_url
    if endpoint_url:
        # For custom S3-compatible storage
        url = f"{endpoint_url}/{bucket_name}/{object_key}"
    else:
        # For AWS S3
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{object_key}"
    
    return url


def document_exists(s3_client: boto3.client, bucket_name: str, object_key: str) -> bool:
    """
    Check if a document exists in S3.
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: Name of the S3 bucket
        object_key: Key (path) for the object in S3
        
    Returns:
        bool: True if document exists, False otherwise
    """
    try:
        # Try to get object metadata
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        logger.debug(f"Document {bucket_name}/{object_key} exists")
        return True
    
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.debug(f"Document {bucket_name}/{object_key} does not exist")
            return False
        else:
            logger.error(f"Error checking if document {bucket_name}/{object_key} exists: {str(e)}")
            raise