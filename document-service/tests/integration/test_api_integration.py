#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the Document Service API endpoints.

This module contains tests that verify the Document Service API endpoints work correctly
with the underlying document processing functionality. It tests health checks, document
operations, status reporting, and diagnostic endpoints.

These tests validate:
- Request validation and response formatting
- Error handling and status codes
- Authentication and authorization
- Integration with underlying services (RabbitMQ, S3)
"""

import json
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app import create_app
from services.classification_service import ClassificationService
from services.document_routing_service import DocumentRoutingService
from services.storage_service import StorageService
from services.queue_service import QueueService
from types.documents import Document, DocumentType, ProcessingStatus
from types.classification import ClassificationResult, ConfidenceScore
from utils.validation_utils import generate_jwt_token


# Fixtures
@pytest.fixture
def app():
    """Create a test instance of the FastAPI application."""
    return create_app(testing=True)


@pytest.fixture
def client(app):
    """Create a test client for the FastAPI application."""
    return TestClient(app)


@pytest.fixture
def admin_token():
    """Generate a valid JWT token with system_admin role."""
    return generate_jwt_token({
        "sub": "test-admin",
        "name": "Test Admin",
        "email": "admin@example.com",
        "roles": ["system_admin"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    })


@pytest.fixture
def operations_token():
    """Generate a valid JWT token with operations_staff role."""
    return generate_jwt_token({
        "sub": "test-ops",
        "name": "Test Operations",
        "email": "ops@example.com",
        "roles": ["operations_staff"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    })


@pytest.fixture
def user_token():
    """Generate a valid JWT token with regular user role (no special permissions)."""
    return generate_jwt_token({
        "sub": "test-user",
        "name": "Test User",
        "email": "user@example.com",
        "roles": ["user"],
        "exp": datetime.utcnow() + timedelta(hours=1)
    })


@pytest.fixture
def expired_token():
    """Generate an expired JWT token."""
    return generate_jwt_token({
        "sub": "test-expired",
        "name": "Test Expired",
        "email": "expired@example.com",
        "roles": ["operations_staff"],
        "exp": datetime.utcnow() - timedelta(hours=1)
    })


@pytest.fixture
def mock_document():
    """Create a mock document for testing."""
    return Document(
        id=uuid.uuid4(),
        file_name="test_document.pdf",
        file_type="application/pdf",
        file_size=1024,
        status=ProcessingStatus.RECEIVED,
        metadata={
            "source": "email",
            "sender": "test@example.com",
            "received_at": datetime.utcnow().isoformat()
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


@pytest.fixture
def mock_classification_result(mock_document):
    """Create a mock classification result for testing."""
    return ClassificationResult(
        document_id=mock_document.id,
        document_type=DocumentType.APPLICATION_FORM,
        confidence=ConfidenceScore(0.95),
        classified_at=datetime.utcnow()
    )


# Health Check Endpoint Tests
@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for the health check endpoints."""

    def test_liveness_check(self, client):
        """Test that the liveness endpoint returns a 200 status code."""
        response = client.get("/health/liveness")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "UP"
        assert "version" in data
        assert "details" in data

    def test_readiness_check_success(self, client):
        """Test that the readiness endpoint returns a 200 status code when all dependencies are available."""
        # Mock the dependencies to be available
        with patch.object(QueueService, 'is_connected', return_value=True), \
             patch.object(StorageService, 'is_connected', return_value=True), \
             patch.object(StorageService, 'get_bucket_name', return_value="test-bucket"):
            
            response = client.get("/health/readiness")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "UP"
            assert data["details"]["dependencies"]["rabbitmq"]["status"] == "UP"
            assert data["details"]["dependencies"]["s3"]["status"] == "UP"

    def test_readiness_check_rabbitmq_down(self, client):
        """Test that the readiness endpoint returns a 503 status code when RabbitMQ is down."""
        # Mock RabbitMQ to be down
        with patch.object(QueueService, 'is_connected', return_value=False), \
             patch.object(StorageService, 'is_connected', return_value=True), \
             patch.object(StorageService, 'get_bucket_name', return_value="test-bucket"):
            
            response = client.get("/health/readiness")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "DOWN"
            assert data["details"]["dependencies"]["rabbitmq"]["status"] == "DOWN"
            assert data["details"]["dependencies"]["s3"]["status"] == "UP"

    def test_readiness_check_s3_down(self, client):
        """Test that the readiness endpoint returns a 503 status code when S3 is down."""
        # Mock S3 to be down
        with patch.object(QueueService, 'is_connected', return_value=True), \
             patch.object(StorageService, 'is_connected', return_value=False):
            
            response = client.get("/health/readiness")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "DOWN"
            assert data["details"]["dependencies"]["rabbitmq"]["status"] == "UP"
            assert data["details"]["dependencies"]["s3"]["status"] == "DOWN"

    def test_readiness_check_all_down(self, client):
        """Test that the readiness endpoint returns a 503 status code when all dependencies are down."""
        # Mock all dependencies to be down
        with patch.object(QueueService, 'is_connected', return_value=False), \
             patch.object(StorageService, 'is_connected', return_value=False):
            
            response = client.get("/health/readiness")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "DOWN"
            assert data["details"]["dependencies"]["rabbitmq"]["status"] == "DOWN"
            assert data["details"]["dependencies"]["s3"]["status"] == "DOWN"

    def test_readiness_check_exception(self, client):
        """Test that the readiness endpoint handles exceptions gracefully."""
        # Mock an exception during health check
        with patch.object(QueueService, 'is_connected', side_effect=Exception("Test exception")), \
             patch.object(StorageService, 'is_connected', return_value=True), \
             patch.object(StorageService, 'get_bucket_name', return_value="test-bucket"):
            
            response = client.get("/health/readiness")
            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            data = response.json()
            assert data["status"] == "DOWN"
            assert data["details"]["dependencies"]["rabbitmq"]["status"] == "DOWN"
            assert "error" in data["details"]["dependencies"]["rabbitmq"]["details"]


