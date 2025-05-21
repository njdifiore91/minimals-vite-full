import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
import json
import logging
from uuid import uuid4
import sys
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.api.ocr import router as ocr_router
from src.types.documents import DocumentType, ProcessingStatus
from src.types.extraction import ExtractedData, ConfidenceScore
from src.types.errors import ServiceError, ErrorCategory


# Mock services
@pytest.fixture
def mock_ocr_service():
    """Mock OCR service for testing"""
    mock = MagicMock()
    mock.process_document = AsyncMock()
    return mock


@pytest.fixture
def mock_confidence_service():
    """Mock confidence service for testing"""
    mock = MagicMock()
    mock.filter_by_confidence = MagicMock()
    mock.get_confidence_thresholds = MagicMock(return_value={
        DocumentType.APPLICATION.value: 0.8,
        DocumentType.TAX_RETURN.value: 0.85,
        DocumentType.BANK_STATEMENT.value: 0.9,
        DocumentType.PAY_STUB.value: 0.85,
        DocumentType.ID_DOCUMENT.value: 0.95,
        DocumentType.OTHER.value: 0.75
    })
    mock.set_confidence_threshold = MagicMock()
    return mock


@pytest.fixture
def mock_field_extraction_service():
    """Mock field extraction service for testing"""
    mock = MagicMock()
    return mock


@pytest.fixture
def mock_storage_service():
    """Mock storage service for testing"""
    mock = MagicMock()
    mock.get_document_metadata = AsyncMock()
    mock.get_ocr_results = AsyncMock()
    mock.update_document_metadata = AsyncMock()
    return mock


@pytest.fixture
def app(mock_ocr_service, mock_confidence_service, mock_field_extraction_service, mock_storage_service):
    """Create a FastAPI app with mocked dependencies for testing"""
    app = FastAPI()
    app.include_router(ocr_router)
    
    # Override dependencies
    app.dependency_overrides[ocr_router.get_ocr_service] = lambda: mock_ocr_service
    app.dependency_overrides[ocr_router.get_confidence_service] = lambda: mock_confidence_service
    app.dependency_overrides[ocr_router.get_field_extraction_service] = lambda: mock_field_extraction_service
    app.dependency_overrides[ocr_router.get_storage_service] = lambda: mock_storage_service
    
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def sample_document_id():
    """Generate a sample document ID for testing"""
    return str(uuid4())


@pytest.fixture
def sample_ocr_results():
    """Generate sample OCR results for testing"""
    return {
        "document_id": str(uuid4()),
        "document_type": DocumentType.APPLICATION.value,
        "extracted_fields": {
            "name": {
                "value": "John Doe",
                "confidence": 0.95
            },
            "business_name": {
                "value": "Acme Corporation",
                "confidence": 0.92
            },
            "address": {
                "value": "123 Main St, Anytown, USA",
                "confidence": 0.88
            },
            "phone": {
                "value": "555-123-4567",
                "confidence": 0.85
            },
            "email": {
                "value": "john.doe@example.com",
                "confidence": 0.93
            },
            "tax_id": {
                "value": "12-3456789",
                "confidence": 0.91
            },
            "requested_amount": {
                "value": "50000",
                "confidence": 0.89
            },
            "business_start_date": {
                "value": "2015-06-15",
                "confidence": 0.82
            }
        },
        "metadata": {
            "processing_time": 2.34,
            "page_count": 3,
            "model_version": "v2.1.0",
            "processed_at": "2025-05-21T14:30:45Z"
        },
        "raw_text": "Sample raw text from the document..."
    }


@pytest.fixture
def sample_document_metadata():
    """Generate sample document metadata for testing"""
    return {
        "document_id": str(uuid4()),
        "filename": "application_form.pdf",
        "file_size": 1024567,
        "mime_type": "application/pdf",
        "document_type": DocumentType.APPLICATION.value,
        "processing_status": ProcessingStatus.COMPLETED.value,
        "created_at": "2025-05-21T14:25:30Z",
        "updated_at": "2025-05-21T14:30:45Z",
        "processing_metrics": {
            "processing_time": 2.34,
            "confidence_avg": 0.89,
            "page_count": 3
        }
    }


