"""
Type definitions for OCR Service configuration, environment variables, and application settings.

This module provides type hints for service configuration, ensuring consistent and type-safe
access to configuration values throughout the codebase. It includes types for TensorFlow model
configuration, RabbitMQ connection parameters, and S3 storage settings.
"""

from __future__ import annotations

import enum
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TypedDict, Union, TypeVar, cast

# Type alias for configuration dictionaries
ConfigDict = Dict[str, Any]


class Environment(enum.Enum):
    """Supported deployment environments for the OCR service."""
    
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, value: Optional[str]) -> Environment:
        """Convert a string to an Environment enum value.
        
        Args:
            value: String representation of the environment
            
        Returns:
            Environment enum value
            
        Raises:
            ValueError: If the string does not match any Environment value
        """
        if not value:
            return cls.DEVELOPMENT
            
        try:
            return cls(value.lower())
        except ValueError:
            valid_values = [e.value for e in cls]
            raise ValueError(f"Invalid environment: {value}. Valid values are: {valid_values}")


@dataclass
class ServiceConfig:
    """Application-wide settings for the OCR service."""
    
    # Service identification
    name: str = "ocr-service"
    version: str = "1.0.0"
    description: str = "OCR Service for extracting data from documents"
    
    # Environment settings
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Network settings
    host: str = "0.0.0.0"
    port: int = 8000
    base_url: str = "/api/v1"
    
    # API settings
    api_timeout: int = 30  # seconds
    max_request_size: int = 50 * 1024 * 1024  # 50 MB
    
    # Concurrency settings
    worker_processes: int = 4
    thread_pool_size: int = 8
    
    # Health check settings
    health_check_interval: int = 60  # seconds
    readiness_timeout: int = 30  # seconds
    
    # Correlation ID settings
    correlation_id_header: str = "X-Correlation-ID"
    generate_correlation_id: bool = True
    
    @classmethod
    def from_env(cls) -> ServiceConfig:
        """Create a ServiceConfig instance from environment variables.
        
        Returns:
            ServiceConfig: Configuration instance with values from environment variables
        """
        env_str = os.getenv("ENVIRONMENT")
        environment = Environment.from_string(env_str)
        
        return cls(
            name=os.getenv("SERVICE_NAME", "ocr-service"),
            version=os.getenv("SERVICE_VERSION", "1.0.0"),
            description=os.getenv("SERVICE_DESCRIPTION", "OCR Service for extracting data from documents"),
            environment=environment,
            debug=os.getenv("DEBUG", "false").lower() == "true",
            host=os.getenv("SERVICE_HOST", "0.0.0.0"),
            port=int(os.getenv("SERVICE_PORT", "8000")),
            base_url=os.getenv("SERVICE_BASE_URL", "/api/v1"),
            api_timeout=int(os.getenv("API_TIMEOUT", "30")),
            max_request_size=int(os.getenv("MAX_REQUEST_SIZE", str(50 * 1024 * 1024))),
            worker_processes=int(os.getenv("WORKER_PROCESSES", "4")),
            thread_pool_size=int(os.getenv("THREAD_POOL_SIZE", "8")),
            health_check_interval=int(os.getenv("HEALTH_CHECK_INTERVAL", "60")),
            readiness_timeout=int(os.getenv("READINESS_TIMEOUT", "30")),
            correlation_id_header=os.getenv("CORRELATION_ID_HEADER", "X-Correlation-ID"),
            generate_correlation_id=os.getenv("GENERATE_CORRELATION_ID", "true").lower() == "true",
        )


