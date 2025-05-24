#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the S3-compatible storage service.

This module contains tests that verify the storage service correctly connects to S3,
retrieves documents, stores documents with encryption, manages document metadata,
and handles storage errors.

These tests validate the following requirements:
1. Document Service must access documents in S3-compatible storage as specified in section 0.1.2
2. S3 storage must use AES-256 encryption for document storage as specified in section 0.2.5
3. Service must use appropriate buckets for different environments as specified in section 0.2.5
4. Service must implement secure credential management as specified in section 0.2.6
5. Service must handle connection errors and retries as specified in section 3.2.3
"""

import os
import json
import tempfile
import time
from datetime import datetime
from unittest.mock import MagicMock, patch, call, ANY

import pytest
import boto3
from botocore.exceptions import ClientError

from document_service.services.storage_service import StorageService
from document_service.types.storage import StorageResult, StorageMetadata
from document_service.config import s3_config


# ===== Test S3 Client Connection =====

def test_storage_service_initialization(mock_s3_client, mock_s3_bucket):
    """Test that the StorageService initializes correctly with S3 client."""
    # Arrange
    mock_s3_client.head_bucket.return_value = {}
    
    # Act
    storage_service = StorageService()
    
    # Assert
    assert storage_service.s3_client is not None
    assert storage_service.bucket_name == s3_config.get_bucket_name()
    assert storage_service.max_retries == 3
    assert storage_service.base_delay == 1
    assert storage_service.default_url_expiration == 3600


def test_storage_service_creates_bucket_if_not_exists(mock_s3_client):
    """Test that the StorageService creates a bucket if it doesn't exist."""
    # Arrange
    # First call to check_bucket_exists returns False, then True for subsequent calls
    mock_s3_client.head_bucket.side_effect = [
        ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadBucket"),
        {}
    ]
    
    # Act
    with patch('document_service.config.s3_config.check_bucket_exists', side_effect=[False, True]):
        with patch('document_service.config.s3_config.create_bucket_if_not_exists') as mock_create_bucket:
            storage_service = StorageService()
    
    # Assert
    mock_create_bucket.assert_called_once()


def test_storage_service_with_custom_bucket(mock_s3_client):
    """Test that the StorageService can be initialized with a custom bucket."""
    # Arrange
    custom_bucket = "custom-bucket"
    mock_s3_client.head_bucket.return_value = {}
    
    # Act
    with patch('document_service.config.s3_config.get_bucket_name', return_value=custom_bucket):
        storage_service = StorageService()
    
    # Assert
    assert storage_service.bucket_name == custom_bucket


# ===== Test Document Upload =====

def test_upload_document_with_encryption(mock_s3_client):
    """Test that documents are uploaded with AES-256 encryption."""
    # Arrange
    storage_service = StorageService()
    document_id = "test-doc-123"
    file_name = "test_document.pdf"
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test document content")
        file_path = temp_file.name
    
    try:
        # Act
        result = storage_service.upload_document(file_path, document_id)
        
        # Assert
        assert result.success is True
        assert result.object_key is not None
        assert result.error is None
        
        # Verify S3 client was called with correct parameters
        mock_s3_client.upload_file.assert_called_once()
        args, kwargs = mock_s3_client.upload_file.call_args
        
        # Check that encryption is enabled
        assert kwargs['ExtraArgs']['ServerSideEncryption'] == 'AES256'
        
        # Check that metadata includes document_id
        assert kwargs['ExtraArgs']['Metadata']['document_id'] == document_id
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)


