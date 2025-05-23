# Sample Documents for MCA Application Processing System

This directory contains sample documents used for testing the Merchant Cash Advance (MCA) Application Processing System's data extraction, classification, and processing capabilities. These documents serve as standardized test data to ensure consistent validation of the system's accuracy and performance.

## Purpose

The sample documents in this folder are designed to:

- Provide consistent test data for unit, integration, and end-to-end testing
- Validate the 99% data extraction accuracy requirement specified in section 0.1.1
- Test document classification algorithms across various document types
- Verify OCR processing capabilities for both typed and handwritten text
- Benchmark system performance against documents of varying quality
- Support automated testing of the Data Service's processing logic

## Document Organization

The sample documents are organized into the following categories:

### 1. Application Forms

Merchant Cash Advance application forms containing business information, funding requests, and owner details.

**Examples:**
- Standard typed applications
- Handwritten applications
- Partially completed applications
- Low-quality scanned applications

### 2. Financial Documents

Financial records used to verify business performance and creditworthiness.

**Examples:**
- Bank statements (multiple banks and formats)
- Credit card processing statements
- Tax returns
- Profit and loss statements
- Balance sheets

### 3. Identity Documents

Documents used to verify the identity of business owners and authorized signatories.

**Examples:**
- Driver's licenses from various states
- Passports
- State ID cards
- Military IDs

### 4. Business Documents

Documents that verify business existence, structure, and compliance.

**Examples:**
- Business licenses
- Articles of incorporation
- Operating agreements
- EIN certificates
- Business insurance policies

## Document Characteristics

### Document Formats

The sample documents are provided in the following formats:

- **PDF**: Most common format, used for multi-page documents
- **JPEG**: Used for photographed documents (typically from mobile devices)
- **PNG**: Used for screenshots and digital documents
- **TIFF**: Used for faxed documents and legacy scanning systems

### Text Types

Documents contain various text types to test OCR capabilities:

- **Typed**: Machine-printed text (highest expected accuracy)
- **Handwritten**: Manually written text (challenging for OCR)
- **Mixed**: Combination of typed and handwritten content (e.g., forms with handwritten entries)

### Quality Variations

Documents are provided in different quality levels to test system resilience:

- **High**: Clear, high-resolution scans with good contrast
- **Medium**: Average quality with minor issues
- **Low**: Poor quality with potential OCR challenges
- **Damaged**: Documents with physical damage (tears, stains, etc.)

## Naming Conventions

Sample documents follow a consistent naming pattern to facilitate identification:

```
[document_type]_[subtype]_[quality]_[sequence].ext
```

Examples:
- `mca_application_standard_001.pdf`: Standard MCA application, sequence #1
- `bank_statement_acme_april_001.pdf`: Bank statement for Acme business, April, sequence #1
- `drivers_license_ca_standard.pdf`: California driver's license, standard quality
- `business_license_state_high_001.pdf`: State business license, high quality, sequence #1

## Usage in Testing

### Integration with Metadata

All sample documents are referenced in the `metadata.json` file, which contains:

- Document classification information
- Expected field values for validation
- Confidence scores for OCR extraction
- Bounding box coordinates for key fields
- Test scenario associations

### Test Scenarios

The documents are organized into test sets that represent complete or partial application packages:

1. **Complete Application Set**: Full document set with high-quality scans
2. **Partial Application Set**: Incomplete document set requiring follow-up
3. **Low Quality Application Set**: Complete set with poor quality documents
4. **Handwritten Application Set**: Application with handwritten forms

### Performance Benchmarks

Each document and document set has associated performance benchmarks:

- Expected processing time
- Expected automation level
- Expected extraction accuracy
- Classification confidence thresholds

## Guidelines for Adding New Test Documents

When adding new sample documents to this collection:

1. **Follow naming conventions** described above
2. **Update metadata.json** with document details and expected extraction results
3. **Include varied quality levels** to test system resilience
4. **Anonymize sensitive information** while maintaining realistic data patterns
5. **Add documents to appropriate category folders**
6. **Document expected field values** for validation testing
7. **Include in relevant test scenarios** if applicable

## Cross-Service Testing

These sample documents are used across multiple services in the MCA processing pipeline:

- **Email Service**: Tests email attachment extraction
- **Document Service**: Tests document classification
- **OCR Service**: Tests data extraction from various document types
- **Data Service**: Tests business rule application and data processing
- **Notification Service**: Tests status updates based on document processing

## Validation Rules

The sample documents support testing of various validation rules:

- Business validation (name, EIN, business type)
- Financial validation (account numbers, statement periods)
- Identity validation (name matching, expiration dates)
- Cross-document validation (consistency across documents)

## Maintaining Test Data

The sample document collection should be periodically reviewed and updated to:

- Add new document types as they are encountered in production
- Improve coverage of edge cases and rare document formats
- Update expected values as business rules change
- Ensure continued alignment with the 99% accuracy requirement

---

For detailed information about specific documents, refer to the `metadata.json` file and the category-specific metadata files in each subdirectory.