# OCR Service Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract data from various document types with high accuracy. The test data is organized into categories based on document type and text characteristics, providing a comprehensive set of test cases for unit, integration, and performance testing.

The OCR Service is designed to achieve 99% data extraction accuracy through AI and machine learning, processing both typed and handwritten text as specified in the MCA Application Processing System requirements. This test data directory serves as the foundation for validating these capabilities.

## Directory Structure

The test data is organized into the following subdirectories:

```
test_data/
├── metadata.json                # Central metadata file for all test documents
├── typed_documents/             # Documents with machine-printed text
│   ├── application_forms/       # MCA application forms with typed content
│   ├── financial_documents/     # Financial statements, tax returns, bank statements
│   ├── business_documents/      # Invoices, contracts, business licenses
│   └── quality_variations/      # Documents with varying quality levels
├── handwritten_documents/       # Documents with handwritten text
│   ├── application_forms/       # MCA application forms with handwritten content
│   └── various styles/          # Documents with different handwriting styles
├── mixed_documents/             # Documents with both typed and handwritten content
│   ├── application_forms/       # Forms with typed fields and handwritten responses
│   └── annotated documents/     # Typed documents with handwritten annotations
├── tables/                      # Documents containing tabular data
│   ├── financial tables/        # Financial data in tabular format
│   └── complex tables/          # Tables with merged cells, multi-page tables
├── forms/                       # Blank form templates for structure recognition
└── images/                      # ID documents, photos with text
```

## Document Types

The test data includes the following document types, as defined in the `metadata.json` file:

- **APPLICATION_FORM**: MCA application forms with various fields
- **TAX_RETURN**: Business and personal tax returns
- **BANK_STATEMENT**: Bank account statements with transaction history
- **PAY_STUB**: Employee pay stubs with income information
- **ID_DOCUMENT**: Driver's licenses, passports, and other identification
- **INVOICE**: Business invoices and receipts
- **BUSINESS_DOCUMENT**: Business licenses, contracts, and agreements
- **FINANCIAL_DOCUMENT**: Financial statements, profit/loss reports
- **OTHER**: Miscellaneous document types

## Text Types

The test data covers three main text types:

- **TYPED**: Machine-printed text (expected OCR accuracy: 98%)
- **HANDWRITTEN**: Manually written text (expected OCR accuracy: 85%)
- **MIXED**: Documents containing both typed and handwritten text (expected OCR accuracy: 90%)

## Document Quality Levels

To test OCR robustness, documents are provided in three quality levels:

- **HIGH**: Clear, high-resolution documents (300+ DPI)
- **MEDIUM**: Average quality documents with minor issues
- **LOW**: Poor quality documents with artifacts, low resolution, or noise

## The `metadata.json` File

The `metadata.json` file is the central configuration file that defines all test documents, their characteristics, and expected OCR extraction results. It contains:

1. **Document metadata**: Type, text type, quality level, and description
2. **Expected fields**: Field names, values, positions, and expected confidence scores
3. **Expected classification confidence**: Target accuracy for document classification
4. **Expected overall confidence**: Target overall extraction accuracy
5. **Confidence thresholds**: Defined thresholds for automation vs. human review

Example structure:

```json
{
  "version": "1.0.0",
  "document_types": ["APPLICATION_FORM", "TAX_RETURN", ...],
  "text_types": ["TYPED", "HANDWRITTEN", "MIXED"],
  "quality_levels": ["HIGH", "MEDIUM", "LOW"],
  "documents": {
    "typed_documents": {
      "application_forms": [
        {
          "id": "app_form_typed_001",
          "file_path": "typed_documents/application_forms/mca_application_standard.pdf",
          "document_type": "APPLICATION_FORM",
          "text_type": "TYPED",
          "quality": "HIGH",
          "description": "Standard MCA application form with typed information",
          "expected_fields": {
            "business_name": {
              "value": "Acme Corporation",
              "position": {"x1": 120, "y1": 150, "x2": 350, "y2": 170},
              "expected_confidence": 0.98
            },
            // Additional fields...
          },
          "expected_classification_confidence": 0.99,
          "expected_overall_confidence": 0.98
        }
      ]
    }
  },
  "confidence_thresholds": {
    "high_confidence": 0.90,
    "medium_confidence": 0.75,
    "low_confidence": 0.60,
    "human_review_threshold": 0.75
  },
  "test_parameters": {
    "typed_text_accuracy_target": 0.98,
    "handwritten_text_accuracy_target": 0.85,
    "mixed_text_accuracy_target": 0.90,
    "classification_accuracy_target": 0.95,
    "field_extraction_accuracy_target": 0.95,
    "overall_accuracy_target": 0.93
  }
}
```

## Using Test Data in Tests

### Loading Test Documents

The test data can be loaded using the fixtures defined in `conftest.py`. Example:

