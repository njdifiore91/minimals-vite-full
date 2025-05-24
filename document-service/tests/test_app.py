#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the core application setup module (app.py) of the Document Service.

This file verifies that the application correctly initializes all components,
loads configuration, sets up logging, and creates service instances. It ensures
the application can start and stop properly and handles errors appropriately.
"""

import os
import pytest
import logging
from unittest.mock import patch, MagicMock, AsyncMock

# Import the application module
try:
    from src.app import Application, get_app, get_application
    from src.config import app_config
    from src.services import QueueService, StorageService, ClassificationService, DocumentRoutingService
except ImportError:
    # If imports fail, the tests will use the mocks from conftest.py
    pass


# ===== Application Initialization Tests =====

@pytest.mark.asyncio
async def test_application_initialization(app_config_fixture, monkeypatch):
    """Test that the Application class initializes correctly."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    monkeypatch.setattr("src.app.QueueService", MagicMock)
    monkeypatch.setattr("src.app.StorageService", MagicMock)
    monkeypatch.setattr("src.app.ClassificationService", MagicMock)
    monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    
    # Create a mock for the API routers
    mock_health_router = MagicMock()
    mock_status_router = MagicMock()
    mock_diagnostics_router = MagicMock()
    mock_documents_router = MagicMock()
    
    monkeypatch.setattr("src.app.health_router", mock_health_router)
    monkeypatch.setattr("src.app.status_router", mock_status_router)
    monkeypatch.setattr("src.app.diagnostics_router", mock_diagnostics_router)
    monkeypatch.setattr("src.app.documents_router", mock_documents_router)
    
    # Initialize the application
    app = Application()
    
    # Verify that the logger was set up
    assert app.logger == mock_logger
    mock_logger.info.assert_any_call("Initializing Document Service application")
    
    # Verify that the configuration was loaded
    assert app.config is not None
    
    # Verify that the FastAPI app was created
    assert app.app is not None
    
    # Verify that the services were initialized
    assert isinstance(app.queue_service, MagicMock)
    assert isinstance(app.storage_service, MagicMock)
    assert isinstance(app.classification_service, MagicMock)
    assert isinstance(app.document_routing_service, MagicMock)
    
    # Verify that the initialized flag is set
    assert app.initialized is True
    assert app.running is False
    
    # Verify that the success message was logged
    mock_logger.info.assert_any_call("Document Service application initialized successfully")


@pytest.mark.asyncio
async def test_application_initialization_with_environment_variables(monkeypatch):
    """Test that the Application class loads configuration from environment variables."""
    # Set environment variables for configuration
    monkeypatch.setenv("SERVICE_NAME", "document-service-env-test")
    monkeypatch.setenv("SERVICE_VERSION", "1.0.0-env-test")
    monkeypatch.setenv("SERVICE_ENVIRONMENT", "test")
    monkeypatch.setenv("LOGGING_LEVEL", "DEBUG")
    
    # Mock the app_config.load_config method
    mock_config = MagicMock()
    mock_config.environment = "test"
    mock_config.version = "1.0.0-env-test"
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Mock the setup_logger function
        mock_logger = MagicMock()
        monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
        
        # Mock the service classes and FastAPI
        monkeypatch.setattr("src.app.QueueService", MagicMock)
        monkeypatch.setattr("src.app.StorageService", MagicMock)
        monkeypatch.setattr("src.app.ClassificationService", MagicMock)
        monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
        monkeypatch.setattr("src.app.FastAPI", MagicMock)
        monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
        
        # Mock the API routers
        monkeypatch.setattr("src.app.health_router", MagicMock())
        monkeypatch.setattr("src.app.status_router", MagicMock())
        monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
        monkeypatch.setattr("src.app.documents_router", MagicMock())
        
        # Initialize the application
        app = Application()
        
        # Verify that the configuration was loaded with environment variables
        assert app.config == mock_config
        assert app.config.version == "1.0.0-env-test"
        assert app.config.environment == "test"
        
        # Verify that the environment was logged
        mock_logger.info.assert_any_call("Loaded configuration for environment: test")


# ===== FastAPI Application Tests =====

