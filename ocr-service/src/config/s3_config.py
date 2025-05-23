#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
S3 Configuration for OCR Service

This module configures the S3-compatible storage client for the OCR Service to access
documents for OCR processing. It defines connection parameters, bucket settings,
encryption options, and access controls. The configuration ensures secure access to
documents in the document repository for text extraction.

Key features:
1. S3 client connection with appropriate authentication
2. AES-256 encryption for document storage
3. Environment-specific bucket configurations
4. Secure credential management
5. Connection options with appropriate timeouts and retry settings

Example:
    from config import s3_config
    
    # Get S3 client configuration
    client_config = s3_config.get_s3_client_config()
    
    # Get bucket name for current environment
    bucket_name = s3_config.get_bucket_name()
    
    # Get storage options with AES-256 encryption
    storage_options = s3_config.get_storage_options('application/pdf')
"""

import os
import logging
from typing import Dict, Any, Optional, Union, cast
from botocore.config import Config

from ..types.storage import (
    S3ClientConfig,
    S3Credentials,
    StorageOptions,
    EncryptionType,
    StorageClass,
    BUCKET_CONFIGS
)
from .app_config import app_config
from ..utils.logging_utils import get_logger

# Configure logging
logger = get_logger(__name__)

# S3 bucket names
DOCUMENT_BUCKET = app_config.S3_BUCKET
EXTRACTED_DATA_BUCKET = f"{app_config.S3_BUCKET}-extracted"

# Default storage options
DEFAULT_STORAGE_OPTIONS = StorageOptions(
    encryption=EncryptionType.AES256,
    storage_class=StorageClass.STANDARD,
    metadata={},
    content_type=None,
    content_disposition=None,
    cache_control="private, max-age=0",
    tags={},
    acl="private"
)

# Signed URL expiration (1 hour)
SIGNED_URL_EXPIRATION = 3600

# Multipart upload settings
MULTIPART_THRESHOLD = 8 * 1024 * 1024  # 8 MB
MULTIPART_CHUNKSIZE = 8 * 1024 * 1024  # 8 MB

# S3 client configuration
S3_CLIENT_CONFIG = S3ClientConfig(
    endpoint_url=app_config.S3_ENDPOINT,
    region=app_config.S3_REGION,
    credentials=S3Credentials(
        access_key=app_config.S3_ACCESS_KEY,
        secret_key=app_config.S3_SECRET_KEY
    ),
    verify_ssl=app_config.S3_VERIFY_SSL,
    use_path_style=False,  # Use virtual hosted-style addressing by default
    max_pool_connections=10,
    timeout=60,
    retries=3
)

# Boto3 configuration with retry settings
S3_BOTO_CONFIG = Config(
    region_name=app_config.S3_REGION,
    signature_version='s3v4',
    retries={
        'max_attempts': 3,
        'mode': 'standard'
    },
    connect_timeout=5,
    read_timeout=60,
    max_pool_connections=10,
    s3={
        'addressing_style': 'virtual',  # Use virtual hosted-style addressing
        'payload_signing_enabled': True,
        'use_accelerate_endpoint': False
    }
)


def get_bucket_name(bucket_type: str = 'document') -> str:
    """
    Get the appropriate bucket name based on the current environment.
    
    Args:
        bucket_type: Type of bucket ('document' or 'extracted')
        
    Returns:
        str: Bucket name for the current environment
    """
    if bucket_type == 'extracted':
        return EXTRACTED_DATA_BUCKET
    else:
        return DOCUMENT_BUCKET


def get_s3_client_config() -> Dict[str, Any]:
    """
    Get the S3 client configuration for boto3.client().
    
    Returns:
        Dict[str, Any]: Configuration dictionary for boto3.client()
    """
    config = {
        'endpoint_url': S3_CLIENT_CONFIG.endpoint_url,
        'region_name': S3_CLIENT_CONFIG.region,
        'aws_access_key_id': S3_CLIENT_CONFIG.credentials.access_key,
        'aws_secret_access_key': S3_CLIENT_CONFIG.credentials.secret_key,
        'verify': S3_CLIENT_CONFIG.verify_ssl,
        'use_ssl': app_config.S3_USE_SSL
    }
    
    # Add session token if available
    if S3_CLIENT_CONFIG.credentials.session_token:
        config['aws_session_token'] = S3_CLIENT_CONFIG.credentials.session_token
    
    # Log configuration (without sensitive data)
    logger.debug(
        f"S3 client configuration: endpoint={config['endpoint_url']}, "
        f"region={config['region_name']}, verify_ssl={config['verify']}, "
        f"use_ssl={config['use_ssl']}"
    )
    
    return config


def get_storage_options(content_type: Optional[str] = None, 
                      metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    Get storage options for S3 operations with AES-256 encryption.
    
    Args:
        content_type: Content type of the document (optional)
        metadata: Document metadata (optional)
        
    Returns:
        Dict[str, Any]: Storage options for S3 operations
    """
    options = {}
    
    # Set server-side encryption
    options['ServerSideEncryption'] = DEFAULT_STORAGE_OPTIONS.encryption.value
    
    # Set storage class
    options['StorageClass'] = DEFAULT_STORAGE_OPTIONS.storage_class.value
    
    # Set content type if provided
    if content_type:
        options['ContentType'] = content_type
    
    # Set metadata if provided
    if metadata:
        options['Metadata'] = metadata
    
    # Set cache control
    if DEFAULT_STORAGE_OPTIONS.cache_control:
        options['CacheControl'] = DEFAULT_STORAGE_OPTIONS.cache_control
    
    # Set content disposition if provided
    if DEFAULT_STORAGE_OPTIONS.content_disposition:
        options['ContentDisposition'] = DEFAULT_STORAGE_OPTIONS.content_disposition
    
    # Set ACL if provided
    if DEFAULT_STORAGE_OPTIONS.acl:
        options['ACL'] = DEFAULT_STORAGE_OPTIONS.acl
    
    # Set tags if provided
    if DEFAULT_STORAGE_OPTIONS.tags:
        tag_set = [{'Key': k, 'Value': v} for k, v in DEFAULT_STORAGE_OPTIONS.tags.items()]
        options['Tagging'] = '&'.join([f"{tag['Key']}={tag['Value']}" for tag in tag_set])
    
    return options


