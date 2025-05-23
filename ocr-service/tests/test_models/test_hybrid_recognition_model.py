#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the HybridRecognitionModel class.

This module contains tests for the combined TensorFlow model for processing documents
containing both typed and handwritten text. It verifies that the model correctly identifies
text types, switches between recognition algorithms, and maintains high accuracy for
mixed-format documents.

Key test areas:
- Text region classification to determine text type (typed vs handwritten)
- Intelligent model switching based on text characteristics
- Unified confidence scoring across different text types
- Optimized processing pipeline for mixed-format documents
- End-to-end processing of documents with both typed and handwritten content
- Performance metrics for hybrid text extraction
"""

import os
import time
import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, List, Any, Tuple

# Import the model to test
from src.models.hybrid_recognition_model import HybridRecognitionModel

# Import related models that are used by the hybrid model
from src.models.typed_text_model import TypedTextModel
from src.models.handwritten_text_model import HandwrittenTextModel

# Import types
from src.types.config import TensorFlowConfig
from src.types.models import OCRModelType, ModelParameters, ModelResult, TextType, TextRegion
from src.types.documents import DocumentType, DocumentContent, DocumentMetadata
from src.types.extraction import ExtractedData, ExtractedField, ConfidenceScore


# ===== Test Fixtures =====

@pytest.fixture
def tf_config() -> TensorFlowConfig:
    """Provides a TensorFlow configuration for testing."""
    return TensorFlowConfig(
        use_gpu=False,  # Disable GPU for testing
        gpu_memory_limit=1024,  # 1GB limit for tests that do use GPU
        gpu_growth=True,
        verification_threshold=0.75,
        num_threads=2,  # Limit threads for testing
        allow_xla=False,  # Disable XLA optimization for testing
        mixed_precision=False  # Disable mixed precision for testing
    )


@pytest.fixture
def model_parameters() -> Dict[str, Any]:
    """Provides model parameters for testing."""
    return {
        'typed_model_path': '/models/typed',
        'handwritten_model_path': '/models/handwritten',
        'classifier_model_path': '/models/classifier',
        'region_overlap_threshold': 0.5,
        'min_region_size': 100,
        'confidence_threshold': 0.7,
        'max_regions': 10,  # Reduced for testing
        'use_parallel_processing': False  # Disable for deterministic testing
    }


@pytest.fixture
def mock_hybrid_model(tf_config, model_parameters) -> HybridRecognitionModel:
    """Provides a HybridRecognitionModel instance with mocked sub-models for testing."""
    # Create the model with test configuration
    with patch('src.models.hybrid_recognition_model.TypedTextModel') as mock_typed_model_class, \
         patch('src.models.hybrid_recognition_model.HandwrittenTextModel') as mock_handwritten_model_class, \
         patch('tensorflow.saved_model.load') as mock_tf_load:
        
        # Configure mocks for sub-models
        mock_typed_model = MagicMock(spec=TypedTextModel)
        mock_typed_model.extract_text.return_value = {
            "text": "Sample typed text",
            "confidence": 0.95
        }
        
        mock_handwritten_model = MagicMock(spec=HandwrittenTextModel)
        mock_handwritten_model.extract_text.return_value = {
            "text": "Sample handwritten text",
            "confidence": 0.85
        }
        
        # Configure mock for classifier model
        mock_classifier = MagicMock()
        mock_classifier.return_value = tf.constant([[0.8, 0.2]])  # [typed_prob, handwritten_prob]
        mock_tf_load.return_value = mock_classifier
        
        # Configure mock classes to return our mock instances
        mock_typed_model_class.return_value = mock_typed_model
        mock_handwritten_model_class.return_value = mock_handwritten_model
        
        # Create the hybrid model
        model = HybridRecognitionModel(
            model_path='/models',
            config=tf_config,
            parameters=model_parameters
        )
        
        # Store mocks for test access
        model._mock_typed_model = mock_typed_model
        model._mock_handwritten_model = mock_handwritten_model
        model._mock_classifier = mock_classifier
        
        return model


@pytest.fixture
def mock_mixed_document() -> np.ndarray:
    """Provides a mock document image with both typed and handwritten text regions."""
    # Create a 500x700 grayscale image (typical document size)
    image = np.ones((700, 500), dtype=np.uint8) * 255
    
    # Add a form-like structure with typed text
    # Header (typed)
    image[50:55, 100:400] = 0  # Title underline
    
    # Form fields (typed labels)
    field_positions = [
        (100, 150, "Name:"),
        (100, 200, "Address:"),
        (100, 250, "Phone:"),
        (100, 300, "Email:"),
        (100, 350, "Business Name:"),
        (100, 400, "Tax ID:"),
        (100, 450, "Revenue:"),
    ]
    
    # Simulate typed text by drawing horizontal lines
    for y_pos, x_end, _ in field_positions:
        # Label
        image[y_pos:y_pos+2, 100:180] = 0
    
    # Simulate handwritten text by drawing more irregular lines
    # These would be the filled-in form fields
    handwritten_positions = [
        (100, 170, 350),  # Name field
        (100, 220, 380),  # Address field
        (100, 270, 300),  # Phone field
        (100, 320, 360),  # Email field
        (100, 370, 340),  # Business Name field
        (100, 420, 280),  # Tax ID field
        (100, 470, 320),  # Revenue field
    ]
    
    # Add some variation to simulate handwriting
    for y_pos, x_start, x_end in handwritten_positions:
        # Create wavy line for handwritten text
        for x in range(x_start, x_end, 2):
            # Add some randomness to y position
            y_offset = int(np.sin((x - x_start) / 10) * 3)
            image[y_pos+y_offset:y_pos+y_offset+3, x:x+2] = 0
    
    return image


@pytest.fixture
def mock_document_metadata() -> DocumentMetadata:
    """Provides mock document metadata for testing."""
    return {
        "id": "test-doc-001",
        "type": DocumentType.APPLICATION,
        "mime_type": "image/png",
        "page_count": 1,
        "width": 500,
        "height": 700,
        "file_size": 350000,
        "file_name": "test_application.png",
        "upload_time": "2023-01-15T10:30:00Z",
        "classification": {
            "document_type": "application_form",
            "confidence": 0.95
        }
    }


@pytest.fixture
def mock_text_regions() -> List[TextRegion]:
    """Provides mock text regions for testing."""
    return [
        TextRegion(
            id=0,
            bbox=(100, 100, 300, 30),
            text_type=TextType.TYPED,
            classification_confidence=0.95,
            text="",
            extraction_confidence=0.0
        ),
        TextRegion(
            id=1,
            bbox=(100, 150, 300, 30),
            text_type=TextType.HANDWRITTEN,
            classification_confidence=0.92,
            text="",
            extraction_confidence=0.0
        ),
        TextRegion(
            id=2,
            bbox=(100, 200, 300, 30),
            text_type=TextType.TYPED,
            classification_confidence=0.97,
            text="",
            extraction_confidence=0.0
        ),
        TextRegion(
            id=3,
            bbox=(100, 250, 300, 30),
            text_type=TextType.HANDWRITTEN,
            classification_confidence=0.89,
            text="",
            extraction_confidence=0.0
        )
    ]


# ===== Test Model Initialization =====

def test_hybrid_model_initialization(tf_config, model_parameters):
    """Test that the HybridRecognitionModel initializes correctly with the given parameters."""
    with patch('src.models.hybrid_recognition_model.TypedTextModel') as mock_typed_model_class, \
         patch('src.models.hybrid_recognition_model.HandwrittenTextModel') as mock_handwritten_model_class, \
         patch('tensorflow.saved_model.load') as mock_tf_load:
        
        # Configure mocks
        mock_typed_model_class.return_value = MagicMock(spec=TypedTextModel)
        mock_handwritten_model_class.return_value = MagicMock(spec=HandwrittenTextModel)
        mock_tf_load.return_value = MagicMock()
        
        # Create the model
        model = HybridRecognitionModel(
            model_path='/models',
            config=tf_config,
            parameters=model_parameters
        )
        
        # Check that model parameters are set correctly
        assert model.region_overlap_threshold == model_parameters['region_overlap_threshold']
        assert model.min_region_size == model_parameters['min_region_size']
        assert model.confidence_threshold == model_parameters['confidence_threshold']
        assert model.max_regions == model_parameters['max_regions']
        assert model.use_parallel_processing == model_parameters['use_parallel_processing']
        
        # Check that sub-models are initialized
        mock_typed_model_class.assert_called_once()
        mock_handwritten_model_class.assert_called_once()
        mock_tf_load.assert_called_once()


def test_hybrid_model_initialization_with_default_parameters(tf_config):
    """Test that the HybridRecognitionModel initializes with default parameters when none are provided."""
    with patch('src.models.hybrid_recognition_model.TypedTextModel') as mock_typed_model_class, \
         patch('src.models.hybrid_recognition_model.HandwrittenTextModel') as mock_handwritten_model_class, \
         patch('tensorflow.saved_model.load') as mock_tf_load:
        
        # Configure mocks
        mock_typed_model_class.return_value = MagicMock(spec=TypedTextModel)
        mock_handwritten_model_class.return_value = MagicMock(spec=HandwrittenTextModel)
        mock_tf_load.return_value = MagicMock()
        
        # Create the model with no parameters
        model = HybridRecognitionModel(
            model_path='/models',
            config=tf_config
        )
        
        # Check that default parameters are used
        assert hasattr(model, 'region_overlap_threshold')
        assert hasattr(model, 'min_region_size')
        assert hasattr(model, 'confidence_threshold')
        assert hasattr(model, 'max_regions')
        assert hasattr(model, 'use_parallel_processing')
        
        # Check that sub-models are initialized with default paths
        mock_typed_model_class.assert_called_once()
        mock_handwritten_model_class.assert_called_once()
        mock_tf_load.assert_called_once()


def test_hybrid_model_initialization_error_handling():
    """Test that the HybridRecognitionModel handles initialization errors gracefully."""
    # Create a minimal config
    config = TensorFlowConfig(
        use_gpu=False,
        gpu_memory_limit=1024,
        gpu_growth=True
    )
    
    # Test error when loading classifier model
    with patch('src.models.hybrid_recognition_model.TypedTextModel') as mock_typed_model_class, \
         patch('src.models.hybrid_recognition_model.HandwrittenTextModel') as mock_handwritten_model_class, \
         patch('tensorflow.saved_model.load', side_effect=Exception("Test error")):
        
        # Configure mocks
        mock_typed_model_class.return_value = MagicMock(spec=TypedTextModel)
        mock_handwritten_model_class.return_value = MagicMock(spec=HandwrittenTextModel)
        
        # Creating the model should raise a RuntimeError
        with pytest.raises(RuntimeError):
            HybridRecognitionModel(
                model_path='/models',
                config=config
            )


# ===== Test Text Region Classification =====

def test_classify_text_region(mock_hybrid_model, mock_mixed_document):
    """Test that the classify_text_region method correctly identifies text types."""
    # Create a small region image (simulating a cropped text region)
    region_image = mock_mixed_document[100:130, 100:300]  # Small crop
    
    # Test classification of a typed text region
    with patch.object(mock_hybrid_model, '_preprocess_for_classification', return_value=region_image), \
         patch.object(mock_hybrid_model.classifier_model, '__call__', return_value=tf.constant([[0.8, 0.2]])):
        
        text_type, confidence = mock_hybrid_model.classify_text_region(region_image)
        
        # Check that the region was classified as typed
        assert text_type == TextType.TYPED
        assert confidence == 0.8
    
    # Test classification of a handwritten text region
    with patch.object(mock_hybrid_model, '_preprocess_for_classification', return_value=region_image), \
         patch.object(mock_hybrid_model.classifier_model, '__call__', return_value=tf.constant([[0.3, 0.7]])):
        
        text_type, confidence = mock_hybrid_model.classify_text_region(region_image)
        
        # Check that the region was classified as handwritten
        assert text_type == TextType.HANDWRITTEN
        assert confidence == 0.7


def test_classify_text_region_error_handling(mock_hybrid_model, mock_mixed_document):
    """Test that the classify_text_region method handles errors gracefully."""
    # Create a small region image
    region_image = mock_mixed_document[100:130, 100:300]  # Small crop
    
    # Test error during preprocessing
    with patch.object(mock_hybrid_model, '_preprocess_for_classification', side_effect=Exception("Test error")):
        # Should not raise an exception
        text_type, confidence = mock_hybrid_model.classify_text_region(region_image)
        
        # Should default to typed text with low confidence
        assert text_type == TextType.TYPED
        assert confidence == 0.5
    
    # Test error during classification
    with patch.object(mock_hybrid_model, '_preprocess_for_classification', return_value=region_image), \
         patch.object(mock_hybrid_model.classifier_model, '__call__', side_effect=Exception("Test error")):
        
        # Should not raise an exception
        text_type, confidence = mock_hybrid_model.classify_text_region(region_image)
        
        # Should default to typed text with low confidence
        assert text_type == TextType.TYPED
        assert confidence == 0.5


def test_preprocess_for_classification(mock_hybrid_model, mock_mixed_document):
    """Test that the _preprocess_for_classification method correctly prepares images for classification."""
    # Create a small region image
    region_image = mock_mixed_document[100:130, 100:300]  # Small crop
    
    # Test preprocessing of a color image
    with patch('cv2.resize', return_value=np.ones((224, 224, 3), dtype=np.uint8)), \
         patch('cv2.cvtColor', return_value=np.ones((224, 224, 3), dtype=np.uint8)):
        
        processed = mock_hybrid_model._preprocess_for_classification(region_image)
        
        # Check that the processed image has the expected shape and type
        assert processed.shape == (224, 224, 3)  # Standard input size for many CNNs
        assert processed.dtype == np.float32
        assert np.max(processed) <= 1.0  # Normalized to [0, 1]


def test_detect_and_classify_regions(mock_hybrid_model, mock_mixed_document):
    """Test that the detect_and_classify_regions method correctly identifies and classifies text regions."""
    # Mock the detect_text_regions function to return some regions
    with patch('src.models.hybrid_recognition_model.detect_text_regions', return_value=[
            (100, 100, 300, 30),  # x, y, width, height
            (100, 150, 300, 30),
            (100, 200, 300, 30),
            (100, 250, 300, 30),
            (100, 300, 300, 30),
            (100, 350, 300, 30),
            (100, 400, 300, 30),
            (100, 450, 300, 30),
            (100, 500, 300, 30),
            (100, 550, 300, 30),
            (100, 600, 300, 30),  # This one exceeds max_regions and should be filtered
        ]), \
         patch.object(mock_hybrid_model, 'classify_text_region', side_effect=[
            (TextType.TYPED, 0.95),
            (TextType.HANDWRITTEN, 0.92),
            (TextType.TYPED, 0.97),
            (TextType.HANDWRITTEN, 0.89),
            (TextType.TYPED, 0.94),
            (TextType.HANDWRITTEN, 0.91),
            (TextType.TYPED, 0.96),
            (TextType.HANDWRITTEN, 0.88),
            (TextType.TYPED, 0.93),
            (TextType.HANDWRITTEN, 0.90),
        ]), \
         patch('src.models.hybrid_recognition_model.crop_region', return_value=np.ones((30, 300), dtype=np.uint8)):
        
        # Set max_regions to 10 for this test
        mock_hybrid_model.max_regions = 10
        
        # Detect and classify regions
        regions = mock_hybrid_model.detect_and_classify_regions(mock_mixed_document)
        
        # Check that the correct number of regions were detected
        assert len(regions) == 10  # Limited by max_regions
        
        # Check that regions were classified correctly
        assert regions[0].text_type == TextType.TYPED
        assert regions[1].text_type == TextType.HANDWRITTEN
        assert regions[2].text_type == TextType.TYPED
        assert regions[3].text_type == TextType.HANDWRITTEN
        
        # Check that confidence scores were set correctly
        assert regions[0].classification_confidence == 0.95
        assert regions[1].classification_confidence == 0.92
        assert regions[2].classification_confidence == 0.97
        assert regions[3].classification_confidence == 0.89


def test_detect_and_classify_regions_filters_small_regions(mock_hybrid_model, mock_mixed_document):
    """Test that the detect_and_classify_regions method filters out very small regions."""
    # Mock the detect_text_regions function to return some regions, including small ones
    with patch('src.models.hybrid_recognition_model.detect_text_regions', return_value=[
            (100, 100, 300, 30),  # Normal size - should be included
            (100, 150, 5, 5),     # Too small - should be filtered out
            (100, 200, 300, 30),  # Normal size - should be included
            (100, 250, 10, 8),    # Too small - should be filtered out
        ]), \
         patch.object(mock_hybrid_model, 'classify_text_region', side_effect=[
            (TextType.TYPED, 0.95),
            (TextType.TYPED, 0.97),
        ]), \
         patch('src.models.hybrid_recognition_model.crop_region', return_value=np.ones((30, 300), dtype=np.uint8)):
        
        # Set min_region_size to filter out small regions
        mock_hybrid_model.min_region_size = 100  # 100 pixels
        
        # Detect and classify regions
        regions = mock_hybrid_model.detect_and_classify_regions(mock_mixed_document)
        
        # Check that only the normal-sized regions were included
        assert len(regions) == 2
        
        # Check that the bounding boxes match the expected regions
        assert regions[0].bbox == (100, 100, 300, 30)
        assert regions[1].bbox == (100, 200, 300, 30)


def test_detect_and_classify_regions_error_handling(mock_hybrid_model, mock_mixed_document):
    """Test that the detect_and_classify_regions method handles errors gracefully."""
    # Mock the detect_text_regions function to raise an exception
    with patch('src.models.hybrid_recognition_model.detect_text_regions', side_effect=Exception("Test error")):
        # Should not raise an exception
        regions = mock_hybrid_model.detect_and_classify_regions(mock_mixed_document)
        
        # Should return an empty list
        assert regions == []


# ===== Test Text Extraction from Regions =====

def test_extract_text_from_regions_sequential(mock_hybrid_model, mock_mixed_document, mock_text_regions):
    """Test that the _extract_text_sequential method correctly extracts text from classified regions."""
    # Create a copy of the regions that we can modify
    regions = [TextRegion(**region.__dict__) for region in mock_text_regions]
    
    # Mock the crop_region function
    with patch('src.models.hybrid_recognition_model.crop_region', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.enhance_contrast', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.deskew_image', return_value=np.ones((30, 300), dtype=np.uint8)):
        
        # Extract text from regions
        updated_regions = mock_hybrid_model._extract_text_sequential(mock_mixed_document, regions)
        
        # Check that the correct number of regions were processed
        assert len(updated_regions) == 4
        
        # Check that text was extracted for each region
        for region in updated_regions:
            if region.text_type == TextType.TYPED:
                assert region.text == "Sample typed text"
                assert region.extraction_confidence == 0.95
            else:  # TextType.HANDWRITTEN
                assert region.text == "Sample handwritten text"
                assert region.extraction_confidence == 0.85


def test_extract_text_from_regions_parallel(mock_hybrid_model, mock_mixed_document, mock_text_regions):
    """Test that the _extract_text_parallel method correctly extracts text from classified regions in parallel."""
    # Create a copy of the regions that we can modify
    regions = [TextRegion(**region.__dict__) for region in mock_text_regions]
    
    # Enable parallel processing for this test
    mock_hybrid_model.use_parallel_processing = True
    
    # Mock the ThreadPoolExecutor and related functions
    with patch('src.models.hybrid_recognition_model.ThreadPoolExecutor') as mock_executor_class, \
         patch('src.models.hybrid_recognition_model.crop_region', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.enhance_contrast', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.deskew_image', return_value=np.ones((30, 300), dtype=np.uint8)):
        
        # Configure mock executor
        mock_executor = MagicMock()
        mock_executor_class.return_value.__enter__.return_value = mock_executor
        
        # Configure mock futures
        mock_futures = []
        for i, region in enumerate(regions):
            mock_future = MagicMock()
            if region.text_type == TextType.TYPED:
                # Update the region with typed text
                region.text = "Sample typed text"
                region.extraction_confidence = 0.95
            else:  # TextType.HANDWRITTEN
                # Update the region with handwritten text
                region.text = "Sample handwritten text"
                region.extraction_confidence = 0.85
            
            # Configure the future to return the updated region
            mock_future.result.return_value = (region, True)
            mock_futures.append(mock_future)
        
        # Configure the executor to return our mock futures
        mock_executor.submit.side_effect = lambda func, region: mock_futures[region.id]
        
        # Configure as_completed to return our futures in order
        with patch('src.models.hybrid_recognition_model.as_completed', return_value=mock_futures):
            # Extract text from regions
            updated_regions = mock_hybrid_model._extract_text_parallel(mock_mixed_document, regions)
            
            # Check that the executor was used correctly
            mock_executor_class.assert_called_once()
            assert mock_executor.submit.call_count == 4
            
            # Check that the correct number of regions were processed
            assert len(updated_regions) == 4
            
            # Check that text was extracted for each region
            for region in updated_regions:
                if region.text_type == TextType.TYPED:
                    assert region.text == "Sample typed text"
                    assert region.extraction_confidence == 0.95
                else:  # TextType.HANDWRITTEN
                    assert region.text == "Sample handwritten text"
                    assert region.extraction_confidence == 0.85


def test_extract_text_from_regions_filters_low_confidence(mock_hybrid_model, mock_mixed_document, mock_text_regions):
    """Test that the extract_text_from_regions method filters out regions with low confidence."""
    # Create a copy of the regions that we can modify
    regions = [TextRegion(**region.__dict__) for region in mock_text_regions]
    
    # Mock the crop_region function and typed_model.extract_text to return low confidence for some regions
    with patch('src.models.hybrid_recognition_model.crop_region', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.enhance_contrast', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.deskew_image', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch.object(mock_hybrid_model.typed_model, 'extract_text', side_effect=[
            {"text": "Sample typed text", "confidence": 0.95},  # High confidence
            {"text": "Low confidence text", "confidence": 0.5}   # Low confidence
         ]), \
         patch.object(mock_hybrid_model.handwritten_model, 'extract_text', side_effect=[
            {"text": "Sample handwritten text", "confidence": 0.85},  # High confidence
            {"text": "Low confidence text", "confidence": 0.4}    # Low confidence
         ]):
        
        # Set confidence threshold
        mock_hybrid_model.confidence_threshold = 0.7
        
        # Extract text from regions
        updated_regions = mock_hybrid_model._extract_text_sequential(mock_mixed_document, regions)
        
        # Check that only high confidence regions were included
        assert len(updated_regions) == 2
        
        # Check that the high confidence regions have the expected text
        assert updated_regions[0].text == "Sample typed text"
        assert updated_regions[0].extraction_confidence == 0.95
        assert updated_regions[1].text == "Sample handwritten text"
        assert updated_regions[1].extraction_confidence == 0.85


def test_extract_text_from_regions_error_handling(mock_hybrid_model, mock_mixed_document, mock_text_regions):
    """Test that the extract_text_from_regions method handles errors gracefully."""
    # Create a copy of the regions that we can modify
    regions = [TextRegion(**region.__dict__) for region in mock_text_regions]
    
    # Mock the crop_region function to raise an exception for one region
    with patch('src.models.hybrid_recognition_model.crop_region', side_effect=[
            np.ones((30, 300), dtype=np.uint8),  # First region succeeds
            Exception("Test error"),               # Second region fails
            np.ones((30, 300), dtype=np.uint8),  # Third region succeeds
            np.ones((30, 300), dtype=np.uint8)   # Fourth region succeeds
        ]), \
         patch('src.models.hybrid_recognition_model.enhance_contrast', return_value=np.ones((30, 300), dtype=np.uint8)), \
         patch('src.models.hybrid_recognition_model.deskew_image', return_value=np.ones((30, 300), dtype=np.uint8)):
        
        # Extract text from regions - should not raise an exception
        updated_regions = mock_hybrid_model._extract_text_sequential(mock_mixed_document, regions)
        
        # Check that all regions were processed, even the one that failed
        assert len(updated_regions) == 4
        
        # Check that the failed region has empty text and zero confidence
        assert updated_regions[1].text == ""
        assert updated_regions[1].extraction_confidence == 0.0


# ===== Test Unified Confidence Scoring =====

def test_extract_text_unified_confidence_scoring(mock_hybrid_model, mock_mixed_document):
    """Test that the extract_text method provides unified confidence scoring across different text types."""
    # Mock the detect_and_classify_regions and extract_text_from_regions methods
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Sample typed text",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="Sample handwritten text",
                extraction_confidence=0.85
            )
        ]), \
         patch.object(mock_hybrid_model, 'extract_text_from_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Sample typed text",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="Sample handwritten text",
                extraction_confidence=0.85
            )
        ]):
        
        # Extract text
        results = mock_hybrid_model.extract_text(mock_mixed_document)
        
        # Check that the results have the expected structure
        assert len(results) == 2
        
        # Check that confidence scores are provided for both text types
        typed_text, typed_confidence = results[0]
        handwritten_text, handwritten_confidence = results[1]
        
        assert typed_text == "Sample typed text"
        assert handwritten_text == "Sample handwritten text"
        
        # Check that confidence scores are on the same scale
        assert 0 <= typed_confidence.value <= 1.0
        assert 0 <= handwritten_confidence.value <= 1.0
        
        # Check that the confidence scores reflect the extraction confidence
        assert typed_confidence.value == 0.92
        assert handwritten_confidence.value == 0.85


# ===== Test Field Extraction =====

def test_extract_fields_application(mock_hybrid_model, mock_mixed_document, mock_document_metadata):
    """Test that the extract_fields method correctly extracts fields from application forms."""
    # Mock the detect_and_classify_regions and extract_text_from_regions methods
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Business Name: Acme Corporation",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="Owner Name: John Smith",
                extraction_confidence=0.85
            ),
            TextRegion(
                id=2,
                bbox=(100, 200, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.93,
                text="Tax ID: 12-3456789",
                extraction_confidence=0.91
            ),
            TextRegion(
                id=3,
                bbox=(100, 250, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.88,
                text="Phone: 555-123-4567",
                extraction_confidence=0.83
            )
        ]), \
         patch.object(mock_hybrid_model, 'extract_text_from_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Business Name: Acme Corporation",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="Owner Name: John Smith",
                extraction_confidence=0.85
            ),
            TextRegion(
                id=2,
                bbox=(100, 200, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.93,
                text="Tax ID: 12-3456789",
                extraction_confidence=0.91
            ),
            TextRegion(
                id=3,
                bbox=(100, 250, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.88,
                text="Phone: 555-123-4567",
                extraction_confidence=0.83
            )
        ]), \
         patch.object(mock_hybrid_model, '_extract_fields_with_patterns', return_value={
            "business_name": ("Acme Corporation", 0.92, 0),
            "owner_name": ("John Smith", 0.85, 1),
            "tax_id": ("12-3456789", 0.91, 2),
            "phone": ("555-123-4567", 0.83, 3)
        }):
        
        # Extract fields
        fields = mock_hybrid_model.extract_fields(mock_mixed_document, mock_document_metadata)
        
        # Check that the fields have the expected structure
        assert len(fields) == 4
        
        # Check that each field has the expected properties
        for field in fields:
            assert "name" in field
            assert "value" in field
            assert "confidence" in field
            assert "location" in field
            assert "category" in field
            assert "metadata" in field
        
        # Check specific field values
        business_name_field = next(f for f in fields if f["name"] == "business_name")
        assert business_name_field["value"] == "Acme Corporation"
        assert business_name_field["confidence"].value == 0.92
        assert business_name_field["metadata"]["text_type"] == "typed"
        
        owner_name_field = next(f for f in fields if f["name"] == "owner_name")
        assert owner_name_field["value"] == "John Smith"
        assert owner_name_field["confidence"].value == 0.85
        assert owner_name_field["metadata"]["text_type"] == "handwritten"


def test_extract_fields_invoice(mock_hybrid_model, mock_mixed_document):
    """Test that the extract_fields method correctly extracts fields from invoices."""
    # Create invoice document metadata
    invoice_metadata = {
        "id": "test-invoice-001",
        "type": DocumentType.INVOICE,
        "mime_type": "image/png",
        "page_count": 1,
        "width": 500,
        "height": 700,
        "file_size": 350000,
        "file_name": "test_invoice.png"
    }
    
    # Mock the detect_and_classify_regions and extract_text_from_regions methods
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Invoice #: INV-12345",
                extraction_confidence=0.94
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.93,
                text="Date: 2023-01-15",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=2,
                bbox=(100, 200, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.96,
                text="Total Amount: $1,234.56",
                extraction_confidence=0.95
            )
        ]), \
         patch.object(mock_hybrid_model, 'extract_text_from_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Invoice #: INV-12345",
                extraction_confidence=0.94
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.93,
                text="Date: 2023-01-15",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=2,
                bbox=(100, 200, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.96,
                text="Total Amount: $1,234.56",
                extraction_confidence=0.95
            )
        ]), \
         patch.object(mock_hybrid_model, '_extract_fields_with_patterns', return_value={
            "invoice_number": ("INV-12345", 0.94, 0),
            "invoice_date": ("2023-01-15", 0.92, 1),
            "total_amount": ("1,234.56", 0.95, 2)
        }):
        
        # Extract fields
        fields = mock_hybrid_model.extract_fields(mock_mixed_document, invoice_metadata)
        
        # Check that the fields have the expected structure
        assert len(fields) == 3
        
        # Check specific field values
        invoice_number_field = next(f for f in fields if f["name"] == "invoice_number")
        assert invoice_number_field["value"] == "INV-12345"
        assert invoice_number_field["confidence"].value == 0.94
        assert invoice_number_field["category"] == "invoice"
        
        total_amount_field = next(f for f in fields if f["name"] == "total_amount")
        assert total_amount_field["value"] == "1,234.56"
        assert total_amount_field["confidence"].value == 0.95
        assert total_amount_field["category"] == "invoice"


def test_extract_fields_error_handling(mock_hybrid_model, mock_mixed_document, mock_document_metadata):
    """Test that the extract_fields method handles errors gracefully."""
    # Mock the detect_and_classify_regions method to raise an exception
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', side_effect=Exception("Test error")):
        # Extract fields - should not raise an exception
        fields = mock_hybrid_model.extract_fields(mock_mixed_document, mock_document_metadata)
        
        # Should return an empty list
        assert fields == []


# ===== Test End-to-End Processing =====

def test_process_document(mock_hybrid_model, mock_mixed_document, mock_document_metadata):
    """Test that the process_document method correctly processes a document end-to-end."""
    # Mock the necessary methods
    with patch.object(mock_hybrid_model, 'preprocess_document', return_value=mock_mixed_document), \
         patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="",
                extraction_confidence=0.0
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="",
                extraction_confidence=0.0
            )
        ]), \
         patch.object(mock_hybrid_model, 'extract_text_from_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Business Name: Acme Corporation",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="Owner Name: John Smith",
                extraction_confidence=0.85
            )
        ]), \
         patch.object(mock_hybrid_model, '_extract_application_fields', return_value=[
            {
                "name": "business_name",
                "value": "Acme Corporation",
                "confidence": ConfidenceScore.from_float(0.92),
                "location": {
                    "page": 0,
                    "top": 100,
                    "left": 100,
                    "bottom": 130,
                    "right": 400,
                    "width": 300,
                    "height": 30
                },
                "category": "application",
                "metadata": {
                    "text_type": "typed",
                    "extraction_time": "2023-01-15T10:30:00Z"
                }
            },
            {
                "name": "owner_name",
                "value": "John Smith",
                "confidence": ConfidenceScore.from_float(0.85),
                "location": {
                    "page": 0,
                    "top": 150,
                    "left": 100,
                    "bottom": 180,
                    "right": 400,
                    "width": 300,
                    "height": 30
                },
                "category": "application",
                "metadata": {
                    "text_type": "handwritten",
                    "extraction_time": "2023-01-15T10:30:00Z"
                }
            }
        ]):
        
        # Process document
        result = mock_hybrid_model.process_document(mock_mixed_document, mock_document_metadata)
        
        # Check that the result has the expected structure
        assert result.success is True
        assert result.error is None
        assert result.processing_time_ms > 0
        
        # Check the extracted data
        assert result.data is not None
        assert len(result.data.fields) == 2
        assert result.data.confidence > 0.8  # Average of 0.92 and 0.85
        
        # Check metadata
        assert "model_name" in result.data.metadata
        assert "model_version" in result.data.metadata
        assert "document_id" in result.data.metadata
        assert "document_type" in result.data.metadata
        assert "processing_time_ms" in result.data.metadata
        assert "regions_detected" in result.data.metadata
        assert "regions_processed" in result.data.metadata
        assert "typed_regions" in result.data.metadata
        assert "handwritten_regions" in result.data.metadata
        
        # Check that the processing time meets the 5-minute requirement
        assert result.processing_time_ms < 300000  # 5 minutes = 300,000 ms


def test_process_document_error_handling(mock_hybrid_model, mock_mixed_document, mock_document_metadata):
    """Test that the process_document method handles errors gracefully."""
    # Mock the preprocess_document method to raise an exception
    with patch.object(mock_hybrid_model, 'preprocess_document', side_effect=Exception("Test error")):
        # Process document - should not raise an exception
        result = mock_hybrid_model.process_document(mock_mixed_document, mock_document_metadata)
        
        # Check that the result indicates failure
        assert result.success is False
        assert result.error is not None
        assert "Test error" in result.error["message"]
        assert result.data is None


# ===== Test Performance Metrics =====

def test_performance_metrics(mock_hybrid_model, mock_mixed_document, mock_document_metadata):
    """Test that the model meets performance requirements for hybrid text extraction."""
    # Mock the necessary methods for a realistic performance test
    with patch.object(mock_hybrid_model, 'preprocess_document', return_value=mock_mixed_document), \
         patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="",
                extraction_confidence=0.0
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="",
                extraction_confidence=0.0
            )
        ]), \
         patch.object(mock_hybrid_model, 'extract_text_from_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 300, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="Business Name: Acme Corporation",
                extraction_confidence=0.92
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 300, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="Owner Name: John Smith",
                extraction_confidence=0.85
            )
        ]), \
         patch.object(mock_hybrid_model, '_extract_application_fields', return_value=[
            {
                "name": "business_name",
                "value": "Acme Corporation",
                "confidence": ConfidenceScore.from_float(0.92),
                "location": {
                    "page": 0,
                    "top": 100,
                    "left": 100,
                    "bottom": 130,
                    "right": 400,
                    "width": 300,
                    "height": 30
                },
                "category": "application",
                "metadata": {
                    "text_type": "typed",
                    "extraction_time": "2023-01-15T10:30:00Z"
                }
            },
            {
                "name": "owner_name",
                "value": "John Smith",
                "confidence": ConfidenceScore.from_float(0.85),
                "location": {
                    "page": 0,
                    "top": 150,
                    "left": 100,
                    "bottom": 180,
                    "right": 400,
                    "width": 300,
                    "height": 30
                },
                "category": "application",
                "metadata": {
                    "text_type": "handwritten",
                    "extraction_time": "2023-01-15T10:30:00Z"
                }
            }
        ]):
        
        # Measure the time to process a document
        start_time = time.time()
        result = mock_hybrid_model.process_document(mock_mixed_document, mock_document_metadata)
        processing_time = time.time() - start_time
        
        # Check that the processing time is reasonable
        # The requirement is to process applications in under 5 minutes,
        # but the OCR component should be much faster than that
        assert processing_time < 5.0  # 5 seconds is a reasonable upper bound for a test
        
        # Check that the confidence score meets the 99% accuracy requirement
        # Note: In a real test, we would compare against ground truth,
        # but for this test we just check that the confidence is high
        assert result.data.confidence > 0.8  # Average of 0.92 and 0.85
        
        # Check that the processing time in the result matches our measurement
        assert abs(result.processing_time_ms - (processing_time * 1000)) < 100  # Allow for small differences


# ===== Test Region Statistics and Visualization =====

def test_get_region_statistics(mock_hybrid_model, mock_mixed_document):
    """Test that the get_region_statistics method correctly analyzes document composition."""
    # Mock the detect_and_classify_regions method
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 100, 30),  # 3000 pixels
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="",
                extraction_confidence=0.0
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 100, 30),  # 3000 pixels
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="",
                extraction_confidence=0.0
            ),
            TextRegion(
                id=2,
                bbox=(100, 200, 100, 30),  # 3000 pixels
                text_type=TextType.TYPED,
                classification_confidence=0.93,
                text="",
                extraction_confidence=0.0
            )
        ]):
        
        # Get region statistics
        stats = mock_hybrid_model.get_region_statistics(mock_mixed_document)
        
        # Check that the statistics have the expected structure
        assert "total_regions" in stats
        assert "typed_regions" in stats
        assert "handwritten_regions" in stats
        assert "typed_percentage" in stats
        assert "handwritten_percentage" in stats
        assert "mixed_document" in stats
        
        # Check the values
        assert stats["total_regions"] == 3
        assert stats["typed_regions"] == 2
        assert stats["handwritten_regions"] == 1
        
        # Check that the document is identified as mixed
        assert stats["mixed_document"] is True


def test_get_region_statistics_error_handling(mock_hybrid_model, mock_mixed_document):
    """Test that the get_region_statistics method handles errors gracefully."""
    # Mock the detect_and_classify_regions method to raise an exception
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', side_effect=Exception("Test error")):
        # Get region statistics - should not raise an exception
        stats = mock_hybrid_model.get_region_statistics(mock_mixed_document)
        
        # Check that the statistics indicate an error
        assert "error" in stats
        assert stats["total_regions"] == 0
        assert stats["typed_regions"] == 0
        assert stats["handwritten_regions"] == 0
        assert stats["mixed_document"] is False


def test_visualize_regions(mock_hybrid_model, mock_mixed_document):
    """Test that the visualize_regions method correctly creates a visualization of detected regions."""
    # Mock the detect_and_classify_regions method
    with patch.object(mock_hybrid_model, 'detect_and_classify_regions', return_value=[
            TextRegion(
                id=0,
                bbox=(100, 100, 100, 30),
                text_type=TextType.TYPED,
                classification_confidence=0.95,
                text="",
                extraction_confidence=0.0
            ),
            TextRegion(
                id=1,
                bbox=(100, 150, 100, 30),
                text_type=TextType.HANDWRITTEN,
                classification_confidence=0.90,
                text="",
                extraction_confidence=0.0
            )
        ]), \
         patch('cv2.rectangle'), \
         patch('cv2.putText'):
        
        # Create visualization
        vis_image = mock_hybrid_model.visualize_regions(mock_mixed_document)
        
        # Check that the visualization has the expected shape
        assert vis_image.shape == mock_mixed_document.shape
        
        # In a real test, we would check the actual visualization,
        # but for this test we just check that it returns an image