#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Test Models Package

This package contains test modules for the TensorFlow models used in the OCR Service
of the Merchant Cash Advance (MCA) Application Processing System. It provides a
structured testing framework for verifying model functionality, accuracy, and performance.

The test modules in this package validate that the OCR models correctly extract data
from various document types with 99% accuracy using machine learning techniques. They
cover both typed and handwritten text recognition, as well as document structure analysis.

Test Modules:
    - test_base_model: Tests for the abstract base class for OCR models
    - test_typed_text_model: Tests for the typed/printed text recognition model
    - test_handwritten_text_model: Tests for the handwritten text recognition model
    - test_hybrid_recognition_model: Tests for the combined model for mixed content
    - test_structure_recognition_model: Tests for document structure analysis
    - test_model_factory: Tests for the model factory class
    - test_confidence_scoring: Tests for confidence scoring utilities

Test Fixtures:
    - Shared test fixtures are defined in conftest.py
    - These include document test data, TensorFlow environment setup, and model mocks

All tests validate that models meet the system requirements:
    - 99% data extraction accuracy
    - Processing applications in under 5 minutes
    - GPU acceleration with CUDA-compatible hardware
"""

__version__ = '1.0.0'
__author__ = 'Dollar Funding MCA Team'

# Import test utilities and fixtures from conftest
from .conftest import (
    # TensorFlow environment fixtures
    tf_config,
    mock_gpu_environment,
    tf_session,
    
    # Document test data fixtures
    metadata,
    typed_document_paths,
    handwritten_document_paths,
    mixed_document_paths,
    table_document_paths,
    form_document_paths,
    image_document_paths,
    document_by_id,
    load_test_document,
    
    # Model initialization fixtures
    mock_typed_text_model,
    mock_handwritten_text_model,
    mock_hybrid_text_model,
    mock_structure_recognition_model,
    
    # Accuracy and performance measurement utilities
    calculate_accuracy,
    measure_performance,
    accuracy_metrics,
    
    # Document preprocessing utilities
    preprocess_document,
    apply_image_distortions,
    
    # Additional test utilities
    expected_field_values,
    create_test_image
)

# Define public API
__all__ = [
    # Version info
    '__version__',
    '__author__',
    
    # TensorFlow environment fixtures
    'tf_config',
    'mock_gpu_environment',
    'tf_session',
    
    # Document test data fixtures
    'metadata',
    'typed_document_paths',
    'handwritten_document_paths',
    'mixed_document_paths',
    'table_document_paths',
    'form_document_paths',
    'image_document_paths',
    'document_by_id',
    'load_test_document',
    
    # Model initialization fixtures
    'mock_typed_text_model',
    'mock_handwritten_text_model',
    'mock_hybrid_text_model',
    'mock_structure_recognition_model',
    
    # Accuracy and performance measurement utilities
    'calculate_accuracy',
    'measure_performance',
    'accuracy_metrics',
    
    # Document preprocessing utilities
    'preprocess_document',
    'apply_image_distortions',
    
    # Additional test utilities
    'expected_field_values',
    'create_test_image'
]