@dataclass
class TensorFlowConfig:
    """Configuration for TensorFlow OCR models.
    
    This class defines the configuration for TensorFlow OCR models, including model paths,
    GPU settings, and performance parameters. It supports the requirements specified in
    section 3.2.3 of the technical specification, including GPU acceleration with at least 8GB VRAM.
    """
    
    # TensorFlow version (as specified in section 3.2.2)
    tensorflow_version: str = "2.15.0"
    
    # Model paths
    model_base_path: str = "/models"
    typed_model_path: str = "/models/typed_text_ocr"
    handwritten_model_path: str = "/models/handwritten_text_ocr"
    hybrid_model_path: str = "/models/hybrid_text_ocr"
    
    # GPU settings
    use_gpu: bool = True
    gpu_memory_limit: Optional[int] = 8192  # 8GB VRAM as specified in section 3.2.3
    gpu_allow_growth: bool = True
    mixed_precision: bool = True
    
    # Performance settings
    inter_op_parallelism_threads: int = 4
    intra_op_parallelism_threads: int = 4
    batch_size: int = 1
    
    # Model parameters
    confidence_threshold: float = 0.65
    max_text_length: int = 768
    beam_width: int = 10
    
    # Input preprocessing
    input_shape: tuple[int, int, int] = (1280, 1280, 3)  # (height, width, channels)
    normalize_input: bool = True
    
    @classmethod
    def from_env(cls) -> TensorFlowConfig:
        """Create a TensorFlowConfig instance from environment variables.
        
        Returns:
            TensorFlowConfig: Configuration instance with values from environment variables
        """
        return cls(
            tensorflow_version=os.getenv("OCR_TENSORFLOW_VERSION", "2.15.0"),
            model_base_path=os.getenv("OCR_MODEL_BASE_PATH", "/models"),
            typed_model_path=os.getenv("OCR_TYPED_MODEL_PATH", "/models/typed_text_ocr"),
            handwritten_model_path=os.getenv("OCR_HANDWRITTEN_MODEL_PATH", "/models/handwritten_text_ocr"),
            hybrid_model_path=os.getenv("OCR_HYBRID_MODEL_PATH", "/models/hybrid_text_ocr"),
            use_gpu=os.getenv("OCR_USE_GPU", "true").lower() == "true",
            gpu_memory_limit=int(os.getenv("OCR_GPU_MEMORY_LIMIT", "8192")) if os.getenv("OCR_GPU_MEMORY_LIMIT") else None,
            gpu_allow_growth=os.getenv("OCR_GPU_ALLOW_GROWTH", "true").lower() == "true",
            mixed_precision=os.getenv("OCR_MIXED_PRECISION", "true").lower() == "true",
            inter_op_parallelism_threads=int(os.getenv("OCR_INTER_OP_PARALLELISM_THREADS", "4")),
            intra_op_parallelism_threads=int(os.getenv("OCR_INTRA_OP_PARALLELISM_THREADS", "4")),
            batch_size=int(os.getenv("OCR_BATCH_SIZE", "1")),
            confidence_threshold=float(os.getenv("OCR_CONFIDENCE_THRESHOLD", "0.65")),
            max_text_length=int(os.getenv("OCR_MAX_TEXT_LENGTH", "768")),
            beam_width=int(os.getenv("OCR_BEAM_WIDTH", "10")),
            input_shape=(
                int(os.getenv("OCR_INPUT_HEIGHT", "1280")),
                int(os.getenv("OCR_INPUT_WIDTH", "1280")),
                int(os.getenv("OCR_INPUT_CHANNELS", "3")),
            ),
            normalize_input=os.getenv("OCR_NORMALIZE_INPUT", "true").lower() == "true",
        )


