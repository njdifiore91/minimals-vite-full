"""Test Models Package for Dollar Funding MCA OCR Service.

This package contains test modules for validating the OCR models used in the
Dollar Funding MCA Application Processing System. The tests verify that the models
correctly extract data from various document types with high accuracy, including
both typed and handwritten text.

Test Modules:
    - test_base_model: Tests for the abstract base class for OCR models
    - test_typed_text_model: Tests for typed/printed text recognition model
    - test_handwritten_text_model: Tests for handwritten text recognition model
    - test_hybrid_recognition_model: Tests for mixed text type recognition model
    - test_structure_recognition_model: Tests for document structure recognition model
    - test_model_factory: Tests for the model factory class
    - test_confidence_scoring: Tests for confidence scoring utilities

Usage:
    # Run all model tests
    pytest ocr-service/tests/test_models

    # Run specific model test
    pytest ocr-service/tests/test_models/test_typed_text_model.py
"""

# Version information
__version__ = '1.0.0'
__author__ = 'Dollar Funding'
__description__ = 'Test suite for TensorFlow OCR models'

# Import common test utilities that may be needed across test modules
from ..conftest import *

# Make test utilities available for import across test files
from .conftest import (
    # TensorFlow environment fixtures
    tf_gpu_mock,
    tf_session,
    
    # Test image fixtures
    sample_typed_image,
    sample_handwritten_image,
    sample_mixed_image,
    sample_table_image,
    
    # Model configuration fixtures
    base_model_config,
    typed_model_config,
    handwritten_model_config,
    hybrid_model_config,
    structure_model_config,
    
    # Mock model fixtures
    mock_base_model,
    mock_typed_model,
    mock_handwritten_model,
    mock_hybrid_model,
    mock_structure_model,
    mock_model_factory,
    
    # Helper functions
    accuracy_calculator,
    performance_timer,
    document_preprocessor,
    confidence_score_validator,
    
    # Test data manifests
    metadata,
    typed_document_manifest,
    handwritten_document_manifest,
    mixed_document_manifest
)

# Define what should be available when importing from this package
__all__ = [
    # TensorFlow environment fixtures
    'tf_gpu_mock',
    'tf_session',
    
    # Test image fixtures
    'sample_typed_image',
    'sample_handwritten_image',
    'sample_mixed_image',
    'sample_table_image',
    
    # Model configuration fixtures
    'base_model_config',
    'typed_model_config',
    'handwritten_model_config',
    'hybrid_model_config',
    'structure_model_config',
    
    # Mock model fixtures
    'mock_base_model',
    'mock_typed_model',
    'mock_handwritten_model',
    'mock_hybrid_model',
    'mock_structure_model',
    'mock_model_factory',
    
    # Helper functions
    'accuracy_calculator',
    'performance_timer',
    'document_preprocessor',
    'confidence_score_validator',
    
    # Test data manifests
    'metadata',
    'typed_document_manifest',
    'handwritten_document_manifest',
    'mixed_document_manifest'
]