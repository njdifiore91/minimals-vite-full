# -*- coding: utf-8 -*-
"""Unit tests for the S3 storage utilities in the Document Service.

This module contains tests that verify the S3 connection management, document upload/download,
metadata management, and error handling functions work correctly. It also ensures that
AES-256 encryption is properly applied to stored documents.

These tests verify:
1. S3 connection management functions work correctly
2. Document upload with encryption verification functions properly
3. Document download and metadata management works as expected
4. Error handling for S3 operations is implemented correctly
5. Signed URL generation for secure access functions properly
"""

import os
import json
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY

import pytest
import boto3
from botocore.exceptions import ClientError
from moto import mock_s3

# Import the module to test
from document_service.src.utils import s3_utils
from document_service.src.config import s3_config


class TestS3Utils:
    """Test class for the Document Service S3 storage utilities."""

    def test_generate_document_key(self):
        """Test that document keys are generated correctly.
        
        This test verifies that the generate_document_key function creates unique keys
        with the correct format, including document type and optional file extension.
        """
        # Test with document type only
        key = s3_utils.generate_document_key('loan_application')
        assert key.startswith('documents/loan_application/')
        assert '-' in key  # Should contain timestamp and UUID separator
        
        # Test with document type and file extension
        key = s3_utils.generate_document_key('tax_return', '.pdf')
        assert key.startswith('documents/tax_return/')
        assert key.endswith('.pdf')
        
        # Test with document type and file extension without dot
        key = s3_utils.generate_document_key('bank_statement', 'pdf')
        assert key.startswith('documents/bank_statement/')
        assert key.endswith('.pdf')
        
        # Test uniqueness
        key1 = s3_utils.generate_document_key('invoice')
        key2 = s3_utils.generate_document_key('invoice')
        assert key1 != key2

    @mock_s3
    def test_upload_document(self, sample_document_file, sample_classification_metadata):
        """Test uploading a document to S3 with metadata and encryption.
        
        This test verifies that the upload_document function correctly uploads a document
        to S3 with the specified metadata and AES-256 encryption.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload the document
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            
            # Verify success and object key
            assert success is True
            assert object_key is not None
            assert object_key.startswith('documents/loan_application/')
            
            # Verify the document was uploaded with encryption
            response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            assert response['ServerSideEncryption'] == 'AES256'
            
            # Verify metadata was set correctly
            metadata = response['Metadata']
            assert metadata['document_type'] == 'loan_application'
            assert 'upload_timestamp' in metadata
            
            # Verify complex metadata was serialized to JSON
            assert 'extracted_fields' in metadata
            extracted_fields = json.loads(metadata['extracted_fields'])
            assert extracted_fields['applicant_name'] == 'John Doe'

    @mock_s3
    def test_upload_document_from_bytes(self, sample_document_bytes, sample_classification_metadata):
        """Test uploading a document from bytes to S3 with metadata and encryption.
        
        This test verifies that the upload_document_from_bytes function correctly uploads
        a document from bytes to S3 with the specified metadata and AES-256 encryption.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload the document
            success, object_key = s3_utils.upload_document_from_bytes(
                sample_document_bytes,
                'tax_return',
                'test_document.pdf',
                sample_classification_metadata
            )
            
            # Verify success and object key
            assert success is True
            assert object_key is not None
            assert object_key.startswith('documents/tax_return/')
            
            # Verify the document was uploaded with encryption
            response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            assert response['ServerSideEncryption'] == 'AES256'
            
            # Verify metadata was set correctly
            metadata = response['Metadata']
            assert metadata['document_type'] == 'tax_return'
            assert metadata['original_filename'] == 'test_document.pdf'
            assert 'upload_timestamp' in metadata
            
            # Verify complex metadata was serialized to JSON
            assert 'extracted_fields' in metadata
            extracted_fields = json.loads(metadata['extracted_fields'])
            assert extracted_fields['applicant_name'] == 'John Doe'
            
            # Verify content was uploaded correctly
            response = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            content = response['Body'].read()
            assert content == sample_document_bytes

    @mock_s3
    def test_download_document(self, sample_document_file, sample_classification_metadata):
        """Test downloading a document from S3 to a local file.
        
        This test verifies that the download_document function correctly downloads
        a document from S3 to a local file path.
        """
        # Set up test bucket and upload a document
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Create a temporary download path
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                download_path = temp_file.name
            
            # Download the document
            success = s3_utils.download_document(object_key, download_path)
            
            # Verify success
            assert success is True
            assert os.path.exists(download_path)
            
            # Verify file content
            with open(download_path, 'rb') as f:
                downloaded_content = f.read()
            with open(sample_document_file, 'rb') as f:
                original_content = f.read()
            assert downloaded_content == original_content
            
            # Clean up
            os.unlink(download_path)

    @mock_s3
    def test_download_document_to_bytes(self, sample_document_bytes, sample_classification_metadata):
        """Test downloading a document from S3 to bytes.
        
        This test verifies that the download_document_to_bytes function correctly downloads
        a document from S3 and returns it as bytes along with its metadata.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document_from_bytes(
                sample_document_bytes,
                'tax_return',
                'test_document.pdf',
                sample_classification_metadata
            )
            assert success is True
            
            # Download the document to bytes
            success, content, metadata = s3_utils.download_document_to_bytes(object_key)
            
            # Verify success, content, and metadata
            assert success is True
            assert content == sample_document_bytes
            assert metadata is not None
            assert metadata['document_type'] == 'tax_return'
            assert metadata['original_filename'] == 'test_document.pdf'

    @mock_s3
    def test_get_document_metadata(self, sample_document_file, sample_classification_metadata):
        """Test retrieving metadata for a document stored in S3.
        
        This test verifies that the get_document_metadata function correctly retrieves
        metadata for a document stored in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Get document metadata
            success, metadata = s3_utils.get_document_metadata(object_key)
            
            # Verify success and metadata
            assert success is True
            assert metadata is not None
            assert metadata['document_type'] == 'loan_application'
            assert 'upload_timestamp' in metadata
            assert 'content_type' in metadata
            assert 'content_length' in metadata
            assert 'last_modified' in metadata
            assert 'e_tag' in metadata
            assert metadata['server_side_encryption'] == 'AES256'
            
            # Verify complex metadata was deserialized from JSON
            assert 'extracted_fields' in metadata
            extracted_fields = json.loads(metadata['extracted_fields'])
            assert extracted_fields['applicant_name'] == 'John Doe'

    @mock_s3
    def test_update_document_metadata(self, sample_document_file, sample_classification_metadata):
        """Test updating metadata for a document stored in S3.
        
        This test verifies that the update_document_metadata function correctly updates
        metadata for a document stored in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Update document metadata
            new_metadata = {
                'document_type': 'loan_application',
                'classification_confidence': '0.98',
                'review_status': 'approved',
                'reviewer': 'John Smith',
                'review_date': datetime.now().isoformat()
            }
            success = s3_utils.update_document_metadata(object_key, new_metadata)
            
            # Verify success
            assert success is True
            
            # Get updated metadata
            success, metadata = s3_utils.get_document_metadata(object_key)
            assert success is True
            
            # Verify metadata was updated
            assert metadata['classification_confidence'] == '0.98'
            assert metadata['review_status'] == 'approved'
            assert metadata['reviewer'] == 'John Smith'
            assert 'review_date' in metadata

    @mock_s3
    def test_generate_presigned_url(self, sample_document_file, sample_classification_metadata):
        """Test generating a presigned URL for secure access to a document.
        
        This test verifies that the generate_presigned_url function correctly generates
        a presigned URL for secure access to a document stored in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Generate a presigned URL
            success, url = s3_utils.generate_presigned_url(object_key, expiration=3600)
            
            # Verify success and URL
            assert success is True
            assert url is not None
            assert url.startswith('https://') or url.startswith('http://')
            assert bucket_name in url
            assert object_key in url
            
            # Test with custom expiration and HTTP method
            success, url = s3_utils.generate_presigned_url(object_key, expiration=1800, http_method='PUT')
            assert success is True
            assert url is not None
            assert 'X-Amz-Expires=1800' in url or 'Expires=' in url

    @mock_s3
    def test_list_documents_by_type(self, sample_document_file, sample_classification_metadata):
        """Test listing documents of a specific type stored in S3.
        
        This test verifies that the list_documents_by_type function correctly lists
        documents of a specific type stored in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload multiple documents
            document_type = 'loan_application'
            for i in range(3):
                success, _ = s3_utils.upload_document(
                    sample_document_file,
                    document_type,
                    sample_classification_metadata
                )
                assert success is True
            
            # List documents by type
            success, documents = s3_utils.list_documents_by_type(document_type)
            
            # Verify success and documents
            assert success is True
            assert documents is not None
            assert len(documents) == 3
            
            # Verify document information
            for doc in documents:
                assert 'key' in doc
                assert doc['key'].startswith(f'documents/{document_type}/')
                assert 'size' in doc
                assert 'last_modified' in doc
                assert 'e_tag' in doc
                assert 'metadata' in doc

    @mock_s3
    def test_delete_document(self, sample_document_file, sample_classification_metadata):
        """Test deleting a document from S3.
        
        This test verifies that the delete_document function correctly deletes
        a document from S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Verify document exists
            assert s3_utils.check_document_exists(object_key) is True
            
            # Delete the document
            success = s3_utils.delete_document(object_key)
            
            # Verify success and document deletion
            assert success is True
            assert s3_utils.check_document_exists(object_key) is False

    @mock_s3
    def test_copy_document(self, sample_document_file, sample_classification_metadata):
        """Test copying a document within S3, optionally updating its metadata.
        
        This test verifies that the copy_document function correctly copies a document
        within S3, optionally updating its metadata.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, source_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Copy the document without changing metadata
            dest_key = 'documents/loan_application/copy_test.pdf'
            success = s3_utils.copy_document(source_key, dest_key)
            
            # Verify success and document copy
            assert success is True
            assert s3_utils.check_document_exists(dest_key) is True
            
            # Get metadata of copied document
            success, metadata = s3_utils.get_document_metadata(dest_key)
            assert success is True
            assert metadata['document_type'] == 'loan_application'
            
            # Copy the document with new metadata
            new_dest_key = 'documents/loan_application/copy_test_with_metadata.pdf'
            new_metadata = {
                'document_type': 'loan_application',
                'classification_confidence': '0.99',
                'review_status': 'approved',
                'reviewer': 'Jane Smith'
            }
            success = s3_utils.copy_document(source_key, new_dest_key, new_metadata)
            
            # Verify success and document copy with new metadata
            assert success is True
            assert s3_utils.check_document_exists(new_dest_key) is True
            
            # Get metadata of copied document with new metadata
            success, metadata = s3_utils.get_document_metadata(new_dest_key)
            assert success is True
            assert metadata['document_type'] == 'loan_application'
            assert metadata['classification_confidence'] == '0.99'
            assert metadata['review_status'] == 'approved'
            assert metadata['reviewer'] == 'Jane Smith'

    @mock_s3
    def test_check_document_exists(self, sample_document_file, sample_classification_metadata):
        """Test checking if a document exists in S3.
        
        This test verifies that the check_document_exists function correctly checks
        if a document exists in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            assert success is True
            
            # Check if document exists
            exists = s3_utils.check_document_exists(object_key)
            assert exists is True
            
            # Check if non-existent document exists
            non_existent_key = 'documents/loan_application/non_existent.pdf'
            exists = s3_utils.check_document_exists(non_existent_key)
            assert exists is False

    @mock_s3
    def test_get_document_classification(self, sample_document_file, sample_classification_metadata):
        """Test getting the classification type and confidence score for a document.
        
        This test verifies that the get_document_classification function correctly gets
        the classification type and confidence score for a document stored in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first with classification metadata
            metadata = sample_classification_metadata.copy()
            metadata['classification_confidence'] = '0.95'
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                metadata
            )
            assert success is True
            
            # Get document classification
            success, doc_type, confidence = s3_utils.get_document_classification(object_key)
            
            # Verify success, document type, and confidence
            assert success is True
            assert doc_type == 'loan_application'
            assert confidence == 0.95

    @mock_s3
    def test_add_classification_metadata(self, sample_document_file, sample_classification_metadata):
        """Test adding or updating classification metadata for a document.
        
        This test verifies that the add_classification_metadata function correctly adds
        or updates classification metadata for a document stored in S3.
        """
        # Set up test bucket
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'test-mca-documents'
        s3_client.create_bucket(Bucket=bucket_name)
        
        # Mock the get_bucket_name function to return our test bucket
        with patch('document_service.src.config.s3_config.get_bucket_name', return_value=bucket_name):
            # Upload a document first without classification metadata
            metadata = {}
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'unknown',
                metadata
            )
            assert success is True
            
            # Add classification metadata
            document_type = 'loan_application'
            confidence = 0.95
            additional_metadata = {
                'requires_review': 'false',
                'page_count': '3',
                'contains_signature': 'true'
            }
            success = s3_utils.add_classification_metadata(
                object_key,
                document_type,
                confidence,
                additional_metadata
            )
            
            # Verify success
            assert success is True
            
            # Get document classification
            success, doc_type, conf = s3_utils.get_document_classification(object_key)
            assert success is True
            assert doc_type == document_type
            assert conf == confidence
            
            # Get document metadata
            success, metadata = s3_utils.get_document_metadata(object_key)
            assert success is True
            assert metadata['document_type'] == document_type
            assert metadata['classification_confidence'] == str(confidence)
            assert 'classification_timestamp' in metadata
            assert metadata['requires_review'] == 'false'
            assert metadata['page_count'] == '3'
            assert metadata['contains_signature'] == 'true'

    def test_upload_document_error(self, sample_document_file, sample_classification_metadata, s3_client_error_factory):
        """Test error handling when uploading a document to S3.
        
        This test verifies that the upload_document function correctly handles errors
        when uploading a document to S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('AccessDenied', 'PutObject')
        with patch('document_service.src.config.s3_config.s3_client.upload_file', side_effect=error):
            # Attempt to upload the document
            success, object_key = s3_utils.upload_document(
                sample_document_file,
                'loan_application',
                sample_classification_metadata
            )
            
            # Verify failure
            assert success is False
            assert object_key is None

    def test_upload_document_from_bytes_error(self, sample_document_bytes, sample_classification_metadata, s3_client_error_factory):
        """Test error handling when uploading a document from bytes to S3.
        
        This test verifies that the upload_document_from_bytes function correctly handles errors
        when uploading a document from bytes to S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('AccessDenied', 'PutObject')
        with patch('document_service.src.config.s3_config.s3_client.put_object', side_effect=error):
            # Attempt to upload the document
            success, object_key = s3_utils.upload_document_from_bytes(
                sample_document_bytes,
                'tax_return',
                'test_document.pdf',
                sample_classification_metadata
            )
            
            # Verify failure
            assert success is False
            assert object_key is None

    def test_download_document_error(self, s3_client_error_factory):
        """Test error handling when downloading a document from S3.
        
        This test verifies that the download_document function correctly handles errors
        when downloading a document from S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('NoSuchKey', 'GetObject')
        with patch('document_service.src.config.s3_config.s3_client.download_file', side_effect=error):
            # Attempt to download the document
            success = s3_utils.download_document('non_existent_key', '/tmp/test.pdf')
            
            # Verify failure
            assert success is False

    def test_download_document_to_bytes_error(self, s3_client_error_factory):
        """Test error handling when downloading a document from S3 to bytes.
        
        This test verifies that the download_document_to_bytes function correctly handles errors
        when downloading a document from S3 to bytes.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('NoSuchKey', 'GetObject')
        with patch('document_service.src.config.s3_config.s3_client.get_object', side_effect=error):
            # Attempt to download the document
            success, content, metadata = s3_utils.download_document_to_bytes('non_existent_key')
            
            # Verify failure
            assert success is False
            assert content is None
            assert metadata is None

    def test_get_document_metadata_error(self, s3_client_error_factory):
        """Test error handling when retrieving metadata for a document stored in S3.
        
        This test verifies that the get_document_metadata function correctly handles errors
        when retrieving metadata for a document stored in S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('NoSuchKey', 'HeadObject')
        with patch('document_service.src.config.s3_config.s3_client.head_object', side_effect=error):
            # Attempt to get document metadata
            success, metadata = s3_utils.get_document_metadata('non_existent_key')
            
            # Verify failure
            assert success is False
            assert metadata is None

    def test_update_document_metadata_error(self, s3_client_error_factory):
        """Test error handling when updating metadata for a document stored in S3.
        
        This test verifies that the update_document_metadata function correctly handles errors
        when updating metadata for a document stored in S3.
        """
        # Mock the get_document_metadata function to return failure
        with patch('document_service.src.utils.s3_utils.get_document_metadata', return_value=(False, None)):
            # Attempt to update document metadata
            success = s3_utils.update_document_metadata('non_existent_key', {'test': 'value'})
            
            # Verify failure
            assert success is False

    def test_generate_presigned_url_error(self, s3_client_error_factory):
        """Test error handling when generating a presigned URL for secure access to a document.
        
        This test verifies that the generate_presigned_url function correctly handles errors
        when generating a presigned URL for secure access to a document stored in S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('InvalidRequest', 'GetObject')
        with patch('document_service.src.config.s3_config.s3_client.generate_presigned_url', side_effect=error):
            # Attempt to generate a presigned URL
            success, url = s3_utils.generate_presigned_url('non_existent_key')
            
            # Verify failure
            assert success is False
            assert url is None

    def test_list_documents_by_type_error(self, s3_client_error_factory):
        """Test error handling when listing documents of a specific type stored in S3.
        
        This test verifies that the list_documents_by_type function correctly handles errors
        when listing documents of a specific type stored in S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('AccessDenied', 'ListObjects')
        with patch('document_service.src.config.s3_config.s3_client.get_paginator', side_effect=error):
            # Attempt to list documents by type
            success, documents = s3_utils.list_documents_by_type('loan_application')
            
            # Verify failure
            assert success is False
            assert documents is None

    def test_delete_document_error(self, s3_client_error_factory):
        """Test error handling when deleting a document from S3.
        
        This test verifies that the delete_document function correctly handles errors
        when deleting a document from S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('AccessDenied', 'DeleteObject')
        with patch('document_service.src.config.s3_config.s3_client.delete_object', side_effect=error):
            # Attempt to delete the document
            success = s3_utils.delete_document('non_existent_key')
            
            # Verify failure
            assert success is False

    def test_copy_document_error(self, s3_client_error_factory):
        """Test error handling when copying a document within S3.
        
        This test verifies that the copy_document function correctly handles errors
        when copying a document within S3.
        """
        # Mock the S3 client to raise an error
        error = s3_client_error_factory('AccessDenied', 'CopyObject')
        with patch('document_service.src.config.s3_config.s3_client.copy_object', side_effect=error):
            # Attempt to copy the document
            success = s3_utils.copy_document('source_key', 'dest_key')
            
            # Verify failure
            assert success is False

    def test_check_document_exists_error(self, s3_client_error_factory):
        """Test error handling when checking if a document exists in S3.
        
        This test verifies that the check_document_exists function correctly handles errors
        when checking if a document exists in S3.
        """
        # Mock the S3 client to raise an error other than 404
        error = s3_client_error_factory('AccessDenied', 'HeadObject')
        with patch('document_service.src.config.s3_config.s3_client.head_object', side_effect=error):
            # Attempt to check if document exists
            exists = s3_utils.check_document_exists('test_key')
            
            # Verify failure
            assert exists is False

    def test_get_document_classification_error(self):
        """Test error handling when getting the classification type and confidence score for a document.
        
        This test verifies that the get_document_classification function correctly handles errors
        when getting the classification type and confidence score for a document stored in S3.
        """
        # Mock the get_document_metadata function to return failure
        with patch('document_service.src.utils.s3_utils.get_document_metadata', return_value=(False, None)):
            # Attempt to get document classification
            success, doc_type, confidence = s3_utils.get_document_classification('non_existent_key')
            
            # Verify failure
            assert success is False
            assert doc_type is None
            assert confidence is None

    def test_add_classification_metadata_error(self):
        """Test error handling when adding or updating classification metadata for a document.
        
        This test verifies that the add_classification_metadata function correctly handles errors
        when adding or updating classification metadata for a document stored in S3.
        """
        # Mock the get_document_metadata function to return failure
        with patch('document_service.src.utils.s3_utils.get_document_metadata', return_value=(False, None)):
            # Attempt to add classification metadata
            success = s3_utils.add_classification_metadata('non_existent_key', 'loan_application', 0.95)
            
            # Verify failure
            assert success is False