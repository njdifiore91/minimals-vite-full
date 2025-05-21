"""Utilities for training and fine-tuning document classification models.

This module provides functions for dataset preparation, cross-validation,
hyperparameter optimization, and model training workflows for document
classification models used by the Document Service.

The Document Service uses scikit-learn 1.4.1 for document classification with a
target accuracy of 99%. This module implements the training pipeline to achieve
this accuracy target through proper dataset preparation, model selection, and
hyperparameter tuning.
"""

from __future__ import annotations

import logging
import os
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import numpy.typing as npt
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    KFold,
    RandomizedSearchCV,
    StratifiedKFold,
    cross_validate,
    train_test_split,
)
from sklearn.svm import SVC

from ..types.classification import (
    ClassificationMetrics,
    ClassificationModel,
    DocumentType,
    FeatureVector,
    ModelConfig,
)

logger = logging.getLogger(__name__)


def prepare_dataset(
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    test_size: float = 0.2,
    random_state: Optional[int] = 42,
    stratify: bool = True,
) -> Tuple[FeatureVector, FeatureVector, npt.NDArray[np.int_], npt.NDArray[np.int_]]:
    """Split dataset into training and test sets.
    
    Args:
        features: Feature vectors for all samples
        labels: Target labels for all samples
        test_size: Proportion of the dataset to include in the test split
        random_state: Random seed for reproducibility
        stratify: Whether to use stratified sampling based on labels
    
    Returns:
        Tuple containing (X_train, X_test, y_train, y_test)
    """
    stratify_param = labels if stratify else None
    
    return train_test_split(
        features,
        labels,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_param,
    )


def create_cross_validator(
    n_splits: int = 5,
    shuffle: bool = True,
    random_state: Optional[int] = 42,
    stratify: bool = True,
) -> Union[KFold, StratifiedKFold]:
    """Create a cross-validator for model evaluation.
    
    Args:
        n_splits: Number of folds
        shuffle: Whether to shuffle the data before splitting
        random_state: Random seed for reproducibility
        stratify: Whether to use stratified sampling based on labels
    
    Returns:
        Cross-validator object
    """
    if stratify:
        return StratifiedKFold(
            n_splits=n_splits,
            shuffle=shuffle,
            random_state=random_state,
        )
    else:
        return KFold(
            n_splits=n_splits,
            shuffle=shuffle,
            random_state=random_state,
        )


def evaluate_cross_validation(
    model: ClassificationModel,
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    cv: Union[int, KFold, StratifiedKFold] = 5,
    scoring: Union[str, List[str]] = ['accuracy', 'precision_macro', 'recall_macro', 'f1_macro'],
) -> Dict[str, List[float]]:
    """Evaluate model performance using cross-validation.
    
    Args:
        model: Classification model to evaluate
        features: Feature vectors for all samples
        labels: Target labels for all samples
        cv: Cross-validation strategy
        scoring: Scoring metrics to evaluate
    
    Returns:
        Dictionary of cross-validation scores
    """
    scores = cross_validate(
        model,
        features,
        labels,
        cv=cv,
        scoring=scoring,
        return_train_score=True,
    )
    
    # Log cross-validation results
    for metric in scoring:
        if isinstance(metric, str):
            test_metric = f'test_{metric}'
            if test_metric in scores:
                logger.info(
                    f"Cross-validation {metric}: "
                    f"mean={np.mean(scores[test_metric]):.4f}, "
                    f"std={np.std(scores[test_metric]):.4f}"
                )
    
    return scores


