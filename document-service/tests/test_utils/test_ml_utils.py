#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the machine learning utilities in the Document Service.

These tests verify that the model loading, feature extraction, prediction,
and confidence scoring functions work correctly. They ensure that document
classification models (SVM, Random Forest) perform as expected.
"""

import os
import json
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path
from typing import Dict, List, Any, Tuple
from sklearn.base import BaseEstimator
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.preprocessing import StandardScaler
from joblib import dump, load

# Import the module to test
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from src.utils import ml_utils
from src.config import model_config


# ============================================================================
# Test Model Loading and Saving
# ============================================================================

@patch('src.utils.ml_utils.load')
def test_load_model_success(mock_load, mock_ml_pipeline):
    """Test successful model loading."""
    # Setup
    model_path = "models/test_model.pkl"
    model_metadata = {
        "model_version": "1.0.0",
        "timestamp": "2023-01-01T00:00:00Z",
        "metrics": {"accuracy": 0.95}
    }
    mock_load.return_value = {
        "model": mock_ml_pipeline,
        "metadata": model_metadata
    }
    
    # Execute
    model, metadata = ml_utils.load_model(model_path)
    
    # Assert
    mock_load.assert_called_once_with(model_path)
    assert model == mock_ml_pipeline
    assert metadata == model_metadata
    assert metadata["model_version"] == "1.0.0"


@patch('src.utils.ml_utils.load')
@patch('os.path.exists')
def test_load_model_file_not_found(mock_exists, mock_load):
    """Test model loading when file doesn't exist."""
    # Setup
    model_path = "models/nonexistent_model.pkl"
    mock_exists.return_value = False
    
    # Execute and Assert
    with pytest.raises(FileNotFoundError):
        ml_utils.load_model(model_path)
    
    mock_exists.assert_called_once_with(model_path)
    mock_load.assert_not_called()


@patch('src.utils.ml_utils.load')
@patch('os.path.exists')
def test_load_model_invalid_format(mock_exists, mock_load):
    """Test model loading with invalid format."""
    # Setup
    model_path = "models/invalid_model.pkl"
    mock_exists.return_value = True
    mock_load.return_value = {"invalid": "format"}
    
    # Execute and Assert
    with pytest.raises(ValueError):
        ml_utils.load_model(model_path)
    
    mock_exists.assert_called_once_with(model_path)
    mock_load.assert_called_once_with(model_path)


@patch('src.utils.ml_utils.dump')
@patch('os.makedirs')
@patch('src.utils.time_utils.get_iso_timestamp')
def test_save_model_success(mock_timestamp, mock_makedirs, mock_dump, mock_ml_pipeline):
    """Test successful model saving."""
    # Setup
    model_path = "models/test_model.pkl"
    model_metadata = {
        "model_version": "1.0.0",
        "metrics": {"accuracy": 0.95}
    }
    mock_timestamp.return_value = "2023-01-01T00:00:00Z"
    
    # Execute
    result = ml_utils.save_model(mock_ml_pipeline, model_metadata, model_path)
    
    # Assert
    mock_makedirs.assert_called_once_with(os.path.dirname(model_path), exist_ok=True)
    mock_dump.assert_called_once()
    assert result == model_path
    assert "timestamp" in model_metadata
    assert model_metadata["timestamp"] == "2023-01-01T00:00:00Z"


@patch('src.utils.ml_utils.dump')
@patch('os.makedirs')
def test_save_model_error(mock_makedirs, mock_dump, mock_ml_pipeline):
    """Test model saving with error."""
    # Setup
    model_path = "models/test_model.pkl"
    model_metadata = {"model_version": "1.0.0"}
    mock_dump.side_effect = IOError("Failed to save model")
    
    # Execute and Assert
    with pytest.raises(Exception):
        ml_utils.save_model(mock_ml_pipeline, model_metadata, model_path)
    
    mock_makedirs.assert_called_once_with(os.path.dirname(model_path), exist_ok=True)
    mock_dump.assert_called_once()


# ============================================================================
# Test Feature Extraction
# ============================================================================

