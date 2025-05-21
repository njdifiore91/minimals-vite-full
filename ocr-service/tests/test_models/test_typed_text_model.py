#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the TypedTextModel class.

This module contains tests for the specialized TensorFlow model for recognizing
and extracting typed/printed text from documents. It verifies that the model
correctly processes typed documents, extracts text with high accuracy, and
provides confidence scores for the extracted data.

Key test areas:
- Typed text recognition accuracy on standard documents
- Text line detection and segmentation algorithms
- Character recognition with language model correction
- Field extraction based on document structure
- Preprocessing for typed document enhancement
- Performance metrics for typed text extraction
"""

import os
import time
import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any

# Import the model to test
from src.models.typed_text_model import TypedTextModel

# Import types
from src.types.models import OCRModelType, ModelParameters, ModelResult
from src.types.documents import DocumentType
from src.types.extraction import ExtractedData


# ===== Test Fixtures =====

@pytest.fixture
def mock_image() -> np.ndarray:
    """Provides a mock image for testing."""
    # Create a simple 100x100 grayscale image with some "text-like" features
    image = np.ones((100, 100), dtype=np.uint8) * 255
    
    # Add some horizontal lines to simulate text
    image[20:22, 10:90] = 0  # Line 1
    image[40:42, 20:80] = 0  # Line 2
    image[60:62, 15:85] = 0  # Line 3
    image[80:82, 25:75] = 0  # Line 4
    
    return image


@pytest.fixture
def mock_document_image() -> np.ndarray:
    """Provides a more complex mock document image for testing."""
    # Create a 500x700 grayscale image (typical document size)
    image = np.ones((700, 500), dtype=np.uint8) * 255
    
    # Add a form-like structure with text lines
    # Header
    image[50:55, 100:400] = 0  # Title underline
    
    # Form fields (labels and values)
    field_positions = [
        (100, 150, "Name:"),
        (100, 200, "Address:"),
        (100, 250, "Phone:"),
        (100, 300, "Email:"),
        (100, 350, "Business Name:"),
        (100, 400, "Tax ID:"),
        (100, 450, "Revenue:"),
    ]
    
    # Simulate text by drawing horizontal lines
    for y_pos, x_end, _ in field_positions:
        # Label
        image[y_pos:y_pos+2, 100:180] = 0
        # Value
        image[y_pos:y_pos+2, 200:x_end] = 0
    
    # Add some "checkbox" elements
    checkbox_positions = [(150, 500), (250, 500), (350, 500)]
    for x, y in checkbox_positions:
        image[y:y+15, x:x+15] = 0  # Box outline
    
    return image


@pytest.fixture
def typed_model(typed_model_parameters) -> TypedTextModel:
    """Provides a TypedTextModel instance for testing."""
    model = TypedTextModel(typed_model_parameters)
    # Mock the load_model method to avoid actual model loading
    model.load_model = MagicMock(return_value=True)
    model.is_initialized = True
    model.model = MagicMock()
    return model


# ===== Test Model Initialization =====

def test_typed_model_initialization(typed_model_parameters):
    """Test that the TypedTextModel initializes correctly with the given parameters."""
    model = TypedTextModel(typed_model_parameters)
    
    # Check that model parameters are set correctly
    assert model.parameters == typed_model_parameters
    assert model.model_type == OCRModelType.TYPED
    assert model.is_initialized is False
    
    # Check that typed-specific parameters are set
    assert hasattr(model, 'line_height_threshold')
    assert hasattr(model, 'char_width_threshold')
    assert hasattr(model, 'language_model_weight')


def test_typed_model_default_parameters():
    """Test that the TypedTextModel initializes with default parameters when none are provided."""
    # Mock the DEFAULT_TYPED_MODEL_PARAMS import
    default_params = {
        'model_type': OCRModelType.TYPED.value,
        'confidence_threshold': 0.75,
        'batch_size': 1,
        'input_shape': (768, 768, 1),
        'language': 'en'
    }
    
    with patch('src.models.typed_text_model.DEFAULT_TYPED_MODEL_PARAMS', default_params):
        model = TypedTextModel()
        
        # Check that default parameters are used
        assert model.parameters['model_type'] == OCRModelType.TYPED.value
        assert model.parameters['confidence_threshold'] == 0.75
        assert model.parameters['batch_size'] == 1


# ===== Test Preprocessing =====

def test_preprocess_typed_image(typed_model, mock_image):
    """Test that the preprocess method correctly enhances typed text images."""
    # Mock the utility functions to isolate the test
    with patch('src.models.typed_text_model.preprocess_for_ocr', return_value=mock_image), \
         patch('src.models.typed_text_model.enhance_contrast', return_value=mock_image), \
         patch('src.models.typed_text_model.normalize_orientation', return_value=mock_image), \
         patch('src.models.typed_text_model.deskew_image', return_value=mock_image), \
         patch('src.models.typed_text_model.sharpen_image', return_value=mock_image), \
         patch('src.models.typed_text_model.binarize_image', return_value=mock_image):
        
        # Process the image
        result = typed_model.preprocess(mock_image)
        
        # Check that the result is a numpy array with the expected shape
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == typed_model.parameters.get('input_shape', (768, 768, 1))[0]
        assert result.shape[1] == typed_model.parameters.get('input_shape', (768, 768, 1))[1]


def test_preprocess_handles_color_images(typed_model):
    """Test that the preprocess method correctly handles color images."""
    # Create a simple color image (RGB)
    color_image = np.ones((100, 100, 3), dtype=np.uint8) * 255
    
    # Mock the utility functions to isolate the test
    with patch('src.models.typed_text_model.preprocess_for_ocr', return_value=color_image), \
         patch('src.models.typed_text_model.enhance_contrast', return_value=color_image), \
         patch('src.models.typed_text_model.normalize_orientation', return_value=color_image), \
         patch('src.models.typed_text_model.deskew_image', return_value=color_image), \
         patch('src.models.typed_text_model.sharpen_image', return_value=color_image), \
         patch('src.models.typed_text_model.binarize_image', return_value=np.ones((100, 100), dtype=np.uint8)):
        
        # Process the image
        result = typed_model.preprocess(color_image)
        
        # Check that the result is a numpy array with the expected shape
        assert isinstance(result, np.ndarray)
        assert result.shape[0] == typed_model.parameters.get('input_shape', (768, 768, 1))[0]
        assert result.shape[1] == typed_model.parameters.get('input_shape', (768, 768, 1))[1]


def test_preprocess_error_handling(typed_model):
    """Test that the preprocess method handles errors gracefully."""
    # Mock the utility function to raise an exception
    with patch('src.models.typed_text_model.preprocess_for_ocr', side_effect=Exception("Test error")):
        # Create a simple image
        image = np.ones((100, 100), dtype=np.uint8) * 255
        
        # Process the image - should not raise an exception
        result = typed_model.preprocess(image)
        
        # Should return the original image as fallback
        assert np.array_equal(result, image)


# ===== Test Text Line Detection =====

def test_detect_text_lines(typed_model, mock_document_image):
    """Test that the detect_text_lines method correctly identifies text lines in an image."""
    # Mock the utility functions to isolate the test
    with patch('src.models.typed_text_model.binarize_image', return_value=mock_document_image), \
         patch('src.models.typed_text_model.detect_text_regions', return_value=[
             (100, 150, 300, 2),  # x, y, width, height
             (100, 200, 300, 2),
             (100, 250, 300, 2),
             (100, 300, 300, 2),
             (100, 350, 300, 2),
             (100, 400, 300, 2),
             (100, 450, 300, 2),
         ]):
        
        # Detect text lines
        text_lines = typed_model.detect_text_lines(mock_document_image)
        
        # Check that text lines were detected
        assert len(text_lines) == 7
        
        # Check the structure of the text line information
        for line in text_lines:
            assert "id" in line
            assert "bbox" in line
            assert "image" in line
            assert "text" in line
            assert "confidence" in line
            
            # Check that the bounding box has the expected format
            assert len(line["bbox"]) == 4  # x, y, width, height


def test_detect_text_lines_filters_small_regions(typed_model, mock_document_image):
    """Test that the detect_text_lines method filters out very small regions."""
    # Mock the utility functions to return some small regions
    with patch('src.models.typed_text_model.binarize_image', return_value=mock_document_image), \
         patch('src.models.typed_text_model.detect_text_regions', return_value=[
             (100, 150, 300, 20),  # Normal size - should be included
             (100, 200, 10, 5),    # Too small - should be filtered out
             (100, 250, 5, 15),    # Too narrow - should be filtered out
             (100, 300, 300, 8),   # Too short - should be filtered out
             (100, 350, 300, 15),  # Normal size - should be included
         ]):
        
        # Set thresholds to filter out small regions
        typed_model.line_height_threshold = 10
        typed_model.char_width_threshold = 5
        
        # Detect text lines
        text_lines = typed_model.detect_text_lines(mock_document_image)
        
        # Check that only the normal-sized regions were included
        assert len(text_lines) == 2
        
        # Check that the bounding boxes match the expected regions
        assert text_lines[0]["bbox"] == (100, 150, 300, 20)
        assert text_lines[1]["bbox"] == (100, 350, 300, 15)


def test_detect_text_lines_error_handling(typed_model):
    """Test that the detect_text_lines method handles errors gracefully."""
    # Mock the utility function to raise an exception
    with patch('src.models.typed_text_model.binarize_image', side_effect=Exception("Test error")):
        # Create a simple image
        image = np.ones((100, 100), dtype=np.uint8) * 255
        
        # Detect text lines - should not raise an exception
        text_lines = typed_model.detect_text_lines(image)
        
        # Should return an empty list
        assert text_lines == []


# ===== Test Character Segmentation =====

def test_segment_characters(typed_model):
    """Test that the segment_characters method correctly identifies characters in a text line."""
    # Create a simple line image with some "character-like" features
    line_image = np.ones((20, 200), dtype=np.uint8) * 255
    
    # Add some vertical lines to simulate characters
    for i in range(5):
        x_pos = 20 + i * 30
        line_image[5:15, x_pos:x_pos+10] = 0  # Character i
    
    # Mock the OpenCV functions
    with patch('cv2.threshold', return_value=(None, line_image)), \
         patch('cv2.findContours', return_value=([
             np.array([[[20, 5], [30, 5], [30, 15], [20, 15]]]),  # Character 1
             np.array([[[50, 5], [60, 5], [60, 15], [50, 15]]]),  # Character 2
             np.array([[[80, 5], [90, 5], [90, 15], [80, 15]]]),  # Character 3
             np.array([[[110, 5], [120, 5], [120, 15], [110, 15]]]),  # Character 4
             np.array([[[140, 5], [150, 5], [150, 15], [140, 15]]]),  # Character 5
             np.array([[[5, 2], [7, 2], [7, 3], [5, 3]]]),  # Noise (too small)
         ], None)):
        
        # Segment characters
        characters = typed_model.segment_characters(line_image)
        
        # Check that characters were detected (excluding noise)
        assert len(characters) == 5
        
        # Check the structure of the character information
        for char in characters:
            assert "id" in char
            assert "bbox" in char
            assert "image" in char
            assert "char" in char
            assert "confidence" in char
            
            # Check that the bounding box has the expected format
            assert len(char["bbox"]) == 4  # x, y, width, height


def test_segment_characters_filters_small_contours(typed_model):
    """Test that the segment_characters method filters out very small contours (noise)."""
    # Create a simple line image
    line_image = np.ones((20, 200), dtype=np.uint8) * 255
    
    # Mock the OpenCV functions to return some small contours
    with patch('cv2.threshold', return_value=(None, line_image)), \
         patch('cv2.findContours', return_value=([
             np.array([[[20, 5], [30, 5], [30, 15], [20, 15]]]),  # Normal size - should be included
             np.array([[[50, 5], [52, 5], [52, 7], [50, 7]]]),   # Too small - should be filtered out
             np.array([[[80, 5], [82, 5], [82, 15], [80, 15]]]),  # Too narrow - should be filtered out
             np.array([[[110, 5], [120, 5], [120, 7], [110, 7]]]),  # Too short - should be filtered out
             np.array([[[140, 5], [150, 5], [150, 15], [140, 15]]]),  # Normal size - should be included
         ], None)):
        
        # Set thresholds to filter out small contours
        typed_model.char_width_threshold = 5
        typed_model.line_height_threshold = 10
        
        # Mock the boundingRect function to return the expected values
        with patch('cv2.boundingRect', side_effect=[
            (20, 5, 10, 10),   # Normal size
            (50, 5, 2, 2),      # Too small
            (80, 5, 2, 10),     # Too narrow
            (110, 5, 10, 2),    # Too short
            (140, 5, 10, 10),   # Normal size
        ]):
            # Segment characters
            characters = typed_model.segment_characters(line_image)
            
            # Check that only the normal-sized characters were included
            assert len(characters) == 2
            
            # Check that the bounding boxes match the expected regions
            assert characters[0]["bbox"] == (20, 5, 10, 10)
            assert characters[1]["bbox"] == (140, 5, 10, 10)


def test_segment_characters_error_handling(typed_model):
    """Test that the segment_characters method handles errors gracefully."""
    # Mock the OpenCV function to raise an exception
    with patch('cv2.threshold', side_effect=Exception("Test error")):
        # Create a simple line image
        line_image = np.ones((20, 200), dtype=np.uint8) * 255
        
        # Segment characters - should not raise an exception
        characters = typed_model.segment_characters(line_image)
        
        # Should return an empty list
        assert characters == []


# ===== Test Language Model Correction =====

def test_apply_language_model_correction(typed_model):
    """Test that the apply_language_model_correction method improves OCR accuracy."""
    # Mock the text_utils.correct_ocr_errors function
    with patch('src.models.typed_text_model.correct_ocr_errors', return_value=("corrected text", 0.95)):
        # Apply language model correction
        text = "raw text with erors"
        confidence = 0.8
        
        corrected_text, adjusted_confidence = typed_model.apply_language_model_correction(text, confidence)
        
        # Check that the text was corrected
        assert corrected_text == "corrected text"
        
        # Check that the confidence was adjusted based on the language model weight
        expected_confidence = (1 - typed_model.language_model_weight) * confidence + \
                             typed_model.language_model_weight * 0.95
        assert adjusted_confidence == expected_confidence


def test_apply_language_model_correction_error_handling(typed_model):
    """Test that the apply_language_model_correction method handles errors gracefully."""
    # Mock the text_utils.correct_ocr_errors function to raise an exception
    with patch('src.models.typed_text_model.correct_ocr_errors', side_effect=Exception("Test error")):
        # Apply language model correction
        text = "raw text with erors"
        confidence = 0.8
        
        # Should not raise an exception
        corrected_text, adjusted_confidence = typed_model.apply_language_model_correction(text, confidence)
        
        # Should return the original text and confidence
        assert corrected_text == text
        assert adjusted_confidence == confidence


# ===== Test Text Extraction =====

def test_extract_text(typed_model, mock_document_image):
    """Test that the extract_text method correctly extracts text from an image."""
    # Mock the necessary methods and functions
    with patch.object(typed_model, 'preprocess', return_value=mock_document_image), \
         patch('src.models.typed_text_model.run_inference', return_value=(np.random.rand(1, 10, 50), {
             'confidence_scores': {'overall': 0.9}
         })), \
         patch.object(typed_model, '_decode_model_output', return_value="Sample extracted text"), \
         patch.object(typed_model, 'apply_language_model_correction', return_value=("Corrected sample text", 0.92)):
        
        # Extract text
        result = typed_model.extract_text(mock_document_image)
        
        # Check that the result has the expected structure
        assert isinstance(result, dict)
        assert "text" in result
        assert "confidence" in result
        assert "bounding_boxes" in result
        assert "word_confidences" in result
        assert "processing_time" in result
        assert "page_number" in result
        assert "model_type" in result
        assert "warnings" in result
        assert "language" in result
        
        # Check the extracted text
        assert result["text"] == "Corrected sample text"
        assert result["confidence"] == 0.92
        assert len(result["bounding_boxes"]) > 0
        assert len(result["word_confidences"]) > 0
        assert result["model_type"] == OCRModelType.TYPED.value


def test_extract_text_loads_model_if_needed(typed_model, mock_document_image):
    """Test that the extract_text method loads the model if it's not initialized."""
    # Set the model as not initialized
    typed_model.is_initialized = False
    
    # Mock the necessary methods and functions
    with patch.object(typed_model, 'load_model', return_value=True) as mock_load, \
         patch.object(typed_model, 'preprocess', return_value=mock_document_image), \
         patch('src.models.typed_text_model.run_inference', return_value=(np.random.rand(1, 10, 50), {
             'confidence_scores': {'overall': 0.9}
         })), \
         patch.object(typed_model, '_decode_model_output', return_value="Sample extracted text"), \
         patch.object(typed_model, 'apply_language_model_correction', return_value=("Corrected sample text", 0.92)):
        
        # Extract text
        result = typed_model.extract_text(mock_document_image)
        
        # Check that the model was loaded
        mock_load.assert_called_once()
        
        # Check that the result has the expected structure
        assert isinstance(result, dict)
        assert result["text"] == "Corrected sample text"


