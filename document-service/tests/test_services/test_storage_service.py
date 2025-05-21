#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the S3-compatible storage service in the Document Service.

This module contains tests for the StorageService class, which handles document
retrieval, storage, and management with secure AES-256 encryption. The tests verify
that the service correctly connects to S3, retrieves documents, stores documents
with encryption, manages document metadata, and handles storage errors.

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
from typing import Dict, Any, Optional

# Import the module to test
from src.services.storage_service import StorageService, handle_s3_errors
from src.types.storage import (
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult,
    StorageKey,
    PresignedUrlOptions,
    StorageError,
    StorageErrorCode,
    EncryptionType,
    DocumentType
)
from src.types.documents import Document, DocumentMetadata


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client for testing."""
    mock_client = MagicMock()
    # Configure common mock responses
    mock_client.head_object.return_value = {
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
    return mock_client


@pytest.fixture
def mock_s3_config():
    """Create a mock S3 configuration for testing."""
    return S3ClientConfig(
        endpoint_url='http://localhost:4566',
        region_name='us-east-1',
        aws_access_key_id='test-key',
        aws_secret_access_key='test-secret',
        use_ssl=True,
        verify=True,
        max_pool_connections=10,
        timeout=30,
        retries=3
    )


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    return Document(
        metadata=DocumentMetadata(
            document_id='test-doc-123',
            application_id='test-app-456',
            original_filename='test-document.pdf',
            content_type='application/pdf',
            size_bytes=1024,
            upload_timestamp=datetime.datetime.now()
        ),
        content=b'test document content',
        document_type=DocumentType.APPLICATION,
        classification_confidence=0.95
    )


@pytest.fixture
def sample_document_path(tmp_path):
    """Create a sample document file for testing."""
    file_path = tmp_path / 'test-document.pdf'
    with open(file_path, 'wb') as f:
        f.write(b'test document content')
    return file_path


@pytest.fixture
def storage_service(mock_s3_client, mock_s3_config):
    """Create a StorageService instance with mocked dependencies for testing."""
    with patch('src.services.storage_service.s3_utils.get_s3_client', return_value=mock_s3_client):
        service = StorageService(mock_s3_config)
        # Override the S3 client with our mock
        service.s3_client = mock_s3_client
        yield service


# ============================================================================
# Test Initialization and Configuration
# ============================================================================

class TestStorageServiceInitialization:
    """Tests for StorageService initialization and configuration."""

    def test_init_with_config(self, mock_s3_client, mock_s3_config):
        """Test initializing StorageService with a provided configuration."""
        with patch('src.services.storage_service.s3_utils.get_s3_client', return_value=mock_s3_client):
            service = StorageService(mock_s3_config)
            
            # Verify the service was initialized with the correct configuration
            assert service.config == mock_s3_config
            assert service.s3_client == mock_s3_client
            assert service.bucket_config.name.startswith('mca-documents-')
            assert service.bucket_config.encryption == EncryptionType.AES256
    
    def test_init_without_config(self, mock_s3_client):
        """Test initializing StorageService without a provided configuration."""
        with patch('src.services.storage_service.s3_utils.get_s3_client', return_value=mock_s3_client), \
             patch.object(StorageService, '_load_config', return_value=mock_s3_config()):
            service = StorageService()
            
            # Verify the service was initialized with the default configuration
            assert service.s3_client == mock_s3_client
            assert service.bucket_config.name.startswith('mca-documents-')
            assert service.bucket_config.encryption == EncryptionType.AES256
    
    def test_load_config(self):
        """Test loading configuration from environment variables."""
        with patch.dict(os.environ, {
            'S3_ENDPOINT_URL': 'http://custom-endpoint.com',
            'S3_REGION_NAME': 'us-west-2',
            'S3_ACCESS_KEY_ID': 'custom-key',
            'S3_SECRET_ACCESS_KEY': 'custom-secret'
        }), patch('src.services.storage_service.s3_config', create=True) as mock_s3_config_module:
            # Set attributes on the mock s3_config module
            mock_s3_config_module.S3_ENDPOINT_URL = None
            mock_s3_config_module.S3_REGION_NAME = None
            mock_s3_config_module.S3_ACCESS_KEY_ID = None
            mock_s3_config_module.S3_SECRET_ACCESS_KEY = None
            
            # Call the method directly
            service = StorageService()
            config = service._load_config()
            
            # Verify the configuration was loaded from environment variables
            assert config['endpoint_url'] == 'http://custom-endpoint.com'
            assert config['region_name'] == 'us-west-2'
            assert config['aws_access_key_id'] == 'custom-key'
            assert config['aws_secret_access_key'] == 'custom-secret'
            assert config['use_ssl'] is True
            assert config['verify'] is True
    
    def test_initialize_bucket_config_production(self):
        """Test initializing bucket configuration for production environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'production'}), \
             patch('src.services.storage_service.s3_config', create=True) as mock_s3_config_module:
            # Set attributes on the mock s3_config module
            mock_s3_config_module.S3_PRODUCTION_BUCKET = 'custom-production-bucket'
            
            service = StorageService(mock_s3_config())
            bucket_config = service._initialize_bucket_config()
            
            # Verify the bucket configuration for production
            assert bucket_config.name == 'custom-production-bucket'
            assert bucket_config.encryption == EncryptionType.AES256
            assert bucket_config.versioning is True
            assert bucket_config.public_access_blocked is True
    
    def test_initialize_bucket_config_staging(self):
        """Test initializing bucket configuration for staging environment."""
        with patch.dict(os.environ, {'ENVIRONMENT': 'staging'}), \
             patch('src.services.storage_service.s3_config', create=True) as mock_s3_config_module:
            # Set attributes on the mock s3_config module
            mock_s3_config_module.S3_STAGING_BUCKET = 'custom-staging-bucket'
            
            service = StorageService(mock_s3_config())
            bucket_config = service._initialize_bucket_config()
            
            # Verify the bucket configuration for staging
            assert bucket_config.name == 'custom-staging-bucket'
            assert bucket_config.encryption == EncryptionType.AES256
            assert bucket_config.versioning is True
            assert bucket_config.public_access_blocked is True
    
    def test_ensure_bucket_encryption(self, mock_s3_client):
        """Test ensuring bucket encryption is enabled."""
        with patch('src.services.storage_service.s3_utils.check_bucket_encryption', return_value=False), \
             patch('src.services.storage_service.s3_utils.enable_bucket_encryption') as mock_enable_encryption, \
             patch('src.services.storage_service.s3_config', create=True) as mock_s3_config_module:
            # Set attributes on the mock s3_config module
            mock_s3_config_module.S3_ENCRYPTION_ENABLED = True
            
            service = StorageService(mock_s3_config())
            service.s3_client = mock_s3_client
            service._ensure_bucket_encryption()
            
            # Verify enable_bucket_encryption was called
            mock_enable_encryption.assert_called_once_with(mock_s3_client, service.bucket_config.name)
    
    def test_ensure_bucket_encryption_already_enabled(self, mock_s3_client):
        """Test ensuring bucket encryption when it's already enabled."""
        with patch('src.services.storage_service.s3_utils.check_bucket_encryption', return_value=True), \
             patch('src.services.storage_service.s3_utils.enable_bucket_encryption') as mock_enable_encryption, \
             patch('src.services.storage_service.s3_config', create=True) as mock_s3_config_module:
            # Set attributes on the mock s3_config module
            mock_s3_config_module.S3_ENCRYPTION_ENABLED = True
            
            service = StorageService(mock_s3_config())
            service.s3_client = mock_s3_client
            service._ensure_bucket_encryption()
            
            # Verify enable_bucket_encryption was not called
            mock_enable_encryption.assert_not_called()


