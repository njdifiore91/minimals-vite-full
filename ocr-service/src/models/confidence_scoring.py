"""Confidence scoring utilities for OCR extraction results.

This module provides algorithms and utilities for calculating, standardizing, and
evaluating confidence scores for OCR extraction results. It enables the system to
make informed decisions about automation versus human review based on the reliability
of extracted text fields.
"""

from __future__ import annotations

import math
import logging
import statistics
from typing import Dict, List, Tuple, Optional, Any, Union, Set, cast

import numpy as np

# Import TensorFlow conditionally to avoid runtime dependency
try:
    import tensorflow as tf
    TensorType = tf.Tensor
except ImportError:
    # Define placeholder type if TensorFlow is not available
    class TensorType:
        pass

from ..types.extraction import (
    ConfidenceScore,
    ExtractedField,
    ExtractedData,
    FieldType,
    TableData
)

# Configure logger
logger = logging.getLogger(__name__)

# Default thresholds for confidence scoring
DEFAULT_CONFIDENCE_THRESHOLD = 0.7  # Default threshold for automation
HIGH_CONFIDENCE_THRESHOLD = 0.9     # Threshold for high confidence
LOW_CONFIDENCE_THRESHOLD = 0.5      # Threshold for low confidence
CRITICAL_FIELD_THRESHOLD = 0.8      # Higher threshold for critical fields

# Field importance weights (higher values indicate more critical fields)
FIELD_IMPORTANCE = {
    "business_name": 0.9,
    "tax_id": 0.95,
    "ein": 0.95,
    "ssn": 0.95,
    "requested_amount": 0.9,
    "monthly_revenue": 0.85,
    "owner_name": 0.85,
    "signature": 0.9,
    "application_date": 0.8,
    "business_address": 0.8,
    "business_phone": 0.75,
    "business_email": 0.75,
    "dba_name": 0.6,
}

# Default importance for fields not explicitly listed
DEFAULT_FIELD_IMPORTANCE = 0.7

# Field type confidence modifiers
# Some field types are inherently more difficult to extract accurately
FIELD_TYPE_MODIFIERS = {
    FieldType.TEXT: 1.0,        # Standard text
    FieldType.NUMBER: 0.95,     # Numbers are usually more reliable
    FieldType.DATE: 0.85,       # Dates can have various formats
    FieldType.CURRENCY: 0.9,    # Currency values are usually clear
    FieldType.PERCENTAGE: 0.9,  # Percentage values are usually clear
    FieldType.NAME: 0.8,        # Names can be complex
    FieldType.ADDRESS: 0.75,    # Addresses are complex
    FieldType.PHONE: 0.9,       # Phone numbers are usually clear
    FieldType.EMAIL: 0.85,      # Emails can be complex
    FieldType.SSN: 0.95,        # SSNs have a standard format
    FieldType.EIN: 0.95,        # EINs have a standard format
    FieldType.ACCOUNT_NUMBER: 0.9,  # Account numbers are usually clear
    FieldType.CHECKBOX: 0.95,   # Checkboxes are usually clear
    FieldType.SIGNATURE: 0.7,   # Signatures are complex
    FieldType.TABLE: 0.8,       # Tables are complex structures
    FieldType.CUSTOM: 0.8,      # Custom fields vary
}


def calculate_character_confidence(char_confidences: List[float]) -> float:
    """Calculate confidence score for a sequence of character confidences.
    
    This function takes a list of character-level confidence scores and
    computes an overall confidence score for the entire text sequence.
    It uses a weighted geometric mean to ensure that low-confidence
    characters have a significant impact on the overall score.
    
    Args:
        char_confidences: List of character-level confidence scores (0.0-1.0)
        
    Returns:
        Overall confidence score for the text sequence (0.0-1.0)
    """
    if not char_confidences:
        return 0.0
    
    # Filter out any invalid values
    valid_confidences = [c for c in char_confidences if 0.0 <= c <= 1.0]
    if not valid_confidences:
        return 0.0
    
    # Use weighted geometric mean to emphasize low confidence characters
    # This ensures that a few low-confidence characters will significantly
    # reduce the overall confidence score
    log_sum = sum(math.log(max(c, 0.0001)) for c in valid_confidences)
    return math.exp(log_sum / len(valid_confidences))


def calculate_word_confidence(word_confidences: List[float]) -> float:
    """Calculate confidence score for a sequence of word confidences.
    
    This function takes a list of word-level confidence scores and
    computes an overall confidence score for the entire text sequence.
    It uses a weighted average that gives more weight to lower confidence
    words to ensure they have appropriate impact on the overall score.
    
    Args:
        word_confidences: List of word-level confidence scores (0.0-1.0)
        
    Returns:
        Overall confidence score for the text sequence (0.0-1.0)
    """
    if not word_confidences:
        return 0.0
    
    # Filter out any invalid values
    valid_confidences = [c for c in word_confidences if 0.0 <= c <= 1.0]
    if not valid_confidences:
        return 0.0
    
    # Calculate weighted average with more weight given to lower confidence words
    weights = [2.0 - c for c in valid_confidences]  # Lower confidence = higher weight
    weighted_sum = sum(c * w for c, w in zip(valid_confidences, weights))
    return weighted_sum / sum(weights)


