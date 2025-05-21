import os
import sys
import pytest
import logging
from unittest.mock import patch, MagicMock, call
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Add path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the app module
from src.app import DocumentServiceApp
from src.types.config import ServiceConfig, ModelConfig, RabbitMQConfig, S3Config, LoggingConfig


@pytest.fixture
def mock_env_vars():
    """Fixture to set up environment variables for testing."""
    env_vars = {
        'SERVICE_NAME': 'document-service',
        'SERVICE_VERSION': '1.0.0',
        'LOG_LEVEL': 'INFO',
        'RABBITMQ_HOST': 'rabbitmq.example.com',
        'RABBITMQ_PORT': '5672',
        'RABBITMQ_EXCHANGE': 'mca.documents',
        'RABBITMQ_QUEUE': 'document-processing',
        'RABBITMQ_ROUTING_KEY': 'documents',
        'RABBITMQ_USE_TLS': 'true',
        'RABBITMQ_CERT_PATH': '/path/to/cert',
        'S3_ENDPOINT_URL': 'https://s3.example.com',
        'S3_REGION_NAME': 'us-east-1',
        'S3_BUCKET_NAME': 'mca-documents-staging',
        'S3_USE_ENCRYPTION': 'true',
        'S3_ENCRYPTION_TYPE': 'AES256',
        'MODEL_PATH': '/path/to/models',
        'SVM_MODEL_FILE': 'svm_model.pkl',
        'RF_MODEL_FILE': 'rf_model.pkl',
        'CONFIDENCE_THRESHOLD': '0.85',
        'ENVIRONMENT': 'staging'
    }
    
    # Save original environment
    original_env = os.environ.copy()
    
    # Set environment variables for test
    for key, value in env_vars.items():
        os.environ[key] = value
    
    yield env_vars
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_logger():
    """Fixture to provide a mock logger."""
    logger = MagicMock(spec=logging.Logger)
    return logger


@pytest.fixture
def mock_queue_service():
    """Fixture to provide a mock QueueService instance."""
    queue_service = MagicMock()
    return queue_service


@pytest.fixture
def mock_storage_service():
    """Fixture to provide a mock StorageService instance."""
    storage_service = MagicMock()
    return storage_service


@pytest.fixture
def mock_classification_service():
    """Fixture to provide a mock ClassificationService instance."""
    classification_service = MagicMock()
    return classification_service


@pytest.fixture
def mock_document_routing_service():
    """Fixture to provide a mock DocumentRoutingService instance."""
    routing_service = MagicMock()
    return routing_service


@pytest.fixture
def app_instance(mock_env_vars):
    """Fixture to provide a DocumentServiceApp instance."""
    with patch('src.app.logging') as mock_logging:
        app = DocumentServiceApp()
        yield app