# Test cases for GET /ocr/{document_id}
class TestGetOcrResults:
    
    def test_get_ocr_results_success(self, client, mock_storage_service, sample_document_id, sample_ocr_results, sample_document_metadata):
        """Test successful retrieval of OCR results"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_ocr_results["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        mock_storage_service.get_ocr_results.return_value = sample_ocr_results
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["document_id"] == sample_document_id
        assert "extracted_fields" in response.json()
        assert "metadata" in response.json()
        assert "raw_text" not in response.json()  # raw_text should not be included by default
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(sample_document_id)
        mock_storage_service.get_ocr_results.assert_called_once_with(sample_document_id)
    
    def test_get_ocr_results_with_raw_text(self, client, mock_storage_service, sample_document_id, sample_ocr_results, sample_document_metadata):
        """Test retrieval of OCR results with raw text included"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_ocr_results["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        mock_storage_service.get_ocr_results.return_value = sample_ocr_results
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}?include_raw_text=true")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "raw_text" in response.json()
        assert response.json()["raw_text"] == sample_ocr_results["raw_text"]
    
    def test_get_ocr_results_with_confidence_threshold(self, client, mock_storage_service, mock_confidence_service, sample_document_id, sample_ocr_results, sample_document_metadata):
        """Test retrieval of OCR results with confidence threshold filtering"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_ocr_results["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        mock_storage_service.get_ocr_results.return_value = sample_ocr_results
        
        # Setup filtered results (only fields with confidence >= 0.9)
        filtered_results = sample_ocr_results.copy()
        filtered_results["extracted_fields"] = {
            k: v for k, v in sample_ocr_results["extracted_fields"].items() 
            if v["confidence"] >= 0.9
        }
        mock_confidence_service.filter_by_confidence.return_value = filtered_results
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}?confidence_threshold=0.9")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "extracted_fields" in response.json()
        
        # Verify confidence service was called with correct parameters
        mock_confidence_service.filter_by_confidence.assert_called_once_with(sample_ocr_results, 0.9)
    
    def test_get_ocr_results_document_not_found(self, client, mock_storage_service, sample_document_id):
        """Test error handling when document is not found"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = None
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_ocr_results_document_not_processed(self, client, mock_storage_service, sample_document_id):
        """Test error handling when document has not been processed yet"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": sample_document_id,
            "processing_status": ProcessingStatus.PENDING.value
        }
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not been processed yet" in response.json()["detail"].lower()
    
    def test_get_ocr_results_missing_results(self, client, mock_storage_service, sample_document_id, sample_document_metadata):
        """Test error handling when OCR results are missing despite completed status"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        mock_storage_service.get_ocr_results.return_value = None
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_ocr_results_service_error(self, client, mock_storage_service, sample_document_id):
        """Test error handling when a service error occurs"""
        # Setup mocks
        mock_storage_service.get_document_metadata.side_effect = ServiceError(
            "Database connection error", ErrorCategory.DATABASE
        )
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "database connection error" in response.json()["detail"].lower()


# Test cases for POST /ocr/{document_id}/process
class TestProcessDocument:
    
    def test_process_document_success(self, client, mock_storage_service, mock_ocr_service, sample_document_id, sample_document_metadata):
        """Test successful document processing request"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_document_metadata["processing_status"] = ProcessingStatus.PENDING.value
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        
        # Make request
        response = client.post(f"/ocr/{sample_document_id}/process")
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "queued for processing" in response.json()["message"].lower()
        assert response.json()["status"] == ProcessingStatus.PROCESSING.value
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(sample_document_id)
        mock_storage_service.update_document_metadata.assert_called_once_with(
            sample_document_id, {"processing_status": ProcessingStatus.PROCESSING.value}
        )
        mock_ocr_service.process_document.assert_called_once_with(sample_document_id, None)
    
    def test_process_document_with_document_type(self, client, mock_storage_service, mock_ocr_service, sample_document_id, sample_document_metadata):
        """Test document processing with specified document type"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_document_metadata["processing_status"] = ProcessingStatus.PENDING.value
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        
        # Make request
        response = client.post(
            f"/ocr/{sample_document_id}/process?document_type={DocumentType.TAX_RETURN.value}"
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        # Verify service calls with correct document type
        mock_ocr_service.process_document.assert_called_once_with(
            sample_document_id, DocumentType.TAX_RETURN.value
        )
    
    def test_process_document_already_processing(self, client, mock_storage_service, sample_document_id):
        """Test handling of document that is already being processed"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": sample_document_id,
            "processing_status": ProcessingStatus.PROCESSING.value
        }
        
        # Make request
        response = client.post(f"/ocr/{sample_document_id}/process")
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "already being processed" in response.json()["message"].lower()
        
        # Verify service calls
        mock_storage_service.update_document_metadata.assert_not_called()
        
    def test_process_document_already_completed(self, client, mock_storage_service, sample_document_id):
        """Test handling of document that has already been processed"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": sample_document_id,
            "processing_status": ProcessingStatus.COMPLETED.value
        }
        
        # Make request
        response = client.post(f"/ocr/{sample_document_id}/process")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "already been processed" in response.json()["message"].lower()
        assert "force_reprocess=true" in response.json()["message"].lower()
        
        # Verify service calls
        mock_storage_service.update_document_metadata.assert_not_called()
    
    def test_process_document_force_reprocess(self, client, mock_storage_service, mock_ocr_service, sample_document_id):
        """Test forcing reprocessing of a completed document"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": sample_document_id,
            "processing_status": ProcessingStatus.COMPLETED.value
        }
        
        # Make request
        response = client.post(f"/ocr/{sample_document_id}/process?force_reprocess=true")
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "queued for processing" in response.json()["message"].lower()
        
        # Verify service calls
        mock_storage_service.update_document_metadata.assert_called_once_with(
            sample_document_id, {"processing_status": ProcessingStatus.PROCESSING.value}
        )
        mock_ocr_service.process_document.assert_called_once()
    
    def test_process_document_not_found(self, client, mock_storage_service, sample_document_id):
        """Test error handling when document is not found"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = None
        
        # Make request
        response = client.post(f"/ocr/{sample_document_id}/process")
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()


