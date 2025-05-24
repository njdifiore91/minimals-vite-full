#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's s3_config.py module.

These tests verify that S3 configuration correctly sets up connection parameters,
bucket settings, encryption options, and access controls. The tests ensure that
document storage works correctly with proper security measures.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the module under test
from src.config.s3_config import (
    get_bucket_name,
    get_s3_client_config,
    get_storage_options,
    validate_s3_configuration,
    DOCUMENT_BUCKET,
    EXTRACTED_DATA_BUCKET,
    DEFAULT_STORAGE_OPTIONS,
    S3_CLIENT_CONFIG,
    S3_BOTO_CONFIG
)

# Import types
from src.types.storage import (
    EncryptionType,
    StorageClass,
    BUCKET_CONFIGS
)


class TestS3Config:
    """Test suite for the S3 configuration module."""

    def test_get_bucket_name_default(self):
        """Test that get_bucket_name returns the correct bucket name for document type."""
        # Test default bucket name (document type)
        bucket_name = get_bucket_name()
        assert bucket_name == DOCUMENT_BUCKET
        
    def test_get_bucket_name_extracted(self):
        """Test that get_bucket_name returns the correct bucket name for extracted data type."""
        # Test extracted data bucket name
        bucket_name = get_bucket_name('extracted')
        assert bucket_name == EXTRACTED_DATA_BUCKET
        
    def test_get_bucket_name_invalid_type(self):
        """Test that get_bucket_name returns the document bucket for invalid types."""
        # Test with invalid bucket type
        bucket_name = get_bucket_name('invalid')
        assert bucket_name == DOCUMENT_BUCKET

    def test_get_s3_client_config_basic(self):
        """Test that get_s3_client_config returns the correct configuration."""
        # Get the S3 client configuration
        config = get_s3_client_config()
        
        # Check that the configuration contains the expected keys
        expected_keys = [
            'endpoint_url',
            'region_name',
            'aws_access_key_id',
            'aws_secret_access_key',
            'verify',
            'use_ssl'
        ]
        
        for key in expected_keys:
            assert key in config, f"Key '{key}' missing from S3 client configuration"
        
        # Check that the values match the S3_CLIENT_CONFIG
        assert config['endpoint_url'] == S3_CLIENT_CONFIG.endpoint_url
        assert config['region_name'] == S3_CLIENT_CONFIG.region
        assert config['aws_access_key_id'] == S3_CLIENT_CONFIG.credentials.access_key
        assert config['aws_secret_access_key'] == S3_CLIENT_CONFIG.credentials.secret_key
        assert config['verify'] == S3_CLIENT_CONFIG.verify_ssl

    def test_get_s3_client_config_with_session_token(self):
        """Test that get_s3_client_config includes session token when available."""
        # Patch the S3_CLIENT_CONFIG to include a session token
        with patch('src.config.s3_config.S3_CLIENT_CONFIG') as mock_config:
            mock_config.endpoint_url = 'https://s3.example.com'
            mock_config.region = 'us-west-2'
            mock_config.credentials.access_key = 'test-access-key'
            mock_config.credentials.secret_key = 'test-secret-key'
            mock_config.credentials.session_token = 'test-session-token'
            mock_config.verify_ssl = True
            
            # Get the S3 client configuration
            config = get_s3_client_config()
            
            # Check that the session token is included
            assert 'aws_session_token' in config
            assert config['aws_session_token'] == 'test-session-token'

    def test_get_storage_options_default(self):
        """Test that get_storage_options returns the correct default options."""
        # Get the storage options with default parameters
        options = get_storage_options()
        
        # Check that the options include AES-256 encryption
        assert 'ServerSideEncryption' in options
        assert options['ServerSideEncryption'] == EncryptionType.AES256.value
        
        # Check that the options include the correct storage class
        assert 'StorageClass' in options
        assert options['StorageClass'] == StorageClass.STANDARD.value
        
        # Check that the options include the correct ACL
        assert 'ACL' in options
        assert options['ACL'] == DEFAULT_STORAGE_OPTIONS.acl

    def test_get_storage_options_with_content_type(self):
        """Test that get_storage_options includes content type when provided."""
        # Get the storage options with a content type
        content_type = 'application/pdf'
        options = get_storage_options(content_type)
        
        # Check that the content type is included
        assert 'ContentType' in options
        assert options['ContentType'] == content_type

    def test_get_storage_options_with_metadata(self):
        """Test that get_storage_options includes metadata when provided."""
        # Get the storage options with metadata
        metadata = {
            'document-id': 'test-doc-123',
            'application-id': 'app-456',
            'document-type': 'invoice'
        }
        options = get_storage_options(metadata=metadata)
        
        # Check that the metadata is included
        assert 'Metadata' in options
        assert options['Metadata'] == metadata

    def test_validate_s3_configuration_valid(self):
        """Test that validate_s3_configuration returns True for valid configuration."""
        # Patch the necessary components for a valid configuration
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.app_config') as mock_app_config, \
             patch('src.config.s3_config.S3_CLIENT_CONFIG') as mock_client_config, \
             patch('src.config.s3_config.BUCKET_CONFIGS') as mock_bucket_configs, \
             patch('src.config.s3_config.DOCUMENT_BUCKET') as mock_document_bucket:
            
            # Set up the mocks for a valid configuration
            mock_storage_options.encryption = EncryptionType.AES256
            mock_app_config.ENVIRONMENT.value = 'production'
            mock_app_config.S3_USE_SSL = True
            mock_client_config.credentials.access_key = 'test-access-key'
            mock_client_config.credentials.secret_key = 'test-secret-key'
            mock_bucket_configs = {
                'production': {
                    'name': 'mca-documents-production'
                }
            }
            mock_document_bucket = 'mca-documents-production'
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation passed
            assert result is True

    def test_validate_s3_configuration_invalid_encryption(self):
        """Test that validate_s3_configuration returns False for invalid encryption."""
        # Patch the necessary components with invalid encryption
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.logger') as mock_logger:
            
            # Set up the mocks for invalid encryption
            mock_storage_options.encryption = EncryptionType.NONE
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation failed
            assert result is False
            
            # Check that the correct error was logged
            mock_logger.error.assert_called_once_with(
                "AES-256 encryption is required for document storage"
            )

    def test_validate_s3_configuration_missing_credentials_non_dev(self):
        """Test that validate_s3_configuration returns False for missing credentials in non-dev environments."""
        # Patch the necessary components with missing credentials in production
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.app_config') as mock_app_config, \
             patch('src.config.s3_config.S3_CLIENT_CONFIG') as mock_client_config, \
             patch('src.config.s3_config.logger') as mock_logger:
            
            # Set up the mocks for missing credentials in production
            mock_storage_options.encryption = EncryptionType.AES256
            mock_app_config.ENVIRONMENT.value = 'production'
            mock_client_config.credentials.access_key = ''
            mock_client_config.credentials.secret_key = 'test-secret-key'
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation failed
            assert result is False
            
            # Check that the correct error was logged
            mock_logger.error.assert_called_once_with(
                "S3 credentials are required for non-development environments"
            )
            
            # Reset the mocks
            mock_logger.reset_mock()
            mock_client_config.credentials.access_key = 'test-access-key'
            mock_client_config.credentials.secret_key = ''
            
            # Validate again with missing secret key
            result = validate_s3_configuration()
            
            # Check that validation failed
            assert result is False
            
            # Check that the correct error was logged
            mock_logger.error.assert_called_once_with(
                "S3 credentials are required for non-development environments"
            )

    def test_validate_s3_configuration_ssl_required_non_dev(self):
        """Test that validate_s3_configuration returns False when SSL is disabled in non-dev environments."""
        # Patch the necessary components with SSL disabled in production
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.app_config') as mock_app_config, \
             patch('src.config.s3_config.S3_CLIENT_CONFIG') as mock_client_config, \
             patch('src.config.s3_config.logger') as mock_logger:
            
            # Set up the mocks for SSL disabled in production
            mock_storage_options.encryption = EncryptionType.AES256
            mock_app_config.ENVIRONMENT.value = 'production'
            mock_client_config.credentials.access_key = 'test-access-key'
            mock_client_config.credentials.secret_key = 'test-secret-key'
            mock_app_config.S3_USE_SSL = False
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation failed
            assert result is False
            
            # Check that the correct error was logged
            mock_logger.error.assert_called_once_with(
                "SSL is required for S3 connections in non-development environments"
            )

    def test_validate_s3_configuration_missing_bucket_config(self):
        """Test that validate_s3_configuration returns False for missing bucket configuration."""
        # Patch the necessary components with missing bucket configuration
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.app_config') as mock_app_config, \
             patch('src.config.s3_config.S3_CLIENT_CONFIG') as mock_client_config, \
             patch('src.config.s3_config.BUCKET_CONFIGS', {}) as mock_bucket_configs, \
             patch('src.config.s3_config.logger') as mock_logger:
            
            # Set up the mocks for missing bucket configuration
            mock_storage_options.encryption = EncryptionType.AES256
            mock_app_config.ENVIRONMENT.value = 'production'
            mock_app_config.S3_USE_SSL = True
            mock_client_config.credentials.access_key = 'test-access-key'
            mock_client_config.credentials.secret_key = 'test-secret-key'
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation failed
            assert result is False
            
            # Check that the correct error was logged
            mock_logger.error.assert_called_once_with(
                "No bucket configuration found for environment: production"
            )

    def test_validate_s3_configuration_bucket_name_mismatch(self):
        """Test that validate_s3_configuration warns for bucket name mismatch."""
        # Patch the necessary components with bucket name mismatch
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.app_config') as mock_app_config, \
             patch('src.config.s3_config.S3_CLIENT_CONFIG') as mock_client_config, \
             patch('src.config.s3_config.BUCKET_CONFIGS') as mock_bucket_configs, \
             patch('src.config.s3_config.DOCUMENT_BUCKET', 'wrong-bucket') as mock_document_bucket, \
             patch('src.config.s3_config.logger') as mock_logger:
            
            # Set up the mocks for bucket name mismatch
            mock_storage_options.encryption = EncryptionType.AES256
            mock_app_config.ENVIRONMENT.value = 'production'
            mock_app_config.S3_USE_SSL = True
            mock_client_config.credentials.access_key = 'test-access-key'
            mock_client_config.credentials.secret_key = 'test-secret-key'
            mock_bucket_configs = {
                'production': {
                    'name': 'mca-documents-production'
                }
            }
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation passed (warning only)
            assert result is True
            
            # Check that the correct warning was logged
            mock_logger.warning.assert_called_once()
            assert "Document bucket name (wrong-bucket) does not match" in mock_logger.warning.call_args[0][0]

    def test_validate_s3_configuration_exception_handling(self):
        """Test that validate_s3_configuration handles exceptions properly."""
        # Patch the necessary components to raise an exception
        with patch('src.config.s3_config.DEFAULT_STORAGE_OPTIONS') as mock_storage_options, \
             patch('src.config.s3_config.logger') as mock_logger:
            
            # Set up the mock to raise an exception
            mock_storage_options.encryption = EncryptionType.AES256
            mock_storage_options.encryption.side_effect = Exception("Test exception")
            
            # Validate the configuration
            result = validate_s3_configuration()
            
            # Check that validation failed
            assert result is False
            
            # Check that the correct error was logged
            mock_logger.error.assert_called_once()
            assert "S3 configuration validation failed:" in mock_logger.error.call_args[0][0]


