"""
Type definitions for document metadata, content types, and processing status.

This module provides type definitions for representing documents throughout the
processing pipeline, from initial receipt to classification and routing.
"""

from __future__ import annotations
from enum import Enum, auto
from typing import Dict, List, Optional, Union, ByteString, TypedDict, Any
from datetime import datetime
import uuid


class DocumentType(Enum):
    """Enumeration of document types for classification.
    
    These types represent the different categories of documents that can be 
    processed by the MCA Application Processing System.
    """
    APPLICATION = "application"  # Loan application forms
    TAX_RETURN = "tax_return"  # Tax return documents (1040, W-2, etc.)
    BANK_STATEMENT = "bank_statement"  # Bank account statements
    PAY_STUB = "pay_stub"  # Employment pay stubs
    ID_DOCUMENT = "id_document"  # Identity documents (driver's license, passport)
    OTHER = "other"  # Unclassified or miscellaneous documents


class ProcessingStatus(Enum):
    """Enumeration of document processing statuses.
    
    These statuses track the document's progress through the processing pipeline.
    """
    RECEIVED = "received"  # Initial state when document is first received
    CLASSIFYING = "classifying"  # Document is being classified
    CLASSIFIED = "classified"  # Document has been classified
    PROCESSING = "processing"  # Document is being processed by OCR
    PROCESSED = "processed"  # Document has been processed
    ERROR = "error"  # Error occurred during processing
    REVIEW = "review"  # Document requires manual review
    COMPLETED = "completed"  # Document processing is complete


class DocumentMetadata(TypedDict):
    """Type definition for document metadata.
    
    Contains information about the document such as filename, size, MIME type,
    and other metadata used for processing and tracking.
    """
    id: str  # Unique identifier for the document
    filename: str  # Original filename of the document
    size: int  # Size of the document in bytes
    mime_type: str  # MIME type of the document (e.g., application/pdf)
    created_at: datetime  # Timestamp when the document was created
    updated_at: datetime  # Timestamp when the document was last updated
    classification_confidence: Optional[float]  # Confidence score of classification (0-1)
    ocr_confidence: Optional[float]  # Overall confidence score of OCR extraction (0-1)
    application_id: Optional[str]  # Associated application ID if known
    storage_path: Optional[str]  # Path in S3-compatible storage
    checksum: Optional[str]  # MD5 or SHA-256 checksum for integrity verification
    page_count: Optional[int]  # Number of pages in the document
    tags: Optional[List[str]]  # Custom tags for the document


class DocumentSource(TypedDict):
    """Type definition for document source information.
    
    Contains information about where the document originated from, such as
    email details, upload information, or API submission data.
    """
    source_type: str  # Type of source (email, upload, api, etc.)
    email_id: Optional[str]  # ID of the email if source is email
    email_sender: Optional[str]  # Sender email address if source is email
    email_subject: Optional[str]  # Email subject if source is email
    email_received_at: Optional[datetime]  # When the email was received
    upload_user_id: Optional[str]  # ID of user who uploaded the document
    upload_ip: Optional[str]  # IP address of uploader
    api_client_id: Optional[str]  # API client ID if submitted via API
    submission_id: Optional[str]  # ID of the submission batch
    received_at: datetime  # When the document was received by the system


# Type alias for document binary content
DocumentContent = ByteString


class ClassificationResult(TypedDict):
    """Type definition for document classification results.
    
    Contains the classification outcome including document type and confidence scores.
    """
    document_type: DocumentType  # Classified document type
    confidence: float  # Overall confidence score (0-1)
    confidence_scores: Dict[str, float]  # Confidence scores for each possible type
    features_used: List[str]  # List of features used for classification
    model_version: str  # Version of the classification model used
    classified_at: datetime  # When the classification was performed
    requires_review: bool  # Whether human review is recommended based on confidence


