import os
import json
import time
import pytest
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any, Tuple

# Import OCR service components
from app import OCRApplication
from services import OCRService, QueueService, StorageService, FieldExtractionService, ConfidenceService
from models import ModelFactory, TypedTextModel, HandwrittenTextModel, HybridRecognitionModel
from types.extraction import ExtractedData, ExtractedField, ConfidenceScore
from types.messages import MessagePayload
from types.storage import StorageMetadata
from utils.time_utils import get_current_timestamp

# Configure logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@pytest.fixture
def app_config():
    """Fixture for test application configuration."""
    return {
        "service_name": "ocr-service",
        "version": "1.0.0",
        "environment": "test",
        "log_level": "INFO",
        "rabbitmq": {
            "host": "localhost",
            "port": 5672,
            "username": "test",
            "password": "test",
            "exchange": "mca.documents.test",
            "queue": "ocr.request.test",
            "result_queue": "data.processing.test",
            "use_tls": False,
        },
        "s3": {
            "endpoint": "http://localhost:9000",
            "bucket": "mca-documents-test",
            "access_key": "test",
            "secret_key": "test",
            "region": "us-east-1",
            "use_encryption": True,
        },
        "tensorflow": {
            "model_path": "./models",
            "use_gpu": False,  # Disable GPU for tests
            "confidence_threshold": 0.75,
            "typed_model_name": "typed_text_model",
            "handwritten_model_name": "handwritten_text_model",
            "hybrid_model_name": "hybrid_recognition_model",
        },
    }


@pytest.fixture
def mock_queue_service():
    """Fixture for mocked QueueService."""
    mock_service = MagicMock(spec=QueueService)
    mock_service.consume_message.return_value = None
    mock_service.publish_message.return_value = True
    return mock_service


@pytest.fixture
def mock_storage_service():
    """Fixture for mocked StorageService."""
    mock_service = MagicMock(spec=StorageService)
    mock_service.download_document.return_value = (b"test document content", "application/pdf")
    mock_service.upload_result.return_value = "test-result-key"
    return mock_service


@pytest.fixture
def mock_model_factory():
    """Fixture for mocked ModelFactory."""
    mock_factory = MagicMock(spec=ModelFactory)
    mock_typed_model = MagicMock(spec=TypedTextModel)
    mock_handwritten_model = MagicMock(spec=HandwrittenTextModel)
    mock_hybrid_model = MagicMock(spec=HybridRecognitionModel)
    
    # Configure the mock models to return test data
    mock_typed_model.extract_text.return_value = {
        "text": "Test typed text",
        "confidence": 0.95,
    }
    mock_handwritten_model.extract_text.return_value = {
        "text": "Test handwritten text",
        "confidence": 0.85,
    }
    mock_hybrid_model.extract_text.return_value = {
        "text": "Test hybrid text",
        "confidence": 0.90,
    }
    
    # Configure the factory to return the appropriate model based on document type
    def get_model_for_document(document_type):
        if document_type == "typed":
            return mock_typed_model
        elif document_type == "handwritten":
            return mock_handwritten_model
        else:  # mixed or unknown
            return mock_hybrid_model
    
    mock_factory.get_model_for_document.side_effect = get_model_for_document
    return mock_factory


