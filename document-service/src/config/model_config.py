#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Configuration for Document Service

This module defines configuration parameters for the machine learning models used in document
classification. It specifies model types (SVM, Random Forest), hyperparameters, feature extraction
settings, classification thresholds, and model paths.

The configuration ensures consistent model behavior across environments and enables accurate
document classification with the required 99% accuracy threshold specified in the technical
requirements.

Features:
    - Model type configuration (SVM, Random Forest)
    - Hyperparameter settings for each model type
    - Feature extraction parameters
    - Classification confidence thresholds
    - Model paths and versioning
    - Environment-specific configurations
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union, Literal

from ..types.config import ModelConfig
from .app_config import get_app_config, Environment

# Set up logging
logger = logging.getLogger(__name__)

# Get application configuration
app_config = get_app_config()

# Base directory for model storage
MODEL_BASE_DIR = os.path.join(app_config.service.base_path, "models")

# Model version
MODEL_VERSION = "1.0.0"

# Document types supported by the classification system
SUPPORTED_DOCUMENT_TYPES = [
    "APPLICATION",              # MCA application form
    "TAX_RETURN",              # Business tax return
    "BANK_STATEMENT",          # Bank account statement
    "PROFIT_LOSS",             # Profit and loss statement
    "BALANCE_SHEET",           # Balance sheet
    "BUSINESS_LICENSE",         # Business license or permit
    "IDENTITY_DOCUMENT",        # Identity document (driver's license, passport)
    "UTILITY_BILL",            # Utility bill for address verification
    "CREDIT_CARD_STATEMENT",    # Credit card processing statement
    "LEASE_AGREEMENT",         # Commercial lease agreement
    "INSURANCE_DOCUMENT",       # Business insurance document
    "INVOICE",                 # Invoice or bill
    "OTHER"                    # Unclassified document type
]

# Classification confidence thresholds by environment
CONFIDENCE_THRESHOLDS = {
    Environment.DEVELOPMENT: 0.65,  # Lower threshold for development
    Environment.STAGING: 0.75,      # Medium threshold for staging
    Environment.PRODUCTION: 0.85,    # Higher threshold for production
}

# Default confidence threshold (used if environment is not recognized)
DEFAULT_CONFIDENCE_THRESHOLD = 0.75

# Get the appropriate confidence threshold for the current environment
CONFIDENCE_THRESHOLD = CONFIDENCE_THRESHOLDS.get(
    app_config.service.environment, 
    DEFAULT_CONFIDENCE_THRESHOLD
)

# Model file paths
MODEL_PATHS = {
    "svm": os.path.join(MODEL_BASE_DIR, f"svm_classifier_{MODEL_VERSION}.pkl"),
    "random_forest": os.path.join(MODEL_BASE_DIR, f"random_forest_classifier_{MODEL_VERSION}.pkl"),
    "vectorizer": os.path.join(MODEL_BASE_DIR, f"tfidf_vectorizer_{MODEL_VERSION}.pkl"),
    "feature_selector": os.path.join(MODEL_BASE_DIR, f"feature_selector_{MODEL_VERSION}.pkl"),
}

# Feature extraction parameters
FEATURE_EXTRACTION = {
    "max_features": 10000,           # Maximum number of features for TF-IDF vectorizer
    "ngram_range": (1, 2),           # Use unigrams and bigrams
    "min_df": 5,                     # Minimum document frequency
    "max_df": 0.85,                  # Maximum document frequency (as a fraction)
    "use_idf": True,                 # Use inverse document frequency
    "sublinear_tf": True,            # Apply sublinear term frequency scaling
    "strip_accents": "unicode",      # Remove accents
    "analyzer": "word",              # Analyze by word (not character)
    "stop_words": "english",         # Remove English stop words
    "lowercase": True,               # Convert to lowercase
    "max_document_length": 50000,    # Maximum document length to process
    "pca_components": 500,           # Number of PCA components (if dimensionality reduction is used)
    "use_pca": False,                # Whether to use PCA for dimensionality reduction
}

