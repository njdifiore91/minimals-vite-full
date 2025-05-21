#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
S3 Storage Utilities for OCR Service

This module provides utility functions for connecting to S3-compatible storage,
uploading extracted data, downloading documents, and managing document metadata.
It implements AES-256 encryption for secure document storage and signed URL
generation for secure access to documents.

The module supports the following key features:
1. S3 connection management with proper configuration
2. Document upload and download with AES-256 encryption
3. Extracted data management with metadata
4. Secure access through signed URLs
5. Error handling for all S3 operations
"""

import os
import logging
import json
import time
from typing import Dict, Optional, Any, Union, Tuple, BinaryIO, List
from urllib.parse import urlparse

import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

# Configure logging
logger = logging.getLogger(__name__)

# Default expiration time for signed URLs (1 hour)
DEFAULT_EXPIRATION = 3600

# Default S3 bucket names from environment variables
DEFAULT_DOCUMENT_BUCKET = os.environ.get('OCR_DOCUMENT_BUCKET', 'mca-documents-production')
DEFAULT_EXTRACTED_DATA_BUCKET = os.environ.get('OCR_EXTRACTED_DATA_BUCKET', 'mca-documents-production')


def get_s3_client(region_name: Optional[str] = None,
                 endpoint_url: Optional[str] = None,
                 aws_access_key_id: Optional[str] = None,
                 aws_secret_access_key: Optional[str] = None,
                 aws_session_token: Optional[str] = None) -> boto3.client:
    """
    Create and return an S3 client with the specified configuration.
    
    Args:
        region_name: AWS region name (defaults to environment variable AWS_REGION)
        endpoint_url: S3-compatible storage endpoint URL
        aws_access_key_id: AWS access key ID (defaults to environment variable)
        aws_secret_access_key: AWS secret access key (defaults to environment variable)
        aws_session_token: AWS session token for temporary credentials
        
    Returns:
        boto3.client: Configured S3 client
    """
    # Use environment variables as defaults if not provided
    region = region_name or os.environ.get('AWS_REGION', 'us-east-1')
    endpoint = endpoint_url or os.environ.get('S3_ENDPOINT_URL')
    access_key = aws_access_key_id or os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = aws_secret_access_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    session_token = aws_session_token or os.environ.get('AWS_SESSION_TOKEN')
    
    # Configure S3 client with signature version 4 for better security
    config = Config(
        signature_version='s3v4',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    
    # Create S3 client
    try:
        client_kwargs = {
            'service_name': 's3',
            'region_name': region,
            'config': config
        }
        
        # Add optional parameters if provided
        if endpoint:
            client_kwargs['endpoint_url'] = endpoint
        if access_key and secret_key:
            client_kwargs['aws_access_key_id'] = access_key
            client_kwargs['aws_secret_access_key'] = secret_key
        if session_token:
            client_kwargs['aws_session_token'] = session_token
        
        s3_client = boto3.client(**client_kwargs)
        logger.debug(f"S3 client created for region {region}")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to create S3 client: {str(e)}")
        raise


def get_s3_resource(region_name: Optional[str] = None,
                   endpoint_url: Optional[str] = None,
                   aws_access_key_id: Optional[str] = None,
                   aws_secret_access_key: Optional[str] = None,
                   aws_session_token: Optional[str] = None) -> boto3.resource:
    """
    Create and return an S3 resource with the specified configuration.
    
    Args:
        region_name: AWS region name (defaults to environment variable AWS_REGION)
        endpoint_url: S3-compatible storage endpoint URL
        aws_access_key_id: AWS access key ID (defaults to environment variable)
        aws_secret_access_key: AWS secret access key (defaults to environment variable)
        aws_session_token: AWS session token for temporary credentials
        
    Returns:
        boto3.resource: Configured S3 resource
    """
    # Use environment variables as defaults if not provided
    region = region_name or os.environ.get('AWS_REGION', 'us-east-1')
    endpoint = endpoint_url or os.environ.get('S3_ENDPOINT_URL')
    access_key = aws_access_key_id or os.environ.get('AWS_ACCESS_KEY_ID')
    secret_key = aws_secret_access_key or os.environ.get('AWS_SECRET_ACCESS_KEY')
    session_token = aws_session_token or os.environ.get('AWS_SESSION_TOKEN')
    
    # Configure S3 resource with signature version 4 for better security
    config = Config(
        signature_version='s3v4',
        retries={
            'max_attempts': 3,
            'mode': 'standard'
        }
    )
    
    # Create S3 resource
    try:
        resource_kwargs = {
            'service_name': 's3',
            'region_name': region,
            'config': config
        }
        
        # Add optional parameters if provided
        if endpoint:
            resource_kwargs['endpoint_url'] = endpoint
        if access_key and secret_key:
            resource_kwargs['aws_access_key_id'] = access_key
            resource_kwargs['aws_secret_access_key'] = secret_key
        if session_token:
            resource_kwargs['aws_session_token'] = session_token
        
        s3_resource = boto3.resource(**resource_kwargs)
        logger.debug(f"S3 resource created for region {region}")
        return s3_resource
    except Exception as e:
        logger.error(f"Failed to create S3 resource: {str(e)}")
        raise


def download_document(bucket: str, key: str, 
                     s3_client: Optional[boto3.client] = None) -> Tuple[bytes, Dict[str, Any]]:
    """
    Download a document from S3 storage.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path to document)
        s3_client: Existing S3 client (optional)
        
    Returns:
        Tuple containing:
            - Document content as bytes
            - Metadata dictionary
    
    Raises:
        ClientError: If document cannot be downloaded
    """
    client = s3_client or get_s3_client()
    
    try:
        logger.info(f"Downloading document from s3://{bucket}/{key}")
        response = client.get_object(Bucket=bucket, Key=key)
        
        # Read document content
        document_content = response['Body'].read()
        
        # Extract metadata
        metadata = {
            'ContentType': response.get('ContentType', 'application/octet-stream'),
            'ContentLength': response.get('ContentLength', 0),
            'LastModified': response.get('LastModified'),
            'ETag': response.get('ETag'),
            'VersionId': response.get('VersionId'),
            'ServerSideEncryption': response.get('ServerSideEncryption'),
            'Metadata': response.get('Metadata', {})
        }
        
        logger.debug(f"Successfully downloaded document ({len(document_content)} bytes)")
        return document_content, metadata
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to download document: {error_code} - {error_message}")
        raise


def upload_document(bucket: str, key: str, document: Union[bytes, BinaryIO],
                  content_type: Optional[str] = None,
                  metadata: Optional[Dict[str, str]] = None,
                  s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Upload a document to S3 storage with AES-256 encryption.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key (path to document)
        document: Document content as bytes or file-like object
        content_type: MIME type of the document
        metadata: Custom metadata to attach to the document
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the S3 response
        
    Raises:
        ClientError: If document cannot be uploaded
    """
    client = s3_client or get_s3_client()
    
    # Prepare upload parameters
    params = {
        'Bucket': bucket,
        'Key': key,
        'Body': document,
        'ServerSideEncryption': 'AES256'  # Enable AES-256 encryption
    }
    
    # Add content type if provided
    if content_type:
        params['ContentType'] = content_type
    
    # Add metadata if provided
    if metadata:
        params['Metadata'] = metadata
    
    try:
        logger.info(f"Uploading document to s3://{bucket}/{key} with encryption")
        response = client.put_object(**params)
        logger.debug(f"Successfully uploaded document to s3://{bucket}/{key}")
        return response
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to upload document: {error_code} - {error_message}")
        raise


