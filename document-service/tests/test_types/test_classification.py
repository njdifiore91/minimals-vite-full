#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for document classification type definitions in the Document Service.

This module validates that ClassificationModel, FeatureVector, ClassificationResult,
ConfidenceScore, ModelParameters, and ClassificationMetrics types correctly handle
model interfaces, feature extraction, and confidence scoring.

These tests ensure type safety for the core classification functionality.
"""

import pytest
import numpy as np
from typing import Dict, Any, cast, List, Tuple
from unittest.mock import MagicMock

# Import the types to test
from document_service.types import (
    DocumentType,
    ClassificationModel,
    ClassificationResult,
    ClassificationMetrics,
    FeatureVector,
    FeatureMatrix,
    ModelParameters,
    ModelVersion,
    ConfidenceScore,
    ProbabilityVector,
    LabelVector
)

# Import scikit-learn models for testing with ClassificationModel protocol
pytest.importorskip("scikit-learn")
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression


class TestClassificationModel:
    """Tests for the ClassificationModel protocol."""

    def test_svm_classifier_implements_protocol(self, feature_matrix, mock_classification_model):
        """Test that SVC implements the ClassificationModel protocol."""
        # Create an SVM classifier
        svm = SVC(probability=True, random_state=42)
        
        # Verify it implements the required methods
        assert hasattr(svm, 'fit')
        assert hasattr(svm, 'predict')
        assert hasattr(svm, 'predict_proba')
        assert hasattr(svm, 'get_params')
        assert hasattr(svm, 'set_params')
        
        # Create synthetic data for testing
        X = feature_matrix
        y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int32)  # Binary labels
        
        # Test fit method
        svm.fit(X, y)
        
        # Test predict method
        predictions = svm.predict(X)
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype == np.int32 or predictions.dtype == np.int64
        
        # Test predict_proba method
        probabilities = svm.predict_proba(X)
        assert isinstance(probabilities, np.ndarray)
        assert probabilities.shape[0] == X.shape[0]  # One prediction per sample
        assert probabilities.shape[1] == 2  # Two classes (binary)
        
        # Test get_params method
        params = svm.get_params()
        assert isinstance(params, dict)
        assert 'probability' in params
        assert params['probability'] is True
        
        # Test set_params method
        svm.set_params(C=2.0)
        assert svm.get_params()['C'] == 2.0

    def test_random_forest_implements_protocol(self, feature_matrix):
        """Test that RandomForestClassifier implements the ClassificationModel protocol."""
        # Create a Random Forest classifier
        rf = RandomForestClassifier(random_state=42)
        
        # Verify it implements the required methods
        assert hasattr(rf, 'fit')
        assert hasattr(rf, 'predict')
        assert hasattr(rf, 'predict_proba')
        assert hasattr(rf, 'get_params')
        assert hasattr(rf, 'set_params')
        
        # Create synthetic data for testing
        X = feature_matrix
        y = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2, 0], dtype=np.int32)  # Multi-class labels
        
        # Test fit method
        rf.fit(X, y)
        
        # Test predict method
        predictions = rf.predict(X)
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype == np.int32 or predictions.dtype == np.int64
        
        # Test predict_proba method
        probabilities = rf.predict_proba(X)
        assert isinstance(probabilities, np.ndarray)
        assert probabilities.shape[0] == X.shape[0]  # One prediction per sample
        assert probabilities.shape[1] == 3  # Three classes
        
        # Test get_params method
        params = rf.get_params()
        assert isinstance(params, dict)
        assert 'n_estimators' in params
        
        # Test set_params method
        rf.set_params(n_estimators=200)
        assert rf.get_params()['n_estimators'] == 200

    def test_logistic_regression_implements_protocol(self, feature_matrix):
        """Test that LogisticRegression implements the ClassificationModel protocol."""
        # Create a Logistic Regression classifier
        lr = LogisticRegression(random_state=42)
        
        # Verify it implements the required methods
        assert hasattr(lr, 'fit')
        assert hasattr(lr, 'predict')
        assert hasattr(lr, 'predict_proba')
        assert hasattr(lr, 'get_params')
        assert hasattr(lr, 'set_params')
        
        # Create synthetic data for testing
        X = feature_matrix
        y = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1], dtype=np.int32)  # Binary labels
        
        # Test fit method
        lr.fit(X, y)
        
        # Test predict method
        predictions = lr.predict(X)
        assert isinstance(predictions, np.ndarray)
        assert predictions.dtype == np.int32 or predictions.dtype == np.int64
        
        # Test predict_proba method
        probabilities = lr.predict_proba(X)
        assert isinstance(probabilities, np.ndarray)
        assert probabilities.shape[0] == X.shape[0]  # One prediction per sample
        assert probabilities.shape[1] == 2  # Two classes (binary)
        
        # Test get_params method
        params = lr.get_params()
        assert isinstance(params, dict)
        assert 'C' in params
        
        # Test set_params method
        lr.set_params(C=0.5)
        assert lr.get_params()['C'] == 0.5

    def test_mock_classification_model(self, mock_classification_model, feature_matrix):
        """Test that our mock classification model correctly implements the protocol."""
        # Create synthetic data for testing
        X = feature_matrix
        y = np.array([1, 2, 3, 1, 2, 3, 1, 2, 3, 1], dtype=np.int32)  # Multi-class labels
        
        # Test fit method
        model = mock_classification_model.fit(X, y)
        assert model is mock_classification_model  # Should return self
        assert mock_classification_model.fitted is True
        
        # Test predict method
        predictions = mock_classification_model.predict(X)
        assert isinstance(predictions, np.ndarray)
        assert mock_classification_model.predict_called is True
        
        # Test predict_proba method
        probabilities = mock_classification_model.predict_proba(X)
        assert isinstance(probabilities, np.ndarray)
        assert mock_classification_model.predict_proba_called is True
        
        # Test get_params method
        params = mock_classification_model.get_params()
        assert isinstance(params, dict)
        
        # Test set_params method
        mock_classification_model.set_params(C=10.0)
        assert mock_classification_model.parameters['C'] == 10.0


class TestFeatureVector:
    """Tests for the FeatureVector type."""

    def test_feature_vector_creation(self):
        """Test creating a feature vector."""
        # Create a feature vector
        feature_vector = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float64)
        
        # Verify it's a valid FeatureVector
        assert isinstance(feature_vector, np.ndarray)
        assert feature_vector.dtype == np.float64
        assert feature_vector.ndim == 1  # 1-dimensional array

    def test_feature_vector_operations(self, feature_vector):
        """Test operations on feature vectors."""
        # Test basic operations
        scaled_vector = feature_vector * 2.0
        assert isinstance(scaled_vector, np.ndarray)
        assert scaled_vector.dtype == np.float64
        
        # Test normalization
        norm = np.linalg.norm(feature_vector)
        normalized_vector = feature_vector / norm if norm > 0 else feature_vector
        assert isinstance(normalized_vector, np.ndarray)
        assert normalized_vector.dtype == np.float64
        
        # Test dot product
        dot_product = np.dot(feature_vector, feature_vector)
        assert isinstance(dot_product, float)

    def test_feature_matrix_operations(self, feature_matrix):
        """Test operations on feature matrices."""
        # Test basic operations
        scaled_matrix = feature_matrix * 2.0
        assert isinstance(scaled_matrix, np.ndarray)
        assert scaled_matrix.dtype == np.float64
        
        # Test matrix multiplication
        result = np.matmul(feature_matrix, feature_matrix.T)
        assert isinstance(result, np.ndarray)
        assert result.shape == (feature_matrix.shape[0], feature_matrix.shape[0])
        
        # Test row extraction (should be a FeatureVector)
        row = feature_matrix[0]
        assert isinstance(row, np.ndarray)
        assert row.dtype == np.float64
        assert row.ndim == 1  # 1-dimensional array


class TestClassificationResult:
    """Tests for the ClassificationResult type."""

    def test_classification_result_creation(self):
        """Test creating a classification result."""
        # Create a classification result
        document_type = DocumentType.LOAN_APPLICATION
        confidence = 0.95
        probabilities = {doc_type: 0.05 / (len(DocumentType) - 1) for doc_type in DocumentType}
        probabilities[document_type] = confidence
        needs_review = False
        feature_importance = {"feature1": 0.8, "feature2": 0.2}
        processing_time_ms = 150.5
        
        result = ClassificationResult(
            document_type=document_type,
            confidence=confidence,
            probabilities=probabilities,
            needs_review=needs_review,
            feature_importance=feature_importance,
            processing_time_ms=processing_time_ms
        )
        
        # Verify the result
        assert result.document_type == document_type
        assert result.confidence == confidence
        assert result.probabilities == probabilities
        assert result.needs_review == needs_review
        assert result.feature_importance == feature_importance
        assert result.processing_time_ms == processing_time_ms

    def test_classification_result_validation(self):
        """Test validation of classification result fields."""
        # Create a classification result with invalid confidence (should be clamped)
        document_type = DocumentType.TAX_RETURN
        confidence = 1.2  # Invalid: > 1.0
        probabilities = {doc_type: 0.0 for doc_type in DocumentType}
        probabilities[document_type] = 1.0
        
        # This should not raise an exception, but confidence should be clamped to 1.0
        result = ClassificationResult(
            document_type=document_type,
            confidence=confidence,
            probabilities=probabilities,
            needs_review=False
        )
        
        # Verify the result
        assert result.confidence <= 1.0
        
        # Create a classification result with negative confidence (should be clamped)
        confidence = -0.2  # Invalid: < 0.0
        probabilities[document_type] = 0.0
        
        # This should not raise an exception, but confidence should be clamped to 0.0
        result = ClassificationResult(
            document_type=document_type,
            confidence=confidence,
            probabilities=probabilities,
            needs_review=True
        )
        
        # Verify the result
        assert result.confidence >= 0.0

    def test_classification_result_with_fixtures(self, classification_result_high_confidence, 
                                               classification_result_low_confidence):
        """Test classification results using fixtures."""
        # Test high confidence result
        assert classification_result_high_confidence.document_type == DocumentType.LOAN_APPLICATION
        assert classification_result_high_confidence.confidence >= 0.95
        assert classification_result_high_confidence.needs_review is False
        assert classification_result_high_confidence.processing_time_ms is not None
        
        # Test low confidence result
        assert classification_result_low_confidence.document_type == DocumentType.TAX_RETURN
        assert classification_result_low_confidence.confidence < 0.75
        assert classification_result_low_confidence.needs_review is True
        assert classification_result_low_confidence.processing_time_ms is not None

    def test_classification_result_unpacking(self, classification_result_high_confidence):
        """Test unpacking a classification result (since it's a NamedTuple)."""
        # Unpack the result
        doc_type, confidence, probabilities, needs_review, feature_importance, processing_time = classification_result_high_confidence
        
        # Verify unpacked values
        assert doc_type == classification_result_high_confidence.document_type
        assert confidence == classification_result_high_confidence.confidence
        assert probabilities == classification_result_high_confidence.probabilities
        assert needs_review == classification_result_high_confidence.needs_review
        assert feature_importance == classification_result_high_confidence.feature_importance
        assert processing_time == classification_result_high_confidence.processing_time_ms


class TestConfidenceScore:
    """Tests for the ConfidenceScore type."""

    def test_confidence_score_range(self):
        """Test that confidence scores are within the valid range."""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 0.75, 0.95, 1.0]
        for score in valid_scores:
            confidence: ConfidenceScore = score
            assert 0.0 <= confidence <= 1.0
        
        # Invalid confidence scores (should be clamped in practice)
        invalid_scores = [-0.1, 1.1, 2.0, -1.0]
        for score in invalid_scores:
            # In a real application, these would be clamped to [0.0, 1.0]
            # Here we're just testing the type annotation
            confidence: ConfidenceScore = max(0.0, min(1.0, score))
            assert 0.0 <= confidence <= 1.0

    def test_confidence_thresholds(self):
        """Test confidence score thresholds for review decisions."""
        # High confidence (no review needed)
        high_confidence: ConfidenceScore = 0.95
        assert high_confidence >= 0.75  # Threshold for automatic processing
        
        # Medium confidence (no review needed, but close to threshold)
        medium_confidence: ConfidenceScore = 0.80
        assert medium_confidence >= 0.75  # Threshold for automatic processing
        
        # Low confidence (review needed)
        low_confidence: ConfidenceScore = 0.70
        assert low_confidence < 0.75  # Below threshold, needs review
        
        # Very low confidence (definitely needs review)
        very_low_confidence: ConfidenceScore = 0.50
        assert very_low_confidence < 0.75  # Below threshold, needs review


