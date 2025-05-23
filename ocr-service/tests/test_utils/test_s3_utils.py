#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the s3_utils.py module.

This module contains tests for S3 connection management, document download and upload with encryption,
document metadata management, error handling for S3 operations, and signed URL generation to ensure
secure document storage and retrieval.
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

from src.utils import s3_utils
from src.types.errors import ServiceError


class TestS3ConnectionManagement:
    """Tests for S3 connection management functions."""

    def test_get_s3_client(self, aws_credentials):
        """Test creating an S3 client with default parameters."""
        # Test with default parameters
        s3_client = s3_utils.get_s3_client()
        assert s3_client is not None
        assert s3_client.__class__.__name__ == 'S3Client'

    def test_get_s3_client_with_params(self, aws_credentials):
        """Test creating an S3 client with custom parameters."""
        # Test with custom parameters
        s3_client = s3_utils.get_s3_client(
            region_name='us-west-2',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret'
        )
        assert s3_client is not None
        assert s3_client.__class__.__name__ == 'S3Client'

    def test_get_s3_client_error(self):
        """Test error handling when creating an S3 client."""
        # Test with invalid parameters that should raise an exception
        with patch('boto3.client', side_effect=Exception('Connection error')):
            with pytest.raises(Exception) as excinfo:
                s3_utils.get_s3_client()
            assert 'Connection error' in str(excinfo.value)

    def test_get_s3_resource(self, aws_credentials):
        """Test creating an S3 resource with default parameters."""
        # Test with default parameters
        s3_resource = s3_utils.get_s3_resource()
        assert s3_resource is not None
        assert s3_resource.__class__.__name__ == 'ServiceResource'

    def test_get_s3_resource_with_params(self, aws_credentials):
        """Test creating an S3 resource with custom parameters."""
        # Test with custom parameters
        s3_resource = s3_utils.get_s3_resource(
            region_name='us-west-2',
            endpoint_url='http://localhost:4566',
            aws_access_key_id='test-key',
            aws_secret_access_key='test-secret'
        )
        assert s3_resource is not None
        assert s3_resource.__class__.__name__ == 'ServiceResource'

    def test_get_s3_resource_error(self):
        """Test error handling when creating an S3 resource."""
        # Test with invalid parameters that should raise an exception
        with patch('boto3.resource', side_effect=Exception('Connection error')):
            with pytest.raises(Exception) as excinfo:
                s3_utils.get_s3_resource()
            assert 'Connection error' in str(excinfo.value)