def test_upload_document_with_metadata(mock_s3_client):
    """Test that documents are uploaded with custom metadata."""
    # Arrange
    storage_service = StorageService()
    document_id = "test-doc-123"
    file_name = "test_document.pdf"
    custom_metadata = {
        "application_id": "app-456",
        "document_type": "application_form",
        "page_count": "5"
    }
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test document content")
        file_path = temp_file.name
    
    try:
        # Act
        result = storage_service.upload_document(file_path, document_id, custom_metadata)
        
        # Assert
        assert result.success is True
        
        # Verify S3 client was called with correct parameters
        mock_s3_client.upload_file.assert_called_once()
        args, kwargs = mock_s3_client.upload_file.call_args
        
        # Check that metadata includes custom fields
        metadata = kwargs['ExtraArgs']['Metadata']
        assert metadata['document_id'] == document_id
        assert metadata['application_id'] == custom_metadata['application_id']
        assert metadata['document_type'] == custom_metadata['document_type']
        assert metadata['page_count'] == custom_metadata['page_count']
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)


def test_upload_document_from_bytes(mock_s3_client):
    """Test that documents can be uploaded from bytes."""
    # Arrange
    storage_service = StorageService()
    document_id = "test-doc-123"
    file_name = "test_document.pdf"
    file_bytes = b"Test document content"
    
    # Act
    with patch('tempfile.NamedTemporaryFile') as mock_temp_file:
        # Setup the mock temporary file
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.name = "/tmp/mock_temp_file"
        mock_temp_file.return_value = mock_file
        
        # Call the method
        result = storage_service.upload_document_from_bytes(file_bytes, file_name, document_id)
    
    # Assert
    assert result.success is True
    assert result.object_key is not None
    
    # Verify temp file was written to
    mock_file.write.assert_called_once_with(file_bytes)
    
    # Verify upload_document was called
    mock_s3_client.upload_file.assert_called_once()


def test_upload_document_error_handling(mock_s3_client):
    """Test that upload errors are handled correctly."""
    # Arrange
    storage_service = StorageService()
    document_id = "test-doc-123"
    file_name = "test_document.pdf"
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_file.write(b"Test document content")
        file_path = temp_file.name
    
    # Configure S3 client to raise an error
    mock_s3_client.upload_file.side_effect = ClientError(
        {"Error": {"Code": "InternalError", "Message": "Internal S3 Error"}},
        "UploadFile"
    )
    
    try:
        # Act
        result = storage_service.upload_document(file_path, document_id)
        
        # Assert
        assert result.success is False
        assert result.object_key is None
        assert result.error is not None
        assert "Failed to upload document" in result.error
    finally:
        # Clean up the temporary file
        if os.path.exists(file_path):
            os.unlink(file_path)


# ===== Test Document Download =====

def test_download_document(mock_s3_client):
    """Test that documents can be downloaded from S3."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Act
    temp_path, error = storage_service.download_document(object_key)
    
    # Assert
    assert temp_path is not None
    assert error is None
    
    # Verify S3 client was called with correct parameters
    mock_s3_client.download_file.assert_called_once_with(
        Bucket=storage_service.bucket_name,
        Key=object_key,
        Filename=ANY
    )


def test_download_document_as_bytes(mock_s3_client):
    """Test that documents can be downloaded as bytes."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Mock the download_document method
    with patch.object(storage_service, 'download_document') as mock_download:
        # Setup the mock to return a temporary file path
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"Test document content")
            temp_file_path = temp_file.name
        
        mock_download.return_value = (temp_file_path, None)
        
        try:
            # Act
            content, error = storage_service.download_document_as_bytes(object_key)
            
            # Assert
            assert content == b"Test document content"
            assert error is None
            
            # Verify download_document was called
            mock_download.assert_called_once_with(object_key)
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)


