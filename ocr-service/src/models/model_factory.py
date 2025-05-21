"""
Model Factory for OCR Service.

This module implements a factory class that creates and returns the appropriate OCR model
based on document type and classification metadata. It centralizes model selection logic
and provides a clean interface for the OCR service to obtain the right model for each document.

The factory implements model caching for performance optimization, ensuring that models
are only loaded once and reused for subsequent requests, significantly reducing processing time.
"""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from typing import Dict, Optional, Union

# Import local modules
from ..config import tensorflow_config
from ..types.documents import DocumentMetadata, DocumentType
from ..types.models import (
    DEFAULT_HANDWRITTEN_MODEL_PARAMS,
    DEFAULT_HYBRID_MODEL_PARAMS,
    DEFAULT_TYPED_MODEL_PARAMS,
    ModelParameters,
    ModelSelectionCriteria,
    ModelSelector,
    OCRModelType,
    TensorFlowModel
)

# Configure logging
logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory class for creating and managing OCR models.
    
    This class is responsible for creating and returning the appropriate OCR model
    based on document type and classification metadata. It implements model caching
    to optimize performance and provides a clean interface for model access.
    """
    
    # Singleton instance
    _instance = None
    
    # Model cache
    _model_cache: Dict[str, TensorFlowModel] = {}
    
    def __new__(cls):
        """Implement singleton pattern to ensure only one factory instance exists."""
        if cls._instance is None:
            cls._instance = super(ModelFactory, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the model factory."""
        logger.info("Initializing OCR Model Factory")
        self._model_cache = {}
        self._load_config()
    
    def _load_config(self):
        """Load model configuration from config files."""
        logger.info("Loading model configuration")
        # Load model paths and parameters from configuration
        self.config = tensorflow_config.get_model_config()
        
        # Update default parameters with configuration values
        self._update_model_params()
    
    def _update_model_params(self):
        """Update default model parameters with configuration values."""
        # Update typed model parameters
        if hasattr(self.config, 'typed_model'):
            for key, value in self.config.typed_model.items():
                if key in DEFAULT_TYPED_MODEL_PARAMS:
                    DEFAULT_TYPED_MODEL_PARAMS[key] = value
        
        # Update handwritten model parameters
        if hasattr(self.config, 'handwritten_model'):
            for key, value in self.config.handwritten_model.items():
                if key in DEFAULT_HANDWRITTEN_MODEL_PARAMS:
                    DEFAULT_HANDWRITTEN_MODEL_PARAMS[key] = value
        
        # Update hybrid model parameters
        if hasattr(self.config, 'hybrid_model'):
            for key, value in self.config.hybrid_model.items():
                if key in DEFAULT_HYBRID_MODEL_PARAMS:
                    DEFAULT_HYBRID_MODEL_PARAMS[key] = value
    
    def get_model_for_document(self, document_metadata: DocumentMetadata) -> TensorFlowModel:
        """Get the appropriate OCR model for the given document.
        
        Args:
            document_metadata: Metadata for the document to process
            
        Returns:
            The appropriate OCR model for the document
        """
        # Create selection criteria from document metadata
        criteria = self._create_selection_criteria(document_metadata)
        
        # Select model type based on criteria
        model_type = ModelSelector.select_model_type(criteria)
        
        # Get or create model instance
        return self.get_model(model_type)
    
    def _create_selection_criteria(self, metadata: DocumentMetadata) -> ModelSelectionCriteria:
        """Create model selection criteria from document metadata.
        
        Args:
            metadata: Document metadata
            
        Returns:
            Model selection criteria
        """
        criteria: ModelSelectionCriteria = {
            'document_type': metadata.document_type.value if hasattr(metadata, 'document_type') else None,
            'content_type': metadata.content_type if hasattr(metadata, 'content_type') else None,
            'file_size': metadata.file_size if hasattr(metadata, 'file_size') else None,
        }
        
        # Add handwriting detection if available
        if hasattr(metadata, 'has_handwriting'):
            criteria['has_handwriting'] = metadata.has_handwriting
        
        # Add image quality if available
        if hasattr(metadata, 'image_quality'):
            criteria['image_quality'] = metadata.image_quality
        
        # Add language if available
        if hasattr(metadata, 'language'):
            criteria['language'] = metadata.language
        
        # Add priority if available
        if hasattr(metadata, 'priority'):
            criteria['priority'] = metadata.priority
        
        return criteria
    
    @lru_cache(maxsize=3)  # Cache at most 3 models (one for each type)
    def get_model(self, model_type: OCRModelType) -> TensorFlowModel:
        """Get or create a model of the specified type.
        
        This method implements model caching to avoid reloading models unnecessarily.
        It uses Python's lru_cache decorator to cache model instances based on model type.
        
        Args:
            model_type: Type of OCR model to get
            
        Returns:
            The requested OCR model
            
        Raises:
            ValueError: If the model type is not supported
        """
        # Check if model is already in cache
        model_key = model_type.value
        if model_key in self._model_cache:
            logger.debug(f"Using cached model for type: {model_type.value}")
            return self._model_cache[model_key]
        
        # Get model parameters
        model_params = self._get_model_parameters(model_type)
        
        # Create and initialize model
        logger.info(f"Creating new model for type: {model_type.value}")
        model = TensorFlowModel(model_params)
        
        try:
            # Load model weights and initialize
            model.load()
            
            # Add to cache
            self._model_cache[model_key] = model
            
            return model
        except Exception as e:
            logger.error(f"Error loading model {model_type.value}: {str(e)}")
            raise RuntimeError(f"Failed to load OCR model: {str(e)}") from e
    
    def _get_model_parameters(self, model_type: OCRModelType) -> ModelParameters:
        """Get parameters for the specified model type.
        
        Args:
            model_type: Type of OCR model
            
        Returns:
            Model parameters
            
        Raises:
            ValueError: If the model type is not supported
        """
        # Get default parameters for model type
        if model_type == OCRModelType.TYPED:
            params = DEFAULT_TYPED_MODEL_PARAMS.copy()
        elif model_type == OCRModelType.HANDWRITTEN:
            params = DEFAULT_HANDWRITTEN_MODEL_PARAMS.copy()
        elif model_type == OCRModelType.HYBRID:
            params = DEFAULT_HYBRID_MODEL_PARAMS.copy()
        else:
            raise ValueError(f"Unsupported model type: {model_type}")
        
        # Override with environment-specific paths if available
        model_dir = os.environ.get('OCR_MODEL_DIR', '/models')
        params['model_path'] = os.path.join(model_dir, f"{model_type.value}_text_ocr")
        params['vocab_path'] = os.path.join(model_dir, f"{model_type.value}_text_ocr/vocab.txt")
        
        # Apply any additional configuration from config files
        self._apply_config_overrides(params, model_type)
        
        return params
    
    def _apply_config_overrides(self, params: ModelParameters, model_type: OCRModelType) -> None:
        """Apply configuration overrides to model parameters.
        
        Args:
            params: Model parameters to update
            model_type: Type of OCR model
        """
        # Apply global overrides
        if hasattr(self.config, 'global'):
            for key, value in self.config.global.items():
                if key in params:
                    params[key] = value
        
        # Apply model-specific overrides
        config_key = f"{model_type.value}_model"
        if hasattr(self.config, config_key):
            model_config = getattr(self.config, config_key)
            for key, value in model_config.items():
                if key in params:
                    params[key] = value
    
    def clear_cache(self) -> None:
        """Clear the model cache.
        
        This method can be used to free memory or force model reloading.
        """
        logger.info("Clearing model cache")
        self._model_cache.clear()
        # Also clear the lru_cache
        self.get_model.cache_clear()
    
    def get_model_by_document_type(self, document_type: Union[DocumentType, str]) -> TensorFlowModel:
        """Get the appropriate OCR model for the given document type.
        
        This is a convenience method for getting a model based on document type alone,
        without needing full document metadata.
        
        Args:
            document_type: Type of document to process
            
        Returns:
            The appropriate OCR model for the document type
        """
        # Convert string to enum if needed
        if isinstance(document_type, str):
            try:
                document_type = DocumentType[document_type.upper()]
            except KeyError:
                logger.warning(f"Unknown document type: {document_type}, using default model")
                return self.get_model(OCRModelType.HYBRID)
        
        # Map document types to model types
        model_type_map = {
            DocumentType.APPLICATION: OCRModelType.HYBRID,
            DocumentType.TAX_RETURN: OCRModelType.TYPED,
            DocumentType.BANK_STATEMENT: OCRModelType.TYPED,
            DocumentType.PAY_STUB: OCRModelType.TYPED,
            DocumentType.ID_DOCUMENT: OCRModelType.HYBRID,
            DocumentType.OTHER: OCRModelType.HYBRID,
        }
        
        model_type = model_type_map.get(document_type, OCRModelType.HYBRID)
        return self.get_model(model_type)


# Create a singleton instance for easy import
model_factory = ModelFactory()


def get_model_for_document(document_metadata: DocumentMetadata) -> TensorFlowModel:
    """Convenience function to get the appropriate OCR model for a document.
    
    Args:
        document_metadata: Metadata for the document to process
        
    Returns:
        The appropriate OCR model for the document
    """
    return model_factory.get_model_for_document(document_metadata)


def get_model(model_type: OCRModelType) -> TensorFlowModel:
    """Convenience function to get a model of the specified type.
    
    Args:
        model_type: Type of OCR model to get
        
    Returns:
        The requested OCR model
    """
    return model_factory.get_model(model_type)


def get_model_by_document_type(document_type: Union[DocumentType, str]) -> TensorFlowModel:
    """Convenience function to get a model based on document type.
    
    Args:
        document_type: Type of document to process
        
    Returns:
        The appropriate OCR model for the document type
    """
    return model_factory.get_model_by_document_type(document_type)


def clear_model_cache() -> None:
    """Convenience function to clear the model cache."""
    model_factory.clear_cache()