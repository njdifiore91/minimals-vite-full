#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
S3 Configuration for OCR Service

This module configures the S3-compatible storage client for the OCR Service to access
documents for OCR processing. It defines connection parameters, bucket settings,
encryption options, and access controls. The configuration enables the service to
securely access documents from the document repository for text extraction.

Key features:
1. Environment-specific bucket configuration
2. AES-256 encryption for document storage
3. Secure credential management
4. Connection options with appropriate timeouts
5. Error handling and retry configuration
"""

import os
import logging
from typing import Dict, Optional, Any

from botocore.config import Config

from ..types.storage import S3ClientConfig, BucketConfig, StorageOptions, BUCKET_CONFIGS

# Configure logging
logger = logging.getLogger(__name__)

# Environment variable names
ENV_VAR_ENVIRONMENT = 'OCR_ENVIRONMENT'
ENV_VAR_S3_ENDPOINT = 'S3_ENDPOINT_URL'
ENV_VAR_AWS_REGION = 'AWS_REGION'
ENV_VAR_AWS_ACCESS_KEY = 'AWS_ACCESS_KEY_ID'
ENV_VAR_AWS_SECRET_KEY = 'AWS_SECRET_ACCESS_KEY'
ENV_VAR_AWS_SESSION_TOKEN = 'AWS_SESSION_TOKEN'
ENV_VAR_DOCUMENT_BUCKET = 'OCR_DOCUMENT_BUCKET'
ENV_VAR_EXTRACTED_DATA_BUCKET = 'OCR_EXTRACTED_DATA_BUCKET'

# Default values
DEFAULT_ENVIRONMENT = 'development'
DEFAULT_REGION = 'us-east-1'
DEFAULT_TIMEOUT = 60  # seconds
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_CONNECT_TIMEOUT = 10  # seconds
DEFAULT_READ_TIMEOUT = 60  # seconds

# Get current environment
ENVIRONMENT = os.environ.get(ENV_VAR_ENVIRONMENT, DEFAULT_ENVIRONMENT)

# Validate environment
if ENVIRONMENT not in BUCKET_CONFIGS:
    logger.warning(f"Unknown environment '{ENVIRONMENT}', defaulting to '{DEFAULT_ENVIRONMENT}'")
    ENVIRONMENT = DEFAULT_ENVIRONMENT

# Get bucket configuration for current environment
BUCKET_CONFIG = BUCKET_CONFIGS[ENVIRONMENT]

# Document bucket name (can be overridden by environment variable)
DOCUMENT_BUCKET = os.environ.get(ENV_VAR_DOCUMENT_BUCKET, BUCKET_CONFIG['name'])

# Extracted data bucket name (defaults to same as document bucket if not specified)
EXTRACTED_DATA_BUCKET = os.environ.get(ENV_VAR_EXTRACTED_DATA_BUCKET, DOCUMENT_BUCKET)

# S3 endpoint URL (optional, for non-AWS S3-compatible storage)
S3_ENDPOINT_URL = os.environ.get(ENV_VAR_S3_ENDPOINT)

# AWS region
AWS_REGION = os.environ.get(ENV_VAR_AWS_REGION, DEFAULT_REGION)

# Default S3 client configuration
S3_CLIENT_CONFIG: S3ClientConfig = {
    'endpoint_url': S3_ENDPOINT_URL,
    'region_name': AWS_REGION,
    'aws_access_key_id': os.environ.get(ENV_VAR_AWS_ACCESS_KEY, ''),
    'aws_secret_access_key': os.environ.get(ENV_VAR_AWS_SECRET_KEY, ''),
    'use_ssl': True,
    'verify': True,
    'signature_version': 's3v4'
}

# Remove None values from S3 client config
S3_CLIENT_CONFIG = {k: v for k, v in S3_CLIENT_CONFIG.items() if v is not None}

# Boto3 connection configuration with timeouts and retries
S3_BOTO_CONFIG = Config(
    signature_version='s3v4',
    retries={
        'max_attempts': DEFAULT_MAX_ATTEMPTS,
        'mode': 'standard'
    },
    connect_timeout=DEFAULT_CONNECT_TIMEOUT,
    read_timeout=DEFAULT_READ_TIMEOUT,
    region_name=AWS_REGION,
    s3={
        'addressing_style': 'virtual',
        'payload_signing_enabled': True
    }
)

# Default storage options with AES-256 encryption
DEFAULT_STORAGE_OPTIONS: StorageOptions = {
    'ServerSideEncryption': 'AES256',
    'ContentType': 'application/octet-stream',
    'ACL': 'private',
}

# Signed URL expiration time (15 minutes)
SIGNED_URL_EXPIRATION = 15 * 60  # seconds

# Multipart upload configuration
MULTIPART_THRESHOLD = 100 * 1024 * 1024  # 100 MB
MULTIPART_CHUNKSIZE = 25 * 1024 * 1024  # 25 MB

# Document storage paths
DOCUMENT_PATH_PREFIX = 'documents/'
EXTRACTED_DATA_PATH_PREFIX = 'extracted_data/'
THUMBNAIL_PATH_PREFIX = 'thumbnails/'


def get_bucket_name(environment: Optional[str] = None) -> str:
    """
    Get the appropriate bucket name for the specified environment.
    
    Args:
        environment: Environment name (development, staging, production)
        
    Returns:
        Bucket name for the specified environment
    """
    env = environment or ENVIRONMENT
    if env not in BUCKET_CONFIGS:
        logger.warning(f"Unknown environment '{env}', defaulting to '{DEFAULT_ENVIRONMENT}'")
        env = DEFAULT_ENVIRONMENT
    
    return BUCKET_CONFIGS[env]['name']


def get_s3_client_config() -> Dict[str, Any]:
    """
    Get the S3 client configuration with credentials.
    
    This function ensures that credentials are properly loaded from environment
    variables and returns a configuration dictionary suitable for boto3.client.
    
    Returns:
        Dict containing S3 client configuration
    """
    config = S3_CLIENT_CONFIG.copy()
    
    # Check if credentials are available
    if not config.get('aws_access_key_id') or not config.get('aws_secret_access_key'):
        logger.warning("AWS credentials not found in environment variables")
        
        # Try to load from AWS credentials file or instance profile
        # This will use the default credential provider chain
        config.pop('aws_access_key_id', None)
        config.pop('aws_secret_access_key', None)
    
    return config


def validate_s3_configuration() -> bool:
    """
    Validate the S3 configuration.
    
    This function checks that the required configuration is available and valid.
    It logs warnings for any issues found.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    valid = True
    
    # Check if bucket exists in configuration
    if ENVIRONMENT not in BUCKET_CONFIGS:
        logger.error(f"Environment '{ENVIRONMENT}' not found in bucket configurations")
        valid = False
    
    # Check if document bucket is configured
    if not DOCUMENT_BUCKET:
        logger.error("Document bucket not configured")
        valid = False
    
    # Check if extracted data bucket is configured
    if not EXTRACTED_DATA_BUCKET:
        logger.error("Extracted data bucket not configured")
        valid = False
    
    # Check if region is configured
    if not AWS_REGION:
        logger.error("AWS region not configured")
        valid = False
    
    # Check if credentials are available (warn only, not error)
    if not S3_CLIENT_CONFIG.get('aws_access_key_id') or not S3_CLIENT_CONFIG.get('aws_secret_access_key'):
        logger.warning("AWS credentials not found in environment variables")
        logger.warning("Will attempt to use instance profile or AWS credentials file")
    
    return valid


def get_storage_options(content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> StorageOptions:
    """
    Get storage options with AES-256 encryption and optional content type and metadata.
    
    Args:
        content_type: MIME type of the document
        metadata: Custom metadata to attach to the document
        
    Returns:
        StorageOptions dictionary
    """
    options = DEFAULT_STORAGE_OPTIONS.copy()
    
    if content_type:
        options['ContentType'] = content_type
    
    if metadata:
        options['Metadata'] = metadata
    
    return options


# Validate configuration on module import
if not validate_s3_configuration():
    logger.warning("S3 configuration validation failed")


# Export bucket configurations for easy access
BUCKETS = {
    'document': DOCUMENT_BUCKET,
    'extracted_data': EXTRACTED_DATA_BUCKET
}


# Log configuration summary
logger.info(f"S3 Configuration: Environment={ENVIRONMENT}, Region={AWS_REGION}")
logger.info(f"Document Bucket: {DOCUMENT_BUCKET}")
logger.info(f"Extracted Data Bucket: {EXTRACTED_DATA_BUCKET}")
if S3_ENDPOINT_URL:
    logger.info(f"S3 Endpoint URL: {S3_ENDPOINT_URL}")