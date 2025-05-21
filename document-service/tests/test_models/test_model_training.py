"""Unit tests for model training utilities.

This module contains tests for the model training utilities used to train and fine-tune
document classification models in the Document Service.
"""

import os
import pickle
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.svm import SVC

from ...src.models.model_training import (
    calculate_metrics,
    create_cross_validator,
    evaluate_cross_validation,
    load_model_checkpoint,
    optimize_hyperparameters_grid,
    optimize_hyperparameters_random,
    prepare_dataset,
    save_model_checkpoint,
    train_model_from_config,
    train_model_with_early_stopping,
    train_random_forest_classifier,
    train_svm_classifier,
)
from ...src.types.classification import ClassificationMetrics, ModelConfig, FeatureExtractor


class TestPrepareDataset:
    """Tests for the prepare_dataset function."""

    def test_prepare_dataset_default(self, document_features):
        """Test prepare_dataset with default parameters."""
        X, y = document_features
        X_train, X_test, y_train, y_test = prepare_dataset(X, y)

        # Check shapes
        assert X_train.shape[0] == int(X.shape[0] * 0.8)  # 80% for training
        assert X_test.shape[0] == int(X.shape[0] * 0.2)   # 20% for testing
        assert len(y_train) == X_train.shape[0]
        assert len(y_test) == X_test.shape[0]

        # Check that all classes are represented in both sets (stratification)
        assert set(y_train) == set(y_test) == set(y)

    def test_prepare_dataset_custom_split(self, document_features):
        """Test prepare_dataset with custom test_size."""
        X, y = document_features
        test_size = 0.3
        X_train, X_test, y_train, y_test = prepare_dataset(X, y, test_size=test_size)

        # Check shapes with custom split
        assert X_train.shape[0] == int(X.shape[0] * (1 - test_size))
        assert X_test.shape[0] == int(X.shape[0] * test_size)

    def test_prepare_dataset_no_stratify(self, document_features):
        """Test prepare_dataset without stratification."""
        X, y = document_features
        X_train, X_test, y_train, y_test = prepare_dataset(X, y, stratify=False)

        # Basic shape checks
        assert X_train.shape[0] + X_test.shape[0] == X.shape[0]
        
        # Note: Without stratification, we can't guarantee all classes are in both sets,
        # especially with small test datasets, so we don't test for that

    def test_prepare_dataset_reproducibility(self, document_features):
        """Test that prepare_dataset is reproducible with the same random_state."""
        X, y = document_features
        random_state = 42

        # Generate two splits with the same random_state
        X_train1, X_test1, y_train1, y_test1 = prepare_dataset(X, y, random_state=random_state)
        X_train2, X_test2, y_train2, y_test2 = prepare_dataset(X, y, random_state=random_state)

        # Check that the splits are identical
        np.testing.assert_array_equal(X_train1, X_train2)
        np.testing.assert_array_equal(X_test1, X_test2)
        np.testing.assert_array_equal(y_train1, y_train2)
        np.testing.assert_array_equal(y_test1, y_test2)

        # Generate a split with a different random_state
        X_train3, X_test3, y_train3, y_test3 = prepare_dataset(X, y, random_state=24)

        # Check that the splits are different
        with pytest.raises(AssertionError):
            np.testing.assert_array_equal(X_train1, X_train3)


class TestCreateCrossValidator:
    """Tests for the create_cross_validator function."""

    def test_create_stratified_cross_validator(self):
        """Test creating a stratified cross-validator."""
        cv = create_cross_validator(stratify=True)
        assert isinstance(cv, StratifiedKFold)
        assert cv.n_splits == 5  # Default
        assert cv.shuffle is True  # Default

    def test_create_standard_cross_validator(self):
        """Test creating a standard (non-stratified) cross-validator."""
        cv = create_cross_validator(stratify=False)
        assert isinstance(cv, KFold)
        assert cv.n_splits == 5  # Default
        assert cv.shuffle is True  # Default

    def test_create_cross_validator_custom_splits(self):
        """Test creating a cross-validator with custom number of splits."""
        n_splits = 10
        cv = create_cross_validator(n_splits=n_splits)
        assert cv.n_splits == n_splits

    def test_create_cross_validator_no_shuffle(self):
        """Test creating a cross-validator without shuffling."""
        cv = create_cross_validator(shuffle=False)
        assert cv.shuffle is False

    def test_create_cross_validator_reproducibility(self):
        """Test that cross-validators with the same random_state produce the same splits."""
        random_state = 42
        cv1 = create_cross_validator(random_state=random_state)
        cv2 = create_cross_validator(random_state=random_state)

        # Create some dummy data
        X = np.random.rand(100, 10)
        y = np.random.randint(0, 5, 100)

        # Get the splits from both cross-validators
        splits1 = list(cv1.split(X, y))
        splits2 = list(cv2.split(X, y))

        # Check that the splits are identical
        for (train1, test1), (train2, test2) in zip(splits1, splits2):
            np.testing.assert_array_equal(train1, train2)
            np.testing.assert_array_equal(test1, test2)


