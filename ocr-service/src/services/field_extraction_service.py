#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Field Extraction Service for OCR results.

This module provides functionality for extracting structured data from OCR results,
identifying key-value pairs, and applying structure recognition to forms, tables,
and document sections. It transforms raw OCR text into structured JSON data for
downstream processing.
"""

import logging
import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from uuid import uuid4

import numpy as np

from ..config import app_config
from ..types.extraction import (
    ConfidenceScore,
    ExtractedData,
    ExtractedField,
    TableData,
    FieldLocation,
    ExtractionMetadata,
    JSONSchema,
    JSONSchemaRegistry,
    FieldType
)
from ..types.documents import DocumentType, Document
from ..utils.text_utils import (
    clean_text,
    normalize_text,
    correct_ocr_errors,
    extract_key_value_pairs,
    normalize_key,
    extract_tables,
    extract_sections,
    validate_field,
    normalize_business_terms,
    DOCUMENT_TYPE_FIELDS
)
from ..utils.logging_utils import get_logger


class FieldExtractionService:
    """Service for extracting structured data from OCR results.
    
    This service is responsible for:
    1. Extracting key-value pairs from OCR text
    2. Recognizing document structure (forms, tables, sections)
    3. Applying document type-specific extraction rules
    4. Normalizing and standardizing extracted fields
    5. Formatting data as structured JSON
    6. Validating and correcting extracted fields
    
    Attributes:
        logger: Logger instance for this service
        config: Application configuration
        document_templates: Templates for different document types
        field_validators: Validation rules for different field types
    """
    
    def __init__(self):
        """Initialize the FieldExtractionService with configuration settings."""
        self.logger = get_logger(__name__)
        self.config = app_config
        
        # Load document templates from configuration
        self.document_templates = self._load_document_templates()
        
        # Initialize field validators
        self.field_validators = self._initialize_field_validators()
        
        self.logger.info("FieldExtractionService initialized with %d document templates", 
                         len(self.document_templates))
    
    def _load_document_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load document templates for different document types.
        
        Templates define expected fields, their positions, and validation rules
        for different document types.
        
        Returns:
            Dictionary mapping document types to their templates
        """
        # Default templates if not specified in config
        default_templates = {
            DocumentType.APPLICATION.value: {
                "expected_fields": DOCUMENT_TYPE_FIELDS[DocumentType.APPLICATION],
                "required_fields": [
                    "legal_name", "address", "phone", "ein", "requested_amount"
                ],
                "field_types": {
                    "legal_name": FieldType.NAME.value,
                    "dba_name": FieldType.NAME.value,
                    "address": FieldType.ADDRESS.value,
                    "phone": FieldType.PHONE.value,
                    "email": FieldType.EMAIL.value,
                    "ein": FieldType.EIN.value,
                    "industry": FieldType.TEXT.value,
                    "years_in_business": FieldType.NUMBER.value,
                    "monthly_revenue": FieldType.CURRENCY.value,
                    "requested_amount": FieldType.CURRENCY.value
                }
            },
            DocumentType.TAX_RETURN.value: {
                "expected_fields": DOCUMENT_TYPE_FIELDS[DocumentType.TAX_RETURN],
                "required_fields": [
                    "tax_year", "business_name", "ein", "gross_receipts", "total_income"
                ],
                "field_types": {
                    "tax_year": FieldType.TEXT.value,
                    "business_name": FieldType.NAME.value,
                    "ein": FieldType.EIN.value,
                    "gross_receipts": FieldType.CURRENCY.value,
                    "total_income": FieldType.CURRENCY.value,
                    "total_deductions": FieldType.CURRENCY.value,
                    "taxable_income": FieldType.CURRENCY.value,
                    "total_tax": FieldType.CURRENCY.value
                }
            },
            DocumentType.BANK_STATEMENT.value: {
                "expected_fields": DOCUMENT_TYPE_FIELDS[DocumentType.BANK_STATEMENT],
                "required_fields": [
                    "bank_name", "account_holder", "account_number", "statement_period", 
                    "opening_balance", "closing_balance"
                ],
                "field_types": {
                    "bank_name": FieldType.NAME.value,
                    "account_holder": FieldType.NAME.value,
                    "account_number": FieldType.ACCOUNT_NUMBER.value,
                    "statement_period": FieldType.DATE.value,
                    "opening_balance": FieldType.CURRENCY.value,
                    "closing_balance": FieldType.CURRENCY.value,
                    "total_deposits": FieldType.CURRENCY.value,
                    "total_withdrawals": FieldType.CURRENCY.value
                }
            },
            DocumentType.PAY_STUB.value: {
                "expected_fields": DOCUMENT_TYPE_FIELDS[DocumentType.PAY_STUB],
                "required_fields": [
                    "employer_name", "employee_name", "pay_period", "pay_date", 
                    "gross_pay", "net_pay"
                ],
                "field_types": {
                    "employer_name": FieldType.NAME.value,
                    "employee_name": FieldType.NAME.value,
                    "pay_period": FieldType.DATE.value,
                    "pay_date": FieldType.DATE.value,
                    "gross_pay": FieldType.CURRENCY.value,
                    "net_pay": FieldType.CURRENCY.value,
                    "ytd_gross": FieldType.CURRENCY.value,
                    "ytd_net": FieldType.CURRENCY.value
                }
            },
            DocumentType.ID_DOCUMENT.value: {
                "expected_fields": DOCUMENT_TYPE_FIELDS[DocumentType.ID_DOCUMENT],
                "required_fields": [
                    "document_type", "id_number", "full_name", "date_of_birth"
                ],
                "field_types": {
                    "document_type": FieldType.TEXT.value,
                    "id_number": FieldType.TEXT.value,
                    "full_name": FieldType.NAME.value,
                    "address": FieldType.ADDRESS.value,
                    "date_of_birth": FieldType.DATE.value,
                    "issue_date": FieldType.DATE.value,
                    "expiration_date": FieldType.DATE.value
                }
            }
        }
        
        # Try to load from config, fall back to defaults if not found
        try:
            templates = getattr(self.config, 'document_templates', None)
            if not templates:
                return default_templates
            return templates
        except (AttributeError, KeyError):
            self.logger.warning("Document templates not found in config, using defaults")
            return default_templates
    
    def _initialize_field_validators(self) -> Dict[str, callable]:
        """Initialize field validators for different field types.
        
        Returns:
            Dictionary mapping field types to validator functions
        """
        return {
            FieldType.EMAIL.value: self._validate_email,
            FieldType.PHONE.value: self._validate_phone,
            FieldType.DATE.value: self._validate_date,
            FieldType.CURRENCY.value: self._validate_currency,
            FieldType.PERCENTAGE.value: self._validate_percentage,
            FieldType.NAME.value: self._validate_name,
            FieldType.ADDRESS.value: self._validate_address,
            FieldType.EIN.value: self._validate_ein,
            FieldType.SSN.value: self._validate_ssn,
            FieldType.ACCOUNT_NUMBER.value: self._validate_account_number,
            FieldType.NUMBER.value: self._validate_number,
            FieldType.CHECKBOX.value: self._validate_checkbox,
            FieldType.TEXT.value: self._validate_text  # Default validator
        }
    
    def extract_fields_from_text(self, text: str, document_type: DocumentType) -> ExtractedData:
        """Extract structured fields from OCR text based on document type.
        
        This is the main entry point for field extraction, which orchestrates the
        extraction process based on document type and structure.
        
        Args:
            text: Raw OCR text to process
            document_type: Type of document for specialized extraction
            
        Returns:
            ExtractedData object containing structured fields and metadata
        """
        self.logger.info("Extracting fields from %s document", document_type.value)
        
        # Clean and normalize the text
        cleaned_text = clean_text(text)
        
        # Extract document sections for context
        sections = extract_sections(cleaned_text)
        
        # Extract tables from the document
        tables = self._extract_and_process_tables(cleaned_text, document_type)
        
        # Extract key-value pairs from the text
        key_value_pairs = extract_key_value_pairs(cleaned_text)
        
        # Process extracted fields based on document type
        fields = self._process_extracted_fields(key_value_pairs, document_type, sections)
        
        # Create extraction metadata
        extraction_id = str(uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Identify missing and low confidence fields
        missing_fields, low_confidence_fields = self._identify_field_issues(fields, document_type)
        
        # Determine if verification is needed
        requires_verification = len(low_confidence_fields) > 0 or len(missing_fields) > 0
        
        # Create the extraction metadata
        metadata = ExtractionMetadata(
            extraction_id=extraction_id,
            document_id="",  # Will be filled by the calling service
            model_id="",  # Will be filled by the calling service
            model_version="",  # Will be filled by the calling service
            document_type=document_type.value,
            page_count=1,  # Will be updated by the calling service
            language="en",  # Default language
            processing_node="",  # Will be filled by the calling service
            extraction_status="success" if not missing_fields else "partial",
            processing_time=0.0,  # Will be updated by the calling service
            warnings=[f"Missing required field: {field}" for field in missing_fields],
            errors=[]
        )
        
        # Create the extracted data
        extracted_data = ExtractedData(
            extraction_id=extraction_id,
            fields=fields,
            tables=tables,
            metadata=metadata,
            raw_text=cleaned_text,
            low_confidence_fields=low_confidence_fields,
            requires_verification=requires_verification,
            extraction_timestamp=timestamp,
            schema_version="1.0",
            document_type=document_type.value
        )
        
        self.logger.info(
            "Extraction completed: %d fields, %d tables, %d missing fields, %d low confidence fields",
            len(fields), len(tables), len(missing_fields), len(low_confidence_fields)
        )
        
        return extracted_data
    
    def _process_extracted_fields(
        self, key_value_pairs: List[Tuple[str, str, float]], 
        document_type: DocumentType,
        sections: Dict[str, str]
    ) -> Dict[str, ExtractedField]:
        """Process extracted key-value pairs into structured fields.
        
        Args:
            key_value_pairs: List of (key, value, confidence) tuples
            document_type: Type of document for specialized processing
            sections: Dictionary of document sections for context
            
        Returns:
            Dictionary of field names to ExtractedField objects
        """
        fields = {}
        template = self.document_templates.get(document_type.value, {})
        expected_field_types = template.get("field_types", {})
        
        # Process each key-value pair
        for key, value, confidence in key_value_pairs:
            # Skip empty values
            if not value.strip():
                continue
            
            # Normalize the key
            normalized_key = normalize_key(key)
            
            # Determine field type
            field_type = expected_field_types.get(normalized_key, FieldType.TEXT.value)
            
            # Validate and normalize the value based on field type
            processed_value, validation_confidence, requires_verification = self._validate_field(
                value, field_type
            )
            
            # Combine extraction and validation confidence
            combined_confidence = confidence * validation_confidence
            
            # Create field location (placeholder - would be populated by OCR service)
            field_location = FieldLocation(
                page=1,
                top=0.0,
                left=0.0,
                bottom=0.0,
                right=0.0,
                width=0.0,
                height=0.0
            )
            
            # Create the extracted field
            field = ExtractedField(
                field_name=normalized_key,
                field_type=field_type,
                value=processed_value,
                raw_text=value,
                confidence=ConfidenceScore(combined_confidence),
                location=field_location,
                alternatives=[],  # Could be populated with alternative values
                metadata={
                    "section": self._find_section_for_field(normalized_key, sections),
                    "original_key": key,
                    "validation_confidence": validation_confidence
                },
                requires_verification=requires_verification,
                verification_reason="Low confidence" if combined_confidence < 0.8 else None,
                extraction_timestamp=datetime.utcnow().isoformat()
            )
            
            fields[normalized_key] = field
        
        # Apply document-specific field processing
        fields = self._apply_document_specific_processing(fields, document_type)
        
        return fields
    
    def _extract_and_process_tables(self, text: str, document_type: DocumentType) -> List[TableData]:
        """Extract and process tables from document text.
        
        Args:
            text: Document text to process
            document_type: Type of document for specialized processing
            
        Returns:
            List of TableData objects
        """
        # Extract raw tables
        raw_tables = extract_tables(text)
        processed_tables = []
        
        for i, raw_table in enumerate(raw_tables):
            # Create a unique ID for the table
            table_id = f"table_{i+1}"
            
            # Extract headers and rows
            headers = raw_table.get("headers", [])
            rows = raw_table.get("rows", [])
            
            # Skip empty tables
            if not headers or not rows:
                continue
            
            # Create field mapping (header name to column index)
            field_mapping = {header.lower().replace(' ', '_'): i for i, header in enumerate(headers)}
            
            # Calculate confidence score for the table
            # This is a simplified approach - in a real implementation, you would use
            # more sophisticated methods to evaluate table extraction quality
            confidence = 0.9  # Default high confidence for tables
            
            # Create the table data
            table_data = TableData(
                table_id=table_id,
                table_name=self._determine_table_name(headers, document_type),
                headers=headers,
                rows=rows,
                header_row_index=0,
                field_mapping=field_mapping,
                row_count=len(rows),
                column_count=len(headers),
                confidence=ConfidenceScore(confidence),
                is_complete=True,  # Assume complete unless determined otherwise
                metadata={
                    "document_type": document_type.value,
                    "extraction_timestamp": datetime.utcnow().isoformat()
                }
            )
            
            processed_tables.append(table_data)
        
        return processed_tables
    
    def _determine_table_name(self, headers: List[str], document_type: DocumentType) -> Optional[str]:
        """Determine a meaningful name for a table based on its headers and document type.
        
        Args:
            headers: Table headers
            document_type: Type of document
            
        Returns:
            Table name or None if no specific name can be determined
        """
        # Convert headers to lowercase for case-insensitive matching
        headers_lower = [h.lower() for h in headers]
        
        # Bank statement tables
        if document_type == DocumentType.BANK_STATEMENT:
            if any("date" in h for h in headers_lower) and any("amount" in h for h in headers_lower):
                return "Transactions"
            if any("deposit" in h for h in headers_lower):
                return "Deposits"
            if any("withdrawal" in h for h in headers_lower):
                return "Withdrawals"
        
        # Tax return tables
        elif document_type == DocumentType.TAX_RETURN:
            if any("income" in h for h in headers_lower):
                return "Income"
            if any("deduction" in h for h in headers_lower):
                return "Deductions"
            if any("expense" in h for h in headers_lower):
                return "Expenses"
        
        # Application tables
        elif document_type == DocumentType.APPLICATION:
            if any("owner" in h for h in headers_lower):
                return "Owners"
            if any("reference" in h for h in headers_lower):
                return "References"
        
        # Default: no specific name determined
        return None
    
    def _find_section_for_field(self, field_name: str, sections: Dict[str, str]) -> Optional[str]:
        """Find the document section that contains a field.
        
        Args:
            field_name: Name of the field to locate
            sections: Dictionary of document sections
            
        Returns:
            Section name or None if not found in any specific section
        """
        # Convert field name to a pattern that might appear in the text
        # Replace underscores with spaces and compile a case-insensitive regex
        field_pattern = re.compile(
            r'\b' + field_name.replace('_', ' ') + r'\b', 
            re.IGNORECASE
        )
        
        for section_name, section_text in sections.items():
            if field_pattern.search(section_text):
                return section_name
        
        return None
    
    def _identify_field_issues(
        self, fields: Dict[str, ExtractedField], document_type: DocumentType
    ) -> Tuple[List[str], List[str]]:
        """Identify missing required fields and low confidence fields.
        
        Args:
            fields: Dictionary of extracted fields
            document_type: Type of document
            
        Returns:
            Tuple of (missing_fields, low_confidence_fields)
        """
        template = self.document_templates.get(document_type.value, {})
        required_fields = template.get("required_fields", [])
        
        # Identify missing required fields
        missing_fields = [field for field in required_fields if field not in fields]
        
        # Identify low confidence fields
        low_confidence_fields = [
            field_name for field_name, field in fields.items()
            if field.confidence.value < 0.8
        ]
        
        return missing_fields, low_confidence_fields
    
    def _apply_document_specific_processing(
        self, fields: Dict[str, ExtractedField], document_type: DocumentType
    ) -> Dict[str, ExtractedField]:
        """Apply document-specific processing rules to extracted fields.
        
        Args:
            fields: Dictionary of extracted fields
            document_type: Type of document
            
        Returns:
            Processed fields dictionary
        """
        # Apply document-specific processing based on document type
        if document_type == DocumentType.APPLICATION:
            return self._process_application_fields(fields)
        elif document_type == DocumentType.TAX_RETURN:
            return self._process_tax_return_fields(fields)
        elif document_type == DocumentType.BANK_STATEMENT:
            return self._process_bank_statement_fields(fields)
        elif document_type == DocumentType.PAY_STUB:
            return self._process_pay_stub_fields(fields)
        elif document_type == DocumentType.ID_DOCUMENT:
            return self._process_id_document_fields(fields)
        else:
            # Default processing for other document types
            return fields
    
    def _process_application_fields(
        self, fields: Dict[str, ExtractedField]
    ) -> Dict[str, ExtractedField]:
        """Process fields specific to application forms.
        
        Args:
            fields: Dictionary of extracted fields
            
        Returns:
            Processed fields dictionary
        """
        # Normalize business names
        if 'legal_name' in fields:
            fields['legal_name'].value = normalize_business_terms(fields['legal_name'].value)
        
        if 'dba_name' in fields:
            fields['dba_name'].value = normalize_business_terms(fields['dba_name'].value)
        
        # Format currency fields
        currency_fields = ['monthly_revenue', 'requested_amount']
        for field_name in currency_fields:
            if field_name in fields:
                fields[field_name].value = self._format_currency(fields[field_name].value)
        
        # Format phone numbers
        if 'phone' in fields:
            fields['phone'].value = self._format_phone_number(fields['phone'].value)
        
        # Format EIN
        if 'ein' in fields:
            fields['ein'].value = self._format_ein(fields['ein'].value)
        
        return fields
    
    def _process_tax_return_fields(
        self, fields: Dict[str, ExtractedField]
    ) -> Dict[str, ExtractedField]:
        """Process fields specific to tax return documents.
        
        Args:
            fields: Dictionary of extracted fields
            
        Returns:
            Processed fields dictionary
        """
        # Normalize business name
        if 'business_name' in fields:
            fields['business_name'].value = normalize_business_terms(fields['business_name'].value)
        
        # Format currency fields
        currency_fields = ['gross_receipts', 'total_income', 'total_deductions', 
                          'taxable_income', 'total_tax']
        for field_name in currency_fields:
            if field_name in fields:
                fields[field_name].value = self._format_currency(fields[field_name].value)
        
        # Format EIN
        if 'ein' in fields:
            fields['ein'].value = self._format_ein(fields['ein'].value)
        
        # Format tax year
        if 'tax_year' in fields:
            fields['tax_year'].value = self._format_tax_year(fields['tax_year'].value)
        
        return fields
    
    def _process_bank_statement_fields(
        self, fields: Dict[str, ExtractedField]
    ) -> Dict[str, ExtractedField]:
        """Process fields specific to bank statement documents.
        
        Args:
            fields: Dictionary of extracted fields
            
        Returns:
            Processed fields dictionary
        """
        # Normalize bank name
        if 'bank_name' in fields:
            fields['bank_name'].value = normalize_business_terms(fields['bank_name'].value)
        
        # Normalize account holder name
        if 'account_holder' in fields:
            fields['account_holder'].value = normalize_business_terms(fields['account_holder'].value)
        
        # Format currency fields
        currency_fields = ['opening_balance', 'closing_balance', 
                          'total_deposits', 'total_withdrawals']
        for field_name in currency_fields:
            if field_name in fields:
                fields[field_name].value = self._format_currency(fields[field_name].value)
        
        # Format account number (mask except last 4 digits)
        if 'account_number' in fields:
            fields['account_number'].value = self._mask_account_number(fields['account_number'].value)
        
        # Format statement period
        if 'statement_period' in fields:
            fields['statement_period'].value = self._format_date_range(fields['statement_period'].value)
        
        return fields
    
    def _process_pay_stub_fields(
        self, fields: Dict[str, ExtractedField]
    ) -> Dict[str, ExtractedField]:
        """Process fields specific to pay stub documents.
        
        Args:
            fields: Dictionary of extracted fields
            
        Returns:
            Processed fields dictionary
        """
        # Normalize employer name
        if 'employer_name' in fields:
            fields['employer_name'].value = normalize_business_terms(fields['employer_name'].value)
        
        # Format currency fields
        currency_fields = ['gross_pay', 'net_pay', 'ytd_gross', 'ytd_net']
        for field_name in currency_fields:
            if field_name in fields:
                fields[field_name].value = self._format_currency(fields[field_name].value)
        
        # Format dates
        date_fields = ['pay_date']
        for field_name in date_fields:
            if field_name in fields:
                fields[field_name].value = self._format_date(fields[field_name].value)
        
        # Format pay period
        if 'pay_period' in fields:
            fields['pay_period'].value = self._format_date_range(fields['pay_period'].value)
        
        return fields
    
    def _process_id_document_fields(
        self, fields: Dict[str, ExtractedField]
    ) -> Dict[str, ExtractedField]:
        """Process fields specific to ID documents.
        
        Args:
            fields: Dictionary of extracted fields
            
        Returns:
            Processed fields dictionary
        """
        # Format dates
        date_fields = ['date_of_birth', 'issue_date', 'expiration_date']
        for field_name in date_fields:
            if field_name in fields:
                fields[field_name].value = self._format_date(fields[field_name].value)
        
        return fields
    
    def _validate_field(
        self, value: str, field_type: str
    ) -> Tuple[Any, float, bool]:
        """Validate and normalize a field value based on its type.
        
        Args:
            value: Raw field value to validate
            field_type: Type of field
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Get the appropriate validator for this field type
        validator = self.field_validators.get(field_type, self._validate_text)
        
        # Apply the validator
        return validator(value)
    
    def _validate_email(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize an email address.
        
        Args:
            value: Email address to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply email-specific corrections
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'email')
        
        # Check if it matches a valid email pattern
        email_pattern = re.compile(r'^[\w\.-]+@([\w\-]+\.)+[A-Za-z]{2,}$')
        is_valid = bool(email_pattern.match(corrected_value))
        
        # Emails with low confidence or invalid format require verification
        requires_verification = not is_valid or confidence < 0.8
        
        return corrected_value, confidence, requires_verification
    
    def _validate_phone(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize a phone number.
        
        Args:
            value: Phone number to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply phone-specific corrections
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'phone')
        
        # Format as a standard phone number
        formatted_value = self._format_phone_number(corrected_value)
        
        # Check if it matches a valid phone pattern after formatting
        phone_pattern = re.compile(r'^\(\d{3}\) \d{3}-\d{4}$')
        is_valid = bool(phone_pattern.match(formatted_value))
        
        # Phone numbers with low confidence or invalid format require verification
        requires_verification = not is_valid or confidence < 0.8
        
        return formatted_value, confidence, requires_verification
    
    def _validate_date(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize a date.
        
        Args:
            value: Date to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply date-specific corrections
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'date')
        
        # Format as a standard date
        formatted_value = self._format_date(corrected_value)
        
        # Check if formatting was successful
        is_valid = formatted_value != corrected_value
        
        # Dates with low confidence or invalid format require verification
        requires_verification = not is_valid or confidence < 0.8
        
        return formatted_value, confidence, requires_verification
    
    def _validate_currency(self, value: str) -> Tuple[float, float, bool]:
        """Validate and normalize a currency value.
        
        Args:
            value: Currency value to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply currency-specific corrections
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'currency')
        
        try:
            # Remove currency symbols and commas
            numeric_string = corrected_value.replace('$', '').replace(',', '').strip()
            
            # Convert to float
            numeric_value = float(numeric_string)
            
            # Currency values with low confidence require verification
            requires_verification = confidence < 0.8
            
            return numeric_value, confidence, requires_verification
        except ValueError:
            # If conversion fails, return 0.0 with low confidence
            return 0.0, 0.5, True
    
    def _validate_percentage(self, value: str) -> Tuple[float, float, bool]:
        """Validate and normalize a percentage value.
        
        Args:
            value: Percentage value to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Remove percentage symbol
        cleaned_value = cleaned_value.replace('%', '').strip()
        
        try:
            # Convert to float
            numeric_value = float(cleaned_value) / 100.0  # Convert to decimal
            
            # Use high confidence for successful conversion
            confidence = 0.9
            requires_verification = False
            
            return numeric_value, confidence, requires_verification
        except ValueError:
            # If conversion fails, return 0.0 with low confidence
            return 0.0, 0.5, True
    
    def _validate_name(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize a name.
        
        Args:
            value: Name to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply business term normalization
        normalized_value = normalize_business_terms(cleaned_value)
        
        # Names with very short length might be incomplete
        is_valid = len(normalized_value) >= 3
        
        # Use high confidence for valid names
        confidence = 0.9 if is_valid else 0.7
        
        # Names that are too short require verification
        requires_verification = not is_valid
        
        return normalized_value, confidence, requires_verification
    
    def _validate_address(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize an address.
        
        Args:
            value: Address to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Addresses with very short length might be incomplete
        is_valid = len(cleaned_value) >= 10
        
        # Use high confidence for valid addresses
        confidence = 0.9 if is_valid else 0.7
        
        # Addresses that are too short require verification
        requires_verification = not is_valid
        
        return cleaned_value, confidence, requires_verification
    
    def _validate_ein(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize an EIN.
        
        Args:
            value: EIN to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply EIN-specific corrections
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'ein')
        
        # Format as a standard EIN
        formatted_value = self._format_ein(corrected_value)
        
        # Check if it matches a valid EIN pattern
        ein_pattern = re.compile(r'^\d{2}-\d{7}$')
        is_valid = bool(ein_pattern.match(formatted_value))
        
        # EINs with low confidence or invalid format require verification
        requires_verification = not is_valid or confidence < 0.8
        
        return formatted_value, confidence, requires_verification
    
    def _validate_ssn(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize an SSN.
        
        Args:
            value: SSN to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Apply SSN-specific corrections
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'ssn')
        
        # Format as a standard SSN
        formatted_value = self._format_ssn(corrected_value)
        
        # Check if it matches a valid SSN pattern
        ssn_pattern = re.compile(r'^\d{3}-\d{2}-\d{4}$')
        is_valid = bool(ssn_pattern.match(formatted_value))
        
        # SSNs with low confidence or invalid format require verification
        requires_verification = not is_valid or confidence < 0.8
        
        return formatted_value, confidence, requires_verification
    
    def _validate_account_number(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize an account number.
        
        Args:
            value: Account number to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Remove all non-numeric characters
        numeric_only = re.sub(r'[^0-9]', '', cleaned_value)
        
        # Account numbers should have a reasonable length
        is_valid = 4 <= len(numeric_only) <= 17
        
        # Use high confidence for valid account numbers
        confidence = 0.9 if is_valid else 0.7
        
        # Account numbers with invalid length require verification
        requires_verification = not is_valid
        
        # Mask the account number for security
        masked_value = self._mask_account_number(numeric_only)
        
        return masked_value, confidence, requires_verification
    
    def _validate_number(self, value: str) -> Tuple[float, float, bool]:
        """Validate and normalize a numeric value.
        
        Args:
            value: Numeric value to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Remove all non-numeric characters except decimal point
        numeric_string = re.sub(r'[^0-9\.]', '', cleaned_value)
        
        try:
            # Convert to float
            numeric_value = float(numeric_string)
            
            # Use high confidence for successful conversion
            confidence = 0.9
            requires_verification = False
            
            return numeric_value, confidence, requires_verification
        except ValueError:
            # If conversion fails, return 0.0 with low confidence
            return 0.0, 0.5, True
    
    def _validate_checkbox(self, value: str) -> Tuple[bool, float, bool]:
        """Validate and normalize a checkbox value.
        
        Args:
            value: Checkbox value to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value).lower()
        
        # Check for positive indicators
        positive_indicators = ['x', 'yes', 'y', 'true', 't', 'checked', 'selected', '✓', '✔']
        is_checked = any(indicator in cleaned_value for indicator in positive_indicators)
        
        # Use high confidence for clear indicators
        confidence = 0.9 if any(indicator == cleaned_value for indicator in positive_indicators) else 0.7
        
        # Ambiguous checkbox values require verification
        requires_verification = confidence < 0.8
        
        return is_checked, confidence, requires_verification
    
    def _validate_text(self, value: str) -> Tuple[str, float, bool]:
        """Validate and normalize a text value.
        
        This is the default validator for fields without a specific type.
        
        Args:
            value: Text value to validate
            
        Returns:
            Tuple of (processed_value, confidence_score, requires_verification)
        """
        # Clean and normalize the value
        cleaned_value = clean_text(value)
        
        # Use high confidence for non-empty text
        confidence = 0.9 if cleaned_value else 0.5
        
        # Empty text requires verification
        requires_verification = not cleaned_value
        
        return cleaned_value, confidence, requires_verification
    
    def _format_currency(self, value: Any) -> str:
        """Format a value as currency.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted currency string
        """
        if isinstance(value, str):
            # Remove currency symbols and commas
            numeric_string = value.replace('$', '').replace(',', '').strip()
            try:
                value = float(numeric_string)
            except ValueError:
                return value  # Return original if conversion fails
        
        if isinstance(value, (int, float)):
            return f"${value:,.2f}"
        
        return str(value)  # Fallback for other types
    
    def _format_phone_number(self, value: str) -> str:
        """Format a value as a phone number.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted phone number string
        """
        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', value)
        
        # Handle different phone number lengths
        if len(digits) == 10:  # Standard US phone number
            return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':  # US phone with country code
            return f"({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        else:
            # Return original if format is unclear
            return value
    
    def _format_ein(self, value: str) -> str:
        """Format a value as an EIN.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted EIN string
        """
        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', value)
        
        # EIN format: XX-XXXXXXX
        if len(digits) == 9:
            return f"{digits[0:2]}-{digits[2:]}"
        else:
            # Return original if format is unclear
            return value
    
    def _format_ssn(self, value: str) -> str:
        """Format a value as an SSN.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted SSN string
        """
        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', value)
        
        # SSN format: XXX-XX-XXXX
        if len(digits) == 9:
            return f"{digits[0:3]}-{digits[3:5]}-{digits[5:]}"
        else:
            # Return original if format is unclear
            return value
    
    def _mask_account_number(self, value: str) -> str:
        """Mask an account number for security.
        
        Args:
            value: Account number to mask
            
        Returns:
            Masked account number string
        """
        # Remove all non-numeric characters
        digits = re.sub(r'\D', '', value)
        
        # Mask all but the last 4 digits
        if len(digits) > 4:
            return f"{'*' * (len(digits) - 4)}{digits[-4:]}"
        else:
            # If less than 4 digits, return as is
            return digits
    
    def _format_date(self, value: str) -> str:
        """Format a value as a date.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted date string
        """
        # Common date patterns
        date_patterns = [
            # MM/DD/YYYY
            (re.compile(r'^(\d{1,2})/(\d{1,2})/(\d{2,4})$'), 
             lambda m: f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{int(m.group(3)):04d}"),
            # MM-DD-YYYY
            (re.compile(r'^(\d{1,2})-(\d{1,2})-(\d{2,4})$'), 
             lambda m: f"{int(m.group(1)):02d}/{int(m.group(2)):02d}/{int(m.group(3)):04d}"),
            # YYYY/MM/DD
            (re.compile(r'^(\d{4})/(\d{1,2})/(\d{1,2})$'), 
             lambda m: f"{int(m.group(2)):02d}/{int(m.group(3)):02d}/{int(m.group(1)):04d}"),
            # YYYY-MM-DD
            (re.compile(r'^(\d{4})-(\d{1,2})-(\d{1,2})$'), 
             lambda m: f"{int(m.group(2)):02d}/{int(m.group(3)):02d}/{int(m.group(1)):04d}"),
            # Month DD, YYYY
            (re.compile(r'^([A-Za-z]{3,9})\s+(\d{1,2}),?\s+(\d{2,4})$'), 
             lambda m: f"{self._month_to_number(m.group(1)):02d}/{int(m.group(2)):02d}/{int(m.group(3)):04d}")
        ]
        
        # Try each pattern
        for pattern, formatter in date_patterns:
            match = pattern.match(value)
            if match:
                try:
                    return formatter(match)
                except (ValueError, IndexError):
                    continue
        
        # Return original if no pattern matches
        return value
    
    def _format_date_range(self, value: str) -> str:
        """Format a value as a date range.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted date range string
        """
        # Look for common date range separators
        separators = [' to ', ' - ', ' through ', '–', '—']
        
        for separator in separators:
            if separator in value:
                parts = value.split(separator, 1)
                if len(parts) == 2:
                    start_date = self._format_date(parts[0].strip())
                    end_date = self._format_date(parts[1].strip())
                    return f"{start_date} - {end_date}"
        
        # If no range separator found, try to format as a single date
        return self._format_date(value)
    
    def _format_tax_year(self, value: str) -> str:
        """Format a value as a tax year.
        
        Args:
            value: Value to format
            
        Returns:
            Formatted tax year string
        """
        # Extract year from various formats
        year_pattern = re.compile(r'\b(19|20)\d{2}\b')
        match = year_pattern.search(value)
        
        if match:
            return match.group(0)  # Return the 4-digit year
        else:
            # Return original if no year found
            return value
    
    def _month_to_number(self, month_name: str) -> int:
        """Convert a month name to its numeric value.
        
        Args:
            month_name: Month name to convert
            
        Returns:
            Month number (1-12)
        """
        month_map = {
            'jan': 1, 'january': 1,
            'feb': 2, 'february': 2,
            'mar': 3, 'march': 3,
            'apr': 4, 'april': 4,
            'may': 5,
            'jun': 6, 'june': 6,
            'jul': 7, 'july': 7,
            'aug': 8, 'august': 8,
            'sep': 9, 'september': 9,
            'oct': 10, 'october': 10,
            'nov': 11, 'november': 11,
            'dec': 12, 'december': 12
        }
        
        return month_map.get(month_name.lower()[:3], 1)  # Default to January if not found
    
    def format_extraction_as_json(self, extracted_data: ExtractedData) -> str:
        """Format extracted data as a JSON string.
        
        Args:
            extracted_data: ExtractedData object to format
            
        Returns:
            JSON string representation of the extracted data
        """
        # Create a serializable dictionary from the extracted data
        serializable_data = {
            "extraction_id": extracted_data.extraction_id,
            "document_type": extracted_data.document_type,
            "fields": {},
            "tables": [],
            "metadata": dict(extracted_data.metadata),
            "requires_verification": extracted_data.requires_verification,
            "low_confidence_fields": extracted_data.low_confidence_fields,
            "extraction_timestamp": extracted_data.extraction_timestamp,
            "schema_version": extracted_data.schema_version
        }
        
        # Convert fields to serializable format
        for field_name, field in extracted_data.fields.items():
            serializable_data["fields"][field_name] = {
                "field_name": field.field_name,
                "field_type": field.field_type,
                "value": field.value,
                "raw_text": field.raw_text,
                "confidence": float(field.confidence),
                "location": dict(field.location),
                "requires_verification": field.requires_verification,
                "verification_reason": field.verification_reason,
                "metadata": field.metadata
            }
        
        # Convert tables to serializable format
        for table in extracted_data.tables:
            serializable_table = {
                "table_id": table.table_id,
                "table_name": table.table_name,
                "headers": table.headers,
                "rows": table.rows,
                "header_row_index": table.header_row_index,
                "field_mapping": table.field_mapping,
                "row_count": table.row_count,
                "column_count": table.column_count,
                "confidence": float(table.confidence),
                "is_complete": table.is_complete,
                "metadata": table.metadata
            }
            serializable_data["tables"].append(serializable_table)
        
        # Convert to JSON string with indentation for readability
        return json.dumps(serializable_data, indent=2, default=str)
    
    def validate_extraction_against_schema(
        self, extracted_data: ExtractedData
    ) -> Tuple[bool, List[str]]:
        """Validate extracted data against its JSON schema.
        
        Args:
            extracted_data: ExtractedData object to validate
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        # Get the document type
        document_type = extracted_data.document_type
        
        # Validate using the schema registry
        return JSONSchemaRegistry.validate_extraction(extracted_data)