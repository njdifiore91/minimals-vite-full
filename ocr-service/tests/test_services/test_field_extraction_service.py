#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the field extraction service.

This module contains tests for the field extraction service, which is responsible for
extracting structured data from OCR results, identifying key-value pairs, and applying
structure recognition to forms, tables, and document sections.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Tuple

# Import the service and types
from ocr_service.src.services.field_extraction_service import FieldExtractionService
from ocr_service.src.types.documents import DocumentType
from ocr_service.src.types.extraction import (
    ExtractedData, ExtractedField, ConfidenceScore, TableData, FieldLocation,
    ExtractionMetadata, FieldType
)


# ===== Test Setup =====

@pytest.fixture
def field_extraction_service():
    """Create a field extraction service instance for testing."""
    return FieldExtractionService()


@pytest.fixture
def sample_ocr_text():
    """Provide sample OCR text for testing field extraction."""
    return """
MERCHANT CASH ADVANCE APPLICATION

Business Name: Acme Corporation
DBA Name: Acme Corp
Address: 123 Main Street
City: Anytown
State: CA
Zip: 90210
Phone: (555) 123-4567
Email: info@acmecorp.com
Tax ID: 12-3456789
Industry: Retail
Years in Business: 5
Monthly Revenue: $50,000
Requested Amount: $100,000

Owner Information:
Name: John Smith
Title: CEO
Phone: (555) 987-6543
Email: john@acmecorp.com

Signature: John Smith
Date: 01/15/2023
"""


@pytest.fixture
def sample_ocr_text_with_table():
    """Provide sample OCR text with a table for testing table extraction."""
    return """
MONTHLY REVENUE SUMMARY

Business Name: Acme Corporation
Period: January 2023 - March 2023

Month    Revenue    Expenses    Profit
Jan      $50,000    $30,000     $20,000
Feb      $55,000    $32,000     $23,000
Mar      $60,000    $35,000     $25,000
Total    $165,000   $97,000     $68,000

Prepared by: Finance Department
Date: 04/05/2023
"""


@pytest.fixture
def sample_ocr_text_with_errors():
    """Provide sample OCR text with common OCR errors for testing error correction."""
    return """
MERCHANT CASH ADVANCE APPLlCATlON

Business Narne: Acrne Corporation
DBA Narne: Acrne Corp
Address: l23 Main Street
City: Anytown
State: CA
Zip: 9O21O
Phone: (S55) l23-4567
Email: info@acrnecorp.corn
Tax lD: l2-34S6789
Industry: Retall
Years in Business: S
Monthly Revenue: $SO,OOO
Requested Arnount: $lOO,OOO
"""


@pytest.fixture
def sample_bank_statement_text():
    """Provide sample bank statement OCR text for testing document-specific extraction."""
    return """
BANK STATEMENT

Bank Name: First National Bank
Account Holder: Acme Corporation
Account Number: 1234567890
Statement Period: 01/01/2023 - 01/31/2023

Opening Balance: $75,000.00
Closing Balance: $82,500.00

Transactions:
Date        Description                 Amount      Balance
01/03/2023  Deposit                     $15,000.00  $90,000.00
01/10/2023  Withdrawal                  -$5,000.00  $85,000.00
01/15/2023  Vendor Payment              -$7,500.00  $77,500.00
01/25/2023  Customer Payment            $5,000.00   $82,500.00

Total Deposits: $20,000.00
Total Withdrawals: $12,500.00
"""


# ===== Test Cases =====

