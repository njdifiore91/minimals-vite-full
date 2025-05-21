"""
Unit tests for the DocumentClassifier class.

This module contains tests for the DocumentClassifier class, which is the main
orchestrator of the document classification process in the Document Service.
The tests verify that the classifier correctly combines feature extraction,
model selection, prediction, confidence scoring, and document routing.
"""

import logging
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime

from ..types.classification import DocumentType, ClassificationResult, ConfidenceScore, FeatureExtractor
from ..types.documents import Document, ProcessingStatus
from ..models.document_classifier import DocumentClassifier
from ..models.svm_classifier import SVMClassifier
from ..models.random_forest_classifier import RandomForestClassifier as RFClassifier


class TestDocumentClassifier:
    """Test suite for the DocumentClassifier class.
    
    This class contains tests for the DocumentClassifier, which is the main
    component that orchestrates the document classification process. The tests
    verify initialization, feature extraction, model fitting, prediction,
    confidence scoring, document routing, and model evaluation.
    """
    
    def test_init_with_default_parameters(self):
        """Test initialization with default parameters."""
        # Arrange & Act
        classifier = DocumentClassifier()
        
        # Assert
        assert classifier.confidence_threshold == 0.75
        assert classifier.svm_model is not None
        assert classifier.random_forest_model is not None
        assert classifier.ensemble_model is not None
        assert len(classifier.feature_extractors) == 0
        
    def test_init_with_custom_parameters(self):
        """Test initialization with custom parameters."""
        # Arrange
        svm_model = MagicMock()
        rf_model = MagicMock()
        feature_extractors = [MagicMock()]
        confidence_threshold = 0.85
        
        # Act
        classifier = DocumentClassifier(
            svm_model=svm_model,
            random_forest_model=rf_model,
            feature_extractors=feature_extractors,
            confidence_threshold=confidence_threshold
        )
        
        # Assert
        assert classifier.confidence_threshold == confidence_threshold
        assert classifier.svm_model is svm_model
        assert classifier.random_forest_model is rf_model
        assert classifier.feature_extractors is feature_extractors
        assert classifier.ensemble_model is not None
        
    def test_load_model_config(self):
        """Test loading model configuration."""
        # Arrange
        with patch('..config.model_config') as mock_config:
            mock_config.DEFAULT_CONFIDENCE_THRESHOLD = 0.8
            mock_config.DEFAULT_FEATURE_EXTRACTORS = [MagicMock()]
            
            # Act
            classifier = DocumentClassifier(model_config_path='/path/to/config')
            
            # Assert
            assert classifier.confidence_threshold == 0.8
            assert len(classifier.feature_extractors) == 1
            
    def test_initialize_models(self):
        """Test model initialization."""
        # Arrange & Act
        classifier = DocumentClassifier()
        
        # Assert
        assert isinstance(classifier.svm_model, SVMClassifier)
        assert isinstance(classifier.random_forest_model, RFClassifier)
        
    def test_build_ensemble_model(self):
        """Test building the ensemble model."""
        # Arrange
        svm_model = MagicMock()
        rf_model = MagicMock()
        
        # Act
        classifier = DocumentClassifier(
            svm_model=svm_model,
            random_forest_model=rf_model
        )
        
        # Assert
        assert classifier.ensemble_model is not None
        assert len(classifier.ensemble_model.estimators) == 2
        assert classifier.ensemble_model.voting == 'soft'
        
    def test_extract_features_with_extractors(self, generate_test_document):
        """Test feature extraction with configured extractors."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        extractor1 = MagicMock(spec=FeatureExtractor)
        extractor1.name = 'extractor1'
        extractor1.feature_names = ['feature1', 'feature2']
        extractor1.extract.return_value = np.array([1.0, 2.0])
        
        extractor2 = MagicMock(spec=FeatureExtractor)
        extractor2.name = 'extractor2'
        extractor2.feature_names = ['feature3', 'feature4']
        extractor2.extract.return_value = np.array([3.0, 4.0])
        
        classifier = DocumentClassifier(
            feature_extractors=[extractor1, extractor2]
        )
        
        # Act
        features = classifier.extract_features(document)
        
        # Assert
        extractor1.extract.assert_called_once_with(document.content)
        extractor2.extract.assert_called_once_with(document.content)
        assert features.shape == (4,)
        assert np.array_equal(features, np.array([1.0, 2.0, 3.0, 4.0]))
        assert classifier.feature_names == ['feature1', 'feature2', 'feature3', 'feature4']
        
    def test_extract_features_with_no_extractors(self, generate_test_document):
        """Test feature extraction with no configured extractors."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        with patch('..models.feature_extraction.extract_document_features') as mock_extract:
            mock_extract.return_value = (np.array([1.0, 2.0, 3.0]), ['f1', 'f2', 'f3'])
            
            classifier = DocumentClassifier()
            
            # Act
            features = classifier.extract_features(document)
            
            # Assert
            mock_extract.assert_called_once_with(document.content)
            assert features.shape == (3,)
            assert np.array_equal(features, np.array([1.0, 2.0, 3.0]))
            assert classifier.feature_names == ['f1', 'f2', 'f3']
            
    def test_extract_features_with_empty_document(self, generate_test_document):
        """Test feature extraction with empty document content."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        document.content = None
        
        classifier = DocumentClassifier()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Document content is required"):
            classifier.extract_features(document)
            
    def test_fit(self, generate_document_batch):
        """Test fitting the classifier to training data."""
        # Arrange
        documents = [Document.from_dict(doc) for doc in generate_document_batch(5)]
        document_types = [DocumentType.APPLICATION, DocumentType.BANK_STATEMENT, 
                          DocumentType.TAX_RETURN, DocumentType.ID_DOCUMENT, 
                          DocumentType.OTHER]
        
        classifier = DocumentClassifier()
        
        # Mock extract_features to return a simple feature vector
        classifier.extract_features = MagicMock(return_value=np.array([1.0, 2.0, 3.0]))
        
        # Mock the underlying models
        classifier.svm_model.fit = MagicMock()
        classifier.random_forest_model.fit = MagicMock()
        classifier.ensemble_model.fit = MagicMock()
        
        # Act
        classifier.fit(documents, document_types)
        
        # Assert
        assert classifier.extract_features.call_count == 5
        classifier.svm_model.fit.assert_called_once()
        classifier.random_forest_model.fit.assert_called_once()
        classifier.ensemble_model.fit.assert_called_once()
        assert len(classifier.document_type_mapping) == 5
        
    def test_fit_with_mismatched_lengths(self, generate_document_batch):
        """Test fitting with mismatched document and label lengths."""
        # Arrange
        documents = [Document.from_dict(doc) for doc in generate_document_batch(5)]
        document_types = [DocumentType.APPLICATION, DocumentType.BANK_STATEMENT]  # Only 2 types
        
        classifier = DocumentClassifier()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Number of documents and document types must match"):
            classifier.fit(documents, document_types)
            
    def test_predict(self, generate_test_document):
        """Test predicting document type."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        classifier = DocumentClassifier()
        classifier.extract_features = MagicMock(return_value=np.array([1.0, 2.0, 3.0]))
        
        # Mock the ensemble model
        classifier.ensemble_model = MagicMock()
        classifier.ensemble_model.predict.return_value = np.array([0])
        classifier.ensemble_model.predict_proba.return_value = np.array([[0.8, 0.1, 0.1]])
        classifier.ensemble_model.classes_ = np.array([0, 1, 2])
        
        # Set up document type mapping
        classifier.document_type_mapping = {
            0: DocumentType.APPLICATION,
            1: DocumentType.BANK_STATEMENT,
            2: DocumentType.TAX_RETURN
        }
        
        # Act
        doc_type, confidence = classifier.predict(document)
        
        # Assert
        assert doc_type == DocumentType.APPLICATION
        assert confidence == 0.8
        classifier.extract_features.assert_called_once_with(document)
        classifier.ensemble_model.predict.assert_called_once()
        classifier.ensemble_model.predict_proba.assert_called_once()
        
    def test_predict_with_untrained_model(self, generate_test_document):
        """Test predicting with an untrained model."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        classifier = DocumentClassifier()
        classifier.ensemble_model = MagicMock()
        # Untrained model doesn't have classes_ attribute
        delattr(classifier.ensemble_model, 'classes_')
        
        # Act & Assert
        with pytest.raises(ValueError, match="Model has not been trained"):
            classifier.predict(document)
            
    def test_classify_document(self, generate_test_document):
        """Test the complete document classification workflow."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        classifier = DocumentClassifier()
        
        # Mock predict method
        classifier.predict = MagicMock(return_value=(DocumentType.APPLICATION, 0.9))
        
        # Mock random forest feature importances
        classifier.random_forest_model = MagicMock()
        classifier.random_forest_model.feature_importances_ = np.array([0.5, 0.3, 0.2])
        classifier.feature_names = ['feature1', 'feature2', 'feature3']
        
        # Act
        result = classifier.classify_document(document)
        
        # Assert
        assert result.document_type == DocumentType.APPLICATION
        assert result.confidence == 0.9
        assert result.requires_review is False  # High confidence
        assert isinstance(result.prediction_time, datetime)
        assert len(result.feature_importance) == 3
        assert document.status == ProcessingStatus.CLASSIFIED
        
    def test_classify_document_low_confidence(self, generate_test_document):
        """Test classification with low confidence requiring review."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        classifier = DocumentClassifier()
        
        # Mock predict method with low confidence
        classifier.predict = MagicMock(return_value=(DocumentType.APPLICATION, 0.6))
        
        # Act
        result = classifier.classify_document(document)
        
        # Assert
        assert result.requires_review is True
        assert document.status == ProcessingStatus.REVIEW
        
    def test_classify_document_with_error(self, generate_test_document):
        """Test classification with an error."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        classifier = DocumentClassifier()
        
        # Mock predict method to raise an exception
        classifier.predict = MagicMock(side_effect=Exception("Test error"))
        
        # Act
        result = classifier.classify_document(document)
        
        # Assert
        assert result.document_type == DocumentType.OTHER
        assert result.confidence == 0.0
        assert result.requires_review is True
        assert document.status == ProcessingStatus.ERROR
        assert document.processing_error is not None
        assert document.processing_error['error_code'] == 'CLASSIFICATION_ERROR'
        
    def test_get_confidence_scores(self, generate_test_document):
        """Test getting confidence scores for all document types."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        classifier = DocumentClassifier()
        classifier.extract_features = MagicMock(return_value=np.array([1.0, 2.0, 3.0]))
        
        # Mock the ensemble model
        classifier.ensemble_model = MagicMock()
        classifier.ensemble_model.predict_proba.return_value = np.array([[0.7, 0.2, 0.1]])
        classifier.ensemble_model.classes_ = np.array([0, 1, 2])
        
        # Set up document type mapping
        classifier.document_type_mapping = {
            0: DocumentType.APPLICATION,
            1: DocumentType.BANK_STATEMENT,
            2: DocumentType.TAX_RETURN
        }
        
        # Act
        confidence_scores = classifier._get_confidence_scores(document)
        
        # Assert
        assert len(confidence_scores) == 3
        assert confidence_scores[DocumentType.APPLICATION.value] == 0.7
        assert confidence_scores[DocumentType.BANK_STATEMENT.value] == 0.2
        assert confidence_scores[DocumentType.TAX_RETURN.value] == 0.1
        
    def test_get_routing_info(self, generate_test_document):
        """Test getting routing information for a classified document."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        # Set up document with classification result
        document.document_type = DocumentType.APPLICATION
        document.classification_result = {
            'document_type': DocumentType.APPLICATION,
            'confidence': 0.9,
            'confidence_scores': {
                'application': 0.9,
                'bank_statement': 0.05,
                'tax_return': 0.05
            },
            'features_used': ['feature1', 'feature2'],
            'model_version': '1.0.0',
            'classified_at': datetime.now(),
            'requires_review': False
        }
        
        # Add metadata
        document.metadata['page_count'] = 5
        document.metadata['mime_type'] = 'application/pdf'
        
        classifier = DocumentClassifier()
        
        # Act
        routing_info = classifier.get_routing_info(document)
        
        # Assert
        assert routing_info['document_type'] == 'application'
        assert routing_info['confidence'] == 0.9
        assert routing_info['requires_review'] is False
        assert routing_info['ocr_pipeline'] == 'application_form'
        assert routing_info['priority'] == 'high'
        assert routing_info['page_count'] == 5
        assert routing_info['mime_type'] == 'application/pdf'
        
    def test_get_routing_info_with_low_confidence(self, generate_test_document):
        """Test routing with low confidence requiring review."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        # Set up document with low confidence classification result
        document.document_type = DocumentType.APPLICATION
        document.classification_result = {
            'document_type': DocumentType.APPLICATION,
            'confidence': 0.6,
            'confidence_scores': {
                'application': 0.6,
                'bank_statement': 0.2,
                'tax_return': 0.2
            },
            'features_used': ['feature1', 'feature2'],
            'model_version': '1.0.0',
            'classified_at': datetime.now(),
            'requires_review': True
        }
        
        classifier = DocumentClassifier()
        
        # Act
        routing_info = classifier.get_routing_info(document)
        
        # Assert
        assert routing_info['requires_review'] is True
        assert routing_info['ocr_pipeline'] == 'application_form_review'
        
    def test_get_routing_info_with_unclassified_document(self, generate_test_document):
        """Test routing with an unclassified document."""
        # Arrange
        document = Document.from_dict(generate_test_document('application_form'))
        
        # Document has not been classified
        document.document_type = None
        document.classification_result = None
        
        classifier = DocumentClassifier()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Document must be classified before routing"):
            classifier.get_routing_info(document)
            
    def test_evaluate(self, generate_document_batch):
        """Test evaluating the classifier on test data."""
        # Arrange
        test_documents = [Document.from_dict(doc) for doc in generate_document_batch(5)]
        true_document_types = [DocumentType.APPLICATION, DocumentType.BANK_STATEMENT, 
                              DocumentType.TAX_RETURN, DocumentType.ID_DOCUMENT, 
                              DocumentType.OTHER]
        
        classifier = DocumentClassifier()
        
        # Mock predict method
        classifier.predict = MagicMock(side_effect=[
            (DocumentType.APPLICATION, 0.9),
            (DocumentType.BANK_STATEMENT, 0.8),
            (DocumentType.TAX_RETURN, 0.7),
            (DocumentType.OTHER, 0.6),  # Incorrect prediction
            (DocumentType.OTHER, 0.5)
        ])
        
        # Mock model_evaluation module
        with patch('..models.model_evaluation.evaluate_classifier') as mock_evaluate:
            mock_evaluate.return_value = MagicMock(
                accuracy=0.8,
                precision={
                    DocumentType.APPLICATION: 1.0,
                    DocumentType.BANK_STATEMENT: 1.0,
                    DocumentType.TAX_RETURN: 1.0,
                    DocumentType.ID_DOCUMENT: 0.0,
                    DocumentType.OTHER: 0.5
                },
                recall={
                    DocumentType.APPLICATION: 1.0,
                    DocumentType.BANK_STATEMENT: 1.0,
                    DocumentType.TAX_RETURN: 1.0,
                    DocumentType.ID_DOCUMENT: 0.0,
                    DocumentType.OTHER: 1.0
                },
                f1_score={
                    DocumentType.APPLICATION: 1.0,
                    DocumentType.BANK_STATEMENT: 1.0,
                    DocumentType.TAX_RETURN: 1.0,
                    DocumentType.ID_DOCUMENT: 0.0,
                    DocumentType.OTHER: 0.67
                }
            )
            
            # Act
            metrics = classifier.evaluate(test_documents, true_document_types)
            
            # Assert
            assert classifier.predict.call_count == 5
            mock_evaluate.assert_called_once()
            assert metrics.accuracy == 0.8
            assert metrics.precision[DocumentType.APPLICATION] == 1.0
            assert metrics.recall[DocumentType.ID_DOCUMENT] == 0.0
            assert metrics.f1_score[DocumentType.OTHER] == 0.67
            
    def test_evaluate_with_mismatched_lengths(self, generate_document_batch):
        """Test evaluation with mismatched document and label lengths."""
        # Arrange
        test_documents = [Document.from_dict(doc) for doc in generate_document_batch(5)]
        true_document_types = [DocumentType.APPLICATION, DocumentType.BANK_STATEMENT]  # Only 2 types
        
        classifier = DocumentClassifier()
        
        # Act & Assert
        with pytest.raises(ValueError, match="Number of test documents and true document types must match"):
            classifier.evaluate(test_documents, true_document_types)
            
    def test_save(self, temp_model_path):
        """Test saving the classifier to disk."""
        # Arrange
        classifier = DocumentClassifier()
        classifier.feature_names = ['feature1', 'feature2', 'feature3']
        classifier.document_type_mapping = {
            0: DocumentType.APPLICATION,
            1: DocumentType.BANK_STATEMENT,
            2: DocumentType.TAX_RETURN
        }
        
        # Mock model_serialization module
        with patch('..models.model_serialization.save_model') as mock_save:
            # Act
            classifier.save(temp_model_path)
            
            # Assert
            mock_save.assert_called_once()
            args, kwargs = mock_save.call_args
            assert args[0] is classifier
            assert args[1] == temp_model_path
            assert 'metadata' in kwargs
            assert kwargs['metadata']['model_type'] == 'ensemble'
            assert kwargs['metadata']['components'] == ['svm', 'random_forest']
            assert kwargs['metadata']['feature_names'] == classifier.feature_names
            
    def test_load(self, temp_model_path):
        """Test loading the classifier from disk."""
        # Arrange
        # Mock model_serialization module
        with patch('..models.model_serialization.load_model') as mock_load:
            mock_classifier = MagicMock()
            mock_metadata = {
                'version': '1.0.0',
                'created_at': '2023-01-01T00:00:00'
            }
            mock_load.return_value = (mock_classifier, mock_metadata)
            
            # Act
            loaded_classifier = DocumentClassifier.load(temp_model_path)
            
            # Assert
            mock_load.assert_called_once_with(temp_model_path)
            assert loaded_classifier is mock_classifier
            
    def test_get_model_info(self):
        """Test getting model information."""
        # Arrange
        classifier = DocumentClassifier()
        classifier.feature_names = ['feature1', 'feature2', 'feature3']
        
        # Mock ensemble model
        classifier.ensemble_model = MagicMock()
        classifier.ensemble_model.classes_ = np.array([0, 1, 2])
        
        # Act
        model_info = classifier.get_model_info()
        
        # Assert
        assert model_info['model_type'] == 'ensemble'
        assert model_info['components'] == ['svm', 'random_forest']
        assert model_info['confidence_threshold'] == 0.75
        assert model_info['feature_count'] == 3
        assert len(model_info['document_types']) == 6  # All DocumentType enum values
        assert model_info['trained'] is True