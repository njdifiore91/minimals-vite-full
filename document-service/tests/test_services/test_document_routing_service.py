#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the document routing service.

This module contains tests that verify the document routing service correctly determines
the optimal OCR processing strategy based on document type, classification confidence,
and document characteristics. It ensures that documents are properly routed to the
appropriate OCR processors with the correct metadata and instructions.
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from document_service.services.document_routing_service import DocumentRoutingService
from document_service.types.classification import ClassificationResult, ConfidenceScore, DocumentType


# ===== Test DocumentRoutingService Initialization =====

def test_init_with_default_config():
    """Test initialization of DocumentRoutingService with default configuration."""
    # Initialize service with default configuration
    routing_service = DocumentRoutingService()
    
    # Verify default thresholds are set correctly
    assert routing_service.high_confidence_threshold == 0.85
    assert routing_service.medium_confidence_threshold == 0.75
    assert routing_service.low_confidence_threshold == 0.60
    
    # Verify routing metrics are initialized
    assert routing_service.routing_metrics['total_routed'] == 0
    assert routing_service.routing_metrics['high_confidence_routes'] == 0
    assert routing_service.routing_metrics['medium_confidence_routes'] == 0
    assert routing_service.routing_metrics['low_confidence_routes'] == 0
    assert routing_service.routing_metrics['fallback_routes'] == 0
    assert routing_service.routing_metrics['routing_errors'] == 0
    assert routing_service.routing_metrics['avg_routing_time_ms'] == 0
    assert routing_service.routing_metrics['total_routing_time_ms'] == 0


def test_init_with_custom_config():
    """Test initialization of DocumentRoutingService with custom configuration."""
    # Create custom configuration
    custom_config = {
        'high_confidence_threshold': 0.90,
        'medium_confidence_threshold': 0.80,
        'low_confidence_threshold': 0.70
    }
    
    # Initialize service with custom configuration
    routing_service = DocumentRoutingService(config=custom_config)
    
    # Verify custom thresholds are set correctly
    assert routing_service.high_confidence_threshold == 0.90
    assert routing_service.medium_confidence_threshold == 0.80
    assert routing_service.low_confidence_threshold == 0.70


# ===== Test Document Routing Logic =====

def test_route_document_high_confidence():
    """Test routing a document with high confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Create test document and classification result
    document_id = "test-doc-123"
    classification_result = ClassificationResult(
        document_id=document_id,
        document_type=DocumentType.APPLICATION,
        confidence=ConfidenceScore(0.95),
        requires_review=False,
        prediction_time=time.time(),
        feature_importance={}
    )
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 1024,
        'page_count': 3,
        'source': 'email'
    }
    
    # Route document
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        routing_result = routing_service.route_document(
            document_id, classification_result, document_metadata
        )
    
    # Verify routing result
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == DocumentType.APPLICATION
    assert routing_result['ocr_processor'] == 'form_ocr'
    assert routing_result['classification_confidence'] == 0.95
    assert routing_result['review_required'] is False
    assert routing_result['processing_priority'] == 'high'
    assert routing_result['content_type'] == 'mixed'
    assert routing_result['routing_timestamp'] == 1609459200
    
    # Verify metrics were updated
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['high_confidence_routes'] == 1


def test_route_document_medium_confidence():
    """Test routing a document with medium confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Create test document and classification result
    document_id = "test-doc-456"
    classification_result = ClassificationResult(
        document_id=document_id,
        document_type=DocumentType.TAX_RETURN,
        confidence=ConfidenceScore(0.80),
        requires_review=False,
        prediction_time=time.time(),
        feature_importance={}
    )
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 2048,
        'page_count': 5,
        'source': 'email'
    }
    
    # Route document
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        routing_result = routing_service.route_document(
            document_id, classification_result, document_metadata
        )
    
    # Verify routing result
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == DocumentType.TAX_RETURN
    assert routing_result['ocr_processor'] == 'financial_ocr'
    assert routing_result['classification_confidence'] == 0.80
    assert routing_result['review_required'] is True  # Medium confidence requires review
    assert routing_result['processing_priority'] == 'medium'
    assert routing_result['content_type'] == 'typed'
    
    # Verify metrics were updated
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['medium_confidence_routes'] == 1