@pytest.fixture
def test_documents():
    """Fixture for test document data."""
    # Load test document metadata from JSON file
    test_data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_data")
    metadata_path = os.path.join(test_data_dir, "metadata.json")
    
    # If metadata.json doesn't exist, use mock data
    if not os.path.exists(metadata_path):
        return {
            "typed": {
                "document_id": "typed-doc-001",
                "document_type": "typed",
                "storage_key": "typed/typed-doc-001.pdf",
                "expected_fields": {
                    "business_name": {"value": "Acme Corporation", "confidence": 0.98},
                    "tax_id": {"value": "12-3456789", "confidence": 0.95},
                    "address": {"value": "123 Main St, Anytown, USA", "confidence": 0.92},
                    "revenue": {"value": "$1,234,567", "confidence": 0.94},
                },
            },
            "handwritten": {
                "document_id": "handwritten-doc-001",
                "document_type": "handwritten",
                "storage_key": "handwritten/handwritten-doc-001.pdf",
                "expected_fields": {
                    "applicant_name": {"value": "John Smith", "confidence": 0.87},
                    "phone_number": {"value": "555-123-4567", "confidence": 0.82},
                    "signature": {"value": "John Smith", "confidence": 0.79},
                    "date": {"value": "01/15/2023", "confidence": 0.85},
                },
            },
            "mixed": {
                "document_id": "mixed-doc-001",
                "document_type": "mixed",
                "storage_key": "mixed/mixed-doc-001.pdf",
                "expected_fields": {
                    "form_id": {"value": "MCA-2023-001", "confidence": 0.97},  # typed
                    "business_name": {"value": "XYZ Enterprises", "confidence": 0.96},  # typed
                    "owner_signature": {"value": "Jane Doe", "confidence": 0.81},  # handwritten
                    "comments": {"value": "Requesting expedited processing", "confidence": 0.83},  # handwritten
                },
            },
            "error": {
                "document_id": "error-doc-001",
                "document_type": "unknown",
                "storage_key": "error/error-doc-001.pdf",
                "expected_error": "Unsupported document format",
            },
        }
    
    # Load actual metadata from file
    with open(metadata_path, "r") as f:
        return json.load(f)


@pytest.fixture
def mock_ocr_application(app_config, mock_queue_service, mock_storage_service, mock_model_factory):
    """Fixture for mocked OCR application with all dependencies."""
    # Create mock services
    mock_ocr_service = MagicMock(spec=OCRService)
    mock_field_extraction_service = MagicMock(spec=FieldExtractionService)
    mock_confidence_service = MagicMock(spec=ConfidenceService)
    
    # Configure the OCR service to process documents
    def process_document(document_data, document_type, document_id):
        # Simulate document processing
        if document_type == "typed":
            extracted_text = "Test typed document content with business information"
            confidence = 0.95
        elif document_type == "handwritten":
            extracted_text = "Test handwritten document with signature"
            confidence = 0.85
        elif document_type == "mixed":
            extracted_text = "Test mixed document with typed and handwritten content"
            confidence = 0.90
        else:
            raise ValueError(f"Unsupported document type: {document_type}")
        
        return {
            "text": extracted_text,
            "confidence": confidence,
            "document_id": document_id,
            "document_type": document_type,
        }
    
    mock_ocr_service.process_document.side_effect = process_document
    
    # Configure the field extraction service
    def extract_fields(ocr_result):
        document_type = ocr_result.get("document_type")
        document_id = ocr_result.get("document_id")
        
        # Create extracted fields based on document type
        if document_type == "typed":
            fields = {
                "business_name": ExtractedField(value="Acme Corporation", confidence=ConfidenceScore(0.98)),
                "tax_id": ExtractedField(value="12-3456789", confidence=ConfidenceScore(0.95)),
                "address": ExtractedField(value="123 Main St, Anytown, USA", confidence=ConfidenceScore(0.92)),
                "revenue": ExtractedField(value="$1,234,567", confidence=ConfidenceScore(0.94)),
            }
        elif document_type == "handwritten":
            fields = {
                "applicant_name": ExtractedField(value="John Smith", confidence=ConfidenceScore(0.87)),
                "phone_number": ExtractedField(value="555-123-4567", confidence=ConfidenceScore(0.82)),
                "signature": ExtractedField(value="John Smith", confidence=ConfidenceScore(0.79)),
                "date": ExtractedField(value="01/15/2023", confidence=ConfidenceScore(0.85)),
            }
        elif document_type == "mixed":
            fields = {
                "form_id": ExtractedField(value="MCA-2023-001", confidence=ConfidenceScore(0.97)),
                "business_name": ExtractedField(value="XYZ Enterprises", confidence=ConfidenceScore(0.96)),
                "owner_signature": ExtractedField(value="Jane Doe", confidence=ConfidenceScore(0.81)),
                "comments": ExtractedField(value="Requesting expedited processing", confidence=ConfidenceScore(0.83)),
            }
        else:
            fields = {}
        
        return ExtractedData(
            document_id=document_id,
            document_type=document_type,
            fields=fields,
            metadata={
                "processing_time": 1.25,  # seconds
                "timestamp": get_current_timestamp(),
                "version": "1.0.0",
            }
        )
    
    mock_field_extraction_service.extract_fields.side_effect = extract_fields
    
    # Configure the confidence service
    def evaluate_confidence(extracted_data):
        # Calculate overall confidence score
        if not extracted_data.fields:
            return extracted_data
        
        field_confidences = [field.confidence.value for field in extracted_data.fields.values()]
        overall_confidence = sum(field_confidences) / len(field_confidences)
        
        # Flag low confidence fields
        low_confidence_fields = []
        for field_name, field in extracted_data.fields.items():
            if field.confidence.value < 0.85:  # Threshold for low confidence
                low_confidence_fields.append(field_name)
        
        # Update metadata with confidence information
        extracted_data.metadata["overall_confidence"] = overall_confidence
        extracted_data.metadata["low_confidence_fields"] = low_confidence_fields
        extracted_data.metadata["requires_review"] = len(low_confidence_fields) > 0 or overall_confidence < 0.90
        
        return extracted_data
    
    mock_confidence_service.evaluate_confidence.side_effect = evaluate_confidence
    
    # Create the application with mock services
    app = OCRApplication(config=app_config)
    app.queue_service = mock_queue_service
    app.storage_service = mock_storage_service
    app.ocr_service = mock_ocr_service
    app.field_extraction_service = mock_field_extraction_service
    app.confidence_service = mock_confidence_service
    app.model_factory = mock_model_factory
    
    return app


