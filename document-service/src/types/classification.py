"""
Type definitions for document classification models, features, and results.

This module provides type definitions for the scikit-learn classification pipeline,
feature extraction, and confidence scoring used by the Document Service.

The Document Service uses scikit-learn 1.4.1 for document classification with a
target accuracy of 99%. Classification confidence thresholds determine whether
documents are automatically processed or flagged for human review.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Literal, Optional, Protocol, Tuple, TypeVar, Union

import numpy as np
import numpy.typing as npt
from sklearn.base import BaseEstimator

# Type variable for generic types
T = TypeVar('T')

# Type alias for feature vectors (document features)
FeatureVector = npt.NDArray[np.float64]

# Type alias for feature names
FeatureNames = List[str]

# Type alias for confidence scores (0.0 to 1.0)
ConfidenceScore = float

# Type alias for model parameters dictionary
ModelParameters = Dict[str, Any]


class DocumentType(enum.Enum):
    """Enumeration of document types for classification.
    
    This enum represents the different types of documents that can be classified
    by the Document Service.
    """
    APPLICATION = "application"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    PAY_STUB = "pay_stub"
    ID_DOCUMENT = "id_document"
    OTHER = "other"


class ClassificationModel(Protocol):
    """Protocol defining the interface for classification models.
    
    This protocol defines the methods that must be implemented by any
    classification model used in the Document Service. It follows the
    scikit-learn estimator interface.
    """
    
    def fit(self, X: FeatureVector, y: npt.ArrayLike) -> Any:
        """Fit the model to the training data.
        
        Args:
            X: Feature vectors for training
            y: Target labels for training
            
        Returns:
            The fitted model
        """
        ...
    
    def predict(self, X: FeatureVector) -> npt.NDArray[np.int_]:
        """Predict class labels for samples in X.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Predicted class labels
        """
        ...
    
    def predict_proba(self, X: FeatureVector) -> npt.NDArray[np.float64]:
        """Predict class probabilities for samples in X.
        
        Args:
            X: Feature vectors to predict
            
        Returns:
            Class probabilities for each sample
        """
        ...


@dataclass
class ClassificationResult:
    """Result of a document classification operation.
    
    This class represents the result of classifying a document, including the
    predicted document type, confidence score, and whether human review is required.
    """
    document_id: str
    document_type: DocumentType
    confidence: ConfidenceScore
    requires_review: bool = False
    prediction_time: datetime = field(default_factory=datetime.now)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self) -> None:
        """Validate the classification result after initialization."""
        # Ensure confidence is between 0.0 and 1.0
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"Confidence score must be between 0.0 and 1.0"
            )
        
        # Set requires_review flag based on confidence threshold (75%)
        if self.confidence < 0.75:
            self.requires_review = True


@dataclass
class FeatureExtractor:
    """Feature extractor for document classification.
    
    This class represents a feature extractor that extracts features from
    document content for classification.
    """
    
    name: str
    extract_fn: Callable[[bytes], FeatureVector]
    feature_names: FeatureNames
    
    def extract(self, document_content: bytes) -> FeatureVector:
        """Extract features from document content.
        
        Args:
            document_content: Binary content of the document
            
        Returns:
            Feature vector extracted from the document
        """
        return self.extract_fn(document_content)


@dataclass
class ClassificationMetrics:
    """Metrics for evaluating classification model performance.
    
    This class represents metrics used to evaluate the performance of a
    classification model, including accuracy, precision, recall, and F1 score.
    """
    
    accuracy: float
    precision: Dict[Union[DocumentType, str], float]
    recall: Dict[Union[DocumentType, str], float]
    f1_score: Dict[Union[DocumentType, str], float]
    confusion_matrix: Optional[npt.NDArray[np.int_]] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self) -> None:
        """Validate the metrics after initialization."""
        # Ensure accuracy is between 0.0 and 1.0
        if not 0.0 <= self.accuracy <= 1.0:
            raise ValueError(
                f"Accuracy must be between 0.0 and 1.0"
            )


@dataclass
class ModelConfig:
    """Configuration for a classification model.
    
    This class represents the configuration for a classification model,
    including the model type, parameters, and feature extractors.
    """
    
    model_type: str
    parameters: ModelParameters
    feature_extractors: List[FeatureExtractor]
    confidence_threshold: float = 0.75
    version: str = '1.0.0'
    description: str = ''
    
    def __post_init__(self) -> None:
        """Validate the model configuration after initialization."""
        # Ensure confidence threshold is between 0.0 and 1.0
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"Confidence threshold must be between 0.0 and 1.0"
            )


class ClassifierFactory:
    """Factory for creating classification models.
    
    This class is responsible for creating and configuring classification models
    based on the provided configuration.
    """
    
    @staticmethod
    def create_model(config: ModelConfig) -> ClassificationModel:
        """Create a classification model based on the provided configuration.
        
        Args:
            config: Model configuration
            
        Returns:
            Configured classification model
            
        Raises:
            ValueError: If the model type is not supported
        """
        if config.model_type == "svm":
            from sklearn.svm import SVC
            return SVC(probability=True, **config.parameters)
        elif config.model_type == "random_forest":
            from sklearn.ensemble import RandomForestClassifier
            return RandomForestClassifier(**config.parameters)
        elif config.model_type == "gradient_boosting":
            from sklearn.ensemble import GradientBoostingClassifier
            return GradientBoostingClassifier(**config.parameters)
        else:
            raise ValueError(f"Unsupported model type: {config.model_type}")"