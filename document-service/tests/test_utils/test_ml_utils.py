#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the machine learning utilities in the Document Service.

This module contains tests for the ML utilities used in document classification,
including model loading, feature extraction, prediction, and confidence scoring.
These tests ensure that the document classification models (SVM, Random Forest)
perform as expected and meet the requirements specified in the technical specification.
"""

import os
import json
import pickle
import pytest
import numpy as np
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

# Import the module to test
from document_service.utils import ml_utils
from document_service.types.documents import Document, DocumentType, DocumentMetadata
from document_service.types.classification import ClassificationResult, ConfidenceScore, ModelMetadata
from document_service.models.feature_extraction import FeatureExtractor


# ===== Model Loading Tests =====

@pytest.mark.parametrize("model_type", ["svm", "random_forest", "ensemble"])
def test_load_model_success(monkeypatch, model_type):
    """
    Test that load_model successfully loads a model from disk.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        model_type: Type of model to load
    """
    # Mock the get_model_path function to return a test path
    monkeypatch.setattr(ml_utils, "get_model_path", lambda x: f"/tmp/test_{x}_model.pkl")
    
    # Mock os.path.exists to return True
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    
    # Create a mock model
    mock_model = MagicMock()
    if model_type == "svm":
        mock_model.__class__ = SVC
    else:
        mock_model.__class__ = RandomForestClassifier
    
    # Mock joblib.load to return the mock model
    monkeypatch.setattr(ml_utils.joblib, "load", lambda x: mock_model)
    
    # Call the function
    model = ml_utils.load_model(model_type)
    
    # Assert that the model was loaded
    assert model is mock_model


def test_load_model_file_not_found(monkeypatch):
    """
    Test that load_model raises FileNotFoundError when the model file doesn't exist.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Mock the get_model_path function to return a test path
    monkeypatch.setattr(ml_utils, "get_model_path", lambda x: "/tmp/nonexistent_model.pkl")
    
    # Mock os.path.exists to return False
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    
    # Call the function and assert that it raises FileNotFoundError
    with pytest.raises(FileNotFoundError):
        ml_utils.load_model("svm")


def test_load_model_joblib_fallback_to_pickle(monkeypatch):
    """
    Test that load_model falls back to pickle if joblib fails.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Mock the get_model_path function to return a test path
    monkeypatch.setattr(ml_utils, "get_model_path", lambda x: "/tmp/test_model.pkl")
    
    # Mock os.path.exists to return True
    monkeypatch.setattr(os.path, "exists", lambda x: True)
    
    # Create a mock model
    mock_model = MagicMock()
    mock_model.__class__ = RandomForestClassifier
    
    # Mock joblib.load to raise an exception
    def mock_joblib_load(path):
        raise Exception("Joblib load failed")
    
    monkeypatch.setattr(ml_utils.joblib, "load", mock_joblib_load)
    
    # Mock pickle.load to return the mock model
    mock_file = MagicMock()
    mock_file.__enter__.return_value = mock_file
    mock_file.read.return_value = b"mock model data"
    
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)
    monkeypatch.setattr(ml_utils.pickle, "load", lambda x: mock_model)
    
    # Call the function
    model = ml_utils.load_model("random_forest")
    
    # Assert that the model was loaded
    assert model is mock_model


def test_load_all_models(monkeypatch):
    """
    Test that load_all_models loads all available models.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Mock the get_model_config function to return a test config
    mock_config = {
        "paths": {
            "svm": "/tmp/svm_model.pkl",
            "random_forest": "/tmp/rf_model.pkl",
            "ensemble": "/tmp/ensemble_model.pkl"
        }
    }
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the load_model function to return mock models
    mock_svm = MagicMock()
    mock_svm.__class__ = SVC
    
    mock_rf = MagicMock()
    mock_rf.__class__ = RandomForestClassifier
    
    mock_ensemble = MagicMock()
    
    def mock_load_model(model_type):
        if model_type == "svm":
            return mock_svm
        elif model_type == "random_forest":
            return mock_rf
        elif model_type == "ensemble":
            return mock_ensemble
        else:
            raise ValueError(f"Unknown model type: {model_type}")
    
    monkeypatch.setattr(ml_utils, "load_model", mock_load_model)
    
    # Call the function
    models = ml_utils.load_all_models()
    
    # Assert that all models were loaded
    assert len(models) == 3
    assert models["svm"] is mock_svm
    assert models["random_forest"] is mock_rf
    assert models["ensemble"] is mock_ensemble


