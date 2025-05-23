# Mixed Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract data from documents containing both typed and handwritten content. As specified in the MCA (Merchant Cash Advance) Application Processing System requirements, the OCR Service must achieve 99% data extraction accuracy through AI and machine learning, including for documents with mixed content types.

Mixed documents present unique challenges for OCR processing as they require the system to accurately identify, differentiate, and extract both machine-printed and handwritten text within the same document. These test samples are essential for validating the OCR Service's ability to handle real-world application documents that frequently contain both content types.

## Purpose

The primary purposes of this test data collection are:

1. **Validate Mixed Content Processing**: Ensure the OCR Service can accurately identify and process both typed and handwritten text within the same document
2. **Test Content Type Classification**: Verify the system's ability to distinguish between typed and handwritten content
3. **Evaluate Field Extraction Accuracy**: Test extraction of specific fields that may contain either content type
4. **Measure Confidence Scoring**: Validate that confidence scores accurately reflect extraction certainty for mixed content
5. **Support Regression Testing**: Prevent regressions in OCR accuracy when making changes to the service
6. **Benchmark Performance**: Establish baseline performance metrics for mixed document processing

## Directory Structure

The mixed_documents directory is organized as follows:

```
mixed_documents/
├── README.md                      # This documentation file
├── sample_manifest.json           # Master manifest of all mixed document test samples
├── .gitignore                     # Excludes binary document files from version control
├── application_forms/             # Application forms with both typed and handwritten content
│   ├── completed/                 # Fully completed application forms
│   └── partially_completed/       # Partially completed application forms
├── annotated_documents/           # Typed documents with handwritten annotations
│   ├── contracts/                 # Contracts with handwritten notes and signatures
│   ├── statements/                # Financial statements with handwritten markups
│   └── reports/                   # Reports with handwritten comments
├── forms_with_signatures/         # Typed forms with handwritten signatures
│   ├── authorization_forms/       # Authorization forms with signatures
│   └── consent_forms/             # Consent forms with signatures
└── quality_variations/            # Documents with varying quality levels
    ├── high_quality/              # Clear, well-formed mixed content
    ├── medium_quality/            # Average legibility mixed content
    └── low_quality/               # Challenging, difficult-to-read mixed content
```

## Document Types

This test data directory includes the following types of mixed content documents:

### 1. Application Forms

MCA application forms containing both typed and handwritten content, such as:
- Pre-printed forms with typed fields and handwritten responses
- Partially typed applications with handwritten additions or corrections
- Forms where some sections are typed and others are handwritten

These documents test the system's ability to extract structured information from form fields with mixed content types.

### 2. Annotated Documents

Typed documents with handwritten annotations, including:
- Contracts with handwritten notes, initials, or amendments
- Financial statements with handwritten calculations or markups
- Reports with handwritten comments or corrections
- Letters with handwritten postscripts or signatures

These documents test the system's ability to distinguish between the primary typed content and secondary handwritten annotations.

### 3. Forms with Signatures

Typed forms with handwritten signatures and dates, including:
- Authorization forms with signature fields
- Consent documents with signature blocks
- Agreements with multiple signature fields
- Forms with both signatures and handwritten dates

These documents test the system's ability to process critical handwritten elements within otherwise typed documents.

### 4. Quality Variations

Documents with varying quality levels to test OCR robustness:

1. **High Quality**:
   - Clear, well-formed typed and handwritten content
   - High contrast between text and background
   - Clean document with no artifacts
   - Expected OCR accuracy: 90-95%

2. **Medium Quality**:
   - Average legibility of typed and handwritten content
   - Some variation in contrast or print/pen quality
   - Minor artifacts or background noise
   - Expected OCR accuracy: 80-90%

3. **Low Quality**:
   - Difficult-to-read content (either typed, handwritten, or both)
   - Poor contrast, faded text, or low resolution
   - Significant artifacts, smudges, or background noise
   - Expected OCR accuracy: 70-80%

## Document Characteristics

Mixed documents in this collection vary across several dimensions:

1. **Content Distribution**: Ratio of typed to handwritten content (mostly typed with signatures, equal mix, mostly handwritten with typed headers)
2. **Content Arrangement**: How typed and handwritten content interact (separate sections, interleaved, overlapping)
3. **Field Types**: Various field types (text fields, checkboxes, signature blocks, free-form areas)
4. **Handwriting Styles**: Different handwriting styles within the same document
5. **Document Complexity**: Simple forms to complex multi-page documents with tables and varied layouts

