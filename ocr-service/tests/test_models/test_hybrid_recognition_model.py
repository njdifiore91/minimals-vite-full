#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the Hybrid Recognition Model.

This module contains tests for the HybridRecognitionModel class, which is responsible
for processing documents containing both typed and handwritten text. The tests verify
that the model correctly identifies text types, switches between recognition algorithms,
and maintains high accuracy for mixed-format documents.
"""

import os
import time
import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Tuple

# Import the model being tested
from src.models.hybrid_recognition_model import (
    HybridRecognitionModel,
    TextRegionClassifier,
    TextRegion,
    HybridRecognitionModelFactory
)

# Import type definitions
from src.types.models import ModelParameters, ModelResult, OCRModelType
from src.types.extraction import ConfidenceScore, ExtractedData, ExtractedField

# Import configuration
from src.config import tensorflow_config


# ===== Test Fixtures =====

@pytest.fixture
def mock_text_region_classifier():
    """Provides a mocked TextRegionClassifier."""
    with patch('src.models.hybrid_recognition_model.TextRegionClassifier') as mock_classifier:
        # Configure the mock to return predictable results
        classifier_instance = MagicMock()
        mock_classifier.return_value = classifier_instance
        
        # Mock the classify_region method to return predictable results
        def mock_classify_region(image_region):
            # Simple logic to classify regions based on image mean value
            # This is just for testing - real classification would be more complex
            mean_value = np.mean(image_region)
            if mean_value > 0.5:
                return ('typed', 0.9)
            else:
                return ('handwritten', 0.85)
        
        classifier_instance.classify_region.side_effect = mock_classify_region
        
        yield classifier_instance


@pytest.fixture
def mock_region_detector():
    """Provides a mocked region detector model."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Create a mock model that returns predictable outputs
        mock_model = MagicMock()
        
        # Mock the predict method to return bounding boxes
        def mock_predict(image, verbose=0):
            # Return a fixed set of bounding boxes for testing
            return {
                'boxes': [[
                    [0.1, 0.1, 0.3, 0.2],  # [y1, x1, y2, x2] format
                    [0.4, 0.1, 0.6, 0.2],
                    [0.7, 0.1, 0.9, 0.2]
                ]],
                'scores': [[0.95, 0.92, 0.88]]
            }
        
        mock_model.predict.side_effect = mock_predict
        mock_load_model.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def mock_typed_model():
    """Provides a mocked typed text recognition model."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Create a mock model that returns predictable outputs
        mock_model = MagicMock()
        
        # Mock the predict method to return text recognition results
        def mock_predict(image, verbose=0):
            # Return a fixed text recognition result for testing
            return {
                'text': 'Sample typed text',
                'confidence': 0.95
            }
        
        mock_model.predict.side_effect = mock_predict
        mock_load_model.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def mock_handwritten_model():
    """Provides a mocked handwritten text recognition model."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Create a mock model that returns predictable outputs
        mock_model = MagicMock()
        
        # Mock the predict method to return text recognition results
        def mock_predict(image, verbose=0):
            # Return a fixed text recognition result for testing
            return {
                'text': 'Sample handwritten text',
                'confidence': 0.85
            }
        
        mock_model.predict.side_effect = mock_predict
        mock_load_model.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def hybrid_model_parameters() -> ModelParameters:
    """Provides parameters for hybrid text OCR model."""
    return {
        'model_type': OCRModelType.HYBRID,
        'confidence_threshold': 0.70,  # Balanced threshold for mixed content
        'detection_confidence_threshold': 0.5,
        'batch_size': 1,
        'image_size': (1024, 768),
        'channels': 3,
        'use_gpu': False,  # Disable GPU for testing
        'preprocessing_steps': ['resize', 'normalize', 'adaptive_threshold'],
        'language': 'en',
        'grayscale': True
    }


@pytest.fixture
def sample_mixed_document_image() -> np.ndarray:
    """Provides a sample document image with mixed content for testing."""
    # Create a synthetic document image with regions of different brightness
    # to simulate typed and handwritten text regions
    height, width = 1024, 768
    image = np.ones((height, width, 3), dtype=np.float32) * 0.9  # Light background
    
    # Add some darker regions to simulate text
    # Typed text region (darker, more uniform)
    image[100:200, 100:600, :] = 0.1  # Dark text on light background
    
    # Handwritten text region (less uniform, more variable)
    for i in range(300, 400):
        for j in range(100, 600):
            # Add some randomness to simulate handwriting
            if np.random.rand() > 0.7:
                image[i, j, :] = 0.2
    
    return image


