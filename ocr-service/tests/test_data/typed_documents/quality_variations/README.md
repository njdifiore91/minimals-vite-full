# Quality Variations Test Data

## Overview

This directory contains test documents with varying quality levels designed to evaluate the OCR service's robustness and accuracy across different document conditions. The primary goal is to ensure the OCR service meets the 99% data extraction accuracy requirement while handling real-world document quality variations.

## Purpose

In real-world scenarios, the OCR service will encounter documents of varying quality. This test suite provides a standardized set of documents with controlled quality variations to:

1. Test the OCR service's performance across different quality levels
2. Establish baseline accuracy metrics for each quality level
3. Validate improvements to OCR algorithms
4. Ensure consistent performance across document types and quality variations
5. Provide regression testing capabilities

## Quality Levels

The test documents are organized into three quality levels:

### High Quality

Documents with optimal characteristics for OCR processing:

- **Resolution**: 300+ DPI (dots per inch)
- **Contrast**: High contrast between text and background (dark text on light background)
- **Noise**: Minimal to no noise or artifacts
- **Focus**: Sharp, clear text with well-defined character edges
- **Alignment**: Properly aligned text with minimal to no skew
- **Expected OCR Confidence**: 95-100%
- **Expected Character Error Rate (CER)**: < 0.5%
- **Expected Word Error Rate (WER)**: < 1%

### Medium Quality

Documents with moderate degradation that may affect OCR accuracy:

- **Resolution**: 150-300 DPI
- **Contrast**: Adequate but not optimal contrast
- **Noise**: Some noise, specks, or minor artifacts
- **Focus**: Slightly blurred text but still readable
- **Alignment**: Minor skew (1-3 degrees)
- **Expected OCR Confidence**: 80-95%
- **Expected Character Error Rate (CER)**: 0.5-2%
- **Expected Word Error Rate (WER)**: 1-5%

### Low Quality

Documents with significant degradation that challenges OCR processing:

- **Resolution**: 72-150 DPI
- **Contrast**: Poor contrast, faded text
- **Noise**: Significant noise, stains, or artifacts
- **Focus**: Blurry text with poorly defined character edges
- **Alignment**: Noticeable skew (3-10 degrees)
- **Expected OCR Confidence**: 60-80%
- **Expected Character Error Rate (CER)**: 2-10%
- **Expected Word Error Rate (WER)**: 5-15%

## Quality Parameters

### Resolution

Resolution affects the amount of detail captured in the document image, measured in DPI (dots per inch):

- Higher resolution provides more pixels per character, enabling better feature extraction
- Lower resolution results in fewer pixels per character, making it harder to distinguish character features
- The OCR service should maintain high accuracy at 300+ DPI and degrade gracefully at lower resolutions

### Contrast

Contrast refers to the difference in intensity between text and background:

- High contrast (black text on white background) provides clear boundaries for character recognition
- Low contrast (faded text, colored backgrounds) makes character boundaries harder to detect
- The OCR service uses preprocessing techniques to enhance contrast before recognition

### Noise

Noise includes unwanted artifacts that can interfere with text recognition:

- Digital noise (compression artifacts, scanner noise)
- Physical noise (dust, stains, marks, speckles)
- Background patterns or textures
- The OCR service employs noise reduction algorithms to minimize these effects

### Focus/Blur

Focus affects the sharpness of character edges:

- Sharp focus provides clear character boundaries
- Blur makes character edges less distinct and can cause characters to merge
- The OCR service uses edge enhancement techniques to improve recognition of blurry text

### Alignment/Skew

Alignment refers to the orientation of text lines relative to the horizontal:

- Properly aligned text follows straight horizontal lines
- Skewed text is rotated at an angle
- The OCR service includes deskewing algorithms to correct alignment issues

## Testing Methodology

### Using the Test Documents

1. **Baseline Testing**: Process all quality levels to establish baseline accuracy metrics
2. **Algorithm Improvement**: When enhancing OCR algorithms, test against all quality levels to ensure improvements
3. **Regression Testing**: Run tests periodically to ensure continued performance
4. **Comparative Analysis**: Compare accuracy across quality levels to identify specific weaknesses

### Evaluation Metrics

1. **Character Error Rate (CER)**: Percentage of incorrectly recognized characters
   - Formula: CER = (S + D + I) / N
   - Where S = substitutions, D = deletions, I = insertions, N = total characters in ground truth

2. **Word Error Rate (WER)**: Percentage of incorrectly recognized words
   - Formula: WER = (S + D + I) / N
   - Where S = substitutions, D = deletions, I = insertions, N = total words in ground truth

3. **OCR Confidence Score**: The confidence level reported by the OCR engine for each character/word
   - Higher confidence generally correlates with higher accuracy
   - Confidence thresholds can be used to flag potential errors

### Expected Confidence Scores

The OCR service reports confidence scores for each recognized character and word. These scores should correlate with document quality:

| Quality Level | Expected Confidence Range | Action on Low Confidence |
|---------------|---------------------------|---------------------------|
| High          | 95-100%                   | Accept as accurate        |
| Medium        | 80-95%                    | Flag for review if < 85%  |
| Low           | 60-80%                    | Flag for review if < 75%  |

## Guidelines for Adding New Test Documents

### Naming Convention

All test documents should follow this naming pattern:

```
[document_type]_[quality_level]_[variation_parameter]_[value].[extension]
```

Example:
```
invoice_high_contrast_100.pdf
invoice_medium_resolution_200dpi.pdf
invoice_low_noise_high.pdf
```

### Required Metadata

Each test document should include a corresponding JSON metadata file with the same base name, containing:

```json
{
  "document_type": "[type of document]",
  "quality_level": "[high|medium|low]",
  "parameters": {
    "resolution": "[DPI value]",
    "contrast": "[high|medium|low]",
    "noise": "[minimal|moderate|significant]",
    "focus": "[sharp|slight_blur|blurry]",
    "alignment": "[proper|minor_skew|significant_skew]"
  },
  "ground_truth": "[path to ground truth text file]",
  "expected_metrics": {
    "cer": "[expected character error rate]",
    "wer": "[expected word error rate]",
    "confidence": "[expected confidence score range]"
  }
}
```

### Creating Quality Variations

To create new test documents with specific quality variations:

1. **Start with high-quality documents**: Begin with a clean, high-resolution document
2. **Apply controlled degradation**: Use image editing tools to systematically degrade specific parameters:
   - Reduce resolution by resampling the image
   - Decrease contrast by adjusting levels/curves
   - Add noise using noise filters
   - Apply Gaussian blur for focus degradation
   - Rotate the image slightly for alignment issues
3. **Create ground truth**: Manually transcribe the text content into a separate text file
4. **Document parameters**: Create the metadata JSON file with all relevant parameters

## Relationship to OCR Confidence Scores

The OCR service's confidence scoring system correlates with document quality parameters:

1. **Resolution impact**: Lower resolution typically results in lower confidence scores
2. **Contrast correlation**: Reduced contrast generally leads to lower confidence
3. **Noise effect**: Increased noise typically reduces confidence scores
4. **Focus influence**: Blurrier text generally receives lower confidence scores
5. **Alignment factor**: Skewed text often results in lower confidence scores

By understanding these relationships, developers can:

- Predict expected confidence scores based on document quality
- Identify specific quality issues based on confidence score patterns
- Implement targeted preprocessing to address specific quality challenges
- Set appropriate confidence thresholds for different document types and quality levels

## Usage in Test Suite

These test documents are used in the OCR service test suite to validate:

1. **Preprocessing effectiveness**: How well preprocessing improves recognition of lower-quality documents
2. **Algorithm robustness**: How well the OCR engine handles various quality challenges
3. **Confidence accuracy**: How well confidence scores correlate with actual accuracy
4. **Error patterns**: What types of errors occur at different quality levels

Refer to the test suite documentation for specific test cases and usage examples.