@dataclass
class RabbitMQConfig:
    """Configuration for RabbitMQ message queue connection.
    
    This class defines the configuration for connecting to RabbitMQ, including connection
    parameters, exchange and queue settings, and security options. It supports the requirements
    specified in section 0.1.3 and 0.2.1.2 of the technical specification for asynchronous
    message-based communication between services.
    """
    
    # Connection settings
    host: str = "rabbitmq"  # Default hostname for RabbitMQ service
    port: int = 5672  # Default AMQP port
    virtual_host: str = "/"  # Default virtual host
    username: str = "guest"  # Default username (should be overridden in production)
    password: str = "guest"  # Default password (should be overridden in production)
    
    # Security settings (TLS required as per section 3.2.3)
    use_ssl: bool = True
    ssl_verify: bool = True
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    ssl_ca_certs: Optional[str] = None
    
    # Connection parameters
    connection_attempts: int = 5
    retry_delay: float = 1.0
    heartbeat: int = 60
    blocked_connection_timeout: int = 300
    
    # Exchange settings (as specified in section 0.2.1.2)
    exchange_name: str = "mca.documents"
    exchange_type: str = "fanout"
    exchange_durable: bool = True
    exchange_auto_delete: bool = False
    
    # Queue settings
    queue_name: str = "data-extraction"
    queue_durable: bool = True
    queue_exclusive: bool = False
    queue_auto_delete: bool = False
    
    # Consumer settings
    prefetch_count: int = 10
    consumer_tag: str = "ocr-service"
    
    # Publisher settings
    delivery_mode: int = 2  # 2 = persistent
    mandatory: bool = True
    
    @classmethod
    def from_env(cls) -> RabbitMQConfig:
        """Create a RabbitMQConfig instance from environment variables.
        
        Returns:
            RabbitMQConfig: Configuration instance with values from environment variables
        """
        return cls(
            host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            virtual_host=os.getenv("RABBITMQ_VIRTUAL_HOST", "/"),
            username=os.getenv("RABBITMQ_USERNAME", "guest"),
            password=os.getenv("RABBITMQ_PASSWORD", "guest"),
            use_ssl=os.getenv("RABBITMQ_USE_SSL", "true").lower() == "true",
            ssl_verify=os.getenv("RABBITMQ_SSL_VERIFY", "true").lower() == "true",
            ssl_cert_path=os.getenv("RABBITMQ_SSL_CERT_PATH"),
            ssl_key_path=os.getenv("RABBITMQ_SSL_KEY_PATH"),
            ssl_ca_certs=os.getenv("RABBITMQ_SSL_CA_CERTS"),
            connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "5")),
            retry_delay=float(os.getenv("RABBITMQ_RETRY_DELAY", "1.0")),
            heartbeat=int(os.getenv("RABBITMQ_HEARTBEAT", "60")),
            blocked_connection_timeout=int(os.getenv("RABBITMQ_BLOCKED_CONNECTION_TIMEOUT", "300")),
            exchange_name=os.getenv("RABBITMQ_EXCHANGE_NAME", "mca.documents"),
            exchange_type=os.getenv("RABBITMQ_EXCHANGE_TYPE", "fanout"),
            exchange_durable=os.getenv("RABBITMQ_EXCHANGE_DURABLE", "true").lower() == "true",
            exchange_auto_delete=os.getenv("RABBITMQ_EXCHANGE_AUTO_DELETE", "false").lower() == "true",
            queue_name=os.getenv("RABBITMQ_QUEUE_NAME", "data-extraction"),
            queue_durable=os.getenv("RABBITMQ_QUEUE_DURABLE", "true").lower() == "true",
            queue_exclusive=os.getenv("RABBITMQ_QUEUE_EXCLUSIVE", "false").lower() == "true",
            queue_auto_delete=os.getenv("RABBITMQ_QUEUE_AUTO_DELETE", "false").lower() == "true",
            prefetch_count=int(os.getenv("RABBITMQ_PREFETCH_COUNT", "10")),
            consumer_tag=os.getenv("RABBITMQ_CONSUMER_TAG", "ocr-service"),
            delivery_mode=int(os.getenv("RABBITMQ_DELIVERY_MODE", "2")),
            mandatory=os.getenv("RABBITMQ_MANDATORY", "true").lower() == "true",
        )


@dataclass
class S3Config:
    """Configuration for S3-compatible storage.
    
    This class defines the configuration for connecting to S3-compatible storage,
    including endpoint, credentials, and security settings. It supports the requirements
    specified in section 0.1.3 and 0.2.5 of the technical specification for secure
    document storage with AES-256 encryption.
    """
    
    # Connection settings
    endpoint_url: str = "http://s3:9000"  # Default endpoint for MinIO in development
    region_name: str = "us-east-1"  # Default region
    aws_access_key_id: str = "minioadmin"  # Default access key (should be overridden in production)
    aws_secret_access_key: str = "minioadmin"  # Default secret key (should be overridden in production)
    
    # Security settings
    use_ssl: bool = True  # Use SSL/TLS for connections
    verify_ssl: bool = True  # Verify SSL certificates
    signature_version: str = "s3v4"  # S3 signature version
    
    # Bucket settings
    bucket_name: str = "mca-documents-development"  # Default bucket name
    
    # Encryption settings (AES-256 required as per section 0.2.5)
    encryption: str = "AES256"  # Server-side encryption algorithm
    
    # Performance settings
    max_pool_connections: int = 10  # Maximum number of connections in the connection pool
    connect_timeout: int = 5  # Connection timeout in seconds
    read_timeout: int = 60  # Read timeout in seconds
    
    # Retry settings
    max_retries: int = 3  # Maximum number of retry attempts
    retry_mode: str = "standard"  # Retry mode (standard, adaptive, legacy)
    
    @classmethod
    def from_env(cls) -> S3Config:
        """Create an S3Config instance from environment variables.
        
        Returns:
            S3Config: Configuration instance with values from environment variables
        """
        # Determine the environment to set the correct bucket name
        env_str = os.getenv("ENVIRONMENT")
        environment = Environment.from_string(env_str)
        bucket_suffix = environment.value if environment else "development"
        
        return cls(
            endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://s3:9000"),
            region_name=os.getenv("S3_REGION_NAME", "us-east-1"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID", "minioadmin"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY", "minioadmin"),
            use_ssl=os.getenv("S3_USE_SSL", "true").lower() == "true",
            verify_ssl=os.getenv("S3_VERIFY_SSL", "true").lower() == "true",
            signature_version=os.getenv("S3_SIGNATURE_VERSION", "s3v4"),
            bucket_name=os.getenv("S3_BUCKET_NAME", f"mca-documents-{bucket_suffix}"),
            encryption=os.getenv("S3_ENCRYPTION", "AES256"),
            max_pool_connections=int(os.getenv("S3_MAX_POOL_CONNECTIONS", "10")),
            connect_timeout=int(os.getenv("S3_CONNECT_TIMEOUT", "5")),
            read_timeout=int(os.getenv("S3_READ_TIMEOUT", "60")),
            max_retries=int(os.getenv("S3_MAX_RETRIES", "3")),
            retry_mode=os.getenv("S3_RETRY_MODE", "standard"),
        )


