"""Tests for the confidence scoring utilities in the OCR service.

This module tests the utilities for calculating and standardizing confidence scores
for extracted text fields. It verifies that the confidence scoring algorithms correctly
assess the reliability of OCR results, enabling downstream services to make informed
decisions about automation versus human review.
"""

import json
import math
import unittest
from datetime import datetime
from unittest import mock

import numpy as np
import pytest

# Fix imports to match the actual project structure
from src.models.confidence_scoring import (
    ConfidenceScore,
    calculate_character_confidence,
    calculate_word_confidence,
    normalize_model_confidence,
    adjust_confidence_by_field_type,
    adjust_confidence_by_context,
    calculate_field_confidence,
    calculate_table_confidence,
    should_flag_for_verification,
    calculate_document_confidence,
    enrich_extraction_with_confidence_metadata,
    confidence_from_tensorflow_output,
    get_confidence_threshold_config,
    update_confidence_threshold_config,
    ConfidenceAnalyzer,
    analyze_confidence_distribution,
    ConfidenceScoreCalibrator,
    FIELD_IMPORTANCE,
    DEFAULT_CONFIDENCE_THRESHOLD,
    HIGH_CONFIDENCE_THRESHOLD,
    LOW_CONFIDENCE_THRESHOLD,
    CRITICAL_FIELD_THRESHOLD,
    FIELD_TYPE_MODIFIERS
)
from src.types.extraction import (
    FieldType,
    ExtractedField,
    ExtractedData,
    TableData
)

# Mock TensorFlow for testing without requiring the actual library
class MockTensor:
    def __init__(self, data):
        self.data = data
    
    def numpy(self):
        return np.array(self.data)


@pytest.fixture
def mock_extracted_field() -> ExtractedField:
    """Create a mock extracted field for testing."""
    return {
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
        "extraction_timestamp": datetime.now()
    }


@pytest.fixture
def mock_low_confidence_field() -> ExtractedField:
    """Create a mock low-confidence extracted field for testing."""
    return {
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
        "extraction_timestamp": datetime.now()
    }


@pytest.fixture
def mock_extracted_data() -> ExtractedData:
    """Create mock extraction results for testing."""
    return {
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
                "extraction_timestamp": datetime.now()
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
                "extraction_timestamp": datetime.now()
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
        "extraction_timestamp": datetime.now(),
        "schema_version": "1.0",
        "document_type": "application_form"
    }


@pytest.fixture
def mock_table_data() -> TableData:
    """Create mock table data for testing."""
    return {
        "table_id": "table1",
        "table_name": "Revenue Table",
        "headers": ["Month", "Revenue", "Expenses", "Profit"],
        "rows": [
            ["January", 10000, 8000, 2000],
            ["February", 12000, 9000, 3000],
            ["March", 15000, 10000, 5000]
        ],
        "header_row_index": 0,
        "field_mapping": {"month": 0, "revenue": 1, "expenses": 2, "profit": 3},
        "row_count": 3,
        "column_count": 4,
        "confidence": ConfidenceScore.from_float(0.85),
        "is_complete": True,
        "metadata": {}
    }


@pytest.fixture
def mock_char_confidences() -> list:
    """Create mock character-level confidence scores for testing."""
    return [0.98, 0.95, 0.99, 0.97, 0.90, 0.85, 0.92, 0.94, 0.91]


@pytest.fixture
def mock_word_confidences() -> list:
    """Create mock word-level confidence scores for testing."""
    return [0.95, 0.87, 0.92, 0.65, 0.78, 0.91, 0.88, 0.72, 0.81]


@pytest.fixture
def mock_tensorflow_output() -> MockTensor:
    """Create a mock TensorFlow output tensor for testing."""
    return MockTensor([[0.95, 0.92, 0.88], [0.85, 0.91, 0.89]])


class TestConfidenceScore:
    """Tests for the ConfidenceScore class."""

    def test_initialization(self):
        """Test that ConfidenceScore initializes correctly."""
        # Test valid initialization
        score = ConfidenceScore(value=0.75)
        assert score.value == 0.75
        
        # Test clamping of values below 0.0
        score = ConfidenceScore(value=-0.5)
        assert score.value == 0.0
        
        # Test clamping of values above 1.0
        score = ConfidenceScore(value=1.5)
        assert score.value == 1.0
    
    def test_from_float(self):
        """Test the from_float factory method."""
        score = ConfidenceScore.from_float(0.8)
        assert score.value == 0.8
        
        # Test clamping
        score = ConfidenceScore.from_float(1.2)
        assert score.value == 1.0
    
    def test_float_conversion(self):
        """Test conversion to float."""
        score = ConfidenceScore(0.65)
        assert float(score) == 0.65
    
    def test_is_low_confidence(self):
        """Test the is_low_confidence method."""
        # Test with default threshold
        score = ConfidenceScore(0.65)
        assert score.is_low_confidence()
        
        score = ConfidenceScore(0.75)
        assert not score.is_low_confidence()
        
        # Test with custom threshold
        score = ConfidenceScore(0.65)
        assert not score.is_low_confidence(0.6)
        
        score = ConfidenceScore(0.55)
        assert score.is_low_confidence(0.6)


