"""
Core application configuration for the Document Service microservice.

This module centralizes environment variables, application settings, and
environment-specific configurations (development, staging, production).
It provides a type-safe configuration interface using Pydantic.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    """Supported environment types for the Document Service."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class AppConfig(BaseSettings):
    """
    Core application configuration for the Document Service.
    
    This class centralizes all configuration settings and provides
    environment-specific overrides. It validates environment variables
    and ensures required values are present.
    """
    # Service information
    SERVICE_NAME: str = "document-service"
    SERVICE_VERSION: str = "1.0.0"
    
    # Environment configuration
    ENVIRONMENT: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT,
        description="The environment in which the service is running"
    )
    
    # Server configuration
    HOST: str = Field(
        default="0.0.0.0",
        description="Host address to bind the service to"
    )
    PORT: int = Field(
        default=8000,
        description="Port to bind the service to"
    )
    
    # API configuration
    API_PREFIX: str = Field(
        default="/api/v1",
        description="Prefix for all API endpoints"
    )
    
    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (ERROR, WARN, INFO, DEBUG)"
    )
    LOG_FORMAT: str = Field(
        default="json",
        description="Logging format (json, text)"
    )
    
    # Document classification confidence thresholds
    MIN_CONFIDENCE_THRESHOLD: float = Field(
        default=0.75,
        description="Minimum confidence threshold for automatic classification"
    )
    HIGH_CONFIDENCE_THRESHOLD: float = Field(
        default=0.95,
        description="High confidence threshold for automatic processing"
    )
    
    # Performance settings
    WORKER_THREADS: int = Field(
        default=4,
        description="Number of worker threads for document processing"
    )
    BATCH_SIZE: int = Field(
        default=10,
        description="Batch size for document processing"
    )
    
    # Timeout settings
    REQUEST_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout for HTTP requests in seconds"
    )
    PROCESSING_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Timeout for document processing in seconds"
    )
    
    # Feature flags
    ENABLE_GPU_ACCELERATION: bool = Field(
        default=False,
        description="Enable GPU acceleration for document processing"
    )
    
    # Model settings
    MODEL_PATH: str = Field(
        default="./models",
        description="Path to the document classification models"
    )
    
    # Health check settings
    HEALTH_CHECK_INTERVAL_SECONDS: int = Field(
        default=60,
        description="Interval between health checks in seconds"
    )
    
    # Metrics settings
    ENABLE_METRICS: bool = Field(
        default=True,
        description="Enable metrics collection"
    )
    METRICS_PORT: int = Field(
        default=9090,
        description="Port for metrics endpoint"
    )
    
    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )
    
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate that the log level is one of the allowed values."""
        allowed_levels = ["ERROR", "WARN", "INFO", "DEBUG"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of {allowed_levels}")
        return v.upper()
    
    def get_environment_settings(self) -> Dict[str, Any]:
        """
        Get environment-specific settings.
        
        Returns:
            Dict[str, Any]: Environment-specific settings
        """
        if self.ENVIRONMENT == EnvironmentType.DEVELOPMENT:
            return {
                "LOG_LEVEL": "DEBUG",
                "MIN_CONFIDENCE_THRESHOLD": 0.6,  # Lower threshold for development
                "ENABLE_GPU_ACCELERATION": False,
                "WORKER_THREADS": 2,
                "BATCH_SIZE": 5,
            }
        elif self.ENVIRONMENT == EnvironmentType.STAGING:
            return {
                "LOG_LEVEL": "INFO",
                "MIN_CONFIDENCE_THRESHOLD": 0.7,
                "ENABLE_GPU_ACCELERATION": True,
                "WORKER_THREADS": 4,
                "BATCH_SIZE": 10,
            }
        elif self.ENVIRONMENT == EnvironmentType.PRODUCTION:
            return {
                "LOG_LEVEL": "INFO",
                "MIN_CONFIDENCE_THRESHOLD": 0.75,
                "ENABLE_GPU_ACCELERATION": True,
                "WORKER_THREADS": 8,
                "BATCH_SIZE": 20,
            }
        return {}
    
    def __init__(self, **data: Any):
        """
        Initialize the configuration with environment-specific overrides.
        
        Args:
            **data: Configuration data
        """
        super().__init__(**data)
        
        # Apply environment-specific settings
        env_settings = self.get_environment_settings()
        for key, value in env_settings.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Create a singleton instance of the configuration
def get_app_config() -> AppConfig:
    """
    Get the application configuration singleton.
    
    Returns:
        AppConfig: The application configuration
    """
    return AppConfig()


# Export the configuration singleton
app_config = get_app_config()