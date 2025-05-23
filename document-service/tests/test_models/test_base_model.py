#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the BaseModel abstract class.

This module contains tests that verify the BaseModel interface correctly defines and enforces
the required methods for all document classifiers, including fit(), predict(), predict_proba(),
and evaluate(). It also tests validation of input data formats and common utility methods.
"""

import pytest
import numpy as np
from abc import ABC
from unittest.mock import MagicMock, patch
from sklearn.base import BaseEstimator

from src.models.base_model import BaseModel


class TestBaseModel:
    """Test suite for the BaseModel abstract class."""

    def test_base_model_is_abstract(self):
        """Test that BaseModel is an abstract class and cannot be instantiated directly."""
        with pytest.raises(TypeError, match=r"Can't instantiate abstract class BaseModel"):
            BaseModel()

    def test_base_model_inheritance(self):
        """Test that BaseModel inherits from ABC and BaseEstimator."""
        assert issubclass(BaseModel, ABC)
        assert issubclass(BaseModel, BaseEstimator)

    def test_abstract_methods_defined(self):
        """Test that all required abstract methods are defined in BaseModel."""
        abstract_methods = [
            "fit",
            "predict",
            "predict_proba",
            "evaluate",
            "save",
            "load"
        ]

        for method in abstract_methods:
            assert hasattr(BaseModel, method), f"BaseModel missing abstract method: {method}"

    def test_concrete_methods_defined(self):
        """Test that all concrete utility methods are defined in BaseModel."""
        concrete_methods = [
            "validate_input",
            "get_feature_importance",
            "cross_validate",
            "calculate_metrics",
            "get_params",
            "set_params",
            "get_confidence_scores",
            "is_prediction_confident"
        ]

        for method in concrete_methods:
            assert hasattr(BaseModel, method), f"BaseModel missing concrete method: {method}"

    def test_subclass_must_implement_abstract_methods(self):
        """Test that subclasses must implement all abstract methods."""
        # Create a subclass that doesn't implement all abstract methods
        class IncompleteModel(BaseModel):
            pass

        with pytest.raises(TypeError):
            IncompleteModel()

        # Create a subclass that implements only some abstract methods
        class PartialModel(BaseModel):
            def fit(self, X, y):
                pass

            def predict(self, X):
                pass

        with pytest.raises(TypeError):
            PartialModel()

        # Create a complete subclass implementing all abstract methods
        class CompleteModel(BaseModel):
            def fit(self, X, y):
                return self

            def predict(self, X):
                return np.array([0])

            def predict_proba(self, X):
                return np.array([[0.9, 0.1]])

            def evaluate(self, X, y):
                return {"accuracy": 0.95}

            def save(self, filepath):
                pass

            @classmethod
            def load(cls, filepath):
                return cls()

        # This should not raise an error
        model = CompleteModel()
        assert isinstance(model, BaseModel)


class TestBaseModelValidateInput:
    """Test suite for the validate_input method of BaseModel."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock model that inherits from BaseModel for testing."""
        class MockModel(BaseModel):
            def fit(self, X, y):
                return self

            def predict(self, X):
                return np.array([0])

            def predict_proba(self, X):
                return np.array([[0.9, 0.1]])

            def evaluate(self, X, y):
                return {"accuracy": 0.95}

            def save(self, filepath):
                pass

            @classmethod
            def load(cls, filepath):
                return cls()

        return MockModel()

    def test_validate_input_valid_data(self, mock_model):
        """Test validate_input with valid input data."""
        X = np.array([[1, 2, 3], [4, 5, 6]])
        y = np.array([0, 1])

        X_validated, y_validated = mock_model.validate_input(X, y)

        assert np.array_equal(X_validated, X)
        assert np.array_equal(y_validated, y)

    def test_validate_input_list_conversion(self, mock_model):
        """Test validate_input converts lists to numpy arrays."""
        X = [[1, 2, 3], [4, 5, 6]]
        y = [0, 1]

        X_validated, y_validated = mock_model.validate_input(X, y)

        assert isinstance(X_validated, np.ndarray)
        assert isinstance(y_validated, np.ndarray)
        assert np.array_equal(X_validated, np.array(X))
        assert np.array_equal(y_validated, np.array(y))

    def test_validate_input_invalid_X_dimension(self, mock_model):
        """Test validate_input raises error for X with invalid dimensions."""
        # 1D array instead of 2D
        X = np.array([1, 2, 3])
        y = np.array([0])

        with pytest.raises(ValueError, match=r"X must be a 2D array"):
            mock_model.validate_input(X, y)

        # 3D array instead of 2D
        X = np.array([[[1, 2], [3, 4]], [[5, 6], [7, 8]]])
        with pytest.raises(ValueError, match=r"X must be a 2D array"):
            mock_model.validate_input(X, y)

    def test_validate_input_invalid_y_dimension(self, mock_model):
        """Test validate_input raises error for y with invalid dimensions."""
        X = np.array([[1, 2, 3], [4, 5, 6]])
        
        # 2D array instead of 1D
        y = np.array([[0], [1]])

        with pytest.raises(ValueError, match=r"y must be a 1D array"):
            mock_model.validate_input(X, y)

    def test_validate_input_mismatched_samples(self, mock_model):
        """Test validate_input raises error when X and y have different sample counts."""
        X = np.array([[1, 2, 3], [4, 5, 6]])
        y = np.array([0, 1, 2])  # 3 samples instead of 2

        with pytest.raises(ValueError, match=r"X and y must have the same number of samples"):
            mock_model.validate_input(X, y)

    def test_validate_input_X_only(self, mock_model):
        """Test validate_input works with only X provided (no y)."""
        X = np.array([[1, 2, 3], [4, 5, 6]])

        X_validated, y_validated = mock_model.validate_input(X)

        assert np.array_equal(X_validated, X)
        assert y_validated is None

    def test_validate_input_unconvertible_X(self, mock_model):
        """Test validate_input raises error for X that can't be converted to numpy array."""
        X = ["string1", "string2"]  # Can't be converted to numeric numpy array

        with pytest.raises(ValueError, match=r"X must be convertible to a numpy array"):
            mock_model.validate_input(X)

    def test_validate_input_unconvertible_y(self, mock_model):
        """Test validate_input raises error for y that can't be converted to numpy array."""
        X = np.array([[1, 2, 3], [4, 5, 6]])
        y = ["class1", "class2"]  # Can't be converted to numeric numpy array

        with pytest.raises(ValueError, match=r"y must be convertible to a numpy array"):
            mock_model.validate_input(X, y)


