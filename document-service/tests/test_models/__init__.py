# -*- coding: utf-8 -*-
"""
Test package for document classification models.

This package contains tests for the document classification models used in the
Document Service. It validates the functionality and accuracy of the SVM and
Random Forest classifiers, as well as the feature extraction, model training,
and evaluation utilities.

The tests in this package ensure that the document classification models meet
the 99% accuracy requirement specified in the technical specification.
"""

import os
import sys
from typing import Dict, List, Tuple, Any, Optional, Union, Callable

# Constants for test configuration
TEST_ACCURACY_THRESHOLD = 0.99  # 99% accuracy requirement
TEST_CONFIDENCE_THRESHOLD = 0.7  # Minimum confidence for classification

# Add helper functions that might be useful across test modules
def get_test_data_path() -> str:
    """
    Get the path to the test data directory.
    
    Returns:
        str: Absolute path to the test data directory
    """
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_data')


def get_model_test_config() -> Dict[str, Any]:
    """
    Get the default test configuration for model testing.
    
    This configuration includes settings for both SVM and Random Forest classifiers,
    as well as feature extraction parameters optimized for testing.
    
    Returns:
        Dict[str, Any]: Default test configuration
    """
    return {
        'models': {
            'svm': {
                'enabled': True,
                'weight': 0.5,
                'params': {
                    'C': 1.0,
                    'kernel': 'linear',
                    'gamma': 'scale',
                    'probability': True,
                    'class_weight': 'balanced',
                    'random_state': 42
                }
            },
            'random_forest': {
                'enabled': True,
                'weight': 0.5,
                'params': {
                    'n_estimators': 100,
                    'max_depth': 20,
                    'min_samples_split': 2,
                    'min_samples_leaf': 1,
                    'bootstrap': True,
                    'oob_score': True,
                    'class_weight': 'balanced',
                    'random_state': 42
                }
            }
        },
        'feature_extraction': {
            'tfidf': {
                'enabled': True,
                'max_features': 100,
                'ngram_range': [1, 2],
                'min_df': 2,
                'max_df': 0.9,
                'stop_words': 'english'
            },
            'metadata': {
                'enabled': True,
                'features': ['page_count', 'file_size', 'mime_type']
            }
        },
        'testing': {
            'accuracy_threshold': TEST_ACCURACY_THRESHOLD,
            'confidence_threshold': TEST_CONFIDENCE_THRESHOLD,
            'test_size': 0.3,
            'cross_validation_folds': 5,
            'random_state': 42
        }
    }


def setup_test_environment() -> None:
    """
    Set up the test environment for model testing.
    
    This function ensures that the necessary paths are added to sys.path
    and that any required environment variables are set.
    """
    # Add the src directory to the Python path if needed
    src_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    # Set environment variables for testing if needed
    os.environ.setdefault('DOCUMENT_SERVICE_ENV', 'test')


# Initialize the test environment when the package is imported
setup_test_environment()