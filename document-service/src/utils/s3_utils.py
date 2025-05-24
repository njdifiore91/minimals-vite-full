"""
S3 Storage Utilities for Document Service.

This module provides utility functions for interacting with S3-compatible storage,
including document upload, download, metadata management, and secure access through
signed URLs. It builds on the base S3 configuration to provide document-specific
functionality for the Document Service.
"""

import os
import json
import uuid
import logging
from typing import Dict, Optional, Any, BinaryIO, Union, Tuple, List
from datetime import datetime, timedelta
import mimetypes
import io

import boto3
from botocore.exceptions import ClientError

from ..config.s3_config import (
    create_s3_client,
    create_s3_resource,
    get_bucket_name,
    s3_client,
    s3_resource
)

# Configure logging
logger = logging.getLogger(__name__)

# Constants
DEFAULT_EXPIRATION = 3600  # Default signed URL expiration in seconds (1 hour)
DOCUMENT_PREFIX = 'documents/'  # Prefix for document storage in S3
METADATA_PREFIX = 'metadata/'  # Prefix for metadata storage in S3


def generate_document_key(document_type: str, file_extension: str = None) -> str:
    """Generate a unique S3 object key for a document.

    Args:
        document_type (str): Type of document (e.g., 'application', 'tax_return', 'bank_statement').
        file_extension (str, optional): File extension. Defaults to None.

    Returns:
        str: Unique S3 object key.
    """
    # Generate a UUID for uniqueness
    unique_id = str(uuid.uuid4())
    
    # Generate a timestamp for organization
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    
    # Construct the key with proper organization
    key = f"{DOCUMENT_PREFIX}{document_type}/{timestamp}-{unique_id}"
    
    # Add file extension if provided
    if file_extension:
        # Ensure extension starts with a dot
        if not file_extension.startswith('.'):
            file_extension = f'.{file_extension}'
        key = f"{key}{file_extension}"
    
    return key


