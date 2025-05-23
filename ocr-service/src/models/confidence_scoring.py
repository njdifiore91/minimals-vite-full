#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Confidence Scoring Module for OCR Service

This module provides utilities for calculating and standardizing confidence scores
for extracted text fields from OCR results. It enables the system to assess the
reliability of extracted data and make informed decisions about automation versus
human review.

The confidence scoring algorithms in this module are critical for achieving the
93% reduction in manual processing through automation while maintaining 99% data
extraction accuracy.

Key Features:
- Field-level confidence calculation based on recognition certainty
- Standardized scoring system across different model types
- Threshold configuration for automation decisions
- Confidence metadata enrichment for extracted fields
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np

from ..types.extraction import (
    ConfidenceScore,
    ExtractedField,
    FieldLocation,
    ExtractionMetadata
)
from ..types.models import OCRModelType, ModelResult

# Configure logger
logger = logging.getLogger(__name__)

# Default confidence thresholds
DEFAULT_HIGH_CONFIDENCE_THRESHOLD = 0.85  # Fields above this are considered high confidence
DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD = 0.65  # Fields above this are considered medium confidence
DEFAULT_LOW_CONFIDENCE_THRESHOLD = 0.40  # Fields below this are considered low confidence

# Model-specific confidence adjustment factors
# Different models have different baseline confidence distributions
MODEL_CONFIDENCE_ADJUSTMENTS = {
    OCRModelType.TYPED: 1.0,  # Baseline adjustment (no change)
    OCRModelType.HANDWRITTEN: 0.85,  # Handwritten recognition is generally less confident
    OCRModelType.HYBRID: 0.92,  # Hybrid model has intermediate confidence
}

# Field type confidence modifiers
# Some field types are inherently more difficult to extract accurately
FIELD_TYPE_MODIFIERS = {
    "text": 1.0,  # Baseline (no adjustment)
    "numeric": 1.05,  # Numeric fields are often more reliable
    "date": 0.95,  # Dates can be ambiguous
    "currency": 1.02,  # Currency values are usually well-formatted
    "address": 0.90,  # Addresses have complex structure
    "name": 0.92,  # Names have variable formats
    "ein": 1.08,  # EINs have consistent format
    "phone": 1.05,  # Phone numbers have consistent format
    "email": 0.93,  # Emails can be complex
    "signature": 0.80,  # Signatures are highly variable
}


def normalize_raw_confidence(raw_confidence: float, model_type: OCRModelType) -> float:
    """
    Normalize raw confidence scores from different OCR models to a standardized scale.
    
    Different OCR models produce confidence scores with different distributions.
    This function normalizes these scores to a consistent scale between 0 and 1.
    
    Args:
        raw_confidence: The raw confidence score from the OCR model (0.0 to 1.0)
        model_type: The type of OCR model that produced the score
        
    Returns:
        A normalized confidence score between 0.0 and 1.0
    """
    if not 0.0 <= raw_confidence <= 1.0:
        logger.warning(f"Raw confidence score {raw_confidence} outside expected range [0.0, 1.0]")
        # Clamp to valid range
        raw_confidence = max(0.0, min(1.0, raw_confidence))
    
    # Apply model-specific adjustment factor
    adjustment_factor = MODEL_CONFIDENCE_ADJUSTMENTS.get(model_type, 1.0)
    
    # Apply sigmoid normalization to create more separation between high and low confidence
    # and to account for model-specific confidence distributions
    normalized = 1.0 / (1.0 + math.exp(-10 * (raw_confidence * adjustment_factor - 0.5)))
    
    return normalized


def calculate_field_confidence(
    raw_confidence: float,
    model_type: OCRModelType,
    field_type: str = "text",
    char_variance: Optional[float] = None,
    context_agreement: Optional[float] = None
) -> float:
    """
    Calculate the confidence score for an extracted field, considering multiple factors.
    
    This function combines raw OCR confidence with additional factors like character
    variance, field type, and context agreement to produce a comprehensive confidence score.
    
    Args:
        raw_confidence: The raw confidence score from the OCR model (0.0 to 1.0)
        model_type: The type of OCR model that produced the score
        field_type: The type of field being extracted (text, numeric, date, etc.)
        char_variance: Optional variance in character recognition confidence
        context_agreement: Optional measure of agreement with expected context
        
    Returns:
        A final confidence score between 0.0 and 1.0
    """
    # Normalize the raw confidence score
    normalized_confidence = normalize_raw_confidence(raw_confidence, model_type)
    
    # Apply field type modifier
    field_modifier = FIELD_TYPE_MODIFIERS.get(field_type.lower(), 1.0)
    modified_confidence = normalized_confidence * field_modifier
    
    # If character variance is provided, incorporate it
    # High variance indicates inconsistent character recognition
    if char_variance is not None:
        # Convert variance to a modifier (lower variance = higher confidence)
        variance_modifier = 1.0 - (min(char_variance, 0.5) * 0.5)
        modified_confidence *= variance_modifier
    
    # If context agreement is provided, incorporate it
    # Higher agreement with expected context increases confidence
    if context_agreement is not None:
        context_modifier = 0.7 + (context_agreement * 0.3)  # Scale to range [0.7, 1.0]
        modified_confidence *= context_modifier
    
    # Ensure the final score is in the valid range [0.0, 1.0]
    return max(0.0, min(1.0, modified_confidence))


