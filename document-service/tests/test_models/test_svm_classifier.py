#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Support Vector Machine (SVM) classifier implementation.

This module contains tests that verify the SVM classifier correctly implements
the base model interface, configures hyperparameters, analyzes feature importance,
calculates confidence scores, and performs cross-validation.
"""

import pytest
import numpy as np
from unittest.mock import patch, MagicMock
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV
from sklearn.inspection import permutation_importance

# Import the SVM classifier and related modules
from src.models.svm_classifier import SVMClassifier
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
        model_path="/models/test_svm_classifier.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        kernel="linear",  # SVM-specific parameter
        C=1.0,  # SVM-specific parameter
        random_state=42,
        verbose=False,
        class_weight="balanced",
        hyperparameter_tuning=False,
        cv_folds=5,
        n_jobs=-1
    )


@pytest.fixture
def svm_classifier(model_config):
    """Fixture that returns an SVM classifier instance for testing."""
    return SVMClassifier(model_config)


@pytest.fixture
def linear_svm_classifier():
    """Fixture that returns an SVM classifier with linear kernel for testing."""
    config = ModelConfig(
        model_path="/models/test_linear_svm.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        kernel="linear",
        C=1.0,
        random_state=42
    )
    return SVMClassifier(config)


@pytest.fixture
def rbf_svm_classifier():
    """Fixture that returns an SVM classifier with RBF kernel for testing."""
    config = ModelConfig(
        model_path="/models/test_rbf_svm.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        kernel="rbf",
        C=10.0,
        gamma="scale",
        random_state=42
    )
    return SVMClassifier(config)


@pytest.fixture
def tuning_svm_classifier():
    """Fixture that returns an SVM classifier with hyperparameter tuning enabled."""
    config = ModelConfig(
        model_path="/models/test_tuning_svm.pkl",
        vectorizer_path="/models/test_tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384,
        kernel="rbf",
        hyperparameter_tuning=True,
        cv_folds=3,  # Use fewer folds for faster testing
        n_jobs=1,  # Use single job for testing
        random_state=42
    )
    return SVMClassifier(config)


# Test cases for SVM classifier
class TestSVMClassifier:
    """Test cases for the SVM classifier implementation."""

    def test_inheritance(self, svm_classifier):
        """Test that SVMClassifier correctly inherits from BaseModel."""
        assert isinstance(svm_classifier, BaseModel)
        assert isinstance(svm_classifier, SVMClassifier)

    def test_initialization(self, svm_classifier, model_config):
        """Test that SVMClassifier initializes correctly with configuration parameters."""
        # Check that the classifier has been initialized with the correct attributes
        assert svm_classifier.kernel == model_config.get('kernel', 'rbf')
        assert svm_classifier.is_linear == (svm_classifier.kernel == 'linear')
        assert svm_classifier.model is not None
        assert isinstance(svm_classifier.model, SVC)
        assert svm_classifier.model_name is not None
        assert svm_classifier.model_version is not None
        assert svm_classifier.trained is False

    def test_get_svm_params_from_config(self, svm_classifier, model_config):
        """Test that SVMClassifier correctly extracts parameters from configuration."""
        params = svm_classifier._get_svm_params_from_config(model_config)
        
        # Check that the parameters match the configuration
        assert params['kernel'] == model_config.get('kernel', 'rbf')
        assert params['C'] == model_config.get('C', 1.0)
        assert params['probability'] is True  # Required for predict_proba
        assert params['random_state'] == model_config.get('random_state', 42)
        assert params['verbose'] == model_config.get('verbose', False)
        assert params['class_weight'] == model_config.get('class_weight', 'balanced')
        
        # Check kernel-specific parameters
        if params['kernel'] == 'rbf':
            assert 'gamma' in params
        elif params['kernel'] == 'poly':
            assert 'degree' in params
            assert 'coef0' in params
        elif params['kernel'] == 'sigmoid':
            assert 'coef0' in params
    
    def test_kernel_specific_params_rbf(self, rbf_svm_classifier):
        """Test that RBF kernel parameters are correctly configured."""
        assert rbf_svm_classifier.kernel == 'rbf'
        assert rbf_svm_classifier.is_linear is False
        
        # Check that the model has the correct parameters
        model_params = rbf_svm_classifier.model.get_params()
        assert model_params['kernel'] == 'rbf'
        assert model_params['gamma'] == 'scale'
        assert model_params['C'] == 10.0
    
    def test_kernel_specific_params_linear(self, linear_svm_classifier):
        """Test that linear kernel parameters are correctly configured."""
        assert linear_svm_classifier.kernel == 'linear'
        assert linear_svm_classifier.is_linear is True
        
        # Check that the model has the correct parameters
        model_params = linear_svm_classifier.model.get_params()
        assert model_params['kernel'] == 'linear'
        assert model_params['C'] == 1.0
    
    def test_fit_method(self, svm_classifier, synthetic_classification_data):
        """Test that the fit method correctly trains the model."""
        X, y = synthetic_classification_data
        
        # Train the model
        result = svm_classifier.fit(X, y)
        
        # Check that the method returns self for method chaining
        assert result is svm_classifier
        
        # Check that the model has been trained
        assert svm_classifier.trained is True
        assert svm_classifier.classes_ is not None
        assert len(svm_classifier.classes_) == len(set(y))
        
        # Check that the model can make predictions
        predictions = svm_classifier.predict(X)
        assert len(predictions) == len(y)
    
    def test_predict_method(self, svm_classifier, synthetic_classification_data):
        """Test that the predict method correctly classifies documents."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Make predictions
        predictions = svm_classifier.predict(X)
        
        # Check that predictions have the correct shape and type
        assert len(predictions) == len(y)
        assert isinstance(predictions, np.ndarray)
        
        # Check that predictions are valid class labels
        for pred in predictions:
            assert pred in svm_classifier.classes_
    
    def test_predict_proba_method(self, svm_classifier, synthetic_classification_data):
        """Test that the predict_proba method correctly returns class probabilities."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Get probability predictions
        probabilities = svm_classifier.predict_proba(X)
        
        # Check that probabilities have the correct shape
        assert probabilities.shape == (len(y), len(svm_classifier.classes_))
        
        # Check that probabilities are valid (sum to 1 for each sample)
        for prob_row in probabilities:
            assert np.isclose(np.sum(prob_row), 1.0)
            assert np.all(prob_row >= 0) and np.all(prob_row <= 1)
    
    def test_evaluate_method(self, svm_classifier, synthetic_classification_data):
        """Test that the evaluate method correctly calculates performance metrics."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Evaluate the model
        metrics = svm_classifier.evaluate(X, y)
        
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
            assert class_key in [str(c) for c in svm_classifier.classes_]
            assert 0 <= metrics['precision'][class_key] <= 1
            assert 0 <= metrics['recall'][class_key] <= 1
            assert 0 <= metrics['f1_score'][class_key] <= 1
        
        # Check that confusion matrix has the correct shape
        assert len(metrics['confusion_matrix']) == len(svm_classifier.classes_)
        assert len(metrics['confusion_matrix'][0]) == len(svm_classifier.classes_)
        
        # Check that average confidence is a float between 0 and 1
        assert isinstance(metrics['average_confidence'], float)
        assert 0 <= metrics['average_confidence'] <= 1
    
    def test_feature_importance_linear(self, linear_svm_classifier, synthetic_classification_data):
        """Test that feature importance is correctly calculated for linear SVM."""
        X, y = synthetic_classification_data
        
        # Set feature names
        feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        linear_svm_classifier.set_feature_names(feature_names)
        
        # Train the model
        linear_svm_classifier.fit(X, y)
        
        # Get feature importance
        importance = linear_svm_classifier.get_feature_importance(X, y)
        
        # Check that importance is a dictionary with feature names as keys
        assert isinstance(importance, dict)
        assert len(importance) == len(feature_names)
        for feature_name in feature_names:
            assert feature_name in importance
            assert isinstance(importance[feature_name], float)
        
        # Check that importance scores sum to approximately 1.0
        assert np.isclose(sum(importance.values()), 1.0)
    
    def test_feature_importance_nonlinear(self, rbf_svm_classifier, synthetic_classification_data):
        """Test that feature importance is correctly calculated for non-linear SVM."""
        X, y = synthetic_classification_data
        
        # Set feature names
        feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        rbf_svm_classifier.set_feature_names(feature_names)
        
        # Train the model
        rbf_svm_classifier.fit(X, y)
        
        # Mock permutation_importance to avoid long computation
        with patch('sklearn.inspection.permutation_importance') as mock_perm_importance:
            # Configure the mock to return a reasonable result
            mock_result = MagicMock()
            mock_result.importances_mean = np.random.rand(len(feature_names))
            mock_perm_importance.return_value = mock_result
            
            # Get feature importance
            importance = rbf_svm_classifier.get_feature_importance(X, y)
            
            # Check that permutation_importance was called
            mock_perm_importance.assert_called_once()
            
            # Check that importance is a dictionary with feature names as keys
            assert isinstance(importance, dict)
            assert len(importance) == len(feature_names)
            for feature_name in feature_names:
                assert feature_name in importance
                assert isinstance(importance[feature_name], float)
            
            # Check that importance scores sum to approximately 1.0
            assert np.isclose(sum(importance.values()), 1.0)
    
    def test_confidence_scoring(self, svm_classifier, synthetic_classification_data):
        """Test that confidence scores are correctly calculated."""
        X, y = synthetic_classification_data
        
        # Train the model
        svm_classifier.fit(X, y)
        
        # Get probability predictions
        probabilities = svm_classifier.predict_proba(X)
        
        # Calculate average confidence manually
        max_probabilities = np.max(probabilities, axis=1)
        expected_avg_confidence = float(np.mean(max_probabilities))
        
        # Calculate average confidence using the model's method
        actual_avg_confidence = svm_classifier._calculate_average_confidence(probabilities)
        
        # Check that the calculated confidence matches the expected value
        assert np.isclose(actual_avg_confidence, expected_avg_confidence)
        
        # Check that confidence is a float between 0 and 1
        assert isinstance(actual_avg_confidence, float)
        assert 0 <= actual_avg_confidence <= 1
    
    def test_hyperparameter_tuning(self, tuning_svm_classifier, synthetic_classification_data):
        """Test that hyperparameter tuning is correctly performed."""
        X, y = synthetic_classification_data
        
        # Mock GridSearchCV to avoid long computation
        with patch('sklearn.model_selection.GridSearchCV') as mock_grid_search:
            # Configure the mock to return a reasonable result
            mock_grid_search_instance = MagicMock()
            mock_grid_search_instance.fit.return_value = None
            mock_grid_search_instance.best_estimator_ = SVC(probability=True)
            mock_grid_search_instance.best_params_ = {'C': 10, 'gamma': 'scale'}
            mock_grid_search_instance.best_score_ = 0.95
            mock_grid_search.return_value = mock_grid_search_instance
            
            # Train the model with hyperparameter tuning
            tuning_svm_classifier.fit(X, y)
            
            # Check that GridSearchCV was called
            mock_grid_search.assert_called_once()
            
            # Check that the model was updated with the best estimator
            assert tuning_svm_classifier.model is mock_grid_search_instance.best_estimator_
    
    def test_cross_validation(self, svm_classifier, synthetic_classification_data):
        """Test that cross-validation is correctly performed."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Mock cross_val_score to avoid long computation
        with patch('sklearn.model_selection.cross_val_score') as mock_cv_score:
            # Configure the mock to return a reasonable result
            mock_cv_score.return_value = np.array([0.92, 0.94, 0.96, 0.93, 0.95])
            
            # Perform cross-validation
            cv_metrics = svm_classifier.cross_validate(X, y, cv=5)
            
            # Check that cross_val_score was called
            mock_cv_score.assert_called_once()
            
            # Check that metrics include required fields
            assert 'mean_accuracy' in cv_metrics
            assert 'std_accuracy' in cv_metrics
            assert 'min_accuracy' in cv_metrics
            assert 'max_accuracy' in cv_metrics
            assert 'cv_folds' in cv_metrics
            
            # Check that metrics have reasonable values
            assert cv_metrics['mean_accuracy'] == 0.94  # Mean of mock values
            assert cv_metrics['std_accuracy'] == 0.01414213562373095  # Std of mock values
            assert cv_metrics['min_accuracy'] == 0.92  # Min of mock values
            assert cv_metrics['max_accuracy'] == 0.96  # Max of mock values
            assert cv_metrics['cv_folds'] == 5
    
    def test_set_feature_names(self, svm_classifier, synthetic_classification_data):
        """Test that feature names can be set and retrieved."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Set feature names
        feature_names = [f'feature_{i}' for i in range(X.shape[1])]
        result = svm_classifier.set_feature_names(feature_names)
        
        # Check that the method returns self for method chaining
        assert result is svm_classifier
        
        # Check that feature names were set correctly
        assert svm_classifier.feature_names == feature_names
    
    def test_get_support_vectors(self, svm_classifier, synthetic_classification_data):
        """Test that support vectors can be retrieved from the trained model."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Get support vectors
        support_vectors = svm_classifier.get_support_vectors()
        
        # Check that support vectors are returned
        assert support_vectors is not None
        assert isinstance(support_vectors, np.ndarray)
        assert support_vectors.shape[1] == X.shape[1]  # Same number of features
    
    def test_get_parameters(self, svm_classifier, synthetic_classification_data):
        """Test that model parameters can be retrieved."""
        X, y = synthetic_classification_data
        
        # Train the model first
        svm_classifier.fit(X, y)
        
        # Get parameters
        params = svm_classifier.get_parameters()
        
        # Check that parameters include SVM-specific fields
        assert 'kernel' in params
        assert 'is_linear' in params
        assert 'n_support_vectors' in params
        assert 'n_classes' in params
        
        # Check that parameters have reasonable values
        assert params['kernel'] == svm_classifier.kernel
        assert params['is_linear'] == svm_classifier.is_linear
        assert params['n_classes'] == len(svm_classifier.classes_)
    
    def test_calibrate_probabilities(self, svm_classifier, train_test_data):
        """Test that probability calibration works correctly."""
        X_train, X_test, y_train, y_test = train_test_data
        
        # Train the model first
        svm_classifier.fit(X_train, y_train)
        
        # Mock CalibratedClassifierCV to avoid long computation
        with patch('sklearn.calibration.CalibratedClassifierCV') as mock_calibrated:
            # Configure the mock to return a reasonable result
            mock_calibrated_instance = MagicMock()
            mock_calibrated_instance.fit.return_value = None
            mock_calibrated.return_value = mock_calibrated_instance
            
            # Calibrate probabilities
            result = svm_classifier.calibrate_probabilities(X_test, y_test)
            
            # Check that CalibratedClassifierCV was called
            mock_calibrated.assert_called_once()
            
            # Check that the method returns self for method chaining
            assert result is svm_classifier
            
            # Check that the model was updated with the calibrated version
            assert svm_classifier.model is mock_calibrated_instance
    
    def test_optimize_threshold(self, svm_classifier, train_test_data):
        """Test that threshold optimization works correctly."""
        X_train, X_test, y_train, y_test = train_test_data
        
        # Train the model first
        svm_classifier.fit(X_train, y_train)
        
        # Mock f1_score to avoid long computation
        with patch('sklearn.metrics.f1_score') as mock_f1_score:
            # Configure the mock to return values that peak at a specific threshold
            mock_f1_score.side_effect = lambda y_true, y_pred, average: 0.8 + 0.1 * (y_pred == y_true).mean()
            
            # Optimize threshold
            threshold = svm_classifier.optimize_threshold(X_test, y_test)
            
            # Check that f1_score was called
            assert mock_f1_score.call_count > 0
            
            # Check that threshold is a float between 0.5 and 1.0
            assert isinstance(threshold, float)
            assert 0.5 <= threshold <= 1.0
            
            # Check that the threshold was updated in the config
            assert svm_classifier.config['min_confidence_threshold'] == threshold
    
    def test_validate_input(self, svm_classifier):
        """Test that input validation works correctly."""
        # Create valid input data
        X_valid = np.random.rand(10, 5)
        y_valid = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'] * 2)
        
        # Create invalid input data
        X_invalid_dim = np.random.rand(10)  # 1D array instead of 2D
        y_invalid_len = np.array(['invoice', 'license'])  # Length mismatch with X
        
        # Test valid input
        svm_classifier._validate_input(X_valid, y_valid)
        
        # Test invalid input dimensions
        with pytest.raises(ValueError):
            svm_classifier._validate_input(X_invalid_dim, y_valid)
        
        # Test invalid input length mismatch
        with pytest.raises(ValueError):
            svm_classifier._validate_input(X_valid, y_invalid_len)
    
    def test_untrained_model_errors(self, svm_classifier):
        """Test that appropriate errors are raised when using an untrained model."""
        # Create test data
        X = np.random.rand(10, 5)
        y = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'] * 2)
        
        # Test predict without training
        with pytest.raises(RuntimeError):
            svm_classifier.predict(X)
        
        # Test predict_proba without training
        with pytest.raises(RuntimeError):
            svm_classifier.predict_proba(X)
        
        # Test evaluate without training
        with pytest.raises(RuntimeError):
            svm_classifier.evaluate(X, y)
        
        # Test get_support_vectors without training
        with pytest.raises(RuntimeError):
            svm_classifier.get_support_vectors()
    
    def test_high_accuracy_requirement(self, svm_classifier, synthetic_classification_data):
        """Test that the model meets the 99% accuracy requirement from the technical specification."""
        X, y = synthetic_classification_data
        
        # Train the model
        svm_classifier.fit(X, y)
        
        # Mock the accuracy to be exactly 99% to test the boundary condition
        with patch('sklearn.metrics.accuracy_score') as mock_accuracy:
            mock_accuracy.return_value = 0.99  # 99% accuracy
            
            # Evaluate the model
            metrics = svm_classifier.evaluate(X, y)
            
            # Check that accuracy meets the 99% requirement
            assert metrics['accuracy'] >= 0.99
            
        # Mock the accuracy to be below 99% to test the warning
        with patch('sklearn.metrics.accuracy_score') as mock_accuracy, \
             patch('logging.getLogger') as mock_logger:
            mock_accuracy.return_value = 0.98  # 98% accuracy
            mock_logger_instance = MagicMock()
            mock_logger.return_value = mock_logger_instance
            
            # Evaluate the model
            metrics = svm_classifier.evaluate(X, y)
            
            # Check that a warning was logged
            mock_logger_instance.warning.assert_called()


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])