#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the BaseModel abstract class.

This module contains tests for the abstract base class that defines the interface
for all document classifiers in the Document Service. It verifies that the BaseModel
interface correctly defines and enforces the required methods, validates input data
formats, and provides common utility methods for all classifiers.
"""

import os
import pytest
import numpy as np
from abc import ABC
from typing import Dict, List, Optional, Any, cast
from unittest.mock import MagicMock, patch

# Fix import paths for testing
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

# Import the modules after fixing the path
from models.base_model import BaseModel, T
from types.classification import (
    ClassificationModel,
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters,
    ClassificationMetrics
)
from types.documents import DocumentType
from types.config import ModelConfig
from types.errors import Result

# These imports are already handled above


# Create a concrete implementation of BaseModel for testing
class ConcreteModel(BaseModel):
    """Concrete implementation of BaseModel for testing purposes."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.model = MagicMock(spec=ClassificationModel)
        self.classes_ = np.array([DocumentType.APPLICATION.value, DocumentType.TAX_RETURN.value, 
                                 DocumentType.BANK_STATEMENT.value, DocumentType.OTHER.value])
        self.feature_names = [f"feature_{i}" for i in range(10)]
        
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'ConcreteModel':
        """Train the model on the provided data."""
        self._validate_input(X, y)
        self.model.fit(X, y)
        self.trained = True
        return self
    
    def predict(self, X: FeatureVector) -> np.ndarray:
        """Predict class labels for the provided data."""
        self._validate_input(X, for_prediction=True)
        return self.model.predict(X)
    
    def predict_proba(self, X: FeatureVector) -> np.ndarray:
        """Predict class probabilities for the provided data."""
        self._validate_input(X, for_prediction=True)
        return self.model.predict_proba(X)
    
    def evaluate(self, X: FeatureVector, y: np.ndarray) -> ClassificationMetrics:
        """Evaluate the model on the provided data."""
        self._validate_input(X, y)
        predictions = self.predict(X)
        return {
            'accuracy': 0.95,
            'precision': {'application': 0.94, 'tax_return': 0.96},
            'recall': {'application': 0.93, 'tax_return': 0.97},
            'f1_score': {'application': 0.935, 'tax_return': 0.965},
            'confusion_matrix': np.array([[45, 5], [3, 47]])
        }


# Create an incomplete implementation that doesn't implement all abstract methods
class IncompleteModel(BaseModel):
    """Incomplete implementation of BaseModel for testing abstract method enforcement."""
    
    def __init__(self, config: ModelConfig):
        super().__init__(config)
    
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'IncompleteModel':
        """Train the model on the provided data."""
        return self
    
    # Missing predict, predict_proba, and evaluate methods


