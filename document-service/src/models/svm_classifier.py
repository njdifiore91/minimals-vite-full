#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Support Vector Machine (SVM) Classifier for Document Classification.

This module implements an SVM classifier for document classification in the Document Service.
It extends the base model interface and provides a complete implementation of SVM-based
document classification with hyperparameter tuning, feature importance analysis, and confidence scoring.

The SVM classifier uses kernel methods to achieve high accuracy in document classification,
particularly for high-dimensional feature spaces typical in text classification. It provides
confidence scores based on distance to the decision boundary and includes methods for
hyperparameter tuning and cross-validation.

Example usage:
    # Initialize the classifier with default parameters
    classifier = SVMClassifier()
    
    # Train the classifier on document features
    classifier.fit(features, labels)
    
    # Predict document types with confidence scores
    predictions = classifier.predict(features)
    probabilities = classifier.predict_proba(features)
    
    # Get feature importance ranking
    importance = classifier.get_feature_importance()
    
    # Optimize hyperparameters
    classifier.optimize_hyperparameters(features, labels)
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

import numpy as np
import pandas as pd
from sklearn.svm import SVC
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from sklearn.inspection import permutation_importance

# Import types
from ..types.classification import (
    ClassificationModel,
    ConfidenceScore,
    DocumentType,
    FeatureVector,
    ModelParameters,
    ClassificationResult,
    ClassificationMetrics
)
from ..types.errors import Result, ServiceError, ErrorCategory

# Set up logging
logger = logging.getLogger(__name__)