class TestDocumentDownloadUpload:
    """Tests for document download and upload functions."""

    def test_download_document(self, s3_mock, s3_bucket_with_files):
        """Test downloading a document from S3."""
        # Test downloading an existing document
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        
        content, metadata = s3_utils.download_document(bucket_name, key, s3_mock)
        
        assert content is not None
        assert isinstance(content, bytes)
        assert metadata is not None
        assert 'ContentType' in metadata
        assert 'ContentLength' in metadata

    def test_download_document_not_found(self, s3_mock):
        """Test error handling when downloading a non-existent document."""
        # Test with non-existent document
        bucket_name = 'mca-documents-testing'
        key = 'non-existent-document.pdf'
        
        # Create a ClientError response similar to what boto3 would return
        error_response = {
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'The specified key does not exist.'
            }
        }
        client_error = ClientError(error_response, 'GetObject')
        
        # Mock the get_object method to raise the ClientError
        with patch.object(s3_mock, 'get_object', side_effect=client_error):
            with pytest.raises(ClientError) as excinfo:
                s3_utils.download_document(bucket_name, key, s3_mock)
            assert 'NoSuchKey' in str(excinfo.value)

    def test_upload_document(self, s3_mock):
        """Test uploading a document to S3 with encryption."""
        bucket_name = 'mca-documents-testing'
        key = 'test-upload.pdf'
        document_content = b'Test document content'
        content_type = 'application/pdf'
        metadata = {'document-type': 'test'}
        
        response = s3_utils.upload_document(
            bucket_name, key, document_content,
            content_type=content_type,
            metadata=metadata,
            s3_client=s3_mock
        )
        
        assert response is not None
        
        # Verify the document was uploaded with encryption
        obj = s3_mock.get_object(Bucket=bucket_name, Key=key)
        assert obj['ServerSideEncryption'] == 'AES256'
        assert obj['ContentType'] == content_type
        assert obj['Metadata'] == metadata

    def test_upload_document_error(self, s3_mock):
        """Test error handling when uploading a document."""
        bucket_name = 'mca-documents-testing'
        key = 'test-upload-error.pdf'
        document_content = b'Test document content'
        
        # Create a ClientError response
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied'
            }
        }
        client_error = ClientError(error_response, 'PutObject')
        
        # Mock the put_object method to raise the ClientError
        with patch.object(s3_mock, 'put_object', side_effect=client_error):
            with pytest.raises(ClientError) as excinfo:
                s3_utils.upload_document(bucket_name, key, document_content, s3_client=s3_mock)
            assert 'AccessDenied' in str(excinfo.value)

    def test_upload_extracted_data(self, s3_mock):
        """Test uploading extracted data to S3."""
        bucket_name = 'mca-documents-testing'
        key = 'extracted/test-data.json'
        original_document_key = 'documents/pdfs/sample_document.pdf'
        extracted_data = {
            'fields': {
                'invoice_number': 'INV-001',
                'date': '2025-05-23',
                'total_amount': '1250.00'
            }
        }
        confidence_scores = {
            'invoice_number': 0.95,
            'date': 0.92,
            'total_amount': 0.88
        }
        document_type = 'invoice'
        
        response = s3_utils.upload_extracted_data(
            bucket_name, key, extracted_data,
            original_document_key=original_document_key,
            confidence_scores=confidence_scores,
            document_type=document_type,
            s3_client=s3_mock
        )
        
        assert response is not None
        
        # Verify the extracted data was uploaded with correct metadata
        obj = s3_mock.get_object(Bucket=bucket_name, Key=key)
        assert obj['ServerSideEncryption'] == 'AES256'
        assert obj['ContentType'] == 'application/json'
        assert obj['Metadata']['original-document'] == original_document_key
        assert obj['Metadata']['document-type'] == document_type
        
        # Verify the content includes confidence scores and metadata
        content = json.loads(obj['Body'].read().decode('utf-8'))
        assert 'confidence_scores' in content
        assert 'metadata' in content
        assert content['metadata']['original_document'] == original_document_key
        assert content['metadata']['document_type'] == document_type


