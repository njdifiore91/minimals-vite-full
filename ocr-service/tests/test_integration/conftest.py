import os
import json
import pytest
import boto3
import tempfile
import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch
from moto import mock_s3

# Import OCR service modules
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from app import OCRServiceApp
from config import app_config, s3_config, rabbitmq_config, tensorflow_config
from models import base_model, typed_text_model, handwritten_text_model, hybrid_recognition_model
from services import ocr_service, queue_service, storage_service, field_extraction_service, confidence_service
from types.documents import DocumentType
from types.extraction import ConfidenceScore, ExtractedField, ExtractedData


# Constants for testing
TEST_BUCKET_NAME = 'mca-documents-test'
TEST_EXCHANGE_NAME = 'mca.documents.test'
TEST_QUEUE_NAME = 'data-extraction-test'


# ===== Mock RabbitMQ Fixtures =====

@pytest.fixture(scope="function")
def mock_rabbitmq_connection():
    """Mock RabbitMQ connection for testing."""
    with patch('services.queue_service.pika.BlockingConnection') as mock_connection:
        # Create mock channel
        mock_channel = MagicMock()
        mock_connection.return_value.channel.return_value = mock_channel
        
        # Setup mock methods
        mock_channel.exchange_declare = MagicMock()
        mock_channel.queue_declare = MagicMock(return_value=MagicMock(method=MagicMock(queue=TEST_QUEUE_NAME)))
        mock_channel.queue_bind = MagicMock()
        mock_channel.basic_consume = MagicMock()
        mock_channel.basic_publish = MagicMock()
        mock_channel.basic_ack = MagicMock()
        
        yield mock_connection, mock_channel


@pytest.fixture(scope="function")
def mock_queue_service(mock_rabbitmq_connection):
    """Mock queue service for testing."""
    mock_connection, mock_channel = mock_rabbitmq_connection
    
    with patch('app.queue_service.QueueService') as MockQueueService:
        mock_queue_svc = MagicMock()
        MockQueueService.return_value = mock_queue_svc
        
        # Setup mock methods
        mock_queue_svc.connect = MagicMock(return_value=True)
        mock_queue_svc.publish_message = MagicMock()
        mock_queue_svc.consume_messages = MagicMock()
        mock_queue_svc.close = MagicMock()
        
        # Add method to simulate message receipt
        def simulate_message(message_body, content_type='application/json'):
            callback = mock_channel.basic_consume.call_args[1]['on_message_callback']
            
            # Create mock delivery channel and properties
            mock_ch = MagicMock()
            mock_method = MagicMock(delivery_tag='test-tag')
            mock_properties = MagicMock(content_type=content_type)
            
            # Convert message to bytes if it's not already
            if isinstance(message_body, dict):
                message_body = json.dumps(message_body).encode('utf-8')
            elif isinstance(message_body, str):
                message_body = message_body.encode('utf-8')
            
            # Call the callback
            callback(mock_ch, mock_method, mock_properties, message_body)
            
        mock_queue_svc.simulate_message = simulate_message
        
        yield mock_queue_svc


# ===== Mock S3 Fixtures =====

@pytest.fixture(scope="function")
def mock_s3_client():
    """Create a mock S3 client using moto."""
    with mock_s3():
        # Create S3 client
        s3_client = boto3.client('s3', region_name='us-east-1')
        
        # Create test bucket
        s3_client.create_bucket(Bucket=TEST_BUCKET_NAME)
        
        yield s3_client


@pytest.fixture(scope="function")
def mock_storage_service(mock_s3_client):
    """Mock storage service for testing."""
    with patch('app.storage_service.StorageService') as MockStorageService:
        mock_storage_svc = MagicMock()
        MockStorageService.return_value = mock_storage_svc
        
        # Setup mock methods
        mock_storage_svc.connect = MagicMock(return_value=True)
        mock_storage_svc.download_document = MagicMock()
        mock_storage_svc.upload_extraction_results = MagicMock()
        mock_storage_svc.close = MagicMock()
        
        # Add method to upload test document to S3
        def upload_test_document(document_path, key=None):
            if key is None:
                key = os.path.basename(document_path)
            
            with open(document_path, 'rb') as f:
                mock_s3_client.put_object(
                    Bucket=TEST_BUCKET_NAME,
                    Key=key,
                    Body=f.read()
                )
            return key
        
        mock_storage_svc.upload_test_document = upload_test_document
        
        # Add method to download document from S3
        def download_test_document(key, output_path=None):
            if output_path is None:
                output_path = os.path.join(tempfile.gettempdir(), key)
            
            response = mock_s3_client.get_object(Bucket=TEST_BUCKET_NAME, Key=key)
            with open(output_path, 'wb') as f:
                f.write(response['Body'].read())
            
            return output_path
        
        mock_storage_svc.download_test_document = download_test_document
        
        yield mock_storage_svc


