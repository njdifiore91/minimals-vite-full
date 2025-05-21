"""
Unit tests for document classification type definitions.

This module contains tests for the type definitions used in the document
classification pipeline, including ClassificationModel, FeatureVector,
ClassificationResult, ConfidenceScore, ModelParameters, and ClassificationMetrics.

These tests ensure type safety and proper validation for the core classification
functionality of the Document Service.
"""

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC

# Import the types module from the document service
try:
    from document_service.types.classification import (
        ClassificationMetrics,
        ClassificationModel,
        ClassificationResult,
        ClassifierFactory,
        ConfidenceScore,
        DocumentType,
        FeatureExtractor,
        FeatureVector,
        ModelConfig,
        ModelParameters,
    )
except ImportError:
    # Alternative import path if the module structure is different
    from document_service.src.types.classification import (
        ClassificationMetrics,
        ClassificationModel,
        ClassificationResult,
        ClassifierFactory,
        ConfidenceScore,
        DocumentType,
        FeatureExtractor,
        FeatureVector,
        ModelConfig,
        ModelParameters,
    )


class TestDocumentType(unittest.TestCase):
    """Test cases for DocumentType enum."""

    def test_document_type_values(self):
        """Test that DocumentType enum has the expected values."""
        self.assertEqual(DocumentType.APPLICATION.value, "application")
        self.assertEqual(DocumentType.TAX_RETURN.value, "tax_return")
        self.assertEqual(DocumentType.BANK_STATEMENT.value, "bank_statement")
        self.assertEqual(DocumentType.PAY_STUB.value, "pay_stub")
        self.assertEqual(DocumentType.ID_DOCUMENT.value, "id_document")
        self.assertEqual(DocumentType.OTHER.value, "other")

    def test_document_type_comparison(self):
        """Test that DocumentType enum values can be compared correctly."""
        self.assertEqual(DocumentType.APPLICATION, DocumentType.APPLICATION)
        self.assertNotEqual(DocumentType.APPLICATION, DocumentType.TAX_RETURN)
        self.assertNotEqual(DocumentType.APPLICATION, "application")


class TestFeatureVector(unittest.TestCase):
    """Test cases for FeatureVector type alias."""

    def test_feature_vector_creation(self):
        """Test that FeatureVector can be created from numpy array."""
        # Create a feature vector with 10 features
        features: FeatureVector = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0], dtype=np.float64)
        
        self.assertEqual(features.shape, (10,))
        self.assertEqual(features.dtype, np.float64)

    def test_feature_vector_operations(self):
        """Test that FeatureVector supports numpy operations."""
        features1: FeatureVector = np.array([0.1, 0.2, 0.3], dtype=np.float64)
        features2: FeatureVector = np.array([0.4, 0.5, 0.6], dtype=np.float64)
        
        # Test addition
        result = features1 + features2
        expected = np.array([0.5, 0.7, 0.9], dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)
        
        # Test multiplication
        result = features1 * 2.0
        expected = np.array([0.2, 0.4, 0.6], dtype=np.float64)
        np.testing.assert_array_almost_equal(result, expected)


class TestClassificationModel(unittest.TestCase):
    """Test cases for ClassificationModel protocol."""

    @pytest.mark.parametrize("model_class,params", [
        (SVC, {"probability": True, "C": 1.0, "kernel": "rbf"}),
        (RandomForestClassifier, {"n_estimators": 100, "max_depth": 10}),
    ])
    def test_model_compatibility(self, model_class, params):
        """Test that scikit-learn models are compatible with ClassificationModel protocol."""
        # Create the model with parameters
        model = model_class(**params)
        
        # Verify it has the required methods
        self.assertTrue(hasattr(model, 'fit'))
        self.assertTrue(hasattr(model, 'predict'))
        self.assertTrue(hasattr(model, 'predict_proba'))
        
        # Create sample data
        X = np.array([[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]], dtype=np.float64)
        y = np.array([0, 1, 0])
        
        # Test fit method
        model.fit(X, y)
        
        # Test predict method
        predictions = model.predict(X)
        self.assertEqual(predictions.shape, (3,))
        
        # Test predict_proba method
        probabilities = model.predict_proba(X)
        self.assertEqual(probabilities.shape, (3, 2))


