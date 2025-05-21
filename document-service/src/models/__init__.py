#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service Models Package.

This package provides the document classification models and related utilities for the Document Service.
It includes implementations of SVM and Random Forest classifiers, feature extraction utilities,
model training and evaluation tools, and the main document classifier that orchestrates the
classification process.

The models in this package are designed to achieve 99% classification accuracy for document types
and provide confidence scores for classification decisions. They support the document classification
requirements of the Merchant Cash Advance (MCA) Application Processing System.

Example usage:
    # Import the main document classifier
    from document_service.models import DocumentClassifier
    
    # Create and train a classifier
    classifier = DocumentClassifier()
    classifier.fit(documents, document_types)
    
    # Classify a document
    result = classifier.classify_document(document)
    
    # Import specific model implementations
    from document_service.models import SVMClassifier, RandomForestClassifier
    
    # Create and train a specific classifier
    svm = SVMClassifier()
    svm.fit(features, labels)
"""

# Import and re-export base model
from .base_model import BaseModel

# Import and re-export classifier implementations
from .svm_classifier import SVMClassifier
from .random_forest_classifier import RandomForestClassifier
from .document_classifier import DocumentClassifier

# Import and re-export model utilities
from .model_serialization import save_model, load_model
from .model_evaluation import evaluate_classifier, calculate_metrics, plot_confusion_matrix
from .model_training import train_model, optimize_hyperparameters, cross_validate
from .feature_extraction import extract_document_features, extract_text_features, extract_metadata_features

# Define package exports
__all__ = [
    # Base model
    'BaseModel',
    
    # Classifier implementations
    'SVMClassifier',
    'RandomForestClassifier',
    'DocumentClassifier',
    
    # Model serialization
    'save_model',
    'load_model',
    
    # Model evaluation
    'evaluate_classifier',
    'calculate_metrics',
    'plot_confusion_matrix',
    
    # Model training
    'train_model',
    'optimize_hyperparameters',
    'cross_validate',
    
    # Feature extraction
    'extract_document_features',
    'extract_text_features',
    'extract_metadata_features',
]