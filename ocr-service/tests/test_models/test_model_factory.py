#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the OCR Model Factory

This module tests the factory class that creates and returns appropriate OCR models
based on document type and classification metadata. It verifies that the factory
correctly selects models, initializes them with proper configuration, and implements
caching for performance optimization.

Test coverage includes:
- Model selection logic based on document classification
- Configuration loading for model parameters
- Model caching for performance optimization
- Unified interface for model access across the service
- Error handling for unknown document types
- Performance impact of model caching
"""

import os
import time
import unittest.mock as mock
from pathlib import Path
from typing import Dict, List, Optional, Any

import pytest
import numpy as np

# Import the model factory and related types
from ocr_service.src.models.model_factory import ModelFactory, get_model_factory
from ocr_service.src.models.base_model import BaseOCRModel
from ocr_service.src.models.typed_text_model import TypedTextModel
from ocr_service.src.models.handwritten_text_model import HandwrittenTextModel
from ocr_service.src.models.hybrid_recognition_model import HybridRecognitionModel
from ocr_service.src.models.structure_recognition_model import StructureRecognitionModel

from ocr_service.src.types.models import OCRModelType, ModelParameters
from ocr_service.src.types.documents import DocumentType, DocumentMetadata
from ocr_service.src.types.config import TensorFlowConfig


# ===== Test Fixtures =====

@pytest.fixture
def mock_tensorflow_config():
    """Create a mock TensorFlow configuration for testing."""
    return TensorFlowConfig(
        models_base_path="/mock/models",
        typed_model_path="typed/v1.0",
        handwritten_model_path="handwritten/v1.0",
        hybrid_model_path="hybrid/v1.0",
        structure_model_path="structure/v1.0"
    )


@pytest.fixture
def mock_model_paths(tmp_path):
    """Create temporary model paths for testing."""
    # Create base directory
    base_dir = tmp_path / "models"
    base_dir.mkdir()
    
    # Create model directories
    typed_dir = base_dir / "typed" / "v1.0"
    handwritten_dir = base_dir / "handwritten" / "v1.0"
    hybrid_dir = base_dir / "hybrid" / "v1.0"
    structure_dir = base_dir / "structure" / "v1.0"
    
    typed_dir.mkdir(parents=True)
    handwritten_dir.mkdir(parents=True)
    hybrid_dir.mkdir(parents=True)
    structure_dir.mkdir(parents=True)
    
    # Create dummy model files
    (typed_dir / "model.h5").touch()
    (handwritten_dir / "model.h5").touch()
    (hybrid_dir / "model.h5").touch()
    (structure_dir / "model.h5").touch()
    
    return {
        "base_dir": base_dir,
        "typed_dir": typed_dir,
        "handwritten_dir": handwritten_dir,
        "hybrid_dir": hybrid_dir,
        "structure_dir": structure_dir
    }


@pytest.fixture
def mock_document_metadata():
    """Create mock document metadata for testing."""
    return {
        "application": DocumentMetadata(
            filename="application.pdf",
            size=1024,
            mime_type="application/pdf",
            document_type=DocumentType.APPLICATION,
            classification_confidence=0.95,
            additional_metadata={"content_type": "hybrid"}
        ),
        "tax_return": DocumentMetadata(
            filename="tax_return.pdf",
            size=2048,
            mime_type="application/pdf",
            document_type=DocumentType.TAX_RETURN,
            classification_confidence=0.98,
            additional_metadata={"content_type": "typed"}
        ),
        "bank_statement": DocumentMetadata(
            filename="bank_statement.pdf",
            size=1536,
            mime_type="application/pdf",
            document_type=DocumentType.BANK_STATEMENT,
            classification_confidence=0.97,
            additional_metadata={"content_type": "typed"}
        ),
        "id_document": DocumentMetadata(
            filename="id_document.jpg",
            size=512,
            mime_type="image/jpeg",
            document_type=DocumentType.ID_DOCUMENT,
            classification_confidence=0.96,
            additional_metadata={"content_type": "hybrid"}
        ),
        "handwritten_note": DocumentMetadata(
            filename="handwritten_note.jpg",
            size=768,
            mime_type="image/jpeg",
            document_type=DocumentType.OTHER,
            classification_confidence=0.90,
            additional_metadata={"content_type": "handwritten", "is_handwritten": True}
        ),
        "structure_document": DocumentMetadata(
            filename="form.pdf",
            size=2048,
            mime_type="application/pdf",
            document_type=DocumentType.APPLICATION,
            classification_confidence=0.95,
            additional_metadata={"needs_structure_recognition": True}
        )
    }


@pytest.fixture
def mock_model_factory(mock_tensorflow_config, mock_model_paths):
    """Create a ModelFactory instance with mocked paths for testing."""
    # Update config with actual paths
    config = mock_tensorflow_config
    config["models_base_path"] = str(mock_model_paths["base_dir"])
    
    # Create factory with mocked config
    factory = ModelFactory(config)
    
    return factory


# ===== Test Model Creation =====

def test_model_factory_initialization(mock_tensorflow_config):
    """Test that the ModelFactory initializes correctly."""
    factory = ModelFactory(mock_tensorflow_config)
    
    # Check that the factory was initialized with the correct configuration
    assert factory._config == mock_tensorflow_config
    assert len(factory._model_paths) == 4  # typed, handwritten, hybrid, structure
    assert factory._model_cache == {}


@mock.patch("ocr_service.src.models.typed_text_model.TypedTextModel")
def test_create_typed_text_model(mock_typed_model_class, mock_model_factory):
    """Test creation of a typed text model."""
    # Configure the mock
    mock_model_instance = mock.MagicMock()
    mock_typed_model_class.return_value = mock_model_instance
    
    # Get a typed text model
    model = mock_model_factory.get_model(OCRModelType.TYPED)
    
    # Check that the correct model class was instantiated
    mock_typed_model_class.assert_called_once()
    assert model == mock_model_instance


@mock.patch("ocr_service.src.models.handwritten_text_model.HandwrittenTextModel")
def test_create_handwritten_text_model(mock_handwritten_model_class, mock_model_factory):
    """Test creation of a handwritten text model."""
    # Configure the mock
    mock_model_instance = mock.MagicMock()
    mock_handwritten_model_class.return_value = mock_model_instance
    
    # Get a handwritten text model
    model = mock_model_factory.get_model(OCRModelType.HANDWRITTEN)
    
    # Check that the correct model class was instantiated
    mock_handwritten_model_class.assert_called_once()
    assert model == mock_model_instance


@mock.patch("ocr_service.src.models.hybrid_recognition_model.HybridRecognitionModel")
def test_create_hybrid_recognition_model(mock_hybrid_model_class, mock_model_factory):
    """Test creation of a hybrid recognition model."""
    # Configure the mock
    mock_model_instance = mock.MagicMock()
    mock_hybrid_model_class.return_value = mock_model_instance
    
    # Get a hybrid recognition model
    model = mock_model_factory.get_model(OCRModelType.HYBRID)
    
    # Check that the correct model class was instantiated
    mock_hybrid_model_class.assert_called_once()
    assert model == mock_model_instance


@mock.patch("ocr_service.src.models.structure_recognition_model.StructureRecognitionModel")
def test_create_structure_recognition_model(mock_structure_model_class, mock_model_factory):
    """Test creation of a structure recognition model."""
    # Configure the mock
    mock_model_instance = mock.MagicMock()
    mock_structure_model_class.return_value = mock_model_instance
    
    # Get a structure recognition model
    model = mock_model_factory.get_model("structure")
    
    # Check that the correct model class was instantiated
    mock_structure_model_class.assert_called_once()
    assert model == mock_model_instance


# ===== Test Model Selection Based on Document Metadata =====

@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_for_document_application(mock_create_model, mock_model_factory, mock_document_metadata):
    """Test model selection for an application document."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get model for application document
    model = mock_model_factory.get_model_for_document(mock_document_metadata["application"])
    
    # Check that the correct model type was created
    mock_create_model.assert_called_with(OCRModelType.HYBRID.value, mock.ANY)
    assert model == mock_model


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_for_document_tax_return(mock_create_model, mock_model_factory, mock_document_metadata):
    """Test model selection for a tax return document."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get model for tax return document
    model = mock_model_factory.get_model_for_document(mock_document_metadata["tax_return"])
    
    # Check that the correct model type was created
    mock_create_model.assert_called_with(OCRModelType.TYPED.value, mock.ANY)
    assert model == mock_model


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_for_document_handwritten(mock_create_model, mock_model_factory, mock_document_metadata):
    """Test model selection for a handwritten document."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get model for handwritten document
    model = mock_model_factory.get_model_for_document(mock_document_metadata["handwritten_note"])
    
    # Check that the correct model type was created
    mock_create_model.assert_called_with(OCRModelType.HANDWRITTEN.value, mock.ANY)
    assert model == mock_model


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_for_document_structure(mock_create_model, mock_model_factory, mock_document_metadata):
    """Test model selection for a document needing structure recognition."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get model for structure document
    model = mock_model_factory.get_model_for_document(mock_document_metadata["structure_document"])
    
    # Check that the correct model type was created
    mock_create_model.assert_called_with("structure", mock.ANY)
    assert model == mock_model


# ===== Test Model Caching =====

@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_model_caching(mock_create_model, mock_model_factory):
    """Test that models are cached and reused."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get a model twice
    model1 = mock_model_factory.get_model(OCRModelType.TYPED)
    model2 = mock_model_factory.get_model(OCRModelType.TYPED)
    
    # Check that the model was only created once
    mock_create_model.assert_called_once()
    assert model1 == model2
    assert mock_model_factory.is_model_cached(OCRModelType.TYPED)


