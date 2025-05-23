#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the status endpoints in the OCR Service API.

This module contains tests for the status endpoints that provide service status,
metrics, and OCR processing statistics. It verifies that the endpoints correctly
report service performance, accuracy metrics, and processing throughput for
monitoring systems like Datadog.
"""

import json
import pytest
from unittest.mock import patch, MagicMock
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, Counter, Gauge, Histogram

# Import the status router to test
from src.api.status import status_router, OCR_PROCESSING_TOTAL, OCR_ACCURACY, QUEUE_DEPTH


# Create a test FastAPI app with the status router
@pytest.fixture
def test_app():
    """Create a test FastAPI app with the status router."""
    app = FastAPI()
    app.include_router(status_router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test app."""
    return TestClient(test_app)


# Tests for the main status endpoint
class TestStatusEndpoint:
    """Tests for the /status endpoint."""

    def test_status_success(self, test_client):
        """Test that the status endpoint returns 200 OK with service status information."""
        # Mock the necessary services and utilities
        with patch("src.api.status.ocr_service.get_metrics", return_value={"accuracy": {"all": {"percentage": 99.0}}}):
            with patch("src.api.status.queue_service.get_queue_depths", return_value={"data-extraction": 5}):
                with patch("src.api.status.get_gpu_utilization", return_value={"0": {"utilization": 75.5, "memory_used": 4096}}):
                    # Make a request to the status endpoint
                    response = test_client.get("/")
                    
                    # Check the response
                    assert response.status_code == 200
                    data = response.json()
                    assert "service" in data
                    assert "version" in data
                    assert "environment" in data
                    assert "status" in data
                    assert "uptime_seconds" in data
                    assert "ocr_stats" in data
                    assert "queue_stats" in data
                    assert "resource_usage" in data
                    
                    # Check OCR stats
                    assert "processed_total" in data["ocr_stats"]
                    assert "average_accuracy" in data["ocr_stats"]
                    assert "average_processing_time" in data["ocr_stats"]
                    
                    # Check queue stats
                    assert "queue_depth" in data["queue_stats"]
                    assert "messages_processed" in data["queue_stats"]
                    
                    # Check resource usage
                    assert "cpu_percent" in data["resource_usage"]
                    assert "memory_bytes" in data["resource_usage"]
                    assert "gpu" in data["resource_usage"]
                    
                    # Verify the service is healthy
                    assert data["status"] == "healthy"
                    
                    # Verify OCR accuracy is at least 99% as specified in section 0.1.1
                    assert data["ocr_stats"]["average_accuracy"] >= 99.0

    def test_status_error_handling(self, test_client):
        """Test that the status endpoint handles errors appropriately."""
        # Mock an exception during the status check
        with patch("src.api.status.ocr_service.get_metrics", side_effect=Exception("Test error")):
            response = test_client.get("/")
            
            # Check the response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Error getting service status" in data["detail"]


# Tests for the health check endpoint
class TestHealthCheckEndpoint:
    """Tests for the /status/health endpoint."""

    def test_health_check_success(self, test_client):
        """Test that the health check endpoint returns 200 OK with healthy status."""
        # Make a request to the health check endpoint
        response = test_client.get("/health")
        
        # Check the response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# Tests for the metrics endpoint
class TestMetricsEndpoint:
    """Tests for the /status/metrics endpoint."""

    def test_metrics_success(self, test_client):
        """Test that the metrics endpoint returns 200 OK with Prometheus metrics."""
        # Mock the queue service
        with patch("src.api.status.queue_service.get_queue_depths", return_value={"data-extraction": 5}):
            # Make a request to the metrics endpoint
            response = test_client.get("/metrics")
            
            # Check the response
            assert response.status_code == 200
            assert response.headers["Content-Type"] == "application/openmetrics-text; version=1.0.0; charset=utf-8"
            
            # Check that the response contains Prometheus metrics
            content = response.content.decode("utf-8")
            assert "ocr_processing_total" in content
            assert "ocr_accuracy_percentage" in content
            assert "rabbitmq_queue_depth" in content
            assert "cpu_usage_percentage" in content
            assert "memory_usage_bytes" in content
            assert "gpu_usage_percentage" in content

    def test_metrics_queue_error_handling(self, test_client):
        """Test that the metrics endpoint handles queue service errors gracefully."""
        # Mock an exception in the queue service
        with patch("src.api.status.queue_service.get_queue_depths", side_effect=Exception("Test error")):
            # Make a request to the metrics endpoint
            response = test_client.get("/metrics")
            
            # Check that the response is still successful despite the error
            assert response.status_code == 200
            assert response.headers["Content-Type"] == "application/openmetrics-text; version=1.0.0; charset=utf-8"


