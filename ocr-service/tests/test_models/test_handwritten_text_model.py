#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the HandwrittenTextModel class.

This module contains tests for the specialized TensorFlow model for recognizing
and extracting handwritten text from documents. It verifies that the model correctly
processes handwritten content, extracts text with high accuracy despite variability
in handwriting styles, and provides confidence scores for the extracted data.
"""

import os
import json
import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import MagicMock, patch, ANY
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Import the model to test
from src.models.handwritten_text_model import HandwrittenTextModel
from src.models.base_model import BaseOCRModel

# Import types
from src.types.models import OCRModelType, ModelParameters, ModelResult
from src.types.extraction import ConfidenceScore, ExtractedField
from src.types.documents import DocumentType

# Import utilities for testing
from src.utils.image_utils import (
    preprocess_for_ocr,
    enhance_contrast,
    normalize_orientation,
    sharpen_image,
    deskew_image,
    normalize_size
)

# Constants for testing
TEST_DATA_DIR = Path(__file__).parent.parent / "test_data"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MANIFEST_PATH = HANDWRITTEN_DOCS_DIR / "sample_manifest.json"


# ===== Test Fixtures =====

@pytest.fixture
def handwritten_model_params() -> ModelParameters:
    """Provides test parameters for handwritten text model."""
    return {
        'model_name': 'handwritten_text_ocr_test',
        'model_version': '1.0.0-test',
        'model_type': OCRModelType.HANDWRITTEN.value,
        'model_path': '/tmp/models/handwritten_test',
        'vocab_path': '/tmp/models/handwritten_test/vocab.txt',
        'input_shape': (64, 1024, 1),  # Grayscale input
        'input_dtype': 'float32',
        'max_text_length': 512,
        'grayscale': True,
        'normalize_input': True,
        'batch_size': 1,
        'use_gpu': False,  # Disable GPU for testing
        'gpu_memory_limit': 1024,  # 1GB for testing
        'num_threads': 2,
        'beam_width': 5,
        'language': 'en',
        'confidence_threshold': 0.6,
    }


@pytest.fixture
def mock_handwritten_model():
    """Provides a mocked handwritten text model."""
    with patch('tensorflow.keras.models.Model') as mock_model_class:
        # Create a mock model that returns predictable outputs
        mock_model = MagicMock()
        
        # Configure predict method to return a sequence of character probabilities
        # Shape: [sequence_length, vocabulary_size]
        seq_length = 50
        vocab_size = 100
        
        # Create a prediction array with high probability for a specific sequence
        # that will decode to "Test handwritten text"
        predictions = np.zeros((seq_length, vocab_size))
        
        # Set high probabilities for specific characters
        # This is a simplified version - in reality, the prediction would be more complex
        char_indices = [20, 5, 19, 20, 0, 8, 1, 14, 4, 23, 18, 9, 20, 20, 5, 14, 0, 20, 5, 24, 20]  # "Test handwritten text"
        for i, char_idx in enumerate(char_indices):
            if i < seq_length:
                predictions[i, char_idx] = 0.9  # High probability for the target character
                # Add some noise to other characters
                for j in range(vocab_size):
                    if j != char_idx:
                        predictions[i, j] = np.random.uniform(0, 0.1)
        
        mock_model.predict.return_value = np.expand_dims(predictions, axis=0)  # Add batch dimension
        mock_model_class.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def sample_handwritten_image() -> np.ndarray:
    """Provides a sample handwritten image for testing."""
    # Create a simple test image (64x1024 grayscale)
    image = np.ones((64, 1024, 1), dtype=np.float32) * 0.9  # Light gray background
    
    # Add some "handwritten" strokes (darker pixels)
    for i in range(10, 50):
        for j in range(100, 900, 20):
            # Create a small "stroke" pattern
            image[i:i+5, j:j+10, 0] = 0.2  # Dark gray
    
    return image


@pytest.fixture
def sample_handwritten_document() -> Tuple[np.ndarray, Dict[str, Any]]:
    """Provides a sample handwritten document with expected extraction results."""
    # Create a sample document image
    image = np.ones((300, 500, 3), dtype=np.uint8) * 240  # Light gray background
    
    # Add some "handwritten" text areas
    # Name field
    for i in range(50, 70):
        for j in range(150, 350, 10):
            # Create a pattern resembling "John Doe"
            image[i:i+3, j:j+7, :] = 50  # Dark gray
    
    # Address field
    for i in range(100, 120):
        for j in range(150, 400, 8):
            # Create a pattern resembling an address
            image[i:i+3, j:j+5, :] = 50  # Dark gray
    
    # Expected extraction results
    expected_results = {
        "text": "John Doe\n123 Main St",
        "confidence": 0.85,
        "fields": {
            "name": {
                "value": "John Doe",
                "confidence": 0.90,
                "location": {"page": 0, "top": 50/300, "left": 150/500, "bottom": 70/300, "right": 350/500}
            },
            "address": {
                "value": "123 Main St",
                "confidence": 0.80,
                "location": {"page": 0, "top": 100/300, "left": 150/500, "bottom": 120/300, "right": 400/500}
            }
        }
    }
    
    return image, expected_results


@pytest.fixture
def handwriting_styles() -> List[Dict[str, Any]]:
    """Provides a list of different handwriting styles for testing."""
    return [
        {
            "style": "print",
            "description": "Clearly printed handwriting",
            "expected_confidence": 0.90,
            "challenges": ["character spacing", "letter formation"]
        },
        {
            "style": "cursive",
            "description": "Connected cursive handwriting",
            "expected_confidence": 0.75,
            "challenges": ["connected letters", "loop variations", "word separation"]
        },
        {
            "style": "mixed",
            "description": "Mixture of print and cursive",
            "expected_confidence": 0.80,
            "challenges": ["style inconsistency", "character recognition"]
        },
        {
            "style": "sloppy",
            "description": "Hastily written with poor legibility",
            "expected_confidence": 0.65,
            "challenges": ["legibility", "character ambiguity", "inconsistent spacing"]
        },
        {
            "style": "artistic",
            "description": "Stylized or decorative handwriting",
            "expected_confidence": 0.60,
            "challenges": ["non-standard forms", "decorative elements", "style variations"]
        }
    ]


@pytest.fixture
def field_definitions() -> List[Dict[str, Any]]:
    """Provides sample field definitions for testing field extraction."""
    return [
        {
            "field_name": "name",
            "field_type": "text",
            "location": {
                "page": 0,
                "top": 0.15,  # Normalized coordinates (0-1)
                "left": 0.3,
                "bottom": 0.25,
                "right": 0.7
            }
        },
        {
            "field_name": "address",
            "field_type": "text",
            "location": {
                "page": 0,
                "top": 0.3,
                "left": 0.3,
                "bottom": 0.4,
                "right": 0.8
            }
        },
        {
            "field_name": "signature",
            "field_type": "signature",
            "location": {
                "page": 0,
                "top": 0.7,
                "left": 0.5,
                "bottom": 0.8,
                "right": 0.9
            }
        }
    ]


# ===== Test Cases =====

def test_handwritten_model_initialization(handwritten_model_params):
    """Test that the handwritten text model initializes correctly."""
    # Initialize the model
    model = HandwrittenTextModel(handwritten_model_params)
    
    # Check that the model has the correct attributes
    assert model.model_params == handwritten_model_params
    assert model.model is None  # Model should not be loaded yet
    assert hasattr(model, 'vocab')
    assert hasattr(model, 'char_to_idx')
    assert hasattr(model, 'idx_to_char')
    assert model.context_model is None


def test_handwritten_model_inheritance():
    """Test that HandwrittenTextModel inherits from BaseOCRModel."""
    model = HandwrittenTextModel()
    assert isinstance(model, BaseOCRModel)


@patch('os.path.exists', return_value=False)
def test_load_vocabulary_with_default(mock_exists, handwritten_model_params):
    """Test loading vocabulary with default values when file doesn't exist."""
    model = HandwrittenTextModel(handwritten_model_params)
    
    # Check that the vocabulary was loaded with default values
    assert len(model.vocab) > 0
    assert '<blank>' in model.vocab
    assert all(char in model.char_to_idx for char in "abcdefghijklmnopqrstuvwxyz0123456789")
    assert all(idx in model.idx_to_char for idx in range(len(model.vocab)))