def normalize_model_confidence(raw_confidence: float, model_type: str) -> float:
    """Normalize confidence scores from different model types to a standard scale.
    
    Different OCR models may produce confidence scores with different
    distributions and biases. This function normalizes these scores to
    a standard scale (0.0-1.0) based on empirical calibration for each model type.
    
    Args:
        raw_confidence: Raw confidence score from the model (0.0-1.0)
        model_type: Type of model that produced the score
        
    Returns:
        Normalized confidence score (0.0-1.0)
    """
    # Model-specific calibration parameters based on empirical analysis
    calibration_params = {
        "typed_text": {"scale": 1.0, "bias": 0.0},  # Typed text models are well-calibrated
        "handwritten": {"scale": 1.2, "bias": -0.1},  # Handwritten models tend to be overconfident
        "hybrid": {"scale": 1.1, "bias": -0.05},  # Hybrid models are slightly overconfident
        "default": {"scale": 1.0, "bias": 0.0}  # Default calibration
    }
    
    # Get calibration parameters for the specified model type
    params = calibration_params.get(model_type.lower(), calibration_params["default"])
    
    # Apply calibration formula: normalized = (raw * scale) + bias
    normalized = (raw_confidence * params["scale"]) + params["bias"]
    
    # Clamp to valid range [0.0, 1.0]
    return max(0.0, min(1.0, normalized))


def adjust_confidence_by_field_type(confidence: float, field_type: FieldType) -> float:
    """Adjust confidence score based on field type.
    
    Some field types are inherently more difficult to extract accurately.
    This function adjusts the confidence score based on the field type to
    account for these differences.
    
    Args:
        confidence: Original confidence score (0.0-1.0)
        field_type: Type of field being extracted
        
    Returns:
        Adjusted confidence score (0.0-1.0)
    """
    # Get modifier for the specified field type
    modifier = FIELD_TYPE_MODIFIERS.get(field_type, 1.0)
    
    # Apply modifier: adjusted = confidence * modifier
    adjusted = confidence * modifier
    
    # Clamp to valid range [0.0, 1.0]
    return max(0.0, min(1.0, adjusted))


def adjust_confidence_by_context(confidence: float, field_name: str, 
                               other_fields: Dict[str, ExtractedField]) -> float:
    """Adjust confidence score based on context from other extracted fields.
    
    The confidence of a field can be adjusted based on the context provided
    by other extracted fields. For example, if a field's value is consistent
    with related fields, its confidence can be increased.
    
    Args:
        confidence: Original confidence score (0.0-1.0)
        field_name: Name of the field being adjusted
        other_fields: Dictionary of other extracted fields
        
    Returns:
        Adjusted confidence score (0.0-1.0)
    """
    # Context-based adjustments for specific field relationships
    adjustment = 0.0
    
    # Example: If both business_name and dba_name are present and similar,
    # increase confidence for both
    if field_name in ("business_name", "dba_name") and "business_name" in other_fields and "dba_name" in other_fields:
        business_name = other_fields["business_name"].get("raw_text", "").lower()
        dba_name = other_fields["dba_name"].get("raw_text", "").lower()
        
        # If business_name is part of dba_name or vice versa, increase confidence
        if (business_name and dba_name and 
            (business_name in dba_name or dba_name in business_name)):
            adjustment += 0.05
    
    # Example: If phone number format is valid, increase confidence
    if field_name == "business_phone" and "business_phone" in other_fields:
        phone = other_fields["business_phone"].get("raw_text", "")
        # Simple check for US phone number format
        if phone and (len(phone.replace("-", "").replace("(", "").replace(")", "").replace(" ", "")) == 10):
            adjustment += 0.05
    
    # Example: If email format is valid, increase confidence
    if field_name == "business_email" and "business_email" in other_fields:
        email = other_fields["business_email"].get("raw_text", "")
        if email and "@" in email and "." in email.split("@")[-1]:
            adjustment += 0.05
    
    # Apply adjustment with clamping to valid range [0.0, 1.0]
    return max(0.0, min(1.0, confidence + adjustment))


def calculate_field_confidence(field_name: str, raw_text: str, 
                             char_confidences: List[float], 
                             model_type: str,
                             field_type: FieldType,
                             other_fields: Optional[Dict[str, ExtractedField]] = None) -> ConfidenceScore:
    """Calculate overall confidence score for an extracted field.
    
    This function combines multiple confidence calculation methods to produce
    a comprehensive confidence score for an extracted field, taking into account
    character-level confidences, field type, and context.
    
    Args:
        field_name: Name of the field being extracted
        raw_text: Raw text extracted for the field
        char_confidences: List of character-level confidence scores
        model_type: Type of OCR model used for extraction
        field_type: Type of field being extracted
        other_fields: Dictionary of other extracted fields for context
        
    Returns:
        ConfidenceScore object representing the overall confidence
    """
    # Calculate base confidence from character confidences
    base_confidence = calculate_character_confidence(char_confidences)
    
    # Normalize confidence based on model type
    normalized_confidence = normalize_model_confidence(base_confidence, model_type)
    
    # Adjust confidence based on field type
    type_adjusted_confidence = adjust_confidence_by_field_type(normalized_confidence, field_type)
    
    # Adjust confidence based on context if other fields are provided
    if other_fields:
        context_adjusted_confidence = adjust_confidence_by_context(
            type_adjusted_confidence, field_name, other_fields)
    else:
        context_adjusted_confidence = type_adjusted_confidence
    
    # Create and return ConfidenceScore object
    return ConfidenceScore.from_float(context_adjusted_confidence)