def validate_s3_configuration() -> bool:
    """
    Validate the S3 configuration to ensure it meets security requirements.
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    try:
        # Check if encryption is enabled
        if DEFAULT_STORAGE_OPTIONS.encryption != EncryptionType.AES256:
            logger.error("AES-256 encryption is required for document storage")
            return False
        
        # Check if credentials are provided for non-development environments
        if app_config.ENVIRONMENT.value != 'development':
            if not S3_CLIENT_CONFIG.credentials.access_key or not S3_CLIENT_CONFIG.credentials.secret_key:
                logger.error("S3 credentials are required for non-development environments")
                return False
        
        # Check if SSL is enabled for non-development environments
        if app_config.ENVIRONMENT.value != 'development' and not app_config.S3_USE_SSL:
            logger.error("SSL is required for S3 connections in non-development environments")
            return False
        
        # Check if bucket exists in configuration
        env = app_config.ENVIRONMENT.value
        if env not in BUCKET_CONFIGS:
            logger.error(f"No bucket configuration found for environment: {env}")
            return False
        
        # Check if bucket name matches configuration
        expected_bucket = BUCKET_CONFIGS[env]['name']
        if DOCUMENT_BUCKET != expected_bucket:
            logger.warning(
                f"Document bucket name ({DOCUMENT_BUCKET}) does not match "
                f"expected value for {env} environment ({expected_bucket})"
            )
        
        logger.info("S3 configuration validation successful")
        return True
        
    except Exception as e:
        logger.error(f"S3 configuration validation failed: {str(e)}")
        return False


# Validate configuration on module import
if not validate_s3_configuration():
    logger.warning("S3 configuration validation failed, service may not function correctly")