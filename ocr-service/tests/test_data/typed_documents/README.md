# Typed Documents Test Data

## Overview

This directory contains test data for validating the OCR Service's ability to extract data from typed documents with 99% accuracy as required by the Merchant Cash Advance (MCA) Application Processing System. The test samples in this folder are specifically designed to evaluate the OCR Service's performance on machine-printed text across various document types, quality levels, and formats.

## Purpose

The primary purposes of this test data collection are:

1. **Validate OCR Accuracy**: Ensure the OCR Service meets the 99% data extraction accuracy requirement through AI and machine learning
2. **Test Robustness**: Evaluate OCR performance across varying document qualities and formats
3. **Regression Testing**: Prevent regressions in OCR accuracy when making changes to the service
4. **Performance Benchmarking**: Establish baseline performance metrics for typed document processing
5. **Automated Validation**: Enable automated testing of OCR extraction results against known values

## Directory Structure

The typed_documents directory is organized into the following subfolders, each containing specific types of test documents:

```
typed_documents/
├── .gitignore                 # Excludes binary document files from version control
├── README.md                  # This documentation file
├── sample_manifest.json       # Master manifest of all typed document test samples
├── quality_variations/        # Documents with varying quality levels (high, medium, low)
├── invoices/                  # Invoice documents (vendor invoices, receipts, etc.)
├── financial_documents/       # Financial documents (bank statements, tax forms, etc.)
├── business_documents/        # Business documents (contracts, agreements, etc.)
└── application_forms/         # Application forms and related documents
```

### Document Categories

#### Quality Variations

The `quality_variations` folder contains documents with different quality levels to test the OCR system's robustness:

- **High Quality**: Clear, high-resolution documents with optimal contrast and no noise
- **Medium Quality**: Documents with moderate resolution, slight contrast issues, or minor noise
- **Low Quality**: Documents with low resolution, poor contrast, significant noise, or other quality issues

Each quality level has its own manifest file that defines expected extraction results and confidence scores.

#### Document Types

The following folders contain domain-specific document types:

- **Invoices**: Various invoice formats including vendor invoices, service invoices, and retail receipts
- **Financial Documents**: Bank statements, tax returns, profit/loss statements, balance sheets
- **Business Documents**: Contracts, agreements, business licenses, articles of incorporation
- **Application Forms**: MCA application forms, consent forms, authorization documents

## Document Characteristics

Test documents in this collection vary across several dimensions:

1. **Quality**: High, medium, and low quality samples
2. **Format**: Various layouts, fonts, and structures
3. **Content Density**: Sparse to dense text content
4. **Field Types**: Structured fields, tables, paragraphs, checkboxes
5. **Special Elements**: Logos, signatures, stamps, watermarks

## Naming Conventions

Test documents follow this naming convention:

```
[document_type]_[subtype]_[quality]_[variant].[extension]
```

Examples:
- `invoice_vendor_high_001.pdf` - High-quality vendor invoice, variant 1
- `financial_bankstatement_medium_002.tiff` - Medium-quality bank statement, variant 2
- `application_consent_low_003.png` - Low-quality consent form, variant 3

## Manifest Files

Each subfolder contains a manifest file (e.g., `invoices_manifest.json`) that defines:

1. **Document Metadata**: File path, type, quality level, and other attributes
2. **Expected OCR Results**: The text content that should be extracted
3. **Field Definitions**: Specific fields to extract with their expected values
4. **Confidence Thresholds**: Minimum acceptable confidence scores for extraction
5. **Performance Metrics**: Expected processing time and resource usage

The root `sample_manifest.json` file provides a master reference of all test documents.

### Manifest Format Example

```json
{
  "document_id": "invoice_vendor_high_001",
  "file_path": "invoices/invoice_vendor_high_001.pdf",
  "document_type": "invoice",
  "subtype": "vendor",
  "quality": "high",
  "expected_fields": {
    "invoice_number": {
      "value": "INV-12345",
      "min_confidence": 0.95,
      "position": {"x": 450, "y": 120, "width": 100, "height": 20}
    },
    "date": {
      "value": "2023-10-15",
      "min_confidence": 0.90,
      "position": {"x": 450, "y": 150, "width": 100, "height": 20}
    },
    "total_amount": {
      "value": "$1,234.56",
      "min_confidence": 0.95,
      "position": {"x": 450, "y": 350, "width": 100, "height": 20}
    }
  },
  "performance_expectations": {
    "max_processing_time_ms": 2000,
    "min_accuracy": 0.99
  }
}
```

## Using Test Documents

### For Manual Testing

1. Select appropriate test documents based on the testing scenario
2. Process the documents through the OCR Service
3. Compare the extraction results with the expected values in the manifest
4. Evaluate accuracy, confidence scores, and processing time

### For Automated Testing

1. Use the manifest files to programmatically load test documents
2. Submit documents to the OCR Service API
3. Compare the API response with the expected values
4. Calculate accuracy metrics and validate against requirements
5. Generate test reports with pass/fail status

## Guidelines for Adding New Test Documents

When adding new test documents to this collection:

1. **Follow naming conventions** described above
2. **Add document metadata** to the appropriate manifest file
3. **Define expected extraction results** for all relevant fields
4. **Specify confidence thresholds** based on document quality
5. **Document any special characteristics** that might affect OCR performance
6. **Include documents in the .gitignore** to prevent binary files from being committed
7. **Store actual document files** in the designated secure storage location

## Test Data Sources

Test documents in this collection come from the following sources:

1. **Synthetic Documents**: Generated specifically for testing purposes
2. **Anonymized Real Documents**: Real documents with sensitive information removed
3. **Public Domain Documents**: Publicly available documents suitable for testing

## Relationship to OCR Service Requirements

This test data directly supports the following requirements from the technical specification:

1. **99% Data Extraction Accuracy**: Test documents validate the OCR Service's ability to achieve 99% accuracy
2. **Processing Time**: Tests verify that documents can be processed within the required time limits
3. **Document Classification**: Tests confirm correct document type identification
4. **Field Extraction**: Tests validate accurate extraction of specific fields with high confidence

## Notes on Binary Files

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control to prevent repository bloat. The `.gitignore` file in this directory ensures that only metadata and configuration files are tracked.

To obtain the actual test documents, contact the project administrator or download them from the designated secure storage location.