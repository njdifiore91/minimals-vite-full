#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the image_utils.py module.

This module contains tests for image preprocessing, normalization, enhancement,
segmentation, and quality assessment functions in the image_utils.py module.
These tests ensure that the image processing utilities work correctly for
optimal document preparation for OCR processing.
"""

import os
import pytest
import numpy as np
import cv2
from unittest.mock import patch, MagicMock
from typing import Dict, List, Tuple, Any
import tempfile

from src.utils.image_utils import (
    # Enums
    ColorSpace, ImageFormat, QualityMetrics,
    # Image loading and basic operations
    load_image, load_image_from_bytes,
    # Image preprocessing
    normalize_size, normalize_orientation, convert_color_space,
    # Image enhancement
    enhance_contrast, remove_noise, sharpen_image, binarize_image, deskew_image,
    # Document segmentation
    detect_text_regions, detect_paragraphs, detect_tables, detect_form_fields,
    segment_document,
    # Image format handling
    convert_to_format, save_image, get_image_format,
    # Image quality assessment
    assess_image_quality, calculate_overall_quality, is_suitable_for_ocr,
    suggest_enhancements,
    # Helper functions
    is_checkbox_checked, is_region_in_bounds, extract_region, preprocess_for_ocr,
    create_field_mask
)
from src.types.documents import DocumentType
from src.types.errors import ServiceError
from src.types.extraction import FieldLocation


# Fixtures for test images
@pytest.fixture
def sample_image_path():
    """Path to a sample image for testing."""
    # This would typically point to a real test image in the test_data directory
    # For this test, we'll use a mock path and patch the actual loading
    return os.path.join(os.path.dirname(__file__), '..', 'test_data', 'typed_documents', 'sample_invoice.png')


@pytest.fixture
def sample_image_bytes():
    """Sample image as bytes for testing."""
    # Create a simple test image as bytes
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Add some text to the image for OCR testing
    cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    # Convert to bytes
    _, buffer = cv2.imencode('.png', img)
    return buffer.tobytes()


@pytest.fixture
def sample_image():
    """Sample image as numpy array for testing."""
    # Create a simple test image
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    # Add some text to the image for OCR testing
    cv2.putText(img, "Test", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    return img


@pytest.fixture
def sample_document_image():
    """Sample document image with text regions, tables, and form fields."""
    # Create a more complex test image simulating a document
    img = np.ones((500, 400, 3), dtype=np.uint8) * 255  # White background
    
    # Add a title
    cv2.putText(img, "INVOICE", (150, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Add some text paragraphs
    cv2.putText(img, "Company: ABC Corp", (50, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Date: 2023-01-15", (50, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Invoice #: INV-12345", (50, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add a table
    # Table header
    cv2.line(img, (50, 150), (350, 150), (0, 0, 0), 2)  # Top horizontal line
    cv2.line(img, (50, 180), (350, 180), (0, 0, 0), 1)  # Header separator
    cv2.line(img, (50, 250), (350, 250), (0, 0, 0), 2)  # Bottom horizontal line
    cv2.line(img, (50, 150), (50, 250), (0, 0, 0), 2)   # Left vertical line
    cv2.line(img, (200, 150), (200, 250), (0, 0, 0), 1)  # Middle vertical line
    cv2.line(img, (350, 150), (350, 250), (0, 0, 0), 2)  # Right vertical line
    
    # Table content
    cv2.putText(img, "Item", (60, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Price", (210, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Product A", (60, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "$100.00", (210, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Product B", (60, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "$150.00", (210, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add a checkbox
    cv2.rectangle(img, (50, 300), (70, 320), (0, 0, 0), 1)  # Empty checkbox
    cv2.putText(img, "I agree to terms", (80, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add a filled checkbox
    cv2.rectangle(img, (50, 350), (70, 370), (0, 0, 0), 1)  # Checkbox outline
    cv2.line(img, (52, 360), (68, 360), (0, 0, 0), 1)  # Horizontal line inside checkbox
    cv2.line(img, (60, 352), (60, 368), (0, 0, 0), 1)  # Vertical line inside checkbox
    cv2.putText(img, "Send me updates", (80, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add a signature line
    cv2.line(img, (50, 450), (200, 450), (0, 0, 0), 1)
    cv2.putText(img, "Signature", (50, 470), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    return img


@pytest.fixture
def skewed_image():
    """Sample skewed image for testing deskewing."""
    # Create a simple test image
    img = np.ones((300, 300, 3), dtype=np.uint8) * 255  # White background
    
    # Add some text
    cv2.putText(img, "Skewed Text", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    
    # Apply rotation to skew the image
    center = (img.shape[1] // 2, img.shape[0] // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, 15, 1.0)  # 15 degree rotation
    skewed = cv2.warpAffine(img, rotation_matrix, (img.shape[1], img.shape[0]))
    
    return skewed


@pytest.fixture
def low_quality_image():
    """Sample low quality image for testing quality assessment."""
    # Create a low quality image with noise and low contrast
    img = np.ones((200, 200, 3), dtype=np.uint8) * 150  # Gray background (low contrast)
    
    # Add some text with low contrast
    cv2.putText(img, "Low Quality", (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 100), 1)
    
    # Add noise
    noise = np.random.randint(0, 30, img.shape).astype(np.uint8)
    noisy_img = cv2.add(img, noise)
    
    # Blur the image to reduce sharpness
    blurred = cv2.GaussianBlur(noisy_img, (7, 7), 0)
    
    return blurred


@pytest.fixture
def handwritten_image():
    """Sample image with handwritten text."""
    # Create a simple image with simulated handwritten text
    img = np.ones((300, 400, 3), dtype=np.uint8) * 255  # White background
    
    # Simulate handwritten text with curved lines
    # Draw a curved line to simulate handwriting
    pts = np.array([[50, 150], [100, 140], [150, 160], [200, 150], [250, 170], [300, 150]], np.int32)
    pts = pts.reshape((-1, 1, 2))
    cv2.polylines(img, [pts], False, (0, 0, 0), 2)
    
    # Add more curved lines to simulate text
    pts2 = np.array([[50, 200], [100, 190], [150, 210], [200, 200]], np.int32)
    pts2 = pts2.reshape((-1, 1, 2))
    cv2.polylines(img, [pts2], False, (0, 0, 0), 2)
    
    pts3 = np.array([[220, 200], [250, 210], [300, 190]], np.int32)
    pts3 = pts3.reshape((-1, 1, 2))
    cv2.polylines(img, [pts3], False, (0, 0, 0), 2)
    
    return img


@pytest.fixture
def mixed_content_image():
    """Sample image with both typed and handwritten content."""
    # Create an image with both typed and handwritten content
    img = np.ones((400, 500, 3), dtype=np.uint8) * 255  # White background
    
    # Add typed text
    cv2.putText(img, "FORM", (200, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
    cv2.putText(img, "Name:", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Date:", (50, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    cv2.putText(img, "Signature:", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Add lines for handwritten content
    cv2.line(img, (100, 100), (300, 100), (0, 0, 0), 1)  # Name line
    cv2.line(img, (100, 150), (300, 150), (0, 0, 0), 1)  # Date line
    cv2.line(img, (150, 200), (300, 200), (0, 0, 0), 1)  # Signature line
    
    # Simulate handwritten content
    # Name
    pts1 = np.array([[120, 95], [150, 90], [180, 95], [210, 90], [240, 95]], np.int32)
    pts1 = pts1.reshape((-1, 1, 2))
    cv2.polylines(img, [pts1], False, (0, 0, 0), 2)
    
    # Date
    cv2.putText(img, "01/15/2023", (120, 145), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 0.5, (0, 0, 0), 1)
    
    # Signature
    pts2 = np.array([[160, 195], [200, 185], [240, 195], [280, 185]], np.int32)
    pts2 = pts2.reshape((-1, 1, 2))
    cv2.polylines(img, [pts2], False, (0, 0, 0), 2)
    
    return img


# Test cases for image loading and basic operations
class TestImageLoading:
    """Test cases for image loading and basic operations."""
    
    @patch('cv2.imread')
    def test_load_image(self, mock_imread, sample_image):
        """Test loading an image from a file path."""
        # Setup mock
        mock_imread.return_value = sample_image
        
        # Call function
        result = load_image('/path/to/image.jpg')
        
        # Verify
        mock_imread.assert_called_once_with('/path/to/image.jpg', cv2.IMREAD_UNCHANGED)
        assert result is not None
        assert result.shape == sample_image.shape
        assert np.array_equal(result, sample_image)
    
    @patch('cv2.imread')
    def test_load_image_failure(self, mock_imread):
        """Test loading an image that doesn't exist."""
        # Setup mock to return None (file not found)
        mock_imread.return_value = None
        
        # Verify exception is raised
        with pytest.raises(ServiceError):
            load_image('/path/to/nonexistent.jpg')
    
    def test_load_image_from_bytes(self, sample_image_bytes, sample_image):
        """Test loading an image from bytes."""
        # Mock the cv2.imdecode function
        with patch('cv2.imdecode') as mock_imdecode:
            mock_imdecode.return_value = sample_image
            
            # Call function
            result = load_image_from_bytes(sample_image_bytes)
            
            # Verify
            assert mock_imdecode.called
            assert result is not None
            assert result.shape == sample_image.shape
            assert np.array_equal(result, sample_image)
    
    def test_load_image_from_bytes_failure(self):
        """Test loading invalid image bytes."""
        # Invalid image bytes
        invalid_bytes = b'not an image'
        
        # Verify exception is raised
        with pytest.raises(ServiceError):
            load_image_from_bytes(invalid_bytes)


# Test cases for image preprocessing
class TestImagePreprocessing:
    """Test cases for image preprocessing functions."""
    
    def test_normalize_size_no_change(self, sample_image):
        """Test normalizing image size when no change is needed."""
        # The sample image is already within acceptable bounds
        result = normalize_size(sample_image)
        
        # Verify no change in dimensions
        assert result.shape == sample_image.shape
        assert np.array_equal(result, sample_image)
    
    def test_normalize_size_too_small(self):
        """Test normalizing an image that is too small."""
        # Create a tiny image
        tiny_image = np.zeros((20, 30, 3), dtype=np.uint8)
        
        # Normalize size (min_size=50 by default)
        result = normalize_size(tiny_image)
        
        # Verify dimensions increased
        assert result.shape[0] >= 50 or result.shape[1] >= 50
        assert result.shape[0] / tiny_image.shape[0] == result.shape[1] / tiny_image.shape[1]  # Aspect ratio preserved
    
    def test_normalize_size_too_large(self):
        """Test normalizing an image that is too large."""
        # Create a large image
        large_image = np.zeros((5000, 6000, 3), dtype=np.uint8)
        
        # Normalize size (max_size=4096 by default)
        result = normalize_size(large_image)
        
        # Verify dimensions decreased
        assert result.shape[0] <= 4096 and result.shape[1] <= 4096
        assert result.shape[0] / large_image.shape[0] == result.shape[1] / large_image.shape[1]  # Aspect ratio preserved
    
    def test_normalize_orientation(self, skewed_image):
        """Test normalizing the orientation of a skewed image."""
        # Normalize orientation
        result = normalize_orientation(skewed_image)
        
        # Verify dimensions unchanged
        assert result.shape == skewed_image.shape
        
        # The result should be different from the input (deskewed)
        # This is a simple check - in a real test we might use more sophisticated methods
        # to verify the orientation correction
        assert not np.array_equal(result, skewed_image)
    
    def test_convert_color_space_to_gray(self, sample_image):
        """Test converting a color image to grayscale."""
        # Convert to grayscale
        result = convert_color_space(sample_image, ColorSpace.GRAY)
        
        # Verify dimensions and type
        assert len(result.shape) == 2  # Grayscale has only height and width dimensions
        assert result.shape[0] == sample_image.shape[0] and result.shape[1] == sample_image.shape[1]
    
    def test_convert_color_space_to_binary(self, sample_image):
        """Test converting a color image to binary."""
        # Convert to binary
        result = convert_color_space(sample_image, ColorSpace.BINARY)
        
        # Verify dimensions and values
        assert len(result.shape) == 2  # Binary has only height and width dimensions
        assert set(np.unique(result)).issubset({0, 1})  # Only 0 and 1 values
    
    def test_convert_color_space_no_change(self, sample_image):
        """Test converting an image to its current color space."""
        # Convert to BGR (which is the default for OpenCV images)
        result = convert_color_space(sample_image, ColorSpace.BGR)
        
        # Verify no change
        assert result.shape == sample_image.shape
        assert np.array_equal(result, sample_image)


# Test cases for image enhancement
class TestImageEnhancement:
    """Test cases for image enhancement functions."""
    
    def test_enhance_contrast(self, sample_image):
        """Test enhancing contrast of an image."""
        # Enhance contrast
        result = enhance_contrast(sample_image)
        
        # Verify dimensions unchanged
        assert result.shape == sample_image.shape
        
        # The result should be different from the input (enhanced contrast)
        # In a real test, we might check histogram properties
        assert not np.array_equal(result, sample_image)
    
    def test_enhance_contrast_grayscale(self, sample_image):
        """Test enhancing contrast of a grayscale image."""
        # Convert to grayscale first
        gray = cv2.cvtColor(sample_image, cv2.COLOR_BGR2GRAY)
        
        # Enhance contrast
        result = enhance_contrast(gray)
        
        # Verify dimensions unchanged
        assert result.shape == gray.shape
        assert len(result.shape) == 2  # Still grayscale
        
        # The result should be different from the input (enhanced contrast)
        assert not np.array_equal(result, gray)
    
    def test_remove_noise_gaussian(self, sample_image):
        """Test removing noise using Gaussian filter."""
        # Add some noise to the image
        noisy = sample_image.copy()
        noise = np.random.randint(0, 50, sample_image.shape).astype(np.uint8)
        noisy = cv2.add(noisy, noise)
        
        # Remove noise
        result = remove_noise(noisy, method='gaussian')
        
        # Verify dimensions unchanged
        assert result.shape == noisy.shape
        
        # The result should be different from the noisy input
        assert not np.array_equal(result, noisy)
        
        # The result should be closer to the original than the noisy version
        # This is a simple metric - in a real test we might use PSNR or SSIM
        assert np.sum(np.abs(result - sample_image)) < np.sum(np.abs(noisy - sample_image))
    
    def test_remove_noise_median(self, sample_image):
        """Test removing noise using median filter."""
        # Add salt and pepper noise
        noisy = sample_image.copy()
        # Add salt (white) noise
        salt = np.random.random(sample_image.shape[:2]) < 0.02
        noisy[salt] = 255
        # Add pepper (black) noise
        pepper = np.random.random(sample_image.shape[:2]) < 0.02
        noisy[pepper] = 0
        
        # Remove noise with median filter (good for salt and pepper)
        result = remove_noise(noisy, method='median')
        
        # Verify dimensions unchanged
        assert result.shape == noisy.shape
        
        # The result should be different from the noisy input
        assert not np.array_equal(result, noisy)
    
    def test_sharpen_image(self, sample_image):
        """Test sharpening an image."""
        # Blur the image first to make sharpening more noticeable
        blurred = cv2.GaussianBlur(sample_image, (5, 5), 0)
        
        # Sharpen the blurred image
        result = sharpen_image(blurred)
        
        # Verify dimensions unchanged
        assert result.shape == blurred.shape
        
        # The result should be different from the blurred input
        assert not np.array_equal(result, blurred)
        
        # Calculate edge content (a simple measure of sharpness)
        def edge_content(img):
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            edges = cv2.Laplacian(img, cv2.CV_64F)
            return np.var(edges)
        
        # Sharpened image should have more edge content than blurred
        assert edge_content(result) > edge_content(blurred)
    
    def test_binarize_image_otsu(self, sample_document_image):
        """Test binarizing an image using Otsu's method."""
        # Convert to grayscale first
        gray = cv2.cvtColor(sample_document_image, cv2.COLOR_BGR2GRAY)
        
        # Binarize using Otsu's method
        result = binarize_image(gray, method='otsu')
        
        # Verify dimensions unchanged
        assert result.shape == gray.shape
        
        # The result should be binary (only black and white)
        assert set(np.unique(result)).issubset({0, 255})
    
    def test_binarize_image_adaptive(self, sample_document_image):
        """Test binarizing an image using adaptive thresholding."""
        # Convert to grayscale first
        gray = cv2.cvtColor(sample_document_image, cv2.COLOR_BGR2GRAY)
        
        # Binarize using adaptive thresholding
        result = binarize_image(gray, method='adaptive')
        
        # Verify dimensions unchanged
        assert result.shape == gray.shape
        
        # The result should be binary (only black and white)
        assert set(np.unique(result)).issubset({0, 255})
    
    def test_deskew_image(self, skewed_image):
        """Test deskewing a skewed image."""
        # Deskew the image
        result = deskew_image(skewed_image)
        
        # Verify dimensions unchanged
        assert result.shape == skewed_image.shape
        
        # The result should be different from the input (deskewed)
        assert not np.array_equal(result, skewed_image)


# Test cases for document segmentation
class TestDocumentSegmentation:
    """Test cases for document segmentation functions."""
    
    def test_detect_text_regions(self, sample_document_image):
        """Test detecting text regions in a document."""
        # Detect text regions
        regions = detect_text_regions(sample_document_image)
        
        # Verify regions were found
        assert len(regions) > 0
        
        # Verify region format (x, y, width, height)
        for region in regions:
            assert len(region) == 4
            x, y, w, h = region
            assert w > 0 and h > 0
            assert 0 <= x < sample_document_image.shape[1]
            assert 0 <= y < sample_document_image.shape[0]
            assert x + w <= sample_document_image.shape[1]
            assert y + h <= sample_document_image.shape[0]
    
    def test_detect_paragraphs(self, sample_document_image):
        """Test detecting paragraph regions in a document."""
        # Detect paragraphs
        paragraphs = detect_paragraphs(sample_document_image)
        
        # Verify paragraphs were found
        assert len(paragraphs) > 0
        
        # Verify paragraph format (x, y, width, height)
        for paragraph in paragraphs:
            assert len(paragraph) == 4
            x, y, w, h = paragraph
            assert w > 0 and h > 0
            assert 0 <= x < sample_document_image.shape[1]
            assert 0 <= y < sample_document_image.shape[0]
            assert x + w <= sample_document_image.shape[1]
            assert y + h <= sample_document_image.shape[0]
    
    def test_detect_tables(self, sample_document_image):
        """Test detecting tables in a document."""
        # Detect tables
        tables = detect_tables(sample_document_image)
        
        # Verify tables were found (our sample image has a table)
        assert len(tables) > 0
        
        # Verify table format (x, y, width, height)
        for table in tables:
            assert len(table) == 4
            x, y, w, h = table
            assert w > 0 and h > 0
            assert 0 <= x < sample_document_image.shape[1]
            assert 0 <= y < sample_document_image.shape[0]
            assert x + w <= sample_document_image.shape[1]
            assert y + h <= sample_document_image.shape[0]
    
    def test_detect_form_fields(self, sample_document_image):
        """Test detecting form fields in a document."""
        # Detect form fields
        fields = detect_form_fields(sample_document_image)
        
        # Verify fields were found (our sample image has checkboxes)
        assert len(fields) > 0
        
        # Verify field format (dictionary with type, bbox, etc.)
        for field in fields:
            assert 'type' in field
            assert 'bbox' in field
            assert field['type'] in ['text_field', 'checkbox']
            
            # Check bbox format (x, y, width, height)
            x, y, w, h = field['bbox']
            assert w > 0 and h > 0
            assert 0 <= x < sample_document_image.shape[1]
            assert 0 <= y < sample_document_image.shape[0]
            assert x + w <= sample_document_image.shape[1]
            assert y + h <= sample_document_image.shape[0]
            
            # If checkbox, should have 'checked' property
            if field['type'] == 'checkbox':
                assert 'checked' in field
                assert isinstance(field['checked'], bool)
    
    def test_segment_document(self, sample_document_image):
        """Test segmenting a document into different regions."""
        # Segment document
        segments = segment_document(sample_document_image)
        
        # Verify segment types
        assert 'text_regions' in segments
        assert 'paragraphs' in segments
        assert 'tables' in segments
        assert 'form_fields' in segments
        assert 'images' in segments
        
        # Verify at least some segments were found
        assert len(segments['text_regions']) > 0
        assert len(segments['paragraphs']) > 0
        
        # Verify segment format for text regions
        for region in segments['text_regions']:
            assert 'type' in region
            assert 'bbox' in region
            assert region['type'] == 'text'
            assert len(region['bbox']) == 4
        
        # Verify segment format for tables
        for table in segments['tables']:
            assert 'type' in table
            assert 'bbox' in table
            assert table['type'] == 'table'
            assert len(table['bbox']) == 4
    
    def test_segment_document_with_document_type(self, sample_document_image):
        """Test segmenting a document with a specific document type."""
        # Segment document with document type
        segments = segment_document(sample_document_image, DocumentType.INVOICE)
        
        # Verify segment types
        assert 'text_regions' in segments
        assert 'paragraphs' in segments
        assert 'tables' in segments
        assert 'form_fields' in segments
        assert 'images' in segments
        
        # Verify at least some segments were found
        assert len(segments['text_regions']) > 0
        assert len(segments['paragraphs']) > 0


# Test cases for image format handling
class TestImageFormatHandling:
    """Test cases for image format handling functions."""
    
    def test_convert_to_format_jpeg(self, sample_image):
        """Test converting an image to JPEG format."""
        # Convert to JPEG
        jpeg_bytes = convert_to_format(sample_image, ImageFormat.JPEG)
        
        # Verify result is bytes
        assert isinstance(jpeg_bytes, bytes)
        assert len(jpeg_bytes) > 0
        
        # Verify bytes can be decoded back to an image
        nparr = np.frombuffer(jpeg_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        assert img is not None
        assert img.shape[:2] == sample_image.shape[:2]  # Same dimensions
    
    def test_convert_to_format_png(self, sample_image):
        """Test converting an image to PNG format."""
        # Convert to PNG
        png_bytes = convert_to_format(sample_image, ImageFormat.PNG)
        
        # Verify result is bytes
        assert isinstance(png_bytes, bytes)
        assert len(png_bytes) > 0
        
        # Verify bytes can be decoded back to an image
        nparr = np.frombuffer(png_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        assert img is not None
        assert img.shape == sample_image.shape  # Same dimensions
    
    def test_save_image(self, sample_image):
        """Test saving an image to a file."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Save the image
            with patch('cv2.imwrite') as mock_imwrite:
                mock_imwrite.return_value = True
                result_path = save_image(sample_image, tmp_path)
                
                # Verify cv2.imwrite was called with correct arguments
                mock_imwrite.assert_called_once_with(tmp_path, sample_image)
                
                # Verify the returned path is the same as the input path
                assert result_path == tmp_path
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_save_image_with_format(self, sample_image):
        """Test saving an image with a specific format."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            # Save the image with a specific format
            with patch('src.utils.image_utils.convert_to_format') as mock_convert:
                mock_convert.return_value = b'fake_image_bytes'
                
                result_path = save_image(sample_image, tmp_path, format=ImageFormat.JPEG)
                
                # Verify convert_to_format was called with correct arguments
                mock_convert.assert_called_once_with(sample_image, ImageFormat.JPEG)
                
                # Verify the returned path is the same as the input path
                assert result_path == tmp_path
        finally:
            # Clean up
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_get_image_format(self):
        """Test determining image format from file path."""
        # Test various file extensions
        assert get_image_format('image.jpg') == ImageFormat.JPEG
        assert get_image_format('image.jpeg') == ImageFormat.JPEG
        assert get_image_format('image.png') == ImageFormat.PNG
        assert get_image_format('image.tif') == ImageFormat.TIFF
        assert get_image_format('image.tiff') == ImageFormat.TIFF
        assert get_image_format('image.bmp') == ImageFormat.BMP
        assert get_image_format('image.pdf') == ImageFormat.PDF
        
        # Test unknown extension (should default to JPEG)
        assert get_image_format('image.unknown') == ImageFormat.JPEG


# Test cases for image quality assessment
class TestImageQualityAssessment:
    """Test cases for image quality assessment functions."""
    
    def test_assess_image_quality(self, sample_image, low_quality_image):
        """Test assessing image quality."""
        # Assess quality of good image
        good_metrics = assess_image_quality(sample_image)
        
        # Assess quality of low quality image
        low_metrics = assess_image_quality(low_quality_image)
        
        # Verify metrics format
        for metrics in [good_metrics, low_metrics]:
            assert QualityMetrics.CONTRAST.value in metrics
            assert QualityMetrics.BRIGHTNESS.value in metrics
            assert QualityMetrics.SHARPNESS.value in metrics
            assert QualityMetrics.NOISE.value in metrics
            assert QualityMetrics.RESOLUTION.value in metrics
            assert QualityMetrics.SKEW.value in metrics
            
            # Verify metric values are in range [0, 1]
            for value in metrics.values():
                assert 0 <= value <= 1
        
        # Verify low quality image has worse metrics than good image
        # At least some metrics should be worse
        assert low_metrics[QualityMetrics.CONTRAST.value] < good_metrics[QualityMetrics.CONTRAST.value] or \
               low_metrics[QualityMetrics.SHARPNESS.value] < good_metrics[QualityMetrics.SHARPNESS.value] or \
               low_metrics[QualityMetrics.NOISE.value] < good_metrics[QualityMetrics.NOISE.value]
    
    def test_calculate_overall_quality(self, sample_image, low_quality_image):
        """Test calculating overall image quality."""
        # Get metrics for both images
        good_metrics = assess_image_quality(sample_image)
        low_metrics = assess_image_quality(low_quality_image)
        
        # Calculate overall quality
        good_quality = calculate_overall_quality(good_metrics)
        low_quality = calculate_overall_quality(low_metrics)
        
        # Verify quality scores are in range [0, 1]
        assert 0 <= good_quality <= 1
        assert 0 <= low_quality <= 1
        
        # Verify low quality image has lower overall quality
        assert low_quality < good_quality
    
    def test_is_suitable_for_ocr(self, sample_image, low_quality_image):
        """Test determining if an image is suitable for OCR."""
        # Check good image
        good_suitable, good_metrics = is_suitable_for_ocr(sample_image)
        
        # Check low quality image
        low_suitable, low_metrics = is_suitable_for_ocr(low_quality_image)
        
        # Verify metrics format
        assert isinstance(good_metrics, dict)
        assert isinstance(low_metrics, dict)
        
        # Verify suitability is boolean
        assert isinstance(good_suitable, bool)
        assert isinstance(low_suitable, bool)
        
        # Good image should be suitable, low quality might not be
        assert good_suitable
    
    def test_suggest_enhancements(self, low_quality_image):
        """Test suggesting image enhancements."""
        # Get metrics for low quality image
        metrics = assess_image_quality(low_quality_image)
        
        # Get enhancement suggestions
        suggestions = suggest_enhancements(metrics)
        
        # Verify suggestions format
        assert isinstance(suggestions, list)
        
        # Low quality image should have some suggested enhancements
        assert len(suggestions) > 0
        
        # Verify suggestion values
        for suggestion in suggestions:
            assert suggestion in [
                'enhance_contrast', 'increase_brightness', 'decrease_brightness',
                'sharpen_image', 'remove_noise', 'increase_resolution', 'deskew_image'
            ]


# Test cases for helper functions
class TestHelperFunctions:
    """Test cases for helper functions."""
    
    def test_is_checkbox_checked(self, sample_document_image):
        """Test determining if a checkbox is checked."""
        # Convert to grayscale
        gray = cv2.cvtColor(sample_document_image, cv2.COLOR_BGR2GRAY)
        
        # Define empty and filled checkbox regions
        empty_checkbox = (50, 300, 20, 20)  # (x, y, width, height)
        filled_checkbox = (50, 350, 20, 20)  # (x, y, width, height)
        
        # Check if checkboxes are checked
        empty_result = is_checkbox_checked(gray, empty_checkbox)
        filled_result = is_checkbox_checked(gray, filled_checkbox)
        
        # Verify results
        assert isinstance(empty_result, bool)
        assert isinstance(filled_result, bool)
        assert not empty_result  # Empty checkbox should not be checked
        assert filled_result  # Filled checkbox should be checked
    
    def test_is_region_in_bounds(self, sample_image):
        """Test checking if a region is within image bounds."""
        # Define regions
        valid_region = (10, 10, 50, 50)  # Within bounds
        invalid_region1 = (-10, 10, 50, 50)  # Negative x
        invalid_region2 = (10, 10, 200, 50)  # Width too large
        
        # Check if regions are in bounds
        assert is_region_in_bounds(valid_region, sample_image.shape[:2])
        assert not is_region_in_bounds(invalid_region1, sample_image.shape[:2])
        assert not is_region_in_bounds(invalid_region2, sample_image.shape[:2])
    
    def test_extract_region(self, sample_document_image):
        """Test extracting a region from an image."""
        # Define a region to extract (the title area)
        region = (100, 10, 200, 40)  # (x, y, width, height)
        
        # Extract the region
        extracted = extract_region(sample_document_image, region)
        
        # Verify dimensions
        assert extracted.shape[0] == region[3]  # Height
        assert extracted.shape[1] == region[2]  # Width
        assert len(extracted.shape) == 3  # Color channels preserved
    
    def test_preprocess_for_ocr(self, sample_document_image):
        """Test preprocessing an image for OCR."""
        # Preprocess without document type
        result1 = preprocess_for_ocr(sample_document_image)
        
        # Preprocess with document type
        result2 = preprocess_for_ocr(sample_document_image, DocumentType.INVOICE)
        
        # Verify dimensions unchanged
        assert result1.shape[:2] == sample_document_image.shape[:2]
        assert result2.shape[:2] == sample_document_image.shape[:2]
        
        # Results should be different from input and from each other
        assert not np.array_equal(result1, sample_document_image)
        assert not np.array_equal(result2, sample_document_image)
        assert not np.array_equal(result1, result2)  # Different document types should give different results
    
    def test_create_field_mask(self, sample_document_image):
        """Test creating a mask highlighting fields in a document."""
        # Define some field locations
        fields = [
            FieldLocation(page=0, top=0.1, left=0.1, bottom=0.2, right=0.5),
            FieldLocation(page=0, top=0.3, left=0.1, bottom=0.4, right=0.5)
        ]
        
        # Create field mask
        result = create_field_mask(sample_document_image, fields)
        
        # Verify dimensions and channels
        assert result.shape == sample_document_image.shape
        assert len(result.shape) == 3  # Should be color image
        
        # Result should be different from input (has highlighted regions)
        assert not np.array_equal(result, sample_document_image)