# ============================================================================
# Test Error Handling
# ============================================================================

class TestStorageServiceErrorHandling:
    """Tests for StorageService error handling."""

    def test_handle_s3_errors_decorator(self):
        """Test the handle_s3_errors decorator for mapping S3 errors to StorageError."""
        # Create a test function with the decorator
        @handle_s3_errors
        def test_function(param):
            if param == 'success':
                return 'success'
            elif param == 'client_error':
                error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
                raise ClientError(error_response, 'GetObject')
            else:
                raise ValueError('Test error')
        
        # Test successful execution
        assert test_function('success') == 'success'
        
        # Test ClientError handling
        with pytest.raises(StorageError) as excinfo:
            test_function('client_error')
        assert excinfo.value.code == StorageErrorCode.OBJECT_NOT_FOUND.value
        assert 'The specified key does not exist' in excinfo.value.message
        
        # Test other exception handling
        with pytest.raises(StorageError) as excinfo:
            test_function('other_error')
        assert excinfo.value.code == StorageErrorCode.STORAGE_ERROR.value
        assert 'Test error' in excinfo.value.message
    
    def test_error_mapping(self):
        """Test mapping of AWS error codes to StorageErrorCode."""
        # Create a test function that raises different AWS errors
        @handle_s3_errors
        def test_function(error_code):
            error_response = {'Error': {'Code': error_code, 'Message': f'Test {error_code} error'}}
            raise ClientError(error_response, 'TestOperation')
        
        # Test NoSuchBucket error
        with pytest.raises(StorageError) as excinfo:
            test_function('NoSuchBucket')
        assert excinfo.value.code == StorageErrorCode.BUCKET_NOT_FOUND.value
        
        # Test NoSuchKey error
        with pytest.raises(StorageError) as excinfo:
            test_function('NoSuchKey')
        assert excinfo.value.code == StorageErrorCode.OBJECT_NOT_FOUND.value
        
        # Test AccessDenied error
        with pytest.raises(StorageError) as excinfo:
            test_function('AccessDenied')
        assert excinfo.value.code == StorageErrorCode.PERMISSION_DENIED.value
        
        # Test InvalidAccessKeyId error
        with pytest.raises(StorageError) as excinfo:
            test_function('InvalidAccessKeyId')
        assert excinfo.value.code == StorageErrorCode.AUTHENTICATION_ERROR.value
        
        # Test SignatureDoesNotMatch error
        with pytest.raises(StorageError) as excinfo:
            test_function('SignatureDoesNotMatch')
        assert excinfo.value.code == StorageErrorCode.AUTHENTICATION_ERROR.value
        
        # Test RequestTimeout error
        with pytest.raises(StorageError) as excinfo:
            test_function('RequestTimeout')
        assert excinfo.value.code == StorageErrorCode.TIMEOUT_ERROR.value
        
        # Test unknown error
        with pytest.raises(StorageError) as excinfo:
            test_function('UnknownError')
        assert excinfo.value.code == StorageErrorCode.STORAGE_ERROR.value