def optimize_hyperparameters_grid(
    model: ClassificationModel,
    param_grid: Dict[str, List[Any]],
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    cv: Union[int, KFold, StratifiedKFold] = 5,
    scoring: str = 'accuracy',
    n_jobs: int = -1,
    verbose: int = 1,
) -> Tuple[ClassificationModel, Dict[str, Any]]:
    """Optimize model hyperparameters using grid search.
    
    Args:
        model: Base classification model to optimize
        param_grid: Dictionary with parameters names as keys and lists of parameter values
        features: Feature vectors for all samples
        labels: Target labels for all samples
        cv: Cross-validation strategy
        scoring: Scoring metric to optimize
        n_jobs: Number of jobs to run in parallel (-1 means using all processors)
        verbose: Verbosity level
    
    Returns:
        Tuple containing (best_model, best_params)
    """
    grid_search = GridSearchCV(
        model,
        param_grid,
        scoring=scoring,
        cv=cv,
        n_jobs=n_jobs,
        verbose=verbose,
        return_train_score=True,
    )
    
    logger.info(f"Starting grid search for {type(model).__name__} with {len(param_grid)} parameters")
    grid_search.fit(features, labels)
    logger.info(f"Grid search complete. Best score: {grid_search.best_score_:.4f}")
    logger.info(f"Best parameters: {grid_search.best_params_}")
    
    return grid_search.best_estimator_, grid_search.best_params_


def optimize_hyperparameters_random(
    model: ClassificationModel,
    param_distributions: Dict[str, Any],
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    n_iter: int = 100,
    cv: Union[int, KFold, StratifiedKFold] = 5,
    scoring: str = 'accuracy',
    n_jobs: int = -1,
    verbose: int = 1,
    random_state: Optional[int] = 42,
) -> Tuple[ClassificationModel, Dict[str, Any]]:
    """Optimize model hyperparameters using randomized search.
    
    Args:
        model: Base classification model to optimize
        param_distributions: Dictionary with parameters names as keys and distributions or lists of parameters
        features: Feature vectors for all samples
        labels: Target labels for all samples
        n_iter: Number of parameter settings that are sampled
        cv: Cross-validation strategy
        scoring: Scoring metric to optimize
        n_jobs: Number of jobs to run in parallel (-1 means using all processors)
        verbose: Verbosity level
        random_state: Random seed for reproducibility
    
    Returns:
        Tuple containing (best_model, best_params)
    """
    random_search = RandomizedSearchCV(
        model,
        param_distributions,
        n_iter=n_iter,
        scoring=scoring,
        cv=cv,
        n_jobs=n_jobs,
        verbose=verbose,
        random_state=random_state,
        return_train_score=True,
    )
    
    logger.info(f"Starting randomized search for {type(model).__name__} with {n_iter} iterations")
    random_search.fit(features, labels)
    logger.info(f"Randomized search complete. Best score: {random_search.best_score_:.4f}")
    logger.info(f"Best parameters: {random_search.best_params_}")
    
    return random_search.best_estimator_, random_search.best_params_


def calculate_metrics(
    y_true: npt.NDArray[np.int_],
    y_pred: npt.NDArray[np.int_],
    y_prob: Optional[npt.NDArray[np.float64]] = None,
    labels: Optional[List[Union[int, str]]] = None,
) -> ClassificationMetrics:
    """Calculate classification metrics for model evaluation.
    
    Args:
        y_true: True labels
        y_pred: Predicted labels
        y_prob: Predicted probabilities (optional, for ROC AUC)
        labels: List of label names (optional)
    
    Returns:
        ClassificationMetrics object with calculated metrics
    """
    # Calculate accuracy
    accuracy = accuracy_score(y_true, y_pred)
    
    # Calculate precision, recall, and F1 score for each class
    precision = precision_score(y_true, y_pred, average=None, zero_division=0)
    recall = recall_score(y_true, y_pred, average=None, zero_division=0)
    f1 = f1_score(y_true, y_pred, average=None, zero_division=0)
    
    # Create dictionaries for precision, recall, and F1 score
    precision_dict = {}
    recall_dict = {}
    f1_dict = {}
    
    # If labels are provided, use them as keys
    if labels is not None:
        for i, label in enumerate(labels):
            if i < len(precision):
                precision_dict[label] = float(precision[i])
                recall_dict[label] = float(recall[i])
                f1_dict[label] = float(f1[i])
    else:
        # Otherwise, use indices as keys
        for i in range(len(precision)):
            precision_dict[str(i)] = float(precision[i])
            recall_dict[str(i)] = float(recall[i])
            f1_dict[str(i)] = float(f1[i])
    
    # Calculate confusion matrix
    cm = confusion_matrix(y_true, y_pred)
    
    # Create ClassificationMetrics object
    metrics = ClassificationMetrics(
        accuracy=float(accuracy),
        precision=precision_dict,
        recall=recall_dict,
        f1_score=f1_dict,
        confusion_matrix=cm,
    )
    
    return metrics


