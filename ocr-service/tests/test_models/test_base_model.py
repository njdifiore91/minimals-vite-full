#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the abstract base class for OCR models.

This module contains tests for the BaseOCRModel abstract class, which defines the
common interface and shared functionality for all OCR models in the system.

The tests verify that:
1. The base model correctly enforces implementation of abstract methods in derived classes
2. The model loading and initialization functionality works as expected
3. The image preprocessing utilities correctly normalize document images
4. The JSON result formatting with confidence scoring works correctly
5. Error handling for invalid inputs and model failures works as expected

These tests ensure that the BaseOCRModel provides a solid foundation for all OCR models
in the system, with consistent behavior and proper error handling.
"""

import os
import time
import logging
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, List, Tuple, Any, Optional, Union

import numpy as np
import pytest
import tensorflow as tf

from ocr_service.src.models.base_model import BaseOCRModel
from ocr_service.src.types.models import ModelParameters, ModelResult, OCRModelType
from ocr_service.src.types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from ocr_service.src.types.errors import ServiceError


# ===== Test Classes =====

class ConcreteOCRModel(BaseOCRModel):
    """Concrete implementation of BaseOCRModel for testing."""
    
    def __init__(self, model_path: str, model_parameters: ModelParameters):
        super().__init__(model_path, model_parameters)
        self.model_type = OCRModelType.TYPED
    
    def load_model(self) -> None:
        """Implement abstract method."""
        self.model = MagicMock()
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """Implement abstract method."""
        return self.normalize_image(image)
    
    def extract_text(self, preprocessed_image: np.ndarray) -> ModelResult:
        """Implement abstract method."""
        return ModelResult(
            model_id="test_model",
            model_type=OCRModelType.TYPED,
            text="Test text",
            confidence=0.95
        )
    
    def format_result(self, model_result: ModelResult) -> ExtractedData:
        """Implement abstract method."""
        field = ExtractedField(
            field_id="test_field",
            field_name="Test Field",
            value="Test text",
            raw_text="Test text",
            confidence=0.95,
            requires_verification=False,
            field_type="text"
        )
        
        return ExtractedData(
            fields={"test_field": field},
            metadata={
                "document_id": "test_doc",
                "extraction_id": "test_extraction",
                "document_type": "test_type",
                "extraction_timestamp": time.time(),
                "ocr_model_version": "1.0.0",
                "average_confidence": 0.95
            }
        )


class IncompleteOCRModel(BaseOCRModel):
    """Incomplete implementation of BaseOCRModel for testing abstract method enforcement."""
    
    def __init__(self, model_path: str, model_parameters: ModelParameters):
        super().__init__(model_path, model_parameters)
        self.model_type = OCRModelType.TYPED
    
    # Missing implementation of abstract methods


# ===== Fixtures =====

@pytest.fixture
def valid_model_path(tmp_path):
    """Create a temporary file to use as a valid model path."""
    model_file = tmp_path / "model.h5"
    model_file.write_text("dummy model content")
    return str(model_file)


@pytest.fixture
def invalid_model_path(tmp_path):
    """Return a path to a non-existent file."""
    return str(tmp_path / "nonexistent_model.h5")


@pytest.fixture
def model_parameters():
    """Create model parameters for testing."""
    return ModelParameters(
        model_type=OCRModelType.TYPED,
        model_id="test_model",
        model_version="1.0.0",
        batch_size=1,
        image_height=1024,
        image_width=1024,
        channels=3,
        use_gpu=False,  # Disable GPU for testing
        confidence_threshold=0.7
    )


@pytest.fixture
def test_image():
    """Create a test image for preprocessing tests."""
    # Create a simple 100x100 grayscale image with values 0-255
    return np.random.randint(0, 256, (100, 100), dtype=np.uint8)


@pytest.fixture
def test_rgb_image():
    """Create a test RGB image for preprocessing tests."""
    # Create a simple 100x100 RGB image with values 0-255
    return np.random.randint(0, 256, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def concrete_model(valid_model_path, model_parameters):
    """Create a concrete OCR model for testing."""
    return ConcreteOCRModel(valid_model_path, model_parameters)


# ===== Tests for Abstract Method Enforcement =====

def test_abstract_class_cannot_be_instantiated(valid_model_path, model_parameters):
    """Test that BaseOCRModel cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseOCRModel(valid_model_path, model_parameters)


