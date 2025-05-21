# Document Quality Variations for OCR Testing

## Overview

This directory contains test documents with varying quality levels designed to evaluate the OCR Service's robustness and accuracy across different document conditions. The test samples are categorized into high, medium, and low quality to ensure the OCR system can maintain the required 99% data extraction accuracy even when processing suboptimal documents.

## Purpose

The primary purposes of this quality variation testing are:

1. **Validate Robustness**: Ensure the OCR Service can handle documents of varying quality while maintaining high accuracy
2. **Establish Performance Baselines**: Document expected performance metrics for different quality levels
3. **Identify Quality Thresholds**: Determine minimum quality requirements for reliable extraction
4. **Test Enhancement Algorithms**: Evaluate preprocessing techniques that improve extraction from low-quality documents
5. **Calibrate Confidence Scores**: Ensure confidence scores accurately reflect extraction reliability across quality levels

## Quality Levels

Documents in this collection are categorized into three quality levels:

### High Quality

High-quality documents have optimal characteristics for OCR processing:

- **Resolution**: 300-600 DPI
- **Contrast**: Strong contrast between text and background (0.8-1.0 normalized ratio)
- **Noise Level**: Minimal to no noise (0.0-0.05 normalized ratio)
- **Blur**: Negligible blur (0.0-0.1 Gaussian blur sigma)
- **Skew**: Minimal skew (-1.0° to 1.0°)
- **Compression**: Minimal compression artifacts (0.0-0.1 normalized ratio)
- **Lighting**: Uniform lighting across the document (0.9-1.0 uniformity)

**Expected Performance**:
- Character Accuracy: 99-100%
- Word Accuracy: 98-100%
- Field Extraction Accuracy: 99-100%
- Confidence Scores: 0.95-1.0
- Processing Time: Baseline (1.0x)

### Medium Quality

Medium-quality documents have moderate imperfections that may affect OCR accuracy:

- **Resolution**: 150-299 DPI
- **Contrast**: Moderate contrast (0.6-0.79 normalized ratio)
- **Noise Level**: Moderate noise (0.06-0.15 normalized ratio)
- **Blur**: Moderate blur (0.11-0.3 Gaussian blur sigma)
- **Skew**: Moderate skew (-3.0° to 3.0°)
- **Compression**: Moderate compression artifacts (0.11-0.3 normalized ratio)
- **Lighting**: Somewhat non-uniform lighting (0.7-0.89 uniformity)

**Expected Performance**:
- Character Accuracy: 95-98%
- Word Accuracy: 93-97%
- Field Extraction Accuracy: 94-98%
- Confidence Scores: 0.85-0.94
- Processing Time: 1.5x baseline

### Low Quality

Low-quality documents have significant imperfections that challenge OCR accuracy:

- **Resolution**: 72-149 DPI
- **Contrast**: Poor contrast (0.4-0.59 normalized ratio)
- **Noise Level**: High noise (0.16-0.3 normalized ratio)
- **Blur**: Significant blur (0.31-0.5 Gaussian blur sigma)
- **Skew**: Significant skew (-10.0° to 10.0°)
- **Compression**: Significant compression artifacts (0.31-0.5 normalized ratio)
- **Lighting**: Non-uniform lighting (0.5-0.69 uniformity)

**Expected Performance**:
- Character Accuracy: 85-94%
- Word Accuracy: 80-92%
- Field Extraction Accuracy: 85-93%
- Confidence Scores: 0.7-0.84
- Processing Time: 2.5x baseline

## Directory Structure

```
quality_variations/
├── .gitignore                     # Excludes binary document files from version control
├── README.md                      # This documentation file
├── quality_parameters.json        # Detailed quality parameter definitions
├── high_quality_manifest.json     # Manifest for high-quality test documents
├── medium_quality_manifest.json   # Manifest for medium-quality test documents
└── low_quality_manifest.json      # Manifest for low-quality test documents
```

## Quality Parameters

The `quality_parameters.json` file defines the specific parameters used to characterize document quality. These parameters include:

1. **Resolution**: Measured in dots per inch (DPI), affects the amount of detail available for character recognition
2. **Contrast**: The difference between text and background, affects character boundary detection
3. **Noise Level**: Random variations in pixel values that can interfere with character recognition
4. **Blur**: Loss of edge definition that affects character boundary detection
5. **Skew**: Document rotation that affects line and paragraph detection
6. **Compression Artifacts**: Distortions introduced by lossy compression algorithms
7. **Lighting Uniformity**: Consistency of illumination across the document

