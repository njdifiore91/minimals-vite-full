"""
Type definitions for Document Service configuration, environment variables, and application settings.

This module provides type definitions for service configuration, ensuring consistent and
type-safe access to configuration values throughout the codebase. It includes types for
scikit-learn model configuration, RabbitMQ connection parameters, and S3 storage settings.

The Document Service uses scikit-learn 1.4.1 for document classification and requires
configuration for different environments (development, staging, production).
"""

from __future__ import annotations

import os
import enum
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeVar, Union, TypedDict, Literal

# Type alias for configuration dictionaries
ConfigDict = Dict[str, Any]


class Environment(enum.Enum):
    """Enumeration of deployment environments.
    
    As specified in section 0.2.5, the system supports development, staging, and production
    environments with different configurations.
    """
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    
    @classmethod
    def from_string(cls, env_str: str) -> Environment:
        """Convert a string to an Environment enum value.
        
        Args:
            env_str: String representation of the environment
            
        Returns:
            Corresponding Environment enum value
            
        Raises:
            ValueError: If the string doesn't match any environment
        """
        normalized = env_str.lower().strip()
        
        if normalized in ("dev", "development"):
            return cls.DEVELOPMENT
        elif normalized in ("stage", "staging"):
            return cls.STAGING
        elif normalized in ("prod", "production"):
            return cls.PRODUCTION
        else:
            raise ValueError(f"Unknown environment: {env_str}")


@dataclass
class ServiceConfig:
    """Configuration for the Document Service application.
    
    This class provides application-wide settings for the Document Service,
    including service name, version, port, and environment.
    """
    name: str = "document-service"
    version: str = "1.0.0"
    port: int = 8000
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    base_path: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent)
    
    @classmethod
    def from_env(cls) -> ServiceConfig:
        """Create a service configuration from environment variables.
        
        Returns:
            ServiceConfig instance with values from environment variables
        """
        env_name = os.environ.get("SERVICE_ENV", "development")
        
        return cls(
            name=os.environ.get("SERVICE_NAME", "document-service"),
            version=os.environ.get("SERVICE_VERSION", "1.0.0"),
            port=int(os.environ.get("SERVICE_PORT", "8000")),
            environment=Environment.from_string(env_name),
            debug=os.environ.get("SERVICE_DEBUG", "false").lower() in ("true", "1", "yes")
        )


@dataclass
class ModelConfig:
    """Configuration for scikit-learn classification models.
    
    This class represents the configuration for the scikit-learn models used for
    document classification in the Document Service.
    """
    model_type: str = "random_forest"  # Default model type
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence_threshold: float = 0.75
    version: str = "1.0.0"
    description: str = ""
    
    @classmethod
    def from_dict(cls, config_dict: ConfigDict) -> ModelConfig:
        """Create a model configuration from a dictionary.
        
        Args:
            config_dict: Dictionary containing model configuration
            
        Returns:
            ModelConfig instance with values from the dictionary
        """
        return cls(
            model_type=config_dict.get("model_type", "random_forest"),
            parameters=config_dict.get("parameters", {}),
            confidence_threshold=config_dict.get("confidence_threshold", 0.75),
            version=config_dict.get("version", "1.0.0"),
            description=config_dict.get("description", "")
        )
    
    def to_dict(self) -> ConfigDict:
        """Convert the model configuration to a dictionary.
        
        Returns:
            Dictionary representation of the model configuration
        """
        return {
            "model_type": self.model_type,
            "parameters": self.parameters,
            "confidence_threshold": self.confidence_threshold,
            "version": self.version,
            "description": self.description
        }


@dataclass
class RabbitMQConfig:
    """Configuration for RabbitMQ connection and exchanges.
    
    As specified in section 0.1.3, the system uses RabbitMQ for asynchronous
    communication between services with specific exchanges and queues.
    """
    host: str = "localhost"
    port: int = 5672
    username: str = "guest"
    password: str = "guest"
    virtual_host: str = "/"
    ssl: bool = True
    heartbeat: int = 60
    connection_attempts: int = 3
    retry_delay: int = 5
    
    # Exchange configuration
    document_exchange: Dict[str, Any] = field(default_factory=lambda: {
        "name": "mca.documents",
        "type": "fanout",
        "durable": True,
        "auto_delete": False,
        "arguments": {}
    })
    
    # Queue configuration
    document_processing_queue: Dict[str, Any] = field(default_factory=lambda: {
        "name": "document-processing",
        "durable": True,
        "exclusive": False,
        "auto_delete": False,
        "arguments": {
            "x-dead-letter-exchange": "mca.dead-letter",
            "x-dead-letter-routing-key": "document-processing.dead",
            "x-message-ttl": 1000 * 60 * 60 * 24  # 24 hours
        }
    })
    
    @classmethod
    def from_env(cls) -> RabbitMQConfig:
        """Create a RabbitMQ configuration from environment variables.
        
        Returns:
            RabbitMQConfig instance with values from environment variables
        """
        return cls(
            host=os.environ.get("RABBITMQ_HOST", "localhost"),
            port=int(os.environ.get("RABBITMQ_PORT", "5672")),
            username=os.environ.get("RABBITMQ_USERNAME", "guest"),
            password=os.environ.get("RABBITMQ_PASSWORD", "guest"),
            virtual_host=os.environ.get("RABBITMQ_VHOST", "/"),
            ssl=os.environ.get("RABBITMQ_SSL", "true").lower() in ("true", "1", "yes"),
            heartbeat=int(os.environ.get("RABBITMQ_HEARTBEAT", "60")),
            connection_attempts=int(os.environ.get("RABBITMQ_CONNECTION_ATTEMPTS", "3")),
            retry_delay=int(os.environ.get("RABBITMQ_RETRY_DELAY", "5"))
        )


