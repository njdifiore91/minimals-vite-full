#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the S3-compatible storage service.

This module contains tests for the StorageService class, which provides
S3-compatible storage operations for the OCR Service microservice. It verifies
document retrieval, storage operations, encryption implementation, and metadata
management with proper security measures including AES-256 encryption.

Key test areas:
1. S3 client connection and authentication
2. Document download functionality from specified buckets
3. AES-256 encryption implementation for document storage
4. Error handling and retry logic for storage operations
5. Document metadata extraction and updating functionality
6. Versioning support for document history tracking
"""

import os
import json
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock, mock_open

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_s3

from src.services.storage_service import StorageService
from src.types.storage import (
    StorageResult,
    StorageMetadata,
    StorageOptions,
    StorageErrorCode,
    StorageKey,
    SignedUrlOptions
)


@pytest.fixture
def s3_client():
    """Fixture that provides a mocked S3 client using moto."""
    with mock_s3():
        # Set up test environment variables
        os.environ["AWS_ACCESS_KEY_ID"] = "testing"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        
        # Create S3 client
        s3 = boto3.client('s3', region_name='us-east-1')
        
        # Create test buckets
        s3.create_bucket(Bucket='mca-documents-production')
        s3.create_bucket(Bucket='mca-documents-staging')
        s3.create_bucket(Bucket='mca-extracted-data-production')
        s3.create_bucket(Bucket='mca-extracted-data-staging')
        
        yield s3


@pytest.fixture
def storage_service(s3_client):
    """Fixture that provides a StorageService instance with mocked S3 client."""
    with patch('src.services.storage_service.boto3.client', return_value=s3_client):
        service = StorageService()
        yield service


@pytest.fixture
def test_document():
    """Fixture that provides a temporary test document."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(b"This is a test document for OCR processing.")
        tmp_path = tmp.name
    
    yield tmp_path
    
    # Clean up the temporary file
    if os.path.exists(tmp_path):
        os.unlink(tmp_path)


@pytest.fixture
def test_metadata():
    """Fixture that provides test document metadata."""
    return {
        "document-id": "doc-123",
        "application-id": "app-456",
        "document-type": "invoice",
        "original-filename": "invoice.pdf",
        "created-at": datetime.now().isoformat(),
        "extraction-status": "pending",
        "custom-field1": "value1",
        "custom-field2": "value2"
    }