def upload_extracted_data(bucket: str, key: str, extracted_data: Dict[str, Any],
                         original_document_key: str,
                         confidence_scores: Optional[Dict[str, float]] = None,
                         document_type: Optional[str] = None,
                         extraction_timestamp: Optional[float] = None,
                         s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Upload extracted data from OCR processing to S3 storage.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key for the extracted data
        extracted_data: Dictionary containing extracted data
        original_document_key: Key of the original document
        confidence_scores: Dictionary of confidence scores for extracted fields
        document_type: Type of document (e.g., 'application_form', 'tax_return')
        extraction_timestamp: Timestamp of extraction (defaults to current time)
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the S3 response
        
    Raises:
        ClientError: If data cannot be uploaded
    """
    client = s3_client or get_s3_client()
    
    # Use current timestamp if not provided
    if extraction_timestamp is None:
        extraction_timestamp = time.time()
    
    # Prepare metadata
    metadata = {
        'original-document': original_document_key,
        'content-type': 'application/json',
        'extraction-type': 'ocr',
        'extraction-timestamp': str(extraction_timestamp)
    }
    
    # Add document type if provided
    if document_type:
        metadata['document-type'] = document_type
    
    # Add confidence scores to the extracted data
    if confidence_scores:
        extracted_data['confidence_scores'] = confidence_scores
    
    # Add extraction metadata to the data itself
    extracted_data['metadata'] = {
        'original_document': original_document_key,
        'extraction_timestamp': extraction_timestamp,
        'document_type': document_type or 'unknown'
    }
    
    # Convert data to JSON
    json_data = json.dumps(extracted_data).encode('utf-8')
    
    try:
        logger.info(f"Uploading extracted data to s3://{bucket}/{key}")
        response = client.put_object(
            Bucket=bucket,
            Key=key,
            Body=json_data,
            ContentType='application/json',
            Metadata=metadata,
            ServerSideEncryption='AES256'  # Enable AES-256 encryption
        )
        logger.debug(f"Successfully uploaded extracted data to s3://{bucket}/{key}")
        return response
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to upload extracted data: {error_code} - {error_message}")
        raise


def update_document_metadata(bucket: str, key: str, metadata: Dict[str, str],
                            s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Update metadata for an existing document in S3 storage.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        metadata: New metadata dictionary
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the S3 response
        
    Raises:
        ClientError: If metadata cannot be updated
    """
    client = s3_client or get_s3_client()
    
    try:
        # Get the current object to copy it with new metadata
        logger.info(f"Updating metadata for s3://{bucket}/{key}")
        
        # Copy object to itself with new metadata
        response = client.copy_object(
            CopySource={'Bucket': bucket, 'Key': key},
            Bucket=bucket,
            Key=key,
            Metadata=metadata,
            MetadataDirective='REPLACE',
            ServerSideEncryption='AES256'  # Maintain encryption
        )
        
        logger.debug(f"Successfully updated metadata for s3://{bucket}/{key}")
        return response
    
    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Failed to update metadata: {error_code} - {error_message}")
        raise


def generate_presigned_url(bucket: str, key: str, expiration: int = DEFAULT_EXPIRATION,
                          s3_client: Optional[boto3.client] = None) -> str:
    """
    Generate a presigned URL for secure access to a document.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration time in seconds (default: 1 hour)
        s3_client: Existing S3 client (optional)
        
    Returns:
        Presigned URL as string
        
    Raises:
        ClientError: If URL cannot be generated
    """
    client = s3_client or get_s3_client()
    
    try:
        logger.info(f"Generating presigned URL for s3://{bucket}/{key} (expires in {expiration}s)")
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expiration
        )
        
        logger.debug(f"Successfully generated presigned URL")
        return url
    
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {str(e)}")
        raise


