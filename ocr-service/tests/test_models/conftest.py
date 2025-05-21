#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test fixtures and utilities for OCR model tests.

This module provides shared test fixtures and utilities for OCR model tests, including:
- Document test data fixtures (typed, handwritten, mixed)
- TensorFlow test environment setup with GPU mocking
- Model initialization and configuration fixtures
- Accuracy and performance measurement utilities
- Document preprocessing utilities

These fixtures enable consistent test setup across all model test modules and simplify
test maintenance.
"""

import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

import numpy as np
import pytest
import tensorflow as tf
from PIL import Image

# Mock imports for testing without actual GPU
from unittest.mock import MagicMock, patch

# Import project modules
from ocr_service.src.types.config import TensorFlowConfig
from ocr_service.src.types.documents import DocumentContent, DocumentMetadata, DocumentType
from ocr_service.src.types.extraction import ConfidenceScore, ExtractedData, ExtractedField
from ocr_service.src.types.models import ModelParameters, ModelResult
from ocr_service.src.utils.image_utils import normalize_image, preprocess_image


# Constants
TEST_DATA_DIR = Path("../test_data")
METADATA_FILE = TEST_DATA_DIR / "metadata.json"
TYPED_DOCS_DIR = TEST_DATA_DIR / "typed_documents"
HANDWRITTEN_DOCS_DIR = TEST_DATA_DIR / "handwritten_documents"
MIXED_DOCS_DIR = TEST_DATA_DIR / "mixed_documents"
TABLES_DIR = TEST_DATA_DIR / "tables"
FORMS_DIR = TEST_DATA_DIR / "forms"
IMAGES_DIR = TEST_DATA_DIR / "images"


# ===== TensorFlow Environment Setup Fixtures =====

@pytest.fixture(scope="session")
def tf_config() -> TensorFlowConfig:
    """
    Provides a TensorFlow configuration for testing.
    
    This fixture creates a TensorFlow configuration with GPU disabled by default
    to ensure tests can run in environments without GPU access.
    
    Returns:
        TensorFlowConfig: Configuration for TensorFlow tests
    """
    return TensorFlowConfig(
        use_gpu=False,
        gpu_memory_limit=1024,  # 1GB limit for tests that do use GPU
        gpu_growth=True,
        verification_threshold=0.75,
        num_threads=2,  # Limit threads for testing
        allow_xla=False,  # Disable XLA optimization for testing
        mixed_precision=False  # Disable mixed precision for testing
    )


@pytest.fixture(scope="session")
def mock_gpu_environment():
    """
    Mocks TensorFlow GPU environment for testing.
    
    This fixture patches TensorFlow GPU-related functions to simulate a GPU environment
    without requiring actual GPU hardware. This allows testing GPU-specific code paths
    in environments without GPU access.
    
    Yields:
        None: The patched environment is active during the test
    """
    # Create mock GPU device
    mock_gpu_device = MagicMock()
    mock_gpu_device.name = "/device:GPU:0"
    
    # Patch TensorFlow functions
    with patch("tensorflow.config.list_physical_devices") as mock_list_devices, \
         patch("tensorflow.config.experimental.set_memory_growth") as mock_set_growth, \
         patch("tensorflow.config.experimental.set_virtual_device_configuration") as mock_set_config:
        
        # Configure mocks
        mock_list_devices.return_value = [mock_gpu_device]
        mock_set_growth.return_value = None
        mock_set_config.return_value = None
        
        yield


@pytest.fixture(scope="function")
def tf_session():
    """
    Provides a clean TensorFlow session for each test.
    
    This fixture ensures each test runs with a fresh TensorFlow session to prevent
    state leakage between tests.
    
    Yields:
        None: The clean session is active during the test
    """
    # Clear any existing session
    tf.keras.backend.clear_session()
    
    # Create a new session
    session = tf.compat.v1.Session()
    tf.compat.v1.keras.backend.set_session(session)
    
    yield
    
    # Clean up after test
    session.close()
    tf.keras.backend.clear_session()


# ===== Document Test Data Fixtures =====

@pytest.fixture(scope="session")
def metadata() -> Dict[str, Any]:
    """
    Loads the test data metadata file.
    
    This fixture loads the central metadata file that defines the structure and expected
    OCR results for all test documents.
    
    Returns:
        Dict[str, Any]: The metadata dictionary
    """
    try:
        with open(METADATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        pytest.skip(f"Metadata file not found: {METADATA_FILE}")
    except json.JSONDecodeError:
        pytest.skip(f"Invalid JSON in metadata file: {METADATA_FILE}")


@pytest.fixture(scope="session")
def typed_document_paths(metadata) -> List[Path]:
    """
    Provides paths to typed document test files.
    
    This fixture returns paths to all typed document test files defined in the metadata.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        List[Path]: List of paths to typed document test files
    """
    paths = []
    
    # Extract paths from metadata
    if "documents" in metadata and "typed_documents" in metadata["documents"]:
        for category, documents in metadata["documents"]["typed_documents"].items():
            for doc in documents:
                file_path = TEST_DATA_DIR / doc["file_path"]
                if file_path.exists():
                    paths.append(file_path)
    
    return paths


@pytest.fixture(scope="session")
def handwritten_document_paths(metadata) -> List[Path]:
    """
    Provides paths to handwritten document test files.
    
    This fixture returns paths to all handwritten document test files defined in the metadata.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        List[Path]: List of paths to handwritten document test files
    """
    paths = []
    
    # Extract paths from metadata
    if "documents" in metadata and "handwritten_documents" in metadata["documents"]:
        for category, documents in metadata["documents"]["handwritten_documents"].items():
            for doc in documents:
                file_path = TEST_DATA_DIR / doc["file_path"]
                if file_path.exists():
                    paths.append(file_path)
    
    return paths


@pytest.fixture(scope="session")
def mixed_document_paths(metadata) -> List[Path]:
    """
    Provides paths to mixed document test files.
    
    This fixture returns paths to all mixed document test files (containing both typed
    and handwritten text) defined in the metadata.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        List[Path]: List of paths to mixed document test files
    """
    paths = []
    
    # Extract paths from metadata
    if "documents" in metadata and "mixed_documents" in metadata["documents"]:
        for category, documents in metadata["documents"]["mixed_documents"].items():
            for doc in documents:
                file_path = TEST_DATA_DIR / doc["file_path"]
                if file_path.exists():
                    paths.append(file_path)
    
    return paths


@pytest.fixture(scope="session")
def table_document_paths(metadata) -> List[Path]:
    """
    Provides paths to tabular document test files.
    
    This fixture returns paths to all tabular document test files defined in the metadata.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        List[Path]: List of paths to tabular document test files
    """
    paths = []
    
    # Extract paths from metadata
    if "tables" in metadata:
        for doc in metadata["tables"]:
            file_path = TEST_DATA_DIR / doc["file_path"]
            if file_path.exists():
                paths.append(file_path)
    
    return paths


@pytest.fixture(scope="session")
def form_document_paths(metadata) -> List[Path]:
    """
    Provides paths to form document test files.
    
    This fixture returns paths to all form document test files defined in the metadata.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        List[Path]: List of paths to form document test files
    """
    paths = []
    
    # Extract paths from metadata
    if "forms" in metadata:
        for doc in metadata["forms"]:
            file_path = TEST_DATA_DIR / doc["file_path"]
            if file_path.exists():
                paths.append(file_path)
    
    return paths


@pytest.fixture(scope="session")
def image_document_paths(metadata) -> List[Path]:
    """
    Provides paths to image document test files.
    
    This fixture returns paths to all image document test files defined in the metadata.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        List[Path]: List of paths to image document test files
    """
    paths = []
    
    # Extract paths from metadata
    if "images" in metadata:
        for doc in metadata["images"]:
            file_path = TEST_DATA_DIR / doc["file_path"]
            if file_path.exists():
                paths.append(file_path)
    
    return paths


@pytest.fixture(scope="session")
def document_by_id(metadata) -> Callable[[str], Dict[str, Any]]:
    """
    Provides a function to retrieve document metadata by ID.
    
    This fixture returns a function that can be used to look up document metadata
    by document ID.
    
    Args:
        metadata: The test data metadata
        
    Returns:
        Callable[[str], Dict[str, Any]]: Function to retrieve document metadata by ID
    """
    def _get_document(doc_id: str) -> Dict[str, Any]:
        # Search in typed documents
        if "documents" in metadata:
            for doc_type, categories in metadata["documents"].items():
                for category, documents in categories.items():
                    for doc in documents:
                        if doc.get("id") == doc_id:
                            return doc
        
        # Search in tables
        if "tables" in metadata:
            for doc in metadata["tables"]:
                if doc.get("id") == doc_id:
                    return doc
        
        # Search in forms
        if "forms" in metadata:
            for doc in metadata["forms"]:
                if doc.get("id") == doc_id:
                    return doc
        
        # Search in images
        if "images" in metadata:
            for doc in metadata["images"]:
                if doc.get("id") == doc_id:
                    return doc
        
        # Document not found
        return None
    
    return _get_document


@pytest.fixture(scope="function")
def load_test_document() -> Callable[[Path], Tuple[np.ndarray, DocumentMetadata]]:
    """
    Provides a function to load test documents.
    
    This fixture returns a function that loads a test document from a file path and
    returns the document content and metadata.
    
    Returns:
        Callable[[Path], Tuple[np.ndarray, DocumentMetadata]]: Function to load test documents
    """
    def _load_document(file_path: Path) -> Tuple[np.ndarray, DocumentMetadata]:
        # Check if file exists
        if not file_path.exists():
            raise FileNotFoundError(f"Test document not found: {file_path}")
        
        # Load image using PIL
        try:
            with Image.open(file_path) as img:
                # Convert to RGB if needed
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Convert to numpy array
                image = np.array(img)
                
                # Create document metadata
                metadata = DocumentMetadata(
                    id=file_path.stem,
                    type=DocumentType.APPLICATION,  # Default type
                    mime_type=f"image/{file_path.suffix[1:]}",
                    page_count=1,
                    width=img.width,
                    height=img.height,
                    file_size=file_path.stat().st_size,
                    file_name=file_path.name
                )
                
                return image, metadata
        except Exception as e:
            raise ValueError(f"Failed to load test document {file_path}: {str(e)}")
    
    return _load_document


# ===== Model Initialization Fixtures =====

@pytest.fixture(scope="function")
def mock_typed_text_model(tf_config):
    """
    Provides a mock typed text OCR model for testing.
    
    This fixture creates a mock typed text OCR model that can be used for testing
    without requiring the actual model implementation.
    
    Args:
        tf_config: TensorFlow configuration
        
    Returns:
        MagicMock: Mock typed text OCR model
    """
    from ocr_service.src.models.typed_text_model import TypedTextModel
    
    # Create mock model
    mock_model = MagicMock(spec=TypedTextModel)
    
    # Configure mock methods
    mock_model.model_name = "typed_text_model"
    mock_model.model_version = "1.0.0-test"
    mock_model.config = tf_config
    
    # Mock extract_text method
    def mock_extract_text(image):
        # Return mock result
        return {
            "text": "Mock typed text extraction result",
            "confidence": 0.95,
            "bounding_boxes": [
                {"text": "Mock typed text", "confidence": 0.95, "bbox": [0, 0, 1, 1]}
            ],
            "word_confidences": [0.95, 0.95, 0.95],
            "processing_time": 0.1,
            "page_number": 1,
            "model_type": "TYPED",
            "warnings": [],
            "language": "en"
        }
    
    mock_model.extract_text.side_effect = mock_extract_text
    
    # Mock extract_fields method
    def mock_extract_fields(image, document_type=None):
        # Return mock result
        return {
            "extraction_id": f"typed-{int(time.time())}",
            "fields": {
                "business_name": {
                    "field_name": "business_name",
                    "field_type": "text",
                    "value": "Acme Corporation",
                    "raw_text": "Acme Corporation",
                    "confidence": ConfidenceScore.from_float(0.95),
                    "location": {
                        "page": 1,
                        "top": 0.1,
                        "left": 0.1,
                        "bottom": 0.15,
                        "right": 0.5,
                        "width": 0.4,
                        "height": 0.05
                    },
                    "alternatives": [],
                    "metadata": {
                        "extraction_method": "typed_text_ocr",
                        "validation_result": True
                    },
                    "requires_verification": False,
                    "verification_reason": None,
                    "extraction_timestamp": time.time()
                }
            },
            "tables": [],
            "metadata": {
                "extraction_id": f"typed-{int(time.time())}",
                "document_id": "mock-document",
                "model_id": "typed_text_ocr",
                "model_version": "1.0.0-test",
                "document_type": "APPLICATION",
                "page_count": 1,
                "language": "en",
                "processing_node": "test-node",
                "extraction_status": "success",
                "processing_time": 0.1,
                "warnings": [],
                "errors": []
            },
            "raw_text": "Mock typed text extraction result",
            "low_confidence_fields": [],
            "requires_verification": False,
            "extraction_timestamp": time.time(),
            "schema_version": "1.0",
            "document_type": "APPLICATION"
        }
    
    mock_model.extract_fields.side_effect = mock_extract_fields
    
    return mock_model


@pytest.fixture(scope="function")
def mock_handwritten_text_model(tf_config):
    """
    Provides a mock handwritten text OCR model for testing.
    
    This fixture creates a mock handwritten text OCR model that can be used for testing
    without requiring the actual model implementation.
    
    Args:
        tf_config: TensorFlow configuration
        
    Returns:
        MagicMock: Mock handwritten text OCR model
    """
    from ocr_service.src.models.handwritten_text_model import HandwrittenTextModel
    
    # Create mock model
    mock_model = MagicMock(spec=HandwrittenTextModel)
    
    # Configure mock methods
    mock_model.model_name = "handwritten_text_model"
    mock_model.model_version = "1.0.0-test"
    mock_model.config = tf_config
    
    # Mock extract_text method
    def mock_extract_text(image):
        # Return mock result
        return {
            "text": "Mock handwritten text extraction result",
            "confidence": 0.85,
            "bounding_boxes": [
                {"text": "Mock handwritten text", "confidence": 0.85, "bbox": [0, 0, 1, 1]}
            ],
            "word_confidences": [0.85, 0.85, 0.85],
            "processing_time": 0.2,
            "page_number": 1,
            "model_type": "HANDWRITTEN",
            "warnings": [],
            "language": "en"
        }
    
    mock_model.extract_text.side_effect = mock_extract_text
    
    # Mock extract_fields method
    def mock_extract_fields(image, field_definitions=None):
        # Return mock result
        return {
            "owner_name": {
                "field_name": "owner_name",
                "field_type": "text",
                "value": "John Smith",
                "raw_text": "John Smith",
                "confidence": ConfidenceScore.from_float(0.85),
                "location": {
                    "page": 1,
                    "top": 0.3,
                    "left": 0.1,
                    "bottom": 0.35,
                    "right": 0.5,
                    "width": 0.4,
                    "height": 0.05
                },
                "alternatives": [],
                "metadata": {
                    "extraction_method": "handwritten_text_model",
                    "model_version": "1.0.0-test"
                },
                "requires_verification": False,
                "verification_reason": None,
                "extraction_timestamp": time.time()
            }
        }
    
    mock_model.extract_fields.side_effect = mock_extract_fields
    
    return mock_model


@pytest.fixture(scope="function")
def mock_hybrid_text_model(tf_config):
    """
    Provides a mock hybrid text OCR model for testing.
    
    This fixture creates a mock hybrid text OCR model that can be used for testing
    without requiring the actual model implementation.
    
    Args:
        tf_config: TensorFlow configuration
        
    Returns:
        MagicMock: Mock hybrid text OCR model
    """
    from ocr_service.src.models.hybrid_recognition_model import HybridTextModel
    
    # Create mock model
    mock_model = MagicMock(spec=HybridTextModel)
    
    # Configure mock methods
    mock_model.model_name = "hybrid_text_model"
    mock_model.model_version = "1.0.0-test"
    mock_model.config = tf_config
    
    # Mock extract_text method
    def mock_extract_text(image):
        # Return mock result
        return {
            "text": "Mock hybrid text extraction result with both typed and handwritten text",
            "confidence": 0.90,
            "bounding_boxes": [
                {"text": "Mock typed text", "confidence": 0.95, "bbox": [0, 0, 0.5, 0.5], "text_type": "TYPED"},
                {"text": "Mock handwritten text", "confidence": 0.85, "bbox": [0, 0.5, 0.5, 1.0], "text_type": "HANDWRITTEN"}
            ],
            "word_confidences": [0.95, 0.95, 0.95, 0.85, 0.85, 0.85],
            "processing_time": 0.3,
            "page_number": 1,
            "model_type": "HYBRID",
            "warnings": [],
            "language": "en"
        }
    
    mock_model.extract_text.side_effect = mock_extract_text
    
    # Mock extract_fields method
    def mock_extract_fields(image, document_type=None):
        # Return mock result with both typed and handwritten fields
        return {
            "extraction_id": f"hybrid-{int(time.time())}",
            "fields": {
                "business_name": {
                    "field_name": "business_name",
                    "field_type": "text",
                    "value": "Acme Corporation",
                    "raw_text": "Acme Corporation",
                    "confidence": ConfidenceScore.from_float(0.95),
                    "location": {
                        "page": 1,
                        "top": 0.1,
                        "left": 0.1,
                        "bottom": 0.15,
                        "right": 0.5,
                        "width": 0.4,
                        "height": 0.05
                    },
                    "alternatives": [],
                    "metadata": {
                        "extraction_method": "hybrid_text_model",
                        "text_type": "TYPED"
                    },
                    "requires_verification": False,
                    "verification_reason": None,
                    "extraction_timestamp": time.time()
                },
                "owner_signature": {
                    "field_name": "owner_signature",
                    "field_type": "signature",
                    "value": "John Smith",
                    "raw_text": "John Smith",
                    "confidence": ConfidenceScore.from_float(0.85),
                    "location": {
                        "page": 1,
                        "top": 0.6,
                        "left": 0.1,
                        "bottom": 0.65,
                        "right": 0.5,
                        "width": 0.4,
                        "height": 0.05
                    },
                    "alternatives": [],
                    "metadata": {
                        "extraction_method": "hybrid_text_model",
                        "text_type": "HANDWRITTEN"
                    },
                    "requires_verification": False,
                    "verification_reason": None,
                    "extraction_timestamp": time.time()
                }
            },
            "tables": [],
            "metadata": {
                "extraction_id": f"hybrid-{int(time.time())}",
                "document_id": "mock-document",
                "model_id": "hybrid_text_model",
                "model_version": "1.0.0-test",
                "document_type": "APPLICATION",
                "page_count": 1,
                "language": "en",
                "processing_node": "test-node",
                "extraction_status": "success",
                "processing_time": 0.3,
                "warnings": [],
                "errors": []
            },
            "raw_text": "Mock hybrid text extraction result with both typed and handwritten text",
            "low_confidence_fields": [],
            "requires_verification": False,
            "extraction_timestamp": time.time(),
            "schema_version": "1.0",
            "document_type": "APPLICATION"
        }
    
    mock_model.extract_fields.side_effect = mock_extract_fields
    
    return mock_model


@pytest.fixture(scope="function")
def mock_structure_recognition_model(tf_config):
    """
    Provides a mock structure recognition model for testing.
    
    This fixture creates a mock structure recognition model that can be used for testing
    without requiring the actual model implementation.
    
    Args:
        tf_config: TensorFlow configuration
        
    Returns:
        MagicMock: Mock structure recognition model
    """
    from ocr_service.src.models.structure_recognition_model import StructureRecognitionModel
    
    # Create mock model
    mock_model = MagicMock(spec=StructureRecognitionModel)
    
    # Configure mock methods
    mock_model.model_name = "structure_recognition_model"
    mock_model.model_version = "1.0.0-test"
    mock_model.config = tf_config
    
    # Mock detect_structure method
    def mock_detect_structure(image):
        # Return mock result
        return {
            "document_type": "APPLICATION",
            "confidence": 0.95,
            "sections": [
                {
                    "name": "header",
                    "bbox": [0, 0, 1, 0.1],
                    "confidence": 0.98
                },
                {
                    "name": "business_info",
                    "bbox": [0, 0.1, 1, 0.4],
                    "confidence": 0.96
                },
                {
                    "name": "owner_info",
                    "bbox": [0, 0.4, 1, 0.7],
                    "confidence": 0.95
                },
                {
                    "name": "signature",
                    "bbox": [0, 0.7, 1, 0.9],
                    "confidence": 0.97
                },
                {
                    "name": "footer",
                    "bbox": [0, 0.9, 1, 1],
                    "confidence": 0.98
                }
            ],
            "fields": [
                {
                    "name": "business_name",
                    "bbox": [0.1, 0.15, 0.5, 0.2],
                    "confidence": 0.96,
                    "field_type": "text"
                },
                {
                    "name": "owner_name",
                    "bbox": [0.1, 0.45, 0.5, 0.5],
                    "confidence": 0.95,
                    "field_type": "text"
                },
                {
                    "name": "owner_signature",
                    "bbox": [0.1, 0.75, 0.5, 0.85],
                    "confidence": 0.97,
                    "field_type": "signature"
                }
            ],
            "tables": [],
            "processing_time": 0.2
        }
    
    mock_model.detect_structure.side_effect = mock_detect_structure
    
    return mock_model


# ===== Accuracy and Performance Measurement Utilities =====

def calculate_accuracy(expected: Dict[str, Any], actual: Dict[str, Any]) -> float:
    """
    Calculate accuracy between expected and actual OCR results.
    
    This function compares the expected and actual OCR results and calculates
    an accuracy score based on field value matches.
    
    Args:
        expected: Expected OCR results
        actual: Actual OCR results
        
    Returns:
        float: Accuracy score between 0.0 and 1.0
    """
    if not expected or not actual:
        return 0.0
    
    # Extract fields from results
    expected_fields = expected.get("fields", {})
    actual_fields = actual.get("fields", {})
    
    # Count matches
    total_fields = len(expected_fields)
    if total_fields == 0:
        return 0.0
    
    matches = 0
    for field_name, expected_field in expected_fields.items():
        if field_name in actual_fields:
            actual_field = actual_fields[field_name]
            
            # Compare field values
            expected_value = expected_field.get("value", "")
            actual_value = actual_field.get("value", "")
            
            # Check for exact match
            if expected_value == actual_value:
                matches += 1
            # Check for close match (for numeric values)
            elif isinstance(expected_value, (int, float)) and isinstance(actual_value, (int, float)):
                if abs(expected_value - actual_value) / max(1, abs(expected_value)) < 0.01:
                    matches += 0.8  # Partial credit for close match
            # Check for substring match (for text values)
            elif isinstance(expected_value, str) and isinstance(actual_value, str):
                if expected_value.lower() in actual_value.lower() or actual_value.lower() in expected_value.lower():
                    matches += 0.5  # Partial credit for substring match
    
    return matches / total_fields


def measure_performance(func: Callable, *args, **kwargs) -> Tuple[Any, float]:
    """
    Measure the performance of a function.
    
    This function measures the execution time of a function and returns both the
    function result and the execution time.
    
    Args:
        func: Function to measure
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        Tuple[Any, float]: Tuple of (function_result, execution_time_seconds)
    """
    start_time = time.time()
    result = func(*args, **kwargs)
    execution_time = time.time() - start_time
    
    return result, execution_time


@pytest.fixture(scope="session")
def accuracy_metrics():
    """
    Provides accuracy metrics from the test metadata.
    
    This fixture extracts accuracy targets from the test metadata for different
    document types and text types.
    
    Returns:
        Dict[str, float]: Dictionary of accuracy metrics
    """
    try:
        with open(METADATA_FILE, "r") as f:
            metadata = json.load(f)
            
            # Extract test parameters
            test_params = metadata.get("test_parameters", {})
            
            return {
                "typed_text_accuracy_target": test_params.get("typed_text_accuracy_target", 0.98),
                "handwritten_text_accuracy_target": test_params.get("handwritten_text_accuracy_target", 0.85),
                "mixed_text_accuracy_target": test_params.get("mixed_text_accuracy_target", 0.90),
                "classification_accuracy_target": test_params.get("classification_accuracy_target", 0.95),
                "field_extraction_accuracy_target": test_params.get("field_extraction_accuracy_target", 0.95),
                "overall_accuracy_target": test_params.get("overall_accuracy_target", 0.93)
            }
    except (FileNotFoundError, json.JSONDecodeError):
        # Default values if metadata file is not available
        return {
            "typed_text_accuracy_target": 0.98,
            "handwritten_text_accuracy_target": 0.85,
            "mixed_text_accuracy_target": 0.90,
            "classification_accuracy_target": 0.95,
            "field_extraction_accuracy_target": 0.95,
            "overall_accuracy_target": 0.93
        }


# ===== Document Preprocessing Utilities =====

@pytest.fixture(scope="function")
def preprocess_document() -> Callable[[np.ndarray, DocumentMetadata], np.ndarray]:
    """
    Provides a function to preprocess documents for OCR testing.
    
    This fixture returns a function that preprocesses a document image for OCR testing,
    applying standard preprocessing steps like normalization and enhancement.
    
    Returns:
        Callable[[np.ndarray, DocumentMetadata], np.ndarray]: Function to preprocess documents
    """
    def _preprocess(image: np.ndarray, metadata: DocumentMetadata) -> np.ndarray:
        # Convert to grayscale if needed
        if len(image.shape) == 3 and image.shape[2] == 3:
            gray = tf.image.rgb_to_grayscale(image).numpy().squeeze()
        else:
            gray = image.copy()
        
        # Normalize image
        normalized = normalize_image(gray)
        
        # Apply additional preprocessing based on document type
        document_type = metadata.get("type", DocumentType.APPLICATION)
        
        if document_type == DocumentType.APPLICATION:
            # Enhance contrast for application forms
            from ocr_service.src.utils.image_utils import enhance_contrast
            enhanced = enhance_contrast(normalized, clip_limit=2.0)
            return enhanced
        elif document_type == DocumentType.BANK_STATEMENT:
            # Sharpen image for bank statements
            from ocr_service.src.utils.image_utils import sharpen_image
            sharpened = sharpen_image(normalized, amount=1.5)
            return sharpened
        else:
            # Default preprocessing
            return normalized
    
    return _preprocess


@pytest.fixture(scope="function")
def apply_image_distortions() -> Callable[[np.ndarray, str], np.ndarray]:
    """
    Provides a function to apply various distortions to test images.
    
    This fixture returns a function that applies different types of distortions to
    test images, allowing testing of OCR models under challenging conditions.
    
    Returns:
        Callable[[np.ndarray, str], np.ndarray]: Function to apply image distortions
    """
    def _apply_distortion(image: np.ndarray, distortion_type: str) -> np.ndarray:
        if distortion_type == "noise":
            # Add random noise
            noise = np.random.normal(0, 25, image.shape).astype(np.uint8)
            noisy_image = np.clip(image + noise, 0, 255).astype(np.uint8)
            return noisy_image
        
        elif distortion_type == "blur":
            # Apply Gaussian blur
            import cv2
            blurred = cv2.GaussianBlur(image, (5, 5), 0)
            return blurred
        
        elif distortion_type == "rotation":
            # Rotate image slightly
            import cv2
            rows, cols = image.shape[:2]
            angle = np.random.uniform(-5, 5)  # Random angle between -5 and 5 degrees
            rotation_matrix = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
            rotated = cv2.warpAffine(image, rotation_matrix, (cols, rows))
            return rotated
        
        elif distortion_type == "perspective":
            # Apply perspective distortion
            import cv2
            rows, cols = image.shape[:2]
            
            # Define source points
            src_points = np.float32([
                [0, 0],
                [cols-1, 0],
                [0, rows-1],
                [cols-1, rows-1]
            ])
            
            # Define destination points with slight distortion
            dst_points = np.float32([
                [cols*0.05, rows*0.05],
                [cols*0.95, rows*0.05],
                [cols*0.05, rows*0.95],
                [cols*0.95, rows*0.95]
            ])
            
            # Calculate perspective transform matrix
            perspective_matrix = cv2.getPerspectiveTransform(src_points, dst_points)
            
            # Apply perspective transform
            warped = cv2.warpPerspective(image, perspective_matrix, (cols, rows))
            return warped
        
        elif distortion_type == "low_contrast":
            # Reduce contrast
            low_contrast = (image * 0.6 + 50).astype(np.uint8)
            return low_contrast
        
        elif distortion_type == "jpeg_compression":
            # Apply JPEG compression artifacts
            import cv2
            import io
            from PIL import Image
            
            # Convert to PIL Image
            pil_image = Image.fromarray(image)
            
            # Save with JPEG compression
            buffer = io.BytesIO()
            pil_image.save(buffer, format="JPEG", quality=30)
            buffer.seek(0)
            
            # Load compressed image
            compressed = np.array(Image.open(buffer))
            return compressed
        
        else:
            # Return original image if distortion type is not recognized
            return image
    
    return _apply_distortion


# ===== Additional Test Utilities =====

@pytest.fixture(scope="function")
def expected_field_values(document_by_id) -> Callable[[str], Dict[str, Any]]:
    """
    Provides a function to retrieve expected field values for a document.
    
    This fixture returns a function that retrieves the expected field values for a
    document based on its ID, which can be used to validate OCR extraction results.
    
    Args:
        document_by_id: Function to retrieve document metadata by ID
        
    Returns:
        Callable[[str], Dict[str, Any]]: Function to retrieve expected field values
    """
    def _get_expected_values(doc_id: str) -> Dict[str, Any]:
        # Get document metadata
        doc_metadata = document_by_id(doc_id)
        if not doc_metadata:
            return {}
        
        # Extract expected fields
        expected_fields = doc_metadata.get("expected_fields", {})
        
        # Format expected values
        expected_values = {}
        for field_name, field_data in expected_fields.items():
            expected_values[field_name] = field_data.get("value")
        
        return expected_values
    
    return _get_expected_values


@pytest.fixture(scope="function")
def create_test_image() -> Callable[[str, str, int, int], Tuple[np.ndarray, DocumentMetadata]]:
    """
    Provides a function to create test images with text.
    
    This fixture returns a function that creates test images with specified text,
    which can be used for testing OCR models with controlled inputs.
    
    Returns:
        Callable[[str, str, int, int], Tuple[np.ndarray, DocumentMetadata]]: Function to create test images
    """
    def _create_image(text: str, text_type: str = "typed", width: int = 800, height: int = 600) -> Tuple[np.ndarray, DocumentMetadata]:
        # Create blank image
        image = np.ones((height, width, 3), dtype=np.uint8) * 255
        
        # Add text to image
        import cv2
        
        if text_type.lower() == "typed":
            # Use a standard font for typed text
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 1.0
            color = (0, 0, 0)  # Black text
            thickness = 2
            
            # Split text into lines
            lines = text.split("\n")
            y_position = 50
            
            for line in lines:
                # Calculate text size to center horizontally
                text_size = cv2.getTextSize(line, font, font_scale, thickness)[0]
                x_position = (width - text_size[0]) // 2
                
                # Add text to image
                cv2.putText(image, line, (x_position, y_position), font, font_scale, color, thickness)
                
                # Move to next line
                y_position += 40
        
        elif text_type.lower() == "handwritten":
            # For handwritten text, we'll use a handwriting-like font
            # In a real implementation, this would use a more sophisticated approach
            font = cv2.FONT_HERSHEY_SCRIPT_COMPLEX
            font_scale = 1.2
            color = (0, 0, 0)  # Black text
            thickness = 2
            
            # Add slight rotation and variation to simulate handwriting
            lines = text.split("\n")
            y_position = 50
            
            for line in lines:
                # Calculate text size to center horizontally
                text_size = cv2.getTextSize(line, font, font_scale, thickness)[0]
                x_position = (width - text_size[0]) // 2
                
                # Add text to image with slight rotation
                for i, char in enumerate(line):
                    char_size = cv2.getTextSize(char, font, font_scale, thickness)[0]
                    angle = np.random.uniform(-5, 5)  # Random angle between -5 and 5 degrees
                    
                    # Create rotation matrix
                    rotation_matrix = cv2.getRotationMatrix2D(
                        (x_position + char_size[0]//2, y_position), 
                        angle, 
                        1
                    )
                    
                    # Create temporary image for this character
                    char_image = np.ones((height, width, 3), dtype=np.uint8) * 255
                    cv2.putText(char_image, char, (x_position, y_position), font, font_scale, color, thickness)
                    
                    # Rotate character
                    rotated_char = cv2.warpAffine(char_image, rotation_matrix, (width, height))
                    
                    # Blend with main image
                    image = cv2.addWeighted(image, 1.0, rotated_char, 1.0, 0)
                    
                    # Move to next character position
                    x_position += char_size[0] + np.random.randint(-2, 3)  # Add slight variation
                
                # Move to next line
                y_position += 50
        
        # Create document metadata
        metadata = DocumentMetadata(
            id=f"test-{text_type}-{int(time.time())}",
            type=DocumentType.APPLICATION,
            mime_type="image/png",
            page_count=1,
            width=width,
            height=height,
            file_size=width * height * 3,  # Approximate size
            file_name=f"test-{text_type}-image.png"
        )
        
        return image, metadata
    
    return _create_image