class TestOCRPipeline:
    """Integration tests for the complete OCR processing pipeline."""
    
    def test_typed_document_processing(self, mock_ocr_application, test_documents):
        """Test processing of a typed document through the complete pipeline."""
        # Get test document data
        doc_data = test_documents["typed"]
        document_id = doc_data["document_id"]
        document_type = doc_data["document_type"]
        storage_key = doc_data["storage_key"]
        expected_fields = doc_data["expected_fields"]
        
        # Create a test message payload
        message_payload = MessagePayload(
            document_id=document_id,
            document_type=document_type,
            storage_key=storage_key,
            metadata={
                "source": "test",
                "priority": "normal",
                "timestamp": get_current_timestamp(),
            }
        )
        
        # Process the document through the pipeline
        result = mock_ocr_application.process_document_message(message_payload)
        
        # Verify the result
        assert result is not None
        assert result.document_id == document_id
        assert result.document_type == document_type
        
        # Verify extracted fields match expected values
        for field_name, expected in expected_fields.items():
            assert field_name in result.fields
            assert result.fields[field_name].value == expected["value"]
            assert abs(result.fields[field_name].confidence.value - expected["confidence"]) < 0.01
        
        # Verify metadata
        assert "processing_time" in result.metadata
        assert "overall_confidence" in result.metadata
        assert result.metadata["overall_confidence"] > 0.90  # High confidence for typed documents
        
        # Verify the result was published to the queue
        mock_ocr_application.queue_service.publish_message.assert_called_once()
    
    def test_handwritten_document_processing(self, mock_ocr_application, test_documents):
        """Test processing of a handwritten document through the complete pipeline."""
        # Get test document data
        doc_data = test_documents["handwritten"]
        document_id = doc_data["document_id"]
        document_type = doc_data["document_type"]
        storage_key = doc_data["storage_key"]
        expected_fields = doc_data["expected_fields"]
        
        # Create a test message payload
        message_payload = MessagePayload(
            document_id=document_id,
            document_type=document_type,
            storage_key=storage_key,
            metadata={
                "source": "test",
                "priority": "normal",
                "timestamp": get_current_timestamp(),
            }
        )
        
        # Process the document through the pipeline
        result = mock_ocr_application.process_document_message(message_payload)
        
        # Verify the result
        assert result is not None
        assert result.document_id == document_id
        assert result.document_type == document_type
        
        # Verify extracted fields match expected values
        for field_name, expected in expected_fields.items():
            assert field_name in result.fields
            assert result.fields[field_name].value == expected["value"]
            assert abs(result.fields[field_name].confidence.value - expected["confidence"]) < 0.01
        
        # Verify metadata
        assert "processing_time" in result.metadata
        assert "overall_confidence" in result.metadata
        assert "low_confidence_fields" in result.metadata
        
        # Handwritten documents typically have lower confidence
        assert result.metadata["overall_confidence"] > 0.80
        
        # Verify the result was published to the queue
        mock_ocr_application.queue_service.publish_message.assert_called_once()
    
    def test_mixed_document_processing(self, mock_ocr_application, test_documents):
        """Test processing of a mixed document (typed and handwritten) through the complete pipeline."""
        # Get test document data
        doc_data = test_documents["mixed"]
        document_id = doc_data["document_id"]
        document_type = doc_data["document_type"]
        storage_key = doc_data["storage_key"]
        expected_fields = doc_data["expected_fields"]
        
        # Create a test message payload
        message_payload = MessagePayload(
            document_id=document_id,
            document_type=document_type,
            storage_key=storage_key,
            metadata={
                "source": "test",
                "priority": "normal",
                "timestamp": get_current_timestamp(),
            }
        )
        
        # Process the document through the pipeline
        result = mock_ocr_application.process_document_message(message_payload)
        
        # Verify the result
        assert result is not None
        assert result.document_id == document_id
        assert result.document_type == document_type
        
        # Verify extracted fields match expected values
        for field_name, expected in expected_fields.items():
            assert field_name in result.fields
            assert result.fields[field_name].value == expected["value"]
            assert abs(result.fields[field_name].confidence.value - expected["confidence"]) < 0.01
        
        # Verify metadata
        assert "processing_time" in result.metadata
        assert "overall_confidence" in result.metadata
        assert "low_confidence_fields" in result.metadata
        
        # Mixed documents have varying confidence levels
        assert result.metadata["overall_confidence"] > 0.85
        
        # Verify the result was published to the queue
        mock_ocr_application.queue_service.publish_message.assert_called_once()
    
    def test_error_handling(self, mock_ocr_application, test_documents):
        """Test error handling in the OCR pipeline."""
        # Get test document data for error case
        doc_data = test_documents["error"]
        document_id = doc_data["document_id"]
        document_type = doc_data["document_type"]
        storage_key = doc_data["storage_key"]
        expected_error = doc_data["expected_error"]
        
        # Create a test message payload
        message_payload = MessagePayload(
            document_id=document_id,
            document_type=document_type,
            storage_key=storage_key,
            metadata={
                "source": "test",
                "priority": "normal",
                "timestamp": get_current_timestamp(),
            }
        )
        
        # Configure OCR service to raise an error
        mock_ocr_application.ocr_service.process_document.side_effect = ValueError(expected_error)
        
        # Process the document and expect error handling
        with pytest.raises(ValueError) as excinfo:
            mock_ocr_application.process_document_message(message_payload)
        
        # Verify the error message
        assert expected_error in str(excinfo.value)
        
        # Verify error was logged (would check logs in a real test)
        # Verify no result was published to the queue
        mock_ocr_application.queue_service.publish_message.assert_not_called()
    
    def test_performance_metrics(self, mock_ocr_application, test_documents):
        """Test performance metrics for document processing."""
        # Get test document data
        doc_data = test_documents["typed"]
        document_id = doc_data["document_id"]
        document_type = doc_data["document_type"]
        storage_key = doc_data["storage_key"]
        
        # Create a test message payload
        message_payload = MessagePayload(
            document_id=document_id,
            document_type=document_type,
            storage_key=storage_key,
            metadata={
                "source": "test",
                "priority": "normal",
                "timestamp": get_current_timestamp(),
            }
        )
        
        # Measure processing time
        start_time = time.time()
        result = mock_ocr_application.process_document_message(message_payload)
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Verify processing time is within acceptable limits (5 minutes = 300 seconds)
        # For tests, we expect much faster processing
        assert processing_time < 300, f"Processing time {processing_time} exceeds 5 minute limit"
        
        # Verify processing time is recorded in metadata
        assert "processing_time" in result.metadata
        
        # Verify accuracy metrics
        assert "overall_confidence" in result.metadata
        assert result.metadata["overall_confidence"] > 0.90  # 90% confidence minimum
    
    def test_document_classification_integration(self, mock_ocr_application, test_documents):
        """Test that document classification correctly selects the appropriate OCR model."""
        # Test with different document types
        for doc_type in ["typed", "handwritten", "mixed"]:
            # Get test document data
            doc_data = test_documents[doc_type]
            document_id = doc_data["document_id"]
            document_type = doc_data["document_type"]
            storage_key = doc_data["storage_key"]
            
            # Create a test message payload
            message_payload = MessagePayload(
                document_id=document_id,
                document_type=document_type,
                storage_key=storage_key,
                metadata={
                    "source": "test",
                    "priority": "normal",
                    "timestamp": get_current_timestamp(),
                }
            )
            
            # Process the document
            mock_ocr_application.process_document_message(message_payload)
            
            # Verify the correct model was selected based on document type
            mock_ocr_application.model_factory.get_model_for_document.assert_called_with(document_type)
    
    def test_confidence_scoring_integration(self, mock_ocr_application, test_documents):
        """Test that confidence scoring correctly identifies low-confidence fields."""
        # Get test document data for handwritten document (typically lower confidence)
        doc_data = test_documents["handwritten"]
        document_id = doc_data["document_id"]
        document_type = doc_data["document_type"]
        storage_key = doc_data["storage_key"]
        expected_fields = doc_data["expected_fields"]
        
        # Identify fields with expected low confidence
        expected_low_confidence_fields = [
            field_name for field_name, field_data in expected_fields.items() 
            if field_data["confidence"] < 0.85
        ]
        
        # Create a test message payload
        message_payload = MessagePayload(
            document_id=document_id,
            document_type=document_type,
            storage_key=storage_key,
            metadata={
                "source": "test",
                "priority": "normal",
                "timestamp": get_current_timestamp(),
            }
        )
        
        # Process the document
        result = mock_ocr_application.process_document_message(message_payload)
        
        # Verify low confidence fields are correctly identified
        assert "low_confidence_fields" in result.metadata
        for field_name in expected_low_confidence_fields:
            assert field_name in result.metadata["low_confidence_fields"]
        
        # Verify review flag is set appropriately
        assert "requires_review" in result.metadata
        assert result.metadata["requires_review"] == (len(expected_low_confidence_fields) > 0)
    
    def test_end_to_end_pipeline(self, mock_ocr_application, test_documents):
        """Test the complete end-to-end OCR pipeline with all components."""
        # Test with each document type
        for doc_type in ["typed", "handwritten", "mixed"]:
            # Get test document data
            doc_data = test_documents[doc_type]
            document_id = doc_data["document_id"]
            document_type = doc_data["document_type"]
            storage_key = doc_data["storage_key"]
            
            # Create a test message payload
            message_payload = MessagePayload(
                document_id=document_id,
                document_type=document_type,
                storage_key=storage_key,
                metadata={
                    "source": "test",
                    "priority": "normal",
                    "timestamp": get_current_timestamp(),
                }
            )
            
            # Reset mock call counts
            mock_ocr_application.storage_service.download_document.reset_mock()
            mock_ocr_application.ocr_service.process_document.reset_mock()
            mock_ocr_application.field_extraction_service.extract_fields.reset_mock()
            mock_ocr_application.confidence_service.evaluate_confidence.reset_mock()
            mock_ocr_application.storage_service.upload_result.reset_mock()
            mock_ocr_application.queue_service.publish_message.reset_mock()
            
            # Process the document
            result = mock_ocr_application.process_document_message(message_payload)
            
            # Verify all pipeline components were called in the correct order
            mock_ocr_application.storage_service.download_document.assert_called_once()
            mock_ocr_application.ocr_service.process_document.assert_called_once()
            mock_ocr_application.field_extraction_service.extract_fields.assert_called_once()
            mock_ocr_application.confidence_service.evaluate_confidence.assert_called_once()
            mock_ocr_application.storage_service.upload_result.assert_called_once()
            mock_ocr_application.queue_service.publish_message.assert_called_once()
            
            # Verify the final result
            assert result is not None
            assert result.document_id == document_id
            assert result.document_type == document_type
            assert len(result.fields) > 0
            assert "overall_confidence" in result.metadata
            assert "processing_time" in result.metadata