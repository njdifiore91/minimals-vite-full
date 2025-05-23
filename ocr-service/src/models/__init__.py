"""OCR Models Package for Dollar Funding MCA Application Processing System.

This package provides TensorFlow-based OCR models for extracting data from various
document types with high accuracy. The models are designed to handle both typed and
handwritten text, as well as document structure recognition.

Usage:
    from ocr_service.models import TypedTextModel, HandwrittenTextModel
    from ocr_service.models import get_model

    # Using specific model directly
    model = TypedTextModel()
    results = model.extract_text(image)

    # Using factory to get appropriate model based on document type
    model = get_model(document_type='invoice')
    results = model.extract_text(image)

Models:
    - BaseModel: Abstract base class for all OCR models
    - TypedTextModel: Model for typed/printed text recognition
    - HandwrittenTextModel: Model for handwritten text recognition
    - HybridRecognitionModel: Model for documents with both typed and handwritten text
    - StructureRecognitionModel: Model for document structure recognition

Utilities:
    - calculate_confidence: Calculate confidence score for extracted text
    - normalize_confidence: Normalize confidence scores across different models
    - get_model: Factory function to get appropriate model based on document type
"""

# Version information
__version__ = '1.0.0'
__author__ = 'Dollar Funding'
__description__ = 'TensorFlow OCR models for document processing'

# Import main classes from model files
from .base_model import BaseModel
from .typed_text_model import TypedTextModel
from .handwritten_text_model import HandwrittenTextModel
from .hybrid_recognition_model import HybridRecognitionModel
from .structure_recognition_model import StructureRecognitionModel
from .model_factory import ModelFactory

# Import confidence scoring utilities
from .confidence_scoring import (
    calculate_confidence,
    normalize_confidence,
    get_confidence_threshold,
    is_confidence_sufficient
)

# Convenient factory function
def get_model(document_type=None, document_metadata=None):
    """Get appropriate OCR model based on document type and metadata.
    
    This is a convenience function that uses ModelFactory to create and return
    the appropriate OCR model for the given document type and metadata.
    
    Args:
        document_type (str, optional): Type of document (e.g., 'invoice', 'application_form').
            If None, will be determined from document_metadata if possible.
        document_metadata (dict, optional): Additional metadata about the document
            that can help determine the appropriate model.
            
    Returns:
        BaseModel: An instance of the appropriate OCR model for the document.
        
    Examples:
        >>> model = get_model('invoice')
        >>> results = model.extract_text(image)
        
        >>> model = get_model(document_metadata={'has_handwriting': True})
        >>> results = model.extract_text(image)
    """
    factory = ModelFactory()
    return factory.create_model(document_type, document_metadata)


# Define public API
__all__ = [
    # Models
    'BaseModel',
    'TypedTextModel',
    'HandwrittenTextModel',
    'HybridRecognitionModel',
    'StructureRecognitionModel',
    'ModelFactory',
    
    # Factory function
    'get_model',
    
    # Confidence utilities
    'calculate_confidence',
    'normalize_confidence',
    'get_confidence_threshold',
    'is_confidence_sufficient',
]
    