def test_route_document_low_confidence():
    """Test routing a document with low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Create test document and classification result
    document_id = "test-doc-789"
    classification_result = ClassificationResult(
        document_id=document_id,
        document_type=DocumentType.BANK_STATEMENT,
        confidence=ConfidenceScore(0.65),
        requires_review=True,
        prediction_time=time.time(),
        feature_importance={}
    )
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 1536,
        'page_count': 2,
        'source': 'email'
    }
    
    # Route document
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        routing_result = routing_service.route_document(
            document_id, classification_result, document_metadata
        )
    
    # Verify routing result
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == DocumentType.BANK_STATEMENT
    assert routing_result['ocr_processor'] == 'financial_ocr'
    assert routing_result['classification_confidence'] == 0.65
    assert routing_result['review_required'] is True  # Low confidence requires review
    assert routing_result['processing_priority'] == 'low'
    assert routing_result['content_type'] == 'typed'
    
    # Verify metrics were updated
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['low_confidence_routes'] == 1


def test_route_document_very_low_confidence():
    """Test routing a document with very low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Create test document and classification result
    document_id = "test-doc-101112"
    classification_result = ClassificationResult(
        document_id=document_id,
        document_type=DocumentType.IDENTITY_DOCUMENT,
        confidence=ConfidenceScore(0.55),
        requires_review=True,
        prediction_time=time.time(),
        feature_importance={}
    )
    document_metadata = {
        'file_type': 'jpg',
        'file_size': 512,
        'page_count': 1,
        'source': 'email'
    }
    
    # Route document
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        routing_result = routing_service.route_document(
            document_id, classification_result, document_metadata
        )
    
    # Verify routing result
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == DocumentType.IDENTITY_DOCUMENT
    assert routing_result['ocr_processor'] == 'general_ocr'  # Very low confidence uses general OCR
    assert routing_result['classification_confidence'] == 0.55
    assert routing_result['review_required'] is True
    assert routing_result['processing_priority'] == 'low'
    assert routing_result['content_type'] == 'mixed'
    
    # Verify metrics were updated
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['fallback_routes'] == 1


def test_route_document_with_error():
    """Test routing a document with an error during processing."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Create test document and classification result (None to trigger error)
    document_id = "test-doc-error"
    classification_result = None  # This will cause an error
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 1024,
        'page_count': 3,
        'source': 'email'
    }
    
    # Route document
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        routing_result = routing_service.route_document(
            document_id, classification_result, document_metadata
        )
    
    # Verify fallback routing result
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == 'unknown'
    assert routing_result['ocr_processor'] == 'general_ocr'
    assert routing_result['classification_confidence'] == 0.0
    assert routing_result['review_required'] is True
    assert routing_result['processing_priority'] == 'low'
    assert routing_result['content_type'] == 'mixed'
    assert 'FALLBACK_ROUTING' in routing_result['special_instructions']
    
    # Verify error metrics were updated
    assert routing_service.routing_metrics['routing_errors'] == 1


# ===== Test OCR Processor Determination =====

def test_determine_ocr_processor_high_confidence():
    """Test determining OCR processor for high confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with high confidence
    document_type = DocumentType.APPLICATION
    confidence_score = ConfidenceScore(0.95)
    document_metadata = {}
    
    # Determine OCR processor
    ocr_processor, review_required, processing_priority = routing_service._determine_ocr_processor(
        document_type, confidence_score, document_metadata
    )
    
    # Verify result
    assert ocr_processor == 'form_ocr'
    assert review_required is False
    assert processing_priority == 'high'


def test_determine_ocr_processor_medium_confidence():
    """Test determining OCR processor for medium confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with medium confidence
    document_type = DocumentType.TAX_RETURN
    confidence_score = ConfidenceScore(0.80)
    document_metadata = {}
    
    # Determine OCR processor
    ocr_processor, review_required, processing_priority = routing_service._determine_ocr_processor(
        document_type, confidence_score, document_metadata
    )
    
    # Verify result
    assert ocr_processor == 'financial_ocr'
    assert review_required is True
    assert processing_priority == 'medium'


def test_determine_ocr_processor_low_confidence():
    """Test determining OCR processor for low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with low confidence
    document_type = DocumentType.BANK_STATEMENT
    confidence_score = ConfidenceScore(0.65)
    document_metadata = {}
    
    # Determine OCR processor
    ocr_processor, review_required, processing_priority = routing_service._determine_ocr_processor(
        document_type, confidence_score, document_metadata
    )
    
    # Verify result
    assert ocr_processor == 'financial_ocr'
    assert review_required is True
    assert processing_priority == 'low'


