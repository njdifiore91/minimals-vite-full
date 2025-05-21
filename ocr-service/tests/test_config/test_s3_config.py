#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service's s3_config.py module.

These tests verify that S3 configuration correctly sets up connection parameters,
bucket settings, encryption options, and access controls. They ensure that
document storage works correctly with proper security measures.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, Any

# Import the module to test
from src.config.s3_config import (
    ENV_VAR_ENVIRONMENT,
    ENV_VAR_S3_ENDPOINT,
    ENV_VAR_AWS_REGION,
    ENV_VAR_AWS_ACCESS_KEY,
    ENV_VAR_AWS_SECRET_KEY,
    ENV_VAR_AWS_SESSION_TOKEN,
    ENV_VAR_DOCUMENT_BUCKET,
    ENV_VAR_EXTRACTED_DATA_BUCKET,
    DEFAULT_ENVIRONMENT,
    DEFAULT_REGION,
    DEFAULT_TIMEOUT,
    DEFAULT_MAX_ATTEMPTS,
    DEFAULT_CONNECT_TIMEOUT,
    DEFAULT_READ_TIMEOUT,
    ENVIRONMENT,
    BUCKET_CONFIG,
    DOCUMENT_BUCKET,
    EXTRACTED_DATA_BUCKET,
    S3_ENDPOINT_URL,
    AWS_REGION,
    S3_CLIENT_CONFIG,
    S3_BOTO_CONFIG,
    DEFAULT_STORAGE_OPTIONS,
    SIGNED_URL_EXPIRATION,
    MULTIPART_THRESHOLD,
    MULTIPART_CHUNKSIZE,
    DOCUMENT_PATH_PREFIX,
    EXTRACTED_DATA_PATH_PREFIX,
    THUMBNAIL_PATH_PREFIX,
    get_bucket_name,
    get_s3_client_config,
    validate_s3_configuration,
    get_storage_options,
    BUCKETS
)

from src.types.storage import BUCKET_CONFIGS, StorageOptions


# ===== Test Constants and Default Values =====

def test_environment_variable_names():
    """
    Test that environment variable names are correctly defined.
    """
    assert ENV_VAR_ENVIRONMENT == 'OCR_ENVIRONMENT'
    assert ENV_VAR_S3_ENDPOINT == 'S3_ENDPOINT_URL'
    assert ENV_VAR_AWS_REGION == 'AWS_REGION'
    assert ENV_VAR_AWS_ACCESS_KEY == 'AWS_ACCESS_KEY_ID'
    assert ENV_VAR_AWS_SECRET_KEY == 'AWS_SECRET_ACCESS_KEY'
    assert ENV_VAR_AWS_SESSION_TOKEN == 'AWS_SESSION_TOKEN'
    assert ENV_VAR_DOCUMENT_BUCKET == 'OCR_DOCUMENT_BUCKET'
    assert ENV_VAR_EXTRACTED_DATA_BUCKET == 'OCR_EXTRACTED_DATA_BUCKET'


def test_default_values():
    """
    Test that default values are correctly defined.
    """
    assert DEFAULT_ENVIRONMENT == 'development'
    assert DEFAULT_REGION == 'us-east-1'
    assert DEFAULT_TIMEOUT == 60
    assert DEFAULT_MAX_ATTEMPTS == 3
    assert DEFAULT_CONNECT_TIMEOUT == 10
    assert DEFAULT_READ_TIMEOUT == 60


def test_storage_path_prefixes():
    """
    Test that storage path prefixes are correctly defined.
    """
    assert DOCUMENT_PATH_PREFIX == 'documents/'
    assert EXTRACTED_DATA_PATH_PREFIX == 'extracted_data/'
    assert THUMBNAIL_PATH_PREFIX == 'thumbnails/'


def test_multipart_upload_configuration():
    """
    Test that multipart upload configuration is correctly defined.
    """
    assert MULTIPART_THRESHOLD == 100 * 1024 * 1024  # 100 MB
    assert MULTIPART_CHUNKSIZE == 25 * 1024 * 1024  # 25 MB


