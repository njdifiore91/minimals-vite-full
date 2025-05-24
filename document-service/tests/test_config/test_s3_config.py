#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's s3_config.py module.

These tests verify that S3 configuration correctly sets up connection parameters,
bucket settings, encryption options, and access controls. They ensure that document
storage works correctly with proper security measures.

Test coverage includes:
- S3 client connection configuration
- AES-256 encryption configuration
- Bucket configuration for different environments
- Credential management configuration
- Connection option configuration
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Import the module to test
from src.config.s3_config import (
    get_bucket_name,
    get_s3_config,
    create_s3_client,
    create_s3_resource,
    upload_file_with_encryption,
    download_file,
    check_bucket_exists,
    create_bucket_if_not_exists,
    BUCKET_NAMES,
    DEFAULT_TIMEOUT,
    MAX_RETRIES,
    RETRY_MODE
)


# ===== Test Bucket Name Configuration =====

@pytest.mark.parametrize(
    "environment,expected_bucket",
    [
        ("development", "mca-documents-development"),
        ("staging", "mca-documents-staging"),
        ("production", "mca-documents-production"),
        ("test", "mca-documents-test"),
        # Test fallback to development for unknown environment
        ("unknown", "mca-documents-development"),
    ],
)
def test_get_bucket_name(environment, expected_bucket, mock_env):
    """Test that the correct bucket name is returned based on the environment."""
    # Set the environment variable
    mock_env({"ENVIRONMENT": environment})
    
    # Get the bucket name
    bucket_name = get_bucket_name()
    
    # Verify the bucket name
    assert bucket_name == expected_bucket


def test_get_bucket_name_with_custom_prefix(mock_env):
    """Test that the bucket name uses a custom prefix if provided."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_BUCKET_PREFIX": "custom-prefix"
    })
    
    # Get the bucket name
    bucket_name = get_bucket_name()
    
    # Verify the bucket name
    assert bucket_name == "custom-prefix-production"


# ===== Test S3 Configuration =====

def test_get_s3_config_default_values():
    """Test that the S3 configuration has the correct default values."""
    # Get the S3 configuration
    config = get_s3_config()
    
    # Verify the configuration
    assert isinstance(config, Config)
    assert config.retries["max_attempts"] == MAX_RETRIES
    assert config.retries["mode"] == RETRY_MODE
    assert config.connect_timeout == DEFAULT_TIMEOUT
    assert config.read_timeout == DEFAULT_TIMEOUT
    assert config.parameter_validation is True
    assert config.s3["addressing_style"] == "path"


def test_get_s3_config_custom_values(monkeypatch):
    """Test that the S3 configuration can be customized with environment variables."""
    # Mock the environment variables
    monkeypatch.setenv("S3_MAX_RETRIES", "5")
    monkeypatch.setenv("S3_RETRY_MODE", "adaptive")
    monkeypatch.setenv("S3_TIMEOUT", "120")
    
    # Mock the constants
    monkeypatch.setattr("src.config.s3_config.MAX_RETRIES", 5)
    monkeypatch.setattr("src.config.s3_config.RETRY_MODE", "adaptive")
    monkeypatch.setattr("src.config.s3_config.DEFAULT_TIMEOUT", 120)
    
    # Get the S3 configuration
    config = get_s3_config()
    
    # Verify the configuration
    assert config.retries["max_attempts"] == 5
    assert config.retries["mode"] == "adaptive"
    assert config.connect_timeout == 120
    assert config.read_timeout == 120


# ===== Test S3 Client Creation =====

def test_create_s3_client_default_config(mock_env):
    """Test creating an S3 client with default configuration."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "development",
        "S3_REGION": "us-east-1"
    })
    
    # Mock boto3.client
    with patch("boto3.client") as mock_client:
        # Create the S3 client
        client = create_s3_client()
        
        # Verify the client creation
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        
        # Verify the arguments
        assert kwargs["service_name"] == "s3"
        assert kwargs["region_name"] == "us-east-1"
        assert isinstance(kwargs["config"], Config)
        
        # Verify that endpoint_url is not set
        assert "endpoint_url" not in kwargs
        
        # Verify that credentials are not set
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs


def test_create_s3_client_with_endpoint(mock_env):
    """Test creating an S3 client with a custom endpoint."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "development",
        "S3_REGION": "us-east-1",
        "S3_ENDPOINT": "http://localhost:4566"
    })
    
    # Mock boto3.client
    with patch("boto3.client") as mock_client:
        # Create the S3 client
        client = create_s3_client()
        
        # Verify the client creation
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        
        # Verify the arguments
        assert kwargs["service_name"] == "s3"
        assert kwargs["region_name"] == "us-east-1"
        assert isinstance(kwargs["config"], Config)
        
        # Verify that endpoint_url is set
        assert kwargs["endpoint_url"] == "http://localhost:4566"


def test_create_s3_client_with_credentials(mock_env):
    """Test creating an S3 client with credentials."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock boto3.client
    with patch("boto3.client") as mock_client:
        # Create the S3 client
        client = create_s3_client()
        
        # Verify the client creation
        mock_client.assert_called_once()
        args, kwargs = mock_client.call_args
        
        # Verify the arguments
        assert kwargs["service_name"] == "s3"
        assert kwargs["region_name"] == "us-east-1"
        assert isinstance(kwargs["config"], Config)
        
        # Verify that credentials are set
        assert kwargs["aws_access_key_id"] == "test-access-key"
        assert kwargs["aws_secret_access_key"] == "test-secret-key"


def test_create_s3_client_error_handling():
    """Test error handling when creating an S3 client."""
    # Mock boto3.client to raise an exception
    with patch("boto3.client", side_effect=Exception("Test error")), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to create the S3 client
        with pytest.raises(Exception, match="Test error"):
            create_s3_client()
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


# ===== Test S3 Resource Creation =====

def test_create_s3_resource_default_config(mock_env):
    """Test creating an S3 resource with default configuration."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "development",
        "S3_REGION": "us-east-1"
    })
    
    # Mock boto3.resource
    with patch("boto3.resource") as mock_resource:
        # Create the S3 resource
        resource = create_s3_resource()
        
        # Verify the resource creation
        mock_resource.assert_called_once()
        args, kwargs = mock_resource.call_args
        
        # Verify the arguments
        assert kwargs["service_name"] == "s3"
        assert kwargs["region_name"] == "us-east-1"
        assert isinstance(kwargs["config"], Config)
        
        # Verify that endpoint_url is not set
        assert "endpoint_url" not in kwargs
        
        # Verify that credentials are not set
        assert "aws_access_key_id" not in kwargs
        assert "aws_secret_access_key" not in kwargs


def test_create_s3_resource_with_endpoint(mock_env):
    """Test creating an S3 resource with a custom endpoint."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "development",
        "S3_REGION": "us-east-1",
        "S3_ENDPOINT": "http://localhost:4566"
    })
    
    # Mock boto3.resource
    with patch("boto3.resource") as mock_resource:
        # Create the S3 resource
        resource = create_s3_resource()
        
        # Verify the resource creation
        mock_resource.assert_called_once()
        args, kwargs = mock_resource.call_args
        
        # Verify the arguments
        assert kwargs["service_name"] == "s3"
        assert kwargs["region_name"] == "us-east-1"
        assert isinstance(kwargs["config"], Config)
        
        # Verify that endpoint_url is set
        assert kwargs["endpoint_url"] == "http://localhost:4566"


