#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for model evaluation utilities in the Document Service.

This module contains tests for the model evaluation utilities used to assess document
classification performance. Tests verify that the evaluation module correctly calculates
classification metrics, generates confusion matrices, produces ROC curves, and reports
performance statistics. Also tests threshold optimization for classification confidence.
"""

import os
import pytest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from unittest.mock import Mock, MagicMock, patch
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.preprocessing import label_binarize

# Import the module to be tested
from models.model_evaluation import (
    ModelEvaluator,
    plot_learning_curve,
    plot_precision_recall_curve,
    plot_calibration_curve,
    evaluate_model_performance
)


# Test ModelEvaluator initialization
def test_model_evaluator_initialization():
    """Test that ModelEvaluator initializes with the correct default threshold."""
    # Default threshold should be 0.99 (99% accuracy requirement)
    evaluator = ModelEvaluator()
    assert evaluator.accuracy_threshold == 0.99
    
    # Custom threshold
    custom_threshold = 0.95
    evaluator = ModelEvaluator(accuracy_threshold=custom_threshold)
    assert evaluator.accuracy_threshold == custom_threshold


# Test calculate_metrics method
def test_calculate_metrics(classification_metrics):
    """Test that calculate_metrics correctly computes classification metrics."""
    # Create test data
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Calculate metrics
    metrics = evaluator.calculate_metrics(y_true, y_pred)
    
    # Verify metrics
    assert metrics['accuracy'] == 1.0
    assert metrics['precision_micro'] == 1.0
    assert metrics['recall_micro'] == 1.0
    assert metrics['f1_micro'] == 1.0
    assert metrics['precision_macro'] == 1.0
    assert metrics['recall_macro'] == 1.0
    assert metrics['f1_macro'] == 1.0
    assert metrics['precision_weighted'] == 1.0
    assert metrics['recall_weighted'] == 1.0
    assert metrics['f1_weighted'] == 1.0


def test_calculate_metrics_with_errors(classification_metrics):
    """Test that calculate_metrics correctly handles prediction errors."""
    # Create test data with errors
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'invoice', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Calculate metrics
    metrics = evaluator.calculate_metrics(y_true, y_pred)
    
    # Verify metrics
    assert metrics['accuracy'] == 0.8  # 4 out of 5 correct
    assert metrics['precision_micro'] == 0.8
    assert metrics['recall_micro'] == 0.8
    assert metrics['f1_micro'] == 0.8
    
    # Macro metrics should be lower due to the imbalance
    assert metrics['precision_macro'] < 1.0
    assert metrics['recall_macro'] < 1.0
    assert metrics['f1_macro'] < 1.0


def test_calculate_metrics_below_threshold(classification_metrics):
    """Test that calculate_metrics correctly identifies when accuracy is below threshold."""
    # Create test data with errors
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'invoice', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator with 0.99 threshold
    evaluator = ModelEvaluator(accuracy_threshold=0.99)
    
    # Calculate metrics
    with pytest.warns(UserWarning, match=r"Model accuracy .* is below the required threshold"):
        metrics = evaluator.calculate_metrics(y_true, y_pred)
    
    # Verify metrics
    assert metrics['accuracy'] == 0.8  # 4 out of 5 correct
    assert metrics['accuracy'] < evaluator.accuracy_threshold


# Test generate_classification_report method
def test_generate_classification_report():
    """Test that generate_classification_report produces a valid classification report."""
    # Create test data
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Generate report
    report = evaluator.generate_classification_report(y_true, y_pred)
    
    # Verify report is a non-empty string
    assert isinstance(report, str)
    assert len(report) > 0
    
    # Verify report contains expected sections
    assert 'precision' in report
    assert 'recall' in report
    assert 'f1-score' in report
    assert 'support' in report
    assert 'accuracy' in report
    assert 'macro avg' in report
    assert 'weighted avg' in report


def test_generate_classification_report_with_target_names():
    """Test that generate_classification_report correctly uses target names."""
    # Create test data
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    target_names = ['Invoice', 'License', 'Bank Statement', 'Tax Document', 'Application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Generate report
    report = evaluator.generate_classification_report(y_true, y_pred, target_names=target_names)
    
    # Verify report contains target names
    for name in target_names:
        assert name in report


# Test plot_confusion_matrix method
@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_confusion_matrix(mock_savefig, mock_show):
    """Test that plot_confusion_matrix generates a valid confusion matrix."""
    # Create test data
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Plot confusion matrix
    cm = evaluator.plot_confusion_matrix(y_true, y_pred, class_names=class_names)
    
    # Verify confusion matrix is correct
    assert isinstance(cm, np.ndarray)
    assert cm.shape == (5, 5)  # 5x5 for 5 classes
    assert np.all(np.diag(cm) == 1)  # All diagonal elements should be 1 (correct predictions)
    assert np.sum(cm) == 5  # Total sum should be 5 (number of samples)
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_confusion_matrix_with_save_path(mock_savefig, mock_show, tmp_path):
    """Test that plot_confusion_matrix correctly saves the figure when a path is provided."""
    # Create test data
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Create save path
    save_path = os.path.join(tmp_path, 'confusion_matrix.png')
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Plot confusion matrix
    cm = evaluator.plot_confusion_matrix(y_true, y_pred, class_names=class_names, save_path=save_path)
    
    # Verify confusion matrix is correct
    assert isinstance(cm, np.ndarray)
    assert cm.shape == (5, 5)  # 5x5 for 5 classes
    
    # Verify plot was shown and saved
    mock_show.assert_called_once()
    mock_savefig.assert_called_once_with(save_path, bbox_inches='tight', dpi=300)


@patch('matplotlib.pyplot.show')
def test_plot_confusion_matrix_normalized(mock_show):
    """Test that plot_confusion_matrix correctly normalizes the confusion matrix."""
    # Create test data with some errors
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'invoice', 'bank_statement', 'tax_document', 'application']
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Plot normalized confusion matrix
    cm = evaluator.plot_confusion_matrix(y_true, y_pred, class_names=class_names, normalize=True)
    
    # Verify confusion matrix is normalized
    assert isinstance(cm, np.ndarray)
    assert cm.shape == (5, 5)  # 5x5 for 5 classes
    assert np.allclose(np.sum(cm, axis=1), np.ones(5))  # Row sums should be 1
    
    # Verify plot was shown
    mock_show.assert_called_once()


# Test plot_roc_curve method
@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_roc_curve_binary(mock_savefig, mock_show):
    """Test that plot_roc_curve correctly generates ROC curve for binary classification."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Plot ROC curve
    results = evaluator.plot_roc_curve(y_true, y_score)
    
    # Verify results
    assert 'auc' in results
    assert 0 <= results['auc'] <= 1  # AUC should be between 0 and 1
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_roc_curve_multiclass(mock_savefig, mock_show):
    """Test that plot_roc_curve correctly generates ROC curves for multiclass classification."""
    # Create multiclass classification data
    y_true = np.array([
        [1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1]
    ])
    y_score = np.array([
        [0.8, 0.05, 0.05, 0.05, 0.05],
        [0.05, 0.8, 0.05, 0.05, 0.05],
        [0.05, 0.05, 0.8, 0.05, 0.05],
        [0.05, 0.05, 0.05, 0.8, 0.05],
        [0.05, 0.05, 0.05, 0.05, 0.8]
    ])
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Plot ROC curve
    results = evaluator.plot_roc_curve(y_true, y_score, class_names=class_names)
    
    # Verify results
    assert 'micro' in results
    assert 'macro' in results
    for i in range(5):
        assert f'class_{i}' in results
        assert 0 <= results[f'class_{i}'] <= 1  # AUC should be between 0 and 1
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_roc_curve_with_save_path(mock_savefig, mock_show, tmp_path):
    """Test that plot_roc_curve correctly saves the figure when a path is provided."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    
    # Create save path
    save_path = os.path.join(tmp_path, 'roc_curve.png')
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Plot ROC curve
    results = evaluator.plot_roc_curve(y_true, y_score, save_path=save_path)
    
    # Verify results
    assert 'auc' in results
    
    # Verify plot was shown and saved
    mock_show.assert_called_once()
    mock_savefig.assert_called_once_with(save_path, bbox_inches='tight', dpi=300)


# Test cross_validate method
def test_cross_validate(synthetic_classification_data):
    """Test that cross_validate correctly performs cross-validation."""
    # Get synthetic data
    X, y = synthetic_classification_data
    
    # Create a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Perform cross-validation
    cv_results = evaluator.cross_validate(model, X, y, cv=3, scoring='accuracy')
    
    # Verify results
    assert 'mean_score' in cv_results
    assert 'std_score' in cv_results
    assert 'min_score' in cv_results
    assert 'max_score' in cv_results
    assert 'all_scores' in cv_results
    
    # Verify score ranges
    assert 0 <= cv_results['mean_score'] <= 1
    assert 0 <= cv_results['std_score'] <= 1
    assert 0 <= cv_results['min_score'] <= 1
    assert 0 <= cv_results['max_score'] <= 1
    assert len(cv_results['all_scores']) == 3  # 3-fold CV


def test_cross_validate_below_threshold(synthetic_classification_data):
    """Test that cross_validate correctly identifies when accuracy is below threshold."""
    # Get synthetic data
    X, y = synthetic_classification_data
    
    # Create a simple model (intentionally weak to get low accuracy)
    model = RandomForestClassifier(n_estimators=1, max_depth=1, random_state=42)
    
    # Initialize evaluator with high threshold
    evaluator = ModelEvaluator(accuracy_threshold=0.99)
    
    # Perform cross-validation
    with pytest.warns(UserWarning, match=r"Cross-validation accuracy .* is below the required threshold"):
        cv_results = evaluator.cross_validate(model, X, y, cv=3, scoring='accuracy')
    
    # Verify results
    assert cv_results['mean_score'] < evaluator.accuracy_threshold


# Test optimize_threshold method
def test_optimize_threshold():
    """Test that optimize_threshold correctly finds the optimal classification threshold."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6, 0.45, 0.55])
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Test with different metrics
    for metric in ['f1', 'accuracy', 'precision', 'recall']:
        # Optimize threshold
        with patch('matplotlib.pyplot.show'):
            results = evaluator.optimize_threshold(y_true, y_score, metric=metric)
        
        # Verify results
        assert 'optimal_threshold' in results
        assert 'optimal_score' in results
        assert 'optimal_predictions' in results
        assert 'thresholds' in results
        assert 'scores' in results
        
        # Verify threshold range
        assert 0 <= results['optimal_threshold'] <= 1
        assert 0 <= results['optimal_score'] <= 1
        assert len(results['optimal_predictions']) == len(y_true)