def test_create_feature_extractor_default_config():
    """Test creating a feature extractor with default configuration."""
    # Execute
    extractor = ml_utils.create_feature_extractor()
    
    # Assert
    assert isinstance(extractor, Pipeline)
    assert len(extractor.steps) > 0
    assert extractor.steps[0][0] == 'tfidf'
    assert isinstance(extractor.steps[0][1], TfidfVectorizer)


def test_create_feature_extractor_custom_config():
    """Test creating a feature extractor with custom configuration."""
    # Setup
    config = {
        "tfidf": {
            "max_features": 5000,
            "min_df": 2,
            "max_df": 0.9,
            "ngram_range": (1, 3),
            "stop_words": None
        },
        "use_svd": True,
        "svd": {
            "n_components": 50,
            "random_state": 123
        },
        "use_scaling": True
    }
    
    # Execute
    extractor = ml_utils.create_feature_extractor(config)
    
    # Assert
    assert isinstance(extractor, Pipeline)
    assert len(extractor.steps) == 3  # tfidf, svd, scaler
    
    # Check TF-IDF configuration
    tfidf = extractor.steps[0][1]
    assert tfidf.max_features == 5000
    assert tfidf.min_df == 2
    assert tfidf.max_df == 0.9
    assert tfidf.ngram_range == (1, 3)
    assert tfidf.stop_words is None
    
    # Check SVD configuration
    svd = extractor.steps[1][1]
    assert isinstance(svd, TruncatedSVD)
    assert svd.n_components == 50
    assert svd.random_state == 123
    
    # Check scaler
    assert isinstance(extractor.steps[2][1], StandardScaler)


def test_create_feature_extractor_no_svd_no_scaling():
    """Test creating a feature extractor without SVD and scaling."""
    # Setup
    config = {
        "tfidf": {
            "max_features": 1000,
            "min_df": 1,
            "max_df": 0.95,
            "ngram_range": (1, 1),
            "stop_words": "english"
        },
        "use_svd": False,
        "use_scaling": False
    }
    
    # Execute
    extractor = ml_utils.create_feature_extractor(config)
    
    # Assert
    assert isinstance(extractor, Pipeline)
    assert len(extractor.steps) == 1  # Only tfidf
    assert extractor.steps[0][0] == 'tfidf'
    assert isinstance(extractor.steps[0][1], TfidfVectorizer)


def test_extract_features_with_new_extractor():
    """Test feature extraction with a new extractor."""
    # Setup
    documents = [
        "This is a sample document for testing feature extraction.",
        "Another document with different content for testing.",
        "A third document to ensure we have enough samples."
    ]
    
    # Execute
    features = ml_utils.extract_features(documents)
    
    # Assert
    assert isinstance(features, np.ndarray)
    assert features.shape[0] == len(documents)  # Number of samples


def test_extract_features_with_existing_extractor():
    """Test feature extraction with an existing extractor."""
    # Setup
    documents = [
        "This is a sample document for testing feature extraction.",
        "Another document with different content for testing.",
        "A third document to ensure we have enough samples."
    ]
    extractor = ml_utils.create_feature_extractor()
    
    # Train the extractor on some initial documents
    extractor.fit(["Initial document for fitting the extractor."])
    
    # Execute
    features = ml_utils.extract_features(documents, extractor)
    
    # Assert
    assert isinstance(features, np.ndarray)
    assert features.shape[0] == len(documents)  # Number of samples


def test_extract_features_empty_documents():
    """Test feature extraction with empty document list."""
    # Setup
    documents = []
    
    # Execute and Assert
    with pytest.raises(ValueError):
        ml_utils.extract_features(documents)


def test_extract_features_invalid_documents():
    """Test feature extraction with invalid document types."""
    # Setup
    documents = ["Valid document", 123, "Another valid document"]
    
    # Execute and Assert
    with pytest.raises(ValueError):
        ml_utils.extract_features(documents)


# ============================================================================
# Test Prediction and Confidence Scoring
# ============================================================================

def test_get_prediction_confidence_max_prob():
    """Test confidence calculation using max probability method."""
    # Setup
    probabilities = np.array([
        [0.1, 0.2, 0.7],
        [0.3, 0.6, 0.1],
        [0.25, 0.25, 0.5]
    ])
    
    # Execute
    confidence = ml_utils.get_prediction_confidence(probabilities, method='max_prob')
    
    # Assert
    assert isinstance(confidence, np.ndarray)
    assert confidence.shape == (3,)
    assert np.allclose(confidence, np.array([0.7, 0.6, 0.5]))


