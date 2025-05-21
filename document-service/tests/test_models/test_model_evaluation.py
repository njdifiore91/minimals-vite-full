import pytest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from unittest.mock import patch, MagicMock
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.calibration import CalibratedClassifierCV

# Import the module under test
from ...src.models.model_evaluation import (
    calculate_classification_metrics,
    generate_confusion_matrix,
    generate_roc_curve,
    cross_validation_performance,
    optimize_threshold,
    calibrate_confidence_scores,
    compare_models,
    evaluate_model_performance,
    generate_precision_recall_curve,
    plot_learning_curve,
    bootstrap_confidence_interval,
    ThresholdClassifier,
    sigmoid,
    softmax
)

# Import model config for testing
from ...src.config import model_config


# Patch plt.show to avoid displaying plots during tests
@pytest.fixture(autouse=True)
def no_show_plots():
    with patch('matplotlib.pyplot.show'):
        yield


# Test calculate_classification_metrics function
class TestCalculateClassificationMetrics:
    def test_perfect_predictions(self):
        """Test with perfect predictions."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'c', 'a', 'b'])
        
        metrics = calculate_classification_metrics(y_true, y_pred)
        
        assert metrics['accuracy'] == 1.0
        assert metrics['precision'] == 1.0
        assert metrics['recall'] == 1.0
        assert metrics['f1'] == 1.0
    
    def test_imperfect_predictions(self):
        """Test with imperfect predictions."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'a', 'a', 'c'])
        
        metrics = calculate_classification_metrics(y_true, y_pred)
        
        assert metrics['accuracy'] == 0.6
        assert 0.0 <= metrics['precision'] <= 1.0
        assert 0.0 <= metrics['recall'] <= 1.0
        assert 0.0 <= metrics['f1'] <= 1.0
    
    def test_different_average_methods(self):
        """Test with different averaging methods."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'a', 'a', 'c'])
        
        metrics_weighted = calculate_classification_metrics(y_true, y_pred, average='weighted')
        metrics_macro = calculate_classification_metrics(y_true, y_pred, average='macro')
        metrics_micro = calculate_classification_metrics(y_true, y_pred, average='micro')
        
        # Accuracy should be the same regardless of averaging method
        assert metrics_weighted['accuracy'] == metrics_macro['accuracy'] == metrics_micro['accuracy']
        
        # Other metrics may differ
        assert metrics_weighted['precision'] != metrics_macro['precision'] or metrics_weighted['precision'] != metrics_micro['precision']
    
    def test_warning_below_threshold(self, caplog):
        """Test that a warning is logged when accuracy is below the required threshold."""
        # Mock the required accuracy threshold
        original_required_accuracy = model_config.REQUIRED_ACCURACY
        model_config.REQUIRED_ACCURACY = 0.9
        
        y_true = np.array(['a', 'b', 'c', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'a', 'a', 'c'])
        
        calculate_classification_metrics(y_true, y_pred)
        
        # Check that a warning was logged
        assert any("below the required threshold" in record.message for record in caplog.records)
        
        # Restore the original threshold
        model_config.REQUIRED_ACCURACY = original_required_accuracy
    
    def test_zero_division_handling(self):
        """Test handling of zero division in metrics calculation."""
        # Create a case where a class is predicted but doesn't exist in ground truth
        y_true = np.array(['a', 'b', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'c', 'c'])  # 'c' doesn't exist in y_true
        
        metrics = calculate_classification_metrics(y_true, y_pred)
        
        # Should not raise ZeroDivisionError
        assert 0.0 <= metrics['precision'] <= 1.0
        assert 0.0 <= metrics['recall'] <= 1.0
        assert 0.0 <= metrics['f1'] <= 1.0


# Test generate_confusion_matrix function
class TestGenerateConfusionMatrix:
    def test_confusion_matrix_generation(self):
        """Test basic confusion matrix generation."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b', 'c', 'a', 'b', 'c'])
        y_pred = np.array(['a', 'b', 'c', 'a', 'b', 'a', 'b', 'c', 'c'])
        class_names = ['a', 'b', 'c']
        
        with patch('matplotlib.pyplot.savefig'):
            cm = generate_confusion_matrix(y_true, y_pred, class_names=class_names)
        
        # Check dimensions
        assert cm.shape == (3, 3)
        
        # Check specific values
        assert cm[0, 0] == 2  # True a, predicted a
        assert cm[0, 1] == 1  # True a, predicted b
        assert cm[0, 2] == 0  # True a, predicted c
        assert cm[2, 0] == 1  # True c, predicted a
    
    def test_normalized_confusion_matrix(self):
        """Test normalized confusion matrix."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b', 'c'])
        y_pred = np.array(['a', 'b', 'a', 'a', 'b', 'c'])
        
        with patch('matplotlib.pyplot.savefig'):
            cm_norm = generate_confusion_matrix(y_true, y_pred, normalize='true')
        
        # Check that rows sum to 1 (normalized by true labels)
        for row in cm_norm:
            assert np.isclose(np.sum(row), 1.0)
    
    def test_save_confusion_matrix(self, tmp_path):
        """Test saving confusion matrix to file."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'a', 'a', 'c'])
        save_path = str(tmp_path / "confusion_matrix.png")
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            generate_confusion_matrix(y_true, y_pred, save_path=save_path)
            
        # Check that savefig was called with the correct path
        mock_savefig.assert_called_once_with(save_path)
    
    def test_seaborn_vs_matplotlib(self):
        """Test both seaborn and matplotlib visualization methods."""
        y_true = np.array(['a', 'b', 'c', 'a', 'b'])
        y_pred = np.array(['a', 'b', 'a', 'a', 'c'])
        
        with patch('matplotlib.pyplot.savefig'):
            # Test with seaborn
            cm_seaborn = generate_confusion_matrix(y_true, y_pred, use_seaborn=True)
            
            # Test with matplotlib
            cm_matplotlib = generate_confusion_matrix(y_true, y_pred, use_seaborn=False)
        
        # Both methods should produce the same confusion matrix
        np.testing.assert_array_equal(cm_seaborn, cm_matplotlib)


