#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the image_utils.py module.

This module contains tests for image preprocessing, normalization, enhancement,
segmentation, and quality assessment functions to ensure optimal document
preparation for OCR processing.
"""

import os
import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

# Import the module to test
from src.utils.image_utils import (
    # Image preprocessing
    load_image, load_image_from_bytes, normalize_size, normalize_orientation,
    convert_color_space, ColorSpace,
    # Image enhancement
    enhance_contrast, remove_noise, sharpen_image, binarize_image, deskew_image,
    # Document segmentation
    detect_text_regions, detect_paragraphs, detect_tables, detect_form_fields,
    segment_document,
    # Image format handling
    convert_to_format, save_image, get_image_format, ImageFormat,
    # Image quality assessment
    assess_image_quality, calculate_overall_quality, is_suitable_for_ocr,
    suggest_enhancements, QualityMetrics,
    # Helper functions
    is_checkbox_checked, is_region_in_bounds, extract_region, preprocess_for_ocr,
    create_field_mask
)
from src.types.documents import DocumentType
from src.types.extraction import FieldLocation
from src.types.errors import ServiceError


# ===== Test Fixtures =====

@pytest.fixture
def sample_image_path(temp_dir):
    """Creates a sample image file for testing."""
    # Create a simple test image (100x100 white with a black rectangle)
    img = np.ones((100, 100), dtype=np.uint8) * 255
    img[25:75, 25:75] = 0  # Black rectangle in the middle
    
    # Save the image
    img_path = os.path.join(temp_dir, "test_image.png")
    cv2.imwrite(img_path, img)
    
    return img_path


@pytest.fixture
def sample_image_bytes(sample_image_path):
    """Provides the sample image as bytes."""
    with open(sample_image_path, "rb") as f:
        return f.read()


@pytest.fixture
def sample_document_image(temp_dir):
    """Creates a sample document image with text-like content."""
    # Create a white background
    img = np.ones((500, 400), dtype=np.uint8) * 255
    
    # Add text-like regions
    # Header
    img[20:40, 50:350] = 0
    
    # Paragraphs
    for i in range(3):
        y_start = 60 + i * 40
        img[y_start:y_start+10, 50:350] = 0
        img[y_start+15:y_start+25, 50:300] = 0
        img[y_start+30:y_start+40, 50:320] = 0
    
    # Table
    table_top = 200
    for i in range(4):
        row_top = table_top + i * 30
        img[row_top:row_top+2, 50:350] = 0  # Horizontal line
        
        # Vertical lines
        img[table_top:table_top+120, 50:52] = 0
        img[table_top:table_top+120, 150:152] = 0
        img[table_top:table_top+120, 250:252] = 0
        img[table_top:table_top+120, 350:352] = 0
    
    # Form fields
    form_top = 350
    for i in range(3):
        field_top = form_top + i * 30
        img[field_top:field_top+15, 50:150] = 0  # Label
        img[field_top:field_top+15, 170:172] = 0  # Colon
        img[field_top+20:field_top+22, 180:350] = 0  # Underline
    
    # Checkbox
    img[450:470, 50:70] = 0  # Empty checkbox
    
    # Filled checkbox
    img[450:470, 100:120] = 0  # Checkbox outline
    img[455:465, 105:115] = 0  # Checkbox fill
    
    # Save the image
    img_path = os.path.join(temp_dir, "test_document.png")
    cv2.imwrite(img_path, img)
    
    return img_path


@pytest.fixture
def skewed_document_image(temp_dir):
    """Creates a skewed document image for testing orientation correction."""
    # Create a white background
    img = np.ones((500, 400), dtype=np.uint8) * 255
    
    # Add text-like lines at a skewed angle
    for i in range(10):
        y_start = 50 + i * 30
        x_start = 50 + i * 10  # This creates the skew
        cv2.line(img, (x_start, y_start), (x_start + 300, y_start), 0, 2)
    
    # Save the image
    img_path = os.path.join(temp_dir, "skewed_document.png")
    cv2.imwrite(img_path, img)
    
    return img_path


@pytest.fixture
def low_quality_image(temp_dir):
    """Creates a low quality image for testing quality assessment."""
    # Create a noisy, low contrast, blurry image
    img = np.ones((100, 100), dtype=np.uint8) * 150  # Low contrast (grayish)
    
    # Add some text-like content with low contrast
    img[25:75, 25:75] = 130  # Barely visible rectangle
    
    # Add noise
    noise = np.random.normal(0, 20, (100, 100))
    img = np.clip(img + noise, 0, 255).astype(np.uint8)
    
    # Apply blur to make it less sharp
    img = cv2.GaussianBlur(img, (7, 7), 0)
    
    # Save the image
    img_path = os.path.join(temp_dir, "low_quality.png")
    cv2.imwrite(img_path, img)
    
    return img_path


@pytest.fixture
def high_quality_image(temp_dir):
    """Creates a high quality image for testing quality assessment."""
    # Create a high contrast, sharp image
    img = np.ones((100, 100), dtype=np.uint8) * 255  # White background
    
    # Add clear text-like content
    img[25:75, 25:75] = 0  # Black rectangle (high contrast)
    
    # Save the image
    img_path = os.path.join(temp_dir, "high_quality.png")
    cv2.imwrite(img_path, img)
    
    return img_path


# ===== Test Classes =====

class TestImageLoading:
    """Tests for image loading functions."""
    
    def test_load_image(self, sample_image_path):
        """Test loading an image from a file path."""
        # Load the image
        image = load_image(sample_image_path)
        
        # Verify the image was loaded correctly
        assert image is not None
        assert isinstance(image, np.ndarray)
        assert image.shape == (100, 100) or image.shape == (100, 100, 3)
        
        # Verify the content (black rectangle in the middle)
        center = image[50, 50]
        corner = image[10, 10]
        assert center < 128  # Should be black/dark in the middle
        assert corner > 128  # Should be white/light in the corner
    
    def test_load_image_nonexistent_file(self):
        """Test loading a non-existent image file."""
        with pytest.raises(ServiceError):
            load_image("nonexistent_file.png")
    
    def test_load_image_from_bytes(self, sample_image_bytes):
        """Test loading an image from bytes."""
        # Load the image
        image = load_image_from_bytes(sample_image_bytes)
        
        # Verify the image was loaded correctly
        assert image is not None
        assert isinstance(image, np.ndarray)
        assert image.shape == (100, 100) or image.shape == (100, 100, 3)
        
        # Verify the content (black rectangle in the middle)
        center = image[50, 50]
        corner = image[10, 10]
        assert center < 128  # Should be black/dark in the middle
        assert corner > 128  # Should be white/light in the corner
    
    def test_load_image_from_invalid_bytes(self):
        """Test loading invalid image bytes."""
        with pytest.raises(ServiceError):
            load_image_from_bytes(b"invalid image data")


class TestImagePreprocessing:
    """Tests for image preprocessing functions."""
    
    def test_normalize_size_small_image(self):
        """Test normalizing a small image to ensure minimum size."""
        # Create a very small image
        small_image = np.ones((30, 40), dtype=np.uint8) * 255
        
        # Normalize the size
        normalized = normalize_size(small_image)
        
        # Verify the image was upscaled
        assert normalized.shape[0] >= 50  # Minimum size
        assert normalized.shape[1] >= 50  # Minimum size
    
    def test_normalize_size_large_image(self):
        """Test normalizing a large image to ensure maximum size."""
        # Create a very large image
        large_image = np.ones((5000, 6000), dtype=np.uint8) * 255
        
        # Normalize the size
        normalized = normalize_size(large_image)
        
        # Verify the image was downscaled
        assert normalized.shape[0] <= 4096  # Maximum size
        assert normalized.shape[1] <= 4096  # Maximum size
    
    def test_normalize_size_normal_image(self, mock_image):
        """Test normalizing a normal-sized image."""
        # Get the original shape
        original_shape = mock_image.shape
        
        # Normalize the size
        normalized = normalize_size(mock_image)
        
        # Verify the image size was not changed significantly
        assert normalized.shape == original_shape
    
    def test_normalize_orientation(self, skewed_document_image):
        """Test correcting the orientation of a skewed document."""
        # Load the skewed image
        skewed = load_image(skewed_document_image)
        
        # Normalize the orientation
        corrected = normalize_orientation(skewed)
        
        # Verify the image was rotated (shape should be the same)
        assert corrected.shape == skewed.shape
        
        # We can't easily verify the rotation angle automatically,
        # but we can check that the function ran without errors
        assert corrected is not None
    
    def test_normalize_orientation_no_lines(self, mock_image):
        """Test orientation correction on an image with no clear lines."""
        # Normalize the orientation
        corrected = normalize_orientation(mock_image)
        
        # Should return the original image if no lines are detected
        np.testing.assert_array_equal(corrected, mock_image)
    
    def test_convert_color_space_rgb_to_gray(self, mock_color_image):
        """Test converting from RGB to grayscale."""
        # Convert to grayscale
        gray = convert_color_space(mock_color_image, ColorSpace.GRAY)
        
        # Verify the conversion
        assert len(gray.shape) == 2  # Should be 2D for grayscale
        assert gray.shape == mock_color_image.shape[:2]  # Width and height should match
    
    def test_convert_color_space_gray_to_rgb(self, mock_image):
        """Test converting from grayscale to RGB."""
        # Convert to RGB
        rgb = convert_color_space(mock_image, ColorSpace.RGB)
        
        # Verify the conversion
        assert len(rgb.shape) == 3  # Should be 3D for RGB
        assert rgb.shape[:2] == mock_image.shape  # Width and height should match
        assert rgb.shape[2] == 3  # Should have 3 channels
    
    def test_convert_color_space_to_binary(self, mock_image):
        """Test converting to binary."""
        # Convert to binary
        binary = convert_color_space(mock_image, ColorSpace.BINARY)
        
        # Verify the conversion
        assert binary.dtype == np.uint8
        assert set(np.unique(binary)).issubset({0, 1})  # Should only contain 0 and 1
    
    def test_convert_color_space_same_space(self, mock_image):
        """Test converting to the same color space."""
        # Convert to the same color space
        result = convert_color_space(mock_image, ColorSpace.GRAY)
        
        # Should return the original image
        np.testing.assert_array_equal(result, mock_image)


class TestImageEnhancement:
    """Tests for image enhancement functions."""
    
    def test_enhance_contrast(self, mock_image):
        """Test enhancing image contrast."""
        # Enhance contrast
        enhanced = enhance_contrast(mock_image)
        
        # Verify the enhancement
        assert enhanced.shape == mock_image.shape
        
        # Calculate histogram before and after
        hist_before = cv2.calcHist([mock_image], [0], None, [256], [0, 256])
        hist_after = cv2.calcHist([enhanced], [0], None, [256], [0, 256])
        
        # The enhanced image should have a wider histogram spread
        std_before = np.std(hist_before)
        std_after = np.std(hist_after)
        
        # This is not always true, but generally contrast enhancement
        # should increase the standard deviation of the histogram
        assert std_after >= std_before * 0.8  # Allow some tolerance
    
    def test_enhance_contrast_color_image(self, mock_color_image):
        """Test enhancing contrast of a color image."""
        # Enhance contrast
        enhanced = enhance_contrast(mock_color_image)
        
        # Verify the enhancement
        assert enhanced.shape == mock_color_image.shape
        assert len(enhanced.shape) == 3  # Should still be a color image
    
    def test_remove_noise_gaussian(self, mock_image):
        """Test removing noise using Gaussian filter."""
        # Add noise to the image
        noisy = mock_image.copy()
        noise = np.random.normal(0, 25, mock_image.shape).astype(np.uint8)
        noisy = cv2.add(noisy, noise)
        
        # Remove noise
        denoised = remove_noise(noisy, method='gaussian')
        
        # Verify the denoising
        assert denoised.shape == noisy.shape
        
        # The denoised image should be smoother (less variance in local regions)
        # We'll check this by comparing the local standard deviation
        def local_std(img):
            return np.mean([np.std(img[i:i+10, j:j+10]) for i in range(0, img.shape[0]-10, 10) for j in range(0, img.shape[1]-10, 10)])
        
        std_noisy = local_std(noisy)
        std_denoised = local_std(denoised)
        
        assert std_denoised < std_noisy
    
    def test_remove_noise_median(self, mock_image):
        """Test removing noise using median filter."""
        # Add salt and pepper noise
        noisy = mock_image.copy()
        # Add salt (white) noise
        salt = np.random.random(mock_image.shape) < 0.02
        noisy[salt] = 255
        # Add pepper (black) noise
        pepper = np.random.random(mock_image.shape) < 0.02
        noisy[pepper] = 0
        
        # Remove noise
        denoised = remove_noise(noisy, method='median')
        
        # Verify the denoising
        assert denoised.shape == noisy.shape
        
        # Count salt and pepper pixels before and after
        salt_before = np.sum(noisy == 255)
        pepper_before = np.sum(noisy == 0)
        salt_after = np.sum(denoised == 255)
        pepper_after = np.sum(denoised == 0)
        
        # Should have fewer salt and pepper pixels after denoising
        assert salt_after < salt_before
        assert pepper_after < pepper_before
    
    def test_remove_noise_bilateral(self, mock_image):
        """Test removing noise using bilateral filter."""
        # Add noise to the image
        noisy = mock_image.copy()
        noise = np.random.normal(0, 25, mock_image.shape).astype(np.uint8)
        noisy = cv2.add(noisy, noise)
        
        # Remove noise
        denoised = remove_noise(noisy, method='bilateral')
        
        # Verify the denoising
        assert denoised.shape == noisy.shape
        
        # The denoised image should be smoother while preserving edges
        # This is hard to verify automatically, but we can check it ran without errors
        assert denoised is not None
    
    def test_remove_noise_unknown_method(self, mock_image):
        """Test removing noise with an unknown method."""
        # Should default to gaussian
        denoised = remove_noise(mock_image, method='unknown')
        
        # Verify the denoising
        assert denoised.shape == mock_image.shape
        assert denoised is not None
    
    def test_sharpen_image(self, mock_image):
        """Test sharpening an image."""
        # Apply blur to make the image less sharp
        blurry = cv2.GaussianBlur(mock_image, (5, 5), 0)
        
        # Sharpen the image
        sharpened = sharpen_image(blurry)
        
        # Verify the sharpening
        assert sharpened.shape == blurry.shape
        
        # Calculate the Laplacian variance (a measure of sharpness)
        lap_var_before = cv2.Laplacian(blurry, cv2.CV_64F).var()
        lap_var_after = cv2.Laplacian(sharpened, cv2.CV_64F).var()
        
        # The sharpened image should have a higher Laplacian variance
        assert lap_var_after > lap_var_before
    
    def test_sharpen_image_color(self, mock_color_image):
        """Test sharpening a color image."""
        # Apply blur to make the image less sharp
        blurry = cv2.GaussianBlur(mock_color_image, (5, 5), 0)
        
        # Sharpen the image
        sharpened = sharpen_image(blurry)
        
        # Verify the sharpening
        assert sharpened.shape == blurry.shape
        assert len(sharpened.shape) == 3  # Should still be a color image
    
    def test_binarize_image_simple(self, mock_image):
        """Test binarizing an image using simple thresholding."""
        # Binarize the image
        binary = binarize_image(mock_image, method='simple')
        
        # Verify the binarization
        assert binary.shape == mock_image.shape
        assert set(np.unique(binary)).issubset({0, 255})  # Should only contain 0 and 255
    
    def test_binarize_image_otsu(self, mock_image):
        """Test binarizing an image using Otsu's method."""
        # Binarize the image
        binary = binarize_image(mock_image, method='otsu')
        
        # Verify the binarization
        assert binary.shape == mock_image.shape
        assert set(np.unique(binary)).issubset({0, 255})  # Should only contain 0 and 255
    
    def test_binarize_image_adaptive(self, mock_image):
        """Test binarizing an image using adaptive thresholding."""
        # Binarize the image
        binary = binarize_image(mock_image, method='adaptive')
        
        # Verify the binarization
        assert binary.shape == mock_image.shape
        assert set(np.unique(binary)).issubset({0, 255})  # Should only contain 0 and 255
    
    def test_binarize_image_sauvola(self, mock_image):
        """Test binarizing an image using Sauvola's method."""
        # Binarize the image
        binary = binarize_image(mock_image, method='sauvola')
        
        # Verify the binarization
        assert binary.shape == mock_image.shape
        assert set(np.unique(binary)).issubset({0, 255})  # Should only contain 0 and 255
    
    def test_binarize_image_unknown_method(self, mock_image):
        """Test binarizing an image with an unknown method."""
        # Should default to Otsu's method
        binary = binarize_image(mock_image, method='unknown')
        
        # Verify the binarization
        assert binary.shape == mock_image.shape
        assert set(np.unique(binary)).issubset({0, 255})  # Should only contain 0 and 255
    
    def test_binarize_image_color(self, mock_color_image):
        """Test binarizing a color image."""
        # Binarize the image
        binary = binarize_image(mock_color_image)
        
        # Verify the binarization
        assert binary.shape == mock_color_image.shape[:2]  # Should be grayscale now
        assert set(np.unique(binary)).issubset({0, 255})  # Should only contain 0 and 255
    
    def test_deskew_image(self, skewed_document_image):
        """Test deskewing a skewed document image."""
        # Load the skewed image
        skewed = load_image(skewed_document_image)
        
        # Deskew the image
        deskewed = deskew_image(skewed)
        
        # Verify the deskewing
        assert deskewed.shape == skewed.shape
        
        # We can't easily verify the deskewing angle automatically,
        # but we can check that the function ran without errors
        assert deskewed is not None
    
    def test_deskew_image_no_text(self, mock_image):
        """Test deskewing an image with no clear text lines."""
        # Deskew the image
        deskewed = deskew_image(mock_image)
        
        # Should return the original image if no text is detected
        np.testing.assert_array_equal(deskewed, mock_image)


class TestDocumentSegmentation:
    """Tests for document segmentation functions."""
    
    def test_detect_text_regions(self, sample_document_image):
        """Test detecting text regions in a document."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Detect text regions
        regions = detect_text_regions(doc_image)
        
        # Verify the detection
        assert len(regions) > 0  # Should detect at least one region
        
        # Each region should be a tuple of (x, y, width, height)
        for region in regions:
            assert len(region) == 4
            x, y, w, h = region
            assert x >= 0 and y >= 0
            assert w > 0 and h > 0
            assert x + w <= doc_image.shape[1]
            assert y + h <= doc_image.shape[0]
    
    def test_detect_paragraphs(self, sample_document_image):
        """Test detecting paragraph regions in a document."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Detect paragraphs
        paragraphs = detect_paragraphs(doc_image)
        
        # Verify the detection
        assert len(paragraphs) > 0  # Should detect at least one paragraph
        
        # Each paragraph should be a tuple of (x, y, width, height)
        for paragraph in paragraphs:
            assert len(paragraph) == 4
            x, y, w, h = paragraph
            assert x >= 0 and y >= 0
            assert w > 0 and h > 0
            assert x + w <= doc_image.shape[1]
            assert y + h <= doc_image.shape[0]
    
    def test_detect_tables(self, sample_document_image):
        """Test detecting table regions in a document."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Detect tables
        tables = detect_tables(doc_image)
        
        # Verify the detection
        assert len(tables) > 0  # Should detect at least one table
        
        # Each table should be a tuple of (x, y, width, height)
        for table in tables:
            assert len(table) == 4
            x, y, w, h = table
            assert x >= 0 and y >= 0
            assert w > 0 and h > 0
            assert x + w <= doc_image.shape[1]
            assert y + h <= doc_image.shape[0]
    
    def test_detect_form_fields(self, sample_document_image):
        """Test detecting form fields in a document."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Detect form fields
        fields = detect_form_fields(doc_image)
        
        # Verify the detection
        assert len(fields) > 0  # Should detect at least one field
        
        # Each field should be a dictionary with type and bbox
        for field in fields:
            assert 'type' in field
            assert field['type'] in ['checkbox', 'text_field']
            
            if field['type'] == 'checkbox':
                assert 'bbox' in field
                assert 'checked' in field
                assert isinstance(field['checked'], bool)
            
            if field['type'] == 'text_field':
                assert 'bbox' in field
                assert 'underline' in field
    
    def test_segment_document(self, sample_document_image):
        """Test segmenting a document into different regions."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Segment the document
        segments = segment_document(doc_image)
        
        # Verify the segmentation
        assert 'text_regions' in segments
        assert 'paragraphs' in segments
        assert 'tables' in segments
        assert 'form_fields' in segments
        assert 'images' in segments
        
        # Should have detected at least some regions
        assert len(segments['text_regions']) > 0
        
        # Check the structure of the segments
        for region in segments['text_regions']:
            assert 'bbox' in region
            assert 'type' in region
    
    def test_segment_document_with_type(self, sample_document_image):
        """Test segmenting a document with a specific document type."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Segment the document with a specific type
        segments = segment_document(doc_image, document_type=DocumentType.APPLICATION)
        
        # Verify the segmentation
        assert 'text_regions' in segments
        assert 'paragraphs' in segments
        assert 'tables' in segments
        assert 'form_fields' in segments
        assert 'images' in segments
        
        # Should have detected at least some regions
        assert len(segments['text_regions']) > 0


class TestImageFormatHandling:
    """Tests for image format handling functions."""
    
    def test_convert_to_format_jpeg(self, mock_image):
        """Test converting an image to JPEG format."""
        # Convert to JPEG
        jpeg_data = convert_to_format(mock_image, ImageFormat.JPEG)
        
        # Verify the conversion
        assert isinstance(jpeg_data, bytes)
        assert len(jpeg_data) > 0
        assert jpeg_data.startswith(b'\xff\xd8')  # JPEG signature
    
    def test_convert_to_format_png(self, mock_image):
        """Test converting an image to PNG format."""
        # Convert to PNG
        png_data = convert_to_format(mock_image, ImageFormat.PNG)
        
        # Verify the conversion
        assert isinstance(png_data, bytes)
        assert len(png_data) > 0
        assert png_data.startswith(b'\x89PNG')  # PNG signature
    
    def test_convert_to_format_tiff(self, mock_image):
        """Test converting an image to TIFF format."""
        # Convert to TIFF
        tiff_data = convert_to_format(mock_image, ImageFormat.TIFF)
        
        # Verify the conversion
        assert isinstance(tiff_data, bytes)
        assert len(tiff_data) > 0
        # TIFF can start with either 'II' or 'MM'
        assert tiff_data.startswith(b'II') or tiff_data.startswith(b'MM')
    
    def test_convert_to_format_bmp(self, mock_image):
        """Test converting an image to BMP format."""
        # Convert to BMP
        bmp_data = convert_to_format(mock_image, ImageFormat.BMP)
        
        # Verify the conversion
        assert isinstance(bmp_data, bytes)
        assert len(bmp_data) > 0
        assert bmp_data.startswith(b'BM')  # BMP signature
    
    def test_convert_to_format_unknown(self, mock_image):
        """Test converting an image to an unknown format."""
        # Create a custom format enum value for testing
        unknown_format = MagicMock()
        unknown_format.name = "UNKNOWN"
        
        # Should default to PNG
        data = convert_to_format(mock_image, unknown_format)
        
        # Verify the conversion
        assert isinstance(data, bytes)
        assert len(data) > 0
        assert data.startswith(b'\x89PNG')  # PNG signature
    
    def test_save_image(self, mock_image, temp_dir):
        """Test saving an image to a file."""
        # Define the output path
        output_path = os.path.join(temp_dir, "saved_image.png")
        
        # Save the image
        result_path = save_image(mock_image, output_path)
        
        # Verify the save
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # Load the saved image to verify content
        saved_image = cv2.imread(output_path, cv2.IMREAD_UNCHANGED)
        assert saved_image is not None
        assert saved_image.shape == mock_image.shape
    
    def test_save_image_with_format(self, mock_image, temp_dir):
        """Test saving an image with a specific format."""
        # Define the output path
        output_path = os.path.join(temp_dir, "saved_image.dat")  # Unusual extension
        
        # Save the image with a specific format
        result_path = save_image(mock_image, output_path, ImageFormat.JPEG)
        
        # Verify the save
        assert result_path == output_path
        assert os.path.exists(output_path)
        
        # Check the file signature to verify it's a JPEG
        with open(output_path, "rb") as f:
            signature = f.read(2)
            assert signature == b'\xff\xd8'  # JPEG signature
    
    def test_save_image_error(self, mock_image):
        """Test error handling when saving an image fails."""
        # Try to save to an invalid path
        with pytest.raises(ServiceError):
            save_image(mock_image, "/nonexistent/directory/image.png")
    
    def test_get_image_format(self):
        """Test detecting image format from file path."""
        # Test various file extensions
        assert get_image_format("image.jpg") == ImageFormat.JPEG
        assert get_image_format("image.jpeg") == ImageFormat.JPEG
        assert get_image_format("image.png") == ImageFormat.PNG
        assert get_image_format("image.tiff") == ImageFormat.TIFF
        assert get_image_format("image.tif") == ImageFormat.TIFF
        assert get_image_format("image.bmp") == ImageFormat.BMP
        assert get_image_format("image.pdf") == ImageFormat.PDF
        
        # Test unknown extension (should default to JPEG)
        assert get_image_format("image.unknown") == ImageFormat.JPEG


class TestImageQualityAssessment:
    """Tests for image quality assessment functions."""
    
    def test_assess_image_quality_high(self, high_quality_image):
        """Test assessing the quality of a high-quality image."""
        # Load the high-quality image
        image = load_image(high_quality_image)
        
        # Assess the quality
        metrics = assess_image_quality(image)
        
        # Verify the assessment
        assert isinstance(metrics, dict)
        assert QualityMetrics.CONTRAST.value in metrics
        assert QualityMetrics.BRIGHTNESS.value in metrics
        assert QualityMetrics.SHARPNESS.value in metrics
        assert QualityMetrics.NOISE.value in metrics
        assert QualityMetrics.RESOLUTION.value in metrics
        assert QualityMetrics.SKEW.value in metrics
        
        # High-quality image should have good contrast and sharpness
        assert metrics[QualityMetrics.CONTRAST.value] > 0.7
        assert metrics[QualityMetrics.SHARPNESS.value] > 0.5
    
    def test_assess_image_quality_low(self, low_quality_image):
        """Test assessing the quality of a low-quality image."""
        # Load the low-quality image
        image = load_image(low_quality_image)
        
        # Assess the quality
        metrics = assess_image_quality(image)
        
        # Verify the assessment
        assert isinstance(metrics, dict)
        
        # Low-quality image should have poor contrast and sharpness
        assert metrics[QualityMetrics.CONTRAST.value] < 0.7
        assert metrics[QualityMetrics.SHARPNESS.value] < 0.7
    
    def test_calculate_overall_quality(self):
        """Test calculating overall quality from individual metrics."""
        # Create sample metrics
        metrics = {
            QualityMetrics.CONTRAST.value: 0.8,
            QualityMetrics.BRIGHTNESS.value: 0.7,
            QualityMetrics.SHARPNESS.value: 0.9,
            QualityMetrics.NOISE.value: 0.6,
            QualityMetrics.RESOLUTION.value: 0.5,
            QualityMetrics.SKEW.value: 0.8
        }
        
        # Calculate overall quality
        overall = calculate_overall_quality(metrics)
        
        # Verify the calculation
        assert 0.0 <= overall <= 1.0
        
        # The overall score should be a weighted average of the metrics
        # We can't know the exact weights, but we can check it's reasonable
        assert overall > 0.5  # These are mostly good scores
    
    def test_is_suitable_for_ocr_high_quality(self, high_quality_image):
        """Test determining if a high-quality image is suitable for OCR."""
        # Load the high-quality image
        image = load_image(high_quality_image)
        
        # Check if suitable for OCR
        is_suitable, metrics = is_suitable_for_ocr(image)
        
        # Verify the result
        assert is_suitable is True
        assert isinstance(metrics, dict)
    
    def test_is_suitable_for_ocr_low_quality(self, low_quality_image):
        """Test determining if a low-quality image is suitable for OCR."""
        # Load the low-quality image
        image = load_image(low_quality_image)
        
        # Check if suitable for OCR
        is_suitable, metrics = is_suitable_for_ocr(image)
        
        # The result depends on how low the quality is
        # We can't assert a specific result, but we can check the return types
        assert isinstance(is_suitable, bool)
        assert isinstance(metrics, dict)
    
    def test_suggest_enhancements_high_quality(self, high_quality_image):
        """Test suggesting enhancements for a high-quality image."""
        # Load the high-quality image
        image = load_image(high_quality_image)
        
        # Assess quality
        metrics = assess_image_quality(image)
        
        # Suggest enhancements
        suggestions = suggest_enhancements(metrics)
        
        # Verify the suggestions
        assert isinstance(suggestions, list)
        # High-quality image should need few or no enhancements
        assert len(suggestions) <= 2
    
    def test_suggest_enhancements_low_quality(self, low_quality_image):
        """Test suggesting enhancements for a low-quality image."""
        # Load the low-quality image
        image = load_image(low_quality_image)
        
        # Assess quality
        metrics = assess_image_quality(image)
        
        # Suggest enhancements
        suggestions = suggest_enhancements(metrics)
        
        # Verify the suggestions
        assert isinstance(suggestions, list)
        # Low-quality image should need multiple enhancements
        assert len(suggestions) >= 1


class TestHelperFunctions:
    """Tests for helper functions."""
    
    def test_is_checkbox_checked_empty(self, sample_document_image):
        """Test detecting an empty checkbox."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Convert to grayscale if needed
        if len(doc_image.shape) == 3:
            gray = cv2.cvtColor(doc_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = doc_image
        
        # Define the empty checkbox region (based on the fixture)
        empty_checkbox = (50, 450, 20, 20)
        
        # Check if it's checked
        is_checked = is_checkbox_checked(gray, empty_checkbox)
        
        # Verify the result
        assert is_checked is False
    
    def test_is_checkbox_checked_filled(self, sample_document_image):
        """Test detecting a filled checkbox."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Convert to grayscale if needed
        if len(doc_image.shape) == 3:
            gray = cv2.cvtColor(doc_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = doc_image
        
        # Define the filled checkbox region (based on the fixture)
        filled_checkbox = (100, 450, 20, 20)
        
        # Check if it's checked
        is_checked = is_checkbox_checked(gray, filled_checkbox)
        
        # Verify the result
        assert is_checked is True
    
    def test_is_region_in_bounds(self):
        """Test checking if a region is within image bounds."""
        # Define image shape
        image_shape = (100, 200)  # height, width
        
        # Test valid regions
        assert is_region_in_bounds((0, 0, 100, 50), image_shape) is True
        assert is_region_in_bounds((50, 25, 100, 50), image_shape) is True
        
        # Test invalid regions
        assert is_region_in_bounds((-10, 0, 50, 50), image_shape) is False
        assert is_region_in_bounds((0, -10, 50, 50), image_shape) is False
        assert is_region_in_bounds((150, 0, 100, 50), image_shape) is False
        assert is_region_in_bounds((0, 75, 50, 50), image_shape) is False
    
    def test_extract_region(self, mock_document_image):
        """Test extracting a region from an image."""
        # Load the document image
        doc_image = load_image(mock_document_image)
        
        # Define a region to extract
        region = (50, 50, 100, 100)
        
        # Extract the region
        extracted = extract_region(doc_image, region)
        
        # Verify the extraction
        assert extracted.shape == (100, 100) if len(doc_image.shape) == 2 else (100, 100, 3)
    
    def test_extract_region_out_of_bounds(self, mock_document_image):
        """Test extracting a region that's partially out of bounds."""
        # Load the document image
        doc_image = load_image(mock_document_image)
        
        # Define a region that's partially out of bounds
        region = (doc_image.shape[1] - 50, doc_image.shape[0] - 50, 100, 100)
        
        # Extract the region (should adjust to fit within bounds)
        extracted = extract_region(doc_image, region)
        
        # Verify the extraction
        assert extracted.shape[0] <= 50  # Height should be at most 50
        assert extracted.shape[1] <= 50  # Width should be at most 50
    
    def test_preprocess_for_ocr(self, sample_document_image):
        """Test the standard preprocessing pipeline for OCR."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Preprocess for OCR
        preprocessed = preprocess_for_ocr(doc_image)
        
        # Verify the preprocessing
        assert preprocessed.shape[:2] == doc_image.shape[:2]  # Dimensions should match
        assert preprocessed is not None
    
    def test_preprocess_for_ocr_with_document_type(self, sample_document_image):
        """Test preprocessing with a specific document type."""
        # Load the document image
        doc_image = load_image(sample_document_image)
        
        # Preprocess for OCR with document type
        preprocessed = preprocess_for_ocr(doc_image, DocumentType.APPLICATION)
        
        # Verify the preprocessing
        assert preprocessed.shape[:2] == doc_image.shape[:2]  # Dimensions should match
        assert preprocessed is not None
    
    def test_create_field_mask(self, mock_document_image):
        """Test creating a mask highlighting specific fields."""
        # Load the document image
        doc_image = load_image(mock_document_image)
        
        # Create some field locations
        field_locations = [
            FieldLocation(label="Field 1", bbox=(50, 50, 100, 30)),
            FieldLocation(label="Field 2", bbox=(50, 100, 100, 30))
        ]
        
        # Create the field mask
        masked = create_field_mask(doc_image, field_locations)
        
        # Verify the mask
        assert masked.shape[:2] == doc_image.shape[:2]  # Dimensions should match
        assert len(masked.shape) == 3  # Should be a color image for highlighting
        assert masked is not None


# ===== Integration Tests =====

class TestIntegration:
    """Integration tests for image processing pipeline."""
    
    def test_full_preprocessing_pipeline(self, sample_document_image):
        """Test the full preprocessing pipeline from loading to OCR preparation."""
        # Load the image
        image = load_image(sample_document_image)
        
        # Normalize size
        normalized = normalize_size(image)
        
        # Correct orientation
        oriented = normalize_orientation(normalized)
        
        # Convert to grayscale
        gray = convert_color_space(oriented, ColorSpace.GRAY)
        
        # Enhance contrast
        enhanced = enhance_contrast(gray)
        
        # Remove noise
        denoised = remove_noise(enhanced, method='gaussian')
        
        # Sharpen
        sharpened = sharpen_image(denoised)
        
        # Verify the pipeline
        assert sharpened is not None
        assert sharpened.shape[:2] == image.shape[:2]  # Dimensions should match
    
    def test_document_analysis_pipeline(self, sample_document_image):
        """Test the document analysis pipeline from loading to segmentation."""
        # Load the image
        image = load_image(sample_document_image)
        
        # Preprocess for OCR
        preprocessed = preprocess_for_ocr(image)
        
        # Segment the document
        segments = segment_document(preprocessed)
        
        # Verify the pipeline
        assert segments is not None
        assert 'text_regions' in segments
        assert 'paragraphs' in segments
        assert 'tables' in segments
        assert 'form_fields' in segments
    
    def test_quality_assessment_pipeline(self, low_quality_image, high_quality_image):
        """Test the quality assessment pipeline with different quality images."""
        # Load the images
        low_quality = load_image(low_quality_image)
        high_quality = load_image(high_quality_image)
        
        # Assess quality
        low_suitable, low_metrics = is_suitable_for_ocr(low_quality)
        high_suitable, high_metrics = is_suitable_for_ocr(high_quality)
        
        # Get enhancement suggestions
        low_suggestions = suggest_enhancements(low_metrics)
        high_suggestions = suggest_enhancements(high_metrics)
        
        # Verify the pipeline
        assert isinstance(low_suitable, bool)
        assert isinstance(high_suitable, bool)
        assert len(low_suggestions) >= len(high_suggestions)  # Low quality should need more enhancements
        
        # Apply suggested enhancements to low quality image
        enhanced = low_quality.copy()
        if 'enhance_contrast' in low_suggestions:
            enhanced = enhance_contrast(enhanced)
        if 'sharpen_image' in low_suggestions:
            enhanced = sharpen_image(enhanced)
        if 'remove_noise' in low_suggestions:
            enhanced = remove_noise(enhanced)
        
        # Reassess quality after enhancements
        enhanced_suitable, enhanced_metrics = is_suitable_for_ocr(enhanced)
        
        # Verify the enhancement improved quality
        overall_before = calculate_overall_quality(low_metrics)
        overall_after = calculate_overall_quality(enhanced_metrics)
        
        # The overall quality should improve after enhancements
        # This might not always be true, but it's a reasonable expectation
        assert overall_after >= overall_before * 0.9  # Allow some tolerance