#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Text processing utilities for the OCR Service.

This module provides functions for post-OCR text cleaning, normalization,
validation, and structured data extraction. It transforms raw OCR output
into structured, usable data for downstream processing.
"""

import re
import string
import unicodedata
from typing import Dict, List, Optional, Tuple, Union, Any, Pattern, Set
import json
import logging
from difflib import SequenceMatcher
import dateutil.parser

# Setup module logger
logger = logging.getLogger(__name__)

# Common regex patterns
EMAIL_PATTERN = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PHONE_PATTERN = re.compile(r'(?:\+?\d{1,2}\s*)?\(?\d{3}\)?[\s.-]*\d{3}[\s.-]*\d{4}')
ZIP_CODE_PATTERN = re.compile(r'\b\d{5}(?:-\d{4})?\b')
EIN_PATTERN = re.compile(r'\b\d{2}-\d{7}\b')
SSN_PATTERN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
CURRENCY_PATTERN = re.compile(r'\$?\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?')
DATE_PATTERN = re.compile(r'\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b')

# Common text replacements for OCR errors
OCR_REPLACEMENTS = {
    'l': '1',  # lowercase l to 1
    'O': '0',  # capital O to 0
    'S': '5',  # capital S to 5
    'Z': '2',  # capital Z to 2
    'B': '8',  # capital B to 8
    'G': '6',  # capital G to 6
    'I': '1',  # capital I to 1
    'o': '0',  # lowercase o to 0
}

# Common field names and their variations
FIELD_NAME_VARIATIONS = {
    'name': ['name', 'full name', 'legal name', 'business name', 'dba name'],
    'address': ['address', 'street address', 'mailing address', 'business address'],
    'city': ['city', 'town', 'municipality'],
    'state': ['state', 'province', 'region'],
    'zip': ['zip', 'zip code', 'postal code', 'post code'],
    'phone': ['phone', 'telephone', 'phone number', 'tel', 'cell', 'mobile'],
    'email': ['email', 'e-mail', 'email address', 'e-mail address'],
    'ein': ['ein', 'tax id', 'tax identification number', 'employer identification number'],
    'ssn': ['ssn', 'social security', 'social security number'],
    'dob': ['dob', 'date of birth', 'birth date', 'birthdate'],
    'revenue': ['revenue', 'annual revenue', 'yearly revenue', 'gross revenue'],
    'industry': ['industry', 'business type', 'sector', 'business category'],
}


def clean_text(text: str) -> str:
    """
    Clean raw OCR text by removing extra whitespace, normalizing characters,
    and fixing common OCR errors.
    
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
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Convert smart quotes to regular quotes
    text = text.replace('"', '"').replace(''', "'").replace(''', "'")
    
    # Apply common OCR error corrections in numeric contexts
    for error, correction in OCR_REPLACEMENTS.items():
        # Only replace characters likely to be digits in numeric contexts
        # For example, replace 'l' with '1' in "l23" but not in "hello"
        text = re.sub(f'(?<=\\d){error}(?=\\d)', correction, text)  # Between digits
        text = re.sub(f'^{error}(?=\\d)', correction, text)  # Start of string followed by digit
        text = re.sub(f'(?<=\\d){error}$', correction, text)  # Digit followed by end of string
    
    return text


def normalize_field(value: str, field_type: Optional[str] = None) -> str:
    """
    Normalize a field value based on its type.
    
    Args:
        value: Field value to normalize
        field_type: Type of field for specific normalization
        
    Returns:
        Normalized field value
    """
    # Clean the text first
    value = clean_text(value)
    
    # Apply specific normalization if field type is provided
    if field_type:
        field_type = field_type.lower()
        
        if field_type == 'phone':
            # Extract only digits
            digits = re.sub(r'\D', '', value)
            if len(digits) == 10:
                return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
            elif len(digits) > 10:
                return f"+{digits[0:-10]} ({digits[-10:-7]}) {digits[-7:-4]}-{digits[-4:]}"