class S3Config(TypedDict):
    """Configuration for S3-compatible storage.
    
    As specified in section 0.2.5, the system uses S3-compatible storage with
    AES-256 encryption for document storage.
    """
    endpoint_url: str
    region_name: str
    aws_access_key_id: str
    aws_secret_access_key: str
    use_ssl: bool
    verify: Union[bool, str]
    max_pool_connections: int
    timeout: int
    retries: int
    bucket_name: str
    encryption: Literal["AES256", "aws:kms", "none"]


def get_s3_config_from_env() -> S3Config:
    """Create an S3 configuration from environment variables.
    
    Returns:
        S3Config instance with values from environment variables
    """
    env = os.environ.get("SERVICE_ENV", "development")
    bucket_suffix = "-production" if env == "production" else "-staging" if env == "staging" else "-development"
    
    return {
        "endpoint_url": os.environ.get("S3_ENDPOINT_URL", "https://s3.amazonaws.com"),
        "region_name": os.environ.get("S3_REGION", "us-east-1"),
        "aws_access_key_id": os.environ.get("S3_ACCESS_KEY", ""),
        "aws_secret_access_key": os.environ.get("S3_SECRET_KEY", ""),
        "use_ssl": os.environ.get("S3_USE_SSL", "true").lower() in ("true", "1", "yes"),
        "verify": os.environ.get("S3_VERIFY", "true").lower() in ("true", "1", "yes"),
        "max_pool_connections": int(os.environ.get("S3_MAX_POOL_CONNECTIONS", "10")),
        "timeout": int(os.environ.get("S3_TIMEOUT", "60")),
        "retries": int(os.environ.get("S3_RETRIES", "3")),
        "bucket_name": os.environ.get("S3_BUCKET", f"mca-documents{bucket_suffix}"),
        "encryption": os.environ.get("S3_ENCRYPTION", "AES256")
    }


class LogLevel(enum.Enum):
    """Enumeration of log levels.
    
    As specified in section 0.2.5, the system uses the following log levels:
    - ERROR: Processing failures
    - WARN: Potential issues
    - INFO: Normal operations
    - DEBUG: Troubleshooting (development only)
    """
    ERROR = "ERROR"
    WARN = "WARN"
    INFO = "INFO"
    DEBUG = "DEBUG"


@dataclass
class LoggingConfig:
    """Configuration for structured logging.
    
    As specified in section 0.2.5, the system implements comprehensive logging
    with specified log levels and formats.
    """
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_path: Optional[str] = None
    console_output: bool = True
    json_format: bool = True
    include_correlation_id: bool = True
    include_document_id: bool = True
    
    @classmethod
    def from_env(cls) -> LoggingConfig:
        """Create a logging configuration from environment variables.
        
        Returns:
            LoggingConfig instance with values from environment variables
        """
        log_level_str = os.environ.get("LOG_LEVEL", "INFO")
        log_level = LogLevel.INFO
        
        try:
            log_level = LogLevel[log_level_str.upper()]
        except KeyError:
            # Default to INFO if invalid level
            pass
        
        return cls(
            level=log_level,
            format=os.environ.get("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
            date_format=os.environ.get("LOG_DATE_FORMAT", "%Y-%m-%d %H:%M:%S"),
            file_path=os.environ.get("LOG_FILE_PATH"),
            console_output=os.environ.get("LOG_CONSOLE", "true").lower() in ("true", "1", "yes"),
            json_format=os.environ.get("LOG_JSON", "true").lower() in ("true", "1", "yes"),
            include_correlation_id=os.environ.get("LOG_CORRELATION_ID", "true").lower() in ("true", "1", "yes"),
            include_document_id=os.environ.get("LOG_DOCUMENT_ID", "true").lower() in ("true", "1", "yes")
        )


@dataclass
class AppConfig:
    """Complete application configuration.
    
    This class combines all configuration components into a single configuration object
    for the Document Service.
    """
    service: ServiceConfig
    model: ModelConfig
    rabbitmq: RabbitMQConfig
    s3: S3Config
    logging: LoggingConfig
    
    @classmethod
    def from_env(cls) -> AppConfig:
        """Create a complete application configuration from environment variables.
        
        Returns:
            AppConfig instance with values from environment variables
        """
        return cls(
            service=ServiceConfig.from_env(),
            model=ModelConfig(),  # Default model config
            rabbitmq=RabbitMQConfig.from_env(),
            s3=get_s3_config_from_env(),
            logging=LoggingConfig.from_env()
        )
    
    def validate(self) -> None:
        """Validate the configuration.
        
        Raises:
            ValueError: If the configuration is invalid
        """
        # Validate S3 configuration
        if not self.s3["aws_access_key_id"] or not self.s3["aws_secret_access_key"]:
            raise ValueError("S3 credentials are required")
        
        # Validate RabbitMQ configuration
        if not self.rabbitmq.host or not self.rabbitmq.username or not self.rabbitmq.password:
            raise ValueError("RabbitMQ connection parameters are required")
        
        # Validate service configuration
        if not self.service.name or not self.service.version:
            raise ValueError("Service name and version are required")