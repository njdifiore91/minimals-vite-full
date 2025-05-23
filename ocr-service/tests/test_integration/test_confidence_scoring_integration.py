#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for confidence scoring across the OCR pipeline.

This module tests the integration of confidence scoring throughout the OCR pipeline,
verifying that confidence scores are correctly calculated, propagated through the system,
and used for decision-making about automation versus human review.

These tests ensure that the OCR Service meets the following requirements:
1. Include confidence scoring for extracted fields as specified in section 0.1.4
2. Flag low-confidence extractions for human verification as specified in section 4.1.8
3. Achieve 93% reduction in manual processing through automation as specified in section 0.1.1
4. Maintain 99% data extraction accuracy as specified in section 0.1.1
"""

import os
import json
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from pathlib import Path

# Import OCR service modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from models.confidence_scoring import (
    normalize_raw_confidence,
    calculate_field_confidence,
    get_confidence_level,
    requires_human_verification,
    enrich_field_with_confidence,
    calculate_document_confidence,
    adjust_thresholds_for_automation_rate
)
from services.confidence_service import ConfidenceService
from types.models import OCRModelType, ModelResult
from types.extraction import (
    ConfidenceScore,
    ExtractedField,
    ExtractedData,
    create_extracted_data
)


# ===== Test Confidence Calculation and Propagation =====

def test_confidence_calculation_integration(mock_ocr_service, mock_tensorflow_models):
    """Test that confidence scores are correctly calculated from raw OCR results."""
    # Create a mock OCR result with known confidence values
    mock_result = ModelResult(
        model_id="test-model",
        model_type=OCRModelType.TYPED,
        text="Dollar Funding LLC",
        confidence=0.85,
        word_confidences={
            "Dollar": 0.92,
            "Funding": 0.88,
            "LLC": 0.75
        }
    )
    
    # Mock the OCR service to return this result
    mock_ocr_service.process_text_region.return_value = mock_result
    
    # Calculate field confidence using the confidence_scoring module
    field_confidence = calculate_field_confidence(
        raw_confidence=mock_result.confidence,
        model_type=mock_result.model_type,
        field_type="text",
        char_variance=0.05
    )
    
    # Verify that confidence calculation produces expected results
    assert 0.0 <= field_confidence <= 1.0, "Confidence score should be between 0 and 1"
    assert field_confidence != mock_result.confidence, "Field confidence should be adjusted from raw confidence"
    
    # Verify that confidence level categorization works correctly
    confidence_level = get_confidence_level(field_confidence)
    assert confidence_level in ["high", "medium", "low", "very_low"], "Confidence level should be a valid category"
    
    # Verify that the confidence level matches the expected threshold
    if field_confidence >= 0.85:
        assert confidence_level == "high"
    elif field_confidence >= 0.65:
        assert confidence_level == "medium"
    elif field_confidence >= 0.40:
        assert confidence_level == "low"
    else:
        assert confidence_level == "very_low"


def test_confidence_propagation_through_extraction(mock_ocr_service):
    """Test that confidence scores are correctly propagated through the extraction process."""
    # Create a sample document path
    document_path = "test_document.pdf"
    
    # Create a sample extraction with varying confidence levels
    extracted_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.92, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.88, field_type="text"),
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.75, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.65, field_type="numeric"),
        ExtractedField(name="signature", value="John Smith", confidence=0.55, field_type="text")
    ]
    
    # Create extraction metadata
    metadata = {
        "document_id": "test-doc-123",
        "extraction_id": "test-ext-456",
        "document_type": "loan_application",
        "processing_time_ms": 1250,
        "model_version": "1.0.0"
    }
    
    # Create extracted data
    extracted_data = create_extracted_data(
        fields={field.name: field for field in extracted_fields},
        metadata=metadata
    )
    
    # Create a confidence service
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount"]
    }
    confidence_service = ConfidenceService(config)
    
    # Enrich the extracted data with confidence information
    enriched_data = confidence_service.enrich_with_confidence_data(extracted_data)
    
    # Verify that confidence metadata was added to the document
    assert "document_confidence" in enriched_data.metadata, "Document confidence should be added to metadata"
    assert "requires_verification" in enriched_data.metadata, "Verification flag should be added to metadata"
    assert "low_confidence_fields" in enriched_data.metadata, "Low confidence fields should be identified in metadata"
    
    # Verify that confidence metadata was added to each field
    for field_name, field in enriched_data.fields.items():
        assert "confidence_category" in field.metadata, f"Field {field_name} should have confidence category"
        assert "normalized_confidence" in field.metadata, f"Field {field_name} should have normalized confidence"
        assert "requires_verification" in field.metadata, f"Field {field_name} should have verification flag"
    
    # Verify that critical fields with lower confidence are flagged for verification
    for field_name in config["critical_fields"]:
        field = enriched_data.fields.get(field_name)
        if field and field.confidence < config["confidence_threshold_critical"]:
            assert field.metadata["requires_verification"], f"Critical field {field_name} with low confidence should require verification"


# ===== Test Decision-Making Based on Confidence Scores =====

def test_human_verification_decision_making(mock_ocr_service):
    """Test that the system correctly decides when human verification is required based on confidence scores."""
    # Create a confidence service with specific thresholds
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount", "business_name"]
    }
    confidence_service = ConfidenceService(config)
    
    # Test case 1: High confidence document that should not require verification
    high_confidence_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.95, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.92, field_type="text"),
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.88, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.90, field_type="numeric"),
        ExtractedField(name="signature", value="John Smith", confidence=0.85, field_type="text")
    ]
    
    high_confidence_data = create_extracted_data(
        fields={field.name: field for field in high_confidence_fields},
        metadata={"document_type": "loan_application"}
    )
    
    # Verify that high confidence document does not require verification
    assert not confidence_service.requires_human_verification(high_confidence_data), \
        "High confidence document should not require verification"
    
    # Test case 2: Document with low confidence critical fields that should require verification
    low_confidence_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.95, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.75, field_type="text"),  # Below critical threshold
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.88, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.80, field_type="numeric"),  # Below critical threshold
        ExtractedField(name="signature", value="John Smith", confidence=0.85, field_type="text")
    ]
    
    low_confidence_data = create_extracted_data(
        fields={field.name: field for field in low_confidence_fields},
        metadata={"document_type": "loan_application"}
    )
    
    # Verify that document with low confidence critical fields requires verification
    assert confidence_service.requires_human_verification(low_confidence_data), \
        "Document with low confidence critical fields should require verification"
    
    # Test case 3: Document with missing critical fields that should require verification
    missing_critical_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.95, field_type="text"),
        # tax_id is missing
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.88, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.90, field_type="numeric"),
        ExtractedField(name="signature", value="John Smith", confidence=0.85, field_type="text")
    ]
    
    missing_fields_data = create_extracted_data(
        fields={field.name: field for field in missing_critical_fields},
        metadata={"document_type": "loan_application"}
    )
    
    # Verify that document with missing critical fields requires verification
    assert confidence_service.requires_human_verification(missing_fields_data), \
        "Document with missing critical fields should require verification"
    
    # Test case 4: Document with too many low confidence fields that should require verification
    many_low_confidence_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.95, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.92, field_type="text"),
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.55, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.90, field_type="numeric"),
        ExtractedField(name="signature", value="John Smith", confidence=0.45, field_type="text"),
        ExtractedField(name="email", value="john@example.com", confidence=0.50, field_type="text"),
        ExtractedField(name="phone", value="555-123-4567", confidence=0.60, field_type="text")
    ]
    
    many_low_confidence_data = create_extracted_data(
        fields={field.name: field for field in many_low_confidence_fields},
        metadata={"document_type": "loan_application"}
    )
    
    # Verify that document with many low confidence fields requires verification
    assert confidence_service.requires_human_verification(many_low_confidence_data), \
        "Document with many low confidence fields should require verification"


def test_confidence_metrics_and_reporting(mock_ocr_service):
    """Test that confidence metrics are correctly calculated and reported for monitoring."""
    # Create a confidence service
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount"]
    }
    confidence_service = ConfidenceService(config)
    
    # Create sample extracted data with mixed confidence levels
    mixed_confidence_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.92, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.88, field_type="text"),
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.75, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.65, field_type="numeric"),
        ExtractedField(name="signature", value="John Smith", confidence=0.55, field_type="text")
    ]
    
    mixed_confidence_data = create_extracted_data(
        fields={field.name: field for field in mixed_confidence_fields},
        metadata={
            "document_type": "loan_application",
            "processing_time_ms": 1250,
            "model_version": "1.0.0"
        }
    )
    
    # Get confidence metrics
    metrics = confidence_service.get_confidence_metrics(mixed_confidence_data)
    
    # Verify that metrics contain expected information
    assert "document_confidence" in metrics, "Metrics should include document confidence"
    assert "requires_verification" in metrics, "Metrics should include verification flag"
    assert "low_confidence_field_count" in metrics, "Metrics should include low confidence field count"
    assert "confidence_by_field_type" in metrics, "Metrics should include confidence by field type"
    assert "critical_fields_confidence" in metrics, "Metrics should include critical fields confidence"
    assert "confidence_distribution" in metrics, "Metrics should include confidence distribution"
    
    # Verify that confidence distribution adds up to total field count
    distribution = metrics["confidence_distribution"]
    assert distribution["high"] + distribution["medium"] + distribution["low"] == len(mixed_confidence_fields), \
        "Confidence distribution should account for all fields"
    
    # Verify that critical fields are correctly identified in metrics
    for critical_field in config["critical_fields"]:
        if critical_field in [field.name for field in mixed_confidence_fields]:
            assert critical_field in metrics["critical_fields_confidence"], \
                f"Critical field {critical_field} should be included in metrics"


# ===== Test Confidence Threshold Adjustment =====

def test_confidence_threshold_adjustment_for_automation_target():
    """Test that confidence thresholds can be adjusted to meet the 93% automation target."""
    # Create initial thresholds
    current_thresholds = {
        "critical": 0.85,
        "standard": 0.65,
        "optional": 0.40
    }
    
    # Test case 1: Current automation rate is below target (90% vs 93%)
    adjusted_thresholds_1 = adjust_thresholds_for_automation_rate(
        current_automation_rate=0.90,
        target_automation_rate=0.93,
        current_thresholds=current_thresholds
    )
    
    # Verify that thresholds are lowered to increase automation rate
    assert adjusted_thresholds_1["critical"] < current_thresholds["critical"], \
        "Critical threshold should be lowered to increase automation rate"
    assert adjusted_thresholds_1["standard"] < current_thresholds["standard"], \
        "Standard threshold should be lowered to increase automation rate"
    assert adjusted_thresholds_1["optional"] < current_thresholds["optional"], \
        "Optional threshold should be lowered to increase automation rate"
    
    # Test case 2: Current automation rate is above target (95% vs 93%)
    adjusted_thresholds_2 = adjust_thresholds_for_automation_rate(
        current_automation_rate=0.95,
        target_automation_rate=0.93,
        current_thresholds=current_thresholds
    )
    
    # Verify that thresholds are raised to decrease automation rate
    assert adjusted_thresholds_2["critical"] > current_thresholds["critical"], \
        "Critical threshold should be raised to decrease automation rate"
    assert adjusted_thresholds_2["standard"] > current_thresholds["standard"], \
        "Standard threshold should be raised to decrease automation rate"
    assert adjusted_thresholds_2["optional"] > current_thresholds["optional"], \
        "Optional threshold should be raised to decrease automation rate"
    
    # Test case 3: Current automation rate is at target (93% vs 93%)
    adjusted_thresholds_3 = adjust_thresholds_for_automation_rate(
        current_automation_rate=0.93,
        target_automation_rate=0.93,
        current_thresholds=current_thresholds
    )
    
    # Verify that thresholds remain unchanged when at target
    assert adjusted_thresholds_3["critical"] == current_thresholds["critical"], \
        "Critical threshold should remain unchanged when at target"
    assert adjusted_thresholds_3["standard"] == current_thresholds["standard"], \
        "Standard threshold should remain unchanged when at target"
    assert adjusted_thresholds_3["optional"] == current_thresholds["optional"], \
        "Optional threshold should remain unchanged when at target"
    
    # Test case 4: Ensure critical threshold has a minimum value
    very_low_thresholds = {
        "critical": 0.82,  # Just above minimum
        "standard": 0.65,
        "optional": 0.40
    }
    
    adjusted_thresholds_4 = adjust_thresholds_for_automation_rate(
        current_automation_rate=0.90,
        target_automation_rate=0.93,
        current_thresholds=very_low_thresholds,
        min_critical_threshold=0.80
    )
    
    # Verify that critical threshold doesn't go below minimum
    assert adjusted_thresholds_4["critical"] >= 0.80, \
        "Critical threshold should not go below minimum value"


# ===== Test End-to-End Confidence Scoring Integration =====

def test_end_to_end_confidence_scoring_integration(mock_app, mock_queue_service, mock_storage_service, mock_ocr_service):
    """Test the end-to-end integration of confidence scoring in the OCR pipeline."""
    # Create a confidence service
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount", "business_name"]
    }
    confidence_service = ConfidenceService(config)
    
    # Set up the mock OCR service to return different confidence levels for different documents
    def simulate_ocr_with_confidence(document_path, document_type, confidence):
        return mock_ocr_service.simulate_ocr_processing(document_path, document_type, confidence)
    
    # Test with a high confidence document
    high_confidence_result = simulate_ocr_with_confidence(
        "high_confidence_doc.pdf", "loan_application", 0.95)
    
    # Enrich with confidence data
    high_confidence_enriched = confidence_service.enrich_with_confidence_data(high_confidence_result)
    
    # Verify that high confidence document does not require verification
    assert not high_confidence_enriched.metadata.get("requires_verification", False), \
        "High confidence document should not require verification"
    
    # Test with a low confidence document
    low_confidence_result = simulate_ocr_with_confidence(
        "low_confidence_doc.pdf", "loan_application", 0.65)
    
    # Enrich with confidence data
    low_confidence_enriched = confidence_service.enrich_with_confidence_data(low_confidence_result)
    
    # Verify that low confidence document requires verification
    assert low_confidence_enriched.metadata.get("requires_verification", False), \
        "Low confidence document should require verification"
    
    # Verify that verification reasons are provided
    assert "verification_reasons" in low_confidence_enriched.metadata, \
        "Verification reasons should be provided for low confidence document"
    
    # Verify that verification guidance is provided
    assert "verification_guidance" in low_confidence_enriched.metadata, \
        "Verification guidance should be provided for low confidence document"
    
    # Verify that the guidance includes priority and suggested focus
    guidance = low_confidence_enriched.metadata.get("verification_guidance", {})
    assert "priority" in guidance, "Verification guidance should include priority"
    assert "suggested_focus" in guidance, "Verification guidance should include suggested focus fields"


# ===== Test Confidence Scoring with Different Document Types =====

def test_confidence_scoring_with_different_document_types(mock_ocr_service):
    """Test that confidence scoring works correctly with different document types."""
    # Create a confidence service
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount", "account_number", "tax_year"],
        "doc_type_adjustments": {
            "loan_application": 1.0,  # Baseline
            "tax_return": 0.95,      # Tax returns are more complex
            "bank_statement": 0.92   # Bank statements have varied formats
        }
    }
    confidence_service = ConfidenceService(config)
    
    # Test with loan application document
    loan_app_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.85, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.85, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.85, field_type="numeric")
    ]
    
    loan_app_data = create_extracted_data(
        fields={field.name: field for field in loan_app_fields},
        metadata={"document_type": "loan_application"}
    )
    
    # Test with tax return document (same raw confidence, but different document type)
    tax_return_fields = [
        ExtractedField(name="taxpayer_name", value="Dollar Funding LLC", confidence=0.85, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.85, field_type="text"),
        ExtractedField(name="tax_year", value="2022", confidence=0.85, field_type="text")
    ]
    
    tax_return_data = create_extracted_data(
        fields={field.name: field for field in tax_return_fields},
        metadata={"document_type": "tax_return"}
    )
    
    # Test with bank statement document (same raw confidence, but different document type)
    bank_statement_fields = [
        ExtractedField(name="account_holder", value="Dollar Funding LLC", confidence=0.85, field_type="text"),
        ExtractedField(name="account_number", value="****1234", confidence=0.85, field_type="text"),
        ExtractedField(name="ending_balance", value="35678.90", confidence=0.85, field_type="numeric")
    ]
    
    bank_statement_data = create_extracted_data(
        fields={field.name: field for field in bank_statement_fields},
        metadata={"document_type": "bank_statement"}
    )
    
    # Calculate document confidence for each document type
    loan_app_confidence = confidence_service.calculate_document_confidence(loan_app_data)
    tax_return_confidence = confidence_service.calculate_document_confidence(tax_return_data)
    bank_statement_confidence = confidence_service.calculate_document_confidence(bank_statement_data)
    
    # Verify that document type adjustments are applied correctly
    # Loan application is baseline, tax return and bank statement should have lower confidence
    assert loan_app_confidence > tax_return_confidence, \
        "Loan application should have higher confidence than tax return with same raw scores"
    assert tax_return_confidence > bank_statement_confidence, \
        "Tax return should have higher confidence than bank statement with same raw scores"
    
    # Verify that the confidence differences match the adjustment factors
    assert abs((tax_return_confidence / loan_app_confidence) - 0.95) < 0.05, \
        "Tax return confidence adjustment should be approximately 0.95"
    assert abs((bank_statement_confidence / loan_app_confidence) - 0.92) < 0.05, \
        "Bank statement confidence adjustment should be approximately 0.92"


# ===== Test Confidence Scoring with Field Importance =====

def test_confidence_scoring_with_field_importance(mock_ocr_service):
    """Test that confidence scoring correctly weights fields by importance."""
    # Create a confidence service with field importance weights
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount"],
        "field_importance": {
            "loan_application": {
                "business_name": 2.0,
                "tax_id": 2.5,
                "requested_amount": 2.0,
                "address": 1.0,
                "signature": 1.5
            }
        }
    }
    confidence_service = ConfidenceService(config)
    
    # Test case 1: Document with high confidence in important fields
    important_fields_high_confidence = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.95, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.92, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.90, field_type="numeric"),
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.70, field_type="text"),
        ExtractedField(name="signature", value="John Smith", confidence=0.65, field_type="text")
    ]
    
    important_high_data = create_extracted_data(
        fields={field.name: field for field in important_fields_high_confidence},
        metadata={"document_type": "loan_application"}
    )
    
    # Test case 2: Document with low confidence in important fields
    important_fields_low_confidence = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.70, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.65, field_type="text"),
        ExtractedField(name="requested_amount", value="50000", confidence=0.60, field_type="numeric"),
        ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=0.90, field_type="text"),
        ExtractedField(name="signature", value="John Smith", confidence=0.95, field_type="text")
    ]
    
    important_low_data = create_extracted_data(
        fields={field.name: field for field in important_fields_low_confidence},
        metadata={"document_type": "loan_application"}
    )
    
    # Calculate document confidence for both cases
    important_high_confidence = confidence_service.calculate_document_confidence(important_high_data)
    important_low_confidence = confidence_service.calculate_document_confidence(important_low_data)
    
    # Verify that document with high confidence in important fields has higher overall confidence
    assert important_high_confidence > important_low_confidence, \
        "Document with high confidence in important fields should have higher overall confidence"
    
    # Verify that the difference is significant due to field importance weighting
    assert (important_high_confidence - important_low_confidence) > 0.15, \
        "Difference in document confidence should be significant due to field importance weighting"
    
    # Verify verification decisions
    assert not confidence_service.requires_human_verification(important_high_data), \
        "Document with high confidence in important fields should not require verification"
    assert confidence_service.requires_human_verification(important_low_data), \
        "Document with low confidence in important fields should require verification"


# ===== Test Confidence Scoring with Suspicious Patterns =====

def test_confidence_scoring_with_suspicious_patterns(mock_ocr_service):
    """Test that confidence scoring correctly identifies suspicious patterns in extracted data."""
    # Create a confidence service
    config = {
        "confidence_threshold_high": 0.85,
        "confidence_threshold_medium": 0.65,
        "confidence_threshold_low": 0.40,
        "confidence_threshold_critical": 0.85,
        "critical_fields": ["tax_id", "requested_amount"]
    }
    confidence_service = ConfidenceService(config)
    
    # Test case: Document with suspicious numeric patterns (inconsistent financial data)
    suspicious_fields = [
        ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=0.95, field_type="text"),
        ExtractedField(name="tax_id", value="12-3456789", confidence=0.92, field_type="text"),
        # Suspicious pattern: Beginning balance + deposits - withdrawals != ending balance
        ExtractedField(name="beginning_balance", value="10000.00", confidence=0.90, field_type="numeric"),
        ExtractedField(name="total_deposits", value="5000.00", confidence=0.90, field_type="numeric"),
        ExtractedField(name="total_withdrawals", value="2000.00", confidence=0.90, field_type="numeric"),
        ExtractedField(name="ending_balance", value="15000.00", confidence=0.90, field_type="numeric")  # Should be 13000.00
    ]
    
    suspicious_data = create_extracted_data(
        fields={field.name: field for field in suspicious_fields},
        metadata={"document_type": "bank_statement"}
    )
    
    # Check if suspicious patterns are detected
    suspicious_patterns = confidence_service._check_suspicious_patterns(suspicious_data)
    
    # Verify that suspicious patterns are detected
    assert len(suspicious_patterns) > 0, "Suspicious patterns should be detected"
    
    # Verify that document with suspicious patterns requires verification
    assert confidence_service.requires_human_verification(suspicious_data), \
        "Document with suspicious patterns should require verification"
    
    # Verify that verification reasons include suspicious patterns
    confidence_service.requires_human_verification(suspicious_data)  # This populates verification_reasons
    verification_reasons = suspicious_data.metadata.get("verification_reasons", [])
    
    suspicious_pattern_reason = next((reason for reason in verification_reasons 
                                     if "suspicious" in reason.lower()), None)
    assert suspicious_pattern_reason is not None, \
        "Verification reasons should include suspicious patterns"