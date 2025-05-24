import json
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Import necessary modules from the document service
# Use relative imports since we're in the tests directory
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.types.status import DocumentStatus, ProcessingStage, StatusHistory


# ============================================================================
# Test Status API Endpoints
# ============================================================================

@pytest.mark.parametrize(
    "expected_status", 
    ["UP", "DEGRADED"]
)
def test_get_status(test_client, mock_s3_storage, mock_rabbitmq_client, expected_status):
    """
    Test the GET /status endpoint.
    
    This test verifies that the status endpoint returns the correct service status
    and includes all required information about system metrics, queue status, and
    document processing statistics.
    
    Args:
        test_client: FastAPI test client
        mock_s3_storage: Mock S3 storage client
        mock_rabbitmq_client: Mock RabbitMQ client
        expected_status: Expected service status (UP or DEGRADED)
    """
    # Mock the DocumentService.get_processing_stats method
    with patch("src.services.document_service.DocumentService.get_processing_stats") as mock_get_stats:
        # Configure mock to return different stats based on expected status
        if expected_status == "UP":
            mock_get_stats.return_value = {
                "total_processed": 1000,
                "successful": 990,
                "failed": 10,
                "avg_processing_time": 2.5,
                "classification_accuracy": 0.99,
                "documents_by_type": {
                    "LOAN_APPLICATION": 300,
                    "TAX_RETURN": 200,
                    "BANK_STATEMENT": 250,
                    "PAY_STUB": 150,
                    "IDENTITY_DOCUMENT": 100
                }
            }
        else:  # DEGRADED
            mock_get_stats.return_value = {
                "total_processed": 1000,
                "successful": 850,
                "failed": 150,  # High failure rate
                "avg_processing_time": 8.5,  # Slow processing
                "classification_accuracy": 0.85,  # Lower accuracy
                "documents_by_type": {
                    "LOAN_APPLICATION": 300,
                    "TAX_RETURN": 200,
                    "BANK_STATEMENT": 250,
                    "PAY_STUB": 150,
                    "IDENTITY_DOCUMENT": 100
                }
            }
        
        # Mock the QueueService.get_queue_stats method
        with patch("src.services.queue_service.QueueService.get_queue_stats") as mock_queue_stats:
            # Configure mock to return different queue stats based on expected status
            if expected_status == "UP":
                mock_queue_stats.return_value = [
                    {
                        "queue_name": "document-processing",
                        "depth": 5,
                        "processing_rate": 120.5,
                        "consumers": 3
                    },
                    {
                        "queue_name": "data-extraction",
                        "depth": 2,
                        "processing_rate": 90.2,
                        "consumers": 2
                    }
                ]
            else:  # DEGRADED
                mock_queue_stats.return_value = [
                    {
                        "queue_name": "document-processing",
                        "depth": 1500,  # Queue backup
                        "processing_rate": 50.5,  # Slow processing
                        "consumers": 3
                    },
                    {
                        "queue_name": "data-extraction",
                        "depth": 800,  # Queue backup
                        "processing_rate": 30.2,  # Slow processing
                        "consumers": 2
                    }
                ]
            
            # Mock system metrics
            with patch("psutil.cpu_percent") as mock_cpu, \
                 patch("psutil.virtual_memory") as mock_memory, \
                 patch("psutil.disk_usage") as mock_disk, \
                 patch("psutil.net_connections") as mock_connections, \
                 patch("psutil.Process") as mock_process:
                
                # Configure mocks based on expected status
                if expected_status == "UP":
                    mock_cpu.return_value = 45.5  # Normal CPU usage
                    mock_memory.return_value.used = 4 * 1024 * 1024 * 1024  # 4 GB
                    mock_memory.return_value.percent = 40.0  # Normal memory usage
                    mock_disk.return_value.percent = 60.0  # Normal disk usage
                else:  # DEGRADED
                    mock_cpu.return_value = 92.5  # High CPU usage
                    mock_memory.return_value.used = 14 * 1024 * 1024 * 1024  # 14 GB
                    mock_memory.return_value.percent = 92.0  # High memory usage
                    mock_disk.return_value.percent = 95.0  # High disk usage
                
                # Common mocks for both scenarios
                mock_connections.return_value = [MagicMock() for _ in range(10)]
                mock_process.return_value.open_files.return_value = [MagicMock() for _ in range(20)]
                
                # Make request to status endpoint
                response = test_client.get("/status")
                
                # Verify response
                assert response.status_code == 200
                data = response.json()
                
                # Check basic structure
                assert "status" in data
                assert "version" in data
                assert "environment" in data
                assert "timestamp" in data
                assert "uptime_seconds" in data
                assert "system" in data
                assert "queues" in data
                assert "document_stats" in data
                
                # Check status matches expected
                assert data["status"] == expected_status
                
                # Check system metrics
                assert "cpu_usage_percent" in data["system"]
                assert "memory_usage_bytes" in data["system"]
                assert "memory_usage_percent" in data["system"]
                assert "disk_usage_percent" in data["system"]
                assert "open_connections" in data["system"]
                assert "open_file_descriptors" in data["system"]
                
                # Check queue information
                assert len(data["queues"]) == 2
                for queue in data["queues"]:
                    assert "queue_name" in queue
                    assert "depth" in queue
                    assert "processing_rate" in queue
                    assert "consumers" in queue
                
                # Check document stats
                assert "total_processed" in data["document_stats"]
                assert "successful" in data["document_stats"]
                assert "failed" in data["document_stats"]
                assert "avg_processing_time" in data["document_stats"]
                assert "classification_accuracy" in data["document_stats"]
                assert "documents_by_type" in data["document_stats"]


