#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for model_training.py

This module contains tests for the model training utilities used to train and fine-tune
document classification models in the Document Service. It tests dataset preparation,
cross-validation, hyperparameter optimization, and model training workflows.

The tests ensure that the training module correctly handles:
1. Dataset preparation (train/test split, stratification)
2. Hyperparameter optimization using grid search and random search
3. Training workflows for different classifier types (SVM, Random Forest)
4. Early stopping and model checkpointing for efficient training
5. Ensemble model training and evaluation
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV

# Import the module to be tested
from src.models.model_training import (
    ModelTrainer, 
    prepare_dataset, 
    optimize_hyperparameters, 
    train_model_with_cv
)

# Import related modules that might be needed for testing
from src.models.base_model import BaseModel
from src.models.svm_classifier import SVMClassifier
from src.models.random_forest_classifier import RandomForestClassifier as RFClassifier
from src.config.model_config import get_model_config


# Fix module imports for testing
@pytest.fixture(autouse=True)
def mock_imports():
    """Mock imports to handle module imports in the test environment."""
    with patch.dict('sys.modules', {
        'src.models.model_training': __import__('src.models.model_training', fromlist=['*']),
        'src.models.base_model': __import__('src.models.base_model', fromlist=['*']),
        'src.models.svm_classifier': __import__('src.models.svm_classifier', fromlist=['*']),
        'src.models.random_forest_classifier': __import__('src.models.random_forest_classifier', fromlist=['*']),
        'src.config.model_config': __import__('src.config.model_config', fromlist=['*']),
    }):
        yield


# Test ModelTrainer initialization
class TestModelTrainerInit:
    """Tests for ModelTrainer initialization."""
    
    def test_init_with_defaults(self):
        """Test ModelTrainer initialization with default parameters."""
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            trainer = ModelTrainer()
            
            assert trainer.target_accuracy == 0.99
            assert hasattr(trainer, 'model_evaluator')
            assert hasattr(trainer, 'output_dir')
    
    def test_init_with_custom_config(self):
        """Test ModelTrainer initialization with custom configuration."""
        custom_config = {
            'target_accuracy': 0.95,
            'base_dir': '/custom/path'
        }
        
        trainer = ModelTrainer(config=custom_config)
        
        assert trainer.target_accuracy == 0.95
        assert trainer.output_dir == '/custom/path/training'
    
    def test_init_with_custom_output_dir(self):
        """Test ModelTrainer initialization with custom output directory."""
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            trainer = ModelTrainer(output_dir='/test/output')
            
            assert trainer.output_dir == '/test/output'


# Test dataset preparation
class TestPrepareDataset:
    """Tests for dataset preparation methods."""
    
    def test_prepare_dataset_method(self, synthetic_classification_data):
        """Test the prepare_dataset method of ModelTrainer."""
        X, y = synthetic_classification_data
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'training': {
                    'train_test_split': {
                        'test_size': 0.2,
                        'random_state': 42,
                        'stratify': True
                    }
                }
            }
            
            trainer = ModelTrainer()
            X_train, X_test, y_train, y_test = trainer.prepare_dataset(X, y)
            
            # Check split sizes
            assert len(X_train) == int(len(X) * 0.8)
            assert len(X_test) == int(len(X) * 0.2)
            assert len(y_train) == len(X_train)
            assert len(y_test) == len(X_test)
            
            # Check that classes are represented in both splits
            assert set(y_train) == set(y_test) == set(y)
    
    def test_prepare_dataset_with_custom_params(self, synthetic_classification_data):
        """Test the prepare_dataset method with custom parameters."""
        X, y = synthetic_classification_data
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            
            trainer = ModelTrainer()
            X_train, X_test, y_train, y_test = trainer.prepare_dataset(
                X, y, test_size=0.3, random_state=123, stratify=False
            )
            
            # Check split sizes
            assert len(X_train) == int(len(X) * 0.7)
            assert len(X_test) == int(len(X) * 0.3)
    
    def test_prepare_dataset_validates_inputs(self):
        """Test that prepare_dataset validates inputs correctly."""
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            
            trainer = ModelTrainer()
            
            # Test with mismatched X and y lengths
            X = np.random.rand(10, 5)
            y = np.array(['a', 'b', 'c'])  # Only 3 labels
            
            with pytest.raises(ValueError, match="X and y must have the same length"):
                trainer.prepare_dataset(X, y)
    
    def test_standalone_prepare_dataset(self, synthetic_classification_data):
        """Test the standalone prepare_dataset function."""
        X, y = synthetic_classification_data
        
        X_train, X_test, y_train, y_test = prepare_dataset(X, y, test_size=0.25, random_state=42)
        
        # Check split sizes
        assert len(X_train) == int(len(X) * 0.75)
        assert len(X_test) == int(len(X) * 0.25)
        assert len(y_train) == len(X_train)
        assert len(y_test) == len(X_test)