def train_svm_classifier(
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    config: Optional[Dict[str, Any]] = None,
    optimize: bool = True,
    n_jobs: int = -1,
) -> Tuple[SVC, ClassificationMetrics]:
    """Train a Support Vector Machine classifier for document classification.
    
    Args:
        features: Feature vectors for all samples
        labels: Target labels for all samples
        config: Configuration parameters for the SVM classifier
        optimize: Whether to optimize hyperparameters
        n_jobs: Number of jobs to run in parallel (-1 means using all processors)
    
    Returns:
        Tuple containing (trained_model, metrics)
    """
    # Default SVM configuration
    default_config = {
        'C': 1.0,
        'kernel': 'rbf',
        'gamma': 'scale',
        'probability': True,
        'class_weight': 'balanced',
        'random_state': 42,
    }
    
    # Update with provided configuration
    if config is not None:
        default_config.update(config)
    
    # Create SVM classifier
    svm = SVC(**default_config)
    
    # Split dataset
    X_train, X_test, y_train, y_test = prepare_dataset(features, labels)
    
    # Optimize hyperparameters if requested
    if optimize:
        # Define parameter grid for grid search
        param_grid = {
            'C': [0.1, 1, 10, 100],
            'gamma': ['scale', 'auto', 0.1, 0.01, 0.001],
            'kernel': ['rbf', 'linear', 'poly', 'sigmoid'],
        }
        
        # Create cross-validator
        cv = create_cross_validator()
        
        # Optimize hyperparameters
        svm, best_params = optimize_hyperparameters_grid(
            svm,
            param_grid,
            X_train,
            y_train,
            cv=cv,
            n_jobs=n_jobs,
        )
        
        logger.info(f"Optimized SVM parameters: {best_params}")
    else:
        # Train with default parameters
        logger.info(f"Training SVM with default parameters: {default_config}")
        svm.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = svm.predict(X_test)
    y_prob = svm.predict_proba(X_test) if hasattr(svm, 'predict_proba') else None
    
    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred, y_prob)
    
    logger.info(f"SVM classifier trained with accuracy: {metrics.accuracy:.4f}")
    
    return svm, metrics


def train_random_forest_classifier(
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    config: Optional[Dict[str, Any]] = None,
    optimize: bool = True,
    n_jobs: int = -1,
) -> Tuple[RandomForestClassifier, ClassificationMetrics]:
    """Train a Random Forest classifier for document classification.
    
    Args:
        features: Feature vectors for all samples
        labels: Target labels for all samples
        config: Configuration parameters for the Random Forest classifier
        optimize: Whether to optimize hyperparameters
        n_jobs: Number of jobs to run in parallel (-1 means using all processors)
    
    Returns:
        Tuple containing (trained_model, metrics)
    """
    # Default Random Forest configuration
    default_config = {
        'n_estimators': 100,
        'max_depth': None,
        'min_samples_split': 2,
        'min_samples_leaf': 1,
        'max_features': 'sqrt',
        'bootstrap': True,
        'class_weight': 'balanced',
        'random_state': 42,
        'n_jobs': n_jobs,
    }
    
    # Update with provided configuration
    if config is not None:
        default_config.update(config)
    
    # Create Random Forest classifier
    rf = RandomForestClassifier(**default_config)
    
    # Split dataset
    X_train, X_test, y_train, y_test = prepare_dataset(features, labels)
    
    # Optimize hyperparameters if requested
    if optimize:
        # Define parameter grid for randomized search
        param_distributions = {
            'n_estimators': [50, 100, 200, 300],
            'max_depth': [None, 10, 20, 30, 40, 50],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None],
            'bootstrap': [True, False],
        }
        
        # Create cross-validator
        cv = create_cross_validator()
        
        # Optimize hyperparameters using randomized search
        rf, best_params = optimize_hyperparameters_random(
            rf,
            param_distributions,
            X_train,
            y_train,
            cv=cv,
            n_jobs=n_jobs,
        )
        
        logger.info(f"Optimized Random Forest parameters: {best_params}")
    else:
        # Train with default parameters
        logger.info(f"Training Random Forest with default parameters: {default_config}")
        rf.fit(X_train, y_train)
    
    # Evaluate on test set
    y_pred = rf.predict(X_test)
    y_prob = rf.predict_proba(X_test)
    
    # Calculate metrics
    metrics = calculate_metrics(y_test, y_pred, y_prob)
    
    logger.info(f"Random Forest classifier trained with accuracy: {metrics.accuracy:.4f}")
    
    return rf, metrics


