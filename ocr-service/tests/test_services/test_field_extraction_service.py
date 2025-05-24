import pytest
import json
import re
from unittest.mock import MagicMock, patch

# Import the service and types
from services.field_extraction_service import FieldExtractionService
from types.extraction import ExtractedField, ConfidenceScore, ExtractedData, FieldLocation, ExtractionMetadata, JSONSchema
from types.models import ModelResult, OCRModelType
from types.errors import ServiceError, ErrorCategory, Result
from models.structure_recognition_model import StructureRecognitionModel

# Test class for FieldExtractionService
class TestFieldExtractionService:
    """Unit tests for the field extraction service.
    
    These tests verify the field extraction service's ability to:
    1. Recognize document structure (forms, tables, sections)
    2. Extract key-value pairs from OCR results
    3. Normalize and standardize field values
    4. Apply document type-specific extraction rules
    5. Format extracted data as JSON
    6. Validate and correct extracted fields
    
    The tests use mock data and fixtures to simulate different document types
    and OCR results, ensuring the service correctly transforms raw OCR text into
    structured data according to document-specific templates.
    """
    
    @pytest.fixture
    def field_extraction_config(self):
        """Create a configuration for the field extraction service."""
        return {
            "confidence_threshold": 0.7,
            "enable_validation": True,
            "enable_normalization": True,
            "templates_path": "/path/to/templates"
        }
    
    @pytest.fixture
    def mock_structure_model(self):
        """Create a mock structure recognition model."""
        model = MagicMock(spec=StructureRecognitionModel)
        model.recognize.return_value = {
            "form_regions": [
                {
                    "name": "business_info_form",
                    "fields": [
                        {
                            "label_end_idx": 15,
                            "start_idx": 0,
                            "end_idx": 40,
                            "x": 0.1,
                            "y": 0.1,
                            "width": 0.5,
                            "height": 0.05,
                            "page": 0
                        },
                        {
                            "label_end_idx": 8,
                            "start_idx": 41,
                            "end_idx": 60,
                            "x": 0.1,
                            "y": 0.2,
                            "width": 0.3,
                            "height": 0.05,
                            "page": 0
                        }
                    ],
                    "x": 0.05,
                    "y": 0.05,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0,
                    "start_idx": 0,
                    "end_idx": 100
                }
            ],
            "table_regions": [
                {
                    "name": "financial_table",
                    "header_row": {
                        "start_idx": 0,
                        "end_idx": 40
                    },
                    "rows": [
                        {
                            "start_idx": 41,
                            "end_idx": 80,
                            "cells": [
                                {"start_idx": 0, "end_idx": 10, "column_index": 0},
                                {"start_idx": 11, "end_idx": 20, "column_index": 1},
                                {"start_idx": 21, "end_idx": 30, "column_index": 2},
                                {"start_idx": 31, "end_idx": 40, "column_index": 3}
                            ],
                            "x": 0.1,
                            "y": 0.4,
                            "width": 0.8,
                            "height": 0.05
                        }
                    ],
                    "column_count": 4,
                    "x": 0.1,
                    "y": 0.35,
                    "width": 0.8,
                    "height": 0.2,
                    "page": 0,
                    "start_idx": 100,
                    "end_idx": 250
                }
            ],
            "section_regions": [
                {
                    "title_end_idx": 22,
                    "start_idx": 0,
                    "end_idx": 100,
                    "x": 0.05,
                    "y": 0.05,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0
                },
                {
                    "title_end_idx": 23,
                    "start_idx": 101,
                    "end_idx": 250,
                    "x": 0.05,
                    "y": 0.35,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0
                }
            ]
        }
        return model
    
    @pytest.fixture
    def field_extraction_service(self, field_extraction_config, mock_structure_model):
        """Create a field extraction service instance for testing."""
        with patch('services.field_extraction_service.StructureRecognitionModel', return_value=mock_structure_model):
            service = FieldExtractionService(field_extraction_config)
            # Replace the private methods with mocks for testing
            service._load_extraction_templates = MagicMock(return_value={
                "loan_application": {
                    "field_mapping": {
                        "Business Name": "business_name",
                        "Tax ID": "tax_id",
                        "Business Address": "business_address",
                        "Phone": "business_phone",
                        "Email": "business_email",
                        "Years in Business": "years_in_business",
                        "Annual Revenue": "annual_revenue",
                        "Owner Name": "owner_name",
                        "Owner SSN": "owner_ssn",
                        "Owner Phone": "owner_phone",
                        "Owner Email": "owner_email"
                    }
                },
                "bank_statement": {
                    "field_mapping": {
                        "Account Number": "account_number",
                        "Account Holder": "account_holder",
                        "Bank Name": "bank_name",
                        "Beginning Balance": "beginning_balance",
                        "Ending Balance": "ending_balance"
                    }
                }
            })
            service._load_normalization_rules = MagicMock(return_value={
                "default": {
                    "date": {"type": "date", "format": "%Y-%m-%d"},
                    "phone": {"type": "phone", "format": "E.164"},
                    "email": {"type": "email"},
                    "ssn": {"type": "ssn", "format": "XXX-XX-XXXX"},
                    "tax_id": {"type": "tax_id", "format": "XX-XXXXXXX"},
                    "amount": {"type": "currency", "format": "USD"}
                },
                "loan_application": {
                    "business_phone": {"type": "phone", "format": "E.164"},
                    "owner_phone": {"type": "phone", "format": "E.164"},
                    "business_email": {"type": "email"},
                    "owner_email": {"type": "email"},
                    "owner_ssn": {"type": "ssn", "format": "XXX-XX-XXXX"},
                    "annual_revenue": {"type": "currency", "format": "USD"},
                    "years_in_business": {"type": "number", "format": "integer"}
                }
            })
            service._load_validation_rules = MagicMock(return_value={
                "default": {
                    "email": {
                        "type": "email",
                        "constraints": {
                            "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                        }
                    },
                    "phone": {
                        "type": "phone",
                        "constraints": {
                            "min_length": 10,
                            "max_length": 15
                        }
                    }
                },
                "loan_application": {
                    "tax_id": {
                        "type": "tax_id",
                        "constraints": {
                            "pattern": r"^\d{2}-\d{7}$|^\d{9}$"
                        }
                    },
                    "owner_ssn": {
                        "type": "ssn",
                        "constraints": {
                            "pattern": r"^\d{3}-\d{2}-\d{4}$|^\d{9}$"
                        }
                    }
                }
            })
            service._load_field_patterns = MagicMock(return_value={
                "default": {
                    "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
                    "phone": r"\(?(d{3})\)?[- ]?(d{3})[- ]?(d{4})",
                    "date": r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2})"
                },
                "loan_application": {
                    "business_name": r"Business\s+Name[:\s]+(.*?)(?=\n|$|\s{2,})",
                    "tax_id": r"(?:Tax\s+ID|EIN|Federal\s+Tax\s+ID)[:\s]+(\d{2}[-]?\d{7})",
                    "years_in_business": r"Years\s+in\s+Business[:\s]+(\d+)",
                    "annual_revenue": r"Annual\s+Revenue[:\s]+\$?([\d,]+\.?\d*)"
                }
            })
            return service
    
    @pytest.fixture
    def mock_ocr_result(self):
        """Create a mock OCR result for testing."""
        return ModelResult(
            text="Business Name: Acme Corporation\nTax ID: 12-3456789\nAddress: 123 Main St, Anytown, USA 12345\nPhone: (555) 123-4567\nEmail: contact@acmecorp.com",
            confidence=0.95,
            model_type=OCRModelType.TYPED,
            metadata={
                "page_count": 1,
                "orientation": "portrait",
                "language": "en"
            }
        )
    
    @pytest.fixture
    def mock_table_ocr_result(self):
        """Create a mock OCR result with table data for testing."""
        return ModelResult(
            text="Financial Statement\n\nMonth    Revenue    Expenses    Profit\nJanuary    $10,000    $7,500    $2,500\nFebruary    $12,000    $8,000    $4,000\nMarch    $15,000    $9,000    $6,000",
            confidence=0.92,
            model_type=OCRModelType.TYPED,
            metadata={
                "page_count": 1,
                "orientation": "portrait",
                "language": "en",
                "has_tables": True
            }
        )
    
    @pytest.fixture
    def mock_form_ocr_result(self):
        """Create a mock OCR result with form data for testing."""
        return ModelResult(
            text="LOAN APPLICATION FORM\n\nBusiness Information:\nBusiness Name: XYZ Enterprises\nTax ID: 98-7654321\nYears in Business: 5\nAnnual Revenue: $500,000\n\nOwner Information:\nOwner Name: Jane Doe\nOwner SSN: 123-45-6789\nOwner Phone: (555) 987-6543\nOwner Email: jane@xyzenterprises.com",
            confidence=0.90,
            model_type=OCRModelType.TYPED,
            metadata={
                "page_count": 1,
                "orientation": "portrait",
                "language": "en",
                "has_forms": True
            }
        )
    
    @pytest.fixture
    def mock_document_structure(self):
        """Create a mock document structure for testing."""
        return {
            "forms": [
                {
                    "name": "business_info_form",
                    "fields": [
                        {
                            "label": "Business Name",
                            "value": "Acme Corporation",
                            "x": 0.1,
                            "y": 0.1,
                            "width": 0.5,
                            "height": 0.05,
                            "page": 0
                        },
                        {
                            "label": "Tax ID",
                            "value": "12-3456789",
                            "x": 0.1,
                            "y": 0.2,
                            "width": 0.3,
                            "height": 0.05,
                            "page": 0
                        }
                    ],
                    "x": 0.05,
                    "y": 0.05,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0,
                    "start_idx": 0,
                    "end_idx": 100
                }
            ],
            "tables": [
                {
                    "name": "financial_table",
                    "headers": ["Month", "Revenue", "Expenses", "Profit"],
                    "rows": [
                        {
                            "text": "January    $10,000    $7,500    $2,500",
                            "cells": [
                                {"text": "January", "column_index": 0, "x": 0.1, "y": 0.4, "width": 0.2, "height": 0.05},
                                {"text": "$10,000", "column_index": 1, "x": 0.3, "y": 0.4, "width": 0.2, "height": 0.05},
                                {"text": "$7,500", "column_index": 2, "x": 0.5, "y": 0.4, "width": 0.2, "height": 0.05},
                                {"text": "$2,500", "column_index": 3, "x": 0.7, "y": 0.4, "width": 0.2, "height": 0.05}
                            ],
                            "start_idx": 150,
                            "end_idx": 200,
                            "x": 0.1,
                            "y": 0.4,
                            "width": 0.8,
                            "height": 0.05
                        }
                    ],
                    "column_count": 4,
                    "row_count": 1,
                    "header_row": {
                        "start_idx": 100,
                        "end_idx": 150
                    },
                    "x": 0.1,
                    "y": 0.35,
                    "width": 0.8,
                    "height": 0.2,
                    "page": 0,
                    "start_idx": 100,
                    "end_idx": 250
                }
            ],
            "sections": [
                {
                    "title": "Business Information",
                    "content": "Business Name: Acme Corporation\nTax ID: 12-3456789",
                    "x": 0.05,
                    "y": 0.05,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0,
                    "start_idx": 0,
                    "end_idx": 100
                },
                {
                    "title": "Financial Information",
                    "content": "Month    Revenue    Expenses    Profit\nJanuary    $10,000    $7,500    $2,500",
                    "x": 0.05,
                    "y": 0.35,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0,
                    "start_idx": 100,
                    "end_idx": 250
                }
            ],
            "page_count": 1,
            "orientation": "portrait",
            "language": "en"
        }
        
    def test_recognize_structure(self, field_extraction_service, mock_ocr_result):
        """Test the structure recognition functionality.
        
        This test verifies that the field extraction service correctly identifies
        document structure elements including forms, tables, and sections.
        """
        # Call the recognize_structure method
        result = field_extraction_service.recognize_structure(mock_ocr_result, "loan_application")
        
        # Verify the result is not an error
        assert not isinstance(result, ServiceError)
        
        # Verify the structure contains the expected elements
        assert "forms" in result
        assert "tables" in result
        assert "sections" in result
        assert "page_count" in result
        assert "orientation" in result
        assert "language" in result
        
        # Verify the page count and orientation match the input
        assert result["page_count"] == mock_ocr_result.metadata["page_count"]
        assert result["orientation"] == mock_ocr_result.metadata["orientation"]
        assert result["language"] == mock_ocr_result.metadata["language"]
    
    def test_extract_key_value_pairs(self, field_extraction_service, mock_ocr_result):
        """Test the key-value pair extraction functionality.
        
        This test verifies that the field extraction service correctly extracts
        key-value pairs from OCR text using both general patterns and document-specific
        patterns.
        """
        # Call the extract_key_value_pairs method
        result = field_extraction_service.extract_key_value_pairs(
            mock_ocr_result.text, "loan_application"
        )
        
        # Verify the result contains the expected key-value pairs
        assert len(result) > 0
        
        # Create a dictionary of extracted key-value pairs for easier testing
        extracted_pairs = {key: value for key, value, _ in result}
        
        # Verify specific key-value pairs were extracted
        assert "Business Name" in extracted_pairs
        assert extracted_pairs["Business Name"] == "Acme Corporation"
        assert "Tax ID" in extracted_pairs
        assert extracted_pairs["Tax ID"] == "12-3456789"
        assert "Address" in extracted_pairs
        assert "Phone" in extracted_pairs
        assert "Email" in extracted_pairs
        
        # Verify confidence scores are included
        for _, _, confidence in result:
            assert isinstance(confidence, ConfidenceScore)
            assert 0.0 <= confidence.value <= 1.0
    
    def test_extract_table_data(self, field_extraction_service, mock_table_ocr_result):
        """Test the table data extraction functionality.
        
        This test verifies that the field extraction service correctly extracts
        structured data from tables identified in the document.
        """
        # Mock the document structure with a table
        table_structure = {
            "name": "financial_table",
            "headers": ["Month", "Revenue", "Expenses", "Profit"],
            "rows": [
                {
                    "start_idx": 0,
                    "end_idx": 50,
                    "cells": [
                        {"column_index": 0, "text": "January"},
                        {"column_index": 1, "text": "$10,000"},
                        {"column_index": 2, "text": "$7,500"},
                        {"column_index": 3, "text": "$2,500"}
                    ]
                },
                {
                    "start_idx": 51,
                    "end_idx": 100,
                    "cells": [
                        {"column_index": 0, "text": "February"},
                        {"column_index": 1, "text": "$12,000"},
                        {"column_index": 2, "text": "$8,000"},
                        {"column_index": 3, "text": "$4,000"}
                    ]
                }
            ],
            "start_idx": 0,
            "end_idx": 200
        }
        
        # Call the extract_table_data method
        result = field_extraction_service.extract_table_data(
            table_structure, mock_table_ocr_result.text
        )
        
        # Verify the result contains the expected table data
        assert len(result) > 0
        
        # Verify the structure of the extracted table data
        for row in result:
            assert isinstance(row, dict)
            # Check that each row has values for all headers
            for header in table_structure["headers"]:
                assert header in row
    
    @patch('services.field_extraction_service.FieldExtractionService._extract_fields_by_document_type')
    def test_extract_structured_data(self, mock_extract_fields, field_extraction_service, mock_ocr_result, mock_document_structure):
        """Test the structured data extraction functionality.
        
        This test verifies that the field extraction service correctly extracts
        structured data from OCR results based on document type, including field
        normalization, validation, and JSON formatting.
        """
        # Setup the mock to return a list of extracted fields
        mock_fields = [
            ExtractedField(
                name="business_name",
                value="Acme Corporation",
                confidence=ConfidenceScore(0.98),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            ),
            ExtractedField(
                name="tax_id",
                value="12-3456789",
                confidence=ConfidenceScore(0.97),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            ),
            ExtractedField(
                name="business_address",
                value="123 Main St, Anytown, USA 12345",
                confidence=ConfidenceScore(0.95),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            )
        ]
        mock_extract_fields.return_value = mock_fields
        
        # Mock the recognize_structure method to return the mock document structure
        field_extraction_service.recognize_structure = MagicMock(return_value=mock_document_structure)
        
        # Call the extract_structured_data method
        result = field_extraction_service.extract_structured_data(
            mock_ocr_result, "loan_application"
        )
        
        # Verify the result is not an error
        assert not isinstance(result, ServiceError)
        
        # Verify the result is an ExtractedData object
        assert isinstance(result, ExtractedData)
        
        # Verify the structure of the extracted data
        assert "data" in result.__dict__
        assert "metadata" in result.__dict__
        assert "schema" in result.__dict__
        
        # Verify the metadata contains the expected fields
        assert "document_type" in result.metadata
        assert result.metadata["document_type"] == "loan_application"
        assert "field_count" in result.metadata
        assert "average_confidence" in result.metadata
        
        # Verify the extract_fields_by_document_type method was called with the correct arguments
        mock_extract_fields.assert_called_once_with(
            mock_ocr_result, mock_document_structure, "loan_application"
        )
    
    def test_field_normalization(self, field_extraction_service):
        """Test the field normalization functionality.
        
        This test verifies that the field extraction service correctly normalizes
        and standardizes field values based on field type and document type.
        """
        # Create test fields with values that need normalization
        test_fields = [
            ExtractedField(
                name="business_phone",
                value="(555) 123-4567",
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            ),
            ExtractedField(
                name="business_email",
                value="CONTACT@acmecorp.com ",  # Uppercase and trailing space
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            ),
            ExtractedField(
                name="annual_revenue",
                value="$500,000",
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            )
        ]
        
        # Call the _normalize_fields method
        normalized_fields = field_extraction_service._normalize_fields(
            test_fields, "loan_application"
        )
        
        # Verify the fields were normalized correctly
        assert len(normalized_fields) == len(test_fields)
        
        # Check phone normalization
        phone_field = next(f for f in normalized_fields if f.name == "business_phone")
        assert "original_value" in phone_field.metadata
        assert phone_field.metadata["original_value"] == "(555) 123-4567"
        assert phone_field.metadata["normalized"] == True
        
        # Check email normalization
        email_field = next(f for f in normalized_fields if f.name == "business_email")
        assert "original_value" in email_field.metadata
        assert email_field.metadata["original_value"] == "CONTACT@acmecorp.com "
        assert email_field.value == "contact@acmecorp.com"  # Lowercase and trimmed
        assert email_field.metadata["normalized"] == True
        
        # Check currency normalization
        revenue_field = next(f for f in normalized_fields if f.name == "annual_revenue")
        assert "original_value" in revenue_field.metadata
        assert revenue_field.metadata["original_value"] == "$500,000"
        assert revenue_field.metadata["field_type"] == "currency"
        assert revenue_field.metadata["normalized"] == True
    
    def test_field_validation(self, field_extraction_service):
        """Test the field validation and error correction functionality.
        
        This test verifies that the field extraction service correctly validates
        extracted fields and attempts to correct errors based on field type and
        document type.
        """
        # Create test fields with values that need validation
        test_fields = [
            ExtractedField(
                name="business_email",
                value="contact@acmecorp.com",  # Valid email
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction", "field_type": "email"}
            ),
            ExtractedField(
                name="tax_id",
                value="123456789",  # Valid but not formatted
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction", "field_type": "tax_id"}
            ),
            ExtractedField(
                name="business_email",
                value="invalid-email",  # Invalid email
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction", "field_type": "email"}
            )
        ]
        
        # Call the _validate_fields method
        validated_fields = field_extraction_service._validate_fields(
            test_fields, "loan_application"
        )
        
        # Verify the fields were validated correctly
        assert len(validated_fields) == len(test_fields)
        
        # Check valid email validation
        valid_email = next(f for f in validated_fields if f.name == "business_email" and f.value == "contact@acmecorp.com")
        assert "validation_failed" not in valid_email.metadata
        
        # Check tax ID validation/correction
        tax_id = next(f for f in validated_fields if f.name == "tax_id")
        if "corrected" in tax_id.metadata and tax_id.metadata["corrected"]:
            assert tax_id.value == "12-3456789"  # Formatted as XX-XXXXXXX
            assert tax_id.metadata["original_value"] == "123456789"
        
        # Check invalid email validation
        invalid_email = next(f for f in validated_fields if f.name == "business_email" and f.value == "invalid-email")
        assert invalid_email.confidence.value <= 0.5  # Confidence reduced for invalid field
        assert "validation_failed" in invalid_email.metadata
        assert invalid_email.metadata["validation_failed"] == True
    
    def test_json_formatting(self, field_extraction_service):
        """Test the JSON formatting functionality.
        
        This test verifies that the field extraction service correctly formats
        extracted fields as JSON according to document type schema.
        """
        # Create test fields to format as JSON
        test_fields = [
            ExtractedField(
                name="business_name",
                value="Acme Corporation",
                confidence=ConfidenceScore(0.98),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction", "section": "business_information"}
            ),
            ExtractedField(
                name="tax_id",
                value="12-3456789",
                confidence=ConfidenceScore(0.97),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction", "section": "business_information"}
            ),
            ExtractedField(
                name="owner_name",
                value="John Doe",
                confidence=ConfidenceScore(0.95),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction", "section": "owner_information"}
            ),
            ExtractedField(
                name="financial_table",
                value=json.dumps([{"Month": "January", "Revenue": "$10,000"}]),
                confidence=ConfidenceScore(0.9),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "table_extraction", "is_table": True}
            )
        ]
        
        # Call the _format_as_json method
        formatted_data = field_extraction_service._format_as_json(
            test_fields, "loan_application"
        )
        
        # Verify the result is an ExtractedData object
        assert isinstance(formatted_data, ExtractedData)
        
        # Verify the data structure
        assert "data" in formatted_data.__dict__
        data = formatted_data.data
        
        # Verify sections are created correctly
        assert "business_information" in data
        assert "owner_information" in data
        
        # Verify fields are placed in the correct sections
        assert "business_name" in data["business_information"]
        assert "tax_id" in data["business_information"]
        assert "owner_name" in data["owner_information"]
        
        # Verify table data is included
        assert "tables" in data
        assert "financial_table" in data["tables"]
        
        # Verify metadata is included
        assert "metadata" in formatted_data.__dict__
        assert formatted_data.metadata["document_type"] == "loan_application"
        assert formatted_data.metadata["field_count"] == len(test_fields)
        
        # Verify schema is included
        assert "schema" in formatted_data.__dict__
        assert formatted_data.schema["schema_id"].startswith("mca-loan_application")
    
    def test_document_type_specific_extraction(self, field_extraction_service, mock_form_ocr_result):
        """Test document type-specific extraction rules.
        
        This test verifies that the field extraction service correctly applies
        document type-specific extraction rules and templates.
        """
        # Mock the document structure
        document_structure = {
            "sections": [
                {
                    "title": "Business Information",
                    "content": "Business Name: XYZ Enterprises\nTax ID: 98-7654321\nYears in Business: 5\nAnnual Revenue: $500,000",
                    "title_end_idx": 22,
                    "start_idx": 0,
                    "end_idx": 100,
                    "x": 0.05,
                    "y": 0.05,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0
                },
                {
                    "title": "Owner Information",
                    "content": "Owner Name: Jane Doe\nOwner SSN: 123-45-6789\nOwner Phone: (555) 987-6543\nOwner Email: jane@xyzenterprises.com",
                    "title_end_idx": 18,
                    "start_idx": 101,
                    "end_idx": 200,
                    "x": 0.05,
                    "y": 0.35,
                    "width": 0.9,
                    "height": 0.3,
                    "page": 0
                }
            ],
            "forms": [],
            "tables": [],
            "page_count": 1,
            "orientation": "portrait",
            "language": "en"
        }
        
        # Call the _extract_loan_application_fields method
        fields = field_extraction_service._extract_loan_application_fields(
            mock_form_ocr_result.text, document_structure
        )
        
        # Verify fields were extracted correctly
        assert len(fields) > 0
        
        # Check for specific fields
        field_names = [field.name for field in fields]
        assert "business_name" in field_names
        assert "tax_id" in field_names
        assert "years_in_business" in field_names
        assert "annual_revenue" in field_names
        
        # Verify field values
        business_name = next(f for f in fields if f.name == "business_name")
        assert business_name.value == "XYZ Enterprises"
        assert business_name.metadata["section"] == "business_information"
        
        # Verify owner information fields
        owner_fields = [f for f in fields if f.metadata.get("section") == "owner_information"]
        assert len(owner_fields) > 0
    
    def test_error_handling(self, field_extraction_service, mock_ocr_result):
        """Test error handling in the field extraction service.
        
        This test verifies that the field extraction service correctly handles
        errors and returns appropriate error objects.
        """
        # Mock the recognize_structure method to raise an exception
        field_extraction_service.recognize_structure = MagicMock(side_effect=Exception("Test error"))
        
        # Call the extract_structured_data method
        result = field_extraction_service.extract_structured_data(
            mock_ocr_result, "loan_application"
        )
        
        # Verify the result is a ServiceError
        assert isinstance(result, ServiceError)
        assert result.category == ErrorCategory.PROCESSING_ERROR
        assert "Test error" in result.message
    
    def test_deduplicate_fields(self, field_extraction_service):
        """Test field deduplication functionality.
        
        This test verifies that the field extraction service correctly deduplicates
        fields, preferring those with higher confidence.
        """
        # Create test fields with duplicates
        test_fields = [
            ExtractedField(
                name="business_name",
                value="Acme Corporation",
                confidence=ConfidenceScore(0.98),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            ),
            ExtractedField(
                name="business_name",  # Duplicate with lower confidence
                value="Acme Corp",
                confidence=ConfidenceScore(0.85),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "form_extraction"}
            ),
            ExtractedField(
                name="tax_id",
                value="12-3456789",
                confidence=ConfidenceScore(0.97),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "key_value_extraction"}
            ),
            ExtractedField(
                name="tax_id",  # Duplicate with higher confidence
                value="12-3456789",
                confidence=ConfidenceScore(0.99),
                location=FieldLocation(page=0, x=0, y=0, width=0, height=0),
                metadata={"source": "form_extraction"}
            )
        ]
        
        # Call the _deduplicate_fields method
        deduplicated_fields = field_extraction_service._deduplicate_fields(test_fields)
        
        # Verify fields were deduplicated correctly
        assert len(deduplicated_fields) == 2  # Should have one of each field name
        
        # Verify the highest confidence field was kept for each name
        business_name = next(f for f in deduplicated_fields if f.name == "business_name")
        assert business_name.value == "Acme Corporation"  # Higher confidence version
        assert business_name.confidence.value == 0.98
        
        tax_id = next(f for f in deduplicated_fields if f.name == "tax_id")
        assert tax_id.value == "12-3456789"
        assert tax_id.confidence.value == 0.99  # Higher confidence version
    
    def test_integration_extract_structured_data(self, field_extraction_service, mock_form_ocr_result):
        """Integration test for the extract_structured_data method.
        
        This test verifies the complete extraction pipeline from OCR result to
        structured data, including structure recognition, field extraction,
        normalization, validation, and JSON formatting.
        """
        # Call the extract_structured_data method with a loan application document
        result = field_extraction_service.extract_structured_data(
            mock_form_ocr_result, "loan_application"
        )
        
        # Verify the result is not an error
        assert not isinstance(result, ServiceError)
        
        # Verify the result is an ExtractedData object
        assert isinstance(result, ExtractedData)
        
        # Verify the data contains expected sections and fields
        data = result.data
        
        # Check for business information section
        assert any(section.startswith("business") for section in data.keys()) or "main" in data
        
        # Check for specific fields that should be extracted from the test document
        all_fields = []
        for section in data.values():
            if isinstance(section, dict):
                all_fields.extend(section.keys())
        
        # Verify key fields were extracted
        assert "business_name" in all_fields or "business_legal_name" in all_fields
        assert "tax_id" in all_fields
        
        # Verify metadata
        assert result.metadata["document_type"] == "loan_application"
        assert result.metadata["field_count"] > 0
        assert 0.0 <= result.metadata["average_confidence"] <= 1.0
        
        # Verify schema
        assert result.schema["schema_id"].startswith("mca-loan_application")
        assert result.schema["version"] is not None