def test_download_document_error_handling(mock_s3_client):
    """Test that download errors are handled correctly."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Configure S3 client to raise an error
    mock_s3_client.download_file.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
        "DownloadFile"
    )
    
    # Act
    temp_path, error = storage_service.download_document(object_key)
    
    # Assert
    assert temp_path is None
    assert error is not None
    assert "Failed to download document" in error


# ===== Test Document Metadata =====

def test_get_document_metadata(mock_s3_client):
    """Test that document metadata can be retrieved."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Configure mock response
    mock_s3_client.head_object.return_value = {
        "ContentLength": 12345,
        "ContentType": "application/pdf",
        "LastModified": datetime.now(),
        "ETag": "\"mock-etag\"",
        "ServerSideEncryption": "AES256",
        "Metadata": {
            "document_id": "test-doc-123",
            "application_id": "app-456",
            "document_type": "application_form"
        }
    }
    
    # Act
    metadata, error = storage_service.get_document_metadata(object_key)
    
    # Assert
    assert metadata is not None
    assert error is None
    assert metadata["content_length"] == "12345"
    assert metadata["content_type"] == "application/pdf"
    assert metadata["server_side_encryption"] == "AES256"
    assert metadata["document_id"] == "test-doc-123"
    assert metadata["application_id"] == "app-456"
    assert metadata["document_type"] == "application_form"
    
    # Verify S3 client was called with correct parameters
    mock_s3_client.head_object.assert_called_once_with(
        Bucket=storage_service.bucket_name,
        Key=object_key
    )


def test_get_document_metadata_not_found(mock_s3_client):
    """Test handling of metadata retrieval for non-existent documents."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/nonexistent-doc.pdf"
    
    # Configure S3 client to raise a NoSuchKey error
    mock_s3_client.head_object.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "HeadObject"
    )
    
    # Act
    metadata, error = storage_service.get_document_metadata(object_key)
    
    # Assert
    assert metadata is None
    assert error is not None
    assert "not found" in error


def test_update_document_metadata(mock_s3_client):
    """Test that document metadata can be updated."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    new_metadata = {
        "classification": "application_form",
        "confidence": "0.95",
        "page_count": "5"
    }
    
    # Configure mock responses
    mock_s3_client.head_object.return_value = {
        "ContentLength": 12345,
        "ContentType": "application/pdf",
        "LastModified": datetime.now(),
        "ETag": "\"mock-etag\"",
        "ServerSideEncryption": "AES256",
        "Metadata": {
            "document_id": "test-doc-123",
            "original_filename": "test_document.pdf"
        }
    }
    
    # Act
    success, error = storage_service.update_document_metadata(object_key, new_metadata)
    
    # Assert
    assert success is True
    assert error is None
    
    # Verify S3 client was called with correct parameters
    mock_s3_client.copy_object.assert_called_once()
    args, kwargs = mock_s3_client.copy_object.call_args
    
    # Check that metadata was updated correctly
    assert kwargs['Metadata']['document_id'] == "test-doc-123"
    assert kwargs['Metadata']['original_filename'] == "test_document.pdf"
    assert kwargs['Metadata']['classification'] == new_metadata['classification']
    assert kwargs['Metadata']['confidence'] == new_metadata['confidence']
    assert kwargs['Metadata']['page_count'] == new_metadata['page_count']
    
    # Check that encryption is maintained
    assert kwargs['ServerSideEncryption'] == 'AES256'


# ===== Test Classification Metadata =====

def test_extract_document_metadata_for_classification(mock_s3_client):
    """Test extraction of document metadata for classification."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Configure mock response
    mock_s3_client.head_object.return_value = {
        "ContentLength": 12345,
        "ContentType": "application/pdf",
        "LastModified": datetime.now(),
        "ETag": "\"mock-etag\"",
        "ServerSideEncryption": "AES256",
        "Metadata": {
            "document_id": "test-doc-123",
            "original_filename": "test_document.pdf",
            "upload_timestamp": datetime.now().isoformat(),
            "classification": "application_form",
            "classification_confidence": "0.85"
        }
    }
    
    # Act
    metadata, error = storage_service.extract_document_metadata_for_classification(object_key)
    
    # Assert
    assert metadata is not None
    assert error is None
    assert metadata["object_key"] == object_key
    assert metadata["file_extension"] == "pdf"
    assert metadata["content_type"] == "application/pdf"
    assert metadata["file_size"] == 12345
    assert metadata["document_id"] == "test-doc-123"
    assert metadata["previous_classification"] == "application_form"
    assert metadata["previous_confidence"] == 0.85


def test_update_classification_results(mock_s3_client):
    """Test updating document metadata with classification results."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    classification_results = {
        "classification": "application_form",
        "confidence": 0.95,
        "document_type": "APPLICATION",
        "features_used": ["text_content", "file_extension"],
        "model_version": "1.0.0"
    }
    
    # Mock the update_document_metadata method
    with patch.object(storage_service, 'update_document_metadata') as mock_update:
        mock_update.return_value = (True, None)
        
        # Act
        success, error = storage_service.update_classification_results(object_key, classification_results)
        
        # Assert
        assert success is True
        assert error is None
        
        # Verify update_document_metadata was called with correct parameters
        mock_update.assert_called_once()
        args, kwargs = mock_update.call_args
        
        # Check that metadata was formatted correctly
        assert args[0] == object_key
        assert args[1]["classification"] == classification_results["classification"]
        assert args[1]["classification_confidence"] == str(classification_results["confidence"])
        assert args[1]["document_type"] == classification_results["document_type"]
        assert args[1]["classification_features_used"] == str(classification_results["features_used"])
        assert args[1]["classification_model_version"] == classification_results["model_version"]
        assert "classification_timestamp" in args[1]