def upload_document(file_path: str, document_type: str, classification_metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Upload a document to S3 with classification metadata and AES-256 encryption.

    Args:
        file_path (str): Path to the document file to upload.
        document_type (str): Type of document (e.g., 'application', 'tax_return').
        classification_metadata (Dict[str, Any]): Classification metadata for the document.

    Returns:
        Tuple[bool, Optional[str]]: Tuple containing success status and object key if successful.
    """
    try:
        # Determine file extension
        _, file_extension = os.path.splitext(file_path)
        
        # Generate a unique object key
        object_key = generate_document_key(document_type, file_extension)
        
        # Determine content type
        content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        
        # Prepare metadata - convert all values to strings for S3 compatibility
        string_metadata = {}
        for key, value in classification_metadata.items():
            if isinstance(value, (dict, list)):
                string_metadata[key] = json.dumps(value)
            else:
                string_metadata[key] = str(value)
        
        # Add document type to metadata
        string_metadata['document_type'] = document_type
        
        # Add timestamp to metadata
        string_metadata['upload_timestamp'] = datetime.now().isoformat()
        
        # Upload the file with encryption and metadata
        bucket_name = get_bucket_name()
        s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=object_key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',  # Enable AES-256 encryption
                'ContentType': content_type,
                'Metadata': string_metadata
            }
        )
        
        logger.info(f"Successfully uploaded document to {bucket_name}/{object_key} with encryption and metadata")
        return True, object_key
    except ClientError as e:
        logger.error(f"Error uploading document to S3: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error uploading document to S3: {str(e)}")
        return False, None


def upload_document_from_bytes(file_bytes: bytes, document_type: str, file_name: str,
                               classification_metadata: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Upload a document from bytes to S3 with classification metadata and AES-256 encryption.
    
    This is particularly useful when processing documents from memory, such as
    when receiving documents from message queues or API requests.

    Args:
        file_bytes (bytes): Document content as bytes.
        document_type (str): Type of document (e.g., 'application', 'tax_return').
        file_name (str): Original file name (used for content type detection).
        classification_metadata (Dict[str, Any]): Classification metadata for the document.

    Returns:
        Tuple[bool, Optional[str]]: Tuple containing success status and object key if successful.
    """
    try:
        # Determine file extension
        _, file_extension = os.path.splitext(file_name)
        
        # Generate a unique object key
        object_key = generate_document_key(document_type, file_extension)
        
        # Determine content type
        content_type = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
        
        # Prepare metadata - convert all values to strings for S3 compatibility
        string_metadata = {}
        for key, value in classification_metadata.items():
            if isinstance(value, (dict, list)):
                string_metadata[key] = json.dumps(value)
            else:
                string_metadata[key] = str(value)
        
        # Add document type to metadata
        string_metadata['document_type'] = document_type
        string_metadata['original_filename'] = file_name
        
        # Add timestamp to metadata
        string_metadata['upload_timestamp'] = datetime.now().isoformat()
        
        # Upload the file with encryption and metadata
        bucket_name = get_bucket_name()
        s3_client.put_object(
            Body=file_bytes,
            Bucket=bucket_name,
            Key=object_key,
            ServerSideEncryption='AES256',  # Enable AES-256 encryption
            ContentType=content_type,
            Metadata=string_metadata
        )
        
        logger.info(f"Successfully uploaded document bytes to {bucket_name}/{object_key} with encryption and metadata")
        return True, object_key
    except ClientError as e:
        logger.error(f"Error uploading document bytes to S3: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error uploading document bytes to S3: {str(e)}")
        return False, None


def download_document(object_key: str, download_path: str) -> bool:
    """Download a document from S3 to a local file path.

    Args:
        object_key (str): S3 object key of the document to download.
        download_path (str): Local path where the document should be saved.

    Returns:
        bool: True if download was successful, False otherwise.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(download_path), exist_ok=True)
        
        # Download the file
        s3_client.download_file(
            Bucket=bucket_name,
            Key=object_key,
            Filename=download_path
        )
        
        logger.info(f"Successfully downloaded {bucket_name}/{object_key} to {download_path}")
        return True
    except ClientError as e:
        logger.error(f"Error downloading document from S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading document from S3: {str(e)}")
        return False


def download_document_to_bytes(object_key: str) -> Tuple[bool, Optional[bytes], Optional[Dict[str, str]]]:
    """Download a document from S3 and return it as bytes along with its metadata.

    Args:
        object_key (str): S3 object key of the document to download.

    Returns:
        Tuple[bool, Optional[bytes], Optional[Dict[str, str]]]: 
            Tuple containing success status, document bytes if successful, and metadata.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Get the object and its metadata
        response = s3_client.get_object(
            Bucket=bucket_name,
            Key=object_key
        )
        
        # Read the file content
        file_content = response['Body'].read()
        
        # Get the metadata
        metadata = response.get('Metadata', {})
        
        logger.info(f"Successfully downloaded {bucket_name}/{object_key} to memory")
        return True, file_content, metadata
    except ClientError as e:
        logger.error(f"Error downloading document from S3 to memory: {str(e)}")
        return False, None, None
    except Exception as e:
        logger.error(f"Unexpected error downloading document from S3 to memory: {str(e)}")
        return False, None, None


def get_document_metadata(object_key: str) -> Tuple[bool, Optional[Dict[str, str]]]:
    """Retrieve metadata for a document stored in S3.

    Args:
        object_key (str): S3 object key of the document.

    Returns:
        Tuple[bool, Optional[Dict[str, str]]]: Tuple containing success status and metadata if successful.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Get the object metadata
        response = s3_client.head_object(
            Bucket=bucket_name,
            Key=object_key
        )
        
        # Extract metadata
        metadata = response.get('Metadata', {})
        
        # Add system metadata
        system_metadata = {
            'content_type': response.get('ContentType', 'application/octet-stream'),
            'content_length': str(response.get('ContentLength', 0)),
            'last_modified': response.get('LastModified', datetime.now()).isoformat(),
            'e_tag': response.get('ETag', '').strip('"'),
            'server_side_encryption': response.get('ServerSideEncryption', 'None')
        }
        
        # Combine user and system metadata
        combined_metadata = {**metadata, **system_metadata}
        
        logger.info(f"Successfully retrieved metadata for {bucket_name}/{object_key}")
        return True, combined_metadata
    except ClientError as e:
        logger.error(f"Error retrieving document metadata from S3: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error retrieving document metadata from S3: {str(e)}")
        return False, None


def update_document_metadata(object_key: str, metadata: Dict[str, str]) -> bool:
    """Update metadata for a document stored in S3.
    
    Note: This creates a copy of the object with new metadata, as S3 doesn't allow
    direct metadata updates.

    Args:
        object_key (str): S3 object key of the document.
        metadata (Dict[str, str]): New metadata to apply to the document.

    Returns:
        bool: True if update was successful, False otherwise.
    """
    try:
        bucket_name = get_bucket_name()
        
        # First, get existing metadata and object info
        success, existing_metadata = get_document_metadata(object_key)
        if not success:
            logger.error(f"Failed to retrieve existing metadata for {bucket_name}/{object_key}")
            return False
        
        # Get content type from existing metadata
        content_type = existing_metadata.get('content_type', 'application/octet-stream')
        
        # Prepare metadata - convert all values to strings for S3 compatibility
        string_metadata = {}
        for key, value in metadata.items():
            if isinstance(value, (dict, list)):
                string_metadata[key] = json.dumps(value)
            else:
                string_metadata[key] = str(value)
        
        # Copy the object to itself with new metadata
        s3_client.copy_object(
            CopySource={'Bucket': bucket_name, 'Key': object_key},
            Bucket=bucket_name,
            Key=object_key,
            MetadataDirective='REPLACE',
            ContentType=content_type,
            Metadata=string_metadata,
            ServerSideEncryption='AES256'  # Maintain encryption
        )
        
        logger.info(f"Successfully updated metadata for {bucket_name}/{object_key}")
        return True
    except ClientError as e:
        logger.error(f"Error updating document metadata in S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error updating document metadata in S3: {str(e)}")
        return False


def generate_presigned_url(object_key: str, expiration: int = DEFAULT_EXPIRATION, 
                          http_method: str = 'GET') -> Tuple[bool, Optional[str]]:
    """Generate a presigned URL for secure access to a document.

    Args:
        object_key (str): S3 object key of the document.
        expiration (int, optional): URL expiration time in seconds. Defaults to DEFAULT_EXPIRATION (1 hour).
        http_method (str, optional): HTTP method for the URL. Defaults to 'GET'.

    Returns:
        Tuple[bool, Optional[str]]: Tuple containing success status and presigned URL if successful.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Generate the presigned URL
        url = s3_client.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration,
            HttpMethod=http_method
        )
        
        logger.info(f"Successfully generated presigned URL for {bucket_name}/{object_key} (expires in {expiration}s)")
        return True, url
    except ClientError as e:
        logger.error(f"Error generating presigned URL: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error generating presigned URL: {str(e)}")
        return False, None