# ============================================================================
# Test Document Download
# ============================================================================

class TestStorageServiceDownload:
    """Tests for StorageService document download functionality."""

    def test_download_document(self, storage_service, mock_s3_client):
        """Test downloading a document from S3."""
        # Set up the mock
        mock_body = MagicMock()
        mock_body.read.return_value = b'test document content'
        mock_s3_client.get_object.return_value = {
            'Body': mock_body,
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
        
        # Call the method
        result = storage_service.download_document('test-document.pdf')
        
        # Verify the result
        assert result.success is True
        content, metadata = result.data
        assert content == b'test document content'
        assert metadata['ContentType'] == 'application/pdf'
        assert metadata['ContentLength'] == 1024
        assert metadata['ServerSideEncryption'] == 'AES256'
        assert metadata['Metadata']['document-classification'] == 'application_form'
        
        # Verify the S3 client was called correctly
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_download_document_error(self, storage_service, mock_s3_client):
        """Test error handling when downloading a document fails."""
        # Set up the mock to raise an error
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        
        # Call the method
        result = storage_service.download_document('non-existent-document.pdf')
        
        # Verify the result
        assert result.success is False
        assert isinstance(result.error, StorageError)
        assert result.error.code == StorageErrorCode.OBJECT_NOT_FOUND.value
        
        # Verify the S3 client was called correctly
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='non-existent-document.pdf'
        )
    
    def test_download_document_to_file(self, storage_service, mock_s3_client, tmp_path):
        """Test downloading a document directly to a file."""
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
        
        # Create a temporary file path
        file_path = str(tmp_path / 'downloaded-document.pdf')
        
        # Mock the s3_utils.download_document_to_file function
        with patch('src.services.storage_service.s3_utils.download_document_to_file', 
                  return_value=mock_s3_client.head_object.return_value) as mock_download:
            # Call the method
            result = storage_service.download_document_to_file('test-document.pdf', file_path)
            
            # Verify the result
            assert result.success is True
            assert result.data['ContentType'] == 'application/pdf'
            assert result.data['ContentLength'] == 1024
            assert result.data['ServerSideEncryption'] == 'AES256'
            assert result.data['Metadata']['document-classification'] == 'application_form'
            
            # Verify the download function was called correctly
            mock_download.assert_called_once_with(
                storage_service.s3_client,
                storage_service.bucket_config.name,
                'test-document.pdf',
                file_path
            )
    
    def test_download_document_to_file_error(self, storage_service, mock_s3_client, tmp_path):
        """Test error handling when downloading a document to a file fails."""
        # Create a temporary file path
        file_path = str(tmp_path / 'downloaded-document.pdf')
        
        # Mock the s3_utils.download_document_to_file function to raise an error
        with patch('src.services.storage_service.s3_utils.download_document_to_file') as mock_download:
            error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
            mock_download.side_effect = ClientError(error_response, 'GetObject')
            
            # Call the method
            result = storage_service.download_document_to_file('non-existent-document.pdf', file_path)
            
            # Verify the result
            assert result.success is False
            assert isinstance(result.error, StorageError)
            assert result.error.code == StorageErrorCode.OBJECT_NOT_FOUND.value
            
            # Verify the download function was called correctly
            mock_download.assert_called_once_with(
                storage_service.s3_client,
                storage_service.bucket_config.name,
                'non-existent-document.pdf',
                file_path
            )
    
    def test_retrieve_document(self, storage_service, mock_s3_client, sample_document):
        """Test retrieving a document with its metadata and classification."""
        # Set up the mocks
        # Mock for download_document
        mock_body = MagicMock()
        mock_body.read.return_value = b'test document content'
        mock_s3_client.get_object.return_value = {
            'Body': mock_body,
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'LastModified': datetime.datetime.now(),
            'ETag': '"123456789"',
            'ServerSideEncryption': 'AES256',
            'Metadata': {
                'application_id': 'test-app-456',
                'document_id': 'test-doc-123',
                'original_filename': 'test-document.pdf'
            }
        }
        
        # Mock for get_document_classification
        with patch.object(storage_service, 'get_document_classification') as mock_get_classification:
            mock_get_classification.return_value = StorageResult(True, ('application', 0.95))
            
            # Mock for parse_storage_key
            with patch.object(storage_service, 'parse_storage_key') as mock_parse_key:
                mock_parse_key.return_value = StorageKey(
                    application_id='test-app-456',
                    document_id='test-doc-123',
                    document_type='application',
                    version='v1'
                )
                
                # Call the method
                result = storage_service.retrieve_document('test-app-456/application/test-doc-123/v1')
                
                # Verify the result
                assert result.success is True
                document = result.data
                assert document.metadata.document_id == 'test-doc-123'
                assert document.metadata.application_id == 'test-app-456'
                assert document.metadata.original_filename == 'test-document.pdf'
                assert document.metadata.content_type == 'application/pdf'
                assert document.content == b'test document content'
                assert document.document_type == DocumentType.APPLICATION
                assert document.classification_confidence == 0.95
                
                # Verify the mocked methods were called correctly
                mock_get_classification.assert_called_once_with('test-app-456/application/test-doc-123/v1')
                mock_parse_key.assert_called_once_with('test-app-456/application/test-doc-123/v1')