class TestEvaluateCrossValidation:
    """Tests for the evaluate_cross_validation function."""

    def test_evaluate_cross_validation_default(self, document_features, trained_svm_classifier):
        """Test cross-validation evaluation with default parameters."""
        X, y = document_features
        scores = evaluate_cross_validation(trained_svm_classifier, X, y)

        # Check that the expected score keys are present
        expected_keys = [
            'fit_time', 'score_time',
            'test_accuracy', 'train_accuracy',
            'test_precision_macro', 'train_precision_macro',
            'test_recall_macro', 'train_recall_macro',
            'test_f1_macro', 'train_f1_macro'
        ]
        for key in expected_keys:
            assert key in scores

        # Check that scores are arrays with the expected length (default 5-fold CV)
        assert len(scores['test_accuracy']) == 5

        # Check that scores are in the valid range [0, 1]
        assert all(0 <= score <= 1 for score in scores['test_accuracy'])
        assert all(0 <= score <= 1 for score in scores['test_precision_macro'])

    def test_evaluate_cross_validation_custom_cv(self, document_features, trained_svm_classifier):
        """Test cross-validation evaluation with custom CV strategy."""
        X, y = document_features
        cv = create_cross_validator(n_splits=3, stratify=True)
        scores = evaluate_cross_validation(trained_svm_classifier, X, y, cv=cv)

        # Check that scores are arrays with the expected length (3-fold CV)
        assert len(scores['test_accuracy']) == 3

    def test_evaluate_cross_validation_custom_scoring(self, document_features, trained_svm_classifier):
        """Test cross-validation evaluation with custom scoring metrics."""
        X, y = document_features
        scoring = ['accuracy', 'precision_micro', 'recall_micro']
        scores = evaluate_cross_validation(trained_svm_classifier, X, y, scoring=scoring)

        # Check that the expected score keys are present
        expected_keys = [
            'test_accuracy', 'train_accuracy',
            'test_precision_micro', 'train_precision_micro',
            'test_recall_micro', 'train_recall_micro'
        ]
        for key in expected_keys:
            assert key in scores

        # Check that unexpected keys are not present
        assert 'test_f1_macro' not in scores


