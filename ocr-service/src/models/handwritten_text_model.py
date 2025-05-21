#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Implements a specialized TensorFlow model for recognizing and extracting handwritten text from documents.

This module provides a TensorFlow-based model optimized for handwritten text recognition,
designed to handle the variability and inconsistency of handwritten notes, signatures,
and form fields that are common in merchant applications. It uses advanced neural networks
with specialized preprocessing techniques to achieve high accuracy in handwriting recognition.
"""

import os
import logging
import numpy as np
import tensorflow as tf
from typing import Dict, List, Tuple, Any, Optional, Union
from datetime import datetime

# Import from project modules
from .base_model import BaseOCRModel
from ..types.models import ModelParameters, OCRModelType, ModelResult
from ..types.extraction import ConfidenceScore, ExtractedField, FieldLocation
from ..types.documents import DocumentType
from ..utils.image_utils import (
    preprocess_for_ocr,
    enhance_contrast,
    normalize_orientation,
    sharpen_image,
    deskew_image,
    normalize_size
)

# Configure logger
logger = logging.getLogger(__name__)

# Constants
DEFAULT_MODEL_PATH = os.environ.get(
    "HANDWRITTEN_MODEL_PATH", 
    "/models/handwritten_text_ocr"
)
DEFAULT_VOCAB_PATH = os.environ.get(
    "HANDWRITTEN_VOCAB_PATH", 
    "/models/handwritten_text_ocr/vocab.txt"
)
MIN_CONFIDENCE_THRESHOLD = 0.6  # Minimum confidence threshold for accepting results
MAX_TEXT_LENGTH = 512  # Maximum text length the model can handle
INPUT_HEIGHT = 64  # Input height for the model
INPUT_WIDTH = 1024  # Input width for the model


class HandwrittenTextModel(BaseOCRModel):
    """
    Specialized TensorFlow model for recognizing and extracting handwritten text from documents.
    
    This model is designed to handle the variability and inconsistency of handwritten notes,
    signatures, and form fields that are common in merchant applications. It uses a combination
    of CNN and RNN layers with attention mechanisms to achieve high accuracy in handwriting recognition.
    
    Attributes:
        model_params (ModelParameters): Parameters for configuring the model
        model (tf.keras.Model): The TensorFlow model for handwritten text recognition
        vocab (List[str]): Vocabulary of characters the model can recognize
        char_to_idx (Dict[str, int]): Mapping from characters to indices
        idx_to_char (Dict[int, str]): Mapping from indices to characters
        context_model (Optional[tf.keras.Model]): Additional model for context-aware recognition
    """
    
    def __init__(self, model_params: Optional[ModelParameters] = None):
        """
        Initialize the handwritten text recognition model.
        
        Args:
            model_params: Parameters for configuring the model (optional)
        """
        # Initialize with default parameters if none provided
        if model_params is None:
            model_params = {
                'model_name': 'handwritten_text_ocr',
                'model_version': '1.0.0',
                'model_type': OCRModelType.HANDWRITTEN.value,
                'model_path': DEFAULT_MODEL_PATH,
                'vocab_path': DEFAULT_VOCAB_PATH,
                'input_shape': (INPUT_HEIGHT, INPUT_WIDTH, 1),  # Grayscale input
                'input_dtype': 'float32',
                'max_text_length': MAX_TEXT_LENGTH,
                'grayscale': True,
                'normalize_input': True,
                'batch_size': 1,
                'use_gpu': True,
                'gpu_memory_limit': 6144,  # 6GB
                'num_threads': 4,
                'beam_width': 10,
                'language': 'en',
                'confidence_threshold': MIN_CONFIDENCE_THRESHOLD,
            }
        
        super().__init__(model_params)
        
        # Additional attributes specific to handwritten text recognition
        self.context_model = None  # Model for context-aware recognition
        self.attention_weights = None  # Attention weights for visualization
        
        # Load vocabulary
        self._load_vocabulary()
    
    def _load_vocabulary(self) -> None:
        """
        Load vocabulary file containing characters the model can recognize.
        
        The vocabulary file should contain one character per line.
        """
        try:
            vocab_path = self.model_params.get('vocab_path', DEFAULT_VOCAB_PATH)
            if not os.path.exists(vocab_path):
                logger.warning(f"Vocabulary file not found at {vocab_path}. Using default vocabulary.")
                # Default vocabulary includes alphanumeric characters and common symbols
                self.vocab = list("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,;:!?()-'\"\/")
            else:
                with open(vocab_path, 'r', encoding='utf-8') as f:
                    self.vocab = [line.strip() for line in f if line.strip()]
            
            # Add blank token for CTC decoding
            if '<blank>' not in self.vocab:
                self.vocab.append('<blank>')
            
            # Create character to index and index to character mappings
            self.char_to_idx = {char: idx for idx, char in enumerate(self.vocab)}
            self.idx_to_char = {idx: char for idx, char in enumerate(self.vocab)}
            
            logger.info(f"Loaded vocabulary with {len(self.vocab)} characters")
        except Exception as e:
            logger.error(f"Error loading vocabulary: {str(e)}")
            raise RuntimeError(f"Failed to load vocabulary: {str(e)}")
    
    def _build_model(self) -> tf.keras.Model:
        """
        Build the TensorFlow model architecture for handwritten text recognition.
        
        This model uses a combination of CNN layers for feature extraction and
        bidirectional LSTM layers with attention mechanisms for sequence modeling.
        
        Returns:
            TensorFlow model for handwritten text recognition
        """
        # Get input shape from model parameters
        input_shape = self.model_params.get('input_shape', (INPUT_HEIGHT, INPUT_WIDTH, 1))
        
        # Input layer
        inputs = tf.keras.layers.Input(shape=input_shape, name='input')
        
        # CNN Feature Extraction Layers
        # First convolutional block
        x = tf.keras.layers.Conv2D(
            filters=32,
            kernel_size=(3, 3),
            strides=(1, 1),
            padding='same',
            activation='relu',
            name='conv1'
        )(inputs)
        x = tf.keras.layers.MaxPooling2D(
            pool_size=(2, 2),
            strides=(2, 2),
            name='pool1'
        )(x)
        x = tf.keras.layers.BatchNormalization(name='bn1')(x)
        
        # Second convolutional block
        x = tf.keras.layers.Conv2D(
            filters=64,
            kernel_size=(3, 3),
            strides=(1, 1),
            padding='same',
            activation='relu',
            name='conv2'
        )(x)
        x = tf.keras.layers.MaxPooling2D(
            pool_size=(2, 2),
            strides=(2, 2),
            name='pool2'
        )(x)
        x = tf.keras.layers.BatchNormalization(name='bn2')(x)
        
        # Third convolutional block
        x = tf.keras.layers.Conv2D(
            filters=128,
            kernel_size=(3, 3),
            strides=(1, 1),
            padding='same',
            activation='relu',
            name='conv3'
        )(x)
        x = tf.keras.layers.MaxPooling2D(
            pool_size=(2, 1),  # Pool only height, preserve width for sequence
            strides=(2, 1),
            name='pool3'
        )(x)
        x = tf.keras.layers.BatchNormalization(name='bn3')(x)
        
        # Fourth convolutional block
        x = tf.keras.layers.Conv2D(
            filters=256,
            kernel_size=(3, 3),
            strides=(1, 1),
            padding='same',
            activation='relu',
            name='conv4'
        )(x)
        x = tf.keras.layers.MaxPooling2D(
            pool_size=(2, 1),  # Pool only height, preserve width for sequence
            strides=(2, 1),
            name='pool4'
        )(x)
        x = tf.keras.layers.BatchNormalization(name='bn4')(x)
        
        # Fifth convolutional block with dilated convolutions for larger receptive field
        x = tf.keras.layers.Conv2D(
            filters=256,
            kernel_size=(3, 3),
            strides=(1, 1),
            padding='same',
            dilation_rate=(2, 2),  # Dilated convolution
            activation='relu',
            name='conv5'
        )(x)
        x = tf.keras.layers.BatchNormalization(name='bn5')(x)
        
        # Reshape for sequence modeling
        # At this point, x has shape (batch, height, width, channels)
        # We need to reshape to (batch, time_steps, features)
        _, h, w, c = x.get_shape().as_list()
        x = tf.keras.layers.Reshape((w, h * c), name='reshape')(x)
        
        # Bidirectional LSTM layers for sequence modeling
        x = tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(256, return_sequences=True),
            name='bilstm1'
        )(x)
        x = tf.keras.layers.Dropout(0.25, name='dropout1')(x)
        
        # Second Bidirectional LSTM with attention mechanism
        lstm2 = tf.keras.layers.Bidirectional(
            tf.keras.layers.LSTM(256, return_sequences=True),
            name='bilstm2'
        )(x)
        x = tf.keras.layers.Dropout(0.25, name='dropout2')(lstm2)
        
        # Attention mechanism
        attention = tf.keras.layers.Dense(1, activation='tanh', name='attention_dense')(x)
        attention = tf.keras.layers.Flatten(name='attention_flatten')(attention)
        attention = tf.keras.layers.Activation('softmax', name='attention_softmax')(attention)
        attention = tf.keras.layers.RepeatVector(512, name='attention_repeat')(attention)
        attention = tf.keras.layers.Permute([2, 1], name='attention_permute')(attention)
        
        # Apply attention to LSTM output
        context = tf.keras.layers.Multiply(name='attention_mul')([lstm2, attention])
        
        # Output layer
        outputs = tf.keras.layers.Dense(
            len(self.vocab),  # Number of characters in vocabulary
            activation='softmax',
            name='dense'
        )(context)
        
        # Create model
        model = tf.keras.Model(inputs=inputs, outputs=outputs, name='handwritten_text_model')
        
        # Compile model
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss=self._ctc_loss,
            metrics=['accuracy']
        )
        
        return model
    
    def _ctc_loss(self, y_true, y_pred):
        """
        Custom CTC loss function for sequence recognition.
        
        Args:
            y_true: True labels
            y_pred: Predicted labels
            
        Returns:
            CTC loss value
        """
        # Get batch size and max length
        batch_size = tf.shape(y_true)[0]
        max_length = tf.shape(y_true)[1]
        
        # Calculate input sequence length (assuming all are the same length)
        input_length = tf.fill([batch_size, 1], tf.shape(y_pred)[1])
        
        # Calculate label length
        label_length = tf.reduce_sum(tf.cast(y_true != 0, tf.int32), axis=1, keepdims=True)
        
        # Calculate CTC loss
        loss = tf.keras.backend.ctc_batch_cost(
            y_true, y_pred, input_length, label_length
        )
        
        return loss
    
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Apply specialized preprocessing for handwritten text images.
        
        This method enhances the image to improve handwriting recognition accuracy,
        including contrast enhancement, deskewing, and noise removal.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image ready for model inference
        """
        # Apply general preprocessing for OCR
        preprocessed = preprocess_for_ocr(image, DocumentType.APPLICATION)
        
        # Apply specialized preprocessing for handwritten text
        # 1. Enhance contrast to make handwriting more visible
        enhanced = enhance_contrast(preprocessed, clip_limit=3.0)
        
        # 2. Deskew the image to straighten handwriting
        deskewed = deskew_image(enhanced)
        
        # 3. Sharpen the image to make handwriting more defined
        sharpened = sharpen_image(deskewed, amount=2.0)
        
        # 4. Normalize size to model input dimensions
        input_shape = self.model_params.get('input_shape', (INPUT_HEIGHT, INPUT_WIDTH, 1))
        height, width = input_shape[0], input_shape[1]
        normalized = normalize_size(sharpened)
        resized = tf.image.resize(normalized, [height, width]).numpy()
        
        # 5. Convert to grayscale if needed
        if len(resized.shape) == 3 and resized.shape[2] == 3:
            grayscale = tf.image.rgb_to_grayscale(resized).numpy()
        elif len(resized.shape) == 2:
            grayscale = np.expand_dims(resized, axis=-1)
        else:
            grayscale = resized
        
        # 6. Normalize pixel values to [0, 1]
        normalized = grayscale.astype(np.float32) / 255.0
        
        return normalized
    
    def extract_text(self, image: np.ndarray) -> ModelResult:
        """
        Extract handwritten text from the image.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            ModelResult containing extracted text and confidence scores
        """
        # Ensure model is loaded
        if self.model is None:
            self.load()
        
        # Preprocess image
        preprocessed = self.preprocess_image(image)
        
        # Add batch dimension
        input_tensor = np.expand_dims(preprocessed, axis=0)
        
        # Record start time for performance measurement
        start_time = datetime.now()
        
        # Run inference
        predictions = self.model.predict(input_tensor, verbose=0)
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Decode predictions using beam search
        beam_width = self.model_params.get('beam_width', 10)
        decoded_text, confidence = self._decode_predictions(predictions[0], beam_width)
        
        # Create bounding boxes for text regions
        # For handwritten text, we assume the entire image is one text region
        height, width = image.shape[:2]
        bounding_boxes = [{
            'x': 0,
            'y': 0,
            'width': width,
            'height': height,
            'text': decoded_text,
            'confidence': float(confidence)
        }]
        
        # Calculate word confidences
        word_confidences = self._calculate_word_confidences(predictions[0], decoded_text)
        
        # Create result
        result = {
            'text': decoded_text,
            'confidence': float(confidence),
            'bounding_boxes': bounding_boxes,
            'word_confidences': word_confidences,
            'processing_time': processing_time,
            'page_number': 1,  # Assuming single page
            'model_type': OCRModelType.HANDWRITTEN.value,
            'warnings': [],
            'language': self.model_params.get('language', 'en')
        }
        
        # Add warnings if confidence is low
        if confidence < self.model_params.get('confidence_threshold', MIN_CONFIDENCE_THRESHOLD):
            result['warnings'].append(f"Low confidence detection: {confidence:.2f}")
        
        return result
    
    def _decode_predictions(self, predictions: np.ndarray, beam_width: int = 10) -> Tuple[str, float]:
        """
        Decode model predictions into text using beam search decoding.
        
        Args:
            predictions: Model predictions as probability distribution over characters
            beam_width: Beam width for beam search decoding
            
        Returns:
            Tuple of (decoded_text, confidence)
        """
        # Get sequence length
        seq_len = predictions.shape[0]
        
        # Initialize beam with empty string and probability 1.0
        beam = [([], 1.0)]
        
        # Perform beam search
        for t in range(seq_len):
            new_beam = []
            
            for prefix, prefix_prob in beam:
                # Get probabilities for this time step
                char_probs = predictions[t]
                
                # Get top-k characters
                top_k_indices = np.argsort(char_probs)[-beam_width:]
                top_k_probs = char_probs[top_k_indices]
                
                # Add each character to the beam
                for i, p in zip(top_k_indices, top_k_probs):
                    # Skip blank character
                    if i == len(self.vocab) - 1:  # Assuming blank is the last character
                        continue
                    
                    # Calculate new probability
                    new_prob = prefix_prob * p
                    
                    # Add to new beam
                    new_prefix = prefix + [i]
                    new_beam.append((new_prefix, new_prob))
            
            # Keep only top beam_width candidates
            beam = sorted(new_beam, key=lambda x: x[1], reverse=True)[:beam_width]
        
        # Get best sequence
        best_sequence, best_prob = beam[0]
        
        # Convert indices to characters
        decoded_text = ''.join([self.idx_to_char[idx] for idx in best_sequence])
        
        # Calculate overall confidence
        confidence = best_prob ** (1.0 / len(best_sequence)) if best_sequence else 0.0
        
        return decoded_text, confidence
    
    def _calculate_word_confidences(self, predictions: np.ndarray, decoded_text: str) -> List[float]:
        """
        Calculate confidence scores for individual words in the decoded text.
        
        Args:
            predictions: Model predictions as probability distribution over characters
            decoded_text: Decoded text string
            
        Returns:
            List of confidence scores for each word
        """
        # Split text into words
        words = decoded_text.split()
        
        if not words:
            return []
        
        # Initialize word confidences
        word_confidences = []
        
        # Track current position in the sequence
        pos = 0
        
        # Calculate confidence for each word
        for word in words:
            word_length = len(word)
            
            # Skip if we're at the end of predictions
            if pos + word_length > predictions.shape[0]:
                word_confidences.append(0.5)  # Default confidence
                continue
            
            # Calculate confidence for this word
            char_confidences = []
            for i, char in enumerate(word):
                if pos + i < predictions.shape[0]:
                    char_idx = self.char_to_idx.get(char, 0)
                    char_confidences.append(predictions[pos + i, char_idx])
            
            # Calculate average confidence for the word
            if char_confidences:
                word_confidence = sum(char_confidences) / len(char_confidences)
                word_confidences.append(float(word_confidence))
            else:
                word_confidences.append(0.5)  # Default confidence
            
            # Move position forward (add 1 for the space)
            pos += word_length + 1
        
        return word_confidences
    
    def extract_fields(self, image: np.ndarray, field_definitions: List[Dict[str, Any]]) -> Dict[str, ExtractedField]:
        """
        Extract specific fields from handwritten text based on field definitions.
        
        Args:
            image: Input image as numpy array
            field_definitions: List of field definitions with locations and types
            
        Returns:
            Dictionary of extracted fields with values and confidence scores
        """
        # Extract text from the entire image
        result = self.extract_text(image)
        extracted_text = result['text']
        overall_confidence = result['confidence']
        
        # Initialize extracted fields dictionary
        extracted_fields = {}
        
        # Process each field definition
        for field_def in field_definitions:
            field_name = field_def.get('field_name', '')
            field_type = field_def.get('field_type', 'text')
            field_location = field_def.get('location', None)
            
            # If field location is provided, extract text from that region
            if field_location:
                # Convert normalized coordinates to pixel coordinates
                height, width = image.shape[:2]
                top = int(field_location['top'] * height)
                left = int(field_location['left'] * width)
                bottom = int(field_location['bottom'] * height)
                right = int(field_location['right'] * width)
                
                # Extract region
                region = image[top:bottom, left:right]
                
                # Extract text from region
                region_result = self.extract_text(region)
                field_text = region_result['text']
                field_confidence = region_result['confidence']
            else:
                # Use the entire text and try to find the field based on context
                field_text, field_confidence = self._extract_field_by_context(
                    extracted_text, field_name, field_type
                )
            
            # Create field location
            if field_location:
                location = field_location
            else:
                # Default location (entire image)
                location = {
                    'page': 0,
                    'top': 0.0,
                    'left': 0.0,
                    'bottom': 1.0,
                    'right': 1.0,
                    'width': 1.0,
                    'height': 1.0
                }
            
            # Process field value based on type
            processed_value = self._process_field_value(field_text, field_type)
            
            # Create confidence score
            confidence_score = ConfidenceScore.from_float(field_confidence)
            
            # Determine if verification is required
            requires_verification = confidence_score.is_low_confidence()
            verification_reason = "Low confidence score" if requires_verification else None
            
            # Create extracted field
            extracted_field = {
                'field_name': field_name,
                'field_type': field_type,
                'value': processed_value,
                'raw_text': field_text,
                'confidence': confidence_score,
                'location': location,
                'alternatives': [],  # No alternatives for now
                'metadata': {
                    'extraction_method': 'handwritten_text_model',
                    'model_version': self.model_params.get('model_version', '1.0.0')
                },
                'requires_verification': requires_verification,
                'verification_reason': verification_reason,
                'extraction_timestamp': datetime.now()
            }
            
            # Add to extracted fields dictionary
            extracted_fields[field_name] = extracted_field
        
        return extracted_fields
    
    def _extract_field_by_context(self, text: str, field_name: str, field_type: str) -> Tuple[str, float]:
        """
        Extract field value from text based on context and field name.
        
        This method uses simple heuristics to find field values in the text.
        For more advanced extraction, a dedicated NER model would be needed.
        
        Args:
            text: Extracted text from the document
            field_name: Name of the field to extract
            field_type: Type of the field
            
        Returns:
            Tuple of (field_value, confidence)
        """
        # Convert field name to lowercase for matching
        field_name_lower = field_name.lower().replace('_', ' ')
        
        # Look for patterns like "Field Name: Value" or "Field Name - Value"
        patterns = [
            f"{field_name_lower}:\s*([\w\s.,;:!?()-'\"/&]+)",
            f"{field_name_lower}\s*-\s*([\w\s.,;:!?()-'\"/&]+)",
            f"{field_name_lower}\s+([\w\s.,;:!?()-'\"/&]+)"
        ]
        
        # Try to match each pattern
        import re
        for pattern in patterns:
            matches = re.search(pattern, text.lower())
            if matches:
                # Found a match
                field_value = matches.group(1).strip()
                # Assign a moderate confidence since this is heuristic-based
                confidence = 0.7
                return field_value, confidence
        
        # If no match found, return empty string with low confidence
        return "", 0.3
    
    def _process_field_value(self, text: str, field_type: str) -> Any:
        """
        Process extracted field text based on field type.
        
        Args:
            text: Extracted text for the field
            field_type: Type of the field
            
        Returns:
            Processed field value
        """
        if not text:
            return None
        
        # Process based on field type
        if field_type == 'text':
            return text.strip()
        
        elif field_type == 'number':
            # Extract numeric value
            import re
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                return float(numbers[0])
            return None
        
        elif field_type == 'date':
            # Try to parse date
            try:
                from dateutil import parser
                return parser.parse(text).strftime('%Y-%m-%d')
            except:
                return text.strip()
        
        elif field_type == 'checkbox':
            # Check if text contains indicators of checked status
            checked_indicators = ['x', 'X', '✓', '✔', 'yes', 'Yes', 'YES', 'true', 'True', 'TRUE']
            return any(indicator in text for indicator in checked_indicators)
        
        elif field_type == 'signature':
            # For signatures, just indicate presence
            return len(text.strip()) > 0
        
        else:
            # Default to returning the text as is
            return text.strip()
    
    def get_attention_heatmap(self, image: np.ndarray) -> np.ndarray:
        """
        Generate attention heatmap for visualizing where the model is focusing.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Attention heatmap as numpy array
        """
        # Ensure model is loaded
        if self.model is None:
            self.load()
        
        # Preprocess image
        preprocessed = self.preprocess_image(image)
        
        # Add batch dimension
        input_tensor = np.expand_dims(preprocessed, axis=0)
        
        # Create attention model that outputs attention weights
        attention_layer_name = 'attention_softmax'
        attention_model = tf.keras.Model(
            inputs=self.model.input,
            outputs=self.model.get_layer(attention_layer_name).output
        )
        
        # Get attention weights
        attention_weights = attention_model.predict(input_tensor, verbose=0)
        
        # Reshape attention weights to match image width
        _, width = preprocessed.shape[:2]
        attention_heatmap = np.zeros((1, width))
        
        # Interpolate attention weights to match image width
        for i in range(width):
            pos = int(i * attention_weights.shape[1] / width)
            if pos < attention_weights.shape[1]:
                attention_heatmap[0, i] = attention_weights[0, pos]
        
        # Normalize heatmap
        attention_heatmap = attention_heatmap / np.max(attention_heatmap)
        
        # Resize heatmap to match original image dimensions
        import cv2
        heatmap = cv2.resize(attention_heatmap, (image.shape[1], image.shape[0]))
        
        return heatmap
    
    def enhance_recognition_with_context(self, text: str, context: Dict[str, Any]) -> Tuple[str, float]:
        """
        Enhance recognition results using contextual information.
        
        This method uses document context to improve recognition accuracy,
        especially for domain-specific terms and expected values.
        
        Args:
            text: Recognized text
            context: Contextual information (document type, expected fields, etc.)
            
        Returns:
            Tuple of (enhanced_text, confidence)
        """
        # If no context provided, return original text
        if not context:
            return text, 0.7
        
        # Get document type from context
        document_type = context.get('document_type', None)
        
        # Apply document type-specific enhancements
        if document_type == 'application_form':
            # For application forms, check for expected fields
            expected_fields = context.get('expected_fields', {})
            
            # Simple spell correction for expected field values
            for field_name, expected_values in expected_fields.items():
                if isinstance(expected_values, list):
                    # Check if any expected value is similar to the text
                    for expected in expected_values:
                        if self._is_similar(text, expected):
                            return expected, 0.9
        
        # Apply general spell correction
        corrected_text = self._apply_spell_correction(text)
        
        # If correction made, assign higher confidence
        if corrected_text != text:
            return corrected_text, 0.8
        
        # Return original text if no enhancements applied
        return text, 0.7
    
    def _is_similar(self, text1: str, text2: str, threshold: float = 0.7) -> bool:
        """
        Check if two strings are similar using Levenshtein distance.
        
        Args:
            text1: First string
            text2: Second string
            threshold: Similarity threshold (0.0-1.0)
            
        Returns:
            True if strings are similar, False otherwise
        """
        # Calculate Levenshtein distance
        import Levenshtein
        distance = Levenshtein.distance(text1.lower(), text2.lower())
        
        # Calculate similarity (1.0 means identical)
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return True  # Both strings are empty
        
        similarity = 1.0 - (distance / max_len)
        
        return similarity >= threshold
    
    def _apply_spell_correction(self, text: str) -> str:
        """
        Apply basic spell correction to the text.
        
        Args:
            text: Input text
            
        Returns:
            Corrected text
        """
        # This is a placeholder for spell correction
        # In a real implementation, you would use a spell correction library
        # such as pyspellchecker or a custom domain-specific correction logic
        
        # For now, just return the original text
        return text