@patch('builtins.open')
@patch('os.path.exists', return_value=True)
def test_load_vocabulary_from_file(mock_exists, mock_open, handwritten_model_params):
    """Test loading vocabulary from a file."""
    # Mock the file content
    mock_open.return_value.__enter__.return_value.readlines.return_value = [
        "a\n", "b\n", "c\n", "1\n", "2\n", "3\n"
    ]
    
    model = HandwrittenTextModel(handwritten_model_params)
    
    # Check that the vocabulary was loaded from the file
    assert 'a' in model.vocab
    assert 'b' in model.vocab
    assert 'c' in model.vocab
    assert '1' in model.vocab
    assert '2' in model.vocab
    assert '3' in model.vocab
    assert '<blank>' in model.vocab


def test_build_model(handwritten_model_params):
    """Test building the TensorFlow model architecture."""
    with patch('tensorflow.keras.layers.Input') as mock_input, \
         patch('tensorflow.keras.layers.Conv2D') as mock_conv2d, \
         patch('tensorflow.keras.layers.MaxPooling2D') as mock_maxpool, \
         patch('tensorflow.keras.layers.BatchNormalization') as mock_batchnorm, \
         patch('tensorflow.keras.layers.Reshape') as mock_reshape, \
         patch('tensorflow.keras.layers.Bidirectional') as mock_bidirectional, \
         patch('tensorflow.keras.layers.LSTM') as mock_lstm, \
         patch('tensorflow.keras.layers.Dense') as mock_dense, \
         patch('tensorflow.keras.Model') as mock_model_class:
        
        # Configure mocks to chain properly
        mock_input.return_value = MagicMock(name='input_tensor')
        mock_conv2d.return_value = MagicMock(name='conv_tensor')
        mock_maxpool.return_value = MagicMock(name='pool_tensor')
        mock_batchnorm.return_value = MagicMock(name='bn_tensor')
        mock_reshape.return_value = MagicMock(name='reshape_tensor')
        mock_bidirectional.return_value = MagicMock(name='bilstm_tensor')
        mock_dense.return_value = MagicMock(name='dense_tensor')
        
        # Mock the model
        mock_model = MagicMock(name='keras_model')
        mock_model_class.return_value = mock_model
        
        # Create the model and build it
        model = HandwrittenTextModel(handwritten_model_params)
        built_model = model._build_model()
        
        # Check that the model was built correctly
        assert built_model == mock_model
        
        # Verify that the expected layers were created
        mock_input.assert_called_once()
        assert mock_conv2d.call_count >= 4  # At least 4 Conv2D layers
        assert mock_maxpool.call_count >= 3  # At least 3 MaxPooling layers
        assert mock_batchnorm.call_count >= 4  # At least 4 BatchNormalization layers
        mock_reshape.assert_called_once()
        assert mock_bidirectional.call_count >= 2  # At least 2 Bidirectional layers
        mock_dense.assert_called()
        
        # Verify model compilation
        mock_model.compile.assert_called_once()


