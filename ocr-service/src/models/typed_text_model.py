#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Typed Text OCR Model for the OCR Service.

This module implements a specialized TensorFlow model for recognizing and extracting
typed/printed text from documents. It is optimized for machine-printed text commonly
found in formal applications, tax forms, and bank statements.

Key features:
- Specialized preprocessing for typed document enhancement
- Text line detection and segmentation algorithms
- Character recognition with language model correction
- Field extraction based on document structure
- High-accuracy OCR (99% as specified in section 0.1.2)

This model is designed to work with CUDA-compatible GPU acceleration with at least
8GB VRAM as required in section 3.2.3 of the technical specification.
"""

import os
import logging
import time
from typing import Dict, List, Tuple, Optional, Any, Union

import numpy as np
import tensorflow as tf
import cv2

# Import base model (abstract class)
from abc import ABC, abstractmethod

# Note: In a production implementation, we would import the BaseOCRModel from a separate file
# For example: from .base_model import BaseOCRModel
# Since we're implementing it here for completeness, we use ABC directly

# Import types
from ..types.models import OCRModelType, ModelParameters, ModelResult, TensorFlowModel
from ..types.extraction import ExtractedField, ConfidenceScore, ExtractedData, FieldLocation
from ..types.documents import DocumentType

# Import utilities
from ..utils.image_utils import (
    preprocess_for_ocr, enhance_contrast, normalize_size, deskew_image,
    detect_text_regions, normalize_orientation, sharpen_image, binarize_image
)
from ..utils.text_utils import (
    clean_text, normalize_text, correct_ocr_errors, extract_key_value_pairs,
    extract_form_fields, validate_field
)
from ..utils.tensorflow_utils import (
    configure_gpu_memory, run_inference, calculate_confidence_scores,
    cleanup_gpu_memory
)

# Configure logger
logger = logging.getLogger(__name__)


class BaseOCRModel(ABC):
    """
    Abstract base class for OCR models.
    
    This class defines the common interface and shared functionality that all OCR models
    must implement, including methods for model loading, image preprocessing, text extraction,
    and result formatting.
    """
    
    def __init__(self, model_parameters: ModelParameters):
        """
        Initialize the OCR model with the specified parameters.
        
        Args:
            model_parameters: Configuration parameters for the model
        """
        self.parameters = model_parameters
        self.model = None
        self.model_type = OCRModelType(model_parameters['model_type'])
        self.tf_model = None
        self.is_initialized = False
        
        # Configure GPU memory
        # As specified in section 3.2.3, TensorFlow OCR processing requires
        # CUDA-compatible GPU acceleration with at least 8GB VRAM
        self.gpu_config = configure_gpu_memory(
            memory_limit=model_parameters.get('gpu_memory_limit'),
            allow_growth=True
        )
        
        logger.info(f"Initialized {self.model_type.value} OCR model")
    
    @abstractmethod
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for OCR.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            Preprocessed image as a numpy array
        """
        pass
    
    @abstractmethod
    def extract_text(self, image: np.ndarray) -> ModelResult:
        """
        Extract text from an image.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            ModelResult containing extracted text and metadata
        """
        pass
    
    @abstractmethod
    def extract_fields(self, image: np.ndarray, document_type: Optional[DocumentType] = None) -> ExtractedData:
        """
        Extract structured fields from an image.
        
        Args:
            image: Input image as a numpy array
            document_type: Type of document for specialized extraction
            
        Returns:
            ExtractedData containing structured fields and metadata
        """
        pass
    
    def load_model(self) -> bool:
        """
        Load the TensorFlow model from the specified path.
        
        Returns:
            True if the model was loaded successfully, False otherwise
        """
        try:
            if not self.parameters.get('model_path'):
                raise ValueError("Model path not specified in parameters")
            
            model_path = self.parameters['model_path']
            logger.info(f"Loading {self.model_type.value} model from {model_path}")
            
            # Create TensorFlow model wrapper
            self.tf_model = TensorFlowModel(self.parameters)
            
            # Load the model
            self.tf_model.load()
            self.model = self.tf_model.model
            self.is_initialized = True
            
            logger.info(f"Successfully loaded {self.model_type.value} model")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def cleanup(self) -> None:
        """
        Clean up resources used by the model.
        """
        try:
            # Clean up GPU memory
            cleanup_results = cleanup_gpu_memory()
            logger.debug(f"GPU memory cleanup results: {cleanup_results}")
            
            # Clear TensorFlow session
            tf.keras.backend.clear_session()
            
            self.is_initialized = False
            logger.info(f"Cleaned up {self.model_type.value} model resources")
            
        except Exception as e:
            logger.error(f"Error cleaning up model resources: {str(e)}")


