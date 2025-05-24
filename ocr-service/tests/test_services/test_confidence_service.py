#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the confidence evaluation service.

This module contains tests for the ConfidenceService class, which is responsible for
evaluating the confidence of extracted fields from OCR results, providing scoring metrics,
and flagging uncertain extractions for human verification.

These tests verify that the confidence service correctly identifies uncertain extractions
for human verification to maintain the 99% data extraction accuracy requirement.
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the service and types
from src.services.confidence_service import ConfidenceService
from src.types.extraction import (
    ExtractedField,
    ExtractedData,
    FieldLocation,
    ConfidenceScore
)
from src.types.models import OCRModelType


# Fixtures for test data
@pytest.fixture
def config_dict():
    """Fixture for test configuration."""
    return {
        'confidence_threshold_high': 0.9,
        'confidence_threshold_medium': 0.75,
        'confidence_threshold_low': 0.5,
        'confidence_threshold_critical': 0.85,
        'field_importance': {
            'loan_application': {
                'applicant_name': 2.0,
                'business_name': 2.0,
                'tax_id': 2.5,
                'requested_amount': 2.0
            }
        },
        'doc_type_adjustments': {
            'loan_application': 1.0,
            'tax_return': 0.95,
            'bank_statement': 0.92,
            'handwritten_form': 0.85
        },
        'critical_fields': [
            'tax_id', 'ein', 'ssn', 'account_number', 'loan_amount',
            'requested_amount', 'applicant_name', 'business_name'
        ]
    }


@pytest.fixture
def confidence_service(config_dict):
    """Fixture for ConfidenceService instance."""
    return ConfidenceService(config_dict)


@pytest.fixture
def sample_field():
    """Fixture for a sample extracted field."""
    return {
        'name': 'business_name',
        'value': 'Acme Corporation',
        'confidence': 0.85,
        'field_type': 'text',
        'metadata': {}
    }


@pytest.fixture
def sample_critical_field():
    """Fixture for a sample critical field."""
    return {
        'name': 'tax_id',
        'value': '12-3456789',
        'confidence': 0.82,
        'field_type': 'ein',
        'metadata': {}
    }


@pytest.fixture
def sample_low_confidence_field():
    """Fixture for a sample low confidence field."""
    return {
        'name': 'address',
        'value': '123 Main St, Anytown, USA',
        'confidence': 0.60,
        'field_type': 'text',
        'metadata': {}
    }


@pytest.fixture
def sample_extracted_data():
    """Fixture for sample extracted data with multiple fields."""
    return {
        'document_type': 'loan_application',
        'fields': [
            {
                'name': 'business_name',
                'value': 'Acme Corporation',
                'confidence': 0.95,
                'field_type': 'text',
                'metadata': {}
            },
            {
                'name': 'tax_id',
                'value': '12-3456789',
                'confidence': 0.88,
                'field_type': 'ein',
                'metadata': {}
            },
            {
                'name': 'requested_amount',
                'value': '50000',
                'confidence': 0.92,
                'field_type': 'numeric',
                'metadata': {}
            },
            {
                'name': 'address',
                'value': '123 Main St, Anytown, USA',
                'confidence': 0.75,
                'field_type': 'text',
                'metadata': {}
            },
            {
                'name': 'application_date',
                'value': '2023-05-15',
                'confidence': 0.89,
                'field_type': 'date',
                'metadata': {}
            }
        ],
        'metadata': {
            'processing_timestamp': datetime.now().isoformat(),
            'model_version': '2.15.0'
        }
    }