def check_document_exists(bucket: str, key: str, s3_client: Optional[boto3.client] = None) -> bool:
    """
    Check if a document exists in S3 storage.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        s3_client: Existing S3 client (optional)
        
    Returns:
        True if document exists, False otherwise
    """
    client = s3_client or get_s3_client()
    
    try:
        client.head_object(Bucket=bucket, Key=key)
        logger.debug(f"Document exists at s3://{bucket}/{key}")
        return True
    
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.debug(f"Document does not exist at s3://{bucket}/{key}")
            return False
        else:
            logger.error(f"Error checking if document exists: {str(e)}")
            raise


def parse_s3_uri(uri: str) -> Tuple[str, str]:
    """
    Parse an S3 URI into bucket and key components.
    
    Args:
        uri: S3 URI in the format s3://bucket/key
        
    Returns:
        Tuple containing (bucket, key)
        
    Raises:
        ValueError: If URI is not a valid S3 URI
    """
    if not uri.startswith('s3://'):
        raise ValueError(f"Invalid S3 URI: {uri}. Must start with 's3://'")
    
    parsed = urlparse(uri)
    bucket = parsed.netloc
    key = parsed.path.lstrip('/')
    
    if not bucket or not key:
        raise ValueError(f"Invalid S3 URI: {uri}. Must contain both bucket and key")
    
    return bucket, key


