#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Base Model for OCR Processing

This module defines the abstract base class for all OCR models in the system.
It establishes the common interface and shared functionality that all OCR models
must implement, including methods for model loading, image preprocessing,
text extraction, and result formatting.
"""

import abc
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import tensorflow as tf

from ..types.config import TensorFlowConfig
from ..types.documents import DocumentContent, DocumentMetadata
from ..types.extraction import ConfidenceScore, ExtractedData, ExtractedField
from ..types.models import ModelParameters, ModelResult
from ..utils.image_utils import normalize_image, preprocess_image
from ..utils.logging_utils import get_logger
from ..utils.tensorflow_utils import configure_gpu_memory


logger = get_logger(__name__)


class BaseOCRModel(abc.ABC):
    """
    Abstract base class for all OCR models in the system.
    
    This class defines the common interface and shared functionality that all OCR models
    must implement. It provides methods for model loading, image preprocessing, text extraction,
    and result formatting with confidence scoring.
    
    Attributes:
        model_path (Path): Path to the TensorFlow model files
        model_name (str): Name of the model for logging and identification
        model_version (str): Version of the model
        config (TensorFlowConfig): Configuration for TensorFlow and GPU settings
        model (tf.keras.Model): The loaded TensorFlow model
        parameters (ModelParameters): Model-specific parameters and hyperparameters
    """
    
    def __init__(self, 
                 model_path: Union[str, Path], 
                 model_name: str,
                 config: TensorFlowConfig,
                 parameters: Optional[ModelParameters] = None) -> None:
        """
        Initialize the OCR model with the specified model path and configuration.
        
        Args:
            model_path: Path to the TensorFlow model files
            model_name: Name of the model for logging and identification
            config: Configuration for TensorFlow and GPU settings
            parameters: Model-specific parameters and hyperparameters (optional)
        
        Raises:
            ValueError: If the model path does not exist or is invalid
            RuntimeError: If GPU initialization fails
        """
        self.model_path = Path(model_path) if isinstance(model_path, str) else model_path
        self.model_name = model_name
        self.config = config
        self.parameters = parameters or {}
        self.model = None
        self.model_version = "unknown"
        
        # Validate model path
        if not self.model_path.exists():
            raise ValueError(f"Model path does not exist: {self.model_path}")
        
        # Configure GPU memory if available
        if config.use_gpu:
            try:
                configure_gpu_memory(config.gpu_memory_limit, config.gpu_growth)
                logger.info(f"GPU configured for {self.model_name} with memory limit: {config.gpu_memory_limit}MB")
            except Exception as e:
                logger.error(f"Failed to configure GPU: {str(e)}")
                raise RuntimeError(f"GPU initialization failed: {str(e)}")
        
        # Load the model
        self._load_model()
        
        logger.info(f"Initialized {self.model_name} (version: {self.model_version})")
    
    def _load_model(self) -> None:
        """
        Load the TensorFlow model from the specified path.
        
        This method loads the model and sets the model_version attribute.
        
        Raises:
            RuntimeError: If model loading fails
        """
        try:
            # Load the model using TensorFlow's SavedModel format
            self.model = tf.saved_model.load(str(self.model_path))
            
            # Try to get model version from saved_model.pb metadata or version file
            version_file = self.model_path / "version.txt"
            if version_file.exists():
                with open(version_file, "r") as f:
                    self.model_version = f.read().strip()
            else:
                # Use directory name as fallback for version
                self.model_version = self.model_path.name
                
            logger.info(f"Successfully loaded {self.model_name} model (version: {self.model_version})")
        except Exception as e:
            error_msg = f"Failed to load model {self.model_name} from {self.model_path}: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def preprocess_document(self, document_content: DocumentContent, 
                           document_metadata: DocumentMetadata) -> np.ndarray:
        """
        Preprocess the document image for OCR processing.
        
        This method applies common preprocessing steps such as normalization,
        resizing, and enhancement to optimize the image for OCR processing.
        
        Args:
            document_content: Binary content of the document
            document_metadata: Metadata of the document including MIME type
            
        Returns:
            Preprocessed image as a numpy array ready for OCR processing
            
        Raises:
            ValueError: If document content is invalid or unsupported
        """
        try:
            # Convert document content to image
            image = preprocess_image(document_content, document_metadata)
            
            # Apply normalization and enhancement
            normalized_image = normalize_image(image)
            
            return normalized_image
        except Exception as e:
            error_msg = f"Failed to preprocess document: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    @abc.abstractmethod
    def extract_text(self, image: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """
        Extract text from the preprocessed document image.
        
        This abstract method must be implemented by all derived classes to
        perform the actual text extraction using the specific OCR model.
        
        Args:
            image: Preprocessed document image as a numpy array
            
        Returns:
            List of tuples containing extracted text and confidence scores
            
        Raises:
            NotImplementedError: If the derived class does not implement this method
        """
        raise NotImplementedError("Derived classes must implement extract_text()")
    
    @abc.abstractmethod
    def extract_fields(self, image: np.ndarray, 
                      document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract structured fields from the document image.
        
        This abstract method must be implemented by all derived classes to
        extract structured fields based on the document type and content.
        
        Args:
            image: Preprocessed document image as a numpy array
            document_metadata: Metadata of the document including type and classification
            
        Returns:
            List of extracted fields with values and confidence scores
            
        Raises:
            NotImplementedError: If the derived class does not implement this method
        """
        raise NotImplementedError("Derived classes must implement extract_fields()")
    
    def process_document(self, document_content: DocumentContent, 
                        document_metadata: DocumentMetadata) -> ModelResult:
        """
        Process a document to extract text and structured fields.
        
        This method orchestrates the complete document processing workflow:
        1. Preprocess the document image
        2. Extract text from the image
        3. Extract structured fields based on document type
        4. Format the results with confidence scores
        
        Args:
            document_content: Binary content of the document
            document_metadata: Metadata of the document
            
        Returns:
            ModelResult containing extracted data and processing metadata
            
        Raises:
            ValueError: If document processing fails
        """
        start_time = datetime.now()
        
        try:
            # Preprocess the document
            preprocessed_image = self.preprocess_document(document_content, document_metadata)
            
            # Extract text and fields
            extracted_text = self.extract_text(preprocessed_image)
            extracted_fields = self.extract_fields(preprocessed_image, document_metadata)
            
            # Calculate overall confidence score
            confidence_scores = [field.confidence for field in extracted_fields]
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Format results
            extracted_data = ExtractedData(
                fields=extracted_fields,
                text=[text for text, _ in extracted_text],
                confidence=overall_confidence,
                metadata={
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "document_id": document_metadata.get("id", ""),
                    "document_type": document_metadata.get("type", ""),
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000
                }
            )
            
            # Create model result
            result = ModelResult(
                success=True,
                data=extracted_data,
                error=None,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            logger.info(
                f"Successfully processed document {document_metadata.get('id', '')} "
                f"with {self.model_name} (confidence: {overall_confidence:.2f})"
            )
            
            return result
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(error_msg)
            
            # Create error result
            result = ModelResult(
                success=False,
                data=None,
                error={
                    "message": error_msg,
                    "type": type(e).__name__
                },
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            return result
    
    def calculate_confidence(self, predictions: np.ndarray) -> ConfidenceScore:
        """
        Calculate confidence score from model predictions.
        
        This method converts raw model prediction probabilities into a
        standardized confidence score between 0.0 and 1.0.
        
        Args:
            predictions: Raw prediction probabilities from the model
            
        Returns:
            Standardized confidence score between 0.0 and 1.0
        """
        # Basic implementation - derived classes may override with model-specific logic
        if predictions is None or len(predictions) == 0:
            return 0.0
        
        # For classification models, use the highest probability
        if predictions.ndim > 1 and predictions.shape[1] > 1:
            return float(np.max(predictions, axis=1).mean())
        
        # For regression or single-output models, normalize to 0-1 range
        return float(np.clip(predictions.mean(), 0.0, 1.0))
    
    def format_result(self, extracted_fields: List[ExtractedField], 
                     document_metadata: DocumentMetadata) -> Dict[str, Any]:
        """
        Format extracted fields into a standardized JSON structure.
        
        This method converts the extracted fields into a structured JSON format
        suitable for downstream processing by the Data Service.
        
        Args:
            extracted_fields: List of extracted fields with values and confidence scores
            document_metadata: Metadata of the document
            
        Returns:
            Structured JSON representation of the extracted data
        """
        # Group fields by category
        categorized_fields = {}
        for field in extracted_fields:
            category = field.category or "general"
            if category not in categorized_fields:
                categorized_fields[category] = []
            
            categorized_fields[category].append({
                "name": field.name,
                "value": field.value,
                "confidence": field.confidence,
                "location": field.location,
                "requires_verification": field.confidence < self.config.verification_threshold
            })
        
        # Calculate overall confidence per category
        category_confidence = {}
        for category, fields in categorized_fields.items():
            confidence_scores = [field["confidence"] for field in fields]
            category_confidence[category] = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Create result structure
        result = {
            "document_id": document_metadata.get("id", ""),
            "document_type": document_metadata.get("type", ""),
            "extraction_time": datetime.now().isoformat(),
            "model": {
                "name": self.model_name,
                "version": self.model_version
            },
            "categories": {
                category: {
                    "fields": fields,
                    "confidence": category_confidence[category]
                } for category, fields in categorized_fields.items()
            },
            "overall_confidence": sum(category_confidence.values()) / len(category_confidence) 
                                if category_confidence else 0.0,
            "requires_verification": any(field["requires_verification"] 
                                      for fields in categorized_fields.values() 
                                      for field in fields)
        }
        
        return result
    
    def __str__(self) -> str:
        """
        Return a string representation of the model.
        
        Returns:
            String representation including model name and version
        """
        return f"{self.model_name} (version: {self.model_version})"
    
    def __repr__(self) -> str:
        """
        Return a detailed string representation of the model.
        
        Returns:
            Detailed string representation including model path and parameters
        """
        return (f"{self.__class__.__name__}(model_name='{self.model_name}', "
                f"model_version='{self.model_version}', "
                f"model_path='{self.model_path}')")