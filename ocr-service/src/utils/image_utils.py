#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Image processing utilities for the OCR Service.

This module provides functions for image preprocessing, normalization, enhancement,
and segmentation to prepare documents for OCR processing. These utilities are essential
for optimizing document images before text extraction to achieve high accuracy OCR results.

The module includes functions for:
- Image loading and basic operations
- Image preprocessing (normalization, orientation correction)
- Image enhancement (contrast, noise removal, sharpening)
- Document segmentation (text regions, tables, form fields)
- Image format handling
- Image quality assessment

These functions are designed to work with TensorFlow OCR models and support GPU acceleration
for optimal performance.
"""

import os
import cv2
import numpy as np
import math
from enum import Enum
import tempfile
from typing import Tuple, List, Dict, Union, Optional, Any

from src.types.errors import ServiceError
from src.types.documents import DocumentType
from src.types.extraction import FieldLocation


# ===== Enums for image processing =====

class ColorSpace(Enum):
    """Enum for color space conversion options."""
    RGB = 1
    BGR = 2
    GRAY = 3
    HSV = 4
    BINARY = 5


class ImageFormat(Enum):
    """Enum for image file formats."""
    JPEG = 1
    PNG = 2
    TIFF = 3
    BMP = 4
    PDF = 5


class QualityMetrics(Enum):
    """Enum for image quality assessment metrics."""
    CONTRAST = "contrast"
    BRIGHTNESS = "brightness"
    SHARPNESS = "sharpness"
    NOISE = "noise"
    RESOLUTION = "resolution"
    SKEW = "skew"


# ===== Image loading and basic operations =====

def load_image(file_path: str) -> np.ndarray:
    """Load an image from a file path.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Image as a numpy array
        
    Raises:
        ServiceError: If the image cannot be loaded
    """
    try:
        image = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ServiceError(f"Failed to load image from {file_path}")
        return image
    except Exception as e:
        raise ServiceError(f"Error loading image from {file_path}: {str(e)}")


def load_image_from_bytes(image_bytes: bytes) -> np.ndarray:
    """Load an image from bytes.
    
    Args:
        image_bytes: Image data as bytes
        
    Returns:
        Image as a numpy array
        
    Raises:
        ServiceError: If the image cannot be loaded
    """
    try:
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_UNCHANGED)
        if image is None:
            raise ServiceError("Failed to decode image from bytes")
        return image
    except Exception as e:
        raise ServiceError(f"Error loading image from bytes: {str(e)}")


# ===== Image preprocessing =====

def normalize_size(image: np.ndarray, min_size: int = 50, max_size: int = 4096) -> np.ndarray:
    """Normalize image size to ensure it's within acceptable bounds for OCR processing.
    
    Args:
        image: Input image
        min_size: Minimum dimension size
        max_size: Maximum dimension size
        
    Returns:
        Resized image
    """
    height, width = image.shape[:2]
    
    # Check if image is too small
    if height < min_size or width < min_size:
        scale = max(min_size / height, min_size / width)
        new_height = int(height * scale)
        new_width = int(width * scale)
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_CUBIC)
        return resized
    
    # Check if image is too large
    if height > max_size or width > max_size:
        scale = min(max_size / height, max_size / width)
        new_height = int(height * scale)
        new_width = int(width * scale)
        resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        return resized
    
    return image


def normalize_orientation(image: np.ndarray) -> np.ndarray:
    """Correct the orientation of the document image.
    
    Uses Hough Line Transform to detect the dominant orientation of text lines
    and rotates the image to correct skew.
    
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
    
    # Apply edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    
    # Use Hough Line Transform to detect lines
    lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
    
    # If no lines detected, return original image
    if lines is None or len(lines) == 0:
        return image
    
    # Calculate the dominant angle
    angles = []
    for line in lines:
        rho, theta = line[0]
        # Only consider mostly horizontal or vertical lines
        if (theta < np.pi/4 or theta > 3*np.pi/4):
            angles.append(theta)
    
    if not angles:
        return image
    
    # Get median angle to avoid outliers
    median_angle = np.median(angles)
    
    # Convert to degrees and adjust
    angle_degrees = np.degrees(median_angle)
    if angle_degrees < 45:
        angle_degrees = angle_degrees
    elif angle_degrees > 135:
        angle_degrees = angle_degrees - 180
    else:
        return image  # No significant skew detected
    
    # Only correct if skew is significant (more than 0.5 degrees)
    if abs(angle_degrees) < 0.5:
        return image
    
    # Rotate the image to correct orientation
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle_degrees, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return rotated


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
        current_space = ColorSpace.BGR  # OpenCV default
    
    # If already in target space, return as is
    if current_space == target_space:
        return image
    
    # Convert to target space
    if target_space == ColorSpace.GRAY:
        if current_space != ColorSpace.GRAY:
            return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif target_space == ColorSpace.RGB:
        if current_space == ColorSpace.GRAY:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif current_space == ColorSpace.BGR:
            return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif target_space == ColorSpace.BGR:
        if current_space == ColorSpace.GRAY:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        elif current_space == ColorSpace.RGB:
            return cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    elif target_space == ColorSpace.HSV:
        if current_space == ColorSpace.GRAY:
            # Convert gray to BGR first, then to HSV
            temp = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            return cv2.cvtColor(temp, cv2.COLOR_BGR2HSV)
        else:
            return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    elif target_space == ColorSpace.BINARY:
        # Convert to grayscale first if needed
        if current_space != ColorSpace.GRAY:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image
        # Apply Otsu's thresholding
        _, binary = cv2.threshold(gray, 0, 1, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    
    # Default case - return original image
    return image


# ===== Image enhancement =====

def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Enhance the contrast of the image using CLAHE (Contrast Limited Adaptive Histogram Equalization).
    
    Args:
        image: Input image
        
    Returns:
        Contrast-enhanced image
    """
    # Handle color images
    if len(image.shape) == 3:
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        
        # Merge channels and convert back to BGR
        merged = cv2.merge((cl, a, b))
        enhanced = cv2.cvtColor(merged, cv2.COLOR_LAB2BGR)
        return enhanced
    else:
        # For grayscale images
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced


def remove_noise(image: np.ndarray, method: str = 'gaussian') -> np.ndarray:
    """Remove noise from the image using various filtering methods.
    
    Args:
        image: Input image
        method: Noise removal method ('gaussian', 'median', or 'bilateral')
        
    Returns:
        Denoised image
    """
    if method == 'gaussian':
        # Gaussian blur for general noise reduction
        return cv2.GaussianBlur(image, (5, 5), 0)
    elif method == 'median':
        # Median filter for salt-and-pepper noise
        return cv2.medianBlur(image, 5)
    elif method == 'bilateral':
        # Bilateral filter preserves edges while removing noise
        if len(image.shape) == 3:
            return cv2.bilateralFilter(image, 9, 75, 75)
        else:
            # For grayscale images
            return cv2.bilateralFilter(image, 9, 75, 75)
    else:
        # Default to Gaussian blur
        return cv2.GaussianBlur(image, (5, 5), 0)


def sharpen_image(image: np.ndarray) -> np.ndarray:
    """Sharpen the image to enhance text edges.
    
    Args:
        image: Input image
        
    Returns:
        Sharpened image
    """
    # Create sharpening kernel
    kernel = np.array([[-1, -1, -1],
                       [-1,  9, -1],
                       [-1, -1, -1]])
    
    # Apply kernel to the image
    sharpened = cv2.filter2D(image, -1, kernel)
    return sharpened


def binarize_image(image: np.ndarray, method: str = 'otsu') -> np.ndarray:
    """Convert image to binary (black and white) using various thresholding methods.
    
    Args:
        image: Input image
        method: Binarization method ('simple', 'otsu', 'adaptive', or 'sauvola')
        
    Returns:
        Binarized image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    
    if method == 'simple':
        # Simple thresholding
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
    elif method == 'otsu':
        # Otsu's thresholding
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    elif method == 'adaptive':
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
    elif method == 'sauvola':
        # Sauvola thresholding (local adaptive)
        # This is an approximation of Sauvola using OpenCV
        window_size = 25
        k = 0.2
        r = 128
        
        # Calculate local mean using a moving window
        mean = cv2.boxFilter(gray, -1, (window_size, window_size), 
                            borderType=cv2.BORDER_REPLICATE)
        
        # Calculate local standard deviation
        mean_sq = cv2.boxFilter(gray**2, -1, (window_size, window_size), 
                               borderType=cv2.BORDER_REPLICATE)
        std = np.sqrt(mean_sq - mean**2)
        
        # Calculate Sauvola threshold
        threshold = mean * (1 + k * ((std / r) - 1))
        binary = np.zeros_like(gray)
        binary[gray > threshold] = 255
    else:
        # Default to Otsu's method
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    return binary


def deskew_image(image: np.ndarray) -> np.ndarray:
    """Deskew the image by detecting and correcting the skew angle.
    
    Args:
        image: Input image
        
    Returns:
        Deskewed image
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Threshold the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find all non-zero points
    coords = np.column_stack(np.where(binary > 0))
    
    # If no text is detected, return original image
    if len(coords) <= 10:
        return image
    
    # Find rotated rectangle
    rect = cv2.minAreaRect(coords)
    angle = rect[-1]
    
    # Adjust angle
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    
    # Only deskew if angle is significant
    if abs(angle) < 0.5:
        return image
    
    # Rotate the image to correct the skew
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    deskewed = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    return deskewed


# ===== Document segmentation =====

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
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Apply morphological operations to connect nearby text
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 1))
    connected = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
    
    # Find contours
    contours, _ = cv2.findContours(connected, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on size and aspect ratio
    text_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h) if h > 0 else 0
        
        # Filter based on size and aspect ratio
        if w > 20 and h > 5 and aspect_ratio > 1.0 and aspect_ratio < 10.0:
            text_regions.append((x, y, w, h))
    
    return text_regions


def detect_paragraphs(image: np.ndarray) -> List[Tuple[int, int, int, int]]:
    """Detect paragraph regions in the document.
    
    Args:
        image: Input image
        
    Returns:
        List of bounding boxes (x, y, width, height) for paragraph regions
    """
    # First detect text regions
    text_regions = detect_text_regions(image)
    
    # If no text regions found, return empty list
    if not text_regions:
        return []
    
    # Group text regions into paragraphs based on vertical proximity
    text_regions.sort(key=lambda r: r[1])  # Sort by y-coordinate
    
    paragraphs = []
    current_paragraph = list(text_regions[0])
    
    for region in text_regions[1:]:
        x, y, w, h = region
        # If this region is close to the bottom of current paragraph, extend it
        if y <= (current_paragraph[1] + current_paragraph[3] + 20):  # 20px threshold
            # Update paragraph bounds
            min_x = min(current_paragraph[0], x)
            min_y = min(current_paragraph[1], y)
            max_x = max(current_paragraph[0] + current_paragraph[2], x + w)
            max_y = max(current_paragraph[1] + current_paragraph[3], y + h)
            
            current_paragraph = [min_x, min_y, max_x - min_x, max_y - min_y]
        else:
            # Start a new paragraph
            paragraphs.append(tuple(current_paragraph))
            current_paragraph = list(region)
    
    # Add the last paragraph
    paragraphs.append(tuple(current_paragraph))
    
    return paragraphs


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
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Detect horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    
    # Detect vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
    
    # Combine horizontal and vertical lines
    table_mask = cv2.bitwise_or(horizontal_lines, vertical_lines)
    
    # Dilate to connect nearby lines
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    table_mask = cv2.dilate(table_mask, kernel, iterations=3)
    
    # Find contours
    contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours based on size
    tables = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter based on size
        if w > 100 and h > 100:
            tables.append((x, y, w, h))
    
    return tables


def detect_form_fields(image: np.ndarray) -> List[Dict[str, Any]]:
    """Detect form fields (checkboxes, text fields) in the document.
    
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
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY_INV, 11, 2)
    
    # Detect horizontal lines (potential underlines for text fields)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
    
    # Find contours for horizontal lines
    h_contours, _ = cv2.findContours(horizontal_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Detect checkboxes
    # Look for square contours
    checkbox_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    checkbox_mask = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, checkbox_kernel)
    
    # Find contours for potential checkboxes
    c_contours, _ = cv2.findContours(checkbox_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    form_fields = []
    
    # Process horizontal lines (potential text fields)
    for contour in h_contours:
        x, y, w, h = cv2.boundingRect(contour)
        # Filter based on size and aspect ratio
        if w > 50 and h < 5 and w / h > 10:  # Likely an underline
            form_fields.append({
                'type': 'text_field',
                'bbox': (x, y, w, h),
                'underline': True
            })
    
    # Process potential checkboxes
    for contour in c_contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = w / float(h) if h > 0 else 0
        
        # Filter based on size and aspect ratio
        if 10 < w < 50 and 10 < h < 50 and 0.8 < aspect_ratio < 1.2:  # Square-ish
            # Check if the checkbox is checked
            checkbox_roi = gray[y:y+h, x:x+w]
            is_checked = is_checkbox_checked(gray, (x, y, w, h))
            
            form_fields.append({
                'type': 'checkbox',
                'bbox': (x, y, w, h),
                'checked': is_checked
            })
    
    return form_fields


def segment_document(image: np.ndarray, document_type: Optional[DocumentType] = None) -> Dict[str, List]:
    """Segment the document into different regions (text, paragraphs, tables, form fields).
    
    Args:
        image: Input image
        document_type: Optional document type for specialized segmentation
        
    Returns:
        Dictionary containing lists of different region types
    """
    # Preprocess the image
    preprocessed = preprocess_for_ocr(image, document_type)
    
    # Detect different region types
    text_regions = detect_text_regions(preprocessed)
    paragraphs = detect_paragraphs(preprocessed)
    tables = detect_tables(preprocessed)
    form_fields = detect_form_fields(preprocessed)
    
    # Detect images/graphics (non-text regions)
    # This is a simplified approach - just find large contours that aren't text or tables
    if len(preprocessed.shape) == 3:
        gray = cv2.cvtColor(preprocessed, cv2.COLOR_BGR2GRAY)
    else:
        gray = preprocessed.copy()
    
    # Threshold the image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find all contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter for potential image regions
    image_regions = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        
        # Check if this region overlaps with text or tables
        is_overlapping = False
        for region in text_regions + tables:
            rx, ry, rw, rh = region
            if (x < rx + rw and x + w > rx and y < ry + rh and y + h > ry):
                is_overlapping = True
                break
        
        # If large enough and not overlapping, consider it an image region
        if area > 10000 and not is_overlapping:
            image_regions.append({
                'type': 'image',
                'bbox': (x, y, w, h)
            })
    
    # Convert text regions and other simple regions to dictionaries with type
    text_regions_dict = [{'type': 'text', 'bbox': region} for region in text_regions]
    paragraphs_dict = [{'type': 'paragraph', 'bbox': region} for region in paragraphs]
    tables_dict = [{'type': 'table', 'bbox': region} for region in tables]
    
    # Return all segments
    return {
        'text_regions': text_regions_dict,
        'paragraphs': paragraphs_dict,
        'tables': tables_dict,
        'form_fields': form_fields,
        'images': image_regions
    }


# ===== Image format handling =====

def convert_to_format(image: np.ndarray, format: ImageFormat) -> bytes:
    """Convert image to the specified format and return as bytes.
    
    Args:
        image: Input image
        format: Target image format
        
    Returns:
        Image data as bytes
    """
    # Set encoding parameters based on format
    if format == ImageFormat.JPEG:
        params = [cv2.IMWRITE_JPEG_QUALITY, 95]
        ext = '.jpg'
    elif format == ImageFormat.PNG:
        params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
        ext = '.png'
    elif format == ImageFormat.TIFF:
        params = [cv2.IMWRITE_TIFF_COMPRESSION, 5]
        ext = '.tiff'
    elif format == ImageFormat.BMP:
        params = []
        ext = '.bmp'
    else:
        # Default to PNG
        params = [cv2.IMWRITE_PNG_COMPRESSION, 9]
        ext = '.png'
    
    # Encode image to bytes
    success, buffer = cv2.imencode(ext, image, params)
    if not success:
        raise ServiceError(f"Failed to convert image to {format.name} format")
    
    return buffer.tobytes()


def save_image(image: np.ndarray, file_path: str, format: Optional[ImageFormat] = None) -> str:
    """Save image to a file.
    
    Args:
        image: Input image
        file_path: Path to save the image
        format: Optional image format (if not specified, inferred from file extension)
        
    Returns:
        Path to the saved file
        
    Raises:
        ServiceError: If the image cannot be saved
    """
    try:
        # If format is specified, convert to that format
        if format is not None:
            image_bytes = convert_to_format(image, format)
            with open(file_path, 'wb') as f:
                f.write(image_bytes)
        else:
            # Save directly using OpenCV
            cv2.imwrite(file_path, image)
        
        return file_path
    except Exception as e:
        raise ServiceError(f"Error saving image to {file_path}: {str(e)}")


def get_image_format(file_path: str) -> ImageFormat:
    """Determine image format from file path extension.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Image format enum
    """
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.jpg', '.jpeg']:
        return ImageFormat.JPEG
    elif ext == '.png':
        return ImageFormat.PNG
    elif ext in ['.tif', '.tiff']:
        return ImageFormat.TIFF
    elif ext == '.bmp':
        return ImageFormat.BMP
    elif ext == '.pdf':
        return ImageFormat.PDF
    else:
        # Default to JPEG
        return ImageFormat.JPEG


# ===== Image quality assessment =====

def assess_image_quality(image: np.ndarray) -> Dict[str, float]:
    """Assess the quality of the image for OCR processing.
    
    Args:
        image: Input image
        
    Returns:
        Dictionary of quality metrics
    """
    # Convert to grayscale if needed
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()
    
    # Calculate contrast (standard deviation of pixel values)
    contrast = np.std(gray) / 255.0
    
    # Calculate brightness (mean pixel value)
    brightness = np.mean(gray) / 255.0
    
    # Calculate sharpness (variance of Laplacian)
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    sharpness = np.var(laplacian) / 10000.0  # Normalize
    if sharpness > 1.0:
        sharpness = 1.0
    
    # Calculate noise level (approximation using local standard deviation)
    noise = 0.0
    block_size = 16
    for y in range(0, gray.shape[0], block_size):
        for x in range(0, gray.shape[1], block_size):
            block = gray[y:min(y+block_size, gray.shape[0]), 
                        x:min(x+block_size, gray.shape[1])]
            if block.size > 0:
                local_std = np.std(block)
                noise += local_std
    
    # Normalize noise
    if gray.size > 0:
        noise = 1.0 - (noise / (gray.size / (block_size**2) * 255.0))
        if noise < 0.0:
            noise = 0.0
        if noise > 1.0:
            noise = 1.0
    
    # Calculate resolution quality (based on image dimensions)
    height, width = gray.shape
    min_dim = min(height, width)
    resolution = min(1.0, min_dim / 1000.0)  # Normalize to 0-1
    
    # Calculate skew (using the deskew function)
    # Convert to binary
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find all non-zero points
    coords = np.column_stack(np.where(binary > 0))
    
    # Default skew value (perfect)
    skew = 1.0
    
    # If enough text is detected, calculate skew
    if len(coords) > 10:
        # Find rotated rectangle
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        
        # Adjust angle
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        
        # Convert angle to quality metric (0-1, where 1 is perfect)
        skew = 1.0 - min(1.0, abs(angle) / 45.0)
    
    # Return all metrics
    return {
        QualityMetrics.CONTRAST.value: contrast,
        QualityMetrics.BRIGHTNESS.value: brightness,
        QualityMetrics.SHARPNESS.value: sharpness,
        QualityMetrics.NOISE.value: noise,
        QualityMetrics.RESOLUTION.value: resolution,
        QualityMetrics.SKEW.value: skew
    }


def calculate_overall_quality(metrics: Dict[str, float]) -> float:
    """Calculate overall image quality score from individual metrics.
    
    Args:
        metrics: Dictionary of quality metrics
        
    Returns:
        Overall quality score (0-1)
    """
    # Define weights for each metric
    weights = {
        QualityMetrics.CONTRAST.value: 0.25,
        QualityMetrics.BRIGHTNESS.value: 0.15,
        QualityMetrics.SHARPNESS.value: 0.25,
        QualityMetrics.NOISE.value: 0.15,
        QualityMetrics.RESOLUTION.value: 0.10,
        QualityMetrics.SKEW.value: 0.10
    }
    
    # Calculate weighted sum
    weighted_sum = 0.0
    total_weight = 0.0
    
    for metric, value in metrics.items():
        if metric in weights:
            weighted_sum += value * weights[metric]
            total_weight += weights[metric]
    
    # Normalize
    if total_weight > 0:
        overall_quality = weighted_sum / total_weight
    else:
        overall_quality = 0.0
    
    return overall_quality


def is_suitable_for_ocr(image: np.ndarray) -> Tuple[bool, Dict[str, float]]:
    """Determine if the image is suitable for OCR processing.
    
    Args:
        image: Input image
        
    Returns:
        Tuple of (is_suitable, quality_metrics)
    """
    # Assess image quality
    metrics = assess_image_quality(image)
    
    # Calculate overall quality
    overall_quality = calculate_overall_quality(metrics)
    
    # Define threshold for OCR suitability
    threshold = 0.5  # Adjust as needed
    
    # Check if image is suitable
    is_suitable = overall_quality >= threshold
    
    return is_suitable, metrics


def suggest_enhancements(metrics: Dict[str, float]) -> List[str]:
    """Suggest image enhancements based on quality metrics.
    
    Args:
        metrics: Dictionary of quality metrics
        
    Returns:
        List of suggested enhancement operations
    """
    suggestions = []
    
    # Define thresholds for each metric
    thresholds = {
        QualityMetrics.CONTRAST.value: 0.4,
        QualityMetrics.BRIGHTNESS.value: 0.3,
        QualityMetrics.SHARPNESS.value: 0.4,
        QualityMetrics.NOISE.value: 0.6,
        QualityMetrics.RESOLUTION.value: 0.5,
        QualityMetrics.SKEW.value: 0.8
    }
    
    # Check each metric and suggest enhancements
    if metrics[QualityMetrics.CONTRAST.value] < thresholds[QualityMetrics.CONTRAST.value]:
        suggestions.append('enhance_contrast')
    
    # For brightness, check if too dark or too bright
    if metrics[QualityMetrics.BRIGHTNESS.value] < thresholds[QualityMetrics.BRIGHTNESS.value]:
        suggestions.append('increase_brightness')
    elif metrics[QualityMetrics.BRIGHTNESS.value] > 0.8:  # Too bright
        suggestions.append('decrease_brightness')
    
    if metrics[QualityMetrics.SHARPNESS.value] < thresholds[QualityMetrics.SHARPNESS.value]:
        suggestions.append('sharpen_image')
    
    if metrics[QualityMetrics.NOISE.value] < thresholds[QualityMetrics.NOISE.value]:
        suggestions.append('remove_noise')
    
    if metrics[QualityMetrics.RESOLUTION.value] < thresholds[QualityMetrics.RESOLUTION.value]:
        suggestions.append('increase_resolution')
    
    if metrics[QualityMetrics.SKEW.value] < thresholds[QualityMetrics.SKEW.value]:
        suggestions.append('deskew_image')
    
    return suggestions


# ===== Helper functions =====

def is_checkbox_checked(image: np.ndarray, bbox: Tuple[int, int, int, int]) -> bool:
    """Determine if a checkbox is checked.
    
    Args:
        image: Input grayscale image
        bbox: Bounding box of the checkbox (x, y, width, height)
        
    Returns:
        True if checkbox is checked, False otherwise
    """
    x, y, w, h = bbox
    
    # Extract the checkbox region
    checkbox = image[y:y+h, x:x+w]
    
    # Threshold to binary
    _, binary = cv2.threshold(checkbox, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Calculate the fill ratio (percentage of black pixels)
    fill_ratio = np.sum(binary == 255) / (w * h)
    
    # If more than 20% filled, consider it checked
    return fill_ratio > 0.2


def is_region_in_bounds(region: Tuple[int, int, int, int], image_shape: Tuple[int, int]) -> bool:
    """Check if a region is within the bounds of the image.
    
    Args:
        region: Region as (x, y, width, height)
        image_shape: Image shape as (height, width)
        
    Returns:
        True if region is within bounds, False otherwise
    """
    x, y, w, h = region
    height, width = image_shape
    
    return (x >= 0 and y >= 0 and 
            x + w <= width and y + h <= height and 
            w > 0 and h > 0)


def extract_region(image: np.ndarray, region: Tuple[int, int, int, int]) -> np.ndarray:
    """Extract a region from an image.
    
    Args:
        image: Input image
        region: Region as (x, y, width, height)
        
    Returns:
        Extracted region
    """
    x, y, w, h = region
    
    # Ensure region is within bounds
    height, width = image.shape[:2]
    x = max(0, x)
    y = max(0, y)
    w = min(width - x, w)
    h = min(height - y, h)
    
    # Extract region
    return image[y:y+h, x:x+w]


def preprocess_for_ocr(image: np.ndarray, document_type: Optional[DocumentType] = None) -> np.ndarray:
    """Apply standard preprocessing pipeline for OCR.
    
    Args:
        image: Input image
        document_type: Optional document type for specialized preprocessing
        
    Returns:
        Preprocessed image
    """
    # Normalize size
    resized = normalize_size(image)
    
    # Convert to grayscale
    if len(resized.shape) == 3:
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    else:
        gray = resized.copy()
    
    # Enhance contrast
    enhanced = enhance_contrast(gray)
    
    # Remove noise
    denoised = remove_noise(enhanced, method='gaussian')
    
    # Apply document type-specific preprocessing if specified
    if document_type == DocumentType.APPLICATION:
        # For application forms, use adaptive thresholding
        binary = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)
        return binary
    elif document_type == DocumentType.INVOICE:
        # For invoices, use Otsu's thresholding
        _, binary = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    elif document_type == DocumentType.ID_DOCUMENT:
        # For ID documents, use sharper image without binarization
        sharpened = sharpen_image(denoised)
        return sharpened
    else:
        # Default preprocessing
        # Deskew the image
        deskewed = deskew_image(denoised)
        return deskewed


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
    
    # Define highlight color (green)
    color = (0, 255, 0)  # BGR
    
    # Draw rectangles around each field
    for field in field_locations:
        x, y, w, h = field.bbox
        cv2.rectangle(highlighted, (x, y), (x + w, y + h), color, 2)
        
        # Add label if available
        if field.label:
            cv2.putText(highlighted, field.label, (x, y - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
    
    return highlighted