def get_bucket_encryption_status(bucket: str, s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Get the encryption status of an S3 bucket.
    
    Args:
        bucket: S3 bucket name
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing encryption configuration or empty dict if not encrypted
        
    Raises:
        ClientError: For errors other than missing encryption configuration
    """
    client = s3_client or get_s3_client()
    
    try:
        response = client.get_bucket_encryption(Bucket=bucket)
        return response.get('ServerSideEncryptionConfiguration', {})
    
    except ClientError as e:
        if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
            logger.warning(f"Bucket {bucket} does not have default encryption configured")
            return {}
        else:
            logger.error(f"Error checking bucket encryption: {str(e)}")
            raise


def list_documents(bucket: str, prefix: str = '', 
                  max_keys: int = 1000,
                  s3_client: Optional[boto3.client] = None) -> List[Dict[str, Any]]:
    """
    List documents in an S3 bucket with the given prefix.
    
    Args:
        bucket: S3 bucket name
        prefix: Prefix to filter objects (folder path)
        max_keys: Maximum number of keys to return
        s3_client: Existing S3 client (optional)
        
    Returns:
        List of dictionaries containing document information
        
    Raises:
        ClientError: If documents cannot be listed
    """
    client = s3_client or get_s3_client()
    
    try:
        logger.info(f"Listing documents in s3://{bucket}/{prefix}")
        response = client.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            MaxKeys=max_keys
        )
        
        documents = []
        for obj in response.get('Contents', []):
            documents.append({
                'key': obj.get('Key'),
                'size': obj.get('Size'),
                'last_modified': obj.get('LastModified'),
                'etag': obj.get('ETag'),
                'storage_class': obj.get('StorageClass')
            })
        
        logger.debug(f"Found {len(documents)} documents")
        return documents
    
    except ClientError as e:
        logger.error(f"Failed to list documents: {str(e)}")
        raise


def delete_document(bucket: str, key: str, s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Delete a document from S3 storage.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the S3 response
        
    Raises:
        ClientError: If document cannot be deleted
    """
    client = s3_client or get_s3_client()
    
    try:
        logger.info(f"Deleting document at s3://{bucket}/{key}")
        response = client.delete_object(
            Bucket=bucket,
            Key=key
        )
        logger.debug(f"Successfully deleted document at s3://{bucket}/{key}")
        return response
    
    except ClientError as e:
        logger.error(f"Failed to delete document: {str(e)}")
        raise


def copy_document(source_bucket: str, source_key: str,
                 dest_bucket: str, dest_key: str,
                 metadata: Optional[Dict[str, str]] = None,
                 s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Copy a document from one location to another in S3 storage.
    
    Args:
        source_bucket: Source S3 bucket name
        source_key: Source S3 object key
        dest_bucket: Destination S3 bucket name
        dest_key: Destination S3 object key
        metadata: New metadata to apply (optional)
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the S3 response
        
    Raises:
        ClientError: If document cannot be copied
    """
    client = s3_client or get_s3_client()
    
    try:
        logger.info(f"Copying document from s3://{source_bucket}/{source_key} to s3://{dest_bucket}/{dest_key}")
        
        params = {
            'CopySource': {'Bucket': source_bucket, 'Key': source_key},
            'Bucket': dest_bucket,
            'Key': dest_key,
            'ServerSideEncryption': 'AES256'  # Maintain encryption
        }
        
        # Add metadata if provided
        if metadata:
            params['Metadata'] = metadata
            params['MetadataDirective'] = 'REPLACE'
        
        response = client.copy_object(**params)
        logger.debug(f"Successfully copied document")
        return response
    
    except ClientError as e:
        logger.error(f"Failed to copy document: {str(e)}")
        raise


def generate_presigned_post(bucket: str, key: str, 
                           fields: Optional[Dict[str, str]] = None,
                           conditions: Optional[List[Any]] = None,
                           expiration: int = DEFAULT_EXPIRATION,
                           s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Generate a presigned POST request for uploading a document.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        fields: Dictionary of prefilled form fields
        conditions: List of conditions to include in the policy
        expiration: URL expiration time in seconds (default: 1 hour)
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the presigned POST data
        
    Raises:
        ClientError: If presigned POST cannot be generated
    """
    client = s3_client or get_s3_client()
    
    # Ensure ServerSideEncryption is set to AES256
    if not fields:
        fields = {}
    fields['ServerSideEncryption'] = 'AES256'
    
    # Add encryption condition if not already present
    if not conditions:
        conditions = []
    if {'ServerSideEncryption': 'AES256'} not in conditions:
        conditions.append({'ServerSideEncryption': 'AES256'})
    
    try:
        logger.info(f"Generating presigned POST for s3://{bucket}/{key} (expires in {expiration}s)")
        response = client.generate_presigned_post(
            Bucket=bucket,
            Key=key,
            Fields=fields,
            Conditions=conditions,
            ExpiresIn=expiration
        )
        
        logger.debug(f"Successfully generated presigned POST")
        return response
    
    except ClientError as e:
        logger.error(f"Failed to generate presigned POST: {str(e)}")
        raise


def ensure_bucket_encryption(bucket: str, s3_client: Optional[boto3.client] = None) -> bool:
    """
    Ensure that a bucket has AES-256 encryption enabled.
    If not, attempt to enable it.
    
    Args:
        bucket: S3 bucket name
        s3_client: Existing S3 client (optional)
        
    Returns:
        True if encryption is enabled, False otherwise
        
    Raises:
        ClientError: If encryption cannot be checked or enabled
    """
    client = s3_client or get_s3_client()
    
    # Check current encryption status
    encryption_config = get_bucket_encryption_status(bucket, client)
    if encryption_config:
        logger.info(f"Bucket {bucket} already has encryption configured")
        return True
    
    # Try to enable encryption
    try:
        logger.info(f"Enabling AES-256 encryption for bucket {bucket}")
        client.put_bucket_encryption(
            Bucket=bucket,
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
        logger.info(f"Successfully enabled encryption for bucket {bucket}")
        return True
    
    except ClientError as e:
        logger.error(f"Failed to enable encryption for bucket {bucket}: {str(e)}")
        return False


def get_document_metadata(bucket: str, key: str, s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Get metadata for a document without downloading the content.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing document metadata
        
    Raises:
        ClientError: If metadata cannot be retrieved
    """
    client = s3_client or get_s3_client()
    
    try:
        logger.info(f"Getting metadata for s3://{bucket}/{key}")
        response = client.head_object(Bucket=bucket, Key=key)
        
        metadata = {
            'ContentType': response.get('ContentType', 'application/octet-stream'),
            'ContentLength': response.get('ContentLength', 0),
            'LastModified': response.get('LastModified'),
            'ETag': response.get('ETag'),
            'VersionId': response.get('VersionId'),
            'ServerSideEncryption': response.get('ServerSideEncryption'),
            'Metadata': response.get('Metadata', {})
        }
        
        logger.debug(f"Successfully retrieved metadata for s3://{bucket}/{key}")
        return metadata
    
    except ClientError as e:
        logger.error(f"Failed to get document metadata: {str(e)}")
        raise


def create_document_key(document_type: str, document_id: str, extension: str = 'pdf') -> str:
    """
    Create a standardized S3 key for a document based on type and ID.
    
    Args:
        document_type: Type of document (e.g., 'application_form', 'tax_return')
        document_id: Unique identifier for the document
        extension: File extension (default: 'pdf')
        
    Returns:
        Standardized S3 key
    """
    # Ensure extension doesn't have a leading dot
    if extension.startswith('.'):
        extension = extension[1:]
    
    # Create timestamp-based path component for organization
    timestamp = time.strftime('%Y/%m/%d', time.gmtime())
    
    # Create standardized key
    key = f"{document_type}/{timestamp}/{document_id}.{extension}"
    
    return key


def create_extracted_data_key(document_key: str) -> str:
    """
    Create a standardized S3 key for extracted data based on the original document key.
    
    Args:
        document_key: Original document S3 key
        
    Returns:
        Standardized S3 key for extracted data
    """
    # Remove file extension
    base_key = document_key.rsplit('.', 1)[0] if '.' in document_key else document_key
    
    # Create extracted data key
    extracted_key = f"{base_key}/extracted_data.json"
    
    return extracted_key


def batch_download_documents(bucket: str, keys: List[str], 
                           s3_client: Optional[boto3.client] = None) -> Dict[str, Tuple[bytes, Dict[str, Any]]]:
    """
    Download multiple documents from S3 storage in parallel.
    
    Args:
        bucket: S3 bucket name
        keys: List of S3 object keys
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict mapping keys to tuples of (content, metadata)
        
    Raises:
        ClientError: If documents cannot be downloaded
    """
    client = s3_client or get_s3_client()
    results = {}
    errors = {}
    
    # Import concurrent.futures here to avoid dependency issues
    import concurrent.futures
    
    def download_single(key):
        try:
            content, metadata = download_document(bucket, key, client)
            return key, (content, metadata)
        except Exception as e:
            return key, e
    
    # Use ThreadPoolExecutor for parallel downloads
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_key = {executor.submit(download_single, key): key for key in keys}
        
        for future in concurrent.futures.as_completed(future_to_key):
            key = future_to_key[future]
            try:
                result_key, result_value = future.result()
                if isinstance(result_value, Exception):
                    errors[result_key] = result_value
                else:
                    results[result_key] = result_value
            except Exception as e:
                errors[key] = e
    
    # Log errors if any
    if errors:
        logger.error(f"Failed to download {len(errors)} documents: {errors}")
    
    logger.info(f"Successfully downloaded {len(results)} documents")
    return results


def is_document_encrypted(bucket: str, key: str, s3_client: Optional[boto3.client] = None) -> bool:
    """
    Check if a document is encrypted with AES-256.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        s3_client: Existing S3 client (optional)
        
    Returns:
        True if document is encrypted with AES-256, False otherwise
    """
    client = s3_client or get_s3_client()
    
    try:
        metadata = get_document_metadata(bucket, key, client)
        encryption = metadata.get('ServerSideEncryption')
        
        return encryption == 'AES256'
    
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            logger.warning(f"Document does not exist at s3://{bucket}/{key}")
            return False
        else:
            logger.error(f"Error checking document encryption: {str(e)}")
            raise


def get_document_url(bucket: str, key: str, expiration: int = DEFAULT_EXPIRATION,
                    s3_client: Optional[boto3.client] = None) -> str:
    """
    Convenience function to generate a presigned URL for a document.
    Alias for generate_presigned_url.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        expiration: URL expiration time in seconds (default: 1 hour)
        s3_client: Existing S3 client (optional)
        
    Returns:
        Presigned URL as string
    """
    return generate_presigned_url(bucket, key, expiration, s3_client)


def get_document_from_uri(uri: str, s3_client: Optional[boto3.client] = None) -> Tuple[bytes, Dict[str, Any]]:
    """
    Download a document using an S3 URI (s3://bucket/key).
    
    Args:
        uri: S3 URI in the format s3://bucket/key
        s3_client: Existing S3 client (optional)
        
    Returns:
        Tuple containing:
            - Document content as bytes
            - Metadata dictionary
    """
    bucket, key = parse_s3_uri(uri)
    return download_document(bucket, key, s3_client)


def upload_document_with_uri(uri: str, document: Union[bytes, BinaryIO],
                           content_type: Optional[str] = None,
                           metadata: Optional[Dict[str, str]] = None,
                           s3_client: Optional[boto3.client] = None) -> Dict[str, Any]:
    """
    Upload a document using an S3 URI (s3://bucket/key).
    
    Args:
        uri: S3 URI in the format s3://bucket/key
        document: Document content as bytes or file-like object
        content_type: MIME type of the document
        metadata: Custom metadata to attach to the document
        s3_client: Existing S3 client (optional)
        
    Returns:
        Dict containing the S3 response
    """
    bucket, key = parse_s3_uri(uri)
    return upload_document(bucket, key, document, content_type, metadata, s3_client)


# Main section for testing
if __name__ == "__main__":
    # Configure logging for testing
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    try:
        # Initialize S3 client
        s3_client = get_s3_client()
        
        # Check if bucket exists and has encryption enabled
        bucket = DEFAULT_DOCUMENT_BUCKET
        logger.info(f"Checking encryption for bucket: {bucket}")
        encryption_status = get_bucket_encryption_status(bucket, s3_client)
        
        if encryption_status:
            logger.info(f"Bucket {bucket} has encryption enabled: {encryption_status}")
        else:
            logger.warning(f"Bucket {bucket} does not have encryption enabled")
            logger.info("Enabling encryption...")
            ensure_bucket_encryption(bucket, s3_client)
        
        # Example document key
        document_key = create_document_key('application_form', 'test-document')
        logger.info(f"Generated document key: {document_key}")
        
        # Example extracted data key
        extracted_key = create_extracted_data_key(document_key)
        logger.info(f"Generated extracted data key: {extracted_key}")
        
        logger.info("S3 utility module test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()