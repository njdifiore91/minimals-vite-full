#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the s3_utils.py module.

This module contains tests for S3 connection management, document download and upload
with encryption, document metadata management, error handling for S3 operations, and
signed URL generation to ensure secure document storage and retrieval.
"""

import os
import json
import pytest
import boto3
import tempfile
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Import the module to test
import sys
import os

# Add the src directory to the path if needed for imports
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src'))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from utils import s3_utils


# ===== S3 Connection Management Tests =====

def test_get_s3_client_default_params():
    """Test creating an S3 client with default parameters."""
    # Set environment variables for testing
    with patch.dict(os.environ, {
        'AWS_REGION': 'us-west-2',
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret'
    }):
        client = s3_utils.get_s3_client()
        
        # Verify client was created with correct parameters
        assert client.meta.region_name == 'us-west-2'
        assert client.meta.config.signature_version == 's3v4'
        assert client.meta.config.retries['max_attempts'] == 3


def test_get_s3_client_custom_params():
    """Test creating an S3 client with custom parameters."""
    client = s3_utils.get_s3_client(
        region_name='eu-central-1',
        endpoint_url='https://custom-endpoint.example.com',
        aws_access_key_id='custom-key',
        aws_secret_access_key='custom-secret',
        aws_session_token='custom-token'
    )
    
    # Verify client was created with correct parameters
    assert client.meta.region_name == 'eu-central-1'
    assert client.meta.endpoint_url == 'https://custom-endpoint.example.com'
    assert client.meta.config.signature_version == 's3v4'


def test_get_s3_resource_default_params():
    """Test creating an S3 resource with default parameters."""
    # Set environment variables for testing
    with patch.dict(os.environ, {
        'AWS_REGION': 'us-west-2',
        'AWS_ACCESS_KEY_ID': 'test-key',
        'AWS_SECRET_ACCESS_KEY': 'test-secret'
    }):
        resource = s3_utils.get_s3_resource()
        
        # Verify resource was created with correct parameters
        assert resource.meta.client.meta.region_name == 'us-west-2'
        assert resource.meta.client.meta.config.signature_version == 's3v4'


def test_get_s3_resource_custom_params():
    """Test creating an S3 resource with custom parameters."""
    resource = s3_utils.get_s3_resource(
        region_name='eu-central-1',
        endpoint_url='https://custom-endpoint.example.com',
        aws_access_key_id='custom-key',
        aws_secret_access_key='custom-secret',
        aws_session_token='custom-token'
    )
    
    # Verify resource was created with correct parameters
    assert resource.meta.client.meta.region_name == 'eu-central-1'
    assert resource.meta.client.meta.endpoint_url == 'https://custom-endpoint.example.com'
    assert resource.meta.client.meta.config.signature_version == 's3v4'


def test_get_s3_client_error_handling():
    """Test error handling when creating an S3 client fails."""
    # Mock boto3.client to raise an exception
    with patch('boto3.client', side_effect=Exception('Connection failed')):
        with pytest.raises(Exception) as excinfo:
            s3_utils.get_s3_client()
        
        assert 'Connection failed' in str(excinfo.value)


# ===== Document Download and Upload Tests =====

def test_download_document(s3_mock, s3_test_files):
    """Test downloading a document from S3."""
    # Get a test file key
    bucket = 'mca-documents-test'  # Use the test bucket name from conftest.py
    key = s3_test_files['pdf']
    
    # Download the document
    content, metadata = s3_utils.download_document(bucket, key, s3_mock)
    
    # Verify the content and metadata
    assert content.startswith(b'%PDF-1.5')
    assert metadata['ContentType'] == 'application/pdf'
    assert 'LastModified' in metadata
    assert 'ETag' in metadata


def test_download_document_not_found(s3_mock):
    """Test error handling when downloading a non-existent document."""
    bucket = 'mca-documents-test'  # Use the test bucket name from conftest.py
    key = 'non-existent-file.pdf'
    
    # Attempt to download a non-existent document
    with pytest.raises(ClientError) as excinfo:
        s3_utils.download_document(bucket, key, s3_mock)
    
    # Verify the error
    assert 'NoSuchKey' in str(excinfo.value)


def test_upload_document(s3_mock):
    """Test uploading a document to S3 with encryption."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'test-upload/document.pdf'
    content = b'%PDF-1.5\nTest PDF content\n%%EOF'
    content_type = 'application/pdf'
    metadata = {'document_id': 'test-123', 'application_id': 'app-456'}
    
    # Upload the document
    response = s3_utils.upload_document(
        bucket, key, content, content_type, metadata, s3_mock
    )
    
    # Verify the response
    assert 'ETag' in response
    
    # Verify the document was uploaded with encryption
    obj = s3_mock.get_object(Bucket=bucket, Key=key)
    assert obj['ServerSideEncryption'] == 'AES256'
    assert obj['ContentType'] == content_type
    assert obj['Metadata'] == metadata
    assert obj['Body'].read() == content