# ============================================================================
# Test Document Upload
# ============================================================================

class TestStorageServiceUpload:
    """Tests for StorageService document upload functionality."""

    def test_upload_document(self, storage_service, mock_s3_client):
        """Test uploading a document to S3 with AES-256 encryption."""
        # Set up the mock
        mock_s3_client.put_object.return_value = {'ETag': '"123456789"'}
        
        # Test data
        document_key = 'test-document.pdf'
        file_obj = io.BytesIO(b'test document content')
        metadata = {'original_filename': 'test.pdf'}
        content_type = 'application/pdf'
        document_classification = 'application_form'
        classification_confidence = 0.95
        
        # Call the method
        result = storage_service.upload_document(
            document_key=document_key,
            file_obj=file_obj,
            metadata=metadata,
            content_type=content_type,
            document_classification=document_classification,
            classification_confidence=classification_confidence
        )
        
        # Verify the result
        assert result.success is True
        assert result.data['ETag'] == '"123456789"'
        
        # Verify the S3 client was called correctly with AES-256 encryption
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key=document_key,
            Body=file_obj,
            ServerSideEncryption='AES256',  # Verify AES-256 encryption is used
            Metadata={
                'original_filename': 'test.pdf',
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            },
            ContentType='application/pdf'
        )
    
    def test_upload_document_error(self, storage_service, mock_s3_client):
        """Test error handling when uploading a document fails."""
        # Set up the mock to raise an error
        error_response = {'Error': {'Code': 'AccessDenied', 'Message': 'Access Denied'}}
        mock_s3_client.put_object.side_effect = ClientError(error_response, 'PutObject')
        
        # Test data
        document_key = 'test-document.pdf'
        file_obj = io.BytesIO(b'test document content')
        
        # Call the method
        result = storage_service.upload_document(
            document_key=document_key,
            file_obj=file_obj
        )
        
        # Verify the result
        assert result.success is False
        assert isinstance(result.error, StorageError)
        assert result.error.code == StorageErrorCode.PERMISSION_DENIED.value
        
        # Verify the S3 client was called correctly
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key=document_key,
            Body=file_obj,
            ServerSideEncryption='AES256',  # Verify AES-256 encryption is still used
            Metadata={}
        )
    
    def test_upload_document_from_file(self, storage_service, mock_s3_client, sample_document_path):
        """Test uploading a document from a file to S3 with AES-256 encryption."""
        # Set up the mock
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024,
            'ServerSideEncryption': 'AES256'
        }
        
        # Mock the s3_utils.upload_document_with_transfer_manager function
        with patch('src.services.storage_service.s3_utils.upload_document_with_transfer_manager', 
                  return_value=mock_s3_client.head_object.return_value) as mock_upload:
            # Test data
            document_key = 'test-document.pdf'
            file_path = str(sample_document_path)
            metadata = {'original_filename': 'test.pdf'}
            content_type = 'application/pdf'
            document_classification = 'application_form'
            classification_confidence = 0.95
            
            # Call the method
            result = storage_service.upload_document_from_file(
                document_key=document_key,
                file_path=file_path,
                metadata=metadata,
                content_type=content_type,
                document_classification=document_classification,
                classification_confidence=classification_confidence
            )
            
            # Verify the result
            assert result.success is True
            assert result.data['ContentType'] == 'application/pdf'
            assert result.data['ContentLength'] == 1024
            assert result.data['ServerSideEncryption'] == 'AES256'
            
            # Verify the upload function was called correctly with AES-256 encryption
            mock_upload.assert_called_once_with(
                storage_service.s3_client,
                storage_service.bucket_config.name,
                document_key,
                file_path,
                metadata,
                content_type,
                document_classification,
                classification_confidence
            )
    
    def test_store_document(self, storage_service, sample_document):
        """Test storing a document with its metadata and classification."""
        # Mock the upload_document method
        with patch.object(storage_service, 'upload_document') as mock_upload:
            mock_upload.return_value = StorageResult(True, {'ETag': '"123456789"'})
            
            # Mock the create_storage_key method
            with patch.object(storage_service, 'create_storage_key') as mock_create_key:
                mock_create_key.return_value = 'test-app-456/application/test-doc-123/v1'
                
                # Call the method
                result = storage_service.store_document(sample_document)
                
                # Verify the result
                assert result.success is True
                assert result.data == 'test-app-456/application/test-doc-123/v1'
                
                # Verify the mocked methods were called correctly
                mock_create_key.assert_called_once_with(
                    application_id=sample_document.metadata.application_id,
                    document_id=sample_document.metadata.document_id,
                    document_type='application',
                    version='v1'
                )
                
                # Verify upload_document was called with the correct parameters
                mock_upload.assert_called_once_with(
                    document_key='test-app-456/application/test-doc-123/v1',
                    file_obj=sample_document.content,
                    metadata={
                        'document_id': sample_document.metadata.document_id,
                        'application_id': sample_document.metadata.application_id,
                        'original_filename': sample_document.metadata.original_filename,
                        'upload_timestamp': ANY,
                        'size_bytes': str(sample_document.metadata.size_bytes)
                    },
                    content_type=sample_document.metadata.content_type,
                    document_classification='application',
                    classification_confidence=sample_document.classification_confidence
                )