def test_clear_cache(mock_model_factory):
    """Test clearing the model cache."""
    # Create some models to cache
    with mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model") as mock_create_model:
        mock_model = mock.MagicMock()
        mock_create_model.return_value = mock_model
        
        # Get models of different types
        mock_model_factory.get_model(OCRModelType.TYPED)
        mock_model_factory.get_model(OCRModelType.HANDWRITTEN)
        mock_model_factory.get_model(OCRModelType.HYBRID)
        
        # Check that models are cached
        assert len(mock_model_factory.get_cached_model_types()) == 3
        
        # Clear cache
        mock_model_factory.clear_cache()
        
        # Check that cache is empty
        assert len(mock_model_factory.get_cached_model_types()) == 0


def test_remove_from_cache(mock_model_factory):
    """Test removing a specific model from the cache."""
    # Create some models to cache
    with mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model") as mock_create_model:
        mock_model = mock.MagicMock()
        mock_create_model.return_value = mock_model
        
        # Get models of different types
        mock_model_factory.get_model(OCRModelType.TYPED)
        mock_model_factory.get_model(OCRModelType.HANDWRITTEN)
        mock_model_factory.get_model(OCRModelType.HYBRID)
        
        # Check that models are cached
        assert len(mock_model_factory.get_cached_model_types()) == 3
        
        # Remove one model from cache
        result = mock_model_factory.remove_from_cache(OCRModelType.TYPED)
        
        # Check that model was removed
        assert result is True
        assert len(mock_model_factory.get_cached_model_types()) == 2
        assert not mock_model_factory.is_model_cached(OCRModelType.TYPED)
        assert mock_model_factory.is_model_cached(OCRModelType.HANDWRITTEN)
        assert mock_model_factory.is_model_cached(OCRModelType.HYBRID)