# ===== Test Document Fixtures =====

@pytest.fixture(scope="session")
def test_data_dir():
    """Return the path to the test data directory."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'test_data'))


@pytest.fixture(scope="session")
def test_documents(test_data_dir):
    """Provide paths to test documents of different types."""
    # Load metadata for test documents
    metadata_path = os.path.join(test_data_dir, 'metadata.json')
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Create dictionary of document paths by type
    documents = {
        'typed': {},
        'handwritten': {},
        'mixed': {}
    }
    
    # Typed documents
    typed_dir = os.path.join(test_data_dir, 'typed_documents')
    if os.path.exists(typed_dir):
        for doc_type in os.listdir(typed_dir):
            type_dir = os.path.join(typed_dir, doc_type)
            if os.path.isdir(type_dir):
                documents['typed'][doc_type] = []
                for filename in os.listdir(type_dir):
                    if filename.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                        doc_path = os.path.join(type_dir, filename)
                        documents['typed'][doc_type].append(doc_path)
    
    # Handwritten documents
    handwritten_dir = os.path.join(test_data_dir, 'handwritten_documents')
    if os.path.exists(handwritten_dir):
        for doc_type in os.listdir(handwritten_dir):
            type_dir = os.path.join(handwritten_dir, doc_type)
            if os.path.isdir(type_dir):
                documents['handwritten'][doc_type] = []
                for filename in os.listdir(type_dir):
                    if filename.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                        doc_path = os.path.join(type_dir, filename)
                        documents['handwritten'][doc_type].append(doc_path)
    
    # Mixed documents
    mixed_dir = os.path.join(test_data_dir, 'mixed_documents')
    if os.path.exists(mixed_dir):
        for doc_type in os.listdir(mixed_dir):
            type_dir = os.path.join(mixed_dir, doc_type)
            if os.path.isdir(type_dir):
                documents['mixed'][doc_type] = []
                for filename in os.listdir(type_dir):
                    if filename.endswith(('.pdf', '.png', '.jpg', '.jpeg', '.tiff')):
                        doc_path = os.path.join(type_dir, filename)
                        documents['mixed'][doc_type].append(doc_path)
    
    return {'documents': documents, 'metadata': metadata}


@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# ===== Mock OCR Service Fixtures =====

@pytest.fixture(scope="function")
def mock_tensorflow_models():
    """Mock TensorFlow models for testing."""
    with patch('models.typed_text_model.TypedTextModel.load_model') as mock_typed_load, \
         patch('models.handwritten_text_model.HandwrittenTextModel.load_model') as mock_handwritten_load, \
         patch('models.hybrid_recognition_model.HybridRecognitionModel.load_model') as mock_hybrid_load:
        
        # Mock the model loading methods
        mock_typed_load.return_value = MagicMock()
        mock_handwritten_load.return_value = MagicMock()
        mock_hybrid_load.return_value = MagicMock()
        
        yield


@pytest.fixture(scope="function")
def mock_ocr_service(mock_tensorflow_models):
    """Mock OCR service for testing."""
    with patch('app.ocr_service.OCRService') as MockOCRService:
        mock_ocr_svc = MagicMock()
        MockOCRService.return_value = mock_ocr_svc
        
        # Setup mock methods
        mock_ocr_svc.initialize = MagicMock(return_value=True)
        mock_ocr_svc.process_document = MagicMock()
        mock_ocr_svc.close = MagicMock()
        
        # Add method to simulate OCR processing with configurable results
        def simulate_ocr_processing(document_path, document_type=DocumentType.APPLICATION, confidence=0.95):
            # Create sample extraction results based on document type
            extracted_fields = []
            
            if document_type == DocumentType.APPLICATION:
                extracted_fields = [
                    ExtractedField(name="business_name", value="Dollar Funding LLC", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="tax_id", value="12-3456789", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="address", value="123 Main St, New York, NY 10001", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="requested_amount", value="50000", confidence=ConfidenceScore(confidence)),
                ]
            elif document_type == DocumentType.TAX_RETURN:
                extracted_fields = [
                    ExtractedField(name="tax_year", value="2022", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="gross_income", value="250000", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="net_income", value="75000", confidence=ConfidenceScore(confidence)),
                ]
            elif document_type == DocumentType.BANK_STATEMENT:
                extracted_fields = [
                    ExtractedField(name="account_number", value="****1234", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="statement_date", value="2023-01-15", confidence=ConfidenceScore(confidence)),
                    ExtractedField(name="ending_balance", value="35678.90", confidence=ConfidenceScore(confidence)),
                ]
            
            # Create extraction result
            extraction_result = ExtractedData(
                document_type=document_type,
                fields=extracted_fields,
                metadata={
                    "filename": os.path.basename(document_path),
                    "processing_time": 1.25,
                    "model_version": "1.0.0"
                }
            )
            
            return extraction_result
        
        mock_ocr_svc.simulate_ocr_processing = simulate_ocr_processing
        
        yield mock_ocr_svc


# ===== Application Fixture =====

@pytest.fixture(scope="function")
def mock_app(mock_queue_service, mock_storage_service, mock_ocr_service):
    """Create a mock OCR service application for testing."""
    with patch('app.OCRServiceApp') as MockApp:
        mock_app_instance = MagicMock()
        MockApp.return_value = mock_app_instance
        
        # Setup mock attributes
        mock_app_instance.queue_service = mock_queue_service
        mock_app_instance.storage_service = mock_storage_service
        mock_app_instance.ocr_service = mock_ocr_service
        
        # Setup mock methods
        mock_app_instance.start = MagicMock()
        mock_app_instance.stop = MagicMock()
        mock_app_instance.process_document = MagicMock()
        
        yield mock_app_instance


# ===== Helper Functions =====

@pytest.fixture(scope="session")
def verify_extraction_result():
    """Helper function to verify OCR extraction results."""
    def _verify(result, expected_fields=None, min_confidence=0.8):
        """Verify that the extraction result contains the expected fields with sufficient confidence.
        
        Args:
            result: The ExtractedData object to verify
            expected_fields: Dictionary of field names and expected values
            min_confidence: Minimum acceptable confidence score (0.0-1.0)
            
        Returns:
            tuple: (is_valid, errors) where is_valid is a boolean and errors is a list of error messages
        """
        errors = []
        
        # Check that result is an ExtractedData object
        if not isinstance(result, ExtractedData):
            errors.append(f"Result is not an ExtractedData object: {type(result)}")
            return False, errors
        
        # Check that fields exist
        if not result.fields:
            errors.append("No fields found in extraction result")
            return False, errors
        
        # Check expected fields if provided
        if expected_fields:
            for field_name, expected_value in expected_fields.items():
                # Find the field in the result
                field = next((f for f in result.fields if f.name == field_name), None)
                
                if field is None:
                    errors.append(f"Expected field '{field_name}' not found in extraction result")
                    continue
                
                # Check field value
                if field.value != expected_value:
                    errors.append(f"Field '{field_name}' has value '{field.value}', expected '{expected_value}'")
                
                # Check confidence
                if field.confidence.value < min_confidence:
                    errors.append(f"Field '{field_name}' has confidence {field.confidence.value}, which is below minimum {min_confidence}")
        
        # Check all fields have sufficient confidence
        low_confidence_fields = [f for f in result.fields if f.confidence.value < min_confidence]
        if low_confidence_fields:
            field_names = [f.name for f in low_confidence_fields]
            errors.append(f"Fields with low confidence: {', '.join(field_names)}")
        
        return len(errors) == 0, errors
    
    return _verify


@pytest.fixture(scope="session")
def create_test_message():
    """Helper function to create test messages for RabbitMQ."""
    def _create_message(document_key, document_type=DocumentType.APPLICATION, source_bucket=TEST_BUCKET_NAME):
        """Create a test message for document processing.
        
        Args:
            document_key: S3 key of the document to process
            document_type: Type of document (from DocumentType enum)
            source_bucket: S3 bucket containing the document
            
        Returns:
            dict: Message payload as a dictionary
        """
        return {
            "document": {
                "bucket": source_bucket,
                "key": document_key,
                "type": document_type.value if isinstance(document_type, DocumentType) else document_type,
                "metadata": {
                    "application_id": "test-app-123",
                    "merchant_id": "test-merchant-456",
                    "upload_timestamp": "2023-05-21T10:30:00Z"
                }
            },
            "requestId": "test-request-789",
            "timestamp": "2023-05-21T10:30:05Z"
        }
    
    return _create_message