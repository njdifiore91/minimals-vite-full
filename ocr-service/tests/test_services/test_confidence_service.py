#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the confidence evaluation service.

This module contains tests that verify confidence scoring algorithms, threshold-based
flagging, and confidence metrics for extracted fields. It ensures the confidence service
correctly identifies uncertain extractions for human verification to maintain the 99%
data extraction accuracy requirement.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple, Union

from ocr_service.src.services.confidence_service import ConfidenceService
from ocr_service.src.types.extraction import (
    ConfidenceScore,
    ExtractedData,
    ExtractedField
)
from ocr_service.src.types.documents import DocumentType
from ocr_service.src.models.confidence_scoring import (
    calculate_field_confidence,
    normalize_confidence_score,
    calculate_document_confidence
)


# Define FieldConfidenceReport class since it's not defined in the existing files
@dataclass
class FieldConfidenceReport:
    """Report on confidence for a single extracted field.
    
    This class represents a confidence report for a single field, including
    the confidence score, threshold, verification flag, and importance weight.
    
    Attributes:
        field_name: Name of the field
        confidence: Confidence score for the field (0.0-1.0)
        threshold: Confidence threshold for this field
        needs_verification: Whether the field needs human verification
        importance_weight: Importance weight for this field (0.0-1.0)
    """
    
    field_name: str
    confidence: float
    threshold: float
    needs_verification: bool
    importance_weight: float