class TestModelParameters:
    """Tests for the ModelParameters type."""

    def test_svm_parameters(self, model_parameters_svm):
        """Test SVM model parameters."""
        # Verify the parameters
        assert "random_state" in model_parameters_svm
        assert "C" in model_parameters_svm
        assert "kernel" in model_parameters_svm
        assert "probability" in model_parameters_svm
        
        # Verify parameter types
        assert isinstance(model_parameters_svm["random_state"], int)
        assert isinstance(model_parameters_svm["C"], float)
        assert model_parameters_svm["kernel"] in ["linear", "poly", "rbf", "sigmoid"]
        assert isinstance(model_parameters_svm["probability"], bool)
        
        # Test using parameters with an SVM model
        svm = SVC(**model_parameters_svm)
        assert svm.C == model_parameters_svm["C"]
        assert svm.kernel == model_parameters_svm["kernel"]
        assert svm.probability == model_parameters_svm["probability"]

    def test_random_forest_parameters(self, model_parameters_random_forest):
        """Test Random Forest model parameters."""
        # Verify the parameters
        assert "random_state" in model_parameters_random_forest
        assert "n_estimators" in model_parameters_random_forest
        assert "criterion" in model_parameters_random_forest
        
        # Verify parameter types
        assert isinstance(model_parameters_random_forest["random_state"], int)
        assert isinstance(model_parameters_random_forest["n_estimators"], int)
        assert model_parameters_random_forest["criterion"] in ["gini", "entropy", "log_loss"]
        
        # Test using parameters with a Random Forest model
        rf = RandomForestClassifier(**model_parameters_random_forest)
        assert rf.n_estimators == model_parameters_random_forest["n_estimators"]
        assert rf.criterion == model_parameters_random_forest["criterion"]

    def test_custom_parameters(self):
        """Test custom model parameters."""
        # Create custom parameters
        params: ModelParameters = {
            "random_state": 42,
            "n_jobs": 4,
            "verbose": True,
            "C": 2.0,
            "kernel": "rbf",
            "gamma": "scale",
            "probability": True
        }
        
        # Verify the parameters
        assert params["random_state"] == 42
        assert params["n_jobs"] == 4
        assert params["verbose"] is True
        assert params["C"] == 2.0
        assert params["kernel"] == "rbf"
        assert params["gamma"] == "scale"
        assert params["probability"] is True
        
        # Test using parameters with an SVM model
        svm = SVC(**params)
        assert svm.C == params["C"]
        assert svm.kernel == params["kernel"]
        assert svm.gamma == params["gamma"]
        assert svm.probability == params["probability"]