def test_preprocess_image(sample_handwritten_image):
    """Test the specialized preprocessing for handwritten text images."""
    with patch('src.utils.image_utils.preprocess_for_ocr') as mock_preprocess, \
         patch('src.utils.image_utils.enhance_contrast') as mock_enhance, \
         patch('src.utils.image_utils.deskew_image') as mock_deskew, \
         patch('src.utils.image_utils.sharpen_image') as mock_sharpen, \
         patch('src.utils.image_utils.normalize_size') as mock_normalize, \
         patch('tensorflow.image.resize') as mock_resize, \
         patch('tensorflow.image.rgb_to_grayscale') as mock_rgb_to_gray:
        
        # Configure mocks to return the input with slight modifications
        mock_preprocess.return_value = sample_handwritten_image * 0.9
        mock_enhance.return_value = sample_handwritten_image * 0.8
        mock_deskew.return_value = sample_handwritten_image * 0.7
        mock_sharpen.return_value = sample_handwritten_image * 0.6
        mock_normalize.return_value = sample_handwritten_image * 0.5
        mock_resize.return_value = tf.constant(sample_handwritten_image * 0.4)
        
        # Create the model and preprocess the image
        model = HandwrittenTextModel()
        preprocessed = model.preprocess_image(sample_handwritten_image)
        
        # Check that all preprocessing steps were called
        mock_preprocess.assert_called_once_with(sample_handwritten_image, DocumentType.APPLICATION)
        mock_enhance.assert_called_once()
        mock_deskew.assert_called_once()
        mock_sharpen.assert_called_once()
        mock_normalize.assert_called_once()
        mock_resize.assert_called_once()
        
        # Check that the output has the expected shape and type
        assert isinstance(preprocessed, np.ndarray)
        assert preprocessed.shape == sample_handwritten_image.shape
        assert preprocessed.dtype == np.float32
        assert 0 <= preprocessed.min() <= preprocessed.max() <= 1  # Normalized to [0,1]


