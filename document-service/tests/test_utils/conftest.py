"""
Pytest configuration file for the test_utils module.

This file contains fixtures and configuration for testing the utility functions
of the Document Service. It provides common test fixtures, mocks, and setup/teardown
functions that can be reused across all test files in the module.
"""

import os
import json
import logging
import tempfile
import datetime
from typing import Dict, Any, List, Optional, Callable, Tuple, BinaryIO
from unittest.mock import MagicMock, patch, Mock

import pytest
import boto3
import pika
import numpy as np
from botocore.exceptions import ClientError
from moto import mock_s3
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ===== Environment Setup =====

@pytest.fixture(scope='session')
def test_env_vars():
    """
    Set up environment variables for testing.
    
    This fixture sets up environment variables needed for testing the Document Service
    utilities. It ensures that tests run with consistent configuration regardless of
    the actual environment.
    """
    # Store original environment variables
    original_env = {}
    test_vars = {
        'DOCUMENT_SERVICE_ENV': 'test',
        'S3_BUCKET_NAME': 'test-mca-documents',
        'S3_ENDPOINT_URL': 'http://localhost:4566',  # LocalStack endpoint
        'RABBITMQ_HOST': 'localhost',
        'RABBITMQ_PORT': '5672',
        'RABBITMQ_USERNAME': 'guest',
        'RABBITMQ_PASSWORD': 'guest',
        'RABBITMQ_EXCHANGE': 'test.mca.documents',
        'RABBITMQ_QUEUE': 'test-document-processing',
        'LOG_LEVEL': 'INFO',
        'MODEL_PATH': '/tmp/test-models'
    }
    
    # Save original values and set test values
    for key, value in test_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value
    
    yield test_vars
    
    # Restore original environment
    for key in test_vars:
        if key in original_env:
            os.environ[key] = original_env[key]
        else:
            del os.environ[key]


# ===== S3 Mocking =====

