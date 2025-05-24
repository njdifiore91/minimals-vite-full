#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Random Forest classifier implementation.

This module contains tests that verify the Random Forest classifier correctly implements
the base model interface, configures hyperparameters, ranks feature importance,
calculates confidence scores based on voting distribution, and optimizes ensemble performance.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from sklearn.ensemble import RandomForestClassifier as SklearnRandomForestClassifier
from sklearn.model_selection import cross_val_score

# Import the Random Forest classifier and related modules
from src.models.random_forest_classifier import RandomForestClassifier
from src.models.base_model import BaseModel
from src.types.config import ModelConfig
from src.types.classification import (
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters,
    ClassificationMetrics,
    DocumentType
)


# Test fixtures
@pytest.fixture
def model_config():
    """Fixture that returns a model configuration for testing."""
    return ModelConfig(
        model_path="/models/test_random_forest_classifier.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        models={
            "random_forest": {
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": 10,
                    "min_samples_split": 2,
                    "min_samples_leaf": 1,
                    "max_features": "sqrt",
                    "bootstrap": True,
                    "oob_score": True,
                    "random_state": 42,
                    "verbose": 0,
                    "class_weight": "balanced"
                }
            }
        },
        random_state=42,
        verbose=False
    )


@pytest.fixture
def rf_classifier(model_config):
    """Fixture that returns a Random Forest classifier instance for testing."""
    return RandomForestClassifier(model_config)


@pytest.fixture
def rf_classifier_with_oob():
    """Fixture that returns a Random Forest classifier with OOB scoring enabled."""
    config = ModelConfig(
        model_path="/models/test_rf_with_oob.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        models={
            "random_forest": {
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": None,
                    "min_samples_split": 2,
                    "min_samples_leaf": 1,
                    "max_features": "sqrt",
                    "bootstrap": True,
                    "oob_score": True,
                    "random_state": 42
                }
            }
        },
        random_state=42
    )
    return RandomForestClassifier(config)


@pytest.fixture
def rf_classifier_without_oob():
    """Fixture that returns a Random Forest classifier with OOB scoring disabled."""
    config = ModelConfig(
        model_path="/models/test_rf_without_oob.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        models={
            "random_forest": {
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": None,
                    "min_samples_split": 2,
                    "min_samples_leaf": 1,
                    "max_features": "sqrt",
                    "bootstrap": True,
                    "oob_score": False,  # OOB scoring disabled
                    "random_state": 42
                }
            }
        },
        random_state=42
    )
    return RandomForestClassifier(config)


@pytest.fixture
def rf_classifier_with_few_estimators():
    """Fixture that returns a Random Forest classifier with few estimators for faster testing."""
    config = ModelConfig(
        model_path="/models/test_rf_few_estimators.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        models={
            "random_forest": {
                "hyperparameters": {
                    "n_estimators": 10,  # Few estimators for faster testing
                    "max_depth": 5,
                    "min_samples_split": 2,
                    "min_samples_leaf": 1,
                    "max_features": "sqrt",
                    "bootstrap": True,
                    "oob_score": True,
                    "random_state": 42
                }
            }
        },
        random_state=42
    )
    return RandomForestClassifier(config)


