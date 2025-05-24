# Handwritten Documents Test Data

## Overview

This directory contains test data for evaluating the OCR Service's ability to extract text from handwritten documents with high accuracy. As specified in the technical requirements, the OCR Service must achieve 99% data extraction accuracy through AI and machine learning for handwritten text processing.

## Purpose

The handwritten document test samples serve several critical purposes:

1. **Validation of OCR Accuracy**: Verify that the OCR Service meets the 99% accuracy requirement for handwritten text extraction
2. **Model Training and Evaluation**: Provide diverse samples for training and evaluating TensorFlow models
3. **Regression Testing**: Ensure that code changes don't negatively impact handwritten text recognition capabilities
4. **Performance Benchmarking**: Establish baseline performance metrics for handwritten text processing
5. **Edge Case Identification**: Test the system's ability to handle challenging handwriting styles and document conditions

## Document Types

This test folder includes the following types of handwritten documents:

| Document Type | Description | Quantity | Naming Pattern |
|---------------|-------------|----------|----------------|
| Application Forms | Merchant Cash Advance application forms with handwritten fields | 20 | `app_form_[001-020].{jpg,png,pdf}` |
| Financial Statements | Handwritten financial records and statements | 15 | `fin_stmt_[001-015].{jpg,png,pdf}` |
| Personal Notes | Free-form handwritten notes related to applications | 10 | `notes_[001-010].{jpg,png,pdf}` |
| Signatures | Isolated signature samples for verification testing | 25 | `sig_[001-025].{jpg,png,pdf}` |
| Mixed Content | Documents containing both handwritten and typed text | 15 | `mixed_[001-015].{jpg,png,pdf}` |
| Field Entries | Individual handwritten field entries (names, addresses, etc.) | 30 | `field_[type]_[001-030].{jpg,png,pdf}` |

## Handwriting Style Variations

To ensure robust OCR testing, the samples include various handwriting styles:

1. **Cursive**: Connected flowing script (approximately 40% of samples)
2. **Print**: Disconnected handwritten characters (approximately 35% of samples)
3. **Mixed**: Combination of cursive and print styles (approximately 25% of samples)

Additionally, the samples vary in:

- **Legibility**: From very neat to challenging handwriting
- **Pen/Pencil Type**: Ballpoint, gel, pencil, marker
- **Writing Pressure**: Light, medium, heavy
- **Line Spacing**: Tight, normal, wide
- **Writing Angle**: Vertical, slanted

For detailed information about the handwriting styles included, refer to the `handwriting_styles.md` file in this directory.

## Quality Variations

The test data includes documents with various quality characteristics to test OCR robustness:

- **Clean Documents**: High-quality scans with clear handwriting
- **Degraded Documents**: Samples with fading, smudging, or aging effects
- **Noisy Documents**: Samples with background noise, stains, or artifacts
- **Low-Contrast Documents**: Samples with poor contrast between text and background
- **Skewed Documents**: Samples with text not perfectly aligned horizontally

## Metadata and Expected Results

Each test document has corresponding metadata and expected OCR results defined in the `sample_manifest.json` file. This manifest includes:

- Document identifier
- Document type
- Handwriting style
- Quality characteristics
- Expected text content
- Field positions and boundaries
- Expected confidence scores

The manifest is used by the test suite to validate OCR extraction results against known values.

## Usage Guidelines

### Using Test Data in Unit Tests

```python
import os
import json
from pathlib import Path

# Load the sample manifest
MANIFEST_PATH = Path(__file__).parent / "sample_manifest.json"
with open(MANIFEST_PATH, "r") as f:
    manifest = json.load(f)

# Get a test document path
def get_test_document_path(doc_id):
    doc_info = manifest.get(doc_id)
    if not doc_info:
        raise ValueError(f"Document ID {doc_id} not found in manifest")
    
    return Path(__file__).parent / doc_info["file_path"]

# Get expected OCR results for a document
def get_expected_results(doc_id):
    doc_info = manifest.get(doc_id)
    if not doc_info:
        raise ValueError(f"Document ID {doc_id} not found in manifest")
    
    return doc_info["expected_text"], doc_info["expected_confidence"]
```

### Using Test Data in Integration Tests

```python
import pytest
from ocr_service.models import HandwrittenTextModel
from ocr_service.utils import calculate_accuracy

@pytest.mark.parametrize("doc_id", [
    "app_form_001",
    "fin_stmt_003",
    "notes_002",
    "sig_010",
    "mixed_005"
])
def test_handwritten_ocr_accuracy(doc_id, test_document_fixture):
    # Get test document and expected results
    doc_path, expected_text, expected_confidence = test_document_fixture(doc_id)
    
    # Process document with OCR model
    model = HandwrittenTextModel()
    extracted_text, confidence = model.process_document(doc_path)
    
    # Calculate accuracy
    accuracy = calculate_accuracy(extracted_text, expected_text)
    
    # Assert high accuracy (99% as per requirements)
    assert accuracy >= 0.99, f"OCR accuracy below threshold: {accuracy}"
    
    # Assert confidence score is within expected range
    assert abs(confidence - expected_confidence) < 0.05, \
        f"Confidence score {confidence} differs from expected {expected_confidence}"
```

## Guidelines for Adding New Test Documents

When adding new handwritten document samples to this test folder, please follow these guidelines:

1. **File Format**: Use high-quality images (300 DPI or higher) in PNG or JPG format, or PDF files
2. **Naming Convention**: Follow the established naming patterns for the document type
3. **Metadata**: Add complete metadata for the new document to `sample_manifest.json`
4. **Ground Truth**: Include the exact text content as ground truth for accuracy validation
5. **Diversity**: Ensure new samples add diversity in terms of handwriting style, content, or quality
6. **Permission**: Ensure you have appropriate rights to use the document for testing purposes
7. **Anonymization**: Remove or replace any personally identifiable information (PII)

### Metadata Template for New Documents

```json
{
  "doc_id": {
    "file_path": "relative/path/to/file.png",
    "document_type": "application_form",
    "handwriting_style": "cursive",
    "quality": "clean",
    "expected_text": "Exact text content of the document",
    "fields": [
      {
        "name": "field_name",
        "coordinates": [x1, y1, x2, y2],
        "expected_value": "field value",
        "expected_confidence": 0.98
      }
    ],
    "expected_confidence": 0.97
  }
}
```

## Performance Expectations

As specified in the technical requirements, the OCR Service must achieve:

- **99% accuracy** for handwritten text extraction
- **Processing time** under 5 minutes from receipt to completion
- **Confidence scoring** for all extracted fields

The test suite uses these documents to validate these performance metrics.

## Integration with Test Framework

These test documents are automatically loaded by the test framework using the fixtures defined in `tests/conftest.py`. The framework handles:

1. Loading the appropriate test documents based on test parameters
2. Providing expected results for validation
3. Calculating accuracy metrics
4. Reporting detailed results for failed tests

## Related Documentation

- See `handwriting_styles.md` for detailed information about handwriting variations
- See `../README.md` for overall test data organization
- See `../../test_models/test_handwritten_text_model.py` for model-specific tests
- See `../../../src/models/handwritten_text_model.py` for implementation details