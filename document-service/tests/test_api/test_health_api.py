import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import status
from fastapi.testclient import TestClient
from pika.exceptions import AMQPConnectionError
from botocore.exceptions import ClientError


@pytest.fixture
def health_response_schema():
    """Schema for validating health check responses."""
    return {
        "status": str,
        "timestamp": str,
        "service": str,
        "details": dict
    }


@pytest.fixture
def readiness_response_schema():
    """Schema for validating readiness check responses."""
    return {
        "status": str,
        "timestamp": str,
        "service": str,
        "dependencies": {
            "rabbitmq": {
                "status": str,
                "details": dict
            },
            "s3": {
                "status": str,
                "details": dict
            }
        }
    }


@pytest.fixture
def detailed_health_response_schema():
    """Schema for validating detailed health check responses."""
    return {
        "status": str,
        "timestamp": str,
        "service": dict,
        "dependencies": {
            "rabbitmq": {
                "status": str,
                "details": dict
            },
            "s3": {
                "status": str,
                "details": dict
            }
        },
        "details": dict
    }


class TestHealthAPI:
    """Test suite for Document Service health check API endpoints."""

    def test_liveness_probe(self, client, validate_response_schema, health_response_schema):
        """Test that the liveness probe endpoint returns a successful response."""
        # Make request to liveness endpoint
        response = client.get("/health/liveness")
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, health_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "UP"
        assert data["service"] == "document-service"
        assert "timestamp" in data
        assert "message" in data["details"]
    
    def test_readiness_probe_success(self, client, validate_response_schema, readiness_response_schema, 
                                    mock_queue_service, mock_storage_service):
        """Test that the readiness probe endpoint returns a successful response when all dependencies are available."""
        # Configure mocks to indicate successful connections
        mock_queue_service.check_connection = MagicMock(return_value=True)
        mock_storage_service.check_connection = MagicMock(return_value=True)
        
        # Make request to readiness endpoint
        response = client.get("/health/readiness")
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, readiness_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "UP"
        assert data["service"] == "document-service"
        assert "timestamp" in data
        assert data["dependencies"]["rabbitmq"]["status"] == "UP"
        assert data["dependencies"]["s3"]["status"] == "UP"
        assert "connected" in data["dependencies"]["rabbitmq"]["details"]
        assert "connected" in data["dependencies"]["s3"]["details"]
        assert data["dependencies"]["rabbitmq"]["details"]["connected"] is True
        assert data["dependencies"]["s3"]["details"]["connected"] is True
    
    def test_readiness_probe_rabbitmq_failure(self, client, validate_response_schema, readiness_response_schema,
                                             mock_queue_service, mock_storage_service):
        """Test that the readiness probe endpoint returns a failure response when RabbitMQ is unavailable."""
        # Configure mocks to indicate RabbitMQ connection failure
        mock_queue_service.check_connection = MagicMock(side_effect=AMQPConnectionError("Connection refused"))
        mock_storage_service.check_connection = MagicMock(return_value=True)
        
        # Make request to readiness endpoint
        response = client.get("/health/readiness")
        
        # Verify response status code indicates service unavailable
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, readiness_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "DOWN"
        assert data["service"] == "document-service"
        assert "timestamp" in data
        assert data["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert data["dependencies"]["s3"]["status"] == "UP"
        assert "connected" in data["dependencies"]["rabbitmq"]["details"]
        assert "connected" in data["dependencies"]["s3"]["details"]
        assert data["dependencies"]["rabbitmq"]["details"]["connected"] is False
        assert data["dependencies"]["s3"]["details"]["connected"] is True
        assert "message" in data["dependencies"]["rabbitmq"]["details"]
        assert "Connection refused" in data["dependencies"]["rabbitmq"]["details"]["message"]
    
    def test_readiness_probe_s3_failure(self, client, validate_response_schema, readiness_response_schema,
                                      mock_queue_service, mock_storage_service):
        """Test that the readiness probe endpoint returns a failure response when S3 storage is unavailable."""
        # Configure mocks to indicate S3 connection failure
        mock_queue_service.check_connection = MagicMock(return_value=True)
        mock_storage_service.check_connection = MagicMock(side_effect=ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
            "HeadBucket"
        ))
        
        # Make request to readiness endpoint
        response = client.get("/health/readiness")
        
        # Verify response status code indicates service unavailable
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, readiness_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "DOWN"
        assert data["service"] == "document-service"
        assert "timestamp" in data
        assert data["dependencies"]["rabbitmq"]["status"] == "UP"
        assert data["dependencies"]["s3"]["status"] == "DOWN"
        assert "connected" in data["dependencies"]["rabbitmq"]["details"]
        assert "connected" in data["dependencies"]["s3"]["details"]
        assert data["dependencies"]["rabbitmq"]["details"]["connected"] is True
        assert data["dependencies"]["s3"]["details"]["connected"] is False
        assert "message" in data["dependencies"]["s3"]["details"]
        assert "The specified bucket does not exist" in data["dependencies"]["s3"]["details"]["message"]
    
    def test_readiness_probe_all_dependencies_failure(self, client, validate_response_schema, readiness_response_schema,
                                                   mock_queue_service, mock_storage_service):
        """Test that the readiness probe endpoint returns a failure response when all dependencies are unavailable."""
        # Configure mocks to indicate all connections failing
        mock_queue_service.check_connection = MagicMock(side_effect=AMQPConnectionError("Connection refused"))
        mock_storage_service.check_connection = MagicMock(side_effect=ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
            "HeadBucket"
        ))
        
        # Make request to readiness endpoint
        response = client.get("/health/readiness")
        
        # Verify response status code indicates service unavailable
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, readiness_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "DOWN"
        assert data["service"] == "document-service"
        assert "timestamp" in data
        assert data["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert data["dependencies"]["s3"]["status"] == "DOWN"
        assert "connected" in data["dependencies"]["rabbitmq"]["details"]
        assert "connected" in data["dependencies"]["s3"]["details"]
        assert data["dependencies"]["rabbitmq"]["details"]["connected"] is False
        assert data["dependencies"]["s3"]["details"]["connected"] is False
        assert "message" in data["dependencies"]["rabbitmq"]["details"]
        assert "message" in data["dependencies"]["s3"]["details"]
        assert "Connection refused" in data["dependencies"]["rabbitmq"]["details"]["message"]
        assert "The specified bucket does not exist" in data["dependencies"]["s3"]["details"]["message"]
    
    def test_detailed_health_check_success(self, client, validate_response_schema, detailed_health_response_schema,
                                         mock_queue_service, mock_storage_service):
        """Test that the detailed health check endpoint returns a successful response with all required information."""
        # Configure mocks to indicate successful connections
        mock_queue_service.check_connection = MagicMock(return_value=True)
        mock_storage_service.check_connection = MagicMock(return_value=True)
        
        # Make request to health check endpoint
        response = client.get("/health")
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, detailed_health_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "UP"
        assert "timestamp" in data
        
        # Verify service information
        assert "name" in data["service"]
        assert "version" in data["service"]
        assert "description" in data["service"]
        assert data["service"]["name"] == "document-service"
        
        # Verify dependencies
        assert data["dependencies"]["rabbitmq"]["status"] == "UP"
        assert data["dependencies"]["s3"]["status"] == "UP"
        assert data["dependencies"]["rabbitmq"]["details"]["connected"] is True
        assert data["dependencies"]["s3"]["details"]["connected"] is True
        
        # Verify details section
        assert "uptime" in data["details"]
        assert "memory_usage" in data["details"]
        assert "cpu_usage" in data["details"]
    
    def test_detailed_health_check_failure(self, client, validate_response_schema, detailed_health_response_schema,
                                         mock_queue_service, mock_storage_service):
        """Test that the detailed health check endpoint returns a failure response when dependencies are unavailable."""
        # Configure mocks to indicate dependency failures
        mock_queue_service.check_connection = MagicMock(return_value=False)
        mock_storage_service.check_connection = MagicMock(side_effect=ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The specified bucket does not exist"}},
            "HeadBucket"
        ))
        
        # Make request to health check endpoint
        response = client.get("/health")
        
        # Verify response status code indicates service unavailable
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, detailed_health_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify response content
        assert data["status"] == "DOWN"
        assert "timestamp" in data
        
        # Verify service information
        assert "name" in data["service"]
        assert "version" in data["service"]
        assert "description" in data["service"]
        assert data["service"]["name"] == "document-service"
        
        # Verify dependencies
        assert data["dependencies"]["rabbitmq"]["status"] == "DOWN"
        assert data["dependencies"]["s3"]["status"] == "DOWN"
        assert data["dependencies"]["rabbitmq"]["details"]["connected"] is False
        assert data["dependencies"]["s3"]["details"]["connected"] is False
        
        # Verify details section
        assert "uptime" in data["details"]
        assert "memory_usage" in data["details"]
        assert "cpu_usage" in data["details"]
    
    def test_health_endpoints_no_auth_required(self, client):
        """Test that health check endpoints are accessible without authentication."""
        # Make requests to all health endpoints without auth headers
        liveness_response = client.get("/health/liveness")
        readiness_response = client.get("/health/readiness")
        health_response = client.get("/health")
        
        # Verify that all endpoints return a response (not 401 Unauthorized)
        assert liveness_response.status_code != status.HTTP_401_UNAUTHORIZED
        assert readiness_response.status_code != status.HTTP_401_UNAUTHORIZED
        assert health_response.status_code != status.HTTP_401_UNAUTHORIZED
        
        # Verify that liveness endpoint always returns 200 OK
        assert liveness_response.status_code == status.HTTP_200_OK
    
    @patch('src.api.health.get_current_timestamp')
    def test_timestamp_format(self, mock_timestamp, client):
        """Test that the timestamp in health check responses is properly formatted."""
        # Mock the timestamp function to return a fixed value
        mock_timestamp.return_value = "2023-04-15T14:30:45.123456Z"
        
        # Make request to liveness endpoint
        response = client.get("/health/liveness")
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Verify timestamp format
        assert data["timestamp"] == "2023-04-15T14:30:45.123456Z"
    
    def test_resource_utilization_reporting(self, client, validate_response_schema, detailed_health_response_schema):
        """Test that the health check endpoint reports resource utilization metrics."""
        # Make request to health check endpoint
        response = client.get("/health")
        
        # Verify response status code
        assert response.status_code == status.HTTP_200_OK
        
        # Parse response data
        data = response.json()
        
        # Validate response schema
        is_valid, errors = validate_response_schema(data, detailed_health_response_schema)
        assert is_valid, f"Response schema validation failed: {errors}"
        
        # Verify resource utilization metrics are present
        assert "memory_usage" in data["details"]
        assert "cpu_usage" in data["details"]
        assert "uptime" in data["details"]
        
        # Note: We're not testing the actual values since they're marked as "Not implemented" in the health.py file
        # In a real implementation, we would mock the resource utilization functions and test their values