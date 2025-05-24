#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Classifier for the Document Service.

This module implements the main document classifier that orchestrates the document classification
process in the Document Service. It provides a high-level interface for document classification,
combining feature extraction, model selection, prediction, and confidence scoring.

The DocumentClassifier uses an ensemble approach, combining SVM and Random Forest classifiers
to achieve high accuracy in document classification. It provides confidence scoring based on
the ensemble predictions and includes methods for routing documents to appropriate OCR processors.

Example usage:
    # Initialize the classifier
    classifier = DocumentClassifier()
    
    # Train the classifier on document features
    classifier.fit(features, labels)
    
    # Classify a document with confidence scoring
    document_type, confidence = classifier.classify(features)
    
    # Get routing information for OCR processing
    routing_info = classifier.get_routing_info(document_type, confidence)
"""

import logging
import time
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any, cast

# Import base model and specific classifiers
from .base_model import BaseModel, T
from .svm_classifier import SVMClassifier
from .random_forest_classifier import RandomForestClassifier

# Import types
from ..types.classification import (
    ClassificationModel,
    FeatureVector,
    ClassificationResult,
    ConfidenceScore,
    ModelParameters,
    ClassificationMetrics
)
from ..types.documents import DocumentType
from ..types.config import ModelConfig
from ..types.errors import Result

# Set up logging
logger = logging.getLogger(__name__)


class DocumentClassifier(BaseModel['DocumentClassifier']):
    """
    Main document classifier that orchestrates the document classification process.
    
    This class combines multiple classification models (SVM and Random Forest) in an
    ensemble approach to achieve high accuracy in document classification. It provides
    methods for training, prediction, confidence scoring, and document routing.
    
    The classifier uses a weighted voting scheme to combine predictions from different
    models, with weights determined by model performance and confidence scores.
    
    Attributes:
        config (ModelConfig): Configuration parameters for the classifier.
        svm_classifier (SVMClassifier): SVM classifier instance.
        rf_classifier (RandomForestClassifier): Random Forest classifier instance.
        ensemble_weights (Dict[str, float]): Weights for each classifier in the ensemble.
        model_name (str): Name of the model for identification and logging.
        model_version (str): Version of the model for tracking and compatibility.
        classes_ (Optional[np.ndarray]): Array of class labels known to the classifier.
        trained (bool): Flag indicating whether the model has been trained.
        feature_names (Optional[List[str]]): Names of features used by the model.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the document classifier with configuration parameters.
        
        Args:
            config (ModelConfig): Configuration parameters for the classifier.
        """
        super().__init__(config)
        
        # Initialize component classifiers
        self.svm_classifier = SVMClassifier(self._get_svm_params())
        self.rf_classifier = RandomForestClassifier(self._get_rf_params())
        
        # Set default ensemble weights
        self.ensemble_weights = {
            'svm': config.get('svm_weight', 0.5),
            'random_forest': config.get('rf_weight', 0.5)
        }
        
        # Normalize weights to sum to 1
        weight_sum = sum(self.ensemble_weights.values())
        if weight_sum > 0:
            self.ensemble_weights = {k: v / weight_sum for k, v in self.ensemble_weights.items()}
        
        # Initialize performance metrics
        self.metrics = {
            'accuracy': 0.0,
            'precision': {},
            'recall': {},
            'f1_score': {},
            'confusion_matrix': None,
            'classification_time': 0.0
        }
        
        logger.info(f"Initialized DocumentClassifier with ensemble weights: {self.ensemble_weights}")
    
    def _get_svm_params(self) -> ModelParameters:
        """
        Get SVM-specific parameters from the configuration.
        
        Returns:
            ModelParameters: Parameters for the SVM classifier.
        """
        svm_params = self.config.get('svm_params', {})
        
        # Set default SVM parameters if not specified
        default_params = {
            "C": 1.0,
            "kernel": "rbf",
            "gamma": "scale",
            "probability": True,
            "class_weight": "balanced",
            "random_state": 42
        }
        
        # Update defaults with provided parameters
        default_params.update(svm_params)
        
        return default_params
    
    def _get_rf_params(self) -> ModelParameters:
        """
        Get Random Forest-specific parameters from the configuration.
        
        Returns:
            ModelParameters: Parameters for the Random Forest classifier.
        """
        rf_params = self.config.get('rf_params', {})
        
        # Set default Random Forest parameters if not specified
        default_params = {
            "n_estimators": 100,
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "max_features": "sqrt",
            "bootstrap": True,
            "oob_score": True,
            "n_jobs": -1,
            "random_state": 42,
            "class_weight": "balanced"
        }
        
        # Update defaults with provided parameters
        default_params.update(rf_params)
        
        return default_params
    
    def fit(self, X: FeatureVector, y: np.ndarray) -> 'DocumentClassifier':
        """
        Train the document classifier on the provided data.
        
        This method trains both the SVM and Random Forest classifiers on the provided
        feature vectors and target labels, then updates the ensemble weights based on
        their performance.
        
        Args:
            X (FeatureVector): Feature vectors for training.
            y (np.ndarray): Target labels for training.
            
        Returns:
            DocumentClassifier: The trained classifier instance (self) for method chaining.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If training fails due to internal errors.
        """
        # Validate input data
        self._validate_input(X, y)
        
        start_time = time.time()
        logger.info(f"Training DocumentClassifier on {X.shape[0]} samples with {X.shape[1]} features")
        
        # Store class labels before training to ensure consistency
        self.classes_ = np.unique(y)
        
        # Train SVM classifier
        logger.info("Training SVM classifier...")
        self.svm_classifier.fit(X, y)
        
        # Train Random Forest classifier
        logger.info("Training Random Forest classifier...")
        self.rf_classifier.fit(X, y)
        
        # Ensure both classifiers have the same class mapping
        # This is important for consistent ensemble predictions
        if hasattr(self.svm_classifier, 'class_mapping') and hasattr(self.rf_classifier, 'class_mapping'):
            # Verify class mappings are consistent
            svm_classes = set(self.svm_classifier.class_mapping.values())
            rf_classes = set(self.rf_classifier.class_mapping.values())
            if svm_classes != rf_classes:
                logger.warning("Class mappings between SVM and RF classifiers are inconsistent")
                # Use SVM mapping as the reference
                self.rf_classifier.class_mapping = self.svm_classifier.class_mapping.copy()
                self.rf_classifier.inverse_class_mapping = self.svm_classifier.inverse_class_mapping.copy()
        
        # Update ensemble weights based on performance if auto-weighting is enabled
        if self.config.get('auto_weighting', True):
            self._update_ensemble_weights(X, y)
        
        # Set trained flag
        self.trained = True
        
        # Store feature names if available
        if hasattr(X, 'columns'):
            self.feature_names = list(X.columns)
            # Also set feature names for component classifiers
            if hasattr(self.svm_classifier, 'set_feature_names'):
                self.svm_classifier.set_feature_names(self.feature_names)
            if hasattr(self.rf_classifier, 'set_feature_names'):
                self.rf_classifier.set_feature_names(self.feature_names)
        
        # Calculate and log training time
        training_time = time.time() - start_time
        logger.info(f"DocumentClassifier training completed in {training_time:.2f} seconds")
        logger.info(f"Updated ensemble weights: {self.ensemble_weights}")
        
        return self
    
    def _update_ensemble_weights(self, X: FeatureVector, y: np.ndarray) -> None:
        """
        Update ensemble weights based on classifier performance.
        
        This method evaluates each classifier on the training data and updates
        the ensemble weights based on their accuracy.
        
        Args:
            X (FeatureVector): Feature vectors for evaluation.
            y (np.ndarray): Target labels for evaluation.
        """
        # Evaluate SVM classifier
        svm_metrics = self.svm_classifier.evaluate(X, y)
        svm_accuracy = svm_metrics['accuracy']
        
        # Evaluate Random Forest classifier
        rf_metrics = self.rf_classifier.evaluate(X, y)
        rf_accuracy = rf_metrics['accuracy']
        
        # Calculate weights based on accuracy
        total_accuracy = svm_accuracy + rf_accuracy
        if total_accuracy > 0:
            self.ensemble_weights['svm'] = svm_accuracy / total_accuracy
            self.ensemble_weights['random_forest'] = rf_accuracy / total_accuracy
        
        logger.info(f"SVM accuracy: {svm_accuracy:.4f}, RF accuracy: {rf_accuracy:.4f}")
        logger.info(f"Updated ensemble weights: {self.ensemble_weights}")
    
    def predict(self, X: FeatureVector) -> np.ndarray:
        """
        Predict class labels for the provided data.
        
        This method combines predictions from the SVM and Random Forest classifiers
        using the ensemble weights to make the final prediction.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Predicted class labels.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained:
            raise RuntimeError("Model has not been trained. Call fit() before predict().")
        
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        # Get predictions from each classifier
        svm_predictions = self.svm_classifier.predict(X)
        rf_predictions = self.rf_classifier.predict(X)
        
        # Get probabilities from each classifier
        svm_probas = self.svm_classifier.predict_proba(X)
        rf_probas = self.rf_classifier.predict_proba(X)
        
        # Ensure consistent document type representation
        svm_predictions = self.ensure_consistent_document_types(svm_predictions)
        rf_predictions = self.ensure_consistent_document_types(rf_predictions)
        
        # Combine predictions using weighted voting
        final_predictions = []
        for i in range(len(X)):
            # Get the predicted class and its probability from each classifier
            svm_pred = svm_predictions[i]
            rf_pred = rf_predictions[i]
            
            # If both classifiers agree, use that prediction
            if svm_pred == rf_pred:
                final_predictions.append(svm_pred)
                continue
            
            # If classifiers disagree, use weighted probabilities
            svm_proba = svm_probas[i]
            rf_proba = rf_probas[i]
            
            # Combine probabilities using ensemble weights
            combined_proba = {}
            for j, cls in enumerate(self.classes_):
                # Ensure we're using the same class mapping for both classifiers
                svm_cls_proba = svm_proba[j] * self.ensemble_weights['svm']
                rf_cls_proba = rf_proba[j] * self.ensemble_weights['random_forest']
                combined_proba[cls] = svm_cls_proba + rf_cls_proba
            
            # Select the class with the highest combined probability
            final_pred = max(combined_proba.items(), key=lambda x: x[1])[0]
            final_predictions.append(final_pred)
        
        # Ensure all predictions are DocumentType instances
        return self.ensure_consistent_document_types(np.array(final_predictions))
    
    def predict_proba(self, X: FeatureVector) -> np.ndarray:
        """
        Predict class probabilities for the provided data.
        
        This method combines probability predictions from the SVM and Random Forest
        classifiers using the ensemble weights to make the final probability prediction.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Predicted class probabilities, where each row sums to 1.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained:
            raise RuntimeError("Model has not been trained. Call fit() before predict_proba().")
        
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        # Get probabilities from each classifier
        svm_probas = self.svm_classifier.predict_proba(X)
        rf_probas = self.rf_classifier.predict_proba(X)
        
        # Combine probabilities using ensemble weights
        combined_probas = []
        for i in range(len(X)):
            svm_proba = svm_probas[i]
            rf_proba = rf_probas[i]
            
            # Combine probabilities using ensemble weights
            combined_proba = svm_proba * self.ensemble_weights['svm'] + rf_proba * self.ensemble_weights['random_forest']
            
            # Normalize to ensure probabilities sum to 1
            combined_proba = combined_proba / np.sum(combined_proba)
            
            combined_probas.append(combined_proba)
        
        return np.array(combined_probas)
    
    def evaluate(self, X: FeatureVector, y: np.ndarray) -> ClassificationMetrics:
        """
        Evaluate the classifier on the provided data.
        
        This method evaluates the ensemble classifier's performance on the provided
        feature vectors and target labels, calculating metrics such as accuracy,
        precision, recall, and F1 score.
        
        Args:
            X (FeatureVector): Feature vectors for evaluation.
            y (np.ndarray): True target labels for evaluation.
            
        Returns:
            ClassificationMetrics: Dictionary of evaluation metrics including accuracy,
                precision, recall, F1 score, and confusion matrix.
                
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If evaluation fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained:
            raise RuntimeError("Model has not been trained. Call fit() before evaluate().")
        
        # Validate input data
        self._validate_input(X, y)
        
        # Get predictions
        start_time = time.time()
        y_pred = self.predict(X)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_recall_fscore_support, confusion_matrix
        
        accuracy = accuracy_score(y, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(y, y_pred, average=None)
        cm = confusion_matrix(y, y_pred)
        
        # Create metrics dictionaries
        precision_dict = {}
        recall_dict = {}
        f1_dict = {}
        
        for i, cls in enumerate(np.unique(y)):
            class_type = self._convert_to_document_type(cls)
            precision_dict[class_type] = float(precision[i])
            recall_dict[class_type] = float(recall[i])
            f1_dict[class_type] = float(f1[i])
        
        # Calculate evaluation time
        eval_time = time.time() - start_time
        
        # Create metrics object
        metrics = {
            'accuracy': float(accuracy),
            'precision': precision_dict,
            'recall': recall_dict,
            'f1_score': f1_dict,
            'confusion_matrix': cm.tolist(),
            'evaluation_time': eval_time
        }
        
        # Store metrics for later use
        self.metrics = metrics
        
        logger.info(f"Evaluation completed in {eval_time:.2f} seconds")
        logger.info(f"Accuracy: {accuracy:.4f}")
        
        return metrics
    
    def classify(self, features: FeatureVector) -> Tuple[DocumentType, Dict[str, float]]:
        """
        Classify a document based on its features.
        
        This is a high-level method that combines prediction and confidence scoring
        to classify a document and provide confidence scores for all possible types.
        
        Args:
            features (FeatureVector): Feature vector representing the document.
            
        Returns:
            Tuple containing the predicted document type and a dictionary of confidence
            scores for all document types.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If classification fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained:
            raise RuntimeError("Model has not been trained. Call fit() before classify().")
        
        # Validate input data
        self._validate_input(features, for_prediction=True)
        
        # Reshape features if needed (for single sample)
        if len(features.shape) == 1:
            features = features.reshape(1, -1)
        
        # Get prediction and probabilities
        start_time = time.time()
        prediction = self.predict(features)[0]
        probabilities = self.predict_proba(features)[0]
        
        # prediction should already be a DocumentType instance from predict()
        # but let's ensure it just to be safe
        if not isinstance(prediction, DocumentType):
            doc_type = self._convert_to_document_type(prediction)
        else:
            doc_type = prediction
        
        # Create confidence scores dictionary
        confidence_scores = {}
        for i, cls in enumerate(self.classes_):
            # Convert class to DocumentType if needed
            if not isinstance(cls, DocumentType):
                class_type = self._convert_to_document_type(cls)
            else:
                class_type = cls
                
            # Use the string value as the key in the confidence scores dictionary
            confidence_scores[str(class_type.value)] = float(probabilities[i])
        
        # Log classification time
        classification_time = time.time() - start_time
        logger.debug(f"Document classified as {doc_type} in {classification_time:.4f} seconds")
        
        return doc_type, confidence_scores
    
    def get_routing_info(self, document_type: DocumentType, confidence_scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Get routing information for OCR processing based on document type and confidence.
        
        This method determines the appropriate OCR processing strategy based on the
        document type, classification confidence, and document characteristics.
        
        Args:
            document_type (DocumentType): The classified document type.
            confidence_scores (Dict[str, float]): Confidence scores for all document types.
            
        Returns:
            Dict[str, Any]: Routing information for OCR processing.
        """
        # Get primary confidence score for the predicted type
        primary_confidence = confidence_scores.get(str(document_type.value), 0.0)
        
        # Determine if human review is required based on confidence threshold
        confidence_threshold = self.config.get('confidence_threshold', 0.7)
        requires_review = primary_confidence < confidence_threshold
        
        # Determine OCR processor based on document type
        ocr_processor = self._get_ocr_processor_for_type(document_type)
        
        # Determine processing priority based on confidence
        if primary_confidence > 0.9:
            priority = "high"
        elif primary_confidence > 0.7:
            priority = "medium"
        else:
            priority = "low"
        
        # Create routing information
        routing_info = {
            "document_type": str(document_type.value),
            "ocr_processor": ocr_processor,
            "confidence": primary_confidence,
            "requires_review": requires_review,
            "processing_priority": priority,
            "routing_timestamp": datetime.now().isoformat(),
            "routing_version": self.model_version
        }
        
        logger.info(f"Document routed to {ocr_processor} processor with {priority} priority")
        if requires_review:
            logger.info(f"Document requires human review due to low confidence ({primary_confidence:.2f})")
        
        return routing_info
    
    def _get_ocr_processor_for_type(self, document_type: DocumentType) -> str:
        """
        Determine the appropriate OCR processor for a document type.
        
        Args:
            document_type (DocumentType): The document type to route.
            
        Returns:
            str: Name of the OCR processor to use.
        """
        # Define OCR processor mapping based on document type
        processor_mapping = {
            DocumentType.APPLICATION: "form_processor",
            DocumentType.TAX_RETURN: "financial_processor",
            DocumentType.BANK_STATEMENT: "financial_processor",
            DocumentType.PAY_STUB: "financial_processor",
            DocumentType.ID_DOCUMENT: "id_processor",
            DocumentType.OTHER: "general_processor"
        }
        
        # Get processor for the document type, defaulting to general processor
        return processor_mapping.get(document_type, "general_processor")
    
    def get_feature_importance(self) -> Dict[str, Dict[str, float]]:
        """
        Get feature importance rankings from all classifiers.
        
        Returns:
            Dict[str, Dict[str, float]]: Dictionary mapping classifier names to
            feature importance dictionaries.
            
        Raises:
            RuntimeError: If the model has not been trained.
        """
        if not self.trained:
            raise RuntimeError("Model has not been trained. Call fit() before get_feature_importance().")
        
        # Get feature importance from each classifier
        svm_importance = self.svm_classifier.get_feature_importance()
        rf_importance = self.rf_classifier.get_feature_importance()
        
        # Combine feature importance from all classifiers
        importance = {
            'svm': svm_importance,
            'random_forest': rf_importance
        }
        
        return importance
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for monitoring.
        
        Returns:
            Dict[str, Any]: Dictionary of performance metrics.
            
        Raises:
            RuntimeError: If the model has not been evaluated.
        """
        if not self.metrics:
            logger.warning("Model has not been evaluated. Call evaluate() to get performance metrics.")
            return {}
        
        return self.metrics
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the classifier.
        
        Returns:
            Dict[str, Any]: Dictionary with classifier information.
        """
        info = {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "ensemble_weights": self.ensemble_weights,
            "trained": self.trained,
            "component_models": {
                "svm": self.svm_classifier.get_model_info(),
                "random_forest": self.rf_classifier.get_model_info()
            },
            "config": self.config
        }
        
        # Add performance metrics if available
        if self.metrics:
            info["performance_metrics"] = self.metrics
        
        return info
        
    def ensure_consistent_document_types(self, predictions: np.ndarray) -> np.ndarray:
        """
        Ensure all predictions are converted to DocumentType instances consistently.
        
        This method ensures that all predictions are properly converted to DocumentType
        instances using the _convert_to_document_type method, which handles different
        input formats (string, int, enum).
        
        Args:
            predictions (np.ndarray): Array of predictions that may be of different types.
            
        Returns:
            np.ndarray: Array of DocumentType instances.
        """
        # Convert each prediction to a DocumentType instance
        converted_predictions = []
        for pred in predictions:
            # Skip if already a DocumentType
            if isinstance(pred, DocumentType):
                converted_predictions.append(pred)
            else:
                # Convert to DocumentType using the base method
                doc_type = self._convert_to_document_type(pred)
                converted_predictions.append(doc_type)
        
        return np.array(converted_predictions)
        
    def save_ensemble(self, base_path: str) -> Result[Dict[str, str]]:
        """
        Save the ensemble classifier and its component models to disk.
        
        Args:
            base_path (str): Base path where models should be saved.
            
        Returns:
            Result[Dict[str, str]]: Success result with paths where models were saved,
                or error result if saving failed.
        """
        if not self.trained:
            return Result.failure("Model has not been trained. Call fit() before saving.")
        
        try:
            import os
            import json
            
            # Create directory if it doesn't exist
            os.makedirs(base_path, exist_ok=True)
            
            # Save component models
            svm_path = os.path.join(base_path, "svm_classifier.pkl")
            rf_path = os.path.join(base_path, "rf_classifier.pkl")
            
            svm_result = self.svm_classifier.save(svm_path)
            if not svm_result.success:
                return Result.failure(f"Failed to save SVM classifier: {svm_result.error}")
                
            rf_result = self.rf_classifier.save(rf_path)
            if not rf_result.success:
                return Result.failure(f"Failed to save Random Forest classifier: {rf_result.error}")
            
            # Save ensemble metadata
            metadata = {
                "model_name": self.model_name,
                "model_version": self.model_version,
                "ensemble_weights": self.ensemble_weights,
                "config": self.config,
                "classes": [str(cls) for cls in self.classes_] if self.classes_ is not None else None,
                "feature_names": self.feature_names,
                "metrics": self.metrics,
                "trained": self.trained,
                "component_models": {
                    "svm": svm_path,
                    "random_forest": rf_path
                }
            }
            
            metadata_path = os.path.join(base_path, "ensemble_metadata.json")
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Save the ensemble model using the parent class method
            ensemble_path = os.path.join(base_path, "document_classifier.pkl")
            ensemble_result = super().save(ensemble_path)
            if not ensemble_result.success:
                return Result.failure(f"Failed to save ensemble model: {ensemble_result.error}")
            
            logger.info(f"Ensemble model saved to {base_path}")
            return Result.success({
                "ensemble": ensemble_path,
                "svm": svm_path,
                "random_forest": rf_path,
                "metadata": metadata_path
            })
        except Exception as e:
            error_msg = f"Failed to save ensemble model: {str(e)}"
            logger.error(error_msg)
            return Result.failure(error_msg)
    
    @classmethod
    def load_ensemble(cls, base_path: str) -> Result['DocumentClassifier']:
        """
        Load an ensemble classifier and its component models from disk.
        
        Args:
            base_path (str): Base path from which to load models.
            
        Returns:
            Result['DocumentClassifier']: Success result with the loaded model instance,
                or error result if loading failed.
        """
        try:
            import os
            import json
            
            # Load ensemble metadata
            metadata_path = os.path.join(base_path, "ensemble_metadata.json")
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Create a new instance with the saved configuration
            instance = cls(metadata["config"])
            
            # Load component models
            svm_path = metadata["component_models"]["svm"]
            rf_path = metadata["component_models"]["random_forest"]
            
            svm_result = SVMClassifier.load(svm_path)
            if not svm_result.success:
                return Result.failure(f"Failed to load SVM classifier: {svm_result.error}")
                
            rf_result = RandomForestClassifier.load(rf_path)
            if not rf_result.success:
                return Result.failure(f"Failed to load Random Forest classifier: {rf_result.error}")
            
            # Set component models
            instance.svm_classifier = svm_result.value
            instance.rf_classifier = rf_result.value
            
            # Restore ensemble attributes
            instance.model_name = metadata["model_name"]
            instance.model_version = metadata["model_version"]
            instance.ensemble_weights = metadata["ensemble_weights"]
            instance.metrics = metadata["metrics"]
            instance.trained = metadata["trained"]
            
            # Restore class labels and feature names
            if metadata["classes"] is not None:
                instance.classes_ = np.array([DocumentType(cls) for cls in metadata["classes"]])
            instance.feature_names = metadata["feature_names"]
            
            logger.info(f"Ensemble model loaded from {base_path}")
            return Result.success(instance)
        except Exception as e:
            error_msg = f"Failed to load ensemble model: {str(e)}"
            logger.error(error_msg)
            return Result.failure(error_msg)