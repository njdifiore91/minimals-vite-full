# Business Documents Test Samples

## Overview

This directory contains a collection of business document samples used for testing the OCR and document classification capabilities of the Merchant Cash Advance (MCA) Application Processing System. These samples are essential for validating that the system can accurately process, classify, and extract data from various types of business documents with the required 99% accuracy rate.

## Purpose

These test samples serve multiple purposes in the development and testing of the MCA system:

1. **Training Data**: Used to train the document classification models in the Document Service
2. **Testing Data**: Used to validate OCR extraction accuracy in the OCR Service
3. **Integration Testing**: Used in end-to-end tests of the document processing pipeline
4. **Quality Assurance**: Used to verify system performance against the 93% automation and 99% accuracy requirements
5. **Regression Testing**: Used to ensure new code changes don't affect existing functionality

## Document Types

This directory includes the following types of business documents:

| Document Type | Description | Common Fields for Extraction |
|---------------|-------------|------------------------------|
| Business Licenses | State and local business operating permits | License number, business name, issue date, expiration date, business type, jurisdiction |
| Incorporation Certificates | Legal documents proving business incorporation | Company name, incorporation date, state/jurisdiction, entity type, registered agent |
| Tax Returns | Business tax filings (federal and state) | EIN, tax year, business income, deductions, tax liability |
| Financial Statements | Balance sheets, income statements, cash flow statements | Revenue, expenses, assets, liabilities, reporting period |
| Bank Statements | Business banking activity records | Account number, balance, transaction history, statement period |
| Utility Bills | Proof of business location/operations | Service address, account number, billing period, amount due |
| Insurance Certificates | Proof of business insurance coverage | Policy number, coverage amounts, effective dates, insured name |
| Merchant Statements | Credit card processing statements | Merchant ID, processing volume, fees, statement period |
| Articles of Organization | LLC formation documents | Company name, formation date, member information, registered agent |
| Business Plans | Strategic business planning documents | Business model, financial projections, market analysis |

## Document Formats

The test samples are provided in various formats to ensure the system can handle different file types:

| Format | Description | Use Cases |
|--------|-------------|----------|
| PDF | Portable Document Format | Most common format for business documents; includes both scanned and digitally created documents |
| JPEG/JPG | Joint Photographic Experts Group | Photos of documents taken with mobile devices; compressed format with some quality loss |
| PNG | Portable Network Graphics | Screenshots and digital documents; lossless compression with support for transparency |
| TIFF | Tagged Image File Format | High-quality scanned documents; lossless format commonly used for document archiving |

## File Naming Convention

All test files follow this naming convention to ensure consistent usage and easy identification:

```
[document_type]_[variant]_[quality]_[id].[extension]
```

Where:
- **document_type**: Abbreviated type (e.g., `bus_license`, `incorp_cert`, `tax_return`)
- **variant**: Subtype or jurisdiction (e.g., `state`, `federal`, `llc`, `corp`)
- **quality**: Image quality indicator (`high`, `medium`, `low`, `damaged`)
- **id**: Unique identifier number
- **extension**: File format (`.pdf`, `.jpg`, `.png`, `.tiff`)

Examples:
- `bus_license_state_high_001.pdf`
- `tax_return_federal_medium_003.jpg`
- `incorp_cert_llc_damaged_002.tiff`

## Quality Variations

The test samples include documents of varying quality to test the system's robustness:

- **High Quality**: Pristine documents with clear text and formatting
- **Medium Quality**: Typical quality found in everyday business operations
- **Low Quality**: Challenging documents with issues like low resolution or poor contrast
- **Damaged**: Documents with physical damage (tears, stains, folds) or digital artifacts

## Usage Guidelines

### For Developers

1. Use these samples to test your OCR and classification implementations
2. Verify extraction accuracy against the known values in the corresponding metadata files
3. Test with various quality levels to ensure robustness
4. Include these samples in automated test suites

### For QA Engineers

1. Use these samples for validation testing of the document processing pipeline
2. Verify classification accuracy meets the 99% requirement
3. Validate extraction accuracy for all required fields
4. Test system performance with batches of mixed document types

## Adding New Samples

When adding new business document test samples, please follow these guidelines:

1. Ensure the document is anonymized and free of any personally identifiable information (PII)
2. Follow the established naming convention
3. Include samples in multiple formats when possible
4. Create corresponding metadata files with expected extraction results
5. Update the inventory list in this README if adding a new document type

## Metadata Files

Each test document has a corresponding JSON metadata file with the same name (different extension) containing:

- Expected classification results
- Expected field extractions with their locations
- Ground truth data for validation

Example metadata file structure:

```json
{
  "document_id": "bus_license_state_high_001",
  "document_type": "business_license",
  "expected_classification": {
    "type": "business_license",
    "subtype": "state",
    "confidence": 0.98
  },
  "expected_fields": {
    "license_number": {
      "value": "BL-12345-2023",
      "confidence": 0.99,
      "bounding_box": [120, 450, 250, 475]
    },
    "business_name": {
      "value": "Acme Business Solutions LLC",
      "confidence": 0.97,
      "bounding_box": [120, 300, 450, 325]
    },
    "issue_date": {
      "value": "2023-01-15",
      "confidence": 0.95,
      "bounding_box": [120, 500, 220, 525]
    },
    "expiration_date": {
      "value": "2024-01-14",
      "confidence": 0.94,
      "bounding_box": [350, 500, 450, 525]
    }
  }
}
```

## Related Documentation

- For details on the document classification process, see the Document Service documentation
- For information on OCR extraction capabilities, see the OCR Service documentation
- For integration with the overall application processing workflow, see the System Workflows documentation

## Compliance and Security

All test documents in this directory are synthetic or properly anonymized to comply with data privacy regulations. No real customer data is included in these test samples.