# ============================================================================
# Test Metadata Management
# ============================================================================

class TestStorageServiceMetadata:
    """Tests for StorageService metadata management functionality."""

    def test_get_document_metadata(self, storage_service, mock_s3_client):
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
                'classification-confidence': '0.95',
                'original_filename': 'test.pdf'
            }
        }
        
        # Call the method
        result = storage_service.get_document_metadata('test-document.pdf')
        
        # Verify the result
        assert result.success is True
        assert result.data['ContentType'] == 'application/pdf'
        assert result.data['ContentLength'] == 1024
        assert result.data['ServerSideEncryption'] == 'AES256'
        assert result.data['Metadata']['document-classification'] == 'application_form'
        assert result.data['Metadata']['classification-confidence'] == '0.95'
        
        # Verify the S3 client was called correctly
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_get_document_classification(self, storage_service, mock_s3_client):
        """Test getting the classification and confidence score for a document."""
        # Set up the mock
        mock_s3_client.head_object.return_value = {
            'Metadata': {
                'document-classification': 'application_form',
                'classification-confidence': '0.95'
            }
        }
        
        # Call the method
        result = storage_service.get_document_classification('test-document.pdf')
        
        # Verify the result
        assert result.success is True
        classification, confidence = result.data
        assert classification == 'application_form'
        assert confidence == 0.95
        
        # Verify the S3 client was called correctly
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_update_document_metadata(self, storage_service, mock_s3_client):
        """Test updating metadata for an existing document."""
        # Set up the mock
        mock_s3_client.copy_object.return_value = {
            'CopyObjectResult': {
                'ETag': '"987654321"',
                'LastModified': datetime.datetime.now()
            }
        }
        
        # Mock the get_document_metadata method
        with patch.object(storage_service, 'get_document_metadata') as mock_get_metadata:
            mock_get_metadata.return_value = StorageResult(True, {
                'Metadata': {
                    'document-classification': 'application_form',
                    'classification-confidence': '0.95',
                    'original_filename': 'test.pdf'
                }
            })
            
            # Test data
            document_key = 'test-document.pdf'
            new_metadata = {
                'document-classification': 'tax_return',
                'classification-confidence': '0.98'
            }
            
            # Call the method
            result = storage_service.update_document_metadata(document_key, new_metadata)
            
            # Verify the result
            assert result.success is True
            assert result.data['CopyObjectResult']['ETag'] == '"987654321"'
            
            # Verify the mocked method was called correctly
            mock_get_metadata.assert_called_once_with(document_key)
            
            # Verify the S3 client was called correctly with AES-256 encryption
            mock_s3_client.copy_object.assert_called_once_with(
                Bucket=storage_service.bucket_config.name,
                CopySource={'Bucket': storage_service.bucket_config.name, 'Key': document_key},
                Key=document_key,
                Metadata={
                    'document-classification': 'tax_return',
                    'classification-confidence': '0.98',
                    'original_filename': 'test.pdf'
                },
                MetadataDirective='REPLACE',
                ServerSideEncryption='AES256'  # Verify AES-256 encryption is maintained
            )
    
    def test_update_document_classification(self, storage_service):
        """Test updating the classification and confidence score for a document."""
        # Mock the update_document_metadata method
        with patch.object(storage_service, 'update_document_metadata') as mock_update_metadata:
            mock_update_metadata.return_value = StorageResult(True, {
                'CopyObjectResult': {
                    'ETag': '"987654321"',
                    'LastModified': datetime.datetime.now()
                }
            })
            
            # Test data
            document_key = 'test-document.pdf'
            document_classification = 'tax_return'
            classification_confidence = 0.98
            
            # Call the method
            result = storage_service.update_document_classification(
                document_key, document_classification, classification_confidence)
            
            # Verify the result
            assert result.success is True
            assert result.data['CopyObjectResult']['ETag'] == '"987654321"'
            
            # Verify the mocked method was called correctly
            mock_update_metadata.assert_called_once_with(
                document_key,
                {
                    'document-classification': 'tax_return',
                    'classification-confidence': '0.98'
                }
            )


