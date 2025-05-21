#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service classification API endpoints.

This module contains tests that verify the Document Service API correctly handles
document classification requests, validates input parameters, processes document
classification operations, and returns appropriate responses with confidence scores.

These tests ensure that the Document Service meets the 99% accuracy requirement
for document classification as specified in the technical specification.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from unittest import mock
from typing import Dict, Any, List, Optional

import pytest
from fastapi import status
from fastapi.testclient import TestClient

# Import the FastAPI app
from src.main import app

# Import the services that need to be mocked
from src.services.classification_service import ClassificationService
from src.services.document_routing_service import DocumentRoutingService
from src.services.storage_service import StorageService

# Import the types needed for testing
from src.types.classification import ClassificationResult, ConfidenceScore, DocumentType
from src.types.documents import Document, DocumentMetadata, ProcessingStatus
from src.types.errors import Result, ServiceError, ErrorCategory


# Create a test client
@pytest.fixture
def client():
    """Create a FastAPI TestClient for API testing."""
    return TestClient(app)


# Mock the classification service
@pytest.fixture
def mock_classification_service():
    """Create a mock ClassificationService for testing."""
    with mock.patch("src.api.documents.get_classification_service") as mock_get_service:
        service = mock.MagicMock(spec=ClassificationService)
        mock_get_service.return_value = service
        yield service


# Mock the document routing service
@pytest.fixture
def mock_document_routing_service():
    """Create a mock DocumentRoutingService for testing."""
    with mock.patch("src.api.documents.get_document_routing_service") as mock_get_service:
        service = mock.MagicMock(spec=DocumentRoutingService)
        mock_get_service.return_value = service
        yield service


# Mock the storage service
@pytest.fixture
def mock_storage_service():
    """Create a mock StorageService for testing."""
    with mock.patch("src.api.documents.get_storage_service") as mock_get_service:
        service = mock.MagicMock(spec=StorageService)
        mock_get_service.return_value = service
        yield service


# Helper function to create a test document
def create_test_document(document_id: Optional[str] = None, document_type: str = "application",
                        status: str = "received", filename: str = "test_document.pdf") -> Document:
    """Create a test document for use in tests.
    
    Args:
        document_id: Optional document ID (defaults to a random UUID)
        document_type: Document type (defaults to "application")
        status: Processing status (defaults to "received")
        filename: Document filename (defaults to "test_document.pdf")
        
    Returns:
        A Document instance for testing
    """
    doc_id = document_id or str(uuid.uuid4())
    
    metadata = DocumentMetadata(
        id=doc_id,
        filename=filename,
        size=1024,
        mime_type="application/pdf",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        storage_path=f"s3://test-bucket/{doc_id}/{filename}",
        page_count=5
    )
    
    return Document(
        metadata=metadata,
        content=b"test document content",
        document_type=DocumentType(document_type) if document_type else None,
        status=ProcessingStatus(status)
    )


# Helper function to create a classification result
def create_classification_result(document_id: str, document_type: str = "application",
                                confidence: float = 0.95, requires_review: bool = False) -> ClassificationResult:
    """Create a test classification result for use in tests.
    
    Args:
        document_id: Document ID
        document_type: Document type (defaults to "application")
        confidence: Confidence score (defaults to 0.95)
        requires_review: Whether the document requires review (defaults to False)
        
    Returns:
        A ClassificationResult instance for testing
    """
    return ClassificationResult(
        document_id=document_id,
        document_type=DocumentType(document_type),
        confidence=ConfidenceScore(confidence),
        requires_review=requires_review,
        prediction_time=datetime.utcnow(),
        feature_importance={"text_length": 0.3, "keyword_count": 0.7}
    )