def test_determine_ocr_processor_very_low_confidence():
    """Test determining OCR processor for very low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with very low confidence
    document_type = DocumentType.IDENTITY_DOCUMENT
    confidence_score = ConfidenceScore(0.55)
    document_metadata = {}
    
    # Determine OCR processor
    ocr_processor, review_required, processing_priority = routing_service._determine_ocr_processor(
        document_type, confidence_score, document_metadata
    )
    
    # Verify result
    assert ocr_processor == 'general_ocr'  # Very low confidence uses general OCR
    assert review_required is True
    assert processing_priority == 'low'


# ===== Test Content Type Determination =====

def test_determine_content_type_from_metadata():
    """Test determining content type from document metadata."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with content type in metadata
    document_type = DocumentType.APPLICATION
    document_metadata = {'content_type': 'handwritten'}
    
    # Determine content type
    content_type = routing_service._determine_content_type(document_type, document_metadata)
    
    # Verify result
    assert content_type == 'handwritten'


def test_determine_content_type_from_document_type():
    """Test determining content type from document type."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with no content type in metadata
    document_type = DocumentType.TAX_RETURN
    document_metadata = {}
    
    # Determine content type
    content_type = routing_service._determine_content_type(document_type, document_metadata)
    
    # Verify result
    assert content_type == 'typed'  # Tax returns are typically typed


def test_determine_content_type_unknown_document_type():
    """Test determining content type for unknown document type."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with unknown document type
    document_type = 'unknown_type'
    document_metadata = {}
    
    # Determine content type
    content_type = routing_service._determine_content_type(document_type, document_metadata)
    
    # Verify result
    assert content_type == 'mixed'  # Default for unknown types


# ===== Test Routing Metadata Creation =====

def test_create_routing_metadata():
    """Test creating routing metadata for a document."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test parameters
    document_id = "test-doc-metadata"
    document_type = DocumentType.APPLICATION
    ocr_processor = 'form_ocr'
    confidence_score = ConfidenceScore(0.95)
    review_required = False
    processing_priority = 'high'
    content_type = 'mixed'
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 1024,
        'page_count': 3,
        'source': 'email'
    }
    
    # Create routing metadata
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        routing_metadata = routing_service._create_routing_metadata(
            document_id, document_type, ocr_processor, confidence_score,
            review_required, processing_priority, content_type, document_metadata
        )
    
    # Verify routing metadata
    assert routing_metadata['document_id'] == document_id
    assert routing_metadata['document_type'] == document_type
    assert routing_metadata['ocr_processor'] == ocr_processor
    assert routing_metadata['classification_confidence'] == 0.95
    assert routing_metadata['review_required'] is False
    assert routing_metadata['processing_priority'] == 'high'
    assert routing_metadata['content_type'] == 'mixed'
    assert routing_metadata['file_type'] == 'pdf'
    assert routing_metadata['file_size'] == 1024
    assert routing_metadata['page_count'] == 3
    assert routing_metadata['source'] == 'email'
    assert routing_metadata['routing_timestamp'] == 1609459200
    assert routing_metadata['routing_version'] == '1.0'
    assert 'routing_id' in routing_metadata
    assert 'special_instructions' in routing_metadata


def test_create_fallback_routing_metadata():
    """Test creating fallback routing metadata for error cases."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test parameters
    document_id = "test-doc-fallback"
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 1024,
        'page_count': 3,
        'source': 'email'
    }
    
    # Create fallback routing metadata
    with patch('time.time', return_value=1609459200.0):  # 2021-01-01 00:00:00 UTC
        fallback_metadata = routing_service._create_fallback_routing_metadata(
            document_id, document_metadata
        )
    
    # Verify fallback routing metadata
    assert fallback_metadata['document_id'] == document_id
    assert fallback_metadata['document_type'] == 'unknown'
    assert fallback_metadata['ocr_processor'] == 'general_ocr'
    assert fallback_metadata['classification_confidence'] == 0.0
    assert fallback_metadata['review_required'] is True
    assert fallback_metadata['processing_priority'] == 'low'
    assert fallback_metadata['content_type'] == 'mixed'
    assert fallback_metadata['file_type'] == 'pdf'
    assert fallback_metadata['file_size'] == 1024
    assert fallback_metadata['page_count'] == 3
    assert fallback_metadata['source'] == 'email'
    assert fallback_metadata['routing_timestamp'] == 1609459200
    assert fallback_metadata['routing_version'] == '1.0'
    assert 'routing_id' in fallback_metadata
    assert 'FALLBACK_ROUTING' in fallback_metadata['special_instructions']
    assert 'Manual review required' in fallback_metadata['special_instructions']


# ===== Test Special Instructions Generation =====