@pytest.fixture
def mock_hybrid_model(mock_region_detector, mock_text_region_classifier, 
                     mock_typed_model, mock_handwritten_model, 
                     hybrid_model_parameters):
    """Provides a mocked HybridRecognitionModel with controlled behavior."""
    with patch('src.models.hybrid_recognition_model.TextRegionClassifier', return_value=mock_text_region_classifier), \
         patch('tensorflow.keras.models.load_model') as mock_load_model, \
         patch('src.config.tensorflow_config.get_model_path') as mock_get_path:
        
        # Configure the mock to return different models based on the path
        def mock_load_model_side_effect(path):
            if 'text_region_detector' in path:
                return mock_region_detector
            elif 'typed_text_model' in path:
                return mock_typed_model
            elif 'handwritten_text_model' in path:
                return mock_handwritten_model
            else:
                return MagicMock()
        
        mock_load_model.side_effect = mock_load_model_side_effect
        
        # Configure the mock to return predictable paths
        def mock_get_path_side_effect(model_name):
            return f"/tmp/models/{model_name}"
        
        mock_get_path.side_effect = mock_get_path_side_effect
        
        # Create the model
        model = HybridRecognitionModel(hybrid_model_parameters)
        
        # Replace the internal models with our mocks
        model.region_detector = mock_region_detector
        model.region_classifier = mock_text_region_classifier
        model.typed_model = mock_typed_model
        model.handwritten_model = mock_handwritten_model
        
        yield model


# ===== Tests for TextRegionClassifier =====

def test_text_region_classifier_initialization():
    """Test that TextRegionClassifier initializes correctly."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Configure the mock
        mock_model = MagicMock()
        mock_load_model.return_value = mock_model
        
        # Initialize the classifier
        classifier = TextRegionClassifier(model_path="/tmp/models/classifier", confidence_threshold=0.8)
        
        # Verify initialization
        assert classifier.model_path == "/tmp/models/classifier"
        assert classifier.confidence_threshold == 0.8
        assert classifier.model is not None
        mock_load_model.assert_called_once_with("/tmp/models/classifier")


def test_text_region_classifier_classify_region():
    """Test that TextRegionClassifier correctly classifies text regions."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Configure the mock
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([[0.8]])  # High value indicates handwritten
        mock_load_model.return_value = mock_model
        
        # Initialize the classifier
        classifier = TextRegionClassifier(model_path="/tmp/models/classifier")
        
        # Create a test image region
        image_region = np.random.rand(100, 300, 3).astype(np.float32)
        
        # Classify the region
        text_type, confidence = classifier.classify_region(image_region)
        
        # Verify classification
        assert text_type == "handwritten"
        assert confidence == 0.8
        mock_model.predict.assert_called_once()


def test_text_region_classifier_classify_region_typed():
    """Test that TextRegionClassifier correctly identifies typed text."""
    with patch('tensorflow.keras.models.load_model') as mock_load_model:
        # Configure the mock
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([[0.2]])  # Low value indicates typed
        mock_load_model.return_value = mock_model
        
        # Initialize the classifier
        classifier = TextRegionClassifier(model_path="/tmp/models/classifier")
        
        # Create a test image region
        image_region = np.random.rand(100, 300, 3).astype(np.float32)
        
        # Classify the region
        text_type, confidence = classifier.classify_region(image_region)
        
        # Verify classification
        assert text_type == "typed"
        assert confidence == 0.8  # 1.0 - 0.2 = 0.8
        mock_model.predict.assert_called_once()


# ===== Tests for TextRegion =====

def test_text_region_initialization():
    """Test that TextRegion initializes correctly."""
    # Create a test image
    image = np.random.rand(100, 300, 3).astype(np.float32)
    
    # Create a bounding box
    bounding_box = {
        'top': 0.1,
        'left': 0.2,
        'bottom': 0.3,
        'right': 0.5
    }
    
    # Initialize the text region
    region = TextRegion(image=image, bounding_box=bounding_box, text_type="typed", confidence=0.9)
    
    # Verify initialization
    assert region.image is image
    assert region.bounding_box == bounding_box
    assert region.text_type == "typed"
    assert region.confidence == 0.9
    assert region.extracted_text is None
    assert region.text_confidence is None