@pytest.mark.asyncio
async def test_create_fastapi_app(monkeypatch):
    """Test that the _create_fastapi_app method creates a properly configured FastAPI instance."""
    # Mock FastAPI and middleware
    mock_fastapi = MagicMock()
    mock_fastapi_instance = MagicMock()
    mock_fastapi.return_value = mock_fastapi_instance
    
    monkeypatch.setattr("src.app.FastAPI", mock_fastapi)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock())
    
    # Mock the API routers
    mock_health_router = MagicMock()
    mock_status_router = MagicMock()
    mock_diagnostics_router = MagicMock()
    mock_documents_router = MagicMock()
    
    monkeypatch.setattr("src.app.health_router", mock_health_router)
    monkeypatch.setattr("src.app.status_router", mock_status_router)
    monkeypatch.setattr("src.app.diagnostics_router", mock_diagnostics_router)
    monkeypatch.setattr("src.app.documents_router", mock_documents_router)
    
    # Mock other dependencies
    monkeypatch.setattr("src.app.setup_logger", lambda: MagicMock())
    monkeypatch.setattr("src.app.QueueService", MagicMock)
    monkeypatch.setattr("src.app.StorageService", MagicMock)
    monkeypatch.setattr("src.app.ClassificationService", MagicMock)
    monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
    
    # Create a mock config
    mock_config = MagicMock()
    mock_config.environment = "test"
    mock_config.version = "1.0.0-test"
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Verify that FastAPI was called with the correct parameters
        mock_fastapi.assert_called_once_with(
            title="Document Service API",
            description="API for the Document Service microservice",
            version=mock_config.version,
            docs_url="/api/docs",  # Should be available in test environment
            redoc_url="/api/redoc"  # Should be available in test environment
        )
        
        # Verify that CORS middleware was added
        mock_fastapi_instance.add_middleware.assert_called_once()
        
        # Verify that the routers were included
        assert mock_fastapi_instance.include_router.call_count >= 3
        
        # Verify that the diagnostics router is included in test environment
        mock_fastapi_instance.include_router.assert_any_call(mock_diagnostics_router, prefix="/diagnostics")


@pytest.mark.asyncio
async def test_create_fastapi_app_production(monkeypatch):
    """Test that the _create_fastapi_app method configures FastAPI correctly for production."""
    # Mock FastAPI and middleware
    mock_fastapi = MagicMock()
    mock_fastapi_instance = MagicMock()
    mock_fastapi.return_value = mock_fastapi_instance
    
    monkeypatch.setattr("src.app.FastAPI", mock_fastapi)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock())
    
    # Mock the API routers
    mock_health_router = MagicMock()
    mock_status_router = MagicMock()
    mock_diagnostics_router = MagicMock()
    mock_documents_router = MagicMock()
    
    monkeypatch.setattr("src.app.health_router", mock_health_router)
    monkeypatch.setattr("src.app.status_router", mock_status_router)
    monkeypatch.setattr("src.app.diagnostics_router", mock_diagnostics_router)
    monkeypatch.setattr("src.app.documents_router", mock_documents_router)
    
    # Mock other dependencies
    monkeypatch.setattr("src.app.setup_logger", lambda: MagicMock())
    monkeypatch.setattr("src.app.QueueService", MagicMock)
    monkeypatch.setattr("src.app.StorageService", MagicMock)
    monkeypatch.setattr("src.app.ClassificationService", MagicMock)
    monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
    
    # Create a mock config for production
    mock_config = MagicMock()
    mock_config.environment = "production"
    mock_config.version = "1.0.0"
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Verify that FastAPI was called with the correct parameters for production
        mock_fastapi.assert_called_once_with(
            title="Document Service API",
            description="API for the Document Service microservice",
            version=mock_config.version,
            docs_url=None,  # Should be disabled in production
            redoc_url=None  # Should be disabled in production
        )
        
        # Verify that the diagnostics router is NOT included in production
        for call in mock_fastapi_instance.include_router.call_args_list:
            args, kwargs = call
            if args[0] == mock_diagnostics_router:
                pytest.fail("Diagnostics router should not be included in production")


# ===== Application Lifecycle Tests =====

