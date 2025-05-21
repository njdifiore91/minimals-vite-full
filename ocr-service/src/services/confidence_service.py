#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Confidence Service for OCR extraction results.

This module provides functionality for evaluating the confidence of extracted fields
from OCR results, providing scoring metrics, and flagging uncertain extractions for
human verification. It is critical for maintaining the 99% data extraction accuracy
requirement by identifying potential errors.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Union

import numpy as np

from ..config import app_config, tensorflow_config
from ..models.confidence_scoring import (
    calculate_field_confidence,
    normalize_confidence_score,
    calculate_document_confidence
)
from ..types.extraction import (
    ConfidenceScore,
    ExtractedData,
    ExtractedField,
    FieldConfidenceReport
)
from ..types.documents import DocumentType
from ..utils.logging_utils import get_logger


class ConfidenceService:
    """Service for evaluating confidence of OCR extraction results.
    
    This service is responsible for:
    1. Evaluating confidence scores from OCR results
    2. Applying thresholds to determine if human verification is needed
    3. Normalizing confidence scores across different document types
    4. Providing metrics for monitoring
    
    Attributes:
        logger: Logger instance for this service
        config: Application configuration
        thresholds: Confidence thresholds for different document types
        field_importance: Dictionary mapping field names to importance weights
    """
    
    def __init__(self):
        """Initialize the ConfidenceService with configuration settings."""
        self.logger = get_logger(__name__)
        self.config = app_config
        self.tf_config = tensorflow_config
        
        # Load confidence thresholds from configuration
        self.thresholds = self.tf_config.confidence_thresholds
        
        # Field importance weights for different document types
        # Higher weight means the field is more important for accuracy
        self.field_importance = self._load_field_importance()
        
        self.logger.info("ConfidenceService initialized with thresholds: %s", self.thresholds)
    
    def _load_field_importance(self) -> Dict[str, Dict[str, float]]:
        """Load field importance weights for different document types.
        
        Returns:
            Dictionary mapping document types to field importance weights
        """
        # Default field importance if not specified in config
        default_importance = {
            "default": {
                "default": 1.0  # Default weight for any field
            }
        }
        
        # Try to load from config, fall back to defaults if not found
        try:
            field_importance = self.tf_config.field_importance
            if not field_importance:
                return default_importance
            return field_importance
        except (AttributeError, KeyError):
            self.logger.warning("Field importance not found in config, using defaults")
            return default_importance
    
    def evaluate_field_confidence(
        self, field: ExtractedField, document_type: DocumentType
    ) -> ConfidenceScore:
        """Evaluate the confidence score for a single extracted field.
        
        Args:
            field: The extracted field to evaluate
            document_type: The type of document the field was extracted from
            
        Returns:
            Normalized confidence score for the field
        """
        # Get raw confidence from the field
        raw_confidence = field.confidence
        
        # Apply field-specific normalization based on document type
        normalized_confidence = normalize_confidence_score(
            raw_confidence,
            field.name,
            document_type
        )
        
        self.logger.debug(
            "Field %s confidence: raw=%.4f, normalized=%.4f",
            field.name, raw_confidence, normalized_confidence
        )
        
        return normalized_confidence
    
    def evaluate_extraction_confidence(
        self, extracted_data: ExtractedData
    ) -> Tuple[float, Dict[str, FieldConfidenceReport]]:
        """Evaluate the confidence of an entire extraction result.
        
        This method calculates confidence scores for each field and an overall
        document confidence score based on weighted field confidences.
        
        Args:
            extracted_data: The complete extraction result to evaluate
            
        Returns:
            Tuple containing:
            - Overall document confidence score (0.0-1.0)
            - Dictionary of field confidence reports
        """
        document_type = extracted_data.document_type
        field_reports = {}
        field_confidences = []
        field_weights = []
        
        # Get importance weights for this document type
        importance_weights = self.field_importance.get(
            document_type.value,
            self.field_importance.get("default", {"default": 1.0})
        )
        
        # Default weight if not specified for a field
        default_weight = importance_weights.get("default", 1.0)
        
        # Evaluate each field
        for field in extracted_data.fields:
            # Get normalized confidence score
            confidence = self.evaluate_field_confidence(field, document_type)
            
            # Get importance weight for this field
            weight = importance_weights.get(field.name, default_weight)
            
            # Get threshold for this field/document type
            threshold = self._get_threshold(field.name, document_type)
            
            # Determine if field needs human verification
            needs_verification = confidence < threshold
            
            # Create field confidence report
            field_reports[field.name] = FieldConfidenceReport(
                field_name=field.name,
                confidence=confidence,
                threshold=threshold,
                needs_verification=needs_verification,
                importance_weight=weight
            )
            
            # Add to lists for weighted average calculation
            field_confidences.append(confidence)
            field_weights.append(weight)
        
        # Calculate overall document confidence score
        if field_confidences:
            # Use weighted average for document confidence
            document_confidence = np.average(field_confidences, weights=field_weights)
        else:
            document_confidence = 0.0
        
        self.logger.info(
            "Document confidence: %.4f (document_type=%s, fields=%d)",
            document_confidence, document_type.value, len(field_reports)
        )
        
        return document_confidence, field_reports
    
    def needs_human_verification(
        self, extracted_data: ExtractedData
    ) -> Tuple[bool, Set[str]]:
        """Determine if the extraction needs human verification.
        
        This method evaluates the extraction confidence and determines if
        human verification is needed based on configured thresholds.
        
        Args:
            extracted_data: The complete extraction result to evaluate
            
        Returns:
            Tuple containing:
            - Boolean indicating if human verification is needed
            - Set of field names that need verification
        """
        document_confidence, field_reports = self.evaluate_extraction_confidence(extracted_data)
        document_type = extracted_data.document_type
        
        # Get document-level threshold
        doc_threshold = self.thresholds.get(
            f"document.{document_type.value}",
            self.thresholds.get("document.default", 0.85)
        )
        
        # Check if document confidence is below threshold
        doc_needs_verification = document_confidence < doc_threshold
        
        # Collect fields that need verification
        fields_needing_verification = {
            field_name for field_name, report in field_reports.items()
            if report.needs_verification
        }
        
        # Document needs verification if overall confidence is low or any critical fields need verification
        needs_verification = doc_needs_verification or bool(fields_needing_verification)
        
        self.logger.info(
            "Verification needed: %s (document_confidence=%.4f, threshold=%.4f, fields_needing_verification=%d)",
            needs_verification, document_confidence, doc_threshold, len(fields_needing_verification)
        )
        
        return needs_verification, fields_needing_verification
    
    def _get_threshold(self, field_name: str, document_type: DocumentType) -> float:
        """Get the confidence threshold for a specific field and document type.
        
        Args:
            field_name: Name of the field
            document_type: Type of document
            
        Returns:
            Confidence threshold value (0.0-1.0)
        """
        # Try field-specific threshold for this document type
        threshold_key = f"field.{document_type.value}.{field_name}"
        threshold = self.thresholds.get(threshold_key)
        
        if threshold is not None:
            return threshold
        
        # Try document-type default threshold
        threshold_key = f"field.{document_type.value}.default"
        threshold = self.thresholds.get(threshold_key)
        
        if threshold is not None:
            return threshold
        
        # Try field-specific threshold for any document type
        threshold_key = f"field.default.{field_name}"
        threshold = self.thresholds.get(threshold_key)
        
        if threshold is not None:
            return threshold
        
        # Fall back to global default threshold
        return self.thresholds.get("field.default.default", 0.75)
    
    def get_confidence_metrics(self, extracted_data: ExtractedData) -> Dict[str, float]:
        """Generate confidence metrics for monitoring and reporting.
        
        Args:
            extracted_data: The extraction result to generate metrics for
            
        Returns:
            Dictionary of metrics for monitoring systems
        """
        document_confidence, field_reports = self.evaluate_extraction_confidence(extracted_data)
        document_type = extracted_data.document_type
        
        # Calculate metrics
        field_confidences = [report.confidence for report in field_reports.values()]
        verification_needed, fields_needing_verification = self.needs_human_verification(extracted_data)
        
        metrics = {
            "document_confidence": document_confidence,
            "fields_count": len(field_reports),
            "fields_needing_verification": len(fields_needing_verification),
            "verification_needed": 1.0 if verification_needed else 0.0,
            "min_field_confidence": min(field_confidences) if field_confidences else 0.0,
            "max_field_confidence": max(field_confidences) if field_confidences else 0.0,
            "avg_field_confidence": np.mean(field_confidences) if field_confidences else 0.0,
            "document_type": hash(document_type.value) % 100  # Hash for numeric representation
        }
        
        return metrics
    
    def enrich_extraction_with_confidence(
        self, extracted_data: ExtractedData
    ) -> ExtractedData:
        """Enrich extraction data with confidence information.
        
        This method adds confidence scores and verification flags to the
        extraction result for downstream processing.
        
        Args:
            extracted_data: The extraction result to enrich
            
        Returns:
            Enriched extraction data with confidence information
        """
        document_confidence, field_reports = self.evaluate_extraction_confidence(extracted_data)
        verification_needed, fields_needing_verification = self.needs_human_verification(extracted_data)
        
        # Create a copy to avoid modifying the original
        enriched_data = extracted_data.copy()
        
        # Add confidence metadata
        enriched_data.metadata["document_confidence"] = document_confidence
        enriched_data.metadata["verification_needed"] = verification_needed
        enriched_data.metadata["fields_needing_verification"] = list(fields_needing_verification)
        
        # Update field confidence information
        for field in enriched_data.fields:
            if field.name in field_reports:
                report = field_reports[field.name]
                field.confidence = report.confidence
                field.metadata["needs_verification"] = report.needs_verification
                field.metadata["threshold"] = report.threshold
        
        return enriched_data