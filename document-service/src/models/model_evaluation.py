"""
Utilities for evaluating the performance of document classification models.

This module provides functions for calculating classification metrics, generating
confusion matrices, ROC curves, and optimizing classification thresholds to ensure
models meet the required 99% accuracy for document classification.
"""

import logging
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from typing import Dict, List, Tuple, Optional, Union, Any, Callable
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_curve,
    auc,
    classification_report,
    precision_recall_curve,
    average_precision_score,
    roc_auc_score
)
from sklearn.model_selection import cross_val_score, StratifiedKFold, learning_curve
from sklearn.base import BaseEstimator, ClassifierMixin
from sklearn.calibration import CalibratedClassifierCV
from sklearn.utils import resample

from ..config import model_config
from ..types.classification import (
    ClassificationModel,
    ClassificationResult,
    ClassificationMetrics,
    ConfidenceScore,
    ModelParameters
)

logger = logging.getLogger(__name__)


def calculate_classification_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    average: str = 'weighted'
) -> ClassificationMetrics:
    """Calculate standard classification metrics.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        average: Averaging method for multi-class metrics ('micro', 'macro', 'weighted')
        
    Returns:
        Dictionary containing accuracy, precision, recall, and F1 score
    """
    metrics = {
        'accuracy': float(accuracy_score(y_true, y_pred)),
        'precision': float(precision_score(y_true, y_pred, average=average, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, average=average, zero_division=0)),
        'f1': float(f1_score(y_true, y_pred, average=average, zero_division=0))
    }
    
    logger.info(f"Classification metrics: {metrics}")
    
    # Check if accuracy meets the required threshold
    if metrics['accuracy'] < model_config.REQUIRED_ACCURACY:
        logger.warning(
            f"Model accuracy {metrics['accuracy']:.4f} is below the required threshold "
            f"of {model_config.REQUIRED_ACCURACY}"
        )
    
    return metrics


def generate_confusion_matrix(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    class_names: Optional[List[str]] = None,
    normalize: Optional[str] = None,
    figsize: Tuple[int, int] = (10, 8),
    cmap: str = 'Blues',
    save_path: Optional[str] = None,
    use_seaborn: bool = True
) -> np.ndarray:
    """Generate and optionally visualize a confusion matrix.
    
    Args:
        y_true: Ground truth labels
        y_pred: Predicted labels
        class_names: Names of the classes for axis labels
        normalize: Normalization method ('true', 'pred', 'all', or None)
        figsize: Figure size for the plot
        cmap: Colormap for the plot
        save_path: Path to save the confusion matrix visualization
        
    Returns:
        Confusion matrix as a numpy array
    """
    # Calculate confusion matrix
    cm = confusion_matrix(y_true, y_pred, normalize=normalize)
    
    # Visualize confusion matrix
    plt.figure(figsize=figsize)
    
    if use_seaborn:
        # Use seaborn for better visualization
        fmt = '.2f' if normalize else 'd'
        df_cm = pd.DataFrame(cm, 
                            index=class_names if class_names is not None else range(cm.shape[0]), 
                            columns=class_names if class_names is not None else range(cm.shape[1]))
        
        sns.heatmap(df_cm, annot=True, fmt=fmt, cmap=cmap, cbar=True,
                   xticklabels=df_cm.columns, yticklabels=df_cm.index)
        plt.title('Confusion Matrix')
        plt.ylabel('True Label')
        plt.xlabel('Predicted Label')
    else:
        # Use matplotlib
        plt.imshow(cm, interpolation='nearest', cmap=cmap)
        plt.title('Confusion Matrix')
        plt.colorbar()
        
        # Set axis labels
        if class_names is not None:
            tick_marks = np.arange(len(class_names))
            plt.xticks(tick_marks, class_names, rotation=45)
            plt.yticks(tick_marks, class_names)
        
        # Add text annotations
        fmt = '.2f' if normalize else 'd'
        thresh = cm.max() / 2.
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                plt.text(j, i, format(cm[i, j], fmt),
                        ha="center", va="center",
                        color="white" if cm[i, j] > thresh else "black")
    
    plt.tight_layout()
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    
    # Save or show the plot
    if save_path:
        plt.savefig(save_path)
        logger.info(f"Confusion matrix saved to {save_path}")
    else:
        plt.show()
    
    plt.close()
    
    return cm


