#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Abstract base class for all OCR models in the system.

This module defines the BaseOCRModel abstract class that establishes the common interface
and shared functionality that all OCR models must implement. It includes methods for model
loading, image preprocessing, text extraction, and result formatting with confidence scoring.

All OCR model implementations (typed text, handwritten text, hybrid) must inherit from this
base class and implement its abstract methods to ensure consistent behavior across the OCR service.

Requirements:
- TensorFlow 2.15.0 with GPU acceleration (CUDA-compatible GPU with at least 8GB VRAM)
- Processing time under 5 minutes per document
- 99% data extraction accuracy
"""

import abc
import os
import time
import logging
from typing import Dict, List, Tuple, Any, Optional, Union

import numpy as np
import tensorflow as tf

from ..types.models import ModelParameters, ModelResult, OCRModelType
from ..types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from ..types.errors import ServiceError


class BaseOCRModel(abc.ABC):
    """
    Abstract base class for all OCR models in the system.
    
    This class defines the common interface and shared functionality that all OCR models
    must implement, including methods for model loading, image preprocessing, text extraction,
    and result formatting with confidence scoring.
    
    Attributes:
        model_type (OCRModelType): The type of OCR model (TYPED, HANDWRITTEN, HYBRID).
        model_path (str): Path to the TensorFlow model file.
        model_parameters (ModelParameters): Configuration parameters for the model.
        model (tf.keras.Model): The loaded TensorFlow model.
        logger (logging.Logger): Logger for the model.
        gpu_available (bool): Whether GPU acceleration is available.
    """
    
    def __init__(self, model_path: str, model_parameters: ModelParameters):
        """
        Initialize the OCR model.
        
        Args:
            model_path (str): Path to the TensorFlow model file.
            model_parameters (ModelParameters): Configuration parameters for the model.
            
        Raises:
            ServiceError: If the model file does not exist or cannot be loaded.
        """
        self.model_path = model_path
        self.model_parameters = model_parameters
        self.model = None
        self.logger = logging.getLogger(__name__)
        
        # Check if GPU is available for TensorFlow
        self.gpu_available = tf.config.list_physical_devices('GPU')
        
        if not self.gpu_available:
            self.logger.warning("No GPU detected. OCR processing may be slow. "
                               "TensorFlow OCR processing requires CUDA-compatible GPU "
                               "acceleration with at least 8GB VRAM.")
        else:
            self.logger.info(f"GPU detected: {self.gpu_available}")
            
            # Configure GPU memory growth to avoid allocating all memory at once
            for gpu in self.gpu_available:
                try:
                    tf.config.experimental.set_memory_growth(gpu, True)
                    self.logger.info(f"Memory growth enabled for GPU: {gpu}")
                except RuntimeError as e:
                    self.logger.error(f"Error configuring GPU memory growth: {str(e)}")
        
        # Validate model path
        if not os.path.exists(model_path):
            error_msg = f"Model file not found at path: {model_path}"
            self.logger.error(error_msg)
            raise ServiceError(error_msg, "MODEL_NOT_FOUND")
    
    @abc.abstractmethod
    def load_model(self) -> None:
        """
        Load the TensorFlow model from the specified path.
        
        This method must be implemented by all derived classes to load the specific
        model architecture required for their OCR task.
        
        Raises:
            ServiceError: If the model cannot be loaded.
        """
        pass
    
    @abc.abstractmethod
    def preprocess_image(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess the input image for OCR processing.
        
        This method must be implemented by all derived classes to perform the specific
        preprocessing steps required for their OCR model.
        
        Args:
            image (np.ndarray): The input image as a numpy array.
            
        Returns:
            np.ndarray: The preprocessed image ready for OCR processing.
        """
        pass
    
    @abc.abstractmethod
    def extract_text(self, preprocessed_image: np.ndarray) -> ModelResult:
        """
        Extract text from the preprocessed image.
        
        This method must be implemented by all derived classes to perform the specific
        text extraction logic required for their OCR model.
        
        Args:
            preprocessed_image (np.ndarray): The preprocessed image ready for OCR processing.
            
        Returns:
            ModelResult: The extracted text with confidence scores.
        """
        pass
    
    @abc.abstractmethod
    def format_result(self, model_result: ModelResult) -> ExtractedData:
        """
        Format the model result into structured extracted data.
        
        This method must be implemented by all derived classes to format the raw model
        output into structured data with field names, values, and confidence scores.
        
        Args:
            model_result (ModelResult): The raw model output.
            
        Returns:
            ExtractedData: The structured extracted data with field names, values, and confidence scores.
        """
        pass
    
    def process(self, image: np.ndarray) -> ExtractedData:
        """
        Process an image and extract text with confidence scores.
        
        This method orchestrates the OCR processing pipeline:
        1. Load the model if not already loaded
        2. Preprocess the input image
        3. Extract text from the preprocessed image
        4. Format the result into structured data
        
        Args:
            image (np.ndarray): The input image as a numpy array.
            
        Returns:
            ExtractedData: The structured extracted data with field names, values, and confidence scores.
            
        Raises:
            ServiceError: If any step in the OCR processing pipeline fails.
        """
        start_time = time.time()
        self.logger.info("Starting OCR processing")
        
        try:
            # Load model if not already loaded
            if self.model is None:
                self.logger.info("Loading OCR model")
                self.load_model()
                self.logger.info("OCR model loaded successfully")
            
            # Preprocess image
            self.logger.info("Preprocessing image")
            preprocessed_image = self.preprocess_image(image)
            self.logger.info("Image preprocessing completed")
            
            # Extract text
            self.logger.info("Extracting text from image")
            model_result = self.extract_text(preprocessed_image)
            self.logger.info("Text extraction completed")
            
            # Format result
            self.logger.info("Formatting extraction result")
            extracted_data = self.format_result(model_result)
            self.logger.info("Result formatting completed")
            
            # Log processing time
            processing_time = time.time() - start_time
            self.logger.info(f"OCR processing completed in {processing_time:.2f} seconds")
            
            return extracted_data
            
        except Exception as e:
            error_msg = f"Error during OCR processing: {str(e)}"
            self.logger.error(error_msg)
            raise ServiceError(error_msg, "OCR_PROCESSING_ERROR")
    
    def calculate_confidence(self, probabilities: np.ndarray) -> ConfidenceScore:
        """
        Calculate confidence score from model probabilities.
        
        This is a shared utility method that all OCR models can use to calculate
        confidence scores from model probabilities.
        
        Args:
            probabilities (np.ndarray): The model probabilities for a prediction.
            
        Returns:
            ConfidenceScore: A confidence score between 0.0 and 1.0.
        """
        # Ensure probabilities are valid
        if probabilities is None or len(probabilities) == 0:
            return ConfidenceScore(0.0)
        
        # Calculate confidence score (mean of top probabilities)
        confidence = float(np.mean(probabilities))
        
        # Ensure confidence is between 0.0 and 1.0
        confidence = max(0.0, min(1.0, confidence))
        
        return ConfidenceScore(confidence)
    
    def normalize_image(self, image: np.ndarray) -> np.ndarray:
        """
        Normalize image pixel values to the range [0, 1].
        
        This is a shared utility method that all OCR models can use to normalize
        image pixel values.
        
        Args:
            image (np.ndarray): The input image as a numpy array.
            
        Returns:
            np.ndarray: The normalized image with pixel values in the range [0, 1].
        """
        # Ensure image is valid
        if image is None or image.size == 0:
            raise ServiceError("Invalid image for normalization", "INVALID_IMAGE")
        
        # Convert image to float32 if not already
        if image.dtype != np.float32:
            image = image.astype(np.float32)
        
        # Normalize pixel values to [0, 1]
        if np.max(image) > 1.0:
            image = image / 255.0
        
        return image
    
    def resize_image(self, image: np.ndarray, target_height: int, preserve_aspect_ratio: bool = True) -> np.ndarray:
        """
        Resize image to target height while optionally preserving aspect ratio.
        
        This is a shared utility method that all OCR models can use to resize images
        to a target height while optionally preserving the aspect ratio.
        
        Args:
            image (np.ndarray): The input image as a numpy array.
            target_height (int): The target height for the resized image.
            preserve_aspect_ratio (bool, optional): Whether to preserve the aspect ratio. Defaults to True.
            
        Returns:
            np.ndarray: The resized image.
        """
        # Ensure image is valid
        if image is None or image.size == 0:
            raise ServiceError("Invalid image for resizing", "INVALID_IMAGE")
        
        # Get original dimensions
        height, width = image.shape[:2]
        
        if preserve_aspect_ratio:
            # Calculate new width to preserve aspect ratio
            aspect_ratio = width / height
            target_width = int(target_height * aspect_ratio)
        else:
            # Use model's default width parameter
            target_width = self.model_parameters.get('width', width)
        
        # Resize image using TensorFlow
        resized_image = tf.image.resize(
            image, 
            [target_height, target_width],
            method=tf.image.ResizeMethod.BILINEAR
        ).numpy()
        
        return resized_image
    
    def enhance_image(self, image: np.ndarray) -> np.ndarray:
        """
        Enhance image quality for better OCR results.
        
        This is a shared utility method that all OCR models can use to enhance image
        quality for better OCR results. It applies common image enhancement techniques
        such as contrast adjustment and noise reduction.
        
        Args:
            image (np.ndarray): The input image as a numpy array.
            
        Returns:
            np.ndarray: The enhanced image.
        """
        # Ensure image is valid
        if image is None or image.size == 0:
            raise ServiceError("Invalid image for enhancement", "INVALID_IMAGE")
        
        # Convert to float32 if not already
        if image.dtype != np.float32:
            image = image.astype(np.float32)
        
        # Normalize to [0, 1]
        if np.max(image) > 1.0:
            image = image / 255.0
        
        # Apply contrast enhancement
        # Stretch histogram to use full range [0, 1]
        min_val = np.min(image)
        max_val = np.max(image)
        if max_val > min_val:  # Avoid division by zero
            image = (image - min_val) / (max_val - min_val)
        
        return image
    
    def __str__(self) -> str:
        """
        Return a string representation of the OCR model.
        
        Returns:
            str: A string representation of the OCR model.
        """
        return f"{self.__class__.__name__}(model_path={self.model_path})"
    
    def __repr__(self) -> str:
        """
        Return a string representation of the OCR model for debugging.
        
        Returns:
            str: A string representation of the OCR model for debugging.
        """
        return f"{self.__class__.__name__}(model_path={self.model_path}, parameters={self.model_parameters})"