def test_text_region_to_field_location():
    """Test that TextRegion correctly converts to FieldLocation."""
    # Create a test image
    image = np.random.rand(100, 300, 3).astype(np.float32)
    
    # Create a bounding box
    bounding_box = {
        'top': 0.1,
        'left': 0.2,
        'bottom': 0.3,
        'right': 0.5
    }
    
    # Initialize the text region
    region = TextRegion(image=image, bounding_box=bounding_box)
    
    # Convert to field location
    location = region.to_field_location(page=2)
    
    # Verify conversion
    assert location['page'] == 2
    assert location['top'] == 0.1
    assert location['left'] == 0.2
    assert location['bottom'] == 0.3
    assert location['right'] == 0.5
    assert location['width'] == 0.3  # right - left
    assert location['height'] == 0.2  # bottom - top


# ===== Tests for HybridRecognitionModel =====

def test_hybrid_model_initialization(mock_hybrid_model):
    """Test that HybridRecognitionModel initializes correctly."""
    # Verify that the model was initialized with the correct components
    assert mock_hybrid_model.region_detector is not None
    assert mock_hybrid_model.region_classifier is not None
    assert mock_hybrid_model.typed_model is not None
    assert mock_hybrid_model.handwritten_model is not None


def test_detect_text_regions(mock_hybrid_model, sample_mixed_document_image):
    """Test that HybridRecognitionModel correctly detects text regions."""
    # Detect text regions
    bounding_boxes = mock_hybrid_model.detect_text_regions(sample_mixed_document_image)
    
    # Verify detection
    assert len(bounding_boxes) == 3  # We expect 3 regions from our mock
    assert all('top' in bbox and 'left' in bbox and 'bottom' in bbox and 'right' in bbox for bbox in bounding_boxes)
    assert all('confidence' in bbox for bbox in bounding_boxes)


def test_extract_text_from_region_typed(mock_hybrid_model):
    """Test that HybridRecognitionModel correctly extracts text from typed regions."""
    # Create a typed text region
    image = np.ones((100, 300, 3), dtype=np.float32) * 0.9  # Light background with dark text
    bounding_box = {'top': 0.1, 'left': 0.2, 'bottom': 0.3, 'right': 0.5}
    region = TextRegion(image=image, bounding_box=bounding_box, text_type="typed", confidence=0.9)
    
    # Extract text
    text, confidence = mock_hybrid_model.extract_text_from_region(region)
    
    # Verify extraction
    assert text == "Sample typed text"  # From our mock_typed_model
    assert confidence == 0.95


def test_extract_text_from_region_handwritten(mock_hybrid_model):
    """Test that HybridRecognitionModel correctly extracts text from handwritten regions."""
    # Create a handwritten text region
    image = np.ones((100, 300, 3), dtype=np.float32) * 0.3  # Darker, more variable
    bounding_box = {'top': 0.4, 'left': 0.2, 'bottom': 0.6, 'right': 0.5}
    region = TextRegion(image=image, bounding_box=bounding_box, text_type="handwritten", confidence=0.85)
    
    # Extract text
    text, confidence = mock_hybrid_model.extract_text_from_region(region)
    
    # Verify extraction
    assert text == "Sample handwritten text"  # From our mock_handwritten_model
    assert confidence == 0.85


def test_extract_text_from_region_unclassified(mock_hybrid_model, mock_text_region_classifier):
    """Test that HybridRecognitionModel correctly classifies and extracts text from unclassified regions."""
    # Create an unclassified text region (no text_type specified)
    image = np.ones((100, 300, 3), dtype=np.float32) * 0.9  # Light background with dark text
    bounding_box = {'top': 0.1, 'left': 0.2, 'bottom': 0.3, 'right': 0.5}
    region = TextRegion(image=image, bounding_box=bounding_box)  # No text_type
    
    # Configure the classifier mock to return "typed"
    mock_text_region_classifier.classify_region.return_value = ("typed", 0.9)
    
    # Extract text
    text, confidence = mock_hybrid_model.extract_text_from_region(region)
    
    # Verify classification and extraction
    mock_text_region_classifier.classify_region.assert_called_once()
    assert region.text_type == "typed"  # Should be set by the model
    assert region.confidence == 0.9
    assert text == "Sample typed text"  # From our mock_typed_model
    assert confidence == 0.95