def test_get_prediction_confidence_margin():
    """Test confidence calculation using margin method."""
    # Setup
    probabilities = np.array([
        [0.1, 0.2, 0.7],  # Margin: 0.7 - 0.2 = 0.5
        [0.3, 0.6, 0.1],  # Margin: 0.6 - 0.3 = 0.3
        [0.25, 0.25, 0.5]  # Margin: 0.5 - 0.25 = 0.25
    ])
    
    # Execute
    confidence = ml_utils.get_prediction_confidence(probabilities, method='margin')
    
    # Assert
    assert isinstance(confidence, np.ndarray)
    assert confidence.shape == (3,)
    assert np.allclose(confidence, np.array([0.5, 0.3, 0.25]))


def test_get_prediction_confidence_entropy():
    """Test confidence calculation using entropy method."""
    # Setup
    probabilities = np.array([
        [0.1, 0.2, 0.7],  # Less uniform, higher confidence
        [0.33, 0.33, 0.34],  # More uniform, lower confidence
        [0.25, 0.25, 0.5]  # Somewhat uniform, medium confidence
    ])
    
    # Execute
    confidence = ml_utils.get_prediction_confidence(probabilities, method='entropy')
    
    # Assert
    assert isinstance(confidence, np.ndarray)
    assert confidence.shape == (3,)
    # First should have highest confidence, second lowest
    assert confidence[0] > confidence[2] > confidence[1]


def test_get_prediction_confidence_invalid_method():
    """Test confidence calculation with invalid method."""
    # Setup
    probabilities = np.array([[0.1, 0.2, 0.7]])
    
    # Execute and Assert
    with pytest.raises(ValueError):
        ml_utils.get_prediction_confidence(probabilities, method='invalid_method')


def test_predict_with_confidence(mock_ml_pipeline):
    """Test prediction with confidence calculation."""
    # Setup
    features = np.array([[1, 2, 3], [4, 5, 6]])
    mock_ml_pipeline.predict.return_value = np.array(['application_form', 'tax_return'])
    mock_ml_pipeline.predict_proba.return_value = np.array([
        [0.1, 0.2, 0.7],
        [0.3, 0.6, 0.1]
    ])
    
    # Execute
    predictions, probabilities, confidence = ml_utils.predict_with_confidence(
        mock_ml_pipeline, features, confidence_method='max_prob', confidence_threshold=0.6
    )
    
    # Assert
    assert isinstance(predictions, np.ndarray)
    assert isinstance(probabilities, np.ndarray)
    assert isinstance(confidence, np.ndarray)
    assert predictions.shape == (2,)
    assert probabilities.shape == (2, 3)
    assert confidence.shape == (2,)
    assert np.allclose(confidence, np.array([0.7, 0.6]))
    mock_ml_pipeline.predict.assert_called_once_with(features)
    mock_ml_pipeline.predict_proba.assert_called_once_with(features)


def test_predict_with_confidence_no_proba():
    """Test prediction with a model that doesn't support probability estimation."""
    # Setup
    features = np.array([[1, 2, 3]])
    model = MagicMock(spec=BaseEstimator)
    model.predict.return_value = np.array(['application_form'])
    # No predict_proba method
    
    # Execute and Assert
    with pytest.raises(ValueError):
        ml_utils.predict_with_confidence(model, features)


# ============================================================================
# Test Model Evaluation and Performance Tracking
# ============================================================================

def test_evaluate_model_performance(mock_ml_pipeline):
    """Test model performance evaluation."""
    # Setup
    X_test = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    y_test = np.array(['application_form', 'tax_return', 'application_form'])
    mock_ml_pipeline.predict.return_value = np.array(['application_form', 'tax_return', 'application_form'])
    class_names = ['application_form', 'tax_return', 'bank_statement']
    
    # Execute
    metrics = ml_utils.evaluate_model_performance(mock_ml_pipeline, X_test, y_test, class_names)
    
    # Assert
    assert isinstance(metrics, dict)
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'f1' in metrics
    assert 'confusion_matrix' in metrics
    assert 'support' in metrics
    assert 'timestamp' in metrics
    assert 'class_metrics' in metrics
    assert metrics['accuracy'] == 1.0  # Perfect predictions in this mock
    assert len(metrics['class_metrics']) == len(class_names)