def generate_roc_curve(
    y_true: np.ndarray,
    y_score: np.ndarray,
    class_index: int = 1,
    figsize: Tuple[int, int] = (10, 8),
    save_path: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Generate and visualize ROC curve for binary classification or a specific class.
    
    Args:
        y_true: Ground truth labels (binary or one-hot encoded)
        y_score: Predicted probabilities or decision function scores
        class_index: Index of the class to evaluate for multi-class problems
        figsize: Figure size for the plot
        save_path: Path to save the ROC curve visualization
        
    Returns:
        Tuple containing (fpr, tpr, thresholds, auc_score)
    """
    # For multi-class, convert to binary problem for the specified class
    if y_true.ndim > 1 and y_true.shape[1] > 1:  # One-hot encoded
        y_true_binary = y_true[:, class_index]
        y_score_binary = y_score[:, class_index]
    elif y_score.ndim > 1 and y_score.shape[1] > 1:  # Multi-class probabilities
        y_true_binary = (y_true == class_index).astype(int)
        y_score_binary = y_score[:, class_index]
    else:  # Already binary
        y_true_binary = y_true
        y_score_binary = y_score
    
    # Calculate ROC curve and AUC
    fpr, tpr, thresholds = roc_curve(y_true_binary, y_score_binary)
    roc_auc = auc(fpr, tpr)
    
    # Plot ROC curve
    plt.figure(figsize=figsize)
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel('False Positive Rate')
    plt.ylabel('True Positive Rate')
    plt.title('Receiver Operating Characteristic (ROC) Curve')
    plt.legend(loc="lower right")
    
    # Save or show the plot
    if save_path:
        plt.savefig(save_path)
        logger.info(f"ROC curve saved to {save_path}")
    else:
        plt.show()
    
    plt.close()
    
    logger.info(f"ROC AUC: {roc_auc:.4f}")
    
    return fpr, tpr, thresholds, roc_auc


def cross_validation_performance(
    model: ClassificationModel,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
    scoring: str = 'accuracy',
    n_jobs: int = -1,
    return_estimator: bool = False
) -> Dict[str, Any]:
    """Evaluate model performance using cross-validation.
    
    Args:
        model: Classification model to evaluate
        X: Feature matrix
        y: Target labels
        cv: Number of cross-validation folds
        scoring: Scoring metric to use
        n_jobs: Number of parallel jobs
        
    Returns:
        Dictionary with cross-validation results
    """
    # Define cross-validation strategy
    cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
    
    if return_estimator:
        from sklearn.model_selection import cross_validate
        cv_results = cross_validate(
            model, X, y, 
            cv=cv_strategy, 
            scoring={
                'accuracy': 'accuracy',
                'precision': 'precision_weighted',
                'recall': 'recall_weighted',
                'f1': 'f1_weighted'
            },
            n_jobs=n_jobs,
            return_estimator=True,
            return_train_score=True
        )
        # Extract the trained estimators
        estimators = cv_results.pop('estimator')
        
        # Calculate cross-validation scores for different metrics
        accuracy_scores = cv_results['test_accuracy']
        precision_scores = cv_results['test_precision']
        recall_scores = cv_results['test_recall']
        f1_scores = cv_results['test_f1']
    else:
        # Calculate cross-validation scores for different metrics
        accuracy_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='accuracy', n_jobs=n_jobs)
        precision_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='precision_weighted', n_jobs=n_jobs)
        recall_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='recall_weighted', n_jobs=n_jobs)
        f1_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring='f1_weighted', n_jobs=n_jobs)
    
    # Compile results
    cv_results = {
        'accuracy': {
            'mean': float(np.mean(accuracy_scores)),
            'std': float(np.std(accuracy_scores)),
            'values': accuracy_scores.tolist()
        },
        'precision': {
            'mean': float(np.mean(precision_scores)),
            'std': float(np.std(precision_scores)),
            'values': precision_scores.tolist()
        },
        'recall': {
            'mean': float(np.mean(recall_scores)),
            'std': float(np.std(recall_scores)),
            'values': recall_scores.tolist()
        },
        'f1': {
            'mean': float(np.mean(f1_scores)),
            'std': float(np.std(f1_scores)),
            'values': f1_scores.tolist()
        }
    }
    
    logger.info(f"Cross-validation results:\n"
               f"Accuracy: {cv_results['accuracy']['mean']:.4f} ± {cv_results['accuracy']['std']:.4f}\n"
               f"Precision: {cv_results['precision']['mean']:.4f} ± {cv_results['precision']['std']:.4f}\n"
               f"Recall: {cv_results['recall']['mean']:.4f} ± {cv_results['recall']['std']:.4f}\n"
               f"F1 Score: {cv_results['f1']['mean']:.4f} ± {cv_results['f1']['std']:.4f}")
    
    # Check if accuracy meets the required threshold
    if cv_results['accuracy']['mean'] < model_config.REQUIRED_ACCURACY:
        logger.warning(
            f"Cross-validation accuracy {cv_results['accuracy']['mean']:.4f} is below "
            f"the required threshold of {model_config.REQUIRED_ACCURACY}"
        )
    
    if return_estimator:
        return cv_results, estimators
    
    return cv_results


def optimize_threshold(
    y_true: np.ndarray,
    y_score: np.ndarray,
    metric: str = 'f1',
    class_index: int = 1,
    thresholds: Optional[np.ndarray] = None,
    plot_curve: bool = True,
    figsize: Tuple[int, int] = (10, 8),
    save_path: Optional[str] = None
) -> Tuple[float, Dict[str, float]]:
    """Optimize classification threshold based on a specified metric.
    
    Args:
        y_true: Ground truth labels
        y_score: Predicted probabilities or decision function scores
        metric: Metric to optimize ('f1', 'precision', 'recall', 'accuracy')
        class_index: Index of the class to evaluate for multi-class problems
        thresholds: Array of thresholds to evaluate (default: 100 values from 0.01 to 0.99)
        plot_curve: Whether to plot the metric vs threshold curve
        figsize: Figure size for the plot
        save_path: Path to save the threshold optimization curve
        
    Returns:
        Tuple containing (optimal_threshold, metrics_at_optimal_threshold)
    """
    # For multi-class, convert to binary problem for the specified class
    if y_true.ndim > 1 and y_true.shape[1] > 1:  # One-hot encoded
        y_true_binary = y_true[:, class_index]
        y_score_binary = y_score[:, class_index]
    elif y_score.ndim > 1 and y_score.shape[1] > 1:  # Multi-class probabilities
        y_true_binary = (y_true == class_index).astype(int)
        y_score_binary = y_score[:, class_index]
    else:  # Already binary
        y_true_binary = y_true
        y_score_binary = y_score
    
    # Define thresholds to evaluate
    if thresholds is None:
        thresholds = np.linspace(0.01, 0.99, 100)
    
    # Initialize arrays to store metric values
    accuracies = np.zeros_like(thresholds)
    precisions = np.zeros_like(thresholds)
    recalls = np.zeros_like(thresholds)
    f1_scores_array = np.zeros_like(thresholds)
    
    # Calculate metrics for each threshold
    for i, threshold in enumerate(thresholds):
        y_pred_binary = (y_score_binary >= threshold).astype(int)
        
        accuracies[i] = accuracy_score(y_true_binary, y_pred_binary)
        precisions[i] = precision_score(y_true_binary, y_pred_binary, zero_division=0)
        recalls[i] = recall_score(y_true_binary, y_pred_binary, zero_division=0)
        f1_scores_array[i] = f1_score(y_true_binary, y_pred_binary, zero_division=0)
    
    # Select the metric to optimize
    if metric == 'accuracy':
        metric_values = accuracies
    elif metric == 'precision':
        metric_values = precisions
    elif metric == 'recall':
        metric_values = recalls
    elif metric == 'f1':
        metric_values = f1_scores_array
    else:
        raise ValueError(f"Unsupported metric: {metric}. Use 'accuracy', 'precision', 'recall', or 'f1'.")
    
    # Find the optimal threshold
    best_idx = np.argmax(metric_values)
    optimal_threshold = float(thresholds[best_idx])
    
    # Metrics at the optimal threshold
    metrics_at_optimal = {
        'threshold': optimal_threshold,
        'accuracy': float(accuracies[best_idx]),
        'precision': float(precisions[best_idx]),
        'recall': float(recalls[best_idx]),
        'f1': float(f1_scores_array[best_idx])
    }
    
    logger.info(f"Optimal threshold: {optimal_threshold:.4f} (optimizing {metric})")
    logger.info(f"Metrics at optimal threshold: {metrics_at_optimal}")
    
    # Plot metric vs threshold curve
    if plot_curve:
        plt.figure(figsize=figsize)
        plt.plot(thresholds, accuracies, label='Accuracy')
        plt.plot(thresholds, precisions, label='Precision')
        plt.plot(thresholds, recalls, label='Recall')
        plt.plot(thresholds, f1_scores_array, label='F1 Score')
        plt.axvline(x=optimal_threshold, color='r', linestyle='--', 
                   label=f'Optimal Threshold = {optimal_threshold:.2f}')
        plt.xlabel('Threshold')
        plt.ylabel('Score')
        plt.title(f'Classification Metrics vs. Threshold (Optimizing {metric})')
        plt.legend(loc='best')
        plt.grid(True, alpha=0.3)
        
        # Save or show the plot
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Threshold optimization curve saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    return optimal_threshold, metrics_at_optimal


def calibrate_confidence_scores(
    model: ClassificationModel,
    X_train: np.ndarray,
    y_train: np.ndarray,
    method: str = 'sigmoid',
    cv: int = 5
) -> ClassificationModel:
    """Calibrate model probability outputs to improve confidence score reliability.
    
    Args:
        model: Classification model to calibrate
        X_train: Training feature matrix
        y_train: Training target labels
        method: Calibration method ('sigmoid' for Platt scaling or 'isotonic' for isotonic regression)
        cv: Number of cross-validation folds for calibration
        
    Returns:
        Calibrated classification model
    """
    calibrated_model = CalibratedClassifierCV(
        model, method=method, cv=cv, n_jobs=-1
    )
    calibrated_model.fit(X_train, y_train)
    
    logger.info(f"Model calibrated using {method} method with {cv}-fold cross-validation")
    
    return calibrated_model


def compare_models(
    models: Dict[str, ClassificationModel],
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: Optional[List[str]] = None,
    figsize: Tuple[int, int] = (12, 10),
    save_path: Optional[str] = None
) -> Dict[str, Dict[str, Any]]:
    """Compare multiple classification models using ROC curves and metrics.
    
    Args:
        models: Dictionary mapping model names to trained models
        X_test: Test feature matrix
        y_test: Test target labels
        class_names: Names of the classes for visualization
        figsize: Figure size for the plot
        save_path: Path to save the comparison plot
        
    Returns:
        Dictionary with comparison results for each model
    """
    # Initialize results dictionary
    results = {}
    
    # Check if binary or multi-class classification
    is_binary = len(np.unique(y_test)) == 2
    
    # Create figure for ROC curves
    plt.figure(figsize=figsize)
    
    # Evaluate each model
    for model_name, model in models.items():
        # Get predictions
        y_pred = model.predict(X_test)
        
        # Calculate basic metrics
        metrics = calculate_classification_metrics(y_test, y_pred)
        results[model_name] = {'metrics': metrics}
        
        # For binary classification, plot ROC curve
        if is_binary:
            try:
                # Get probability scores
                if hasattr(model, 'predict_proba'):
                    y_prob = model.predict_proba(X_test)[:, 1]
                elif hasattr(model, 'decision_function'):
                    y_prob = model.decision_function(X_test)
                else:
                    logger.warning(f"Model {model_name} does not support predict_proba or decision_function")
                    continue
                
                # Calculate ROC curve
                fpr, tpr, _ = roc_curve(y_test, y_prob)
                roc_auc = auc(fpr, tpr)
                
                # Plot ROC curve
                plt.plot(fpr, tpr, lw=2, label=f'{model_name} (AUC = {roc_auc:.3f})')
                
                # Store ROC data
                results[model_name]['roc'] = {
                    'fpr': fpr.tolist(),
                    'tpr': tpr.tolist(),
                    'auc': float(roc_auc)
                }
            except Exception as e:
                logger.error(f"Error calculating ROC curve for {model_name}: {str(e)}")
    
    # Finalize ROC plot
    if is_binary:
        plt.plot([0, 1], [0, 1], 'k--', lw=2)
        plt.xlim([0.0, 1.0])
        plt.ylim([0.0, 1.05])
        plt.xlabel('False Positive Rate')
        plt.ylabel('True Positive Rate')
        plt.title('ROC Curves for Model Comparison')
        plt.legend(loc="lower right")
        
        # Save or show the plot
        if save_path:
            plt.savefig(save_path)
            logger.info(f"Model comparison plot saved to {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    return results


def evaluate_model_performance(
    model: ClassificationModel,
    X_test: np.ndarray,
    y_test: np.ndarray,
    class_names: Optional[List[str]] = None,
    output_dir: Optional[str] = None,
    threshold: Optional[float] = None,
    bootstrap_ci: bool = False
) -> Dict[str, Any]:
    """Comprehensive evaluation of a classification model's performance.
    
    Args:
        model: Trained classification model to evaluate
        X_test: Test feature matrix
        y_test: Test target labels
        class_names: Names of the classes for visualization
        output_dir: Directory to save evaluation artifacts
        
    Returns:
        Dictionary containing all evaluation results
    """
    # Get predictions and probabilities
    if threshold is not None and hasattr(model, 'predict_proba'):
        # Apply custom threshold if specified
        y_prob = model.predict_proba(X_test)
        if y_prob.shape[1] == 2:  # Binary classification
            y_pred = (y_prob[:, 1] >= threshold).astype(int)
        else:
            # For multi-class, still use argmax but log the custom threshold
            logger.warning("Custom threshold specified for multi-class classification. "
                          "Using argmax instead.")
            y_pred = model.predict(X_test)
    else:
        y_pred = model.predict(X_test)
    
    try:
        y_prob = model.predict_proba(X_test)
    except (AttributeError, NotImplementedError):
        logger.warning("Model does not support predict_proba, using decision_function if available")
        try:
            y_prob = model.decision_function(X_test)
            # Convert decision function to pseudo-probabilities
            if y_prob.ndim == 1:  # Binary classification
                y_prob = np.column_stack([1 - sigmoid(y_prob), sigmoid(y_prob)])
            else:  # Multi-class
                y_prob = softmax(y_prob, axis=1)
        except (AttributeError, NotImplementedError):
            logger.warning("Model does not support decision_function either, skipping probability-based metrics")
            y_prob = None
    
    # Basic classification metrics
    metrics = calculate_classification_metrics(y_test, y_pred)
    
    # Detailed classification report
    report = classification_report(y_test, y_pred, target_names=class_names, output_dict=True)
    
    # Confusion matrix
    cm_path = f"{output_dir}/confusion_matrix.png" if output_dir else None
    cm = generate_confusion_matrix(y_test, y_pred, class_names=class_names, save_path=cm_path)
    
    # Initialize results dictionary
    results = {
        'metrics': metrics,
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
    }
    
    # Add bootstrap confidence intervals if requested
    if bootstrap_ci:
        accuracy_ci = bootstrap_confidence_interval(model, X_test, y_test, accuracy_score)
        precision_ci = bootstrap_confidence_interval(model, X_test, y_test, 
                                                   lambda y, y_pred: precision_score(y, y_pred, average='weighted', zero_division=0))
        recall_ci = bootstrap_confidence_interval(model, X_test, y_test,
                                                lambda y, y_pred: recall_score(y, y_pred, average='weighted', zero_division=0))
        f1_ci = bootstrap_confidence_interval(model, X_test, y_test,
                                            lambda y, y_pred: f1_score(y, y_pred, average='weighted', zero_division=0))
        
        results['bootstrap_ci'] = {
            'accuracy': accuracy_ci,
            'precision': precision_ci,
            'recall': recall_ci,
            'f1': f1_ci
        }
    
    # Add probability-based metrics if available
    if y_prob is not None:
        # For binary classification or per-class metrics in multi-class
        if y_prob.shape[1] == 2:  # Binary classification
            # ROC curve
            roc_path = f"{output_dir}/roc_curve.png" if output_dir else None
            fpr, tpr, roc_thresholds, roc_auc = generate_roc_curve(
                y_test, y_prob[:, 1], save_path=roc_path
            )
            
            # Precision-Recall curve
            pr_path = f"{output_dir}/precision_recall_curve.png" if output_dir else None
            precision, recall, pr_thresholds, avg_precision = generate_precision_recall_curve(
                y_test, y_prob[:, 1], save_path=pr_path
            )
            
            # Threshold optimization
            threshold_path = f"{output_dir}/threshold_optimization.png" if output_dir else None
            optimal_threshold, threshold_metrics = optimize_threshold(
                y_test, y_prob[:, 1], save_path=threshold_path
            )
            
            results.update({
                'roc': {
                    'fpr': fpr.tolist(),
                    'tpr': tpr.tolist(),
                    'thresholds': roc_thresholds.tolist(),
                    'auc': float(roc_auc)
                },
                'precision_recall': {
                    'precision': precision.tolist(),
                    'recall': recall.tolist(),
                    'thresholds': pr_thresholds.tolist() if len(pr_thresholds) > 0 else [],
                    'average_precision': float(avg_precision)
                },
                'threshold_optimization': {
                    'optimal_threshold': optimal_threshold,
                    'metrics': threshold_metrics
                }
            })
        else:  # Multi-class
            # For multi-class, we can compute ROC AUC for each class
            n_classes = y_prob.shape[1]
            multi_roc_auc = {}
            
            for i in range(n_classes):
                class_name = class_names[i] if class_names else f"Class {i}"
                roc_path = f"{output_dir}/roc_curve_class_{i}.png" if output_dir else None
                _, _, _, roc_auc = generate_roc_curve(
                    y_test, y_prob, class_index=i, save_path=roc_path
                )
                multi_roc_auc[class_name] = float(roc_auc)
            
            results['multi_class_roc_auc'] = multi_roc_auc
    
    return results


def generate_precision_recall_curve(
    y_true: np.ndarray,
    y_score: np.ndarray,
    class_index: int = 1,
    figsize: Tuple[int, int] = (10, 8),
    save_path: Optional[str] = None
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    """Generate and visualize Precision-Recall curve for binary classification or a specific class.
    
    Args:
        y_true: Ground truth labels (binary or one-hot encoded)
        y_score: Predicted probabilities or decision function scores
        class_index: Index of the class to evaluate for multi-class problems
        figsize: Figure size for the plot
        save_path: Path to save the Precision-Recall curve visualization
        
    Returns:
        Tuple containing (precision, recall, thresholds, average_precision)
    """
    # For multi-class, convert to binary problem for the specified class
    if y_true.ndim > 1 and y_true.shape[1] > 1:  # One-hot encoded
        y_true_binary = y_true[:, class_index]
        y_score_binary = y_score[:, class_index]
    elif y_score.ndim > 1 and y_score.shape[1] > 1:  # Multi-class probabilities
        y_true_binary = (y_true == class_index).astype(int)
        y_score_binary = y_score[:, class_index]
    else:  # Already binary
        y_true_binary = y_true
        y_score_binary = y_score
    
    # Calculate Precision-Recall curve
    precision, recall, thresholds = precision_recall_curve(y_true_binary, y_score_binary)
    avg_precision = average_precision_score(y_true_binary, y_score_binary)
    
    # Plot Precision-Recall curve
    plt.figure(figsize=figsize)
    plt.plot(recall, precision, color='darkorange', lw=2, 
             label=f'Precision-Recall curve (AP = {avg_precision:.2f})')
    plt.xlabel('Recall')
    plt.ylabel('Precision')
    plt.title('Precision-Recall Curve')
    plt.legend(loc="best")
    plt.grid(True, alpha=0.3)
    
    # Save or show the plot
    if save_path:
        plt.savefig(save_path)
        logger.info(f"Precision-Recall curve saved to {save_path}")
    else:
        plt.show()
    
    plt.close()
    
    logger.info(f"Average Precision: {avg_precision:.4f}")
    
    return precision, recall, thresholds, avg_precision


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Apply sigmoid function to convert decision function values to probabilities."""
    return 1 / (1 + np.exp(-x))


def softmax(x: np.ndarray, axis: int = 1) -> np.ndarray:
    """Apply softmax function to convert decision function values to probabilities."""
    # Subtract max for numerical stability
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / np.sum(e_x, axis=axis, keepdims=True)


def plot_learning_curve(
    estimator: ClassificationModel,
    X: np.ndarray,
    y: np.ndarray,
    cv: int = 5,
    train_sizes: np.ndarray = np.linspace(0.1, 1.0, 5),
    scoring: str = 'accuracy',
    n_jobs: int = -1,
    figsize: Tuple[int, int] = (10, 6),
    save_path: Optional[str] = None
) -> Dict[str, np.ndarray]:
    """Generate and plot a learning curve to evaluate model performance with varying training set sizes.
    
    Args:
        estimator: Classification model to evaluate
        X: Feature matrix
        y: Target labels
        cv: Number of cross-validation folds
        train_sizes: Array of training set sizes to evaluate
        scoring: Scoring metric to use
        n_jobs: Number of parallel jobs
        figsize: Figure size for the plot
        save_path: Path to save the learning curve plot
        
    Returns:
        Dictionary with learning curve results
    """
    train_sizes, train_scores, test_scores = learning_curve(
        estimator, X, y, train_sizes=train_sizes, cv=cv, scoring=scoring, n_jobs=n_jobs
    )
    
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)
    
    # Plot learning curve
    plt.figure(figsize=figsize)
    plt.title(f'Learning Curve ({scoring})')
    plt.xlabel('Training examples')
    plt.ylabel(f'Score ({scoring})')
    plt.grid(True, alpha=0.3)
    
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, 
                     alpha=0.1, color='blue')
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, 
                     alpha=0.1, color='orange')
    
    plt.plot(train_sizes, train_mean, 'o-', color='blue', label='Training score')
    plt.plot(train_sizes, test_mean, 'o-', color='orange', label='Cross-validation score')
    
    plt.legend(loc='best')
    
    # Add horizontal line for required accuracy
    if scoring == 'accuracy':
        plt.axhline(y=model_config.REQUIRED_ACCURACY, color='r', linestyle='--',
                   label=f'Required Accuracy ({model_config.REQUIRED_ACCURACY})')
        plt.legend(loc='best')
    
    # Save or show the plot
    if save_path:
        plt.savefig(save_path)
        logger.info(f"Learning curve saved to {save_path}")
    else:
        plt.show()
    
    plt.close()
    
    return {
        'train_sizes': train_sizes,
        'train_scores': train_scores,
        'test_scores': test_scores,
        'train_mean': train_mean,
        'train_std': train_std,
        'test_mean': test_mean,
        'test_std': test_std
    }