def test_signed_url_expiration():
    """
    Test that signed URL expiration is correctly defined.
    """
    assert SIGNED_URL_EXPIRATION == 15 * 60  # 15 minutes


# ===== Test Environment-Specific Bucket Configurations =====

def test_bucket_configs_structure():
    """
    Test that BUCKET_CONFIGS contains the correct environments and structure.
    """
    assert 'development' in BUCKET_CONFIGS
    assert 'staging' in BUCKET_CONFIGS
    assert 'production' in BUCKET_CONFIGS
    
    for env in ['development', 'staging', 'production']:
        assert 'name' in BUCKET_CONFIGS[env]
        assert 'region' in BUCKET_CONFIGS[env]
        assert 'encryption' in BUCKET_CONFIGS[env]
        assert 'kms_key_id' in BUCKET_CONFIGS[env]
        assert 'versioning' in BUCKET_CONFIGS[env]
        assert 'lifecycle_rules' in BUCKET_CONFIGS[env]
        assert 'cors_rules' in BUCKET_CONFIGS[env]
        assert 'public_access_blocked' in BUCKET_CONFIGS[env]


def test_bucket_configs_values():
    """
    Test that BUCKET_CONFIGS contains the correct values for each environment.
    """
    # Development environment
    assert BUCKET_CONFIGS['development']['name'] == 'mca-documents-development'
    assert BUCKET_CONFIGS['development']['region'] == 'us-east-1'
    assert BUCKET_CONFIGS['development']['encryption'] == 'AES256'
    assert BUCKET_CONFIGS['development']['versioning'] is True
    assert BUCKET_CONFIGS['development']['public_access_blocked'] is True
    
    # Staging environment
    assert BUCKET_CONFIGS['staging']['name'] == 'mca-documents-staging'
    assert BUCKET_CONFIGS['staging']['region'] == 'us-east-1'
    assert BUCKET_CONFIGS['staging']['encryption'] == 'AES256'
    assert BUCKET_CONFIGS['staging']['versioning'] is True
    assert BUCKET_CONFIGS['staging']['public_access_blocked'] is True
    
    # Production environment
    assert BUCKET_CONFIGS['production']['name'] == 'mca-documents-production'
    assert BUCKET_CONFIGS['production']['region'] == 'us-east-1'
    assert BUCKET_CONFIGS['production']['encryption'] == 'AES256'
    assert BUCKET_CONFIGS['production']['versioning'] is True
    assert BUCKET_CONFIGS['production']['public_access_blocked'] is True


# ===== Test Default Storage Options =====

def test_default_storage_options():
    """
    Test that DEFAULT_STORAGE_OPTIONS contains the correct values.
    """
    assert DEFAULT_STORAGE_OPTIONS['ServerSideEncryption'] == 'AES256'
    assert DEFAULT_STORAGE_OPTIONS['ContentType'] == 'application/octet-stream'
    assert DEFAULT_STORAGE_OPTIONS['ACL'] == 'private'


# ===== Test S3 Client Configuration =====

def test_s3_client_config_structure():
    """
    Test that S3_CLIENT_CONFIG contains the correct structure.
    """
    assert 'region_name' in S3_CLIENT_CONFIG
    assert 'use_ssl' in S3_CLIENT_CONFIG
    assert 'verify' in S3_CLIENT_CONFIG
    assert 'signature_version' in S3_CLIENT_CONFIG


def test_s3_boto_config():
    """
    Test that S3_BOTO_CONFIG is correctly configured.
    """
    assert S3_BOTO_CONFIG.signature_version == 's3v4'
    assert S3_BOTO_CONFIG.retries['max_attempts'] == DEFAULT_MAX_ATTEMPTS
    assert S3_BOTO_CONFIG.retries['mode'] == 'standard'
    assert S3_BOTO_CONFIG.connect_timeout == DEFAULT_CONNECT_TIMEOUT
    assert S3_BOTO_CONFIG.read_timeout == DEFAULT_READ_TIMEOUT
    assert S3_BOTO_CONFIG.region_name == AWS_REGION
    assert S3_BOTO_CONFIG.s3['addressing_style'] == 'virtual'
    assert S3_BOTO_CONFIG.s3['payload_signing_enabled'] is True


