#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Machine learning utilities for the Document Service.

This module provides utility functions for model loading, feature extraction,
prediction, and confidence scoring. It's essential for the document classification
functionality of the service using scikit-learn models.
"""

import os
import logging
import pickle
import joblib
import time
import json
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional, Any, Set

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix

# Import from other modules
from ..config.model_config import get_model_config, get_model_path, get_confidence_threshold
from ..models.feature_extraction import FeatureExtractor
from ..types.documents import Document, DocumentType
from ..types.classification import ClassificationResult, ConfidenceScore, ModelMetadata

# Set up logging
logger = logging.getLogger(__name__)


# Model loading functions
def load_model(model_type: str) -> BaseEstimator:
    """
    Load a trained model from disk.
    
    Args:
        model_type: Type of model to load (svm, random_forest, ensemble)
        
    Returns:
        Loaded scikit-learn model
        
    Raises:
        FileNotFoundError: If the model file doesn't exist
        ValueError: If the model type is not supported
    """
    model_config = get_model_config()
    model_path = get_model_path(model_type)
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    logger.info(f"Loading {model_type} model from {model_path}")
    
    try:
        # Try loading with joblib first (preferred for scikit-learn models)
        model = joblib.load(model_path)
        logger.info(f"Successfully loaded {model_type} model using joblib")
        return model
    except Exception as joblib_error:
        logger.warning(f"Failed to load model with joblib: {str(joblib_error)}")
        try:
            # Fall back to pickle if joblib fails
            with open(model_path, 'rb') as f:
                model = pickle.load(f)
            logger.info(f"Successfully loaded {model_type} model using pickle")
            return model
        except Exception as pickle_error:
            logger.error(f"Failed to load model with pickle: {str(pickle_error)}")
            raise ValueError(f"Failed to load model {model_type}: {str(pickle_error)}")


def load_all_models() -> Dict[str, BaseEstimator]:
    """
    Load all available trained models.
    
    Returns:
        Dictionary of model type to loaded model
    """
    model_config = get_model_config()
    models = {}
    
    for model_type in model_config["paths"].keys():
        try:
            models[model_type] = load_model(model_type)
        except (FileNotFoundError, ValueError) as e:
            logger.warning(f"Could not load {model_type} model: {str(e)}")
    
    if not models:
        logger.error("No models could be loaded")
    else:
        logger.info(f"Successfully loaded {len(models)} models: {', '.join(models.keys())}")
    
    return models


def get_model_metadata(model_type: str) -> ModelMetadata:
    """
    Get metadata for a trained model.
    
    Args:
        model_type: Type of model to get metadata for
        
    Returns:
        Model metadata
        
    Raises:
        FileNotFoundError: If the model metadata file doesn't exist
        ValueError: If the model type is not supported
    """
    model_config = get_model_config()
    model_path = get_model_path(model_type)
    metadata_path = f"{os.path.splitext(model_path)[0]}_metadata.json"
    
    if not os.path.exists(metadata_path):
        logger.warning(f"Model metadata file not found: {metadata_path}")
        # Return basic metadata if file doesn't exist
        return ModelMetadata(
            model_type=model_type,
            version=model_config["version"],
            created_at=datetime.fromtimestamp(os.path.getctime(model_path)) if os.path.exists(model_path) else datetime.now(),
            accuracy=None,
            f1_score=None,
            training_parameters=None
        )
    
    try:
        with open(metadata_path, 'r') as f:
            metadata_dict = json.load(f)
        
        # Convert string date to datetime
        if "created_at" in metadata_dict and isinstance(metadata_dict["created_at"], str):
            metadata_dict["created_at"] = datetime.fromisoformat(metadata_dict["created_at"])
        
        return ModelMetadata(**metadata_dict)
    except Exception as e:
        logger.error(f"Failed to load model metadata: {str(e)}")
        # Return basic metadata if loading fails
        return ModelMetadata(
            model_type=model_type,
            version=model_config["version"],
            created_at=datetime.fromtimestamp(os.path.getctime(model_path)) if os.path.exists(model_path) else datetime.now(),
            accuracy=None,
            f1_score=None,
            training_parameters=None
        )


# Feature extraction functions
def create_feature_extractor(config: Optional[Dict[str, Any]] = None) -> FeatureExtractor:
    """
    Create a feature extractor with the specified configuration.
    
    Args:
        config: Feature extraction configuration (if None, uses default from model_config)
        
    Returns:
        Configured feature extractor
    """
    if config is None:
        model_config = get_model_config()
        config = model_config["feature_extraction"]
    
    logger.info("Creating feature extractor with configuration")
    return FeatureExtractor(config)


def extract_features_from_document(document: Document, feature_extractor: Optional[FeatureExtractor] = None) -> np.ndarray:
    """
    Extract features from a document for classification.
    
    Args:
        document: Document to extract features from
        feature_extractor: Feature extractor to use (if None, creates a new one)
        
    Returns:
        Feature vector as numpy array
    """
    if feature_extractor is None:
        feature_extractor = create_feature_extractor()
    
    logger.info(f"Extracting features from document {document.metadata.id if hasattr(document.metadata, 'id') else 'unknown'}")
    
    # Check if feature extractor is fitted
    if not feature_extractor.is_fitted:
        logger.warning("Feature extractor not fitted. Using default extraction.")
        # For a single document, we can't properly fit the extractor
        # So we'll use a simplified approach
        from ..models.feature_extraction import TextExtractor, TextPreprocessor, MetadataExtractor
        
        # Extract text
        text_extractor = TextExtractor()
        text = text_extractor.extract_text(document)
        
        # Preprocess text
        text_preprocessor = TextPreprocessor()
        preprocessed_text = text_preprocessor.preprocess(text)
        
        # Extract metadata features
        metadata_extractor = MetadataExtractor()
        metadata_features = metadata_extractor.extract_metadata_features(document)
        
        # Combine features (simplified approach)
        # This is not ideal but allows for prediction without a fitted extractor
        features = np.array(list(metadata_features.values()))
        
        logger.warning("Using simplified feature extraction. Classification may be less accurate.")
        return features
    
    # Use the fitted feature extractor
    feature_vector = feature_extractor.extract_features_from_document(document)
    return feature_vector.values


# Prediction functions
def predict_document_type(document: Document, model: Optional[BaseEstimator] = None, 
                         feature_extractor: Optional[FeatureExtractor] = None) -> ClassificationResult:
    """
    Predict the document type for a document.
    
    Args:
        document: Document to classify
        model: Model to use for prediction (if None, loads the ensemble model)
        feature_extractor: Feature extractor to use (if None, creates a new one)
        
    Returns:
        Classification result with document type and confidence scores
    """
    model_config = get_model_config()
    
    # Load model if not provided
    if model is None:
        try:
            model = load_model("ensemble")
        except (FileNotFoundError, ValueError):
            logger.warning("Ensemble model not available. Trying random_forest model.")
            try:
                model = load_model("random_forest")
            except (FileNotFoundError, ValueError):
                logger.warning("Random forest model not available. Trying SVM model.")
                try:
                    model = load_model("svm")
                except (FileNotFoundError, ValueError):
                    raise ValueError("No classification models available")
    
    # Extract features
    features = extract_features_from_document(document, feature_extractor)
    features = features.reshape(1, -1)  # Reshape for single sample prediction
    
    # Get document categories
    document_categories = model_config["document_categories"]
    
    # Make prediction
    start_time = time.time()
    
    try:
        # Get predicted class
        predicted_class = model.predict(features)[0]
        
        # Get prediction probabilities if available
        if hasattr(model, "predict_proba"):
            probabilities = model.predict_proba(features)[0]
            confidence_scores = {
                category: float(prob) 
                for category, prob in zip(model.classes_, probabilities)
            }
        else:
            # For models without predict_proba, use decision function if available
            if hasattr(model, "decision_function"):
                decisions = model.decision_function(features)[0]
                # Convert decision values to pseudo-probabilities
                if len(model.classes_) == 2:  # Binary classification
                    # For binary classification, decision_function returns a single value
                    pos_score = 1 / (1 + np.exp(-decisions))  # Sigmoid function
                    confidence_scores = {
                        model.classes_[0]: float(1 - pos_score),
                        model.classes_[1]: float(pos_score)
                    }
                else:  # Multi-class classification
                    # Softmax to convert decision values to pseudo-probabilities
                    exp_decisions = np.exp(decisions - np.max(decisions))
                    softmax_scores = exp_decisions / exp_decisions.sum()
                    confidence_scores = {
                        category: float(score) 
                        for category, score in zip(model.classes_, softmax_scores)
                    }
            else:
                # If no probability or decision function, use binary confidence
                confidence_scores = {category: 1.0 if category == predicted_class else 0.0 for category in document_categories}
    except Exception as e:
        logger.error(f"Error during prediction: {str(e)}")
        # Return unknown classification with zero confidence
        return ClassificationResult(
            document_id=document.metadata.id if hasattr(document.metadata, "id") else None,
            document_type="unknown",
            confidence_scores={category: 0.0 for category in document_categories},
            prediction_time=time.time() - start_time,
            model_type=getattr(model, "_estimator_type", "unknown"),
            model_version=model_config["version"],
            threshold_applied=False,
            requires_review=True
        )
    
    # Get confidence threshold for the predicted document type
    threshold = get_confidence_threshold(predicted_class)
    
    # Check if confidence meets threshold
    predicted_confidence = confidence_scores.get(predicted_class, 0.0)
    requires_review = predicted_confidence < threshold
    
    # Create classification result
    result = ClassificationResult(
        document_id=document.metadata.id if hasattr(document.metadata, "id") else None,
        document_type=predicted_class,
        confidence_scores=confidence_scores,
        prediction_time=time.time() - start_time,
        model_type=getattr(model, "_estimator_type", "unknown"),
        model_version=model_config["version"],
        threshold_applied=True,
        requires_review=requires_review
    )
    
    logger.info(f"Classified document as {predicted_class} with confidence {predicted_confidence:.4f}")
    if requires_review:
        logger.info(f"Document requires review (confidence {predicted_confidence:.4f} < threshold {threshold:.4f})")
    
    return result


def predict_document_types_batch(documents: List[Document], model: Optional[BaseEstimator] = None,
                               feature_extractor: Optional[FeatureExtractor] = None) -> List[ClassificationResult]:
    """
    Predict document types for a batch of documents.
    
    Args:
        documents: List of documents to classify
        model: Model to use for prediction (if None, loads the ensemble model)
        feature_extractor: Feature extractor to use (if None, creates a new one)
        
    Returns:
        List of classification results
    """
    model_config = get_model_config()
    
    # Load model if not provided
    if model is None:
        try:
            model = load_model("ensemble")
        except (FileNotFoundError, ValueError):
            logger.warning("Ensemble model not available. Trying random_forest model.")
            try:
                model = load_model("random_forest")
            except (FileNotFoundError, ValueError):
                logger.warning("Random forest model not available. Trying SVM model.")
                try:
                    model = load_model("svm")
                except (FileNotFoundError, ValueError):
                    raise ValueError("No classification models available")
    
    # Create feature extractor if not provided
    if feature_extractor is None:
        feature_extractor = create_feature_extractor()
        
        # If we have enough documents, fit the feature extractor
        if len(documents) >= 5:  # Arbitrary threshold for fitting
            logger.info(f"Fitting feature extractor on {len(documents)} documents")
            feature_extractor.fit(documents)
    
    # Extract features for all documents
    features_list = []
    for doc in documents:
        try:
            features = extract_features_from_document(doc, feature_extractor)
            features_list.append(features)
        except Exception as e:
            logger.error(f"Error extracting features from document: {str(e)}")
            # Add a placeholder for failed feature extraction
            features_list.append(None)
    
    # Make predictions for documents with successful feature extraction
    results = []
    for i, (doc, features) in enumerate(zip(documents, features_list)):
        if features is None:
            # Create a failed classification result
            results.append(ClassificationResult(
                document_id=doc.metadata.id if hasattr(doc.metadata, "id") else None,
                document_type="unknown",
                confidence_scores={category: 0.0 for category in model_config["document_categories"]},
                prediction_time=0.0,
                model_type=getattr(model, "_estimator_type", "unknown"),
                model_version=model_config["version"],
                threshold_applied=False,
                requires_review=True,
                error="Feature extraction failed"
            ))
        else:
            try:
                # Reshape features for single sample prediction
                features_reshaped = features.reshape(1, -1)
                
                # Get predicted class
                predicted_class = model.predict(features_reshaped)[0]
                
                # Get prediction probabilities if available
                if hasattr(model, "predict_proba"):
                    probabilities = model.predict_proba(features_reshaped)[0]
                    confidence_scores = {
                        category: float(prob) 
                        for category, prob in zip(model.classes_, probabilities)
                    }
                else:
                    # For models without predict_proba, use decision function if available
                    if hasattr(model, "decision_function"):
                        decisions = model.decision_function(features_reshaped)[0]
                        # Convert decision values to pseudo-probabilities
                        if len(model.classes_) == 2:  # Binary classification
                            pos_score = 1 / (1 + np.exp(-decisions))  # Sigmoid function
                            confidence_scores = {
                                model.classes_[0]: float(1 - pos_score),
                                model.classes_[1]: float(pos_score)
                            }
                        else:  # Multi-class classification
                            exp_decisions = np.exp(decisions - np.max(decisions))
                            softmax_scores = exp_decisions / exp_decisions.sum()
                            confidence_scores = {
                                category: float(score) 
                                for category, score in zip(model.classes_, softmax_scores)
                            }
                    else:
                        # If no probability or decision function, use binary confidence
                        confidence_scores = {category: 1.0 if category == predicted_class else 0.0 
                                           for category in model_config["document_categories"]}
                
                # Get confidence threshold for the predicted document type
                threshold = get_confidence_threshold(predicted_class)
                
                # Check if confidence meets threshold
                predicted_confidence = confidence_scores.get(predicted_class, 0.0)
                requires_review = predicted_confidence < threshold
                
                # Create classification result
                results.append(ClassificationResult(
                    document_id=doc.metadata.id if hasattr(doc.metadata, "id") else None,
                    document_type=predicted_class,
                    confidence_scores=confidence_scores,
                    prediction_time=0.0,  # Not measuring individual prediction time in batch mode
                    model_type=getattr(model, "_estimator_type", "unknown"),
                    model_version=model_config["version"],
                    threshold_applied=True,
                    requires_review=requires_review
                ))
                
            except Exception as e:
                logger.error(f"Error during prediction for document {i}: {str(e)}")
                # Create a failed classification result
                results.append(ClassificationResult(
                    document_id=doc.metadata.id if hasattr(doc.metadata, "id") else None,
                    document_type="unknown",
                    confidence_scores={category: 0.0 for category in model_config["document_categories"]},
                    prediction_time=0.0,
                    model_type=getattr(model, "_estimator_type", "unknown"),
                    model_version=model_config["version"],
                    threshold_applied=False,
                    requires_review=True,
                    error=f"Prediction failed: {str(e)}"
                ))
    
    logger.info(f"Classified {len(documents)} documents in batch mode")
    return results


# Confidence scoring functions
def calculate_confidence_score(probabilities: Dict[str, float], predicted_class: str) -> ConfidenceScore:
    """
    Calculate a detailed confidence score for a classification result.
    
    Args:
        probabilities: Dictionary of class probabilities
        predicted_class: The predicted class
        
    Returns:
        Detailed confidence score
    """
    model_config = get_model_config()
    
    # Get the probability for the predicted class
    predicted_prob = probabilities.get(predicted_class, 0.0)
    
    # Get the second highest probability
    other_probs = [prob for cls, prob in probabilities.items() if cls != predicted_class]
    second_highest_prob = max(other_probs) if other_probs else 0.0
    
    # Calculate margin (difference between top two probabilities)
    margin = predicted_prob - second_highest_prob
    
    # Get confidence thresholds
    thresholds = model_config["confidence_thresholds"]
    document_threshold = get_confidence_threshold(predicted_class)
    
    # Determine confidence level
    if predicted_prob >= thresholds["high"]:
        confidence_level = "high"
    elif predicted_prob >= thresholds["medium"]:
        confidence_level = "medium"
    elif predicted_prob >= thresholds["low"]:
        confidence_level = "low"
    else:
        confidence_level = "very_low"
    
    # Determine if review is required
    requires_review = predicted_prob < document_threshold
    
    # Create confidence score
    return ConfidenceScore(
        value=float(predicted_prob),
        level=confidence_level,
        margin=float(margin),
        threshold=float(document_threshold),
        requires_review=requires_review
    )


def get_confidence_level(confidence_value: float) -> str:
    """
    Get the confidence level string for a confidence value.
    
    Args:
        confidence_value: Confidence value between 0 and 1
        
    Returns:
        Confidence level string (high, medium, low, very_low)
    """
    model_config = get_model_config()
    thresholds = model_config["confidence_thresholds"]
    
    if confidence_value >= thresholds["high"]:
        return "high"
    elif confidence_value >= thresholds["medium"]:
        return "medium"
    elif confidence_value >= thresholds["low"]:
        return "low"
    else:
        return "very_low"


# Model evaluation functions
def evaluate_model_performance(model: BaseEstimator, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, Any]:
    """
    Evaluate the performance of a model on test data.
    
    Args:
        model: Trained model to evaluate
        X_test: Test features
        y_test: True labels for test data
        
    Returns:
        Dictionary of performance metrics
    """
    # Make predictions
    y_pred = model.predict(X_test)
    
    # Calculate metrics
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, average="weighted")
    recall = recall_score(y_test, y_pred, average="weighted")
    f1 = f1_score(y_test, y_pred, average="weighted")
    conf_matrix = confusion_matrix(y_test, y_pred)
    
    # Get prediction probabilities if available
    if hasattr(model, "predict_proba"):
        y_proba = model.predict_proba(X_test)
        # Calculate average confidence
        avg_confidence = np.mean([proba[np.argmax(proba)] for proba in y_proba])
    else:
        avg_confidence = None
    
    # Create performance metrics dictionary
    metrics = {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1_score": float(f1),
        "confusion_matrix": conf_matrix.tolist(),
        "average_confidence": float(avg_confidence) if avg_confidence is not None else None,
        "sample_count": len(y_test)
    }
    
    logger.info(f"Model evaluation results: accuracy={accuracy:.4f}, f1_score={f1:.4f}")
    return metrics


def monitor_prediction_performance(predictions: List[ClassificationResult]) -> Dict[str, Any]:
    """
    Monitor the performance of predictions in production.
    
    Args:
        predictions: List of classification results
        
    Returns:
        Dictionary of monitoring metrics
    """
    if not predictions:
        return {}
    
    # Calculate metrics
    total_predictions = len(predictions)
    requires_review_count = sum(1 for p in predictions if p.requires_review)
    error_count = sum(1 for p in predictions if hasattr(p, "error") and p.error)
    
    # Calculate average confidence by document type
    confidence_by_type = {}
    for p in predictions:
        if p.document_type not in confidence_by_type:
            confidence_by_type[p.document_type] = []
        if p.document_type in p.confidence_scores:
            confidence_by_type[p.document_type].append(p.confidence_scores[p.document_type])
    
    avg_confidence_by_type = {
        doc_type: sum(scores) / len(scores) if scores else 0.0
        for doc_type, scores in confidence_by_type.items()
    }
    
    # Calculate average prediction time
    avg_prediction_time = sum(p.prediction_time for p in predictions) / total_predictions if total_predictions > 0 else 0.0
    
    # Create monitoring metrics dictionary
    metrics = {
        "total_predictions": total_predictions,
        "requires_review_count": requires_review_count,
        "requires_review_percentage": requires_review_count / total_predictions if total_predictions > 0 else 0.0,
        "error_count": error_count,
        "error_percentage": error_count / total_predictions if total_predictions > 0 else 0.0,
        "average_confidence_by_type": avg_confidence_by_type,
        "average_prediction_time": avg_prediction_time
    }
    
    return metrics


# Model versioning functions
def get_model_version() -> str:
    """
    Get the current model version.
    
    Returns:
        Current model version string
    """
    model_config = get_model_config()
    return model_config["version"]


def check_model_compatibility(model: BaseEstimator) -> bool:
    """
    Check if a model is compatible with the current configuration.
    
    Args:
        model: Model to check compatibility for
        
    Returns:
        True if compatible, False otherwise
    """
    # Check if model has the expected attributes for its type
    if isinstance(model, RandomForestClassifier):
        expected_attrs = ["n_estimators", "criterion", "max_depth"]
    elif isinstance(model, SVC):
        expected_attrs = ["C", "kernel", "gamma"]
    else:
        # For other model types, just check if it has predict method
        return hasattr(model, "predict")
    
    # Check if model has all expected attributes
    return all(hasattr(model, attr) for attr in expected_attrs)


def validate_model(model: BaseEstimator, X_sample: np.ndarray, expected_classes: Set[str]) -> bool:
    """
    Validate that a model can make predictions and has the expected classes.
    
    Args:
        model: Model to validate
        X_sample: Sample features for prediction
        expected_classes: Set of expected class labels
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Check if model can make predictions
        _ = model.predict(X_sample)
        
        # Check if model has the expected classes
        if hasattr(model, "classes_"):
            model_classes = set(model.classes_)
            if not expected_classes.issubset(model_classes):
                logger.warning(f"Model is missing expected classes. Expected: {expected_classes}, Got: {model_classes}")
                return False
        
        return True
    except Exception as e:
        logger.error(f"Model validation failed: {str(e)}")
        return False