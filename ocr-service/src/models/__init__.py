# -*- coding: utf-8 -*-
"""
OCR Service Models Package

This package contains the TensorFlow models used for Optical Character Recognition (OCR)
in the Merchant Cash Advance (MCA) Application Processing System. It provides a clean,
well-organized API for model access throughout the OCR service.

The models in this package are designed to extract data from various document types
with 99% accuracy using machine learning techniques. They support both typed and
handwritten text recognition, as well as document structure analysis.

Models:
    - TypedTextModel: For recognizing and extracting typed/printed text
    - HandwrittenTextModel: For recognizing and extracting handwritten text
    - HybridRecognitionModel: Combined model for documents with mixed content
    - StructureRecognitionModel: For analyzing document structure and layout

Utilities:
    - ModelFactory: Factory class for creating appropriate models based on document type
    - confidence_scoring: Utilities for calculating confidence scores for extracted text

All models require GPU acceleration with CUDA-compatible hardware (min 8GB VRAM).
"""

__version__ = '1.0.0'
__author__ = 'Dollar Funding MCA Team'

# Import base model
from .base_model import BaseModel

# Import concrete model implementations
from .typed_text_model import TypedTextModel
from .handwritten_text_model import HandwrittenTextModel
from .hybrid_recognition_model import HybridRecognitionModel
from .structure_recognition_model import StructureRecognitionModel

# Import model factory
from .model_factory import ModelFactory

# Import confidence scoring utilities
from .confidence_scoring import (
    calculate_confidence_score,
    get_field_confidence,
    is_confidence_above_threshold,
    enrich_with_confidence_metadata
)

# Define public API
__all__ = [
    # Version info
    '__version__',
    '__author__',
    
    # Models
    'BaseModel',
    'TypedTextModel',
    'HandwrittenTextModel',
    'HybridRecognitionModel',
    'StructureRecognitionModel',
    
    # Factory
    'ModelFactory',
    
    # Confidence scoring utilities
    'calculate_confidence_score',
    'get_field_confidence',
    'is_confidence_above_threshold',
    'enrich_with_confidence_metadata',
    
    # Convenience functions
    'create_model_for_document',
    'get_model_by_type'
]

# Convenience functions
def create_model_for_document(document, config=None):
    """
    Create an appropriate OCR model for the given document.
    
    This is a convenience function that uses the ModelFactory to create
    the most appropriate model based on document classification metadata.
    
    Args:
        document: Document object containing metadata and content
        config: Optional configuration dictionary for model parameters
        
    Returns:
        An instance of a concrete OCR model (TypedTextModel, HandwrittenTextModel, etc.)
    """
    factory = ModelFactory(config)
    return factory.create_for_document(document)

def get_model_by_type(model_type, config=None):
    """
    Get a specific OCR model by its type.
    
    This is a convenience function that uses the ModelFactory to create
    a model of the specified type with the given configuration.
    
    Args:
        model_type: String or enum value specifying the model type
                   (e.g., 'TYPED', 'HANDWRITTEN', 'HYBRID', 'STRUCTURE')
        config: Optional configuration dictionary for model parameters
        
    Returns:
        An instance of the requested OCR model
    """
    factory = ModelFactory(config)
    return factory.create_by_type(model_type)