# ===== Test get_bucket_name Function =====

def test_get_bucket_name_with_valid_environment():
    """
    Test that get_bucket_name returns the correct bucket name for a valid environment.
    """
    assert get_bucket_name('development') == 'mca-documents-development'
    assert get_bucket_name('staging') == 'mca-documents-staging'
    assert get_bucket_name('production') == 'mca-documents-production'


def test_get_bucket_name_with_invalid_environment():
    """
    Test that get_bucket_name returns the default bucket name for an invalid environment.
    """
    with patch('src.config.s3_config.logger') as mock_logger:
        assert get_bucket_name('invalid') == 'mca-documents-development'
        mock_logger.warning.assert_called_once()


def test_get_bucket_name_with_default_environment():
    """
    Test that get_bucket_name uses the global ENVIRONMENT when no environment is specified.
    """
    with patch('src.config.s3_config.ENVIRONMENT', 'production'):
        assert get_bucket_name() == 'mca-documents-production'


# ===== Test get_s3_client_config Function =====

def test_get_s3_client_config_with_credentials():
    """
    Test that get_s3_client_config returns the correct configuration when credentials are available.
    """
    with patch('src.config.s3_config.S3_CLIENT_CONFIG', {
        'endpoint_url': 'https://s3.amazonaws.com',
        'region_name': 'us-east-1',
        'aws_access_key_id': 'test-access-key',
        'aws_secret_access_key': 'test-secret-key',
        'use_ssl': True,
        'verify': True,
        'signature_version': 's3v4'
    }):
        config = get_s3_client_config()
        assert config['endpoint_url'] == 'https://s3.amazonaws.com'
        assert config['region_name'] == 'us-east-1'
        assert config['aws_access_key_id'] == 'test-access-key'
        assert config['aws_secret_access_key'] == 'test-secret-key'
        assert config['use_ssl'] is True
        assert config['verify'] is True
        assert config['signature_version'] == 's3v4'


def test_get_s3_client_config_without_credentials():
    """
    Test that get_s3_client_config removes credentials when they are not available.
    """
    with patch('src.config.s3_config.S3_CLIENT_CONFIG', {
        'endpoint_url': 'https://s3.amazonaws.com',
        'region_name': 'us-east-1',
        'aws_access_key_id': '',
        'aws_secret_access_key': '',
        'use_ssl': True,
        'verify': True,
        'signature_version': 's3v4'
    }), patch('src.config.s3_config.logger') as mock_logger:
        config = get_s3_client_config()
        assert 'aws_access_key_id' not in config
        assert 'aws_secret_access_key' not in config
        assert config['endpoint_url'] == 'https://s3.amazonaws.com'
        assert config['region_name'] == 'us-east-1'
        assert config['use_ssl'] is True
        assert config['verify'] is True
        assert config['signature_version'] == 's3v4'
        mock_logger.warning.assert_called()


# ===== Test validate_s3_configuration Function =====

def test_validate_s3_configuration_valid():
    """
    Test that validate_s3_configuration returns True for a valid configuration.
    """
    with patch.multiple('src.config.s3_config',
                        ENVIRONMENT='development',
                        DOCUMENT_BUCKET='mca-documents-development',
                        EXTRACTED_DATA_BUCKET='mca-documents-development',
                        AWS_REGION='us-east-1',
                        S3_CLIENT_CONFIG={
                            'aws_access_key_id': 'test-access-key',
                            'aws_secret_access_key': 'test-secret-key'
                        }):
        assert validate_s3_configuration() is True


def test_validate_s3_configuration_invalid_environment():
    """
    Test that validate_s3_configuration returns False for an invalid environment.
    """
    with patch.multiple('src.config.s3_config',
                        ENVIRONMENT='invalid',
                        DOCUMENT_BUCKET='mca-documents-development',
                        EXTRACTED_DATA_BUCKET='mca-documents-development',
                        AWS_REGION='us-east-1',
                        S3_CLIENT_CONFIG={
                            'aws_access_key_id': 'test-access-key',
                            'aws_secret_access_key': 'test-secret-key'
                        }), \
         patch('src.config.s3_config.logger') as mock_logger:
        assert validate_s3_configuration() is False
        mock_logger.error.assert_called_with("Environment 'invalid' not found in bucket configurations")


