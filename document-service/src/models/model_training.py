#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Training Utilities for Document Classification

This module provides utilities for training and fine-tuning document classification models
in the Document Service. It implements dataset preparation, cross-validation,
hyperparameter optimization, and model training workflows to ensure models meet
the required 99% accuracy for document classification.

The module supports the following key functionalities:
1. Dataset preparation (train/test split, stratification)
2. Cross-validation for model evaluation
3. Hyperparameter optimization using grid search and random search
4. Training workflows for different classifier types (SVM, Random Forest)
5. Early stopping and model checkpointing for efficient training

Classes:
    ModelTrainer: Main class for training document classification models

Functions:
    prepare_dataset: Split dataset into training and testing sets
    optimize_hyperparameters: Find optimal hyperparameters for a model
    train_model: Train a specific model type with given parameters
    evaluate_model: Evaluate model performance against requirements
    save_trained_model: Save a trained model with metadata
"""

import os
import time
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Union, Optional, Any, Callable, Type
from datetime import datetime

from sklearn.model_selection import (
    train_test_split,
    GridSearchCV,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_val_score
)
from sklearn.metrics import accuracy_score, f1_score
from sklearn.base import BaseEstimator
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_class_weight

# Import local modules
from ..config.model_config import MODEL_CONFIG, get_model_config
from ..types.classification import FeatureVector, ModelParameters
from ..types.documents import DocumentType
from .model_evaluation import ModelEvaluator, evaluate_model_performance
from .model_serialization import save_model, load_model
from .base_model import BaseModel
from .svm_classifier import SVMClassifier
from .random_forest_classifier import RandomForestClassifier as RFClassifier

# Configure logger
logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    Main class for training document classification models.
    
    This class provides methods for dataset preparation, hyperparameter optimization,
    model training, and evaluation to ensure models meet the required 99% accuracy
    for document classification.
    
    Attributes:
        config (Dict[str, Any]): Configuration parameters for model training
        model_evaluator (ModelEvaluator): Evaluator for model performance
        output_dir (str): Directory for saving model artifacts
        target_accuracy (float): Required accuracy threshold (default: 0.99)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, output_dir: Optional[str] = None):
        """
        Initialize the ModelTrainer with configuration parameters.
        
        Args:
            config: Configuration parameters (defaults to model_config.MODEL_CONFIG)
            output_dir: Directory for saving model artifacts (defaults to config value)
        """
        self.config = config if config is not None else get_model_config()
        self.target_accuracy = self.config.get('target_accuracy', 0.99)
        self.model_evaluator = ModelEvaluator(accuracy_threshold=self.target_accuracy)
        
        # Set output directory
        if output_dir is not None:
            self.output_dir = output_dir
        else:
            self.output_dir = os.path.join(self.config.get('base_dir', './models'), 'training')
        
        # Create output directory if it doesn't exist
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ModelTrainer initialized with target accuracy: {self.target_accuracy}")
        logger.info(f"Model artifacts will be saved to: {self.output_dir}")
    
    def prepare_dataset(
        self, 
        X: FeatureVector, 
        y: np.ndarray,
        test_size: Optional[float] = None,
        random_state: Optional[int] = None,
        stratify: Optional[bool] = None
    ) -> Tuple[FeatureVector, FeatureVector, np.ndarray, np.ndarray]:
        """
        Split dataset into training and testing sets with optional stratification.
        
        Args:
            X: Feature vectors for training
            y: Target labels for training
            test_size: Proportion of the dataset to include in the test split
            random_state: Random seed for reproducibility
            stratify: Whether to use stratified sampling based on target labels
            
        Returns:
            Tuple containing (X_train, X_test, y_train, y_test)
        """
        # Get configuration parameters or use provided values
        train_test_config = self.config.get('training', {}).get('train_test_split', {})
        test_size = test_size if test_size is not None else train_test_config.get('test_size', 0.2)
        random_state = random_state if random_state is not None else train_test_config.get('random_state', 42)
        stratify_param = stratify if stratify is not None else train_test_config.get('stratify', True)
        
        # Validate inputs
        if not isinstance(X, np.ndarray) and not hasattr(X, 'shape'):
            raise ValueError("X must be a numpy array or have a shape attribute")
        
        if not isinstance(y, np.ndarray) and not hasattr(y, 'shape'):
            raise ValueError("y must be a numpy array or have a shape attribute")
        
        if len(X) != len(y):
            raise ValueError(f"X and y must have the same length. Got X: {len(X)}, y: {len(y)}")
        
        # Determine stratify parameter
        stratify_data = y if stratify_param else None
        
        # Split the dataset
        logger.info(f"Splitting dataset with test_size={test_size}, stratify={stratify_param}")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=stratify_data
        )
        
        # Log split information
        logger.info(f"Dataset split: train={len(X_train)} samples, test={len(X_test)} samples")
        
        # Log class distribution
        train_class_dist = np.unique(y_train, return_counts=True)
        test_class_dist = np.unique(y_test, return_counts=True)
        
        logger.info(f"Training set class distribution: {dict(zip(train_class_dist[0], train_class_dist[1]))}")
        logger.info(f"Testing set class distribution: {dict(zip(test_class_dist[0], test_class_dist[1]))}")
        
        return X_train, X_test, y_train, y_test
    
    def optimize_hyperparameters(
        self,
        model_type: str,
        X: FeatureVector,
        y: np.ndarray,
        param_grid: Optional[Dict[str, List[Any]]] = None,
        cv: Optional[int] = None,
        n_iter: Optional[int] = None,
        scoring: Optional[str] = None,
        n_jobs: Optional[int] = None
    ) -> Tuple[Dict[str, Any], float]:
        """
        Find optimal hyperparameters for a model using grid search or random search.
        
        Args:
            model_type: Type of model ('svm' or 'random_forest')
            X: Feature vectors for training
            y: Target labels for training
            param_grid: Parameter grid for search (defaults to config value)
            cv: Number of cross-validation folds (defaults to config value)
            n_iter: Number of iterations for random search (defaults to config value)
            scoring: Scoring metric (defaults to config value)
            n_jobs: Number of parallel jobs (defaults to config value)
            
        Returns:
            Tuple containing (best_params, best_score)
            
        Raises:
            ValueError: If model_type is not supported
        """
        # Validate model type
        if model_type not in ['svm', 'random_forest']:
            raise ValueError(f"Unsupported model type: {model_type}. Supported types: ['svm', 'random_forest']")
        
        # Get model-specific configuration
        model_config = self.config.get('models', {}).get(model_type, {})
        tuning_config = model_config.get('hyperparameter_tuning', {})
        
        # Set default parameters from configuration
        cv = cv if cv is not None else tuning_config.get('cv', 5)
        scoring = scoring if scoring is not None else tuning_config.get('scoring', 'f1_weighted')
        n_jobs = n_jobs if n_jobs is not None else tuning_config.get('n_jobs', -1)
        tuning_method = tuning_config.get('method', 'grid_search')
        
        # Get base model and parameter grid
        if model_type == 'svm':
            base_model = SVC(probability=True, random_state=42)
            param_grid = param_grid if param_grid is not None else tuning_config.get('param_grid', {
                'C': [0.1, 1.0, 10.0, 100.0],
                'kernel': ['linear', 'rbf'],
                'gamma': ['scale', 'auto', 0.1, 0.01]
            })
        else:  # random_forest
            base_model = RandomForestClassifier(random_state=42)
            param_grid = param_grid if param_grid is not None else tuning_config.get('param_distributions', {
                'n_estimators': [50, 100, 200, 300],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2', None]
            })
        
        # Create cross-validation strategy
        cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        
        # Perform hyperparameter search
        start_time = time.time()
        logger.info(f"Starting hyperparameter optimization for {model_type} using {tuning_method}")
        
        if tuning_method == 'grid_search':
            search = GridSearchCV(
                base_model,
                param_grid,
                cv=cv_strategy,
                scoring=scoring,
                n_jobs=n_jobs,
                verbose=1,
                return_train_score=True
            )
        else:  # random_search
            n_iter = n_iter if n_iter is not None else tuning_config.get('n_iter', 20)
            search = RandomizedSearchCV(
                base_model,
                param_grid,
                n_iter=n_iter,
                cv=cv_strategy,
                scoring=scoring,
                n_jobs=n_jobs,
                verbose=1,
                return_train_score=True,
                random_state=42
            )
        
        # Fit the search
        search.fit(X, y)
        
        # Get best parameters and score
        best_params = search.best_params_
        best_score = search.best_score_
        
        # Log results
        elapsed_time = time.time() - start_time
        logger.info(f"Hyperparameter optimization completed in {elapsed_time:.2f} seconds")
        logger.info(f"Best parameters: {best_params}")
        logger.info(f"Best {scoring} score: {best_score:.4f}")
        
        # Save search results to file
        results_df = pd.DataFrame(search.cv_results_)
        results_path = os.path.join(self.output_dir, f"{model_type}_hyperparameter_search_results.csv")
        results_df.to_csv(results_path, index=False)
        logger.info(f"Hyperparameter search results saved to {results_path}")
        
        return best_params, best_score
    
    def train_model(
        self,
        model_type: str,
        X_train: FeatureVector,
        y_train: np.ndarray,
        X_val: Optional[FeatureVector] = None,
        y_val: Optional[np.ndarray] = None,
        hyperparameters: Optional[Dict[str, Any]] = None,
        class_balancing: Optional[bool] = None
    ) -> BaseModel:
        """
        Train a specific model type with given parameters.
        
        Args:
            model_type: Type of model ('svm' or 'random_forest')
            X_train: Feature vectors for training
            y_train: Target labels for training
            X_val: Feature vectors for validation (optional)
            y_val: Target labels for validation (optional)
            hyperparameters: Model hyperparameters (defaults to config value)
            class_balancing: Whether to apply class balancing (defaults to config value)
            
        Returns:
            Trained model instance
            
        Raises:
            ValueError: If model_type is not supported
        """
        # Validate model type
        if model_type not in ['svm', 'random_forest']:
            raise ValueError(f"Unsupported model type: {model_type}. Supported types: ['svm', 'random_forest']")
        
        # Get model-specific configuration
        model_config = self.config.get('models', {}).get(model_type, {})
        training_config = self.config.get('training', {})
        
        # Determine class balancing
        if class_balancing is None:
            class_balancing = training_config.get('class_balancing', {}).get('method', 'class_weight') == 'class_weight'
        
        # Compute class weights if needed
        class_weights = None
        if class_balancing:
            class_weights = compute_class_weight(
                'balanced',
                classes=np.unique(y_train),
                y=y_train
            )
            class_weights = dict(zip(np.unique(y_train), class_weights))
            logger.info(f"Computed class weights: {class_weights}")
        
        # Get or use provided hyperparameters
        if hyperparameters is None:
            hyperparameters = model_config.get('hyperparameters', {})
            logger.info(f"Using default hyperparameters from config: {hyperparameters}")
        else:
            logger.info(f"Using provided hyperparameters: {hyperparameters}")
        
        # Create model instance
        start_time = time.time()
        logger.info(f"Training {model_type} model")
        
        if model_type == 'svm':
            # Update hyperparameters with class weights if needed
            if class_balancing:
                hyperparameters['class_weight'] = class_weights
            
            # Create SVM classifier
            model = SVMClassifier(self.config)
            
            # Set hyperparameters
            model.set_hyperparameters(hyperparameters)
            
        else:  # random_forest
            # Update hyperparameters with class weights if needed
            if class_balancing:
                hyperparameters['class_weight'] = class_weights
            
            # Create Random Forest classifier
            model = RFClassifier(self.config)
            
            # Set hyperparameters
            model.set_hyperparameters(hyperparameters)
        
        # Train the model
        model.fit(X_train, y_train)
        
        # Log training time
        elapsed_time = time.time() - start_time
        logger.info(f"Model training completed in {elapsed_time:.2f} seconds")
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            val_metrics = model.evaluate(X_val, y_val)
            logger.info(f"Validation metrics: {val_metrics}")
            
            # Check if model meets accuracy requirements
            if val_metrics['accuracy'] < self.target_accuracy:
                logger.warning(f"Model accuracy {val_metrics['accuracy']:.4f} is below the target accuracy {self.target_accuracy}")
            else:
                logger.info(f"Model meets target accuracy: {val_metrics['accuracy']:.4f} >= {self.target_accuracy}")
        
        return model
    
    def train_with_early_stopping(
        self,
        model_type: str,
        X_train: FeatureVector,
        y_train: np.ndarray,
        X_val: FeatureVector,
        y_val: np.ndarray,
        max_iterations: Optional[int] = None,
        patience: Optional[int] = None,
        min_delta: Optional[float] = None
    ) -> BaseModel:
        """
        Train a model with early stopping based on validation performance.
        
        This method is primarily useful for models that support incremental training
        or can be trained in stages (like ensemble methods).
        
        Args:
            model_type: Type of model ('random_forest' is recommended)
            X_train: Feature vectors for training
            y_train: Target labels for training
            X_val: Feature vectors for validation
            y_val: Target labels for validation
            max_iterations: Maximum number of training iterations
            patience: Number of iterations with no improvement before stopping
            min_delta: Minimum change to qualify as improvement
            
        Returns:
            Trained model instance
            
        Raises:
            ValueError: If model_type is not supported for early stopping
        """
        # Early stopping works best with ensemble methods like Random Forest
        if model_type != 'random_forest':
            logger.warning(f"Early stopping is optimized for 'random_forest', but got '{model_type}'")
        
        # Get early stopping configuration
        early_stopping_config = self.config.get('training', {}).get('early_stopping', {})
        patience = patience if patience is not None else early_stopping_config.get('patience', 5)
        min_delta = min_delta if min_delta is not None else early_stopping_config.get('min_delta', 0.001)
        
        # For Random Forest, we'll train with increasing numbers of estimators
        if model_type == 'random_forest':
            # Get model configuration
            rf_config = self.config.get('models', {}).get('random_forest', {})
            hyperparameters = rf_config.get('hyperparameters', {})
            
            # Set maximum iterations (number of trees to try)
            max_iterations = max_iterations if max_iterations is not None else hyperparameters.get('n_estimators', 100)
            
            # Create base model with minimal estimators
            base_estimators = 10  # Start with a small number of trees
            model_hyperparams = hyperparameters.copy()
            model_hyperparams['n_estimators'] = base_estimators
            model_hyperparams['warm_start'] = True  # Enable incremental training
            
            # Create model instance
            model = RFClassifier(self.config)
            model.set_hyperparameters(model_hyperparams)
            
            # Initial training
            logger.info(f"Starting Random Forest training with early stopping (max_iterations={max_iterations}, patience={patience})")
            model.fit(X_train, y_train)
            
            # Evaluate initial model
            best_score = accuracy_score(y_val, model.predict(X_val))
            best_estimators = base_estimators
            no_improvement_count = 0
            
            logger.info(f"Initial model with {base_estimators} estimators: validation accuracy = {best_score:.4f}")
            
            # Incremental training with early stopping
            step_size = max(10, max_iterations // 20)  # Add trees in steps of 10 or 5% of max, whichever is larger
            
            for n_estimators in range(base_estimators + step_size, max_iterations + 1, step_size):
                # Update number of estimators
                model.model.n_estimators = n_estimators
                
                # Continue training (warm_start=True means we're adding trees)
                model.fit(X_train, y_train)
                
                # Evaluate current model
                current_score = accuracy_score(y_val, model.predict(X_val))
                
                logger.info(f"Model with {n_estimators} estimators: validation accuracy = {current_score:.4f}")
                
                # Check for improvement
                if current_score > best_score + min_delta:
                    best_score = current_score
                    best_estimators = n_estimators
                    no_improvement_count = 0
                    logger.info(f"Improvement detected: new best accuracy = {best_score:.4f} with {best_estimators} estimators")
                else:
                    no_improvement_count += 1
                    logger.info(f"No improvement for {no_improvement_count} iterations")
                
                # Check early stopping condition
                if no_improvement_count >= patience:
                    logger.info(f"Early stopping triggered after {n_estimators} estimators")
                    break
                
                # Check if we've reached target accuracy
                if current_score >= self.target_accuracy:
                    logger.info(f"Reached target accuracy {self.target_accuracy} with {n_estimators} estimators")
                    break
            
            # Reset to best number of estimators if not the current one
            if model.model.n_estimators != best_estimators:
                logger.info(f"Resetting to best model with {best_estimators} estimators")
                model.model.n_estimators = best_estimators
                model.fit(X_train, y_train)
            
            logger.info(f"Final model: {best_estimators} estimators, validation accuracy = {best_score:.4f}")
            return model
            
        else:  # For other model types, use standard training
            logger.warning(f"Early stopping implementation for {model_type} uses standard training")
            return self.train_model(model_type, X_train, y_train, X_val, y_val)
    
    def train_ensemble_model(
        self,
        X_train: FeatureVector,
        y_train: np.ndarray,
        X_val: FeatureVector,
        y_val: np.ndarray,
        models: Optional[List[Tuple[str, Dict[str, Any]]]] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Train an ensemble of models and combine their predictions.
        
        Args:
            X_train: Feature vectors for training
            y_train: Target labels for training
            X_val: Feature vectors for validation
            y_val: Target labels for validation
            models: List of (model_type, hyperparameters) tuples (defaults to config)
            weights: Dictionary of model weights for ensemble (defaults to config)
            
        Returns:
            Dictionary containing trained models and ensemble metadata
        """
        # Get ensemble configuration
        ensemble_config = self.config.get('models', {}).get('ensemble', {})
        ensemble_method = ensemble_config.get('method', 'voting')
        ensemble_voting = ensemble_config.get('voting', 'soft')
        
        # Use provided weights or get from config
        weights = weights if weights is not None else ensemble_config.get('weights', {
            'svm': 0.4,
            'random_forest': 0.6
        })
        
        # Determine models to train
        if models is None:
            models = []
            for model_type, weight in weights.items():
                if model_type in ['svm', 'random_forest'] and weight > 0:
                    model_config = self.config.get('models', {}).get(model_type, {})
                    hyperparameters = model_config.get('hyperparameters', {})
                    models.append((model_type, hyperparameters))
        
        if not models:
            raise ValueError("No models specified for ensemble training")
        
        # Train individual models
        trained_models = {}
        model_predictions = {}
        model_probabilities = {}
        
        logger.info(f"Training ensemble with {len(models)} models using {ensemble_method} method")
        
        for model_type, hyperparameters in models:
            logger.info(f"Training {model_type} for ensemble")
            model = self.train_model(model_type, X_train, y_train, X_val, y_val, hyperparameters)
            trained_models[model_type] = model
            
            # Get predictions and probabilities on validation set
            model_predictions[model_type] = model.predict(X_val)
            model_probabilities[model_type] = model.predict_proba(X_val)
        
        # Combine predictions based on ensemble method
        if ensemble_method == 'voting':
            if ensemble_voting == 'hard':
                # Hard voting: majority rule
                ensemble_pred = self._hard_voting_ensemble(model_predictions, weights)
            else:  # soft voting
                # Soft voting: weighted probability average
                ensemble_pred, ensemble_prob = self._soft_voting_ensemble(model_probabilities, weights)
        else:
            raise ValueError(f"Unsupported ensemble method: {ensemble_method}")
        
        # Evaluate ensemble performance
        ensemble_accuracy = accuracy_score(y_val, ensemble_pred)
        ensemble_f1 = f1_score(y_val, ensemble_pred, average='weighted')
        
        logger.info(f"Ensemble performance: accuracy={ensemble_accuracy:.4f}, f1={ensemble_f1:.4f}")
        
        # Compare with individual models
        for model_type in trained_models:
            model_accuracy = accuracy_score(y_val, model_predictions[model_type])
            model_f1 = f1_score(y_val, model_predictions[model_type], average='weighted')
            logger.info(f"{model_type} performance: accuracy={model_accuracy:.4f}, f1={model_f1:.4f}")
        
        # Check if ensemble meets accuracy requirements
        if ensemble_accuracy < self.target_accuracy:
            logger.warning(f"Ensemble accuracy {ensemble_accuracy:.4f} is below the target accuracy {self.target_accuracy}")
        else:
            logger.info(f"Ensemble meets target accuracy: {ensemble_accuracy:.4f} >= {self.target_accuracy}")
        
        # Return ensemble results
        return {
            'models': trained_models,
            'weights': weights,
            'method': ensemble_method,
            'voting': ensemble_voting,
            'accuracy': ensemble_accuracy,
            'f1_score': ensemble_f1
        }
    
    def _hard_voting_ensemble(self, predictions: Dict[str, np.ndarray], weights: Dict[str, float]) -> np.ndarray:
        """
        Combine predictions using hard voting (majority rule with optional weights).
        
        Args:
            predictions: Dictionary of model predictions
            weights: Dictionary of model weights
            
        Returns:
            Combined predictions
        """
        # Get all unique classes
        all_classes = np.unique(np.concatenate([pred for pred in predictions.values()]))
        n_samples = next(iter(predictions.values())).shape[0]
        
        # Initialize vote counts
        votes = np.zeros((n_samples, len(all_classes)))
        
        # Count weighted votes for each class
        for model_type, pred in predictions.items():
            weight = weights.get(model_type, 1.0)
            for i, p in enumerate(pred):
                class_idx = np.where(all_classes == p)[0][0]
                votes[i, class_idx] += weight
        
        # Get class with most votes for each sample
        ensemble_pred = all_classes[np.argmax(votes, axis=1)]
        return ensemble_pred
    
    def _soft_voting_ensemble(self, probabilities: Dict[str, np.ndarray], weights: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Combine predictions using soft voting (weighted probability average).
        
        Args:
            probabilities: Dictionary of model class probabilities
            weights: Dictionary of model weights
            
        Returns:
            Tuple of (combined predictions, combined probabilities)
        """
        # Ensure all models have the same number of classes in the same order
        first_model = next(iter(probabilities.values()))
        n_samples, n_classes = first_model.shape
        
        # Initialize weighted probabilities
        weighted_proba = np.zeros((n_samples, n_classes))
        total_weight = 0.0
        
        # Sum weighted probabilities
        for model_type, proba in probabilities.items():
            if proba.shape != first_model.shape:
                raise ValueError(f"Model {model_type} has different probability shape: {proba.shape} vs {first_model.shape}")
            
            weight = weights.get(model_type, 1.0)
            weighted_proba += weight * proba
            total_weight += weight
        
        # Normalize by total weight
        if total_weight > 0:
            weighted_proba /= total_weight
        
        # Get class with highest probability for each sample
        ensemble_pred = np.argmax(weighted_proba, axis=1)
        
        return ensemble_pred, weighted_proba
    
    def save_trained_model(
        self,
        model: BaseModel,
        model_type: str,
        metrics: Dict[str, Any],
        version: Optional[str] = None,
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Save a trained model with metadata.
        
        Args:
            model: Trained model to save
            model_type: Type of model ('svm', 'random_forest', 'ensemble')
            metrics: Performance metrics for the model
            version: Model version (defaults to config value)
            additional_metadata: Additional metadata to store with the model
            
        Returns:
            Path to the saved model file
        """
        # Get model version
        if version is None:
            version = self.config.get('version', '1.0.0')
        
        # Prepare metadata
        metadata = {
            'model_type': model_type,
            'training_date': datetime.now().isoformat(),
            'metrics': metrics,
            'hyperparameters': model.get_parameters(),
            'target_accuracy': self.target_accuracy,
            'meets_requirements': metrics.get('accuracy', 0) >= self.target_accuracy
        }
        
        # Add additional metadata if provided
        if additional_metadata:
            metadata.update(additional_metadata)
        
        # Save the model
        model_path = save_model(
            model.model,  # Get the underlying scikit-learn model
            model_type,
            version,
            metadata,
            model_dir=self.config.get('base_dir')
        )
        
        logger.info(f"Model saved to {model_path}")
        return model_path
    
    def train_and_evaluate_model(
        self,
        model_type: str,
        X: FeatureVector,
        y: np.ndarray,
        optimize_hyperparams: bool = True,
        use_early_stopping: bool = True,
        save_model: bool = True
    ) -> Tuple[BaseModel, Dict[str, Any]]:
        """
        Complete workflow to train, evaluate, and optionally save a model.
        
        Args:
            model_type: Type of model ('svm', 'random_forest', 'ensemble')
            X: Feature vectors
            y: Target labels
            optimize_hyperparams: Whether to perform hyperparameter optimization
            use_early_stopping: Whether to use early stopping (for supported models)
            save_model: Whether to save the trained model
            
        Returns:
            Tuple containing (trained_model, evaluation_metrics)
        """
        # Prepare dataset
        X_train, X_test, y_train, y_test = self.prepare_dataset(X, y)
        
        # Further split training data for validation if using early stopping
        if use_early_stopping and model_type in ['random_forest']:
            X_train, X_val, y_train, y_val = self.prepare_dataset(X_train, y_train, test_size=0.2)
        else:
            X_val, y_val = X_test, y_test
        
        # Optimize hyperparameters if requested
        hyperparameters = None
        if optimize_hyperparams:
            hyperparameters, _ = self.optimize_hyperparameters(model_type, X_train, y_train)
        
        # Train model with or without early stopping
        if use_early_stopping and model_type in ['random_forest']:
            model = self.train_with_early_stopping(model_type, X_train, y_train, X_val, y_val)
        else:
            model = self.train_model(model_type, X_train, y_train, X_val, y_val, hyperparameters)
        
        # Evaluate model on test set
        metrics = model.evaluate(X_test, y_test)
        logger.info(f"Test metrics: {metrics}")
        
        # Generate detailed evaluation report
        output_dir = os.path.join(self.output_dir, f"{model_type}_evaluation")
        os.makedirs(output_dir, exist_ok=True)
        
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)
        
        # Get class names if available
        class_names = None
        if hasattr(model, 'classes_') and model.classes_ is not None:
            class_names = [str(c) for c in model.classes_]
        
        # Generate detailed evaluation report
        detailed_metrics = evaluate_model_performance(
            model.model,  # Get the underlying scikit-learn model
            X_test,
            y_test,
            class_names=class_names,
            accuracy_threshold=self.target_accuracy,
            output_dir=output_dir
        )
        
        # Combine metrics
        combined_metrics = {**metrics, 'detailed': detailed_metrics}
        
        # Save model if requested
        if save_model:
            model_path = self.save_trained_model(model, model_type, combined_metrics)
            combined_metrics['model_path'] = model_path
        
        return model, combined_metrics