# SVM model parameters
SVM_PARAMS = {
    "kernel": "linear",              # Kernel type (linear, rbf, poly, sigmoid)
    "C": 1.0,                        # Regularization parameter
    "probability": True,             # Enable probability estimates
    "class_weight": "balanced",      # Adjust weights inversely proportional to class frequencies
    "random_state": 42,              # Random seed for reproducibility
    "verbose": False,                # Verbose output during training
    "max_iter": 1000,               # Maximum number of iterations
    "tol": 1e-4,                     # Tolerance for stopping criterion
    "decision_function_shape": "ovr", # One-vs-rest decision function
    "gamma": "scale",                # Kernel coefficient for rbf, poly and sigmoid
    "degree": 3,                     # Degree of polynomial kernel function
    "coef0": 0.0,                    # Independent term in kernel function
    "shrinking": True,               # Use shrinking heuristic
    "cache_size": 200,               # Kernel cache size in MB
    "break_ties": False,             # Break ties according to confidence
}

# Random Forest model parameters
RANDOM_FOREST_PARAMS = {
    "n_estimators": 200,             # Number of trees in the forest
    "criterion": "gini",             # Function to measure quality of split
    "max_depth": None,               # Maximum depth of the tree
    "min_samples_split": 2,          # Minimum samples required to split an internal node
    "min_samples_leaf": 1,           # Minimum samples required to be at a leaf node
    "min_weight_fraction_leaf": 0.0, # Minimum weighted fraction of the sum total of weights
    "max_features": "sqrt",          # Number of features to consider for best split
    "max_leaf_nodes": None,          # Maximum number of leaf nodes
    "min_impurity_decrease": 0.0,    # Minimum decrease in impurity required for split
    "bootstrap": True,               # Use bootstrap samples
    "oob_score": True,               # Use out-of-bag samples to estimate generalization score
    "n_jobs": -1,                    # Number of jobs to run in parallel (-1 means using all processors)
    "random_state": 42,              # Random seed for reproducibility
    "verbose": 0,                    # Verbose output during training
    "warm_start": False,             # Reuse the solution of the previous call
    "class_weight": "balanced",      # Adjust weights inversely proportional to class frequencies
    "ccp_alpha": 0.0,                # Complexity parameter for minimal cost-complexity pruning
    "max_samples": None,             # Number of samples to draw from X to train each base estimator
}

# Model training parameters
TRAINING_PARAMS = {
    "test_size": 0.2,                 # Fraction of data to use for testing
    "cv_folds": 5,                   # Number of cross-validation folds
    "hyperparameter_tuning": True,    # Whether to perform hyperparameter tuning
    "n_iter_search": 20,             # Number of parameter settings sampled in random search
    "early_stopping": True,          # Whether to use early stopping during training
    "early_stopping_rounds": 5,      # Number of rounds with no improvement to trigger early stopping
    "stratify": True,                # Whether to stratify the train/test split
    "shuffle": True,                 # Whether to shuffle the data before splitting
    "random_state": 42,              # Random seed for reproducibility
    "save_best_model": True,         # Whether to save the best model during cross-validation
    "refit": True,                   # Whether to refit the model on the entire dataset after CV
}

# Model evaluation parameters
EVALUATION_PARAMS = {
    "accuracy_threshold": 0.99,        # Required accuracy threshold (99% as per technical spec)
    "metrics": ["accuracy", "precision", "recall", "f1", "roc_auc"],  # Metrics to calculate
    "generate_confusion_matrix": True,  # Whether to generate confusion matrix
    "generate_roc_curve": True,        # Whether to generate ROC curve
    "generate_precision_recall_curve": True,  # Whether to generate precision-recall curve
    "generate_feature_importance": True,  # Whether to generate feature importance plot
    "save_evaluation_results": True,    # Whether to save evaluation results
    "evaluation_results_path": os.path.join(MODEL_BASE_DIR, "evaluation_results"),  # Path to save evaluation results
}

