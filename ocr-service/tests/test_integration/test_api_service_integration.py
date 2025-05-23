"""Integration tests for the OCR Service API and Service layer integration.

This module tests the integration between the API layer and service layer of the OCR Service.
It verifies that API endpoints correctly invoke the appropriate services and return proper
responses, ensuring that the API accurately reflects the state and capabilities of the
underlying services.

The tests focus on:
1. API endpoints correctly invoking service methods with the right parameters
2. Service responses being correctly transformed into API responses
3. Error propagation from services to API responses
4. Request validation and parameter handling across the API-service boundary
5. Authentication and authorization integration with services
"""

import json
import os
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call
import sys
from pathlib import Path

# Add the src directory to the path so we can import the modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, status
from fastapi.testclient import TestClient

# Import the API routers
from src.api.ocr import router as ocr_router
from src.api.health import router as health_router
from src.api.status import router as status_router
from src.api.diagnostics import router as diagnostics_router

# Import the service interfaces
from src.services.ocr_service import OCRService
from src.services.storage_service import StorageService
from src.services.queue_service import QueueService
from src.services.field_extraction_service import FieldExtractionService
from src.services.confidence_service import ConfidenceService

# Import the types
from src.types.extraction import ExtractedData, ConfidenceScore
from src.types.errors import ServiceError, ErrorCategory
from src.types.messages import MessagePayload
from src.types.storage import StorageMetadata
from src.types.models import OCRModelType, ModelResult


