#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service's model_config.py module.

These tests verify that model configuration correctly sets up classifier parameters,
feature extraction settings, classification thresholds, and model paths. They ensure
that machine learning models are properly configured for document classification with
the required 99% accuracy threshold specified in the technical requirements.

Test coverage includes:
- Classifier configuration (SVM, Random Forest)
- Classification threshold configuration
- Feature extraction parameter configuration
- Model path and versioning configuration
- Model evaluation metric configuration
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Import the module to test
from src.config.model_config import (
    create_model_config,
    get_model_config,
    model_config,
    MODEL_VERSION,
    SUPPORTED_DOCUMENT_TYPES,
    CONFIDENCE_THRESHOLDS,
    MODEL_PATHS,
    FEATURE_EXTRACTION,
    SVM_PARAMS,
    RANDOM_FOREST_PARAMS,
    TRAINING_PARAMS,
    EVALUATION_PARAMS,
    VALIDATION_PARAMS,
    DOCUMENT_PROCESSING,
    HARDWARE_CONSTRAINTS
)

# Import configuration types
from src.types.config import ModelConfig
from src.config.app_config import Environment


# ===== Test Model Configuration Creation =====

def test_create_model_config_random_forest(patch_app_config, mock_app_config):
    """Test creating model configuration with Random Forest classifier."""
    # Configure mock app_config to use random_forest
    mock_app_config.model.model_type = "random_forest"
    
    # Create model configuration
    config = create_model_config()
    
    # Verify model path
    assert config["model_path"] == MODEL_PATHS["random_forest"]
    
    # Verify Random Forest parameters are included
    for key, value in RANDOM_FOREST_PARAMS.items():
        assert config[key] == value
    
    # Verify SVM parameters are not included
    for key in SVM_PARAMS.keys():
        if key not in RANDOM_FOREST_PARAMS:
            assert key not in config
    
    # Verify common configuration
    assert config["vectorizer_path"] == MODEL_PATHS["vectorizer"]
    assert config["min_confidence_threshold"] == mock_app_config.model.confidence_threshold
    assert config["supported_document_types"] == SUPPORTED_DOCUMENT_TYPES
    assert config["batch_size"] == DOCUMENT_PROCESSING["batch_size"]
    assert config["max_document_size_mb"] == DOCUMENT_PROCESSING["max_document_size_mb"]
    assert config["gpu_acceleration"] == HARDWARE_CONSTRAINTS["gpu_acceleration"]
    assert config["memory_limit_mb"] == HARDWARE_CONSTRAINTS["memory_limit_mb"]
    
    # Verify feature extraction parameters
    assert config["feature_extraction"] == FEATURE_EXTRACTION
    
    # Verify training parameters
    assert config["training"] == TRAINING_PARAMS
    
    # Verify evaluation parameters
    assert config["evaluation"] == EVALUATION_PARAMS
    
    # Verify validation parameters
    assert config["validation"] == VALIDATION_PARAMS
    
    # Verify document processing parameters
    assert config["document_processing"] == DOCUMENT_PROCESSING
    
    # Verify hardware constraints
    assert config["hardware_constraints"] == HARDWARE_CONSTRAINTS


def test_create_model_config_svm(patch_app_config, mock_app_config):
    """Test creating model configuration with SVM classifier."""
    # Configure mock app_config to use svm
    mock_app_config.model.model_type = "svm"
    
    # Create model configuration
    config = create_model_config()
    
    # Verify model path
    assert config["model_path"] == MODEL_PATHS["svm"]
    
    # Verify SVM parameters are included
    for key, value in SVM_PARAMS.items():
        assert config[key] == value
    
    # Verify Random Forest parameters are not included
    for key in RANDOM_FOREST_PARAMS.keys():
        if key not in SVM_PARAMS:
            assert key not in config
    
    # Verify common configuration
    assert config["vectorizer_path"] == MODEL_PATHS["vectorizer"]
    assert config["min_confidence_threshold"] == mock_app_config.model.confidence_threshold
    assert config["supported_document_types"] == SUPPORTED_DOCUMENT_TYPES


def test_create_model_config_unknown_model_type(patch_app_config, mock_app_config):
    """Test creating model configuration with unknown model type."""
    # Configure mock app_config to use unknown model type
    mock_app_config.model.model_type = "unknown_model"
    
    # Create model configuration
    with patch("src.config.model_config.logger") as mock_logger:
        config = create_model_config()
        
        # Verify warning is logged
        mock_logger.warning.assert_called_once()
    
    # Verify model path defaults to random_forest
    assert config["model_path"] == MODEL_PATHS["random_forest"]
    
    # Verify Random Forest parameters are used as fallback
    for key, value in RANDOM_FOREST_PARAMS.items():
        assert config[key] == value


# ===== Test Model Configuration Singleton =====

def test_get_model_config():
    """Test that get_model_config returns the singleton instance."""
    # Mock the model_config global variable
    mock_config = MagicMock(spec=ModelConfig)
    
    with patch("src.config.model_config.model_config", mock_config):
        config = get_model_config()
        assert config is mock_config