def test_evaluate_model_performance_without_class_names(mock_ml_pipeline):
    """Test model performance evaluation without class names."""
    # Setup
    X_test = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
    y_test = np.array(['application_form', 'tax_return', 'application_form'])
    mock_ml_pipeline.predict.return_value = np.array(['application_form', 'tax_return', 'application_form'])
    
    # Execute
    metrics = ml_utils.evaluate_model_performance(mock_ml_pipeline, X_test, y_test)
    
    # Assert
    assert isinstance(metrics, dict)
    assert 'accuracy' in metrics
    assert 'precision' in metrics
    assert 'recall' in metrics
    assert 'f1' in metrics
    assert 'confusion_matrix' in metrics
    assert 'support' in metrics
    assert 'timestamp' in metrics
    assert 'class_metrics' not in metrics
    assert metrics['accuracy'] == 1.0  # Perfect predictions in this mock


@patch('src.utils.ml_utils.logger')
def test_track_model_performance(mock_logger):
    """Test model performance tracking."""
    # Setup
    model_name = "test_model"
    metrics = {
        'accuracy': 0.95,
        'precision': 0.94,
        'recall': 0.93,
        'f1': 0.935,
        'confusion_matrix': [[10, 1], [2, 20]],
        'support': 33,
        'timestamp': '2023-01-01T00:00:00Z'
    }
    
    # Execute
    ml_utils.track_model_performance(model_name, metrics)
    
    # Assert
    mock_logger.info.assert_called_once()
    # Check that the log message contains the metrics
    log_message = mock_logger.info.call_args[0][0]
    assert model_name in log_message
    assert str(metrics['accuracy']) in log_message
    assert str(metrics['precision']) in log_message
    assert str(metrics['recall']) in log_message
    assert str(metrics['f1']) in log_message


# ============================================================================
# Test Model Validation
# ============================================================================

def test_validate_model_valid(mock_ml_pipeline):
    """Test model validation with a valid model."""
    # Setup
    expected_classes = ['bank_statement', 'tax_return', 'identity_document', 
                        'business_license', 'utility_bill', 'application_form']
    mock_ml_pipeline.classes_ = np.array(expected_classes)
    
    # Execute
    result = ml_utils.validate_model(mock_ml_pipeline, expected_classes)
    
    # Assert
    assert result is True


def test_validate_model_missing_method():
    """Test model validation with missing required method."""
    # Setup
    model = MagicMock(spec=BaseEstimator)
    # Missing predict_proba method
    model.fit = MagicMock()
    model.predict = MagicMock()
    expected_classes = ['application_form', 'tax_return']
    
    # Execute
    result = ml_utils.validate_model(model, expected_classes)
    
    # Assert
    assert result is False


def test_validate_model_wrong_classes(mock_ml_pipeline):
    """Test model validation with incorrect classes."""
    # Setup
    expected_classes = ['application_form', 'tax_return', 'bank_statement']
    mock_ml_pipeline.classes_ = np.array(['application_form', 'tax_return'])
    
    # Execute
    result = ml_utils.validate_model(mock_ml_pipeline, expected_classes)
    
    # Assert
    assert result is False


# ============================================================================
# Test Model Version Information
# ============================================================================

@patch('src.utils.ml_utils.load_model')
def test_get_model_version_info(mock_load_model):
    """Test getting model version information."""
    # Setup
    model_path = "models/test_model.pkl"
    mock_model = MagicMock()
    mock_metadata = {
        "model_version": "1.0.0",
        "timestamp": "2023-01-01T00:00:00Z",
        "parameters": {"C": 1.0, "kernel": "rbf"},
        "metrics": {"accuracy": 0.95, "f1": 0.94}
    }
    mock_load_model.return_value = (mock_model, mock_metadata)
    
    # Execute
    version_info = ml_utils.get_model_version_info(model_path)
    
    # Assert
    assert isinstance(version_info, dict)
    assert version_info["version"] == "1.0.0"
    assert version_info["timestamp"] == "2023-01-01T00:00:00Z"
    assert version_info["parameters"] == {"C": 1.0, "kernel": "rbf"}
    assert version_info["accuracy"] == 0.95
    assert version_info["f1"] == 0.94