class TestCharacterConfidence:
    """Tests for character-level confidence calculation."""

    def test_calculate_character_confidence(self, mock_char_confidences):
        """Test calculation of character-level confidence."""
        confidence = calculate_character_confidence(mock_char_confidences)
        
        # The result should be a weighted geometric mean of the character confidences
        # This emphasizes low confidence characters
        expected = math.exp(sum(math.log(c) for c in mock_char_confidences) / len(mock_char_confidences))
        assert abs(confidence - expected) < 0.0001
        
        # The result should be lower than the arithmetic mean due to emphasis on low values
        arithmetic_mean = sum(mock_char_confidences) / len(mock_char_confidences)
        assert confidence < arithmetic_mean
    
    def test_empty_input(self):
        """Test handling of empty input."""
        confidence = calculate_character_confidence([])
        assert confidence == 0.0
    
    def test_invalid_values(self):
        """Test handling of invalid confidence values."""
        # Test with negative values
        confidence = calculate_character_confidence([-0.1, 0.5, 0.8])
        assert 0.0 <= confidence <= 1.0
        
        # Test with values > 1.0
        confidence = calculate_character_confidence([0.5, 1.2, 0.8])
        assert 0.0 <= confidence <= 1.0
        
        # Test with all invalid values
        confidence = calculate_character_confidence([-0.1, 1.2])
        assert confidence == 0.0


class TestWordConfidence:
    """Tests for word-level confidence calculation."""

    def test_calculate_word_confidence(self, mock_word_confidences):
        """Test calculation of word-level confidence."""
        confidence = calculate_word_confidence(mock_word_confidences)
        
        # The result should be a weighted average of the word confidences
        # with more weight given to lower confidence words
        weights = [2.0 - c for c in mock_word_confidences]
        expected = sum(c * w for c, w in zip(mock_word_confidences, weights)) / sum(weights)
        assert abs(confidence - expected) < 0.0001
        
        # The result should be lower than the arithmetic mean due to emphasis on low values
        arithmetic_mean = sum(mock_word_confidences) / len(mock_word_confidences)
        assert confidence < arithmetic_mean
    
    def test_empty_input(self):
        """Test handling of empty input."""
        confidence = calculate_word_confidence([])
        assert confidence == 0.0
    
    def test_invalid_values(self):
        """Test handling of invalid confidence values."""
        # Test with negative values
        confidence = calculate_word_confidence([-0.1, 0.5, 0.8])
        assert 0.0 <= confidence <= 1.0
        
        # Test with values > 1.0
        confidence = calculate_word_confidence([0.5, 1.2, 0.8])
        assert 0.0 <= confidence <= 1.0
        
        # Test with all invalid values
        confidence = calculate_word_confidence([-0.1, 1.2])
        assert confidence == 0.0


class TestModelConfidenceNormalization:
    """Tests for model-specific confidence normalization."""

    def test_normalize_model_confidence(self):
        """Test normalization of confidence scores from different model types."""
        # Test typed text model (well-calibrated)
        raw_confidence = 0.85
        normalized = normalize_model_confidence(raw_confidence, "typed_text")
        assert normalized == 0.85  # No change expected
        
        # Test handwritten model (tends to be overconfident)
        raw_confidence = 0.85
        normalized = normalize_model_confidence(raw_confidence, "handwritten")
        assert normalized < raw_confidence  # Should be adjusted downward
        
        # Test hybrid model (slightly overconfident)
        raw_confidence = 0.85
        normalized = normalize_model_confidence(raw_confidence, "hybrid")
        assert normalized < raw_confidence  # Should be adjusted downward
        assert normalized > normalize_model_confidence(raw_confidence, "handwritten")  # But less than handwritten
        
        # Test unknown model type (should use default calibration)
        raw_confidence = 0.85
        normalized = normalize_model_confidence(raw_confidence, "unknown")
        assert normalized == 0.85  # Should use default calibration
    
    def test_normalization_clamping(self):
        """Test that normalized values are clamped to [0.0, 1.0]."""
        # Test clamping at lower bound
        raw_confidence = 0.05
        normalized = normalize_model_confidence(raw_confidence, "handwritten")
        assert normalized >= 0.0
        
        # Test clamping at upper bound
        raw_confidence = 0.95
        normalized = normalize_model_confidence(raw_confidence, "typed_text")
        assert normalized <= 1.0


class TestFieldTypeAdjustment:
    """Tests for field type-based confidence adjustment."""

    def test_adjust_confidence_by_field_type(self):
        """Test adjustment of confidence scores based on field type."""
        base_confidence = 0.8
        
        # Test standard text field (no adjustment)
        adjusted = adjust_confidence_by_field_type(base_confidence, FieldType.TEXT)
        assert adjusted == base_confidence
        
        # Test field types that are easier to extract (higher confidence)
        adjusted = adjust_confidence_by_field_type(base_confidence, FieldType.NUMBER)
        assert adjusted > base_confidence
        
        # Test field types that are harder to extract (lower confidence)
        adjusted = adjust_confidence_by_field_type(base_confidence, FieldType.SIGNATURE)
        assert adjusted < base_confidence
        
        # Test field types with moderate difficulty
        adjusted = adjust_confidence_by_field_type(base_confidence, FieldType.DATE)
        assert adjusted < base_confidence
        assert adjusted > adjust_confidence_by_field_type(base_confidence, FieldType.SIGNATURE)
    
    def test_adjustment_clamping(self):
        """Test that adjusted values are clamped to [0.0, 1.0]."""
        # Test clamping at lower bound
        low_confidence = 0.1
        adjusted = adjust_confidence_by_field_type(low_confidence, FieldType.SIGNATURE)
        assert adjusted >= 0.0
        
        # Test clamping at upper bound
        high_confidence = 0.95
        adjusted = adjust_confidence_by_field_type(high_confidence, FieldType.NUMBER)
        assert adjusted <= 1.0


