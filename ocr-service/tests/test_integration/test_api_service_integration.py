import json
import os
import pytest
import uuid
from unittest.mock import MagicMock, patch
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from api import router as api_router
from services import OCRService, StorageService, FieldExtractionService, ConfidenceService
from types.documents import DocumentType, Document, DocumentMetadata
from types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from types.errors import ServiceError


@pytest.fixture
def app():
    """Create a FastAPI test application with the API router."""
    app = FastAPI()
    app.include_router(api_router)
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def mock_ocr_service():
    """Create a mock OCR service."""
    mock_service = MagicMock(spec=OCRService)
    return mock_service


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service."""
    mock_service = MagicMock(spec=StorageService)
    return mock_service


@pytest.fixture
def mock_field_extraction_service():
    """Create a mock field extraction service."""
    mock_service = MagicMock(spec=FieldExtractionService)
    return mock_service


@pytest.fixture
def mock_confidence_service():
    """Create a mock confidence service."""
    mock_service = MagicMock(spec=ConfidenceService)
    return mock_service


@pytest.fixture
def sample_document():
    """Create a sample document for testing."""
    document_id = str(uuid.uuid4())
    metadata = DocumentMetadata(
        filename="test_document.pdf",
        size=1024,
        mime_type="application/pdf",
        created_at="2025-05-01T12:00:00Z",
        document_type=DocumentType.APPLICATION
    )
    return Document(id=document_id, metadata=metadata, content=b"test content")


@pytest.fixture
def sample_extracted_data():
    """Create sample extracted data for testing."""
    fields = {
        "applicant_name": ExtractedField(
            value="John Doe",
            confidence=ConfidenceScore(0.95),
            location={"page": 1, "top": 100, "left": 100, "width": 200, "height": 30}
        ),
        "business_name": ExtractedField(
            value="Acme Corp",
            confidence=ConfidenceScore(0.92),
            location={"page": 1, "top": 150, "left": 100, "width": 200, "height": 30}
        ),
        "tax_id": ExtractedField(
            value="123-45-6789",
            confidence=ConfidenceScore(0.88),
            location={"page": 1, "top": 200, "left": 100, "width": 200, "height": 30}
        ),
        "address": ExtractedField(
            value="123 Main St, Anytown, USA",
            confidence=ConfidenceScore(0.85),
            location={"page": 1, "top": 250, "left": 100, "width": 300, "height": 30}
        ),
    }
    return ExtractedData(
        document_id=str(uuid.uuid4()),
        fields=fields,
        metadata={
            "processing_time": 1.25,
            "model_version": "v2.3.0",
            "document_type": "APPLICATION"
        }
    )


@pytest.fixture
def auth_headers():
    """Create authentication headers for testing."""
    return {"Authorization": "Bearer test_token"}


# Test OCR API endpoints integration with services
class TestOCRAPIServiceIntegration:
    
    @patch("api.ocr.get_ocr_service")
    def test_get_ocr_results(self, mock_get_ocr_service, client, mock_ocr_service, sample_extracted_data, auth_headers):
        """Test that the GET /ocr/{document_id} endpoint correctly invokes the OCR service."""
        # Arrange
        document_id = "test-doc-123"
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_ocr_results.return_value = sample_extracted_data
        
        # Act
        response = client.get(f"/ocr/{document_id}", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "fields" in response.json()
        assert "applicant_name" in response.json()["fields"]
        mock_ocr_service.get_ocr_results.assert_called_once_with(document_id)
    
    @patch("api.ocr.get_ocr_service")
    def test_get_ocr_results_not_found(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the GET /ocr/{document_id} endpoint correctly handles not found errors."""
        # Arrange
        document_id = "nonexistent-doc"
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_ocr_results.side_effect = ServiceError(
            "Document not found", status_code=status.HTTP_404_NOT_FOUND
        )
        
        # Act
        response = client.get(f"/ocr/{document_id}", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.json()
        mock_ocr_service.get_ocr_results.assert_called_once_with(document_id)
    
    @patch("api.ocr.get_ocr_service")
    def test_process_document(self, mock_get_ocr_service, client, mock_ocr_service, sample_extracted_data, auth_headers):
        """Test that the POST /ocr/{document_id}/process endpoint correctly invokes the OCR service."""
        # Arrange
        document_id = "test-doc-123"
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.process_document.return_value = sample_extracted_data
        
        # Act
        response = client.post(
            f"/ocr/{document_id}/process", 
            headers=auth_headers,
            json={"force_reprocess": True, "priority": "high"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "fields" in response.json()
        assert "processing_id" in response.json()
        mock_ocr_service.process_document.assert_called_once_with(
            document_id, force_reprocess=True, priority="high"
        )
    
    @patch("api.ocr.get_ocr_service")
    def test_process_document_validation_error(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the POST /ocr/{document_id}/process endpoint correctly handles validation errors."""
        # Arrange
        document_id = "test-doc-123"
        mock_get_ocr_service.return_value = mock_ocr_service
        
        # Act - Send invalid priority value
        response = client.post(
            f"/ocr/{document_id}/process", 
            headers=auth_headers,
            json={"force_reprocess": True, "priority": "invalid_priority"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "detail" in response.json()
        # Ensure service was not called with invalid parameters
        mock_ocr_service.process_document.assert_not_called()
    
    @patch("api.ocr.get_ocr_service")
    def test_batch_process(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the POST /ocr/batch endpoint correctly invokes the OCR service."""
        # Arrange
        document_ids = ["doc-1", "doc-2", "doc-3"]
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.batch_process.return_value = {
            "batch_id": "batch-123",
            "submitted": 3,
            "status": "processing"
        }
        
        # Act
        response = client.post(
            "/ocr/batch", 
            headers=auth_headers,
            json={"document_ids": document_ids, "priority": "normal"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "batch_id" in response.json()
        assert response.json()["submitted"] == 3
        mock_ocr_service.batch_process.assert_called_once_with(
            document_ids, priority="normal"
        )
    
    @patch("api.ocr.get_ocr_service")
    @patch("api.ocr.get_confidence_service")
    def test_update_confidence_threshold(self, mock_get_confidence_service, mock_get_ocr_service, 
                                        client, mock_ocr_service, mock_confidence_service, auth_headers):
        """Test that the PUT /ocr/confidence-threshold endpoint correctly invokes the confidence service."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_get_confidence_service.return_value = mock_confidence_service
        mock_confidence_service.update_confidence_threshold.return_value = {
            "threshold": 0.75,
            "updated_at": "2025-05-01T12:00:00Z"
        }
        
        # Act
        response = client.put(
            "/ocr/confidence-threshold", 
            headers=auth_headers,
            json={"threshold": 0.75}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["threshold"] == 0.75
        mock_confidence_service.update_confidence_threshold.assert_called_once_with(0.75)


# Test Health API endpoints integration with services
class TestHealthAPIServiceIntegration:
    
    @patch("api.health.get_ocr_service")
    @patch("api.health.get_storage_service")
    def test_readiness_probe(self, mock_get_storage_service, mock_get_ocr_service, 
                            client, mock_ocr_service, mock_storage_service):
        """Test that the GET /health/readiness endpoint correctly checks service dependencies."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_get_storage_service.return_value = mock_storage_service
        mock_ocr_service.check_health.return_value = True
        mock_storage_service.check_health.return_value = True
        
        # Act
        response = client.get("/health/readiness")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ready"
        mock_ocr_service.check_health.assert_called_once()
        mock_storage_service.check_health.assert_called_once()
    
    @patch("api.health.get_ocr_service")
    @patch("api.health.get_storage_service")
    def test_readiness_probe_not_ready(self, mock_get_storage_service, mock_get_ocr_service, 
                                     client, mock_ocr_service, mock_storage_service):
        """Test that the GET /health/readiness endpoint correctly reports when services are not ready."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_get_storage_service.return_value = mock_storage_service
        mock_ocr_service.check_health.return_value = True
        mock_storage_service.check_health.return_value = False  # Storage service not ready
        
        # Act
        response = client.get("/health/readiness")
        
        # Assert
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["status"] == "not ready"
        assert "details" in response.json()
        assert "storage" in response.json()["details"]
        mock_ocr_service.check_health.assert_called_once()
        mock_storage_service.check_health.assert_called_once()
    
    def test_liveness_probe(self, client):
        """Test that the GET /health/liveness endpoint correctly reports service liveness."""
        # Act
        response = client.get("/health/liveness")
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "alive"


# Test Status API endpoints integration with services
class TestStatusAPIServiceIntegration:
    
    @patch("api.status.get_ocr_service")
    def test_get_service_status(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the GET /status endpoint correctly retrieves service status."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_status.return_value = {
            "status": "operational",
            "version": "1.0.0",
            "uptime": 3600,
            "processed_documents": 1250,
            "accuracy": 0.992
        }
        
        # Act
        response = client.get("/status", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "operational"
        assert "accuracy" in response.json()
        mock_ocr_service.get_status.assert_called_once()
    
    @patch("api.status.get_ocr_service")
    def test_get_metrics(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the GET /status/metrics endpoint correctly retrieves service metrics."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_metrics.return_value = {
            "processing_time": {
                "avg": 1.25,
                "p95": 2.5,
                "p99": 4.0
            },
            "accuracy": {
                "overall": 0.992,
                "by_field_type": {
                    "text": 0.995,
                    "numeric": 0.990,
                    "date": 0.985
                }
            },
            "queue_depth": 15,
            "gpu_utilization": 0.75,
            "memory_usage": 0.65
        }
        
        # Act
        response = client.get("/status/metrics", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "processing_time" in response.json()
        assert "accuracy" in response.json()
        assert "queue_depth" in response.json()
        mock_ocr_service.get_metrics.assert_called_once()


# Test Diagnostics API endpoints integration with services
class TestDiagnosticsAPIServiceIntegration:
    
    @patch("api.diagnostics.get_ocr_service")
    def test_get_logs(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the GET /diagnostics/logs endpoint correctly retrieves service logs."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_logs.return_value = {
            "logs": [
                {"timestamp": "2025-05-01T12:00:00Z", "level": "INFO", "message": "Service started"},
                {"timestamp": "2025-05-01T12:01:00Z", "level": "INFO", "message": "Document processed"},
                {"timestamp": "2025-05-01T12:02:00Z", "level": "WARN", "message": "Low confidence field detected"}
            ],
            "count": 3
        }
        
        # Act
        response = client.get("/diagnostics/logs?limit=10&level=INFO", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "logs" in response.json()
        assert len(response.json()["logs"]) == 3
        mock_ocr_service.get_logs.assert_called_once_with(limit=10, level="INFO")
    
    @patch("api.diagnostics.get_ocr_service")
    def test_get_config(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the GET /diagnostics/config endpoint correctly retrieves service configuration."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_config.return_value = {
            "model_version": "v2.3.0",
            "confidence_threshold": 0.75,
            "gpu_enabled": True,
            "max_document_size": 10485760,  # 10MB
            "supported_formats": ["pdf", "png", "jpg", "tiff"]
        }
        
        # Act
        response = client.get("/diagnostics/config", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "model_version" in response.json()
        assert "confidence_threshold" in response.json()
        mock_ocr_service.get_config.assert_called_once()
    
    @patch("api.diagnostics.get_ocr_service")
    def test_run_diagnostic_test(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the POST /diagnostics/test endpoint correctly runs diagnostic tests."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.run_diagnostic_test.return_value = {
            "test_id": "test-123",
            "status": "passed",
            "results": {
                "model_loading": "passed",
                "gpu_access": "passed",
                "s3_connectivity": "passed",
                "rabbitmq_connectivity": "passed"
            },
            "execution_time": 1.5
        }
        
        # Act
        response = client.post(
            "/diagnostics/test", 
            headers=auth_headers,
            json={"test_type": "full"}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "passed"
        assert "results" in response.json()
        mock_ocr_service.run_diagnostic_test.assert_called_once_with(test_type="full")
    
    @patch("api.diagnostics.get_ocr_service")
    def test_get_models(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the GET /diagnostics/models endpoint correctly retrieves model information."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.get_models.return_value = {
            "models": [
                {
                    "name": "typed_text_model",
                    "version": "v2.3.0",
                    "type": "TYPED",
                    "loaded": True,
                    "last_used": "2025-05-01T11:45:00Z"
                },
                {
                    "name": "handwritten_text_model",
                    "version": "v1.8.2",
                    "type": "HANDWRITTEN",
                    "loaded": True,
                    "last_used": "2025-05-01T10:30:00Z"
                },
                {
                    "name": "hybrid_text_model",
                    "version": "v1.5.0",
                    "type": "HYBRID",
                    "loaded": True,
                    "last_used": "2025-05-01T09:15:00Z"
                }
            ],
            "count": 3
        }
        
        # Act
        response = client.get("/diagnostics/models", headers=auth_headers)
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert "models" in response.json()
        assert len(response.json()["models"]) == 3
        mock_ocr_service.get_models.assert_called_once()
    
    @patch("api.diagnostics.get_ocr_service")
    def test_reload_models(self, mock_get_ocr_service, client, mock_ocr_service, auth_headers):
        """Test that the POST /diagnostics/models/reload endpoint correctly reloads models."""
        # Arrange
        mock_get_ocr_service.return_value = mock_ocr_service
        mock_ocr_service.reload_models.return_value = {
            "status": "success",
            "reloaded": 3,
            "execution_time": 2.5
        }
        
        # Act
        response = client.post(
            "/diagnostics/models/reload", 
            headers=auth_headers,
            json={"model_types": ["TYPED", "HANDWRITTEN", "HYBRID"]}
        )
        
        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "success"
        assert response.json()["reloaded"] == 3
        mock_ocr_service.reload_models.assert_called_once_with(
            model_types=["TYPED", "HANDWRITTEN", "HYBRID"]
        )


# Test authentication and authorization integration
class TestAuthenticationIntegration:
    
    def test_missing_auth_header(self, client):
        """Test that endpoints requiring authentication reject requests without auth headers."""
        # Act - Try to access a protected endpoint without auth headers
        response = client.get("/ocr/test-doc-123")
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()
    
    @patch("api.ocr.verify_token")
    def test_invalid_auth_token(self, mock_verify_token, client):
        """Test that endpoints requiring authentication reject requests with invalid tokens."""
        # Arrange
        mock_verify_token.return_value = False
        headers = {"Authorization": "Bearer invalid_token"}
        
        # Act - Try to access a protected endpoint with invalid token
        response = client.get("/ocr/test-doc-123", headers=headers)
        
        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "detail" in response.json()
    
    @patch("api.ocr.verify_token")
    @patch("api.ocr.check_permissions")
    def test_insufficient_permissions(self, mock_check_permissions, mock_verify_token, client):
        """Test that endpoints requiring specific permissions reject requests without those permissions."""
        # Arrange
        mock_verify_token.return_value = True  # Token is valid
        mock_check_permissions.return_value = False  # But permissions are insufficient
        headers = {"Authorization": "Bearer valid_token"}
        
        # Act - Try to access a protected endpoint with insufficient permissions
        response = client.post(
            "/diagnostics/models/reload", 
            headers=headers,
            json={"model_types": ["TYPED"]}
        )
        
        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert "detail" in response.json()