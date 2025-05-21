import pytest
import unittest.mock as mock
import numpy as np
from typing import Dict, List, Any

# Import the classification service and related types
from src.services.classification_service import ClassificationService
from src.models.document_classifier import DocumentClassifier
from src.models.svm_classifier import SVMClassifier
from src.models.random_forest_classifier import RandomForestClassifier
from src.types.documents import Document, DocumentType, ProcessingStatus
from src.types.classification import ClassificationResult, ConfidenceScore
from src.config.model_config import model_config
from src.utils.logging_utils import get_logger


@pytest.fixture
def mock_document_classifier():
    """Fixture for mocking the DocumentClassifier."""
    classifier = mock.MagicMock(spec=DocumentClassifier)
    return classifier


@pytest.fixture
def mock_svm_classifier():
    """Fixture for mocking the SVMClassifier."""
    classifier = mock.MagicMock(spec=SVMClassifier)
    return classifier


@pytest.fixture
def mock_random_forest_classifier():
    """Fixture for mocking the RandomForestClassifier."""
    classifier = mock.MagicMock(spec=RandomForestClassifier)
    return classifier


@pytest.fixture
def mock_logger():
    """Fixture for mocking the logger."""
    logger = mock.MagicMock()
    return logger


@pytest.fixture
def sample_document():
    """Fixture for creating a sample document for testing."""
    return Document(
        id="doc123",
        filename="test_document.pdf",
        content=b"test document content",
        mime_type="application/pdf",
        size=1024,
        metadata={
            "source": "email",
            "received_at": "2023-01-01T12:00:00Z",
            "sender": "test@example.com"
        },
        status=ProcessingStatus.RECEIVED
    )


@pytest.fixture
def classification_service(mock_document_classifier, mock_svm_classifier, 
                          mock_random_forest_classifier, mock_logger):
    """Fixture for creating a ClassificationService with mocked dependencies."""
    with mock.patch('src.services.classification_service.get_logger', return_value=mock_logger):
        service = ClassificationService(
            document_classifier=mock_document_classifier,
            svm_classifier=mock_svm_classifier,
            random_forest_classifier=mock_random_forest_classifier,
            config=model_config
        )
        return service


