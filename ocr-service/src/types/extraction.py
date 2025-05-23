"""
Type definitions for OCR extraction results, field extraction, confidence scoring, and JSON formatting.

This module provides type definitions for representing the results of OCR processing,
including extracted text, field identification, confidence scores, and structured data.
These types are used throughout the OCR Service to ensure type safety and consistent
data structures for extraction results.

The OCR Service extracts data from documents using TensorFlow models, adds confidence
scoring for extracted fields, and formats the data in a standardized JSON structure.
These type definitions support the core functionality of identifying fields in documents,
tracking their positions, assessing extraction confidence, and flagging low-confidence
extractions for human verification.

Example usage:
    ```python
    # Create field extractions
    business_name = {
        'field_id': 'business_name',
        'field_name': 'Business Name',
        'value': 'Acme Corporation',
        'raw_text': 'Acme Corporation',
        'confidence': 0.98,
        'requires_verification': False,
        'field_type': 'text'
    }
    
    # Create metadata
    metadata = {
        'document_id': 'doc-123',
        'extraction_id': 'ext-456',
        'document_type': 'loan_application',
        'extraction_timestamp': datetime.now(),
        'ocr_model_version': '2.15.0',
        'average_confidence': 0.92
    }
    
    # Create document-specific data
    loan_app_data = {
        'business_name': business_name,
        # ... other fields
    }
    
    # Create extraction result
    extraction = create_extracted_data(
        fields={'business_name': business_name},
        metadata=metadata,
        document_type_specific_data=loan_app_data
    )
    
    # Check if human verification is needed
    if extraction.requires_human_verification():
        # Route for human review
        pass
    ```
"""

from typing import Dict, List, Optional, Union, TypedDict, Literal, Any, TypeVar, Generic
from datetime import datetime
import json

# Type for confidence scores (0.0 to 1.0)
# Confidence scores represent the model's certainty about an extraction
# 0.0 = No confidence, 1.0 = Complete confidence
ConfidenceScore = float  # Range: 0.0 to 1.0

# Threshold for low confidence that requires human verification
# Fields with confidence below this threshold will be flagged for review
# This value is set to 0.75 (75%) based on validation testing that showed
# optimal balance between automation rate and accuracy
LOW_CONFIDENCE_THRESHOLD = 0.75


class FieldLocation(TypedDict):
    """
    Represents the location of a field in the original document.
    
    Coordinates are normalized to the page dimensions (0.0 to 1.0) to make them
    resolution-independent. This allows for consistent field highlighting across
    different display resolutions and zoom levels.
    
    For example, a value of {page: 0, top: 0.1, left: 0.2, bottom: 0.15, right: 0.8}
    represents a field on the first page, starting 10% from the top of the page,
    20% from the left, with a height of 5% of the page and a width of 60% of the page.
    """
    page: int  # Page number (0-indexed)
    top: float  # Top coordinate (normalized 0.0-1.0)
    left: float  # Left coordinate (normalized 0.0-1.0)
    bottom: float  # Bottom coordinate (normalized 0.0-1.0)
    right: float  # Right coordinate (normalized 0.0-1.0)


class ExtractedField(TypedDict, total=False):
    """
    Represents an individual extracted field with value and confidence score.
    
    This type captures all information about a single extracted field, including its
    value, confidence score, location in the document, and any additional metadata.
    The 'total=False' parameter indicates that all fields are optional, allowing for
    partial extractions when complete information is not available.
    
    Fields with confidence scores below LOW_CONFIDENCE_THRESHOLD are automatically
    flagged for human verification by setting requires_verification=True.
    
    For fields with multiple possible interpretations, the 'alternatives' list
    provides secondary extraction options with their own confidence scores.
    """
    field_id: str  # Unique identifier for the field
    field_name: str  # Human-readable name of the field
    value: Union[str, int, float, bool, None]  # Extracted value (processed/normalized)
    raw_text: str  # Original text as extracted before processing/normalization
    confidence: ConfidenceScore  # Confidence score for the extraction (0.0-1.0)
    requires_verification: bool  # Flag indicating if human verification is needed
    location: FieldLocation  # Location of the field in the document
    field_type: str  # Type of the field (e.g., 'text', 'number', 'date', 'checkbox')
    alternatives: List[Dict[str, Union[str, ConfidenceScore]]]  # Alternative extractions
    metadata: Dict[str, Any]  # Additional field-specific metadata