class TestContextAdjustment:
    """Tests for context-based confidence adjustment."""

    def test_adjust_confidence_by_context(self, mock_extracted_field, mock_low_confidence_field):
        """Test adjustment of confidence scores based on context from other fields."""
        # Create a dictionary of other fields for context
        other_fields = {
            "business_name": mock_extracted_field,
            "tax_id": mock_low_confidence_field
        }
        
        # Test business_name field with matching dba_name
        base_confidence = 0.8
        other_fields["dba_name"] = {
            "field_name": "dba_name",
            "field_type": "name",
            "value": "ACME Corporation",
            "raw_text": "ACME Corporation",
            "confidence": ConfidenceScore.from_float(0.85)
        }
        
        adjusted = adjust_confidence_by_context(base_confidence, "business_name", other_fields)
        assert adjusted > base_confidence  # Should be increased due to matching dba_name
        
        # Test phone number field with valid format
        base_confidence = 0.8
        other_fields["business_phone"] = {
            "field_name": "business_phone",
            "field_type": "phone",
            "value": "(555) 123-4567",
            "raw_text": "(555) 123-4567",
            "confidence": ConfidenceScore.from_float(0.75)
        }
        
        adjusted = adjust_confidence_by_context(base_confidence, "business_phone", other_fields)
        assert adjusted > base_confidence  # Should be increased due to valid format
        
        # Test email field with valid format
        base_confidence = 0.8
        other_fields["business_email"] = {
            "field_name": "business_email",
            "field_type": "email",
            "value": "info@acme.com",
            "raw_text": "info@acme.com",
            "confidence": ConfidenceScore.from_float(0.75)
        }
        
        adjusted = adjust_confidence_by_context(base_confidence, "business_email", other_fields)
        assert adjusted > base_confidence  # Should be increased due to valid format
        
        # Test field with no context adjustment
        base_confidence = 0.8
        adjusted = adjust_confidence_by_context(base_confidence, "owner_name", other_fields)
        assert adjusted == base_confidence  # Should be unchanged
    
    def test_adjustment_clamping(self, mock_extracted_field, mock_low_confidence_field):
        """Test that adjusted values are clamped to [0.0, 1.0]."""
        # Create a dictionary of other fields for context
        other_fields = {
            "business_name": mock_extracted_field,
            "tax_id": mock_low_confidence_field,
            "dba_name": {
                "field_name": "dba_name",
                "field_type": "name",
                "value": "ACME Corporation",
                "raw_text": "ACME Corporation",
                "confidence": ConfidenceScore.from_float(0.85)
            }
        }
        
        # Test clamping at upper bound
        high_confidence = 0.98
        adjusted = adjust_confidence_by_context(high_confidence, "business_name", other_fields)
        assert adjusted <= 1.0


class TestFieldConfidenceCalculation:
    """Tests for field-level confidence calculation."""

    def test_calculate_field_confidence(self, mock_char_confidences, mock_extracted_field, mock_low_confidence_field):
        """Test calculation of field-level confidence scores."""
        # Create a dictionary of other fields for context
        other_fields = {
            "business_name": mock_extracted_field,
            "tax_id": mock_low_confidence_field
        }
        
        # Test calculation with all parameters
        confidence = calculate_field_confidence(
            field_name="business_name",
            raw_text="ACME Corp",
            char_confidences=mock_char_confidences,
            model_type="typed_text",
            field_type=FieldType.NAME,
            other_fields=other_fields
        )
        
        # Result should be a ConfidenceScore instance
        assert isinstance(confidence, ConfidenceScore)
        
        # Value should be in range [0.0, 1.0]
        assert 0.0 <= float(confidence) <= 1.0
        
        # Test calculation without context
        confidence_no_context = calculate_field_confidence(
            field_name="business_name",
            raw_text="ACME Corp",
            char_confidences=mock_char_confidences,
            model_type="typed_text",
            field_type=FieldType.NAME
        )
        
        # Result should still be valid
        assert isinstance(confidence_no_context, ConfidenceScore)
        assert 0.0 <= float(confidence_no_context) <= 1.0
    
    def test_model_type_impact(self, mock_char_confidences):
        """Test the impact of model type on field confidence calculation."""
        # Calculate confidence for different model types
        typed_confidence = calculate_field_confidence(
            field_name="business_name",
            raw_text="ACME Corp",
            char_confidences=mock_char_confidences,
            model_type="typed_text",
            field_type=FieldType.NAME
        )
        
        handwritten_confidence = calculate_field_confidence(
            field_name="business_name",
            raw_text="ACME Corp",
            char_confidences=mock_char_confidences,
            model_type="handwritten",
            field_type=FieldType.NAME
        )
        
        # Handwritten model should have lower confidence due to calibration
        assert float(handwritten_confidence) < float(typed_confidence)
    
    def test_field_type_impact(self, mock_char_confidences):
        """Test the impact of field type on field confidence calculation."""
        # Calculate confidence for different field types
        name_confidence = calculate_field_confidence(
            field_name="business_name",
            raw_text="ACME Corp",
            char_confidences=mock_char_confidences,
            model_type="typed_text",
            field_type=FieldType.NAME
        )
        
        signature_confidence = calculate_field_confidence(
            field_name="signature",
            raw_text="John Doe",
            char_confidences=mock_char_confidences,
            model_type="typed_text",
            field_type=FieldType.SIGNATURE
        )
        
        # Signature field should have lower confidence due to field type modifier
        assert float(signature_confidence) < float(name_confidence)