# Test hyperparameter optimization
class TestHyperparameterOptimization:
    """Tests for hyperparameter optimization methods."""
    
    def test_optimize_hyperparameters_svm(self, synthetic_classification_data):
        """Test hyperparameter optimization for SVM classifier."""
        X, y = synthetic_classification_data
        
        # Create a small subset for faster testing
        X_subset = X[:20]
        y_subset = y[:20]
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'svm': {
                        'hyperparameter_tuning': {
                            'method': 'grid_search',
                            'cv': 3,
                            'scoring': 'accuracy',
                            'n_jobs': 1,
                            'param_grid': {
                                'C': [0.1, 1.0],
                                'kernel': ['linear', 'rbf'],
                                'gamma': ['scale']
                            }
                        }
                    }
                }
            }
            
            trainer = ModelTrainer()
            
            # Mock GridSearchCV to avoid actual computation
            with patch('sklearn.model_selection.GridSearchCV') as mock_grid_search:
                mock_grid_search.return_value.fit.return_value = None
                mock_grid_search.return_value.best_params_ = {'C': 1.0, 'kernel': 'linear', 'gamma': 'scale'}
                mock_grid_search.return_value.best_score_ = 0.95
                mock_grid_search.return_value.cv_results_ = {'mean_test_score': [0.9, 0.95]}
                
                best_params, best_score = trainer.optimize_hyperparameters('svm', X_subset, y_subset)
                
                # Check that GridSearchCV was called with correct parameters
                mock_grid_search.assert_called_once()
                args, kwargs = mock_grid_search.call_args
                assert isinstance(args[0], SVC)
                assert 'C' in kwargs['param_grid']
                assert kwargs['cv'].n_splits == 3
                assert kwargs['scoring'] == 'accuracy'
                
                # Check results
                assert best_params == {'C': 1.0, 'kernel': 'linear', 'gamma': 'scale'}
                assert best_score == 0.95
    
    def test_optimize_hyperparameters_random_forest(self, synthetic_classification_data):
        """Test hyperparameter optimization for Random Forest classifier."""
        X, y = synthetic_classification_data
        
        # Create a small subset for faster testing
        X_subset = X[:20]
        y_subset = y[:20]
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'random_forest': {
                        'hyperparameter_tuning': {
                            'method': 'random_search',
                            'cv': 3,
                            'scoring': 'f1_weighted',
                            'n_jobs': 1,
                            'n_iter': 5,
                            'param_distributions': {
                                'n_estimators': [50, 100],
                                'max_depth': [None, 10],
                                'min_samples_split': [2, 5]
                            }
                        }
                    }
                }
            }
            
            trainer = ModelTrainer()
            
            # Mock RandomizedSearchCV to avoid actual computation
            with patch('sklearn.model_selection.RandomizedSearchCV') as mock_random_search:
                mock_random_search.return_value.fit.return_value = None
                mock_random_search.return_value.best_params_ = {'n_estimators': 100, 'max_depth': None, 'min_samples_split': 2}
                mock_random_search.return_value.best_score_ = 0.92
                mock_random_search.return_value.cv_results_ = {'mean_test_score': [0.9, 0.92]}
                
                best_params, best_score = trainer.optimize_hyperparameters('random_forest', X_subset, y_subset)
                
                # Check that RandomizedSearchCV was called with correct parameters
                mock_random_search.assert_called_once()
                args, kwargs = mock_random_search.call_args
                assert isinstance(args[0], RandomForestClassifier)
                assert 'n_estimators' in kwargs['param_distributions']
                assert kwargs['cv'].n_splits == 3
                assert kwargs['scoring'] == 'f1_weighted'
                assert kwargs['n_iter'] == 5
                
                # Check results
                assert best_params == {'n_estimators': 100, 'max_depth': None, 'min_samples_split': 2}
                assert best_score == 0.92
    
    def test_optimize_hyperparameters_invalid_model_type(self, synthetic_classification_data):
        """Test that optimize_hyperparameters raises error for invalid model type."""
        X, y = synthetic_classification_data
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            
            trainer = ModelTrainer()
            
            with pytest.raises(ValueError, match="Unsupported model type"):
                trainer.optimize_hyperparameters('invalid_model', X, y)
    
    def test_standalone_optimize_hyperparameters(self, synthetic_classification_data):
        """Test the standalone optimize_hyperparameters function."""
        X, y = synthetic_classification_data
        
        # Create a small subset for faster testing
        X_subset = X[:20]
        y_subset = y[:20]
        
        # Mock GridSearchCV to avoid actual computation
        with patch('sklearn.model_selection.GridSearchCV') as mock_grid_search:
            mock_grid_search.return_value.fit.return_value = None
            mock_grid_search.return_value.best_params_ = {'C': 1.0, 'kernel': 'linear'}
            mock_grid_search.return_value.best_score_ = 0.95
            
            param_grid = {'C': [0.1, 1.0], 'kernel': ['linear', 'rbf']}
            best_params, best_score = optimize_hyperparameters(
                'svm', X_subset, y_subset, param_grid=param_grid, cv=3, method='grid_search'
            )
            
            # Check results
            assert best_params == {'C': 1.0, 'kernel': 'linear'}
            assert best_score == 0.95


