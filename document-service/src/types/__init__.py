#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service Type Definitions Package.

This package provides type definitions for the Document Service, ensuring type safety
and consistent interfaces across the application. It exports all type classes, interfaces,
and type aliases from individual modules for easy importing throughout the codebase.

Example usage:
    ```python
    # Import specific types
    from document_service.types import DocumentType, ClassificationResult, StorageMetadata
    
    # Use imported types
    result: ClassificationResult = classify_document(document_bytes)
    metadata: StorageMetadata = create_metadata(result, document_id)
    ```

This package helps maintain a clean import interface and prevents circular dependencies
by centralizing all type definitions in one place.
"""

# Classification types
from .classification import (
    # Type aliases
    FeatureVector,
    FeatureMatrix,
    ProbabilityVector,
    LabelVector,
    ConfidenceScore,
    FeatureExtractor,
    SerializedModel,
    
    # Enums
    DocumentType,
    
    # Classes and Protocols
    ModelParameters,
    ClassificationResult,
    ClassificationMetrics,
    ClassificationModel,
    ModelVersion
)

# Storage types
from .storage import (
    # Configuration types
    S3Credentials,
    S3ClientConfig,
    EncryptionConfig,
    StorageOptions,
    
    # Document metadata types
    DocumentClassification,
    StorageMetadata,
    
    # Lifecycle management types
    LifecycleTransition,
    LifecycleExpiration,
    LifecycleRule,
    
    # Bucket configuration types
    BucketConfig,
    EnvironmentBuckets,
    
    # Error handling types
    StorageErrorDetail,
    StorageError,
    StorageResult,
    
    # Storage operation types
    StorageKey,
    RetryConfig,
    StorageOperations,
    StorageKeyGenerator,
    
    # Callback types
    UploadFileCallback,
    DownloadFileCallback
)

# Configuration types
from .config import (
    # Type aliases
    ConfigDict,
    EnvironmentType,
    
    # Configuration classes
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
    AppConfig,
    
    # Helper functions
    validate_config
)

__all__ = [
    # Classification types
    'FeatureVector',
    'FeatureMatrix',
    'ProbabilityVector',
    'LabelVector',
    'ConfidenceScore',
    'FeatureExtractor',
    'SerializedModel',
    'DocumentType',
    'ModelParameters',
    'ClassificationResult',
    'ClassificationMetrics',
    'ClassificationModel',
    'ModelVersion',
    
    # Storage types
    'S3Credentials',
    'S3ClientConfig',
    'EncryptionConfig',
    'StorageOptions',
    'DocumentClassification',
    'StorageMetadata',
    'LifecycleTransition',
    'LifecycleExpiration',
    'LifecycleRule',
    'BucketConfig',
    'EnvironmentBuckets',
    'StorageErrorDetail',
    'StorageError',
    'StorageResult',
    'StorageKey',
    'RetryConfig',
    'StorageOperations',
    'StorageKeyGenerator',
    'UploadFileCallback',
    'DownloadFileCallback',
    
    # Configuration types
    'ConfigDict',
    'EnvironmentType',
    'ServiceConfig',
    'ModelConfig',
    'RabbitMQConfig',
    'S3Config',
    'LoggingConfig',
    'AppConfig',
    'validate_config'
]