# Typed Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract information from typed/printed text documents with 99% accuracy. These test documents are used to verify the performance of the TensorFlow-based OCR models specifically optimized for machine-printed text commonly found in merchant cash advance (MCA) applications and supporting documents.

## Purpose

The test data in this directory serves several critical purposes:

1. **Model Validation**: Verify that the OCR Service can accurately extract text from typed documents with the required 99% accuracy as specified in section 0.1.1 of the technical specification
2. **Regression Testing**: Ensure that model updates or code changes don't reduce extraction accuracy
3. **Performance Benchmarking**: Measure processing time to ensure applications are processed within the 5-minute requirement as mandated in the technical specification
4. **Edge Case Handling**: Test the system's ability to handle documents with varying quality, formats, and content
5. **Field Extraction Testing**: Validate the extraction of specific fields (business names, amounts, dates, etc.) from structured documents
6. **Integration Testing**: Verify that the OCR Service properly integrates with the Document Service for classification-based processing
7. **Confidence Scoring**: Test the accuracy of confidence scores to ensure proper flagging of uncertain extractions for human verification

## Directory Structure

The typed_documents directory is organized into the following structure:

```
typed_documents/
├── README.md                    # This documentation file
├── sample_manifest.json         # Master manifest of all typed document samples
├── financial_documents/         # Financial document test samples
│   ├── README.md                # Financial documents documentation
│   ├── financial_documents_manifest.json  # Financial document test specifications
│   └── .gitignore               # Git ignore rules for binary files
├── invoices/                    # Invoice document test samples
│   ├── README.md                # Invoice documentation
│   └── invoices_manifest.json   # Invoice test specifications
└── quality_variations/          # Documents with varying quality levels
    ├── README.md                # Quality variations documentation
    ├── high_quality_manifest.json  # High-quality document specifications
    ├── low_quality_manifest.json   # Low-quality document specifications
    └── .gitignore               # Git ignore rules for binary files
```

## Document Types

This test directory includes the following types of typed documents:

### Application Forms
- Merchant Cash Advance applications
- Business loan applications
- Credit applications
- Funding request forms

### Financial Documents
- Tax returns (1040, 1065, 1120, etc.)
- Bank statements
- Profit and loss statements
- Balance sheets
- Cash flow statements

### Invoices and Receipts
- Vendor invoices
- Service invoices
- Purchase orders
- Receipts
- Bills of lading

### Identity Documents
- Business licenses
- Articles of incorporation
- EIN confirmation letters
- Business registration certificates

## Quality Variations

To test the robustness of the OCR system, documents are provided in three quality levels. These variations are critical for ensuring the OCR Service can achieve the required 99% accuracy across a range of real-world document conditions.

### High Quality
- Resolution: 300+ DPI (400-600 DPI for documents with small fonts below 10pt)
- Contrast: Strong, clear text against background with optimal brightness (around 50%)
- Noise: Minimal to none, clean background without patterns or artifacts
- Document condition: No skew, perfectly aligned text, no damage or discoloration
- Font characteristics: Standard fonts (Arial, Times New Roman, Calibri) at 10pt or larger
- Format: Digital native or high-quality scan with proper lighting
- Expected OCR accuracy: 99-100%

### Medium Quality
- Resolution: 150-300 DPI
- Contrast: Good but may have some inconsistencies or slight variations in brightness
- Noise: Some noise or minor artifacts present, slight background patterns
- Document condition: Minimal skew (less than 2 degrees), slight fading or minor creases
- Font characteristics: Mix of standard and less common fonts, some size variations
- Format: Good quality scan or photo with adequate lighting
- Expected OCR accuracy: 95-98%

### Low Quality
- Resolution: Below 150 DPI
- Contrast: Poor, faded text, or low contrast between text and background
- Noise: Significant noise, artifacts, or distortions, prominent background patterns
- Document condition: Noticeable skew (2-5 degrees), visible damage, wrinkles, or discoloration
- Font characteristics: Unusual fonts, very small text (below 8pt), inconsistent font usage
- Format: Poor scan, photo with shadows or glare, or fax transmission
- Expected OCR accuracy: 85-95%

These quality variations allow for comprehensive testing of the OCR Service's ability to handle documents across the quality spectrum, ensuring it meets the 99% accuracy requirement for high-quality documents while maintaining acceptable performance for lower quality inputs.

## Manifest Files

Each subdirectory contains a manifest JSON file that defines the test documents and their expected OCR extraction results. These manifests are used for automated validation of OCR accuracy. The manifest files follow this structure:

```json
{
  "document_id": {
    "file_path": "relative/path/to/document.pdf",
    "document_type": "application_form",
    "quality": "high",
    "characteristics": {
      "resolution": 300,
      "contrast": "high",
      "noise_level": "low",
      "orientation": "portrait"
    },
    "expected_text": {
      "full_text": "Sample of expected text content...",
      "fields": {
        "business_name": {
          "value": "ABC Corporation",
          "confidence_threshold": 0.95,
          "location": {
            "page": 0,
            "top": 0.1,
            "left": 0.2,
            "bottom": 0.15,
            "right": 0.8
          }
        },
        "tax_id": {
          "value": "12-3456789",
          "confidence_threshold": 0.98,
          "location": {
            "page": 0,
            "top": 0.2,
            "left": 0.5,
            "bottom": 0.25,
            "right": 0.7
          }
        }
      }
    }
  }
}
```

