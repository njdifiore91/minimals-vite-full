#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the document classification service.

This module contains tests that verify the classification service correctly orchestrates
feature extraction, model selection, classification, and confidence scoring to determine
document types with high accuracy.
"""

import pytest
import logging
import json
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, List
import numpy as np

# Import the service to test
from src.services.classification_service import ClassificationService

# Import models and types
from src.models import DocumentClassifier
from src.models.feature_extraction import extract_features
from src.types.classification import ClassificationResult, FeatureVector, ConfidenceScore
from src.types.documents import DocumentType
from src.types.storage import StorageMetadata


@pytest.fixture
def mock_document_classifier():
    """
    Fixture that provides a mocked DocumentClassifier.
    """
    mock_classifier = Mock(spec=DocumentClassifier)
    
    # Configure the mock to return a document type and confidence scores
    mock_classifier.classify.return_value = (
        DocumentType.APPLICATION,
        {
            "application": 0.85,
            "tax_return": 0.05,
            "bank_statement": 0.05,
            "pay_stub": 0.03,
            "id_document": 0.01,
            "other": 0.01
        }
    )
    
    return mock_classifier


@pytest.fixture
def mock_feature_extractor():
    """
    Fixture that provides a mocked feature extraction function.
    """
    with patch('src.models.feature_extraction.extract_features') as mock_extract:
        # Configure the mock to return a feature vector
        mock_extract.return_value = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        yield mock_extract


@pytest.fixture
def mock_confidence_metrics():
    """
    Fixture that provides a mocked confidence metrics calculation function.
    """
    with patch('src.utils.ml_utils.calculate_confidence_metrics') as mock_metrics:
        # Configure the mock to return confidence metrics
        mock_metrics.return_value = {
            "primary_confidence": 0.85,
            "margin": 0.80,  # Difference between top and second highest confidence
            "entropy": 0.75,  # Measure of uncertainty
            "confidence_level": "high"
        }
        yield mock_metrics


@pytest.fixture
def mock_document_validator():
    """
    Fixture that provides a mocked document format validator.
    """
    with patch('src.utils.validation_utils.validate_document_format') as mock_validator:
        # Configure the mock to return True (valid document)
        mock_validator.return_value = True
        yield mock_validator


@pytest.fixture
def classification_service(mock_document_classifier):
    """
    Fixture that provides a ClassificationService instance with mocked dependencies.
    """
    with patch('src.services.classification_service.DocumentClassifier',
              return_value=mock_document_classifier):
        service = ClassificationService()
        # Override confidence threshold for testing
        service.confidence_threshold = 0.7
        # Set document types
        service.document_types = [
            "application", "tax_return", "bank_statement", 
            "pay_stub", "id_document", "other"
        ]
        yield service


@pytest.fixture
def sample_document_data():
    """
    Fixture that provides sample document data for testing.
    """
    # Create a simple PDF-like byte array
    return b'%PDF-1.5\n1 0 obj\n<</Type/Catalog/Pages 2 0 R>>\nendobj\n'


@pytest.fixture
def sample_document_metadata():
    """
    Fixture that provides sample document metadata for testing.
    """
    return {
        "file_name": "test_application.pdf",
        "content_type": "application/pdf",
        "file_size": 1024,
        "page_count": 2
    }


class TestClassificationService:
    """
    Test suite for the ClassificationService class.
    """
    
    def test_initialization(self):
        """
        Test that the ClassificationService initializes correctly.
        """
        with patch('src.services.classification_service.DocumentClassifier'):
            service = ClassificationService()
            
            # Verify that the service has been initialized with expected attributes
            assert hasattr(service, 'classifier')
            assert hasattr(service, 'logger')
            assert hasattr(service, 'confidence_threshold')
            assert hasattr(service, 'document_types')
            assert hasattr(service, 'classification_metrics')
            
            # Verify that metrics are initialized to zero
            assert service.classification_metrics["total_documents"] == 0
            assert service.classification_metrics["successful_classifications"] == 0
            assert service.classification_metrics["low_confidence_classifications"] == 0
            assert service.classification_metrics["failed_classifications"] == 0
    
    def test_classify_document_success(self, classification_service, sample_document_data, 
                                      sample_document_metadata, mock_feature_extractor,
                                      mock_confidence_metrics):
        """
        Test successful document classification with high confidence.
        """
        # Classify the document
        result = classification_service.classify_document(sample_document_data, sample_document_metadata)
        
        # Verify that feature extraction was called
        mock_feature_extractor.assert_called_once_with(sample_document_data, sample_document_metadata)
        
        # Verify that the classifier was called
        classification_service.classifier.classify.assert_called_once()
        
        # Verify that confidence metrics were calculated
        mock_confidence_metrics.assert_called_once()
        
        # Verify the result structure
        assert result["document_type"] == "application"
        assert result["confidence_score"] == 0.85
        assert result["requires_review"] is False  # 0.85 > 0.7 threshold
        assert "confidence_metrics" in result
        assert "storage_metadata" in result
        assert "all_scores" in result
        
        # Verify that metrics were updated
        assert classification_service.classification_metrics["total_documents"] == 1
        assert classification_service.classification_metrics["successful_classifications"] == 1
        assert classification_service.classification_metrics["low_confidence_classifications"] == 0
    
    def test_classify_document_low_confidence(self, classification_service, sample_document_data, 
                                            sample_document_metadata, mock_feature_extractor,
                                            mock_confidence_metrics):
        """
        Test document classification with low confidence requiring review.
        """
        # Configure mock to return low confidence
        mock_confidence_metrics.return_value = {
            "primary_confidence": 0.65,  # Below the 0.7 threshold
            "margin": 0.30,
            "entropy": 1.2,
            "confidence_level": "medium"
        }
        
        # Classify the document
        result = classification_service.classify_document(sample_document_data, sample_document_metadata)
        
        # Verify the result indicates review is required
        assert result["requires_review"] is True
        assert result["confidence_score"] == 0.65
        
        # Verify that metrics were updated correctly
        assert classification_service.classification_metrics["total_documents"] == 1
        assert classification_service.classification_metrics["successful_classifications"] == 0
        assert classification_service.classification_metrics["low_confidence_classifications"] == 1
    
    def test_classify_document_validation_error(self, classification_service, sample_document_data, 
                                              sample_document_metadata, mock_document_validator):
        """
        Test document classification with validation error.
        """
        # Configure validator to raise an exception
        mock_document_validator.side_effect = ValueError("Invalid document format")
        
        # Attempt to classify the document and expect an exception
        with pytest.raises(ValueError, match="Invalid document format"):
            classification_service.classify_document(sample_document_data, sample_document_metadata)
        
        # Verify that metrics were updated correctly
        assert classification_service.classification_metrics["total_documents"] == 1
        assert classification_service.classification_metrics["failed_classifications"] == 1
    
    def test_classify_document_classification_error(self, classification_service, sample_document_data, 
                                                 sample_document_metadata, mock_feature_extractor):
        """
        Test document classification with classification error.
        """
        # Configure classifier to raise an exception
        classification_service.classifier.classify.side_effect = Exception("Classification failed")
        
        # Attempt to classify the document and expect an exception
        with pytest.raises(RuntimeError, match="Document classification failed"):
            classification_service.classify_document(sample_document_data, sample_document_metadata)
        
        # Verify that metrics were updated correctly
        assert classification_service.classification_metrics["total_documents"] == 1
        assert classification_service.classification_metrics["failed_classifications"] == 1
    
    def test_extract_document_features(self, classification_service, sample_document_data, 
                                     sample_document_metadata, mock_feature_extractor):
        """
        Test feature extraction from document.
        """
        # Extract features
        features = classification_service._extract_document_features(sample_document_data, sample_document_metadata)
        
        # Verify that feature extraction was called
        mock_feature_extractor.assert_called_once_with(sample_document_data, sample_document_metadata)
        
        # Verify that features were returned
        assert features is not None
        assert isinstance(features, np.ndarray)
    
    def test_extract_document_features_error(self, classification_service, sample_document_data, 
                                          sample_document_metadata, mock_feature_extractor):
        """
        Test feature extraction with error.
        """
        # Configure feature extractor to raise an exception
        mock_feature_extractor.side_effect = Exception("Feature extraction failed")
        
        # Attempt to extract features and expect an exception
        with pytest.raises(ValueError, match="Feature extraction failed"):
            classification_service._extract_document_features(sample_document_data, sample_document_metadata)
    
    def test_perform_classification(self, classification_service, mock_feature_extractor):
        """
        Test classification of feature vector.
        """
        # Create a feature vector
        features = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        
        # Perform classification
        document_type, confidence_scores = classification_service._perform_classification(features)
        
        # Verify that the classifier was called
        classification_service.classifier.classify.assert_called_once_with(features)
        
        # Verify that document type and confidence scores were returned
        assert document_type == DocumentType.APPLICATION
        assert confidence_scores["application"] == 0.85
    
    def test_perform_classification_error(self, classification_service, mock_feature_extractor):
        """
        Test classification with error.
        """
        # Create a feature vector
        features = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        
        # Configure classifier to raise an exception
        classification_service.classifier.classify.side_effect = Exception("Classification failed")
        
        # Attempt to classify and expect an exception
        with pytest.raises(RuntimeError, match="Classification failed"):
            classification_service._perform_classification(features)
    
    def test_create_classification_result(self, classification_service, mock_confidence_metrics):
        """
        Test creation of classification result.
        """
        # Create test data
        document_type = "application"
        confidence_scores = {
            "application": 0.85,
            "tax_return": 0.05,
            "bank_statement": 0.05,
            "pay_stub": 0.03,
            "id_document": 0.01,
            "other": 0.01
        }
        metadata = {
            "file_name": "test_application.pdf",
            "content_type": "application/pdf",
            "file_size": 1024
        }
        features = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
        
        # Create classification result
        result = classification_service._create_classification_result(
            document_type, confidence_scores, metadata, features
        )
        
        # Verify that confidence metrics were calculated
        mock_confidence_metrics.assert_called_once_with(confidence_scores, document_type)
        
        # Verify the result structure
        assert result["document_type"] == document_type
        assert result["confidence_score"] == 0.85
        assert result["requires_review"] is False  # 0.85 > 0.7 threshold
        assert result["all_scores"] == confidence_scores
        assert result["metadata"] == metadata
        assert "storage_metadata" in result
        assert "feature_summary" in result
    
    def test_create_storage_metadata(self, classification_service):
        """
        Test creation of storage metadata.
        """
        # Create test data
        document_type = "application"
        confidence_metrics = {
            "primary_confidence": 0.85,
            "margin": 0.80,
            "entropy": 0.75,
            "confidence_level": "high"
        }
        requires_review = False
        original_metadata = {
            "file_name": "test_application.pdf",
            "content_type": "application/pdf",
            "file_size": 1024
        }
        
        # Create storage metadata
        storage_metadata = classification_service._create_storage_metadata(
            document_type, confidence_metrics, requires_review, original_metadata
        )
        
        # Verify the metadata structure
        assert storage_metadata["document_type"] == document_type
        assert storage_metadata["classification_confidence"] == 0.85
        assert "classification_timestamp" in storage_metadata
        assert "classification_version" in storage_metadata
        assert storage_metadata["requires_human_review"] is False
        assert "service_version" in storage_metadata
        assert storage_metadata["content_type"] == "application/pdf"
        assert storage_metadata["file_name"] == "test_application.pdf"
        assert storage_metadata["file_size"] == 1024
    
    def test_summarize_features(self, classification_service):
        """
        Test feature vector summarization.
        """
        # Test with numpy array
        features_array = np.array([[0.1, 0.2, 0.3, 0.4, 0.5]])
        summary_array = classification_service._summarize_features(features_array)
        assert "dimensions" in summary_array
        assert summary_array["dimensions"] == features_array.shape
        
        # Test with dictionary
        features_dict = {"feature1": 0.1, "feature2": 0.2, "feature3": 0.3}
        summary_dict = classification_service._summarize_features(features_dict)
        assert "feature_count" in summary_dict
        assert summary_dict["feature_count"] == 3
        
        # Test with other type
        features_other = "not a feature vector"
        summary_other = classification_service._summarize_features(features_other)
        assert "feature_type" in summary_other
        assert summary_other["feature_type"] == "<class 'str'>"
    
    def test_update_performance_metrics(self, classification_service):
        """
        Test updating of performance metrics.
        """
        # Create a test result
        result = {
            "document_type": "application",
            "confidence_score": 0.85,
            "requires_review": False
        }
        processing_time = 0.5  # seconds
        
        # Enable performance metrics
        classification_service.enable_performance_metrics = True
        
        # Update metrics
        classification_service._update_performance_metrics(result, processing_time)
        
        # Verify metrics were updated
        assert classification_service.classification_metrics["total_documents"] == 1
        assert classification_service.classification_metrics["successful_classifications"] == 1
        assert classification_service.classification_metrics["low_confidence_classifications"] == 0
        assert classification_service.classification_metrics["average_confidence"] == 0.85
        assert classification_service.classification_metrics["average_processing_time"] == 0.5
        
        # Add another result with different values
        result2 = {
            "document_type": "tax_return",
            "confidence_score": 0.75,
            "requires_review": False
        }
        processing_time2 = 0.7  # seconds
        
        # Update metrics again
        classification_service._update_performance_metrics(result2, processing_time2)
        
        # Verify metrics were updated correctly
        assert classification_service.classification_metrics["total_documents"] == 2
        assert classification_service.classification_metrics["successful_classifications"] == 2
        assert classification_service.classification_metrics["low_confidence_classifications"] == 0
        # Average confidence should be (0.85 + 0.75) / 2 = 0.8
        assert classification_service.classification_metrics["average_confidence"] == 0.8
        # Average processing time should be (0.5 + 0.7) / 2 = 0.6
        assert classification_service.classification_metrics["average_processing_time"] == 0.6
        
        # Test with a low confidence result
        result3 = {
            "document_type": "bank_statement",
            "confidence_score": 0.65,
            "requires_review": True
        }
        processing_time3 = 0.6  # seconds
        
        # Update metrics again
        classification_service._update_performance_metrics(result3, processing_time3)
        
        # Verify metrics were updated correctly
        assert classification_service.classification_metrics["total_documents"] == 3
        assert classification_service.classification_metrics["successful_classifications"] == 2
        assert classification_service.classification_metrics["low_confidence_classifications"] == 1
        # Average confidence should be (0.85 + 0.75 + 0.65) / 3 = 0.75
        assert classification_service.classification_metrics["average_confidence"] == 0.75
        # Average processing time should be (0.5 + 0.7 + 0.6) / 3 = 0.6
        assert classification_service.classification_metrics["average_processing_time"] == 0.6
    
    def test_get_performance_metrics(self, classification_service):
        """
        Test retrieval of performance metrics.
        """
        # Set some metrics
        classification_service.classification_metrics = {
            "total_documents": 100,
            "successful_classifications": 85,
            "low_confidence_classifications": 10,
            "failed_classifications": 5,
            "average_confidence": 0.82,
            "average_processing_time": 0.45
        }
        
        # Get metrics
        metrics = classification_service.get_performance_metrics()
        
        # Verify metrics
        assert metrics == classification_service.classification_metrics
        assert metrics["total_documents"] == 100
        assert metrics["successful_classifications"] == 85
        assert metrics["low_confidence_classifications"] == 10
        assert metrics["failed_classifications"] == 5
        assert metrics["average_confidence"] == 0.82
        assert metrics["average_processing_time"] == 0.45
    
    def test_get_supported_document_types(self, classification_service):
        """
        Test retrieval of supported document types.
        """
        # Set document types
        classification_service.document_types = [
            "application", "tax_return", "bank_statement", 
            "pay_stub", "id_document", "other"
        ]
        
        # Get document types
        document_types = classification_service.get_supported_document_types()
        
        # Verify document types
        assert document_types == classification_service.document_types
        assert len(document_types) == 6
        assert "application" in document_types
        assert "tax_return" in document_types
        assert "bank_statement" in document_types
        assert "pay_stub" in document_types
        assert "id_document" in document_types
        assert "other" in document_types