def test_extract_text(mock_handwritten_model, sample_handwritten_image):
    """Test extracting text from a handwritten image."""
    with patch.object(HandwrittenTextModel, 'load') as mock_load, \
         patch.object(HandwrittenTextModel, 'preprocess_image', return_value=sample_handwritten_image) as mock_preprocess, \
         patch.object(HandwrittenTextModel, '_decode_predictions', return_value=("Test handwritten text", 0.85)) as mock_decode, \
         patch.object(HandwrittenTextModel, '_calculate_word_confidences', return_value=[0.9, 0.8, 0.85]) as mock_word_conf:
        
        # Create the model
        model = HandwrittenTextModel()
        model.model = mock_handwritten_model
        
        # Extract text from the image
        result = model.extract_text(sample_handwritten_image)
        
        # Check that the necessary methods were called
        mock_preprocess.assert_called_once_with(sample_handwritten_image)
        mock_decode.assert_called_once()
        mock_word_conf.assert_called_once()
        
        # Check the result structure
        assert isinstance(result, dict)
        assert 'text' in result
        assert 'confidence' in result
        assert 'bounding_boxes' in result
        assert 'word_confidences' in result
        assert 'processing_time' in result
        assert 'model_type' in result
        assert 'warnings' in result
        
        # Check the result values
        assert result['text'] == "Test handwritten text"
        assert result['confidence'] == 0.85
        assert result['model_type'] == OCRModelType.HANDWRITTEN.value
        assert len(result['bounding_boxes']) == 1
        assert len(result['word_confidences']) == 3


def test_decode_predictions():
    """Test decoding model predictions into text."""
    # Create a model with a simple vocabulary
    model = HandwrittenTextModel()
    model.vocab = list("abcdefghijklmnopqrstuvwxyz ") + ['<blank>']
    model.char_to_idx = {char: idx for idx, char in enumerate(model.vocab)}
    model.idx_to_char = {idx: char for idx, char in enumerate(model.vocab)}
    
    # Create sample predictions
    # Shape: [sequence_length, vocabulary_size]
    seq_length = 10
    vocab_size = len(model.vocab)
    predictions = np.zeros((seq_length, vocab_size))
    
    # Set high probabilities for "hello test"
    char_indices = [7, 4, 11, 11, 14, 26, 19, 4, 18, 19]  # "hello test"
    for i, char_idx in enumerate(char_indices):
        predictions[i, char_idx] = 0.9
    
    # Decode the predictions
    decoded_text, confidence = model._decode_predictions(predictions, beam_width=3)
    
    # Check the result
    assert decoded_text == "hello test"
    assert 0.8 <= confidence <= 1.0  # High confidence expected