## File Naming Conventions

Test documents follow this naming convention:

```
[document_type]_[subtype]_[quality]_[variant].[extension]
```

Examples:
- `application_mca_high_001.pdf` - High-quality MCA application, variant 1
- `tax_return_1120_medium_002.pdf` - Medium-quality 1120 tax return, variant 2
- `bank_statement_chase_low_001.pdf` - Low-quality Chase bank statement, variant 1
- `invoice_vendor_high_003.pdf` - High-quality vendor invoice, variant 3

## Using Test Documents

### For Manual Testing

1. Select appropriate test documents based on the test scenario
2. Process the documents through the OCR Service
3. Compare the extracted text and fields with the expected results in the manifest
4. Verify extraction accuracy and confidence scores
5. Evaluate processing time to ensure it meets the 5-minute requirement
6. Check field extraction accuracy against known values in the manifest
7. Verify proper handling of documents with varying quality levels

### For Automated Testing

```python
# Example test code
from ocr_service.models.typed_text_model import TypedTextModel
from ocr_service.utils.testing import load_test_document, load_manifest

def test_typed_document_extraction():
    # Load test document and its expected results
    document_id = "application_mca_high_001"
    document_path = "typed_documents/application_mca_high_001.pdf"
    manifest = load_manifest("typed_documents/sample_manifest.json")
    expected = manifest[document_id]["expected_text"]
    
    # Load document content
    document_content, document_metadata = load_test_document(document_path)
    
    # Initialize OCR model
    model = TypedTextModel(model_path="/path/to/model")
    
    # Process document
    preprocessed_image = model.preprocess_document(document_content, document_metadata)
    extracted_text = model.extract_text(preprocessed_image)
    extracted_fields = model.extract_fields(preprocessed_image, document_metadata)
    
    # Validate results
    assert len(extracted_text) > 0, "No text extracted"
    
    # Check field extraction accuracy
    for field_name, expected_field in expected["fields"].items():
        matching_fields = [f for f in extracted_fields if f["field_id"] == field_name]
        assert len(matching_fields) > 0, f"Field {field_name} not extracted"
        
        extracted_field = matching_fields[0]
        assert extracted_field["value"] == expected_field["value"], \
            f"Field {field_name} value mismatch: expected {expected_field['value']}, got {extracted_field['value']}"
        
        assert extracted_field["confidence"] >= expected_field["confidence_threshold"], \
            f"Field {field_name} confidence below threshold: expected {expected_field['confidence_threshold']}, got {extracted_field['confidence']}"
```

## Guidelines for Adding New Test Documents

1. **Document Selection**: Choose documents that represent real-world examples encountered in MCA processing
2. **Anonymization**: Ensure all PII (Personally Identifiable Information) is anonymized or replaced with fictional data
3. **Quality Variation**: Include variations in quality to test robustness
4. **Manifest Updates**: Add entries to the appropriate manifest file with expected extraction results
5. **Validation**: Manually verify that the OCR system can extract the expected text and fields
6. **Documentation**: Update relevant README files if adding new document types

### Steps to Add a New Test Document

1. Name the document according to the naming convention
2. Place the document in the appropriate subdirectory
3. Process the document through the OCR system to get baseline results
4. Create or update the manifest entry with expected extraction results
5. Add automated tests for the new document

## Binary Files Handling

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control to prevent repository bloat. The `.gitignore` files in each directory ensure that only metadata and configuration files are tracked.

To obtain the actual test documents:

1. Access the shared document repository at `s3://mca-documents-staging/test-data/`
2. Download the required documents to your local test environment
3. Place them in the corresponding directories according to the manifest structure

Alternatively, you can generate synthetic test documents using the document generation scripts in the `ocr-service/scripts/generate_test_data` directory.

## Performance Expectations

The OCR Service is expected to process typed documents with the following performance characteristics:

- **Accuracy**: 99% for high-quality documents, 95%+ for medium-quality, 85%+ for low-quality
- **Processing Time**: Under 5 seconds per page for typed documents to meet the overall 5-minute application processing requirement
- **Field Extraction**: Correctly identify and extract all fields defined in the manifest with proper field type recognition
- **Confidence Scoring**: Provide accurate confidence scores that correlate with extraction accuracy
- **Error Handling**: Properly flag low-confidence extractions for human verification
- **Robustness**: Maintain consistent performance across different document types and quality variations

These performance metrics are aligned with the project requirements specified in section 0.1.1 of the technical specification, which mandates 99% data extraction accuracy through AI and machine learning, and processing applications in under 5 minutes from receipt to completion.

## Related Documentation

- [OCR Service Architecture](../../README.md)
- [TypedTextModel Documentation](../../src/models/typed_text_model.py)
- [Testing Strategy](../../docs/testing_strategy.md)
- [Document Classification Guide](../../../document-service/docs/classification_guide.md)