class TestOptimizeHyperparameters:
    """Tests for the hyperparameter optimization functions."""

    def test_optimize_hyperparameters_grid(self, document_features):
        """Test grid search hyperparameter optimization."""
        X, y = document_features
        X_train, _, y_train, _ = prepare_dataset(X, y, test_size=0.2)

        # Create a simple SVM model
        model = SVC(probability=True)

        # Define a simple parameter grid
        param_grid = {
            'C': [0.1, 1.0],
            'kernel': ['linear', 'rbf']
        }

        # Optimize hyperparameters
        best_model, best_params = optimize_hyperparameters_grid(
            model, param_grid, X_train, y_train, cv=2, n_jobs=1, verbose=0
        )

        # Check that the best model is an SVC
        assert isinstance(best_model, SVC)

        # Check that the best parameters are a subset of the parameter grid
        assert best_params['C'] in param_grid['C']
        assert best_params['kernel'] in param_grid['kernel']

    def test_optimize_hyperparameters_random(self, document_features):
        """Test randomized search hyperparameter optimization."""
        X, y = document_features
        X_train, _, y_train, _ = prepare_dataset(X, y, test_size=0.2)

        # Create a simple Random Forest model
        model = RandomForestClassifier()

        # Define parameter distributions
        param_distributions = {
            'n_estimators': [50, 100],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5]
        }

        # Optimize hyperparameters
        best_model, best_params = optimize_hyperparameters_random(
            model, param_distributions, X_train, y_train, n_iter=4, cv=2, n_jobs=1, verbose=0
        )

        # Check that the best model is a RandomForestClassifier
        assert isinstance(best_model, RandomForestClassifier)

        # Check that the best parameters are a subset of the parameter distributions
        assert best_params['n_estimators'] in param_distributions['n_estimators']
        assert best_params['max_depth'] in param_distributions['max_depth']
        assert best_params['min_samples_split'] in param_distributions['min_samples_split']

    def test_optimize_hyperparameters_reproducibility(self, document_features):
        """Test that hyperparameter optimization is reproducible with the same random_state."""
        X, y = document_features
        X_train, _, y_train, _ = prepare_dataset(X, y, test_size=0.2)

        # Create two identical Random Forest models
        model1 = RandomForestClassifier(random_state=42)
        model2 = RandomForestClassifier(random_state=42)

        # Define parameter distributions
        param_distributions = {
            'n_estimators': [50, 100],
            'max_depth': [None, 10, 20],
            'min_samples_split': [2, 5]
        }

        # Optimize hyperparameters with the same random_state
        random_state = 42
        _, best_params1 = optimize_hyperparameters_random(
            model1, param_distributions, X_train, y_train, n_iter=4, cv=2, 
            n_jobs=1, verbose=0, random_state=random_state
        )
        _, best_params2 = optimize_hyperparameters_random(
            model2, param_distributions, X_train, y_train, n_iter=4, cv=2, 
            n_jobs=1, verbose=0, random_state=random_state
        )

        # Check that the best parameters are identical
        assert best_params1 == best_params2


class TestCalculateMetrics:
    """Tests for the calculate_metrics function."""

    def test_calculate_metrics_basic(self):
        """Test basic metrics calculation."""
        # Create some test data
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 1, 0, 1, 2])

        # Calculate metrics
        metrics = calculate_metrics(y_true, y_pred)

        # Check that the metrics object is correctly created
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1

        # Check that precision, recall, and F1 dictionaries have the expected keys
        for class_idx in ['0', '1', '2']:
            assert class_idx in metrics.precision
            assert class_idx in metrics.recall
            assert class_idx in metrics.f1_score

        # Check that the confusion matrix is created
        assert metrics.confusion_matrix is not None
        assert metrics.confusion_matrix.shape == (3, 3)  # 3 classes

    def test_calculate_metrics_with_labels(self):
        """Test metrics calculation with custom labels."""
        # Create some test data
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 1, 0, 1, 2])
        labels = ['class_a', 'class_b', 'class_c']

        # Calculate metrics with labels
        metrics = calculate_metrics(y_true, y_pred, labels=labels)

        # Check that precision, recall, and F1 dictionaries have the expected keys
        for label in labels:
            assert label in metrics.precision
            assert label in metrics.recall
            assert label in metrics.f1_score

    def test_calculate_metrics_with_probabilities(self):
        """Test metrics calculation with probability scores."""
        # Create some test data
        y_true = np.array([0, 1, 2, 0, 1, 2])
        y_pred = np.array([0, 1, 1, 0, 1, 2])
        y_prob = np.array([
            [0.8, 0.1, 0.1],
            [0.1, 0.8, 0.1],
            [0.2, 0.6, 0.2],
            [0.7, 0.2, 0.1],
            [0.1, 0.7, 0.2],
            [0.1, 0.2, 0.7]
        ])

        # Calculate metrics with probabilities
        metrics = calculate_metrics(y_true, y_pred, y_prob=y_prob)

        # Basic checks (we can't easily verify the ROC AUC values)
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1