class SVMClassifier(ClassificationModel):
    """Support Vector Machine classifier for document classification.
    
    This class implements an SVM classifier for document classification,
    extending the base model interface. It provides methods for training, prediction,
    confidence scoring, feature importance analysis, and hyperparameter tuning.
    
    The classifier uses scikit-learn's SVC as the underlying implementation
    and enhances it with additional functionality specific to document classification
    requirements.
    """
    
    def __init__(self, params: Optional[ModelParameters] = None):
        """Initialize the SVM classifier.
        
        Args:
            params: Optional dictionary of model parameters. If None, default parameters are used.
        """
        self.params = params or self._get_default_params()
        self.model = self._create_model()
        self.feature_names: List[str] = []
        self.class_mapping: Dict[int, DocumentType] = {}
        self.inverse_class_mapping: Dict[DocumentType, int] = {}
        self.is_fitted = False
        self.version = "1.0.0"
        self.last_trained = None
        self.feature_importances_ = None
        self.training_accuracy = None
        
        logger.info(f"Initialized SVMClassifier with parameters: {self.params}")
    
    def _get_default_params(self) -> ModelParameters:
        """Get default parameters for the SVM classifier.
        
        Returns:
            Dictionary of default model parameters
        """
        return {
            "C": 1.0,              # Regularization parameter
            "kernel": "rbf",      # Kernel type (rbf, linear, poly, sigmoid)
            "degree": 3,          # Degree of polynomial kernel (if kernel='poly')
            "gamma": "scale",     # Kernel coefficient for 'rbf', 'poly' and 'sigmoid'
            "coef0": 0.0,         # Independent term in kernel function (for 'poly' and 'sigmoid')
            "shrinking": True,    # Whether to use the shrinking heuristic
            "probability": True,  # Whether to enable probability estimates
            "tol": 1e-3,          # Tolerance for stopping criterion
            "cache_size": 200,    # Size of kernel cache
            "class_weight": "balanced",  # Class weights
            "verbose": False,     # Enable verbose output
            "max_iter": -1,       # Hard limit on iterations within solver (-1 means no limit)
            "decision_function_shape": "ovr",  # Decision function shape ('ovo', 'ovr')
            "break_ties": False,  # Whether to break ties according to confidence values
            "random_state": 42    # Random seed for reproducibility
        }
    
    def _create_model(self) -> SVC:
        """Create a scikit-learn SVC with the specified parameters.
        
        Returns:
            Initialized scikit-learn SVC
        """
        return SVC(**self.params)
    
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'SVMClassifier':
        """Fit the SVM classifier to the training data.
        
        Args:
            X: Feature vectors for training
            y: Target labels for training (can be numeric indices or DocumentType instances)
            
        Returns:
            Self for method chaining
            
        Raises:
            ValueError: If input data is invalid
        """
        if X.shape[0] != len(y):
            raise ValueError(f"Number of samples in X ({X.shape[0]}) does not match length of y ({len(y)})")
        
        start_time = time.time()
        logger.info(f"Training SVMClassifier on {X.shape[0]} samples with {X.shape[1]} features")
        
        # Convert DocumentType instances to numeric indices if needed
        if isinstance(y[0], DocumentType):
            # Create class mapping
            unique_classes = list(set(y))
            self.class_mapping = {i: cls for i, cls in enumerate(unique_classes)}
            self.inverse_class_mapping = {cls: i for i, cls in enumerate(unique_classes)}
            
            # Convert to numeric indices
            y_numeric = np.array([self.inverse_class_mapping[cls] for cls in y])
        else:
            # Assume y already contains numeric indices
            y_numeric = y
            
            # Create default class mapping if not already set
            if not self.class_mapping:
                unique_classes = list(set(y_numeric))
                self.class_mapping = {i: DocumentType(f"CLASS_{i}") for i in unique_classes}
                self.inverse_class_mapping = {v: k for k, v in self.class_mapping.items()}
        
        # Fit the model
        self.model.fit(X, y_numeric)
        
        # Update model state
        self.is_fitted = True
        self.last_trained = datetime.now()
        
        # Calculate training accuracy
        y_pred = self.model.predict(X)
        self.training_accuracy = accuracy_score(y_numeric, y_pred)
        
        elapsed_time = time.time() - start_time
        logger.info(f"SVMClassifier training completed in {elapsed_time:.2f} seconds")
        logger.info(f"Training accuracy: {self.training_accuracy:.4f}")
        
        return self
    
    def predict(self, X: FeatureVector) -> np.ndarray:
        """Predict class labels for samples in X.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Predicted class labels (as DocumentType instances)
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before predict().")
        
        # Get numeric predictions from the model
        y_pred_numeric = self.model.predict(X)
        
        # Convert numeric predictions to DocumentType instances
        y_pred = np.array([self.class_mapping[idx] for idx in y_pred_numeric])
        
        return y_pred
    
    def predict_proba(self, X: FeatureVector) -> np.ndarray:
        """Predict class probabilities for samples in X.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Class probabilities for each sample
            
        Raises:
            ValueError: If the model has not been trained or probability=False
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before predict_proba().")
        
        if not self.params.get("probability", True):
            raise ValueError("SVM model was trained with probability=False. Cannot predict probabilities.")
        
        # Get probability predictions from the model
        probas = self.model.predict_proba(X)
        
        return probas
    
    def predict_with_confidence(self, X: FeatureVector) -> List[Tuple[DocumentType, ConfidenceScore]]:
        """Predict class labels with confidence scores for samples in X.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            List of tuples containing (predicted class, confidence score)
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before predict_with_confidence().")
        
        # Get numeric predictions from the model
        y_pred_numeric = self.model.predict(X)
        
        # Get confidence scores
        if self.params.get("probability", True):
            # If probability=True, use predict_proba
            probas = self.model.predict_proba(X)
            confidences = np.max(probas, axis=1)
        else:
            # If probability=False, use decision_function
            # For binary classification, decision_function returns a 1D array
            # For multiclass, it returns a 2D array with shape (n_samples, n_classes)
            decision_values = self.model.decision_function(X)
            
            if decision_values.ndim == 1:
                # Binary classification
                # Convert decision values to confidence scores (0 to 1 range)
                # Using sigmoid function: 1 / (1 + exp(-x))
                confidences = 1.0 / (1.0 + np.exp(-np.abs(decision_values)))
            else:
                # Multiclass classification
                # For each sample, get the maximum decision value
                # and convert to confidence score
                max_decision_values = np.max(decision_values, axis=1)
                confidences = 1.0 / (1.0 + np.exp(-max_decision_values))
        
        # Create result list
        results = []
        for i, pred_idx in enumerate(y_pred_numeric):
            # Get predicted class and its confidence
            pred_class = self.class_mapping[pred_idx]
            confidence = confidences[i]
            
            # Create confidence score
            confidence_score = ConfidenceScore(confidence)
            
            # Add to results
            results.append((pred_class, confidence_score))
        
        return results
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance ranking.
        
        For SVM, feature importance is not directly available like in tree-based models.
        This method uses permutation importance to estimate feature importance.
        
        Returns:
            Dictionary mapping feature names to importance scores
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_feature_importance().")
        
        # If feature importances have already been calculated, return them
        if self.feature_importances_ is not None:
            # Create dictionary mapping feature names to importance scores
            if self.feature_names and len(self.feature_names) == len(self.feature_importances_):
                # If feature names are available, use them
                importance_dict = {name: float(importance) for name, importance in zip(self.feature_names, self.feature_importances_)}
            else:
                # Otherwise, use feature indices
                importance_dict = {f"feature_{i}": float(importance) for i, importance in enumerate(self.feature_importances_)}
            
            # Sort by importance (descending)
            importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
            
            return importance_dict
        
        logger.warning("Feature importance for SVM requires a separate dataset. Returning empty dictionary.")
        return {}
    
    def calculate_feature_importance(self, X: FeatureVector, y: np.ndarray, n_repeats: int = 10, random_state: int = 42) -> Dict[str, float]:
        """Calculate feature importance using permutation importance.
        
        This method calculates feature importance by measuring how much model performance
        decreases when a feature is randomly permuted. It requires a separate dataset
        (typically the validation set) to calculate importance.
        
        Args:
            X: Feature vectors for importance calculation
            y: Target labels for importance calculation
            n_repeats: Number of times to permute each feature
            random_state: Random seed for reproducibility
            
        Returns:
            Dictionary mapping feature names to importance scores
            
        Raises:
            ValueError: If the model has not been trained or input data is invalid
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before calculate_feature_importance().")
        
        if X.shape[0] != len(y):
            raise ValueError(f"Number of samples in X ({X.shape[0]}) does not match length of y ({len(y)})")
        
        # Convert DocumentType instances to numeric indices if needed
        if isinstance(y[0], DocumentType):
            y_numeric = np.array([self.inverse_class_mapping.get(cls, -1) for cls in y])
            # Check for unknown classes
            if -1 in y_numeric:
                raise ValueError("Data contains classes not seen during training")
        else:
            # Assume y already contains numeric indices
            y_numeric = y
        
        logger.info(f"Calculating permutation importance with {n_repeats} repeats")
        start_time = time.time()
        
        # Calculate permutation importance
        result = permutation_importance(
            self.model, X, y_numeric, n_repeats=n_repeats, random_state=random_state
        )
        
        # Store feature importances
        self.feature_importances_ = result.importances_mean
        
        # Create dictionary mapping feature names to importance scores
        if self.feature_names and len(self.feature_names) == len(self.feature_importances_):
            # If feature names are available, use them
            importance_dict = {name: float(importance) for name, importance in zip(self.feature_names, self.feature_importances_)}
        else:
            # Otherwise, use feature indices
            importance_dict = {f"feature_{i}": float(importance) for i, importance in enumerate(self.feature_importances_)}
        
        # Sort by importance (descending)
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        
        elapsed_time = time.time() - start_time
        logger.info(f"Permutation importance calculation completed in {elapsed_time:.2f} seconds")
        
        return importance_dict
    
    def get_decision_function(self, X: FeatureVector) -> np.ndarray:
        """Get decision function values for samples in X.
        
        The decision function gives the signed distance to the hyperplane for each sample.
        For binary classification, positive values indicate the first class, negative values
        indicate the second class. For multiclass, the decision function is calculated for
        each class against the rest (for 'ovr') or for each pair of classes (for 'ovo').
        
        Args:
            X: Feature vectors to get decision function values for
            
        Returns:
            Decision function values
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_decision_function().")
        
        # Get decision function values from the model
        decision_values = self.model.decision_function(X)
        
        return decision_values
    
    def get_support_vectors(self) -> Tuple[np.ndarray, List[int]]:
        """Get support vectors and their indices.
        
        Support vectors are the samples that lie closest to the decision boundary.
        They are the most difficult to classify and have the most influence on the
        position of the hyperplane.
        
        Returns:
            Tuple containing (support vectors, support vector indices)
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_support_vectors().")
        
        # Get support vectors and their indices from the model
        support_vectors = self.model.support_vectors_
        support_indices = self.model.support_
        
        return support_vectors, support_indices.tolist()
    
    def get_kernel_matrix(self, X: FeatureVector) -> np.ndarray:
        """Get kernel matrix for samples in X.
        
        The kernel matrix contains the kernel values between each pair of samples.
        This is useful for understanding the similarity structure of the data in
        the feature space induced by the kernel.
        
        Args:
            X: Feature vectors to get kernel matrix for
            
        Returns:
            Kernel matrix with shape (n_samples, n_samples)
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_kernel_matrix().")
        
        # Get kernel function from the model
        kernel = self.model._get_kernel()
        
        # Calculate kernel matrix
        K = kernel(X, X)
        
        return K
    
    def optimize_hyperparameters(self, X: FeatureVector, y: np.ndarray, 
                               param_grid: Optional[Dict[str, List[Any]]] = None,
                               cv: int = 5, scoring: str = 'accuracy',
                               n_iter: int = 10, method: str = 'grid') -> Dict[str, Any]:
        """Optimize hyperparameters using cross-validation.
        
        Args:
            X: Feature vectors for optimization
            y: Target labels for optimization
            param_grid: Parameter grid to search. If None, a default grid is used.
            cv: Number of cross-validation folds
            scoring: Scoring metric to use
            n_iter: Number of iterations for randomized search
            method: Search method ('grid' or 'random')
            
        Returns:
            Dictionary with optimization results
            
        Raises:
            ValueError: If input data is invalid or method is unknown
        """
        if X.shape[0] != len(y):
            raise ValueError(f"Number of samples in X ({X.shape[0]}) does not match length of y ({len(y)})")
        
        if method not in ['grid', 'random']:
            raise ValueError(f"Unknown search method: {method}. Use 'grid' or 'random'.")
        
        start_time = time.time()
        logger.info(f"Optimizing SVMClassifier parameters using {method} search with {cv}-fold cross-validation")
        
        # Convert DocumentType instances to numeric indices if needed
        if isinstance(y[0], DocumentType):
            # Create class mapping
            unique_classes = list(set(y))
            self.class_mapping = {i: cls for i, cls in enumerate(unique_classes)}
            self.inverse_class_mapping = {cls: i for i, cls in enumerate(unique_classes)}
            
            # Convert to numeric indices
            y_numeric = np.array([self.inverse_class_mapping[cls] for cls in y])
        else:
            # Assume y already contains numeric indices
            y_numeric = y
        
        # Define default parameter grid if not provided
        if param_grid is None:
            param_grid = {
                "C": [0.1, 1.0, 10.0, 100.0],
                "kernel": ["linear", "rbf", "poly", "sigmoid"],
                "gamma": ["scale", "auto", 0.1, 0.01, 0.001],
                "degree": [2, 3, 4],  # Only relevant for poly kernel
                "class_weight": ["balanced", None]
            }
        
        # Create base model for search
        base_model = SVC(probability=True, random_state=42)
        
        # Perform parameter search
        if method == 'grid':
            search = GridSearchCV(base_model, param_grid, cv=cv, scoring=scoring, n_jobs=-1)
        else:  # method == 'random'
            search = RandomizedSearchCV(base_model, param_grid, n_iter=n_iter, cv=cv, scoring=scoring, n_jobs=-1, random_state=42)
        
        # Fit the search
        search.fit(X, y_numeric)
        
        # Get best parameters and score
        best_params = search.best_params_
        best_score = search.best_score_
        
        # Update model with best parameters
        self.params.update(best_params)
        self.model = self._create_model()
        
        # Fit the model with best parameters
        self.fit(X, y_numeric)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Parameter optimization completed in {elapsed_time:.2f} seconds")
        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Best cross-validation score: {best_score:.4f}")
        
        # Return optimization results
        return {
            "best_params": best_params,
            "best_score": best_score,
            "cv_results": search.cv_results_,
            "elapsed_time": elapsed_time
        }
    
    def evaluate(self, X: FeatureVector, y: np.ndarray) -> ClassificationMetrics:
        """Evaluate the classifier on test data.
        
        Args:
            X: Feature vectors for testing
            y: True labels for testing
            
        Returns:
            Classification metrics including accuracy, precision, recall, and F1 score
            
        Raises:
            ValueError: If the model has not been trained or input data is invalid
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before evaluate().")
        
        if X.shape[0] != len(y):
            raise ValueError(f"Number of samples in X ({X.shape[0]}) does not match length of y ({len(y)})")
        
        # Convert DocumentType instances to numeric indices if needed
        if isinstance(y[0], DocumentType):
            y_numeric = np.array([self.inverse_class_mapping.get(cls, -1) for cls in y])
            # Check for unknown classes
            if -1 in y_numeric:
                raise ValueError("Test data contains classes not seen during training")
        else:
            # Assume y already contains numeric indices
            y_numeric = y
        
        # Get predictions
        y_pred_numeric = self.model.predict(X)
        
        # Calculate metrics
        accuracy = accuracy_score(y_numeric, y_pred_numeric)
        precision, recall, f1, _ = precision_recall_fscore_support(y_numeric, y_pred_numeric, average=None)
        
        # Create metrics dictionaries
        precision_dict = {}
        recall_dict = {}
        f1_dict = {}
        
        for i, class_idx in enumerate(np.unique(y_numeric)):
            class_type = self.class_mapping[class_idx]
            precision_dict[class_type] = float(precision[i])
            recall_dict[class_type] = float(recall[i])
            f1_dict[class_type] = float(f1[i])
        
        # Create confusion matrix
        from sklearn.metrics import confusion_matrix
        cm = confusion_matrix(y_numeric, y_pred_numeric)
        
        # Create ClassificationMetrics object
        metrics = ClassificationMetrics(
            accuracy=accuracy,
            precision=precision_dict,
            recall=recall_dict,
            f1_score=f1_dict,
            confusion_matrix=cm
        )
        
        return metrics
    
    def cross_validate(self, X: FeatureVector, y: np.ndarray, cv: int = 5, scoring: str = 'accuracy') -> Dict[str, List[float]]:
        """Perform cross-validation on the classifier.
        
        Args:
            X: Feature vectors for cross-validation
            y: Target labels for cross-validation
            cv: Number of cross-validation folds
            scoring: Scoring metric to use
            
        Returns:
            Dictionary with cross-validation results
            
        Raises:
            ValueError: If input data is invalid
        """
        if X.shape[0] != len(y):
            raise ValueError(f"Number of samples in X ({X.shape[0]}) does not match length of y ({len(y)})")
        
        logger.info(f"Performing {cv}-fold cross-validation with scoring metric '{scoring}'")
        
        # Convert DocumentType instances to numeric indices if needed
        if isinstance(y[0], DocumentType):
            # Create class mapping
            unique_classes = list(set(y))
            self.class_mapping = {i: cls for i, cls in enumerate(unique_classes)}
            self.inverse_class_mapping = {cls: i for i, cls in enumerate(unique_classes)}
            
            # Convert to numeric indices
            y_numeric = np.array([self.inverse_class_mapping[cls] for cls in y])
        else:
            # Assume y already contains numeric indices
            y_numeric = y
        
        # Create model for cross-validation
        model = SVC(**self.params)
        
        # Perform cross-validation
        from sklearn.model_selection import cross_validate
        cv_results = cross_validate(
            model, X, y_numeric, cv=cv, scoring=scoring, return_train_score=True
        )
        
        # Convert results to lists
        results = {
            "test_score": cv_results["test_score"].tolist(),
            "train_score": cv_results["train_score"].tolist(),
            "fit_time": cv_results["fit_time"].tolist(),
            "score_time": cv_results["score_time"].tolist()
        }
        
        # Log results
        logger.info(f"Cross-validation results:")
        logger.info(f"  Mean test score: {np.mean(results['test_score']):.4f}")
        logger.info(f"  Mean train score: {np.mean(results['train_score']):.4f}")
        logger.info(f"  Mean fit time: {np.mean(results['fit_time']):.4f} seconds")
        
        return results
    
    def set_feature_names(self, feature_names: List[str]) -> None:
        """Set feature names for the classifier.
        
        Args:
            feature_names: List of feature names
            
        Raises:
            ValueError: If feature names length doesn't match model expectations
        """
        if self.is_fitted and hasattr(self.model, 'n_features_in_') and len(feature_names) != self.model.n_features_in_:
            raise ValueError(f"Number of feature names ({len(feature_names)}) does not match model's expected number of features ({self.model.n_features_in_})")
        
        self.feature_names = feature_names
        logger.debug(f"Set {len(feature_names)} feature names for SVMClassifier")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the classifier.
        
        Returns:
            Dictionary with classifier information
        """
        info = {
            "model_type": "svm",
            "version": self.version,
            "parameters": self.params,
            "is_fitted": self.is_fitted,
            "feature_count": len(self.feature_names) if self.feature_names else None,
            "class_count": len(self.class_mapping) if self.class_mapping else None,
            "classes": [str(cls) for cls in self.class_mapping.values()] if self.class_mapping else None,
        }
        
        # Add training information if available
        if self.is_fitted:
            info.update({
                "last_trained": self.last_trained.isoformat() if self.last_trained else None,
                "training_accuracy": self.training_accuracy,
                "n_support": self.model.n_support_.tolist() if hasattr(self.model, 'n_support_') else None,
                "n_features": self.model.n_features_in_ if hasattr(self.model, 'n_features_in_') else None,
                "n_classes": self.model.n_classes_ if hasattr(self.model, 'n_classes_') else None,
            })
        
        return info
    
    def get_confidence_calibration(self, X: FeatureVector, y: np.ndarray) -> Dict[str, List[float]]:
        """Calculate confidence calibration metrics.
        
        This method assesses how well the model's confidence scores align with
        its actual accuracy, which is important for reliable decision-making.
        
        Args:
            X: Feature vectors for calibration assessment
            y: True labels for calibration assessment
            
        Returns:
            Dictionary with calibration metrics
            
        Raises:
            ValueError: If the model has not been trained or input data is invalid
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_confidence_calibration().")
        
        if not self.params.get("probability", True):
            raise ValueError("SVM model was trained with probability=False. Cannot calculate confidence calibration.")
        
        if X.shape[0] != len(y):
            raise ValueError(f"Number of samples in X ({X.shape[0]}) does not match length of y ({len(y)})")
        
        # Convert DocumentType instances to numeric indices if needed
        if isinstance(y[0], DocumentType):
            y_numeric = np.array([self.inverse_class_mapping.get(cls, -1) for cls in y])
            # Check for unknown classes
            if -1 in y_numeric:
                raise ValueError("Test data contains classes not seen during training")
        else:
            # Assume y already contains numeric indices
            y_numeric = y
        
        # Get predictions and probabilities
        y_pred_numeric = self.model.predict(X)
        probas = self.model.predict_proba(X)
        
        # Get max probability for each prediction (confidence)
        confidences = np.max(probas, axis=1)
        
        # Check if predictions are correct
        correct = (y_pred_numeric == y_numeric)
        
        # Create confidence bins
        bins = np.linspace(0, 1, 11)  # 10 bins from 0 to 1
        bin_indices = np.digitize(confidences, bins) - 1
        
        # Calculate accuracy in each bin
        bin_accuracies = []
        bin_confidences = []
        bin_counts = []
        
        for i in range(len(bins) - 1):
            bin_mask = (bin_indices == i)
            if np.sum(bin_mask) > 0:
                bin_acc = np.mean(correct[bin_mask])
                bin_conf = np.mean(confidences[bin_mask])
                bin_count = np.sum(bin_mask)
                
                bin_accuracies.append(float(bin_acc))
                bin_confidences.append(float(bin_conf))
                bin_counts.append(int(bin_count))
            else:
                bin_accuracies.append(0.0)
                bin_confidences.append(0.0)
                bin_counts.append(0)
        
        # Calculate calibration metrics
        # Expected Calibration Error (ECE)
        ece = np.sum(np.abs(np.array(bin_accuracies) - np.array(bin_confidences)) * 
                    np.array(bin_counts) / len(y_numeric))
        
        # Return calibration metrics
        return {
            "bin_edges": bins.tolist(),
            "bin_accuracies": bin_accuracies,
            "bin_confidences": bin_confidences,
            "bin_counts": bin_counts,
            "expected_calibration_error": float(ece)
        }
    
    def save(self, path: str) -> Result[bool]:
        """Save the model to disk.
        
        Args:
            path: Path to save the model to
            
        Returns:
            Result indicating success or failure
        """
        try:
            import joblib
            import os
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Save the model
            joblib.dump(self, path)
            
            logger.info(f"Model saved to {path}")
            return Result.success(True)
        except Exception as e:
            error_msg = f"Error saving model: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.STORAGE_ERROR,
                message=error_msg
            ))
    
    @classmethod
    def load(cls, path: str) -> Result['SVMClassifier']:
        """Load a model from disk.
        
        Args:
            path: Path to load the model from
            
        Returns:
            Result containing the loaded model or an error
        """
        try:
            import joblib
            
            # Load the model
            model = joblib.load(path)
            
            # Verify that it's the correct type
            if not isinstance(model, cls):
                raise TypeError(f"Loaded object is not a {cls.__name__}")
            
            logger.info(f"Model loaded from {path}")
            return Result.success(model)
        except Exception as e:
            error_msg = f"Error loading model: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.STORAGE_ERROR,
                message=error_msg
            ))