class TestBaseModelUtilityMethods:
    """Test suite for the utility methods of BaseModel."""

    @pytest.fixture
    def mock_model(self):
        """Create a mock model that inherits from BaseModel for testing."""
        class MockModel(BaseModel):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.is_fitted = True
                self.classes_ = np.array(["class1", "class2"])
                self.feature_names_ = ["feature1", "feature2", "feature3"]

            def fit(self, X, y):
                return self

            def predict(self, X):
                return np.array([0, 1])

            def predict_proba(self, X):
                return np.array([[0.8, 0.2], [0.3, 0.7]])

            def evaluate(self, X, y):
                return {"accuracy": 0.95}

            def save(self, filepath):
                pass

            @classmethod
            def load(cls, filepath):
                return cls()

        return MockModel(confidence_threshold=0.75)

    def test_get_feature_importance_default(self, mock_model):
        """Test that get_feature_importance returns None by default."""
        assert mock_model.get_feature_importance() is None

    def test_get_params(self, mock_model):
        """Test that get_params returns the model parameters."""
        params = mock_model.get_params()
        assert isinstance(params, dict)
        assert params["confidence_threshold"] == 0.75

    def test_set_params(self, mock_model):
        """Test that set_params updates the model parameters."""
        mock_model.set_params(confidence_threshold=0.9, new_param="value")
        params = mock_model.get_params()
        
        assert params["confidence_threshold"] == 0.9
        assert params["new_param"] == "value"

    def test_get_confidence_scores(self, mock_model):
        """Test that get_confidence_scores returns the maximum probability for each sample."""
        probabilities = np.array([[0.8, 0.2], [0.3, 0.7]])
        confidence_scores = mock_model.get_confidence_scores(probabilities)
        
        assert np.array_equal(confidence_scores, np.array([0.8, 0.7]))

    def test_is_prediction_confident(self, mock_model):
        """Test that is_prediction_confident correctly applies the confidence threshold."""
        # Should be confident (0.8 > 0.75)
        assert mock_model.is_prediction_confident(0.8) is True
        
        # Should be confident (0.75 == 0.75)
        assert mock_model.is_prediction_confident(0.75) is True
        
        # Should not be confident (0.7 < 0.75)
        assert mock_model.is_prediction_confident(0.7) is False

    @patch("document_service.src.models.base_model.cross_val_score")
    def test_cross_validate(self, mock_cross_val_score, mock_model):
        """Test that cross_validate correctly performs cross-validation."""
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        y = np.array([0, 1, 0, 1])
        
        # Mock the cross_val_score function to return predefined scores
        mock_cross_val_score.return_value = np.array([0.95, 0.90, 0.85])
        
        cv_metrics = mock_model.cross_validate(X, y, cv=3)
        
        # Verify cross_val_score was called with correct parameters
        mock_cross_val_score.assert_called_once_with(mock_model, X, y, cv=3, scoring="accuracy")
        
        # Verify the returned metrics
        assert cv_metrics["cv_accuracy_mean"] == 0.9  # (0.95 + 0.90 + 0.85) / 3
        assert cv_metrics["cv_accuracy_std"] == pytest.approx(0.05, abs=1e-6)  # std of [0.95, 0.90, 0.85]
        assert cv_metrics["cv_accuracy_min"] == 0.85
        assert cv_metrics["cv_accuracy_max"] == 0.95
        assert cv_metrics["cv_folds"] == 3

    @patch("src.models.base_model.cross_val_score")
    def test_cross_validate_below_threshold(self, mock_cross_val_score, mock_model, caplog):
        """Test that cross_validate logs a warning when accuracy is below 99%."""
        X = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]])
        y = np.array([0, 1, 0, 1])
        
        # Mock the cross_val_score function to return scores below 99%
        mock_cross_val_score.return_value = np.array([0.95, 0.90, 0.85])
        
        cv_metrics = mock_model.cross_validate(X, y, cv=3)
        
        # Verify a warning was logged
        assert any("below the required 99% threshold" in record.message for record in caplog.records)

    @patch("src.models.base_model.accuracy_score")
    @patch("src.models.base_model.precision_recall_fscore_support")
    @patch("src.models.base_model.confusion_matrix")
    @patch("src.models.base_model.roc_auc_score")
    def test_calculate_metrics(self, mock_roc_auc, mock_cm, mock_prf, mock_accuracy, mock_model, caplog):
        """Test that calculate_metrics correctly calculates classification metrics."""
        y_true = np.array([0, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 0])  # One misclassification
        y_prob = np.array([[0.8, 0.2], [0.3, 0.7], [0.9, 0.1], [0.6, 0.4]])  # Probabilities for binary classification
        
        # Mock the metric functions
        mock_accuracy.return_value = 0.75  # 3/4 correct
        mock_prf.return_value = (0.8, 0.7, 0.75, None)  # precision, recall, f1, support
        mock_cm.return_value = np.array([[2, 0], [1, 1]])  # Confusion matrix
        mock_roc_auc.return_value = 0.85  # AUC score
        
        metrics = mock_model.calculate_metrics(y_true, y_pred, y_prob)
        
        # Verify the metric functions were called correctly
        mock_accuracy.assert_called_once_with(y_true, y_pred)
        mock_prf.assert_called_once_with(y_true, y_pred, average="weighted")
        mock_cm.assert_called_once_with(y_true, y_pred)
        mock_roc_auc.assert_called_once_with(y_true, y_prob[:, 1])
        
        # Verify the returned metrics
        assert metrics["accuracy"] == 0.75
        assert metrics["precision"] == 0.8
        assert metrics["recall"] == 0.7
        assert metrics["f1_score"] == 0.75
        assert metrics["confusion_matrix"] == [[2, 0], [1, 1]]
        assert metrics["roc_auc"] == 0.85
        
        # Verify a warning was logged for accuracy below 99%
        assert any("below the required 99% threshold" in record.message for record in caplog.records)

    @patch("src.models.base_model.accuracy_score")
    @patch("src.models.base_model.precision_recall_fscore_support")
    @patch("src.models.base_model.confusion_matrix")
    def test_calculate_metrics_without_probabilities(self, mock_cm, mock_prf, mock_accuracy, mock_model):
        """Test that calculate_metrics works without probability scores."""
        y_true = np.array([0, 1, 0, 1])
        y_pred = np.array([0, 1, 0, 0])  # One misclassification
        
        # Mock the metric functions
        mock_accuracy.return_value = 0.75  # 3/4 correct
        mock_prf.return_value = (0.8, 0.7, 0.75, None)  # precision, recall, f1, support
        mock_cm.return_value = np.array([[2, 0], [1, 1]])  # Confusion matrix
        
        metrics = mock_model.calculate_metrics(y_true, y_pred)  # No y_prob provided
        
        # Verify the returned metrics (should not include roc_auc)
        assert "roc_auc" not in metrics
        assert metrics["accuracy"] == 0.75
        assert metrics["precision"] == 0.8
        assert metrics["recall"] == 0.7
        assert metrics["f1_score"] == 0.75

    @patch("src.models.base_model.roc_auc_score")
    def test_calculate_metrics_multiclass(self, mock_roc_auc, mock_model):
        """Test that calculate_metrics correctly handles multiclass classification."""
        y_true = np.array([0, 1, 2, 0])
        y_pred = np.array([0, 1, 1, 0])  # One misclassification
        y_prob = np.array([
            [0.8, 0.1, 0.1],  # Class 0
            [0.1, 0.8, 0.1],  # Class 1
            [0.2, 0.6, 0.2],  # Misclassified as 1 instead of 2
            [0.7, 0.2, 0.1]   # Class 0
        ])
        
        # Mock the ROC AUC score for multiclass
        mock_roc_auc.return_value = 0.82
        
        # Patch the other metric functions to return realistic values
        with patch("src.models.base_model.accuracy_score", return_value=0.75), \
             patch("src.models.base_model.precision_recall_fscore_support", 
                   return_value=(np.array([0.8, 0.7, 0.0]), np.array([1.0, 0.5, 0.0]), np.array([0.89, 0.58, 0.0]), None)), \
             patch("src.models.base_model.confusion_matrix", 
                   return_value=np.array([[2, 0, 0], [0, 1, 1], [0, 0, 0]])):
            
            metrics = mock_model.calculate_metrics(y_true, y_pred, y_prob)
        
        # Verify ROC AUC was calculated correctly for multiclass
        mock_roc_auc.assert_called_once_with(y_true, y_prob, multi_class="ovr", average="weighted")
        assert metrics["roc_auc"] == 0.82

    def test_repr(self, mock_model):
        """Test the string representation of the model."""
        repr_str = repr(mock_model)
        
        # The representation should include the class name, parameters, and fitted status
        assert "MockModel" in repr_str
        assert "confidence_threshold=0.75" in repr_str
        assert "fitted" in repr_str  # The mock model has is_fitted=True


