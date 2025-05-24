#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for Document Service classification API endpoints.

This module contains unit tests for the document classification API endpoints,
verifying that the API correctly handles document classification requests,
validates input parameters, processes document classification operations,
and returns appropriate responses with confidence scores.

The tests cover:
1. Successful classification of various document types
2. Validation of input parameters and file formats
3. Error handling for invalid requests and server errors
4. Confidence score validation in classification responses
5. Verification of 99% accuracy requirement
"""

import json
import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi import status
from io import BytesIO

# Import test fixtures
from conftest import (
    TEST_DOCUMENT_TYPES,
    TEST_FILE_FORMATS,
    TEST_BUCKET_NAME
)


# ============================================================================
# Classification API Tests
# ============================================================================

class TestClassificationAPI:
    """Test suite for document classification API endpoints."""

    # ========================================================================
    # Single Document Classification Tests
    # ========================================================================

    def test_classify_document_success(self, test_client, mock_classification_model, 
                                      mock_s3_storage, generate_test_document,
                                      mock_auth_headers, validate_response):
        """Test successful classification of a document."""
        # Generate a test document
        document_type = "LOAN_APPLICATION"
        file_format = "pdf"
        content, metadata = generate_test_document(document_type, file_format)
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service to use our mock model
            with patch('src.api.documents.get_classification_service', return_value=mock_classification_model):
                # Upload the document to mock storage
                mock_s3_storage.upload_document(
                    document_data=content,
                    document_key=f"documents/{document_id}.{file_format}",
                    metadata=metadata
                )
                
                # Make the API request
                response = test_client.post(
                    f"/documents/{document_id}/classify",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert response_json["document_id"] == document_id
                assert response_json["status"] == "classification_complete"
                assert "classification" in response_json
                assert "document_type" in response_json["classification"]
                assert "confidence" in response_json["classification"]
                assert "requires_review" in response_json["classification"]
                assert "classified_at" in response_json["classification"]
                
                # Verify confidence score is a float between 0 and 1
                confidence = response_json["classification"]["confidence"]
                assert isinstance(confidence, float)
                assert 0 <= confidence <= 1
                
                # Verify document type is valid
                assert response_json["classification"]["document_type"] in [
                    doc_type.lower() for doc_type in TEST_DOCUMENT_TYPES
                ]

    def test_classify_document_with_high_accuracy(self, test_client, mock_classification_model, 
                                                mock_s3_storage, generate_test_document,
                                                mock_auth_headers):
        """Test that document classification meets 99% accuracy requirement."""
        # Set model accuracy to 99%
        mock_classification_model.set_accuracy(0.99)
        
        # Generate a test document
        document_type = "LOAN_APPLICATION"
        file_format = "pdf"
        content, metadata = generate_test_document(document_type, file_format)
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service to use our mock model
            with patch('src.api.documents.get_classification_service', return_value=mock_classification_model):
                # Upload the document to mock storage
                mock_s3_storage.upload_document(
                    document_data=content,
                    document_key=f"documents/{document_id}.{file_format}",
                    metadata=metadata
                )
                
                # Make the API request
                response = test_client.post(
                    f"/documents/{document_id}/classify",
                    headers=mock_auth_headers
                )
                
                # Check response status
                assert response.status_code == status.HTTP_200_OK
                
                # Check confidence score meets accuracy requirement
                response_json = response.json()
                confidence = response_json["classification"]["confidence"]
                assert confidence >= 0.99, "Classification confidence should be at least 99%"

    def test_classify_document_not_found(self, test_client, mock_classification_model, 
                                        mock_s3_storage, mock_auth_headers,
                                        validate_response):
        """Test classification of a non-existent document."""
        # Create a random document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return None
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service', return_value=mock_classification_model):
                # Make the API request
                response = test_client.post(
                    f"/documents/{document_id}/classify",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_404_NOT_FOUND)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert f"Document with ID {document_id} not found" in response_json["detail"]

    def test_classify_document_already_classified(self, test_client, mock_classification_model, 
                                                mock_s3_storage, generate_test_document,
                                                mock_auth_headers, validate_response):
        """Test classification of an already classified document without force flag."""
        # Generate a test document
        document_type = "BANK_STATEMENT"
        file_format = "pdf"
        content, metadata = generate_test_document(document_type, file_format)
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Add classification result to metadata
        metadata["classification_confidence"] = 0.95
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service to return an existing classification
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return an existing classification result
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = {
                    "document_type": document_type,
                    "confidence": 0.95,
                    "classified_at": datetime.now()
                }
                mock_get_classification_service.return_value = mock_service
                
                # Upload the document to mock storage
                mock_s3_storage.upload_document(
                    document_data=content,
                    document_key=f"documents/{document_id}.{file_format}",
                    metadata=metadata
                )
                
                # Make the API request without force flag
                response = test_client.post(
                    f"/documents/{document_id}/classify",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert response_json["document_id"] == document_id
                assert response_json["status"] == "already_classified"
                assert "classification" in response_json
                assert response_json["classification"]["document_type"] == document_type.lower()
                assert response_json["classification"]["confidence"] == 0.95

    def test_classify_document_force_reclassification(self, test_client, mock_classification_model, 
                                                    mock_s3_storage, generate_test_document,
                                                    mock_auth_headers, validate_response):
        """Test force reclassification of an already classified document."""
        # Generate a test document
        document_type = "TAX_RETURN"
        file_format = "pdf"
        content, metadata = generate_test_document(document_type, file_format)
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Add classification result to metadata
        metadata["classification_confidence"] = 0.95
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return an existing classification result
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = {
                    "document_type": document_type,
                    "confidence": 0.95,
                    "classified_at": datetime.now()
                }
                # Configure the classify_document method to return a new classification
                mock_service.classify_document.return_value = {
                    "document_type": document_type,
                    "confidence": 0.99,
                    "classified_at": datetime.now()
                }
                mock_get_classification_service.return_value = mock_service
                
                # Mock the document routing service
                with patch('src.api.documents.get_document_routing_service') as mock_get_routing_service:
                    mock_routing_service = MagicMock()
                    mock_routing_service.route_document.return_value = {
                        "destination": "ocr-service",
                        "routed_at": datetime.now()
                    }
                    mock_get_routing_service.return_value = mock_routing_service
                    
                    # Upload the document to mock storage
                    mock_s3_storage.upload_document(
                        document_data=content,
                        document_key=f"documents/{document_id}.{file_format}",
                        metadata=metadata
                    )
                    
                    # Make the API request with force flag
                    response = test_client.post(
                        f"/documents/{document_id}/classify?force=true",
                        headers=mock_auth_headers
                    )
                    
                    # Validate the response
                    validate_response(response, expected_status_code=status.HTTP_200_OK)
                    
                    # Check response content
                    response_json = response.json()
                    assert response_json["document_id"] == document_id
                    assert response_json["status"] == "classification_complete"
                    assert "classification" in response_json
                    assert response_json["classification"]["document_type"] == document_type.lower()
                    assert response_json["classification"]["confidence"] == 0.99

    def test_classify_document_invalid_format(self, test_client, mock_classification_model, 
                                            mock_s3_storage, generate_test_document,
                                            mock_auth_headers, validate_response):
        """Test classification of a document with invalid format."""
        # Generate a test document with invalid format
        document_type = "LOAN_APPLICATION"
        file_format = "invalid"
        content = b"Invalid document content"
        metadata = {
            "document_type": document_type,
            "file_format": file_format,
            "created_at": datetime.now().isoformat(),
            "document_id": str(uuid.uuid4()),
            "application_id": str(uuid.uuid4()),
            "size": len(content)
        }
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service to raise a validation error
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to raise a validation error
                from src.types.errors import ValidationError
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = None
                mock_service.classify_document.side_effect = ValidationError(
                    "Unsupported document format: invalid",
                    {"format": "invalid", "supported_formats": TEST_FILE_FORMATS}
                )
                mock_get_classification_service.return_value = mock_service
                
                # Upload the document to mock storage
                mock_s3_storage.upload_document(
                    document_data=content,
                    document_key=f"documents/{document_id}.{file_format}",
                    metadata=metadata
                )
                
                # Make the API request
                response = test_client.post(
                    f"/documents/{document_id}/classify",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_400_BAD_REQUEST)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert "Unsupported document format" in response_json["detail"]

    # ========================================================================
    # Batch Document Classification Tests
    # ========================================================================

    def test_batch_classify_documents_success(self, test_client, mock_classification_model, 
                                            mock_s3_storage, generate_test_documents,
                                            mock_auth_headers, validate_response):
        """Test successful batch classification of documents."""
        # Generate multiple test documents
        documents = generate_test_documents(count=3)
        document_ids = []
        
        # Upload documents to mock storage
        for i, (content, metadata) in enumerate(documents):
            document_id = str(uuid.uuid4())
            document_ids.append(document_id)
            
            mock_s3_storage.upload_document(
                document_data=content,
                document_key=f"documents/{document_id}.{metadata['file_format']}",
                metadata=metadata
            )
        
        # Mock the storage service to return the documents
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = None
                mock_service.queue_for_classification.return_value = True
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request
                response = test_client.post(
                    "/documents/batch",
                    headers=mock_auth_headers,
                    json={"document_ids": document_ids}
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert "summary" in response_json
                assert "results" in response_json
                assert response_json["summary"]["total"] == len(document_ids)
                assert response_json["summary"]["successful"] == len(document_ids)
                assert response_json["summary"]["failed"] == 0
                assert response_json["summary"]["skipped"] == 0
                
                # Check that each document was queued for classification
                for document_id in document_ids:
                    assert any(result["document_id"] == document_id for result in response_json["results"]["successful"])

    def test_batch_classify_empty_list(self, test_client, mock_classification_model, 
                                      mock_s3_storage, mock_auth_headers,
                                      validate_response):
        """Test batch classification with an empty document list."""
        # Mock the storage service
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service', return_value=mock_classification_model):
                # Make the API request with empty list
                response = test_client.post(
                    "/documents/batch",
                    headers=mock_auth_headers,
                    json={"document_ids": []}
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_400_BAD_REQUEST)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert "No document IDs provided" in response_json["detail"]

    def test_batch_classify_too_many_documents(self, test_client, mock_classification_model, 
                                             mock_s3_storage, mock_auth_headers,
                                             validate_response):
        """Test batch classification with too many documents."""
        # Create a list of 101 document IDs (exceeding the limit of 100)
        document_ids = [str(uuid.uuid4()) for _ in range(101)]
        
        # Mock the storage service
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service', return_value=mock_classification_model):
                # Make the API request with too many documents
                response = test_client.post(
                    "/documents/batch",
                    headers=mock_auth_headers,
                    json={"document_ids": document_ids}
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_400_BAD_REQUEST)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert "Batch size exceeds maximum limit" in response_json["detail"]

    def test_batch_classify_mixed_results(self, test_client, mock_classification_model, 
                                        mock_s3_storage, generate_test_documents,
                                        mock_auth_headers, validate_response):
        """Test batch classification with mixed results (success, failure, skipped)."""
        # Generate test documents
        documents = generate_test_documents(count=3)
        document_ids = []
        
        # Upload documents to mock storage
        for i, (content, metadata) in enumerate(documents):
            document_id = str(uuid.uuid4())
            document_ids.append(document_id)
            
            # For the first document, add classification result to metadata
            if i == 0:
                metadata["classification_confidence"] = 0.95
            
            mock_s3_storage.upload_document(
                document_data=content,
                document_key=f"documents/{document_id}.{metadata['file_format']}",
                metadata=metadata
            )
        
        # Add a non-existent document ID
        document_ids.append(str(uuid.uuid4()))
        
        # Mock the storage service
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock
                mock_service = MagicMock()
                
                # Return existing classification for first document
                def get_classification_result(doc_id):
                    if doc_id == document_ids[0]:
                        return {
                            "document_type": "LOAN_APPLICATION",
                            "confidence": 0.95,
                            "classified_at": datetime.now()
                        }
                    return None
                
                mock_service.get_classification_result.side_effect = get_classification_result
                mock_service.queue_for_classification.return_value = True
                
                # For the last document (non-existent), make get_document return None
                def get_document(doc_id):
                    if doc_id == document_ids[-1]:
                        return None
                    return {"id": doc_id, "metadata": {}}
                
                mock_s3_storage.get_document.side_effect = get_document
                
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request
                response = test_client.post(
                    "/documents/batch",
                    headers=mock_auth_headers,
                    json={"document_ids": document_ids}
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert "summary" in response_json
                assert "results" in response_json
                assert response_json["summary"]["total"] == len(document_ids)
                assert response_json["summary"]["successful"] == 2  # 2 successful
                assert response_json["summary"]["failed"] == 1  # 1 failed (non-existent)
                assert response_json["summary"]["skipped"] == 1  # 1 skipped (already classified)
                
                # Check successful documents
                successful_ids = [result["document_id"] for result in response_json["results"]["successful"]]
                assert document_ids[1] in successful_ids
                assert document_ids[2] in successful_ids
                
                # Check skipped documents
                skipped_ids = [result["document_id"] for result in response_json["results"]["skipped"]]
                assert document_ids[0] in skipped_ids
                
                # Check failed documents
                failed_ids = [result["document_id"] for result in response_json["results"]["failed"]]
                assert document_ids[3] in failed_ids

    # ========================================================================
    # Document Retrieval Tests
    # ========================================================================

    def test_get_document_classification(self, test_client, mock_classification_model, 
                                        mock_s3_storage, generate_test_document,
                                        mock_auth_headers, validate_response):
        """Test retrieval of document classification status."""
        # Generate a test document
        document_type = "BANK_STATEMENT"
        file_format = "pdf"
        content, metadata = generate_test_document(document_type, file_format)
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service') as mock_get_storage_service:
            # Configure the mock to return document metadata
            mock_storage = MagicMock()
            mock_storage.get_document_metadata.return_value = {
                "id": document_id,
                "metadata": metadata,
                "status": "classified",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            mock_get_storage_service.return_value = mock_storage
            
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return classification result
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = {
                    "document_type": document_type,
                    "confidence": 0.95,
                    "classified_at": datetime.now()
                }
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request
                response = test_client.get(
                    f"/documents/{document_id}",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert response_json["document_id"] == document_id
                assert "metadata" in response_json
                assert "status" in response_json
                assert "classification" in response_json
                assert response_json["classification"]["document_type"] == document_type.lower()
                assert response_json["classification"]["confidence"] == 0.95
                assert "requires_review" in response_json["classification"]
                assert "classified_at" in response_json["classification"]

    def test_get_document_not_found(self, test_client, mock_classification_model, 
                                  mock_s3_storage, mock_auth_headers,
                                  validate_response):
        """Test retrieval of a non-existent document."""
        # Create a random document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return None
        with patch('src.api.documents.get_storage_service') as mock_get_storage_service:
            # Configure the mock to return None
            mock_storage = MagicMock()
            mock_storage.get_document_metadata.return_value = None
            mock_get_storage_service.return_value = mock_storage
            
            # Make the API request
            response = test_client.get(
                f"/documents/{document_id}",
                headers=mock_auth_headers
            )
            
            # Validate the response
            validate_response(response, expected_status_code=status.HTTP_404_NOT_FOUND)
            
            # Check error message
            response_json = response.json()
            assert "detail" in response_json
            assert f"Document with ID {document_id} not found" in response_json["detail"]

    def test_get_document_without_classification(self, test_client, mock_classification_model, 
                                               mock_s3_storage, generate_test_document,
                                               mock_auth_headers, validate_response):
        """Test retrieval of a document without classification result."""
        # Generate a test document
        document_type = "TAX_RETURN"
        file_format = "pdf"
        content, metadata = generate_test_document(document_type, file_format)
        
        # Create a document ID
        document_id = str(uuid.uuid4())
        
        # Mock the storage service to return the document
        with patch('src.api.documents.get_storage_service') as mock_get_storage_service:
            # Configure the mock to return document metadata
            mock_storage = MagicMock()
            mock_storage.get_document_metadata.return_value = {
                "id": document_id,
                "metadata": metadata,
                "status": "received",
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            mock_get_storage_service.return_value = mock_storage
            
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return None for classification result
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = None
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request
                response = test_client.get(
                    f"/documents/{document_id}",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert response_json["document_id"] == document_id
                assert "metadata" in response_json
                assert "status" in response_json
                assert "classification" not in response_json

    # ========================================================================
    # Document Listing Tests
    # ========================================================================

    def test_list_documents(self, test_client, mock_classification_model, 
                          mock_s3_storage, mock_auth_headers,
                          validate_response):
        """Test listing of documents with default parameters."""
        # Mock the storage service
        with patch('src.api.documents.get_storage_service') as mock_get_storage_service:
            # Configure the mock to return a list of documents
            mock_storage = MagicMock()
            documents = [
                {
                    "id": str(uuid.uuid4()),
                    "metadata": {
                        "document_type": "LOAN_APPLICATION",
                        "file_format": "pdf",
                        "created_at": datetime.now().isoformat(),
                        "application_id": str(uuid.uuid4()),
                        "size": 1024
                    },
                    "status": "classified",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                },
                {
                    "id": str(uuid.uuid4()),
                    "metadata": {
                        "document_type": "BANK_STATEMENT",
                        "file_format": "pdf",
                        "created_at": datetime.now().isoformat(),
                        "application_id": str(uuid.uuid4()),
                        "size": 2048
                    },
                    "status": "processed",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            ]
            mock_storage.list_documents.return_value = (documents, len(documents))
            mock_get_storage_service.return_value = mock_storage
            
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return classification results
                mock_service = MagicMock()
                
                def get_classification_result(doc_id):
                    for doc in documents:
                        if doc["id"] == doc_id:
                            return {
                                "document_type": doc["metadata"]["document_type"],
                                "confidence": 0.95,
                                "classified_at": datetime.now()
                            }
                    return None
                
                mock_service.get_classification_result.side_effect = get_classification_result
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request
                response = test_client.get(
                    "/documents",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert "documents" in response_json
                assert "pagination" in response_json
                assert len(response_json["documents"]) == len(documents)
                assert response_json["pagination"]["total_items"] == len(documents)
                assert response_json["pagination"]["page"] == 1
                
                # Check document content
                for doc in response_json["documents"]:
                    assert "document_id" in doc
                    assert "metadata" in doc
                    assert "status" in doc
                    assert "created_at" in doc
                    assert "updated_at" in doc
                    assert "classification" in doc
                    assert "document_type" in doc["classification"]
                    assert "confidence" in doc["classification"]
                    assert "requires_review" in doc["classification"]
                    assert "classified_at" in doc["classification"]

    def test_list_documents_with_filters(self, test_client, mock_classification_model, 
                                       mock_s3_storage, mock_auth_headers,
                                       validate_response):
        """Test listing of documents with filters."""
        # Mock the storage service
        with patch('src.api.documents.get_storage_service') as mock_get_storage_service:
            # Configure the mock to return a filtered list of documents
            mock_storage = MagicMock()
            documents = [
                {
                    "id": str(uuid.uuid4()),
                    "metadata": {
                        "document_type": "BANK_STATEMENT",
                        "file_format": "pdf",
                        "created_at": datetime.now().isoformat(),
                        "application_id": str(uuid.uuid4()),
                        "size": 2048
                    },
                    "status": "classified",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            ]
            mock_storage.list_documents.return_value = (documents, len(documents))
            mock_get_storage_service.return_value = mock_storage
            
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return classification results
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = {
                    "document_type": "BANK_STATEMENT",
                    "confidence": 0.85,
                    "classified_at": datetime.now()
                }
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request with filters
                response = test_client.get(
                    "/documents?document_type=bank_statement&status=classified&confidence_min=0.8&requires_review=true",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert "documents" in response_json
                assert "pagination" in response_json
                assert len(response_json["documents"]) == len(documents)
                
                # Verify that the storage service was called with the correct filters
                mock_storage.list_documents.assert_called_once()
                call_args = mock_storage.list_documents.call_args[1]
                assert call_args["document_type"] is not None
                assert call_args["status"] is not None
                assert call_args["confidence_min"] == 0.8
                assert call_args["requires_review"] is True

    def test_list_documents_pagination(self, test_client, mock_classification_model, 
                                     mock_s3_storage, mock_auth_headers,
                                     validate_response):
        """Test document listing with pagination."""
        # Mock the storage service
        with patch('src.api.documents.get_storage_service') as mock_get_storage_service:
            # Configure the mock to return a paginated list of documents
            mock_storage = MagicMock()
            
            # Create 30 documents (more than one page with default page_size=20)
            documents = []
            for i in range(30):
                documents.append({
                    "id": str(uuid.uuid4()),
                    "metadata": {
                        "document_type": random.choice(TEST_DOCUMENT_TYPES),
                        "file_format": random.choice(TEST_FILE_FORMATS),
                        "created_at": datetime.now().isoformat(),
                        "application_id": str(uuid.uuid4()),
                        "size": random.randint(1000, 5000)
                    },
                    "status": "classified",
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                })
            
            # Return only the second page (items 20-29)
            def list_documents(**kwargs):
                page = kwargs.get("page", 1)
                page_size = kwargs.get("page_size", 20)
                start_idx = (page - 1) * page_size
                end_idx = min(start_idx + page_size, len(documents))
                return (documents[start_idx:end_idx], len(documents))
            
            mock_storage.list_documents.side_effect = list_documents
            mock_get_storage_service.return_value = mock_storage
            
            # Mock the classification service
            with patch('src.api.documents.get_classification_service') as mock_get_classification_service:
                # Configure the mock to return classification results
                mock_service = MagicMock()
                mock_service.get_classification_result.return_value = {
                    "document_type": "LOAN_APPLICATION",
                    "confidence": 0.95,
                    "classified_at": datetime.now()
                }
                mock_get_classification_service.return_value = mock_service
                
                # Make the API request for page 2
                response = test_client.get(
                    "/documents?page=2&page_size=10",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_200_OK)
                
                # Check response content
                response_json = response.json()
                assert "documents" in response_json
                assert "pagination" in response_json
                assert len(response_json["documents"]) == 10  # page_size=10
                assert response_json["pagination"]["page"] == 2
                assert response_json["pagination"]["page_size"] == 10
                assert response_json["pagination"]["total_items"] == 30
                assert response_json["pagination"]["total_pages"] == 3  # 30 items with page_size=10

    def test_list_documents_invalid_filter(self, test_client, mock_classification_model, 
                                         mock_s3_storage, mock_auth_headers,
                                         validate_response):
        """Test document listing with invalid filter values."""
        # Mock the storage service
        with patch('src.api.documents.get_storage_service', return_value=mock_s3_storage):
            # Mock the classification service
            with patch('src.api.documents.get_classification_service', return_value=mock_classification_model):
                # Make the API request with invalid document type
                response = test_client.get(
                    "/documents?document_type=invalid_type",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_400_BAD_REQUEST)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert "Invalid document type" in response_json["detail"]
                
                # Make the API request with invalid status
                response = test_client.get(
                    "/documents?status=invalid_status",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_400_BAD_REQUEST)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert "Invalid status" in response_json["detail"]
                
                # Make the API request with invalid confidence range
                response = test_client.get(
                    "/documents?confidence_min=1.5",
                    headers=mock_auth_headers
                )
                
                # Validate the response
                validate_response(response, expected_status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
                
                # Check error message
                response_json = response.json()
                assert "detail" in response_json
                assert "confidence_min" in str(response_json["detail"])