#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the S3-compatible storage service.

This module contains tests that verify document retrieval, storage operations,
encryption implementation, and metadata management for the storage service.
It ensures the storage service correctly handles document access with proper
security measures including AES-256 encryption.
"""

import os
import json
import pytest
import boto3
from unittest.mock import MagicMock, patch, call
from botocore.exceptions import ClientError, ConnectionError
from datetime import datetime

# Import the service to test
from src.services.storage_service import StorageService, with_retry

# Import types
from src.types.storage import StorageOptions, StorageMetadata, StorageResult


# ===== Test Initialization and Configuration =====

def test_storage_service_initialization(s3_client_config):
    """Test that the storage service initializes correctly with the provided configuration."""
    # Create a storage service with the test configuration
    service = StorageService(s3_client_config)
    
    # Verify the service was initialized with the correct configuration
    assert service.config == s3_client_config
    assert service.bucket_name == s3_client_config.get('bucket')


def test_get_bucket_name_by_environment():
    """Test that the correct bucket name is selected based on the environment."""
    # Test with production environment
    with patch('src.services.storage_service.app_config.ENVIRONMENT', 'production'):
        with patch('src.services.storage_service.s3_config.PRODUCTION_BUCKET', 'mca-documents-production'):
            service = StorageService()
            assert service._get_bucket_name() == 'mca-documents-production'
    
    # Test with staging environment
    with patch('src.services.storage_service.app_config.ENVIRONMENT', 'staging'):
        with patch('src.services.storage_service.s3_config.STAGING_BUCKET', 'mca-documents-staging'):
            service = StorageService()
            assert service._get_bucket_name() == 'mca-documents-staging'
    
    # Test with development environment
    with patch('src.services.storage_service.app_config.ENVIRONMENT', 'development'):
        with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', 'mca-documents-development'):
            service = StorageService()
            assert service._get_bucket_name() == 'mca-documents-development'


def test_initialize_client_with_retry_settings():
    """Test that the S3 client is initialized with the correct retry settings."""
    with patch('boto3.client') as mock_boto3_client:
        # Create a mock client
        mock_client = MagicMock()
        mock_boto3_client.return_value = mock_client
        
        # Create a storage service
        service = StorageService()
        
        # Verify boto3.client was called with the correct parameters
        mock_boto3_client.assert_called_once()
        
        # Check that retry configuration was included
        args, kwargs = mock_boto3_client.call_args
        assert 's3' in args or kwargs.get('service_name') == 's3'
        assert 'config' in kwargs
        
        # Verify the client was stored correctly
        assert service.client == mock_client


# ===== Test Document Download Operations =====

def test_download_document_success(s3_mock):
    """Test successful document download from S3."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'test-document.pdf'
    content = b'Test document content'
    metadata = {
        'document-id': 'doc-123',
        'application-id': 'app-456',
        'content-type': 'application/pdf'
    }
    
    # Upload a test document to the mock S3
    s3_mock.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content,
        Metadata=metadata,
        ServerSideEncryption='AES256'
    )
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                result = service.download_document(key)
    
    # Verify the result
    assert result.success is True
    assert result.data == content
    assert result.metadata is not None
    assert result.metadata.get('metadata') == metadata


def test_download_document_with_version_id(s3_mock):
    """Test document download with a specific version ID."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'test-document-versioned.pdf'
    content_v1 = b'Test document content v1'
    content_v2 = b'Test document content v2'
    
    # Enable versioning on the bucket
    s3_mock.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    
    # Upload two versions of the document
    response_v1 = s3_mock.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content_v1,
        ServerSideEncryption='AES256'
    )
    version_id_v1 = response_v1.get('VersionId')
    
    response_v2 = s3_mock.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content_v2,
        ServerSideEncryption='AES256'
    )
    version_id_v2 = response_v2.get('VersionId')
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                
                # Download the latest version (v2)
                result_latest = service.download_document(key)
                
                # Download a specific version (v1)
                result_v1 = service.download_document(key, version_id=version_id_v1)
    
    # Verify the results
    assert result_latest.success is True
    assert result_latest.data == content_v2
    
    assert result_v1.success is True
    assert result_v1.data == content_v1
    assert result_v1.version_id == version_id_v1


def test_download_document_not_found(s3_mock):
    """Test document download when the document doesn't exist."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'non-existent-document.pdf'
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                result = service.download_document(key)
    
    # Verify the result
    assert result.success is False
    assert 'NoSuchKey' in result.error or 'not found' in result.error.lower()


