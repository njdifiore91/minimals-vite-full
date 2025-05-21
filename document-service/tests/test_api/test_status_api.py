"""
Unit tests for the Document Service status API endpoints.

This module contains tests that verify the Document Service status API endpoints
correctly report service status, document processing metrics, and queue depths.
It also tests the integration with the notification service for status updates.
"""

import json
import time
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from src.api.status import (
    record_document_processed,
    record_processing_time,
    update_classification_accuracy,
    update_queue_depth,
    DOCUMENT_PROCESSED_COUNTER,
    DOCUMENT_PROCESSING_TIME,
    CLASSIFICATION_ACCURACY,
    QUEUE_DEPTH
)
from src.types.documents import DocumentType, ProcessingStatus


class TestStatusEndpoints:
    """Test cases for the Document Service status API endpoints."""

    def test_get_status(self, client: TestClient, mock_queue_service):
        """Test that the status endpoint returns the correct service status information."""
        # Mock the queue depth method
        mock_queue_service.get_queue_depth.return_value = 5
        mock_queue_service.get_connection_count.return_value = 3
        
        # Call the status endpoint
        response = client.get("/status")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check required fields
        assert data["status"] == "operational"
        assert data["service"] == "document-service"
        assert "version" in data
        assert "uptime_seconds" in data
        assert "environment" in data
        
        # Check resource information
        assert "resources" in data
        assert "cpu_percent" in data["resources"]
        assert "memory_usage_bytes" in data["resources"]
        assert "thread_count" in data["resources"]
        
        # Check queue information
        assert "queue" in data
        assert data["queue"]["document_processing_depth"] == 5
        
        # Check connection information
        assert "connections" in data
        assert data["connections"]["rabbitmq"] == 3

    def test_get_status_with_queue_error(self, client: TestClient, mock_queue_service):
        """Test that the status endpoint handles queue service errors gracefully."""
        # Mock the queue depth method to raise an exception
        mock_queue_service.get_queue_depth.side_effect = Exception("Queue connection error")
        mock_queue_service.get_connection_count.side_effect = Exception("Connection count error")
        
        # Call the status endpoint
        response = client.get("/status")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that the endpoint still returns a valid response despite the error
        assert data["status"] == "operational"
        assert data["queue"]["document_processing_depth"] == -1
        assert data["connections"]["rabbitmq"] == -1

    def test_health_check(self, client: TestClient):
        """Test that the health check endpoint returns a healthy status."""
        # Call the health check endpoint
        response = client.get("/status/health")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_metrics_endpoint(self, client: TestClient, mock_queue_service):
        """Test that the metrics endpoint returns Prometheus metrics in the correct format."""
        # Mock the queue depth method
        mock_queue_service.get_queue_depth.return_value = 10
        
        # Call the metrics endpoint
        response = client.get("/status/metrics")
        
        # Verify the response
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/openmetrics-text; version=1.0.0; charset=utf-8"
        
        # Check that the response contains expected metric names
        content = response.text
        assert "document_service_documents_processed_total" in content
        assert "document_service_processing_time_seconds" in content
        assert "document_service_classification_accuracy" in content
        assert "document_service_queue_depth" in content
        assert "document_service_cpu_usage_percent" in content
        assert "document_service_memory_usage_bytes" in content

    def test_metrics_with_queue_error(self, client: TestClient, mock_queue_service):
        """Test that the metrics endpoint handles queue service errors gracefully."""
        # Mock the queue depth method to raise an exception
        mock_queue_service.get_queue_depth.side_effect = Exception("Queue connection error")
        
        # Call the metrics endpoint
        response = client.get("/status/metrics")
        
        # Verify the response still succeeds despite the error
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "application/openmetrics-text; version=1.0.0; charset=utf-8"

    def test_get_processing_stats(self, client: TestClient):
        """Test that the processing stats endpoint returns detailed statistics."""
        # Call the processing stats endpoint
        response = client.get("/status/stats")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check required sections
        assert "throughput" in data
        assert "accuracy" in data
        assert "errors" in data
        assert "queue_status" in data
        
        # Check throughput metrics
        assert "documents_per_minute" in data["throughput"]
        assert "documents_processed_today" in data["throughput"]
        assert "documents_processed_total" in data["throughput"]
        
        # Check accuracy metrics
        assert "overall_percent" in data["accuracy"]
        assert "by_model" in data["accuracy"]
        assert "by_document_type" in data["accuracy"]
        
        # Check error metrics
        assert "error_rate_percent" in data["errors"]
        assert "most_common_errors" in data["errors"]
        
        # Check queue metrics
        assert "current_depth" in data["queue_status"]
        assert "average_wait_time_seconds" in data["queue_status"]
        assert "max_wait_time_seconds" in data["queue_status"]