class TestConfidenceService:
    """Test suite for the ConfidenceService class."""
    
    @pytest.fixture
    def confidence_service(self):
        """Create a ConfidenceService instance for testing."""
        # Mock the configuration
        with patch('ocr_service.src.config.app_config') as mock_app_config, \
             patch('ocr_service.src.config.tensorflow_config') as mock_tf_config:
            
            # Configure the mock tensorflow_config
            mock_tf_config.confidence_thresholds = {
                "field.default.default": 0.75,  # Default threshold for any field
                "field.APPLICATION.business_name": 0.85,  # Higher threshold for business name
                "field.APPLICATION.tax_id": 0.90,  # Higher threshold for tax ID
                "field.APPLICATION.signature": 0.80,  # Higher threshold for signature
                "field.default.address": 0.70,  # Lower threshold for address
                "document.APPLICATION": 0.80,  # Document-level threshold for applications
                "document.default": 0.75  # Default document-level threshold
            }
            
            # Create and return the service
            service = ConfidenceService()
            return service
    
    @pytest.fixture
    def sample_extracted_field(self):
        """Create a sample extracted field for testing."""
        return ExtractedField(
            field_name="business_name",
            field_type="text",
            value="Acme Corporation",
            raw_text="Acme Corporation",
            confidence=ConfidenceScore.from_float(0.92),
            location={
                "page": 0,
                "top": 0.1,
                "left": 0.1,
                "bottom": 0.15,
                "right": 0.5,
                "width": 0.4,
                "height": 0.05
            },
            alternatives=[],
            metadata={},
            requires_verification=False,
            verification_reason="",
            extraction_timestamp="2023-01-01T12:00:00Z"
        )
    
    @pytest.fixture
    def sample_extracted_data(self):
        """Create sample extracted data for testing."""
        fields = {
            "business_name": ExtractedField(
                field_name="business_name",
                field_type="text",
                value="Acme Corporation",
                raw_text="Acme Corporation",
                confidence=ConfidenceScore.from_float(0.92),
                location={
                    "page": 0,
                    "top": 0.1,
                    "left": 0.1,
                    "bottom": 0.15,
                    "right": 0.5,
                    "width": 0.4,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            ),
            "tax_id": ExtractedField(
                field_name="tax_id",
                field_type="text",
                value="12-3456789",
                raw_text="12-3456789",
                confidence=ConfidenceScore.from_float(0.65),  # Low confidence
                location={
                    "page": 0,
                    "top": 0.2,
                    "left": 0.1,
                    "bottom": 0.25,
                    "right": 0.3,
                    "width": 0.2,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            ),
            "address": ExtractedField(
                field_name="address",
                field_type="text",
                value="123 Main St, Anytown, CA 90210",
                raw_text="123 Main St, Anytown, CA 90210",
                confidence=ConfidenceScore.from_float(0.88),
                location={
                    "page": 0,
                    "top": 0.3,
                    "left": 0.1,
                    "bottom": 0.35,
                    "right": 0.6,
                    "width": 0.5,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            ),
            "requested_amount": ExtractedField(
                field_name="requested_amount",
                field_type="currency",
                value=50000,
                raw_text="$50,000",
                confidence=ConfidenceScore.from_float(0.95),
                location={
                    "page": 0,
                    "top": 0.4,
                    "left": 0.1,
                    "bottom": 0.45,
                    "right": 0.3,
                    "width": 0.2,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            ),
            "signature": ExtractedField(
                field_name="signature",
                field_type="signature",
                value="John Smith",
                raw_text="John Smith",
                confidence=ConfidenceScore.from_float(0.78),
                location={
                    "page": 0,
                    "top": 0.8,
                    "left": 0.6,
                    "bottom": 0.85,
                    "right": 0.8,
                    "width": 0.2,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            )
        }
        
        return ExtractedData(
            extraction_id="test-extraction-123",
            fields=fields,
            tables=[],
            metadata={
                "extraction_id": "test-extraction-123",
                "document_id": "doc-123",
                "model_id": "typed_text_v1",
                "model_version": "1.0",
                "document_type": "application_form",
                "page_count": 1,
                "language": "en",
                "processing_node": "node1",
                "extraction_status": "success",
                "processing_time": 1.5,
                "warnings": [],
                "errors": []
            },
            raw_text="Acme Corporation\n12-3456789\n123 Main St, Anytown, CA 90210\n$50,000\nJohn Smith",
            low_confidence_fields=[],
            requires_verification=False,
            extraction_timestamp="2023-01-01T12:00:00Z",
            schema_version="1.0",
            document_type="APPLICATION"
        )
    
    def test_initialization(self, confidence_service):
        """Test that the ConfidenceService initializes correctly."""
        assert confidence_service is not None
        assert hasattr(confidence_service, 'thresholds')
        assert hasattr(confidence_service, 'field_importance')
        assert confidence_service.thresholds["field.default.default"] == 0.75
        assert confidence_service.thresholds["field.APPLICATION.business_name"] == 0.85
    
    def test_evaluate_field_confidence(self, confidence_service, sample_extracted_field):
        """Test evaluating confidence for a single field."""
        # Test with a high-confidence field
        confidence = confidence_service.evaluate_field_confidence(
            sample_extracted_field, DocumentType.APPLICATION
        )
        
        # Check that the confidence score is returned correctly
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        
        # Test with a low-confidence field
        low_confidence_field = sample_extracted_field.copy()
        low_confidence_field.confidence = ConfidenceScore.from_float(0.3)
        
        confidence = confidence_service.evaluate_field_confidence(
            low_confidence_field, DocumentType.APPLICATION
        )
        
        # Check that the confidence score is returned correctly
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.5  # Should be low confidence
    
    def test_evaluate_extraction_confidence(self, confidence_service, sample_extracted_data):
        """Test evaluating confidence for an entire extraction."""
        # Evaluate the extraction confidence
        document_confidence, field_reports = confidence_service.evaluate_extraction_confidence(
            sample_extracted_data
        )
        
        # Check the document confidence
        assert isinstance(document_confidence, float)
        assert 0.0 <= document_confidence <= 1.0
        
        # Check the field reports
        assert isinstance(field_reports, dict)
        assert len(field_reports) == len(sample_extracted_data["fields"])
        
        # Check that each field has a report
        for field_name in sample_extracted_data["fields"]:
            assert field_name in field_reports
            report = field_reports[field_name]
            assert isinstance(report, FieldConfidenceReport)
            assert report.field_name == field_name
            assert 0.0 <= report.confidence <= 1.0
            assert 0.0 <= report.threshold <= 1.0
            assert isinstance(report.needs_verification, bool)
            assert 0.0 <= report.importance_weight <= 1.0
        
        # Check that the tax_id field is flagged for verification (low confidence)
        assert field_reports["tax_id"].needs_verification
        
        # Check that the business_name field is not flagged (high confidence)
        assert not field_reports["business_name"].needs_verification
    
    def test_needs_human_verification(self, confidence_service, sample_extracted_data):
        """Test determining if an extraction needs human verification."""
        # Test with the sample data (should need verification due to tax_id)
        needs_verification, fields_needing_verification = confidence_service.needs_human_verification(
            sample_extracted_data
        )
        
        # Check the results
        assert needs_verification  # Should need verification
        assert isinstance(fields_needing_verification, set)
        assert "tax_id" in fields_needing_verification  # tax_id has low confidence
        
        # Test with all high-confidence fields
        high_confidence_data = sample_extracted_data.copy()
        for field_name, field in high_confidence_data["fields"].items():
            field_copy = field.copy()
            field_copy.confidence = ConfidenceScore.from_float(0.95)  # High confidence
            high_confidence_data["fields"][field_name] = field_copy
        
        needs_verification, fields_needing_verification = confidence_service.needs_human_verification(
            high_confidence_data
        )
        
        # Check the results
        assert not needs_verification  # Should not need verification
        assert len(fields_needing_verification) == 0  # No fields need verification
    
    def test_get_threshold(self, confidence_service):
        """Test getting confidence thresholds for different fields and document types."""
        # Test getting threshold for a specific field and document type
        threshold = confidence_service._get_threshold("business_name", DocumentType.APPLICATION)
        assert threshold == 0.85  # From the mock configuration
        
        # Test getting threshold for a field with default document type
        threshold = confidence_service._get_threshold("address", DocumentType.OTHER)
        assert threshold == 0.70  # From the mock configuration
        
        # Test getting threshold for a field and document type with no specific threshold
        threshold = confidence_service._get_threshold("email", DocumentType.APPLICATION)
        assert threshold == 0.75  # Should fall back to default
        
        # Test getting threshold for a completely unknown field and document type
        threshold = confidence_service._get_threshold("unknown_field", DocumentType.OTHER)
        assert threshold == 0.75  # Should fall back to global default
    
    def test_get_confidence_metrics(self, confidence_service, sample_extracted_data):
        """Test generating confidence metrics for monitoring."""
        # Get confidence metrics
        metrics = confidence_service.get_confidence_metrics(sample_extracted_data)
        
        # Check the metrics
        assert isinstance(metrics, dict)
        assert "document_confidence" in metrics
        assert "fields_count" in metrics
        assert "fields_needing_verification" in metrics
        assert "verification_needed" in metrics
        assert "min_field_confidence" in metrics
        assert "max_field_confidence" in metrics
        assert "avg_field_confidence" in metrics
        
        # Check specific values
        assert metrics["fields_count"] == len(sample_extracted_data["fields"])
        assert metrics["fields_needing_verification"] > 0  # tax_id needs verification
        assert metrics["verification_needed"] == 1.0  # Verification is needed
        assert 0.0 <= metrics["min_field_confidence"] <= 1.0
        assert 0.0 <= metrics["max_field_confidence"] <= 1.0
        assert 0.0 <= metrics["avg_field_confidence"] <= 1.0
        assert metrics["min_field_confidence"] <= metrics["avg_field_confidence"] <= metrics["max_field_confidence"]
    
    def test_enrich_extraction_with_confidence(self, confidence_service, sample_extracted_data):
        """Test enriching extraction data with confidence information."""
        # Enrich the extraction data
        enriched_data = confidence_service.enrich_extraction_with_confidence(sample_extracted_data)
        
        # Check that the original data was not modified
        assert enriched_data is not sample_extracted_data
        
        # Check that confidence metadata was added
        assert "document_confidence" in enriched_data.metadata
        assert "verification_needed" in enriched_data.metadata
        assert "fields_needing_verification" in enriched_data.metadata
        
        # Check that field confidence information was updated
        for field_name, field in enriched_data.fields.items():
            assert "needs_verification" in field.metadata
            assert "threshold" in field.metadata
            
        # Check that the tax_id field is flagged for verification
        assert enriched_data.fields["tax_id"].metadata["needs_verification"]
        
        # Check that the business_name field is not flagged
        assert not enriched_data.fields["business_name"].metadata["needs_verification"]
    
    def test_confidence_normalization(self, confidence_service):
        """Test confidence score normalization across different document types."""
        # Create fields with the same raw confidence but different document types
        field1 = ExtractedField(
            field_name="business_name",
            field_type="text",
            value="Acme Corporation",
            raw_text="Acme Corporation",
            confidence=ConfidenceScore.from_float(0.8),
            location={
                "page": 0,
                "top": 0.1,
                "left": 0.1,
                "bottom": 0.15,
                "right": 0.5,
                "width": 0.4,
                "height": 0.05
            },
            alternatives=[],
            metadata={},
            requires_verification=False,
            verification_reason="",
            extraction_timestamp="2023-01-01T12:00:00Z"
        )
        
        # Evaluate confidence for different document types
        confidence1 = confidence_service.evaluate_field_confidence(field1, DocumentType.APPLICATION)
        confidence2 = confidence_service.evaluate_field_confidence(field1, DocumentType.TAX_RETURN)
        
        # The confidence scores might be different due to normalization
        # This is a simple check to ensure the function runs without errors
        assert isinstance(confidence1, float)
        assert isinstance(confidence2, float)
    
    def test_document_level_confidence_assessment(self, confidence_service):
        """Test document-level confidence assessment with different field combinations."""
        # Create test data with different field confidence patterns
        high_confidence_data = self.create_test_extraction_data([
            ("field1", 0.95),
            ("field2", 0.92),
            ("field3", 0.90)
        ])
        
        mixed_confidence_data = self.create_test_extraction_data([
            ("field1", 0.95),
            ("field2", 0.60),  # Low confidence
            ("field3", 0.90)
        ])
        
        low_confidence_data = self.create_test_extraction_data([
            ("field1", 0.65),  # Low confidence
            ("field2", 0.60),  # Low confidence
            ("field3", 0.55)   # Low confidence
        ])
        
        # Evaluate document confidence for each dataset
        high_doc_confidence, _ = confidence_service.evaluate_extraction_confidence(high_confidence_data)
        mixed_doc_confidence, _ = confidence_service.evaluate_extraction_confidence(mixed_confidence_data)
        low_doc_confidence, _ = confidence_service.evaluate_extraction_confidence(low_confidence_data)
        
        # Check that document confidence reflects field confidences
        assert high_doc_confidence > mixed_doc_confidence > low_doc_confidence
        
        # Check verification needs
        high_needs_verification, _ = confidence_service.needs_human_verification(high_confidence_data)
        mixed_needs_verification, _ = confidence_service.needs_human_verification(mixed_confidence_data)
        low_needs_verification, _ = confidence_service.needs_human_verification(low_confidence_data)
        
        assert not high_needs_verification  # High confidence should not need verification
        assert mixed_needs_verification     # Mixed confidence should need verification
        assert low_needs_verification       # Low confidence should need verification
    
    def test_confidence_reporting(self, confidence_service, sample_extracted_data):
        """Test confidence reporting functionality."""
        # Get confidence metrics
        metrics = confidence_service.get_confidence_metrics(sample_extracted_data)
        
        # Check that metrics include all required fields for monitoring
        required_metrics = [
            "document_confidence",
            "fields_count",
            "fields_needing_verification",
            "verification_needed",
            "min_field_confidence",
            "max_field_confidence",
            "avg_field_confidence",
            "document_type"
        ]
        
        for metric in required_metrics:
            assert metric in metrics
        
        # Check that metrics values are within expected ranges
        assert 0.0 <= metrics["document_confidence"] <= 1.0
        assert metrics["fields_count"] > 0
        assert metrics["fields_needing_verification"] >= 0
        assert metrics["verification_needed"] in [0.0, 1.0]
        assert 0.0 <= metrics["min_field_confidence"] <= 1.0
        assert 0.0 <= metrics["max_field_confidence"] <= 1.0
        assert 0.0 <= metrics["avg_field_confidence"] <= 1.0
    
    def test_threshold_based_flagging(self, confidence_service):
        """Test threshold-based flagging of low-confidence extractions."""
        # Create test fields with different confidence levels
        fields = [
            # Field name, confidence, threshold, should be flagged
            ("business_name", 0.90, 0.85, False),  # Above threshold
            ("business_name", 0.80, 0.85, True),   # Below threshold
            ("tax_id", 0.95, 0.90, False),         # Above threshold
            ("tax_id", 0.85, 0.90, True),          # Below threshold
            ("address", 0.75, 0.70, False),        # Above threshold
            ("address", 0.65, 0.70, True),         # Below threshold
            ("unknown_field", 0.80, 0.75, False),  # Above default threshold
            ("unknown_field", 0.70, 0.75, True)    # Below default threshold
        ]
        
        # Test each field
        for field_name, confidence_value, threshold, should_be_flagged in fields:
            # Create a field with the specified confidence
            field = ExtractedField(
                field_name=field_name,
                field_type="text",
                value="Test Value",
                raw_text="Test Value",
                confidence=ConfidenceScore.from_float(confidence_value),
                location={
                    "page": 0,
                    "top": 0.1,
                    "left": 0.1,
                    "bottom": 0.15,
                    "right": 0.5,
                    "width": 0.4,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            )
            
            # Create test data with just this field
            test_data = self.create_test_extraction_data([(field_name, confidence_value)])
            
            # Check if verification is needed
            needs_verification, fields_needing_verification = confidence_service.needs_human_verification(test_data)
            
            # Check that the field is flagged correctly
            if should_be_flagged:
                assert field_name in fields_needing_verification
                assert needs_verification
            else:
                assert field_name not in fields_needing_verification
                # Note: needs_verification might still be True if the document confidence is low
    
    def test_field_level_confidence_metrics(self, confidence_service, sample_extracted_data):
        """Test field-level confidence metrics calculation."""
        # Evaluate extraction confidence
        _, field_reports = confidence_service.evaluate_extraction_confidence(sample_extracted_data)
        
        # Check metrics for each field
        for field_name, field in sample_extracted_data["fields"].items():
            # Get the report for this field
            report = field_reports[field_name]
            
            # Check that the report contains the correct metrics
            assert report.field_name == field_name
            assert isinstance(report.confidence, float)
            assert isinstance(report.threshold, float)
            assert isinstance(report.needs_verification, bool)
            assert isinstance(report.importance_weight, float)
            
            # Check that the confidence value is within range
            assert 0.0 <= report.confidence <= 1.0
            
            # Check that the threshold is within range
            assert 0.0 <= report.threshold <= 1.0
            
            # Check that the importance weight is within range
            assert 0.0 <= report.importance_weight <= 1.0
            
            # Check that needs_verification is consistent with the confidence and threshold
            if report.confidence < report.threshold:
                assert report.needs_verification
            else:
                assert not report.needs_verification
    
    # Helper method to create test extraction data
    def create_test_extraction_data(self, field_data):
        """Create test extraction data with specified fields and confidence scores.
        
        Args:
            field_data: List of tuples (field_name, confidence_value)
            
        Returns:
            ExtractedData object with the specified fields
        """
        fields = {}
        
        for field_name, confidence_value in field_data:
            fields[field_name] = ExtractedField(
                field_name=field_name,
                field_type="text",
                value="Test Value",
                raw_text="Test Value",
                confidence=ConfidenceScore.from_float(confidence_value),
                location={
                    "page": 0,
                    "top": 0.1,
                    "left": 0.1,
                    "bottom": 0.15,
                    "right": 0.5,
                    "width": 0.4,
                    "height": 0.05
                },
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason="",
                extraction_timestamp="2023-01-01T12:00:00Z"
            )
        
        return ExtractedData(
            extraction_id="test-extraction-123",
            fields=fields,
            tables=[],
            metadata={
                "extraction_id": "test-extraction-123",
                "document_id": "doc-123",
                "model_id": "typed_text_v1",
                "model_version": "1.0",
                "document_type": "application_form",
                "page_count": 1,
                "language": "en",
                "processing_node": "node1",
                "extraction_status": "success",
                "processing_time": 1.5,
                "warnings": [],
                "errors": []
            },
            raw_text="Test extraction data",
            low_confidence_fields=[],
            requires_verification=False,
            extraction_timestamp="2023-01-01T12:00:00Z",
            schema_version="1.0",
            document_type="APPLICATION"
        )