# ===== Test Classifier Configuration =====

def test_svm_params():
    """Test SVM classifier parameters."""
    # Verify required SVM parameters
    assert "kernel" in SVM_PARAMS
    assert "C" in SVM_PARAMS
    assert "probability" in SVM_PARAMS
    assert "class_weight" in SVM_PARAMS
    assert "random_state" in SVM_PARAMS
    
    # Verify parameter values
    assert SVM_PARAMS["probability"] is True  # Required for confidence scores
    assert SVM_PARAMS["class_weight"] == "balanced"  # Required for imbalanced classes
    assert SVM_PARAMS["random_state"] == 42  # Required for reproducibility


def test_random_forest_params():
    """Test Random Forest classifier parameters."""
    # Verify required Random Forest parameters
    assert "n_estimators" in RANDOM_FOREST_PARAMS
    assert "criterion" in RANDOM_FOREST_PARAMS
    assert "class_weight" in RANDOM_FOREST_PARAMS
    assert "random_state" in RANDOM_FOREST_PARAMS
    assert "oob_score" in RANDOM_FOREST_PARAMS
    
    # Verify parameter values
    assert RANDOM_FOREST_PARAMS["n_estimators"] >= 100  # Sufficient number of trees
    assert RANDOM_FOREST_PARAMS["class_weight"] == "balanced"  # Required for imbalanced classes
    assert RANDOM_FOREST_PARAMS["random_state"] == 42  # Required for reproducibility
    assert RANDOM_FOREST_PARAMS["oob_score"] is True  # Required for model evaluation


# ===== Test Classification Threshold Configuration =====

def test_confidence_thresholds():
    """Test confidence thresholds for different environments."""
    # Verify thresholds for each environment
    assert Environment.DEVELOPMENT in CONFIDENCE_THRESHOLDS
    assert Environment.STAGING in CONFIDENCE_THRESHOLDS
    assert Environment.PRODUCTION in CONFIDENCE_THRESHOLDS
    
    # Verify threshold values
    assert CONFIDENCE_THRESHOLDS[Environment.DEVELOPMENT] < CONFIDENCE_THRESHOLDS[Environment.STAGING]
    assert CONFIDENCE_THRESHOLDS[Environment.STAGING] < CONFIDENCE_THRESHOLDS[Environment.PRODUCTION]
    assert CONFIDENCE_THRESHOLDS[Environment.PRODUCTION] >= 0.85  # High threshold for production


def test_confidence_threshold_by_environment(patch_app_config, mock_app_config):
    """Test that the correct confidence threshold is used based on the environment."""
    # Test development environment
    mock_app_config.service.environment = Environment.DEVELOPMENT
    config = create_model_config()
    assert config["min_confidence_threshold"] == CONFIDENCE_THRESHOLDS[Environment.DEVELOPMENT]
    
    # Test staging environment
    mock_app_config.service.environment = Environment.STAGING
    config = create_model_config()
    assert config["min_confidence_threshold"] == CONFIDENCE_THRESHOLDS[Environment.STAGING]
    
    # Test production environment
    mock_app_config.service.environment = Environment.PRODUCTION
    config = create_model_config()
    assert config["min_confidence_threshold"] == CONFIDENCE_THRESHOLDS[Environment.PRODUCTION]


# ===== Test Feature Extraction Configuration =====

def test_feature_extraction_params():
    """Test feature extraction parameters."""
    # Verify required feature extraction parameters
    assert "max_features" in FEATURE_EXTRACTION
    assert "ngram_range" in FEATURE_EXTRACTION
    assert "min_df" in FEATURE_EXTRACTION
    assert "max_df" in FEATURE_EXTRACTION
    assert "use_idf" in FEATURE_EXTRACTION
    assert "stop_words" in FEATURE_EXTRACTION
    
    # Verify parameter values
    assert FEATURE_EXTRACTION["max_features"] >= 5000  # Sufficient vocabulary size
    assert FEATURE_EXTRACTION["ngram_range"] == (1, 2)  # Unigrams and bigrams
    assert FEATURE_EXTRACTION["use_idf"] is True  # Use inverse document frequency
    assert FEATURE_EXTRACTION["stop_words"] == "english"  # Remove English stop words


def test_feature_extraction_in_model_config():
    """Test that feature extraction parameters are included in model configuration."""
    config = create_model_config()
    assert "feature_extraction" in config
    assert config["feature_extraction"] == FEATURE_EXTRACTION


# ===== Test Model Path and Versioning Configuration =====

def test_model_version():
    """Test model version."""
    # Verify model version format (semver)
    assert MODEL_VERSION.count(".") >= 2  # At least major.minor.patch
    
    # Verify model version is included in model paths
    for path in MODEL_PATHS.values():
        assert MODEL_VERSION in path


