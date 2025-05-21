#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Routing Service.

This module contains tests that verify the document routing service correctly determines
the optimal OCR processing strategy based on document type, classification confidence,
and document characteristics. It validates that documents are routed to appropriate OCR
processors with correct metadata and processing hints.
"""

import pytest
import unittest.mock as mock
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import the service to test
from document_service.src.services.document_routing_service import DocumentRoutingService

# Import types
from document_service.src.types.documents import Document, DocumentType, ProcessingStatus, DocumentMetadata
from document_service.src.types.classification import ClassificationResult, ConfidenceScore
from document_service.src.types.messages import MessagePayload, MessageHeaders
from document_service.src.types.errors import Result, ServiceError


@pytest.fixture
def mock_queue_service():
    """Create a mock queue service for testing."""
    queue_service = mock.MagicMock()
    queue_service.publish_message = mock.MagicMock(return_value=None)
    return queue_service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service for testing."""
    storage_service = mock.MagicMock()
    storage_service.update_document_metadata = mock.MagicMock(return_value=None)
    return storage_service


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    metadata = {
        'id': 'doc-123',
        'filename': 'test_document.pdf',
        'size': 1024,
        'mime_type': 'application/pdf',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'storage_path': 's3://mca-documents-test/doc-123.pdf',
        'page_count': 3
    }
    
    return Document(
        metadata=metadata,
        document_type=None,
        status=ProcessingStatus.RECEIVED
    )


@pytest.fixture
def sample_classification_result():
    """Create a sample classification result for testing."""
    return ClassificationResult(
        document_id='doc-123',
        document_type=DocumentType.APPLICATION,
        confidence=0.85,
        requires_review=False,
        prediction_time=datetime.utcnow(),
        feature_importance={'feature1': 0.5, 'feature2': 0.3}
    )


@pytest.fixture
def low_confidence_classification_result():
    """Create a low confidence classification result for testing."""
    return ClassificationResult(
        document_id='doc-123',
        document_type=DocumentType.APPLICATION,
        confidence=0.65,  # Below default threshold of 0.75
        requires_review=True,
        prediction_time=datetime.utcnow(),
        feature_importance={'feature1': 0.5, 'feature2': 0.3}
    )


@pytest.fixture
def classification_result_with_alternatives():
    """Create a classification result with alternative types for testing."""
    result = ClassificationResult(
        document_id='doc-123',
        document_type=DocumentType.APPLICATION,
        confidence=0.70,
        requires_review=True,
        prediction_time=datetime.utcnow(),
        feature_importance={'feature1': 0.5, 'feature2': 0.3}
    )
    
    # Add alternative types
    result.alternative_types = {
        DocumentType.TAX_RETURN: 0.20,
        DocumentType.BANK_STATEMENT: 0.10
    }
    
    return result