# ===== Test Retry Logic =====

def test_retry_logic_success_after_failure(mock_s3_client):
    """Test that operations are retried after transient failures."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Configure S3 client to fail twice then succeed
    error_response = {"Error": {"Code": "InternalError", "Message": "Internal S3 Error"}}
    mock_s3_client.head_object.side_effect = [
        ClientError(error_response, "HeadObject"),  # First call fails
        ClientError(error_response, "HeadObject"),  # Second call fails
        {  # Third call succeeds
            "ContentLength": 12345,
            "ContentType": "application/pdf",
            "LastModified": datetime.now(),
            "Metadata": {"document_id": "test-doc-123"}
        }
    ]
    
    # Mock time.sleep to avoid waiting during tests
    with patch('time.sleep') as mock_sleep:
        # Act
        metadata, error = storage_service.get_document_metadata(object_key)
        
        # Assert
        assert metadata is not None
        assert error is None
        assert mock_s3_client.head_object.call_count == 3
        assert mock_sleep.call_count == 2
        
        # Verify exponential backoff
        assert mock_sleep.call_args_list[0] == call(1)  # First retry: base_delay * 2^0
        assert mock_sleep.call_args_list[1] == call(2)  # Second retry: base_delay * 2^1


def test_retry_logic_all_attempts_fail(mock_s3_client):
    """Test that the operation fails after all retry attempts fail."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Configure S3 client to always fail
    error_response = {"Error": {"Code": "InternalError", "Message": "Internal S3 Error"}}
    client_error = ClientError(error_response, "HeadObject")
    mock_s3_client.head_object.side_effect = client_error
    
    # Mock time.sleep to avoid waiting during tests
    with patch('time.sleep') as mock_sleep:
        # Act
        metadata, error = storage_service.get_document_metadata(object_key)
        
        # Assert
        assert metadata is None
        assert error is not None
        assert "Failed to retrieve metadata" in error
        assert mock_s3_client.head_object.call_count == storage_service.max_retries
        assert mock_sleep.call_count == storage_service.max_retries - 1


# ===== Test Utility Methods =====