def prepare_dataset(
    X: FeatureVector,
    y: np.ndarray,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True
) -> Tuple[FeatureVector, FeatureVector, np.ndarray, np.ndarray]:
    """
    Split dataset into training and testing sets with optional stratification.
    
    This is a standalone function that provides the same functionality as
    ModelTrainer.prepare_dataset without requiring a ModelTrainer instance.
    
    Args:
        X: Feature vectors for training
        y: Target labels for training
        test_size: Proportion of the dataset to include in the test split
        random_state: Random seed for reproducibility
        stratify: Whether to use stratified sampling based on target labels
        
    Returns:
        Tuple containing (X_train, X_test, y_train, y_test)
    """
    # Determine stratify parameter
    stratify_data = y if stratify else None
    
    # Split the dataset
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=stratify_data
    )
    
    # Log split information
    logger.info(f"Dataset split: train={len(X_train)} samples, test={len(X_test)} samples")
    
    return X_train, X_test, y_train, y_test


def optimize_hyperparameters(
    model_type: str,
    X: FeatureVector,
    y: np.ndarray,
    param_grid: Optional[Dict[str, List[Any]]] = None,
    cv: int = 5,
    scoring: str = 'f1_weighted',
    n_jobs: int = -1,
    method: str = 'grid_search',
    n_iter: int = 20
) -> Tuple[Dict[str, Any], float]:
    """
    Find optimal hyperparameters for a model using grid search or random search.
    
    This is a standalone function that provides similar functionality to
    ModelTrainer.optimize_hyperparameters without requiring a ModelTrainer instance.
    
    Args:
        model_type: Type of model ('svm' or 'random_forest')
        X: Feature vectors for training
        y: Target labels for training
        param_grid: Parameter grid for search
        cv: Number of cross-validation folds
        scoring: Scoring metric
        n_jobs: Number of parallel jobs
        method: Search method ('grid_search' or 'random_search')
        n_iter: Number of iterations for random search
        
    Returns:
        Tuple containing (best_params, best_score)
        
    Raises:
        ValueError: If model_type is not supported
    """
    # Validate model type
    if model_type not in ['svm', 'random_forest']:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: ['svm', 'random_forest']")
    
    # Get default parameter grid if not provided
    if param_grid is None:
        if model_type == 'svm':
            param_grid = {
                'C': [0.1, 1.0, 10.0, 100.0],
                'kernel': ['linear', 'rbf'],
                'gamma': ['scale', 'auto', 0.1, 0.01]
            }
        else:  # random_forest
            param_grid = {
                'n_estimators': [50, 100, 200, 300],
                'max_depth': [None, 10, 20, 30],
                'min_samples_split': [2, 5, 10],
                'min_samples_leaf': [1, 2, 4],
                'max_features': ['sqrt', 'log2', None]
            }
    
    # Get base model
    if model_type == 'svm':
        base_model = SVC(probability=True, random_state=42)
    else:  # random_forest
        base_model = RandomForestClassifier(random_state=42)
    
    # Create cross-validation strategy
    cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    
    # Perform hyperparameter search
    start_time = time.time()
    logger.info(f"Starting hyperparameter optimization for {model_type} using {method}")
    
    if method == 'grid_search':
        search = GridSearchCV(
            base_model,
            param_grid,
            cv=cv_strategy,
            scoring=scoring,
            n_jobs=n_jobs,
            verbose=1,
            return_train_score=True
        )
    else:  # random_search
        search = RandomizedSearchCV(
            base_model,
            param_grid,
            n_iter=n_iter,
            cv=cv_strategy,
            scoring=scoring,
            n_jobs=n_jobs,
            verbose=1,
            return_train_score=True,
            random_state=42
        )
    
    # Fit the search
    search.fit(X, y)
    
    # Get best parameters and score
    best_params = search.best_params_
    best_score = search.best_score_
    
    # Log results
    elapsed_time = time.time() - start_time
    logger.info(f"Hyperparameter optimization completed in {elapsed_time:.2f} seconds")
    logger.info(f"Best parameters: {best_params}")
    logger.info(f"Best {scoring} score: {best_score:.4f}")
    
    return best_params, best_score


