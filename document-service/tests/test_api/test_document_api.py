#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the Document Service API endpoints.

This module contains tests for the Document Service CRUD API endpoints, verifying
that the API correctly handles document operations including upload, retrieval,
update, and deletion. It validates proper storage path generation, metadata extraction,
and integration with S3-compatible storage.
"""

import os
import json
import uuid
import pytest
import io
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, ANY
from fastapi import FastAPI
from fastapi.testclient import TestClient
from typing import Dict, List, Any, Optional

# Import the API router and dependencies
from document_service.src.api.documents import router as documents_router
from document_service.src.services.classification_service import ClassificationService
from document_service.src.services.document_routing_service import DocumentRoutingService
from document_service.src.services.storage_service import StorageService
from document_service.src.types.documents import Document, DocumentType, ProcessingStatus
from document_service.src.types.classification import ClassificationResult, ConfidenceScore
from document_service.src.types.errors import ServiceError, ErrorCategory


# Create a test FastAPI app
@pytest.fixture
def app():
    """Create a FastAPI test application with the documents router."""
    app = FastAPI()
    app.include_router(documents_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_storage_service():
    """Create a mock StorageService for testing."""
    with patch("document_service.src.api.documents.get_storage_service") as mock_get_service:
        mock_service = MagicMock(spec=StorageService)
        mock_get_service.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_classification_service():
    """Create a mock ClassificationService for testing."""
    with patch("document_service.src.api.documents.get_classification_service") as mock_get_service:
        mock_service = MagicMock(spec=ClassificationService)
        mock_get_service.return_value = mock_service
        yield mock_service


@pytest.fixture
def mock_document_routing_service():
    """Create a mock DocumentRoutingService for testing."""
    with patch("document_service.src.api.documents.get_document_routing_service") as mock_get_service:
        mock_service = MagicMock(spec=DocumentRoutingService)
        mock_get_service.return_value = mock_service
        yield mock_service


@pytest.fixture
def sample_document_id():
    """Generate a sample document ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_document(sample_document_id):
    """Create a sample Document object for testing."""
    metadata = {
        'id': sample_document_id,
        'filename': 'test_document.pdf',
        'size': 1024,
        'mime_type': 'application/pdf',
        'created_at': datetime.utcnow(),
        'updated_at': datetime.utcnow(),
        'application_id': str(uuid.uuid4()),
        'storage_path': f'documents/2023/05/01/{sample_document_id}.pdf',
        'checksum': 'abc123checksum',
        'page_count': 3,
        'tags': ['application', 'loan']
    }
    
    document = MagicMock(spec=Document)
    document.metadata = metadata
    document.status = ProcessingStatus.RECEIVED
    document.document_type = None
    document.classification_result = None
    document.processing_error = None
    document.to_dict.return_value = {
        'metadata': metadata,
        'status': ProcessingStatus.RECEIVED.value
    }
    
    return document


@pytest.fixture
def sample_classification_result(sample_document_id):
    """Create a sample ClassificationResult for testing."""
    result = MagicMock(spec=ClassificationResult)
    result.document_type = DocumentType.APPLICATION
    result.confidence = ConfidenceScore(0.85)
    result.classified_at = datetime.utcnow()
    result.requires_review = False
    
    return result