class TestBaseModel:
    """Test suite for the BaseModel abstract class."""
    
    @pytest.fixture
    def model_config(self) -> ModelConfig:
        """Create a model configuration for testing."""
        return ModelConfig(
            model_type="test_model",
            parameters={"param1": 1, "param2": "value"},
            confidence_threshold=0.75,
            version="1.0.0",
            description="Test model for unit tests"
        )
    
    @pytest.fixture
    def concrete_model(self, model_config) -> ConcreteModel:
        """Create a concrete model instance for testing."""
        model = ConcreteModel(model_config)
        # Mock the model's predict and predict_proba methods
        model.model.predict.return_value = np.array(["application", "tax_return", "bank_statement"])
        model.model.predict_proba.return_value = np.array([
            [0.8, 0.1, 0.05, 0.05],
            [0.1, 0.75, 0.1, 0.05],
            [0.05, 0.1, 0.8, 0.05]
        ])
        model.trained = True
        return model
    
    @pytest.fixture
    def feature_vector(self) -> FeatureVector:
        """Create a feature vector for testing."""
        return np.random.random((3, 10))
    
    @pytest.fixture
    def target_labels(self) -> np.ndarray:
        """Create target labels for testing."""
        return np.array(["application", "tax_return", "bank_statement"])
    
    def test_abstract_class_cannot_be_instantiated(self, model_config):
        """Test that BaseModel cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseModel(model_config)
    
    def test_incomplete_implementation_raises_error(self):
        """Test that an incomplete implementation raises TypeError."""
        with pytest.raises(TypeError):
            IncompleteModel(ModelConfig())
    
    def test_initialization(self, concrete_model, model_config):
        """Test that the model is initialized correctly."""
        assert concrete_model.config == model_config
        assert concrete_model.model_name == "ConcreteModel"
        assert concrete_model.model_version == "1.0.0"
        assert concrete_model.trained is True  # We set this in the fixture
        assert len(concrete_model.feature_names) == 10
        assert concrete_model.classes_ is not None
    
    def test_fit_method(self, concrete_model, feature_vector, target_labels):
        """Test the fit method."""
        # Reset trained flag for this test
        concrete_model.trained = False
        
        result = concrete_model.fit(feature_vector, target_labels)
        
        # Check that the model's fit method was called with the correct arguments
        concrete_model.model.fit.assert_called_once_with(feature_vector, target_labels)
        
        # Check that the trained flag was set
        assert concrete_model.trained is True
        
        # Check that the method returns self for method chaining
        assert result is concrete_model
    
    def test_predict_method(self, concrete_model, feature_vector):
        """Test the predict method."""
        predictions = concrete_model.predict(feature_vector)
        
        # Check that the model's predict method was called with the correct arguments
        concrete_model.model.predict.assert_called_once_with(feature_vector)
        
        # Check that the predictions have the expected shape
        assert len(predictions) == 3
        assert predictions[0] == "application"
    
    def test_predict_proba_method(self, concrete_model, feature_vector):
        """Test the predict_proba method."""
        probabilities = concrete_model.predict_proba(feature_vector)
        
        # Check that the model's predict_proba method was called with the correct arguments
        concrete_model.model.predict_proba.assert_called_once_with(feature_vector)
        
        # Check that the probabilities have the expected shape
        assert probabilities.shape == (3, 4)
        assert np.isclose(probabilities[0, 0], 0.8)
    
    def test_evaluate_method(self, concrete_model, feature_vector, target_labels):
        """Test the evaluate method."""
        metrics = concrete_model.evaluate(feature_vector, target_labels)
        
        # Check that the metrics have the expected structure
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'confusion_matrix' in metrics
        
        # Check specific metric values
        assert metrics['accuracy'] == 0.95
        assert metrics['precision']['application'] == 0.94
        assert metrics['recall']['tax_return'] == 0.97
    
    def test_predict_with_confidence(self, concrete_model, feature_vector):
        """Test the predict_with_confidence method."""
        results = concrete_model.predict_with_confidence(feature_vector)
        
        # Check that the results have the expected structure
        assert len(results) == 3
        assert isinstance(results[0], ClassificationResult)
        assert hasattr(results[0], 'document_type')
        assert hasattr(results[0], 'confidence')
        assert hasattr(results[0], 'model_name')
        assert hasattr(results[0], 'model_version')
        assert hasattr(results[0], 'prediction_time')
        assert hasattr(results[0], 'class_probabilities')
        
        # Check specific result values
        assert results[0].document_type == DocumentType.APPLICATION
        assert results[0].confidence.value == 0.8
        assert results[0].confidence.threshold == 0.75
        assert results[0].confidence.requires_review is False
        assert results[0].model_name == "ConcreteModel"
        assert results[0].model_version == "1.0.0"
    
    def test_predict_with_confidence_requires_review(self, concrete_model, feature_vector):
        """Test that predict_with_confidence sets requires_review correctly."""
        # Modify the probabilities to be below the threshold
        concrete_model.model.predict_proba.return_value = np.array([
            [0.7, 0.1, 0.1, 0.1],  # Below threshold
            [0.8, 0.1, 0.05, 0.05],  # Above threshold
            [0.6, 0.2, 0.1, 0.1]   # Below threshold
        ])
        
        results = concrete_model.predict_with_confidence(feature_vector)
        
        # Check that requires_review is set correctly
        assert results[0].confidence.requires_review is True
        assert results[1].confidence.requires_review is False
        assert results[2].confidence.requires_review is True
    
    def test_predict_with_confidence_untrained_model(self, model_config, feature_vector):
        """Test that predict_with_confidence raises an error for untrained models."""
        model = ConcreteModel(model_config)
        model.trained = False
        
        with pytest.raises(RuntimeError, match="Model has not been trained"):
            model.predict_with_confidence(feature_vector)
    
    def test_save_method(self, concrete_model, tmp_path):
        """Test the save method."""
        model_path = os.path.join(tmp_path, "test_model.pkl")
        
        with patch("pickle.dump") as mock_dump:
            result = concrete_model.save(model_path)
        
        # Check that pickle.dump was called
        mock_dump.assert_called_once()
        
        # Check that the result is a success
        assert result.is_success
        assert result.value == model_path
    
    def test_save_method_untrained_model(self, model_config, tmp_path):
        """Test that save raises an error for untrained models."""
        model = ConcreteModel(model_config)
        model.trained = False
        model_path = os.path.join(tmp_path, "test_model.pkl")
        
        result = model.save(model_path)
        
        # Check that the result is a failure
        assert result.is_failure
        assert "Model has not been trained" in str(result.error)
    
    def test_load_method(self, concrete_model, model_config, tmp_path):
        """Test the load method."""
        model_path = os.path.join(tmp_path, "test_model.pkl")
        
        # Mock data to be loaded
        model_data = {
            'model': MagicMock(),
            'model_name': "ConcreteModel",
            'model_version': "1.0.0",
            'classes_': np.array(["application", "tax_return"]),
            'feature_names': ["feature_1", "feature_2"],
            'config': model_config,
            'trained': True
        }
        
        with patch("pickle.load", return_value=model_data):
            with patch("builtins.open", create=True):
                result = ConcreteModel.load(model_path)
        
        # Check that the result is a success
        assert result.is_success
        assert isinstance(result.value, ConcreteModel)
        assert result.value.model_name == "ConcreteModel"
        assert result.value.model_version == "1.0.0"
        assert result.value.trained is True
    
    def test_load_method_error(self, tmp_path):
        """Test that load handles errors correctly."""
        model_path = os.path.join(tmp_path, "nonexistent_model.pkl")
        
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            result = ConcreteModel.load(model_path)
        
        # Check that the result is a failure
        assert result.is_failure
        assert "Failed to load model" in str(result.error)
    
    def test_get_parameters(self, concrete_model):
        """Test the get_parameters method."""
        # Mock the model's get_params method
        concrete_model.model.get_params.return_value = {"param1": 1, "param2": "value"}
        
        params = concrete_model.get_parameters()
        
        # Check that the parameters have the expected structure
        assert "param1" in params
        assert "param2" in params
        assert "model_name" in params
        assert "model_version" in params
        assert "trained" in params
        assert "n_features" in params
        assert "n_classes" in params
        
        # Check specific parameter values
        assert params["param1"] == 1
        assert params["param2"] == "value"
        assert params["model_name"] == "ConcreteModel"
        assert params["model_version"] == "1.0.0"
        assert params["trained"] is True
        assert params["n_features"] == 10
        assert params["n_classes"] == 4
    
    def test_validate_input_valid_data(self, concrete_model, feature_vector, target_labels):
        """Test that _validate_input accepts valid data."""
        # This should not raise an exception
        concrete_model._validate_input(feature_vector, target_labels)
    
    def test_validate_input_none_features(self, concrete_model, target_labels):
        """Test that _validate_input rejects None features."""
        with pytest.raises(ValueError, match="Feature vectors \(X\) cannot be None"):
            concrete_model._validate_input(None, target_labels)
    
    def test_validate_input_invalid_features_shape(self, concrete_model, target_labels):
        """Test that _validate_input rejects features with invalid shape."""
        # 1D array instead of 2D
        invalid_features = np.array([1, 2, 3])
        
        with pytest.raises(ValueError, match="Feature vectors \(X\) must be a 2D array-like object"):
            concrete_model._validate_input(invalid_features, target_labels)
    
    def test_validate_input_none_labels(self, concrete_model, feature_vector):
        """Test that _validate_input rejects None labels for training."""
        with pytest.raises(ValueError, match="Target labels \(y\) cannot be None for training"):
            concrete_model._validate_input(feature_vector, None)
    
    def test_validate_input_mismatched_samples(self, concrete_model, feature_vector):
        """Test that _validate_input rejects mismatched sample counts."""
        # 4 labels but only 3 feature vectors
        mismatched_labels = np.array(["application", "tax_return", "bank_statement", "other"])
        
        with pytest.raises(ValueError, match="Number of samples in X \(3\) and y \(4\) do not match"):
            concrete_model._validate_input(feature_vector, mismatched_labels)
    
    def test_validate_input_for_prediction_untrained_model(self, model_config, feature_vector):
        """Test that _validate_input rejects prediction on untrained models."""
        model = ConcreteModel(model_config)
        model.trained = False
        
        with pytest.raises(RuntimeError, match="Model has not been trained"):
            model._validate_input(feature_vector, for_prediction=True)
    
    def test_convert_to_document_type_from_string(self, concrete_model):
        """Test that _convert_to_document_type converts strings correctly."""
        doc_type = concrete_model._convert_to_document_type("application")
        assert doc_type == DocumentType.APPLICATION
        
        doc_type = concrete_model._convert_to_document_type("TAX_RETURN")
        assert doc_type == DocumentType.TAX_RETURN
    
    def test_convert_to_document_type_from_int(self, concrete_model):
        """Test that _convert_to_document_type converts integers correctly."""
        # This assumes DocumentType enum values are integers
        # If they're strings, this test would need to be adjusted
        with patch.object(DocumentType, "__call__", return_value=DocumentType.APPLICATION):
            doc_type = concrete_model._convert_to_document_type(1)
            assert doc_type == DocumentType.APPLICATION
    
    def test_convert_to_document_type_from_enum(self, concrete_model):
        """Test that _convert_to_document_type handles enum values correctly."""
        doc_type = concrete_model._convert_to_document_type(DocumentType.APPLICATION)
        assert doc_type == DocumentType.APPLICATION
    
    def test_convert_to_document_type_invalid(self, concrete_model):
        """Test that _convert_to_document_type handles invalid values gracefully."""
        # Should default to OTHER for invalid values
        doc_type = concrete_model._convert_to_document_type("invalid_type")
        assert doc_type == DocumentType.OTHER