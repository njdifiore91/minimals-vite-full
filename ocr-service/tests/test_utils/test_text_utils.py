#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the text_utils module.

This module contains tests for text cleaning, normalization, validation,
key-value pair extraction, and structured data extraction functions to ensure
proper transformation of OCR output into structured data.
"""

import json
import pytest
from unittest.mock import MagicMock, patch

# Import the module to test
from src.utils import text_utils
from src.types.documents import DocumentType
from src.types.extraction import ExtractedData, ExtractedField, FieldLocation


# ===== Text Cleaning and Normalization Tests =====

def test_clean_text_removes_extra_whitespace():
    """Test that clean_text removes extra whitespace."""
    # Arrange
    text = "This   has    extra    whitespace   "
    expected = "This has extra whitespace"
    
    # Act
    result = text_utils.clean_text(text)
    
    # Assert
    assert result == expected


def test_clean_text_normalizes_line_breaks():
    """Test that clean_text normalizes different types of line breaks."""
    # Arrange
    text = "Line 1\r\nLine 2\rLine 3\nLine 4"
    expected = "Line 1\nLine 2\nLine 3\nLine 4"
    
    # Act
    result = text_utils.clean_text(text)
    
    # Assert
    assert result == expected


def test_clean_text_removes_control_characters():
    """Test that clean_text removes control characters."""
    # Arrange
    text = "Text with\x00control\x01characters"
    expected = "Text withcontrolcharacters"
    
    # Act
    result = text_utils.clean_text(text)
    
    # Assert
    assert result == expected


def test_clean_text_handles_empty_input():
    """Test that clean_text handles empty input gracefully."""
    # Arrange
    text = ""
    expected = ""
    
    # Act
    result = text_utils.clean_text(text)
    
    # Assert
    assert result == expected


def test_clean_text_handles_none_input():
    """Test that clean_text handles None input gracefully."""
    # Arrange
    text = None
    expected = ""
    
    # Act
    result = text_utils.clean_text(text)
    
    # Assert
    assert result == expected


def test_clean_text_removes_excessive_newlines():
    """Test that clean_text removes excessive newlines."""
    # Arrange
    text = "Line 1\n\n\n\n\nLine 2"
    expected = "Line 1\n\nLine 2"
    
    # Act
    result = text_utils.clean_text(text)
    
    # Assert
    assert result == expected


def test_normalize_text_converts_to_lowercase():
    """Test that normalize_text converts text to lowercase."""
    # Arrange
    text = "This Has MIXED Case"
    expected = "this has mixed case"
    
    # Act
    result = text_utils.normalize_text(text)
    
    # Assert
    assert result == expected


def test_normalize_text_preserves_case_when_specified():
    """Test that normalize_text preserves case when lowercase=False."""
    # Arrange
    text = "This Has MIXED Case"
    expected = "This Has MIXED Case"
    
    # Act
    result = text_utils.normalize_text(text, lowercase=False)
    
    # Assert
    assert result == expected


def test_normalize_text_removes_punctuation():
    """Test that normalize_text removes most punctuation."""
    # Arrange
    text = "This, has; punctuation! (and) [symbols]."
    expected = "this has punctuation and symbols"
    
    # Act
    result = text_utils.normalize_text(text)
    
    # Assert
    assert result == expected


def test_normalize_text_preserves_specific_characters():
    """Test that normalize_text preserves specific characters needed for validation."""
    # Arrange
    text = "email@example.com 123-456-7890 01/15/2023"
    expected = "email@example.com 123-456-7890 01/15/2023"
    
    # Act
    result = text_utils.normalize_text(text)
    
    # Assert
    assert result == expected


def test_normalize_text_handles_empty_input():
    """Test that normalize_text handles empty input gracefully."""
    # Arrange
    text = ""
    expected = ""
    
    # Act
    result = text_utils.normalize_text(text)
    
    # Assert
    assert result == expected


def test_normalize_text_handles_none_input():
    """Test that normalize_text handles None input gracefully."""
    # Arrange
    text = None
    expected = ""
    
    # Act
    result = text_utils.normalize_text(text)
    
    # Assert
    assert result == expected


# ===== OCR Error Correction Tests =====

def test_correct_ocr_errors_basic_substitutions():
    """Test that correct_ocr_errors applies basic substitutions."""
    # Arrange
    text = "C0mpany Name: ABC C0rp"
    expected = "Company Name: ABC Corp"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text)
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_with_field_type_email():
    """Test that correct_ocr_errors applies email-specific corrections."""
    # Arrange
    text = "user @ example . com"
    expected = "user@example.com"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text, field_type="email")
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_with_field_type_phone():
    """Test that correct_ocr_errors applies phone-specific corrections."""
    # Arrange
    text = "(555) l23-4567"  # lowercase l instead of 1
    expected = "(555) 123-4567"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text, field_type="phone")
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_with_field_type_date():
    """Test that correct_ocr_errors applies date-specific corrections."""
    # Arrange
    text = "Ol/l5/2O23"  # letter O instead of 0, lowercase l instead of 1
    expected = "01/15/2023"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text, field_type="date")
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_with_field_type_currency():
    """Test that correct_ocr_errors applies currency-specific corrections."""
    # Arrange
    text = "$l,234.5O"  # lowercase l instead of 1, letter O instead of 0
    expected = "$1,234.50"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text, field_type="currency")
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_with_field_type_ein():
    """Test that correct_ocr_errors applies EIN-specific corrections."""
    # Arrange
    text = "l2-345678O"  # lowercase l instead of 1, letter O instead of 0
    expected = "12-3456780"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text, field_type="ein")
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_with_field_type_ssn():
    """Test that correct_ocr_errors applies SSN-specific corrections."""
    # Arrange
    text = "l23-45-678O"  # lowercase l instead of 1, letter O instead of 0
    expected = "123-45-6780"
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text, field_type="ssn")
    
    # Assert
    assert result == expected
    assert confidence < 1.0  # Confidence should be reduced due to corrections


def test_correct_ocr_errors_handles_empty_input():
    """Test that correct_ocr_errors handles empty input gracefully."""
    # Arrange
    text = ""
    expected = ""
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text)
    
    # Assert
    assert result == expected
    assert confidence == 0.0  # Confidence should be zero for empty input


def test_correct_ocr_errors_handles_none_input():
    """Test that correct_ocr_errors handles None input gracefully."""
    # Arrange
    text = None
    expected = ""
    
    # Act
    result, confidence = text_utils.correct_ocr_errors(text)
    
    # Assert
    assert result == expected
    assert confidence == 0.0  # Confidence should be zero for None input


# ===== Business Term Normalization Tests =====

def test_normalize_business_terms_basic():
    """Test that normalize_business_terms normalizes common business terms."""
    # Arrange
    text = "Acme Corp is a subsidiary of Acme Incorporated"
    expected = "Acme Corp. is a subsidiary of Acme Inc."
    
    # Act
    result = text_utils.normalize_business_terms(text)
    
    # Assert
    assert result == expected


def test_normalize_business_terms_case_insensitive():
    """Test that normalize_business_terms is case insensitive."""
    # Arrange
    text = "ACME CORP is a subsidiary of acme incorporated"
    expected = "ACME Corp. is a subsidiary of acme Inc."
    
    # Act
    result = text_utils.normalize_business_terms(text)
    
    # Assert
    assert result == expected


def test_normalize_business_terms_multiple_terms():
    """Test that normalize_business_terms handles multiple terms in the same text."""
    # Arrange
    text = "Acme llc, Baker company, and Charlie limited"
    expected = "Acme LLC, Baker Co., and Charlie Ltd."
    
    # Act
    result = text_utils.normalize_business_terms(text)
    
    # Assert
    assert result == expected


def test_normalize_business_terms_handles_empty_input():
    """Test that normalize_business_terms handles empty input gracefully."""
    # Arrange
    text = ""
    expected = ""
    
    # Act
    result = text_utils.normalize_business_terms(text)
    
    # Assert
    assert result == expected


def test_normalize_business_terms_handles_none_input():
    """Test that normalize_business_terms handles None input gracefully."""
    # Arrange
    text = None
    expected = ""
    
    # Act
    result = text_utils.normalize_business_terms(text)
    
    # Assert
    assert result == expected


# ===== Key-Value Pair Extraction Tests =====

def test_extract_key_value_pairs_with_colon_separator():
    """Test that extract_key_value_pairs extracts pairs with colon separators."""
    # Arrange
    text = "Name: John Doe\nAddress: 123 Main St\nPhone: 555-123-4567"
    
    # Act
    result = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert len(result) == 3
    assert result[0][0] == "name"  # Normalized key
    assert result[0][1] == "John Doe"  # Value
    assert result[1][0] == "address"  # Normalized key
    assert result[1][1] == "123 Main St"  # Value
    assert result[2][0] == "phone"  # Normalized key
    assert result[2][1] == "555-123-4567"  # Value


def test_extract_key_value_pairs_with_different_separators():
    """Test that extract_key_value_pairs handles different separators."""
    # Arrange
    text = "Name: John Doe\nAddress = 123 Main St\nPhone - 555-123-4567"
    
    # Act
    result = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert len(result) == 3
    assert result[0][0] == "name"
    assert result[0][1] == "John Doe"
    assert result[1][0] == "address"
    assert result[1][1] == "123 Main St"
    assert result[2][0] == "phone"
    assert result[2][1] == "555-123-4567"


def test_extract_key_value_pairs_with_multiline_values():
    """Test that extract_key_value_pairs handles multi-line values."""
    # Arrange
    text = "Address: 123 Main St\nAnytown, CA 12345\n\nPhone: 555-123-4567"
    
    # Act
    result = text_utils.extract_key_value_pairs(text, line_threshold=2)
    
    # Assert
    assert len(result) == 2
    assert result[0][0] == "address"
    assert "123 Main St" in result[0][1]
    assert "Anytown, CA 12345" in result[0][1]
    assert result[1][0] == "phone"
    assert result[1][1] == "555-123-4567"


def test_extract_key_value_pairs_with_ocr_errors():
    """Test that extract_key_value_pairs corrects OCR errors in values."""
    # Arrange
    text = "Email: john.doe@examp1e.com\nPhone: 555-l23-4567"
    
    # Act
    result = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert len(result) == 2
    assert result[0][0] == "email"
    assert result[0][1] == "john.doe@example.com"  # Corrected value
    assert result[1][0] == "phone"
    assert result[1][1] == "555-123-4567"  # Corrected value


def test_extract_key_value_pairs_handles_empty_input():
    """Test that extract_key_value_pairs handles empty input gracefully."""
    # Arrange
    text = ""
    
    # Act
    result = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert len(result) == 0


def test_extract_key_value_pairs_handles_none_input():
    """Test that extract_key_value_pairs handles None input gracefully."""
    # Arrange
    text = None
    
    # Act
    result = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert len(result) == 0


def test_extract_key_value_pairs_with_complex_form():
    """Test that extract_key_value_pairs handles complex form structures."""
    # Arrange
    text = """LOAN APPLICATION FORM
    
    BUSINESS INFORMATION
    Legal Business Name: Acme Corporation
    DBA Name: Acme Corp
    Tax ID (EIN): 12-3456789
    Business Address: 123 Main St, Anytown, CA 12345
    Business Phone: (555) 123-4567
    Business Email: info@acmecorp.com
    
    OWNER INFORMATION
    Owner Name: John Doe
    Owner SSN: 123-45-6789
    Owner Address: 456 Oak St, Anytown, CA 12345
    Owner Phone: (555) 987-6543
    
    FUNDING REQUEST
    Requested Amount: $50,000.00
    Purpose of Funds: Equipment purchase and working capital
    """
    
    # Act
    result = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert len(result) >= 10  # Should extract at least 10 key-value pairs
    
    # Check a few specific fields
    business_name = next((kv for kv in result if kv[0] == "legal_business_name"), None)
    assert business_name is not None
    assert business_name[1] == "Acme Corporation"
    
    tax_id = next((kv for kv in result if kv[0] == "tax_id"), None)
    assert tax_id is not None
    assert tax_id[1] == "12-3456789"
    
    requested_amount = next((kv for kv in result if kv[0] == "requested_amount"), None)
    assert requested_amount is not None
    assert requested_amount[1] == "$50,000.00"


# ===== Key Normalization Tests =====

def test_normalize_key_basic():
    """Test that normalize_key normalizes basic keys."""
    # Arrange
    key = "Business Name"
    expected = "business_name"
    
    # Act
    result = text_utils.normalize_key(key)
    
    # Assert
    assert result == expected


def test_normalize_key_with_punctuation():
    """Test that normalize_key removes punctuation."""
    # Arrange
    key = "Business Name:"
    expected = "business_name"
    
    # Act
    result = text_utils.normalize_key(key)
    
    # Assert
    assert result == expected


def test_normalize_key_with_common_prefixes():
    """Test that normalize_key removes common prefixes."""
    # Arrange
    key = "Please enter Business Name"
    expected = "business_name"
    
    # Act
    result = text_utils.normalize_key(key)
    
    # Assert
    assert result == expected


def test_normalize_key_with_common_suffixes():
    """Test that normalize_key removes common suffixes."""
    # Arrange
    key = "Business Name (required)"
    expected = "business_name"
    
    # Act
    result = text_utils.normalize_key(key)
    
    # Assert
    assert result == expected


def test_normalize_key_matches_known_variations():
    """Test that normalize_key matches known field name variations."""
    # Arrange
    variations = [
        "email", "e-mail", "email address", "e-mail address"
    ]
    expected = "email"
    
    # Act & Assert
    for variation in variations:
        result = text_utils.normalize_key(variation)
        assert result == expected


def test_normalize_key_handles_empty_input():
    """Test that normalize_key handles empty input gracefully."""
    # Arrange
    key = ""
    expected = ""
    
    # Act
    result = text_utils.normalize_key(key)
    
    # Assert
    assert result == expected


def test_normalize_key_handles_none_input():
    """Test that normalize_key handles None input gracefully."""
    # Arrange
    key = None
    expected = ""
    
    # Act
    result = text_utils.normalize_key(key)
    
    # Assert
    assert result == expected


def test_is_potential_key_positive_cases():
    """Test that is_potential_key correctly identifies potential keys."""
    # Arrange
    potential_keys = [
        "Name",
        "Address",
        "Phone Number",
        "Email Address:",
        "Tax ID (required)"
    ]
    
    # Act & Assert
    for key in potential_keys:
        assert text_utils.is_potential_key(key) is True


def test_is_potential_key_negative_cases():
    """Test that is_potential_key correctly rejects non-keys."""
    # Arrange
    non_keys = [
        "This is a very long line of text that is definitely not a key because it exceeds the maximum length threshold for keys",
        "A",  # Too short
        "123456",  # Just numbers
        ""  # Empty string
    ]
    
    # Act & Assert
    for key in non_keys:
        assert text_utils.is_potential_key(key) is False


def test_is_potential_key_handles_none_input():
    """Test that is_potential_key handles None input gracefully."""
    # Arrange
    key = None
    
    # Act
    result = text_utils.is_potential_key(key)
    
    # Assert
    assert result is False


# ===== Structured Data Extraction Tests =====

def test_extract_structured_data_application_form():
    """Test that extract_structured_data correctly extracts application form data."""
    # Arrange
    text = """LOAN APPLICATION FORM
    
    Legal Name: Acme Corporation
    DBA Name: Acme Corp
    Address: 123 Main St, Anytown, CA 12345
    Phone: (555) 123-4567
    Email: info@acmecorp.com
    EIN: 12-3456789
    Industry: Manufacturing
    Years in Business: 5
    Monthly Revenue: $50,000.00
    Requested Amount: $100,000.00
    """
    
    # Act
    result = text_utils.extract_structured_data(text, DocumentType.APPLICATION)
    
    # Assert
    assert "fields" in result
    assert "metadata" in result
    
    # Check that expected fields are extracted
    fields = result["fields"]
    assert "legal_name" in fields
    assert fields["legal_name"]["value"] == "Acme Corporation"
    assert "dba_name" in fields
    assert fields["dba_name"]["value"] == "Acme Corp"
    assert "ein" in fields
    assert fields["ein"]["value"] == "12-3456789"
    
    # Check metadata
    metadata = result["metadata"]
    assert metadata["document_type"] == DocumentType.APPLICATION.value
    assert "missing_fields" in metadata
    assert "low_confidence_fields" in metadata


def test_extract_structured_data_bank_statement():
    """Test that extract_structured_data correctly extracts bank statement data."""
    # Arrange
    text = """BANK STATEMENT
    
    Bank Name: First National Bank
    Account Holder: Acme Corporation
    Account Number: ****1234
    Statement Period: 01/01/2023 - 01/31/2023
    Opening Balance: $10,000.00
    Closing Balance: $12,500.00
    Total Deposits: $5,000.00
    Total Withdrawals: $2,500.00
    """
    
    # Act
    result = text_utils.extract_structured_data(text, DocumentType.BANK_STATEMENT)
    
    # Assert
    assert "fields" in result
    assert "metadata" in result
    
    # Check that expected fields are extracted
    fields = result["fields"]
    assert "bank_name" in fields
    assert fields["bank_name"]["value"] == "First National Bank"
    assert "account_holder" in fields
    assert fields["account_holder"]["value"] == "Acme Corporation"
    assert "opening_balance" in fields
    assert fields["opening_balance"]["value"] == "$10,000.00"
    
    # Check metadata
    metadata = result["metadata"]
    assert metadata["document_type"] == DocumentType.BANK_STATEMENT.value


def test_extract_structured_data_with_ocr_errors():
    """Test that extract_structured_data handles OCR errors in the input text."""
    # Arrange
    text = """LOAN APPLlCATlON FORM
    
    Legal Name: Acme C0rp0ration
    DBA Name: Acme C0rp
    Address: l23 Main St, Anytown, CA l2345
    Phone: (555) l23-4567
    Email: info@acmec0rp.com
    EIN: l2-3456789
    """
    
    # Act
    result = text_utils.extract_structured_data(text, DocumentType.APPLICATION)
    
    # Assert
    assert "fields" in result
    
    # Check that OCR errors are corrected
    fields = result["fields"]
    assert "legal_name" in fields
    assert fields["legal_name"]["value"] == "Acme Corporation"  # Corrected
    assert "ein" in fields
    assert fields["ein"]["value"] == "12-3456789"  # Corrected
    
    # Check that low confidence fields are flagged
    metadata = result["metadata"]
    assert len(metadata["low_confidence_fields"]) > 0


def test_extract_structured_data_handles_empty_input():
    """Test that extract_structured_data handles empty input gracefully."""
    # Arrange
    text = ""
    
    # Act
    result = text_utils.extract_structured_data(text, DocumentType.APPLICATION)
    
    # Assert
    assert "fields" in result
    assert len(result["fields"]) == 0
    assert "metadata" in result
    assert len(result["metadata"]["missing_fields"]) > 0  # Should have missing fields


def test_extract_structured_data_handles_none_input():
    """Test that extract_structured_data handles None input gracefully."""
    # Arrange
    text = None
    
    # Act
    result = text_utils.extract_structured_data(text, DocumentType.APPLICATION)
    
    # Assert
    assert "fields" in result
    assert len(result["fields"]) == 0
    assert "metadata" in result
    assert len(result["metadata"]["missing_fields"]) > 0  # Should have missing fields


# ===== JSON Schema Generation Tests =====

def test_generate_json_schema_application():
    """Test that generate_json_schema correctly generates a schema for application documents."""
    # Arrange
    document_type = DocumentType.APPLICATION
    
    # Act
    schema = text_utils.generate_json_schema(document_type)
    
    # Assert
    assert "$schema" in schema
    assert "title" in schema
    assert "properties" in schema
    assert "required" in schema
    
    # Check that expected properties are included
    properties = schema["properties"]
    assert "legal_name" in properties
    assert "dba_name" in properties
    assert "address" in properties
    assert "ein" in properties
    
    # Check property types
    assert properties["legal_name"]["type"] == "string"
    assert properties["monthly_revenue"]["type"] == "number"
    
    # Check required fields
    required = schema["required"]
    assert "legal_name" in required
    assert "address" in required
    assert "ein" in required


def test_generate_json_schema_bank_statement():
    """Test that generate_json_schema correctly generates a schema for bank statement documents."""
    # Arrange
    document_type = DocumentType.BANK_STATEMENT
    
    # Act
    schema = text_utils.generate_json_schema(document_type)
    
    # Assert
    assert "properties" in schema
    
    # Check that expected properties are included
    properties = schema["properties"]
    assert "bank_name" in properties
    assert "account_holder" in properties
    assert "account_number" in properties
    assert "statement_period" in properties
    assert "opening_balance" in properties
    assert "closing_balance" in properties
    
    # Check property types
    assert properties["bank_name"]["type"] == "string"
    assert properties["opening_balance"]["type"] == "number"


def test_generate_json_schema_tax_return():
    """Test that generate_json_schema correctly generates a schema for tax return documents."""
    # Arrange
    document_type = DocumentType.TAX_RETURN
    
    # Act
    schema = text_utils.generate_json_schema(document_type)
    
    # Assert
    assert "properties" in schema
    
    # Check that expected properties are included
    properties = schema["properties"]
    assert "tax_year" in properties
    assert "business_name" in properties
    assert "ein" in properties
    assert "gross_receipts" in properties
    assert "total_income" in properties
    assert "total_deductions" in properties
    assert "taxable_income" in properties
    assert "total_tax" in properties
    
    # Check property types
    assert properties["tax_year"]["type"] == "string"
    assert properties["gross_receipts"]["type"] == "number"


def test_generate_json_schema_unknown_document_type():
    """Test that generate_json_schema handles unknown document types gracefully."""
    # Arrange - Create a custom document type not in the predefined types
    class CustomDocumentType(enum.Enum):
        CUSTOM = "custom"
    
    document_type = CustomDocumentType.CUSTOM
    
    # Act
    schema = text_utils.generate_json_schema(document_type)
    
    # Assert
    assert "properties" in schema
    assert len(schema["properties"]) == 0  # Should have no properties
    assert "required" in schema
    assert len(schema["required"]) == 0  # Should have no required fields


# ===== Table Extraction Tests =====

def test_extract_tables_basic():
    """Test that extract_tables correctly extracts basic tables."""
    # Arrange
    text = """Date       Description        Amount
    01/15/2023  Deposit            $1,000.00
    01/20/2023  Withdrawal         $500.00
    01/25/2023  Interest           $2.50"""
    
    # Act
    tables = text_utils.extract_tables(text)
    
    # Assert
    assert len(tables) == 1
    table = tables[0]
    assert "headers" in table
    assert "rows" in table
    
    # Check headers
    assert len(table["headers"]) == 3
    assert "Date" in table["headers"]
    assert "Description" in table["headers"]
    assert "Amount" in table["headers"]
    
    # Check rows
    assert len(table["rows"]) == 3
    assert table["rows"][0][0] == "01/15/2023"
    assert table["rows"][0][1] == "Deposit"
    assert table["rows"][0][2] == "$1,000.00"


def test_extract_tables_multiple():
    """Test that extract_tables correctly extracts multiple tables."""
    # Arrange
    text = """Table 1:
    Date       Description        Amount
    01/15/2023  Deposit            $1,000.00
    01/20/2023  Withdrawal         $500.00
    
    Table 2:
    Item        Quantity    Price       Total
    Widget A    5           $10.00      $50.00
    Widget B    10          $15.00      $150.00"""
    
    # Act
    tables = text_utils.extract_tables(text)
    
    # Assert
    assert len(tables) == 2
    
    # Check first table
    table1 = tables[0]
    assert len(table1["headers"]) == 3
    assert len(table1["rows"]) == 2
    
    # Check second table
    table2 = tables[1]
    assert len(table2["headers"]) == 4
    assert len(table2["rows"]) == 2


def test_extract_tables_with_misaligned_columns():
    """Test that extract_tables handles misaligned columns."""
    # Arrange
    text = """Date      Description          Amount
    01/15/2023    Deposit      $1,000.00
    01/20/2023  Withdrawal  $500.00
    01/25/2023 Interest $2.50"""
    
    # Act
    tables = text_utils.extract_tables(text)
    
    # Assert
    # The function should still extract a table, but some rows might be missing
    # due to misalignment
    assert len(tables) > 0


def test_extract_tables_handles_empty_input():
    """Test that extract_tables handles empty input gracefully."""
    # Arrange
    text = ""
    
    # Act
    tables = text_utils.extract_tables(text)
    
    # Assert
    assert len(tables) == 0


def test_extract_tables_handles_none_input():
    """Test that extract_tables handles None input gracefully."""
    # Arrange
    text = None
    
    # Act
    tables = text_utils.extract_tables(text)
    
    # Assert
    assert len(tables) == 0


# ===== Field Validation Tests =====

def test_validate_field_email_valid():
    """Test that validate_field correctly validates valid email addresses."""
    # Arrange
    value = "john.doe@example.com"
    field_type = "email"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == value
    assert confidence > 0.8  # High confidence for valid email


def test_validate_field_email_invalid():
    """Test that validate_field correctly identifies invalid email addresses."""
    # Arrange
    value = "john.doe@example"  # Missing TLD
    field_type = "email"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is False
    assert corrected_value == "john.doe@example"  # Attempted correction
    assert confidence < 0.8  # Low confidence for invalid email


def test_validate_field_phone_valid():
    """Test that validate_field correctly validates valid phone numbers."""
    # Arrange
    value = "(555) 123-4567"
    field_type = "phone"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == value
    assert confidence > 0.8  # High confidence for valid phone


def test_validate_field_phone_with_ocr_errors():
    """Test that validate_field corrects OCR errors in phone numbers."""
    # Arrange
    value = "(555) l23-4567"  # lowercase l instead of 1
    field_type = "phone"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == "(555) 123-4567"  # Corrected
    assert confidence < 1.0  # Reduced confidence due to correction


def test_validate_field_date_valid():
    """Test that validate_field correctly validates valid dates."""
    # Arrange
    value = "01/15/2023"
    field_type = "date"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == value
    assert confidence > 0.8  # High confidence for valid date


def test_validate_field_date_with_ocr_errors():
    """Test that validate_field corrects OCR errors in dates."""
    # Arrange
    value = "Ol/l5/2O23"  # letter O instead of 0, lowercase l instead of 1
    field_type = "date"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == "01/15/2023"  # Corrected
    assert confidence < 1.0  # Reduced confidence due to correction


def test_validate_field_currency_valid():
    """Test that validate_field correctly validates valid currency values."""
    # Arrange
    value = "$1,234.56"
    field_type = "currency"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == value
    assert confidence > 0.8  # High confidence for valid currency


def test_validate_field_ein_valid():
    """Test that validate_field correctly validates valid EIN numbers."""
    # Arrange
    value = "12-3456789"
    field_type = "ein"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == value
    assert confidence > 0.8  # High confidence for valid EIN


def test_validate_field_ssn_valid():
    """Test that validate_field correctly validates valid SSN numbers."""
    # Arrange
    value = "123-45-6789"
    field_type = "ssn"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is True
    assert corrected_value == value
    assert confidence > 0.8  # High confidence for valid SSN


def test_validate_field_handles_empty_input():
    """Test that validate_field handles empty input gracefully."""
    # Arrange
    value = ""
    field_type = "email"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is False
    assert corrected_value == ""
    assert confidence == 0.0  # Zero confidence for empty input


def test_validate_field_handles_none_input():
    """Test that validate_field handles None input gracefully."""
    # Arrange
    value = None
    field_type = "email"
    
    # Act
    is_valid, corrected_value, confidence = text_utils.validate_field(value, field_type)
    
    # Assert
    assert is_valid is False
    assert corrected_value == ""
    assert confidence == 0.0  # Zero confidence for None input


# ===== JSON Formatting Tests =====

def test_format_extracted_data_as_json():
    """Test that format_extracted_data_as_json correctly formats extracted data as JSON."""
    # Arrange
    extracted_data = {
        "fields": {
            "name": {
                "value": "John Doe",
                "confidence": 0.95,
                "location": {"page": 1, "top": 0.1, "left": 0.1, "width": 0.3, "height": 0.05}
            },
            "email": {
                "value": "john.doe@example.com",
                "confidence": 0.9,
                "location": {"page": 1, "top": 0.2, "left": 0.1, "width": 0.4, "height": 0.05}
            }
        },
        "metadata": {
            "document_type": "application",
            "extraction_timestamp": "2023-01-01T00:00:00Z",
            "missing_fields": [],
            "low_confidence_fields": []
        }
    }
    
    # Act
    json_string = text_utils.format_extracted_data_as_json(extracted_data)
    
    # Assert
    assert isinstance(json_string, str)
    
    # Verify that the JSON string can be parsed back to a dictionary
    parsed_data = json.loads(json_string)
    assert "fields" in parsed_data
    assert "metadata" in parsed_data
    assert "name" in parsed_data["fields"]
    assert "email" in parsed_data["fields"]
    assert parsed_data["fields"]["name"]["value"] == "John Doe"
    assert parsed_data["fields"]["email"]["value"] == "john.doe@example.com"


def test_format_extracted_data_as_json_handles_empty_input():
    """Test that format_extracted_data_as_json handles empty input gracefully."""
    # Arrange
    extracted_data = {
        "fields": {},
        "metadata": {
            "document_type": "application",
            "extraction_timestamp": "2023-01-01T00:00:00Z",
            "missing_fields": ["name", "email", "address"],
            "low_confidence_fields": []
        }
    }
    
    # Act
    json_string = text_utils.format_extracted_data_as_json(extracted_data)
    
    # Assert
    assert isinstance(json_string, str)
    
    # Verify that the JSON string can be parsed back to a dictionary
    parsed_data = json.loads(json_string)
    assert "fields" in parsed_data
    assert len(parsed_data["fields"]) == 0  # Empty fields
    assert "metadata" in parsed_data
    assert len(parsed_data["metadata"]["missing_fields"]) == 3  # Three missing fields


# ===== Form Field Extraction Tests =====

def test_extract_form_fields_basic():
    """Test that extract_form_fields correctly extracts basic form fields."""
    # Arrange
    text = """LOAN APPLICATION FORM
    
    Name: John Doe
    Email: john.doe@example.com
    Phone: (555) 123-4567
    Address: 123 Main St, Anytown, CA 12345
    """
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert "name" in form_fields
    assert form_fields["name"]["value"] == "John Doe"
    assert form_fields["name"]["field_type"] == "text"
    
    assert "email" in form_fields
    assert form_fields["email"]["value"] == "john.doe@example.com"
    assert form_fields["email"]["field_type"] == "email"
    assert form_fields["email"]["is_valid"] is True
    
    assert "phone" in form_fields
    assert form_fields["phone"]["value"] == "(555) 123-4567"
    assert form_fields["phone"]["field_type"] == "phone"
    assert form_fields["phone"]["is_valid"] is True


def test_extract_form_fields_with_ocr_errors():
    """Test that extract_form_fields corrects OCR errors in form fields."""
    # Arrange
    text = """LOAN APPLICATION FORM
    
    Name: J0hn D0e
    Email: john.doe@examp1e.com
    Phone: (555) l23-4567
    """
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert "name" in form_fields
    assert form_fields["name"]["value"] == "John Doe"  # Corrected
    
    assert "email" in form_fields
    assert form_fields["email"]["value"] == "john.doe@example.com"  # Corrected
    
    assert "phone" in form_fields
    assert form_fields["phone"]["value"] == "(555) 123-4567"  # Corrected


def test_extract_form_fields_with_invalid_fields():
    """Test that extract_form_fields identifies invalid fields."""
    # Arrange
    text = """LOAN APPLICATION FORM
    
    Email: john.doe@invalid
    Phone: 555-123
    """
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert "email" in form_fields
    assert form_fields["email"]["is_valid"] is False
    assert form_fields["email"]["needs_review"] is True
    
    assert "phone" in form_fields
    assert form_fields["phone"]["is_valid"] is False
    assert form_fields["phone"]["needs_review"] is True


def test_extract_form_fields_handles_empty_input():
    """Test that extract_form_fields handles empty input gracefully."""
    # Arrange
    text = ""
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert isinstance(form_fields, dict)
    assert len(form_fields) == 0  # No fields extracted


def test_extract_form_fields_handles_none_input():
    """Test that extract_form_fields handles None input gracefully."""
    # Arrange
    text = None
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert isinstance(form_fields, dict)
    assert len(form_fields) == 0  # No fields extracted


# ===== Field Type Determination Tests =====

def test_determine_field_type_email():
    """Test that determine_field_type correctly identifies email fields."""
    # Arrange
    keys = ["email", "e-mail", "email address", "business email"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "email"


def test_determine_field_type_phone():
    """Test that determine_field_type correctly identifies phone fields."""
    # Arrange
    keys = ["phone", "telephone", "mobile", "cell", "business phone"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "phone"


def test_determine_field_type_date():
    """Test that determine_field_type correctly identifies date fields."""
    # Arrange
    keys = ["date", "dob", "birth date", "issue date", "expiration date"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "date"


def test_determine_field_type_currency():
    """Test that determine_field_type correctly identifies currency fields."""
    # Arrange
    keys = ["amount", "revenue", "income", "payment", "balance", "price"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "currency"


def test_determine_field_type_ein():
    """Test that determine_field_type correctly identifies EIN fields."""
    # Arrange
    keys = ["ein", "tax id", "tax identification", "employer identification"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "ein"


def test_determine_field_type_ssn():
    """Test that determine_field_type correctly identifies SSN fields."""
    # Arrange
    keys = ["ssn", "social security", "social security number"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "ssn"


def test_determine_field_type_zip():
    """Test that determine_field_type correctly identifies ZIP code fields."""
    # Arrange
    keys = ["zip", "zip code", "postal", "postal code", "post code"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "zip"


def test_determine_field_type_default():
    """Test that determine_field_type returns 'text' for unknown field types."""
    # Arrange
    keys = ["name", "address", "city", "state", "notes", "comments"]
    
    # Act & Assert
    for key in keys:
        assert text_utils.determine_field_type(key) == "text"


# ===== Section Extraction Tests =====

def test_extract_sections_basic():
    """Test that extract_sections correctly extracts basic document sections."""
    # Arrange
    text = """BUSINESS INFORMATION
    
    Legal Business Name: Acme Corporation
    DBA Name: Acme Corp
    Tax ID (EIN): 12-3456789
    
    OWNER INFORMATION
    
    Owner Name: John Doe
    Owner SSN: 123-45-6789
    Owner Address: 456 Oak St, Anytown, CA 12345
    
    FUNDING REQUEST
    
    Requested Amount: $50,000.00
    Purpose of Funds: Equipment purchase and working capital
    """
    
    # Act
    sections = text_utils.extract_sections(text)
    
    # Assert
    assert len(sections) == 4  # HEADER + 3 sections
    assert "BUSINESS INFORMATION" in sections
    assert "OWNER INFORMATION" in sections
    assert "FUNDING REQUEST" in sections
    
    # Check section content
    assert "Legal Business Name" in sections["BUSINESS INFORMATION"]
    assert "Owner Name" in sections["OWNER INFORMATION"]
    assert "Requested Amount" in sections["FUNDING REQUEST"]


def test_extract_sections_with_numbered_sections():
    """Test that extract_sections correctly extracts numbered document sections."""
    # Arrange
    text = """SECTION 1: BUSINESS INFORMATION
    
    Legal Business Name: Acme Corporation
    DBA Name: Acme Corp
    
    SECTION 2: OWNER INFORMATION
    
    Owner Name: John Doe
    Owner SSN: 123-45-6789
    
    SECTION 3: FUNDING REQUEST
    
    Requested Amount: $50,000.00
    Purpose of Funds: Equipment purchase
    """
    
    # Act
    sections = text_utils.extract_sections(text)
    
    # Assert
    assert len(sections) == 4  # HEADER + 3 sections
    assert "SECTION 1: BUSINESS INFORMATION" in sections
    assert "SECTION 2: OWNER INFORMATION" in sections
    assert "SECTION 3: FUNDING REQUEST" in sections


def test_extract_sections_with_mixed_case():
    """Test that extract_sections correctly extracts sections with mixed case."""
    # Arrange
    text = """Business Information
    
    Legal Business Name: Acme Corporation
    DBA Name: Acme Corp
    
    OWNER INFORMATION
    
    Owner Name: John Doe
    Owner SSN: 123-45-6789
    """
    
    # Act
    sections = text_utils.extract_sections(text)
    
    # Assert
    # The function should only identify all-caps sections as headings
    assert "OWNER INFORMATION" in sections
    assert "Business Information" not in sections


def test_extract_sections_handles_empty_input():
    """Test that extract_sections handles empty input gracefully."""
    # Arrange
    text = ""
    
    # Act
    sections = text_utils.extract_sections(text)
    
    # Assert
    assert isinstance(sections, dict)
    assert len(sections) == 0  # No sections extracted


def test_extract_sections_handles_none_input():
    """Test that extract_sections handles None input gracefully."""
    # Arrange
    text = None
    
    # Act
    sections = text_utils.extract_sections(text)
    
    # Assert
    assert isinstance(sections, dict)
    assert len(sections) == 0  # No sections extracted


# ===== Tests Using Fixtures =====

def test_clean_text_with_sample_ocr_text(sample_ocr_text):
    """Test clean_text with sample OCR text from fixtures."""
    # Act
    cleaned_noisy = text_utils.clean_text(sample_ocr_text["noisy"])
    cleaned_form_fields = text_utils.clean_text(sample_ocr_text["form_fields"])
    cleaned_mixed_format = text_utils.clean_text(sample_ocr_text["mixed_format"])
    
    # Assert
    assert len(cleaned_noisy) > 0
    assert len(cleaned_form_fields) > 0
    assert len(cleaned_mixed_format) > 0
    assert "\n" in cleaned_form_fields  # Should preserve line breaks
    assert "\n\n" in cleaned_mixed_format  # Should preserve paragraph breaks


def test_extract_key_value_pairs_with_fixtures(sample_ocr_text):
    """Test extract_key_value_pairs with sample OCR text from fixtures."""
    # Act
    pairs_form = text_utils.extract_key_value_pairs(sample_ocr_text["form_fields"])
    pairs_mixed = text_utils.extract_key_value_pairs(sample_ocr_text["mixed_format"])
    
    # Assert
    assert len(pairs_form) >= 5  # Should extract at least 5 key-value pairs from form fields
    assert len(pairs_mixed) >= 3  # Should extract at least 3 key-value pairs from mixed format
    
    # Check specific fields from form
    name_pair = next((p for p in pairs_form if p[0] == "name"), None)
    assert name_pair is not None
    assert name_pair[1] == "John Doe"
    
    # Check specific fields from mixed format
    date_pair = next((p for p in pairs_mixed if p[0] == "date"), None)
    assert date_pair is not None
    assert "01/15/2023" in date_pair[1]


def test_extract_structured_data_with_fixtures(sample_ocr_text, key_value_pairs):
    """Test extract_structured_data with sample OCR text and key-value pairs from fixtures."""
    # Act
    application_data = text_utils.extract_structured_data(
        sample_ocr_text["form_fields"], DocumentType.APPLICATION
    )
    
    # Assert
    assert "fields" in application_data
    assert "metadata" in application_data
    assert application_data["metadata"]["document_type"] == DocumentType.APPLICATION.value
    
    # Check that some fields were extracted
    fields = application_data["fields"]
    assert len(fields) > 0
    
    # Check that the metadata includes expected fields
    metadata = application_data["metadata"]
    assert "missing_fields" in metadata
    assert "low_confidence_fields" in metadata
    assert "needs_review" in metadata


def test_extract_tables_with_fixtures(sample_ocr_text):
    """Test extract_tables with sample OCR text from fixtures."""
    # Act
    tables_from_table = text_utils.extract_tables(sample_ocr_text["table"])
    tables_from_mixed = text_utils.extract_tables(sample_ocr_text["mixed_format"])
    
    # Assert
    assert len(tables_from_table) >= 1  # Should extract at least one table from table text
    assert len(tables_from_mixed) >= 1  # Should extract at least one table from mixed format
    
    # Check the structure of the first table
    if tables_from_table:
        table = tables_from_table[0]
        assert "headers" in table
        assert "rows" in table
        assert len(table["headers"]) >= 3  # Should have at least 3 columns
        assert len(table["rows"]) >= 2  # Should have at least 2 rows


def test_validate_field_with_fixtures(key_value_pairs):
    """Test validate_field with key-value pairs from fixtures."""
    # Extract some fields from the fixtures
    application = key_value_pairs["application"]
    
    # Act & Assert for email field
    is_valid, corrected, confidence = text_utils.validate_field(
        application["email"], "email"
    )
    assert is_valid is True
    assert corrected == application["email"]
    assert confidence > 0.8
    
    # Act & Assert for phone field
    is_valid, corrected, confidence = text_utils.validate_field(
        application["phone"], "phone"
    )
    assert is_valid is True
    assert corrected == application["phone"]
    assert confidence > 0.8
    
    # Act & Assert for tax_id field
    is_valid, corrected, confidence = text_utils.validate_field(
        application["tax_id"], "ein"
    )
    assert is_valid is True
    assert corrected == application["tax_id"]
    assert confidence > 0.8


# ===== Integration Tests =====

def test_end_to_end_application_processing():
    """Test end-to-end processing of an application form."""
    # Arrange
    application_text = """LOAN APPLICATION FORM
    
    BUSINESS INFORMATION
    Legal Name: Acme Corporation
    DBA Name: Acme Corp
    Tax ID (EIN): 12-3456789
    Address: 123 Main St, Anytown, CA 12345
    Phone: (555) 123-4567
    Email: info@acmecorp.com
    Industry: Manufacturing
    Years in Business: 5
    Monthly Revenue: $50,000.00
    
    OWNER INFORMATION
    Owner Name: John Doe
    Owner SSN: 123-45-6789
    Owner Address: 456 Oak St, Anytown, CA 12345
    Owner Phone: (555) 987-6543
    
    FUNDING REQUEST
    Requested Amount: $100,000.00
    Purpose of Funds: Equipment purchase and working capital
    
    Signature: John Doe
    Date: 01/15/2023
    """
    
    # Act - Process the text through multiple functions
    cleaned_text = text_utils.clean_text(application_text)
    key_value_pairs = text_utils.extract_key_value_pairs(cleaned_text)
    structured_data = text_utils.extract_structured_data(cleaned_text, DocumentType.APPLICATION)
    sections = text_utils.extract_sections(cleaned_text)
    form_fields = text_utils.extract_form_fields(cleaned_text)
    json_output = text_utils.format_extracted_data_as_json(structured_data)
    
    # Assert
    # Check key-value extraction
    assert len(key_value_pairs) >= 10  # Should extract at least 10 key-value pairs
    
    # Check structured data extraction
    assert "fields" in structured_data
    assert "metadata" in structured_data
    assert len(structured_data["fields"]) >= 5  # Should extract at least 5 fields
    
    # Check section extraction
    assert len(sections) >= 3  # Should extract at least 3 sections
    assert "BUSINESS INFORMATION" in sections
    assert "OWNER INFORMATION" in sections
    assert "FUNDING REQUEST" in sections
    
    # Check form field extraction
    assert len(form_fields) >= 5  # Should extract at least 5 form fields
    assert "legal_name" in form_fields or "name" in form_fields
    assert "requested_amount" in form_fields or "amount" in form_fields
    
    # Check JSON output
    assert isinstance(json_output, str)
    parsed_json = json.loads(json_output)
    assert "fields" in parsed_json
    assert "metadata" in parsed_json


def test_end_to_end_bank_statement_processing():
    """Test end-to-end processing of a bank statement."""
    # Arrange
    bank_statement_text = """FIRST NATIONAL BANK
    ACCOUNT STATEMENT
    
    ACCOUNT INFORMATION
    Account Holder: Acme Corporation
    Account Number: ****1234
    Statement Period: 01/01/2023 - 01/31/2023
    
    SUMMARY
    Opening Balance: $10,000.00
    Total Deposits: $5,000.00
    Total Withdrawals: $2,500.00
    Closing Balance: $12,500.00
    
    TRANSACTION DETAILS
    Date        Description                 Amount      Balance
    01/05/2023  Deposit                    $2,000.00   $12,000.00
    01/10/2023  Deposit                    $3,000.00   $15,000.00
    01/15/2023  Withdrawal - Rent          -$1,500.00  $13,500.00
    01/20/2023  Withdrawal - Utilities     -$500.00    $13,000.00
    01/25/2023  Withdrawal - Payroll       -$500.00    $12,500.00
    """
    
    # Act - Process the text through multiple functions
    cleaned_text = text_utils.clean_text(bank_statement_text)
    key_value_pairs = text_utils.extract_key_value_pairs(cleaned_text)
    structured_data = text_utils.extract_structured_data(cleaned_text, DocumentType.BANK_STATEMENT)
    sections = text_utils.extract_sections(cleaned_text)
    tables = text_utils.extract_tables(cleaned_text)
    json_output = text_utils.format_extracted_data_as_json(structured_data)
    
    # Assert
    # Check key-value extraction
    assert len(key_value_pairs) >= 5  # Should extract at least 5 key-value pairs
    
    # Check structured data extraction
    assert "fields" in structured_data
    assert "metadata" in structured_data
    assert len(structured_data["fields"]) >= 3  # Should extract at least 3 fields
    
    # Check section extraction
    assert len(sections) >= 3  # Should extract at least 3 sections
    assert "ACCOUNT INFORMATION" in sections or "ACCOUNT STATEMENT" in sections
    assert "SUMMARY" in sections
    assert "TRANSACTION DETAILS" in sections
    
    # Check table extraction
    assert len(tables) >= 1  # Should extract at least 1 table
    if tables:
        assert len(tables[0]["headers"]) >= 3  # Should have at least 3 columns
        assert len(tables[0]["rows"]) >= 3  # Should have at least 3 rows
    
    # Check JSON output
    assert isinstance(json_output, str)
    parsed_json = json.loads(json_output)
    assert "fields" in parsed_json
    assert "metadata" in parsed_json


# ===== Edge Case Tests =====

def test_handling_of_malformed_input():
    """Test handling of malformed or corrupted input text."""
    # Arrange
    malformed_text = """\x00\x01\x02Name: J\xffohn Doe\n\r\n\r\nEmail: \u2028john.doe@example.com\u2029"""
    
    # Act
    cleaned_text = text_utils.clean_text(malformed_text)
    key_value_pairs = text_utils.extract_key_value_pairs(cleaned_text)
    
    # Assert
    assert "\x00" not in cleaned_text  # Control characters should be removed
    assert "\xff" not in cleaned_text  # Non-printable characters should be removed
    assert "\u2028" not in cleaned_text  # Line separators should be normalized
    assert "\u2029" not in cleaned_text  # Paragraph separators should be normalized
    
    # Should still extract key-value pairs despite malformed input
    assert len(key_value_pairs) > 0
    name_pair = next((p for p in key_value_pairs if p[0] == "name"), None)
    assert name_pair is not None
    email_pair = next((p for p in key_value_pairs if p[0] == "email"), None)
    assert email_pair is not None


def test_handling_of_extremely_long_input():
    """Test handling of extremely long input text."""
    # Arrange
    long_text = "Line " + "very long content " * 1000 + "\n" + "Name: John Doe\nEmail: john.doe@example.com"
    
    # Act
    cleaned_text = text_utils.clean_text(long_text)
    key_value_pairs = text_utils.extract_key_value_pairs(cleaned_text)
    
    # Assert
    assert len(cleaned_text) > 1000  # Should not truncate the text
    
    # Should still extract key-value pairs from the end of the text
    assert len(key_value_pairs) >= 2
    name_pair = next((p for p in key_value_pairs if p[0] == "name"), None)
    assert name_pair is not None
    assert name_pair[1] == "John Doe"
    email_pair = next((p for p in key_value_pairs if p[0] == "email"), None)
    assert email_pair is not None
    assert email_pair[1] == "john.doe@example.com"


# ===== Mock Tests =====

@patch('src.utils.text_utils.correct_ocr_errors')
def test_extract_key_value_pairs_calls_correct_ocr_errors(mock_correct_ocr_errors):
    """Test that extract_key_value_pairs calls correct_ocr_errors for each value."""
    # Arrange
    mock_correct_ocr_errors.return_value = ("Corrected Value", 0.95)
    text = "Name: John Doe\nEmail: john.doe@example.com"
    
    # Act
    key_value_pairs = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert mock_correct_ocr_errors.call_count >= 2  # Should be called for each value
    assert len(key_value_pairs) == 2
    assert key_value_pairs[0][1] == "Corrected Value"  # Should use the corrected value
    assert key_value_pairs[0][2] == 0.95  # Should use the confidence score


@patch('src.utils.text_utils.normalize_key')
def test_extract_key_value_pairs_calls_normalize_key(mock_normalize_key):
    """Test that extract_key_value_pairs calls normalize_key for each key."""
    # Arrange
    mock_normalize_key.return_value = "normalized_key"
    text = "Name: John Doe\nEmail: john.doe@example.com"
    
    # Act
    key_value_pairs = text_utils.extract_key_value_pairs(text)
    
    # Assert
    assert mock_normalize_key.call_count >= 2  # Should be called for each key
    assert len(key_value_pairs) == 2
    assert key_value_pairs[0][0] == "normalized_key"  # Should use the normalized key
    assert key_value_pairs[1][0] == "normalized_key"  # Should use the normalized key


@patch('src.utils.text_utils.extract_key_value_pairs')
def test_extract_structured_data_calls_extract_key_value_pairs(mock_extract_key_value_pairs):
    """Test that extract_structured_data calls extract_key_value_pairs."""
    # Arrange
    mock_extract_key_value_pairs.return_value = [
        ("name", "John Doe", 0.95),
        ("email", "john.doe@example.com", 0.9)
    ]
    text = "Name: John Doe\nEmail: john.doe@example.com"
    
    # Act
    structured_data = text_utils.extract_structured_data(text, DocumentType.APPLICATION)
    
    # Assert
    mock_extract_key_value_pairs.assert_called_once_with(text)
    assert "fields" in structured_data
    assert "name" in structured_data["fields"]
    assert "email" in structured_data["fields"]


@patch('src.utils.text_utils.validate_field')
def test_extract_form_fields_calls_validate_field(mock_validate_field):
    """Test that extract_form_fields calls validate_field for each field."""
    # Arrange
    mock_validate_field.return_value = (True, "Validated Value", 0.95)
    text = "Name: John Doe\nEmail: john.doe@example.com"
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert mock_validate_field.call_count >= 2  # Should be called for each field
    assert len(form_fields) == 2
    assert form_fields["name"]["value"] == "Validated Value"  # Should use the validated value
    assert form_fields["name"]["confidence"] < 1.0  # Should combine confidence scores
    assert form_fields["name"]["is_valid"] is True  # Should use the validation result


@patch('src.utils.text_utils.determine_field_type')
def test_extract_form_fields_calls_determine_field_type(mock_determine_field_type):
    """Test that extract_form_fields calls determine_field_type for each field."""
    # Arrange
    mock_determine_field_type.return_value = "custom_type"
    text = "Name: John Doe\nEmail: john.doe@example.com"
    
    # Act
    form_fields = text_utils.extract_form_fields(text)
    
    # Assert
    assert mock_determine_field_type.call_count >= 2  # Should be called for each field
    assert len(form_fields) == 2
    assert form_fields["name"]["field_type"] == "custom_type"  # Should use the determined field type
    assert form_fields["email"]["field_type"] == "custom_type"  # Should use the determined field type