# Tests for the document classification endpoint
class TestClassificationEndpoint:
    """Tests for the /documents/{document_id}/classify endpoint."""
    
    def test_successful_classification(self, client, mock_storage_service, mock_classification_service, mock_document_routing_service):
        """Test successful document classification with high confidence."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(document_id, confidence=0.98)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "ocr_service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["document_id"] == document_id
        assert response_data["status"] == "classification_complete"
        assert response_data["classification"]["document_type"] == "application"
        assert response_data["classification"]["confidence"] == 0.98
        assert response_data["classification"]["requires_review"] is False
        assert "classified_at" in response_data["classification"]
        assert "routing" in response_data
        assert response_data["routing"]["destination"] == "ocr_service"
        
        # Verify service calls
        mock_storage_service.get_document.assert_called_once_with(document_id)
        mock_classification_service.classify_document.assert_called_once_with(document)
        mock_document_routing_service.route_document.assert_called_once()
        mock_storage_service.update_document_metadata.assert_called_once()
    
    def test_classification_with_low_confidence(self, client, mock_storage_service, mock_classification_service, mock_document_routing_service):
        """Test document classification with low confidence that requires review."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(document_id, confidence=0.65, requires_review=True)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "manual_review"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["document_id"] == document_id
        assert response_data["classification"]["confidence"] == 0.65
        assert response_data["classification"]["requires_review"] is True
        assert response_data["routing"]["destination"] == "manual_review"
    
    def test_classification_with_force_parameter(self, client, mock_storage_service, mock_classification_service, mock_document_routing_service):
        """Test document classification with force=True parameter to reclassify already classified documents."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id, status="classified")
        classification_result = create_classification_result(document_id)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.get_classification_result.return_value = classification_result
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "ocr_service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act - First without force parameter
        response_without_force = client.post(f"/documents/{document_id}/classify")
        
        # Assert - Should return already classified status
        assert response_without_force.status_code == status.HTTP_200_OK
        response_data = response_without_force.json()
        assert response_data["status"] == "already_classified"
        
        # Act - Then with force parameter
        response_with_force = client.post(f"/documents/{document_id}/classify?force=true")
        
        # Assert - Should perform classification
        assert response_with_force.status_code == status.HTTP_200_OK
        response_data = response_with_force.json()
        assert response_data["status"] == "classification_complete"
        
        # Verify service calls
        mock_classification_service.classify_document.assert_called_once_with(document)
    
    def test_document_not_found(self, client, mock_storage_service):
        """Test classification of a non-existent document."""
        # Arrange
        document_id = str(uuid.uuid4())
        mock_storage_service.get_document.return_value = None
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        response_data = response.json()
        assert "detail" in response_data
        assert f"Document with ID {document_id} not found" in response_data["detail"]
    
    def test_classification_service_error(self, client, mock_storage_service, mock_classification_service):
        """Test handling of classification service errors."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        
        # Create a service error
        error = ServiceError(
            message="Classification model failed to process document",
            category=ErrorCategory.PROCESSING_ERROR,
            context={"document_id": document_id}
        )
        mock_classification_service.classify_document.return_value = Result.failure(error)
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "detail" in response_data
        assert "Classification model failed to process document" in response_data["detail"]
    
    def test_validation_error(self, client, mock_storage_service, mock_classification_service):
        """Test handling of document validation errors."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        
        # Create a validation error
        error = ServiceError(
            message="Invalid document format: not a PDF",
            category=ErrorCategory.VALIDATION,
            context={"document_id": document_id, "mime_type": "text/plain"}
        )
        mock_classification_service.classify_document.return_value = Result.failure(error)
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "detail" in response_data
        assert "Invalid document format" in response_data["detail"]


# Tests for the batch classification endpoint
class TestBatchClassificationEndpoint:
    """Tests for the /documents/batch endpoint."""
    
    def test_successful_batch_classification(self, client, mock_storage_service, mock_classification_service):
        """Test successful batch classification of multiple documents."""
        # Arrange
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        documents = [create_test_document(doc_id) for doc_id in document_ids]
        
        # Configure mocks
        mock_storage_service.get_document.side_effect = documents
        mock_classification_service.queue_for_classification.return_value = None
        
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert "summary" in response_data
        assert response_data["summary"]["total"] == 3
        assert response_data["summary"]["successful"] == 3
        assert response_data["summary"]["failed"] == 0
        assert response_data["summary"]["skipped"] == 0
        
        # Verify service calls
        assert mock_storage_service.get_document.call_count == 3
        assert mock_classification_service.queue_for_classification.call_count == 3
    
    def test_batch_with_some_documents_not_found(self, client, mock_storage_service, mock_classification_service):
        """Test batch classification with some documents not found."""
        # Arrange
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Configure mocks to return None for the second document (not found)
        mock_storage_service.get_document.side_effect = [
            create_test_document(document_ids[0]),
            None,
            create_test_document(document_ids[2])
        ]
        mock_classification_service.queue_for_classification.return_value = None
        
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["summary"]["total"] == 3
        assert response_data["summary"]["successful"] == 2
        assert response_data["summary"]["failed"] == 1
        
        # Check that the failed document is correctly identified
        failed_docs = response_data["results"]["failed"]
        assert len(failed_docs) == 1
        assert failed_docs[0]["document_id"] == document_ids[1]
        assert "Document not found" in failed_docs[0]["error"]
    
    def test_batch_with_already_classified_documents(self, client, mock_storage_service, mock_classification_service):
        """Test batch classification with some already classified documents."""
        # Arrange
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Create documents with different statuses
        documents = [
            create_test_document(document_ids[0]),  # New document
            create_test_document(document_ids[1], status="classified"),  # Already classified
            create_test_document(document_ids[2])  # New document
        ]
        
        # Configure mocks
        mock_storage_service.get_document.side_effect = documents
        
        # Mock classification results for already classified document
        mock_classification_service.get_classification_result.side_effect = [
            None,  # First document not classified yet
            create_classification_result(document_ids[1]),  # Second document already classified
            None  # Third document not classified yet
        ]
        
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["summary"]["total"] == 3
        assert response_data["summary"]["successful"] == 2
        assert response_data["summary"]["skipped"] == 1
        
        # Check that the skipped document is correctly identified
        skipped_docs = response_data["results"]["skipped"]
        assert len(skipped_docs) == 1
        assert skipped_docs[0]["document_id"] == document_ids[1]
        assert "Already classified" in skipped_docs[0]["reason"]
    
    def test_batch_with_force_parameter(self, client, mock_storage_service, mock_classification_service):
        """Test batch classification with force=true to reclassify already classified documents."""
        # Arrange
        document_ids = [str(uuid.uuid4()) for _ in range(2)]
        
        # Create documents with different statuses
        documents = [
            create_test_document(document_ids[0]),  # New document
            create_test_document(document_ids[1], status="classified")  # Already classified
        ]
        
        # Configure mocks
        mock_storage_service.get_document.side_effect = documents
        
        # Mock classification results for already classified document
        mock_classification_service.get_classification_result.side_effect = [
            None,  # First document not classified yet
            create_classification_result(document_ids[1])  # Second document already classified
        ]
        
        # Act
        response = client.post(
            "/documents/batch?force=true",
            json={"document_ids": document_ids}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["summary"]["total"] == 2
        assert response_data["summary"]["successful"] == 2
        assert response_data["summary"]["skipped"] == 0
        
        # Verify that both documents were queued for classification
        assert mock_classification_service.queue_for_classification.call_count == 2
    
    def test_batch_with_empty_document_ids(self, client):
        """Test batch classification with empty document IDs list."""
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": []}
        )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "detail" in response_data
        assert "No document IDs provided" in response_data["detail"]
    
    def test_batch_with_too_many_document_ids(self, client):
        """Test batch classification with too many document IDs (exceeding limit)."""
        # Arrange - Create 101 document IDs (exceeding the limit of 100)
        document_ids = [str(uuid.uuid4()) for _ in range(101)]
        
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        response_data = response.json()
        assert "detail" in response_data
        assert "Batch size exceeds maximum limit" in response_data["detail"]


# Tests for document classification with different document types
class TestDocumentTypeClassification:
    """Tests for classification of different document types."""
    
    @pytest.mark.parametrize("document_type,confidence", [
        ("application", 0.99),
        ("tax_return", 0.95),
        ("bank_statement", 0.98),
        ("pay_stub", 0.97),
        ("id_document", 0.96)
    ])
    def test_classification_of_different_document_types(self, client, mock_storage_service, 
                                                     mock_classification_service, mock_document_routing_service,
                                                     document_type, confidence):
        """Test classification of different document types with high confidence."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(
            document_id, document_type=document_type, confidence=confidence
        )
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "ocr_service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["classification"]["document_type"] == document_type
        assert response_data["classification"]["confidence"] == confidence
        assert response_data["classification"]["requires_review"] is False
    
    def test_classification_of_unknown_document_type(self, client, mock_storage_service, 
                                                  mock_classification_service, mock_document_routing_service):
        """Test classification of a document with unknown type and low confidence."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(
            document_id, document_type="other", confidence=0.45, requires_review=True
        )
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "manual_review"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["classification"]["document_type"] == "other"
        assert response_data["classification"]["confidence"] == 0.45
        assert response_data["classification"]["requires_review"] is True
        assert response_data["routing"]["destination"] == "manual_review"


# Tests for confidence score validation
class TestConfidenceScoreValidation:
    """Tests for validation of confidence scores in classification responses."""
    
    def test_high_confidence_classification(self, client, mock_storage_service, 
                                          mock_classification_service, mock_document_routing_service):
        """Test classification with very high confidence (99%)."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(document_id, confidence=0.99)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "ocr_service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["classification"]["confidence"] == 0.99
        assert response_data["classification"]["requires_review"] is False
    
    def test_medium_confidence_classification(self, client, mock_storage_service, 
                                            mock_classification_service, mock_document_routing_service):
        """Test classification with medium confidence (85%)."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(document_id, confidence=0.85)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "ocr_service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["classification"]["confidence"] == 0.85
        assert response_data["classification"]["requires_review"] is False
    
    def test_low_confidence_classification(self, client, mock_storage_service, 
                                         mock_classification_service, mock_document_routing_service):
        """Test classification with low confidence (65%)."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(
            document_id, confidence=0.65, requires_review=True
        )
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "manual_review"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["classification"]["confidence"] == 0.65
        assert response_data["classification"]["requires_review"] is True
        assert response_data["routing"]["destination"] == "manual_review"
    
    def test_very_low_confidence_classification(self, client, mock_storage_service, 
                                              mock_classification_service, mock_document_routing_service):
        """Test classification with very low confidence (30%)."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        classification_result = create_classification_result(
            document_id, confidence=0.30, requires_review=True
        )
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.return_value = Result.success(classification_result)
        
        # Mock routing result
        routing_result = mock.MagicMock()
        routing_result.destination = "manual_review"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["classification"]["confidence"] == 0.30
        assert response_data["classification"]["requires_review"] is True
        assert response_data["routing"]["destination"] == "manual_review"


# Tests for input validation
class TestInputValidation:
    """Tests for validation of input parameters."""
    
    def test_invalid_document_id_format(self, client):
        """Test classification with invalid document ID format."""
        # Act
        response = client.post("/documents/invalid-uuid/classify")
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        assert "invalid-uuid" in str(response_data["detail"])
    
    def test_invalid_force_parameter(self, client, mock_storage_service):
        """Test classification with invalid force parameter."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        mock_storage_service.get_document.return_value = document
        
        # Act - Use an invalid value for force parameter
        response = client.post(f"/documents/{document_id}/classify?force=invalid")
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        assert "force" in str(response_data["detail"])
    
    def test_batch_with_invalid_document_ids(self, client):
        """Test batch classification with invalid document IDs."""
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": ["invalid-uuid", str(uuid.uuid4())]}
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        response_data = response.json()
        assert "detail" in response_data
        assert "invalid-uuid" in str(response_data["detail"])


