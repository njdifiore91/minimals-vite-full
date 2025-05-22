#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Support Vector Machine (SVM) classifier for document classification.

This module implements an SVM-based document classifier that extends the base model
interface. It provides methods for training, prediction, evaluation, and feature
importance analysis for document classification tasks.

The SVM classifier supports both linear and non-linear kernels, with hyperparameter
tuning capabilities and confidence scoring for classification results.

Classes:
    SVMClassifier: SVM-based document classifier implementation.

Example:
    ```python
    from models import SVMClassifier
    from types.config import ModelConfig
    
    # Create configuration
    config = ModelConfig(
        model_path="/models/svm_classifier.pkl",
        vectorizer_path="/models/tfidf_vectorizer.pkl",
        min_confidence_threshold=0.75,
        supported_document_types=["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"],
        batch_size=32,
        max_document_size_mb=10,
        gpu_acceleration=False,
        memory_limit_mb=16384
    )
    
    # Create and train classifier
    classifier = SVMClassifier(config)
    classifier.fit(X_train, y_train)
    
    # Make predictions with confidence scores
    results = classifier.predict_with_confidence(X_test)
    
    # Evaluate model performance
    metrics = classifier.evaluate(X_test, y_test)
    ```
"""

import logging
import numpy as np
from typing import Dict, List, Optional, Tuple, Union, Any, cast
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from sklearn.inspection import permutation_importance
import time

from .base_model import BaseModel, T
from ..types.classification import (
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters,
    ClassificationMetrics,
    DocumentType
)
from ..types.config import ModelConfig
from ..types.errors import Result

logger = logging.getLogger(__name__)


class SVMClassifier(BaseModel['SVMClassifier']):
    """
    Support Vector Machine (SVM) classifier for document classification.
    
    This class extends the BaseModel abstract class to provide a complete
    implementation of SVM-based document classification with hyperparameter tuning,
    feature importance analysis, and confidence scoring.
    
    Attributes:
        config (ModelConfig): Configuration parameters for the model.
        model (Optional[SVC]): The underlying scikit-learn SVM model instance.
        model_name (str): Name of the model for identification and logging.
        model_version (str): Version of the model for tracking and compatibility.
        classes_ (Optional[np.ndarray]): Array of class labels known to the classifier.
        trained (bool): Flag indicating whether the model has been trained.
        feature_names (Optional[List[str]]): Names of features used by the model.
        kernel (str): Kernel type used by the SVM (linear, rbf, poly, sigmoid).
        is_linear (bool): Flag indicating whether the model uses a linear kernel.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the SVM classifier with configuration parameters.
        
        Args:
            config (ModelConfig): Configuration parameters for the model.
        """
        super().__init__(config)
        
        # Set SVM-specific attributes
        self.kernel = config.get('kernel', 'rbf')
        self.is_linear = self.kernel == 'linear'
        
        # Initialize SVM model with configuration parameters
        svm_params = self._get_svm_params_from_config(config)
        self.model = SVC(**svm_params)
        
        logger.info(f"Initialized {self.model_name} with {self.kernel} kernel")
    
    def _get_svm_params_from_config(self, config: ModelConfig) -> Dict[str, Any]:
        """
        Extract SVM-specific parameters from the configuration.
        
        Args:
            config (ModelConfig): Configuration parameters for the model.
            
        Returns:
            Dict[str, Any]: Dictionary of SVM parameters for scikit-learn.
        """
        # Default SVM parameters
        params = {
            'kernel': self.kernel,
            'C': config.get('C', 1.0),
            'probability': True,  # Required for predict_proba
            'random_state': config.get('random_state', 42),
            'verbose': config.get('verbose', False),
            'class_weight': config.get('class_weight', 'balanced'),
        }
        
        # Add kernel-specific parameters
        if self.kernel == 'rbf' or self.kernel == 'poly' or self.kernel == 'sigmoid':
            params['gamma'] = config.get('gamma', 'scale')
            
        if self.kernel == 'poly':
            params['degree'] = config.get('degree', 3)
            params['coef0'] = config.get('coef0', 0.0)
            
        if self.kernel == 'sigmoid':
            params['coef0'] = config.get('coef0', 0.0)
        
        return params
    
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'SVMClassifier':
        """
        Train the SVM model on the provided data.
        
        Args:
            X (FeatureVector): Feature vectors for training.
            y (np.ndarray): Target labels for training.
            
        Returns:
            SVMClassifier: The trained model instance (self) for method chaining.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If training fails due to internal errors.
        """
        # Validate input data
        self._validate_input(X, y)
        
        start_time = time.time()
        logger.info(f"Training {self.model_name} on {X.shape[0]} samples with {X.shape[1]} features")
        
        try:
            # Check if hyperparameter tuning is enabled
            if self.config.get('hyperparameter_tuning', False):
                self._perform_hyperparameter_tuning(X, y)
            else:
                # Train the model with current parameters
                self.model.fit(X, y)
            
            # Store class labels and feature count
            self.classes_ = self.model.classes_
            self.trained = True
            
            training_time = time.time() - start_time
            logger.info(f"Training completed in {training_time:.2f} seconds")
            
            # Evaluate on training data for initial performance assessment
            train_accuracy = self.model.score(X, y)
            logger.info(f"Training accuracy: {train_accuracy:.4f}")
            
            return self
            
        except Exception as e:
            error_msg = f"Failed to train {self.model_name}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def _perform_hyperparameter_tuning(self, X: FeatureVector, y: np.ndarray) -> None:
        """
        Perform hyperparameter tuning using grid search cross-validation.
        
        Args:
            X (FeatureVector): Feature vectors for training.
            y (np.ndarray): Target labels for training.
            
        Raises:
            RuntimeError: If hyperparameter tuning fails.
        """
        logger.info("Performing hyperparameter tuning with grid search")
        
        # Define parameter grid based on kernel type
        if self.kernel == 'linear':
            param_grid = {
                'C': [0.1, 1, 10, 100],
                'class_weight': ['balanced', None],
            }
        elif self.kernel == 'rbf':
            param_grid = {
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.1, 0.01, 0.001],
                'class_weight': ['balanced', None],
            }
        elif self.kernel == 'poly':
            param_grid = {
                'C': [0.1, 1, 10],
                'degree': [2, 3, 4],
                'gamma': ['scale', 'auto', 0.1, 0.01],
                'class_weight': ['balanced', None],
            }
        else:  # sigmoid
            param_grid = {
                'C': [0.1, 1, 10, 100],
                'gamma': ['scale', 'auto', 0.1, 0.01, 0.001],
                'coef0': [0.0, 0.1, 0.5],
                'class_weight': ['balanced', None],
            }
        
        # Create grid search with cross-validation
        cv_folds = self.config.get('cv_folds', 5)
        grid_search = GridSearchCV(
            estimator=self.model,
            param_grid=param_grid,
            cv=cv_folds,
            scoring='accuracy',
            n_jobs=self.config.get('n_jobs', -1),
            verbose=self.config.get('verbose', 0)
        )
        
        # Perform grid search
        try:
            grid_search.fit(X, y)
            
            # Update model with best parameters
            self.model = grid_search.best_estimator_
            
            logger.info(f"Best parameters found: {grid_search.best_params_}")
            logger.info(f"Best cross-validation accuracy: {grid_search.best_score_:.4f}")
            
        except Exception as e:
            error_msg = f"Hyperparameter tuning failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def predict(self, X: FeatureVector) -> np.ndarray:
        """
        Predict class labels for the provided data.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Predicted class labels.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before prediction.")
        
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        try:
            # Make predictions
            predictions = self.model.predict(X)
            return predictions
            
        except Exception as e:
            error_msg = f"Prediction failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def predict_proba(self, X: FeatureVector) -> np.ndarray:
        """
        Predict class probabilities for the provided data.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Predicted class probabilities, where each row sums to 1.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before prediction.")
        
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        try:
            # Make probability predictions
            probabilities = self.model.predict_proba(X)
            return probabilities
            
        except Exception as e:
            error_msg = f"Probability prediction failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def evaluate(self, X: FeatureVector, y: np.ndarray) -> ClassificationMetrics:
        """
        Evaluate the model on the provided data.
        
        Args:
            X (FeatureVector): Feature vectors for evaluation.
            y (np.ndarray): True target labels for evaluation.
            
        Returns:
            ClassificationMetrics: Dictionary of evaluation metrics including accuracy,
                precision, recall, F1 score, and confusion matrix.
                
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If evaluation fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None or self.classes_ is None:
            raise RuntimeError("Model has not been trained. Call fit() before evaluation.")
        
        # Validate input data
        self._validate_input(X, y, for_prediction=True)
        
        try:
            # Make predictions
            y_pred = self.predict(X)
            y_proba = self.predict_proba(X)
            
            # Calculate accuracy
            accuracy = accuracy_score(y, y_pred)
            
            # Calculate precision, recall, and F1 score for each class
            precision, recall, f1, support = precision_recall_fscore_support(
                y, y_pred, average=None, labels=self.classes_
            )
            
            # Calculate confusion matrix
            cm = confusion_matrix(y, y_pred, labels=self.classes_)
            
            # Calculate average confidence score
            avg_confidence = self._calculate_average_confidence(y_proba)
            
            # Create metrics dictionary
            metrics: ClassificationMetrics = {
                'accuracy': float(accuracy),
                'precision': {str(self.classes_[i]): float(precision[i]) for i in range(len(self.classes_))},
                'recall': {str(self.classes_[i]): float(recall[i]) for i in range(len(self.classes_))},
                'f1_score': {str(self.classes_[i]): float(f1[i]) for i in range(len(self.classes_))},
                'confusion_matrix': cm.tolist(),
                'support': {str(self.classes_[i]): int(support[i]) for i in range(len(self.classes_))},
                'average_confidence': float(avg_confidence)
            }
            
            # Add feature importance if available
            if self.feature_names is not None:
                feature_importance = self.get_feature_importance(X, y)
                metrics['feature_importance'] = feature_importance
            
            return metrics
            
        except Exception as e:
            error_msg = f"Evaluation failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def _calculate_average_confidence(self, probabilities: np.ndarray) -> float:
        """
        Calculate the average confidence score across all predictions.
        
        Args:
            probabilities (np.ndarray): Predicted class probabilities.
            
        Returns:
            float: Average confidence score.
        """
        # For each sample, get the maximum probability (confidence in the predicted class)
        max_probabilities = np.max(probabilities, axis=1)
        return float(np.mean(max_probabilities))
    
    def get_feature_importance(self, X: FeatureVector, y: np.ndarray) -> Dict[str, float]:
        """
        Calculate feature importance scores for the trained model.
        
        For linear kernels, uses the absolute values of the coefficients.
        For non-linear kernels, uses permutation importance.
        
        Args:
            X (FeatureVector): Feature vectors for importance calculation.
            y (np.ndarray): True target labels.
            
        Returns:
            Dict[str, float]: Dictionary mapping feature names to importance scores.
            
        Raises:
            RuntimeError: If the model has not been trained.
            ValueError: If feature names are not available.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before getting feature importance.")
        
        if self.feature_names is None:
            raise ValueError("Feature names are not available. Set feature_names before getting feature importance.")
        
        feature_importance: Dict[str, float] = {}
        
        try:
            # For linear kernel, use coefficients as feature importance
            if self.is_linear:
                # Get coefficients from the model
                if hasattr(self.model, 'coef_'):
                    # For binary classification, coef_ is a 2D array with shape (1, n_features)
                    # For multiclass, it's (n_classes, n_features)
                    coef = self.model.coef_
                    
                    # For multiclass, average the absolute coefficients across all classes
                    if coef.shape[0] > 1:  # multiclass
                        importance_scores = np.mean(np.abs(coef), axis=0)
                    else:  # binary
                        importance_scores = np.abs(coef[0])
                    
                    # Create dictionary of feature importances
                    for i, feature_name in enumerate(self.feature_names):
                        feature_importance[feature_name] = float(importance_scores[i])
                else:
                    logger.warning("Coefficients not available for feature importance calculation")
            else:
                # For non-linear kernels, use permutation importance
                logger.info("Calculating permutation importance for non-linear kernel")
                
                # Calculate permutation importance
                perm_importance = permutation_importance(
                    self.model, X, y,
                    n_repeats=10,
                    random_state=self.config.get('random_state', 42),
                    n_jobs=self.config.get('n_jobs', -1)
                )
                
                # Create dictionary of feature importances
                for i, feature_name in enumerate(self.feature_names):
                    feature_importance[feature_name] = float(perm_importance.importances_mean[i])
            
            # Normalize importance scores to sum to 1.0
            total_importance = sum(feature_importance.values())
            if total_importance > 0:
                for feature_name in feature_importance:
                    feature_importance[feature_name] /= total_importance
            
            return feature_importance
            
        except Exception as e:
            error_msg = f"Feature importance calculation failed: {str(e)}"
            logger.error(error_msg)
            # Return empty dict instead of raising exception
            return {}
    
    def cross_validate(self, X: FeatureVector, y: np.ndarray, cv: int = 5) -> Dict[str, float]:
        """
        Perform cross-validation to estimate model performance.
        
        Args:
            X (FeatureVector): Feature vectors for cross-validation.
            y (np.ndarray): Target labels for cross-validation.
            cv (int): Number of cross-validation folds.
            
        Returns:
            Dict[str, float]: Dictionary of cross-validation metrics.
            
        Raises:
            ValueError: If input data is invalid.
            RuntimeError: If cross-validation fails.
        """
        # Validate input data
        self._validate_input(X, y)
        
        try:
            # Perform cross-validation
            cv_scores = cross_val_score(
                self.model, X, y, cv=cv, scoring='accuracy',
                n_jobs=self.config.get('n_jobs', -1)
            )
            
            # Calculate metrics
            cv_metrics = {
                'mean_accuracy': float(np.mean(cv_scores)),
                'std_accuracy': float(np.std(cv_scores)),
                'min_accuracy': float(np.min(cv_scores)),
                'max_accuracy': float(np.max(cv_scores)),
                'cv_folds': cv
            }
            
            return cv_metrics
            
        except Exception as e:
            error_msg = f"Cross-validation failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def set_feature_names(self, feature_names: List[str]) -> 'SVMClassifier':
        """
        Set the feature names for the model.
        
        Args:
            feature_names (List[str]): List of feature names.
            
        Returns:
            SVMClassifier: Self for method chaining.
            
        Raises:
            ValueError: If feature names length doesn't match model expectations.
        """
        if self.trained and self.model is not None and hasattr(self.model, 'coef_'):
            expected_features = self.model.coef_.shape[1]
            if len(feature_names) != expected_features:
                raise ValueError(
                    f"Feature names length ({len(feature_names)}) doesn't match "
                    f"model's expected features ({expected_features})"
                )
        
        self.feature_names = feature_names
        return self
    
    def get_support_vectors(self) -> Optional[np.ndarray]:
        """
        Get the support vectors from the trained model.
        
        Returns:
            Optional[np.ndarray]: Array of support vectors or None if not available.
            
        Raises:
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before getting support vectors.")
        
        if hasattr(self.model, 'support_vectors_'):
            return self.model.support_vectors_
        
        return None
    
    def get_parameters(self) -> ModelParameters:
        """
        Get the model parameters.
        
        Returns:
            ModelParameters: Dictionary of model parameters.
        """
        params = super().get_parameters()
        
        # Add SVM-specific parameters
        if self.model is not None:
            params.update({
                'kernel': self.kernel,
                'is_linear': self.is_linear,
                'n_support_vectors': len(self.model.support_vectors_) if hasattr(self.model, 'support_vectors_') else 0,
                'n_classes': len(self.classes_) if self.classes_ is not None else 0,
            })
        
        return params
    
    def calibrate_probabilities(self, X: FeatureVector, y: np.ndarray) -> 'SVMClassifier':
        """
        Calibrate probability estimates for better confidence scoring.
        
        SVM probability estimates can sometimes be poorly calibrated.
        This method uses Platt scaling to improve probability calibration.
        
        Args:
            X (FeatureVector): Calibration data features.
            y (np.ndarray): Calibration data labels.
            
        Returns:
            SVMClassifier: Self for method chaining.
            
        Raises:
            RuntimeError: If the model has not been trained.
            ValueError: If input data is invalid.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before calibration.")
        
        # Validate input data
        self._validate_input(X, y)
        
        try:
            from sklearn.calibration import CalibratedClassifierCV
            
            # Create a calibrated classifier using the trained model
            calibrated_classifier = CalibratedClassifierCV(
                base_estimator=self.model,
                cv='prefit',  # Use the already fitted model
                method='sigmoid'  # Platt scaling
            )
            
            # Fit the calibrator
            calibrated_classifier.fit(X, y)
            
            # Replace the model with the calibrated version
            self.model = calibrated_classifier
            
            logger.info(f"Probability calibration completed for {self.model_name}")
            return self
            
        except Exception as e:
            error_msg = f"Probability calibration failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def optimize_threshold(self, X: FeatureVector, y: np.ndarray) -> float:
        """
        Optimize the confidence threshold for classification decisions.
        
        This method finds the optimal threshold that maximizes F1 score
        on the provided validation data.
        
        Args:
            X (FeatureVector): Validation data features.
            y (np.ndarray): Validation data labels.
            
        Returns:
            float: Optimized confidence threshold.
            
        Raises:
            RuntimeError: If the model has not been trained.
            ValueError: If input data is invalid.
        """
        if not self.trained or self.model is None or self.classes_ is None:
            raise RuntimeError("Model has not been trained. Call fit() before threshold optimization.")
        
        # Validate input data
        self._validate_input(X, y, for_prediction=True)
        
        try:
            from sklearn.metrics import f1_score
            
            # Get probability predictions
            probabilities = self.predict_proba(X)
            
            # Try different thresholds
            thresholds = np.arange(0.5, 1.0, 0.01)
            best_threshold = 0.5
            best_f1 = 0.0
            
            for threshold in thresholds:
                # For each sample, predict the class with highest probability
                # if that probability exceeds the threshold, otherwise predict
                # the class that requires review
                y_pred = np.zeros_like(y)
                
                for i in range(len(y)):
                    max_prob_idx = np.argmax(probabilities[i])
                    max_prob = probabilities[i][max_prob_idx]
                    
                    if max_prob >= threshold:
                        y_pred[i] = self.classes_[max_prob_idx]
                    else:
                        # If below threshold, assign to most common class
                        # This is a simplification; in practice, these would be flagged for review
                        y_pred[i] = self.classes_[max_prob_idx]
                
                # Calculate F1 score for this threshold
                f1 = f1_score(y, y_pred, average='weighted')
                
                # Update best threshold if F1 score improves
                if f1 > best_f1:
                    best_f1 = f1
                    best_threshold = threshold
            
            logger.info(f"Optimized confidence threshold: {best_threshold:.2f} (F1: {best_f1:.4f})")
            
            # Update the confidence threshold in the config
            self.config['min_confidence_threshold'] = best_threshold
            
            return best_threshold
            
        except Exception as e:
            error_msg = f"Threshold optimization failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e