```python
def test_typed_document_extraction(typed_application_form):
    # typed_application_form is a fixture that loads a test document
    ocr_service = OCRService()
    result = ocr_service.process_document(typed_application_form)
    
    # Verify extraction accuracy against expected values
    assert result.extracted_fields["business_name"] == "Acme Corporation"
    assert result.confidence_scores["business_name"] >= 0.95
```

### Testing Different Document Types

Test different document types to ensure the OCR service can handle various formats:

```python
@pytest.mark.parametrize("document_fixture", [
    "typed_application_form",
    "handwritten_application_form",
    "mixed_application_form",
    "bank_statement",
    "tax_return"
])
def test_document_classification(document_fixture, request):
    # Load the document fixture dynamically
    document = request.getfixturevalue(document_fixture)
    
    # Test document classification
    document_service = DocumentService()
    classification = document_service.classify_document(document)
    
    # Verify classification against expected document type
    expected_type = document.metadata["document_type"]
    assert classification.document_type == expected_type
    assert classification.confidence >= 0.95
```

### Testing OCR Accuracy

Test OCR accuracy against expected values defined in metadata:

```python
def test_ocr_accuracy(document_with_metadata):
    # Process document with OCR service
    ocr_service = OCRService()
    result = ocr_service.process_document(document_with_metadata)
    
    # Get expected values from metadata
    expected_fields = document_with_metadata.metadata["expected_fields"]
    
    # Verify each extracted field against expected values
    for field_name, expected in expected_fields.items():
        assert field_name in result.extracted_fields
        assert result.extracted_fields[field_name] == expected["value"]
        assert result.confidence_scores[field_name] >= expected["expected_confidence"]
```

## Performance Testing

The test data includes documents of varying complexity to test OCR performance:

```python
@pytest.mark.performance
def test_ocr_processing_time(document_with_metadata):
    # Process document with OCR service
    ocr_service = OCRService()
    
    # Measure processing time
    start_time = time.time()
    result = ocr_service.process_document(document_with_metadata)
    processing_time = time.time() - start_time
    
    # Verify processing time meets requirements
    # The system must process applications in under 5 minutes
    assert processing_time < 300  # seconds
```

## Expected OCR Accuracy

The OCR Service is expected to achieve the following accuracy levels:

| Document Type | Text Type | Quality | Expected Field Accuracy | Expected Overall Accuracy |
|---------------|-----------|---------|------------------------|---------------------------|
| Application Form | Typed | High | 98% | 98% |
| Application Form | Typed | Low | 85% | 84% |
| Application Form | Handwritten | Medium | 85% | 83% |
| Application Form | Handwritten | Low | 78% | 75% |
| Application Form | Mixed | High | 90% | 89% |
| Financial Document | Typed | High | 98% | 98% |
| Financial Document | Mixed | High | 92% | 92% |
| ID Document | Mixed | High | 95% | 93% |
| Table | Typed | High | 95% | 97% |

These accuracy targets are defined in the `test_parameters` section of `metadata.json` and are used to validate the OCR Service's performance.

## Adding New Test Documents

To add new test documents to the test data directory:

1. Place the document file in the appropriate subdirectory based on its type and text characteristics
2. Update the `metadata.json` file with the document's metadata and expected extraction results
3. Create a fixture in `conftest.py` to load the document for testing
4. Add test cases that use the new document to validate OCR functionality

Example metadata entry for a new document:

```json
{
  "id": "invoice_typed_002",
  "file_path": "typed_documents/business_documents/invoice_complex.pdf",
  "document_type": "INVOICE",
  "text_type": "TYPED",
  "quality": "MEDIUM",
  "description": "Complex business invoice with multiple line items",
  "expected_fields": {
    "invoice_number": {
      "value": "INV-2025-5678",
      "position": {"x1": 450, "y1": 150, "x2": 550, "y2": 170},
      "expected_confidence": 0.95
    },
    // Additional fields...
  },
  "expected_classification_confidence": 0.97,
  "expected_overall_confidence": 0.96
}
```

## Binary Files and Version Control

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control using `.gitignore` files in each subdirectory. This prevents large binary files from bloating the repository while maintaining necessary metadata.

To obtain the actual test documents:

1. Download them from the shared document repository (contact the OCR team for access)
2. Place them in the appropriate subdirectories according to the paths defined in `metadata.json`
3. Run the verification script to ensure all documents are correctly placed:

```bash
python -m ocr_service.tests.verify_test_data
```

## Test Data Maintenance

The test data should be regularly updated to include new document types, edge cases, and challenging scenarios. When updating the test data:

1. Maintain backward compatibility with existing tests
2. Update the `version` field in `metadata.json` when making significant changes
3. Document any changes in the appropriate README files
4. Ensure all new documents have complete metadata entries
5. Verify that the OCR Service can still achieve the required accuracy targets

## References

- OCR Service Implementation: `ocr-service/src/services/ocr_service.py`
- Model Implementations: `ocr-service/src/models/`
- Test Fixtures: `ocr-service/tests/conftest.py`
- Testing Strategy: Technical Specification Section 6.6