class TestTableConfidenceCalculation:
    """Tests for table-level confidence calculation."""

    def test_calculate_table_confidence(self, mock_table_data):
        """Test calculation of table-level confidence scores."""
        confidence = calculate_table_confidence(mock_table_data)
        
        # Result should be a ConfidenceScore instance
        assert isinstance(confidence, ConfidenceScore)
        
        # Value should be in range [0.0, 1.0]
        assert 0.0 <= float(confidence) <= 1.0
        
        # For a complete table, confidence should be high
        assert float(confidence) >= 0.8
        
        # Test with incomplete table
        incomplete_table = mock_table_data.copy()
        incomplete_table["is_complete"] = False
        
        incomplete_confidence = calculate_table_confidence(incomplete_table)
        
        # Incomplete table should have lower confidence
        assert float(incomplete_confidence) < float(confidence)


class TestVerificationFlagging:
    """Tests for verification flagging based on confidence scores."""

    def test_should_flag_for_verification(self):
        """Test determination of whether a field should be flagged for verification."""
        # Test critical field with confidence below threshold
        should_verify, reason = should_flag_for_verification(
            field_name="tax_id",
            confidence=ConfidenceScore.from_float(0.75)
        )
        
        # Should be flagged due to critical field with confidence below critical threshold
        assert should_verify
        assert reason  # Reason should be provided
        
        # Test critical field with confidence above threshold
        should_verify, reason = should_flag_for_verification(
            field_name="tax_id",
            confidence=ConfidenceScore.from_float(0.85)
        )
        
        # Should not be flagged
        assert not should_verify
        assert not reason  # No reason needed
        
        # Test non-critical field with confidence below threshold
        should_verify, reason = should_flag_for_verification(
            field_name="business_address",
            confidence=ConfidenceScore.from_float(0.65)
        )
        
        # Should be flagged due to confidence below default threshold
        assert should_verify
        assert reason  # Reason should be provided
        
        # Test non-critical field with confidence above threshold
        should_verify, reason = should_flag_for_verification(
            field_name="business_address",
            confidence=ConfidenceScore.from_float(0.75)
        )
        
        # Should not be flagged
        assert not should_verify
        assert not reason  # No reason needed


class TestDocumentConfidenceCalculation:
    """Tests for document-level confidence calculation."""

    def test_calculate_document_confidence(self, mock_extracted_data):
        """Test calculation of document-level confidence scores."""
        confidence = calculate_document_confidence(mock_extracted_data)
        
        # Result should be a ConfidenceScore instance
        assert isinstance(confidence, ConfidenceScore)
        
        # Value should be in range [0.0, 1.0]
        assert 0.0 <= float(confidence) <= 1.0
        
        # For the mock data, confidence should be a weighted average of field confidences
        # with more weight given to critical fields
        fields = mock_extracted_data["fields"]
        weighted_sum = 0.0
        weight_sum = 0.0
        
        for field_name, field_data in fields.items():
            confidence_value = float(field_data["confidence"])
            importance = FIELD_IMPORTANCE.get(field_name, 0.7)  # Default importance
            
            weighted_sum += confidence_value * importance
            weight_sum += importance
        
        expected = weighted_sum / weight_sum
        assert abs(float(confidence) - expected) < 0.0001
    
    def test_empty_document(self):
        """Test handling of documents with no fields."""
        empty_data = {
            "extraction_id": "123456",
            "fields": {},
            "tables": [],
            "metadata": {},
            "raw_text": "",
            "low_confidence_fields": [],
            "requires_verification": False,
            "extraction_timestamp": datetime.now(),
            "schema_version": "1.0",
            "document_type": "application_form"
        }
        
        confidence = calculate_document_confidence(empty_data)
        
        # Result should be a ConfidenceScore instance with value 0.0
        assert isinstance(confidence, ConfidenceScore)
        assert float(confidence) == 0.0


