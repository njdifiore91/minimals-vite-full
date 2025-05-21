import json
import os
import uuid
from datetime import datetime
from io import BytesIO
from unittest.mock import patch, MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from botocore.exceptions import ClientError

from src.types.documents import DocumentType, ProcessingStatus


@pytest.fixture
def document_response_schema():
    """Schema for validating document response."""
    return {
        "document_id": str,
        "metadata": dict,
        "status": str,
        "created_at": str,
        "updated_at": str,
        "classification": dict
    }


@pytest.fixture
def document_list_response_schema():
    """Schema for validating document list response."""
    return {
        "documents": [document_response_schema],
        "pagination": {
            "page": int,
            "page_size": int,
            "total_items": int,
            "total_pages": int
        }
    }


@pytest.fixture
def document_classification_response_schema():
    """Schema for validating document classification response."""
    return {
        "document_id": str,
        "status": str,
        "classification": {
            "document_type": str,
            "confidence": float,
            "requires_review": bool,
            "classified_at": str
        },
        "routing": {
            "destination": str,
            "routed_at": str
        }
    }


@pytest.fixture
def document_batch_response_schema():
    """Schema for validating batch document operation response."""
    return {
        "summary": {
            "total": int,
            "successful": int,
            "failed": int,
            "skipped": int
        },
        "results": {
            "successful": list,
            "failed": list,
            "skipped": list
        }
    }