class TestClassificationResult(unittest.TestCase):
    """Test cases for ClassificationResult dataclass."""

    def test_classification_result_creation(self):
        """Test that ClassificationResult can be created with valid values."""
        result = ClassificationResult(
            document_id="doc123",
            document_type=DocumentType.APPLICATION,
            confidence=0.95,
            feature_importance={"feature1": 0.7, "feature2": 0.2, "feature3": 0.1}
        )
        
        self.assertEqual(result.document_id, "doc123")
        self.assertEqual(result.document_type, DocumentType.APPLICATION)
        self.assertEqual(result.confidence, 0.95)
        self.assertFalse(result.requires_review)
        self.assertIsInstance(result.prediction_time, datetime)
        self.assertEqual(result.feature_importance, {"feature1": 0.7, "feature2": 0.2, "feature3": 0.1})

    @pytest.mark.parametrize("invalid_confidence", [
        -0.1,  # Negative value
        1.1,   # Greater than 1.0
    ])
    def test_confidence_validation(self, invalid_confidence):
        """Test that confidence score is validated to be between 0.0 and 1.0."""
        with self.assertRaises(ValueError):
            ClassificationResult(
                document_id="doc123",
                document_type=DocumentType.APPLICATION,
                confidence=invalid_confidence
            )

    @pytest.mark.parametrize("confidence,expected_review_flag", [
        (0.8, False),   # Above threshold
        (0.7, True),    # Below threshold
        (0.75, False),  # At threshold
    ])
    def test_requires_review_flag(self, confidence, expected_review_flag):
        """Test that requires_review flag is set based on confidence threshold."""
        result = ClassificationResult(
            document_id="doc123",
            document_type=DocumentType.APPLICATION,
            confidence=confidence
        )
        self.assertEqual(result.requires_review, expected_review_flag)


class TestFeatureExtractor(unittest.TestCase):
    """Test cases for FeatureExtractor dataclass."""

    def test_feature_extractor_creation(self):
        """Test that FeatureExtractor can be created with valid values."""
        # Mock extract function
        def extract_fn(content: bytes) -> FeatureVector:
            return np.array([0.1, 0.2, 0.3], dtype=np.float64)
        
        extractor = FeatureExtractor(
            name="test_extractor",
            extract_fn=extract_fn,
            feature_names=["feature1", "feature2", "feature3"]
        )
        
        self.assertEqual(extractor.name, "test_extractor")
        self.assertEqual(extractor.feature_names, ["feature1", "feature2", "feature3"])
        self.assertEqual(extractor.extract_fn, extract_fn)

    def test_extract_method(self):
        """Test that extract method calls the extract function with document content."""
        # Mock extract function
        def extract_fn(content: bytes) -> FeatureVector:
            # Return different features based on content
            if content == b"doc1":
                return np.array([0.1, 0.2, 0.3], dtype=np.float64)
            else:
                return np.array([0.4, 0.5, 0.6], dtype=np.float64)
        
        extractor = FeatureExtractor(
            name="test_extractor",
            extract_fn=extract_fn,
            feature_names=["feature1", "feature2", "feature3"]
        )
        
        # Test with different document contents
        features1 = extractor.extract(b"doc1")
        np.testing.assert_array_almost_equal(features1, np.array([0.1, 0.2, 0.3], dtype=np.float64))
        
        features2 = extractor.extract(b"doc2")
        np.testing.assert_array_almost_equal(features2, np.array([0.4, 0.5, 0.6], dtype=np.float64))


class TestClassificationMetrics(unittest.TestCase):
    """Test cases for ClassificationMetrics dataclass."""

    def test_metrics_creation(self):
        """Test that ClassificationMetrics can be created with valid values."""
        metrics = ClassificationMetrics(
            accuracy=0.95,
            precision={DocumentType.APPLICATION: 0.92, DocumentType.TAX_RETURN: 0.98},
            recall={DocumentType.APPLICATION: 0.90, DocumentType.TAX_RETURN: 0.97},
            f1_score={DocumentType.APPLICATION: 0.91, DocumentType.TAX_RETURN: 0.975},
            confusion_matrix=np.array([[45, 5], [3, 47]])
        )
        
        self.assertEqual(metrics.accuracy, 0.95)
        self.assertEqual(metrics.precision[DocumentType.APPLICATION], 0.92)
        self.assertEqual(metrics.recall[DocumentType.TAX_RETURN], 0.97)
        self.assertEqual(metrics.f1_score[DocumentType.APPLICATION], 0.91)
        np.testing.assert_array_equal(metrics.confusion_matrix, np.array([[45, 5], [3, 47]]))
        self.assertIsInstance(metrics.timestamp, datetime)

    @pytest.mark.parametrize("invalid_accuracy", [
        -0.1,  # Negative value
        1.1,   # Greater than 1.0
    ])
    def test_accuracy_validation(self, invalid_accuracy):
        """Test that accuracy is validated to be between 0.0 and 1.0."""
        with self.assertRaises(ValueError):
            ClassificationMetrics(
                accuracy=invalid_accuracy,
                precision={DocumentType.APPLICATION: 0.9},
                recall={DocumentType.APPLICATION: 0.9},
                f1_score={DocumentType.APPLICATION: 0.9}
            )

    def test_string_document_type_keys(self):
        """Test that metrics can use string keys for document types."""
        metrics = ClassificationMetrics(
            accuracy=0.95,
            precision={"application": 0.92, "tax_return": 0.98},
            recall={"application": 0.90, "tax_return": 0.97},
            f1_score={"application": 0.91, "tax_return": 0.975}
        )
        
        self.assertEqual(metrics.precision["application"], 0.92)
        self.assertEqual(metrics.recall["tax_return"], 0.97)
        self.assertEqual(metrics.f1_score["application"], 0.91)


