#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for S3 storage in the OCR Service.

This module tests the integration between the OCR Service and S3-compatible storage.
It verifies that the service correctly stores and retrieves documents and extracted data,
with proper encryption, metadata management, and error handling.

Key features tested:
1. Document storage with AES-256 encryption
2. Document retrieval with proper metadata
3. Error handling and retry logic for S3 operations
4. Bucket configuration and access control
5. Storage of both original documents and extracted data
"""

import os
import json
import pytest
import boto3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from moto import mock_s3
from botocore.exceptions import ClientError, ConnectionError

# Import OCR service modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from config import s3_config
from services.storage_service import StorageService
from types.storage import StorageMetadata, StorageOptions, EncryptionType, StorageErrorCode


# ===== Test Document Storage with AES-256 Encryption =====

@pytest.mark.usefixtures("mock_s3_client")
def test_document_upload_with_encryption(mock_s3_client, temp_dir):
    """Test that documents are uploaded with AES-256 encryption."""
    # Create a test document
    test_file_path = os.path.join(temp_dir, "test_document.pdf")
    with open(test_file_path, "wb") as f:
        f.write(b"Test document content")
    
    # Create storage service
    storage_service = StorageService()
    
    # Upload document
    document_key = "applications/test-app-123/documents/test-doc-456/application/test_document.pdf"
    metadata = {
        "document-id": "test-doc-456",
        "application-id": "test-app-123",
        "document-type": "application",
        "original-filename": "test_document.pdf"
    }
    
    with open(test_file_path, "rb") as f:
        result = storage_service.upload_document(
            key=document_key,
            data=f.read(),
            metadata=metadata,
            options=StorageOptions(
                encryption=EncryptionType.AES256,
                content_type="application/pdf"
            )
        )
    
    # Verify upload was successful
    assert result.success is True
    
    # Verify document was uploaded with AES-256 encryption
    response = mock_s3_client.get_object(Bucket=s3_config.get_bucket_name(), Key=document_key)
    assert response["ServerSideEncryption"] == "AES256"
    assert response["ContentType"] == "application/pdf"
    assert response["Metadata"] == metadata


@pytest.mark.usefixtures("mock_s3_client")
def test_extracted_data_upload_with_encryption(mock_s3_client, temp_dir):
    """Test that extracted data is uploaded with AES-256 encryption."""
    # Create storage service
    storage_service = StorageService()
    
    # Create test extraction data
    document_key = "applications/test-app-123/documents/test-doc-456/application/test_document.pdf"
    extraction_data = {
        "text": "Sample extracted text",
        "fields": {
            "business_name": "Dollar Funding LLC",
            "tax_id": "12-3456789",
            "address": "123 Main St, New York, NY 10001"
        }
    }
    confidence_scores = {
        "business_name": 0.98,
        "tax_id": 0.95,
        "address": 0.92
    }
    
    # Upload extraction results
    result = storage_service.upload_extraction_results(
        document_key=document_key,
        extraction_data=extraction_data,
        confidence_scores=confidence_scores
    )
    
    # Verify upload was successful
    assert result.success is True
    
    # Verify extraction results were uploaded with AES-256 encryption
    results_key = f"{document_key.rsplit('.', 1)[0]}_results.json"
    response = mock_s3_client.get_object(Bucket=s3_config.get_bucket_name(), Key=results_key)
    
    # Verify encryption
    assert response["ServerSideEncryption"] == "AES256"
    
    # Verify content
    results_data = json.loads(response["Body"].read().decode("utf-8"))
    assert results_data["document_key"] == document_key
    assert results_data["extracted_data"] == extraction_data
    assert results_data["confidence_scores"] == confidence_scores


# ===== Test Document Retrieval with Metadata =====

@pytest.mark.usefixtures("mock_s3_client")
def test_document_retrieval_with_metadata(mock_s3_client):
    """Test retrieving documents with metadata from S3."""
    # Create storage service
    storage_service = StorageService()
    
    # Set up test data
    bucket_name = s3_config.get_bucket_name()
    document_key = "applications/test-app-123/documents/test-doc-456/application/test_document.pdf"
    content = b"Test document content for retrieval"
    metadata = {
        "document-id": "test-doc-456",
        "application-id": "test-app-123",
        "document-type": "application",
        "original-filename": "test_document.pdf"
    }
    
    # Upload a test document to S3
    mock_s3_client.put_object(
        Bucket=bucket_name,
        Key=document_key,
        Body=content,
        Metadata=metadata,
        ServerSideEncryption="AES256",
        ContentType="application/pdf"
    )
    
    # Retrieve the document
    result = storage_service.download_document(document_key)
    
    # Verify retrieval was successful
    assert result.success is True
    assert result.data == content
    
    # Verify metadata was retrieved correctly
    assert result.metadata is not None
    assert "metadata" in result.metadata
    assert result.metadata["metadata"] == metadata
    assert result.metadata["content_type"] == "application/pdf"
    assert result.metadata["server_side_encryption"] == "AES256"


@pytest.mark.usefixtures("mock_s3_client")
def test_extraction_results_retrieval(mock_s3_client):
    """Test retrieving extraction results from S3."""
    # Create storage service
    storage_service = StorageService()
    
    # Set up test data
    bucket_name = s3_config.get_bucket_name()
    document_key = "applications/test-app-123/documents/test-doc-456/application/test_document.pdf"
    results_key = f"{document_key.rsplit('.', 1)[0]}_results.json"
    
    extraction_data = {
        "document_key": document_key,
        "extracted_data": {
            "text": "Sample extracted text",
            "fields": {
                "business_name": "Dollar Funding LLC",
                "tax_id": "12-3456789"
            }
        },
        "confidence_scores": {
            "business_name": 0.98,
            "tax_id": 0.95
        },
        "version": "1.0.0-test",
        "extraction_timestamp": "2023-05-21T10:30:00Z"
    }
    
    # Upload test extraction results to S3
    mock_s3_client.put_object(
        Bucket=bucket_name,
        Key=results_key,
        Body=json.dumps(extraction_data).encode("utf-8"),
        ServerSideEncryption="AES256",
        ContentType="application/json",
        Metadata={
            "content-type": "application/json",
            "extraction-service": "ocr-service",
            "extraction-timestamp": "2023-05-21T10:30:00Z"
        }
    )
    
    # Retrieve the extraction results
    result = storage_service.get_extraction_results(document_key)
    
    # Verify retrieval was successful
    assert result.success is True
    
    # Verify extraction data was retrieved correctly
    assert result.data is not None
    assert result.data["document_key"] == document_key
    assert result.data["extracted_data"]["fields"]["business_name"] == "Dollar Funding LLC"
    assert result.data["confidence_scores"]["business_name"] == 0.98


# ===== Test Error Handling and Retry Logic =====

def test_download_document_with_connection_error():
    """Test document download with a connection error that triggers retries."""
    # Create a mock S3 client that raises a connection error
    mock_client = MagicMock()
    mock_client.get_object.side_effect = ConnectionError("Connection failed")
    
    # Create a storage service with the mock client
    with patch("boto3.client", return_value=mock_client):
        storage_service = StorageService()
        
        # Patch the retry decorator to use small delays for faster testing
        with patch("services.storage_service.with_retry", 
                  return_value=lambda func: lambda *args, **kwargs: func(*args, **kwargs)):
            result = storage_service.download_document("test-key")
    
    # Verify the result
    assert result.success is False
    assert "connection error" in result.error.lower() or "failed" in result.error.lower()
    
    # Verify the client method was called
    mock_client.get_object.assert_called_once()


@pytest.mark.usefixtures("mock_s3_client")
def test_document_not_found_error(mock_s3_client):
    """Test error handling when a document doesn't exist."""
    # Create storage service
    storage_service = StorageService()
    
    # Attempt to retrieve a non-existent document
    result = storage_service.download_document("non-existent-document.pdf")
    
    # Verify the result
    assert result.success is False
    assert result.error_code in [StorageErrorCode.OBJECT_NOT_FOUND, StorageErrorCode.RESOURCE_NOT_FOUND]
    assert "not found" in result.error.lower() or "does not exist" in result.error.lower()