class TestTrainClassifiers:
    """Tests for the classifier training functions."""

    def test_train_svm_classifier(self, document_features):
        """Test training an SVM classifier."""
        X, y = document_features

        # Train SVM classifier without optimization
        svm, metrics = train_svm_classifier(X, y, optimize=False)

        # Check that the model and metrics are correctly returned
        assert isinstance(svm, SVC)
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1

    def test_train_svm_classifier_with_config(self, document_features, svm_classifier_config):
        """Test training an SVM classifier with custom configuration."""
        X, y = document_features

        # Train SVM classifier with custom config
        svm, metrics = train_svm_classifier(X, y, config=svm_classifier_config, optimize=False)

        # Check that the model has the expected parameters
        assert svm.kernel == svm_classifier_config['kernel']
        assert svm.C == svm_classifier_config['C']
        assert svm.gamma == svm_classifier_config['gamma']
        assert svm.probability == svm_classifier_config['probability']

    def test_train_random_forest_classifier(self, document_features):
        """Test training a Random Forest classifier."""
        X, y = document_features

        # Train Random Forest classifier without optimization
        rf, metrics = train_random_forest_classifier(X, y, optimize=False)

        # Check that the model and metrics are correctly returned
        assert isinstance(rf, RandomForestClassifier)
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1

    def test_train_random_forest_classifier_with_config(self, document_features, random_forest_classifier_config):
        """Test training a Random Forest classifier with custom configuration."""
        X, y = document_features

        # Train Random Forest classifier with custom config
        rf, metrics = train_random_forest_classifier(
            X, y, config=random_forest_classifier_config, optimize=False
        )

        # Check that the model has the expected parameters
        assert rf.n_estimators == random_forest_classifier_config['n_estimators']
        assert rf.max_depth == random_forest_classifier_config['max_depth']
        assert rf.min_samples_split == random_forest_classifier_config['min_samples_split']
        assert rf.min_samples_leaf == random_forest_classifier_config['min_samples_leaf']

    @patch('sklearn.model_selection.train_test_split')
    def test_train_classifiers_use_prepare_dataset(self, mock_train_test_split, document_features):
        """Test that classifier training functions use prepare_dataset."""
        X, y = document_features
        mock_train_test_split.return_value = (X, X, y, y)  # Mock the split

        # Train classifiers
        train_svm_classifier(X, y, optimize=False)
        train_random_forest_classifier(X, y, optimize=False)

        # Check that train_test_split was called
        assert mock_train_test_split.call_count == 2


class TestEarlyStoppingAndCheckpointing:
    """Tests for early stopping and model checkpointing."""

    def test_train_model_with_early_stopping(self, document_features):
        """Test training a model with early stopping."""
        X, y = document_features

        # Create a model that supports warm_start
        model = RandomForestClassifier(warm_start=True, n_estimators=10)

        # Train with early stopping
        trained_model, metrics = train_model_with_early_stopping(
            model, X, y, max_epochs=5, patience=2
        )

        # Check that the model and metrics are correctly returned
        assert isinstance(trained_model, RandomForestClassifier)
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1

    def test_train_model_with_early_stopping_no_incremental(self, document_features):
        """Test early stopping with a model that doesn't support incremental training."""
        X, y = document_features

        # Create a model that doesn't support incremental training
        model = SVC(probability=True)

        # Train with early stopping
        trained_model, metrics = train_model_with_early_stopping(
            model, X, y, max_epochs=5, patience=2
        )

        # Check that the model and metrics are correctly returned
        assert isinstance(trained_model, SVC)
        assert isinstance(metrics, ClassificationMetrics)

    def test_train_model_with_checkpointing(self, document_features, tmp_path):
        """Test training a model with checkpointing."""
        X, y = document_features

        # Create a model that supports warm_start
        model = RandomForestClassifier(warm_start=True, n_estimators=10)

        # Create a temporary checkpoint directory
        checkpoint_dir = str(tmp_path / "checkpoints")

        # Train with checkpointing
        trained_model, metrics = train_model_with_early_stopping(
            model, X, y, max_epochs=3, patience=2, checkpoint_dir=checkpoint_dir
        )

        # Check that checkpoint files were created
        checkpoint_files = list(Path(checkpoint_dir).glob("*.pkl"))
        assert len(checkpoint_files) > 0

    def test_save_and_load_model_checkpoint(self, trained_random_forest_classifier, tmp_path):
        """Test saving and loading a model checkpoint."""
        model = trained_random_forest_classifier

        # Create metrics
        metrics = ClassificationMetrics(
            accuracy=0.95,
            precision={'0': 0.94, '1': 0.96},
            recall={'0': 0.93, '1': 0.97},
            f1_score={'0': 0.935, '1': 0.965}
        )

        # Create a temporary checkpoint directory
        checkpoint_dir = str(tmp_path / "checkpoints")

        # Save model checkpoint
        checkpoint_path = save_model_checkpoint(
            model, metrics, checkpoint_dir, "random_forest", metadata={"version": "1.0.0"}
        )

        # Check that the checkpoint file exists
        assert os.path.exists(checkpoint_path)

        # Load model checkpoint
        loaded_model, metadata = load_model_checkpoint(checkpoint_path)

        # Check that the loaded model is the same type as the original
        assert isinstance(loaded_model, RandomForestClassifier)

        # Check that the metadata was correctly saved and loaded
        assert "version" in metadata
        assert metadata["version"] == "1.0.0"
        assert "accuracy" in metadata
        assert metadata["accuracy"] == 0.95