class TestDocumentMetadataManagement:
    """Tests for document metadata management functions."""

    def test_update_document_metadata(self, s3_mock, s3_bucket_with_files):
        """Test updating metadata for an existing document."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        new_metadata = {
            'document-type': 'invoice',
            'processed': 'true',
            'confidence': '0.95'
        }
        
        response = s3_utils.update_document_metadata(bucket_name, key, new_metadata, s3_mock)
        assert response is not None
        
        # Verify the metadata was updated
        obj = s3_mock.get_object(Bucket=bucket_name, Key=key)
        assert obj['Metadata'] == new_metadata
        assert obj['ServerSideEncryption'] == 'AES256'  # Encryption should be maintained

    def test_update_document_metadata_not_found(self, s3_mock):
        """Test error handling when updating metadata for a non-existent document."""
        bucket_name = 'mca-documents-testing'
        key = 'non-existent-document.pdf'
        new_metadata = {'document-type': 'invoice'}
        
        # Create a ClientError response
        error_response = {
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'The specified key does not exist.'
            }
        }
        client_error = ClientError(error_response, 'CopyObject')
        
        # Mock the copy_object method to raise the ClientError
        with patch.object(s3_mock, 'copy_object', side_effect=client_error):
            with pytest.raises(ClientError) as excinfo:
                s3_utils.update_document_metadata(bucket_name, key, new_metadata, s3_mock)
            assert 'NoSuchKey' in str(excinfo.value)

    def test_get_document_metadata(self, s3_mock, s3_bucket_with_files):
        """Test getting metadata for a document without downloading content."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        
        metadata = s3_utils.get_document_metadata(bucket_name, key, s3_mock)
        assert metadata is not None
        assert 'ContentType' in metadata
        assert 'ContentLength' in metadata
        assert 'LastModified' in metadata
        assert 'Metadata' in metadata

    def test_get_document_metadata_not_found(self, s3_mock):
        """Test error handling when getting metadata for a non-existent document."""
        bucket_name = 'mca-documents-testing'
        key = 'non-existent-document.pdf'
        
        # Create a ClientError response
        error_response = {
            'Error': {
                'Code': 'NoSuchKey',
                'Message': 'The specified key does not exist.'
            }
        }
        client_error = ClientError(error_response, 'HeadObject')
        
        # Mock the head_object method to raise the ClientError
        with patch.object(s3_mock, 'head_object', side_effect=client_error):
            with pytest.raises(ClientError) as excinfo:
                s3_utils.get_document_metadata(bucket_name, key, s3_mock)
            assert 'NoSuchKey' in str(excinfo.value)

    def test_check_document_exists(self, s3_mock, s3_bucket_with_files):
        """Test checking if a document exists in S3 storage."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        
        # Test with existing document
        exists = s3_utils.check_document_exists(bucket_name, key, s3_mock)
        assert exists is True
        
        # Test with non-existent document
        non_existent_key = 'non-existent-document.pdf'
        # Create a ClientError response
        error_response = {
            'Error': {
                'Code': '404',
                'Message': 'Not Found'
            }
        }
        client_error = ClientError(error_response, 'HeadObject')
        
        # Mock the head_object method to raise the ClientError
        with patch.object(s3_mock, 'head_object', side_effect=client_error):
            exists = s3_utils.check_document_exists(bucket_name, non_existent_key, s3_mock)
            assert exists is False

    def test_is_document_encrypted(self, s3_mock, s3_bucket_with_files):
        """Test checking if a document is encrypted with AES-256."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        
        # Upload a document with encryption
        s3_mock.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=b'Test content',
            ServerSideEncryption='AES256'
        )
        
        # Test with encrypted document
        is_encrypted = s3_utils.is_document_encrypted(bucket_name, key, s3_mock)
        assert is_encrypted is True
        
        # Upload a document without encryption
        unencrypted_key = 'unencrypted-document.pdf'
        s3_mock.put_object(
            Bucket=bucket_name,
            Key=unencrypted_key,
            Body=b'Unencrypted content'
        )
        
        # Test with unencrypted document
        is_encrypted = s3_utils.is_document_encrypted(bucket_name, unencrypted_key, s3_mock)
        assert is_encrypted is False


