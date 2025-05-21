"""
Types package for the Document Service.

This package provides type definitions used throughout the Document Service application.
It exports all type classes, interfaces, and enums from individual modules, providing
a clean import interface for the application.

Example:
    ```python
    from document_service.types import DocumentMetadata, ClassificationResult
    ```

Rather than:
    ```python
    from document_service.types.documents import DocumentMetadata
    from document_service.types.classification import ClassificationResult
    ```
"""

# Import and re-export types from errors module
from .errors import (
    ServiceError,
    ErrorDetails,
    LogEntry,
    ErrorCategory,
    MonitoringAlert,
    Result,
)

# Import and re-export types from classification module
from .classification import (
    ClassificationModel,
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters,
    ClassificationMetrics,
)

# Import and re-export types from storage module
from .storage import (
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult,
    StorageKey,
)

# Import and re-export types from documents module
from .documents import (
    DocumentMetadata,
    DocumentContent,
    DocumentType,
    ProcessingStatus,
    DocumentSource,
    Document,
)

# Import and re-export types from messages module
from .messages import (
    MessagePayload,
    MessageHeaders,
    ExchangeConfig,
    QueueConfig,
    PublishOptions,
    ConsumeOptions,
)

# Import and re-export types from config module
from .config import (
    ConfigDict,
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
)

# Define __all__ to explicitly specify what is exported from this package
__all__ = [
    # From errors.py
    'ServiceError',
    'ErrorDetails',
    'LogEntry',
    'ErrorCategory',
    'MonitoringAlert',
    'Result',
    
    # From classification.py
    'ClassificationModel',
    'FeatureVector',
    'ClassificationResult',
    'ConfidenceScore',
    'ModelParameters',
    'ClassificationMetrics',
    
    # From storage.py
    'S3ClientConfig',
    'StorageOptions',
    'StorageMetadata',
    'BucketConfig',
    'StorageResult',
    'StorageKey',
    
    # From documents.py
    'DocumentMetadata',
    'DocumentContent',
    'DocumentType',
    'ProcessingStatus',
    'DocumentSource',
    'Document',
    
    # From messages.py
    'MessagePayload',
    'MessageHeaders',
    'ExchangeConfig',
    'QueueConfig',
    'PublishOptions',
    'ConsumeOptions',
    
    # From config.py
    'ConfigDict',
    'ServiceConfig',
    'ModelConfig',
    'RabbitMQConfig',
    'S3Config',
    'LoggingConfig',
]