class TestFieldExtractionService:
    """Test cases for the field extraction service."""

    def test_initialization(self, field_extraction_service):
        """Test that the field extraction service initializes correctly."""
        # Verify that the service has loaded document templates
        assert field_extraction_service.document_templates is not None
        assert len(field_extraction_service.document_templates) > 0
        
        # Verify that field validators are initialized
        assert field_extraction_service.field_validators is not None
        assert len(field_extraction_service.field_validators) > 0

    def test_extract_fields_from_text_application(self, field_extraction_service, sample_ocr_text):
        """Test extracting fields from application form text."""
        # Extract fields from the sample text
        extracted_data = field_extraction_service.extract_fields_from_text(
            sample_ocr_text, DocumentType.APPLICATION
        )
        
        # Verify the extracted data structure
        assert isinstance(extracted_data, ExtractedData)
        assert extracted_data['extraction_id'] is not None
        assert extracted_data['document_type'] == DocumentType.APPLICATION.value
        
        # Verify that key fields were extracted correctly
        fields = extracted_data['fields']
        assert 'business_name' in fields
        assert fields['business_name']['value'] == 'Acme Corporation'
        assert 'tax_id' in fields
        assert fields['tax_id']['value'] == '12-3456789'
        assert 'requested_amount' in fields
        assert fields['requested_amount']['value'] == '$100,000'
        
        # Verify confidence scores
        assert fields['business_name']['confidence'].value >= 0.8
        
        # Verify metadata
        assert extracted_data['metadata']['document_type'] == DocumentType.APPLICATION.value
        assert extracted_data['metadata']['extraction_status'] in ['success', 'partial']

    def test_extract_fields_from_text_bank_statement(self, field_extraction_service, sample_bank_statement_text):
        """Test extracting fields from bank statement text."""
        # Extract fields from the sample text
        extracted_data = field_extraction_service.extract_fields_from_text(
            sample_bank_statement_text, DocumentType.BANK_STATEMENT
        )
        
        # Verify the extracted data structure
        assert isinstance(extracted_data, ExtractedData)
        assert extracted_data['document_type'] == DocumentType.BANK_STATEMENT.value
        
        # Verify that key fields were extracted correctly
        fields = extracted_data['fields']
        assert 'bank_name' in fields
        assert fields['bank_name']['value'] == 'First National Bank'
        assert 'account_holder' in fields
        assert fields['account_holder']['value'] == 'Acme Corporation'
        assert 'account_number' in fields
        # Account number should be masked except last 4 digits
        assert fields['account_number']['value'].endswith('7890')
        assert '*' in fields['account_number']['value']
        assert 'opening_balance' in fields
        assert fields['opening_balance']['value'] == '$75,000.00'
        assert 'closing_balance' in fields
        assert fields['closing_balance']['value'] == '$82,500.00'
        
        # Verify tables were extracted
        tables = extracted_data['tables']
        assert len(tables) > 0
        assert 'Transactions' in [table.get('table_name') for table in tables]

    def test_extract_and_process_tables(self, field_extraction_service, sample_ocr_text_with_table):
        """Test extracting and processing tables from text."""
        # Use the private method to extract tables
        tables = field_extraction_service._extract_and_process_tables(
            sample_ocr_text_with_table, DocumentType.APPLICATION
        )
        
        # Verify that tables were extracted
        assert len(tables) > 0
        
        # Verify the structure of the first table
        table = tables[0]
        assert isinstance(table, TableData)
        assert table['headers'] == ['Month', 'Revenue', 'Expenses', 'Profit']
        assert len(table['rows']) == 4  # 3 months + total
        assert table['row_count'] == 4
        assert table['column_count'] == 4
        
        # Verify the content of the table
        assert table['rows'][0][0] == 'Jan'
        assert table['rows'][0][1] == '$50,000'
        assert table['rows'][3][0] == 'Total'
        assert table['rows'][3][3] == '$68,000'
        
        # Verify field mapping
        assert 'month' in table['field_mapping']
        assert 'revenue' in table['field_mapping']
        assert 'expenses' in table['field_mapping']
        assert 'profit' in table['field_mapping']

    def test_process_extracted_fields(self, field_extraction_service, sample_ocr_text):
        """Test processing extracted key-value pairs into structured fields."""
        # Extract key-value pairs from the sample text
        from ocr_service.src.utils.text_utils import extract_key_value_pairs, extract_sections
        key_value_pairs = extract_key_value_pairs(sample_ocr_text)
        sections = extract_sections(sample_ocr_text)
        
        # Process the extracted fields
        fields = field_extraction_service._process_extracted_fields(
            key_value_pairs, DocumentType.APPLICATION, sections
        )
        
        # Verify that fields were processed correctly
        assert len(fields) > 0
        assert 'business_name' in fields
        assert fields['business_name']['value'] == 'Acme Corporation'
        assert fields['business_name']['field_type'] == FieldType.NAME.value
        
        # Verify field normalization
        assert 'phone' in fields
        assert fields['phone']['value'] == '(555) 123-4567'  # Properly formatted
        
        # Verify field validation
        assert 'email' in fields
        assert fields['email']['value'] == 'info@acmecorp.com'
        assert fields['email']['requires_verification'] is False  # Valid email
        
        # Verify field location
        assert 'location' in fields['business_name']
        assert isinstance(fields['business_name']['location'], FieldLocation)

    def test_error_correction(self, field_extraction_service, sample_ocr_text_with_errors):
        """Test correction of common OCR errors."""
        # Extract fields from the text with errors
        extracted_data = field_extraction_service.extract_fields_from_text(
            sample_ocr_text_with_errors, DocumentType.APPLICATION
        )
        
        # Verify that errors were corrected
        fields = extracted_data['fields']
        
        # Check for common OCR error corrections
        # 'l' (lowercase L) to '1' (one)
        assert 'tax_id' in fields
        assert fields['tax_id']['value'] == '12-3456789'  # Corrected from 'l2-34S6789'
        
        # 'O' (uppercase O) to '0' (zero)
        assert 'zip' in fields
        assert '90210' in fields['zip']['value']  # Corrected from '9O21O'
        
        # 'S' to '5'
        assert 'phone' in fields
        assert '555' in fields['phone']['value']  # Corrected from 'S55'
        
        # Verify confidence scores reflect corrections
        # Confidence should be lower for fields with corrections
        assert fields['tax_id']['confidence'].value < 1.0

    def test_field_validation(self, field_extraction_service):
        """Test validation of different field types."""
        # Test email validation
        valid_email = 'test@example.com'
        invalid_email = 'test@example'
        
        valid_result, valid_confidence, valid_verification = field_extraction_service._validate_email(valid_email)
        invalid_result, invalid_confidence, invalid_verification = field_extraction_service._validate_email(invalid_email)
        
        assert valid_result == valid_email
        assert valid_confidence > 0.8
        assert valid_verification is False
        
        assert invalid_result == invalid_email
        assert invalid_confidence < 0.8
        assert invalid_verification is True
        
        # Test phone validation
        valid_phone = '(555) 123-4567'
        invalid_phone = '555-123-456'
        
        valid_result, valid_confidence, valid_verification = field_extraction_service._validate_phone(valid_phone)
        invalid_result, invalid_confidence, invalid_verification = field_extraction_service._validate_phone(invalid_phone)
        
        assert valid_result == valid_phone
        assert valid_confidence > 0.8
        assert valid_verification is False
        
        assert invalid_result == invalid_phone
        assert invalid_confidence < 0.8
        assert invalid_verification is True
        
        # Test EIN validation
        valid_ein = '12-3456789'
        invalid_ein = '123-45678'
        
        valid_result, valid_confidence, valid_verification = field_extraction_service._validate_ein(valid_ein)
        invalid_result, invalid_confidence, invalid_verification = field_extraction_service._validate_ein(invalid_ein)
        
        assert valid_result == valid_ein
        assert valid_confidence > 0.8
        assert valid_verification is False
        
        assert invalid_result == invalid_ein
        assert invalid_confidence < 0.8
        assert invalid_verification is True

    def test_document_specific_processing(self, field_extraction_service):
        """Test document-specific field processing."""
        # Create sample fields for different document types
        application_fields = {
            'legal_name': ExtractedField(
                field_name='legal_name',
                field_type=FieldType.NAME.value,
                value='acme corporation',  # Lowercase for testing normalization
                raw_text='acme corporation',
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(
                    page=1, top=0.1, left=0.1, bottom=0.15, right=0.5, width=0.4, height=0.05
                ),
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason=None,
                extraction_timestamp='2023-01-01T12:00:00Z'
            ),
            'monthly_revenue': ExtractedField(
                field_name='monthly_revenue',
                field_type=FieldType.CURRENCY.value,
                value='50000',  # No formatting
                raw_text='50000',
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(
                    page=1, top=0.3, left=0.1, bottom=0.35, right=0.5, width=0.4, height=0.05
                ),
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason=None,
                extraction_timestamp='2023-01-01T12:00:00Z'
            )
        }
        
        # Process application fields
        processed_fields = field_extraction_service._process_application_fields(application_fields)
        
        # Verify business name normalization
        assert processed_fields['legal_name']['value'] == 'Acme Corporation'  # Properly capitalized
        
        # Verify currency formatting
        assert processed_fields['monthly_revenue']['value'] == '$50,000.00'  # Properly formatted
        
        # Test bank statement processing
        bank_fields = {
            'account_number': ExtractedField(
                field_name='account_number',
                field_type=FieldType.ACCOUNT_NUMBER.value,
                value='1234567890',  # Full account number
                raw_text='1234567890',
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(
                    page=1, top=0.2, left=0.1, bottom=0.25, right=0.5, width=0.4, height=0.05
                ),
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason=None,
                extraction_timestamp='2023-01-01T12:00:00Z'
            )
        }
        
        # Process bank statement fields
        processed_fields = field_extraction_service._process_bank_statement_fields(bank_fields)
        
        # Verify account number masking
        assert processed_fields['account_number']['value'] == '******7890'  # Masked except last 4

    def test_format_extraction_as_json(self, field_extraction_service, sample_ocr_text):
        """Test formatting extracted data as JSON."""
        # Extract fields from the sample text
        extracted_data = field_extraction_service.extract_fields_from_text(
            sample_ocr_text, DocumentType.APPLICATION
        )
        
        # Format as JSON
        json_data = field_extraction_service.format_extraction_as_json(extracted_data)
        
        # Verify that the result is valid JSON
        parsed_data = json.loads(json_data)
        
        # Verify the structure of the JSON
        assert 'extraction_id' in parsed_data
        assert 'document_type' in parsed_data
        assert 'fields' in parsed_data
        assert 'tables' in parsed_data
        assert 'metadata' in parsed_data
        
        # Verify that fields were properly serialized
        assert 'business_name' in parsed_data['fields']
        assert parsed_data['fields']['business_name']['value'] == 'Acme Corporation'
        
        # Verify that confidence scores were properly serialized as floats
        assert isinstance(parsed_data['fields']['business_name']['confidence'], float)

    def test_identify_field_issues(self, field_extraction_service):
        """Test identification of missing and low confidence fields."""
        # Create sample fields with some missing required fields and low confidence
        fields = {
            'business_name': ExtractedField(
                field_name='business_name',
                field_type=FieldType.NAME.value,
                value='Acme Corporation',
                raw_text='Acme Corporation',
                confidence=ConfidenceScore(0.9),  # High confidence
                location=FieldLocation(
                    page=1, top=0.1, left=0.1, bottom=0.15, right=0.5, width=0.4, height=0.05
                ),
                alternatives=[],
                metadata={},
                requires_verification=False,
                verification_reason=None,
                extraction_timestamp='2023-01-01T12:00:00Z'
            ),
            'phone': ExtractedField(
                field_name='phone',
                field_type=FieldType.PHONE.value,
                value='(555) 123-4567',
                raw_text='(555) 123-4567',
                confidence=ConfidenceScore(0.7),  # Low confidence
                location=FieldLocation(
                    page=1, top=0.2, left=0.1, bottom=0.25, right=0.5, width=0.4, height=0.05
                ),
                alternatives=[],
                metadata={},
                requires_verification=True,
                verification_reason='Low confidence',
                extraction_timestamp='2023-01-01T12:00:00Z'
            )
            # Missing 'legal_name', 'address', 'ein', 'requested_amount'
        }
        
        # Identify missing and low confidence fields
        missing_fields, low_confidence_fields = field_extraction_service._identify_field_issues(
            fields, DocumentType.APPLICATION
        )
        
        # Verify missing required fields
        assert 'legal_name' in missing_fields
        assert 'address' in missing_fields
        assert 'ein' in missing_fields
        assert 'requested_amount' in missing_fields
        
        # Verify low confidence fields
        assert 'phone' in low_confidence_fields
        assert 'business_name' not in low_confidence_fields

    def test_find_section_for_field(self, field_extraction_service, sample_ocr_text):
        """Test finding the document section that contains a field."""
        # Extract sections from the sample text
        from ocr_service.src.utils.text_utils import extract_sections
        sections = extract_sections(sample_ocr_text)
        
        # Find sections for different fields
        business_name_section = field_extraction_service._find_section_for_field('business_name', sections)
        owner_name_section = field_extraction_service._find_section_for_field('owner_name', sections)
        
        # Verify that fields were assigned to the correct sections
        assert business_name_section is not None
        assert 'MERCHANT CASH ADVANCE APPLICATION' in business_name_section
        
        assert owner_name_section is not None
        assert 'Owner Information' in owner_name_section

    def test_determine_table_name(self, field_extraction_service):
        """Test determining a meaningful name for a table based on headers."""
        # Test bank statement transaction table
        bank_headers = ['Date', 'Description', 'Amount', 'Balance']
        bank_table_name = field_extraction_service._determine_table_name(
            bank_headers, DocumentType.BANK_STATEMENT
        )
        assert bank_table_name == 'Transactions'
        
        # Test tax return income table
        tax_headers = ['Source', 'Income', 'Tax Rate']
        tax_table_name = field_extraction_service._determine_table_name(
            tax_headers, DocumentType.TAX_RETURN
        )
        assert tax_table_name == 'Income'
        
        # Test application owners table
        app_headers = ['Owner Name', 'Title', 'Ownership %']
        app_table_name = field_extraction_service._determine_table_name(
            app_headers, DocumentType.APPLICATION
        )
        assert app_table_name == 'Owners'
        
        # Test unknown table
        unknown_headers = ['Column1', 'Column2', 'Column3']
        unknown_table_name = field_extraction_service._determine_table_name(
            unknown_headers, DocumentType.APPLICATION
        )
        assert unknown_table_name is None

    def test_format_helpers(self, field_extraction_service):
        """Test helper methods for formatting different field types."""
        # Test currency formatting
        assert field_extraction_service._format_currency(50000) == '$50,000.00'
        assert field_extraction_service._format_currency('50000') == '$50,000.00'
        assert field_extraction_service._format_currency('$50,000') == '$50,000.00'
        
        # Test phone number formatting
        assert field_extraction_service._format_phone_number('5551234567') == '(555) 123-4567'
        assert field_extraction_service._format_phone_number('(555)123-4567') == '(555) 123-4567'
        assert field_extraction_service._format_phone_number('555-123-4567') == '(555) 123-4567'
        
        # Test EIN formatting
        assert field_extraction_service._format_ein('123456789') == '12-3456789'
        assert field_extraction_service._format_ein('12-3456789') == '12-3456789'
        
        # Test account number masking
        assert field_extraction_service._format_account_number('1234567890') == '******7890'
        assert field_extraction_service._format_account_number('12345') == '12345'  # Short numbers not masked
        
        # Test date formatting
        assert field_extraction_service._format_date('01/15/2023') == '01/15/2023'
        assert field_extraction_service._format_date('2023-01-15') == '01/15/2023'
        assert field_extraction_service._format_date('January 15, 2023') == '01/15/2023'

    def test_validate_extraction_against_schema(self, field_extraction_service, sample_ocr_text):
        """Test validating extracted data against JSON schema."""
        # Extract fields from the sample text
        extracted_data = field_extraction_service.extract_fields_from_text(
            sample_ocr_text, DocumentType.APPLICATION
        )
        
        # Mock the JSONSchemaRegistry.validate_extraction method
        with patch('ocr_service.src.types.extraction.JSONSchemaRegistry.validate_extraction') as mock_validate:
            # Set up the mock to return success
            mock_validate.return_value = (True, [])
            
            # Validate the extraction
            is_valid, errors = field_extraction_service.validate_extraction_against_schema(extracted_data)
            
            # Verify that validation was called with the correct data
            mock_validate.assert_called_once_with(extracted_data)
            
            # Verify the result
            assert is_valid is True
            assert len(errors) == 0
            
            # Reset the mock and set it to return validation errors
            mock_validate.reset_mock()
            mock_validate.return_value = (False, ['Missing required field: tax_id'])
            
            # Validate again
            is_valid, errors = field_extraction_service.validate_extraction_against_schema(extracted_data)
            
            # Verify the result
            assert is_valid is False
            assert len(errors) == 1
            assert 'Missing required field: tax_id' in errors

    def test_edge_cases(self, field_extraction_service):
        """Test handling of edge cases and unusual inputs."""
        # Test with empty text
        empty_data = field_extraction_service.extract_fields_from_text(
            "", DocumentType.APPLICATION
        )
        assert empty_data['fields'] == {}
        assert empty_data['metadata']['extraction_status'] == 'partial'
        
        # Test with very short text
        short_data = field_extraction_service.extract_fields_from_text(
            "Business Name: ABC", DocumentType.APPLICATION
        )
        assert len(short_data['fields']) <= 1
        
        # Test with text in unexpected format
        unusual_data = field_extraction_service.extract_fields_from_text(
            "This is not a standard form format. There are no clear key-value pairs here.",
            DocumentType.APPLICATION
        )
        assert len(unusual_data['fields']) == 0
        assert unusual_data['requires_verification'] is True
        
        # Test with unknown document type
        with pytest.raises(ValueError):
            field_extraction_service.extract_fields_from_text(
                "Business Name: ABC", "UNKNOWN_TYPE"
            )


# Run the tests
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])