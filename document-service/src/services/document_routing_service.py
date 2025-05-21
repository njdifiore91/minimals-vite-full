#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Routing Service for the Document Service microservice.

This module handles the routing of classified documents to appropriate OCR processors
based on document type, classification confidence, and document characteristics.
It determines the optimal OCR processing strategy and creates routing metadata for
downstream OCR processors.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any, Union

# Import types
from ..types.documents import Document, DocumentType, ProcessingStatus
from ..types.classification import ClassificationResult, ConfidenceScore
from ..types.messages import MessagePayload, MessageHeaders
from ..types.errors import ServiceError, Result

# Import utilities
from ..utils.logging_utils import log_with_context
from ..utils.time_utils import get_current_timestamp
from ..utils.error_utils import create_service_error

# Import configuration
from ..config.model_config import CONFIDENCE_THRESHOLDS


class DocumentRoutingService:
    """
    Service for routing classified documents to appropriate OCR processors.
    
    This service determines the optimal OCR processing strategy based on document type,
    classification confidence, and document characteristics. It creates routing metadata
    for downstream OCR processors and implements fallback strategies for uncertain
    classifications.
    """
    
    def __init__(self, queue_service=None, storage_service=None):
        """
        Initialize the DocumentRoutingService.
        
        Args:
            queue_service: Service for publishing messages to RabbitMQ
            storage_service: Service for storing documents and metadata in S3
        """
        self.logger = logging.getLogger(__name__)
        self.queue_service = queue_service
        self.storage_service = storage_service
        
        # Default confidence threshold (can be overridden by config)
        self.confidence_threshold = 0.75
        
        # Load confidence thresholds from configuration
        self._load_confidence_thresholds()
        
        # OCR processor routing map
        self.ocr_processor_map = {
            DocumentType.APPLICATION: "application_processor",
            DocumentType.TAX_RETURN: "tax_document_processor",
            DocumentType.BANK_STATEMENT: "financial_document_processor",
            DocumentType.PAY_STUB: "financial_document_processor",
            DocumentType.ID_DOCUMENT: "identity_document_processor",
            DocumentType.OTHER: "general_document_processor"
        }
        
        # Document characteristics map for OCR strategy selection
        self.document_characteristics_map = {
            "typed": "typed_text_ocr",
            "handwritten": "handwritten_text_ocr",
            "mixed": "hybrid_ocr",
            "default": "hybrid_ocr"  # Default to most comprehensive OCR
        }
    
    def _load_confidence_thresholds(self) -> None:
        """
        Load confidence thresholds from configuration.
        
        This method loads document type-specific confidence thresholds from the
        configuration, falling back to the default threshold if not specified.
        """
        try:
            # Get default threshold from configuration
            if hasattr(CONFIDENCE_THRESHOLDS, 'DEFAULT'):
                self.confidence_threshold = CONFIDENCE_THRESHOLDS.DEFAULT
                
            # Get document type-specific thresholds
            self.type_confidence_thresholds = {}
            for doc_type in DocumentType:
                threshold_key = f"{doc_type.name}_THRESHOLD"
                if hasattr(CONFIDENCE_THRESHOLDS, threshold_key):
                    self.type_confidence_thresholds[doc_type] = getattr(CONFIDENCE_THRESHOLDS, threshold_key)
                else:
                    self.type_confidence_thresholds[doc_type] = self.confidence_threshold
        except Exception as e:
            self.logger.warning(f"Failed to load confidence thresholds from configuration: {str(e)}. Using defaults.")
            # Set default thresholds if configuration loading fails
            self.type_confidence_thresholds = {doc_type: self.confidence_threshold for doc_type in DocumentType}
    
    def route_document(self, document: Document, classification_result: ClassificationResult) -> Result[Dict[str, Any]]:
        """
        Route a classified document to the appropriate OCR processor.
        
        This method determines the optimal OCR processing strategy based on document type,
        classification confidence, and document characteristics. It creates routing metadata
        for downstream OCR processors and implements fallback strategies for uncertain
        classifications.
        
        Args:
            document: The document to route
            classification_result: The classification result from the classification service
            
        Returns:
            Result containing routing metadata or error
        """
        try:
            self.logger.info(f"Routing document {document.id} with classification {classification_result.document_type}")
            
            # Extract document type and confidence from classification result
            doc_type = classification_result.document_type
            confidence = classification_result.confidence
            
            # Get confidence threshold for this document type
            threshold = self.type_confidence_thresholds.get(doc_type, self.confidence_threshold)
            
            # Determine if human review is needed based on confidence
            needs_human_review = confidence < threshold
            
            # Determine document characteristics for OCR strategy selection
            doc_characteristics = self._determine_document_characteristics(document, classification_result)
            
            # Select OCR processor based on document type
            ocr_processor = self.ocr_processor_map.get(doc_type, "general_document_processor")
            
            # Select OCR strategy based on document characteristics
            ocr_strategy = self.document_characteristics_map.get(
                doc_characteristics, 
                self.document_characteristics_map["default"]
            )
            
            # Create routing metadata
            routing_metadata = self._create_routing_metadata(
                document=document,
                classification_result=classification_result,
                ocr_processor=ocr_processor,
                ocr_strategy=ocr_strategy,
                needs_human_review=needs_human_review,
                doc_characteristics=doc_characteristics
            )
            
            # Log routing decision
            log_with_context(
                self.logger,
                "info",
                f"Document {document.id} routed to {ocr_processor} using {ocr_strategy}",
                extra={
                    "document_id": document.id,
                    "document_type": doc_type.name if doc_type else "UNKNOWN",
                    "confidence": confidence,
                    "ocr_processor": ocr_processor,
                    "ocr_strategy": ocr_strategy,
                    "needs_human_review": needs_human_review
                }
            )
            
            # Update document metadata with routing information
            if self.storage_service:
                self._update_document_metadata(document, routing_metadata)
            
            # Publish routing message to OCR service
            if self.queue_service:
                self._publish_routing_message(document, routing_metadata)
            
            return Result.success(routing_metadata)
            
        except Exception as e:
            error = create_service_error(
                service="DocumentRoutingService",
                operation="route_document",
                message=f"Failed to route document {document.id}: {str(e)}",
                exception=e
            )
            self.logger.error(f"Error routing document: {error}")
            return Result.failure(error)
    
    def _determine_document_characteristics(self, document: Document, classification_result: ClassificationResult) -> str:
        """
        Determine document characteristics for OCR strategy selection.
        
        This method analyzes the document and classification result to determine
        the document characteristics (typed, handwritten, mixed) for selecting
        the appropriate OCR strategy.
        
        Args:
            document: The document to analyze
            classification_result: The classification result
            
        Returns:
            Document characteristics ("typed", "handwritten", "mixed", or "default")
        """
        # Extract document characteristics from classification result if available
        if hasattr(classification_result, 'document_characteristics'):
            return classification_result.document_characteristics
        
        # Default characteristics based on document type
        doc_type = classification_result.document_type
        
        # Default characteristics mapping
        type_to_characteristics = {
            DocumentType.APPLICATION: "mixed",  # Applications often contain both typed and handwritten content
            DocumentType.TAX_RETURN: "typed",  # Tax returns are typically typed/printed
            DocumentType.BANK_STATEMENT: "typed",  # Bank statements are typically typed/printed
            DocumentType.PAY_STUB: "typed",  # Pay stubs are typically typed/printed
            DocumentType.ID_DOCUMENT: "mixed",  # ID documents often contain both typed and handwritten content
            DocumentType.OTHER: "mixed"  # Default to mixed for unknown document types
        }
        
        # Get default characteristics for this document type
        return type_to_characteristics.get(doc_type, "mixed")
    
    def _create_routing_metadata(self, document: Document, classification_result: ClassificationResult, 
                               ocr_processor: str, ocr_strategy: str, needs_human_review: bool,
                               doc_characteristics: str) -> Dict[str, Any]:
        """
        Create routing metadata for downstream OCR processors.
        
        This method creates a metadata dictionary containing routing information
        for downstream OCR processors, including document type, confidence scores,
        processing hints, and routing decisions.
        
        Args:
            document: The document being routed
            classification_result: The classification result
            ocr_processor: The selected OCR processor
            ocr_strategy: The selected OCR strategy
            needs_human_review: Whether human review is needed
            doc_characteristics: Document characteristics
            
        Returns:
            Routing metadata dictionary
        """
        # Create base metadata
        metadata = {
            "document_id": document.id,
            "routing_timestamp": get_current_timestamp(),
            "routing_service_version": "1.0.0",
            "routing_decisions": {
                "ocr_processor": ocr_processor,
                "ocr_strategy": ocr_strategy,
                "needs_human_review": needs_human_review,
                "priority": "high" if needs_human_review else "normal"
            },
            "document_metadata": {
                "document_type": classification_result.document_type.name if classification_result.document_type else "UNKNOWN",
                "document_characteristics": doc_characteristics,
                "page_count": getattr(document, 'page_count', 1),
                "file_size": getattr(document, 'file_size', 0),
                "mime_type": getattr(document, 'mime_type', "application/pdf")
            },
            "classification_metadata": {
                "confidence": classification_result.confidence,
                "classification_model": getattr(classification_result, 'model_name', "unknown"),
                "classification_version": getattr(classification_result, 'model_version', "unknown"),
                "alternative_types": self._get_alternative_types(classification_result)
            }
        }
        
        # Add processing hints based on document type
        metadata["processing_hints"] = self._generate_processing_hints(
            document_type=classification_result.document_type,
            doc_characteristics=doc_characteristics,
            confidence=classification_result.confidence
        )
        
        return metadata
    
    def _get_alternative_types(self, classification_result: ClassificationResult) -> List[Dict[str, Any]]:
        """
        Get alternative document types for borderline classifications.
        
        For low-confidence classifications, this method extracts alternative
        document types from the classification result to help OCR processors
        handle borderline cases.
        
        Args:
            classification_result: The classification result
            
        Returns:
            List of alternative document types with confidence scores
        """
        alternatives = []
        
        # Check if alternative_types is available in classification_result
        if hasattr(classification_result, 'alternative_types') and classification_result.alternative_types:
            for alt_type, alt_confidence in classification_result.alternative_types.items():
                alternatives.append({
                    "type": alt_type.name if isinstance(alt_type, DocumentType) else str(alt_type),
                    "confidence": alt_confidence
                })
        
        return alternatives
    
    def _generate_processing_hints(self, document_type: DocumentType, 
                                 doc_characteristics: str, confidence: float) -> Dict[str, Any]:
        """
        Generate processing hints for OCR processors based on document type and characteristics.
        
        This method creates processing hints that help OCR processors optimize their
        extraction strategies for specific document types and characteristics.
        
        Args:
            document_type: The document type
            doc_characteristics: Document characteristics
            confidence: Classification confidence
            
        Returns:
            Dictionary of processing hints
        """
        # Base processing hints
        hints = {
            "expected_content_type": doc_characteristics,
            "confidence_level": "high" if confidence >= 0.9 else "medium" if confidence >= 0.75 else "low"
        }
        
        # Add document type-specific hints
        if document_type == DocumentType.APPLICATION:
            hints.update({
                "form_detection": True,
                "signature_detection": True,
                "table_detection": True,
                "expected_fields": [
                    "applicant_name", "business_name", "address", "phone", "email",
                    "tax_id", "requested_amount", "business_type", "signature"
                ]
            })
        elif document_type == DocumentType.TAX_RETURN:
            hints.update({
                "form_detection": True,
                "table_detection": True,
                "expected_fields": [
                    "taxpayer_name", "tax_id", "tax_year", "income", "deductions",
                    "tax_due", "filing_status"
                ]
            })
        elif document_type == DocumentType.BANK_STATEMENT:
            hints.update({
                "table_detection": True,
                "expected_fields": [
                    "account_holder", "account_number", "bank_name", "statement_period",
                    "opening_balance", "closing_balance", "transactions"
                ]
            })
        elif document_type == DocumentType.PAY_STUB:
            hints.update({
                "table_detection": True,
                "expected_fields": [
                    "employee_name", "employer_name", "pay_period", "gross_pay",
                    "net_pay", "deductions", "year_to_date"
                ]
            })
        elif document_type == DocumentType.ID_DOCUMENT:
            hints.update({
                "id_detection": True,
                "expected_fields": [
                    "full_name", "id_number", "date_of_birth", "issue_date",
                    "expiration_date", "address"
                ]
            })
        else:  # DocumentType.OTHER or unknown
            hints.update({
                "form_detection": True,
                "table_detection": True,
                "general_text_extraction": True
            })
        
        return hints
    
    def _update_document_metadata(self, document: Document, routing_metadata: Dict[str, Any]) -> None:
        """
        Update document metadata in storage with routing information.
        
        This method updates the document metadata in S3 storage with routing
        information for tracking and audit purposes.
        
        Args:
            document: The document being routed
            routing_metadata: The routing metadata
        """
        try:
            # Create metadata update with routing information
            metadata_update = {
                "routing_info": {
                    "timestamp": routing_metadata["routing_timestamp"],
                    "ocr_processor": routing_metadata["routing_decisions"]["ocr_processor"],
                    "ocr_strategy": routing_metadata["routing_decisions"]["ocr_strategy"],
                    "needs_human_review": routing_metadata["routing_decisions"]["needs_human_review"]
                },
                "processing_status": ProcessingStatus.ROUTING_COMPLETE.name
            }
            
            # Update document metadata in storage
            self.storage_service.update_document_metadata(document.id, metadata_update)
            
            self.logger.debug(f"Updated document {document.id} metadata with routing information")
        except Exception as e:
            self.logger.warning(f"Failed to update document {document.id} metadata: {str(e)}")
    
    def _publish_routing_message(self, document: Document, routing_metadata: Dict[str, Any]) -> None:
        """
        Publish routing message to OCR service via RabbitMQ.
        
        This method creates and publishes a message to the OCR service with
        routing information and document details.
        
        Args:
            document: The document being routed
            routing_metadata: The routing metadata
        """
        try:
            # Create message payload
            payload = {
                "document_id": document.id,
                "storage_path": getattr(document, 'storage_path', None),
                "routing_metadata": routing_metadata,
                "timestamp": get_current_timestamp()
            }
            
            # Create message headers
            headers = {
                "document_type": routing_metadata["document_metadata"]["document_type"],
                "ocr_processor": routing_metadata["routing_decisions"]["ocr_processor"],
                "ocr_strategy": routing_metadata["routing_decisions"]["ocr_strategy"],
                "priority": routing_metadata["routing_decisions"]["priority"]
            }
            
            # Determine routing key based on document type and processor
            routing_key = f"ocr.{routing_metadata['routing_decisions']['ocr_processor']}"
            
            # Publish message to OCR service
            self.queue_service.publish_message(
                exchange="mca.documents",
                routing_key=routing_key,
                payload=payload,
                headers=headers
            )
            
            self.logger.info(f"Published routing message for document {document.id} to OCR service")
        except Exception as e:
            self.logger.error(f"Failed to publish routing message for document {document.id}: {str(e)}")