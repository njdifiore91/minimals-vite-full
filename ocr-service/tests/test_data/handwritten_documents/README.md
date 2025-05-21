# Handwritten Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract data from handwritten documents with high accuracy. As specified in the MCA Application Processing System requirements, the OCR Service must achieve 99% data extraction accuracy through AI and machine learning, including for handwritten text.

The test samples in this directory represent a diverse range of handwritten document types, writing styles, and quality levels to ensure comprehensive testing of the OCR system's handwriting recognition capabilities. These samples are essential for validating the system's ability to process real-world handwritten mortgage application documents.

## Directory Structure

The handwritten documents test data is organized as follows:

```
handwritten_documents/
├── README.md                      # This documentation file
├── handwriting_styles.md          # Detailed catalog of handwriting styles
├── sample_manifest.json           # Configuration file defining test samples
├── .gitignore                     # Git configuration to exclude binary files
├── application_forms/             # Handwritten MCA application forms
│   ├── complete/                  # Fully completed application forms
│   └── partial/                   # Partially completed application forms
├── financial_information/         # Handwritten financial documents
│   ├── income_statements/         # Income declarations and statements
│   └── expense_records/           # Expense records and receipts
├── identification/                # Handwritten identification information
│   ├── signatures/                # Signature samples with variations
│   └── personal_information/      # Handwritten personal details
└── mixed_quality/                 # Documents with varying quality levels
    ├── high_quality/              # Clear, well-formed handwriting
    ├── medium_quality/            # Average legibility handwriting
    └── low_quality/               # Challenging, difficult-to-read handwriting
```

## Document Types

This test data directory includes the following types of handwritten documents:

### 1. Application Forms

Handwritten MCA (Merchant Cash Advance) application forms containing various fields such as:
- Business information (name, address, type)
- Owner details (name, contact information)
- Financial information (requested amount, revenue)
- References and bank details
- Signatures and dates

These forms test the system's ability to extract structured information from form fields with handwritten content.

### 2. Financial Information

Handwritten financial documents including:
- Income statements and declarations
- Expense records and receipts
- Financial calculations and projections
- Bank account information
- Transaction records

These documents test the system's ability to extract numerical data, financial notation, and tabular information from handwritten sources.

### 3. Identification Information

Handwritten identification documents including:
- Signature samples with multiple variations
- Personal identification information
- Contact details
- Handwritten notes and annotations

These documents test the system's ability to process highly variable personal identifiers, particularly signatures which present unique challenges for OCR systems.

### 4. Mixed Content Documents

Documents containing a mixture of handwritten and typed content, including:
- Forms with typed fields and handwritten responses
- Typed documents with handwritten annotations
- Documents with handwritten corrections or additions

These documents test the system's ability to distinguish between and correctly process both handwritten and typed text within the same document.

## Handwriting Styles

The test data includes a diverse range of handwriting styles to ensure the OCR system can handle real-world variation. For detailed information about each style and its specific challenges, refer to the [handwriting_styles.md](./handwriting_styles.md) file. The main categories include:

1. **Print Handwriting**: Separated characters similar to printed text (highest expected accuracy)
2. **Cursive Handwriting**: Connected characters with flowing strokes (challenging for OCR)
3. **Mixed Handwriting**: Combination of print and cursive styles
4. **Artistic/Stylized Handwriting**: Highly personalized with decorative elements
5. **Rapid/Hasty Handwriting**: Quickly written with minimal attention to legibility
6. **Block/All-Caps Handwriting**: Text written entirely in capital letters
7. **Handwriting with Special Characters**: Includes non-alphabetic characters and symbols

Each style presents unique challenges for OCR processing and requires specific approaches for accurate text extraction.

## Document Quality Variations

To test OCR robustness, the test data includes documents with varying quality levels:

1. **High Quality**:
   - Clear, well-formed handwriting
   - High contrast between text and background
   - Clean document with no artifacts
   - Consistent pen pressure and line thickness
   - Expected OCR accuracy: 85-95%