# Test model training
class TestModelTraining:
    """Tests for model training methods."""
    
    def test_train_model_svm(self, synthetic_classification_data):
        """Test training an SVM model."""
        X, y = synthetic_classification_data
        
        # Create a small subset for faster testing
        X_subset = X[:20]
        y_subset = y[:20]
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'svm': {
                        'hyperparameters': {
                            'C': 1.0,
                            'kernel': 'linear',
                            'gamma': 'scale'
                        }
                    }
                },
                'training': {
                    'class_balancing': {
                        'method': 'class_weight'
                    }
                }
            }
            
            # Mock SVMClassifier
            with patch('document_service.src.models.svm_classifier.SVMClassifier') as mock_svm_class:
                mock_svm = MagicMock()
                mock_svm.fit.return_value = None
                mock_svm.evaluate.return_value = {'accuracy': 0.95, 'f1': 0.94}
                mock_svm_class.return_value = mock_svm
                
                trainer = ModelTrainer()
                model = trainer.train_model('svm', X_subset, y_subset)
                
                # Check that SVMClassifier was instantiated and methods were called
                mock_svm_class.assert_called_once()
                mock_svm.set_hyperparameters.assert_called_once()
                mock_svm.fit.assert_called_once_with(X_subset, y_subset)
                
                # Check that the model was returned
                assert model == mock_svm
    
    def test_train_model_random_forest(self, synthetic_classification_data):
        """Test training a Random Forest model."""
        X, y = synthetic_classification_data
        
        # Create a small subset for faster testing
        X_subset = X[:20]
        y_subset = y[:20]
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'random_forest': {
                        'hyperparameters': {
                            'n_estimators': 100,
                            'max_depth': None,
                            'min_samples_split': 2
                        }
                    }
                },
                'training': {
                    'class_balancing': {
                        'method': 'none'
                    }
                }
            }
            
            # Mock RandomForestClassifier
            with patch('src.models.random_forest_classifier.RandomForestClassifier') as mock_rf_class:
                mock_rf = MagicMock()
                mock_rf.fit.return_value = None
                mock_rf.evaluate.return_value = {'accuracy': 0.97, 'f1': 0.96}
                mock_rf_class.return_value = mock_rf
                
                trainer = ModelTrainer()
                model = trainer.train_model('random_forest', X_subset, y_subset)
                
                # Check that RandomForestClassifier was instantiated and methods were called
                mock_rf_class.assert_called_once()
                mock_rf.set_hyperparameters.assert_called_once()
                mock_rf.fit.assert_called_once_with(X_subset, y_subset)
                
                # Check that the model was returned
                assert model == mock_rf
    
    def test_train_model_with_validation(self, synthetic_classification_data):
        """Test training a model with validation data."""
        X, y = synthetic_classification_data
        
        # Create train and validation sets
        X_train = X[:60]
        y_train = y[:60]
        X_val = X[60:80]
        y_val = y[60:80]
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'svm': {
                        'hyperparameters': {
                            'C': 1.0,
                            'kernel': 'linear'
                        }
                    }
                }
            }
            
            # Mock SVMClassifier
            with patch('src.models.svm_classifier.SVMClassifier') as mock_svm_class:
                mock_svm = MagicMock()
                mock_svm.fit.return_value = None
                mock_svm.evaluate.return_value = {'accuracy': 0.95, 'f1': 0.94}
                mock_svm_class.return_value = mock_svm
                
                trainer = ModelTrainer()
                model = trainer.train_model('svm', X_train, y_train, X_val, y_val)
                
                # Check that evaluate was called with validation data
                mock_svm.evaluate.assert_called_once_with(X_val, y_val)
    
    def test_train_model_invalid_model_type(self, synthetic_classification_data):
        """Test that train_model raises error for invalid model type."""
        X, y = synthetic_classification_data
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            
            trainer = ModelTrainer()
            
            with pytest.raises(ValueError, match="Unsupported model type"):
                trainer.train_model('invalid_model', X, y)
    
    def test_standalone_train_model_with_cv(self, synthetic_classification_data):
        """Test the standalone train_model_with_cv function."""
        X, y = synthetic_classification_data
        
        # Create a small subset for faster testing
        X_subset = X[:20]
        y_subset = y[:20]
        
        # Mock cross_val_score and SVC
        with patch('sklearn.model_selection.cross_val_score') as mock_cv_score:
            mock_cv_score.return_value = np.array([0.9, 0.95, 0.92, 0.94, 0.93])
            
            with patch('sklearn.svm.SVC') as mock_svc:
                mock_svc.return_value.fit.return_value = None
                
                model, metrics = train_model_with_cv('svm', X_subset, y_subset, cv=5)
                
                # Check that cross_val_score was called
                mock_cv_score.assert_called_once()
                
                # Check that model was trained on all data
                mock_svc.return_value.fit.assert_called_once()
                
                # Check metrics
                assert 'cv_scores' in metrics
                assert 'mean_cv_accuracy' in metrics
                assert metrics['mean_cv_accuracy'] == 0.928  # Mean of the mock scores