# Document API Endpoint Tests
@pytest.mark.integration
class TestDocumentEndpoints:
    """Tests for the document API endpoints."""

    def test_get_document_success(self, client, mock_document, mock_classification_result):
        """Test retrieving a document's classification status."""
        document_id = mock_document.id
        
        # Mock the storage and classification services
        with patch.object(StorageService, 'get_document_metadata', return_value=mock_document), \
             patch.object(ClassificationService, 'get_classification_result', return_value=mock_classification_result):
            
            response = client.get(f"/documents/{document_id}")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["document_id"] == str(document_id)
            assert data["status"] == mock_document.status.value
            assert "metadata" in data
            assert "classification" in data
            assert data["classification"]["document_type"] == mock_classification_result.document_type.value
            assert data["classification"]["confidence"] == mock_classification_result.confidence.value

    def test_get_document_not_found(self, client):
        """Test retrieving a non-existent document."""
        document_id = uuid.uuid4()
        
        # Mock the storage service to return None (document not found)
        with patch.object(StorageService, 'get_document_metadata', return_value=None):
            
            response = client.get(f"/documents/{document_id}")
            assert response.status_code == status.HTTP_404_NOT_FOUND
            data = response.json()
            assert "detail" in data
            assert f"Document with ID {document_id} not found" in data["detail"]

    def test_get_document_invalid_id(self, client):
        """Test retrieving a document with an invalid ID."""
        response = client.get("/documents/invalid-uuid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_document_server_error(self, client, mock_document):
        """Test server error handling when retrieving a document."""
        document_id = mock_document.id
        
        # Mock the storage service to raise an exception
        with patch.object(StorageService, 'get_document_metadata', side_effect=Exception("Test exception")):
            
            response = client.get(f"/documents/{document_id}")
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            data = response.json()
            assert "detail" in data

    def test_classify_document_success(self, client, mock_document, mock_classification_result):
        """Test manually triggering document classification."""
        document_id = mock_document.id
        
        # Mock the services
        with patch.object(StorageService, 'get_document', return_value=mock_document), \
             patch.object(ClassificationService, 'get_classification_result', return_value=None), \
             patch.object(ClassificationService, 'classify_document', return_value=mock_classification_result), \
             patch.object(DocumentRoutingService, 'route_document', return_value=MagicMock(destination="ocr-service", routed_at=datetime.utcnow())), \
             patch.object(StorageService, 'update_document_metadata', return_value=None):
            
            response = client.post(f"/documents/{document_id}/classify")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["document_id"] == str(document_id)
            assert data["status"] == "classification_complete"
            assert "classification" in data
            assert data["classification"]["document_type"] == mock_classification_result.document_type.value
            assert data["classification"]["confidence"] == mock_classification_result.confidence.value
            assert "routing" in data
            assert data["routing"]["destination"] == "ocr-service"

    def test_classify_document_already_classified(self, client, mock_document, mock_classification_result):
        """Test manually triggering classification for an already classified document."""
        document_id = mock_document.id
        
        # Mock the services to indicate document is already classified
        with patch.object(StorageService, 'get_document', return_value=mock_document), \
             patch.object(ClassificationService, 'get_classification_result', return_value=mock_classification_result):
            
            response = client.post(f"/documents/{document_id}/classify")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["document_id"] == str(document_id)
            assert data["status"] == "already_classified"
            assert "classification" in data

    def test_classify_document_force_reclassification(self, client, mock_document, mock_classification_result):
        """Test forcing reclassification of an already classified document."""
        document_id = mock_document.id
        
        # Mock the services
        with patch.object(StorageService, 'get_document', return_value=mock_document), \
             patch.object(ClassificationService, 'get_classification_result', return_value=mock_classification_result), \
             patch.object(ClassificationService, 'classify_document', return_value=mock_classification_result), \
             patch.object(DocumentRoutingService, 'route_document', return_value=MagicMock(destination="ocr-service", routed_at=datetime.utcnow())), \
             patch.object(StorageService, 'update_document_metadata', return_value=None):
            
            response = client.post(f"/documents/{document_id}/classify?force=true")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["document_id"] == str(document_id)
            assert data["status"] == "classification_complete"

    def test_classify_document_not_found(self, client):
        """Test classifying a non-existent document."""
        document_id = uuid.uuid4()
        
        # Mock the storage service to return None (document not found)
        with patch.object(StorageService, 'get_document', return_value=None):
            
            response = client.post(f"/documents/{document_id}/classify")
            assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_batch_classify_success(self, client):
        """Test batch document classification."""
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Mock the services
        with patch.object(StorageService, 'get_document', return_value=MagicMock()), \
             patch.object(ClassificationService, 'get_classification_result', return_value=None), \
             patch.object(ClassificationService, 'queue_for_classification', return_value=None):
            
            response = client.post(
                "/documents/batch",
                json={"document_ids": document_ids}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "summary" in data
            assert data["summary"]["total"] == len(document_ids)
            assert data["summary"]["successful"] == len(document_ids)
            assert data["summary"]["failed"] == 0
            assert data["summary"]["skipped"] == 0

    def test_batch_classify_empty_list(self, client):
        """Test batch classification with an empty list of document IDs."""
        response = client.post(
            "/documents/batch",
            json={"document_ids": []}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_batch_classify_too_many_documents(self, client):
        """Test batch classification with too many document IDs."""
        document_ids = [str(uuid.uuid4()) for _ in range(101)]  # Exceeds the 100 limit
        
        response = client.post(
            "/documents/batch",
            json={"document_ids": document_ids}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_batch_classify_mixed_results(self, client):
        """Test batch classification with mixed results (success, failure, skipped)."""
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        
        # Mock the services with different behaviors for each document
        with patch.object(StorageService, 'get_document', side_effect=[
                MagicMock(),  # First document exists
                None,          # Second document doesn't exist
                MagicMock()    # Third document exists
            ]), \
             patch.object(ClassificationService, 'get_classification_result', side_effect=[
                None,           # First document not classified
                None,           # Second document not relevant (will fail earlier)
                MagicMock()     # Third document already classified
            ]), \
             patch.object(ClassificationService, 'queue_for_classification', return_value=None):
            
            response = client.post(
                "/documents/batch",
                json={"document_ids": document_ids}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["summary"]["total"] == 3
            assert data["summary"]["successful"] == 1
            assert data["summary"]["failed"] == 1
            assert data["summary"]["skipped"] == 1

    def test_list_documents_success(self, client, mock_document):
        """Test listing documents with filtering."""
        # Mock the services
        with patch.object(StorageService, 'list_documents', return_value=([mock_document], 1)), \
             patch.object(ClassificationService, 'get_classification_result', return_value=None):
            
            response = client.get("/documents?page=1&page_size=20")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "documents" in data
            assert len(data["documents"]) == 1
            assert "pagination" in data
            assert data["pagination"]["page"] == 1
            assert data["pagination"]["total_items"] == 1

    def test_list_documents_with_filters(self, client, mock_document, mock_classification_result):
        """Test listing documents with various filters."""
        # Mock the services
        with patch.object(StorageService, 'list_documents', return_value=([mock_document], 1)), \
             patch.object(ClassificationService, 'get_classification_result', return_value=mock_classification_result):
            
            response = client.get(
                "/documents?document_type=APPLICATION_FORM&status=RECEIVED&confidence_min=0.9&requires_review=false"
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["documents"]) == 1
            assert "classification" in data["documents"][0]

    def test_list_documents_invalid_filter(self, client):
        """Test listing documents with invalid filter values."""
        response = client.get("/documents?document_type=INVALID_TYPE")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_documents_empty_result(self, client):
        """Test listing documents with no results."""
        # Mock the services to return empty results
        with patch.object(StorageService, 'list_documents', return_value=([], 0)):
            
            response = client.get("/documents")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert len(data["documents"]) == 0
            assert data["pagination"]["total_items"] == 0


# Status API Endpoint Tests
@pytest.mark.integration
class TestStatusEndpoints:
    """Tests for the status API endpoints."""

    def test_get_status_success(self, client):
        """Test retrieving service status."""
        # Mock the services
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory', return_value=MagicMock(used=1024*1024*1024, percent=50.0)), \
             patch('psutil.disk_usage', return_value=MagicMock(percent=50.0)), \
             patch('psutil.net_connections', return_value=[]), \
             patch('psutil.Process', return_value=MagicMock(open_files=lambda: [])), \
             patch.object(QueueService, 'get_queue_stats', return_value=[]), \
             patch.object(DocumentService, 'get_processing_stats', return_value=MagicMock(
                 total_processed=100,
                 successful=95,
                 failed=5,
                 avg_processing_time=2.5,
                 classification_accuracy=0.95,
                 documents_by_type={"APPLICATION_FORM": 50, "TAX_RETURN": 30, "BANK_STATEMENT": 20}
             )):
            
            response = client.get("/status")
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "status" in data
            assert "version" in data
            assert "system" in data
            assert "queues" in data
            assert "document_stats" in data

    def test_get_metrics_success(self, client, operations_token):
        """Test retrieving Prometheus metrics with valid token."""
        response = client.get(
            "/status/metrics",
            headers={"Authorization": f"Bearer {operations_token}"}
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"

    def test_get_metrics_unauthorized(self, client):
        """Test retrieving metrics without authentication."""
        response = client.get("/status/metrics")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_metrics_forbidden(self, client, user_token):
        """Test retrieving metrics with insufficient permissions."""
        response = client.get(
            "/status/metrics",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_metrics_expired_token(self, client, expired_token):
        """Test retrieving metrics with an expired token."""
        response = client.get(
            "/status/metrics",
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_document_stats_success(self, client, admin_token):
        """Test retrieving detailed document processing statistics with admin token."""
        # Mock the document service
        with patch.object(DocumentService, 'get_detailed_stats', return_value={
            "document_types": [
                {"type": "APPLICATION_FORM", "count": 50, "avg_confidence": 0.95},
                {"type": "TAX_RETURN", "count": 30, "avg_confidence": 0.92},
                {"type": "BANK_STATEMENT", "count": 20, "avg_confidence": 0.88}
            ],
            "processing_times": {
                "avg_seconds": 2.5,
                "p50_seconds": 2.0,
                "p95_seconds": 5.0,
                "p99_seconds": 10.0
            },
            "accuracy": {
                "overall": 0.95,
                "by_type": {
                    "APPLICATION_FORM": 0.98,
                    "TAX_RETURN": 0.95,
                    "BANK_STATEMENT": 0.90
                }
            }
        }):
            
            response = client.get(
                "/status/stats",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "document_types" in data
            assert "processing_times" in data
            assert "accuracy" in data


# Diagnostics API Endpoint Tests
@pytest.mark.integration
class TestDiagnosticsEndpoints:
    """Tests for the diagnostics API endpoints."""

    def test_get_logs_success(self, client, operations_token):
        """Test retrieving logs with valid token."""
        # Mock the log file reading
        mock_log_entries = [
            json.dumps({
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "service": "document-service",
                "message": "Test log message",
                "correlation_id": "test-correlation-id",
                "environment": "test"
            })
        ]
        
        with patch('builtins.open', return_value=MagicMock(__enter__=lambda _: MagicMock(readlines=lambda: mock_log_entries))), \
             patch('os.path.exists', return_value=True):
            
            response = client.get(
                "/diagnostics/logs?level=INFO&limit=10",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "logs" in data
            assert len(data["logs"]) == 1
            assert data["logs"][0]["level"] == "INFO"
            assert data["logs"][0]["message"] == "Test log message"

    def test_get_logs_unauthorized(self, client):
        """Test retrieving logs without authentication."""
        response = client.get("/diagnostics/logs")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_logs_forbidden(self, client, user_token):
        """Test retrieving logs with insufficient permissions."""
        response = client.get(
            "/diagnostics/logs",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_get_config_success(self, client, operations_token):
        """Test retrieving service configuration with valid token."""
        # Mock the configuration retrieval
        with patch('app_config.get_safe_config', return_value={
            "log_level": "INFO",
            "rabbitmq": {"host": "rabbitmq", "port": 5672},
            "s3": {"bucket": "test-bucket"}
        }), \
        patch('os.environ.get', side_effect=lambda key, default: 
              "test" if key == "ENVIRONMENT" else 
              "1.0.0" if key == "SERVICE_VERSION" else 
              default), \
        patch('_get_package_version', return_value="1.0.0"), \
        patch('_get_python_version', return_value="3.9.0"):
            
            response = client.get(
                "/diagnostics/config",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "app_config" in data
            assert "environment" in data
            assert "version" in data
            assert "dependencies" in data

    def test_run_diagnostic_tests_success(self, client, operations_token):
        """Test running diagnostic tests with valid token."""
        # Mock the test functions
        with patch('_test_rabbitmq_connection', return_value={
            "test_name": "RabbitMQ Connection",
            "status": "success",
            "message": "Successfully connected to RabbitMQ",
            "details": {"connected": True}
        }), \
        patch('_test_s3_connection', return_value={
            "test_name": "S3 Storage Connection",
            "status": "success",
            "message": "Successfully connected to S3 storage",
            "details": {"connected": True}
        }):
            
            response = client.post(
                "/diagnostics/test",
                json={"test_type": "all"},
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "test_results" in data
            assert "overall_status" in data
            assert "execution_time" in data
            assert data["overall_status"] == "success"

    def test_run_diagnostic_tests_partial_failure(self, client, operations_token):
        """Test running diagnostic tests with partial failure."""
        # Mock the test functions with one success and one failure
        with patch('_test_rabbitmq_connection', return_value={
            "test_name": "RabbitMQ Connection",
            "status": "success",
            "message": "Successfully connected to RabbitMQ",
            "details": {"connected": True}
        }), \
        patch('_test_s3_connection', return_value={
            "test_name": "S3 Storage Connection",
            "status": "failure",
            "message": "Failed to connect to S3 storage",
            "details": {"connected": False, "error": "Connection timeout"}
        }):
            
            response = client.post(
                "/diagnostics/test",
                json={"test_type": "all"},
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["overall_status"] == "failure"
            assert len(data["test_results"]) == 2
            assert any(result["status"] == "failure" for result in data["test_results"])


if __name__ == "__main__":
    pytest.main()