def calculate_table_confidence(table_data: TableData) -> ConfidenceScore:
    """Calculate overall confidence score for an extracted table.
    
    This function calculates a confidence score for an entire table based on
    the confidence of its individual cells and structural integrity.
    
    Args:
        table_data: Extracted table data
        
    Returns:
        ConfidenceScore object representing the overall table confidence
    """
    # Extract cell confidences from table data
    # This assumes table cells have confidence scores
    cell_confidences = []
    
    # Calculate structural integrity score based on completeness
    structure_score = 1.0 if table_data.get("is_complete", False) else 0.8
    
    # If no cell confidences are available, return structure score
    if not cell_confidences:
        return ConfidenceScore.from_float(structure_score)
    
    # Calculate average cell confidence
    avg_cell_confidence = statistics.mean(cell_confidences)
    
    # Combine cell confidence and structure score with more weight on structure
    combined_confidence = (avg_cell_confidence * 0.7) + (structure_score * 0.3)
    
    return ConfidenceScore.from_float(combined_confidence)


def should_flag_for_verification(field_name: str, confidence: ConfidenceScore) -> Tuple[bool, str]:
    """Determine if a field should be flagged for human verification.
    
    This function decides whether a field should be flagged for human verification
    based on its confidence score and importance. Critical fields have higher
    confidence thresholds.
    
    Args:
        field_name: Name of the field being evaluated
        confidence: Confidence score for the field
        
    Returns:
        Tuple of (requires_verification, reason)
    """
    # Get importance weight for the field
    importance = FIELD_IMPORTANCE.get(field_name, DEFAULT_FIELD_IMPORTANCE)
    
    # Calculate threshold based on field importance
    # More important fields have higher thresholds
    threshold = DEFAULT_CONFIDENCE_THRESHOLD
    if importance >= 0.9:
        threshold = CRITICAL_FIELD_THRESHOLD  # Higher threshold for critical fields
    elif importance >= 0.8:
        threshold = DEFAULT_CONFIDENCE_THRESHOLD + 0.05  # Slightly higher for important fields
    
    # Check if confidence is below threshold
    if float(confidence) < threshold:
        reason = f"Confidence {float(confidence):.2f} below threshold {threshold:.2f} for {field_name}"
        return True, reason
    
    return False, ""


def calculate_document_confidence(extracted_data: ExtractedData) -> ConfidenceScore:
    """Calculate overall confidence score for an entire document extraction.
    
    This function calculates a weighted average confidence score for an entire
    document based on the confidence scores of individual fields, giving more
    weight to critical fields.
    
    Args:
        extracted_data: Complete extraction results for a document
        
    Returns:
        ConfidenceScore object representing the overall document confidence
    """
    fields = extracted_data.get("fields", {})
    if not fields:
        return ConfidenceScore.from_float(0.0)
    
    # Calculate weighted average of field confidences
    weighted_sum = 0.0
    weight_sum = 0.0
    
    for field_name, field_data in fields.items():
        # Get confidence score and importance weight
        confidence = float(field_data.get("confidence", ConfidenceScore.from_float(0.0)))
        importance = FIELD_IMPORTANCE.get(field_name, DEFAULT_FIELD_IMPORTANCE)
        
        # Add to weighted sum
        weighted_sum += confidence * importance
        weight_sum += importance
    
    # Calculate weighted average
    if weight_sum > 0:
        avg_confidence = weighted_sum / weight_sum
    else:
        avg_confidence = 0.0
    
    return ConfidenceScore.from_float(avg_confidence)


def enrich_extraction_with_confidence_metadata(extracted_data: ExtractedData) -> ExtractedData:
    """Enrich extraction results with confidence metadata.
    
    This function analyzes the confidence scores of all fields in an extraction
    and adds metadata about low-confidence fields and verification requirements.
    
    Args:
        extracted_data: Extraction results to enrich
        
    Returns:
        Enriched extraction results with confidence metadata
    """
    fields = extracted_data.get("fields", {})
    low_confidence_fields = []
    requires_verification = False
    verification_reasons = []
    
    # Analyze each field for confidence issues
    for field_name, field_data in fields.items():
        confidence = field_data.get("confidence", ConfidenceScore.from_float(0.0))
        
        # Check if field should be flagged for verification
        should_verify, reason = should_flag_for_verification(field_name, confidence)
        
        # Update field data with verification flag and reason
        field_data["requires_verification"] = should_verify
        field_data["verification_reason"] = reason if should_verify else ""
        
        # Track low confidence fields and verification requirements
        if should_verify:
            low_confidence_fields.append(field_name)
            requires_verification = True
            verification_reasons.append(reason)
    
    # Update extraction metadata
    extracted_data["low_confidence_fields"] = low_confidence_fields
    extracted_data["requires_verification"] = requires_verification
    
    # Add overall document confidence
    document_confidence = calculate_document_confidence(extracted_data)
    extracted_data["metadata"]["overall_confidence"] = float(document_confidence)
    extracted_data["metadata"]["verification_reasons"] = verification_reasons
    
    return extracted_data