## Challenges of Mixed Document Processing

Mixed documents present several unique challenges for OCR processing:

1. **Content Type Classification**: Accurately distinguishing between typed and handwritten text
2. **Varied Processing Requirements**: Applying different OCR techniques for each content type
3. **Contextual Understanding**: Determining which content represents the primary data vs. annotations
4. **Overlapping Content**: Processing areas where typed and handwritten content may overlap
5. **Confidence Scoring**: Providing accurate confidence scores for fields with mixed content types
6. **Performance Optimization**: Balancing processing time with accuracy for complex documents

## Naming Conventions

Test documents follow this naming convention:

```
[document_type]_[subtype]_[content_ratio]_[quality]_[variant].[extension]
```

Where:
- `document_type`: Indicates the document category (app_form, annotated, signed_form)
- `subtype`: Specifies the document subtype (consent, contract, statement, etc.)
- `content_ratio`: Indicates the approximate ratio of typed to handwritten content (mostly_typed, equal_mix, mostly_handwritten)
- `quality`: Indicates the document quality (high, medium, low)
- `variant`: A unique identifier number (001, 002, etc.)

Examples:
- `app_form_loan_mostly_typed_high_001.pdf`: High-quality loan application form that is mostly typed with some handwritten fields
- `annotated_contract_equal_mix_medium_002.tiff`: Medium-quality contract with roughly equal amounts of typed and handwritten content
- `signed_form_consent_mostly_typed_low_003.png`: Low-quality consent form that is mostly typed with handwritten signatures

## Manifest Files

The `sample_manifest.json` file provides a master reference of all test documents with detailed metadata including:

1. **Document Metadata**: File path, type, content ratio, quality level, and other attributes
2. **Content Regions**: Defined regions for typed and handwritten content
3. **Expected OCR Results**: The text content that should be extracted from each region
4. **Field Definitions**: Specific fields to extract with their expected values and content type
5. **Confidence Thresholds**: Minimum acceptable confidence scores for extraction
6. **Performance Metrics**: Expected processing time and resource usage

### Manifest Format Example

```json
{
  "document_id": "app_form_loan_mostly_typed_high_001",
  "file_path": "application_forms/completed/app_form_loan_mostly_typed_high_001.pdf",
  "document_type": "APPLICATION_FORM",
  "subtype": "LOAN",
  "content_ratio": "MOSTLY_TYPED",
  "quality": "HIGH",
  "description": "Loan application form with typed fields and handwritten responses",
  "content_regions": [
    {
      "id": "header",
      "content_type": "TYPED",
      "position": {"x1": 50, "y1": 50, "x2": 550, "y2": 150}
    },
    {
      "id": "applicant_info",
      "content_type": "HANDWRITTEN",
      "position": {"x1": 200, "y1": 200, "x2": 500, "y2": 300}
    }
  ],
  "expected_fields": {
    "business_name": {
      "value": "Acme Corporation",
      "content_type": "HANDWRITTEN",
      "position": {"x1": 200, "y1": 200, "x2": 400, "y2": 220},
      "min_confidence": 0.85
    },
    "loan_amount": {
      "value": "$50,000",
      "content_type": "HANDWRITTEN",
      "position": {"x1": 200, "y1": 250, "x2": 300, "y2": 270},
      "min_confidence": 0.90
    },
    "application_id": {
      "value": "LOAN-2023-12345",
      "content_type": "TYPED",
      "position": {"x1": 450, "y1": 100, "x2": 550, "y2": 120},
      "min_confidence": 0.95
    }
  },
  "performance_expectations": {
    "max_processing_time_ms": 3000,
    "min_overall_accuracy": 0.92,
    "min_typed_accuracy": 0.95,
    "min_handwritten_accuracy": 0.85
  }
}
```

## Using Test Documents

### For Manual Testing

1. Select appropriate test documents based on the testing scenario
2. Process the documents through the OCR Service
3. Compare the extraction results with the expected values in the manifest
4. Evaluate accuracy, confidence scores, and processing time for both typed and handwritten content
5. Verify that the system correctly identifies and differentiates between content types

### For Automated Testing

1. Use the manifest file to programmatically load test documents
2. Submit documents to the OCR Service API
3. Compare the API response with the expected values
4. Calculate accuracy metrics for both typed and handwritten content
5. Validate against the 99% overall accuracy requirement
6. Generate test reports with pass/fail status

### Example Test Code