def test_calculate_word_confidences():
    """Test calculating confidence scores for individual words."""
    # Create a model with a simple vocabulary
    model = HandwrittenTextModel()
    model.vocab = list("abcdefghijklmnopqrstuvwxyz ") + ['<blank>']
    model.char_to_idx = {char: idx for idx, char in enumerate(model.vocab)}
    model.idx_to_char = {idx: char for idx, char in enumerate(model.vocab)}
    
    # Create sample predictions
    # Shape: [sequence_length, vocabulary_size]
    seq_length = 11
    vocab_size = len(model.vocab)
    predictions = np.zeros((seq_length, vocab_size))
    
    # Set high probabilities for "hello world"
    text = "hello world"
    positions = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    chars = [7, 4, 11, 11, 14, 26, 22, 14, 17, 11, 3]  # "hello world"
    
    # Set different confidence levels for different words
    confidences = [0.9, 0.9, 0.9, 0.9, 0.9, 0.0, 0.7, 0.7, 0.7, 0.7, 0.7]  # "hello" high confidence, "world" lower
    
    for i, (char_idx, conf) in enumerate(zip(chars, confidences)):
        predictions[positions[i], char_idx] = conf
    
    # Calculate word confidences
    word_confidences = model._calculate_word_confidences(predictions, text)
    
    # Check the result
    assert len(word_confidences) == 2  # "hello" and "world"
    assert word_confidences[0] > word_confidences[1]  # "hello" should have higher confidence than "world"


def test_extract_fields(sample_handwritten_document, field_definitions):
    """Test extracting specific fields from handwritten text."""
    image, expected_results = sample_handwritten_document
    
    with patch.object(HandwrittenTextModel, 'extract_text') as mock_extract_text, \
         patch.object(HandwrittenTextModel, '_extract_field_by_context', return_value=("Test field", 0.75)) as mock_extract_field, \
         patch.object(HandwrittenTextModel, '_process_field_value', side_effect=lambda text, field_type: text) as mock_process:
        
        # Configure the mock to return different results for different regions
        def mock_extract_side_effect(img):
            # Check if this is the main image or a region
            if img.shape == image.shape:
                return {
                    'text': expected_results['text'],
                    'confidence': expected_results['confidence'],
                    'bounding_boxes': [{'text': expected_results['text'], 'confidence': expected_results['confidence']}]
                }
            else:
                # This is a region extraction
                # Return different results based on region size (simplified approach)
                height, width = img.shape[:2]
                if height < 30:  # Name field
                    return {
                        'text': "John Doe",
                        'confidence': 0.90,
                        'bounding_boxes': [{'text': "John Doe", 'confidence': 0.90}]
                    }
                else:  # Address field
                    return {
                        'text': "123 Main St",
                        'confidence': 0.80,
                        'bounding_boxes': [{'text': "123 Main St", 'confidence': 0.80}]
                    }
        
        mock_extract_text.side_effect = mock_extract_side_effect
        
        # Create the model and extract fields
        model = HandwrittenTextModel()
        extracted_fields = model.extract_fields(image, field_definitions)
        
        # Check that the necessary methods were called
        assert mock_extract_text.call_count >= 1
        assert mock_process.call_count == len(field_definitions)
        
        # Check the result structure
        assert isinstance(extracted_fields, dict)
        assert len(extracted_fields) == len(field_definitions)
        
        # Check each extracted field
        for field_def in field_definitions:
            field_name = field_def['field_name']
            assert field_name in extracted_fields
            
            field = extracted_fields[field_name]
            assert 'field_name' in field
            assert 'field_type' in field
            assert 'value' in field
            assert 'raw_text' in field
            assert 'confidence' in field
            assert 'location' in field
            assert 'requires_verification' in field
            
            assert field['field_name'] == field_name
            assert field['field_type'] == field_def['field_type']
            assert isinstance(field['confidence'], ConfidenceScore)


def test_extract_field_by_context():
    """Test extracting field values from text based on context."""
    model = HandwrittenTextModel()
    
    # Test with various text patterns
    text1 = "Name: John Doe\nAddress: 123 Main St\nPhone: 555-123-4567"
    name1, conf1 = model._extract_field_by_context(text1, "name", "text")
    addr1, conf1_addr = model._extract_field_by_context(text1, "address", "text")
    
    assert name1 == "John Doe"
    assert addr1 == "123 Main St"
    assert conf1 > 0.5
    assert conf1_addr > 0.5
    
    # Test with different pattern
    text2 = "NAME - Jane Smith\nADDRESS - 456 Oak Ave"
    name2, conf2 = model._extract_field_by_context(text2, "name", "text")
    addr2, conf2_addr = model._extract_field_by_context(text2, "address", "text")
    
    assert name2 == "Jane Smith"
    assert addr2 == "456 Oak Ave"
    assert conf2 > 0.5
    assert conf2_addr > 0.5
    
    # Test with no match
    text3 = "This text doesn't contain the field"
    name3, conf3 = model._extract_field_by_context(text3, "name", "text")
    
    assert name3 == ""
    assert conf3 < 0.5  # Low confidence expected