# ===== Test Error Handling =====

def test_invalid_model_type(mock_model_factory):
    """Test error handling for invalid model types."""
    # Try to get a model with an invalid type
    with pytest.raises(ValueError) as excinfo:
        mock_model_factory.get_model("invalid_type")
    
    # Check error message
    assert "Invalid model type" in str(excinfo.value)
    assert "Valid types are" in str(excinfo.value)


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_model_creation_error(mock_create_model, mock_model_factory):
    """Test error handling for model creation failures."""
    # Configure the mock to raise an exception
    mock_create_model.side_effect = Exception("Model creation failed")
    
    # Try to get a model
    with pytest.raises(ValueError) as excinfo:
        mock_model_factory.get_model(OCRModelType.TYPED)
    
    # Check error message
    assert "Failed to create model" in str(excinfo.value)
    assert "Model creation failed" in str(excinfo.value)


# ===== Test Performance Optimization =====

@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_caching_performance(mock_create_model, mock_model_factory):
    """Test performance improvement from model caching."""
    # Configure the mock to simulate slow model creation
    def slow_create_model(*args, **kwargs):
        time.sleep(0.1)  # Simulate time-consuming model creation
        return mock.MagicMock()
    
    mock_create_model.side_effect = slow_create_model
    
    # Time first model creation (should be slow)
    start_time = time.time()
    model1 = mock_model_factory.get_model(OCRModelType.TYPED)
    first_creation_time = time.time() - start_time
    
    # Time second model creation (should be fast due to caching)
    start_time = time.time()
    model2 = mock_model_factory.get_model(OCRModelType.TYPED)
    cached_creation_time = time.time() - start_time
    
    # Check that cached creation is significantly faster
    assert cached_creation_time < first_creation_time / 10  # At least 10x faster
    assert model1 == model2  # Same model instance