def test_validate_s3_configuration_missing_document_bucket():
    """
    Test that validate_s3_configuration returns False when document bucket is missing.
    """
    with patch.multiple('src.config.s3_config',
                        ENVIRONMENT='development',
                        DOCUMENT_BUCKET='',
                        EXTRACTED_DATA_BUCKET='mca-documents-development',
                        AWS_REGION='us-east-1',
                        S3_CLIENT_CONFIG={
                            'aws_access_key_id': 'test-access-key',
                            'aws_secret_access_key': 'test-secret-key'
                        }), \
         patch('src.config.s3_config.logger') as mock_logger:
        assert validate_s3_configuration() is False
        mock_logger.error.assert_called_with("Document bucket not configured")


def test_validate_s3_configuration_missing_extracted_data_bucket():
    """
    Test that validate_s3_configuration returns False when extracted data bucket is missing.
    """
    with patch.multiple('src.config.s3_config',
                        ENVIRONMENT='development',
                        DOCUMENT_BUCKET='mca-documents-development',
                        EXTRACTED_DATA_BUCKET='',
                        AWS_REGION='us-east-1',
                        S3_CLIENT_CONFIG={
                            'aws_access_key_id': 'test-access-key',
                            'aws_secret_access_key': 'test-secret-key'
                        }), \
         patch('src.config.s3_config.logger') as mock_logger:
        assert validate_s3_configuration() is False
        mock_logger.error.assert_called_with("Extracted data bucket not configured")


def test_validate_s3_configuration_missing_region():
    """
    Test that validate_s3_configuration returns False when region is missing.
    """
    with patch.multiple('src.config.s3_config',
                        ENVIRONMENT='development',
                        DOCUMENT_BUCKET='mca-documents-development',
                        EXTRACTED_DATA_BUCKET='mca-documents-development',
                        AWS_REGION='',
                        S3_CLIENT_CONFIG={
                            'aws_access_key_id': 'test-access-key',
                            'aws_secret_access_key': 'test-secret-key'
                        }), \
         patch('src.config.s3_config.logger') as mock_logger:
        assert validate_s3_configuration() is False
        mock_logger.error.assert_called_with("AWS region not configured")


def test_validate_s3_configuration_missing_credentials():
    """
    Test that validate_s3_configuration warns but returns True when credentials are missing.
    """
    with patch.multiple('src.config.s3_config',
                        ENVIRONMENT='development',
                        DOCUMENT_BUCKET='mca-documents-development',
                        EXTRACTED_DATA_BUCKET='mca-documents-development',
                        AWS_REGION='us-east-1',
                        S3_CLIENT_CONFIG={
                            'aws_access_key_id': '',
                            'aws_secret_access_key': ''
                        }), \
         patch('src.config.s3_config.logger') as mock_logger:
        assert validate_s3_configuration() is True
        mock_logger.warning.assert_called_with("AWS credentials not found in environment variables")


# ===== Test get_storage_options Function =====

def test_get_storage_options_default():
    """
    Test that get_storage_options returns the default options when no parameters are provided.
    """
    options = get_storage_options()
    assert options['ServerSideEncryption'] == 'AES256'
    assert options['ContentType'] == 'application/octet-stream'
    assert options['ACL'] == 'private'
    assert 'Metadata' not in options


def test_get_storage_options_with_content_type():
    """
    Test that get_storage_options correctly sets the content type.
    """
    options = get_storage_options(content_type='application/pdf')
    assert options['ServerSideEncryption'] == 'AES256'
    assert options['ContentType'] == 'application/pdf'
    assert options['ACL'] == 'private'
    assert 'Metadata' not in options