@pytest.fixture
def mock_s3_client():
    """
    Create a mocked S3 client using moto.
    
    This fixture provides a mocked S3 client that can be used for testing S3 operations
    without making actual AWS API calls. It creates a test bucket and yields the client.
    """
    with mock_s3():
        # Create S3 client
        s3_client = boto3.client(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        
        # Create test bucket
        bucket_name = os.environ['S3_BUCKET_NAME']
        s3_client.create_bucket(Bucket=bucket_name)
        
        yield s3_client


@pytest.fixture
def mock_s3_resource():
    """
    Create a mocked S3 resource using moto.
    
    This fixture provides a mocked S3 resource that can be used for testing S3 operations
    without making actual AWS API calls. It creates a test bucket and yields the resource.
    """
    with mock_s3():
        # Create S3 resource
        s3_resource = boto3.resource(
            's3',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        
        # Create test bucket
        bucket_name = os.environ['S3_BUCKET_NAME']
        s3_resource.create_bucket(Bucket=bucket_name)
        
        yield s3_resource


@pytest.fixture
def s3_test_bucket(mock_s3_client):
    """
    Get the name of the test S3 bucket.
    
    This fixture returns the name of the test S3 bucket created by the mock_s3_client fixture.
    """
    return os.environ['S3_BUCKET_NAME']


@pytest.fixture
def s3_document_key():
    """
    Generate a test document key for S3 operations.
    
    This fixture generates a unique document key that can be used for testing S3 operations.
    """
    return f"documents/test/test-document-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}.pdf"


@pytest.fixture
def sample_document_bytes():
    """
    Generate sample document bytes for testing.
    
    This fixture generates a sample PDF document as bytes that can be used for testing
    document processing functions.
    """
    # This is a minimal valid PDF file as bytes
    return b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF'


@pytest.fixture
def sample_document_file(sample_document_bytes):
    """
    Create a temporary file with sample document content.
    
    This fixture creates a temporary file with sample PDF content that can be used
    for testing file operations.
    """
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
        temp_file.write(sample_document_bytes)
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Clean up the temporary file
    if os.path.exists(temp_file_path):
        os.unlink(temp_file_path)


@pytest.fixture
def sample_classification_metadata():
    """
    Generate sample classification metadata for testing.
    
    This fixture generates sample classification metadata that can be used for testing
    document classification functions.
    """
    return {
        'document_type': 'loan_application',
        'classification_confidence': 0.95,
        'page_count': 3,
        'contains_signature': True,
        'requires_review': False,
        'extracted_fields': {
            'applicant_name': 'John Doe',
            'business_name': 'Acme Corporation',
            'application_date': '2023-05-01'
        }
    }


# ===== RabbitMQ Mocking =====

@pytest.fixture
def mock_rabbitmq_connection():
    """
    Mock a RabbitMQ connection for testing.
    
    This fixture provides a mocked RabbitMQ connection that can be used for testing
    RabbitMQ operations without connecting to an actual RabbitMQ server.
    """
    with patch('pika.BlockingConnection') as mock_connection:
        # Create mock connection and channel
        mock_channel = MagicMock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        # Configure mock channel methods
        mock_channel.basic_publish.return_value = None
        mock_channel.basic_consume.return_value = None
        mock_channel.basic_ack.return_value = None
        mock_channel.basic_nack.return_value = None
        mock_channel.basic_reject.return_value = None
        mock_channel.queue_declare.return_value = pika.frame.Method(
            1, pika.spec.Queue.DeclareOk(queue=os.environ['RABBITMQ_QUEUE'], message_count=0, consumer_count=0)
        )
        
        yield mock_connection.return_value


@pytest.fixture
def mock_rabbitmq_channel(mock_rabbitmq_connection):
    """
    Mock a RabbitMQ channel for testing.
    
    This fixture provides a mocked RabbitMQ channel that can be used for testing
    RabbitMQ operations without connecting to an actual RabbitMQ server.
    """
    return mock_rabbitmq_connection.channel.return_value


@pytest.fixture
def mock_rabbitmq_client():
    """
    Mock the RabbitMQ client for testing.
    
    This fixture patches the get_rabbitmq_client function to return a mock client
    that can be used for testing RabbitMQ operations.
    """
    with patch('document_service.config.rabbitmq_config.get_rabbitmq_client') as mock_get_client:
        # Create mock client
        mock_client = MagicMock()
        mock_client.connection = MagicMock()
        mock_client.channel = MagicMock()
        mock_get_client.return_value = mock_client
        
        yield mock_client


@pytest.fixture
def sample_rabbitmq_message():
    """
    Generate a sample RabbitMQ message for testing.
    
    This fixture generates a sample message that can be used for testing RabbitMQ
    message handling functions.
    """
    return {
        'document_id': 'doc-12345',
        'document_type': 'loan_application',
        's3_path': 'test-mca-documents/documents/loan_application/20230501-123456-doc-12345.pdf',
        'metadata': {
            'sender': 'test@example.com',
            'received_at': '2023-05-01T12:34:56Z',
            'subject': 'Loan Application',
            'filename': 'application.pdf'
        },
        'confidence': 0.95,
        'classification_timestamp': int(datetime.datetime.now().timestamp()),
        'service': 'document-service',
        'requires_review': False
    }


@pytest.fixture
def mock_pika_basic_deliver():
    """
    Mock a pika.spec.Basic.Deliver object for testing.
    
    This fixture creates a mock Basic.Deliver object that can be used for testing
    message handling functions.
    """
    mock_deliver = MagicMock(spec=pika.spec.Basic.Deliver)
    mock_deliver.delivery_tag = 1
    mock_deliver.exchange = os.environ['RABBITMQ_EXCHANGE']
    mock_deliver.routing_key = 'document.classify'
    mock_deliver.redelivered = False
    return mock_deliver


@pytest.fixture
def mock_pika_properties():
    """
    Mock a pika.spec.BasicProperties object for testing.
    
    This fixture creates a mock BasicProperties object that can be used for testing
    message handling functions.
    """
    mock_props = MagicMock(spec=pika.spec.BasicProperties)
    mock_props.content_type = 'application/json'
    mock_props.content_encoding = None
    mock_props.headers = {'source': 'email-service'}
    mock_props.delivery_mode = 2  # persistent
    mock_props.priority = None
    mock_props.correlation_id = None
    mock_props.reply_to = None
    mock_props.expiration = None
    mock_props.message_id = 'msg-12345'
    mock_props.timestamp = int(datetime.datetime.now().timestamp())
    mock_props.type = None
    mock_props.user_id = None
    mock_props.app_id = 'email-service'
    mock_props.cluster_id = None
    return mock_props


# ===== ML Model Mocking =====

@pytest.fixture
def mock_random_forest_classifier():
    """
    Mock a RandomForestClassifier for testing.
    
    This fixture provides a mocked RandomForestClassifier that can be used for testing
    document classification functions without training an actual model.
    """
    mock_classifier = MagicMock(spec=RandomForestClassifier)
    mock_classifier.predict.return_value = np.array(['loan_application'])
    mock_classifier.predict_proba.return_value = np.array([[0.05, 0.95]])
    mock_classifier.classes_ = np.array(['tax_return', 'loan_application'])
    return mock_classifier


@pytest.fixture
def mock_svm_classifier():
    """
    Mock an SVM classifier for testing.
    
    This fixture provides a mocked SVM classifier that can be used for testing
    document classification functions without training an actual model.
    """
    mock_classifier = MagicMock(spec=SVC)
    mock_classifier.predict.return_value = np.array(['loan_application'])
    mock_classifier.predict_proba.return_value = np.array([[0.1, 0.9]])
    mock_classifier.classes_ = np.array(['tax_return', 'loan_application'])
    return mock_classifier


@pytest.fixture
def mock_document_classifier(mock_random_forest_classifier, mock_svm_classifier):
    """
    Mock a DocumentClassifier for testing.
    
    This fixture provides a mocked DocumentClassifier that can be used for testing
    document classification functions without using actual ML models.
    """
    mock_classifier = MagicMock()
    mock_classifier.classify.return_value = ('loan_application', 0.95)
    mock_classifier.get_confidence.return_value = 0.95
    mock_classifier.rf_classifier = mock_random_forest_classifier
    mock_classifier.svm_classifier = mock_svm_classifier
    return mock_classifier


# ===== File and Document Fixtures =====

@pytest.fixture
def sample_document_types():
    """
    Provide a list of sample document types for testing.
    
    This fixture returns a list of document types that can be used for testing
    document classification and routing functions.
    """
    return [
        'loan_application',
        'tax_return',
        'bank_statement',
        'profit_loss',
        'balance_sheet',
        'identity_document',
        'business_license',
        'utility_bill',
        'invoice',
        'other'
    ]


@pytest.fixture
def create_test_document_factory():
    """
    Factory function for creating test documents with different types and content.
    
    This fixture provides a factory function that can create test documents with
    different types and content for testing document processing functions.
    """
    def _create_document(doc_type='loan_application', pages=1, with_signature=True):
        """
        Create a test document with specified parameters.
        
        Args:
            doc_type (str): Type of document to create
            pages (int): Number of pages in the document
            with_signature (bool): Whether to include a signature
            
        Returns:
            tuple: (file_path, metadata)
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            # Create a minimal PDF with specified number of pages
            pdf_content = b'%PDF-1.4\n'
            for i in range(pages):
                pdf_content += f"Page {i+1} content\n".encode()
            if with_signature:
                pdf_content += b"Signature: John Doe\n"
            pdf_content += b"%%EOF"
            
            temp_file.write(pdf_content)
            temp_file_path = temp_file.name
        
        # Create metadata
        metadata = {
            'document_type': doc_type,
            'page_count': pages,
            'contains_signature': with_signature,
            'created_at': datetime.datetime.now().isoformat(),
            'file_size': len(pdf_content)
        }
        
        return temp_file_path, metadata
    
    return _create_document


@pytest.fixture
def create_test_image_factory():
    """
    Factory function for creating test image files.
    
    This fixture provides a factory function that can create test image files
    for testing document processing functions.
    """
    def _create_image(width=100, height=100, format='PNG'):
        """
        Create a test image with specified parameters.
        
        Args:
            width (int): Width of the image
            height (int): Height of the image
            format (str): Image format (PNG, JPEG, etc.)
            
        Returns:
            str: Path to the created image file
        """
        try:
            from PIL import Image
            
            # Create a new image with a white background
            image = Image.new('RGB', (width, height), color='white')
            
            # Save the image to a temporary file
            suffix = f'.{format.lower()}'
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
                image.save(temp_file, format=format)
                temp_file_path = temp_file.name
            
            return temp_file_path
        except ImportError:
            # If PIL is not available, create a dummy file
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
                temp_file.write(b'\x89PNG\r\n\x1a\n')
                temp_file_path = temp_file.name
            
            return temp_file_path
    
    return _create_image


# ===== Error and Exception Fixtures =====

@pytest.fixture
def s3_client_error_factory():
    """
    Factory function for creating S3 client errors.
    
    This fixture provides a factory function that can create different types of
    S3 client errors for testing error handling in S3 operations.
    """
    def _create_error(error_code='NoSuchKey', operation_name='GetObject'):
        """
        Create an S3 client error with specified parameters.
        
        Args:
            error_code (str): S3 error code
            operation_name (str): S3 operation name
            
        Returns:
            ClientError: Boto3 ClientError exception
        """
        return ClientError(
            {
                'Error': {
                    'Code': error_code,
                    'Message': f"S3 Error: {error_code}"
                }
            },
            operation_name
        )
    
    return _create_error


@pytest.fixture
def rabbitmq_exception_factory():
    """
    Factory function for creating RabbitMQ exceptions.
    
    This fixture provides a factory function that can create different types of
    RabbitMQ exceptions for testing error handling in RabbitMQ operations.
    """
    def _create_exception(exception_type='ConnectionClosed', reply_code=0, reply_text=''):
        """
        Create a RabbitMQ exception with specified parameters.
        
        Args:
            exception_type (str): Type of exception to create
            reply_code (int): Reply code for the exception
            reply_text (str): Reply text for the exception
            
        Returns:
            Exception: RabbitMQ exception
        """
        exceptions = {
            'ConnectionClosed': pika.exceptions.ConnectionClosed,
            'ConnectionClosedByBroker': pika.exceptions.ConnectionClosedByBroker,
            'ConnectionBlockedTimeout': pika.exceptions.ConnectionBlockedTimeout,
            'ChannelClosed': pika.exceptions.ChannelClosed,
            'ChannelClosedByBroker': pika.exceptions.ChannelClosedByBroker,
            'AMQPConnectionError': pika.exceptions.AMQPConnectionError
        }
        
        exception_class = exceptions.get(exception_type, pika.exceptions.AMQPError)
        
        if exception_type in ['ConnectionClosed', 'ChannelClosed']:
            return exception_class(reply_code, reply_text)
        elif exception_type in ['ConnectionClosedByBroker', 'ChannelClosedByBroker']:
            return exception_class(reply_code, reply_text)
        else:
            return exception_class()
    
    return _create_exception


# ===== Test Coverage Configuration =====

def pytest_configure(config):
    """
    Configure pytest for the test session.
    
    This function is called by pytest at the start of the test session and is used
    to configure test coverage reporting and other session-wide settings.
    """
    # Configure coverage reporting
    config.option.cov_source = ['document_service']
    config.option.cov_report = ['term', 'html']
    config.option.cov_config = '.coveragerc'
    
    # Set up logging for tests
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def pytest_sessionfinish(session, exitstatus):
    """
    Perform cleanup after the test session.
    
    This function is called by pytest at the end of the test session and is used
    to perform any necessary cleanup or reporting.
    """
    # Clean up any temporary files or resources
    for root, dirs, files in os.walk(tempfile.gettempdir()):
        for file in files:
            if file.startswith('test_document_') or file.startswith('test_image_'):
                try:
                    os.unlink(os.path.join(root, file))
                except (OSError, IOError):
                    pass


# ===== Utility Fixtures =====

@pytest.fixture
def mock_logger():
    """
    Mock a logger for testing.
    
    This fixture provides a mocked logger that can be used for testing logging
    functionality without actually writing to log files.
    """
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        # Configure mock logger methods
        mock_logger.debug = MagicMock()
        mock_logger.info = MagicMock()
        mock_logger.warning = MagicMock()
        mock_logger.error = MagicMock()
        mock_logger.critical = MagicMock()
        
        yield mock_logger


@pytest.fixture
def mock_time():
    """
    Mock the time module for testing.
    
    This fixture patches the time.time function to return a fixed timestamp,
    which is useful for testing functions that depend on the current time.
    """
    with patch('time.time') as mock_time:
        mock_time.return_value = 1620000000  # 2021-05-03 00:00:00 UTC
        yield mock_time


@pytest.fixture
def mock_uuid():
    """
    Mock the uuid module for testing.
    
    This fixture patches the uuid.uuid4 function to return a fixed UUID,
    which is useful for testing functions that generate UUIDs.
    """
    with patch('uuid.uuid4') as mock_uuid4:
        mock_uuid4.return_value = 'test-uuid-12345'
        yield mock_uuid4