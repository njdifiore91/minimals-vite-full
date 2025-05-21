#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for S3 storage utilities in the Document Service.

This module contains tests for the S3 connection management, document upload/download,
metadata management, and error handling functions in the s3_utils module.

All tests use mocking to avoid making actual S3 calls during testing.
"""

import os
import io
import json
import pytest
import datetime
from unittest.mock import MagicMock, patch, call, ANY
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Dict, Any

# Import the module to test
from document_service.utils import s3_utils


# ============================================================================
# Test Connection Management Functions
# ============================================================================

class TestConnectionManagement:
    """Tests for S3 connection management functions."""

    def test_get_s3_client(self):
        """Test creating an S3 client with custom parameters."""
        with patch('boto3.client') as mock_boto3_client:
            # Set up the mock
            mock_client = MagicMock()
            mock_boto3_client.return_value = mock_client
            
            # Call the function
            result = s3_utils.get_s3_client(
                region_name='us-west-2',
                endpoint_url='https://custom-endpoint.com',
                aws_access_key_id='test-key',
                aws_secret_access_key='test-secret'
            )
            
            # Verify the result
            assert result == mock_client
            
            # Verify boto3.client was called with the correct parameters
            mock_boto3_client.assert_called_once_with(
                's3',
                region_name='us-west-2',
                endpoint_url='https://custom-endpoint.com',
                aws_access_key_id='test-key',
                aws_secret_access_key='test-secret',
                config=ANY
            )
    
    def test_get_s3_client_with_default_config(self):
        """Test creating an S3 client with default configuration."""
        with patch('boto3.client') as mock_boto3_client:
            # Set up the mock
            mock_client = MagicMock()
            mock_boto3_client.return_value = mock_client
            
            # Call the function
            result = s3_utils.get_s3_client()
            
            # Verify the result
            assert result == mock_client
            
            # Verify boto3.client was called with the default configuration
            mock_boto3_client.assert_called_once_with(
                's3',
                region_name=None,
                endpoint_url=None,
                aws_access_key_id=None,
                aws_secret_access_key=None,
                config=ANY
            )
    
    def test_get_s3_client_error_handling(self):
        """Test error handling when creating an S3 client fails."""
        with patch('boto3.client') as mock_boto3_client:
            # Set up the mock to raise an exception
            mock_boto3_client.side_effect = Exception("Connection error")
            
            # Call the function and verify it raises the exception
            with pytest.raises(Exception) as excinfo:
                s3_utils.get_s3_client()
            
            # Verify the exception message
            assert "Connection error" in str(excinfo.value)
    
    def test_get_default_s3_client(self):
        """Test getting a default S3 client using environment variables."""
        with patch('document_service.utils.s3_utils.get_s3_client') as mock_get_s3_client:
            # Set up the mock
            mock_client = MagicMock()
            mock_get_s3_client.return_value = mock_client
            
            # Set environment variables for testing
            with patch.object(s3_utils, 'S3_REGION_NAME', 'us-east-1'), \
                 patch.object(s3_utils, 'S3_ENDPOINT_URL', 'http://localhost:9000'), \
                 patch.object(s3_utils, 'S3_ACCESS_KEY_ID', 'test-key'), \
                 patch.object(s3_utils, 'S3_SECRET_ACCESS_KEY', 'test-secret'):
                
                # Call the function
                result = s3_utils.get_default_s3_client()
                
                # Verify the result
                assert result == mock_client
                
                # Verify get_s3_client was called with the correct parameters
                mock_get_s3_client.assert_called_once_with(
                    region_name='us-east-1',
                    endpoint_url='http://localhost:9000',
                    aws_access_key_id='test-key',
                    aws_secret_access_key='test-secret'
                )


# ============================================================================
# Test Document Upload Functions
# ============================================================================

class TestDocumentUpload:
    """Tests for document upload functions."""

    def test_upload_document(self, mock_s3_client):
        """Test uploading a document with AES-256 encryption."""
        # Set up the mock
        mock_s3_client.put_object.return_value = {'ETag': '"123456789"'}
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        file_obj = io.BytesIO(b'test content')
        metadata = {'original_filename': 'test.pdf'}
        content_type = 'application/pdf'
        document_classification = 'application_form'
        classification_confidence = 0.95
        
        # Call the function
        result = s3_utils.upload_document(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key,
            file_obj=file_obj,
            metadata=metadata,
            content_type=content_type,
            document_classification=document_classification,
            classification_confidence=classification_confidence
        )
        
        # Verify the result
        assert result == {'ETag': '"123456789"'}
        
        # Verify put_object was called with the correct parameters
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_obj,
            ServerSideEncryption='AES256',  # Verify AES-256 encryption is used
            Metadata={
                'original_filename': 'test.pdf',
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            },
            ContentType='application/pdf'
        )
    
    def test_upload_document_without_optional_params(self, mock_s3_client):
        """Test uploading a document without optional parameters."""
        # Set up the mock
        mock_s3_client.put_object.return_value = {'ETag': '"123456789"'}
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        file_obj = io.BytesIO(b'test content')
        
        # Call the function
        result = s3_utils.upload_document(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key,
            file_obj=file_obj
        )
        
        # Verify the result
        assert result == {'ETag': '"123456789"'}
        
        # Verify put_object was called with the correct parameters
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_obj,
            ServerSideEncryption='AES256',  # Verify AES-256 encryption is still used
            Metadata={}
        )
    
    def test_upload_document_error_handling(self, mock_s3_client):
        """Test error handling when uploading a document fails."""
        # Set up the mock to raise a ClientError
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        file_obj = io.BytesIO(b'test content')
        
        # Call the function and verify it raises the exception
        with pytest.raises(ClientError) as excinfo:
            s3_utils.upload_document(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key,
                file_obj=file_obj
            )
        
        # Verify the exception details
        assert 'AccessDenied' in str(excinfo.value)
        assert 'Access Denied' in str(excinfo.value)
    
    def test_upload_document_with_transfer_manager(self, mock_s3_client, sample_document_path):
        """Test uploading a large document using the transfer manager."""
        # Set up the mocks
        mock_s3_resource = MagicMock()
        mock_s3_client.meta.region_name = 'us-east-1'
        mock_s3_client.meta.endpoint_url = 'http://localhost:9000'
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'Metadata': {'document-classification': 'application_form'}
        }
        
        with patch('boto3.resource') as mock_boto3_resource:
            # Set up the resource mock
            mock_boto3_resource.return_value = mock_s3_resource
            
            # Test data
            bucket_name = 'test-bucket'
            object_key = 'test-document.pdf'
            file_path = str(sample_document_path)
            metadata = {'original_filename': 'test.pdf'}
            content_type = 'application/pdf'
            document_classification = 'application_form'
            classification_confidence = 0.95
            
            # Call the function
            result = s3_utils.upload_document_with_transfer_manager(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key,
                file_path=file_path,
                metadata=metadata,
                content_type=content_type,
                document_classification=document_classification,
                classification_confidence=classification_confidence
            )
            
            # Verify the result
            assert result == {
                'ContentType': 'application/pdf',
                'ContentLength': 1024,
                'Metadata': {'document-classification': 'application_form'}
            }
            
            # Verify boto3.resource was called with the correct parameters
            mock_boto3_resource.assert_called_once_with(
                's3',
                region_name='us-east-1',
                endpoint_url='http://localhost:9000'
            )
            
            # Verify upload_file was called with the correct parameters
            mock_s3_resource.meta.client.upload_file.assert_called_once_with(
                Filename=file_path,
                Bucket=bucket_name,
                Key=object_key,
                ExtraArgs={
                    'ServerSideEncryption': 'AES256',  # Verify AES-256 encryption is used
                    'Metadata': {
                        'original_filename': 'test.pdf',
                        'document-classification': 'application_form',
                        'classification-confidence': '0.95'
                    },
                    'ContentType': 'application/pdf'
                },
                Config=ANY
            )
            
            # Verify head_object was called to get the metadata
            mock_s3_client.head_object.assert_called_once_with(
                Bucket=bucket_name,
                Key=object_key
            )


# ============================================================================
# Test Document Download Functions
# ============================================================================

class TestDocumentDownload:
    """Tests for document download functions."""

    def test_download_document(self, mock_s3_client):
        """Test downloading a document from S3."""
        # Set up the mock
        mock_body = MagicMock()
        mock_body.read.return_value = b'test content'
        mock_s3_client.get_object.return_value = {
            'Body': mock_body,
            'ContentType': 'application/pdf',
            'ContentLength': 12,
            'LastModified': datetime.datetime.now(),
            'ETag': '"123456789"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            }
        }
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        
        # Call the function
        content, metadata = s3_utils.download_document(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key
        )
        
        # Verify the result
        assert content == b'test content'
        assert metadata['ContentType'] == 'application/pdf'
        assert metadata['ContentLength'] == 12
        assert 'LastModified' in metadata
        assert metadata['ETag'] == '"123456789"'
        assert metadata['ServerSideEncryption'] == 'AES256'
        assert metadata['Metadata']['document-classification'] == 'application_form'
        assert metadata['Metadata']['classification-confidence'] == '0.95'
        
        # Verify get_object was called with the correct parameters
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )
    
    def test_download_document_error_handling(self, mock_s3_client):
        """Test error handling when downloading a document fails."""
        # Set up the mock to raise a ClientError
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'non-existent-document.pdf'
        
        # Call the function and verify it raises the exception
        with pytest.raises(ClientError) as excinfo:
            s3_utils.download_document(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key
            )
        
        # Verify the exception details
        assert 'NoSuchKey' in str(excinfo.value)
        assert 'The specified key does not exist' in str(excinfo.value)
    
    def test_download_document_to_file(self, mock_s3_client, tmp_path):
        """Test downloading a document directly to a file."""
        # Set up the mocks
        mock_s3_resource = MagicMock()
        mock_s3_client.meta.region_name = 'us-east-1'
        mock_s3_client.meta.endpoint_url = 'http://localhost:9000'
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'LastModified': datetime.datetime.now(),
            'ETag': '"123456789"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            }
        }
        
        with patch('boto3.resource') as mock_boto3_resource:
            # Set up the resource mock
            mock_boto3_resource.return_value = mock_s3_resource
            
            # Test data
            bucket_name = 'test-bucket'
            object_key = 'test-document.pdf'
            file_path = str(tmp_path / 'downloaded-document.pdf')
            
            # Call the function
            result = s3_utils.download_document_to_file(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key,
                file_path=file_path
            )
            
            # Verify the result
            assert result['ContentType'] == 'application/pdf'
            assert result['ContentLength'] == 1024
            assert 'LastModified' in result
            assert result['ETag'] == '"123456789"'
            assert result['ServerSideEncryption'] == 'AES256'
            assert result['Metadata']['document-classification'] == 'application_form'
            assert result['Metadata']['classification-confidence'] == '0.95'
            
            # Verify boto3.resource was called with the correct parameters
            mock_boto3_resource.assert_called_once_with(
                's3',
                region_name='us-east-1',
                endpoint_url='http://localhost:9000'
            )
            
            # Verify download_file was called with the correct parameters
            mock_s3_resource.meta.client.download_file.assert_called_once_with(
                Bucket=bucket_name,
                Key=object_key,
                Filename=file_path,
                Config=ANY
            )
            
            # Verify head_object was called to get the metadata
            mock_s3_client.head_object.assert_called_once_with(
                Bucket=bucket_name,
                Key=object_key
            )


# ============================================================================
# Test Metadata Management Functions
# ============================================================================

class TestMetadataManagement:
    """Tests for metadata management functions."""

    def test_get_document_metadata(self, mock_s3_client):
        """Test getting metadata for a document without downloading the content."""
        # Set up the mock
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'LastModified': datetime.datetime.now(),
            'ETag': '"123456789"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            }
        }
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        
        # Call the function
        result = s3_utils.get_document_metadata(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key
        )
        
        # Verify the result
        assert result['ContentType'] == 'application/pdf'
        assert result['ContentLength'] == 1024
        assert 'LastModified' in result
        assert result['ETag'] == '"123456789"'
        assert result['ServerSideEncryption'] == 'AES256'
        assert result['Metadata']['document-classification'] == 'application_form'
        assert result['Metadata']['classification-confidence'] == '0.95'
        
        # Verify head_object was called with the correct parameters
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )
    
    def test_get_document_classification(self, mock_s3_client):
        """Test getting the classification and confidence score for a document."""
        # Set up the mock
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'LastModified': datetime.datetime.now(),
            'ETag': '"123456789"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            }
        }
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        
        # Call the function
        classification, confidence = s3_utils.get_document_classification(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key
        )
        
        # Verify the result
        assert classification == 'application_form'
        assert confidence == 0.95
        
        # Verify head_object was called with the correct parameters
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )
    
    def test_update_document_metadata(self, mock_s3_client):
        """Test updating metadata for an existing document."""
        # Set up the mocks
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'LastModified': datetime.datetime.now(),
            'ETag': '"123456789"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'document-classification': 'application_form',
                'classification-confidence': '0.95',
                'original-filename': 'test.pdf'
            }
        }
        mock_s3_client.copy_object.return_value = {
            'CopyObjectResult': {
                'ETag': '"987654321"',
                'LastModified': datetime.datetime.now()
            }
        }
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        new_metadata = {
            'document-classification': 'tax_return',
            'classification-confidence': '0.98'
        }
        
        # Call the function
        result = s3_utils.update_document_metadata(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key,
            metadata=new_metadata
        )
        
        # Verify the result
        assert 'CopyObjectResult' in result
        assert result['CopyObjectResult']['ETag'] == '"987654321"'
        
        # Verify head_object was called to get the current metadata
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )
        
        # Verify copy_object was called with the correct parameters
        mock_s3_client.copy_object.assert_called_once_with(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': object_key},
            Key=object_key,
            Metadata={
                'document-classification': 'tax_return',
                'classification-confidence': '0.98',
                'original-filename': 'test.pdf'
            },
            MetadataDirective='REPLACE',
            ServerSideEncryption='AES256'  # Verify AES-256 encryption is maintained
        )
    
    def test_update_document_classification(self, mock_s3_client):
        """Test updating the classification and confidence score for a document."""
        # Set up the mocks for update_document_metadata which is called by update_document_classification
        with patch('document_service.utils.s3_utils.update_document_metadata') as mock_update_metadata:
            mock_update_metadata.return_value = {
                'CopyObjectResult': {
                    'ETag': '"987654321"',
                    'LastModified': datetime.datetime.now()
                }
            }
            
            # Test data
            bucket_name = 'test-bucket'
            object_key = 'test-document.pdf'
            document_classification = 'tax_return'
            classification_confidence = 0.98
            
            # Call the function
            result = s3_utils.update_document_classification(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key,
                document_classification=document_classification,
                classification_confidence=classification_confidence
            )
            
            # Verify the result
            assert 'CopyObjectResult' in result
            assert result['CopyObjectResult']['ETag'] == '"987654321"'
            
            # Verify update_document_metadata was called with the correct parameters
            mock_update_metadata.assert_called_once_with(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key,
                metadata={
                    'document-classification': 'tax_return',
                    'classification-confidence': '0.98'
                }
            )


# ============================================================================
# Test URL Generation Functions
# ============================================================================

class TestUrlGeneration:
    """Tests for URL generation functions."""

    def test_generate_presigned_url(self, mock_s3_client):
        """Test generating a presigned URL for secure access to an S3 object."""
        # Set up the mock
        mock_s3_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/test-document.pdf?signature=abc123'
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        expiration = 3600  # 1 hour
        http_method = 'GET'
        
        # Call the function
        result = s3_utils.generate_presigned_url(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key,
            expiration=expiration,
            http_method=http_method
        )
        
        # Verify the result
        assert result == 'https://test-bucket.s3.amazonaws.com/test-document.pdf?signature=abc123'
        
        # Verify generate_presigned_url was called with the correct parameters
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
    
    def test_generate_presigned_url_put_method(self, mock_s3_client):
        """Test generating a presigned URL for uploading an object to S3."""
        # Set up the mock
        mock_s3_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/test-document.pdf?signature=abc123'
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        expiration = 3600  # 1 hour
        http_method = 'PUT'
        
        # Call the function
        result = s3_utils.generate_presigned_url(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key,
            expiration=expiration,
            http_method=http_method
        )
        
        # Verify the result
        assert result == 'https://test-bucket.s3.amazonaws.com/test-document.pdf?signature=abc123'
        
        # Verify generate_presigned_url was called with the correct parameters
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod='put_object',
            Params={
                'Bucket': bucket_name,
                'Key': object_key
            },
            ExpiresIn=expiration
        )
    
    def test_generate_presigned_url_invalid_method(self, mock_s3_client):
        """Test error handling for invalid HTTP method."""
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        http_method = 'DELETE'  # Invalid method
        
        # Call the function and verify it raises a ValueError
        with pytest.raises(ValueError) as excinfo:
            s3_utils.generate_presigned_url(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                object_key=object_key,
                http_method=http_method
            )
        
        # Verify the exception message
        assert "Unsupported HTTP method: DELETE" in str(excinfo.value)
    
    def test_generate_presigned_post(self, mock_s3_client):
        """Test generating a presigned POST policy for uploading objects to S3."""
        # Set up the mock
        mock_s3_client.generate_presigned_post.return_value = {
            'url': 'https://test-bucket.s3.amazonaws.com/',
            'fields': {
                'key': 'test-document.pdf',
                'AWSAccessKeyId': 'test-key',
                'policy': 'base64-encoded-policy',
                'signature': 'signature',
                'x-amz-server-side-encryption': 'AES256'
            }
        }
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        fields = {'success_action_redirect': 'https://example.com/success'}
        conditions = [{'acl': 'private'}]
        expiration = 3600  # 1 hour
        
        # Call the function
        result = s3_utils.generate_presigned_post(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key,
            fields=fields,
            conditions=conditions,
            expiration=expiration
        )
        
        # Verify the result
        assert result['url'] == 'https://test-bucket.s3.amazonaws.com/'
        assert result['fields']['key'] == 'test-document.pdf'
        assert result['fields']['x-amz-server-side-encryption'] == 'AES256'
        
        # Verify generate_presigned_post was called with the correct parameters
        mock_s3_client.generate_presigned_post.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key,
            Fields={
                'success_action_redirect': 'https://example.com/success',
                'x-amz-server-side-encryption': 'AES256'
            },
            Conditions=[
                {'acl': 'private'},
                {'x-amz-server-side-encryption': 'AES256'}
            ],
            ExpiresIn=expiration
        )
    
    def test_get_document_url(self, mock_s3_client):
        """Test getting a direct URL to a document in S3."""
        # Set up the mock
        mock_s3_client.meta.region_name = 'us-east-1'
        mock_s3_client.meta.endpoint_url = None  # Standard AWS S3
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        
        # Call the function
        result = s3_utils.get_document_url(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key
        )
        
        # Verify the result for standard AWS S3
        assert result == 'https://test-bucket.s3.us-east-1.amazonaws.com/test-document.pdf'
        
        # Test with custom endpoint
        mock_s3_client.meta.endpoint_url = 'http://localhost:9000'
        
        # Call the function again
        result = s3_utils.get_document_url(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            object_key=object_key
        )
        
        # Verify the result for custom endpoint
        assert result == 'http://localhost:9000/test-bucket/test-document.pdf'


# ============================================================================
# Test Bucket Operations Functions
# ============================================================================

class TestBucketOperations:
    """Tests for bucket operations functions."""

    def test_check_bucket_encryption_enabled(self, mock_s3_client):
        """Test checking if a bucket has AES-256 encryption enabled (positive case)."""
        # Set up the mock
        mock_s3_client.get_bucket_encryption.return_value = {
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
        
        # Test data
        bucket_name = 'test-bucket'
        
        # Call the function
        result = s3_utils.check_bucket_encryption(mock_s3_client, bucket_name)
        
        # Verify the result
        assert result is True
        
        # Verify get_bucket_encryption was called with the correct parameters
        mock_s3_client.get_bucket_encryption.assert_called_once_with(Bucket=bucket_name)
    
    def test_check_bucket_encryption_disabled(self, mock_s3_client):
        """Test checking if a bucket has AES-256 encryption enabled (negative case)."""
        # Set up the mock
        mock_s3_client.get_bucket_encryption.return_value = {
            'ServerSideEncryptionConfiguration': {
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'KMS'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        }
        
        # Test data
        bucket_name = 'test-bucket'
        
        # Call the function
        result = s3_utils.check_bucket_encryption(mock_s3_client, bucket_name)
        
        # Verify the result
        assert result is False
        
        # Verify get_bucket_encryption was called with the correct parameters
        mock_s3_client.get_bucket_encryption.assert_called_once_with(Bucket=bucket_name)
    
    def test_check_bucket_encryption_not_configured(self, mock_s3_client):
        """Test checking if a bucket has encryption when it's not configured."""
        # Set up the mock to raise a ClientError for no encryption configuration
        error_response = {'Error': {'Code': 'ServerSideEncryptionConfigurationNotFoundError', 'Message': 'The server side encryption configuration was not found'}}
        mock_s3_client.get_bucket_encryption.side_effect = ClientError(error_response, 'GetBucketEncryption')
        
        # Test data
        bucket_name = 'test-bucket'
        
        # Call the function
        result = s3_utils.check_bucket_encryption(mock_s3_client, bucket_name)
        
        # Verify the result
        assert result is False
        
        # Verify get_bucket_encryption was called with the correct parameters
        mock_s3_client.get_bucket_encryption.assert_called_once_with(Bucket=bucket_name)
    
    def test_enable_bucket_encryption(self, mock_s3_client):
        """Test enabling AES-256 encryption for a bucket."""
        # Set up the mock
        mock_s3_client.put_bucket_encryption.return_value = {}
        
        # Test data
        bucket_name = 'test-bucket'
        
        # Call the function
        result = s3_utils.enable_bucket_encryption(mock_s3_client, bucket_name)
        
        # Verify the result
        assert result == {}
        
        # Verify put_bucket_encryption was called with the correct parameters
        mock_s3_client.put_bucket_encryption.assert_called_once_with(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {
                            'SSEAlgorithm': 'AES256'
                        },
                        'BucketKeyEnabled': True
                    }
                ]
            }
        )