# Test generate_roc_curve function
class TestGenerateROCCurve:
    def test_binary_classification_roc(self):
        """Test ROC curve generation for binary classification."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4, 0.9, 0.1])
        
        with patch('matplotlib.pyplot.savefig'):
            fpr, tpr, thresholds, roc_auc = generate_roc_curve(y_true, y_score)
        
        # Check that FPR and TPR have the same length
        assert len(fpr) == len(tpr)
        
        # Check that FPR and thresholds have the same length
        assert len(fpr) == len(thresholds)
        
        # Check that AUC is between 0 and 1
        assert 0.0 <= roc_auc <= 1.0
        
        # For this example, AUC should be high (good classifier)
        assert roc_auc > 0.8
    
    def test_multiclass_roc(self):
        """Test ROC curve generation for multi-class classification."""
        # One-hot encoded true labels
        y_true = np.array([
            [1, 0, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 0],
            [0, 1, 0]
        ])
        
        # Predicted probabilities
        y_score = np.array([
            [0.8, 0.1, 0.1],
            [0.2, 0.7, 0.1],
            [0.1, 0.2, 0.7],
            [0.7, 0.2, 0.1],
            [0.1, 0.8, 0.1]
        ])
        
        with patch('matplotlib.pyplot.savefig'):
            # Test ROC for class 0
            fpr0, tpr0, _, auc0 = generate_roc_curve(y_true, y_score, class_index=0)
            
            # Test ROC for class 1
            fpr1, tpr1, _, auc1 = generate_roc_curve(y_true, y_score, class_index=1)
        
        # Check that AUCs are between 0 and 1
        assert 0.0 <= auc0 <= 1.0
        assert 0.0 <= auc1 <= 1.0
        
        # For this example, AUCs should be high (good classifier)
        assert auc0 > 0.8
        assert auc1 > 0.8
    
    def test_save_roc_curve(self, tmp_path):
        """Test saving ROC curve to file."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4])
        save_path = str(tmp_path / "roc_curve.png")
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            generate_roc_curve(y_true, y_score, save_path=save_path)
            
        # Check that savefig was called with the correct path
        mock_savefig.assert_called_once_with(save_path)
    
    def test_roc_with_different_class_indices(self):
        """Test ROC curve generation with different class indices."""
        # Multi-class probabilities
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_score = np.array([
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.1, 0.1, 0.8],
            [0.7, 0.2, 0.1],
            [0.2, 0.7, 0.1],
            [0.1, 0.2, 0.7]
        ])
        
        with patch('matplotlib.pyplot.savefig'):
            # Test ROC for class 0
            _, _, _, auc0 = generate_roc_curve(y_true, y_score, class_index=0)
            
            # Test ROC for class 1
            _, _, _, auc1 = generate_roc_curve(y_true, y_score, class_index=1)
            
            # Test ROC for class 2
            _, _, _, auc2 = generate_roc_curve(y_true, y_score, class_index=2)
        
        # All AUCs should be high for this perfect classifier
        assert auc0 > 0.9
        assert auc1 > 0.9
        assert auc2 > 0.9