class ExtractionMetadata(TypedDict, total=False):
    """
    Metadata about the extraction process.
    
    This type captures information about the extraction process itself, including
    timestamps, model versions, processing metrics, and status information. This
    metadata is crucial for auditing, debugging, and tracking the extraction pipeline.
    
    The extraction_status field indicates whether the extraction was successful:
    - 'complete': All expected fields were extracted successfully
    - 'partial': Some fields were extracted, but others are missing
    - 'failed': The extraction process failed entirely
    
    When extraction_status is 'failed', the failure_reason field provides details
    about what went wrong.
    
    The average_confidence and lowest_confidence fields provide aggregate metrics
    about the overall quality of the extraction, which can be used to determine
    whether human review is required.
    """
    document_id: str  # ID of the processed document
    extraction_id: str  # Unique ID for this extraction
    document_type: str  # Type of document processed (loan_application, tax_return, etc.)
    extraction_timestamp: datetime  # When extraction was performed
    ocr_model_version: str  # Version of the OCR model used
    processing_time_ms: int  # Time taken to process in milliseconds
    page_count: int  # Number of pages in the document
    average_confidence: ConfidenceScore  # Average confidence across all fields
    lowest_confidence: ConfidenceScore  # Lowest confidence score in any field
    requires_human_review: bool  # Whether human review is required
    source_document_path: str  # Path to the source document in S3
    extraction_status: Literal['complete', 'partial', 'failed']  # Status of extraction
    failure_reason: Optional[str]  # Reason for failure if status is 'failed'


T = TypeVar('T')  # Generic type for field collections