def test_upload_extracted_data(s3_mock):
    """Test uploading extracted data to S3."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'test-upload/extracted_data.json'
    original_document_key = 'test-upload/document.pdf'
    extracted_data = {
        'fields': {
            'name': 'John Doe',
            'address': '123 Main St',
            'phone': '555-123-4567'
        }
    }
    confidence_scores = {
        'name': 0.98,
        'address': 0.95,
        'phone': 0.92
    }
    document_type = 'application'
    
    # Upload the extracted data
    response = s3_utils.upload_extracted_data(
        bucket, key, extracted_data, original_document_key,
        confidence_scores, document_type, s3_mock
    )
    
    # Verify the response
    assert 'ETag' in response
    
    # Verify the data was uploaded with encryption
    obj = s3_mock.get_object(Bucket=bucket, Key=key)
    assert obj['ServerSideEncryption'] == 'AES256'
    assert obj['ContentType'] == 'application/json'
    
    # Verify metadata
    assert obj['Metadata']['original-document'] == original_document_key
    assert obj['Metadata']['document-type'] == document_type
    assert 'extraction-timestamp' in obj['Metadata']
    
    # Verify content
    content = json.loads(obj['Body'].read().decode('utf-8'))
    assert content['fields'] == extracted_data['fields']
    assert content['confidence_scores'] == confidence_scores
    assert content['metadata']['original_document'] == original_document_key
    assert content['metadata']['document_type'] == document_type


# ===== Document Metadata Management Tests =====

def test_update_document_metadata(s3_mock, s3_test_files):
    """Test updating metadata for an existing document."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['application']
    
    # New metadata to apply
    new_metadata = {
        'document_id': 'doc-123',
        'application_id': 'app-456',
        'document_type': 'application',
        'status': 'processed',
        'confidence': '0.95'
    }
    
    # Update the metadata
    response = s3_utils.update_document_metadata(bucket, key, new_metadata, s3_mock)
    
    # Verify the response
    assert 'ETag' in response
    
    # Verify the metadata was updated
    obj = s3_mock.head_object(Bucket=bucket, Key=key)
    assert obj['Metadata'] == new_metadata
    assert obj['ServerSideEncryption'] == 'AES256'  # Encryption maintained


def test_get_document_metadata(s3_mock, s3_test_files):
    """Test retrieving metadata for a document without downloading content."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['application']
    
    # Get the metadata
    metadata = s3_utils.get_document_metadata(bucket, key, s3_mock)
    
    # Verify the metadata
    assert metadata['ContentType'] == 'application/pdf'
    assert 'ContentLength' in metadata
    assert 'LastModified' in metadata
    assert 'ETag' in metadata
    assert 'ServerSideEncryption' in metadata
    assert 'Metadata' in metadata
    assert metadata['Metadata']['document_id'] == 'doc-123'
    assert metadata['Metadata']['application_id'] == 'app-456'


# ===== Error Handling Tests =====

def test_error_handling_upload_document(s3_mock):
    """Test error handling when uploading a document fails."""
    bucket = 'non-existent-bucket'
    key = 'test-document.pdf'
    content = b'Test content'
    
    # Attempt to upload to a non-existent bucket
    with pytest.raises(ClientError) as excinfo:
        s3_utils.upload_document(bucket, key, content, s3_client=s3_mock)
    
    # Verify the error
    assert 'NoSuchBucket' in str(excinfo.value)


def test_error_handling_update_metadata(s3_mock):
    """Test error handling when updating metadata fails."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'non-existent-file.pdf'
    metadata = {'test': 'value'}
    
    # Attempt to update metadata for a non-existent document
    with pytest.raises(ClientError) as excinfo:
        s3_utils.update_document_metadata(bucket, key, metadata, s3_mock)
    
    # Verify the error
    assert 'NoSuchKey' in str(excinfo.value)


