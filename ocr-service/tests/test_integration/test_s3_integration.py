#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for S3 storage in the OCR Service.

This module tests the integration between the OCR Service and S3-compatible storage,
verifying document storage and retrieval with AES-256 encryption, metadata management,
error handling, and bucket configuration.

Key test areas:
1. Document upload and download with AES-256 encryption
2. Metadata management for documents
3. Error handling and retry logic for S3 operations
4. Bucket configuration and access control
5. Extraction results storage and retrieval
"""

import json
import os
import pytest
import boto3
import botocore
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError, ConnectionError

# Import application modules
from src.services.storage_service import StorageService
from src.types.storage import StorageOptions, StorageResult
from src.types.extraction import ExtractedData


class TestS3Integration:
    """Test suite for S3 integration with the OCR Service."""

    def test_document_upload_with_encryption(self, s3_mock, s3_client_config, sample_document):
        """Test uploading a document with AES-256 encryption.
        
        This test verifies that documents are uploaded with AES-256 encryption
        as required by the technical specification.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Upload the document
        result = storage_service.upload_document(
            key=document_key,
            data=sample_document.content,
            metadata={
                "document_id": sample_document.metadata.document_id,
                "application_id": sample_document.metadata.application_id,
                "content_type": sample_document.metadata.content_type
            }
        )
        
        # Verify upload was successful
        assert result.success is True
        assert result.version_id is not None
        
        # Verify the document was uploaded with AES-256 encryption
        response = s3_mock.head_object(
            Bucket=s3_client_config.bucket,
            Key=document_key
        )
        
        # Check for AES-256 encryption
        assert response.get('ServerSideEncryption') == 'AES256', "Document not encrypted with AES-256"
        
        # Verify metadata was stored correctly
        assert response.get('Metadata', {}).get('document_id') == sample_document.metadata.document_id
        assert response.get('Metadata', {}).get('application_id') == sample_document.metadata.application_id

    def test_document_download_and_metadata(self, s3_mock, s3_client_config, sample_document):
        """Test downloading a document and retrieving its metadata.
        
        This test verifies that documents can be downloaded from S3 storage
        and that metadata is correctly retrieved.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Upload the document first
        s3_mock.put_object(
            Bucket=s3_client_config.bucket,
            Key=document_key,
            Body=sample_document.content,
            ServerSideEncryption='AES256',
            Metadata={
                "document_id": sample_document.metadata.document_id,
                "application_id": sample_document.metadata.application_id,
                "content_type": sample_document.metadata.content_type
            }
        )
        
        # Download the document
        result = storage_service.download_document(key=document_key)
        
        # Verify download was successful
        assert result.success is True
        assert result.data == sample_document.content
        
        # Verify metadata was retrieved correctly
        assert result.metadata is not None
        assert result.metadata.metadata.get('document_id') == sample_document.metadata.document_id
        assert result.metadata.metadata.get('application_id') == sample_document.metadata.application_id
        assert result.metadata.server_side_encryption == 'AES256'

    def test_extraction_results_storage(self, s3_mock, s3_client_config, sample_document, sample_extracted_data):
        """Test storing OCR extraction results in S3.
        
        This test verifies that OCR extraction results are correctly stored in S3
        with proper metadata and encryption.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Extract confidence scores from sample data
        confidence_scores = {field_name: field.confidence.value 
                            for field_name, field in sample_extracted_data.fields.items()}
        
        # Convert extracted data to dictionary for storage
        extraction_data = {
            "document_id": sample_extracted_data.document_id,
            "application_id": sample_extracted_data.application_id,
            "document_type": sample_extracted_data.document_type.value,
            "fields": {name: {"value": field.value} 
                      for name, field in sample_extracted_data.fields.items()},
            "requires_verification": sample_extracted_data.requires_verification,
            "processing_time": sample_extracted_data.processing_time
        }
        
        # Upload extraction results
        result = storage_service.upload_extraction_results(
            document_key=document_key,
            extraction_data=extraction_data,
            confidence_scores=confidence_scores
        )
        
        # Verify upload was successful
        assert result.success is True
        
        # Verify the results were stored with correct key format
        results_key = f"{document_key.rsplit('.', 1)[0]}_results.json"
        
        # Check if results exist in S3
        response = s3_mock.get_object(
            Bucket=s3_client_config.bucket,
            Key=results_key
        )
        
        # Verify encryption
        assert response.get('ServerSideEncryption') == 'AES256'
        
        # Verify content
        content = json.loads(response['Body'].read().decode('utf-8'))
        assert content['document_key'] == document_key
        assert 'extraction_timestamp' in content
        assert content['extracted_data'] == extraction_data
        assert content['confidence_scores'] == confidence_scores

    def test_metadata_update(self, s3_mock, s3_client_config, sample_document):
        """Test updating document metadata in S3.
        
        This test verifies that document metadata can be updated after upload.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Upload the document first
        s3_mock.put_object(
            Bucket=s3_client_config.bucket,
            Key=document_key,
            Body=sample_document.content,
            ServerSideEncryption='AES256',
            Metadata={
                "document_id": sample_document.metadata.document_id,
                "application_id": sample_document.metadata.application_id,
                "content_type": sample_document.metadata.content_type
            }
        )
        
        # Update metadata
        new_metadata = {
            "document_id": sample_document.metadata.document_id,
            "application_id": sample_document.metadata.application_id,
            "content_type": sample_document.metadata.content_type,
            "processing_status": "completed",
            "confidence_score": "0.95"
        }
        
        result = storage_service.update_document_metadata(
            key=document_key,
            metadata=new_metadata
        )
        
        # Verify update was successful
        assert result.success is True
        
        # Verify metadata was updated
        response = s3_mock.head_object(
            Bucket=s3_client_config.bucket,
            Key=document_key
        )
        
        # Check updated metadata
        assert response.get('Metadata', {}).get('processing_status') == 'completed'
        assert response.get('Metadata', {}).get('confidence_score') == '0.95'

    def test_document_versioning(self, s3_mock, s3_client_config, sample_document):
        """Test document versioning in S3.
        
        This test verifies that document versioning is correctly implemented
        for audit and compliance purposes.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Enable versioning on the bucket
        s3_mock.put_bucket_versioning(
            Bucket=s3_client_config.bucket,
            VersioningConfiguration={'Status': 'Enabled'}
        )
        
        # Verify versioning is enabled
        assert storage_service.check_bucket_versioning() is True
        
        # Upload the document multiple times to create versions
        for i in range(3):
            modified_content = sample_document.content + f"\nVersion {i+1}".encode('utf-8')
            result = storage_service.upload_document(
                key=document_key,
                data=modified_content,
                metadata={
                    "document_id": sample_document.metadata.document_id,
                    "version": str(i+1)
                }
            )
            assert result.success is True
        
        # Get document versions
        result = storage_service.get_document_versions(key=document_key)
        
        # Verify versions were retrieved
        assert result.success is True
        assert result.data is not None
        assert len(result.data) == 3  # Should have 3 versions

    def test_error_handling_nonexistent_document(self, s3_mock, s3_client_config):
        """Test error handling for nonexistent documents.
        
        This test verifies that the storage service correctly handles attempts
        to download nonexistent documents.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Attempt to download a nonexistent document
        result = storage_service.download_document(key="nonexistent/document.pdf")
        
        # Verify the operation failed with appropriate error
        assert result.success is False
        assert "NoSuchKey" in result.error or "not found" in result.error.lower()

    @patch('src.services.storage_service.boto3.client')
    def test_retry_logic_connection_error(self, mock_boto3_client, s3_client_config, sample_document):
        """Test retry logic for connection errors.
        
        This test verifies that the storage service correctly implements retry logic
        with exponential backoff for connection errors.
        """
        # Configure mock to raise ConnectionError on first two calls, then succeed
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        # First two calls raise ConnectionError, third succeeds
        mock_s3.get_object.side_effect = [
            ConnectionError("Connection error"),
            ConnectionError("Connection error"),
            {
                'Body': MagicMock(read=lambda: sample_document.content),
                'Metadata': {'document_id': sample_document.metadata.document_id},
                'ServerSideEncryption': 'AES256'
            }
        ]
        
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Patch the retry decorator to use shorter delays for testing
        with patch('src.services.storage_service.with_retry', 
                  lambda max_retries=3, base_delay=0.1, max_delay=0.3: 
                  lambda f: lambda *args, **kwargs: f(*args, **kwargs)):
            
            # Download the document (should retry and eventually succeed)
            result = storage_service.download_document(key=document_key)
            
            # Verify download was successful after retries
            assert result.success is True
            assert result.data == sample_document.content
            
            # Verify get_object was called 3 times (2 failures + 1 success)
            assert mock_s3.get_object.call_count == 3

    def test_presigned_url_generation(self, s3_mock, s3_client_config, sample_document):
        """Test generation of presigned URLs for secure document access.
        
        This test verifies that the storage service can generate presigned URLs
        with appropriate expiration times for secure document access.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Define test document key
        document_key = f"documents/{sample_document.metadata.document_id}.pdf"
        
        # Upload the document first
        s3_mock.put_object(
            Bucket=s3_client_config.bucket,
            Key=document_key,
            Body=sample_document.content,
            ServerSideEncryption='AES256'
        )
        
        # Generate a presigned URL with short expiration
        url = storage_service.generate_presigned_url(
            key=document_key,
            expiration=60  # 1 minute expiration
        )
        
        # Verify URL was generated
        assert url is not None
        assert document_key in url
        assert "X-Amz-Algorithm" in url
        assert "X-Amz-Credential" in url
        assert "X-Amz-Date" in url
        assert "X-Amz-Expires" in url
        assert "X-Amz-SignedHeaders" in url
        assert "X-Amz-Signature" in url

    def test_bucket_access_control(self, s3_mock, s3_client_config):
        """Test bucket access control for security.
        
        This test verifies that the storage service correctly handles bucket
        access control for security purposes.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Verify the service can access the configured bucket
        assert storage_service.document_exists("test-document.txt") is False
        
        # Test with incorrect bucket configuration
        invalid_config = s3_client_config
        invalid_config.bucket = "nonexistent-bucket"
        
        invalid_storage_service = StorageService(invalid_config)
        
        # Attempt to check document existence in nonexistent bucket
        with pytest.raises(Exception) as excinfo:
            invalid_storage_service.document_exists("test-document.txt")
        
        # Verify appropriate error was raised
        assert "NoSuchBucket" in str(excinfo.value) or "not found" in str(excinfo.value).lower()

    def test_large_document_handling(self, s3_mock, s3_client_config):
        """Test handling of large documents.
        
        This test verifies that the storage service can handle large documents
        efficiently and correctly.
        """
        # Initialize the storage service with test configuration
        storage_service = StorageService(s3_client_config)
        
        # Create a large document (5MB)
        large_document_key = "documents/large-document.pdf"
        large_document_content = b"%PDF-1.5\n" + b"X" * (5 * 1024 * 1024) + b"\n%%EOF"
        
        # Upload the large document
        result = storage_service.upload_document(
            key=large_document_key,
            data=large_document_content,
            metadata={"size": "5MB"}
        )
        
        # Verify upload was successful
        assert result.success is True
        
        # Download the large document
        download_result = storage_service.download_document(key=large_document_key)
        
        # Verify download was successful
        assert download_result.success is True
        assert len(download_result.data) == len(large_document_content)
        assert download_result.data == large_document_content


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])