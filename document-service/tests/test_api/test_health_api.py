import pytest
import json
from unittest.mock import patch, MagicMock

from fastapi import status
from fastapi.testclient import TestClient

# Import the health router for direct testing
from src.api.health import health_router, get_queue_service, get_storage_service


@pytest.fixture
def app_with_mocked_dependencies(test_app, mock_rabbitmq_client, mock_s3_storage):
    """
    Creates a test application with mocked dependencies for health check testing.
    
    Args:
        test_app: The FastAPI test application fixture
        mock_rabbitmq_client: The mock RabbitMQ client fixture
        mock_s3_storage: The mock S3 storage fixture
        
    Returns:
        TestClient: A test client with mocked dependencies
    """
    # Create a test client
    client = TestClient(test_app)
    
    # Patch the dependency injection functions
    with patch('src.api.health.get_queue_service', return_value=mock_rabbitmq_client), \
         patch('src.api.health.get_storage_service', return_value=mock_s3_storage):
        yield client


class TestHealthAPI:
    """
    Tests for the Document Service health check API endpoints.
    
    These tests verify that the API correctly reports service health status,
    dependencies availability (S3 storage, RabbitMQ), and resource utilization.
    """
    
    def test_liveness_probe(self, test_client):
        """
        Test that the liveness probe endpoint returns a 200 status code and the correct response format.
        
        The liveness probe should always return a 200 status code if the service is running,
        regardless of the status of dependencies.
        """
        # Make a request to the liveness probe endpoint
        response = test_client.get("/health/liveness")
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the response format
        assert "status" in response_data
        assert "version" in response_data
        assert "details" in response_data
        
        # Verify the status is UP
        assert response_data["status"] == "UP"
        
        # Verify the details contain the service name
        assert "service" in response_data["details"]
        assert response_data["details"]["service"] == "document-service"
    
    def test_readiness_probe_all_dependencies_available(self, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the readiness probe endpoint returns a 200 status code when all dependencies are available.
        
        The readiness probe should return a 200 status code when all dependencies (RabbitMQ, S3) are available.
        """
        # Configure mocks to indicate that dependencies are available
        mock_rabbitmq_client.is_connected = MagicMock(return_value=True)
        mock_s3_storage.check_connection = MagicMock(return_value=True)
        mock_s3_storage.get_bucket_name = MagicMock(return_value="mca-documents-test")
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the response format
        assert "status" in response_data
        assert "version" in response_data
        assert "details" in response_data
        
        # Verify the status is UP
        assert response_data["status"] == "UP"
        
        # Verify the details contain dependency information
        assert "dependencies" in response_data["details"]
        assert "rabbitmq" in response_data["details"]["dependencies"]
        assert "s3" in response_data["details"]["dependencies"]
        
        # Verify RabbitMQ status is UP
        assert response_data["details"]["dependencies"]["rabbitmq"]["status"] == "UP"
        assert "details" in response_data["details"]["dependencies"]["rabbitmq"]
        assert "connection" in response_data["details"]["dependencies"]["rabbitmq"]["details"]
        assert response_data["details"]["dependencies"]["rabbitmq"]["details"]["connection"] == "established"
        
        # Verify S3 status is UP
        assert response_data["details"]["dependencies"]["s3"]["status"] == "UP"
        assert "details" in response_data["details"]["dependencies"]["s3"]
        assert "connection" in response_data["details"]["dependencies"]["s3"]["details"]
        assert response_data["details"]["dependencies"]["s3"]["details"]["connection"] == "established"
        assert "bucket" in response_data["details"]["dependencies"]["s3"]["details"]
        assert response_data["details"]["dependencies"]["s3"]["details"]["bucket"] == "mca-documents-test"
    
    def test_readiness_probe_rabbitmq_unavailable(self, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the readiness probe endpoint returns a 503 status code when RabbitMQ is unavailable.
        
        The readiness probe should return a 503 status code when RabbitMQ is unavailable,
        even if S3 is available.
        """
        # Configure mocks to indicate that RabbitMQ is unavailable but S3 is available
        mock_rabbitmq_client.is_connected = MagicMock(return_value=False)
        mock_s3_storage.check_connection = MagicMock(return_value=True)
        mock_s3_storage.get_bucket_name = MagicMock(return_value="mca-documents-test")
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the status is DOWN
        assert response_data["status"] == "DOWN"
        
        # Verify the details contain dependency information
        assert "dependencies" in response_data["details"]
        assert "rabbitmq" in response_data["details"]["dependencies"]
        assert "s3" in response_data["details"]["dependencies"]
        
        # Verify RabbitMQ status is DOWN
        assert response_data["details"]["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert "details" in response_data["details"]["dependencies"]["rabbitmq"]
        assert "error" in response_data["details"]["dependencies"]["rabbitmq"]["details"]
        
        # Verify S3 status is UP
        assert response_data["details"]["dependencies"]["s3"]["status"] == "UP"
    
    def test_readiness_probe_s3_unavailable(self, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the readiness probe endpoint returns a 503 status code when S3 is unavailable.
        
        The readiness probe should return a 503 status code when S3 is unavailable,
        even if RabbitMQ is available.
        """
        # Configure mocks to indicate that S3 is unavailable but RabbitMQ is available
        mock_rabbitmq_client.is_connected = MagicMock(return_value=True)
        mock_s3_storage.check_connection = MagicMock(return_value=False)
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the status is DOWN
        assert response_data["status"] == "DOWN"
        
        # Verify the details contain dependency information
        assert "dependencies" in response_data["details"]
        assert "rabbitmq" in response_data["details"]["dependencies"]
        assert "s3" in response_data["details"]["dependencies"]
        
        # Verify RabbitMQ status is UP
        assert response_data["details"]["dependencies"]["rabbitmq"]["status"] == "UP"
        
        # Verify S3 status is DOWN
        assert response_data["details"]["dependencies"]["s3"]["status"] == "DOWN"
        assert "details" in response_data["details"]["dependencies"]["s3"]
        assert "error" in response_data["details"]["dependencies"]["s3"]["details"]
    
    def test_readiness_probe_all_dependencies_unavailable(self, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the readiness probe endpoint returns a 503 status code when all dependencies are unavailable.
        
        The readiness probe should return a 503 status code when both RabbitMQ and S3 are unavailable.
        """
        # Configure mocks to indicate that both dependencies are unavailable
        mock_rabbitmq_client.is_connected = MagicMock(return_value=False)
        mock_s3_storage.check_connection = MagicMock(return_value=False)
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the status is DOWN
        assert response_data["status"] == "DOWN"
        
        # Verify the details contain dependency information
        assert "dependencies" in response_data["details"]
        assert "rabbitmq" in response_data["details"]["dependencies"]
        assert "s3" in response_data["details"]["dependencies"]
        
        # Verify RabbitMQ status is DOWN
        assert response_data["details"]["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert "details" in response_data["details"]["dependencies"]["rabbitmq"]
        assert "error" in response_data["details"]["dependencies"]["rabbitmq"]["details"]
        
        # Verify S3 status is DOWN
        assert response_data["details"]["dependencies"]["s3"]["status"] == "DOWN"
        assert "details" in response_data["details"]["dependencies"]["s3"]
        assert "error" in response_data["details"]["dependencies"]["s3"]["details"]
    
    def test_rabbitmq_connection_error(self, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the readiness probe handles RabbitMQ connection errors gracefully.
        
        The readiness probe should handle exceptions thrown by the RabbitMQ client
        and include error details in the response.
        """
        # Configure mocks to throw an exception when checking RabbitMQ connection
        mock_rabbitmq_client.is_connected = MagicMock(side_effect=Exception("Connection refused"))
        mock_s3_storage.check_connection = MagicMock(return_value=True)
        mock_s3_storage.get_bucket_name = MagicMock(return_value="mca-documents-test")
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the status is DOWN
        assert response_data["status"] == "DOWN"
        
        # Verify the details contain dependency information
        assert "dependencies" in response_data["details"]
        assert "rabbitmq" in response_data["details"]["dependencies"]
        
        # Verify RabbitMQ status is DOWN with error details
        assert response_data["details"]["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert "details" in response_data["details"]["dependencies"]["rabbitmq"]
        assert "error" in response_data["details"]["dependencies"]["rabbitmq"]["details"]
        assert "Connection refused" in response_data["details"]["dependencies"]["rabbitmq"]["details"]["error"]
    
    def test_s3_connection_error(self, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the readiness probe handles S3 connection errors gracefully.
        
        The readiness probe should handle exceptions thrown by the S3 storage client
        and include error details in the response.
        """
        # Configure mocks to throw an exception when checking S3 connection
        mock_rabbitmq_client.is_connected = MagicMock(return_value=True)
        mock_s3_storage.check_connection = MagicMock(side_effect=Exception("Access denied"))
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the status is DOWN
        assert response_data["status"] == "DOWN"
        
        # Verify the details contain dependency information
        assert "dependencies" in response_data["details"]
        assert "s3" in response_data["details"]["dependencies"]
        
        # Verify S3 status is DOWN with error details
        assert response_data["details"]["dependencies"]["s3"]["status"] == "DOWN"
        assert "details" in response_data["details"]["dependencies"]["s3"]
        assert "error" in response_data["details"]["dependencies"]["s3"]["details"]
        assert "Access denied" in response_data["details"]["dependencies"]["s3"]["details"]["error"]
    
    @patch('src.api.health.HealthStatus')
    def test_health_status_includes_resource_utilization(self, mock_health_status, app_with_mocked_dependencies, mock_rabbitmq_client, mock_s3_storage):
        """
        Test that the health status includes resource utilization metrics.
        
        The health status should include metrics for CPU, memory, and disk usage.
        """
        # Configure mocks to indicate that dependencies are available
        mock_rabbitmq_client.is_connected = MagicMock(return_value=True)
        mock_s3_storage.check_connection = MagicMock(return_value=True)
        mock_s3_storage.get_bucket_name = MagicMock(return_value="mca-documents-test")
        
        # Configure the mock HealthStatus to include resource utilization metrics
        mock_health_status.return_value = {
            "status": "UP",
            "version": "1.0.0",
            "details": {
                "service": "document-service",
                "dependencies": {
                    "rabbitmq": {
                        "status": "UP",
                        "details": {
                            "connection": "established",
                            "exchange": "mca.documents",
                            "queue": "document-processing"
                        }
                    },
                    "s3": {
                        "status": "UP",
                        "details": {
                            "connection": "established",
                            "bucket": "mca-documents-test"
                        }
                    }
                },
                "resources": {
                    "cpu": {
                        "usage_percent": 25.5,
                        "cores": 4
                    },
                    "memory": {
                        "usage_percent": 60.2,
                        "total_mb": 8192,
                        "used_mb": 4931.6
                    },
                    "disk": {
                        "usage_percent": 45.8,
                        "total_gb": 100,
                        "used_gb": 45.8
                    }
                }
            }
        }
        
        # Make a request to the readiness probe endpoint
        response = app_with_mocked_dependencies.get("/health/readiness")
        
        # Verify the response
        assert response.status_code == status.HTTP_200_OK
        
        # Parse the response body
        response_data = response.json()
        
        # Verify the response includes resource utilization metrics
        assert "resources" in response_data["details"]
        assert "cpu" in response_data["details"]["resources"]
        assert "memory" in response_data["details"]["resources"]
        assert "disk" in response_data["details"]["resources"]
        
        # Verify CPU metrics
        assert "usage_percent" in response_data["details"]["resources"]["cpu"]
        assert "cores" in response_data["details"]["resources"]["cpu"]
        
        # Verify memory metrics
        assert "usage_percent" in response_data["details"]["resources"]["memory"]
        assert "total_mb" in response_data["details"]["resources"]["memory"]
        assert "used_mb" in response_data["details"]["resources"]["memory"]
        
        # Verify disk metrics
        assert "usage_percent" in response_data["details"]["resources"]["disk"]
        assert "total_gb" in response_data["details"]["resources"]["disk"]
        assert "used_gb" in response_data["details"]["resources"]["disk"]
    
    def test_health_endpoints_accessible_without_authentication(self, test_client):
        """
        Test that health endpoints are accessible without authentication.
        
        Health endpoints should be accessible without authentication to allow
        Kubernetes probes to check service health without credentials.
        """
        # Make requests to health endpoints without authentication headers
        liveness_response = test_client.get("/health/liveness")
        readiness_response = test_client.get("/health/readiness")
        
        # Verify that the endpoints are accessible (status code is not 401 Unauthorized)
        assert liveness_response.status_code != status.HTTP_401_UNAUTHORIZED
        assert readiness_response.status_code != status.HTTP_401_UNAUTHORIZED
        
        # Verify that the liveness endpoint returns a 200 status code
        assert liveness_response.status_code == status.HTTP_200_OK
        
        # Note: The readiness endpoint may return 503 if dependencies are unavailable,
        # but it should not return 401 Unauthorized