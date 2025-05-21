"""
Type definitions for document metadata, content types, and processing status.

This module provides type definitions for representing documents throughout the OCR
processing pipeline, from receipt to text extraction and result formatting.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Union, ByteString, Any
from datetime import datetime
import uuid


class DocumentType(Enum):
    """Enumeration of supported document types for OCR processing."""
    APPLICATION = "application"
    TAX_RETURN = "tax_return"
    BANK_STATEMENT = "bank_statement"
    PAY_STUB = "pay_stub"
    ID_DOCUMENT = "id_document"
    OTHER = "other"


class ProcessingStatus(Enum):
    """Enumeration of document processing statuses throughout the OCR pipeline."""
    RECEIVED = "received"  # Document has been received but not yet processed
    QUEUED = "queued"  # Document is queued for OCR processing
    PROCESSING = "processing"  # Document is currently being processed
    COMPLETED = "completed"  # Document has been successfully processed
    FAILED = "failed"  # Document processing has failed
    MANUAL_REVIEW = "manual_review"  # Document requires manual review


class DocumentMetadata:
    """Metadata for a document in the OCR processing pipeline."""
    
    def __init__(
        self,
        filename: str,
        size: int,
        mime_type: str,
        created_at: datetime = None,
        updated_at: datetime = None,
        document_id: str = None,
        document_type: DocumentType = None,
        classification_confidence: float = None,
        s3_path: str = None,
        additional_metadata: Dict[str, Any] = None
    ):
        """Initialize document metadata.
        
        Args:
            filename: Original filename of the document
            size: Size of the document in bytes
            mime_type: MIME type of the document (e.g., 'application/pdf')
            created_at: Timestamp when the document was created
            updated_at: Timestamp when the document was last updated
            document_id: Unique identifier for the document
            document_type: Type of document (APPLICATION, TAX_RETURN, etc.)
            classification_confidence: Confidence score of document classification (0.0-1.0)
            s3_path: Path to the document in S3 storage
            additional_metadata: Additional metadata key-value pairs
        """
        self.filename = filename
        self.size = size
        self.mime_type = mime_type
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.document_id = document_id or str(uuid.uuid4())
        self.document_type = document_type
        self.classification_confidence = classification_confidence
        self.s3_path = s3_path
        self.additional_metadata = additional_metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation.
        
        Returns:
            Dictionary representation of metadata
        """
        result = {
            "filename": self.filename,
            "size": self.size,
            "mime_type": self.mime_type,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "document_id": self.document_id,
            "additional_metadata": self.additional_metadata
        }
        
        if self.document_type:
            result["document_type"] = self.document_type.value
            
        if self.classification_confidence is not None:
            result["classification_confidence"] = self.classification_confidence
            
        if self.s3_path:
            result["s3_path"] = self.s3_path
            
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentMetadata':
        """Create DocumentMetadata instance from dictionary.
        
        Args:
            data: Dictionary containing metadata fields
            
        Returns:
            DocumentMetadata instance
        """
        created_at = datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at")
        updated_at = datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at")
        
        document_type = None
        if "document_type" in data and data["document_type"]:
            try:
                document_type = DocumentType(data["document_type"])
            except ValueError:
                # Handle invalid document type
                pass
        
        return cls(
            filename=data["filename"],
            size=data["size"],
            mime_type=data["mime_type"],
            created_at=created_at,
            updated_at=updated_at,
            document_id=data.get("document_id"),
            document_type=document_type,
            classification_confidence=data.get("classification_confidence"),
            s3_path=data.get("s3_path"),
            additional_metadata=data.get("additional_metadata", {})
        )


# Type alias for document binary content
DocumentContent = ByteString


