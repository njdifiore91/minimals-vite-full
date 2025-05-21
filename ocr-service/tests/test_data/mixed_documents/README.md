# Mixed Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract data from documents that contain both typed and handwritten text. Mixed documents present unique challenges for OCR processing, requiring specialized hybrid approaches to achieve high accuracy across different text types within the same document.

The test data in this folder is critical for ensuring the OCR Service meets the 99% data extraction accuracy requirement specified in section 0.1.1 of the MCA Application Processing System technical specification, particularly for documents that combine multiple text types.

## Document Types

This folder contains the following types of mixed documents:

1. **Application Forms with Handwritten Entries**: Typed forms with handwritten responses in designated fields
2. **Typed Documents with Signatures**: Documents that are primarily typed but include handwritten signatures
3. **Annotated Documents**: Typed documents with handwritten notes, corrections, or annotations
4. **Forms with Checkboxes**: Documents with typed text and handwritten checkmarks or selections
5. **Financial Documents with Handwritten Updates**: Financial statements or invoices with handwritten modifications
6. **ID Documents with Handwritten Elements**: Identification documents containing both printed and handwritten information
7. **Correspondence with Handwritten Notes**: Letters or emails that have been printed and annotated by hand

## Challenges of Mixed Document Processing

Mixed documents present several unique challenges for OCR processing:

1. **Text Type Detection**: The system must accurately distinguish between typed and handwritten text within the same document
2. **Model Selection**: Different OCR models are optimal for different text types, requiring dynamic model selection or hybrid approaches
3. **Varying Confidence Levels**: Typed text typically yields higher confidence scores than handwritten text, requiring normalized confidence scoring
4. **Layout Complexity**: Handwritten annotations may not follow the document's structured layout, requiring flexible field detection
5. **Context Awareness**: Understanding the relationship between typed fields and handwritten responses requires contextual processing
6. **Quality Variations**: Handwritten portions may vary significantly in quality, style, and legibility compared to typed portions
7. **Field Boundary Detection**: Determining where typed text ends and handwritten text begins can be challenging

The OCR Service addresses these challenges through the Hybrid OCR approach described in section 4.1.8 of the technical specification, which dynamically applies appropriate models based on text type detection.

## Document Organization

Mixed documents in this folder are organized into subfolders based on their primary purpose:

```
mixed_documents/
├── application_forms/       # MCA application forms with typed fields and handwritten responses
├── annotated_documents/     # Typed documents with handwritten annotations or corrections
├── financial_documents/     # Financial statements with handwritten modifications
└── identity_documents/      # ID documents with both printed and handwritten elements
```

## Naming Conventions

Test files follow this naming convention:

```
mixed_{document_type}_{content_description}_{quality}_{id}.{extension}
```

Where:
- `document_type`: The primary document type (application, invoice, letter, etc.)
- `content_description`: Brief description of the document content
- `quality`: Image quality (high, medium, low)
- `id`: Unique identifier
- `extension`: File extension (pdf, tiff, png, jpg)

Examples:
- `mixed_application_standard_high_001.pdf`: High-quality standard application form with mixed content
- `mixed_invoice_annotated_medium_003.pdf`: Medium-quality invoice with handwritten annotations
- `mixed_letter_signed_low_002.pdf`: Low-quality letter with handwritten signature

## Expected OCR Accuracy

The OCR Service is expected to achieve the following accuracy levels for mixed documents:

| Document Type | Quality | Expected Field Accuracy | Expected Overall Accuracy |
|---------------|---------|------------------------|---------------------------|
| Application Form | High | 92% | 90% |
| Application Form | Medium | 88% | 85% |
| Application Form | Low | 82% | 80% |
| Financial Document | High | 94% | 92% |
| Financial Document | Medium | 90% | 87% |
| Annotated Document | High | 90% | 88% |
| ID Document | High | 95% | 93% |

These accuracy targets are defined in the `test_parameters` section of the central `metadata.json` file and are used to validate the OCR Service's performance on mixed documents.

## Using Mixed Document Test Data

### Loading Test Documents

Mixed document test data can be loaded using the fixtures defined in `conftest.py`. Example:

```python
def test_mixed_document_extraction(mixed_application_form):
    # mixed_application_form is a fixture that loads a test document
    ocr_service = OCRService()
    result = ocr_service.process_document(mixed_application_form)
    
    # Verify extraction accuracy against expected values
    assert result.extracted_fields["business_name"] == "Acme Corporation"
    assert result.extracted_fields["applicant_signature"] == "John Smith"
    assert result.confidence_scores["business_name"] >= 0.95  # Typed field
    assert result.confidence_scores["applicant_signature"] >= 0.85  # Handwritten field
```

### Testing Hybrid OCR Capabilities

Test the OCR service's ability to apply the appropriate model based on text type:

```python
def test_hybrid_ocr_model_selection(mixed_document_with_metadata):
    # Process document with OCR service
    ocr_service = OCRService()
    result = ocr_service.process_document(mixed_document_with_metadata)
    
    # Verify model selection for different text types
    assert result.model_selections["business_name"] == "typed_text_model"
    assert result.model_selections["applicant_signature"] == "handwritten_text_model"
    
    # Verify overall processing approach
    assert result.processing_approach == "hybrid"
```

## Adding New Test Documents

To add new mixed document test files to this directory:

1. Place the document file in the appropriate subdirectory based on its primary purpose
2. Follow the naming convention described above
3. Update the `sample_manifest.json` file with the document's metadata and expected extraction results
4. Add an entry to the central `metadata.json` file in the parent directory
5. Create a fixture in `conftest.py` if needed for specific testing scenarios

Example metadata entry for a new mixed document:

```json
{
  "id": "mixed_application_standard_high_005",
  "file_path": "mixed_documents/application_forms/mixed_application_standard_high_005.pdf",
  "document_type": "APPLICATION_FORM",
  "text_type": "MIXED",
  "quality": "HIGH",
  "description": "Standard MCA application form with typed fields and handwritten responses",
  "typed_fields": ["business_name", "business_address", "tax_id", "requested_amount"],
  "handwritten_fields": ["owner_name", "owner_signature", "date"],
  "expected_fields": {
    "business_name": {
      "value": "Summit Enterprises LLC",
      "position": {"x1": 120, "y1": 150, "x2": 350, "y2": 170},
      "expected_confidence": 0.98,
      "text_type": "TYPED"
    },
    "owner_signature": {
      "value": "Michael Johnson",
      "position": {"x1": 400, "y1": 550, "x2": 550, "y2": 580},
      "expected_confidence": 0.87,
      "text_type": "HANDWRITTEN"
    }
    // Additional fields...
  },
  "expected_classification_confidence": 0.97,
  "expected_overall_confidence": 0.92
}
```

## Binary Files and Version Control

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control using the `.gitignore` file in this directory. This prevents large binary files from bloating the repository while maintaining necessary metadata.

To obtain the actual test documents:

1. Download them from the shared document repository (contact the OCR team for access)
2. Place them in the appropriate subdirectories according to the paths defined in `sample_manifest.json`
3. Run the verification script to ensure all documents are correctly placed:

```bash
python -m ocr_service.tests.verify_test_data --folder mixed_documents
```

## Related Documentation

- Main test data documentation: `../README.md`
- Mixed document challenges: `mixed_document_challenges.md`
- Sample manifest: `sample_manifest.json`
- OCR Service implementation: `../../src/services/ocr_service.py`
- Hybrid text model: `../../src/models/hybrid_text_model.py`