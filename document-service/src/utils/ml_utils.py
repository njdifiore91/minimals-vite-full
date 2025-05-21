#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Machine Learning Utilities for Document Service

This module provides utility functions for machine learning operations in the Document Service,
including model loading, feature extraction, prediction, confidence scoring, and performance monitoring.

These utilities support the document classification functionality using scikit-learn models.
"""

import os
import time
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Union, Optional, Any, Callable
from sklearn.base import BaseEstimator
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
from joblib import dump, load

# Import local modules
try:
    from config import model_config
    from utils import logging_utils, error_utils, time_utils
except ImportError:
    # Handle relative imports when running as script
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).resolve().parent.parent))
    from config import model_config
    from utils import logging_utils, error_utils, time_utils

logger = logging.getLogger(__name__)

# Constants
MODEL_VERSION_KEY = "model_version"
MODEL_TIMESTAMP_KEY = "timestamp"
MODEL_METRICS_KEY = "metrics"
MODEL_PARAMS_KEY = "parameters"
MODEL_FEATURES_KEY = "features"


def load_model(model_path: str) -> Tuple[BaseEstimator, Dict[str, Any]]:
    """
    Load a scikit-learn model and its metadata from disk.
    
    Args:
        model_path: Path to the saved model file
        
    Returns:
        Tuple containing the loaded model and its metadata dictionary
        
    Raises:
        FileNotFoundError: If the model file doesn't exist
        ValueError: If the loaded file is not a valid model
    """
    start_time = time.time()
    try:
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model file not found at {model_path}")
        
        # Load the model and metadata
        model_data = load(model_path)
        
        # Validate model data structure
        if not isinstance(model_data, dict) or 'model' not in model_data or 'metadata' not in model_data:
            raise ValueError(f"Invalid model format at {model_path}")
        
        model = model_data['model']
        metadata = model_data['metadata']
        
        # Log model loading
        version = metadata.get(MODEL_VERSION_KEY, 'unknown')
        logger.info(
            f"Loaded model version {version} from {model_path} "
            f"in {time_utils.format_duration(time.time() - start_time)}"
        )
        
        return model, metadata
    
    except Exception as e:
        error_msg = f"Failed to load model from {model_path}: {str(e)}"
        logger.error(error_msg)
        raise error_utils.create_error("ModelLoadError", error_msg, e) from e


def save_model(model: BaseEstimator, metadata: Dict[str, Any], model_path: str) -> str:
    """
    Save a scikit-learn model and its metadata to disk.
    
    Args:
        model: The scikit-learn model to save
        metadata: Dictionary containing model metadata
        model_path: Path where the model should be saved
        
    Returns:
        Path to the saved model file
        
    Raises:
        ValueError: If the model or metadata is invalid
        IOError: If the model cannot be saved
    """
    start_time = time.time()
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        # Update metadata with timestamp if not present
        if MODEL_TIMESTAMP_KEY not in metadata:
            metadata[MODEL_TIMESTAMP_KEY] = time_utils.get_iso_timestamp()
        
        # Create model data dictionary
        model_data = {
            'model': model,
            'metadata': metadata
        }
        
        # Save the model
        dump(model_data, model_path, compress=3)
        
        # Log model saving
        version = metadata.get(MODEL_VERSION_KEY, 'unknown')
        logger.info(
            f"Saved model version {version} to {model_path} "
            f"in {time_utils.format_duration(time.time() - start_time)}"
        )
        
        return model_path
    
    except Exception as e:
        error_msg = f"Failed to save model to {model_path}: {str(e)}"
        logger.error(error_msg)
        raise error_utils.create_error("ModelSaveError", error_msg, e) from e


def create_feature_extractor(config: Dict[str, Any] = None) -> Pipeline:
    """
    Create a scikit-learn pipeline for feature extraction based on configuration.
    
    Args:
        config: Configuration dictionary for feature extraction
               If None, uses default configuration from model_config
               
    Returns:
        A scikit-learn Pipeline for feature extraction
    """
    if config is None:
        config = model_config.FEATURE_EXTRACTION_CONFIG
    
    # Create TF-IDF vectorizer
    tfidf_params = config.get('tfidf', {})
    tfidf = TfidfVectorizer(
        max_features=tfidf_params.get('max_features', 10000),
        min_df=tfidf_params.get('min_df', 5),
        max_df=tfidf_params.get('max_df', 0.85),
        ngram_range=tfidf_params.get('ngram_range', (1, 2)),
        stop_words=tfidf_params.get('stop_words', 'english')
    )
    
    # Create dimensionality reduction if configured
    use_svd = config.get('use_svd', True)
    pipeline_steps = [('tfidf', tfidf)]
    
    if use_svd:
        svd_params = config.get('svd', {})
        svd = TruncatedSVD(
            n_components=svd_params.get('n_components', 100),
            random_state=svd_params.get('random_state', 42)
        )
        pipeline_steps.append(('svd', svd))
    
    # Add scaling if configured
    use_scaling = config.get('use_scaling', True)
    if use_scaling:
        pipeline_steps.append(('scaler', StandardScaler()))
    
    return Pipeline(pipeline_steps)


def extract_features(documents: List[str], extractor: Optional[Pipeline] = None) -> np.ndarray:
    """
    Extract features from a list of document texts.
    
    Args:
        documents: List of document texts to extract features from
        extractor: Feature extraction pipeline (if None, creates a new one)
        
    Returns:
        Numpy array of extracted features
        
    Raises:
        ValueError: If documents is empty or contains non-string elements
    """
    if not documents:
        raise ValueError("Empty document list provided for feature extraction")
    
    if not all(isinstance(doc, str) for doc in documents):
        raise ValueError("All documents must be strings")
    
    # Create extractor if not provided
    if extractor is None:
        extractor = create_feature_extractor()
        # Fit and transform
        return extractor.fit_transform(documents)
    
    # If extractor is already fitted, just transform
    try:
        return extractor.transform(documents)
    except Exception as e:
        # If transform fails, try fit_transform (extractor might not be fitted)
        try:
            return extractor.fit_transform(documents)
        except Exception as inner_e:
            error_msg = f"Feature extraction failed: {str(inner_e)}"
            logger.error(error_msg)
            raise error_utils.create_error("FeatureExtractionError", error_msg, inner_e) from inner_e


def get_prediction_confidence(probabilities: np.ndarray, method: str = 'max_prob') -> np.ndarray:
    """
    Calculate confidence scores for predictions based on probability distributions.
    
    Args:
        probabilities: Array of class probabilities from classifier
        method: Method to calculate confidence
                'max_prob': Maximum probability (default)
                'margin': Difference between top two probabilities
                'entropy': Entropy-based confidence (higher entropy = lower confidence)
                
    Returns:
        Array of confidence scores (0-1 range)
    """
    if method == 'max_prob':
        # Simply use the maximum probability as confidence
        return np.max(probabilities, axis=1)
    
    elif method == 'margin':
        # Sort probabilities in descending order
        sorted_probs = np.sort(probabilities, axis=1)[:, ::-1]
        # Calculate margin between top two classes
        # If only one class, use the probability directly
        if sorted_probs.shape[1] > 1:
            return sorted_probs[:, 0] - sorted_probs[:, 1]
        else:
            return sorted_probs[:, 0]
    
    elif method == 'entropy':
        # Calculate entropy of the probability distribution
        # Add small epsilon to avoid log(0)
        epsilon = 1e-10
        entropy = -np.sum(probabilities * np.log(probabilities + epsilon), axis=1)
        # Normalize to 0-1 range (max entropy is log(n_classes))
        n_classes = probabilities.shape[1]
        max_entropy = np.log(n_classes)
        # Convert to confidence (1 - normalized entropy)
        return 1.0 - (entropy / max_entropy)
    
    else:
        raise ValueError(f"Unknown confidence method: {method}")


def predict_with_confidence(
    model: BaseEstimator, 
    features: np.ndarray, 
    confidence_method: str = 'max_prob',
    confidence_threshold: float = 0.75
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Make predictions with a classifier and calculate confidence scores.
    
    Args:
        model: Trained classifier model
        features: Feature matrix for prediction
        confidence_method: Method to calculate confidence
        confidence_threshold: Threshold for high/low confidence classification
        
    Returns:
        Tuple of (predictions, probabilities, confidence_scores)
        
    Raises:
        ValueError: If model doesn't support predict_proba
    """
    # Check if model supports probability estimates
    if not hasattr(model, 'predict_proba'):
        raise ValueError("Model does not support probability estimation")
    
    # Get predictions and probabilities
    predictions = model.predict(features)
    probabilities = model.predict_proba(features)
    
    # Calculate confidence scores
    confidence_scores = get_prediction_confidence(probabilities, method=confidence_method)
    
    # Log prediction statistics
    low_confidence_count = np.sum(confidence_scores < confidence_threshold)
    logger.info(
        f"Made {len(predictions)} predictions with "
        f"{low_confidence_count} below confidence threshold {confidence_threshold}"
    )
    
    return predictions, probabilities, confidence_scores


