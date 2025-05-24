# Identity Documents Test Samples

## Purpose

This directory contains a collection of sample identity documents used for testing the document classification and OCR extraction capabilities of the Merchant Cash Advance (MCA) Application Processing System. These samples are essential for:

- Testing the Document Service's ability to correctly classify identity documents with high confidence (≥75%)
- Validating the OCR Service's ability to extract personal information from identity documents with 99% accuracy
- Ensuring consistent processing of various identity document types across different formats and quality levels
- Supporting automated testing of the document processing pipeline
- Providing reference samples for debugging and troubleshooting

## Document Types

This collection includes the following types of identity documents:

### Driver's Licenses

- US state driver's licenses (multiple states with varying formats)
- International driver's licenses
- Commercial driver's licenses (CDL)
- Provisional/temporary licenses

### Passports

- US passports (including newer and older versions)
- International passports (various countries)
- Passport cards
- Emergency travel documents

### National ID Cards

- National identity cards from various countries
- Permanent resident cards (Green cards)
- Military ID cards
- State-issued identification cards

### Other Identity Documents

- Social Security cards
- Birth certificates
- Tribal identification cards
- Consular identification cards

## Document Characteristics

The test samples include documents with various characteristics to ensure robust testing:

### File Formats

- PDF (both searchable and image-only)
- JPEG/JPG (various compression levels)
- PNG (with transparency and without)
- TIFF (single and multi-page)

### Quality Variations

- High-quality scans (300+ DPI)
- Medium-quality scans (150-300 DPI)
- Low-quality scans (<150 DPI)
- Mobile phone photographs (various lighting conditions)
- Documents with wear, creases, or partial damage
- Watermarked documents

### Security Features

- Holograms
- Microprinting
- UV-reactive elements
- Barcodes and QR codes
- Machine-readable zones (MRZ)

## Naming Convention

All test files follow this naming convention to ensure consistent organization and usage:

```
[document_type]_[country/state]_[format]_[quality]_[variant].[extension]
```

Where:
- `document_type`: dl (driver's license), pp (passport), id (national ID), etc.
- `country/state`: ISO country code or US state abbreviation (e.g., US, CA, TX, UK)
- `format`: pdf, jpg, png, tiff
- `quality`: high, med, low
- `variant`: front, back, open, sample1, sample2, etc. (optional)
- `extension`: pdf, jpg, png, tif

Examples:
- `dl_CA_jpg_high_front.jpg` - California driver's license front, high quality, JPG format
- `pp_US_pdf_med.pdf` - US passport, medium quality, PDF format
- `id_UK_png_low_sample1.png` - UK national ID card, low quality, PNG format, sample variant 1

## Usage Guidelines

### For Testing

1. Use these samples to test the document classification capabilities of the Document Service
2. Validate OCR extraction accuracy against the known data in these documents
3. Test the system's ability to handle various document qualities and formats
4. Include these samples in automated test suites for regression testing

### For Development

1. Reference these samples when implementing new document classification models
2. Use as training data for improving OCR extraction accuracy
3. Benchmark system performance against these standard samples

## Adding New Samples

When adding new identity document samples to this collection, please follow these guidelines:

1. **Anonymize all personal information** - Replace real personal data with fictional information
2. **Follow the naming convention** described above
3. **Include diverse examples** - Add documents with varying qualities, formats, and characteristics
4. **Document the expected extraction fields** - Create a companion JSON file with the same name containing the expected extraction results
5. **Optimize file size** - Keep file sizes reasonable while maintaining necessary quality for testing
6. **Include metadata** - Add relevant metadata in the companion JSON file (e.g., document type, issuing authority)

## Legal Considerations

All identity document samples in this collection:

1. Must be properly anonymized with fictional personal information
2. Must not contain actual personal identifiable information (PII)
3. Should be clearly marked as "SAMPLE" or "SPECIMEN" where possible
4. Must comply with relevant regulations regarding the reproduction of identity documents

## Related Documentation

- For OCR extraction specifications, see the OCR Service documentation
- For document classification details, see the Document Service documentation
- For integration with the document processing pipeline, see the system workflow documentation