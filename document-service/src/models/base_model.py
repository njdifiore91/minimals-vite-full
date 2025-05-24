#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Abstract base class for all document classifiers in the Document Service.

This module defines the common interface that all classifier implementations must follow,
including methods for training, prediction, evaluation, and serialization.

All document classifier models (SVM, Random Forest, etc.) must inherit from this base class
to ensure a consistent interface throughout the Document Service. This standardization
enables seamless integration of different classifier types and simplifies the development
of new classifiers.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import numpy as np
from sklearn.base import BaseEstimator
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score
from sklearn.model_selection import cross_val_score

logger = logging.getLogger(__name__)


class BaseModel(ABC, BaseEstimator):
    """
    Abstract base class for all document classifiers in the Document Service.
    
    This class establishes the common interface that all classifier implementations
    must follow, including methods for training, prediction, evaluation, and serialization.
    
    All document classifier models should inherit from this class and implement
    the required abstract methods. This ensures that all classifiers maintain the
    99% accuracy requirement specified in the technical specification.
    
    Attributes:
        model_params (Dict[str, Any]): Configuration parameters for the model.
        is_fitted (bool): Flag indicating if the model has been trained.
        classes_ (np.ndarray): Array of class labels known to the classifier.
        feature_names_ (List[str]): Names of features used during training.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the base model with configuration parameters.
        
        Args:
            **kwargs: Arbitrary keyword arguments for model configuration.
                     These parameters will be passed to the underlying scikit-learn model.
        """
        self.model_params = kwargs
        self.is_fitted = False
        self.classes_ = None
        self.feature_names_ = None
        self.model_version = "1.0.0"
        self.confidence_threshold = kwargs.get('confidence_threshold', 0.8)
        
        logger.info(f"Initializing {self.__class__.__name__} with parameters: {kwargs}")
    
    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'BaseModel':
        """
        Train the model on the provided data.
        
        Args:
            X: Training data features of shape (n_samples, n_features).
            y: Target values of shape (n_samples,).
            
        Returns:
            self: The trained model instance.
        """
        pass
    
    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Predict the class labels for the provided data.
        
        Args:
            X: Data features of shape (n_samples, n_features).
            
        Returns:
            np.ndarray: Predicted class labels of shape (n_samples,).
        """
        pass
    
    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """
        Predict class probabilities for the provided data.
        
        Args:
            X: Data features of shape (n_samples, n_features).
            
        Returns:
            np.ndarray: Class probabilities of shape (n_samples, n_classes).
        """
        pass
    
    @abstractmethod
    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate the model performance on the provided data.
        
        Args:
            X: Data features of shape (n_samples, n_features).
            y: True class labels of shape (n_samples,).
            
        Returns:
            Dict[str, float]: Dictionary containing evaluation metrics including accuracy,
                             precision, recall, and F1 score. Must achieve 99% accuracy
                             as specified in the technical requirements.
        """
        pass
        
    @abstractmethod
    def save(self, filepath: str) -> None:
        """
        Save the trained model to disk.
        
        Args:
            filepath: Path where the model should be saved.
            
        Returns:
            None
        """
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, filepath: str) -> 'BaseModel':
        """
        Load a trained model from disk.
        
        Args:
            filepath: Path to the saved model.
            
        Returns:
            BaseModel: Loaded model instance.
        """
        pass
    
    def validate_input(self, X: np.ndarray, y: Optional[np.ndarray] = None) -> Tuple[np.ndarray, Optional[np.ndarray]]:
        """
        Validate input data format and structure.
        
        Args:
            X: Input features to validate.
            y: Optional target values to validate.
            
        Returns:
            Tuple containing validated X and y (if provided).
            
        Raises:
            ValueError: If input data does not meet requirements.
        """
        # Validate X
        if not isinstance(X, np.ndarray):
            try:
                X = np.array(X)
            except:
                raise ValueError("X must be convertible to a numpy array")
        
        if X.ndim != 2:
            raise ValueError(f"X must be a 2D array, got {X.ndim}D array instead")
        
        # Validate y if provided
        if y is not None:
            if not isinstance(y, np.ndarray):
                try:
                    y = np.array(y)
                except:
                    raise ValueError("y must be convertible to a numpy array")
            
            if y.ndim != 1:
                raise ValueError(f"y must be a 1D array, got {y.ndim}D array instead")
            
            if len(y) != X.shape[0]:
                raise ValueError(f"X and y must have the same number of samples. "
                               f"Got X: {X.shape[0]} samples, y: {len(y)} samples")
        
        return X, y
    
    def get_feature_importance(self) -> Optional[Dict[str, float]]:
        """
        Get feature importance scores if the model supports it.
        
        Returns:
            Optional[Dict[str, float]]: Dictionary mapping feature names to importance scores,
                                        or None if not supported by the model.
        """
        return None
    
    def cross_validate(self, X: np.ndarray, y: np.ndarray, cv: int = 5) -> Dict[str, float]:
        """
        Perform cross-validation to evaluate the model.
        
        Args:
            X: Data features of shape (n_samples, n_features).
            y: True class labels of shape (n_samples,).
            cv: Number of cross-validation folds.
            
        Returns:
            Dict[str, float]: Dictionary containing cross-validation metrics.
        """
        X, y = self.validate_input(X, y)
        
        try:
            # Perform cross-validation
            cv_scores = cross_val_score(self, X, y, cv=cv, scoring='accuracy')
            
            # Calculate metrics
            cv_metrics = {
                'cv_accuracy_mean': float(np.mean(cv_scores)),
                'cv_accuracy_std': float(np.std(cv_scores)),
                'cv_accuracy_min': float(np.min(cv_scores)),
                'cv_accuracy_max': float(np.max(cv_scores)),
                'cv_folds': cv
            }
            
            # Check if accuracy meets the 99% requirement from technical specification
            if cv_metrics['cv_accuracy_mean'] < 0.99:
                logger.warning(f"Cross-validation accuracy {cv_metrics['cv_accuracy_mean']:.4f} "
                              f"is below the required 99% threshold")
            
            return cv_metrics
        except Exception as e:
            logger.error(f"Cross-validation failed: {str(e)}")
            raise
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> Dict[str, float]:
        """
        Calculate common evaluation metrics for classification.
        
        Args:
            y_true: True class labels.
            y_pred: Predicted class labels.
            y_prob: Optional predicted probabilities for ROC AUC calculation.
            
        Returns:
            Dict[str, float]: Dictionary containing evaluation metrics.
        """
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted')
        
        metrics = {
            'accuracy': float(accuracy),
            'precision': float(precision),
            'recall': float(recall),
            'f1_score': float(f1)
        }
        
        # Calculate confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        metrics['confusion_matrix'] = cm.tolist()
        
        # Calculate ROC AUC if probabilities are provided and it's a binary classification
        if y_prob is not None:
            try:
                # For binary classification
                if y_prob.shape[1] == 2:
                    metrics['roc_auc'] = float(roc_auc_score(y_true, y_prob[:, 1]))
                # For multiclass classification
                elif y_prob.shape[1] > 2:
                    metrics['roc_auc'] = float(roc_auc_score(y_true, y_prob, multi_class='ovr', average='weighted'))
            except Exception as e:
                logger.warning(f"Could not calculate ROC AUC: {str(e)}")
        
        # Check if accuracy meets the 99% requirement from technical specification
        if accuracy < 0.99:
            logger.warning(f"Model accuracy {accuracy:.4f} is below the required 99% threshold")
        
        return metrics
    
    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """
        Get parameters for this model.
        
        Args:
            deep: If True, will return the parameters for this estimator and
                 contained subobjects that are estimators.
                 
        Returns:
            Dict[str, Any]: Parameter names mapped to their values.
        """
        return self.model_params.copy()
    
    def set_params(self, **params) -> 'BaseModel':
        """
        Set the parameters of this model.
        
        Args:
            **params: Model parameters.
            
        Returns:
            self: Model instance with updated parameters.
        """
        if not params:
            return self
        
        for key, value in params.items():
            self.model_params[key] = value
        
        return self
    
    def get_confidence_scores(self, probabilities: np.ndarray) -> np.ndarray:
        """
        Calculate confidence scores from prediction probabilities.
        
        Args:
            probabilities: Prediction probabilities of shape (n_samples, n_classes).
            
        Returns:
            np.ndarray: Confidence scores of shape (n_samples,).
        """
        # For each sample, get the highest probability as the confidence score
        return np.max(probabilities, axis=1)
    
    def is_prediction_confident(self, confidence: float) -> bool:
        """
        Determine if a prediction is confident based on the confidence threshold.
        
        Args:
            confidence: Confidence score for a prediction.
            
        Returns:
            bool: True if the prediction is confident, False otherwise.
        """
        return confidence >= self.confidence_threshold
    
    def __repr__(self) -> str:
        """
        Return a string representation of the model.
        
        Returns:
            str: String representation.
        """
        class_name = self.__class__.__name__
        params_str = ', '.join(f"{k}={v}" for k, v in self.model_params.items())
        fitted_status = "fitted" if self.is_fitted else "not fitted"
        return f"{class_name}({params_str}) - {fitted_status}"