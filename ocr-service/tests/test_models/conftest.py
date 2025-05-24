import os
import json
import pytest
import numpy as np
import tensorflow as tf
from pathlib import Path
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Tuple, Optional, Union

# Add docstring for the module
"""
Conftest module for OCR model tests.

This module provides shared test fixtures and utilities for OCR model tests.
It includes fixtures for document test data, TensorFlow test environment setup,
model initialization, and helper functions for measuring model accuracy and performance.

The fixtures in this module enable consistent test setup across all model test modules
and simplify test maintenance by centralizing common test functionality.
"""

# Path constants
TEST_DATA_DIR = Path(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'test_data'))
TYPED_DOCS_DIR = TEST_DATA_DIR / 'typed_documents'
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / 'handwritten_documents'
MIXED_DOCS_DIR = TEST_DATA_DIR / 'mixed_documents'
TABLES_DIR = TEST_DATA_DIR / 'tables'

# Load metadata once to avoid repeated file I/O during tests
@pytest.fixture(scope="session")
def metadata():
    """Load the global test metadata file."""
    with open(TEST_DATA_DIR / 'metadata.json', 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def typed_document_manifest():
    """Load the typed document manifest."""
    with open(TYPED_DOCS_DIR / 'sample_manifest.json', 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def handwritten_document_manifest():
    """Load the handwritten document manifest."""
    with open(HANDWRITTEN_DOCS_DIR / 'sample_manifest.json', 'r') as f:
        return json.load(f)


@pytest.fixture(scope="session")
def mixed_document_manifest():
    """Load the mixed document manifest."""
    with open(MIXED_DOCS_DIR / 'sample_manifest.json', 'r') as f:
        return json.load(f)


# TensorFlow environment setup
@pytest.fixture(scope="session")
def tf_gpu_mock():
    """Mock TensorFlow GPU environment for testing.
    
    This fixture ensures tests can run in environments without GPU hardware
    by mocking the TensorFlow GPU detection and configuration. It addresses the
    requirement that TensorFlow OCR processing requires CUDA-compatible GPU
    acceleration, allowing tests to run in CI/CD environments that may not have
    GPU hardware available.
    """
    # Create a mock GPU device
    mock_gpu = MagicMock()
    mock_gpu.name = '/device:GPU:0'
    mock_gpu.device_type = 'GPU'
    
    # Patch TensorFlow's device detection to return our mock GPU
    with patch('tensorflow.config.list_physical_devices') as mock_list_devices, \
         patch('tensorflow.config.experimental.set_memory_growth') as mock_set_memory_growth, \
         patch('tensorflow.config.experimental.set_virtual_device_configuration') as mock_set_config:
        
        # Configure the mock to return a GPU device
        mock_list_devices.return_value = [mock_gpu]
        
        # Yield to allow tests to run with the mock in place
        yield {
            'mock_gpu': mock_gpu,
            'mock_list_devices': mock_list_devices,
            'mock_set_memory_growth': mock_set_memory_growth,
            'mock_set_config': mock_set_config
        }


@pytest.fixture
def tf_session():
    """Create a TensorFlow session for testing.
    
    This fixture provides an isolated TensorFlow session for each test,
    ensuring that model operations don't interfere with each other.
    """
    # Create a new TensorFlow graph and session for isolation
    graph = tf.Graph()
    with graph.as_default():
        session = tf.compat.v1.Session(graph=graph)
        with session.as_default():
            yield session


# Test image fixtures
@pytest.fixture
def sample_typed_image():
    """Create a sample image for typed text testing.
    
    Returns a numpy array representing a document image with typed text.
    """
    # Create a blank white image (800x600, 3 channels, white background)
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    return image


@pytest.fixture
def sample_handwritten_image():
    """Create a sample image for handwritten text testing.
    
    Returns a numpy array representing a document image with handwritten text.
    """
    # Create a blank white image (800x600, 3 channels, white background)
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    return image


@pytest.fixture
def sample_mixed_image():
    """Create a sample image for mixed text testing.
    
    Returns a numpy array representing a document image with both typed and handwritten text.
    """
    # Create a blank white image (800x600, 3 channels, white background)
    image = np.ones((800, 600, 3), dtype=np.uint8) * 255
    return image


@pytest.fixture
def sample_table_image():
    """Create a sample image for table structure testing.
    
    Returns a numpy array representing a document image with a table structure.
    """
    # Create a blank white image (1000x800, 3 channels, white background)
    image = np.ones((1000, 800, 3), dtype=np.uint8) * 255
    return image


# Model configuration fixtures
@pytest.fixture
def base_model_config():
    """Provide a base configuration for OCR models."""
    return {
        'model_path': '/tmp/test_model',
        'confidence_threshold': 0.75,
        'batch_size': 1,
        'image_size': (800, 600),
        'channels': 3,
        'use_gpu': True,
        'language': 'en'
    }


@pytest.fixture
def typed_model_config(base_model_config):
    """Provide configuration for typed text OCR model."""
    config = base_model_config.copy()
    config.update({
        'model_type': 'typed',
        'preprocessing': {
            'denoise': True,
            'deskew': True,
            'normalize': True
        },
        'post_processing': {
            'spell_check': True,
            'grammar_check': False
        }
    })
    return config


@pytest.fixture
def handwritten_model_config(base_model_config):
    """Provide configuration for handwritten text OCR model."""
    config = base_model_config.copy()
    config.update({
        'model_type': 'handwritten',
        'preprocessing': {
            'denoise': True,
            'deskew': True,
            'normalize': True,
            'enhance_contrast': True
        },
        'post_processing': {
            'spell_check': True,
            'grammar_check': False,
            'context_correction': True
        }
    })
    return config


@pytest.fixture
def hybrid_model_config(base_model_config):
    """Provide configuration for hybrid text OCR model."""
    config = base_model_config.copy()
    config.update({
        'model_type': 'hybrid',
        'preprocessing': {
            'denoise': True,
            'deskew': True,
            'normalize': True,
            'enhance_contrast': True,
            'region_classification': True
        },
        'post_processing': {
            'spell_check': True,
            'grammar_check': False,
            'context_correction': True
        },
        'region_classifier_threshold': 0.8
    })
    return config


@pytest.fixture
def structure_model_config(base_model_config):
    """Provide configuration for document structure recognition model."""
    config = base_model_config.copy()
    config.update({
        'model_type': 'structure',
        'preprocessing': {
            'denoise': True,
            'deskew': True,
            'normalize': True
        },
        'detection': {
            'tables': True,
            'forms': True,
            'sections': True,
            'fields': True
        },
        'min_confidence': 0.7
    })
    return config


# Mock model fixtures
@pytest.fixture
def mock_base_model(tf_gpu_mock):
    """Create a mock base OCR model for testing."""
    with patch('ocr_service.src.models.base_model.BaseModel') as mock_model:
        # Configure the mock to return expected values
        instance = mock_model.return_value
        instance.preprocess_image.return_value = np.ones((224, 224, 3), dtype=np.float32)
        instance.load_model.return_value = None
        instance.get_confidence_score.return_value = 0.95
        
        yield instance


@pytest.fixture
def mock_typed_model(mock_base_model):
    """Create a mock typed text OCR model for testing."""
    with patch('ocr_service.src.models.typed_text_model.TypedTextModel') as mock_model:
        # Configure the mock to return expected values
        instance = mock_model.return_value
        instance.preprocess_image.return_value = np.ones((224, 224, 3), dtype=np.float32)
        instance.extract_text.return_value = {
            'text': 'Sample typed text',
            'confidence': 0.95,
            'bounding_box': [10, 10, 100, 30]
        }
        instance.get_confidence_score.return_value = 0.95
        
        yield instance


@pytest.fixture
def mock_handwritten_model(mock_base_model):
    """Create a mock handwritten text OCR model for testing."""
    with patch('ocr_service.src.models.handwritten_text_model.HandwrittenTextModel') as mock_model:
        # Configure the mock to return expected values
        instance = mock_model.return_value
        instance.preprocess_image.return_value = np.ones((224, 224, 3), dtype=np.float32)
        instance.extract_text.return_value = {
            'text': 'Sample handwritten text',
            'confidence': 0.85,
            'bounding_box': [10, 10, 100, 30]
        }
        instance.get_confidence_score.return_value = 0.85
        
        yield instance


@pytest.fixture
def mock_hybrid_model(mock_base_model):
    """Create a mock hybrid text OCR model for testing."""
    with patch('ocr_service.src.models.hybrid_recognition_model.HybridRecognitionModel') as mock_model:
        # Configure the mock to return expected values
        instance = mock_model.return_value
        instance.preprocess_image.return_value = np.ones((224, 224, 3), dtype=np.float32)
        instance.classify_region.return_value = 'typed'
        instance.extract_text.return_value = {
            'text': 'Sample mixed text',
            'confidence': 0.90,
            'bounding_box': [10, 10, 100, 30],
            'text_type': 'mixed'
        }
        instance.get_confidence_score.return_value = 0.90
        
        yield instance


@pytest.fixture
def mock_structure_model(mock_base_model):
    """Create a mock document structure recognition model for testing."""
    with patch('ocr_service.src.models.structure_recognition_model.StructureRecognitionModel') as mock_model:
        # Configure the mock to return expected values
        instance = mock_model.return_value
        instance.preprocess_image.return_value = np.ones((224, 224, 3), dtype=np.float32)
        instance.detect_structure.return_value = {
            'tables': [
                {'x': 10, 'y': 10, 'width': 500, 'height': 300, 'confidence': 0.95}
            ],
            'forms': [
                {'x': 10, 'y': 350, 'width': 500, 'height': 200, 'confidence': 0.90}
            ],
            'sections': [
                {'x': 10, 'y': 10, 'width': 500, 'height': 550, 'confidence': 0.98}
            ]
        }
        instance.get_confidence_score.return_value = 0.95
        
        yield instance


@pytest.fixture
def mock_model_factory():
    """Create a mock model factory for testing."""
    with patch('ocr_service.src.models.model_factory.ModelFactory') as mock_factory:
        # Configure the mock to return expected values
        instance = mock_factory.return_value
        
        # Configure get_model to return different models based on document type
        def get_model_side_effect(doc_type, **kwargs):
            if doc_type == 'typed':
                return MagicMock(name='TypedTextModel')
            elif doc_type == 'handwritten':
                return MagicMock(name='HandwrittenTextModel')
            elif doc_type == 'mixed':
                return MagicMock(name='HybridRecognitionModel')
            elif doc_type == 'structure':
                return MagicMock(name='StructureRecognitionModel')
            else:
                return MagicMock(name='BaseModel')
        
        instance.get_model.side_effect = get_model_side_effect
        
        yield instance


# Helper functions for tests
@pytest.fixture
def accuracy_calculator():
    """Provide a function to calculate OCR accuracy metrics.
    
    This fixture returns a function that calculates character and word-level accuracy
    between predicted OCR text and expected ground truth text. It's essential for
    validating that the OCR models meet the 99% accuracy requirement specified in
    the technical specification.
    """
    def calculate_accuracy(predicted_text: str, expected_text: str) -> Dict[str, float]:
        """Calculate accuracy metrics between predicted and expected text.
        
        Args:
            predicted_text: The text extracted by the OCR model
            expected_text: The ground truth text
            
        Returns:
            Dictionary containing accuracy metrics:
            - character_accuracy: Character-level accuracy
            - word_accuracy: Word-level accuracy
            - exact_match: Boolean indicating exact match
        """
        # Character-level accuracy
        if not expected_text:
            return {'character_accuracy': 0.0, 'word_accuracy': 0.0, 'exact_match': False}
            
        # Calculate Levenshtein distance for character-level accuracy
        import Levenshtein
        char_distance = Levenshtein.distance(predicted_text, expected_text)
        char_accuracy = max(0.0, 1.0 - (char_distance / len(expected_text)))
        
        # Word-level accuracy
        predicted_words = predicted_text.split()
        expected_words = expected_text.split()
        
        if not expected_words:
            return {'character_accuracy': char_accuracy, 'word_accuracy': 0.0, 'exact_match': False}
            
        # Count matching words
        word_matches = sum(1 for p, e in zip(predicted_words, expected_words) if p == e)
        word_accuracy = word_matches / len(expected_words) if expected_words else 0.0
        
        # Exact match
        exact_match = predicted_text == expected_text
        
        return {
            'character_accuracy': char_accuracy,
            'word_accuracy': word_accuracy,
            'exact_match': exact_match
        }
    
    return calculate_accuracy


@pytest.fixture
def performance_timer():
    """Provide a function to measure model performance.
    
    This fixture returns a function that measures execution time and memory usage
    of model operations. It's critical for ensuring that the OCR service meets the
    performance requirement of processing applications in under 5 minutes from
    receipt to completion as specified in the technical specification.
    """
    def measure_performance(func, *args, **kwargs):
        """Measure execution time and memory usage of a function.
        
        Args:
            func: The function to measure
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            Dictionary containing performance metrics:
            - execution_time: Time taken to execute the function (in seconds)
            - peak_memory: Peak memory usage during execution (in MB)
            - result: The result returned by the function
        """
        import time
        import tracemalloc
        
        # Start memory tracking
        tracemalloc.start()
        
        # Measure execution time
        start_time = time.time()
        result = func(*args, **kwargs)
        execution_time = time.time() - start_time
        
        # Get peak memory usage
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        
        return {
            'execution_time': execution_time,
            'peak_memory': peak / (1024 * 1024),  # Convert to MB
            'result': result
        }
    
    return measure_performance


@pytest.fixture
def document_preprocessor():
    """Provide utilities for document preprocessing in tests.
    
    This fixture returns a class with methods for preprocessing document images
    before OCR processing. It implements various preprocessing techniques that
    are essential for achieving the 99% data extraction accuracy required by
    the technical specification.
    """
    class DocumentPreprocessor:
        @staticmethod
        def normalize_image(image: np.ndarray) -> np.ndarray:
            """Normalize image for model input."""
            # Convert to float32 and scale to [0, 1]
            normalized = image.astype(np.float32) / 255.0
            return normalized
        
        @staticmethod
        def resize_image(image: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
            """Resize image to target dimensions."""
            import cv2
            return cv2.resize(image, target_size)
        
        @staticmethod
        def apply_preprocessing(image: np.ndarray, config: Dict[str, Any]) -> np.ndarray:
            """Apply preprocessing steps based on configuration."""
            import cv2
            result = image.copy()
            
            # Apply preprocessing steps based on config
            if config.get('denoise', False):
                # Apply denoising
                result = cv2.fastNlMeansDenoisingColored(result, None, 10, 10, 7, 21)
                
            if config.get('deskew', False):
                # Convert to grayscale for deskewing
                if len(result.shape) == 3:
                    gray = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
                else:
                    gray = result
                    
                # Find skew angle and rotate
                # This is a simplified version for testing
                # In a real implementation, this would detect the actual skew angle
                angle = 0  # Assume no skew for testing
                (h, w) = gray.shape[:2]
                center = (w // 2, h // 2)
                M = cv2.getRotationMatrix2D(center, angle, 1.0)
                result = cv2.warpAffine(result, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            
            if config.get('normalize', False):
                # Normalize image
                result = DocumentPreprocessor.normalize_image(result)
                
            if config.get('enhance_contrast', False):
                # Convert to LAB color space and enhance contrast
                if len(result.shape) == 3 and result.shape[2] == 3:
                    lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
                    l, a, b = cv2.split(lab)
                    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                    cl = clahe.apply(l)
                    limg = cv2.merge((cl, a, b))
                    result = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
            
            return result
    
    return DocumentPreprocessor()


@pytest.fixture
def confidence_score_validator():
    """Provide a function to validate confidence scores.
    
    This fixture returns a function that validates confidence scores against a threshold.
    It's essential for implementing the requirement to flag low-confidence extractions
    for human verification, which supports the 93% reduction in manual processing
    through automation as specified in the technical specification.
    """
    def validate_confidence(scores: Dict[str, float], threshold: float = 0.75) -> Dict[str, Any]:
        """Validate confidence scores against threshold.
        
        Args:
            scores: Dictionary of field names to confidence scores
            threshold: Minimum acceptable confidence threshold
            
        Returns:
            Dictionary containing validation results:
            - valid_fields: List of fields with confidence above threshold
            - invalid_fields: List of fields with confidence below threshold
            - overall_confidence: Average confidence across all fields
            - meets_threshold: Boolean indicating if all fields meet threshold
        """
        valid_fields = []
        invalid_fields = []
        
        for field, score in scores.items():
            if score >= threshold:
                valid_fields.append(field)
            else:
                invalid_fields.append(field)
        
        overall_confidence = sum(scores.values()) / len(scores) if scores else 0.0
        meets_threshold = len(invalid_fields) == 0
        
        return {
            'valid_fields': valid_fields,
            'invalid_fields': invalid_fields,
            'overall_confidence': overall_confidence,
            'meets_threshold': meets_threshold
        }
    
    return validate_confidence