# ============================================================================
# Test Document Operations Functions
# ============================================================================

class TestDocumentOperations:
    """Tests for document operations functions."""

    def test_delete_document(self, mock_s3_client):
        """Test deleting a document from S3."""
        # Set up the mock
        mock_s3_client.delete_object.return_value = {}
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        
        # Call the function
        result = s3_utils.delete_document(mock_s3_client, bucket_name, object_key)
        
        # Verify the result
        assert result == {}
        
        # Verify delete_object was called with the correct parameters
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )
    
    def test_list_documents(self, mock_s3_client):
        """Test listing documents in an S3 bucket."""
        # Set up the mock
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {
                    'Key': 'document1.pdf',
                    'Size': 1024,
                    'LastModified': datetime.datetime.now(),
                    'ETag': '"123456789"',
                    'StorageClass': 'STANDARD'
                },
                {
                    'Key': 'document2.pdf',
                    'Size': 2048,
                    'LastModified': datetime.datetime.now(),
                    'ETag': '"987654321"',
                    'StorageClass': 'STANDARD'
                }
            ]
        }
        
        # Test data
        bucket_name = 'test-bucket'
        prefix = 'documents/'
        max_keys = 10
        
        # Call the function
        result = s3_utils.list_documents(
            s3_client=mock_s3_client,
            bucket_name=bucket_name,
            prefix=prefix,
            max_keys=max_keys
        )
        
        # Verify the result
        assert len(result) == 2
        assert result[0]['Key'] == 'document1.pdf'
        assert result[0]['Size'] == 1024
        assert 'LastModified' in result[0]
        assert result[0]['ETag'] == '"123456789"'
        assert result[0]['StorageClass'] == 'STANDARD'
        
        # Verify list_objects_v2 was called with the correct parameters
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket=bucket_name,
            Prefix=prefix,
            MaxKeys=max_keys
        )
    
    def test_list_documents_by_classification(self, mock_s3_client):
        """Test listing documents in an S3 bucket with a specific classification."""
        # Set up the mocks
        mock_s3_client.list_objects_v2.return_value = {
            'Contents': [
                {'Key': 'document1.pdf', 'Size': 1024, 'LastModified': datetime.datetime.now()},
                {'Key': 'document2.pdf', 'Size': 2048, 'LastModified': datetime.datetime.now()}
            ]
        }
        
        # Mock the get_document_classification function
        with patch('document_service.utils.s3_utils.get_document_classification') as mock_get_classification:
            # First document is an application form, second is a tax return
            mock_get_classification.side_effect = [
                ('application_form', 0.95),
                ('tax_return', 0.98)
            ]
            
            # Test data
            bucket_name = 'test-bucket'
            classification = 'application_form'
            prefix = 'documents/'
            max_keys = 10
            
            # Call the function
            result = s3_utils.list_documents_by_classification(
                s3_client=mock_s3_client,
                bucket_name=bucket_name,
                classification=classification,
                prefix=prefix,
                max_keys=max_keys
            )
            
            # Verify the result
            assert len(result) == 1
            assert result[0]['Key'] == 'document1.pdf'
            
            # Verify list_documents was called with the correct parameters
            mock_s3_client.list_objects_v2.assert_called_once_with(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            # Verify get_document_classification was called for each document
            assert mock_get_classification.call_count == 2
            mock_get_classification.assert_has_calls([
                call(mock_s3_client, bucket_name, 'document1.pdf'),
                call(mock_s3_client, bucket_name, 'document2.pdf')
            ])
    
    def test_document_exists(self, mock_s3_client):
        """Test checking if a document exists in S3 (positive case)."""
        # Set up the mock
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024
        }
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'test-document.pdf'
        
        # Call the function
        result = s3_utils.document_exists(mock_s3_client, bucket_name, object_key)
        
        # Verify the result
        assert result is True
        
        # Verify head_object was called with the correct parameters
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )
    
    def test_document_does_not_exist(self, mock_s3_client):
        """Test checking if a document exists in S3 (negative case)."""
        # Set up the mock to raise a ClientError for non-existent object
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        # Test data
        bucket_name = 'test-bucket'
        object_key = 'non-existent-document.pdf'
        
        # Call the function
        result = s3_utils.document_exists(mock_s3_client, bucket_name, object_key)
        
        # Verify the result
        assert result is False
        
        # Verify head_object was called with the correct parameters
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=bucket_name,
            Key=object_key
        )


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])