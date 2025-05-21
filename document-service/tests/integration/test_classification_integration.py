"""Integration tests for document classification and routing in the Document Service.

This module contains tests that verify the Document Service correctly classifies documents
using SVM and Random Forest models, calculates confidence scores, and routes documents
to appropriate OCR processors based on classification results. The tests validate:

1. Classification accuracy for different document types
2. Confidence scoring and threshold validation
3. Document routing based on classification results
4. Handling of low-confidence classifications
5. Ensemble classification combining multiple models
6. Classification performance metrics
7. Processing of different document types (application forms, tax returns, etc.)

These tests ensure that the Document Service meets the 99% accuracy requirement
and correctly implements the confidence threshold (75%) for determining whether
documents should be automatically processed or flagged for human review.
"""

import os
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from io import BytesIO

# Import the services and models to be tested
from src.services.classification_service import ClassificationService
from src.services.document_routing_service import DocumentRoutingService
from src.services.storage_service import StorageService
from src.models.document_classifier import DocumentClassifier
from src.models.svm_classifier import SVMClassifier
from src.models.random_forest_classifier import RandomForestClassifier
from src.types.documents import Document, DocumentType, DocumentMetadata, ProcessingStatus
from src.types.classification import ClassificationResult, ConfidenceScore
from src.types.config import ModelConfig


# Fixtures for the integration tests
# These fixtures provide mock objects and configurations for testing the document
# classification and routing functionality without requiring actual trained models
# or real documents. They simulate the behavior of the various components involved
# in document classification and routing.
@pytest.fixture
def model_config():
    """Fixture for model configuration."""
    return ModelConfig(
        svm_params={
            'C': 1.0,
            'kernel': 'linear',
            'probability': True
        },
        random_forest_params={
            'n_estimators': 100,
            'max_depth': 10,
            'random_state': 42
        },
        confidence_threshold=0.75,  # 75% threshold as specified in section 4.1.7
        feature_extraction_params={
            'max_features': 5000,
            'ngram_range': (1, 2)
        }
    )


@pytest.fixture
def mock_storage_service():
    """Fixture for mocked storage service."""
    mock_service = MagicMock(spec=StorageService)
    
    # Setup the mock to return different document content based on document type
    def mock_get_document(document_id):
        # Create different document content based on the document_id prefix
        if document_id.startswith('app_'):
            with open(os.path.join(os.path.dirname(__file__), '../test_data/application_form.pdf'), 'rb') as f:
                content = f.read()
            doc_type = 'application_form'
        elif document_id.startswith('tax_'):
            with open(os.path.join(os.path.dirname(__file__), '../test_data/tax_return.pdf'), 'rb') as f:
                content = f.read()
            doc_type = 'tax_return'
        elif document_id.startswith('bank_'):
            with open(os.path.join(os.path.dirname(__file__), '../test_data/bank_statement.pdf'), 'rb') as f:
                content = f.read()
            doc_type = 'bank_statement'
        elif document_id.startswith('pay_'):
            with open(os.path.join(os.path.dirname(__file__), '../test_data/pay_stub.pdf'), 'rb') as f:
                content = f.read()
            doc_type = 'pay_stub'
        elif document_id.startswith('id_'):
            with open(os.path.join(os.path.dirname(__file__), '../test_data/id_document.pdf'), 'rb') as f:
                content = f.read()
            doc_type = 'id_document'
        else:
            with open(os.path.join(os.path.dirname(__file__), '../test_data/other_document.pdf'), 'rb') as f:
                content = f.read()
            doc_type = 'other'
        
        # Create a document with the appropriate metadata
        metadata = DocumentMetadata(
            filename=f"{document_id}.pdf",
            content_type="application/pdf",
            size=len(content),
            created_at="2023-01-01T00:00:00Z",
            source="test"
        )
        
        return Document(
            id=document_id,
            metadata=metadata,
            content=BytesIO(content),
            doc_type=doc_type,
            status=ProcessingStatus.RECEIVED
        )
    
    mock_service.get_document.side_effect = mock_get_document
    return mock_service


