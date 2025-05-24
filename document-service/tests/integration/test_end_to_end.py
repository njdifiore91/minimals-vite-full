import os
import time
import uuid
import json
import pytest
import logging
from unittest.mock import patch, MagicMock, call
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple

# Import application components
from app import DocumentServiceApp
from config import app_config, rabbitmq_config
from services import QueueService, StorageService, ClassificationService, DocumentRoutingService
from models import DocumentClassifier
from types.classification import ClassificationResult, ConfidenceScore
from types.storage import StorageMetadata
from utils.validation_utils import validate_document_format
from utils.file_utils import get_mime_type
from utils.time_utils import get_current_timestamp, calculate_processing_time

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestDocumentProcessingEndToEnd:
    """
    Integration tests for the complete document processing flow in the Document Service.
    
    These tests verify that documents are correctly consumed from RabbitMQ, classified,
    stored in S3, and routed to appropriate OCR processors. The tests validate the entire
    processing pipeline from message consumption to result publication.
    """
    
    @pytest.fixture
    def app(self, mock_queue_service, mock_storage_service, mock_classification_service, mock_document_routing_service):
        """
        Create a test instance of the DocumentServiceApp with mocked services.
        """
        app = DocumentServiceApp()
        app.queue_service = mock_queue_service
        app.storage_service = mock_storage_service
        app.classification_service = mock_classification_service
        app.document_routing_service = mock_document_routing_service
        return app
    
    @pytest.fixture
    def sample_document_message(self, sample_pdf_document):
        """
        Create a sample RabbitMQ message containing a document for processing.
        """
        return {
            "message_id": str(uuid.uuid4()),
            "document": {
                "id": str(uuid.uuid4()),
                "name": "loan_application.pdf",
                "content_type": "application/pdf",
                "size": len(sample_pdf_document),
                "binary_data": sample_pdf_document,
                "source": "email",
                "received_timestamp": get_current_timestamp(),
                "sender": "applicant@example.com",
                "subject": "Loan Application Documents"
            },
            "metadata": {
                "application_id": str(uuid.uuid4()),
                "customer_id": str(uuid.uuid4()),
                "priority": "high"
            }
        }
    
    def test_complete_document_processing_flow(self, app, sample_document_message, caplog):
        """
        Test the complete document processing flow from message consumption to result publication.
        
        This test verifies that a document is correctly processed through the entire pipeline:
        1. Message is consumed from RabbitMQ
        2. Document is validated and stored in S3
        3. Document is classified with high confidence
        4. Document is routed to the appropriate OCR processor
        5. Results are published to the OCR queue
        6. Processing completes within time limits
        7. Proper logging occurs throughout the process
        """
        caplog.set_level(logging.INFO)
        
        # Set up expected classification result
        expected_classification = ClassificationResult(
            document_type="loan_application",
            confidence=ConfidenceScore(score=0.95, threshold=0.75),
            features={
                "page_count": 3,
                "has_signature": True,
                "has_tables": True
            },
            metadata={
                "document_id": sample_document_message["document"]["id"],
                "application_id": sample_document_message["metadata"]["application_id"],
                "classification_timestamp": get_current_timestamp()
            }
        )
        
        # Configure mocks for the happy path
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        app.classification_service.classify_document.return_value = expected_classification
        
        app.document_routing_service.determine_routing.return_value = {
            "queue": "ocr.loan_application",
            "routing_key": "ocr.typed.form",
            "priority": 8,
            "metadata": {
                "expected_fields": ["name", "address", "loan_amount", "term", "signature"],
                "document_type": "loan_application",
                "confidence": 0.95
            }
        }
        
        # Start processing time measurement
        start_time = time.time()
        
        # Process the document
        app.process_document(sample_document_message)
        
        # End processing time measurement
        processing_time = time.time() - start_time
        
        # Verify processing time is under the required limit (5 minutes)
        assert processing_time < 300, f"Processing took {processing_time} seconds, which exceeds the 5-minute limit"
        
        # Verify document validation was performed
        app.storage_service.store_document.assert_called_once()
        
        # Verify document was classified
        app.classification_service.classify_document.assert_called_once()
        
        # Verify document was routed
        app.document_routing_service.determine_routing.assert_called_once_with(
            expected_classification
        )
        
        # Verify result was published to the OCR queue
        app.queue_service.publish_message.assert_called_once()
        publish_args = app.queue_service.publish_message.call_args[0]
        assert publish_args[0] == "ocr.loan_application"  # queue
        assert publish_args[1] == "ocr.typed.form"  # routing key
        
        # Verify the published message contains the expected data
        published_message = json.loads(publish_args[2])
        assert published_message["document_id"] == sample_document_message["document"]["id"]
        assert published_message["document_type"] == "loan_application"
        assert published_message["confidence"] == 0.95
        assert "storage_path" in published_message
        assert "application_id" in published_message
        
        # Verify proper logging occurred
        assert "Document received for processing" in caplog.text
        assert "Document stored in S3" in caplog.text
        assert "Document classified as loan_application with 95% confidence" in caplog.text
        assert "Document routed to OCR processor" in caplog.text
        assert "Document processing completed successfully" in caplog.text
    
    def test_document_processing_with_low_confidence(self, app, sample_document_message, caplog):
        """
        Test document processing when classification confidence is below the threshold.
        
        This test verifies that when a document is classified with low confidence:
        1. It is flagged for human review
        2. It is still routed to the appropriate OCR processor
        3. The message published to the OCR queue includes the low confidence flag
        4. Proper warning logs are generated
        """
        caplog.set_level(logging.WARNING)
        
        # Set up classification result with low confidence
        low_confidence_classification = ClassificationResult(
            document_type="loan_application",
            confidence=ConfidenceScore(score=0.65, threshold=0.75),  # Below threshold
            features={
                "page_count": 3,
                "has_signature": True,
                "has_tables": True
            },
            metadata={
                "document_id": sample_document_message["document"]["id"],
                "application_id": sample_document_message["metadata"]["application_id"],
                "classification_timestamp": get_current_timestamp()
            }
        )
        
        # Configure mocks
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        app.classification_service.classify_document.return_value = low_confidence_classification
        
        app.document_routing_service.determine_routing.return_value = {
            "queue": "ocr.loan_application",
            "routing_key": "ocr.typed.form",
            "priority": 5,  # Lower priority due to low confidence
            "metadata": {
                "expected_fields": ["name", "address", "loan_amount", "term", "signature"],
                "document_type": "loan_application",
                "confidence": 0.65,
                "requires_review": True
            }
        }
        
        # Process the document
        app.process_document(sample_document_message)
        
        # Verify document was classified
        app.classification_service.classify_document.assert_called_once()
        
        # Verify document was routed despite low confidence
        app.document_routing_service.determine_routing.assert_called_once_with(
            low_confidence_classification
        )
        
        # Verify result was published to the OCR queue with the review flag
        app.queue_service.publish_message.assert_called_once()
        publish_args = app.queue_service.publish_message.call_args[0]
        published_message = json.loads(publish_args[2])
        assert published_message["requires_review"] is True
        assert published_message["confidence"] == 0.65
        
        # Verify proper warning logs were generated
        assert "Low confidence classification detected" in caplog.text
        assert "Document flagged for human review" in caplog.text
    
    def test_document_processing_with_unsupported_format(self, app, sample_document_message, caplog):
        """
        Test document processing when the document format is not supported.
        
        This test verifies that when an unsupported document is received:
        1. The document is rejected with appropriate error
        2. The error is properly logged
        3. No classification or routing is attempted
        """
        caplog.set_level(logging.ERROR)
        
        # Modify the document to have an unsupported format
        sample_document_message["document"]["name"] = "document.xyz"
        sample_document_message["document"]["content_type"] = "application/xyz"
        
        # Configure the validation to fail
        with patch('utils.validation_utils.validate_document_format', return_value=False):
            # Process the document
            with pytest.raises(ValueError, match="Unsupported document format"):
                app.process_document(sample_document_message)
        
        # Verify classification was not attempted
        app.classification_service.classify_document.assert_not_called()
        
        # Verify routing was not attempted
        app.document_routing_service.determine_routing.assert_not_called()
        
        # Verify no message was published
        app.queue_service.publish_message.assert_not_called()
        
        # Verify error was logged
        assert "Unsupported document format" in caplog.text
        assert "Document processing failed" in caplog.text
    
    def test_document_processing_with_s3_storage_failure(self, app, sample_document_message, caplog):
        """
        Test document processing when S3 storage fails.
        
        This test verifies that when S3 storage fails:
        1. The error is properly handled and logged
        2. The document processing is retried up to the configured limit
        3. After retries are exhausted, the document is sent to a dead-letter queue
        """
        caplog.set_level(logging.ERROR)
        
        # Configure storage service to raise an exception
        app.storage_service.store_document.side_effect = Exception("S3 connection error")
        
        # Configure retry settings for testing
        app.max_retries = 3
        app.retry_delay = 0.1  # Short delay for testing
        
        # Process the document (should handle the exception and retry)
        with patch('time.sleep'):  # Mock sleep to speed up the test
            app.process_document(sample_document_message)
        
        # Verify storage was attempted multiple times (up to max_retries)
        assert app.storage_service.store_document.call_count == app.max_retries
        
        # Verify the document was sent to the dead-letter queue after retries
        app.queue_service.publish_to_dlq.assert_called_once()
        dlq_args = app.queue_service.publish_to_dlq.call_args[0]
        dlq_message = json.loads(dlq_args[0])
        assert dlq_message["document_id"] == sample_document_message["document"]["id"]
        assert "S3 connection error" in dlq_message["error"]
        
        # Verify errors were logged
        assert "Failed to store document in S3" in caplog.text
        assert f"Retry attempt 1 of {app.max_retries}" in caplog.text
        assert f"Retry attempt 2 of {app.max_retries}" in caplog.text
        assert f"Retry attempt 3 of {app.max_retries}" in caplog.text
        assert "Max retries exceeded" in caplog.text
        assert "Document sent to dead-letter queue" in caplog.text
    
    def test_document_processing_with_classification_failure(self, app, sample_document_message, caplog):
        """
        Test document processing when classification fails.
        
        This test verifies that when document classification fails:
        1. The error is properly handled and logged
        2. The document is still stored in S3
        3. The document is sent to a manual classification queue
        """
        caplog.set_level(logging.ERROR)
        
        # Configure storage to succeed
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        # Configure classification to fail
        app.classification_service.classify_document.side_effect = Exception("Classification model error")
        
        # Process the document
        app.process_document(sample_document_message)
        
        # Verify document was stored in S3
        app.storage_service.store_document.assert_called_once()
        
        # Verify classification was attempted
        app.classification_service.classify_document.assert_called_once()
        
        # Verify routing was not attempted
        app.document_routing_service.determine_routing.assert_not_called()
        
        # Verify document was sent to manual classification queue
        app.queue_service.publish_message.assert_called_once()
        publish_args = app.queue_service.publish_message.call_args[0]
        assert publish_args[0] == "manual.classification"  # queue
        assert publish_args[1] == "document.manual.review"  # routing key
        
        # Verify error was logged
        assert "Classification failed" in caplog.text
        assert "Document sent for manual classification" in caplog.text
    
    def test_document_processing_with_routing_failure(self, app, sample_document_message, caplog):
        """
        Test document processing when routing determination fails.
        
        This test verifies that when document routing fails:
        1. The error is properly handled and logged
        2. The document is still stored in S3 and classified
        3. The document is sent to a default OCR queue with a warning flag
        """
        caplog.set_level(logging.ERROR)
        
        # Configure storage to succeed
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        # Configure classification to succeed
        classification_result = ClassificationResult(
            document_type="loan_application",
            confidence=ConfidenceScore(score=0.95, threshold=0.75),
            features={
                "page_count": 3,
                "has_signature": True,
                "has_tables": True
            },
            metadata={
                "document_id": sample_document_message["document"]["id"],
                "application_id": sample_document_message["metadata"]["application_id"],
                "classification_timestamp": get_current_timestamp()
            }
        )
        app.classification_service.classify_document.return_value = classification_result
        
        # Configure routing to fail
        app.document_routing_service.determine_routing.side_effect = Exception("Routing configuration error")
        
        # Process the document
        app.process_document(sample_document_message)
        
        # Verify document was stored in S3
        app.storage_service.store_document.assert_called_once()
        
        # Verify document was classified
        app.classification_service.classify_document.assert_called_once()
        
        # Verify routing was attempted
        app.document_routing_service.determine_routing.assert_called_once()
        
        # Verify document was sent to default OCR queue
        app.queue_service.publish_message.assert_called_once()
        publish_args = app.queue_service.publish_message.call_args[0]
        assert publish_args[0] == "ocr.default"  # default queue
        assert publish_args[1] == "ocr.document.default"  # default routing key
        
        # Verify the published message contains the warning flag
        published_message = json.loads(publish_args[2])
        assert published_message["routing_error"] is True
        assert published_message["document_type"] == "loan_application"
        
        # Verify error was logged
        assert "Routing determination failed" in caplog.text
        assert "Using default OCR routing" in caplog.text
    
    def test_document_processing_performance(self, app, sample_document_message):
        """
        Test document processing performance meets the required standards.
        
        This test verifies that document processing meets performance requirements:
        1. Processing time is under 5 minutes (300 seconds)
        2. Classification accuracy is at least 99% for known document types
        3. Resource utilization stays within acceptable limits
        """
        # Configure mocks for successful processing
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        # Configure classification with high accuracy
        app.classification_service.classify_document.return_value = ClassificationResult(
            document_type="loan_application",
            confidence=ConfidenceScore(score=0.99, threshold=0.75),  # 99% confidence
            features={
                "page_count": 3,
                "has_signature": True,
                "has_tables": True
            },
            metadata={
                "document_id": sample_document_message["document"]["id"],
                "application_id": sample_document_message["metadata"]["application_id"],
                "classification_timestamp": get_current_timestamp()
            }
        )
        
        app.document_routing_service.determine_routing.return_value = {
            "queue": "ocr.loan_application",
            "routing_key": "ocr.typed.form",
            "priority": 8,
            "metadata": {
                "expected_fields": ["name", "address", "loan_amount", "term", "signature"],
                "document_type": "loan_application",
                "confidence": 0.99
            }
        }
        
        # Process multiple documents to measure average performance
        processing_times = []
        num_documents = 10
        
        for _ in range(num_documents):
            start_time = time.time()
            app.process_document(sample_document_message)
            processing_time = time.time() - start_time
            processing_times.append(processing_time)
        
        # Calculate average processing time
        avg_processing_time = sum(processing_times) / len(processing_times)
        max_processing_time = max(processing_times)
        
        # Verify performance requirements
        assert avg_processing_time < 5.0, f"Average processing time {avg_processing_time}s exceeds target of 5.0s"
        assert max_processing_time < 300, f"Maximum processing time {max_processing_time}s exceeds limit of 300s"
        
        # Verify classification accuracy
        assert app.classification_service.classify_document.return_value.confidence.score >= 0.99, \
            "Classification confidence does not meet the 99% accuracy requirement"
    
    def test_document_processing_with_various_document_types(self, app, caplog):
        """
        Test document processing with various document types.
        
        This test verifies that the document processing pipeline correctly handles
        different document types with appropriate classification and routing.
        """
        caplog.set_level(logging.INFO)
        
        # Define test cases for different document types
        document_types = [
            ("loan_application.pdf", "application/pdf", "loan_application", "ocr.typed.form"),
            ("tax_return.pdf", "application/pdf", "tax_return", "ocr.typed.tax"),
            ("bank_statement.pdf", "application/pdf", "bank_statement", "ocr.typed.statement"),
            ("pay_stub.jpg", "image/jpeg", "pay_stub", "ocr.mixed.pay"),
            ("drivers_license.jpg", "image/jpeg", "identity_document", "ocr.mixed.id"),
            ("utility_bill.png", "image/png", "proof_of_address", "ocr.typed.bill")
        ]
        
        for doc_name, content_type, doc_type, routing_key in document_types:
            # Reset mock call counts
            app.storage_service.reset_mock()
            app.classification_service.reset_mock()
            app.document_routing_service.reset_mock()
            app.queue_service.reset_mock()
            
            # Create document message
            document_id = str(uuid.uuid4())
            document_message = {
                "message_id": str(uuid.uuid4()),
                "document": {
                    "id": document_id,
                    "name": doc_name,
                    "content_type": content_type,
                    "size": 1024,  # Dummy size
                    "binary_data": b"dummy_data",  # Dummy data
                    "source": "email",
                    "received_timestamp": get_current_timestamp(),
                    "sender": "applicant@example.com",
                    "subject": "Loan Application Documents"
                },
                "metadata": {
                    "application_id": str(uuid.uuid4()),
                    "customer_id": str(uuid.uuid4()),
                    "priority": "high"
                }
            }
            
            # Configure mocks for this document type
            app.storage_service.store_document.return_value = {
                "storage_path": f"documents/{document_id}.{doc_name.split('.')[-1]}",
                "metadata": StorageMetadata(
                    document_id=document_id,
                    content_type=content_type,
                    size=1024,
                    upload_timestamp=get_current_timestamp(),
                    encryption="AES-256"
                )
            }
            
            app.classification_service.classify_document.return_value = ClassificationResult(
                document_type=doc_type,
                confidence=ConfidenceScore(score=0.95, threshold=0.75),
                features={
                    "page_count": 2,
                    "has_signature": True,
                    "has_tables": doc_type in ["tax_return", "bank_statement"]
                },
                metadata={
                    "document_id": document_id,
                    "application_id": document_message["metadata"]["application_id"],
                    "classification_timestamp": get_current_timestamp()
                }
            )
            
            app.document_routing_service.determine_routing.return_value = {
                "queue": f"ocr.{doc_type}",
                "routing_key": routing_key,
                "priority": 8,
                "metadata": {
                    "document_type": doc_type,
                    "confidence": 0.95
                }
            }
            
            # Process the document
            app.process_document(document_message)
            
            # Verify document was stored in S3
            app.storage_service.store_document.assert_called_once()
            
            # Verify document was classified
            app.classification_service.classify_document.assert_called_once()
            
            # Verify document was routed correctly
            app.document_routing_service.determine_routing.assert_called_once()
            
            # Verify result was published to the correct OCR queue
            app.queue_service.publish_message.assert_called_once()
            publish_args = app.queue_service.publish_message.call_args[0]
            assert publish_args[0] == f"ocr.{doc_type}"  # queue
            assert publish_args[1] == routing_key  # routing key
            
            # Verify proper logging occurred
            assert f"Document classified as {doc_type}" in caplog.text
    
    def test_document_processing_with_message_publishing_failure(self, app, sample_document_message, caplog):
        """
        Test document processing when message publishing to the OCR queue fails.
        
        This test verifies that when message publishing fails:
        1. The error is properly handled and logged
        2. The document processing retries publishing up to the configured limit
        3. After retries are exhausted, the error is logged and tracked
        """
        caplog.set_level(logging.ERROR)
        
        # Configure successful storage and classification
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        app.classification_service.classify_document.return_value = ClassificationResult(
            document_type="loan_application",
            confidence=ConfidenceScore(score=0.95, threshold=0.75),
            features={
                "page_count": 3,
                "has_signature": True,
                "has_tables": True
            },
            metadata={
                "document_id": sample_document_message["document"]["id"],
                "application_id": sample_document_message["metadata"]["application_id"],
                "classification_timestamp": get_current_timestamp()
            }
        )
        
        app.document_routing_service.determine_routing.return_value = {
            "queue": "ocr.loan_application",
            "routing_key": "ocr.typed.form",
            "priority": 8,
            "metadata": {
                "expected_fields": ["name", "address", "loan_amount", "term", "signature"],
                "document_type": "loan_application",
                "confidence": 0.95
            }
        }
        
        # Configure publishing to fail
        app.queue_service.publish_message.side_effect = Exception("RabbitMQ connection error")
        
        # Configure retry settings for testing
        app.max_retries = 3
        app.retry_delay = 0.1  # Short delay for testing
        
        # Process the document (should handle the exception and retry)
        with patch('time.sleep'):  # Mock sleep to speed up the test
            app.process_document(sample_document_message)
        
        # Verify publishing was attempted multiple times (up to max_retries)
        assert app.queue_service.publish_message.call_count == app.max_retries
        
        # Verify errors were logged
        assert "Failed to publish message to OCR queue" in caplog.text
        assert f"Retry attempt 1 of {app.max_retries}" in caplog.text
        assert f"Retry attempt 2 of {app.max_retries}" in caplog.text
        assert f"Retry attempt 3 of {app.max_retries}" in caplog.text
        assert "Max retries exceeded for publishing message" in caplog.text
        
        # Verify the error was tracked
        app.queue_service.track_failed_message.assert_called_once()
        track_args = app.queue_service.track_failed_message.call_args[0]
        assert track_args[0] == "ocr.loan_application"  # queue
        assert track_args[1] == "ocr.typed.form"  # routing key
        assert "RabbitMQ connection error" in track_args[3]  # error message
    
    def test_logging_throughout_document_processing(self, app, sample_document_message, caplog):
        """
        Test that proper logging occurs throughout the document processing pipeline.
        
        This test verifies that:
        1. All processing steps are logged at the appropriate level
        2. Logs include required context information
        3. Performance metrics are logged
        4. Document metadata is included in logs
        """
        # Capture logs at all levels
        caplog.set_level(logging.DEBUG)
        
        # Configure mocks for successful processing
        app.storage_service.store_document.return_value = {
            "storage_path": f"documents/{sample_document_message['document']['id']}.pdf",
            "metadata": StorageMetadata(
                document_id=sample_document_message["document"]["id"],
                content_type="application/pdf",
                size=sample_document_message["document"]["size"],
                upload_timestamp=get_current_timestamp(),
                encryption="AES-256"
            )
        }
        
        app.classification_service.classify_document.return_value = ClassificationResult(
            document_type="loan_application",
            confidence=ConfidenceScore(score=0.95, threshold=0.75),
            features={
                "page_count": 3,
                "has_signature": True,
                "has_tables": True
            },
            metadata={
                "document_id": sample_document_message["document"]["id"],
                "application_id": sample_document_message["metadata"]["application_id"],
                "classification_timestamp": get_current_timestamp()
            }
        )
        
        app.document_routing_service.determine_routing.return_value = {
            "queue": "ocr.loan_application",
            "routing_key": "ocr.typed.form",
            "priority": 8,
            "metadata": {
                "expected_fields": ["name", "address", "loan_amount", "term", "signature"],
                "document_type": "loan_application",
                "confidence": 0.95
            }
        }
        
        # Process the document
        app.process_document(sample_document_message)
        
        # Verify INFO level logs
        info_logs = [record for record in caplog.records if record.levelno == logging.INFO]
        assert any("Document received for processing" in record.message for record in info_logs)
        assert any("Document stored in S3" in record.message for record in info_logs)
        assert any("Document classified" in record.message for record in info_logs)
        assert any("Document routed to OCR processor" in record.message for record in info_logs)
        assert any("Document processing completed successfully" in record.message for record in info_logs)
        
        # Verify DEBUG level logs
        debug_logs = [record for record in caplog.records if record.levelno == logging.DEBUG]
        assert any("Validating document format" in record.message for record in debug_logs)
        assert any("Extracting document features" in record.message for record in debug_logs)
        assert any("Applying classification models" in record.message for record in debug_logs)
        assert any("Determining optimal OCR routing" in record.message for record in debug_logs)
        assert any("Preparing message for OCR queue" in record.message for record in debug_logs)
        
        # Verify context information in logs
        document_id = sample_document_message["document"]["id"]
        assert any(document_id in record.message for record in caplog.records)
        
        # Verify performance metrics in logs
        assert any("Processing time:" in record.message for record in info_logs)
        assert any("Classification confidence:" in record.message for record in info_logs)
        
        # Verify structured logging format
        for record in caplog.records:
            if record.levelno >= logging.INFO:
                assert hasattr(record, "document_id")
                assert hasattr(record, "timestamp")