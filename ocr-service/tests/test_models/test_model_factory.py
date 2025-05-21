#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the OCR Model Factory.

This module contains tests for the ModelFactory class that creates and returns
appropriate OCR models based on document type and classification metadata.

These tests verify that the factory correctly selects models, initializes them
with proper configuration, and implements caching for performance optimization.
"""

import os
import time
import unittest.mock as mock
from typing import Dict, Any

import pytest

from src.models.model_factory import (
    ModelFactory,
    get_model_for_document,
    get_model,
    get_model_by_document_type,
    clear_model_cache
)
from src.types.documents import DocumentMetadata, DocumentType
from src.types.models import OCRModelType, ModelParameters, TensorFlowModel


# Mock configuration for testing
@pytest.fixture
def mock_config():
    """Create a mock configuration for testing."""
    return mock.MagicMock(
        global_={
            "batch_size": 2,
            "confidence_threshold": 0.75,
        },
        typed_model={
            "model_path": "/mock/typed_model",
            "batch_size": 4,
        },
        handwritten_model={
            "model_path": "/mock/handwritten_model",
            "batch_size": 2,
        },
        hybrid_model={
            "model_path": "/mock/hybrid_model",
            "batch_size": 1,
        }
    )


# Mock document metadata for testing
@pytest.fixture
def typed_document_metadata():
    """Create mock metadata for a typed document."""
    return DocumentMetadata(
        filename="tax_return.pdf",
        size=1024,
        mime_type="application/pdf",
        document_type=DocumentType.TAX_RETURN,
        additional_metadata={
            "has_handwriting": False,
            "image_quality": 0.9,
            "language": "en",
            "priority": "high"
        }
    )


@pytest.fixture
def handwritten_document_metadata():
    """Create mock metadata for a handwritten document."""
    return DocumentMetadata(
        filename="handwritten_note.jpg",
        size=512,
        mime_type="image/jpeg",
        document_type=DocumentType.OTHER,
        additional_metadata={
            "has_handwriting": True,
            "image_quality": 0.7,
            "language": "en",
            "priority": "medium"
        }
    )


@pytest.fixture
def hybrid_document_metadata():
    """Create mock metadata for a document with mixed content."""
    return DocumentMetadata(
        filename="application_form.pdf",
        size=2048,
        mime_type="application/pdf",
        document_type=DocumentType.APPLICATION,
        additional_metadata={
            "has_handwriting": None,  # Unknown if it has handwriting
            "image_quality": 0.8,
            "language": "en",
            "priority": "high"
        }
    )


@pytest.fixture
def unknown_document_metadata():
    """Create mock metadata for a document with unknown type."""
    return DocumentMetadata(
        filename="unknown_document.pdf",
        size=1536,
        mime_type="application/pdf",
        document_type=None,  # Unknown document type
        additional_metadata={
            "image_quality": 0.6,
            "language": "en",
            "priority": "low"
        }
    )


# Mock TensorFlow model for testing
class MockTensorFlowModel(TensorFlowModel):
    """Mock implementation of TensorFlowModel for testing."""
    
    def __init__(self, parameters: ModelParameters):
        self.parameters = parameters
        self.model = None
        self.metrics = None
        self.loaded = False
    
    def load(self) -> bool:
        """Mock implementation of model loading."""
        self.loaded = True
        return True


# Test class for ModelFactory
class TestModelFactory:
    """Tests for the ModelFactory class."""
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_initialization(self, mock_tf_config, mock_config):
        """Test that the factory initializes correctly."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        
        # Execute
        factory = ModelFactory()
        
        # Verify
        assert factory is not None
        mock_tf_config.get_model_config.assert_called_once()
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_singleton_pattern(self, mock_tf_config, mock_config):
        """Test that the factory implements the singleton pattern."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        
        # Execute
        factory1 = ModelFactory()
        factory2 = ModelFactory()
        
        # Verify
        assert factory1 is factory2
        # Config should only be loaded once
        assert mock_tf_config.get_model_config.call_count == 1
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_typed(self, mock_tf_config, mock_config):
        """Test getting a typed text model."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model(OCRModelType.TYPED)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        assert model.loaded
        assert model.parameters['model_type'] == OCRModelType.TYPED.value
        # Batch size should be overridden from config
        assert model.parameters['batch_size'] == 4
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_handwritten(self, mock_tf_config, mock_config):
        """Test getting a handwritten text model."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model(OCRModelType.HANDWRITTEN)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        assert model.loaded
        assert model.parameters['model_type'] == OCRModelType.HANDWRITTEN.value
        # Batch size should be overridden from config
        assert model.parameters['batch_size'] == 2
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_hybrid(self, mock_tf_config, mock_config):
        """Test getting a hybrid text model."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model(OCRModelType.HYBRID)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        assert model.loaded
        assert model.parameters['model_type'] == OCRModelType.HYBRID.value
        # Batch size should be overridden from config
        assert model.parameters['batch_size'] == 1
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_invalid_type(self, mock_tf_config, mock_config):
        """Test getting a model with an invalid type."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute and verify
        with pytest.raises(ValueError):
            factory.get_model("invalid_type")
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_model_caching(self, mock_tf_config, mock_config):
        """Test that models are cached for performance."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model1 = factory.get_model(OCRModelType.TYPED)
        model2 = factory.get_model(OCRModelType.TYPED)
        
        # Verify
        assert model1 is model2  # Should be the same instance (cached)
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_clear_cache(self, mock_tf_config, mock_config):
        """Test clearing the model cache."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        model1 = factory.get_model(OCRModelType.TYPED)
        
        # Execute
        factory.clear_cache()
        model2 = factory.get_model(OCRModelType.TYPED)
        
        # Verify
        assert model1 is not model2  # Should be different instances after cache clear
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_for_document_typed(self, mock_tf_config, mock_config, typed_document_metadata):
        """Test getting a model for a typed document."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model_for_document(typed_document_metadata)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        assert model.parameters['model_type'] == OCRModelType.TYPED.value
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_for_document_handwritten(self, mock_tf_config, mock_config, handwritten_document_metadata):
        """Test getting a model for a handwritten document."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model_for_document(handwritten_document_metadata)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        assert model.parameters['model_type'] == OCRModelType.HANDWRITTEN.value
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_for_document_hybrid(self, mock_tf_config, mock_config, hybrid_document_metadata):
        """Test getting a model for a document with mixed content."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model_for_document(hybrid_document_metadata)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        assert model.parameters['model_type'] == OCRModelType.HYBRID.value
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_for_document_unknown(self, mock_tf_config, mock_config, unknown_document_metadata):
        """Test getting a model for a document with unknown type."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute
        model = factory.get_model_for_document(unknown_document_metadata)
        
        # Verify
        assert model is not None
        assert isinstance(model, MockTensorFlowModel)
        # Should default to hybrid model for unknown document types
        assert model.parameters['model_type'] == OCRModelType.HYBRID.value
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_get_model_by_document_type(self, mock_tf_config, mock_config):
        """Test getting a model by document type."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Execute and verify
        # Tax returns should use typed model
        model = factory.get_model_by_document_type(DocumentType.TAX_RETURN)
        assert model.parameters['model_type'] == OCRModelType.TYPED.value
        
        # Applications should use hybrid model
        model = factory.get_model_by_document_type(DocumentType.APPLICATION)
        assert model.parameters['model_type'] == OCRModelType.HYBRID.value
        
        # String document types should also work
        model = factory.get_model_by_document_type("TAX_RETURN")
        assert model.parameters['model_type'] == OCRModelType.TYPED.value
        
        # Unknown document types should default to hybrid
        model = factory.get_model_by_document_type("UNKNOWN_TYPE")
        assert model.parameters['model_type'] == OCRModelType.HYBRID.value
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_model_loading_error(self, mock_tf_config, mock_config):
        """Test error handling when model loading fails."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Mock TensorFlowModel to raise an exception during loading
        with mock.patch('src.models.model_factory.TensorFlowModel.load', side_effect=Exception("Model loading failed")):
            # Execute and verify
            with pytest.raises(RuntimeError):
                factory.get_model(OCRModelType.TYPED)
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_environment_variable_override(self, mock_tf_config, mock_config, monkeypatch):
        """Test that environment variables can override model paths."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Set environment variable to override model path
        monkeypatch.setenv("OCR_MODEL_DIR", "/custom/models")
        
        # Execute
        model = factory.get_model(OCRModelType.TYPED)
        
        # Verify
        assert "/custom/models" in model.parameters['model_path']
        assert "/custom/models" in model.parameters['vocab_path']
    
    @mock.patch('ocr_service.src.models.model_factory.tensorflow_config')
    @mock.patch('ocr_service.src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_performance_impact_of_caching(self, mock_tf_config, mock_config):
        """Test the performance impact of model caching."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        factory = ModelFactory()
        
        # Clear any existing cache
        factory.clear_cache()
        
        # Measure time to load model first time (uncached)
        start_time = time.time()
        model1 = factory.get_model(OCRModelType.TYPED)
        first_load_time = time.time() - start_time
        
        # Measure time to load model second time (cached)
        start_time = time.time()
        model2 = factory.get_model(OCRModelType.TYPED)
        cached_load_time = time.time() - start_time
        
        # Verify
        assert model1 is model2  # Should be the same instance (cached)
        assert cached_load_time < first_load_time  # Cached access should be faster
        
        # The performance improvement should be significant (at least 10x faster)
        # This is a reasonable expectation for in-memory caching vs. model loading
        assert first_load_time > cached_load_time * 10
    
    @mock.patch('src.models.model_factory.tensorflow_config')
    @mock.patch('src.models.model_factory.TensorFlowModel', MockTensorFlowModel)
    def test_convenience_functions(self, mock_tf_config, mock_config, typed_document_metadata):
        """Test the convenience functions for accessing models."""
        # Setup
        mock_tf_config.get_model_config.return_value = mock_config
        
        # Execute and verify
        # Test get_model_for_document
        model = get_model_for_document(typed_document_metadata)
        assert model is not None
        assert model.parameters['model_type'] == OCRModelType.TYPED.value
        
        # Test get_model
        model = get_model(OCRModelType.HANDWRITTEN)
        assert model is not None
        assert model.parameters['model_type'] == OCRModelType.HANDWRITTEN.value
        
        # Test get_model_by_document_type
        model = get_model_by_document_type(DocumentType.APPLICATION)
        assert model is not None
        assert model.parameters['model_type'] == OCRModelType.HYBRID.value
        
        # Test clear_model_cache
        model1 = get_model(OCRModelType.TYPED)
        clear_model_cache()
        model2 = get_model(OCRModelType.TYPED)
        assert model1 is not model2  # Should be different instances after cache clear


# Run the tests
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])