class TestS3ConfigWithFixtures:
    """Test suite for S3 configuration using pytest fixtures."""

    # Import Environment enum from conftest.py
    from tests.test_config.conftest import Environment

    @pytest.mark.parametrize('env_vars', [Environment.DEVELOPMENT], indirect=True)
    def test_development_environment(self, env_vars):
        """Test S3 configuration with development environment variables."""
        # Check that the bucket name is correct for development
        assert DOCUMENT_BUCKET == 'mca-documents-staging'
        
        # Check that SSL is disabled in development
        client_config = get_s3_client_config()
        assert client_config['use_ssl'] is False
        assert client_config['verify'] is False
        
        # Check that the endpoint is correct for development
        assert client_config['endpoint_url'] == 'http://localhost:9000'

    @pytest.mark.parametrize('env_vars', [Environment.STAGING], indirect=True)
    def test_staging_environment(self, env_vars):
        """Test S3 configuration with staging environment variables."""
        # Check that the bucket name is correct for staging
        assert DOCUMENT_BUCKET == 'mca-documents-staging'
        
        # Check that SSL is enabled in staging
        client_config = get_s3_client_config()
        assert client_config['use_ssl'] is True
        assert client_config['verify'] is True
        
        # Check that the endpoint is correct for staging
        assert client_config['endpoint_url'] == 'https://s3.staging.dollarfunding.com'

    @pytest.mark.parametrize('env_vars', [Environment.PRODUCTION], indirect=True)
    def test_production_environment(self, env_vars):
        """Test S3 configuration with production environment variables."""
        # Check that the bucket name is correct for production
        assert DOCUMENT_BUCKET == 'mca-documents-production'
        
        # Check that SSL is enabled in production
        client_config = get_s3_client_config()
        assert client_config['use_ssl'] is True
        assert client_config['verify'] is True
        
        # Check that the endpoint is correct for production
        assert client_config['endpoint_url'] == 'https://s3.dollarfunding.com'

    def test_storage_options_encryption(self):
        """Test that storage options always include AES-256 encryption."""
        # Get storage options
        options = get_storage_options()
        
        # Check that AES-256 encryption is always enabled
        assert 'ServerSideEncryption' in options
        assert options['ServerSideEncryption'] == EncryptionType.AES256.value

    def test_s3_boto_config(self):
        """Test that S3_BOTO_CONFIG is correctly configured."""
        # Check that the boto3 configuration has the correct settings
        assert S3_BOTO_CONFIG.signature_version == 's3v4'
        assert S3_BOTO_CONFIG.retries['max_attempts'] == 3
        assert S3_BOTO_CONFIG.connect_timeout == 5
        assert S3_BOTO_CONFIG.read_timeout == 60
        assert S3_BOTO_CONFIG.s3['addressing_style'] == 'virtual'
        assert S3_BOTO_CONFIG.s3['payload_signing_enabled'] is True

    def test_multipart_upload_settings(self):
        """Test that multipart upload settings are correctly configured."""
        # Import the multipart upload settings
        from src.config.s3_config import MULTIPART_THRESHOLD, MULTIPART_CHUNKSIZE
        
        # Check that the multipart upload settings are correct
        assert MULTIPART_THRESHOLD == 8 * 1024 * 1024  # 8 MB
        assert MULTIPART_CHUNKSIZE == 8 * 1024 * 1024  # 8 MB

    def test_signed_url_expiration(self):
        """Test that signed URL expiration is correctly configured."""
        # Import the signed URL expiration
        from src.config.s3_config import SIGNED_URL_EXPIRATION
        
        # Check that the signed URL expiration is correct
        assert SIGNED_URL_EXPIRATION == 3600  # 1 hour