class TestSecureAccess:
    """Tests for secure access functions."""

    def test_generate_presigned_url(self, s3_mock, s3_bucket_with_files):
        """Test generating a presigned URL for secure access to a document."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        expiration = 3600  # 1 hour
        
        # Mock the generate_presigned_url method
        s3_mock.generate_presigned_url = MagicMock(return_value='https://example.com/presigned-url')
        
        url = s3_utils.generate_presigned_url(bucket_name, key, expiration, s3_mock)
        assert url is not None
        assert url == 'https://example.com/presigned-url'
        
        # Verify the method was called with correct parameters
        s3_mock.generate_presigned_url.assert_called_once_with(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )

    def test_generate_presigned_url_error(self, s3_mock):
        """Test error handling when generating a presigned URL."""
        bucket_name = 'mca-documents-testing'
        key = 'documents/pdfs/sample_document.pdf'
        
        # Mock the generate_presigned_url method to raise an exception
        s3_mock.generate_presigned_url = MagicMock(side_effect=ClientError(
            {
                'Error': {
                    'Code': 'InvalidRequest',
                    'Message': 'Invalid request'
                }
            },
            'GeneratePresignedUrl'
        ))
        
        with pytest.raises(ClientError) as excinfo:
            s3_utils.generate_presigned_url(bucket_name, key, 3600, s3_mock)
        assert 'InvalidRequest' in str(excinfo.value)

    def test_generate_presigned_post(self, s3_mock):
        """Test generating a presigned POST request for uploading a document."""
        bucket_name = 'mca-documents-testing'
        key = 'documents/pdfs/new-document.pdf'
        fields = {'Content-Type': 'application/pdf'}
        conditions = [{'Content-Type': 'application/pdf'}]
        expiration = 3600  # 1 hour
        
        # Mock the generate_presigned_post method
        s3_mock.generate_presigned_post = MagicMock(return_value={
            'url': 'https://example.com/bucket',
            'fields': {
                'key': key,
                'AWSAccessKeyId': 'test-key',
                'policy': 'test-policy',
                'signature': 'test-signature',
                'Content-Type': 'application/pdf',
                'ServerSideEncryption': 'AES256'
            }
        })
        
        post_data = s3_utils.generate_presigned_post(
            bucket_name, key, fields, conditions, expiration, s3_mock
        )
        assert post_data is not None
        assert 'url' in post_data
        assert 'fields' in post_data
        assert post_data['fields']['ServerSideEncryption'] == 'AES256'
        
        # Verify the method was called with correct parameters
        s3_mock.generate_presigned_post.assert_called_once()

    def test_get_document_url(self, s3_mock):
        """Test the convenience function for generating a presigned URL."""
        bucket_name = 'mca-documents-testing'
        key = 'documents/pdfs/sample_document.pdf'
        expiration = 3600  # 1 hour
        
        # Mock the generate_presigned_url method
        s3_mock.generate_presigned_url = MagicMock(return_value='https://example.com/presigned-url')
        
        # Test that get_document_url calls generate_presigned_url with the same parameters
        with patch('src.utils.s3_utils.generate_presigned_url') as mock_generate_url:
            mock_generate_url.return_value = 'https://example.com/presigned-url'
            url = s3_utils.get_document_url(bucket_name, key, expiration, s3_mock)
            assert url == 'https://example.com/presigned-url'
            mock_generate_url.assert_called_once_with(bucket_name, key, expiration, s3_mock)


class TestErrorHandling:
    """Tests for error handling in S3 operations."""

    def test_s3_client_connection_error(self):
        """Test handling of connection errors when creating an S3 client."""
        with patch('boto3.client', side_effect=Exception('Connection error')):
            with pytest.raises(Exception) as excinfo:
                s3_utils.get_s3_client()
            assert 'Connection error' in str(excinfo.value)

    def test_download_document_error(self, s3_mock):
        """Test handling of errors when downloading a document."""
        bucket_name = 'mca-documents-testing'
        key = 'documents/pdfs/sample_document.pdf'
        
        # Test with different error types
        error_codes = ['NoSuchKey', 'AccessDenied', 'InvalidObjectState']
        
        for code in error_codes:
            # Create a ClientError response
            error_response = {
                'Error': {
                    'Code': code,
                    'Message': f'Error: {code}'
                }
            }
            client_error = ClientError(error_response, 'GetObject')
            
            # Mock the get_object method to raise the ClientError
            with patch.object(s3_mock, 'get_object', side_effect=client_error):
                with pytest.raises(ClientError) as excinfo:
                    s3_utils.download_document(bucket_name, key, s3_mock)
                assert code in str(excinfo.value)

    def test_upload_document_error(self, s3_mock):
        """Test handling of errors when uploading a document."""
        bucket_name = 'mca-documents-testing'
        key = 'documents/pdfs/sample_document.pdf'
        document_content = b'Test document content'
        
        # Test with different error types
        error_codes = ['AccessDenied', 'InvalidBucketName', 'NoSuchBucket']
        
        for code in error_codes:
            # Create a ClientError response
            error_response = {
                'Error': {
                    'Code': code,
                    'Message': f'Error: {code}'
                }
            }
            client_error = ClientError(error_response, 'PutObject')
            
            # Mock the put_object method to raise the ClientError
            with patch.object(s3_mock, 'put_object', side_effect=client_error):
                with pytest.raises(ClientError) as excinfo:
                    s3_utils.upload_document(bucket_name, key, document_content, s3_client=s3_mock)
                assert code in str(excinfo.value)

    def test_parse_s3_uri_error(self):
        """Test error handling when parsing an invalid S3 URI."""
        # Test with invalid URI format
        invalid_uris = [
            'http://example.com',  # Not an S3 URI
            's3://',              # Missing bucket and key
            's3://bucket',        # Missing key
            's3:///key'           # Missing bucket
        ]
        
        for uri in invalid_uris:
            with pytest.raises(ValueError) as excinfo:
                s3_utils.parse_s3_uri(uri)
            assert 'Invalid S3 URI' in str(excinfo.value)

    def test_ensure_bucket_encryption_error(self, s3_mock):
        """Test error handling when ensuring bucket encryption."""
        bucket_name = 'mca-documents-testing'
        
        # Mock the put_bucket_encryption method to raise an exception
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied'
            }
        }
        client_error = ClientError(error_response, 'PutBucketEncryption')
        
        with patch.object(s3_mock, 'put_bucket_encryption', side_effect=client_error):
            with patch('src.utils.s3_utils.get_bucket_encryption_status', return_value={}):
                result = s3_utils.ensure_bucket_encryption(bucket_name, s3_mock)
                assert result is False


class TestUtilityFunctions:
    """Tests for utility functions in the s3_utils module."""

    def test_parse_s3_uri(self):
        """Test parsing an S3 URI into bucket and key components."""
        # Test with valid URI
        uri = 's3://mca-documents-testing/documents/pdfs/sample_document.pdf'
        bucket, key = s3_utils.parse_s3_uri(uri)
        assert bucket == 'mca-documents-testing'
        assert key == 'documents/pdfs/sample_document.pdf'
        
        # Test with URI containing special characters
        uri = 's3://mca-documents-testing/documents/pdfs/sample document with spaces.pdf'
        bucket, key = s3_utils.parse_s3_uri(uri)
        assert bucket == 'mca-documents-testing'
        assert key == 'documents/pdfs/sample document with spaces.pdf'

    def test_create_document_key(self):
        """Test creating a standardized S3 key for a document."""
        document_type = 'invoice'
        document_id = 'doc-12345'
        extension = 'pdf'
        
        key = s3_utils.create_document_key(document_type, document_id, extension)
        assert document_type in key
        assert document_id in key
        assert key.endswith('.pdf')
        
        # Test with leading dot in extension
        key = s3_utils.create_document_key(document_type, document_id, '.pdf')
        assert key.endswith('.pdf')
        assert not key.endswith('..pdf')  # Should not have double dots

    def test_create_extracted_data_key(self):
        """Test creating a standardized S3 key for extracted data."""
        document_key = 'invoice/2025/05/23/doc-12345.pdf'
        
        extracted_key = s3_utils.create_extracted_data_key(document_key)
        assert extracted_key == 'invoice/2025/05/23/doc-12345/extracted_data.json'
        
        # Test with key that doesn't have an extension
        document_key = 'invoice/2025/05/23/doc-12345'
        extracted_key = s3_utils.create_extracted_data_key(document_key)
        assert extracted_key == 'invoice/2025/05/23/doc-12345/extracted_data.json'

    def test_get_document_from_uri(self, s3_mock, s3_bucket_with_files):
        """Test downloading a document using an S3 URI."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        uri = f's3://{bucket_name}/{key}'
        
        # Mock the download_document function
        with patch('src.utils.s3_utils.download_document') as mock_download:
            mock_download.return_value = (b'test content', {'ContentType': 'application/pdf'})
            content, metadata = s3_utils.get_document_from_uri(uri, s3_mock)
            assert content == b'test content'
            assert metadata['ContentType'] == 'application/pdf'
            mock_download.assert_called_once_with(bucket_name, key, s3_mock)

    def test_upload_document_with_uri(self, s3_mock):
        """Test uploading a document using an S3 URI."""
        bucket_name = 'mca-documents-testing'
        key = 'documents/pdfs/sample_document.pdf'
        uri = f's3://{bucket_name}/{key}'
        document_content = b'Test document content'
        
        # Mock the upload_document function
        with patch('src.utils.s3_utils.upload_document') as mock_upload:
            mock_upload.return_value = {'ETag': '"test-etag"'}
            response = s3_utils.upload_document_with_uri(
                uri, document_content, content_type='application/pdf', s3_client=s3_mock
            )
            assert response['ETag'] == '"test-etag"'
            mock_upload.assert_called_once()

    def test_batch_download_documents(self, s3_mock, s3_bucket_with_files):
        """Test downloading multiple documents in parallel."""
        bucket_name = s3_bucket_with_files.name
        keys = [
            'documents/pdfs/sample_document.pdf',
            'documents/images/sample_text.png',
            'results/sample_data.json'
        ]
        
        # Mock the download_document function to return different content for each key
        def mock_download_side_effect(bucket, key, client):
            content_map = {
                'documents/pdfs/sample_document.pdf': b'pdf content',
                'documents/images/sample_text.png': b'png content',
                'results/sample_data.json': b'{"test": true}'
            }
            metadata_map = {
                'documents/pdfs/sample_document.pdf': {'ContentType': 'application/pdf'},
                'documents/images/sample_text.png': {'ContentType': 'image/png'},
                'results/sample_data.json': {'ContentType': 'application/json'}
            }
            return content_map[key], metadata_map[key]
        
        with patch('src.utils.s3_utils.download_document', side_effect=mock_download_side_effect):
            results = s3_utils.batch_download_documents(bucket_name, keys, s3_mock)
            assert len(results) == 3
            assert results['documents/pdfs/sample_document.pdf'][0] == b'pdf content'
            assert results['documents/images/sample_text.png'][0] == b'png content'
            assert results['results/sample_data.json'][0] == b'{"test": true}'