# ===== Test Document Upload Operations =====

def test_upload_document_success(s3_mock):
    """Test successful document upload to S3 with AES-256 encryption."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'upload-test-document.pdf'
    content = b'Test document content for upload'
    metadata = {
        'document-id': 'doc-789',
        'application-id': 'app-123',
        'content-type': 'application/pdf'
    }
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                result = service.upload_document(
                    key=key,
                    data=content,
                    metadata=metadata,
                    options=StorageOptions(content_type="application/pdf")
                )
    
    # Verify the result
    assert result.success is True
    assert result.version_id is not None
    
    # Verify the document was uploaded with the correct content and metadata
    response = s3_mock.get_object(Bucket=bucket_name, Key=key)
    assert response['Body'].read() == content
    assert response['Metadata'] == metadata
    assert response['ServerSideEncryption'] == 'AES256'  # Verify AES-256 encryption


def test_upload_extraction_results(s3_mock):
    """Test uploading OCR extraction results to S3."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    document_key = 'test-document.pdf'
    extraction_data = {
        'text': 'Extracted text from document',
        'fields': {
            'name': 'John Doe',
            'address': '123 Main St',
            'phone': '555-123-4567'
        }
    }
    confidence_scores = {
        'name': 0.98,
        'address': 0.92,
        'phone': 0.89
    }
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                with patch('src.services.storage_service.app_config.VERSION', '1.0.0-test'):
                    service = StorageService()
                    result = service.upload_extraction_results(
                        document_key=document_key,
                        extraction_data=extraction_data,
                        confidence_scores=confidence_scores
                    )
    
    # Verify the result
    assert result.success is True
    
    # Verify the results were uploaded correctly
    results_key = f"{document_key.rsplit('.', 1)[0]}_results.json"
    response = s3_mock.get_object(Bucket=bucket_name, Key=results_key)
    results_data = json.loads(response['Body'].read().decode('utf-8'))
    
    assert results_data['document_key'] == document_key
    assert results_data['extracted_data'] == extraction_data
    assert results_data['confidence_scores'] == confidence_scores
    assert results_data['version'] == '1.0.0-test'
    assert 'extraction_timestamp' in results_data
    
    # Verify metadata and encryption
    assert response['Metadata']['content-type'] == 'application/json'
    assert response['Metadata']['extraction-service'] == 'ocr-service'
    assert 'extraction-timestamp' in response['Metadata']
    assert response['ServerSideEncryption'] == 'AES256'  # Verify AES-256 encryption


# ===== Test Error Handling and Retry Logic =====

def test_with_retry_decorator():
    """Test the with_retry decorator for implementing retry logic."""
    # Create a mock function that fails twice and succeeds on the third try
    mock_func = MagicMock(side_effect=[ConnectionError("Connection failed"), 
                                      ConnectionError("Connection failed again"), 
                                      "Success"])
    
    # Apply the with_retry decorator
    decorated_func = with_retry(max_retries=3, base_delay=0.01, max_delay=0.1)(mock_func)
    
    # Call the decorated function
    result = decorated_func()
    
    # Verify the function was called multiple times and eventually succeeded
    assert mock_func.call_count == 3
    assert result == "Success"


def test_with_retry_decorator_max_retries_exceeded():
    """Test the with_retry decorator when max retries are exceeded."""
    # Create a mock function that always fails
    mock_func = MagicMock(side_effect=ConnectionError("Connection failed"))
    
    # Apply the with_retry decorator with a small delay for faster testing
    decorated_func = with_retry(max_retries=2, base_delay=0.01, max_delay=0.05)(mock_func)
    
    # Call the decorated function and expect it to raise an exception
    with pytest.raises(ConnectionError):
        decorated_func()
    
    # Verify the function was called the expected number of times
    assert mock_func.call_count == 3  # Initial call + 2 retries