def test_extract_text_handles_model_load_failure(typed_model, mock_document_image):
    """Test that the extract_text method handles model loading failures."""
    # Set the model as not initialized
    typed_model.is_initialized = False
    
    # Mock the load_model method to fail
    with patch.object(typed_model, 'load_model', return_value=False):
        # Extract text - should raise a RuntimeError
        with pytest.raises(RuntimeError):
            typed_model.extract_text(mock_document_image)


def test_extract_text_handles_inference_failure(typed_model, mock_document_image):
    """Test that the extract_text method handles inference failures."""
    # Mock the necessary methods and functions
    with patch.object(typed_model, 'preprocess', return_value=mock_document_image), \
         patch('src.models.typed_text_model.run_inference', return_value=(None, {
             'error': 'Inference failed'
         })):
        
        # Extract text - should raise a RuntimeError
        with pytest.raises(RuntimeError):
            typed_model.extract_text(mock_document_image)


def test_extract_text_error_handling(typed_model, mock_document_image):
    """Test that the extract_text method handles general errors gracefully."""
    # Mock the preprocess method to raise an exception
    with patch.object(typed_model, 'preprocess', side_effect=Exception("Test error")):
        # Extract text - should not raise an exception
        result = typed_model.extract_text(mock_document_image)
        
        # Should return an empty result with error
        assert result["text"] == ""
        assert result["confidence"] == 0.0
        assert len(result["warnings"]) > 0
        assert "Test error" in result["warnings"][0]


