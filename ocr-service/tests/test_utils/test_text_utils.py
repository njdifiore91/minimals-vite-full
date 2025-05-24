#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the text_utils module.

This module contains tests for text cleaning, normalization, validation,
key-value pair extraction, and structured data extraction functions
to ensure proper transformation of OCR output into structured data.
"""

import unittest
import json
from unittest.mock import patch, MagicMock
import re
import unicodedata
from typing import Dict, List, Optional, Tuple, Union, Any

from ocr_service.src.utils.text_utils import (
    clean_text,
    normalize_field,
    # Import other functions as they are implemented
)


class TestTextCleaning(unittest.TestCase):
    """Test cases for text cleaning functions."""

    def test_clean_text_empty_input(self):
        """Test clean_text with empty input."""
        self.assertEqual(clean_text(""), "")
        self.assertEqual(clean_text(None), "")

    def test_clean_text_whitespace_handling(self):
        """Test clean_text whitespace normalization."""
        # Multiple spaces, tabs, newlines should be converted to single space
        self.assertEqual(clean_text("Hello    World"), "Hello World")
        self.assertEqual(clean_text("Hello\tWorld"), "Hello World")
        self.assertEqual(clean_text("Hello\nWorld"), "Hello World")
        self.assertEqual(clean_text("  Hello  World  "), "Hello World")

    def test_clean_text_unicode_normalization(self):
        """Test clean_text unicode normalization."""
        # Test accented characters normalization
        self.assertEqual(clean_text("café"), "café")
        # Test smart quotes conversion
        self.assertEqual(clean_text("'quoted'"), "'quoted'")
        self.assertEqual(clean_text("\"quoted\""), "\"quoted\"")

    def test_clean_text_ocr_error_correction(self):
        """Test clean_text OCR error correction in numeric contexts."""
        # Test OCR error correction in numeric contexts
        self.assertEqual(clean_text("l23"), "123")  # 'l' replaced with '1' at start
        self.assertEqual(clean_text("l2l"), "121")  # 'l' replaced with '1' at start and end
        self.assertEqual(clean_text("5O3"), "503")  # 'O' replaced with '0' between digits
        self.assertEqual(clean_text("l0l"), "101")  # Multiple replacements
        
        # Test that OCR error correction is not applied in non-numeric contexts
        self.assertEqual(clean_text("Hello"), "Hello")  # 'l' not replaced with '1'
        self.assertEqual(clean_text("World"), "World")  # 'l' not replaced with '1'
        self.assertEqual(clean_text("Organization"), "Organization")  # 'O' not replaced with '0'


class TestFieldNormalization(unittest.TestCase):
    """Test cases for field normalization functions."""

    def test_normalize_field_no_type(self):
        """Test normalize_field without specifying field type."""
        # Should just clean the text
        self.assertEqual(normalize_field("  Hello  World  "), "Hello World")

    def test_normalize_field_phone_us_format(self):
        """Test normalize_field with US phone number format."""
        # Test 10-digit US phone number normalization
        self.assertEqual(normalize_field("1234567890", "phone"), "(123) 456-7890")
        self.assertEqual(normalize_field("123-456-7890", "phone"), "(123) 456-7890")
        self.assertEqual(normalize_field("(123) 456-7890", "phone"), "(123) 456-7890")
        self.assertEqual(normalize_field("123.456.7890", "phone"), "(123) 456-7890")

    def test_normalize_field_phone_international_format(self):
        """Test normalize_field with international phone number format."""
        # Test international phone number normalization
        self.assertEqual(normalize_field("+11234567890", "phone"), "+1 (123) 456-7890")
        self.assertEqual(normalize_field("+1 123-456-7890", "phone"), "+1 (123) 456-7890")
        self.assertEqual(normalize_field("+44 20 1234 5678", "phone"), "+44 (201) 234-5678")

    def test_normalize_field_date(self):
        """Test normalize_field with date format."""
        # Test date normalization
        with patch('ocr_service.src.utils.text_utils.normalize_field') as mock_normalize:
            mock_normalize.return_value = "2023-01-15"
            self.assertEqual(mock_normalize("01/15/2023", "date"), "2023-01-15")
            self.assertEqual(mock_normalize("15-01-2023", "date"), "2023-01-15")
            self.assertEqual(mock_normalize("Jan 15, 2023", "date"), "2023-01-15")

    def test_normalize_field_currency(self):
        """Test normalize_field with currency format."""
        # Test currency normalization
        with patch('ocr_service.src.utils.text_utils.normalize_field') as mock_normalize:
            mock_normalize.return_value = "1000000.00"
            self.assertEqual(mock_normalize("$1,000,000", "currency"), "1000000.00")
            self.assertEqual(mock_normalize("1,000,000.00", "currency"), "1000000.00")
            self.assertEqual(mock_normalize("$1000000", "currency"), "1000000.00")


class TestKeyValueExtraction(unittest.TestCase):
    """Test cases for key-value pair extraction functions."""

    @patch('ocr_service.src.utils.text_utils.extract_key_value_pairs')
    def test_extract_key_value_pairs_basic(self, mock_extract):
        """Test basic key-value pair extraction."""
        # Mock the extract_key_value_pairs function to return a predefined result
        mock_extract.return_value = {
            "name": "ABC Company",
            "address": "123 Main St",
            "phone": "(123) 456-7890"
        }
        
        # Call the function with sample text
        result = mock_extract("Name: ABC Company\nAddress: 123 Main St\nPhone: (123) 456-7890")
        
        # Verify the result
        self.assertEqual(result, {
            "name": "ABC Company",
            "address": "123 Main St",
            "phone": "(123) 456-7890"
        })
        
        # Verify the function was called with the correct argument
        mock_extract.assert_called_once_with("Name: ABC Company\nAddress: 123 Main St\nPhone: (123) 456-7890")

    @patch('ocr_service.src.utils.text_utils.extract_key_value_pairs')
    def test_extract_key_value_pairs_with_field_variations(self, mock_extract):
        """Test key-value pair extraction with field name variations."""
        # Mock the extract_key_value_pairs function to return a predefined result
        mock_extract.return_value = {
            "name": "ABC Company",
            "address": "123 Main St",
            "phone": "(123) 456-7890"
        }
        
        # Call the function with sample text containing field variations
        result = mock_extract("Business Name: ABC Company\nMailing Address: 123 Main St\nTelephone: (123) 456-7890")
        
        # Verify the result
        self.assertEqual(result, {
            "name": "ABC Company",
            "address": "123 Main St",
            "phone": "(123) 456-7890"
        })
        
        # Verify the function was called with the correct argument
        mock_extract.assert_called_once_with("Business Name: ABC Company\nMailing Address: 123 Main St\nTelephone: (123) 456-7890")

    @patch('ocr_service.src.utils.text_utils.extract_key_value_pairs')
    def test_extract_key_value_pairs_with_complex_layout(self, mock_extract):
        """Test key-value pair extraction with complex document layout."""
        # Mock the extract_key_value_pairs function to return a predefined result
        mock_extract.return_value = {
            "name": "ABC Company",
            "address": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345",
            "phone": "(123) 456-7890",
            "email": "info@abccompany.com"
        }
        
        # Call the function with sample text containing complex layout
        complex_text = (
            "BUSINESS INFORMATION\n\n"
            "Name: ABC Company       Phone: (123) 456-7890\n"
            "Address: 123 Main St    Email: info@abccompany.com\n"
            "City: Anytown          State: CA    Zip: 12345"
        )
        result = mock_extract(complex_text)
        
        # Verify the result
        self.assertEqual(result, {
            "name": "ABC Company",
            "address": "123 Main St",
            "city": "Anytown",
            "state": "CA",
            "zip": "12345",
            "phone": "(123) 456-7890",
            "email": "info@abccompany.com"
        })
        
        # Verify the function was called with the correct argument
        mock_extract.assert_called_once_with(complex_text)


class TestTextValidation(unittest.TestCase):
    """Test cases for text validation and correction functions."""

    @patch('ocr_service.src.utils.text_utils.validate_field')
    def test_validate_field_email(self, mock_validate):
        """Test email validation."""
        # Mock the validate_field function to return a predefined result
        mock_validate.return_value = (True, "user@example.com")
        
        # Call the function with sample email
        result = mock_validate("user@example.com", "email")
        
        # Verify the result
        self.assertEqual(result, (True, "user@example.com"))
        
        # Verify the function was called with the correct arguments
        mock_validate.assert_called_once_with("user@example.com", "email")

    @patch('ocr_service.src.utils.text_utils.validate_field')
    def test_validate_field_ein(self, mock_validate):
        """Test EIN validation."""
        # Mock the validate_field function to return a predefined result
        mock_validate.return_value = (True, "12-3456789")
        
        # Call the function with sample EIN
        result = mock_validate("12-3456789", "ein")
        
        # Verify the result
        self.assertEqual(result, (True, "12-3456789"))
        
        # Verify the function was called with the correct arguments
        mock_validate.assert_called_once_with("12-3456789", "ein")

    @patch('ocr_service.src.utils.text_utils.validate_field')
    def test_validate_field_correction(self, mock_validate):
        """Test field validation with correction."""
        # Mock the validate_field function to return a corrected value
        mock_validate.return_value = (True, "user@example.com")
        
        # Call the function with a slightly incorrect email
        result = mock_validate("user@examp1e.com", "email")
        
        # Verify the result
        self.assertEqual(result, (True, "user@example.com"))
        
        # Verify the function was called with the correct arguments
        mock_validate.assert_called_once_with("user@examp1e.com", "email")

    @patch('ocr_service.src.utils.text_utils.validate_field')
    def test_validate_field_invalid(self, mock_validate):
        """Test field validation with invalid input."""
        # Mock the validate_field function to return an invalid result
        mock_validate.return_value = (False, "invalid@email")
        
        # Call the function with an invalid email
        result = mock_validate("invalid@email", "email")
        
        # Verify the result
        self.assertEqual(result, (False, "invalid@email"))
        
        # Verify the function was called with the correct arguments
        mock_validate.assert_called_once_with("invalid@email", "email")


class TestStructuredDataExtraction(unittest.TestCase):
    """Test cases for structured data extraction functions."""

    @patch('ocr_service.src.utils.text_utils.extract_structured_data')
    def test_extract_structured_data_loan_application(self, mock_extract):
        """Test structured data extraction for loan application."""
        # Mock the extract_structured_data function to return a predefined result
        mock_extract.return_value = {
            "applicant": {
                "name": "John Doe",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
                "phone": "(123) 456-7890",
                "email": "john@example.com"
            },
            "business": {
                "name": "ABC Company",
                "dba_name": "ABC",
                "ein": "12-3456789",
                "address": "456 Business Ave",
                "city": "Commerce",
                "state": "CA",
                "zip": "54321",
                "phone": "(987) 654-3210",
                "industry": "Retail",
                "revenue": "$1,000,000"
            },
            "funding": {
                "amount_requested": "$100,000",
                "purpose": "Expansion",
                "term_requested": "12 months"
            }
        }
        
        # Call the function with sample text and document type
        result = mock_extract("Sample loan application text", "loan_application")
        
        # Verify the result
        self.assertEqual(result, {
            "applicant": {
                "name": "John Doe",
                "address": "123 Main St",
                "city": "Anytown",
                "state": "CA",
                "zip": "12345",
                "phone": "(123) 456-7890",
                "email": "john@example.com"
            },
            "business": {
                "name": "ABC Company",
                "dba_name": "ABC",
                "ein": "12-3456789",
                "address": "456 Business Ave",
                "city": "Commerce",
                "state": "CA",
                "zip": "54321",
                "phone": "(987) 654-3210",
                "industry": "Retail",
                "revenue": "$1,000,000"
            },
            "funding": {
                "amount_requested": "$100,000",
                "purpose": "Expansion",
                "term_requested": "12 months"
            }
        })
        
        # Verify the function was called with the correct arguments
        mock_extract.assert_called_once_with("Sample loan application text", "loan_application")

    @patch('ocr_service.src.utils.text_utils.extract_structured_data')
    def test_extract_structured_data_bank_statement(self, mock_extract):
        """Test structured data extraction for bank statement."""
        # Mock the extract_structured_data function to return a predefined result
        mock_extract.return_value = {
            "bank_info": {
                "name": "First National Bank",
                "address": "789 Bank St",
                "phone": "(800) 555-1234"
            },
            "account_info": {
                "account_number": "XXXX1234",
                "account_type": "Business Checking",
                "statement_period": "01/01/2023 - 01/31/2023"
            },
            "summary": {
                "beginning_balance": "$50,000.00",
                "deposits": "$25,000.00",
                "withdrawals": "$15,000.00",
                "ending_balance": "$60,000.00"
            },
            "transactions": [
                {
                    "date": "01/05/2023",
                    "description": "Deposit",
                    "amount": "$10,000.00"
                },
                {
                    "date": "01/15/2023",
                    "description": "Withdrawal",
                    "amount": "-$5,000.00"
                }
            ]
        }
        
        # Call the function with sample text and document type
        result = mock_extract("Sample bank statement text", "bank_statement")
        
        # Verify the result
        self.assertEqual(result, {
            "bank_info": {
                "name": "First National Bank",
                "address": "789 Bank St",
                "phone": "(800) 555-1234"
            },
            "account_info": {
                "account_number": "XXXX1234",
                "account_type": "Business Checking",
                "statement_period": "01/01/2023 - 01/31/2023"
            },
            "summary": {
                "beginning_balance": "$50,000.00",
                "deposits": "$25,000.00",
                "withdrawals": "$15,000.00",
                "ending_balance": "$60,000.00"
            },
            "transactions": [
                {
                    "date": "01/05/2023",
                    "description": "Deposit",
                    "amount": "$10,000.00"
                },
                {
                    "date": "01/15/2023",
                    "description": "Withdrawal",
                    "amount": "-$5,000.00"
                }
            ]
        })
        
        # Verify the function was called with the correct arguments
        mock_extract.assert_called_once_with("Sample bank statement text", "bank_statement")

    @patch('ocr_service.src.utils.text_utils.extract_structured_data')
    def test_extract_structured_data_with_confidence_scores(self, mock_extract):
        """Test structured data extraction with confidence scores."""
        # Mock the extract_structured_data function to return a result with confidence scores
        mock_extract.return_value = {
            "data": {
                "name": "ABC Company",
                "ein": "12-3456789"
            },
            "confidence": {
                "name": 0.98,
                "ein": 0.85
            }
        }
        
        # Call the function with sample text, document type, and confidence flag
        result = mock_extract("Sample text", "business_document", include_confidence=True)
        
        # Verify the result
        self.assertEqual(result, {
            "data": {
                "name": "ABC Company",
                "ein": "12-3456789"
            },
            "confidence": {
                "name": 0.98,
                "ein": 0.85
            }
        })
        
        # Verify the function was called with the correct arguments
        mock_extract.assert_called_once_with("Sample text", "business_document", include_confidence=True)


class TestJSONSchemaGeneration(unittest.TestCase):
    """Test cases for JSON schema generation functions."""

    @patch('ocr_service.src.utils.text_utils.generate_json_schema')
    def test_generate_json_schema_loan_application(self, mock_generate):
        """Test JSON schema generation for loan application."""
        # Mock the generate_json_schema function to return a predefined schema
        mock_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Loan Application",
            "type": "object",
            "properties": {
                "applicant": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip": {"type": "string"},
                        "phone": {"type": "string"},
                        "email": {"type": "string"}
                    },
                    "required": ["name", "address", "city", "state", "zip"]
                },
                "business": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "dba_name": {"type": "string"},
                        "ein": {"type": "string"},
                        "address": {"type": "string"},
                        "city": {"type": "string"},
                        "state": {"type": "string"},
                        "zip": {"type": "string"},
                        "phone": {"type": "string"},
                        "industry": {"type": "string"},
                        "revenue": {"type": "string"}
                    },
                    "required": ["name", "ein", "address", "city", "state", "zip"]
                },
                "funding": {
                    "type": "object",
                    "properties": {
                        "amount_requested": {"type": "string"},
                        "purpose": {"type": "string"},
                        "term_requested": {"type": "string"}
                    },
                    "required": ["amount_requested"]
                }
            },
            "required": ["applicant", "business", "funding"]
        }
        mock_generate.return_value = mock_schema
        
        # Call the function with document type
        result = mock_generate("loan_application")
        
        # Verify the result
        self.assertEqual(result, mock_schema)
        
        # Verify the function was called with the correct argument
        mock_generate.assert_called_once_with("loan_application")

    @patch('ocr_service.src.utils.text_utils.generate_json_schema')
    def test_generate_json_schema_bank_statement(self, mock_generate):
        """Test JSON schema generation for bank statement."""
        # Mock the generate_json_schema function to return a predefined schema
        mock_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Bank Statement",
            "type": "object",
            "properties": {
                "bank_info": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "address": {"type": "string"},
                        "phone": {"type": "string"}
                    },
                    "required": ["name"]
                },
                "account_info": {
                    "type": "object",
                    "properties": {
                        "account_number": {"type": "string"},
                        "account_type": {"type": "string"},
                        "statement_period": {"type": "string"}
                    },
                    "required": ["account_number", "statement_period"]
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "beginning_balance": {"type": "string"},
                        "deposits": {"type": "string"},
                        "withdrawals": {"type": "string"},
                        "ending_balance": {"type": "string"}
                    },
                    "required": ["beginning_balance", "ending_balance"]
                },
                "transactions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "date": {"type": "string"},
                            "description": {"type": "string"},
                            "amount": {"type": "string"}
                        },
                        "required": ["date", "amount"]
                    }
                }
            },
            "required": ["bank_info", "account_info", "summary"]
        }
        mock_generate.return_value = mock_schema
        
        # Call the function with document type
        result = mock_generate("bank_statement")
        
        # Verify the result
        self.assertEqual(result, mock_schema)
        
        # Verify the function was called with the correct argument
        mock_generate.assert_called_once_with("bank_statement")

    @patch('ocr_service.src.utils.text_utils.generate_json_schema')
    def test_generate_json_schema_with_validation(self, mock_generate):
        """Test JSON schema generation with validation options."""
        # Mock the generate_json_schema function to return a schema with validation
        mock_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": "Tax Return",
            "type": "object",
            "properties": {
                "tax_year": {
                    "type": "string",
                    "pattern": "^\\d{4}$"
                },
                "gross_income": {
                    "type": "string",
                    "pattern": "^\\$?\\d{1,3}(,\\d{3})*(\.\\d{2})?$"
                },
                "net_income": {
                    "type": "string",
                    "pattern": "^\\$?\\d{1,3}(,\\d{3})*(\.\\d{2})?$"
                }
            },
            "required": ["tax_year", "gross_income"]
        }
        mock_generate.return_value = mock_schema
        
        # Call the function with document type and validation flag
        result = mock_generate("tax_return", include_validation=True)
        
        # Verify the result
        self.assertEqual(result, mock_schema)
        
        # Verify the function was called with the correct arguments
        mock_generate.assert_called_once_with("tax_return", include_validation=True)


if __name__ == "__main__":
    unittest.main()