# Test cross_validation_performance function
class TestCrossValidationPerformance:
    def test_cross_validation_basic(self):
        """Test basic cross-validation performance evaluation."""
        # Create a simple dataset
        X = np.random.random((100, 10))
        y = np.random.choice(['a', 'b', 'c'], size=100)
        
        # Create a simple model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Run cross-validation
        cv_results = cross_validation_performance(model, X, y, cv=3)
        
        # Check that results contain expected metrics
        assert 'accuracy' in cv_results
        assert 'precision' in cv_results
        assert 'recall' in cv_results
        assert 'f1' in cv_results
        
        # Check that each metric has mean, std, and values
        for metric in ['accuracy', 'precision', 'recall', 'f1']:
            assert 'mean' in cv_results[metric]
            assert 'std' in cv_results[metric]
            assert 'values' in cv_results[metric]
            
            # Check that mean and std are floats
            assert isinstance(cv_results[metric]['mean'], float)
            assert isinstance(cv_results[metric]['std'], float)
            
            # Check that values is a list of length cv
            assert isinstance(cv_results[metric]['values'], list)
            assert len(cv_results[metric]['values']) == 3
    
    def test_cross_validation_with_return_estimator(self):
        """Test cross-validation with return_estimator=True."""
        # Create a simple dataset
        X = np.random.random((50, 5))
        y = np.random.choice(['a', 'b'], size=50)
        
        # Create a simple model
        model = SVC(probability=True, random_state=42)
        
        # Run cross-validation with return_estimator=True
        cv_results, estimators = cross_validation_performance(
            model, X, y, cv=2, return_estimator=True
        )
        
        # Check that estimators is a list of trained models
        assert isinstance(estimators, list)
        assert len(estimators) == 2  # cv=2
        assert all(isinstance(est, SVC) for est in estimators)
    
    def test_warning_below_threshold(self, caplog):
        """Test that a warning is logged when accuracy is below the required threshold."""
        # Create a dataset with random labels (should give ~50% accuracy for binary classification)
        X = np.random.random((50, 5))
        y = np.random.choice([0, 1], size=50)
        
        # Create a simple model
        model = RandomForestClassifier(n_estimators=2, random_state=42)
        
        # Mock the required accuracy threshold
        original_required_accuracy = model_config.REQUIRED_ACCURACY
        model_config.REQUIRED_ACCURACY = 0.9  # Set high threshold
        
        # Run cross-validation
        cross_validation_performance(model, X, y, cv=2)
        
        # Check that a warning was logged
        assert any("below the required threshold" in record.message for record in caplog.records)
        
        # Restore the original threshold
        model_config.REQUIRED_ACCURACY = original_required_accuracy
    
    def test_different_scoring_metrics(self):
        """Test cross-validation with different scoring metrics."""
        # Create a simple dataset
        X = np.random.random((60, 8))
        y = np.random.choice(['a', 'b', 'c'], size=60)
        
        # Create a simple model
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        
        # Run cross-validation with different scoring metrics
        cv_results_accuracy = cross_validation_performance(
            model, X, y, cv=3, scoring='accuracy'
        )
        
        cv_results_f1 = cross_validation_performance(
            model, X, y, cv=3, scoring='f1_weighted'
        )
        
        # Both should return the same metrics
        assert set(cv_results_accuracy.keys()) == set(cv_results_f1.keys())