def bootstrap_confidence_interval(
    model: ClassificationModel,
    X: np.ndarray,
    y: np.ndarray,
    metric_func: Callable,
    n_iterations: int = 1000,
    confidence_level: float = 0.95,
    random_state: Optional[int] = None
) -> Dict[str, float]:
    """Calculate confidence intervals for model performance metrics using bootstrapping.
    
    Args:
        model: Trained classification model
        X: Feature matrix
        y: Target labels
        metric_func: Function to calculate the metric (e.g., accuracy_score)
        n_iterations: Number of bootstrap iterations
        confidence_level: Confidence level for the interval (default: 0.95 for 95% CI)
        random_state: Random seed for reproducibility
        
    Returns:
        Dictionary with bootstrap results
    """
    # Make predictions
    y_pred = model.predict(X)
    
    # Calculate base metric
    base_metric = metric_func(y, y_pred)
    
    # Initialize array to store bootstrap results
    bootstrap_metrics = np.zeros(n_iterations)
    
    # Set random state for reproducibility
    rng = np.random.RandomState(random_state)
    
    # Perform bootstrap iterations
    for i in range(n_iterations):
        # Generate bootstrap sample indices
        indices = rng.randint(0, len(y), size=len(y))
        
        # Calculate metric on bootstrap sample
        bootstrap_metrics[i] = metric_func(y[indices], y_pred[indices])
    
    # Calculate confidence interval
    alpha = 1.0 - confidence_level
    lower_percentile = alpha / 2.0 * 100
    upper_percentile = (1.0 - alpha / 2.0) * 100
    lower_bound = np.percentile(bootstrap_metrics, lower_percentile)
    upper_bound = np.percentile(bootstrap_metrics, upper_percentile)
    
    logger.info(f"Bootstrap {metric_func.__name__} estimate: {base_metric:.4f} "
               f"[{lower_bound:.4f}, {upper_bound:.4f}] ({confidence_level*100:.1f}% CI)")
    
    return {
        'base_metric': float(base_metric),
        'lower_bound': float(lower_bound),
        'upper_bound': float(upper_bound),
        'confidence_level': confidence_level,
        'n_iterations': n_iterations,
        'bootstrap_samples': bootstrap_metrics.tolist()
    }