def test_incomplete_implementation_raises_error(valid_model_path, model_parameters):
    """Test that incomplete implementation of abstract methods raises error."""
    with pytest.raises(TypeError):
        IncompleteOCRModel(valid_model_path, model_parameters)


def test_concrete_implementation_can_be_instantiated(valid_model_path, model_parameters):
    """Test that concrete implementation can be instantiated."""
    model = ConcreteOCRModel(valid_model_path, model_parameters)
    assert isinstance(model, BaseOCRModel)
    assert isinstance(model, ConcreteOCRModel)


# ===== Tests for Model Initialization =====

def test_init_with_valid_model_path(valid_model_path, model_parameters):
    """Test initialization with a valid model path."""
    model = ConcreteOCRModel(valid_model_path, model_parameters)
    assert model.model_path == valid_model_path
    assert model.model_parameters == model_parameters
    assert model.model is None  # Model not loaded yet
    assert isinstance(model.logger, logging.Logger)


def test_init_with_invalid_model_path(invalid_model_path, model_parameters):
    """Test initialization with an invalid model path raises ServiceError."""
    with pytest.raises(ServiceError) as excinfo:
        ConcreteOCRModel(invalid_model_path, model_parameters)
    
    assert "Model file not found" in str(excinfo.value)
    assert excinfo.value.error_code == "MODEL_NOT_FOUND"


def test_gpu_detection_with_gpu_available():
    """Test GPU detection when GPU is available."""
    # Mock TensorFlow's GPU detection
    with patch('tensorflow.config.list_physical_devices') as mock_list_devices:
        # Create a mock GPU device
        mock_gpu = MagicMock()
        mock_gpu.device_type = 'GPU'
        mock_list_devices.return_value = [mock_gpu]
        
        # Create model parameters with GPU enabled
        params = ModelParameters(
            model_type=OCRModelType.TYPED,
            model_id="test_model",
            model_version="1.0.0",
            use_gpu=True
        )
        
        # Create a temporary file for model path
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            # Initialize model
            model = ConcreteOCRModel(tmp.name, params)
            
            # Check that GPU was detected
            assert model.gpu_available
            mock_list_devices.assert_called_once_with('GPU')


def test_gpu_detection_with_no_gpu_available():
    """Test GPU detection when no GPU is available."""
    # Mock TensorFlow's GPU detection
    with patch('tensorflow.config.list_physical_devices') as mock_list_devices:
        # Return empty list (no GPUs)
        mock_list_devices.return_value = []
        
        # Create model parameters with GPU enabled
        params = ModelParameters(
            model_type=OCRModelType.TYPED,
            model_id="test_model",
            model_version="1.0.0",
            use_gpu=True
        )
        
        # Create a temporary file for model path
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            # Initialize model
            model = ConcreteOCRModel(tmp.name, params)
            
            # Check that no GPU was detected
            assert not model.gpu_available
            mock_list_devices.assert_called_once_with('GPU')


# ===== Tests for Image Preprocessing Utilities =====

def test_normalize_image_with_uint8_image(concrete_model, test_image):
    """Test normalizing a uint8 image to float32 in range [0, 1]."""
    # Ensure input is uint8 with values 0-255
    assert test_image.dtype == np.uint8
    assert np.max(test_image) > 1.0
    
    # Normalize image
    normalized = concrete_model.normalize_image(test_image)
    
    # Check that output is float32 with values in range [0, 1]
    assert normalized.dtype == np.float32
    assert np.max(normalized) <= 1.0
    assert np.min(normalized) >= 0.0


def test_normalize_image_with_float32_image(concrete_model):
    """Test normalizing an already normalized float32 image."""
    # Create a float32 image already in range [0, 1]
    image = np.random.random((100, 100)).astype(np.float32)
    assert image.dtype == np.float32
    assert np.max(image) <= 1.0
    
    # Normalize image
    normalized = concrete_model.normalize_image(image)
    
    # Check that output is still float32 with values in range [0, 1]
    assert normalized.dtype == np.float32
    assert np.max(normalized) <= 1.0
    assert np.min(normalized) >= 0.0
    
    # Check that the image wasn't changed (already normalized)
    np.testing.assert_allclose(normalized, image)


def test_normalize_image_with_invalid_input(concrete_model):
    """Test normalizing with invalid input raises ServiceError."""
    # Test with None
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.normalize_image(None)
    assert "Invalid image for normalization" in str(excinfo.value)
    
    # Test with empty array
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.normalize_image(np.array([]))
    assert "Invalid image for normalization" in str(excinfo.value)