# Test optimize_threshold function
class TestOptimizeThreshold:
    def test_optimize_threshold_binary(self):
        """Test threshold optimization for binary classification."""
        # Create binary classification data
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4, 0.9, 0.1])
        
        with patch('matplotlib.pyplot.savefig'):
            # Optimize for F1 score
            optimal_threshold, metrics = optimize_threshold(y_true, y_score, metric='f1')
        
        # Check that optimal threshold is between 0 and 1
        assert 0.0 <= optimal_threshold <= 1.0
        
        # Check that metrics contains expected keys
        assert 'threshold' in metrics
        assert 'accuracy' in metrics
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1' in metrics
        
        # Check that threshold in metrics matches the returned optimal threshold
        assert metrics['threshold'] == optimal_threshold
    
    def test_optimize_different_metrics(self):
        """Test threshold optimization with different metrics."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4, 0.9, 0.1])
        
        with patch('matplotlib.pyplot.savefig'):
            # Optimize for different metrics
            threshold_f1, _ = optimize_threshold(y_true, y_score, metric='f1')
            threshold_accuracy, _ = optimize_threshold(y_true, y_score, metric='accuracy')
            threshold_precision, _ = optimize_threshold(y_true, y_score, metric='precision')
            threshold_recall, _ = optimize_threshold(y_true, y_score, metric='recall')
        
        # Different metrics may lead to different optimal thresholds
        # At least one pair should be different
        thresholds = [threshold_f1, threshold_accuracy, threshold_precision, threshold_recall]
        assert len(set(thresholds)) > 1
    
    def test_custom_thresholds(self):
        """Test threshold optimization with custom threshold values."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4, 0.9, 0.1])
        
        # Define custom thresholds to evaluate
        custom_thresholds = np.array([0.3, 0.5, 0.7])
        
        with patch('matplotlib.pyplot.savefig'):
            optimal_threshold, metrics = optimize_threshold(
                y_true, y_score, metric='f1', thresholds=custom_thresholds
            )
        
        # Optimal threshold should be one of the custom thresholds
        assert optimal_threshold in custom_thresholds
    
    def test_multiclass_threshold_optimization(self):
        """Test threshold optimization for multi-class classification."""
        # Multi-class data
        y_true = np.array([0, 1, 2, 0, 1, 2, 0, 1, 2])
        y_score = np.array([
            [0.8, 0.1, 0.1],  # Class 0
            [0.1, 0.8, 0.1],  # Class 1
            [0.1, 0.1, 0.8],  # Class 2
            [0.7, 0.2, 0.1],  # Class 0
            [0.2, 0.7, 0.1],  # Class 1
            [0.1, 0.2, 0.7],  # Class 2
            [0.6, 0.3, 0.1],  # Class 0
            [0.3, 0.6, 0.1],  # Class 1
            [0.1, 0.3, 0.6]   # Class 2
        ])
        
        with patch('matplotlib.pyplot.savefig'):
            # Optimize threshold for class 1
            optimal_threshold, metrics = optimize_threshold(
                y_true, y_score, metric='f1', class_index=1
            )
        
        # Check that optimal threshold is between 0 and 1
        assert 0.0 <= optimal_threshold <= 1.0
        
        # Apply the threshold to get predictions for class 1
        y_pred_class1 = (y_score[:, 1] >= optimal_threshold).astype(int)
        
        # Convert to binary problem for class 1
        y_true_class1 = (y_true == 1).astype(int)
        
        # Calculate F1 score manually
        f1 = f1_score(y_true_class1, y_pred_class1)
        
        # F1 score should match the one reported in metrics
        assert np.isclose(f1, metrics['f1'])
    
    def test_save_threshold_curve(self, tmp_path):
        """Test saving threshold optimization curve to file."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4])
        save_path = str(tmp_path / "threshold_curve.png")
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            optimize_threshold(y_true, y_score, save_path=save_path)
            
        # Check that savefig was called with the correct path
        mock_savefig.assert_called_once_with(save_path)


# Test calibrate_confidence_scores function
class TestCalibrateConfidenceScores:
    def test_calibration_with_sigmoid_method(self):
        """Test calibration with sigmoid method (Platt scaling)."""
        # Create a simple dataset
        X_train = np.random.random((100, 5))
        y_train = np.random.choice([0, 1], size=100)
        X_test = np.random.random((20, 5))
        
        # Create a base classifier
        base_model = SVC(kernel='linear', probability=False, random_state=42)
        base_model.fit(X_train, y_train)
        
        # Calibrate the model
        calibrated_model = calibrate_confidence_scores(
            base_model, X_train, y_train, method='sigmoid', cv=3
        )
        
        # Check that the calibrated model is a CalibratedClassifierCV instance
        assert isinstance(calibrated_model, CalibratedClassifierCV)
        
        # Check that the calibrated model can predict probabilities
        proba = calibrated_model.predict_proba(X_test)
        assert proba.shape == (20, 2)  # Binary classification
        
        # Check that probabilities sum to 1 for each sample
        assert np.allclose(np.sum(proba, axis=1), 1.0)
    
    def test_calibration_with_isotonic_method(self):
        """Test calibration with isotonic regression method."""
        # Create a simple dataset
        X_train = np.random.random((100, 5))
        y_train = np.random.choice([0, 1, 2], size=100)  # Multi-class
        X_test = np.random.random((20, 5))
        
        # Create a base classifier
        base_model = RandomForestClassifier(n_estimators=10, random_state=42)
        base_model.fit(X_train, y_train)
        
        # Calibrate the model
        calibrated_model = calibrate_confidence_scores(
            base_model, X_train, y_train, method='isotonic', cv=3
        )
        
        # Check that the calibrated model is a CalibratedClassifierCV instance
        assert isinstance(calibrated_model, CalibratedClassifierCV)
        
        # Check that the calibrated model can predict probabilities
        proba = calibrated_model.predict_proba(X_test)
        assert proba.shape == (20, 3)  # 3 classes
        
        # Check that probabilities sum to 1 for each sample
        assert np.allclose(np.sum(proba, axis=1), 1.0)
    
    def test_calibration_improves_probability_estimates(self):
        """Test that calibration improves probability estimates."""
        # Create a dataset with a clear decision boundary
        np.random.seed(42)
        X_train = np.vstack([
            np.random.randn(50, 2) - np.array([2, 2]),  # Class 0
            np.random.randn(50, 2) + np.array([2, 2])   # Class 1
        ])
        y_train = np.hstack([np.zeros(50), np.ones(50)])
        
        # Create a test set
        X_test = np.vstack([
            np.random.randn(20, 2) - np.array([2, 2]),  # Class 0
            np.random.randn(20, 2) + np.array([2, 2])   # Class 1
        ])
        y_test = np.hstack([np.zeros(20), np.ones(20)])
        
        # Create a base classifier (SVM with linear kernel)
        base_model = SVC(kernel='linear', probability=True, random_state=42)
        base_model.fit(X_train, y_train)
        
        # Get uncalibrated probabilities
        uncalibrated_proba = base_model.predict_proba(X_test)
        
        # Calibrate the model
        calibrated_model = calibrate_confidence_scores(
            base_model, X_train, y_train, method='sigmoid', cv=3
        )
        
        # Get calibrated probabilities
        calibrated_proba = calibrated_model.predict_proba(X_test)
        
        # Both should give the same predictions
        uncalibrated_pred = np.argmax(uncalibrated_proba, axis=1)
        calibrated_pred = np.argmax(calibrated_proba, axis=1)
        assert np.array_equal(uncalibrated_pred, calibrated_pred)
        
        # But calibrated probabilities should be different
        assert not np.allclose(uncalibrated_proba, calibrated_proba)


# Test compare_models function
class TestCompareModels:
    def test_compare_binary_classifiers(self):
        """Test comparison of binary classifiers."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create two different models
        svm = SVC(probability=True, random_state=42)
        rf = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Train the models
        svm.fit(X_train, y_train)
        rf.fit(X_train, y_train)
        
        # Compare models
        with patch('matplotlib.pyplot.savefig'):
            results = compare_models(
                {'SVM': svm, 'Random Forest': rf},
                X_test, y_test
            )
        
        # Check that results contain both models
        assert 'SVM' in results
        assert 'Random Forest' in results
        
        # Check that each model has metrics and ROC data
        for model_name in ['SVM', 'Random Forest']:
            assert 'metrics' in results[model_name]
            assert 'roc' in results[model_name]
            
            # Check that metrics contain expected keys
            assert 'accuracy' in results[model_name]['metrics']
            assert 'precision' in results[model_name]['metrics']
            assert 'recall' in results[model_name]['metrics']
            assert 'f1' in results[model_name]['metrics']
            
            # Check that ROC data contains expected keys
            assert 'fpr' in results[model_name]['roc']
            assert 'tpr' in results[model_name]['roc']
            assert 'auc' in results[model_name]['roc']
    
    def test_save_comparison_plot(self, tmp_path):
        """Test saving model comparison plot to file."""
        # Create a simple dataset
        X = np.random.random((50, 3))
        y = np.random.choice([0, 1], size=50)
        
        # Create two different models
        svm = SVC(probability=True, random_state=42)
        rf = RandomForestClassifier(n_estimators=5, random_state=42)
        
        # Train the models
        svm.fit(X, y)
        rf.fit(X, y)
        
        # Compare models and save plot
        save_path = str(tmp_path / "model_comparison.png")
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            compare_models(
                {'SVM': svm, 'Random Forest': rf},
                X, y, save_path=save_path
            )
            
        # Check that savefig was called with the correct path
        mock_savefig.assert_called_once_with(save_path)
    
    def test_compare_multiclass_classifiers(self):
        """Test comparison of multi-class classifiers."""
        # Create a multi-class dataset
        X = np.random.random((90, 5))
        y = np.random.choice([0, 1, 2], size=90)
        X_train, X_test = X[:60], X[60:]
        y_train, y_test = y[:60], y[60:]
        
        # Create two different models
        svm = SVC(probability=True, random_state=42)
        rf = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Train the models
        svm.fit(X_train, y_train)
        rf.fit(X_train, y_train)
        
        # Compare models
        with patch('matplotlib.pyplot.savefig'):
            results = compare_models(
                {'SVM': svm, 'Random Forest': rf},
                X_test, y_test, class_names=['Class 0', 'Class 1', 'Class 2']
            )
        
        # Check that results contain both models
        assert 'SVM' in results
        assert 'Random Forest' in results
        
        # Check that each model has metrics
        for model_name in ['SVM', 'Random Forest']:
            assert 'metrics' in results[model_name]
            
            # Check that metrics contain expected keys
            assert 'accuracy' in results[model_name]['metrics']
            assert 'precision' in results[model_name]['metrics']
            assert 'recall' in results[model_name]['metrics']
            assert 'f1' in results[model_name]['metrics']


