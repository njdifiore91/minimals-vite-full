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
from typing import Dict, List, Optional, Tuple, Union, Any

# Import types
from ..types.extraction import (
    ConfidenceScore,
    ExtractedData,
    ExtractedField,
    FieldLocation
)
from ..types.models import ModelType
from ..types.config import ConfigDict

# Import utilities
from ..utils.logging_utils import get_logger
from ..models.confidence_scoring import calculate_base_confidence

logger = get_logger(__name__)


class ConfidenceService:
    """Service for evaluating confidence of OCR extraction results.
    
    This service provides methods for calculating confidence scores for extracted
    fields, normalizing scores across different document types, and flagging
    low-confidence extractions for human verification. It is critical for maintaining
    the 99% data extraction accuracy requirement by identifying potential errors.
    
    The service implements several key features:
    1. Field-level confidence scoring with document type normalization
    2. Document-level confidence assessment with weighted field importance
    3. Threshold-based flagging for human verification
    4. Confidence metrics for monitoring and optimization
    5. Suspicious pattern detection for additional verification triggers
    
    This service works in conjunction with the OCR models to ensure that
    extraction results meet the required accuracy standards and that human
    verification is applied where needed to maintain quality.
    """
    
    def __init__(self, config: ConfigDict):
        """Initialize the ConfidenceService with configuration.
        
        Args:
            config: Configuration dictionary containing confidence thresholds
                   and scoring parameters.
        """
        self.config = config
        
        # Default confidence thresholds if not specified in config
        self.thresholds = {
            'high': config.get('confidence_threshold_high', 0.9),
            'medium': config.get('confidence_threshold_medium', 0.75),
            'low': config.get('confidence_threshold_low', 0.5),
            'critical_fields': config.get('confidence_threshold_critical', 0.85)
        }
        
        # Field importance weights by document type
        self.field_importance = config.get('field_importance', {})
        
        # Document type specific confidence adjustments
        self.doc_type_adjustments = config.get('doc_type_adjustments', {})
        
        # Critical fields that require higher confidence
        default_critical_fields = [
            'tax_id', 'ein', 'ssn', 'account_number', 'loan_amount', 
            'requested_amount', 'applicant_name', 'business_name',
            'adjusted_gross_income', 'total_tax', 'ending_balance'
        ]
        self.critical_fields = config.get('critical_fields', default_critical_fields)
        
        # Configure verification thresholds
        self.verification_thresholds = {
            'low_confidence_ratio': config.get('verification_threshold_low_confidence_ratio', 0.25),
            'missing_critical_ratio': config.get('verification_threshold_missing_critical_ratio', 0.5)
        }
        
        logger.info(f"Initialized ConfidenceService with thresholds: {self.thresholds}")
        logger.info(f"Critical fields configured: {self.critical_fields}")
    
    def evaluate_field_confidence(self, field: ExtractedField) -> ConfidenceScore:
        """Evaluate the confidence score of a single extracted field.
        
        This method applies field-specific adjustments based on field type,
        content characteristics, and extraction method.
        
        Args:
            field: The extracted field to evaluate.
            
        Returns:
            Normalized confidence score for the field.
        """
        # Start with the raw confidence from the OCR model
        raw_confidence = field.confidence
        
        # Get base confidence from the confidence_scoring model
        # This uses TensorFlow model's internal confidence metrics
        base_confidence = calculate_base_confidence(field)
        
        # Use the higher of raw confidence or base confidence as starting point
        # This helps when the model's internal metrics are more reliable
        adjusted_confidence = max(raw_confidence, base_confidence)
        
        # Apply adjustments based on field characteristics
        
        # Adjust based on field length (very short or very long fields may be less reliable)
        if field.value and isinstance(field.value, str):
            length = len(field.value)
            if length < 3 and adjusted_confidence < 0.95:
                # Short fields are penalized unless very high confidence
                adjusted_confidence *= 0.9
            elif length > 50:
                # Long fields get a small penalty as they're more likely to contain errors
                adjusted_confidence *= 0.95
        
        # Adjust based on field type (e.g., numeric fields with non-numeric characters)
        if field.field_type == 'numeric' and field.value:
            if not str(field.value).replace('.', '').replace('-', '').isdigit():
                adjusted_confidence *= 0.7  # Significant penalty for wrong data type
        
        # Adjust for critical fields that require higher confidence
        if field.name in self.critical_fields:
            # Critical fields use a different threshold, so adjust confidence accordingly
            critical_threshold = self.thresholds['critical_fields']
            if adjusted_confidence < critical_threshold:
                # Mark clearly below threshold
                adjusted_confidence *= 0.9
        
        # Check for common patterns that indicate potential errors
        if field.field_type == 'date' and field.value:
            # Simple date validation - this would be more comprehensive in production
            if not self._is_valid_date_format(str(field.value)):
                adjusted_confidence *= 0.8
        
        # Ensure confidence is in valid range [0.0, 1.0]
        adjusted_confidence = max(0.0, min(1.0, adjusted_confidence))
        
        logger.debug(f"Field confidence for {field.name}: {raw_confidence:.4f} -> {adjusted_confidence:.4f}")
        return ConfidenceScore(adjusted_confidence)
    
    def _is_valid_date_format(self, date_str: str) -> bool:
        """Simple helper to check if a string looks like a valid date format.
        
        Args:
            date_str: String to check for date format.
            
        Returns:
            True if the string appears to be in a valid date format.
        """
        # This is a simplified check - in production this would be more comprehensive
        import re
        # Check for common date formats (MM/DD/YYYY, YYYY-MM-DD, etc.)
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{2,4}',  # MM/DD/YY or MM/DD/YYYY
            r'\d{4}-\d{1,2}-\d{1,2}',  # YYYY-MM-DD
            r'\d{1,2}-\d{1,2}-\d{2,4}',  # DD-MM-YY or DD-MM-YYYY
            r'\d{1,2}\.\d{1,2}\.\d{2,4}'  # DD.MM.YY or DD.MM.YYYY
        ]
        
        return any(re.match(pattern, date_str) for pattern in date_patterns)
    
    def normalize_confidence_by_document_type(self, 
                                             confidence: float, 
                                             doc_type: str) -> float:
        """Normalize confidence scores based on document type.
        
        Different document types may have different baseline confidence levels
        due to varying complexity, quality, and structure. This method normalizes
        confidence scores to ensure consistent thresholds across document types.
        
        Args:
            confidence: Raw confidence score.
            doc_type: Document type identifier.
            
        Returns:
            Normalized confidence score adjusted for document type.
        """
        # Document type specific adjustments based on known complexity and quality issues
        # These adjustments are based on empirical analysis of document processing accuracy
        default_adjustments = {
            'loan_application': 1.0,      # Baseline - no adjustment
            'tax_return': 0.95,           # Tax returns often have complex tables
            'bank_statement': 0.92,       # Bank statements have varied formats
            'pay_stub': 0.98,             # Pay stubs are usually well-structured
            'identity_document': 0.90,    # ID documents often have security features that interfere with OCR
            'invoice': 0.94,              # Invoices have varied layouts
            'handwritten_form': 0.85      # Handwritten forms are inherently less reliable
        }
        
        # Get adjustment factor from config, falling back to default adjustments if not specified
        # This allows for runtime configuration without code changes
        adjustment = self.doc_type_adjustments.get(
            doc_type, 
            default_adjustments.get(doc_type, 1.0)
        )
        
        # Apply adjustment factor
        normalized = confidence * adjustment
        
        # Ensure confidence is in valid range [0.0, 1.0]
        normalized = max(0.0, min(1.0, normalized))
        
        logger.debug(f"Normalized confidence for {doc_type}: {confidence} -> {normalized} (adjustment: {adjustment})")
        return normalized
    
    def calculate_document_confidence(self, extracted_data: ExtractedData) -> float:
        """Calculate overall confidence score for the entire document.
        
        This method computes a weighted average of field confidences, giving
        more weight to critical fields and adjusting based on document type.
        It also considers document structure and completeness.
        
        Args:
            extracted_data: The complete extracted data from a document.
            
        Returns:
            Overall document confidence score.
        """
        if not extracted_data.fields:
            logger.warning("No fields in extracted data to calculate document confidence")
            return 0.0
        
        total_weight = 0.0
        weighted_confidence_sum = 0.0
        doc_type = extracted_data.document_type
        
        # Default field importance weights by document type if not in config
        default_field_weights = {
            'loan_application': {
                'applicant_name': 2.0,
                'business_name': 2.0,
                'tax_id': 2.5,
                'requested_amount': 2.0,
                'business_address': 1.5,
                'phone_number': 1.0,
                'email': 1.0,
                'signature': 2.0
            },
            'tax_return': {
                'taxpayer_name': 2.0,
                'tax_id': 2.5,
                'tax_year': 2.0,
                'adjusted_gross_income': 2.5,
                'total_tax': 2.0,
                'signature': 1.5
            },
            'bank_statement': {
                'account_holder': 2.0,
                'account_number': 2.5,
                'statement_date': 1.5,
                'beginning_balance': 2.0,
                'ending_balance': 2.0,
                'total_deposits': 1.5,
                'total_withdrawals': 1.5
            }
        }
        
        # Get field importance weights for this document type from config or defaults
        field_weights = self.field_importance.get(
            doc_type, 
            default_field_weights.get(doc_type, {})
        )
        
        # Track missing critical fields
        expected_fields = set(field_weights.keys())
        found_fields = set()
        
        for field in extracted_data.fields:
            found_fields.add(field.name)
            
            # Get field weight, default to 1.0 if not specified
            weight = field_weights.get(field.name, 1.0)
            
            # Critical fields get double weight if not already weighted
            if field.name in self.critical_fields and weight == 1.0:
                weight *= 2.0
                
            # Add to weighted sum
            weighted_confidence_sum += field.confidence * weight
            total_weight += weight
        
        # Calculate weighted average of field confidences
        if total_weight > 0:
            field_confidence = weighted_confidence_sum / total_weight
        else:
            field_confidence = 0.0
        
        # Calculate document completeness factor
        # Missing critical fields significantly reduce overall confidence
        missing_critical_fields = [f for f in self.critical_fields if f not in found_fields]
        completeness_factor = 1.0
        
        if missing_critical_fields:
            # Reduce confidence based on missing critical fields
            # More missing fields = lower confidence
            missing_ratio = len(missing_critical_fields) / len(self.critical_fields) \
                if self.critical_fields else 0
            completeness_factor = max(0.5, 1.0 - missing_ratio)
            logger.warning(f"Missing critical fields: {missing_critical_fields}")
        
        # Apply completeness factor to field confidence
        doc_confidence = field_confidence * completeness_factor
            
        # Normalize by document type
        normalized_confidence = self.normalize_confidence_by_document_type(
            doc_confidence, doc_type)
        
        logger.info(f"Document confidence for {doc_type}: {normalized_confidence:.4f} "
                  f"(field confidence: {field_confidence:.4f}, completeness: {completeness_factor:.2f})")
        return normalized_confidence
    
    def flag_low_confidence_fields(self, 
                                  extracted_data: ExtractedData) -> List[ExtractedField]:
        """Identify fields with confidence below acceptable thresholds.
        
        This method flags fields that require human verification due to low
        confidence scores, with special attention to critical fields that
        may have higher confidence requirements.
        
        Args:
            extracted_data: The complete extracted data from a document.
            
        Returns:
            List of fields that require human verification.
        """
        low_confidence_fields = []
        doc_type = extracted_data.document_type
        
        # Define field-specific thresholds for common document types
        # These override the general thresholds for specific fields that may need
        # special handling based on their importance or typical OCR challenges
        field_specific_thresholds = {
            'loan_application': {
                'tax_id': 0.95,           # Tax ID/EIN needs very high confidence
                'requested_amount': 0.90,  # Loan amount needs high confidence
                'signature': 0.80          # Signatures are inherently variable
            },
            'tax_return': {
                'tax_id': 0.95,            # Tax ID/EIN needs very high confidence
                'adjusted_gross_income': 0.90,  # Financial figures need high confidence
                'total_tax': 0.90          # Financial figures need high confidence
            },
            'bank_statement': {
                'account_number': 0.95,     # Account numbers need very high confidence
                'ending_balance': 0.90     # Financial figures need high confidence
            }
        }
        
        # Get document-specific field thresholds
        doc_field_thresholds = field_specific_thresholds.get(doc_type, {})
        
        for field in extracted_data.fields:
            # Determine appropriate threshold with this priority:
            # 1. Field-specific threshold for this document type
            # 2. Critical field threshold if it's a critical field
            # 3. Default medium threshold
            if field.name in doc_field_thresholds:
                threshold = doc_field_thresholds[field.name]
            elif field.name in self.critical_fields:
                threshold = self.thresholds['critical_fields']
            else:
                threshold = self.thresholds['medium']
            
            # Normalize confidence for this document type
            normalized_confidence = self.normalize_confidence_by_document_type(
                field.confidence, doc_type)
            
            # Flag if below threshold
            if normalized_confidence < threshold:
                low_confidence_fields.append(field)
                logger.debug(f"Flagged low confidence field: {field.name} = {field.value} "
                           f"(confidence: {normalized_confidence:.4f}, threshold: {threshold})")
                
                # Add reason for flagging to help human reviewers
                field.metadata['verification_reason'] = (
                    f"Confidence {normalized_confidence:.2f} below threshold {threshold:.2f}"
                )
                
                # For numeric fields, add additional context if the value seems suspicious
                if field.field_type == 'numeric' and field.value:
                    try:
                        value = float(field.value)
                        # Check for suspiciously high or low values based on field name
                        if 'amount' in field.name.lower() and value > 1000000:
                            field.metadata['verification_reason'] += "; Unusually high amount"
                        elif 'balance' in field.name.lower() and value < 0:
                            field.metadata['verification_reason'] += "; Negative balance"
                    except (ValueError, TypeError):
                        # If conversion fails, that's another reason for verification
                        field.metadata['verification_reason'] += "; Non-numeric value in numeric field"
        
        return low_confidence_fields
    
    def requires_human_verification(self, extracted_data: ExtractedData) -> bool:
        """Determine if the document requires human verification.
        
        This method evaluates both document-level confidence and individual
        field confidences to determine if human verification is required.
        It implements a multi-factor decision process to ensure 99% accuracy.
        
        Args:
            extracted_data: The complete extracted data from a document.
            
        Returns:
            True if human verification is required, False otherwise.
        """
        verification_reasons = []
        
        # Calculate document confidence
        doc_confidence = self.calculate_document_confidence(extracted_data)
        
        # Check if document confidence is below threshold
        if doc_confidence < self.thresholds['medium']:
            reason = f"Overall confidence {doc_confidence:.4f} below threshold {self.thresholds['medium']}"
            verification_reasons.append(reason)
            logger.info(f"Document requires verification: {reason}")
        
        # Check for critical fields with low confidence
        critical_field_issues = []
        for field in extracted_data.fields:
            if field.name in self.critical_fields:
                normalized_confidence = self.normalize_confidence_by_document_type(
                    field.confidence, extracted_data.document_type)
                
                if normalized_confidence < self.thresholds['critical_fields']:
                    issue = f"Critical field '{field.name}' has confidence {normalized_confidence:.4f} below threshold {self.thresholds['critical_fields']}"
                    critical_field_issues.append(issue)
        
        if critical_field_issues:
            verification_reasons.append(f"Critical field issues: {len(critical_field_issues)}")
            for issue in critical_field_issues:
                logger.info(f"Document requires verification: {issue}")
        
        # Check for missing critical fields
        field_names = {field.name for field in extracted_data.fields}
        missing_critical = [name for name in self.critical_fields if name not in field_names]
        if missing_critical:
            reason = f"Missing critical fields: {', '.join(missing_critical)}"
            verification_reasons.append(reason)
            logger.info(f"Document requires verification: {reason}")
        
        # Check if too many fields have low confidence
        low_confidence_fields = self.flag_low_confidence_fields(extracted_data)
        low_confidence_ratio = len(low_confidence_fields) / len(extracted_data.fields) \
            if extracted_data.fields else 0
        
        if low_confidence_ratio > 0.25:  # If more than 25% of fields have low confidence
            reason = f"{len(low_confidence_fields)} of {len(extracted_data.fields)} fields have low confidence ({low_confidence_ratio:.2%})"
            verification_reasons.append(reason)
            logger.info(f"Document requires verification: {reason}")
        
        # Check for suspicious data patterns that might indicate OCR errors
        suspicious_patterns = self._check_suspicious_patterns(extracted_data)
        if suspicious_patterns:
            reason = f"Suspicious data patterns detected: {', '.join(suspicious_patterns)}"
            verification_reasons.append(reason)
            logger.info(f"Document requires verification: {reason}")
        
        # Store verification reasons in metadata for reporting
        extracted_data.metadata['verification_reasons'] = verification_reasons
        
        if verification_reasons:
            return True
        
        logger.info(f"Document passed confidence checks with score {doc_confidence:.4f}")
        return False
    
    def _check_suspicious_patterns(self, extracted_data: ExtractedData) -> List[str]:
        """Check for suspicious patterns in the extracted data that might indicate OCR errors.
        
        Args:
            extracted_data: The complete extracted data from a document.
            
        Returns:
            List of suspicious patterns detected.
        """
        suspicious_patterns = []
        doc_type = extracted_data.document_type
        
        # Check for inconsistent dates
        dates = {}
        for field in extracted_data.fields:
            if field.field_type == 'date' and field.value:
                dates[field.name] = field.value
        
        # Example: Check if statement_date is after report_date
        if 'statement_date' in dates and 'report_date' in dates:
            try:
                from datetime import datetime
                # This is simplified - would need proper date parsing in production
                statement_date = datetime.strptime(str(dates['statement_date']), '%Y-%m-%d')
                report_date = datetime.strptime(str(dates['report_date']), '%Y-%m-%d')
                
                if statement_date > report_date:
                    suspicious_patterns.append(f"Statement date {statement_date} is after report date {report_date}")
            except (ValueError, TypeError):
                # Date parsing failed - this itself is suspicious
                suspicious_patterns.append("Date format inconsistency detected")
        
        # Check for numeric inconsistencies in financial documents
        if doc_type in ['bank_statement', 'tax_return', 'loan_application']:
            # Example: Check if ending_balance = beginning_balance + total_deposits - total_withdrawals
            try:
                numeric_fields = {}
                for field in extracted_data.fields:
                    if field.field_type == 'numeric' and field.value is not None:
                        try:
                            numeric_fields[field.name] = float(field.value)
                        except (ValueError, TypeError):
                            pass
                
                # Bank statement balance check
                if all(k in numeric_fields for k in ['beginning_balance', 'ending_balance', 'total_deposits', 'total_withdrawals']):
                    expected_ending = numeric_fields['beginning_balance'] + numeric_fields['total_deposits'] - numeric_fields['total_withdrawals']
                    actual_ending = numeric_fields['ending_balance']
                    
                    # Allow for small rounding differences
                    if abs(expected_ending - actual_ending) > 0.1:
                        suspicious_patterns.append(f"Balance mismatch: expected ending {expected_ending:.2f}, got {actual_ending:.2f}")
            except Exception as e:
                logger.warning(f"Error checking numeric consistency: {str(e)}")
        
        return suspicious_patterns
    
    def get_confidence_metrics(self, extracted_data: ExtractedData) -> Dict[str, Any]:
        """Generate confidence metrics for monitoring and reporting.
        
        This method calculates various confidence metrics for the document,
        which can be used for monitoring, optimization, and reporting.
        These metrics are essential for maintaining the 99% data extraction
        accuracy requirement and for continuous service improvement.
        
        Args:
            extracted_data: The complete extracted data from a document.
            
        Returns:
            Dictionary of confidence metrics.
        """
        # Calculate document confidence
        doc_confidence = self.calculate_document_confidence(extracted_data)
        
        # Flag low confidence fields
        low_confidence_fields = self.flag_low_confidence_fields(extracted_data)
        
        # Check if human verification is required
        requires_verification = self.requires_human_verification(extracted_data)
        verification_reasons = extracted_data.metadata.get('verification_reasons', [])
        
        # Calculate confidence metrics
        metrics = {
            'document_confidence': doc_confidence,
            'requires_verification': requires_verification,
            'verification_reasons': verification_reasons,
            'low_confidence_field_count': len(low_confidence_fields),
            'total_field_count': len(extracted_data.fields),
            'low_confidence_ratio': len(low_confidence_fields) / len(extracted_data.fields) \
                if extracted_data.fields else 0,
            'confidence_by_field_type': {},
            'critical_fields_confidence': {},
            'document_type': extracted_data.document_type,
            'processing_timestamp': extracted_data.metadata.get('processing_timestamp'),
            'model_version': extracted_data.metadata.get('model_version'),
            'confidence_distribution': {
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
        
        # Calculate confidence by field type
        field_type_confidences = {}
        for field in extracted_data.fields:
            field_type = field.field_type
            if field_type not in field_type_confidences:
                field_type_confidences[field_type] = []
            field_type_confidences[field_type].append(field.confidence)
            
            # Count fields by confidence category
            normalized_confidence = self.normalize_confidence_by_document_type(
                field.confidence, extracted_data.document_type)
            
            if normalized_confidence >= self.thresholds['high']:
                metrics['confidence_distribution']['high'] += 1
            elif normalized_confidence >= self.thresholds['medium']:
                metrics['confidence_distribution']['medium'] += 1
            else:
                metrics['confidence_distribution']['low'] += 1
        
        # Calculate average confidence by field type
        for field_type, confidences in field_type_confidences.items():
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            metrics['confidence_by_field_type'][field_type] = {
                'average': avg_confidence,
                'min': min(confidences) if confidences else 0,
                'max': max(confidences) if confidences else 0,
                'count': len(confidences)
            }
        
        # Calculate confidence for critical fields
        missing_critical_fields = []
        for critical_field in self.critical_fields:
            found = False
            for field in extracted_data.fields:
                if field.name == critical_field:
                    metrics['critical_fields_confidence'][critical_field] = {
                        'confidence': field.confidence,
                        'normalized_confidence': self.normalize_confidence_by_document_type(
                            field.confidence, extracted_data.document_type),
                        'requires_verification': field.name in [f.name for f in low_confidence_fields]
                    }
                    found = True
                    break
            
            if not found:
                missing_critical_fields.append(critical_field)
        
        metrics['missing_critical_fields'] = missing_critical_fields
        
        # Add performance metrics
        if 'processing_time_ms' in extracted_data.metadata:
            metrics['processing_time_ms'] = extracted_data.metadata['processing_time_ms']
        
        # Add document quality metrics if available
        if 'document_quality' in extracted_data.metadata:
            metrics['document_quality'] = extracted_data.metadata['document_quality']
        
        logger.debug(f"Generated confidence metrics for document: {metrics['document_confidence']:.4f} confidence, "
                   f"{metrics['low_confidence_field_count']} low confidence fields")
        return metrics
    
    def enrich_with_confidence_data(self, extracted_data: ExtractedData) -> ExtractedData:
        """Enrich extracted data with confidence information.
        
        This method adds confidence metadata to the extracted data, including
        flags for fields requiring verification and overall confidence metrics.
        This enrichment is critical for maintaining the 99% data extraction
        accuracy requirement by enabling downstream services to make informed
        decisions about automated processing versus human review.
        
        Args:
            extracted_data: The complete extracted data from a document.
            
        Returns:
            Enriched extracted data with confidence information.
        """
        # Calculate document confidence
        doc_confidence = self.calculate_document_confidence(extracted_data)
        
        # Flag low confidence fields
        low_confidence_fields = self.flag_low_confidence_fields(extracted_data)
        low_confidence_field_names = [field.name for field in low_confidence_fields]
        
        # Determine if human verification is required
        requires_verification = self.requires_human_verification(extracted_data)
        
        # Generate confidence metrics
        confidence_metrics = self.get_confidence_metrics(extracted_data)
        
        # Add confidence metadata to extracted data
        extracted_data.metadata['document_confidence'] = doc_confidence
        extracted_data.metadata['requires_verification'] = requires_verification
        extracted_data.metadata['low_confidence_fields'] = low_confidence_field_names
        extracted_data.metadata['confidence_metrics'] = confidence_metrics
        
        # Add verification priority based on document confidence
        if requires_verification:
            if doc_confidence < self.thresholds['low']:
                verification_priority = 'high'
            elif doc_confidence < self.thresholds['medium']:
                verification_priority = 'medium'
            else:
                verification_priority = 'low'
            
            extracted_data.metadata['verification_priority'] = verification_priority
        
        # Mark each field with its confidence category and verification status
        for field in extracted_data.fields:
            normalized_confidence = self.normalize_confidence_by_document_type(
                field.confidence, extracted_data.document_type)
            
            if normalized_confidence >= self.thresholds['high']:
                confidence_category = 'high'
            elif normalized_confidence >= self.thresholds['medium']:
                confidence_category = 'medium'
            else:
                confidence_category = 'low'
            
            requires_field_verification = field.name in low_confidence_field_names
            
            # Enrich field with confidence metadata
            field.metadata['confidence_category'] = confidence_category
            field.metadata['normalized_confidence'] = normalized_confidence
            field.metadata['requires_verification'] = requires_field_verification
            
            # Add field-specific verification guidance for human reviewers
            if requires_field_verification:
                if field.name in self.critical_fields:
                    field.metadata['verification_priority'] = 'high'
                    field.metadata['verification_note'] = 'Critical field requiring verification'
                elif confidence_category == 'low':
                    field.metadata['verification_priority'] = 'medium'
                    field.metadata['verification_note'] = 'Low confidence extraction'
                else:
                    field.metadata['verification_priority'] = 'low'
                    field.metadata['verification_note'] = 'Verification recommended'
        
        # Add document-level verification guidance
        if requires_verification:
            verification_reasons = extracted_data.metadata.get('verification_reasons', [])
            extracted_data.metadata['verification_guidance'] = {
                'priority': verification_priority,
                'reasons': verification_reasons,
                'critical_fields': [f for f in self.critical_fields if f in low_confidence_field_names],
                'suggested_focus': [f.name for f in low_confidence_fields[:5]]  # Top 5 fields to check
            }
        
        logger.info(f"Enriched document with confidence data: {doc_confidence:.4f} confidence, "
                  f"verification {'required' if requires_verification else 'not required'}")
        return extracted_data