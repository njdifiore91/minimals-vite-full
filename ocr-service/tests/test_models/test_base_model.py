#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the BaseOCRModel abstract base class.

This module contains tests for the BaseOCRModel abstract base class, which defines
the interface for all OCR models in the system. It verifies that the base model
correctly defines the interface, implements shared functionality, and enforces
implementation of abstract methods in derived classes.
"""

import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest import mock

import numpy as np
import pytest
import tensorflow as tf

# Try different import approaches to handle various test environments
try:
    # Direct imports assuming the package is installed
    from src.models.base_model import BaseOCRModel
    from src.types.config import TensorFlowConfig
    from src.types.documents import DocumentContent, DocumentMetadata
    from src.types.extraction import ConfidenceScore, ExtractedData, ExtractedField
    from src.types.models import ModelParameters, ModelResult
except ImportError:
    try:
        # Relative imports from the test directory
        import sys
        import os
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
        from src.models.base_model import BaseOCRModel
        from src.types.config import TensorFlowConfig
        from src.types.documents import DocumentContent, DocumentMetadata
        from src.types.extraction import ConfidenceScore, ExtractedData, ExtractedField
        from src.types.models import ModelParameters, ModelResult
    except ImportError:
        # Fully qualified package name
        from ocr_service.src.models.base_model import BaseOCRModel
        from ocr_service.src.types.config import TensorFlowConfig
        from ocr_service.src.types.documents import DocumentContent, DocumentMetadata
        from ocr_service.src.types.extraction import ConfidenceScore, ExtractedData, ExtractedField
        from ocr_service.src.types.models import ModelParameters, ModelResult


# Mock implementation of BaseOCRModel for testing
class MockOCRModel(BaseOCRModel):
    """Mock implementation of BaseOCRModel for testing.
    
    This class implements the abstract methods required by BaseOCRModel
    to allow testing of the base class functionality.
    """
    
    def extract_text(self, image: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """Mock implementation of extract_text."""
        return [("Sample text", 0.95), ("More text", 0.85)]
    
    def extract_fields(self, image: np.ndarray, 
                      document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """Mock implementation of extract_fields."""
        return [
            {
                "field_name": "business_name",
                "field_type": "text",
                "value": "ABC Corporation",
                "raw_text": "ABC Corporation",
                "confidence": 0.95,
                "location": {
                    "page": 0,
                    "top": 0.1,
                    "left": 0.1,
                    "bottom": 0.15,
                    "right": 0.5,
                    "width": 0.4,
                    "height": 0.05
                },
                "alternatives": [],
                "metadata": {},
                "requires_verification": False,
                "verification_reason": None,
                "extraction_timestamp": datetime.now()
            }
        ]


# Incomplete implementation of BaseOCRModel for testing abstract method enforcement
class IncompleteOCRModel(BaseOCRModel):
    """Incomplete implementation of BaseOCRModel for testing abstract method enforcement.
    
    This class intentionally does not implement all required abstract methods
    to test that the abstract method enforcement works correctly.
    """
    
    def extract_text(self, image: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """Mock implementation of extract_text."""
        return [("Sample text", 0.95)]
    
    # Intentionally missing extract_fields implementation


@pytest.fixture
def mock_tensorflow_config():
    """Fixture for TensorFlowConfig with test settings."""
    return TensorFlowConfig(
        use_gpu=False,  # Disable GPU for tests
        gpu_memory_limit=None,
        verification_threshold=0.7
    )


@pytest.fixture
def mock_model_path():
    """Fixture for creating a temporary directory for model path."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a version.txt file in the temp directory
        version_file = Path(temp_dir) / "version.txt"
        with open(version_file, "w") as f:
            f.write("1.0.0-test")
        
        yield Path(temp_dir)


@pytest.fixture
def mock_document_content():
    """Fixture for mock document content."""
    # Create a simple 100x100 RGB image as numpy array
    return np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)