def test_create_s3_resource_with_credentials(mock_env):
    """Test creating an S3 resource with credentials."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock boto3.resource
    with patch("boto3.resource") as mock_resource:
        # Create the S3 resource
        resource = create_s3_resource()
        
        # Verify the resource creation
        mock_resource.assert_called_once()
        args, kwargs = mock_resource.call_args
        
        # Verify the arguments
        assert kwargs["service_name"] == "s3"
        assert kwargs["region_name"] == "us-east-1"
        assert isinstance(kwargs["config"], Config)
        
        # Verify that credentials are set
        assert kwargs["aws_access_key_id"] == "test-access-key"
        assert kwargs["aws_secret_access_key"] == "test-secret-key"


def test_create_s3_resource_error_handling():
    """Test error handling when creating an S3 resource."""
    # Mock boto3.resource to raise an exception
    with patch("boto3.resource", side_effect=Exception("Test error")), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to create the S3 resource
        with pytest.raises(Exception, match="Test error"):
            create_s3_resource()
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


# ===== Test File Upload with Encryption =====

def test_upload_file_with_encryption_success(mock_env):
    """Test successful file upload with encryption."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Upload a file with encryption
        result = upload_file_with_encryption(
            file_path="/tmp/test.pdf",
            object_key="documents/test.pdf",
            metadata={"document_type": "invoice"}
        )
        
        # Verify the result
        assert result is True
        
        # Verify that the client's upload_file method was called
        mock_client.upload_file.assert_called_once_with(
            Filename="/tmp/test.pdf",
            Bucket="mca-documents-production",
            Key="documents/test.pdf",
            ExtraArgs={
                "ServerSideEncryption": "AES256",
                "Metadata": {"document_type": "invoice"}
            }
        )
        
        # Verify that success is logged
        mock_logger.info.assert_called_once()


def test_upload_file_with_encryption_no_metadata(mock_env):
    """Test file upload with encryption but without metadata."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Upload a file with encryption but without metadata
        result = upload_file_with_encryption(
            file_path="/tmp/test.pdf",
            object_key="documents/test.pdf"
        )
        
        # Verify the result
        assert result is True
        
        # Verify that the client's upload_file method was called
        mock_client.upload_file.assert_called_once_with(
            Filename="/tmp/test.pdf",
            Bucket="mca-documents-production",
            Key="documents/test.pdf",
            ExtraArgs={
                "ServerSideEncryption": "AES256"
            }
        )
        
        # Verify that success is logged
        mock_logger.info.assert_called_once()


def test_upload_file_with_encryption_client_error(mock_env):
    """Test error handling for ClientError during file upload."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.upload_file.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "upload_file"
    )
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to upload a file
        result = upload_file_with_encryption(
            file_path="/tmp/test.pdf",
            object_key="documents/test.pdf"
        )
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


def test_upload_file_with_encryption_unexpected_error(mock_env):
    """Test error handling for unexpected errors during file upload."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.upload_file.side_effect = Exception("Unexpected error")
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to upload a file
        result = upload_file_with_encryption(
            file_path="/tmp/test.pdf",
            object_key="documents/test.pdf"
        )
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


# ===== Test File Download =====

def test_download_file_success(mock_env):
    """Test successful file download."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Download a file
        result = download_file(
            object_key="documents/test.pdf",
            download_path="/tmp/downloaded.pdf"
        )
        
        # Verify the result
        assert result is True
        
        # Verify that the client's download_file method was called
        mock_client.download_file.assert_called_once_with(
            Bucket="mca-documents-production",
            Key="documents/test.pdf",
            Filename="/tmp/downloaded.pdf"
        )
        
        # Verify that success is logged
        mock_logger.info.assert_called_once()


def test_download_file_client_error(mock_env):
    """Test error handling for ClientError during file download."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.download_file.side_effect = ClientError(
        {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
        "download_file"
    )
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to download a file
        result = download_file(
            object_key="documents/nonexistent.pdf",
            download_path="/tmp/downloaded.pdf"
        )
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


def test_download_file_unexpected_error(mock_env):
    """Test error handling for unexpected errors during file download."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.download_file.side_effect = Exception("Unexpected error")
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to download a file
        result = download_file(
            object_key="documents/test.pdf",
            download_path="/tmp/downloaded.pdf"
        )
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


# ===== Test Bucket Existence Check =====

