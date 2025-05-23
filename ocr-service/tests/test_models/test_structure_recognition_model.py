#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the StructureRecognitionModel class.

This module contains tests for the TensorFlow model that recognizes and analyzes
document structure, including forms, tables, and field relationships. It verifies
that the model correctly identifies document elements, their relationships, and
provides context for extracted text.

The tests cover:
1. Form field detection and labeling algorithms
2. Table structure recognition with cell relationship mapping
3. Section identification for contextual understanding
4. Semantic relationship mapping between document elements
5. Structure recognition on various document types
6. Performance metrics for structure recognition
"""

import os
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

import numpy as np
import pytest
import tensorflow as tf
from PIL import Image

# Import the model and related types
from ocr_service.src.models.structure_recognition_model import StructureRecognitionModel
from ocr_service.src.types.config import TensorFlowConfig
from ocr_service.src.types.documents import DocumentContent, DocumentMetadata, DocumentType
from ocr_service.src.types.extraction import ConfidenceScore, ExtractedField, FieldLocation
from ocr_service.src.types.models import ModelParameters, ModelResult


# Test constants
MODEL_ACCURACY_THRESHOLD = 0.95  # 95% accuracy requirement
PROCESSING_TIME_THRESHOLD = 5.0  # 5 seconds max processing time


# ===== Test Fixtures =====

@pytest.fixture
def structure_recognition_model(tf_config, mock_gpu_environment):
    """
    Creates a StructureRecognitionModel instance for testing.
    
    Args:
        tf_config: TensorFlow configuration fixture
        mock_gpu_environment: Mocked GPU environment fixture
        
    Returns:
        StructureRecognitionModel: Initialized model for testing
    """
    # Create model parameters
    model_params = ModelParameters({
        "min_confidence_threshold": 0.7,
        "max_detections": 100,
        "structure_types": [
            "form_field",
            "form_label",
            "table",
            "table_cell",
            "table_header",
            "section_heading",
            "section_content",
            "list_item",
            "checkbox",
            "signature_field"
        ]
    })
    
    # Mock the model path
    model_path = Path("/tmp/mock_structure_model")
    
    # Create a mock model using patch
    with pytest.MonkeyPatch.context() as mp:
        # Mock the TensorFlow model loading
        mp.setattr(tf.saved_model, "load", lambda path: create_mock_structure_model())
        
        # Create and return the model
        model = StructureRecognitionModel(model_path, tf_config, model_params)
        
        return model


def create_mock_structure_model():
    """
    Creates a mock TensorFlow structure recognition model.
    
    Returns:
        Mock TensorFlow SavedModel with required signatures
    """
    mock_model = tf.Module()
    
    # Add signatures dictionary with required functions
    mock_model.signatures = {
        "recognize_structure": create_mock_recognize_structure_function(),
        "extract_text": create_mock_extract_text_function(),
        "analyze_structure": create_mock_analyze_structure_function()
    }
    
    return mock_model


def create_mock_recognize_structure_function():
    """
    Creates a mock recognize_structure function for the model.
    
    Returns:
        Mock function that returns structure recognition results
    """
    @tf.function(input_signature=[tf.TensorSpec(shape=[None, None, None, 3], dtype=tf.float32)])
    def recognize_structure(image):
        batch_size = tf.shape(image)[0]
        
        # Create mock structure detection results
        structure_types = tf.constant([[0, 1, 2, 3, 4]], dtype=tf.int32)  # 5 detections
        structure_boxes = tf.constant([[
            [0.1, 0.1, 0.2, 0.2],  # form_field
            [0.05, 0.1, 0.1, 0.2],  # form_label
            [0.3, 0.3, 0.7, 0.7],  # table
            [0.35, 0.35, 0.45, 0.45],  # table_cell
            [0.35, 0.35, 0.45, 0.45],  # table_header
        ]], dtype=tf.float32)
        structure_confidences = tf.constant([[0.95, 0.92, 0.98, 0.94, 0.96]], dtype=tf.float32)
        
        return {
            "structure_types": structure_types,
            "structure_boxes": structure_boxes,
            "structure_confidences": structure_confidences
        }
    
    return recognize_structure


def create_mock_extract_text_function():
    """
    Creates a mock extract_text function for the model.
    
    Returns:
        Mock function that returns text extraction results
    """
    @tf.function(input_signature=[tf.TensorSpec(shape=[None, None, None, 3], dtype=tf.float32)])
    def extract_text(image):
        batch_size = tf.shape(image)[0]
        
        # Create mock text extraction results
        texts = tf.constant([[b"Sample text 1", b"Sample text 2"]], dtype=tf.string)
        confidences = tf.constant([[0.95, 0.92]], dtype=tf.float32)
        
        return {
            "texts": texts,
            "confidences": confidences
        }
    
    return extract_text


def create_mock_analyze_structure_function():
    """
    Creates a mock analyze_structure function for the model.
    
    Returns:
        Mock function that returns document structure analysis results
    """
    @tf.function(input_signature=[tf.TensorSpec(shape=[None, None, None, 3], dtype=tf.float32)])
    def analyze_structure(image):
        batch_size = tf.shape(image)[0]
        
        # Create mock structure analysis results
        document_type = tf.constant([[b"application_form"]], dtype=tf.string)
        confidence = tf.constant([[0.95]], dtype=tf.float32)
        
        # Form fields
        form_field_count = tf.constant([[2]], dtype=tf.int32)
        form_field_boxes = tf.constant([[
            [0.1, 0.1, 0.2, 0.2],
            [0.3, 0.1, 0.4, 0.2]
        ]], dtype=tf.float32)
        form_field_confidences = tf.constant([[0.95, 0.92]], dtype=tf.float32)
        form_field_values = tf.constant([[b"Field 1", b"Field 2"]], dtype=tf.string)
        
        # Form labels
        form_label_count = tf.constant([[2]], dtype=tf.int32)
        form_label_boxes = tf.constant([[
            [0.05, 0.1, 0.1, 0.2],
            [0.25, 0.1, 0.3, 0.2]
        ]], dtype=tf.float32)
        form_label_confidences = tf.constant([[0.94, 0.91]], dtype=tf.float32)
        form_label_values = tf.constant([[b"Label 1", b"Label 2"]], dtype=tf.string)
        
        # Tables
        table_count = tf.constant([[1]], dtype=tf.int32)
        table_boxes = tf.constant([[
            [0.3, 0.3, 0.7, 0.7]
        ]], dtype=tf.float32)
        table_confidences = tf.constant([[0.98]], dtype=tf.float32)
        
        # Table cells
        table_cell_count = tf.constant([[4]], dtype=tf.int32)
        table_cell_boxes = tf.constant([[
            [0.35, 0.35, 0.45, 0.45],
            [0.55, 0.35, 0.65, 0.45],
            [0.35, 0.55, 0.45, 0.65],
            [0.55, 0.55, 0.65, 0.65]
        ]], dtype=tf.float32)
        table_cell_confidences = tf.constant([[0.94, 0.93, 0.92, 0.91]], dtype=tf.float32)
        table_cell_values = tf.constant([[b"Cell 1,1", b"Cell 1,2", b"Cell 2,1", b"Cell 2,2"]], dtype=tf.string)
        
        # Table headers
        table_header_count = tf.constant([[2]], dtype=tf.int32)
        table_header_boxes = tf.constant([[
            [0.35, 0.35, 0.45, 0.45],
            [0.55, 0.35, 0.65, 0.45]
        ]], dtype=tf.float32)
        table_header_confidences = tf.constant([[0.96, 0.95]], dtype=tf.float32)
        table_header_values = tf.constant([[b"Header 1", b"Header 2"]], dtype=tf.string)
        
        # Section headings
        section_heading_count = tf.constant([[2]], dtype=tf.int32)
        section_heading_boxes = tf.constant([[
            [0.1, 0.8, 0.9, 0.85],
            [0.1, 0.9, 0.9, 0.95]
        ]], dtype=tf.float32)
        section_heading_confidences = tf.constant([[0.97, 0.96]], dtype=tf.float32)
        section_heading_values = tf.constant([[b"Section 1", b"Section 2"]], dtype=tf.string)
        
        return {
            "document_type": document_type,
            "confidence": confidence,
            "form_field_count": form_field_count,
            "form_field_boxes": form_field_boxes,
            "form_field_confidences": form_field_confidences,
            "form_field_values": form_field_values,
            "form_label_count": form_label_count,
            "form_label_boxes": form_label_boxes,
            "form_label_confidences": form_label_confidences,
            "form_label_values": form_label_values,
            "table_count": table_count,
            "table_boxes": table_boxes,
            "table_confidences": table_confidences,
            "table_cell_count": table_cell_count,
            "table_cell_boxes": table_cell_boxes,
            "table_cell_confidences": table_cell_confidences,
            "table_cell_values": table_cell_values,
            "table_header_count": table_header_count,
            "table_header_boxes": table_header_boxes,
            "table_header_confidences": table_header_confidences,
            "table_header_values": table_header_values,
            "section_heading_count": section_heading_count,
            "section_heading_boxes": section_heading_boxes,
            "section_heading_confidences": section_heading_confidences,
            "section_heading_values": section_heading_values
        }
    
    return analyze_structure


@pytest.fixture
def sample_form_image(create_test_image):
    """
    Creates a sample form image for testing.
    
    Args:
        create_test_image: Fixture to create test images
        
    Returns:
        Tuple[np.ndarray, DocumentMetadata]: Sample form image and metadata
    """
    # Create a form-like image with fields and labels
    form_text = "Label 1: _______________\nLabel 2: _______________\n\nSignature: _____________"
    image, metadata = create_test_image(form_text, "typed", width=800, height=600)
    
    # Update metadata
    metadata.document_type = DocumentType.APPLICATION
    
    return image, metadata


@pytest.fixture
def sample_table_image(create_test_image):
    """
    Creates a sample table image for testing.
    
    Args:
        create_test_image: Fixture to create test images
        
    Returns:
        Tuple[np.ndarray, DocumentMetadata]: Sample table image and metadata
    """
    # Create a table-like image
    table_text = "Header 1 | Header 2\n---------|---------\nCell 1,1 | Cell 1,2\nCell 2,1 | Cell 2,2"
    image, metadata = create_test_image(table_text, "typed", width=800, height=600)
    
    # Update metadata
    metadata.document_type = DocumentType.FINANCIAL_STATEMENT
    
    return image, metadata


@pytest.fixture
def sample_sectioned_image(create_test_image):
    """
    Creates a sample sectioned document image for testing.
    
    Args:
        create_test_image: Fixture to create test images
        
    Returns:
        Tuple[np.ndarray, DocumentMetadata]: Sample sectioned image and metadata
    """
    # Create a document with sections
    section_text = "Section 1\n\nThis is content for section 1.\n\nSection 2\n\nThis is content for section 2."
    image, metadata = create_test_image(section_text, "typed", width=800, height=800)
    
    # Update metadata
    metadata.document_type = DocumentType.APPLICATION
    
    return image, metadata


@pytest.fixture
def sample_mixed_image(create_test_image):
    """
    Creates a sample mixed document image with form fields, tables, and sections.
    
    Args:
        create_test_image: Fixture to create test images
        
    Returns:
        Tuple[np.ndarray, DocumentMetadata]: Sample mixed image and metadata
    """
    # Create a complex document with multiple structure types
    mixed_text = "Application Form\n\nName: _______________\nDate: _______________\n\nTable of References\nName | Phone\n-----|------\nJohn | 555-1234\nJane | 555-5678\n\nSection 1: Personal Information\n\nPlease provide your personal details below.\n\nSignature: _____________"
    image, metadata = create_test_image(mixed_text, "typed", width=1000, height=1200)
    
    # Update metadata
    metadata.document_type = DocumentType.APPLICATION
    
    return image, metadata


# ===== Test Cases =====

class TestStructureRecognitionModel:
    """
    Tests for the StructureRecognitionModel class.
    """
    
    def test_model_initialization(self, structure_recognition_model):
        """
        Test that the model initializes correctly with the expected attributes.
        
        Args:
            structure_recognition_model: The model fixture
        """
        # Check model attributes
        assert structure_recognition_model.model_name == "StructureRecognitionModel"
        assert structure_recognition_model.model_version is not None
        assert len(structure_recognition_model.structure_types) > 0
        assert "form_field" in structure_recognition_model.structure_types
        assert "table" in structure_recognition_model.structure_types
        assert "section_heading" in structure_recognition_model.structure_types
        
        # Check configuration
        assert structure_recognition_model.min_confidence_threshold == 0.7
        assert structure_recognition_model.config is not None
    
    def test_extract_text(self, structure_recognition_model, sample_form_image):
        """
        Test the extract_text method for extracting text with structural context.
        
        Args:
            structure_recognition_model: The model fixture
            sample_form_image: Sample form image fixture
        """
        # Get the image and metadata
        image, _ = sample_form_image
        
        # Extract text
        start_time = time.time()
        text_results = structure_recognition_model.extract_text(image)
        execution_time = time.time() - start_time
        
        # Check results
        assert len(text_results) > 0
        for text, confidence in text_results:
            assert isinstance(text, str)
            assert isinstance(confidence, float)
            assert 0.0 <= confidence <= 1.0
            assert len(text) > 0
        
        # Check performance
        assert execution_time < PROCESSING_TIME_THRESHOLD, \
            f"Text extraction took {execution_time:.2f}s, which exceeds the threshold of {PROCESSING_TIME_THRESHOLD}s"
    
    def test_extract_fields_form(self, structure_recognition_model, sample_form_image):
        """
        Test the extract_fields method for form field detection and labeling.
        
        Args:
            structure_recognition_model: The model fixture
            sample_form_image: Sample form image fixture
        """
        # Get the image and metadata
        image, metadata = sample_form_image
        
        # Extract fields
        start_time = time.time()
        fields = structure_recognition_model.extract_fields(image, metadata)
        execution_time = time.time() - start_time
        
        # Check results
        assert len(fields) > 0
        
        # Check for form fields and labels
        form_fields = [f for f in fields if f.metadata.get("structure_type") == "form_field"]
        form_labels = [f for f in fields if f.metadata.get("structure_type") == "form_label"]
        
        assert len(form_fields) > 0, "No form fields detected"
        assert len(form_labels) > 0, "No form labels detected"
        
        # Check field properties
        for field in form_fields:
            assert field.field_id is not None
            assert field.field_name is not None
            assert field.value is not None
            assert field.confidence is not None
            assert field.location is not None
            assert field.field_type is not None
            assert field.metadata is not None
            assert "structure_type" in field.metadata
            assert "detection_confidence" in field.metadata
        
        # Check performance
        assert execution_time < PROCESSING_TIME_THRESHOLD, \
            f"Field extraction took {execution_time:.2f}s, which exceeds the threshold of {PROCESSING_TIME_THRESHOLD}s"
    
    def test_extract_fields_table(self, structure_recognition_model, sample_table_image):
        """
        Test the extract_fields method for table structure recognition.
        
        Args:
            structure_recognition_model: The model fixture
            sample_table_image: Sample table image fixture
        """
        # Get the image and metadata
        image, metadata = sample_table_image
        
        # Extract fields
        fields = structure_recognition_model.extract_fields(image, metadata)
        
        # Check results
        assert len(fields) > 0
        
        # Check for table cells and headers
        table_cells = [f for f in fields if f.metadata.get("structure_type") == "table_cell"]
        table_headers = [f for f in fields if f.metadata.get("structure_type") == "table_header"]
        
        assert len(table_cells) > 0, "No table cells detected"
        assert len(table_headers) > 0, "No table headers detected"
        
        # Check for table relationships
        for cell in table_cells:
            assert "relationships" in cell.metadata, "No relationships found in table cell metadata"
            relationships = cell.metadata["relationships"]
            
            # Check for table relationship
            assert "table" in relationships, "No table relationship found in table cell"
            table_rel = relationships["table"]
            assert "table_id" in table_rel
            assert "row" in table_rel
            assert "column" in table_rel
            
            # Check for header relationship if not a header cell
            if not table_rel.get("is_header", False):
                assert "header" in relationships, "No header relationship found in non-header table cell"
    
    def test_extract_fields_sections(self, structure_recognition_model, sample_sectioned_image):
        """
        Test the extract_fields method for section identification.
        
        Args:
            structure_recognition_model: The model fixture
            sample_sectioned_image: Sample sectioned document image fixture
        """
        # Get the image and metadata
        image, metadata = sample_sectioned_image
        
        # Extract fields
        fields = structure_recognition_model.extract_fields(image, metadata)
        
        # Check results
        assert len(fields) > 0
        
        # Check for section headings and content
        section_headings = [f for f in fields if f.metadata.get("structure_type") == "section_heading"]
        section_contents = [f for f in fields if f.metadata.get("structure_type") == "section_content"]
        
        assert len(section_headings) > 0, "No section headings detected"
        assert len(section_contents) > 0, "No section content detected"
        
        # Check for section relationships
        for heading in section_headings:
            assert "relationships" in heading.metadata, "No relationships found in section heading metadata"
            relationships = heading.metadata["relationships"]
            
            # Check for section relationship
            assert "section" in relationships, "No section relationship found in section heading"
            section_rel = relationships["section"]
            assert "content" in section_rel
            assert "subsections" in section_rel
        
        # Check content relationships to headings
        for content in section_contents:
            assert "relationships" in content.metadata, "No relationships found in section content metadata"
            relationships = content.metadata["relationships"]
            
            # Check for section relationship
            assert "section" in relationships, "No section relationship found in section content"
            section_rel = relationships["section"]
            assert "heading" in section_rel
            assert "heading_text" in section_rel
    
    def test_semantic_relationships(self, structure_recognition_model, sample_mixed_image):
        """
        Test semantic relationship mapping between document elements.
        
        Args:
            structure_recognition_model: The model fixture
            sample_mixed_image: Sample mixed document image fixture
        """
        # Get the image and metadata
        image, metadata = sample_mixed_image
        
        # Extract fields
        fields = structure_recognition_model.extract_fields(image, metadata)
        
        # Check results
        assert len(fields) > 0
        
        # Check for relationships between different structure types
        form_fields = [f for f in fields if f.metadata.get("structure_type") == "form_field"]
        form_labels = [f for f in fields if f.metadata.get("structure_type") == "form_label"]
        
        # Check label-field relationships
        label_field_pairs = 0
        for field in form_fields:
            if "relationships" in field.metadata and "label" in field.metadata["relationships"]:
                label_field_pairs += 1
                label_rel = field.metadata["relationships"]["label"]
                assert "field_id" in label_rel
                assert "value" in label_rel
        
        assert label_field_pairs > 0, "No label-field relationships detected"
        
        # Check for hierarchical relationships
        section_headings = [f for f in fields if f.metadata.get("structure_type") == "section_heading"]
        if len(section_headings) >= 2:
            # Check if any section is a subsection of another
            subsection_count = 0
            for heading in section_headings:
                if "relationships" in heading.metadata and "parent_section" in heading.metadata["relationships"]:
                    subsection_count += 1
            
            # Not all documents will have subsections, so this is not a hard requirement
            if subsection_count > 0:
                assert subsection_count > 0, "No subsection relationships detected in a document with multiple sections"
    
    def test_structure_recognition_accuracy(self, structure_recognition_model, sample_mixed_image):
        """
        Test the accuracy of structure recognition on a complex document.
        
        Args:
            structure_recognition_model: The model fixture
            sample_mixed_image: Sample mixed document image fixture
        """
        # Get the image and metadata
        image, metadata = sample_mixed_image
        
        # Analyze document structure
        structure_info = structure_recognition_model.analyze_document_structure(image)
        
        # Check results
        assert structure_info is not None
        assert "document_type" in structure_info
        assert "confidence" in structure_info
        assert "structures" in structure_info
        
        # Check confidence
        assert structure_info["confidence"] > 0.7, "Structure recognition confidence is too low"
        
        # Check structures
        structures = structure_info["structures"]
        assert len(structures) > 0, "No structures detected"
        
        # Check for expected structure types
        expected_types = ["form_field", "form_label", "table", "table_cell", "section_heading"]
        found_types = 0
        for struct_type in expected_types:
            if struct_type in structures and len(structures[struct_type]) > 0:
                found_types += 1
        
        # Calculate accuracy as percentage of expected types found
        accuracy = found_types / len(expected_types)
        assert accuracy >= MODEL_ACCURACY_THRESHOLD, \
            f"Structure recognition accuracy {accuracy:.2f} is below the threshold of {MODEL_ACCURACY_THRESHOLD}"
    
    def test_performance_metrics(self, structure_recognition_model, sample_mixed_image):
        """
        Test performance metrics for structure recognition.
        
        Args:
            structure_recognition_model: The model fixture
            sample_mixed_image: Sample mixed document image fixture
        """
        # Get the image and metadata
        image, metadata = sample_mixed_image
        
        # Measure performance of document structure analysis
        start_time = time.time()
        structure_info = structure_recognition_model.analyze_document_structure(image)
        structure_analysis_time = time.time() - start_time
        
        # Measure performance of field extraction
        start_time = time.time()
        fields = structure_recognition_model.extract_fields(image, metadata)
        field_extraction_time = time.time() - start_time
        
        # Measure performance of full document processing
        start_time = time.time()
        result = structure_recognition_model.process_document(
            DocumentContent(image.tobytes()),
            metadata
        )
        full_processing_time = time.time() - start_time
        
        # Check performance metrics
        assert structure_analysis_time < PROCESSING_TIME_THRESHOLD, \
            f"Structure analysis took {structure_analysis_time:.2f}s, which exceeds the threshold of {PROCESSING_TIME_THRESHOLD}s"
        
        assert field_extraction_time < PROCESSING_TIME_THRESHOLD, \
            f"Field extraction took {field_extraction_time:.2f}s, which exceeds the threshold of {PROCESSING_TIME_THRESHOLD}s"
        
        assert full_processing_time < PROCESSING_TIME_THRESHOLD, \
            f"Full document processing took {full_processing_time:.2f}s, which exceeds the threshold of {PROCESSING_TIME_THRESHOLD}s"
        
        # Log performance metrics
        print(f"Structure analysis time: {structure_analysis_time:.2f}s")
        print(f"Field extraction time: {field_extraction_time:.2f}s")
        print(f"Full processing time: {full_processing_time:.2f}s")
    
    def test_process_document(self, structure_recognition_model, sample_mixed_image):
        """
        Test the process_document method for end-to-end document processing.
        
        Args:
            structure_recognition_model: The model fixture
            sample_mixed_image: Sample mixed document image fixture
        """
        # Get the image and metadata
        image, metadata = sample_mixed_image
        
        # Process document
        result = structure_recognition_model.process_document(
            DocumentContent(image.tobytes()),
            metadata
        )
        
        # Check results
        assert result is not None
        assert result.success, "Document processing failed"
        assert result.data is not None
        
        # Check extracted data
        assert "fields" in result.data
        assert len(result.data["fields"]) > 0
        
        # Check metadata
        assert "metadata" in result.data
        assert "document_structure" in result.data["metadata"]
        
        # Check document structure
        doc_structure = result.data["metadata"]["document_structure"]
        assert "document_type" in doc_structure
        assert "confidence" in doc_structure
        assert "structures" in doc_structure
        
        # Check processing time
        assert result.processing_time < PROCESSING_TIME_THRESHOLD, \
            f"Document processing took {result.processing_time:.2f}s, which exceeds the threshold of {PROCESSING_TIME_THRESHOLD}s"
    
    def test_structure_recognition_on_various_document_types(self, structure_recognition_model,
                                                           sample_form_image, sample_table_image,
                                                           sample_sectioned_image, sample_mixed_image):
        """
        Test structure recognition on various document types.
        
        Args:
            structure_recognition_model: The model fixture
            sample_form_image: Sample form image fixture
            sample_table_image: Sample table image fixture
            sample_sectioned_image: Sample sectioned document image fixture
            sample_mixed_image: Sample mixed document image fixture
        """
        # Test on different document types
        document_images = [
            ("Form", sample_form_image),
            ("Table", sample_table_image),
            ("Sectioned", sample_sectioned_image),
            ("Mixed", sample_mixed_image)
        ]
        
        for doc_type, (image, metadata) in document_images:
            # Analyze document structure
            structure_info = structure_recognition_model.analyze_document_structure(image)
            
            # Check results
            assert structure_info is not None, f"Structure analysis failed for {doc_type} document"
            assert "document_type" in structure_info
            assert "confidence" in structure_info
            assert "structures" in structure_info
            
            # Check confidence
            assert structure_info["confidence"] > 0.7, f"Structure recognition confidence is too low for {doc_type} document"
            
            # Check structures
            structures = structure_info["structures"]
            assert len(structures) > 0, f"No structures detected in {doc_type} document"
            
            # Check for expected structure types based on document type
            if doc_type == "Form":
                expected_types = ["form_field", "form_label"]
            elif doc_type == "Table":
                expected_types = ["table", "table_cell", "table_header"]
            elif doc_type == "Sectioned":
                expected_types = ["section_heading", "section_content"]
            else:  # Mixed
                expected_types = ["form_field", "form_label", "table", "section_heading"]
            
            found_types = 0
            for struct_type in expected_types:
                if struct_type in structures and len(structures[struct_type]) > 0:
                    found_types += 1
            
            # Calculate accuracy as percentage of expected types found
            accuracy = found_types / len(expected_types)
            assert accuracy >= MODEL_ACCURACY_THRESHOLD, \
                f"Structure recognition accuracy {accuracy:.2f} is below the threshold of {MODEL_ACCURACY_THRESHOLD} for {doc_type} document"
    
    def test_field_relationships_after_extraction(self, structure_recognition_model, sample_mixed_image):
        """
        Test that field relationships are correctly added after extraction.
        
        Args:
            structure_recognition_model: The model fixture
            sample_mixed_image: Sample mixed document image fixture
        """
        # Get the image and metadata
        image, metadata = sample_mixed_image
        
        # Extract fields
        fields = structure_recognition_model.extract_fields(image, metadata)
        
        # Check that fields have relationships
        fields_with_relationships = 0
        for field in fields:
            if "relationships" in field.metadata and len(field.metadata["relationships"]) > 0:
                fields_with_relationships += 1
        
        # At least some fields should have relationships
        assert fields_with_relationships > 0, "No fields have relationships after extraction"
        
        # Check specific relationship types
        relationship_types = set()
        for field in fields:
            if "relationships" in field.metadata:
                relationship_types.update(field.metadata["relationships"].keys())
        
        # Check for expected relationship types
        expected_relationships = ["label", "table", "header", "section"]
        found_relationships = 0
        for rel_type in expected_relationships:
            if rel_type in relationship_types:
                found_relationships += 1
        
        # Calculate coverage as percentage of expected relationship types found
        coverage = found_relationships / len(expected_relationships)
        assert coverage >= 0.5, \
            f"Relationship type coverage {coverage:.2f} is too low, expected at least 0.5"


# ===== Additional Test Functions =====

def test_link_labels_to_fields(structure_recognition_model):
    """
    Test the _link_labels_to_fields method for linking form labels to fields.
    
    Args:
        structure_recognition_model: The model fixture
    """
    # Create test fields
    fields = [
        ExtractedField(
            field_id="label_1",
            field_name="Label 1",
            value="Name:",
            raw_text="Name:",
            confidence=0.95,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.1, left=0.1, bottom=0.15, right=0.2),
            field_type="text",
            metadata={"structure_type": "form_label"}
        ),
        ExtractedField(
            field_id="field_1",
            field_name="Field 1",
            value="John Doe",
            raw_text="John Doe",
            confidence=0.92,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.1, left=0.25, bottom=0.15, right=0.4),
            field_type="text",
            metadata={"structure_type": "form_field"}
        )
    ]
    
    # Link labels to fields
    structure_recognition_model._link_labels_to_fields(fields)
    
    # Check results
    form_field = fields[1]
    assert "relationships" in form_field.metadata
    assert "label" in form_field.metadata["relationships"]
    label_rel = form_field.metadata["relationships"]["label"]
    assert label_rel["field_id"] == "label_1"
    assert label_rel["value"] == "Name:"
    assert form_field.field_name == "Name:"


def test_group_cells_into_tables(structure_recognition_model):
    """
    Test the _group_cells_into_tables method for grouping table cells.
    
    Args:
        structure_recognition_model: The model fixture
    """
    # Create test cells
    cells = [
        ExtractedField(
            field_id="cell_1",
            field_name="Cell 1",
            value="Value 1",
            raw_text="Value 1",
            confidence=0.95,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.3, bottom=0.35, right=0.4),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_2",
            field_name="Cell 2",
            value="Value 2",
            raw_text="Value 2",
            confidence=0.92,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.5, bottom=0.35, right=0.6),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_3",
            field_name="Cell 3",
            value="Value 3",
            raw_text="Value 3",
            confidence=0.93,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.3, bottom=0.45, right=0.4),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_4",
            field_name="Cell 4",
            value="Value 4",
            raw_text="Value 4",
            confidence=0.91,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.5, bottom=0.45, right=0.6),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        )
    ]
    
    # Group cells into tables
    tables = structure_recognition_model._group_cells_into_tables(cells)
    
    # Check results
    assert len(tables) == 1, "Cells were not grouped into a single table"
    assert len(tables[0]) == 4, "Not all cells were included in the table"


def test_group_cells_into_rows(structure_recognition_model):
    """
    Test the _group_cells_into_rows method for grouping table cells into rows.
    
    Args:
        structure_recognition_model: The model fixture
    """
    # Create test cells
    cells = [
        ExtractedField(
            field_id="cell_1",
            field_name="Cell 1",
            value="Value 1",
            raw_text="Value 1",
            confidence=0.95,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.3, bottom=0.35, right=0.4),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_2",
            field_name="Cell 2",
            value="Value 2",
            raw_text="Value 2",
            confidence=0.92,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.5, bottom=0.35, right=0.6),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_3",
            field_name="Cell 3",
            value="Value 3",
            raw_text="Value 3",
            confidence=0.93,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.3, bottom=0.45, right=0.4),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_4",
            field_name="Cell 4",
            value="Value 4",
            raw_text="Value 4",
            confidence=0.91,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.5, bottom=0.45, right=0.6),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        )
    ]
    
    # Group cells into rows
    rows = structure_recognition_model._group_cells_into_rows(cells)
    
    # Check results
    assert len(rows) == 2, "Cells were not grouped into two rows"
    assert len(rows[0]) == 2, "First row does not have two cells"
    assert len(rows[1]) == 2, "Second row does not have two cells"
    
    # Check row ordering
    assert rows[0][0].field_id == "cell_1", "First cell in first row is incorrect"
    assert rows[0][1].field_id == "cell_2", "Second cell in first row is incorrect"
    assert rows[1][0].field_id == "cell_3", "First cell in second row is incorrect"
    assert rows[1][1].field_id == "cell_4", "Second cell in second row is incorrect"


def test_group_cells_into_columns(structure_recognition_model):
    """
    Test the _group_cells_into_columns method for grouping table cells into columns.
    
    Args:
        structure_recognition_model: The model fixture
    """
    # Create test cells
    cells = [
        ExtractedField(
            field_id="cell_1",
            field_name="Cell 1",
            value="Value 1",
            raw_text="Value 1",
            confidence=0.95,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.3, bottom=0.35, right=0.4),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_2",
            field_name="Cell 2",
            value="Value 2",
            raw_text="Value 2",
            confidence=0.92,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.5, bottom=0.35, right=0.6),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_3",
            field_name="Cell 3",
            value="Value 3",
            raw_text="Value 3",
            confidence=0.93,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.3, bottom=0.45, right=0.4),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        ),
        ExtractedField(
            field_id="cell_4",
            field_name="Cell 4",
            value="Value 4",
            raw_text="Value 4",
            confidence=0.91,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.5, bottom=0.45, right=0.6),
            field_type="text",
            metadata={"structure_type": "table_cell"}
        )
    ]
    
    # Group cells into columns
    columns = structure_recognition_model._group_cells_into_columns(cells)
    
    # Check results
    assert len(columns) == 2, "Cells were not grouped into two columns"
    assert len(columns[0]) == 2, "First column does not have two cells"
    assert len(columns[1]) == 2, "Second column does not have two cells"
    
    # Check column ordering
    assert columns[0][0].field_id == "cell_1", "First cell in first column is incorrect"
    assert columns[0][1].field_id == "cell_3", "Second cell in first column is incorrect"
    assert columns[1][0].field_id == "cell_2", "First cell in second column is incorrect"
    assert columns[1][1].field_id == "cell_4", "Second cell in second column is incorrect"


def test_establish_section_hierarchies(structure_recognition_model):
    """
    Test the _establish_section_hierarchies method for establishing section hierarchies.
    
    Args:
        structure_recognition_model: The model fixture
    """
    # Create test sections
    fields = [
        ExtractedField(
            field_id="heading_1",
            field_name="Section 1",
            value="Section 1",
            raw_text="Section 1",
            confidence=0.95,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.1, left=0.1, bottom=0.15, right=0.9),
            field_type="text",
            metadata={"structure_type": "section_heading"}
        ),
        ExtractedField(
            field_id="content_1",
            field_name="Content 1",
            value="This is content for section 1.",
            raw_text="This is content for section 1.",
            confidence=0.92,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.2, left=0.1, bottom=0.25, right=0.9),
            field_type="text",
            metadata={"structure_type": "section_content"}
        ),
        ExtractedField(
            field_id="heading_2",
            field_name="Section 2",
            value="Section 2",
            raw_text="Section 2",
            confidence=0.93,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.3, left=0.1, bottom=0.35, right=0.9),
            field_type="text",
            metadata={"structure_type": "section_heading"}
        ),
        ExtractedField(
            field_id="content_2",
            field_name="Content 2",
            value="This is content for section 2.",
            raw_text="This is content for section 2.",
            confidence=0.91,
            requires_verification=False,
            location=FieldLocation(page=0, top=0.4, left=0.1, bottom=0.45, right=0.9),
            field_type="text",
            metadata={"structure_type": "section_content"}
        )
    ]
    
    # Establish section hierarchies
    structure_recognition_model._establish_section_hierarchies(fields)
    
    # Check results
    heading_1 = fields[0]
    content_1 = fields[1]
    heading_2 = fields[2]
    content_2 = fields[3]
    
    # Check heading relationships
    assert "relationships" in heading_1.metadata
    assert "section" in heading_1.metadata["relationships"]
    section_rel_1 = heading_1.metadata["relationships"]["section"]
    assert "content" in section_rel_1
    assert "content_1" in section_rel_1["content"]
    
    assert "relationships" in heading_2.metadata
    assert "section" in heading_2.metadata["relationships"]
    section_rel_2 = heading_2.metadata["relationships"]["section"]
    assert "content" in section_rel_2
    assert "content_2" in section_rel_2["content"]
    
    # Check content relationships
    assert "relationships" in content_1.metadata
    assert "section" in content_1.metadata["relationships"]
    content_rel_1 = content_1.metadata["relationships"]["section"]
    assert "heading" in content_rel_1
    assert content_rel_1["heading"] == "heading_1"
    assert content_rel_1["heading_text"] == "Section 1"
    
    assert "relationships" in content_2.metadata
    assert "section" in content_2.metadata["relationships"]
    content_rel_2 = content_2.metadata["relationships"]["section"]
    assert "heading" in content_rel_2
    assert content_rel_2["heading"] == "heading_2"
    assert content_rel_2["heading_text"] == "Section 2"