# Test early stopping
class TestEarlyStopping:
    """Tests for early stopping functionality."""
    
    def test_train_with_early_stopping(self, synthetic_classification_data):
        """Test training with early stopping for Random Forest."""
        X, y = synthetic_classification_data
        
        # Create train and validation sets
        X_train = X[:60]
        y_train = y[:60]
        X_val = X[60:80]
        y_val = y[60:80]
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'random_forest': {
                        'hyperparameters': {
                            'n_estimators': 100,
                            'max_depth': None
                        }
                    }
                },
                'training': {
                    'early_stopping': {
                        'patience': 3,
                        'min_delta': 0.001
                    }
                }
            }
            
            # Mock RandomForestClassifier
            with patch('src.models.random_forest_classifier.RandomForestClassifier') as mock_rf_class:
                mock_rf = MagicMock()
                mock_rf.fit.return_value = None
                mock_rf.predict.side_effect = lambda X: np.array(['invoice'] * len(X))
                mock_rf.model = MagicMock()
                mock_rf_class.return_value = mock_rf
                
                # Mock accuracy_score to simulate improving then plateauing accuracy
                with patch('sklearn.metrics.accuracy_score') as mock_accuracy:
                    # Simulate accuracy scores that improve then plateau
                    mock_accuracy.side_effect = [0.8, 0.85, 0.89, 0.9, 0.901, 0.902, 0.902, 0.902]
                    
                    trainer = ModelTrainer()
                    model = trainer.train_with_early_stopping(
                        'random_forest', X_train, y_train, X_val, y_val, max_iterations=100, patience=3
                    )
                    
                    # Check that RandomForestClassifier was instantiated
                    mock_rf_class.assert_called_once()
                    
                    # Check that fit was called multiple times (initial + incremental)
                    assert mock_rf.fit.call_count > 1
                    
                    # Check that early stopping occurred (not all iterations were used)
                    assert mock_rf.model.n_estimators < 100
    
    def test_train_with_early_stopping_non_rf_warning(self, synthetic_classification_data):
        """Test warning when using early stopping with non-Random Forest model."""
        X, y = synthetic_classification_data
        
        # Create train and validation sets
        X_train = X[:60]
        y_train = y[:60]
        X_val = X[60:80]
        y_val = y[60:80]
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {'target_accuracy': 0.99}
            
            # Mock SVMClassifier
            with patch('src.models.svm_classifier.SVMClassifier') as mock_svm_class:
                mock_svm = MagicMock()
                mock_svm.fit.return_value = None
                mock_svm.evaluate.return_value = {'accuracy': 0.95, 'f1': 0.94}
                mock_svm_class.return_value = mock_svm
                
                # Mock logger to capture warnings
                with patch('logging.Logger.warning') as mock_warning:
                    trainer = ModelTrainer()
                    model = trainer.train_with_early_stopping('svm', X_train, y_train, X_val, y_val)
                    
                    # Check that a warning was logged
                    mock_warning.assert_called_once()
                    assert "Early stopping is optimized for 'random_forest'" in mock_warning.call_args[0][0]
                    
                    # Check that train_model was called as fallback
                    assert mock_svm.fit.call_count == 1