class TestDocumentRoutingService:
    """Test suite for the DocumentRoutingService class."""
    
    def test_initialization(self, mock_queue_service, mock_storage_service):
        """Test that the service initializes correctly with dependencies."""
        service = DocumentRoutingService(queue_service=mock_queue_service, storage_service=mock_storage_service)
        
        assert service.queue_service == mock_queue_service
        assert service.storage_service == mock_storage_service
        assert service.confidence_threshold == 0.75  # Default threshold
        assert len(service.ocr_processor_map) == len(DocumentType)
        assert len(service.document_characteristics_map) == 4  # typed, handwritten, mixed, default
    
    def test_load_confidence_thresholds(self, mock_queue_service, mock_storage_service):
        """Test loading confidence thresholds from configuration."""
        with mock.patch('document_service.src.services.document_routing_service.CONFIDENCE_THRESHOLDS') as mock_config:
            # Set up mock configuration
            mock_config.DEFAULT = 0.80
            mock_config.APPLICATION_THRESHOLD = 0.85
            mock_config.TAX_RETURN_THRESHOLD = 0.90
            
            service = DocumentRoutingService(mock_queue_service, mock_storage_service)
            service._load_confidence_thresholds()
            
            assert service.confidence_threshold == 0.80
            assert service.type_confidence_thresholds[DocumentType.APPLICATION] == 0.85
            assert service.type_confidence_thresholds[DocumentType.TAX_RETURN] == 0.90
            # Other types should default to the default threshold
            assert service.type_confidence_thresholds[DocumentType.BANK_STATEMENT] == 0.80
    
    def test_route_document_success(self, mock_queue_service, mock_storage_service, sample_document, sample_classification_result):
        """Test successful document routing with high confidence."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Execute the method under test
        result = service.route_document(sample_document, sample_classification_result)
        
        # Verify the result
        assert result.is_success
        routing_metadata = result.value
        
        # Check routing metadata
        assert routing_metadata['document_id'] == sample_document.metadata['id']
        assert 'routing_timestamp' in routing_metadata
        assert routing_metadata['routing_decisions']['ocr_processor'] == 'application_processor'
        assert routing_metadata['routing_decisions']['ocr_strategy'] == 'mixed_ocr'
        assert routing_metadata['routing_decisions']['needs_human_review'] is False
        assert routing_metadata['document_metadata']['document_type'] == 'APPLICATION'
        
        # Verify storage service was called
        mock_storage_service.update_document_metadata.assert_called_once()
        
        # Verify queue service was called
        mock_queue_service.publish_message.assert_called_once()
        call_args = mock_queue_service.publish_message.call_args[1]
        assert call_args['exchange'] == 'mca.documents'
        assert call_args['routing_key'] == 'ocr.application_processor'
    
    def test_route_document_low_confidence(self, mock_queue_service, mock_storage_service, sample_document, low_confidence_classification_result):
        """Test document routing with low confidence requiring human review."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Execute the method under test
        result = service.route_document(sample_document, low_confidence_classification_result)
        
        # Verify the result
        assert result.is_success
        routing_metadata = result.value
        
        # Check routing metadata for human review flag
        assert routing_metadata['routing_decisions']['needs_human_review'] is True
        assert routing_metadata['routing_decisions']['priority'] == 'high'  # High priority for human review
        
        # Verify queue service was called with appropriate headers
        mock_queue_service.publish_message.assert_called_once()
        call_args = mock_queue_service.publish_message.call_args[1]
        assert call_args['headers']['priority'] == 'high'
    
    def test_determine_document_characteristics(self, mock_queue_service, mock_storage_service, sample_document, sample_classification_result):
        """Test determination of document characteristics for OCR strategy selection."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Test with classification result that has document_characteristics attribute
        sample_classification_result.document_characteristics = 'typed'
        characteristics = service._determine_document_characteristics(sample_document, sample_classification_result)
        assert characteristics == 'typed'
        
        # Test without document_characteristics attribute (should use default mapping)
        delattr(sample_classification_result, 'document_characteristics')
        characteristics = service._determine_document_characteristics(sample_document, sample_classification_result)
        assert characteristics == 'mixed'  # Default for APPLICATION type
        
        # Test with different document type
        sample_classification_result.document_type = DocumentType.TAX_RETURN
        characteristics = service._determine_document_characteristics(sample_document, sample_classification_result)
        assert characteristics == 'typed'  # Default for TAX_RETURN type
    
    def test_create_routing_metadata(self, mock_queue_service, mock_storage_service, sample_document, sample_classification_result):
        """Test creation of routing metadata for downstream OCR processors."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Execute the method under test
        metadata = service._create_routing_metadata(
            document=sample_document,
            classification_result=sample_classification_result,
            ocr_processor='application_processor',
            ocr_strategy='mixed_ocr',
            needs_human_review=False,
            doc_characteristics='mixed'
        )
        
        # Verify metadata structure and content
        assert metadata['document_id'] == sample_document.metadata['id']
        assert 'routing_timestamp' in metadata
        assert metadata['routing_decisions']['ocr_processor'] == 'application_processor'
        assert metadata['routing_decisions']['ocr_strategy'] == 'mixed_ocr'
        assert metadata['routing_decisions']['needs_human_review'] is False
        assert metadata['routing_decisions']['priority'] == 'normal'
        assert metadata['document_metadata']['document_type'] == 'APPLICATION'
        assert metadata['document_metadata']['document_characteristics'] == 'mixed'
        assert metadata['document_metadata']['page_count'] == 3
        assert metadata['classification_metadata']['confidence'] == 0.85
        assert 'processing_hints' in metadata
        
        # Verify processing hints for APPLICATION type
        assert metadata['processing_hints']['form_detection'] is True
        assert metadata['processing_hints']['signature_detection'] is True
        assert 'expected_fields' in metadata['processing_hints']
        assert 'applicant_name' in metadata['processing_hints']['expected_fields']
    
    def test_get_alternative_types(self, mock_queue_service, mock_storage_service, classification_result_with_alternatives):
        """Test extraction of alternative document types for borderline classifications."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Execute the method under test
        alternatives = service._get_alternative_types(classification_result_with_alternatives)
        
        # Verify alternatives
        assert len(alternatives) == 2
        assert alternatives[0]['type'] == 'TAX_RETURN'
        assert alternatives[0]['confidence'] == 0.20
        assert alternatives[1]['type'] == 'BANK_STATEMENT'
        assert alternatives[1]['confidence'] == 0.10
        
        # Test with classification result without alternatives
        result_without_alternatives = ClassificationResult(
            document_id='doc-123',
            document_type=DocumentType.APPLICATION,
            confidence=0.85,
            requires_review=False
        )
        
        alternatives = service._get_alternative_types(result_without_alternatives)
        assert len(alternatives) == 0
    
    def test_generate_processing_hints(self, mock_queue_service, mock_storage_service):
        """Test generation of processing hints for OCR processors."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Test hints for APPLICATION type with high confidence
        hints = service._generate_processing_hints(
            document_type=DocumentType.APPLICATION,
            doc_characteristics='mixed',
            confidence=0.95
        )
        
        assert hints['expected_content_type'] == 'mixed'
        assert hints['confidence_level'] == 'high'
        assert hints['form_detection'] is True
        assert hints['signature_detection'] is True
        assert 'expected_fields' in hints
        assert 'applicant_name' in hints['expected_fields']
        
        # Test hints for TAX_RETURN type with medium confidence
        hints = service._generate_processing_hints(
            document_type=DocumentType.TAX_RETURN,
            doc_characteristics='typed',
            confidence=0.80
        )
        
        assert hints['expected_content_type'] == 'typed'
        assert hints['confidence_level'] == 'medium'
        assert hints['form_detection'] is True
        assert hints['table_detection'] is True
        assert 'expected_fields' in hints
        assert 'taxpayer_name' in hints['expected_fields']
        
        # Test hints for OTHER type with low confidence
        hints = service._generate_processing_hints(
            document_type=DocumentType.OTHER,
            doc_characteristics='mixed',
            confidence=0.60
        )
        
        assert hints['expected_content_type'] == 'mixed'
        assert hints['confidence_level'] == 'low'
        assert hints['form_detection'] is True
        assert hints['table_detection'] is True
        assert hints['general_text_extraction'] is True
    
    def test_update_document_metadata(self, mock_queue_service, mock_storage_service, sample_document):
        """Test updating document metadata in storage with routing information."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Create sample routing metadata
        routing_metadata = {
            'routing_timestamp': '2023-01-01T12:00:00Z',
            'routing_decisions': {
                'ocr_processor': 'application_processor',
                'ocr_strategy': 'mixed_ocr',
                'needs_human_review': False
            }
        }
        
        # Execute the method under test
        service._update_document_metadata(sample_document, routing_metadata)
        
        # Verify storage service was called with correct parameters
        mock_storage_service.update_document_metadata.assert_called_once_with(
            sample_document.id,
            {
                'routing_info': {
                    'timestamp': routing_metadata['routing_timestamp'],
                    'ocr_processor': 'application_processor',
                    'ocr_strategy': 'mixed_ocr',
                    'needs_human_review': False
                },
                'processing_status': 'ROUTING_COMPLETE'
            }
        )
    
    def test_publish_routing_message(self, mock_queue_service, mock_storage_service, sample_document):
        """Test publishing routing message to OCR service via RabbitMQ."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Create sample routing metadata
        routing_metadata = {
            'document_id': 'doc-123',
            'routing_timestamp': '2023-01-01T12:00:00Z',
            'routing_decisions': {
                'ocr_processor': 'application_processor',
                'ocr_strategy': 'mixed_ocr',
                'needs_human_review': False,
                'priority': 'normal'
            },
            'document_metadata': {
                'document_type': 'APPLICATION',
                'document_characteristics': 'mixed'
            }
        }
        
        # Execute the method under test
        service._publish_routing_message(sample_document, routing_metadata)
        
        # Verify queue service was called with correct parameters
        mock_queue_service.publish_message.assert_called_once()
        call_args = mock_queue_service.publish_message.call_args[1]
        
        assert call_args['exchange'] == 'mca.documents'
        assert call_args['routing_key'] == 'ocr.application_processor'
        
        # Check payload
        payload = call_args['payload']
        assert payload['document_id'] == 'doc-123'
        assert payload['storage_path'] == 's3://mca-documents-test/doc-123.pdf'
        assert 'routing_metadata' in payload
        assert 'timestamp' in payload
        
        # Check headers
        headers = call_args['headers']
        assert headers['document_type'] == 'APPLICATION'
        assert headers['ocr_processor'] == 'application_processor'
        assert headers['ocr_strategy'] == 'mixed_ocr'
        assert headers['priority'] == 'normal'
    
    def test_route_document_error_handling(self, mock_queue_service, mock_storage_service, sample_document, sample_classification_result):
        """Test error handling in route_document method."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Make storage service raise an exception
        mock_storage_service.update_document_metadata.side_effect = Exception("Storage error")
        
        # Execute the method under test
        result = service.route_document(sample_document, sample_classification_result)
        
        # Verify the result is a failure
        assert result.is_failure
        assert "Failed to route document" in str(result.error)
        assert "Storage error" in str(result.error)
    
    def test_fallback_strategy_for_uncertain_classification(self, mock_queue_service, mock_storage_service, sample_document):
        """Test fallback strategy for uncertain classifications."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Create a very low confidence classification result
        very_low_confidence_result = ClassificationResult(
            document_id='doc-123',
            document_type=DocumentType.OTHER,  # Fallback to OTHER type
            confidence=0.35,  # Very low confidence
            requires_review=True,
            prediction_time=datetime.utcnow()
        )
        
        # Execute the method under test
        result = service.route_document(sample_document, very_low_confidence_result)
        
        # Verify the result
        assert result.is_success
        routing_metadata = result.value
        
        # Check routing decisions for fallback strategy
        assert routing_metadata['routing_decisions']['needs_human_review'] is True
        assert routing_metadata['routing_decisions']['priority'] == 'high'
        assert routing_metadata['routing_decisions']['ocr_processor'] == 'general_document_processor'
        
        # Verify processing hints for uncertain classification
        assert routing_metadata['processing_hints']['confidence_level'] == 'low'
        assert routing_metadata['processing_hints']['general_text_extraction'] is True
        
        # Verify queue service was called with appropriate routing key
        mock_queue_service.publish_message.assert_called_once()
        call_args = mock_queue_service.publish_message.call_args[1]
        assert call_args['routing_key'] == 'ocr.general_document_processor'
    
    def test_document_type_specific_confidence_thresholds(self, mock_queue_service, mock_storage_service, sample_document):
        """Test document type-specific confidence thresholds."""
        # Create a service with custom thresholds
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Override type confidence thresholds
        service.type_confidence_thresholds = {
            DocumentType.APPLICATION: 0.80,
            DocumentType.TAX_RETURN: 0.90,
            DocumentType.BANK_STATEMENT: 0.85,
            DocumentType.PAY_STUB: 0.85,
            DocumentType.ID_DOCUMENT: 0.95,  # Higher threshold for sensitive documents
            DocumentType.OTHER: 0.70
        }
        
        # Test with APPLICATION type at 0.85 confidence (above threshold)
        high_confidence_result = ClassificationResult(
            document_id='doc-123',
            document_type=DocumentType.APPLICATION,
            confidence=0.85,
            requires_review=False
        )
        
        result = service.route_document(sample_document, high_confidence_result)
        assert result.is_success
        assert result.value['routing_decisions']['needs_human_review'] is False
        
        # Test with APPLICATION type at 0.75 confidence (below threshold)
        low_confidence_result = ClassificationResult(
            document_id='doc-123',
            document_type=DocumentType.APPLICATION,
            confidence=0.75,
            requires_review=False  # This should be overridden by the threshold check
        )
        
        result = service.route_document(sample_document, low_confidence_result)
        assert result.is_success
        assert result.value['routing_decisions']['needs_human_review'] is True
        
        # Test with ID_DOCUMENT type at 0.90 confidence (below threshold)
        id_document_result = ClassificationResult(
            document_id='doc-123',
            document_type=DocumentType.ID_DOCUMENT,
            confidence=0.90,
            requires_review=False
        )
        
        result = service.route_document(sample_document, id_document_result)
        assert result.is_success
        assert result.value['routing_decisions']['needs_human_review'] is True
    
    def test_routing_decision_tracking(self, mock_queue_service, mock_storage_service, sample_document, sample_classification_result):
        """Test tracking of routing decisions for monitoring."""
        service = DocumentRoutingService(mock_queue_service, mock_storage_service)
        
        # Execute the method under test
        result = service.route_document(sample_document, sample_classification_result)
        
        # Verify the result
        assert result.is_success
        
        # Verify storage service was called to update metadata with routing information
        mock_storage_service.update_document_metadata.assert_called_once()
        call_args = mock_storage_service.update_document_metadata.call_args[0]
        
        # First argument should be document ID
        assert call_args[0] == sample_document.id
        
        # Second argument should be metadata update with routing info
        metadata_update = call_args[1]
        assert 'routing_info' in metadata_update
        assert 'timestamp' in metadata_update['routing_info']
        assert metadata_update['routing_info']['ocr_processor'] == 'application_processor'
        assert metadata_update['routing_info']['ocr_strategy'] == 'mixed_ocr'
        assert metadata_update['routing_info']['needs_human_review'] is False
        assert metadata_update['processing_status'] == 'ROUTING_COMPLETE'