def test_optimize_threshold_invalid_metric():
    """Test that optimize_threshold raises an error for invalid metrics."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Test with invalid metric
    with pytest.raises(ValueError, match=r"Metric must be one of"):
        evaluator.optimize_threshold(y_true, y_score, metric='invalid_metric')


# Test generate_performance_report method
def test_generate_performance_report():
    """Test that generate_performance_report correctly generates a comprehensive performance report."""
    # Create test data
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_score = np.array([
        [0.8, 0.05, 0.05, 0.05, 0.05],
        [0.05, 0.8, 0.05, 0.05, 0.05],
        [0.05, 0.05, 0.8, 0.05, 0.05],
        [0.05, 0.05, 0.05, 0.8, 0.05],
        [0.05, 0.05, 0.05, 0.05, 0.8]
    ])
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Generate report
    results = evaluator.generate_performance_report(y_true, y_pred, y_score, class_names)
    
    # Verify results
    assert 'metrics' in results
    assert 'classification_report' in results
    assert 'confusion_matrix' in results
    assert 'meets_requirements' in results
    
    # Verify metrics
    assert results['metrics']['accuracy'] == 1.0
    assert results['meets_requirements'] is True


def test_generate_performance_report_below_threshold():
    """Test that generate_performance_report correctly identifies when performance is below threshold."""
    # Create test data with errors
    y_true = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    y_pred = ['invoice', 'invoice', 'bank_statement', 'tax_document', 'application']
    y_score = np.array([
        [0.8, 0.05, 0.05, 0.05, 0.05],
        [0.6, 0.3, 0.03, 0.03, 0.04],  # Incorrect prediction
        [0.05, 0.05, 0.8, 0.05, 0.05],
        [0.05, 0.05, 0.05, 0.8, 0.05],
        [0.05, 0.05, 0.05, 0.05, 0.8]
    ])
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Initialize evaluator with high threshold
    evaluator = ModelEvaluator(accuracy_threshold=0.99)
    
    # Generate report
    with pytest.warns(UserWarning, match=r"Model accuracy .* is below the required threshold"):
        results = evaluator.generate_performance_report(y_true, y_pred, y_score, class_names)
    
    # Verify results
    assert results['metrics']['accuracy'] == 0.8  # 4 out of 5 correct
    assert results['meets_requirements'] is False


# Test plot_learning_curve function
@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_learning_curve(mock_savefig, mock_show, synthetic_classification_data):
    """Test that plot_learning_curve correctly generates a learning curve."""
    # Get synthetic data
    X, y = synthetic_classification_data
    
    # Create a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    
    # Plot learning curve
    results = plot_learning_curve(model, X, y, cv=3, train_sizes=np.linspace(0.1, 1.0, 5))
    
    # Verify results
    assert 'train_sizes' in results
    assert 'train_scores' in results
    assert 'test_scores' in results
    assert 'train_mean' in results
    assert 'train_std' in results
    assert 'test_mean' in results
    assert 'test_std' in results
    
    # Verify shapes
    assert len(results['train_sizes']) == 5  # 5 train sizes
    assert results['train_scores'].shape == (5, 3)  # 5 train sizes, 3-fold CV
    assert results['test_scores'].shape == (5, 3)  # 5 train sizes, 3-fold CV
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_learning_curve_with_save_path(mock_savefig, mock_show, synthetic_classification_data, tmp_path):
    """Test that plot_learning_curve correctly saves the figure when a path is provided."""
    # Get synthetic data
    X, y = synthetic_classification_data
    
    # Create a simple model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    
    # Create save path
    save_path = os.path.join(tmp_path, 'learning_curve.png')
    
    # Plot learning curve
    results = plot_learning_curve(model, X, y, cv=3, train_sizes=np.linspace(0.1, 1.0, 5), save_path=save_path)
    
    # Verify plot was shown and saved
    mock_show.assert_called_once()
    mock_savefig.assert_called_once_with(save_path, bbox_inches='tight', dpi=300)


# Test plot_precision_recall_curve function
@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_precision_recall_curve_binary(mock_savefig, mock_show):
    """Test that plot_precision_recall_curve correctly generates a precision-recall curve for binary classification."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    
    # Plot precision-recall curve
    results = plot_precision_recall_curve(y_true, y_score)
    
    # Verify results
    assert 'precision' in results
    assert 'recall' in results
    assert 'average_precision' in results
    assert 0 <= results['average_precision'] <= 1  # AP should be between 0 and 1
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_precision_recall_curve_multiclass(mock_savefig, mock_show):
    """Test that plot_precision_recall_curve correctly generates precision-recall curves for multiclass classification."""
    # Create multiclass classification data
    y_true = np.array([
        [1, 0, 0, 0, 0],
        [0, 1, 0, 0, 0],
        [0, 0, 1, 0, 0],
        [0, 0, 0, 1, 0],
        [0, 0, 0, 0, 1]
    ])
    y_score = np.array([
        [0.8, 0.05, 0.05, 0.05, 0.05],
        [0.05, 0.8, 0.05, 0.05, 0.05],
        [0.05, 0.05, 0.8, 0.05, 0.05],
        [0.05, 0.05, 0.05, 0.8, 0.05],
        [0.05, 0.05, 0.05, 0.05, 0.8]
    ])
    class_names = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
    
    # Plot precision-recall curve
    results = plot_precision_recall_curve(y_true, y_score, class_names=class_names)
    
    # Verify results
    assert 'precision' in results
    assert 'recall' in results
    assert 'average_precision' in results
    assert 'precision_micro' in results
    assert 'recall_micro' in results
    assert 'average_precision_micro' in results
    
    # Verify class-specific results
    for i in range(5):
        assert i in results['precision']
        assert i in results['recall']
        assert i in results['average_precision']
        assert 0 <= results['average_precision'][i] <= 1  # AP should be between 0 and 1
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_precision_recall_curve_with_save_path(mock_savefig, mock_show, tmp_path):
    """Test that plot_precision_recall_curve correctly saves the figure when a path is provided."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    
    # Create save path
    save_path = os.path.join(tmp_path, 'precision_recall_curve.png')
    
    # Plot precision-recall curve
    results = plot_precision_recall_curve(y_true, y_score, save_path=save_path)
    
    # Verify plot was shown and saved
    mock_show.assert_called_once()
    mock_savefig.assert_called_once_with(save_path, bbox_inches='tight', dpi=300)


# Test plot_calibration_curve function
@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_calibration_curve(mock_savefig, mock_show):
    """Test that plot_calibration_curve correctly generates a calibration curve."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 1])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3, 0.7, 0.4, 0.6, 0.45, 0.55])
    
    # Plot calibration curve
    results = plot_calibration_curve(y_true, y_score, n_bins=5)
    
    # Verify results
    assert 'prob_true' in results
    assert 'prob_pred' in results
    assert len(results['prob_true']) == 5  # 5 bins
    assert len(results['prob_pred']) == 5  # 5 bins
    
    # Verify plot was shown
    mock_show.assert_called_once()
    mock_savefig.assert_not_called()  # No save path provided


