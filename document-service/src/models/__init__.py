#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service Models Package

This package provides document classification models and utilities for the Document Service.
It includes base model interfaces, specific classifier implementations (SVM, Random Forest),
feature extraction utilities, model training, evaluation, and serialization components.

The models in this package are designed to achieve 99% classification accuracy as specified
in the technical requirements for the Document Service.

Classes:
    BaseModel: Abstract base class for all document classifiers
    SVMClassifier: Support Vector Machine classifier implementation
    RandomForestClassifier: Random Forest classifier implementation
    DocumentClassifier: Main document classifier that orchestrates the classification process
    
    TextExtractor: Extracts text from various document formats
    TextPreprocessor: Preprocesses text for feature extraction
    TfidfFeatureExtractor: Extracts TF-IDF features from text
    MetadataFeatureExtractor: Extracts features from document metadata
    DimensionalityReducer: Reduces dimensionality of feature vectors
    FeatureExtractor: Main class for feature extraction
    
    ModelEvaluator: Evaluates model performance against requirements
    ModelTrainer: Trains and fine-tunes classification models

Functions:
    save_model: Serialize and save a trained model with metadata
    load_model: Load a serialized model with validation
    list_models: List all available models in the registry
    get_model_metadata: Retrieve metadata for a specific model
    register_model: Register a model in the model registry
    delete_model: Remove a model from storage and registry
    rollback_model: Rollback to a previous model version
    validate_model: Validate model integrity and compatibility
    
    prepare_dataset: Split dataset into training and testing sets
    optimize_hyperparameters: Find optimal hyperparameters for a model
    train_model_with_cv: Train a model with cross-validation
    plot_learning_curve: Plot learning curve for model evaluation
    plot_precision_recall_curve: Plot precision-recall curve
    plot_calibration_curve: Plot calibration curve
    evaluate_model_performance: Evaluate a model's performance
"""

# Import base model
from .base_model import BaseModel

# Import classifier implementations
from .svm_classifier import SVMClassifier
from .random_forest_classifier import RandomForestClassifier
from .document_classifier import DocumentClassifier

# Import feature extraction utilities
from .feature_extraction import (
    TextExtractor,
    TextPreprocessor,
    TfidfFeatureExtractor,
    MetadataFeatureExtractor,
    DimensionalityReducer,
    FeatureExtractor
)

# Import model serialization utilities
from .model_serialization import (
    save_model,
    load_model,
    list_models,
    get_model_metadata,
    register_model,
    delete_model,
    rollback_model,
    validate_model
)

# Import model evaluation utilities
from .model_evaluation import (
    ModelEvaluator,
    plot_learning_curve,
    plot_precision_recall_curve,
    plot_calibration_curve,
    evaluate_model_performance
)

# Import model training utilities
from .model_training import (
    ModelTrainer,
    prepare_dataset,
    optimize_hyperparameters,
    train_model_with_cv
)

__all__ = [
    # Base model
    'BaseModel',
    
    # Classifier implementations
    'SVMClassifier',
    'RandomForestClassifier',
    'DocumentClassifier',
    
    # Feature extraction
    'TextExtractor',
    'TextPreprocessor',
    'TfidfFeatureExtractor',
    'MetadataFeatureExtractor',
    'DimensionalityReducer',
    'FeatureExtractor',
    
    # Model serialization
    'save_model',
    'load_model',
    'list_models',
    'get_model_metadata',
    'register_model',
    'delete_model',
    'rollback_model',
    'validate_model',
    
    # Model evaluation
    'ModelEvaluator',
    'plot_learning_curve',
    'plot_precision_recall_curve',
    'plot_calibration_curve',
    'evaluate_model_performance',
    
    # Model training
    'ModelTrainer',
    'prepare_dataset',
    'optimize_hyperparameters',
    'train_model_with_cv'
]