# ===== Test Model Output Decoding =====

def test_decode_model_output_with_vocab_file(typed_model):
    """Test that the _decode_model_output method correctly decodes model output using a vocabulary file."""
    # Create a temporary vocabulary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("\n".join([" ", "a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]))
        vocab_path = f.name
    
    try:
        # Set the vocabulary path in the model parameters
        typed_model.parameters['vocab_path'] = vocab_path
        
        # Create a sample model output (character probabilities)
        # Shape: [batch_size, sequence_length, vocab_size]
        output = np.zeros((1, 5, 11))  # 11 characters in the vocabulary
        
        # Set the highest probability for each position to spell "hello"
        output[0, 0, 8] = 1.0  # h
        output[0, 1, 5] = 1.0  # e
        output[0, 2, 10] = 1.0  # j (should be l, but we only have a-j)
        output[0, 3, 10] = 1.0  # j (should be l, but we only have a-j)
        output[0, 4, 9] = 1.0  # i (should be o, but we only have a-j)
        
        # Mock the clean_text function to return the input unchanged
        with patch('src.models.typed_text_model.clean_text', lambda x: x):
            # Decode the output
            text = typed_model._decode_model_output(output)
            
            # Check that the text was decoded correctly
            assert text == "hejji"
    finally:
        # Clean up the temporary file
        os.unlink(vocab_path)