@pytest.mark.asyncio
async def test_application_start(monkeypatch):
    """Test that the start method initializes connections and starts services."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    mock_queue_service = MagicMock()
    mock_queue_service.connect = AsyncMock()
    mock_queue_service.start_consuming = AsyncMock()
    
    mock_storage_service = MagicMock()
    mock_storage_service.connect = AsyncMock()
    
    mock_classification_service = MagicMock()
    mock_classification_service.initialize = AsyncMock()
    
    mock_document_routing_service = MagicMock()
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", lambda: mock_document_routing_service)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    mock_config.environment = "test"
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Start the application
        await app.start()
        
        # Verify that the connections were established
        mock_queue_service.connect.assert_called_once()
        mock_storage_service.connect.assert_called_once()
        mock_classification_service.initialize.assert_called_once()
        
        # Verify that message consumption was started
        mock_queue_service.start_consuming.assert_called_once()
        
        # Verify that the running flag is set
        assert app.running is True
        
        # Verify that the success message was logged
        mock_logger.info.assert_any_call("Document Service application started successfully")


@pytest.mark.asyncio
async def test_application_start_already_running(monkeypatch):
    """Test that the start method handles the case when the application is already running."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    mock_queue_service = MagicMock()
    mock_storage_service = MagicMock()
    mock_classification_service = MagicMock()
    mock_document_routing_service = MagicMock()
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", lambda: mock_document_routing_service)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Set the running flag to True
        app.running = True
        
        # Start the application
        await app.start()
        
        # Verify that no connections were established
        assert not mock_queue_service.connect.called
        assert not mock_storage_service.connect.called
        assert not mock_classification_service.initialize.called
        
        # Verify that the warning was logged
        mock_logger.warning.assert_called_with("Application is already running")


@pytest.mark.asyncio
async def test_application_start_not_initialized(monkeypatch):
    """Test that the start method raises an error when the application is not initialized."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    monkeypatch.setattr("src.app.QueueService", MagicMock)
    monkeypatch.setattr("src.app.StorageService", MagicMock)
    monkeypatch.setattr("src.app.ClassificationService", MagicMock)
    monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Set the initialized flag to False
        app.initialized = False
        
        # Start the application and expect an error
        with pytest.raises(RuntimeError, match="Application must be initialized before starting"):
            await app.start()


@pytest.mark.asyncio
async def test_application_start_connection_error(monkeypatch):
    """Test that the start method handles connection errors properly."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    mock_queue_service = MagicMock()
    mock_queue_service.connect = AsyncMock(side_effect=Exception("Connection error"))
    mock_queue_service.disconnect = AsyncMock()
    
    mock_storage_service = MagicMock()
    mock_storage_service.connect = AsyncMock()
    mock_storage_service.disconnect = AsyncMock()
    
    mock_classification_service = MagicMock()
    mock_classification_service.initialize = AsyncMock()
    mock_classification_service.cleanup = AsyncMock()
    
    mock_document_routing_service = MagicMock()
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", lambda: mock_document_routing_service)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Start the application and expect an error
        with pytest.raises(Exception, match="Connection error"):
            await app.start()
        
        # Verify that the error was logged
        mock_logger.error.assert_called_with("Failed to start Document Service application: Connection error")
        
        # Verify that stop was called to clean up
        mock_queue_service.disconnect.assert_called_once()