# Tests for the OCR metrics endpoint
class TestOcrMetricsEndpoint:
    """Tests for the /status/metrics/ocr endpoint."""

    def test_ocr_metrics_success(self, test_client, auth_token):
        """Test that the OCR metrics endpoint returns 200 OK with OCR metrics."""
        # Mock the OCR service
        mock_ocr_metrics = {
            "accuracy": {
                "all": {"percentage": 99.0, "sample_size": 1000},
                "APPLICATION": {"percentage": 99.5, "sample_size": 500},
                "TAX_RETURN": {"percentage": 98.5, "sample_size": 300},
                "BANK_STATEMENT": {"percentage": 97.8, "sample_size": 200},
            },
            "processing_time": {
                "average": 1.5,
                "p50": 1.2,
                "p90": 2.5,
                "p99": 4.0,
            },
            "confidence_scores": {
                "average": 0.92,
                "by_field_type": {
                    "business_name": 0.98,
                    "tax_id": 0.95,
                    "address": 0.92,
                    "signature": 0.85,
                },
            },
            "throughput": {
                "documents_per_minute": 60,
                "pages_per_minute": 180,
            },
            "error_rate": {
                "percentage": 1.0,
                "by_document_type": {
                    "APPLICATION": 0.5,
                    "TAX_RETURN": 1.5,
                    "BANK_STATEMENT": 2.2,
                },
            },
        }
        
        with patch("src.api.status.ocr_service.get_metrics", return_value=mock_ocr_metrics):
            # Make a request to the OCR metrics endpoint with authentication
            response = test_client.get("/metrics/ocr", headers={"Authorization": f"Bearer {auth_token}"})
            
            # Check the response
            assert response.status_code == 200
            data = response.json()
            
            # Check that the response contains the expected OCR metrics
            assert "accuracy" in data
            assert "processing_time" in data
            assert "confidence_scores" in data
            assert "throughput" in data
            assert "error_rate" in data
            
            # Verify OCR accuracy is at least 99% as specified in section 0.1.1
            assert data["accuracy"]["all"]["percentage"] >= 99.0

    def test_ocr_metrics_unauthorized(self, test_client):
        """Test that the OCR metrics endpoint requires authentication."""
        # Make a request to the OCR metrics endpoint without authentication
        response = test_client.get("/metrics/ocr")
        
        # Check that the response requires authentication
        assert response.status_code == 401 or response.status_code == 403

    def test_ocr_metrics_error_handling(self, test_client, auth_token):
        """Test that the OCR metrics endpoint handles errors appropriately."""
        # Mock an exception in the OCR service
        with patch("src.api.status.ocr_service.get_metrics", side_effect=Exception("Test error")):
            # Make a request to the OCR metrics endpoint with authentication
            response = test_client.get("/metrics/ocr", headers={"Authorization": f"Bearer {auth_token}"})
            
            # Check the response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Error getting OCR metrics" in data["detail"]


# Tests for the queue metrics endpoint
class TestQueueMetricsEndpoint:
    """Tests for the /status/metrics/queue endpoint."""

    def test_queue_metrics_success(self, test_client, auth_token):
        """Test that the queue metrics endpoint returns 200 OK with queue metrics."""
        # Mock the queue service
        mock_queue_metrics = {
            "queue_depths": {
                "data-extraction": 5,
                "document-processing": 3,
                "notification": 2,
            },
            "processing_times": {
                "average": 0.5,
                "p50": 0.3,
                "p90": 0.8,
                "p99": 1.5,
            },
            "error_rates": {
                "percentage": 0.5,
                "by_queue": {
                    "data-extraction": 0.3,
                    "document-processing": 0.7,
                    "notification": 0.2,
                },
            },
            "throughput": {
                "messages_per_second": 10,
                "by_queue": {
                    "data-extraction": 5,
                    "document-processing": 3,
                    "notification": 2,
                },
            },
        }
        
        with patch("src.api.status.queue_service.get_metrics", return_value=mock_queue_metrics):
            # Make a request to the queue metrics endpoint with authentication
            response = test_client.get("/metrics/queue", headers={"Authorization": f"Bearer {auth_token}"})
            
            # Check the response
            assert response.status_code == 200
            data = response.json()
            
            # Check that the response contains the expected queue metrics
            assert "queue_depths" in data
            assert "processing_times" in data
            assert "error_rates" in data
            assert "throughput" in data
            
            # Verify queue depths are being tracked as specified in section 0.2.5
            assert "data-extraction" in data["queue_depths"]
            assert isinstance(data["queue_depths"]["data-extraction"], int)

    def test_queue_metrics_unauthorized(self, test_client):
        """Test that the queue metrics endpoint requires authentication."""
        # Make a request to the queue metrics endpoint without authentication
        response = test_client.get("/metrics/queue")
        
        # Check that the response requires authentication
        assert response.status_code == 401 or response.status_code == 403

    def test_queue_metrics_error_handling(self, test_client, auth_token):
        """Test that the queue metrics endpoint handles errors appropriately."""
        # Mock an exception in the queue service
        with patch("src.api.status.queue_service.get_metrics", side_effect=Exception("Test error")):
            # Make a request to the queue metrics endpoint with authentication
            response = test_client.get("/metrics/queue", headers={"Authorization": f"Bearer {auth_token}"})
            
            # Check the response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Error getting queue metrics" in data["detail"]