# Test ensemble model training
class TestEnsembleTraining:
    """Tests for ensemble model training."""
    
    def test_train_ensemble_model(self, synthetic_classification_data):
        """Test training an ensemble of models."""
        X, y = synthetic_classification_data
        
        # Create train and validation sets
        X_train = X[:60]
        y_train = y[:60]
        X_val = X[60:80]
        y_val = y[60:80]
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'ensemble': {
                        'method': 'voting',
                        'voting': 'soft',
                        'weights': {
                            'svm': 0.4,
                            'random_forest': 0.6
                        }
                    },
                    'svm': {
                        'hyperparameters': {'C': 1.0, 'kernel': 'linear'}
                    },
                    'random_forest': {
                        'hyperparameters': {'n_estimators': 100, 'max_depth': None}
                    }
                }
            }
            
            # Mock classifiers
            with patch('src.models.svm_classifier.SVMClassifier') as mock_svm_class, \
                 patch('src.models.random_forest_classifier.RandomForestClassifier') as mock_rf_class:
                
                # Create mock SVM classifier
                mock_svm = MagicMock()
                mock_svm.fit.return_value = None
                mock_svm.predict.return_value = np.array(['invoice', 'license'] * 10)
                mock_svm.predict_proba.return_value = np.array([
                    [0.7, 0.1, 0.1, 0.05, 0.05],
                    [0.1, 0.7, 0.1, 0.05, 0.05]
                ] * 10)
                mock_svm_class.return_value = mock_svm
                
                # Create mock Random Forest classifier
                mock_rf = MagicMock()
                mock_rf.fit.return_value = None
                mock_rf.predict.return_value = np.array(['invoice', 'license'] * 10)
                mock_rf.predict_proba.return_value = np.array([
                    [0.8, 0.05, 0.05, 0.05, 0.05],
                    [0.05, 0.8, 0.05, 0.05, 0.05]
                ] * 10)
                mock_rf_class.return_value = mock_rf
                
                # Mock accuracy_score and f1_score
                with patch('sklearn.metrics.accuracy_score') as mock_accuracy, \
                     patch('sklearn.metrics.f1_score') as mock_f1:
                    
                    mock_accuracy.return_value = 0.95
                    mock_f1.return_value = 0.94
                    
                    trainer = ModelTrainer()
                    ensemble_results = trainer.train_ensemble_model(X_train, y_train, X_val, y_val)
                    
                    # Check that both classifiers were trained
                    mock_svm_class.assert_called_once()
                    mock_rf_class.assert_called_once()
                    mock_svm.fit.assert_called_once()
                    mock_rf.fit.assert_called_once()
                    
                    # Check ensemble results
                    assert 'models' in ensemble_results
                    assert 'weights' in ensemble_results
                    assert 'accuracy' in ensemble_results
                    assert 'f1_score' in ensemble_results
                    assert ensemble_results['accuracy'] == 0.95
                    assert ensemble_results['f1_score'] == 0.94
                    assert ensemble_results['weights'] == {'svm': 0.4, 'random_forest': 0.6}
                    assert ensemble_results['method'] == 'voting'
                    assert ensemble_results['voting'] == 'soft'
    
    def test_train_ensemble_model_hard_voting(self, synthetic_classification_data):
        """Test training an ensemble with hard voting."""
        X, y = synthetic_classification_data
        
        # Create train and validation sets
        X_train = X[:60]
        y_train = y[:60]
        X_val = X[60:80]
        y_val = y[60:80]
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'ensemble': {
                        'method': 'voting',
                        'voting': 'hard',
                        'weights': {
                            'svm': 0.5,
                            'random_forest': 0.5
                        }
                    }
                }
            }
            
            # Mock train_model method to return mock classifiers
            with patch.object(ModelTrainer, 'train_model') as mock_train_model:
                # Create mock classifiers
                mock_svm = MagicMock()
                mock_svm.predict.return_value = np.array(['invoice', 'license'] * 10)
                mock_svm.predict_proba.return_value = np.array([
                    [0.7, 0.1, 0.1, 0.05, 0.05],
                    [0.1, 0.7, 0.1, 0.05, 0.05]
                ] * 10)
                
                mock_rf = MagicMock()
                mock_rf.predict.return_value = np.array(['invoice', 'license'] * 10)
                mock_rf.predict_proba.return_value = np.array([
                    [0.8, 0.05, 0.05, 0.05, 0.05],
                    [0.05, 0.8, 0.05, 0.05, 0.05]
                ] * 10)
                
                # Configure mock_train_model to return different classifiers based on model_type
                mock_train_model.side_effect = lambda model_type, *args, **kwargs: \
                    mock_svm if model_type == 'svm' else mock_rf
                
                # Mock accuracy_score and f1_score
                with patch('sklearn.metrics.accuracy_score') as mock_accuracy, \
                     patch('sklearn.metrics.f1_score') as mock_f1:
                    
                    mock_accuracy.return_value = 0.95
                    mock_f1.return_value = 0.94
                    
                    trainer = ModelTrainer()
                    ensemble_results = trainer.train_ensemble_model(
                        X_train, y_train, X_val, y_val,
                        models=[('svm', {}), ('random_forest', {})]
                    )
                    
                    # Check that both classifiers were trained
                    assert mock_train_model.call_count == 2
                    
                    # Check ensemble results
                    assert ensemble_results['voting'] == 'hard'
                    assert ensemble_results['accuracy'] == 0.95
    
    def test_train_ensemble_model_no_models(self):
        """Test that train_ensemble_model raises error when no models are specified."""
        X = np.random.rand(10, 5)
        y = np.array(['a', 'b'] * 5)
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'ensemble': {
                        'weights': {}
                    }
                }
            }
            
            trainer = ModelTrainer()
            
            with pytest.raises(ValueError, match="No models specified for ensemble training"):
                trainer.train_ensemble_model(X, y, X, y, models=[])
    
    def test_train_ensemble_model_unsupported_method(self, synthetic_classification_data):
        """Test that train_ensemble_model raises error for unsupported ensemble method."""
        X, y = synthetic_classification_data
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'models': {
                    'ensemble': {
                        'method': 'unsupported_method',
                        'weights': {
                            'svm': 0.5,
                            'random_forest': 0.5
                        }
                    }
                }
            }
            
            # Mock train_model to return mock classifiers
            with patch.object(ModelTrainer, 'train_model') as mock_train_model:
                mock_train_model.return_value = MagicMock()
                
                trainer = ModelTrainer()
                
                with pytest.raises(ValueError, match="Unsupported ensemble method"):
                    trainer.train_ensemble_model(X, y, X, y)


