#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Integration tests for the Document Service API endpoints.

This module contains tests that verify the API correctly handles document operations,
health checks, status reporting, and diagnostics. It validates request validation,
response formatting, error handling, and authentication.
"""

import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Generator, Tuple

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import application modules
from app import create_app
from services.classification_service import ClassificationService
from services.document_routing_service import DocumentRoutingService
from services.queue_service import QueueService
from services.storage_service import StorageService
from types.documents import Document, DocumentType, ProcessingStatus
from types.classification import ClassificationResult, ConfidenceScore
from types.errors import ServiceError, ErrorCategory
from utils.security_utils import create_test_token


# Fixtures
@pytest.fixture
def app() -> FastAPI:
    """Create a FastAPI application instance for testing.
    
    Returns:
        FastAPI: The application instance
    """
    return create_app(testing=True)


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create a test client for the FastAPI application.
    
    Args:
        app: The FastAPI application instance
        
    Returns:
        TestClient: The test client
    """
    return TestClient(app)


@pytest.fixture
def admin_token() -> str:
    """Create a JWT token with admin permissions.
    
    Returns:
        str: The JWT token
    """
    return create_test_token({
        "sub": "admin-user",
        "name": "Admin User",
        "email": "admin@example.com",
        "roles": ["System Admin"]
    })


@pytest.fixture
def operations_token() -> str:
    """Create a JWT token with operations staff permissions.
    
    Returns:
        str: The JWT token
    """
    return create_test_token({
        "sub": "ops-user",
        "name": "Operations User",
        "email": "ops@example.com",
        "roles": ["Operations Staff"]
    })


@pytest.fixture
def regular_token() -> str:
    """Create a JWT token with regular user permissions.
    
    Returns:
        str: The JWT token
    """
    return create_test_token({
        "sub": "regular-user",
        "name": "Regular User",
        "email": "user@example.com",
        "roles": ["User"]
    })


@pytest.fixture
def mock_queue_service() -> Generator[MagicMock, None, None]:
    """Mock the QueueService for testing.
    
    Yields:
        MagicMock: The mocked QueueService
    """
    with patch("app.QueueService") as mock:
        # Configure the mock
        instance = mock.return_value
        instance.check_connection.return_value = True
        instance.get_queue_depth.return_value = 5
        instance.get_connection_count.return_value = 2
        yield instance


