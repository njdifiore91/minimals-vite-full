"""
Core application configuration for the OCR Service microservice.

This module centralizes environment variables, application settings, and environment-specific
configurations for the OCR Service. It provides a type-safe configuration interface that
can be imported and used throughout the application.

The configuration is loaded from environment variables with validation to ensure required
values are present. Different settings are provided for development, staging, and production
environments.

Example:
    from config import app_config
    
    # Access configuration values
    service_name = app_config.SERVICE_NAME
    rabbitmq_host = app_config.RABBITMQ_HOST
    s3_bucket = app_config.S3_BUCKET
"""

import os
import sys
from enum import Enum
from typing import Dict, Any, Optional, Union, List, cast
from pathlib import Path

# Define environment types
class Environment(str, Enum):
    """Supported application environments."""
    DEVELOPMENT = 'development'
    STAGING = 'staging'
    PRODUCTION = 'production'
    
    @classmethod
    def from_string(cls, value: str) -> 'Environment':
        """Convert a string to an Environment enum value."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.DEVELOPMENT

# Define log levels
class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'

# Create a singleton instance
_config_instance = None

class AppConfig:
    """
    Core application configuration for the OCR Service.
    
    This class centralizes all configuration settings and provides
    environment-specific defaults. It validates required environment
    variables and raises clear error messages when they're missing.
    """
    
    # Service information
    SERVICE_NAME: str = 'ocr-service'
    SERVICE_VERSION: str = '1.0.0'
    
    # Environment
    ENVIRONMENT: Environment
    
    # Server settings
    HOST: str
    PORT: int
    
    # RabbitMQ configuration
    RABBITMQ_HOST: str
    RABBITMQ_PORT: int
    RABBITMQ_USERNAME: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_VHOST: str
    RABBITMQ_EXCHANGE: str
    RABBITMQ_QUEUE: str
    RABBITMQ_USE_TLS: bool
    RABBITMQ_CLIENT_CERT: Optional[str]
    RABBITMQ_CLIENT_KEY: Optional[str]
    RABBITMQ_CA_CERT: Optional[str]
    
    # S3 configuration
    S3_ENDPOINT: str
    S3_REGION: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET: str
    S3_USE_SSL: bool
    S3_VERIFY_SSL: bool
    
    # TensorFlow configuration
    TF_MODEL_PATH: str
    TF_USE_GPU: bool
    TF_GPU_MEMORY_LIMIT: Optional[int]
    TF_CONFIDENCE_THRESHOLD: float
    
    # Logging configuration
    LOG_LEVEL: LogLevel
    LOG_FORMAT: str
    LOG_FILE: Optional[str]
    
    # Performance settings
    BATCH_SIZE: int
    MAX_WORKERS: int
    PROCESSING_TIMEOUT: int
    
    def __init__(self):
        """Initialize the configuration with values from environment variables."""
        # Load environment
        self.ENVIRONMENT = self._get_environment()
        
        # Load server settings
        self.HOST = self._get_env('HOST', '0.0.0.0')
        self.PORT = int(self._get_env('PORT', '8080'))
        
        # Load RabbitMQ configuration
        self.RABBITMQ_HOST = self._get_env('RABBITMQ_HOST', 'localhost')
        self.RABBITMQ_PORT = int(self._get_env('RABBITMQ_PORT', '5672'))
        self.RABBITMQ_USERNAME = self._get_env('RABBITMQ_USERNAME', 'guest')
        self.RABBITMQ_PASSWORD = self._get_env('RABBITMQ_PASSWORD', 'guest')
        self.RABBITMQ_VHOST = self._get_env('RABBITMQ_VHOST', '/')
        self.RABBITMQ_EXCHANGE = self._get_env('RABBITMQ_EXCHANGE', 'mca.documents')
        self.RABBITMQ_QUEUE = self._get_env('RABBITMQ_QUEUE', 'data-extraction')
        self.RABBITMQ_USE_TLS = self._get_env_bool('RABBITMQ_USE_TLS', True)
        self.RABBITMQ_CLIENT_CERT = self._get_env('RABBITMQ_CLIENT_CERT', None)
        self.RABBITMQ_CLIENT_KEY = self._get_env('RABBITMQ_CLIENT_KEY', None)
        self.RABBITMQ_CA_CERT = self._get_env('RABBITMQ_CA_CERT', None)
        
        # Load S3 configuration
        self.S3_ENDPOINT = self._get_env('S3_ENDPOINT', 's3.amazonaws.com')
        self.S3_REGION = self._get_env('S3_REGION', 'us-east-1')
        self.S3_ACCESS_KEY = self._get_env('S3_ACCESS_KEY', '')
        self.S3_SECRET_KEY = self._get_env('S3_SECRET_KEY', '')
        self.S3_BUCKET = self._get_env('S3_BUCKET', self._get_default_bucket())
        self.S3_USE_SSL = self._get_env_bool('S3_USE_SSL', True)
        self.S3_VERIFY_SSL = self._get_env_bool('S3_VERIFY_SSL', True)
        
        # Load TensorFlow configuration
        self.TF_MODEL_PATH = self._get_env('TF_MODEL_PATH', './models')
        self.TF_USE_GPU = self._get_env_bool('TF_USE_GPU', True)
        gpu_memory = self._get_env('TF_GPU_MEMORY_LIMIT', None)
        self.TF_GPU_MEMORY_LIMIT = int(gpu_memory) if gpu_memory else None
        self.TF_CONFIDENCE_THRESHOLD = float(self._get_env('TF_CONFIDENCE_THRESHOLD', '0.85'))
        
        # Load logging configuration
        log_level = self._get_env('LOG_LEVEL', self._get_default_log_level())
        self.LOG_LEVEL = LogLevel(log_level)
        self.LOG_FORMAT = self._get_env(
            'LOG_FORMAT', 
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.LOG_FILE = self._get_env('LOG_FILE', None)
        
        # Load performance settings
        self.BATCH_SIZE = int(self._get_env('BATCH_SIZE', '10'))
        self.MAX_WORKERS = int(self._get_env('MAX_WORKERS', '4'))
        self.PROCESSING_TIMEOUT = int(self._get_env('PROCESSING_TIMEOUT', '300'))  # 5 minutes
        
        # Validate configuration
        self._validate_configuration()
    
    def _get_environment(self) -> Environment:
        """Get the current environment from environment variables."""
        env = os.getenv('ENVIRONMENT', 'development')
        return Environment.from_string(env)
    
    def _get_env(self, key: str, default: Optional[str] = None) -> str:
        """
        Get an environment variable with a default value.
        
        Args:
            key: The environment variable name
            default: The default value if not set
            
        Returns:
            The environment variable value or default
            
        Raises:
            ValueError: If the environment variable is required but not set
        """
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Required environment variable '{key}' is not set")
        return value
    
    def _get_env_bool(self, key: str, default: bool = False) -> bool:
        """
        Get a boolean environment variable.
        
        Args:
            key: The environment variable name
            default: The default value if not set
            
        Returns:
            The boolean value of the environment variable
        """
        value = os.getenv(key, str(default).lower())
        return value.lower() in ('true', '1', 't', 'yes', 'y')
    
    def _get_default_bucket(self) -> str:
        """Get the default S3 bucket name based on the environment."""
        if self.ENVIRONMENT == Environment.PRODUCTION:
            return 'mca-documents-production'
        elif self.ENVIRONMENT == Environment.STAGING:
            return 'mca-documents-staging'
        else:
            return 'mca-documents-development'
    
    def _get_default_log_level(self) -> str:
        """Get the default log level based on the environment."""
        if self.ENVIRONMENT == Environment.PRODUCTION:
            return LogLevel.INFO.value
        elif self.ENVIRONMENT == Environment.STAGING:
            return LogLevel.INFO.value
        else:
            return LogLevel.DEBUG.value
    
    def _validate_configuration(self) -> None:
        """
        Validate the configuration to ensure all required values are present
        and properly formatted.
        
        Raises:
            ValueError: If any configuration validation fails
        """
        # Validate RabbitMQ TLS configuration
        if self.RABBITMQ_USE_TLS:
            if self.ENVIRONMENT in (Environment.STAGING, Environment.PRODUCTION):
                if not self.RABBITMQ_CLIENT_CERT:
                    raise ValueError("RABBITMQ_CLIENT_CERT is required when TLS is enabled in staging/production")
                if not self.RABBITMQ_CLIENT_KEY:
                    raise ValueError("RABBITMQ_CLIENT_KEY is required when TLS is enabled in staging/production")
                if not self.RABBITMQ_CA_CERT:
                    raise ValueError("RABBITMQ_CA_CERT is required when TLS is enabled in staging/production")
        
        # Validate S3 credentials
        if self.ENVIRONMENT in (Environment.STAGING, Environment.PRODUCTION):
            if not self.S3_ACCESS_KEY:
                raise ValueError("S3_ACCESS_KEY is required in staging/production")
            if not self.S3_SECRET_KEY:
                raise ValueError("S3_SECRET_KEY is required in staging/production")
        
        # Validate TensorFlow GPU configuration
        if self.ENVIRONMENT == Environment.PRODUCTION and self.TF_USE_GPU:
            if not self.TF_GPU_MEMORY_LIMIT or self.TF_GPU_MEMORY_LIMIT < 8192:  # 8GB minimum
                raise ValueError("TF_GPU_MEMORY_LIMIT must be at least 8GB (8192MB) for production use")
    
    def as_dict(self) -> Dict[str, Any]:
        """
        Convert the configuration to a dictionary.
        
        Returns:
            A dictionary of all configuration values
        """
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
    
    def __str__(self) -> str:
        """String representation of the configuration."""
        return f"AppConfig(environment={self.ENVIRONMENT}, service={self.SERVICE_NAME}, version={self.SERVICE_VERSION})"


def get_config() -> AppConfig:
    """
    Get the singleton configuration instance.
    
    Returns:
        The AppConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance


# Create a singleton instance for easy import
app_config = get_config()