def test_get_metrics_unauthorized(test_client):
    """
    Test the GET /status/metrics endpoint without authentication.
    
    This test verifies that the metrics endpoint requires authentication
    and returns a 401 Unauthorized response when no token is provided.
    
    Args:
        test_client: FastAPI test client
    """
    # Make request without authentication
    response = test_client.get("/status/metrics")
    
    # Verify response
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_metrics_authorized(test_client, mock_auth_headers):
    """
    Test the GET /status/metrics endpoint with authentication.
    
    This test verifies that the metrics endpoint returns Prometheus-formatted
    metrics when a valid authentication token is provided.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Mock system metrics
        with patch("psutil.cpu_percent") as mock_cpu, \
             patch("psutil.virtual_memory") as mock_memory, \
             patch("psutil.disk_usage") as mock_disk, \
             patch("psutil.net_connections") as mock_connections:
            
            # Configure mocks
            mock_cpu.return_value = 45.5
            mock_memory.return_value.used = 4 * 1024 * 1024 * 1024  # 4 GB
            mock_disk.return_value.percent = 60.0
            mock_connections.return_value = [MagicMock() for _ in range(10)]
            
            # Make request with authentication
            response = test_client.get("/status/metrics", headers=mock_auth_headers)
            
            # Verify response
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/plain; version=0.0.4; charset=utf-8"
            
            # Check that response contains Prometheus metrics
            content = response.content.decode("utf-8")
            assert "document_service_documents_processed_total" in content
            assert "document_service_processing_seconds" in content
            assert "document_service_classification_accuracy" in content
            assert "document_service_queue_depth" in content
            assert "document_service_cpu_usage_percent" in content
            assert "document_service_memory_usage_bytes" in content
            assert "document_service_api_requests_total" in content


def test_get_document_stats_unauthorized(test_client):
    """
    Test the GET /status/stats endpoint without authentication.
    
    This test verifies that the document stats endpoint requires authentication
    and returns a 401 Unauthorized response when no token is provided.
    
    Args:
        test_client: FastAPI test client
    """
    # Make request without authentication
    response = test_client.get("/status/stats")
    
    # Verify response
    assert response.status_code == 401
    assert "detail" in response.json()
    assert "WWW-Authenticate" in response.headers
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_get_document_stats_authorized(test_client, mock_auth_headers):
    """
    Test the GET /status/stats endpoint with authentication.
    
    This test verifies that the document stats endpoint returns detailed
    document processing statistics when a valid authentication token is provided.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Mock the DocumentService.get_detailed_stats method
        with patch("src.services.document_service.DocumentService.get_detailed_stats") as mock_get_stats:
            # Configure mock to return detailed stats
            mock_get_stats.return_value = {
                "total_processed": 1000,
                "successful": 990,
                "failed": 10,
                "avg_processing_time": 2.5,
                "classification_accuracy": 0.99,
                "documents_by_type": {
                    "LOAN_APPLICATION": 300,
                    "TAX_RETURN": 200,
                    "BANK_STATEMENT": 250,
                    "PAY_STUB": 150,
                    "IDENTITY_DOCUMENT": 100
                },
                "processing_time_by_type": {
                    "LOAN_APPLICATION": 3.2,
                    "TAX_RETURN": 2.8,
                    "BANK_STATEMENT": 2.5,
                    "PAY_STUB": 1.9,
                    "IDENTITY_DOCUMENT": 1.5
                },
                "accuracy_by_type": {
                    "LOAN_APPLICATION": 0.99,
                    "TAX_RETURN": 0.98,
                    "BANK_STATEMENT": 0.99,
                    "PAY_STUB": 0.97,
                    "IDENTITY_DOCUMENT": 0.95
                },
                "error_rates": {
                    "classification_errors": 0.01,
                    "extraction_errors": 0.02,
                    "storage_errors": 0.005,
                    "timeout_errors": 0.001
                },
                "hourly_throughput": [
                    {"hour": "00:00", "count": 35},
                    {"hour": "01:00", "count": 28},
                    {"hour": "02:00", "count": 15},
                    # ... more hourly data
                    {"hour": "23:00", "count": 42}
                ],
                "document_types": [
                    {
                        "type": "LOAN_APPLICATION",
                        "count": 300,
                        "avg_processing_time": 3.2,
                        "accuracy": 0.99,
                        "error_rate": 0.01,
                        "confidence_distribution": {
                            "high": 0.85,
                            "medium": 0.12,
                            "low": 0.03
                        }
                    },
                    # ... more document types
                ]
            }
            
            # Make request with authentication
            response = test_client.get("/status/stats", headers=mock_auth_headers)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check basic structure
            assert "total_processed" in data
            assert "successful" in data
            assert "failed" in data
            assert "avg_processing_time" in data
            assert "classification_accuracy" in data
            assert "documents_by_type" in data
            assert "processing_time_by_type" in data
            assert "accuracy_by_type" in data
            assert "error_rates" in data
            assert "hourly_throughput" in data
            assert "document_types" in data
            
            # Check detailed stats
            assert data["total_processed"] == 1000
            assert data["successful"] == 990
            assert data["failed"] == 10
            assert data["classification_accuracy"] == 0.99
            assert len(data["documents_by_type"]) == 5
            assert len(data["processing_time_by_type"]) == 5
            assert len(data["accuracy_by_type"]) == 5
            assert len(data["error_rates"]) == 4
            assert len(data["hourly_throughput"]) > 0
            assert len(data["document_types"]) > 0


