"""
S3 Configuration Module for Document Service.

This module configures the S3-compatible storage client for the Document Service
to store and retrieve documents. It defines connection parameters, bucket settings,
encryption options, and access controls.
"""

import os
import logging
from typing import Dict, Optional, Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger(__name__)

# Environment variables
ENV = os.environ.get('ENVIRONMENT', 'development')
S3_ENDPOINT = os.environ.get('S3_ENDPOINT', None)
S3_REGION = os.environ.get('S3_REGION', 'us-east-1')
S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY', None)
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY', None)
S3_BUCKET_PREFIX = os.environ.get('S3_BUCKET_PREFIX', 'mca-documents')

# Default configuration values
DEFAULT_TIMEOUT = 60  # seconds
MAX_RETRIES = 3
RETRY_MODE = 'standard'

# Bucket names for different environments
BUCKET_NAMES = {
    'production': f"{S3_BUCKET_PREFIX}-production",
    'staging': f"{S3_BUCKET_PREFIX}-staging",
    'development': f"{S3_BUCKET_PREFIX}-development",
    'test': f"{S3_BUCKET_PREFIX}-test"
}


def get_bucket_name() -> str:
    """Get the appropriate bucket name based on the current environment.

    Returns:
        str: The bucket name for the current environment.
    """
    return BUCKET_NAMES.get(ENV, BUCKET_NAMES['development'])


def get_s3_config() -> Config:
    """Create and return the S3 client configuration with appropriate settings.

    Returns:
        Config: Boto3 configuration object with retry settings.
    """
    return Config(
        retries={
            'max_attempts': MAX_RETRIES,
            'mode': RETRY_MODE
        },
        connect_timeout=DEFAULT_TIMEOUT,
        read_timeout=DEFAULT_TIMEOUT,
        parameter_validation=True,
        s3={
            'addressing_style': 'path'
        }
    )


def create_s3_client() -> boto3.client:
    """Create and return an S3 client with the appropriate configuration.

    Returns:
        boto3.client: Configured S3 client.

    Raises:
        Exception: If there's an error creating the S3 client.
    """
    try:
        # Create client configuration
        config = get_s3_config()
        
        # Create client with credentials if provided
        client_kwargs = {
            'service_name': 's3',
            'region_name': S3_REGION,
            'config': config
        }
        
        # Add endpoint URL if specified
        if S3_ENDPOINT:
            client_kwargs['endpoint_url'] = S3_ENDPOINT
            
        # Add credentials if provided
        if S3_ACCESS_KEY and S3_SECRET_KEY:
            client_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
            client_kwargs['aws_secret_access_key'] = S3_SECRET_KEY
        
        # Create the client
        client = boto3.client(**client_kwargs)
        
        logger.info(f"S3 client created successfully for region {S3_REGION}")
        return client
    except Exception as e:
        logger.error(f"Error creating S3 client: {str(e)}")
        raise


def create_s3_resource() -> boto3.resource:
    """Create and return an S3 resource with the appropriate configuration.

    Returns:
        boto3.resource: Configured S3 resource.

    Raises:
        Exception: If there's an error creating the S3 resource.
    """
    try:
        # Create client configuration
        config = get_s3_config()
        
        # Create resource with credentials if provided
        resource_kwargs = {
            'service_name': 's3',
            'region_name': S3_REGION,
            'config': config
        }
        
        # Add endpoint URL if specified
        if S3_ENDPOINT:
            resource_kwargs['endpoint_url'] = S3_ENDPOINT
            
        # Add credentials if provided
        if S3_ACCESS_KEY and S3_SECRET_KEY:
            resource_kwargs['aws_access_key_id'] = S3_ACCESS_KEY
            resource_kwargs['aws_secret_access_key'] = S3_SECRET_KEY
        
        # Create the resource
        resource = boto3.resource(**resource_kwargs)
        
        logger.info(f"S3 resource created successfully for region {S3_REGION}")
        return resource
    except Exception as e:
        logger.error(f"Error creating S3 resource: {str(e)}")
        raise