# Test cases for GET /documents/{document_id}
class TestGetDocument:
    """Test cases for the GET /documents/{document_id} endpoint."""
    
    def test_get_document_success(self, client, mock_storage_service, mock_classification_service, 
                                  sample_document, sample_document_id, sample_classification_result):
        """Test successful document retrieval by ID."""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = sample_classification_result
        
        # Make request
        response = client.get(f"/documents/{sample_document_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document_id
        assert "metadata" in data
        assert "classification" in data
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["classification"]["confidence"] == 0.85
        assert data["classification"]["requires_review"] is False
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.get_classification_result.assert_called_once_with(uuid.UUID(sample_document_id))
    
    def test_get_document_not_found(self, client, mock_storage_service, sample_document_id):
        """Test document retrieval when document doesn't exist."""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = None
        
        # Make request
        response = client.get(f"/documents/{sample_document_id}")
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Document with ID {sample_document_id} not found" in data["detail"]
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(uuid.UUID(sample_document_id))
    
    def test_get_document_without_classification(self, client, mock_storage_service, 
                                               mock_classification_service, sample_document, 
                                               sample_document_id):
        """Test document retrieval when document exists but has no classification."""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = None
        
        # Make request
        response = client.get(f"/documents/{sample_document_id}")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document_id
        assert "metadata" in data
        assert "classification" not in data
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.get_classification_result.assert_called_once_with(uuid.UUID(sample_document_id))
    
    def test_get_document_server_error(self, client, mock_storage_service, sample_document_id):
        """Test document retrieval when server error occurs."""
        # Setup mocks
        mock_storage_service.get_document_metadata.side_effect = Exception("Database connection error")
        
        # Make request
        response = client.get(f"/documents/{sample_document_id}")
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "An error occurred while retrieving the document" in data["detail"]
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(uuid.UUID(sample_document_id))


# Test cases for POST /documents/{document_id}/classify
class TestClassifyDocument:
    """Test cases for the POST /documents/{document_id}/classify endpoint."""
    
    def test_classify_document_success(self, client, mock_storage_service, mock_classification_service,
                                      mock_document_routing_service, sample_document, sample_document_id,
                                      sample_classification_result):
        """Test successful document classification."""
        # Setup mocks
        mock_storage_service.get_document.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = None
        mock_classification_service.classify_document.return_value = sample_classification_result
        
        routing_result = MagicMock()
        routing_result.destination = "ocr-service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Make request
        response = client.post(f"/documents/{sample_document_id}/classify")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document_id
        assert data["status"] == "classification_complete"
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["classification"]["confidence"] == 0.85
        assert data["routing"]["destination"] == "ocr-service"
        
        # Verify service calls
        mock_storage_service.get_document.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.get_classification_result.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.classify_document.assert_called_once_with(sample_document)
        mock_document_routing_service.route_document.assert_called_once_with(
            sample_document, sample_classification_result)
        mock_storage_service.update_document_metadata.assert_called_once_with(sample_document)
    
    def test_classify_document_already_classified(self, client, mock_storage_service, 
                                               mock_classification_service, sample_document, 
                                               sample_document_id, sample_classification_result):
        """Test document classification when document is already classified."""
        # Setup mocks
        mock_storage_service.get_document.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = sample_classification_result
        
        # Make request
        response = client.post(f"/documents/{sample_document_id}/classify")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document_id
        assert data["status"] == "already_classified"
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        
        # Verify service calls
        mock_storage_service.get_document.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.get_classification_result.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.classify_document.assert_not_called()
    
    def test_classify_document_force_reclassification(self, client, mock_storage_service, 
                                                   mock_classification_service, mock_document_routing_service,
                                                   sample_document, sample_document_id, 
                                                   sample_classification_result):
        """Test document classification with force=True to reclassify already classified document."""
        # Setup mocks
        mock_storage_service.get_document.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = sample_classification_result
        mock_classification_service.classify_document.return_value = sample_classification_result
        
        routing_result = MagicMock()
        routing_result.destination = "ocr-service"
        routing_result.routed_at = datetime.utcnow()
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Make request
        response = client.post(f"/documents/{sample_document_id}/classify?force=true")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == sample_document_id
        assert data["status"] == "classification_complete"
        
        # Verify service calls
        mock_storage_service.get_document.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.get_classification_result.assert_called_once_with(uuid.UUID(sample_document_id))
        mock_classification_service.classify_document.assert_called_once_with(sample_document)
    
    def test_classify_document_not_found(self, client, mock_storage_service, sample_document_id):
        """Test document classification when document doesn't exist."""
        # Setup mocks
        mock_storage_service.get_document.return_value = None
        
        # Make request
        response = client.post(f"/documents/{sample_document_id}/classify")
        
        # Verify response
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert f"Document with ID {sample_document_id} not found" in data["detail"]
    
    def test_classify_document_service_error(self, client, mock_storage_service, mock_classification_service,
                                           sample_document, sample_document_id):
        """Test document classification when service error occurs."""
        # Setup mocks
        mock_storage_service.get_document.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = None
        
        service_error = ServiceError(
            message="Classification model not found",
            category=ErrorCategory.CLASSIFICATION
        )
        mock_classification_service.classify_document.side_effect = service_error
        
        # Make request
        response = client.post(f"/documents/{sample_document_id}/classify")
        
        # Verify response
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Classification model not found" in data["detail"]


# Test cases for POST /documents/batch
class TestBatchClassify:
    """Test cases for the POST /documents/batch endpoint."""
    
    def test_batch_classify_success(self, client, mock_storage_service, mock_classification_service,
                                   sample_document):
        """Test successful batch document classification."""
        # Create document IDs
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Setup mocks
        mock_storage_service.get_document.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = None
        
        # Make request
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert data["summary"]["total"] == 3
        assert data["summary"]["successful"] == 3
        assert data["summary"]["failed"] == 0
        assert data["summary"]["skipped"] == 0
        
        # Verify service calls
        assert mock_storage_service.get_document.call_count == 3
        assert mock_classification_service.get_classification_result.call_count == 3
        assert mock_classification_service.queue_for_classification.call_count == 3
    
    def test_batch_classify_mixed_results(self, client, mock_storage_service, mock_classification_service,
                                         sample_document, sample_classification_result):
        """Test batch classification with mixed results (success, failure, skipped)."""
        # Create document IDs
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Setup mocks to simulate different scenarios for each document
        def get_document_side_effect(doc_id):
            if doc_id == uuid.UUID(document_ids[0]):
                return sample_document  # Success
            elif doc_id == uuid.UUID(document_ids[1]):
                return None  # Not found
            else:
                return sample_document  # Already classified
        
        def get_classification_result_side_effect(doc_id):
            if doc_id == uuid.UUID(document_ids[0]):
                return None  # Not classified yet
            elif doc_id == uuid.UUID(document_ids[1]):
                return None  # Not relevant (document not found)
            else:
                return sample_classification_result  # Already classified
        
        mock_storage_service.get_document.side_effect = get_document_side_effect
        mock_classification_service.get_classification_result.side_effect = get_classification_result_side_effect
        
        # Make request
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["summary"]["total"] == 3
        assert data["summary"]["successful"] == 1
        assert data["summary"]["failed"] == 1
        assert data["summary"]["skipped"] == 1
        
        # Check results details
        assert len(data["results"]["successful"]) == 1
        assert len(data["results"]["failed"]) == 1
        assert len(data["results"]["skipped"]) == 1
        
        # Verify document IDs in each category
        assert data["results"]["successful"][0]["document_id"] == document_ids[0]
        assert data["results"]["failed"][0]["document_id"] == document_ids[1]
        assert data["results"]["skipped"][0]["document_id"] == document_ids[2]
    
    def test_batch_classify_empty_list(self, client):
        """Test batch classification with empty document list."""
        # Make request
        response = client.post(
            "/documents/batch",
            json={"document_ids": []}
        )
        
        # Verify response
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "No document IDs provided" in data["detail"]
    
    def test_batch_classify_too_many_documents(self, client):
        """Test batch classification with too many documents."""
        # Create 101 document IDs (exceeding the 100 limit)
        document_ids = [str(uuid.uuid4()) for _ in range(101)]
        
        # Make request
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        
        # Verify response
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Batch size exceeds maximum limit of 100 documents" in data["detail"]


# Test cases for GET /documents
class TestListDocuments:
    """Test cases for the GET /documents endpoint."""
    
    def test_list_documents_no_filters(self, client, mock_storage_service, mock_classification_service,
                                      sample_document):
        """Test listing documents without filters."""
        # Setup mocks
        mock_storage_service.list_documents.return_value = ([sample_document], 1)
        mock_classification_service.get_classification_result.return_value = None
        
        # Make request
        response = client.get("/documents")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert "pagination" in data
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_items"] == 1
        
        # Verify service calls
        mock_storage_service.list_documents.assert_called_once_with(
            document_type=None,
            status=None,
            confidence_min=None,
            confidence_max=None,
            requires_review=None,
            page=1,
            page_size=20
        )
    
    def test_list_documents_with_filters(self, client, mock_storage_service, mock_classification_service,
                                        sample_document):
        """Test listing documents with filters."""
        # Setup mocks
        mock_storage_service.list_documents.return_value = ([sample_document], 1)
        mock_classification_service.get_classification_result.return_value = None
        
        # Make request with filters
        response = client.get(
            "/documents?document_type=application&status=received&confidence_min=0.7&confidence_max=1.0&requires_review=false&page=2&page_size=10"
        )
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "pagination" in data
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 10
        
        # Verify service calls with correct filters
        mock_storage_service.list_documents.assert_called_once()
        call_args = mock_storage_service.list_documents.call_args[1]
        assert call_args["document_type"] is not None
        assert call_args["status"] is not None
        assert call_args["confidence_min"] == 0.7
        assert call_args["confidence_max"] == 1.0
        assert call_args["requires_review"] is False
        assert call_args["page"] == 2
        assert call_args["page_size"] == 10
    
    def test_list_documents_invalid_filter(self, client):
        """Test listing documents with invalid filter values."""
        # Make request with invalid document type
        response = client.get("/documents?document_type=invalid_type")
        
        # Verify response
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid document type: invalid_type" in data["detail"]
    
    def test_list_documents_with_classification(self, client, mock_storage_service, 
                                              mock_classification_service, sample_document,
                                              sample_classification_result):
        """Test listing documents with classification results."""
        # Setup mocks
        mock_storage_service.list_documents.return_value = ([sample_document], 1)
        mock_classification_service.get_classification_result.return_value = sample_classification_result
        
        # Make request
        response = client.get("/documents")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert "classification" in data["documents"][0]
        assert data["documents"][0]["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["documents"][0]["classification"]["confidence"] == 0.85
    
    def test_list_documents_pagination(self, client, mock_storage_service, mock_classification_service):
        """Test document listing pagination."""
        # Create multiple sample documents
        documents = [MagicMock(spec=Document) for _ in range(5)]
        for i, doc in enumerate(documents):
            doc.id = uuid.uuid4()
            doc.metadata = {
                'id': str(doc.id),
                'filename': f'document_{i}.pdf',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            doc.status = ProcessingStatus.RECEIVED
        
        # Setup mocks
        mock_storage_service.list_documents.return_value = (documents, 15)  # 15 total documents, 5 per page
        mock_classification_service.get_classification_result.return_value = None
        
        # Make request for page 2
        response = client.get("/documents?page=2&page_size=5")
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert "pagination" in data
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 5
        assert data["pagination"]["total_items"] == 15
        assert data["pagination"]["total_pages"] == 3  # 15 items with 5 per page = 3 pages
        
        # Verify service calls
        mock_storage_service.list_documents.assert_called_once_with(
            document_type=None,
            status=None,
            confidence_min=None,
            confidence_max=None,
            requires_review=None,
            page=2,
            page_size=5
        )


# Integration tests for S3 storage
class TestS3Integration:
    """Integration tests for S3 storage functionality."""
    
    @pytest.mark.integration
    def test_document_upload_with_encryption(self, mock_storage_service):
        """Test document upload with AES-256 encryption."""
        # This is a placeholder for an integration test that would verify
        # S3 storage with encryption. In a real test environment, this would
        # use a mock S3 service like Moto or a test S3 bucket.
        
        # For now, we'll just verify that the StorageService is configured to use encryption
        storage_service = StorageService()
        
        # Create a test file
        test_file_content = b"Test document content"
        test_file = io.BytesIO(test_file_content)
        document_id = str(uuid.uuid4())
        file_name = "test_document.pdf"
        
        # Mock the S3 client's upload_fileobj method
        with patch.object(storage_service.s3_client, 'upload_fileobj') as mock_upload:
            # Call the upload method
            storage_service.upload_document_from_bytes(
                test_file_content, file_name, document_id, {"test_key": "test_value"}
            )
            
            # Verify the upload was called with encryption
            mock_upload.assert_called_once()
            _, kwargs = mock_upload.call_args
            assert "ExtraArgs" in kwargs
            assert "ServerSideEncryption" in kwargs["ExtraArgs"]
            assert kwargs["ExtraArgs"]["ServerSideEncryption"] == "AES256"
    
    @pytest.mark.integration
    def test_document_metadata_extraction(self, mock_storage_service):
        """Test extraction of document metadata for classification."""
        # Setup a mock S3 client response
        storage_service = StorageService()
        object_key = "documents/2023/05/01/test-document.pdf"
        
        # Mock the head_object response
        mock_response = {
            "ContentLength": 1024,
            "ContentType": "application/pdf",
            "LastModified": datetime.utcnow(),
            "ETag": "\"abc123\"",
            "ServerSideEncryption": "AES256",
            "Metadata": {
                "document_id": "test-123",
                "original_filename": "original.pdf",
                "upload_timestamp": datetime.utcnow().isoformat(),
                "classification": "application",
                "classification_confidence": "0.92"
            }
        }
        
        with patch.object(storage_service.s3_client, 'head_object', return_value=mock_response):
            # Call the metadata extraction method
            metadata, error = storage_service.extract_document_metadata_for_classification(object_key)
            
            # Verify the metadata was extracted correctly
            assert error is None
            assert metadata is not None
            assert metadata["object_key"] == object_key
            assert metadata["file_extension"] == "pdf"
            assert metadata["content_type"] == "application/pdf"
            assert metadata["file_size"] == 1024
            assert metadata["original_filename"] == "original.pdf"
            assert metadata["document_id"] == "test-123"
            assert metadata["previous_classification"] == "application"
            assert metadata["previous_confidence"] == 0.92
    
    @pytest.mark.integration
    def test_document_storage_path_generation(self):
        """Test generation of storage paths for documents."""
        storage_service = StorageService()
        document_id = "test-document-123"
        file_name = "test_document.pdf"
        
        # Use a patched datetime to get a predictable path
        fixed_date = datetime(2023, 5, 1)
        with patch('datetime.datetime') as mock_datetime:
            mock_datetime.now.return_value = fixed_date
            
            # Call the path generation method
            object_key = storage_service._generate_object_key(document_id, file_name)
            
            # Verify the path format
            assert object_key == "documents/2023/05/01/test-document-123.pdf"
            assert object_key.startswith("documents/")
            assert object_key.endswith(".pdf")
            assert document_id in object_key


# Test cases for document ownership and permissions
class TestDocumentPermissions:
    """Test cases for document ownership and permission validation."""
    
    @pytest.mark.parametrize("user_role,expected_status", [
        ("admin", 200),
        ("operations", 200),
        ("user", 403)
    ])
    def test_document_access_by_role(self, client, mock_storage_service, mock_classification_service,
                                    sample_document, sample_document_id, user_role, expected_status):
        """Test document access based on user role."""
        # This test would normally use authentication middleware
        # For now, we'll simulate it with a mock
        
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = sample_document
        mock_classification_service.get_classification_result.return_value = None
        
        # Mock the authentication middleware
        with patch("document_service.src.api.documents.get_current_user") as mock_get_user:
            mock_user = {"id": "user-123", "role": user_role}
            mock_get_user.return_value = mock_user
            
            # Make request
            response = client.get(f"/documents/{sample_document_id}")
            
            # Verify response based on role
            assert response.status_code == expected_status
            
            if expected_status == 200:
                data = response.json()
                assert data["document_id"] == sample_document_id
            else:
                data = response.json()
                assert "detail" in data
                assert "Permission denied" in data["detail"]
    
    def test_document_ownership_validation(self, client, mock_storage_service, sample_document,
                                         sample_document_id):
        """Test validation of document ownership before operations."""
        # Setup document with owner information
        sample_document.metadata["owner_id"] = "user-456"
        mock_storage_service.get_document.return_value = sample_document
        
        # Mock the authentication middleware
        with patch("document_service.src.api.documents.get_current_user") as mock_get_user:
            # User is not the owner
            mock_user = {"id": "user-123", "role": "user"}
            mock_get_user.return_value = mock_user
            
            # Make request
            response = client.post(f"/documents/{sample_document_id}/classify")
            
            # Verify response
            assert response.status_code == 403
            data = response.json()
            assert "detail" in data
            assert "You do not have permission to access this document" in data["detail"]


# Test cases for document version history
class TestDocumentVersionHistory:
    """Test cases for document version history functionality."""
    
    def test_document_update_maintains_version_history(self, mock_storage_service):
        """Test that document updates maintain version history."""
        storage_service = StorageService()
        object_key = "documents/2023/05/01/test-document.pdf"
        
        # Mock the current metadata
        current_metadata = {
            "document_id": "test-123",
            "version": "1",
            "content_length": "1024",
            "content_type": "application/pdf",
            "last_modified": datetime.utcnow().isoformat(),
            "server_side_encryption": "AES256",
            "e_tag": "abc123"
        }
        
        # New metadata to update
        update_metadata = {
            "classification": "bank_statement",
            "classification_confidence": "0.95"
        }
        
        # Mock the get_document_metadata and copy_object methods
        with patch.object(storage_service, 'get_document_metadata', return_value=(current_metadata, None)):
            with patch.object(storage_service.s3_client, 'copy_object') as mock_copy_object:
                # Call the update method
                success, error = storage_service.update_document_metadata(object_key, update_metadata)
                
                # Verify the update was successful
                assert success is True
                assert error is None
                
                # Verify copy_object was called with correct parameters
                mock_copy_object.assert_called_once()
                _, kwargs = mock_copy_object.call_args
                
                # Verify metadata includes version history
                assert "Metadata" in kwargs
                assert "version" in kwargs["Metadata"]
                assert kwargs["Metadata"]["version"] == "2"  # Version should be incremented
                
                # Verify new metadata was included
                assert kwargs["Metadata"]["classification"] == "bank_statement"
                assert kwargs["Metadata"]["classification_confidence"] == "0.95"
                
                # Verify encryption was maintained
                assert kwargs["ServerSideEncryption"] == "AES256"


# Run the tests
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])