@pytest.fixture
def mock_storage_service() -> Generator[MagicMock, None, None]:
    """Mock the StorageService for testing.
    
    Yields:
        MagicMock: The mocked StorageService
    """
    with patch("app.StorageService") as mock:
        # Configure the mock
        instance = mock.return_value
        instance.check_connection.return_value = True
        
        # Mock document retrieval
        test_doc_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        test_doc = Document(
            id=test_doc_id,
            metadata={
                "filename": "test_document.pdf",
                "size": 1024,
                "mime_type": "application/pdf"
            },
            status=ProcessingStatus.RECEIVED,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        instance.get_document.return_value = test_doc
        instance.get_document_metadata.return_value = test_doc
        
        # Mock document listing
        instance.list_documents.return_value = ([test_doc], 1)
        
        yield instance


@pytest.fixture
def mock_classification_service() -> Generator[MagicMock, None, None]:
    """Mock the ClassificationService for testing.
    
    Yields:
        MagicMock: The mocked ClassificationService
    """
    with patch("app.ClassificationService") as mock:
        # Configure the mock
        instance = mock.return_value
        
        # Mock classification result
        test_doc_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        classification_result = ClassificationResult(
            document_id=test_doc_id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(value=0.95),
            classified_at=datetime.now()
        )
        instance.get_classification_result.return_value = classification_result
        instance.classify_document.return_value = classification_result
        
        yield instance


@pytest.fixture
def mock_document_routing_service() -> Generator[MagicMock, None, None]:
    """Mock the DocumentRoutingService for testing.
    
    Yields:
        MagicMock: The mocked DocumentRoutingService
    """
    with patch("app.DocumentRoutingService") as mock:
        # Configure the mock
        instance = mock.return_value
        
        # Mock routing result
        instance.route_document.return_value = MagicMock(
            destination="ocr-service",
            routed_at=datetime.now()
        )
        
        yield instance


# Health Check Tests
@pytest.mark.integration
class TestHealthEndpoints:
    """Tests for the health check endpoints."""
    
    def test_liveness_probe(self, client: TestClient):
        """Test the liveness probe endpoint."""
        response = client.get("/health/liveness")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "timestamp" in data
        assert data["service"] == "document-service"
    
    def test_readiness_probe_success(self, client: TestClient, mock_queue_service: MagicMock, mock_storage_service: MagicMock):
        """Test the readiness probe endpoint when all dependencies are available."""
        # Configure mocks for successful connections
        mock_queue_service.check_connection.return_value = True
        mock_storage_service.check_connection.return_value = True
        
        response = client.get("/health/readiness")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "timestamp" in data
        assert data["service"] == "document-service"
        assert data["dependencies"]["rabbitmq"]["status"] == "UP"
        assert data["dependencies"]["s3"]["status"] == "UP"
    
    def test_readiness_probe_rabbitmq_down(self, client: TestClient, mock_queue_service: MagicMock, mock_storage_service: MagicMock):
        """Test the readiness probe endpoint when RabbitMQ is down."""
        # Configure mocks for RabbitMQ connection failure
        mock_queue_service.check_connection.return_value = False
        mock_storage_service.check_connection.return_value = True
        
        response = client.get("/health/readiness")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "DOWN"
        assert data["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert data["dependencies"]["s3"]["status"] == "UP"
    
    def test_readiness_probe_s3_down(self, client: TestClient, mock_queue_service: MagicMock, mock_storage_service: MagicMock):
        """Test the readiness probe endpoint when S3 is down."""
        # Configure mocks for S3 connection failure
        mock_queue_service.check_connection.return_value = True
        mock_storage_service.check_connection.return_value = False
        
        response = client.get("/health/readiness")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "DOWN"
        assert data["dependencies"]["rabbitmq"]["status"] == "UP"
        assert data["dependencies"]["s3"]["status"] == "DOWN"
    
    def test_readiness_probe_all_down(self, client: TestClient, mock_queue_service: MagicMock, mock_storage_service: MagicMock):
        """Test the readiness probe endpoint when all dependencies are down."""
        # Configure mocks for all connections failing
        mock_queue_service.check_connection.return_value = False
        mock_storage_service.check_connection.return_value = False
        
        response = client.get("/health/readiness")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "DOWN"
        assert data["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert data["dependencies"]["s3"]["status"] == "DOWN"
    
    def test_health_check_endpoint(self, client: TestClient, mock_queue_service: MagicMock, mock_storage_service: MagicMock):
        """Test the general health check endpoint."""
        # Configure mocks for successful connections
        mock_queue_service.check_connection.return_value = True
        mock_storage_service.check_connection.return_value = True
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "UP"
        assert "timestamp" in data
        assert "service" in data
        assert "dependencies" in data
        assert "details" in data
        assert data["dependencies"]["rabbitmq"]["status"] == "UP"
        assert data["dependencies"]["s3"]["status"] == "UP"
    
    def test_health_check_connection_error(self, client: TestClient, mock_queue_service: MagicMock, mock_storage_service: MagicMock):
        """Test the health check endpoint when a connection error occurs."""
        # Configure mock to raise an exception
        mock_queue_service.check_connection.side_effect = Exception("Connection error")
        
        response = client.get("/health")
        
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "DOWN"
        assert data["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert "Connection error" in data["dependencies"]["rabbitmq"]["details"]["message"]


# Document Operations Tests
@pytest.mark.integration
class TestDocumentEndpoints:
    """Tests for the document operations endpoints."""
    
    def test_get_document(self, client: TestClient, mock_storage_service: MagicMock, mock_classification_service: MagicMock):
        """Test retrieving a document's classification status."""
        # Test document ID
        doc_id = "00000000-0000-0000-0000-000000000001"
        
        response = client.get(f"/documents/{doc_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert "metadata" in data
        assert "status" in data
        assert "classification" in data
        assert data["classification"]["document_type"] == "APPLICATION"
        assert data["classification"]["confidence"] == 0.95
        assert data["classification"]["requires_review"] is False
    
    def test_get_document_not_found(self, client: TestClient, mock_storage_service: MagicMock):
        """Test retrieving a non-existent document."""
        # Configure mock to return None for non-existent document
        mock_storage_service.get_document_metadata.return_value = None
        
        response = client.get("/documents/00000000-0000-0000-0000-000000000999")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]
    
    def test_get_document_invalid_id(self, client: TestClient):
        """Test retrieving a document with an invalid ID."""
        response = client.get("/documents/invalid-id")
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_classify_document(self, client: TestClient, mock_storage_service: MagicMock, 
                              mock_classification_service: MagicMock, mock_document_routing_service: MagicMock):
        """Test manually triggering document classification."""
        # Test document ID
        doc_id = "00000000-0000-0000-0000-000000000001"
        
        response = client.post(f"/documents/{doc_id}/classify")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert data["status"] == "classification_complete"
        assert "classification" in data
        assert "routing" in data
        assert data["classification"]["document_type"] == "APPLICATION"
        assert data["classification"]["confidence"] == 0.95
        assert data["routing"]["destination"] == "ocr-service"
    
    def test_classify_document_already_classified(self, client: TestClient, mock_storage_service: MagicMock, 
                                                mock_classification_service: MagicMock):
        """Test classifying an already classified document without force flag."""
        # Test document ID
        doc_id = "00000000-0000-0000-0000-000000000001"
        
        # Configure mock to return existing classification
        mock_classification_service.get_classification_result.return_value = ClassificationResult(
            document_id=uuid.UUID(doc_id),
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(value=0.95),
            classified_at=datetime.now()
        )
        
        response = client.post(f"/documents/{doc_id}/classify?force=false")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert data["status"] == "already_classified"
        assert data["classification"]["document_type"] == "APPLICATION"
    
    def test_classify_document_force_reclassification(self, client: TestClient, mock_storage_service: MagicMock, 
                                                    mock_classification_service: MagicMock, 
                                                    mock_document_routing_service: MagicMock):
        """Test forcing reclassification of an already classified document."""
        # Test document ID
        doc_id = "00000000-0000-0000-0000-000000000001"
        
        # Configure mock to return existing classification
        mock_classification_service.get_classification_result.return_value = ClassificationResult(
            document_id=uuid.UUID(doc_id),
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(value=0.95),
            classified_at=datetime.now()
        )
        
        response = client.post(f"/documents/{doc_id}/classify?force=true")
        
        assert response.status_code == 200
        data = response.json()
        assert data["document_id"] == doc_id
        assert data["status"] == "classification_complete"
        
        # Verify classify_document was called
        mock_classification_service.classify_document.assert_called_once()
    
    def test_classify_document_not_found(self, client: TestClient, mock_storage_service: MagicMock):
        """Test classifying a non-existent document."""
        # Configure mock to return None for non-existent document
        mock_storage_service.get_document.return_value = None
        
        response = client.post("/documents/00000000-0000-0000-0000-000000000999/classify")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"]
    
    def test_classify_document_service_error(self, client: TestClient, mock_storage_service: MagicMock, 
                                           mock_classification_service: MagicMock):
        """Test handling of service errors during classification."""
        # Test document ID
        doc_id = "00000000-0000-0000-0000-000000000001"
        
        # Configure mock to raise a service error
        mock_classification_service.classify_document.side_effect = ServiceError(
            message="Classification error",
            category=ErrorCategory.PROCESSING
        )
        
        response = client.post(f"/documents/{doc_id}/classify")
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Classification error" in data["detail"]
    
    def test_batch_classify(self, client: TestClient, mock_classification_service: MagicMock):
        """Test batch document classification."""
        # Test document IDs
        doc_ids = [
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
            "00000000-0000-0000-0000-000000000003"
        ]
        
        response = client.post("/documents/batch", json=doc_ids)
        
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        assert "results" in data
        assert data["summary"]["total"] == 3
        
        # Verify queue_for_classification was called for each document
        assert mock_classification_service.queue_for_classification.call_count == 3
    
    def test_batch_classify_empty_list(self, client: TestClient):
        """Test batch classification with an empty list."""
        response = client.post("/documents/batch", json=[])
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "No document IDs provided" in data["detail"]
    
    def test_batch_classify_too_many_documents(self, client: TestClient):
        """Test batch classification with too many documents."""
        # Create a list of 101 document IDs (exceeding the limit of 100)
        doc_ids = [str(uuid.uuid4()) for _ in range(101)]
        
        response = client.post("/documents/batch", json=doc_ids)
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Batch size exceeds maximum limit" in data["detail"]
    
    def test_list_documents(self, client: TestClient, mock_storage_service: MagicMock, mock_classification_service: MagicMock):
        """Test listing documents with filtering."""
        response = client.get("/documents?document_type=application&status=received&page=1&page_size=20")
        
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "pagination" in data
        assert len(data["documents"]) == 1  # Our mock returns 1 document
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 20
        
        # Verify list_documents was called with correct parameters
        mock_storage_service.list_documents.assert_called_once()
        call_args = mock_storage_service.list_documents.call_args[1]
        assert call_args["page"] == 1
        assert call_args["page_size"] == 20
    
    def test_list_documents_invalid_filter(self, client: TestClient):
        """Test listing documents with an invalid filter."""
        response = client.get("/documents?document_type=invalid_type")
        
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "Invalid document type" in data["detail"]


# Status Endpoint Tests
@pytest.mark.integration
class TestStatusEndpoints:
    """Tests for the status endpoints."""
    
    def test_get_status(self, client: TestClient, mock_queue_service: MagicMock):
        """Test retrieving service status."""
        # Configure mock
        mock_queue_service.get_queue_depth.return_value = 5
        mock_queue_service.get_connection_count.return_value = 2
        
        response = client.get("/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "operational"
        assert data["service"] == "document-service"
        assert "version" in data
        assert "uptime_seconds" in data
        assert "resources" in data
        assert "queue" in data
        assert "connections" in data
        assert data["queue"]["document_processing_depth"] == 5
        assert data["connections"]["rabbitmq"] == 2
    
    def test_get_status_queue_error(self, client: TestClient, mock_queue_service: MagicMock):
        """Test status endpoint when queue service has an error."""
        # Configure mock to raise an exception
        mock_queue_service.get_queue_depth.side_effect = Exception("Queue error")
        
        response = client.get("/status")
        
        assert response.status_code == 200  # Should still return 200 even with queue error
        data = response.json()
        assert data["status"] == "operational"
        assert data["queue"]["document_processing_depth"] == -1  # Error indicator
    
    def test_health_check(self, client: TestClient):
        """Test the simple health check endpoint."""
        response = client.get("/status/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_metrics_endpoint(self, client: TestClient, mock_queue_service: MagicMock):
        """Test the Prometheus metrics endpoint."""
        response = client.get("/status/metrics")
        
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/openmetrics-text; version=1.0.0; charset=utf-8"
        # Prometheus metrics are plain text, so we can't easily parse them as JSON
        assert "document_service_" in response.text
    
    def test_processing_stats(self, client: TestClient):
        """Test retrieving processing statistics."""
        response = client.get("/status/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "throughput" in data
        assert "accuracy" in data
        assert "errors" in data
        assert "queue_status" in data
        assert data["accuracy"]["overall_percent"] > 90  # Should be high accuracy


# Diagnostics Endpoint Tests
@pytest.mark.integration
class TestDiagnosticsEndpoints:
    """Tests for the diagnostics endpoints."""
    
    def test_get_logs_unauthorized(self, client: TestClient):
        """Test retrieving logs without authentication."""
        response = client.get("/diagnostics/logs")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_get_logs_forbidden(self, client: TestClient, regular_token: str):
        """Test retrieving logs with insufficient permissions."""
        response = client.get(
            "/diagnostics/logs",
            headers={"Authorization": f"Bearer {regular_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "required" in data["detail"]
    
    def test_get_logs_operations_staff(self, client: TestClient, operations_token: str):
        """Test retrieving logs with operations staff permissions."""
        with patch("utils.logging_utils.get_logs") as mock_get_logs:
            # Configure mock to return sample logs
            mock_get_logs.return_value = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "INFO",
                    "message": "Test log message",
                    "context": {"test": True}
                }
            ]
            
            response = client.get(
                "/diagnostics/logs?limit=10&level=INFO",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "logs" in data
            assert "count" in data
            assert data["count"] == 1
            assert data["logs"][0]["level"] == "INFO"
            assert data["logs"][0]["message"] == "Test log message"
            
            # Verify get_logs was called with correct parameters
            mock_get_logs.assert_called_once_with(
                limit=10, level="INFO", start_time=None, end_time=None
            )
    
    def test_get_logs_admin(self, client: TestClient, admin_token: str):
        """Test retrieving logs with admin permissions."""
        with patch("utils.logging_utils.get_logs") as mock_get_logs:
            # Configure mock to return sample logs
            mock_get_logs.return_value = [
                {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "message": "Test error message",
                    "context": {"error": True}
                }
            ]
            
            response = client.get(
                "/diagnostics/logs?limit=10&level=ERROR",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "logs" in data
            assert "count" in data
            assert data["count"] == 1
            assert data["logs"][0]["level"] == "ERROR"
    
    def test_get_config_unauthorized(self, client: TestClient):
        """Test retrieving configuration without authentication."""
        response = client.get("/diagnostics/config")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_get_config_forbidden(self, client: TestClient, operations_token: str):
        """Test retrieving configuration with insufficient permissions."""
        response = client.get(
            "/diagnostics/config",
            headers={"Authorization": f"Bearer {operations_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert "detail" in data
        assert "Admin permissions required" in data["detail"]
    
    def test_get_config_admin(self, client: TestClient, admin_token: str):
        """Test retrieving configuration with admin permissions."""
        with patch("config.app_config.load_config") as mock_load_config:
            # Configure mock to return sample config
            mock_config = MagicMock()
            mock_config.service_name = "document-service"
            mock_config.version = "1.0.0"
            mock_config.port = 8000
            mock_config.host = "0.0.0.0"
            mock_config.debug = False
            mock_config.environment = "test"
            
            # RabbitMQ config
            mock_config.rabbitmq = MagicMock()
            mock_config.rabbitmq.__dict__ = {
                "host": "rabbitmq",
                "port": 5672,
                "username": "user",
                "password": "password",
                "vhost": "/",
                "exchange": "mca.documents",
                "queue": "document-processing"
            }
            
            # S3 config
            mock_config.s3 = MagicMock()
            mock_config.s3.__dict__ = {
                "endpoint": "s3.amazonaws.com",
                "region": "us-east-1",
                "bucket": "mca-documents-test",
                "access_key": "access_key",
                "secret_key": "secret_key",
                "encryption_key": "encryption_key"
            }
            
            # Model config
            mock_config.model = MagicMock()
            mock_config.model.__dict__ = {
                "path": "/models",
                "version": "1.0.0",
                "type": "svm"
            }
            
            mock_load_config.return_value = mock_config
            
            response = client.get(
                "/diagnostics/config",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            assert "rabbitmq" in data
            assert "s3" in data
            assert "model" in data
            assert "environment" in data
            assert data["service"]["name"] == "document-service"
            assert data["environment"] == "test"
            
            # Verify sensitive values are masked
            assert data["rabbitmq"]["password"] == "*****"
            assert data["s3"]["access_key"] == "*****"
            assert data["s3"]["secret_key"] == "*****"
            assert data["s3"]["encryption_key"] == "*****"
    
    def test_run_diagnostic_tests_unauthorized(self, client: TestClient):
        """Test running diagnostic tests without authentication."""
        response = client.get("/diagnostics/test")
        
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data
    
    def test_run_diagnostic_tests_operations_staff(self, client: TestClient, operations_token: str):
        """Test running diagnostic tests with operations staff permissions."""
        with patch("app.get_application") as mock_get_app, \
             patch("utils.rabbitmq_utils.test_rabbitmq_connection") as mock_test_rabbitmq, \
             patch("utils.s3_utils.test_s3_connection") as mock_test_s3, \
             patch("utils.ml_utils.get_model_info") as mock_get_model_info:
            
            # Configure mocks
            mock_app = MagicMock()
            mock_app.queue_service = MagicMock()
            mock_app.storage_service = MagicMock()
            mock_app.classification_service = MagicMock()
            mock_app.start_time = time.time() - 3600  # 1 hour ago
            mock_get_app.return_value = mock_app
            
            mock_test_rabbitmq.return_value = {
                "connected": True,
                "latency_ms": 5.2,
                "details": "Connected to RabbitMQ"
            }
            
            mock_test_s3.return_value = {
                "connected": True,
                "latency_ms": 12.7,
                "details": "Connected to S3"
            }
            
            mock_get_model_info.return_value = {
                "loaded": True,
                "version": "1.0.0",
                "accuracy": 0.992,
                "last_trained": "2023-01-15T12:00:00Z",
                "document_types": ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"]
            }
            
            response = client.get(
                "/diagnostics/test",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "timestamp" in data
            assert "system" in data
            assert "rabbitmq" in data
            assert "s3" in data
            assert "model" in data
            assert "overall_status" in data
            assert data["overall_status"] == "healthy"
            assert data["rabbitmq"]["connected"] is True
            assert data["s3"]["connected"] is True
            assert data["model"]["loaded"] is True
    
    def test_run_diagnostic_tests_degraded(self, client: TestClient, operations_token: str):
        """Test running diagnostic tests with degraded service."""
        with patch("app.get_application") as mock_get_app, \
             patch("utils.rabbitmq_utils.test_rabbitmq_connection") as mock_test_rabbitmq, \
             patch("utils.s3_utils.test_s3_connection") as mock_test_s3, \
             patch("utils.ml_utils.get_model_info") as mock_get_model_info:
            
            # Configure mocks
            mock_app = MagicMock()
            mock_app.queue_service = MagicMock()
            mock_app.storage_service = MagicMock()
            mock_app.classification_service = MagicMock()
            mock_get_app.return_value = mock_app
            
            mock_test_rabbitmq.return_value = {
                "connected": True,
                "latency_ms": 5.2,
                "details": "Connected to RabbitMQ"
            }
            
            mock_test_s3.return_value = {
                "connected": True,
                "latency_ms": 12.7,
                "details": "Connected to S3"
            }
            
            # Model not loaded
            mock_get_model_info.return_value = {
                "loaded": False,
                "version": "1.0.0",
                "accuracy": 0.0,
                "last_trained": "2023-01-15T12:00:00Z",
                "document_types": []
            }
            
            response = client.get(
                "/diagnostics/test",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_status"] == "degraded"
            assert data["rabbitmq"]["connected"] is True
            assert data["s3"]["connected"] is True
            assert data["model"]["loaded"] is False
    
    def test_run_diagnostic_tests_critical(self, client: TestClient, operations_token: str):
        """Test running diagnostic tests with critical failures."""
        with patch("app.get_application") as mock_get_app, \
             patch("utils.rabbitmq_utils.test_rabbitmq_connection") as mock_test_rabbitmq, \
             patch("utils.s3_utils.test_s3_connection") as mock_test_s3, \
             patch("utils.ml_utils.get_model_info") as mock_get_model_info:
            
            # Configure mocks
            mock_app = MagicMock()
            mock_app.queue_service = MagicMock()
            mock_app.storage_service = MagicMock()
            mock_app.classification_service = MagicMock()
            mock_get_app.return_value = mock_app
            
            # RabbitMQ connection failure
            mock_test_rabbitmq.return_value = {
                "connected": False,
                "error": "Connection refused"
            }
            
            # S3 connection failure
            mock_test_s3.return_value = {
                "connected": False,
                "error": "Access denied"
            }
            
            mock_get_model_info.return_value = {
                "loaded": True,
                "version": "1.0.0",
                "accuracy": 0.992,
                "last_trained": "2023-01-15T12:00:00Z",
                "document_types": ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"]
            }
            
            response = client.get(
                "/diagnostics/test",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_status"] == "critical"
            assert data["rabbitmq"]["connected"] is False
            assert data["s3"]["connected"] is False
            assert "Connection refused" in data["rabbitmq"]["error"]
            assert "Access denied" in data["s3"]["error"]
    
    def test_test_rabbitmq(self, client: TestClient, operations_token: str):
        """Test the RabbitMQ connection test endpoint."""
        with patch("app.get_application") as mock_get_app, \
             patch("utils.rabbitmq_utils.test_rabbitmq_connection") as mock_test_rabbitmq:
            
            # Configure mocks
            mock_app = MagicMock()
            mock_app.queue_service = MagicMock()
            mock_get_app.return_value = mock_app
            
            mock_test_rabbitmq.return_value = {
                "connected": True,
                "latency_ms": 5.2,
                "details": "Connected to RabbitMQ and published test message"
            }
            
            response = client.post(
                "/diagnostics/test/rabbitmq",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["latency_ms"] == 5.2
            assert "test message" in data["details"]
            
            # Verify test_rabbitmq_connection was called with test_publish=True
            mock_test_rabbitmq.assert_called_once_with(mock_app.queue_service, test_publish=True)
    
    def test_test_s3(self, client: TestClient, operations_token: str):
        """Test the S3 connection test endpoint."""
        with patch("app.get_application") as mock_get_app, \
             patch("utils.s3_utils.test_s3_connection") as mock_test_s3:
            
            # Configure mocks
            mock_app = MagicMock()
            mock_app.storage_service = MagicMock()
            mock_get_app.return_value = mock_app
            
            mock_test_s3.return_value = {
                "connected": True,
                "latency_ms": 12.7,
                "details": "Connected to S3 and verified write access"
            }
            
            response = client.post(
                "/diagnostics/test/s3",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert data["latency_ms"] == 12.7
            assert "verified write access" in data["details"]
            
            # Verify test_s3_connection was called with test_write=True
            mock_test_s3.assert_called_once_with(mock_app.storage_service, test_write=True)
    
    def test_test_model(self, client: TestClient, operations_token: str):
        """Test the model test endpoint."""
        with patch("app.get_application") as mock_get_app, \
             patch("utils.ml_utils.get_model_info") as mock_get_model_info:
            
            # Configure mocks
            mock_app = MagicMock()
            mock_app.classification_service = MagicMock()
            mock_get_app.return_value = mock_app
            
            mock_get_model_info.return_value = {
                "loaded": True,
                "version": "1.0.0",
                "accuracy": 0.992,
                "last_trained": "2023-01-15T12:00:00Z",
                "document_types": ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"]
            }
            
            response = client.post(
                "/diagnostics/test/model",
                headers={"Authorization": f"Bearer {operations_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["loaded"] is True
            assert data["version"] == "1.0.0"
            assert data["accuracy"] == 0.992
            assert data["document_types"] == ["APPLICATION", "TAX_RETURN", "BANK_STATEMENT"]
            
            # Verify get_model_info was called with run_test=True
            mock_get_model_info.assert_called_once_with(mock_app.classification_service, run_test=True)