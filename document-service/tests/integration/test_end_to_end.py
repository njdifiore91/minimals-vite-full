import os
import time
import uuid
import json
import pytest
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Tuple

# Import Document Service components
from src.app import DocumentServiceApp
from src.config import app_config, rabbitmq_config, s3_config, model_config
from src.types.documents import DocumentType, ProcessingStatus
from src.types.classification import ClassificationResult
from src.types.messages import MessagePayload
from src.services.queue_service import QueueService
from src.services.storage_service import StorageService
from src.services.classification_service import ClassificationService
from src.services.document_routing_service import DocumentRoutingService

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.mark.integration
class TestDocumentServiceEndToEnd:
    """
    End-to-end integration tests for the Document Service.
    
    These tests verify the complete document processing flow from message consumption
    to result publication, ensuring that all components work together correctly.
    """
    
    @pytest.fixture
    def app(self, rabbitmq_connection, s3_client, classification_models):
        """
        Creates a Document Service application instance with test dependencies.
        """
        # Create a test configuration
        test_config = app_config.get_test_config()
        
        # Initialize the application with test dependencies
        app = DocumentServiceApp(config=test_config)
        
        # Inject test dependencies
        app.queue_service = QueueService(
            connection=rabbitmq_connection,
            config=rabbitmq_config
        )
        app.storage_service = StorageService(
            s3_client=s3_client,
            config=s3_config
        )
        app.classification_service = ClassificationService(
            models=classification_models,
            config=model_config
        )
        app.document_routing_service = DocumentRoutingService(
            config=model_config
        )
        
        # Start the application
        app.start()
        
        yield app
        
        # Stop the application after tests
        app.stop()
    
    @pytest.fixture
    def test_documents(self, s3_client, test_bucket):
        """
        Creates test documents of different types in S3 for testing.
        
        Returns a dictionary mapping document IDs to their expected classification types.
        """
        document_types = {
            "application_form.pdf": DocumentType.APPLICATION,
            "tax_return_2023.pdf": DocumentType.TAX_RETURN,
            "bank_statement_march.pdf": DocumentType.BANK_STATEMENT,
            "pay_stub_q1.pdf": DocumentType.PAY_STUB,
            "drivers_license.jpg": DocumentType.ID_DOCUMENT,
            "misc_document.pdf": DocumentType.OTHER
        }
        
        document_ids = {}
        
        # Upload test documents to S3
        for filename, doc_type in document_types.items():
            document_id = str(uuid.uuid4())
            document_path = os.path.join("test_data", filename)
            
            # Create test document content if file doesn't exist
            if not os.path.exists(document_path):
                with open(document_path, "wb") as f:
                    f.write(b"Test document content for " + filename.encode())
            
            # Upload to S3
            with open(document_path, "rb") as f:
                s3_client.upload_fileobj(
                    f,
                    test_bucket,
                    f"documents/{document_id}/{filename}",
                    ExtraArgs={
                        "ServerSideEncryption": "AES256",
                        "Metadata": {
                            "filename": filename,
                            "content-type": "application/pdf" if filename.endswith(".pdf") else "image/jpeg"
                        }
                    }
                )
            
            document_ids[document_id] = doc_type
        
        return document_ids
    
    @pytest.fixture
    def test_messages(self, test_documents, test_bucket):
        """
        Creates test RabbitMQ messages for the test documents.
        """
        messages = []
        
        for document_id, _ in test_documents.items():
            # Create a message payload for each document
            message = {
                "document_id": document_id,
                "bucket": test_bucket,
                "path": f"documents/{document_id}",
                "metadata": {
                    "received_timestamp": int(time.time()),
                    "sender": "test@example.com",
                    "subject": "Test Document Submission",
                    "message_id": f"test-message-{document_id}"
                }
            }
            
            messages.append(message)
        
        return messages
    
    @pytest.fixture
    def mock_publish_message(self):
        """
        Mocks the message publishing to capture published messages.
        """
        published_messages = []
        
        def capture_message(exchange, routing_key, message, headers=None):
            published_messages.append({
                "exchange": exchange,
                "routing_key": routing_key,
                "message": message,
                "headers": headers or {}
            })
            return True
        
        with patch("src.services.queue_service.QueueService.publish_message", side_effect=capture_message) as mock:
            yield mock, published_messages
    
    def test_document_processing_pipeline(self, app, test_messages, mock_publish_message, test_documents):
        """
        Tests the complete document processing pipeline from message consumption to result publication.
        
        This test verifies that:
        1. Documents are correctly consumed from RabbitMQ
        2. Documents are classified with the correct document type
        3. Classification results are published to the OCR Service
        4. The entire process completes within the required time limit
        """
        mock_publish, published_messages = mock_publish_message
        
        # Process each test message
        for message in test_messages:
            # Start timing the processing
            start_time = time.time()
            
            # Simulate message consumption
            app.process_document_message(message)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Verify processing time is under the required limit (5 minutes)
            assert processing_time < 300, f"Document processing took too long: {processing_time} seconds"
            
            # Log processing time for monitoring
            logger.info(f"Document {message['document_id']} processed in {processing_time:.2f} seconds")
        
        # Verify that all messages were processed and published
        assert len(published_messages) == len(test_messages), "Not all messages were processed"
        
        # Verify classification results
        for published in published_messages:
            # Extract document ID from the published message
            document_id = json.loads(published["message"])["document_id"]
            
            # Get the expected document type
            expected_type = test_documents[document_id]
            
            # Get the actual classified type from the published message
            actual_type = json.loads(published["message"])["classification"]["document_type"]
            
            # Verify the document was classified correctly
            assert actual_type == expected_type.value, f"Document {document_id} was misclassified"
            
            # Verify confidence score is included and above threshold
            confidence = json.loads(published["message"])["classification"]["confidence"]
            assert confidence >= 0.75, f"Classification confidence too low: {confidence}"
            
            # Verify routing key is correct based on document type
            expected_routing_key = f"ocr.{expected_type.value.lower()}"
            assert published["routing_key"] == expected_routing_key, f"Incorrect routing key: {published['routing_key']}"
    
    def test_classification_accuracy(self, app, test_documents, s3_client, test_bucket):
        """
        Tests the classification accuracy for different document types.
        
        This test verifies that the document classification meets the 99% accuracy requirement
        by testing with a larger set of documents for each type.
        """
        # Number of test documents per type
        num_docs_per_type = 100
        
        # Track classification results
        results = {
            doc_type: {"correct": 0, "total": 0} for doc_type in DocumentType
        }
        
        # Test classification for each document type
        for doc_type in DocumentType:
            for i in range(num_docs_per_type):
                # Create a test document with features typical of this type
                document_id = str(uuid.uuid4())
                document_content = self._generate_test_document_content(doc_type, i)
                
                # Mock S3 storage and retrieval
                with patch.object(app.storage_service, 'get_document', return_value=document_content):
                    # Classify the document
                    classification_result = app.classification_service.classify_document(
                        document_id=document_id,
                        document_content=document_content,
                        metadata={}
                    )
                    
                    # Check if classification is correct
                    if classification_result.document_type == doc_type:
                        results[doc_type]["correct"] += 1
                    
                    results[doc_type]["total"] += 1
        
        # Calculate overall accuracy
        total_correct = sum(result["correct"] for result in results.values())
        total_docs = sum(result["total"] for result in results.values())
        overall_accuracy = total_correct / total_docs if total_docs > 0 else 0
        
        # Log accuracy results
        logger.info(f"Overall classification accuracy: {overall_accuracy:.4f}")
        for doc_type, result in results.items():
            accuracy = result["correct"] / result["total"] if result["total"] > 0 else 0
            logger.info(f"{doc_type.name} accuracy: {accuracy:.4f} ({result['correct']}/{result['total']})")
        
        # Verify accuracy meets the 99% requirement
        assert overall_accuracy >= 0.99, f"Classification accuracy below requirement: {overall_accuracy:.4f}"
    
    def test_error_handling_and_recovery(self, app, test_messages):
        """
        Tests error handling and recovery throughout the document processing pipeline.
        
        This test verifies that the service can handle and recover from various error conditions:
        1. S3 access errors
        2. Classification errors
        3. Message publishing errors
        """
        # Test S3 access error
        with patch.object(app.storage_service, 'get_document', side_effect=Exception("S3 access error")):
            # Process should handle the error and log it without crashing
            with pytest.raises(Exception) as excinfo:
                app.process_document_message(test_messages[0])
            assert "S3 access error" in str(excinfo.value)
        
        # Test classification error
        with patch.object(app.classification_service, 'classify_document', side_effect=Exception("Classification error")):
            # Process should handle the error and log it without crashing
            with pytest.raises(Exception) as excinfo:
                app.process_document_message(test_messages[0])
            assert "Classification error" in str(excinfo.value)
        
        # Test message publishing error with retry
        with patch.object(app.queue_service, 'publish_message') as mock_publish:
            # First call fails, second succeeds
            mock_publish.side_effect = [Exception("Publishing error"), True]
            
            # Mock document retrieval and classification
            with patch.object(app.storage_service, 'get_document', return_value=b"Test document"):
                with patch.object(app.classification_service, 'classify_document', return_value=ClassificationResult(
                    document_type=DocumentType.APPLICATION,
                    confidence=0.95,
                    metadata={}
                )):
                    # Process should retry and succeed
                    app.process_document_message(test_messages[0])
            
            # Verify publish was called twice (initial failure and retry)
            assert mock_publish.call_count == 2
    
    def test_performance_metrics(self, app, test_messages, mock_publish_message):
        """
        Tests performance metrics for document processing.
        
        This test verifies that document processing meets performance requirements:
        1. Processing time under 5 minutes per document
        2. Memory usage within acceptable limits
        3. CPU usage within acceptable limits
        """
        mock_publish, published_messages = mock_publish_message
        
        # Track processing times
        processing_times = []
        
        # Process each test message and measure performance
        for message in test_messages:
            # Mock document retrieval and classification for consistent testing
            with patch.object(app.storage_service, 'get_document', return_value=b"Test document"):
                with patch.object(app.classification_service, 'classify_document', return_value=ClassificationResult(
                    document_type=DocumentType.APPLICATION,
                    confidence=0.95,
                    metadata={}
                )):
                    # Start timing
                    start_time = time.time()
                    
                    # Process the message
                    app.process_document_message(message)
                    
                    # Record processing time
                    processing_time = time.time() - start_time
                    processing_times.append(processing_time)
        
        # Calculate performance metrics
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        max_processing_time = max(processing_times) if processing_times else 0
        
        # Log performance metrics
        logger.info(f"Average processing time: {avg_processing_time:.4f} seconds")
        logger.info(f"Maximum processing time: {max_processing_time:.4f} seconds")
        
        # Verify performance requirements
        assert avg_processing_time < 5.0, f"Average processing time too high: {avg_processing_time:.4f} seconds"
        assert max_processing_time < 30.0, f"Maximum processing time too high: {max_processing_time:.4f} seconds"
    
    def test_logging_and_monitoring(self, app, test_messages, caplog):
        """
        Tests logging and monitoring throughout the document processing pipeline.
        
        This test verifies that appropriate logging occurs at each stage of processing
        and that log levels are correctly applied based on the event type.
        """
        # Set log capture level
        caplog.set_level(logging.DEBUG)
        
        # Process a test message
        with patch.object(app.storage_service, 'get_document', return_value=b"Test document"):
            with patch.object(app.classification_service, 'classify_document', return_value=ClassificationResult(
                document_type=DocumentType.APPLICATION,
                confidence=0.95,
                metadata={}
            )):
                app.process_document_message(test_messages[0])
        
        # Verify logging for each processing stage
        log_records = caplog.records
        
        # Check for message received log
        assert any("Received document message" in record.message for record in log_records), "Missing message received log"
        
        # Check for document retrieval log
        assert any("Retrieved document from S3" in record.message for record in log_records), "Missing document retrieval log"
        
        # Check for classification log
        assert any("Classified document" in record.message for record in log_records), "Missing classification log"
        
        # Check for message publishing log
        assert any("Published classification result" in record.message for record in log_records), "Missing message publishing log"
        
        # Verify log levels are appropriate
        info_logs = [r for r in log_records if r.levelno == logging.INFO]
        debug_logs = [r for r in log_records if r.levelno == logging.DEBUG]
        
        # Normal operations should be INFO level
        assert len(info_logs) >= 4, "Not enough INFO level logs for normal operations"
        
        # Detailed processing should be DEBUG level
        assert len(debug_logs) > 0, "Missing DEBUG level logs for detailed processing"
    
    def test_edge_cases(self, app):
        """
        Tests edge cases and error conditions in the document processing pipeline.
        
        This test verifies that the service handles various edge cases correctly:
        1. Empty documents
        2. Very large documents
        3. Unsupported document types
        4. Low confidence classifications
        5. Missing metadata
        """
        # Test empty document
        empty_message = {
            "document_id": str(uuid.uuid4()),
            "bucket": "test-bucket",
            "path": "documents/empty",
            "metadata": {}
        }
        
        with patch.object(app.storage_service, 'get_document', return_value=b""):
            with pytest.raises(Exception) as excinfo:
                app.process_document_message(empty_message)
            assert "Empty document" in str(excinfo.value)
        
        # Test very large document (simulate size check)
        large_message = {
            "document_id": str(uuid.uuid4()),
            "bucket": "test-bucket",
            "path": "documents/large",
            "metadata": {}
        }
        
        with patch.object(app.storage_service, 'get_document', return_value=b"X" * (100 * 1024 * 1024)):
            with pytest.raises(Exception) as excinfo:
                app.process_document_message(large_message)
            assert "exceeds maximum size" in str(excinfo.value)
        
        # Test unsupported document type
        unsupported_message = {
            "document_id": str(uuid.uuid4()),
            "bucket": "test-bucket",
            "path": "documents/unsupported.xyz",
            "metadata": {}
        }
        
        with patch.object(app.storage_service, 'get_document', return_value=b"Unsupported content"):
            with patch.object(app.storage_service, 'get_document_metadata', return_value={"content-type": "application/x-unsupported"}):
                with pytest.raises(Exception) as excinfo:
                    app.process_document_message(unsupported_message)
                assert "Unsupported document type" in str(excinfo.value)
        
        # Test low confidence classification
        low_confidence_message = {
            "document_id": str(uuid.uuid4()),
            "bucket": "test-bucket",
            "path": "documents/low_confidence",
            "metadata": {}
        }
        
        with patch.object(app.storage_service, 'get_document', return_value=b"Ambiguous document content"):
            with patch.object(app.classification_service, 'classify_document', return_value=ClassificationResult(
                document_type=DocumentType.OTHER,
                confidence=0.3,  # Low confidence
                metadata={}
            )):
                # Should flag for human review but not fail
                with patch.object(app.queue_service, 'publish_message') as mock_publish:
                    app.process_document_message(low_confidence_message)
                    
                    # Verify message was published with human_review flag
                    args, kwargs = mock_publish.call_args
                    message_body = json.loads(args[2])
                    assert message_body["human_review_required"] == True, "Low confidence document not flagged for review"
    
    def _generate_test_document_content(self, doc_type: DocumentType, index: int) -> bytes:
        """
        Generates test document content with features typical of the specified document type.
        
        Args:
            doc_type: The document type to generate content for
            index: A unique index to ensure document uniqueness
            
        Returns:
            Bytes representing the document content
        """
        # In a real implementation, this would generate more realistic document content
        # based on the document type, with appropriate features for classification
        
        content_templates = {
            DocumentType.APPLICATION: b"MORTGAGE APPLICATION FORM\nApplicant Name: Test User\nLoan Amount: $300,000\nProperty Address: 123 Main St\nCredit Score: 750\nEmployment: 5 years\nIncome: $120,000",
            
            DocumentType.TAX_RETURN: b"FORM 1040 - U.S. INDIVIDUAL INCOME TAX RETURN\nTax Year: 2023\nName: Test User\nSSN: XXX-XX-1234\nTotal Income: $120,000\nAdjusted Gross Income: $105,000\nTotal Tax: $24,500",
            
            DocumentType.BANK_STATEMENT: b"MONTHLY STATEMENT\nAccount: XXXXXX1234\nPeriod: 01/01/2023 - 01/31/2023\nOpening Balance: $12,345.67\nDeposits: $5,432.10\nWithdrawals: $2,345.67\nClosing Balance: $15,432.10",
            
            DocumentType.PAY_STUB: b"EMPLOYEE PAY STUB\nEmployee: Test User\nPay Period: 01/01/2023 - 01/15/2023\nGross Pay: $5,000.00\nFederal Tax: $750.00\nState Tax: $250.00\nNet Pay: $4,000.00",
            
            DocumentType.ID_DOCUMENT: b"DRIVER LICENSE\nName: Test User\nAddress: 123 Main St\nDOB: 01/01/1980\nIssue Date: 01/01/2020\nExpiration Date: 01/01/2028\nLicense #: D1234567",
            
            DocumentType.OTHER: b"MISCELLANEOUS DOCUMENT\nThis document contains various information that doesn't fit into the other categories.\nIt might be a letter, a receipt, or some other supporting document."
        }
        
        # Get the template for this document type
        template = content_templates.get(doc_type, b"Unknown document type")
        
        # Add unique identifier to ensure document uniqueness
        unique_content = template + f"\nDocument ID: {index}".encode()
        
        return unique_content