def list_documents_by_type(document_type: str, max_items: int = 1000) -> Tuple[bool, Optional[List[Dict[str, Any]]]]:
    """List documents of a specific type stored in S3.

    Args:
        document_type (str): Type of documents to list.
        max_items (int, optional): Maximum number of items to return. Defaults to 1000.

    Returns:
        Tuple[bool, Optional[List[Dict[str, Any]]]]: 
            Tuple containing success status and list of document information if successful.
    """
    try:
        bucket_name = get_bucket_name()
        prefix = f"{DOCUMENT_PREFIX}{document_type}/"
        
        # List objects with the specified prefix
        paginator = s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=bucket_name,
            Prefix=prefix,
            PaginationConfig={
                'MaxItems': max_items,
                'PageSize': 100
            }
        )
        
        # Collect document information
        documents = []
        for page in page_iterator:
            if 'Contents' in page:
                for obj in page['Contents']:
                    # Get object key and basic info
                    obj_key = obj['Key']
                    obj_info = {
                        'key': obj_key,
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'e_tag': obj['ETag'].strip('"')
                    }
                    
                    # Get metadata for each object
                    success, metadata = get_document_metadata(obj_key)
                    if success:
                        obj_info['metadata'] = metadata
                    
                    documents.append(obj_info)
        
        logger.info(f"Successfully listed {len(documents)} documents of type '{document_type}'")
        return True, documents
    except ClientError as e:
        logger.error(f"Error listing documents by type: {str(e)}")
        return False, None
    except Exception as e:
        logger.error(f"Unexpected error listing documents by type: {str(e)}")
        return False, None


