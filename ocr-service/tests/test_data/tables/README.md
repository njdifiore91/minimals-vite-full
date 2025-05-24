# Tables Test Data for OCR Service

## Overview

This directory contains test data for validating the OCR service's ability to extract data from tabular documents with high accuracy. The test samples in this directory are specifically designed to evaluate the OCR service's performance in processing various types of tabular data formats, complexities, and quality variations.

## Purpose

The primary purpose of this test data collection is to:

1. Validate the OCR service's ability to extract data from tabular documents with 99% accuracy as required by the MCA Application Processing System
2. Test the robustness of the OCR algorithms against various table formats and complexities
3. Provide a consistent set of test cases for regression testing
4. Benchmark performance improvements in the OCR pipeline
5. Support the development of table-specific extraction algorithms

## Table Document Types

This directory includes the following types of tabular documents:

### Financial Documents

- **Bank Statements**: Monthly account activity with transaction details
- **Financial Statements**: Balance sheets, income statements, cash flow statements
- **Transaction Histories**: Credit card statements, payment records
- **Invoices**: Itemized billing documents with line items and totals

### Business Documents

- **Inventory Lists**: Product listings with quantities, SKUs, and pricing
- **Price Lists**: Product catalogs with pricing information
- **Sales Reports**: Periodic sales data organized by product, region, or time
- **Expense Reports**: Itemized business expenses with categories and amounts

### Application Forms

- **Merchant Information Tables**: Business details in tabular format
- **Revenue Tables**: Historical revenue data for merchant evaluation
- **Fee Schedules**: Advance fee structures and repayment terms

## Table Complexity Variations

The test data is organized to include varying levels of complexity:

### Simple Tables

- Clean, well-defined borders
- Regular grid structure
- Consistent spacing
- High-quality printing/scanning
- Typed text only
- Single-page tables

### Complex Tables

- Merged cells (spanning multiple rows or columns)
- Nested tables (tables within tables)
- Irregular spacing or alignment
- Mixed content (text, numbers, symbols)
- Varying font styles and sizes
- Multi-page tables with headers/footers

### Challenging Tables

- Missing or partial borders
- Low-quality scans or images
- Handwritten entries in cells
- Rotated or skewed tables
- Tables with background colors or patterns
- Tables with overlapping elements

## File Naming Convention

Test files follow this naming convention to facilitate easy identification and usage:

```
[document_type]_[complexity]_[format]_[variant].{extension}
```

Where:
- **document_type**: The category of document (e.g., bank_statement, invoice, inventory)
- **complexity**: simple, complex, or challenging
- **format**: The structural format (e.g., grid, borderless, merged_cells)
- **variant**: A numeric identifier for variations of the same type (e.g., 01, 02)
- **extension**: File format (e.g., pdf, jpg, png, tiff)

Examples:
- `bank_statement_simple_grid_01.pdf`
- `invoice_complex_merged_cells_03.jpg`
- `inventory_challenging_handwritten_02.png`

## Ground Truth Data

Each test document is accompanied by a corresponding ground truth file in JSON format with the same base name. These files contain the expected extraction results for validation purposes:

```
[document_name].json
```

The ground truth JSON files include:

- Table boundaries (coordinates)
- Row and column definitions
- Cell content with expected text
- Cell relationships (merged cells, etc.)
- Confidence thresholds for validation

## Usage Guidelines

### Running Tests

To use these test files with the OCR service:

1. Import the test files using the test harness
2. Process the files through the OCR pipeline
3. Compare the extraction results with the ground truth data
4. Validate accuracy against the 99% requirement

### Adding New Test Documents

When adding new test documents to this collection:

1. Follow the established naming convention
2. Include both the document file and its ground truth JSON file
3. Document any special characteristics or edge cases in the file
4. Ensure the test case covers a unique scenario not already represented
5. Verify the ground truth data is accurate before committing

### Performance Benchmarking

These test files should be used to benchmark the OCR service's performance metrics:

- Extraction accuracy (character-level and structural)
- Processing time
- Memory usage
- GPU utilization (when applicable)

## Test Data Organization

The test files are organized into subdirectories based on document type and complexity:

```
/tables
  /financial_documents
    /bank_statements
    /financial_statements
    /transaction_histories
    /invoices
  /business_documents
    /inventory_lists
    /price_lists
    /sales_reports
    /expense_reports
  /application_forms
    /merchant_information
    /revenue_tables
    /fee_schedules
```

## Technical Implementation

The OCR service uses a combination of techniques to process tabular data:

1. **Table Detection**: Identifies table boundaries using computer vision techniques
2. **Structure Recognition**: Determines rows, columns, and cell relationships
3. **Text Extraction**: Applies OCR to extract text content from each cell
4. **Post-processing**: Validates and corrects extraction results based on context

These test files are designed to validate each step of this pipeline and ensure the overall accuracy meets the 99% requirement specified in the technical specification.

## Contribution

When contributing new test files, please ensure they:

1. Represent real-world scenarios relevant to the MCA application process
2. Include proper ground truth data for validation
3. Follow the established naming conventions
4. Are properly documented with any special characteristics

---

*This test data is part of the OCR Service for the Merchant Cash Advance (MCA) Application Processing System.*