def test_get_model_metadata_with_file(monkeypatch):
    """
    Test that get_model_metadata loads metadata from a file.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Mock the get_model_config function to return a test config
    mock_config = {"version": "1.0.0"}
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_model_path function to return a test path
    monkeypatch.setattr(ml_utils, "get_model_path", lambda x: "/tmp/test_model.pkl")
    
    # Mock os.path.exists to return True for both model and metadata
    def mock_exists(path):
        return True
    
    monkeypatch.setattr(os.path, "exists", mock_exists)
    
    # Mock metadata file content
    metadata_content = {
        "model_type": "random_forest",
        "version": "1.0.0",
        "created_at": "2023-01-01T00:00:00",
        "accuracy": 0.95,
        "f1_score": 0.94,
        "training_parameters": {"n_estimators": 100}
    }
    
    # Mock open and json.load
    mock_file = MagicMock()
    mock_file.__enter__.return_value = mock_file
    monkeypatch.setattr("builtins.open", lambda *args, **kwargs: mock_file)
    monkeypatch.setattr(json, "load", lambda x: metadata_content)
    
    # Call the function
    metadata = ml_utils.get_model_metadata("random_forest")
    
    # Assert that the metadata was loaded correctly
    assert metadata.model_type == "random_forest"
    assert metadata.version == "1.0.0"
    assert isinstance(metadata.created_at, datetime)
    assert metadata.accuracy == 0.95
    assert metadata.f1_score == 0.94
    assert metadata.training_parameters == {"n_estimators": 100}


def test_get_model_metadata_without_file(monkeypatch):
    """
    Test that get_model_metadata returns basic metadata when the file doesn't exist.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Mock the get_model_config function to return a test config
    mock_config = {"version": "1.0.0"}
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_model_path function to return a test path
    monkeypatch.setattr(ml_utils, "get_model_path", lambda x: "/tmp/test_model.pkl")
    
    # Mock os.path.exists to return True for model but False for metadata
    def mock_exists(path):
        return ".json" not in path
    
    monkeypatch.setattr(os.path, "exists", mock_exists)
    
    # Mock os.path.getctime to return a timestamp
    monkeypatch.setattr(os.path, "getctime", lambda x: 1672531200)  # 2023-01-01 00:00:00
    
    # Call the function
    metadata = ml_utils.get_model_metadata("random_forest")
    
    # Assert that basic metadata was returned
    assert metadata.model_type == "random_forest"
    assert metadata.version == "1.0.0"
    assert isinstance(metadata.created_at, datetime)
    assert metadata.accuracy is None
    assert metadata.f1_score is None
    assert metadata.training_parameters is None


# ===== Feature Extraction Tests =====

def test_create_feature_extractor():
    """
    Test that create_feature_extractor creates a feature extractor with the specified configuration.
    """
    # Create a test configuration
    config = {"feature_extraction": {"max_features": 1000}}
    
    # Mock the get_model_config function to return the test config
    with patch("document_service.utils.ml_utils.get_model_config", return_value=config):
        # Call the function
        extractor = ml_utils.create_feature_extractor()
        
        # Assert that a FeatureExtractor was created
        assert isinstance(extractor, FeatureExtractor)


