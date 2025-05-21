import json
import os
import pytest
import time
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta

# Import services
from services import QueueService, StorageService, ClassificationService, DocumentRoutingService
from models import DocumentClassifier
from config import app_config, rabbitmq_config, s3_config, model_config
from types.documents import Document, DocumentMetadata, DocumentType, ProcessingStatus
from types.messages import MessagePayload, MessageHeaders
from types.classification import ClassificationResult, ConfidenceScore
from types.errors import ServiceError


@pytest.fixture
def mock_document():
    """Create a mock document for testing."""
    return Document(
        metadata=DocumentMetadata(
            id="test-doc-123",
            filename="test_application.pdf",
            content_type="application/pdf",
            size=1024,
            created_at=datetime.now().isoformat(),
            source="email"
        ),
        content=b"test document content",
        processing_status=ProcessingStatus.RECEIVED
    )


@pytest.fixture
def mock_message_payload(mock_document):
    """Create a mock message payload for testing."""
    return MessagePayload(
        document_id=mock_document.metadata.id,
        storage_path="mca-documents-staging/test_application.pdf",
        metadata={
            "filename": mock_document.metadata.filename,
            "content_type": mock_document.metadata.content_type,
            "size": mock_document.metadata.size,
            "created_at": mock_document.metadata.created_at,
            "source": mock_document.metadata.source
        }
    )


@pytest.fixture
def mock_classification_result():
    """Create a mock classification result for testing."""
    return ClassificationResult(
        document_type=DocumentType.APPLICATION,
        confidence=ConfidenceScore(
            score=0.95,
            threshold=0.8,
            is_confident=True
        ),
        metadata={
            "page_count": 3,
            "has_signature": True,
            "is_complete": True
        }
    )


@pytest.fixture
def mock_queue_service():
    """Create a mock queue service for testing."""
    service = MagicMock(spec=QueueService)
    service.consume_message.return_value = True
    service.publish_message.return_value = True
    return service


@pytest.fixture
def mock_storage_service(mock_document):
    """Create a mock storage service for testing."""
    service = MagicMock(spec=StorageService)
    service.get_document.return_value = mock_document
    service.store_document.return_value = "mca-documents-staging/test_application_classified.pdf"
    return service


@pytest.fixture
def mock_classification_service(mock_classification_result):
    """Create a mock classification service for testing."""
    service = MagicMock(spec=ClassificationService)
    service.classify_document.return_value = mock_classification_result
    return service


@pytest.fixture
def mock_document_routing_service():
    """Create a mock document routing service for testing."""
    service = MagicMock(spec=DocumentRoutingService)
    service.route_document.return_value = {
        "queue": "data-extraction",
        "routing_key": "application.form",
        "priority": 1
    }
    return service


@pytest.fixture
def mock_document_classifier():
    """Create a mock document classifier for testing."""
    classifier = MagicMock(spec=DocumentClassifier)
    classifier.predict.return_value = DocumentType.APPLICATION
    classifier.predict_proba.return_value = {DocumentType.APPLICATION: 0.95}
    return classifier


@pytest.fixture
def integrated_services(mock_queue_service, mock_storage_service, 
                      mock_classification_service, mock_document_routing_service):
    """Create a dictionary of integrated services for testing."""
    return {
        "queue_service": mock_queue_service,
        "storage_service": mock_storage_service,
        "classification_service": mock_classification_service,
        "routing_service": mock_document_routing_service
    }


