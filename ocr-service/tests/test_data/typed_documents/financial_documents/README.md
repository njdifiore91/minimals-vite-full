# Financial Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract data from financial documents with 99% accuracy as required by the Merchant Cash Advance (MCA) Application Processing System. The test samples in this folder are specifically designed to evaluate the OCR Service's performance on financial documents that merchants typically submit as part of their MCA application process.

## Purpose

The primary purposes of this financial document test collection are:

1. **Validate Financial Data Extraction Accuracy**: Ensure the OCR Service meets the 99% data extraction accuracy requirement for financial documents through AI and machine learning
2. **Test Financial Document Processing**: Evaluate OCR performance across various financial document types and formats
3. **Verify Numerical Data Extraction**: Test the system's ability to accurately extract and interpret financial figures, dates, and tabular data
4. **Regression Testing**: Prevent regressions in financial data extraction accuracy when making changes to the service
5. **Performance Benchmarking**: Establish baseline performance metrics for financial document processing

## Financial Document Categories

This collection includes the following categories of financial documents:

### Bank Statements

Monthly and quarterly bank statements with transaction histories, balances, and account information. These documents test the OCR Service's ability to extract:

- Account holder information
- Account numbers (partially masked)
- Statement periods
- Opening and closing balances
- Transaction details in tabular format
- Deposit and withdrawal totals

### Tax Returns

Business and personal tax returns with financial information, tax calculations, and supporting schedules. These documents test the OCR Service's ability to extract:

- Business/taxpayer identification information
- Income figures across multiple categories
- Deduction and expense breakdowns
- Tax calculations and amounts due
- Signature information and filing dates

### Profit & Loss Statements

Quarterly and annual profit and loss statements showing revenue, expenses, and net income. These documents test the OCR Service's ability to extract:

- Business identification information
- Reporting periods
- Revenue breakdowns by category
- Expense categorizations
- Net income calculations
- Comparative data across time periods

### Balance Sheets

Financial statements showing assets, liabilities, and equity at specific points in time. These documents test the OCR Service's ability to extract:

- Business identification information
- Statement dates
- Asset categorizations and values
- Liability categorizations and values
- Equity information
- Totals and subtotals

### Credit Card Statements

Merchant credit card processing statements showing transaction volumes, fees, and deposits. These documents test the OCR Service's ability to extract:

- Merchant identification information
- Processing volumes and transaction counts
- Fee calculations and breakdowns
- Card type summaries
- Daily or monthly processing summaries

### Financial Statements

Comprehensive annual financial reports including income statements, balance sheets, cash flow statements, and notes. These documents test the OCR Service's ability to extract:

- Business identification information
- Reporting periods
- Complex financial data across multiple statements
- Comparative data across fiscal years
- Footnotes and explanatory information

## Document Quality Variations

Test documents in this collection are available in three quality levels to test the OCR system's robustness:

### High Quality (Expected Confidence ≥ 0.95)

- Clear, high-resolution (300 dpi) documents
- Optimal contrast and no noise
- Professional formatting and layout
- Clean, standard fonts
- No scanning artifacts

### Medium Quality (Expected Confidence ≥ 0.85)

- Moderate resolution (200 dpi) documents
- Slight blur or contrast issues
- Minor noise or artifacts
- Some variation in formatting
- Occasional scanning artifacts

### Low Quality (Expected Confidence ≥ 0.75)

- Low resolution (150 dpi or less) documents
- Poor contrast or significant noise
- Skewed or misaligned content
- Inconsistent formatting
- Visible scanning artifacts

## Document Characteristics

Financial test documents vary across several dimensions:

1. **Format**: Various layouts, fonts, and structures typical of financial institutions
2. **Content Density**: From sparse statements to dense transaction tables
3. **Field Types**: Structured fields, complex tables, numerical data, dates
4. **Complexity**: Simple single-page statements to multi-page comprehensive reports
5. **Special Elements**: Financial institution logos, watermarks, security features

## Naming Conventions