@patch('src.utils.ml_utils.load_model')
def test_get_model_version_info_file_not_found(mock_load_model):
    """Test getting model version information when file doesn't exist."""
    # Setup
    model_path = "models/nonexistent_model.pkl"
    mock_load_model.side_effect = FileNotFoundError("File not found")
    
    # Execute and Assert
    with pytest.raises(FileNotFoundError):
        ml_utils.get_model_version_info(model_path)


@patch('src.utils.ml_utils.load_model')
@patch('src.utils.ml_utils.logger')
def test_get_model_version_info_error(mock_logger, mock_load_model):
    """Test getting model version information with an error."""
    # Setup
    model_path = "models/error_model.pkl"
    mock_load_model.side_effect = Exception("Test error")
    
    # Execute
    version_info = ml_utils.get_model_version_info(model_path)
    
    # Assert
    assert isinstance(version_info, dict)
    assert version_info["version"] == "unknown"
    assert "error" in version_info
    assert version_info["error"] == "Test error"
    mock_logger.error.assert_called_once()


@patch('src.utils.ml_utils.get_model_version_info')
def test_compare_model_versions(mock_get_version_info):
    """Test comparing multiple model versions."""
    # Setup
    model_paths = ["models/model_v1.pkl", "models/model_v2.pkl"]
    mock_get_version_info.side_effect = [
        {"version": "1.0.0", "timestamp": "2023-01-01T00:00:00Z", "accuracy": 0.90, "f1": 0.89},
        {"version": "2.0.0", "timestamp": "2023-02-01T00:00:00Z", "accuracy": 0.95, "f1": 0.94}
    ]
    
    # Execute
    comparison = ml_utils.compare_model_versions(model_paths)
    
    # Assert
    assert isinstance(comparison, pd.DataFrame)
    assert len(comparison) == 2
    assert "version" in comparison.columns
    assert "timestamp" in comparison.columns
    assert "accuracy" in comparison.columns
    assert "f1" in comparison.columns
    assert "path" in comparison.columns
    assert comparison.iloc[0]["version"] == "1.0.0"
    assert comparison.iloc[1]["version"] == "2.0.0"


@patch('src.utils.ml_utils.get_model_version_info')
@patch('src.utils.ml_utils.logger')
def test_compare_model_versions_with_error(mock_logger, mock_get_version_info):
    """Test comparing model versions with an error for one model."""
    # Setup
    model_paths = ["models/model_v1.pkl", "models/error_model.pkl"]
    mock_get_version_info.side_effect = [
        {"version": "1.0.0", "timestamp": "2023-01-01T00:00:00Z", "accuracy": 0.90, "f1": 0.89},
        Exception("Test error")
    ]
    
    # Execute
    comparison = ml_utils.compare_model_versions(model_paths)
    
    # Assert
    assert isinstance(comparison, pd.DataFrame)
    assert len(comparison) == 1  # Only one successful model
    assert comparison.iloc[0]["version"] == "1.0.0"
    mock_logger.warning.assert_called_once()


@patch('src.utils.ml_utils.get_model_version_info')
def test_compare_model_versions_empty(mock_get_version_info):
    """Test comparing model versions with no valid models."""
    # Setup
    model_paths = []
    
    # Execute
    comparison = ml_utils.compare_model_versions(model_paths)
    
    # Assert
    assert isinstance(comparison, pd.DataFrame)
    assert len(comparison) == 0
    assert "version" in comparison.columns
    assert "timestamp" in comparison.columns
    assert "accuracy" in comparison.columns
    assert "f1" in comparison.columns
    assert "path" in comparison.columns


# ============================================================================
# Test Feature Importance and Model Size
# ============================================================================