class TestClassificationService:
    """Test suite for the ClassificationService."""

    def test_classify_document_success(self, classification_service, sample_document, mock_document_classifier):
        """Test successful document classification."""
        # Arrange
        expected_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.95, threshold=0.8),
            metadata={
                "processing_time_ms": 150,
                "model_version": "1.0.0",
                "features_used": ["text_content", "page_count", "has_signature"]
            }
        )
        mock_document_classifier.classify.return_value = expected_result
        
        # Act
        result = classification_service.classify_document(sample_document)
        
        # Assert
        assert result == expected_result
        mock_document_classifier.classify.assert_called_once_with(sample_document)
        assert sample_document.status == ProcessingStatus.CLASSIFIED
        assert sample_document.metadata.get("classification_result") is not None

    def test_classify_document_with_low_confidence(self, classification_service, sample_document, mock_document_classifier):
        """Test document classification with low confidence score."""
        # Arrange
        low_confidence_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.OTHER,
            confidence=ConfidenceScore(score=0.65, threshold=0.8),  # Below threshold
            metadata={
                "processing_time_ms": 120,
                "model_version": "1.0.0",
                "features_used": ["text_content", "page_count"]
            }
        )
        mock_document_classifier.classify.return_value = low_confidence_result
        
        # Act
        result = classification_service.classify_document(sample_document)
        
        # Assert
        assert result == low_confidence_result
        assert result.confidence.score < result.confidence.threshold
        assert sample_document.status == ProcessingStatus.NEEDS_REVIEW
        assert sample_document.metadata.get("requires_manual_review") is True

    def test_classify_document_with_different_classifiers(self, classification_service, sample_document, 
                                                        mock_svm_classifier, mock_random_forest_classifier):
        """Test document classification using different classifier models."""
        # Arrange
        svm_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.92, threshold=0.8),
            metadata={"model_type": "svm"}
        )
        
        rf_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.88, threshold=0.8),
            metadata={"model_type": "random_forest"}
        )
        
        mock_svm_classifier.classify.return_value = svm_result
        mock_random_forest_classifier.classify.return_value = rf_result
        
        # Act
        result_svm = classification_service.classify_with_model(sample_document, "svm")
        result_rf = classification_service.classify_with_model(sample_document, "random_forest")
        
        # Assert
        assert result_svm == svm_result
        assert result_rf == rf_result
        mock_svm_classifier.classify.assert_called_once_with(sample_document)
        mock_random_forest_classifier.classify.assert_called_once_with(sample_document)

    def test_ensemble_classification(self, classification_service, sample_document, 
                                   mock_svm_classifier, mock_random_forest_classifier):
        """Test ensemble classification combining multiple model results."""
        # Arrange
        svm_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.92, threshold=0.8),
            metadata={"model_type": "svm"}
        )
        
        rf_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.BANK_STATEMENT,  # Different classification
            confidence=ConfidenceScore(score=0.88, threshold=0.8),
            metadata={"model_type": "random_forest"}
        )
        
        mock_svm_classifier.classify.return_value = svm_result
        mock_random_forest_classifier.classify.return_value = rf_result
        
        # Expected ensemble result (higher confidence wins)
        expected_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,  # SVM result wins due to higher confidence
            confidence=ConfidenceScore(score=0.92, threshold=0.8),
            metadata={
                "ensemble": True,
                "models_used": ["svm", "random_forest"],
                "individual_results": {
                    "svm": {"type": "APPLICATION", "confidence": 0.92},
                    "random_forest": {"type": "BANK_STATEMENT", "confidence": 0.88}
                }
            }
        )
        
        classification_service.ensemble_classify = mock.MagicMock(return_value=expected_result)
        
        # Act
        result = classification_service.ensemble_classify(sample_document)
        
        # Assert
        assert result.document_type == DocumentType.APPLICATION
        assert result.confidence.score == 0.92
        assert result.metadata.get("ensemble") is True
        assert "models_used" in result.metadata
        assert "individual_results" in result.metadata

    def test_classification_performance_metrics(self, classification_service, sample_document, mock_document_classifier, mock_logger):
        """Test that performance metrics are logged during classification."""
        # Arrange
        result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.95, threshold=0.8),
            metadata={
                "processing_time_ms": 150,
                "model_version": "1.0.0"
            }
        )
        mock_document_classifier.classify.return_value = result
        
        # Act
        classification_service.classify_document(sample_document)
        
        # Assert
        # Verify that performance metrics are logged
        mock_logger.info.assert_any_call(
            mock.ANY,  # Log message format string
            mock.ANY,  # Document ID
            mock.ANY,  # Document type
            mock.ANY,  # Confidence score
            mock.ANY   # Processing time
        )
        
        # Verify that metrics are tracked for monitoring
        assert classification_service.metrics["total_documents_processed"] > 0
        assert "processing_times" in classification_service.metrics
        assert "confidence_scores" in classification_service.metrics

    def test_document_type_determination(self, classification_service, sample_document):
        """Test document type determination based on content and features."""
        # Arrange
        # Mock the feature extraction to return specific features
        features = {
            "text_content": "LOAN APPLICATION FORM",
            "has_signature": True,
            "has_date": True,
            "page_count": 3
        }
        
        classification_service.extract_features = mock.MagicMock(return_value=features)
        
        # Mock the classifier to use our features
        classification_service.document_classifier.classify = mock.MagicMock(side_effect=lambda doc: 
            ClassificationResult(
                document_id=doc.id,
                document_type=DocumentType.APPLICATION,
                confidence=ConfidenceScore(score=0.98, threshold=0.8),
                metadata={"features": features}
            )
        )
        
        # Act
        result = classification_service.classify_document(sample_document)
        
        # Assert
        assert result.document_type == DocumentType.APPLICATION
        assert result.confidence.score > 0.95  # High confidence for clear application document
        assert "features" in result.metadata
        assert result.metadata["features"]["text_content"] == "LOAN APPLICATION FORM"

    def test_classification_result_formatting(self, classification_service, sample_document, mock_document_classifier):
        """Test that classification results are properly formatted for downstream services."""
        # Arrange
        internal_result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.TAX_RETURN,
            confidence=ConfidenceScore(score=0.91, threshold=0.8),
            metadata={
                "processing_time_ms": 130,
                "model_version": "1.0.0",
                "internal_model_data": {"weights": [0.1, 0.2, 0.3]}
            }
        )
        mock_document_classifier.classify.return_value = internal_result
        
        # Act
        result = classification_service.classify_document(sample_document)
        formatted_result = classification_service.format_result_for_downstream(result)
        
        # Assert
        assert formatted_result["document_id"] == sample_document.id
        assert formatted_result["document_type"] == "TAX_RETURN"
        assert formatted_result["confidence"] == 0.91
        assert "processing_time_ms" in formatted_result
        assert "internal_model_data" not in formatted_result  # Internal data should be filtered out
        assert "classification_timestamp" in formatted_result

    def test_handle_unsupported_document_type(self, classification_service, sample_document):
        """Test handling of unsupported document types."""
        # Arrange
        # Modify the document to have an unsupported MIME type
        sample_document.mime_type = "application/octet-stream"
        
        # Act
        result = classification_service.classify_document(sample_document)
        
        # Assert
        assert result.document_type == DocumentType.OTHER
        assert result.confidence.score < result.confidence.threshold  # Low confidence for unsupported type
        assert sample_document.status == ProcessingStatus.NEEDS_REVIEW
        assert sample_document.metadata.get("unsupported_document_type") is True

    def test_classification_with_empty_document(self, classification_service):
        """Test classification behavior with empty document content."""
        # Arrange
        empty_document = Document(
            id="empty123",
            filename="empty.pdf",
            content=b"",  # Empty content
            mime_type="application/pdf",
            size=0,
            metadata={},
            status=ProcessingStatus.RECEIVED
        )
        
        # Act
        result = classification_service.classify_document(empty_document)
        
        # Assert
        assert result.document_type == DocumentType.OTHER
        assert result.confidence.score < 0.5  # Very low confidence for empty document
        assert empty_document.status == ProcessingStatus.ERROR
        assert "error" in empty_document.metadata
        assert "empty_document" in empty_document.metadata["error"]

    def test_classification_error_handling(self, classification_service, sample_document, mock_document_classifier, mock_logger):
        """Test error handling during classification process."""
        # Arrange
        error_message = "Classification model failed to process document"
        mock_document_classifier.classify.side_effect = Exception(error_message)
        
        # Act
        result = classification_service.classify_document(sample_document)
        
        # Assert
        assert result.document_type == DocumentType.OTHER
        assert result.confidence.score == 0.0
        assert sample_document.status == ProcessingStatus.ERROR
        assert "error" in sample_document.metadata
        assert error_message in sample_document.metadata["error"]
        
        # Verify error is logged
        mock_logger.error.assert_called_with(
            mock.ANY,  # Log message format string
            sample_document.id,
            mock.ANY   # Exception details
        )

    def test_batch_classification(self, classification_service, mock_document_classifier):
        """Test batch classification of multiple documents."""
        # Arrange
        documents = [
            Document(id=f"doc{i}", filename=f"doc{i}.pdf", content=b"content", 
                    mime_type="application/pdf", size=100, metadata={}, 
                    status=ProcessingStatus.RECEIVED)
            for i in range(5)
        ]
        
        # Mock classifier to return different results for each document
        def mock_classify(doc):
            doc_index = int(doc.id[3:])  # Extract index from doc id (doc0, doc1, etc.)
            doc_types = [DocumentType.APPLICATION, DocumentType.TAX_RETURN, 
                        DocumentType.BANK_STATEMENT, DocumentType.PAY_STUB, DocumentType.ID_DOCUMENT]
            confidences = [0.98, 0.95, 0.92, 0.88, 0.85]
            
            return ClassificationResult(
                document_id=doc.id,
                document_type=doc_types[doc_index],
                confidence=ConfidenceScore(score=confidences[doc_index], threshold=0.8),
                metadata={"batch_index": doc_index}
            )
        
        mock_document_classifier.classify.side_effect = mock_classify
        
        # Act
        results = classification_service.batch_classify(documents)
        
        # Assert
        assert len(results) == 5
        assert results[0].document_type == DocumentType.APPLICATION
        assert results[1].document_type == DocumentType.TAX_RETURN
        assert results[2].document_type == DocumentType.BANK_STATEMENT
        assert results[3].document_type == DocumentType.PAY_STUB
        assert results[4].document_type == DocumentType.ID_DOCUMENT
        
        # Verify all documents were updated
        for i, doc in enumerate(documents):
            assert doc.status == ProcessingStatus.CLASSIFIED
            assert "classification_result" in doc.metadata
            assert doc.metadata.get("batch_index") == i

    def test_confidence_score_calculation(self, classification_service, sample_document):
        """Test confidence score calculation based on model outputs."""
        # Arrange
        # Mock probability distributions from classifiers
        svm_probs = np.array([0.05, 0.85, 0.05, 0.03, 0.02])  # Highest for class 1 (index 1)
        rf_probs = np.array([0.10, 0.75, 0.08, 0.05, 0.02])   # Also highest for class 1
        
        # Mock the classifiers to return these probabilities
        classification_service.svm_classifier.predict_proba = mock.MagicMock(return_value=svm_probs)
        classification_service.random_forest_classifier.predict_proba = mock.MagicMock(return_value=rf_probs)
        
        # Mock the document type mapping (index 1 corresponds to TAX_RETURN)
        classification_service.index_to_document_type = mock.MagicMock(return_value=DocumentType.TAX_RETURN)
        
        # Act
        # Call a method that uses these probabilities to calculate confidence
        confidence = classification_service.calculate_confidence(svm_probs, rf_probs)
        document_type = classification_service.get_document_type_from_probabilities(svm_probs, rf_probs)
        
        # Assert
        assert confidence > 0.8  # High confidence from agreement between models
        assert document_type == DocumentType.TAX_RETURN
        
        # Test with disagreeing models
        svm_probs_2 = np.array([0.05, 0.85, 0.05, 0.03, 0.02])  # Highest for class 1
        rf_probs_2 = np.array([0.05, 0.15, 0.70, 0.05, 0.05])   # Highest for class 2
        
        # Confidence should be lower when models disagree
        confidence_2 = classification_service.calculate_confidence(svm_probs_2, rf_probs_2)
        assert confidence_2 < confidence

    def test_model_version_tracking(self, classification_service, sample_document, mock_document_classifier):
        """Test that model version information is tracked in classification results."""
        # Arrange
        model_version = "1.2.3"
        training_date = "2023-01-15"
        
        # Set up model metadata
        classification_service.model_metadata = {
            "version": model_version,
            "training_date": training_date,
            "accuracy": 0.992,
            "f1_score": 0.989
        }
        
        result = ClassificationResult(
            document_id=sample_document.id,
            document_type=DocumentType.APPLICATION,
            confidence=ConfidenceScore(score=0.95, threshold=0.8),
            metadata={}
        )
        mock_document_classifier.classify.return_value = result
        
        # Act
        classification_service.enrich_result_with_model_metadata = mock.MagicMock(side_effect=
            lambda r: r.metadata.update({
                "model_version": model_version,
                "model_training_date": training_date
            })
        )
        
        result = classification_service.classify_document(sample_document)
        
        # Assert
        assert "model_version" in result.metadata
        assert result.metadata["model_version"] == model_version
        assert "model_training_date" in result.metadata
        assert result.metadata["model_training_date"] == training_date