Financial test documents follow this naming convention:

```
[financial_type]_[subtype]_[quality]_[variant].[extension]
```

Examples:
- `bank_statement_monthly_high_001.pdf` - High-quality monthly bank statement, variant 1
- `tax_return_business_medium_002.pdf` - Medium-quality business tax return, variant 2
- `profit_loss_quarterly_low_003.pdf` - Low-quality quarterly profit & loss statement, variant 3

## Manifest File

The `financial_documents_manifest.json` file defines:

1. **Document Metadata**: File path, type, quality level, and other attributes
2. **Expected OCR Results**: The specific fields that should be extracted
3. **Field Definitions**: Field names, expected values, and positions
4. **Confidence Thresholds**: Minimum acceptable confidence scores for extraction
5. **Table Definitions**: Structure and content of tabular data

### Manifest Structure

The manifest includes:

- Document categories and quality levels
- Document-specific metadata (ID, filename, category, type, quality)
- Document characteristics (resolution, orientation, page count)
- Expected extraction results for fields and tables
- Position information for fields and tables
- Expected confidence scores

## Using Financial Test Documents

### For Manual Testing

1. Select appropriate financial test documents based on the testing scenario
2. Process the documents through the OCR Service
3. Compare the extraction results with the expected values in the manifest
4. Evaluate accuracy, confidence scores, and processing time
5. Pay special attention to numerical values, which must be within 0.1% of expected values

### For Automated Testing

1. Use the manifest file to programmatically load financial test documents
2. Submit documents to the OCR Service API
3. Compare the API response with the expected values
4. Calculate accuracy metrics and validate against requirements
5. Generate test reports with pass/fail status

### Performance Requirements

When testing with financial documents, verify that the OCR Service meets these performance requirements:

- Processing time: < 2 seconds per page, < 10 seconds per document
- Memory usage: < 1GB per document
- GPU acceleration: Required for production environment

## Guidelines for Adding New Financial Test Documents

When adding new financial test documents to this collection:

1. **Follow naming conventions** described above
2. **Add document metadata** to the financial_documents_manifest.json file
3. **Define expected extraction results** for all relevant fields and tables
4. **Specify confidence thresholds** based on document quality
5. **Document any special characteristics** that might affect OCR performance
6. **Anonymize sensitive information** in real financial documents
7. **Include documents in the .gitignore** to prevent binary files from being committed

### Anonymization Requirements

When adding real financial documents, ensure all sensitive information is properly anonymized:

- Replace actual account numbers with masked versions (e.g., XXXX1234)
- Replace actual names with fictional business or individual names
- Replace actual addresses with generic addresses
- Maintain realistic financial figures to preserve testing validity
- Document the anonymization process for each document

## Relationship to OCR Service Requirements

This financial document test data directly supports the following requirements from the technical specification:

1. **99% Data Extraction Accuracy**: Test documents validate the OCR Service's ability to achieve 99% accuracy with financial data
2. **Processing Time**: Tests verify that financial documents can be processed within the required time limits
3. **Document Classification**: Tests confirm correct financial document type identification
4. **Field Extraction**: Tests validate accurate extraction of specific financial fields with high confidence

## Notes on Binary Files

Actual financial document files (PDF, TIFF, PNG, JPEG) are excluded from version control to prevent repository bloat. The `.gitignore` file in this directory ensures that only metadata and configuration files are tracked.

To obtain the actual financial test documents:

1. Download the financial document test package from the secure S3 bucket:
   s3://mca-documents-staging/test-data/financial_documents.zip

2. Extract the package to this directory, preserving the folder structure

3. Run the verification script to ensure all required financial test documents are present:
   ```
   python ../../../verify_test_data.py typed_documents/financial_documents
   ```

## Related Test Data

This financial document test data works in conjunction with other test data collections:

- **Application Forms**: For testing complete application packages
- **Business Documents**: For testing supporting business documentation
- **Quality Variations**: For testing OCR robustness across quality levels