Each parameter has a defined range for each quality level, and these ranges are used to categorize test documents and establish performance expectations.

## Impact on OCR Performance

Document quality significantly impacts OCR performance in several ways:

### Resolution Impact

Lower resolution reduces the number of pixels available to define each character, making it harder to distinguish similar characters (e.g., 'O' vs '0', 'l' vs 'I'). The OCR Service employs super-resolution techniques for low-resolution documents to enhance character definition before processing.

### Contrast Impact

Poor contrast makes it difficult to separate text from background, especially for thin fonts or small text. The OCR Service applies adaptive contrast enhancement to improve text visibility in low-contrast documents.

### Noise Impact

Noise can cause false character detection or obscure actual characters. The OCR Service uses noise reduction algorithms tailored to document type and noise characteristics.

### Blur Impact

Blur reduces edge definition, making character boundaries less distinct. The OCR Service applies deconvolution techniques to sharpen blurred text before processing.

### Skew Impact

Skewed documents affect line detection and text alignment. The OCR Service automatically detects and corrects document skew before processing.

### Confidence Score Correlation

There is a direct correlation between document quality and confidence scores:

- High-quality documents typically yield confidence scores of 0.95-1.0
- Medium-quality documents typically yield confidence scores of 0.85-0.94
- Low-quality documents typically yield confidence scores of 0.7-0.84

The OCR Service uses these confidence score ranges to determine when manual review is required:

- Scores ≥ 0.95: Auto-approved (high confidence)
- Scores 0.85-0.94: Flagged for spot-checking
- Scores 0.7-0.84: Sent for manual review
- Scores < 0.7: Rejected, requiring document resubmission

## Testing Methodology

### Automated Testing

The quality variation test suite automatically:

1. Processes documents of each quality level through the OCR pipeline
2. Compares extracted text and field values against expected results in the manifest
3. Validates that confidence scores align with expected ranges for each quality level
4. Measures processing time and resource usage
5. Generates reports on accuracy, precision, recall, and F1 score

### Performance Requirements

Even with low-quality documents, the OCR Service must maintain:

- Overall field extraction accuracy of at least 99% for critical fields
- Processing time within 5 seconds per page for low-quality documents
- Correct confidence score assignment (within expected ranges)
- Proper identification of documents requiring manual review

## Guidelines for Adding New Test Documents

When adding new quality variation test documents:

1. **Characterize the Document**: Measure and document quality parameters using the definitions in `quality_parameters.json`
2. **Categorize Appropriately**: Assign the document to the correct quality level based on its parameters
3. **Create Ground Truth**: Manually transcribe all text and field values to create accurate expected results
4. **Update Manifest**: Add the document to the appropriate quality level manifest with expected values and confidence thresholds
5. **Document Special Characteristics**: Note any unique challenges the document presents
6. **Follow Naming Conventions**: Use the standard naming format: `[document_type]_[subtype]_[quality]_[variant].[extension]`

## Relationship to OCR Service Requirements

This quality variation testing directly supports the following requirements from the technical specification:

1. **99% Data Extraction Accuracy**: Validates that the OCR Service maintains high accuracy across varying document qualities
2. **Processing Time Requirements**: Ensures documents are processed within time limits even when quality is suboptimal
3. **Confidence Scoring**: Verifies that confidence scores accurately reflect extraction reliability
4. **Automated Processing**: Tests the system's ability to automatically identify documents requiring manual review

## Hardware Considerations

Processing low-quality documents requires more computational resources:

- **CPU Usage**: 2-3x higher for low-quality documents
- **Memory Usage**: 1.5-2x higher for low-quality documents
- **GPU Acceleration**: Critical for real-time processing of low-quality documents

The test environment should match production specifications to ensure realistic performance metrics:

- **Minimum**: 4-core CPU, 16GB RAM, NVIDIA T4 GPU (8GB VRAM)
- **Recommended**: 8+ core CPU, 32GB RAM, NVIDIA A10 GPU (16GB VRAM)

## Notes on Binary Files

Actual document files (PDF, TIFF, PNG, JPEG) are excluded from version control to prevent repository bloat. The `.gitignore` file in this directory ensures that only metadata and configuration files are tracked.

To obtain the actual test documents, contact the project administrator or download them from the designated secure storage location.