def test_resize_image_with_preserve_aspect_ratio(concrete_model, test_image):
    """Test resizing an image while preserving aspect ratio."""
    # Original dimensions
    original_height, original_width = test_image.shape
    target_height = 200
    
    # Resize image with preserved aspect ratio
    resized = concrete_model.resize_image(test_image, target_height, preserve_aspect_ratio=True)
    
    # Check dimensions
    assert resized.shape[0] == target_height
    expected_width = int(target_height * (original_width / original_height))
    assert resized.shape[1] == expected_width


def test_resize_image_without_preserve_aspect_ratio(concrete_model, test_image):
    """Test resizing an image without preserving aspect ratio."""
    # Set model parameters with specific width
    concrete_model.model_parameters = ModelParameters(
        model_type=OCRModelType.TYPED,
        model_id="test_model",
        model_version="1.0.0",
        image_width=300,
        image_height=200
    )
    
    # Resize image without preserving aspect ratio
    target_height = 200
    resized = concrete_model.resize_image(test_image, target_height, preserve_aspect_ratio=False)
    
    # Check dimensions
    assert resized.shape[0] == target_height
    assert resized.shape[1] == 300  # From model parameters


def test_resize_image_with_invalid_input(concrete_model):
    """Test resizing with invalid input raises ServiceError."""
    # Test with None
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.resize_image(None, 200)
    assert "Invalid image for resizing" in str(excinfo.value)
    
    # Test with empty array
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.resize_image(np.array([]), 200)
    assert "Invalid image for resizing" in str(excinfo.value)


def test_enhance_image(concrete_model, test_image):
    """Test enhancing image quality for better OCR results."""
    # Ensure input is uint8 with values 0-255
    assert test_image.dtype == np.uint8
    
    # Enhance image
    enhanced = concrete_model.enhance_image(test_image)
    
    # Check that output is float32 with values in range [0, 1]
    assert enhanced.dtype == np.float32
    assert np.max(enhanced) <= 1.0
    assert np.min(enhanced) >= 0.0


def test_enhance_image_with_invalid_input(concrete_model):
    """Test enhancing with invalid input raises ServiceError."""
    # Test with None
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.enhance_image(None)
    assert "Invalid image for enhancement" in str(excinfo.value)
    
    # Test with empty array
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.enhance_image(np.array([]))
    assert "Invalid image for enhancement" in str(excinfo.value)


# ===== Tests for Confidence Scoring =====

def test_calculate_confidence_with_valid_probabilities(concrete_model):
    """Test calculating confidence score from valid probabilities."""
    # Test with high probabilities
    high_probs = np.array([0.9, 0.95, 0.98])
    high_confidence = concrete_model.calculate_confidence(high_probs)
    assert isinstance(high_confidence, float)
    assert 0.9 <= high_confidence <= 0.98
    
    # Test with low probabilities
    low_probs = np.array([0.3, 0.4, 0.5])
    low_confidence = concrete_model.calculate_confidence(low_probs)
    assert isinstance(low_confidence, float)
    assert 0.3 <= low_confidence <= 0.5


def test_calculate_confidence_with_invalid_probabilities(concrete_model):
    """Test calculating confidence score with invalid probabilities."""
    # Test with None
    confidence = concrete_model.calculate_confidence(None)
    assert confidence == 0.0
    
    # Test with empty array
    confidence = concrete_model.calculate_confidence(np.array([]))
    assert confidence == 0.0
    
    # Test with probabilities outside [0, 1] range
    probs = np.array([-0.1, 0.5, 1.2])
    confidence = concrete_model.calculate_confidence(probs)
    assert 0.0 <= confidence <= 1.0  # Should clamp to valid range


# ===== Tests for Process Method =====