def test_check_bucket_exists_success(mock_env):
    """Test successful bucket existence check."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Check if the bucket exists
        result = check_bucket_exists()
        
        # Verify the result
        assert result is True
        
        # Verify that the client's head_bucket method was called
        mock_client.head_bucket.assert_called_once_with(Bucket="mca-documents-production")
        
        # Verify that success is logged
        mock_logger.info.assert_called_once()


def test_check_bucket_exists_custom_bucket(mock_env):
    """Test bucket existence check with a custom bucket name."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Check if a custom bucket exists
        result = check_bucket_exists("custom-bucket")
        
        # Verify the result
        assert result is True
        
        # Verify that the client's head_bucket method was called with the custom bucket
        mock_client.head_bucket.assert_called_once_with(Bucket="custom-bucket")
        
        # Verify that success is logged
        mock_logger.info.assert_called_once()


def test_check_bucket_exists_not_found(mock_env):
    """Test bucket existence check when the bucket doesn't exist."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "404", "Message": "Not Found"}},
        "head_bucket"
    )
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Check if the bucket exists
        result = check_bucket_exists()
        
        # Verify the result
        assert result is False
        
        # Verify that the warning is logged
        mock_logger.warning.assert_called_once()


def test_check_bucket_exists_no_such_bucket(mock_env):
    """Test bucket existence check with NoSuchBucket error."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
        "head_bucket"
    )
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Check if the bucket exists
        result = check_bucket_exists()
        
        # Verify the result
        assert result is False
        
        # Verify that the warning is logged
        mock_logger.warning.assert_called_once()


def test_check_bucket_exists_other_client_error(mock_env):
    """Test bucket existence check with other ClientError."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = ClientError(
        {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
        "head_bucket"
    )
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Check if the bucket exists
        result = check_bucket_exists()
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


def test_check_bucket_exists_unexpected_error(mock_env):
    """Test bucket existence check with unexpected error."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.head_bucket.side_effect = Exception("Unexpected error")
    
    # Mock create_s3_client to return the mock client
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Check if the bucket exists
        result = check_bucket_exists()
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


# ===== Test Bucket Creation =====