def confidence_from_tensorflow_output(output_tensor: TensorType) -> List[float]:
    """Extract confidence scores from TensorFlow model output.
    
    This function converts TensorFlow model output tensors into a list of
    confidence scores that can be used for confidence calculation.
    
    Args:
        output_tensor: TensorFlow tensor containing model output
        
    Returns:
        List of confidence scores (0.0-1.0)
    """
    try:
        # Convert tensor to numpy array
        if hasattr(output_tensor, "numpy"):
            scores = output_tensor.numpy()
        else:
            scores = np.array(output_tensor)
        
        # Flatten array and convert to list
        flat_scores = scores.flatten().tolist()
        
        # Ensure all scores are in range [0.0, 1.0]
        normalized_scores = [max(0.0, min(1.0, score)) for score in flat_scores]
        
        return normalized_scores
    except Exception as e:
        logger.error(f"Error extracting confidence from TensorFlow output: {e}")
        return [0.5]  # Return default confidence on error


def get_confidence_threshold_config() -> Dict[str, float]:
    """Get confidence threshold configuration.
    
    This function returns the current confidence threshold configuration,
    which can be customized based on system requirements and performance.
    
    Returns:
        Dictionary of confidence threshold configuration
    """
    return {
        "default": DEFAULT_CONFIDENCE_THRESHOLD,
        "high": HIGH_CONFIDENCE_THRESHOLD,
        "low": LOW_CONFIDENCE_THRESHOLD,
        "critical": CRITICAL_FIELD_THRESHOLD,
    }


def update_confidence_threshold_config(config: Dict[str, float]) -> None:
    """Update confidence threshold configuration.
    
    This function updates the global confidence threshold configuration
    based on the provided values.
    
    Args:
        config: Dictionary of confidence threshold configuration
    """
    global DEFAULT_CONFIDENCE_THRESHOLD, HIGH_CONFIDENCE_THRESHOLD, LOW_CONFIDENCE_THRESHOLD, CRITICAL_FIELD_THRESHOLD
    
    # Update global thresholds if provided in config
    if "default" in config:
        DEFAULT_CONFIDENCE_THRESHOLD = config["default"]
    if "high" in config:
        HIGH_CONFIDENCE_THRESHOLD = config["high"]
    if "low" in config:
        LOW_CONFIDENCE_THRESHOLD = config["low"]
    if "critical" in config:
        CRITICAL_FIELD_THRESHOLD = config["critical"]
    
    logger.info(f"Updated confidence threshold configuration: {get_confidence_threshold_config()}")


