"""Type definitions for OCR extraction results used by the OCR Service.

This module provides type hints for representing the results of OCR processing,
including extracted text, field identification, confidence scores, and structured data.
It ensures type safety for extraction results throughout the OCR processing pipeline.
"""

from __future__ import annotations

import enum
import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union, ClassVar, Type, cast

# Import TensorFlow type hints conditionally to avoid runtime dependency
try:
    import tensorflow as tf
    TensorType = tf.Tensor
except ImportError:
    # Define placeholder type if TensorFlow is not available
    class TensorType:
        pass


@dataclass
class ConfidenceScore:
    """Type representing the confidence level of an extraction.
    
    This is a float value between 0.0 and 1.0 that represents the confidence
    level of an OCR extraction. Higher values indicate higher confidence.
    """
    
    value: float
    
    def __post_init__(self):
        """Ensure value is within valid range."""
        self.value = max(0.0, min(1.0, self.value))
    
    def __float__(self) -> float:
        """Convert to float."""
        return self.value
    
    def is_low_confidence(self, threshold: float = 0.7) -> bool:
        """Check if this confidence score is below the specified threshold.
        
        Args:
            threshold: Confidence threshold (default: 0.7)
            
        Returns:
            True if confidence is below threshold
        """
        return self.value < threshold
    
    @classmethod
    def from_float(cls, value: float) -> 'ConfidenceScore':
        """Create a new ConfidenceScore instance with value clamped to [0.0, 1.0].
        
        Args:
            value: Confidence value
            
        Returns:
            New ConfidenceScore instance
        """
        return cls(value=value)


class FieldType(enum.Enum):
    """Types of fields that can be extracted from documents during OCR processing.
    
    These field types correspond to different data types and formats
    that can be extracted from documents during OCR processing.
    """
    
    TEXT = "text"  # General text content
    NUMBER = "number"  # Numeric value
    DATE = "date"  # Date value
    CURRENCY = "currency"  # Monetary value
    PERCENTAGE = "percentage"  # Percentage value
    NAME = "name"  # Person name
    ADDRESS = "address"  # Physical address
    PHONE = "phone"  # Phone number
    EMAIL = "email"  # Email address
    SSN = "ssn"  # Social Security Number
    EIN = "ein"  # Employer Identification Number
    ACCOUNT_NUMBER = "account_number"  # Account number
    CHECKBOX = "checkbox"  # Checkbox (checked/unchecked)
    SIGNATURE = "signature"  # Signature field
    TABLE = "table"  # Table structure
    CUSTOM = "custom"  # Custom field type


class FieldLocation(TypedDict):
    """Location of a field within a document.
    
    This type represents the position of an extracted field within the original document,
    using normalized coordinates (0.0-1.0) relative to the document dimensions.
    """
    
    page: int  # Page number (0-based)
    top: float  # Top coordinate (normalized 0.0-1.0)
    left: float  # Left coordinate (normalized 0.0-1.0)
    bottom: float  # Bottom coordinate (normalized 0.0-1.0)
    right: float  # Right coordinate (normalized 0.0-1.0)
    width: float  # Width of the field (normalized 0.0-1.0)
    height: float  # Height of the field (normalized 0.0-1.0)


class ExtractedField(TypedDict):
    """Representation of an individual extracted field.
    
    This type represents a single field extracted from a document,
    including its value, confidence score, and location information.
    """
    
    field_name: str  # Name of the field (e.g., "business_name", "tax_id")
    field_type: str  # Type of field
    value: Any  # Processed value of the field
    raw_text: str  # Raw extracted text before processing
    confidence: ConfidenceScore  # Confidence score for this field
    location: FieldLocation  # Location in the document
    alternatives: List[Tuple[Any, ConfidenceScore]]  # Alternative values with confidence scores
    metadata: Dict[str, Any]  # Additional field-specific metadata
    requires_verification: bool  # Whether this field requires human verification
    verification_reason: Optional[str]  # Reason for verification if required
    extraction_timestamp: datetime  # When the field was extracted


