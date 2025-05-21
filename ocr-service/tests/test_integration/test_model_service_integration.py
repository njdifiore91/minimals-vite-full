#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for OCR models and services.

This module tests the integration between TensorFlow models and OCR services,
verifying that models are correctly loaded and used by services, and that model
outputs are properly processed and transformed into structured data with confidence scores.
"""

import os
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, List, Any, Tuple

# Import application modules
from src.models.model_factory import ModelFactory, get_model, get_model_for_document, get_model_by_document_type
from src.models.base_model import BaseModel
from src.services.ocr_service import OCRService
from src.services.confidence_service import ConfidenceService
from src.services.field_extraction_service import FieldExtractionService
from src.types.documents import Document, DocumentType, DocumentMetadata, ProcessingStatus
from src.types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from src.types.models import OCRModelType, ModelResult, ModelParameters
from src.types.errors import ServiceError, ErrorCategory, Result


@pytest.fixture
def mock_tensorflow_model():
    """Create a mock TensorFlow model that returns predefined results."""
    mock_model = MagicMock(spec=BaseModel)
    
    # Configure the mock to return a valid ModelResult
    mock_result = ModelResult(
        model_type=OCRModelType.TYPED,
        extracted_fields=[
            ExtractedField(name="legal_name", value="ABC Corporation", confidence=0.95, page=1),
            ExtractedField(name="dba_name", value="ABC Corp", confidence=0.92, page=1),
            ExtractedField(name="business_address", value="123 Main St, New York, NY 10001", confidence=0.88, page=1),
            ExtractedField(name="business_phone", value="(555) 123-4567", confidence=0.94, page=1),
            ExtractedField(name="tax_id", value="12-3456789", confidence=0.85, page=1),
            ExtractedField(name="requested_amount", value="$50,000", confidence=0.91, page=1),
        ],
        average_confidence=0.91,
        processing_time=1.25,
        metadata={"model_version": "1.0.0"}
    )
    
    mock_model.extract_text.return_value = mock_result
    mock_model.model_type = OCRModelType.TYPED
    
    return mock_model


@pytest.fixture
def mock_handwritten_model():
    """Create a mock handwritten TensorFlow model that returns predefined results."""
    mock_model = MagicMock(spec=BaseModel)
    
    # Configure the mock to return a valid ModelResult with lower confidence scores
    mock_result = ModelResult(
        model_type=OCRModelType.HANDWRITTEN,
        extracted_fields=[
            ExtractedField(name="legal_name", value="XYZ Enterprises", confidence=0.82, page=1),
            ExtractedField(name="dba_name", value="XYZ", confidence=0.79, page=1),
            ExtractedField(name="business_address", value="456 Oak Ave, Boston, MA 02108", confidence=0.75, page=1),
            ExtractedField(name="business_phone", value="(555) 987-6543", confidence=0.81, page=1),
            ExtractedField(name="tax_id", value="98-7654321", confidence=0.72, page=1),
            ExtractedField(name="requested_amount", value="$75,000", confidence=0.78, page=1),
        ],
        average_confidence=0.78,
        processing_time=2.5,
        metadata={"model_version": "1.0.0"}
    )
    
    mock_model.extract_text.return_value = mock_result
    mock_model.model_type = OCRModelType.HANDWRITTEN
    
    return mock_model


@pytest.fixture
def mock_hybrid_model():
    """Create a mock hybrid TensorFlow model that returns predefined results."""
    mock_model = MagicMock(spec=BaseModel)
    
    # Configure the mock to return a valid ModelResult with mixed confidence scores
    mock_result = ModelResult(
        model_type=OCRModelType.HYBRID,
        extracted_fields=[
            ExtractedField(name="legal_name", value="123 Funding LLC", confidence=0.88, page=1),
            ExtractedField(name="dba_name", value="123 Funding", confidence=0.85, page=1),
            ExtractedField(name="business_address", value="789 Pine St, Chicago, IL 60601", confidence=0.82, page=1),
            ExtractedField(name="business_phone", value="(555) 456-7890", confidence=0.87, page=1),
            ExtractedField(name="tax_id", value="45-6789123", confidence=0.79, page=1),
            ExtractedField(name="requested_amount", value="$100,000", confidence=0.84, page=1),
        ],
        average_confidence=0.84,
        processing_time=1.75,
        metadata={"model_version": "1.0.0"}
    )
    
    mock_model.extract_text.return_value = mock_result
    mock_model.model_type = OCRModelType.HYBRID
    
    return mock_model


@pytest.fixture
def mock_model_factory(mock_tensorflow_model, mock_handwritten_model, mock_hybrid_model):
    """Create a mock model factory that returns predefined models."""
    with patch('src.models.model_factory.ModelFactory', autospec=True) as MockFactory:
        factory_instance = MockFactory.return_value
        
        # Configure the factory to return different models based on model type
        factory_instance.get_model.side_effect = lambda model_type: {
            OCRModelType.TYPED: mock_tensorflow_model,
            OCRModelType.HANDWRITTEN: mock_handwritten_model,
            OCRModelType.HYBRID: mock_hybrid_model
        }.get(model_type, mock_hybrid_model)
        
        # Configure the factory to return models based on document type
        factory_instance.get_model_by_document_type.side_effect = lambda doc_type: {
            DocumentType.APPLICATION: mock_hybrid_model,
            DocumentType.TAX_RETURN: mock_tensorflow_model,
            DocumentType.BANK_STATEMENT: mock_tensorflow_model,
            DocumentType.PAY_STUB: mock_tensorflow_model,
            DocumentType.ID_DOCUMENT: mock_hybrid_model,
            DocumentType.OTHER: mock_hybrid_model
        }.get(doc_type, mock_hybrid_model)
        
        # Configure the factory to return models based on document metadata
        factory_instance.get_model_for_document.side_effect = lambda metadata: {
            DocumentType.APPLICATION: mock_hybrid_model,
            DocumentType.TAX_RETURN: mock_tensorflow_model,
            DocumentType.BANK_STATEMENT: mock_tensorflow_model,
            DocumentType.PAY_STUB: mock_tensorflow_model,
            DocumentType.ID_DOCUMENT: mock_hybrid_model,
            DocumentType.OTHER: mock_hybrid_model
        }.get(metadata.document_type, mock_hybrid_model)
        
        yield factory_instance


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    metadata = DocumentMetadata(
        document_id="doc-123456",
        filename="application.pdf",
        mime_type="application/pdf",
        size=12345,
        page_count=1,
        request_id="req-789012"
    )
    
    # Create a dummy document content (would be bytes in real application)
    content = b"Sample document content"
    
    document = Document(
        content=content,
        metadata=metadata,
        document_type=DocumentType.APPLICATION,
        processing_status=ProcessingStatus.PENDING
    )
    
    return document


@pytest.fixture
def mock_gpu_environment():
    """Mock the GPU environment for testing."""
    with patch('src.utils.tensorflow_utils.setup_gpu_environment', return_value=True):
        with patch('src.utils.tensorflow_utils.get_gpu_info', return_value="Tesla T4"):
            yield


@pytest.fixture
def mock_image_utils():
    """Mock image utilities for testing."""
    with patch('src.utils.image_utils.convert_to_image', return_value=np.zeros((100, 100))):
        with patch('src.utils.image_utils.assess_image_quality', return_value=0.95):
            with patch('src.utils.image_utils.preprocess_for_ocr', return_value=np.zeros((100, 100))):
                yield


@pytest.fixture
def ocr_service_with_mocks(mock_model_factory, mock_gpu_environment, mock_image_utils):
    """Create an OCR service with mocked dependencies."""
    with patch('src.models.model_factory.model_factory', mock_model_factory):
        with patch('src.services.ocr_service.ModelFactory', return_value=mock_model_factory):
            # Create the OCR service with mocked dependencies
            service = OCRService()
            yield service


class TestModelServiceIntegration:
    """Test the integration between OCR models and services."""
    
    def test_model_factory_integration_with_ocr_service(self, ocr_service_with_mocks, mock_model_factory):
        """Test that the OCR service correctly integrates with the model factory."""
        # Verify that the OCR service initializes with the model factory
        assert ocr_service_with_mocks.model_factory is not None
        assert ocr_service_with_mocks.model_factory == mock_model_factory
        
        # Verify that the model factory was initialized during OCR service initialization
        mock_model_factory._preload_models.assert_called_once()
    
    def test_model_selection_based_on_document_type(self, ocr_service_with_mocks, mock_model_factory, sample_document):
        """Test that the OCR service selects the appropriate model based on document type."""
        # Process a sample document
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is successful
        assert result.is_success
        
        # Verify that the model factory was called to get the appropriate model
        mock_model_factory.get_model.assert_called_with(OCRModelType.HYBRID)
    
    def test_model_output_processing(self, ocr_service_with_mocks, mock_hybrid_model, sample_document):
        """Test that the OCR service correctly processes model outputs into structured data."""
        # Process a sample document
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            with patch('src.services.ocr_service.OCRService._extract_text', return_value=mock_hybrid_model.extract_text()):
                result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is successful
        assert result.is_success
        
        # Extract the processed data from the result
        extracted_data, processing_time = result.value
        
        # Verify that the extracted data contains the expected fields
        assert extracted_data.document_id == sample_document.metadata.document_id
        assert extracted_data.document_type == sample_document.document_type.name
        assert len(extracted_data.fields) == 6  # Number of fields in the mock model result
        
        # Verify that the field values match the model output
        assert extracted_data.fields["legal_name"]["value"] == "123 Funding LLC"
        assert extracted_data.fields["dba_name"]["value"] == "123 Funding"
        assert extracted_data.fields["business_address"]["value"] == "789 Pine St, Chicago, IL 60601"
        assert extracted_data.fields["business_phone"]["value"] == "(555) 456-7890"
        assert extracted_data.fields["tax_id"]["value"] == "45-6789123"
        assert extracted_data.fields["requested_amount"]["value"] == "$100,000"
        
        # Verify that confidence scores are included
        assert "confidence" in extracted_data.fields["legal_name"]
        assert extracted_data.fields["legal_name"]["confidence"] == 0.88
        
        # Verify that the average confidence is calculated correctly
        assert extracted_data.average_confidence == 0.84
    
    def test_confidence_scoring_integration(self, ocr_service_with_mocks, mock_hybrid_model, sample_document):
        """Test that confidence scoring is correctly integrated with model outputs."""
        # Process a sample document
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            with patch('src.services.ocr_service.OCRService._extract_text', return_value=mock_hybrid_model.extract_text()):
                result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is successful
        assert result.is_success
        
        # Extract the processed data from the result
        extracted_data, processing_time = result.value
        
        # Verify that each field has a confidence score
        for field_name, field_data in extracted_data.fields.items():
            assert "confidence" in field_data
            assert 0 <= field_data["confidence"] <= 1
        
        # Verify that fields have a requires_review flag based on confidence
        for field_name, field_data in extracted_data.fields.items():
            assert "requires_review" in field_data
            # The mock TensorFlow config has a default confidence threshold of 0.8
            # Fields with confidence < 0.8 should be flagged for review
            if field_data["confidence"] < 0.8:
                assert field_data["requires_review"] is True
        
        # Verify that the document has an overall requires_review flag
        assert hasattr(extracted_data, "requires_review")
    
    def test_model_selection_for_different_document_types(self, mock_model_factory):
        """Test that different document types are mapped to appropriate models."""
        # Test model selection for different document types
        document_types = [
            DocumentType.APPLICATION,
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.PAY_STUB,
            DocumentType.ID_DOCUMENT,
            DocumentType.OTHER
        ]
        
        expected_model_types = [
            OCRModelType.HYBRID,  # For APPLICATION
            OCRModelType.TYPED,   # For TAX_RETURN
            OCRModelType.TYPED,   # For BANK_STATEMENT
            OCRModelType.TYPED,   # For PAY_STUB
            OCRModelType.HYBRID,  # For ID_DOCUMENT
            OCRModelType.HYBRID   # For OTHER
        ]
        
        # Test get_model_by_document_type function
        for doc_type, expected_model_type in zip(document_types, expected_model_types):
            with patch('src.models.model_factory.model_factory', mock_model_factory):
                model = get_model_by_document_type(doc_type)
                assert model.model_type == expected_model_type
                mock_model_factory.get_model_by_document_type.assert_called_with(doc_type)
    
    def test_gpu_acceleration_integration(self, ocr_service_with_mocks, mock_hybrid_model, sample_document):
        """Test that GPU acceleration is correctly integrated with model processing."""
        # Process a sample document
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            with patch('src.services.ocr_service.OCRService._extract_text', return_value=mock_hybrid_model.extract_text()):
                result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is successful
        assert result.is_success
        
        # Extract the processed data from the result
        extracted_data, processing_time = result.value
        
        # Verify that GPU acceleration information is included in metadata
        assert "gpu_accelerated" in extracted_data.metadata
        assert extracted_data.metadata["gpu_accelerated"] is True
    
    def test_model_fallback_on_gpu_error(self, ocr_service_with_mocks, mock_hybrid_model, sample_document):
        """Test that the service falls back to CPU when GPU errors occur."""
        # Configure the mock to simulate a GPU memory error on first call, then succeed
        gpu_error_extract_text = MagicMock(side_effect=[
            ServiceError("GPU memory error", ErrorCategory.EXTRACTION, {"error": "CUDA out of memory"}),
            mock_hybrid_model.extract_text()
        ])
        
        # Process a sample document with the mocked extract_text method
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            with patch('src.services.ocr_service.OCRService._extract_text', side_effect=gpu_error_extract_text):
                with patch('src.utils.tensorflow_utils.is_gpu_memory_error', return_value=True):
                    with patch('src.utils.tensorflow_utils.cpu_only_context'):
                        result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is successful (fallback worked)
        assert result.is_success
    
    def test_document_type_specific_preprocessing(self, ocr_service_with_mocks, sample_document):
        """Test that document type-specific preprocessing options are applied."""
        # Test preprocessing options for different document types
        document_types = [
            DocumentType.APPLICATION,
            DocumentType.TAX_RETURN,
            DocumentType.BANK_STATEMENT,
            DocumentType.ID_DOCUMENT
        ]
        
        for doc_type in document_types:
            # Update the sample document with the current document type
            sample_document.document_type = doc_type
            
            # Get preprocessing options for this document type
            preprocessing_options = ocr_service_with_mocks._get_preprocessing_options(doc_type)
            
            # Verify that preprocessing options are returned as a dictionary
            assert isinstance(preprocessing_options, dict)
            
            # Verify that basic preprocessing options are included
            assert "deskew" in preprocessing_options
            assert "denoise" in preprocessing_options
            assert "normalize" in preprocessing_options
            
            # Verify document type-specific options
            if doc_type == DocumentType.ID_DOCUMENT:
                assert preprocessing_options["remove_background"] is False
                assert preprocessing_options["enhance_contrast"] is True
                assert preprocessing_options["sharpen"] is True
            elif doc_type == DocumentType.BANK_STATEMENT:
                assert preprocessing_options["enhance_contrast"] is True
                assert preprocessing_options["remove_background"] is True
            elif doc_type == DocumentType.APPLICATION:
                assert preprocessing_options["denoise"] is True
                assert preprocessing_options["sharpen"] is False
                assert preprocessing_options["binarize"] is False
            elif doc_type == DocumentType.TAX_RETURN:
                assert preprocessing_options["remove_background"] is True
                assert preprocessing_options["sharpen"] is True
    
    def test_error_handling_in_model_integration(self, ocr_service_with_mocks, sample_document):
        """Test that errors in model processing are properly handled."""
        # Configure the extract_text method to raise an error
        error_message = "Model processing error"
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            with patch('src.services.ocr_service.OCRService._extract_text', 
                      side_effect=ServiceError(error_message, ErrorCategory.EXTRACTION, {})):
                result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is a failure
        assert not result.is_success
        assert isinstance(result.error, ServiceError)
        assert error_message in result.error.message
        
        # Verify that the document status is updated to ERROR
        assert sample_document.processing_status == ProcessingStatus.ERROR
    
    def test_model_result_validation(self, ocr_service_with_mocks, mock_hybrid_model, sample_document):
        """Test that model results are properly validated."""
        # Create a model result with missing critical fields
        incomplete_result = ModelResult(
            model_type=OCRModelType.HYBRID,
            extracted_fields=[
                # Missing critical fields like legal_name, tax_id
                ExtractedField(name="dba_name", value="123 Funding", confidence=0.85, page=1),
                ExtractedField(name="business_address", value="789 Pine St, Chicago, IL 60601", confidence=0.82, page=1),
            ],
            average_confidence=0.83,
            processing_time=1.75,
            metadata={"model_version": "1.0.0"}
        )
        
        # Process a sample document with the incomplete result
        with patch('src.services.ocr_service.OCRService._determine_model_type', return_value=OCRModelType.HYBRID):
            with patch('src.services.ocr_service.OCRService._extract_text', return_value=incomplete_result):
                result = ocr_service_with_mocks.process_document(sample_document)
        
        # Verify that the result is successful (validation doesn't fail the process)
        assert result.is_success
        
        # Extract the processed data from the result
        extracted_data, processing_time = result.value
        
        # Verify that the document is flagged for review due to missing critical fields
        assert extracted_data.requires_review is True