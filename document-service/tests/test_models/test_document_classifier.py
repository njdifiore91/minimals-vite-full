#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the DocumentClassifier class.

This module contains comprehensive tests for the DocumentClassifier class that
orchestrates the document classification process in the Document Service.

Tests verify that the classifier correctly combines feature extraction, model selection,
prediction, and confidence scoring. Includes tests for ensemble methods, document type
routing logic, and classification performance monitoring.
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Import the DocumentClassifier class and related types
from src.models.document_classifier import DocumentClassifier
from src.models.svm_classifier import SVMClassifier
from src.models.random_forest_classifier import RandomForestClassifier
from src.types.classification import ClassificationResult, ConfidenceScore
from src.types.documents import DocumentType
from src.types.config import ModelConfig
from src.types.errors import Result


# Test DocumentClassifier initialization
class TestDocumentClassifierInitialization:
    """Tests for DocumentClassifier initialization with different configurations."""
    
    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        # Create a minimal configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Verify initialization
        assert classifier is not None
        assert classifier.config == config
        assert classifier.svm_classifier is not None
        assert classifier.rf_classifier is not None
        assert classifier.ensemble_weights['svm'] == 0.5
        assert classifier.ensemble_weights['random_forest'] == 0.5
        assert classifier.trained is False
    
    def test_init_with_custom_weights(self):
        """Test initialization with custom ensemble weights."""
        # Create configuration with custom weights
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'svm_weight': 0.7,
            'rf_weight': 0.3
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Verify custom weights
        assert classifier.ensemble_weights['svm'] == 0.7
        assert classifier.ensemble_weights['random_forest'] == 0.3
    
    def test_init_with_custom_svm_params(self):
        """Test initialization with custom SVM parameters."""
        # Create configuration with custom SVM parameters
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'svm_params': {
                'C': 2.0,
                'kernel': 'poly',
                'degree': 3
            }
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Verify SVM parameters
        svm_params = classifier._get_svm_params()
        assert svm_params['C'] == 2.0
        assert svm_params['kernel'] == 'poly'
        assert svm_params['degree'] == 3
    
    def test_init_with_custom_rf_params(self):
        """Test initialization with custom Random Forest parameters."""
        # Create configuration with custom RF parameters
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'rf_params': {
                'n_estimators': 200,
                'max_depth': 10,
                'min_samples_split': 5
            }
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Verify RF parameters
        rf_params = classifier._get_rf_params()
        assert rf_params['n_estimators'] == 200
        assert rf_params['max_depth'] == 10
        assert rf_params['min_samples_split'] == 5
    
    def test_init_with_invalid_config(self):
        """Test initialization with invalid configuration."""
        # Create an empty configuration
        config = {}
        
        # Initialize the classifier (should not raise an exception)
        classifier = DocumentClassifier(config)
        
        # Verify default values are used
        assert classifier.ensemble_weights['svm'] == 0.5
        assert classifier.ensemble_weights['random_forest'] == 0.5
        
        # Verify default parameters are used
        svm_params = classifier._get_svm_params()
        assert svm_params['C'] == 1.0
        assert svm_params['kernel'] == 'rbf'
        
        rf_params = classifier._get_rf_params()
        assert rf_params['n_estimators'] == 100
        assert rf_params['max_depth'] is None