class TestExtractionEnrichment:
    """Tests for enriching extraction results with confidence metadata."""

    def test_enrich_extraction_with_confidence_metadata(self, mock_extracted_data):
        """Test enrichment of extraction results with confidence metadata."""
        # Modify the mock data to ensure one field requires verification
        mock_data = mock_extracted_data.copy()
        mock_data["fields"]["tax_id"]["confidence"] = ConfidenceScore.from_float(0.65)
        
        # Enrich the extraction data
        enriched_data = enrich_extraction_with_confidence_metadata(mock_data)
        
        # Check that metadata was added
        assert "low_confidence_fields" in enriched_data
        assert "requires_verification" in enriched_data
        assert "overall_confidence" in enriched_data["metadata"]
        assert "verification_reasons" in enriched_data["metadata"]
        
        # Check that the tax_id field was flagged for verification
        assert "tax_id" in enriched_data["low_confidence_fields"]
        assert enriched_data["requires_verification"]
        assert enriched_data["fields"]["tax_id"]["requires_verification"]
        assert enriched_data["fields"]["tax_id"]["verification_reason"]
        
        # Check that the business_name field was not flagged
        assert "business_name" not in enriched_data["low_confidence_fields"]
        assert not enriched_data["fields"]["business_name"]["requires_verification"]
        assert not enriched_data["fields"]["business_name"]["verification_reason"]
    
    def test_enrich_high_confidence_extraction(self, mock_extracted_data):
        """Test enrichment of extraction results with all high-confidence fields."""
        # Modify the mock data to ensure all fields have high confidence
        mock_data = mock_extracted_data.copy()
        mock_data["fields"]["tax_id"]["confidence"] = ConfidenceScore.from_float(0.85)
        mock_data["fields"]["business_name"]["confidence"] = ConfidenceScore.from_float(0.95)
        
        # Enrich the extraction data
        enriched_data = enrich_extraction_with_confidence_metadata(mock_data)
        
        # Check that no fields were flagged for verification
        assert len(enriched_data["low_confidence_fields"]) == 0
        assert not enriched_data["requires_verification"]
        assert not enriched_data["fields"]["tax_id"]["requires_verification"]
        assert not enriched_data["fields"]["business_name"]["requires_verification"]


class TestTensorFlowOutputConversion:
    """Tests for converting TensorFlow output to confidence scores."""

    def test_confidence_from_tensorflow_output(self, mock_tensorflow_output):
        """Test extraction of confidence scores from TensorFlow output."""
        confidences = confidence_from_tensorflow_output(mock_tensorflow_output)
        
        # Result should be a list of confidence scores
        assert isinstance(confidences, list)
        
        # Values should be in range [0.0, 1.0]
        assert all(0.0 <= c <= 1.0 for c in confidences)
        
        # Length should match the flattened tensor
        expected_length = mock_tensorflow_output.data.size
        assert len(confidences) == expected_length
        
        # Values should match the tensor data
        expected_values = mock_tensorflow_output.data.flatten().tolist()
        assert confidences == expected_values
    
    def test_error_handling(self):
        """Test error handling for invalid TensorFlow output."""
        # Test with None input
        with mock.patch("logging.error"):
            confidences = confidence_from_tensorflow_output(None)
            assert confidences == [0.5]  # Should return default confidence
        
        # Test with input that raises an exception
        class BadTensor:
            def numpy(self):
                raise ValueError("Test error")
        
        with mock.patch("logging.error"):
            confidences = confidence_from_tensorflow_output(BadTensor())
            assert confidences == [0.5]  # Should return default confidence


class TestThresholdConfiguration:
    """Tests for confidence threshold configuration."""

    def test_get_confidence_threshold_config(self):
        """Test retrieval of confidence threshold configuration."""
        config = get_confidence_threshold_config()
        
        # Config should contain all threshold types
        assert "default" in config
        assert "high" in config
        assert "low" in config
        assert "critical" in config
        
        # Values should match the global constants
        assert config["default"] == DEFAULT_CONFIDENCE_THRESHOLD
        assert config["high"] == HIGH_CONFIDENCE_THRESHOLD
        assert config["low"] == LOW_CONFIDENCE_THRESHOLD
        assert config["critical"] == CRITICAL_FIELD_THRESHOLD
    
    def test_update_confidence_threshold_config(self):
        """Test updating of confidence threshold configuration."""
        # Save original values
        original_default = DEFAULT_CONFIDENCE_THRESHOLD
        original_high = HIGH_CONFIDENCE_THRESHOLD
        original_low = LOW_CONFIDENCE_THRESHOLD
        original_critical = CRITICAL_FIELD_THRESHOLD
        
        try:
            # Update the configuration
            new_config = {
                "default": 0.75,
                "high": 0.95,
                "low": 0.55,
                "critical": 0.85
            }
            
            update_confidence_threshold_config(new_config)
            
            # Check that global constants were updated
            assert DEFAULT_CONFIDENCE_THRESHOLD == 0.75
            assert HIGH_CONFIDENCE_THRESHOLD == 0.95
            assert LOW_CONFIDENCE_THRESHOLD == 0.55
            assert CRITICAL_FIELD_THRESHOLD == 0.85
            
            # Check that get_confidence_threshold_config returns the updated values
            config = get_confidence_threshold_config()
            assert config["default"] == 0.75
            assert config["high"] == 0.95
            assert config["low"] == 0.55
            assert config["critical"] == 0.85
            
            # Test partial update
            partial_config = {"default": 0.72}
            update_confidence_threshold_config(partial_config)
            
            # Only the specified value should be updated
            config = get_confidence_threshold_config()
            assert config["default"] == 0.72
            assert config["high"] == 0.95  # Unchanged
            assert config["low"] == 0.55  # Unchanged
            assert config["critical"] == 0.85  # Unchanged
        finally:
            # Restore original values
            update_confidence_threshold_config({
                "default": original_default,
                "high": original_high,
                "low": original_low,
                "critical": original_critical
            })