# Tests for the resource metrics endpoint
class TestResourceMetricsEndpoint:
    """Tests for the /status/metrics/resource endpoint."""

    def test_resource_metrics_success(self, test_client, auth_token):
        """Test that the resource metrics endpoint returns 200 OK with resource metrics."""
        # Mock the GPU utilization
        mock_gpu_stats = {
            "0": {
                "utilization": 75.5,
                "memory_used": 4096,
                "memory_total": 8192,
                "temperature": 65,
            }
        }
        
        with patch("src.api.status.get_gpu_utilization", return_value=mock_gpu_stats):
            # Make a request to the resource metrics endpoint with authentication
            response = test_client.get("/metrics/resource", headers={"Authorization": f"Bearer {auth_token}"})
            
            # Check the response
            assert response.status_code == 200
            data = response.json()
            
            # Check that the response contains the expected resource metrics
            assert "cpu" in data
            assert "memory" in data
            assert "gpu" in data
            
            # Check CPU metrics
            assert "usage_percent" in data["cpu"]
            assert "core_count" in data["cpu"]
            assert "load_average" in data["cpu"]
            
            # Check memory metrics
            assert "total_bytes" in data["memory"]
            assert "available_bytes" in data["memory"]
            assert "used_bytes" in data["memory"]
            assert "percent" in data["memory"]
            
            # Check GPU metrics
            assert "0" in data["gpu"]
            assert "utilization" in data["gpu"]["0"]
            assert "memory_used" in data["gpu"]["0"]
            assert "memory_total" in data["gpu"]["0"]
            assert "temperature" in data["gpu"]["0"]

    def test_resource_metrics_unauthorized(self, test_client):
        """Test that the resource metrics endpoint requires authentication."""
        # Make a request to the resource metrics endpoint without authentication
        response = test_client.get("/metrics/resource")
        
        # Check that the response requires authentication
        assert response.status_code == 401 or response.status_code == 403

    def test_resource_metrics_error_handling(self, test_client, auth_token):
        """Test that the resource metrics endpoint handles errors appropriately."""
        # Mock an exception during resource metrics collection
        with patch("src.api.status.psutil.cpu_percent", side_effect=Exception("Test error")):
            # Make a request to the resource metrics endpoint with authentication
            response = test_client.get("/metrics/resource", headers={"Authorization": f"Bearer {auth_token}"})
            
            # Check the response
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Error getting resource metrics" in data["detail"]


# Tests for the Prometheus metrics
class TestPrometheusMetrics:
    """Tests for the Prometheus metrics defined in the status module."""

    def test_ocr_processing_total_counter(self):
        """Test that the OCR_PROCESSING_TOTAL counter works correctly."""
        # Reset the counter
        OCR_PROCESSING_TOTAL._metrics.clear()
        
        # Increment the counter for different document types and statuses
        OCR_PROCESSING_TOTAL.labels(document_type="APPLICATION", status="COMPLETED").inc()
        OCR_PROCESSING_TOTAL.labels(document_type="TAX_RETURN", status="COMPLETED").inc(2)
        OCR_PROCESSING_TOTAL.labels(document_type="BANK_STATEMENT", status="FAILED").inc()
        
        # Check the counter values
        for sample in OCR_PROCESSING_TOTAL.collect()[0].samples:
            if sample.labels["document_type"] == "APPLICATION" and sample.labels["status"] == "COMPLETED":
                assert sample.value == 1
            elif sample.labels["document_type"] == "TAX_RETURN" and sample.labels["status"] == "COMPLETED":
                assert sample.value == 2
            elif sample.labels["document_type"] == "BANK_STATEMENT" and sample.labels["status"] == "FAILED":
                assert sample.value == 1

    def test_ocr_accuracy_gauge(self):
        """Test that the OCR_ACCURACY gauge works correctly."""
        # Reset the gauge
        OCR_ACCURACY._metrics.clear()
        
        # Set accuracy values for different document types
        OCR_ACCURACY.labels(document_type="all").set(99.0)
        OCR_ACCURACY.labels(document_type="APPLICATION").set(99.5)
        OCR_ACCURACY.labels(document_type="TAX_RETURN").set(98.5)
        
        # Check the gauge values
        for sample in OCR_ACCURACY.collect()[0].samples:
            if sample.labels["document_type"] == "all":
                assert sample.value == 99.0
            elif sample.labels["document_type"] == "APPLICATION":
                assert sample.value == 99.5
            elif sample.labels["document_type"] == "TAX_RETURN":
                assert sample.value == 98.5

    def test_queue_depth_gauge(self):
        """Test that the QUEUE_DEPTH gauge works correctly."""
        # Reset the gauge
        QUEUE_DEPTH._metrics.clear()
        
        # Set queue depth values for different queues
        QUEUE_DEPTH.labels(queue_name="data-extraction").set(5)
        QUEUE_DEPTH.labels(queue_name="document-processing").set(3)
        QUEUE_DEPTH.labels(queue_name="notification").set(2)
        
        # Check the gauge values
        for sample in QUEUE_DEPTH.collect()[0].samples:
            if sample.labels["queue_name"] == "data-extraction":
                assert sample.value == 5
            elif sample.labels["queue_name"] == "document-processing":
                assert sample.value == 3
            elif sample.labels["queue_name"] == "notification":
                assert sample.value == 2