@pytest.fixture
def sample_low_confidence_data():
    """Fixture for sample extracted data with low confidence fields."""
    return {
        'document_type': 'loan_application',
        'fields': [
            {
                'name': 'business_name',
                'value': 'Acme Corporation',
                'confidence': 0.65,  # Below threshold for critical field
                'field_type': 'text',
                'metadata': {}
            },
            {
                'name': 'tax_id',
                'value': '12-3456789',
                'confidence': 0.72,  # Below threshold for critical field
                'field_type': 'ein',
                'metadata': {}
            },
            {
                'name': 'requested_amount',
                'value': '50000',
                'confidence': 0.68,  # Below threshold for critical field
                'field_type': 'numeric',
                'metadata': {}
            },
            {
                'name': 'address',
                'value': '123 Main St, Anytown, USA',
                'confidence': 0.45,  # Very low confidence
                'field_type': 'text',
                'metadata': {}
            }
        ],
        'metadata': {
            'processing_timestamp': datetime.now().isoformat(),
            'model_version': '2.15.0'
        }
    }


@pytest.fixture
def sample_missing_critical_data():
    """Fixture for sample extracted data with missing critical fields."""
    return {
        'document_type': 'loan_application',
        'fields': [
            {
                'name': 'business_address',
                'value': '123 Main St, Anytown, USA',
                'confidence': 0.85,
                'field_type': 'text',
                'metadata': {}
            },
            {
                'name': 'application_date',
                'value': '2023-05-15',
                'confidence': 0.89,
                'field_type': 'date',
                'metadata': {}
            }
        ],
        'metadata': {
            'processing_timestamp': datetime.now().isoformat(),
            'model_version': '2.15.0'
        }
    }


# Tests for field-level confidence evaluation
def test_evaluate_field_confidence(confidence_service, sample_field):
    """Test that field confidence is correctly evaluated."""
    field = MagicMock(**sample_field)
    confidence_score = confidence_service.evaluate_field_confidence(field)
    
    # Confidence should be a float between 0 and 1
    assert isinstance(confidence_score, float)
    assert 0.0 <= confidence_score <= 1.0
    
    # For this sample field, confidence should be close to the original value
    # since it's a standard text field with no special adjustments
    assert abs(confidence_score - sample_field['confidence']) < 0.15


def test_evaluate_field_confidence_with_critical_field(confidence_service, sample_critical_field):
    """Test that critical field confidence is correctly evaluated with higher standards."""
    field = MagicMock(**sample_critical_field)
    confidence_score = confidence_service.evaluate_field_confidence(field)
    
    # Critical fields with confidence below threshold should be adjusted downward
    assert confidence_score < sample_critical_field['confidence']


def test_evaluate_field_confidence_with_numeric_field(confidence_service):
    """Test that numeric field confidence is correctly evaluated."""
    # Test with valid numeric field
    valid_numeric_field = MagicMock(
        name='amount',
        value='1000.50',
        confidence=0.85,
        field_type='numeric',
        metadata={}
    )
    valid_score = confidence_service.evaluate_field_confidence(valid_numeric_field)
    
    # Test with invalid numeric field (contains non-numeric characters)
    invalid_numeric_field = MagicMock(
        name='amount',
        value='1000.50a',  # Contains a letter
        confidence=0.85,
        field_type='numeric',
        metadata={}
    )
    invalid_score = confidence_service.evaluate_field_confidence(invalid_numeric_field)
    
    # Invalid numeric field should have lower confidence
    assert invalid_score < valid_score


def test_evaluate_field_confidence_with_date_field(confidence_service):
    """Test that date field confidence is correctly evaluated."""
    # Test with valid date field
    valid_date_field = MagicMock(
        name='application_date',
        value='2023-05-15',
        confidence=0.85,
        field_type='date',
        metadata={}
    )
    valid_score = confidence_service.evaluate_field_confidence(valid_date_field)
    
    # Test with invalid date field
    invalid_date_field = MagicMock(
        name='application_date',
        value='not-a-date',  # Invalid date format
        confidence=0.85,
        field_type='date',
        metadata={}
    )
    invalid_score = confidence_service.evaluate_field_confidence(invalid_date_field)
    
    # Invalid date field should have lower confidence
    assert invalid_score < valid_score


