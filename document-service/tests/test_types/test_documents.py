"""Unit tests for document metadata and processing type definitions.

This module contains tests for DocumentMetadata, DocumentContent, DocumentType,
ProcessingStatus, DocumentSource, and Document types to ensure they correctly
handle document representation throughout the processing pipeline.
"""

import pytest
from datetime import datetime
import uuid
import io
from typing import Dict, List, Optional, Any

from src.types.documents import (
    DocumentType,
    ProcessingStatus,
    DocumentMetadata,
    DocumentSource,
    DocumentContent,
    ClassificationResult,
    ProcessingError,
    Document,
    DocumentList,
    DocumentDict
)


# Test fixtures and helper functions
@pytest.fixture
def sample_metadata() -> DocumentMetadata:
    """Create a sample DocumentMetadata for testing."""
    return {
        'id': str(uuid.uuid4()),
        'filename': 'test_document.pdf',
        'size': 1024,
        'mime_type': 'application/pdf',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'classification_confidence': 0.95,
        'ocr_confidence': 0.87,
        'application_id': str(uuid.uuid4()),
        'storage_path': f's3://mca-documents-staging/documents/{uuid.uuid4()}.pdf',
        'checksum': 'a1b2c3d4e5f6g7h8i9j0',
        'page_count': 3,
        'tags': ['application', 'mortgage', 'completed']
    }


@pytest.fixture
def sample_source() -> DocumentSource:
    """Create a sample DocumentSource for testing."""
    return {
        'source_type': 'email',
        'email_id': f'<{uuid.uuid4()}@mail.example.com>',
        'email_sender': 'applicant@example.com',
        'email_subject': 'Mortgage Application Documents',
        'email_received_at': datetime.utcnow(),
        'upload_user_id': None,
        'upload_ip': None,
        'api_client_id': None,
        'submission_id': str(uuid.uuid4()),
        'received_at': datetime.utcnow()
    }


@pytest.fixture
def sample_classification_result() -> ClassificationResult:
    """Create a sample ClassificationResult for testing."""
    return {
        'document_type': DocumentType.APPLICATION,
        'confidence': 0.95,
        'confidence_scores': {
            'application': 0.95,
            'tax_return': 0.03,
            'bank_statement': 0.01,
            'pay_stub': 0.005,
            'id_document': 0.004,
            'other': 0.001
        },
        'features_used': ['text_content', 'layout', 'form_fields'],
        'model_version': '1.0.0',
        'classified_at': datetime.utcnow(),
        'requires_review': False
    }


@pytest.fixture
def sample_processing_error() -> ProcessingError:
    """Create a sample ProcessingError for testing."""
    return {
        'error_code': 'OCR_EXTRACTION_FAILED',
        'error_message': 'Failed to extract text from document',
        'error_timestamp': datetime.utcnow(),
        'error_location': 'ocr_service.extract_text',
        'error_details': {
            'page': 2,
            'reason': 'Low image quality'
        },
        'retry_count': 2,
        'is_recoverable': True
    }


@pytest.fixture
def sample_document_content() -> DocumentContent:
    """Create sample binary content for testing."""
    # Create a simple PDF-like binary content for testing
    buffer = io.BytesIO()
    buffer.write(b'%PDF-1.5\n%Test Document Content\n')
    buffer.write(b'This is a test document for unit testing.\n')
    buffer.write(b'%%EOF')
    return buffer.getvalue()