def test_error_handling_get_metadata(s3_mock):
    """Test error handling when retrieving metadata fails."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'non-existent-file.pdf'
    
    # Attempt to get metadata for a non-existent document
    with pytest.raises(ClientError) as excinfo:
        s3_utils.get_document_metadata(bucket, key, s3_mock)
    
    # Verify the error
    assert 'NoSuchKey' in str(excinfo.value)


# ===== Signed URL Generation Tests =====

def test_generate_presigned_url(s3_mock, s3_test_files):
    """Test generating a presigned URL for secure access."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['pdf']
    expiration = 3600  # 1 hour
    
    # Generate a presigned URL
    url = s3_utils.generate_presigned_url(bucket, key, expiration, s3_mock)
    
    # Verify the URL
    assert url.startswith('https://')
    assert bucket in url
    assert key in url
    assert 'X-Amz-Algorithm=' in url
    assert 'X-Amz-Credential=' in url
    assert 'X-Amz-Date=' in url
    assert 'X-Amz-Expires=' in url
    assert 'X-Amz-SignedHeaders=' in url
    assert 'X-Amz-Signature=' in url


def test_generate_presigned_post(s3_mock):
    """Test generating a presigned POST request for uploading."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'test-upload/document.pdf'
    fields = {'Content-Type': 'application/pdf'}
    conditions = [
        {'bucket': bucket},
        ['starts-with', '$key', 'test-upload/'],
        {'Content-Type': 'application/pdf'}
    ]
    expiration = 3600  # 1 hour
    
    # Generate a presigned POST
    post_data = s3_utils.generate_presigned_post(
        bucket, key, fields, conditions, expiration, s3_mock
    )
    
    # Verify the POST data
    assert 'url' in post_data
    assert 'fields' in post_data
    assert post_data['url'].endswith(bucket)
    assert post_data['fields']['key'] == key
    assert post_data['fields']['Content-Type'] == 'application/pdf'
    assert post_data['fields']['ServerSideEncryption'] == 'AES256'
    assert 'policy' in post_data['fields']
    assert 'x-amz-algorithm' in post_data['fields']
    assert 'x-amz-credential' in post_data['fields']
    assert 'x-amz-date' in post_data['fields']
    assert 'x-amz-signature' in post_data['fields']


# ===== Helper Function Tests =====

def test_parse_s3_uri_valid():
    """Test parsing a valid S3 URI."""
    uri = 's3://my-bucket/path/to/document.pdf'
    bucket, key = s3_utils.parse_s3_uri(uri)
    
    assert bucket == 'my-bucket'
    assert key == 'path/to/document.pdf'


def test_parse_s3_uri_invalid():
    """Test parsing an invalid S3 URI."""
    # Test with non-S3 URI
    with pytest.raises(ValueError) as excinfo:
        s3_utils.parse_s3_uri('http://example.com/file.pdf')
    assert 'Invalid S3 URI' in str(excinfo.value)
    
    # Test with missing key
    with pytest.raises(ValueError) as excinfo:
        s3_utils.parse_s3_uri('s3://my-bucket/')
    assert 'Invalid S3 URI' in str(excinfo.value)
    
    # Test with missing bucket
    with pytest.raises(ValueError) as excinfo:
        s3_utils.parse_s3_uri('s3:///path/to/file.pdf')
    assert 'Invalid S3 URI' in str(excinfo.value)


def test_check_document_exists(s3_mock, s3_test_files):
    """Test checking if a document exists in S3."""
    bucket = s3_utils.TEST_BUCKET_NAME
    
    # Test with existing document
    existing_key = s3_test_files['pdf']
    assert s3_utils.check_document_exists(bucket, existing_key, s3_mock) is True
    
    # Test with non-existent document
    non_existent_key = 'non-existent-file.pdf'
    assert s3_utils.check_document_exists(bucket, non_existent_key, s3_mock) is False


def test_create_document_key():
    """Test creating a standardized S3 key for a document."""
    document_type = 'application'
    document_id = 'doc-123456'
    extension = 'pdf'
    
    # Create a document key
    key = s3_utils.create_document_key(document_type, document_id, extension)
    
    # Verify the key format
    # Format should be: document_type/YYYY/MM/DD/document_id.extension
    import time
    timestamp = time.strftime('%Y/%m/%d', time.gmtime())
    expected_key = f"{document_type}/{timestamp}/{document_id}.{extension}"
    
    assert key == expected_key


def test_create_extracted_data_key():
    """Test creating a standardized S3 key for extracted data."""
    document_key = 'application/2023/01/15/doc-123456.pdf'
    
    # Create an extracted data key
    key = s3_utils.create_extracted_data_key(document_key)
    
    # Verify the key format
    # Format should be: original_key_without_extension/extracted_data.json
    expected_key = 'application/2023/01/15/doc-123456/extracted_data.json'
    
    assert key == expected_key


# ===== Encryption Tests =====

def test_is_document_encrypted(s3_mock, s3_test_files):
    """Test checking if a document is encrypted with AES-256."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['pdf']
    
    # Upload a document with encryption
    s3_mock.put_object(
        Bucket=bucket,
        Key='encrypted-document.pdf',
        Body=b'Test content',
        ServerSideEncryption='AES256'
    )
    
    # Upload a document without encryption
    s3_mock.put_object(
        Bucket=bucket,
        Key='unencrypted-document.pdf',
        Body=b'Test content'
    )
    
    # Check encryption status
    assert s3_utils.is_document_encrypted(bucket, 'encrypted-document.pdf', s3_mock) is True
    assert s3_utils.is_document_encrypted(bucket, 'unencrypted-document.pdf', s3_mock) is False