class TestMetricsHelpers:
    """Test cases for the Document Service metrics helper functions."""

    def test_record_document_processed(self):
        """Test that the record_document_processed function increments the counter."""
        # Get the initial value
        initial_value = DOCUMENT_PROCESSED_COUNTER.labels(
            document_type=DocumentType.APPLICATION.value,
            status=ProcessingStatus.COMPLETED.value
        )._value.get()
        
        # Call the function
        record_document_processed(
            document_type=DocumentType.APPLICATION.value,
            status=ProcessingStatus.COMPLETED.value
        )
        
        # Get the new value
        new_value = DOCUMENT_PROCESSED_COUNTER.labels(
            document_type=DocumentType.APPLICATION.value,
            status=ProcessingStatus.COMPLETED.value
        )._value.get()
        
        # Verify the counter was incremented
        assert new_value == initial_value + 1

    def test_record_processing_time(self):
        """Test that the record_processing_time function observes the processing time."""
        # Get the initial count
        initial_count = DOCUMENT_PROCESSING_TIME.labels(
            document_type=DocumentType.APPLICATION.value
        )._count.get()
        
        # Call the function
        record_processing_time(
            document_type=DocumentType.APPLICATION.value,
            processing_time=1.5
        )
        
        # Get the new count
        new_count = DOCUMENT_PROCESSING_TIME.labels(
            document_type=DocumentType.APPLICATION.value
        )._count.get()
        
        # Verify the histogram count was incremented
        assert new_count == initial_count + 1

    def test_update_classification_accuracy(self):
        """Test that the update_classification_accuracy function sets the gauge value."""
        # Call the function
        update_classification_accuracy(model_type="svm", accuracy=98.5)
        
        # Get the value
        value = CLASSIFICATION_ACCURACY.labels(model_type="svm")._value.get()
        
        # Verify the gauge was set to the correct value
        assert value == 98.5

    def test_update_queue_depth(self):
        """Test that the update_queue_depth function sets the gauge value."""
        # Call the function
        update_queue_depth(queue_name="document-processing", depth=42)
        
        # Get the value
        value = QUEUE_DEPTH.labels(queue_name="document-processing")._value.get()
        
        # Verify the gauge was set to the correct value
        assert value == 42


class TestDocumentStatusTracking:
    """Test cases for document status tracking and notification integration."""

    @patch('src.api.status.record_document_processed')
    def test_document_status_update(self, mock_record_processed, client: TestClient, create_test_document):
        """Test that document status updates are properly tracked and recorded in metrics."""
        # Create a test document
        document = create_test_document()
        document_id = document.metadata['document_id']
        
        # Mock the API endpoint for updating document status
        with patch('src.services.queue_service.QueueService.publish') as mock_publish:
            # Call the document status update endpoint
            response = client.put(
                f"/documents/{document_id}/status",
                json={"status": ProcessingStatus.COMPLETED.value}
            )
            
            # Verify the response
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == ProcessingStatus.COMPLETED.value
            
            # Verify that the metrics were updated
            mock_record_processed.assert_called_once_with(
                document_type=document.document_type.value if document.document_type else "unknown",
                status=ProcessingStatus.COMPLETED.value
            )
            
            # Verify that a notification was published to the queue
            mock_publish.assert_called_once()
            # Check that the published message contains the correct information
            published_message = mock_publish.call_args[0][0]
            assert published_message["document_id"] == document_id
            assert published_message["status"] == ProcessingStatus.COMPLETED.value

    def test_batch_status_retrieval(self, client: TestClient, create_test_documents):
        """Test that batch status retrieval works correctly for multiple documents."""
        # Create multiple test documents
        documents = create_test_documents(5)
        document_ids = [doc.metadata['document_id'] for doc in documents]
        
        # Call the batch status endpoint
        response = client.post(
            "/documents/batch/status",
            json={"document_ids": document_ids}
        )
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that all document statuses are returned
        assert len(data["documents"]) == 5
        for doc_status in data["documents"]:
            assert "document_id" in doc_status
            assert "status" in doc_status
            assert doc_status["document_id"] in document_ids

    @patch('src.services.queue_service.QueueService.publish')
    def test_status_webhook_notification(self, mock_publish, client: TestClient, create_test_document):
        """Test that status updates trigger webhook notifications via the queue service."""
        # Create a test document
        document = create_test_document()
        document_id = document.metadata['document_id']
        
        # Call the document status update endpoint
        response = client.put(
            f"/documents/{document_id}/status",
            json={
                "status": ProcessingStatus.CLASSIFIED.value,
                "notify": True  # Request notification
            }
        )
        
        # Verify the response
        assert response.status_code == 200
        
        # Verify that a notification was published to the queue
        mock_publish.assert_called_once()
        
        # Check that the published message contains the correct information
        published_message = mock_publish.call_args[0][0]
        assert published_message["document_id"] == document_id
        assert published_message["status"] == ProcessingStatus.CLASSIFIED.value
        assert published_message["event_type"] == "status_update"
        assert "timestamp" in published_message

    def test_status_history_retrieval(self, client: TestClient, create_test_document):
        """Test that status history is maintained and can be retrieved for audit purposes."""
        # Create a test document
        document = create_test_document()
        document_id = document.metadata['document_id']
        
        # Update the document status multiple times to create history
        status_updates = [
            ProcessingStatus.RECEIVED.value,
            ProcessingStatus.CLASSIFYING.value,
            ProcessingStatus.CLASSIFIED.value,
            ProcessingStatus.PROCESSING.value,
            ProcessingStatus.COMPLETED.value
        ]
        
        for status in status_updates:
            # Small delay to ensure different timestamps
            time.sleep(0.01)
            
            # Update the status
            client.put(
                f"/documents/{document_id}/status",
                json={"status": status}
            )
        
        # Retrieve the status history
        response = client.get(f"/documents/{document_id}/status/history")
        
        # Verify the response
        assert response.status_code == 200
        data = response.json()
        
        # Check that the history contains all status updates
        assert len(data["history"]) == len(status_updates)
        
        # Check that the history is in chronological order (oldest first)
        for i, status_record in enumerate(data["history"]):
            assert status_record["status"] == status_updates[i]
            assert "timestamp" in status_record
            
            # Check that timestamps are in ascending order
            if i > 0:
                prev_timestamp = data["history"][i-1]["timestamp"]
                curr_timestamp = status_record["timestamp"]
                assert prev_timestamp < curr_timestamp