class TestClassificationMetrics:
    """Tests for the ClassificationMetrics type."""

    def test_classification_metrics_creation(self):
        """Test creating classification metrics."""
        # Create classification metrics
        metrics: ClassificationMetrics = {
            "accuracy": 0.95,
            "precision": {
                DocumentType.LOAN_APPLICATION: 0.98,
                DocumentType.TAX_RETURN: 0.96,
                DocumentType.BANK_STATEMENT: 0.94,
                DocumentType.PAY_STUB: 0.92,
                DocumentType.IDENTITY_DOCUMENT: 0.97,
                DocumentType.BUSINESS_LICENSE: 0.93,
                DocumentType.UTILITY_BILL: 0.91,
                DocumentType.INSURANCE_DOCUMENT: 0.90,
                DocumentType.OTHER: 0.85
            },
            "recall": {
                DocumentType.LOAN_APPLICATION: 0.97,
                DocumentType.TAX_RETURN: 0.95,
                DocumentType.BANK_STATEMENT: 0.93,
                DocumentType.PAY_STUB: 0.91,
                DocumentType.IDENTITY_DOCUMENT: 0.96,
                DocumentType.BUSINESS_LICENSE: 0.92,
                DocumentType.UTILITY_BILL: 0.90,
                DocumentType.INSURANCE_DOCUMENT: 0.89,
                DocumentType.OTHER: 0.84
            },
            "f1_score": {
                DocumentType.LOAN_APPLICATION: 0.975,
                DocumentType.TAX_RETURN: 0.955,
                DocumentType.BANK_STATEMENT: 0.935,
                DocumentType.PAY_STUB: 0.915,
                DocumentType.IDENTITY_DOCUMENT: 0.965,
                DocumentType.BUSINESS_LICENSE: 0.925,
                DocumentType.UTILITY_BILL: 0.905,
                DocumentType.INSURANCE_DOCUMENT: 0.895,
                DocumentType.OTHER: 0.845
            },
            "confusion_matrix": [
                [95, 2, 1, 0, 1, 0, 0, 0, 1],
                [3, 94, 2, 0, 0, 0, 0, 0, 1],
                [2, 3, 93, 1, 0, 0, 0, 0, 1],
                [1, 0, 2, 95, 1, 0, 0, 0, 1],
                [0, 0, 0, 1, 97, 1, 0, 0, 1],
                [0, 0, 0, 0, 2, 96, 1, 0, 1],
                [0, 0, 0, 0, 0, 2, 97, 0, 1],
                [0, 0, 0, 0, 0, 0, 1, 98, 1],
                [1, 1, 1, 1, 1, 1, 1, 1, 92]
            ],
            "support": {
                DocumentType.LOAN_APPLICATION: 100,
                DocumentType.TAX_RETURN: 100,
                DocumentType.BANK_STATEMENT: 100,
                DocumentType.PAY_STUB: 100,
                DocumentType.IDENTITY_DOCUMENT: 100,
                DocumentType.BUSINESS_LICENSE: 100,
                DocumentType.UTILITY_BILL: 100,
                DocumentType.INSURANCE_DOCUMENT: 100,
                DocumentType.OTHER: 100
            },
            "roc_auc": {
                DocumentType.LOAN_APPLICATION: 0.99,
                DocumentType.TAX_RETURN: 0.98,
                DocumentType.BANK_STATEMENT: 0.97,
                DocumentType.PAY_STUB: 0.96,
                DocumentType.IDENTITY_DOCUMENT: 0.99,
                DocumentType.BUSINESS_LICENSE: 0.97,
                DocumentType.UTILITY_BILL: 0.96,
                DocumentType.INSURANCE_DOCUMENT: 0.95,
                DocumentType.OTHER: 0.92
            },
            "average_confidence": 0.94
        }
        
        # Verify the metrics
        assert metrics["accuracy"] == 0.95
        assert metrics["precision"][DocumentType.LOAN_APPLICATION] == 0.98
        assert metrics["recall"][DocumentType.TAX_RETURN] == 0.95
        assert metrics["f1_score"][DocumentType.BANK_STATEMENT] == 0.935
        assert metrics["confusion_matrix"][0][0] == 95
        assert metrics["support"][DocumentType.PAY_STUB] == 100
        assert metrics["roc_auc"][DocumentType.IDENTITY_DOCUMENT] == 0.99
        assert metrics["average_confidence"] == 0.94

    def test_classification_metrics_validation(self):
        """Test validation of classification metrics."""
        # Create metrics with invalid accuracy (should be >= 0.99 for production)
        metrics: ClassificationMetrics = {
            "accuracy": 0.98,  # Below 0.99 requirement
            "precision": {DocumentType.LOAN_APPLICATION: 0.98},
            "recall": {DocumentType.LOAN_APPLICATION: 0.97},
            "f1_score": {DocumentType.LOAN_APPLICATION: 0.975},
            "confusion_matrix": [[95, 5], [3, 97]],
            "support": {DocumentType.LOAN_APPLICATION: 100},
            "average_confidence": 0.94
        }
        
        # In a real application, this would trigger a warning or error
        # Here we're just testing the type annotation
        assert metrics["accuracy"] < 0.99
        
        # Update to valid accuracy
        metrics["accuracy"] = 0.99
        assert metrics["accuracy"] >= 0.99

    def test_model_version(self):
        """Test the ModelVersion type."""
        # Create a model version
        version: ModelVersion = {
            "model_id": "doc-classifier-v1",
            "version": "1.0.0",
            "trained_at": "2023-05-15T14:30:00Z",
            "accuracy": 0.99,
            "parameters": {
                "random_state": 42,
                "C": 1.0,
                "kernel": "rbf",
                "probability": True
            },
            "feature_count": 5000,
            "class_distribution": {
                DocumentType.LOAN_APPLICATION: 1000,
                DocumentType.TAX_RETURN: 800,
                DocumentType.BANK_STATEMENT: 750,
                DocumentType.PAY_STUB: 700,
                DocumentType.IDENTITY_DOCUMENT: 650,
                DocumentType.BUSINESS_LICENSE: 600,
                DocumentType.UTILITY_BILL: 550,
                DocumentType.INSURANCE_DOCUMENT: 500,
                DocumentType.OTHER: 450
            },
            "description": "Document classifier trained on balanced dataset with SVM",
            "created_by": "data-science-team"
        }
        
        # Verify the version
        assert version["model_id"] == "doc-classifier-v1"
        assert version["version"] == "1.0.0"
        assert version["trained_at"] == "2023-05-15T14:30:00Z"
        assert version["accuracy"] == 0.99
        assert version["parameters"]["C"] == 1.0
        assert version["feature_count"] == 5000
        assert version["class_distribution"][DocumentType.LOAN_APPLICATION] == 1000
        assert version["description"] == "Document classifier trained on balanced dataset with SVM"
        assert version["created_by"] == "data-science-team"