# Test classes for API-Service integration
class TestOCRApiServiceIntegration:
    """Test the integration between OCR API endpoints and OCR service."""
    
    def test_get_ocr_results_service_integration(self, integration_client, mock_storage_service, 
                                               sample_document_id, sample_ocr_results, sample_document_metadata):
        """Test that GET /ocr/{document_id} correctly integrates with storage service."""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_ocr_results["document_id"] = sample_document_id
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        mock_storage_service.get_ocr_results.return_value = sample_ocr_results
        
        # Make request
        response = integration_client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["document_id"] == sample_document_id
        assert "extracted_fields" in response.json()
        assert "metadata" in response.json()
        
        # Verify service calls - this is the key part of integration testing
        mock_storage_service.get_document_metadata.assert_called_once_with(sample_document_id)
        mock_storage_service.get_ocr_results.assert_called_once_with(sample_document_id)
    
    def test_get_ocr_results_with_confidence_filtering(self, integration_client, mock_storage_service, 
                                                    mock_confidence_service, sample_document_id, 
                                                    sample_ocr_results, sample_document_metadata):
        """Test that confidence filtering correctly integrates with confidence service."""
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
        response = integration_client.get(f"/ocr/{sample_document_id}?confidence_threshold=0.9")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "extracted_fields" in response.json()
        
        # Verify confidence service integration
        mock_confidence_service.filter_by_confidence.assert_called_once_with(sample_ocr_results, 0.9)
    
    def test_process_document_service_integration(self, integration_client, mock_storage_service, 
                                               mock_ocr_service, sample_document_id, sample_document_metadata):
        """Test that POST /ocr/{document_id}/process correctly integrates with OCR service."""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_document_metadata["processing_status"] = "PENDING"
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        
        # Make request
        response = integration_client.post(f"/ocr/{sample_document_id}/process")
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert "queued for processing" in response.json()["message"].lower()
        
        # Verify service calls - this is the key part of integration testing
        mock_storage_service.get_document_metadata.assert_called_once_with(sample_document_id)
        mock_storage_service.update_document_metadata.assert_called_once_with(
            sample_document_id, {"processing_status": "PROCESSING"}
        )
        mock_ocr_service.process_document.assert_called_once_with(sample_document_id, None)
    
    def test_process_document_with_document_type(self, integration_client, mock_storage_service, 
                                              mock_ocr_service, sample_document_id, sample_document_metadata):
        """Test document processing with specified document type integration."""
        # Setup mocks
        sample_document_metadata["document_id"] = sample_document_id
        sample_document_metadata["processing_status"] = "PENDING"
        mock_storage_service.get_document_metadata.return_value = sample_document_metadata
        
        # Make request with document type
        document_type = "TAX_RETURN"
        response = integration_client.post(f"/ocr/{sample_document_id}/process?document_type={document_type}")
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        # Verify service calls with correct document type
        mock_ocr_service.process_document.assert_called_once_with(sample_document_id, document_type)
    
    def test_batch_processing_service_integration(self, integration_client, mock_storage_service, mock_ocr_service):
        """Test that POST /ocr/batch correctly integrates with OCR service for multiple documents."""
        # Generate document IDs
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Setup mocks
        mock_storage_service.get_document_metadata.side_effect = [
            {"document_id": doc_id, "processing_status": "PENDING"}
            for doc_id in document_ids
        ]
        
        # Make request
        response = integration_client.post(
            "/ocr/batch",
            json={"document_ids": document_ids}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.json()["processed"] == 3
        assert response.json()["skipped"] == 0
        
        # Verify service calls
        assert mock_storage_service.update_document_metadata.call_count == 3
        assert mock_ocr_service.process_document.call_count == 3
        
        # Verify each document was processed with the correct ID
        for doc_id in document_ids:
            mock_ocr_service.process_document.assert_any_call(doc_id, None)
    
    def test_confidence_threshold_management(self, integration_client, mock_confidence_service):
        """Test that confidence threshold management correctly integrates with confidence service."""
        # Test getting thresholds
        response = integration_client.get("/ocr/confidence/threshold")
        assert response.status_code == status.HTTP_200_OK
        assert "APPLICATION" in response.json()
        mock_confidence_service.get_confidence_thresholds.assert_called_once()
        
        # Test updating a threshold
        document_type = "APPLICATION"
        new_threshold = 0.85
        response = integration_client.put(
            f"/ocr/confidence/threshold/{document_type}",
            json={"threshold": new_threshold}
        )
        
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["document_type"] == document_type
        assert response.json()["threshold"] == new_threshold
        
        # Verify service call
        mock_confidence_service.set_confidence_threshold.assert_called_once_with(
            document_type, new_threshold
        )
    
    def test_error_propagation_from_service(self, integration_client, mock_storage_service, sample_document_id):
        """Test that errors from services are properly propagated to API responses."""
        # Setup mock to raise a service error
        error_message = "Database connection error"
        mock_storage_service.get_document_metadata.side_effect = ServiceError(
            error_message, ErrorCategory.DATABASE
        )
        
        # Make request
        response = integration_client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert error_message.lower() in response.json()["detail"].lower()


class TestHealthApiServiceIntegration:
    """Test the integration between Health API endpoints and underlying services."""
    
    def test_liveness_probe_integration(self, integration_client):
        """Test that GET /health/liveness correctly reports application liveness."""
        response = integration_client.get("/health/liveness")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"
    
    def test_readiness_probe_integration(self, integration_client, mock_queue_service, mock_storage_service):
        """Test that GET /health/readiness correctly integrates with required services."""
        # Setup mocks
        mock_queue_service.is_connected.return_value = True
        mock_storage_service.is_connected.return_value = True
        
        # Make request
        response = integration_client.get("/health/readiness")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["status"] == "ok"
        assert "dependencies" in response.json()
        assert response.json()["dependencies"]["rabbitmq"] == "ok"
        assert response.json()["dependencies"]["s3"] == "ok"
        
        # Verify service calls
        mock_queue_service.is_connected.assert_called_once()
        mock_storage_service.is_connected.assert_called_once()
    
    def test_readiness_probe_with_service_failure(self, integration_client, mock_queue_service, mock_storage_service):
        """Test that readiness probe correctly reports service failures."""
        # Setup mocks - RabbitMQ is down
        mock_queue_service.is_connected.return_value = False
        mock_storage_service.is_connected.return_value = True
        
        # Make request
        response = integration_client.get("/health/readiness")
        
        # Assertions
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["status"] == "error"
        assert response.json()["dependencies"]["rabbitmq"] == "error"
        assert response.json()["dependencies"]["s3"] == "ok"


class TestStatusApiServiceIntegration:
    """Test the integration between Status API endpoints and underlying services."""
    
    def test_metrics_endpoint_integration(self, integration_client, mock_queue_service, mock_ocr_service):
        """Test that GET /status/metrics correctly integrates with services for metrics."""
        # Setup mocks
        mock_queue_service.get_queue_depth.return_value = 5
        mock_ocr_service.get_accuracy_metrics.return_value = {
            "overall_accuracy": 0.99,  # 99% as specified in requirements
            "field_accuracies": {
                "business_name": 0.98,
                "tax_id": 0.97,
                "address": 0.96
            }
        }
        
        # Make request
        response = integration_client.get("/status/metrics")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "metrics" in response.json()
        assert "queue_depth" in response.json()["metrics"]
        assert "ocr_accuracy" in response.json()["metrics"]
        assert response.json()["metrics"]["queue_depth"] == 5
        assert response.json()["metrics"]["ocr_accuracy"] == 0.99
        
        # Verify service calls
        mock_queue_service.get_queue_depth.assert_called_once()
        mock_ocr_service.get_accuracy_metrics.assert_called_once()


class TestDiagnosticsApiServiceIntegration:
    """Test the integration between Diagnostics API endpoints and underlying services."""
    
    def test_models_endpoint_integration(self, integration_client, mock_ocr_service):
        """Test that GET /diagnostics/models correctly integrates with OCR service."""
        # Setup mocks
        mock_ocr_service.get_model_info.return_value = [
            {
                "model_type": "TYPED",
                "version": "v2.1.0",
                "accuracy": 0.98,
                "last_updated": "2025-05-01T10:00:00Z"
            },
            {
                "model_type": "HANDWRITTEN",
                "version": "v1.5.0",
                "accuracy": 0.95,
                "last_updated": "2025-04-15T14:30:00Z"
            },
            {
                "model_type": "HYBRID",
                "version": "v1.2.0",
                "accuracy": 0.93,
                "last_updated": "2025-04-20T09:15:00Z"
            }
        ]
        
        # Make request
        response = integration_client.get("/diagnostics/models")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert "models" in response.json()
        assert len(response.json()["models"]) == 3
        assert response.json()["models"][0]["model_type"] == "TYPED"
        
        # Verify service calls
        mock_ocr_service.get_model_info.assert_called_once()
    
    def test_model_reload_integration(self, integration_client, mock_ocr_service):
        """Test that POST /diagnostics/models/reload correctly integrates with OCR service."""
        # Setup mocks
        mock_ocr_service.reload_models.return_value = {
            "success": True,
            "models_reloaded": 3,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Make request
        response = integration_client.post("/diagnostics/models/reload")
        
        # Assertions
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] == True
        assert response.json()["models_reloaded"] == 3
        
        # Verify service calls
        mock_ocr_service.reload_models.assert_called_once()


class TestAuthorizationIntegration:
    """Test the integration between API authorization and service layer."""
    
    @patch("src.api.ocr.verify_token")
    def test_secured_endpoint_with_valid_token(self, mock_verify_token, integration_client, 
                                             mock_ocr_service, mock_storage_service, sample_document_id):
        """Test that secured endpoints correctly integrate with auth service for valid tokens."""
        # Setup mocks
        mock_verify_token.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        
        mock_storage_service.get_document_metadata.return_value = {
            "document_id": sample_document_id,
            "processing_status": "PENDING"
        }
        
        # Make request to a secured endpoint with token
        response = integration_client.post(
            f"/ocr/{sample_document_id}/process",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_202_ACCEPTED
        
        # Verify token verification was called
        mock_verify_token.assert_called_once_with("valid-token")
    
    @patch("src.api.ocr.verify_token")
    def test_secured_endpoint_with_invalid_token(self, mock_verify_token, integration_client, sample_document_id):
        """Test that secured endpoints correctly handle invalid tokens."""
        # Setup mocks to simulate invalid token
        mock_verify_token.side_effect = ServiceError("Invalid token", ErrorCategory.AUTHENTICATION)
        
        # Make request to a secured endpoint with invalid token
        response = integration_client.post(
            f"/ocr/{sample_document_id}/process",
            headers={"Authorization": "Bearer invalid-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Verify token verification was called
        mock_verify_token.assert_called_once_with("invalid-token")
    
    @patch("src.api.ocr.verify_token")
    def test_secured_endpoint_with_insufficient_permissions(self, mock_verify_token, integration_client, sample_document_id):
        """Test that secured endpoints correctly handle tokens with insufficient permissions."""
        # Setup mocks to simulate token with insufficient permissions
        mock_verify_token.return_value = {
            "sub": "test-user",
            "roles": ["read_only"],  # Role without write permissions
            "exp": (datetime.utcnow() + timedelta(hours=1)).timestamp()
        }
        
        # Make request to a secured endpoint requiring write permissions
        response = integration_client.post(
            f"/ocr/{sample_document_id}/process",
            headers={"Authorization": "Bearer limited-token"}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_403_FORBIDDEN
        
        # Verify token verification was called
        mock_verify_token.assert_called_once_with("limited-token")


class TestErrorHandlingIntegration:
    """Test the integration between API error handling and service layer errors."""
    
    def test_service_error_propagation(self, integration_client, mock_storage_service, sample_document_id):
        """Test that service errors are properly propagated to API responses."""
        # Setup mock to raise different types of service errors
        errors = [
            (ServiceError("Database connection failed", ErrorCategory.DATABASE), status.HTTP_500_INTERNAL_SERVER_ERROR),
            (ServiceError("Document not found", ErrorCategory.NOT_FOUND), status.HTTP_404_NOT_FOUND),
            (ServiceError("Invalid document format", ErrorCategory.VALIDATION), status.HTTP_400_BAD_REQUEST),
            (ServiceError("Service temporarily unavailable", ErrorCategory.SERVICE_UNAVAILABLE), status.HTTP_503_SERVICE_UNAVAILABLE),
        ]
        
        for error, expected_status in errors:
            # Reset mock and set side effect
            mock_storage_service.get_document_metadata.reset_mock()
            mock_storage_service.get_document_metadata.side_effect = error
            
            # Make request
            response = integration_client.get(f"/ocr/{sample_document_id}")
            
            # Assertions
            assert response.status_code == expected_status
            assert error.message.lower() in response.json()["detail"].lower()
    
    def test_validation_error_handling(self, integration_client):
        """Test that validation errors are properly handled and returned."""
        # Make request with invalid confidence threshold (outside 0-1 range)
        response = integration_client.put(
            "/ocr/confidence/threshold/APPLICATION",
            json={"threshold": 1.5}  # Invalid: > 1.0
        )
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Make request with invalid document type
        response = integration_client.put(
            "/ocr/confidence/threshold/INVALID_TYPE",
            json={"threshold": 0.8}
        )
        
        # Assertions
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_unexpected_exception_handling(self, integration_client, mock_storage_service, sample_document_id):
        """Test that unexpected exceptions are properly caught and returned as 500 errors."""
        # Setup mock to raise an unexpected exception
        mock_storage_service.get_document_metadata.side_effect = Exception("Unexpected error")
        
        # Make request
        response = integration_client.get(f"/ocr/{sample_document_id}")
        
        # Assertions
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "internal server error" in response.json()["detail"].lower()

# Test fixtures
@pytest.fixture
def app():
    """Create a FastAPI app with all routers for integration testing."""
    app = FastAPI(title="OCR Service", description="OCR Service API", version="1.0.0")
    app.include_router(ocr_router, prefix="/ocr")
    app.include_router(health_router, prefix="/health")
    app.include_router(status_router, prefix="/status")
    app.include_router(diagnostics_router, prefix="/diagnostics")
    return app


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_ocr_service():
    """Create a mock OCR service that tracks interactions for verification."""
    mock = MagicMock(spec=OCRService)
    mock.process_document = AsyncMock()
    mock.get_model_info = MagicMock()
    mock.reload_models = AsyncMock()
    return mock


@pytest.fixture
def mock_storage_service():
    """Create a mock storage service that tracks interactions for verification."""
    mock = MagicMock(spec=StorageService)
    mock.get_document_metadata = AsyncMock()
    mock.get_ocr_results = AsyncMock()
    mock.update_document_metadata = AsyncMock()
    mock.store_ocr_results = AsyncMock()
    return mock


@pytest.fixture
def mock_queue_service():
    """Create a mock queue service that tracks interactions for verification."""
    mock = MagicMock(spec=QueueService)
    mock.publish_message = AsyncMock()
    mock.consume_messages = AsyncMock()
    mock.get_queue_depth = AsyncMock(return_value=5)
    return mock


@pytest.fixture
def mock_field_extraction_service():
    """Create a mock field extraction service that tracks interactions for verification."""
    mock = MagicMock(spec=FieldExtractionService)
    mock.extract_fields = MagicMock()
    mock.validate_fields = MagicMock()
    mock.format_extracted_data = MagicMock()
    return mock


@pytest.fixture
def mock_confidence_service():
    """Create a mock confidence service that tracks interactions for verification."""
    mock = MagicMock(spec=ConfidenceService)
    mock.calculate_confidence = MagicMock()
    mock.filter_by_confidence = MagicMock()
    mock.get_confidence_thresholds = MagicMock(return_value={
        "APPLICATION": 0.8,
        "TAX_RETURN": 0.85,
        "BANK_STATEMENT": 0.9,
        "PAY_STUB": 0.85,
        "ID_DOCUMENT": 0.95,
        "OTHER": 0.75
    })
    mock.set_confidence_threshold = MagicMock()
    return mock


@pytest.fixture
def sample_document_id():
    """Generate a sample document ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_ocr_results():
    """Generate sample OCR results for testing."""
    return {
        "document_id": str(uuid.uuid4()),
        "document_type": "APPLICATION",
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
    """Generate sample document metadata for testing."""
    return {
        "document_id": str(uuid.uuid4()),
        "filename": "application_form.pdf",
        "file_size": 1024567,
        "mime_type": "application/pdf",
        "document_type": "APPLICATION",
        "processing_status": "COMPLETED",
        "created_at": "2025-05-21T14:25:30Z",
        "updated_at": "2025-05-21T14:30:45Z",
        "processing_metrics": {
            "processing_time": 2.34,
            "confidence_avg": 0.89,
            "page_count": 3
        }
    }


@pytest.fixture
def app_with_mocked_services(app, mock_ocr_service, mock_storage_service, mock_queue_service, 
                           mock_field_extraction_service, mock_confidence_service):
    """Create a FastAPI app with all services mocked for integration testing."""
    # Override the service dependencies
    app.dependency_overrides[ocr_router.get_ocr_service] = lambda: mock_ocr_service
    app.dependency_overrides[ocr_router.get_storage_service] = lambda: mock_storage_service
    app.dependency_overrides[ocr_router.get_queue_service] = lambda: mock_queue_service
    app.dependency_overrides[ocr_router.get_field_extraction_service] = lambda: mock_field_extraction_service
    app.dependency_overrides[ocr_router.get_confidence_service] = lambda: mock_confidence_service
    
    # Override health check dependencies
    app.dependency_overrides[health_router.get_queue_service] = lambda: mock_queue_service
    app.dependency_overrides[health_router.get_storage_service] = lambda: mock_storage_service
    
    # Override status dependencies
    app.dependency_overrides[status_router.get_queue_service] = lambda: mock_queue_service
    app.dependency_overrides[status_router.get_ocr_service] = lambda: mock_ocr_service
    
    return app


@pytest.fixture
def integration_client(app_with_mocked_services):
    """Create a test client with mocked services for integration testing."""
    return TestClient(app_with_mocked_services)