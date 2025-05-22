#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Random Forest classifier for document classification in the Document Service.

This module implements a Random Forest classifier that extends the base model interface
and provides a complete implementation of Random Forest-based document classification
with ensemble learning, feature importance ranking, and confidence scoring.

Classes:
    RandomForestClassifier: Random Forest classifier for document classification.

Example:
    ```python
    from ..config.model_config import get_model_config
    from ..types.config import ModelConfig
    
    # Get model configuration
    config = get_model_config()
    
    # Create and train the classifier
    classifier = RandomForestClassifier(config)
    classifier.fit(X_train, y_train)
    
    # Make predictions with confidence scores
    results = classifier.predict_with_confidence(X_test)
    
    # Evaluate the classifier
    metrics = classifier.evaluate(X_test, y_test)
    ```
"""

import logging
import numpy as np
import time
from typing import Dict, List, Optional, Tuple, Union, Any, cast
from sklearn.ensemble import RandomForestClassifier as SklearnRandomForestClassifier
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix, roc_auc_score
from sklearn.model_selection import cross_val_score

from .base_model import BaseModel, T
from ..types.classification import (
    ClassificationModel,
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters,
    ClassificationMetrics
)
from ..types.documents import DocumentType
from ..types.config import ModelConfig
from ..types.errors import Result, ClassificationError

logger = logging.getLogger(__name__)


class RandomForestClassifier(BaseModel['RandomForestClassifier']):
    """
    Random Forest classifier for document classification.
    
    This class implements a Random Forest classifier that extends the base model interface
    and provides a complete implementation of Random Forest-based document classification
    with ensemble learning, feature importance ranking, and confidence scoring.
    
    Attributes:
        config (ModelConfig): Configuration parameters for the model.
        model (Optional[SklearnRandomForestClassifier]): The underlying scikit-learn Random Forest model.
        model_name (str): Name of the model for identification and logging.
        model_version (str): Version of the model for tracking and compatibility.
        classes_ (Optional[np.ndarray]): Array of class labels known to the classifier.
        trained (bool): Flag indicating whether the model has been trained.
        feature_names (Optional[List[str]]): Names of features used by the model.
        feature_importances_ (Optional[np.ndarray]): Feature importance scores.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the Random Forest classifier with configuration parameters.
        
        Args:
            config (ModelConfig): Configuration parameters for the model.
        """
        super().__init__(config)
        
        # Get Random Forest specific configuration
        rf_config = config.get('models', {}).get('random_forest', {})
        self.hyperparameters = rf_config.get('hyperparameters', {})
        
        # Initialize the scikit-learn Random Forest classifier
        self.model = SklearnRandomForestClassifier(**self.hyperparameters)
        self.feature_importances_: Optional[np.ndarray] = None
        
        logger.info(f"Initialized {self.model_name} with hyperparameters: {self.hyperparameters}")
    
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'RandomForestClassifier':
        """
        Train the Random Forest classifier on the provided data.
        
        Args:
            X (FeatureVector): Feature vectors for training.
            y (np.ndarray): Target labels for training.
            
        Returns:
            RandomForestClassifier: The trained model instance (self) for method chaining.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If training fails due to internal errors.
        """
        # Validate input data
        self._validate_input(X, y)
        
        try:
            # Record start time for performance monitoring
            start_time = time.time()
            
            # Fit the model
            self.model.fit(X, y)
            
            # Store class labels and feature importances
            self.classes_ = self.model.classes_
            self.feature_importances_ = self.model.feature_importances_
            
            # Set trained flag
            self.trained = True
            
            # Store feature names if provided
            if hasattr(X, 'columns'):
                self.feature_names = list(X.columns)
            
            # Log training results
            training_time = time.time() - start_time
            logger.info(f"{self.model_name} trained in {training_time:.2f} seconds with "
                       f"{self.model.n_estimators} trees and {X.shape[1]} features")
            
            # Log out-of-bag score if available
            if self.model.oob_score:
                logger.info(f"Out-of-bag score: {self.model.oob_score_:.4f}")
            
            return self
        except Exception as e:
            error_msg = f"Failed to train {self.model_name}: {str(e)}"
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
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        try:
            # Make predictions
            predictions = self.model.predict(X)
            
            logger.debug(f"Made {len(predictions)} predictions with {self.model_name}")
            
            return predictions
        except Exception as e:
            error_msg = f"Failed to predict with {self.model_name}: {str(e)}"
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
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        try:
            # Make probability predictions
            probabilities = self.model.predict_proba(X)
            
            logger.debug(f"Made {len(probabilities)} probability predictions with {self.model_name}")
            
            return probabilities
        except Exception as e:
            error_msg = f"Failed to predict probabilities with {self.model_name}: {str(e)}"
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
        # Validate input data
        self._validate_input(X, y, for_prediction=True)
        
        try:
            # Make predictions
            y_pred = self.predict(X)
            y_proba = self.predict_proba(X)
            
            # Calculate metrics
            accuracy = accuracy_score(y, y_pred)
            precision, recall, f1, support = precision_recall_fscore_support(y, y_pred, average=None)
            conf_matrix = confusion_matrix(y, y_pred)
            
            # Calculate ROC AUC if possible (requires binary or multiclass with probabilities)
            roc_auc = None
            try:
                if len(self.classes_) == 2:  # Binary classification
                    roc_auc = roc_auc_score(y, y_proba[:, 1])
                else:  # Multiclass classification
                    roc_auc = roc_auc_score(y, y_proba, multi_class='ovr', average='weighted')
            except Exception as e:
                logger.warning(f"Could not calculate ROC AUC: {str(e)}")
            
            # Calculate average confidence
            confidences = np.max(y_proba, axis=1)
            avg_confidence = float(np.mean(confidences))
            
            # Convert class indices to DocumentType for metrics
            precision_dict = {}
            recall_dict = {}
            f1_dict = {}
            support_dict = {}
            
            for i, class_label in enumerate(self.classes_):
                doc_type = self._convert_to_document_type(class_label)
                precision_dict[doc_type] = float(precision[i])
                recall_dict[doc_type] = float(recall[i])
                f1_dict[doc_type] = float(f1[i])
                support_dict[doc_type] = int(support[i])
            
            # Create ROC AUC dictionary if available
            roc_auc_dict = None
            if roc_auc is not None:
                if isinstance(roc_auc, float):  # Binary classification
                    pos_class = self._convert_to_document_type(self.classes_[1])
                    roc_auc_dict = {pos_class: float(roc_auc)}
                else:  # Multiclass classification with per-class AUC
                    roc_auc_dict = {}
                    for i, class_label in enumerate(self.classes_):
                        doc_type = self._convert_to_document_type(class_label)
                        roc_auc_dict[doc_type] = float(roc_auc[i]) if isinstance(roc_auc, np.ndarray) else float(roc_auc)
            
            # Create metrics dictionary
            metrics: ClassificationMetrics = {
                'accuracy': float(accuracy),
                'precision': precision_dict,
                'recall': recall_dict,
                'f1_score': f1_dict,
                'confusion_matrix': conf_matrix.tolist(),
                'support': support_dict,
                'average_confidence': avg_confidence
            }
            
            # Add ROC AUC if available
            if roc_auc_dict is not None:
                metrics['roc_auc'] = roc_auc_dict
            
            # Log evaluation results
            logger.info(f"{self.model_name} evaluation: accuracy={accuracy:.4f}, "
                       f"avg_confidence={avg_confidence:.4f}")
            
            return metrics
        except Exception as e:
            error_msg = f"Failed to evaluate {self.model_name}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores for the trained model.
        
        Returns:
            Dict[str, float]: Dictionary mapping feature names to importance scores.
            
        Raises:
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None or self.feature_importances_ is None:
            raise RuntimeError("Model has not been trained. Call fit() before getting feature importance.")
        
        # Create feature importance dictionary
        importance_dict = {}
        
        # If feature names are available, use them as keys
        if self.feature_names is not None:
            for i, feature_name in enumerate(self.feature_names):
                importance_dict[feature_name] = float(self.feature_importances_[i])
        else:
            # Otherwise, use feature indices as keys
            for i, importance in enumerate(self.feature_importances_):
                importance_dict[f"feature_{i}"] = float(importance)
        
        # Sort by importance (descending)
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        
        return importance_dict
    
    def get_oob_score(self) -> Optional[float]:
        """
        Get the out-of-bag (OOB) score for the trained model.
        
        The OOB score is the mean accuracy on the out-of-bag samples,
        which provides an unbiased estimate of the generalization error.
        
        Returns:
            Optional[float]: The OOB score if available, None otherwise.
            
        Raises:
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before getting OOB score.")
        
        # Check if OOB score is available
        if hasattr(self.model, 'oob_score_') and self.model.oob_score:
            return float(self.model.oob_score_)
        else:
            logger.warning("OOB score not available. Set oob_score=True in model hyperparameters.")
            return None
    
    def get_estimator_importances(self) -> List[np.ndarray]:
        """
        Get feature importances for each individual tree in the forest.
        
        This method provides a deeper insight into how different trees in the
        ensemble contribute to the overall feature importance.
        
        Returns:
            List[np.ndarray]: List of feature importance arrays, one per tree.
            
        Raises:
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before getting estimator importances.")
        
        # Get feature importances for each tree
        importances = []
        for tree in self.model.estimators_:
            importances.append(tree.feature_importances_)
        
        return importances
    
    def get_confidence_from_votes(self, X: FeatureVector) -> np.ndarray:
        """
        Calculate confidence scores based on voting distribution across trees.
        
        This method provides a more detailed confidence metric based on the
        agreement between individual trees in the forest, which can be more
        informative than the standard probability estimates.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Confidence scores based on voting distribution.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If the model has not been trained.
        """
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before calculating confidence.")
        
        # Get predictions from all trees
        tree_predictions = []
        for tree in self.model.estimators_:
            tree_predictions.append(tree.predict(X))
        
        # Convert to numpy array for easier manipulation
        tree_predictions = np.array(tree_predictions)
        
        # Get overall predictions
        predictions = self.predict(X)
        
        # Calculate confidence based on voting distribution
        confidences = []
        for i, pred in enumerate(predictions):
            # Count votes for the predicted class
            votes_for_pred = np.sum(tree_predictions[:, i] == pred)
            # Calculate confidence as proportion of trees that voted for the predicted class
            confidence = votes_for_pred / self.model.n_estimators
            confidences.append(confidence)
        
        return np.array(confidences)
    
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
            ValueError: If input data is invalid or incompatible with the model.
        """
        # Validate input data
        self._validate_input(X, y)
        
        try:
            # Perform cross-validation
            cv_scores = cross_val_score(self.model, X, y, cv=cv)
            
            # Calculate metrics
            cv_metrics = {
                'mean_accuracy': float(np.mean(cv_scores)),
                'std_accuracy': float(np.std(cv_scores)),
                'min_accuracy': float(np.min(cv_scores)),
                'max_accuracy': float(np.max(cv_scores)),
                'folds': cv
            }
            
            logger.info(f"Cross-validation results: mean_accuracy={cv_metrics['mean_accuracy']:.4f}, "
                       f"std_accuracy={cv_metrics['std_accuracy']:.4f}")
            
            return cv_metrics
        except Exception as e:
            error_msg = f"Failed to perform cross-validation: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def optimize_ensemble(self, X: FeatureVector, y: np.ndarray) -> 'RandomForestClassifier':
        """
        Optimize the ensemble by pruning low-performing trees.
        
        This method evaluates the performance of each tree in the ensemble and
        removes trees that perform poorly, potentially improving overall accuracy
        and reducing model size.
        
        Args:
            X (FeatureVector): Feature vectors for optimization.
            y (np.ndarray): Target labels for optimization.
            
        Returns:
            RandomForestClassifier: The optimized model instance (self) for method chaining.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If the model has not been trained.
        """
        # Validate input data and check if model is trained
        self._validate_input(X, y, for_prediction=True)
        
        if not self.trained or self.model is None:
            raise RuntimeError("Model has not been trained. Call fit() before optimizing ensemble.")
        
        try:
            # Evaluate each tree's performance
            tree_scores = []
            for i, tree in enumerate(self.model.estimators_):
                y_pred = tree.predict(X)
                score = accuracy_score(y, y_pred)
                tree_scores.append((i, score))
            
            # Sort trees by performance (descending)
            tree_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Keep only the top 80% of trees (or at least 10 trees)
            keep_count = max(int(0.8 * len(tree_scores)), 10)
            keep_indices = [idx for idx, _ in tree_scores[:keep_count]]
            
            # Create a new forest with only the selected trees
            selected_trees = [self.model.estimators_[i] for i in keep_indices]
            
            # Update the model with the selected trees
            self.model.estimators_ = selected_trees
            self.model.n_estimators = len(selected_trees)
            
            logger.info(f"Optimized ensemble: reduced from {len(tree_scores)} to {len(selected_trees)} trees")
            
            # Re-evaluate the optimized model
            metrics = self.evaluate(X, y)
            logger.info(f"Optimized ensemble performance: accuracy={metrics['accuracy']:.4f}")
            
            return self
        except Exception as e:
            error_msg = f"Failed to optimize ensemble: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
    
    def get_parameters(self) -> ModelParameters:
        """
        Get the model parameters.
        
        Returns:
            ModelParameters: Dictionary of model parameters.
        """
        params = super().get_parameters()
        
        # Add Random Forest specific parameters
        if self.trained and self.model is not None:
            params.update({
                'n_estimators': self.model.n_estimators,
                'max_depth': self.model.max_depth,
                'min_samples_split': self.model.min_samples_split,
                'min_samples_leaf': self.model.min_samples_leaf,
                'max_features': self.model.max_features,
                'bootstrap': self.model.bootstrap,
                'oob_score': self.model.oob_score,
                'criterion': self.model.criterion,
            })
            
            # Add OOB score if available
            if hasattr(self.model, 'oob_score_') and self.model.oob_score:
                params['oob_score_value'] = float(self.model.oob_score_)
        
        return params