# Test evaluate_model_performance function
class TestEvaluateModelPerformance:
    def test_comprehensive_evaluation_binary(self):
        """Test comprehensive evaluation of a binary classifier."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate model performance
        with patch('matplotlib.pyplot.savefig'):
            results = evaluate_model_performance(model, X_test, y_test)
        
        # Check that results contain expected sections
        assert 'metrics' in results
        assert 'classification_report' in results
        assert 'confusion_matrix' in results
        assert 'roc' in results
        assert 'precision_recall' in results
        assert 'threshold_optimization' in results
        
        # Check that metrics contain expected keys
        assert 'accuracy' in results['metrics']
        assert 'precision' in results['metrics']
        assert 'recall' in results['metrics']
        assert 'f1' in results['metrics']
        
        # Check that ROC data contains expected keys
        assert 'fpr' in results['roc']
        assert 'tpr' in results['roc']
        assert 'thresholds' in results['roc']
        assert 'auc' in results['roc']
        
        # Check that threshold optimization contains expected keys
        assert 'optimal_threshold' in results['threshold_optimization']
        assert 'metrics' in results['threshold_optimization']
    
    def test_evaluation_with_custom_threshold(self):
        """Test evaluation with a custom classification threshold."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate model performance with custom threshold
        with patch('matplotlib.pyplot.savefig'):
            results = evaluate_model_performance(model, X_test, y_test, threshold=0.7)
        
        # Check that results contain expected sections
        assert 'metrics' in results
        
        # Get predictions with default threshold (0.5)
        y_pred_default = model.predict(X_test)
        
        # Get predictions with custom threshold (0.7)
        y_prob = model.predict_proba(X_test)
        y_pred_custom = (y_prob[:, 1] >= 0.7).astype(int)
        
        # Predictions should be different
        assert not np.array_equal(y_pred_default, y_pred_custom)
    
    def test_evaluation_with_bootstrap_ci(self):
        """Test evaluation with bootstrap confidence intervals."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate model performance with bootstrap confidence intervals
        with patch('matplotlib.pyplot.savefig'):
            results = evaluate_model_performance(
                model, X_test, y_test, bootstrap_ci=True
            )
        
        # Check that results contain bootstrap confidence intervals
        assert 'bootstrap_ci' in results
        
        # Check that bootstrap CI contains expected metrics
        assert 'accuracy' in results['bootstrap_ci']
        assert 'precision' in results['bootstrap_ci']
        assert 'recall' in results['bootstrap_ci']
        assert 'f1' in results['bootstrap_ci']
        
        # Check that each metric has expected keys
        for metric in ['accuracy', 'precision', 'recall', 'f1']:
            assert 'base_metric' in results['bootstrap_ci'][metric]
            assert 'lower_bound' in results['bootstrap_ci'][metric]
            assert 'upper_bound' in results['bootstrap_ci'][metric]
            
            # Check that bounds are valid
            assert results['bootstrap_ci'][metric]['lower_bound'] <= results['bootstrap_ci'][metric]['base_metric']
            assert results['bootstrap_ci'][metric]['upper_bound'] >= results['bootstrap_ci'][metric]['base_metric']
    
    def test_evaluation_with_output_dir(self, tmp_path):
        """Test evaluation with output directory for artifacts."""
        # Create a simple dataset
        X = np.random.random((50, 3))
        y = np.random.choice([0, 1], size=50)
        X_train, X_test = X[:40], X[40:]
        y_train, y_test = y[:40], y[40:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        model.fit(X_train, y_train)
        
        # Evaluate model performance with output directory
        output_dir = str(tmp_path)
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            evaluate_model_performance(model, X_test, y_test, output_dir=output_dir)
            
        # Check that savefig was called multiple times for different artifacts
        assert mock_savefig.call_count >= 3


# Test generate_precision_recall_curve function
class TestGeneratePrecisionRecallCurve:
    def test_precision_recall_curve_binary(self):
        """Test precision-recall curve generation for binary classification."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4, 0.9, 0.1])
        
        with patch('matplotlib.pyplot.savefig'):
            precision, recall, thresholds, avg_precision = generate_precision_recall_curve(y_true, y_score)
        
        # Check that precision and recall have the same length
        assert len(precision) == len(recall)
        
        # Check that average precision is between 0 and 1
        assert 0.0 <= avg_precision <= 1.0
        
        # For this example, average precision should be high (good classifier)
        assert avg_precision > 0.7
    
    def test_save_precision_recall_curve(self, tmp_path):
        """Test saving precision-recall curve to file."""
        y_true = np.array([0, 1, 0, 1, 1, 0, 1, 0])
        y_score = np.array([0.1, 0.9, 0.2, 0.8, 0.7, 0.3, 0.6, 0.4])
        save_path = str(tmp_path / "precision_recall_curve.png")
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            generate_precision_recall_curve(y_true, y_score, save_path=save_path)
            
        # Check that savefig was called with the correct path
        mock_savefig.assert_called_once_with(save_path)
    
    def test_multiclass_precision_recall(self):
        """Test precision-recall curve for multi-class classification."""
        # Multi-class data
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_score = np.array([
            [0.8, 0.1, 0.1],  # Class 0
            [0.1, 0.8, 0.1],  # Class 1
            [0.1, 0.1, 0.8],  # Class 2
            [0.7, 0.2, 0.1],  # Class 0
            [0.2, 0.7, 0.1],  # Class 1
            [0.1, 0.2, 0.7]   # Class 2
        ])
        
        with patch('matplotlib.pyplot.savefig'):
            # Test precision-recall for class 1
            precision, recall, thresholds, avg_precision = generate_precision_recall_curve(
                y_true, y_score, class_index=1
            )
        
        # Check that average precision is between 0 and 1
        assert 0.0 <= avg_precision <= 1.0
        
        # For this example, average precision should be high (good classifier)
        assert avg_precision > 0.8