def upload_file_with_encryption(file_path: str, object_key: str, metadata: Optional[Dict[str, str]] = None) -> bool:
    """Upload a file to S3 with server-side encryption.

    Args:
        file_path (str): Path to the file to upload.
        object_key (str): S3 object key for the uploaded file.
        metadata (Optional[Dict[str, str]], optional): Metadata to attach to the object. Defaults to None.

    Returns:
        bool: True if upload was successful, False otherwise.
    """
    try:
        s3_client = create_s3_client()
        bucket_name = get_bucket_name()
        
        # Prepare extra arguments for upload
        extra_args = {
            'ServerSideEncryption': 'AES256',  # Enable AES-256 encryption
        }
        
        # Add metadata if provided
        if metadata:
            extra_args['Metadata'] = metadata
        
        # Upload the file with encryption
        s3_client.upload_file(
            Filename=file_path,
            Bucket=bucket_name,
            Key=object_key,
            ExtraArgs=extra_args
        )
        
        logger.info(f"Successfully uploaded {file_path} to {bucket_name}/{object_key} with encryption")
        return True
    except ClientError as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error uploading file to S3: {str(e)}")
        return False


def download_file(object_key: str, download_path: str) -> bool:
    """Download a file from S3.

    Args:
        object_key (str): S3 object key to download.
        download_path (str): Local path where the file should be saved.

    Returns:
        bool: True if download was successful, False otherwise.
    """
    try:
        s3_client = create_s3_client()
        bucket_name = get_bucket_name()
        
        # Download the file
        s3_client.download_file(
            Bucket=bucket_name,
            Key=object_key,
            Filename=download_path
        )
        
        logger.info(f"Successfully downloaded {bucket_name}/{object_key} to {download_path}")
        return True
    except ClientError as e:
        logger.error(f"Error downloading file from S3: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error downloading file from S3: {str(e)}")
        return False


def check_bucket_exists(bucket_name: Optional[str] = None) -> bool:
    """Check if the specified bucket exists.

    Args:
        bucket_name (Optional[str], optional): Name of the bucket to check. 
            If None, uses the default bucket for the current environment. Defaults to None.

    Returns:
        bool: True if the bucket exists, False otherwise.
    """
    try:
        s3_client = create_s3_client()
        bucket = bucket_name or get_bucket_name()
        
        # Check if bucket exists by listing it
        s3_client.head_bucket(Bucket=bucket)
        logger.info(f"Bucket {bucket} exists")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == '404' or error_code == 'NoSuchBucket':
            logger.warning(f"Bucket {bucket} does not exist")
        else:
            logger.error(f"Error checking bucket {bucket}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error checking bucket: {str(e)}")
        return False


def create_bucket_if_not_exists(bucket_name: Optional[str] = None) -> bool:
    """Create the specified bucket if it doesn't exist.

    Args:
        bucket_name (Optional[str], optional): Name of the bucket to create. 
            If None, uses the default bucket for the current environment. Defaults to None.

    Returns:
        bool: True if the bucket exists or was created successfully, False otherwise.
    """
    try:
        bucket = bucket_name or get_bucket_name()
        
        # Check if bucket already exists
        if check_bucket_exists(bucket):
            return True
        
        # Create the bucket with encryption
        s3_client = create_s3_client()
        create_bucket_args = {
            'Bucket': bucket
        }
        
        # Add region configuration if not using the default region
        if S3_REGION != 'us-east-1':
            create_bucket_args['CreateBucketConfiguration'] = {
                'LocationConstraint': S3_REGION
            }
        
        # Create the bucket
        s3_client.create_bucket(**create_bucket_args)
        
        # Enable default encryption on the bucket
        s3_client.put_bucket_encryption(
            Bucket=bucket,
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
        
        logger.info(f"Successfully created bucket {bucket} with encryption")
        return True
    except ClientError as e:
        logger.error(f"Error creating bucket: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error creating bucket: {str(e)}")
        return False


# Initialize S3 client and resource as module-level variables for reuse
try:
    s3_client = create_s3_client()
    s3_resource = create_s3_resource()
    logger.info("S3 client and resource initialized successfully")
    
    # Ensure the default bucket exists
    default_bucket = get_bucket_name()
    if not check_bucket_exists(default_bucket):
        logger.warning(f"Default bucket {default_bucket} does not exist. It should be created before using the service.")
except Exception as e:
    logger.error(f"Failed to initialize S3 client and resource: {str(e)}")
    logger.warning("S3 operations will fail until configuration issues are resolved")