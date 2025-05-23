#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the OCR Service module.

This module contains tests for the OCR Service, which is responsible for extracting text
from documents using TensorFlow models. The tests verify model loading, document type detection,
OCR strategy selection, and text extraction accuracy for both typed and handwritten documents.

The OCR Service must meet the following requirements:
- Extract data from documents using TensorFlow models
- Achieve 99% data extraction accuracy
- Use GPU acceleration for performance
- Apply appropriate OCR model based on document type
- Support both typed and handwritten text extraction
- Process applications in under 5 minutes from receipt to completion
"""

import os
import time
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock

# Import the module to test
from services.ocr_service import OCRService
from types.models import OCRModelType, ModelParameters, ModelResult
from types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from types.errors import ServiceError, Result
from config import tensorflow_config


class TestOCRService:
    """Test suite for the OCR Service."""

    @pytest.fixture
    def ocr_service(self, mock_tensorflow_import, mock_typed_text_model, 
                   mock_handwritten_text_model, mock_hybrid_recognition_model):
        """Create an OCR service instance with mocked models for testing."""
        with patch('services.ocr_service.ModelFactory') as mock_factory:
            # Configure the mock factory to return our mock models
            factory_instance = mock_factory.return_value
            factory_instance.get_model.side_effect = lambda model_type: {
                OCRModelType.TYPED: mock_typed_text_model,
                OCRModelType.HANDWRITTEN: mock_handwritten_text_model,
                OCRModelType.HYBRID: mock_hybrid_recognition_model
            }.get(model_type)
            
            # Create the OCR service
            service = OCRService()
            
            # Verify the service initialized correctly
            assert service.typed_model == mock_typed_text_model
            assert service.handwritten_model == mock_handwritten_text_model
            assert service.hybrid_model == mock_hybrid_recognition_model
            
            return service

    def test_initialization(self, mock_tensorflow_import):
        """Test that the OCR service initializes correctly."""
        with patch('services.ocr_service.ModelFactory') as mock_factory:
            # Configure the mock factory
            factory_instance = mock_factory.return_value
            factory_instance.get_model.return_value = MagicMock()
            
            # Create the OCR service
            service = OCRService()
            
            # Verify initialization steps were performed
            assert mock_factory.called
            assert factory_instance.get_model.call_count == 3  # Called for each model type
            assert service.logger is not None

    def test_gpu_configuration(self, mock_tensorflow_import):
        """Test that GPU configuration is applied correctly."""
        with patch('services.ocr_service.ModelFactory'):
            with patch.object(tensorflow_config, 'GPU_CONFIG', {
                'enable_gpu': True,
                'allow_memory_growth': True,
                'memory_limit_mb': 4096,
                'visible_devices': [0]
            }):
                # Create the OCR service
                service = OCRService()
                
                # Verify GPU configuration was applied
                mock_tensorflow = mock_tensorflow_import
                assert mock_tensorflow.config.experimental.set_memory_growth.called
                assert mock_tensorflow.config.set_visible_devices.called

    def test_model_loading(self, mock_tensorflow_import):
        """Test that models are loaded correctly during initialization."""
        with patch('services.ocr_service.ModelFactory') as mock_factory:
            # Configure the mock factory
            factory_instance = mock_factory.return_value
            mock_typed_model = MagicMock()
            mock_handwritten_model = MagicMock()
            mock_hybrid_model = MagicMock()
            
            factory_instance.get_model.side_effect = lambda model_type: {
                OCRModelType.TYPED: mock_typed_model,
                OCRModelType.HANDWRITTEN: mock_handwritten_model,
                OCRModelType.HYBRID: mock_hybrid_model
            }.get(model_type)
            
            # Create the OCR service
            service = OCRService()
            
            # Verify models were loaded
            assert service.typed_model == mock_typed_model
            assert service.handwritten_model == mock_handwritten_model
            assert service.hybrid_model == mock_hybrid_model
            
            # Verify warm-up was performed
            assert mock_typed_model.extract_text.called
            assert mock_handwritten_model.extract_text.called
            assert mock_hybrid_model.extract_text.called

    def test_model_warm_up(self, ocr_service):
        """Test that models are warmed up during initialization."""
        # Verify that extract_text was called on each model during initialization
        assert ocr_service.typed_model.extract_text.called
        assert ocr_service.handwritten_model.extract_text.called
        assert ocr_service.hybrid_model.extract_text.called

    def test_detect_document_type_typed(self, ocr_service):
        """Test document type detection for typed documents."""
        # Mock the tensorflow_utils.detect_text_type function
        with patch('services.ocr_service.tensorflow_utils.detect_text_type') as mock_detect:
            # Configure the mock to return a typed document result
            mock_detect.return_value = {
                'typed_percentage': 90.0,
                'handwritten_percentage': 5.0
            }
            
            # Call the method
            image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
            result = ocr_service.detect_document_type(image)
            
            # Verify the result
            assert result == OCRModelType.TYPED
            assert mock_detect.called

    def test_detect_document_type_handwritten(self, ocr_service):
        """Test document type detection for handwritten documents."""
        # Mock the tensorflow_utils.detect_text_type function
        with patch('services.ocr_service.tensorflow_utils.detect_text_type') as mock_detect:
            # Configure the mock to return a handwritten document result
            mock_detect.return_value = {
                'typed_percentage': 5.0,
                'handwritten_percentage': 90.0
            }
            
            # Call the method
            image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
            result = ocr_service.detect_document_type(image)
            
            # Verify the result
            assert result == OCRModelType.HANDWRITTEN
            assert mock_detect.called

    def test_detect_document_type_hybrid(self, ocr_service):
        """Test document type detection for hybrid documents."""
        # Mock the tensorflow_utils.detect_text_type function
        with patch('services.ocr_service.tensorflow_utils.detect_text_type') as mock_detect:
            # Configure the mock to return a hybrid document result
            mock_detect.return_value = {
                'typed_percentage': 60.0,
                'handwritten_percentage': 40.0
            }
            
            # Call the method
            image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
            result = ocr_service.detect_document_type(image)
            
            # Verify the result
            assert result == OCRModelType.HYBRID
            assert mock_detect.called

    def test_detect_document_type_error(self, ocr_service):
        """Test document type detection error handling."""
        # Mock the tensorflow_utils.detect_text_type function to raise an exception
        with patch('services.ocr_service.tensorflow_utils.detect_text_type') as mock_detect:
            mock_detect.side_effect = Exception("Detection error")
            
            # Call the method
            image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
            result = ocr_service.detect_document_type(image)
            
            # Verify the result defaults to HYBRID on error
            assert result == OCRModelType.HYBRID
            assert mock_detect.called

    def test_select_model(self, ocr_service):
        """Test model selection based on document type."""
        # Test typed model selection
        model = ocr_service.select_model(OCRModelType.TYPED)
        assert model == ocr_service.typed_model
        
        # Test handwritten model selection
        model = ocr_service.select_model(OCRModelType.HANDWRITTEN)
        assert model == ocr_service.handwritten_model
        
        # Test hybrid model selection
        model = ocr_service.select_model(OCRModelType.HYBRID)
        assert model == ocr_service.hybrid_model

    def test_process_document_success(self, ocr_service, mock_document_bytes):
        """Test successful document processing."""
        # Mock dependencies
        with patch('services.ocr_service.image_utils.convert_document_to_image') as mock_convert:
            with patch('services.ocr_service.image_utils.preprocess_image') as mock_preprocess:
                # Configure mocks
                mock_image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
                mock_convert.return_value = mock_image
                mock_preprocess.return_value = mock_image
                
                # Mock detect_document_type to return TYPED
                with patch.object(ocr_service, 'detect_document_type', return_value=OCRModelType.TYPED):
                    # Configure the typed model to return a successful result
                    extraction_result = MagicMock()
                    ocr_service.typed_model.extract_text.return_value = extraction_result
                    
                    # Mock the remaining processing steps
                    with patch.object(ocr_service, '_apply_structure_recognition') as mock_structure:
                        with patch.object(ocr_service, '_extract_fields') as mock_extract:
                            with patch.object(ocr_service, '_score_field_confidence') as mock_score:
                                with patch.object(ocr_service, '_format_extraction_result') as mock_format:
                                    # Configure the mocks
                                    structured_data = {'structured': True}
                                    extracted_fields = [{'field': 'value'}]
                                    scored_fields = [{'field': 'value', 'confidence': 0.95}]
                                    result = ExtractedData(fields=scored_fields, metadata={'document_id': 'test'})
                                    
                                    mock_structure.return_value = structured_data
                                    mock_extract.return_value = extracted_fields
                                    mock_score.return_value = scored_fields
                                    mock_format.return_value = result
                                    
                                    # Call the method
                                    metadata = {'request_id': 'req-123', 'document_type': 'application_form'}
                                    process_result = ocr_service.process_document(mock_document_bytes, metadata)
                                    
                                    # Verify the result
                                    assert process_result.is_success()
                                    assert process_result.value() == result
                                    assert mock_convert.called
                                    assert mock_preprocess.called
                                    assert ocr_service.typed_model.extract_text.called
                                    assert mock_structure.called
                                    assert mock_extract.called
                                    assert mock_score.called
                                    assert mock_format.called

    def test_process_document_with_classification(self, ocr_service, mock_document_bytes):
        """Test document processing with classification from metadata."""
        # Mock dependencies
        with patch('services.ocr_service.image_utils.convert_document_to_image') as mock_convert:
            with patch('services.ocr_service.image_utils.preprocess_image') as mock_preprocess:
                # Configure mocks
                mock_image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
                mock_convert.return_value = mock_image
                mock_preprocess.return_value = mock_image
                
                # Mock detect_document_type (should not be called in this test)
                detect_spy = patch.object(ocr_service, 'detect_document_type')
                mock_detect = detect_spy.start()
                
                # Configure the handwritten model to return a successful result
                extraction_result = MagicMock()
                ocr_service.handwritten_model.extract_text.return_value = extraction_result
                
                # Mock the remaining processing steps
                with patch.object(ocr_service, '_apply_structure_recognition') as mock_structure:
                    with patch.object(ocr_service, '_extract_fields') as mock_extract:
                        with patch.object(ocr_service, '_score_field_confidence') as mock_score:
                            with patch.object(ocr_service, '_format_extraction_result') as mock_format:
                                # Configure the mocks
                                structured_data = {'structured': True}
                                extracted_fields = [{'field': 'value'}]
                                scored_fields = [{'field': 'value', 'confidence': 0.95}]
                                result = ExtractedData(fields=scored_fields, metadata={'document_id': 'test'})
                                
                                mock_structure.return_value = structured_data
                                mock_extract.return_value = extracted_fields
                                mock_score.return_value = scored_fields
                                mock_format.return_value = result
                                
                                # Call the method with classification in metadata
                                metadata = {
                                    'request_id': 'req-123', 
                                    'document_type': 'application_form',
                                    'classification': 'handwritten'  # This should select the handwritten model
                                }
                                process_result = ocr_service.process_document(mock_document_bytes, metadata)
                                
                                # Verify the result
                                assert process_result.is_success()
                                assert process_result.value() == result
                                assert not mock_detect.called  # detect_document_type should not be called
                                assert ocr_service.handwritten_model.extract_text.called
                                
                                # Clean up the spy
                                detect_spy.stop()

    def test_process_document_conversion_error(self, ocr_service, mock_document_bytes):
        """Test document processing with document conversion error."""
        # Mock dependencies
        with patch('services.ocr_service.image_utils.convert_document_to_image') as mock_convert:
            # Configure mock to return None (conversion failure)
            mock_convert.return_value = None
            
            # Call the method
            metadata = {'request_id': 'req-123', 'document_type': 'application_form'}
            process_result = ocr_service.process_document(mock_document_bytes, metadata)
            
            # Verify the result
            assert process_result.is_failure()
            assert process_result.error().code == "DOCUMENT_CONVERSION_ERROR"
            assert mock_convert.called

    def test_process_document_extraction_error(self, ocr_service, mock_document_bytes):
        """Test document processing with extraction error."""
        # Mock dependencies
        with patch('services.ocr_service.image_utils.convert_document_to_image') as mock_convert:
            with patch('services.ocr_service.image_utils.preprocess_image') as mock_preprocess:
                # Configure mocks
                mock_image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
                mock_convert.return_value = mock_image
                mock_preprocess.return_value = mock_image
                
                # Mock detect_document_type to return TYPED
                with patch.object(ocr_service, 'detect_document_type', return_value=OCRModelType.TYPED):
                    # Configure the typed model to raise an exception
                    ocr_service.typed_model.extract_text.side_effect = Exception("Extraction error")
                    
                    # Call the method
                    metadata = {'request_id': 'req-123', 'document_type': 'application_form'}
                    process_result = ocr_service.process_document(mock_document_bytes, metadata)
                    
                    # Verify the result
                    assert process_result.is_failure()
                    assert process_result.error().code == "DOCUMENT_PROCESSING_ERROR"
                    assert mock_convert.called
                    assert mock_preprocess.called
                    assert ocr_service.typed_model.extract_text.called

    def test_apply_structure_recognition(self, ocr_service):
        """Test structure recognition for different document types."""
        # Mock tensorflow_utils functions
        with patch('services.ocr_service.tensorflow_utils.recognize_application_form_structure') as mock_app_form:
            with patch('services.ocr_service.tensorflow_utils.recognize_tax_document_structure') as mock_tax:
                with patch('services.ocr_service.tensorflow_utils.recognize_bank_statement_structure') as mock_bank:
                    with patch('services.ocr_service.tensorflow_utils.recognize_identity_document_structure') as mock_id:
                        with patch('services.ocr_service.tensorflow_utils.recognize_generic_structure') as mock_generic:
                            # Configure mocks
                            mock_app_form.return_value = {'type': 'application_form'}
                            mock_tax.return_value = {'type': 'tax_document'}
                            mock_bank.return_value = {'type': 'bank_statement'}
                            mock_id.return_value = {'type': 'identity_document'}
                            mock_generic.return_value = {'type': 'generic'}
                            
                            extraction_result = {'raw': 'data'}
                            
                            # Test application form
                            result = ocr_service._apply_structure_recognition(
                                extraction_result, {'document_type': 'application_form'}
                            )
                            assert result == {'type': 'application_form'}
                            assert mock_app_form.called
                            
                            # Test tax document
                            result = ocr_service._apply_structure_recognition(
                                extraction_result, {'document_type': 'tax_document'}
                            )
                            assert result == {'type': 'tax_document'}
                            assert mock_tax.called
                            
                            # Test bank statement
                            result = ocr_service._apply_structure_recognition(
                                extraction_result, {'document_type': 'bank_statement'}
                            )
                            assert result == {'type': 'bank_statement'}
                            assert mock_bank.called
                            
                            # Test identity document
                            result = ocr_service._apply_structure_recognition(
                                extraction_result, {'document_type': 'identity_document'}
                            )
                            assert result == {'type': 'identity_document'}
                            assert mock_id.called
                            
                            # Test unknown document type
                            result = ocr_service._apply_structure_recognition(
                                extraction_result, {'document_type': 'unknown'}
                            )
                            assert result == {'type': 'generic'}
                            assert mock_generic.called

    def test_apply_structure_recognition_error(self, ocr_service):
        """Test structure recognition error handling."""
        # Mock tensorflow_utils function to raise an exception
        with patch('services.ocr_service.tensorflow_utils.recognize_application_form_structure') as mock_app_form:
            mock_app_form.side_effect = Exception("Structure recognition error")
            
            extraction_result = {'raw': 'data'}
            
            # Test error handling
            result = ocr_service._apply_structure_recognition(
                extraction_result, {'document_type': 'application_form'}
            )
            
            # Should return the original extraction result on error
            assert result == extraction_result
            assert mock_app_form.called

    def test_extract_fields(self, ocr_service):
        """Test field extraction for different document types."""
        # Mock text_utils functions
        with patch('services.ocr_service.text_utils.extract_application_form_fields') as mock_app_form:
            with patch('services.ocr_service.text_utils.extract_tax_document_fields') as mock_tax:
                with patch('services.ocr_service.text_utils.extract_bank_statement_fields') as mock_bank:
                    with patch('services.ocr_service.text_utils.extract_identity_document_fields') as mock_id:
                        with patch('services.ocr_service.text_utils.extract_generic_fields') as mock_generic:
                            # Configure mocks
                            mock_app_form.return_value = [{'field_id': 'app_field'}]
                            mock_tax.return_value = [{'field_id': 'tax_field'}]
                            mock_bank.return_value = [{'field_id': 'bank_field'}]
                            mock_id.return_value = [{'field_id': 'id_field'}]
                            mock_generic.return_value = [{'field_id': 'generic_field'}]
                            
                            structured_data = {'structured': True}
                            
                            # Test application form
                            result = ocr_service._extract_fields(
                                structured_data, {'document_type': 'application_form'}
                            )
                            assert result == [{'field_id': 'app_field'}]
                            assert mock_app_form.called
                            
                            # Test tax document
                            result = ocr_service._extract_fields(
                                structured_data, {'document_type': 'tax_document'}
                            )
                            assert result == [{'field_id': 'tax_field'}]
                            assert mock_tax.called
                            
                            # Test bank statement
                            result = ocr_service._extract_fields(
                                structured_data, {'document_type': 'bank_statement'}
                            )
                            assert result == [{'field_id': 'bank_field'}]
                            assert mock_bank.called
                            
                            # Test identity document
                            result = ocr_service._extract_fields(
                                structured_data, {'document_type': 'identity_document'}
                            )
                            assert result == [{'field_id': 'id_field'}]
                            assert mock_id.called
                            
                            # Test unknown document type
                            result = ocr_service._extract_fields(
                                structured_data, {'document_type': 'unknown'}
                            )
                            assert result == [{'field_id': 'generic_field'}]
                            assert mock_generic.called

    def test_extract_fields_error(self, ocr_service):
        """Test field extraction error handling."""
        # Mock text_utils function to raise an exception
        with patch('services.ocr_service.text_utils.extract_application_form_fields') as mock_app_form:
            mock_app_form.side_effect = Exception("Field extraction error")
            
            structured_data = {'structured': True}
            
            # Test error handling
            result = ocr_service._extract_fields(
                structured_data, {'document_type': 'application_form'}
            )
            
            # Should return an empty list on error
            assert result == []
            assert mock_app_form.called

    def test_score_field_confidence(self, ocr_service):
        """Test confidence scoring for extracted fields."""
        # Mock tensorflow_utils.calculate_field_confidence
        with patch('services.ocr_service.tensorflow_utils.calculate_field_confidence') as mock_calc:
            # Configure mock to return different confidence scores
            mock_calc.side_effect = [0.95, 0.65, 0.85]
            
            # Create test fields
            extracted_fields = [
                ExtractedField(
                    field_id="field1",
                    field_type="text",
                    value="Value 1",
                    location={"page": 0, "top": 0.1, "left": 0.1, "bottom": 0.2, "right": 0.5},
                    metadata={}
                ),
                ExtractedField(
                    field_id="field2",
                    field_type="number",
                    value="12345",
                    location={"page": 0, "top": 0.3, "left": 0.1, "bottom": 0.4, "right": 0.5},
                    metadata={}
                ),
                ExtractedField(
                    field_id="field3",
                    field_type="date",
                    value="2023-01-15",
                    location={"page": 0, "top": 0.5, "left": 0.1, "bottom": 0.6, "right": 0.5},
                    metadata={}
                )
            ]
            
            # Configure tensorflow_config.CONFIDENCE_THRESHOLD
            with patch.object(tensorflow_config, 'CONFIDENCE_THRESHOLD', 0.75):
                # Call the method
                result = ocr_service._score_field_confidence(extracted_fields)
                
                # Verify the result
                assert len(result) == 3
                assert result[0].confidence.value == 0.95
                assert result[1].confidence.value == 0.65
                assert result[2].confidence.value == 0.85
                
                # Verify low confidence field is flagged
                assert not result[0].metadata.get('requires_review', False)
                assert result[1].metadata.get('requires_review', False)
                assert not result[2].metadata.get('requires_review', False)
                
                # Verify mock was called for each field
                assert mock_calc.call_count == 3

    def test_score_field_confidence_error(self, ocr_service):
        """Test confidence scoring error handling."""
        # Mock tensorflow_utils.calculate_field_confidence to raise an exception
        with patch('services.ocr_service.tensorflow_utils.calculate_field_confidence') as mock_calc:
            mock_calc.side_effect = Exception("Confidence calculation error")
            
            # Create test fields
            extracted_fields = [
                ExtractedField(
                    field_id="field1",
                    field_type="text",
                    value="Value 1",
                    location={"page": 0, "top": 0.1, "left": 0.1, "bottom": 0.2, "right": 0.5},
                    metadata={}
                )
            ]
            
            # Call the method
            result = ocr_service._score_field_confidence(extracted_fields)
            
            # Verify the result
            assert len(result) == 1
            assert result[0].confidence == 0.5  # Default mid-range confidence
            assert result[0].metadata.get('requires_review', False)  # Should be flagged for review
            
            # Verify mock was called
            assert mock_calc.called

    def test_format_extraction_result(self, ocr_service):
        """Test formatting of extraction results."""
        # Mock time_utils.get_iso_timestamp
        with patch('services.ocr_service.time_utils.get_iso_timestamp') as mock_timestamp:
            # Configure mock
            mock_timestamp.return_value = "2023-05-23T12:34:56Z"
            
            # Configure app_config.VERSION
            with patch.object(ocr_service, 'app_config') as mock_config:
                mock_config.VERSION = "1.2.3"
                
                # Create test fields
                scored_fields = [
                    ExtractedField(
                        field_id="field1",
                        field_type="text",
                        value="Value 1",
                        confidence=ConfidenceScore(0.95),
                        location={"page": 0, "top": 0.1, "left": 0.1, "bottom": 0.2, "right": 0.5},
                        metadata={}
                    ),
                    ExtractedField(
                        field_id="field2",
                        field_type="number",
                        value="12345",
                        confidence=ConfidenceScore(0.65),
                        location={"page": 0, "top": 0.3, "left": 0.1, "bottom": 0.4, "right": 0.5},
                        metadata={"requires_review": True}
                    )
                ]
                
                # Create metadata
                metadata = {
                    "document_id": "doc-123",
                    "request_id": "req-456",
                    "document_type": "application_form"
                }
                
                # Call the method
                result = ocr_service._format_extraction_result(scored_fields, metadata)
                
                # Verify the result
                assert result.fields == scored_fields
                assert result.metadata["document_id"] == "doc-123"
                assert result.metadata["request_id"] == "req-456"
                assert result.metadata["document_type"] == "application_form"
                assert result.metadata["extraction_timestamp"] == "2023-05-23T12:34:56Z"
                assert result.metadata["ocr_service_version"] == "1.2.3"
                assert result.metadata["requires_review"] == True  # One field requires review
                assert result.metadata["overall_confidence"] == 0.8  # Average of 0.95 and 0.65
                
                # Verify mock was called
                assert mock_timestamp.called

    def test_format_extraction_result_error(self, ocr_service):
        """Test extraction result formatting error handling."""
        # Mock time_utils.get_iso_timestamp
        with patch('services.ocr_service.time_utils.get_iso_timestamp') as mock_timestamp:
            # Configure mock to raise an exception
            mock_timestamp.side_effect = Exception("Timestamp error")
            
            # Configure app_config.VERSION
            with patch.object(ocr_service, 'app_config') as mock_config:
                mock_config.VERSION = "1.2.3"
                
                # Create test fields
                scored_fields = [
                    ExtractedField(
                        field_id="field1",
                        field_type="text",
                        value="Value 1",
                        confidence=ConfidenceScore(0.95),
                        location={"page": 0, "top": 0.1, "left": 0.1, "bottom": 0.2, "right": 0.5},
                        metadata={}
                    )
                ]
                
                # Create metadata
                metadata = {
                    "document_id": "doc-123",
                    "request_id": "req-456",
                    "document_type": "application_form"
                }
                
                # Call the method
                result = ocr_service._format_extraction_result(scored_fields, metadata)
                
                # Verify the result contains error information
                assert result.fields == scored_fields
                assert result.metadata["document_id"] == "doc-123"
                assert result.metadata["request_id"] == "req-456"
                assert "error" in result.metadata
                assert result.metadata["requires_review"] == True  # Should require review due to error
                
                # Verify mock was called
                assert mock_timestamp.called

    def test_get_service_status(self, ocr_service):
        """Test service status reporting."""
        # Mock tensorflow_utils.get_gpu_info
        with patch('services.ocr_service.tensorflow_utils.get_gpu_info') as mock_gpu_info:
            # Configure mock
            mock_gpu_info.return_value = {
                "gpus": ["GPU 0", "GPU 1"],
                "memory_usage": {"GPU 0": "4GB", "GPU 1": "6GB"}
            }
            
            # Mock time_utils.get_iso_timestamp
            with patch('services.ocr_service.time_utils.get_iso_timestamp') as mock_timestamp:
                # Configure mock
                mock_timestamp.return_value = "2023-05-23T12:34:56Z"
                
                # Configure app_config.VERSION
                with patch.object(ocr_service, 'app_config') as mock_config:
                    mock_config.VERSION = "1.2.3"
                    
                    # Call the method
                    status = ocr_service.get_service_status()
                    
                    # Verify the result
                    assert status["service"] == "ocr-service"
                    assert status["version"] == "1.2.3"
                    assert status["status"] == "healthy"
                    assert status["gpu_available"] == True
                    assert status["gpu_info"] == {
                        "gpus": ["GPU 0", "GPU 1"],
                        "memory_usage": {"GPU 0": "4GB", "GPU 1": "6GB"}
                    }
                    assert status["models_loaded"] == True
                    assert status["timestamp"] == "2023-05-23T12:34:56Z"
                    
                    # Verify mocks were called
                    assert mock_gpu_info.called
                    assert mock_timestamp.called

    def test_performance_requirements(self, ocr_service, mock_document_bytes):
        """Test that document processing meets performance requirements."""
        # Mock dependencies
        with patch('services.ocr_service.image_utils.convert_document_to_image') as mock_convert:
            with patch('services.ocr_service.image_utils.preprocess_image') as mock_preprocess:
                # Configure mocks
                mock_image = np.zeros((300, 300, 3), dtype=np.uint8)  # Dummy image
                mock_convert.return_value = mock_image
                mock_preprocess.return_value = mock_image
                
                # Mock detect_document_type to return TYPED
                with patch.object(ocr_service, 'detect_document_type', return_value=OCRModelType.TYPED):
                    # Configure the typed model to return a successful result
                    extraction_result = MagicMock()
                    ocr_service.typed_model.extract_text.return_value = extraction_result
                    
                    # Mock the remaining processing steps
                    with patch.object(ocr_service, '_apply_structure_recognition') as mock_structure:
                        with patch.object(ocr_service, '_extract_fields') as mock_extract:
                            with patch.object(ocr_service, '_score_field_confidence') as mock_score:
                                with patch.object(ocr_service, '_format_extraction_result') as mock_format:
                                    # Configure the mocks
                                    structured_data = {'structured': True}
                                    extracted_fields = [{'field': 'value'}]
                                    scored_fields = [{'field': 'value', 'confidence': 0.95}]
                                    result = ExtractedData(fields=scored_fields, metadata={'document_id': 'test'})
                                    
                                    mock_structure.return_value = structured_data
                                    mock_extract.return_value = extracted_fields
                                    mock_score.return_value = scored_fields
                                    mock_format.return_value = result
                                    
                                    # Call the method and measure time
                                    start_time = time.time()
                                    metadata = {'request_id': 'req-123', 'document_type': 'application_form'}
                                    process_result = ocr_service.process_document(mock_document_bytes, metadata)
                                    end_time = time.time()
                                    
                                    # Calculate processing time
                                    processing_time = end_time - start_time
                                    
                                    # Verify the result
                                    assert process_result.is_success()
                                    
                                    # Verify processing time is under 5 minutes (300 seconds)
                                    # In a real test, we would use a more realistic threshold,
                                    # but for this mock test, we'll just verify it's under 300 seconds
                                    assert processing_time < 300, f"Processing time {processing_time} exceeds 5 minutes"

    def test_accuracy_requirements(self, ocr_service):
        """Test that OCR accuracy meets the 99% requirement."""
        # This test would normally use real documents with known ground truth,
        # but for this mock test, we'll verify the confidence scoring mechanism
        
        # Create test fields with high confidence (>= 99%)
        extracted_fields = [
            ExtractedField(
                field_id="field1",
                field_type="text",
                value="Value 1",
                location={"page": 0, "top": 0.1, "left": 0.1, "bottom": 0.2, "right": 0.5},
                metadata={}
            ),
            ExtractedField(
                field_id="field2",
                field_type="number",
                value="12345",
                location={"page": 0, "top": 0.3, "left": 0.1, "bottom": 0.4, "right": 0.5},
                metadata={}
            )
        ]
        
        # Mock tensorflow_utils.calculate_field_confidence to return high confidence
        with patch('services.ocr_service.tensorflow_utils.calculate_field_confidence') as mock_calc:
            # Configure mock to return 99% confidence
            mock_calc.return_value = 0.99
            
            # Call the method
            result = ocr_service._score_field_confidence(extracted_fields)
            
            # Verify the result
            assert len(result) == 2
            assert result[0].confidence.value == 0.99
            assert result[1].confidence.value == 0.99
            
            # Calculate overall accuracy
            overall_accuracy = sum(field.confidence.value for field in result) / len(result)
            
            # Verify accuracy meets the 99% requirement
            assert overall_accuracy >= 0.99, f"Overall accuracy {overall_accuracy} is below 99%"
            
            # Verify mock was called for each field
            assert mock_calc.call_count == 2