def test_decode_model_output_with_fallback_vocab(typed_model):
    """Test that the _decode_model_output method uses a fallback vocabulary when no file is specified."""
    # Set an invalid vocabulary path
    typed_model.parameters['vocab_path'] = "/nonexistent/path"
    
    # Create a sample model output (character probabilities)
    # Shape: [batch_size, sequence_length, vocab_size]
    # We'll use a small subset of the fallback vocabulary
    output = np.zeros((1, 5, 10))
    
    # Set the highest probability for each position to spell "hello"
    # Using indices that would correspond to these letters in the fallback vocab
    output[0, 0, 8] = 1.0  # h
    output[0, 1, 5] = 1.0  # e
    output[0, 2, 1] = 1.0  # a (not l, but we're testing the mechanism)
    output[0, 3, 1] = 1.0  # a (not l, but we're testing the mechanism)
    output[0, 4, 2] = 1.0  # b (not o, but we're testing the mechanism)
    
    # Mock the clean_text function to return the input unchanged
    with patch('src.models.typed_text_model.clean_text', lambda x: x):
        # Decode the output
        text = typed_model._decode_model_output(output)
        
        # The exact output depends on the fallback vocabulary implementation
        # We just check that it returned a string of the expected length
        assert isinstance(text, str)
        assert len(text) == 5