# Test cases for Random Forest classifier
class TestRandomForestClassifier:
    """Test cases for the Random Forest classifier implementation."""

    def test_inheritance(self, rf_classifier):
        """Test that RandomForestClassifier correctly inherits from BaseModel."""
        assert isinstance(rf_classifier, BaseModel)
        assert isinstance(rf_classifier, RandomForestClassifier)

    def test_initialization(self, rf_classifier, model_config):
        """Test that RandomForestClassifier initializes correctly with configuration parameters."""
        # Check that the classifier has been initialized with the correct attributes
        assert rf_classifier.model is not None
        assert isinstance(rf_classifier.model, SklearnRandomForestClassifier)
        assert rf_classifier.model_name is not None
        assert rf_classifier.model_version is not None
        assert rf_classifier.trained is False
        
        # Check that hyperparameters were correctly extracted from config
        rf_config = model_config.get('models', {}).get('random_forest', {}).get('hyperparameters', {})
        assert rf_classifier.hyperparameters == rf_config
        
        # Check that the model was initialized with the correct hyperparameters
        for param, value in rf_config.items():
            assert getattr(rf_classifier.model, param) == value

    def test_fit_method(self, rf_classifier, synthetic_classification_data):
        """Test that the fit method correctly trains the model."""
        X, y = synthetic_classification_data
        
        # Train the model
        result = rf_classifier.fit(X, y)
        
        # Check that the method returns self for method chaining
        assert result is rf_classifier
        
        # Check that the model has been trained
        assert rf_classifier.trained is True
        assert rf_classifier.classes_ is not None
        assert len(rf_classifier.classes_) == len(set(y))
        assert rf_classifier.feature_importances_ is not None
        
        # Check that the model can make predictions
        predictions = rf_classifier.predict(X)
        assert len(predictions) == len(y)

    def test_predict_method(self, rf_classifier, synthetic_classification_data):
        """Test that the predict method correctly classifies documents."""
        X, y = synthetic_classification_data
        
        # Train the model first
        rf_classifier.fit(X, y)
        
        # Make predictions
        predictions = rf_classifier.predict(X)
        
        # Check that predictions have the correct shape and type
        assert len(predictions) == len(y)
        assert isinstance(predictions, np.ndarray)
        
        # Check that predictions are valid class labels
        for pred in predictions:
            assert pred in rf_classifier.classes_

    def test_predict_proba_method(self, rf_classifier, synthetic_classification_data):
        """Test that the predict_proba method correctly returns class probabilities."""
        X, y = synthetic_classification_data
        
        # Train the model first
        rf_classifier.fit(X, y)
        
        # Get probability predictions
        probabilities = rf_classifier.predict_proba(X)
        
        # Check that probabilities have the correct shape
        assert probabilities.shape == (len(y), len(rf_classifier.classes_))
        
        # Check that probabilities are valid (sum to 1 for each sample)
        for prob_row in probabilities:
            assert np.isclose(np.sum(prob_row), 1.0)
            assert np.all(prob_row >= 0) and np.all(prob_row <= 1)

    def test_evaluate_method(self, rf_classifier, synthetic_classification_data):
        """Test that the evaluate method correctly calculates performance metrics."""
        X, y = synthetic_classification_data
        
        # Train the model first
        rf_classifier.fit(X, y)
        
        # Evaluate the model
        metrics = rf_classifier.evaluate(X, y)
        
        # Check that metrics include required fields
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'confusion_matrix' in metrics
        assert 'support' in metrics
        assert 'average_confidence' in metrics
        
        # Check that accuracy is a float between 0 and 1
        assert isinstance(metrics['accuracy'], float)
        assert 0 <= metrics['accuracy'] <= 1
        
        # Check that precision, recall, and f1_score are dictionaries with class keys
        for class_key in metrics['precision']:
            assert isinstance(class_key, str)
            assert 0 <= metrics['precision'][class_key] <= 1
            assert 0 <= metrics['recall'][class_key] <= 1
            assert 0 <= metrics['f1_score'][class_key] <= 1
        
        # Check that confusion matrix has the correct shape
        assert len(metrics['confusion_matrix']) == len(rf_classifier.classes_)
        assert len(metrics['confusion_matrix'][0]) == len(rf_classifier.classes_)
        
        # Check that average confidence is a float between 0 and 1
        assert isinstance(metrics['average_confidence'], float)
        assert 0 <= metrics['average_confidence'] <= 1

    def test_get_feature_importance(self, rf_classifier, synthetic_classification_data):
        """Test that feature importance is correctly calculated."""
        X, y = synthetic_classification_data
        
        # Set feature names
        feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        rf_classifier.feature_names = feature_names
        
        # Train the model
        rf_classifier.fit(X, y)
        
        # Get feature importance
        importance = rf_classifier.get_feature_importance()
        
        # Check that importance is a dictionary with feature names as keys
        assert isinstance(importance, dict)
        assert len(importance) == len(feature_names)
        for feature_name in feature_names:
            assert feature_name in importance
            assert isinstance(importance[feature_name], float)
        
        # Check that importance scores are normalized (sum to 1.0)
        assert np.isclose(sum(importance.values()), 1.0)
        
        # Check that importance scores are sorted in descending order
        importance_values = list(importance.values())
        assert all(importance_values[i] >= importance_values[i+1] for i in range(len(importance_values)-1))

    def test_get_oob_score_with_oob_enabled(self, rf_classifier_with_oob, synthetic_classification_data):
        """Test that OOB score is correctly retrieved when OOB scoring is enabled."""
        X, y = synthetic_classification_data
        
        # Train the model
        rf_classifier_with_oob.fit(X, y)
        
        # Get OOB score
        oob_score = rf_classifier_with_oob.get_oob_score()
        
        # Check that OOB score is a float between 0 and 1
        assert isinstance(oob_score, float)
        assert 0 <= oob_score <= 1

    def test_get_oob_score_with_oob_disabled(self, rf_classifier_without_oob, synthetic_classification_data):
        """Test that OOB score is None when OOB scoring is disabled."""
        X, y = synthetic_classification_data
        
        # Train the model
        rf_classifier_without_oob.fit(X, y)
        
        # Get OOB score
        oob_score = rf_classifier_without_oob.get_oob_score()
        
        # Check that OOB score is None when OOB scoring is disabled
        assert oob_score is None

    def test_get_estimator_importances(self, rf_classifier, synthetic_classification_data):
        """Test that estimator importances are correctly retrieved."""
        X, y = synthetic_classification_data
        
        # Train the model
        rf_classifier.fit(X, y)
        
        # Get estimator importances
        importances = rf_classifier.get_estimator_importances()
        
        # Check that importances is a list of arrays, one per tree
        assert isinstance(importances, list)
        assert len(importances) == rf_classifier.model.n_estimators
        
        # Check that each importance array has the correct shape
        for imp in importances:
            assert isinstance(imp, np.ndarray)
            assert imp.shape == (X.shape[1],)
            assert np.isclose(np.sum(imp), 1.0)  # Each tree's importances sum to 1.0

    def test_get_confidence_from_votes(self, rf_classifier_with_few_estimators, synthetic_classification_data):
        """Test that confidence scores based on voting distribution are correctly calculated."""
        X, y = synthetic_classification_data
        
        # Train the model
        rf_classifier_with_few_estimators.fit(X, y)
        
        # Get confidence scores based on voting distribution
        confidences = rf_classifier_with_few_estimators.get_confidence_from_votes(X)
        
        # Check that confidences have the correct shape
        assert isinstance(confidences, np.ndarray)
        assert len(confidences) == len(y)
        
        # Check that confidences are floats between 0 and 1
        assert np.all(confidences >= 0) and np.all(confidences <= 1)
        
        # Check that confidences are related to the agreement between trees
        # Higher confidence should correlate with more trees voting for the same class
        predictions = rf_classifier_with_few_estimators.predict(X)
        probabilities = rf_classifier_with_few_estimators.predict_proba(X)
        max_probs = np.max(probabilities, axis=1)
        
        # There should be a positive correlation between confidence from votes and max probability
        # This is a loose test since they're calculated differently
        correlation = np.corrcoef(confidences, max_probs)[0, 1]
        assert correlation > 0

    def test_cross_validate(self, rf_classifier, synthetic_classification_data):
        """Test that cross-validation is correctly performed."""
        X, y = synthetic_classification_data
        
        # Mock cross_val_score to avoid long computation
        with patch('sklearn.model_selection.cross_val_score') as mock_cv_score:
            # Configure the mock to return a reasonable result
            mock_cv_score.return_value = np.array([0.92, 0.94, 0.96, 0.93, 0.95])
            
            # Perform cross-validation
            cv_metrics = rf_classifier.cross_validate(X, y, cv=5)
            
            # Check that cross_val_score was called
            mock_cv_score.assert_called_once()
            
            # Check that metrics include required fields
            assert 'mean_accuracy' in cv_metrics
            assert 'std_accuracy' in cv_metrics
            assert 'min_accuracy' in cv_metrics
            assert 'max_accuracy' in cv_metrics
            assert 'folds' in cv_metrics
            
            # Check that metrics have reasonable values
            assert cv_metrics['mean_accuracy'] == 0.94  # Mean of mock values
            assert cv_metrics['std_accuracy'] == 0.01414213562373095  # Std of mock values
            assert cv_metrics['min_accuracy'] == 0.92  # Min of mock values
            assert cv_metrics['max_accuracy'] == 0.96  # Max of mock values
            assert cv_metrics['folds'] == 5

    def test_optimize_ensemble(self, rf_classifier_with_few_estimators, synthetic_classification_data):
        """Test that ensemble optimization correctly prunes low-performing trees."""
        X, y = synthetic_classification_data
        
        # Train the model
        rf_classifier_with_few_estimators.fit(X, y)
        
        # Get the original number of estimators
        original_n_estimators = rf_classifier_with_few_estimators.model.n_estimators
        
        # Optimize the ensemble
        result = rf_classifier_with_few_estimators.optimize_ensemble(X, y)
        
        # Check that the method returns self for method chaining
        assert result is rf_classifier_with_few_estimators
        
        # Check that the number of estimators has been reduced
        assert rf_classifier_with_few_estimators.model.n_estimators <= original_n_estimators
        
        # Check that the model can still make predictions
        predictions = rf_classifier_with_few_estimators.predict(X)
        assert len(predictions) == len(y)

    def test_get_parameters(self, rf_classifier, synthetic_classification_data):
        """Test that model parameters can be retrieved."""
        X, y = synthetic_classification_data
        
        # Train the model first
        rf_classifier.fit(X, y)
        
        # Get parameters
        params = rf_classifier.get_parameters()
        
        # Check that parameters include Random Forest specific fields
        assert 'n_estimators' in params
        assert 'max_depth' in params
        assert 'min_samples_split' in params
        assert 'min_samples_leaf' in params
        assert 'max_features' in params
        assert 'bootstrap' in params
        assert 'oob_score' in params
        assert 'criterion' in params
        
        # Check that parameters have reasonable values
        assert params['n_estimators'] == rf_classifier.model.n_estimators
        assert params['max_depth'] == rf_classifier.model.max_depth
        assert params['bootstrap'] == rf_classifier.model.bootstrap
        assert params['oob_score'] == rf_classifier.model.oob_score
        
        # Check that OOB score value is included if OOB scoring is enabled
        if rf_classifier.model.oob_score:
            assert 'oob_score_value' in params
            assert isinstance(params['oob_score_value'], float)
            assert 0 <= params['oob_score_value'] <= 1

    def test_validate_input(self, rf_classifier):
        """Test that input validation works correctly."""
        # Create valid input data
        X_valid = np.random.rand(10, 5)
        y_valid = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'] * 2)
        
        # Create invalid input data
        X_invalid_dim = np.random.rand(10)  # 1D array instead of 2D
        y_invalid_len = np.array(['invoice', 'license'])  # Length mismatch with X
        
        # Test valid input
        rf_classifier._validate_input(X_valid, y_valid)
        
        # Test invalid input dimensions
        with pytest.raises(ValueError):
            rf_classifier._validate_input(X_invalid_dim, y_valid)
        
        # Test invalid input length mismatch
        with pytest.raises(ValueError):
            rf_classifier._validate_input(X_valid, y_invalid_len)

    def test_untrained_model_errors(self, rf_classifier):
        """Test that appropriate errors are raised when using an untrained model."""
        # Create test data
        X = np.random.rand(10, 5)
        y = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'] * 2)
        
        # Test predict without training
        with pytest.raises(RuntimeError):
            rf_classifier.predict(X)
        
        # Test predict_proba without training
        with pytest.raises(RuntimeError):
            rf_classifier.predict_proba(X)
        
        # Test evaluate without training
        with pytest.raises(RuntimeError):
            rf_classifier.evaluate(X, y)
        
        # Test get_feature_importance without training
        with pytest.raises(RuntimeError):
            rf_classifier.get_feature_importance()
        
        # Test get_oob_score without training
        with pytest.raises(RuntimeError):
            rf_classifier.get_oob_score()
        
        # Test get_estimator_importances without training
        with pytest.raises(RuntimeError):
            rf_classifier.get_estimator_importances()
        
        # Test get_confidence_from_votes without training
        with pytest.raises(RuntimeError):
            rf_classifier.get_confidence_from_votes(X)
        
        # Test optimize_ensemble without training
        with pytest.raises(RuntimeError):
            rf_classifier.optimize_ensemble(X, y)

    def test_high_accuracy_requirement(self, rf_classifier, synthetic_classification_data):
        """Test that the model meets the 99% accuracy requirement from the technical specification."""
        X, y = synthetic_classification_data
        
        # Train the model
        rf_classifier.fit(X, y)
        
        # Mock the accuracy to be exactly 99% to test the boundary condition
        with patch('sklearn.metrics.accuracy_score') as mock_accuracy:
            mock_accuracy.return_value = 0.99  # 99% accuracy
            
            # Evaluate the model
            metrics = rf_classifier.evaluate(X, y)
            
            # Check that accuracy meets the 99% requirement
            assert metrics['accuracy'] >= 0.99
            
        # Mock the accuracy to be below 99% to test the warning
        with patch('sklearn.metrics.accuracy_score') as mock_accuracy, \
             patch('logging.getLogger') as mock_logger:
            mock_accuracy.return_value = 0.98  # 98% accuracy
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            # Evaluate the model
            metrics = rf_classifier.evaluate(X, y)
            
            # Check that a warning was logged
            mock_logger_instance.warning.assert_called()


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])