def train_model_with_early_stopping(
    model: ClassificationModel,
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    validation_size: float = 0.2,
    max_epochs: int = 100,
    patience: int = 5,
    checkpoint_dir: Optional[str] = None,
    random_state: Optional[int] = 42,
) -> Tuple[ClassificationModel, ClassificationMetrics]:
    """Train a model with early stopping based on validation performance.
    
    This function is primarily useful for iterative models like gradient boosting
    that support partial_fit or warm_start. For models like SVM that don't support
    incremental training, this function will fall back to standard training.
    
    Args:
        model: Classification model to train
        features: Feature vectors for all samples
        labels: Target labels for all samples
        validation_size: Proportion of the dataset to include in the validation split
        max_epochs: Maximum number of training epochs
        patience: Number of epochs with no improvement after which training will be stopped
        checkpoint_dir: Directory to save model checkpoints
        random_state: Random seed for reproducibility
    
    Returns:
        Tuple containing (trained_model, metrics)
    """
    # Check if model supports warm_start or partial_fit
    supports_incremental = hasattr(model, 'warm_start') or hasattr(model, 'partial_fit')
    
    if not supports_incremental:
        logger.warning(
            f"Model {type(model).__name__} does not support incremental training. "
            f"Falling back to standard training."
        )
        model.fit(features, labels)
        y_pred = model.predict(features)
        metrics = calculate_metrics(labels, y_pred)
        return model, metrics
    
    # Split dataset into training and validation sets
    X_train, X_val, y_train, y_val = prepare_dataset(
        features,
        labels,
        test_size=validation_size,
        random_state=random_state,
    )
    
    # Initialize variables for early stopping
    best_score = 0.0
    best_epoch = 0
    best_model = None
    epochs_no_improve = 0
    
    # Create checkpoint directory if specified
    if checkpoint_dir is not None:
        os.makedirs(checkpoint_dir, exist_ok=True)
    
    # Training loop
    for epoch in range(max_epochs):
        # Train model for one epoch
        if hasattr(model, 'warm_start'):
            # For models with warm_start, we need to set warm_start=True and fit again
            model.set_params(warm_start=True)
            model.fit(X_train, y_train)
        elif hasattr(model, 'partial_fit'):
            # For models with partial_fit, we can incrementally train
            model.partial_fit(X_train, y_train)
        
        # Evaluate on validation set
        y_val_pred = model.predict(X_val)
        val_accuracy = accuracy_score(y_val, y_val_pred)
        
        logger.info(f"Epoch {epoch+1}/{max_epochs}, Validation Accuracy: {val_accuracy:.4f}")
        
        # Check if this is the best model so far
        if val_accuracy > best_score:
            best_score = val_accuracy
            best_epoch = epoch
            best_model = pickle.dumps(model)
            epochs_no_improve = 0
            
            # Save checkpoint if directory is specified
            if checkpoint_dir is not None:
                checkpoint_path = os.path.join(
                    checkpoint_dir,
                    f"{type(model).__name__}_epoch_{epoch+1}_acc_{val_accuracy:.4f}.pkl"
                )
                joblib.dump(model, checkpoint_path)
                logger.info(f"Saved checkpoint to {checkpoint_path}")
        else:
            epochs_no_improve += 1
            logger.info(f"No improvement for {epochs_no_improve} epochs")
        
        # Check early stopping condition
        if epochs_no_improve >= patience:
            logger.info(
                f"Early stopping at epoch {epoch+1}. "
                f"Best epoch was {best_epoch+1} with accuracy {best_score:.4f}"
            )
            break
    
    # Restore best model
    if best_model is not None:
        model = pickle.loads(best_model)
    
    # Calculate final metrics on validation set
    y_val_pred = model.predict(X_val)
    metrics = calculate_metrics(y_val, y_val_pred)
    
    logger.info(
        f"Training completed. Best validation accuracy: {metrics.accuracy:.4f} "
        f"at epoch {best_epoch+1}"
    )
    
    return model, metrics


