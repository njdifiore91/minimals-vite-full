#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Abstract base class for document classifiers in the Document Service.

This module defines the common interface that all document classifier implementations
must follow, including methods for training, prediction, evaluation, and serialization.
It establishes a consistent API for all classifiers to ensure interoperability and
standardized behavior throughout the document classification pipeline.

Classes:
    BaseModel: Abstract base class for document classifiers.

Example:
    ```python
    class SVMClassifier(BaseModel):
        def __init__(self, config: ModelConfig):
            super().__init__(config)
            # SVM-specific initialization
            
        def fit(self, X: FeatureVector, y: np.ndarray) -> 'SVMClassifier':
            # SVM-specific training implementation
            return self
            
        def predict(self, X: FeatureVector) -> np.ndarray:
            # SVM-specific prediction implementation
            return predictions
            
        def predict_proba(self, X: FeatureVector) -> np.ndarray:
            # SVM-specific probability prediction implementation
            return probabilities
            
        def evaluate(self, X: FeatureVector, y: np.ndarray) -> ClassificationMetrics:
            # SVM-specific evaluation implementation
            return metrics
    ```
"""

from abc import ABC, abstractmethod
import logging
import numpy as np
import os
import pickle
import time
from typing import Any, Dict, List, Optional, Tuple, Union, TypeVar, Generic, cast

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

# Type variable for the implementing class to enable method chaining
T = TypeVar('T', bound='BaseModel')

logger = logging.getLogger(__name__)


class BaseModel(ABC, Generic[T]):
    """
    Abstract base class for all document classifiers in the Document Service.
    
    This class defines the common interface that all classifier implementations must follow,
    including methods for training, prediction, evaluation, and serialization. It also
    provides common utility methods for all classifiers.
    
    All document classifiers must extend this class and implement its abstract methods.
    
    Attributes:
        config (ModelConfig): Configuration parameters for the model.
        model (Optional[ClassificationModel]): The underlying scikit-learn model instance.
        model_name (str): Name of the model for identification and logging.
        model_version (str): Version of the model for tracking and compatibility.
        classes_ (Optional[np.ndarray]): Array of class labels known to the classifier.
        trained (bool): Flag indicating whether the model has been trained.
        feature_names (Optional[List[str]]): Names of features used by the model.
    """
    
    def __init__(self, config: ModelConfig):
        """
        Initialize the base model with configuration parameters.
        
        Args:
            config (ModelConfig): Configuration parameters for the model.
        """
        self.config = config
        self.model: Optional[ClassificationModel] = None
        self.model_name: str = self.__class__.__name__
        self.model_version: str = config.get('version', '1.0.0')
        self.classes_: Optional[np.ndarray] = None
        self.trained: bool = False
        self.feature_names: Optional[List[str]] = None
        
        logger.info(f"Initialized {self.model_name} v{self.model_version}")
    
    @abstractmethod
    def fit(self, X: FeatureVector, y: np.ndarray) -> T:
        """
        Train the model on the provided data.
        
        This method must be implemented by all subclasses to train the underlying
        classification model on the provided feature vectors and target labels.
        
        Args:
            X (FeatureVector): Feature vectors for training.
            y (np.ndarray): Target labels for training.
            
        Returns:
            T: The trained model instance (self) for method chaining.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If training fails due to internal errors.
        """
        pass
    
    @abstractmethod
    def predict(self, X: FeatureVector) -> np.ndarray:
        """
        Predict class labels for the provided data.
        
        This method must be implemented by all subclasses to predict class labels
        for the provided feature vectors using the trained model.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Predicted class labels.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        pass
    
    @abstractmethod
    def predict_proba(self, X: FeatureVector) -> np.ndarray:
        """
        Predict class probabilities for the provided data.
        
        This method must be implemented by all subclasses to predict class probabilities
        for the provided feature vectors using the trained model.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            np.ndarray: Predicted class probabilities, where each row sums to 1.
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        pass
    
    @abstractmethod
    def evaluate(self, X: FeatureVector, y: np.ndarray) -> ClassificationMetrics:
        """
        Evaluate the model on the provided data.
        
        This method must be implemented by all subclasses to evaluate the model's
        performance on the provided feature vectors and target labels.
        
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
        pass
    
    def predict_with_confidence(self, X: FeatureVector) -> List[ClassificationResult]:
        """
        Predict class labels with confidence scores for the provided data.
        
        This method combines predict() and predict_proba() to provide both class labels
        and confidence scores for the predictions.
        
        Args:
            X (FeatureVector): Feature vectors for prediction.
            
        Returns:
            List[ClassificationResult]: List of classification results with document types
                and confidence scores.
                
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
            RuntimeError: If prediction fails due to internal errors.
            RuntimeError: If the model has not been trained.
        """
        if not self.trained or self.model is None or self.classes_ is None:
            raise RuntimeError("Model has not been trained. Call fit() before prediction.")
        
        # Validate input data
        self._validate_input(X, for_prediction=True)
        
        # Get predictions and probabilities
        predictions = self.predict(X)
        probabilities = self.predict_proba(X)
        
        results: List[ClassificationResult] = []
        
        # Create classification results with confidence scores
        for i, (pred, probs) in enumerate(zip(predictions, probabilities)):
            # Get the predicted class and its probability
            pred_idx = np.where(self.classes_ == pred)[0][0]
            confidence = float(probs[pred_idx])
            
            # Convert numeric/string class to DocumentType
            doc_type = self._convert_to_document_type(pred)
            
            # Create confidence score object
            confidence_score = ConfidenceScore(
                value=confidence,
                threshold=self.config.get('confidence_threshold', 0.7),
                requires_review=confidence < self.config.get('confidence_threshold', 0.7)
            )
            
            # Create classification result
            result = ClassificationResult(
                document_type=doc_type,
                confidence=confidence_score,
                model_name=self.model_name,
                model_version=self.model_version,
                prediction_time=time.time(),
                class_probabilities={str(self.classes_[j]): float(p) for j, p in enumerate(probs)}
            )
            
            results.append(result)
        
        return results
    
    def save(self, path: str) -> Result[str]:
        """
        Save the trained model to disk.
        
        Args:
            path (str): Path where the model should be saved.
            
        Returns:
            Result[str]: Success result with the path where the model was saved,
                or error result if saving failed.
        """
        if not self.trained or self.model is None:
            return Result.failure("Model has not been trained. Call fit() before saving.")
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(path), exist_ok=True)
            
            # Prepare model data for serialization
            model_data = {
                'model': self.model,
                'model_name': self.model_name,
                'model_version': self.model_version,
                'classes_': self.classes_,
                'feature_names': self.feature_names,
                'config': self.config,
                'trained': self.trained
            }
            
            # Save the model to disk
            with open(path, 'wb') as f:
                pickle.dump(model_data, f)
            
            logger.info(f"Model {self.model_name} v{self.model_version} saved to {path}")
            return Result.success(path)
        except Exception as e:
            error_msg = f"Failed to save model {self.model_name} to {path}: {str(e)}"
            logger.error(error_msg)
            return Result.failure(error_msg)
    
    @classmethod
    def load(cls, path: str) -> Result[T]:
        """
        Load a trained model from disk.
        
        Args:
            path (str): Path from which to load the model.
            
        Returns:
            Result[T]: Success result with the loaded model instance,
                or error result if loading failed.
        """
        try:
            # Load the model from disk
            with open(path, 'rb') as f:
                model_data = pickle.load(f)
            
            # Create a new instance of the model
            instance = cls(model_data['config'])
            
            # Restore model attributes
            instance.model = model_data['model']
            instance.model_name = model_data['model_name']
            instance.model_version = model_data['model_version']
            instance.classes_ = model_data['classes_']
            instance.feature_names = model_data['feature_names']
            instance.trained = model_data['trained']
            
            logger.info(f"Model {instance.model_name} v{instance.model_version} loaded from {path}")
            return Result.success(cast(T, instance))
        except Exception as e:
            error_msg = f"Failed to load model from {path}: {str(e)}"
            logger.error(error_msg)
            return Result.failure(error_msg)
    
    def get_parameters(self) -> ModelParameters:
        """
        Get the model parameters.
        
        Returns:
            ModelParameters: Dictionary of model parameters.
        """
        if self.model is None:
            return {}
        
        # Get model parameters
        params = getattr(self.model, 'get_params', lambda: {})() 
        
        # Add additional metadata
        params.update({
            'model_name': self.model_name,
            'model_version': self.model_version,
            'trained': self.trained,
            'n_features': len(self.feature_names) if self.feature_names else 0,
            'n_classes': len(self.classes_) if self.classes_ else 0
        })
        
        return params
    
    def _validate_input(self, X: FeatureVector, y: Optional[np.ndarray] = None, 
                       for_prediction: bool = False) -> None:
        """
        Validate input data for training or prediction.
        
        Args:
            X (FeatureVector): Feature vectors to validate.
            y (Optional[np.ndarray]): Target labels to validate (for training).
            for_prediction (bool): Whether validation is for prediction (True) or training (False).
            
        Raises:
            ValueError: If input data is invalid or incompatible with the model.
        """
        # Check if X is not None
        if X is None:
            raise ValueError("Feature vectors (X) cannot be None")
        
        # Check if X has the expected shape
        if not hasattr(X, 'shape') or len(getattr(X, 'shape', ())) != 2:
            raise ValueError("Feature vectors (X) must be a 2D array-like object")
        
        # For training, validate y as well
        if not for_prediction:
            if y is None:
                raise ValueError("Target labels (y) cannot be None for training")
            
            if len(y) != X.shape[0]:
                raise ValueError(f"Number of samples in X ({X.shape[0]}) and y ({len(y)}) do not match")
        
        # For prediction, check if model is trained
        if for_prediction and (not self.trained or self.model is None):
            raise RuntimeError("Model has not been trained. Call fit() before prediction.")
    
    def _convert_to_document_type(self, class_label: Any) -> DocumentType:
        """
        Convert a class label to a DocumentType enum value.
        
        Args:
            class_label (Any): Class label to convert.
            
        Returns:
            DocumentType: Corresponding DocumentType enum value.
            
        Raises:
            ValueError: If the class label cannot be converted to a DocumentType.
        """
        # If class_label is already a DocumentType, return it
        if isinstance(class_label, DocumentType):
            return class_label
        
        # Try to convert string or int to DocumentType
        try:
            if isinstance(class_label, str):
                return DocumentType[class_label.upper()]
            elif isinstance(class_label, (int, np.integer)):
                return DocumentType(class_label)
            else:
                # Try string conversion as a fallback
                return DocumentType[str(class_label).upper()]
        except (KeyError, ValueError):
            # If conversion fails, default to OTHER
            logger.warning(f"Could not convert class label '{class_label}' to DocumentType. Using OTHER.")
            return DocumentType.OTHER