@pytest.mark.asyncio
async def test_application_stop(monkeypatch):
    """Test that the stop method closes connections and performs cleanup."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    mock_queue_service = MagicMock()
    mock_queue_service.connect = AsyncMock()
    mock_queue_service.start_consuming = AsyncMock()
    mock_queue_service.stop_consuming = AsyncMock()
    mock_queue_service.disconnect = AsyncMock()
    
    mock_storage_service = MagicMock()
    mock_storage_service.connect = AsyncMock()
    mock_storage_service.disconnect = AsyncMock()
    
    mock_classification_service = MagicMock()
    mock_classification_service.initialize = AsyncMock()
    mock_classification_service.cleanup = AsyncMock()
    
    mock_document_routing_service = MagicMock()
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", lambda: mock_document_routing_service)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Set the running flag to True
        app.running = True
        
        # Stop the application
        await app.stop()
        
        # Verify that the connections were closed
        mock_queue_service.stop_consuming.assert_called_once()
        mock_queue_service.disconnect.assert_called_once()
        mock_storage_service.disconnect.assert_called_once()
        mock_classification_service.cleanup.assert_called_once()
        
        # Verify that the running flag is set to False
        assert app.running is False
        
        # Verify that the success message was logged
        mock_logger.info.assert_any_call("Document Service application stopped successfully")


@pytest.mark.asyncio
async def test_application_stop_with_errors(monkeypatch):
    """Test that the stop method handles errors during shutdown."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes with errors
    mock_queue_service = MagicMock()
    mock_queue_service.stop_consuming = AsyncMock(side_effect=Exception("Error stopping queue"))
    mock_queue_service.disconnect = AsyncMock(side_effect=Exception("Error disconnecting queue"))
    
    mock_storage_service = MagicMock()
    mock_storage_service.disconnect = AsyncMock(side_effect=Exception("Error disconnecting storage"))
    
    mock_classification_service = MagicMock()
    mock_classification_service.cleanup = AsyncMock(side_effect=Exception("Error cleaning up classification"))
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Stop the application
        await app.stop()
        
        # Verify that all errors were logged
        mock_logger.error.assert_any_call("Error stopping queue consumption: Error stopping queue")
        mock_logger.error.assert_any_call("Error disconnecting from RabbitMQ: Error disconnecting queue")
        mock_logger.error.assert_any_call("Error disconnecting from S3: Error disconnecting storage")
        mock_logger.error.assert_any_call("Error cleaning up classification service: Error cleaning up classification")
        
        # Verify that the running flag is set to False despite errors
        assert app.running is False
        
        # Verify that the success message was still logged
        mock_logger.info.assert_any_call("Document Service application stopped successfully")


# ===== Document Processing Tests =====

