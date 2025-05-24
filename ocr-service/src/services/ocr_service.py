#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Module

This module provides the core OCR processing service that orchestrates the application of 
TensorFlow models for text extraction from documents. It handles model loading, selection 
of appropriate OCR techniques based on document type, and processing of documents with 
GPU acceleration.
"""

import os
import time
import logging
from typing import Dict, List, Optional, Tuple, Union, Any

import tensorflow as tf
import numpy as np

# Import from local modules
from ..config import app_config, tensorflow_config
from ..models.model_factory import ModelFactory
from ..models.base_model import BaseModel
from ..types.models import OCRModelType, ModelParameters, ModelResult
from ..types.extraction import ExtractedData, ConfidenceScore, ExtractedField
from ..types.storage import StorageMetadata
from ..types.errors import ServiceError, Result
from ..utils import (
    image_utils,
    tensorflow_utils,
    text_utils,
    time_utils,
    logging_utils,
    error_utils
)


class OCRService:
    """
    Core OCR processing service that orchestrates the application of TensorFlow models
    for text extraction from documents.
    
    This service handles:
    - TensorFlow model loading and initialization with GPU acceleration
    - Document type detection for OCR strategy selection
    - Typed text OCR processing for machine-printed documents
    - Handwritten text OCR processing for handwritten documents
    - Hybrid OCR processing for mixed document types
    - Performance monitoring and optimization for GPU utilization
    """
    
    def __init__(self):
        """
        Initialize the OCR service with TensorFlow models and GPU configuration.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing OCR Service")
        
        # Configure GPU settings
        self._configure_gpu()
        
        # Initialize model factory
        self.model_factory = ModelFactory()
        
        # Load models based on configuration
        self._load_models()
        
        self.logger.info("OCR Service initialized successfully")
    
    def _configure_gpu(self) -> None:
        """
        Configure TensorFlow to use GPU acceleration with optimized settings.
        """
        try:
            # Check if GPU is available
            gpus = tf.config.list_physical_devices('GPU')
            if not gpus:
                self.logger.warning("No GPU found. Running on CPU which may impact performance")
                return
            
            self.logger.info(f"Found {len(gpus)} GPU(s): {gpus}")
            
            # Configure memory growth to avoid allocating all GPU memory at once
            for gpu in gpus:
                tf.config.experimental.set_memory_growth(gpu, True)
            
            # Set visible devices if specified in config
            if tensorflow_config.VISIBLE_DEVICES is not None:
                tf.config.set_visible_devices(
                    gpus[tensorflow_config.VISIBLE_DEVICES], 'GPU'
                )
            
            # Configure memory limit if specified
            if tensorflow_config.GPU_MEMORY_LIMIT > 0:
                tf.config.set_logical_device_configuration(
                    gpus[0],
                    [tf.config.LogicalDeviceConfiguration(
                        memory_limit=tensorflow_config.GPU_MEMORY_LIMIT
                    )]
                )
            
            # Set TensorFlow to use mixed precision for better performance
            if tensorflow_config.USE_MIXED_PRECISION:
                tf.keras.mixed_precision.set_global_policy('mixed_float16')
            
            self.logger.info("GPU configuration completed successfully")
        
        except Exception as e:
            error_msg = f"Error configuring GPU: {str(e)}"
            self.logger.error(error_msg)
            # Continue with CPU as fallback
            self.logger.warning("Falling back to CPU execution")
    
    def _load_models(self) -> None:
        """
        Load and initialize all required OCR models.
        """
        try:
            self.logger.info("Loading OCR models")
            
            # Record model loading start time for performance monitoring
            start_time = time.time()
            
            # Pre-load models for faster inference during processing
            # This ensures models are ready when documents arrive
            self.typed_model = self.model_factory.get_model(OCRModelType.TYPED)
            self.handwritten_model = self.model_factory.get_model(OCRModelType.HANDWRITTEN)
            self.hybrid_model = self.model_factory.get_model(OCRModelType.HYBRID)
            
            # Warm up models with dummy data to initialize weights and optimize performance
            self._warm_up_models()
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"All OCR models loaded successfully in {elapsed_time:.2f} seconds")
        
        except Exception as e:
            error_msg = f"Failed to load OCR models: {str(e)}"
            self.logger.error(error_msg)
            raise ServiceError("MODEL_LOADING_ERROR", error_msg)
    
    def _warm_up_models(self) -> None:
        """
        Warm up models with dummy data to initialize weights and optimize performance.
        """
        try:
            self.logger.info("Warming up OCR models")
            
            # Create a small dummy image for model warm-up
            dummy_image = np.zeros((300, 300, 3), dtype=np.uint8)
            dummy_image = image_utils.preprocess_image(dummy_image)
            
            # Warm up each model with the dummy image
            self.typed_model.extract_text(dummy_image)
            self.handwritten_model.extract_text(dummy_image)
            self.hybrid_model.extract_text(dummy_image)
            
            self.logger.info("Model warm-up completed successfully")
        
        except Exception as e:
            self.logger.warning(f"Model warm-up failed: {str(e)}. This may impact initial processing performance.")
    
    def detect_document_type(self, image: np.ndarray) -> OCRModelType:
        """
        Detect the document type (typed, handwritten, or mixed) to select the appropriate OCR model.
        
        Args:
            image: The preprocessed document image as a numpy array
            
        Returns:
            OCRModelType: The detected document type (TYPED, HANDWRITTEN, or HYBRID)
        """
        try:
            self.logger.info("Detecting document type for OCR model selection")
            
            # Use TensorFlow utilities to analyze the image and detect text type
            text_type_result = tensorflow_utils.detect_text_type(image)
            
            # Calculate percentages of different text types
            typed_percentage = text_type_result.get('typed_percentage', 0)
            handwritten_percentage = text_type_result.get('handwritten_percentage', 0)
            
            # Decision thresholds from configuration
            typed_threshold = tensorflow_config.TYPED_THRESHOLD
            handwritten_threshold = tensorflow_config.HANDWRITTEN_THRESHOLD
            
            # Determine document type based on percentages and thresholds
            if typed_percentage >= typed_threshold and handwritten_percentage < handwritten_threshold:
                self.logger.info(f"Document classified as TYPED (typed: {typed_percentage:.2f}%, handwritten: {handwritten_percentage:.2f}%)")
                return OCRModelType.TYPED
            
            elif handwritten_percentage >= handwritten_threshold and typed_percentage < typed_threshold:
                self.logger.info(f"Document classified as HANDWRITTEN (typed: {typed_percentage:.2f}%, handwritten: {handwritten_percentage:.2f}%)")
                return OCRModelType.HANDWRITTEN
            
            else:
                self.logger.info(f"Document classified as HYBRID (typed: {typed_percentage:.2f}%, handwritten: {handwritten_percentage:.2f}%)")
                return OCRModelType.HYBRID
        
        except Exception as e:
            error_msg = f"Error detecting document type: {str(e)}"
            self.logger.error(error_msg)
            # Default to hybrid model as the safest fallback
            self.logger.warning("Defaulting to HYBRID model due to detection error")
            return OCRModelType.HYBRID
    
    def select_model(self, document_type: OCRModelType) -> BaseModel:
        """
        Select the appropriate OCR model based on the document type.
        
        Args:
            document_type: The detected document type
            
        Returns:
            BaseModel: The selected OCR model instance
        """
        if document_type == OCRModelType.TYPED:
            return self.typed_model
        elif document_type == OCRModelType.HANDWRITTEN:
            return self.handwritten_model
        else:  # HYBRID or unknown
            return self.hybrid_model
    
    def process_document(self, document_data: bytes, metadata: Dict[str, Any]) -> Result[ExtractedData]:
        """
        Process a document for OCR text extraction.
        
        Args:
            document_data: The raw document data as bytes
            metadata: Document metadata including classification information
            
        Returns:
            Result[ExtractedData]: The extracted data with confidence scores or an error
        """
        start_time = time.time()
        request_id = metadata.get('request_id', 'unknown')
        document_type = metadata.get('document_type', 'unknown')
        
        self.logger.info(f"Processing document: request_id={request_id}, document_type={document_type}")
        
        try:
            # Convert document to image
            image = image_utils.convert_document_to_image(document_data)
            if image is None:
                error_msg = "Failed to convert document to image"
                self.logger.error(error_msg)
                return Result.failure(ServiceError("DOCUMENT_CONVERSION_ERROR", error_msg))
            
            # Preprocess the image for OCR
            preprocessed_image = image_utils.preprocess_image(image)
            
            # Detect document type if not provided in metadata or override is enabled
            model_type = None
            if 'classification' in metadata and not tensorflow_config.OVERRIDE_CLASSIFICATION:
                # Use classification from metadata if available
                classification = metadata['classification']
                if classification == 'typed':
                    model_type = OCRModelType.TYPED
                elif classification == 'handwritten':
                    model_type = OCRModelType.HANDWRITTEN
                elif classification == 'mixed':
                    model_type = OCRModelType.HYBRID
            
            # If model type is not determined from metadata, detect it
            if model_type is None:
                model_type = self.detect_document_type(preprocessed_image)
            
            # Select the appropriate model
            model = self.select_model(model_type)
            
            # Extract text using the selected model
            self.logger.info(f"Extracting text using {model_type.name} model")
            extraction_result = model.extract_text(preprocessed_image)
            
            # Apply structure recognition to identify forms, tables, and sections
            structured_data = self._apply_structure_recognition(extraction_result, metadata)
            
            # Extract key-value fields based on document type and structure
            extracted_fields = self._extract_fields(structured_data, metadata)
            
            # Calculate confidence scores for extracted fields
            scored_fields = self._score_field_confidence(extracted_fields)
            
            # Format the results as JSON
            result = self._format_extraction_result(scored_fields, metadata)
            
            # Calculate processing time for monitoring
            processing_time = time.time() - start_time
            self.logger.info(f"Document processing completed in {processing_time:.2f} seconds")
            
            # Add processing metrics to result
            result.metadata['processing_time'] = processing_time
            result.metadata['model_type'] = model_type.name
            
            return Result.success(result)
        
        except Exception as e:
            error_msg = f"Error processing document: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            processing_time = time.time() - start_time
            return Result.failure(
                ServiceError(
                    "DOCUMENT_PROCESSING_ERROR", 
                    error_msg,
                    metadata={
                        'processing_time': processing_time,
                        'request_id': request_id
                    }
                )
            )
    
    def _apply_structure_recognition(self, extraction_result: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply structure recognition to identify forms, tables, and document sections.
        
        Args:
            extraction_result: The raw extraction result from the OCR model
            metadata: Document metadata including classification information
            
        Returns:
            Dict[str, Any]: The structured data with identified forms, tables, and sections
        """
        try:
            self.logger.info("Applying structure recognition")
            
            # Get document type from metadata for specialized structure recognition
            document_type = metadata.get('document_type', 'unknown')
            
            # Apply structure recognition based on document type
            if document_type == 'application_form':
                return tensorflow_utils.recognize_application_form_structure(extraction_result)
            elif document_type == 'tax_document':
                return tensorflow_utils.recognize_tax_document_structure(extraction_result)
            elif document_type == 'bank_statement':
                return tensorflow_utils.recognize_bank_statement_structure(extraction_result)
            elif document_type == 'identity_document':
                return tensorflow_utils.recognize_identity_document_structure(extraction_result)
            else:
                # Generic structure recognition for unknown document types
                return tensorflow_utils.recognize_generic_structure(extraction_result)
        
        except Exception as e:
            self.logger.warning(f"Structure recognition failed: {str(e)}. Falling back to raw extraction.")
            return extraction_result
    
    def _extract_fields(self, structured_data: Dict[str, Any], metadata: Dict[str, Any]) -> List[ExtractedField]:
        """
        Extract key-value fields from structured data based on document type.
        
        Args:
            structured_data: The structured data with identified forms, tables, and sections
            metadata: Document metadata including classification information
            
        Returns:
            List[ExtractedField]: The extracted fields with values
        """
        try:
            self.logger.info("Extracting key-value fields")
            
            # Get document type from metadata for specialized field extraction
            document_type = metadata.get('document_type', 'unknown')
            
            # Apply field extraction based on document type
            if document_type == 'application_form':
                return text_utils.extract_application_form_fields(structured_data)
            elif document_type == 'tax_document':
                return text_utils.extract_tax_document_fields(structured_data)
            elif document_type == 'bank_statement':
                return text_utils.extract_bank_statement_fields(structured_data)
            elif document_type == 'identity_document':
                return text_utils.extract_identity_document_fields(structured_data)
            else:
                # Generic field extraction for unknown document types
                return text_utils.extract_generic_fields(structured_data)
        
        except Exception as e:
            self.logger.warning(f"Field extraction failed: {str(e)}. Returning empty field list.")
            return []
    
    def _score_field_confidence(self, extracted_fields: List[ExtractedField]) -> List[ExtractedField]:
        """
        Calculate confidence scores for extracted fields.
        
        Args:
            extracted_fields: The extracted fields with values
            
        Returns:
            List[ExtractedField]: The extracted fields with confidence scores
        """
        try:
            self.logger.info("Calculating confidence scores for extracted fields")
            
            # Use confidence service to score each field
            scored_fields = []
            for field in extracted_fields:
                # Calculate confidence based on OCR certainty and field validation
                confidence = tensorflow_utils.calculate_field_confidence(
                    field.value,
                    field.field_type,
                    field.location
                )
                
                # Create a new field with confidence score
                scored_field = ExtractedField(
                    field_id=field.field_id,
                    field_type=field.field_type,
                    value=field.value,
                    confidence=ConfidenceScore(confidence),
                    location=field.location,
                    metadata=field.metadata
                )
                
                # Flag low confidence fields
                if confidence < tensorflow_config.CONFIDENCE_THRESHOLD:
                    scored_field.metadata['requires_review'] = True
                
                scored_fields.append(scored_field)
            
            return scored_fields
        
        except Exception as e:
            self.logger.warning(f"Confidence scoring failed: {str(e)}. Using default confidence values.")
            # Apply default confidence if scoring fails
            for field in extracted_fields:
                field.confidence = ConfidenceScore(0.5)  # Default mid-range confidence
                field.metadata['requires_review'] = True  # Flag for review due to scoring failure
            
            return extracted_fields
    
    def _format_extraction_result(self, scored_fields: List[ExtractedField], metadata: Dict[str, Any]) -> ExtractedData:
        """
        Format the extraction result as structured JSON data.
        
        Args:
            scored_fields: The extracted fields with confidence scores
            metadata: Document metadata including classification information
            
        Returns:
            ExtractedData: The formatted extraction result
        """
        try:
            self.logger.info("Formatting extraction result as JSON")
            
            # Get document type from metadata for specialized JSON formatting
            document_type = metadata.get('document_type', 'unknown')
            
            # Create extraction metadata
            extraction_metadata = {
                'document_id': metadata.get('document_id', 'unknown'),
                'request_id': metadata.get('request_id', 'unknown'),
                'document_type': document_type,
                'extraction_timestamp': time_utils.get_iso_timestamp(),
                'ocr_service_version': app_config.VERSION,
                'requires_review': any(field.metadata.get('requires_review', False) for field in scored_fields)
            }
            
            # Calculate overall confidence score
            if scored_fields:
                overall_confidence = sum(field.confidence.value for field in scored_fields) / len(scored_fields)
                extraction_metadata['overall_confidence'] = overall_confidence
            else:
                extraction_metadata['overall_confidence'] = 0.0
            
            # Create the extraction result
            result = ExtractedData(
                fields=scored_fields,
                metadata=extraction_metadata
            )
            
            return result
        
        except Exception as e:
            self.logger.warning(f"Result formatting failed: {str(e)}. Using simplified format.")
            
            # Create a simplified result if formatting fails
            extraction_metadata = {
                'document_id': metadata.get('document_id', 'unknown'),
                'request_id': metadata.get('request_id', 'unknown'),
                'extraction_timestamp': time_utils.get_iso_timestamp(),
                'ocr_service_version': app_config.VERSION,
                'error': str(e),
                'requires_review': True
            }
            
            return ExtractedData(
                fields=scored_fields,
                metadata=extraction_metadata
            )
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get the current status of the OCR service.
        
        Returns:
            Dict[str, Any]: Service status information
        """
        # Check GPU status
        gpu_info = tensorflow_utils.get_gpu_info()
        
        # Check model status
        models_loaded = hasattr(self, 'typed_model') and hasattr(self, 'handwritten_model') and hasattr(self, 'hybrid_model')
        
        return {
            'service': 'ocr-service',
            'version': app_config.VERSION,
            'status': 'healthy' if models_loaded else 'degraded',
            'gpu_available': bool(gpu_info.get('gpus', [])),
            'gpu_info': gpu_info,
            'models_loaded': models_loaded,
            'timestamp': time_utils.get_iso_timestamp()
        }