def test_model_paths():
    """Test model file paths."""
    # Verify required model paths
    assert "svm" in MODEL_PATHS
    assert "random_forest" in MODEL_PATHS
    assert "vectorizer" in MODEL_PATHS
    
    # Verify path format
    for path in MODEL_PATHS.values():
        assert path.endswith(".pkl")  # Pickle file extension
        assert MODEL_VERSION in path  # Version included in filename


# ===== Test Document Types Configuration =====

def test_supported_document_types():
    """Test supported document types."""
    # Verify required document types
    required_types = [
        "APPLICATION",
        "TAX_RETURN",
        "BANK_STATEMENT",
        "PROFIT_LOSS",
        "BALANCE_SHEET",
        "BUSINESS_LICENSE",
        "IDENTITY_DOCUMENT"
    ]
    
    for doc_type in required_types:
        assert doc_type in SUPPORTED_DOCUMENT_TYPES
    
    # Verify "OTHER" type is included for unclassified documents
    assert "OTHER" in SUPPORTED_DOCUMENT_TYPES


# ===== Test Model Evaluation Configuration =====

def test_evaluation_params():
    """Test model evaluation parameters."""
    # Verify required evaluation parameters
    assert "accuracy_threshold" in EVALUATION_PARAMS
    assert "metrics" in EVALUATION_PARAMS
    
    # Verify accuracy threshold meets technical requirements (99%)
    assert EVALUATION_PARAMS["accuracy_threshold"] >= 0.99
    
    # Verify required metrics
    required_metrics = ["accuracy", "precision", "recall", "f1"]
    for metric in required_metrics:
        assert metric in EVALUATION_PARAMS["metrics"]


def test_training_params():
    """Test model training parameters."""
    # Verify required training parameters
    assert "test_size" in TRAINING_PARAMS
    assert "cv_folds" in TRAINING_PARAMS
    assert "hyperparameter_tuning" in TRAINING_PARAMS
    
    # Verify parameter values
    assert 0 < TRAINING_PARAMS["test_size"] < 1  # Valid test size
    assert TRAINING_PARAMS["cv_folds"] >= 3  # Sufficient cross-validation


# ===== Test Hardware Constraints Configuration =====

def test_hardware_constraints():
    """Test hardware resource constraints."""
    # Verify required hardware constraints
    assert "memory_limit_mb" in HARDWARE_CONSTRAINTS
    assert "gpu_acceleration" in HARDWARE_CONSTRAINTS
    assert "cpu_count" in HARDWARE_CONSTRAINTS
    
    # Verify memory limit meets technical requirements (16GB minimum)
    assert HARDWARE_CONSTRAINTS["memory_limit_mb"] >= 16384  # 16GB in MB


# ===== Test Document Processing Configuration =====

def test_document_processing_params():
    """Test document processing parameters."""
    # Verify required document processing parameters
    assert "max_document_size_mb" in DOCUMENT_PROCESSING
    assert "supported_formats" in DOCUMENT_PROCESSING
    assert "extract_text" in DOCUMENT_PROCESSING
    assert "ocr_engine" in DOCUMENT_PROCESSING
    
    # Verify supported document formats
    required_formats = ["pdf", "png", "jpg", "jpeg"]
    for format in required_formats:
        assert format in DOCUMENT_PROCESSING["supported_formats"]
    
    # Verify OCR configuration
    assert DOCUMENT_PROCESSING["extract_text"] is True
    assert DOCUMENT_PROCESSING["ocr_engine"] in ["tesseract", "textract"]


# ===== Test Environment-Specific Configuration =====

@pytest.mark.parametrize(
    "environment,expected_threshold",
    [
        (Environment.DEVELOPMENT, 0.65),
        (Environment.STAGING, 0.75),
        (Environment.PRODUCTION, 0.85),
    ],
)
def test_environment_specific_confidence_threshold(environment, expected_threshold):
    """Test environment-specific confidence thresholds."""
    assert CONFIDENCE_THRESHOLDS[environment] == expected_threshold


# ===== Test Validation Parameters =====

def test_validation_params():
    """Test model validation parameters."""
    # Verify required validation parameters
    assert "validation_size" in VALIDATION_PARAMS
    assert "min_samples_per_class" in VALIDATION_PARAMS
    assert "validation_frequency" in VALIDATION_PARAMS
    assert "alert_on_performance_drop" in VALIDATION_PARAMS
    assert "performance_drop_threshold" in VALIDATION_PARAMS
    assert "retraining_threshold" in VALIDATION_PARAMS
    
    # Verify parameter values
    assert 0 < VALIDATION_PARAMS["validation_size"] < 1  # Valid validation size
    assert VALIDATION_PARAMS["min_samples_per_class"] > 0  # Positive minimum samples
    assert VALIDATION_PARAMS["alert_on_performance_drop"] is True  # Alert on performance drop
    assert 0 < VALIDATION_PARAMS["performance_drop_threshold"] < 1  # Valid threshold
    assert VALIDATION_PARAMS["performance_drop_threshold"] < VALIDATION_PARAMS["retraining_threshold"]  # Retraining threshold higher than alert threshold