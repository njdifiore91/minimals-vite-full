#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Classification Service for Document Service Microservice

This module orchestrates the document classification process, coordinating feature extraction,
model selection, classification, and confidence scoring to determine document types with 99% accuracy.

The service is responsible for:
1. Extracting features from documents
2. Selecting and applying appropriate classification models
3. Determining document types with confidence scores
4. Formatting classification results for downstream services
5. Monitoring and logging classification performance

Typical usage example:
    classification_service = ClassificationService()
    classification_result = classification_service.classify_document(document_data)
"""

import logging
import time
from typing import Dict, Any, List, Optional, Tuple, Union
import os
import json

# Import models
from models import DocumentClassifier
from models.feature_extraction import extract_features

# Import types
from types.classification import ClassificationResult, FeatureVector, ConfidenceScore
from types.storage import StorageMetadata

# Import configuration
from config import model_config, app_config

# Import utilities
from utils.ml_utils import calculate_confidence_metrics
from utils.validation_utils import validate_document_format


class ClassificationService:
    """
    Service for classifying documents using machine learning models.
    
    This service orchestrates the document classification process, including feature extraction,
    model selection, classification, and confidence scoring. It provides a high-level interface
    for document classification that can be used by other components of the Document Service.
    
    Attributes:
        classifier (DocumentClassifier): The document classifier instance.
        logger (logging.Logger): Logger for the classification service.
        confidence_threshold (float): Minimum confidence threshold for classification.
        document_types (List[str]): List of supported document types.
    """
    
    def __init__(self):
        """
        Initializes the ClassificationService with configured models and settings.
        
        Loads the document classifier, configures logging, and sets up classification parameters
        from the application configuration.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ClassificationService")
        
        # Load classifier from models package
        self.classifier = DocumentClassifier()
        
        # Load configuration settings
        self.confidence_threshold = model_config.CLASSIFICATION_CONFIDENCE_THRESHOLD
        self.document_types = model_config.DOCUMENT_TYPES
        self.enable_performance_metrics = app_config.ENABLE_PERFORMANCE_METRICS
        
        # Initialize performance metrics
        self.classification_metrics = {
            "total_documents": 0,
            "successful_classifications": 0,
            "low_confidence_classifications": 0,
            "failed_classifications": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0
        }
        
        self.logger.info(f"ClassificationService initialized with {len(self.document_types)} document types")
        self.logger.info(f"Confidence threshold set to {self.confidence_threshold}")
    
    def classify_document(self, document_data: bytes, document_metadata: Dict[str, Any] = None) -> ClassificationResult:
        """
        Classifies a document based on its content and metadata.
        
        Args:
            document_data: Binary content of the document to classify.
            document_metadata: Optional metadata about the document (file type, size, etc.).
            
        Returns:
            A ClassificationResult containing the document type, confidence score, and metadata.
            
        Raises:
            ValueError: If the document format is invalid or unsupported.
            RuntimeError: If classification fails due to model errors.
        """
        start_time = time.time()
        self.classification_metrics["total_documents"] += 1
        
        if document_metadata is None:
            document_metadata = {}
        
        try:
            # Validate document format
            self.logger.debug("Validating document format")
            validate_document_format(document_data, document_metadata)
            
            # Extract features from document
            self.logger.debug("Extracting features from document")
            features = self._extract_document_features(document_data, document_metadata)
            
            # Classify document using extracted features
            self.logger.debug("Classifying document")
            document_type, confidence_scores = self._perform_classification(features)
            
            # Create classification result
            result = self._create_classification_result(
                document_type, 
                confidence_scores, 
                document_metadata,
                features
            )
            
            # Update performance metrics
            processing_time = time.time() - start_time
            self._update_performance_metrics(result, processing_time)
            
            self.logger.info(
                f"Document classified as '{document_type}' with confidence {result['confidence_score']:.2f}"
            )
            return result
            
        except ValueError as e:
            self.logger.error(f"Invalid document format: {str(e)}")
            self.classification_metrics["failed_classifications"] += 1
            raise
        except Exception as e:
            self.logger.error(f"Classification failed: {str(e)}")
            self.classification_metrics["failed_classifications"] += 1
            raise RuntimeError(f"Document classification failed: {str(e)}")
    
    def _extract_document_features(self, document_data: bytes, metadata: Dict[str, Any]) -> FeatureVector:
        """
        Extracts features from a document for classification.
        
        Args:
            document_data: Binary content of the document.
            metadata: Metadata about the document.
            
        Returns:
            A feature vector representing the document.
            
        Raises:
            ValueError: If feature extraction fails.
        """
        try:
            # Use feature extraction from models package
            features = extract_features(document_data, metadata)
            return features
        except Exception as e:
            self.logger.error(f"Feature extraction failed: {str(e)}")
            raise ValueError(f"Feature extraction failed: {str(e)}")
    
    def _perform_classification(self, features: FeatureVector) -> Tuple[str, Dict[str, float]]:
        """
        Performs document classification using the document classifier.
        
        Args:
            features: Feature vector representing the document.
            
        Returns:
            A tuple containing the document type and confidence scores for all types.
            
        Raises:
            RuntimeError: If classification fails.
        """
        try:
            # Use classifier from models package
            document_type, confidence_scores = self.classifier.classify(features)
            return document_type, confidence_scores
        except Exception as e:
            self.logger.error(f"Classification failed: {str(e)}")
            raise RuntimeError(f"Classification failed: {str(e)}")
    
    def _create_classification_result(self, 
                                     document_type: str, 
                                     confidence_scores: Dict[str, float],
                                     metadata: Dict[str, Any],
                                     features: FeatureVector) -> ClassificationResult:
        """
        Creates a structured classification result with confidence metrics.
        
        Args:
            document_type: The classified document type.
            confidence_scores: Confidence scores for all document types.
            metadata: Original document metadata.
            features: Feature vector used for classification.
            
        Returns:
            A ClassificationResult containing the document type, confidence score, and metadata.
        """
        # Calculate additional confidence metrics
        confidence_metrics = calculate_confidence_metrics(confidence_scores, document_type)
        
        # Determine if classification requires human review
        requires_review = confidence_metrics["primary_confidence"] < self.confidence_threshold
        
        # Create storage metadata for downstream services
        storage_metadata = self._create_storage_metadata(
            document_type, 
            confidence_metrics,
            requires_review,
            metadata
        )
        
        # Create the classification result
        result = {
            "document_type": document_type,
            "confidence_score": confidence_metrics["primary_confidence"],
            "confidence_metrics": confidence_metrics,
            "requires_review": requires_review,
            "all_scores": confidence_scores,
            "metadata": metadata,
            "storage_metadata": storage_metadata,
            "feature_summary": self._summarize_features(features)
        }
        
        return result
    
    def _create_storage_metadata(self, 
                               document_type: str, 
                               confidence_metrics: Dict[str, float],
                               requires_review: bool,
                               original_metadata: Dict[str, Any]) -> StorageMetadata:
        """
        Creates storage metadata for the classified document.
        
        Args:
            document_type: The classified document type.
            confidence_metrics: Confidence metrics for the classification.
            requires_review: Whether the document requires human review.
            original_metadata: Original document metadata.
            
        Returns:
            StorageMetadata for the document.
        """
        # Create metadata for storage
        storage_metadata = {
            "document_type": document_type,
            "classification_confidence": confidence_metrics["primary_confidence"],
            "classification_timestamp": time.time(),
            "classification_version": model_config.MODEL_VERSION,
            "requires_human_review": requires_review,
            "service_version": app_config.SERVICE_VERSION,
        }
        
        # Add original metadata fields that are relevant for storage
        if "content_type" in original_metadata:
            storage_metadata["content_type"] = original_metadata["content_type"]
        if "file_name" in original_metadata:
            storage_metadata["file_name"] = original_metadata["file_name"]
        if "file_size" in original_metadata:
            storage_metadata["file_size"] = original_metadata["file_size"]
        
        return storage_metadata
    
    def _summarize_features(self, features: FeatureVector) -> Dict[str, Any]:
        """
        Creates a summary of the feature vector for logging and debugging.
        
        Args:
            features: The feature vector used for classification.
            
        Returns:
            A dictionary containing a summary of the features.
        """
        # This would typically summarize the feature vector in a human-readable way
        # For now, we'll just return the feature dimensions and some basic stats
        if hasattr(features, "shape"):
            return {"dimensions": features.shape}
        elif isinstance(features, dict):
            return {"feature_count": len(features)}
        else:
            return {"feature_type": str(type(features))}
    
    def _update_performance_metrics(self, result: ClassificationResult, processing_time: float) -> None:
        """
        Updates performance metrics based on classification result.
        
        Args:
            result: The classification result.
            processing_time: Time taken to classify the document in seconds.
        """
        if not self.enable_performance_metrics:
            return
        
        # Update success/failure counts
        if result["requires_review"]:
            self.classification_metrics["low_confidence_classifications"] += 1
        else:
            self.classification_metrics["successful_classifications"] += 1
        
        # Update average confidence
        total_confidence = (self.classification_metrics["average_confidence"] * 
                           (self.classification_metrics["total_documents"] - 1))
        total_confidence += result["confidence_score"]
        self.classification_metrics["average_confidence"] = (
            total_confidence / self.classification_metrics["total_documents"]
        )
        
        # Update average processing time
        total_time = (self.classification_metrics["average_processing_time"] * 
                     (self.classification_metrics["total_documents"] - 1))
        total_time += processing_time
        self.classification_metrics["average_processing_time"] = (
            total_time / self.classification_metrics["total_documents"]
        )
        
        # Log metrics periodically
        if self.classification_metrics["total_documents"] % 100 == 0:
            self.logger.info(f"Classification metrics: {json.dumps(self.classification_metrics)}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Returns the current performance metrics for monitoring.
        
        Returns:
            A dictionary containing performance metrics.
        """
        return self.classification_metrics
    
    def get_supported_document_types(self) -> List[str]:
        """
        Returns the list of document types supported by the classifier.
        
        Returns:
            A list of supported document types.
        """
        return self.document_types