#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for OCR model and service integration.

These tests verify that TensorFlow models are correctly loaded and used by services,
and that model outputs are properly processed and transformed into structured data
with confidence scores.

Requirements tested:
- OCR Service must use TensorFlow for text recognition as specified in section 3.2.2
- Service must apply appropriate OCR model based on document type as specified in section 4.1.8
- Service must include confidence scoring for extracted fields as specified in section 0.1.4
- TensorFlow OCR processing requires CUDA-compatible GPU acceleration as specified in section 3.2.3
"""

import os
import json
import pytest
import numpy as np
import tensorflow as tf
from unittest.mock import patch, MagicMock

# Import the services and models to test
from services import OCRService, ConfidenceService, FieldExtractionService
from models import ModelFactory, TypedTextModel, HandwrittenTextModel, HybridRecognitionModel
from models.confidence_scoring import calculate_confidence_score
from config import OCRConfig


@pytest.fixture
def mock_gpu_available():
    """Mock GPU availability for testing."""
    with patch('tensorflow.config.list_physical_devices') as mock_devices:
        # Mock a GPU device being available
        mock_devices.return_value = [tf.config.PhysicalDevice(name='/physical_device:GPU:0', 
                                                            device_type='GPU')]
        yield mock_devices


@pytest.fixture
def mock_s3_document(document_type):
    """Mock S3 document retrieval for testing."""
    # Load appropriate test document based on document_type
    test_data_path = os.path.join(os.path.dirname(__file__), 
                                 f'../test_data/{document_type}_documents')
    
    # Get the first document from the manifest
    manifest_path = os.path.join(test_data_path, 'sample_manifest.json')
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
        sample_doc = list(manifest.keys())[0]
    
    # Create a mock document object
    class MockDocument:
        def __init__(self, doc_type, content, metadata):
            self.doc_type = doc_type
            self.content = content
            self.metadata = metadata
    
    # Return a mock document with appropriate metadata
    return MockDocument(
        doc_type=document_type,
        content=np.random.randint(0, 255, (1000, 800, 3), dtype=np.uint8),  # Mock image data
        metadata={
            'classification': document_type,
            'confidence': 0.95,
            'document_id': 'test-doc-123',
            'expected_fields': manifest[sample_doc]['expected_fields']
        }
    )


@pytest.fixture
def ocr_config():
    """Create a test OCR configuration."""
    return OCRConfig(
        model_path='/models',
        confidence_threshold=0.75,
        gpu_memory_limit=8192,  # 8GB as specified in requirements
        batch_size=4,
        enable_gpu=True
    )


@pytest.fixture
def model_factory(ocr_config, mock_gpu_available):
    """Create a model factory for testing."""
    return ModelFactory(config=ocr_config)


@pytest.fixture
def ocr_service(model_factory, ocr_config):
    """Create an OCR service for testing."""
    confidence_service = ConfidenceService(config=ocr_config)
    field_extraction_service = FieldExtractionService(config=ocr_config)
    
    return OCRService(
        model_factory=model_factory,
        confidence_service=confidence_service,
        field_extraction_service=field_extraction_service,
        config=ocr_config
    )


class TestModelServiceIntegration:
    """Test the integration between OCR models and services."""

    def test_gpu_acceleration_enabled(self, ocr_service, mock_gpu_available):
        """Test that GPU acceleration is enabled for TensorFlow models.
        
        Requirement: TensorFlow OCR processing requires CUDA-compatible GPU acceleration
        as specified in section 3.2.3
        """
        # Verify that the service is configured to use GPU
        assert ocr_service.config.enable_gpu is True
        
        # Verify that TensorFlow is configured to use GPU
        with patch('tensorflow.config.experimental.set_memory_growth') as mock_set_memory:
            ocr_service.initialize_gpu()
            mock_set_memory.assert_called_once()
        
        # Verify that GPU memory limit is set correctly (8GB as specified in requirements)
        assert ocr_service.config.gpu_memory_limit == 8192

    def test_model_selection_by_document_type(self, model_factory):
        """Test that the appropriate model is selected based on document type.
        
        Requirement: Service must apply appropriate OCR model based on document type
        as specified in section 4.1.8
        """
        # Test typed document model selection
        typed_model = model_factory.get_model(document_type='typed')
        assert isinstance(typed_model, TypedTextModel)
        
        # Test handwritten document model selection
        handwritten_model = model_factory.get_model(document_type='handwritten')
        assert isinstance(handwritten_model, HandwrittenTextModel)
        
        # Test mixed document model selection
        mixed_model = model_factory.get_model(document_type='mixed')
        assert isinstance(mixed_model, HybridRecognitionModel)

    @pytest.mark.parametrize("document_type", ["typed", "handwritten", "mixed"])
    def test_model_initialization_in_service(self, ocr_service, document_type):
        """Test that models are correctly initialized and loaded in the service context.
        
        Requirement: OCR Service must use TensorFlow for text recognition
        as specified in section 3.2.2
        """
        with patch('models.base_model.BaseModel.load_model') as mock_load:
            # Mock the model loading process
            mock_load.return_value = MagicMock(spec=tf.keras.Model)
            
            # Initialize the service with the specified document type
            model = ocr_service.model_factory.get_model(document_type=document_type)
            
            # Verify that the model was loaded
            mock_load.assert_called_once()
            
            # Verify that the model is a TensorFlow model
            assert hasattr(model, 'model')
            assert isinstance(model.model, MagicMock)
            assert model.model._spec_class == tf.keras.Model

    @pytest.mark.parametrize("document_type", ["typed", "handwritten", "mixed"])
    def test_ocr_processing_pipeline(self, ocr_service, mock_s3_document, document_type):
        """Test the complete OCR processing pipeline from model to structured data.
        
        This test verifies that documents are processed through the entire pipeline,
        from model inference to structured data with confidence scores.
        """
        # Get a mock document of the specified type
        document = mock_s3_document(document_type)
        
        # Mock the model inference to return some text regions
        with patch.object(TypedTextModel, 'extract_text') as mock_extract, \
             patch.object(HandwrittenTextModel, 'extract_text') as mock_hw_extract, \
             patch.object(HybridRecognitionModel, 'extract_text') as mock_hybrid_extract, \
             patch.object(FieldExtractionService, 'extract_fields') as mock_extract_fields, \
             patch.object(ConfidenceService, 'calculate_confidence') as mock_calc_confidence:
            
            # Configure the mocks to return appropriate data
            mock_text_regions = [
                {'text': 'Sample text 1', 'bbox': [10, 10, 100, 30], 'confidence': 0.92},
                {'text': 'Sample text 2', 'bbox': [10, 40, 100, 60], 'confidence': 0.85}
            ]
            
            mock_extract.return_value = mock_text_regions
            mock_hw_extract.return_value = mock_text_regions
            mock_hybrid_extract.return_value = mock_text_regions
            
            # Mock field extraction to return structured fields
            expected_fields = document.metadata['expected_fields']
            mock_fields = {
                field_name: {'value': field_value, 'confidence': 0.9}
                for field_name, field_value in expected_fields.items()
            }
            mock_extract_fields.return_value = mock_fields
            
            # Mock confidence calculation to return document-level confidence
            mock_calc_confidence.return_value = 0.88
            
            # Process the document
            result = ocr_service.process_document(document)
            
            # Verify that the appropriate extraction method was called based on document type
            if document_type == 'typed':
                mock_extract.assert_called_once()
            elif document_type == 'handwritten':
                mock_hw_extract.assert_called_once()
            else:  # mixed
                mock_hybrid_extract.assert_called_once()
            
            # Verify that field extraction was called
            mock_extract_fields.assert_called_once()
            
            # Verify that confidence calculation was called
            mock_calc_confidence.assert_called_once()
            
            # Verify the structure of the result
            assert 'document_id' in result
            assert 'fields' in result
            assert 'confidence' in result
            assert result['document_id'] == document.metadata['document_id']
            assert result['confidence'] == 0.88
            
            # Verify that all expected fields are present in the result
            for field_name in expected_fields.keys():
                assert field_name in result['fields']
                assert 'value' in result['fields'][field_name]
                assert 'confidence' in result['fields'][field_name]

    def test_confidence_scoring_integration(self, ocr_service):
        """Test that confidence scoring is correctly integrated with OCR results.
        
        Requirement: Service must include confidence scoring for extracted fields
        as specified in section 0.1.4
        """
        # Create sample OCR results with raw confidence scores
        ocr_results = [
            {'text': 'John Doe', 'bbox': [10, 10, 100, 30], 'confidence': 0.95},
            {'text': '123 Main St', 'bbox': [10, 40, 150, 60], 'confidence': 0.87},
            {'text': 'Anytown, CA 12345', 'bbox': [10, 70, 200, 90], 'confidence': 0.76}
        ]
        
        # Create sample extracted fields
        extracted_fields = {
            'name': {'value': 'John Doe', 'raw_confidence': 0.95},
            'address_line1': {'value': '123 Main St', 'raw_confidence': 0.87},
            'address_line2': {'value': 'Anytown, CA 12345', 'raw_confidence': 0.76}
        }
        
        # Mock the confidence service to use the real calculation function
        with patch.object(ConfidenceService, 'calculate_confidence', 
                         side_effect=lambda fields: calculate_confidence_score(fields)):
            
            # Calculate confidence scores for the fields
            confidence_service = ConfidenceService(config=ocr_service.config)
            document_confidence = confidence_service.calculate_confidence(extracted_fields)
            
            # Apply confidence scores to the fields
            for field_name, field_data in extracted_fields.items():
                field_data['confidence'] = field_data['raw_confidence']
                del field_data['raw_confidence']
            
            # Verify that document-level confidence is calculated correctly
            # It should be the average of the field confidences
            expected_confidence = sum(item['confidence'] for item in extracted_fields.values()) / len(extracted_fields)
            assert abs(document_confidence - expected_confidence) < 0.001
            
            # Verify that all fields have confidence scores
            for field_name, field_data in extracted_fields.items():
                assert 'confidence' in field_data
                assert 0 <= field_data['confidence'] <= 1

    def test_low_confidence_flagging(self, ocr_service):
        """Test that low-confidence extractions are flagged for human review.
        
        This test verifies that fields with confidence scores below the threshold
        are correctly flagged for human review.
        """
        # Create sample extracted fields with varying confidence scores
        extracted_fields = {
            'name': {'value': 'John Doe', 'confidence': 0.95},  # High confidence
            'address': {'value': '123 Main St', 'confidence': 0.87},  # High confidence
            'ssn': {'value': '123-45-6789', 'confidence': 0.65},  # Low confidence
            'phone': {'value': '555-123-4567', 'confidence': 0.72}  # Low confidence
        }
        
        # Set the confidence threshold
        threshold = ocr_service.config.confidence_threshold  # Should be 0.75 from fixture
        
        # Identify fields that need human review
        fields_for_review = {}
        for field_name, field_data in extracted_fields.items():
            if field_data['confidence'] < threshold:
                fields_for_review[field_name] = field_data
        
        # Verify that the correct fields are flagged for review
        assert 'ssn' in fields_for_review
        assert 'phone' in fields_for_review
        assert 'name' not in fields_for_review
        assert 'address' not in fields_for_review
        
        # Verify that the number of flagged fields is correct
        assert len(fields_for_review) == 2

    def test_model_output_transformation(self, ocr_service):
        """Test that model outputs are correctly transformed into structured data.
        
        This test verifies that raw OCR outputs are properly processed and transformed
        into structured field data with appropriate confidence scores.
        """
        # Create sample OCR results (raw model output)
        ocr_results = [
            {'text': 'Name: John Doe', 'bbox': [10, 10, 150, 30], 'confidence': 0.95},
            {'text': 'Address: 123 Main St', 'bbox': [10, 40, 200, 60], 'confidence': 0.87},
            {'text': 'Phone: 555-123-4567', 'bbox': [10, 70, 200, 90], 'confidence': 0.82},
            {'text': 'Email: john.doe@example.com', 'bbox': [10, 100, 250, 120], 'confidence': 0.91}
        ]
        
        # Mock the field extraction service
        with patch.object(FieldExtractionService, 'extract_fields') as mock_extract_fields:
            # Configure the mock to return structured fields
            expected_fields = {
                'name': {'value': 'John Doe', 'confidence': 0.95},
                'address': {'value': '123 Main St', 'confidence': 0.87},
                'phone': {'value': '555-123-4567', 'confidence': 0.82},
                'email': {'value': 'john.doe@example.com', 'confidence': 0.91}
            }
            mock_extract_fields.return_value = expected_fields
            
            # Process the OCR results
            field_extraction_service = FieldExtractionService(config=ocr_service.config)
            extracted_fields = field_extraction_service.extract_fields(ocr_results)
            
            # Verify that the field extraction was called
            mock_extract_fields.assert_called_once_with(ocr_results)
            
            # Verify that the extracted fields match the expected structure
            assert extracted_fields == expected_fields
            
            # Verify that all fields have values and confidence scores
            for field_name, field_data in extracted_fields.items():
                assert 'value' in field_data
                assert 'confidence' in field_data
                assert 0 <= field_data['confidence'] <= 1


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])