def test_extract_features_from_document(monkeypatch):
    """
    Test that extract_features_from_document extracts features from a document.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Create a mock document
    mock_document = MagicMock(spec=Document)
    mock_document.metadata = MagicMock()
    mock_document.metadata.id = "test-doc-123"
    
    # Create a mock feature extractor
    mock_extractor = MagicMock(spec=FeatureExtractor)
    mock_extractor.is_fitted = True
    mock_extractor.extract_features_from_document.return_value = pd.Series([0.1, 0.2, 0.3])
    
    # Call the function
    with patch("document_service.utils.ml_utils.create_feature_extractor", return_value=mock_extractor):
        features = ml_utils.extract_features_from_document(mock_document, mock_extractor)
    
    # Assert that features were extracted
    assert isinstance(features, np.ndarray)
    assert features.shape == (3,)
    assert np.allclose(features, np.array([0.1, 0.2, 0.3]))
    
    # Assert that the extractor was called with the document
    mock_extractor.extract_features_from_document.assert_called_once_with(mock_document)


def test_extract_features_from_document_not_fitted(monkeypatch):
    """
    Test that extract_features_from_document handles the case when the extractor is not fitted.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
    """
    # Create a mock document
    mock_document = MagicMock(spec=Document)
    mock_document.metadata = MagicMock()
    mock_document.metadata.id = "test-doc-123"
    
    # Create a mock feature extractor
    mock_extractor = MagicMock(spec=FeatureExtractor)
    mock_extractor.is_fitted = False
    
    # Mock the text extraction and preprocessing classes
    mock_text_extractor = MagicMock()
    mock_text_extractor.extract_text.return_value = "test document text"
    
    mock_text_preprocessor = MagicMock()
    mock_text_preprocessor.preprocess.return_value = "processed test document text"
    
    mock_metadata_extractor = MagicMock()
    mock_metadata_extractor.extract_metadata_features.return_value = {"size": 1000, "page_count": 2}
    
    # Patch the imports
    with patch("document_service.models.feature_extraction.TextExtractor", return_value=mock_text_extractor), \
         patch("document_service.models.feature_extraction.TextPreprocessor", return_value=mock_text_preprocessor), \
         patch("document_service.models.feature_extraction.MetadataExtractor", return_value=mock_metadata_extractor):
        
        # Call the function
        features = ml_utils.extract_features_from_document(mock_document, mock_extractor)
    
    # Assert that features were extracted using the simplified approach
    assert isinstance(features, np.ndarray)
    assert features.shape == (2,)  # Two metadata features
    assert np.allclose(features, np.array([1000, 2]))


# ===== Prediction Tests =====

def test_predict_document_type(monkeypatch, mock_random_forest_classifier):
    """
    Test that predict_document_type correctly predicts the document type.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_random_forest_classifier: Mock RandomForestClassifier fixture
    """
    # Create a mock document
    mock_document = MagicMock(spec=Document)
    mock_document.metadata = MagicMock()
    mock_document.metadata.id = "test-doc-123"
    
    # Mock the extract_features_from_document function
    mock_features = np.array([0.1, 0.2, 0.3])
    monkeypatch.setattr(ml_utils, "extract_features_from_document", lambda doc, extractor: mock_features)
    
    # Mock the get_model_config function
    mock_config = {
        "document_categories": ["tax_return", "loan_application"],
        "version": "1.0.0"
    }
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_confidence_threshold function
    monkeypatch.setattr(ml_utils, "get_confidence_threshold", lambda doc_type: 0.8)
    
    # Configure the mock classifier
    mock_random_forest_classifier.predict.return_value = np.array(["loan_application"])
    mock_random_forest_classifier.predict_proba.return_value = np.array([[0.05, 0.95]])
    mock_random_forest_classifier.classes_ = np.array(["tax_return", "loan_application"])
    mock_random_forest_classifier._estimator_type = "classifier"
    
    # Call the function
    result = ml_utils.predict_document_type(mock_document, mock_random_forest_classifier)
    
    # Assert that the prediction was made correctly
    assert isinstance(result, ClassificationResult)
    assert result.document_id == "test-doc-123"
    assert result.document_type == "loan_application"
    assert result.confidence_scores == {"tax_return": 0.05, "loan_application": 0.95}
    assert result.prediction_time > 0
    assert result.model_type == "classifier"
    assert result.model_version == "1.0.0"
    assert result.threshold_applied is True
    assert result.requires_review is False  # 0.95 > 0.8


def test_predict_document_type_low_confidence(monkeypatch, mock_random_forest_classifier):
    """
    Test that predict_document_type correctly flags documents with low confidence for review.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_random_forest_classifier: Mock RandomForestClassifier fixture
    """
    # Create a mock document
    mock_document = MagicMock(spec=Document)
    mock_document.metadata = MagicMock()
    mock_document.metadata.id = "test-doc-123"
    
    # Mock the extract_features_from_document function
    mock_features = np.array([0.1, 0.2, 0.3])
    monkeypatch.setattr(ml_utils, "extract_features_from_document", lambda doc, extractor: mock_features)
    
    # Mock the get_model_config function
    mock_config = {
        "document_categories": ["tax_return", "loan_application"],
        "version": "1.0.0"
    }
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_confidence_threshold function
    monkeypatch.setattr(ml_utils, "get_confidence_threshold", lambda doc_type: 0.8)
    
    # Configure the mock classifier
    mock_random_forest_classifier.predict.return_value = np.array(["loan_application"])
    mock_random_forest_classifier.predict_proba.return_value = np.array([[0.3, 0.7]])
    mock_random_forest_classifier.classes_ = np.array(["tax_return", "loan_application"])
    mock_random_forest_classifier._estimator_type = "classifier"
    
    # Call the function
    result = ml_utils.predict_document_type(mock_document, mock_random_forest_classifier)
    
    # Assert that the prediction was made correctly and flagged for review
    assert isinstance(result, ClassificationResult)
    assert result.document_type == "loan_application"
    assert result.confidence_scores == {"tax_return": 0.3, "loan_application": 0.7}
    assert result.requires_review is True  # 0.7 < 0.8


def test_predict_document_type_with_svm_decision_function(monkeypatch, mock_svm_classifier):
    """
    Test that predict_document_type works with SVM models that use decision_function instead of predict_proba.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_svm_classifier: Mock SVM classifier fixture
    """
    # Create a mock document
    mock_document = MagicMock(spec=Document)
    mock_document.metadata = MagicMock()
    mock_document.metadata.id = "test-doc-123"
    
    # Mock the extract_features_from_document function
    mock_features = np.array([0.1, 0.2, 0.3])
    monkeypatch.setattr(ml_utils, "extract_features_from_document", lambda doc, extractor: mock_features)
    
    # Mock the get_model_config function
    mock_config = {
        "document_categories": ["tax_return", "loan_application"],
        "version": "1.0.0"
    }
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_confidence_threshold function
    monkeypatch.setattr(ml_utils, "get_confidence_threshold", lambda doc_type: 0.8)
    
    # Configure the mock classifier
    mock_svm_classifier.predict.return_value = np.array(["loan_application"])
    # Remove predict_proba
    del mock_svm_classifier.predict_proba
    # Add decision_function
    mock_svm_classifier.decision_function = MagicMock(return_value=np.array([2.0]))  # Positive value for loan_application
    mock_svm_classifier.classes_ = np.array(["tax_return", "loan_application"])
    mock_svm_classifier._estimator_type = "classifier"
    
    # Call the function
    result = ml_utils.predict_document_type(mock_document, mock_svm_classifier)
    
    # Assert that the prediction was made correctly
    assert isinstance(result, ClassificationResult)
    assert result.document_type == "loan_application"
    # Check that confidence scores were calculated from decision function
    assert "tax_return" in result.confidence_scores
    assert "loan_application" in result.confidence_scores
    assert result.confidence_scores["loan_application"] > 0.5  # Should be high for positive decision value


def test_predict_document_types_batch(monkeypatch, mock_random_forest_classifier):
    """
    Test that predict_document_types_batch correctly predicts types for a batch of documents.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_random_forest_classifier: Mock RandomForestClassifier fixture
    """
    # Create mock documents
    mock_doc1 = MagicMock(spec=Document)
    mock_doc1.metadata = MagicMock()
    mock_doc1.metadata.id = "test-doc-1"
    
    mock_doc2 = MagicMock(spec=Document)
    mock_doc2.metadata = MagicMock()
    mock_doc2.metadata.id = "test-doc-2"
    
    documents = [mock_doc1, mock_doc2]
    
    # Mock the extract_features_from_document function
    def mock_extract_features(doc, extractor):
        if doc.metadata.id == "test-doc-1":
            return np.array([0.1, 0.2, 0.3])
        else:
            return np.array([0.4, 0.5, 0.6])
    
    monkeypatch.setattr(ml_utils, "extract_features_from_document", mock_extract_features)
    
    # Mock the get_model_config function
    mock_config = {
        "document_categories": ["tax_return", "loan_application"],
        "version": "1.0.0"
    }
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_confidence_threshold function
    monkeypatch.setattr(ml_utils, "get_confidence_threshold", lambda doc_type: 0.8)
    
    # Configure the mock classifier
    mock_random_forest_classifier.predict.side_effect = [
        np.array(["loan_application"]),  # For doc1
        np.array(["tax_return"])         # For doc2
    ]
    mock_random_forest_classifier.predict_proba.side_effect = [
        np.array([[0.05, 0.95]]),  # For doc1
        np.array([[0.85, 0.15]])   # For doc2
    ]
    mock_random_forest_classifier.classes_ = np.array(["tax_return", "loan_application"])
    mock_random_forest_classifier._estimator_type = "classifier"
    
    # Call the function
    results = ml_utils.predict_document_types_batch(documents, mock_random_forest_classifier)
    
    # Assert that the predictions were made correctly
    assert len(results) == 2
    assert results[0].document_id == "test-doc-1"
    assert results[0].document_type == "loan_application"
    assert results[0].confidence_scores["loan_application"] == 0.95
    assert results[0].requires_review is False  # 0.95 > 0.8
    
    assert results[1].document_id == "test-doc-2"
    assert results[1].document_type == "tax_return"
    assert results[1].confidence_scores["tax_return"] == 0.85
    assert results[1].requires_review is False  # 0.85 > 0.8


def test_predict_document_types_batch_with_feature_extraction_error(monkeypatch, mock_random_forest_classifier):
    """
    Test that predict_document_types_batch handles feature extraction errors gracefully.
    
    Args:
        monkeypatch: Pytest monkeypatch fixture
        mock_random_forest_classifier: Mock RandomForestClassifier fixture
    """
    # Create mock documents
    mock_doc1 = MagicMock(spec=Document)
    mock_doc1.metadata = MagicMock()
    mock_doc1.metadata.id = "test-doc-1"
    
    mock_doc2 = MagicMock(spec=Document)
    mock_doc2.metadata = MagicMock()
    mock_doc2.metadata.id = "test-doc-2"
    
    documents = [mock_doc1, mock_doc2]
    
    # Mock the extract_features_from_document function to raise an exception for doc2
    def mock_extract_features(doc, extractor):
        if doc.metadata.id == "test-doc-1":
            return np.array([0.1, 0.2, 0.3])
        else:
            raise Exception("Feature extraction failed")
    
    monkeypatch.setattr(ml_utils, "extract_features_from_document", mock_extract_features)
    
    # Mock the get_model_config function
    mock_config = {
        "document_categories": ["tax_return", "loan_application"],
        "version": "1.0.0"
    }
    monkeypatch.setattr(ml_utils, "get_model_config", lambda: mock_config)
    
    # Mock the get_confidence_threshold function
    monkeypatch.setattr(ml_utils, "get_confidence_threshold", lambda doc_type: 0.8)
    
    # Configure the mock classifier
    mock_random_forest_classifier.predict.return_value = np.array(["loan_application"])
    mock_random_forest_classifier.predict_proba.return_value = np.array([[0.05, 0.95]])
    mock_random_forest_classifier.classes_ = np.array(["tax_return", "loan_application"])
    mock_random_forest_classifier._estimator_type = "classifier"
    
    # Call the function
    results = ml_utils.predict_document_types_batch(documents, mock_random_forest_classifier)
    
    # Assert that the predictions were made correctly for doc1 and handled error for doc2
    assert len(results) == 2
    assert results[0].document_id == "test-doc-1"
    assert results[0].document_type == "loan_application"
    assert results[0].confidence_scores["loan_application"] == 0.95
    
    assert results[1].document_id == "test-doc-2"
    assert results[1].document_type == "unknown"
    assert all(score == 0.0 for score in results[1].confidence_scores.values())
    assert results[1].requires_review is True


# ===== Confidence Scoring Tests =====

def test_calculate_confidence_score():
    """
    Test that calculate_confidence_score correctly calculates confidence scores.
    """
    # Create test probabilities
    probabilities = {
        "tax_return": 0.2,
        "loan_application": 0.7,
        "bank_statement": 0.1
    }
    
    # Mock the get_model_config function
    with patch("document_service.utils.ml_utils.get_model_config") as mock_get_config:
        mock_get_config.return_value = {
            "confidence_thresholds": {
                "high": 0.9,
                "medium": 0.7,
                "low": 0.5
            }
        }
        
        # Mock the get_confidence_threshold function
        with patch("document_service.utils.ml_utils.get_confidence_threshold", return_value=0.8):
            # Call the function
            score = ml_utils.calculate_confidence_score(probabilities, "loan_application")
    
    # Assert that the confidence score was calculated correctly
    assert isinstance(score, ConfidenceScore)
    assert score.value == 0.7
    assert score.level == "medium"  # 0.7 >= 0.7 (medium threshold)
    assert score.margin == 0.5  # 0.7 - 0.2 = 0.5
    assert score.threshold == 0.8
    assert score.requires_review is True  # 0.7 < 0.8


def test_get_confidence_level():
    """
    Test that get_confidence_level returns the correct confidence level.
    """
    # Mock the get_model_config function
    with patch("document_service.utils.ml_utils.get_model_config") as mock_get_config:
        mock_get_config.return_value = {
            "confidence_thresholds": {
                "high": 0.9,
                "medium": 0.7,
                "low": 0.5
            }
        }
        
        # Test different confidence values
        assert ml_utils.get_confidence_level(0.95) == "high"    # 0.95 >= 0.9
        assert ml_utils.get_confidence_level(0.8) == "medium"  # 0.8 >= 0.7
        assert ml_utils.get_confidence_level(0.6) == "low"     # 0.6 >= 0.5
        assert ml_utils.get_confidence_level(0.3) == "very_low"  # 0.3 < 0.5


# ===== Model Evaluation Tests =====

def test_evaluate_model_performance():
    """
    Test that evaluate_model_performance correctly evaluates model performance.
    """
    # Create test data
    X_test = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6], [0.7, 0.8]])
    y_test = np.array(["tax_return", "loan_application", "tax_return", "loan_application"])
    
    # Create a mock model
    mock_model = MagicMock()
    mock_model.predict.return_value = np.array(["tax_return", "loan_application", "tax_return", "loan_application"])
    mock_model.predict_proba.return_value = np.array([
        [0.9, 0.1],
        [0.2, 0.8],
        [0.7, 0.3],
        [0.1, 0.9]
    ])
    
    # Call the function
    with patch("document_service.utils.ml_utils.accuracy_score", return_value=1.0), \
         patch("document_service.utils.ml_utils.precision_score", return_value=1.0), \
         patch("document_service.utils.ml_utils.recall_score", return_value=1.0), \
         patch("document_service.utils.ml_utils.f1_score", return_value=1.0), \
         patch("document_service.utils.ml_utils.confusion_matrix", return_value=np.array([[2, 0], [0, 2]])):
        
        metrics = ml_utils.evaluate_model_performance(mock_model, X_test, y_test)
    
    # Assert that the metrics were calculated correctly
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["confusion_matrix"] == [[2, 0], [0, 2]]
    assert metrics["average_confidence"] > 0.0
    assert metrics["sample_count"] == 4


def test_monitor_prediction_performance():
    """
    Test that monitor_prediction_performance correctly calculates monitoring metrics.
    """
    # Create test predictions
    predictions = [
        ClassificationResult(
            document_id="doc1",
            document_type="loan_application",
            confidence_scores={"tax_return": 0.1, "loan_application": 0.9},
            prediction_time=0.1,
            model_type="classifier",
            model_version="1.0.0",
            threshold_applied=True,
            requires_review=False
        ),
        ClassificationResult(
            document_id="doc2",
            document_type="tax_return",
            confidence_scores={"tax_return": 0.7, "loan_application": 0.3},
            prediction_time=0.2,
            model_type="classifier",
            model_version="1.0.0",
            threshold_applied=True,
            requires_review=True
        ),
        ClassificationResult(
            document_id="doc3",
            document_type="unknown",
            confidence_scores={"tax_return": 0.0, "loan_application": 0.0},
            prediction_time=0.3,
            model_type="classifier",
            model_version="1.0.0",
            threshold_applied=False,
            requires_review=True,
            error="Classification failed"
        )
    ]
    
    # Call the function
    metrics = ml_utils.monitor_prediction_performance(predictions)
    
    # Assert that the metrics were calculated correctly
    assert metrics["total_predictions"] == 3
    assert metrics["requires_review_count"] == 2
    assert metrics["requires_review_percentage"] == 2/3
    assert metrics["error_count"] == 1
    assert metrics["error_percentage"] == 1/3
    assert "loan_application" in metrics["average_confidence_by_type"]
    assert "tax_return" in metrics["average_confidence_by_type"]
    assert metrics["average_confidence_by_type"]["loan_application"] == 0.9
    assert metrics["average_confidence_by_type"]["tax_return"] == 0.7
    assert metrics["average_prediction_time"] == 0.2  # (0.1 + 0.2 + 0.3) / 3


# ===== Model Versioning Tests =====

def test_get_model_version():
    """
    Test that get_model_version returns the correct model version.
    """
    # Mock the get_model_config function
    with patch("document_service.utils.ml_utils.get_model_config") as mock_get_config:
        mock_get_config.return_value = {"version": "1.0.0"}
        
        # Call the function
        version = ml_utils.get_model_version()
    
    # Assert that the version was returned correctly
    assert version == "1.0.0"


def test_check_model_compatibility_random_forest():
    """
    Test that check_model_compatibility correctly checks compatibility for RandomForestClassifier.
    """
    # Create a mock RandomForestClassifier
    mock_rf = MagicMock(spec=RandomForestClassifier)
    mock_rf.n_estimators = 100
    mock_rf.criterion = "gini"
    mock_rf.max_depth = None
    
    # Call the function
    result = ml_utils.check_model_compatibility(mock_rf)
    
    # Assert that the model is compatible
    assert result is True


def test_check_model_compatibility_svm():
    """
    Test that check_model_compatibility correctly checks compatibility for SVC.
    """
    # Create a mock SVC
    mock_svm = MagicMock(spec=SVC)
    mock_svm.C = 1.0
    mock_svm.kernel = "linear"
    mock_svm.gamma = "scale"
    
    # Call the function
    result = ml_utils.check_model_compatibility(mock_svm)
    
    # Assert that the model is compatible
    assert result is True


def test_check_model_compatibility_other():
    """
    Test that check_model_compatibility correctly checks compatibility for other model types.
    """
    # Create a mock model that's not RandomForestClassifier or SVC
    mock_model = MagicMock()
    mock_model.predict = MagicMock()
    
    # Call the function
    result = ml_utils.check_model_compatibility(mock_model)
    
    # Assert that the model is compatible if it has a predict method
    assert result is True


def test_validate_model():
    """
    Test that validate_model correctly validates a model.
    """
    # Create a mock model
    mock_model = MagicMock()
    mock_model.predict = MagicMock(return_value=np.array(["tax_return"]))
    mock_model.classes_ = np.array(["tax_return", "loan_application"])
    
    # Create test data
    X_sample = np.array([[0.1, 0.2, 0.3]])
    expected_classes = {"tax_return", "loan_application"}
    
    # Call the function
    result = ml_utils.validate_model(mock_model, X_sample, expected_classes)
    
    # Assert that the model is valid
    assert result is True
    mock_model.predict.assert_called_once_with(X_sample)


def test_validate_model_missing_classes():
    """
    Test that validate_model correctly identifies models with missing classes.
    """
    # Create a mock model
    mock_model = MagicMock()
    mock_model.predict = MagicMock(return_value=np.array(["tax_return"]))
    mock_model.classes_ = np.array(["tax_return"])  # Missing loan_application
    
    # Create test data
    X_sample = np.array([[0.1, 0.2, 0.3]])
    expected_classes = {"tax_return", "loan_application"}
    
    # Call the function
    result = ml_utils.validate_model(mock_model, X_sample, expected_classes)
    
    # Assert that the model is invalid due to missing classes
    assert result is False


def test_validate_model_prediction_error():
    """
    Test that validate_model correctly handles prediction errors.
    """
    # Create a mock model
    mock_model = MagicMock()
    mock_model.predict = MagicMock(side_effect=Exception("Prediction failed"))
    mock_model.classes_ = np.array(["tax_return", "loan_application"])
    
    # Create test data
    X_sample = np.array([[0.1, 0.2, 0.3]])
    expected_classes = {"tax_return", "loan_application"}
    
    # Call the function
    result = ml_utils.validate_model(mock_model, X_sample, expected_classes)
    
    # Assert that the model is invalid due to prediction error
    assert result is False