# Test DocumentClassifier training
class TestDocumentClassifierTraining:
    """Tests for DocumentClassifier training with fit() method."""
    
    @pytest.fixture
    def mock_classifiers(self):
        """Fixture that returns mocked SVM and RF classifiers."""
        with patch('src.models.document_classifier.SVMClassifier') as mock_svm, \
             patch('src.models.document_classifier.RandomForestClassifier') as mock_rf:
            
            # Configure mock SVM classifier
            mock_svm_instance = Mock()
            mock_svm_instance.fit.return_value = mock_svm_instance
            mock_svm_instance.evaluate.return_value = {'accuracy': 0.9}
            mock_svm.return_value = mock_svm_instance
            
            # Configure mock RF classifier
            mock_rf_instance = Mock()
            mock_rf_instance.fit.return_value = mock_rf_instance
            mock_rf_instance.evaluate.return_value = {'accuracy': 0.95}
            mock_rf.return_value = mock_rf_instance
            
            yield mock_svm_instance, mock_rf_instance
    
    def test_fit_with_valid_data(self, mock_classifiers, synthetic_classification_data):
        """Test training with valid data."""
        mock_svm, mock_rf = mock_classifiers
        X, y = synthetic_classification_data
        
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier with mocked components
        classifier = DocumentClassifier(config)
        classifier.svm_classifier = mock_svm
        classifier.rf_classifier = mock_rf
        
        # Train the classifier
        result = classifier.fit(X, y)
        
        # Verify training
        assert result is classifier  # Should return self for method chaining
        assert classifier.trained is True
        mock_svm.fit.assert_called_once_with(X, y)
        mock_rf.fit.assert_called_once_with(X, y)
    
    def test_fit_with_auto_weighting(self, mock_classifiers, synthetic_classification_data):
        """Test training with auto-weighting enabled."""
        mock_svm, mock_rf = mock_classifiers
        X, y = synthetic_classification_data
        
        # Create configuration with auto-weighting
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'auto_weighting': True
        }
        
        # Initialize the classifier with mocked components
        classifier = DocumentClassifier(config)
        classifier.svm_classifier = mock_svm
        classifier.rf_classifier = mock_rf
        
        # Train the classifier
        classifier.fit(X, y)
        
        # Verify auto-weighting
        assert classifier.ensemble_weights['svm'] == 0.9 / 1.85  # 0.9 / (0.9 + 0.95)
        assert classifier.ensemble_weights['random_forest'] == 0.95 / 1.85  # 0.95 / (0.9 + 0.95)
        mock_svm.evaluate.assert_called_once_with(X, y)
        mock_rf.evaluate.assert_called_once_with(X, y)
    
    def test_fit_with_feature_names(self, mock_classifiers):
        """Test training with feature names."""
        mock_svm, mock_rf = mock_classifiers
        
        # Create DataFrame with named columns
        X = pd.DataFrame({
            'feature1': [1, 2, 3],
            'feature2': [4, 5, 6],
            'feature3': [7, 8, 9]
        })
        y = np.array(['invoice', 'license', 'bank_statement'])
        
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier with mocked components
        classifier = DocumentClassifier(config)
        classifier.svm_classifier = mock_svm
        classifier.rf_classifier = mock_rf
        
        # Add set_feature_names method to mocks
        mock_svm.set_feature_names = Mock()
        mock_rf.set_feature_names = Mock()
        
        # Train the classifier
        classifier.fit(X, y)
        
        # Verify feature names are stored
        assert classifier.feature_names == ['feature1', 'feature2', 'feature3']
        mock_svm.set_feature_names.assert_called_once_with(['feature1', 'feature2', 'feature3'])
        mock_rf.set_feature_names.assert_called_once_with(['feature1', 'feature2', 'feature3'])
    
    def test_fit_with_invalid_data(self, mock_classifiers):
        """Test training with invalid data."""
        mock_svm, mock_rf = mock_classifiers
        
        # Create invalid data (different lengths)
        X = np.array([[1, 2, 3], [4, 5, 6]])
        y = np.array(['invoice'])
        
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier with mocked components
        classifier = DocumentClassifier(config)
        classifier.svm_classifier = mock_svm
        classifier.rf_classifier = mock_rf
        
        # Add validation method
        classifier._validate_input = Mock(side_effect=ValueError("Input validation failed"))
        
        # Train the classifier (should raise ValueError)
        with pytest.raises(ValueError, match="Input validation failed"):
            classifier.fit(X, y)
        
        # Verify validation was called
        classifier._validate_input.assert_called_once_with(X, y)