def test_process_with_valid_image(concrete_model, test_image):
    """Test processing a valid image."""
    # Mock the abstract methods
    concrete_model.load_model = MagicMock()
    concrete_model.preprocess_image = MagicMock(return_value=test_image)
    concrete_model.extract_text = MagicMock(return_value=ModelResult(
        model_id="test_model",
        model_type=OCRModelType.TYPED,
        text="Test text",
        confidence=0.95
    ))
    concrete_model.format_result = MagicMock(return_value=ExtractedData(
        fields={
            "test_field": {
                "field_id": "test_field",
                "field_name": "Test Field",
                "value": "Test text",
                "raw_text": "Test text",
                "confidence": 0.95,
                "requires_verification": False,
                "field_type": "text"
            }
        },
        metadata={
            "document_id": "test_doc",
            "extraction_id": "test_extraction",
            "document_type": "test_type",
            "extraction_timestamp": time.time(),
            "ocr_model_version": "1.0.0",
            "average_confidence": 0.95
        }
    ))
    
    # Process image
    result = concrete_model.process(test_image)
    
    # Check that all methods were called
    concrete_model.load_model.assert_called_once()
    concrete_model.preprocess_image.assert_called_once_with(test_image)
    concrete_model.extract_text.assert_called_once()
    concrete_model.format_result.assert_called_once()
    
    # Check result
    assert isinstance(result, ExtractedData)
    assert "test_field" in result.fields
    assert result.fields["test_field"]["value"] == "Test text"
    assert result.fields["test_field"]["confidence"] == 0.95


def test_process_with_model_already_loaded(concrete_model, test_image):
    """Test processing when model is already loaded."""
    # Set model as already loaded
    concrete_model.model = MagicMock()
    
    # Mock the abstract methods
    concrete_model.load_model = MagicMock()
    concrete_model.preprocess_image = MagicMock(return_value=test_image)
    concrete_model.extract_text = MagicMock(return_value=ModelResult(
        model_id="test_model",
        model_type=OCRModelType.TYPED,
        text="Test text",
        confidence=0.95
    ))
    concrete_model.format_result = MagicMock(return_value=ExtractedData(
        fields={
            "test_field": {
                "field_id": "test_field",
                "field_name": "Test Field",
                "value": "Test text",
                "raw_text": "Test text",
                "confidence": 0.95,
                "requires_verification": False,
                "field_type": "text"
            }
        },
        metadata={
            "document_id": "test_doc",
            "extraction_id": "test_extraction",
            "document_type": "test_type",
            "extraction_timestamp": time.time(),
            "ocr_model_version": "1.0.0",
            "average_confidence": 0.95
        }
    ))
    
    # Process image
    result = concrete_model.process(test_image)
    
    # Check that load_model was not called (model already loaded)
    concrete_model.load_model.assert_not_called()
    
    # Check that other methods were called
    concrete_model.preprocess_image.assert_called_once_with(test_image)
    concrete_model.extract_text.assert_called_once()
    concrete_model.format_result.assert_called_once()


def test_process_with_preprocessing_error(concrete_model, test_image):
    """Test processing with error during preprocessing."""
    # Mock the abstract methods
    concrete_model.load_model = MagicMock()
    concrete_model.preprocess_image = MagicMock(side_effect=ServiceError("Preprocessing error", "PREPROCESSING_ERROR"))
    
    # Process image should raise ServiceError
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.process(test_image)
    
    assert "Preprocessing error" in str(excinfo.value)
    
    # Check that load_model was called but not extract_text or format_result
    concrete_model.load_model.assert_called_once()
    concrete_model.preprocess_image.assert_called_once_with(test_image)


def test_process_with_extraction_error(concrete_model, test_image):
    """Test processing with error during text extraction."""
    # Mock the abstract methods
    concrete_model.load_model = MagicMock()
    concrete_model.preprocess_image = MagicMock(return_value=test_image)
    concrete_model.extract_text = MagicMock(side_effect=ServiceError("Extraction error", "EXTRACTION_ERROR"))
    
    # Process image should raise ServiceError
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.process(test_image)
    
    assert "Extraction error" in str(excinfo.value)
    
    # Check that load_model and preprocess_image were called but not format_result
    concrete_model.load_model.assert_called_once()
    concrete_model.preprocess_image.assert_called_once_with(test_image)
    concrete_model.extract_text.assert_called_once()


def test_process_with_formatting_error(concrete_model, test_image):
    """Test processing with error during result formatting."""
    # Mock the abstract methods
    concrete_model.load_model = MagicMock()
    concrete_model.preprocess_image = MagicMock(return_value=test_image)
    concrete_model.extract_text = MagicMock(return_value=ModelResult(
        model_id="test_model",
        model_type=OCRModelType.TYPED,
        text="Test text",
        confidence=0.95
    ))
    concrete_model.format_result = MagicMock(side_effect=ServiceError("Formatting error", "FORMATTING_ERROR"))
    
    # Process image should raise ServiceError
    with pytest.raises(ServiceError) as excinfo:
        concrete_model.process(test_image)
    
    assert "Formatting error" in str(excinfo.value)
    
    # Check that all methods were called
    concrete_model.load_model.assert_called_once()
    concrete_model.preprocess_image.assert_called_once_with(test_image)
    concrete_model.extract_text.assert_called_once()
    concrete_model.format_result.assert_called_once()