def test_process_document(mock_hybrid_model, sample_mixed_document_image):
    """Test that HybridRecognitionModel correctly processes a complete document."""
    # Process the document
    result = mock_hybrid_model.process_document(sample_mixed_document_image, document_type="application_form")
    
    # Verify the result structure
    assert 'extraction_id' in result
    assert 'fields' in result
    assert 'metadata' in result
    assert 'raw_text' in result
    assert 'low_confidence_fields' in result
    assert 'requires_verification' in result
    assert 'extraction_timestamp' in result
    
    # Verify that fields were extracted
    assert len(result['fields']) > 0
    
    # Verify metadata
    assert result['metadata']['document_type'] == "application_form"
    assert result['metadata']['model_id'] == "hybrid_text_ocr"
    assert result['metadata']['extraction_status'] == "success"
    assert 'processing_time' in result['metadata']


def test_model_switching_accuracy(mock_hybrid_model, sample_mixed_document_image):
    """Test that HybridRecognitionModel correctly switches between models based on text type."""
    # Process the document
    result = mock_hybrid_model.process_document(sample_mixed_document_image)
    
    # Check if both typed and handwritten text were recognized
    typed_found = False
    handwritten_found = False
    
    for field_name, field in result['fields'].items():
        if field['metadata']['text_type'] == "typed":
            typed_found = True
            assert "Sample typed text" in field['value']
        elif field['metadata']['text_type'] == "handwritten":
            handwritten_found = True
            assert "Sample handwritten text" in field['value']
    
    # Verify that both text types were found and processed correctly
    assert typed_found, "No typed text was recognized"
    assert handwritten_found, "No handwritten text was recognized"


def test_confidence_scoring(mock_hybrid_model, sample_mixed_document_image):
    """Test that HybridRecognitionModel correctly assigns confidence scores."""
    # Process the document
    result = mock_hybrid_model.process_document(sample_mixed_document_image)
    
    # Check confidence scores for each field
    for field_name, field in result['fields'].items():
        assert 'confidence' in field
        assert 0 <= field['confidence']['score'] <= 1
        
        # Verify that confidence scores match the expected values from our mocks
        if field['metadata']['text_type'] == "typed":
            assert field['confidence']['score'] == 0.95
        elif field['metadata']['text_type'] == "handwritten":
            assert field['confidence']['score'] == 0.85


def test_performance_metrics(mock_hybrid_model, sample_mixed_document_image):
    """Test that HybridRecognitionModel meets performance requirements."""
    # Measure processing time
    start_time = time.time()
    result = mock_hybrid_model.process_document(sample_mixed_document_image)
    processing_time = time.time() - start_time
    
    # Verify that processing time is within acceptable limits
    # The actual limit would depend on the specific requirements
    # For this test, we'll use a generous limit since we're using mocks
    assert processing_time < 5.0, f"Processing time {processing_time:.2f}s exceeds 5.0s limit"
    
    # Verify that the processing time in the result matches our measurement
    assert abs(result['metadata']['processing_time'] - processing_time) < 0.1


# ===== Tests for HybridRecognitionModelFactory =====

def test_hybrid_model_factory_create_model():
    """Test that HybridRecognitionModelFactory correctly creates models."""
    with patch('src.models.hybrid_recognition_model.HybridRecognitionModel') as mock_model_class, \
         patch('src.config.tensorflow_config.DEFAULT_HYBRID_MODEL_PARAMS', {'default_param': 'value'}):
        
        # Configure the mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Create a model with default parameters
        model = HybridRecognitionModelFactory.create_model()
        
        # Verify that the model was created with the correct parameters
        mock_model_class.assert_called_once()
        args, kwargs = mock_model_class.call_args
        assert 'default_param' in args[0]
        assert args[0]['default_param'] == 'value'
        
        # Reset the mock
        mock_model_class.reset_mock()
        
        # Create a model with a specific document type
        model = HybridRecognitionModelFactory.create_model(document_type="application_form")
        
        # Verify that the model was created with adjusted parameters
        mock_model_class.assert_called_once()
        
        # Reset the mock
        mock_model_class.reset_mock()
        
        # Create a model with custom parameters
        custom_params = {'custom_param': 'custom_value'}
        model = HybridRecognitionModelFactory.create_model(custom_parameters=custom_params)
        
        # Verify that the model was created with the custom parameters
        mock_model_class.assert_called_once()
        args, kwargs = mock_model_class.call_args
        assert 'custom_param' in args[0]
        assert args[0]['custom_param'] == 'custom_value'


