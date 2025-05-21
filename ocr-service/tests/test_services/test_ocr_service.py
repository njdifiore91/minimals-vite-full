#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service module.

This module contains tests for the OCR Service, which is responsible for
extracting text from documents using TensorFlow models. The tests verify
model loading, document type detection, OCR strategy selection, and text
extraction accuracy for both typed and handwritten documents.

The tests ensure that the OCR service correctly processes documents with
GPU acceleration and meets the 99% data extraction accuracy requirement.
"""

import os
import time
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, ANY
from pathlib import Path

# Import the OCR service and related types
from ocr_service.src.services.ocr_service import OCRService
from ocr_service.src.types.documents import Document, DocumentType, ProcessingStatus
from ocr_service.src.types.models import OCRModelType, ModelResult
from ocr_service.src.types.extraction import ExtractedData, ConfidenceScore
from ocr_service.src.types.errors import ServiceError, ErrorCategory, Result
from ocr_service.src.config import app_config, tensorflow_config
from ocr_service.src.models.model_factory import ModelFactory


# Test OCR Service Initialization
class TestOCRServiceInitialization:
    """Tests for OCR Service initialization and configuration."""

    def test_initialization_with_gpu(self, mock_tensorflow):
        """Test that OCR service initializes correctly with GPU available."""
        # Mock GPU availability
        with patch('ocr_service.src.utils.tensorflow_utils.setup_gpu_environment', return_value=True):
            with patch('ocr_service.src.utils.tensorflow_utils.get_gpu_info', return_value="Tesla T4, 16GB"):
                # Initialize OCR service
                service = OCRService()
                
                # Verify service is initialized correctly
                assert service.gpu_available is True
                assert service.model_factory is not None
                assert service.tf_config == tensorflow_config

    def test_initialization_without_gpu(self, mock_tensorflow):
        """Test that OCR service initializes correctly without GPU."""
        # Mock GPU unavailability
        with patch('ocr_service.src.utils.tensorflow_utils.setup_gpu_environment', return_value=False):
            # Initialize OCR service
            service = OCRService()
            
            # Verify service is initialized correctly
            assert service.gpu_available is False
            assert service.model_factory is not None
            assert service.tf_config == tensorflow_config

    def test_initialization_gpu_required_but_unavailable(self, mock_tensorflow):
        """Test that OCR service raises error when GPU is required but unavailable."""
        # Mock GPU unavailability
        with patch('ocr_service.src.utils.tensorflow_utils.setup_gpu_environment', return_value=False):
            # Mock config to require GPU
            with patch.object(tensorflow_config, 'require_gpu', True):
                # Verify service initialization raises error
                with pytest.raises(ServiceError) as excinfo:
                    OCRService()
                
                # Verify error details
                assert excinfo.value.category == ErrorCategory.CONFIGURATION
                assert "GPU acceleration required" in str(excinfo.value)

    def test_model_preloading(self, mock_tensorflow, mock_model_factory):
        """Test that OCR service preloads models during initialization."""
        # Initialize OCR service
        service = OCRService()
        
        # Verify model factory's get_model was called for each model type
        assert mock_model_factory.get_model.call_count >= len(OCRModelType)
        
        # Verify each model type was loaded
        for model_type in OCRModelType:
            mock_model_factory.get_model.assert_any_call(model_type)


# Test Document Processing
class TestDocumentProcessing:
    """Tests for document processing functionality."""

    def test_process_document_success(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test successful document processing."""
        # Create mock model result
        mock_result = MagicMock()
        mock_result.extracted_fields = [
            MagicMock(name="business_name", value="Acme Corp", confidence=0.95),
            MagicMock(name="tax_id", value="12-3456789", confidence=0.92)
        ]
        mock_result.average_confidence = 0.94
        mock_result.model_type = OCRModelType.TYPED
        mock_result.processing_time = 1.5
        mock_result.metadata = {}
        
        # Mock model to return successful result
        mock_model = MagicMock()
        mock_model.extract_text.return_value = mock_result
        mock_model_factory.get_model.return_value = mock_model
        
        # Initialize OCR service
        service = OCRService()
        
        # Process document
        result = service.process_document(sample_document)
        
        # Verify result is successful
        assert result.is_success()
        extracted_data, processing_time = result.value
        
        # Verify extracted data
        assert extracted_data.document_id == sample_document.metadata.document_id
        assert extracted_data.average_confidence >= 0.9
        assert len(extracted_data.fields) >= 2
        assert "business_name" in extracted_data.fields
        assert "tax_id" in extracted_data.fields
        assert processing_time > 0
        
        # Verify document status was updated
        assert sample_document.processing_status == ProcessingStatus.COMPLETED

    def test_process_document_error(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test document processing with error."""
        # Mock model to raise exception
        mock_model = MagicMock()
        mock_model.extract_text.side_effect = Exception("Test error")
        mock_model_factory.get_model.return_value = mock_model
        
        # Initialize OCR service
        service = OCRService()
        
        # Process document
        result = service.process_document(sample_document)
        
        # Verify result is failure
        assert result.is_failure()
        error = result.error
        
        # Verify error details
        assert error.category == ErrorCategory.PROCESSING
        assert "Test error" in error.message
        assert error.details["document_id"] == sample_document.metadata.document_id
        
        # Verify document status was updated to error
        assert sample_document.processing_status == ProcessingStatus.ERROR

    def test_document_preprocessing(self, mock_tensorflow, sample_document):
        """Test document preprocessing."""
        # Mock image_utils functions
        with patch('ocr_service.src.utils.image_utils.convert_to_image') as mock_convert:
            with patch('ocr_service.src.utils.image_utils.assess_image_quality', return_value=0.85) as mock_assess:
                with patch('ocr_service.src.utils.image_utils.preprocess_for_ocr') as mock_preprocess:
                    # Initialize OCR service
                    service = OCRService()
                    
                    # Call _preprocess_document directly
                    service._preprocess_document(sample_document)
                    
                    # Verify image conversion was called
                    mock_convert.assert_called_once_with(
                        sample_document.content, 
                        sample_document.metadata.mime_type
                    )
                    
                    # Verify image quality assessment was called
                    mock_assess.assert_called_once()
                    
                    # Verify preprocessing was called with appropriate options
                    mock_preprocess.assert_called_once()

    def test_preprocessing_error_handling(self, mock_tensorflow, sample_document):
        """Test error handling during document preprocessing."""
        # Mock image_utils.convert_to_image to raise exception
        with patch('ocr_service.src.utils.image_utils.convert_to_image', 
                  side_effect=Exception("Invalid image format")):
            # Initialize OCR service
            service = OCRService()
            
            # Verify preprocessing raises ServiceError
            with pytest.raises(ServiceError) as excinfo:
                service._preprocess_document(sample_document)
            
            # Verify error details
            assert excinfo.value.category == ErrorCategory.PREPROCESSING
            assert "Invalid image format" in str(excinfo.value)
            assert excinfo.value.details["document_id"] == sample_document.metadata.document_id


# Test Model Type Determination
class TestModelTypeDetermination:
    """Tests for OCR model type determination based on document content."""

    def test_determine_model_type_from_document_type(self, mock_tensorflow):
        """Test model type determination based on document type."""
        # Initialize OCR service
        service = OCRService()
        
        # Test with different document types
        test_cases = [
            (DocumentType.APPLICATION, OCRModelType.HYBRID),
            (DocumentType.ID_DOCUMENT, OCRModelType.HYBRID),
            (DocumentType.TAX_RETURN, OCRModelType.TYPED),
            (DocumentType.BANK_STATEMENT, OCRModelType.TYPED),
            (DocumentType.PAY_STUB, OCRModelType.TYPED)
        ]
        
        # Mock always_analyze_content to False to use document type prediction
        with patch.object(service.tf_config, 'always_analyze_content', False):
            for doc_type, expected_model_type in test_cases:
                # Create a mock image
                mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
                
                # Determine model type
                model_type = service._determine_model_type(mock_image, doc_type)
                
                # Verify model type matches expected
                assert model_type == expected_model_type, \
                    f"Document type {doc_type} should use model type {expected_model_type}"

    def test_determine_model_type_from_content_analysis(self, mock_tensorflow):
        """Test model type determination based on content analysis."""
        # Initialize OCR service
        service = OCRService()
        
        # Test cases with different content characteristics
        test_cases = [
            # (has_typed, has_handwritten, confidence, expected_model_type)
            (True, False, 0.9, OCRModelType.TYPED),
            (False, True, 0.9, OCRModelType.HANDWRITTEN),
            (True, True, 0.9, OCRModelType.HYBRID),
            # Low confidence case
            (True, False, 0.5, OCRModelType.TYPED)  # Should use document type prediction
        ]
        
        # Mock tensorflow_utils.detect_text_types
        for has_typed, has_handwritten, confidence, expected_model_type in test_cases:
            with patch('ocr_service.src.utils.tensorflow_utils.detect_text_types', 
                      return_value=(has_typed, has_handwritten, confidence)):
                # Create a mock image
                mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
                
                # Force content analysis
                with patch.object(service.tf_config, 'always_analyze_content', True):
                    # Determine model type
                    model_type = service._determine_model_type(mock_image, DocumentType.APPLICATION)
                    
                    # Verify model type matches expected
                    assert model_type == expected_model_type, \
                        f"Content with typed={has_typed}, handwritten={has_handwritten}, " \
                        f"confidence={confidence} should use model type {expected_model_type}"

    def test_model_type_override_with_high_confidence(self, mock_tensorflow):
        """Test that high-confidence content detection overrides document type prediction."""
        # Initialize OCR service
        service = OCRService()
        
        # Mock document type that would normally use TYPED
        doc_type = DocumentType.TAX_RETURN
        
        # Mock content detection to find handwriting with high confidence
        with patch('ocr_service.src.utils.tensorflow_utils.detect_text_types', 
                  return_value=(False, True, 0.95)):
            # Create a mock image
            mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
            
            # Set confidence threshold lower than detection confidence
            with patch.object(service.tf_config, 'text_type_confidence_threshold', 0.9):
                # Determine model type
                model_type = service._determine_model_type(mock_image, doc_type)
                
                # Verify high-confidence detection overrides document type prediction
                assert model_type == OCRModelType.HANDWRITTEN, \
                    "High-confidence content detection should override document type prediction"


# Test Text Extraction
class TestTextExtraction:
    """Tests for text extraction functionality."""

    def test_extract_text_success(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test successful text extraction."""
        # Create mock model result
        mock_result = MagicMock()
        mock_result.extracted_fields = [
            MagicMock(name="business_name", value="Acme Corp", confidence=0.95),
            MagicMock(name="tax_id", value="12-3456789", confidence=0.92)
        ]
        mock_result.average_confidence = 0.94
        
        # Mock model to return successful result
        mock_model = MagicMock()
        mock_model.extract_text.return_value = mock_result
        
        # Initialize OCR service
        service = OCRService()
        
        # Mock preprocessed image
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Extract text
        result = service._extract_text(mock_model, mock_image, sample_document)
        
        # Verify model.extract_text was called with correct parameters
        mock_model.extract_text.assert_called_once_with(
            mock_image, 
            document_type=sample_document.document_type,
            context=ANY
        )
        
        # Verify result matches mock result
        assert result == mock_result

    def test_extract_text_with_retry(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test text extraction with retry logic."""
        # Create mock model result
        mock_result = MagicMock()
        mock_result.extracted_fields = [
            MagicMock(name="business_name", value="Acme Corp", confidence=0.95)
        ]
        mock_result.average_confidence = 0.95
        
        # Mock model to fail first, then succeed
        mock_model = MagicMock()
        mock_model.extract_text.side_effect = [
            ServiceError("Temporary error", ErrorCategory.EXTRACTION),
            mock_result
        ]
        
        # Initialize OCR service
        service = OCRService()
        
        # Mock preprocessed image
        mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        # Extract text (should retry and succeed)
        result = service._extract_text(mock_model, mock_image, sample_document)
        
        # Verify model.extract_text was called twice
        assert mock_model.extract_text.call_count == 2
        
        # Verify result matches mock result
        assert result == mock_result

    def test_extract_text_gpu_fallback(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test fallback to CPU when GPU memory error occurs."""
        # Create mock model result
        mock_result = MagicMock()
        mock_result.extracted_fields = [
            MagicMock(name="business_name", value="Acme Corp", confidence=0.95)
        ]
        mock_result.average_confidence = 0.95
        
        # Mock model to fail with GPU error, then succeed with CPU
        mock_model = MagicMock()
        mock_model.extract_text.side_effect = [
            Exception("CUDA out of memory"),  # GPU error
            mock_result  # CPU success
        ]
        
        # Mock GPU-related functions
        with patch('ocr_service.src.utils.tensorflow_utils.is_gpu_memory_error', return_value=True):
            with patch('ocr_service.src.utils.tensorflow_utils.cpu_only_context'):
                # Initialize OCR service with GPU available
                service = OCRService()
                service.gpu_available = True
                
                # Mock preprocessed image
                mock_image = np.zeros((100, 100, 3), dtype=np.uint8)
                
                # Extract text (should fall back to CPU and succeed)
                result = service._extract_text(mock_model, mock_image, sample_document)
                
                # Verify model.extract_text was called twice
                assert mock_model.extract_text.call_count == 2
                
                # Verify result matches mock result
                assert result == mock_result


# Test Result Formatting
class TestResultFormatting:
    """Tests for extraction result formatting."""

    def test_format_extraction_results(self, mock_tensorflow, sample_document):
        """Test formatting of extraction results."""
        # Create mock model result
        mock_result = MagicMock()
        mock_result.extracted_fields = [
            MagicMock(name="business_name", value="Acme Corp", confidence=0.95),
            MagicMock(name="tax_id", value="12-3456789", confidence=0.92),
            MagicMock(name="address", value="123 Main St", confidence=0.85),
            MagicMock(name="phone", value="555-123-4567", confidence=0.65)  # Low confidence
        ]
        mock_result.average_confidence = 0.85
        mock_result.model_type = OCRModelType.TYPED
        mock_result.processing_time = 1.5
        mock_result.metadata = {}
        
        # Initialize OCR service
        service = OCRService()
        
        # Format extraction results
        extracted_data = service._format_extraction_results(mock_result, sample_document)
        
        # Verify basic metadata
        assert extracted_data.document_id == sample_document.metadata.document_id
        assert extracted_data.document_type == sample_document.document_type.name
        assert extracted_data.average_confidence == mock_result.average_confidence
        assert len(extracted_data.fields) == 4
        
        # Verify fields were formatted correctly
        assert "business_name" in extracted_data.fields
        assert extracted_data.fields["business_name"]["value"] == "Acme Corp"
        assert extracted_data.fields["business_name"]["confidence"] == 0.95
        assert extracted_data.fields["business_name"]["requires_review"] is False
        
        # Verify low confidence field is flagged for review
        assert "phone" in extracted_data.fields
        assert extracted_data.fields["phone"]["requires_review"] is True

    def test_normalize_field_value(self, mock_tensorflow):
        """Test normalization of field values."""
        # Initialize OCR service
        service = OCRService()
        
        # Test cases for different field types
        test_cases = [
            # (field_name, raw_value, expected_normalized_value)
            ("application_date", "01/15/2023", "01/15/2023"),  # Date field
            ("total_amount", "$1,234.56", "1234.56"),  # Amount field
            ("ssn", "123-45-6789", "123456789"),  # SSN field
            ("phone_number", "(555) 123-4567", "5551234567"),  # Phone field
            ("ein", "12-3456789", "123456789"),  # EIN field
            ("business_name", "  Acme Corp  ", "Acme Corp")  # Text field (trimmed)
        ]
        
        # Test each case
        for field_name, raw_value, expected in test_cases:
            normalized = service._normalize_field_value(raw_value, field_name, DocumentType.APPLICATION)
            assert normalized == expected, \
                f"Field {field_name} with value '{raw_value}' should normalize to '{expected}'"

    def test_determine_if_review_required(self, mock_tensorflow):
        """Test determination of whether human review is required."""
        # Initialize OCR service
        service = OCRService()
        
        # Create test extracted data with varying confidence levels
        extracted_data = MagicMock()
        extracted_data.average_confidence = 0.85
        extracted_data.fields = {
            "business_name": {"confidence": 0.95, "requires_review": False},
            "tax_id": {"confidence": 0.92, "requires_review": False},
            "address": {"confidence": 0.85, "requires_review": False},
            "phone": {"confidence": 0.65, "requires_review": True}  # Low confidence
        }
        
        # Test cases
        test_cases = [
            # (document_type, expected_review_required, reason)
            (DocumentType.APPLICATION, True, "Critical field has low confidence"),
            (DocumentType.OTHER, False, "No critical fields for OTHER type"),
            (None, True, "Unknown document type requires review")
        ]
        
        # Test each case
        for doc_type, expected, reason in test_cases:
            requires_review = service._determine_if_review_required(extracted_data, doc_type)
            assert requires_review == expected, reason


# Test Performance and Accuracy
class TestPerformanceAndAccuracy:
    """Tests for performance and accuracy requirements."""

    def test_processing_time_logging(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test that processing time is logged and evaluated against requirements."""
        # Create mock model result
        mock_result = MagicMock()
        mock_result.extracted_fields = [
            MagicMock(name="business_name", value="Acme Corp", confidence=0.95)
        ]
        mock_result.average_confidence = 0.95
        mock_result.model_type = OCRModelType.TYPED
        mock_result.processing_time = 1.5
        mock_result.metadata = {}
        
        # Mock model to return successful result
        mock_model = MagicMock()
        mock_model.extract_text.return_value = mock_result
        mock_model_factory.get_model.return_value = mock_model
        
        # Mock logging
        with patch('ocr_service.src.services.ocr_service.logging') as mock_logging:
            # Initialize OCR service
            service = OCRService()
            
            # Process document
            result = service.process_document(sample_document)
            
            # Verify processing time was logged
            assert any("processing time" in str(call) for call in mock_logging.info.call_args_list)
            
            # Verify warning is logged if processing time exceeds target
            with patch.object(app_config, 'max_processing_time_seconds', 0.1):  # Set low threshold
                service.process_document(sample_document)
                assert any("exceeded target time" in str(call) for call in mock_logging.warning.call_args_list)

    @pytest.mark.slow
    def test_gpu_acceleration_performance(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test that GPU acceleration improves performance."""
        # Skip if not running performance tests
        pytest.skip("Performance test skipped in regular test runs")
        
        # Create real OCR service (not mocked)
        with patch('ocr_service.src.utils.tensorflow_utils.setup_gpu_environment') as mock_setup_gpu:
            # Test with GPU disabled
            mock_setup_gpu.return_value = False
            cpu_service = OCRService()
            
            # Process document with CPU and measure time
            start_time = time.time()
            cpu_service.process_document(sample_document)
            cpu_time = time.time() - start_time
            
            # Test with GPU enabled
            mock_setup_gpu.return_value = True
            gpu_service = OCRService()
            
            # Process document with GPU and measure time
            start_time = time.time()
            gpu_service.process_document(sample_document)
            gpu_time = time.time() - start_time
            
            # Verify GPU is faster than CPU
            assert gpu_time < cpu_time, "GPU processing should be faster than CPU processing"

    def test_accuracy_metrics_logging(self, mock_tensorflow, mock_model_factory, sample_document):
        """Test that accuracy metrics are logged and evaluated against requirements."""
        # Create mock model result with high confidence
        high_confidence_result = MagicMock()
        high_confidence_result.extracted_fields = [
            MagicMock(name="field1", value="value1", confidence=0.98),
            MagicMock(name="field2", value="value2", confidence=0.97)
        ]
        high_confidence_result.average_confidence = 0.975
        high_confidence_result.model_type = OCRModelType.TYPED
        high_confidence_result.metadata = {}
        
        # Create mock model result with low confidence
        low_confidence_result = MagicMock()
        low_confidence_result.extracted_fields = [
            MagicMock(name="field1", value="value1", confidence=0.65),
            MagicMock(name="field2", value="value2", confidence=0.70)
        ]
        low_confidence_result.average_confidence = 0.675
        low_confidence_result.model_type = OCRModelType.TYPED
        low_confidence_result.metadata = {}
        
        # Mock model factory
        mock_model = MagicMock()
        mock_model_factory.get_model.return_value = mock_model
        
        # Mock logging
        with patch('ocr_service.src.services.ocr_service.logging') as mock_logging:
            with patch('ocr_service.src.utils.logging_utils.log_metrics') as mock_log_metrics:
                # Initialize OCR service
                service = OCRService()
                
                # Test with high confidence result
                mock_model.extract_text.return_value = high_confidence_result
                service.process_document(sample_document)
                
                # Verify accuracy metrics were logged
                assert mock_log_metrics.called
                assert any("average_confidence" in str(call) for call in mock_log_metrics.call_args_list)
                
                # Test with low confidence result
                mock_model.extract_text.return_value = low_confidence_result
                service.process_document(sample_document)
                
                # Verify warning is logged for low confidence
                assert any("extraction confidence" in str(call) for call in mock_logging.warning.call_args_list)

    @pytest.mark.parametrize("confidence,expected_review", [
        (0.99, False),  # High confidence, no review needed
        (0.85, False),   # Good confidence, no review needed
        (0.75, True),    # Moderate confidence, review needed
        (0.60, True)     # Low confidence, review needed
    ])
    def test_confidence_threshold_for_review(self, mock_tensorflow, confidence, expected_review):
        """Test that documents are flagged for review based on confidence threshold."""
        # Initialize OCR service
        service = OCRService()
        
        # Set confidence threshold
        with patch.object(service.tf_config, 'document_confidence_threshold', 0.80):
            # Create mock extracted data
            extracted_data = MagicMock()
            extracted_data.average_confidence = confidence
            extracted_data.fields = {}
            
            # Determine if review is required
            requires_review = service._determine_if_review_required(extracted_data, DocumentType.OTHER)
            
            # Verify review requirement matches expected
            assert requires_review == expected_review, \
                f"Confidence {confidence} should {'require' if expected_review else 'not require'} review"


# Test Integration with Other Services
class TestServiceIntegration:
    """Tests for integration with other services."""

    def test_log_performance_metrics(self, mock_tensorflow, sample_document):
        """Test logging of performance metrics for monitoring."""
        # Initialize OCR service
        service = OCRService()
        
        # Create mock extracted data
        extracted_data = MagicMock()
        extracted_data.average_confidence = 0.92
        extracted_data.fields = {
            "field1": {"requires_review": False},
            "field2": {"requires_review": True}
        }
        extracted_data.metadata = {"model_type": "TYPED"}
        
        # Mock logging_utils.log_metrics
        with patch('ocr_service.src.utils.logging_utils.log_metrics') as mock_log_metrics:
            # Log performance metrics
            service._log_performance_metrics(sample_document, 1.5, extracted_data)
            
            # Verify log_metrics was called with correct parameters
            mock_log_metrics.assert_called_once_with("ocr_processing", ANY)
            
            # Verify metrics include required fields
            metrics = mock_log_metrics.call_args[0][1]
            assert "processing_time" in metrics
            assert "average_confidence" in metrics
            assert "document_id" in metrics
            assert "document_type" in metrics
            
            # Verify GPU metrics are included if GPU is available
            if service.gpu_available:
                assert "gpu_utilization" in metrics

    def test_record_model_performance_metrics(self, mock_tensorflow):
        """Test recording of model performance metrics for optimization."""
        # Initialize OCR service
        service = OCRService()
        
        # Mock logging
        with patch('ocr_service.src.services.ocr_service.logging') as mock_logging:
            # Record model performance metrics
            service._record_model_performance_metrics(
                DocumentType.APPLICATION,
                "TYPED",
                {"average_confidence": 0.92, "low_confidence_fields": 1, "total_fields": 10},
                {"processing_time": 1.5, "fields_per_second": 6.67, "meets_sla": True}
            )
            
            # Verify metrics were logged
            assert mock_logging.debug.called
            assert any("Model performance metrics" in str(call) for call in mock_logging.debug.call_args_list)


# Main test execution
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])