@patch('matplotlib.pyplot.show')
@patch('matplotlib.pyplot.savefig')
def test_plot_calibration_curve_with_save_path(mock_savefig, mock_show, tmp_path):
    """Test that plot_calibration_curve correctly saves the figure when a path is provided."""
    # Create binary classification data
    y_true = np.array([0, 1, 0, 1, 0])
    y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.3])
    
    # Create save path
    save_path = os.path.join(tmp_path, 'calibration_curve.png')
    
    # Plot calibration curve
    results = plot_calibration_curve(y_true, y_score, save_path=save_path)
    
    # Verify plot was shown and saved
    mock_show.assert_called_once()
    mock_savefig.assert_called_once_with(save_path, bbox_inches='tight', dpi=300)


# Test evaluate_model_performance function
@patch('models.model_evaluation.ModelEvaluator.plot_confusion_matrix')
@patch('models.model_evaluation.ModelEvaluator.plot_roc_curve')
@patch('models.model_evaluation.plot_precision_recall_curve')
@patch('models.model_evaluation.plot_calibration_curve')
@patch('models.model_evaluation.plot_learning_curve')
def test_evaluate_model_performance(mock_lc, mock_cal, mock_pr, mock_roc, mock_cm, train_test_data, tmp_path):
    """Test that evaluate_model_performance correctly evaluates a model's performance."""
    # Get train-test data
    X_train, X_test, y_train, y_test = train_test_data
    
    # Create and train a model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Create output directory
    output_dir = os.path.join(tmp_path, 'evaluation_results')
    
    # Mock the plotting functions to avoid actual plotting
    mock_cm.return_value = np.eye(5)  # Identity matrix as confusion matrix
    mock_roc.return_value = {'auc': 0.9}  # Mock ROC results
    mock_pr.return_value = {'average_precision': 0.9}  # Mock PR results
    mock_cal.return_value = {'prob_true': np.array([0.1, 0.5, 0.9]), 'prob_pred': np.array([0.2, 0.6, 0.8])}  # Mock calibration results
    
    # Evaluate model performance
    results = evaluate_model_performance(
        model, X_test, y_test, 
        class_names=['invoice', 'license', 'bank_statement', 'tax_document', 'application'],
        accuracy_threshold=0.8,  # Lower threshold for test to pass
        output_dir=output_dir
    )
    
    # Verify results
    assert 'metrics' in results
    assert 'classification_report' in results
    assert 'confusion_matrix' in results
    assert 'meets_requirements' in results
    
    # Verify output directory was created
    assert os.path.exists(output_dir)
    assert os.path.exists(os.path.join(output_dir, 'evaluation_results.json'))
    
    # Verify plotting functions were called
    mock_cm.assert_called_once()
    # Other mocks may or may not be called depending on the test data