class TestConfidenceAnalyzer:
    """Tests for the ConfidenceAnalyzer class."""

    def test_add_document(self, mock_extracted_data):
        """Test adding a document to the analyzer."""
        analyzer = ConfidenceAnalyzer()
        
        # Add a document
        analyzer.add_document(mock_extracted_data)
        
        # Check that document confidence was tracked
        assert len(analyzer.document_confidences) == 1
        
        # Check that field confidences were tracked
        assert "business_name" in analyzer.field_confidences
        assert "tax_id" in analyzer.field_confidences
        assert len(analyzer.field_confidences["business_name"]) == 1
        assert len(analyzer.field_confidences["tax_id"]) == 1
        
        # Check that verification rates were tracked
        assert "business_name" in analyzer.verification_rates
        assert "tax_id" in analyzer.verification_rates
        assert analyzer.verification_rates["business_name"]["total"] == 1
        assert analyzer.verification_rates["tax_id"]["total"] == 1
        
        # Check that automation rates were tracked
        assert "application_form" in analyzer.automation_rates
        assert analyzer.automation_rates["application_form"]["total"] == 1
    
    def test_get_overall_automation_rate(self, mock_extracted_data):
        """Test calculation of overall automation rate."""
        analyzer = ConfidenceAnalyzer()
        
        # Add documents with different verification requirements
        # First document: no verification required
        analyzer.add_document(mock_extracted_data)
        
        # Second document: verification required
        mock_data2 = mock_extracted_data.copy()
        mock_data2["requires_verification"] = True
        mock_data2["document_type"] = "application_form"
        analyzer.add_document(mock_data2)
        
        # Third document: no verification required, different type
        mock_data3 = mock_extracted_data.copy()
        mock_data3["document_type"] = "tax_return"
        analyzer.add_document(mock_data3)
        
        # Calculate automation rate
        automation_rate = analyzer.get_overall_automation_rate()
        
        # Expected rate: 2 automated out of 3 total = 66.67%
        expected_rate = (2 / 3) * 100.0
        assert abs(automation_rate - expected_rate) < 0.01
    
    def test_get_field_verification_rates(self, mock_extracted_data):
        """Test calculation of field verification rates."""
        analyzer = ConfidenceAnalyzer()
        
        # Add a document with one field requiring verification
        mock_data = mock_extracted_data.copy()
        mock_data["fields"]["tax_id"]["requires_verification"] = True
        analyzer.add_document(mock_data)
        
        # Add another document with both fields requiring verification
        mock_data2 = mock_extracted_data.copy()
        mock_data2["fields"]["tax_id"]["requires_verification"] = True
        mock_data2["fields"]["business_name"]["requires_verification"] = True
        analyzer.add_document(mock_data2)
        
        # Calculate field verification rates
        verification_rates = analyzer.get_field_verification_rates()
        
        # Expected rates:
        # tax_id: 2 verified out of 2 total = 100%
        # business_name: 1 verified out of 2 total = 50%
        assert abs(verification_rates["tax_id"] - 100.0) < 0.01
        assert abs(verification_rates["business_name"] - 50.0) < 0.01
    
    def test_get_field_confidence_stats(self, mock_extracted_data):
        """Test calculation of field confidence statistics."""
        analyzer = ConfidenceAnalyzer()
        
        # Add documents with different confidence scores
        mock_data1 = mock_extracted_data.copy()
        mock_data1["fields"]["business_name"]["confidence"] = ConfidenceScore.from_float(0.9)
        mock_data1["fields"]["tax_id"]["confidence"] = ConfidenceScore.from_float(0.7)
        analyzer.add_document(mock_data1)
        
        mock_data2 = mock_extracted_data.copy()
        mock_data2["fields"]["business_name"]["confidence"] = ConfidenceScore.from_float(0.8)
        mock_data2["fields"]["tax_id"]["confidence"] = ConfidenceScore.from_float(0.6)
        analyzer.add_document(mock_data2)
        
        # Calculate field confidence statistics
        confidence_stats = analyzer.get_field_confidence_stats()
        
        # Check that statistics were calculated for both fields
        assert "business_name" in confidence_stats
        assert "tax_id" in confidence_stats
        
        # Check that all statistics are present
        business_stats = confidence_stats["business_name"]
        assert "mean" in business_stats
        assert "median" in business_stats
        assert "min" in business_stats
        assert "max" in business_stats
        assert "std_dev" in business_stats
        
        # Check that values are correct for business_name
        assert abs(business_stats["mean"] - 0.85) < 0.01
        assert abs(business_stats["median"] - 0.85) < 0.01
        assert abs(business_stats["min"] - 0.8) < 0.01
        assert abs(business_stats["max"] - 0.9) < 0.01
        
        # Check that values are correct for tax_id
        tax_stats = confidence_stats["tax_id"]
        assert abs(tax_stats["mean"] - 0.65) < 0.01
        assert abs(tax_stats["median"] - 0.65) < 0.01
        assert abs(tax_stats["min"] - 0.6) < 0.01
        assert abs(tax_stats["max"] - 0.7) < 0.01
    
    def test_suggest_threshold_adjustments(self, mock_extracted_data):
        """Test suggestion of threshold adjustments based on analysis."""
        analyzer = ConfidenceAnalyzer()
        
        # Add documents to simulate low automation rate
        for i in range(10):
            mock_data = mock_extracted_data.copy()
            mock_data["requires_verification"] = (i < 3)  # 3 out of 10 require verification
            analyzer.add_document(mock_data)
        
        # Get threshold suggestions
        suggestions = analyzer.suggest_threshold_adjustments()
        
        # Should suggest global threshold adjustment for high automation rate
        assert "global" in suggestions
        assert "default" in suggestions["global"]
        assert "reason" in suggestions["global"]
        
        # Test with field-specific issues
        analyzer = ConfidenceAnalyzer()
        
        # Add documents with high verification rate for tax_id but good confidence
        for i in range(10):
            mock_data = mock_extracted_data.copy()
            mock_data["fields"]["tax_id"]["confidence"] = ConfidenceScore.from_float(0.7)
            mock_data["fields"]["tax_id"]["requires_verification"] = True
            analyzer.add_document(mock_data)
        
        # Get threshold suggestions
        suggestions = analyzer.suggest_threshold_adjustments()
        
        # Should suggest field-specific threshold adjustment for tax_id
        assert "tax_id" in suggestions
        assert "threshold" in suggestions["tax_id"]
        assert "reason" in suggestions["tax_id"]
    
    def test_generate_report(self, mock_extracted_data):
        """Test generation of comprehensive analysis report."""
        analyzer = ConfidenceAnalyzer()
        
        # Add a document
        analyzer.add_document(mock_extracted_data)
        
        # Generate report
        report = analyzer.generate_report()
        
        # Check that all sections are present
        assert "document_confidence" in report
        assert "field_confidence" in report
        assert "verification_rates" in report
        assert "automation_rates" in report
        assert "overall_automation_rate" in report
        assert "threshold_suggestions" in report
        assert "current_thresholds" in report
        assert "sample_size" in report
        assert "timestamp" in report
        
        # Check that sample size is correct
        assert report["sample_size"] == 1


