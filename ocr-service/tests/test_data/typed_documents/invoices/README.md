# Invoice Test Data

## Purpose

This directory contains test invoice documents used to validate the OCR Service's ability to extract data from various types of invoices with 99% accuracy as required by the Merchant Cash Advance (MCA) Application Processing System. These test samples are essential for:

- Training and validating the OCR models for invoice data extraction
- Testing the OCR Service's ability to handle different invoice formats and layouts
- Ensuring consistent extraction accuracy across various document qualities and conditions
- Providing benchmark documents for regression testing
- Validating the 99% data extraction accuracy requirement specified in section 0.1.1

## Invoice Types

This test data collection includes the following types of invoices:

1. **Vendor Invoices**: Standard B2B invoices from suppliers to businesses
2. **Service Invoices**: Invoices for professional services (consulting, legal, etc.)
3. **Retail Receipts**: Point-of-sale receipts from retail establishments
4. **Utility Bills**: Electricity, water, gas, and telecommunications invoices
5. **Equipment Invoices**: Invoices for equipment purchases or rentals
6. **Recurring Subscription Invoices**: Regular billing for subscription services
7. **Construction/Contractor Invoices**: Invoices for construction or contracting work
8. **Medical/Healthcare Invoices**: Invoices for medical services or supplies
9. **Transportation/Shipping Invoices**: Freight, shipping, and logistics invoices
10. **International Invoices**: Invoices with multiple currencies and international formats

## Document Quality Variations

To test the robustness of the OCR system, the invoice samples include various quality variations:

| Quality Variation | Description | Purpose |
|-------------------|-------------|----------|
| High Quality | Pristine, clear documents | Baseline for maximum accuracy |
| Low Resolution | 150 DPI or lower | Test extraction from low-resolution scans |
| Skewed | 5-15 degree rotation | Test alignment correction algorithms |
| Noisy | Added digital noise or artifacts | Test noise reduction preprocessing |
| Faded Text | Low contrast between text and background | Test contrast enhancement capabilities |
| Handwritten Annotations | Invoices with handwritten notes | Test mixed typed/handwritten content handling |
| Watermarked | Documents with watermarks | Test background removal capabilities |
| Compressed | JPEG compression artifacts | Test resilience to compression artifacts |
| Multiple Pages | Multi-page invoice documents | Test page handling and data aggregation |
| Small Font | Invoices with 8pt or smaller text | Test small text recognition capabilities |

## Naming Convention

Invoice test files follow this naming convention:

```
[invoice_type]_[industry]_[quality]_[variant].[extension]
```

Where:
- `invoice_type`: vendor, service, retail, utility, equipment, subscription, construction, medical, shipping, international
- `industry`: industry sector (retail, manufacturing, healthcare, technology, etc.)
- `quality`: hq (high quality), lq (low quality), skewed, noisy, faded, annotated, watermarked, compressed, multipage, smallfont
- `variant`: numeric identifier for variations of the same type/quality (01, 02, 03, etc.)
- `extension`: pdf, tiff, png, jpeg

Examples:
- `vendor_manufacturing_hq_01.pdf`: High-quality vendor invoice from manufacturing industry
- `retail_food_lq_03.jpeg`: Low-quality retail receipt from food industry
- `service_technology_skewed_02.pdf`: Skewed service invoice from technology industry

## Usage with Test Framework

These invoice test samples are used in conjunction with the `invoices_manifest.json` file, which contains:

- Expected field locations for each invoice
- Expected text content for each field
- Expected confidence scores for extraction
- Metadata about each document's characteristics

The OCR Service test suite uses this manifest to validate extraction accuracy against known values. Tests will verify that:

1. All required fields are correctly identified (invoice number, date, vendor, line items, totals, etc.)
2. Extracted text matches expected values within acceptable confidence thresholds
3. Processing time meets the 5-minute requirement specified in section 0.1.1
4. Overall extraction accuracy meets the 99% requirement

## Guidelines for Adding New Test Documents

When adding new invoice test documents to this collection:

1. Follow the established naming convention
2. Update the `invoices_manifest.json` file with expected extraction results
3. Include a variety of industries and document qualities
4. Ensure documents represent real-world scenarios
5. Include edge cases that test the limits of the OCR system
6. Remove any personally identifiable information (PII) from test documents
7. Compress documents appropriately to minimize repository size
8. Include at least one example of each field type that needs to be extracted

## Binary Files Storage

Actual invoice document files (PDF, TIFF, PNG, JPEG) are excluded from version control via the `.gitignore` file to prevent repository bloat. These files should be stored in the designated S3 bucket with the following structure:

```
s3://mca-documents-[environment]/test-data/typed_documents/invoices/
```

Where `[environment]` is one of: development, staging, production

To download the test files for local development, use the provided utility script:

```bash
# From the project root directory
./scripts/download_test_data.sh typed_documents/invoices
```

## Related Documentation

- [OCR Service Technical Specification](../../../README.md)
- [Document Classification Guidelines](../../test_models/README.md)
- [Test Data Management Policy](../../README.md)
- [Typed Documents Test Suite](../README.md)