# ============================================================================
# Test Storage Key Management
# ============================================================================

class TestStorageServiceKeys:
    """Tests for StorageService storage key management functionality."""

    def test_create_storage_key(self, storage_service):
        """Test creating a storage key for a document."""
        # Test data
        application_id = 'test-app-456'
        document_id = 'test-doc-123'
        document_type = 'application'
        version = 'v1'
        
        # Call the method
        key = storage_service.create_storage_key(
            application_id=application_id,
            document_id=document_id,
            document_type=document_type,
            version=version
        )
        
        # Verify the result
        assert key == 'test-app-456/application/test-doc-123/v1'
    
    def test_create_storage_key_with_enum(self, storage_service):
        """Test creating a storage key with a DocumentType enum."""
        # Test data
        application_id = 'test-app-456'
        document_id = 'test-doc-123'
        document_type = DocumentType.APPLICATION
        version = 'v1'
        
        # Call the method
        key = storage_service.create_storage_key(
            application_id=application_id,
            document_id=document_id,
            document_type=document_type,
            version=version
        )
        
        # Verify the result
        assert key == 'test-app-456/application/test-doc-123/v1'
    
    def test_parse_storage_key(self, storage_service):
        """Test parsing a storage key string into a StorageKey object."""
        # Test data
        key_string = 'test-app-456/application/test-doc-123/v1'
        
        # Call the method
        key = storage_service.parse_storage_key(key_string)
        
        # Verify the result
        assert key.application_id == 'test-app-456'
        assert key.document_type == 'application'
        assert key.document_id == 'test-doc-123'
        assert key.version == 'v1'
    
    def test_parse_storage_key_invalid(self, storage_service):
        """Test parsing an invalid storage key string."""
        # Test data
        key_string = 'invalid-key-format'
        
        # Call the method and verify it raises a ValueError
        with pytest.raises(ValueError) as excinfo:
            storage_service.parse_storage_key(key_string)
        
        # Verify the exception message
        assert 'Invalid storage key format' in str(excinfo.value)


