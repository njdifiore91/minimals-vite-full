"""
Type definitions for Document Service configuration.

This module provides type definitions for service configuration, ensuring consistent
and type-safe access to configuration values throughout the codebase.
"""

from typing import Dict, List, Optional, Union, TypedDict, Literal, Any, TypeVar, cast
from pathlib import Path

# Type alias for configuration dictionaries
ConfigDict = Dict[str, Any]

# Environment type
EnvironmentType = Literal['development', 'staging', 'production']


class ServiceConfig(TypedDict):
    """Application-wide service configuration."""
    name: str
    version: str
    environment: EnvironmentType
    host: str
    port: int
    debug: bool
    api_prefix: str
    allowed_origins: List[str]


class ModelConfig(TypedDict):
    """Configuration for scikit-learn document classification models."""
    model_path: str
    vectorizer_path: str
    min_confidence_threshold: float
    supported_document_types: List[str]
    batch_size: int
    max_document_size_mb: int
    gpu_acceleration: bool
    memory_limit_mb: int  # Minimum 16GB RAM required as per spec


class RabbitMQConfig(TypedDict):
    """Configuration for RabbitMQ message queue."""
    host: str
    port: int
    username: str
    password: str
    vhost: str
    exchange: str
    queue_document_processing: str
    queue_data_extraction: str
    routing_key: str
    ssl: bool
    ssl_cert_path: Optional[str]
    ssl_key_path: Optional[str]
    ssl_ca_certs: Optional[str]
    heartbeat: int
    connection_timeout: int
    prefetch_count: int


class S3Config(TypedDict):
    """Configuration for S3-compatible document storage."""
    endpoint_url: str
    region_name: str
    access_key_id: str
    secret_access_key: str
    bucket_name: str
    use_ssl: bool
    verify: bool
    encryption: Literal['AES256']
    presigned_url_expiration: int  # in seconds
    max_pool_connections: int


class LoggingConfig(TypedDict):
    """Configuration for structured logging."""
    level: Literal['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
    format: str
    date_format: str
    file_path: Optional[str]
    max_bytes: int
    backup_count: int
    json_format: bool
    include_correlation_id: bool


class AppConfig(TypedDict):
    """Complete application configuration."""
    service: ServiceConfig
    model: ModelConfig
    rabbitmq: RabbitMQConfig
    s3: S3Config
    logging: LoggingConfig


# Helper function for environment variable validation
def validate_config(config: AppConfig) -> AppConfig:
    """Validate the application configuration.
    
    Args:
        config: The application configuration to validate.
        
    Returns:
        The validated configuration.
        
    Raises:
        ValueError: If the configuration is invalid.
    """
    # Validate service configuration
    if config['service']['environment'] not in ['development', 'staging', 'production']:
        raise ValueError(f"Invalid environment: {config['service']['environment']}")
    
    # Validate model configuration
    if config['model']['min_confidence_threshold'] < 0 or config['model']['min_confidence_threshold'] > 1:
        raise ValueError(f"Invalid confidence threshold: {config['model']['min_confidence_threshold']}")
    
    if config['model']['memory_limit_mb'] < 16384:  # 16GB minimum as per spec
        raise ValueError(f"Memory limit below required 16GB: {config['model']['memory_limit_mb']}MB")
    
    # Validate S3 configuration
    if config['s3']['encryption'] != 'AES256':
        raise ValueError(f"Invalid encryption type: {config['s3']['encryption']}. Must be AES256.")
    
    # Validate RabbitMQ configuration
    if config['rabbitmq']['ssl']:
        if not all([config['rabbitmq']['ssl_cert_path'], 
                   config['rabbitmq']['ssl_key_path'], 
                   config['rabbitmq']['ssl_ca_certs']]):
            raise ValueError("SSL is enabled but certificate paths are not properly configured")
    
    return config