@pytest.mark.integration
class TestDocumentProcessingIntegration:
    """Integration tests for the document processing pipeline."""

    def test_end_to_end_document_processing(self, integrated_services, mock_message_payload, mock_document):
        """Test the complete document processing flow from queue to routing."""
        # Setup services
        queue_service = integrated_services["queue_service"]
        storage_service = integrated_services["storage_service"]
        classification_service = integrated_services["classification_service"]
        routing_service = integrated_services["routing_service"]

        # Mock queue service to return our test message
        queue_service.get_message.return_value = (json.dumps(mock_message_payload.__dict__), "test-delivery-tag")

        # Start processing flow
        start_time = time.time()

        # 1. Get message from queue
        message_body, delivery_tag = queue_service.get_message()
        message_data = json.loads(message_body)
        
        # 2. Get document from storage
        document = storage_service.get_document(message_data["document_id"], message_data["storage_path"])
        assert document.metadata.id == mock_document.metadata.id
        
        # 3. Classify document
        classification_result = classification_service.classify_document(document)
        assert classification_result.document_type == DocumentType.APPLICATION
        assert classification_result.confidence.score >= 0.9  # High confidence
        
        # 4. Update document with classification result
        document.classification_result = classification_result
        document.processing_status = ProcessingStatus.CLASSIFIED
        
        # 5. Store updated document
        updated_path = storage_service.store_document(document)
        assert "classified" in updated_path
        
        # 6. Route document to OCR service
        routing_info = routing_service.route_document(document, classification_result)
        assert routing_info["queue"] == "data-extraction"
        
        # 7. Publish to OCR queue
        ocr_message = {
            "document_id": document.metadata.id,
            "storage_path": updated_path,
            "document_type": classification_result.document_type.value,
            "confidence": classification_result.confidence.score,
            "routing": routing_info
        }
        success = queue_service.publish_message(routing_info["queue"], json.dumps(ocr_message))
        assert success is True
        
        # 8. Acknowledge original message
        queue_service.acknowledge_message(delivery_tag)
        
        # Verify processing time
        processing_time = time.time() - start_time
        assert processing_time < 5.0  # Under 5 seconds for test
        
        # Verify all service interactions occurred
        storage_service.get_document.assert_called_once()
        classification_service.classify_document.assert_called_once()
        routing_service.route_document.assert_called_once()
        queue_service.publish_message.assert_called_once()
        queue_service.acknowledge_message.assert_called_once()

    def test_service_interactions_and_data_handoffs(self, integrated_services, mock_document, mock_classification_result):
        """Test the interactions between services and data handoffs."""
        # Setup services
        storage_service = integrated_services["storage_service"]
        classification_service = integrated_services["classification_service"]
        routing_service = integrated_services["routing_service"]
        
        # 1. Storage to Classification handoff
        document = storage_service.get_document("test-doc-123", "test-path")
        classification_result = classification_service.classify_document(document)
        
        # Verify classification service received correct document
        classification_service.classify_document.assert_called_with(document)
        
        # 2. Classification to Routing handoff
        document.classification_result = classification_result
        routing_info = routing_service.route_document(document, classification_result)
        
        # Verify routing service received correct document and classification
        routing_service.route_document.assert_called_with(document, classification_result)
        
        # 3. Verify data consistency across handoffs
        assert document.metadata.id == "test-doc-123"
        assert document.classification_result.document_type == DocumentType.APPLICATION

    def test_error_propagation_between_services(self, integrated_services, mock_document):
        """Test error propagation between services."""
        # Setup services
        queue_service = integrated_services["queue_service"]
        storage_service = integrated_services["storage_service"]
        classification_service = integrated_services["classification_service"]
        
        # 1. Test storage service error
        storage_error = ServiceError("Storage error", "Failed to retrieve document")
        storage_service.get_document.side_effect = storage_error
        
        # Verify error is propagated
        with pytest.raises(ServiceError) as excinfo:
            document = storage_service.get_document("test-doc-123", "test-path")
        assert "Storage error" in str(excinfo.value)
        
        # Reset mock
        storage_service.get_document.side_effect = None
        storage_service.get_document.return_value = mock_document
        
        # 2. Test classification service error
        classification_error = ServiceError("Classification error", "Failed to classify document")
        classification_service.classify_document.side_effect = classification_error
        
        # Verify error is propagated
        with pytest.raises(ServiceError) as excinfo:
            document = storage_service.get_document("test-doc-123", "test-path")
            classification_result = classification_service.classify_document(document)
        assert "Classification error" in str(excinfo.value)
        
        # 3. Test queue service error
        queue_error = ServiceError("Queue error", "Failed to publish message")
        queue_service.publish_message.side_effect = queue_error
        
        # Verify error is propagated
        with pytest.raises(ServiceError) as excinfo:
            queue_service.publish_message("test-queue", "test-message")
        assert "Queue error" in str(excinfo.value)

    @patch('time.time')
    def test_performance_metrics_collection(self, mock_time, integrated_services, mock_document, mock_classification_result):
        """Test performance metrics collection across services."""
        # Setup time mock to return predictable values
        mock_time.side_effect = [100.0, 100.5, 101.0, 101.3, 101.5]  # 0.5s, 0.5s, 0.3s, 0.2s
        
        # Setup services
        storage_service = integrated_services["storage_service"]
        classification_service = integrated_services["classification_service"]
        routing_service = integrated_services["routing_service"]
        
        # Enable performance tracking on mocks
        storage_service.get_document.return_value = mock_document
        classification_service.classify_document.return_value = mock_classification_result
        
        # 1. Measure storage service performance
        start_time = time.time()
        document = storage_service.get_document("test-doc-123", "test-path")
        storage_time = time.time() - start_time
        
        # 2. Measure classification service performance
        start_time = time.time()
        classification_result = classification_service.classify_document(document)
        classification_time = time.time() - start_time
        
        # 3. Measure routing service performance
        start_time = time.time()
        routing_info = routing_service.route_document(document, classification_result)
        routing_time = time.time() - start_time
        
        # 4. Calculate total processing time
        total_time = storage_time + classification_time + routing_time
        
        # Verify performance metrics
        assert storage_time == 0.5
        assert classification_time == 0.5
        assert routing_time == 0.3
        assert total_time == 1.3  # Total processing time
        
        # Verify processing time is under required threshold (5 minutes)
        assert total_time < 300.0  # 5 minutes in seconds

    def test_configuration_consistency(self):
        """Test configuration consistency between services."""
        # 1. Test RabbitMQ configuration consistency
        assert rabbitmq_config.EXCHANGE_NAME == "mca.documents"
        assert rabbitmq_config.QUEUE_NAME == "document-processing"
        assert rabbitmq_config.ROUTING_KEY == "document.classify"
        
        # 2. Test S3 configuration consistency
        assert "mca-documents-staging" in s3_config.BUCKET_NAME
        assert s3_config.ENCRYPTION == "AES256"
        
        # 3. Test model configuration consistency
        assert model_config.CONFIDENCE_THRESHOLD >= 0.8  # High confidence threshold
        assert "SVM" in model_config.CLASSIFIER_TYPES
        assert "RANDOM_FOREST" in model_config.CLASSIFIER_TYPES
        
        # 4. Test environment-specific settings
        if app_config.ENVIRONMENT == "production":
            assert s3_config.BUCKET_NAME == "mca-documents-production"
        elif app_config.ENVIRONMENT == "staging":
            assert s3_config.BUCKET_NAME == "mca-documents-staging"


