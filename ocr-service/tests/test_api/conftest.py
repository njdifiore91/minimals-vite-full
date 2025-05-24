import json
import os
import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
from pydantic import BaseModel, ValidationError
from typing import Dict, List, Any, Optional, Union

# Import the necessary modules from the OCR service
# These imports will be adjusted based on the actual structure of the OCR service
from src.app import create_app
from src.api import router as api_router
from src.config import app_config, rabbitmq_config, s3_config, tensorflow_config


# Constants for testing
TEST_JWT_SECRET = "test_secret_key"
TEST_DOCUMENT_ID = "test-doc-123"
TEST_APPLICATION_ID = "test-app-456"
TEST_BUCKET_NAME = "mca-documents-test"


# Helper function to create a test JWT token
def create_test_token(user_id: str = "test-user", role: str = "operations", expires_delta: timedelta = None) -> str:
    """
    Create a test JWT token for authentication in tests.
    
    Args:
        user_id: The user ID to include in the token
        role: The role to assign to the user (operations or admin)
        expires_delta: Optional expiration time delta
        
    Returns:
        A JWT token string
    """
    import jwt
    from datetime import datetime, timedelta
    
    expires_delta = expires_delta or timedelta(minutes=15)
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4())
    }
    
    encoded_jwt = jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return encoded_jwt