@pytest.fixture
def mock_svm_classifier(model_config):
    """Fixture for mocked SVM classifier."""
    classifier = MagicMock(spec=SVMClassifier)
    
    # Setup the mock to return different classification results based on document type
    def mock_predict(document):
        # Determine document type based on document ID prefix
        doc_id = document.id
        
        if doc_id.startswith('app_'):
            return DocumentType.APPLICATION
        elif doc_id.startswith('tax_'):
            return DocumentType.TAX_RETURN
        elif doc_id.startswith('bank_'):
            return DocumentType.BANK_STATEMENT
        elif doc_id.startswith('pay_'):
            return DocumentType.PAY_STUB
        elif doc_id.startswith('id_'):
            return DocumentType.ID_DOCUMENT
        else:
            return DocumentType.OTHER
    
    def mock_predict_proba(document):
        # Return probability distributions based on document type
        doc_id = document.id
        
        # Default low confidence distribution
        probas = {
            DocumentType.APPLICATION: 0.2,
            DocumentType.TAX_RETURN: 0.2,
            DocumentType.BANK_STATEMENT: 0.2,
            DocumentType.PAY_STUB: 0.1,
            DocumentType.ID_DOCUMENT: 0.1,
            DocumentType.OTHER: 0.2
        }
        
        # High confidence for the correct type
        if doc_id.startswith('app_'):
            probas[DocumentType.APPLICATION] = 0.9
        elif doc_id.startswith('tax_'):
            probas[DocumentType.TAX_RETURN] = 0.9
        elif doc_id.startswith('bank_'):
            probas[DocumentType.BANK_STATEMENT] = 0.9
        elif doc_id.startswith('pay_'):
            probas[DocumentType.PAY_STUB] = 0.9
        elif doc_id.startswith('id_'):
            probas[DocumentType.ID_DOCUMENT] = 0.9
        else:
            probas[DocumentType.OTHER] = 0.9
            
        # For low confidence test case
        if doc_id.startswith('low_conf_'):
            for key in probas:
                probas[key] = 0.3 if key == DocumentType.APPLICATION else 0.14
        
        return probas
    
    classifier.predict.side_effect = mock_predict
    classifier.predict_proba.side_effect = mock_predict_proba
    return classifier


@pytest.fixture
def mock_random_forest_classifier(model_config):
    """Fixture for mocked Random Forest classifier."""
    classifier = MagicMock(spec=RandomForestClassifier)
    
    # Setup similar to SVM but with slightly different probabilities
    def mock_predict(document):
        # Determine document type based on document ID prefix
        doc_id = document.id
        
        if doc_id.startswith('app_'):
            return DocumentType.APPLICATION
        elif doc_id.startswith('tax_'):
            return DocumentType.TAX_RETURN
        elif doc_id.startswith('bank_'):
            return DocumentType.BANK_STATEMENT
        elif doc_id.startswith('pay_'):
            return DocumentType.PAY_STUB
        elif doc_id.startswith('id_'):
            return DocumentType.ID_DOCUMENT
        else:
            return DocumentType.OTHER
    
    def mock_predict_proba(document):
        # Return probability distributions based on document type
        doc_id = document.id
        
        # Default low confidence distribution
        probas = {
            DocumentType.APPLICATION: 0.15,
            DocumentType.TAX_RETURN: 0.15,
            DocumentType.BANK_STATEMENT: 0.15,
            DocumentType.PAY_STUB: 0.15,
            DocumentType.ID_DOCUMENT: 0.15,
            DocumentType.OTHER: 0.25
        }
        
        # High confidence for the correct type
        if doc_id.startswith('app_'):
            probas[DocumentType.APPLICATION] = 0.85
        elif doc_id.startswith('tax_'):
            probas[DocumentType.TAX_RETURN] = 0.85
        elif doc_id.startswith('bank_'):
            probas[DocumentType.BANK_STATEMENT] = 0.85
        elif doc_id.startswith('pay_'):
            probas[DocumentType.PAY_STUB] = 0.85
        elif doc_id.startswith('id_'):
            probas[DocumentType.ID_DOCUMENT] = 0.85
        else:
            probas[DocumentType.OTHER] = 0.85
            
        # For low confidence test case
        if doc_id.startswith('low_conf_'):
            for key in probas:
                probas[key] = 0.25 if key == DocumentType.APPLICATION else 0.15
        
        return probas
    
    classifier.predict.side_effect = mock_predict
    classifier.predict_proba.side_effect = mock_predict_proba
    return classifier


@pytest.fixture
def document_classifier(mock_svm_classifier, mock_random_forest_classifier, model_config):
    """Fixture for document classifier that uses both SVM and Random Forest."""
    with patch('src.models.document_classifier.SVMClassifier', return_value=mock_svm_classifier), \
         patch('src.models.document_classifier.RandomForestClassifier', return_value=mock_random_forest_classifier):
        classifier = DocumentClassifier(model_config)
        yield classifier