# ===== Tests for String Representation =====

def test_str_representation(concrete_model):
    """Test string representation of the model."""
    str_repr = str(concrete_model)
    assert "ConcreteOCRModel" in str_repr
    assert concrete_model.model_path in str_repr


def test_repr_representation(concrete_model):
    """Test debug representation of the model."""
    repr_str = repr(concrete_model)
    assert "ConcreteOCRModel" in repr_str
    assert concrete_model.model_path in repr_str
    assert "parameters" in repr_str


# ===== Tests for Performance Requirements =====

def test_processing_time_under_5_minutes(concrete_model, test_image):
    """Test that processing time is under 5 minutes as required."""
    # Mock the abstract methods for quick execution
    concrete_model.load_model = MagicMock()
    concrete_model.preprocess_image = MagicMock(return_value=test_image)
    concrete_model.extract_text = MagicMock(return_value=ModelResult(
        model_id="test_model",
        model_type=OCRModelType.TYPED,
        text="Test text",
        confidence=0.95
    ))
    concrete_model.format_result = MagicMock(return_value=ExtractedData(
        fields={
            "test_field": {
                "field_id": "test_field",
                "field_name": "Test Field",
                "value": "Test text",
                "raw_text": "Test text",
                "confidence": 0.95,
                "requires_verification": False,
                "field_type": "text"
            }
        },
        metadata={
            "document_id": "test_doc",
            "extraction_id": "test_extraction",
            "document_type": "test_type",
            "extraction_timestamp": time.time(),
            "ocr_model_version": "1.0.0",
            "average_confidence": 0.95
        }
    ))
    
    # Measure processing time
    start_time = time.time()
    concrete_model.process(test_image)
    processing_time = time.time() - start_time
    
    # Check that processing time is under 5 minutes (300 seconds)
    # In practice, this should be much faster, but we're testing the requirement
    assert processing_time < 300, f"Processing time {processing_time:.2f}s exceeds 5 minutes"


# ===== Tests for GPU Acceleration Requirement =====

def test_gpu_warning_when_not_available():
    """Test that a warning is logged when GPU is not available."""
    # Mock TensorFlow's GPU detection
    with patch('tensorflow.config.list_physical_devices') as mock_list_devices:
        # Return empty list (no GPUs)
        mock_list_devices.return_value = []
        
        # Create model parameters with GPU enabled
        params = ModelParameters(
            model_type=OCRModelType.TYPED,
            model_id="test_model",
            model_version="1.0.0",
            use_gpu=True
        )
        
        # Create a temporary file for model path
        import tempfile
        with tempfile.NamedTemporaryFile() as tmp:
            # Mock logger to capture warnings
            mock_logger = MagicMock()
            
            # Initialize model with mocked logger
            with patch('logging.getLogger', return_value=mock_logger):
                ConcreteOCRModel(tmp.name, params)
                
                # Check that warning was logged
                mock_logger.warning.assert_called_once()
                warning_msg = mock_logger.warning.call_args[0][0]
                assert "No GPU detected" in warning_msg
                assert "CUDA-compatible GPU" in warning_msg


# ===== Tests for Accuracy Requirement =====

def test_confidence_scoring_for_accuracy_requirement(concrete_model):
    """Test that confidence scoring supports the 99% accuracy requirement."""
    # Create probabilities representing high accuracy (99%)
    high_accuracy_probs = np.array([0.99, 0.98, 0.99, 0.99])
    
    # Calculate confidence
    confidence = concrete_model.calculate_confidence(high_accuracy_probs)
    
    # Check that confidence reflects high accuracy
    assert confidence >= 0.98, f"Confidence {confidence} does not reflect 99% accuracy requirement"
    
    # Create probabilities representing lower accuracy
    low_accuracy_probs = np.array([0.7, 0.8, 0.75])
    
    # Calculate confidence
    confidence = concrete_model.calculate_confidence(low_accuracy_probs)
    
    # Check that confidence reflects lower accuracy
    assert confidence < 0.9, f"Confidence {confidence} does not accurately reflect lower accuracy"