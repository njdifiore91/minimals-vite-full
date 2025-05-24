# OCR Service - Types Package
"""
This module exports all type definitions used throughout the OCR Service.

The types package provides a centralized location for all data structures,
enums, and type definitions used in the OCR processing pipeline. This ensures
consistency across the application and simplifies imports.

Rather than importing from individual modules, consumers can import directly
from the types package:

    from ocr_service.types import DocumentType, OCRRequest, ConfidenceScore
"""

# Import and re-export all types from submodules
# This provides a clean import interface for the application

# Document type definitions
from .document_types import (
    DocumentType,
    DocumentFormat,
    DocumentSource,
    DocumentMetadata,
    DocumentContent,
)

# OCR request/response types
from .ocr_types import (
    OCRRequest,
    OCRResponse,
    OCROptions,
    OCRProcessingMode,
    OCREngine,
)

# Field extraction types
from .extraction_types import (
    ExtractedField,
    FieldType,
    FieldLocation,
    TableData,
    TableCell,
    TableRow,
)

# Confidence scoring types
from .confidence_types import (
    ConfidenceScore,
    ConfidenceLevel,
    ConfidenceThresholds,
)

# Error and status types
from .status_types import (
    ProcessingStatus,
    ErrorCode,
    ErrorDetail,
    ProcessingResult,
)

# Message queue types
from .message_types import (
    RabbitMQMessage,
    MessagePayload,
    MessageHeaders,
    MessagePriority,
)

# Storage types
from .storage_types import (
    S3Location,
    StorageCredentials,
    StorageOptions,
    EncryptionType,
)

# Common utility types
from .common_types import (
    JSONDict,
    Coordinates,
    BoundingBox,
    ImageSize,
    TimeStamp,
    UUID,
)

# Version information
__version__ = '1.0.0'