2. **Medium Quality**:
   - Average legibility
   - Some variation in contrast or pen pressure
   - Minor artifacts or background noise
   - Slight inconsistencies in writing style
   - Expected OCR accuracy: 75-85%

3. **Low Quality**:
   - Difficult-to-read handwriting
   - Poor contrast or faded text
   - Significant artifacts, smudges, or background noise
   - Highly inconsistent writing style or pressure
   - Expected OCR accuracy: 60-75%

## Naming Conventions

Test files follow a consistent naming convention to facilitate organization and automated testing:

```
[document_type]_[handwriting_style]_[quality]_[sequence].pdf
```

Where:
- `document_type`: Indicates the document category (app_form, financial, id, mixed)
- `handwriting_style`: Indicates the primary handwriting style (print, cursive, mixed, artistic, rapid, block, special)
- `quality`: Indicates the document quality (high, medium, low)
- `sequence`: A unique identifier number (001, 002, etc.)

Examples:
- `app_form_print_high_001.pdf`: High-quality application form with print handwriting
- `financial_cursive_medium_003.pdf`: Medium-quality financial document with cursive handwriting
- `id_mixed_low_002.pdf`: Low-quality identification document with mixed handwriting

## Using the Test Data

### Loading Test Documents

The test data can be loaded using the fixtures defined in `conftest.py`. Example:

```python
def test_handwritten_extraction(handwritten_application_form):
    # handwritten_application_form is a fixture that loads a test document
    ocr_service = OCRService()
    result = ocr_service.process_document(handwritten_application_form)
    
    # Verify extraction accuracy against expected values
    assert result.extracted_fields["business_name"] == "Acme Corporation"
    assert result.confidence_scores["business_name"] >= 0.85
```

### Testing Different Handwriting Styles

Test across different handwriting styles to ensure robust recognition:

```python
@pytest.mark.parametrize("handwriting_style", [
    "print",
    "cursive",
    "mixed",
    "artistic",
    "rapid",
    "block"
])
def test_handwriting_style_extraction(handwriting_style, request):
    # Load a document with the specified handwriting style
    document = request.getfixturevalue(f"handwritten_{handwriting_style}_sample")
    
    # Process with OCR service
    ocr_service = OCRService()
    result = ocr_service.process_document(document)
    
    # Verify extraction meets minimum accuracy for the style
    expected_accuracy = get_expected_accuracy_for_style(handwriting_style)
    assert result.overall_accuracy >= expected_accuracy
```

### Testing Confidence Scoring

Test that confidence scores accurately reflect extraction certainty:

```python
def test_confidence_scoring(handwritten_document_with_metadata):
    # Process document with OCR service
    ocr_service = OCRService()
    result = ocr_service.process_document(handwritten_document_with_metadata)
    
    # Get expected values from metadata
    expected_fields = handwritten_document_with_metadata.metadata["expected_fields"]
    
    # Verify confidence scores correlate with extraction accuracy
    for field_name, expected in expected_fields.items():
        extracted_value = result.extracted_fields[field_name]
        confidence = result.confidence_scores[field_name]
        
        # Check if confidence score accurately reflects extraction quality
        if extracted_value == expected["value"]:
            assert confidence >= expected["expected_confidence"]
        else:
            # If extraction is incorrect, confidence should be lower
            assert confidence < expected["expected_confidence"]
```

## Adding New Test Documents

To add new handwritten document test samples:

1. **Prepare the Document**:
   - Create or obtain a handwritten document that tests specific OCR capabilities
   - Ensure the document represents real-world use cases for the MCA system
   - Document the expected text content and field values

2. **Name the File** according to the naming convention described above

3. **Place the File** in the appropriate subdirectory based on document type and quality

4. **Update the Manifest**:
   - Add an entry to `sample_manifest.json` with document metadata
   - Include expected field values and positions
   - Specify expected confidence scores for each field

5. **Create Test Fixtures** if needed in `conftest.py`

6. **Verify Integration** with the test suite by running relevant tests

Example manifest entry for a new document:

```json
{
  "id": "app_form_cursive_medium_005",
  "file_path": "handwritten_documents/application_forms/medium_quality/app_form_cursive_medium_005.pdf",
  "document_type": "APPLICATION_FORM",
  "text_type": "HANDWRITTEN",
  "handwriting_style": "CURSIVE",
  "quality": "MEDIUM",
  "description": "MCA application form with cursive handwriting, medium quality",
  "expected_fields": {
    "business_name": {
      "value": "Johnson Consulting Group",
      "position": {"x1": 120, "y1": 150, "x2": 350, "y2": 170},
      "expected_confidence": 0.82
    },
    "owner_name": {
      "value": "Sarah Johnson",
      "position": {"x1": 120, "y1": 200, "x2": 350, "y2": 220},
      "expected_confidence": 0.85
    },
    "requested_amount": {
      "value": "75000",
      "position": {"x1": 120, "y1": 250, "x2": 250, "y2": 270},
      "expected_confidence": 0.80
    }
    // Additional fields...
  },
  "expected_classification_confidence": 0.95,
  "expected_overall_confidence": 0.83
}
```

## Expected Accuracy

The OCR Service is expected to achieve the following accuracy levels for handwritten documents:

| Document Type | Handwriting Style | Quality | Expected Field Accuracy | Expected Overall Accuracy |
|---------------|-------------------|---------|------------------------|---------------------------|
| Application Form | Print | High | 90-95% | 92% |
| Application Form | Print | Medium | 85-90% | 87% |
| Application Form | Print | Low | 75-85% | 80% |
| Application Form | Cursive | High | 85-90% | 87% |
| Application Form | Cursive | Medium | 75-85% | 80% |
| Application Form | Cursive | Low | 65-75% | 70% |
| Application Form | Mixed | High | 85-90% | 87% |
| Financial Document | Print | High | 90-95% | 92% |
| Financial Document | Cursive | Medium | 75-85% | 80% |
| ID Document | Mixed | High | 85-90% | 87% |

These accuracy targets are defined in the `test_parameters` section of the parent `metadata.json` file and are used to validate the OCR Service's performance against the 99% overall system accuracy requirement.

## Confidence Thresholds

The following confidence thresholds should be used for verification decisions:

| Handwriting Style | Automation Threshold | Verification Threshold | Notes |
|-------------------|----------------------|------------------------|-------|
| Print             | ≥ 0.85              | < 0.75                 | High automation potential |
| Cursive           | ≥ 0.75              | < 0.65                 | May require more verification |
| Mixed             | ≥ 0.80              | < 0.70                 | Context-dependent verification |
| Artistic          | ≥ 0.70              | < 0.60                 | Higher verification rate expected |
| Rapid/Hasty       | ≥ 0.70              | < 0.60                 | Field-dependent thresholds |
| Block/All-Caps    | ≥ 0.80              | < 0.70                 | Good automation candidate |
| Special Characters | ≥ 0.75              | < 0.65                 | Symbol-dependent verification |

Fields with confidence scores:
- Above the "Automation Threshold" can be processed automatically
- Below the "Verification Threshold" must be flagged for human review
- Between these thresholds should be handled based on field criticality

## Binary Files and Version Control

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control using the `.gitignore` file in this directory. This prevents large binary files from bloating the repository while maintaining necessary metadata.

To obtain the actual test documents:

1. Download them from the shared document repository (contact the OCR team for access)
2. Place them in the appropriate subdirectories according to the paths defined in `sample_manifest.json`
3. Run the verification script to ensure all documents are correctly placed:

```bash
python -m ocr_service.tests.verify_test_data --type handwritten
```

## References

- [Handwriting Styles Catalog](./handwriting_styles.md): Detailed information about handwriting styles and their challenges
- [Sample Manifest](./sample_manifest.json): Configuration file defining all test samples
- [OCR Service Implementation](../../src/services/ocr_service.py): Core OCR service implementation
- [Handwritten Text Model](../../src/models/handwritten_text_model.py): Specialized model for handwritten text recognition
- [Test Fixtures](../../tests/conftest.py): Test fixtures for loading handwritten document samples
- [Technical Specification](../../../README.md): Overall system requirements and specifications