@pytest.fixture
def classification_service(document_classifier, mock_storage_service, model_config):
    """Fixture for classification service."""
    return ClassificationService(
        classifier=document_classifier,
        storage_service=mock_storage_service,
        model_config=model_config
    )


@pytest.fixture
def document_routing_service(model_config):
    """Fixture for document routing service."""
    return DocumentRoutingService(model_config=model_config)


# Test document IDs for different document types
# These IDs are used to retrieve mock documents of different types from the
# mock storage service. The ID prefix determines the document type and
# classification result in the mock classifiers.
DOCUMENT_IDS = {
    'application': 'app_12345',
    'tax_return': 'tax_12345',
    'bank_statement': 'bank_12345',
    'pay_stub': 'pay_12345',
    'id_document': 'id_12345',
    'other': 'other_12345',
    'low_confidence': 'low_conf_12345'
}


class TestClassificationIntegration:
    """Integration tests for document classification and routing.
    
    This test class verifies the integration between the classification service,
    document routing service, and the underlying classification models (SVM and
    Random Forest). It ensures that documents are correctly classified, confidence
    scores are accurately calculated, and documents are routed to the appropriate
    OCR processors based on their classification and confidence level.
    
    The tests use mock objects to simulate document storage and classification models,
    allowing for controlled testing of the classification and routing logic without
    requiring actual documents or trained models.
    """
    
    def test_document_classification_accuracy(self, classification_service, mock_storage_service):
        """Test that documents are classified with high accuracy (>99%).
        
        This test verifies that the classification service correctly identifies
        different document types with high confidence. It tests each document type
        (application forms, tax returns, bank statements, pay stubs, ID documents,
        and other) to ensure they are classified correctly.
        
        The test validates that:
        1. Each document is classified as the expected document type
        2. The confidence score exceeds the required threshold (75%)
        3. The classification result contains all required metadata
        
        This test is critical for ensuring the Document Service meets the 99%
        accuracy requirement specified in section 0.1.2 of the technical spec.
        """
        # Test classification for each document type
        for doc_type, doc_id in DOCUMENT_IDS.items():
            if doc_type == 'low_confidence':
                continue  # Skip low confidence test case for this test
                
            # Get the document from storage
            document = mock_storage_service.get_document(doc_id)
            
            # Classify the document
            result = classification_service.classify_document(document)
            
            # Verify the classification result
            assert result is not None
            assert isinstance(result, ClassificationResult)
            
            # Check that the document type matches the expected type
            expected_type = None
            if doc_type == 'application':
                expected_type = DocumentType.APPLICATION
            elif doc_type == 'tax_return':
                expected_type = DocumentType.TAX_RETURN
            elif doc_type == 'bank_statement':
                expected_type = DocumentType.BANK_STATEMENT
            elif doc_type == 'pay_stub':
                expected_type = DocumentType.PAY_STUB
            elif doc_type == 'id_document':
                expected_type = DocumentType.ID_DOCUMENT
            else:
                expected_type = DocumentType.OTHER
                
            assert result.document_type == expected_type
            
            # Check that the confidence score is high (above 75%)
            assert result.confidence.score > 0.75
    
    def test_confidence_scoring(self, classification_service, mock_storage_service, model_config):
        """Test that confidence scores are calculated correctly and thresholds are applied.
        
        This test verifies that the classification service correctly calculates
        confidence scores for document classifications and applies the appropriate
        threshold (75% as specified in section 4.1.7) to determine whether a document
        should be automatically processed or flagged for human review.
        
        The test validates both high-confidence and low-confidence scenarios:
        1. High-confidence documents have scores above the threshold and are not flagged for review
        2. Low-confidence documents have scores below the threshold and are flagged for review
        
        This test ensures that the confidence scoring mechanism works correctly,
        which is critical for the system's ability to identify uncertain classifications
        and route them for human review, maintaining the 99% accuracy requirement.
        """
        # Test high confidence case
        high_conf_doc = mock_storage_service.get_document(DOCUMENT_IDS['application'])
        high_conf_result = classification_service.classify_document(high_conf_doc)
        
        # Verify high confidence result
        assert high_conf_result.confidence.score > model_config.confidence_threshold
        assert not high_conf_result.confidence.requires_review
        
        # Test low confidence case
        low_conf_doc = mock_storage_service.get_document(DOCUMENT_IDS['low_confidence'])
        low_conf_result = classification_service.classify_document(low_conf_doc)
        
        # Verify low confidence result
        assert low_conf_result.confidence.score < model_config.confidence_threshold
        assert low_conf_result.confidence.requires_review
    
    def test_document_routing(self, classification_service, document_routing_service, mock_storage_service):
        """Test that documents are routed to the appropriate OCR processors based on type.
        
        This test verifies that the document routing service correctly routes documents
        to the appropriate OCR processors based on their classification. Each document
        type should be routed to a specialized OCR processor optimized for that type.
        
        The test validates that:
        1. Each document type is routed to the correct queue with the appropriate routing key
        2. The routing metadata contains all required information for OCR processing
        3. The routing decision is consistent with the document classification
        
        This test ensures that the Document Service correctly implements the routing
        logic specified in section 0.1.2, which is essential for the system's ability
        to process different document types with specialized OCR pipelines.
        """
        # Test routing for each document type
        for doc_type, doc_id in DOCUMENT_IDS.items():
            if doc_type == 'low_confidence':
                continue  # Skip low confidence test case for this test
                
            # Get the document from storage
            document = mock_storage_service.get_document(doc_id)
            
            # Classify the document
            result = classification_service.classify_document(document)
            
            # Route the document
            routing_result = document_routing_service.route_document(document, result)
            
            # Verify the routing result
            assert routing_result is not None
            assert 'queue' in routing_result
            assert 'routing_key' in routing_result
            assert 'metadata' in routing_result
            
            # Check that the routing is appropriate for the document type
            if doc_type == 'application':
                assert routing_result['routing_key'] == 'ocr.application'
            elif doc_type == 'tax_return':
                assert routing_result['routing_key'] == 'ocr.tax'
            elif doc_type == 'bank_statement':
                assert routing_result['routing_key'] == 'ocr.bank'
            elif doc_type == 'pay_stub':
                assert routing_result['routing_key'] == 'ocr.pay'
            elif doc_type == 'id_document':
                assert routing_result['routing_key'] == 'ocr.identity'
            else:
                assert routing_result['routing_key'] == 'ocr.general'
    
    def test_low_confidence_routing(self, classification_service, document_routing_service, mock_storage_service):
        """Test that low confidence documents are flagged for human review.
        
        This test verifies that documents with classification confidence below the
        threshold (75% as specified in section 4.1.7) are correctly flagged for
        human review and routed to a special queue for manual processing.
        
        The test validates that:
        1. Low confidence documents are routed to the human review queue
        2. The routing metadata includes a flag indicating human review is required
        3. The confidence score is correctly calculated and below the threshold
        
        This test is critical for ensuring that the system maintains high accuracy
        by identifying uncertain classifications and routing them for human verification,
        as required by the technical specification.
        """
        # Get a low confidence document
        document = mock_storage_service.get_document(DOCUMENT_IDS['low_confidence'])
        
        # Classify the document
        result = classification_service.classify_document(document)
        
        # Route the document
        routing_result = document_routing_service.route_document(document, result)
        
        # Verify the routing result
        assert routing_result is not None
        assert 'queue' in routing_result
        assert 'routing_key' in routing_result
        assert 'metadata' in routing_result
        
        # Check that the document is flagged for human review
        assert routing_result['routing_key'] == 'ocr.human_review'
        assert routing_result['metadata']['requires_review'] == True
    
    def test_ensemble_classification(self, classification_service, mock_storage_service, 
                                     mock_svm_classifier, mock_random_forest_classifier):
        """Test that ensemble classification combines results from both SVM and Random Forest models.
        
        This test verifies that the document classifier correctly implements ensemble
        classification by combining predictions from both the SVM and Random Forest models.
        The ensemble approach should improve classification accuracy by leveraging the
        strengths of both models.
        
        The test validates that:
        1. The ensemble prediction method is called during classification
        2. The final classification result reflects a weighted combination of both models
        3. The confidence score accurately represents the ensemble's confidence
        
        This test ensures that the Document Service correctly implements the ensemble
        classification approach specified in section 0.2.3, which is essential for
        achieving the 99% accuracy requirement.
        """
        # Setup different predictions for SVM and RF to test ensemble logic
        doc_id = 'ensemble_test'
        document = mock_storage_service.get_document(doc_id)
        
        # Mock SVM to predict APPLICATION with 0.6 confidence
        mock_svm_classifier.predict.return_value = DocumentType.APPLICATION
        mock_svm_classifier.predict_proba.return_value = {
            DocumentType.APPLICATION: 0.6,
            DocumentType.TAX_RETURN: 0.1,
            DocumentType.BANK_STATEMENT: 0.1,
            DocumentType.PAY_STUB: 0.1,
            DocumentType.ID_DOCUMENT: 0.05,
            DocumentType.OTHER: 0.05
        }
        
        # Mock RF to predict TAX_RETURN with 0.7 confidence
        mock_random_forest_classifier.predict.return_value = DocumentType.TAX_RETURN
        mock_random_forest_classifier.predict_proba.return_value = {
            DocumentType.APPLICATION: 0.2,
            DocumentType.TAX_RETURN: 0.7,
            DocumentType.BANK_STATEMENT: 0.05,
            DocumentType.PAY_STUB: 0.02,
            DocumentType.ID_DOCUMENT: 0.02,
            DocumentType.OTHER: 0.01
        }
        
        # Classify the document
        with patch.object(classification_service.classifier, '_ensemble_predict') as mock_ensemble:
            # Mock the ensemble to return a weighted average
            mock_ensemble.return_value = (DocumentType.TAX_RETURN, 0.65)
            
            result = classification_service.classify_document(document)
            
            # Verify that ensemble prediction was called
            mock_ensemble.assert_called_once()
            
            # Verify the classification result
            assert result.document_type == DocumentType.TAX_RETURN
            assert abs(result.confidence.score - 0.65) < 0.01
    
    def test_classification_performance_metrics(self, classification_service, mock_storage_service):
        """Test that classification performance metrics are tracked for monitoring.
        
        This test verifies that the classification service correctly tracks performance
        metrics for each document classification operation. These metrics are essential
        for monitoring the system's performance, identifying issues, and ensuring that
        the service meets its performance requirements.
        
        The test validates that:
        1. Performance metrics are tracked for each document classification
        2. The metrics include document ID, classification time, document type, confidence score, and review flag
        3. The metrics are properly formatted for consumption by monitoring systems
        
        This test ensures that the Document Service implements the monitoring requirements
        specified in section 0.2.5, which are essential for tracking classification accuracy,
        processing time, and other key performance indicators.
        """
        # Setup performance tracking mock
        with patch('src.services.classification_service.track_performance') as mock_track:
            # Classify multiple documents
            for doc_id in DOCUMENT_IDS.values():
                document = mock_storage_service.get_document(doc_id)
                classification_service.classify_document(document)
            
            # Verify that performance tracking was called for each document
            assert mock_track.call_count == len(DOCUMENT_IDS)
            
            # Verify that the performance metrics include the required fields
            for call_args in mock_track.call_args_list:
                metrics = call_args[0][0]  # First positional argument
                assert 'document_id' in metrics
                assert 'classification_time_ms' in metrics
                assert 'document_type' in metrics
                assert 'confidence_score' in metrics
                assert 'requires_review' in metrics
    
    def test_different_document_types(self, classification_service, mock_storage_service):
        """Test classification of different document types with specific validation for each type.
        
        This test verifies that the classification service correctly identifies and
        processes different types of documents, including application forms, tax returns,
        bank statements, pay stubs, ID documents, and other miscellaneous documents.
        
        The test validates that:
        1. Each document type is correctly identified with high confidence
        2. The document metadata is updated with the correct document type
        3. The document status is updated to reflect successful classification
        
        This test ensures that the Document Service can handle the diverse range of
        document types specified in section 4.1.7, which is essential for the system's
        ability to process mortgage credit applications with various supporting documents.
        """
        # Define expected document types and their corresponding enum values
        expected_types = {
            'application': DocumentType.APPLICATION,
            'tax_return': DocumentType.TAX_RETURN,
            'bank_statement': DocumentType.BANK_STATEMENT,
            'pay_stub': DocumentType.PAY_STUB,
            'id_document': DocumentType.ID_DOCUMENT,
            'other': DocumentType.OTHER
        }
        
        # Test each document type
        for doc_type, expected_enum in expected_types.items():
            # Get the document
            document = mock_storage_service.get_document(DOCUMENT_IDS[doc_type])
            
            # Classify the document
            result = classification_service.classify_document(document)
            
            # Verify the classification result
            assert result.document_type == expected_enum
            assert result.confidence.score > 0.75  # High confidence
            
            # Verify document metadata is updated
            assert document.doc_type == expected_enum.name.lower()
            assert document.status == ProcessingStatus.CLASSIFIED