@pytest.fixture
def mock_document_metadata():
    """Fixture for mock document metadata."""
    return {
        "id": "doc-123",
        "type": "application_form",
        "mime_type": "image/jpeg",
        "filename": "test_document.jpg",
        "size": 12345,
        "created_at": datetime.now().isoformat(),
        "classification": {
            "type": "application_form",
            "confidence": 0.98
        }
    }


@mock.patch("src.models.base_model.configure_gpu_memory")
@mock.patch("src.models.base_model.tf.saved_model.load")
@mock.patch("src.models.base_model.preprocess_image")
@mock.patch("src.models.base_model.normalize_image")
class TestBaseOCRModel:
    """Tests for the BaseOCRModel abstract base class."""
    
    def test_abstract_method_enforcement(self, *mocks):
        """Test that abstract methods must be implemented by derived classes."""
        # Creating an instance of IncompleteOCRModel should raise TypeError
        # because it doesn't implement all abstract methods
        with pytest.raises(TypeError) as excinfo:
            model = IncompleteOCRModel(
                model_path="/path/to/model",
                model_name="incomplete_model",
                config=mock_tensorflow_config()
            )
        
        # Check that the error message mentions the missing abstract method
        assert "abstract method" in str(excinfo.value)
        assert "extract_fields" in str(excinfo.value)
    
    def test_initialization(self, mock_normalize_image, mock_preprocess_image, 
                           mock_tf_load, mock_configure_gpu):
        """Test model initialization and loading."""
        # Mock the TensorFlow model
        mock_tf_model = mock.MagicMock()
        mock_tf_load.return_value = mock_tf_model
        
        # Create a mock model path
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            # Initialize the model
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Check that the model was initialized correctly
            assert model.model_path == model_path
            assert model.model_name == "test_model"
            assert model.model_version == "1.0.0-test"
            assert model.model is mock_tf_model
            
            # Check that the model was loaded
            mock_tf_load.assert_called_once_with(str(model_path))
            
            # GPU should not be configured for tests
            mock_configure_gpu.assert_not_called()
    
    def test_gpu_configuration(self, mock_normalize_image, mock_preprocess_image, 
                              mock_tf_load, mock_configure_gpu):
        """Test GPU configuration during initialization."""
        # Create a config with GPU enabled
        gpu_config = TensorFlowConfig(
            use_gpu=True,
            gpu_memory_limit=4096,  # 4GB
            gpu_growth=True
        )
        
        # Initialize the model with GPU config
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            # Initialize the model
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=gpu_config
            )
            
            # Check that GPU was configured
            mock_configure_gpu.assert_called_once_with(4096, True)
    
    def test_model_loading_error(self, mock_normalize_image, mock_preprocess_image, 
                                mock_tf_load, mock_configure_gpu):
        """Test error handling when model loading fails."""
        # Make tf.saved_model.load raise an exception
        mock_tf_load.side_effect = RuntimeError("Failed to load model")
        
        # Initializing the model should raise RuntimeError
        with pytest.raises(RuntimeError) as excinfo:
            with tempfile.TemporaryDirectory() as temp_dir:
                model_path = Path(temp_dir)
                
                # Create a version.txt file
                version_file = model_path / "version.txt"
                with open(version_file, "w") as f:
                    f.write("1.0.0-test")
                
                model = MockOCRModel(
                    model_path=model_path,
                    model_name="test_model",
                    config=mock_tensorflow_config()
                )
        
        # Check that the error message is correct
        assert "Failed to load model" in str(excinfo.value)
    
    def test_invalid_model_path(self, mock_normalize_image, mock_preprocess_image, 
                               mock_tf_load, mock_configure_gpu):
        """Test error handling when model path is invalid."""
        # Initializing the model with a non-existent path should raise ValueError
        with pytest.raises(ValueError) as excinfo:
            model = MockOCRModel(
                model_path="/non/existent/path",
                model_name="test_model",
                config=mock_tensorflow_config()
            )
        
        # Check that the error message is correct
        assert "Model path does not exist" in str(excinfo.value)
    
    def test_preprocess_document(self, mock_normalize_image, mock_preprocess_image, 
                                mock_tf_load, mock_configure_gpu, 
                                mock_document_content, mock_document_metadata):
        """Test document preprocessing."""
        # Mock the preprocessing functions
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_preprocess_image.return_value = mock_image
        
        normalized_image = np.ones((100, 100, 3), dtype=np.float32)
        mock_normalize_image.return_value = normalized_image
        
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Preprocess the document
            result = model.preprocess_document(mock_document_content, mock_document_metadata)
            
            # Check that the preprocessing functions were called correctly
            mock_preprocess_image.assert_called_once_with(mock_document_content, mock_document_metadata)
            mock_normalize_image.assert_called_once_with(mock_image)
            
            # Check that the result is correct
            assert np.array_equal(result, normalized_image)
    
    def test_preprocess_document_error(self, mock_normalize_image, mock_preprocess_image, 
                                      mock_tf_load, mock_configure_gpu, 
                                      mock_document_content, mock_document_metadata):
        """Test error handling when document preprocessing fails."""
        # Make preprocess_image raise an exception
        mock_preprocess_image.side_effect = ValueError("Invalid document content")
        
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Preprocessing the document should raise ValueError
            with pytest.raises(ValueError) as excinfo:
                model.preprocess_document(mock_document_content, mock_document_metadata)
            
            # Check that the error message is correct
            assert "Failed to preprocess document" in str(excinfo.value)
            assert "Invalid document content" in str(excinfo.value)
    
    def test_process_document(self, mock_normalize_image, mock_preprocess_image, 
                             mock_tf_load, mock_configure_gpu, 
                             mock_document_content, mock_document_metadata):
        """Test end-to-end document processing."""
        # Mock the preprocessing functions
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_preprocess_image.return_value = mock_image
        
        normalized_image = np.ones((100, 100, 3), dtype=np.float32)
        mock_normalize_image.return_value = normalized_image
        
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Process the document
            result = model.process_document(mock_document_content, mock_document_metadata)
            
            # Check that the result is a ModelResult
            assert isinstance(result, dict)
            assert result["success"] is True
            assert "data" in result
            assert "error" in result
            assert result["error"] is None
            assert "processing_time_ms" in result
            
            # Check the extracted data
            extracted_data = result["data"]
            assert "fields" in extracted_data
            assert "text" in extracted_data
            assert "confidence" in extracted_data
            assert "metadata" in extracted_data
            
            # Check metadata
            metadata = extracted_data["metadata"]
            assert metadata["model_name"] == "test_model"
            assert metadata["model_version"] == "1.0.0-test"
            assert metadata["document_id"] == "doc-123"
            assert metadata["document_type"] == "application_form"
            assert "processing_time_ms" in metadata
    
    def test_process_document_error(self, mock_normalize_image, mock_preprocess_image, 
                                   mock_tf_load, mock_configure_gpu, 
                                   mock_document_content, mock_document_metadata):
        """Test error handling when document processing fails."""
        # Mock the preprocessing functions to raise an exception
        mock_preprocess_image.side_effect = ValueError("Invalid document content")
        
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Process the document - should not raise an exception but return an error result
            result = model.process_document(mock_document_content, mock_document_metadata)
            
            # Check that the result indicates an error
            assert isinstance(result, dict)
            assert result["success"] is False
            assert result["data"] is None
            assert "error" in result
            assert result["error"] is not None
            assert "message" in result["error"]
            assert "Failed to process document" in result["error"]["message"]
            assert "type" in result["error"]
            assert result["error"]["type"] == "ValueError"
            assert "processing_time_ms" in result
    
    def test_calculate_confidence(self, mock_normalize_image, mock_preprocess_image, 
                                 mock_tf_load, mock_configure_gpu):
        """Test confidence score calculation."""
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Test with various prediction arrays
            # Single value
            predictions = np.array([0.85])
            confidence = model.calculate_confidence(predictions)
            assert confidence == 0.85
            
            # Multiple values (1D array)
            predictions = np.array([0.9, 0.8, 0.7])
            confidence = model.calculate_confidence(predictions)
            assert confidence == 0.8  # mean of [0.9, 0.8, 0.7]
            
            # 2D array (classification probabilities)
            predictions = np.array([[0.9, 0.1], [0.8, 0.2], [0.7, 0.3]])
            confidence = model.calculate_confidence(predictions)
            assert confidence == 0.8  # mean of max values [0.9, 0.8, 0.7]
            
            # Empty array
            predictions = np.array([])
            confidence = model.calculate_confidence(predictions)
            assert confidence == 0.0
            
            # None
            confidence = model.calculate_confidence(None)
            assert confidence == 0.0
            
            # Values outside [0, 1] range should be clipped
            predictions = np.array([1.2, -0.1, 0.5])
            confidence = model.calculate_confidence(predictions)
            assert 0.0 <= confidence <= 1.0
    
    def test_format_result(self, mock_normalize_image, mock_preprocess_image, 
                          mock_tf_load, mock_configure_gpu, 
                          mock_document_metadata):
        """Test result formatting."""
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Create some extracted fields
            extracted_fields = [
                {
                    "name": "business_name",
                    "value": "ABC Corporation",
                    "confidence": 0.95,
                    "location": {
                        "page": 0,
                        "top": 0.1,
                        "left": 0.1,
                        "bottom": 0.15,
                        "right": 0.5,
                        "width": 0.4,
                        "height": 0.05
                    },
                    "category": "business_info"
                },
                {
                    "name": "tax_id",
                    "value": "12-3456789",
                    "confidence": 0.85,
                    "location": {
                        "page": 0,
                        "top": 0.2,
                        "left": 0.1,
                        "bottom": 0.25,
                        "right": 0.3,
                        "width": 0.2,
                        "height": 0.05
                    },
                    "category": "business_info"
                },
                {
                    "name": "signature",
                    "value": True,
                    "confidence": 0.65,  # Below verification threshold
                    "location": {
                        "page": 0,
                        "top": 0.8,
                        "left": 0.1,
                        "bottom": 0.9,
                        "right": 0.3,
                        "width": 0.2,
                        "height": 0.1
                    },
                    "category": "signatures"
                }
            ]
            
            # Format the result
            result = model.format_result(extracted_fields, mock_document_metadata)
            
            # Check the result structure
            assert "document_id" in result
            assert result["document_id"] == "doc-123"
            assert "document_type" in result
            assert result["document_type"] == "application_form"
            assert "extraction_time" in result
            assert "model" in result
            assert result["model"]["name"] == "test_model"
            assert result["model"]["version"] == "1.0.0-test"
            assert "categories" in result
            assert "overall_confidence" in result
            assert "requires_verification" in result
            
            # Check categories
            categories = result["categories"]
            assert "business_info" in categories
            assert "signatures" in categories
            
            # Check fields in categories
            business_info = categories["business_info"]
            assert "fields" in business_info
            assert "confidence" in business_info
            assert len(business_info["fields"]) == 2
            
            # Check verification flag
            assert result["requires_verification"] is True  # Because signature is below threshold
            
            # Check field verification flags
            signature_field = categories["signatures"]["fields"][0]
            assert signature_field["requires_verification"] is True
            
            business_name_field = business_info["fields"][0]
            assert business_name_field["requires_verification"] is False
    
    def test_string_representation(self, mock_normalize_image, mock_preprocess_image, 
                                  mock_tf_load, mock_configure_gpu):
        """Test string representation of the model."""
        # Initialize the model
        with tempfile.TemporaryDirectory() as temp_dir:
            model_path = Path(temp_dir)
            
            # Create a version.txt file
            version_file = model_path / "version.txt"
            with open(version_file, "w") as f:
                f.write("1.0.0-test")
            
            model = MockOCRModel(
                model_path=model_path,
                model_name="test_model",
                config=mock_tensorflow_config()
            )
            
            # Check string representation
            assert str(model) == "test_model (version: 1.0.0-test)"
            
            # Check repr
            repr_str = repr(model)
            assert "MockOCRModel" in repr_str
            assert "model_name='test_model'" in repr_str
            assert "model_version='1.0.0-test'" in repr_str
            assert str(model_path) in repr_str


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])