def test_download_document_with_connection_error():
    """Test document download with a connection error that triggers retries."""
    # Create a mock S3 client that raises a connection error
    mock_client = MagicMock()
    mock_client.get_object.side_effect = ConnectionError("Connection failed")
    
    # Create a storage service with the mock client
    with patch('src.services.storage_service.boto3.client', return_value=mock_client):
        service = StorageService()
        
        # Patch the retry decorator to use small delays for faster testing
        with patch('src.services.storage_service.with_retry', 
                  return_value=with_retry(max_retries=2, base_delay=0.01, max_delay=0.05)):
            result = service.download_document('test-key')
    
    # Verify the result
    assert result.success is False
    assert 'connection error' in result.error.lower()
    
    # Verify the client method was called multiple times
    assert mock_client.get_object.call_count > 1


# ===== Test Metadata Management =====

def test_extract_metadata():
    """Test extraction of metadata from an S3 object response."""
    # Create a mock S3 response
    mock_response = {
        'ContentType': 'application/pdf',
        'ContentLength': 12345,
        'LastModified': datetime(2023, 1, 1, 12, 0, 0),
        'ETag': '"abcdef123456"',
        'VersionId': 'v1',
        'ServerSideEncryption': 'AES256',
        'Metadata': {
            'document-id': 'doc-123',
            'application-id': 'app-456'
        }
    }
    
    # Create a storage service
    service = StorageService()
    
    # Extract metadata
    metadata = service._extract_metadata(mock_response)
    
    # Verify the extracted metadata
    assert metadata.content_type == 'application/pdf'
    assert metadata.content_length == 12345
    assert metadata.last_modified == datetime(2023, 1, 1, 12, 0, 0)
    assert metadata.etag == 'abcdef123456'  # ETag should be stripped of quotes
    assert metadata.version_id == 'v1'
    assert metadata.server_side_encryption == 'AES256'
    assert metadata.metadata == {'document-id': 'doc-123', 'application-id': 'app-456'}


def test_update_document_metadata(s3_mock):
    """Test updating metadata for a document in S3."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'metadata-test-document.pdf'
    content = b'Test document content for metadata update'
    initial_metadata = {
        'document-id': 'doc-123',
        'application-id': 'app-456',
        'status': 'pending'
    }
    updated_metadata = {
        'document-id': 'doc-123',
        'application-id': 'app-456',
        'status': 'completed',
        'confidence': '0.95'
    }
    
    # Upload a test document with initial metadata
    s3_mock.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content,
        Metadata=initial_metadata,
        ServerSideEncryption='AES256'
    )
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                result = service.update_document_metadata(key, updated_metadata)
    
    # Verify the result
    assert result.success is True
    
    # Verify the metadata was updated
    response = s3_mock.get_object(Bucket=bucket_name, Key=key)
    assert response['Metadata'] == updated_metadata
    
    # Verify the content was preserved
    assert response['Body'].read() == content
    
    # Verify encryption was maintained
    assert response['ServerSideEncryption'] == 'AES256'


# ===== Test Versioning Support =====

def test_get_document_versions(s3_mock):
    """Test retrieving all versions of a document for audit purposes."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'versioned-document.pdf'
    
    # Enable versioning on the bucket
    s3_mock.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    
    # Upload multiple versions of the document
    version_ids = []
    for i in range(3):
        response = s3_mock.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=f'Version {i+1} content'.encode(),
            ServerSideEncryption='AES256'
        )
        version_ids.append(response.get('VersionId'))
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                result = service.get_document_versions(key)
    
    # Verify the result
    assert result.success is True
    assert len(result.data) == 3  # Should have 3 versions
    
    # Verify version information
    for version in result.data:
        assert 'version_id' in version
        assert 'last_modified' in version
        assert 'is_latest' in version
        assert 'size' in version
    
    # The latest version should be marked as such
    latest_versions = [v for v in result.data if v['is_latest']]
    assert len(latest_versions) == 1