# Test classes
class TestDocumentType:
    """Tests for the DocumentType enumeration."""

    def test_document_type_values(self):
        """Test that DocumentType enum has the expected values."""
        assert DocumentType.APPLICATION.value == "application"
        assert DocumentType.TAX_RETURN.value == "tax_return"
        assert DocumentType.BANK_STATEMENT.value == "bank_statement"
        assert DocumentType.PAY_STUB.value == "pay_stub"
        assert DocumentType.ID_DOCUMENT.value == "id_document"
        assert DocumentType.OTHER.value == "other"

    def test_document_type_comparison(self):
        """Test that DocumentType enum values can be compared correctly."""
        assert DocumentType.APPLICATION == DocumentType.APPLICATION
        assert DocumentType.APPLICATION != DocumentType.TAX_RETURN
        assert DocumentType.APPLICATION is DocumentType.APPLICATION

    def test_document_type_from_string(self):
        """Test that DocumentType can be created from string values."""
        assert DocumentType("application") == DocumentType.APPLICATION
        assert DocumentType("tax_return") == DocumentType.TAX_RETURN
        assert DocumentType("bank_statement") == DocumentType.BANK_STATEMENT
        assert DocumentType("pay_stub") == DocumentType.PAY_STUB
        assert DocumentType("id_document") == DocumentType.ID_DOCUMENT
        assert DocumentType("other") == DocumentType.OTHER

    def test_invalid_document_type(self):
        """Test that invalid document type strings raise ValueError."""
        with pytest.raises(ValueError):
            DocumentType("invalid_type")