def test_decode_model_output_error_handling(typed_model):
    """Test that the _decode_model_output method handles errors gracefully."""
    # Create a sample model output
    output = np.zeros((1, 5, 10))
    
    # Mock the open function to raise an exception
    with patch('builtins.open', side_effect=Exception("Test error")), \
         patch('src.models.typed_text_model.clean_text', side_effect=Exception("Test error")):
        
        # Decode the output - should not raise an exception
        text = typed_model._decode_model_output(output)
        
        # Should return an empty string
        assert text == ""


# ===== Test Field Extraction =====

def test_extract_fields(typed_model, mock_document_image):
    """Test that the extract_fields method correctly extracts structured fields from an image."""
    # Mock the necessary methods and functions
    with patch.object(typed_model, 'extract_text', return_value={
        "text": "Sample extracted text with key-value pairs",
        "confidence": 0.9
    }), \
    patch('src.models.typed_text_model.extract_key_value_pairs', return_value=[
        ("name", "John Doe", 0.95),
        ("address", "123 Main St", 0.92),
        ("phone", "555-123-4567", 0.88),
        ("email", "john.doe@example.com", 0.94),
        ("business_name", "Acme Corp", 0.96),
        ("tax_id", "12-3456789", 0.85)
    ]), \
    patch('src.models.typed_text_model.extract_form_fields', return_value=[]), \
    patch.object(typed_model, '_determine_field_type', side_effect=lambda k: {
        "name": "text",
        "address": "text",
        "phone": "phone",
        "email": "email",
        "business_name": "text",
        "tax_id": "ein"
    }.get(k, "text")), \
    patch('src.models.typed_text_model.validate_field', return_value=(True, "Validated value", 0.95)):
        
        # Extract fields
        result = typed_model.extract_fields(mock_document_image, DocumentType.APPLICATION)
        
        # Check that the result has the expected structure
        assert isinstance(result, dict)
        assert "extraction_id" in result
        assert "fields" in result
        assert "tables" in result
        assert "metadata" in result
        assert "raw_text" in result
        assert "low_confidence_fields" in result
        assert "requires_verification" in result
        assert "extraction_timestamp" in result
        assert "schema_version" in result
        assert "document_type" in result
        
        # Check the extracted fields
        assert len(result["fields"]) == 6  # 6 key-value pairs
        assert "name" in result["fields"]
        assert "address" in result["fields"]
        assert "phone" in result["fields"]
        assert "email" in result["fields"]
        assert "business_name" in result["fields"]
        assert "tax_id" in result["fields"]
        
        # Check the structure of an extracted field
        field = result["fields"]["name"]
        assert "field_name" in field
        assert "field_type" in field
        assert "value" in field
        assert "raw_text" in field
        assert "confidence" in field
        assert "location" in field
        assert "alternatives" in field
        assert "metadata" in field
        assert "requires_verification" in field
        assert "verification_reason" in field
        assert "extraction_timestamp" in field
        
        # Check the metadata
        assert result["metadata"]["extraction_status"] == "success"
        assert result["metadata"]["document_type"] == DocumentType.APPLICATION.value
        assert "processing_time" in result["metadata"]