def test_evaluate_model_performance_no_output_dir(train_test_data):
    """Test that evaluate_model_performance works correctly without an output directory."""
    # Get train-test data
    X_train, X_test, y_train, y_test = train_test_data
    
    # Create and train a model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Patch the plotting functions to avoid actual plotting
    with patch('models.model_evaluation.ModelEvaluator.plot_confusion_matrix') as mock_cm, \
         patch('models.model_evaluation.ModelEvaluator.plot_roc_curve') as mock_roc:
        
        # Mock the confusion matrix function
        mock_cm.return_value = np.eye(5)  # Identity matrix as confusion matrix
        mock_roc.return_value = {'auc': 0.9}  # Mock ROC results
        
        # Evaluate model performance without output directory
        results = evaluate_model_performance(
            model, X_test, y_test, 
            class_names=['invoice', 'license', 'bank_statement', 'tax_document', 'application'],
            accuracy_threshold=0.8  # Lower threshold for test to pass
        )
    
    # Verify results
    assert 'metrics' in results
    assert 'classification_report' in results
    assert 'confusion_matrix' in results
    assert 'meets_requirements' in results


# Test integration with real models
def test_integration_with_real_model(synthetic_classification_data):
    """Test the integration of model evaluation with a real model."""
    # Get synthetic data
    X, y = synthetic_classification_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    
    # Create and train a model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Make predictions
    y_pred = model.predict(X_test)
    y_score = model.predict_proba(X_test)
    
    # Initialize evaluator
    evaluator = ModelEvaluator(accuracy_threshold=0.7)  # Lower threshold for test to pass
    
    # Calculate metrics
    metrics = evaluator.calculate_metrics(y_test, y_pred)
    
    # Verify metrics
    assert 'accuracy' in metrics
    assert 'precision_micro' in metrics
    assert 'recall_micro' in metrics
    assert 'f1_micro' in metrics
    
    # Generate classification report
    report = evaluator.generate_classification_report(y_test, y_pred)
    assert isinstance(report, str)
    
    # Generate performance report
    with patch('matplotlib.pyplot.show'):
        results = evaluator.generate_performance_report(y_test, y_pred, y_score)
    
    # Verify performance report
    assert 'metrics' in results
    assert 'classification_report' in results
    assert 'confusion_matrix' in results
    assert 'meets_requirements' in results