# ===== Test Unified Interface =====

@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_string_type(mock_create_model, mock_model_factory):
    """Test getting a model using a string type."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get a model using string type
    model = mock_model_factory.get_model("typed")
    
    # Check that the correct model type was created
    mock_create_model.assert_called_with(OCRModelType.TYPED.value, None)
    assert model == mock_model


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_enum_type(mock_create_model, mock_model_factory):
    """Test getting a model using an enum type."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Get a model using enum type
    model = mock_model_factory.get_model(OCRModelType.TYPED)
    
    # Check that the correct model type was created
    mock_create_model.assert_called_with(OCRModelType.TYPED.value, None)
    assert model == mock_model


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._create_model")
def test_get_model_with_parameters(mock_create_model, mock_model_factory):
    """Test getting a model with custom parameters."""
    # Configure the mock
    mock_model = mock.MagicMock()
    mock_create_model.return_value = mock_model
    
    # Create custom parameters
    parameters = ModelParameters(
        model_type=OCRModelType.TYPED,
        model_id="custom_typed_model",
        model_version="1.0.0",
        confidence_threshold=0.8,
        batch_size=2,
        language="en",
        preprocessing_steps=["deskew", "denoise"]
    )
    
    # Get a model with custom parameters
    model = mock_model_factory.get_model(OCRModelType.TYPED, parameters)
    
    # Check that the correct model type and parameters were used
    mock_create_model.assert_called_with(OCRModelType.TYPED.value, parameters)
    assert model == mock_model


# ===== Test Singleton Factory =====

def test_get_model_factory_singleton():
    """Test that get_model_factory returns a singleton instance."""
    # Get factory instances
    factory1 = get_model_factory()
    factory2 = get_model_factory()
    
    # Check that they are the same instance
    assert factory1 is factory2


def test_get_model_factory_with_config(mock_tensorflow_config):
    """Test that get_model_factory accepts a custom configuration."""
    # Reset singleton instance
    import ocr_service.src.models.model_factory
    ocr_service.src.models.model_factory._factory_instance = None
    
    # Get factory with custom config
    factory = get_model_factory(mock_tensorflow_config)
    
    # Check that factory was initialized with the custom config
    assert factory._config == mock_tensorflow_config


# ===== Test Best Model Selection =====

@mock.patch("ocr_service.src.models.model_factory.ModelFactory._evaluate_model_performance")
@mock.patch("ocr_service.src.models.model_factory.ModelFactory.get_model")
def test_select_best_model(mock_get_model, mock_evaluate_performance, mock_model_factory, mock_document_metadata):
    """Test selecting the best model based on performance metrics."""
    # Configure mocks
    mock_hybrid_model = mock.MagicMock()
    mock_typed_model = mock.MagicMock()
    mock_handwritten_model = mock.MagicMock()
    
    mock_get_model.side_effect = [
        mock_hybrid_model,      # First call returns hybrid model
        mock_typed_model,       # Second call returns typed model
        mock_handwritten_model  # Third call returns handwritten model
    ]
    
    # Configure performance evaluation
    mock_evaluate_performance.side_effect = [
        0.85,  # Hybrid model performance
        0.92,  # Typed model performance (best)
        0.78   # Handwritten model performance
    ]
    
    # Select best model
    best_model = mock_model_factory.select_best_model(
        mock_document_metadata["tax_return"],
        performance_threshold=0.90
    )
    
    # Check that the best model was selected
    assert best_model == mock_typed_model
    assert mock_get_model.call_count == 2  # Should stop after finding a model above threshold
    assert mock_evaluate_performance.call_count == 2