def test_extract_fields_flags_low_confidence(typed_model, mock_document_image):
    """Test that the extract_fields method flags fields with low confidence for verification."""
    # Mock the necessary methods and functions
    with patch.object(typed_model, 'extract_text', return_value={
        "text": "Sample extracted text with key-value pairs",
        "confidence": 0.9
    }), \
    patch('src.models.typed_text_model.extract_key_value_pairs', return_value=[
        ("name", "John Doe", 0.95),  # High confidence
        ("address", "123 Main St", 0.7),  # Low confidence
        ("phone", "555-123-4567", 0.6)  # Low confidence
    ]), \
    patch('src.models.typed_text_model.extract_form_fields', return_value=[]), \
    patch.object(typed_model, '_determine_field_type', return_value="text"), \
    patch('src.models.typed_text_model.validate_field', side_effect=[
        (True, "John Doe", 0.95),  # Valid
        (True, "123 Main St", 0.9),  # Valid
        (False, "555-123-4567", 0.8)  # Invalid format
    ]):
        
        # Extract fields
        result = typed_model.extract_fields(mock_document_image)
        
        # Check that low confidence fields are flagged
        assert result["requires_verification"] is True
        assert len(result["low_confidence_fields"]) == 2
        assert "address" in result["low_confidence_fields"]
        assert "phone" in result["low_confidence_fields"]
        
        # Check that the fields have the correct verification flags
        assert result["fields"]["name"]["requires_verification"] is False
        assert result["fields"]["address"]["requires_verification"] is True
        assert result["fields"]["phone"]["requires_verification"] is True
        
        # Check that the verification reasons are set correctly
        assert result["fields"]["address"]["verification_reason"] == "Low confidence score"
        assert result["fields"]["phone"]["verification_reason"] == "Invalid text format"


