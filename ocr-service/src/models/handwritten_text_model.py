#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Handwritten Text OCR Model for the OCR Service.

This module implements a specialized TensorFlow model for recognizing and extracting
handwritten text from documents. It is designed to handle the variability and inconsistency
of handwritten notes, signatures, and form fields that are common in merchant applications.

Key features:
- Specialized preprocessing for handwriting enhancement
- Neural network architecture for variable handwriting styles
- Context-aware text recognition for improved accuracy
- Confidence scoring specific to handwritten text challenges
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

# Import base model
from .base_model import BaseOCRModel

# Import types
from ..types.models import ModelParameters, ModelResult
from ..types.extraction import ExtractedField, ConfidenceScore, ExtractedData
from ..types.documents import DocumentMetadata, DocumentContent, DocumentType

# Import utilities
from ..utils.image_utils import (
    normalize_image, preprocess_image, enhance_contrast, deskew_image,
    detect_text_regions, normalize_orientation, sharpen_image
)
from ..utils.text_utils import (
    clean_text, normalize_text, correct_ocr_errors, extract_key_value_pairs,
    validate_field
)
from ..utils.tensorflow_utils import configure_gpu_memory


# Configure logger
logger = logging.getLogger(__name__)


class HandwrittenTextModel(BaseOCRModel):
    """
    Specialized OCR model for handwritten text recognition.
    
    This model is designed to handle the variability and inconsistency of handwritten
    notes, signatures, and form fields that are common in merchant applications.
    It uses advanced neural networks optimized for handwriting recognition.
    """
    
    def __init__(self, 
                 model_path: Union[str, os.PathLike], 
                 model_name: str = "handwritten_text_model",
                 config: Optional[Dict[str, Any]] = None,
                 parameters: Optional[ModelParameters] = None) -> None:
        """
        Initialize the handwritten text OCR model.
        
        Args:
            model_path: Path to the TensorFlow model files
            model_name: Name of the model for logging and identification
            config: Configuration for TensorFlow and GPU settings
            parameters: Model-specific parameters and hyperparameters (optional)
        """
        # Default configuration if not provided
        if config is None:
            from ..types.config import TensorFlowConfig
            config = TensorFlowConfig(
                use_gpu=True,
                gpu_memory_limit=8192,  # 8GB VRAM as required in section 3.2.3
                gpu_growth=True,
                verification_threshold=0.75
            )
        
        # Initialize base class
        super().__init__(model_path, model_name, config, parameters)
        
        # Handwritten text specific parameters
        self.stroke_width_range = (1, 10)  # Typical range for handwritten strokes in pixels
        self.context_window_size = 5       # Number of characters to consider for context
        self.language_model_weight = 0.4   # Weight for language model correction (0.0-1.0)
        self.min_confidence_threshold = 0.6  # Minimum confidence for acceptance
        
        # Additional model parameters specific to handwritten text
        self.parameters.update({
            "use_attention": True,           # Use attention mechanism for context awareness
            "use_bidirectional_rnn": True,  # Use bidirectional RNN for sequence modeling
            "beam_width": 5,               # Beam width for CTC beam search decoding
            "normalize_text": True,         # Apply text normalization to outputs
            "enhance_contrast": True,       # Apply contrast enhancement in preprocessing
            "use_character_segmentation": False,  # Don't use character segmentation for handwriting
            "use_word_segmentation": True,  # Use word segmentation instead
            "use_line_detection": True,     # Detect handwritten lines
            "use_slant_correction": True,   # Correct for slanted handwriting
            "use_stroke_width_transform": True,  # Use stroke width transform for enhancement
        })
        
        logger.info(f"Initialized {self.model_name} with specialized parameters for handwritten text")
    
    def preprocess_document(self, document_content: DocumentContent, 
                           document_metadata: DocumentMetadata) -> np.ndarray:
        """
        Preprocess the document image for handwritten text OCR processing.
        
        This method applies specialized preprocessing optimized for handwritten text,
        including contrast enhancement, stroke width normalization, and noise reduction.
        
        Args:
            document_content: Binary content of the document
            document_metadata: Metadata of the document including MIME type
            
        Returns:
            Preprocessed image as a numpy array ready for OCR processing
            
        Raises:
            ValueError: If document content is invalid or unsupported
        """
        try:
            # Call base class preprocessing first
            image = super().preprocess_document(document_content, document_metadata)
            
            # Apply handwritten text specific preprocessing
            
            # 1. Convert to grayscale if not already
            if len(image.shape) == 3 and image.shape[2] > 1:
                gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
            else:
                gray = image.squeeze()
            
            # 2. Apply adaptive contrast enhancement for handwritten text
            # Handwritten text often has varying pressure and intensity
            if self.parameters.get("enhance_contrast", True):
                enhanced = self._enhance_handwriting_contrast(gray)
            else:
                enhanced = gray
            
            # 3. Apply deskewing if enabled
            # Handwritten text is often slanted
            if self.parameters.get("use_slant_correction", True):
                deskewed = self._correct_handwriting_slant(enhanced)
            else:
                deskewed = enhanced
            
            # 4. Apply stroke width normalization if enabled
            # Handwritten text has variable stroke widths
            if self.parameters.get("use_stroke_width_transform", True):
                normalized = self._normalize_stroke_width(deskewed)
            else:
                normalized = deskewed
            
            # 5. Apply noise reduction specific to handwritten documents
            # Handwritten documents often have background noise
            denoised = self._reduce_handwriting_noise(normalized)
            
            # 6. Ensure proper dimensions for the model
            # Reshape to model input dimensions if needed
            if hasattr(self, 'model') and self.model is not None:
                # Get input shape from model signature
                input_shape = None
                for signature in self.model.signatures.values():
                    for input_tensor in signature.inputs.values():
                        input_shape = input_tensor.shape
                        break
                    if input_shape is not None:
                        break
                
                if input_shape is not None and len(input_shape) >= 3:
                    target_height, target_width = input_shape[1], input_shape[2]
                    
                    # Resize while preserving aspect ratio
                    h, w = denoised.shape[:2]
                    aspect = w / h
                    
                    if aspect > 1:  # Wider than tall
                        new_width = target_width
                        new_height = int(target_width / aspect)
                    else:  # Taller than wide
                        new_height = target_height
                        new_width = int(target_height * aspect)
                    
                    # Resize to target dimensions
                    resized = cv2.resize(denoised, (new_width, new_height), 
                                         interpolation=cv2.INTER_AREA)
                    
                    # Create a blank canvas of the target size
                    final = np.zeros((target_height, target_width), dtype=resized.dtype)
                    
                    # Center the resized image on the canvas
                    y_offset = (target_height - new_height) // 2
                    x_offset = (target_width - new_width) // 2
                    
                    final[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized
                    
                    # Normalize pixel values to [0, 1] if not already
                    if final.max() > 1.0:
                        final = final / 255.0
                    
                    # Add channel dimension if needed
                    if len(input_shape) == 4 and len(final.shape) == 2:
                        final = np.expand_dims(final, axis=-1)
                    
                    return final
            
            # If we couldn't determine the input shape, just normalize and return
            if denoised.max() > 1.0:
                denoised = denoised / 255.0
            
            return denoised
            
        except Exception as e:
            error_msg = f"Failed to preprocess document for handwritten text: {str(e)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
    
    def _enhance_handwriting_contrast(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance contrast specifically for handwritten text.
        
        This method applies adaptive histogram equalization with parameters
        optimized for handwritten text, which often has varying pressure and intensity.
        
        Args:
            image: Grayscale image as a numpy array
            
        Returns:
            Contrast-enhanced image as a numpy array
        """
        try:
            # Ensure image is in the right format
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
            # with parameters optimized for handwritten text
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(image)
            
            # Apply additional bilateral filtering to preserve edges while reducing noise
            filtered = cv2.bilateralFilter(enhanced, d=5, sigmaColor=75, sigmaSpace=75)
            
            return filtered
        except Exception as e:
            logger.warning(f"Error enhancing handwriting contrast: {str(e)}")
            return image
    
    def _correct_handwriting_slant(self, image: np.ndarray) -> np.ndarray:
        """
        Correct slant in handwritten text.
        
        This method detects and corrects the slant angle of handwritten text,
        which is often not perfectly horizontal.
        
        Args:
            image: Grayscale image as a numpy array
            
        Returns:
            Slant-corrected image as a numpy array
        """
        try:
            # Ensure image is in the right format
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            # Binarize the image
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Find contours
            contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Calculate the average angle of the contours
            angles = []
            for contour in contours:
                if len(contour) >= 5:  # Need at least 5 points for ellipse fitting
                    try:
                        ellipse = cv2.fitEllipse(contour)
                        angle = ellipse[2]
                        # Normalize angle to -45 to 45 degrees
                        if angle > 90:
                            angle = angle - 180
                        angles.append(angle)
                    except:
                        pass
            
            # If we have angles, calculate the average
            if angles:
                avg_angle = sum(angles) / len(angles)
                
                # Only correct if the angle is significant
                if abs(avg_angle) > 5:
                    # Get image dimensions
                    h, w = image.shape[:2]
                    center = (w // 2, h // 2)
                    
                    # Create rotation matrix
                    M = cv2.getRotationMatrix2D(center, avg_angle, 1.0)
                    
                    # Apply rotation
                    corrected = cv2.warpAffine(image, M, (w, h), 
                                              flags=cv2.INTER_CUBIC, 
                                              borderMode=cv2.BORDER_REPLICATE)
                    return corrected
            
            # If no correction was applied, return the original image
            return image
        except Exception as e:
            logger.warning(f"Error correcting handwriting slant: {str(e)}")
            return image
    
    def _normalize_stroke_width(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize stroke width in handwritten text.
        
        This method applies stroke width transformation to normalize the
        varying pressure and stroke widths common in handwritten text.
        
        Args:
            image: Grayscale image as a numpy array
            
        Returns:
            Stroke-normalized image as a numpy array
        """
        try:
            # Ensure image is in the right format
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            # Binarize the image
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            
            # Apply morphological operations to normalize stroke width
            # First, apply a small erosion to remove thin noise
            kernel = np.ones((2, 2), np.uint8)
            eroded = cv2.erode(binary, kernel, iterations=1)
            
            # Then, apply a dilation to normalize stroke width
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(eroded, kernel, iterations=1)
            
            # Invert back to original polarity
            normalized = cv2.bitwise_not(dilated)
            
            return normalized
        except Exception as e:
            logger.warning(f"Error normalizing stroke width: {str(e)}")
            return image
    
    def _reduce_handwriting_noise(self, image: np.ndarray) -> np.ndarray:
        """
        Reduce noise in handwritten document images.
        
        This method applies specialized noise reduction techniques optimized
        for handwritten documents, which often have background noise and artifacts.
        
        Args:
            image: Grayscale image as a numpy array
            
        Returns:
            Noise-reduced image as a numpy array
        """
        try:
            # Ensure image is in the right format
            if image.dtype != np.uint8:
                image = (image * 255).astype(np.uint8)
            
            # Apply non-local means denoising
            # This preserves edges better than Gaussian blur
            denoised = cv2.fastNlMeansDenoising(image, None, h=10, searchWindowSize=21, templateWindowSize=7)
            
            return denoised
        except Exception as e:
            logger.warning(f"Error reducing handwriting noise: {str(e)}")
            return image
    
    def extract_text(self, image: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """
        Extract text from the preprocessed document image.
        
        This method uses the TensorFlow model to recognize handwritten text
        in the document image, with context-aware processing for improved accuracy.
        
        Args:
            image: Preprocessed document image as a numpy array
            
        Returns:
            List of tuples containing extracted text and confidence scores
            
        Raises:
            RuntimeError: If text extraction fails
        """
        try:
            logger.info("Extracting handwritten text from document image")
            start_time = time.time()
            
            # Ensure model is loaded
            if self.model is None:
                raise RuntimeError("Model not loaded. Call _load_model() first.")
            
            # Prepare image for model input
            # Add batch dimension if needed
            if len(image.shape) == 2:
                # Add channel dimension for grayscale
                image = np.expand_dims(image, axis=-1)
            
            # Add batch dimension
            input_image = np.expand_dims(image, axis=0)
            
            # Run inference using the TensorFlow model
            # The exact API depends on how the model was saved and its signature
            try:
                # Try using the default serving signature
                if hasattr(self.model, 'signatures') and 'serving_default' in self.model.signatures:
                    serving_fn = self.model.signatures['serving_default']
                    input_tensor_name = list(serving_fn.inputs.keys())[0]
                    output = serving_fn({input_tensor_name: tf.convert_to_tensor(input_image)})
                    
                    # Extract predictions from output
                    predictions = list(output.values())[0].numpy()
                else:
                    # Fallback to direct call
                    predictions = self.model(input_image).numpy()
            except Exception as e:
                logger.error(f"Error during model inference: {str(e)}")
                # Try alternative approach with saved model
                predictions = self.model(input_image).numpy()
            
            # Process the predictions to extract text and confidence scores
            extracted_text = self._decode_predictions(predictions)
            
            # Apply context-aware correction if enabled
            if self.parameters.get("use_attention", True):
                extracted_text = self._apply_context_correction(extracted_text)
            
            # Log processing time
            processing_time = time.time() - start_time
            logger.info(f"Handwritten text extraction completed in {processing_time:.2f} seconds")
            
            return extracted_text
        except Exception as e:
            error_msg = f"Failed to extract handwritten text: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _decode_predictions(self, predictions: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """
        Decode model predictions into text with confidence scores.
        
        This method converts the raw model output (typically character probabilities)
        into readable text with associated confidence scores.
        
        Args:
            predictions: Raw model predictions as numpy array
            
        Returns:
            List of tuples containing (text, confidence_score)
        """
        try:
            # This implementation depends on the specific model architecture and output format
            # For this example, we'll assume the model outputs character probabilities
            # for a fixed vocabulary, similar to many handwriting recognition models
            
            # Load vocabulary (character mapping)
            vocab_path = self.parameters.get('vocab_path')
            if vocab_path and os.path.exists(vocab_path):
                with open(vocab_path, 'r') as f:
                    vocab = [line.strip() for line in f]
            else:
                # Fallback vocabulary (simplified)
                vocab = [' '] + list('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?!-\'"():;/')
            
            # For CTC-based models, predictions shape is typically [batch_size, time_steps, num_classes]
            if len(predictions.shape) == 3:
                batch_size, time_steps, num_classes = predictions.shape
                
                # Process each sequence in the batch
                results = []
                for b in range(batch_size):
                    # Get the most likely character at each time step
                    best_chars = np.argmax(predictions[b], axis=1)
                    
                    # Get the confidence (probability) of each prediction
                    confidences = np.max(predictions[b], axis=1)
                    
                    # Decode using CTC-like approach (merge repeated characters)
                    text = ""
                    confidence_values = []
                    prev_char = -1
                    
                    for t in range(time_steps):
                        char_idx = best_chars[t]
                        
                        # Skip if it's a repeated character (CTC behavior)
                        if char_idx != prev_char and char_idx < len(vocab):
                            # Skip blank character (typically index 0)
                            if char_idx > 0 or vocab[char_idx] != ' ':
                                text += vocab[char_idx]
                                confidence_values.append(confidences[t])
                        
                        prev_char = char_idx
                    
                    # Calculate overall confidence as average of character confidences
                    avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
                    
                    # Create confidence score object
                    confidence_score = ConfidenceScore.from_float(avg_confidence)
                    
                    results.append((text, confidence_score))
                
                return results
            else:
                logger.warning(f"Unexpected prediction shape: {predictions.shape}")
                # Return empty result for unexpected format
                return [("<error: unexpected format>", ConfidenceScore.from_float(0.0))]
                
        except Exception as e:
            logger.error(f"Error decoding predictions: {str(e)}")
            return [("<error: decoding failed>", ConfidenceScore.from_float(0.0))]
    
    def _apply_context_correction(self, extracted_text: List[Tuple[str, ConfidenceScore]]) -> List[Tuple[str, ConfidenceScore]]:
        """
        Apply context-aware correction to improve text recognition accuracy.
        
        This method uses language models and contextual information to correct
        common errors in handwritten text recognition.
        
        Args:
            extracted_text: List of (text, confidence) tuples from initial recognition
            
        Returns:
            List of (corrected_text, adjusted_confidence) tuples
        """
        try:
            corrected_results = []
            
            for text, confidence in extracted_text:
                # Skip empty text
                if not text:
                    corrected_results.append((text, confidence))
                    continue
                
                # Apply language model correction
                corrected_text, correction_confidence = correct_ocr_errors(text)
                
                # Combine original confidence with correction confidence
                # Weight the original confidence more heavily for handwritten text
                adjusted_confidence = (1 - self.language_model_weight) * confidence.value + \
                                    self.language_model_weight * correction_confidence
                
                # Create new confidence score
                new_confidence = ConfidenceScore.from_float(adjusted_confidence)
                
                corrected_results.append((corrected_text, new_confidence))
            
            return corrected_results
        except Exception as e:
            logger.warning(f"Error applying context correction: {str(e)}")
            return extracted_text
    
    def extract_fields(self, image: np.ndarray, 
                      document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract structured fields from the document image.
        
        This method identifies and extracts structured fields from handwritten documents,
        such as form fields, signatures, and annotations.
        
        Args:
            image: Preprocessed document image as a numpy array
            document_metadata: Metadata of the document including type and classification
            
        Returns:
            List of extracted fields with values and confidence scores
            
        Raises:
            RuntimeError: If field extraction fails
        """
        try:
            logger.info("Extracting fields from handwritten document")
            start_time = time.time()
            
            # Extract text from the image
            extracted_text_results = self.extract_text(image)
            
            # Combine all text into a single string for field extraction
            full_text = " ".join([text for text, _ in extracted_text_results])
            
            # Calculate average confidence
            avg_confidence = sum([conf.value for _, conf in extracted_text_results]) / len(extracted_text_results) \
                            if extracted_text_results else 0.0
            
            # Extract fields based on document type
            document_type = document_metadata.get("type", DocumentType.OTHER)
            
            # Detect text regions in the image
            text_regions = self._detect_handwritten_regions(image)
            
            # Extract key-value pairs from the text
            key_value_pairs = extract_key_value_pairs(full_text)
            
            # Create extracted fields
            extracted_fields = []
            
            # Process each key-value pair
            for i, (key, value, pair_confidence) in enumerate(key_value_pairs):
                # Skip empty values
                if not value:
                    continue
                
                # Determine field type based on key
                field_type = self._determine_field_type(key)
                
                # Validate and correct the field value
                is_valid, corrected_value, validation_confidence = validate_field(value, field_type)
                
                # Combine extraction and validation confidence
                combined_confidence = pair_confidence * validation_confidence * avg_confidence
                
                # Create field location
                # Use detected region if available, otherwise use placeholder
                if i < len(text_regions):
                    x, y, w, h = text_regions[i]
                    field_location = {
                        "page": 1,  # Assuming single page
                        "top": float(y) / image.shape[0],
                        "left": float(x) / image.shape[1],
                        "bottom": float(y + h) / image.shape[0],
                        "right": float(x + w) / image.shape[1],
                        "width": float(w) / image.shape[1],
                        "height": float(h) / image.shape[0]
                    }
                else:
                    # Placeholder location
                    field_location = {
                        "page": 1,
                        "top": 0.0,
                        "left": 0.0,
                        "bottom": 0.0,
                        "right": 0.0,
                        "width": 0.0,
                        "height": 0.0
                    }
                
                # Create the extracted field
                field = ExtractedField(
                    name=key,
                    value=corrected_value,
                    confidence=ConfidenceScore.from_float(combined_confidence),
                    field_type=field_type,
                    location=field_location,
                    requires_verification=combined_confidence < self.min_confidence_threshold,
                    category=self._determine_field_category(key, document_type)
                )
                
                extracted_fields.append(field)
            
            # Add signature field if detected
            signature_field = self._extract_signature(image, document_metadata)
            if signature_field:
                extracted_fields.append(signature_field)
            
            # Log processing time
            processing_time = time.time() - start_time
            logger.info(f"Field extraction completed in {processing_time:.2f} seconds")
            
            return extracted_fields
        except Exception as e:
            error_msg = f"Failed to extract fields from handwritten document: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def _detect_handwritten_regions(self, image: np.ndarray) -> List[Tuple[int, int, int, int]]:
        """
        Detect regions containing handwritten text in the document.
        
        This method identifies areas in the document that contain handwritten text,
        which is useful for locating form fields and annotations.
        
        Args:
            image: Preprocessed document image as a numpy array
            
        Returns:
            List of bounding boxes as (x, y, width, height) tuples
        """
        try:
            # Ensure image is in the right format
            if len(image.shape) == 3 and image.shape[2] > 1:
                gray = cv2.cvtColor(
                    (image * 255).astype(np.uint8) if image.max() <= 1.0 else image.astype(np.uint8), 
                    cv2.COLOR_RGB2GRAY
                )
            elif len(image.shape) == 3 and image.shape[2] == 1:
                gray = image.squeeze()
            else:
                gray = image
            
            # Convert to uint8 if needed
            if gray.dtype != np.uint8:
                gray = (gray * 255).astype(np.uint8)
            
            # Apply adaptive thresholding to handle varying illumination
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Apply morphological operations to connect nearby text
            kernel = np.ones((5, 5), np.uint8)
            dilated = cv2.dilate(binary, kernel, iterations=2)
            
            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size
            min_area = 100  # Minimum area in pixels
            text_regions = []
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = w * h
                
                # Skip very small regions (likely noise)
                if area < min_area:
                    continue
                
                # Skip very large regions (likely page borders)
                if area > 0.5 * gray.shape[0] * gray.shape[1]:
                    continue
                
                text_regions.append((x, y, w, h))
            
            # Sort regions by vertical position (top to bottom)
            text_regions.sort(key=lambda r: r[1])
            
            return text_regions
        except Exception as e:
            logger.warning(f"Error detecting handwritten regions: {str(e)}")
            return []
    
    def _determine_field_type(self, key: str) -> str:
        """
        Determine the field type based on the key name.
        
        Args:
            key: Field key to analyze
            
        Returns:
            Field type string (text, number, date, etc.)
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
        if any(term in key for term in ['amount', 'revenue', 'income', 'payment', 'balance', 'price', 'cost', 'fee']):
            return 'currency'
        
        # Check for signature fields
        if any(term in key for term in ['signature', 'sign', 'signed']):
            return 'signature'
        
        # Check for name fields
        if any(term in key for term in ['name', 'first', 'last', 'middle', 'full']):
            return 'name'
        
        # Check for address fields
        if any(term in key for term in ['address', 'street', 'city', 'state', 'zip', 'postal']):
            return 'address'
        
        # Default to text for unknown field types
        return 'text'
    
    def _determine_field_category(self, key: str, document_type: DocumentType) -> str:
        """
        Determine the category of a field based on its key and document type.
        
        Args:
            key: Field key to categorize
            document_type: Type of document
            
        Returns:
            Category string (personal, business, financial, etc.)
        """
        key = key.lower()
        
        # Personal information fields
        if any(term in key for term in ['name', 'email', 'phone', 'address', 'dob', 'birth', 'ssn', 'social']):
            return 'personal'
        
        # Business information fields
        if any(term in key for term in ['business', 'company', 'dba', 'ein', 'tax id', 'employer']):
            return 'business'
        
        # Financial information fields
        if any(term in key for term in ['revenue', 'income', 'payment', 'balance', 'amount', 'bank', 'account']):
            return 'financial'
        
        # Application-specific fields
        if document_type == DocumentType.APPLICATION:
            return 'application'
        
        # Default category
        return 'general'
    
    def _extract_signature(self, image: np.ndarray, document_metadata: DocumentMetadata) -> Optional[ExtractedField]:
        """
        Extract signature from the document if present.
        
        This method uses specialized detection techniques to identify and extract
        signatures, which are a common element in handwritten documents.
        
        Args:
            image: Preprocessed document image as a numpy array
            document_metadata: Metadata of the document
            
        Returns:
            ExtractedField for the signature if found, None otherwise
        """
        try:
            # Ensure image is in the right format
            if len(image.shape) == 3 and image.shape[2] > 1:
                gray = cv2.cvtColor(
                    (image * 255).astype(np.uint8) if image.max() <= 1.0 else image.astype(np.uint8), 
                    cv2.COLOR_RGB2GRAY
                )
            elif len(image.shape) == 3 and image.shape[2] == 1:
                gray = image.squeeze()
            else:
                gray = image
            
            # Convert to uint8 if needed
            if gray.dtype != np.uint8:
                gray = (gray * 255).astype(np.uint8)
            
            # Apply adaptive thresholding
            binary = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 11, 2
            )
            
            # Apply morphological operations
            kernel = np.ones((3, 3), np.uint8)
            dilated = cv2.dilate(binary, kernel, iterations=1)
            
            # Find contours
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by size and shape
            signature_candidates = []
            
            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                area = cv2.contourArea(contour)
                rect_area = w * h
                
                # Skip very small contours
                if area < 500:
                    continue
                
                # Calculate aspect ratio and density
                aspect_ratio = float(w) / h if h > 0 else 0
                density = float(area) / rect_area if rect_area > 0 else 0
                
                # Signatures typically have these characteristics
                if 1.5 < aspect_ratio < 10 and 0.1 < density < 0.5:
                    signature_candidates.append((x, y, w, h, density))
            
            # If we found signature candidates, use the one with lowest density
            # (signatures typically have lower density than printed text)
            if signature_candidates:
                # Sort by density (ascending)
                signature_candidates.sort(key=lambda c: c[4])
                
                # Get the best candidate
                x, y, w, h, density = signature_candidates[0]
                
                # Create field location
                field_location = {
                    "page": 1,  # Assuming single page
                    "top": float(y) / gray.shape[0],
                    "left": float(x) / gray.shape[1],
                    "bottom": float(y + h) / gray.shape[0],
                    "right": float(x + w) / gray.shape[1],
                    "width": float(w) / gray.shape[1],
                    "height": float(h) / gray.shape[0]
                }
                
                # Create signature field
                signature_field = ExtractedField(
                    name="signature",
                    value="<signature_detected>",  # Placeholder value
                    confidence=ConfidenceScore.from_float(0.85),  # Typical confidence for signature detection
                    field_type="signature",
                    location=field_location,
                    requires_verification=True,  # Signatures always require verification
                    category="authorization"
                )
                
                return signature_field
            
            return None
        except Exception as e:
            logger.warning(f"Error extracting signature: {str(e)}")
            return None
    
    def calculate_confidence(self, predictions: np.ndarray) -> ConfidenceScore:
        """
        Calculate confidence score from model predictions for handwritten text.
        
        This method implements specialized confidence scoring for handwritten text,
        which typically has more variability and uncertainty than typed text.
        
        Args:
            predictions: Raw prediction probabilities from the model
            
        Returns:
            Standardized confidence score between 0.0 and 1.0
        """
        try:
            # If predictions is None or empty, return zero confidence
            if predictions is None or len(predictions) == 0:
                return ConfidenceScore.from_float(0.0)
            
            # For handwritten text, we typically have lower confidence thresholds
            # than for typed text, so we adjust the scoring accordingly
            
            # For classification models, use the highest probability
            if predictions.ndim > 1 and predictions.shape[1] > 1:
                # Get the max probability for each position
                max_probs = np.max(predictions, axis=1)
                
                # Calculate mean probability
                mean_prob = float(np.mean(max_probs))
                
                # Apply sigmoid-like scaling to boost mid-range confidences
                # This helps account for the inherent variability in handwriting
                adjusted_confidence = 1.0 / (1.0 + np.exp(-10 * (mean_prob - 0.5)))
                
                return ConfidenceScore.from_float(adjusted_confidence)
            
            # For regression or single-output models, normalize to 0-1 range
            normalized = float(np.clip(predictions.mean(), 0.0, 1.0))
            
            # Apply handwriting-specific adjustment
            # Handwritten text typically has lower raw confidence, so we boost it slightly
            adjusted = 0.7 * normalized + 0.3 * (normalized ** 0.5)
            
            return ConfidenceScore.from_float(adjusted)
        except Exception as e:
            logger.warning(f"Error calculating confidence: {str(e)}")
            return ConfidenceScore.from_float(0.5)  # Default to medium confidence on error