# Test plot_learning_curve function
class TestPlotLearningCurve:
    def test_learning_curve_generation(self):
        """Test learning curve generation."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        
        # Create a simple model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Generate learning curve
        with patch('matplotlib.pyplot.savefig'):
            results = plot_learning_curve(model, X, y, cv=3, train_sizes=np.linspace(0.2, 1.0, 3))
        
        # Check that results contain expected keys
        assert 'train_sizes' in results
        assert 'train_scores' in results
        assert 'test_scores' in results
        assert 'train_mean' in results
        assert 'train_std' in results
        assert 'test_mean' in results
        assert 'test_std' in results
        
        # Check that train_sizes has the expected length
        assert len(results['train_sizes']) == 3
        
        # Check that scores have the expected shape
        assert results['train_scores'].shape == (3, 3)  # 3 train sizes, 3 CV folds
        assert results['test_scores'].shape == (3, 3)   # 3 train sizes, 3 CV folds
        
        # Check that means and stds have the expected length
        assert len(results['train_mean']) == 3
        assert len(results['train_std']) == 3
        assert len(results['test_mean']) == 3
        assert len(results['test_std']) == 3
    
    def test_save_learning_curve(self, tmp_path):
        """Test saving learning curve to file."""
        # Create a simple dataset
        X = np.random.random((50, 3))
        y = np.random.choice([0, 1], size=50)
        
        # Create a simple model
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        
        # Generate learning curve and save plot
        save_path = str(tmp_path / "learning_curve.png")
        
        with patch('matplotlib.pyplot.savefig') as mock_savefig:
            plot_learning_curve(model, X, y, cv=2, save_path=save_path)
            
        # Check that savefig was called with the correct path
        mock_savefig.assert_called_once_with(save_path)
    
    def test_learning_curve_with_different_scoring(self):
        """Test learning curve with different scoring metrics."""
        # Create a simple dataset
        X = np.random.random((60, 4))
        y = np.random.choice([0, 1, 2], size=60)  # Multi-class
        
        # Create a simple model
        model = RandomForestClassifier(n_estimators=5, random_state=42)
        
        # Generate learning curves with different scoring metrics
        with patch('matplotlib.pyplot.savefig'):
            results_accuracy = plot_learning_curve(model, X, y, cv=2, scoring='accuracy')
            results_f1 = plot_learning_curve(model, X, y, cv=2, scoring='f1_weighted')
        
        # Both should have the same structure but different values
        assert set(results_accuracy.keys()) == set(results_f1.keys())
        
        # Values should be different
        assert not np.array_equal(results_accuracy['test_mean'], results_f1['test_mean'])


# Test bootstrap_confidence_interval function
class TestBootstrapConfidenceInterval:
    def test_bootstrap_accuracy(self):
        """Test bootstrap confidence interval for accuracy."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Calculate bootstrap confidence interval for accuracy
        results = bootstrap_confidence_interval(
            model, X_test, y_test, accuracy_score, n_iterations=100, random_state=42
        )
        
        # Check that results contain expected keys
        assert 'base_metric' in results
        assert 'lower_bound' in results
        assert 'upper_bound' in results
        assert 'confidence_level' in results
        assert 'n_iterations' in results
        assert 'bootstrap_samples' in results
        
        # Check that bounds are valid
        assert results['lower_bound'] <= results['base_metric'] <= results['upper_bound']
        
        # Check that bootstrap samples have the expected length
        assert len(results['bootstrap_samples']) == 100
    
    def test_bootstrap_with_custom_metric(self):
        """Test bootstrap confidence interval with a custom metric function."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Define a custom metric function (F1 score for class 1)
        def custom_f1(y_true, y_pred):
            return f1_score(y_true, y_pred, pos_label=1)
        
        # Calculate bootstrap confidence interval with custom metric
        results = bootstrap_confidence_interval(
            model, X_test, y_test, custom_f1, n_iterations=50, random_state=42
        )
        
        # Check that results contain expected keys
        assert 'base_metric' in results
        assert 'lower_bound' in results
        assert 'upper_bound' in results
        
        # Check that bounds are valid
        assert results['lower_bound'] <= results['base_metric'] <= results['upper_bound']
    
    def test_bootstrap_with_different_confidence_levels(self):
        """Test bootstrap confidence interval with different confidence levels."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create and train a model
        model = RandomForestClassifier(n_estimators=10, random_state=42)
        model.fit(X_train, y_train)
        
        # Calculate bootstrap confidence intervals with different confidence levels
        results_90 = bootstrap_confidence_interval(
            model, X_test, y_test, accuracy_score, confidence_level=0.9, random_state=42
        )
        
        results_99 = bootstrap_confidence_interval(
            model, X_test, y_test, accuracy_score, confidence_level=0.99, random_state=42
        )
        
        # 99% CI should be wider than 90% CI
        ci_width_90 = results_90['upper_bound'] - results_90['lower_bound']
        ci_width_99 = results_99['upper_bound'] - results_99['lower_bound']
        assert ci_width_99 > ci_width_90


