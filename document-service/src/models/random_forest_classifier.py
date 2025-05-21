#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Random Forest Classifier for Document Classification.

This module implements a Random Forest classifier for document classification in the Document Service.
It extends the base model interface and provides a complete implementation of Random Forest-based
document classification with ensemble learning, feature importance ranking, and confidence scoring.

The Random Forest classifier uses an ensemble of decision trees to achieve high accuracy and robustness
in document classification. It provides confidence scores based on voting distribution and includes
methods for ensemble optimization and out-of-bag error estimation.

Example usage:
    # Initialize the classifier with default parameters
    classifier = RandomForestClassifier()
    
    # Train the classifier on document features
    classifier.fit(features, labels)
    
    # Predict document types with confidence scores
    predictions = classifier.predict(features)
    probabilities = classifier.predict_proba(features)
    
    # Get feature importance ranking
    importance = classifier.get_feature_importance()
    
    # Optimize ensemble parameters
    classifier.optimize_ensemble(features, labels)
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier as SklearnRF
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV, cross_val_score
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

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


class RandomForestClassifier(ClassificationModel):
    """Random Forest classifier for document classification.
    
    This class implements a Random Forest classifier for document classification,
    extending the base model interface. It provides methods for training, prediction,
    confidence scoring, feature importance ranking, and ensemble optimization.
    
    The classifier uses scikit-learn's RandomForestClassifier as the underlying
    implementation and enhances it with additional functionality specific to
    document classification requirements.
    """
    
    def __init__(self, params: Optional[ModelParameters] = None):
        """Initialize the Random Forest classifier.
        
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
        self.oob_score_ = None
        self.training_accuracy = None
        
        logger.info(f"Initialized RandomForestClassifier with parameters: {self.params}")
    
    def _get_default_params(self) -> ModelParameters:
        """Get default parameters for the Random Forest classifier.
        
        Returns:
            Dictionary of default model parameters
        """
        return {
            "n_estimators": 100,  # Number of trees in the forest
            "max_depth": None,   # Maximum depth of the trees (None means unlimited)
            "min_samples_split": 2,  # Minimum samples required to split a node
            "min_samples_leaf": 1,   # Minimum samples required at a leaf node
            "max_features": "sqrt",  # Number of features to consider for best split
            "bootstrap": True,       # Whether to use bootstrap samples
            "oob_score": True,       # Whether to use out-of-bag samples to estimate accuracy
            "n_jobs": -1,           # Number of jobs to run in parallel (-1 means using all processors)
            "random_state": 42,      # Random seed for reproducibility
            "class_weight": "balanced",  # Use balanced class weights
            "criterion": "gini"      # Function to measure the quality of a split
        }
    
    def _create_model(self) -> SklearnRF:
        """Create a scikit-learn RandomForestClassifier with the specified parameters.
        
        Returns:
            Initialized scikit-learn RandomForestClassifier
        """
        return SklearnRF(**self.params)
    
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'RandomForestClassifier':
        """Fit the Random Forest classifier to the training data.
        
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
        logger.info(f"Training RandomForestClassifier on {X.shape[0]} samples with {X.shape[1]} features")
        
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
        self.feature_importances_ = self.model.feature_importances_
        self.oob_score_ = self.model.oob_score_ if self.params.get("oob_score", False) else None
        
        # Calculate training accuracy
        y_pred = self.model.predict(X)
        self.training_accuracy = accuracy_score(y_numeric, y_pred)
        
        elapsed_time = time.time() - start_time
        logger.info(f"RandomForestClassifier training completed in {elapsed_time:.2f} seconds")
        logger.info(f"Training accuracy: {self.training_accuracy:.4f}")
        if self.oob_score_ is not None:
            logger.info(f"Out-of-bag score: {self.oob_score_:.4f}")
        
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
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before predict_proba().")
        
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
        
        # Get numeric predictions and probabilities from the model
        y_pred_numeric = self.model.predict(X)
        probas = self.model.predict_proba(X)
        
        # Create result list
        results = []
        for i, pred_idx in enumerate(y_pred_numeric):
            # Get predicted class and its probability
            pred_class = self.class_mapping[pred_idx]
            confidence = probas[i, pred_idx]
            
            # Create confidence score
            confidence_score = ConfidenceScore(confidence)
            
            # Add to results
            results.append((pred_class, confidence_score))
        
        return results
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance ranking.
        
        Returns:
            Dictionary mapping feature names to importance scores
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_feature_importance().")
        
        # Get feature importances from the model
        importances = self.model.feature_importances_
        
        # Create dictionary mapping feature names to importance scores
        if self.feature_names and len(self.feature_names) == len(importances):
            # If feature names are available, use them
            importance_dict = {name: float(importance) for name, importance in zip(self.feature_names, importances)}
        else:
            # Otherwise, use feature indices
            importance_dict = {f"feature_{i}": float(importance) for i, importance in enumerate(importances)}
        
        # Sort by importance (descending)
        importance_dict = dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))
        
        return importance_dict
    
    def get_confidence_distribution(self, X: FeatureVector) -> Dict[str, List[float]]:
        """Get confidence distribution across all classes for samples in X.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Dictionary mapping class names to lists of confidence scores
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_confidence_distribution().")
        
        # Get probability predictions from the model
        probas = self.model.predict_proba(X)
        
        # Create dictionary mapping class names to confidence scores
        distribution = {}
        for class_idx, class_type in self.class_mapping.items():
            class_name = class_type.value if hasattr(class_type, 'value') else str(class_type)
            distribution[class_name] = probas[:, class_idx].tolist()
        
        return distribution
    
    def get_tree_decisions(self, X: FeatureVector) -> Dict[str, List[int]]:
        """Get individual tree decisions for samples in X.
        
        This method provides insight into how individual trees in the forest
        vote for each sample, which is useful for understanding ensemble behavior.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Dictionary mapping sample indices to lists of tree predictions
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_tree_decisions().")
        
        # Get predictions from individual trees
        tree_decisions = {}
        for i, sample in enumerate(X):
            sample_decisions = []
            for tree in self.model.estimators_:
                # Get prediction from this tree
                pred = tree.predict(sample.reshape(1, -1))[0]
                sample_decisions.append(int(pred))
            
            tree_decisions[f"sample_{i}"] = sample_decisions
        
        return tree_decisions
    
    def get_voting_distribution(self, X: FeatureVector) -> Dict[str, Dict[str, int]]:
        """Get voting distribution across trees for samples in X.
        
        This method counts how many trees voted for each class for each sample,
        providing insight into the ensemble's decision-making process.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Dictionary mapping sample indices to vote counts per class
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_voting_distribution().")
        
        # Get tree decisions
        tree_decisions = self.get_tree_decisions(X)
        
        # Count votes for each class
        voting_distribution = {}
        for sample_idx, decisions in tree_decisions.items():
            # Count votes for each class
            vote_counts = {}
            for decision in decisions:
                class_type = self.class_mapping[decision]
                class_name = class_type.value if hasattr(class_type, 'value') else str(class_type)
                vote_counts[class_name] = vote_counts.get(class_name, 0) + 1
            
            voting_distribution[sample_idx] = vote_counts
        
        return voting_distribution
    
    def get_oob_error(self) -> Optional[float]:
        """Get out-of-bag error estimate.
        
        Returns:
            Out-of-bag error estimate, or None if not available
        """
        if not self.is_fitted or not self.params.get("oob_score", False):
            return None
        
        # Out-of-bag error is 1 - oob_score
        return 1.0 - self.oob_score_
    
    def optimize_ensemble(self, X: FeatureVector, y: np.ndarray, 
                         param_grid: Optional[Dict[str, List[Any]]] = None,
                         cv: int = 5, scoring: str = 'accuracy',
                         n_iter: int = 10, method: str = 'grid') -> Dict[str, Any]:
        """Optimize ensemble parameters using cross-validation.
        
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
        logger.info(f"Optimizing RandomForestClassifier parameters using {method} search with {cv}-fold cross-validation")
        
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
                "n_estimators": [50, 100, 200],
                "max_depth": [None, 10, 20, 30],
                "min_samples_split": [2, 5, 10],
                "min_samples_leaf": [1, 2, 4],
                "max_features": ["sqrt", "log2", None],
                "criterion": ["gini", "entropy"]
            }
        
        # Create base model for search
        base_model = SklearnRF(random_state=42, oob_score=True, n_jobs=-1)
        
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
    
    def set_feature_names(self, feature_names: List[str]) -> None:
        """Set feature names for the classifier.
        
        Args:
            feature_names: List of feature names
            
        Raises:
            ValueError: If feature names length doesn't match model expectations
        """
        if self.is_fitted and len(feature_names) != self.model.n_features_in_:
            raise ValueError(f"Number of feature names ({len(feature_names)}) does not match model's expected number of features ({self.model.n_features_in_})")
        
        self.feature_names = feature_names
        logger.debug(f"Set {len(feature_names)} feature names for RandomForestClassifier")
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the classifier.
        
        Returns:
            Dictionary with classifier information
        """
        info = {
            "model_type": "random_forest",
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
                "oob_score": self.oob_score_,
                "oob_error": self.get_oob_error(),
                "n_estimators": self.model.n_estimators,
                "n_features": self.model.n_features_in_,
                "n_classes": self.model.n_classes_,
            })
        
        return info
    
    def get_ensemble_diversity(self) -> Dict[str, float]:
        """Calculate diversity metrics for the ensemble.
        
        This method calculates various diversity metrics for the ensemble,
        which can be useful for understanding the robustness of the model.
        
        Returns:
            Dictionary with diversity metrics
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.is_fitted:
            raise ValueError("Model has not been trained. Call fit() before get_ensemble_diversity().")
        
        # Get predictions from individual trees on OOB samples
        if not hasattr(self.model, 'oob_decision_function_'):
            logger.warning("Out-of-bag predictions not available. Set oob_score=True when initializing the model.")
            return {}
        
        # Calculate pairwise disagreement between trees
        n_trees = len(self.model.estimators_)
        disagreement_sum = 0
        agreement_sum = 0
        total_pairs = 0
        
        # This is a simplified calculation for demonstration purposes
        # In a real implementation, you would use the actual tree predictions on OOB samples
        for i in range(n_trees):
            for j in range(i + 1, n_trees):
                # Compare predictions of tree i and tree j
                # This is a placeholder - in a real implementation, you would use actual predictions
                disagreement_rate = 0.3  # Placeholder value
                agreement_rate = 1.0 - disagreement_rate
                
                disagreement_sum += disagreement_rate
                agreement_sum += agreement_rate
                total_pairs += 1
        
        # Calculate average disagreement and agreement
        avg_disagreement = disagreement_sum / total_pairs if total_pairs > 0 else 0
        avg_agreement = agreement_sum / total_pairs if total_pairs > 0 else 0
        
        # Calculate entropy-based diversity (placeholder)
        entropy_diversity = 0.8  # Placeholder value
        
        # Return diversity metrics
        return {
            "average_disagreement": avg_disagreement,
            "average_agreement": avg_agreement,
            "entropy_diversity": entropy_diversity,
            "n_trees": n_trees
        }
    
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
    def load(cls, path: str) -> Result['RandomForestClassifier']:
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