@pytest.mark.asyncio
async def test_process_document(monkeypatch):
    """Test that the _process_document method correctly processes documents."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    mock_queue_service = MagicMock()
    mock_queue_service.publish_classification_result = AsyncMock()
    mock_queue_service.handle_processing_error = AsyncMock()
    
    mock_storage_service = MagicMock()
    mock_storage_service.download_document = AsyncMock(return_value=b"test document content")
    
    mock_classification_service = MagicMock()
    mock_classification_result = MagicMock()
    mock_classification_service.classify_document = AsyncMock(return_value=mock_classification_result)
    
    mock_document_routing_service = MagicMock()
    mock_routing_result = MagicMock()
    mock_document_routing_service.route_document.return_value = mock_routing_result
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", lambda: mock_document_routing_service)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Create a test message
        test_message = {
            "document_id": "test-doc-123",
            "s3_key": "test-document.pdf",
            "metadata": {
                "filename": "test-document.pdf",
                "size": 1024,
                "content_type": "application/pdf"
            }
        }
        
        # Process the document
        await app._process_document(test_message)
        
        # Verify that the document was downloaded
        mock_storage_service.download_document.assert_called_once_with(test_message)
        
        # Verify that the document was classified
        mock_classification_service.classify_document.assert_called_once_with(b"test document content")
        
        # Verify that the document was routed
        mock_document_routing_service.route_document.assert_called_once_with(mock_classification_result)
        
        # Verify that the classification result was published
        mock_queue_service.publish_classification_result.assert_called_once_with(mock_routing_result)
        
        # Verify that the success message was logged
        mock_logger.info.assert_any_call("Document processed successfully: test-doc-123")


@pytest.mark.asyncio
async def test_process_document_error(monkeypatch):
    """Test that the _process_document method handles errors correctly."""
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes with an error
    mock_queue_service = MagicMock()
    mock_queue_service.handle_processing_error = AsyncMock()
    
    mock_storage_service = MagicMock()
    mock_storage_service.download_document = AsyncMock(side_effect=Exception("Download error"))
    
    mock_classification_service = MagicMock()
    mock_document_routing_service = MagicMock()
    
    monkeypatch.setattr("src.app.QueueService", lambda config: mock_queue_service)
    monkeypatch.setattr("src.app.StorageService", lambda config: mock_storage_service)
    monkeypatch.setattr("src.app.ClassificationService", lambda config: mock_classification_service)
    monkeypatch.setattr("src.app.DocumentRoutingService", lambda: mock_document_routing_service)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Create a test message
        test_message = {
            "document_id": "test-doc-123",
            "s3_key": "test-document.pdf",
            "metadata": {
                "filename": "test-document.pdf",
                "size": 1024,
                "content_type": "application/pdf"
            }
        }
        
        # Process the document
        await app._process_document(test_message)
        
        # Verify that the error was logged
        mock_logger.error.assert_called_with("Error processing document: Download error")
        
        # Verify that the error was handled
        mock_queue_service.handle_processing_error.assert_called_once_with(test_message, "Download error")


# ===== Signal Handler Tests =====

@pytest.mark.asyncio
async def test_setup_signal_handlers(monkeypatch):
    """Test that the setup_signal_handlers method sets up signal handlers correctly."""
    # Mock the signal module
    mock_signal = MagicMock()
    monkeypatch.setattr("src.app.signal", mock_signal)
    
    # Mock the setup_logger function
    mock_logger = MagicMock()
    monkeypatch.setattr("src.app.setup_logger", lambda: mock_logger)
    
    # Mock the service classes
    monkeypatch.setattr("src.app.QueueService", MagicMock)
    monkeypatch.setattr("src.app.StorageService", MagicMock)
    monkeypatch.setattr("src.app.ClassificationService", MagicMock)
    monkeypatch.setattr("src.app.DocumentRoutingService", MagicMock)
    
    # Mock FastAPI and router imports
    monkeypatch.setattr("src.app.FastAPI", MagicMock)
    monkeypatch.setattr("src.app.CORSMiddleware", MagicMock)
    monkeypatch.setattr("src.app.health_router", MagicMock())
    monkeypatch.setattr("src.app.status_router", MagicMock())
    monkeypatch.setattr("src.app.diagnostics_router", MagicMock())
    monkeypatch.setattr("src.app.documents_router", MagicMock())
    
    # Create a mock config
    mock_config = MagicMock()
    
    with patch("src.app.app_config.load_config", return_value=mock_config):
        # Initialize the application
        app = Application()
        
        # Set up signal handlers
        app.setup_signal_handlers()
        
        # Verify that signal handlers were set up
        assert mock_signal.signal.call_count == 2
        mock_signal.signal.assert_any_call(mock_signal.SIGINT, mock_signal.signal.call_args[0][1])
        mock_signal.signal.assert_any_call(mock_signal.SIGTERM, mock_signal.signal.call_args[0][1])
        
        # Verify that the success message was logged
        mock_logger.info.assert_any_call("Signal handlers set up for graceful shutdown")


# ===== Global Application Instance Tests =====

@pytest.mark.asyncio
async def test_get_app(monkeypatch):
    """Test that the get_app function returns a singleton Application instance."""
    # Mock the Application class
    mock_application = MagicMock()
    monkeypatch.setattr("src.app.Application", lambda: mock_application)
    
    # Reset the global app_instance
    import src.app
    src.app.app_instance = None
    
    # Get the application instance
    app1 = src.app.get_app()
    app2 = src.app.get_app()
    
    # Verify that the same instance was returned
    assert app1 is app2
    assert app1 is mock_application


@pytest.mark.asyncio
async def test_get_application_dependency(monkeypatch):
    """Test that the get_application dependency returns the global Application instance."""
    # Mock the get_app function
    mock_app = MagicMock()
    mock_get_app = MagicMock(return_value=mock_app)
    monkeypatch.setattr("src.app.get_app", mock_get_app)
    
    # Get the application instance via the dependency
    import src.app
    app = src.app.get_application()
    
    # Verify that get_app was called
    mock_get_app.assert_called_once()
    
    # Verify that the correct instance was returned
    assert app is mock_app


@pytest.mark.asyncio
async def test_app_export(monkeypatch):
    """Test that the app export provides the FastAPI application instance."""
    # Mock the Application class
    mock_fastapi_app = MagicMock()
    mock_application = MagicMock()
    mock_application.app = mock_fastapi_app
    
    # Mock the get_app function
    mock_get_app = MagicMock(return_value=mock_application)
    monkeypatch.setattr("src.app.get_app", mock_get_app)
    
    # Get the exported FastAPI app
    import src.app
    app = src.app.app
    
    # Verify that the correct instance was exported
    assert app is mock_fastapi_app