# Test utility functions (sigmoid, softmax)
class TestUtilityFunctions:
    def test_sigmoid(self):
        """Test sigmoid function."""
        # Test with various inputs
        assert sigmoid(0) == 0.5  # Sigmoid of 0 should be 0.5
        assert sigmoid(100) > 0.999  # Sigmoid of large positive number should be close to 1
        assert sigmoid(-100) < 0.001  # Sigmoid of large negative number should be close to 0
        
        # Test with array input
        x = np.array([-10, -1, 0, 1, 10])
        y = sigmoid(x)
        
        # Check that output has the same shape as input
        assert y.shape == x.shape
        
        # Check that all values are between 0 and 1
        assert np.all((y >= 0) & (y <= 1))
    
    def test_softmax(self):
        """Test softmax function."""
        # Test with a single vector
        x = np.array([1, 2, 3, 4])
        y = softmax(x)
        
        # Check that output has the same shape as input
        assert y.shape == x.shape
        
        # Check that values sum to 1
        assert np.isclose(np.sum(y), 1.0)
        
        # Check that all values are between 0 and 1
        assert np.all((y >= 0) & (y <= 1))
        
        # Test with a batch of vectors
        x_batch = np.array([
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ])
        y_batch = softmax(x_batch, axis=1)
        
        # Check that output has the same shape as input
        assert y_batch.shape == x_batch.shape
        
        # Check that each row sums to 1
        assert np.allclose(np.sum(y_batch, axis=1), np.ones(3))
        
        # Check that all values are between 0 and 1
        assert np.all((y_batch >= 0) & (y_batch <= 1))