class DocumentSource:
    """Information about the source of a document."""
    
    def __init__(
        self,
        source_type: str,  # 'email', 'upload', 'api', etc.
        source_id: str = None,  # Email ID, upload session ID, API request ID, etc.
        source_metadata: Dict[str, Any] = None,  # Additional source-specific metadata
        received_at: datetime = None  # When the document was received
    ):
        """Initialize document source information.
        
        Args:
            source_type: Type of source (email, upload, api, etc.)
            source_id: Identifier for the source
            source_metadata: Additional metadata about the source
            received_at: When the document was received
        """
        self.source_type = source_type
        self.source_id = source_id
        self.source_metadata = source_metadata or {}
        self.received_at = received_at or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert source information to dictionary representation.
        
        Returns:
            Dictionary representation of source information
        """
        return {
            "source_type": self.source_type,
            "source_id": self.source_id,
            "source_metadata": self.source_metadata,
            "received_at": self.received_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentSource':
        """Create DocumentSource instance from dictionary.
        
        Args:
            data: Dictionary containing source information
            
        Returns:
            DocumentSource instance
        """
        received_at = datetime.fromisoformat(data["received_at"]) if isinstance(data.get("received_at"), str) else data.get("received_at")
        
        return cls(
            source_type=data["source_type"],
            source_id=data.get("source_id"),
            source_metadata=data.get("source_metadata", {}),
            received_at=received_at
        )


class Document:
    """Complete document representation including metadata, content, and processing information."""
    
    def __init__(
        self,
        metadata: DocumentMetadata,
        content: Optional[DocumentContent] = None,
        source: Optional[DocumentSource] = None,
        processing_status: ProcessingStatus = ProcessingStatus.RECEIVED,
        extracted_data: Optional[Dict[str, Any]] = None,
        confidence_scores: Optional[Dict[str, float]] = None,
        processing_history: Optional[List[Dict[str, Any]]] = None
    ):
        """Initialize document.
        
        Args:
            metadata: Document metadata
            content: Binary content of the document (may be None if only metadata is needed)
            source: Information about the document source
            processing_status: Current processing status of the document
            extracted_data: Data extracted from the document by OCR
            confidence_scores: Confidence scores for extracted fields
            processing_history: History of processing events for this document
        """
        self.metadata = metadata
        self.content = content
        self.source = source
        self.processing_status = processing_status
        self.extracted_data = extracted_data or {}
        self.confidence_scores = confidence_scores or {}
        self.processing_history = processing_history or []
    
    def add_processing_event(self, event_type: str, details: Dict[str, Any] = None) -> None:
        """Add a processing event to the document's history.
        
        Args:
            event_type: Type of processing event
            details: Additional details about the event
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "details": details or {}
        }
        self.processing_history.append(event)
        self.metadata.updated_at = datetime.now()
    
    def update_status(self, status: ProcessingStatus) -> None:
        """Update the document's processing status.
        
        Args:
            status: New processing status
        """
        self.processing_status = status
        self.add_processing_event("status_change", {"new_status": status.value})
    
    def to_dict(self, include_content: bool = False) -> Dict[str, Any]:
        """Convert document to dictionary representation.
        
        Args:
            include_content: Whether to include binary content in the result
            
        Returns:
            Dictionary representation of document
        """
        result = {
            "metadata": self.metadata.to_dict(),
            "processing_status": self.processing_status.value,
            "processing_history": self.processing_history,
            "extracted_data": self.extracted_data,
            "confidence_scores": self.confidence_scores
        }
        
        if self.source:
            result["source"] = self.source.to_dict()
            
        if include_content and self.content:
            # Note: Binary content would need to be base64 encoded for JSON serialization
            # This is just a placeholder for the actual implementation
            result["content"] = "<binary_content>"
            
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], content: Optional[DocumentContent] = None) -> 'Document':
        """Create Document instance from dictionary.
        
        Args:
            data: Dictionary containing document data
            content: Binary content of the document (optional)
            
        Returns:
            Document instance
        """
        metadata = DocumentMetadata.from_dict(data["metadata"])
        
        source = None
        if "source" in data:
            source = DocumentSource.from_dict(data["source"])
        
        processing_status = ProcessingStatus.RECEIVED
        if "processing_status" in data:
            try:
                processing_status = ProcessingStatus(data["processing_status"])
            except ValueError:
                # Handle invalid processing status
                pass
        
        return cls(
            metadata=metadata,
            content=content,
            source=source,
            processing_status=processing_status,
            extracted_data=data.get("extracted_data", {}),
            confidence_scores=data.get("confidence_scores", {}),
            processing_history=data.get("processing_history", [])
        )