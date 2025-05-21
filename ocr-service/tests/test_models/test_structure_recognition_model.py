#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the StructureRecognitionModel class.

This module contains tests for the TensorFlow model that recognizes and analyzes document structure,
including forms, tables, and field relationships. It verifies that the model correctly identifies
document elements, their relationships, and provides context for extracted text.
"""

import os
import json
import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path

# Import the model to test
from src.models.structure_recognition_model import StructureRecognitionModel
from src.types.models import ModelParameters
from src.types.documents import DocumentType
from src.types.extraction import ExtractedData, FieldLocation, ExtractionMetadata


# Test fixtures
@pytest.fixture
def mock_tensorflow_model():
    """Create a mock TensorFlow model for testing."""
    with patch('tensorflow.saved_model.load') as mock_load:
        # Create a mock model with signatures
        mock_model = MagicMock()
        
        # Mock the serving_default signature
        mock_serving_default = MagicMock()
        mock_input = MagicMock()
        mock_input.shape.as_list.return_value = [1, 1024, 1024, 3]
        mock_serving_default.inputs = [mock_input]
        
        # Mock the field_detection signature
        mock_field_detection = MagicMock()
        
        # Mock the table_analysis signature
        mock_table_analysis = MagicMock()
        
        # Set up the signatures dictionary
        mock_model.signatures = {
            "serving_default": mock_serving_default,
            "field_detection": mock_field_detection,
            "table_analysis": mock_table_analysis
        }
        
        # Configure the mock to return our mock model
        mock_load.return_value = mock_model
        
        yield mock_model


@pytest.fixture
def model_parameters():
    """Create model parameters for testing."""
    return ModelParameters(
        confidence_threshold=0.75,
        gpu_enabled=False,  # Disable GPU for testing
        batch_size=1,
        model_type="structure_recognition"
    )


@pytest.fixture
def structure_recognition_model(mock_tensorflow_model, model_parameters):
    """Create a StructureRecognitionModel instance for testing."""
    with patch('src.models.structure_recognition_model.configure_gpu_memory'):
        model = StructureRecognitionModel("/models/structure_recognition", model_parameters)
        return model


@pytest.fixture
def sample_image():
    """Create a sample image for testing."""
    # Create a 1024x768 RGB image with random data
    return np.random.randint(0, 255, (768, 1024, 3), dtype=np.uint8)


@pytest.fixture
def sample_structure_result():
    """Create a sample structure detection result."""
    return {
        "elements": [
            {
                "id": 0,
                "type": "form",
                "bbox": [100, 100, 900, 700],
                "confidence": 0.95
            },
            {
                "id": 1,
                "type": "table",
                "bbox": [150, 400, 850, 650],
                "confidence": 0.92
            },
            {
                "id": 2,
                "type": "section",
                "bbox": [150, 150, 850, 350],
                "confidence": 0.90
            },
            {
                "id": 3,
                "type": "header",
                "bbox": [150, 150, 850, 200],
                "confidence": 0.96
            }
        ],
        "relationships": [
            {
                "from_id": 0,
                "to_id": 1,
                "type": "contains",
                "confidence": 0.88
            },
            {
                "from_id": 0,
                "to_id": 2,
                "type": "contains",
                "confidence": 0.89
            },
            {
                "from_id": 2,
                "to_id": 3,
                "type": "contains",
                "confidence": 0.92
            }
        ]
    }


@pytest.fixture
def sample_form_fields_result():
    """Create a sample form fields detection result."""
    return [
        {
            "id": 0,
            "form_id": 0,
            "type": "text",
            "bbox": [200, 200, 400, 230],
            "confidence": 0.92,
            "label": "Business Name",
            "properties": {"type": "string", "multi_line": False}
        },
        {
            "id": 1,
            "form_id": 0,
            "type": "text",
            "bbox": [200, 250, 400, 280],
            "confidence": 0.90,
            "label": "Business Address",
            "properties": {"type": "string", "multi_line": False}
        },
        {
            "id": 2,
            "form_id": 0,
            "type": "checkbox",
            "bbox": [200, 300, 230, 330],
            "confidence": 0.95,
            "label": "Agree to Terms",
            "properties": {"type": "boolean", "multi_line": False}
        },
        {
            "id": 3,
            "form_id": 0,
            "type": "signature",
            "bbox": [200, 350, 400, 380],
            "confidence": 0.88,
            "label": "Signature",
            "properties": {"type": "image", "multi_line": False}
        }
    ]


@pytest.fixture
def sample_tables_result():
    """Create a sample tables detection result."""
    return [
        {
            "id": 1,
            "bbox": [150, 400, 850, 650],
            "confidence": 0.92,
            "rows": 5,
            "columns": 3,
            "cells": [
                # Header row
                {
                    "id": 0,
                    "bbox": [150, 400, 350, 450],
                    "confidence": 0.94,
                    "is_header": True,
                    "row": 0,
                    "column": 0
                },
                {
                    "id": 1,
                    "bbox": [350, 400, 550, 450],
                    "confidence": 0.93,
                    "is_header": True,
                    "row": 0,
                    "column": 1
                },
                {
                    "id": 2,
                    "bbox": [550, 400, 850, 450],
                    "confidence": 0.92,
                    "is_header": True,
                    "row": 0,
                    "column": 2
                },
                # Data row 1
                {
                    "id": 3,
                    "bbox": [150, 450, 350, 500],
                    "confidence": 0.91,
                    "is_header": False,
                    "row": 1,
                    "column": 0
                },
                {
                    "id": 4,
                    "bbox": [350, 450, 550, 500],
                    "confidence": 0.90,
                    "is_header": False,
                    "row": 1,
                    "column": 1
                },
                {
                    "id": 5,
                    "bbox": [550, 450, 850, 500],
                    "confidence": 0.89,
                    "is_header": False,
                    "row": 1,
                    "column": 2
                }
            ]
        }
    ]


@pytest.fixture
def sample_sections_result():
    """Create a sample sections detection result."""
    return [
        {
            "id": 2,
            "bbox": [150, 150, 850, 350],
            "confidence": 0.90,
            "parent_id": None,
            "header": [150, 150, 850, 200],
            "header_confidence": 0.96
        }
    ]


# Tests
def test_model_initialization(structure_recognition_model):
    """Test that the model initializes correctly."""
    # Check that the model has been initialized with the correct attributes
    assert structure_recognition_model.confidence_threshold == 0.75
    assert structure_recognition_model.model is not None
    assert structure_recognition_model.input_shape == [1, 1024, 1024, 3]
    assert len(structure_recognition_model.field_types) > 0
    assert len(structure_recognition_model.structure_types) > 0


def test_preprocess_image(structure_recognition_model, sample_image):
    """Test image preprocessing functionality."""
    # Preprocess the sample image
    preprocessed = structure_recognition_model.preprocess_image(sample_image)
    
    # Check that the output has the correct shape and type
    assert isinstance(preprocessed, tf.Tensor)
    assert preprocessed.shape[0] == 1  # Batch dimension
    assert preprocessed.shape[3] == 3  # RGB channels
    
    # Check that the values are normalized to [0, 1]
    assert tf.reduce_min(preprocessed) >= 0.0
    assert tf.reduce_max(preprocessed) <= 1.0


def test_detect_structure(structure_recognition_model, sample_image, mock_tensorflow_model):
    """Test structure detection functionality."""
    # Mock the model's inference function
    mock_infer = MagicMock()
    mock_tensorflow_model.signatures["serving_default"] = mock_infer
    
    # Configure the mock to return test data
    mock_result = {
        "structure_boxes": tf.constant([[[100, 100, 900, 700], [150, 400, 850, 650], [150, 150, 850, 350], [150, 150, 850, 200]]]),
        "structure_scores": tf.constant([[0.95, 0.92, 0.90, 0.96]]),
        "structure_classes": tf.constant([[0, 1, 2, 3]]),
        "relationship_matrix": tf.constant([[[0.0, 0.88, 0.89, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.92], [0.0, 0.0, 0.0, 0.0]]])
    }
    mock_infer.return_value = mock_result
    
    # Preprocess the image
    preprocessed = structure_recognition_model.preprocess_image(sample_image)
    
    # Detect structure
    structure = structure_recognition_model.detect_structure(preprocessed)
    
    # Check that the structure contains the expected elements and relationships
    assert "elements" in structure
    assert "relationships" in structure
    assert len(structure["elements"]) == 4
    assert len(structure["relationships"]) > 0
    
    # Check that elements have the expected attributes
    for element in structure["elements"]:
        assert "id" in element
        assert "type" in element
        assert "bbox" in element
        assert "confidence" in element
        assert element["confidence"] > structure_recognition_model.confidence_threshold
    
    # Check that relationships have the expected attributes
    for relationship in structure["relationships"]:
        assert "from_id" in relationship
        assert "to_id" in relationship
        assert "type" in relationship
        assert "confidence" in relationship
        assert relationship["confidence"] > structure_recognition_model.confidence_threshold


def test_detect_form_fields(structure_recognition_model, sample_image, mock_tensorflow_model, sample_structure_result):
    """Test form field detection functionality."""
    # Mock the model's field detection function
    mock_field_detection = MagicMock()
    mock_tensorflow_model.signatures["field_detection"] = mock_field_detection
    
    # Configure the mock to return test data
    mock_result = {
        "field_boxes": tf.constant([[[200, 200, 400, 230], [200, 250, 400, 280], [200, 300, 230, 330], [200, 350, 400, 380]]]),
        "field_scores": tf.constant([[0.92, 0.90, 0.95, 0.88]]),
        "field_classes": tf.constant([[0, 0, 2, 3]]),
        "field_labels": tf.constant([b"Business Name", b"Business Address", b"Agree to Terms", b"Signature"])
    }
    mock_field_detection.return_value = mock_result
    
    # Preprocess the image
    preprocessed = structure_recognition_model.preprocess_image(sample_image)
    
    # Detect form fields
    form_fields = structure_recognition_model.detect_form_fields(preprocessed, sample_structure_result)
    
    # Check that form fields were detected
    assert len(form_fields) > 0
    
    # Check that fields have the expected attributes
    for field in form_fields:
        assert "id" in field
        assert "form_id" in field
        assert "type" in field
        assert "bbox" in field
        assert "confidence" in field
        assert "properties" in field
        assert field["confidence"] > structure_recognition_model.confidence_threshold


def test_detect_tables(structure_recognition_model, sample_image, mock_tensorflow_model, sample_structure_result):
    """Test table detection functionality."""
    # Mock the model's table analysis function
    mock_table_analysis = MagicMock()
    mock_tensorflow_model.signatures["table_analysis"] = mock_table_analysis
    
    # Configure the mock to return test data
    mock_result = {
        "cell_boxes": tf.constant([[[150, 400, 350, 450], [350, 400, 550, 450], [550, 400, 850, 450], 
                                 [150, 450, 350, 500], [350, 450, 550, 500], [550, 450, 850, 500]]]),
        "cell_scores": tf.constant([[0.94, 0.93, 0.92, 0.91, 0.90, 0.89]]),
        "cell_types": tf.constant([[0, 0, 0, 1, 1, 1]]),  # 0 for header, 1 for data
        "row_indices": tf.constant([[0, 0, 0, 1, 1, 1]]),
        "col_indices": tf.constant([[0, 1, 2, 0, 1, 2]])
    }
    mock_table_analysis.return_value = mock_result
    
    # Preprocess the image
    preprocessed = structure_recognition_model.preprocess_image(sample_image)
    
    # Detect tables
    tables = structure_recognition_model.detect_tables(preprocessed, sample_structure_result)
    
    # Check that tables were detected
    assert len(tables) > 0
    
    # Check that tables have the expected attributes
    for table in tables:
        assert "id" in table
        assert "bbox" in table
        assert "confidence" in table
        assert "rows" in table
        assert "columns" in table
        assert "cells" in table
        assert table["confidence"] > structure_recognition_model.confidence_threshold
        
        # Check that cells have the expected attributes
        for cell in table["cells"]:
            assert "id" in cell
            assert "bbox" in cell
            assert "confidence" in cell
            assert "is_header" in cell
            assert "row" in cell
            assert "column" in cell
            assert cell["confidence"] > structure_recognition_model.confidence_threshold


def test_detect_sections(structure_recognition_model, sample_structure_result):
    """Test section detection functionality."""
    # Detect sections
    sections = structure_recognition_model.detect_sections(sample_structure_result)
    
    # Check that sections were detected
    assert len(sections) > 0
    
    # Check that sections have the expected attributes
    for section in sections:
        assert "id" in section
        assert "bbox" in section
        assert "confidence" in section
        assert "parent_id" in section
        assert section["confidence"] > structure_recognition_model.confidence_threshold


def test_extract_structure(structure_recognition_model, sample_image, mock_tensorflow_model):
    """Test complete structure extraction functionality."""
    # Mock the necessary methods
    with patch.object(structure_recognition_model, 'detect_structure', return_value=sample_structure_result) as mock_detect_structure, \
         patch.object(structure_recognition_model, 'detect_form_fields', return_value=sample_form_fields_result()) as mock_detect_form_fields, \
         patch.object(structure_recognition_model, 'detect_tables', return_value=sample_tables_result()) as mock_detect_tables, \
         patch.object(structure_recognition_model, 'detect_sections', return_value=sample_sections_result()) as mock_detect_sections:
        
        # Extract structure
        structure = structure_recognition_model.extract_structure(sample_image, DocumentType.APPLICATION)
        
        # Check that the structure contains all expected components
        assert "document_type" in structure
        assert "structure_elements" in structure
        assert "structure_relationships" in structure
        assert "form_fields" in structure
        assert "tables" in structure
        assert "sections" in structure
        
        # Check that the document type is correct
        assert structure["document_type"] == DocumentType.APPLICATION.value
        
        # Verify that all methods were called with the correct arguments
        mock_detect_structure.assert_called_once()
        mock_detect_form_fields.assert_called_once()
        mock_detect_tables.assert_called_once()
        mock_detect_sections.assert_called_once()


def test_process_image(structure_recognition_model, sample_image):
    """Test the complete image processing pipeline."""
    # Mock the extract_structure method
    with patch.object(structure_recognition_model, 'extract_structure') as mock_extract_structure:
        # Configure the mock to return a sample structure
        mock_extract_structure.return_value = {
            "document_type": "application",
            "structure_elements": sample_structure_result()["elements"],
            "structure_relationships": sample_structure_result()["relationships"],
            "form_fields": sample_form_fields_result(),
            "tables": sample_tables_result(),
            "sections": sample_sections_result()
        }
        
        # Process the image
        result = structure_recognition_model.process_image(sample_image, DocumentType.APPLICATION)
        
        # Check that the result has the expected attributes
        assert result["success"] is True
        assert "data" in result
        assert "metadata" in result
        assert result["error"] is None
        
        # Check that the metadata has the expected attributes
        assert "model_name" in result["metadata"]
        assert "model_version" in result["metadata"]
        assert "confidence_score" in result["metadata"]
        assert "processing_time" in result["metadata"]
        assert "document_type" in result["metadata"]
        
        # Verify that extract_structure was called with the correct arguments
        mock_extract_structure.assert_called_once_with(sample_image, DocumentType.APPLICATION)


def test_map_field_relationships(structure_recognition_model):
    """Test field relationship mapping functionality."""
    # Create a sample structure with form fields and tables
    structure = {
        "form_fields": [
            {
                "id": 0,
                "form_id": 0,
                "type": "key_value",
                "bbox": [200, 200, 300, 230],
                "confidence": 0.92,
                "label": "Business Name:"
            },
            {
                "id": 1,
                "form_id": 0,
                "type": "text",
                "bbox": [310, 200, 500, 230],
                "confidence": 0.90,
                "label": "Acme Corp"
            },
            {
                "id": 2,
                "form_id": 0,
                "type": "key_value",
                "bbox": [200, 250, 300, 280],
                "confidence": 0.91,
                "label": "Address:"
            },
            {
                "id": 3,
                "form_id": 0,
                "type": "text",
                "bbox": [310, 250, 500, 280],
                "confidence": 0.89,
                "label": "123 Main St"
            }
        ],
        "tables": [
            {
                "id": 1,
                "cells": [
                    {
                        "id": 0,
                        "is_header": True,
                        "row": 0,
                        "column": 0
                    },
                    {
                        "id": 1,
                        "is_header": True,
                        "row": 0,
                        "column": 1
                    },
                    {
                        "id": 2,
                        "is_header": False,
                        "row": 1,
                        "column": 0
                    },
                    {
                        "id": 3,
                        "is_header": False,
                        "row": 1,
                        "column": 1
                    }
                ]
            }
        ]
    }
    
    # Map field relationships
    relationships = structure_recognition_model.map_field_relationships(structure)
    
    # Check that relationships were created for form fields
    assert "0" in relationships
    assert "1" in relationships
    assert "2" in relationships
    assert "3" in relationships
    
    # Check that key-value pairs are related
    assert "1" in relationships["0"]
    assert "3" in relationships["2"]
    
    # Check that table cells have relationships
    assert "table_1_cell_0" in relationships
    assert "table_1_cell_1" in relationships
    assert "table_1_cell_2" in relationships
    assert "table_1_cell_3" in relationships
    
    # Check that cells in the same row are related
    assert "table_1_cell_1" in relationships["table_1_cell_0"]
    assert "table_1_cell_3" in relationships["table_1_cell_2"]
    
    # Check that cells in the same column are related
    assert "table_1_cell_2" in relationships["table_1_cell_0"]
    assert "table_1_cell_3" in relationships["table_1_cell_1"]
    
    # Check that header cells are related to data cells in the same column
    assert "table_1_cell_0" in relationships["table_1_cell_2"]
    assert "table_1_cell_1" in relationships["table_1_cell_3"]


def test_are_fields_related(structure_recognition_model):
    """Test field relationship detection functionality."""
    # Create sample fields
    key_field = {
        "id": 0,
        "type": "key_value",
        "bbox": [200, 200, 300, 230]
    }
    
    value_field = {
        "id": 1,
        "type": "text",
        "bbox": [310, 200, 500, 230]
    }
    
    unrelated_field = {
        "id": 2,
        "type": "text",
        "bbox": [200, 400, 300, 430]
    }
    
    # Test key-value relationship
    assert structure_recognition_model._are_fields_related(key_field, value_field) is True
    
    # Test proximity-based relationship
    close_field = {
        "id": 3,
        "type": "text",
        "bbox": [510, 200, 600, 230]
    }
    assert structure_recognition_model._are_fields_related(value_field, close_field) is True
    
    # Test unrelated fields
    assert structure_recognition_model._are_fields_related(key_field, unrelated_field) is False


def test_error_handling(structure_recognition_model, sample_image):
    """Test error handling in the model."""
    # Mock the extract_structure method to raise an exception
    with patch.object(structure_recognition_model, 'extract_structure', side_effect=Exception("Test error")):
        # Process the image
        result = structure_recognition_model.process_image(sample_image, DocumentType.APPLICATION)
        
        # Check that the result indicates failure
        assert result["success"] is False
        assert result["data"] is None
        assert result["error"] == "Test error"
        
        # Check that the metadata has the expected attributes
        assert "model_name" in result["metadata"]
        assert "model_version" in result["metadata"]
        assert "confidence_score" in result["metadata"]
        assert "processing_time" in result["metadata"]
        assert "document_type" in result["metadata"]


def test_performance_metrics(structure_recognition_model, sample_image):
    """Test performance metrics collection."""
    # Mock the necessary methods with timing information
    with patch.object(structure_recognition_model, 'extract_structure') as mock_extract_structure, \
         patch('time.time', side_effect=[0.0, 1.5]):  # Mock time.time to return 0.0 then 1.5 (1.5 seconds elapsed)
        
        # Configure the mock to return a sample structure
        mock_extract_structure.return_value = {
            "document_type": "application",
            "structure_elements": sample_structure_result()["elements"],
            "structure_relationships": sample_structure_result()["relationships"],
            "form_fields": sample_form_fields_result(),
            "tables": sample_tables_result(),
            "sections": sample_sections_result()
        }
        
        # Process the image
        result = structure_recognition_model.process_image(sample_image, DocumentType.APPLICATION)
        
        # Check that the processing time is recorded
        assert result["metadata"]["processing_time"] > 0.0


def test_gpu_acceleration(model_parameters):
    """Test GPU acceleration configuration."""
    # Enable GPU for testing
    gpu_params = model_parameters.copy()
    gpu_params["gpu_enabled"] = True
    
    # Mock the GPU configuration function
    with patch('src.models.structure_recognition_model.configure_gpu_memory') as mock_configure_gpu, \
         patch('tensorflow.saved_model.load'):
        
        # Initialize the model with GPU enabled
        model = StructureRecognitionModel("/models/structure_recognition", gpu_params)
        
        # Verify that GPU configuration was attempted
        mock_configure_gpu.assert_called_once()


def test_document_type_handling(structure_recognition_model, sample_image):
    """Test handling of different document types."""
    # Mock the extract_structure method
    with patch.object(structure_recognition_model, 'extract_structure') as mock_extract_structure:
        # Test with APPLICATION document type
        structure_recognition_model.process_image(sample_image, DocumentType.APPLICATION)
        mock_extract_structure.assert_called_with(sample_image, DocumentType.APPLICATION)
        
        # Test with BANK_STATEMENT document type
        structure_recognition_model.process_image(sample_image, DocumentType.BANK_STATEMENT)
        mock_extract_structure.assert_called_with(sample_image, DocumentType.BANK_STATEMENT)
        
        # Test with TAX_RETURN document type
        structure_recognition_model.process_image(sample_image, DocumentType.TAX_RETURN)
        mock_extract_structure.assert_called_with(sample_image, DocumentType.TAX_RETURN)


def test_confidence_threshold_filtering(structure_recognition_model, sample_image, mock_tensorflow_model):
    """Test filtering of low-confidence detections."""
    # Mock the model's inference function
    mock_infer = MagicMock()
    mock_tensorflow_model.signatures["serving_default"] = mock_infer
    
    # Configure the mock to return test data with mixed confidence scores
    mock_result = {
        "structure_boxes": tf.constant([[[100, 100, 900, 700], [150, 400, 850, 650], [150, 150, 850, 350], [150, 150, 850, 200]]]),
        "structure_scores": tf.constant([[0.95, 0.92, 0.60, 0.40]]),  # Two scores below threshold
        "structure_classes": tf.constant([[0, 1, 2, 3]]),
        "relationship_matrix": tf.constant([[[0.0, 0.88, 0.89, 0.0], [0.0, 0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 0.92], [0.0, 0.0, 0.0, 0.0]]])
    }
    mock_infer.return_value = mock_result
    
    # Preprocess the image
    preprocessed = structure_recognition_model.preprocess_image(sample_image)
    
    # Detect structure
    structure = structure_recognition_model.detect_structure(preprocessed)
    
    # Check that only high-confidence elements are included
    assert len(structure["elements"]) == 2  # Only the first two elements have confidence > threshold
    for element in structure["elements"]:
        assert element["confidence"] > structure_recognition_model.confidence_threshold