# Test DocumentClassifier prediction
class TestDocumentClassifierPrediction:
    """Tests for DocumentClassifier prediction methods."""
    
    @pytest.fixture
    def trained_classifier(self, mock_svm_classifier, mock_random_forest_classifier):
        """Fixture that returns a trained DocumentClassifier with mocked components."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Replace component classifiers with mocks
        classifier.svm_classifier = mock_svm_classifier
        classifier.rf_classifier = mock_random_forest_classifier
        
        # Set trained flag and classes
        classifier.trained = True
        classifier.classes_ = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'])
        
        # Add validation method
        classifier._validate_input = Mock(return_value=None)
        
        # Add document type conversion method
        classifier._convert_to_document_type = Mock(side_effect=lambda x: DocumentType(x))
        classifier.ensure_consistent_document_types = Mock(side_effect=lambda x: x)
        
        return classifier
    
    def test_predict_when_classifiers_agree(self, trained_classifier):
        """Test prediction when both classifiers agree."""
        # Create test data
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        
        # Configure mocks to return the same predictions
        trained_classifier.svm_classifier.predict.return_value = np.array(['invoice', 'license', 'bank_statement'])
        trained_classifier.rf_classifier.predict.return_value = np.array(['invoice', 'license', 'bank_statement'])
        
        # Make prediction
        predictions = trained_classifier.predict(X)
        
        # Verify predictions
        assert len(predictions) == 3
        assert predictions[0] == 'invoice'
        assert predictions[1] == 'license'
        assert predictions[2] == 'bank_statement'
        
        # Verify both classifiers were called
        trained_classifier.svm_classifier.predict.assert_called_once_with(X)
        trained_classifier.rf_classifier.predict.assert_called_once_with(X)
        
        # Verify probabilities were not needed
        trained_classifier.svm_classifier.predict_proba.assert_not_called()
        trained_classifier.rf_classifier.predict_proba.assert_not_called()
    
    def test_predict_when_classifiers_disagree(self, trained_classifier):
        """Test prediction when classifiers disagree."""
        # Create test data
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]])
        
        # Configure mocks to return different predictions
        trained_classifier.svm_classifier.predict.return_value = np.array(['invoice', 'license', 'bank_statement'])
        trained_classifier.rf_classifier.predict.return_value = np.array(['invoice', 'tax_document', 'application'])
        
        # Configure probability predictions
        trained_classifier.svm_classifier.predict_proba.return_value = np.array([
            [0.8, 0.05, 0.05, 0.05, 0.05],  # invoice
            [0.05, 0.8, 0.05, 0.05, 0.05],   # license
            [0.05, 0.05, 0.8, 0.05, 0.05]    # bank_statement
        ])
        trained_classifier.rf_classifier.predict_proba.return_value = np.array([
            [0.75, 0.06, 0.06, 0.06, 0.07],  # invoice
            [0.06, 0.06, 0.06, 0.75, 0.07],   # tax_document
            [0.07, 0.06, 0.06, 0.06, 0.75]    # application
        ])
        
        # Set ensemble weights
        trained_classifier.ensemble_weights = {'svm': 0.6, 'random_forest': 0.4}
        
        # Make prediction
        predictions = trained_classifier.predict(X)
        
        # Verify predictions
        assert len(predictions) == 3
        assert predictions[0] == 'invoice'  # Both agree
        
        # For the second sample, SVM predicts 'license' with 0.8 confidence (weighted: 0.48)
        # RF predicts 'tax_document' with 0.75 confidence (weighted: 0.3)
        # Combined: license=0.48, tax_document=0.3, so 'license' wins
        assert predictions[1] == 'license'
        
        # For the third sample, SVM predicts 'bank_statement' with 0.8 confidence (weighted: 0.48)
        # RF predicts 'application' with 0.75 confidence (weighted: 0.3)
        # Combined: bank_statement=0.48, application=0.3, so 'bank_statement' wins
        assert predictions[2] == 'bank_statement'
        
        # Verify both classifiers were called
        trained_classifier.svm_classifier.predict.assert_called_once_with(X)
        trained_classifier.rf_classifier.predict.assert_called_once_with(X)
        trained_classifier.svm_classifier.predict_proba.assert_called_once_with(X)
        trained_classifier.rf_classifier.predict_proba.assert_called_once_with(X)
    
    def test_predict_proba(self, trained_classifier):
        """Test probability prediction."""
        # Create test data
        X = np.array([[1, 2, 3], [4, 5, 6]])
        
        # Configure probability predictions
        trained_classifier.svm_classifier.predict_proba.return_value = np.array([
            [0.8, 0.05, 0.05, 0.05, 0.05],
            [0.05, 0.8, 0.05, 0.05, 0.05]
        ])
        trained_classifier.rf_classifier.predict_proba.return_value = np.array([
            [0.7, 0.1, 0.1, 0.05, 0.05],
            [0.1, 0.7, 0.1, 0.05, 0.05]
        ])
        
        # Set ensemble weights
        trained_classifier.ensemble_weights = {'svm': 0.6, 'random_forest': 0.4}
        
        # Make probability prediction
        probabilities = trained_classifier.predict_proba(X)
        
        # Verify probabilities
        assert probabilities.shape == (2, 5)
        
        # Calculate expected probabilities for first sample
        # SVM: [0.8, 0.05, 0.05, 0.05, 0.05] * 0.6 = [0.48, 0.03, 0.03, 0.03, 0.03]
        # RF: [0.7, 0.1, 0.1, 0.05, 0.05] * 0.4 = [0.28, 0.04, 0.04, 0.02, 0.02]
        # Combined: [0.76, 0.07, 0.07, 0.05, 0.05]
        expected_proba1 = np.array([0.48, 0.03, 0.03, 0.03, 0.03]) + np.array([0.28, 0.04, 0.04, 0.02, 0.02])
        expected_proba1 = expected_proba1 / np.sum(expected_proba1)  # Normalize
        
        # Calculate expected probabilities for second sample
        # SVM: [0.05, 0.8, 0.05, 0.05, 0.05] * 0.6 = [0.03, 0.48, 0.03, 0.03, 0.03]
        # RF: [0.1, 0.7, 0.1, 0.05, 0.05] * 0.4 = [0.04, 0.28, 0.04, 0.02, 0.02]
        # Combined: [0.07, 0.76, 0.07, 0.05, 0.05]
        expected_proba2 = np.array([0.03, 0.48, 0.03, 0.03, 0.03]) + np.array([0.04, 0.28, 0.04, 0.02, 0.02])
        expected_proba2 = expected_proba2 / np.sum(expected_proba2)  # Normalize
        
        # Verify probabilities match expected values
        np.testing.assert_allclose(probabilities[0], expected_proba1, rtol=1e-5)
        np.testing.assert_allclose(probabilities[1], expected_proba2, rtol=1e-5)
        
        # Verify both classifiers were called
        trained_classifier.svm_classifier.predict_proba.assert_called_once_with(X)
        trained_classifier.rf_classifier.predict_proba.assert_called_once_with(X)
    
    def test_predict_untrained_model(self):
        """Test prediction with an untrained model."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier (untrained)
        classifier = DocumentClassifier(config)
        classifier.trained = False
        
        # Create test data
        X = np.array([[1, 2, 3]])
        
        # Make prediction (should raise RuntimeError)
        with pytest.raises(RuntimeError, match="Model has not been trained"):
            classifier.predict(X)
        
        # Make probability prediction (should raise RuntimeError)
        with pytest.raises(RuntimeError, match="Model has not been trained"):
            classifier.predict_proba(X)