class TestBaseModelImplementation:
    """Test suite for a complete implementation of BaseModel."""

    @pytest.fixture
    def complete_model_class(self):
        """Create a complete implementation of BaseModel for testing."""
        class CompleteModel(BaseModel):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self._model = MagicMock()
                self.is_fitted = False
                self.classes_ = None
                self.feature_names_ = None

            def fit(self, X, y):
                X, y = self.validate_input(X, y)
                self._model.fit(X, y)
                self.is_fitted = True
                self.classes_ = np.unique(y)
                self.feature_names_ = [f"feature_{i}" for i in range(X.shape[1])]
                return self

            def predict(self, X):
                X, _ = self.validate_input(X)
                if not self.is_fitted:
                    raise ValueError("Model is not fitted yet.")
                return self._model.predict(X)

            def predict_proba(self, X):
                X, _ = self.validate_input(X)
                if not self.is_fitted:
                    raise ValueError("Model is not fitted yet.")
                return self._model.predict_proba(X)

            def evaluate(self, X, y):
                X, y = self.validate_input(X, y)
                if not self.is_fitted:
                    raise ValueError("Model is not fitted yet.")
                y_pred = self.predict(X)
                y_prob = self.predict_proba(X)
                return self.calculate_metrics(y, y_pred, y_prob)

            def save(self, filepath):
                # Mock implementation
                pass

            @classmethod
            def load(cls, filepath):
                # Mock implementation
                return cls()

            def get_feature_importance(self):
                if not self.is_fitted:
                    return None
                # Mock feature importance
                return {name: 1.0/len(self.feature_names_) for name in self.feature_names_}

        return CompleteModel

    def test_complete_implementation(self, complete_model_class):
        """Test a complete implementation of BaseModel."""
        model = complete_model_class()
        
        # Test that the model can be instantiated
        assert isinstance(model, BaseModel)
        
        # Test that the model is not fitted initially
        assert model.is_fitted is False
        assert model.classes_ is None
        assert model.feature_names_ is None
        
        # Test that the model can be fitted
        X = np.array([[1, 2], [3, 4], [5, 6]])
        y = np.array([0, 1, 0])
        
        # Mock the underlying model's predict and predict_proba methods
        model._model.predict.return_value = np.array([0, 1, 0])
        model._model.predict_proba.return_value = np.array([[0.8, 0.2], [0.3, 0.7], [0.9, 0.1]])
        
        # Fit the model
        model.fit(X, y)
        
        # Test that the model is now fitted
        assert model.is_fitted is True
        assert np.array_equal(model.classes_, np.array([0, 1]))
        assert model.feature_names_ == ["feature_0", "feature_1"]
        
        # Test prediction methods
        y_pred = model.predict(X)
        assert np.array_equal(y_pred, np.array([0, 1, 0]))
        
        y_prob = model.predict_proba(X)
        assert np.array_equal(y_prob, np.array([[0.8, 0.2], [0.3, 0.7], [0.9, 0.1]]))
        
        # Test evaluation
        with patch.object(model, "calculate_metrics", return_value={"accuracy": 1.0}):
            metrics = model.evaluate(X, y)
            assert metrics["accuracy"] == 1.0
        
        # Test feature importance
        importance = model.get_feature_importance()
        assert importance == {"feature_0": 0.5, "feature_1": 0.5}

    def test_unfitted_model_behavior(self, complete_model_class):
        """Test behavior of an unfitted model."""
        model = complete_model_class()
        X = np.array([[1, 2], [3, 4]])
        y = np.array([0, 1])
        
        # Test that predict raises an error if the model is not fitted
        with pytest.raises(ValueError, match=r"Model is not fitted yet"):
            model.predict(X)
        
        # Test that predict_proba raises an error if the model is not fitted
        with pytest.raises(ValueError, match=r"Model is not fitted yet"):
            model.predict_proba(X)
        
        # Test that evaluate raises an error if the model is not fitted
        with pytest.raises(ValueError, match=r"Model is not fitted yet"):
            model.evaluate(X, y)
        
        # Test that get_feature_importance returns None if the model is not fitted
        assert model.get_feature_importance() is None