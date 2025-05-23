# OCR Service Test Data

This directory contains test data for validating the OCR Service's ability to extract data from various document types with 99% accuracy through AI and machine learning. The test data is organized to support comprehensive testing of the OCR Service's capabilities across different document types, text styles, and quality levels.

## Directory Structure

```
test_data/
├── metadata.json                # Central metadata file with expected OCR results
├── typed_documents/            # Documents with machine-printed text
│   ├── invoices/               # Invoice documents
│   ├── financial_documents/    # Financial statements and reports
│   └── quality_variations/     # Documents with varying quality levels
├── handwritten_documents/      # Documents with handwritten text
├── mixed_documents/            # Documents with both typed and handwritten content
└── tables/                     # Documents with tabular data
```

## Test Data Overview

### metadata.json

The `metadata.json` file is the central configuration file that defines the structure and expected OCR results for all test documents. It contains:

- Document metadata (type, page count, quality, orientation)
- Expected field values and positions for each document
- Expected confidence scores for extracted fields
- Table definitions and expected extraction results
- Confidence thresholds for different quality levels

This file serves as the source of truth for validating OCR extraction results during testing. All test cases should reference this file to verify that the OCR Service extracts data with the required accuracy.

### Typed Documents

The `typed_documents/` directory contains machine-printed text documents of various types:

- **Loan applications**: Standard business loan application forms
- **Tax returns**: Business tax return documents with financial data
- **Bank statements**: Account statements with transaction tables
- **Invoices**: Vendor invoices with line items and totals
- **Financial documents**: Financial reports, projections, and analyses

These documents are further organized into subfolders based on document type and quality variations:

- `invoices/`: Contains various invoice formats from different vendors
- `financial_documents/`: Contains financial statements and reports
- `quality_variations/`: Contains documents with varying quality levels (high, medium, low) to test OCR robustness

Expected OCR accuracy for typed documents:
- High quality: 95-99% confidence
- Medium quality: 85-95% confidence
- Low quality: 75-85% confidence

### Handwritten Documents

The `handwritten_documents/` directory contains documents with handwritten text in various styles:

- **Cursive handwriting**: Flowing, connected script
- **Print handwriting**: Disconnected, printed characters
- **Mixed handwriting**: Combination of cursive and print
- **Signatures**: Handwritten signatures in various styles

These documents test the OCR Service's ability to extract handwritten text, which is typically more challenging than typed text. The directory includes documents with varying handwriting quality and legibility to test the robustness of the OCR models.

Expected OCR accuracy for handwritten documents:
- Clear handwriting: 80-90% confidence
- Average handwriting: 75-85% confidence
- Difficult handwriting: 65-75% confidence

### Mixed Documents

The `mixed_documents/` directory contains documents with both typed and handwritten content, such as:

- Printed forms with handwritten entries
- Typed documents with handwritten annotations
- Documents with handwritten signatures on typed content

These documents test the OCR Service's ability to distinguish between and correctly process both typed and handwritten text within the same document. This capability is critical for processing real-world documents like filled application forms.

Expected OCR accuracy for mixed documents:
- Typed content: 90-99% confidence
- Handwritten content: 75-90% confidence

### Tables

The `tables/` directory contains documents with tabular data of varying complexity:

- Simple tables with basic row/column structure
- Complex tables with merged cells and nested headers
- Multi-page tables that span across multiple pages

These documents test the OCR Service's ability to extract structured data while maintaining row and column relationships. Table extraction is particularly important for financial documents like bank statements and invoices.

Expected OCR accuracy for tables:
- Simple tables: 90-95% confidence
- Complex tables: 85-90% confidence
- Multi-page tables: 80-90% confidence

## Using Test Data in Tests

### Unit Tests

For unit testing individual OCR components:

1. Use the `metadata.json` file to retrieve expected values for specific documents
2. Test document classification accuracy using samples from each category
3. Test text extraction on specific regions using the position data
4. Validate confidence score calculation against expected thresholds

Example:

```python
def test_field_extraction(document_path, field_name):
    # Load test document metadata
    metadata = load_metadata()
    document_id = os.path.basename(document_path).split('.')[0]
    document_type = get_document_type(document_path)
    
    # Get expected field data from metadata
    expected_field = metadata[document_type][document_id]['expected_fields'][field_name]
    expected_value = expected_field['value']
    expected_confidence = expected_field['expected_confidence']
    field_position = expected_field['position']
    
    # Extract field using OCR
    extracted_field = ocr_service.extract_field(document_path, field_position)
    
    # Assert extraction accuracy
    assert extracted_field['value'] == expected_value
    assert extracted_field['confidence'] >= expected_confidence
```

### Integration Tests

For testing the complete OCR pipeline:

1. Process complete documents through the entire OCR pipeline
2. Validate all extracted fields against expected values in `metadata.json`
3. Test document processing workflows with different document types
4. Verify that confidence scores meet the required thresholds for automation

Example:

```python
def test_document_processing_pipeline(document_path):
    # Load test document metadata
    metadata = load_metadata()
    document_id = os.path.basename(document_path).split('.')[0]
    document_type = get_document_type(document_path)
    
    # Process document through the complete pipeline
    processing_result = ocr_service.process_document(document_path)
    
    # Validate all extracted fields
    expected_fields = metadata[document_type][document_id]['expected_fields']
    for field_name, expected_field in expected_fields.items():
        extracted_field = processing_result['fields'].get(field_name)
        assert extracted_field is not None
        assert extracted_field['value'] == expected_field['value']
        assert extracted_field['confidence'] >= expected_field['expected_confidence']
    
    # Validate overall document confidence
    assert processing_result['overall_confidence'] >= metadata['confidence_thresholds']['automation_threshold']
```

### Performance Testing

For testing OCR performance and accuracy metrics:

1. Process large batches of documents to measure throughput
2. Calculate accuracy metrics across document types and quality levels
3. Benchmark processing time for different document complexities
4. Test GPU acceleration for performance improvements

Example:

```python
def test_ocr_accuracy_metrics():
    # Process all test documents
    results = []
    for document_type in ['typed_documents', 'handwritten_documents', 'mixed_documents']:
        document_paths = get_all_documents(document_type)
        for document_path in document_paths:
            result = ocr_service.process_document(document_path)
            results.append(result)
    
    # Calculate accuracy metrics
    accuracy = calculate_accuracy(results)
    
    # Assert overall accuracy meets requirements
    assert accuracy >= 0.99  # 99% accuracy requirement
```

## Adding New Test Documents

When adding new test documents to the test data directory:

1. Place the document in the appropriate subfolder based on its type and content
2. Update the `metadata.json` file with the document's metadata and expected extraction results
3. Follow the existing naming conventions for consistency
4. Include documents with varying characteristics to test different aspects of the OCR Service
5. Document any special characteristics or challenges in the relevant README.md file

## Confidence Thresholds

The OCR Service uses confidence thresholds to determine when human review is required:

- **High confidence (≥ 0.9)**: Automated processing without human review
- **Medium confidence (0.75-0.9)**: May require human verification for critical fields
- **Low confidence (< 0.75)**: Requires human review

The automation threshold is set at 0.75, meaning fields with confidence scores below this threshold will be flagged for human review to maintain the 99% accuracy requirement.

## Test Data Maintenance

The test data should be regularly updated to include new document types, edge cases, and challenging scenarios. As the OCR Service evolves, the test data should be expanded to validate new capabilities and improvements.

When updating the test data:

1. Ensure that all new documents have corresponding entries in the `metadata.json` file
2. Update expected confidence thresholds as OCR models improve
3. Add new document types as they are supported by the OCR Service
4. Document any changes to the test data structure or organization

## References

- OCR Service Technical Specification (Section 0.1.1, 0.1.2, 0.1.3)
- Testing Strategy (Section 6.6)
- Document Classification Requirements
- OCR Extraction Specifications