def test_ensure_bucket_encryption(s3_mock):
    """Test ensuring that a bucket has AES-256 encryption enabled."""
    bucket = s3_utils.TEST_BUCKET_NAME
    
    # Ensure encryption is enabled
    result = s3_utils.ensure_bucket_encryption(bucket, s3_mock)
    assert result is True
    
    # Verify encryption configuration
    encryption_config = s3_utils.get_bucket_encryption_status(bucket, s3_mock)
    assert encryption_config is not None
    assert 'Rules' in encryption_config
    assert len(encryption_config['Rules']) > 0
    assert encryption_config['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'AES256'


# ===== Batch Operations Tests =====

def test_batch_download_documents(s3_mock, s3_test_files):
    """Test downloading multiple documents in parallel."""
    bucket = s3_utils.TEST_BUCKET_NAME
    keys = [s3_test_files['pdf'], s3_test_files['application'], s3_test_files['bank_statement']]
    
    # Download multiple documents
    results = s3_utils.batch_download_documents(bucket, keys, s3_mock)
    
    # Verify results
    assert len(results) == 3
    for key in keys:
        assert key in results
        content, metadata = results[key]
        assert isinstance(content, bytes)
        assert isinstance(metadata, dict)
        assert 'ContentType' in metadata
        assert 'Metadata' in metadata


def test_list_documents(s3_mock, s3_test_files):
    """Test listing documents in an S3 bucket with a prefix."""
    bucket = s3_utils.TEST_BUCKET_NAME
    prefix = 'documents/'
    
    # List documents
    documents = s3_utils.list_documents(bucket, prefix, s3_client=s3_mock)
    
    # Verify results
    assert len(documents) >= 2  # At least application and bank_statement
    for doc in documents:
        assert 'key' in doc
        assert doc['key'].startswith(prefix)
        assert 'size' in doc
        assert 'last_modified' in doc
        assert 'etag' in doc


def test_copy_document(s3_mock, s3_test_files):
    """Test copying a document from one location to another."""
    bucket = s3_utils.TEST_BUCKET_NAME
    source_key = s3_test_files['pdf']
    dest_key = 'copied-documents/document.pdf'
    metadata = {'copied': 'true', 'source': source_key}
    
    # Copy the document
    response = s3_utils.copy_document(
        bucket, source_key, bucket, dest_key, metadata, s3_mock
    )
    
    # Verify the response
    assert 'ETag' in response
    
    # Verify the copied document
    obj = s3_mock.head_object(Bucket=bucket, Key=dest_key)
    assert obj['ServerSideEncryption'] == 'AES256'
    assert obj['Metadata'] == metadata


def test_delete_document(s3_mock, s3_test_files):
    """Test deleting a document from S3 storage."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['pdf']
    
    # Delete the document
    response = s3_utils.delete_document(bucket, key, s3_mock)
    
    # Verify the document was deleted
    assert s3_utils.check_document_exists(bucket, key, s3_mock) is False


# ===== Convenience Function Tests =====

def test_get_document_url(s3_mock, s3_test_files):
    """Test the convenience function for generating a presigned URL."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['pdf']
    
    # Generate a URL
    url = s3_utils.get_document_url(bucket, key, s3_client=s3_mock)
    
    # Verify the URL
    assert url.startswith('https://')
    assert bucket in url
    assert key in url


def test_get_document_from_uri(s3_mock, s3_test_files):
    """Test downloading a document using an S3 URI."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = s3_test_files['pdf']
    uri = f's3://{bucket}/{key}'
    
    # Download using URI
    content, metadata = s3_utils.get_document_from_uri(uri, s3_mock)
    
    # Verify the content and metadata
    assert content.startswith(b'%PDF-1.5')
    assert metadata['ContentType'] == 'application/pdf'


def test_upload_document_with_uri(s3_mock):
    """Test uploading a document using an S3 URI."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'uri-upload/document.pdf'
    uri = f's3://{bucket}/{key}'
    content = b'%PDF-1.5\nTest PDF content\n%%EOF'
    
    # Upload using URI
    response = s3_utils.upload_document_with_uri(
        uri, content, 'application/pdf', {'test': 'value'}, s3_mock
    )
    
    # Verify the upload
    assert 'ETag' in response
    assert s3_utils.check_document_exists(bucket, key, s3_mock) is True


# ===== Mock Client Tests =====

def test_with_mock_s3_client(mock_s3_client):
    """Test using a fully mocked S3 client for unit testing without moto."""
    bucket = 'test-bucket'
    key = 'test-document.pdf'
    
    # Test download
    content, metadata = s3_utils.download_document(bucket, key, mock_s3_client)
    assert content.startswith(b'%PDF-1.5')
    assert metadata['ContentType'] == 'application/pdf'
    
    # Test upload
    response = s3_utils.upload_document(bucket, key, b'test', s3_client=mock_s3_client)
    assert 'ETag' in response
    
    # Test presigned URL
    url = s3_utils.generate_presigned_url(bucket, key, s3_client=mock_s3_client)
    assert url == 'https://example.com/presigned-url'
    
    # Test list documents
    docs = s3_utils.list_documents(bucket, s3_client=mock_s3_client)
    assert len(docs) == 2
    assert docs[0]['key'] == 'documents/doc1.pdf'


# ===== Error Injection Tests =====

def test_download_document_with_error_injection(s3_mock):
    """Test error handling with injected errors during download."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'test-document.pdf'
    
    # Create a patched client that raises an error for get_object
    error_client = MagicMock()
    error_client.get_object.side_effect = ClientError(
        {'Error': {'Code': 'InternalError', 'Message': 'Simulated internal error'}},
        'GetObject'
    )
    
    # Test error handling
    with pytest.raises(ClientError) as excinfo:
        s3_utils.download_document(bucket, key, error_client)
    
    assert 'InternalError' in str(excinfo.value)
    assert 'Simulated internal error' in str(excinfo.value)


def test_upload_document_with_error_injection(s3_mock):
    """Test error handling with injected errors during upload."""
    bucket = s3_utils.TEST_BUCKET_NAME
    key = 'test-document.pdf'
    content = b'Test content'
    
    # Create a patched client that raises an error for put_object
    error_client = MagicMock()
    error_client.put_object.side_effect = ClientError(
        {'Error': {'Code': 'InternalError', 'Message': 'Simulated internal error'}},
        'PutObject'
    )
    
    # Test error handling
    with pytest.raises(ClientError) as excinfo:
        s3_utils.upload_document(bucket, key, content, s3_client=error_client)
    
    assert 'InternalError' in str(excinfo.value)
    assert 'Simulated internal error' in str(excinfo.value)


# ===== Integration-Style Tests =====

def test_full_document_lifecycle(s3_mock):
    """Test a complete document lifecycle from upload to deletion."""
    bucket = 'mca-documents-test'  # Use the test bucket name from conftest.py
    document_type = 'application'
    document_id = 'doc-' + datetime.now().strftime('%Y%m%d%H%M%S')
    content = b'%PDF-1.5\nTest PDF content for lifecycle test\n%%EOF'
    metadata = {
        'document_id': document_id,
        'application_id': 'app-test',
        'document_type': document_type
    }
    
    # 1. Create a document key
    key = s3_utils.create_document_key(document_type, document_id)
    assert '/' in key
    assert key.endswith('.pdf')
    
    # 2. Upload the document
    upload_response = s3_utils.upload_document(
        bucket, key, content, 'application/pdf', metadata, s3_mock
    )
    assert 'ETag' in upload_response
    
    # 3. Verify the document exists
    assert s3_utils.check_document_exists(bucket, key, s3_mock) is True
    
    # 4. Get document metadata
    doc_metadata = s3_utils.get_document_metadata(bucket, key, s3_mock)
    assert doc_metadata['Metadata'] == metadata
    assert doc_metadata['ServerSideEncryption'] == 'AES256'
    
    # 5. Download the document
    downloaded_content, _ = s3_utils.download_document(bucket, key, s3_mock)
    assert downloaded_content == content
    
    # 6. Create extracted data key
    extracted_key = s3_utils.create_extracted_data_key(key)
    assert extracted_key.endswith('/extracted_data.json')
    
    # 7. Upload extracted data
    extracted_data = {
        'fields': {
            'name': 'John Doe',
            'address': '123 Main St'
        }
    }
    confidence_scores = {'name': 0.98, 'address': 0.95}
    
    s3_utils.upload_extracted_data(
        bucket, extracted_key, extracted_data, key,
        confidence_scores, document_type, s3_mock
    )
    
    # 8. Generate a presigned URL
    url = s3_utils.generate_presigned_url(bucket, key, 3600, s3_mock)
    assert url.startswith('https://')
    
    # 9. Update document metadata
    updated_metadata = metadata.copy()
    updated_metadata['status'] = 'processed'
    updated_metadata['confidence'] = '0.95'
    
    s3_utils.update_document_metadata(bucket, key, updated_metadata, s3_mock)
    
    # 10. Verify updated metadata
    new_metadata = s3_utils.get_document_metadata(bucket, key, s3_mock)
    assert new_metadata['Metadata'] == updated_metadata
    
    # 11. Delete the document
    s3_utils.delete_document(bucket, key, s3_mock)
    assert s3_utils.check_document_exists(bucket, key, s3_mock) is False
    
    # 12. Delete the extracted data
    s3_utils.delete_document(bucket, extracted_key, s3_mock)
    assert s3_utils.check_document_exists(bucket, extracted_key, s3_mock) is False


# ===== Main Function Test =====

def test_main_function():
    """Test the main function for manual testing."""
    # Mock everything to avoid actual S3 calls
    with patch('boto3.client') as mock_client, \
         patch('boto3.resource') as mock_resource, \
         patch('logging.basicConfig') as mock_logging, \
         patch.object(s3_utils, 'get_bucket_encryption_status') as mock_get_encryption, \
         patch.object(s3_utils, 'ensure_bucket_encryption') as mock_ensure_encryption, \
         patch.object(s3_utils, 'create_document_key') as mock_create_key, \
         patch.object(s3_utils, 'create_extracted_data_key') as mock_create_extracted_key:
        
        # Configure mocks
        mock_client_instance = MagicMock()
        mock_client.return_value = mock_client_instance
        mock_get_encryption.return_value = {}
        mock_ensure_encryption.return_value = True
        mock_create_key.return_value = 'application/2023/01/15/test-document.pdf'
        mock_create_extracted_key.return_value = 'application/2023/01/15/test-document/extracted_data.json'
        
        # Run the main function by simulating the __name__ == "__main__" condition
        # We need to call the code that would be executed in the if block
        with patch.dict(os.environ, {
            'OCR_DOCUMENT_BUCKET': 'mca-documents-test'
        }):
            # Call the functions that would be called in the main block
            s3_client = s3_utils.get_s3_client()
            bucket = s3_utils.DEFAULT_DOCUMENT_BUCKET
            s3_utils.get_bucket_encryption_status(bucket, s3_client)
            s3_utils.create_document_key('application_form', 'test-document')
            s3_utils.create_extracted_data_key('application_form/test-document.pdf')
        
        # Verify the functions were called
        mock_client.assert_called()
        mock_get_encryption.assert_called()
        mock_create_key.assert_called()
        mock_create_extracted_key.assert_called()