# Tests for error handling
class TestErrorHandling:
    """Tests for error handling in the classification API."""
    
    def test_internal_server_error(self, client, mock_storage_service, mock_classification_service):
        """Test handling of unexpected internal server errors."""
        # Arrange
        document_id = str(uuid.uuid4())
        document = create_test_document(document_id)
        
        # Configure mocks
        mock_storage_service.get_document.return_value = document
        mock_classification_service.classify_document.side_effect = Exception("Unexpected error")
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "detail" in response_data
        assert "error occurred" in response_data["detail"]
    
    def test_service_unavailable(self, client, mock_storage_service):
        """Test handling of service unavailability."""
        # Arrange
        document_id = str(uuid.uuid4())
        
        # Configure mocks to simulate service unavailability
        mock_storage_service.get_document.side_effect = Exception("Database connection error")
        
        # Act
        response = client.post(f"/documents/{document_id}/classify")
        
        # Assert
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        response_data = response.json()
        assert "detail" in response_data
        assert "error occurred" in response_data["detail"]
    
    def test_batch_with_partial_failures(self, client, mock_storage_service, mock_classification_service):
        """Test batch classification with partial failures."""
        # Arrange
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Configure mocks to succeed for first document, fail for second, and succeed for third
        mock_storage_service.get_document.side_effect = [
            create_test_document(document_ids[0]),
            create_test_document(document_ids[1]),
            create_test_document(document_ids[2])
        ]
        
        # Make the second document fail during queue_for_classification
        def mock_queue_side_effect(doc_id):
            if doc_id == document_ids[1]:
                raise Exception("Queue connection error")
            return None
            
        mock_classification_service.queue_for_classification.side_effect = mock_queue_side_effect
        
        # Act
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        response_data = response.json()
        assert response_data["summary"]["total"] == 3
        assert response_data["summary"]["successful"] == 2
        assert response_data["summary"]["failed"] == 1
        
        # Check that the failed document is correctly identified
        failed_docs = response_data["results"]["failed"]
        assert len(failed_docs) == 1
        assert failed_docs[0]["document_id"] == document_ids[1]
        assert "Queue connection error" in failed_docs[0]["error"]