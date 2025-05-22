#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Routing Service for the Document Service microservice.

This module handles the routing of classified documents to appropriate OCR processors
based on document type, classification confidence, and document characteristics.
It determines the optimal OCR processing strategy and creates routing metadata
for downstream OCR processors.
"""

import logging
import time
from typing import Dict, Any, Optional, List, Tuple

from ..types.classification import ClassificationResult, ConfidenceScore
from ..config import model_config
from ..utils import validation_utils

# Configure logger
logger = logging.getLogger(__name__)


class DocumentRoutingService:
    """
    Service for routing classified documents to appropriate OCR processors.
    
    This service determines the optimal OCR processing strategy based on document type,
    classification confidence, and document characteristics. It creates routing metadata
    for downstream OCR processors and implements fallback strategies for low-confidence
    classifications.
    """
    
    # Document type to OCR processor mapping
    DOCUMENT_TYPE_PROCESSORS = {
        'loan_application': 'form_ocr',
        'tax_return': 'financial_ocr',
        'bank_statement': 'financial_ocr',
        'pay_stub': 'financial_ocr',
        'identity_document': 'id_ocr',
        'invoice': 'financial_ocr',
        'utility_bill': 'general_ocr',
        'business_license': 'general_ocr',
        'insurance_document': 'general_ocr',
        'credit_report': 'financial_ocr',
        'lease_agreement': 'contract_ocr',
        'articles_of_incorporation': 'contract_ocr',
        'bank_letter': 'general_ocr',
        'financial_statement': 'financial_ocr',
        'other': 'general_ocr'
    }
    
    # Document type to content type mapping (typed, handwritten, mixed)
    DOCUMENT_CONTENT_TYPES = {
        'loan_application': 'mixed',
        'tax_return': 'typed',
        'bank_statement': 'typed',
        'pay_stub': 'typed',
        'identity_document': 'mixed',
        'invoice': 'typed',
        'utility_bill': 'typed',
        'business_license': 'typed',
        'insurance_document': 'typed',
        'credit_report': 'typed',
        'lease_agreement': 'typed',
        'articles_of_incorporation': 'typed',
        'bank_letter': 'typed',
        'financial_statement': 'typed',
        'other': 'mixed'
    }
    
    # Confidence thresholds for routing decisions
    HIGH_CONFIDENCE_THRESHOLD = 0.85  # 85% confidence for automatic processing
    MEDIUM_CONFIDENCE_THRESHOLD = 0.75  # 75% confidence for specialized processing with review flag
    LOW_CONFIDENCE_THRESHOLD = 0.60  # 60% confidence for fallback processing with mandatory review
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the DocumentRoutingService.
        
        Args:
            config: Optional configuration dictionary to override default settings.
        """
        self.config = config or {}
        
        # Override default thresholds if provided in config
        self.high_confidence_threshold = self.config.get(
            'high_confidence_threshold', 
            model_config.CLASSIFICATION_HIGH_CONFIDENCE_THRESHOLD
        )
        self.medium_confidence_threshold = self.config.get(
            'medium_confidence_threshold', 
            model_config.CLASSIFICATION_MEDIUM_CONFIDENCE_THRESHOLD
        )
        self.low_confidence_threshold = self.config.get(
            'low_confidence_threshold', 
            model_config.CLASSIFICATION_LOW_CONFIDENCE_THRESHOLD
        )
        
        # Initialize routing metrics
        self.routing_metrics = {
            'total_routed': 0,
            'high_confidence_routes': 0,
            'medium_confidence_routes': 0,
            'low_confidence_routes': 0,
            'fallback_routes': 0,
            'routing_errors': 0,
            'avg_routing_time_ms': 0,
            'total_routing_time_ms': 0
        }
        
        logger.info("DocumentRoutingService initialized with confidence thresholds: "
                   f"high={self.high_confidence_threshold}, "
                   f"medium={self.medium_confidence_threshold}, "
                   f"low={self.low_confidence_threshold}")
    
    def route_document(self, 
                      document_id: str, 
                      classification_result: ClassificationResult, 
                      document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route a classified document to the appropriate OCR processor.
        
        Args:
            document_id: Unique identifier for the document
            classification_result: Result of document classification
            document_metadata: Metadata about the document (size, format, etc.)
            
        Returns:
            Dictionary containing routing information for downstream OCR processing
        """
        start_time = time.time()
        
        try:
            # Validate inputs
            if not document_id or not classification_result or not document_metadata:
                raise ValueError("Missing required parameters for document routing")
            
            # Extract document type and confidence from classification result
            document_type = classification_result.document_type
            confidence_score = classification_result.confidence
            
            # Validate document type
            if not validation_utils.is_valid_document_type(document_type):
                logger.warning(f"Invalid document type: {document_type}. Using fallback routing.")
                document_type = 'other'
                confidence_score = ConfidenceScore(0.0)  # Force fallback routing
            
            # Determine OCR processor based on document type and confidence
            ocr_processor, review_required, processing_priority = self._determine_ocr_processor(
                document_type, confidence_score, document_metadata
            )
            
            # Determine content type (typed, handwritten, mixed)
            content_type = self._determine_content_type(document_type, document_metadata)
            
            # Create routing metadata
            routing_metadata = self._create_routing_metadata(
                document_id, document_type, ocr_processor, 
                confidence_score, review_required, processing_priority,
                content_type, document_metadata
            )
            
            # Update routing metrics
            self._update_routing_metrics(confidence_score, start_time)
            
            logger.info(f"Document {document_id} routed to {ocr_processor} processor "
                       f"with confidence {confidence_score.value:.2f}, "
                       f"review_required={review_required}, "
                       f"priority={processing_priority}")
            
            return routing_metadata
            
        except Exception as e:
            logger.error(f"Error routing document {document_id}: {str(e)}")
            self.routing_metrics['routing_errors'] += 1
            
            # Create fallback routing metadata for error cases
            return self._create_fallback_routing_metadata(
                document_id, document_metadata
            )
    
    def _determine_ocr_processor(self, 
                                document_type: str, 
                                confidence_score: ConfidenceScore,
                                document_metadata: Dict[str, Any]) -> Tuple[str, bool, str]:
        """
        Determine the appropriate OCR processor based on document type and confidence.
        
        Args:
            document_type: Type of document as determined by classification
            confidence_score: Confidence score of the classification
            document_metadata: Metadata about the document
            
        Returns:
            Tuple containing (ocr_processor, review_required, processing_priority)
        """
        # Get the default OCR processor for this document type
        default_processor = self.DOCUMENT_TYPE_PROCESSORS.get(document_type, 'general_ocr')
        
        # Determine if review is required based on confidence score
        if confidence_score.value >= self.high_confidence_threshold:
            # High confidence - use specialized processor without review
            return default_processor, False, 'high'
        
        elif confidence_score.value >= self.medium_confidence_threshold:
            # Medium confidence - use specialized processor with review flag
            return default_processor, True, 'medium'
        
        elif confidence_score.value >= self.low_confidence_threshold:
            # Low confidence - use specialized processor with mandatory review
            return default_processor, True, 'low'
        
        else:
            # Very low confidence - use general OCR with mandatory review
            return 'general_ocr', True, 'low'
    
    def _determine_content_type(self, 
                              document_type: str, 
                              document_metadata: Dict[str, Any]) -> str:
        """
        Determine the content type (typed, handwritten, mixed) for the document.
        
        Args:
            document_type: Type of document as determined by classification
            document_metadata: Metadata about the document
            
        Returns:
            Content type string ('typed', 'handwritten', or 'mixed')
        """
        # Check if document metadata contains content type information
        if 'content_type' in document_metadata:
            content_type = document_metadata['content_type']
            if content_type in ['typed', 'handwritten', 'mixed']:
                return content_type
        
        # Use default mapping based on document type
        return self.DOCUMENT_CONTENT_TYPES.get(document_type, 'mixed')
    
    def _create_routing_metadata(self,
                               document_id: str,
                               document_type: str,
                               ocr_processor: str,
                               confidence_score: ConfidenceScore,
                               review_required: bool,
                               processing_priority: str,
                               content_type: str,
                               document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create routing metadata for downstream OCR processing.
        
        Args:
            document_id: Unique identifier for the document
            document_type: Type of document as determined by classification
            ocr_processor: Selected OCR processor
            confidence_score: Confidence score of the classification
            review_required: Whether human review is required
            processing_priority: Priority level for processing
            content_type: Content type (typed, handwritten, mixed)
            document_metadata: Original document metadata
            
        Returns:
            Dictionary containing routing metadata
        """
        # Extract relevant fields from document metadata
        file_type = document_metadata.get('file_type', 'unknown')
        file_size = document_metadata.get('file_size', 0)
        page_count = document_metadata.get('page_count', 1)
        source = document_metadata.get('source', 'unknown')
        
        # Create routing metadata
        routing_metadata = {
            'document_id': document_id,
            'routing_id': f"route_{document_id}_{int(time.time())}",
            'document_type': document_type,
            'ocr_processor': ocr_processor,
            'classification_confidence': confidence_score.value,
            'review_required': review_required,
            'processing_priority': processing_priority,
            'content_type': content_type,
            'file_type': file_type,
            'file_size': file_size,
            'page_count': page_count,
            'source': source,
            'routing_timestamp': int(time.time()),
            'routing_version': '1.0',
            'special_instructions': self._generate_special_instructions(
                document_type, confidence_score, content_type
            )
        }
        
        return routing_metadata
    
    def _create_fallback_routing_metadata(self,
                                        document_id: str,
                                        document_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create fallback routing metadata for error cases.
        
        Args:
            document_id: Unique identifier for the document
            document_metadata: Original document metadata
            
        Returns:
            Dictionary containing fallback routing metadata
        """
        # Extract relevant fields from document metadata
        file_type = document_metadata.get('file_type', 'unknown')
        file_size = document_metadata.get('file_size', 0)
        page_count = document_metadata.get('page_count', 1)
        source = document_metadata.get('source', 'unknown')
        
        # Create fallback routing metadata
        fallback_metadata = {
            'document_id': document_id,
            'routing_id': f"fallback_{document_id}_{int(time.time())}",
            'document_type': 'unknown',
            'ocr_processor': 'general_ocr',
            'classification_confidence': 0.0,
            'review_required': True,
            'processing_priority': 'low',
            'content_type': 'mixed',
            'file_type': file_type,
            'file_size': file_size,
            'page_count': page_count,
            'source': source,
            'routing_timestamp': int(time.time()),
            'routing_version': '1.0',
            'special_instructions': 'FALLBACK_ROUTING: Document classification failed. '
                                   'Manual review required.'
        }
        
        return fallback_metadata
    
    def _generate_special_instructions(self,
                                     document_type: str,
                                     confidence_score: ConfidenceScore,
                                     content_type: str) -> str:
        """
        Generate special instructions for OCR processing based on document characteristics.
        
        Args:
            document_type: Type of document
            confidence_score: Confidence score of the classification
            content_type: Content type (typed, handwritten, mixed)
            
        Returns:
            String containing special instructions
        """
        instructions = []
        
        # Add instructions based on confidence score
        if confidence_score.value < self.low_confidence_threshold:
            instructions.append("LOW_CONFIDENCE: Classification uncertain. Verify document type.")
        
        # Add instructions based on content type
        if content_type == 'handwritten':
            instructions.append("HANDWRITTEN: Use handwriting recognition models.")
        elif content_type == 'mixed':
            instructions.append("MIXED_CONTENT: Use hybrid OCR approach.")
        
        # Add document-specific instructions
        if document_type == 'loan_application':
            instructions.append("FORM_EXTRACTION: Extract form fields with labels.")
        elif document_type == 'tax_return':
            instructions.append("TABLE_EXTRACTION: Focus on financial tables and totals.")
        elif document_type == 'identity_document':
            instructions.append("ID_VERIFICATION: Extract and verify identity fields.")
        
        return ' '.join(instructions) if instructions else ''
    
    def _update_routing_metrics(self, confidence_score: ConfidenceScore, start_time: float) -> None:
        """
        Update routing metrics for monitoring and optimization.
        
        Args:
            confidence_score: Confidence score of the classification
            start_time: Start time of the routing operation
        """
        # Calculate routing time in milliseconds
        routing_time_ms = (time.time() - start_time) * 1000
        
        # Update total metrics
        self.routing_metrics['total_routed'] += 1
        self.routing_metrics['total_routing_time_ms'] += routing_time_ms
        self.routing_metrics['avg_routing_time_ms'] = (
            self.routing_metrics['total_routing_time_ms'] / self.routing_metrics['total_routed']
        )
        
        # Update confidence-based metrics
        if confidence_score.value >= self.high_confidence_threshold:
            self.routing_metrics['high_confidence_routes'] += 1
        elif confidence_score.value >= self.medium_confidence_threshold:
            self.routing_metrics['medium_confidence_routes'] += 1
        elif confidence_score.value >= self.low_confidence_threshold:
            self.routing_metrics['low_confidence_routes'] += 1
        else:
            self.routing_metrics['fallback_routes'] += 1
    
    def get_routing_metrics(self) -> Dict[str, Any]:
        """
        Get current routing metrics for monitoring and optimization.
        
        Returns:
            Dictionary containing routing metrics
        """
        return self.routing_metrics
    
    def get_ocr_processor_for_document_type(self, document_type: str) -> str:
        """
        Get the default OCR processor for a given document type.
        
        Args:
            document_type: Type of document
            
        Returns:
            OCR processor name
        """
        return self.DOCUMENT_TYPE_PROCESSORS.get(document_type, 'general_ocr')
    
    def get_content_type_for_document_type(self, document_type: str) -> str:
        """
        Get the default content type for a given document type.
        
        Args:
            document_type: Type of document
            
        Returns:
            Content type (typed, handwritten, mixed)
        """
        return self.DOCUMENT_CONTENT_TYPES.get(document_type, 'mixed')