# ============================================================================
# Test Document Status Tracking
# ============================================================================

def test_document_status_tracking(test_client, mock_auth_headers, mock_rabbitmq_client):
    """
    Test document status tracking functionality.
    
    This test verifies that the document service correctly tracks and reports
    the status of documents throughout the classification pipeline.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
        mock_rabbitmq_client: Mock RabbitMQ client
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Create test document IDs
        document_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        
        # Mock the DocumentService.get_document_status method
        with patch("src.services.document_service.DocumentService.get_document_status") as mock_get_status:
            # Configure mock to return document status
            mock_get_status.return_value = {
                "document_id": document_id,
                "application_id": application_id,
                "status": "PROCESSED",
                "stage": "CLASSIFICATION_COMPLETE",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "processing_time_ms": 250,
                "document_type": "LOAN_APPLICATION",
                "confidence": 0.95,
                "needs_review": False,
                "error": None,
                "history": [
                    {
                        "timestamp": (datetime.now() - timedelta(seconds=10)).isoformat(),
                        "stage": "RECEIVED",
                        "status": "PENDING",
                        "details": "Document received for processing"
                    },
                    {
                        "timestamp": (datetime.now() - timedelta(seconds=8)).isoformat(),
                        "stage": "VALIDATION",
                        "status": "PROCESSING",
                        "details": "Validating document format"
                    },
                    {
                        "timestamp": (datetime.now() - timedelta(seconds=5)).isoformat(),
                        "stage": "CLASSIFICATION",
                        "status": "PROCESSING",
                        "details": "Classifying document type"
                    },
                    {
                        "timestamp": datetime.now().isoformat(),
                        "stage": "CLASSIFICATION_COMPLETE",
                        "status": "PROCESSED",
                        "details": "Document classified as LOAN_APPLICATION with 95% confidence"
                    }
                ]
            }
            
            # Make request to get document status
            response = test_client.get(f"/documents/{document_id}/status", headers=mock_auth_headers)
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check basic structure
            assert "document_id" in data
            assert "application_id" in data
            assert "status" in data
            assert "stage" in data
            assert "created_at" in data
            assert "updated_at" in data
            assert "processing_time_ms" in data
            assert "document_type" in data
            assert "confidence" in data
            assert "needs_review" in data
            assert "history" in data
            
            # Check specific values
            assert data["document_id"] == document_id
            assert data["application_id"] == application_id
            assert data["status"] == "PROCESSED"
            assert data["stage"] == "CLASSIFICATION_COMPLETE"
            assert data["document_type"] == "LOAN_APPLICATION"
            assert data["confidence"] == 0.95
            assert data["needs_review"] is False
            assert len(data["history"]) == 4


def test_batch_status_retrieval(test_client, mock_auth_headers):
    """
    Test batch status retrieval functionality.
    
    This test verifies that the document service correctly handles batch
    status retrieval for multiple documents.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Create test document IDs
        document_ids = [str(uuid.uuid4()) for _ in range(3)]
        application_id = str(uuid.uuid4())
        
        # Mock the DocumentService.get_documents_status method
        with patch("src.services.document_service.DocumentService.get_documents_status") as mock_get_status:
            # Configure mock to return batch status
            mock_get_status.return_value = {
                "documents": [
                    {
                        "document_id": document_ids[0],
                        "application_id": application_id,
                        "status": "PROCESSED",
                        "stage": "CLASSIFICATION_COMPLETE",
                        "document_type": "LOAN_APPLICATION",
                        "confidence": 0.95,
                        "processing_time_ms": 250,
                        "updated_at": datetime.now().isoformat()
                    },
                    {
                        "document_id": document_ids[1],
                        "application_id": application_id,
                        "status": "PROCESSED",
                        "stage": "CLASSIFICATION_COMPLETE",
                        "document_type": "BANK_STATEMENT",
                        "confidence": 0.98,
                        "processing_time_ms": 180,
                        "updated_at": datetime.now().isoformat()
                    },
                    {
                        "document_id": document_ids[2],
                        "application_id": application_id,
                        "status": "FAILED",
                        "stage": "CLASSIFICATION",
                        "document_type": None,
                        "confidence": None,
                        "processing_time_ms": 320,
                        "updated_at": datetime.now().isoformat(),
                        "error": {
                            "code": "CLASSIFICATION_ERROR",
                            "message": "Failed to classify document",
                            "details": "Document format not supported"
                        }
                    }
                ],
                "total": 3,
                "successful": 2,
                "failed": 1,
                "pending": 0,
                "processing": 0
            }
            
            # Make request to get batch status by application ID
            response = test_client.get(
                f"/documents/status", 
                params={"application_id": application_id},
                headers=mock_auth_headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check basic structure
            assert "documents" in data
            assert "total" in data
            assert "successful" in data
            assert "failed" in data
            assert "pending" in data
            assert "processing" in data
            
            # Check specific values
            assert data["total"] == 3
            assert data["successful"] == 2
            assert data["failed"] == 1
            assert data["pending"] == 0
            assert data["processing"] == 0
            assert len(data["documents"]) == 3
            
            # Check document details
            for doc in data["documents"]:
                assert "document_id" in doc
                assert "application_id" in doc
                assert "status" in doc
                assert "stage" in doc
                assert "updated_at" in doc
                
                # Check that document_id is in our list
                assert doc["document_id"] in document_ids
                assert doc["application_id"] == application_id
            
            # Make request to get batch status by document IDs
            response = test_client.post(
                f"/documents/status/batch",
                json={"document_ids": document_ids},
                headers=mock_auth_headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check that we got the same structure
            assert "documents" in data
            assert "total" in data
            assert len(data["documents"]) == 3


def test_status_webhook_notification(test_client, mock_auth_headers, mock_rabbitmq_client):
    """
    Test status webhook notification functionality.
    
    This test verifies that the document service correctly sends status
    update notifications to the notification service via RabbitMQ.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
        mock_rabbitmq_client: Mock RabbitMQ client
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Create test document ID
        document_id = str(uuid.uuid4())
        application_id = str(uuid.uuid4())
        
        # Mock the DocumentService.update_document_status method
        with patch("src.services.document_service.DocumentService.update_document_status") as mock_update_status:
            # Configure mock to return updated status
            mock_update_status.return_value = {
                "document_id": document_id,
                "application_id": application_id,
                "status": "PROCESSED",
                "stage": "CLASSIFICATION_COMPLETE",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "processing_time_ms": 250,
                "document_type": "LOAN_APPLICATION",
                "confidence": 0.95,
                "needs_review": False,
                "error": None
            }
            
            # Make request to update document status
            response = test_client.put(
                f"/documents/{document_id}/status",
                json={
                    "status": "PROCESSED",
                    "stage": "CLASSIFICATION_COMPLETE",
                    "document_type": "LOAN_APPLICATION",
                    "confidence": 0.95,
                    "processing_time_ms": 250,
                    "needs_review": False
                },
                headers=mock_auth_headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check that status was updated
            assert data["status"] == "PROCESSED"
            assert data["stage"] == "CLASSIFICATION_COMPLETE"
            
            # Verify that notification was sent to RabbitMQ
            assert mock_rabbitmq_client.publish_message.called
            
            # Get the message that was published
            call_args = mock_rabbitmq_client.publish_message.call_args
            message = call_args[0][0]  # First positional argument
            
            # Check message structure if it's a dict
            if isinstance(message, dict):
                assert "event_type" in message
                assert "document_id" in message
                assert "application_id" in message
                assert "status" in message
                assert "timestamp" in message
                
                # Check specific values
                assert message["event_type"] == "document_status_updated"
                assert message["document_id"] == document_id
                assert message["application_id"] == application_id
                assert message["status"] == "PROCESSED"


def test_status_history_and_audit_trail(test_client, mock_auth_headers):
    """
    Test status history and audit trail functionality.
    
    This test verifies that the document service correctly maintains and
    reports status history for audit purposes.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Create test document ID
        document_id = str(uuid.uuid4())
        
        # Mock the DocumentService.get_document_status_history method
        with patch("src.services.document_service.DocumentService.get_document_status_history") as mock_get_history:
            # Configure mock to return status history
            now = datetime.now()
            mock_get_history.return_value = {
                "document_id": document_id,
                "history": [
                    {
                        "timestamp": (now - timedelta(minutes=30)).isoformat(),
                        "stage": "RECEIVED",
                        "status": "PENDING",
                        "details": "Document received for processing",
                        "user_id": None,
                        "system_event": True
                    },
                    {
                        "timestamp": (now - timedelta(minutes=29)).isoformat(),
                        "stage": "VALIDATION",
                        "status": "PROCESSING",
                        "details": "Validating document format",
                        "user_id": None,
                        "system_event": True
                    },
                    {
                        "timestamp": (now - timedelta(minutes=28)).isoformat(),
                        "stage": "CLASSIFICATION",
                        "status": "PROCESSING",
                        "details": "Classifying document type",
                        "user_id": None,
                        "system_event": True
                    },
                    {
                        "timestamp": (now - timedelta(minutes=27)).isoformat(),
                        "stage": "CLASSIFICATION_COMPLETE",
                        "status": "PROCESSED",
                        "details": "Document classified as LOAN_APPLICATION with 95% confidence",
                        "user_id": None,
                        "system_event": True
                    },
                    {
                        "timestamp": (now - timedelta(minutes=20)).isoformat(),
                        "stage": "MANUAL_REVIEW",
                        "status": "PROCESSING",
                        "details": "Document flagged for manual review due to low confidence",
                        "user_id": "user-123",
                        "system_event": False
                    },
                    {
                        "timestamp": (now - timedelta(minutes=15)).isoformat(),
                        "stage": "MANUAL_REVIEW_COMPLETE",
                        "status": "PROCESSED",
                        "details": "Manual review completed, document type confirmed as LOAN_APPLICATION",
                        "user_id": "user-123",
                        "system_event": False
                    }
                ],
                "total_events": 6,
                "system_events": 4,
                "user_events": 2,
                "first_event": (now - timedelta(minutes=30)).isoformat(),
                "last_event": (now - timedelta(minutes=15)).isoformat(),
                "processing_duration_seconds": 900  # 15 minutes
            }
            
            # Make request to get status history
            response = test_client.get(
                f"/documents/{document_id}/status/history",
                headers=mock_auth_headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check basic structure
            assert "document_id" in data
            assert "history" in data
            assert "total_events" in data
            assert "system_events" in data
            assert "user_events" in data
            assert "first_event" in data
            assert "last_event" in data
            assert "processing_duration_seconds" in data
            
            # Check specific values
            assert data["document_id"] == document_id
            assert data["total_events"] == 6
            assert data["system_events"] == 4
            assert data["user_events"] == 2
            assert len(data["history"]) == 6
            
            # Check history entries
            for entry in data["history"]:
                assert "timestamp" in entry
                assert "stage" in entry
                assert "status" in entry
                assert "details" in entry
                assert "user_id" in entry
                assert "system_event" in entry


def test_processing_metrics_reporting(test_client, mock_auth_headers):
    """
    Test processing metrics reporting functionality.
    
    This test verifies that the document service correctly reports processing
    metrics including time and error rates.
    
    Args:
        test_client: FastAPI test client
        mock_auth_headers: Mock authentication headers
    """
    # Mock the validate_jwt_token function
    with patch("src.utils.validation_utils.validate_jwt_token") as mock_validate:
        # Configure mock to return a valid token payload with required roles
        mock_validate.return_value = {
            "sub": "test-user",
            "roles": ["operations_staff"],
            "exp": datetime.now().timestamp() + 3600
        }
        
        # Mock the DocumentService.get_processing_metrics method
        with patch("src.services.document_service.DocumentService.get_processing_metrics") as mock_get_metrics:
            # Configure mock to return processing metrics
            now = datetime.now()
            start_time = now - timedelta(days=7)  # Last 7 days
            mock_get_metrics.return_value = {
                "time_period": {
                    "start": start_time.isoformat(),
                    "end": now.isoformat(),
                    "duration_days": 7
                },
                "total_documents": 5000,
                "documents_per_day": [
                    {"date": (start_time + timedelta(days=i)).strftime("%Y-%m-%d"), "count": random.randint(600, 800)}
                    for i in range(7)
                ],
                "avg_processing_time_ms": 245,
                "processing_time_percentiles": {
                    "p50": 220,
                    "p90": 350,
                    "p95": 450,
                    "p99": 750
                },
                "error_rates": {
                    "overall": 0.02,
                    "by_type": {
                        "CLASSIFICATION_ERROR": 0.01,
                        "EXTRACTION_ERROR": 0.005,
                        "VALIDATION_ERROR": 0.003,
                        "STORAGE_ERROR": 0.002
                    },
                    "by_document_type": {
                        "LOAN_APPLICATION": 0.015,
                        "TAX_RETURN": 0.025,
                        "BANK_STATEMENT": 0.018,
                        "PAY_STUB": 0.022,
                        "IDENTITY_DOCUMENT": 0.03
                    }
                },
                "accuracy": {
                    "overall": 0.98,
                    "by_document_type": {
                        "LOAN_APPLICATION": 0.985,
                        "TAX_RETURN": 0.975,
                        "BANK_STATEMENT": 0.982,
                        "PAY_STUB": 0.978,
                        "IDENTITY_DOCUMENT": 0.97
                    }
                },
                "processing_stages": {
                    "validation": {
                        "avg_time_ms": 50,
                        "error_rate": 0.005
                    },
                    "classification": {
                        "avg_time_ms": 150,
                        "error_rate": 0.01
                    },
                    "extraction": {
                        "avg_time_ms": 200,
                        "error_rate": 0.015
                    },
                    "storage": {
                        "avg_time_ms": 45,
                        "error_rate": 0.002
                    }
                }
            }
            
            # Make request to get processing metrics
            response = test_client.get(
                "/documents/metrics",
                params={"days": 7},
                headers=mock_auth_headers
            )
            
            # Verify response
            assert response.status_code == 200
            data = response.json()
            
            # Check basic structure
            assert "time_period" in data
            assert "total_documents" in data
            assert "documents_per_day" in data
            assert "avg_processing_time_ms" in data
            assert "processing_time_percentiles" in data
            assert "error_rates" in data
            assert "accuracy" in data
            assert "processing_stages" in data
            
            # Check specific values
            assert data["total_documents"] == 5000
            assert data["avg_processing_time_ms"] == 245
            assert len(data["documents_per_day"]) == 7
            assert data["error_rates"]["overall"] == 0.02
            assert data["accuracy"]["overall"] == 0.98
            
            # Check processing stages
            for stage in ["validation", "classification", "extraction", "storage"]:
                assert stage in data["processing_stages"]
                assert "avg_time_ms" in data["processing_stages"][stage]
                assert "error_rate" in data["processing_stages"][stage]