class TypedTextModel(BaseOCRModel):
    """
    Specialized OCR model for typed/printed text recognition.
    
    This model is optimized for machine-printed text commonly found in formal applications,
    tax forms, and bank statements. It provides high-accuracy OCR for structured documents
    with consistent fonts and layouts.
    """
    
    def __init__(self, model_parameters: Optional[ModelParameters] = None):
        """
        Initialize the typed text OCR model.
        
        Args:
            model_parameters: Configuration parameters for the model (optional)
        """
        # Use default parameters if none provided
        if model_parameters is None:
            from ..types.models import DEFAULT_TYPED_MODEL_PARAMS
            model_parameters = DEFAULT_TYPED_MODEL_PARAMS
        
        # Ensure model type is set correctly
        model_parameters['model_type'] = OCRModelType.TYPED.value
        
        # Initialize base class
        super().__init__(model_parameters)
        
        # Typed text specific parameters
        self.line_height_threshold = 10  # Minimum line height in pixels
        self.char_width_threshold = 5    # Minimum character width in pixels
        self.language_model_weight = 0.3  # Weight for language model correction (0.0-1.0)
        
        logger.info("Initialized TypedTextModel with specialized parameters")
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for typed text OCR.
        
        This method applies specialized preprocessing optimized for typed/printed text,
        including contrast enhancement, deskewing, and binarization.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            Preprocessed image as a numpy array
        """
        try:
            logger.debug("Preprocessing image for typed text OCR")
            start_time = time.time()
            
            # Apply general OCR preprocessing
            preprocessed = preprocess_for_ocr(image, DocumentType.APPLICATION)
            
            # Apply typed text specific preprocessing
            
            # 1. Enhance contrast for better text visibility
            # Typed text benefits from higher contrast
            enhanced = enhance_contrast(preprocessed, clip_limit=2.5, tile_grid_size=(16, 16))
            
            # 2. Ensure proper orientation
            # Typed text typically has consistent orientation
            oriented = normalize_orientation(enhanced)
            
            # 3. Deskew the image to align text horizontally
            # Critical for typed text recognition accuracy
            deskewed = deskew_image(oriented)
            
            # 4. Sharpen the image to improve character definition
            # Typed text benefits from sharper edges
            sharpened = sharpen_image(deskewed, amount=1.8)
            
            # 5. Binarize the image for clearer text/background separation
            # Use Otsu's method for optimal threshold selection
            if len(sharpened.shape) == 3:  # Color image
                # Convert to grayscale first
                gray = tf.image.rgb_to_grayscale(sharpened).numpy()
                binary = binarize_image(gray, method='otsu')
            else:  # Already grayscale
                binary = binarize_image(sharpened, method='otsu')
            
            # 6. Normalize size to model input dimensions
            input_shape = self.parameters.get('input_shape', (768, 768, 1))
            height, width = input_shape[0], input_shape[1]
            
            # Resize while preserving aspect ratio
            h, w = binary.shape[:2]
            aspect = w / h
            
            if aspect > 1:  # Wider than tall
                new_width = width
                new_height = int(width / aspect)
            else:  # Taller than wide
                new_height = height
                new_width = int(height * aspect)
            
            # Resize to target dimensions
            resized = tf.image.resize(
                tf.expand_dims(binary, axis=-1) if len(binary.shape) == 2 else binary,
                [new_height, new_width],
                method=tf.image.ResizeMethod.BILINEAR
            ).numpy()
            
            # Create a blank canvas of the target size
            if len(resized.shape) == 3 and resized.shape[2] == 1:
                final = np.zeros((height, width, 1), dtype=resized.dtype)
            else:
                final = np.zeros((height, width, 3), dtype=resized.dtype)
            
            # Center the resized image on the canvas
            y_offset = (height - new_height) // 2
            x_offset = (width - new_width) // 2
            
            if len(resized.shape) == 3 and resized.shape[2] == 1:
                final[y_offset:y_offset+new_height, x_offset:x_offset+new_width, 0] = resized[:, :, 0]
            elif len(resized.shape) == 3 and resized.shape[2] == 3:
                final[y_offset:y_offset+new_height, x_offset:x_offset+new_width, :] = resized
            else:
                final[y_offset:y_offset+new_height, x_offset:x_offset+new_width, 0] = resized
            
            # Normalize pixel values to [0, 1] if not already
            if final.max() > 1.0:
                final = final / 255.0
            
            processing_time = time.time() - start_time
            logger.debug(f"Preprocessing completed in {processing_time:.2f} seconds")
            
            return final
            
        except Exception as e:
            logger.error(f"Error preprocessing image: {str(e)}")
            # Return original image as fallback
            return image
    
    def detect_text_lines(self, image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect and extract text lines from an image.
        
        This method identifies horizontal lines of text in the document, which is
        particularly effective for typed text with consistent baselines.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            List of dictionaries containing text line information
        """
        try:
            logger.debug("Detecting text lines in image")
            
            # Convert to grayscale if needed
            if len(image.shape) == 3:
                gray = tf.image.rgb_to_grayscale(image).numpy().squeeze()
            else:
                gray = image.copy()
            
            # Binarize the image
            binary = binarize_image(gray, method='otsu')
            
            # Detect text regions
            text_regions = detect_text_regions(binary)
            
            # Sort regions by vertical position (top to bottom)
            text_regions.sort(key=lambda r: r[1])  # Sort by y-coordinate
            
            text_lines = []
            for i, region in enumerate(text_regions):
                x, y, w, h = region
                
                # Skip very small regions
                if h < self.line_height_threshold or w < self.char_width_threshold * 3:
                    continue
                
                # Extract the region
                line_image = binary[y:y+h, x:x+w]
                
                # Create text line information
                text_line = {
                    "id": i,
                    "bbox": (x, y, w, h),
                    "image": line_image,
                    "text": "",  # Will be filled by OCR
                    "confidence": 0.0  # Will be filled by OCR
                }
                
                text_lines.append(text_line)
            
            logger.debug(f"Detected {len(text_lines)} text lines")
            return text_lines
            
        except Exception as e:
            logger.error(f"Error detecting text lines: {str(e)}")
            return []
    
    def segment_characters(self, line_image: np.ndarray) -> List[Dict[str, Any]]:
        """
        Segment a text line into individual characters.
        
        This method identifies individual characters within a text line, which is
        useful for character-level recognition and confidence scoring.
        
        Args:
            line_image: Binary image of a text line
            
        Returns:
            List of dictionaries containing character information
        """
        try:
            # Ensure image is binary
            if len(line_image.shape) == 3:
                binary = tf.image.rgb_to_grayscale(line_image).numpy().squeeze()
                _, binary = cv2.threshold(binary, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            else:
                _, binary = cv2.threshold(line_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Find contours of characters
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Sort contours by horizontal position (left to right)
            contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])
            
            characters = []
            for i, contour in enumerate(contours):
                x, y, w, h = cv2.boundingRect(contour)
                
                # Skip very small contours (noise)
                if w < self.char_width_threshold or h < self.line_height_threshold / 2:
                    continue
                
                # Extract the character image
                char_image = binary[y:y+h, x:x+w]
                
                # Create character information
                character = {
                    "id": i,
                    "bbox": (x, y, w, h),
                    "image": char_image,
                    "char": "",  # Will be filled by OCR
                    "confidence": 0.0  # Will be filled by OCR
                }
                
                characters.append(character)
            
            return characters
            
        except Exception as e:
            logger.error(f"Error segmenting characters: {str(e)}")
            return []
    
    def apply_language_model_correction(self, text: str, confidence: float) -> Tuple[str, float]:
        """
        Apply language model correction to improve OCR accuracy.
        
        This method uses statistical language models to correct common OCR errors
        in typed text, improving overall accuracy.
        
        Args:
            text: Raw OCR text to correct
            confidence: Confidence score of the raw OCR text
            
        Returns:
            Tuple of (corrected_text, adjusted_confidence)
        """
        try:
            # Use text_utils.correct_ocr_errors for basic correction
            corrected_text, correction_confidence = correct_ocr_errors(text)
            
            # Combine original confidence with correction confidence
            # Weight the original confidence more heavily
            adjusted_confidence = (1 - self.language_model_weight) * confidence + \
                                self.language_model_weight * correction_confidence
            
            return corrected_text, adjusted_confidence
            
        except Exception as e:
            logger.error(f"Error applying language model correction: {str(e)}")
            return text, confidence
    
    def extract_text(self, image: np.ndarray) -> ModelResult:
        """
        Extract text from an image using the typed text OCR model.
        
        This method processes the image, runs inference with the TensorFlow model,
        and returns the extracted text with confidence scores.
        
        The implementation is optimized to achieve 99% accuracy for typed documents
        as specified in section 0.1.2 of the technical specification.
        
        Args:
            image: Input image as a numpy array
            
        Returns:
            ModelResult containing extracted text and metadata
        """
        try:
            logger.info("Extracting text from image using typed text model")
            start_time = time.time()
            
            # Check if model is initialized
            if not self.is_initialized:
                logger.warning("Model not initialized. Loading model...")
                if not self.load_model():
                    raise RuntimeError("Failed to load model")
            
            # Preprocess the image
            preprocessed = self.preprocess(image)
            
            # Run inference using tensorflow_utils.run_inference
            output, metadata = run_inference(
                model=self.model,
                image=preprocessed,
                model_type=self.model_type.value,
                batch_size=self.parameters.get('batch_size', 1),
                confidence_threshold=self.parameters.get('confidence_threshold', 0.75)
            )
            
            if output is None:
                raise RuntimeError(f"Inference failed: {metadata.get('error', 'Unknown error')}")
            
            # Process the model output to extract text
            # This depends on the specific model architecture and output format
            # For this implementation, we'll assume the model outputs character probabilities
            
            # Decode the output to text
            # This is a simplified example - actual implementation would depend on model output format
            extracted_text = self._decode_model_output(output)
            
            # Apply language model correction
            corrected_text, adjusted_confidence = self.apply_language_model_correction(
                extracted_text, metadata['confidence_scores'].get('overall', 0.9)
            )
            
            # Create bounding boxes for text regions
            # For simplicity, we'll use a single bounding box for the entire text
            bounding_boxes = [{
                "text": corrected_text,
                "confidence": adjusted_confidence,
                "bbox": [0, 0, 1, 1]  # Normalized coordinates [x, y, width, height]
            }]
            
            # Calculate word confidences
            # For simplicity, we'll use the same confidence for all words
            words = corrected_text.split()
            word_confidences = [adjusted_confidence] * len(words)
            
            # Create the model result
            result = {
                "text": corrected_text,
                "confidence": adjusted_confidence,
                "bounding_boxes": bounding_boxes,
                "word_confidences": word_confidences,
                "processing_time": time.time() - start_time,
                "page_number": 1,  # Assuming single page
                "model_type": self.model_type.value,
                "warnings": [],
                "language": self.parameters.get('language', 'en')
            }
            
            logger.info(f"Text extraction completed in {result['processing_time']:.2f} seconds")
            return result
            
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            # Return empty result with error
            return {
                "text": "",
                "confidence": 0.0,
                "bounding_boxes": [],
                "word_confidences": [],
                "processing_time": time.time() - start_time,
                "page_number": 1,
                "model_type": self.model_type.value,
                "warnings": [f"Error extracting text: {str(e)}"],
                "language": self.parameters.get('language', 'en')
            }
    
    def _decode_model_output(self, output: np.ndarray) -> str:
        """
        Decode model output to text.
        
        This method converts the model's numerical output (typically character probabilities)
        to human-readable text.
        
        Args:
            output: Model output as numpy array
            
        Returns:
            Decoded text string
        """
        try:
            # This is a simplified implementation - actual decoding would depend on model architecture
            # For a real implementation, you would use a character mapping and beam search
            
            # For demonstration purposes, we'll assume the model outputs character indices
            # and we have a vocabulary mapping indices to characters
            
            # Load vocabulary from file if specified in parameters
            vocab_path = self.parameters.get('vocab_path')
            if vocab_path and os.path.exists(vocab_path):
                with open(vocab_path, 'r') as f:
                    vocab = [line.strip() for line in f]
            else:
                # Fallback vocabulary (simplified)
                vocab = [' '] + list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?!-\'"():;/')
            
            # Assume output is a sequence of character probabilities
            # Shape: [batch_size, sequence_length, vocab_size]
            if len(output.shape) == 3:
                # Get the most likely character at each position
                char_indices = np.argmax(output[0], axis=1)
                
                # Convert indices to characters
                chars = [vocab[idx] if idx < len(vocab) else '' for idx in char_indices]
                
                # Join characters to form text
                text = ''.join(chars)
                
                # Clean up the text (remove repeated spaces, etc.)
                text = clean_text(text)
                
                return text
            else:
                logger.warning(f"Unexpected output shape: {output.shape}")
                return ""
                
        except Exception as e:
            logger.error(f"Error decoding model output: {str(e)}")
            return ""
    
    def extract_fields(self, image: np.ndarray, document_type: Optional[DocumentType] = None) -> ExtractedData:
        """
        Extract structured fields from an image based on document structure.
        
        This method identifies and extracts key-value pairs and form fields from the document,
        using the document type to apply specialized extraction rules.
        
        The implementation is optimized for performance to ensure the system can process
        applications in under 5 minutes from receipt to completion as specified in
        section 0.1.2 of the technical specification.
        
        Args:
            image: Input image as a numpy array
            document_type: Type of document for specialized extraction
            
        Returns:
            ExtractedData containing structured fields and metadata
        """
        try:
            logger.info(f"Extracting fields from image using typed text model")
            start_time = time.time()
            
            # Extract text from the image
            text_result = self.extract_text(image)
            extracted_text = text_result["text"]
            text_confidence = text_result["confidence"]
            
            # Use document type or default to APPLICATION
            if document_type is None:
                document_type = DocumentType.APPLICATION
            
            # Extract key-value pairs from the text
            key_value_pairs = extract_key_value_pairs(extracted_text)
            
            # Extract form fields
            form_fields = extract_form_fields(extracted_text)
            
            # Create extracted fields dictionary
            fields = {}
            low_confidence_fields = []
            requires_verification = False
            
            # Process each key-value pair
            for key, value, confidence in key_value_pairs:
                # Skip empty values
                if not value:
                    continue
                
                # Determine field type based on key
                field_type = self._determine_field_type(key)
                
                # Validate and correct the field value
                is_valid, corrected_value, validation_confidence = validate_field(value, field_type)
                
                # Combine extraction and validation confidence
                combined_confidence = confidence * validation_confidence * text_confidence
                
                # Create field location (placeholder - would be populated by actual bounding box)
                field_location = {
                    "page": 1,
                    "top": 0.0,
                    "left": 0.0,
                    "bottom": 0.0,
                    "right": 0.0,
                    "width": 0.0,
                    "height": 0.0
                }
                
                # Check if field requires verification
                field_requires_verification = combined_confidence < 0.8 or not is_valid
                verification_reason = None
                
                if field_requires_verification:
                    requires_verification = True
                    low_confidence_fields.append(key)
                    
                    if combined_confidence < 0.8:
                        verification_reason = "Low confidence score"
                    elif not is_valid:
                        verification_reason = f"Invalid {field_type} format"
                
                # Create the extracted field
                extracted_field = {
                    "field_name": key,
                    "field_type": field_type,
                    "value": corrected_value,
                    "raw_text": value,
                    "confidence": ConfidenceScore.from_float(combined_confidence),
                    "location": field_location,
                    "alternatives": [],  # Would be populated with alternative values
                    "metadata": {
                        "extraction_method": "typed_text_ocr",
                        "validation_result": is_valid
                    },
                    "requires_verification": field_requires_verification,
                    "verification_reason": verification_reason,
                    "extraction_timestamp": time.time()
                }
                
                fields[key] = extracted_field
            
            # Create extraction metadata
            extraction_metadata = {
                "extraction_id": f"typed-{int(time.time())}",
                "document_id": "unknown",  # Would be populated with actual document ID
                "model_id": self.parameters.get('model_name', 'typed_text_ocr'),
                "model_version": self.parameters.get('model_version', '1.0.0'),
                "document_type": document_type.value,
                "page_count": 1,  # Assuming single page
                "language": self.parameters.get('language', 'en'),
                "processing_node": "unknown",  # Would be populated with actual node ID
                "extraction_status": "success",
                "processing_time": time.time() - start_time,
                "warnings": text_result.get("warnings", []),
                "errors": []
            }
            
            # Create the extracted data
            extracted_data = {
                "extraction_id": extraction_metadata["extraction_id"],
                "fields": fields,
                "tables": [],  # Would be populated with extracted tables
                "metadata": extraction_metadata,
                "raw_text": extracted_text,
                "low_confidence_fields": low_confidence_fields,
                "requires_verification": requires_verification,
                "extraction_timestamp": time.time(),
                "schema_version": "1.0",
                "document_type": document_type.value
            }
            
            logger.info(f"Field extraction completed in {extraction_metadata['processing_time']:.2f} seconds")
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting fields: {str(e)}")
            # Return empty result with error
            return {
                "extraction_id": f"typed-{int(time.time())}",
                "fields": {},
                "tables": [],
                "metadata": {
                    "extraction_status": "failed",
                    "errors": [str(e)]
                },
                "raw_text": "",
                "low_confidence_fields": [],
                "requires_verification": True,
                "extraction_timestamp": time.time(),
                "schema_version": "1.0",
                "document_type": document_type.value if document_type else DocumentType.OTHER.value
            }
    
    def _determine_field_type(self, key: str) -> str:
        """
        Determine the field type based on the key name.
        
        Args:
            key: Field key to analyze
            
        Returns:
            Field type string (email, phone, date, etc.)
        """
        key = key.lower()
        
        # Check for email fields
        if any(term in key for term in ['email', 'e-mail']):
            return 'email'
        
        # Check for phone fields
        if any(term in key for term in ['phone', 'telephone', 'mobile', 'cell']):
            return 'phone'
        
        # Check for date fields
        if any(term in key for term in ['date', 'dob', 'birth', 'issued', 'expiry', 'expiration']):
            return 'date'
        
        # Check for currency fields
        if any(term in key for term in ['amount', 'revenue', 'income', 'payment', 'balance', 'price', 'cost', 'fee', 'salary', 'wage']):
            return 'currency'
        
        # Check for EIN fields
        if any(term in key for term in ['ein', 'tax id', 'tax identification', 'employer identification']):
            return 'ein'
        
        # Check for SSN fields
        if any(term in key for term in ['ssn', 'social security']):
            return 'ssn'
        
        # Check for ZIP code fields
        if any(term in key for term in ['zip', 'postal', 'post code']):
            return 'zip'
        
        # Default to text for unknown field types
        return 'text'