# Mock classes for dependencies
class MockRabbitMQConnection:
    """
    Mock RabbitMQ connection for testing message queue integration.
    """
    def __init__(self):
        self.connected = True
        self.messages = []
        self.channel = MagicMock()
        self.connection = MagicMock()
        
    def publish_message(self, exchange: str, routing_key: str, message: Dict[str, Any]) -> bool:
        """
        Mock publishing a message to RabbitMQ.
        
        Args:
            exchange: The exchange to publish to
            routing_key: The routing key for the message
            message: The message to publish
            
        Returns:
            True if successful
        """
        self.messages.append({
            "exchange": exchange,
            "routing_key": routing_key,
            "message": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        return True
    
    def get_messages(self) -> List[Dict[str, Any]]:
        """
        Get all published messages.
        
        Returns:
            List of published messages
        """
        return self.messages
    
    def is_connected(self) -> bool:
        """
        Check if the connection is active.
        
        Returns:
            Connection status
        """
        return self.connected
    
    def disconnect(self):
        """
        Simulate disconnection.
        """
        self.connected = False
        
    def reconnect(self):
        """
        Simulate reconnection.
        """
        self.connected = True


class MockS3Client:
    """
    Mock S3 client for testing document storage.
    """
    def __init__(self):
        self.connected = True
        self.objects = {}
        self.buckets = [TEST_BUCKET_NAME]
        
    def upload_file(self, file_path: str, bucket: str, key: str) -> bool:
        """
        Mock uploading a file to S3.
        
        Args:
            file_path: Path to the file to upload
            bucket: Bucket to upload to
            key: Object key in the bucket
            
        Returns:
            True if successful
        """
        if bucket not in self.buckets:
            return False
        
        self.objects[f"{bucket}/{key}"] = {
            "content": f"Mock content for {key}",
            "metadata": {
                "ContentType": "application/pdf",
                "ContentLength": 12345,
                "LastModified": datetime.utcnow().isoformat()
            }
        }
        return True
    
    def download_file(self, bucket: str, key: str, download_path: str) -> bool:
        """
        Mock downloading a file from S3.
        
        Args:
            bucket: Bucket to download from
            key: Object key in the bucket
            download_path: Path to save the downloaded file
            
        Returns:
            True if successful
        """
        if bucket not in self.buckets:
            return False
        
        object_key = f"{bucket}/{key}"
        if object_key not in self.objects:
            return False
        
        # In a real test, we would write to the download_path
        # Here we just simulate success
        return True
    
    def get_object_metadata(self, bucket: str, key: str) -> Dict[str, Any]:
        """
        Mock getting object metadata from S3.
        
        Args:
            bucket: Bucket containing the object
            key: Object key in the bucket
            
        Returns:
            Object metadata
        """
        object_key = f"{bucket}/{key}"
        if object_key in self.objects:
            return self.objects[object_key]["metadata"]
        return {}
    
    def is_connected(self) -> bool:
        """
        Check if the connection is active.
        
        Returns:
            Connection status
        """
        return self.connected
    
    def disconnect(self):
        """
        Simulate disconnection.
        """
        self.connected = False
        
    def reconnect(self):
        """
        Simulate reconnection.
        """
        self.connected = True


class MockGPUManager:
    """
    Mock GPU manager for testing GPU availability.
    """
    def __init__(self, available: bool = True, memory_gb: float = 16.0):
        self.available = available
        self.memory_gb = memory_gb
        self.utilization = 0.0
        
    def is_gpu_available(self) -> bool:
        """
        Check if GPU is available.
        
        Returns:
            GPU availability status
        """
        return self.available
    
    def get_gpu_memory(self) -> float:
        """
        Get available GPU memory in GB.
        
        Returns:
            Available GPU memory in GB
        """
        return self.memory_gb
    
    def get_gpu_utilization(self) -> float:
        """
        Get GPU utilization percentage.
        
        Returns:
            GPU utilization percentage
        """
        return self.utilization
    
    def set_gpu_available(self, available: bool):
        """
        Set GPU availability for testing.
        
        Args:
            available: GPU availability status
        """
        self.available = available
    
    def set_gpu_memory(self, memory_gb: float):
        """
        Set available GPU memory for testing.
        
        Args:
            memory_gb: Available GPU memory in GB
        """
        self.memory_gb = memory_gb
    
    def set_gpu_utilization(self, utilization: float):
        """
        Set GPU utilization for testing.
        
        Args:
            utilization: GPU utilization percentage
        """
        self.utilization = utilization


# Schema validation helper
def validate_response_schema(response_data: Dict[str, Any], schema_class: BaseModel) -> bool:
    """
    Validate response data against a Pydantic schema.
    
    Args:
        response_data: Response data to validate
        schema_class: Pydantic schema class to validate against
        
    Returns:
        True if validation succeeds, False otherwise
    """
    try:
        schema_class.parse_obj(response_data)
        return True
    except ValidationError:
        return False


# OpenAPI schema validation helper
def validate_against_openapi(response_data: Dict[str, Any], schema_name: str, openapi_path: str = None) -> bool:
    """
    Validate response data against an OpenAPI schema.
    
    Args:
        response_data: Response data to validate
        schema_name: Name of the schema in the OpenAPI specification
        openapi_path: Path to the OpenAPI specification file
        
    Returns:
        True if validation succeeds, False otherwise
    """
    from jsonschema import validate, ValidationError
    
    # Default to the project's OpenAPI specification if not provided
    openapi_path = openapi_path or os.path.join(os.path.dirname(__file__), "../../openapi.json")
    
    try:
        with open(openapi_path, "r") as f:
            openapi_spec = json.load(f)
            
        schema = openapi_spec.get("components", {}).get("schemas", {}).get(schema_name)
        if not schema:
            return False
        
        validate(instance=response_data, schema=schema)
        return True
    except (FileNotFoundError, json.JSONDecodeError, ValidationError):
        return False


# Pytest fixtures
@pytest.fixture
def mock_rabbitmq():
    """
    Fixture providing a mock RabbitMQ connection.
    
    Returns:
        MockRabbitMQConnection instance
    """
    return MockRabbitMQConnection()


@pytest.fixture
def mock_s3():
    """
    Fixture providing a mock S3 client.
    
    Returns:
        MockS3Client instance
    """
    return MockS3Client()


@pytest.fixture
def mock_gpu():
    """
    Fixture providing a mock GPU manager.
    
    Returns:
        MockGPUManager instance
    """
    return MockGPUManager()


@pytest.fixture
def app(mock_rabbitmq, mock_s3, mock_gpu):
    """
    Fixture providing a FastAPI application instance with mocked dependencies.
    
    Args:
        mock_rabbitmq: Mock RabbitMQ connection
        mock_s3: Mock S3 client
        mock_gpu: Mock GPU manager
        
    Returns:
        FastAPI application instance
    """
    # Create a test configuration
    test_config = {
        "APP_ENV": "test",
        "APP_NAME": "ocr-service-test",
        "APP_VERSION": "0.1.0-test",
        "LOG_LEVEL": "DEBUG",
        "API_PREFIX": "/api/v1",
        "JWT_SECRET": TEST_JWT_SECRET,
        "JWT_ALGORITHM": "HS256",
        "RABBITMQ_HOST": "localhost",
        "RABBITMQ_PORT": 5672,
        "RABBITMQ_USER": "guest",
        "RABBITMQ_PASSWORD": "guest",
        "RABBITMQ_EXCHANGE": "mca.documents",
        "RABBITMQ_QUEUE": "data-extraction",
        "S3_ENDPOINT": "localhost:9000",
        "S3_ACCESS_KEY": "minioadmin",
        "S3_SECRET_KEY": "minioadmin",
        "S3_BUCKET": TEST_BUCKET_NAME,
        "S3_SECURE": False,
        "TENSORFLOW_MODEL_PATH": "/tmp/models",
        "TENSORFLOW_GPU_MEMORY_LIMIT": 8,
        "OCR_CONFIDENCE_THRESHOLD": 0.75
    }
    
    # Patch the configuration and dependencies
    with patch.dict(os.environ, test_config), \
         patch("src.app.create_rabbitmq_connection", return_value=mock_rabbitmq), \
         patch("src.app.create_s3_client", return_value=mock_s3), \
         patch("src.app.check_gpu_availability", return_value=True), \
         patch("src.app.load_tensorflow_models", return_value=True):
        
        # Create the application
        app = create_app()
        
        # Add test-specific middleware or configuration here if needed
        return app


@pytest.fixture
def client(app):
    """
    Fixture providing a FastAPI TestClient instance.
    
    Args:
        app: FastAPI application instance
        
    Returns:
        FastAPI TestClient instance
    """
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """
    Fixture providing authentication headers with a valid JWT token.
    
    Returns:
        Dict with Authorization header
    """
    token = create_test_token()
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth_headers():
    """
    Fixture providing authentication headers with a valid admin JWT token.
    
    Returns:
        Dict with Authorization header for admin role
    """
    token = create_test_token(role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_auth_headers():
    """
    Fixture providing authentication headers with an expired JWT token.
    
    Returns:
        Dict with Authorization header containing expired token
    """
    token = create_test_token(expires_delta=timedelta(minutes=-15))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_document_metadata():
    """
    Fixture providing sample document metadata for testing.
    
    Returns:
        Dict with document metadata
    """
    return {
        "document_id": TEST_DOCUMENT_ID,
        "application_id": TEST_APPLICATION_ID,
        "document_type": "bank_statement",
        "file_name": "bank_statement.pdf",
        "file_size": 12345,
        "mime_type": "application/pdf",
        "upload_date": datetime.utcnow().isoformat(),
        "classification": {
            "document_type": "bank_statement",
            "confidence": 0.95,
            "page_count": 3
        },
        "storage_path": f"{TEST_BUCKET_NAME}/{TEST_APPLICATION_ID}/{TEST_DOCUMENT_ID}.pdf"
    }


@pytest.fixture
def sample_ocr_results():
    """
    Fixture providing sample OCR results for testing.
    
    Returns:
        Dict with OCR extraction results
    """
    return {
        "document_id": TEST_DOCUMENT_ID,
        "application_id": TEST_APPLICATION_ID,
        "processing_time": 2.45,  # seconds
        "extraction_date": datetime.utcnow().isoformat(),
        "document_type": "bank_statement",
        "extracted_data": {
            "account_holder": {
                "value": "ACME CORPORATION",
                "confidence": 0.98
            },
            "account_number": {
                "value": "123456789",
                "confidence": 0.95
            },
            "bank_name": {
                "value": "FIRST NATIONAL BANK",
                "confidence": 0.99
            },
            "statement_date": {
                "value": "2023-01-15",
                "confidence": 0.92
            },
            "opening_balance": {
                "value": "5000.00",
                "confidence": 0.88
            },
            "closing_balance": {
                "value": "6250.75",
                "confidence": 0.89
            },
            "transactions": {
                "value": [
                    {
                        "date": "2023-01-03",
                        "description": "DEPOSIT",
                        "amount": "1500.00",
                        "type": "credit"
                    },
                    {
                        "date": "2023-01-10",
                        "description": "WITHDRAWAL ATM",
                        "amount": "300.00",
                        "type": "debit"
                    },
                    {
                        "date": "2023-01-12",
                        "description": "PAYMENT RECEIVED",
                        "amount": "750.75",
                        "type": "credit"
                    }
                ],
                "confidence": 0.85
            }
        },
        "page_count": 3,
        "overall_confidence": 0.92,
        "processing_status": "completed",
        "error": None
    }


@pytest.fixture
def sample_metrics_data():
    """
    Fixture providing sample metrics data for testing.
    
    Returns:
        Dict with service metrics
    """
    return {
        "service": "ocr-service",
        "version": "0.1.0-test",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": 3600,  # seconds
        "ocr_metrics": {
            "documents_processed": 150,
            "documents_failed": 3,
            "average_processing_time": 2.3,  # seconds
            "average_confidence": 0.94,
            "accuracy": 0.99
        },
        "queue_metrics": {
            "queue_depth": 5,
            "messages_processed": 147,
            "messages_failed": 2,
            "average_queue_time": 1.2  # seconds
        },
        "resource_metrics": {
            "cpu_usage": 45.2,  # percentage
            "memory_usage": 1.2,  # GB
            "gpu_memory_usage": 6.5,  # GB
            "gpu_utilization": 78.3  # percentage
        }
    }


# Helper functions for tests
def get_test_document_path(document_type: str, filename: str) -> str:
    """
    Get the path to a test document file.
    
    Args:
        document_type: Type of document (e.g., 'typed_documents', 'handwritten_documents')
        filename: Name of the test document file
        
    Returns:
        Absolute path to the test document file
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    return os.path.join(base_dir, "test_data", document_type, filename)


def setup_test_document(mock_s3: MockS3Client, document_metadata: Dict[str, Any]) -> bool:
    """
    Set up a test document in the mock S3 storage.
    
    Args:
        mock_s3: Mock S3 client
        document_metadata: Document metadata
        
    Returns:
        True if successful
    """
    bucket = document_metadata["storage_path"].split("/")[0]
    key = "/".join(document_metadata["storage_path"].split("/")[1:])
    
    # Add the document to the mock S3 storage
    mock_s3.objects[f"{bucket}/{key}"] = {
        "content": f"Mock content for {key}",
        "metadata": {
            "ContentType": document_metadata["mime_type"],
            "ContentLength": document_metadata["file_size"],
            "LastModified": document_metadata["upload_date"]
        }
    }
    
    return True


def setup_test_message(mock_rabbitmq: MockRabbitMQConnection, document_metadata: Dict[str, Any]) -> bool:
    """
    Set up a test message in the mock RabbitMQ queue.
    
    Args:
        mock_rabbitmq: Mock RabbitMQ connection
        document_metadata: Document metadata
        
    Returns:
        True if successful
    """
    # Create a message for the document
    message = {
        "event_type": "document.classified",
        "document": document_metadata,
        "timestamp": datetime.utcnow().isoformat(),
        "correlation_id": str(uuid.uuid4())
    }
    
    # Add the message to the mock RabbitMQ queue
    mock_rabbitmq.publish_message(
        exchange=rabbitmq_config.RABBITMQ_EXCHANGE,
        routing_key="document.classified",
        message=message
    )
    
    return True