@pytest.mark.usefixtures("mock_s3_client")
def test_upload_with_retry_on_failure(mock_s3_client):
    """Test retry logic for document upload."""
    # Create a storage service
    storage_service = StorageService()
    
    # Create a mock S3 client that fails once then succeeds
    original_put_object = mock_s3_client.put_object
    call_count = [0]
    
    def mock_put_object(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            raise ConnectionError("Simulated connection error")
        return original_put_object(*args, **kwargs)
    
    mock_s3_client.put_object = mock_put_object
    
    # Upload document with retry
    document_key = "test-retry-document.pdf"
    content = b"Test document content for retry"
    
    result = storage_service.upload_document(
        key=document_key,
        data=content,
        options=StorageOptions(encryption=EncryptionType.AES256)
    )
    
    # Verify upload was eventually successful
    assert result.success is True
    assert call_count[0] > 1  # Ensure retry happened
    
    # Verify document was uploaded
    response = mock_s3_client.get_object(Bucket=s3_config.get_bucket_name(), Key=document_key)
    assert response["Body"].read() == content


# ===== Test Bucket Configuration and Access Control =====

@pytest.mark.usefixtures("mock_s3_client")
def test_bucket_versioning(mock_s3_client):
    """Test that bucket versioning is enabled."""
    # Create storage service
    storage_service = StorageService()
    
    # Enable versioning on the bucket
    bucket_name = s3_config.get_bucket_name()
    mock_s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"}
    )
    
    # Check if versioning is enabled
    result = storage_service.check_bucket_versioning()
    
    # Verify versioning is enabled
    assert result is True


