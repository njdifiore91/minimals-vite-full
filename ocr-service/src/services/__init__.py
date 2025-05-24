#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service - Services Package

This module serves as the central entry point for the OCR Service services module.
It imports and re-exports all service components to present a single, cohesive API surface,
simplifying service imports throughout the application and ensuring consistent service usage.

Services included:
- OCRService: Core OCR processing service that orchestrates TensorFlow models for text extraction
- QueueService: RabbitMQ message handling service for consuming and publishing messages
- StorageService: S3-compatible storage operations for document retrieval and storage
- FieldExtractionService: Specialized service for extracting structured data from OCR results
- ConfidenceService: Evaluates the confidence of extracted fields and flags uncertain extractions

Usage examples:
    from services import OCRService
    from services import QueueService
    from services import StorageService
    from services import FieldExtractionService
    from services import ConfidenceService

    # Or import all services
    from services import *
"""

# Import all services to expose them at the package level
from .ocr_service import OCRService
from .queue_service import QueueService
from .storage_service import StorageService
from .field_extraction_service import FieldExtractionService
from .confidence_service import ConfidenceService

# Define __all__ to control what is imported with 'from services import *'
__all__ = [
    'OCRService',
    'QueueService',
    'StorageService',
    'FieldExtractionService',
    'ConfidenceService'
]