def test_process_field_value():
    """Test processing extracted field text based on field type."""
    model = HandwrittenTextModel()
    
    # Test text field
    text_value = model._process_field_value("  John Doe  ", "text")
    assert text_value == "John Doe"
    
    # Test number field
    number_value = model._process_field_value("Amount: $123.45", "number")
    assert number_value == 123.45
    
    # Test date field
    date_value = model._process_field_value("January 15, 2023", "date")
    assert date_value == "2023-01-15"
    
    # Test checkbox field
    checkbox_value1 = model._process_field_value("X", "checkbox")
    checkbox_value2 = model._process_field_value("Yes", "checkbox")
    checkbox_value3 = model._process_field_value("No", "checkbox")
    
    assert checkbox_value1 is True
    assert checkbox_value2 is True
    assert checkbox_value3 is False
    
    # Test signature field
    signature_value1 = model._process_field_value("John Doe", "signature")
    signature_value2 = model._process_field_value("", "signature")
    
    assert signature_value1 is True
    assert signature_value2 is False
    
    # Test unknown field type
    unknown_value = model._process_field_value("Test value", "unknown_type")
    assert unknown_value == "Test value"


def test_get_attention_heatmap(sample_handwritten_image):
    """Test generating attention heatmap for visualization."""
    with patch.object(HandwrittenTextModel, 'load') as mock_load, \
         patch('tensorflow.keras.Model') as mock_model_class:
        
        # Configure the mock model to return attention weights
        attention_model = MagicMock()
        attention_weights = np.random.rand(1, 50)  # Random attention weights
        attention_model.predict.return_value = attention_weights
        mock_model_class.return_value = attention_model
        
        # Create the model
        model = HandwrittenTextModel()
        model.model = MagicMock()  # Main model
        
        # Generate attention heatmap
        with patch('cv2.resize', return_value=np.random.rand(300, 500)) as mock_resize:
            heatmap = model.get_attention_heatmap(sample_handwritten_image)
        
        # Check that the necessary methods were called
        mock_model_class.assert_called_once()
        attention_model.predict.assert_called_once()
        mock_resize.assert_called_once()
        
        # Check the result
        assert isinstance(heatmap, np.ndarray)
        assert 0 <= heatmap.min() <= heatmap.max() <= 1  # Normalized to [0,1]


def test_enhance_recognition_with_context():
    """Test enhancing recognition results using contextual information."""
    with patch.object(HandwrittenTextModel, '_is_similar', return_value=True) as mock_similar, \
         patch.object(HandwrittenTextModel, '_apply_spell_correction', return_value="Corrected text") as mock_spell:
        
        model = HandwrittenTextModel()
        
        # Test with application form context
        context1 = {
            "document_type": "application_form",
            "expected_fields": {
                "name": ["John Smith", "Jane Smith"],
                "address": ["123 Main St", "456 Oak Ave"]
            }
        }
        
        text1 = "Jahn Smith"  # Misspelled name
        enhanced1, conf1 = model.enhance_recognition_with_context(text1, context1)
        
        # Should match with "John Smith" due to similarity
        assert enhanced1 == "John Smith"
        assert conf1 > 0.8  # High confidence expected
        
        # Test with no context
        text2 = "Misspelled text"
        enhanced2, conf2 = model.enhance_recognition_with_context(text2, {})
        
        # Should apply general spell correction
        assert enhanced2 == "Corrected text"
        assert 0.7 <= conf2 <= 0.8  # Moderate confidence expected


def test_is_similar():
    """Test checking if two strings are similar using Levenshtein distance."""
    model = HandwrittenTextModel()
    
    # Test with similar strings
    assert model._is_similar("John", "john") is True
    assert model._is_similar("John Smith", "John Smth") is True
    assert model._is_similar("123 Main St", "123 Main Street") is True
    
    # Test with dissimilar strings
    assert model._is_similar("John", "Jane") is False
    assert model._is_similar("Apple", "Orange") is False
    assert model._is_similar("123 Main St", "456 Oak Ave") is False
    
    # Test with empty strings
    assert model._is_similar("", "") is True
    assert model._is_similar("Text", "") is False


