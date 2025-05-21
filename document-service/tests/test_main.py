import os
import signal
import pytest
from unittest.mock import patch, MagicMock, call
import sys

# Add path to allow importing from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the main module - this will be patched in tests
with patch('src.app.DocumentServiceApp'):
    from src.main import main, signal_handler, initialize_app, setup_rabbitmq, setup_s3_client, load_models, start_processing


@pytest.fixture
def mock_app():
    """Fixture to provide a mock DocumentServiceApp instance."""
    app = MagicMock()
    app.config = {
        'service_name': 'document-service',
        'rabbitmq': {
            'host': 'localhost',
            'port': 5672,
            'exchange': 'mca.documents',
            'queue': 'document-processing',
            'routing_key': 'documents',
            'use_tls': True,
            'cert_path': '/path/to/cert',
            'connection_attempts': 3,
            'retry_delay': 5
        },
        's3': {
            'endpoint_url': 'https://s3.example.com',
            'region_name': 'us-east-1',
            'bucket_name': 'mca-documents-staging',
            'use_encryption': True,
            'encryption_type': 'AES256'
        },
        'model': {
            'path': '/path/to/models',
            'svm_model_file': 'svm_model.pkl',
            'rf_model_file': 'rf_model.pkl',
            'confidence_threshold': 0.85
        }
    }
    return app


@pytest.fixture
def mock_queue_service():
    """Fixture to provide a mock QueueService instance."""
    queue_service = MagicMock()
    queue_service.connect.return_value = True
    return queue_service


@pytest.fixture
def mock_storage_service():
    """Fixture to provide a mock StorageService instance."""
    storage_service = MagicMock()
    storage_service.initialize.return_value = True
    return storage_service


@pytest.fixture
def mock_classification_service():
    """Fixture to provide a mock ClassificationService instance."""
    classification_service = MagicMock()
    classification_service.load_models.return_value = True
    return classification_service


@pytest.fixture
def mock_document_routing_service():
    """Fixture to provide a mock DocumentRoutingService instance."""
    routing_service = MagicMock()
    return routing_service