class TestModelConfig(unittest.TestCase):
    """Test cases for ModelConfig dataclass."""

    def test_model_config_creation(self):
        """Test that ModelConfig can be created with valid values."""
        # Mock feature extractor
        extractor = MagicMock(spec=FeatureExtractor)
        
        config = ModelConfig(
            model_type="svm",
            parameters={"C": 1.0, "kernel": "rbf"},
            feature_extractors=[extractor],
            confidence_threshold=0.8,
            version="1.0.0",
            description="Test model configuration"
        )
        
        self.assertEqual(config.model_type, "svm")
        self.assertEqual(config.parameters, {"C": 1.0, "kernel": "rbf"})
        self.assertEqual(config.feature_extractors, [extractor])
        self.assertEqual(config.confidence_threshold, 0.8)
        self.assertEqual(config.version, "1.0.0")
        self.assertEqual(config.description, "Test model configuration")

    @pytest.mark.parametrize("invalid_threshold", [
        -0.1,  # Negative value
        1.1,   # Greater than 1.0
    ])
    def test_confidence_threshold_validation(self, invalid_threshold):
        """Test that confidence threshold is validated to be between 0.0 and 1.0."""
        extractor = MagicMock(spec=FeatureExtractor)
        
        with self.assertRaises(ValueError):
            ModelConfig(
                model_type="svm",
                parameters={"C": 1.0},
                feature_extractors=[extractor],
                confidence_threshold=invalid_threshold
            )


class TestClassifierFactory(unittest.TestCase):
    """Test cases for ClassifierFactory class."""

    @pytest.mark.parametrize("model_type,parameters,expected_class,expected_attrs", [
        (
            "svm", 
            {"C": 1.0, "kernel": "rbf"}, 
            SVC, 
            {"C": 1.0, "kernel": "rbf", "probability": True}
        ),
        (
            "random_forest", 
            {"n_estimators": 100, "max_depth": 10}, 
            RandomForestClassifier, 
            {"n_estimators": 100, "max_depth": 10}
        ),
        (
            "gradient_boosting", 
            {"n_estimators": 100, "learning_rate": 0.1}, 
            "GradientBoostingClassifier", 
            {"n_estimators": 100, "learning_rate": 0.1}
        ),
    ])
    def test_create_model(self, model_type, parameters, expected_class, expected_attrs):
        """Test that ClassifierFactory can create different model types."""
        from sklearn.ensemble import GradientBoostingClassifier
        
        extractor = MagicMock(spec=FeatureExtractor)
        
        config = ModelConfig(
            model_type=model_type,
            parameters=parameters,
            feature_extractors=[extractor]
        )
        
        model = ClassifierFactory.create_model(config)
        
        # Handle string class name for GradientBoostingClassifier
        if expected_class == "GradientBoostingClassifier":
            self.assertIsInstance(model, GradientBoostingClassifier)
        else:
            self.assertIsInstance(model, expected_class)
        
        # Verify model attributes
        for attr_name, attr_value in expected_attrs.items():
            self.assertEqual(getattr(model, attr_name), attr_value)

    def test_unsupported_model_type(self):
        """Test that ClassifierFactory raises ValueError for unsupported model types."""
        extractor = MagicMock(spec=FeatureExtractor)
        
        config = ModelConfig(
            model_type="unsupported_model",
            parameters={},
            feature_extractors=[extractor]
        )
        
        with self.assertRaises(ValueError) as context:
            ClassifierFactory.create_model(config)
        
        self.assertIn("Unsupported model type", str(context.exception))


if __name__ == "__main__":
    unittest.main()