def test_generate_special_instructions_low_confidence():
    """Test generating special instructions for low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with low confidence
    document_type = DocumentType.APPLICATION
    confidence_score = ConfidenceScore(0.55)
    content_type = 'mixed'
    
    # Generate special instructions
    instructions = routing_service._generate_special_instructions(
        document_type, confidence_score, content_type
    )
    
    # Verify instructions
    assert 'LOW_CONFIDENCE' in instructions
    assert 'MIXED_CONTENT' in instructions
    assert 'FORM_EXTRACTION' in instructions


def test_generate_special_instructions_handwritten():
    """Test generating special instructions for handwritten documents."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with handwritten content
    document_type = DocumentType.APPLICATION
    confidence_score = ConfidenceScore(0.85)
    content_type = 'handwritten'
    
    # Generate special instructions
    instructions = routing_service._generate_special_instructions(
        document_type, confidence_score, content_type
    )
    
    # Verify instructions
    assert 'HANDWRITTEN' in instructions
    assert 'FORM_EXTRACTION' in instructions


def test_generate_special_instructions_tax_return():
    """Test generating special instructions for tax return documents."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with tax return document
    document_type = DocumentType.TAX_RETURN
    confidence_score = ConfidenceScore(0.90)
    content_type = 'typed'
    
    # Generate special instructions
    instructions = routing_service._generate_special_instructions(
        document_type, confidence_score, content_type
    )
    
    # Verify instructions
    assert 'TABLE_EXTRACTION' in instructions


def test_generate_special_instructions_identity_document():
    """Test generating special instructions for identity documents."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with identity document
    document_type = DocumentType.IDENTITY_DOCUMENT
    confidence_score = ConfidenceScore(0.95)
    content_type = 'mixed'
    
    # Generate special instructions
    instructions = routing_service._generate_special_instructions(
        document_type, confidence_score, content_type
    )
    
    # Verify instructions
    assert 'ID_VERIFICATION' in instructions
    assert 'MIXED_CONTENT' in instructions


# ===== Test Routing Metrics =====

def test_update_routing_metrics_high_confidence():
    """Test updating routing metrics for high confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with high confidence
    confidence_score = ConfidenceScore(0.95)
    start_time = time.time() - 0.1  # 100ms ago
    
    # Update metrics
    routing_service._update_routing_metrics(confidence_score, start_time)
    
    # Verify metrics
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['high_confidence_routes'] == 1
    assert routing_service.routing_metrics['medium_confidence_routes'] == 0
    assert routing_service.routing_metrics['low_confidence_routes'] == 0
    assert routing_service.routing_metrics['fallback_routes'] == 0
    assert routing_service.routing_metrics['total_routing_time_ms'] > 0
    assert routing_service.routing_metrics['avg_routing_time_ms'] > 0


def test_update_routing_metrics_medium_confidence():
    """Test updating routing metrics for medium confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with medium confidence
    confidence_score = ConfidenceScore(0.80)
    start_time = time.time() - 0.1  # 100ms ago
    
    # Update metrics
    routing_service._update_routing_metrics(confidence_score, start_time)
    
    # Verify metrics
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['high_confidence_routes'] == 0
    assert routing_service.routing_metrics['medium_confidence_routes'] == 1
    assert routing_service.routing_metrics['low_confidence_routes'] == 0
    assert routing_service.routing_metrics['fallback_routes'] == 0


def test_update_routing_metrics_low_confidence():
    """Test updating routing metrics for low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with low confidence
    confidence_score = ConfidenceScore(0.65)
    start_time = time.time() - 0.1  # 100ms ago
    
    # Update metrics
    routing_service._update_routing_metrics(confidence_score, start_time)
    
    # Verify metrics
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['high_confidence_routes'] == 0
    assert routing_service.routing_metrics['medium_confidence_routes'] == 0
    assert routing_service.routing_metrics['low_confidence_routes'] == 1
    assert routing_service.routing_metrics['fallback_routes'] == 0


def test_update_routing_metrics_very_low_confidence():
    """Test updating routing metrics for very low confidence classification."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with very low confidence
    confidence_score = ConfidenceScore(0.55)
    start_time = time.time() - 0.1  # 100ms ago
    
    # Update metrics
    routing_service._update_routing_metrics(confidence_score, start_time)
    
    # Verify metrics
    assert routing_service.routing_metrics['total_routed'] == 1
    assert routing_service.routing_metrics['high_confidence_routes'] == 0
    assert routing_service.routing_metrics['medium_confidence_routes'] == 0
    assert routing_service.routing_metrics['low_confidence_routes'] == 0
    assert routing_service.routing_metrics['fallback_routes'] == 1