class ThresholdClassifier:
    """Wrapper for classification models that applies a custom decision threshold.
    
    This class wraps a classifier that provides predict_proba and allows setting
    a custom threshold for binary classification decisions.
    """
    
    def __init__(self, classifier: ClassificationModel, threshold: float = 0.5):
        """Initialize the threshold classifier.
        
        Args:
            classifier: Base classification model that provides predict_proba
            threshold: Decision threshold for positive class (default: 0.5)
        """
        self.classifier = classifier
        self.threshold = threshold
    
    def fit(self, X: np.ndarray, y: np.ndarray) -> 'ThresholdClassifier':
        """Fit the underlying classifier.
        
        Args:
            X: Feature matrix
            y: Target labels
            
        Returns:
            Self instance
        """
        self.classifier.fit(X, y)
        return self
    
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict class labels using the custom threshold.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predicted class labels
        """
        y_prob = self.classifier.predict_proba(X)[:, 1]
        return (y_prob >= self.threshold).astype(int)
    
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Predict class probabilities.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predicted class probabilities
        """
        return self.classifier.predict_proba(X)
    
    def get_confidence_scores(self, X: np.ndarray) -> List[ConfidenceScore]:
        """Get confidence scores for predictions.
        
        Args:
            X: Feature matrix
            
        Returns:
            List of confidence scores for each prediction
        """
        probas = self.predict_proba(X)
        predictions = self.predict(X)
        
        confidence_scores = []
        for i, (proba, pred) in enumerate(zip(probas, predictions)):
            # For binary classification
            if probas.shape[1] == 2:
                confidence = float(proba[1]) if pred == 1 else float(proba[0])
            else:  # For multi-class
                confidence = float(proba[pred])
            
            confidence_scores.append({
                'prediction': int(pred),
                'confidence': confidence,
                'meets_threshold': confidence >= self.threshold
            })
        
        return confidence_scores