# ============================================================================
# Test Document Operations
# ============================================================================

class TestStorageServiceOperations:
    """Tests for StorageService document operations functionality."""

    def test_document_exists(self, storage_service, mock_s3_client):
        """Test checking if a document exists in S3 (positive case)."""
        # Set up the mock
        mock_s3_client.head_object.return_value = {
            'ContentType': 'application/pdf',
            'ContentLength': 1024
        }
        
        # Call the method
        result = storage_service.document_exists('test-document.pdf')
        
        # Verify the result
        assert result.success is True
        assert result.data is True
        
        # Verify the S3 client was called correctly
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_document_does_not_exist(self, storage_service, mock_s3_client):
        """Test checking if a document exists in S3 (negative case)."""
        # Set up the mock to raise a ClientError for non-existent object
        error_response = {'Error': {'Code': '404', 'Message': 'Not Found'}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, 'HeadObject')
        
        # Call the method
        result = storage_service.document_exists('non-existent-document.pdf')
        
        # Verify the result
        assert result.success is True
        assert result.data is False
        
        # Verify the S3 client was called correctly
        mock_s3_client.head_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='non-existent-document.pdf'
        )
    
    def test_delete_document(self, storage_service, mock_s3_client):
        """Test deleting a document from S3."""
        # Set up the mock
        mock_s3_client.delete_object.return_value = {}
        
        # Call the method
        result = storage_service.delete_document('test-document.pdf')
        
        # Verify the result
        assert result.success is True
        assert result.data == {}
        
        # Verify the S3 client was called correctly
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_list_documents(self, storage_service, mock_s3_client):
        """Test listing documents in the S3 bucket with optional prefix filtering."""
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
        
        # Call the method
        result = storage_service.list_documents(prefix='documents/', max_keys=10)
        
        # Verify the result
        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]['Key'] == 'document1.pdf'
        assert result.data[0]['Size'] == 1024
        assert result.data[1]['Key'] == 'document2.pdf'
        assert result.data[1]['Size'] == 2048
        
        # Verify the S3 client was called correctly
        mock_s3_client.list_objects_v2.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Prefix='documents/',
            MaxKeys=10
        )
    
    def test_list_documents_by_classification(self, storage_service, mock_s3_client):
        """Test listing documents with a specific classification."""
        # Mock the list_documents method
        with patch.object(storage_service, 'list_documents') as mock_list_documents:
            mock_list_documents.return_value = StorageResult(True, [
                {'Key': 'document1.pdf', 'Size': 1024},
                {'Key': 'document2.pdf', 'Size': 2048}
            ])
            
            # Mock the get_document_classification method
            with patch.object(storage_service, 'get_document_classification') as mock_get_classification:
                # First document is an application form, second is a tax return
                mock_get_classification.side_effect = [
                    StorageResult(True, ('application_form', 0.95)),
                    StorageResult(True, ('tax_return', 0.98))
                ]
                
                # Call the method
                result = storage_service.list_documents_by_classification(
                    classification='application_form',
                    prefix='documents/',
                    max_keys=10
                )
                
                # Verify the result
                assert result.success is True
                assert len(result.data) == 1
                assert result.data[0]['Key'] == 'document1.pdf'
                
                # Verify the mocked methods were called correctly
                mock_list_documents.assert_called_once_with(
                    prefix='documents/',
                    max_keys=10
                )
                assert mock_get_classification.call_count == 2
                mock_get_classification.assert_any_call('document1.pdf')
                mock_get_classification.assert_any_call('document2.pdf')


# ============================================================================
# Test URL Generation
# ============================================================================

