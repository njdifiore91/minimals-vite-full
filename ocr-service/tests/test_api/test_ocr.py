#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for OCR processing endpoints in the OCR Service API.

This module contains tests for the OCR API endpoints that handle document processing,
result retrieval, batch processing, and confidence threshold management. It verifies
that the OCR endpoints correctly process documents, extract data with confidence scores,
and handle various document types.

The tests ensure that:
1. OCR results can be retrieved for processed documents
2. Documents can be manually processed with different parameters
3. Batch processing works correctly for multiple documents
4. Confidence thresholds can be retrieved and updated
5. Processing status can be checked for ongoing jobs
6. Error handling works correctly for invalid inputs and processing failures
7. OCR operations are properly logged

These tests are critical for ensuring the core OCR functionality works as expected
and integrates properly with the API layer.
"""

import json
import pytest
import uuid
from unittest.mock import patch, MagicMock
from fastapi import status
from typing import Dict, List, Any

# Import test fixtures
from .conftest import (
    app,
    client,
    mock_s3,
    auth_token,
    sample_document,
    sample_ocr_result,
    sample_ocr_result_with_low_confidence,
    validate_response,
    mock_tensorflow_service
)


# Tests for GET /ocr/{document_id} endpoint

def test_get_ocr_results_success(client, mock_s3, sample_ocr_result):
    """
    Test successful retrieval of OCR results for a document.
    
    This test verifies that the GET /ocr/{document_id} endpoint correctly returns
    OCR results when they exist for the specified document ID.
    """
    # Setup: Store a sample OCR result in the mock S3 storage
    document_id = sample_ocr_result["document_id"]
    
    # Mock the OCRService.get_ocr_results method to return the sample result
    with patch("services.OCRService.get_ocr_results", return_value=sample_ocr_result["extracted_data"]) as mock_get_results:
        # Mock the StorageService.document_exists method to return True
        with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
            # Make the request
            response = client.get(f"/ocr/{document_id}")
            
            # Verify the response
            assert response.status_code == status.HTTP_200_OK
            
            # Verify the response data
            response_data = response.json()
            assert "fields" in response_data
            assert "business_name" in response_data["fields"]
            assert response_data["fields"]["business_name"]["value"] == "Acme Corporation"
            assert response_data["fields"]["business_name"]["confidence"] == 0.98
            
            # Verify that the service methods were called correctly
            mock_document_exists.assert_called_once_with(document_id)
            mock_get_results.assert_called_once_with(document_id, True)


def test_get_ocr_results_document_not_found(client, mock_s3):
    """
    Test error handling when document is not found.
    
    This test verifies that the GET /ocr/{document_id} endpoint correctly returns
    a 404 error when the document does not exist.
    """
    # Generate a random document ID that doesn't exist
    document_id = str(uuid.uuid4())
    
    # Mock the StorageService.document_exists method to return False
    with patch("services.StorageService.document_exists", return_value=False) as mock_document_exists:
        # Make the request
        response = client.get(f"/ocr/{document_id}")
        
        # Verify the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify the error message
        response_data = response.json()
        assert "detail" in response_data
        assert f"Document {document_id} not found" in response_data["detail"]
        
        # Verify that the service method was called correctly
        mock_document_exists.assert_called_once_with(document_id)


def test_get_ocr_results_not_available(client, mock_s3):
    """
    Test error handling when OCR results are not available.
    
    This test verifies that the GET /ocr/{document_id} endpoint correctly returns
    a 404 error when OCR results are not available for the document.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.get_ocr_results method to return None
        with patch("services.OCRService.get_ocr_results", return_value=None) as mock_get_results:
            # Make the request
            response = client.get(f"/ocr/{document_id}")
            
            # Verify the response
            assert response.status_code == status.HTTP_404_NOT_FOUND
            
            # Verify the error message
            response_data = response.json()
            assert "detail" in response_data
            assert f"OCR results not available for document {document_id}" in response_data["detail"]
            
            # Verify that the service methods were called correctly
            mock_document_exists.assert_called_once_with(document_id)
            mock_get_results.assert_called_once_with(document_id, True)


