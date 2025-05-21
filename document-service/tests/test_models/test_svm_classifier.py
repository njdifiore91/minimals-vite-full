#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the SVM classifier implementation used for document classification.

This module contains tests that verify the Support Vector Machine (SVM) classifier
correctly implements the base model interface, configures hyperparameters,
analyzes feature importance, calculates confidence scores, and performs
cross-validation.
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score
from sklearn.model_selection import GridSearchCV
from sklearn.inspection import permutation_importance

# Import the SVM classifier implementation
from document_service.models.svm_classifier import SVMClassifier
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


class TestSVMClassifier:
    """Test suite for the SVM classifier implementation."""

    def test_init_with_default_params(self):
        """Test that the classifier initializes with default parameters."""
        # Create classifier with default parameters
        classifier = SVMClassifier()
        
        # Check that the model is initialized
        assert classifier.model is not None
        assert isinstance(classifier.model, SVC)
        
        # Check default parameters
        assert classifier.params['C'] == 1.0
        assert classifier.params['kernel'] == 'rbf'
        assert classifier.params['probability'] is True
        assert classifier.params['class_weight'] == 'balanced'
        assert classifier.params['random_state'] == 42
        
        # Check initial state
        assert classifier.is_fitted is False
        assert classifier.feature_names == []
        assert classifier.class_mapping == {}
        assert classifier.inverse_class_mapping == {}
        assert classifier.version == "1.0.0"
        assert classifier.last_trained is None

    def test_init_with_custom_params(self):
        """Test that the classifier initializes with custom parameters."""
        # Define custom parameters
        custom_params = {
            'C': 10.0,
            'kernel': 'linear',
            'gamma': 'auto',
            'probability': True,
            'class_weight': None,
            'random_state': 123
        }
        
        # Create classifier with custom parameters
        classifier = SVMClassifier(custom_params)
        
        # Check that the model is initialized with custom parameters
        assert classifier.model is not None
        assert isinstance(classifier.model, SVC)
        
        # Check custom parameters
        assert classifier.params['C'] == 10.0
        assert classifier.params['kernel'] == 'linear'
        assert classifier.params['gamma'] == 'auto'
        assert classifier.params['probability'] is True
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
        classifier = SVMClassifier()
        
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

    def test_fit_with_document_type_labels(self, document_features):
        """Test fitting the classifier with DocumentType labels."""
        # Get features and labels
        X, y_str = document_features
        
        # Convert string labels to DocumentType
        y = np.array([DocumentType(label) for label in y_str])
        
        # Create classifier
        classifier = SVMClassifier()
        
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
        classifier = SVMClassifier()
        
        # Test with mismatched X and y shapes
        X = np.random.random((10, 5))
        y = np.array([0, 1, 2])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.fit(X, y)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_predict_without_fit(self):
        """Test that predict raises ValueError if model is not fitted."""
        # Create classifier
        classifier = SVMClassifier()
        
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
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Predict
        predictions = classifier.predict(X)
        
        # Check predictions
        assert len(predictions) == len(X)
        assert all(isinstance(pred, DocumentType) for pred in predictions)

    def test_predict_proba_without_fit(self):
        """Test that predict_proba raises ValueError if model is not fitted."""
        # Create classifier
        classifier = SVMClassifier()
        
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
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Predict probabilities
        probas = classifier.predict_proba(X)
        
        # Check probabilities
        assert probas.shape == (len(X), len(set(y_str)))
        assert np.all(probas >= 0.0) and np.all(probas <= 1.0)
        assert np.allclose(np.sum(probas, axis=1), 1.0, rtol=1e-5)

    def test_predict_proba_with_probability_false(self, document_features):
        """Test that predict_proba raises ValueError if probability=False."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier with probability=False
        classifier = SVMClassifier({'probability': False})
        classifier.fit(X, y_str)
        
        # Test predict_proba with probability=False
        with pytest.raises(ValueError) as excinfo:
            classifier.predict_proba(X)
        
        assert "probability=False" in str(excinfo.value)

    def test_predict_with_confidence(self, document_features):
        """Test prediction with confidence scores."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
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
        classifier = SVMClassifier()
        
        # Test predict_with_confidence without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.predict_with_confidence(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_predict_with_confidence_probability_false(self, document_features):
        """Test prediction with confidence when probability=False."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier with probability=False
        classifier = SVMClassifier({'probability': False})
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

    def test_get_feature_importance_without_fit(self):
        """Test that get_feature_importance raises ValueError if model is not fitted."""
        # Create classifier
        classifier = SVMClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_feature_importance()
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_feature_importance(self, document_features):
        """Test feature importance retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Get feature importance
        importance = classifier.get_feature_importance()
        
        # For SVM without explicit calculation, this should return an empty dict
        assert isinstance(importance, dict)

    def test_calculate_feature_importance(self, document_features):
        """Test feature importance calculation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Calculate feature importance
        importance = classifier.calculate_feature_importance(X, y_str, n_repeats=2)
        
        # Check importance
        assert isinstance(importance, dict)
        assert len(importance) == len(feature_names)
        assert all(name in importance for name in feature_names)
        assert all(isinstance(score, float) for score in importance.values())

    def test_calculate_feature_importance_without_fit(self, document_features):
        """Test that calculate_feature_importance raises ValueError if model is not fitted."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier without fitting
        classifier = SVMClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.calculate_feature_importance(X, y_str)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_calculate_feature_importance_with_invalid_data(self, document_features):
        """Test that calculate_feature_importance raises ValueError with invalid data."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Test with mismatched X and y shapes
        X_invalid = np.random.random((10, X.shape[1]))
        y_invalid = np.array([y_str[0], y_str[1], y_str[2]])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.calculate_feature_importance(X_invalid, y_invalid)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_get_decision_function(self, document_features):
        """Test decision function retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Get decision function values
        decision_values = classifier.get_decision_function(X)
        
        # Check decision values
        n_classes = len(set(y_str))
        expected_shape = (len(X), n_classes) if n_classes > 2 else (len(X),)
        assert decision_values.shape == expected_shape or decision_values.shape[0] == len(X)

    def test_get_decision_function_without_fit(self):
        """Test that get_decision_function raises ValueError if model is not fitted."""
        # Create classifier
        classifier = SVMClassifier()
        
        # Test get_decision_function without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_decision_function(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_support_vectors(self, document_features):
        """Test support vector retrieval."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Get support vectors
        support_vectors, support_indices = classifier.get_support_vectors()
        
        # Check support vectors
        assert isinstance(support_vectors, np.ndarray)
        assert support_vectors.shape[1] == X.shape[1]  # Same number of features
        assert isinstance(support_indices, list)
        assert all(isinstance(idx, int) for idx in support_indices)
        assert all(0 <= idx < len(X) for idx in support_indices)

    def test_get_support_vectors_without_fit(self):
        """Test that get_support_vectors raises ValueError if model is not fitted."""
        # Create classifier
        classifier = SVMClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_support_vectors()
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_kernel_matrix(self, document_features):
        """Test kernel matrix calculation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Get kernel matrix
        K = classifier.get_kernel_matrix(X)
        
        # Check kernel matrix
        assert isinstance(K, np.ndarray)
        assert K.shape == (len(X), len(X))  # Square matrix with size n_samples
        assert np.all(np.diag(K) > 0)  # Diagonal elements should be positive

    def test_get_kernel_matrix_without_fit(self):
        """Test that get_kernel_matrix raises ValueError if model is not fitted."""
        # Create classifier
        classifier = SVMClassifier()
        
        # Test get_kernel_matrix without fitting
        X = np.random.random((5, 10))
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_kernel_matrix(X)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_optimize_hyperparameters(self, document_features):
        """Test hyperparameter optimization."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = SVMClassifier()
        
        # Define a small parameter grid for testing
        param_grid = {
            'C': [0.1, 1.0],
            'kernel': ['linear', 'rbf'],
            'gamma': ['scale', 'auto']
        }
        
        # Optimize hyperparameters with grid search
        result = classifier.optimize_hyperparameters(
            X, y_str, param_grid=param_grid, cv=2, method='grid'
        )
        
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

    def test_optimize_hyperparameters_random_search(self, document_features):
        """Test hyperparameter optimization with random search."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = SVMClassifier()
        
        # Define a small parameter grid for testing
        param_grid = {
            'C': [0.1, 1.0, 10.0],
            'kernel': ['linear', 'rbf'],
            'gamma': ['scale', 'auto']
        }
        
        # Optimize hyperparameters with random search
        result = classifier.optimize_hyperparameters(
            X, y_str, param_grid=param_grid, cv=2, n_iter=2, method='random'
        )
        
        # Check result
        assert isinstance(result, dict)
        assert 'best_params' in result
        assert 'best_score' in result
        assert 'cv_results' in result
        assert 'elapsed_time' in result

    def test_optimize_hyperparameters_invalid_method(self, document_features):
        """Test that optimize_hyperparameters raises ValueError with invalid method."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = SVMClassifier()
        
        # Test with invalid method
        with pytest.raises(ValueError) as excinfo:
            classifier.optimize_hyperparameters(X, y_str, method='invalid')
        
        assert "Unknown search method" in str(excinfo.value)

    def test_optimize_hyperparameters_invalid_data(self):
        """Test that optimize_hyperparameters raises ValueError with invalid data."""
        # Create classifier
        classifier = SVMClassifier()
        
        # Test with mismatched X and y shapes
        X = np.random.random((10, 5))
        y = np.array([0, 1, 2])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.optimize_hyperparameters(X, y)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_evaluate(self, document_features):
        """Test model evaluation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
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
        classifier = SVMClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.evaluate(X, y_str)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_evaluate_with_invalid_data(self, document_features):
        """Test that evaluate raises ValueError with invalid data."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Test with mismatched X and y shapes
        X_invalid = np.random.random((10, X.shape[1]))
        y_invalid = np.array([y_str[0], y_str[1], y_str[2]])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.evaluate(X_invalid, y_invalid)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_cross_validate(self, document_features):
        """Test cross-validation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = SVMClassifier()
        
        # Perform cross-validation
        results = classifier.cross_validate(X, y_str, cv=2)
        
        # Check results
        assert isinstance(results, dict)
        assert 'test_score' in results
        assert 'train_score' in results
        assert 'fit_time' in results
        assert 'score_time' in results
        assert len(results['test_score']) == 2  # 2-fold CV
        assert all(0.0 <= score <= 1.0 for score in results['test_score'])
        assert all(0.0 <= score <= 1.0 for score in results['train_score'])

    def test_cross_validate_with_invalid_data(self):
        """Test that cross_validate raises ValueError with invalid data."""
        # Create classifier
        classifier = SVMClassifier()
        
        # Test with mismatched X and y shapes
        X = np.random.random((10, 5))
        y = np.array([0, 1, 2])  # Only 3 labels for 10 samples
        
        with pytest.raises(ValueError) as excinfo:
            classifier.cross_validate(X, y)
        
        assert "Number of samples in X" in str(excinfo.value)

    def test_set_feature_names(self, document_features):
        """Test setting feature names."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier
        classifier = SVMClassifier()
        
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
        classifier = SVMClassifier()
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
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Get model info
        info = classifier.get_model_info()
        
        # Check info
        assert isinstance(info, dict)
        assert info['model_type'] == 'svm'
        assert info['version'] == '1.0.0'
        assert info['is_fitted'] is True
        assert info['feature_count'] == len(feature_names)
        assert info['class_count'] == len(set(y_str))
        assert 'last_trained' in info
        assert 'training_accuracy' in info
        assert 'n_support' in info
        assert 'n_features' in info
        assert 'n_classes' in info

    def test_get_model_info_without_fit(self):
        """Test model info retrieval without fitting."""
        # Create classifier
        classifier = SVMClassifier()
        
        # Get model info
        info = classifier.get_model_info()
        
        # Check info
        assert isinstance(info, dict)
        assert info['model_type'] == 'svm'
        assert info['version'] == '1.0.0'
        assert info['is_fitted'] is False
        assert info['feature_count'] is None
        assert info['class_count'] is None
        assert 'last_trained' not in info
        assert 'training_accuracy' not in info

    def test_get_confidence_calibration(self, document_features):
        """Test confidence calibration calculation."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
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
        classifier = SVMClassifier()
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_confidence_calibration(X, y_str)
        
        assert "Model has not been trained" in str(excinfo.value)

    def test_get_confidence_calibration_with_probability_false(self, document_features):
        """Test that get_confidence_calibration raises ValueError if probability=False."""
        # Get features and labels
        X, y_str = document_features
        
        # Create classifier with probability=False
        classifier = SVMClassifier({'probability': False})
        classifier.fit(X, y_str)
        
        with pytest.raises(ValueError) as excinfo:
            classifier.get_confidence_calibration(X, y_str)
        
        assert "probability=False" in str(excinfo.value)

    def test_get_confidence_calibration_with_invalid_data(self, document_features):
        """Test that get_confidence_calibration raises ValueError with invalid data."""
        # Get features and labels
        X, y_str = document_features
        
        # Create and fit classifier
        classifier = SVMClassifier()
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
        classifier = SVMClassifier()
        classifier.fit(X, y_str)
        
        # Set feature names
        feature_names = [f"feature_{i}" for i in range(X.shape[1])]
        classifier.set_feature_names(feature_names)
        
        # Save the model
        model_path = os.path.join(tmp_path, "svm_model.joblib")
        save_result = classifier.save(model_path)
        
        # Check save result
        assert save_result.is_success()
        assert os.path.exists(model_path)
        
        # Load the model
        load_result = SVMClassifier.load(model_path)
        
        # Check load result
        assert load_result.is_success()
        loaded_classifier = load_result.value
        
        # Check loaded classifier
        assert isinstance(loaded_classifier, SVMClassifier)
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
        classifier = SVMClassifier()
        
        # Save the model
        model_path = os.path.join(tmp_path, "svm_model.joblib")
        save_result = classifier.save(model_path)
        
        # Check save result
        assert not save_result.is_success()
        assert isinstance(save_result.error, ServiceError)
        assert save_result.error.category == ErrorCategory.STORAGE_ERROR

    def test_load_invalid_path(self):
        """Test that load returns a failure result with invalid path."""
        # Load from invalid path
        load_result = SVMClassifier.load("/invalid/path/model.joblib")
        
        # Check load result
        assert not load_result.is_success()
        assert isinstance(load_result.error, ServiceError)
        assert load_result.error.category == ErrorCategory.STORAGE_ERROR


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])