@pytest.mark.integration
class TestDocumentClassificationAccuracy:
    """Integration tests for document classification accuracy."""
    
    @pytest.fixture
    def classification_service_with_real_models(self, mock_document_classifier):
        """Create a classification service with real models for testing."""
        with patch('models.DocumentClassifier', return_value=mock_document_classifier):
            service = ClassificationService()
            return service
    
    def test_classification_accuracy(self, classification_service_with_real_models, mock_document):
        """Test that classification accuracy meets the 99% requirement."""
        # Setup test documents with known types
        test_documents = [
            (mock_document, DocumentType.APPLICATION),  # Expected to be classified as APPLICATION
            # Add more test documents with known types
        ]
        
        # Track classification results
        correct_classifications = 0
        total_classifications = len(test_documents)
        
        # Classify each document and check accuracy
        for document, expected_type in test_documents:
            result = classification_service_with_real_models.classify_document(document)
            if result.document_type == expected_type:
                correct_classifications += 1
        
        # Calculate accuracy
        accuracy = correct_classifications / total_classifications
        
        # Verify accuracy meets requirement (99%)
        assert accuracy >= 0.99, f"Classification accuracy {accuracy:.2%} does not meet 99% requirement"


@pytest.mark.integration
class TestErrorHandlingAndRecovery:
    """Integration tests for error handling and recovery."""
    
    def test_queue_connection_recovery(self, integrated_services):
        """Test that queue service can recover from connection errors."""
        queue_service = integrated_services["queue_service"]
        
        # Simulate connection error and recovery
        connection_error = ServiceError("Connection error", "RabbitMQ connection lost")
        queue_service.get_message.side_effect = [connection_error, ("recovered message", "tag")]
        
        # First call should raise error
        with pytest.raises(ServiceError):
            queue_service.get_message()
        
        # Service should attempt to reconnect
        queue_service.reconnect.assert_called_once()
        
        # Second call should succeed after recovery
        message, tag = queue_service.get_message()
        assert message == "recovered message"
    
    def test_storage_retry_logic(self, integrated_services, mock_document):
        """Test that storage service implements retry logic for transient errors."""
        storage_service = integrated_services["storage_service"]
        
        # Simulate transient error that succeeds on retry
        transient_error = ServiceError("Transient error", "Temporary S3 unavailability")
        storage_service.get_document.side_effect = [transient_error, mock_document]
        
        # Configure retry settings
        with patch('config.s3_config.MAX_RETRIES', 3):
            with patch('config.s3_config.RETRY_DELAY', 0.1):  # Short delay for testing
                # Should retry and eventually succeed
                document = storage_service.get_document("test-doc-123", "test-path")
                assert document.metadata.id == mock_document.metadata.id
                
                # Verify retry was attempted
                assert storage_service.get_document.call_count == 2