def train_model_with_cv(
    model_type: str,
    X: FeatureVector,
    y: np.ndarray,
    hyperparameters: Optional[Dict[str, Any]] = None,
    cv: int = 5,
    random_state: int = 42
) -> Tuple[BaseEstimator, Dict[str, Any]]:
    """
    Train a model with cross-validation and return the best model.
    
    Args:
        model_type: Type of model ('svm' or 'random_forest')
        X: Feature vectors for training
        y: Target labels for training
        hyperparameters: Model hyperparameters
        cv: Number of cross-validation folds
        random_state: Random seed for reproducibility
        
    Returns:
        Tuple containing (trained_model, cross_validation_metrics)
        
    Raises:
        ValueError: If model_type is not supported
    """
    # Validate model type
    if model_type not in ['svm', 'random_forest']:
        raise ValueError(f"Unsupported model type: {model_type}. Supported types: ['svm', 'random_forest']")
    
    # Get default hyperparameters if not provided
    if hyperparameters is None:
        if model_type == 'svm':
            hyperparameters = {
                'C': 10.0,
                'kernel': 'rbf',
                'gamma': 'scale',
                'probability': True,
                'class_weight': 'balanced',
                'random_state': random_state
            }
        else:  # random_forest
            hyperparameters = {
                'n_estimators': 100,
                'max_depth': None,
                'min_samples_split': 2,
                'min_samples_leaf': 1,
                'max_features': 'sqrt',
                'class_weight': 'balanced',
                'random_state': random_state
            }
    
    # Create model
    if model_type == 'svm':
        model = SVC(**hyperparameters)
    else:  # random_forest
        model = RandomForestClassifier(**hyperparameters)
    
    # Create cross-validation strategy
    cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=random_state)
    
    # Perform cross-validation
    logger.info(f"Performing {cv}-fold cross-validation for {model_type}")
    cv_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='accuracy')
    
    # Log cross-validation results
    logger.info(f"Cross-validation scores: {cv_scores}")
    logger.info(f"Mean CV accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")
    
    # Train final model on all data
    logger.info(f"Training final {model_type} model on all data")
    model.fit(X, y)
    
    # Return model and metrics
    metrics = {
        'cv_scores': cv_scores,
        'mean_cv_accuracy': cv_scores.mean(),
        'std_cv_accuracy': cv_scores.std(),
        'hyperparameters': hyperparameters
    }
    
    return model, metrics


if __name__ == "__main__":
    # Example usage
    from sklearn.datasets import make_classification
    import numpy as np
    
    # Configure logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Generate sample data
    X, y = make_classification(n_samples=1000, n_classes=len(DocumentType), n_features=20, 
                             n_informative=10, random_state=42)
    
    # Create model trainer
    trainer = ModelTrainer()
    
    # Train and evaluate a Random Forest model
    rf_model, rf_metrics = trainer.train_and_evaluate_model('random_forest', X, y)
    
    print(f"Random Forest accuracy: {rf_metrics['accuracy']:.4f}")
    
    # Train and evaluate an SVM model
    svm_model, svm_metrics = trainer.train_and_evaluate_model('svm', X, y)
    
    print(f"SVM accuracy: {svm_metrics['accuracy']:.4f}")
    
    # Train an ensemble model
    X_train, X_test, y_train, y_test = trainer.prepare_dataset(X, y)
    ensemble_results = trainer.train_ensemble_model(X_train, y_train, X_test, y_test)
    
    print(f"Ensemble accuracy: {ensemble_results['accuracy']:.4f}")