# Test model saving
class TestModelSaving:
    """Tests for model saving functionality."""
    
    def test_save_trained_model(self, tmp_path):
        """Test saving a trained model with metadata."""
        # Create a mock model
        mock_model = MagicMock()
        mock_model.get_parameters.return_value = {'C': 1.0, 'kernel': 'linear'}
        mock_model.model = MagicMock()  # The underlying scikit-learn model
        
        # Create metrics
        metrics = {
            'accuracy': 0.95,
            'f1': 0.94,
            'precision': 0.93,
            'recall': 0.92
        }
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'base_dir': str(tmp_path)
            }
            
            # Mock save_model function
            with patch('src.models.model_serialization.save_model') as mock_save_model:
                mock_save_model.return_value = str(tmp_path / 'models/svm_classifier_1.0.0.pkl')
                
                trainer = ModelTrainer()
                model_path = trainer.save_trained_model(
                    mock_model, 'svm', metrics, version='1.0.0',
                    additional_metadata={'author': 'test'}
                )
                
                # Check that save_model was called with correct parameters
                mock_save_model.assert_called_once()
                args, kwargs = mock_save_model.call_args
                
                # Check model and model_type
                assert args[0] == mock_model.model
                assert args[1] == 'svm'
                assert args[2] == '1.0.0'
                
                # Check metadata
                metadata = args[3]
                assert metadata['model_type'] == 'svm'
                assert metadata['metrics'] == metrics
                assert metadata['hyperparameters'] == {'C': 1.0, 'kernel': 'linear'}
                assert metadata['target_accuracy'] == 0.99
                assert metadata['meets_requirements'] is False  # 0.95 < 0.99
                assert metadata['author'] == 'test'
                
                # Check model_dir
                assert kwargs['model_dir'] == str(tmp_path)
                
                # Check return value
                assert model_path == str(tmp_path / 'models/svm_classifier_1.0.0.pkl')