def test_get_ocr_results_exclude_low_confidence(client, mock_s3, sample_ocr_result_with_low_confidence):
    """
    Test retrieval of OCR results with low confidence fields excluded.
    
    This test verifies that the GET /ocr/{document_id} endpoint correctly filters out
    low confidence fields when include_low_confidence=False is specified.
    """
    # Setup: Store a sample OCR result with low confidence fields
    document_id = sample_ocr_result_with_low_confidence["document_id"]
    
    # Mock the OCRService.get_ocr_results method to return the sample result
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        with patch("services.OCRService.get_ocr_results", return_value=sample_ocr_result_with_low_confidence["extracted_data"]) as mock_get_results:
            # Make the request with include_low_confidence=False
            response = client.get(f"/ocr/{document_id}?include_low_confidence=false")
            
            # Verify the response
            assert response.status_code == status.HTTP_200_OK
            
            # Verify that the service methods were called correctly
            mock_document_exists.assert_called_once_with(document_id)
            mock_get_results.assert_called_once_with(document_id, False)


def test_get_ocr_results_service_error(client, mock_s3):
    """
    Test error handling when a service error occurs.
    
    This test verifies that the GET /ocr/{document_id} endpoint correctly returns
    a 500 error when a service error occurs during OCR result retrieval.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.get_ocr_results method to raise a ServiceError
        with patch("services.OCRService.get_ocr_results", side_effect=Exception("Test service error")) as mock_get_results:
            # Make the request
            response = client.get(f"/ocr/{document_id}")
            
            # Verify the response
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            
            # Verify the error message
            response_data = response.json()
            assert "detail" in response_data
            assert "An unexpected error occurred" in response_data["detail"]
            
            # Verify that the service methods were called correctly
            mock_document_exists.assert_called_once_with(document_id)
            mock_get_results.assert_called_once_with(document_id, True)


# Tests for POST /ocr/{document_id}/process endpoint

def test_process_document_success(client, mock_s3):
    """
    Test successful manual processing of a document.
    
    This test verifies that the POST /ocr/{document_id}/process endpoint correctly
    initiates OCR processing for a document and returns a processing status.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    processing_id = str(uuid.uuid4())
    
    # Request payload
    payload = {
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return False
        with patch("services.OCRService.has_ocr_results", return_value=False) as mock_has_results:
            # Mock the OCRService.process_document method to return a processing ID
            with patch("services.OCRService.process_document", return_value=processing_id) as mock_process:
                # Make the request
                response = client.post(f"/ocr/{document_id}/process", json=payload)
                
                # Verify the response
                assert response.status_code == status.HTTP_202_ACCEPTED
                
                # Verify the response data
                response_data = response.json()
                assert response_data["status"] == "processing"
                assert response_data["document_id"] == document_id
                assert response_data["processing_id"] == processing_id
                
                # Verify that the service methods were called correctly
                mock_document_exists.assert_called_once_with(document_id)
                mock_has_results.assert_called_once_with(document_id)
                mock_process.assert_called_once_with(
                    document_id,
                    model_type=payload["model_type"],
                    confidence_threshold=payload["confidence_threshold"]
                )


def test_process_document_already_processed(client, mock_s3):
    """
    Test handling of already processed documents.
    
    This test verifies that the POST /ocr/{document_id}/process endpoint correctly
    handles documents that have already been processed when force_reprocess=False.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    
    # Request payload with force_reprocess=False
    payload = {
        "force_reprocess": False,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return True
        with patch("services.OCRService.has_ocr_results", return_value=True) as mock_has_results:
            # Make the request
            response = client.post(f"/ocr/{document_id}/process", json=payload)
            
            # Verify the response
            assert response.status_code == status.HTTP_202_ACCEPTED
            
            # Verify the response data
            response_data = response.json()
            assert response_data["status"] == "already_processed"
            assert response_data["document_id"] == document_id
            assert "Use force_reprocess=true to reprocess" in response_data["message"]
            
            # Verify that the service methods were called correctly
            mock_document_exists.assert_called_once_with(document_id)
            mock_has_results.assert_called_once_with(document_id)


def test_process_document_force_reprocess(client, mock_s3):
    """
    Test forced reprocessing of a document.
    
    This test verifies that the POST /ocr/{document_id}/process endpoint correctly
    reprocesses a document when force_reprocess=True, even if it has already been processed.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    processing_id = str(uuid.uuid4())
    
    # Request payload with force_reprocess=True
    payload = {
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return True
        with patch("services.OCRService.has_ocr_results", return_value=True) as mock_has_results:
            # Mock the OCRService.process_document method to return a processing ID
            with patch("services.OCRService.process_document", return_value=processing_id) as mock_process:
                # Make the request
                response = client.post(f"/ocr/{document_id}/process", json=payload)
                
                # Verify the response
                assert response.status_code == status.HTTP_202_ACCEPTED
                
                # Verify the response data
                response_data = response.json()
                assert response_data["status"] == "processing"
                assert response_data["document_id"] == document_id
                assert response_data["processing_id"] == processing_id
                
                # Verify that the service methods were called correctly
                mock_document_exists.assert_called_once_with(document_id)
                mock_has_results.assert_called_once_with(document_id)
                mock_process.assert_called_once_with(
                    document_id,
                    model_type=payload["model_type"],
                    confidence_threshold=payload["confidence_threshold"]
                )


def test_process_document_not_found(client, mock_s3):
    """
    Test error handling when document is not found.
    
    This test verifies that the POST /ocr/{document_id}/process endpoint correctly
    returns a 404 error when the document does not exist.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    
    # Request payload
    payload = {
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return False
    with patch("services.StorageService.document_exists", return_value=False) as mock_document_exists:
        # Make the request
        response = client.post(f"/ocr/{document_id}/process", json=payload)
        
        # Verify the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify the error message
        response_data = response.json()
        assert "detail" in response_data
        assert f"Document {document_id} not found" in response_data["detail"]
        
        # Verify that the service method was called correctly
        mock_document_exists.assert_called_once_with(document_id)


def test_process_document_processing_error(client, mock_s3):
    """
    Test error handling when OCR processing fails.
    
    This test verifies that the POST /ocr/{document_id}/process endpoint correctly
    returns a 500 error when OCR processing fails.
    """
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    
    # Request payload
    payload = {
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return False
        with patch("services.OCRService.has_ocr_results", return_value=False) as mock_has_results:
            # Mock the OCRService.process_document method to raise an OCRProcessingError
            with patch("services.OCRService.process_document", side_effect=Exception("Test processing error")) as mock_process:
                # Make the request
                response = client.post(f"/ocr/{document_id}/process", json=payload)
                
                # Verify the response
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
                
                # Verify the error message
                response_data = response.json()
                assert "detail" in response_data
                assert "An unexpected error occurred" in response_data["detail"]
                
                # Verify that the service methods were called correctly
                mock_document_exists.assert_called_once_with(document_id)
                mock_has_results.assert_called_once_with(document_id)
                mock_process.assert_called_once_with(
                    document_id,
                    model_type=payload["model_type"],
                    confidence_threshold=payload["confidence_threshold"]
                )


# Tests for POST /ocr/batch endpoint

def test_batch_process_success(client, mock_s3):
    """
    Test successful batch processing of documents.
    
    This test verifies that the POST /ocr/batch endpoint correctly initiates
    OCR processing for multiple documents and returns a batch processing status.
    """
    # Generate random document IDs
    document_ids = [str(uuid.uuid4()) for _ in range(3)]
    
    # Request payload
    payload = {
        "document_ids": document_ids,
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True for all documents
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return False for all documents
        with patch("services.OCRService.has_ocr_results", return_value=False) as mock_has_results:
            # Mock the OCRService.process_document method to return a processing ID
            with patch("services.OCRService.process_document", return_value=str(uuid.uuid4())) as mock_process:
                # Make the request
                response = client.post("/ocr/batch", json=payload)
                
                # Verify the response
                assert response.status_code == status.HTTP_202_ACCEPTED
                
                # Verify the response data
                response_data = response.json()
                assert response_data["total"] == len(document_ids)
                assert response_data["success_count"] == len(document_ids)
                assert response_data["failure_count"] == 0
                assert len(response_data["processed"]) == len(document_ids)
                assert len(response_data["failed"]) == 0
                
                # Verify that the service methods were called correctly
                assert mock_document_exists.call_count == len(document_ids)
                assert mock_has_results.call_count == len(document_ids)
                assert mock_process.call_count == len(document_ids)


def test_batch_process_mixed_results(client, mock_s3):
    """
    Test batch processing with mixed results (some success, some failure).
    
    This test verifies that the POST /ocr/batch endpoint correctly handles a mix of
    successful and failed document processing in a batch operation.
    """
    # Generate random document IDs
    document_ids = [str(uuid.uuid4()) for _ in range(3)]
    
    # Request payload
    payload = {
        "document_ids": document_ids,
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True for first document, False for others
    def mock_document_exists_side_effect(doc_id):
        return doc_id == document_ids[0]
    
    with patch("services.StorageService.document_exists", side_effect=mock_document_exists_side_effect) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return False
        with patch("services.OCRService.has_ocr_results", return_value=False) as mock_has_results:
            # Mock the OCRService.process_document method to return a processing ID
            with patch("services.OCRService.process_document", return_value=str(uuid.uuid4())) as mock_process:
                # Make the request
                response = client.post("/ocr/batch", json=payload)
                
                # Verify the response
                assert response.status_code == status.HTTP_202_ACCEPTED
                
                # Verify the response data
                response_data = response.json()
                assert response_data["total"] == len(document_ids)
                assert response_data["success_count"] == 1
                assert response_data["failure_count"] == 2
                assert len(response_data["processed"]) == 1
                assert len(response_data["failed"]) == 2
                assert document_ids[0] in response_data["processed"]
                assert document_ids[1] in response_data["failed"]
                assert document_ids[2] in response_data["failed"]
                assert response_data["failed"][document_ids[1]] == "Document not found"
                assert response_data["failed"][document_ids[2]] == "Document not found"
                
                # Verify that the service methods were called correctly
                assert mock_document_exists.call_count == len(document_ids)
                assert mock_has_results.call_count == 1  # Only called for the first document
                assert mock_process.call_count == 1  # Only called for the first document


def test_batch_process_already_processed(client, mock_s3):
    """
    Test batch processing with already processed documents.
    
    This test verifies that the POST /ocr/batch endpoint correctly handles documents
    that have already been processed when force_reprocess=False.
    """
    # Generate random document IDs
    document_ids = [str(uuid.uuid4()) for _ in range(3)]
    
    # Request payload with force_reprocess=False
    payload = {
        "document_ids": document_ids,
        "force_reprocess": False,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Mock the StorageService.document_exists method to return True for all documents
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.has_ocr_results method to return True for all documents
        with patch("services.OCRService.has_ocr_results", return_value=True) as mock_has_results:
            # Make the request
            response = client.post("/ocr/batch", json=payload)
            
            # Verify the response
            assert response.status_code == status.HTTP_202_ACCEPTED
            
            # Verify the response data
            response_data = response.json()
            assert response_data["total"] == len(document_ids)
            assert response_data["success_count"] == 0
            assert response_data["failure_count"] == len(document_ids)
            assert len(response_data["processed"]) == 0
            assert len(response_data["failed"]) == len(document_ids)
            for doc_id in document_ids:
                assert doc_id in response_data["failed"]
                assert "Already processed" in response_data["failed"][doc_id]
            
            # Verify that the service methods were called correctly
            assert mock_document_exists.call_count == len(document_ids)
            assert mock_has_results.call_count == len(document_ids)


def test_batch_process_empty_list(client, mock_s3):
    """
    Test batch processing with an empty document list.
    
    This test verifies that the POST /ocr/batch endpoint correctly handles an empty
    list of document IDs.
    """
    # Request payload with empty document_ids list
    payload = {
        "document_ids": [],
        "force_reprocess": True,
        "model_type": "TYPED",
        "confidence_threshold": 0.8
    }
    
    # Make the request
    response = client.post("/ocr/batch", json=payload)
    
    # Verify the response
    assert response.status_code == status.HTTP_202_ACCEPTED
    
    # Verify the response data
    response_data = response.json()
    assert response_data["total"] == 0
    assert response_data["success_count"] == 0
    assert response_data["failure_count"] == 0
    assert len(response_data["processed"]) == 0
    assert len(response_data["failed"]) == 0


# Tests for GET /ocr/confidence/thresholds endpoint

def test_get_confidence_thresholds(client):
    """
    Test retrieval of confidence thresholds.
    
    This test verifies that the GET /ocr/confidence/thresholds endpoint correctly
    returns the current confidence thresholds used for OCR extraction.
    """
    # Sample thresholds to return from the mock
    sample_thresholds = {
        "global_threshold": 0.75,
        "document_type_thresholds": {
            "APPLICATION": 0.8,
            "TAX_RETURN": 0.7,
            "BANK_STATEMENT": 0.75
        },
        "field_type_thresholds": {
            "business_name": 0.9,
            "tax_id": 0.95,
            "signature": 0.6
        }
    }
    
    # Mock the ConfidenceService.get_thresholds method to return the sample thresholds
    with patch("services.ConfidenceService.get_thresholds") as mock_get_thresholds:
        # Configure the mock to return an object with the sample thresholds as attributes
        mock_thresholds = MagicMock()
        mock_thresholds.global_threshold = sample_thresholds["global_threshold"]
        mock_thresholds.document_type_thresholds = sample_thresholds["document_type_thresholds"]
        mock_thresholds.field_type_thresholds = sample_thresholds["field_type_thresholds"]
        mock_get_thresholds.return_value = mock_thresholds
        
        # Make the request
        response = client.get("/ocr/confidence/thresholds")
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the response data
        response_data = response.json()
        assert response_data["global_threshold"] == sample_thresholds["global_threshold"]
        assert response_data["document_type_thresholds"] == sample_thresholds["document_type_thresholds"]
        assert response_data["field_type_thresholds"] == sample_thresholds["field_type_thresholds"]
        
        # Verify that the service method was called correctly
        mock_get_thresholds.assert_called_once()


def test_get_confidence_thresholds_service_error(client):
    """
    Test error handling when a service error occurs during threshold retrieval.
    
    This test verifies that the GET /ocr/confidence/thresholds endpoint correctly
    returns a 500 error when a service error occurs during threshold retrieval.
    """
    # Mock the ConfidenceService.get_thresholds method to raise an exception
    with patch("services.ConfidenceService.get_thresholds", side_effect=Exception("Test service error")) as mock_get_thresholds:
        # Make the request
        response = client.get("/ocr/confidence/thresholds")
        
        # Verify the response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verify the error message
        response_data = response.json()
        assert "detail" in response_data
        assert "An unexpected error occurred" in response_data["detail"]
        
        # Verify that the service method was called correctly
        mock_get_thresholds.assert_called_once()


# Tests for PUT /ocr/confidence/thresholds endpoint

def test_update_confidence_thresholds(client):
    """
    Test updating confidence thresholds.
    
    This test verifies that the PUT /ocr/confidence/thresholds endpoint correctly
    updates the confidence thresholds used for OCR extraction.
    """
    # Request payload with threshold updates
    payload = {
        "global_threshold": 0.8,
        "document_type_thresholds": {
            "APPLICATION": 0.85,
            "TAX_RETURN": 0.75
        },
        "field_type_thresholds": {
            "business_name": 0.95,
            "signature": 0.7
        }
    }
    
    # Mock the ConfidenceService.update_thresholds method
    with patch("services.ConfidenceService.update_thresholds") as mock_update_thresholds:
        # Configure the mock to return an object with the updated thresholds as attributes
        mock_thresholds = MagicMock()
        mock_thresholds.global_threshold = payload["global_threshold"]
        mock_thresholds.document_type_thresholds = payload["document_type_thresholds"]
        mock_thresholds.field_type_thresholds = payload["field_type_thresholds"]
        mock_update_thresholds.return_value = mock_thresholds
        
        # Make the request
        response = client.put("/ocr/confidence/thresholds", json=payload)
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the response data
        response_data = response.json()
        assert response_data["global_threshold"] == payload["global_threshold"]
        assert response_data["document_type_thresholds"] == payload["document_type_thresholds"]
        assert response_data["field_type_thresholds"] == payload["field_type_thresholds"]
        
        # Verify that the service method was called correctly
        mock_update_thresholds.assert_called_once_with(
            global_threshold=payload["global_threshold"],
            document_type_thresholds=payload["document_type_thresholds"],
            field_type_thresholds=payload["field_type_thresholds"]
        )


def test_update_confidence_thresholds_partial(client):
    """
    Test partial update of confidence thresholds.
    
    This test verifies that the PUT /ocr/confidence/thresholds endpoint correctly
    handles partial updates of confidence thresholds.
    """
    # Request payload with only global_threshold
    payload = {
        "global_threshold": 0.8
    }
    
    # Mock the ConfidenceService.update_thresholds method
    with patch("services.ConfidenceService.update_thresholds") as mock_update_thresholds:
        # Configure the mock to return an object with the updated thresholds as attributes
        mock_thresholds = MagicMock()
        mock_thresholds.global_threshold = payload["global_threshold"]
        mock_thresholds.document_type_thresholds = {"APPLICATION": 0.85}
        mock_thresholds.field_type_thresholds = {"business_name": 0.95}
        mock_update_thresholds.return_value = mock_thresholds
        
        # Make the request
        response = client.put("/ocr/confidence/thresholds", json=payload)
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the response data
        response_data = response.json()
        assert response_data["global_threshold"] == payload["global_threshold"]
        assert "document_type_thresholds" in response_data
        assert "field_type_thresholds" in response_data
        
        # Verify that the service method was called correctly
        mock_update_thresholds.assert_called_once_with(
            global_threshold=payload["global_threshold"],
            document_type_thresholds=None,
            field_type_thresholds=None
        )


def test_update_confidence_thresholds_invalid_value(client):
    """
    Test validation of threshold values.
    
    This test verifies that the PUT /ocr/confidence/thresholds endpoint correctly
    validates threshold values and returns a 400 error for invalid values.
    """
    # Request payload with invalid global_threshold (outside 0.0-1.0 range)
    payload = {
        "global_threshold": 1.5
    }
    
    # Make the request
    response = client.put("/ocr/confidence/thresholds", json=payload)
    
    # Verify the response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Verify the error message
    response_data = response.json()
    assert "detail" in response_data
    assert "Global threshold must be between 0.0 and 1.0" in response_data["detail"]


def test_update_confidence_thresholds_invalid_document_type(client):
    """
    Test validation of document type thresholds.
    
    This test verifies that the PUT /ocr/confidence/thresholds endpoint correctly
    validates document type threshold values and returns a 400 error for invalid values.
    """
    # Request payload with invalid document type threshold
    payload = {
        "document_type_thresholds": {
            "APPLICATION": 1.2
        }
    }
    
    # Make the request
    response = client.put("/ocr/confidence/thresholds", json=payload)
    
    # Verify the response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Verify the error message
    response_data = response.json()
    assert "detail" in response_data
    assert "Threshold for document type APPLICATION must be between 0.0 and 1.0" in response_data["detail"]


def test_update_confidence_thresholds_invalid_field_type(client):
    """
    Test validation of field type thresholds.
    
    This test verifies that the PUT /ocr/confidence/thresholds endpoint correctly
    validates field type threshold values and returns a 400 error for invalid values.
    """
    # Request payload with invalid field type threshold
    payload = {
        "field_type_thresholds": {
            "business_name": -0.1
        }
    }
    
    # Make the request
    response = client.put("/ocr/confidence/thresholds", json=payload)
    
    # Verify the response
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Verify the error message
    response_data = response.json()
    assert "detail" in response_data
    assert "Threshold for field type business_name must be between 0.0 and 1.0" in response_data["detail"]


# Tests for GET /ocr/status/{processing_id} endpoint

def test_get_processing_status_success(client):
    """
    Test retrieval of OCR processing status.
    
    This test verifies that the GET /ocr/status/{processing_id} endpoint correctly
    returns the status of an OCR processing job.
    """
    # Generate a random processing ID
    processing_id = str(uuid.uuid4())
    
    # Sample status information to return from the mock
    status_info = {
        "processing_id": processing_id,
        "document_id": str(uuid.uuid4()),
        "status": "COMPLETED",
        "start_time": "2023-01-01T12:00:00Z",
        "end_time": "2023-01-01T12:01:30Z",
        "processing_time": 90.5,
        "model_type": "TYPED",
        "confidence_threshold": 0.75,
        "result_available": True
    }
    
    # Mock the OCRService.get_processing_status method to return the sample status
    with patch("services.OCRService.get_processing_status", return_value=status_info) as mock_get_status:
        # Make the request
        response = client.get(f"/ocr/status/{processing_id}")
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Verify the response data
        response_data = response.json()
        assert response_data == status_info
        
        # Verify that the service method was called correctly
        mock_get_status.assert_called_once_with(processing_id)


def test_get_processing_status_not_found(client):
    """
    Test error handling when processing job is not found.
    
    This test verifies that the GET /ocr/status/{processing_id} endpoint correctly
    returns a 404 error when the processing job does not exist.
    """
    # Generate a random processing ID
    processing_id = str(uuid.uuid4())
    
    # Mock the OCRService.get_processing_status method to return None
    with patch("services.OCRService.get_processing_status", return_value=None) as mock_get_status:
        # Make the request
        response = client.get(f"/ocr/status/{processing_id}")
        
        # Verify the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify the error message
        response_data = response.json()
        assert "detail" in response_data
        assert f"Processing job {processing_id} not found" in response_data["detail"]
        
        # Verify that the service method was called correctly
        mock_get_status.assert_called_once_with(processing_id)


def test_get_processing_status_service_error(client):
    """
    Test error handling when a service error occurs during status retrieval.
    
    This test verifies that the GET /ocr/status/{processing_id} endpoint correctly
    returns a 500 error when a service error occurs during status retrieval.
    """
    # Generate a random processing ID
    processing_id = str(uuid.uuid4())
    
    # Mock the OCRService.get_processing_status method to raise an exception
    with patch("services.OCRService.get_processing_status", side_effect=Exception("Test service error")) as mock_get_status:
        # Make the request
        response = client.get(f"/ocr/status/{processing_id}")
        
        # Verify the response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verify the error message
        response_data = response.json()
        assert "detail" in response_data
        assert "An unexpected error occurred" in response_data["detail"]
        
        # Verify that the service method was called correctly
        mock_get_status.assert_called_once_with(processing_id)


# Test logging of OCR operations

def test_logging_of_ocr_operations(client, mock_s3, caplog):
    """
    Test that OCR operations are properly logged.
    
    This test verifies that OCR operations are properly logged with the correct
    log level and message format.
    """
    # Set up logging capture
    caplog.set_level(logging.INFO)
    
    # Generate a random document ID
    document_id = str(uuid.uuid4())
    
    # Mock the StorageService.document_exists method to return True
    with patch("services.StorageService.document_exists", return_value=True) as mock_document_exists:
        # Mock the OCRService.get_ocr_results method to return None
        with patch("services.OCRService.get_ocr_results", return_value=None) as mock_get_results:
            # Make the request
            response = client.get(f"/ocr/{document_id}")
            
            # Verify that appropriate log messages were generated
            assert any(f"Retrieving OCR results for document {document_id}" in record.message for record in caplog.records)
            assert any(f"OCR results not found for document {document_id}" in record.message for record in caplog.records)
            
            # Verify log levels
            info_logs = [record for record in caplog.records if record.levelname == "INFO"]
            warning_logs = [record for record in caplog.records if record.levelname == "WARNING"]
            assert len(info_logs) > 0
            assert len(warning_logs) > 0