# Test DocumentClassifier evaluation
class TestDocumentClassifierEvaluation:
    """Tests for DocumentClassifier evaluation methods."""
    
    @pytest.fixture
    def trained_classifier_for_eval(self):
        """Fixture that returns a trained DocumentClassifier for evaluation testing."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.trained = True
        
        # Mock methods
        classifier._validate_input = Mock(return_value=None)
        classifier.predict = Mock()
        classifier._convert_to_document_type = Mock(side_effect=lambda x: DocumentType(x))
        
        return classifier
    
    def test_evaluate(self, trained_classifier_for_eval):
        """Test evaluation with valid data."""
        # Create test data
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12], [13, 14, 15]])
        y = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'])
        
        # Configure predict to return predictions
        trained_classifier_for_eval.predict.return_value = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'])
        
        # Mock sklearn metrics
        with patch('src.models.document_classifier.accuracy_score') as mock_accuracy, \
             patch('src.models.document_classifier.precision_recall_fscore_support') as mock_prf, \
             patch('src.models.document_classifier.confusion_matrix') as mock_cm:
            
            # Configure mocks
            mock_accuracy.return_value = 1.0
            mock_prf.return_value = (np.array([1.0, 1.0, 1.0, 1.0, 1.0]), np.array([1.0, 1.0, 1.0, 1.0, 1.0]), 
                                     np.array([1.0, 1.0, 1.0, 1.0, 1.0]), None)
            mock_cm.return_value = np.array([[1, 0, 0, 0, 0], [0, 1, 0, 0, 0], [0, 0, 1, 0, 0], 
                                             [0, 0, 0, 1, 0], [0, 0, 0, 0, 1]])
            
            # Evaluate the classifier
            metrics = trained_classifier_for_eval.evaluate(X, y)
            
            # Verify metrics
            assert metrics['accuracy'] == 1.0
            assert len(metrics['precision']) == 5
            assert len(metrics['recall']) == 5
            assert len(metrics['f1_score']) == 5
            assert len(metrics['confusion_matrix']) == 5
            
            # Verify metrics were calculated
            mock_accuracy.assert_called_once_with(y, trained_classifier_for_eval.predict.return_value)
            mock_prf.assert_called_once_with(y, trained_classifier_for_eval.predict.return_value, average=None)
            mock_cm.assert_called_once_with(y, trained_classifier_for_eval.predict.return_value)
    
    def test_evaluate_untrained_model(self):
        """Test evaluation with an untrained model."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier (untrained)
        classifier = DocumentClassifier(config)
        classifier.trained = False
        
        # Create test data
        X = np.array([[1, 2, 3]])
        y = np.array(['invoice'])
        
        # Evaluate the classifier (should raise RuntimeError)
        with pytest.raises(RuntimeError, match="Model has not been trained"):
            classifier.evaluate(X, y)