class ExtractionMetadata(TypedDict):
    """Metadata about the extraction process.
    
    This type contains information about the extraction process itself,
    including timing, processing details, and status information.
    """
    
    extraction_id: str  # Unique ID for this extraction
    document_id: str  # ID of the document processed
    model_id: str  # ID of the model used for extraction
    model_version: str  # Version of the model used
    document_type: str  # Type of document processed
    page_count: int  # Number of pages processed
    language: str  # Language of the document
    processing_node: str  # ID of the node that processed the document
    extraction_status: str  # Status of the extraction (success, partial, failed)
    processing_time: float  # Time taken to process the document in seconds
    warnings: List[str]  # Warnings generated during extraction
    errors: List[str]  # Errors encountered during extraction


class TableData(TypedDict):
    """Representation of an extracted table.
    
    This type represents a table structure extracted from a document,
    including headers, rows, and metadata.
    """
    
    table_id: str  # Unique ID for this table
    table_name: Optional[str]  # Name of the table if identified
    headers: List[str]  # Column headers
    rows: List[List[Any]]  # Table data as a list of rows
    header_row_index: int  # Index of the header row
    field_mapping: Dict[str, int]  # Mapping of field names to column indices
    row_count: int  # Number of rows
    column_count: int  # Number of columns
    confidence: ConfidenceScore  # Overall table confidence score
    is_complete: bool  # Whether the table was completely extracted
    metadata: Dict[str, Any]  # Additional table-specific metadata


class ExtractedData(TypedDict):
    """Complete extraction results for a document.
    
    This type represents the complete set of data extracted from a document,
    including all fields, tables, and metadata.
    """
    
    extraction_id: str  # Unique ID for this extraction
    fields: Dict[str, ExtractedField]  # Extracted fields by name
    tables: List[TableData]  # Extracted tables
    metadata: ExtractionMetadata  # Extraction metadata
    raw_text: str  # Full raw text extracted from the document
    low_confidence_fields: List[str]  # Names of fields with low confidence
    requires_verification: bool  # Whether this extraction requires human verification
    extraction_timestamp: datetime  # When the extraction was completed
    schema_version: str  # Version of the extraction schema
    document_type: str  # Type of document processed


class JSONSchemaType(enum.Enum):
    """JSON Schema types for defining the structure of extracted data.
    
    These types correspond to the standard JSON Schema types used to define
    the structure of extracted data for validation and documentation.
    """
    
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    OBJECT = "object"
    ARRAY = "array"
    NULL = "null"


class JSONSchemaProperty(TypedDict, total=False):
    """JSON Schema property definition.
    
    This type represents a property definition in a JSON Schema,
    used to define the structure of extracted data.
    The 'total=False' parameter indicates that all fields are optional.
    """
    
    type: Union[JSONSchemaType, List[JSONSchemaType]]  # Property type(s)
    format: str  # Format specifier (e.g., "date-time", "email")
    description: str  # Property description
    enum: List[Any]  # Enumerated values
    minimum: float  # Minimum value for numbers
    maximum: float  # Maximum value for numbers
    minLength: int  # Minimum length for strings
    maxLength: int  # Maximum length for strings
    pattern: str  # Regex pattern for strings
    required: List[str]  # Required properties (for objects)
    properties: Dict[str, 'JSONSchemaProperty']  # Nested properties (for objects)
    items: Union['JSONSchemaProperty', List['JSONSchemaProperty']]  # Array item definition


class JSONSchema(TypedDict, total=False):
    """JSON Schema definition for extracted data.
    
    This type represents a complete JSON Schema definition,
    used to define and validate the structure of extracted data.
    The 'total=False' parameter indicates that all fields are optional.
    """
    
    $schema: str  # JSON Schema version
    $id: str  # Schema identifier
    title: str  # Schema title
    description: str  # Schema description
    type: JSONSchemaType  # Schema type (usually "object")
    properties: Dict[str, JSONSchemaProperty]  # Schema properties
    required: List[str]  # Required properties
    additionalProperties: bool  # Whether additional properties are allowed