def test_hybrid_model_factory_document_type_specific_parameters():
    """Test that HybridRecognitionModelFactory applies document-specific parameters."""
    with patch('src.models.hybrid_recognition_model.HybridRecognitionModel') as mock_model_class, \
         patch('src.config.tensorflow_config.DEFAULT_HYBRID_MODEL_PARAMS', {'confidence_threshold': 0.7}):
        
        # Configure the mock
        mock_model = MagicMock()
        mock_model_class.return_value = mock_model
        
        # Create models for different document types
        model1 = HybridRecognitionModelFactory.create_model(document_type="application_form")
        args1, _ = mock_model_class.call_args
        
        mock_model_class.reset_mock()
        model2 = HybridRecognitionModelFactory.create_model(document_type="tax_return")
        args2, _ = mock_model_class.call_args
        
        mock_model_class.reset_mock()
        model3 = HybridRecognitionModelFactory.create_model(document_type="bank_statement")
        args3, _ = mock_model_class.call_args
        
        # Verify that different parameters were applied based on document type
        assert args1[0]['confidence_threshold'] != args2[0]['confidence_threshold']
        assert args2[0]['confidence_threshold'] != args3[0]['confidence_threshold']
        assert args1[0]['confidence_threshold'] != args3[0]['confidence_threshold']


# ===== Integration Tests =====

def test_end_to_end_processing(mock_hybrid_model, sample_mixed_document_image):
    """Test the complete end-to-end document processing workflow."""
    # Process the document
    result = mock_hybrid_model.process_document(sample_mixed_document_image, document_type="application_form")
    
    # Verify that the document was processed successfully
    assert result['metadata']['extraction_status'] == "success"
    
    # Verify that text was extracted
    assert result['raw_text'] != ""
    
    # Verify that fields were extracted
    assert len(result['fields']) > 0
    
    # Verify that both typed and handwritten text were recognized
    text_types = [field['metadata']['text_type'] for field in result['fields'].values()]
    assert "typed" in text_types
    assert "handwritten" in text_types
    
    # Verify that confidence scores were assigned
    assert all('confidence' in field for field in result['fields'].values())
    
    # Verify that low-confidence fields were identified
    low_confidence_fields = result['low_confidence_fields']
    requires_verification = result['requires_verification']
    assert isinstance(low_confidence_fields, list)
    assert isinstance(requires_verification, bool)
    assert requires_verification == (len(low_confidence_fields) > 0)


def test_json_structure_compliance(mock_hybrid_model, sample_mixed_document_image):
    """Test that the extraction result complies with the required JSON structure."""
    # Process the document
    result = mock_hybrid_model.process_document(sample_mixed_document_image)
    
    # Verify the top-level structure
    required_keys = [
        'extraction_id', 'fields', 'metadata', 'raw_text',
        'low_confidence_fields', 'requires_verification',
        'extraction_timestamp', 'schema_version', 'document_type'
    ]
    for key in required_keys:
        assert key in result, f"Missing required key: {key}"
    
    # Verify the metadata structure
    required_metadata_keys = [
        'extraction_id', 'document_id', 'model_id', 'model_version',
        'document_type', 'page_count', 'language', 'processing_node',
        'extraction_status', 'processing_time', 'warnings', 'errors'
    ]
    for key in required_metadata_keys:
        assert key in result['metadata'], f"Missing required metadata key: {key}"
    
    # Verify the field structure
    for field_name, field in result['fields'].items():
        required_field_keys = [
            'field_name', 'field_type', 'value', 'raw_text', 'confidence',
            'location', 'alternatives', 'metadata', 'requires_verification',
            'verification_reason', 'extraction_timestamp'
        ]
        for key in required_field_keys:
            assert key in field, f"Missing required field key: {key} in field {field_name}"
        
        # Verify the confidence structure
        assert 'score' in field['confidence']
        assert 'level' in field['confidence']
        
        # Verify the location structure
        required_location_keys = [
            'page', 'top', 'left', 'bottom', 'right', 'width', 'height'
        ]
        for key in required_location_keys:
            assert key in field['location'], f"Missing required location key: {key} in field {field_name}"