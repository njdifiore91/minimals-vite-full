#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Module

This module provides the core OCR processing service that orchestrates the application of
TensorFlow models for text extraction from documents. It handles model loading, selection
of appropriate OCR techniques based on document type, and processing of documents with
GPU acceleration.

The service is designed to achieve 99% data extraction accuracy and process documents
quickly to meet the 5-minute end-to-end requirement for the MCA application processing system.
"""

import time
from typing import Dict, List, Optional, Tuple, Union, Any
import logging
import traceback
import os

# Import from local modules
from ..config import app_config, tensorflow_config
from ..models.model_factory import ModelFactory
from ..models.base_model import BaseModel
from ..types.documents import Document, DocumentType, ProcessingStatus
from ..types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from ..types.models import OCRModelType, ModelResult
from ..types.errors import ServiceError, ErrorCategory, Result
from ..utils import (
    logging_utils, 
    time_utils, 
    tensorflow_utils, 
    image_utils, 
    retry_utils,
    validation_utils,
    text_utils
)


class OCRService:
    """
    Core OCR processing service that orchestrates document text extraction using TensorFlow models.
    
    This service handles the selection and application of appropriate OCR models based on document
    type and content characteristics. It supports typed text, handwritten text, and hybrid document
    processing with GPU acceleration to achieve high accuracy and performance.
    
    The service is designed to achieve 99% data extraction accuracy and process documents
    quickly to meet the 5-minute end-to-end requirement for the MCA application processing system.
    
    Key features:
    - Automatic model selection based on document type and content analysis
    - GPU-accelerated processing with CPU fallback for large documents
    - Confidence scoring for all extracted fields
    - Automatic flagging of low-confidence extractions for human review
    - Comprehensive performance monitoring and optimization
    - Document type-specific processing optimizations
    - Robust error handling and retry logic
    """
    
    def __init__(self):
        """
        Initialize the OCR service with required configurations and models.
        
        Sets up logging, loads TensorFlow configuration, initializes GPU resources,
        and prepares the model factory for OCR model creation.
        
        Raises:
            ServiceError: If initialization fails, particularly if GPU is required but not available
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing OCR Service")
        
        # Load TensorFlow configuration
        self.tf_config = tensorflow_config
        
        # Initialize GPU resources
        self.gpu_available = tensorflow_utils.setup_gpu_environment(
            memory_limit=self.tf_config.gpu_memory_limit,
            allow_growth=self.tf_config.gpu_memory_growth
        )
        
        if not self.gpu_available and self.tf_config.require_gpu:
            error_msg = "GPU acceleration required but no compatible GPU found"
            self.logger.error(error_msg)
            raise ServiceError(
                message=error_msg,
                category=ErrorCategory.CONFIGURATION,
                details={"tf_config": self.tf_config.__dict__}
            )
        
        # Log GPU information
        if self.gpu_available:
            gpu_info = tensorflow_utils.get_gpu_info()
            self.logger.info(f"Using GPU for OCR processing: {gpu_info}")
        else:
            self.logger.warning("No GPU available. Using CPU for OCR processing (slower performance)")
        
        # Initialize model factory
        self.model_factory = ModelFactory()
        
        # Load models in background to speed up first request
        self._preload_models()
        
        self.logger.info("OCR Service initialized successfully")
    
    def _preload_models(self):
        """
        Preload OCR models to improve performance for the first request.
        
        This method loads all OCR models in the background to avoid the initial
        loading delay when processing the first document.
        """
        try:
            self.logger.info("Preloading OCR models...")
            # Preload all model types
            for model_type in OCRModelType:
                self.model_factory.get_model(model_type)
            self.logger.info("OCR models preloaded successfully")
        except Exception as e:
            # Log error but don't fail initialization - models will be loaded on demand
            self.logger.warning(f"Failed to preload OCR models: {str(e)}")
            self.logger.debug(traceback.format_exc())
    
    def process_document(self, document: Document) -> Result[Tuple[ExtractedData, float]]:
        """
        Process a document using appropriate OCR models based on document type and content.
        
        Args:
            document: The document to process, containing metadata and binary content
            
        Returns:
            A Result containing either:
              - A tuple with the extracted data and the total processing time in seconds
              - A ServiceError if processing fails
        """
        start_time = time.time()
        request_id = document.metadata.request_id if hasattr(document.metadata, 'request_id') else None
        self.logger.info(f"Processing document: {document.metadata.filename}", extra={"request_id": request_id})
        
        try:
            # Update document status
            document.processing_status = ProcessingStatus.PROCESSING
            
            # Preprocess document image
            preprocessed_image = self._preprocess_document(document)
            
            # Determine document content type and select appropriate model
            model_type = self._determine_model_type(preprocessed_image, document.document_type)
            self.logger.info(
                f"Selected model type: {model_type.name} for document {document.metadata.filename}",
                extra={"request_id": request_id}
            )
            
            # Get appropriate model from factory
            ocr_model = self.model_factory.get_model(model_type)
            
            # Extract text using selected model
            extraction_result = self._extract_text(ocr_model, preprocessed_image, document)
            
            # Format and validate extraction results
            extracted_data = self._format_extraction_results(extraction_result, document)
            
            # Update document status
            document.processing_status = ProcessingStatus.COMPLETED
            
            # Calculate processing time
            processing_time = time.time() - start_time
            self.logger.info(
                f"Document processing completed in {processing_time:.2f} seconds: {document.metadata.filename}",
                extra={"request_id": request_id}
            )
            
            # Log performance metrics
            self._log_performance_metrics(document, processing_time, extracted_data)
            
            # Check if processing time meets performance requirements
            if processing_time > app_config.max_processing_time_seconds:
                self.logger.warning(
                    f"Document processing exceeded target time: {processing_time:.2f} seconds > "
                    f"{app_config.max_processing_time_seconds} seconds",
                    extra={"request_id": request_id}
                )
            
            return Result.success((extracted_data, processing_time))
            
        except Exception as e:
            # Update document status to error
            document.processing_status = ProcessingStatus.ERROR
            
            # Calculate processing time even for errors
            processing_time = time.time() - start_time
            
            # Log the error with context
            error_msg = f"Error processing document {document.metadata.filename}: {str(e)}"
            self.logger.error(error_msg, extra={"request_id": request_id})
            self.logger.debug(traceback.format_exc(), extra={"request_id": request_id})
            
            # Create service error with context
            error = ServiceError(
                message=error_msg,
                category=ErrorCategory.PROCESSING,
                details={
                    "document_id": document.metadata.document_id,
                    "document_type": document.document_type.name if document.document_type else "UNKNOWN",
                    "processing_time": processing_time,
                    "original_error": str(e),
                    "traceback": traceback.format_exc(),
                    "request_id": request_id
                }
            )
            
            return Result.failure(error)
    
    def _preprocess_document(self, document: Document) -> Any:
        """
        Preprocess the document image for OCR processing.
        
        Applies image normalization, enhancement, and preparation techniques to optimize
        the document for text extraction.
        
        Args:
            document: The document to preprocess
            
        Returns:
            Preprocessed image ready for OCR processing
            
        Raises:
            ServiceError: If preprocessing fails
        """
        request_id = document.metadata.request_id if hasattr(document.metadata, 'request_id') else None
        self.logger.debug(f"Preprocessing document: {document.metadata.filename}", extra={"request_id": request_id})
        
        try:
            # Convert document content to image based on file type
            image = image_utils.convert_to_image(document.content, document.metadata.mime_type)
            
            # Check image quality and dimensions
            quality_score = image_utils.assess_image_quality(image)
            if quality_score < self.tf_config.min_image_quality_score:
                self.logger.warning(
                    f"Low quality document image detected (score: {quality_score}). "
                    f"OCR results may be less accurate.",
                    extra={"request_id": request_id}
                )
            
            # Apply preprocessing pipeline with document-type specific optimizations
            preprocessing_options = self._get_preprocessing_options(document.document_type)
            
            preprocessed = image_utils.preprocess_for_ocr(
                image,
                **preprocessing_options
            )
            
            # Log preprocessing results
            self.logger.debug(
                f"Document preprocessing completed with options: {preprocessing_options}",
                extra={"request_id": request_id}
            )
            
            return preprocessed
        
        except Exception as e:
            error_msg = f"Failed to preprocess document {document.metadata.filename}: {str(e)}"
            self.logger.error(error_msg, extra={"request_id": request_id})
            raise ServiceError(
                message=error_msg,
                category=ErrorCategory.PREPROCESSING,
                details={
                    "document_id": document.metadata.document_id,
                    "mime_type": document.metadata.mime_type,
                    "original_error": str(e),
                    "request_id": request_id
                }
            )
    
    def _get_preprocessing_options(self, document_type: Optional[DocumentType]) -> Dict[str, bool]:
        """
        Get document type-specific preprocessing options.
        
        Different document types benefit from different preprocessing techniques.
        This method returns the optimal preprocessing options for each document type.
        
        Args:
            document_type: The type of document being processed
            
        Returns:
            Dictionary of preprocessing options
        """
        # Default preprocessing options
        options = {
            "deskew": True,
            "denoise": True,
            "normalize": True,
            "enhance_contrast": True,
            "remove_background": False,
            "sharpen": False,
            "binarize": False
        }
        
        # Apply document type-specific optimizations
        if document_type:
            if document_type == DocumentType.ID_DOCUMENT:
                # ID documents often have security features that shouldn't be removed
                options["remove_background"] = False
                options["enhance_contrast"] = True
                options["sharpen"] = True
            
            elif document_type == DocumentType.BANK_STATEMENT:
                # Bank statements often have light text that benefits from contrast enhancement
                options["enhance_contrast"] = True
                options["remove_background"] = True
                
            elif document_type == DocumentType.APPLICATION:
                # Applications may have handwritten text that benefits from less aggressive processing
                options["denoise"] = True
                options["sharpen"] = False
                options["binarize"] = False
                
            elif document_type == DocumentType.TAX_RETURN:
                # Tax returns often have dense text that benefits from background removal
                options["remove_background"] = True
                options["sharpen"] = True
        
        return options
    
    def _determine_model_type(self, image: Any, document_type: Optional[DocumentType]) -> OCRModelType:
        """
        Determine the appropriate OCR model type based on document content and classification.
        
        Analyzes the document image to detect whether it contains typed text, handwritten text,
        or a mixture of both, and selects the appropriate OCR model type accordingly.
        
        Args:
            image: The preprocessed document image
            document_type: The classified document type, if available
            
        Returns:
            The selected OCR model type (TYPED, HANDWRITTEN, or HYBRID)
        """
        # Start with a model type prediction based on document type
        predicted_model_type = None
        
        # Use document type to inform model selection if available
        if document_type:
            # Document types that typically contain handwritten content
            if document_type == DocumentType.APPLICATION:
                # Applications often contain a mix of typed and handwritten content
                predicted_model_type = OCRModelType.HYBRID
                
            elif document_type == DocumentType.ID_DOCUMENT:
                # ID documents often contain both typed and handwritten elements
                predicted_model_type = OCRModelType.HYBRID
                
            elif document_type in [DocumentType.TAX_RETURN, DocumentType.BANK_STATEMENT]:
                # These are typically typed documents
                predicted_model_type = OCRModelType.TYPED
                
            elif document_type == DocumentType.PAY_STUB:
                # Pay stubs are typically typed documents
                predicted_model_type = OCRModelType.TYPED
        
        # If we have a high-confidence prediction based on document type, use it
        # Otherwise, analyze the image content to detect text types
        if predicted_model_type is None or self.tf_config.always_analyze_content:
            # Analyze image to detect text type using TensorFlow text detection model
            has_typed, has_handwritten, confidence = tensorflow_utils.detect_text_types(image)
            
            self.logger.debug(
                f"Text type detection results: typed={has_typed}, handwritten={has_handwritten}, "
                f"confidence={confidence:.2f}"
            )
            
            # Determine model type based on detected text types
            if has_typed and has_handwritten:
                detected_model_type = OCRModelType.HYBRID
            elif has_handwritten:
                detected_model_type = OCRModelType.HANDWRITTEN
            else:
                # Default to typed text model if no handwriting detected
                detected_model_type = OCRModelType.TYPED
            
            # If we had a prediction but detection has high confidence, use detection result
            if predicted_model_type is not None:
                if confidence >= self.tf_config.text_type_confidence_threshold:
                    # Detection has high confidence, override prediction
                    if predicted_model_type != detected_model_type:
                        self.logger.info(
                            f"Overriding predicted model type {predicted_model_type} with detected "
                            f"model type {detected_model_type} (confidence: {confidence:.2f})"
                        )
                    return detected_model_type
                else:
                    # Detection has low confidence, use prediction
                    self.logger.info(
                        f"Using predicted model type {predicted_model_type} due to low detection "
                        f"confidence ({confidence:.2f})"
                    )
                    return predicted_model_type
            else:
                # No prediction, use detection result
                return detected_model_type
        else:
            # Use the high-confidence prediction based on document type
            self.logger.debug(f"Using predicted model type {predicted_model_type} based on document type")
            return predicted_model_type
    
    @retry_utils.retry(max_attempts=3, exceptions=(ServiceError,), 
    exclude_categories=[ErrorCategory.VALIDATION, ErrorCategory.CONFIGURATION])
    def _extract_text(self, model: BaseModel, image: Any, document: Document) -> ModelResult:
        """
        Extract text from the document image using the selected OCR model.
        
        Applies the OCR model to the preprocessed document image and extracts text content
        with confidence scores. Includes retry logic for transient failures.
        
        Args:
            model: The OCR model to use for text extraction
            image: The preprocessed document image
            document: The original document with metadata
            
        Returns:
            Model result containing extracted text and confidence scores
            
        Raises:
            ServiceError: If text extraction fails after retries
        """
        request_id = document.metadata.request_id if hasattr(document.metadata, 'request_id') else None
        self.logger.debug(
            f"Extracting text from document: {document.metadata.filename}", 
            extra={"request_id": request_id}
        )
        
        try:
            # Apply the model to extract text with document type context
            extraction_start = time.time()
            result = model.extract_text(
                image, 
                document_type=document.document_type,
                context={
                    "document_id": document.metadata.document_id,
                    "request_id": request_id,
                    "filename": document.metadata.filename
                }
            )
            extraction_time = time.time() - extraction_start
            
            # Log extraction statistics
            self.logger.info(
                f"Text extraction completed for {document.metadata.filename} in {extraction_time:.2f}s: "
                f"{len(result.extracted_fields)} fields extracted with "
                f"average confidence {result.average_confidence:.2f}",
                extra={"request_id": request_id}
            )
            
            # Check if extraction meets quality thresholds
            if result.average_confidence < self.tf_config.min_acceptable_confidence:
                self.logger.warning(
                    f"Low confidence extraction results ({result.average_confidence:.2f}) for "
                    f"document {document.metadata.filename}. Results may require manual review.",
                    extra={"request_id": request_id}
                )
            
            # Check if extraction time meets performance requirements
            if extraction_time > self.tf_config.extraction_time_warning_threshold:
                self.logger.warning(
                    f"Slow text extraction ({extraction_time:.2f}s) for document "
                    f"{document.metadata.filename}. Consider optimization.",
                    extra={"request_id": request_id}
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Text extraction failed for document {document.metadata.filename}: {str(e)}"
            self.logger.error(error_msg, extra={"request_id": request_id})
            
            # Check if this is a GPU-related error that might benefit from fallback to CPU
            if tensorflow_utils.is_gpu_memory_error(str(e)) and self.gpu_available:
                self.logger.warning(
                    f"GPU memory error detected. Attempting fallback to CPU for document "
                    f"{document.metadata.filename}",
                    extra={"request_id": request_id}
                )
                try:
                    # Temporarily disable GPU for this extraction
                    with tensorflow_utils.cpu_only_context():
                        result = model.extract_text(
                            image, 
                            document_type=document.document_type,
                            context={
                                "document_id": document.metadata.document_id,
                                "request_id": request_id,
                                "filename": document.metadata.filename,
                                "fallback_to_cpu": True
                            }
                        )
                    
                    self.logger.info(
                        f"Successfully extracted text using CPU fallback for document "
                        f"{document.metadata.filename}",
                        extra={"request_id": request_id}
                    )
                    return result
                    
                except Exception as cpu_error:
                    # CPU fallback also failed, raise the original error
                    self.logger.error(
                        f"CPU fallback extraction also failed: {str(cpu_error)}",
                        extra={"request_id": request_id}
                    )
            
            # Raise service error with context for retry mechanism
            raise ServiceError(
                message=error_msg,
                category=ErrorCategory.EXTRACTION,
                details={
                    "document_id": document.metadata.document_id,
                    "model_type": model.model_type.name,
                    "original_error": str(e),
                    "request_id": request_id
                }
            )
    
    def _format_extraction_results(self, result: ModelResult, document: Document) -> ExtractedData:
        """
        Format the extraction results into structured data for downstream processing.
        
        Transforms the raw OCR results into a structured JSON format with field names,
        values, and confidence scores according to document type-specific schemas.
        
        Args:
            result: The model extraction result
            document: The original document with metadata
            
        Returns:
            Structured extracted data in standardized format
            
        Raises:
            ServiceError: If formatting fails
        """
        request_id = document.metadata.request_id if hasattr(document.metadata, 'request_id') else None
        self.logger.debug(
            f"Formatting extraction results for document: {document.metadata.filename}",
            extra={"request_id": request_id}
        )
        
        try:
            # Create extracted data object with basic metadata
            extracted_data = ExtractedData(
                document_id=document.metadata.document_id,
                document_type=document.document_type.name if document.document_type else "UNKNOWN",
                extraction_timestamp=time_utils.get_current_timestamp(),
                average_confidence=result.average_confidence,
                fields={},
                metadata={
                    "model_type": result.model_type.name,
                    "processing_time": result.processing_time,
                    "version": app_config.version,
                    "request_id": request_id,
                    "filename": document.metadata.filename,
                    "mime_type": document.metadata.mime_type,
                    "gpu_accelerated": self.gpu_available and not result.metadata.get("fallback_to_cpu", False)
                }
            )
            
            # Add document-specific schema version based on document type
            if document.document_type:
                schema_version = self._get_schema_version_for_document_type(document.document_type)
                extracted_data.metadata["schema_version"] = schema_version
            
            # Add extracted fields with confidence scores and validation
            for field in result.extracted_fields:
                # Apply field-specific validation and normalization
                normalized_value = self._normalize_field_value(field.value, field.name, document.document_type)
                
                # Calculate if field requires review based on confidence and validation results
                requires_review = field.confidence < self.tf_config.confidence_threshold
                
                # Add field to extracted data
                extracted_data.fields[field.name] = {
                    "value": normalized_value,
                    "raw_value": field.value,  # Keep original value for reference
                    "confidence": field.confidence,
                    "requires_review": requires_review,
                    "position": field.position if hasattr(field, 'position') else None,
                    "page": field.page if hasattr(field, 'page') else 1
                }
            
            # Add document structure information if available
            if hasattr(result, 'document_structure') and result.document_structure:
                extracted_data.metadata["document_structure"] = result.document_structure
            
            # Flag document for review if overall confidence is low or critical fields are missing
            extracted_data.requires_review = self._determine_if_review_required(
                extracted_data, document.document_type
            )
            
            # Validate the extracted data against the expected schema
            self._validate_extracted_data(extracted_data, document.document_type)
            
            return extracted_data
            
        except Exception as e:
            error_msg = f"Failed to format extraction results for document {document.metadata.filename}: {str(e)}"
            self.logger.error(error_msg, extra={"request_id": request_id})
            raise ServiceError(
                message=error_msg,
                category=ErrorCategory.FORMATTING,
                details={
                    "document_id": document.metadata.document_id,
                    "original_error": str(e),
                    "request_id": request_id
                }
            )
    
    def _get_schema_version_for_document_type(self, document_type: DocumentType) -> str:
        """
        Get the schema version for a specific document type.
        
        Different document types may have different schema versions for their
        extracted data format.
        
        Args:
            document_type: The type of document
            
        Returns:
            Schema version string
        """
        # Schema version mapping by document type
        schema_versions = {
            DocumentType.APPLICATION: "1.2",
            DocumentType.TAX_RETURN: "1.1",
            DocumentType.BANK_STATEMENT: "1.3",
            DocumentType.PAY_STUB: "1.0",
            DocumentType.ID_DOCUMENT: "1.1",
            DocumentType.OTHER: "1.0"
        }
        
        return schema_versions.get(document_type, "1.0")
    
    def _normalize_field_value(self, value: str, field_name: str, document_type: Optional[DocumentType]) -> str:
        """
        Normalize and validate a field value based on field name and document type.
        
        Applies field-specific normalization rules to ensure consistent data format
        for downstream processing.
        
        Args:
            value: The raw field value from OCR
            field_name: The name of the field
            document_type: The type of document
            
        Returns:
            Normalized field value
        """
        # Skip normalization for empty values
        if not value or not value.strip():
            return value
        
        # Apply common normalization rules
        normalized = value.strip()
        
        # Apply field-specific normalization
        if "date" in field_name.lower():
            # Normalize date formats
            try:
                normalized = time_utils.normalize_date_string(normalized)
            except ValueError:
                # If date normalization fails, return the original value
                pass
                
        elif "amount" in field_name.lower() or "total" in field_name.lower():
            # Normalize currency amounts
            normalized = normalized.replace("$", "").replace(",", "").strip()
            
        elif "ssn" in field_name.lower() or "social" in field_name.lower():
            # Normalize Social Security Numbers
            normalized = normalized.replace("-", "").replace(" ", "").strip()
            
        elif "phone" in field_name.lower():
            # Normalize phone numbers
            normalized = normalized.replace("-", "").replace("(", "").replace(")", "").replace(" ", "").strip()
            
        elif "ein" in field_name.lower() or "tax_id" in field_name.lower():
            # Normalize Employer Identification Numbers
            normalized = normalized.replace("-", "").replace(" ", "").strip()
        
        return normalized
    
    def _determine_if_review_required(self, extracted_data: ExtractedData, document_type: Optional[DocumentType]) -> bool:
        """
        Determine if the document requires human review based on extraction results.
        
        Checks overall confidence, presence of critical fields, and field-specific
        confidence scores to decide if human review is needed.
        
        Args:
            extracted_data: The extracted data
            document_type: The type of document
            
        Returns:
            True if human review is required, False otherwise
        """
        # Check overall confidence threshold
        if extracted_data.average_confidence < self.tf_config.document_confidence_threshold:
            return True
        
        # If document type is unknown, require review
        if not document_type:
            return True
        
        # Check for missing critical fields based on document type
        critical_fields = self._get_critical_fields_for_document_type(document_type)
        for field in critical_fields:
            if field not in extracted_data.fields:
                # Critical field is missing
                return True
            if extracted_data.fields[field]["requires_review"]:
                # Critical field has low confidence
                return True
        
        # Check if too many fields require review
        fields_requiring_review = sum(1 for field in extracted_data.fields.values() if field["requires_review"])
        total_fields = len(extracted_data.fields)
        
        if total_fields > 0 and (fields_requiring_review / total_fields) > self.tf_config.max_fields_requiring_review_ratio:
            return True
        
        return False
    
    def _get_critical_fields_for_document_type(self, document_type: DocumentType) -> List[str]:
        """
        Get the list of critical fields for a specific document type.
        
        Critical fields are those that must be present and have high confidence
        for the document to be processed automatically without human review.
        
        Args:
            document_type: The type of document
            
        Returns:
            List of critical field names
        """
        # Define critical fields by document type
        critical_fields_map = {
            DocumentType.APPLICATION: [
                "legal_name", "dba_name", "business_address", "business_phone", 
                "tax_id", "requested_amount"
            ],
            DocumentType.TAX_RETURN: [
                "tax_year", "business_name", "ein", "total_income", "taxable_income"
            ],
            DocumentType.BANK_STATEMENT: [
                "account_holder", "account_number", "statement_date", "ending_balance"
            ],
            DocumentType.PAY_STUB: [
                "employee_name", "employer_name", "pay_period", "gross_pay", "net_pay"
            ],
            DocumentType.ID_DOCUMENT: [
                "full_name", "id_number", "expiration_date"
            ],
            DocumentType.OTHER: []
        }
        
        return critical_fields_map.get(document_type, [])
    
    def _validate_extracted_data(self, extracted_data: ExtractedData, document_type: Optional[DocumentType]) -> None:
        """
        Validate the extracted data against the expected schema for the document type.
        
        Ensures that the extracted data meets the structural and content requirements
        for downstream processing.
        
        Args:
            extracted_data: The extracted data to validate
            document_type: The type of document
            
        Raises:
            ServiceError: If validation fails
        """
        # Skip validation for unknown document types
        if not document_type:
            return
        
        try:
            # Validate basic structure
            if not hasattr(extracted_data, 'fields') or not extracted_data.fields:
                raise ValueError("Extracted data must contain fields")
            
            if not hasattr(extracted_data, 'document_id') or not extracted_data.document_id:
                raise ValueError("Extracted data must contain document_id")
            
            # Validate document type-specific schema
            # This would typically use a JSON schema validator in a production system
            # For simplicity, we're just checking critical fields here
            critical_fields = self._get_critical_fields_for_document_type(document_type)
            missing_fields = [field for field in critical_fields if field not in extracted_data.fields]
            
            if missing_fields and not extracted_data.requires_review:
                self.logger.warning(
                    f"Document is missing critical fields {missing_fields} but is not flagged for review. "
                    f"Forcing review flag."
                )
                extracted_data.requires_review = True
                
        except Exception as e:
            # Log validation error but don't fail - just flag for review
            self.logger.warning(f"Extracted data validation failed: {str(e)}")
            extracted_data.requires_review = True
            extracted_data.metadata["validation_error"] = str(e)
    
    def _log_performance_metrics(self, document: Document, processing_time: float, extracted_data: ExtractedData) -> None:
        """
        Log performance metrics for monitoring and optimization.
        
        Records processing time, extraction accuracy, and resource utilization metrics
        for monitoring and performance optimization.
        
        Args:
            document: The processed document
            processing_time: Total processing time in seconds
            extracted_data: The extracted data with confidence scores
        """
        request_id = document.metadata.request_id if hasattr(document.metadata, 'request_id') else None
        
        # Get GPU utilization and memory usage if available
        gpu_metrics = {}
        if self.gpu_available:
            gpu_metrics = {
                "gpu_utilization": tensorflow_utils.get_gpu_utilization(),
                "gpu_memory_used": tensorflow_utils.get_gpu_memory_used(),
                "gpu_memory_total": tensorflow_utils.get_gpu_memory_total()
            }
        
        # Calculate field statistics
        total_fields = len(extracted_data.fields)
        low_confidence_fields = sum(
            1 for field in extracted_data.fields.values() 
            if field["requires_review"]
        )
        
        # Calculate accuracy metrics
        accuracy_metrics = {
            "average_confidence": extracted_data.average_confidence,
            "total_fields": total_fields,
            "low_confidence_fields": low_confidence_fields,
            "low_confidence_percentage": (low_confidence_fields / total_fields * 100) if total_fields > 0 else 0,
            "requires_review": extracted_data.requires_review
        }
        
        # Calculate performance metrics
        performance_metrics = {
            "processing_time": processing_time,
            "processing_time_ms": int(processing_time * 1000),
            "fields_per_second": total_fields / processing_time if processing_time > 0 else 0,
            "meets_sla": processing_time <= app_config.max_processing_time_seconds
        }
        
        # Document metadata
        document_metrics = {
            "document_id": document.metadata.document_id,
            "document_type": document.document_type.name if document.document_type else "UNKNOWN",
            "mime_type": document.metadata.mime_type,
            "file_size_bytes": document.metadata.size if hasattr(document.metadata, 'size') else None,
            "page_count": document.metadata.page_count if hasattr(document.metadata, 'page_count') else 1
        }
        
        # System metrics
        system_metrics = {
            "service_version": app_config.version,
            "environment": app_config.environment,
            "host": os.environ.get("HOSTNAME", "unknown"),
            "timestamp": time_utils.get_current_timestamp()
        }
        
        # Combine all metrics
        metrics = {
            **document_metrics,
            **accuracy_metrics,
            **performance_metrics,
            **gpu_metrics,
            **system_metrics,
            "request_id": request_id
        }
        
        # Log metrics as structured JSON
        self.logger.info(f"Performance metrics: {metrics}", extra={"request_id": request_id})
        
        # Additional logging for monitoring systems
        logging_utils.log_metrics("ocr_processing", metrics)
        
        # Check if we're meeting performance targets
        if not performance_metrics["meets_sla"]:
            self.logger.warning(
                f"Document processing time ({processing_time:.2f}s) exceeds SLA target "
                f"({app_config.max_processing_time_seconds}s)",
                extra={"request_id": request_id}
            )
        
        # Check if we're meeting accuracy targets
        if extracted_data.average_confidence < self.tf_config.target_confidence:
            self.logger.warning(
                f"Document extraction confidence ({extracted_data.average_confidence:.2f}) below target "
                f"({self.tf_config.target_confidence})",
                extra={"request_id": request_id}
            )
        
        # Record metrics for model performance tracking
        self._record_model_performance_metrics(
            document.document_type,
            extracted_data.metadata.get("model_type", "UNKNOWN"),
            accuracy_metrics,
            performance_metrics
        )
    
    def _record_model_performance_metrics(self, document_type: Optional[DocumentType], 
                                         model_type: str, accuracy_metrics: Dict, 
                                         performance_metrics: Dict) -> None:
        """
        Record model performance metrics for long-term tracking and optimization.
        
        Aggregates performance metrics by document type and model type to track
        model performance over time and identify optimization opportunities.
        
        Args:
            document_type: The type of document processed
            model_type: The type of model used for extraction
            accuracy_metrics: Metrics related to extraction accuracy
            performance_metrics: Metrics related to processing performance
        """
        try:
            # In a production system, this would store metrics in a time-series database
            # For this implementation, we'll just log them
            doc_type = document_type.name if document_type else "UNKNOWN"
            
            self.logger.debug(
                f"Model performance metrics - Document Type: {doc_type}, Model Type: {model_type}, "
                f"Confidence: {accuracy_metrics['average_confidence']:.2f}, "
                f"Processing Time: {performance_metrics['processing_time']:.2f}s"
            )
            
            # This would typically update a metrics database or monitoring system
            # For example, using Prometheus, StatsD, or a custom metrics aggregator
            pass
            
        except Exception as e:
            # Don't fail processing if metrics recording fails
            self.logger.warning(f"Failed to record model performance metrics: {str(e)}")