class TestConfidenceDistributionAnalysis:
    """Tests for confidence distribution analysis."""

    def test_analyze_confidence_distribution(self, mock_word_confidences):
        """Test analysis of confidence score distribution."""
        distribution = analyze_confidence_distribution(mock_word_confidences)
        
        # Check that all sections are present
        assert "count" in distribution
        assert "mean" in distribution
        assert "median" in distribution
        assert "std_dev" in distribution
        assert "min" in distribution
        assert "max" in distribution
        assert "percentiles" in distribution
        assert "histogram" in distribution
        assert "confidence_ranges" in distribution
        
        # Check that count is correct
        assert distribution["count"] == len(mock_word_confidences)
        
        # Check that mean is correct
        expected_mean = sum(mock_word_confidences) / len(mock_word_confidences)
        assert abs(distribution["mean"] - expected_mean) < 0.01
        
        # Check that percentiles are present
        assert "p10" in distribution["percentiles"]
        assert "p25" in distribution["percentiles"]
        assert "p75" in distribution["percentiles"]
        assert "p90" in distribution["percentiles"]
        
        # Check that histogram has 10 bins
        assert len(distribution["histogram"]) == 10
        
        # Check that confidence ranges are present
        assert "low" in distribution["confidence_ranges"]
        assert "medium" in distribution["confidence_ranges"]
        assert "high" in distribution["confidence_ranges"]
    
    def test_empty_input(self):
        """Test handling of empty input."""
        distribution = analyze_confidence_distribution([])
        
        # Should return minimal result with count=0
        assert distribution == {"count": 0}


