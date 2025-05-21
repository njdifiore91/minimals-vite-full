#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Random Forest classifier implementation used for document classification.

This module contains tests that verify the Random Forest classifier correctly implements
the base model interface, configures hyperparameters, ranks feature importance,
calculates confidence scores, and optimizes ensemble performance.
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from sklearn.ensemble import RandomForestClassifier as SklearnRF
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

# Import the Random Forest classifier implementation
from document_service.models.random_forest_classifier import RandomForestClassifier
from document_service.types.classification import (
    ClassificationModel,
    ConfidenceScore,
    DocumentType,
    FeatureVector,
    ModelParameters,
    ClassificationResult,
    ClassificationMetrics
)
from document_service.types.errors import Result, ServiceError, ErrorCategory


class TestRandomForestClassifier:
    """Test suite for the Random Forest classifier implementation."""

    def test_init_with_default_params(self):
        """Test that the classifier initializes with default parameters."""
        # Create classifier with default parameters
        classifier = RandomForestClassifier()
        
        # Check that the model is initialized
        assert classifier.model is not None
        assert isinstance(classifier.model, SklearnRF)
        
        # Check default parameters
        assert classifier.params['n_estimators'] == 100
        assert classifier.params['max_depth'] is None
        assert classifier.params['min_samples_split'] == 2
        assert classifier.params['min_samples_leaf'] == 1
        assert classifier.params['max_features'] == 'sqrt'
        assert classifier.params['bootstrap'] is True
        assert classifier.params['oob_score'] is True
        assert classifier.params['class_weight'] == 'balanced'
        assert classifier.params['random_state'] == 42
        
        # Check initial state
        assert classifier.is_fitted is False
        assert classifier.feature_names == []
        assert classifier.class_mapping == {}
        assert classifier.inverse_class_mapping == {}
        assert classifier.version == "1.0.0"
        assert classifier.last_trained is None
        assert classifier.feature_importances_ is None
        assert classifier.oob_score_ is None
        assert classifier.training_accuracy is None

    def test_init_with_custom_params(self):
        """Test that the classifier initializes with custom parameters."""
        # Define custom parameters
        custom_params = {
            'n_estimators': 200,
            'max_depth': 10,
            'min_samples_split': 5,
            'min_samples_leaf': 2,
            'max_features': 'log2',
            'bootstrap': True,
            'oob_score': False,
            'class_weight': None,
            'random_state': 123
        }
        
        # Create classifier with custom parameters
        classifier = RandomForestClassifier(custom_params)
        
        # Check that the model is initialized with custom parameters
        assert classifier.model is not None
        assert isinstance(classifier.model, SklearnRF)
        
        # Check custom parameters
        assert classifier.params['n_estimators'] == 200
        assert classifier.params['max_depth'] == 10
        assert classifier.params['min_samples_split'] == 5
        assert classifier.params['min_samples_leaf'] == 2
        assert classifier.params['max_features'] == 'log2'
        assert classifier.params['bootstrap'] is True
        assert classifier.params['oob_score'] is False
        assert classifier.params['class_weight'] is None
        assert classifier.params['random_state'] == 123

    def test_fit_with_numeric_labels(self, document_features):
        """Test fitting the classifier with numeric labels."""
        # Get features and labels
        X, y_str = document_features
        
        # Convert string labels to numeric
        unique_labels = list(set(y_str))
        label_map = {label: i for i, label in enumerate(unique_labels)}
        y = np.array([label_map[label] for label in y_str])
        
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Fit the classifier
        result = classifier.fit(X, y)
        
        # Check that fit returns self for method chaining
        assert result is classifier
        
        # Check that the model is fitted
        assert classifier.is_fitted is True
        assert classifier.last_trained is not None
        
        # Check class mapping
        assert len(classifier.class_mapping) == len(unique_labels)
        assert all(isinstance(key, int) for key in classifier.class_mapping.keys())
        assert all(isinstance(val, DocumentType) for val in classifier.class_mapping.values())
        
        # Check inverse class mapping
        assert len(classifier.inverse_class_mapping) == len(unique_labels)
        assert all(isinstance(key, DocumentType) for key in classifier.inverse_class_mapping.keys())
        assert all(isinstance(val, int) for val in classifier.inverse_class_mapping.values())
        
        # Check training accuracy
        assert 0.0 <= classifier.training_accuracy <= 1.0
        
        # Check feature importances
        assert classifier.feature_importances_ is not None
        assert len(classifier.feature_importances_) == X.shape[1]
        
        # Check OOB score if enabled
        if classifier.params.get("oob_score", False):
            assert classifier.oob_score_ is not None
            assert 0.0 <= classifier.oob_score_ <= 1.0

    def test_fit_with_document_type_labels(self, document_features):
        """Test fitting the classifier with DocumentType labels."""
        # Get features and labels
        X, y_str = document_features
        
        # Convert string labels to DocumentType
        y = np.array([DocumentType(label) for label in y_str])
        
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Fit the classifier
        classifier.fit(X, y)
        
        # Check that the model is fitted
        assert classifier.is_fitted is True
        
        # Check class mapping
        assert len(classifier.class_mapping) == len(set(y_str))
        assert all(isinstance(key, int) for key in classifier.class_mapping.keys())
        assert all(isinstance(val, DocumentType) for val in classifier.class_mapping.values())
        
        # Check inverse class mapping
        assert len(classifier.inverse_class_mapping) == len(set(y_str))
        assert all(isinstance(key, DocumentType) for key in classifier.inverse_class_mapping.keys())
        assert all(isinstance(val, int) for val in classifier.inverse_class_mapping.values())

    def test_fit_with_invalid_data(self):
        """Test that fit raises ValueError with invalid data."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test with mismatched X and y shapes
        X = np.random.random((10, 5))
        y = np.array([0, 1, 2])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.fit(X, y)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_predict_without_fit(self):
        """Test that predict raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test predict without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.predict(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_predict(self, document_features):
        """Test prediction with fitted model."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Predict
        predictions = classifier.predict(X)
        
        # Check predictions
        assert len(predictions) == len(X)
        assert all(isinstance(pred, DocumentType) for pred in predictions)

    def test_predict_proba_without_fit(self):
        """Test that predict_proba raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test predict_proba without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.predict_proba(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_predict_proba(self, document_features):
        """Test probability prediction with fitted model."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Predict probabilities
        probas = classifier.predict_proba(X)
        
        # Check probabilities
        assert probas.shape == (len(X), len(set(y_str)))
        assert np.all(probas >= 0.0) and np.all(probas <= 1.0)
        assert np.allclose(np.sum(probas, axis=1), 1.0, rtol=1e-5)

    def test_predict_with_confidence(self, document_features):
        """Test prediction with confidence scores."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Predict with confidence
        results = classifier.predict_with_confidence(X)
        
        # Check results
        assert len(results) == len(X)
        assert all(isinstance(result, tuple) for result in results)
        assert all(len(result) == 2 for result in results)
        assert all(isinstance(result[0], DocumentType) for result in results)
        assert all(isinstance(result[1], float) for result in results)
        assert all(0.0 <= result[1] <= 1.0 for result in results)

    def test_predict_with_confidence_without_fit(self):
        """Test that predict_with_confidence raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test predict_with_confidence without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.predict_with_confidence(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_feature_importance_without_fit(self):
        """Test that get_feature_importance raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_feature_importance()
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_feature_importance(self, document_features):
        """Test feature importance retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Get feature importance
        importance = classifier.get_feature_importance()
        
        # Check importance
        assert isinstance(importance, dict)
        assert len(importance) == X.shape[1]
        assert all(isinstance(score, float) for score in importance.values())
        assert sum(importance.values()) > 0.99  # Sum should be approximately 1.0
        
        # Check that importance is sorted in descending order
        importance_values = list(importance.values())
        assert all(importance_values[i] >= importance_values[i+1] for i in range(len(importance_values)-1))

    def test_get_feature_importance_with_feature_names(self, document_features):
        """Test feature importance retrieval with feature names."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Get feature importance
        importance = classifier.get_feature_importance()
        
        # Check importance
        assert isinstance(importance, dict)
        assert len(importance) == len(feature_names)
        assert all(name in importance for name in feature_names)
        assert all(isinstance(score, float) for score in importance.values())

    def test_get_tree_decisions_without_fit(self):
        """Test that get_tree_decisions raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test get_tree_decisions without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_tree_decisions(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_tree_decisions(self, document_features):
        """Test tree decisions retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier with a small number of trees for testing
        classifier = RandomForestClassifier({'n_estimators': 10})
        classifier.fit(X, y_str)
        
        # Get tree decisions for a subset of samples
        X_subset = X[:3]  # Use first 3 samples for testing
        tree_decisions = classifier.get_tree_decisions(X_subset)
        
        # Check tree decisions
        assert isinstance(tree_decisions, dict)
        assert len(tree_decisions) == len(X_subset)
        assert all(f"sample_{i}" in tree_decisions for i in range(len(X_subset)))
        assert all(len(decisions) == 10 for decisions in tree_decisions.values())  # 10 trees
        assert all(isinstance(decision, int) for decisions in tree_decisions.values() for decision in decisions)

    def test_get_voting_distribution_without_fit(self):
        """Test that get_voting_distribution raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test get_voting_distribution without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_voting_distribution(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_voting_distribution(self, document_features):
        """Test voting distribution retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier with a small number of trees for testing
        classifier = RandomForestClassifier({'n_estimators': 10})
        classifier.fit(X, y_str)
        
        # Get voting distribution for a subset of samples
        X_subset = X[:3]  # Use first 3 samples for testing
        voting_distribution = classifier.get_voting_distribution(X_subset)
        
        # Check voting distribution
        assert isinstance(voting_distribution, dict)
        assert len(voting_distribution) == len(X_subset)
        assert all(f"sample_{i}" in voting_distribution for i in range(len(X_subset)))
        
        # Check that vote counts sum to number of trees
        for sample_votes in voting_distribution.values():
            assert sum(sample_votes.values()) == 10  # 10 trees

    def test_get_oob_error_without_fit(self):
        """Test that get_oob_error returns None if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Get OOB error without fitting
        oob_error = classifier.get_oob_error()
        
        # Check that OOB error is None
        assert oob_error is None

    def test_get_oob_error_with_oob_score_disabled(self, document_features):
        """Test that get_oob_error returns None if oob_score is disabled."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier with oob_score disabled
        classifier = RandomForestClassifier({'oob_score': False})
        classifier.fit(X, y_str)
        
        # Get OOB error
        oob_error = classifier.get_oob_error()
        
        # Check that OOB error is None
        assert oob_error is None

    def test_get_oob_error(self, document_features):
        """Test OOB error retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier with oob_score enabled
        classifier = RandomForestClassifier({'oob_score': True})
        classifier.fit(X, y_str)
        
        # Get OOB error
        oob_error = classifier.get_oob_error()
        
        # Check OOB error
        assert oob_error is not None
        assert 0.0 <= oob_error <= 1.0
        assert oob_error == 1.0 - classifier.oob_score_

    def test_optimize_ensemble_without_fit(self, document_features):
        """Test ensemble optimization without prior fitting."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier without fitting
        classifier = RandomForestClassifier()
        
        # Define a small parameter grid for testing
        param_grid = {
            'n_estimators': [50, 100],
            'max_depth': [None, 10],
            'min_samples_split': [2, 5]
        }
        
        # Optimize ensemble
        result = classifier.optimize_ensemble(X, y_str, param_grid=param_grid, cv=2, method='grid')
        
        # Check result
        assert isinstance(result, dict)
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'cv_results' in result
        assert 'elapsed_time' in result
        
        # Check that best parameters were applied
        for param, value in result['best_params'].items():
            assert classifier.params[param] == value
        
        # Check that the model was fitted
        assert classifier.is_fitted is True

    def test_optimize_ensemble_with_random_search(self, document_features):
        """Test ensemble optimization with random search."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Define a small parameter grid for testing
        param_grid = {
            'n_estimators': [50, 100, 200],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4]
        }
        
        # Optimize ensemble with random search
        result = classifier.optimize_ensemble(
            X, y_str, param_grid=param_grid, cv=2, n_iter=2, method='random'
        )
        
        # Check result
        assert isinstance(result, dict)
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'cv_results' in result
        assert 'elapsed_time' in result

    def test_optimize_ensemble_invalid_method(self, document_features):
        """Test that optimize_ensemble raises ValueError with invalid method."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test with invalid method
        with pytest.raises(ValueError) as excinfo:
            classifier.optimize_ensemble(X, y_str, method='invalid')
        
        assert "Unknown search method" in str(excinfo.value)

    def test_optimize_ensemble_invalid_data(self):
        """Test that optimize_ensemble raises ValueError with invalid data."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Test with mismatched X and y shapes
        X = np.random.random((10, 5))
        y = np.array([0, 1, 2])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.optimize_ensemble(X, y)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_evaluate(self, document_features):
        """Test model evaluation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Evaluate the model
        metrics = classifier.evaluate(X, y_str)
        
        # Check metrics
        assert isinstance(metrics, ClassificationMetrics)
        assert 0.0 <= metrics.accuracy <= 1.0
        assert isinstance(metrics.precision, dict)
        assert isinstance(metrics.recall, dict)
        assert isinstance(metrics.f1_score, dict)
        assert metrics.confusion_matrix is not None
        assert metrics.confusion_matrix.shape == (len(set(y_str)), len(set(y_str)))

    def test_evaluate_without_fit(self, document_features):
        """Test that evaluate raises ValueError if model is not fitted."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier without fitting
        classifier = RandomForestClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.evaluate(X, y_str)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_evaluate_with_invalid_data(self, document_features):
        """Test that evaluate raises ValueError with invalid data."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Test with mismatched X and y shapes
        X_invalid = np.random.random((10, X.shape[1]))
        y_invalid = np.array([y_str[0], y_str[1], y_str[2]])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.evaluate(X_invalid, y_invalid)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_set_feature_names(self, document_features):
        """Test setting feature names."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Check feature names
        assert classifier.feature_names == feature_names

    def test_set_feature_names_with_wrong_length(self, document_features):
        """Test that set_feature_names raises ValueError with wrong length."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Test with wrong number of feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1] + 5)]  # Too many names
        
        with pytest.raises(ValueError) as excinfo:
            classifier.set_feature_names(feature_names)
        
        assert "Number of feature names" in str(excinfo.value)

    def test_get_model_info(self, document_features):
        """Test model info retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Get model info
        info = classifier.get_model_info()
        
        # Check info
        assert isinstance(info, dict)
        assert info['model_type'] == 'random_forest'
        assert info['version'] == '1.0.0'
        assert info['is_fitted'] is True
        assert info['feature_count'] == len(feature_names)
        assert info['class_count'] == len(set(y_str))
        assert 'last_trained' in info
        assert 'training_accuracy' in info
        assert 'oob_score' in info
        assert 'oob_error' in info
        assert 'n_estimators' in info
        assert 'n_features' in info
        assert 'n_classes' in info

    def test_get_model_info_without_fit(self):
        """Test model info retrieval without fitting."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        # Get model info
        info = classifier.get_model_info()
        
        # Check info
        assert isinstance(info, dict)
        assert info['model_type'] == 'random_forest'
        assert info['version'] == '1.0.0'
        assert info['is_fitted'] is False
        assert info['feature_count'] is None
        assert info['class_count'] is None
        assert 'last_trained' not in info
        assert 'training_accuracy' not in info
        assert 'oob_score' not in info

    def test_get_ensemble_diversity(self, document_features):
        """Test ensemble diversity calculation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier with oob_score enabled
        classifier = RandomForestClassifier({'oob_score': True})
        classifier.fit(X, y_str)
        
        # Get ensemble diversity
        diversity = classifier.get_ensemble_diversity()
        
        # Check diversity metrics
        assert isinstance(diversity, dict)
        assert 'average_disagreement' in diversity
        assert 'average_agreement' in diversity
        assert 'entropy_diversity' in diversity
        assert 'n_trees' in diversity
        assert diversity['n_trees'] == classifier.params['n_estimators']
        assert 0.0 <= diversity['average_disagreement'] <= 1.0
        assert 0.0 <= diversity['average_agreement'] <= 1.0
        assert 0.0 <= diversity['entropy_diversity'] <= 1.0

    def test_get_ensemble_diversity_without_fit(self):
        """Test that get_ensemble_diversity raises ValueError if model is not fitted."""
        # Create classifier
        classifier = RandomForestClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_ensemble_diversity()
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_confidence_calibration(self, document_features):
        """Test confidence calibration calculation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Get confidence calibration
        calibration = classifier.get_confidence_calibration(X, y_str)
        
        # Check calibration
        assert isinstance(calibration, dict)
        assert 'bin_edges' in calibration
        assert 'bin_accuracies' in calibration
        assert 'bin_confidences' in calibration
        assert 'bin_counts' in calibration
        assert 'expected_calibration_error' in calibration
        assert len(calibration['bin_edges']) == 11  # 10 bins + 1
        assert len(calibration['bin_accuracies']) == 10  # 10 bins
        assert len(calibration['bin_confidences']) == 10  # 10 bins
        assert len(calibration['bin_counts']) == 10  # 10 bins
        assert 0.0 <= calibration['expected_calibration_error'] <= 1.0

    def test_get_confidence_calibration_without_fit(self, document_features):
        """Test that get_confidence_calibration raises ValueError if model is not fitted."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier without fitting
        classifier = RandomForestClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_confidence_calibration(X, y_str)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_confidence_calibration_with_invalid_data(self, document_features):
        """Test that get_confidence_calibration raises ValueError with invalid data."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Test with mismatched X and y shapes
        X_invalid = np.random.random((10, X.shape[1]))
        y_invalid = np.array([y_str[0], y_str[1], y_str[2]])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_confidence_calibration(X_invalid, y_invalid)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_save_and_load(self, document_features, tmp_path):
        """Test model serialization and deserialization."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = RandomForestClassifier()
        classifier.fit(X, y_str)
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Save the model
        model_path = os.path.join(tmp_path, "rf_model.joblib")
        save_result = classifier.save(model_path)
        
        # Check save result
        assert save_result.is_success()
        assert os.path.exists(model_path)
        
        # Load the model
        load_result = RandomForestClassifier.load(model_path)
        
        # Check load result
        assert load_result.is_success()
        loaded_classifier = load_result.value
        
        # Check loaded classifier
        assert isinstance(loaded_classifier, RandomForestClassifier)
        assert loaded_classifier.is_fitted is True
        assert loaded_classifier.feature_names == feature_names
        assert loaded_classifier.version == classifier.version
        assert len(loaded_classifier.class_mapping) == len(classifier.class_mapping)
        
        # Check that loaded model makes the same predictions
        original_preds = classifier.predict(X)
        loaded_preds = loaded_classifier.predict(X)
        assert np.array_equal(original_preds, loaded_preds)

    def test_save_without_fit(self, tmp_path):
        """Test that save returns a failure result if model is not fitted."""
        # Create classifier without fitting
        classifier = RandomForestClassifier()
        
        # Save the model
        model_path = os.path.join(tmp_path, "rf_model.joblib")
        save_result = classifier.save(model_path)
        
        # Check save result
        assert not save_result.is_success()
        assert isinstance(save_result.error, ServiceError)
        assert save_result.error.category == ErrorCategory.STORAGE_ERROR

    def test_load_invalid_path(self):
        """Test that load returns a failure result with invalid path."""
        # Load from invalid path
        load_result = RandomForestClassifier.load("/invalid/path/model.joblib")
        
        # Check load result
        assert not load_result.is_success()
        assert isinstance(load_result.error, ServiceError)
        assert load_result.error.category == ErrorCategory.STORAGE_ERROR


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])