@pytest.mark.usefixtures("mock_s3_client")
def test_document_versioning(mock_s3_client):
    """Test document versioning in S3."""
    # Create storage service
    storage_service = StorageService()
    
    # Enable versioning on the bucket
    bucket_name = s3_config.get_bucket_name()
    mock_s3_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={"Status": "Enabled"}
    )
    
    # Upload multiple versions of a document
    document_key = "test-versioned-document.pdf"
    content_v1 = b"Version 1 content"
    content_v2 = b"Version 2 content"
    
    # Upload version 1
    result_v1 = storage_service.upload_document(
        key=document_key,
        data=content_v1,
        options=StorageOptions(encryption=EncryptionType.AES256)
    )
    version_id_v1 = result_v1.version_id
    
    # Upload version 2
    result_v2 = storage_service.upload_document(
        key=document_key,
        data=content_v2,
        options=StorageOptions(encryption=EncryptionType.AES256)
    )
    version_id_v2 = result_v2.version_id
    
    # Verify both uploads were successful and have different version IDs
    assert result_v1.success is True
    assert result_v2.success is True
    assert version_id_v1 is not None
    assert version_id_v2 is not None
    assert version_id_v1 != version_id_v2
    
    # Retrieve the latest version (v2)
    result_latest = storage_service.download_document(document_key)
    
    # Retrieve version 1 specifically
    result_v1_specific = storage_service.download_document(document_key, version_id=version_id_v1)
    
    # Verify retrievals were successful
    assert result_latest.success is True
    assert result_v1_specific.success is True
    
    # Verify content matches expected versions
    assert result_latest.data == content_v2
    assert result_v1_specific.data == content_v1


