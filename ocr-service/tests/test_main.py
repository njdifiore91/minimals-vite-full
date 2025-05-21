import os
import signal
import pytest
from unittest.mock import patch, MagicMock, call
import tensorflow as tf

# Import the main module - this will be patched in tests
with patch('tensorflow.config.list_physical_devices'):
    with patch('tensorflow.config.experimental.set_memory_growth'):
        from ocr_service.src.main import main, initialize_app, setup_rabbitmq, setup_s3, load_tensorflow_models, signal_handler


@pytest.fixture
def mock_app():
    """Fixture for mocked application instance"""
    app_mock = MagicMock()
    app_mock.start = MagicMock()
    app_mock.stop = MagicMock()
    return app_mock


@pytest.fixture
def mock_gpu_devices():
    """Fixture for mocked GPU devices"""
    gpu_device = MagicMock()
    gpu_device.name = 'GPU:0'
    return [gpu_device]


@pytest.fixture
def mock_environment_variables():
    """Fixture to set required environment variables for testing"""
    original_env = os.environ.copy()
    
    # Set test environment variables
    os.environ['RABBITMQ_HOST'] = 'test-rabbitmq'
    os.environ['RABBITMQ_PORT'] = '5672'
    os.environ['RABBITMQ_USERNAME'] = 'test-user'
    os.environ['RABBITMQ_PASSWORD'] = 'test-password'
    os.environ['RABBITMQ_EXCHANGE'] = 'mca.documents'
    os.environ['RABBITMQ_QUEUE'] = 'data-extraction'
    os.environ['S3_ENDPOINT'] = 'test-s3-endpoint'
    os.environ['S3_BUCKET'] = 'mca-documents-test'
    os.environ['S3_ACCESS_KEY'] = 'test-access-key'
    os.environ['S3_SECRET_KEY'] = 'test-secret-key'
    os.environ['S3_REGION'] = 'us-east-1'
    os.environ['LOG_LEVEL'] = 'INFO'
    os.environ['ENVIRONMENT'] = 'test'
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