# Test DocumentClassifier classification
class TestDocumentClassifierClassification:
    """Tests for DocumentClassifier high-level classification methods."""
    
    @pytest.fixture
    def trained_classifier_for_classify(self):
        """Fixture that returns a trained DocumentClassifier for classification testing."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.trained = True
        classifier.classes_ = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'])
        
        # Mock methods
        classifier._validate_input = Mock(return_value=None)
        classifier.predict = Mock()
        classifier.predict_proba = Mock()
        classifier._convert_to_document_type = Mock(side_effect=lambda x: DocumentType(x))
        
        return classifier
    
    def test_classify(self, trained_classifier_for_classify):
        """Test high-level classification method."""
        # Create test data
        features = np.array([1, 2, 3])
        
        # Configure predict to return a single prediction
        trained_classifier_for_classify.predict.return_value = np.array([DocumentType.APPLICATION])
        
        # Configure predict_proba to return probabilities
        trained_classifier_for_classify.predict_proba.return_value = np.array([
            [0.05, 0.05, 0.05, 0.05, 0.8]  # High confidence for 'application'
        ])
        
        # Classify the document
        doc_type, confidence_scores = trained_classifier_for_classify.classify(features)
        
        # Verify classification
        assert doc_type == DocumentType.APPLICATION
        assert len(confidence_scores) == 5
        assert confidence_scores[DocumentType.APPLICATION.value] == 0.8
        assert confidence_scores[DocumentType.INVOICE.value] == 0.05
        
        # Verify methods were called
        trained_classifier_for_classify.predict.assert_called_once()
        trained_classifier_for_classify.predict_proba.assert_called_once()
    
    def test_classify_with_reshape(self, trained_classifier_for_classify):
        """Test classification with feature reshaping."""
        # Create 1D feature vector
        features = np.array([1, 2, 3])
        
        # Configure predict to return a single prediction
        trained_classifier_for_classify.predict.return_value = np.array([DocumentType.INVOICE])
        
        # Configure predict_proba to return probabilities
        trained_classifier_for_classify.predict_proba.return_value = np.array([
            [0.8, 0.05, 0.05, 0.05, 0.05]  # High confidence for 'invoice'
        ])
        
        # Classify the document
        doc_type, confidence_scores = trained_classifier_for_classify.classify(features)
        
        # Verify classification
        assert doc_type == DocumentType.INVOICE
        
        # Verify predict was called with reshaped features
        # The reshape happens inside the classify method
        trained_classifier_for_classify.predict.assert_called_once()
        trained_classifier_for_classify.predict_proba.assert_called_once()
    
    def test_classify_untrained_model(self):
        """Test classification with an untrained model."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier (untrained)
        classifier = DocumentClassifier(config)
        classifier.trained = False
        
        # Create test data
        features = np.array([1, 2, 3])
        
        # Classify the document (should raise RuntimeError)
        with pytest.raises(RuntimeError, match="Model has not been trained"):
            classifier.classify(features)


# Test DocumentClassifier routing
class TestDocumentClassifierRouting:
    """Tests for DocumentClassifier document routing logic."""
    
    def test_get_routing_info(self):
        """Test routing information generation."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.model_version = "1.0.0"
        
        # Create document type and confidence scores
        document_type = DocumentType.APPLICATION
        confidence_scores = {
            DocumentType.INVOICE.value: 0.05,
            DocumentType.LICENSE.value: 0.05,
            DocumentType.BANK_STATEMENT.value: 0.05,
            DocumentType.TAX_RETURN.value: 0.05,
            DocumentType.APPLICATION.value: 0.8
        }
        
        # Mock _get_ocr_processor_for_type method
        classifier._get_ocr_processor_for_type = Mock(return_value="form_processor")
        
        # Get routing information
        routing_info = classifier.get_routing_info(document_type, confidence_scores)
        
        # Verify routing information
        assert routing_info["document_type"] == document_type.value
        assert routing_info["ocr_processor"] == "form_processor"
        assert routing_info["confidence"] == 0.8
        assert routing_info["requires_review"] is False  # 0.8 > 0.7 threshold
        assert routing_info["processing_priority"] == "medium"  # 0.8 is medium priority
        assert "routing_timestamp" in routing_info
        assert routing_info["routing_version"] == "1.0.0"
        
        # Verify OCR processor was determined
        classifier._get_ocr_processor_for_type.assert_called_once_with(document_type)
    
    def test_get_routing_info_low_confidence(self):
        """Test routing information with low confidence."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Create document type and confidence scores (low confidence)
        document_type = DocumentType.APPLICATION
        confidence_scores = {
            DocumentType.INVOICE.value: 0.2,
            DocumentType.LICENSE.value: 0.2,
            DocumentType.BANK_STATEMENT.value: 0.2,
            DocumentType.TAX_RETURN.value: 0.1,
            DocumentType.APPLICATION.value: 0.3  # Low confidence
        }
        
        # Mock _get_ocr_processor_for_type method
        classifier._get_ocr_processor_for_type = Mock(return_value="form_processor")
        
        # Get routing information
        routing_info = classifier.get_routing_info(document_type, confidence_scores)
        
        # Verify routing information
        assert routing_info["document_type"] == document_type.value
        assert routing_info["ocr_processor"] == "form_processor"
        assert routing_info["confidence"] == 0.3
        assert routing_info["requires_review"] is True  # 0.3 < 0.7 threshold
        assert routing_info["processing_priority"] == "low"  # 0.3 is low priority
    
    def test_get_routing_info_high_confidence(self):
        """Test routing information with high confidence."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7,
            'confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Create document type and confidence scores (high confidence)
        document_type = DocumentType.APPLICATION
        confidence_scores = {
            DocumentType.INVOICE.value: 0.02,
            DocumentType.LICENSE.value: 0.02,
            DocumentType.BANK_STATEMENT.value: 0.02,
            DocumentType.TAX_RETURN.value: 0.02,
            DocumentType.APPLICATION.value: 0.92  # High confidence
        }
        
        # Mock _get_ocr_processor_for_type method
        classifier._get_ocr_processor_for_type = Mock(return_value="form_processor")
        
        # Get routing information
        routing_info = classifier.get_routing_info(document_type, confidence_scores)
        
        # Verify routing information
        assert routing_info["document_type"] == document_type.value
        assert routing_info["ocr_processor"] == "form_processor"
        assert routing_info["confidence"] == 0.92
        assert routing_info["requires_review"] is False  # 0.92 > 0.7 threshold
        assert routing_info["processing_priority"] == "high"  # 0.92 is high priority
    
    def test_get_ocr_processor_for_type(self):
        """Test OCR processor selection based on document type."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Test processor selection for each document type
        assert classifier._get_ocr_processor_for_type(DocumentType.APPLICATION) == "form_processor"
        assert classifier._get_ocr_processor_for_type(DocumentType.TAX_RETURN) == "financial_processor"
        assert classifier._get_ocr_processor_for_type(DocumentType.BANK_STATEMENT) == "financial_processor"
        assert classifier._get_ocr_processor_for_type(DocumentType.ID_DOCUMENT) == "id_processor"
        assert classifier._get_ocr_processor_for_type(DocumentType.OTHER) == "general_processor"
        
        # Test with an unknown document type (should use general processor)
        assert classifier._get_ocr_processor_for_type("unknown_type") == "general_processor"