def test_check_bucket_versioning(s3_mock):
    """Test checking if versioning is enabled on the bucket."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    
    # Enable versioning on the bucket
    s3_mock.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                result = service.check_bucket_versioning()
    
    # Verify versioning is enabled
    assert result is True


def test_enable_bucket_versioning(s3_mock):
    """Test enabling versioning on the bucket if not already enabled."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    
    # Disable versioning on the bucket
    s3_mock.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Suspended'}
    )
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                
                # Verify versioning is not enabled
                assert service.check_bucket_versioning() is False
                
                # Enable versioning
                result = service.enable_bucket_versioning()
                
                # Verify versioning was enabled
                assert result is True
                assert service.check_bucket_versioning() is True


# ===== Test Additional Functionality =====

def test_generate_presigned_url(s3_mock):
    """Test generating a presigned URL for temporary access to a document."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'presigned-url-document.pdf'
    content = b'Test document content for presigned URL'
    
    # Upload a test document
    s3_mock.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=content,
        ServerSideEncryption='AES256'
    )
    
    # Mock the generate_presigned_url method
    s3_mock.generate_presigned_url = MagicMock(return_value='https://example.com/presigned-url')
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                url = service.generate_presigned_url(key, expiration=3600)
    
    # Verify the URL was generated
    assert url == 'https://example.com/presigned-url'
    
    # Verify the generate_presigned_url method was called with the correct parameters
    s3_mock.generate_presigned_url.assert_called_once_with(
        'get_object',
        Params={'Bucket': bucket_name, 'Key': key},
        ExpiresIn=3600
    )


def test_document_exists(s3_mock):
    """Test checking if a document exists in S3 storage."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    existing_key = 'existing-document.pdf'
    non_existing_key = 'non-existing-document.pdf'
    
    # Upload a test document
    s3_mock.put_object(
        Bucket=bucket_name,
        Key=existing_key,
        Body=b'Test document content',
        ServerSideEncryption='AES256'
    )
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                
                # Check if the existing document exists
                exists_result = service.document_exists(existing_key)
                
                # Check if the non-existing document exists
                not_exists_result = service.document_exists(non_existing_key)
    
    # Verify the results
    assert exists_result is True
    assert not_exists_result is False


def test_delete_document(s3_mock):
    """Test deleting a document from S3 storage."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'document-to-delete.pdf'
    
    # Upload a test document
    s3_mock.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=b'Test document content to delete',
        ServerSideEncryption='AES256'
    )
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                
                # Verify the document exists
                assert service.document_exists(key) is True
                
                # Delete the document
                result = service.delete_document(key)
                
                # Verify the document was deleted
                assert result.success is True
                assert service.document_exists(key) is False


def test_delete_specific_version(s3_mock):
    """Test deleting a specific version of a document from S3 storage."""
    # Set up test data
    bucket_name = 'mca-documents-test'
    key = 'versioned-document-to-delete.pdf'
    
    # Enable versioning on the bucket
    s3_mock.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )
    
    # Upload multiple versions of the document
    version_ids = []
    for i in range(3):
        response = s3_mock.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=f'Version {i+1} content'.encode(),
            ServerSideEncryption='AES256'
        )
        version_ids.append(response.get('VersionId'))
    
    # Create a storage service with the mock S3 client
    with patch('src.services.storage_service.boto3.client', return_value=s3_mock):
        with patch('src.services.storage_service.app_config.ENVIRONMENT', 'test'):
            with patch('src.services.storage_service.s3_config.DEVELOPMENT_BUCKET', bucket_name):
                service = StorageService()
                
                # Delete a specific version
                version_to_delete = version_ids[1]  # Delete the middle version
                result = service.delete_document(key, version_id=version_to_delete)
                
                # Verify the result
                assert result.success is True
                
                # Get all versions
                versions_result = service.get_document_versions(key)
                
                # Verify the specific version was deleted
                remaining_version_ids = [v['version_id'] for v in versions_result.data]
                assert version_to_delete not in remaining_version_ids
                assert len(remaining_version_ids) == 2  # Should have 2 versions left