class TestMain:
    """Test cases for the main module of the OCR Service"""

    @patch('ocr_service.src.main.initialize_app')
    @patch('ocr_service.src.main.setup_rabbitmq')
    @patch('ocr_service.src.main.setup_s3')
    @patch('ocr_service.src.main.load_tensorflow_models')
    @patch('ocr_service.src.main.signal.signal')
    def test_main_initializes_all_components(self, mock_signal, mock_load_models, 
                                           mock_setup_s3, mock_setup_rabbitmq, 
                                           mock_initialize_app, mock_environment_variables):
        """Test that main initializes all required components"""
        # Setup
        mock_app = MagicMock()
        mock_initialize_app.return_value = mock_app
        
        # Execute
        main()
        
        # Assert
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        mock_setup_s3.assert_called_once_with(mock_app)
        mock_load_models.assert_called_once_with(mock_app)
        mock_app.start.assert_called_once()
        
        # Verify signal handlers are registered
        assert mock_signal.call_count >= 2
        mock_signal.assert_has_calls([
            call(signal.SIGINT, signal_handler),
            call(signal.SIGTERM, signal_handler)
        ], any_order=True)

    @patch('ocr_service.src.app.App')
    def test_initialize_app_creates_app_instance(self, mock_app_class, mock_environment_variables):
        """Test that initialize_app creates and returns an App instance"""
        # Setup
        mock_app_instance = MagicMock()
        mock_app_class.return_value = mock_app_instance
        
        # Execute
        app = initialize_app()
        
        # Assert
        mock_app_class.assert_called_once()
        assert app == mock_app_instance

    @patch('ocr_service.src.main.pika')
    def test_setup_rabbitmq_establishes_connection(self, mock_pika, mock_app, mock_environment_variables):
        """Test that setup_rabbitmq establishes a connection to RabbitMQ"""
        # Setup
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_pika.ConnectionParameters.return_value = MagicMock()
        mock_pika.BlockingConnection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # Execute
        setup_rabbitmq(mock_app)
        
        # Assert
        mock_pika.ConnectionParameters.assert_called_once_with(
            host='test-rabbitmq',
            port=5672,
            credentials=mock_pika.PlainCredentials('test-user', 'test-password')
        )
        mock_pika.BlockingConnection.assert_called_once()
        mock_connection.channel.assert_called_once()
        mock_channel.exchange_declare.assert_called_once_with(
            exchange='mca.documents',
            exchange_type='fanout',
            durable=True
        )
        mock_channel.queue_declare.assert_called_once_with(
            queue='data-extraction',
            durable=True
        )
        mock_channel.queue_bind.assert_called_once_with(
            exchange='mca.documents',
            queue='data-extraction'
        )
        mock_app.set_rabbitmq_connection.assert_called_once_with(mock_connection)
        mock_app.set_rabbitmq_channel.assert_called_once_with(mock_channel)

    @patch('ocr_service.src.main.boto3')
    def test_setup_s3_initializes_client(self, mock_boto3, mock_app, mock_environment_variables):
        """Test that setup_s3 initializes an S3 client"""
        # Setup
        mock_s3_client = MagicMock()
        mock_boto3.client.return_value = mock_s3_client
        
        # Execute
        setup_s3(mock_app)
        
        # Assert
        mock_boto3.client.assert_called_once_with(
            's3',
            endpoint_url='test-s3-endpoint',
            aws_access_key_id='test-access-key',
            aws_secret_access_key='test-secret-key',
            region_name='us-east-1'
        )
        mock_app.set_s3_client.assert_called_once_with(mock_s3_client)

    @patch('tensorflow.config.list_physical_devices')
    @patch('tensorflow.config.experimental.set_memory_growth')
    def test_load_tensorflow_models_with_gpu(self, mock_set_memory_growth, 
                                           mock_list_physical_devices, 
                                           mock_app, mock_gpu_devices):
        """Test that load_tensorflow_models configures GPU and loads models"""
        # Setup
        mock_list_physical_devices.return_value = mock_gpu_devices
        
        # Execute
        load_tensorflow_models(mock_app)
        
        # Assert
        mock_list_physical_devices.assert_called_once_with('GPU')
        mock_set_memory_growth.assert_called_once_with(mock_gpu_devices[0], True)
        mock_app.load_ocr_models.assert_called_once()

    @patch('tensorflow.config.list_physical_devices')
    def test_load_tensorflow_models_no_gpu(self, mock_list_physical_devices, mock_app):
        """Test that load_tensorflow_models raises an error when no GPU is available"""
        # Setup
        mock_list_physical_devices.return_value = []
        
        # Execute and Assert
        with pytest.raises(RuntimeError) as excinfo:
            load_tensorflow_models(mock_app)
        
        assert "GPU is required for OCR processing" in str(excinfo.value)
        mock_list_physical_devices.assert_called_once_with('GPU')
        mock_app.load_ocr_models.assert_not_called()

    def test_signal_handler_stops_app(self, mock_app):
        """Test that signal_handler stops the app and exits"""
        # Setup
        mock_signal_num = signal.SIGTERM
        mock_frame = None
        
        # Execute with exit patched to prevent actual exit
        with patch('sys.exit') as mock_exit:
            signal_handler(mock_signal_num, mock_frame, app=mock_app)
        
        # Assert
        mock_app.stop.assert_called_once()
        mock_exit.assert_called_once_with(0)

    @patch('ocr_service.src.main.initialize_app')
    @patch('ocr_service.src.main.setup_rabbitmq')
    def test_main_handles_rabbitmq_connection_error(self, mock_setup_rabbitmq, 
                                                 mock_initialize_app, 
                                                 mock_environment_variables):
        """Test that main handles RabbitMQ connection errors gracefully"""
        # Setup
        mock_app = MagicMock()
        mock_initialize_app.return_value = mock_app
        mock_setup_rabbitmq.side_effect = Exception("RabbitMQ connection error")
        
        # Execute with exit patched to prevent actual exit
        with patch('sys.exit') as mock_exit:
            main()
        
        # Assert
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        mock_app.stop.assert_called_once()
        mock_exit.assert_called_once_with(1)

    @patch('ocr_service.src.main.initialize_app')
    @patch('ocr_service.src.main.setup_rabbitmq')
    @patch('ocr_service.src.main.setup_s3')
    def test_main_handles_s3_connection_error(self, mock_setup_s3, 
                                           mock_setup_rabbitmq, 
                                           mock_initialize_app, 
                                           mock_environment_variables):
        """Test that main handles S3 connection errors gracefully"""
        # Setup
        mock_app = MagicMock()
        mock_initialize_app.return_value = mock_app
        mock_setup_s3.side_effect = Exception("S3 connection error")
        
        # Execute with exit patched to prevent actual exit
        with patch('sys.exit') as mock_exit:
            main()
        
        # Assert
        mock_initialize_app.assert_called_once()
        mock_setup_rabbitmq.assert_called_once_with(mock_app)
        mock_setup_s3.assert_called_once_with(mock_app)
        mock_app.stop.assert_called_once()
        mock_exit.assert_called_once_with(1)


if __name__ == "__main__":
    pytest.main(['-xvs', __file__])