# Tests for document type normalization
def test_normalize_confidence_by_document_type(confidence_service):
    """Test that confidence scores are normalized correctly based on document type."""
    base_confidence = 0.85
    
    # Test normalization for different document types
    loan_app_confidence = confidence_service.normalize_confidence_by_document_type(
        base_confidence, 'loan_application')
    tax_return_confidence = confidence_service.normalize_confidence_by_document_type(
        base_confidence, 'tax_return')
    bank_statement_confidence = confidence_service.normalize_confidence_by_document_type(
        base_confidence, 'bank_statement')
    handwritten_confidence = confidence_service.normalize_confidence_by_document_type(
        base_confidence, 'handwritten_form')
    
    # Verify that adjustments are applied correctly
    assert loan_app_confidence == base_confidence  # No adjustment for loan applications
    assert tax_return_confidence < loan_app_confidence  # Tax returns have lower confidence
    assert bank_statement_confidence < loan_app_confidence  # Bank statements have lower confidence
    assert handwritten_confidence < tax_return_confidence  # Handwritten forms have lowest confidence


def test_normalize_confidence_by_unknown_document_type(confidence_service):
    """Test normalization with unknown document type."""
    base_confidence = 0.85
    unknown_confidence = confidence_service.normalize_confidence_by_document_type(
        base_confidence, 'unknown_type')
    
    # Unknown document types should use default adjustment (1.0)
    assert unknown_confidence == base_confidence


# Tests for document-level confidence calculation
def test_calculate_document_confidence(confidence_service, sample_extracted_data):
    """Test calculation of overall document confidence."""
    extracted_data = MagicMock(
        document_type=sample_extracted_data['document_type'],
        fields=[MagicMock(**field) for field in sample_extracted_data['fields']],
        metadata=sample_extracted_data['metadata']
    )
    
    doc_confidence = confidence_service.calculate_document_confidence(extracted_data)
    
    # Document confidence should be a float between 0 and 1
    assert isinstance(doc_confidence, float)
    assert 0.0 <= doc_confidence <= 1.0
    
    # For this sample with high confidence fields, document confidence should be high
    assert doc_confidence > 0.8


def test_calculate_document_confidence_with_missing_critical_fields(
        confidence_service, sample_missing_critical_data):
    """Test document confidence calculation with missing critical fields."""
    extracted_data = MagicMock(
        document_type=sample_missing_critical_data['document_type'],
        fields=[MagicMock(**field) for field in sample_missing_critical_data['fields']],
        metadata=sample_missing_critical_data['metadata']
    )
    
    doc_confidence = confidence_service.calculate_document_confidence(extracted_data)
    
    # Document with missing critical fields should have lower confidence
    assert doc_confidence < 0.7


def test_calculate_document_confidence_with_empty_fields(confidence_service):
    """Test document confidence calculation with no fields."""
    extracted_data = MagicMock(
        document_type='loan_application',
        fields=[],
        metadata={}
    )
    
    doc_confidence = confidence_service.calculate_document_confidence(extracted_data)
    
    # Document with no fields should have zero confidence
    assert doc_confidence == 0.0


# Tests for low confidence field flagging
def test_flag_low_confidence_fields(confidence_service, sample_extracted_data):
    """Test identification of low confidence fields."""
    extracted_data = MagicMock(
        document_type=sample_extracted_data['document_type'],
        fields=[MagicMock(**field) for field in sample_extracted_data['fields']],
        metadata=sample_extracted_data['metadata']
    )
    
    low_confidence_fields = confidence_service.flag_low_confidence_fields(extracted_data)
    
    # In our sample data, most fields have high confidence
    # Only the address field might be flagged depending on thresholds
    assert len(low_confidence_fields) <= 1
    
    # If any field is flagged, it should have metadata explaining why
    for field in low_confidence_fields:
        assert 'verification_reason' in field.metadata


def test_flag_low_confidence_fields_with_low_confidence_data(
        confidence_service, sample_low_confidence_data):
    """Test identification of low confidence fields with low confidence data."""
    extracted_data = MagicMock(
        document_type=sample_low_confidence_data['document_type'],
        fields=[MagicMock(**field) for field in sample_low_confidence_data['fields']],
        metadata=sample_low_confidence_data['metadata']
    )
    
    low_confidence_fields = confidence_service.flag_low_confidence_fields(extracted_data)
    
    # All fields in this sample should be flagged as low confidence
    assert len(low_confidence_fields) == len(sample_low_confidence_data['fields'])
    
    # Critical fields should have higher thresholds
    critical_fields_flagged = [f for f in low_confidence_fields 
                              if f.name in confidence_service.critical_fields]
    assert len(critical_fields_flagged) >= 2  # tax_id and business_name are critical