def get_confidence_level(
    confidence_score: float,
    high_threshold: float = DEFAULT_HIGH_CONFIDENCE_THRESHOLD,
    medium_threshold: float = DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD,
    low_threshold: float = DEFAULT_LOW_CONFIDENCE_THRESHOLD
) -> str:
    """
    Convert a numeric confidence score to a categorical confidence level.
    
    Args:
        confidence_score: The calculated confidence score (0.0 to 1.0)
        high_threshold: Threshold for high confidence classification
        medium_threshold: Threshold for medium confidence classification
        low_threshold: Threshold for low confidence classification
        
    Returns:
        A string representing the confidence level: 'high', 'medium', 'low', or 'very_low'
    """
    if confidence_score >= high_threshold:
        return "high"
    elif confidence_score >= medium_threshold:
        return "medium"
    elif confidence_score >= low_threshold:
        return "low"
    else:
        return "very_low"


def requires_human_verification(
    confidence_score: float,
    field_importance: str = "standard",
    verification_thresholds: Optional[Dict[str, float]] = None
) -> bool:
    """
    Determine if a field requires human verification based on confidence and importance.
    
    Critical fields may require verification even with higher confidence scores,
    while standard fields only require verification with lower confidence.
    
    Args:
        confidence_score: The calculated confidence score (0.0 to 1.0)
        field_importance: The importance of the field ('critical', 'standard', or 'optional')
        verification_thresholds: Optional custom thresholds for different importance levels
        
    Returns:
        Boolean indicating whether human verification is required
    """
    # Default verification thresholds by field importance
    default_thresholds = {
        "critical": 0.85,  # Critical fields require high confidence
        "standard": 0.65,  # Standard fields require medium confidence
        "optional": 0.40,  # Optional fields only require verification if very low confidence
    }
    
    # Use custom thresholds if provided, otherwise use defaults
    thresholds = verification_thresholds or default_thresholds
    
    # Get the threshold for this field's importance
    threshold = thresholds.get(field_importance, default_thresholds["standard"])
    
    # Require verification if confidence is below threshold
    return confidence_score < threshold


def calculate_character_variance(char_confidences: List[float]) -> float:
    """
    Calculate the variance in character recognition confidences.
    
    High variance indicates inconsistent character recognition, which may
    suggest lower overall confidence even if the average is high.
    
    Args:
        char_confidences: List of confidence scores for individual characters
        
    Returns:
        The variance of the character confidence scores
    """
    if not char_confidences:
        return 0.0
    
    return float(np.var(char_confidences))


def enrich_field_with_confidence(
    field: ExtractedField,
    raw_confidence: float,
    model_type: OCRModelType,
    char_confidences: Optional[List[float]] = None,
    context_agreement: Optional[float] = None
) -> ExtractedField:
    """
    Enrich an extracted field with confidence metadata.
    
    This function calculates confidence scores and adds them to the field metadata,
    enabling downstream services to make informed decisions about automation.
    
    Args:
        field: The extracted field to enrich
        raw_confidence: The raw confidence score from the OCR model
        model_type: The type of OCR model that produced the score
        char_confidences: Optional list of character-level confidence scores
        context_agreement: Optional measure of agreement with expected context
        
    Returns:
        The enriched field with confidence metadata
    """
    # Calculate character variance if character confidences are provided
    char_variance = None
    if char_confidences:
        char_variance = calculate_character_variance(char_confidences)
    
    # Calculate the final confidence score
    confidence_score = calculate_field_confidence(
        raw_confidence,
        model_type,
        field.get("field_type", "text"),
        char_variance,
        context_agreement
    )
    
    # Determine confidence level
    confidence_level = get_confidence_level(confidence_score)
    
    # Determine if human verification is required
    needs_verification = requires_human_verification(
        confidence_score,
        field.get("importance", "standard")
    )
    
    # Create confidence metadata
    confidence_metadata = {
        "score": confidence_score,
        "level": confidence_level,
        "needs_verification": needs_verification,
        "raw_score": raw_confidence,
        "model_type": model_type.value
    }
    
    # Add character variance if available
    if char_variance is not None:
        confidence_metadata["char_variance"] = char_variance
    
    # Add context agreement if available
    if context_agreement is not None:
        confidence_metadata["context_agreement"] = context_agreement
    
    # Update the field with confidence metadata
    enriched_field = field.copy()
    enriched_field["confidence"] = confidence_metadata
    
    return enriched_field


