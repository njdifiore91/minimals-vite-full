#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the core application setup module (app.py) of the OCR Service.

This file verifies that the application correctly initializes all components,
loads configuration, sets up logging, and creates service instances. It ensures
the application can start and stop properly and handles errors appropriately.
"""

import os
import pytest
import logging
from unittest.mock import MagicMock, patch, call
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Import the Application class to test
from src.app import Application

# Import types for type checking
from src.types.config import ServiceConfig, TensorFlowConfig, RabbitMQConfig, S3Config, LoggingConfig


class TestApplication:
    """Test suite for the OCR Service Application class."""

    def test_application_initialization(self, app_config):
        """Test that the Application initializes correctly with valid configuration."""
        # Create an application instance
        app = Application(config=app_config)
        
        # Verify that the application was initialized correctly
        assert app.config == app_config
        assert app.logger is not None
        assert app.is_running is False
        assert app.fastapi_app is not None
        assert isinstance(app.fastapi_app, FastAPI)

    def test_application_initialization_with_invalid_config(self):
        """Test that the Application raises an error with invalid configuration."""
        # Test with None config
        with pytest.raises(ValueError, match="Configuration cannot be None"):
            Application(config=None)
        
        # Test with empty config
        with pytest.raises(ValueError, match="Invalid configuration"):
            Application(config={})
        
        # Test with missing required config sections
        incomplete_config = {"service": {"service_name": "test"}}
        with pytest.raises(ValueError, match="Missing required configuration"):
            Application(config=incomplete_config)

    def test_logger_initialization(self, app_config):
        """Test that the logger is initialized correctly with the specified log level."""
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Create an application instance
            app = Application(config=app_config)
            
            # Verify that the logger was configured correctly
            mock_get_logger.assert_called_once_with('ocr-service-test')
            mock_logger.setLevel.assert_called_once()

    @pytest.mark.parametrize("log_level,expected_level", [
        ("DEBUG", logging.DEBUG),
        ("INFO", logging.INFO),
        ("WARNING", logging.WARNING),
        ("ERROR", logging.ERROR),
        ("CRITICAL", logging.CRITICAL),
        ("invalid", logging.INFO),  # Default to INFO for invalid levels
    ])
    def test_logger_levels(self, app_config, log_level, expected_level):
        """Test that different log levels are set correctly."""
        # Modify the config to use the test log level
        app_config["logging"]["level"] = log_level
        
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Create an application instance
            app = Application(config=app_config)
            
            # Verify that the logger was set to the expected level
            mock_logger.setLevel.assert_called_once_with(expected_level)

    def test_service_creation(self, app_config):
        """Test that all required services are created during initialization."""
        # Create patches for all service classes
        with patch('src.services.ocr_service.OCRService') as mock_ocr_service, \
             patch('src.services.queue_service.QueueService') as mock_queue_service, \
             patch('src.services.storage_service.StorageService') as mock_storage_service, \
             patch('src.services.confidence_service.ConfidenceService') as mock_confidence_service, \
             patch('src.services.field_extraction_service.FieldExtractionService') as mock_field_extraction_service:
            
            # Create an application instance
            app = Application(config=app_config)
            
            # Verify that all services were created
            mock_ocr_service.assert_called_once()
            mock_queue_service.assert_called_once()
            mock_storage_service.assert_called_once()
            mock_confidence_service.assert_called_once()
            mock_field_extraction_service.assert_called_once()
            
            # Verify that the services were assigned to the application
            assert app.ocr_service is not None
            assert app.queue_service is not None
            assert app.storage_service is not None
            assert app.confidence_service is not None
            assert app.field_extraction_service is not None

    def test_start_method(self, mock_application):
        """Test that the start method initializes all services correctly."""
        # Start the application
        mock_application.start()
        
        # Verify that all services were started
        mock_application.queue_service.connect.assert_called_once()
        mock_application.storage_service.connect.assert_called_once()
        
        # Verify that the application is marked as running
        assert mock_application.is_running is True

    def test_start_method_with_queue_error(self, mock_application):
        """Test that the start method handles queue connection errors."""
        # Configure the queue service to fail on connect
        mock_application.queue_service.connect.side_effect = Exception("Queue connection error")
        
        # Start the application and expect an exception
        with pytest.raises(Exception, match="Failed to start application"):
            mock_application.start()
        
        # Verify that the application is not marked as running
        assert mock_application.is_running is False

    def test_stop_method(self, mock_application):
        """Test that the stop method shuts down all services correctly."""
        # First start the application
        mock_application.start()
        assert mock_application.is_running is True
        
        # Then stop it
        mock_application.stop()
        
        # Verify that all services were stopped
        mock_application.queue_service.disconnect.assert_called_once()
        mock_application.storage_service.disconnect.assert_called_once()
        
        # Verify that the application is marked as not running
        assert mock_application.is_running is False

    def test_stop_method_with_error(self, mock_application):
        """Test that the stop method handles service disconnection errors."""
        # First start the application
        mock_application.start()
        assert mock_application.is_running is True
        
        # Configure the queue service to fail on disconnect
        mock_application.queue_service.disconnect.side_effect = Exception("Queue disconnection error")
        
        # Stop the application
        mock_application.stop()
        
        # Verify that the application still attempts to stop all services
        mock_application.queue_service.disconnect.assert_called_once()
        mock_application.storage_service.disconnect.assert_called_once()
        
        # Verify that the application is marked as not running despite the error
        assert mock_application.is_running is False

    def test_health_check_endpoints(self, mock_application):
        """Test that the health check endpoints are set up correctly."""
        # Create a test client for the FastAPI app
        client = TestClient(mock_application.fastapi_app)
        
        # Test the liveness endpoint
        response = client.get("/health/liveness")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
        
        # Test the readiness endpoint when not running
        mock_application.is_running = False
        response = client.get("/health/readiness")
        assert response.status_code == 503
        assert response.json()["status"] == "not_ready"
        
        # Test the readiness endpoint when running
        mock_application.is_running = True
        response = client.get("/health/readiness")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"

    def test_api_router_setup(self, app_config):
        """Test that the API routers are set up correctly."""
        with patch('src.api.router.router') as mock_router:
            # Create an application instance
            app = Application(config=app_config)
            
            # Verify that the router was included in the FastAPI app
            app.fastapi_app.include_router.assert_called_with(mock_router)

    def test_environment_variable_loading(self):
        """Test that the application can load configuration from environment variables."""
        # Set up environment variables for testing
        env_vars = {
            "OCR_SERVICE_NAME": "ocr-service-env-test",
            "OCR_SERVICE_VERSION": "1.0.0-env-test",
            "OCR_SERVICE_PORT": "8081",
            "OCR_SERVICE_ENVIRONMENT": "test",
            "OCR_TENSORFLOW_MODEL_PATH": "/tmp/models-env-test",
            "OCR_RABBITMQ_HOST": "rabbitmq-env-test",
            "OCR_S3_BUCKET": "mca-documents-env-test",
            "OCR_LOGGING_LEVEL": "DEBUG"
        }
        
        with patch.dict(os.environ, env_vars):
            with patch('src.app.Application._load_config_from_env') as mock_load_config:
                # Mock the config loading to return a valid config
                mock_load_config.return_value = {
                    "service": ServiceConfig(
                        service_name="ocr-service-env-test",
                        version="1.0.0-env-test",
                        environment="test",
                        port=8081,
                        debug=True
                    ),
                    "tensorflow": TensorFlowConfig(
                        model_path="/tmp/models-env-test",
                        typed_model_name="typed_model",
                        handwritten_model_name="handwritten_model",
                        hybrid_model_name="hybrid_model",
                        gpu_memory_limit=1024,
                        confidence_threshold=0.75,
                        use_gpu=False
                    ),
                    "rabbitmq": RabbitMQConfig(
                        host="rabbitmq-env-test",
                        port=5672,
                        username="guest",
                        password="guest",
                        vhost="/",
                        exchange="mca.documents.test",
                        queue="data-extraction-test",
                        routing_key="ocr.test",
                        use_tls=False,
                        cert_path=None,
                        reconnect_attempts=3,
                        reconnect_delay=1
                    ),
                    "s3": S3Config(
                        endpoint_url="http://localhost:4566",
                        region="us-east-1",
                        bucket="mca-documents-env-test",
                        access_key="test",
                        secret_key="test",
                        use_ssl=False,
                        encryption_key="test-encryption-key",
                        timeout=5
                    ),
                    "logging": LoggingConfig(
                        level="DEBUG",
                        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                        file_path=None
                    )
                }
                
                # Create an application instance
                app = Application()
                
                # Verify that the config loading method was called
                mock_load_config.assert_called_once()
                
                # Verify that the application was initialized with the loaded config
                assert app.config["service"].service_name == "ocr-service-env-test"
                assert app.config["tensorflow"].model_path == "/tmp/models-env-test"
                assert app.config["rabbitmq"].host == "rabbitmq-env-test"
                assert app.config["s3"].bucket == "mca-documents-env-test"
                assert app.config["logging"].level == "DEBUG"

    def test_gpu_availability_check(self, app_config):
        """Test that the application checks for GPU availability."""
        with patch('tensorflow.config.list_physical_devices') as mock_list_devices:
            # Mock GPU availability
            mock_list_devices.return_value = ['/device:GPU:0']
            
            # Create an application instance with GPU enabled
            app_config["tensorflow"]["use_gpu"] = True
            app = Application(config=app_config)
            
            # Verify that GPU devices were checked
            mock_list_devices.assert_called_once_with('GPU')
            
            # Verify that the application logged GPU availability
            assert app.config["tensorflow"].use_gpu is True

    def test_gpu_not_available(self, app_config):
        """Test that the application handles missing GPU gracefully."""
        with patch('tensorflow.config.list_physical_devices') as mock_list_devices, \
             patch('logging.getLogger') as mock_get_logger:
            # Mock no GPU available
            mock_list_devices.return_value = []
            
            # Mock logger
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger
            
            # Create an application instance with GPU enabled
            app_config["tensorflow"]["use_gpu"] = True
            app = Application(config=app_config)
            
            # Verify that GPU devices were checked
            mock_list_devices.assert_called_once_with('GPU')
            
            # Verify that the application logged a warning about missing GPU
            mock_logger.warning.assert_called_with(
                "GPU acceleration requested but no GPU devices found. Falling back to CPU."
            )
            
            # Verify that the application disabled GPU usage
            assert app.config["tensorflow"].use_gpu is False

    def test_application_version(self, app_config):
        """Test that the application exposes its version correctly."""
        # Create an application instance
        app = Application(config=app_config)
        
        # Verify that the version is accessible
        assert app.version == app_config["service"].version
        
        # Test the version endpoint
        client = TestClient(app.fastapi_app)
        response = client.get("/version")
        assert response.status_code == 200
        assert response.json()["version"] == app_config["service"].version

    def test_application_metrics_endpoint(self, mock_application):
        """Test that the application exposes metrics correctly."""
        # Configure mock services to return metrics
        mock_application.ocr_service.get_metrics.return_value = {
            "documents_processed": 100,
            "average_confidence": 0.92,
            "processing_time_avg_ms": 450
        }
        
        # Test the metrics endpoint
        client = TestClient(mock_application.fastapi_app)
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "documents_processed" in response.json()
        assert response.json()["documents_processed"] == 100
        assert "average_confidence" in response.json()
        assert response.json()["average_confidence"] == 0.92

    def test_application_exception_handling(self, app_config):
        """Test that the application handles exceptions correctly."""
        with patch('src.services.ocr_service.OCRService') as mock_ocr_service:
            # Configure the OCR service to raise an exception during initialization
            mock_ocr_service.side_effect = Exception("OCR service initialization error")
            
            # Create an application instance and expect an exception
            with pytest.raises(Exception, match="Failed to initialize application"):
                Application(config=app_config)

    def test_application_shutdown_hook(self, mock_application):
        """Test that the application registers a shutdown hook."""
        with patch('atexit.register') as mock_register:
            # Start the application
            mock_application.start()
            
            # Verify that a shutdown hook was registered
            mock_register.assert_called_once_with(mock_application.stop)

    def test_application_context_manager(self, mock_application):
        """Test that the application can be used as a context manager."""
        # Use the application as a context manager
        with mock_application as app:
            # Verify that the application was started
            mock_application.start.assert_called_once()
            assert app.is_running is True
        
        # Verify that the application was stopped after the context
        mock_application.stop.assert_called_once()