class ConfidenceAnalyzer:
    """Analyzer for confidence scores across document batches.
    
    This class provides utilities for analyzing confidence scores across
    multiple documents, tracking performance metrics, and generating reports.
    It helps in tuning confidence thresholds and improving extraction accuracy.
    """
    
    def __init__(self):
        """Initialize the ConfidenceAnalyzer."""
        self.document_confidences = []
        self.field_confidences = {}
        self.verification_rates = {}
        self.automation_rates = {}
    
    def add_document(self, extracted_data: ExtractedData) -> None:
        """Add a document's extraction results for analysis.
        
        Args:
            extracted_data: Extraction results for a document
        """
        # Track overall document confidence
        doc_confidence = float(calculate_document_confidence(extracted_data))
        self.document_confidences.append(doc_confidence)
        
        # Track field-level confidences
        fields = extracted_data.get("fields", {})
        for field_name, field_data in fields.items():
            confidence = float(field_data.get("confidence", ConfidenceScore.from_float(0.0)))
            requires_verification = field_data.get("requires_verification", False)
            
            # Initialize field tracking if not already present
            if field_name not in self.field_confidences:
                self.field_confidences[field_name] = []
                self.verification_rates[field_name] = {"verified": 0, "total": 0}
            
            # Update tracking
            self.field_confidences[field_name].append(confidence)
            self.verification_rates[field_name]["total"] += 1
            if requires_verification:
                self.verification_rates[field_name]["verified"] += 1
        
        # Track document-level automation
        requires_verification = extracted_data.get("requires_verification", False)
        doc_type = extracted_data.get("document_type", "unknown")
        
        if doc_type not in self.automation_rates:
            self.automation_rates[doc_type] = {"automated": 0, "total": 0}
        
        self.automation_rates[doc_type]["total"] += 1
        if not requires_verification:
            self.automation_rates[doc_type]["automated"] += 1
    
    def get_overall_automation_rate(self) -> float:
        """Calculate the overall automation rate across all documents.
        
        Returns:
            Automation rate as a percentage (0.0-100.0)
        """
        total_docs = sum(stats["total"] for stats in self.automation_rates.values())
        automated_docs = sum(stats["automated"] for stats in self.automation_rates.values())
        
        if total_docs > 0:
            return (automated_docs / total_docs) * 100.0
        return 0.0
    
    def get_field_verification_rates(self) -> Dict[str, float]:
        """Calculate verification rates for each field.
        
        Returns:
            Dictionary mapping field names to verification rates (0.0-100.0)
        """
        verification_rates = {}
        
        for field_name, stats in self.verification_rates.items():
            if stats["total"] > 0:
                rate = (stats["verified"] / stats["total"]) * 100.0
                verification_rates[field_name] = rate
            else:
                verification_rates[field_name] = 0.0
        
        return verification_rates
    
    def get_field_confidence_stats(self) -> Dict[str, Dict[str, float]]:
        """Calculate confidence statistics for each field.
        
        Returns:
            Dictionary mapping field names to confidence statistics
        """
        confidence_stats = {}
        
        for field_name, confidences in self.field_confidences.items():
            if confidences:
                stats = {
                    "mean": statistics.mean(confidences),
                    "median": statistics.median(confidences),
                    "min": min(confidences),
                    "max": max(confidences),
                    "std_dev": statistics.stdev(confidences) if len(confidences) > 1 else 0.0
                }
                confidence_stats[field_name] = stats
        
        return confidence_stats
    
    def get_document_confidence_stats(self) -> Dict[str, float]:
        """Calculate confidence statistics across all documents.
        
        Returns:
            Dictionary of document confidence statistics
        """
        if not self.document_confidences:
            return {"mean": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "std_dev": 0.0}
        
        return {
            "mean": statistics.mean(self.document_confidences),
            "median": statistics.median(self.document_confidences),
            "min": min(self.document_confidences),
            "max": max(self.document_confidences),
            "std_dev": statistics.stdev(self.document_confidences) if len(self.document_confidences) > 1 else 0.0
        }
    
    def suggest_threshold_adjustments(self) -> Dict[str, Dict[str, float]]:
        """Suggest adjustments to confidence thresholds based on analysis.
        
        This method analyzes the collected confidence data and suggests
        adjustments to thresholds to optimize automation while maintaining accuracy.
        
        Returns:
            Dictionary of suggested threshold adjustments
        """
        suggestions = {}
        current_thresholds = get_confidence_threshold_config()
        
        # Get overall automation rate
        automation_rate = self.get_overall_automation_rate()
        target_automation = 93.0  # Target 93% automation as specified in requirements
        
        # Suggest global threshold adjustments based on automation rate
        if automation_rate < target_automation - 5.0:  # More than 5% below target
            suggestions["global"] = {
                "default": max(0.1, current_thresholds["default"] - 0.05),
                "critical": max(0.2, current_thresholds["critical"] - 0.03),
                "reason": f"Automation rate ({automation_rate:.1f}%) is below target ({target_automation:.1f}%)"
            }
        elif automation_rate > target_automation + 5.0:  # More than 5% above target
            suggestions["global"] = {
                "default": min(0.9, current_thresholds["default"] + 0.03),
                "critical": min(0.95, current_thresholds["critical"] + 0.02),
                "reason": f"Automation rate ({automation_rate:.1f}%) is above target ({target_automation:.1f}%)"
            }
        
        # Suggest field-specific threshold adjustments
        field_verification_rates = self.get_field_verification_rates()
        field_confidence_stats = self.get_field_confidence_stats()
        
        for field_name, verification_rate in field_verification_rates.items():
            # Skip fields with insufficient data
            if field_name not in field_confidence_stats:
                continue
            
            stats = field_confidence_stats[field_name]
            importance = FIELD_IMPORTANCE.get(field_name, DEFAULT_FIELD_IMPORTANCE)
            
            # High verification rate but good confidence distribution
            if verification_rate > 30.0 and stats["median"] > 0.6:
                suggestions[field_name] = {
                    "threshold": max(0.1, stats["median"] - 0.1),
                    "reason": f"High verification rate ({verification_rate:.1f}%) despite good median confidence ({stats['median']:.2f})"
                }
            
            # Low verification rate but concerning confidence distribution
            elif verification_rate < 5.0 and stats["std_dev"] > 0.2:
                suggestions[field_name] = {
                    "threshold": min(0.95, stats["median"] + 0.05),
                    "reason": f"Low verification rate ({verification_rate:.1f}%) with high confidence variance ({stats['std_dev']:.2f})"
                }
        
        return suggestions
    
    def generate_report(self) -> Dict[str, Any]:
        """Generate a comprehensive report of confidence analysis.
        
        Returns:
            Dictionary containing the complete confidence analysis report
        """
        return {
            "document_confidence": self.get_document_confidence_stats(),
            "field_confidence": self.get_field_confidence_stats(),
            "verification_rates": self.get_field_verification_rates(),
            "automation_rates": self.automation_rates,
            "overall_automation_rate": self.get_overall_automation_rate(),
            "threshold_suggestions": self.suggest_threshold_adjustments(),
            "current_thresholds": get_confidence_threshold_config(),
            "sample_size": len(self.document_confidences),
            "timestamp": datetime.now().isoformat()
        }


