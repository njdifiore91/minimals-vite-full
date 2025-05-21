#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text processing utilities for the OCR Service.

This module provides functions for post-OCR text cleaning, normalization,
validation, and structured data extraction. It transforms raw OCR output
into structured, usable data for downstream processing.
"""

import re
import json
import string
import unicodedata
from typing import Dict, List, Tuple, Optional, Any, Pattern, Union, Set
from difflib import SequenceMatcher
from collections import defaultdict

# Import types
from ..types.extraction import ExtractedField, ConfidenceScore, ExtractedData
from ..types.documents import DocumentType

# Regular expressions for common patterns
EMAIL_PATTERN = re.compile(r'^[\w\.-]+@([\w\-]+\.)+[A-Za-z]{2,}$')
PHONE_PATTERN = re.compile(r'^\+?[\d\(\)\-\s]{10,20}$')
ZIP_CODE_PATTERN = re.compile(r'^\d{5}(?:-\d{4})?$')
EIN_PATTERN = re.compile(r'^\d{2}-\d{7}$')
SSN_PATTERN = re.compile(r'^\d{3}-\d{2}-\d{4}$')
CURRENCY_PATTERN = re.compile(r'^\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?$')
DATE_PATTERNS = [
    re.compile(r'^\d{1,2}/\d{1,2}/\d{2,4}$'),  # MM/DD/YYYY
    re.compile(r'^\d{1,2}-\d{1,2}-\d{2,4}$'),  # MM-DD-YYYY
    re.compile(r'^\d{4}/\d{1,2}/\d{1,2}$'),  # YYYY/MM/DD
    re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$'),  # YYYY-MM-DD
    re.compile(r'^[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{2,4}$'),  # Month DD, YYYY
]

# Common OCR errors and their corrections
OCR_SUBSTITUTIONS = {
    '0': 'O',  # Zero to letter O confusion
    'O': '0',  # Letter O to zero confusion
    '1': 'I',  # One to letter I confusion
    'I': '1',  # Letter I to one confusion
    'S': '5',  # Letter S to five confusion
    '5': 'S',  # Five to letter S confusion
    'B': '8',  # Letter B to eight confusion
    '8': 'B',  # Eight to letter B confusion
    'Z': '2',  # Letter Z to two confusion
    '2': 'Z',  # Two to letter Z confusion
    'G': '6',  # Letter G to six confusion
    '6': 'G',  # Six to letter G confusion
    'l': '1',  # Lowercase L to one confusion
    'rn': 'm',  # 'rn' to 'm' confusion
    'm': 'rn',  # 'm' to 'rn' confusion
}

# Common business terms and abbreviations for normalization
BUSINESS_TERMS = {
    'llc': 'LLC',
    'inc': 'Inc.',
    'incorporated': 'Inc.',
    'corporation': 'Corp.',
    'corp': 'Corp.',
    'limited': 'Ltd.',
    'ltd': 'Ltd.',
    'company': 'Co.',
    'co': 'Co.',
    'lp': 'LP',
    'llp': 'LLP',
    'pllc': 'PLLC',
}

# Common field names and their variations for key normalization
FIELD_NAME_VARIATIONS = {
    'name': ['name', 'full name', 'legal name', 'business name', 'company name'],
    'dba': ['dba', 'doing business as', 'd/b/a', 'd.b.a', 'trade name', 'trading as'],
    'address': ['address', 'street address', 'mailing address', 'business address', 'location'],
    'city': ['city', 'town', 'municipality'],
    'state': ['state', 'province', 'region'],
    'zip': ['zip', 'zip code', 'postal code', 'post code', 'postcode'],
    'phone': ['phone', 'telephone', 'phone number', 'tel', 'contact number', 'business phone'],
    'email': ['email', 'e-mail', 'email address', 'e-mail address'],
    'ein': ['ein', 'tax id', 'tax identification number', 'employer identification number', 'federal tax id'],
    'ssn': ['ssn', 'social security number', 'social security'],
    'revenue': ['revenue', 'annual revenue', 'yearly revenue', 'gross revenue', 'sales', 'annual sales'],
    'industry': ['industry', 'business type', 'sector', 'business category'],
}

# Document type specific field sets
DOCUMENT_TYPE_FIELDS = {
    DocumentType.APPLICATION: [
        'legal_name', 'dba_name', 'address', 'city', 'state', 'zip', 'phone', 'email',
        'ein', 'industry', 'years_in_business', 'monthly_revenue', 'requested_amount'
    ],
    DocumentType.TAX_RETURN: [
        'tax_year', 'business_name', 'ein', 'gross_receipts', 'total_income',
        'total_deductions', 'taxable_income', 'total_tax'
    ],
    DocumentType.BANK_STATEMENT: [
        'bank_name', 'account_holder', 'account_number', 'statement_period',
        'opening_balance', 'closing_balance', 'total_deposits', 'total_withdrawals'
    ],
    DocumentType.PAY_STUB: [
        'employer_name', 'employee_name', 'pay_period', 'pay_date',
        'gross_pay', 'net_pay', 'ytd_gross', 'ytd_net'
    ],
    DocumentType.ID_DOCUMENT: [
        'document_type', 'id_number', 'full_name', 'address', 'date_of_birth',
        'issue_date', 'expiration_date'
    ],
    DocumentType.OTHER: [
        'document_title', 'date', 'content_summary'
    ]
}


def clean_text(text: str) -> str:
    """
    Clean raw OCR text by removing extra whitespace, normalizing line breaks,
    and fixing common OCR artifacts.
    
    Args:
        text: Raw OCR text to clean
        
    Returns:
        Cleaned text string
    """
    if not text:
        return ""
    
    # Normalize unicode characters
    text = unicodedata.normalize('NFKD', text)
    
    # Replace multiple spaces with a single space
    text = re.sub(r'\s+', ' ', text)
    
    # Normalize line breaks
    text = re.sub(r'\r\n|\r', '\n', text)
    
    # Remove non-printable characters
    text = ''.join(c for c in text if c.isprintable() or c == '\n')
    
    # Fix common OCR artifacts
    text = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', text)  # Remove control characters
    text = re.sub(r'[\u2028\u2029]', '\n', text)  # Line/paragraph separators to newline
    
    # Remove excessive newlines (more than 2 consecutive)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def normalize_text(text: str, lowercase: bool = True) -> str:
    """
    Normalize text by converting to lowercase, removing punctuation,
    and standardizing whitespace.
    
    Args:
        text: Text to normalize
        lowercase: Whether to convert to lowercase (default: True)
        
    Returns:
        Normalized text string
    """
    if not text:
        return ""
    
    # Convert to lowercase if specified
    if lowercase:
        text = text.lower()
    
    # Remove punctuation except for specific characters needed for validation
    # Keep: @, ., -, _, +, / for emails, phone numbers, dates, etc.
    punctuation_to_remove = ''.join(c for c in string.punctuation if c not in '@.-_+/')
    translator = str.maketrans('', '', punctuation_to_remove)
    text = text.translate(translator)
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def correct_ocr_errors(text: str, field_type: Optional[str] = None) -> Tuple[str, float]:
    """
    Attempt to correct common OCR errors based on known substitution patterns
    and field-specific validation.
    
    Args:
        text: Text to correct
        field_type: Type of field (email, phone, date, etc.) for specialized correction
        
    Returns:
        Tuple of (corrected_text, confidence_score)
    """
    if not text:
        return "", 0.0
    
    original_text = text
    confidence = 1.0  # Start with perfect confidence
    
    # Apply general OCR substitutions
    for error, correction in OCR_SUBSTITUTIONS.items():
        if error in text:
            # Reduce confidence slightly for each substitution
            confidence *= 0.95
            text = text.replace(error, correction)
    
    # Apply field-specific corrections
    if field_type:
        field_type = field_type.lower()
        
        if field_type == 'email':
            # Fix common email OCR errors
            text = re.sub(r'\s+@\s+', '@', text)  # Remove spaces around @
            text = re.sub(r'\s+\.\s+', '.', text)  # Remove spaces around dots
            
            # Validate email format
            if not EMAIL_PATTERN.match(text):
                confidence *= 0.7  # Significant confidence reduction for invalid email
                
        elif field_type == 'phone':
            # Remove all non-numeric characters except +, (, ), -
            text = re.sub(r'[^\d\+\(\)\-]', '', text)
            
            # Validate phone format
            if not PHONE_PATTERN.match(text):
                confidence *= 0.7
                
        elif field_type == 'date':
            # Fix common date OCR errors
            text = re.sub(r'O', '0', text)  # Replace letter O with zero
            text = re.sub(r'l', '1', text)  # Replace lowercase l with one
            
            # Validate date format
            is_valid_date = any(pattern.match(text) for pattern in DATE_PATTERNS)
            if not is_valid_date:
                confidence *= 0.7
                
        elif field_type == 'currency':
            # Remove all non-numeric characters except $, ., ,
            text = re.sub(r'[^\d\$\.,]', '', text)
            
            # Validate currency format
            if not CURRENCY_PATTERN.match(text):
                confidence *= 0.7
                
        elif field_type == 'ein':
            # Remove all non-numeric characters except -
            text = re.sub(r'[^\d\-]', '', text)
            
            # Validate EIN format
            if not EIN_PATTERN.match(text):
                confidence *= 0.7
                
        elif field_type == 'ssn':
            # Remove all non-numeric characters except -
            text = re.sub(r'[^\d\-]', '', text)
            
            # Validate SSN format
            if not SSN_PATTERN.match(text):
                confidence *= 0.7
    
    # Calculate overall confidence based on how much the text changed
    if original_text != text:
        # Use sequence matcher to calculate similarity
        similarity = SequenceMatcher(None, original_text, text).ratio()
        # Adjust confidence based on similarity (less similar = less confident)
        confidence *= similarity
    
    return text, confidence


def normalize_business_terms(text: str) -> str:
    """
    Normalize business terms and abbreviations to standard formats.
    
    Args:
        text: Text containing business terms to normalize
        
    Returns:
        Text with normalized business terms
    """
    if not text:
        return ""
    
    # Create a pattern to match business terms
    pattern = r'\b(' + '|'.join(re.escape(term) for term in BUSINESS_TERMS.keys()) + r')\b'
    
    # Function to replace matched terms with their normalized form
    def replace_term(match):
        term = match.group(0).lower()
        return BUSINESS_TERMS.get(term, term)
    
    # Apply replacements
    normalized_text = re.sub(pattern, replace_term, text, flags=re.IGNORECASE)
    
    return normalized_text


def extract_key_value_pairs(text: str, line_threshold: int = 3) -> List[Tuple[str, str, float]]:
    """
    Extract key-value pairs from document text using pattern recognition.
    
    Args:
        text: Document text to process
        line_threshold: Maximum number of lines to consider for multi-line values
        
    Returns:
        List of tuples containing (key, value, confidence_score)
    """
    if not text:
        return []
    
    # Clean and split the text into lines
    cleaned_text = clean_text(text)
    lines = cleaned_text.split('\n')
    
    key_value_pairs = []
    current_key = None
    current_value = []
    current_confidence = 1.0
    line_count = 0
    
    # Common key-value separators
    separators = [':', '=', '-', '–', '—']
    
    # Pattern for key-value pairs on the same line
    kv_pattern = re.compile(r'^([\w\s\-\.\&\,\']+)([:\=\-–—])\s*(.+)$')
    
    for line in lines:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
        
        # Check for key-value pair on the same line
        kv_match = kv_pattern.match(line)
        
        if kv_match:
            # If we were building a multi-line value, add the previous key-value pair
            if current_key and current_value:
                value_text = ' '.join(current_value)
                key_value_pairs.append((current_key, value_text, current_confidence))
            
            # Extract the new key-value pair
            key = kv_match.group(1).strip()
            value = kv_match.group(3).strip()
            
            # Normalize the key
            normalized_key = normalize_key(key)
            
            # Correct OCR errors in the value based on the key type
            corrected_value, confidence = correct_ocr_errors(value, normalized_key)
            
            key_value_pairs.append((normalized_key, corrected_value, confidence))
            
            # Reset for the next pair
            current_key = None
            current_value = []
            current_confidence = 1.0
            line_count = 0
            
        elif any(separator in line for separator in separators):
            # Handle case where the separator is present but not matched by the regex
            for separator in separators:
                if separator in line:
                    parts = line.split(separator, 1)
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = parts[1].strip()
                        
                        if key and value:  # Both key and value must be non-empty
                            # If we were building a multi-line value, add the previous key-value pair
                            if current_key and current_value:
                                value_text = ' '.join(current_value)
                                key_value_pairs.append((current_key, value_text, current_confidence))
                            
                            # Normalize the key
                            normalized_key = normalize_key(key)
                            
                            # Correct OCR errors in the value based on the key type
                            corrected_value, confidence = correct_ocr_errors(value, normalized_key)
                            
                            key_value_pairs.append((normalized_key, corrected_value, confidence))
                            
                            # Reset for the next pair
                            current_key = None
                            current_value = []
                            current_confidence = 1.0
                            line_count = 0
                            break
        
        elif current_key and line_count < line_threshold:
            # Continue building a multi-line value
            current_value.append(line)
            line_count += 1
            
        elif is_potential_key(line):
            # If we were building a multi-line value, add the previous key-value pair
            if current_key and current_value:
                value_text = ' '.join(current_value)
                key_value_pairs.append((current_key, value_text, current_confidence))
            
            # Start a new potential key
            current_key = normalize_key(line)
            current_value = []
            current_confidence = 1.0
            line_count = 0
            
        else:
            # If no key is being processed, this might be a standalone line
            # We'll skip it as it doesn't fit our key-value pattern
            pass
    
    # Add the last key-value pair if there is one being built
    if current_key and current_value:
        value_text = ' '.join(current_value)
        key_value_pairs.append((current_key, value_text, current_confidence))
    
    return key_value_pairs


def normalize_key(key: str) -> str:
    """
    Normalize a key by removing punctuation, converting to lowercase,
    and matching to known field names.
    
    Args:
        key: Key to normalize
        
    Returns:
        Normalized key string
    """
    if not key:
        return ""
    
    # Clean and normalize the key
    normalized = normalize_text(key, lowercase=True)
    
    # Remove common key prefixes
    prefixes = ['please enter', 'enter', 'provide', 'your', 'business', 'applicant']
    for prefix in prefixes:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix):].strip()
    
    # Remove common key suffixes
    suffixes = ['(required)', 'required', 'optional', ':']
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[:-len(suffix)].strip()
    
    # Match to known field name variations
    for standard_key, variations in FIELD_NAME_VARIATIONS.items():
        if normalized in variations:
            return standard_key
    
    # If no match found, convert spaces to underscores for a consistent format
    return normalized.replace(' ', '_')


def is_potential_key(text: str) -> bool:
    """
    Determine if a text line is likely to be a form field key/label.
    
    Args:
        text: Text line to evaluate
        
    Returns:
        Boolean indicating if the text is likely a key
    """
    if not text:
        return False
    
    # Clean and normalize the text
    normalized = normalize_text(text, lowercase=True)
    
    # Check if it's a very short line (likely not a key)
    if len(normalized) < 3:
        return False
    
    # Check if it's a very long line (likely not a key)
    if len(normalized) > 50:
        return False
    
    # Check if it contains common key words
    key_indicators = ['name', 'address', 'phone', 'email', 'date', 'number', 'amount', 'id', 'tax']
    if any(indicator in normalized for indicator in key_indicators):
        return True
    
    # Check if it matches any known field name variations
    for variations in FIELD_NAME_VARIATIONS.values():
        if normalized in variations:
            return True
    
    # Check if it ends with common key suffixes
    key_suffixes = [':', '?', '(required)', 'required', 'optional']
    if any(normalized.endswith(suffix) for suffix in key_suffixes):
        return True
    
    # If none of the above conditions are met, it's less likely to be a key
    return False


def extract_structured_data(text: str, document_type: DocumentType) -> ExtractedData:
    """
    Extract structured data from document text based on document type.
    
    Args:
        text: Document text to process
        document_type: Type of document for specialized extraction
        
    Returns:
        ExtractedData object containing structured fields and metadata
    """
    # Extract key-value pairs from the text
    key_value_pairs = extract_key_value_pairs(text)
    
    # Get the expected fields for this document type
    expected_fields = DOCUMENT_TYPE_FIELDS.get(document_type, [])
    
    # Initialize the extracted data with empty fields
    extracted_fields: Dict[str, ExtractedField] = {}
    missing_fields: List[str] = []
    low_confidence_fields: List[str] = []
    
    # Process each key-value pair
    for key, value, confidence in key_value_pairs:
        # Skip empty values
        if not value:
            continue
        
        # Create field location (placeholder - would be populated by OCR service)
        field_location = {
            "page": 1,
            "top": 0,
            "left": 0,
            "width": 0,
            "height": 0
        }
        
        # Create the extracted field
        extracted_field = {
            "key": key,
            "value": value,
            "confidence": confidence,
            "location": field_location,
            "needs_review": confidence < 0.8  # Flag for human review if confidence is low
        }
        
        # Add to extracted fields
        extracted_fields[key] = extracted_field
        
        # Track low confidence fields
        if confidence < 0.8:
            low_confidence_fields.append(key)
    
    # Check for missing expected fields
    for field in expected_fields:
        if field not in extracted_fields:
            missing_fields.append(field)
    
    # Create the extraction metadata
    metadata = {
        "document_type": document_type.value,
        "extraction_timestamp": "2023-01-01T00:00:00Z",  # Placeholder - would be current time
        "missing_fields": missing_fields,
        "low_confidence_fields": low_confidence_fields,
        "needs_review": len(low_confidence_fields) > 0 or len(missing_fields) > 0
    }
    
    # Create the extracted data object
    extracted_data = {
        "fields": extracted_fields,
        "metadata": metadata
    }
    
    return extracted_data


def generate_json_schema(document_type: DocumentType) -> Dict[str, Any]:
    """
    Generate a JSON schema for the specified document type.
    
    Args:
        document_type: Type of document to generate schema for
        
    Returns:
        JSON schema as a dictionary
    """
    # Get the expected fields for this document type
    fields = DOCUMENT_TYPE_FIELDS.get(document_type, [])
    
    # Define field types based on field names
    field_types = {
        "legal_name": "string",
        "dba_name": "string",
        "address": "string",
        "city": "string",
        "state": "string",
        "zip": "string",
        "phone": "string",
        "email": "string",
        "ein": "string",
        "ssn": "string",
        "industry": "string",
        "years_in_business": "number",
        "monthly_revenue": "number",
        "requested_amount": "number",
        "tax_year": "string",
        "business_name": "string",
        "gross_receipts": "number",
        "total_income": "number",
        "total_deductions": "number",
        "taxable_income": "number",
        "total_tax": "number",
        "bank_name": "string",
        "account_holder": "string",
        "account_number": "string",
        "statement_period": "string",
        "opening_balance": "number",
        "closing_balance": "number",
        "total_deposits": "number",
        "total_withdrawals": "number",
        "employer_name": "string",
        "employee_name": "string",
        "pay_period": "string",
        "pay_date": "string",
        "gross_pay": "number",
        "net_pay": "number",
        "ytd_gross": "number",
        "ytd_net": "number",
        "document_type": "string",
        "id_number": "string",
        "full_name": "string",
        "date_of_birth": "string",
        "issue_date": "string",
        "expiration_date": "string",
        "document_title": "string",
        "date": "string",
        "content_summary": "string"
    }
    
    # Create properties for each field
    properties = {}
    required_fields = []
    
    for field in fields:
        field_type = field_types.get(field, "string")  # Default to string if type not defined
        
        # Define the property
        if field_type == "string":
            properties[field] = {
                "type": "string",
                "description": f"{field.replace('_', ' ').title()}"
            }
        elif field_type == "number":
            properties[field] = {
                "type": "number",
                "description": f"{field.replace('_', ' ').title()}"
            }
        
        # Add to required fields (except for optional fields)
        optional_fields = ["dba_name", "content_summary"]
        if field not in optional_fields:
            required_fields.append(field)
    
    # Create the schema
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": f"{document_type.value} Schema",
        "description": f"Schema for {document_type.value} document type",
        "type": "object",
        "properties": properties,
        "required": required_fields
    }
    
    return schema


def extract_tables(text: str) -> List[Dict[str, Any]]:
    """
    Extract tabular data from document text.
    
    Args:
        text: Document text to process
        
    Returns:
        List of dictionaries representing tables with headers and rows
    """
    if not text:
        return []
    
    # Clean and split the text into lines
    cleaned_text = clean_text(text)
    lines = cleaned_text.split('\n')
    
    tables = []
    current_table = None
    header_line = None
    
    # Patterns to identify table headers and data rows
    header_pattern = re.compile(r'^\s*([A-Za-z\s]+(?:\s+[A-Za-z\s]+){2,})\s*$')
    data_row_pattern = re.compile(r'^\s*([\w\s\-\.\$\,]+(?:\s{2,}[\w\s\-\.\$\,]+){2,})\s*$')
    
    for i, line in enumerate(lines):
        # Skip empty lines
        if not line.strip():
            continue
        
        # Check if this line looks like a table header
        header_match = header_pattern.match(line)
        if header_match and not current_table:
            # This might be a header line
            header_line = line
            
            # Look ahead to see if the next non-empty lines match data row pattern
            data_rows = []
            for j in range(i + 1, min(i + 5, len(lines))):
                if lines[j].strip() and data_row_pattern.match(lines[j]):
                    data_rows.append(lines[j])
            
            # If we found potential data rows, start a new table
            if len(data_rows) >= 2:  # At least 2 data rows to confirm it's a table
                # Split header into columns based on whitespace
                header_parts = re.split(r'\s{2,}', header_line.strip())
                
                current_table = {
                    "headers": header_parts,
                    "rows": []
                }
        
        # If we're currently building a table, check if this line is a data row
        elif current_table and data_row_pattern.match(line):
            # Split the line into columns based on whitespace
            row_parts = re.split(r'\s{2,}', line.strip())
            
            # Only add the row if it has the same number of columns as the header
            if len(row_parts) == len(current_table["headers"]):
                current_table["rows"].append(row_parts)
            else:
                # If column count doesn't match, this might be the end of the table
                tables.append(current_table)
                current_table = None
                header_line = None
        
        # If we're building a table but this line doesn't match a data row,
        # it might be the end of the table
        elif current_table:
            tables.append(current_table)
            current_table = None
            header_line = None
    
    # Add the last table if there is one being built
    if current_table:
        tables.append(current_table)
    
    return tables


def validate_field(value: str, field_type: str) -> Tuple[bool, str, float]:
    """
    Validate a field value based on its expected type and format.
    
    Args:
        value: Field value to validate
        field_type: Type of field (email, phone, date, etc.)
        
    Returns:
        Tuple of (is_valid, corrected_value, confidence_score)
    """
    if not value:
        return False, "", 0.0
    
    # Clean the value
    cleaned_value = clean_text(value)
    
    # Apply field-specific validation and correction
    field_type = field_type.lower()
    
    if field_type == 'email':
        # Correct common email OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'email')
        
        # Validate email format
        is_valid = bool(EMAIL_PATTERN.match(corrected_value))
        return is_valid, corrected_value, confidence
        
    elif field_type == 'phone':
        # Correct common phone OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'phone')
        
        # Validate phone format
        is_valid = bool(PHONE_PATTERN.match(corrected_value))
        return is_valid, corrected_value, confidence
        
    elif field_type == 'date':
        # Correct common date OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'date')
        
        # Validate date format
        is_valid = any(pattern.match(corrected_value) for pattern in DATE_PATTERNS)
        return is_valid, corrected_value, confidence
        
    elif field_type == 'currency':
        # Correct common currency OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'currency')
        
        # Validate currency format
        is_valid = bool(CURRENCY_PATTERN.match(corrected_value))
        return is_valid, corrected_value, confidence
        
    elif field_type == 'ein':
        # Correct common EIN OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'ein')
        
        # Validate EIN format
        is_valid = bool(EIN_PATTERN.match(corrected_value))
        return is_valid, corrected_value, confidence
        
    elif field_type == 'ssn':
        # Correct common SSN OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'ssn')
        
        # Validate SSN format
        is_valid = bool(SSN_PATTERN.match(corrected_value))
        return is_valid, corrected_value, confidence
        
    elif field_type == 'zip':
        # Correct common ZIP code OCR errors
        corrected_value, confidence = correct_ocr_errors(cleaned_value, 'zip')
        
        # Validate ZIP code format
        is_valid = bool(ZIP_CODE_PATTERN.match(corrected_value))
        return is_valid, corrected_value, confidence
    
    # For other field types, just return the cleaned value with high confidence
    return True, cleaned_value, 0.9


def format_extracted_data_as_json(extracted_data: ExtractedData) -> str:
    """
    Format extracted data as a JSON string.
    
    Args:
        extracted_data: ExtractedData object to format
        
    Returns:
        JSON string representation of the extracted data
    """
    # Convert to JSON string with indentation for readability
    return json.dumps(extracted_data, indent=2)


def extract_form_fields(text: str) -> Dict[str, Any]:
    """
    Extract form fields from document text, focusing on application forms.
    
    Args:
        text: Document text to process
        
    Returns:
        Dictionary of form fields with their values and metadata
    """
    # Extract key-value pairs
    key_value_pairs = extract_key_value_pairs(text)
    
    # Create a dictionary to store form fields
    form_fields = {}
    
    # Process each key-value pair
    for key, value, confidence in key_value_pairs:
        # Determine the field type based on the key
        field_type = determine_field_type(key)
        
        # Validate and correct the field value
        is_valid, corrected_value, validation_confidence = validate_field(value, field_type)
        
        # Combine the extraction confidence with the validation confidence
        combined_confidence = confidence * validation_confidence
        
        # Create the form field entry
        form_fields[key] = {
            "value": corrected_value,
            "confidence": combined_confidence,
            "is_valid": is_valid,
            "field_type": field_type,
            "needs_review": combined_confidence < 0.8 or not is_valid
        }
    
    return form_fields


def determine_field_type(key: str) -> str:
    """
    Determine the field type based on the key name.
    
    Args:
        key: Field key to analyze
        
    Returns:
        Field type string (email, phone, date, etc.)
    """
    key = key.lower()
    
    # Check for email fields
    if any(term in key for term in ['email', 'e-mail']):
        return 'email'
    
    # Check for phone fields
    if any(term in key for term in ['phone', 'telephone', 'mobile', 'cell']):
        return 'phone'
    
    # Check for date fields
    if any(term in key for term in ['date', 'dob', 'birth', 'issued', 'expiry', 'expiration']):
        return 'date'
    
    # Check for currency fields
    if any(term in key for term in ['amount', 'revenue', 'income', 'payment', 'balance', 'price', 'cost', 'fee', 'salary', 'wage']):
        return 'currency'
    
    # Check for EIN fields
    if any(term in key for term in ['ein', 'tax id', 'tax identification', 'employer identification']):
        return 'ein'
    
    # Check for SSN fields
    if any(term in key for term in ['ssn', 'social security']):
        return 'ssn'
    
    # Check for ZIP code fields
    if any(term in key for term in ['zip', 'postal', 'post code']):
        return 'zip'
    
    # Default to text for unknown field types
    return 'text'


def extract_sections(text: str) -> Dict[str, str]:
    """
    Extract document sections based on headings and content blocks.
    
    Args:
        text: Document text to process
        
    Returns:
        Dictionary of section headings and their content
    """
    if not text:
        return {}
    
    # Clean and split the text into lines
    cleaned_text = clean_text(text)
    lines = cleaned_text.split('\n')
    
    sections = {}
    current_section = "HEADER"  # Default section for content before the first heading
    current_content = []
    
    # Pattern to identify section headings
    # Looks for lines that are all uppercase, or have specific heading markers
    heading_pattern = re.compile(r'^\s*(?:[A-Z][\s\.]*)(?:[A-Z][\s\.]*)+\s*$|^\s*(?:SECTION|PART)\s+[\d\w]+[\s\:].*$')
    
    for line in lines:
        line = line.strip()
        if not line:  # Skip empty lines
            continue
        
        # Check if this line looks like a section heading
        if heading_pattern.match(line) and len(line) < 100:  # Avoid matching long all-caps paragraphs
            # Save the previous section if it exists
            if current_content:
                sections[current_section] = '\n'.join(current_content)
            
            # Start a new section
            current_section = line
            current_content = []
        else:
            # Add to the current section content
            current_content.append(line)
    
    # Add the last section
    if current_content:
        sections[current_section] = '\n'.join(current_content)
    
    return sections