def test_get_storage_options_with_metadata():
    """
    Test that get_storage_options correctly sets the metadata.
    """
    metadata = {
        'document_id': 'test-document-id',
        'application_id': 'test-application-id',
        'document_type': 'application'
    }
    options = get_storage_options(metadata=metadata)
    assert options['ServerSideEncryption'] == 'AES256'
    assert options['ContentType'] == 'application/octet-stream'
    assert options['ACL'] == 'private'
    assert options['Metadata'] == metadata


def test_get_storage_options_with_content_type_and_metadata():
    """
    Test that get_storage_options correctly sets both content type and metadata.
    """
    metadata = {
        'document_id': 'test-document-id',
        'application_id': 'test-application-id',
        'document_type': 'application'
    }
    options = get_storage_options(content_type='application/pdf', metadata=metadata)
    assert options['ServerSideEncryption'] == 'AES256'
    assert options['ContentType'] == 'application/pdf'
    assert options['ACL'] == 'private'
    assert options['Metadata'] == metadata


# ===== Test BUCKETS Dictionary =====

def test_buckets_dictionary():
    """
    Test that BUCKETS dictionary contains the correct values.
    """
    assert 'document' in BUCKETS
    assert 'extracted_data' in BUCKETS
    assert BUCKETS['document'] == DOCUMENT_BUCKET
    assert BUCKETS['extracted_data'] == EXTRACTED_DATA_BUCKET


# ===== Integration Tests with Environment Fixtures =====

def test_s3_config_with_dev_environment(dev_env_vars):
    """
    Test that S3 configuration is correct for development environment.
    """
    # Reload the module to apply the environment variables
    with patch.dict(os.environ, dev_env_vars):
        # We need to mock the import to avoid circular imports
        with patch('src.config.s3_config.BUCKET_CONFIGS', BUCKET_CONFIGS):
            # Import the module again to reload with new environment variables
            from importlib import reload
            import src.config.s3_config
            reload(src.config.s3_config)
            
            # Verify the configuration
            assert src.config.s3_config.ENVIRONMENT == 'development'
            assert src.config.s3_config.S3_ENDPOINT_URL == 'localhost:4566'
            assert src.config.s3_config.AWS_REGION == 'us-east-1'
            assert src.config.s3_config.DOCUMENT_BUCKET == 'mca-documents-development'
            assert src.config.s3_config.S3_CLIENT_CONFIG['endpoint_url'] == 'localhost:4566'
            assert src.config.s3_config.S3_CLIENT_CONFIG['region_name'] == 'us-east-1'
            assert src.config.s3_config.S3_CLIENT_CONFIG['aws_access_key_id'] == 'test'
            assert src.config.s3_config.S3_CLIENT_CONFIG['aws_secret_access_key'] == 'test'
            assert src.config.s3_config.S3_CLIENT_CONFIG['use_ssl'] is True


def test_s3_config_with_staging_environment(staging_env_vars):
    """
    Test that S3 configuration is correct for staging environment.
    """
    # Reload the module to apply the environment variables
    with patch.dict(os.environ, staging_env_vars):
        # We need to mock the import to avoid circular imports
        with patch('src.config.s3_config.BUCKET_CONFIGS', BUCKET_CONFIGS):
            # Import the module again to reload with new environment variables
            from importlib import reload
            import src.config.s3_config
            reload(src.config.s3_config)
            
            # Verify the configuration
            assert src.config.s3_config.ENVIRONMENT == 'staging'
            assert src.config.s3_config.S3_ENDPOINT_URL == 's3.amazonaws.com'
            assert src.config.s3_config.AWS_REGION == 'us-east-1'
            assert src.config.s3_config.DOCUMENT_BUCKET == 'mca-documents-staging'
            assert src.config.s3_config.S3_CLIENT_CONFIG['endpoint_url'] == 's3.amazonaws.com'
            assert src.config.s3_config.S3_CLIENT_CONFIG['region_name'] == 'us-east-1'
            assert src.config.s3_config.S3_CLIENT_CONFIG['aws_access_key_id'] == 'staging-access-key'
            assert src.config.s3_config.S3_CLIENT_CONFIG['aws_secret_access_key'] == 'staging-secret-key'
            assert src.config.s3_config.S3_CLIENT_CONFIG['use_ssl'] is True