def delete_document(object_key: str) -> bool:
    """Delete a document from S3.

    Args:
        object_key (str): S3 object key of the document to delete.

    Returns:
        bool: True if deletion was successful, False otherwise.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Delete the object
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=object_key
        )
        
        logger.info(f"Successfully deleted document {bucket_name}/{object_key}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting document from S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error deleting document from S3: {str(e)}")
        return False


def copy_document(source_key: str, dest_key: str, new_metadata: Optional[Dict[str, str]] = None) -> bool:
    """Copy a document within S3, optionally updating its metadata.

    Args:
        source_key (str): S3 object key of the source document.
        dest_key (str): S3 object key for the destination.
        new_metadata (Optional[Dict[str, str]], optional): New metadata to apply. Defaults to None.

    Returns:
        bool: True if copy was successful, False otherwise.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Prepare copy parameters
        copy_params = {
            'CopySource': {'Bucket': bucket_name, 'Key': source_key},
            'Bucket': bucket_name,
            'Key': dest_key,
            'ServerSideEncryption': 'AES256'  # Maintain encryption
        }
        
        # If new metadata is provided, apply it
        if new_metadata:
            # Get existing metadata to preserve content type
            success, existing_metadata = get_document_metadata(source_key)
            if success:
                content_type = existing_metadata.get('content_type', 'application/octet-stream')
                copy_params['ContentType'] = content_type
            
            # Prepare metadata - convert all values to strings for S3 compatibility
            string_metadata = {}
            for key, value in new_metadata.items():
                if isinstance(value, (dict, list)):
                    string_metadata[key] = json.dumps(value)
                else:
                    string_metadata[key] = str(value)
            
            copy_params['MetadataDirective'] = 'REPLACE'
            copy_params['Metadata'] = string_metadata
        
        # Copy the object
        s3_client.copy_object(**copy_params)
        
        logger.info(f"Successfully copied document from {bucket_name}/{source_key} to {bucket_name}/{dest_key}")
        return True
    except ClientError as e:
        logger.error(f"Error copying document in S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error copying document in S3: {str(e)}")
        return False


def check_document_exists(object_key: str) -> bool:
    """Check if a document exists in S3.

    Args:
        object_key (str): S3 object key of the document to check.

    Returns:
        bool: True if the document exists, False otherwise.
    """
    try:
        bucket_name = get_bucket_name()
        
        # Check if object exists
        s3_client.head_object(
            Bucket=bucket_name,
            Key=object_key
        )
        
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404' or error_code == 'NoSuchKey':
            logger.info(f"Document {bucket_name}/{object_key} does not exist")
        else:
            logger.error(f"Error checking if document exists: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking if document exists: {str(e)}")
        return False


def get_document_classification(object_key: str) -> Tuple[bool, Optional[str], Optional[float]]:
    """Get the classification type and confidence score for a document.

    Args:
        object_key (str): S3 object key of the document.

    Returns:
        Tuple[bool, Optional[str], Optional[float]]: 
            Tuple containing success status, classification type if successful, and confidence score.
    """
    try:
        # Get document metadata
        success, metadata = get_document_metadata(object_key)
        if not success:
            logger.error(f"Failed to retrieve metadata for classification")
            return False, None, None
        
        # Extract classification information
        document_type = metadata.get('document_type')
        confidence_str = metadata.get('classification_confidence', '0.0')
        
        # Convert confidence to float
        try:
            confidence = float(confidence_str)
        except (ValueError, TypeError):
            confidence = 0.0
        
        logger.info(f"Retrieved classification for document: {document_type} (confidence: {confidence})")
        return True, document_type, confidence
    except Exception as e:
        logger.error(f"Unexpected error retrieving document classification: {str(e)}")
        return False, None, None


def add_classification_metadata(object_key: str, document_type: str, 
                               confidence: float, additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
    """Add or update classification metadata for a document.

    Args:
        object_key (str): S3 object key of the document.
        document_type (str): Classification type of the document.
        confidence (float): Confidence score of the classification (0.0 to 1.0).
        additional_metadata (Optional[Dict[str, Any]], optional): Additional metadata to add. Defaults to None.

    Returns:
        bool: True if update was successful, False otherwise.
    """
    try:
        # Get existing metadata
        success, existing_metadata = get_document_metadata(object_key)
        if not success:
            logger.error(f"Failed to retrieve existing metadata for classification update")
            return False
        
        # Prepare new metadata
        new_metadata = {
            'document_type': document_type,
            'classification_confidence': str(confidence),
            'classification_timestamp': datetime.now().isoformat()
        }
        
        # Add additional metadata if provided
        if additional_metadata:
            for key, value in additional_metadata.items():
                new_metadata[key] = value
        
        # Update document metadata
        return update_document_metadata(object_key, new_metadata)
    except Exception as e:
        logger.error(f"Unexpected error adding classification metadata: {str(e)}")
        return False