# Test 99% accuracy threshold requirement
def test_99_percent_accuracy_requirement(synthetic_classification_data):
    """Test that the 99% accuracy threshold requirement is enforced."""
    # Get synthetic data
    X, y = synthetic_classification_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    
    # Create and train a model (intentionally weak to get low accuracy)
    model = RandomForestClassifier(n_estimators=1, max_depth=1, random_state=42)
    model.fit(X_train, y_train)
    
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Initialize evaluator with 99% threshold
    evaluator = ModelEvaluator(accuracy_threshold=0.99)
    
    # Calculate metrics
    with pytest.warns(UserWarning, match=r"Model accuracy .* is below the required threshold"):
        metrics = evaluator.calculate_metrics(y_test, y_pred)
    
    # Verify metrics
    assert metrics['accuracy'] < 0.99  # Accuracy should be below threshold
    
    # Generate performance report
    with pytest.warns(UserWarning, match=r"Model does not meet the accuracy requirement"):
        results = evaluator.generate_performance_report(y_test, y_pred)
    
    # Verify performance report
    assert results['meets_requirements'] is False


# Test confidence scoring for classification
def test_confidence_scoring(synthetic_classification_data):
    """Test that confidence scoring for classification is correctly evaluated."""
    # Get synthetic data
    X, y = synthetic_classification_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    
    # Create and train a model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Make predictions with probabilities
    y_pred = model.predict(X_test)
    y_score = model.predict_proba(X_test)
    
    # Initialize evaluator
    evaluator = ModelEvaluator()
    
    # Optimize threshold for confidence
    with patch('matplotlib.pyplot.show'):
        results = evaluator.optimize_threshold(y_test == y_pred, np.max(y_score, axis=1), metric='f1')
    
    # Verify results
    assert 'optimal_threshold' in results
    assert 'optimal_score' in results
    assert 'optimal_predictions' in results
    
    # Verify that high confidence predictions are more likely to be correct
    high_confidence_mask = np.max(y_score, axis=1) >= results['optimal_threshold']
    if np.any(high_confidence_mask):
        high_confidence_accuracy = np.mean(y_test[high_confidence_mask] == y_pred[high_confidence_mask])
        overall_accuracy = np.mean(y_test == y_pred)
        assert high_confidence_accuracy >= overall_accuracy