def save_model_checkpoint(
    model: ClassificationModel,
    metrics: ClassificationMetrics,
    checkpoint_dir: str,
    model_name: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Save a model checkpoint with metrics and metadata.
    
    Args:
        model: Trained classification model
        metrics: Model evaluation metrics
        checkpoint_dir: Directory to save the checkpoint
        model_name: Name of the model
        metadata: Additional metadata to save with the model
    
    Returns:
        Path to the saved checkpoint
    """
    # Create checkpoint directory if it doesn't exist
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # Generate checkpoint filename with timestamp and accuracy
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    accuracy_str = f"{metrics.accuracy:.4f}".replace('.', '_')
    checkpoint_filename = f"{model_name}_{timestamp}_acc_{accuracy_str}.pkl"
    checkpoint_path = os.path.join(checkpoint_dir, checkpoint_filename)
    
    # Prepare metadata
    if metadata is None:
        metadata = {}
    
    metadata.update({
        'model_name': model_name,
        'timestamp': timestamp,
        'accuracy': metrics.accuracy,
        'precision': metrics.precision,
        'recall': metrics.recall,
        'f1_score': metrics.f1_score,
    })
    
    # Save model with metadata
    joblib.dump({'model': model, 'metadata': metadata}, checkpoint_path)
    
    logger.info(f"Saved model checkpoint to {checkpoint_path}")
    
    return checkpoint_path


def load_model_checkpoint(
    checkpoint_path: str,
) -> Tuple[ClassificationModel, Dict[str, Any]]:
    """Load a model checkpoint with metadata.
    
    Args:
        checkpoint_path: Path to the checkpoint file
    
    Returns:
        Tuple containing (model, metadata)
    """
    # Load checkpoint
    checkpoint = joblib.load(checkpoint_path)
    
    # Extract model and metadata
    model = checkpoint['model']
    metadata = checkpoint.get('metadata', {})
    
    logger.info(f"Loaded model checkpoint from {checkpoint_path}")
    
    return model, metadata


def train_model_from_config(
    config: ModelConfig,
    features: FeatureVector,
    labels: npt.NDArray[np.int_],
    optimize: bool = True,
    early_stopping: bool = True,
    checkpoint_dir: Optional[str] = None,
    n_jobs: int = -1,
) -> Tuple[ClassificationModel, ClassificationMetrics]:
    """Train a model based on the provided configuration.
    
    Args:
        config: Model configuration
        features: Feature vectors for all samples
        labels: Target labels for all samples
        optimize: Whether to optimize hyperparameters
        early_stopping: Whether to use early stopping
        checkpoint_dir: Directory to save model checkpoints
        n_jobs: Number of jobs to run in parallel (-1 means using all processors)
    
    Returns:
        Tuple containing (trained_model, metrics)
    """
    # Create model based on configuration
    if config.model_type == "svm":
        model, metrics = train_svm_classifier(
            features,
            labels,
            config=config.parameters,
            optimize=optimize,
            n_jobs=n_jobs,
        )
    elif config.model_type == "random_forest":
        model, metrics = train_random_forest_classifier(
            features,
            labels,
            config=config.parameters,
            optimize=optimize,
            n_jobs=n_jobs,
        )
    else:
        raise ValueError(f"Unsupported model type: {config.model_type}")
    
    # Apply early stopping if requested and supported
    if early_stopping and hasattr(model, 'warm_start') or hasattr(model, 'partial_fit'):
        model, metrics = train_model_with_early_stopping(
            model,
            features,
            labels,
            checkpoint_dir=checkpoint_dir,
        )
    
    # Save checkpoint if directory is specified
    if checkpoint_dir is not None:
        save_model_checkpoint(
            model,
            metrics,
            checkpoint_dir,
            config.model_type,
            metadata={
                'config': config.__dict__,
                'optimize': optimize,
                'early_stopping': early_stopping,
            },
        )
    
    return model, metrics