```python
def test_mixed_document_extraction(mixed_document_fixture):
    # Get document and expected values from fixture
    document_path, expected_data = mixed_document_fixture
    
    # Process with OCR service
    ocr_service = OCRService()
    result = ocr_service.process_document(document_path)
    
    # Verify content type classification
    for region_id, region_data in expected_data["content_regions"].items():
        detected_type = result.content_regions[region_id]["detected_type"]
        assert detected_type == region_data["content_type"]
    
    # Verify field extraction for both typed and handwritten content
    typed_correct = 0
    typed_total = 0
    handwritten_correct = 0
    handwritten_total = 0
    
    for field_name, expected in expected_data["expected_fields"].items():
        extracted = result.extracted_fields[field_name]
        confidence = result.confidence_scores[field_name]
        
        # Check extraction accuracy
        is_correct = extracted == expected["value"]
        
        # Track accuracy by content type
        if expected["content_type"] == "TYPED":
            typed_total += 1
            if is_correct:
                typed_correct += 1
        else:  # HANDWRITTEN
            handwritten_total += 1
            if is_correct:
                handwritten_correct += 1
        
        # Verify confidence score meets minimum threshold
        assert confidence >= expected["min_confidence"]
    
    # Calculate accuracy metrics
    typed_accuracy = typed_correct / typed_total if typed_total > 0 else 1.0
    handwritten_accuracy = handwritten_correct / handwritten_total if handwritten_total > 0 else 1.0
    overall_accuracy = (typed_correct + handwritten_correct) / (typed_total + handwritten_total)
    
    # Verify accuracy meets requirements
    assert typed_accuracy >= expected_data["performance_expectations"]["min_typed_accuracy"]
    assert handwritten_accuracy >= expected_data["performance_expectations"]["min_handwritten_accuracy"]
    assert overall_accuracy >= expected_data["performance_expectations"]["min_overall_accuracy"]
```

## Expected Accuracy Metrics

The OCR Service is expected to achieve the following accuracy levels for mixed documents:

| Document Type | Content Ratio | Quality | Typed Content Accuracy | Handwritten Content Accuracy | Overall Accuracy |
|---------------|---------------|---------|------------------------|------------------------------|------------------|
| Application Form | Mostly Typed | High | 95-98% | 85-90% | 92-95% |
| Application Form | Equal Mix | High | 95-98% | 85-90% | 90-93% |
| Application Form | Mostly Handwritten | High | 95-98% | 85-90% | 87-92% |
| Annotated Document | Mostly Typed | High | 95-98% | 80-85% | 90-95% |
| Signed Form | Mostly Typed | High | 95-98% | 75-85% | 92-96% |
| Any Type | Any Ratio | Medium | 90-95% | 75-85% | 85-90% |
| Any Type | Any Ratio | Low | 85-90% | 65-75% | 75-85% |

These accuracy targets are defined to support the overall system requirement of 99% data extraction accuracy, recognizing that mixed documents present additional challenges compared to purely typed or handwritten documents.

## Guidelines for Adding New Test Documents

When adding new mixed document test samples:

1. **Follow the naming convention** described above
2. **Place the file** in the appropriate subdirectory based on document type and quality
3. **Add document metadata** to the sample_manifest.json file, including:
   - Document identification information
   - Content region definitions for typed and handwritten areas
   - Expected field values with content type specifications
   - Confidence thresholds based on content type and quality
   - Performance expectations
4. **Document any special characteristics** that might affect OCR performance
5. **Include the document in the .gitignore** to prevent binary files from being committed
6. **Store the actual document file** in the designated secure storage location

## Test Data Sources

Mixed document test samples come from the following sources:

1. **Synthetic Documents**: Generated specifically for testing purposes with controlled variations
2. **Anonymized Real Documents**: Real application documents with sensitive information removed
3. **Hybrid Documents**: Typed templates with handwritten content added for testing

## Relationship to OCR Service Requirements

This test data directly supports the following requirements from the technical specification:

1. **99% Data Extraction Accuracy**: Test documents validate the OCR Service's ability to achieve high accuracy across different content types
2. **Processing Time**: Tests verify that mixed documents can be processed within the required time limits
3. **Content Type Classification**: Tests confirm correct identification of typed vs. handwritten content
4. **Field Extraction**: Tests validate accurate extraction of specific fields with appropriate confidence scores

## Notes on Binary Files

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control to prevent repository bloat. The `.gitignore` file in this directory ensures that only metadata and configuration files are tracked.

To obtain the actual test documents, contact the project administrator or download them from the designated secure storage location.