# Test cases for POST /ocr/batch
class TestBatchProcessing:
    
    def test_batch_processing_success(self, client, mock_storage_service, mock_ocr_service):
        """Test successful batch processing request"""
        # Generate document IDs
        document_ids = [str(uuid4()) for _ in range(3)]
        
        # Setup mocks
        mock_storage_service.get_document_metadata.side_effect = [
            {"document_id": doc_id, "processing_status": ProcessingStatus.PENDING.value}
            for doc_id in document_ids
        ]
        
        # Make request
        response = client.post(
            "/ocr/batch",
            json={"document_ids": document_ids}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["processed"] == 3
        assert response.json()["skipped"] == 0
        assert response.json()["not_found"] == 0
        assert len(response.json()["results"]) == 3
        
        # Verify service calls
        assert mock_storage_service.update_document_metadata.call_count == 3
        assert mock_ocr_service.process_document.call_count == 3
    
    def test_batch_processing_mixed_statuses(self, client, mock_storage_service, mock_ocr_service):
        """Test batch processing with documents in different states"""
        # Generate document IDs
        document_ids = [str(uuid4()) for _ in range(3)]
        
        # Setup mocks to return different statuses
        mock_storage_service.get_document_metadata.side_effect = [
            {"document_id": document_ids[0], "processing_status": ProcessingStatus.PENDING.value},
            {"document_id": document_ids[1], "processing_status": ProcessingStatus.COMPLETED.value},
            None  # Document not found
        ]
        
        # Make request
        response = client.post(
            "/ocr/batch",
            json={"document_ids": document_ids}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["processed"] == 1
        assert response.json()["skipped"] == 1
        assert response.json()["not_found"] == 1
        
        # Verify service calls
        assert mock_storage_service.update_document_metadata.call_count == 1
        assert mock_ocr_service.process_document.call_count == 1
    
    def test_batch_processing_force_reprocess(self, client, mock_storage_service, mock_ocr_service):
        """Test batch processing with force_reprocess flag"""
        # Generate document IDs
        document_ids = [str(uuid4()) for _ in range(2)]
        
        # Setup mocks
        mock_storage_service.get_document_metadata.side_effect = [
            {"document_id": document_ids[0], "processing_status": ProcessingStatus.COMPLETED.value},
            {"document_id": document_ids[1], "processing_status": ProcessingStatus.COMPLETED.value}
        ]
        
        # Make request
        response = client.post(
            "/ocr/batch?force_reprocess=true",
            json={"document_ids": document_ids}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["processed"] == 2
        assert response.json()["skipped"] == 0
        
        # Verify service calls
        assert mock_storage_service.update_document_metadata.call_count == 2
        assert mock_ocr_service.process_document.call_count == 2
    
    def test_batch_processing_empty_list(self, client):
        """Test error handling for empty document list"""
        # Make request
        response = client.post(
            "/ocr/batch",
            json={"document_ids": []}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no document ids provided" in response.json()["detail"].lower()
    
    def test_batch_processing_too_many_documents(self, client):
        """Test error handling for too many documents"""
        # Generate 101 document IDs (exceeding the 100 limit)
        document_ids = [str(uuid4()) for _ in range(101)]
        
        # Make request
        response = client.post(
            "/ocr/batch",
            json={"document_ids": document_ids}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "batch size exceeds maximum limit" in response.json()["detail"].lower()


# Test cases for confidence threshold management
class TestConfidenceThresholds:
    
    def test_get_confidence_thresholds(self, client, mock_confidence_service):
        """Test retrieving confidence thresholds"""
        # Make request
        response = client.get("/ocr/confidence/threshold")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert DocumentType.APPLICATION.value in response.json()
        assert DocumentType.TAX_RETURN.value in response.json()
        assert DocumentType.BANK_STATEMENT.value in response.json()
        assert DocumentType.PAY_STUB.value in response.json()
        assert DocumentType.ID_DOCUMENT.value in response.json()
        assert DocumentType.OTHER.value in response.json()
        
        # Verify service calls
        mock_confidence_service.get_confidence_thresholds.assert_called_once()
    
    def test_update_confidence_threshold(self, client, mock_confidence_service):
        """Test updating confidence threshold for a document type"""
        # Make request
        response = client.put(
            f"/ocr/confidence/threshold/{DocumentType.APPLICATION.value}",
            json={"threshold": 0.85}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["document_type"] == DocumentType.APPLICATION.value
        assert response.json()["threshold"] == 0.85
        assert "updated" in response.json()["message"].lower()
        
        # Verify service calls
        mock_confidence_service.set_confidence_threshold.assert_called_once_with(
            DocumentType.APPLICATION, 0.85
        )
    
    def test_update_confidence_threshold_invalid_value(self, client):
        """Test error handling for invalid confidence threshold value"""
        # Make request with value > 1.0
        response = client.put(
            f"/ocr/confidence/threshold/{DocumentType.APPLICATION.value}",
            json={"threshold": 1.5}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Make request with value < 0.0
        response = client.put(
            f"/ocr/confidence/threshold/{DocumentType.APPLICATION.value}",
            json={"threshold": -0.5}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# Test cases for GET /ocr/status/{document_id}
class TestDocumentStatus:
    
    def test_get_document_status(self, client, mock_storage_service, sample_document_id, sample_document_metadata):
        """Test retrieving document processing status"""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        
        # Make request
        response = client.get(f"/ocr/status/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["document_id"] == sample_document_id
        assert response.json()["status"] == ProcessingStatus.COMPLETED.value
        assert "processing_metrics" in response.json()
        
        # Verify service calls
        mock_storage_service.get_document_metadata.assert_called_once_with(sample_document_id)
    
    def test_get_document_status_not_found(self, client, mock_storage_service, sample_document_id):
        """Test error handling when document is not found"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = None
        
        # Make request
        response = client.get(f"/ocr/status/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()
    
    def test_get_document_status_with_error(self, client, mock_storage_service, sample_document_id):
        """Test retrieving status for a document with processing error"""
        # Setup mocks
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": sample_document_id,
            "processing_status": ProcessingStatus.ERROR.value,
            "error": "Failed to extract text from document",
            "updated_at": "2025-05-21T14:35:12Z"
        }
        
        # Make request
        response = client.get(f"/ocr/status/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == ProcessingStatus.ERROR.value
        assert "error" in response.json()
        assert response.json()["error"] == "Failed to extract text from document"


# Test logging functionality
class TestLogging:
    
    @patch("src.api.ocr.get_logger")
    def test_logging_for_get_ocr_results(self, mock_get_logger, client, mock_storage_service, sample_document_id, sample_document_metadata, sample_ocr_results):
        """Test that appropriate logging occurs during OCR results retrieval"""
        # Setup logger mock
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Setup service mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_ocr_results["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        mock_storage_service.get_ocr_results.return_value = sample_ocr_results
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        
        # Verify logging calls
        mock_logger.info.assert_called_with(f"Retrieving OCR results for document: {sample_document_id}")
    
    @patch("src.api.ocr.get_logger")
    def test_logging_for_document_not_found(self, mock_get_logger, client, mock_storage_service, sample_document_id):
        """Test that appropriate logging occurs when document is not found"""
        # Setup logger mock
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Setup service mocks
        mock_storage_service.get_document_metadata.return_value = None
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Verify logging calls
        mock_logger.warning.assert_called_with(f"Document not found: {sample_document_id}")
    
    @patch("src.api.ocr.get_logger")
    def test_logging_for_service_error(self, mock_get_logger, client, mock_storage_service, sample_document_id):
        """Test that appropriate logging occurs when a service error happens"""
        # Setup logger mock
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Setup service mocks
        error_message = "Database connection error"
        mock_storage_service.get_document_metadata.side_effect = ServiceError(
            error_message, ErrorCategory.DATABASE
        )
        
        # Make request
        response = client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verify logging calls
        mock_logger.error.assert_called_with(
            f"Service error retrieving OCR results: {error_message}", 
            exc_info=True
        )