@pytest.mark.usefixtures("mock_s3_client")
def test_bucket_encryption_configuration(mock_s3_client):
    """Test that bucket encryption is properly configured."""
    # Create storage service
    storage_service = StorageService()
    
    # Set up bucket encryption configuration
    bucket_name = s3_config.get_bucket_name()
    mock_s3_client.put_bucket_encryption(
        Bucket=bucket_name,
        ServerSideEncryptionConfiguration={
            "Rules": [
                {
                    "ApplyServerSideEncryptionByDefault": {
                        "SSEAlgorithm": "AES256"
                    },
                    "BucketKeyEnabled": True
                }
            ]
        }
    )
    
    # Get bucket encryption configuration
    response = mock_s3_client.get_bucket_encryption(Bucket=bucket_name)
    
    # Verify encryption configuration
    rules = response["ServerSideEncryptionConfiguration"]["Rules"]
    assert len(rules) > 0
    assert rules[0]["ApplyServerSideEncryptionByDefault"]["SSEAlgorithm"] == "AES256"


# ===== Test Storage of Original Documents and Extracted Data =====

@pytest.mark.usefixtures("mock_s3_client")
def test_complete_document_processing_flow(mock_s3_client, temp_dir):
    """Test the complete flow of storing original document and extracted data."""
    # Create a test document
    test_file_path = os.path.join(temp_dir, "complete_flow_document.pdf")
    with open(test_file_path, "wb") as f:
        f.write(b"Test document content for complete flow")
    
    # Create storage service
    storage_service = StorageService()
    
    # 1. Upload original document
    document_key = "applications/test-app-789/documents/test-doc-123/application/complete_flow_document.pdf"
    metadata = {
        "document-id": "test-doc-123",
        "application-id": "test-app-789",
        "document-type": "application",
        "original-filename": "complete_flow_document.pdf"
    }
    
    with open(test_file_path, "rb") as f:
        upload_result = storage_service.upload_document(
            key=document_key,
            data=f.read(),
            metadata=metadata,
            options=StorageOptions(
                encryption=EncryptionType.AES256,
                content_type="application/pdf"
            )
        )
    
    # Verify document upload was successful
    assert upload_result.success is True
    
    # 2. Upload extraction results
    extraction_data = {
        "text": "Complete flow extracted text",
        "fields": {
            "business_name": "Complete Flow LLC",
            "tax_id": "98-7654321",
            "address": "456 Flow St, San Francisco, CA 94107"
        }
    }
    confidence_scores = {
        "business_name": 0.99,
        "tax_id": 0.97,
        "address": 0.94
    }
    
    extraction_result = storage_service.upload_extraction_results(
        document_key=document_key,
        extraction_data=extraction_data,
        confidence_scores=confidence_scores
    )
    
    # Verify extraction results upload was successful
    assert extraction_result.success is True
    
    # 3. Retrieve original document
    document_result = storage_service.download_document(document_key)
    
    # Verify document retrieval was successful
    assert document_result.success is True
    assert document_result.data == b"Test document content for complete flow"
    
    # 4. Retrieve extraction results
    results_result = storage_service.get_extraction_results(document_key)
    
    # Verify extraction results retrieval was successful
    assert results_result.success is True
    assert results_result.data["extracted_data"]["fields"]["business_name"] == "Complete Flow LLC"
    assert results_result.data["confidence_scores"]["business_name"] == 0.99
    
    # 5. Update document metadata with extraction status
    updated_metadata = metadata.copy()
    updated_metadata["extraction-status"] = "completed"
    updated_metadata["extraction-confidence"] = "0.97"
    
    metadata_result = storage_service.update_document_metadata(document_key, updated_metadata)
    
    # Verify metadata update was successful
    assert metadata_result.success is True
    
    # 6. Verify updated metadata
    updated_document_result = storage_service.download_document(document_key)
    
    # Verify updated metadata was retrieved correctly
    assert updated_document_result.success is True
    assert updated_document_result.metadata["metadata"]["extraction-status"] == "completed"
    assert updated_document_result.metadata["metadata"]["extraction-confidence"] == "0.97"