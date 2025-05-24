#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Type definitions for OCR Service configuration.

This module provides type definitions for service configuration, ensuring consistent
and type-safe access to configuration values throughout the codebase. It includes
types for TensorFlow model configuration, RabbitMQ connection parameters, and S3
storage settings.
"""

from typing import Dict, List, Optional, Union, TypedDict, Literal, TypeVar, Any
from enum import Enum

# Type alias for configuration dictionaries
ConfigDict = Dict[str, Any]


class EnvironmentType(str, Enum):
    """Supported environment types for the OCR Service."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Log levels for the OCR Service."""
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


class ServiceConfig(TypedDict, total=False):
    """Application-wide settings for the OCR Service.
    
    Attributes:
        name: The name of the service
        version: The version of the service
        port: The port the service listens on
        environment: The environment the service is running in
        debug: Whether debug mode is enabled
        correlation_id_header: The header name for correlation IDs
    """
    name: str
    version: str
    port: int
    environment: EnvironmentType
    debug: bool
    correlation_id_header: str


class GPUSettings(TypedDict, total=False):
    """GPU settings for TensorFlow.
    
    Attributes:
        memory_limit: Memory limit for GPU in MB
        allow_growth: Whether to allow GPU memory growth
        visible_devices: List of visible GPU devices
        per_process_gpu_memory_fraction: Fraction of GPU memory to use
    """
    memory_limit: int
    allow_growth: bool
    visible_devices: List[int]
    per_process_gpu_memory_fraction: float


class ModelSettings(TypedDict, total=False):
    """Settings for a TensorFlow model.
    
    Attributes:
        path: Path to the model file
        version: Version of the model
        batch_size: Batch size for inference
        confidence_threshold: Minimum confidence threshold for predictions
        input_shape: Input shape for the model
        max_text_length: Maximum text length for OCR
    """
    path: str
    version: str
    batch_size: int
    confidence_threshold: float
    input_shape: List[int]
    max_text_length: int


class TensorFlowConfig(TypedDict, total=False):
    """Configuration for TensorFlow and OCR models.
    
    Attributes:
        version: TensorFlow version
        gpu: GPU settings
        models: Dictionary of model configurations
        typed_text_model: Settings for typed text OCR model
        handwritten_text_model: Settings for handwritten text OCR model
        hybrid_model: Settings for hybrid OCR model
        enable_gpu: Whether to enable GPU acceleration
        cuda_visible_devices: CUDA visible devices environment variable value
    """
    version: str
    gpu: GPUSettings
    models: Dict[str, ModelSettings]
    typed_text_model: ModelSettings
    handwritten_text_model: ModelSettings
    hybrid_model: ModelSettings
    enable_gpu: bool
    cuda_visible_devices: str


class RabbitMQCredentials(TypedDict, total=False):
    """Credentials for RabbitMQ connection.
    
    Attributes:
        username: RabbitMQ username
        password: RabbitMQ password
        client_cert_path: Path to client certificate for TLS
        client_key_path: Path to client key for TLS
        ca_cert_path: Path to CA certificate for TLS
    """
    username: str
    password: str
    client_cert_path: str
    client_key_path: str
    ca_cert_path: str


class RabbitMQExchange(TypedDict, total=False):
    """Configuration for a RabbitMQ exchange.
    
    Attributes:
        name: Exchange name
        type: Exchange type (direct, fanout, topic, headers)
        durable: Whether the exchange is durable
        auto_delete: Whether the exchange is auto-deleted
    """
    name: str
    type: Literal["direct", "fanout", "topic", "headers"]
    durable: bool
    auto_delete: bool


class RabbitMQQueue(TypedDict, total=False):
    """Configuration for a RabbitMQ queue.
    
    Attributes:
        name: Queue name
        durable: Whether the queue is durable
        exclusive: Whether the queue is exclusive
        auto_delete: Whether the queue is auto-deleted
        arguments: Additional queue arguments
    """
    name: str
    durable: bool
    exclusive: bool
    auto_delete: bool
    arguments: Dict[str, Any]


