#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Services Package

This package provides service components for the OCR Service microservice, offering
a cohesive API surface for service functionality throughout the application. It includes
services for OCR processing, queue management, storage operations, field extraction,
and confidence scoring.

By centralizing service imports in this package, we ensure consistent service usage
across the application and provide a clean import interface for developers.

Example usage:
    from services import OCRService, QueueService, StorageService
    
    ocr_service = OCRService()
    result = ocr_service.process_document(document)
"""

from __future__ import annotations

# Import and re-export OCR service
from .ocr_service import OCRService

# Import and re-export queue service
from .queue_service import QueueService

# Import and re-export storage service
from .storage_service import StorageService

# Import and re-export field extraction service
from .field_extraction_service import FieldExtractionService

# Import and re-export confidence service
from .confidence_service import ConfidenceService

# Define __all__ to explicitly specify exported names
__all__ = [
    # OCR processing service
    'OCRService',
    
    # Queue management service
    'QueueService',
    
    # Storage operations service
    'StorageService',
    
    # Field extraction service
    'FieldExtractionService',
    
    # Confidence scoring service
    'ConfidenceService',
]