def analyze_confidence_distribution(confidences: List[float]) -> Dict[str, Any]:
    """Analyze the distribution of confidence scores.
    
    This function analyzes a list of confidence scores to understand their
    distribution, which can be useful for tuning confidence thresholds.
    
    Args:
        confidences: List of confidence scores to analyze
        
    Returns:
        Dictionary containing distribution analysis
    """
    if not confidences:
        return {"count": 0}
    
    # Calculate basic statistics
    mean = statistics.mean(confidences)
    median = statistics.median(confidences)
    std_dev = statistics.stdev(confidences) if len(confidences) > 1 else 0.0
    
    # Calculate percentiles
    sorted_confidences = sorted(confidences)
    p10 = sorted_confidences[int(len(sorted_confidences) * 0.1)]
    p25 = sorted_confidences[int(len(sorted_confidences) * 0.25)]
    p75 = sorted_confidences[int(len(sorted_confidences) * 0.75)]
    p90 = sorted_confidences[int(len(sorted_confidences) * 0.9)]
    
    # Calculate histogram (10 bins from 0.0 to 1.0)
    histogram = [0] * 10
    for conf in confidences:
        bin_index = min(9, int(conf * 10))
        histogram[bin_index] += 1
    
    # Calculate percentage in each confidence range
    low_conf = sum(1 for c in confidences if c < LOW_CONFIDENCE_THRESHOLD) / len(confidences) * 100.0
    med_conf = sum(1 for c in confidences if LOW_CONFIDENCE_THRESHOLD <= c < HIGH_CONFIDENCE_THRESHOLD) / len(confidences) * 100.0
    high_conf = sum(1 for c in confidences if c >= HIGH_CONFIDENCE_THRESHOLD) / len(confidences) * 100.0
    
    return {
        "count": len(confidences),
        "mean": mean,
        "median": median,
        "std_dev": std_dev,
        "min": min(confidences),
        "max": max(confidences),
        "percentiles": {"p10": p10, "p25": p25, "p75": p75, "p90": p90},
        "histogram": histogram,
        "confidence_ranges": {"low": low_conf, "medium": med_conf, "high": high_conf}
    }