class TestBucketOperations:
    """Tests for bucket-level operations."""

    def test_get_bucket_encryption_status(self, s3_mock):
        """Test getting the encryption status of an S3 bucket."""
        bucket_name = 'mca-documents-testing'
        
        # Mock the get_bucket_encryption method to return encryption configuration
        encryption_config = {
            'ServerSideEncryptionConfiguration': {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        }
        s3_mock.get_bucket_encryption = MagicMock(return_value=encryption_config)
        
        status = s3_utils.get_bucket_encryption_status(bucket_name, s3_mock)
        assert status == encryption_config.get('ServerSideEncryptionConfiguration')
        s3_mock.get_bucket_encryption.assert_called_once_with(Bucket=bucket_name)
        
        # Test with no encryption configuration
        error_response = {
            'Error': {
                'Code': 'ServerSideEncryptionConfigurationNotFoundError',
                'Message': 'The server side encryption configuration was not found'
            }
        }
        client_error = ClientError(error_response, 'GetBucketEncryption')
        s3_mock.get_bucket_encryption = MagicMock(side_effect=client_error)
        
        status = s3_utils.get_bucket_encryption_status(bucket_name, s3_mock)
        assert status == {}
        
        # Test with other error
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied'
            }
        }
        client_error = ClientError(error_response, 'GetBucketEncryption')
        s3_mock.get_bucket_encryption = MagicMock(side_effect=client_error)
        
        with pytest.raises(ClientError) as excinfo:
            s3_utils.get_bucket_encryption_status(bucket_name, s3_mock)
        assert 'AccessDenied' in str(excinfo.value)

    def test_ensure_bucket_encryption(self, s3_mock):
        """Test ensuring that a bucket has AES-256 encryption enabled."""
        bucket_name = 'mca-documents-testing'
        
        # Test with encryption already configured
        with patch('src.utils.s3_utils.get_bucket_encryption_status') as mock_get_status:
            mock_get_status.return_value = {'Rules': [{'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}}]}
            result = s3_utils.ensure_bucket_encryption(bucket_name, s3_mock)
            assert result is True
            s3_mock.put_bucket_encryption.assert_not_called()
        
        # Test with no encryption configured
        with patch('src.utils.s3_utils.get_bucket_encryption_status') as mock_get_status:
            mock_get_status.return_value = {}
            result = s3_utils.ensure_bucket_encryption(bucket_name, s3_mock)
            assert result is True
            s3_mock.put_bucket_encryption.assert_called_once()
            # Verify the encryption configuration
            call_args = s3_mock.put_bucket_encryption.call_args[1]
            assert call_args['Bucket'] == bucket_name
            assert 'ServerSideEncryptionConfiguration' in call_args
            assert call_args['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm'] == 'AES256'

    def test_list_documents(self, s3_mock, s3_bucket_with_files):
        """Test listing documents in an S3 bucket with a given prefix."""
        bucket_name = s3_bucket_with_files.name
        prefix = 'documents/pdfs/'
        
        # Mock the list_objects_v2 method
        s3_mock.list_objects_v2 = MagicMock(return_value={
            'Contents': [
                {
                    'Key': 'documents/pdfs/sample_document.pdf',
                    'Size': 1024,
                    'LastModified': datetime(2025, 5, 23, 10, 15, 30),
                    'ETag': '"test-etag"',
                    'StorageClass': 'STANDARD'
                },
                {
                    'Key': 'documents/pdfs/another_document.pdf',
                    'Size': 2048,
                    'LastModified': datetime(2025, 5, 23, 11, 30, 45),
                    'ETag': '"another-etag"',
                    'StorageClass': 'STANDARD'
                }
            ]
        })
        
        documents = s3_utils.list_documents(bucket_name, prefix, s3_client=s3_mock)
        assert len(documents) == 2
        assert documents[0]['key'] == 'documents/pdfs/sample_document.pdf'
        assert documents[0]['size'] == 1024
        assert documents[1]['key'] == 'documents/pdfs/another_document.pdf'
        assert documents[1]['size'] == 2048
        
        # Verify the method was called with correct parameters
        s3_mock.list_objects_v2.assert_called_once_with(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=1000
        )
        
        # Test with empty result
        s3_mock.list_objects_v2 = MagicMock(return_value={})
        documents = s3_utils.list_documents(bucket_name, prefix, s3_client=s3_mock)
        assert len(documents) == 0

    def test_delete_document(self, s3_mock, s3_bucket_with_files):
        """Test deleting a document from S3 storage."""
        bucket_name = s3_bucket_with_files.name
        key = 'documents/pdfs/sample_document.pdf'
        
        # Mock the delete_object method
        s3_mock.delete_object = MagicMock(return_value={'DeleteMarker': True})
        
        response = s3_utils.delete_document(bucket_name, key, s3_mock)
        assert response is not None
        assert response.get('DeleteMarker') is True
        
        # Verify the method was called with correct parameters
        s3_mock.delete_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=key
        )
        
        # Test with error
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied'
            }
        }
        client_error = ClientError(error_response, 'DeleteObject')
        s3_mock.delete_object = MagicMock(side_effect=client_error)
        
        with pytest.raises(ClientError) as excinfo:
            s3_utils.delete_document(bucket_name, key, s3_mock)
        assert 'AccessDenied' in str(excinfo.value)

    def test_copy_document(self, s3_mock, s3_bucket_with_files):
        """Test copying a document from one location to another in S3 storage."""
        source_bucket = s3_bucket_with_files.name
        source_key = 'documents/pdfs/sample_document.pdf'
        dest_bucket = 'mca-documents-testing-dest'
        dest_key = 'documents/pdfs/copied_document.pdf'
        metadata = {'document-type': 'invoice'}
        
        # Mock the copy_object method
        s3_mock.copy_object = MagicMock(return_value={'CopyObjectResult': {'ETag': '"test-etag"'}})
        
        response = s3_utils.copy_document(
            source_bucket, source_key,
            dest_bucket, dest_key,
            metadata=metadata,
            s3_client=s3_mock
        )
        assert response is not None
        assert 'CopyObjectResult' in response
        
        # Verify the method was called with correct parameters
        s3_mock.copy_object.assert_called_once()
        call_args = s3_mock.copy_object.call_args[1]
        assert call_args['CopySource'] == {'Bucket': source_bucket, 'Key': source_key}
        assert call_args['Bucket'] == dest_bucket
        assert call_args['Key'] == dest_key
        assert call_args['ServerSideEncryption'] == 'AES256'
        assert call_args['Metadata'] == metadata
        assert call_args['MetadataDirective'] == 'REPLACE'
        
        # Test without metadata
        s3_mock.copy_object.reset_mock()
        response = s3_utils.copy_document(
            source_bucket, source_key,
            dest_bucket, dest_key,
            s3_client=s3_mock
        )
        assert response is not None
        s3_mock.copy_object.assert_called_once()
        call_args = s3_mock.copy_object.call_args[1]
        assert 'Metadata' not in call_args
        assert 'MetadataDirective' not in call_args