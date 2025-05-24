#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Hybrid Recognition Model for OCR Processing

This module implements a combined TensorFlow model that can process documents
containing both typed and handwritten text. The model intelligently switches
between typed and handwritten recognition algorithms based on text region
classification, optimizing accuracy for mixed-format documents.

Key features:
- Text region classification to determine text type (typed vs handwritten)
- Intelligent model switching based on text characteristics
- Unified confidence scoring across different text types
- Optimized processing pipeline for mixed-format documents

This model is essential for processing mixed-format documents like partially
completed application forms, significantly reducing processing time compared
to running documents through separate models.
"""

import logging
import os
import time
import traceback
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import tensorflow as tf
import cv2

from .base_model import BaseOCRModel
from .typed_text_model import TypedTextModel
from .handwritten_text_model import HandwrittenTextModel
from ..types.config import TensorFlowConfig
from ..types.documents import DocumentContent, DocumentMetadata, DocumentType
from ..types.extraction import ConfidenceScore, ExtractedData, ExtractedField, FieldLocation
from ..types.models import ModelParameters, ModelResult, OCRModelType, TextRegion, TextType
from ..utils.image_utils import (
    normalize_image, preprocess_image, detect_text_regions, crop_region,
    enhance_contrast, deskew_image, sharpen_image, normalize_size
)
from ..utils.logging_utils import get_logger
from ..utils.text_utils import clean_text, normalize_text, correct_ocr_errors


logger = get_logger(__name__)


class HybridRecognitionModel(BaseOCRModel):
    """
    Combined OCR model that can process documents with both typed and handwritten text.
    
    This model intelligently switches between typed and handwritten recognition algorithms
    based on text region classification. It's optimized for mixed-format documents like
    partially completed application forms.
    
    Attributes:
        typed_model (TypedTextModel): Model for processing typed/printed text
        handwritten_model (HandwrittenTextModel): Model for processing handwritten text
        classifier_model (tf.keras.Model): Model for classifying text regions as typed or handwritten
        region_overlap_threshold (float): Threshold for determining region overlaps
        min_region_size (int): Minimum size of text regions to process
        confidence_threshold (float): Minimum confidence threshold for text extraction
    """
    
    def __init__(self, 
                 model_path: str, 
                 config: TensorFlowConfig,
                 parameters: Optional[ModelParameters] = None) -> None:
        """
        Initialize the hybrid recognition model.
        
        Args:
            model_path: Path to the model directory containing all required models
            config: TensorFlow configuration settings
            parameters: Additional model parameters (optional)
        """
        # Initialize base model with hybrid model name
        super().__init__(model_path, "hybrid_recognition_model", config, parameters)
        
        # Set default parameters if none provided
        if parameters is None:
            parameters = {}
        
        # Model paths
        typed_model_path = parameters.get('typed_model_path', f"{model_path}/typed")
        handwritten_model_path = parameters.get('handwritten_model_path', f"{model_path}/handwritten")
        classifier_model_path = parameters.get('classifier_model_path', f"{model_path}/classifier")
        
        # Configuration parameters
        self.region_overlap_threshold = parameters.get('region_overlap_threshold', 0.5)
        self.min_region_size = parameters.get('min_region_size', 100)  # Minimum region size in pixels
        self.confidence_threshold = parameters.get('confidence_threshold', 0.7)
        self.max_regions = parameters.get('max_regions', 50)  # Maximum number of regions to process
        self.use_parallel_processing = parameters.get('use_parallel_processing', True)
        
        # Initialize sub-models with appropriate configurations
        logger.info("Initializing typed text model...")
        typed_config = self._create_model_config(config, "typed")
        self.typed_model = TypedTextModel(typed_model_path, typed_config)
        
        logger.info("Initializing handwritten text model...")
        handwritten_config = self._create_model_config(config, "handwritten")
        self.handwritten_model = HandwrittenTextModel(handwritten_model_path, handwritten_config)
        
        # Initialize text region classifier model
        logger.info("Initializing text region classifier model...")
        self._load_classifier_model(classifier_model_path)
        
        logger.info("Hybrid recognition model initialized successfully")
    
    def _create_model_config(self, base_config: TensorFlowConfig, model_type: str) -> TensorFlowConfig:
        """
        Create a specialized configuration for each sub-model.
        
        This allows for optimizing GPU memory usage between the models.
        
        Args:
            base_config: Base TensorFlow configuration
            model_type: Type of model ("typed" or "handwritten")
            
        Returns:
            Specialized TensorFlow configuration
        """
        # Create a copy of the base configuration
        config_dict = base_config.__dict__.copy()
        
        # Adjust GPU memory limit based on model type
        if model_type == "typed":
            # Typed text models typically need less memory
            config_dict["gpu_memory_limit"] = min(config_dict.get("gpu_memory_limit", 4096), 4096)
        elif model_type == "handwritten":
            # Handwritten models are more complex and need more memory
            config_dict["gpu_memory_limit"] = min(config_dict.get("gpu_memory_limit", 6144), 6144)
        
        # Create a new configuration object
        return TensorFlowConfig(**config_dict)
    
    def _load_classifier_model(self, classifier_path: str) -> None:
        """
        Load the text region classifier model.
        
        This model classifies text regions as either typed or handwritten.
        
        Args:
            classifier_path: Path to the classifier model
            
        Raises:
            RuntimeError: If model loading fails
        """
        try:
            # Load the classifier model
            self.classifier_model = tf.saved_model.load(classifier_path)
            logger.info("Text region classifier model loaded successfully")
        except Exception as e:
            error_msg = f"Failed to load text region classifier model: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def classify_text_region(self, region_image: np.ndarray) -> Tuple[TextType, float]:
        """
        Classify a text region as either typed or handwritten.
        
        Args:
            region_image: Image of the text region to classify
            
        Returns:
            Tuple of (text_type, confidence)
        """
        try:
            # Preprocess the region image for classification
            preprocessed = self._preprocess_for_classification(region_image)
            
            # Add batch dimension
            input_tensor = np.expand_dims(preprocessed, axis=0)
            
            # Run inference with the classifier model
            predictions = self.classifier_model(input_tensor)
            
            # Get the predicted class and confidence
            # Assuming predictions shape is [batch_size, num_classes] where num_classes=2
            # Class 0 = Typed, Class 1 = Handwritten
            if isinstance(predictions, dict) and 'logits' in predictions:
                # Some models return a dictionary with logits
                logits = predictions['logits'].numpy()
                probabilities = tf.nn.softmax(logits, axis=-1).numpy()
            else:
                # Others might return probabilities directly
                probabilities = predictions.numpy()
            
            # Get the class with highest probability
            class_idx = np.argmax(probabilities[0])
            confidence = float(probabilities[0, class_idx])
            
            # Map class index to TextType
            text_type = TextType.TYPED if class_idx == 0 else TextType.HANDWRITTEN
            
            logger.debug(f"Classified region as {text_type.value} with confidence {confidence:.2f}")
            return text_type, confidence
            
        except Exception as e:
            logger.error(f"Error classifying text region: {str(e)}")
            # Default to typed text with low confidence if classification fails
            return TextType.TYPED, 0.5
    
    def _preprocess_for_classification(self, image: np.ndarray) -> np.ndarray:
        """
        Preprocess an image for text type classification.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image ready for classification
        """
        try:
            # Resize to classifier input size (e.g., 224x224 for many CNN models)
            input_size = (224, 224)
            resized = cv2.resize(image, input_size)
            
            # Convert to grayscale if needed
            if len(resized.shape) == 3 and resized.shape[2] == 3:
                grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                # Convert back to 3 channels for model input
                processed = cv2.cvtColor(grayscale, cv2.COLOR_GRAY2RGB)
            elif len(resized.shape) == 2:
                # Convert grayscale to 3 channels for model input
                processed = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
            else:
                processed = resized
            
            # Normalize pixel values to [0, 1]
            normalized = processed.astype(np.float32) / 255.0
            
            return normalized
            
        except Exception as e:
            logger.error(f"Error preprocessing image for classification: {str(e)}")
            # Return original image as fallback
            return image
    
    def detect_and_classify_regions(self, image: np.ndarray) -> List[TextRegion]:
        """
        Detect text regions in the image and classify them as typed or handwritten.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            List of TextRegion objects with classification
        """
        try:
            # Detect text regions in the image
            logger.debug("Detecting text regions in image")
            raw_regions = detect_text_regions(image)
            
            # Filter out very small regions
            filtered_regions = []
            for i, (x, y, w, h) in enumerate(raw_regions):
                if w * h >= self.min_region_size:
                    filtered_regions.append((x, y, w, h))
            
            # Limit the number of regions to process
            if len(filtered_regions) > self.max_regions:
                logger.warning(f"Too many text regions detected ({len(filtered_regions)}). "
                              f"Limiting to {self.max_regions} regions.")
                # Sort regions by size (largest first) and take the top max_regions
                filtered_regions.sort(key=lambda r: r[2] * r[3], reverse=True)
                filtered_regions = filtered_regions[:self.max_regions]
            
            # Process each region
            text_regions = []
            for i, (x, y, w, h) in enumerate(filtered_regions):
                # Crop the region from the image
                region_image = crop_region(image, x, y, w, h)
                
                # Classify the region as typed or handwritten
                text_type, confidence = self.classify_text_region(region_image)
                
                # Create TextRegion object
                region = TextRegion(
                    id=i,
                    bbox=(x, y, w, h),
                    text_type=text_type,
                    classification_confidence=confidence,
                    text="",  # Will be filled later during extraction
                    extraction_confidence=0.0  # Will be filled later during extraction
                )
                
                text_regions.append(region)
            
            logger.info(f"Detected and classified {len(text_regions)} text regions")
            return text_regions
            
        except Exception as e:
            logger.error(f"Error detecting and classifying text regions: {str(e)}")
            return []
    
    def extract_text_from_regions(self, image: np.ndarray, regions: List[TextRegion]) -> List[TextRegion]:
        """
        Extract text from each classified region using the appropriate model.
        
        This method optimizes processing by using parallel execution when appropriate,
        helping to meet the requirement of processing applications in under 5 minutes.
        
        Args:
            image: Input image as numpy array
            regions: List of classified text regions
            
        Returns:
            Updated list of TextRegion objects with extracted text
        """
        try:
            # Process regions in parallel if enabled and we have multiple regions
            if self.use_parallel_processing and len(regions) > 1:
                return self._extract_text_parallel(image, regions)
            else:
                return self._extract_text_sequential(image, regions)
                
        except Exception as e:
            logger.error(f"Error extracting text from regions: {str(e)}")
            return regions
    
    def _extract_text_parallel(self, image: np.ndarray, regions: List[TextRegion]) -> List[TextRegion]:
        """
        Extract text from regions in parallel using ThreadPoolExecutor.
        
        This method significantly improves processing time for documents with many text regions.
        
        Args:
            image: Input image as numpy array
            regions: List of classified text regions
            
        Returns:
            Updated list of TextRegion objects with extracted text
        """
        # Group regions by text type
        typed_regions = [r for r in regions if r.text_type == TextType.TYPED]
        handwritten_regions = [r for r in regions if r.text_type == TextType.HANDWRITTEN]
        
        # Process each type in parallel
        updated_regions = []
        
        # Function to process a single region
        def process_region(region):
            try:
                # Crop the region from the image
                x, y, w, h = region.bbox
                region_image = crop_region(image, x, y, w, h)
                
                # Process based on text type
                if region.text_type == TextType.TYPED:
                    # Apply additional preprocessing for typed text
                    enhanced_image = enhance_contrast(region_image, clip_limit=2.0)
                    deskewed_image = deskew_image(enhanced_image)
                    
                    # Use typed text model
                    result = self.typed_model.extract_text(deskewed_image)
                else:
                    # Apply additional preprocessing for handwritten text
                    enhanced_image = enhance_contrast(region_image, clip_limit=3.0)
                    
                    # Use handwritten text model
                    result = self.handwritten_model.extract_text(enhanced_image)
                
                # Extract results
                extracted_text = result.get("text", "")
                confidence = result.get("confidence", 0.0)
                
                # Update region with extracted text and confidence
                region.text = extracted_text
                region.extraction_confidence = confidence
                
                return region, True
                
            except Exception as e:
                logger.error(f"Error processing region {region.id} in parallel: {str(e)}")
                # Mark as failed but return the region
                region.text = ""
                region.extraction_confidence = 0.0
                return region, False
        
        # Maximum number of workers based on available CPU cores
        max_workers = min(8, (os.cpu_count() or 4))
        
        # Process regions in parallel
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all regions for processing
            future_to_region = {executor.submit(process_region, region): region for region in regions}
            
            # Collect results as they complete
            for future in as_completed(future_to_region):
                try:
                    region, success = future.result()
                    if success and region.extraction_confidence >= self.confidence_threshold and region.text.strip():
                        updated_regions.append(region)
                except Exception as e:
                    logger.error(f"Exception in parallel processing: {str(e)}")
        
        # Sort regions by vertical position (top to bottom)
        updated_regions.sort(key=lambda r: r.bbox[1])
        
        return updated_regions
    
    def _extract_text_sequential(self, image: np.ndarray, regions: List[TextRegion]) -> List[TextRegion]:
        """
        Extract text from regions sequentially.
        
        Args:
            image: Input image as numpy array
            regions: List of classified text regions
            
        Returns:
            Updated list of TextRegion objects with extracted text
        """
        updated_regions = []
        
        # Group regions by text type for batch processing
        typed_regions = [r for r in regions if r.text_type == TextType.TYPED]
        handwritten_regions = [r for r in regions if r.text_type == TextType.HANDWRITTEN]
        
        # Process typed regions
        for region in typed_regions:
            try:
                # Crop the region from the image
                x, y, w, h = region.bbox
                region_image = crop_region(image, x, y, w, h)
                
                # Apply additional preprocessing for typed text
                enhanced_image = enhance_contrast(region_image, clip_limit=2.0)
                deskewed_image = deskew_image(enhanced_image)
                
                # Use typed text model
                result = self.typed_model.extract_text(deskewed_image)
                extracted_text = result.get("text", "")
                confidence = result.get("confidence", 0.0)
                
                # Update region with extracted text and confidence
                region.text = extracted_text
                region.extraction_confidence = confidence
                
                # Skip regions with low confidence or empty text
                if confidence >= self.confidence_threshold and extracted_text.strip():
                    updated_regions.append(region)
                else:
                    logger.debug(f"Skipping low confidence typed region: {confidence:.2f} < {self.confidence_threshold}")
                    
            except Exception as e:
                logger.error(f"Error processing typed region {region.id}: {str(e)}")
                # Keep the region but mark it as failed
                region.text = ""
                region.extraction_confidence = 0.0
                updated_regions.append(region)
        
        # Process handwritten regions
        for region in handwritten_regions:
            try:
                # Crop the region from the image
                x, y, w, h = region.bbox
                region_image = crop_region(image, x, y, w, h)
                
                # Apply additional preprocessing for handwritten text
                enhanced_image = enhance_contrast(region_image, clip_limit=3.0)
                
                # Use handwritten text model
                result = self.handwritten_model.extract_text(enhanced_image)
                extracted_text = result.get("text", "")
                confidence = result.get("confidence", 0.0)
                
                # Update region with extracted text and confidence
                region.text = extracted_text
                region.extraction_confidence = confidence
                
                # Skip regions with low confidence or empty text
                if confidence >= self.confidence_threshold and extracted_text.strip():
                    updated_regions.append(region)
                else:
                    logger.debug(f"Skipping low confidence handwritten region: {confidence:.2f} < {self.confidence_threshold}")
                    
            except Exception as e:
                logger.error(f"Error processing handwritten region {region.id}: {str(e)}")
                # Keep the region but mark it as failed
                region.text = ""
                region.extraction_confidence = 0.0
                updated_regions.append(region)
        
        # Sort regions by vertical position (top to bottom)
        updated_regions.sort(key=lambda r: r.bbox[1])
        
        return updated_regions
    
    def extract_text(self, image: np.ndarray) -> List[Tuple[str, ConfidenceScore]]:
        """
        Extract text from the document image using the hybrid approach.
        
        This method implements the abstract method from BaseOCRModel.
        
        Args:
            image: Preprocessed document image as a numpy array
            
        Returns:
            List of tuples containing extracted text and confidence scores
        """
        try:
            # Detect and classify text regions
            regions = self.detect_and_classify_regions(image)
            
            # Extract text from each region
            processed_regions = self.extract_text_from_regions(image, regions)
            
            # Combine results
            results = []
            for region in processed_regions:
                if region.text and region.extraction_confidence > 0:
                    confidence = ConfidenceScore.from_float(region.extraction_confidence)
                    results.append((region.text, confidence))
            
            return results
            
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            return []
    
    def extract_fields(self, image: np.ndarray, 
                      document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract structured fields from the document image.
        
        This method implements the abstract method from BaseOCRModel.
        
        Args:
            image: Preprocessed document image as a numpy array
            document_metadata: Metadata of the document including type and classification
            
        Returns:
            List of extracted fields with values and confidence scores
        """
        try:
            # Get document type from metadata
            document_type = document_metadata.get("type", DocumentType.APPLICATION)
            
            # Detect and classify text regions
            regions = self.detect_and_classify_regions(image)
            
            # Extract text from each region
            processed_regions = self.extract_text_from_regions(image, regions)
            
            # Extract fields based on document type
            if document_type == DocumentType.APPLICATION:
                return self._extract_application_fields(processed_regions, document_metadata)
            elif document_type == DocumentType.INVOICE:
                return self._extract_invoice_fields(processed_regions, document_metadata)
            elif document_type == DocumentType.BANK_STATEMENT:
                return self._extract_bank_statement_fields(processed_regions, document_metadata)
            else:
                # Default extraction for unknown document types
                return self._extract_generic_fields(processed_regions, document_metadata)
                
        except Exception as e:
            logger.error(f"Error extracting fields: {str(e)}")
            return []
    
    def _extract_application_fields(self, regions: List[TextRegion], 
                                  document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract fields specific to application forms.
        
        Args:
            regions: List of processed text regions
            document_metadata: Document metadata
            
        Returns:
            List of extracted fields
        """
        # Define field patterns to look for in application forms
        field_patterns = {
            "legal_name": [r"legal\s+name[\s:]*([\w\s.,&'-]+)", r"business\s+name[\s:]*([\w\s.,&'-]+)"],
            "dba_name": [r"dba[\s:]*([\w\s.,&'-]+)", r"doing\s+business\s+as[\s:]*([\w\s.,&'-]+)"],
            "ein": [r"ein[\s:]*([0-9]{2}-?[0-9]{7})", r"tax\s+id[\s:]*([0-9]{2}-?[0-9]{7})"],
            "address": [r"address[\s:]*([\w\s.,#'-]+)", r"location[\s:]*([\w\s.,#'-]+)"],
            "phone": [r"phone[\s:]*([0-9()-\s.]+)", r"telephone[\s:]*([0-9()-\s.]+)"],
            "email": [r"email[\s:]*([\w.@-]+)", r"e-mail[\s:]*([\w.@-]+)"],
            "revenue": [r"revenue[\s:]*\$?([0-9,.]+)[kK]?", r"annual\s+sales[\s:]*\$?([0-9,.]+)[kK]?"],
            "years_in_business": [r"years\s+in\s+business[\s:]*([0-9.]+)", r"time\s+in\s+business[\s:]*([0-9.]+)"]
        }
        
        # Extract fields using regex patterns
        extracted_fields = self._extract_fields_with_patterns(regions, field_patterns)
        
        # Create ExtractedField objects
        fields = []
        for field_name, (value, confidence, region_id) in extracted_fields.items():
            # Get region information for field location
            region = next((r for r in regions if r.id == region_id), None)
            
            # Create field location
            if region:
                x, y, w, h = region.bbox
                location = FieldLocation(
                    page=0,  # Assuming single page
                    top=y,
                    left=x,
                    bottom=y + h,
                    right=x + w,
                    width=w,
                    height=h
                )
            else:
                # Default location if region not found
                location = FieldLocation(
                    page=0,
                    top=0,
                    left=0,
                    bottom=0,
                    right=0,
                    width=0,
                    height=0
                )
            
            # Create extracted field
            field = ExtractedField(
                name=field_name,
                value=value,
                confidence=ConfidenceScore.from_float(confidence),
                location=location,
                category="application",
                metadata={
                    "text_type": region.text_type.value if region else "unknown",
                    "extraction_time": datetime.now().isoformat()
                }
            )
            
            fields.append(field)
        
        return fields
    
    def _extract_invoice_fields(self, regions: List[TextRegion], 
                              document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract fields specific to invoices.
        
        Args:
            regions: List of processed text regions
            document_metadata: Document metadata
            
        Returns:
            List of extracted fields
        """
        # Define field patterns for invoices
        field_patterns = {
            "invoice_number": [r"invoice\s+(?:no|number|#)[\s:]*([\w-]+)", r"inv\s+(?:no|number|#)[\s:]*([\w-]+)"],
            "invoice_date": [r"invoice\s+date[\s:]*([\w\s.,/-]+)", r"date[\s:]*([\w\s.,/-]+)"],
            "due_date": [r"due\s+date[\s:]*([\w\s.,/-]+)", r"payment\s+due[\s:]*([\w\s.,/-]+)"],
            "total_amount": [r"total[\s:]*\$?([0-9,.]+)", r"amount\s+due[\s:]*\$?([0-9,.]+)"],
            "vendor_name": [r"from[\s:]*([\w\s.,&'-]+)", r"vendor[\s:]*([\w\s.,&'-]+)"],
            "customer_name": [r"to[\s:]*([\w\s.,&'-]+)", r"bill\s+to[\s:]*([\w\s.,&'-]+)"]
        }
        
        # Extract fields using regex patterns
        extracted_fields = self._extract_fields_with_patterns(regions, field_patterns)
        
        # Create ExtractedField objects (similar to application fields)
        fields = []
        for field_name, (value, confidence, region_id) in extracted_fields.items():
            # Get region information for field location
            region = next((r for r in regions if r.id == region_id), None)
            
            # Create field location
            if region:
                x, y, w, h = region.bbox
                location = FieldLocation(
                    page=0,  # Assuming single page
                    top=y,
                    left=x,
                    bottom=y + h,
                    right=x + w,
                    width=w,
                    height=h
                )
            else:
                # Default location if region not found
                location = FieldLocation(
                    page=0,
                    top=0,
                    left=0,
                    bottom=0,
                    right=0,
                    width=0,
                    height=0
                )
            
            # Create extracted field
            field = ExtractedField(
                name=field_name,
                value=value,
                confidence=ConfidenceScore.from_float(confidence),
                location=location,
                category="invoice",
                metadata={
                    "text_type": region.text_type.value if region else "unknown",
                    "extraction_time": datetime.now().isoformat()
                }
            )
            
            fields.append(field)
        
        return fields
    
    def _extract_bank_statement_fields(self, regions: List[TextRegion], 
                                     document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract fields specific to bank statements.
        
        Args:
            regions: List of processed text regions
            document_metadata: Document metadata
            
        Returns:
            List of extracted fields
        """
        # Define field patterns for bank statements
        field_patterns = {
            "account_number": [r"account\s+(?:no|number|#)[\s:]*([\w-]+)", r"acct\s+(?:no|number|#)[\s:]*([\w-]+)"],
            "statement_date": [r"statement\s+date[\s:]*([\w\s.,/-]+)", r"period[\s:]*([\w\s.,/-]+)"],
            "opening_balance": [r"opening\s+balance[\s:]*\$?([0-9,.]+)", r"beginning\s+balance[\s:]*\$?([0-9,.]+)"],
            "closing_balance": [r"closing\s+balance[\s:]*\$?([0-9,.]+)", r"ending\s+balance[\s:]*\$?([0-9,.]+)"],
            "bank_name": [r"bank\s+name[\s:]*([\w\s.,&'-]+)", r"([\w\s.,&'-]+)\s+bank"],
            "customer_name": [r"customer[\s:]*([\w\s.,&'-]+)", r"account\s+holder[\s:]*([\w\s.,&'-]+)"]
        }
        
        # Extract fields using regex patterns
        extracted_fields = self._extract_fields_with_patterns(regions, field_patterns)
        
        # Create ExtractedField objects (similar to application fields)
        fields = []
        for field_name, (value, confidence, region_id) in extracted_fields.items():
            # Get region information for field location
            region = next((r for r in regions if r.id == region_id), None)
            
            # Create field location
            if region:
                x, y, w, h = region.bbox
                location = FieldLocation(
                    page=0,  # Assuming single page
                    top=y,
                    left=x,
                    bottom=y + h,
                    right=x + w,
                    width=w,
                    height=h
                )
            else:
                # Default location if region not found
                location = FieldLocation(
                    page=0,
                    top=0,
                    left=0,
                    bottom=0,
                    right=0,
                    width=0,
                    height=0
                )
            
            # Create extracted field
            field = ExtractedField(
                name=field_name,
                value=value,
                confidence=ConfidenceScore.from_float(confidence),
                location=location,
                category="bank_statement",
                metadata={
                    "text_type": region.text_type.value if region else "unknown",
                    "extraction_time": datetime.now().isoformat()
                }
            )
            
            fields.append(field)
        
        return fields
    
    def _extract_generic_fields(self, regions: List[TextRegion], 
                              document_metadata: DocumentMetadata) -> List[ExtractedField]:
        """
        Extract generic fields for unknown document types.
        
        Args:
            regions: List of processed text regions
            document_metadata: Document metadata
            
        Returns:
            List of extracted fields
        """
        # For generic documents, we'll extract key-value pairs based on common patterns
        field_patterns = {
            "name": [r"name[\s:]*([\w\s.,&'-]+)"],
            "date": [r"date[\s:]*([\w\s.,/-]+)"],
            "amount": [r"amount[\s:]*\$?([0-9,.]+)", r"total[\s:]*\$?([0-9,.]+)"],
            "id": [r"id[\s:]*([\w-]+)", r"number[\s:]*([\w-]+)"],
            "address": [r"address[\s:]*([\w\s.,#'-]+)"],
            "phone": [r"phone[\s:]*([0-9()-\s.]+)"],
            "email": [r"email[\s:]*([\w.@-]+)"]
        }
        
        # Extract fields using regex patterns
        extracted_fields = self._extract_fields_with_patterns(regions, field_patterns)
        
        # Create ExtractedField objects
        fields = []
        for field_name, (value, confidence, region_id) in extracted_fields.items():
            # Get region information for field location
            region = next((r for r in regions if r.id == region_id), None)
            
            # Create field location
            if region:
                x, y, w, h = region.bbox
                location = FieldLocation(
                    page=0,  # Assuming single page
                    top=y,
                    left=x,
                    bottom=y + h,
                    right=x + w,
                    width=w,
                    height=h
                )
            else:
                # Default location if region not found
                location = FieldLocation(
                    page=0,
                    top=0,
                    left=0,
                    bottom=0,
                    right=0,
                    width=0,
                    height=0
                )
            
            # Create extracted field
            field = ExtractedField(
                name=field_name,
                value=value,
                confidence=ConfidenceScore.from_float(confidence),
                location=location,
                category="generic",
                metadata={
                    "text_type": region.text_type.value if region else "unknown",
                    "extraction_time": datetime.now().isoformat()
                }
            )
            
            fields.append(field)
        
        return fields
    
    def _extract_fields_with_patterns(self, regions: List[TextRegion], 
                                    field_patterns: Dict[str, List[str]]) -> Dict[str, Tuple[str, float, int]]:
        """
        Extract fields from text regions using regex patterns.
        
        Args:
            regions: List of processed text regions
            field_patterns: Dictionary of field names and their regex patterns
            
        Returns:
            Dictionary of field names and their extracted values, confidences, and region IDs
        """
        import re
        
        # Initialize results dictionary
        extracted_fields = {}
        
        # Process each region
        for region in regions:
            # Skip empty regions
            if not region.text:
                continue
            
            # Check each field pattern
            for field_name, patterns in field_patterns.items():
                # Skip if field already extracted with high confidence
                if field_name in extracted_fields and extracted_fields[field_name][1] > 0.8:
                    continue
                
                # Try each pattern for this field
                for pattern in patterns:
                    match = re.search(pattern, region.text, re.IGNORECASE)
                    if match:
                        value = match.group(1).strip()
                        confidence = region.extraction_confidence
                        
                        # Store or update the field if it has higher confidence
                        if field_name not in extracted_fields or confidence > extracted_fields[field_name][1]:
                            extracted_fields[field_name] = (value, confidence, region.id)
                        
                        break  # Found a match, no need to try other patterns
        
        return extracted_fields
    
    def process_document(self, document_content: DocumentContent, 
                        document_metadata: DocumentMetadata) -> ModelResult:
        """
        Process a document to extract text and structured fields using the hybrid approach.
        
        This method overrides the process_document method from BaseOCRModel to implement
        the hybrid processing approach. It's optimized to meet the requirement of processing
        applications in under 5 minutes from receipt to completion as specified in section 0.1.2.
        
        Args:
            document_content: Binary content of the document
            document_metadata: Metadata of the document
            
        Returns:
            ModelResult containing extracted data and processing metadata
        """
        start_time = datetime.now()
        
        try:
            # Preprocess the document
            logger.info(f"Preprocessing document {document_metadata.get('id', '')}")
            preprocessed_image = self.preprocess_document(document_content, document_metadata)
            
            # Detect and classify text regions
            logger.info("Detecting and classifying text regions")
            regions = self.detect_and_classify_regions(preprocessed_image)
            
            # Log region statistics
            typed_count = sum(1 for r in regions if r.text_type == TextType.TYPED)
            handwritten_count = sum(1 for r in regions if r.text_type == TextType.HANDWRITTEN)
            logger.info(f"Detected {len(regions)} regions: {typed_count} typed, {handwritten_count} handwritten")
            
            # Extract text from each region
            logger.info("Extracting text from regions")
            processed_regions = self.extract_text_from_regions(preprocessed_image, regions)
            
            # Log processing statistics
            successful_regions = sum(1 for r in processed_regions if r.text)
            logger.info(f"Successfully extracted text from {successful_regions} of {len(processed_regions)} regions")
            
            # Extract fields based on document type
            document_type = document_metadata.get("type", DocumentType.APPLICATION)
            logger.info(f"Extracting fields for document type: {document_type}")
            
            if document_type == DocumentType.APPLICATION:
                extracted_fields = self._extract_application_fields(processed_regions, document_metadata)
            elif document_type == DocumentType.INVOICE:
                extracted_fields = self._extract_invoice_fields(processed_regions, document_metadata)
            elif document_type == DocumentType.BANK_STATEMENT:
                extracted_fields = self._extract_bank_statement_fields(processed_regions, document_metadata)
            else:
                extracted_fields = self._extract_generic_fields(processed_regions, document_metadata)
            
            # Log field extraction statistics
            logger.info(f"Extracted {len(extracted_fields)} fields from document")
            
            # Calculate overall confidence score
            confidence_scores = [field.confidence for field in extracted_fields]
            overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
            
            # Check if confidence meets the 99% accuracy requirement
            if overall_confidence < 0.99:
                logger.warning(f"Document confidence {overall_confidence:.2f} is below the 99% accuracy requirement")
            
            # Combine all extracted text
            all_text = [region.text for region in processed_regions if region.text]
            
            # Calculate processing time
            processing_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            
            # Check if processing time meets the 5-minute requirement
            if processing_time_ms > 300000:  # 5 minutes = 300,000 ms
                logger.warning(f"Document processing time {processing_time_ms/1000:.2f}s exceeds the 5-minute requirement")
            
            # Format results
            extracted_data = ExtractedData(
                fields=extracted_fields,
                text=all_text,
                confidence=overall_confidence,
                metadata={
                    "model_name": self.model_name,
                    "model_version": self.model_version,
                    "document_id": document_metadata.get("id", ""),
                    "document_type": document_metadata.get("type", ""),
                    "processing_time_ms": processing_time_ms,
                    "regions_detected": len(regions),
                    "regions_processed": len(processed_regions),
                    "typed_regions": sum(1 for r in processed_regions if r.text_type == TextType.TYPED),
                    "handwritten_regions": sum(1 for r in processed_regions if r.text_type == TextType.HANDWRITTEN),
                    "requires_verification": overall_confidence < 0.99,
                    "extraction_timestamp": datetime.now().isoformat()
                }
            )
            
            # Create model result
            result = ModelResult(
                success=True,
                data=extracted_data,
                error=None,
                processing_time_ms=processing_time_ms
            )
            
            logger.info(
                f"Successfully processed document {document_metadata.get('id', '')} "
                f"with hybrid model (confidence: {overall_confidence:.2f}, time: {processing_time_ms/1000:.2f}s)"
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process document: {str(e)}"
            logger.error(error_msg)
            
            # Create error result
            result = ModelResult(
                success=False,
                data=None,
                error={
                    "message": error_msg,
                    "type": type(e).__name__,
                    "stack_trace": str(e.__traceback__)
                },
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
            
            return result
    
    def get_region_statistics(self, image: np.ndarray) -> Dict[str, Any]:
        """
        Get statistics about text regions in the document.
        
        This method is useful for analyzing the document composition and
        understanding the distribution of typed vs handwritten content.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Dictionary of statistics about text regions
        """
        try:
            # Detect and classify text regions
            regions = self.detect_and_classify_regions(image)
            
            # Count typed and handwritten regions
            typed_count = sum(1 for r in regions if r.text_type == TextType.TYPED)
            handwritten_count = sum(1 for r in regions if r.text_type == TextType.HANDWRITTEN)
            
            # Calculate area covered by each type
            total_area = image.shape[0] * image.shape[1]
            typed_area = sum(r.bbox[2] * r.bbox[3] for r in regions if r.text_type == TextType.TYPED)
            handwritten_area = sum(r.bbox[2] * r.bbox[3] for r in regions if r.text_type == TextType.HANDWRITTEN)
            
            # Calculate percentages
            typed_percentage = (typed_area / total_area) * 100 if total_area > 0 else 0
            handwritten_percentage = (handwritten_area / total_area) * 100 if total_area > 0 else 0
            
            # Create statistics dictionary
            stats = {
                "total_regions": len(regions),
                "typed_regions": typed_count,
                "handwritten_regions": handwritten_count,
                "typed_percentage": typed_percentage,
                "handwritten_percentage": handwritten_percentage,
                "mixed_document": typed_count > 0 and handwritten_count > 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting region statistics: {str(e)}")
            return {
                "error": str(e),
                "total_regions": 0,
                "typed_regions": 0,
                "handwritten_regions": 0,
                "typed_percentage": 0,
                "handwritten_percentage": 0,
                "mixed_document": False
            }
    
    def visualize_regions(self, image: np.ndarray) -> np.ndarray:
        """
        Create a visualization of detected and classified text regions.
        
        This method is useful for debugging and understanding how the model
        is segmenting and classifying the document.
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Visualization image with colored bounding boxes
        """
        try:
            # Make a copy of the image for visualization
            if len(image.shape) == 2:  # Grayscale
                vis_image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
            else:  # Already color
                vis_image = image.copy()
            
            # Detect and classify text regions
            regions = self.detect_and_classify_regions(image)
            
            # Draw bounding boxes for each region
            for region in regions:
                x, y, w, h = region.bbox
                
                # Choose color based on text type (green for typed, blue for handwritten)
                if region.text_type == TextType.TYPED:
                    color = (0, 255, 0)  # Green
                else:
                    color = (255, 0, 0)  # Blue
                
                # Draw rectangle
                cv2.rectangle(vis_image, (x, y), (x + w, y + h), color, 2)
                
                # Add confidence text
                conf_text = f"{region.classification_confidence:.2f}"
                cv2.putText(vis_image, conf_text, (x, y - 5), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
            
            return vis_image
            
        except Exception as e:
            logger.error(f"Error visualizing regions: {str(e)}")
            return image