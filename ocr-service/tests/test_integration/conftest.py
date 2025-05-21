#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Provides shared test fixtures and utilities for OCR Service integration tests.

Sets up test environment with mocked external dependencies (RabbitMQ, S3),
test documents, and helper functions. Enables consistent test setup across
all integration test modules and simplifies test maintenance.
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Generator, Tuple

# Import application modules
from src.types.config import RabbitMQConfig
from src.types.messages import MessagePayload, MessageHeaders


@pytest.fixture
def integration_test_rabbitmq_config() -> RabbitMQConfig:
    """Provides a RabbitMQ configuration specifically for integration tests."""
    return RabbitMQConfig(
        host="localhost",
        port=5672,
        username="guest",
        password="guest",
        vhost="/",
        exchange_name="mca.documents.test",
        exchange_type="fanout",
        ocr_request_queue="ocr.request.test",
        data_processing_queue="data.processing.test",
        use_tls=True,  # Enable TLS for testing
        ca_cert_path="/path/to/ca.pem",
        client_cert_path="/path/to/client.pem",
        client_key_path="/path/to/client.key",
        cert_password=None,
        use_cert_auth=True,
        heartbeat=30,
        connection_timeout=15,
        prefetch_count=10,
        max_retries=3,
        retry_delay=0.1,  # Short delay for testing
        max_delay=0.5     # Short max delay for testing
    )


@pytest.fixture
def mock_rabbitmq_channel():
    """Provides a mocked RabbitMQ channel for integration tests."""
    mock_channel = MagicMock()
    
    # Configure mock methods
    mock_channel.exchange_declare = MagicMock()
    mock_channel.queue_declare = MagicMock(return_value=MagicMock(method=MagicMock(queue="test-queue")))
    mock_channel.queue_bind = MagicMock()
    mock_channel.basic_publish = MagicMock()
    mock_channel.basic_consume = MagicMock(return_value="test-consumer-tag")
    mock_channel.basic_ack = MagicMock()
    mock_channel.basic_reject = MagicMock()
    mock_channel.basic_cancel = MagicMock()
    mock_channel.basic_qos = MagicMock()
    mock_channel.is_closed = False
    mock_channel.close = MagicMock()
    
    return mock_channel


@pytest.fixture
def mock_rabbitmq_connection(mock_rabbitmq_channel):
    """Provides a mocked RabbitMQ connection for integration tests."""
    mock_connection = MagicMock()
    
    # Configure mock methods
    mock_connection.channel = MagicMock(return_value=mock_rabbitmq_channel)
    mock_connection.is_closed = False
    mock_connection.close = MagicMock()
    
    return mock_connection


@pytest.fixture
def sample_rabbitmq_message() -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Provides a sample RabbitMQ message for testing."""
    payload = {
        "document_id": "doc-123456",
        "application_id": "app-789012",
        "document_type": "application",
        "storage_path": "s3://mca-documents-test/documents/doc-123456.pdf",
        "mime_type": "application/pdf",
        "file_name": "application.pdf",
        "file_size": 12345,
        "created_at": "2023-01-01T12:00:00Z",
        "metadata": {
            "source": "email",
            "sender": "applicant@example.com"
        },
        "classification": {
            "type": "application",
            "confidence": 0.95
        }
    }
    
    headers = {
        "message_id": "msg-123456",
        "correlation_id": "corr-123456",
        "timestamp": "2023-01-01T12:00:00Z",
        "content_type": "application/json",
        "content_encoding": "utf-8",
        "app_id": "document-service"
    }
    
    return payload, headers


@pytest.fixture
def sample_rabbitmq_properties(sample_rabbitmq_message):
    """Provides sample RabbitMQ message properties for testing."""
    _, headers = sample_rabbitmq_message
    
    mock_properties = MagicMock()
    mock_properties.headers = headers
    mock_properties.content_type = headers.get("content_type")
    mock_properties.content_encoding = headers.get("content_encoding")
    mock_properties.correlation_id = headers.get("correlation_id")
    mock_properties.message_id = headers.get("message_id")
    mock_properties.timestamp = headers.get("timestamp")
    mock_properties.app_id = headers.get("app_id")
    
    return mock_properties


@pytest.fixture
def sample_rabbitmq_method():
    """Provides a sample RabbitMQ method (delivery info) for testing."""
    mock_method = MagicMock()
    mock_method.delivery_tag = 1
    mock_method.routing_key = "ocr.request"
    mock_method.exchange = "mca.documents.test"
    
    return mock_method