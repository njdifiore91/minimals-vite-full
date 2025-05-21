import os
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

# Import the module to test
from src.config.model_config import (
    MODEL_CONFIG,
    MODEL_BASE_DIR,
    MODEL_VERSION,
    MODEL_PATHS,
    DOCUMENT_CATEGORIES,
    CONFIDENCE_THRESHOLDS,
    DOCUMENT_CONFIDENCE_THRESHOLDS,
    FEATURE_EXTRACTION,
    SVM_CONFIG,
    RANDOM_FOREST_CONFIG,
    ENSEMBLE_CONFIG,
    EVALUATION_CONFIG,
    TRAINING_CONFIG,
    SERIALIZATION_CONFIG,
    get_model_config,
    get_model_path,
    get_confidence_threshold,
    get_model_hyperparameters
)


class TestModelConfig:
    """
    Test suite for the model_config.py module.
    
    These tests verify that model configuration correctly sets up classifier parameters,
    feature extraction settings, classification thresholds, and model paths.
    """

    def test_model_base_dir_creation(self):
        """Test that the model base directory is created if it doesn't exist."""
        # Create a temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Patch the MODEL_BASE_DIR to use our temporary directory
            with patch('src.config.model_config.MODEL_BASE_DIR', temp_dir):
                # Import the module again to trigger directory creation
                from importlib import reload
                import src.config.model_config
                reload(src.config.model_config)
                
                # Check that the directory exists
                assert os.path.exists(temp_dir)

    def test_model_version_format(self):
        """Test that the model version follows semantic versioning."""
        # Check that the version is a string
        assert isinstance(MODEL_VERSION, str)
        
        # Check that the version follows semantic versioning (x.y.z)
        version_parts = MODEL_VERSION.split('.')
        assert len(version_parts) == 3
        
        # Check that each part is a number
        for part in version_parts:
            assert part.isdigit()

    def test_model_paths(self):
        """Test that model paths are correctly constructed."""
        # Check that all required model types have paths
        required_models = ['svm', 'random_forest', 'ensemble']
        for model_type in required_models:
            assert model_type in MODEL_PATHS
            
            # Check that the path includes the base directory and version
            path = MODEL_PATHS[model_type]
            assert MODEL_BASE_DIR in path
            assert MODEL_VERSION in path
            
            # Check that the path has the correct extension
            assert path.endswith('.pkl')

    def test_document_categories(self):
        """Test that all required document categories are defined."""
        # Check that we have the required document categories
        required_categories = [
            'application_form',
            'bank_statement',
            'tax_return',
            'identity_document',
            'business_license',
            'invoice',
            'utility_bill',
            'credit_report',
            'financial_statement',
            'other'
        ]
        
        for category in required_categories:
            assert category in DOCUMENT_CATEGORIES

    def test_confidence_thresholds(self):
        """Test that confidence thresholds are correctly defined."""
        # Check that all required threshold levels are defined
        required_thresholds = ['high', 'medium', 'low', 'minimum']
        for level in required_thresholds:
            assert level in CONFIDENCE_THRESHOLDS
            
            # Check that thresholds are between 0 and 1
            assert 0 <= CONFIDENCE_THRESHOLDS[level] <= 1
        
        # Check that thresholds are in descending order
        assert CONFIDENCE_THRESHOLDS['high'] > CONFIDENCE_THRESHOLDS['medium']
        assert CONFIDENCE_THRESHOLDS['medium'] > CONFIDENCE_THRESHOLDS['low']
        assert CONFIDENCE_THRESHOLDS['low'] > CONFIDENCE_THRESHOLDS['minimum']

    def test_document_confidence_thresholds(self):
        """Test that document-specific confidence thresholds are correctly defined."""
        # Check that all document categories have thresholds
        for category in DOCUMENT_CATEGORIES:
            assert category in DOCUMENT_CONFIDENCE_THRESHOLDS
            
            # Check that thresholds are between 0 and 1
            assert 0 <= DOCUMENT_CONFIDENCE_THRESHOLDS[category] <= 1
        
        # Check that sensitive documents have higher thresholds
        assert DOCUMENT_CONFIDENCE_THRESHOLDS['identity_document'] >= 0.9
        
        # Check that the catch-all category has a lower threshold
        assert DOCUMENT_CONFIDENCE_THRESHOLDS['other'] <= 0.7

    def test_feature_extraction_config(self):
        """Test that feature extraction configuration is correctly defined."""
        # Check that all required sections are present
        required_sections = ['text', 'metadata', 'preprocessing', 'dimensionality_reduction']
        for section in required_sections:
            assert section in FEATURE_EXTRACTION
        
        # Check text vectorization settings
        assert FEATURE_EXTRACTION['text']['vectorizer'] == 'tfidf'
        assert isinstance(FEATURE_EXTRACTION['text']['max_features'], int)
        assert isinstance(FEATURE_EXTRACTION['text']['ngram_range'], tuple)
        assert len(FEATURE_EXTRACTION['text']['ngram_range']) == 2
        
        # Check metadata settings
        assert isinstance(FEATURE_EXTRACTION['metadata']['include'], bool)
        assert isinstance(FEATURE_EXTRACTION['metadata']['features'], list)
        
        # Check preprocessing settings
        assert isinstance(FEATURE_EXTRACTION['preprocessing']['lowercase'], bool)
        assert isinstance(FEATURE_EXTRACTION['preprocessing']['remove_punctuation'], bool)
        assert isinstance(FEATURE_EXTRACTION['preprocessing']['remove_digits'], bool)
        assert isinstance(FEATURE_EXTRACTION['preprocessing']['stemming'], bool)
        assert isinstance(FEATURE_EXTRACTION['preprocessing']['lemmatization'], bool)
        
        # Check dimensionality reduction settings
        assert isinstance(FEATURE_EXTRACTION['dimensionality_reduction']['apply'], bool)
        assert FEATURE_EXTRACTION['dimensionality_reduction']['method'] in ['pca', 'lda', 'tsne']
        assert isinstance(FEATURE_EXTRACTION['dimensionality_reduction']['n_components'], int)

    def test_svm_config(self):
        """Test that SVM classifier configuration is correctly defined."""
        # Check that the model type is correct
        assert SVM_CONFIG['model_type'] == 'svm'
        assert isinstance(SVM_CONFIG['enabled'], bool)
        
        # Check hyperparameters
        assert 'hyperparameters' in SVM_CONFIG
        assert 'C' in SVM_CONFIG['hyperparameters']
        assert 'kernel' in SVM_CONFIG['hyperparameters']
        assert 'gamma' in SVM_CONFIG['hyperparameters']
        assert 'probability' in SVM_CONFIG['hyperparameters']
        assert SVM_CONFIG['hyperparameters']['probability'] is True  # Required for confidence scores
        
        # Check hyperparameter tuning
        assert 'hyperparameter_tuning' in SVM_CONFIG
        assert 'perform' in SVM_CONFIG['hyperparameter_tuning']
        assert 'method' in SVM_CONFIG['hyperparameter_tuning']
        assert 'param_grid' in SVM_CONFIG['hyperparameter_tuning']
        assert 'C' in SVM_CONFIG['hyperparameter_tuning']['param_grid']
        assert 'kernel' in SVM_CONFIG['hyperparameter_tuning']['param_grid']

    def test_random_forest_config(self):
        """Test that Random Forest classifier configuration is correctly defined."""
        # Check that the model type is correct
        assert RANDOM_FOREST_CONFIG['model_type'] == 'random_forest'
        assert isinstance(RANDOM_FOREST_CONFIG['enabled'], bool)
        
        # Check hyperparameters
        assert 'hyperparameters' in RANDOM_FOREST_CONFIG
        assert 'n_estimators' in RANDOM_FOREST_CONFIG['hyperparameters']
        assert 'criterion' in RANDOM_FOREST_CONFIG['hyperparameters']
        assert 'max_depth' in RANDOM_FOREST_CONFIG['hyperparameters']
        assert 'random_state' in RANDOM_FOREST_CONFIG['hyperparameters']
        assert 'class_weight' in RANDOM_FOREST_CONFIG['hyperparameters']
        
        # Check hyperparameter tuning
        assert 'hyperparameter_tuning' in RANDOM_FOREST_CONFIG
        assert 'perform' in RANDOM_FOREST_CONFIG['hyperparameter_tuning']
        assert 'method' in RANDOM_FOREST_CONFIG['hyperparameter_tuning']
        assert 'param_distributions' in RANDOM_FOREST_CONFIG['hyperparameter_tuning']
        assert 'n_estimators' in RANDOM_FOREST_CONFIG['hyperparameter_tuning']['param_distributions']
        assert 'max_depth' in RANDOM_FOREST_CONFIG['hyperparameter_tuning']['param_distributions']

    def test_ensemble_config(self):
        """Test that ensemble configuration is correctly defined."""
        # Check that the model type is correct
        assert ENSEMBLE_CONFIG['model_type'] == 'ensemble'
        assert isinstance(ENSEMBLE_CONFIG['enabled'], bool)
        
        # Check ensemble settings
        assert 'method' in ENSEMBLE_CONFIG
        assert 'voting' in ENSEMBLE_CONFIG
        assert ENSEMBLE_CONFIG['voting'] in ['hard', 'soft']
        
        # Check weights
        assert 'weights' in ENSEMBLE_CONFIG
        assert 'svm' in ENSEMBLE_CONFIG['weights']
        assert 'random_forest' in ENSEMBLE_CONFIG['weights']
        assert sum(ENSEMBLE_CONFIG['weights'].values()) == 1.0  # Weights should sum to 1

    def test_evaluation_config(self):
        """Test that evaluation configuration is correctly defined."""
        # Check test size
        assert 'test_size' in EVALUATION_CONFIG
        assert 0 < EVALUATION_CONFIG['test_size'] < 1
        
        # Check metrics
        assert 'metrics' in EVALUATION_CONFIG
        required_metrics = ['accuracy', 'precision', 'recall', 'f1']
        for metric in required_metrics:
            assert metric in EVALUATION_CONFIG['metrics']
        
        # Check cross-validation
        assert 'cv' in EVALUATION_CONFIG
        assert isinstance(EVALUATION_CONFIG['cv'], int)
        assert EVALUATION_CONFIG['cv'] >= 3  # At least 3-fold CV
        
        # Check stratification
        assert 'stratify' in EVALUATION_CONFIG
        assert isinstance(EVALUATION_CONFIG['stratify'], bool)
        
        # Check threshold optimization
        assert 'threshold_optimization' in EVALUATION_CONFIG
        assert isinstance(EVALUATION_CONFIG['threshold_optimization'], bool)

    def test_training_config(self):
        """Test that training configuration is correctly defined."""
        # Check train-test split
        assert 'train_test_split' in TRAINING_CONFIG
        assert 'test_size' in TRAINING_CONFIG['train_test_split']
        assert 'random_state' in TRAINING_CONFIG['train_test_split']
        assert 'stratify' in TRAINING_CONFIG['train_test_split']
        
        # Check early stopping
        assert 'early_stopping' in TRAINING_CONFIG
        assert 'enabled' in TRAINING_CONFIG['early_stopping']
        assert 'patience' in TRAINING_CONFIG['early_stopping']
        assert 'min_delta' in TRAINING_CONFIG['early_stopping']
        
        # Check class balancing
        assert 'class_balancing' in TRAINING_CONFIG
        assert 'method' in TRAINING_CONFIG['class_balancing']
        assert TRAINING_CONFIG['class_balancing']['method'] in ['class_weight', 'oversampling', 'undersampling', 'smote']

    def test_serialization_config(self):
        """Test that serialization configuration is correctly defined."""
        # Check format
        assert 'format' in SERIALIZATION_CONFIG
        assert SERIALIZATION_CONFIG['format'] in ['pickle', 'joblib', 'onnx']
        
        # Check compression
        assert 'compression' in SERIALIZATION_CONFIG
        assert isinstance(SERIALIZATION_CONFIG['compression'], bool)
        
        # Check versioning
        assert 'versioning' in SERIALIZATION_CONFIG
        assert 'enabled' in SERIALIZATION_CONFIG['versioning']
        assert 'format' in SERIALIZATION_CONFIG['versioning']
        assert SERIALIZATION_CONFIG['versioning']['format'] in ['semver', 'date', 'custom']

    def test_get_model_config(self):
        """Test that get_model_config returns the complete model configuration."""
        config = get_model_config()
        
        # Check that the config is a dictionary
        assert isinstance(config, dict)
        
        # Check that all required sections are present
        required_sections = [
            'version', 'base_dir', 'paths', 'document_categories',
            'confidence_thresholds', 'document_confidence_thresholds',
            'feature_extraction', 'models', 'evaluation', 'training',
            'serialization', 'target_accuracy'
        ]
        
        for section in required_sections:
            assert section in config
        
        # Check that the models section contains all required models
        assert 'svm' in config['models']
        assert 'random_forest' in config['models']
        assert 'ensemble' in config['models']
        
        # Check that the target accuracy is 99% as per requirements
        assert config['target_accuracy'] == 0.99

    def test_get_model_path(self):
        """Test that get_model_path returns the correct path for a model type."""
        # Test valid model types
        for model_type in ['svm', 'random_forest', 'ensemble']:
            path = get_model_path(model_type)
            assert MODEL_BASE_DIR in path
            assert MODEL_VERSION in path
            assert path.endswith('.pkl')
        
        # Test invalid model type
        with pytest.raises(ValueError):
            get_model_path('invalid_model')

    def test_get_confidence_threshold(self):
        """Test that get_confidence_threshold returns the correct threshold for a document type."""
        # Test valid document types
        for doc_type in DOCUMENT_CATEGORIES:
            threshold = get_confidence_threshold(doc_type)
            assert 0 <= threshold <= 1
            assert threshold == DOCUMENT_CONFIDENCE_THRESHOLDS[doc_type]
        
        # Test invalid document type (should default to 'other')
        threshold = get_confidence_threshold('invalid_type')
        assert threshold == DOCUMENT_CONFIDENCE_THRESHOLDS['other']

    def test_get_model_hyperparameters(self):
        """Test that get_model_hyperparameters returns the correct hyperparameters for a model type."""
        # Test SVM
        svm_params = get_model_hyperparameters('svm')
        assert svm_params == SVM_CONFIG['hyperparameters']
        
        # Test Random Forest
        rf_params = get_model_hyperparameters('random_forest')
        assert rf_params == RANDOM_FOREST_CONFIG['hyperparameters']
        
        # Test invalid model type
        with pytest.raises(ValueError):
            get_model_hyperparameters('invalid_model')

    def test_model_config_consistency(self):
        """Test that the model configuration is internally consistent."""
        # Check that all document categories have confidence thresholds
        for category in DOCUMENT_CATEGORIES:
            assert category in DOCUMENT_CONFIDENCE_THRESHOLDS
        
        # Check that all model types in MODEL_PATHS have corresponding configurations
        for model_type in MODEL_PATHS.keys():
            if model_type == 'svm':
                assert model_type == SVM_CONFIG['model_type']
            elif model_type == 'random_forest':
                assert model_type == RANDOM_FOREST_CONFIG['model_type']
            elif model_type == 'ensemble':
                assert model_type == ENSEMBLE_CONFIG['model_type']
        
        # Check that ensemble weights reference valid model types
        for model_type in ENSEMBLE_CONFIG['weights'].keys():
            assert model_type in ['svm', 'random_forest']

    @patch('os.environ.get')
    def test_model_base_dir_from_environment(self, mock_environ_get):
        """Test that MODEL_BASE_DIR can be set from environment variables."""
        # Set up the mock to return a custom path
        custom_path = '/custom/model/path'
        mock_environ_get.return_value = custom_path
        
        # Import the module again to use the mocked environment variable
        with patch.dict('sys.modules'):
            from importlib import reload
            import src.config.model_config
            reload(src.config.model_config)
            
            # Check that the base directory is set from the environment
            assert src.config.model_config.MODEL_BASE_DIR == custom_path