class ConfidenceScoreCalibrator:
    """Calibrates confidence scores based on historical data.
    
    This class provides utilities for calibrating confidence scores based on
    historical data, improving the accuracy of confidence estimation over time.
    It uses a simple Platt scaling approach to adjust raw confidence scores.
    """
    
    def __init__(self):
        """Initialize the ConfidenceScoreCalibrator."""
        # Parameters for Platt scaling (logistic regression)
        self.a = 1.0  # Scale parameter
        self.b = 0.0  # Bias parameter
        self.model_calibrations = {}  # Calibration parameters by model type
        self.field_calibrations = {}  # Calibration parameters by field name
        self.is_calibrated = False
    
    def calibrate(self, raw_scores: List[float], true_scores: List[float]) -> None:
        """Calibrate the model using paired raw and true confidence scores.
        
        This method implements a simplified Platt scaling approach to calibrate
        raw confidence scores to better match true confidence levels.
        
        Args:
            raw_scores: List of raw confidence scores from the model
            true_scores: List of true/verified confidence scores
        """
        if len(raw_scores) != len(true_scores) or len(raw_scores) < 10:
            logger.warning("Insufficient data for calibration")
            return
        
        # Simple linear regression to find a and b
        # such that true_score ≈ a * raw_score + b
        n = len(raw_scores)
        sum_x = sum(raw_scores)
        sum_y = sum(true_scores)
        sum_xx = sum(x * x for x in raw_scores)
        sum_xy = sum(x * y for x, y in zip(raw_scores, true_scores))
        
        # Calculate regression parameters
        try:
            self.a = (n * sum_xy - sum_x * sum_y) / (n * sum_xx - sum_x * sum_x)
            self.b = (sum_y - self.a * sum_x) / n
            self.is_calibrated = True
            
            logger.info(f"Calibrated confidence scoring: score = {self.a:.4f} * raw_score + {self.b:.4f}")
        except ZeroDivisionError:
            logger.error("Calibration failed due to division by zero")
    
    def calibrate_by_model(self, model_type: str, raw_scores: List[float], true_scores: List[float]) -> None:
        """Calibrate confidence scores for a specific model type.
        
        Args:
            model_type: Type of model to calibrate
            raw_scores: List of raw confidence scores from the model
            true_scores: List of true/verified confidence scores
        """
        if len(raw_scores) != len(true_scores) or len(raw_scores) < 10:
            logger.warning(f"Insufficient data for calibrating model type: {model_type}")
            return
        
        # Create a new calibrator for this model type
        calibrator = ConfidenceScoreCalibrator()
        calibrator.calibrate(raw_scores, true_scores)
        
        if calibrator.is_calibrated:
            self.model_calibrations[model_type] = {
                "a": calibrator.a,
                "b": calibrator.b
            }
            logger.info(f"Calibrated model type {model_type}: score = {calibrator.a:.4f} * raw_score + {calibrator.b:.4f}")
    
    def calibrate_by_field(self, field_name: str, raw_scores: List[float], true_scores: List[float]) -> None:
        """Calibrate confidence scores for a specific field.
        
        Args:
            field_name: Name of the field to calibrate
            raw_scores: List of raw confidence scores for the field
            true_scores: List of true/verified confidence scores
        """
        if len(raw_scores) != len(true_scores) or len(raw_scores) < 10:
            logger.warning(f"Insufficient data for calibrating field: {field_name}")
            return
        
        # Create a new calibrator for this field
        calibrator = ConfidenceScoreCalibrator()
        calibrator.calibrate(raw_scores, true_scores)
        
        if calibrator.is_calibrated:
            self.field_calibrations[field_name] = {
                "a": calibrator.a,
                "b": calibrator.b
            }
            logger.info(f"Calibrated field {field_name}: score = {calibrator.a:.4f} * raw_score + {calibrator.b:.4f}")
    
    def calibrate_score(self, raw_score: float) -> float:
        """Calibrate a raw confidence score using the current calibration parameters.
        
        Args:
            raw_score: Raw confidence score to calibrate
            
        Returns:
            Calibrated confidence score
        """
        if not self.is_calibrated:
            return raw_score
        
        # Apply calibration: calibrated = a * raw_score + b
        calibrated = (self.a * raw_score) + self.b
        
        # Clamp to valid range [0.0, 1.0]
        return max(0.0, min(1.0, calibrated))
    
    def calibrate_score_by_model(self, raw_score: float, model_type: str) -> float:
        """Calibrate a raw confidence score for a specific model type.
        
        Args:
            raw_score: Raw confidence score to calibrate
            model_type: Type of model that produced the score
            
        Returns:
            Calibrated confidence score
        """
        if model_type not in self.model_calibrations:
            return self.calibrate_score(raw_score)  # Fall back to global calibration
        
        # Get calibration parameters for this model type
        params = self.model_calibrations[model_type]
        
        # Apply calibration: calibrated = a * raw_score + b
        calibrated = (params["a"] * raw_score) + params["b"]
        
        # Clamp to valid range [0.0, 1.0]
        return max(0.0, min(1.0, calibrated))
    
    def calibrate_score_by_field(self, raw_score: float, field_name: str, model_type: str = None) -> float:
        """Calibrate a raw confidence score for a specific field.
        
        Args:
            raw_score: Raw confidence score to calibrate
            field_name: Name of the field being calibrated
            model_type: Optional model type for fallback calibration
            
        Returns:
            Calibrated confidence score
        """
        # Try field-specific calibration first
        if field_name in self.field_calibrations:
            params = self.field_calibrations[field_name]
            calibrated = (params["a"] * raw_score) + params["b"]
            return max(0.0, min(1.0, calibrated))
        
        # Fall back to model-specific calibration if available
        if model_type is not None:
            return self.calibrate_score_by_model(raw_score, model_type)
        
        # Fall back to global calibration
        return self.calibrate_score(raw_score)
    
    def save_calibration(self, file_path: str) -> bool:
        """Save calibration parameters to a file.
        
        Args:
            file_path: Path to save calibration parameters
            
        Returns:
            True if successful, False otherwise
        """
        try:
            calibration_data = {
                "global": {"a": self.a, "b": self.b},
                "models": self.model_calibrations,
                "fields": self.field_calibrations,
                "is_calibrated": self.is_calibrated,
                "timestamp": datetime.now().isoformat()
            }
            
            with open(file_path, "w") as f:
                json.dump(calibration_data, f, indent=2)
            
            logger.info(f"Saved confidence calibration to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save confidence calibration: {e}")
            return False
    
    def load_calibration(self, file_path: str) -> bool:
        """Load calibration parameters from a file.
        
        Args:
            file_path: Path to load calibration parameters from
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(file_path, "r") as f:
                calibration_data = json.load(f)
            
            # Load global calibration
            if "global" in calibration_data:
                self.a = calibration_data["global"]["a"]
                self.b = calibration_data["global"]["b"]
            
            # Load model-specific calibrations
            if "models" in calibration_data:
                self.model_calibrations = calibration_data["models"]
            
            # Load field-specific calibrations
            if "fields" in calibration_data:
                self.field_calibrations = calibration_data["fields"]
            
            self.is_calibrated = calibration_data.get("is_calibrated", False)
            
            logger.info(f"Loaded confidence calibration from {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to load confidence calibration: {e}")
            return False


# Global calibrator instance for convenience
global_calibrator = ConfidenceScoreCalibrator()


def get_field_importance(field_name: str) -> float:
    """Get the importance weight for a field.
    
    Args:
        field_name: Name of the field
        
    Returns:
        Importance weight (0.0-1.0)
    """
    return FIELD_IMPORTANCE.get(field_name, DEFAULT_FIELD_IMPORTANCE)


def set_field_importance(field_name: str, importance: float) -> None:
    """Set the importance weight for a field.
    
    Args:
        field_name: Name of the field
        importance: Importance weight (0.0-1.0)
    """
    global FIELD_IMPORTANCE
    FIELD_IMPORTANCE[field_name] = max(0.0, min(1.0, importance))
    logger.info(f"Set importance for field {field_name} to {FIELD_IMPORTANCE[field_name]:.2f}")


def batch_process_confidence(extracted_data_list: List[ExtractedData]) -> Dict[str, Any]:
    """Process confidence scores for a batch of documents.
    
    This function processes confidence scores for a batch of documents,
    enriching them with confidence metadata and generating a summary report.
    
    Args:
        extracted_data_list: List of extraction results to process
        
    Returns:
        Dictionary containing batch processing results and summary
    """
    if not extracted_data_list:
        return {"count": 0, "message": "No documents to process"}
    
    # Create analyzer for batch statistics
    analyzer = ConfidenceAnalyzer()
    
    # Process each document
    for i, extracted_data in enumerate(extracted_data_list):
        # Enrich with confidence metadata
        extracted_data_list[i] = enrich_extraction_with_confidence_metadata(extracted_data)
        
        # Add to analyzer for statistics
        analyzer.add_document(extracted_data_list[i])
    
    # Generate summary report
    summary = {
        "count": len(extracted_data_list),
        "automation_rate": analyzer.get_overall_automation_rate(),
        "verification_rates": analyzer.get_field_verification_rates(),
        "document_confidence": analyzer.get_document_confidence_stats(),
        "threshold_suggestions": analyzer.suggest_threshold_adjustments()
    }
    
    return {
        "processed_documents": extracted_data_list,
        "summary": summary
    }


def estimate_automation_impact(current_thresholds: Dict[str, float], 
                             proposed_thresholds: Dict[str, float],
                             confidence_data: List[float]) -> Dict[str, Any]:
    """Estimate the impact of threshold changes on automation rate.
    
    This function estimates how changing confidence thresholds would
    affect the automation rate based on historical confidence data.
    
    Args:
        current_thresholds: Current confidence thresholds
        proposed_thresholds: Proposed confidence thresholds
        confidence_data: Historical confidence scores
        
    Returns:
        Dictionary containing impact analysis
    """
    if not confidence_data:
        return {"error": "No confidence data provided"}
    
    # Calculate current automation rate
    current_automated = sum(1 for c in confidence_data if c >= current_thresholds.get("default", DEFAULT_CONFIDENCE_THRESHOLD))
    current_rate = (current_automated / len(confidence_data)) * 100.0
    
    # Calculate proposed automation rate
    proposed_automated = sum(1 for c in confidence_data if c >= proposed_thresholds.get("default", DEFAULT_CONFIDENCE_THRESHOLD))
    proposed_rate = (proposed_automated / len(confidence_data)) * 100.0
    
    # Calculate impact
    impact = proposed_rate - current_rate
    relative_impact = (impact / current_rate) * 100.0 if current_rate > 0 else 0.0
    
    return {
        "current_rate": current_rate,
        "proposed_rate": proposed_rate,
        "absolute_impact": impact,
        "relative_impact": relative_impact,
        "sample_size": len(confidence_data),
        "current_threshold": current_thresholds.get("default", DEFAULT_CONFIDENCE_THRESHOLD),
        "proposed_threshold": proposed_thresholds.get("default", DEFAULT_CONFIDENCE_THRESHOLD)
    }


# Example usage of the confidence scoring module

'''
Example 1: Calculate confidence score for an extracted field

```python
# Character-level confidences from OCR model
char_confidences = [0.98, 0.95, 0.99, 0.97, 0.90, 0.85, 0.92, 0.94, 0.91]

# Calculate field confidence
field_confidence = calculate_field_confidence(
    field_name="business_name",
    raw_text="ACME Corp",
    char_confidences=char_confidences,
    model_type="typed_text",
    field_type=FieldType.NAME
)

print(f"Field confidence: {float(field_confidence):.2f}")
print(f"Requires verification: {field_confidence.is_low_confidence()}")
```

Example 2: Enrich extraction results with confidence metadata

```python
# Sample extraction results
extracted_data = {
    "extraction_id": "123456",
    "fields": {
        "business_name": {
            "field_name": "business_name",
            "field_type": "name",
            "value": "ACME Corp",
            "raw_text": "ACME Corp",
            "confidence": ConfidenceScore.from_float(0.92),
            "location": {
                "page": 0,
                "top": 0.1,
                "left": 0.1,
                "bottom": 0.15,
                "right": 0.5,
                "width": 0.4,
                "height": 0.05
            },
            "alternatives": [],
            "metadata": {},
            "requires_verification": False,
            "verification_reason": "",
            "extraction_timestamp": "2023-01-01T12:00:00Z"
        },
        "tax_id": {
            "field_name": "tax_id",
            "field_type": "ein",
            "value": "12-3456789",
            "raw_text": "12-3456789",
            "confidence": ConfidenceScore.from_float(0.65),
            "location": {
                "page": 0,
                "top": 0.2,
                "left": 0.1,
                "bottom": 0.25,
                "right": 0.3,
                "width": 0.2,
                "height": 0.05
            },
            "alternatives": [],
            "metadata": {},
            "requires_verification": False,
            "verification_reason": "",
            "extraction_timestamp": "2023-01-01T12:00:00Z"
        }
    },
    "tables": [],
    "metadata": {
        "extraction_id": "123456",
        "document_id": "doc123",
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
    "raw_text": "ACME Corp\n12-3456789",
    "low_confidence_fields": [],
    "requires_verification": False,
    "extraction_timestamp": "2023-01-01T12:00:00Z",
    "schema_version": "1.0",
    "document_type": "application_form"
}

# Enrich with confidence metadata
enriched_data = enrich_extraction_with_confidence_metadata(extracted_data)

# Check if document requires verification
if enriched_data["requires_verification"]:
    print("Document requires verification")
    print(f"Low confidence fields: {enriched_data['low_confidence_fields']}")
else:
    print("Document can be automated")
```

Example 3: Analyze confidence distribution

```python
# Sample confidence scores
confidences = [0.95, 0.87, 0.92, 0.65, 0.78, 0.91, 0.88, 0.72, 0.81, 0.79]

# Analyze distribution
distribution = analyze_confidence_distribution(confidences)

print(f"Mean confidence: {distribution['mean']:.2f}")
print(f"Median confidence: {distribution['median']:.2f}")
print(f"Low confidence percentage: {distribution['confidence_ranges']['low']:.1f}%")
print(f"High confidence percentage: {distribution['confidence_ranges']['high']:.1f}%")
```
'''