def calculate_document_confidence(
    fields: List[ExtractedField],
    field_weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Calculate an overall confidence score for a document based on its fields.
    
    This function computes a weighted average of field confidence scores,
    allowing more important fields to have greater influence on the overall score.
    
    Args:
        fields: List of extracted fields with confidence metadata
        field_weights: Optional dictionary mapping field names to weights
        
    Returns:
        An overall document confidence score between 0.0 and 1.0
    """
    if not fields:
        return 0.0
    
    # Default to equal weights if not provided
    if not field_weights:
        field_weights = {field.get("name", f"field_{i}"): 1.0 for i, field in enumerate(fields)}
    
    total_weight = 0.0
    weighted_sum = 0.0
    
    for field in fields:
        field_name = field.get("name", "")
        confidence = field.get("confidence", {})
        confidence_score = confidence.get("score", 0.0)
        
        # Get weight for this field, default to 1.0
        weight = field_weights.get(field_name, 1.0)
        
        weighted_sum += confidence_score * weight
        total_weight += weight
    
    # Avoid division by zero
    if total_weight == 0.0:
        return 0.0
    
    return weighted_sum / total_weight


def adjust_thresholds_for_automation_rate(
    current_automation_rate: float,
    target_automation_rate: float = 0.93,  # 93% automation target
    current_thresholds: Dict[str, float] = None,
    max_adjustment: float = 0.10,  # Maximum 10% adjustment
    min_critical_threshold: float = 0.80  # Minimum threshold for critical fields
) -> Dict[str, float]:
    """
    Dynamically adjust verification thresholds to achieve target automation rate.
    
    This function enables the system to self-tune to achieve the 93% automation
    target while maintaining accuracy requirements.
    
    Args:
        current_automation_rate: The current automation rate (0.0 to 1.0)
        target_automation_rate: The target automation rate (default 0.93)
        current_thresholds: The current verification thresholds
        max_adjustment: Maximum allowed threshold adjustment
        min_critical_threshold: Minimum threshold for critical fields
        
    Returns:
        Adjusted verification thresholds
    """
    # Use default thresholds if none provided
    if current_thresholds is None:
        current_thresholds = {
            "critical": 0.85,
            "standard": 0.65,
            "optional": 0.40,
        }
    
    # Calculate the difference between current and target rates
    rate_difference = target_automation_rate - current_automation_rate
    
    # No adjustment needed if we're within 1% of target
    if abs(rate_difference) < 0.01:
        return current_thresholds.copy()
    
    # Calculate adjustment factor (limited by max_adjustment)
    adjustment = min(max(rate_difference * 0.2, -max_adjustment), max_adjustment)
    
    # Apply adjustment to thresholds
    adjusted_thresholds = {}
    for importance, threshold in current_thresholds.items():
        # Adjust threshold (lower threshold = more automation)
        new_threshold = threshold - adjustment
        
        # Ensure critical fields maintain minimum threshold
        if importance == "critical":
            new_threshold = max(new_threshold, min_critical_threshold)
        
        # Ensure thresholds stay in valid range
        new_threshold = max(0.0, min(1.0, new_threshold))
        
        adjusted_thresholds[importance] = new_threshold
    
    logger.info(
        f"Adjusted verification thresholds from {current_thresholds} to "
        f"{adjusted_thresholds} (current automation rate: {current_automation_rate:.2f}, "
        f"target: {target_automation_rate:.2f})"
    )
    
    return adjusted_thresholds


def analyze_confidence_distribution(
    confidence_scores: List[float]
) -> Dict[str, Any]:
    """
    Analyze the distribution of confidence scores for monitoring and optimization.
    
    This function calculates statistics about confidence score distribution,
    which can be used for monitoring system performance and identifying
    opportunities for model improvement.
    
    Args:
        confidence_scores: List of confidence scores from extracted fields
        
    Returns:
        Dictionary containing distribution statistics
    """
    if not confidence_scores:
        return {
            "count": 0,
            "mean": 0.0,
            "median": 0.0,
            "std_dev": 0.0,
            "min": 0.0,
            "max": 0.0,
            "quartiles": [0.0, 0.0, 0.0],
            "below_threshold": {
                "low": 0,
                "medium": 0,
                "high": 0
            }
        }
    
    scores = np.array(confidence_scores)
    
    # Calculate basic statistics
    mean = float(np.mean(scores))
    median = float(np.median(scores))
    std_dev = float(np.std(scores))
    min_val = float(np.min(scores))
    max_val = float(np.max(scores))
    
    # Calculate quartiles
    quartiles = [float(np.percentile(scores, q)) for q in [25, 50, 75]]
    
    # Count scores below thresholds
    below_threshold = {
        "low": int(np.sum(scores < DEFAULT_LOW_CONFIDENCE_THRESHOLD)),
        "medium": int(np.sum(scores < DEFAULT_MEDIUM_CONFIDENCE_THRESHOLD)),
        "high": int(np.sum(scores < DEFAULT_HIGH_CONFIDENCE_THRESHOLD))
    }
    
    return {
        "count": len(scores),
        "mean": mean,
        "median": median,
        "std_dev": std_dev,
        "min": min_val,
        "max": max_val,
        "quartiles": quartiles,
        "below_threshold": below_threshold
    }