class TestMain:
    """Test suite for the main module of the Document Service."""

    @patch('src.app.DocumentServiceApp')
    def test_initialize_app(self, mock_app_class, mock_app):
        """Test that the application is initialized correctly."""
        mock_app_class.return_value = mock_app
        
        app = initialize_app()
        
        # Verify app was created
        mock_app_class.assert_called_once()
        
        # Verify app was returned
        assert app == mock_app
        
        # Verify logger was initialized
        mock_app.init_logger.assert_called_once()
        
        # Verify config was loaded
        mock_app.load_config.assert_called_once()

    @patch('src.services.QueueService')
    def test_setup_rabbitmq_success(self, mock_queue_service_class, mock_app, mock_queue_service):
        """Test successful RabbitMQ setup."""
        mock_queue_service_class.return_value = mock_queue_service
        
        result = setup_rabbitmq(mock_app)
        
        # Verify QueueService was created with app
        mock_queue_service_class.assert_called_once_with(mock_app)
        
        # Verify connection was attempted
        mock_queue_service.connect.assert_called_once_with(
            host=mock_app.config['rabbitmq']['host'],
            port=mock_app.config['rabbitmq']['port'],
            exchange=mock_app.config['rabbitmq']['exchange'],
            queue=mock_app.config['rabbitmq']['queue'],
            routing_key=mock_app.config['rabbitmq']['routing_key'],
            use_tls=mock_app.config['rabbitmq']['use_tls'],
            cert_path=mock_app.config['rabbitmq']['cert_path']
        )
        
        # Verify result is the queue service
        assert result == mock_queue_service

    @patch('src.services.QueueService')
    def test_setup_rabbitmq_failure(self, mock_queue_service_class, mock_app, mock_queue_service):
        """Test RabbitMQ setup failure with retry."""
        mock_queue_service_class.return_value = mock_queue_service
        
        # Configure connect to fail on first attempt, succeed on second
        mock_queue_service.connect.side_effect = [Exception("Connection failed"), True]
        
        with patch('time.sleep') as mock_sleep:
            result = setup_rabbitmq(mock_app)
        
        # Verify connection was attempted twice
        assert mock_queue_service.connect.call_count == 2
        
        # Verify sleep was called for retry delay
        mock_sleep.assert_called_once_with(mock_app.config['rabbitmq']['retry_delay'])
        
        # Verify result is the queue service
        assert result == mock_queue_service

    @patch('src.services.QueueService')
    def test_setup_rabbitmq_max_retries_exceeded(self, mock_queue_service_class, mock_app, mock_queue_service):
        """Test RabbitMQ setup failure with max retries exceeded."""
        mock_queue_service_class.return_value = mock_queue_service
        
        # Configure connect to always fail
        mock_queue_service.connect.side_effect = Exception("Connection failed")
        
        with patch('time.sleep') as mock_sleep:
            with pytest.raises(Exception, match="Failed to connect to RabbitMQ after maximum attempts"):
                setup_rabbitmq(mock_app)
        
        # Verify connection was attempted for the configured number of attempts
        assert mock_queue_service.connect.call_count == mock_app.config['rabbitmq']['connection_attempts']
        
        # Verify sleep was called for each retry
        assert mock_sleep.call_count == mock_app.config['rabbitmq']['connection_attempts'] - 1

    @patch('src.services.StorageService')
    def test_setup_s3_client_success(self, mock_storage_service_class, mock_app, mock_storage_service):
        """Test successful S3 client setup."""
        mock_storage_service_class.return_value = mock_storage_service
        
        result = setup_s3_client(mock_app)
        
        # Verify StorageService was created with app
        mock_storage_service_class.assert_called_once_with(mock_app)
        
        # Verify initialization was attempted
        mock_storage_service.initialize.assert_called_once_with(
            endpoint_url=mock_app.config['s3']['endpoint_url'],
            region_name=mock_app.config['s3']['region_name'],
            bucket_name=mock_app.config['s3']['bucket_name'],
            use_encryption=mock_app.config['s3']['use_encryption'],
            encryption_type=mock_app.config['s3']['encryption_type']
        )
        
        # Verify result is the storage service
        assert result == mock_storage_service

    @patch('src.services.StorageService')
    def test_setup_s3_client_failure(self, mock_storage_service_class, mock_app, mock_storage_service):
        """Test S3 client setup failure."""
        mock_storage_service_class.return_value = mock_storage_service
        
        # Configure initialize to fail
        mock_storage_service.initialize.side_effect = Exception("S3 initialization failed")
        
        with pytest.raises(Exception, match="Failed to initialize S3 client"):
            setup_s3_client(mock_app)
        
        # Verify initialization was attempted
        mock_storage_service.initialize.assert_called_once()

    @patch('src.services.ClassificationService')
    def test_load_models_success(self, mock_classification_service_class, mock_app, mock_classification_service):
        """Test successful model loading."""
        mock_classification_service_class.return_value = mock_classification_service
        
        result = load_models(mock_app)
        
        # Verify ClassificationService was created with app
        mock_classification_service_class.assert_called_once_with(mock_app)
        
        # Verify models were loaded
        mock_classification_service.load_models.assert_called_once_with(
            model_path=mock_app.config['model']['path'],
            svm_model_file=mock_app.config['model']['svm_model_file'],
            rf_model_file=mock_app.config['model']['rf_model_file'],
            confidence_threshold=mock_app.config['model']['confidence_threshold']
        )
        
        # Verify result is the classification service
        assert result == mock_classification_service

    @patch('src.services.ClassificationService')
    def test_load_models_failure(self, mock_classification_service_class, mock_app, mock_classification_service):
        """Test model loading failure."""
        mock_classification_service_class.return_value = mock_classification_service
        
        # Configure load_models to fail
        mock_classification_service.load_models.side_effect = Exception("Model loading failed")
        
        with pytest.raises(Exception, match="Failed to load classification models"):
            load_models(mock_app)
        
        # Verify load_models was attempted
        mock_classification_service.load_models.assert_called_once()

    def test_start_processing(self, mock_app, mock_queue_service, mock_classification_service, mock_document_routing_service):
        """Test starting the document processing."""
        start_processing(mock_app, mock_queue_service, mock_classification_service, mock_document_routing_service)
        
        # Verify start_consuming was called with the correct callback
        mock_queue_service.start_consuming.assert_called_once()
        
        # Get the callback function that was passed to start_consuming
        callback = mock_queue_service.start_consuming.call_args[0][0]
        
        # Test the callback with a sample message
        sample_message = {
            'document_id': '12345',
            'document_type': 'application_form',
            'storage_path': 's3://bucket/path/to/document.pdf'
        }
        
        # Call the callback with the sample message
        callback(sample_message)
        
        # Verify classification service was called with the message
        mock_classification_service.classify_document.assert_called_once_with(sample_message)
        
        # Verify routing service was called with the classification result
        mock_document_routing_service.route_document.assert_called_once_with(
            mock_classification_service.classify_document.return_value
        )

    def test_signal_handler(self, mock_app):
        """Test the signal handler for graceful shutdown."""
        # Create mock frame for signal handler (not used but required by signature)
        mock_frame = MagicMock()
        
        # Call signal handler with SIGTERM
        signal_handler(signal.SIGTERM, mock_frame, mock_app, mock_queue_service, mock_classification_service)
        
        # Verify queue service was stopped
        mock_queue_service.stop_consuming.assert_called_once()
        
        # Verify app was stopped
        mock_app.stop.assert_called_once()
        
        # Verify sys.exit was called with 0
        with patch('sys.exit') as mock_exit:
            signal_handler(signal.SIGTERM, mock_frame, mock_app, mock_queue_service, mock_classification_service)
            mock_exit.assert_called_once_with(0)

    @patch('src.main.initialize_app')
    @patch('src.main.setup_rabbitmq')
    @patch('src.main.setup_s3_client')
    @patch('src.main.load_models')
    @patch('src.main.start_processing')
    @patch('src.services.DocumentRoutingService')
    @patch('signal.signal')
    def test_main_success(self, mock_signal, mock_routing_service_class, mock_start_processing, 
                         mock_load_models, mock_setup_s3, mock_setup_rabbitmq, mock_initialize_app, 
                         mock_app, mock_queue_service, mock_storage_service, mock_classification_service):
        """Test successful execution of the main function."""
        # Configure mocks
        mock_initialize_app.return_value = mock_app
        mock_setup_rabbitmq.return_value = mock_queue_service
        mock_setup_s3.return_value = mock_storage_service
        mock_load_models.return_value = mock_classification_service
        mock_routing_service = MagicMock()
        mock_routing_service_class.return_value = mock_routing_service
        
        # Call main function
        main()
        
        # Verify initialization sequence
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        mock_setup_s3.assert_called_once_with(mock_app)
        mock_load_models.assert_called_once_with(mock_app)
        mock_routing_service_class.assert_called_once_with(mock_app, mock_classification_service)
        
        # Verify signal handlers were registered
        assert mock_signal.call_count == 2
        mock_signal.assert_has_calls([
            call(signal.SIGTERM, signal_handler, mock_app, mock_queue_service, mock_classification_service),
            call(signal.SIGINT, signal_handler, mock_app, mock_queue_service, mock_classification_service)
        ])
        
        # Verify processing was started
        mock_start_processing.assert_called_once_with(
            mock_app, mock_queue_service, mock_classification_service, mock_routing_service
        )

    @patch('src.main.initialize_app')
    @patch('src.main.setup_rabbitmq')
    def test_main_rabbitmq_failure(self, mock_setup_rabbitmq, mock_initialize_app, mock_app):
        """Test main function with RabbitMQ setup failure."""
        # Configure mocks
        mock_initialize_app.return_value = mock_app
        mock_setup_rabbitmq.side_effect = Exception("Failed to connect to RabbitMQ after maximum attempts")
        
        # Call main function and expect exception
        with pytest.raises(Exception, match="Failed to connect to RabbitMQ after maximum attempts"):
            main()
        
        # Verify initialization sequence
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        
        # Verify app was stopped due to error
        mock_app.stop.assert_called_once()

    @patch('src.main.initialize_app')
    @patch('src.main.setup_rabbitmq')
    @patch('src.main.setup_s3_client')
    def test_main_s3_failure(self, mock_setup_s3, mock_setup_rabbitmq, mock_initialize_app, 
                           mock_app, mock_queue_service):
        """Test main function with S3 setup failure."""
        # Configure mocks
        mock_initialize_app.return_value = mock_app
        mock_setup_rabbitmq.return_value = mock_queue_service
        mock_setup_s3.side_effect = Exception("Failed to initialize S3 client")
        
        # Call main function and expect exception
        with pytest.raises(Exception, match="Failed to initialize S3 client"):
            main()
        
        # Verify initialization sequence
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        mock_setup_s3.assert_called_once_with(mock_app)
        
        # Verify resources were cleaned up
        mock_queue_service.stop_consuming.assert_called_once()
        mock_app.stop.assert_called_once()

    @patch('src.main.initialize_app')
    @patch('src.main.setup_rabbitmq')
    @patch('src.main.setup_s3_client')
    @patch('src.main.load_models')
    def test_main_model_loading_failure(self, mock_load_models, mock_setup_s3, mock_setup_rabbitmq, 
                                      mock_initialize_app, mock_app, mock_queue_service, mock_storage_service):
        """Test main function with model loading failure."""
        # Configure mocks
        mock_initialize_app.return_value = mock_app
        mock_setup_rabbitmq.return_value = mock_queue_service
        mock_setup_s3.return_value = mock_storage_service
        mock_load_models.side_effect = Exception("Failed to load classification models")
        
        # Call main function and expect exception
        with pytest.raises(Exception, match="Failed to load classification models"):
            main()
        
        # Verify initialization sequence
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        mock_setup_s3.assert_called_once_with(mock_app)
        mock_load_models.assert_called_once_with(mock_app)
        
        # Verify resources were cleaned up
        mock_queue_service.stop_consuming.assert_called_once()
        mock_app.stop.assert_called_once()


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])