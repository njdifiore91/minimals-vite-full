#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Evaluation Utilities for Document Classification

This module provides utilities for evaluating the performance of document classification models
in the Document Service. It implements metrics calculation, confusion matrix analysis,
ROC curve generation, and performance reporting to ensure models meet accuracy requirements.

The module supports the following key functionalities:
1. Classification metrics calculation (accuracy, precision, recall, F1)
2. Confusion matrix analysis and visualization
3. ROC curve and AUC calculation for model comparison
4. Cross-validation performance reporting
5. Threshold optimization for classification confidence

These utilities help ensure that document classification models maintain the required
99% data extraction accuracy as specified in the technical requirements.
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from typing import Dict, List, Tuple, Union, Optional, Any
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
    roc_curve,
    auc,
    roc_auc_score,
    precision_recall_curve,
    average_precision_score
)
from sklearn.model_selection import cross_val_score, StratifiedKFold, learning_curve
from sklearn.calibration import calibration_curve
import logging
from pathlib import Path
import os
import json

# Configure logger
logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Class for evaluating document classification models.
    
    This class provides methods for calculating classification metrics,
    generating confusion matrices, ROC curves, and performing cross-validation
    to ensure models meet the required 99% accuracy threshold.
    
    The evaluator implements comprehensive model assessment capabilities to validate
    that document classification models meet the technical requirements for the
    Document Service, particularly the 99% data extraction accuracy requirement.
    """
    
    def __init__(self, accuracy_threshold: float = 0.99):
        """Initialize the ModelEvaluator.
        
        Args:
            accuracy_threshold: Minimum required accuracy threshold (default: 0.99)
        """
        self.accuracy_threshold = accuracy_threshold
        logger.info(f"ModelEvaluator initialized with accuracy threshold: {accuracy_threshold}")
    
    def calculate_metrics(self, y_true: np.ndarray, y_pred: np.ndarray, 
                         labels: Optional[List] = None) -> Dict[str, float]:
        """Calculate classification metrics.
        
        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            labels: List of label names (optional)
            
        Returns:
            Dictionary containing accuracy, precision, recall, and F1 score
        """
        metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'precision_micro': precision_score(y_true, y_pred, average='micro'),
            'precision_macro': precision_score(y_true, y_pred, average='macro'),
            'precision_weighted': precision_score(y_true, y_pred, average='weighted'),
            'recall_micro': recall_score(y_true, y_pred, average='micro'),
            'recall_macro': recall_score(y_true, y_pred, average='macro'),
            'recall_weighted': recall_score(y_true, y_pred, average='weighted'),
            'f1_micro': f1_score(y_true, y_pred, average='micro'),
            'f1_macro': f1_score(y_true, y_pred, average='macro'),
            'f1_weighted': f1_score(y_true, y_pred, average='weighted')
        }
        
        logger.info(f"Classification metrics: accuracy={metrics['accuracy']:.4f}, "
                  f"precision_weighted={metrics['precision_weighted']:.4f}, "
                  f"recall_weighted={metrics['recall_weighted']:.4f}, "
                  f"f1_weighted={metrics['f1_weighted']:.4f}")
        
        # Check if accuracy meets the threshold
        if metrics['accuracy'] < self.accuracy_threshold:
            logger.warning(f"Model accuracy {metrics['accuracy']:.4f} is below the required threshold "
                          f"of {self.accuracy_threshold}")
        
        return metrics
    
    def generate_classification_report(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                      target_names: Optional[List[str]] = None) -> str:
        """Generate a detailed classification report.
        
        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            target_names: List of target class names (optional)
            
        Returns:
            String containing the classification report
        """
        report = classification_report(y_true, y_pred, target_names=target_names)
        logger.info(f"Classification report:\n{report}")
        return report
    
    def plot_confusion_matrix(self, y_true: np.ndarray, y_pred: np.ndarray, 
                             class_names: Optional[List[str]] = None, 
                             normalize: bool = False,
                             cmap: str = 'Blues',
                             figsize: Tuple[int, int] = (10, 8),
                             save_path: Optional[str] = None,
                             use_seaborn: bool = True) -> np.ndarray:
        """Generate and plot a confusion matrix.
        
        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            class_names: List of class names (optional)
            normalize: Whether to normalize the confusion matrix (default: False)
            cmap: Colormap for the plot (default: 'Blues')
            figsize: Figure size as (width, height) in inches (default: (10, 8))
            save_path: Path to save the figure (optional)
            use_seaborn: Whether to use seaborn for enhanced visualization (default: True)
            
        Returns:
            Confusion matrix as numpy array
        """
        # Compute confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        # Normalize if requested
        if normalize:
            cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
            title = 'Normalized Confusion Matrix'
        else:
            title = 'Confusion Matrix'
        
        # Plot the confusion matrix
        plt.figure(figsize=figsize)
        
        if use_seaborn:
            # Use seaborn for enhanced visualization
            df_cm = pd.DataFrame(cm, index=class_names if class_names is not None else None,
                               columns=class_names if class_names is not None else None)
            
            # Create a more visually appealing heatmap
            sns.heatmap(df_cm, annot=True, fmt='.2f' if normalize else 'd',
                      cmap=cmap, cbar=True, linewidths=0.5,
                      annot_kws={"size": 10 if cm.shape[0] > 10 else 12})
            plt.title(title, fontsize=14)
            plt.ylabel('True Label', fontsize=12)
            plt.xlabel('Predicted Label', fontsize=12)
        else:
            # Use matplotlib for basic visualization
            plt.imshow(cm, interpolation='nearest', cmap=plt.cm.get_cmap(cmap))
            plt.title(title, fontsize=14)
            plt.colorbar()
            
            # Add class labels
            if class_names is not None:
                tick_marks = np.arange(len(class_names))
                plt.xticks(tick_marks, class_names, rotation=45, ha='right')
                plt.yticks(tick_marks, class_names)
            
            # Add text annotations to each cell
            fmt = '.2f' if normalize else 'd'
            thresh = cm.max() / 2.
            for i in range(cm.shape[0]):
                for j in range(cm.shape[1]):
                    plt.text(j, i, format(cm[i, j], fmt),
                            ha="center", va="center",
                            color="white" if cm[i, j] > thresh else "black")
            
            plt.ylabel('True Label', fontsize=12)
            plt.xlabel('Predicted Label', fontsize=12)
        
        plt.tight_layout()
        
        # Save the figure if a path is provided
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            logger.info(f"Confusion matrix saved to {save_path}")
        
        plt.show()
        return cm
    
    def plot_roc_curve(self, y_true: np.ndarray, y_score: np.ndarray, 
                      class_names: Optional[List[str]] = None,
                      figsize: Tuple[int, int] = (10, 8),
                      save_path: Optional[str] = None) -> Dict[str, float]:
        """Generate and plot ROC curves for each class.
        
        Args:
            y_true: Ground truth labels (one-hot encoded for multiclass)
            y_score: Predicted probabilities
            class_names: List of class names (optional)
            figsize: Figure size as (width, height) in inches (default: (10, 8))
            save_path: Path to save the figure (optional)
            
        Returns:
            Dictionary containing AUC scores for each class
        """
        # For binary classification
        if len(y_score.shape) == 1 or y_score.shape[1] == 2:
            if len(y_score.shape) == 2:  # If probabilities for both classes are provided
                y_score = y_score[:, 1]  # Take the probability of the positive class
            
            fpr, tpr, _ = roc_curve(y_true, y_score)
            roc_auc = auc(fpr, tpr)
            
            plt.figure(figsize=figsize)
            plt.plot(fpr, tpr, lw=2, label=f'ROC curve (area = {roc_auc:.2f})')
            plt.plot([0, 1], [0, 1], 'k--', lw=2)
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate', fontsize=12)
            plt.ylabel('True Positive Rate', fontsize=12)
            plt.title('Receiver Operating Characteristic (ROC) Curve', fontsize=14)
            plt.legend(loc="lower right")
            
            if save_path:
                plt.savefig(save_path, bbox_inches='tight', dpi=300)
                logger.info(f"ROC curve saved to {save_path}")
            
            plt.show()
            return {'auc': roc_auc}
        
        # For multiclass classification
        else:
            n_classes = y_score.shape[1]
            
            # Compute ROC curve and ROC area for each class
            fpr = {}
            tpr = {}
            roc_auc = {}
            
            for i in range(n_classes):
                fpr[i], tpr[i], _ = roc_curve(y_true[:, i], y_score[:, i])
                roc_auc[i] = auc(fpr[i], tpr[i])
            
            # Plot all ROC curves
            plt.figure(figsize=figsize)
            
            # Plot the micro-average ROC curve
            fpr_micro, tpr_micro, _ = roc_curve(y_true.ravel(), y_score.ravel())
            roc_auc_micro = auc(fpr_micro, tpr_micro)
            plt.plot(fpr_micro, tpr_micro,
                    label=f'micro-average ROC curve (area = {roc_auc_micro:.2f})',
                    color='deeppink', linestyle=':', linewidth=4)
            
            # Plot the macro-average ROC curve
            all_fpr = np.unique(np.concatenate([fpr[i] for i in range(n_classes)]))
            mean_tpr = np.zeros_like(all_fpr)
            for i in range(n_classes):
                mean_tpr += np.interp(all_fpr, fpr[i], tpr[i])
            mean_tpr /= n_classes
            
            roc_auc_macro = auc(all_fpr, mean_tpr)
            plt.plot(all_fpr, mean_tpr,
                    label=f'macro-average ROC curve (area = {roc_auc_macro:.2f})',
                    color='navy', linestyle=':', linewidth=4)
            
            # Plot ROC curves for each class
            colors = plt.cm.get_cmap('tab10')(np.linspace(0, 1, n_classes))
            for i, color in zip(range(n_classes), colors):
                class_name = class_names[i] if class_names is not None else f'Class {i}'
                plt.plot(fpr[i], tpr[i], color=color, lw=2,
                        label=f'ROC curve of {class_name} (area = {roc_auc[i]:.2f})')
            
            plt.plot([0, 1], [0, 1], 'k--', lw=2)
            plt.xlim([0.0, 1.0])
            plt.ylim([0.0, 1.05])
            plt.xlabel('False Positive Rate', fontsize=12)
            plt.ylabel('True Positive Rate', fontsize=12)
            plt.title('Receiver Operating Characteristic (ROC) Curve for Multi-class', fontsize=14)
            plt.legend(loc="lower right")
            
            if save_path:
                plt.savefig(save_path, bbox_inches='tight', dpi=300)
                logger.info(f"ROC curve saved to {save_path}")
            
            plt.show()
            
            # Return AUC scores
            auc_scores = {f'class_{i}': roc_auc[i] for i in range(n_classes)}
            auc_scores['micro'] = roc_auc_micro
            auc_scores['macro'] = roc_auc_macro
            
            return auc_scores
    
    def cross_validate(self, model: Any, X: np.ndarray, y: np.ndarray, 
                      cv: int = 5, scoring: str = 'accuracy') -> Dict[str, float]:
        """Perform cross-validation to evaluate model performance.
        
        Args:
            model: Classifier model with fit and predict methods
            X: Feature matrix
            y: Target labels
            cv: Number of cross-validation folds (default: 5)
            scoring: Scoring metric to use (default: 'accuracy')
            
        Returns:
            Dictionary containing cross-validation results
        """
        # Define cross-validation strategy
        cv_strategy = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)
        
        # Perform cross-validation
        cv_scores = cross_val_score(model, X, y, cv=cv_strategy, scoring=scoring)
        
        # Calculate statistics
        cv_results = {
            'mean_score': np.mean(cv_scores),
            'std_score': np.std(cv_scores),
            'min_score': np.min(cv_scores),
            'max_score': np.max(cv_scores),
            'all_scores': cv_scores
        }
        
        logger.info(f"Cross-validation results ({scoring}): "
                  f"mean={cv_results['mean_score']:.4f}, "
                  f"std={cv_results['std_score']:.4f}, "
                  f"min={cv_results['min_score']:.4f}, "
                  f"max={cv_results['max_score']:.4f}")
        
        # Check if mean score meets the threshold
        if scoring == 'accuracy' and cv_results['mean_score'] < self.accuracy_threshold:
            logger.warning(f"Cross-validation accuracy {cv_results['mean_score']:.4f} "
                          f"is below the required threshold of {self.accuracy_threshold}")
        
        return cv_results
    
    def optimize_threshold(self, y_true: np.ndarray, y_score: np.ndarray, 
                         metric: str = 'f1') -> Dict[str, Union[float, np.ndarray]]:
        """Optimize classification threshold based on a specified metric.
        
        Args:
            y_true: Ground truth binary labels
            y_score: Predicted probabilities for the positive class
            metric: Metric to optimize ('f1', 'accuracy', 'precision', or 'recall')
            
        Returns:
            Dictionary containing optimal threshold and corresponding predictions
        """
        # Validate inputs
        if metric not in ['f1', 'accuracy', 'precision', 'recall']:
            raise ValueError("Metric must be one of: 'f1', 'accuracy', 'precision', 'recall'")
        
        # Generate a range of thresholds to evaluate
        thresholds = np.linspace(0.01, 0.99, 99)
        scores = []
        
        # Evaluate each threshold
        for threshold in thresholds:
            y_pred = (y_score >= threshold).astype(int)
            
            if metric == 'f1':
                score = f1_score(y_true, y_pred)
            elif metric == 'accuracy':
                score = accuracy_score(y_true, y_pred)
            elif metric == 'precision':
                score = precision_score(y_true, y_pred)
            elif metric == 'recall':
                score = recall_score(y_true, y_pred)
            
            scores.append(score)
        
        # Find the threshold that maximizes the metric
        best_idx = np.argmax(scores)
        optimal_threshold = thresholds[best_idx]
        optimal_score = scores[best_idx]
        optimal_predictions = (y_score >= optimal_threshold).astype(int)
        
        logger.info(f"Optimal threshold: {optimal_threshold:.4f} with {metric} score: {optimal_score:.4f}")
        
        # Plot threshold vs. metric
        plt.figure(figsize=(10, 6))
        plt.plot(thresholds, scores, 'b-')
        plt.axvline(x=optimal_threshold, color='r', linestyle='--')
        plt.xlabel('Threshold', fontsize=12)
        plt.ylabel(f'{metric.capitalize()} Score', fontsize=12)
        plt.title(f'Threshold Optimization for {metric.capitalize()}', fontsize=14)
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
        
        return {
            'optimal_threshold': optimal_threshold,
            'optimal_score': optimal_score,
            'optimal_predictions': optimal_predictions,
            'thresholds': thresholds,
            'scores': np.array(scores)
        }
    
    def generate_performance_report(self, y_true: np.ndarray, y_pred: np.ndarray, 
                                  y_score: Optional[np.ndarray] = None,
                                  class_names: Optional[List[str]] = None) -> Dict[str, Any]:
        """Generate a comprehensive performance report.
        
        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            y_score: Predicted probabilities (optional)
            class_names: List of class names (optional)
            
        Returns:
            Dictionary containing all performance metrics and reports
        """
        # Calculate basic metrics
        metrics = self.calculate_metrics(y_true, y_pred)
        
        # Generate classification report
        report = self.generate_classification_report(y_true, y_pred, target_names=class_names)
        
        # Compute confusion matrix (without plotting)
        cm = confusion_matrix(y_true, y_pred)
        
        # Initialize results dictionary
        results = {
            'metrics': metrics,
            'classification_report': report,
            'confusion_matrix': cm
        }
        
        # Add ROC AUC if probabilities are provided
        if y_score is not None:
            try:
                # For binary classification
                if len(np.unique(y_true)) == 2:
                    if len(y_score.shape) == 2:  # If probabilities for both classes are provided
                        y_score_binary = y_score[:, 1]  # Take the probability of the positive class
                    else:
                        y_score_binary = y_score
                    
                    results['roc_auc'] = roc_auc_score(y_true, y_score_binary)
                    logger.info(f"ROC AUC: {results['roc_auc']:.4f}")
                
                # For multiclass classification
                else:
                    # One-hot encode the true labels if they're not already
                    from sklearn.preprocessing import label_binarize
                    classes = np.unique(y_true)
                    y_true_bin = label_binarize(y_true, classes=classes)
                    
                    if len(y_score.shape) == 1 or y_score.shape[1] == 1:
                        logger.warning("Multiclass ROC AUC requires probability estimates for each class")
                    else:
                        results['roc_auc_ovr'] = roc_auc_score(y_true_bin, y_score, multi_class='ovr')
                        results['roc_auc_ovo'] = roc_auc_score(y_true_bin, y_score, multi_class='ovo')
                        logger.info(f"ROC AUC (OvR): {results['roc_auc_ovr']:.4f}, "
                                  f"ROC AUC (OvO): {results['roc_auc_ovo']:.4f}")
            except Exception as e:
                logger.warning(f"Could not calculate ROC AUC: {str(e)}")
        
        # Check if performance meets requirements
        meets_requirements = metrics['accuracy'] >= self.accuracy_threshold
        results['meets_requirements'] = meets_requirements
        
        if meets_requirements:
            logger.info("Model meets the accuracy requirements")
        else:
            logger.warning(f"Model does not meet the accuracy requirement of {self.accuracy_threshold}")
        
        return results


def plot_learning_curve(model: Any, X: np.ndarray, y: np.ndarray, 
                      cv: int = 5, n_jobs: int = -1, train_sizes: np.ndarray = np.linspace(0.1, 1.0, 10),
                      figsize: Tuple[int, int] = (10, 6), save_path: Optional[str] = None) -> Dict[str, np.ndarray]:
    """Plot learning curve to evaluate model performance with varying training set sizes.
    
    Args:
        model: Classifier model with fit and predict methods
        X: Feature matrix
        y: Target labels
        cv: Number of cross-validation folds (default: 5)
        n_jobs: Number of jobs to run in parallel (default: -1, all processors)
        train_sizes: Array of training set sizes to evaluate
        figsize: Figure size as (width, height) in inches (default: (10, 6))
        save_path: Path to save the figure (optional)
        
    Returns:
        Dictionary containing train sizes, train scores, and test scores
    """
    plt.figure(figsize=figsize)
    
    # Calculate learning curve
    train_sizes, train_scores, test_scores = learning_curve(
        model, X, y, cv=cv, n_jobs=n_jobs, train_sizes=train_sizes, shuffle=True, random_state=42
    )
    
    # Calculate mean and standard deviation
    train_mean = np.mean(train_scores, axis=1)
    train_std = np.std(train_scores, axis=1)
    test_mean = np.mean(test_scores, axis=1)
    test_std = np.std(test_scores, axis=1)
    
    # Plot learning curve
    plt.plot(train_sizes, train_mean, 'o-', color='r', label='Training score')
    plt.fill_between(train_sizes, train_mean - train_std, train_mean + train_std, alpha=0.1, color='r')
    plt.plot(train_sizes, test_mean, 'o-', color='g', label='Cross-validation score')
    plt.fill_between(train_sizes, test_mean - test_std, test_mean + test_std, alpha=0.1, color='g')
    
    plt.title('Learning Curve', fontsize=14)
    plt.xlabel('Training Set Size', fontsize=12)
    plt.ylabel('Accuracy Score', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        logger.info(f"Learning curve saved to {save_path}")
    
    plt.show()
    
    return {
        'train_sizes': train_sizes,
        'train_scores': train_scores,
        'test_scores': test_scores,
        'train_mean': train_mean,
        'train_std': train_std,
        'test_mean': test_mean,
        'test_std': test_std
    }


def plot_precision_recall_curve(y_true: np.ndarray, y_score: np.ndarray, 
                              class_names: Optional[List[str]] = None,
                              figsize: Tuple[int, int] = (10, 6),
                              save_path: Optional[str] = None) -> Dict[str, Any]:
    """Plot precision-recall curve for binary or multiclass classification.
    
    Args:
        y_true: Ground truth labels (one-hot encoded for multiclass)
        y_score: Predicted probabilities
        class_names: List of class names (optional)
        figsize: Figure size as (width, height) in inches (default: (10, 6))
        save_path: Path to save the figure (optional)
        
    Returns:
        Dictionary containing precision, recall, and average precision scores
    """
    plt.figure(figsize=figsize)
    
    # For binary classification
    if len(y_score.shape) == 1 or y_score.shape[1] == 2:
        if len(y_score.shape) == 2:  # If probabilities for both classes are provided
            y_score = y_score[:, 1]  # Take the probability of the positive class
        
        precision, recall, _ = precision_recall_curve(y_true, y_score)
        avg_precision = average_precision_score(y_true, y_score)
        
        plt.plot(recall, precision, lw=2, label=f'Precision-Recall curve (AP = {avg_precision:.2f})')
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title('Precision-Recall Curve', fontsize=14)
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            logger.info(f"Precision-recall curve saved to {save_path}")
        
        plt.show()
        return {
            'precision': precision,
            'recall': recall,
            'average_precision': avg_precision
        }
    
    # For multiclass classification
    else:
        n_classes = y_score.shape[1]
        precision = {}
        recall = {}
        avg_precision = {}
        
        for i in range(n_classes):
            precision[i], recall[i], _ = precision_recall_curve(y_true[:, i], y_score[:, i])
            avg_precision[i] = average_precision_score(y_true[:, i], y_score[:, i])
            
            class_name = class_names[i] if class_names is not None else f'Class {i}'
            plt.plot(recall[i], precision[i], lw=2,
                    label=f'{class_name} (AP = {avg_precision[i]:.2f})')
        
        # Calculate micro-average precision-recall curve
        precision_micro, recall_micro, _ = precision_recall_curve(y_true.ravel(), y_score.ravel())
        avg_precision_micro = average_precision_score(y_true.ravel(), y_score.ravel())
        
        plt.plot(recall_micro, precision_micro, lw=2, linestyle=':', color='black',
                label=f'micro-average (AP = {avg_precision_micro:.2f})')
        
        plt.xlabel('Recall', fontsize=12)
        plt.ylabel('Precision', fontsize=12)
        plt.title('Precision-Recall Curve for Multi-class', fontsize=14)
        plt.legend(loc="best")
        plt.grid(True, alpha=0.3)
        
        if save_path:
            plt.savefig(save_path, bbox_inches='tight', dpi=300)
            logger.info(f"Precision-recall curve saved to {save_path}")
        
        plt.show()
        
        # Return results
        results = {
            'precision': precision,
            'recall': recall,
            'average_precision': avg_precision,
            'precision_micro': precision_micro,
            'recall_micro': recall_micro,
            'average_precision_micro': avg_precision_micro
        }
        
        return results


def plot_calibration_curve(y_true: np.ndarray, y_score: np.ndarray, 
                         n_bins: int = 10, figsize: Tuple[int, int] = (10, 6),
                         save_path: Optional[str] = None) -> Dict[str, np.ndarray]:
    """Plot calibration curve to evaluate probability calibration.
    
    Args:
        y_true: Ground truth binary labels
        y_score: Predicted probabilities for the positive class
        n_bins: Number of bins for calibration curve (default: 10)
        figsize: Figure size as (width, height) in inches (default: (10, 6))
        save_path: Path to save the figure (optional)
        
    Returns:
        Dictionary containing calibration curve data
    """
    plt.figure(figsize=figsize)
    
    # Calculate calibration curve
    prob_true, prob_pred = calibration_curve(y_true, y_score, n_bins=n_bins)
    
    # Plot calibration curve
    plt.plot(prob_pred, prob_true, 's-', label='Calibration curve')
    plt.plot([0, 1], [0, 1], 'k--', label='Perfectly calibrated')
    
    plt.title('Calibration Curve', fontsize=14)
    plt.xlabel('Mean Predicted Probability', fontsize=12)
    plt.ylabel('Fraction of Positives', fontsize=12)
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=300)
        logger.info(f"Calibration curve saved to {save_path}")
    
    plt.show()
    
    return {
        'prob_true': prob_true,
        'prob_pred': prob_pred
    }


def evaluate_model_performance(model: Any, X_test: np.ndarray, y_test: np.ndarray, 
                             class_names: Optional[List[str]] = None,
                             accuracy_threshold: float = 0.99,
                             output_dir: Optional[str] = None) -> Dict[str, Any]:
    """Convenience function to evaluate a model's performance.
    
    Args:
        model: Trained classifier model with predict and predict_proba methods
        X_test: Test feature matrix
        y_test: Test target labels
        class_names: List of class names (optional)
        accuracy_threshold: Minimum required accuracy threshold (default: 0.99)
        output_dir: Directory to save evaluation results and plots (optional)
        
    Returns:
        Dictionary containing performance metrics and evaluation results
    """
    # Create evaluator
    evaluator = ModelEvaluator(accuracy_threshold=accuracy_threshold)
    
    # Create output directory if specified
    if output_dir is not None:
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"Saving evaluation results to {output_dir}")
    
    # Get predictions
    y_pred = model.predict(X_test)
    
    # Get probability scores if available
    y_score = None
    if hasattr(model, 'predict_proba'):
        try:
            y_score = model.predict_proba(X_test)
        except Exception as e:
            logger.warning(f"Could not get probability scores: {str(e)}")
    
    # Generate comprehensive performance report
    results = evaluator.generate_performance_report(y_test, y_pred, y_score, class_names)
    
    # Plot confusion matrix
    cm_save_path = os.path.join(output_dir, 'confusion_matrix.png') if output_dir else None
    cm = evaluator.plot_confusion_matrix(y_test, y_pred, class_names=class_names, save_path=cm_save_path)
    results['confusion_matrix_plot'] = cm
    
    # Plot ROC curve if probability scores are available
    if y_score is not None:
        try:
            # For binary classification
            if len(np.unique(y_test)) == 2:
                roc_save_path = os.path.join(output_dir, 'roc_curve_binary.png') if output_dir else None
                roc_results = evaluator.plot_roc_curve(y_test, y_score, save_path=roc_save_path)
                results['roc_curve'] = roc_results
            
            # For multiclass classification
            else:
                # One-hot encode the true labels
                from sklearn.preprocessing import label_binarize
                classes = np.unique(y_test)
                y_test_bin = label_binarize(y_test, classes=classes)
                
                if y_score.shape[1] == len(classes):
                    roc_save_path = os.path.join(output_dir, 'roc_curve_multiclass.png') if output_dir else None
                    roc_results = evaluator.plot_roc_curve(y_test_bin, y_score, class_names=class_names, save_path=roc_save_path)
                    results['roc_curve'] = roc_results
        except Exception as e:
            logger.warning(f"Could not plot ROC curve: {str(e)}")
    
    # Generate additional evaluation plots if output directory is specified
    if output_dir is not None and y_score is not None:
        try:
            # Generate precision-recall curve
            if len(np.unique(y_test)) == 2:
                # Binary classification
                if len(y_score.shape) == 2:  # If probabilities for both classes are provided
                    y_score_binary = y_score[:, 1]  # Take the probability of the positive class
                else:
                    y_score_binary = y_score
                
                pr_save_path = os.path.join(output_dir, 'precision_recall_curve.png')
                pr_results = plot_precision_recall_curve(y_test, y_score_binary, save_path=pr_save_path)
                results['precision_recall_curve'] = pr_results
                
                # Generate calibration curve
                cal_save_path = os.path.join(output_dir, 'calibration_curve.png')
                cal_results = plot_calibration_curve(y_test, y_score_binary, save_path=cal_save_path)
                results['calibration_curve'] = cal_results
            else:
                # Multiclass classification - one-hot encode the true labels if needed
                from sklearn.preprocessing import label_binarize
                classes = np.unique(y_test)
                y_test_bin = label_binarize(y_test, classes=classes)
                
                if y_score.shape[1] == len(classes):
                    pr_save_path = os.path.join(output_dir, 'precision_recall_curve_multiclass.png')
                    pr_results = plot_precision_recall_curve(y_test_bin, y_score, class_names=class_names, save_path=pr_save_path)
                    results['precision_recall_curve'] = pr_results
        except Exception as e:
            logger.warning(f"Could not generate additional evaluation plots: {str(e)}")
    
        # Convert numpy arrays to lists for JSON serialization
        json_results = {}
        for key, value in results.items():
            if key not in ['confusion_matrix_plot', 'roc_curve', 'optimal_predictions', 'precision_recall_curve', 'calibration_curve']:
                if isinstance(value, np.ndarray):
                    json_results[key] = value.tolist()
                elif isinstance(value, dict):
                    json_results[key] = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in value.items()}
                else:
                    json_results[key] = value
        
        # Save metrics to JSON file
        with open(os.path.join(output_dir, 'evaluation_results.json'), 'w') as f:
            json.dump(json_results, f, indent=4)
        
        logger.info(f"Evaluation results saved to {os.path.join(output_dir, 'evaluation_results.json')}")
    
    return results


if __name__ == "__main__":
    # Example usage
    from sklearn.datasets import make_classification
    from sklearn.model_selection import train_test_split
    from sklearn.ensemble import RandomForestClassifier
    import tempfile
    
    # Generate sample data
    X, y = make_classification(n_samples=1000, n_classes=3, n_features=20, n_informative=10, random_state=42)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    
    # Train a model
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)
    
    # Create a temporary directory for output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Evaluate the model and save results to the temporary directory
        results = evaluate_model_performance(
            model, X_test, y_test, 
            class_names=['Class 0', 'Class 1', 'Class 2'],
            output_dir=temp_dir
        )
        
        # Print accuracy
        print(f"Accuracy: {results['metrics']['accuracy']:.4f}")
        print(f"Results saved to: {temp_dir}")
        
        # Generate and plot learning curve
        learning_curve_path = os.path.join(temp_dir, 'learning_curve.png')
        lc_results = plot_learning_curve(model, X, y, save_path=learning_curve_path)
        print(f"Learning curve saved to: {learning_curve_path}")