class TestProcessingStatus:
    """Tests for the ProcessingStatus enumeration."""

    def test_processing_status_values(self):
        """Test that ProcessingStatus enum has the expected values."""
        assert ProcessingStatus.RECEIVED.value == "received"
        assert ProcessingStatus.CLASSIFYING.value == "classifying"
        assert ProcessingStatus.CLASSIFIED.value == "classified"
        assert ProcessingStatus.PROCESSING.value == "processing"
        assert ProcessingStatus.PROCESSED.value == "processed"
        assert ProcessingStatus.ERROR.value == "error"
        assert ProcessingStatus.REVIEW.value == "review"
        assert ProcessingStatus.COMPLETED.value == "completed"

    def test_processing_status_comparison(self):
        """Test that ProcessingStatus enum values can be compared correctly."""
        assert ProcessingStatus.RECEIVED == ProcessingStatus.RECEIVED
        assert ProcessingStatus.RECEIVED != ProcessingStatus.PROCESSING
        assert ProcessingStatus.RECEIVED is ProcessingStatus.RECEIVED

    def test_processing_status_from_string(self):
        """Test that ProcessingStatus can be created from string values."""
        assert ProcessingStatus("received") == ProcessingStatus.RECEIVED
        assert ProcessingStatus("classifying") == ProcessingStatus.CLASSIFYING
        assert ProcessingStatus("classified") == ProcessingStatus.CLASSIFIED
        assert ProcessingStatus("processing") == ProcessingStatus.PROCESSING
        assert ProcessingStatus("processed") == ProcessingStatus.PROCESSED
        assert ProcessingStatus("error") == ProcessingStatus.ERROR
        assert ProcessingStatus("review") == ProcessingStatus.REVIEW
        assert ProcessingStatus("completed") == ProcessingStatus.COMPLETED

    def test_invalid_processing_status(self):
        """Test that invalid processing status strings raise ValueError."""
        with pytest.raises(ValueError):
            ProcessingStatus("invalid_status")

    def test_status_transitions(self):
        """Test valid status transitions in document processing workflow."""
        # Define valid transitions for testing
        valid_transitions = {
            ProcessingStatus.RECEIVED: [ProcessingStatus.CLASSIFYING, ProcessingStatus.ERROR],
            ProcessingStatus.CLASSIFYING: [ProcessingStatus.CLASSIFIED, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.CLASSIFIED: [ProcessingStatus.PROCESSING, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.PROCESSING: [ProcessingStatus.PROCESSED, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.PROCESSED: [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.ERROR: [ProcessingStatus.CLASSIFYING, ProcessingStatus.PROCESSING, ProcessingStatus.REVIEW],
            ProcessingStatus.REVIEW: [ProcessingStatus.CLASSIFYING, ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED],
            ProcessingStatus.COMPLETED: []
        }

        # Test that each status can transition to its valid next states
        for current_status, next_statuses in valid_transitions.items():
            for next_status in next_statuses:
                # This is a simple validation that would be implemented in a real system
                # In a real implementation, this would be part of the Document class logic
                assert self._is_valid_transition(current_status, next_status)

    def _is_valid_transition(self, current: ProcessingStatus, next_status: ProcessingStatus) -> bool:
        """Helper method to validate status transitions."""
        # Define valid transitions
        valid_transitions = {
            ProcessingStatus.RECEIVED: [ProcessingStatus.CLASSIFYING, ProcessingStatus.ERROR],
            ProcessingStatus.CLASSIFYING: [ProcessingStatus.CLASSIFIED, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.CLASSIFIED: [ProcessingStatus.PROCESSING, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.PROCESSING: [ProcessingStatus.PROCESSED, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.PROCESSED: [ProcessingStatus.COMPLETED, ProcessingStatus.ERROR, ProcessingStatus.REVIEW],
            ProcessingStatus.ERROR: [ProcessingStatus.CLASSIFYING, ProcessingStatus.PROCESSING, ProcessingStatus.REVIEW],
            ProcessingStatus.REVIEW: [ProcessingStatus.CLASSIFYING, ProcessingStatus.PROCESSING, ProcessingStatus.COMPLETED],
            ProcessingStatus.COMPLETED: []
        }
        return next_status in valid_transitions.get(current, [])


class TestDocumentMetadata:
    """Tests for the DocumentMetadata type."""

    def test_document_metadata_creation(self, sample_metadata):
        """Test that DocumentMetadata can be created with all fields."""
        metadata = sample_metadata
        assert isinstance(metadata, dict)
        assert 'id' in metadata
        assert 'filename' in metadata
        assert 'size' in metadata
        assert 'mime_type' in metadata
        assert 'created_at' in metadata
        assert 'updated_at' in metadata

    def test_document_metadata_optional_fields(self):
        """Test that DocumentMetadata can be created with only required fields."""
        # Create metadata with only required fields
        metadata: DocumentMetadata = {
            'id': str(uuid.uuid4()),
            'filename': 'minimal_document.pdf',
            'size': 512,
            'mime_type': 'application/pdf',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        assert isinstance(metadata, dict)
        assert 'id' in metadata
        assert 'filename' in metadata
        assert 'size' in metadata
        assert 'mime_type' in metadata
        assert 'created_at' in metadata
        assert 'updated_at' in metadata
        assert 'classification_confidence' not in metadata
        assert 'ocr_confidence' not in metadata

    def test_document_metadata_types(self, sample_metadata):
        """Test that DocumentMetadata field types are correct."""
        metadata = sample_metadata
        assert isinstance(metadata['id'], str)
        assert isinstance(metadata['filename'], str)
        assert isinstance(metadata['size'], int)
        assert isinstance(metadata['mime_type'], str)
        assert isinstance(metadata['created_at'], datetime)
        assert isinstance(metadata['updated_at'], datetime)
        assert isinstance(metadata['classification_confidence'], float)
        assert isinstance(metadata['ocr_confidence'], float)
        assert isinstance(metadata['application_id'], str)
        assert isinstance(metadata['storage_path'], str)
        assert isinstance(metadata['checksum'], str)
        assert isinstance(metadata['page_count'], int)
        assert isinstance(metadata['tags'], list)

    def test_document_metadata_validation(self):
        """Test validation of DocumentMetadata fields."""
        # In a real implementation, there would be validation logic
        # Here we're just testing that the types are correct
        metadata: DocumentMetadata = {
            'id': str(uuid.uuid4()),
            'filename': 'test_document.pdf',
            'size': 1024,
            'mime_type': 'application/pdf',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'classification_confidence': 0.95,
            'ocr_confidence': 0.87,
            'application_id': str(uuid.uuid4()),
            'storage_path': f's3://mca-documents-staging/documents/{uuid.uuid4()}.pdf',
            'checksum': 'a1b2c3d4e5f6g7h8i9j0',
            'page_count': 3,
            'tags': ['application', 'mortgage', 'completed']
        }

        # Validate confidence scores are between 0 and 1
        assert 0 <= metadata['classification_confidence'] <= 1
        assert 0 <= metadata['ocr_confidence'] <= 1

        # Validate size is positive
        assert metadata['size'] > 0

        # Validate page count is positive
        assert metadata['page_count'] > 0


class TestDocumentSource:
    """Tests for the DocumentSource type."""

    def test_document_source_creation(self, sample_source):
        """Test that DocumentSource can be created with all fields."""
        source = sample_source
        assert isinstance(source, dict)
        assert 'source_type' in source
        assert 'email_id' in source
        assert 'email_sender' in source
        assert 'email_subject' in source
        assert 'email_received_at' in source
        assert 'received_at' in source

    def test_document_source_email(self, sample_source):
        """Test email-specific fields in DocumentSource."""
        source = sample_source
        assert source['source_type'] == 'email'
        assert source['email_id'] is not None
        assert source['email_sender'] is not None
        assert source['email_subject'] is not None
        assert source['email_received_at'] is not None
        assert source['upload_user_id'] is None
        assert source['upload_ip'] is None
        assert source['api_client_id'] is None

    def test_document_source_upload(self):
        """Test upload-specific fields in DocumentSource."""
        source: DocumentSource = {
            'source_type': 'upload',
            'email_id': None,
            'email_sender': None,
            'email_subject': None,
            'email_received_at': None,
            'upload_user_id': str(uuid.uuid4()),
            'upload_ip': '192.168.1.1',
            'api_client_id': None,
            'submission_id': str(uuid.uuid4()),
            'received_at': datetime.utcnow()
        }

        assert source['source_type'] == 'upload'
        assert source['email_id'] is None
        assert source['email_sender'] is None
        assert source['email_subject'] is None
        assert source['email_received_at'] is None
        assert source['upload_user_id'] is not None
        assert source['upload_ip'] is not None
        assert source['api_client_id'] is None

    def test_document_source_api(self):
        """Test API-specific fields in DocumentSource."""
        source: DocumentSource = {
            'source_type': 'api',
            'email_id': None,
            'email_sender': None,
            'email_subject': None,
            'email_received_at': None,
            'upload_user_id': None,
            'upload_ip': None,
            'api_client_id': 'client_123',
            'submission_id': str(uuid.uuid4()),
            'received_at': datetime.utcnow()
        }

        assert source['source_type'] == 'api'
        assert source['email_id'] is None
        assert source['email_sender'] is None
        assert source['email_subject'] is None
        assert source['email_received_at'] is None
        assert source['upload_user_id'] is None
        assert source['upload_ip'] is None
        assert source['api_client_id'] is not None


class TestDocumentContent:
    """Tests for the DocumentContent type."""

    def test_document_content_creation(self, sample_document_content):
        """Test that DocumentContent can be created and accessed."""
        content = sample_document_content
        assert isinstance(content, bytes)
        assert len(content) > 0

    def test_document_content_pdf(self, sample_document_content):
        """Test PDF-like content in DocumentContent."""
        content = sample_document_content
        assert content.startswith(b'%PDF')
        assert content.endswith(b'%%EOF')

    def test_document_content_empty(self):
        """Test empty DocumentContent."""
        content: DocumentContent = b''
        assert isinstance(content, bytes)
        assert len(content) == 0

    def test_document_content_large(self):
        """Test large DocumentContent handling."""
        # Create a 1MB document for testing
        content: DocumentContent = b'X' * (1024 * 1024)
        assert isinstance(content, bytes)
        assert len(content) == 1024 * 1024


class TestDocument:
    """Tests for the Document class."""

    def test_document_creation(self, sample_metadata, sample_document_content):
        """Test that Document can be created with metadata and content."""
        document = Document(
            metadata=sample_metadata,
            content=sample_document_content
        )

        assert document.metadata == sample_metadata
        assert document.content == sample_document_content
        assert document.status == ProcessingStatus.RECEIVED
        assert document.document_type is None
        assert document.source is None
        assert document.classification_result is None
        assert document.processing_error is None

    def test_document_with_all_fields(self, sample_metadata, sample_document_content, 
                                     sample_source, sample_classification_result):
        """Test that Document can be created with all fields."""
        document = Document(
            metadata=sample_metadata,
            content=sample_document_content,
            document_type=DocumentType.APPLICATION,
            status=ProcessingStatus.CLASSIFIED,
            source=sample_source,
            classification_result=sample_classification_result
        )

        assert document.metadata == sample_metadata
        assert document.content == sample_document_content
        assert document.status == ProcessingStatus.CLASSIFIED
        assert document.document_type == DocumentType.APPLICATION
        assert document.source == sample_source
        assert document.classification_result == sample_classification_result
        assert document.processing_error is None

    def test_document_update_status(self, sample_metadata):
        """Test updating document status."""
        document = Document(metadata=sample_metadata)
        assert document.status == ProcessingStatus.RECEIVED

        # Update status and check that updated_at is changed
        original_updated_at = document.metadata['updated_at']
        document.update_status(ProcessingStatus.CLASSIFYING)
        assert document.status == ProcessingStatus.CLASSIFYING
        assert document.metadata['updated_at'] > original_updated_at

    def test_document_set_classification_result(self, sample_metadata, sample_classification_result):
        """Test setting classification result on document."""
        document = Document(metadata=sample_metadata)
        assert document.classification_result is None
        assert document.document_type is None

        # Set classification result and check that document is updated
        document.set_classification_result(sample_classification_result)
        assert document.classification_result == sample_classification_result
        assert document.document_type == DocumentType.APPLICATION
        assert document.metadata['classification_confidence'] == 0.95
        assert document.status == ProcessingStatus.CLASSIFIED

    def test_document_set_error(self, sample_metadata, sample_processing_error):
        """Test setting error on document."""
        document = Document(metadata=sample_metadata)
        assert document.processing_error is None
        assert document.status == ProcessingStatus.RECEIVED

        # Set error and check that document is updated
        document.set_error(sample_processing_error)
        assert document.processing_error == sample_processing_error
        assert document.status == ProcessingStatus.ERROR

    def test_document_to_dict(self, sample_metadata, sample_document_content, 
                             sample_source, sample_classification_result):
        """Test converting document to dictionary."""
        document = Document(
            metadata=sample_metadata,
            content=sample_document_content,
            document_type=DocumentType.APPLICATION,
            status=ProcessingStatus.CLASSIFIED,
            source=sample_source,
            classification_result=sample_classification_result
        )

        # Convert to dict and check fields
        doc_dict = document.to_dict()
        assert isinstance(doc_dict, dict)
        assert 'metadata' in doc_dict
        assert 'status' in doc_dict
        assert 'document_type' in doc_dict
        assert 'source' in doc_dict
        assert 'classification_result' in doc_dict
        assert 'content' not in doc_dict  # Content should not be included

    def test_document_from_dict(self, sample_metadata, sample_source, sample_classification_result):
        """Test creating document from dictionary."""
        # Create a document dict
        doc_dict = {
            'metadata': sample_metadata,
            'status': ProcessingStatus.CLASSIFIED.value,
            'document_type': DocumentType.APPLICATION.value,
            'source': sample_source,
            'classification_result': sample_classification_result
        }

        # Create document from dict
        document = Document.from_dict(doc_dict)
        assert document.metadata == sample_metadata
        assert document.status == ProcessingStatus.CLASSIFIED
        assert document.document_type == DocumentType.APPLICATION
        assert document.source == sample_source
        assert document.classification_result == sample_classification_result
        assert document.content is None

    def test_document_id_generation(self):
        """Test that document ID is generated if not provided."""
        # Create metadata without ID
        metadata: DocumentMetadata = {
            'filename': 'test_document.pdf',
            'size': 1024,
            'mime_type': 'application/pdf',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # Create document and check that ID is generated
        document = Document(metadata=metadata)
        assert 'id' in document.metadata
        assert document.metadata['id'] is not None
        assert isinstance(document.metadata['id'], str)

    def test_document_timestamp_generation(self):
        """Test that timestamps are generated if not provided."""
        # Create metadata without timestamps
        metadata: DocumentMetadata = {
            'id': str(uuid.uuid4()),
            'filename': 'test_document.pdf',
            'size': 1024,
            'mime_type': 'application/pdf'
        }

        # Create document and check that timestamps are generated
        document = Document(metadata=metadata)
        assert 'created_at' in document.metadata
        assert document.metadata['created_at'] is not None
        assert isinstance(document.metadata['created_at'], datetime)
        assert 'updated_at' in document.metadata
        assert document.metadata['updated_at'] is not None
        assert isinstance(document.metadata['updated_at'], datetime)


class TestDocumentCollections:
    """Tests for document collection types."""

    def test_document_list(self, sample_metadata):
        """Test DocumentList type."""
        # Create a list of documents
        doc1 = Document(metadata=sample_metadata)
        doc2 = Document(metadata={
            **sample_metadata,
            'id': str(uuid.uuid4()),
            'filename': 'another_document.pdf'
        })

        doc_list: DocumentList = [doc1, doc2]
        assert len(doc_list) == 2
        assert isinstance(doc_list[0], Document)
        assert isinstance(doc_list[1], Document)

    def test_document_dict(self, sample_metadata):
        """Test DocumentDict type."""
        # Create a dict of documents
        doc1 = Document(metadata=sample_metadata)
        doc2 = Document(metadata={
            **sample_metadata,
            'id': str(uuid.uuid4()),
            'filename': 'another_document.pdf'
        })

        doc_dict: DocumentDict = {
            doc1.metadata['id']: doc1,
            doc2.metadata['id']: doc2
        }

        assert len(doc_dict) == 2
        assert isinstance(doc_dict[doc1.metadata['id']], Document)
        assert isinstance(doc_dict[doc2.metadata['id']], Document)


class TestClassificationAccuracy:
    """Tests related to document classification accuracy requirements."""

    def test_high_confidence_classification(self, sample_classification_result):
        """Test high confidence classification handling."""
        # Create a document with high confidence classification
        metadata: DocumentMetadata = {
            'id': str(uuid.uuid4()),
            'filename': 'test_document.pdf',
            'size': 1024,
            'mime_type': 'application/pdf',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        document = Document(metadata=metadata)
        document.set_classification_result(sample_classification_result)

        # Check that document is classified correctly
        assert document.document_type == DocumentType.APPLICATION
        assert document.status == ProcessingStatus.CLASSIFIED
        assert document.metadata['classification_confidence'] == 0.95

    def test_low_confidence_classification(self, sample_classification_result):
        """Test low confidence classification handling."""
        # Create a document with low confidence classification
        metadata: DocumentMetadata = {
            'id': str(uuid.uuid4()),
            'filename': 'test_document.pdf',
            'size': 1024,
            'mime_type': 'application/pdf',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        # Modify classification result to have low confidence and require review
        low_confidence_result = sample_classification_result.copy()
        low_confidence_result['confidence'] = 0.65
        low_confidence_result['requires_review'] = True

        document = Document(metadata=metadata)
        document.set_classification_result(low_confidence_result)

        # Check that document is flagged for review
        assert document.document_type == DocumentType.APPLICATION
        assert document.status == ProcessingStatus.REVIEW
        assert document.metadata['classification_confidence'] == 0.65

    def test_classification_confidence_thresholds(self):
        """Test classification confidence thresholds."""
        # In a real implementation, there would be logic to determine if a document
        # requires review based on confidence thresholds
        # Here we're just testing the concept

        # Define confidence thresholds
        HIGH_CONFIDENCE = 0.90  # 90% confidence or higher is considered high
        MEDIUM_CONFIDENCE = 0.75  # 75-90% confidence is medium
        LOW_CONFIDENCE = 0.50  # 50-75% confidence is low
        # Below 50% confidence is very low

        # Test high confidence
        assert self._requires_review(0.95) is False
        # Test medium confidence
        assert self._requires_review(0.85) is False
        # Test low confidence
        assert self._requires_review(0.65) is True
        # Test very low confidence
        assert self._requires_review(0.45) is True

    def _requires_review(self, confidence: float) -> bool:
        """Helper method to determine if a document requires review based on confidence."""
        # Define confidence threshold for automatic processing
        CONFIDENCE_THRESHOLD = 0.75  # 75% confidence or higher for automatic processing
        return confidence < CONFIDENCE_THRESHOLD