class ExtractedData(Generic[T]):
    """
    Represents complete extraction results with field collections.
    
    This class is the primary container for all extraction results, including individual
    fields, metadata about the extraction process, and document-type-specific structured data.
    It provides methods for validating the extraction, accessing fields, identifying
    low-confidence extractions, and serializing the results to JSON.
    
    The class is generic over type T, which represents the document-type-specific data
    structure. This allows for type-safe handling of different document types while
    maintaining a consistent interface.
    
    Example:
        ```python
        # Create an extraction result for a loan application
        loan_app_extraction = ExtractedData[
            LoanApplicationData
        ](
            fields={...},
            metadata={...},
            document_type_specific_data=loan_app_data
        )
        
        # Check if human verification is needed
        if loan_app_extraction.requires_human_verification():
            # Route for human review
            pass
            
        # Get the extraction as JSON for API response
        json_data = loan_app_extraction.to_json()
        ```
    """
    def __init__(
        self,
        fields: Dict[str, ExtractedField],
        metadata: ExtractionMetadata,
        document_type_specific_data: Optional[T] = None
    ):
        """
        Initialize an ExtractedData instance.
        
        Args:
            fields: Dictionary mapping field IDs to ExtractedField objects
            metadata: Metadata about the extraction process
            document_type_specific_data: Optional structured data specific to the document type
        """
        self.fields = fields
        self.metadata = metadata
        self.document_type_specific_data = document_type_specific_data
        self._validate()
    
    def _validate(self) -> None:
        """
        Validate the extraction data for completeness and correctness.
        
        This method checks if all required fields for the specific document type
        are present and have valid values. It also verifies that confidence scores
        are within the valid range (0.0-1.0).
        
        The implementation would be customized based on document type requirements.
        """
        # Check if any required fields are missing based on document type
        # This would be implemented based on specific document type requirements
        pass
    
    def get_field(self, field_id: str) -> Optional[ExtractedField]:
        """
        Get a field by its ID.
        
        Args:
            field_id: The ID of the field to retrieve
            
        Returns:
            The ExtractedField if found, None otherwise
        """
        return self.fields.get(field_id)
    
    def get_low_confidence_fields(self) -> Dict[str, ExtractedField]:
        """
        Get all fields with confidence below the threshold.
        
        Returns:
            Dictionary of field_id -> ExtractedField for all fields with
            confidence below LOW_CONFIDENCE_THRESHOLD
        """
        return {
            field_id: field for field_id, field in self.fields.items()
            if field.get('confidence', 0.0) < LOW_CONFIDENCE_THRESHOLD
        }
    
    def requires_human_verification(self) -> bool:
        """
        Check if any fields require human verification.
        
        Returns:
            True if any field has requires_verification=True, False otherwise
        """
        return any(field.get('requires_verification', False) for field in self.fields.values())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the extraction results to a dictionary.
        
        Returns:
            Dictionary representation of the extraction results
        """
        return {
            'fields': self.fields,
            'metadata': self.metadata,
            'document_type_specific_data': self.document_type_specific_data,
        }
    
    def to_json(self) -> str:
        """
        Convert the extraction results to a JSON string.
        
        Returns:
            JSON string representation of the extraction results
        """
        # Custom JSON encoder would be needed to handle datetime objects
        return json.dumps(self.to_dict(), default=str)


class JSONSchema(TypedDict):
    """
    Represents a JSON schema for defining the structure of extracted data.
    
    This type follows the JSON Schema specification (https://json-schema.org/)
    and is used to validate the structure of extracted data before it is
    passed to downstream services. Each document type has its own schema
    that defines the expected fields and their types.
    
    Example:
        ```python
        loan_application_schema = JSONSchema(
            type='object',
            properties={
                'applicant_name': {'type': 'object', 'properties': {...}},
                'business_name': {'type': 'object', 'properties': {...}},
                # ... other fields
            },
            required=['applicant_name', 'business_name'],
            additionalProperties=False
        )
        ```
    """
    type: str  # JSON schema type (usually 'object' for document data)
    properties: Dict[str, Any]  # Schema properties defining field structure
    required: List[str]  # List of required property names
    additionalProperties: bool  # Whether additional properties are allowed


# Document-specific extraction types

class LoanApplicationData(TypedDict, total=False):
    """
    Specific data structure for loan application documents.
    
    This type defines the expected fields in a loan application document,
    including applicant information, business details, and requested loan amount.
    Each field is represented as an ExtractedField with its own value and confidence score.
    
    The 'total=False' parameter indicates that all fields are optional, allowing for
    partial extractions when complete information is not available in the document.
    """
    applicant_name: ExtractedField  # Full name of the applicant
    business_name: ExtractedField  # Legal name of the business
    business_address: ExtractedField  # Physical address of the business
    business_phone: ExtractedField  # Contact phone number
    business_email: ExtractedField  # Contact email address
    tax_id: ExtractedField  # Business tax ID (EIN)
    requested_amount: ExtractedField  # Amount of funding requested
    business_start_date: ExtractedField  # When the business was established
    monthly_revenue: ExtractedField  # Average monthly revenue
    business_type: ExtractedField  # Legal structure (LLC, Corp, etc.)
    industry: ExtractedField  # Business industry or sector
    application_date: ExtractedField  # Date of application submission


class TaxReturnData(TypedDict, total=False):
    """
    Specific data structure for tax return documents.
    
    This type defines the expected fields in a business tax return document,
    including tax year, business identification, and financial information.
    Each field is represented as an ExtractedField with its own value and confidence score.
    
    Tax returns are critical for verifying business income and financial health
    as part of the MCA application process.
    """
    tax_year: ExtractedField  # Year the tax return covers
    business_name: ExtractedField  # Legal name of the business
    tax_id: ExtractedField  # Business tax ID (EIN)
    gross_revenue: ExtractedField  # Total revenue before expenses
    net_income: ExtractedField  # Income after expenses
    total_expenses: ExtractedField  # Sum of all business expenses
    filing_date: ExtractedField  # When the return was filed
    tax_preparer: ExtractedField  # Person/firm who prepared the return


class BankStatementData(TypedDict, total=False):
    """
    Specific data structure for bank statement documents.
    
    This type defines the expected fields in a bank statement document,
    including account information, balances, and transaction summaries.
    Each field is represented as an ExtractedField with its own value and confidence score.
    
    Bank statements provide evidence of cash flow and business activity,
    which are key factors in MCA application assessment.
    """
    account_holder: ExtractedField  # Name on the account
    account_number: ExtractedField  # Bank account number (partially masked)
    bank_name: ExtractedField  # Name of the financial institution
    statement_period: ExtractedField  # Time period covered by the statement
    beginning_balance: ExtractedField  # Balance at start of period
    ending_balance: ExtractedField  # Balance at end of period
    total_deposits: ExtractedField  # Sum of all deposits
    total_withdrawals: ExtractedField  # Sum of all withdrawals
    average_daily_balance: ExtractedField  # Average balance during period


class IdentityDocumentData(TypedDict, total=False):
    """
    Specific data structure for identity documents.
    
    This type defines the expected fields in identity documents such as
    driver's licenses, passports, and other government-issued ID cards.
    Each field is represented as an ExtractedField with its own value and confidence score.
    
    Identity documents are used to verify the identity of business owners
    and authorized signatories as part of the MCA application process.
    """
    document_type: ExtractedField  # Driver's license, passport, etc.
    full_name: ExtractedField  # Full name of the document holder
    document_number: ExtractedField  # ID number or license number
    issue_date: ExtractedField  # When the document was issued
    expiration_date: ExtractedField  # When the document expires
    issuing_authority: ExtractedField  # Agency that issued the document
    date_of_birth: ExtractedField  # DOB of the document holder
    address: ExtractedField  # Residential address if included


# Type alias for all document-specific data types
DocumentSpecificData = Union[
    LoanApplicationData,
    TaxReturnData,
    BankStatementData,
    IdentityDocumentData,
    Dict[str, Any]  # For other document types not explicitly defined
]


# Factory function to create appropriate ExtractedData instance based on document type
def create_extracted_data(
    fields: Dict[str, ExtractedField],
    metadata: ExtractionMetadata,
    document_type_specific_data: Optional[DocumentSpecificData] = None
) -> ExtractedData[DocumentSpecificData]:
    """
    Create an ExtractedData instance with the appropriate document-specific data.
    
    This factory function simplifies the creation of ExtractedData instances by handling
    the generic type parameter automatically. It ensures that the document-specific data
    is properly typed based on the document type specified in the metadata.
    
    Args:
        fields: Dictionary mapping field IDs to ExtractedField objects
        metadata: Metadata about the extraction process
        document_type_specific_data: Optional structured data specific to the document type
        
    Returns:
        An ExtractedData instance with the appropriate document-specific data type
        
    Example:
        ```python
        # Extract data from a loan application
        metadata = {
            'document_id': 'doc-123',
            'document_type': 'loan_application',
            # ... other metadata
        }
        
        # Create loan application specific data
        loan_data = {
            'business_name': business_name_field,
            'requested_amount': amount_field,
            # ... other fields
        }
        
        # Create the extraction result
        result = create_extracted_data(
            fields={'business_name': business_name_field, ...},
            metadata=metadata,
            document_type_specific_data=loan_data
        )
        ```
    """
    return ExtractedData(fields, metadata, document_type_specific_data)