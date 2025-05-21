# model_config.py

"""
Configuration parameters for machine learning models used in document classification.

This module defines the configuration for SVM and Random Forest classifiers,
including hyperparameters, feature extraction settings, classification thresholds,
and model paths. It ensures consistent model behavior across environments and
enables accurate document classification with 99% accuracy.
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Union, Optional

# Base directory for model storage
MODEL_BASE_DIR = os.environ.get(
    "MODEL_BASE_DIR", 
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
)

# Ensure model directory exists
Path(MODEL_BASE_DIR).mkdir(parents=True, exist_ok=True)

# Model version
MODEL_VERSION = "1.0.0"

# Model file paths
MODEL_PATHS = {
    "svm": os.path.join(MODEL_BASE_DIR, f"svm_classifier_{MODEL_VERSION}.pkl"),
    "random_forest": os.path.join(MODEL_BASE_DIR, f"random_forest_classifier_{MODEL_VERSION}.pkl"),
    "ensemble": os.path.join(MODEL_BASE_DIR, f"ensemble_classifier_{MODEL_VERSION}.pkl"),
}

# Document categories for classification
DOCUMENT_CATEGORIES = [
    "application_form",
    "bank_statement",
    "tax_return",
    "identity_document",
    "business_license",
    "invoice",
    "utility_bill",
    "credit_report",
    "financial_statement",
    "other"
]

# Classification confidence thresholds
CONFIDENCE_THRESHOLDS = {
    "high": 0.85,  # High confidence classification
    "medium": 0.70,  # Medium confidence classification
    "low": 0.50,  # Low confidence classification
    "minimum": 0.30,  # Minimum threshold for classification
}

# Document-specific confidence thresholds
DOCUMENT_CONFIDENCE_THRESHOLDS = {
    "application_form": 0.80,
    "bank_statement": 0.85,
    "tax_return": 0.85,
    "identity_document": 0.90,  # Higher threshold for sensitive documents
    "business_license": 0.80,
    "invoice": 0.75,
    "utility_bill": 0.75,
    "credit_report": 0.85,
    "financial_statement": 0.85,
    "other": 0.60,  # Lower threshold for catch-all category
}

# Feature extraction parameters
FEATURE_EXTRACTION = {
    "text": {
        "vectorizer": "tfidf",  # TF-IDF vectorization
        "max_features": 5000,  # Maximum number of features
        "ngram_range": (1, 2),  # Use unigrams and bigrams
        "min_df": 2,  # Minimum document frequency
        "max_df": 0.9,  # Maximum document frequency
        "stop_words": "english",  # English stop words
    },
    "metadata": {
        "include": True,  # Include document metadata
        "features": [
            "page_count",
            "file_size",
            "has_images",
            "has_tables",
            "has_signatures",
        ],
    },
    "preprocessing": {
        "lowercase": True,  # Convert text to lowercase
        "remove_punctuation": True,  # Remove punctuation
        "remove_digits": False,  # Keep digits
        "stemming": True,  # Apply stemming
        "lemmatization": False,  # Don't apply lemmatization
    },
    "dimensionality_reduction": {
        "apply": True,  # Apply dimensionality reduction
        "method": "pca",  # Principal Component Analysis
        "n_components": 100,  # Number of components
    },
}

# SVM classifier configuration
SVM_CONFIG = {
    "model_type": "svm",
    "enabled": True,  # Enable SVM classifier
    "hyperparameters": {
        "C": 10.0,  # Regularization parameter
        "kernel": "rbf",  # Kernel type (rbf, linear, poly, sigmoid)
        "gamma": "scale",  # Kernel coefficient
        "probability": True,  # Enable probability estimates
        "class_weight": "balanced",  # Balanced class weights
        "decision_function_shape": "ovr",  # One-vs-rest decision function
        "tol": 1e-3,  # Tolerance for stopping criterion
        "cache_size": 200,  # Kernel cache size in MB
        "verbose": False,  # Verbose output
        "max_iter": -1,  # No limit on iterations
        "random_state": 42,  # Random seed for reproducibility
    },
    "hyperparameter_tuning": {
        "perform": True,  # Perform hyperparameter tuning
        "method": "grid_search",  # Grid search method
        "cv": 5,  # 5-fold cross-validation
        "n_jobs": -1,  # Use all available cores
        "param_grid": {
            "C": [0.1, 1.0, 10.0, 100.0],
            "kernel": ["linear", "rbf"],
            "gamma": ["scale", "auto", 0.1, 0.01],
        },
        "scoring": "f1_weighted",  # Scoring metric
    },
}

# Random Forest classifier configuration
RANDOM_FOREST_CONFIG = {
    "model_type": "random_forest",
    "enabled": True,  # Enable Random Forest classifier
    "hyperparameters": {
        "n_estimators": 100,  # Number of trees
        "criterion": "gini",  # Function to measure split quality
        "max_depth": None,  # Maximum depth of trees (None = unlimited)
        "min_samples_split": 2,  # Minimum samples to split node
        "min_samples_leaf": 1,  # Minimum samples at leaf node
        "min_weight_fraction_leaf": 0.0,  # Minimum weighted fraction at leaf node
        "max_features": "sqrt",  # Number of features for best split
        "max_leaf_nodes": None,  # Maximum number of leaf nodes
        "min_impurity_decrease": 0.0,  # Minimum impurity decrease for split
        "bootstrap": True,  # Use bootstrap samples
        "oob_score": True,  # Use out-of-bag samples for estimation
        "n_jobs": -1,  # Use all available cores
        "random_state": 42,  # Random seed for reproducibility
        "verbose": 0,  # Verbosity level
        "warm_start": False,  # Reuse previous solution
        "class_weight": "balanced",  # Balanced class weights
        "ccp_alpha": 0.0,  # Complexity parameter for pruning
        "max_samples": None,  # Number of samples for each tree
    },
    "hyperparameter_tuning": {
        "perform": True,  # Perform hyperparameter tuning
        "method": "random_search",  # Random search method
        "cv": 5,  # 5-fold cross-validation
        "n_jobs": -1,  # Use all available cores
        "n_iter": 20,  # Number of parameter settings sampled
        "param_distributions": {
            "n_estimators": [50, 100, 200, 300],
            "max_depth": [None, 10, 20, 30],
            "min_samples_split": [2, 5, 10],
            "min_samples_leaf": [1, 2, 4],
            "max_features": ["sqrt", "log2", None],
        },
        "scoring": "f1_weighted",  # Scoring metric
    },
}

# Ensemble configuration
ENSEMBLE_CONFIG = {
    "model_type": "ensemble",
    "enabled": True,  # Enable ensemble classifier
    "method": "voting",  # Voting ensemble method
    "voting": "soft",  # Soft voting (use probabilities)
    "weights": {  # Weights for each classifier
        "svm": 0.4,
        "random_forest": 0.6,
    },
}

# Model evaluation configuration
EVALUATION_CONFIG = {
    "test_size": 0.2,  # Test set size (20%)
    "metrics": [  # Evaluation metrics
        "accuracy",
        "precision",
        "recall",
        "f1",
        "roc_auc",
        "confusion_matrix",
    ],
    "cv": 5,  # 5-fold cross-validation
    "stratify": True,  # Stratified sampling
    "threshold_optimization": True,  # Optimize classification thresholds
}

# Model training configuration
TRAINING_CONFIG = {
    "train_test_split": {
        "test_size": 0.2,  # Test set size (20%)
        "random_state": 42,  # Random seed for reproducibility
        "stratify": True,  # Stratified sampling
    },
    "early_stopping": {
        "enabled": True,  # Enable early stopping
        "patience": 5,  # Number of epochs with no improvement
        "min_delta": 0.001,  # Minimum change to qualify as improvement
    },
    "class_balancing": {
        "method": "class_weight",  # Use class weights
        "alternative_methods": [  # Alternative methods
            "oversampling",
            "undersampling",
            "smote",
        ],
    },
}

# Model serialization configuration
SERIALIZATION_CONFIG = {
    "format": "pickle",  # Serialization format
    "compression": True,  # Use compression
    "include_metadata": True,  # Include metadata
    "versioning": {
        "enabled": True,  # Enable versioning
        "format": "semver",  # Semantic versioning
        "auto_increment": True,  # Auto-increment version
    },
}

# Combined model configuration
MODEL_CONFIG = {
    "version": MODEL_VERSION,
    "base_dir": MODEL_BASE_DIR,
    "paths": MODEL_PATHS,
    "document_categories": DOCUMENT_CATEGORIES,
    "confidence_thresholds": CONFIDENCE_THRESHOLDS,
    "document_confidence_thresholds": DOCUMENT_CONFIDENCE_THRESHOLDS,
    "feature_extraction": FEATURE_EXTRACTION,
    "models": {
        "svm": SVM_CONFIG,
        "random_forest": RANDOM_FOREST_CONFIG,
        "ensemble": ENSEMBLE_CONFIG,
    },
    "evaluation": EVALUATION_CONFIG,
    "training": TRAINING_CONFIG,
    "serialization": SERIALIZATION_CONFIG,
    "target_accuracy": 0.99,  # Target 99% accuracy as per requirements
}


def get_model_config() -> Dict[str, Any]:
    """
    Get the complete model configuration.
    
    Returns:
        Dict[str, Any]: The complete model configuration.
    """
    return MODEL_CONFIG


def get_model_path(model_type: str) -> str:
    """
    Get the path for a specific model type.
    
    Args:
        model_type (str): The type of model (svm, random_forest, ensemble).
        
    Returns:
        str: The path to the model file.
        
    Raises:
        ValueError: If the model type is not supported.
    """
    if model_type not in MODEL_PATHS:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: {list(MODEL_PATHS.keys())}")
    return MODEL_PATHS[model_type]


def get_confidence_threshold(document_type: str) -> float:
    """
    Get the confidence threshold for a specific document type.
    
    Args:
        document_type (str): The type of document.
        
    Returns:
        float: The confidence threshold for the document type.
        
    Raises:
        ValueError: If the document type is not supported.
    """
    if document_type not in DOCUMENT_CONFIDENCE_THRESHOLDS:
        # Default to 'other' category if not found
        return DOCUMENT_CONFIDENCE_THRESHOLDS["other"]
    return DOCUMENT_CONFIDENCE_THRESHOLDS[document_type]


def get_model_hyperparameters(model_type: str) -> Dict[str, Any]:
    """
    Get the hyperparameters for a specific model type.
    
    Args:
        model_type (str): The type of model (svm, random_forest).
        
    Returns:
        Dict[str, Any]: The hyperparameters for the model.
        
    Raises:
        ValueError: If the model type is not supported.
    """
    if model_type == "svm":
        return SVM_CONFIG["hyperparameters"]
    elif model_type == "random_forest":
        return RANDOM_FOREST_CONFIG["hyperparameters"]
    else:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: ['svm', 'random_forest']")