# Test performance metrics for monitoring
def test_performance_metrics_for_monitoring(synthetic_classification_data, tmp_path):
    """Test that performance metrics for monitoring are correctly generated."""
    # Get synthetic data
    X, y = synthetic_classification_data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)
    
    # Create and train a model
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_train, y_train)
    
    # Create output directory
    output_dir = os.path.join(tmp_path, 'monitoring_metrics')
    
    # Patch the plotting functions to avoid actual plotting
    with patch('models.model_evaluation.ModelEvaluator.plot_confusion_matrix') as mock_cm, \
         patch('models.model_evaluation.ModelEvaluator.plot_roc_curve') as mock_roc, \
         patch('models.model_evaluation.plot_precision_recall_curve') as mock_pr, \
         patch('models.model_evaluation.plot_calibration_curve') as mock_cal, \
         patch('models.model_evaluation.plot_learning_curve') as mock_lc:
        
        # Mock the plotting functions
        mock_cm.return_value = np.eye(5)  # Identity matrix as confusion matrix
        mock_roc.return_value = {'auc': 0.9}  # Mock ROC results
        mock_pr.return_value = {'average_precision': 0.9}  # Mock PR results
        mock_cal.return_value = {'prob_true': np.array([0.1, 0.5, 0.9]), 'prob_pred': np.array([0.2, 0.6, 0.8])}  # Mock calibration results
        
        # Evaluate model performance
        results = evaluate_model_performance(
            model, X_test, y_test, 
            class_names=['invoice', 'license', 'bank_statement', 'tax_document', 'application'],
            accuracy_threshold=0.8,  # Lower threshold for test to pass
            output_dir=output_dir
        )
    
    # Verify output directory was created
    assert os.path.exists(output_dir)
    assert os.path.exists(os.path.join(output_dir, 'evaluation_results.json'))
    
    # Verify metrics file contains required metrics
    with open(os.path.join(output_dir, 'evaluation_results.json'), 'r') as f:
        import json
        metrics_json = json.load(f)
    
    # Verify metrics
    assert 'metrics' in metrics_json
    assert 'accuracy' in metrics_json['metrics']
    assert 'precision_weighted' in metrics_json['metrics']
    assert 'recall_weighted' in metrics_json['metrics']
    assert 'f1_weighted' in metrics_json['metrics']


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])