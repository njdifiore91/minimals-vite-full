#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Model Factory for OCR Processing

This module implements a factory class that creates and returns the appropriate OCR model
based on document type and classification metadata. This factory centralizes model selection
logic and provides a clean interface for the OCR service to obtain the right model for each
document.

Key features:
- Dynamic OCR model instantiation based on document classification
- Model caching for performance optimization
- Configuration loading for model parameters
- Unified interface for model access across the service

The factory supports the following model types:
- TypedTextModel: For documents with machine-printed text
- HandwrittenTextModel: For documents with handwritten text
- HybridRecognitionModel: For documents with both typed and handwritten text
- StructureRecognitionModel: For recognizing document structure
"""

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Type, Union

# Import model types
from .base_model import BaseOCRModel
from .typed_text_model import TypedTextModel
from .handwritten_text_model import HandwrittenTextModel
from .hybrid_recognition_model import HybridRecognitionModel
from .structure_recognition_model import StructureRecognitionModel

# Import types
from ..types.models import OCRModelType, ModelParameters
from ..types.documents import DocumentType, DocumentMetadata
from ..types.config import TensorFlowConfig

# Import configuration
from ..config.tensorflow_config import get_tensorflow_config
from ..utils.logging_utils import get_logger


logger = get_logger(__name__)


class ModelFactory:
    """
    Factory class for creating and managing OCR models.
    
    This class is responsible for creating and returning the appropriate OCR model
    based on document type and classification metadata. It centralizes model selection
    logic and provides a clean interface for the OCR service to obtain the right model
    for each document.
    
    The factory implements model caching to avoid repeatedly loading models, which
    significantly improves performance for batch processing scenarios.
    
    Attributes:
        _model_cache (Dict[str, BaseOCRModel]): Cache of loaded models
        _config (TensorFlowConfig): TensorFlow configuration
        _model_paths (Dict[str, Path]): Paths to model files
    """
    
    def __init__(self, config: Optional[TensorFlowConfig] = None):
        """
        Initialize the model factory with the specified configuration.
        
        Args:
            config: TensorFlow configuration (optional, will load from config module if not provided)
        """
        self._model_cache: Dict[str, BaseOCRModel] = {}
        self._config = config or get_tensorflow_config()
        
        # Set up model paths based on configuration
        models_base_path = Path(self._config.models_base_path)
        self._model_paths = {
            OCRModelType.TYPED.value: models_base_path / self._config.typed_model_path,
            OCRModelType.HANDWRITTEN.value: models_base_path / self._config.handwritten_model_path,
            OCRModelType.HYBRID.value: models_base_path / self._config.hybrid_model_path,
            "structure": models_base_path / self._config.structure_model_path
        }
        
        # Validate model paths
        for model_type, path in self._model_paths.items():
            if not path.exists():
                logger.warning(f"Model path for {model_type} does not exist: {path}")
        
        logger.info(f"Initialized ModelFactory with {len(self._model_paths)} model paths")
    
    def get_model(self, model_type: Union[str, OCRModelType], 
                 parameters: Optional[ModelParameters] = None) -> BaseOCRModel:
        """
        Get an OCR model of the specified type.
        
        This method returns a cached model if available, or creates and caches a new model
        if needed. It ensures that models are efficiently reused across multiple document
        processing requests.
        
        Args:
            model_type: Type of OCR model to get (typed, handwritten, hybrid, structure)
            parameters: Model-specific parameters (optional)
            
        Returns:
            OCR model instance
            
        Raises:
            ValueError: If the model type is invalid or the model cannot be created
        """
        # Convert string model type to enum if needed
        if isinstance(model_type, str):
            try:
                # Handle "structure" as a special case
                if model_type.lower() == "structure":
                    model_key = "structure"
                else:
                    model_type = OCRModelType(model_type.lower())
                    model_key = model_type.value
            except ValueError:
                valid_types = [t.value for t in OCRModelType] + ["structure"]
                raise ValueError(f"Invalid model type: {model_type}. Valid types are: {valid_types}")
        else:
            model_key = model_type.value
        
        # Check if model is already cached
        if model_key in self._model_cache:
            logger.debug(f"Using cached model for type: {model_key}")
            return self._model_cache[model_key]
        
        # Create new model
        logger.info(f"Creating new model for type: {model_key}")
        model = self._create_model(model_key, parameters)
        
        # Cache the model
        self._model_cache[model_key] = model
        
        return model
    
    def get_model_for_document(self, document_metadata: DocumentMetadata) -> BaseOCRModel:
        """
        Get the appropriate OCR model for a document based on its metadata.
        
        This method analyzes the document metadata to determine the most appropriate
        OCR model for processing the document. It considers document type, classification
        confidence, and other metadata to make an intelligent selection.
        
        Args:
            document_metadata: Metadata of the document to process
            
        Returns:
            OCR model instance appropriate for the document
            
        Raises:
            ValueError: If a suitable model cannot be determined
        """
        # Get document type
        doc_type = document_metadata.document_type
        
        # Get content type from metadata if available
        content_type = document_metadata.additional_metadata.get("content_type")
        
        # Check if structure recognition is needed first
        if document_metadata.additional_metadata.get("needs_structure_recognition", False):
            logger.info(f"Using structure recognition model for document {document_metadata.document_id}")
            return self.get_model("structure")
        
        # Determine model type based on document and content type
        model_type = self._determine_model_type(doc_type, content_type)
        
        # Get model parameters based on document type
        parameters = self._get_parameters_for_document(doc_type)
        
        # Get the model
        logger.info(f"Using {model_type} model for document {document_metadata.document_id}")
        return self.get_model(model_type, parameters)
        
    def get_structure_recognition_model(self) -> StructureRecognitionModel:
        """
        Get the structure recognition model.
        
        This is a convenience method for getting the structure recognition model,
        which is used to analyze document structure before text extraction.
        
        Returns:
            Structure recognition model instance
        """
        return self.get_model("structure")
    
    def _create_model(self, model_type: str, parameters: Optional[ModelParameters] = None) -> BaseOCRModel:
        """
        Create a new OCR model of the specified type.
        
        This method instantiates a new model of the specified type with the given parameters.
        It handles the details of model initialization and configuration.
        
        Args:
            model_type: Type of OCR model to create
            parameters: Model-specific parameters (optional)
            
        Returns:
            OCR model instance
            
        Raises:
            ValueError: If the model type is invalid or the model cannot be created
        """
        # Get model path
        if model_type not in self._model_paths:
            valid_types = list(self._model_paths.keys())
            raise ValueError(f"Invalid model type: {model_type}. Valid types are: {valid_types}")
        
        model_path = self._model_paths[model_type]
        
        # Create model based on type
        try:
            if model_type == OCRModelType.TYPED.value:
                return TypedTextModel(
                    model_path=model_path,
                    model_name="typed_text_model",
                    config=self._config,
                    parameters=parameters
                )
            elif model_type == OCRModelType.HANDWRITTEN.value:
                return HandwrittenTextModel(
                    model_path=model_path,
                    model_name="handwritten_text_model",
                    config=self._config,
                    parameters=parameters
                )
            elif model_type == OCRModelType.HYBRID.value:
                return HybridRecognitionModel(
                    model_path=model_path,
                    model_name="hybrid_recognition_model",
                    config=self._config,
                    parameters=parameters
                )
            elif model_type == "structure":
                return StructureRecognitionModel(
                    model_path=model_path,
                    model_name="structure_recognition_model",
                    config=self._config,
                    parameters=parameters
                )
            else:
                raise ValueError(f"Unsupported model type: {model_type}")
        except Exception as e:
            error_msg = f"Failed to create model of type {model_type}: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
    
    def _determine_model_type(self, document_type: Optional[DocumentType], 
                             content_type: Optional[str]) -> str:
        """
        Determine the appropriate model type for a document.
        
        This method analyzes the document type and content type to determine
        the most appropriate OCR model type for processing.
        
        Args:
            document_type: Type of document
            content_type: Type of content (typed, handwritten, hybrid)
            
        Returns:
            Model type string
        """
        # If content type is explicitly specified, use it
        if content_type:
            try:
                return OCRModelType(content_type.lower()).value
            except ValueError:
                # Invalid content type, fall back to document type
                pass
        
        # If document type is not specified, default to hybrid
        if not document_type:
            return OCRModelType.HYBRID.value
        
        # Map document types to default model types
        document_model_mapping = {
            DocumentType.APPLICATION: OCRModelType.HYBRID.value,
            DocumentType.TAX_RETURN: OCRModelType.TYPED.value,
            DocumentType.BANK_STATEMENT: OCRModelType.TYPED.value,
            DocumentType.PAY_STUB: OCRModelType.TYPED.value,
            DocumentType.ID_DOCUMENT: OCRModelType.HYBRID.value,
            DocumentType.OTHER: OCRModelType.HYBRID.value
        }
        
        # Check for additional metadata that might influence model selection
        if document_type and hasattr(document_type, 'additional_metadata'):
            metadata = getattr(document_type, 'additional_metadata', {})
            
            # Check if document has been pre-classified as handwritten
            if metadata.get('is_handwritten', False):
                return OCRModelType.HANDWRITTEN.value
            
            # Check if document has been pre-classified as typed
            if metadata.get('is_typed', False):
                return OCRModelType.TYPED.value
            
            # Check if document has been pre-classified as mixed
            if metadata.get('is_mixed', False):
                return OCRModelType.HYBRID.value
            
            # Check if document quality is poor (use more robust hybrid model)
            if metadata.get('document_quality') == 'poor':
                return OCRModelType.HYBRID.value
        
        # Use the default mapping if no special conditions apply
        return document_model_mapping.get(document_type, OCRModelType.HYBRID.value)
    
    def _get_parameters_for_document(self, document_type: Optional[DocumentType]) -> Optional[ModelParameters]:
        """
        Get model parameters optimized for a specific document type.
        
        This method returns model parameters that are optimized for processing
        a specific type of document.
        
        Args:
            document_type: Type of document
            
        Returns:
            Model parameters or None if no specific parameters are needed
        """
        if not document_type:
            return None
            
        # Define document-specific parameters
        # These parameters are optimized for each document type based on testing
        # and performance analysis
        parameters_map = {
            DocumentType.APPLICATION: ModelParameters(
                model_type=OCRModelType.HYBRID,
                model_id="hybrid_application",
                model_version="1.0.0",
                confidence_threshold=0.75,  # Balanced threshold for hybrid content
                batch_size=1,
                language="en",
                preprocessing_steps=["deskew", "denoise", "normalize"],
                postprocessing_steps=["spell_check", "grammar_check"]
            ),
            DocumentType.TAX_RETURN: ModelParameters(
                model_type=OCRModelType.TYPED,
                model_id="typed_tax_return",
                model_version="1.0.0",
                confidence_threshold=0.85,  # Higher threshold for critical financial data
                batch_size=1,
                language="en",
                preprocessing_steps=["deskew", "binarize", "enhance_contrast"],
                postprocessing_steps=["validate_numbers", "validate_dates"]
            ),
            DocumentType.BANK_STATEMENT: ModelParameters(
                model_type=OCRModelType.TYPED,
                model_id="typed_bank_statement",
                model_version="1.0.0",
                confidence_threshold=0.85,  # Higher threshold for critical financial data
                batch_size=1,
                language="en",
                preprocessing_steps=["deskew", "binarize", "enhance_contrast"],
                postprocessing_steps=["validate_numbers", "validate_dates"]
            ),
            DocumentType.PAY_STUB: ModelParameters(
                model_type=OCRModelType.TYPED,
                model_id="typed_pay_stub",
                model_version="1.0.0",
                confidence_threshold=0.80,  # High threshold for financial data
                batch_size=1,
                language="en",
                preprocessing_steps=["deskew", "binarize", "enhance_contrast"],
                postprocessing_steps=["validate_numbers", "validate_dates"]
            ),
            DocumentType.ID_DOCUMENT: ModelParameters(
                model_type=OCRModelType.HYBRID,
                model_id="hybrid_id_document",
                model_version="1.0.0",
                confidence_threshold=0.85,  # Higher threshold for identity verification
                batch_size=1,
                language="en",
                preprocessing_steps=["deskew", "enhance_contrast", "normalize"],
                postprocessing_steps=["validate_id_format"]
            )
        }
        
        # Return parameters for the document type, or None if not defined
        return parameters_map.get(document_type)
    
    def clear_cache(self) -> None:
        """
        Clear the model cache to free up resources.
        
        This method should be called when models are no longer needed,
        such as during service shutdown or when memory needs to be reclaimed.
        """
        logger.info(f"Clearing model cache ({len(self._model_cache)} models)")
        
        # Clean up each model
        for model_type, model in self._model_cache.items():
            try:
                # Call any cleanup methods on the model
                if hasattr(model, "cleanup") and callable(model.cleanup):
                    model.cleanup()
                logger.debug(f"Cleaned up model: {model_type}")
            except Exception as e:
                logger.warning(f"Error cleaning up model {model_type}: {str(e)}")
        
        # Clear the cache
        self._model_cache.clear()
    
    def get_cached_model_types(self) -> list:
        """
        Get a list of model types currently in the cache.
        
        Returns:
            List of model type strings
        """
        return list(self._model_cache.keys())
    
    def is_model_cached(self, model_type: Union[str, OCRModelType]) -> bool:
        """
        Check if a model of the specified type is cached.
        
        Args:
            model_type: Type of OCR model to check
            
        Returns:
            True if the model is cached, False otherwise
        """
        # Convert enum to string if needed
        if isinstance(model_type, OCRModelType):
            model_type = model_type.value
            
        return model_type in self._model_cache
    
    def remove_from_cache(self, model_type: Union[str, OCRModelType]) -> bool:
        """
        Remove a specific model from the cache.
        
        Args:
            model_type: Type of OCR model to remove
            
        Returns:
            True if the model was removed, False if it wasn't in the cache
        """
        # Convert enum to string if needed
        if isinstance(model_type, OCRModelType):
            model_type = model_type.value
            
        if model_type in self._model_cache:
            model = self._model_cache[model_type]
            
            # Clean up the model
            try:
                if hasattr(model, "cleanup") and callable(model.cleanup):
                    model.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up model {model_type}: {str(e)}")
            
            # Remove from cache
            del self._model_cache[model_type]
            logger.debug(f"Removed model from cache: {model_type}")
            return True
        
        return False
    
    def __del__(self):
        """
        Clean up resources when the factory is deleted.
        """
        try:
            self.clear_cache()
        except Exception as e:
            # Can't use logger here as it might be None during interpreter shutdown
            print(f"Error cleaning up ModelFactory: {str(e)}")


    def select_best_model(self, document_metadata: DocumentMetadata, 
                        performance_threshold: float = 0.95) -> BaseOCRModel:
        """
        Select the best model for a document based on performance metrics.
        
        This method tries multiple models on a sample of the document and selects
        the one with the best performance metrics. This is useful for documents
        where the content type is uncertain or mixed.
        
        Args:
            document_metadata: Metadata of the document to process
            performance_threshold: Threshold for acceptable performance (0.0-1.0)
            
        Returns:
            Best performing OCR model instance
            
        Raises:
            ValueError: If no model meets the performance threshold
        """
        logger.info(f"Selecting best model for document {document_metadata.document_id}")
        
        # Get document type
        doc_type = document_metadata.document_type
        
        # Models to try, in order of preference
        model_types_to_try = [
            OCRModelType.HYBRID.value,  # Try hybrid first as it's most versatile
            OCRModelType.TYPED.value,   # Then try typed
            OCRModelType.HANDWRITTEN.value  # Finally try handwritten
        ]
        
        best_model = None
        best_performance = 0.0
        
        # Try each model type
        for model_type in model_types_to_try:
            try:
                # Get model parameters
                parameters = self._get_parameters_for_document(doc_type)
                
                # Get model
                model = self.get_model(model_type, parameters)
                
                # Evaluate model performance (this would be implemented in a real system)
                # For now, we'll use a placeholder implementation
                performance = self._evaluate_model_performance(model, document_metadata)
                
                logger.debug(f"Model {model_type} performance: {performance:.2f}")
                
                # Update best model if this one performs better
                if performance > best_performance:
                    best_model = model
                    best_performance = performance
                    
                    # If performance is good enough, stop trying more models
                    if performance >= performance_threshold:
                        logger.info(f"Selected model {model_type} with performance {performance:.2f}")
                        return model
                    
            except Exception as e:
                logger.warning(f"Error evaluating model {model_type}: {str(e)}")
        
        # If we found a model but it didn't meet the threshold, use it anyway
        if best_model is not None:
            logger.info(f"Using best available model with performance {best_performance:.2f}")
            return best_model
            
        # If no model worked, fall back to hybrid
        logger.warning(f"No suitable model found, falling back to hybrid")
        return self.get_model(OCRModelType.HYBRID.value)
    
    def _evaluate_model_performance(self, model: BaseOCRModel, 
                                  document_metadata: DocumentMetadata) -> float:
        """
        Evaluate model performance on a document.
        
        This method evaluates how well a model performs on a document
        by analyzing confidence scores and other metrics.
        
        Args:
            model: OCR model to evaluate
            document_metadata: Metadata of the document to process
            
        Returns:
            Performance score between 0.0 and 1.0
        """
        # This is a placeholder implementation
        # In a real implementation, this would run the model on a sample of the document
        # and analyze the results to determine performance
        
        # For now, return a score based on model type and document type
        model_type = model.model_name
        doc_type = document_metadata.document_type
        
        # Default performance scores based on model and document type
        performance_matrix = {
            "typed_text_model": {
                DocumentType.APPLICATION: 0.85,
                DocumentType.TAX_RETURN: 0.95,
                DocumentType.BANK_STATEMENT: 0.95,
                DocumentType.PAY_STUB: 0.90,
                DocumentType.ID_DOCUMENT: 0.80,
                DocumentType.OTHER: 0.75
            },
            "handwritten_text_model": {
                DocumentType.APPLICATION: 0.80,
                DocumentType.TAX_RETURN: 0.70,
                DocumentType.BANK_STATEMENT: 0.65,
                DocumentType.PAY_STUB: 0.70,
                DocumentType.ID_DOCUMENT: 0.85,
                DocumentType.OTHER: 0.75
            },
            "hybrid_recognition_model": {
                DocumentType.APPLICATION: 0.90,
                DocumentType.TAX_RETURN: 0.85,
                DocumentType.BANK_STATEMENT: 0.85,
                DocumentType.PAY_STUB: 0.85,
                DocumentType.ID_DOCUMENT: 0.90,
                DocumentType.OTHER: 0.85
            }
        }
        
        # Get performance score from matrix, or use default
        if model_type in performance_matrix and doc_type in performance_matrix[model_type]:
            return performance_matrix[model_type][doc_type]
        else:
            return 0.75  # Default performance score


# Singleton instance for global use
_factory_instance = None


def get_model_factory(config: Optional[TensorFlowConfig] = None) -> ModelFactory:
    """
    Get the global ModelFactory instance.
    
    This function returns the singleton ModelFactory instance,
    creating it if it doesn't exist yet.
    
    Args:
        config: TensorFlow configuration (optional)
        
    Returns:
        ModelFactory instance
    """
    global _factory_instance
    
    if _factory_instance is None:
        _factory_instance = ModelFactory(config)
        
    return _factory_instance