class RabbitMQConfig(TypedDict, total=False):
    """Configuration for RabbitMQ connection and channels.
    
    Attributes:
        host: RabbitMQ host
        port: RabbitMQ port
        virtual_host: RabbitMQ virtual host
        credentials: RabbitMQ credentials
        connection_attempts: Number of connection attempts
        retry_delay: Delay between connection attempts in seconds
        heartbeat: Heartbeat interval in seconds
        blocked_connection_timeout: Timeout for blocked connections
        ssl: Whether to use SSL/TLS
        ssl_options: SSL/TLS options
        exchange: Exchange configuration
        queue: Queue configuration
        prefetch_count: Prefetch count for consumer
    """
    host: str
    port: int
    virtual_host: str
    credentials: RabbitMQCredentials
    connection_attempts: int
    retry_delay: int
    heartbeat: int
    blocked_connection_timeout: int
    ssl: bool
    ssl_options: Dict[str, Any]
    exchange: RabbitMQExchange
    queue: RabbitMQQueue
    prefetch_count: int


class S3Credentials(TypedDict, total=False):
    """Credentials for S3 connection.
    
    Attributes:
        access_key: S3 access key
        secret_key: S3 secret key
        session_token: S3 session token
    """
    access_key: str
    secret_key: str
    session_token: Optional[str]


class S3Encryption(TypedDict, total=False):
    """Encryption settings for S3.
    
    Attributes:
        algorithm: Encryption algorithm (AES256, aws:kms)
        kms_key_id: KMS key ID for aws:kms encryption
    """
    algorithm: Literal["AES256", "aws:kms"]
    kms_key_id: Optional[str]


class S3Bucket(TypedDict, total=False):
    """Configuration for an S3 bucket.
    
    Attributes:
        name: Bucket name
        region: Bucket region
        prefix: Key prefix for objects
    """
    name: str
    region: str
    prefix: str


class S3Config(TypedDict, total=False):
    """Configuration for S3-compatible storage.
    
    Attributes:
        endpoint_url: S3 endpoint URL
        region: S3 region
        credentials: S3 credentials
        buckets: Dictionary of bucket configurations by environment
        encryption: S3 encryption settings
        use_ssl: Whether to use SSL/TLS
        verify: Whether to verify SSL certificates
        timeout: Connection timeout in seconds
        max_pool_connections: Maximum number of connections in the connection pool
    """
    endpoint_url: str
    region: str
    credentials: S3Credentials
    buckets: Dict[EnvironmentType, S3Bucket]
    encryption: S3Encryption
    use_ssl: bool
    verify: bool
    timeout: int
    max_pool_connections: int


class LogHandler(TypedDict, total=False):
    """Configuration for a log handler.
    
    Attributes:
        type: Handler type (console, file, syslog)
        level: Log level
        format: Log format
        filename: Filename for file handler
        maxBytes: Maximum file size for rotating file handler
        backupCount: Number of backup files for rotating file handler
    """
    type: Literal["console", "file", "syslog"]
    level: LogLevel
    format: str
    filename: Optional[str]
    maxBytes: Optional[int]
    backupCount: Optional[int]


class LoggingConfig(TypedDict, total=False):
    """Configuration for logging.
    
    Attributes:
        level: Default log level
        handlers: List of log handlers
        format: Default log format
        include_correlation_id: Whether to include correlation ID in logs
        include_timestamp: Whether to include timestamp in logs
        include_service_info: Whether to include service info in logs
    """
    level: LogLevel
    handlers: List[LogHandler]
    format: str
    include_correlation_id: bool
    include_timestamp: bool
    include_service_info: bool


class AppConfig(TypedDict, total=False):
    """Complete application configuration.
    
    Attributes:
        service: Service configuration
        tensorflow: TensorFlow configuration
        rabbitmq: RabbitMQ configuration
        s3: S3 configuration
        logging: Logging configuration
    """
    service: ServiceConfig
    tensorflow: TensorFlowConfig
    rabbitmq: RabbitMQConfig
    s3: S3Config
    logging: LoggingConfig