@mock.patch("ocr_service.src.models.model_factory.ModelFactory._evaluate_model_performance")
@mock.patch("ocr_service.src.models.model_factory.ModelFactory.get_model")
def test_select_best_model_fallback(mock_get_model, mock_evaluate_performance, mock_model_factory, mock_document_metadata):
    """Test fallback to best available model when no model meets the threshold."""
    # Configure mocks
    mock_hybrid_model = mock.MagicMock()
    mock_typed_model = mock.MagicMock()
    mock_handwritten_model = mock.MagicMock()
    
    mock_get_model.side_effect = [
        mock_hybrid_model,      # First call returns hybrid model
        mock_typed_model,       # Second call returns typed model
        mock_handwritten_model  # Third call returns handwritten model
    ]
    
    # Configure performance evaluation (all below threshold)
    mock_evaluate_performance.side_effect = [
        0.85,  # Hybrid model performance (best)
        0.80,  # Typed model performance
        0.78   # Handwritten model performance
    ]
    
    # Select best model with high threshold
    best_model = mock_model_factory.select_best_model(
        mock_document_metadata["tax_return"],
        performance_threshold=0.95
    )
    
    # Check that the best available model was selected
    assert best_model == mock_hybrid_model
    assert mock_get_model.call_count == 3  # Should try all models
    assert mock_evaluate_performance.call_count == 3


# ===== Test Document-Specific Parameters =====

def test_get_parameters_for_document(mock_model_factory):
    """Test getting model parameters optimized for a specific document type."""
    # Get parameters for different document types
    app_params = mock_model_factory._get_parameters_for_document(DocumentType.APPLICATION)
    tax_params = mock_model_factory._get_parameters_for_document(DocumentType.TAX_RETURN)
    bank_params = mock_model_factory._get_parameters_for_document(DocumentType.BANK_STATEMENT)
    id_params = mock_model_factory._get_parameters_for_document(DocumentType.ID_DOCUMENT)
    
    # Check that parameters are document-specific
    assert app_params is not None
    assert tax_params is not None
    assert bank_params is not None
    assert id_params is not None
    
    # Check that parameters have different values
    assert app_params.model_id != tax_params.model_id
    assert app_params.confidence_threshold != tax_params.confidence_threshold
    
    # Check specific parameter values
    assert tax_params.confidence_threshold > app_params.confidence_threshold  # Tax documents need higher confidence
    assert "validate_numbers" in tax_params.postprocessing_steps  # Tax documents need number validation
    assert "validate_id_format" in id_params.postprocessing_steps  # ID documents need format validation


# ===== Test Model Type Determination =====

def test_determine_model_type(mock_model_factory):
    """Test determining the appropriate model type for a document."""
    # Test with explicit content type
    model_type = mock_model_factory._determine_model_type(
        DocumentType.APPLICATION,
        "typed"
    )
    assert model_type == OCRModelType.TYPED.value
    
    # Test with document type only
    model_type = mock_model_factory._determine_model_type(
        DocumentType.TAX_RETURN,
        None
    )
    assert model_type == OCRModelType.TYPED.value
    
    # Test with no document type (should default to hybrid)
    model_type = mock_model_factory._determine_model_type(
        None,
        None
    )
    assert model_type == OCRModelType.HYBRID.value
    
    # Test with additional metadata
    document_type = DocumentType.APPLICATION
    document_type.additional_metadata = {"is_handwritten": True}
    model_type = mock_model_factory._determine_model_type(
        document_type,
        None
    )
    assert model_type == OCRModelType.HANDWRITTEN.value