class TestDocumentAPI:
    """Test suite for Document Service CRUD API endpoints."""

    def test_get_document_by_id_success(self, client, validate_response_schema, document_response_schema,
                                       mock_storage_service, mock_classification_service, auth_headers,
                                       create_test_document):
        """Test that the document retrieval endpoint returns a document by ID."""
        # Create a test document
        test_doc = create_test_document(DocumentType.APPLICATION)
        document_id = test_doc.metadata["document_id"]
        
        # Mock storage service to return the test document
        mock_storage_service.get_document_metadata.return_value = test_doc.metadata
        
        # Mock classification service to return classification results
        mock_classification_service.get_classification_result.return_value = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.95,
            "classified_at": datetime.now().isoformat()
        }
        
        # Make request to get document endpoint
        response = client.get(f"/documents/{document_id}", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["document_id"] == document_id
        assert "metadata" in data
        assert "status" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "classification" in data
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["classification"]["confidence"] == 0.95
        assert "classified_at" in data["classification"]
    
    def test_get_document_by_id_not_found(self, client, mock_storage_service, auth_headers):
        """Test that the document retrieval endpoint returns 404 for non-existent document."""
        # Generate a random document ID
        document_id = str(uuid.uuid4())
        
        # Mock storage service to return None (document not found)
        mock_storage_service.get_document_metadata.return_value = None
        
        # Make request to get document endpoint
        response = client.get(f"/documents/{document_id}", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Parse response data
        data = response.json()
        
        # Verify error message
        assert "detail" in data
        assert f"Document with ID {document_id} not found" in data["detail"]
    
    def test_get_document_by_id_server_error(self, client, mock_storage_service, auth_headers):
        """Test that the document retrieval endpoint handles server errors properly."""
        # Generate a random document ID
        document_id = str(uuid.uuid4())
        
        # Mock storage service to raise an exception
        mock_storage_service.get_document_metadata.side_effect = Exception("Database connection error")
        
        # Make request to get document endpoint
        response = client.get(f"/documents/{document_id}", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Parse response data
        data = response.json()
        
        # Verify error message
        assert "detail" in data
        assert "An error occurred" in data["detail"]
    
    def test_classify_document_success(self, client, validate_response_schema, document_classification_response_schema,
                                      mock_storage_service, mock_classification_service, mock_document_routing_service,
                                      auth_headers, create_test_document):
        """Test that the document classification endpoint successfully classifies a document."""
        # Create a test document
        test_doc = create_test_document(DocumentType.APPLICATION)
        document_id = test_doc.metadata["document_id"]
        
        # Mock storage service to return the test document
        mock_storage_service.get_document.return_value = test_doc
        mock_storage_service.update_document_metadata.return_value = True
        
        # Mock classification service to return classification results
        classification_result = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.95,
            "classified_at": datetime.now().isoformat()
        }
        mock_classification_service.get_classification_result.return_value = None  # No existing classification
        mock_classification_service.classify_document.return_value = classification_result
        
        # Mock document routing service
        routing_result = {
            "destination": "ocr-service",
            "routed_at": datetime.now().isoformat()
        }
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Make request to classify document endpoint
        response = client.post(f"/documents/{document_id}/classify", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_classification_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["document_id"] == document_id
        assert data["status"] == "classification_complete"
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["classification"]["confidence"] == 0.95
        assert "classified_at" in data["classification"]
        assert data["routing"]["destination"] == "ocr-service"
        assert "routed_at" in data["routing"]
        
        # Verify that the document was updated with the new status
        mock_storage_service.update_document_metadata.assert_called_once()
    
    def test_classify_document_already_classified(self, client, validate_response_schema, 
                                                document_classification_response_schema,
                                                mock_storage_service, mock_classification_service,
                                                auth_headers, create_test_document):
        """Test that the document classification endpoint handles already classified documents."""
        # Create a test document
        test_doc = create_test_document(DocumentType.APPLICATION)
        document_id = test_doc.metadata["document_id"]
        
        # Mock storage service to return the test document
        mock_storage_service.get_document.return_value = test_doc
        
        # Mock classification service to return existing classification
        existing_classification = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.95,
            "classified_at": datetime.now().isoformat()
        }
        mock_classification_service.get_classification_result.return_value = existing_classification
        
        # Make request to classify document endpoint without force parameter
        response = client.post(f"/documents/{document_id}/classify", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_classification_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content indicates already classified
        assert data["document_id"] == document_id
        assert data["status"] == "already_classified"
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["classification"]["confidence"] == 0.95
        
        # Verify that classify_document was not called
        mock_classification_service.classify_document.assert_not_called()
    
    def test_classify_document_force_reclassification(self, client, validate_response_schema,
                                                    document_classification_response_schema,
                                                    mock_storage_service, mock_classification_service,
                                                    mock_document_routing_service, auth_headers,
                                                    create_test_document):
        """Test that the document classification endpoint forces reclassification when requested."""
        # Create a test document
        test_doc = create_test_document(DocumentType.APPLICATION)
        document_id = test_doc.metadata["document_id"]
        
        # Mock storage service to return the test document
        mock_storage_service.get_document.return_value = test_doc
        mock_storage_service.update_document_metadata.return_value = True
        
        # Mock classification service
        existing_classification = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.85,
            "classified_at": datetime.now().isoformat()
        }
        new_classification = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.98,
            "classified_at": datetime.now().isoformat()
        }
        mock_classification_service.get_classification_result.return_value = existing_classification
        mock_classification_service.classify_document.return_value = new_classification
        
        # Mock document routing service
        routing_result = {
            "destination": "ocr-service",
            "routed_at": datetime.now().isoformat()
        }
        mock_document_routing_service.route_document.return_value = routing_result
        
        # Make request to classify document endpoint with force=True
        response = client.post(f"/documents/{document_id}/classify?force=true", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_classification_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content shows new classification
        assert data["document_id"] == document_id
        assert data["status"] == "classification_complete"
        assert data["classification"]["document_type"] == DocumentType.APPLICATION.value
        assert data["classification"]["confidence"] == 0.98  # New confidence score
        
        # Verify that classify_document was called
        mock_classification_service.classify_document.assert_called_once()
    
    def test_batch_classify_documents_success(self, client, validate_response_schema, document_batch_response_schema,
                                            mock_storage_service, mock_classification_service, auth_headers,
                                            create_test_document):
        """Test that the batch document classification endpoint successfully queues documents for classification."""
        # Create test documents
        doc_ids = [str(uuid.uuid4()) for _ in range(3)]
        test_docs = [create_test_document(DocumentType.APPLICATION) for _ in range(3)]
        
        # Update document IDs to match our test IDs
        for i, doc in enumerate(test_docs):
            doc.metadata["document_id"] = doc_ids[i]
        
        # Mock storage service
        def get_document_side_effect(doc_id):
            for doc in test_docs:
                if doc.metadata["document_id"] == doc_id:
                    return doc
            return None
        
        mock_storage_service.get_document.side_effect = get_document_side_effect
        
        # Mock classification service
        mock_classification_service.get_classification_result.return_value = None  # No existing classifications
        mock_classification_service.queue_for_classification.return_value = True
        
        # Make request to batch classify endpoint
        request_data = {"document_ids": doc_ids}
        response = client.post("/documents/batch", json=request_data, headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_batch_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["summary"]["total"] == 3
        assert data["summary"]["successful"] == 3
        assert data["summary"]["failed"] == 0
        assert data["summary"]["skipped"] == 0
        assert len(data["results"]["successful"]) == 3
        assert len(data["results"]["failed"]) == 0
        assert len(data["results"]["skipped"]) == 0
        
        # Verify that queue_for_classification was called for each document
        assert mock_classification_service.queue_for_classification.call_count == 3
    
    def test_batch_classify_documents_mixed_results(self, client, validate_response_schema, 
                                                  document_batch_response_schema,
                                                  mock_storage_service, mock_classification_service, 
                                                  auth_headers, create_test_document):
        """Test that the batch document classification endpoint handles mixed success/failure/skipped results."""
        # Create test documents
        doc_ids = [str(uuid.uuid4()) for _ in range(3)]
        test_docs = [create_test_document(DocumentType.APPLICATION) for _ in range(2)]  # Only 2 docs exist
        
        # Update document IDs to match our test IDs
        for i, doc in enumerate(test_docs):
            doc.metadata["document_id"] = doc_ids[i]
        
        # Mock storage service
        def get_document_side_effect(doc_id):
            if doc_id == doc_ids[0]:
                return test_docs[0]  # First document exists
            elif doc_id == doc_ids[1]:
                return test_docs[1]  # Second document exists
            else:
                return None  # Third document doesn't exist
        
        mock_storage_service.get_document.side_effect = get_document_side_effect
        
        # Mock classification service
        def get_classification_result_side_effect(doc_id):
            if doc_id == doc_ids[0]:
                # First document is already classified
                return {
                    "document_type": DocumentType.APPLICATION,
                    "confidence": 0.95,
                    "classified_at": datetime.now().isoformat()
                }
            else:
                # Others are not classified
                return None
        
        mock_classification_service.get_classification_result.side_effect = get_classification_result_side_effect
        mock_classification_service.queue_for_classification.return_value = True
        
        # Make request to batch classify endpoint
        request_data = {"document_ids": doc_ids}
        response = client.post("/documents/batch", json=request_data, headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_batch_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["summary"]["total"] == 3
        assert data["summary"]["successful"] == 1  # Only one document successfully queued
        assert data["summary"]["failed"] == 1  # One document not found
        assert data["summary"]["skipped"] == 1  # One document already classified
        assert len(data["results"]["successful"]) == 1
        assert len(data["results"]["failed"]) == 1
        assert len(data["results"]["skipped"]) == 1
        
        # Verify that queue_for_classification was called only once
        assert mock_classification_service.queue_for_classification.call_count == 1
    
    def test_list_documents_success(self, client, validate_response_schema, document_list_response_schema,
                                  mock_storage_service, mock_classification_service, auth_headers,
                                  create_test_documents):
        """Test that the document list endpoint returns a paginated list of documents."""
        # Create test documents
        test_docs = create_test_documents(5)
        
        # Mock storage service
        mock_storage_service.list_documents.return_value = (test_docs, 5)  # 5 documents, 5 total
        
        # Mock classification service to return classification for each document
        def get_classification_result_side_effect(doc_id):
            return {
                "document_type": DocumentType.APPLICATION,
                "confidence": 0.95,
                "classified_at": datetime.now().isoformat()
            }
        
        mock_classification_service.get_classification_result.side_effect = get_classification_result_side_effect
        
        # Make request to list documents endpoint
        response = client.get("/documents?page=1&page_size=10", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_list_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert "documents" in data
        assert "pagination" in data
        assert len(data["documents"]) == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 10
        assert data["pagination"]["total_items"] == 5
        assert data["pagination"]["total_pages"] == 1
        
        # Verify that each document has classification data
        for doc in data["documents"]:
            assert "classification" in doc
            assert doc["classification"]["document_type"] == DocumentType.APPLICATION.value
            assert doc["classification"]["confidence"] == 0.95
    
    def test_list_documents_with_filters(self, client, validate_response_schema, document_list_response_schema,
                                        mock_storage_service, mock_classification_service, auth_headers,
                                        create_test_documents):
        """Test that the document list endpoint correctly applies filters."""
        # Create test documents
        test_docs = create_test_documents(3)
        
        # Mock storage service
        mock_storage_service.list_documents.return_value = (test_docs, 3)  # 3 documents, 3 total
        
        # Mock classification service
        mock_classification_service.get_classification_result.return_value = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.95,
            "classified_at": datetime.now().isoformat()
        }
        
        # Make request to list documents endpoint with filters
        query_params = "document_type=application&status=classified&confidence_min=0.8&requires_review=false"
        response = client.get(f"/documents?{query_params}", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_list_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify that list_documents was called with the correct filters
        mock_storage_service.list_documents.assert_called_once_with(
            document_type=DocumentType.APPLICATION,
            status=ProcessingStatus.CLASSIFIED,
            confidence_min=0.8,
            confidence_max=None,
            requires_review=False,
            page=1,
            page_size=20
        )
    
    def test_list_documents_invalid_filter(self, client, auth_headers):
        """Test that the document list endpoint handles invalid filter values."""
        # Make request with invalid document_type
        response = client.get("/documents?document_type=invalid_type", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse response data
        data = response.json()
        
        # Verify error message
        assert "detail" in data
        assert "Invalid document type" in data["detail"]
        
        # Make request with invalid status
        response = client.get("/documents?status=invalid_status", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        
        # Parse response data
        data = response.json()
        
        # Verify error message
        assert "detail" in data
        assert "Invalid status" in data["detail"]
    
    def test_s3_storage_integration_with_encryption(self, client, mock_s3_client, auth_headers):
        """Test that documents are stored in S3 with AES-256 encryption."""
        # Create a test file
        file_content = b"Test document content"
        file = BytesIO(file_content)
        file.name = "test_document.pdf"
        
        # Create multipart form data
        files = {"file": ("test_document.pdf", file, "application/pdf")}
        data = {"application_id": str(uuid.uuid4())}
        
        # Make request to upload document endpoint
        response = client.post("/documents/upload", files=files, data=data, headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_201_CREATED
        
        # Parse response data
        data = response.json()
        
        # Verify document was created
        assert "document_id" in data
        assert "storage_path" in data
        
        # Verify document was stored in S3 with encryption
        document_key = data["storage_path"]
        s3_object = mock_s3_client.get_object(Bucket="mca-documents-test", Key=document_key)
        
        # Check that the object has the ServerSideEncryption header set to AES256
        assert "ServerSideEncryption" in s3_object
        assert s3_object["ServerSideEncryption"] == "AES256"
        
        # Verify the content was stored correctly
        assert s3_object["Body"].read() == file_content
    
    def test_document_upload_with_metadata_extraction(self, client, mock_s3_client, auth_headers):
        """Test that document upload extracts and stores metadata."""
        # Create a test file
        file_content = b"%PDF-1.5\nTest document with metadata"
        file = BytesIO(file_content)
        file.name = "financial_statement.pdf"
        
        # Create multipart form data
        files = {"file": ("financial_statement.pdf", file, "application/pdf")}
        data = {
            "application_id": str(uuid.uuid4()),
            "document_type": "bank_statement",
            "metadata": json.dumps({
                "bank_name": "Test Bank",
                "account_number": "XXXX1234",
                "statement_date": "2023-04-01"
            })
        }
        
        # Make request to upload document endpoint
        response = client.post("/documents/upload", files=files, data=data, headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_201_CREATED
        
        # Parse response data
        data = response.json()
        
        # Verify document was created with metadata
        assert "document_id" in data
        assert "metadata" in data
        assert "bank_name" in data["metadata"]
        assert data["metadata"]["bank_name"] == "Test Bank"
        assert "account_number" in data["metadata"]
        assert data["metadata"]["account_number"] == "XXXX1234"
        assert "statement_date" in data["metadata"]
        assert data["metadata"]["statement_date"] == "2023-04-01"
        
        # Verify document type was set correctly
        assert "document_type" in data
        assert data["document_type"] == "bank_statement"
    
    def test_document_update_maintains_version_history(self, client, mock_s3_client, auth_headers):
        """Test that document updates maintain version history in S3."""
        # Create a test document in S3
        document_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        document_key = f"applications/{application_id}/documents/{document_id}/v1.pdf"
        
        # Upload initial version to S3
        mock_s3_client.put_object(
            Bucket="mca-documents-test",
            Key=document_key,
            Body=b"Initial document content",
            Metadata={
                "document_id": document_id,
                "application_id": application_id,
                "version": "1"
            },
            ServerSideEncryption="AES256"
        )
        
        # Create update data
        update_data = {
            "metadata": {
                "status": "reviewed",
                "reviewer": "test-user",
                "review_date": datetime.now().isoformat()
            }
        }
        
        # Make request to update document endpoint
        response = client.put(f"/documents/{document_id}", json=update_data, headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Verify document was updated
        assert "document_id" in data
        assert data["document_id"] == document_id
        assert "version" in data
        assert data["version"] == "2"  # Version incremented
        
        # Verify that both versions exist in S3
        v1_key = document_key
        v2_key = f"applications/{application_id}/documents/{document_id}/v2.pdf"
        
        # Check v1 still exists
        v1_object = mock_s3_client.get_object(Bucket="mca-documents-test", Key=v1_key)
        assert v1_object["Metadata"]["version"] == "1"
        
        # Check v2 exists with updated metadata
        v2_object = mock_s3_client.get_object(Bucket="mca-documents-test", Key=v2_key)
        assert v2_object["Metadata"]["version"] == "2"
        assert "status" in v2_object["Metadata"]
        assert v2_object["Metadata"]["status"] == "reviewed"
    
    def test_document_deletion_and_archiving(self, client, mock_s3_client, auth_headers):
        """Test that document deletion properly archives documents instead of permanently deleting them."""
        # Create a test document in S3
        document_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        document_key = f"applications/{application_id}/documents/{document_id}/v1.pdf"
        
        # Upload document to S3
        mock_s3_client.put_object(
            Bucket="mca-documents-test",
            Key=document_key,
            Body=b"Document content",
            Metadata={
                "document_id": document_id,
                "application_id": application_id,
                "version": "1"
            },
            ServerSideEncryption="AES256"
        )
        
        # Make request to delete document endpoint
        response = client.delete(f"/documents/{document_id}", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Verify document was marked as deleted
        assert "document_id" in data
        assert data["document_id"] == document_id
        assert "status" in data
        assert data["status"] == "archived"
        
        # Verify that the document was moved to the archive location
        archive_key = f"archive/applications/{application_id}/documents/{document_id}/v1.pdf"
        
        # Original location should no longer have the document
        with pytest.raises(ClientError):
            mock_s3_client.get_object(Bucket="mca-documents-test", Key=document_key)
        
        # Archive location should have the document
        archived_object = mock_s3_client.get_object(Bucket="mca-documents-test", Key=archive_key)
        assert archived_object["Metadata"]["document_id"] == document_id
        assert archived_object["Metadata"]["application_id"] == application_id
        assert "archived_at" in archived_object["Metadata"]
        assert "archived_by" in archived_object["Metadata"]
    
    def test_document_retrieval_by_application_id(self, client, validate_response_schema, 
                                                document_list_response_schema,
                                                mock_storage_service, mock_classification_service, 
                                                auth_headers, create_test_documents):
        """Test that documents can be retrieved by application ID."""
        # Create test documents with the same application ID
        application_id = str(uuid.uuid4())
        test_docs = create_test_documents(3)
        
        # Set the same application ID for all documents
        for doc in test_docs:
            doc.metadata["application_id"] = application_id
        
        # Mock storage service
        mock_storage_service.list_documents_by_application_id.return_value = (test_docs, 3)
        
        # Mock classification service
        mock_classification_service.get_classification_result.return_value = {
            "document_type": DocumentType.APPLICATION,
            "confidence": 0.95,
            "classified_at": datetime.now().isoformat()
        }
        
        # Make request to get documents by application ID
        response = client.get(f"/applications/{application_id}/documents", headers=auth_headers)
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, document_list_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert "documents" in data
        assert len(data["documents"]) == 3
        
        # Verify all documents have the same application ID
        for doc in data["documents"]:
            assert doc["metadata"]["application_id"] == application_id
        
        # Verify that list_documents_by_application_id was called with the correct parameters
        mock_storage_service.list_documents_by_application_id.assert_called_once_with(
            application_id=application_id,
            page=1,
            page_size=20
        )
    
    def test_document_ownership_validation(self, client, mock_storage_service, auth_headers):
        """Test that document operations validate document ownership."""
        # Create document IDs
        document_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        
        # Mock storage service to return document metadata
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": document_id,
            "application_id": application_id,
            "owner_id": "different-user-id"  # Different from the authenticated user
        }
        
        # Make request to update document endpoint
        update_data = {"metadata": {"status": "reviewed"}}
        response = client.put(f"/documents/{document_id}", json=update_data, headers=auth_headers)
        
        # Verify response status code indicates forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Parse response data
        data = response.json()
        
        # Verify error message
        assert "detail" in data
        assert "You do not have permission to modify this document" in data["detail"]
        
        # Make request to delete document endpoint
        response = client.delete(f"/documents/{document_id}", headers=auth_headers)
        
        # Verify response status code indicates forbidden
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Parse response data
        data = response.json()
        
        # Verify error message
        assert "detail" in data
        assert "You do not have permission to delete this document" in data["detail"]