class TestStorageService:
    """Test cases for the StorageService class."""

    def test_initialization(self, storage_service):
        """Test that the StorageService initializes correctly."""
        assert storage_service is not None
        assert storage_service.document_bucket == "mca-documents-production"
        assert storage_service.extracted_data_bucket == "mca-extracted-data-production"

    def test_download_document(self, storage_service, s3_client, test_document):
        """Test downloading a document from S3 storage."""
        # Upload a test document to S3
        key = "test/document.txt"
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ServerSideEncryption="AES256"
            )
        
        # Download the document
        result = storage_service.download_document(key)
        
        # Verify the result
        assert result.success is True
        assert os.path.exists(result.data)
        
        # Verify the content
        with open(result.data, 'rb') as f:
            content = f.read()
            assert content == b"This is a test document for OCR processing."

    def test_download_document_with_local_path(self, storage_service, s3_client, test_document):
        """Test downloading a document to a specific local path."""
        # Upload a test document to S3
        key = "test/document_local.txt"
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ServerSideEncryption="AES256"
            )
        
        # Create a local path for download
        local_path = os.path.join(tempfile.gettempdir(), "downloaded_document.txt")
        
        # Download the document to the local path
        result = storage_service.download_document(key, local_path)
        
        # Verify the result
        assert result.success is True
        assert result.data == local_path
        assert os.path.exists(local_path)
        
        # Verify the content
        with open(local_path, 'rb') as f:
            content = f.read()
            assert content == b"This is a test document for OCR processing."
        
        # Clean up
        if os.path.exists(local_path):
            os.unlink(local_path)

    def test_download_document_not_found(self, storage_service):
        """Test downloading a document that doesn't exist."""
        key = "test/nonexistent.txt"
        
        # Download the document
        result = storage_service.download_document(key)
        
        # Verify the result
        assert result.success is False
        assert result.error_code == StorageErrorCode.RESOURCE_NOT_FOUND

    def test_upload_document(self, storage_service, test_document, test_metadata):
        """Test uploading a document to S3 storage with AES-256 encryption."""
        key = "test/uploaded_document.txt"
        
        # Upload the document
        result = storage_service.upload_document(
            local_path=test_document,
            key=key,
            metadata=test_metadata,
            content_type="text/plain"
        )
        
        # Verify the result
        assert result.success is True
        assert result.data == key
        
        # Verify the document was uploaded with encryption
        response = storage_service.s3_client.head_object(
            Bucket=storage_service.document_bucket,
            Key=key
        )
        
        # Check encryption
        assert response.get('ServerSideEncryption') == "AES256"
        
        # Check metadata
        for key, value in test_metadata.items():
            assert response['Metadata'].get(key.lower()) == value
        
        # Check content type
        assert response.get('ContentType') == "text/plain"

    def test_upload_extracted_data(self, storage_service):
        """Test uploading extracted OCR data to S3 storage."""
        key = "test/extracted_data.json"
        data = {
            "document_id": "doc-123",
            "application_id": "app-456",
            "extracted_fields": {
                "invoice_number": {
                    "value": "INV-12345",
                    "confidence": 0.95
                },
                "date": {
                    "value": "2025-05-01",
                    "confidence": 0.92
                },
                "total_amount": {
                    "value": "$1,234.56",
                    "confidence": 0.88
                }
            }
        }
        
        # Upload the extracted data
        result = storage_service.upload_extracted_data(
            data=data,
            key=key,
            metadata=test_metadata
        )
        
        # Verify the result
        assert result.success is True
        assert result.data == key
        
        # Verify the data was uploaded with encryption
        response = storage_service.s3_client.get_object(
            Bucket=storage_service.extracted_data_bucket,
            Key=key
        )
        
        # Check encryption
        assert response.get('ServerSideEncryption') == "AES256"
        
        # Check content
        content = response['Body'].read().decode('utf-8')
        uploaded_data = json.loads(content)
        assert uploaded_data == data

    def test_get_document_metadata(self, storage_service, s3_client, test_document, test_metadata):
        """Test retrieving document metadata from S3 storage."""
        key = "test/metadata_document.txt"
        
        # Upload a test document with metadata
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                Metadata=test_metadata,
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Get the metadata
        result = storage_service.get_document_metadata(key)
        
        # Verify the result
        assert result.success is True
        assert isinstance(result.data, StorageMetadata)
        
        # Check metadata fields
        assert result.data.document_id == test_metadata['document-id']
        assert result.data.application_id == test_metadata['application-id']
        assert result.data.document_type == test_metadata['document-type']
        assert result.data.original_filename == test_metadata['original-filename']
        assert result.data.content_type == "text/plain"
        assert result.data.extraction_status == test_metadata['extraction-status']
        
        # Check custom metadata
        assert result.data.custom_metadata['field1'] == test_metadata['custom-field1']
        assert result.data.custom_metadata['field2'] == test_metadata['custom-field2']

    def test_update_document_metadata(self, storage_service, s3_client, test_document, test_metadata):
        """Test updating document metadata in S3 storage."""
        key = "test/update_metadata_document.txt"
        
        # Upload a test document with metadata
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                Metadata=test_metadata,
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Update metadata
        metadata_updates = {
            "extraction-status": "completed",
            "extraction-confidence": "0.95",
            "custom-field3": "new-value"
        }
        
        result = storage_service.update_document_metadata(key, metadata_updates)
        
        # Verify the result
        assert result.success is True
        
        # Get the updated metadata
        updated_metadata_result = storage_service.get_document_metadata(key)
        updated_metadata = updated_metadata_result.data
        
        # Check updated fields
        assert updated_metadata.extraction_status == "completed"
        assert updated_metadata.extraction_confidence == 0.95
        assert updated_metadata.custom_metadata['field3'] == "new-value"
        
        # Check that original fields are preserved
        assert updated_metadata.document_id == test_metadata['document-id']
        assert updated_metadata.application_id == test_metadata['application-id']
        assert updated_metadata.document_type == test_metadata['document-type']

    def test_update_extraction_status(self, storage_service, s3_client, test_document, test_metadata):
        """Test updating extraction status and confidence for a document."""
        key = "test/extraction_status_document.txt"
        
        # Upload a test document with metadata
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                Metadata=test_metadata,
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Update extraction status and confidence
        result = storage_service.update_extraction_status(
            key=key,
            status="completed",
            confidence=0.98
        )
        
        # Verify the result
        assert result.success is True
        
        # Get the updated metadata
        updated_metadata_result = storage_service.get_document_metadata(key)
        updated_metadata = updated_metadata_result.data
        
        # Check updated fields
        assert updated_metadata.extraction_status == "completed"
        assert updated_metadata.extraction_confidence == 0.98

    def test_get_document_versions(self, storage_service, s3_client, test_document):
        """Test retrieving version history for a document in S3 storage."""
        key = "test/versioned_document.txt"
        
        # Enable versioning on the bucket
        s3_client.put_bucket_versioning(
            Bucket=storage_service.document_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Upload initial version
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Upload second version
        s3_client.put_object(
            Bucket=storage_service.document_bucket,
            Key=key,
            Body=b"Updated content for version 2",
            ContentType="text/plain",
            ServerSideEncryption="AES256"
        )
        
        # Get version history
        result = storage_service.get_document_versions(key)
        
        # Verify the result
        assert result.success is True
        assert len(result.data) == 2  # Should have two versions
        
        # Check version attributes
        for version in result.data:
            assert 'version_id' in version
            assert 'last_modified' in version
            assert 'size_bytes' in version
            assert 'is_latest' in version
            assert 'etag' in version

    def test_get_document_version(self, storage_service, s3_client, test_document):
        """Test retrieving a specific version of a document from S3 storage."""
        key = "test/specific_version_document.txt"
        
        # Enable versioning on the bucket
        s3_client.put_bucket_versioning(
            Bucket=storage_service.document_bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Upload initial version
        with open(test_document, 'rb') as f:
            response = s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Get the version ID
        version_id = response['VersionId']
        
        # Upload second version
        s3_client.put_object(
            Bucket=storage_service.document_bucket,
            Key=key,
            Body=b"Updated content for version 2",
            ContentType="text/plain",
            ServerSideEncryption="AES256"
        )
        
        # Get the specific version
        result = storage_service.get_document_version(key, version_id)
        
        # Verify the result
        assert result.success is True
        assert os.path.exists(result.data)
        
        # Verify the content matches the first version
        with open(result.data, 'rb') as f:
            content = f.read()
            assert content == b"This is a test document for OCR processing."

    def test_generate_presigned_url(self, storage_service, s3_client, test_document):
        """Test generating a presigned URL for accessing a document."""
        key = "test/presigned_url_document.txt"
        
        # Upload a test document
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Generate a presigned URL
        options = SignedUrlOptions(expiration=3600)
        result = storage_service.generate_presigned_url(key, options)
        
        # Verify the result
        assert result.success is True
        assert isinstance(result.data, str)
        assert "https://" in result.data
        assert key in result.data
        assert "AWSAccessKeyId" in result.data
        assert "Signature" in result.data
        assert "Expires" in result.data

    def test_check_document_exists(self, storage_service, s3_client, test_document):
        """Test checking if a document exists in S3 storage."""
        key = "test/exists_document.txt"
        
        # Upload a test document
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Check if document exists
        result = storage_service.check_document_exists(key)
        
        # Verify the result
        assert result.success is True
        assert result.data is True
        
        # Check for non-existent document
        nonexistent_result = storage_service.check_document_exists("test/nonexistent.txt")
        
        # Verify the result
        assert nonexistent_result.success is True
        assert nonexistent_result.data is False

    def test_list_documents(self, storage_service, s3_client, test_document):
        """Test listing documents in S3 storage with a given prefix."""
        prefix = "test/list/"
        
        # Upload multiple test documents with the same prefix
        for i in range(3):
            key = f"{prefix}document_{i}.txt"
            with open(test_document, 'rb') as f:
                s3_client.put_object(
                    Bucket=storage_service.document_bucket,
                    Key=key,
                    Body=f.read(),
                    ContentType="text/plain",
                    ServerSideEncryption="AES256"
                )
        
        # Upload a document with a different prefix
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key="different/prefix/document.txt",
                Body=f.read(),
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # List documents with the prefix
        result = storage_service.list_documents(prefix)
        
        # Verify the result
        assert result.success is True
        assert len(result.data) == 3
        
        # Check that all documents have the correct prefix
        for document in result.data:
            assert document['key'].startswith(prefix)

    def test_delete_document(self, storage_service, s3_client, test_document):
        """Test deleting a document from S3 storage."""
        key = "test/delete_document.txt"
        
        # Upload a test document
        with open(test_document, 'rb') as f:
            s3_client.put_object(
                Bucket=storage_service.document_bucket,
                Key=key,
                Body=f.read(),
                ContentType="text/plain",
                ServerSideEncryption="AES256"
            )
        
        # Verify the document exists
        exists_result = storage_service.check_document_exists(key)
        assert exists_result.success is True
        assert exists_result.data is True
        
        # Delete the document
        delete_result = storage_service.delete_document(key)
        
        # Verify the delete result
        assert delete_result.success is True
        assert delete_result.data is True
        
        # Verify the document no longer exists
        after_delete_result = storage_service.check_document_exists(key)
        assert after_delete_result.success is True
        assert after_delete_result.data is False

    def test_calculate_md5(self, storage_service, test_document):
        """Test calculating MD5 hash for a file."""
        # Calculate MD5 hash
        md5_hash = storage_service.calculate_md5(test_document)
        
        # Verify the result is a valid MD5 hash
        assert isinstance(md5_hash, str)
        assert len(md5_hash) == 32  # MD5 hash is 32 characters long
        
        # Verify the hash is consistent
        second_hash = storage_service.calculate_md5(test_document)
        assert md5_hash == second_hash

    def test_health_check(self, storage_service):
        """Test the health check functionality."""
        # Perform health check
        result = storage_service.health_check()
        
        # Verify the result
        assert result is True

    def test_error_handling_connection_error(self, storage_service):
        """Test error handling for connection errors."""
        # Mock a connection error
        error_response = {
            'Error': {
                'Code': 'ConnectionError',
                'Message': 'Connection error occurred'
            }
        }
        client_error = ClientError(error_response, 'GetObject')
        
        with patch.object(storage_service.s3_client, 'download_file', side_effect=client_error):
            result = storage_service.download_document("test/error_document.txt")
        
        # Verify the result
        assert result.success is False
        assert result.error_code == StorageErrorCode.CONNECTION_ERROR
        assert "Connection error occurred" in result.error_message

    def test_error_handling_timeout(self, storage_service):
        """Test error handling for timeout errors."""
        # Mock a timeout error
        error_response = {
            'Error': {
                'Code': 'RequestTimeout',
                'Message': 'Request timed out'
            }
        }
        client_error = ClientError(error_response, 'GetObject')
        
        with patch.object(storage_service.s3_client, 'download_file', side_effect=client_error):
            result = storage_service.download_document("test/timeout_document.txt")
        
        # Verify the result
        assert result.success is False
        assert result.error_code == StorageErrorCode.TIMEOUT
        assert "Request timed out" in result.error_message

    def test_error_handling_access_denied(self, storage_service):
        """Test error handling for access denied errors."""
        # Mock an access denied error
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access denied'
            }
        }
        client_error = ClientError(error_response, 'GetObject')
        
        with patch.object(storage_service.s3_client, 'download_file', side_effect=client_error):
            result = storage_service.download_document("test/access_denied_document.txt")
        
        # Verify the result
        assert result.success is False
        assert result.error_code == StorageErrorCode.ACCESS_DENIED
        assert "Access denied" in result.error_message

    def test_error_handling_unknown_error(self, storage_service):
        """Test error handling for unknown errors."""
        # Mock an unknown error
        with patch.object(storage_service.s3_client, 'download_file', side_effect=Exception("Unknown error")):
            result = storage_service.download_document("test/unknown_error_document.txt")
        
        # Verify the result
        assert result.success is False
        assert result.error_code == StorageErrorCode.UNKNOWN_ERROR
        assert "Unknown error" in result.error_message

    def test_retry_logic(self, storage_service):
        """Test retry logic for transient errors."""
        # Mock a connection error that succeeds on the second attempt
        error_response = {
            'Error': {
                'Code': 'ConnectionError',
                'Message': 'Connection error occurred'
            }
        }
        client_error = ClientError(error_response, 'GetObject')
        
        # Create a side effect that fails on first call but succeeds on second call
        mock_download = MagicMock(side_effect=[client_error, None])
        
        with patch.object(storage_service.s3_client, 'download_file', mock_download):
            result = storage_service.download_document("test/retry_document.txt")
        
        # Verify the result
        assert result.success is True
        assert mock_download.call_count == 2  # Should have been called twice due to retry


if __name__ == "__main__":
    pytest.main()