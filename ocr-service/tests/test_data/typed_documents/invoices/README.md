# Invoice Test Data

## Purpose

This directory contains a collection of sample invoice documents used for testing the OCR Service's ability to extract data from various types of invoices with high accuracy. These test samples are essential for validating that the OCR Service meets the requirement of 99% data extraction accuracy through AI and machine learning as specified in the technical specifications.

The invoice test data serves several critical purposes:

1. **Validation of OCR accuracy** for invoice-specific fields and layouts
2. **Testing of field extraction** for invoice-specific data points (invoice numbers, dates, line items, totals)
3. **Verification of confidence scoring** for extracted invoice data
4. **Performance benchmarking** for invoice processing speed
5. **Regression testing** to ensure continued accuracy as the OCR models evolve

## Invoice Types Included

This test data collection includes the following types of invoices, each with unique characteristics and extraction challenges:

### Vendor Invoices
- **Supplier invoices** - Standard B2B invoices from suppliers to businesses
- **Wholesale invoices** - Bulk order invoices with multiple line items and quantity discounts
- **Manufacturing invoices** - Invoices for raw materials and manufacturing components

### Service Invoices
- **Professional services** - Invoices for consulting, legal, accounting services
- **Subscription services** - Recurring billing invoices with subscription details
- **Contractor invoices** - Invoices for project-based work with hourly rates

### Retail Receipts
- **Point-of-sale receipts** - Standard retail transaction receipts
- **E-commerce order confirmations** - Online purchase receipts
- **Return receipts** - Documentation of returned merchandise

### Financial Invoices
- **Loan statements** - Documentation of loan payments and terms
- **Equipment leasing** - Invoices for leased business equipment
- **Financing agreements** - Documentation of financing terms and payments

### Utility Invoices
- **Electricity bills** - Monthly utility statements with usage metrics
- **Telecommunications** - Phone and internet service invoices
- **Water/sewage bills** - Municipal utility invoices

## Document Quality Variations

To test the robustness of the OCR system, invoice samples are provided in various quality levels:

### Quality Levels
1. **High Quality** - Clear, high-resolution scans with optimal contrast
2. **Medium Quality** - Typical quality scans with minor imperfections
3. **Low Quality** - Challenging documents with issues like:
   - Faded text
   - Poor contrast
   - Scan artifacts
   - Skewed alignment
   - Background noise

### Format Variations
- **Digital native PDFs** - Programmatically generated invoices
- **Scanned documents** - Physical documents converted to digital format
- **Faxed documents** - Documents with typical fax artifacts and quality issues
- **Mobile phone captures** - Documents photographed with smartphone cameras

### Content Variations
- **Simple invoices** - Basic invoices with minimal line items
- **Complex invoices** - Detailed invoices with numerous line items and calculations
- **Multi-page invoices** - Invoices spanning multiple pages
- **Invoices with attachments** - Invoices with supplementary documentation

## Naming Convention

Invoice test files follow this naming convention to facilitate easy identification and selection:

```
[invoice_type]_[subtype]_[quality]_[variant].[extension]
```

Examples:
- `vendor_supplier_high_001.pdf` - High-quality supplier invoice, variant 1
- `service_consulting_medium_002.pdf` - Medium-quality consulting invoice, variant 2
- `retail_pos_low_003.pdf` - Low-quality point-of-sale receipt, variant 3

Additional naming elements may include:
- `_handwritten` - Contains handwritten annotations or fields
- `_damaged` - Deliberately damaged document (coffee stains, tears, etc.)
- `_rotated` - Document with non-standard orientation

## Test Data Organization

### Directory Structure

The invoice test data is organized into subdirectories by invoice type:

```
invoices/
├── vendor/
├── service/
├── retail/
├── financial/
└── utility/
```

### Manifest File

All test documents are registered in the `invoices_manifest.json` file, which contains:

- File paths relative to this directory
- Expected OCR extraction results for each document
- Document characteristics and metadata
- Expected confidence scores for key fields

The manifest file is used by automated tests to validate OCR extraction accuracy against known values.

## Using the Test Data

### For Manual Testing

1. Select invoice samples that represent your test scenario
2. Process them through the OCR Service using the API or test utilities
3. Compare the extracted data with the expected results in the manifest

### For Automated Testing

1. Use the test utilities in `ocr-service/tests/test_models/test_typed_text_model.py`
2. Reference the manifest file for expected extraction results
3. Validate extraction accuracy and confidence scores

### Performance Testing

Use the full set of invoice samples to benchmark:
- Processing time per invoice
- Accuracy rates across different invoice types
- Confidence score distribution
- Resource utilization during processing

## Guidelines for Adding New Test Documents

When adding new invoice test documents to this collection:

1. **Follow the naming convention** described above
2. **Add the document to the appropriate subdirectory** based on type
3. **Update the manifest file** with:
   - Document path
   - Expected extraction results
   - Document characteristics
   - Expected confidence scores
4. **Include diverse examples** that test different aspects of OCR capability
5. **Ensure proper licensing** for any real-world documents (redact sensitive information)
6. **Document any special characteristics** in the manifest metadata

## Validation Requirements

The OCR Service must correctly extract the following fields from invoice documents with 99% accuracy:

### Required Fields
- Invoice number
- Invoice date
- Due date
- Vendor/supplier information
- Customer/billing information
- Line items (description, quantity, unit price, total)
- Subtotal
- Tax amounts
- Total amount
- Payment terms

### Confidence Scoring

Each extracted field must include a confidence score (0.0-1.0) indicating the OCR system's confidence in the extraction accuracy. Fields with confidence scores below configurable thresholds should be flagged for human verification.

## Integration with OCR Pipeline

These test documents are processed through the complete OCR pipeline:

1. Document classification by the Document Service
2. Text extraction by the OCR Service's `typed_text_model.py`
3. Field identification based on document structure
4. Confidence scoring for each extracted field
5. JSON formatting of extraction results

The test suite validates each step of this pipeline to ensure end-to-end accuracy.