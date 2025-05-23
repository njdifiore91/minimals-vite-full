# Financial Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract information from financial documents with 99% accuracy as required by the Merchant Cash Advance (MCA) Application Processing System. These financial document samples are critical for testing the TensorFlow-based OCR models' performance on various financial document types commonly encountered in MCA applications.

## Purpose

The financial document test samples serve several important purposes:

1. **Accuracy Validation**: Verify that the OCR Service can extract financial data with the required 99% accuracy as specified in section 0.1.1 of the technical specification
2. **Financial Data Extraction**: Test the system's ability to accurately extract numerical values, dates, and tabular financial information
3. **Document Type Handling**: Ensure proper extraction from various financial document types (tax returns, bank statements, etc.)
4. **Quality Robustness**: Test OCR performance across different document quality levels (high, medium, low)
5. **Field Recognition**: Validate accurate identification and extraction of specific financial fields (totals, dates, account numbers, etc.)
6. **Table Extraction**: Test the extraction of complex financial tables with proper structure recognition
7. **Confidence Scoring**: Verify that confidence scores accurately reflect extraction reliability

## Financial Document Types

This test directory includes the following types of financial documents:

### Tax Returns
- Form 1120 (Corporate Tax Returns)
- Form 1040 Schedule C (Sole Proprietorship)
- Form 1065 (Partnership Returns)
- State tax filings
- Supporting tax schedules

### Bank Statements
- Business checking account statements
- Business savings account statements
- Transaction histories
- Account summaries
- Electronic statement exports

### Profit & Loss Statements
- Quarterly P&L reports
- Annual profit and loss statements
- Detailed expense breakdowns
- Revenue category summaries
- Comparative P&L statements

### Balance Sheets
- Company balance sheets
- Asset and liability listings
- Equity statements
- Comparative balance sheets
- Consolidated balance sheets

### Cash Flow Statements
- Operating activities
- Investing activities
- Financing activities
- Net cash flow reports
- Cash reconciliation statements

### Income Statements
- Revenue reports
- Expense reports
- Earnings statements
- Quarterly income summaries
- Year-to-date income reports

## Document Quality Variations

To test the robustness of the OCR system, financial documents are provided in three quality levels. These variations ensure the OCR Service can achieve the required 99% accuracy for high-quality documents while maintaining acceptable performance for lower quality inputs.

### High Quality
- Resolution: 300+ DPI
- Contrast: Strong, clear text with optimal contrast
- Noise: Minimal to none, clean background
- Document condition: No skew, perfectly aligned text
- Format: Digital native or high-quality scan
- Expected OCR accuracy: 99-100%

### Medium Quality
- Resolution: 150-300 DPI
- Contrast: Good but with some inconsistencies
- Noise: Some noise or minor artifacts present
- Document condition: Minimal skew (less than 2 degrees)
- Format: Good quality scan with adequate lighting
- Expected OCR accuracy: 95-98%

### Low Quality
- Resolution: Below 150 DPI
- Contrast: Poor, faded text, or low contrast
- Noise: Significant noise or distortions
- Document condition: Noticeable skew (2-5 degrees)
- Format: Fax transmission or poor scan
- Expected OCR accuracy: 85-95%

## Manifest File

The `financial_documents_manifest.json` file defines all test documents and their expected OCR extraction results. This manifest is used for automated validation of OCR accuracy and contains:

- Document metadata (type, quality, orientation)
- Expected text content for each document
- Field locations and expected values
- Table structures and expected data
- Confidence thresholds for extraction validation

Example manifest structure for a financial document:

```json
{
  "id": "tax_return_001",
  "file_name": "tax_return_001.pdf",
  "category": "tax_returns",
  "quality": "high",
  "orientation": "portrait",
  "page_count": 3,
  "expected_extraction": {
    "fields": [
      {
        "name": "business_name",
        "value": "Acme Corporation",
        "expected_confidence": 0.98,
        "location": {
          "page": 1,
          "top": 150,
          "left": 200,
          "width": 250,
          "height": 30
        }
      },
      // Additional fields...
    ],
    "tables": [
      {
        "name": "income_statement",
        "location": {
          "page": 2,
          "top": 150,
          "left": 50,
          "width": 500,
          "height": 400
        },
        "rows": 10,
        "columns": 2,
        "headers": ["Item", "Amount"],
        "data": [
          ["Gross receipts or sales", "$1,200,000"],
          // Additional rows...
        ]
      }
    ]
  }
}
```

## File Naming Conventions

Financial test documents follow this naming convention:

```
[document_type]_[subtype]_[quality]_[variant].[extension]
```

Examples:
- `tax_return_1120_high_001.pdf` - High-quality 1120 corporate tax return, variant 1
- `bank_statement_checking_medium_002.pdf` - Medium-quality checking account statement, variant 2
- `profit_loss_quarterly_low_001.pdf` - Low-quality quarterly P&L statement, variant 1
- `balance_sheet_annual_high_003.pdf` - High-quality annual balance sheet, variant 3