# Test DocumentClassifier serialization
class TestDocumentClassifierSerialization:
    """Tests for DocumentClassifier serialization and loading."""
    
    @pytest.fixture
    def trained_classifier_for_save(self, mock_svm_classifier, mock_random_forest_classifier):
        """Fixture that returns a trained DocumentClassifier for serialization testing."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.trained = True
        classifier.classes_ = np.array(['invoice', 'license', 'bank_statement', 'tax_document', 'application'])
        classifier.feature_names = ['feature1', 'feature2', 'feature3']
        classifier.metrics = {
            'accuracy': 0.95,
            'precision': {'invoice': 0.9, 'license': 0.95},
            'recall': {'invoice': 0.9, 'license': 0.95},
            'f1_score': {'invoice': 0.9, 'license': 0.95},
            'confusion_matrix': [[9, 1], [1, 19]],
            'classification_time': 0.1
        }
        
        # Replace component classifiers with mocks
        classifier.svm_classifier = mock_svm_classifier
        classifier.rf_classifier = mock_random_forest_classifier
        
        # Configure save methods for component classifiers
        mock_svm_classifier.save = Mock(return_value=Result.success("/tmp/models/svm_classifier.pkl"))
        mock_random_forest_classifier.save = Mock(return_value=Result.success("/tmp/models/rf_classifier.pkl"))
        
        # Mock super().save method
        with patch('src.models.document_classifier.BaseModel.save') as mock_super_save:
            mock_super_save.return_value = Result.success("/tmp/models/document_classifier.pkl")
            classifier.super_save = mock_super_save
        
        return classifier
    
    def test_save_ensemble(self, trained_classifier_for_save, tmp_path):
        """Test saving the ensemble classifier."""
        # Create a temporary directory for saving
        model_dir = str(tmp_path / "models")
        
        # Save the ensemble
        result = trained_classifier_for_save.save_ensemble(model_dir)
        
        # Verify save was successful
        assert result.is_success
        assert "ensemble" in result.value
        assert "svm" in result.value
        assert "random_forest" in result.value
        assert "metadata" in result.value
        
        # Verify component classifiers were saved
        trained_classifier_for_save.svm_classifier.save.assert_called_once()
        trained_classifier_for_save.rf_classifier.save.assert_called_once()
        
        # Verify metadata file was created
        metadata_path = result.value["metadata"]
        assert "ensemble_metadata.json" in metadata_path
    
    def test_save_ensemble_untrained(self, tmp_path):
        """Test saving an untrained ensemble classifier."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier (untrained)
        classifier = DocumentClassifier(config)
        classifier.trained = False
        
        # Create a temporary directory for saving
        model_dir = str(tmp_path / "models")
        
        # Save the ensemble (should fail)
        result = classifier.save_ensemble(model_dir)
        
        # Verify save failed
        assert result.is_failure
        assert "not been trained" in result.error
    
    def test_load_ensemble(self, tmp_path):
        """Test loading the ensemble classifier."""
        # Create a temporary directory for loading
        model_dir = str(tmp_path / "models")
        
        # Mock os.path.join to return predictable paths
        with patch('os.path.join') as mock_join, \
             patch('json.load') as mock_json_load, \
             patch('src.models.document_classifier.SVMClassifier.load') as mock_svm_load, \
             patch('src.models.document_classifier.RandomForestClassifier.load') as mock_rf_load, \
             patch('open'):
            
            # Configure mock_join to return predictable paths
            mock_join.side_effect = lambda *args: '/'.join(args)
            
            # Configure mock_json_load to return metadata
            mock_json_load.return_value = {
                "model_name": "document_classifier_v1",
                "model_version": "1.0.0",
                "ensemble_weights": {"svm": 0.6, "random_forest": 0.4},
                "config": {"model_path": "/tmp/models", "min_confidence_threshold": 0.7},
                "classes": ["invoice", "license", "bank_statement", "tax_document", "application"],
                "feature_names": ["feature1", "feature2", "feature3"],
                "metrics": {"accuracy": 0.95},
                "trained": True,
                "component_models": {
                    "svm": "/tmp/models/svm_classifier.pkl",
                    "random_forest": "/tmp/models/rf_classifier.pkl"
                }
            }
            
            # Configure mock_svm_load to return a mock SVM classifier
            mock_svm = Mock()
            mock_svm_load.return_value = Result.success(mock_svm)
            
            # Configure mock_rf_load to return a mock RF classifier
            mock_rf = Mock()
            mock_rf_load.return_value = Result.success(mock_rf)
            
            # Load the ensemble
            result = DocumentClassifier.load_ensemble(model_dir)
            
            # Verify load was successful
            assert result.is_success
            assert isinstance(result.value, DocumentClassifier)
            assert result.value.model_name == "document_classifier_v1"
            assert result.value.model_version == "1.0.0"
            assert result.value.ensemble_weights == {"svm": 0.6, "random_forest": 0.4}
            assert result.value.trained is True
            assert result.value.svm_classifier is mock_svm
            assert result.value.rf_classifier is mock_rf
            
            # Verify component classifiers were loaded
            mock_svm_load.assert_called_once_with("/tmp/models/svm_classifier.pkl")
            mock_rf_load.assert_called_once_with("/tmp/models/rf_classifier.pkl")
    
    def test_load_ensemble_failure(self, tmp_path):
        """Test loading the ensemble classifier with component failure."""
        # Create a temporary directory for loading
        model_dir = str(tmp_path / "models")
        
        # Mock os.path.join to return predictable paths
        with patch('os.path.join') as mock_join, \
             patch('json.load') as mock_json_load, \
             patch('src.models.document_classifier.SVMClassifier.load') as mock_svm_load, \
             patch('open'):
            
            # Configure mock_join to return predictable paths
            mock_join.side_effect = lambda *args: '/'.join(args)
            
            # Configure mock_json_load to return metadata
            mock_json_load.return_value = {
                "model_name": "document_classifier_v1",
                "model_version": "1.0.0",
                "ensemble_weights": {"svm": 0.6, "random_forest": 0.4},
                "config": {"model_path": "/tmp/models", "min_confidence_threshold": 0.7},
                "classes": ["invoice", "license", "bank_statement", "tax_document", "application"],
                "feature_names": ["feature1", "feature2", "feature3"],
                "metrics": {"accuracy": 0.95},
                "trained": True,
                "component_models": {
                    "svm": "/tmp/models/svm_classifier.pkl",
                    "random_forest": "/tmp/models/rf_classifier.pkl"
                }
            }
            
            # Configure mock_svm_load to fail
            mock_svm_load.return_value = Result.failure("Failed to load SVM classifier")
            
            # Load the ensemble (should fail)
            result = DocumentClassifier.load_ensemble(model_dir)
            
            # Verify load failed
            assert result.is_failure
            assert "Failed to load SVM classifier" in result.error