# Test complete training workflow
class TestCompleteWorkflow:
    """Tests for the complete model training workflow."""
    
    def test_train_and_evaluate_model(self, synthetic_classification_data):
        """Test the complete train_and_evaluate_model workflow."""
        X, y = synthetic_classification_data
        
        with patch('document_service.src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'base_dir': './models'
            }
            
            # Mock various methods to avoid actual computation
            with patch.object(ModelTrainer, 'prepare_dataset') as mock_prepare_dataset, \
                 patch.object(ModelTrainer, 'optimize_hyperparameters') as mock_optimize_hyperparams, \
                 patch.object(ModelTrainer, 'train_model') as mock_train_model, \
                 patch.object(ModelTrainer, 'save_trained_model') as mock_save_model, \
                 patch('document_service.src.models.model_evaluation.evaluate_model_performance') as mock_evaluate:
                
                # Configure mocks
                mock_prepare_dataset.side_effect = lambda X, y, **kwargs: (X[:80], X[80:], y[:80], y[80:])
                mock_optimize_hyperparams.return_value = ({'C': 1.0, 'kernel': 'linear'}, 0.95)
                
                mock_model = MagicMock()
                mock_model.evaluate.return_value = {'accuracy': 0.95, 'f1': 0.94}
                mock_model.predict.return_value = ['invoice', 'license'] * 10
                mock_model.predict_proba.return_value = np.random.rand(20, 5)
                mock_model.classes_ = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
                mock_train_model.return_value = mock_model
                
                mock_save_model.return_value = './models/svm_classifier_1.0.0.pkl'
                
                mock_evaluate.return_value = {
                    'accuracy': 0.95,
                    'precision': 0.94,
                    'recall': 0.93,
                    'f1': 0.94,
                    'confusion_matrix': np.array([[10, 0], [1, 9]])
                }
                
                trainer = ModelTrainer()
                model, metrics = trainer.train_and_evaluate_model(
                    'svm', X, y, optimize_hyperparams=True, save_model=True
                )
                
                # Check that all methods were called
                mock_prepare_dataset.assert_called_once()
                mock_optimize_hyperparams.assert_called_once()
                mock_train_model.assert_called_once()
                mock_model.evaluate.assert_called_once()
                mock_evaluate.assert_called_once()
                mock_save_model.assert_called_once()
                
                # Check results
                assert model == mock_model
                assert 'accuracy' in metrics
                assert 'detailed' in metrics
                assert 'model_path' in metrics
                assert metrics['model_path'] == './models/svm_classifier_1.0.0.pkl'
    
    def test_train_and_evaluate_model_with_early_stopping(self, synthetic_classification_data):
        """Test train_and_evaluate_model with early stopping."""
        X, y = synthetic_classification_data
        
        with patch('src.config.model_config.get_model_config') as mock_get_config:
            mock_get_config.return_value = {
                'target_accuracy': 0.99,
                'base_dir': './models'
            }
            
            # Mock various methods to avoid actual computation
            with patch.object(ModelTrainer, 'prepare_dataset') as mock_prepare_dataset, \
                 patch.object(ModelTrainer, 'train_with_early_stopping') as mock_early_stopping, \
                 patch.object(ModelTrainer, 'save_trained_model') as mock_save_model, \
                 patch('src.models.model_evaluation.evaluate_model_performance') as mock_evaluate:
                
                # Configure mocks
                mock_prepare_dataset.side_effect = [
                    (X[:80], X[80:], y[:80], y[80:]),  # First call
                    (X[:60], X[60:80], y[:60], y[60:80])  # Second call (for validation split)
                ]
                
                mock_model = MagicMock()
                mock_model.evaluate.return_value = {'accuracy': 0.95, 'f1': 0.94}
                mock_model.predict.return_value = ['invoice', 'license'] * 10
                mock_model.predict_proba.return_value = np.random.rand(20, 5)
                mock_model.classes_ = ['invoice', 'license', 'bank_statement', 'tax_document', 'application']
                mock_early_stopping.return_value = mock_model
                
                mock_save_model.return_value = './models/rf_classifier_1.0.0.pkl'
                
                mock_evaluate.return_value = {
                    'accuracy': 0.95,
                    'precision': 0.94,
                    'recall': 0.93,
                    'f1': 0.94,
                    'confusion_matrix': np.array([[10, 0], [1, 9]])
                }
                
                trainer = ModelTrainer()
                model, metrics = trainer.train_and_evaluate_model(
                    'random_forest', X, y, optimize_hyperparams=False, use_early_stopping=True, save_model=True
                )
                
                # Check that early stopping was used
                assert mock_prepare_dataset.call_count == 2
                mock_early_stopping.assert_called_once()
                
                # Check results
                assert model == mock_model
                assert 'accuracy' in metrics
                assert metrics['accuracy'] == 0.95