def test_get_feature_importance_with_feature_importances():
    """Test getting feature importance from a model with feature_importances_."""
    # Setup
    model = MagicMock(spec=RandomForestClassifier)
    model.feature_importances_ = np.array([0.3, 0.5, 0.2])
    feature_names = ["feature1", "feature2", "feature3"]
    
    # Execute
    importance = ml_utils.get_feature_importance(model, feature_names)
    
    # Assert
    assert isinstance(importance, dict)
    assert len(importance) == 3
    assert importance["feature2"] > importance["feature1"] > importance["feature3"]
    assert importance["feature2"] == 0.5


def test_get_feature_importance_with_coef():
    """Test getting feature importance from a model with coef_."""
    # Setup
    model = MagicMock(spec=SVC)
    # Multi-class coefficients (3 classes, 3 features)
    model.coef_ = np.array([
        [0.1, 0.2, 0.3],
        [-0.2, 0.4, 0.1],
        [0.3, -0.1, 0.2]
    ])
    feature_names = ["feature1", "feature2", "feature3"]
    
    # Execute
    importance = ml_utils.get_feature_importance(model, feature_names)
    
    # Assert
    assert isinstance(importance, dict)
    assert len(importance) == 3
    # Average absolute values: feature1=0.2, feature2=0.23333, feature3=0.2
    assert importance["feature2"] > importance["feature1"]
    assert importance["feature2"] > importance["feature3"]


def test_get_feature_importance_no_importance_attr():
    """Test getting feature importance from a model without importance attributes."""
    # Setup
    model = MagicMock(spec=BaseEstimator)
    # No feature_importances_ or coef_ attributes
    
    # Execute
    importance = ml_utils.get_feature_importance(model)
    
    # Assert
    assert isinstance(importance, dict)
    assert len(importance) == 0


def test_get_feature_importance_mismatched_names():
    """Test getting feature importance with mismatched feature names."""
    # Setup
    model = MagicMock(spec=RandomForestClassifier)
    model.feature_importances_ = np.array([0.3, 0.5, 0.2])
    feature_names = ["feature1", "feature2"]  # Too few names
    
    # Execute
    importance = ml_utils.get_feature_importance(model, feature_names)
    
    # Assert
    assert isinstance(importance, dict)
    assert len(importance) == 3
    assert "feature_0" in importance or "feature0" in importance
    assert "feature_1" in importance or "feature1" in importance
    assert "feature_2" in importance or "feature2" in importance


@patch('tempfile.NamedTemporaryFile')
@patch('os.path.getsize')
@patch('src.utils.ml_utils.dump')
def test_get_model_size(mock_dump, mock_getsize, mock_tempfile, mock_ml_pipeline):
    """Test getting the model size."""
    # Setup
    mock_tempfile.return_value.__enter__.return_value.name = "temp_model.pkl"
    mock_getsize.return_value = 1024 * 1024  # 1 MB
    
    # Execute
    size = ml_utils.get_model_size(mock_ml_pipeline)
    
    # Assert
    assert isinstance(size, str)
    assert "1.00 MB" in size
    mock_dump.assert_called_once()
    mock_getsize.assert_called_once()


@patch('tempfile.NamedTemporaryFile')
@patch('os.path.getsize')
@patch('src.utils.ml_utils.dump')
def test_get_model_size_small(mock_dump, mock_getsize, mock_tempfile, mock_ml_pipeline):
    """Test getting a small model size."""
    # Setup
    mock_tempfile.return_value.__enter__.return_value.name = "temp_model.pkl"
    mock_getsize.return_value = 512  # 512 bytes
    
    # Execute
    size = ml_utils.get_model_size(mock_ml_pipeline)
    
    # Assert
    assert isinstance(size, str)
    assert "512.00 B" in size or "0.50 KB" in size
    mock_dump.assert_called_once()
    mock_getsize.assert_called_once()


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
def test_end_to_end_classification_workflow():
    """Test the end-to-end document classification workflow."""
    # This test would be implemented in an integration test suite
    # It would test the full workflow from loading a model to classifying documents
    # For now, we'll just mark it as a placeholder
    pass


# ============================================================================
# Main Test Runner
# ============================================================================

if __name__ == "__main__":
    pytest.main(['-xvs', __file__])