"""
OCR Service Types Package

This package provides type definitions for the OCR Service, ensuring type safety
throughout the application. It includes types for document processing, OCR models,
extraction results, storage operations, message handling, error management, and
service configuration.

By centralizing type definitions in this package, we ensure consistent typing
across the application and provide a clean import interface for developers.

Example usage:
    from ocr_service.types import ExtractedData, OCRModelType, DocumentType
    
    def process_document(document_type: DocumentType) -> ExtractedData:
        # Implementation...
        pass
"""

from __future__ import annotations

# Import and re-export types from storage module
from .storage import (
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult,
    StorageErrorType,
    DocumentType as StorageDocumentType,
    StorageKey,
    DEFAULT_STORAGE_OPTIONS,
    BUCKET_CONFIGS,
)

# Import and re-export types from models module
from .models import (
    OCRModelType,
    ModelParameters,
    ModelMetrics,
    ModelResult,
    ModelSelectionCriteria,
    ModelSelector,
    TensorFlowModel,
    DEFAULT_TYPED_MODEL_PARAMS,
    DEFAULT_HANDWRITTEN_MODEL_PARAMS,
    DEFAULT_HYBRID_MODEL_PARAMS,
)

# Import and re-export types from extraction module
from .extraction import (
    ConfidenceScore,
    FieldType,
    FieldLocation,
    ExtractedField,
    ExtractionMetadata,
    TableData,
    ExtractedData,
    JSONSchemaType,
    JSONSchemaProperty,
    JSONSchema,
    JSONSchemaRegistry,
    APPLICATION_FORM_SCHEMA,
)

# Import and re-export types from messages module
from .messages import (
    MessagePayload,
    MessageHeaders,
    ExchangeConfig,
    QueueConfig,
    PublishOptions,
    ConsumeOptions,
    MessagePriority,
    DeliveryMode,
    MessageStatus,
    RabbitMQConfig,
)

# Import and re-export types from errors module
from .errors import (
    ServiceError,
    ErrorDetails,
    LogEntry,
    ErrorCategory,
    MonitoringAlert,
    Result,
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

# Import and re-export types from config module
from .config import (
    ConfigDict,
    ServiceConfig,
    TensorFlowConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
)

# Resolve name conflicts by providing aliases
DocumentTypeStorage = StorageDocumentType

# Define __all__ to explicitly specify exported names
__all__ = [
    # Storage types
    'S3ClientConfig',
    'StorageOptions',
    'StorageMetadata',
    'BucketConfig',
    'StorageResult',
    'StorageErrorType',
    'StorageDocumentType',
    'DocumentTypeStorage',
    'StorageKey',
    'DEFAULT_STORAGE_OPTIONS',
    'BUCKET_CONFIGS',
    
    # Model types
    'OCRModelType',
    'ModelParameters',
    'ModelMetrics',
    'ModelResult',
    'ModelSelectionCriteria',
    'ModelSelector',
    'TensorFlowModel',
    'DEFAULT_TYPED_MODEL_PARAMS',
    'DEFAULT_HANDWRITTEN_MODEL_PARAMS',
    'DEFAULT_HYBRID_MODEL_PARAMS',
    
    # Extraction types
    'ConfidenceScore',
    'FieldType',
    'FieldLocation',
    'ExtractedField',
    'ExtractionMetadata',
    'TableData',
    'ExtractedData',
    'JSONSchemaType',
    'JSONSchemaProperty',
    'JSONSchema',
    'JSONSchemaRegistry',
    'APPLICATION_FORM_SCHEMA',
    
    # Message types
    'MessagePayload',
    'MessageHeaders',
    'ExchangeConfig',
    'QueueConfig',
    'PublishOptions',
    'ConsumeOptions',
    'MessagePriority',
    'DeliveryMode',
    'MessageStatus',
    'RabbitMQConfig',
    
    # Error types
    'ServiceError',
    'ErrorDetails',
    'LogEntry',
    'ErrorCategory',
    'MonitoringAlert',
    'Result',
    
    # Document types
    'DocumentMetadata',
    'DocumentContent',
    'DocumentType',
    'ProcessingStatus',
    'DocumentSource',
    'Document',
    
    # Config types
    'ConfigDict',
    'ServiceConfig',
    'TensorFlowConfig',
    'RabbitMQConfig',
    'S3Config',
    'LoggingConfig',
]