class JSONSchemaRegistry:
    """Registry of JSON Schemas for different document types.
    
    This class provides a registry of JSON Schemas for different document types,
    allowing schemas to be registered, retrieved, and used for validation.
    """
    
    _schemas: ClassVar[Dict[str, JSONSchema]] = {}
    
    @classmethod
    def register_schema(cls, document_type: str, schema: JSONSchema) -> None:
        """Register a JSON Schema for a document type.
        
        Args:
            document_type: Document type identifier
            schema: JSON Schema for the document type
        """
        cls._schemas[document_type] = schema
    
    @classmethod
    def get_schema(cls, document_type: str) -> Optional[JSONSchema]:
        """Get the JSON Schema for a document type.
        
        Args:
            document_type: Document type identifier
            
        Returns:
            JSON Schema for the document type, or None if not found
        """
        return cls._schemas.get(document_type)
    
    @classmethod
    def validate_extraction(cls, data: ExtractedData) -> Tuple[bool, List[str]]:
        """Validate extracted data against its schema.
        
        Args:
            data: Extracted data to validate
            
        Returns:
            A tuple of (is_valid, error_messages)
        """
        document_type = data.get('document_type')
        if not document_type:
            return False, ["Missing document_type in extracted data"]
        
        schema = cls.get_schema(document_type)
        if not schema:
            return False, [f"No schema registered for document type: {document_type}"]
        
        try:
            # This is a simplified validation example
            # In a real implementation, you would use a JSON Schema validator library
            errors = []
            
            # Check required fields
            required_fields = schema.get('required', [])
            for field_name in required_fields:
                if field_name not in data.get('fields', {}):
                    errors.append(f"Missing required field: {field_name}")
            
            # Check field types (simplified)
            properties = schema.get('properties', {})
            for field_name, field_data in data.get('fields', {}).items():
                if field_name in properties:
                    field_schema = properties[field_name]
                    field_type = field_schema.get('type')
                    if field_type and isinstance(field_type, str):
                        # Simplified type checking
                        value = field_data.get('value')
                        if field_type == 'string' and not isinstance(value, str):
                            errors.append(f"Field {field_name} should be a string")
                        elif field_type == 'number' and not isinstance(value, (int, float)):
                            errors.append(f"Field {field_name} should be a number")
                        elif field_type == 'boolean' and not isinstance(value, bool):
                            errors.append(f"Field {field_name} should be a boolean")
            
            return len(errors) == 0, errors
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]


# Example JSON Schema for an application form
APPLICATION_FORM_SCHEMA: JSONSchema = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "$id": "https://dollarfunding.com/schemas/application-form.json",
    "title": "Application Form Schema",
    "description": "Schema for extracted data from application forms",
    "type": JSONSchemaType.OBJECT,
    "properties": {
        "business_name": {
            "type": JSONSchemaType.STRING,
            "description": "Legal business name",
            "minLength": 1,
            "maxLength": 100
        },
        "dba_name": {
            "type": JSONSchemaType.STRING,
            "description": "Doing business as name",
            "minLength": 0,
            "maxLength": 100
        },
        "tax_id": {
            "type": JSONSchemaType.STRING,
            "description": "Business tax ID (EIN)",
            "pattern": r"^\d{2}-\d{7}$"
        },
        "business_address": {
            "type": JSONSchemaType.STRING,
            "description": "Business street address",
            "minLength": 5,
            "maxLength": 200
        },
        "business_phone": {
            "type": JSONSchemaType.STRING,
            "description": "Business phone number",
            "pattern": r"^\(\d{3}\) \d{3}-\d{4}$"
        },
        "business_email": {
            "type": JSONSchemaType.STRING,
            "description": "Business email address",
            "format": "email"
        },
        "requested_amount": {
            "type": JSONSchemaType.NUMBER,
            "description": "Requested funding amount",
            "minimum": 5000,
            "maximum": 500000
        },
        "business_start_date": {
            "type": JSONSchemaType.STRING,
            "description": "Business start date",
            "format": "date"
        },
        "monthly_revenue": {
            "type": JSONSchemaType.NUMBER,
            "description": "Average monthly revenue",
            "minimum": 0
        },
        "owner_name": {
            "type": JSONSchemaType.STRING,
            "description": "Business owner's full name",
            "minLength": 2,
            "maxLength": 100
        },
        "owner_ssn": {
            "type": JSONSchemaType.STRING,
            "description": "Business owner's SSN",
            "pattern": r"^\d{3}-\d{2}-\d{4}$"
        },
        "signature_present": {
            "type": JSONSchemaType.BOOLEAN,
            "description": "Whether a signature is present on the application"
        },
        "application_date": {
            "type": JSONSchemaType.STRING,
            "description": "Date of application submission",
            "format": "date"
        }
    },
    "required": [
        "business_name",
        "tax_id",
        "business_address",
        "business_phone",
        "requested_amount",
        "owner_name",
        "signature_present",
        "application_date"
    ]
}

# Register the application form schema
JSONSchemaRegistry.register_schema("application_form", APPLICATION_FORM_SCHEMA)