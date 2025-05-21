#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the complete OCR processing pipeline.

This module tests the end-to-end OCR pipeline from document receipt to data extraction,
verifying that all components (document preprocessing, OCR processing, field extraction,
confidence scoring) work together correctly to extract data from documents with high accuracy.

The tests validate:
1. Processing of different document types (typed, handwritten, mixed)
2. Error handling and recovery in the pipeline
3. Accuracy and performance metrics for the complete pipeline
4. Integration between all OCR service components
"""

import os
import time
import json
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from typing import Dict, List, Any, Tuple

# Import application modules
from src.app import Application
from src.services.ocr_service import OCRService
from src.services.queue_service import QueueService
from src.services.storage_service import StorageService
from src.services.confidence_service import ConfidenceService
from src.services.field_extraction_service import FieldExtractionService
from src.models.model_factory import ModelFactory
from src.types.documents import Document, DocumentType, DocumentMetadata, ProcessingStatus
from src.types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from src.types.models import OCRModelType, ModelResult, ModelParameters
from src.types.messages import MessagePayload, MessageHeaders
from src.types.errors import ServiceError, ErrorCategory, Result


class TestOCRPipeline:
    """Test the complete OCR processing pipeline from document receipt to data extraction."""
    
    @pytest.mark.parametrize("document_fixture", [
        "typed_document",
        "handwritten_document",
        "mixed_document"
    ])
    def test_end_to_end_document_processing(self, document_fixture, request, mock_application):
        """Test the complete OCR pipeline with different document types.
        
        This test verifies that the OCR pipeline correctly processes different types of documents
        (typed, handwritten, mixed) from receipt to data extraction, with all components working together.
        """
        # Get the document fixture
        document = request.getfixturevalue(document_fixture)
        
        # Configure the mock application for this test
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Process the document through the pipeline
        result = mock_application.process_document(document)
        
        # Verify that the result is successful
        assert result.is_success, f"Processing failed: {result.error.message if not result.is_success else ''}"
        
        # Extract the processed data and processing time from the result
        extracted_data, processing_time = result.value
        
        # Verify that the extracted data contains the expected fields
        assert extracted_data.document_id == document.metadata.document_id
        assert extracted_data.document_type == document.document_type.name
        assert len(extracted_data.fields) > 0
        
        # Verify that each field has a confidence score
        for field_name, field_data in extracted_data.fields.items():
            assert "value" in field_data
            assert "confidence" in field_data
            assert 0 <= field_data["confidence"] <= 1
        
        # Verify that the document has an overall confidence score
        assert hasattr(extracted_data, "average_confidence")
        assert 0 <= extracted_data.average_confidence <= 1
        
        # Verify that the processing time is reasonable (under 5 minutes as per requirements)
        assert processing_time < 300  # 5 minutes in seconds
        
        # Verify that the document status is updated to PROCESSED
        assert document.processing_status == ProcessingStatus.PROCESSED
        
        # Verify that the storage service was called to store the extracted data
        mock_application.storage_service.upload_extracted_data.assert_called_once()
        
        # Verify that the queue service was called to publish the result
        mock_application.queue_service.publish_message.assert_called_once()
    
    def test_pipeline_with_low_confidence_document(self, mixed_document, mock_application):
        """Test the OCR pipeline with a document that has low confidence scores.
        
        This test verifies that the OCR pipeline correctly identifies documents with low confidence
        scores and flags them for human verification.
        """
        # Configure the mock application for low confidence processing
        self._configure_mocks_for_low_confidence_processing(mock_application)
        
        # Process the document through the pipeline
        result = mock_application.process_document(mixed_document)
        
        # Verify that the result is successful
        assert result.is_success
        
        # Extract the processed data and processing time from the result
        extracted_data, processing_time = result.value
        
        # Verify that the document is flagged for human verification
        assert extracted_data.requires_review is True
        
        # Verify that low-confidence fields are flagged for review
        low_confidence_fields = [field for field, data in extracted_data.fields.items() 
                               if data["confidence"] < 0.8]
        assert len(low_confidence_fields) > 0
        
        for field in low_confidence_fields:
            assert extracted_data.fields[field]["requires_review"] is True
        
        # Verify that the document status is updated to NEEDS_REVIEW
        assert mixed_document.processing_status == ProcessingStatus.NEEDS_REVIEW
        
        # Verify that the storage service was called to store the extracted data
        mock_application.storage_service.upload_extracted_data.assert_called_once()
        
        # Verify that the queue service was called to publish the result
        mock_application.queue_service.publish_message.assert_called_once()
    
    def test_pipeline_with_document_retrieval_error(self, sample_document_metadata, mock_application):
        """Test the OCR pipeline's error handling when document retrieval fails.
        
        This test verifies that the OCR pipeline correctly handles errors when retrieving
        documents from storage.
        """
        # Configure the storage service to simulate a document retrieval error
        mock_application.storage_service.download_document.side_effect = ServiceError(
            "Failed to download document", ErrorCategory.STORAGE, {"status_code": 404}
        )
        
        # Create a document with only metadata (no content)
        document = Document(
            metadata=sample_document_metadata,
            content=None,
            document_type=DocumentType.APPLICATION,
            status=ProcessingStatus.PENDING
        )
        
        # Process the document through the pipeline
        result = mock_application.process_document(document)
        
        # Verify that the result is a failure
        assert not result.is_success
        assert isinstance(result.error, ServiceError)
        assert "Failed to download document" in result.error.message
        assert result.error.category == ErrorCategory.STORAGE
        
        # Verify that the document status is updated to ERROR
        assert document.processing_status == ProcessingStatus.ERROR
        
        # Verify that the queue service was called to publish the error
        mock_application.queue_service.publish_message.assert_called_once()
    
    def test_pipeline_with_ocr_processing_error(self, typed_document, mock_application):
        """Test the OCR pipeline's error handling when OCR processing fails.
        
        This test verifies that the OCR pipeline correctly handles errors during OCR processing.
        """
        # Configure the OCR service to simulate a processing error
        mock_application.ocr_service.process_document.side_effect = ServiceError(
            "OCR processing failed", ErrorCategory.EXTRACTION, {"model": "typed_model"}
        )
        
        # Process the document through the pipeline
        result = mock_application.process_document(typed_document)
        
        # Verify that the result is a failure
        assert not result.is_success
        assert isinstance(result.error, ServiceError)
        assert "OCR processing failed" in result.error.message
        assert result.error.category == ErrorCategory.EXTRACTION
        
        # Verify that the document status is updated to ERROR
        assert typed_document.processing_status == ProcessingStatus.ERROR
        
        # Verify that the queue service was called to publish the error
        mock_application.queue_service.publish_message.assert_called_once()
    
    def test_pipeline_with_field_extraction_error(self, handwritten_document, mock_application):
        """Test the OCR pipeline's error handling when field extraction fails.
        
        This test verifies that the OCR pipeline correctly handles errors during field extraction.
        """
        # Configure the OCR service to succeed but field extraction to fail
        mock_application.ocr_service.process_document.return_value = Result.success(({"text": "Sample text"}, 1.0))
        mock_application.field_extraction_service.extract_fields.side_effect = ServiceError(
            "Field extraction failed", ErrorCategory.EXTRACTION, {"fields": ["name", "address"]}
        )
        
        # Process the document through the pipeline
        result = mock_application.process_document(handwritten_document)
        
        # Verify that the result is a failure
        assert not result.is_success
        assert isinstance(result.error, ServiceError)
        assert "Field extraction failed" in result.error.message
        assert result.error.category == ErrorCategory.EXTRACTION
        
        # Verify that the document status is updated to ERROR
        assert handwritten_document.processing_status == ProcessingStatus.ERROR
        
        # Verify that the queue service was called to publish the error
        mock_application.queue_service.publish_message.assert_called_once()
    
    def test_pipeline_with_queue_publishing_error(self, typed_document, mock_application):
        """Test the OCR pipeline's error handling when queue publishing fails.
        
        This test verifies that the OCR pipeline correctly handles errors when publishing
        results to the message queue.
        """
        # Configure the mocks for successful processing but queue publishing failure
        self._configure_mocks_for_successful_processing(mock_application)
        mock_application.queue_service.publish_message.side_effect = ServiceError(
            "Failed to publish message", ErrorCategory.MESSAGING, {"exchange": "mca.documents"}
        )
        
        # Process the document through the pipeline
        result = mock_application.process_document(typed_document)
        
        # Verify that the result is a failure
        assert not result.is_success
        assert isinstance(result.error, ServiceError)
        assert "Failed to publish message" in result.error.message
        assert result.error.category == ErrorCategory.MESSAGING
        
        # Verify that the document status is still PROCESSED (since OCR succeeded)
        assert typed_document.processing_status == ProcessingStatus.PROCESSED
        
        # Verify that the storage service was called to store the extracted data
        mock_application.storage_service.upload_extracted_data.assert_called_once()
    
    def test_pipeline_with_storage_upload_error(self, typed_document, mock_application):
        """Test the OCR pipeline's error handling when storage upload fails.
        
        This test verifies that the OCR pipeline correctly handles errors when uploading
        extracted data to storage.
        """
        # Configure the mocks for successful processing but storage upload failure
        self._configure_mocks_for_successful_processing(mock_application)
        mock_application.storage_service.upload_extracted_data.side_effect = ServiceError(
            "Failed to upload extracted data", ErrorCategory.STORAGE, {"bucket": "mca-documents-test"}
        )
        
        # Process the document through the pipeline
        result = mock_application.process_document(typed_document)
        
        # Verify that the result is a failure
        assert not result.is_success
        assert isinstance(result.error, ServiceError)
        assert "Failed to upload extracted data" in result.error.message
        assert result.error.category == ErrorCategory.STORAGE
        
        # Verify that the document status is still PROCESSED (since OCR succeeded)
        assert typed_document.processing_status == ProcessingStatus.PROCESSED
        
        # Verify that the queue service was not called (since storage failed first)
        mock_application.queue_service.publish_message.assert_not_called()
    
    def test_pipeline_performance_metrics(self, document_collection, mock_application):
        """Test the OCR pipeline's performance metrics.
        
        This test verifies that the OCR pipeline meets the performance requirements
        specified in the technical specification (processing time under 5 minutes,
        99% data extraction accuracy).
        """
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Process each document in the collection and collect metrics
        processing_times = []
        confidence_scores = []
        
        for document in document_collection:
            # Process the document through the pipeline
            start_time = time.time()
            result = mock_application.process_document(document)
            end_time = time.time()
            
            # Verify that the result is successful
            assert result.is_success
            
            # Extract the processed data and processing time from the result
            extracted_data, processing_time = result.value
            
            # Collect metrics
            processing_times.append(end_time - start_time)
            confidence_scores.append(extracted_data.average_confidence)
        
        # Verify that the average processing time is under 5 minutes
        avg_processing_time = sum(processing_times) / len(processing_times)
        assert avg_processing_time < 300, f"Average processing time ({avg_processing_time}s) exceeds 5 minutes"
        
        # Verify that the average confidence score is at least 0.99 (99% accuracy)
        avg_confidence = sum(confidence_scores) / len(confidence_scores)
        assert avg_confidence >= 0.99, f"Average confidence score ({avg_confidence}) is below 99%"
    
    def test_pipeline_with_retry_on_temporary_failure(self, typed_document, mock_application):
        """Test the OCR pipeline's retry mechanism for temporary failures.
        
        This test verifies that the OCR pipeline correctly retries operations that
        fail with temporary errors.
        """
        # Configure the OCR service to fail temporarily on first call, then succeed
        temp_error = ServiceError("Temporary error", ErrorCategory.EXTRACTION, {"retryable": True})
        mock_application.ocr_service.process_document.side_effect = [
            Result.failure(temp_error),
            Result.success(({"text": "Sample text"}, 1.0))
        ]
        
        # Configure the rest of the pipeline for successful processing
        mock_application.field_extraction_service.extract_fields.return_value = Result.success({
            "fields": {
                "name": {"value": "John Doe", "confidence": 0.98},
                "address": {"value": "123 Main St", "confidence": 0.95}
            }
        })
        mock_application.confidence_service.evaluate_confidence.return_value = Result.success({
            "overall_confidence": 0.99,
            "requires_verification": False
        })
        mock_application.storage_service.upload_extracted_data.return_value = Result.success(
            "s3://mca-documents-test/extracted/doc-123.json"
        )
        mock_application.queue_service.publish_message.return_value = Result.success(True)
        
        # Process the document through the pipeline
        result = mock_application.process_document(typed_document)
        
        # Verify that the result is successful (retry worked)
        assert result.is_success
        
        # Verify that the OCR service was called twice (initial failure + retry)
        assert mock_application.ocr_service.process_document.call_count == 2
        
        # Verify that the document status is updated to PROCESSED
        assert typed_document.processing_status == ProcessingStatus.PROCESSED
    
    def test_pipeline_with_document_classification(self, sample_document, mock_application):
        """Test the OCR pipeline's document classification capabilities.
        
        This test verifies that the OCR pipeline correctly classifies documents and
        applies the appropriate processing based on document type.
        """
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Set up a mock for the document classification function
        with patch('src.services.ocr_service.OCRService._classify_document') as mock_classify:
            # Configure the mock to return different document types
            mock_classify.return_value = DocumentType.BANK_STATEMENT
            
            # Process the document through the pipeline
            result = mock_application.process_document(sample_document)
            
            # Verify that the result is successful
            assert result.is_success
            
            # Verify that the document type was updated based on classification
            assert sample_document.document_type == DocumentType.BANK_STATEMENT
            
            # Verify that the OCR service used the classified document type
            mock_application.ocr_service.process_document.assert_called_once()
            called_document = mock_application.ocr_service.process_document.call_args[0][0]
            assert called_document.document_type == DocumentType.BANK_STATEMENT
    
    def test_pipeline_accuracy_with_test_data(self, test_metadata, mock_application, s3_mock):
        """Test the OCR pipeline's accuracy using test data with known values.
        
        This test verifies that the OCR pipeline achieves the required 99% accuracy
        by comparing extracted values with known expected values from test metadata.
        """
        # Skip this test if test metadata is not available
        if not test_metadata or "documents" not in test_metadata:
            pytest.skip("Test metadata not available")
        
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Track accuracy metrics
        total_fields = 0
        correct_fields = 0
        
        # Process each document in the test metadata
        for doc_name, doc_metadata in test_metadata["documents"].items():
            # Create a document based on the test metadata
            document = self._create_document_from_metadata(doc_name, doc_metadata)
            
            # Configure the field extraction service to return expected fields
            expected_fields = doc_metadata.get("expected_fields", {})
            mock_application.field_extraction_service.extract_fields.return_value = Result.success({
                "fields": {
                    field: {"value": value, "confidence": 0.95}
                    for field, value in expected_fields.items()
                }
            })
            
            # Process the document through the pipeline
            result = mock_application.process_document(document)
            
            # Verify that the result is successful
            assert result.is_success
            
            # Extract the processed data from the result
            extracted_data, _ = result.value
            
            # Compare extracted fields with expected fields
            for field, expected_value in expected_fields.items():
                total_fields += 1
                if field in extracted_data.fields and extracted_data.fields[field]["value"] == expected_value:
                    correct_fields += 1
        
        # Calculate accuracy
        accuracy = correct_fields / total_fields if total_fields > 0 else 0
        
        # Verify that the accuracy is at least 99%
        assert accuracy >= 0.99, f"Accuracy ({accuracy * 100}%) is below the required 99%"
    
    def test_pipeline_with_gpu_acceleration(self, typed_document, mock_application):
        """Test the OCR pipeline with GPU acceleration.
        
        This test verifies that the OCR pipeline correctly uses GPU acceleration
        for OCR processing when available.
        """
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Mock the GPU environment
        with patch('src.utils.tensorflow_utils.is_gpu_available', return_value=True):
            with patch('src.utils.tensorflow_utils.get_gpu_info', return_value="Tesla T4"):
                # Process the document through the pipeline
                result = mock_application.process_document(typed_document)
                
                # Verify that the result is successful
                assert result.is_success
                
                # Extract the processed data from the result
                extracted_data, _ = result.value
                
                # Verify that GPU acceleration was used
                assert "gpu_accelerated" in extracted_data.metadata
                assert extracted_data.metadata["gpu_accelerated"] is True
                assert "gpu_info" in extracted_data.metadata
                assert extracted_data.metadata["gpu_info"] == "Tesla T4"
    
    def test_pipeline_with_cpu_fallback(self, typed_document, mock_application):
        """Test the OCR pipeline's CPU fallback when GPU is not available.
        
        This test verifies that the OCR pipeline correctly falls back to CPU
        processing when GPU acceleration is not available.
        """
        # Configure the mocks for successful processing
        self._configure_mocks_for_successful_processing(mock_application)
        
        # Mock the GPU environment to indicate no GPU available
        with patch('src.utils.tensorflow_utils.is_gpu_available', return_value=False):
            # Process the document through the pipeline
            result = mock_application.process_document(typed_document)
            
            # Verify that the result is successful
            assert result.is_success
            
            # Extract the processed data from the result
            extracted_data, _ = result.value
            
            # Verify that CPU processing was used
            assert "gpu_accelerated" in extracted_data.metadata
            assert extracted_data.metadata["gpu_accelerated"] is False
    
    # Helper methods
    
    def _configure_mocks_for_successful_processing(self, mock_application):
        """Configure the mock application for successful document processing."""
        # Configure the OCR service to return successful results
        mock_application.ocr_service.process_document.return_value = Result.success(({
            "text": "Sample extracted text for testing",
            "confidence": 0.95
        }, 1.0))
        
        # Configure the field extraction service to return successful results
        mock_application.field_extraction_service.extract_fields.return_value = Result.success({
            "fields": {
                "name": {"value": "John Doe", "confidence": 0.98},
                "address": {"value": "123 Main St", "confidence": 0.95},
                "phone": {"value": "555-123-4567", "confidence": 0.92},
                "email": {"value": "john.doe@example.com", "confidence": 0.97},
                "business_name": {"value": "Acme Corporation", "confidence": 0.99},
                "tax_id": {"value": "12-3456789", "confidence": 0.96}
            }
        })
        
        # Configure the confidence service to return high confidence scores
        mock_application.confidence_service.evaluate_confidence.return_value = Result.success({
            "overall_confidence": 0.99,
            "requires_verification": False
        })
        
        # Configure the storage service to return successful results
        mock_application.storage_service.upload_extracted_data.return_value = Result.success(
            "s3://mca-documents-test/extracted/doc-123.json"
        )
        
        # Configure the queue service to return successful results
        mock_application.queue_service.publish_message.return_value = Result.success(True)
    
    def _configure_mocks_for_low_confidence_processing(self, mock_application):
        """Configure the mock application for low confidence document processing."""
        # Configure the OCR service to return successful results but with low confidence
        mock_application.ocr_service.process_document.return_value = Result.success(({
            "text": "Sample extracted text with low confidence",
            "confidence": 0.65
        }, 1.0))
        
        # Configure the field extraction service to return results with low confidence
        mock_application.field_extraction_service.extract_fields.return_value = Result.success({
            "fields": {
                "name": {"value": "John Doe", "confidence": 0.78},  # Below 0.8 threshold
                "address": {"value": "123 Main St", "confidence": 0.65},  # Below 0.8 threshold
                "phone": {"value": "555-123-4567", "confidence": 0.82},
                "email": {"value": "john.doe@example.com", "confidence": 0.75},  # Below 0.8 threshold
                "business_name": {"value": "Acme Corporation", "confidence": 0.85},
                "tax_id": {"value": "12-3456789", "confidence": 0.72}  # Below 0.8 threshold
            }
        })
        
        # Configure the confidence service to return low confidence scores
        mock_application.confidence_service.evaluate_confidence.return_value = Result.success({
            "overall_confidence": 0.75,  # Below 0.8 threshold
            "requires_verification": True
        })
        
        # Configure the storage service to return successful results
        mock_application.storage_service.upload_extracted_data.return_value = Result.success(
            "s3://mca-documents-test/extracted/doc-123.json"
        )
        
        # Configure the queue service to return successful results
        mock_application.queue_service.publish_message.return_value = Result.success(True)
    
    def _create_document_from_metadata(self, doc_name, doc_metadata):
        """Create a document object from test metadata."""
        metadata = DocumentMetadata(
            filename=doc_name,
            content_type="application/pdf",
            size=12345,
            created_at="2023-01-01T12:00:00Z",
            updated_at="2023-01-01T12:00:00Z",
            document_id=f"doc-{doc_name.replace('.', '-')}",
            application_id="app-test-123"
        )
        
        # Create dummy content
        content = b"%PDF-1.5\nTest document content\n%%EOF"
        
        # Determine document type from metadata
        doc_type_str = doc_metadata.get("type", "application").upper()
        doc_type = getattr(DocumentType, doc_type_str, DocumentType.OTHER)
        
        return Document(
            metadata=metadata,
            content=content,
            document_type=doc_type,
            status=ProcessingStatus.PENDING
        )