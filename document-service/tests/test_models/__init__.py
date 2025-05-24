# -*- coding: utf-8 -*-
"""
Test package for document classification models.

This package contains test modules for all components of the document classification
system, including base models, specific classifier implementations (SVM, Random Forest),
feature extraction, model training, evaluation, and serialization.

The package provides shared fixtures, constants, and utility functions to simplify
writing and maintaining tests for the document classification models.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path to allow imports from the models package
src_path = str(Path(__file__).parent.parent.parent / 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Constants for test data paths
TEST_DATA_DIR = Path(__file__).parent.parent / 'test_data'
TEST_DOCUMENTS_DIR = TEST_DATA_DIR / 'documents'
TEST_MODELS_DIR = TEST_DATA_DIR / 'models'

# Document type constants for testing
DOCUMENT_TYPES = [
    'invoice',
    'bank_statement',
    'tax_return',
    'id_document',
    'business_license',
    'utility_bill',
    'credit_report',
    'financial_statement',
    'application_form',
    'miscellaneous'
]

# Confidence threshold constants
HIGH_CONFIDENCE_THRESHOLD = 0.9
MEDIUM_CONFIDENCE_THRESHOLD = 0.7
LOW_CONFIDENCE_THRESHOLD = 0.5

# Model performance thresholds for testing
MIN_ACCURACY_THRESHOLD = 0.99  # 99% accuracy requirement
MIN_PRECISION_THRESHOLD = 0.95
MIN_RECALL_THRESHOLD = 0.95
MIN_F1_THRESHOLD = 0.95

# Utility functions for test data generation
def get_test_document_path(document_type, filename):
    """Get the path to a test document file.
    
    Args:
        document_type (str): Type of document (e.g., 'invoice', 'bank_statement')
        filename (str): Name of the test document file
        
    Returns:
        Path: Path object pointing to the test document
    """
    return TEST_DOCUMENTS_DIR / document_type / filename


def get_test_model_path(model_type, version='latest'):
    """Get the path to a test model file.
    
    Args:
        model_type (str): Type of model (e.g., 'svm', 'random_forest')
        version (str): Model version, defaults to 'latest'
        
    Returns:
        Path: Path object pointing to the test model
    """
    return TEST_MODELS_DIR / model_type / f"{model_type}_{version}.pkl"