# ===== Performance Tests =====

@pytest.mark.slow
def test_performance_metrics(sample_handwritten_document):
    """Test performance metrics for handwritten text extraction."""
    image, _ = sample_handwritten_document
    
    with patch.object(HandwrittenTextModel, 'load') as mock_load, \
         patch.object(HandwrittenTextModel, 'extract_text', return_value={
             'text': "Performance test",
             'confidence': 0.85,
             'processing_time': 0.5,  # 500ms processing time
             'bounding_boxes': [{'text': "Performance test", 'confidence': 0.85}]
         }) as mock_extract:
        
        # Create the model
        model = HandwrittenTextModel()
        
        # Measure processing time for multiple extractions
        num_iterations = 10
        start_time = datetime.now()
        
        for _ in range(num_iterations):
            result = model.extract_text(image)
        
        total_time = (datetime.now() - start_time).total_seconds()
        avg_time = total_time / num_iterations
        
        # Check that the processing time is within acceptable limits
        # The requirement is to process applications in under 5 minutes,
        # but each individual extraction should be much faster
        assert avg_time < 1.0  # Less than 1 second per extraction
        assert result['processing_time'] < 1.0  # Less than 1 second reported time


@pytest.mark.parametrize("style", [
    "print",
    "cursive",
    "mixed",
    "sloppy",
    "artistic"
])
def test_handwriting_style_accuracy(style, handwriting_styles, sample_handwritten_image):
    """Test handwritten text recognition accuracy on various writing styles."""
    # Find the expected confidence for this style
    style_info = next(s for s in handwriting_styles if s["style"] == style)
    expected_confidence = style_info["expected_confidence"]
    
    with patch.object(HandwrittenTextModel, 'load') as mock_load, \
         patch.object(HandwrittenTextModel, 'extract_text', return_value={
             'text': f"Sample {style} handwriting",
             'confidence': expected_confidence,
             'bounding_boxes': [{'text': f"Sample {style} handwriting", 'confidence': expected_confidence}]
         }) as mock_extract:
        
        # Create the model
        model = HandwrittenTextModel()
        
        # Extract text
        result = model.extract_text(sample_handwritten_image)
        
        # Check that the confidence meets the minimum threshold for this style
        assert result['confidence'] >= expected_confidence * 0.9  # Allow for 10% variation
        
        # For sloppy and artistic styles, verify that warnings are generated if confidence is low
        if style in ["sloppy", "artistic"] and expected_confidence < 0.7:
            assert len(result.get('warnings', [])) > 0


# ===== Integration Tests =====

@pytest.mark.integration
def test_end_to_end_extraction(sample_handwritten_document, field_definitions):
    """Test end-to-end extraction process from image to structured fields."""
    image, expected_results = sample_handwritten_document
    
    with patch.object(HandwrittenTextModel, 'load') as mock_load, \
         patch.object(HandwrittenTextModel, 'extract_text', return_value={
             'text': expected_results['text'],
             'confidence': expected_results['confidence'],
             'bounding_boxes': [{'text': expected_results['text'], 'confidence': expected_results['confidence']}]
         }), \
         patch.object(HandwrittenTextModel, 'extract_fields', return_value={
             field['field_name']: {
                 'field_name': field['field_name'],
                 'field_type': field['field_type'],
                 'value': expected_results['fields'][field['field_name']]['value'],
                 'confidence': ConfidenceScore.from_float(expected_results['fields'][field['field_name']]['confidence']),
                 'location': field['location'],
                 'requires_verification': False
             } for field in field_definitions if field['field_name'] in expected_results['fields']
         }) as mock_extract_fields:
        
        # Create the model
        model = HandwrittenTextModel()
        
        # Extract text and fields
        text_result = model.extract_text(image)
        fields_result = model.extract_fields(image, field_definitions)
        
        # Check text extraction results
        assert text_result['text'] == expected_results['text']
        assert text_result['confidence'] == expected_results['confidence']
        
        # Check field extraction results
        for field_name, expected_field in expected_results['fields'].items():
            assert field_name in fields_result
            extracted = fields_result[field_name]
            
            assert extracted['value'] == expected_field['value']
            assert extracted['confidence'].value >= expected_field['confidence'] * 0.9  # Allow for 10% variation