# Tests for human verification determination
def test_requires_human_verification(confidence_service, sample_extracted_data):
    """Test determination of whether human verification is required."""
    extracted_data = MagicMock(
        document_type=sample_extracted_data['document_type'],
        fields=[MagicMock(**field) for field in sample_extracted_data['fields']],
        metadata=sample_extracted_data['metadata']
    )
    
    requires_verification = confidence_service.requires_human_verification(extracted_data)
    
    # High quality sample should not require verification
    assert requires_verification is False


def test_requires_human_verification_with_low_confidence(
        confidence_service, sample_low_confidence_data):
    """Test verification requirement with low confidence data."""
    extracted_data = MagicMock(
        document_type=sample_low_confidence_data['document_type'],
        fields=[MagicMock(**field) for field in sample_low_confidence_data['fields']],
        metadata=sample_low_confidence_data['metadata']
    )
    
    requires_verification = confidence_service.requires_human_verification(extracted_data)
    
    # Low confidence data should require verification
    assert requires_verification is True
    
    # Verification reasons should be stored in metadata
    assert 'verification_reasons' in extracted_data.metadata
    assert len(extracted_data.metadata['verification_reasons']) > 0


def test_requires_human_verification_with_missing_critical_fields(
        confidence_service, sample_missing_critical_data):
    """Test verification requirement with missing critical fields."""
    extracted_data = MagicMock(
        document_type=sample_missing_critical_data['document_type'],
        fields=[MagicMock(**field) for field in sample_missing_critical_data['fields']],
        metadata=sample_missing_critical_data['metadata']
    )
    
    requires_verification = confidence_service.requires_human_verification(extracted_data)
    
    # Data with missing critical fields should require verification
    assert requires_verification is True
    
    # Verification reasons should mention missing critical fields
    assert any('missing critical fields' in reason.lower() 
              for reason in extracted_data.metadata['verification_reasons'])


# Tests for suspicious pattern detection
def test_check_suspicious_patterns(confidence_service):
    """Test detection of suspicious patterns in extracted data."""
    # Create data with suspicious date inconsistency
    extracted_data = MagicMock(
        document_type='bank_statement',
        fields=[
            MagicMock(name='statement_date', value='2023-06-15', field_type='date', confidence=0.9, metadata={}),
            MagicMock(name='report_date', value='2023-05-15', field_type='date', confidence=0.9, metadata={})
        ],
        metadata={}
    )
    
    suspicious_patterns = confidence_service._check_suspicious_patterns(extracted_data)
    
    # Should detect that statement_date is after report_date
    assert len(suspicious_patterns) > 0
    assert any('date' in pattern.lower() for pattern in suspicious_patterns)


def test_check_suspicious_patterns_with_numeric_inconsistency(confidence_service):
    """Test detection of suspicious numeric inconsistencies."""
    # Create data with suspicious balance inconsistency
    extracted_data = MagicMock(
        document_type='bank_statement',
        fields=[
            MagicMock(name='beginning_balance', value='1000.00', field_type='numeric', confidence=0.9, metadata={}),
            MagicMock(name='ending_balance', value='1500.00', field_type='numeric', confidence=0.9, metadata={}),
            MagicMock(name='total_deposits', value='200.00', field_type='numeric', confidence=0.9, metadata={}),
            MagicMock(name='total_withdrawals', value='100.00', field_type='numeric', confidence=0.9, metadata={})
        ],
        metadata={}
    )
    
    suspicious_patterns = confidence_service._check_suspicious_patterns(extracted_data)
    
    # Should detect that ending_balance doesn't match calculation
    assert len(suspicious_patterns) > 0
    assert any('balance' in pattern.lower() for pattern in suspicious_patterns)


