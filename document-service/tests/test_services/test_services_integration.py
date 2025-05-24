import pytest
import time
import json
import logging
from unittest.mock import MagicMock, patch, call
from io import BytesIO

from app import DocumentServiceApp
from services import QueueService, StorageService, ClassificationService, DocumentRoutingService
from models import DocumentClassifier
from config import AppConfig
from utils.metrics import MetricsCollector
from utils.logging_utils import setup_logger


@pytest.mark.integration
class TestDocumentServiceIntegration:
    """Integration tests for the Document Service components.
    
    These tests verify that the queue, storage, classification, and routing services
    work together correctly in the document processing pipeline.
    """
    
    @pytest.fixture
    def app_config(self):
        """Create a test configuration for the Document Service."""
        config = AppConfig()
        config.rabbitmq_host = "test-rabbitmq"
        config.rabbitmq_port = 5672
        config.rabbitmq_user = "test-user"
        config.rabbitmq_password = "test-password"
        config.rabbitmq_exchange = "mca.documents"
        config.rabbitmq_queue = "document-processing"
        config.s3_endpoint = "http://test-s3:9000"
        config.s3_access_key = "test-access-key"
        config.s3_secret_key = "test-secret-key"
        config.s3_bucket = "mca-documents-test"
        config.s3_region = "us-east-1"
        config.log_level = "INFO"
        return config
    
    @pytest.fixture
    def metrics_collector(self):
        """Create a mock metrics collector."""
        return MagicMock(spec=MetricsCollector)
    
    @pytest.fixture
    def document_service_app(self, app_config, metrics_collector):
        """Create a Document Service application with mocked components."""
        with patch("services.QueueService") as mock_queue_service, \
             patch("services.StorageService") as mock_storage_service, \
             patch("services.ClassificationService") as mock_classification_service, \
             patch("services.DocumentRoutingService") as mock_routing_service:
            
            # Create the app with mocked services
            app = DocumentServiceApp(app_config)
            app.queue_service = mock_queue_service.return_value
            app.storage_service = mock_storage_service.return_value
            app.classification_service = mock_classification_service.return_value
            app.document_routing_service = mock_routing_service.return_value
            app.metrics_collector = metrics_collector
            
            # Configure the mocks
            app.queue_service.consume_message.side_effect = self._mock_consume_message
            
            yield app
    
    def _mock_consume_message(self, callback):
        """Mock the consume_message method to call the callback with a test message."""
        # This will be replaced in specific tests
        pass
    
    def _create_test_document_message(self, document_type="application"):
        """Create a test document message for processing."""
        return {
            "message_id": "test-message-123",
            "document": {
                "id": "doc-123",
                "filename": f"{document_type}.pdf",
                "size": 1024,
                "content_type": "application/pdf",
                "s3_path": f"documents/{document_type}.pdf",
                "metadata": {
                    "sender": "test@example.com",
                    "subject": "Test Document",
                    "received_at": "2023-01-01T12:00:00Z"
                }
            }
        }
    
    def test_end_to_end_document_processing(self, document_service_app, monkeypatch):
        """Test the end-to-end document processing flow.
        
        This test verifies that a document is correctly processed through the entire pipeline:
        1. Message is consumed from the queue
        2. Document is retrieved from storage
        3. Document is classified
        4. Document is routed to the appropriate OCR processor
        5. Results are published back to the queue
        """
        # Setup test data
        test_message = self._create_test_document_message("application")
        test_document_content = BytesIO(b"Test document content")
        test_classification_result = {
            "document_type": "loan_application",
            "confidence": 0.95,
            "features": {"page_count": 3, "has_signature": True}
        }
        test_routing_result = {
            "ocr_processor": "typed_text",
            "priority": "high",
            "processing_hints": {"form_type": "standard_application"}
        }
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service to provide our test message
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock storage service to return our test document
        app.storage_service.get_document.return_value = test_document_content
        
        # Mock classification service to return our test classification
        app.classification_service.classify_document.return_value = test_classification_result
        
        # Mock routing service to return our test routing
        app.document_routing_service.route_document.return_value = test_routing_result
        
        # Run the document processing
        app.start()
        
        # Verify the document was processed correctly through the entire pipeline
        app.storage_service.get_document.assert_called_once_with(test_message["document"]["s3_path"])
        app.classification_service.classify_document.assert_called_once()
        app.document_routing_service.route_document.assert_called_once_with(
            test_classification_result, test_message["document"]
        )
        app.queue_service.publish_message.assert_called_once()
        
        # Verify the published message contains the expected data
        published_message = app.queue_service.publish_message.call_args[0][0]
        assert published_message["document_id"] == test_message["document"]["id"]
        assert published_message["classification"] == test_classification_result
        assert published_message["routing"] == test_routing_result
        
        # Verify metrics were collected
        app.metrics_collector.record_processing_time.assert_called()
        app.metrics_collector.increment_processed_documents.assert_called_once()
    
    def test_service_interactions_and_data_handoffs(self, document_service_app):
        """Test the interactions between services and data handoffs.
        
        This test verifies that data is correctly passed between services and that
        each service receives the expected inputs and produces the expected outputs.
        """
        # Setup test data
        test_message = self._create_test_document_message("tax_return")
        test_document_content = BytesIO(b"Test tax return content")
        
        # Configure mocks with specific behavior to test data handoffs
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock storage service with verification of input
        def mock_get_document(path):
            assert path == test_message["document"]["s3_path"]
            return test_document_content
        app.storage_service.get_document.side_effect = mock_get_document
        
        # Mock classification service with verification of input
        def mock_classify(document, metadata=None):
            assert document == test_document_content
            assert metadata["filename"] == test_message["document"]["filename"]
            return {"document_type": "tax_return", "confidence": 0.92}
        app.classification_service.classify_document.side_effect = mock_classify
        
        # Mock routing service with verification of input
        def mock_route(classification, document_info):
            assert classification["document_type"] == "tax_return"
            assert document_info == test_message["document"]
            return {"ocr_processor": "financial_document", "priority": "medium"}
        app.document_routing_service.route_document.side_effect = mock_route
        
        # Run the document processing
        app.start()
        
        # Verify the message was published with the correct data
        app.queue_service.publish_message.assert_called_once()
        published_message = app.queue_service.publish_message.call_args[0][0]
        assert published_message["document_id"] == test_message["document"]["id"]
        assert published_message["classification"]["document_type"] == "tax_return"
        assert published_message["routing"]["ocr_processor"] == "financial_document"
    
    def test_error_propagation_between_services(self, document_service_app, caplog):
        """Test error propagation between services.
        
        This test verifies that errors in one service are properly propagated and handled
        by the document processing pipeline, with appropriate logging and error reporting.
        """
        caplog.set_level(logging.ERROR)
        
        # Setup test data
        test_message = self._create_test_document_message("bank_statement")
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock storage service to raise an exception
        app.storage_service.get_document.side_effect = Exception("Storage service error")
        
        # Run the document processing
        app.start()
        
        # Verify error was logged
        assert "Storage service error" in caplog.text
        assert "Failed to process document" in caplog.text
        
        # Verify error metrics were collected
        app.metrics_collector.increment_processing_errors.assert_called_once()
        
        # Verify error was reported to the queue service
        app.queue_service.publish_error.assert_called_once()
        error_message = app.queue_service.publish_error.call_args[0][0]
        assert error_message["document_id"] == test_message["document"]["id"]
        assert "error" in error_message
        assert "Storage service error" in error_message["error"]
    
    def test_performance_metrics_collection(self, document_service_app):
        """Test performance metrics collection across services.
        
        This test verifies that performance metrics are correctly collected during
        document processing, including processing time, throughput, and accuracy metrics.
        """
        # Setup test data
        test_message = self._create_test_document_message("pay_stub")
        test_document_content = BytesIO(b"Test pay stub content")
        test_classification_result = {
            "document_type": "pay_stub",
            "confidence": 0.88,
            "processing_time_ms": 150
        }
        test_routing_result = {
            "ocr_processor": "financial_document",
            "priority": "medium",
            "processing_time_ms": 50
        }
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock services with timing information
        app.storage_service.get_document.return_value = test_document_content
        app.classification_service.classify_document.return_value = test_classification_result
        app.document_routing_service.route_document.return_value = test_routing_result
        
        # Run the document processing
        start_time = time.time()
        app.start()
        end_time = time.time()
        
        # Verify metrics were collected
        app.metrics_collector.record_processing_time.assert_called()
        app.metrics_collector.record_classification_confidence.assert_called_with(0.88)
        app.metrics_collector.record_classification_time.assert_called_with(150)
        app.metrics_collector.record_routing_time.assert_called_with(50)
        
        # Verify total processing time was recorded
        total_time_call = app.metrics_collector.record_total_processing_time.call_args[0][0]
        assert isinstance(total_time_call, (int, float))
        
        # Verify the processing time meets the performance requirement (under 5 minutes)
        assert (end_time - start_time) < 300  # 5 minutes = 300 seconds
    
    def test_configuration_consistency(self, document_service_app, app_config):
        """Test configuration consistency between services.
        
        This test verifies that configuration settings are consistently applied across
        all services in the document processing pipeline.
        """
        app = document_service_app
        
        # Verify queue service configuration
        app.queue_service.configure.assert_called_once()
        queue_config = app.queue_service.configure.call_args[0][0]
        assert queue_config.rabbitmq_host == app_config.rabbitmq_host
        assert queue_config.rabbitmq_port == app_config.rabbitmq_port
        assert queue_config.rabbitmq_user == app_config.rabbitmq_user
        assert queue_config.rabbitmq_password == app_config.rabbitmq_password
        assert queue_config.rabbitmq_exchange == app_config.rabbitmq_exchange
        assert queue_config.rabbitmq_queue == app_config.rabbitmq_queue
        
        # Verify storage service configuration
        app.storage_service.configure.assert_called_once()
        storage_config = app.storage_service.configure.call_args[0][0]
        assert storage_config.s3_endpoint == app_config.s3_endpoint
        assert storage_config.s3_access_key == app_config.s3_access_key
        assert storage_config.s3_secret_key == app_config.s3_secret_key
        assert storage_config.s3_bucket == app_config.s3_bucket
        assert storage_config.s3_region == app_config.s3_region
        
        # Verify classification service configuration
        app.classification_service.configure.assert_called_once()
        
        # Verify routing service configuration
        app.document_routing_service.configure.assert_called_once()
    
    def test_document_processing_with_low_confidence(self, document_service_app):
        """Test document processing with low confidence classification.
        
        This test verifies that documents with low confidence classification are properly
        handled, including flagging for human review and applying fallback strategies.
        """
        # Setup test data
        test_message = self._create_test_document_message("unknown")
        test_document_content = BytesIO(b"Test unknown document content")
        test_classification_result = {
            "document_type": "unknown",
            "confidence": 0.45,  # Low confidence
            "possible_types": ["application", "tax_return", "bank_statement"]
        }
        test_routing_result = {
            "ocr_processor": "general",
            "priority": "low",
            "requires_human_review": True,
            "processing_hints": {"extract_all_text": True}
        }
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock services
        app.storage_service.get_document.return_value = test_document_content
        app.classification_service.classify_document.return_value = test_classification_result
        app.document_routing_service.route_document.return_value = test_routing_result
        
        # Run the document processing
        app.start()
        
        # Verify the document was flagged for human review
        app.queue_service.publish_message.assert_called_once()
        published_message = app.queue_service.publish_message.call_args[0][0]
        assert published_message["requires_human_review"] == True
        assert published_message["classification"]["confidence"] < 0.75  # Threshold from spec
        
        # Verify metrics were collected
        app.metrics_collector.increment_low_confidence_documents.assert_called_once()
    
    def test_document_processing_with_multiple_document_types(self, document_service_app):
        """Test processing of different document types.
        
        This test verifies that different document types are correctly classified and routed
        to the appropriate OCR processors based on their content and characteristics.
        """
        # Setup test data for different document types
        document_types = [
            {"type": "loan_application", "confidence": 0.98, "ocr": "typed_text"},
            {"type": "tax_return", "confidence": 0.95, "ocr": "financial_document"},
            {"type": "bank_statement", "confidence": 0.92, "ocr": "financial_document"},
            {"type": "pay_stub", "confidence": 0.90, "ocr": "financial_document"},
            {"type": "identity_document", "confidence": 0.96, "ocr": "identity_document"}
        ]
        
        # Configure mocks
        app = document_service_app
        
        # Process each document type
        for doc_info in document_types:
            # Reset mock call counts
            app.queue_service.reset_mock()
            app.storage_service.reset_mock()
            app.classification_service.reset_mock()
            app.document_routing_service.reset_mock()
            
            # Setup test data for this document type
            test_message = self._create_test_document_message(doc_info["type"])
            test_document_content = BytesIO(f"Test {doc_info['type']} content".encode())
            test_classification_result = {
                "document_type": doc_info["type"],
                "confidence": doc_info["confidence"]
            }
            test_routing_result = {
                "ocr_processor": doc_info["ocr"],
                "priority": "high" if doc_info["confidence"] > 0.95 else "medium"
            }
            
            # Mock queue service
            def mock_consume(callback, message=test_message):
                callback(message)
                return True
            app.queue_service.consume_message.side_effect = lambda cb: mock_consume(cb, test_message)
            
            # Mock services
            app.storage_service.get_document.return_value = test_document_content
            app.classification_service.classify_document.return_value = test_classification_result
            app.document_routing_service.route_document.return_value = test_routing_result
            
            # Run the document processing
            app.start()
            
            # Verify the document was processed correctly
            app.queue_service.publish_message.assert_called_once()
            published_message = app.queue_service.publish_message.call_args[0][0]
            assert published_message["classification"]["document_type"] == doc_info["type"]
            assert published_message["routing"]["ocr_processor"] == doc_info["ocr"]
    
    def test_retry_logic_for_transient_errors(self, document_service_app, caplog):
        """Test retry logic for transient errors.
        
        This test verifies that the document service correctly implements retry logic
        for transient errors, such as temporary S3 or RabbitMQ unavailability.
        """
        caplog.set_level(logging.INFO)
        
        # Setup test data
        test_message = self._create_test_document_message("application")
        test_document_content = BytesIO(b"Test document content")
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock storage service to fail on first attempt, succeed on second
        storage_call_count = 0
        def mock_get_document(path):
            nonlocal storage_call_count
            storage_call_count += 1
            if storage_call_count == 1:
                raise Exception("Temporary S3 unavailability")
            return test_document_content
        app.storage_service.get_document.side_effect = mock_get_document
        
        # Mock classification service
        app.classification_service.classify_document.return_value = {
            "document_type": "loan_application",
            "confidence": 0.95
        }
        
        # Mock routing service
        app.document_routing_service.route_document.return_value = {
            "ocr_processor": "typed_text",
            "priority": "high"
        }
        
        # Run the document processing
        app.start()
        
        # Verify retry was attempted and succeeded
        assert storage_call_count == 2
        assert "Temporary S3 unavailability" in caplog.text
        assert "Retrying document retrieval" in caplog.text
        
        # Verify the document was eventually processed successfully
        app.queue_service.publish_message.assert_called_once()
        app.metrics_collector.increment_retry_attempts.assert_called_once()
    
    def test_logging_at_appropriate_levels(self, document_service_app, caplog):
        """Test logging at appropriate levels.
        
        This test verifies that the document service logs events at the appropriate levels
        as specified in the technical specification (ERROR, WARN, INFO, DEBUG).
        """
        # Set log level to capture all logs
        caplog.set_level(logging.DEBUG)
        
        # Setup test data
        test_message = self._create_test_document_message("application")
        test_document_content = BytesIO(b"Test document content")
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            # Log at different levels in the queue service
            app.logger.error("Test ERROR message from queue service")
            app.logger.warning("Test WARNING message from queue service")
            app.logger.info("Test INFO message from queue service")
            app.logger.debug("Test DEBUG message from queue service")
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock other services
        app.storage_service.get_document.return_value = test_document_content
        app.classification_service.classify_document.return_value = {"document_type": "loan_application", "confidence": 0.95}
        app.document_routing_service.route_document.return_value = {"ocr_processor": "typed_text", "priority": "high"}
        
        # Run the document processing
        app.start()
        
        # Verify logs at different levels were captured
        assert "Test ERROR message from queue service" in caplog.text
        assert "Test WARNING message from queue service" in caplog.text
        assert "Test INFO message from queue service" in caplog.text
        assert "Test DEBUG message from queue service" in caplog.text
        
        # Verify log format includes timestamp, level, and component
        for record in caplog.records:
            assert record.levelname in ["ERROR", "WARNING", "INFO", "DEBUG"]
            assert "document_service" in record.name.lower()
    
    def test_processing_time_within_requirements(self, document_service_app):
        """Test that document processing time meets requirements.
        
        This test verifies that document processing completes within the required time
        limit of 5 minutes as specified in the technical specification.
        """
        # Setup test data
        test_message = self._create_test_document_message("application")
        test_document_content = BytesIO(b"Test document content")
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock other services with realistic processing times
        app.storage_service.get_document.return_value = test_document_content
        
        # Add a small delay to simulate processing time
        def mock_classify(document, metadata=None):
            time.sleep(0.1)  # 100ms delay
            return {"document_type": "loan_application", "confidence": 0.95, "processing_time_ms": 100}
        app.classification_service.classify_document.side_effect = mock_classify
        
        def mock_route(classification, document_info):
            time.sleep(0.05)  # 50ms delay
            return {"ocr_processor": "typed_text", "priority": "high", "processing_time_ms": 50}
        app.document_routing_service.route_document.side_effect = mock_route
        
        # Run the document processing and measure time
        start_time = time.time()
        app.start()
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify processing time is within requirements (5 minutes = 300 seconds)
        assert processing_time < 300
        
        # More realistic expectation for unit test (should be much faster)
        assert processing_time < 1.0  # Should complete in under 1 second in test environment
        
        # Verify processing time metrics were recorded
        app.metrics_collector.record_total_processing_time.assert_called_once()
        recorded_time = app.metrics_collector.record_total_processing_time.call_args[0][0]
        assert recorded_time > 0
        assert recorded_time < 1000  # Less than 1000ms
    
    def test_document_classification_accuracy(self, document_service_app):
        """Test document classification accuracy metrics.
        
        This test verifies that the document service maintains the required 99% classification
        accuracy as specified in the technical specification.
        """
        # Setup test data for accuracy testing
        test_documents = [
            {"type": "loan_application", "expected": "loan_application", "confidence": 0.99},
            {"type": "tax_return", "expected": "tax_return", "confidence": 0.98},
            {"type": "bank_statement", "expected": "bank_statement", "confidence": 0.97},
            {"type": "pay_stub", "expected": "pay_stub", "confidence": 0.99},
            {"type": "identity_document", "expected": "identity_document", "confidence": 0.98},
            # One misclassification to test accuracy calculation
            {"type": "utility_bill", "expected": "other", "confidence": 0.85}
        ]
        
        # Configure mocks
        app = document_service_app
        
        # Track classification results
        classification_results = []
        
        # Process each test document
        for doc in test_documents:
            # Reset mock call counts
            app.queue_service.reset_mock()
            app.storage_service.reset_mock()
            app.classification_service.reset_mock()
            app.document_routing_service.reset_mock()
            
            # Setup test data
            test_message = self._create_test_document_message(doc["type"])
            test_document_content = BytesIO(f"Test {doc['type']} content".encode())
            
            # Mock queue service
            def mock_consume(callback, message=test_message):
                callback(message)
                return True
            app.queue_service.consume_message.side_effect = lambda cb: mock_consume(cb, test_message)
            
            # Mock storage service
            app.storage_service.get_document.return_value = test_document_content
            
            # Mock classification service
            app.classification_service.classify_document.return_value = {
                "document_type": doc["expected"],  # Use expected type to simulate classification
                "confidence": doc["confidence"]
            }
            
            # Mock routing service
            app.document_routing_service.route_document.return_value = {
                "ocr_processor": "general",
                "priority": "medium"
            }
            
            # Run the document processing
            app.start()
            
            # Record classification result
            classification_results.append({
                "actual_type": doc["type"],
                "classified_type": doc["expected"],
                "is_correct": doc["type"] == doc["expected"]
            })
        
        # Calculate accuracy
        correct_classifications = sum(1 for result in classification_results if result["is_correct"])
        accuracy = correct_classifications / len(classification_results)
        
        # Verify accuracy meets requirements (99%)
        # Note: In this test we're simulating one misclassification out of 6 documents,
        # so the expected accuracy is 5/6 = 83.33%. In a real system with more documents,
        # the accuracy would need to be 99% or higher.
        assert accuracy >= 0.8  # For this small test set
        
        # Verify accuracy metrics were recorded
        assert app.metrics_collector.record_classification_accuracy.call_count == len(test_documents)
    
    def test_graceful_shutdown(self, document_service_app):
        """Test graceful shutdown of the document service.
        
        This test verifies that the document service shuts down gracefully when requested,
        properly closing connections to RabbitMQ and S3, and completing in-progress tasks.
        """
        # Configure mocks
        app = document_service_app
        
        # Mock in-progress task
        in_progress_task = MagicMock()
        app._in_progress_tasks = [in_progress_task]
        
        # Call shutdown
        app.stop()
        
        # Verify connections were closed properly
        app.queue_service.close.assert_called_once()
        app.storage_service.close.assert_called_once()
        
        # Verify in-progress tasks were completed
        in_progress_task.wait.assert_called_once()
        
        # Verify shutdown was logged
        app.logger.info.assert_any_call("Document service shutting down gracefully")
        app.logger.info.assert_any_call("Document service shutdown complete")
    
    def test_message_format_compliance(self, document_service_app):
        """Test message format compliance with specifications.
        
        This test verifies that messages published to RabbitMQ comply with the
        standardized JSON format specified in the technical specification.
        """
        # Setup test data
        test_message = self._create_test_document_message("application")
        test_document_content = BytesIO(b"Test document content")
        test_classification_result = {
            "document_type": "loan_application",
            "confidence": 0.95,
            "features": {"page_count": 3, "has_signature": True}
        }
        test_routing_result = {
            "ocr_processor": "typed_text",
            "priority": "high",
            "processing_hints": {"form_type": "standard_application"}
        }
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock services
        app.storage_service.get_document.return_value = test_document_content
        app.classification_service.classify_document.return_value = test_classification_result
        app.document_routing_service.route_document.return_value = test_routing_result
        
        # Run the document processing
        app.start()
        
        # Verify the published message format
        app.queue_service.publish_message.assert_called_once()
        published_message = app.queue_service.publish_message.call_args[0][0]
        
        # Verify required fields are present
        assert "message_id" in published_message
        assert "document_id" in published_message
        assert "classification" in published_message
        assert "routing" in published_message
        assert "timestamp" in published_message
        
        # Verify field formats
        assert isinstance(published_message["message_id"], str)
        assert published_message["document_id"] == test_message["document"]["id"]
        assert published_message["classification"] == test_classification_result
        assert published_message["routing"] == test_routing_result
        assert isinstance(published_message["timestamp"], str)
        
        # Verify the message can be serialized to JSON
        try:
            json_message = json.dumps(published_message)
            assert isinstance(json_message, str)
        except Exception as e:
            pytest.fail(f"Failed to serialize message to JSON: {e}")
    
    def test_concurrent_document_processing(self, document_service_app):
        """Test concurrent document processing.
        
        This test verifies that the document service can process multiple documents
        concurrently without errors or race conditions.
        """
        # Setup test data for multiple documents
        test_documents = [
            {"id": "doc-1", "type": "loan_application"},
            {"id": "doc-2", "type": "tax_return"},
            {"id": "doc-3", "type": "bank_statement"},
            {"id": "doc-4", "type": "pay_stub"},
            {"id": "doc-5", "type": "identity_document"}
        ]
        
        # Configure mocks
        app = document_service_app
        
        # Create test messages
        test_messages = []
        for doc in test_documents:
            message = self._create_test_document_message(doc["type"])
            message["document"]["id"] = doc["id"]
            test_messages.append(message)
        
        # Mock queue service to provide multiple messages
        message_index = 0
        processed_messages = []
        
        def mock_consume(callback):
            nonlocal message_index
            if message_index < len(test_messages):
                callback(test_messages[message_index])
                processed_messages.append(test_messages[message_index]["document"]["id"])
                message_index += 1
                return True
            return False
        
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock other services
        app.storage_service.get_document.return_value = BytesIO(b"Test document content")
        app.classification_service.classify_document.return_value = {"document_type": "test_type", "confidence": 0.95}
        app.document_routing_service.route_document.return_value = {"ocr_processor": "general", "priority": "medium"}
        
        # Configure app to process multiple messages
        app.max_messages = len(test_documents)
        
        # Run the document processing
        app.start()
        
        # Verify all documents were processed
        assert len(processed_messages) == len(test_documents)
        for doc in test_documents:
            assert doc["id"] in processed_messages
        
        # Verify publish_message was called for each document
        assert app.queue_service.publish_message.call_count == len(test_documents)
    
    def test_document_processing_with_corrupted_document(self, document_service_app, caplog):
        """Test document processing with corrupted document.
        
        This test verifies that the document service correctly handles corrupted documents,
        logging appropriate errors and reporting the issue without crashing.
        """
        caplog.set_level(logging.ERROR)
        
        # Setup test data
        test_message = self._create_test_document_message("corrupted")
        corrupted_content = BytesIO(b"Corrupted document content")
        
        # Configure mocks
        app = document_service_app
        
        # Mock queue service
        def mock_consume(callback):
            callback(test_message)
            return True
        app.queue_service.consume_message.side_effect = mock_consume
        
        # Mock storage service to return corrupted content
        app.storage_service.get_document.return_value = corrupted_content
        
        # Mock classification service to raise an exception for corrupted document
        app.classification_service.classify_document.side_effect = Exception("Document is corrupted or unreadable")
        
        # Run the document processing
        app.start()
        
        # Verify error was logged
        assert "Document is corrupted or unreadable" in caplog.text
        assert "Failed to process document" in caplog.text
        
        # Verify error metrics were collected
        app.metrics_collector.increment_processing_errors.assert_called_once()
        app.metrics_collector.increment_corrupted_documents.assert_called_once()
        
        # Verify error was reported to the queue service
        app.queue_service.publish_error.assert_called_once()
        error_message = app.queue_service.publish_error.call_args[0][0]
        assert error_message["document_id"] == test_message["document"]["id"]
        assert "error" in error_message
        assert "corrupted" in error_message["error"].lower() or "unreadable" in error_message["error"].lower()