def test_get_routing_metrics():
    """Test getting routing metrics."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Update metrics with some test data
    routing_service._update_routing_metrics(ConfidenceScore(0.95), time.time() - 0.1)
    routing_service._update_routing_metrics(ConfidenceScore(0.80), time.time() - 0.1)
    routing_service._update_routing_metrics(ConfidenceScore(0.65), time.time() - 0.1)
    routing_service._update_routing_metrics(ConfidenceScore(0.55), time.time() - 0.1)
    
    # Get metrics
    metrics = routing_service.get_routing_metrics()
    
    # Verify metrics
    assert metrics['total_routed'] == 4
    assert metrics['high_confidence_routes'] == 1
    assert metrics['medium_confidence_routes'] == 1
    assert metrics['low_confidence_routes'] == 1
    assert metrics['fallback_routes'] == 1
    assert metrics['routing_errors'] == 0
    assert metrics['total_routing_time_ms'] > 0
    assert metrics['avg_routing_time_ms'] > 0


# ===== Test Utility Methods =====

def test_get_ocr_processor_for_document_type():
    """Test getting OCR processor for a document type."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with various document types
    assert routing_service.get_ocr_processor_for_document_type(DocumentType.APPLICATION) == 'form_ocr'
    assert routing_service.get_ocr_processor_for_document_type(DocumentType.TAX_RETURN) == 'financial_ocr'
    assert routing_service.get_ocr_processor_for_document_type(DocumentType.BANK_STATEMENT) == 'financial_ocr'
    assert routing_service.get_ocr_processor_for_document_type(DocumentType.IDENTITY_DOCUMENT) == 'id_ocr'
    assert routing_service.get_ocr_processor_for_document_type('unknown_type') == 'general_ocr'


def test_get_content_type_for_document_type():
    """Test getting content type for a document type."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with various document types
    assert routing_service.get_content_type_for_document_type(DocumentType.APPLICATION) == 'mixed'
    assert routing_service.get_content_type_for_document_type(DocumentType.TAX_RETURN) == 'typed'
    assert routing_service.get_content_type_for_document_type(DocumentType.BANK_STATEMENT) == 'typed'
    assert routing_service.get_content_type_for_document_type(DocumentType.IDENTITY_DOCUMENT) == 'mixed'
    assert routing_service.get_content_type_for_document_type('unknown_type') == 'mixed'


# ===== Test Invalid Input Handling =====

def test_route_document_missing_parameters():
    """Test routing a document with missing parameters."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Test with missing parameters
    document_id = "test-doc-missing"
    classification_result = None
    document_metadata = None
    
    # Route document
    routing_result = routing_service.route_document(
        document_id, classification_result, document_metadata
    )
    
    # Verify fallback routing result
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == 'unknown'
    assert routing_result['ocr_processor'] == 'general_ocr'
    assert routing_result['classification_confidence'] == 0.0
    assert routing_result['review_required'] is True
    assert routing_result['processing_priority'] == 'low'
    assert routing_result['content_type'] == 'mixed'
    assert 'FALLBACK_ROUTING' in routing_result['special_instructions']
    
    # Verify error metrics were updated
    assert routing_service.routing_metrics['routing_errors'] == 1


def test_route_document_invalid_document_type():
    """Test routing a document with an invalid document type."""
    # Initialize service
    routing_service = DocumentRoutingService()
    
    # Create test document and classification result with invalid document type
    document_id = "test-doc-invalid"
    classification_result = ClassificationResult(
        document_id=document_id,
        document_type="invalid_type",  # Invalid document type
        confidence=ConfidenceScore(0.95),
        requires_review=False,
        prediction_time=time.time(),
        feature_importance={}
    )
    document_metadata = {
        'file_type': 'pdf',
        'file_size': 1024,
        'page_count': 3,
        'source': 'email'
    }
    
    # Mock validation_utils.is_valid_document_type to return False
    with patch('document_service.utils.validation_utils.is_valid_document_type', return_value=False):
        # Route document
        routing_result = routing_service.route_document(
            document_id, classification_result, document_metadata
        )
    
    # Verify routing result uses fallback for invalid document type
    assert routing_result['document_id'] == document_id
    assert routing_result['document_type'] == 'other'
    assert routing_result['ocr_processor'] == 'general_ocr'
    assert routing_result['classification_confidence'] == 0.0  # Reset to 0 for fallback
    assert routing_result['review_required'] is True
    assert routing_result['processing_priority'] == 'low'