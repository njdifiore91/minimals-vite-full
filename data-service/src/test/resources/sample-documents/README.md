# Sample Documents for MCA Application Processing System

## Overview

This directory contains sample documents used for testing the Data Service component of the Merchant Cash Advance (MCA) Application Processing System. These documents simulate real-world inputs that the system will process, allowing for comprehensive testing of document classification, OCR data extraction, and application processing workflows.

## Purpose

The sample documents in this folder serve several critical purposes:

1. **Validation of OCR Accuracy**: Test the system's ability to maintain 99% data extraction accuracy through AI and machine learning as specified in the technical requirements.

2. **Document Classification Testing**: Verify that the Document Service correctly classifies different document types with high confidence levels.

3. **End-to-End Processing Verification**: Ensure the complete document processing pipeline functions correctly from email ingestion through final application processing.

4. **Regression Testing**: Provide a consistent set of test documents to detect any regressions in processing accuracy during development.

5. **Performance Benchmarking**: Establish baseline performance metrics for document processing times and accuracy rates.

## Document Organization

The sample documents are organized into the following categories, each in its own subdirectory:

### 1. Application Forms (`/application_forms`)

Contains MCA application forms in various formats:
- Standard typed applications
- Handwritten applications
- Partially completed applications
- Applications with various quality levels

### 2. Financial Documents (`/financial_documents`)

Includes financial records necessary for MCA application processing:
- Bank statements (multiple months)
- Credit card processing statements
- Profit and loss statements
- Balance sheets
- Cash flow statements

### 3. Identity Documents (`/identity_documents`)

Contains personal identification documents for business owners:
- Driver's licenses
- Passports
- National ID cards
- Other government-issued identification

### 4. Business Documents (`/business_documents`)

Includes various business verification documents:
- Business licenses
- Incorporation certificates
- Business tax returns
- Articles of organization
- Operating agreements

## Document Characteristics

The sample documents have been created with various characteristics to test the system's robustness:

### Document Formats
- **PDF**: Most common format for official documents
- **TIFF/TIF**: Common format for scanned documents
- **JPEG/JPG**: Typical format for mobile phone captures
- **PNG**: Alternative format for digital documents

### Content Types
- **Typed**: Machine-printed text (high OCR accuracy expected)
- **Handwritten**: Manually completed forms (more challenging for OCR)
- **Mixed**: Combination of typed and handwritten content

### Quality Variations
- **High**: Clear, high-resolution documents (baseline for testing)
- **Medium**: Slightly degraded quality (tests robustness)
- **Low**: Poor quality scans or images (tests system limits)

## Naming Conventions

All sample documents follow a consistent naming convention to facilitate testing:

```
[document_type]_[subtype]_[entity]_[additional_info].[format]
```

Examples:
- `mca_application_standard.pdf` - Standard MCA application form
- `bank_statement_acme_april.pdf` - April bank statement for Acme company
- `drivers_license_smith.jpg` - Driver's license for person with last name Smith
- `business_license_acme.pdf` - Business license for Acme company

## Metadata and Expected Results

Each document has associated metadata defined in the `metadata.json` file at the root of this directory. This metadata includes:

- Document type and subtype
- Format and quality information
- Expected classification results (type and confidence level)
- Expected data extraction results (field values and confidence levels)

This metadata is used by automated tests to verify that the system correctly processes each document and extracts the expected information with the required accuracy levels.

## Usage in Testing

These sample documents are used in various testing scenarios:

1. **Unit Tests**: Testing specific components of the Data Service
2. **Integration Tests**: Verifying interactions between services
3. **End-to-End Tests**: Validating complete processing workflows
4. **Performance Tests**: Measuring processing times and resource usage
5. **Accuracy Tests**: Verifying data extraction meets the 99% accuracy requirement

## Adding New Test Documents

When adding new test documents to this collection, please follow these guidelines:

1. **Place in Correct Directory**: Add the document to the appropriate category subdirectory
2. **Follow Naming Conventions**: Use the established naming pattern
3. **Update Metadata**: Add an entry to the `metadata.json` file with all required information
4. **Document Source**: Include information about the document's source or creation method
5. **Verify Gitignore**: Ensure the document is properly handled by the `.gitignore` configuration

## Important Notes

1. **Binary Files**: Actual document files (PDF, TIFF, JPEG, PNG) are not stored in the Git repository to prevent bloat. They must be downloaded separately from the secure document storage. See the `.gitignore` file for details.

2. **Sensitive Information**: All sample documents contain fictional data. No real personal or business information should ever be added to this test collection.

3. **Document Retrieval**: To obtain the actual document files, follow the instructions in the `.gitignore` file to download them from the secure S3 storage location.

4. **Consistency**: Maintain consistency between the actual documents and their metadata entries in `metadata.json`.

## Related Documentation

- See the Document Service documentation for details on document classification
- See the OCR Service documentation for information on data extraction processes
- See the Data Service documentation for application processing workflows

## Testing Requirements

These sample documents support the system's key requirements:

- Process applications in under 5 minutes from receipt to completion
- Maintain 99% data extraction accuracy through AI and machine learning
- Achieve 93% reduction in manual processing through automation
- Support all required document types for complete application processing