class TestConfidenceScoreCalibrator:
    """Tests for the ConfidenceScoreCalibrator class."""

    def test_calibration(self):
        """Test calibration of confidence scores."""
        calibrator = ConfidenceScoreCalibrator()
        
        # Create paired raw and true confidence scores
        raw_scores = [0.6, 0.7, 0.8, 0.9]
        true_scores = [0.5, 0.6, 0.7, 0.8]  # Systematically lower
        
        # Calibrate the model
        calibrator.calibrate(raw_scores, true_scores)
        
        # Check that calibration was successful
        assert calibrator.is_calibrated
        
        # Check that a and b were calculated correctly
        # For this simple example, a should be approximately 1.0 and b should be approximately -0.1
        assert abs(calibrator.a - 1.0) < 0.1
        assert abs(calibrator.b + 0.1) < 0.1
        
        # Test calibration of a new score
        raw_score = 0.85
        calibrated = calibrator.calibrate_score(raw_score)
        
        # Expected result: 0.85 * a + b ≈ 0.85 - 0.1 = 0.75
        expected = raw_score * calibrator.a + calibrator.b
        assert abs(calibrated - expected) < 0.01
    
    def test_model_specific_calibration(self):
        """Test model-specific calibration of confidence scores."""
        calibrator = ConfidenceScoreCalibrator()
        
        # Create paired raw and true confidence scores for different models
        typed_raw = [0.7, 0.8, 0.9]
        typed_true = [0.7, 0.8, 0.9]  # Well-calibrated
        
        handwritten_raw = [0.7, 0.8, 0.9]
        handwritten_true = [0.5, 0.6, 0.7]  # Overconfident
        
        # Calibrate for each model type
        calibrator.calibrate_by_model("typed_text", typed_raw, typed_true)
        calibrator.calibrate_by_model("handwritten", handwritten_raw, handwritten_true)
        
        # Check that model calibrations were stored
        assert "typed_text" in calibrator.model_calibrations
        assert "handwritten" in calibrator.model_calibrations
        
        # Test calibration for each model type
        raw_score = 0.8
        
        typed_calibrated = calibrator.calibrate_score_by_model(raw_score, "typed_text")
        handwritten_calibrated = calibrator.calibrate_score_by_model(raw_score, "handwritten")
        
        # Typed text should be well-calibrated (minimal adjustment)
        assert abs(typed_calibrated - raw_score) < 0.1
        
        # Handwritten should be adjusted downward
        assert handwritten_calibrated < raw_score
        assert handwritten_calibrated < typed_calibrated
    
    def test_field_specific_calibration(self):
        """Test field-specific calibration of confidence scores."""
        calibrator = ConfidenceScoreCalibrator()
        
        # Create paired raw and true confidence scores for different fields
        business_name_raw = [0.7, 0.8, 0.9]
        business_name_true = [0.7, 0.8, 0.9]  # Well-calibrated
        
        signature_raw = [0.7, 0.8, 0.9]
        signature_true = [0.5, 0.6, 0.7]  # Overconfident
        
        # Calibrate for each field
        calibrator.calibrate_by_field("business_name", business_name_raw, business_name_true)
        calibrator.calibrate_by_field("signature", signature_raw, signature_true)
        
        # Check that field calibrations were stored
        assert "business_name" in calibrator.field_calibrations
        assert "signature" in calibrator.field_calibrations
        
        # Test calibration for each field
        raw_score = 0.8
        
        business_name_calibrated = calibrator.calibrate_score_by_field(raw_score, "business_name")
        signature_calibrated = calibrator.calibrate_score_by_field(raw_score, "signature")
        
        # Business name should be well-calibrated (minimal adjustment)
        assert abs(business_name_calibrated - raw_score) < 0.1
        
        # Signature should be adjusted downward
        assert signature_calibrated < raw_score
        assert signature_calibrated < business_name_calibrated
    
    def test_insufficient_data_handling(self):
        """Test handling of insufficient data for calibration."""
        calibrator = ConfidenceScoreCalibrator()
        
        # Try to calibrate with insufficient data
        with mock.patch("logging.warning"):
            calibrator.calibrate([0.8, 0.9], [0.7, 0.8])  # Only 2 samples
            assert not calibrator.is_calibrated
            
            calibrator.calibrate_by_model("typed_text", [0.8, 0.9], [0.7, 0.8])
            assert "typed_text" not in calibrator.model_calibrations
            
            calibrator.calibrate_by_field("business_name", [0.8, 0.9], [0.7, 0.8])
            assert "business_name" not in calibrator.field_calibrations
    
    def test_save_and_load_calibration(self):
        """Test saving and loading of calibration parameters."""
        calibrator = ConfidenceScoreCalibrator()
        
        # Create paired raw and true confidence scores
        raw_scores = [0.6, 0.7, 0.8, 0.9]
        true_scores = [0.5, 0.6, 0.7, 0.8]  # Systematically lower
        
        # Calibrate the model
        calibrator.calibrate(raw_scores, true_scores)
        
        # Save calibration to a mock file
        mock_file = mock.mock_open()
        with mock.patch("builtins.open", mock_file):
            with mock.patch("json.dump") as mock_json_dump:
                result = calibrator.save_calibration("calibration.json")
                assert result  # Should return True
                mock_json_dump.assert_called_once()
        
        # Load calibration from a mock file
        mock_data = {
            "global": {"a": 0.9, "b": -0.05},
            "models": {"typed_text": {"a": 1.0, "b": 0.0}},
            "fields": {"business_name": {"a": 1.0, "b": 0.0}},
            "is_calibrated": True,
            "timestamp": datetime.now().isoformat()
        }
        
        mock_file = mock.mock_open()
        with mock.patch("builtins.open", mock_file):
            with mock.patch("json.load", return_value=mock_data):
                new_calibrator = ConfidenceScoreCalibrator()
                result = new_calibrator.load_calibration("calibration.json")
                assert result  # Should return True
                
                # Check that parameters were loaded correctly
                assert new_calibrator.is_calibrated
                assert new_calibrator.a == 0.9
                assert new_calibrator.b == -0.05
                assert "typed_text" in new_calibrator.model_calibrations
                assert "business_name" in new_calibrator.field_calibrations


if __name__ == "__main__":
    pytest.main()