class ProcessingError(TypedDict):
    """Type definition for document processing errors.
    
    Contains information about errors that occurred during document processing.
    """
    error_code: str  # Error code for the error
    error_message: str  # Human-readable error message
    error_timestamp: datetime  # When the error occurred
    error_location: str  # Where in the pipeline the error occurred
    error_details: Optional[Dict[str, Any]]  # Additional error details
    retry_count: int  # Number of retry attempts
    is_recoverable: bool  # Whether the error is recoverable


class Document:
    """Class representing a document in the processing pipeline.
    
    Combines metadata, content, classification results, and processing status
    into a single object that can be passed between services.
    """
    
    def __init__(
        self,
        metadata: DocumentMetadata,
        content: Optional[DocumentContent] = None,
        document_type: Optional[DocumentType] = None,
        status: ProcessingStatus = ProcessingStatus.RECEIVED,
        source: Optional[DocumentSource] = None,
        classification_result: Optional[ClassificationResult] = None,
        processing_error: Optional[ProcessingError] = None
    ):
        """Initialize a new Document instance.
        
        Args:
            metadata: Document metadata information
            content: Binary content of the document (optional)
            document_type: Type of the document if known (optional)
            status: Current processing status (defaults to RECEIVED)
            source: Information about document source (optional)
            classification_result: Classification results if available (optional)
            processing_error: Error information if applicable (optional)
        """
        self.metadata = metadata
        self.content = content
        self.document_type = document_type
        self.status = status
        self.source = source
        self.classification_result = classification_result
        self.processing_error = processing_error
        
        # Generate ID if not provided
        if 'id' not in self.metadata or not self.metadata['id']:
            self.metadata['id'] = str(uuid.uuid4())
            
        # Set timestamps if not provided
        current_time = datetime.utcnow()
        if 'created_at' not in self.metadata or not self.metadata['created_at']:
            self.metadata['created_at'] = current_time
        if 'updated_at' not in self.metadata or not self.metadata['updated_at']:
            self.metadata['updated_at'] = current_time
    
    def update_status(self, new_status: ProcessingStatus) -> None:
        """Update the document's processing status.
        
        Args:
            new_status: The new processing status to set
        """
        self.status = new_status
        self.metadata['updated_at'] = datetime.utcnow()
    
    def set_classification_result(self, result: ClassificationResult) -> None:
        """Set the document's classification result.
        
        Args:
            result: The classification result to set
        """
        self.classification_result = result
        self.document_type = result['document_type']
        self.metadata['classification_confidence'] = result['confidence']
        self.metadata['updated_at'] = datetime.utcnow()
        
        # Update status based on confidence and review requirement
        if result['requires_review']:
            self.update_status(ProcessingStatus.REVIEW)
        else:
            self.update_status(ProcessingStatus.CLASSIFIED)
    
    def set_error(self, error: ProcessingError) -> None:
        """Set an error on the document.
        
        Args:
            error: The error information to set
        """
        self.processing_error = error
        self.update_status(ProcessingStatus.ERROR)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the document to a dictionary representation.
        
        Returns:
            Dict representation of the document
        """
        result = {
            'metadata': self.metadata,
            'status': self.status.value,
        }
        
        if self.document_type:
            result['document_type'] = self.document_type.value
        
        if self.source:
            result['source'] = self.source
        
        if self.classification_result:
            result['classification_result'] = self.classification_result
        
        if self.processing_error:
            result['processing_error'] = self.processing_error
        
        # Don't include content in dict representation for serialization
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Document:
        """Create a Document instance from a dictionary.
        
        Args:
            data: Dictionary containing document data
            
        Returns:
            A new Document instance
        """
        # Convert string status to enum
        status = ProcessingStatus(data.get('status', ProcessingStatus.RECEIVED.value))
        
        # Convert string document_type to enum if present
        document_type = None
        if 'document_type' in data and data['document_type']:
            document_type = DocumentType(data['document_type'])
        
        return cls(
            metadata=data['metadata'],
            document_type=document_type,
            status=status,
            source=data.get('source'),
            classification_result=data.get('classification_result'),
            processing_error=data.get('processing_error')
        )


# Type aliases for collections of documents
DocumentList = List[Document]
DocumentDict = Dict[str, Document]  # Mapping of document ID to Document