# Tests for confidence metrics generation
def test_get_confidence_metrics(confidence_service, sample_extracted_data):
    """Test generation of confidence metrics for monitoring and reporting."""
    extracted_data = MagicMock(
        document_type=sample_extracted_data['document_type'],
        fields=[MagicMock(**field) for field in sample_extracted_data['fields']],
        metadata=sample_extracted_data['metadata']
    )
    
    metrics = confidence_service.get_confidence_metrics(extracted_data)
    
    # Verify that all expected metrics are present
    assert 'document_confidence' in metrics
    assert 'requires_verification' in metrics
    assert 'low_confidence_field_count' in metrics
    assert 'total_field_count' in metrics
    assert 'low_confidence_ratio' in metrics
    assert 'confidence_by_field_type' in metrics
    assert 'critical_fields_confidence' in metrics
    assert 'document_type' in metrics
    assert 'confidence_distribution' in metrics
    
    # Verify that metrics have expected values
    assert metrics['document_type'] == sample_extracted_data['document_type']
    assert metrics['total_field_count'] == len(sample_extracted_data['fields'])
    assert 0.0 <= metrics['document_confidence'] <= 1.0
    assert isinstance(metrics['requires_verification'], bool)


def test_get_confidence_metrics_with_low_confidence(
        confidence_service, sample_low_confidence_data):
    """Test confidence metrics with low confidence data."""
    extracted_data = MagicMock(
        document_type=sample_low_confidence_data['document_type'],
        fields=[MagicMock(**field) for field in sample_low_confidence_data['fields']],
        metadata=sample_low_confidence_data['metadata']
    )
    
    metrics = confidence_service.get_confidence_metrics(extracted_data)
    
    # Verify that metrics reflect low confidence
    assert metrics['requires_verification'] is True
    assert metrics['low_confidence_field_count'] > 0
    assert metrics['low_confidence_ratio'] > 0.5  # More than half of fields have low confidence


# Tests for confidence data enrichment
def test_enrich_with_confidence_data(confidence_service, sample_extracted_data):
    """Test enrichment of extracted data with confidence information."""
    extracted_data = MagicMock(
        document_type=sample_extracted_data['document_type'],
        fields=[MagicMock(**field) for field in sample_extracted_data['fields']],
        metadata={}
    )
    
    enriched_data = confidence_service.enrich_with_confidence_data(extracted_data)
    
    # Verify that confidence metadata was added
    assert 'document_confidence' in enriched_data.metadata
    assert 'requires_verification' in enriched_data.metadata
    assert 'low_confidence_fields' in enriched_data.metadata
    assert 'confidence_metrics' in enriched_data.metadata
    
    # Verify that each field was enriched with confidence metadata
    for field in enriched_data.fields:
        assert 'confidence_category' in field.metadata
        assert 'normalized_confidence' in field.metadata
        assert 'requires_verification' in field.metadata


def test_enrich_with_confidence_data_requiring_verification(
        confidence_service, sample_low_confidence_data):
    """Test enrichment of data requiring verification."""
    extracted_data = MagicMock(
        document_type=sample_low_confidence_data['document_type'],
        fields=[MagicMock(**field) for field in sample_low_confidence_data['fields']],
        metadata={}
    )
    
    enriched_data = confidence_service.enrich_with_confidence_data(extracted_data)
    
    # Verify that verification guidance was added
    assert enriched_data.metadata['requires_verification'] is True
    assert 'verification_guidance' in enriched_data.metadata
    assert 'priority' in enriched_data.metadata['verification_guidance']
    assert 'reasons' in enriched_data.metadata['verification_guidance']
    assert 'suggested_focus' in enriched_data.metadata['verification_guidance']
    
    # Verify that fields requiring verification have appropriate metadata
    verification_fields = [f for f in enriched_data.fields 
                          if f.metadata['requires_verification']]
    assert len(verification_fields) > 0
    
    for field in verification_fields:
        assert 'verification_priority' in field.metadata
        assert 'verification_note' in field.metadata