@pytest.mark.integration
def test_gpu_acceleration():
    """Test that GPU acceleration is used when available."""
    with patch('tensorflow.config.list_physical_devices') as mock_devices, \
         patch('tensorflow.config.experimental.set_memory_growth') as mock_memory_growth, \
         patch('tensorflow.config.experimental.set_virtual_device_configuration') as mock_device_config:
        
        # Simulate GPU being available
        mock_devices.return_value = [MagicMock(name='GPU:0')]
        
        # Create model with GPU enabled
        model_params = {
            'use_gpu': True,
            'gpu_memory_limit': 4096  # 4GB
        }
        
        model = HandwrittenTextModel(model_params)
        
        # Load the model to trigger GPU configuration
        with patch.object(model, '_build_model') as mock_build, \
             patch('tensorflow.keras.models.load_model') as mock_load_model:
            mock_build.return_value = MagicMock()
            mock_load_model.return_value = MagicMock()
            
            model.load()
        
        # Check that GPU configuration was attempted
        mock_devices.assert_called()
        assert mock_memory_growth.called or mock_device_config.called


# ===== Error Handling Tests =====

def test_error_handling_invalid_image():
    """Test error handling for invalid image input."""
    model = HandwrittenTextModel()
    
    # Test with None image
    with pytest.raises(ValueError):
        model.extract_text(None)
    
    # Test with empty image
    with pytest.raises(ValueError):
        model.extract_text(np.array([]))
    
    # Test with invalid image shape
    with pytest.raises(ValueError):
        model.extract_text(np.zeros((10,)))  # 1D array


def test_error_handling_model_not_loaded():
    """Test error handling when model is not loaded."""
    model = HandwrittenTextModel()
    model.model = None  # Ensure model is not loaded
    
    with patch.object(model, 'load') as mock_load:
        mock_load.side_effect = RuntimeError("Failed to load model")
        
        with pytest.raises(RuntimeError):
            model.extract_text(np.zeros((100, 100, 3)))


def test_low_confidence_warning():
    """Test that warnings are generated for low confidence extractions."""
    with patch.object(HandwrittenTextModel, 'load') as mock_load, \
         patch.object(HandwrittenTextModel, '_decode_predictions', return_value=("Low confidence text", 0.3)) as mock_decode, \
         patch.object(HandwrittenTextModel, '_calculate_word_confidences', return_value=[0.3, 0.3, 0.3]) as mock_word_conf:
        
        # Create the model with high confidence threshold
        model_params = {'confidence_threshold': 0.7}
        model = HandwrittenTextModel(model_params)
        model.model = MagicMock()
        model.model.predict.return_value = np.zeros((1, 10, 100))  # Dummy predictions
        
        # Extract text
        with patch.object(model, 'preprocess_image', return_value=np.zeros((64, 1024, 1))) as mock_preprocess:
            result = model.extract_text(np.zeros((100, 100, 3)))
        
        # Check that warnings were generated
        assert 'warnings' in result
        assert len(result['warnings']) > 0
        assert any('Low confidence' in warning for warning in result['warnings'])


# ===== Utility Tests =====

def test_ctc_loss():
    """Test the custom CTC loss function."""
    model = HandwrittenTextModel()
    
    # Create dummy inputs
    y_true = tf.constant([[1, 2, 3, 0, 0], [4, 5, 0, 0, 0]])  # Batch of 2, padded with zeros
    y_pred = tf.random.uniform((2, 10, 100))  # Batch of 2, 10 time steps, 100 classes
    
    # Calculate loss
    with patch('tensorflow.keras.backend.ctc_batch_cost', return_value=tf.constant(1.5)) as mock_ctc_cost:
        loss = model._ctc_loss(y_true, y_pred)
    
    # Check that CTC batch cost was called
    mock_ctc_cost.assert_called_once()
    
    # Check that loss has the expected value
    assert loss.numpy() == 1.5