class TestTrainModelFromConfig:
    """Tests for the train_model_from_config function."""

    def test_train_model_from_config_svm(self, document_features):
        """Test training an SVM model from configuration."""
        X, y = document_features

        # Create a feature extractor
        feature_extractor = FeatureExtractor(
            name="test_extractor",
            extract_fn=lambda x: x,  # Dummy function
            feature_names=["feature1", "feature2"]
        )

        # Create model configuration for SVM
        config = ModelConfig(
            model_type="svm",
            parameters={
                "C": 1.0,
                "kernel": "linear",
                "probability": True
            },
            feature_extractors=[feature_extractor]
        )

        # Train model from config
        model, metrics = train_model_from_config(
            config, X, y, optimize=False, early_stopping=False
        )

        # Check that the model and metrics are correctly returned
        assert isinstance(model, SVC)
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1

    def test_train_model_from_config_random_forest(self, document_features):
        """Test training a Random Forest model from configuration."""
        X, y = document_features

        # Create a feature extractor
        feature_extractor = FeatureExtractor(
            name="test_extractor",
            extract_fn=lambda x: x,  # Dummy function
            feature_names=["feature1", "feature2"]
        )

        # Create model configuration for Random Forest
        config = ModelConfig(
            model_type="random_forest",
            parameters={
                "n_estimators": 100,
                "max_depth": 10
            },
            feature_extractors=[feature_extractor]
        )

        # Train model from config
        model, metrics = train_model_from_config(
            config, X, y, optimize=False, early_stopping=False
        )

        # Check that the model and metrics are correctly returned
        assert isinstance(model, RandomForestClassifier)
        assert isinstance(metrics, ClassificationMetrics)
        assert 0 <= metrics.accuracy <= 1

    def test_train_model_from_config_unsupported_model(self, document_features):
        """Test training with an unsupported model type."""
        X, y = document_features

        # Create a feature extractor
        feature_extractor = FeatureExtractor(
            name="test_extractor",
            extract_fn=lambda x: x,  # Dummy function
            feature_names=["feature1", "feature2"]
        )

        # Create model configuration with unsupported model type
        config = ModelConfig(
            model_type="unsupported_model",
            parameters={},
            feature_extractors=[feature_extractor]
        )

        # Check that training with an unsupported model type raises ValueError
        with pytest.raises(ValueError, match="Unsupported model type"):
            train_model_from_config(config, X, y)

    def test_train_model_from_config_with_checkpoint(self, document_features, tmp_path):
        """Test training a model from configuration with checkpointing."""
        X, y = document_features

        # Create a feature extractor
        feature_extractor = FeatureExtractor(
            name="test_extractor",
            extract_fn=lambda x: x,  # Dummy function
            feature_names=["feature1", "feature2"]
        )

        # Create model configuration for Random Forest
        config = ModelConfig(
            model_type="random_forest",
            parameters={
                "n_estimators": 100,
                "max_depth": 10,
                "warm_start": True  # Enable warm_start for early stopping
            },
            feature_extractors=[feature_extractor]
        )

        # Create a temporary checkpoint directory
        checkpoint_dir = str(tmp_path / "checkpoints")

        # Train model from config with checkpointing
        model, metrics = train_model_from_config(
            config, X, y, optimize=False, early_stopping=True, checkpoint_dir=checkpoint_dir
        )

        # Check that checkpoint files were created
        checkpoint_files = list(Path(checkpoint_dir).glob("*.pkl"))
        assert len(checkpoint_files) > 0