# Model validation parameters
VALIDATION_PARAMS = {
    "validation_size": 0.1,            # Fraction of data to use for validation
    "min_samples_per_class": 10,      # Minimum number of samples required per class
    "validation_frequency": "daily",   # How often to validate the model
    "alert_on_performance_drop": True,  # Whether to alert on performance drop
    "performance_drop_threshold": 0.05,  # Threshold for performance drop to trigger alert
    "retraining_threshold": 0.1,      # Performance drop threshold to trigger retraining
}

# Document processing parameters
DOCUMENT_PROCESSING = {
    "max_document_size_mb": 10,       # Maximum document size in MB
    "supported_formats": ["pdf", "png", "jpg", "jpeg", "tiff", "tif", "bmp", "txt"],  # Supported document formats
    "extract_text": True,             # Whether to extract text from documents
    "extract_metadata": True,         # Whether to extract metadata from documents
    "extract_images": True,           # Whether to extract images from documents
    "ocr_engine": "tesseract",        # OCR engine to use (tesseract, textract)
    "ocr_language": "eng",            # OCR language
    "dpi": 300,                       # DPI for image processing
    "batch_size": 32,                 # Batch size for document processing
    "timeout": 300,                   # Timeout for document processing in seconds
    "max_pages": 50,                  # Maximum number of pages to process
    "extract_tables": True,           # Whether to extract tables from documents
}

# Hardware resource constraints
HARDWARE_CONSTRAINTS = {
    "memory_limit_mb": 16384,          # Minimum 16GB RAM required as per spec
    "gpu_acceleration": False,         # Whether to use GPU acceleration
    "gpu_memory_limit_mb": 8192,       # GPU memory limit in MB
    "cpu_count": -1,                   # Number of CPU cores to use (-1 means all available)
    "disk_space_limit_mb": 10240,      # Disk space limit in MB
    "temp_directory": "/tmp/document-service",  # Temporary directory for processing
}

# Create the complete model configuration
def create_model_config() -> ModelConfig:
    """
    Create and return the model configuration.
    
    This function combines all model-related configuration parameters into a single
    ModelConfig object that can be used throughout the Document Service.
    
    Returns:
        ModelConfig: Complete model configuration
    """
    model_config = {
        "model_path": MODEL_PATHS.get(app_config.model.model_type, MODEL_PATHS["random_forest"]),
        "vectorizer_path": MODEL_PATHS["vectorizer"],
        "min_confidence_threshold": CONFIDENCE_THRESHOLD,
        "supported_document_types": SUPPORTED_DOCUMENT_TYPES,
        "batch_size": DOCUMENT_PROCESSING["batch_size"],
        "max_document_size_mb": DOCUMENT_PROCESSING["max_document_size_mb"],
        "gpu_acceleration": HARDWARE_CONSTRAINTS["gpu_acceleration"],
        "memory_limit_mb": HARDWARE_CONSTRAINTS["memory_limit_mb"],
    }
    
    # Add model-specific parameters based on the selected model type
    if app_config.model.model_type == "svm":
        model_config.update(SVM_PARAMS)
    elif app_config.model.model_type == "random_forest":
        model_config.update(RANDOM_FOREST_PARAMS)
    else:
        logger.warning(f"Unknown model type: {app_config.model.model_type}. Using Random Forest parameters.")
        model_config.update(RANDOM_FOREST_PARAMS)
    
    # Add feature extraction parameters
    model_config.update({
        "feature_extraction": FEATURE_EXTRACTION,
        "training": TRAINING_PARAMS,
        "evaluation": EVALUATION_PARAMS,
        "validation": VALIDATION_PARAMS,
        "document_processing": DOCUMENT_PROCESSING,
        "hardware_constraints": HARDWARE_CONSTRAINTS,
    })
    
    return model_config


# Create the model configuration
model_config = create_model_config()


def get_model_config() -> ModelConfig:
    """
    Get the model configuration.
    
    This function returns the singleton instance of the model configuration.
    
    Returns:
        ModelConfig: The model configuration
    """
    return model_config


# Export the configuration object
__all__ = ["model_config", "get_model_config", "SUPPORTED_DOCUMENT_TYPES", "MODEL_VERSION"]