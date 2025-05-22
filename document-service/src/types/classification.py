#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Type definitions for document classification models, features, and results.

This module provides type hints for the scikit-learn classification pipeline,
feature extraction, and confidence scoring used in the Document Service.

These types ensure consistent interfaces across the classification system
and provide type safety for the core classification functionality.
"""

from typing import Any, Dict, List, Tuple, Union, Optional, TypeVar, Protocol, Callable
from typing import TypedDict, Literal, NamedTuple
import numpy as np
from numpy.typing import NDArray
from enum import Enum, auto

# Type aliases for basic classification components
FeatureVector = NDArray[np.float64]  # Feature vector representation of a document
FeatureMatrix = NDArray[np.float64]  # Matrix of feature vectors (n_samples, n_features)
ProbabilityVector = NDArray[np.float64]  # Probability vector for class predictions
LabelVector = NDArray[np.int32]  # Vector of class labels

# Type for confidence scores (0.0 to 1.0)
ConfidenceScore = float  # Must be between 0.0 and 1.0

# Document types that can be classified
class DocumentType(Enum):
    """Enumeration of document types that can be classified by the system."""
    LOAN_APPLICATION = auto()
    TAX_RETURN = auto()
    BANK_STATEMENT = auto()
    PAY_STUB = auto()
    IDENTITY_DOCUMENT = auto()
    BUSINESS_LICENSE = auto()
    UTILITY_BILL = auto()
    INSURANCE_DOCUMENT = auto()
    OTHER = auto()


class ModelParameters(TypedDict, total=False):
    """Type for model configuration and hyperparameters.
    
    This type allows for flexible parameter specification while maintaining
    type safety for common hyperparameters used in scikit-learn models.
    """
    # Common parameters
    random_state: int
    n_jobs: int
    verbose: bool
    
    # SVM specific parameters
    C: float
    kernel: Literal['linear', 'poly', 'rbf', 'sigmoid']
    gamma: Union[float, Literal['scale', 'auto']]
    degree: int
    coef0: float
    probability: bool
    
    # Random Forest specific parameters
    n_estimators: int
    criterion: Literal['gini', 'entropy', 'log_loss']
    max_depth: Optional[int]
    min_samples_split: Union[int, float]
    min_samples_leaf: Union[int, float]
    max_features: Union[int, float, Literal['sqrt', 'log2']]
    bootstrap: bool
    oob_score: bool
    class_weight: Union[Dict[int, float], Literal['balanced', 'balanced_subsample']]


class ClassificationResult(NamedTuple):
    """Result of a document classification operation.
    
    Contains the predicted document type, confidence score, and additional metadata
    about the classification decision.
    """
    document_type: DocumentType
    confidence: ConfidenceScore
    probabilities: Dict[DocumentType, ConfidenceScore]  # Probabilities for all classes
    needs_review: bool  # True if confidence is below threshold (default 0.75)
    feature_importance: Optional[Dict[str, float]] = None  # Feature importance if available
    processing_time_ms: Optional[float] = None  # Classification processing time in milliseconds


class ClassificationMetrics(TypedDict):
    """Metrics for evaluating classification model performance.
    
    These metrics are used to evaluate and compare model performance during
    training, validation, and monitoring.
    """
    accuracy: float  # Overall accuracy (must be >= 0.99 for production use)
    precision: Dict[DocumentType, float]  # Precision per class
    recall: Dict[DocumentType, float]  # Recall per class
    f1_score: Dict[DocumentType, float]  # F1 score per class
    confusion_matrix: List[List[int]]  # Confusion matrix as nested list
    support: Dict[DocumentType, int]  # Number of samples per class
    roc_auc: Optional[Dict[DocumentType, float]]  # ROC AUC per class (if available)
    average_confidence: float  # Average confidence score across all predictions


class ClassificationModel(Protocol):
    """Protocol defining the interface for classification models.
    
    All document classification models must implement this interface to ensure
    consistent usage across the system. This includes scikit-learn models and
    custom implementations.
    """
    def fit(self, X: FeatureMatrix, y: LabelVector) -> Any:
        """Train the model on the given feature matrix and labels.
        
        Args:
            X: Feature matrix of shape (n_samples, n_features)
            y: Label vector of shape (n_samples,)
            
        Returns:
            The trained model instance
        """
        ...
    
    def predict(self, X: FeatureMatrix) -> LabelVector:
        """Predict class labels for the given feature matrix.
        
        Args:
            X: Feature matrix of shape (n_samples, n_features)
            
        Returns:
            Predicted class labels of shape (n_samples,)
        """
        ...
    
    def predict_proba(self, X: FeatureMatrix) -> NDArray[np.float64]:
        """Predict class probabilities for the given feature matrix.
        
        Args:
            X: Feature matrix of shape (n_samples, n_features)
            
        Returns:
            Class probabilities of shape (n_samples, n_classes)
        """
        ...
    
    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Get parameters for this model.
        
        Args:
            deep: If True, return the parameters of all sub-objects
            
        Returns:
            Parameter names mapped to their values
        """
        ...
    
    def set_params(self, **params: Any) -> Any:
        """Set the parameters of this model.
        
        Args:
            **params: Model parameters to set
            
        Returns:
            The model instance
        """
        ...


# Type for feature extraction functions
FeatureExtractor = Callable[[Any], FeatureVector]

# Type for model serialization
SerializedModel = bytes

# Type for model version information
class ModelVersion(TypedDict):
    """Version information for a trained classification model.
    
    Used for model tracking, versioning, and auditing.
    """
    model_id: str  # Unique identifier for the model
    version: str  # Semantic version (e.g., "1.0.0")
    trained_at: str  # ISO format timestamp
    accuracy: float  # Validation accuracy
    parameters: ModelParameters  # Model hyperparameters
    feature_count: int  # Number of features
    class_distribution: Dict[DocumentType, int]  # Training class distribution
    description: str  # Human-readable description
    created_by: str  # User or process that created the model