class TestDocumentServiceApp:
    """Test suite for the DocumentServiceApp class."""

    def test_init(self, app_instance):
        """Test that the application initializes correctly."""
        # Verify app attributes are initialized
        assert app_instance.config is None
        assert app_instance.logger is None
        assert app_instance.queue_service is None
        assert app_instance.storage_service is None
        assert app_instance.classification_service is None
        assert app_instance.document_routing_service is None
        assert app_instance.api_app is None
        assert app_instance.running is False

    @patch('src.app.logging')
    def test_init_logger(self, mock_logging, app_instance):
        """Test logger initialization with different log levels."""
        # Test with INFO level
        os.environ['LOG_LEVEL'] = 'INFO'
        app_instance.init_logger()
        
        # Verify logger was configured
        mock_logging.basicConfig.assert_called_once()
        assert mock_logging.basicConfig.call_args[1]['level'] == logging.INFO
        
        # Verify logger was created
        mock_logging.getLogger.assert_called_once_with('document-service')
        assert app_instance.logger == mock_logging.getLogger.return_value
        
        # Test with DEBUG level
        mock_logging.reset_mock()
        os.environ['LOG_LEVEL'] = 'DEBUG'
        app_instance.init_logger()
        
        # Verify logger was configured with DEBUG level
        assert mock_logging.basicConfig.call_args[1]['level'] == logging.DEBUG
        
        # Test with invalid level (should default to INFO)
        mock_logging.reset_mock()
        os.environ['LOG_LEVEL'] = 'INVALID'
        app_instance.init_logger()
        
        # Verify logger was configured with INFO level
        assert mock_logging.basicConfig.call_args[1]['level'] == logging.INFO

    def test_load_config(self, app_instance, mock_env_vars):
        """Test configuration loading from environment variables."""
        # Initialize logger first
        with patch('src.app.logging'):
            app_instance.init_logger()
        
        # Load configuration
        app_instance.load_config()
        
        # Verify config was loaded
        assert app_instance.config is not None
        
        # Verify service config
        assert app_instance.config['service_name'] == 'document-service'
        assert app_instance.config['service_version'] == '1.0.0'
        assert app_instance.config['environment'] == 'staging'
        
        # Verify RabbitMQ config
        assert app_instance.config['rabbitmq']['host'] == 'rabbitmq.example.com'
        assert app_instance.config['rabbitmq']['port'] == 5672
        assert app_instance.config['rabbitmq']['exchange'] == 'mca.documents'
        assert app_instance.config['rabbitmq']['queue'] == 'document-processing'
        assert app_instance.config['rabbitmq']['routing_key'] == 'documents'
        assert app_instance.config['rabbitmq']['use_tls'] is True
        assert app_instance.config['rabbitmq']['cert_path'] == '/path/to/cert'
        
        # Verify S3 config
        assert app_instance.config['s3']['endpoint_url'] == 'https://s3.example.com'
        assert app_instance.config['s3']['region_name'] == 'us-east-1'
        assert app_instance.config['s3']['bucket_name'] == 'mca-documents-staging'
        assert app_instance.config['s3']['use_encryption'] is True
        assert app_instance.config['s3']['encryption_type'] == 'AES256'
        
        # Verify model config
        assert app_instance.config['model']['path'] == '/path/to/models'
        assert app_instance.config['model']['svm_model_file'] == 'svm_model.pkl'
        assert app_instance.config['model']['rf_model_file'] == 'rf_model.pkl'
        assert app_instance.config['model']['confidence_threshold'] == 0.85

    def test_load_config_missing_required_vars(self, app_instance):
        """Test configuration loading with missing required variables."""
        # Initialize logger first
        with patch('src.app.logging'):
            app_instance.init_logger()
        
        # Remove required environment variables
        os.environ.pop('SERVICE_NAME', None)
        os.environ.pop('RABBITMQ_HOST', None)
        
        # Attempt to load configuration
        with pytest.raises(ValueError, match="Required environment variable 'SERVICE_NAME' is missing"):
            app_instance.load_config()
        
        # Set SERVICE_NAME but keep RABBITMQ_HOST missing
        os.environ['SERVICE_NAME'] = 'document-service'
        
        # Attempt to load configuration
        with pytest.raises(ValueError, match="Required environment variable 'RABBITMQ_HOST' is missing"):
            app_instance.load_config()

    def test_load_config_invalid_values(self, app_instance, mock_env_vars):
        """Test configuration loading with invalid values."""
        # Initialize logger first
        with patch('src.app.logging'):
            app_instance.init_logger()
        
        # Set invalid values
        os.environ['RABBITMQ_PORT'] = 'not-a-number'
        os.environ['RABBITMQ_USE_TLS'] = 'not-a-boolean'
        os.environ['CONFIDENCE_THRESHOLD'] = 'not-a-float'
        
        # Load configuration
        app_instance.load_config()
        
        # Verify default values were used
        assert app_instance.config['rabbitmq']['port'] == 5672  # Default port
        assert app_instance.config['rabbitmq']['use_tls'] is False  # Default for invalid boolean
        assert app_instance.config['model']['confidence_threshold'] == 0.9  # Default threshold

    @patch('src.services.QueueService')
    @patch('src.services.StorageService')
    @patch('src.services.ClassificationService')
    @patch('src.services.DocumentRoutingService')
    def test_create_services(self, mock_routing_service_class, mock_classification_service_class,
                           mock_storage_service_class, mock_queue_service_class,
                           app_instance, mock_queue_service, mock_storage_service,
                           mock_classification_service, mock_document_routing_service):
        """Test service creation and dependency injection."""
        # Configure mocks
        mock_queue_service_class.return_value = mock_queue_service
        mock_storage_service_class.return_value = mock_storage_service
        mock_classification_service_class.return_value = mock_classification_service
        mock_routing_service_class.return_value = mock_document_routing_service
        
        # Initialize logger and load config
        with patch('src.app.logging'):
            app_instance.init_logger()
            app_instance.load_config()
        
        # Create services
        app_instance.create_services()
        
        # Verify services were created
        mock_queue_service_class.assert_called_once_with(app_instance)
        mock_storage_service_class.assert_called_once_with(app_instance)
        mock_classification_service_class.assert_called_once_with(app_instance)
        mock_routing_service_class.assert_called_once_with(app_instance, mock_classification_service)
        
        # Verify services were assigned
        assert app_instance.queue_service == mock_queue_service
        assert app_instance.storage_service == mock_storage_service
        assert app_instance.classification_service == mock_classification_service
        assert app_instance.document_routing_service == mock_document_routing_service

    @patch('src.app.FastAPI')
    @patch('src.api.router')
    def test_create_api_app(self, mock_router, mock_fastapi_class, app_instance):
        """Test FastAPI application creation."""
        # Configure mocks
        mock_api_app = MagicMock()
        mock_fastapi_class.return_value = mock_api_app
        
        # Initialize logger and load config
        with patch('src.app.logging'):
            app_instance.init_logger()
            app_instance.load_config()
        
        # Create API app
        app_instance.create_api_app()
        
        # Verify FastAPI app was created
        mock_fastapi_class.assert_called_once_with(
            title="Document Service API",
            description="API for the Document Service microservice",
            version=app_instance.config['service_version']
        )
        
        # Verify router was included
        mock_api_app.include_router.assert_called_once_with(mock_router)
        
        # Verify API app was assigned
        assert app_instance.api_app == mock_api_app

    def test_start(self, app_instance):
        """Test application start method."""
        # Initialize logger and load config
        with patch('src.app.logging'):
            app_instance.init_logger()
            app_instance.load_config()
        
        # Create mock services
        app_instance.queue_service = MagicMock()
        app_instance.storage_service = MagicMock()
        app_instance.classification_service = MagicMock()
        app_instance.document_routing_service = MagicMock()
        app_instance.api_app = MagicMock()
        app_instance.logger = MagicMock()
        
        # Start the application
        app_instance.start()
        
        # Verify running flag was set
        assert app_instance.running is True
        
        # Verify logger was called
        app_instance.logger.info.assert_called_with("Document Service started")

    def test_stop(self, app_instance):
        """Test application stop method."""
        # Initialize logger and load config
        with patch('src.app.logging'):
            app_instance.init_logger()
            app_instance.load_config()
        
        # Create mock services
        app_instance.queue_service = MagicMock()
        app_instance.storage_service = MagicMock()
        app_instance.classification_service = MagicMock()
        app_instance.document_routing_service = MagicMock()
        app_instance.api_app = MagicMock()
        app_instance.logger = MagicMock()
        
        # Set running flag
        app_instance.running = True
        
        # Stop the application
        app_instance.stop()
        
        # Verify running flag was cleared
        assert app_instance.running is False
        
        # Verify logger was called
        app_instance.logger.info.assert_called_with("Document Service stopped")

    def test_health_check_endpoints(self, app_instance):
        """Test health check endpoints for Kubernetes probes."""
        # Initialize logger and load config
        with patch('src.app.logging'):
            app_instance.init_logger()
            app_instance.load_config()
        
        # Create API app
        with patch('src.app.FastAPI') as mock_fastapi_class:
            mock_api_app = MagicMock()
            mock_fastapi_class.return_value = mock_api_app
            
            with patch('src.api.router'):
                app_instance.create_api_app()
        
        # Create mock services
        app_instance.queue_service = MagicMock()
        app_instance.storage_service = MagicMock()
        app_instance.classification_service = MagicMock()
        app_instance.document_routing_service = MagicMock()
        
        # Configure service mocks for health checks
        app_instance.queue_service.is_connected.return_value = True
        app_instance.storage_service.is_initialized.return_value = True
        app_instance.classification_service.is_ready.return_value = True
        
        # Create test client
        client = TestClient(app_instance.api_app)
        
        # Test liveness endpoint
        with patch('fastapi.testclient.TestClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {"status": "alive"}
            
            response = client.get("/health/liveness")
            
            assert response.status_code == 200
            assert response.json() == {"status": "alive"}
        
        # Test readiness endpoint - all services ready
        with patch('fastapi.testclient.TestClient.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {
                "status": "ready",
                "rabbitmq": True,
                "s3": True,
                "classification": True
            }
            
            response = client.get("/health/readiness")
            
            assert response.status_code == 200
            assert response.json() == {
                "status": "ready",
                "rabbitmq": True,
                "s3": True,
                "classification": True
            }
        
        # Test readiness endpoint - RabbitMQ not ready
        app_instance.queue_service.is_connected.return_value = False
        
        with patch('fastapi.testclient.TestClient.get') as mock_get:
            mock_get.return_value.status_code = 503
            mock_get.return_value.json.return_value = {
                "status": "not ready",
                "rabbitmq": False,
                "s3": True,
                "classification": True
            }
            
            response = client.get("/health/readiness")
            
            assert response.status_code == 503
            assert response.json() == {
                "status": "not ready",
                "rabbitmq": False,
                "s3": True,
                "classification": True
            }

    def test_initialize(self, app_instance):
        """Test the complete initialization sequence."""
        # Mock all dependencies
        with patch('src.app.logging'), 
             patch('src.services.QueueService'), 
             patch('src.services.StorageService'), 
             patch('src.services.ClassificationService'), 
             patch('src.services.DocumentRoutingService'), 
             patch('src.app.FastAPI'), 
             patch('src.api.router'):
            
            # Initialize the application
            app_instance.initialize()
            
            # Verify initialization sequence
            assert app_instance.logger is not None
            assert app_instance.config is not None
            assert app_instance.queue_service is not None
            assert app_instance.storage_service is not None
            assert app_instance.classification_service is not None
            assert app_instance.document_routing_service is not None
            assert app_instance.api_app is not None

    def test_initialize_with_error(self, app_instance):
        """Test initialization with an error."""
        # Mock logger
        with patch('src.app.logging') as mock_logging:
            mock_logger = MagicMock()
            mock_logging.getLogger.return_value = mock_logger
            
            # Force an error during config loading
            with patch.object(app_instance, 'load_config', side_effect=ValueError("Configuration error")):
                
                # Initialize the application
                with pytest.raises(ValueError, match="Configuration error"):
                    app_instance.initialize()
                
                # Verify error was logged
                mock_logger.error.assert_called_with("Failed to initialize application: Configuration error")


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])