def test_extract_fields_error_handling(typed_model, mock_document_image):
    """Test that the extract_fields method handles errors gracefully."""
    # Mock the extract_text method to raise an exception
    with patch.object(typed_model, 'extract_text', side_effect=Exception("Test error")):
        # Extract fields - should not raise an exception
        result = typed_model.extract_fields(mock_document_image)
        
        # Should return an empty result with error
        assert result["fields"] == {}
        assert result["metadata"]["extraction_status"] == "failed"
        assert len(result["metadata"]["errors"]) > 0
        assert "Test error" in result["metadata"]["errors"][0]


# ===== Test Field Type Determination =====

def test_determine_field_type():
    """Test that the _determine_field_type method correctly identifies field types based on key names."""
    model = TypedTextModel()
    
    # Test email fields
    assert model._determine_field_type("email") == "email"
    assert model._determine_field_type("Email Address") == "email"
    assert model._determine_field_type("Business E-mail") == "email"
    
    # Test phone fields
    assert model._determine_field_type("phone") == "phone"
    assert model._determine_field_type("Telephone Number") == "phone"
    assert model._determine_field_type("Mobile Phone") == "phone"
    assert model._determine_field_type("Cell") == "phone"
    
    # Test date fields
    assert model._determine_field_type("date") == "date"
    assert model._determine_field_type("Date of Birth") == "date"
    assert model._determine_field_type("DOB") == "date"
    assert model._determine_field_type("Issue Date") == "date"
    assert model._determine_field_type("Expiry Date") == "date"
    
    # Test currency fields
    assert model._determine_field_type("amount") == "currency"
    assert model._determine_field_type("Annual Revenue") == "currency"
    assert model._determine_field_type("Monthly Income") == "currency"
    assert model._determine_field_type("Payment Amount") == "currency"
    assert model._determine_field_type("Balance") == "currency"
    
    # Test EIN fields
    assert model._determine_field_type("ein") == "ein"
    assert model._determine_field_type("Tax ID") == "ein"
    assert model._determine_field_type("Employer Identification Number") == "ein"
    
    # Test SSN fields
    assert model._determine_field_type("ssn") == "ssn"
    assert model._determine_field_type("Social Security Number") == "ssn"
    
    # Test ZIP code fields
    assert model._determine_field_type("zip") == "zip"
    assert model._determine_field_type("ZIP Code") == "zip"
    assert model._determine_field_type("Postal Code") == "zip"
    
    # Test default (text) for unknown field types
    assert model._determine_field_type("name") == "text"
    assert model._determine_field_type("address") == "text"
    assert model._determine_field_type("notes") == "text"