@dataclass
class LoggingConfig:
    """Configuration for structured logging.
    
    This class defines the configuration for structured logging, including log levels,
    formatting, and output destinations. It supports the requirements specified in
    section 0.2.5 of the technical specification for comprehensive logging with
    specified log levels.
    """
    
    # Log level settings
    log_level: str = "INFO"  # Default log level
    
    # Log format settings
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"  # Default log format
    date_format: str = "%Y-%m-%d %H:%M:%S"  # Default date format
    
    # JSON logging settings
    use_json_formatter: bool = True  # Use JSON formatter for structured logging
    include_timestamp: bool = True  # Include timestamp in JSON logs
    include_hostname: bool = True  # Include hostname in JSON logs
    include_service_name: bool = True  # Include service name in JSON logs
    
    # Log output settings
    log_to_console: bool = True  # Log to console
    log_to_file: bool = False  # Log to file
    log_file_path: Optional[str] = None  # Path to log file
    log_file_max_size: int = 10 * 1024 * 1024  # 10 MB
    log_file_backup_count: int = 5  # Number of backup log files
    
    # Correlation ID settings
    include_correlation_id: bool = True  # Include correlation ID in logs
    correlation_id_field: str = "correlation_id"  # Field name for correlation ID
    
    @classmethod
    def from_env(cls) -> LoggingConfig:
        """Create a LoggingConfig instance from environment variables.
        
        Returns:
            LoggingConfig: Configuration instance with values from environment variables
        """
        log_level_str = os.getenv("LOG_LEVEL", "INFO")
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if log_level_str not in valid_log_levels:
            log_level_str = "INFO"
            
        return cls(
            log_level=log_level_str,
            log_format=os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            date_format=os.getenv("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
            use_json_formatter=os.getenv("LOG_JSON_FORMATTER", "true").lower() == "true",
            include_timestamp=os.getenv("LOG_INCLUDE_TIMESTAMP", "true").lower() == "true",
            include_hostname=os.getenv("LOG_INCLUDE_HOSTNAME", "true").lower() == "true",
            include_service_name=os.getenv("LOG_INCLUDE_SERVICE_NAME", "true").lower() == "true",
            log_to_console=os.getenv("LOG_TO_CONSOLE", "true").lower() == "true",
            log_to_file=os.getenv("LOG_TO_FILE", "false").lower() == "true",
            log_file_path=os.getenv("LOG_FILE_PATH"),
            log_file_max_size=int(os.getenv("LOG_FILE_MAX_SIZE", str(10 * 1024 * 1024))),
            log_file_backup_count=int(os.getenv("LOG_FILE_BACKUP_COUNT", "5")),
            include_correlation_id=os.getenv("LOG_INCLUDE_CORRELATION_ID", "true").lower() == "true",
            correlation_id_field=os.getenv("LOG_CORRELATION_ID_FIELD", "correlation_id"),
        )


@dataclass
class AppConfig:
    """Main application configuration that combines all configuration components.
    
    This class serves as the central configuration for the OCR service, combining
    all individual configuration components into a single, unified configuration object.
    It provides a convenient way to access all configuration settings from a single point.
    """
    
    service: ServiceConfig = field(default_factory=ServiceConfig)
    tensorflow: TensorFlowConfig = field(default_factory=TensorFlowConfig)
    rabbitmq: RabbitMQConfig = field(default_factory=RabbitMQConfig)
    s3: S3Config = field(default_factory=S3Config)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_env(cls) -> AppConfig:
        """Create an AppConfig instance from environment variables.
        
        Returns:
            AppConfig: Configuration instance with values from environment variables
        """
        return cls(
            service=ServiceConfig.from_env(),
            tensorflow=TensorFlowConfig.from_env(),
            rabbitmq=RabbitMQConfig.from_env(),
            s3=S3Config.from_env(),
            logging=LoggingConfig.from_env(),
        )