def test_s3_config_with_prod_environment(prod_env_vars):
    """
    Test that S3 configuration is correct for production environment.
    """
    # Reload the module to apply the environment variables
    with patch.dict(os.environ, prod_env_vars):
        # We need to mock the import to avoid circular imports
        with patch('src.config.s3_config.BUCKET_CONFIGS', BUCKET_CONFIGS):
            # Import the module again to reload with new environment variables
            from importlib import reload
            import src.config.s3_config
            reload(src.config.s3_config)
            
            # Verify the configuration
            assert src.config.s3_config.ENVIRONMENT == 'production'
            assert src.config.s3_config.S3_ENDPOINT_URL == 's3.amazonaws.com'
            assert src.config.s3_config.AWS_REGION == 'us-east-1'
            assert src.config.s3_config.DOCUMENT_BUCKET == 'mca-documents-production'
            assert src.config.s3_config.S3_CLIENT_CONFIG['endpoint_url'] == 's3.amazonaws.com'
            assert src.config.s3_config.S3_CLIENT_CONFIG['region_name'] == 'us-east-1'
            assert src.config.s3_config.S3_CLIENT_CONFIG['aws_access_key_id'] == 'production-access-key'
            assert src.config.s3_config.S3_CLIENT_CONFIG['aws_secret_access_key'] == 'production-secret-key'
            assert src.config.s3_config.S3_CLIENT_CONFIG['use_ssl'] is True


# ===== Test Missing Environment Variables =====

def test_s3_config_with_missing_environment_variable(env_vars, clear_env_vars):
    """
    Test that S3 configuration uses defaults when environment variables are missing.
    """
    # Set up a minimal environment
    env_vars['OCR_ENVIRONMENT'] = 'development'
    
    # Clear specific environment variables
    clear_env_vars([
        'S3_ENDPOINT_URL',
        'AWS_REGION',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'OCR_DOCUMENT_BUCKET',
        'OCR_EXTRACTED_DATA_BUCKET'
    ])
    
    # Reload the module to apply the environment variables
    with patch('src.config.s3_config.BUCKET_CONFIGS', BUCKET_CONFIGS):
        # Import the module again to reload with new environment variables
        from importlib import reload
        import src.config.s3_config
        reload(src.config.s3_config)
        
        # Verify the configuration uses defaults
        assert src.config.s3_config.ENVIRONMENT == 'development'
        assert src.config.s3_config.S3_ENDPOINT_URL is None
        assert src.config.s3_config.AWS_REGION == DEFAULT_REGION
        assert src.config.s3_config.DOCUMENT_BUCKET == 'mca-documents-development'
        assert src.config.s3_config.EXTRACTED_DATA_BUCKET == 'mca-documents-development'
        assert src.config.s3_config.S3_CLIENT_CONFIG['region_name'] == DEFAULT_REGION
        assert 'endpoint_url' not in src.config.s3_config.S3_CLIENT_CONFIG
        assert src.config.s3_config.S3_CLIENT_CONFIG['aws_access_key_id'] == ''
        assert src.config.s3_config.S3_CLIENT_CONFIG['aws_secret_access_key'] == ''


# ===== Test Invalid Environment =====

def test_s3_config_with_invalid_environment(env_vars):
    """
    Test that S3 configuration defaults to development when an invalid environment is specified.
    """
    # Set an invalid environment
    env_vars['OCR_ENVIRONMENT'] = 'invalid'
    
    # Reload the module to apply the environment variables
    with patch('src.config.s3_config.logger') as mock_logger, \
         patch('src.config.s3_config.BUCKET_CONFIGS', BUCKET_CONFIGS):
        # Import the module again to reload with new environment variables
        from importlib import reload
        import src.config.s3_config
        reload(src.config.s3_config)
        
        # Verify the configuration defaults to development
        assert src.config.s3_config.ENVIRONMENT == DEFAULT_ENVIRONMENT
        mock_logger.warning.assert_called_with(
            f"Unknown environment 'invalid', defaulting to '{DEFAULT_ENVIRONMENT}'"
        )