def test_create_bucket_if_not_exists_already_exists(mock_env):
    """Test bucket creation when the bucket already exists."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock check_bucket_exists to return True
    with patch("src.config.s3_config.check_bucket_exists", return_value=True), \
         patch("src.config.s3_config.create_s3_client") as mock_create_client, \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"):
        
        # Create the bucket if it doesn't exist
        result = create_bucket_if_not_exists()
        
        # Verify the result
        assert result is True
        
        # Verify that create_s3_client was not called
        mock_create_client.assert_not_called()


def test_create_bucket_if_not_exists_create_success(mock_env):
    """Test successful bucket creation."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock check_bucket_exists to return False, then True
    with patch("src.config.s3_config.check_bucket_exists", side_effect=[False, True]), \
         patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Create the bucket if it doesn't exist
        result = create_bucket_if_not_exists()
        
        # Verify the result
        assert result is True
        
        # Verify that the client's create_bucket method was called
        mock_client.create_bucket.assert_called_once_with(Bucket="mca-documents-production")
        
        # Verify that the client's put_bucket_encryption method was called
        mock_client.put_bucket_encryption.assert_called_once_with(
            Bucket="mca-documents-production",
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
        
        # Verify that success is logged
        mock_logger.info.assert_called_once()


def test_create_bucket_if_not_exists_create_with_region(mock_env):
    """Test bucket creation with a non-default region."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-west-2",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock check_bucket_exists to return False, then True
    with patch("src.config.s3_config.check_bucket_exists", side_effect=[False, True]), \
         patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.S3_REGION", "us-west-2"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Create the bucket if it doesn't exist
        result = create_bucket_if_not_exists()
        
        # Verify the result
        assert result is True
        
        # Verify that the client's create_bucket method was called with region configuration
        mock_client.create_bucket.assert_called_once_with(
            Bucket="mca-documents-production",
            CreateBucketConfiguration={
                "LocationConstraint": "us-west-2"
            }
        )


def test_create_bucket_if_not_exists_custom_bucket(mock_env):
    """Test bucket creation with a custom bucket name."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    
    # Mock check_bucket_exists to return False, then True
    with patch("src.config.s3_config.check_bucket_exists", side_effect=[False, True]), \
         patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Create a custom bucket if it doesn't exist
        result = create_bucket_if_not_exists("custom-bucket")
        
        # Verify the result
        assert result is True
        
        # Verify that the client's create_bucket method was called with the custom bucket
        mock_client.create_bucket.assert_called_once_with(Bucket="custom-bucket")
        
        # Verify that the client's put_bucket_encryption method was called with the custom bucket
        mock_client.put_bucket_encryption.assert_called_once_with(
            Bucket="custom-bucket",
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


def test_create_bucket_if_not_exists_client_error(mock_env):
    """Test error handling for ClientError during bucket creation."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.create_bucket.side_effect = ClientError(
        {"Error": {"Code": "BucketAlreadyOwnedByYou", "Message": "Your previous request to create the named bucket succeeded and you already own it."}},
        "create_bucket"
    )
    
    # Mock check_bucket_exists to return False
    with patch("src.config.s3_config.check_bucket_exists", return_value=False), \
         patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to create the bucket
        result = create_bucket_if_not_exists()
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


def test_create_bucket_if_not_exists_unexpected_error(mock_env):
    """Test error handling for unexpected errors during bucket creation."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client
    mock_client = MagicMock()
    mock_client.create_bucket.side_effect = Exception("Unexpected error")
    
    # Mock check_bucket_exists to return False
    with patch("src.config.s3_config.check_bucket_exists", return_value=False), \
         patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Attempt to create the bucket
        result = create_bucket_if_not_exists()
        
        # Verify the result
        assert result is False
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()


# ===== Test Module Initialization =====

def test_module_initialization(mock_env):
    """Test that the module initializes S3 client and resource correctly."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client and resource
    mock_client = MagicMock()
    mock_resource = MagicMock()
    
    # Mock the functions
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.create_s3_resource", return_value=mock_resource), \
         patch("src.config.s3_config.check_bucket_exists", return_value=True), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Import the module to trigger initialization
        import importlib
        importlib.reload(sys.modules["src.config.s3_config"])
        
        # Verify that the functions were called
        assert sys.modules["src.config.s3_config"].create_s3_client.called
        assert sys.modules["src.config.s3_config"].create_s3_resource.called
        assert sys.modules["src.config.s3_config"].check_bucket_exists.called
        assert sys.modules["src.config.s3_config"].get_bucket_name.called
        
        # Verify that success is logged
        mock_logger.info.assert_called()


def test_module_initialization_bucket_not_exists(mock_env):
    """Test module initialization when the bucket doesn't exist."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock the S3 client and resource
    mock_client = MagicMock()
    mock_resource = MagicMock()
    
    # Mock the functions
    with patch("src.config.s3_config.create_s3_client", return_value=mock_client), \
         patch("src.config.s3_config.create_s3_resource", return_value=mock_resource), \
         patch("src.config.s3_config.check_bucket_exists", return_value=False), \
         patch("src.config.s3_config.get_bucket_name", return_value="mca-documents-production"), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Import the module to trigger initialization
        import importlib
        importlib.reload(sys.modules["src.config.s3_config"])
        
        # Verify that the warning is logged
        mock_logger.warning.assert_called_once()


def test_module_initialization_error(mock_env):
    """Test error handling during module initialization."""
    # Set the environment variables
    mock_env({
        "ENVIRONMENT": "production",
        "S3_REGION": "us-east-1",
        "S3_ACCESS_KEY": "test-access-key",
        "S3_SECRET_KEY": "test-secret-key"
    })
    
    # Mock create_s3_client to raise an exception
    with patch("src.config.s3_config.create_s3_client", side_effect=Exception("Test error")), \
         patch("src.config.s3_config.logger") as mock_logger:
        
        # Import the module to trigger initialization
        import importlib
        importlib.reload(sys.modules["src.config.s3_config"])
        
        # Verify that the error is logged
        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_called_once()