def evaluate_model_performance(
    model: BaseEstimator, 
    X_test: np.ndarray, 
    y_test: np.ndarray,
    class_names: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Evaluate model performance on test data and return metrics.
    
    Args:
        model: Trained classifier model
        X_test: Test feature matrix
        y_test: True labels for test data
        class_names: List of class names (optional)
        
    Returns:
        Dictionary containing performance metrics
    """
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate basic metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(y_test, y_pred, average='weighted')
    
    # Calculate confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    
    # Calculate per-class metrics if class names are provided
    class_metrics = None
    if class_names is not None:
        prec, rec, f1, supp = precision_recall_fscore_support(y_test, y_pred, average=None)
        class_metrics = {
            name: {
                'precision': float(prec[i]),
                'recall': float(rec[i]),
                'f1': float(f1[i]),
                'support': int(supp[i])
            } for i, name in enumerate(class_names)
        }
    
    # Compile metrics dictionary
    metrics = {
        'accuracy': float(accuracy),
        'precision': float(precision),
        'recall': float(recall),
        'f1': float(f1),
        'confusion_matrix': cm.tolist(),
        'support': int(np.sum(support)),
        'timestamp': time_utils.get_iso_timestamp()
    }
    
    if class_metrics:
        metrics['class_metrics'] = class_metrics
    
    return metrics


def track_model_performance(model_name: str, metrics: Dict[str, Any]) -> None:
    """
    Track model performance metrics for monitoring.
    
    Args:
        model_name: Name of the model being tracked
        metrics: Dictionary of performance metrics
    """
    # Log performance metrics
    logger.info(f"Model {model_name} performance: accuracy={metrics['accuracy']:.4f}, "
                f"precision={metrics['precision']:.4f}, recall={metrics['recall']:.4f}, "
                f"f1={metrics['f1']:.4f}")
    
    # Here we would typically send metrics to a monitoring system
    # This could be implemented with various backends (Prometheus, CloudWatch, etc.)
    # For now, we'll just log them
    
    # Example of how this might be implemented with a monitoring client:
    # try:
    #     monitoring_client.record_metrics({
    #         f"model.{model_name}.accuracy": metrics['accuracy'],
    #         f"model.{model_name}.precision": metrics['precision'],
    #         f"model.{model_name}.recall": metrics['recall'],
    #         f"model.{model_name}.f1": metrics['f1']
    #     })
    # except Exception as e:
    #     logger.warning(f"Failed to record metrics to monitoring system: {str(e)}")


def validate_model(model: BaseEstimator, expected_classes: List[str]) -> bool:
    """
    Validate that a model meets basic requirements for use.
    
    Args:
        model: Model to validate
        expected_classes: List of class names the model should predict
        
    Returns:
        True if model is valid, False otherwise
    """
    # Check that model has required methods
    required_methods = ['fit', 'predict', 'predict_proba']
    for method in required_methods:
        if not hasattr(model, method):
            logger.error(f"Model validation failed: missing required method '{method}'")
            return False
    
    # Check that model has expected classes
    if hasattr(model, 'classes_'):
        model_classes = model.classes_
        if len(model_classes) != len(expected_classes) or not all(c in model_classes for c in expected_classes):
            logger.error(f"Model validation failed: expected classes {expected_classes}, "
                        f"got {model_classes}")
            return False
    else:
        logger.warning("Model validation: model has no classes_ attribute, skipping class validation")
    
    return True


def get_model_version_info(model_path: str) -> Dict[str, Any]:
    """
    Get version information for a saved model.
    
    Args:
        model_path: Path to the saved model file
        
    Returns:
        Dictionary containing model version information
        
    Raises:
        FileNotFoundError: If the model file doesn't exist
    """
    try:
        _, metadata = load_model(model_path)
        
        # Extract relevant version info
        version_info = {
            'version': metadata.get(MODEL_VERSION_KEY, 'unknown'),
            'timestamp': metadata.get(MODEL_TIMESTAMP_KEY, 'unknown'),
            'parameters': metadata.get(MODEL_PARAMS_KEY, {}),
        }
        
        # Add performance metrics if available
        if MODEL_METRICS_KEY in metadata:
            metrics = metadata[MODEL_METRICS_KEY]
            version_info['accuracy'] = metrics.get('accuracy', 'unknown')
            version_info['f1'] = metrics.get('f1', 'unknown')
        
        return version_info
    
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.error(f"Failed to get model version info: {str(e)}")
        return {'version': 'unknown', 'error': str(e)}


def compare_model_versions(model_paths: List[str]) -> pd.DataFrame:
    """
    Compare multiple model versions and their performance metrics.
    
    Args:
        model_paths: List of paths to model files to compare
        
    Returns:
        Pandas DataFrame with model comparison information
    """
    comparison_data = []
    
    for path in model_paths:
        try:
            version_info = get_model_version_info(path)
            version_info['path'] = path
            comparison_data.append(version_info)
        except Exception as e:
            logger.warning(f"Skipping model at {path} due to error: {str(e)}")
    
    # Convert to DataFrame for easier analysis
    if comparison_data:
        return pd.DataFrame(comparison_data)
    else:
        return pd.DataFrame(columns=['version', 'timestamp', 'accuracy', 'f1', 'path'])


def get_feature_importance(model: BaseEstimator, feature_names: List[str] = None) -> Dict[str, float]:
    """
    Extract feature importance from a trained model if available.
    
    Args:
        model: Trained model
        feature_names: List of feature names (optional)
        
    Returns:
        Dictionary mapping feature names to importance scores,
        or empty dict if model doesn't support feature importance
    """
    # Different models store feature importance in different attributes
    importance_attrs = ['feature_importances_', 'coef_']
    
    # Try to find feature importance attribute
    importance = None
    for attr in importance_attrs:
        if hasattr(model, attr):
            importance = getattr(model, attr)
            break
    
    if importance is None:
        logger.info("Model doesn't provide feature importance information")
        return {}
    
    # Handle different shapes of importance values
    if importance.ndim > 1:
        # For multi-class models with coef_ (e.g., LinearSVC, LogisticRegression)
        # Use the average absolute value across classes
        importance = np.abs(importance).mean(axis=0)
    
    # If feature names not provided, use generic names
    if feature_names is None:
        feature_names = [f"feature_{i}" for i in range(len(importance))]
    
    # Ensure we have the right number of feature names
    if len(feature_names) != len(importance):
        logger.warning(
            f"Feature names length ({len(feature_names)}) doesn't match "
            f"importance length ({len(importance)}). Using generic names."
        )
        feature_names = [f"feature_{i}" for i in range(len(importance))]
    
    # Create dictionary of feature importance
    importance_dict = {name: float(imp) for name, imp in zip(feature_names, importance)}
    
    # Sort by importance (descending)
    return dict(sorted(importance_dict.items(), key=lambda x: x[1], reverse=True))


def get_model_size(model: BaseEstimator) -> str:
    """
    Estimate the memory size of a model.
    
    Args:
        model: The model to measure
        
    Returns:
        Human-readable string representing the model size
    """
    import sys
    import tempfile
    
    # Save model to a temporary file to measure its size
    with tempfile.NamedTemporaryFile() as tmp:
        dump(model, tmp.name)
        size_bytes = os.path.getsize(tmp.name)
    
    # Convert to human-readable format
    units = ['B', 'KB', 'MB', 'GB']
    size = size_bytes
    unit_index = 0
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"