## Using Financial Test Documents

### For Manual Testing

1. Select appropriate financial documents based on the test scenario
2. Process the documents through the OCR Service
3. Compare the extracted financial data with the expected results in the manifest
4. Verify extraction accuracy for financial fields and tables
5. Evaluate confidence scores for financial data extraction
6. Check performance across different financial document types and quality levels

### For Automated Testing

```python
# Example test code for financial documents
from ocr_service.models.financial_document_model import FinancialDocumentModel
from ocr_service.utils.testing import load_test_document, load_manifest

def test_financial_document_extraction():
    # Load financial test document and its expected results
    document_id = "tax_return_001"
    document_path = "typed_documents/financial_documents/tax_return_001.pdf"
    manifest = load_manifest("typed_documents/financial_documents/financial_documents_manifest.json")
    expected = manifest["documents"][0]["expected_extraction"]
    
    # Load document content
    document_content, document_metadata = load_test_document(document_path)
    
    # Initialize OCR model
    model = FinancialDocumentModel()
    
    # Process document
    extracted_data = model.extract_financial_data(document_content, document_metadata)
    
    # Validate financial field extraction
    for expected_field in expected["fields"]:
        field_name = expected_field["name"]
        expected_value = expected_field["value"]
        expected_confidence = expected_field["expected_confidence"]
        
        # Find matching extracted field
        extracted_field = next((f for f in extracted_data["fields"] if f["name"] == field_name), None)
        
        assert extracted_field is not None, f"Financial field {field_name} not extracted"
        assert extracted_field["value"] == expected_value, \
            f"Financial field {field_name} value mismatch: expected {expected_value}, got {extracted_field['value']}"
        assert extracted_field["confidence"] >= expected_confidence, \
            f"Financial field {field_name} confidence below threshold: expected {expected_confidence}, got {extracted_field['confidence']}"
    
    # Validate financial table extraction
    for expected_table in expected["tables"]:
        table_name = expected_table["name"]
        
        # Find matching extracted table
        extracted_table = next((t for t in extracted_data["tables"] if t["name"] == table_name), None)
        
        assert extracted_table is not None, f"Financial table {table_name} not extracted"
        assert len(extracted_table["data"]) == len(expected_table["data"]), \
            f"Financial table {table_name} row count mismatch"
        
        # Check table data
        for i, expected_row in enumerate(expected_table["data"]):
            extracted_row = extracted_table["data"][i]
            assert extracted_row == expected_row, \
                f"Financial table {table_name} data mismatch at row {i}"
```

## Guidelines for Adding New Financial Test Documents

1. **Document Selection**: Choose financial documents that represent real-world examples encountered in MCA processing
2. **Anonymization**: Ensure all PII (Personally Identifiable Information) and sensitive financial data is anonymized or replaced with fictional data
3. **Quality Variation**: Include financial documents with varying quality levels to test OCR robustness
4. **Manifest Updates**: Add entries to the financial_documents_manifest.json file with expected extraction results
5. **Validation**: Manually verify that the OCR system can extract the expected financial data
6. **Comprehensive Coverage**: Ensure coverage of all critical financial document types and edge cases

### Steps to Add a New Financial Test Document

1. Name the financial document according to the naming convention
2. Place the document in this directory
3. Process the document through the OCR system to get baseline results
4. Create a new entry in the financial_documents_manifest.json file with:
   - Document metadata
   - Expected field values and locations
   - Expected table structures and data
   - Confidence thresholds for validation
5. Add automated tests for the new financial document

## Binary Files Handling

Actual financial document files (PDF, TIFF, PNG, JPEG) are excluded from version control via the .gitignore file to prevent repository bloat. Only metadata and configuration files are tracked.

To obtain the actual financial test documents:

1. Access the shared document repository at `s3://mca-documents-staging/test-data/financial_documents.zip`
2. Download the required documents to your local test environment
3. Place them in this directory according to the manifest structure

Alternatively, you can generate synthetic financial test documents using the document generation scripts in the `ocr-service/scripts/generate_test_data` directory.

## Performance Expectations

The OCR Service is expected to process financial documents with the following performance characteristics:

- **Accuracy**: 99% for high-quality financial documents as required by section 0.1.1 of the technical specification
- **Processing Time**: Under 5 seconds per page for financial documents to meet the overall 5-minute application processing requirement
- **Field Extraction**: Correctly identify and extract all financial fields defined in the manifest
- **Table Extraction**: Accurately extract financial tables with proper structure recognition
- **Confidence Scoring**: Provide accurate confidence scores that correlate with extraction accuracy
- **Error Handling**: Properly flag low-confidence financial data extractions for human verification

## Related Documentation

- [OCR Service Architecture](../../README.md)
- [Financial Document Processing Guide](../../docs/financial_document_processing.md)
- [Testing Strategy](../../docs/testing_strategy.md)
- [Document Classification Guide](../../../document-service/docs/classification_guide.md)