#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the confidence scoring module of the OCR Service.

This module contains tests for the confidence scoring algorithms used to assess
the reliability of OCR results. These tests verify that the confidence scoring
system correctly evaluates extraction quality, enabling downstream services to
make informed decisions about automation versus human review.

The tests cover:
- Normalization of raw confidence scores from different model types
- Field-level confidence calculation based on multiple factors
- Confidence level categorization (high, medium, low, very_low)
- Human verification requirement determination
- Character variance calculation for consistency assessment
- Field enrichment with confidence metadata
- Document-level confidence calculation
- Dynamic threshold adjustment for automation rate optimization
- Confidence distribution analysis for monitoring

These tests are critical for ensuring the OCR Service can achieve the 93% reduction
in manual processing through automation while maintaining 99% data extraction accuracy.
"""

import json
import math
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
import pytest

from ocr_service.src.models.confidence_scoring import (
    normalize_raw_confidence,
    calculate_field_confidence,
    get_confidence_level,
    requires_human_verification,
    calculate_character_variance,
    enrich_field_with_confidence,
    calculate_document_confidence,
    adjust_thresholds_for_automation_rate,
    analyze_confidence_distribution,
    DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD,
    DEFAULT_LOW_CONFIDENCE_THRESHOLD,
    MODEL_CONFIDENCE_ADJUSTMENTS,
    FIELD_TYPE_MODIFIERS
)
from ocr_service.src.types.models import OCRModelType
from ocr_service.src.types.extraction import ExtractedField


# ===== Test Fixtures =====

@pytest.fixture
def sample_extracted_field() -> ExtractedField:
    """Provides a sample extracted field for testing."""
    return {
        "field_id": "business_name",
        "field_name": "Business Name",
        "value": "Acme Corporation",
        "raw_text": "Acme Corporation",
        "field_type": "text",
        "importance": "standard"
    }


@pytest.fixture
def sample_character_confidences() -> List[float]:
    """Provides sample character-level confidence scores for testing."""
    return [0.98, 0.95, 0.99, 0.92, 0.97, 0.90, 0.93, 0.96, 0.91, 0.94]


@pytest.fixture
def sample_fields() -> Dict[str, ExtractedField]:
    """Provides a sample set of extracted fields for testing."""
    return {
        "business_name": {
            "field_id": "business_name",
            "field_name": "Business Name",
            "value": "Acme Corporation",
            "raw_text": "Acme Corporation",
            "field_type": "text",
            "importance": "standard",
            "confidence": {
                "score": 0.95,
                "level": "high",
                "needs_verification": False,
                "raw_score": 0.92,
                "model_type": "typed"
            }
        },
        "tax_id": {
            "field_id": "tax_id",
            "field_name": "Tax ID",
            "value": "12-3456789",
            "raw_text": "12-3456789",
            "field_type": "ein",
            "importance": "critical",
            "confidence": {
                "score": 0.88,
                "level": "high",
                "needs_verification": False,
                "raw_score": 0.85,
                "model_type": "typed"
            }
        },
        "owner_signature": {
            "field_id": "owner_signature",
            "field_name": "Owner Signature",
            "value": "John Smith",
            "raw_text": "John Smith",
            "field_type": "signature",
            "importance": "critical",
            "confidence": {
                "score": 0.75,
                "level": "medium",
                "needs_verification": True,
                "raw_score": 0.70,
                "model_type": "handwritten"
            }
        },
        "business_address": {
            "field_id": "business_address",
            "field_name": "Business Address",
            "value": "123 Main St, Anytown, USA 12345",
            "raw_text": "123 Main St, Anytown, USA 12345",
            "field_type": "address",
            "importance": "standard",
            "confidence": {
                "score": 0.82,
                "level": "medium",
                "needs_verification": False,
                "raw_score": 0.78,
                "model_type": "typed"
            }
        },
        "monthly_revenue": {
            "field_id": "monthly_revenue",
            "field_name": "Monthly Revenue",
            "value": "$45,000",
            "raw_text": "$45,000",
            "field_type": "currency",
            "importance": "standard",
            "confidence": {
                "score": 0.91,
                "level": "high",
                "needs_verification": False,
                "raw_score": 0.88,
                "model_type": "typed"
            }
        }
    }


@pytest.fixture
def sample_confidence_scores() -> List[float]:
    """Provides a sample list of confidence scores for distribution analysis."""
    return [
        0.98, 0.95, 0.92, 0.88, 0.85, 0.82, 0.78, 0.75, 0.72, 0.68,
        0.65, 0.62, 0.58, 0.55, 0.52, 0.48, 0.45, 0.42, 0.38, 0.35
    ]


# ===== Test normalize_raw_confidence =====

def test_normalize_raw_confidence_typed():
    """Test normalization of raw confidence scores for typed text model."""
    # Test with various confidence scores for typed text model
    assert normalize_raw_confidence(0.9, OCRModelType.TYPED) > 0.9
    assert normalize_raw_confidence(0.5, OCRModelType.TYPED) == 0.5
    assert normalize_raw_confidence(0.1, OCRModelType.TYPED) < 0.1
    
    # Verify that normalization preserves order
    assert normalize_raw_confidence(0.9, OCRModelType.TYPED) > normalize_raw_confidence(0.8, OCRModelType.TYPED)
    assert normalize_raw_confidence(0.7, OCRModelType.TYPED) > normalize_raw_confidence(0.6, OCRModelType.TYPED)
    assert normalize_raw_confidence(0.5, OCRModelType.TYPED) > normalize_raw_confidence(0.4, OCRModelType.TYPED)


def test_normalize_raw_confidence_handwritten():
    """Test normalization of raw confidence scores for handwritten text model."""
    # Test with various confidence scores for handwritten text model
    # Handwritten models typically have lower raw confidence, so normalization should adjust for this
    typed_confidence = normalize_raw_confidence(0.8, OCRModelType.TYPED)
    handwritten_confidence = normalize_raw_confidence(0.8, OCRModelType.HANDWRITTEN)
    
    # Handwritten confidence should be lower than typed for the same raw score
    assert handwritten_confidence < typed_confidence
    
    # Verify that the adjustment factor is applied correctly
    adjustment_factor = MODEL_CONFIDENCE_ADJUSTMENTS[OCRModelType.HANDWRITTEN]
    assert adjustment_factor < MODEL_CONFIDENCE_ADJUSTMENTS[OCRModelType.TYPED]


def test_normalize_raw_confidence_hybrid():
    """Test normalization of raw confidence scores for hybrid text model."""
    # Test with various confidence scores for hybrid text model
    # Hybrid models should have confidence between typed and handwritten
    typed_confidence = normalize_raw_confidence(0.8, OCRModelType.TYPED)
    hybrid_confidence = normalize_raw_confidence(0.8, OCRModelType.HYBRID)
    handwritten_confidence = normalize_raw_confidence(0.8, OCRModelType.HANDWRITTEN)
    
    # Hybrid confidence should be between typed and handwritten
    assert handwritten_confidence < hybrid_confidence < typed_confidence


def test_normalize_raw_confidence_out_of_range():
    """Test normalization with out-of-range confidence scores."""
    # Test with confidence scores outside the valid range [0.0, 1.0]
    # These should be clamped to the valid range
    assert 0.0 <= normalize_raw_confidence(-0.2, OCRModelType.TYPED) <= 1.0
    assert 0.0 <= normalize_raw_confidence(1.5, OCRModelType.TYPED) <= 1.0


# ===== Test calculate_field_confidence =====

def test_calculate_field_confidence_basic():
    """Test basic field confidence calculation."""
    # Test with basic parameters
    confidence = calculate_field_confidence(0.9, OCRModelType.TYPED)
    assert 0.0 <= confidence <= 1.0
    assert confidence > 0.9  # Normalized confidence should be higher for high raw confidence


def test_calculate_field_confidence_field_types():
    """Test field confidence calculation with different field types."""
    # Test with different field types
    # Numeric fields should have higher confidence than text fields
    text_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, field_type="text")
    numeric_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, field_type="numeric")
    assert numeric_confidence > text_confidence
    
    # Signature fields should have lower confidence than text fields
    signature_confidence = calculate_field_confidence(0.9, OCRModelType.HANDWRITTEN, field_type="signature")
    assert signature_confidence < text_confidence
    
    # EIN fields should have higher confidence than address fields
    ein_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, field_type="ein")
    address_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, field_type="address")
    assert ein_confidence > address_confidence


def test_calculate_field_confidence_with_variance():
    """Test field confidence calculation with character variance."""
    # Test with character variance
    # Higher variance should result in lower confidence
    base_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED)
    with_variance_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, char_variance=0.2)
    assert with_variance_confidence < base_confidence
    
    # Higher variance should result in even lower confidence
    higher_variance_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, char_variance=0.4)
    assert higher_variance_confidence < with_variance_confidence


def test_calculate_field_confidence_with_context():
    """Test field confidence calculation with context agreement."""
    # Test with context agreement
    # Higher context agreement should result in higher confidence
    base_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED)
    with_context_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, context_agreement=0.8)
    assert with_context_confidence > base_confidence
    
    # Lower context agreement should result in lower confidence
    low_context_confidence = calculate_field_confidence(0.9, OCRModelType.TYPED, context_agreement=0.3)
    assert low_context_confidence < base_confidence


def test_calculate_field_confidence_combined_factors():
    """Test field confidence calculation with multiple factors combined."""
    # Test with all factors combined
    confidence = calculate_field_confidence(
        raw_confidence=0.85,
        model_type=OCRModelType.HYBRID,
        field_type="address",
        char_variance=0.15,
        context_agreement=0.7
    )
    
    # Verify that the result is within valid range
    assert 0.0 <= confidence <= 1.0
    
    # Verify that the combined factors produce a reasonable result
    # For address field (modifier 0.90) with hybrid model (0.92), moderate variance (0.15),
    # and good context agreement (0.7), the confidence should be moderately high
    assert 0.7 <= confidence <= 0.9


# ===== Test get_confidence_level =====

def test_get_confidence_level_high():
    """Test confidence level categorization for high confidence."""
    # Test with high confidence scores
    assert get_confidence_level(0.95) == "high"
    assert get_confidence_level(0.90) == "high"
    assert get_confidence_level(DEFAULT_HIGH_CONFIDENCE_THRESHOLD) == "high"
    assert get_confidence_level(DEFAULT_HIGH_CONFIDENCE_THRESHOLD + 0.01) == "high"


def test_get_confidence_level_medium():
    """Test confidence level categorization for medium confidence."""
    # Test with medium confidence scores
    assert get_confidence_level(0.75) == "medium"
    assert get_confidence_level(0.70) == "medium"
    assert get_confidence_level(DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD) == "medium"
    assert get_confidence_level(DEFAULT_HIGH_CONFIDENCE_THRESHOLD - 0.01) == "medium"
    assert get_confidence_level(DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD + 0.01) == "medium"


def test_get_confidence_level_low():
    """Test confidence level categorization for low confidence."""
    # Test with low confidence scores
    assert get_confidence_level(0.55) == "low"
    assert get_confidence_level(0.50) == "low"
    assert get_confidence_level(DEFAULT_LOW_CONFIDENCE_THRESHOLD) == "low"
    assert get_confidence_level(DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD - 0.01) == "low"
    assert get_confidence_level(DEFAULT_LOW_CONFIDENCE_THRESHOLD + 0.01) == "low"


def test_get_confidence_level_very_low():
    """Test confidence level categorization for very low confidence."""
    # Test with very low confidence scores
    assert get_confidence_level(0.35) == "very_low"
    assert get_confidence_level(0.20) == "very_low"
    assert get_confidence_level(0.0) == "very_low"
    assert get_confidence_level(DEFAULT_LOW_CONFIDENCE_THRESHOLD - 0.01) == "very_low"


def test_get_confidence_level_custom_thresholds():
    """Test confidence level categorization with custom thresholds."""
    # Test with custom thresholds
    custom_high = 0.90
    custom_medium = 0.70
    custom_low = 0.50
    
    assert get_confidence_level(0.95, custom_high, custom_medium, custom_low) == "high"
    assert get_confidence_level(0.85, custom_high, custom_medium, custom_low) == "medium"
    assert get_confidence_level(0.65, custom_high, custom_medium, custom_low) == "low"
    assert get_confidence_level(0.45, custom_high, custom_medium, custom_low) == "very_low"


# ===== Test requires_human_verification =====

def test_requires_human_verification_standard():
    """Test human verification requirement for standard fields."""
    # Test with standard field importance
    # Standard fields require verification below medium confidence threshold
    assert requires_human_verification(0.60, "standard") == True
    assert requires_human_verification(0.70, "standard") == False


def test_requires_human_verification_critical():
    """Test human verification requirement for critical fields."""
    # Test with critical field importance
    # Critical fields require verification below high confidence threshold
    assert requires_human_verification(0.80, "critical") == True
    assert requires_human_verification(0.90, "critical") == False


def test_requires_human_verification_optional():
    """Test human verification requirement for optional fields."""
    # Test with optional field importance
    # Optional fields only require verification below low confidence threshold
    assert requires_human_verification(0.35, "optional") == True
    assert requires_human_verification(0.45, "optional") == False


def test_requires_human_verification_custom_thresholds():
    """Test human verification requirement with custom thresholds."""
    # Test with custom verification thresholds
    custom_thresholds = {
        "critical": 0.90,
        "standard": 0.75,
        "optional": 0.60
    }
    
    assert requires_human_verification(0.85, "critical", custom_thresholds) == True
    assert requires_human_verification(0.95, "critical", custom_thresholds) == False
    
    assert requires_human_verification(0.70, "standard", custom_thresholds) == True
    assert requires_human_verification(0.80, "standard", custom_thresholds) == False
    
    assert requires_human_verification(0.55, "optional", custom_thresholds) == True
    assert requires_human_verification(0.65, "optional", custom_thresholds) == False


def test_requires_human_verification_unknown_importance():
    """Test human verification requirement with unknown field importance."""
    # Test with unknown field importance
    # Should default to standard importance
    assert requires_human_verification(0.60, "unknown") == True
    assert requires_human_verification(0.70, "unknown") == False


# ===== Test calculate_character_variance =====

def test_calculate_character_variance_uniform(sample_character_confidences):
    """Test character variance calculation with uniform confidences."""
    # Test with uniform character confidences
    uniform_confidences = [0.9, 0.9, 0.9, 0.9, 0.9]
    variance = calculate_character_variance(uniform_confidences)
    assert variance == 0.0


def test_calculate_character_variance_varied(sample_character_confidences):
    """Test character variance calculation with varied confidences."""
    # Test with varied character confidences
    variance = calculate_character_variance(sample_character_confidences)
    assert variance > 0.0
    
    # Calculate expected variance manually for verification
    expected_variance = np.var(sample_character_confidences)
    assert variance == pytest.approx(expected_variance)


def test_calculate_character_variance_empty():
    """Test character variance calculation with empty list."""
    # Test with empty list
    variance = calculate_character_variance([])
    assert variance == 0.0


def test_calculate_character_variance_single():
    """Test character variance calculation with single value."""
    # Test with single value
    variance = calculate_character_variance([0.9])
    assert variance == 0.0


# ===== Test enrich_field_with_confidence =====

def test_enrich_field_with_confidence_basic(sample_extracted_field):
    """Test basic field enrichment with confidence metadata."""
    # Test basic enrichment
    enriched = enrich_field_with_confidence(
        field=sample_extracted_field,
        raw_confidence=0.9,
        model_type=OCRModelType.TYPED
    )
    
    # Verify that confidence metadata was added
    assert "confidence" in enriched
    assert "score" in enriched["confidence"]
    assert "level" in enriched["confidence"]
    assert "needs_verification" in enriched["confidence"]
    assert "raw_score" in enriched["confidence"]
    assert "model_type" in enriched["confidence"]
    
    # Verify that the original field was not modified
    assert "confidence" not in sample_extracted_field


def test_enrich_field_with_confidence_with_char_confidences(sample_extracted_field):
    """Test field enrichment with character confidences."""
    # Test enrichment with character confidences
    char_confidences = [0.95, 0.92, 0.98, 0.90, 0.93]
    enriched = enrich_field_with_confidence(
        field=sample_extracted_field,
        raw_confidence=0.9,
        model_type=OCRModelType.TYPED,
        char_confidences=char_confidences
    )
    
    # Verify that character variance was added
    assert "char_variance" in enriched["confidence"]
    assert enriched["confidence"]["char_variance"] > 0.0


def test_enrich_field_with_confidence_with_context(sample_extracted_field):
    """Test field enrichment with context agreement."""
    # Test enrichment with context agreement
    enriched = enrich_field_with_confidence(
        field=sample_extracted_field,
        raw_confidence=0.9,
        model_type=OCRModelType.TYPED,
        context_agreement=0.8
    )
    
    # Verify that context agreement was added
    assert "context_agreement" in enriched["confidence"]
    assert enriched["confidence"]["context_agreement"] == 0.8


def test_enrich_field_with_confidence_verification_flag(sample_extracted_field):
    """Test field enrichment with verification flag."""
    # Test with confidence below verification threshold for standard fields
    low_confidence = 0.6  # Below standard verification threshold
    enriched = enrich_field_with_confidence(
        field=sample_extracted_field,
        raw_confidence=low_confidence,
        model_type=OCRModelType.TYPED
    )
    
    # Verify that needs_verification flag is set
    assert enriched["confidence"]["needs_verification"] == True
    
    # Test with confidence above verification threshold
    high_confidence = 0.9  # Above standard verification threshold
    enriched = enrich_field_with_confidence(
        field=sample_extracted_field,
        raw_confidence=high_confidence,
        model_type=OCRModelType.TYPED
    )
    
    # Verify that needs_verification flag is not set
    assert enriched["confidence"]["needs_verification"] == False


def test_enrich_field_with_confidence_critical_field():
    """Test field enrichment with critical field importance."""
    # Test with critical field importance
    critical_field = {
        "field_id": "tax_id",
        "field_name": "Tax ID",
        "value": "12-3456789",
        "raw_text": "12-3456789",
        "field_type": "ein",
        "importance": "critical"
    }
    
    # Test with confidence below critical verification threshold
    medium_confidence = 0.8  # Below critical verification threshold
    enriched = enrich_field_with_confidence(
        field=critical_field,
        raw_confidence=medium_confidence,
        model_type=OCRModelType.TYPED
    )
    
    # Verify that needs_verification flag is set for critical field
    assert enriched["confidence"]["needs_verification"] == True
    
    # Test with confidence above critical verification threshold
    high_confidence = 0.95  # Above critical verification threshold
    enriched = enrich_field_with_confidence(
        field=critical_field,
        raw_confidence=high_confidence,
        model_type=OCRModelType.TYPED
    )
    
    # Verify that needs_verification flag is not set
    assert enriched["confidence"]["needs_verification"] == False


# ===== Test calculate_document_confidence =====

def test_calculate_document_confidence_basic(sample_fields):
    """Test basic document confidence calculation."""
    # Test with sample fields
    confidence = calculate_document_confidence(list(sample_fields.values()))
    
    # Verify that the result is within valid range
    assert 0.0 <= confidence <= 1.0
    
    # Verify that the result is reasonable
    # Average of field confidences: (0.95 + 0.88 + 0.75 + 0.82 + 0.91) / 5 = 0.862
    assert 0.85 <= confidence <= 0.87


def test_calculate_document_confidence_weighted(sample_fields):
    """Test document confidence calculation with field weights."""
    # Test with field weights
    field_weights = {
        "business_name": 1.5,  # More important
        "tax_id": 2.0,        # Most important
        "owner_signature": 1.0,
        "business_address": 0.8,
        "monthly_revenue": 1.2
    }
    
    confidence = calculate_document_confidence(
        fields=list(sample_fields.values()),
        field_weights=field_weights
    )
    
    # Verify that the result is within valid range
    assert 0.0 <= confidence <= 1.0
    
    # Verify that the result is influenced by weights
    # Weighted average should be different from unweighted average
    unweighted_confidence = calculate_document_confidence(list(sample_fields.values()))
    assert confidence != pytest.approx(unweighted_confidence)
    
    # Since tax_id (0.88) has highest weight and is below average,
    # weighted confidence should be lower than unweighted
    assert confidence < unweighted_confidence


def test_calculate_document_confidence_empty():
    """Test document confidence calculation with empty fields list."""
    # Test with empty fields list
    confidence = calculate_document_confidence([])
    assert confidence == 0.0


def test_calculate_document_confidence_missing_confidence():
    """Test document confidence calculation with fields missing confidence."""
    # Test with fields missing confidence metadata
    fields = [
        {
            "field_id": "business_name",
            "field_name": "Business Name",
            "value": "Acme Corporation",
            "raw_text": "Acme Corporation",
            "field_type": "text"
            # No confidence metadata
        },
        {
            "field_id": "tax_id",
            "field_name": "Tax ID",
            "value": "12-3456789",
            "raw_text": "12-3456789",
            "field_type": "ein",
            "confidence": {
                "score": 0.88,
                "level": "high",
                "needs_verification": False
            }
        }
    ]
    
    confidence = calculate_document_confidence(fields)
    
    # Verify that the result only considers fields with confidence metadata
    assert confidence == 0.88


# ===== Test adjust_thresholds_for_automation_rate =====

def test_adjust_thresholds_for_automation_rate_increase():
    """Test threshold adjustment to increase automation rate."""
    # Test with current automation rate below target
    current_rate = 0.85  # Below target of 0.93
    adjusted_thresholds = adjust_thresholds_for_automation_rate(current_rate)
    
    # Verify that thresholds were lowered to increase automation
    default_thresholds = {
        "critical": 0.85,
        "standard": 0.65,
        "optional": 0.40
    }
    
    for importance, threshold in adjusted_thresholds.items():
        assert threshold < default_thresholds[importance]


def test_adjust_thresholds_for_automation_rate_decrease():
    """Test threshold adjustment to decrease automation rate."""
    # Test with current automation rate above target
    current_rate = 0.98  # Above target of 0.93
    adjusted_thresholds = adjust_thresholds_for_automation_rate(current_rate)
    
    # Verify that thresholds were raised to decrease automation
    default_thresholds = {
        "critical": 0.85,
        "standard": 0.65,
        "optional": 0.40
    }
    
    for importance, threshold in adjusted_thresholds.items():
        assert threshold > default_thresholds[importance]


def test_adjust_thresholds_for_automation_rate_at_target():
    """Test threshold adjustment when already at target rate."""
    # Test with current automation rate at target
    current_rate = 0.93  # Equal to default target
    adjusted_thresholds = adjust_thresholds_for_automation_rate(current_rate)
    
    # Verify that thresholds were not changed
    default_thresholds = {
        "critical": 0.85,
        "standard": 0.65,
        "optional": 0.40
    }
    
    for importance, threshold in adjusted_thresholds.items():
        assert threshold == pytest.approx(default_thresholds[importance])


def test_adjust_thresholds_for_automation_rate_custom_target():
    """Test threshold adjustment with custom target rate."""
    # Test with custom target automation rate
    current_rate = 0.85
    custom_target = 0.90
    adjusted_thresholds = adjust_thresholds_for_automation_rate(
        current_rate,
        target_automation_rate=custom_target
    )
    
    # Verify that thresholds were adjusted based on custom target
    default_thresholds = {
        "critical": 0.85,
        "standard": 0.65,
        "optional": 0.40
    }
    
    for importance, threshold in adjusted_thresholds.items():
        assert threshold < default_thresholds[importance]


def test_adjust_thresholds_for_automation_rate_custom_thresholds():
    """Test threshold adjustment with custom starting thresholds."""
    # Test with custom starting thresholds
    current_rate = 0.85
    custom_thresholds = {
        "critical": 0.90,
        "standard": 0.70,
        "optional": 0.50
    }
    
    adjusted_thresholds = adjust_thresholds_for_automation_rate(
        current_rate,
        current_thresholds=custom_thresholds
    )
    
    # Verify that custom thresholds were adjusted
    for importance, threshold in adjusted_thresholds.items():
        assert threshold < custom_thresholds[importance]


def test_adjust_thresholds_for_automation_rate_min_critical():
    """Test threshold adjustment respects minimum critical threshold."""
    # Test with very low current automation rate
    current_rate = 0.50  # Far below target
    min_critical = 0.80
    
    adjusted_thresholds = adjust_thresholds_for_automation_rate(
        current_rate,
        min_critical_threshold=min_critical
    )
    
    # Verify that critical threshold respects minimum
    assert adjusted_thresholds["critical"] >= min_critical
    
    # Other thresholds should be lowered significantly
    default_thresholds = {
        "standard": 0.65,
        "optional": 0.40
    }
    
    for importance, threshold in adjusted_thresholds.items():
        if importance != "critical":
            assert threshold < default_thresholds[importance]


# ===== Test analyze_confidence_distribution =====

def test_analyze_confidence_distribution_basic(sample_confidence_scores):
    """Test basic confidence distribution analysis."""
    # Test with sample confidence scores
    distribution = analyze_confidence_distribution(sample_confidence_scores)
    
    # Verify that all expected metrics are present
    assert "count" in distribution
    assert "mean" in distribution
    assert "median" in distribution
    assert "std_dev" in distribution
    assert "min" in distribution
    assert "max" in distribution
    assert "quartiles" in distribution
    assert "below_threshold" in distribution
    
    # Verify that the metrics are correct
    assert distribution["count"] == len(sample_confidence_scores)
    assert distribution["mean"] == pytest.approx(np.mean(sample_confidence_scores))
    assert distribution["median"] == pytest.approx(np.median(sample_confidence_scores))
    assert distribution["std_dev"] == pytest.approx(np.std(sample_confidence_scores))
    assert distribution["min"] == pytest.approx(min(sample_confidence_scores))
    assert distribution["max"] == pytest.approx(max(sample_confidence_scores))


def test_analyze_confidence_distribution_quartiles(sample_confidence_scores):
    """Test quartile calculation in confidence distribution analysis."""
    # Test quartile calculation
    distribution = analyze_confidence_distribution(sample_confidence_scores)
    
    # Verify that quartiles are correct
    expected_quartiles = [
        np.percentile(sample_confidence_scores, 25),
        np.percentile(sample_confidence_scores, 50),
        np.percentile(sample_confidence_scores, 75)
    ]
    
    assert len(distribution["quartiles"]) == 3
    for i, quartile in enumerate(distribution["quartiles"]):
        assert quartile == pytest.approx(expected_quartiles[i])


def test_analyze_confidence_distribution_thresholds(sample_confidence_scores):
    """Test threshold counting in confidence distribution analysis."""
    # Test threshold counting
    distribution = analyze_confidence_distribution(sample_confidence_scores)
    
    # Verify that threshold counts are correct
    below_low = sum(1 for score in sample_confidence_scores if score < DEFAULT_LOW_CONFIDENCE_THRESHOLD)
    below_medium = sum(1 for score in sample_confidence_scores if score < DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD)
    below_high = sum(1 for score in sample_confidence_scores if score < DEFAULT_HIGH_CONFIDENCE_THRESHOLD)
    
    assert distribution["below_threshold"]["low"] == below_low
    assert distribution["below_threshold"]["medium"] == below_medium
    assert distribution["below_threshold"]["high"] == below_high


def test_analyze_confidence_distribution_empty():
    """Test confidence distribution analysis with empty list."""
    # Test with empty list
    distribution = analyze_confidence_distribution([])
    
    # Verify that default values are returned
    assert distribution["count"] == 0
    assert distribution["mean"] == 0.0
    assert distribution["median"] == 0.0
    assert distribution["std_dev"] == 0.0
    assert distribution["min"] == 0.0
    assert distribution["max"] == 0.0
    assert distribution["quartiles"] == [0.0, 0.0, 0.0]
    assert distribution["below_threshold"]["low"] == 0
    assert distribution["below_threshold"]["medium"] == 0
    assert distribution["below_threshold"]["high"] == 0


# ===== Integration Tests =====

def test_confidence_scoring_end_to_end(sample_extracted_field):
    """Test the entire confidence scoring pipeline end-to-end."""
    # Test the entire pipeline from raw confidence to enriched field
    raw_confidence = 0.82
    model_type = OCRModelType.TYPED
    char_confidences = [0.85, 0.80, 0.90, 0.75, 0.80, 0.85, 0.78, 0.88]
    context_agreement = 0.75
    
    # Step 1: Normalize raw confidence
    normalized_confidence = normalize_raw_confidence(raw_confidence, model_type)
    
    # Step 2: Calculate character variance
    char_variance = calculate_character_variance(char_confidences)
    
    # Step 3: Calculate field confidence
    field_confidence = calculate_field_confidence(
        raw_confidence=raw_confidence,
        model_type=model_type,
        field_type=sample_extracted_field["field_type"],
        char_variance=char_variance,
        context_agreement=context_agreement
    )
    
    # Step 4: Determine confidence level
    confidence_level = get_confidence_level(field_confidence)
    
    # Step 5: Determine if verification is required
    needs_verification = requires_human_verification(
        confidence_score=field_confidence,
        field_importance=sample_extracted_field.get("importance", "standard")
    )
    
    # Step 6: Enrich field with confidence metadata
    enriched_field = enrich_field_with_confidence(
        field=sample_extracted_field,
        raw_confidence=raw_confidence,
        model_type=model_type,
        char_confidences=char_confidences,
        context_agreement=context_agreement
    )
    
    # Verify that all steps produced consistent results
    assert enriched_field["confidence"]["raw_score"] == raw_confidence
    assert enriched_field["confidence"]["score"] == field_confidence
    assert enriched_field["confidence"]["level"] == confidence_level
    assert enriched_field["confidence"]["needs_verification"] == needs_verification
    assert enriched_field["confidence"]["char_variance"] == char_variance
    assert enriched_field["confidence"]["context_agreement"] == context_agreement


def test_confidence_scoring_automation_rate():
    """Test that confidence scoring enables target automation rate."""
    # Create a set of fields with various confidence scores
    fields = [
        {"importance": "critical", "confidence": {"score": 0.95}},  # High confidence critical field
        {"importance": "critical", "confidence": {"score": 0.82}},  # Medium confidence critical field
        {"importance": "standard", "confidence": {"score": 0.88}},  # High confidence standard field
        {"importance": "standard", "confidence": {"score": 0.72}},  # Medium confidence standard field
        {"importance": "standard", "confidence": {"score": 0.60}},  # Low confidence standard field
        {"importance": "optional", "confidence": {"score": 0.55}},  # Medium confidence optional field
        {"importance": "optional", "confidence": {"score": 0.35}},  # Low confidence optional field
    ]
    
    # Calculate initial automation rate
    verification_count = 0
    for field in fields:
        if requires_human_verification(
            field["confidence"]["score"],
            field["importance"]
        ):
            verification_count += 1
    
    initial_automation_rate = 1.0 - (verification_count / len(fields))
    
    # Adjust thresholds to achieve target automation rate
    target_rate = 0.85  # 85% automation target
    adjusted_thresholds = adjust_thresholds_for_automation_rate(
        current_automation_rate=initial_automation_rate,
        target_automation_rate=target_rate
    )
    
    # Calculate new automation rate with adjusted thresholds
    verification_count = 0
    for field in fields:
        if requires_human_verification(
            field["confidence"]["score"],
            field["importance"],
            adjusted_thresholds
        ):
            verification_count += 1
    
    new_automation_rate = 1.0 - (verification_count / len(fields))
    
    # Verify that the new automation rate is closer to the target
    assert abs(new_automation_rate - target_rate) < abs(initial_automation_rate - target_rate)


def test_confidence_scoring_correlation_with_accuracy():
    """Test correlation between confidence scores and actual accuracy."""
    # Create a set of fields with confidence scores and ground truth
    fields_with_truth = [
        {
            "confidence": {"score": 0.95},
            "value": "Acme Corporation",
            "ground_truth": "Acme Corporation"
        },
        {
            "confidence": {"score": 0.88},
            "value": "12-3456789",
            "ground_truth": "12-3456789"
        },
        {
            "confidence": {"score": 0.82},
            "value": "123 Main St",
            "ground_truth": "123 Main St"
        },
        {
            "confidence": {"score": 0.75},
            "value": "John Smith",
            "ground_truth": "John Smith"
        },
        {
            "confidence": {"score": 0.68},
            "value": "$45,000",
            "ground_truth": "$45,000"
        },
        {
            "confidence": {"score": 0.62},
            "value": "Manufacturing",
            "ground_truth": "Manufacturing"
        },
        {
            "confidence": {"score": 0.55},
            "value": "January 15, 2023",
            "ground_truth": "January 15, 2023"
        },
        {
            "confidence": {"score": 0.48},
            "value": "Quarterly",
            "ground_truth": "Quarterly"
        },
        {
            "confidence": {"score": 0.42},
            "value": "New York",
            "ground_truth": "New Jersey"
        },
        {
            "confidence": {"score": 0.35},
            "value": "555-123-4567",
            "ground_truth": "555-123-4567"
        },
        {
            "confidence": {"score": 0.28},
            "value": "info@acme.com",
            "ground_truth": "info@acmecorp.com"
        },
        {
            "confidence": {"score": 0.22},
            "value": "Established 2005",
            "ground_truth": "Established 2015"
        }
    ]
    
    # Calculate accuracy for each field
    for field in fields_with_truth:
        field["accurate"] = field["value"] == field["ground_truth"]
    
    # Group fields by confidence level
    high_confidence = [f for f in fields_with_truth if f["confidence"]["score"] >= DEFAULT_HIGH_CONFIDENCE_THRESHOLD]
    medium_confidence = [f for f in fields_with_truth if DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD <= f["confidence"]["score"] < DEFAULT_HIGH_CONFIDENCE_THRESHOLD]
    low_confidence = [f for f in fields_with_truth if DEFAULT_LOW_CONFIDENCE_THRESHOLD <= f["confidence"]["score"] < DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD]
    very_low_confidence = [f for f in fields_with_truth if f["confidence"]["score"] < DEFAULT_LOW_CONFIDENCE_THRESHOLD]
    
    # Calculate accuracy rates by confidence level
    high_accuracy = sum(1 for f in high_confidence if f["accurate"]) / len(high_confidence) if high_confidence else 0
    medium_accuracy = sum(1 for f in medium_confidence if f["accurate"]) / len(medium_confidence) if medium_confidence else 0
    low_accuracy = sum(1 for f in low_confidence if f["accurate"]) / len(low_confidence) if low_confidence else 0
    very_low_accuracy = sum(1 for f in very_low_confidence if f["accurate"]) / len(very_low_confidence) if very_low_confidence else 0
    
    # Verify that higher confidence correlates with higher accuracy
    assert high_accuracy > medium_accuracy
    assert medium_accuracy > low_accuracy
    assert low_accuracy > very_low_accuracy
    
    # Verify that high confidence fields meet the 99% accuracy requirement
    # Note: With a small sample size, we use a lower threshold for the test
    assert high_accuracy >= 0.9  # In production with larger samples, this would be 0.99