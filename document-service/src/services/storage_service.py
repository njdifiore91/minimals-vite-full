"""Storage Service for Document Service microservice.

This module provides S3-compatible storage operations for the Document Service,
handling document retrieval, storage, and management with secure AES-256 encryption.
It includes functionality for uploading, downloading, and managing documents with
proper error handling and retry logic.
"""

import os
import logging
import tempfile
from typing import Dict, Optional, Any, Tuple, List, BinaryIO, Union
from pathlib import Path
import uuid
import json
import time
from datetime import datetime, timedelta

import boto3
from botocore.exceptions import ClientError

from ..config import s3_config
from ..types.storage import StorageMetadata, StorageResult

# Configure logging
logger = logging.getLogger(__name__)

class StorageService:
    """Service for handling S3-compatible storage operations.
    
    This class provides methods for document retrieval, storage, and management
    with secure AES-256 encryption. It handles error conditions and implements
    retry logic for storage operations.
    """
    
    def __init__(self):
        """Initialize the StorageService with S3 client and configuration."""
        self.s3_client = s3_config.create_s3_client()
        self.s3_resource = s3_config.create_s3_resource()
        self.bucket_name = s3_config.get_bucket_name()
        
        # Ensure the bucket exists
        if not s3_config.check_bucket_exists(self.bucket_name):
            logger.warning(f"Bucket {self.bucket_name} does not exist. Attempting to create it.")
            s3_config.create_bucket_if_not_exists(self.bucket_name)
            
        # Maximum number of retries for operations
        self.max_retries = 3
        # Base delay for exponential backoff (in seconds)
        self.base_delay = 1
        # Default expiration time for signed URLs (in seconds)
        self.default_url_expiration = 3600  # 1 hour
        # Temporary directory for downloaded files
        self.temp_dir = tempfile.gettempdir()
        
        logger.info(f"StorageService initialized with bucket: {self.bucket_name}")
        
    def _generate_object_key(self, document_id: str, file_name: str) -> str:
        """Generate a unique object key for storing a document in S3.
        
        Args:
            document_id (str): Unique identifier for the document.
            file_name (str): Original file name of the document.
            
        Returns:
            str: Generated object key for S3 storage.
        """
        # Extract file extension
        _, ext = os.path.splitext(file_name)
        
        # Generate a timestamp-based path to organize files
        now = datetime.now()
        date_path = now.strftime("%Y/%m/%d")
        
        # Create the object key with a structured path
        return f"documents/{date_path}/{document_id}{ext}"
    
    def _with_retry(self, operation_func, *args, **kwargs) -> Any:
        """Execute an operation with retry logic using exponential backoff.
        
        Args:
            operation_func: Function to execute with retry logic.
            *args: Positional arguments to pass to the function.
            **kwargs: Keyword arguments to pass to the function.
            
        Returns:
            Any: Result of the operation function if successful.
            
        Raises:
            Exception: The last exception encountered after all retries fail.
        """
        last_exception = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                return operation_func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                # Calculate delay with exponential backoff
                delay = self.base_delay * (2 ** (attempt - 1))
                
                logger.warning(
                    f"Operation failed (attempt {attempt}/{self.max_retries}): {str(e)}. "
                    f"Retrying in {delay} seconds..."
                )
                
                time.sleep(delay)
        
        # If we get here, all retries failed
        logger.error(f"Operation failed after {self.max_retries} attempts: {str(last_exception)}")
        raise last_exception
    
    def upload_document(self, file_path: str, document_id: str, 
                        metadata: Optional[Dict[str, str]] = None) -> StorageResult:
        """Upload a document to S3 storage with AES-256 encryption.
        
        Args:
            file_path (str): Path to the file to upload.
            document_id (str): Unique identifier for the document.
            metadata (Optional[Dict[str, str]], optional): Metadata to attach to the document.
                Defaults to None.
                
        Returns:
            StorageResult: Result of the upload operation containing success status,
                object key, and error message if applicable.
        """
        try:
            # Get the file name from the path
            file_name = os.path.basename(file_path)
            
            # Generate the object key
            object_key = self._generate_object_key(document_id, file_name)
            
            # Prepare metadata with additional information
            full_metadata = {
                'document_id': document_id,
                'original_filename': file_name,
                'upload_timestamp': datetime.now().isoformat(),
            }
            
            # Add custom metadata if provided
            if metadata:
                full_metadata.update(metadata)
            
            # Upload the file with retry logic
            def upload_operation():
                # Prepare extra arguments for upload
                extra_args = {
                    'ServerSideEncryption': 'AES256',  # Enable AES-256 encryption
                    'Metadata': full_metadata
                }
                
                # Upload the file with encryption
                self.s3_client.upload_file(
                    Filename=file_path,
                    Bucket=self.bucket_name,
                    Key=object_key,
                    ExtraArgs=extra_args
                )
                
                return object_key
            
            # Execute the upload with retry logic
            object_key = self._with_retry(upload_operation)
            
            logger.info(f"Successfully uploaded document {document_id} to {self.bucket_name}/{object_key}")
            
            return StorageResult(
                success=True,
                object_key=object_key,
                error=None
            )
            
        except Exception as e:
            error_msg = f"Failed to upload document {document_id}: {str(e)}"
            logger.error(error_msg)
            
            return StorageResult(
                success=False,
                object_key=None,
                error=error_msg
            )
    
    def upload_document_from_bytes(self, file_bytes: bytes, file_name: str, document_id: str,
                                  metadata: Optional[Dict[str, str]] = None) -> StorageResult:
        """Upload a document from bytes to S3 storage with AES-256 encryption.
        
        Args:
            file_bytes (bytes): Document content as bytes.
            file_name (str): Original file name.
            document_id (str): Unique identifier for the document.
            metadata (Optional[Dict[str, str]], optional): Metadata to attach to the document.
                Defaults to None.
                
        Returns:
            StorageResult: Result of the upload operation containing success status,
                object key, and error message if applicable.
        """
        try:
            # Create a temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(file_bytes)
                temp_path = temp_file.name
            
            try:
                # Upload the document using the temporary file
                result = self.upload_document(temp_path, document_id, metadata)
                return result
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            error_msg = f"Failed to upload document {document_id} from bytes: {str(e)}"
            logger.error(error_msg)
            
            return StorageResult(
                success=False,
                object_key=None,
                error=error_msg
            )
    
    def download_document(self, object_key: str) -> Tuple[Optional[str], Optional[str]]:
        """Download a document from S3 storage to a temporary file.
        
        Args:
            object_key (str): S3 object key of the document to download.
            
        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing the path to the downloaded file
                and an error message if applicable. If download fails, the file path will be None.
        """
        try:
            # Generate a temporary file path
            file_name = os.path.basename(object_key)
            temp_path = os.path.join(self.temp_dir, f"{uuid.uuid4()}_{file_name}")
            
            # Download the file with retry logic
            def download_operation():
                self.s3_client.download_file(
                    Bucket=self.bucket_name,
                    Key=object_key,
                    Filename=temp_path
                )
                return temp_path
            
            # Execute the download with retry logic
            temp_path = self._with_retry(download_operation)
            
            logger.info(f"Successfully downloaded {self.bucket_name}/{object_key} to {temp_path}")
            
            return temp_path, None
            
        except Exception as e:
            error_msg = f"Failed to download document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return None, error_msg
    
    def download_document_as_bytes(self, object_key: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Download a document from S3 storage and return its contents as bytes.
        
        Args:
            object_key (str): S3 object key of the document to download.
            
        Returns:
            Tuple[Optional[bytes], Optional[str]]: A tuple containing the document content as bytes
                and an error message if applicable. If download fails, the content will be None.
        """
        try:
            # Download to temporary file first
            temp_path, error = self.download_document(object_key)
            
            if error or not temp_path:
                return None, error
            
            try:
                # Read the file content
                with open(temp_path, 'rb') as file:
                    content = file.read()
                
                return content, None
            finally:
                # Clean up the temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            error_msg = f"Failed to download document {object_key} as bytes: {str(e)}"
            logger.error(error_msg)
            
            return None, error_msg
    
    def get_document_metadata(self, object_key: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
        """Retrieve metadata for a document stored in S3.
        
        Args:
            object_key (str): S3 object key of the document.
            
        Returns:
            Tuple[Optional[Dict[str, str]], Optional[str]]: A tuple containing the document metadata
                and an error message if applicable. If retrieval fails, the metadata will be None.
        """
        try:
            # Get object metadata with retry logic
            def get_metadata_operation():
                response = self.s3_client.head_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
                return response
            
            # Execute the operation with retry logic
            response = self._with_retry(get_metadata_operation)
            
            # Extract metadata from the response
            metadata = response.get('Metadata', {})
            
            # Add system metadata
            system_metadata = {
                'content_length': str(response.get('ContentLength', 0)),
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'last_modified': response.get('LastModified', datetime.now()).isoformat(),
                'server_side_encryption': response.get('ServerSideEncryption', 'None'),
                'e_tag': response.get('ETag', '').strip('"'),
            }
            
            # Combine user and system metadata
            combined_metadata = {**system_metadata, **metadata}
            
            logger.info(f"Successfully retrieved metadata for {self.bucket_name}/{object_key}")
            
            return combined_metadata, None
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            
            if error_code == '404' or error_code == 'NoSuchKey':
                error_msg = f"Document {object_key} not found"
            else:
                error_msg = f"Failed to retrieve metadata for document {object_key}: {str(e)}"
                
            logger.error(error_msg)
            return None, error_msg
            
        except Exception as e:
            error_msg = f"Unexpected error retrieving metadata for document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return None, error_msg
    
    def update_document_metadata(self, object_key: str, metadata: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """Update metadata for a document stored in S3.
        
        Args:
            object_key (str): S3 object key of the document.
            metadata (Dict[str, str]): New metadata to apply to the document.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a success flag and an error message
                if applicable. If the update fails, the success flag will be False.
        """
        try:
            # Get current metadata first to preserve existing values
            current_metadata, error = self.get_document_metadata(object_key)
            
            if error or not current_metadata:
                return False, error or "Failed to retrieve current metadata"
            
            # Extract user metadata (excluding system metadata)
            user_metadata = {}
            for key, value in current_metadata.items():
                if key not in ['content_length', 'content_type', 'last_modified', 'server_side_encryption', 'e_tag']:
                    user_metadata[key] = value
            
            # Update with new metadata
            updated_metadata = {**user_metadata, **metadata}
            
            # Copy the object to itself with new metadata
            def update_metadata_operation():
                self.s3_client.copy_object(
                    Bucket=self.bucket_name,
                    CopySource={'Bucket': self.bucket_name, 'Key': object_key},
                    Key=object_key,
                    Metadata=updated_metadata,
                    MetadataDirective='REPLACE',
                    ServerSideEncryption='AES256'  # Maintain encryption
                )
                return True
            
            # Execute the operation with retry logic
            self._with_retry(update_metadata_operation)
            
            logger.info(f"Successfully updated metadata for {self.bucket_name}/{object_key}")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to update metadata for document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return False, error_msg
    
    def delete_document(self, object_key: str) -> Tuple[bool, Optional[str]]:
        """Delete a document from S3 storage.
        
        Args:
            object_key (str): S3 object key of the document to delete.
            
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a success flag and an error message
                if applicable. If the deletion fails, the success flag will be False.
        """
        try:
            # Delete the object with retry logic
            def delete_operation():
                self.s3_client.delete_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
                return True
            
            # Execute the operation with retry logic
            self._with_retry(delete_operation)
            
            logger.info(f"Successfully deleted document {self.bucket_name}/{object_key}")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to delete document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return False, error_msg
    
    def generate_presigned_url(self, object_key: str, expiration: int = None) -> Tuple[Optional[str], Optional[str]]:
        """Generate a presigned URL for temporary access to a document.
        
        Args:
            object_key (str): S3 object key of the document.
            expiration (int, optional): URL expiration time in seconds. 
                Defaults to None, which uses the default expiration time.
                
        Returns:
            Tuple[Optional[str], Optional[str]]: A tuple containing the presigned URL
                and an error message if applicable. If generation fails, the URL will be None.
        """
        try:
            # Use default expiration if not specified
            if expiration is None:
                expiration = self.default_url_expiration
            
            # Generate the URL with retry logic
            def generate_url_operation():
                url = self.s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': self.bucket_name,
                        'Key': object_key
                    },
                    ExpiresIn=expiration
                )
                return url
            
            # Execute the operation with retry logic
            url = self._with_retry(generate_url_operation)
            
            logger.info(f"Generated presigned URL for {self.bucket_name}/{object_key} (expires in {expiration} seconds)")
            
            return url, None
            
        except Exception as e:
            error_msg = f"Failed to generate presigned URL for document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return None, error_msg
    
    def list_documents(self, prefix: str = None, max_items: int = 1000) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """List documents in the S3 bucket with optional prefix filtering.
        
        Args:
            prefix (str, optional): Prefix to filter objects by. Defaults to None.
            max_items (int, optional): Maximum number of items to return. Defaults to 1000.
            
        Returns:
            Tuple[Optional[List[Dict[str, Any]]], Optional[str]]: A tuple containing a list of document
                information dictionaries and an error message if applicable. If listing fails, the list will be None.
        """
        try:
            # List objects with retry logic
            def list_operation():
                paginator = self.s3_client.get_paginator('list_objects_v2')
                
                # Prepare pagination parameters
                pagination_config = {
                    'MaxItems': max_items,
                    'PageSize': 100  # Number of items per page
                }
                
                # Prepare list parameters
                list_params = {
                    'Bucket': self.bucket_name
                }
                
                # Add prefix if specified
                if prefix:
                    list_params['Prefix'] = prefix
                
                # Get paginated results
                page_iterator = paginator.paginate(
                    **list_params,
                    PaginationConfig=pagination_config
                )
                
                # Collect all objects
                objects = []
                for page in page_iterator:
                    if 'Contents' in page:
                        objects.extend(page['Contents'])
                
                return objects
            
            # Execute the operation with retry logic
            objects = self._with_retry(list_operation)
            
            # Format the results
            documents = []
            for obj in objects:
                # Extract basic information
                doc_info = {
                    'key': obj.get('Key'),
                    'size': obj.get('Size'),
                    'last_modified': obj.get('LastModified').isoformat() if obj.get('LastModified') else None,
                    'etag': obj.get('ETag', '').strip('"')
                }
                
                documents.append(doc_info)
            
            logger.info(f"Listed {len(documents)} documents in {self.bucket_name}" + 
                       (f" with prefix '{prefix}'" if prefix else ""))
            
            return documents, None
            
        except Exception as e:
            error_msg = f"Failed to list documents: {str(e)}"
            logger.error(error_msg)
            
            return None, error_msg
    
    def extract_document_metadata_for_classification(self, object_key: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Extract document metadata specifically for classification context.
        
        This method retrieves document metadata and formats it specifically for use
        in the document classification process, including content type, size, and any
        existing classification information.
        
        Args:
            object_key (str): S3 object key of the document.
            
        Returns:
            Tuple[Optional[Dict[str, Any]], Optional[str]]: A tuple containing the formatted metadata
                for classification and an error message if applicable. If extraction fails, the metadata will be None.
        """
        try:
            # Get the document metadata
            metadata, error = self.get_document_metadata(object_key)
            
            if error or not metadata:
                return None, error or "Failed to retrieve document metadata"
            
            # Extract file extension from the key
            _, ext = os.path.splitext(object_key)
            ext = ext.lower().lstrip('.')
            
            # Format metadata for classification
            classification_metadata = {
                'object_key': object_key,
                'file_extension': ext,
                'content_type': metadata.get('content_type', 'application/octet-stream'),
                'file_size': int(metadata.get('content_length', 0)),
                'original_filename': metadata.get('original_filename', os.path.basename(object_key)),
                'document_id': metadata.get('document_id', ''),
                'upload_timestamp': metadata.get('upload_timestamp', ''),
                
                # Include any existing classification information if available
                'previous_classification': metadata.get('classification', ''),
                'previous_confidence': float(metadata.get('classification_confidence', 0.0)),
                'previous_document_type': metadata.get('document_type', ''),
            }
            
            logger.info(f"Extracted classification metadata for {object_key}")
            
            return classification_metadata, None
            
        except Exception as e:
            error_msg = f"Failed to extract classification metadata for document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return None, error_msg
    
    def update_classification_results(self, object_key: str, classification_results: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Update document metadata with classification results.
        
        Args:
            object_key (str): S3 object key of the document.
            classification_results (Dict[str, Any]): Classification results to store in metadata.
                Should include 'classification', 'confidence', and 'document_type' keys.
                
        Returns:
            Tuple[bool, Optional[str]]: A tuple containing a success flag and an error message
                if applicable. If the update fails, the success flag will be False.
        """
        try:
            # Extract classification information
            classification = classification_results.get('classification', '')
            confidence = classification_results.get('confidence', 0.0)
            document_type = classification_results.get('document_type', '')
            
            # Prepare metadata update
            metadata_update = {
                'classification': classification,
                'classification_confidence': str(confidence),
                'document_type': document_type,
                'classification_timestamp': datetime.now().isoformat(),
            }
            
            # Add any additional classification metadata
            for key, value in classification_results.items():
                if key not in ['classification', 'confidence', 'document_type']:
                    metadata_update[f'classification_{key}'] = str(value)
            
            # Update the document metadata
            success, error = self.update_document_metadata(object_key, metadata_update)
            
            if not success:
                return False, error
            
            logger.info(f"Updated classification results for {object_key}: {classification} (confidence: {confidence})")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to update classification results for document {object_key}: {str(e)}"
            logger.error(error_msg)
            
            return False, error_msg
    
    def check_connection(self) -> bool:
        """Check if the S3 connection is working properly.
        
        This method is used for health checks to verify that the service can
        connect to the S3 storage and perform basic operations.
        
        Returns:
            bool: True if the connection is working, False otherwise.
        """
        try:
            # Try to list a small number of objects to verify connection
            def check_operation():
                self.s3_client.list_objects_v2(
                    Bucket=self.bucket_name,
                    MaxKeys=1
                )
                return True
            
            # Execute the operation with retry logic
            self._with_retry(check_operation)
            
            logger.debug(f"S3 connection check successful for bucket {self.bucket_name}")
            return True
            
        except Exception as e:
            logger.error(f"S3 connection check failed: {str(e)}")
            return False
    
    def get_storage_metrics(self) -> Dict[str, Any]:
        """Get storage metrics for monitoring and diagnostics.
        
        Returns:
            Dict[str, Any]: Dictionary containing storage metrics such as
                document count, total size, and bucket information.
        """
        try:
            metrics = {
                'bucket_name': self.bucket_name,
                'document_count': 0,
                'total_size_bytes': 0,
                'connection_status': 'healthy',
                'timestamp': datetime.now().isoformat()
            }
            
            # Get document count and total size
            documents, error = self.list_documents(max_items=10000)
            
            if error or documents is None:
                metrics['connection_status'] = 'error'
                metrics['error'] = error or 'Unknown error listing documents'
                return metrics
            
            # Calculate metrics
            metrics['document_count'] = len(documents)
            metrics['total_size_bytes'] = sum(doc.get('size', 0) for doc in documents)
            
            # Add additional metrics
            if metrics['document_count'] > 0:
                metrics['average_size_bytes'] = metrics['total_size_bytes'] / metrics['document_count']
            else:
                metrics['average_size_bytes'] = 0
                
            metrics['total_size_mb'] = metrics['total_size_bytes'] / (1024 * 1024)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Failed to get storage metrics: {str(e)}")
            
            return {
                'bucket_name': self.bucket_name,
                'connection_status': 'error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }