#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Image processing utilities for the OCR Service.

This module provides functions for image preprocessing, normalization, enhancement,
and segmentation to prepare documents for OCR processing. It's essential for
optimizing document images before text extraction.
"""

import cv2
import numpy as np
import math
import logging
from typing import Tuple, List, Dict, Optional, Union, Any
from enum import Enum
import os
import tempfile
from PIL import Image, ImageEnhance, ImageFilter

from ..types.documents import DocumentType
from ..types.extraction import FieldLocation
from ..types.errors import ServiceError

# Configure logger
logger = logging.getLogger(__name__)

# Constants
MIN_OCR_DPI = 300  # Minimum DPI for good OCR results
MAX_IMAGE_SIZE = 4096  # Maximum dimension for processing
MIN_IMAGE_SIZE = 50  # Minimum dimension for processing
DEFAULT_BINARIZATION_THRESHOLD = 128  # Default threshold for binarization
MIN_QUALITY_SCORE = 0.4  # Minimum quality score for OCR suitability


class ImageFormat(Enum):
    """Supported image formats for OCR processing."""
    JPEG = "jpeg"
    PNG = "png"
    TIFF = "tiff"
    BMP = "bmp"
    PDF = "pdf"


class ColorSpace(Enum):
    """Color spaces for image processing."""
    RGB = "rgb"
    GRAY = "gray"
    HSV = "hsv"
    BINARY = "binary"


class QualityMetrics(Enum):
    """Image quality metrics for OCR suitability assessment."""
    CONTRAST = "contrast"
    BRIGHTNESS = "brightness"
    SHARPNESS = "sharpness"
    NOISE = "noise"
    RESOLUTION = "resolution"
    SKEW = "skew"


# ===== Image Preprocessing Functions =====

def load_image(image_path: str) -> np.ndarray:
    """Load an image from file path.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Loaded image as numpy array
        
    Raises:
        ServiceError: If image cannot be loaded
    """
    try:
        image = cv2.imread(image_path)
        if image is None:
            raise ServiceError(f"Failed to load image from {image_path}")
        return image
    except Exception as e:
        logger.error(f"Error loading image from {image_path}: {str(e)}")
        raise ServiceError(f"Error loading image: {str(e)}")


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Load an image from bytes.
    
    Args:
        image_bytes: Image data as bytes
        
    Returns:
        Loaded image as numpy array
        
    Raises:
        ServiceError: If image cannot be loaded
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            raise ServiceError("Failed to decode image from bytes")
        return image
    except Exception as e:
        logger.error(f"Error loading image from bytes: {str(e)}")
        raise ServiceError(f"Error loading image from bytes: {str(e)}")


def normalize_size(image: np.ndarray, target_dpi: int = MIN_OCR_DPI) -> np.ndarray:
    """Normalize image size to ensure minimum DPI for OCR.
    
    Args:
        image: Input image
        target_dpi: Target DPI for the image (default: 300)
        
    Returns:
        Resized image
    """
    # Calculate current image dimensions
    height, width = image.shape[:2]
    
    # Check if image is too small
    if width < MIN_IMAGE_SIZE or height < MIN_IMAGE_SIZE:
        logger.warning(f"Image is too small: {width}x{height}. Upscaling to minimum size.")
        scale_factor = max(MIN_IMAGE_SIZE / width, MIN_IMAGE_SIZE / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        return image
    
    # Check if image is too large
    if width > MAX_IMAGE_SIZE or height > MAX_IMAGE_SIZE:
        logger.info(f"Image is too large: {width}x{height}. Downscaling to maximum size.")
        scale_factor = min(MAX_IMAGE_SIZE / width, MAX_IMAGE_SIZE / height)
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
    
    # Estimate current DPI (assuming standard 8.5x11 inch document)
    # This is a rough estimate and would need to be adjusted based on actual document size
    estimated_dpi = min(width / 8.5, height / 11)
    
    # Resize if estimated DPI is too low
    if estimated_dpi < target_dpi:
        logger.info(f"Estimated DPI ({estimated_dpi:.1f}) is below target ({target_dpi}). Upscaling image.")
        scale_factor = target_dpi / estimated_dpi
        new_width = int(width * scale_factor)
        new_height = int(height * scale_factor)
        image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
    
    return image


def normalize_orientation(image: np.ndarray) -> np.ndarray:
    """Detect and correct image orientation to ensure text is horizontal.
    
    Args:
        image: Input image
        
    Returns:
        Orientation-corrected image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Use Hough Line Transform to detect lines
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
    
    if lines is None or len(lines) == 0:
        logger.info("No lines detected for orientation correction. Returning original image.")
        return image
    
    # Calculate angles of detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 - x1 == 0:  # Avoid division by zero
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # Consider only angles that are likely to be text lines (-30 to 30 degrees)
        if abs(angle) <= 30 or abs(angle - 180) <= 30 or abs(angle + 180) <= 30:
            angles.append(angle)
    
    if not angles:
        logger.info("No valid text line angles detected. Returning original image.")
        return image
    
    # Find the most common angle using a histogram approach
    hist, bins = np.histogram(angles, bins=60, range=(-30, 30))
    dominant_angle_bin = np.argmax(hist)
    dominant_angle = (bins[dominant_angle_bin] + bins[dominant_angle_bin + 1]) / 2
    
    # If the dominant angle is close to horizontal, no rotation needed
    if abs(dominant_angle) < 1.0:
        return image
    
    logger.info(f"Detected skew angle: {dominant_angle:.2f} degrees. Correcting orientation.")
    
    # Rotate the image to correct orientation
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, dominant_angle, 1.0)
    rotated_image = cv2.warpAffine(image, rotation_matrix, (width, height), 
                                  flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated_image


def convert_color_space(image: np.ndarray, target_space: ColorSpace) -> np.ndarray:
    """Convert image to the specified color space.
    
    Args:
        image: Input image
        target_space: Target color space
        
    Returns:
        Converted image
    """
    # Determine current color space
    if len(image.shape) == 2:
        current_space = ColorSpace.GRAY
    else:
        current_space = ColorSpace.RGB  # Assuming BGR in OpenCV
    
    # Return if already in target space
    if current_space == target_space:
        return image
    
    # Convert to target space
    if target_space == ColorSpace.GRAY:
        if current_space == ColorSpace.RGB:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif current_space == ColorSpace.HSV:
            return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    elif target_space == ColorSpace.RGB:
        if current_space == ColorSpace.GRAY:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif current_space == ColorSpace.HSV:
            return cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
        elif current_space == ColorSpace.BINARY:
            # Convert binary to grayscale, then to RGB
            return cv2.cvtColor(image * 255, cv2.COLOR_GRAY2BGR)
    
    elif target_space == ColorSpace.HSV:
        if current_space == ColorSpace.GRAY:
            rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            return cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
        elif current_space == ColorSpace.RGB:
            return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    elif target_space == ColorSpace.BINARY:
        if current_space == ColorSpace.GRAY:
            _, binary = cv2.threshold(image, DEFAULT_BINARIZATION_THRESHOLD, 1, cv2.THRESH_BINARY)
            return binary
        elif current_space == ColorSpace.RGB:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, DEFAULT_BINARIZATION_THRESHOLD, 1, cv2.THRESH_BINARY)
            return binary
        elif current_space == ColorSpace.HSV:
            rgb = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)
            gray = cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, DEFAULT_BINARIZATION_THRESHOLD, 1, cv2.THRESH_BINARY)
            return binary
    
    # If we get here, the conversion is not supported
    logger.warning(f"Unsupported color space conversion from {current_space} to {target_space}")
    return image


# ===== Image Enhancement Functions =====

def enhance_contrast(image: np.ndarray, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
    """Enhance image contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Input image
        clip_limit: Threshold for contrast limiting
        tile_grid_size: Size of grid for histogram equalization
        
    Returns:
        Contrast-enhanced image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        is_color = True
    else:
        gray = image.copy()
        is_color = False
    
    # Apply CLAHE
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    enhanced_gray = clahe.apply(gray)
    
    # Return enhanced image in original color space
    if is_color:
        # Create YUV image (Y = luminance, UV = chrominance)
        yuv_image = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
        # Replace Y channel with enhanced image
        yuv_image[:,:,0] = enhanced_gray
        # Convert back to BGR
        enhanced_image = cv2.cvtColor(yuv_image, cv2.COLOR_YUV2BGR)
        return enhanced_image
    else:
        return enhanced_gray


def remove_noise(image: np.ndarray, method: str = 'gaussian', kernel_size: int = 5) -> np.ndarray:
    """Remove noise from image using various filtering methods.
    
    Args:
        image: Input image
        method: Noise removal method ('gaussian', 'median', 'bilateral', 'nlm')
        kernel_size: Size of kernel for filtering
        
    Returns:
        Noise-reduced image
    """
    if method == 'gaussian':
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)
    
    elif method == 'median':
        return cv2.medianBlur(image, kernel_size)
    
    elif method == 'bilateral':
        # Bilateral filter preserves edges while removing noise
        if len(image.shape) == 3:
            return cv2.bilateralFilter(image, kernel_size, 75, 75)
        else:
            return cv2.bilateralFilter(image, kernel_size, 75, 75)
    
    elif method == 'nlm':
        # Non-local means denoising (best quality but slowest)
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
        else:
            return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
    
    else:
        logger.warning(f"Unknown noise removal method: {method}. Using gaussian blur.")
        return cv2.GaussianBlur(image, (kernel_size, kernel_size), 0)


def sharpen_image(image: np.ndarray, amount: float = 1.5) -> np.ndarray:
    """Sharpen image to improve text clarity.
    
    Args:
        image: Input image
        amount: Sharpening intensity
        
    Returns:
        Sharpened image
    """
    # Convert to PIL Image for easier sharpening
    if len(image.shape) == 3:
        # OpenCV uses BGR, PIL uses RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(image_rgb)
    else:
        pil_image = Image.fromarray(image)
    
    # Apply sharpening filter
    enhancer = ImageEnhance.Sharpness(pil_image)
    sharpened_pil = enhancer.enhance(amount)
    
    # Convert back to numpy array
    if len(image.shape) == 3:
        sharpened_rgb = np.array(sharpened_pil)
        sharpened = cv2.cvtColor(sharpened_rgb, cv2.COLOR_RGB2BGR)
    else:
        sharpened = np.array(sharpened_pil)
    
    return sharpened


def binarize_image(image: np.ndarray, method: str = 'otsu') -> np.ndarray:
    """Convert image to binary (black and white) using various thresholding methods.
    
    Args:
        image: Input grayscale image
        method: Binarization method ('simple', 'otsu', 'adaptive', 'sauvola')
        
    Returns:
        Binarized image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    if method == 'simple':
        _, binary = cv2.threshold(gray, DEFAULT_BINARIZATION_THRESHOLD, 255, cv2.THRESH_BINARY)
    
    elif method == 'otsu':
        # Otsu's method automatically determines optimal threshold value
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    elif method == 'adaptive':
        # Adaptive thresholding handles varying illumination
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
    
    elif method == 'sauvola':
        # Sauvola's method is good for document images
        # This is an approximation of Sauvola using OpenCV
        window_size = 25
        k = 0.2
        r = 128
        
        # Calculate mean and standard deviation using local windows
        mean = cv2.boxFilter(gray, -1, (window_size, window_size), 
                            borderType=cv2.BORDER_REPLICATE)
        mean_sq = cv2.boxFilter(gray**2, -1, (window_size, window_size), 
                               borderType=cv2.BORDER_REPLICATE)
        variance = mean_sq - mean**2
        std = np.sqrt(variance)
        
        # Calculate Sauvola threshold
        threshold = mean * (1 + k * ((std / r) - 1))
        binary = np.zeros_like(gray)
        binary[gray > threshold] = 255
    
    else:
        logger.warning(f"Unknown binarization method: {method}. Using Otsu's method.")
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary


def deskew_image(image: np.ndarray) -> np.ndarray:
    """Detect and correct skew in document images.
    
    Args:
        image: Input image
        
    Returns:
        Deskewed image
    """
    # This is a more specialized version of normalize_orientation focused on small skew angles
    
    # Convert to grayscale and binarize
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binarize the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find all non-zero points
    coords = np.column_stack(np.where(binary > 0))
    
    if len(coords) == 0:
        logger.info("No text detected for deskewing. Returning original image.")
        return image
    
    # Find rotated rectangle around text
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    
    # Adjust angle for proper deskewing
    if angle < -45:
        angle = 90 + angle
    else:
        angle = -angle
    
    # If angle is very small, no need to deskew
    if abs(angle) < 0.5:
        return image
    
    logger.info(f"Detected skew angle: {angle:.2f} degrees. Deskewing image.")
    
    # Rotate the image to correct skew
    height, width = image.shape[:2]
    center = (width // 2, height // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(image, rotation_matrix, (width, height), 
                             flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return deskewed


# ===== Document Segmentation Functions =====

def detect_text_regions(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect regions containing text in the document.
    
    Args:
        image: Input image
        
    Returns:
        List of bounding boxes (x, y, width, height) for text regions
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binarize the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Apply morphological operations to connect text into blocks
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(binary, kernel, iterations=3)
    
    # Find contours of text regions
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on size and aspect ratio
    text_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h)
        area = w * h
        
        # Filter out very small regions and those with extreme aspect ratios
        if area > 100 and 0.1 < aspect_ratio < 15:
            text_regions.append((x, y, w, h))
    
    logger.info(f"Detected {len(text_regions)} text regions in the document")
    return text_regions


def detect_paragraphs(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect paragraph regions in the document.
    
    Args:
        image: Input image
        
    Returns:
        List of bounding boxes (x, y, width, height) for paragraph regions
    """
    # Similar to detect_text_regions but with different morphological operations
    # to group text lines into paragraphs
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binarize the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Apply morphological operations to connect text lines into paragraphs
    # First connect characters in a line
    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (10, 1))
    connected_lines = cv2.dilate(binary, kernel_horizontal, iterations=1)
    
    # Then connect lines in a paragraph
    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 20))
    connected_paragraphs = cv2.dilate(connected_lines, kernel_vertical, iterations=1)
    
    # Find contours of paragraph regions
    contours, _ = cv2.findContours(connected_paragraphs, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on size
    paragraph_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        
        # Filter out very small regions
        if area > 500:
            paragraph_regions.append((x, y, w, h))
    
    logger.info(f"Detected {len(paragraph_regions)} paragraph regions in the document")
    return paragraph_regions


def detect_tables(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect table regions in the document.
    
    Args:
        image: Input image
        
    Returns:
        List of bounding boxes (x, y, width, height) for table regions
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binarize the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Apply morphological operations to detect table structures
    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=3)
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel, iterations=3)
    
    # Combine horizontal and vertical lines
    table_structure = cv2.add(horizontal_lines, vertical_lines)
    
    # Dilate to connect nearby lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    table_structure = cv2.dilate(table_structure, kernel, iterations=2)
    
    # Find contours of table regions
    contours, _ = cv2.findContours(table_structure, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on size and shape
    table_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h)
        area = w * h
        
        # Tables typically have reasonable aspect ratios and are larger
        if area > 5000 and 0.2 < aspect_ratio < 5:
            table_regions.append((x, y, w, h))
    
    logger.info(f"Detected {len(table_regions)} table regions in the document")
    return table_regions


def detect_form_fields(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detect form fields (checkboxes, text fields, etc.) in the document.
    
    Args:
        image: Input image
        
    Returns:
        List of dictionaries containing field information
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Binarize the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Detect form field regions
    form_fields = []
    
    # Detect checkboxes (small squares)
    checkbox_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    checkbox_image = cv2.morphologyEx(binary, cv2.MORPH_OPEN, checkbox_kernel, iterations=1)
    checkbox_contours, _ = cv2.findContours(checkbox_image, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in checkbox_contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h)
        area = w * h
        
        # Checkboxes are typically square and small
        if 100 < area < 1000 and 0.8 < aspect_ratio < 1.2:
            # Check if it's actually a checkbox by looking for a square shape
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
            
            if len(approx) == 4:  # It's a quadrilateral
                form_fields.append({
                    'type': 'checkbox',
                    'bbox': (x, y, w, h),
                    'checked': is_checkbox_checked(gray, (x, y, w, h))
                })
    
    # Detect text fields (horizontal lines with space above)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    line_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    for contour in line_contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h)
        
        # Text field underlines are typically very wide and thin
        if w > 50 and aspect_ratio > 10:
            # Look for text above the line
            text_region = (x, y - 30, w, 30)  # 30 pixels above the line
            if is_region_in_bounds(text_region, gray.shape):
                form_fields.append({
                    'type': 'text_field',
                    'bbox': (x, y - 30, w, 30),
                    'underline': (x, y, w, h)
                })
    
    logger.info(f"Detected {len(form_fields)} form fields in the document")
    return form_fields


def segment_document(image: np.ndarray, document_type: Optional[DocumentType] = None) -> Dict[str, List[Dict[str, Any]]]:
    """Segment document into different regions based on content type.
    
    Args:
        image: Input image
        document_type: Type of document for specialized segmentation
        
    Returns:
        Dictionary containing lists of different region types
    """
    # Initialize result dictionary
    segments = {
        'text_regions': [],
        'paragraphs': [],
        'tables': [],
        'form_fields': [],
        'images': []
    }
    
    # Detect text regions
    text_boxes = detect_text_regions(image)
    segments['text_regions'] = [{'bbox': box, 'type': 'text'} for box in text_boxes]
    
    # Detect paragraphs
    paragraph_boxes = detect_paragraphs(image)
    segments['paragraphs'] = [{'bbox': box, 'type': 'paragraph'} for box in paragraph_boxes]
    
    # Detect tables
    table_boxes = detect_tables(image)
    segments['tables'] = [{'bbox': box, 'type': 'table'} for box in table_boxes]
    
    # Detect form fields
    form_fields = detect_form_fields(image)
    segments['form_fields'] = form_fields
    
    # Apply document type-specific segmentation if available
    if document_type:
        if document_type == DocumentType.APPLICATION:
            # Application forms typically have more structured form fields
            # Enhance form field detection for applications
            pass
        
        elif document_type == DocumentType.TAX_RETURN:
            # Tax returns typically have tables with numerical data
            # Enhance table detection for tax returns
            pass
        
        elif document_type == DocumentType.BANK_STATEMENT:
            # Bank statements have tables with transaction data
            # Enhance table detection for bank statements
            pass
    
    return segments


# ===== Image Format Handling Functions =====

def convert_to_format(image: np.ndarray, target_format: ImageFormat) -> bytes:
    """Convert image to the specified format.
    
    Args:
        image: Input image
        target_format: Target image format
        
    Returns:
        Image data in the specified format as bytes
    """
    # Encode image to the target format
    if target_format == ImageFormat.JPEG:
        _, encoded_image = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, 95])
    
    elif target_format == ImageFormat.PNG:
        _, encoded_image = cv2.imencode('.png', image)
    
    elif target_format == ImageFormat.TIFF:
        _, encoded_image = cv2.imencode('.tiff', image)
    
    elif target_format == ImageFormat.BMP:
        _, encoded_image = cv2.imencode('.bmp', image)
    
    else:
        logger.warning(f"Unsupported target format: {target_format}. Converting to PNG.")
        _, encoded_image = cv2.imencode('.png', image)
    
    return encoded_image.tobytes()


def save_image(image: np.ndarray, output_path: str, image_format: Optional[ImageFormat] = None) -> str:
    """Save image to file.
    
    Args:
        image: Input image
        output_path: Path to save the image
        image_format: Format to save the image (if None, inferred from output_path)
        
    Returns:
        Path to the saved image
    """
    try:
        # If format is specified, convert to that format
        if image_format:
            image_data = convert_to_format(image, image_format)
            with open(output_path, 'wb') as f:
                f.write(image_data)
        else:
            # Otherwise, let OpenCV determine format from file extension
            cv2.imwrite(output_path, image)
        
        return output_path
    
    except Exception as e:
        logger.error(f"Error saving image to {output_path}: {str(e)}")
        raise ServiceError(f"Error saving image: {str(e)}")


def get_image_format(image_path: str) -> ImageFormat:
    """Determine image format from file path.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Detected image format
    """
    extension = os.path.splitext(image_path)[1].lower()
    
    if extension == '.jpg' or extension == '.jpeg':
        return ImageFormat.JPEG
    elif extension == '.png':
        return ImageFormat.PNG
    elif extension == '.tiff' or extension == '.tif':
        return ImageFormat.TIFF
    elif extension == '.bmp':
        return ImageFormat.BMP
    elif extension == '.pdf':
        return ImageFormat.PDF
    else:
        logger.warning(f"Unknown image format: {extension}. Assuming JPEG.")
        return ImageFormat.JPEG


# ===== Image Quality Assessment Functions =====

def assess_image_quality(image: np.ndarray) -> Dict[str, float]:
    """Assess image quality for OCR suitability.
    
    Args:
        image: Input image
        
    Returns:
        Dictionary of quality metrics with scores between 0.0 and 1.0
    """
    # Initialize quality metrics
    quality_metrics = {
        QualityMetrics.CONTRAST.value: 0.0,
        QualityMetrics.BRIGHTNESS.value: 0.0,
        QualityMetrics.SHARPNESS.value: 0.0,
        QualityMetrics.NOISE.value: 0.0,
        QualityMetrics.RESOLUTION.value: 0.0,
        QualityMetrics.SKEW.value: 0.0
    }
    
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Assess contrast
    min_val, max_val, _, _ = cv2.minMaxLoc(gray)
    contrast_range = max_val - min_val
    quality_metrics[QualityMetrics.CONTRAST.value] = min(contrast_range / 255.0, 1.0)
    
    # Assess brightness
    mean_brightness = np.mean(gray) / 255.0
    # Optimal brightness is around 0.5 (middle of range)
    brightness_score = 1.0 - 2.0 * abs(mean_brightness - 0.5)
    quality_metrics[QualityMetrics.BRIGHTNESS.value] = max(brightness_score, 0.0)
    
    # Assess sharpness using Laplacian variance
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    laplacian_var = laplacian.var()
    # Normalize sharpness score (empirical values based on testing)
    sharpness_score = min(laplacian_var / 500.0, 1.0)
    quality_metrics[QualityMetrics.SHARPNESS.value] = sharpness_score
    
    # Assess noise using homogeneity of regions
    # Calculate local standard deviation
    mean, stddev = cv2.meanStdDev(gray)
    noise_level = stddev[0][0] / 128.0  # Normalize to [0, 1] range
    noise_score = 1.0 - min(noise_level, 1.0)
    quality_metrics[QualityMetrics.NOISE.value] = noise_score
    
    # Assess resolution based on image size
    height, width = gray.shape
    min_dimension = min(height, width)
    # Normalize resolution score (empirical values based on testing)
    resolution_score = min(min_dimension / 1000.0, 1.0)
    quality_metrics[QualityMetrics.RESOLUTION.value] = resolution_score
    
    # Assess skew using Hough Line Transform
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi/180, threshold=100, minLineLength=100, maxLineGap=10)
    
    if lines is not None and len(lines) > 0:
        angles = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            if x2 - x1 == 0:  # Avoid division by zero
                continue
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            # Consider only angles that are likely to be text lines
            if abs(angle) <= 30 or abs(angle - 180) <= 30 or abs(angle + 180) <= 30:
                angles.append(angle)
        
        if angles:
            # Find the most common angle
            hist, bins = np.histogram(angles, bins=60, range=(-30, 30))
            dominant_angle_bin = np.argmax(hist)
            dominant_angle = (bins[dominant_angle_bin] + bins[dominant_angle_bin + 1]) / 2
            
            # Calculate skew score (0 degrees is perfect)
            skew_score = 1.0 - min(abs(dominant_angle) / 30.0, 1.0)
            quality_metrics[QualityMetrics.SKEW.value] = skew_score
        else:
            # No valid text line angles detected
            quality_metrics[QualityMetrics.SKEW.value] = 0.5  # Neutral score
    else:
        # No lines detected
        quality_metrics[QualityMetrics.SKEW.value] = 0.5  # Neutral score
    
    return quality_metrics


def calculate_overall_quality(quality_metrics: Dict[str, float]) -> float:
    """Calculate overall image quality score from individual metrics.
    
    Args:
        quality_metrics: Dictionary of quality metrics
        
    Returns:
        Overall quality score between 0.0 and 1.0
    """
    # Define weights for each metric based on importance for OCR
    weights = {
        QualityMetrics.CONTRAST.value: 0.25,
        QualityMetrics.BRIGHTNESS.value: 0.15,
        QualityMetrics.SHARPNESS.value: 0.25,
        QualityMetrics.NOISE.value: 0.15,
        QualityMetrics.RESOLUTION.value: 0.10,
        QualityMetrics.SKEW.value: 0.10
    }
    
    # Calculate weighted sum
    weighted_sum = sum(quality_metrics[metric] * weights[metric] for metric in quality_metrics)
    
    return weighted_sum


def is_suitable_for_ocr(image: np.ndarray) -> Tuple[bool, Dict[str, float]]:
    """Determine if image is suitable for OCR processing.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (is_suitable, quality_metrics)
    """
    # Assess image quality
    quality_metrics = assess_image_quality(image)
    overall_quality = calculate_overall_quality(quality_metrics)
    
    # Log quality assessment results
    logger.info(f"Image quality assessment: {quality_metrics}")
    logger.info(f"Overall quality score: {overall_quality:.2f}")
    
    # Determine if image is suitable for OCR
    is_suitable = overall_quality >= MIN_QUALITY_SCORE
    
    if not is_suitable:
        logger.warning(f"Image quality ({overall_quality:.2f}) is below minimum threshold ({MIN_QUALITY_SCORE})")
        
        # Identify specific issues
        issues = []
        if quality_metrics[QualityMetrics.CONTRAST.value] < 0.4:
            issues.append("low contrast")
        if quality_metrics[QualityMetrics.BRIGHTNESS.value] < 0.4:
            issues.append("poor brightness")
        if quality_metrics[QualityMetrics.SHARPNESS.value] < 0.4:
            issues.append("insufficient sharpness")
        if quality_metrics[QualityMetrics.NOISE.value] < 0.4:
            issues.append("excessive noise")
        if quality_metrics[QualityMetrics.RESOLUTION.value] < 0.4:
            issues.append("low resolution")
        if quality_metrics[QualityMetrics.SKEW.value] < 0.4:
            issues.append("significant skew")
        
        if issues:
            logger.warning(f"Image quality issues: {', '.join(issues)}")
    
    return is_suitable, quality_metrics


def suggest_enhancements(quality_metrics: Dict[str, float]) -> List[str]:
    """Suggest image enhancements based on quality assessment.
    
    Args:
        quality_metrics: Dictionary of quality metrics
        
    Returns:
        List of suggested enhancement operations
    """
    suggestions = []
    
    # Check each metric and suggest appropriate enhancements
    if quality_metrics[QualityMetrics.CONTRAST.value] < 0.4:
        suggestions.append("enhance_contrast")
    
    if quality_metrics[QualityMetrics.BRIGHTNESS.value] < 0.4:
        suggestions.append("normalize_brightness")
    
    if quality_metrics[QualityMetrics.SHARPNESS.value] < 0.4:
        suggestions.append("sharpen_image")
    
    if quality_metrics[QualityMetrics.NOISE.value] < 0.4:
        suggestions.append("remove_noise")
    
    if quality_metrics[QualityMetrics.RESOLUTION.value] < 0.4:
        suggestions.append("normalize_size")
    
    if quality_metrics[QualityMetrics.SKEW.value] < 0.4:
        suggestions.append("deskew_image")
    
    return suggestions


# ===== Helper Functions =====

def is_checkbox_checked(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
    """Determine if a checkbox is checked.
    
    Args:
        image: Input grayscale image
        bbox: Bounding box of the checkbox (x, y, width, height)
        
    Returns:
        True if checkbox is checked, False otherwise
    """
    x, y, w, h = bbox
    
    # Extract checkbox region
    checkbox_region = image[y:y+h, x:x+w]
    
    # Binarize the region
    _, binary = cv2.threshold(checkbox_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Calculate percentage of black pixels (potential check mark)
    black_pixel_percentage = np.sum(binary == 255) / (w * h)
    
    # If more than 20% of pixels are black, consider it checked
    return black_pixel_percentage > 0.2


def is_region_in_bounds(region: Tuple[int, int, int, int], image_shape: Tuple[int, int]) -> bool:
    """Check if a region is within image bounds.
    
    Args:
        region: Region as (x, y, width, height)
        image_shape: Image shape as (height, width)
        
    Returns:
        True if region is within bounds, False otherwise
    """
    x, y, w, h = region
    height, width = image_shape
    
    return (x >= 0 and y >= 0 and x + w <= width and y + h <= height)


def extract_region(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
    """Extract a region from an image.
    
    Args:
        image: Input image
        bbox: Bounding box as (x, y, width, height)
        
    Returns:
        Extracted region
    """
    x, y, w, h = bbox
    
    # Ensure region is within image bounds
    if not is_region_in_bounds(bbox, image.shape[:2]):
        logger.warning(f"Region {bbox} is outside image bounds {image.shape[:2]}")
        # Adjust region to fit within image bounds
        x = max(0, x)
        y = max(0, y)
        w = min(w, image.shape[1] - x)
        h = min(h, image.shape[0] - y)
    
    return image[y:y+h, x:x+w]


def preprocess_for_ocr(image: np.ndarray, document_type: Optional[DocumentType] = None) -> np.ndarray:
    """Apply a standard preprocessing pipeline for OCR.
    
    Args:
        image: Input image
        document_type: Type of document for specialized preprocessing
        
    Returns:
        Preprocessed image ready for OCR
    """
    # Normalize image size
    image = normalize_size(image)
    
    # Correct orientation
    image = normalize_orientation(image)
    
    # Convert to grayscale
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Enhance contrast
    enhanced = enhance_contrast(gray)
    
    # Remove noise
    denoised = remove_noise(enhanced, method='gaussian')
    
    # Sharpen image
    sharpened = sharpen_image(denoised)
    
    # Apply document type-specific preprocessing if available
    if document_type:
        if document_type == DocumentType.APPLICATION:
            # Application forms typically have form fields
            # Enhance form field visibility
            pass
        
        elif document_type == DocumentType.TAX_RETURN:
            # Tax returns typically have tables with numerical data
            # Enhance table visibility
            pass
        
        elif document_type == DocumentType.BANK_STATEMENT:
            # Bank statements have tables with transaction data
            # Enhance table visibility
            pass
    
    return sharpened


def create_field_mask(image: np.ndarray, field_locations: List[FieldLocation]) -> np.ndarray:
    """Create a mask highlighting specific fields in the document.
    
    Args:
        image: Input image
        field_locations: List of field locations
        
    Returns:
        Image with highlighted fields
    """
    # Create a copy of the image for highlighting
    if len(image.shape) == 2:
        # Convert grayscale to color for highlighting
        highlighted = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    else:
        highlighted = image.copy()
    
    # Draw rectangles around each field
    for field in field_locations:
        x, y, w, h = field.bbox
        cv2.rectangle(highlighted, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        # Add field label if available
        if hasattr(field, 'label') and field.label:
            cv2.putText(highlighted, field.label, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    
    return highlighted