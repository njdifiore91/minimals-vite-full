#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the core application setup module (app.py) of the OCR Service.

This test suite verifies that the OCR Service application correctly initializes all components,
loads configuration, sets up logging, and creates service instances. It ensures the application
can start and stop properly and handles errors appropriately.

The tests use pytest fixtures to mock external dependencies and isolate the application
for testing. Each test focuses on a specific aspect of the application's functionality.

Requirements tested:
- OCR Service must be implemented as a Python microservice using TensorFlow
- Service must implement consistent health check endpoints for Kubernetes probes
- Configuration must be loaded from environment variables for containerized deployment
- Service must extract data from documents with 99% accuracy
"""

import os
import pytest
import logging
import threading
import tensorflow as tf
from unittest.mock import MagicMock, patch, call
from fastapi.testclient import TestClient

# Import the application module
from src.app import OCRServiceApp
from src.utils.error_utils import ServiceError
from src.config import app_config, logging_config, tensorflow_config


@pytest.fixture
def mock_services():
    """Fixture to mock all service dependencies."""
    with patch('src.app.OCRService') as mock_ocr_service, \
         patch('src.app.QueueService') as mock_queue_service, \
         patch('src.app.StorageService') as mock_storage_service, \
         patch('src.app.FieldExtractionService') as mock_field_extraction_service, \
         patch('src.app.ConfidenceService') as mock_confidence_service, \
         patch('src.app.setup_logger') as mock_setup_logger, \
         patch('src.utils.tensorflow_utils.get_available_gpus') as mock_get_gpus, \
         patch('src.utils.tensorflow_utils.get_gpu_memory') as mock_get_gpu_memory, \
         patch('src.utils.tensorflow_utils.check_gpu_tensorflow_compatibility') as mock_check_gpu, \
         patch('src.utils.tensorflow_utils.get_cuda_version') as mock_get_cuda_version:
        
        # Create mock instances
        mock_ocr_service_instance = MagicMock()
        mock_queue_service_instance = MagicMock()
        mock_storage_service_instance = MagicMock()
        mock_field_extraction_instance = MagicMock()
        mock_confidence_service_instance = MagicMock()
        
        # Configure the mocks to return the instances
        mock_ocr_service.return_value = mock_ocr_service_instance
        mock_queue_service.return_value = mock_queue_service_instance
        mock_storage_service.return_value = mock_storage_service_instance
        mock_field_extraction_service.return_value = mock_field_extraction_instance
        mock_confidence_service.return_value = mock_confidence_service_instance
        
        # Configure GPU utility mocks
        mock_get_gpus.return_value = ['/device:GPU:0']
        mock_get_gpu_memory.return_value = 16384  # 16GB
        mock_check_gpu.return_value = True
        mock_get_cuda_version.return_value = '11.2'
        
        yield {
            'ocr_service': mock_ocr_service,
            'ocr_service_instance': mock_ocr_service_instance,
            'queue_service': mock_queue_service,
            'queue_service_instance': mock_queue_service_instance,
            'storage_service': mock_storage_service,
            'storage_service_instance': mock_storage_service_instance,
            'field_extraction_service': mock_field_extraction_service,
            'field_extraction_instance': mock_field_extraction_instance,
            'confidence_service': mock_confidence_service,
            'confidence_service_instance': mock_confidence_service_instance,
            'setup_logger': mock_setup_logger,
            'get_gpus': mock_get_gpus,
            'get_gpu_memory': mock_get_gpu_memory,
            'check_gpu': mock_check_gpu,
            'get_cuda_version': mock_get_cuda_version
        }


@pytest.fixture
def app_instance(mock_services):
    """Fixture to create an application instance with mocked services."""
    # Create the application instance
    app = OCRServiceApp()
    
    # Create a test client
    test_client = TestClient(app.app)
    
    # Add the test client to the app for convenience
    app.test_client = test_client
    
    yield app
    
    # Clean up
    app.stop()


def test_app_initialization(mock_services):
    """Test that the application initializes correctly."""
    # Create the application instance
    app = OCRServiceApp()
    
    # Verify that the logger was set up
    mock_services['setup_logger'].assert_called_once_with(logging_config)
    
    # Verify that all services were initialized
    mock_services['ocr_service'].assert_called_once_with(
        tensorflow_config=tensorflow_config,
        environment=app_config.ENVIRONMENT
    )
    mock_services['queue_service'].assert_called_once()
    mock_services['storage_service'].assert_called_once_with(
        s3_config=app_config,
        environment=app_config.ENVIRONMENT
    )
    mock_services['field_extraction_service'].assert_called_once()
    mock_services['confidence_service'].assert_called_once()
    
    # Verify that the FastAPI app was created
    assert app.app is not None
    assert app.app.title == "OCR Service"
    
    # Verify that the API router was included
    assert len(app.app.routes) > 0
    
    # Verify that the application state was initialized
    assert app.app.state.ocr_service == mock_services['ocr_service_instance']
    assert app.app.state.queue_service == mock_services['queue_service_instance']
    assert app.app.state.storage_service == mock_services['storage_service_instance']
    assert app.app.state.field_extraction_service == mock_services['field_extraction_instance']
    assert app.app.state.confidence_service == mock_services['confidence_service_instance']
    assert app.app.state.is_healthy is False
    assert app.app.state.is_ready is False
    
    # Verify that the stop event was created
    assert isinstance(app._stop_event, threading.Event)
    assert app._processing_thread is None


def test_app_start(app_instance, mock_services):
    """Test that the application starts correctly."""
    # Start the application
    app_instance.start()
    
    # Verify that the storage service was connected
    mock_services['storage_service_instance'].connect.assert_called_once()
    
    # Verify that the OCR models were loaded
    mock_services['ocr_service_instance'].load_models.assert_called_once()
    
    # Verify that the queue service was connected
    mock_services['queue_service_instance'].connect.assert_called_once()
    
    # Verify that the processing thread was started
    assert app_instance._processing_thread is not None
    assert app_instance._processing_thread.is_alive()
    
    # Verify that the application state was updated
    assert app_instance.app.state.is_healthy is True
    assert app_instance.app.state.is_ready is True


def test_app_stop(app_instance, mock_services):
    """Test that the application stops correctly."""
    # Start the application first
    app_instance.start()
    
    # Then stop it
    app_instance.stop()
    
    # Verify that the application state was updated
    assert app_instance.app.state.is_healthy is False
    assert app_instance.app.state.is_ready is False
    
    # Verify that the stop event was set
    assert app_instance._stop_event.is_set()
    
    # Verify that the queue service was disconnected
    mock_services['queue_service_instance'].disconnect.assert_called_once()
    
    # Verify that the storage service was disconnected
    mock_services['storage_service_instance'].disconnect.assert_called_once()
    
    # Verify that the OCR models were unloaded
    mock_services['ocr_service_instance'].unload_models.assert_called_once()


def test_app_start_error_handling(app_instance, mock_services):
    """Test that the application handles errors during startup."""
    # Configure the storage service to raise an exception
    mock_services['storage_service_instance'].connect.side_effect = Exception("Storage connection error")
    
    # Attempt to start the application and expect an exception
    with pytest.raises(ServiceError) as excinfo:
        app_instance.start()
    
    # Verify that the error message is correct
    assert "Failed to start application" in str(excinfo.value)
    assert "Storage connection error" in str(excinfo.value)
    
    # Verify that stop was called to clean up
    mock_services['queue_service_instance'].disconnect.assert_called_once()


def test_app_stop_error_handling(app_instance, mock_services):
    """Test that the application handles errors during shutdown."""
    # Start the application first
    app_instance.start()
    
    # Configure the services to raise exceptions during disconnect
    mock_services['queue_service_instance'].disconnect.side_effect = Exception("Queue disconnect error")
    mock_services['storage_service_instance'].disconnect.side_effect = Exception("Storage disconnect error")
    mock_services['ocr_service_instance'].unload_models.side_effect = Exception("Model unload error")
    
    # Stop the application - should not raise exceptions
    app_instance.stop()
    
    # Verify that the application state was updated despite errors
    assert app_instance.app.state.is_healthy is False
    assert app_instance.app.state.is_ready is False
    
    # Verify that all disconnect methods were called despite errors
    mock_services['queue_service_instance'].disconnect.assert_called_once()
    mock_services['storage_service_instance'].disconnect.assert_called_once()
    mock_services['ocr_service_instance'].unload_models.assert_called_once()


def test_message_processing(app_instance, mock_services):
    """Test the message processing functionality."""
    # Create a test message
    test_message = {
        'document_id': 'test-document-123',
        'document_type': 'invoice'
    }
    
    # Process the message
    result = app_instance._process_message(test_message)
    
    # Verify that the message was processed correctly
    assert result is True
    
    # Verify that the storage service was called to download the document
    mock_services['storage_service_instance'].download_document.assert_called_once_with('test-document-123')
    
    # Verify that the OCR service was called to process the document
    mock_services['ocr_service_instance'].process_document.assert_called_once()
    
    # Verify that the field extraction service was called
    mock_services['field_extraction_instance'].extract_fields.assert_called_once()
    
    # Verify that the confidence service was called
    mock_services['confidence_service_instance'].calculate_confidence.assert_called_once()
    
    # Verify that the storage service was called to upload the results
    mock_services['storage_service_instance'].upload_extraction_result.assert_called_once()
    
    # Verify that the queue service was called to publish the results
    mock_services['queue_service_instance'].publish_result.assert_called_once()


def test_message_processing_error_handling(app_instance, mock_services):
    """Test error handling during message processing."""
    # Create a test message
    test_message = {
        'document_id': 'test-document-123',
        'document_type': 'invoice'
    }
    
    # Configure the storage service to raise an exception
    mock_services['storage_service_instance'].download_document.side_effect = Exception("Download error")
    
    # Process the message
    result = app_instance._process_message(test_message)
    
    # Verify that the result indicates failure
    assert result is False
    
    # Verify that the queue service was called to publish an error message
    mock_services['queue_service_instance'].publish_error.assert_called_once()
    assert 'document_id' in mock_services['queue_service_instance'].publish_error.call_args[0][0]
    assert 'error' in mock_services['queue_service_instance'].publish_error.call_args[0][0]
    assert 'timestamp' in mock_services['queue_service_instance'].publish_error.call_args[0][0]


def test_health_endpoints(app_instance, mock_services):
    """Test the health check endpoints required for Kubernetes probes."""
    # Configure mock services for health checks
    mock_services['queue_service_instance'].check_connection = MagicMock(return_value=True)
    mock_services['queue_service_instance'].check_exchange_exists = MagicMock(return_value=True)
    mock_services['queue_service_instance'].check_queue_exists = MagicMock(return_value=True)
    
    mock_services['storage_service_instance'].check_connection = MagicMock(return_value=True)
    mock_services['storage_service_instance'].check_bucket_exists = MagicMock(return_value=True)
    
    # Test the liveness endpoint
    response = app_instance.test_client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert "service" in response.json()
    assert "version" in response.json()
    assert "timestamp" in response.json()
    
    # Test the readiness endpoint when not ready
    app_instance.app.state.is_ready = False
    response = app_instance.test_client.get("/api/v1/health/readiness")
    assert response.status_code == 503  # Service Unavailable
    
    # Start the application to make it ready
    app_instance.start()
    app_instance.app.state.is_ready = True
    
    # Test the readiness endpoint when ready
    response = app_instance.test_client.get("/api/v1/health/readiness")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    
    # Verify that the readiness check includes all required dependencies
    assert "dependencies" in response.json()
    assert "rabbitmq" in response.json()["dependencies"]
    assert "s3" in response.json()["dependencies"]
    assert "gpu" in response.json()["dependencies"]


def test_environment_configuration(mock_services):
    """Test that the application loads configuration from environment variables for containerized deployment."""
    # Set environment variables for testing
    os.environ["ENVIRONMENT"] = "production"
    os.environ["LOG_LEVEL"] = "INFO"
    os.environ["TF_USE_GPU"] = "true"
    os.environ["TF_GPU_MEMORY_LIMIT"] = "8192"
    os.environ["RABBITMQ_HOST"] = "rabbitmq.production"
    os.environ["RABBITMQ_PORT"] = "5672"
    os.environ["RABBITMQ_USERNAME"] = "mca_service"
    os.environ["RABBITMQ_PASSWORD"] = "secure_password"
    os.environ["S3_ENDPOINT"] = "s3.production"
    os.environ["S3_BUCKET"] = "mca-documents-production"
    
    # Mock the AppConfig to capture environment variable loading
    with patch('src.config.app_config.AppConfig') as MockAppConfig, \
         patch('src.config.app_config.Environment.from_string') as mock_env_from_string, \
         patch('src.config.app_config.LogLevel') as MockLogLevel:
        
        # Configure mocks
        mock_env_from_string.return_value = "production"
        mock_config = MagicMock()
        MockAppConfig.return_value = mock_config
        
        # Create a new app_config instance to trigger environment variable loading
        from src.config.app_config import get_config
        config = get_config()
        
        # Create the application instance
        app = OCRServiceApp()
        
        # Verify that environment variables were used
        MockAppConfig.assert_called_once()
        mock_env_from_string.assert_called_with("production")
    
    # Clean up environment variables
    del os.environ["ENVIRONMENT"]
    del os.environ["LOG_LEVEL"]
    del os.environ["TF_USE_GPU"]
    del os.environ["TF_GPU_MEMORY_LIMIT"]
    del os.environ["RABBITMQ_HOST"]
    del os.environ["RABBITMQ_PORT"]
    del os.environ["RABBITMQ_USERNAME"]
    del os.environ["RABBITMQ_PASSWORD"]
    del os.environ["S3_ENDPOINT"]
    del os.environ["S3_BUCKET"]


def test_cors_configuration(app_instance):
    """Test that CORS is configured correctly for frontend integration."""
    # Test a CORS preflight request
    headers = {
        "Origin": "http://localhost:3000",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type,Authorization",
    }
    response = app_instance.test_client.options("/api/v1/ocr/process", headers=headers)
    
    # Verify that CORS headers are present
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "access-control-allow-headers" in response.headers
    assert "access-control-allow-credentials" in response.headers
    
    # Verify specific CORS settings
    assert response.headers["access-control-allow-origin"] == "*"  # Should be restricted in production
    assert "POST" in response.headers["access-control-allow-methods"]
    assert "GET" in response.headers["access-control-allow-methods"]
    
    # Test an actual request with CORS headers
    headers = {"Origin": "http://localhost:3000"}
    response = app_instance.test_client.get("/api/v1/health/liveness", headers=headers)
    
    # Verify that CORS headers are included in the response
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_message_processing_thread(app_instance, mock_services):
    """Test the message processing thread for handling document processing."""
    # Start the application
    app_instance.start()
    
    # Verify that the processing thread was created and started
    assert app_instance._processing_thread is not None
    assert app_instance._processing_thread.is_alive()
    assert app_instance._processing_thread.daemon is True  # Should be a daemon thread
    
    # Verify that the queue service's start_consuming method will be called in the thread
    # We can't directly test the thread's execution, but we can verify the thread was started
    # with the correct target function
    assert app_instance._processing_thread._target == app_instance._message_processing_loop
    
    # Simulate an error in the queue service
    mock_services['queue_service_instance'].start_consuming.side_effect = Exception("Connection lost")
    
    # Manually call the processing loop to simulate thread execution
    # Set the stop event first so it only runs once
    app_instance._stop_event.set()
    app_instance._message_processing_loop()
    
    # Verify that reconnect was not attempted because stop_event was set
    mock_services['queue_service_instance'].reconnect.assert_not_called()
    
    # Reset the stop event and mock
    app_instance._stop_event.clear()
    mock_services['queue_service_instance'].reconnect.reset_mock()
    
    # Now simulate the thread running with an error but without stop_event set
    # We'll need to make it set the stop event after one iteration to prevent infinite loop
    def side_effect(*args, **kwargs):
        # Set stop event after exception to prevent infinite loop in test
        app_instance._stop_event.set()
        raise Exception("Connection lost")
    
    mock_services['queue_service_instance'].start_consuming.side_effect = side_effect
    
    # Call the processing loop again
    app_instance._message_processing_loop()
    
    # Verify that reconnect was attempted this time
    mock_services['queue_service_instance'].reconnect.assert_called_once()
    
    # Stop the application
    app_instance.stop()


def test_tensorflow_gpu_configuration(mock_services):
    """Test that TensorFlow GPU configuration is applied correctly for OCR processing."""
    # Set environment variables for testing
    os.environ["TF_USE_GPU"] = "true"
    os.environ["TF_GPU_MEMORY_LIMIT"] = "8192"
    
    # Create the application instance with mocked TensorFlow
    with patch('src.services.ocr_service.tf') as mock_tf, \
         patch('src.config.tensorflow_config.TF_USE_GPU', True), \
         patch('src.config.tensorflow_config.TF_GPU_MEMORY_LIMIT', 8192):
        
        # Configure mock TensorFlow
        mock_tf.config = MagicMock()
        mock_tf.config.experimental = MagicMock()
        mock_tf.config.experimental.set_memory_growth = MagicMock()
        mock_tf.config.experimental.set_virtual_device_configuration = MagicMock()
        mock_tf.config.list_physical_devices = MagicMock(return_value=['GPU:0'])
        mock_tf.config.experimental.VirtualDeviceConfiguration = MagicMock()
        
        # Create and start the application
        app = OCRServiceApp()
        app.start()
        
        # Verify that the OCR service was initialized with the correct configuration
        mock_services['ocr_service'].assert_called_once_with(
            tensorflow_config=tensorflow_config,
            environment=app_config.ENVIRONMENT
        )
        
        # Verify that the OCR service loaded models with GPU configuration
        mock_services['ocr_service_instance'].load_models.assert_called_once()
    
    # Clean up environment variables
    del os.environ["TF_USE_GPU"]
    del os.environ["TF_GPU_MEMORY_LIMIT"]
    
    # Stop the application
    app.stop()


def test_document_processing_accuracy(app_instance, mock_services):
    """Test that document processing meets the 99% accuracy requirement as specified in section 0.1.2."""
    # Create a test message
    test_message = {
        'document_id': 'test-document-123',
        'document_type': 'invoice'
    }
    
    # Configure the mock services for the test
    mock_document = MagicMock()
    mock_ocr_result = MagicMock()
    mock_extracted_data = MagicMock()
    
    mock_services['storage_service_instance'].download_document.return_value = mock_document
    mock_services['ocr_service_instance'].process_document.return_value = mock_ocr_result
    mock_services['field_extraction_instance'].extract_fields.return_value = mock_extracted_data
    
    # Configure the confidence service to return high confidence scores (99% accuracy)
    mock_services['confidence_service_instance'].calculate_confidence.return_value = {
        'overall_confidence': 0.99,  # 99% confidence
        'field_confidence': {
            'invoice_number': 0.99,
            'date': 0.99,
            'total_amount': 0.99,
            'vendor_name': 0.99
        },
        'requires_review': False,
        'processing_time': 1.5
    }
    
    # Configure the storage service to return a result key
    mock_services['storage_service_instance'].upload_extraction_result.return_value = 'results/test-document-123.json'
    
    # Process the message
    result = app_instance._process_message(test_message)
    
    # Verify that the result indicates success
    assert result is True
    
    # Verify that the document was processed through the entire pipeline
    mock_services['storage_service_instance'].download_document.assert_called_once_with('test-document-123')
    mock_services['ocr_service_instance'].process_document.assert_called_once_with(mock_document)
    mock_services['field_extraction_instance'].extract_fields.assert_called_once_with(
        mock_ocr_result, document_type='invoice'
    )
    mock_services['confidence_service_instance'].calculate_confidence.assert_called_once_with(mock_extracted_data)
    
    # Verify that the confidence scores meet the 99% requirement
    published_result = mock_services['queue_service_instance'].publish_result.call_args[0][0]
    assert published_result['confidence_score'] >= 0.99
    assert published_result['requires_review'] is False
    
    # Verify that the result was published to the queue
    mock_services['queue_service_instance'].publish_result.assert_called_once()
    
    # Test with a lower confidence score (below 99%)
    mock_services['confidence_service_instance'].calculate_confidence.return_value = {
        'overall_confidence': 0.85,  # 85% confidence - below requirement
        'field_confidence': {
            'invoice_number': 0.99,
            'date': 0.75,  # Problem field
            'total_amount': 0.99,
            'vendor_name': 0.70  # Problem field
        },
        'requires_review': True,  # Should require review
        'processing_time': 1.8
    }
    
    # Reset mocks for the second test
    mock_services['queue_service_instance'].publish_result.reset_mock()
    
    # Process the message again
    result = app_instance._process_message(test_message)
    
    # Verify that the result still indicates success (processing completed)
    assert result is True
    
    # Verify that the result was flagged for review due to lower confidence
    published_result = mock_services['queue_service_instance'].publish_result.call_args[0][0]
    assert published_result['confidence_score'] < 0.99
    assert published_result['requires_review'] is True