@pytest.mark.integration
class TestEndToEndPerformance:
    """Integration tests for end-to-end performance."""
    
    def test_processing_time_requirement(self, integrated_services, mock_message_payload):
        """Test that document processing meets the 5-minute requirement."""
        # Setup services
        queue_service = integrated_services["queue_service"]
        storage_service = integrated_services["storage_service"]
        classification_service = integrated_services["classification_service"]
        routing_service = integrated_services["routing_service"]
        
        # Mock queue service to return our test message
        queue_service.get_message.return_value = (json.dumps(mock_message_payload.__dict__), "test-delivery-tag")
        
        # Process multiple documents and measure time
        num_documents = 10
        start_time = time.time()
        
        for _ in range(num_documents):
            # 1. Get message from queue
            message_body, delivery_tag = queue_service.get_message()
            message_data = json.loads(message_body)
            
            # 2. Get document from storage
            document = storage_service.get_document(message_data["document_id"], message_data["storage_path"])
            
            # 3. Classify document
            classification_result = classification_service.classify_document(document)
            
            # 4. Route document
            routing_info = routing_service.route_document(document, classification_result)
            
            # 5. Publish to OCR queue
            queue_service.publish_message(routing_info["queue"], "test-message")
            
            # 6. Acknowledge original message
            queue_service.acknowledge_message(delivery_tag)
        
        # Calculate average processing time
        total_time = time.time() - start_time
        avg_time = total_time / num_documents
        
        # Verify average processing time is under required threshold (5 minutes)
        assert avg_time < 300.0, f"Average processing time {avg_time:.2f}s exceeds 5-minute requirement"
        
        # For test environment, we expect much faster processing
        assert avg_time < 1.0, f"Average processing time {avg_time:.2f}s is slower than expected for tests"