def test_generate_presigned_url(mock_s3_client):
    """Test generation of presigned URLs for document access."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    expiration = 1800  # 30 minutes
    
    # Configure mock response
    mock_s3_client.generate_presigned_url.return_value = "https://example.com/presigned-url"
    
    # Act
    url, error = storage_service.generate_presigned_url(object_key, expiration)
    
    # Assert
    assert url == "https://example.com/presigned-url"
    assert error is None
    
    # Verify S3 client was called with correct parameters
    mock_s3_client.generate_presigned_url.assert_called_once_with(
        'get_object',
        Params={
            'Bucket': storage_service.bucket_name,
            'Key': object_key
        },
        ExpiresIn=expiration
    )


def test_list_documents(mock_s3_client):
    """Test listing documents in the S3 bucket."""
    # Arrange
    storage_service = StorageService()
    prefix = "documents/"
    
    # Configure mock response
    mock_s3_client.get_paginator.return_value.paginate.return_value = [{
        "Contents": [
            {
                "Key": "documents/doc1.pdf",
                "Size": 12345,
                "LastModified": datetime.now(),
                "ETag": "\"mock-etag-1\""
            },
            {
                "Key": "documents/doc2.pdf",
                "Size": 23456,
                "LastModified": datetime.now(),
                "ETag": "\"mock-etag-2\""
            }
        ]
    }]
    
    # Act
    documents, error = storage_service.list_documents(prefix)
    
    # Assert
    assert documents is not None
    assert error is None
    assert len(documents) == 2
    assert documents[0]["key"] == "documents/doc1.pdf"
    assert documents[1]["key"] == "documents/doc2.pdf"
    
    # Verify S3 client was called with correct parameters
    mock_s3_client.get_paginator.assert_called_once_with('list_objects_v2')
    mock_s3_client.get_paginator.return_value.paginate.assert_called_once()


def test_delete_document(mock_s3_client):
    """Test deleting a document from S3."""
    # Arrange
    storage_service = StorageService()
    object_key = "documents/test-doc-123.pdf"
    
    # Act
    success, error = storage_service.delete_document(object_key)
    
    # Assert
    assert success is True
    assert error is None
    
    # Verify S3 client was called with correct parameters
    mock_s3_client.delete_object.assert_called_once_with(
        Bucket=storage_service.bucket_name,
        Key=object_key
    )


def test_check_connection(mock_s3_client):
    """Test checking the S3 connection."""
    # Arrange
    storage_service = StorageService()
    
    # Act
    is_connected = storage_service.check_connection()
    
    # Assert
    assert is_connected is True
    
    # Verify S3 client was called
    mock_s3_client.list_objects_v2.assert_called_once_with(
        Bucket=storage_service.bucket_name,
        MaxKeys=1
    )


def test_check_connection_failure(mock_s3_client):
    """Test checking the S3 connection when it fails."""
    # Arrange
    storage_service = StorageService()
    
    # Configure S3 client to raise an error
    mock_s3_client.list_objects_v2.side_effect = ClientError(
        {"Error": {"Code": "NetworkError", "Message": "Network Error"}},
        "ListObjectsV2"
    )
    
    # Act
    is_connected = storage_service.check_connection()
    
    # Assert
    assert is_connected is False


def test_get_storage_metrics(mock_s3_client):
    """Test getting storage metrics."""
    # Arrange
    storage_service = StorageService()
    
    # Configure mock response
    mock_s3_client.get_paginator.return_value.paginate.return_value = [{
        "Contents": [
            {"Key": "documents/doc1.pdf", "Size": 10000},
            {"Key": "documents/doc2.pdf", "Size": 20000},
            {"Key": "documents/doc3.pdf", "Size": 30000},
        ]
    }]
    
    # Act
    metrics = storage_service.get_storage_metrics()
    
    # Assert
    assert metrics["bucket_name"] == storage_service.bucket_name
    assert metrics["document_count"] == 3
    assert metrics["total_size_bytes"] == 60000
    assert metrics["average_size_bytes"] == 20000
    assert metrics["total_size_mb"] == 60000 / (1024 * 1024)
    assert metrics["connection_status"] == "healthy"


def test_get_storage_metrics_error(mock_s3_client):
    """Test getting storage metrics when there's an error."""
    # Arrange
    storage_service = StorageService()
    
    # Configure S3 client to raise an error
    mock_s3_client.get_paginator.return_value.paginate.side_effect = ClientError(
        {"Error": {"Code": "NetworkError", "Message": "Network Error"}},
        "ListObjectsV2"
    )
    
    # Act
    metrics = storage_service.get_storage_metrics()
    
    # Assert
    assert metrics["bucket_name"] == storage_service.bucket_name
    assert metrics["connection_status"] == "error"
    assert "error" in metrics