# Test DocumentClassifier utility methods
class TestDocumentClassifierUtilities:
    """Tests for DocumentClassifier utility methods."""
    
    def test_get_feature_importance(self, mock_svm_classifier, mock_random_forest_classifier):
        """Test feature importance retrieval."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.trained = True
        
        # Replace component classifiers with mocks
        classifier.svm_classifier = mock_svm_classifier
        classifier.rf_classifier = mock_random_forest_classifier
        
        # Configure get_feature_importance for component classifiers
        mock_svm_classifier.get_feature_importance.return_value = {
            'feature1': 0.5,
            'feature2': 0.3,
            'feature3': 0.2
        }
        mock_random_forest_classifier.get_feature_importance.return_value = {
            'feature1': 0.4,
            'feature2': 0.4,
            'feature3': 0.2
        }
        
        # Get feature importance
        importance = classifier.get_feature_importance()
        
        # Verify feature importance
        assert 'svm' in importance
        assert 'random_forest' in importance
        assert importance['svm']['feature1'] == 0.5
        assert importance['random_forest']['feature1'] == 0.4
        
        # Verify component methods were called
        mock_svm_classifier.get_feature_importance.assert_called_once()
        mock_random_forest_classifier.get_feature_importance.assert_called_once()
    
    def test_get_performance_metrics(self):
        """Test performance metrics retrieval."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Set metrics
        classifier.metrics = {
            'accuracy': 0.95,
            'precision': {'invoice': 0.9, 'license': 0.95},
            'recall': {'invoice': 0.9, 'license': 0.95},
            'f1_score': {'invoice': 0.9, 'license': 0.95},
            'confusion_matrix': [[9, 1], [1, 19]],
            'classification_time': 0.1
        }
        
        # Get performance metrics
        metrics = classifier.get_performance_metrics()
        
        # Verify metrics
        assert metrics['accuracy'] == 0.95
        assert metrics['precision']['invoice'] == 0.9
        assert metrics['recall']['invoice'] == 0.9
        assert metrics['f1_score']['invoice'] == 0.9
        assert metrics['confusion_matrix'] == [[9, 1], [1, 19]]
        assert metrics['classification_time'] == 0.1
    
    def test_get_performance_metrics_no_metrics(self):
        """Test performance metrics retrieval with no metrics."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.metrics = {}
        
        # Get performance metrics
        metrics = classifier.get_performance_metrics()
        
        # Verify empty metrics
        assert metrics == {}
    
    def test_get_model_info(self, mock_svm_classifier, mock_random_forest_classifier):
        """Test model information retrieval."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        classifier.model_name = "document_classifier_v1"
        classifier.model_version = "1.0.0"
        classifier.trained = True
        classifier.ensemble_weights = {'svm': 0.6, 'random_forest': 0.4}
        
        # Set metrics
        classifier.metrics = {
            'accuracy': 0.95,
            'precision': {'invoice': 0.9, 'license': 0.95},
            'recall': {'invoice': 0.9, 'license': 0.95},
            'f1_score': {'invoice': 0.9, 'license': 0.95},
            'confusion_matrix': [[9, 1], [1, 19]],
            'classification_time': 0.1
        }
        
        # Replace component classifiers with mocks
        classifier.svm_classifier = mock_svm_classifier
        classifier.rf_classifier = mock_random_forest_classifier
        
        # Configure get_model_info for component classifiers
        mock_svm_classifier.get_model_info.return_value = {
            'model_name': 'svm_classifier',
            'model_version': '1.0.0',
            'kernel': 'rbf',
            'C': 1.0
        }
        mock_random_forest_classifier.get_model_info.return_value = {
            'model_name': 'random_forest_classifier',
            'model_version': '1.0.0',
            'n_estimators': 100,
            'max_depth': None
        }
        
        # Get model information
        info = classifier.get_model_info()
        
        # Verify model information
        assert info['model_name'] == "document_classifier_v1"
        assert info['model_version'] == "1.0.0"
        assert info['ensemble_weights'] == {'svm': 0.6, 'random_forest': 0.4}
        assert info['trained'] is True
        assert 'component_models' in info
        assert 'svm' in info['component_models']
        assert 'random_forest' in info['component_models']
        assert 'performance_metrics' in info
        assert info['performance_metrics']['accuracy'] == 0.95
        
        # Verify component methods were called
        mock_svm_classifier.get_model_info.assert_called_once()
        mock_random_forest_classifier.get_model_info.assert_called_once()
    
    def test_ensure_consistent_document_types(self):
        """Test document type consistency enforcement."""
        # Create configuration
        config = {
            'model_path': '/tmp/models',
            'min_confidence_threshold': 0.7
        }
        
        # Initialize the classifier
        classifier = DocumentClassifier(config)
        
        # Mock _convert_to_document_type method
        classifier._convert_to_document_type = Mock(side_effect=lambda x: DocumentType(x) if not isinstance(x, DocumentType) else x)
        
        # Create mixed predictions (strings and DocumentType instances)
        predictions = np.array([
            'invoice',
            DocumentType.LICENSE,
            'bank_statement',
            DocumentType.TAX_RETURN,
            'application'
        ])
        
        # Ensure consistent document types
        consistent_predictions = classifier.ensure_consistent_document_types(predictions)
        
        # Verify all predictions are DocumentType instances
        for pred in consistent_predictions:
            assert isinstance(pred, DocumentType)
        
        # Verify conversion was called for string types only
        assert classifier._convert_to_document_type.call_count == 3  # 3 string types