# Test ThresholdClassifier class
class TestThresholdClassifier:
    def test_initialization(self):
        """Test initialization of ThresholdClassifier."""
        # Create a base classifier
        base_model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Create a threshold classifier with default threshold
        threshold_clf = ThresholdClassifier(base_model)
        
        # Check that the base classifier is stored correctly
        assert threshold_clf.classifier == base_model
        
        # Check that the default threshold is 0.5
        assert threshold_clf.threshold == 0.5
        
        # Create a threshold classifier with custom threshold
        threshold_clf_custom = ThresholdClassifier(base_model, threshold=0.7)
        assert threshold_clf_custom.threshold == 0.7
    
    def test_fit_and_predict(self):
        """Test fit and predict methods of ThresholdClassifier."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create a base classifier
        base_model = RandomForestClassifier(n_estimators=10, random_state=42)
        
        # Create a threshold classifier with custom threshold
        threshold_clf = ThresholdClassifier(base_model, threshold=0.7)
        
        # Fit the classifier
        threshold_clf.fit(X_train, y_train)
        
        # Check that the base classifier was fitted
        assert hasattr(base_model, 'classes_')
        
        # Predict with the threshold classifier
        y_pred = threshold_clf.predict(X_test)
        
        # Check that predictions are binary
        assert set(np.unique(y_pred)).issubset({0, 1})
        
        # Get probabilities
        y_prob = threshold_clf.predict_proba(X_test)
        
        # Check that probabilities have the correct shape
        assert y_prob.shape == (len(X_test), 2)  # Binary classification
        
        # Check that probabilities sum to 1 for each sample
        assert np.allclose(np.sum(y_prob, axis=1), np.ones(len(X_test)))
    
    def test_custom_threshold_effect(self):
        """Test that custom threshold affects predictions."""
        # Create a simple dataset
        X = np.random.random((100, 5))
        y = np.random.choice([0, 1], size=100)
        X_train, X_test = X[:80], X[80:]
        y_train, y_test = y[:80], y[80:]
        
        # Create a base classifier
        base_model = RandomForestClassifier(n_estimators=10, random_state=42)
        base_model.fit(X_train, y_train)
        
        # Create threshold classifiers with different thresholds
        threshold_clf_low = ThresholdClassifier(base_model, threshold=0.3)
        threshold_clf_high = ThresholdClassifier(base_model, threshold=0.7)
        
        # Predict with both classifiers
        y_pred_low = threshold_clf_low.predict(X_test)
        y_pred_high = threshold_clf_high.predict(X_test)
        
        # Higher threshold should result in fewer positive predictions
        assert np.sum(y_pred_low) >= np.sum(y_pred_high)
    
    def test_get_confidence_scores(self):
        """Test get_confidence_scores method."""
        # Create a simple dataset
        X = np.random.random((50, 5))
        y = np.random.choice([0, 1], size=50)
        X_train, X_test = X[:40], X[40:]
        y_train, y_test = y[:40], y[40:]
        
        # Create and train a base classifier
        base_model = RandomForestClassifier(n_estimators=5, random_state=42)
        base_model.fit(X_train, y_train)
        
        # Create a threshold classifier
        threshold_clf = ThresholdClassifier(base_model, threshold=0.6)
        
        # Get confidence scores
        confidence_scores = threshold_clf.get_confidence_scores(X_test)
        
        # Check that we get one score per sample
        assert len(confidence_scores) == len(X_test)
        
        # Check that each score has the expected keys
        for score in confidence_scores:
            assert 'prediction' in score
            assert 'confidence' in score
            assert 'meets_threshold' in score
            
            # Check that prediction is binary
            assert score['prediction'] in [0, 1]
            
            # Check that confidence is between 0 and 1
            assert 0.0 <= score['confidence'] <= 1.0
            
            # Check that meets_threshold is consistent with confidence and threshold
            if score['confidence'] >= threshold_clf.threshold:
                assert score['meets_threshold'] is True
            else:
                assert score['meets_threshold'] is False