# ===== Test Performance Metrics =====

def test_performance_metrics(typed_model, mock_document_image):
    """Test that the model meets performance requirements for typed text extraction."""
    # Mock the necessary methods and functions for a realistic performance test
    with patch.object(typed_model, 'preprocess', return_value=mock_document_image), \
         patch('src.models.typed_text_model.run_inference', return_value=(np.random.rand(1, 10, 50), {
             'confidence_scores': {'overall': 0.9}
         })), \
         patch.object(typed_model, '_decode_model_output', return_value="Sample extracted text"), \
         patch.object(typed_model, 'apply_language_model_correction', return_value=("Corrected sample text", 0.92)):
        
        # Measure the time to extract text
        start_time = time.time()
        result = typed_model.extract_text(mock_document_image)
        extraction_time = time.time() - start_time
        
        # Check that the extraction time is reasonable
        # The requirement is to process applications in under 5 minutes,
        # but the OCR component should be much faster than that
        assert extraction_time < 5.0  # 5 seconds is a reasonable upper bound for a test
        
        # Check that the confidence score meets the 99% accuracy requirement
        # Note: In a real test, we would compare against ground truth,
        # but for this test we just check that the confidence is high
        assert result["confidence"] > 0.9  # 90% confidence is a reasonable lower bound for a test


# ===== Test GPU Acceleration =====

def test_gpu_acceleration_configuration(typed_model_parameters):
    """Test that the model is configured to use GPU acceleration as required."""
    # Set the use_gpu parameter to True for this test
    typed_model_parameters['use_gpu'] = True
    
    # Mock the configure_gpu_memory function
    with patch('src.models.typed_text_model.configure_gpu_memory') as mock_configure_gpu:
        # Initialize the model
        model = TypedTextModel(typed_model_parameters)
        
        # Check that configure_gpu_memory was called with the expected parameters
        mock_configure_gpu.assert_called_once()
        args, kwargs = mock_configure_gpu.call_args
        assert kwargs.get('allow_growth') is True
        
        # Check that the GPU configuration is stored
        assert hasattr(model, 'gpu_config')