class TestStorageServiceUrls:
    """Tests for StorageService URL generation functionality."""

    def test_generate_presigned_url(self, storage_service, mock_s3_client):
        """Test generating a presigned URL for secure access to a document."""
        # Set up the mock
        mock_s3_client.generate_presigned_url.return_value = 'https://test-bucket.s3.amazonaws.com/test-document.pdf?signature=abc123'
        
        # Call the method
        result = storage_service.generate_presigned_url(
            document_key='test-document.pdf',
            expiration=3600,
            http_method='GET'
        )
        
        # Verify the result
        assert result.success is True
        assert result.data == 'https://test-bucket.s3.amazonaws.com/test-document.pdf?signature=abc123'
        
        # Verify the S3 client was called correctly
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod='get_object',
            Params={
                'Bucket': storage_service.bucket_config.name,
                'Key': 'test-document.pdf'
            },
            ExpiresIn=3600
        )
    
    def test_generate_presigned_post(self, storage_service, mock_s3_client):
        """Test generating a presigned POST policy for uploading documents directly to S3."""
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
        
        # Call the method
        result = storage_service.generate_presigned_post(
            document_key='test-document.pdf',
            fields={'success_action_redirect': 'https://example.com/success'},
            conditions=[{'acl': 'private'}],
            expiration=3600
        )
        
        # Verify the result
        assert result.success is True
        assert result.data['url'] == 'https://test-bucket.s3.amazonaws.com/'
        assert result.data['fields']['key'] == 'test-document.pdf'
        assert result.data['fields']['x-amz-server-side-encryption'] == 'AES256'
        
        # Verify the S3 client was called correctly
        mock_s3_client.generate_presigned_post.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf',
            Fields={
                'success_action_redirect': 'https://example.com/success',
                'x-amz-server-side-encryption': 'AES256'
            },
            Conditions=[
                {'acl': 'private'},
                {'x-amz-server-side-encryption': 'AES256'}
            ],
            ExpiresIn=3600
        )


# ============================================================================
# Test Retry Logic
# ============================================================================

class TestStorageServiceRetry:
    """Tests for StorageService retry logic."""

    def test_retry_on_connection_error(self, storage_service, mock_s3_client):
        """Test retry logic when a connection error occurs."""
        # Set up the mock to fail twice with connection errors, then succeed
        error_response = {'Error': {'Code': 'RequestTimeout', 'Message': 'Request timed out'}}
        mock_s3_client.get_object.side_effect = [
            ClientError(error_response, 'GetObject'),  # First attempt fails
            ClientError(error_response, 'GetObject'),  # Second attempt fails
            {'Body': MagicMock(read=lambda: b'test content'), 'Metadata': {}}  # Third attempt succeeds
        ]
        
        # Call the method
        result = storage_service.download_document('test-document.pdf')
        
        # Verify the result
        assert result.success is True
        assert result.data[0] == b'test content'
        
        # Verify the S3 client was called three times
        assert mock_s3_client.get_object.call_count == 3
        mock_s3_client.get_object.assert_called_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_retry_max_attempts_exceeded(self, storage_service, mock_s3_client):
        """Test retry logic when maximum retry attempts are exceeded."""
        # Set up the mock to always fail with connection errors
        error_response = {'Error': {'Code': 'RequestTimeout', 'Message': 'Request timed out'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        
        # Call the method
        result = storage_service.download_document('test-document.pdf')
        
        # Verify the result
        assert result.success is False
        assert isinstance(result.error, StorageError)
        assert result.error.code == StorageErrorCode.TIMEOUT_ERROR.value
        
        # Verify the S3 client was called the maximum number of times (3 retries + 1 initial attempt)
        assert mock_s3_client.get_object.call_count == 4
        mock_s3_client.get_object.assert_called_with(
            Bucket=storage_service.bucket_config.name,
            Key='test-document.pdf'
        )
    
    def test_no_retry_on_non_retryable_error(self, storage_service, mock_s3_client):
        """Test that non-retryable errors are not retried."""
        # Set up the mock to fail with a non-retryable error (e.g., NoSuchKey)
        error_response = {'Error': {'Code': 'NoSuchKey', 'Message': 'The specified key does not exist.'}}
        mock_s3_client.get_object.side_effect = ClientError(error_response, 'GetObject')
        
        # Call the method
        result = storage_service.download_document('non-existent-document.pdf')
        
        # Verify the result
        assert result.success is False
        assert isinstance(result.error, StorageError)
        assert result.error.code == StorageErrorCode.OBJECT_NOT_FOUND.value
        
        # Verify the S3 client was called only once (no retries)
        mock_s3_client.get_object.assert_called_once_with(
            Bucket=storage_service.bucket_config.name,
            Key='non-existent-document.pdf'
        )


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])