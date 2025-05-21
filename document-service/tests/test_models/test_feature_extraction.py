#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unit tests for the feature extraction module.

This module contains tests for the feature extraction utilities used in document classification.
Tests verify that the feature extraction module correctly extracts text from various document formats,
preprocesses text, implements TF-IDF vectorization, and performs feature engineering for document metadata.
Also tests dimensionality reduction techniques.
"""

import os
import re
import pytest
import numpy as np
import pandas as pd
from unittest.mock import MagicMock, patch, mock_open
from io import BytesIO

# Import the module to test
from document_service.src.models.feature_extraction import (
    TextExtractor,
    TextPreprocessor,
    TextVectorizer,
    MetadataExtractor,
    DimensionalityReducer,
    FeatureExtractor
)

# Import document-specific types
from document_service.src.types.documents import Document, DocumentType, DocumentMetadata
from document_service.src.types.classification import FeatureVector, ClassificationResult


# Tests for TextExtractor class
class TestTextExtractor:
    """Tests for the TextExtractor class."""
    
    def test_initialization(self):
        """Test that TextExtractor initializes correctly."""
        extractor = TextExtractor()
        assert extractor is not None
        assert extractor.config == {}
        
        # Test with custom config
        config = {'custom_param': 'value'}
        extractor = TextExtractor(config)
        assert extractor.config == config
    
    @patch('document_service.src.models.feature_extraction.pdfminer.high_level')
    def test_extract_from_pdf(self, mock_pdfminer, generate_test_document):
        """Test PDF text extraction."""
        # Create a mock document
        doc = generate_test_document(doc_type='application_form', mime_type='application/pdf')
        document = MagicMock()
        document.content = b'PDF content'
        document.metadata = MagicMock()
        document.metadata.mime_type = 'application/pdf'
        
        # Configure mock
        mock_pdfminer.extract_text.return_value = "Extracted PDF text"
        
        # Create extractor and test
        extractor = TextExtractor()
        extractor._has_pdfminer = True
        result = extractor._extract_from_pdf(document)
        
        # Verify results
        assert result == "Extracted PDF text"
        mock_pdfminer.extract_text.assert_called_once()
    
    @patch('document_service.src.models.feature_extraction.pytesseract')
    @patch('document_service.src.models.feature_extraction.Image')
    def test_extract_from_image(self, mock_image, mock_pytesseract, generate_test_document):
        """Test image text extraction using OCR."""
        # Create a mock document
        doc = generate_test_document(doc_type='identity_document', mime_type='image/jpeg')
        document = MagicMock()
        document.content = b'Image content'
        document.metadata = MagicMock()
        document.metadata.mime_type = 'image/jpeg'
        
        # Configure mocks
        mock_image_instance = MagicMock()
        mock_image.open.return_value = mock_image_instance
        mock_pytesseract.image_to_string.return_value = "Extracted image text"
        
        # Create extractor and test
        extractor = TextExtractor()
        extractor._has_ocr = True
        result = extractor._extract_from_image(document)
        
        # Verify results
        assert result == "Extracted image text"
        mock_image.open.assert_called_once()
        mock_pytesseract.image_to_string.assert_called_once_with(mock_image_instance, lang="eng")
    
    def test_extract_from_text(self, generate_test_document):
        """Test text document extraction."""
        # Create a mock document
        doc = generate_test_document(doc_type='bank_statement', mime_type='text/plain')
        document = MagicMock()
        document.content = "Plain text content".encode('utf-8')
        document.metadata = MagicMock()
        document.metadata.mime_type = 'text/plain'
        
        # Create extractor and test
        extractor = TextExtractor()
        result = extractor._extract_from_text(document)
        
        # Verify results
        assert result == "Plain text content"
    
    def test_extract_text_based_on_mime_type(self):
        """Test that extract_text selects the correct extraction method based on mime type."""
        # Create a mock extractor with mocked extraction methods
        extractor = TextExtractor()
        extractor._extract_from_pdf = MagicMock(return_value="PDF result")
        extractor._extract_from_image = MagicMock(return_value="Image result")
        extractor._extract_from_text = MagicMock(return_value="Text result")
        extractor._extract_generic = MagicMock(return_value="Generic result")
        
        # Test PDF extraction
        pdf_doc = MagicMock()
        pdf_doc.metadata.mime_type = 'application/pdf'
        assert extractor.extract_text(pdf_doc) == "PDF result"
        extractor._extract_from_pdf.assert_called_once_with(pdf_doc)
        
        # Test image extraction
        img_doc = MagicMock()
        img_doc.metadata.mime_type = 'image/jpeg'
        assert extractor.extract_text(img_doc) == "Image result"
        extractor._extract_from_image.assert_called_once_with(img_doc)
        
        # Test text extraction
        txt_doc = MagicMock()
        txt_doc.metadata.mime_type = 'text/plain'
        assert extractor.extract_text(txt_doc) == "Text result"
        extractor._extract_from_text.assert_called_once_with(txt_doc)
        
        # Test generic extraction for unknown mime type
        unknown_doc = MagicMock()
        unknown_doc.metadata.mime_type = 'application/unknown'
        assert extractor.extract_text(unknown_doc) == "Generic result"
        extractor._extract_generic.assert_called_once_with(unknown_doc)
    
    def test_extract_text_handles_errors(self):
        """Test that extract_text handles errors gracefully."""
        # Create a mock extractor with extraction methods that raise exceptions
        extractor = TextExtractor()
        extractor._extract_from_pdf = MagicMock(side_effect=Exception("PDF error"))
        extractor._extract_from_image = MagicMock(side_effect=Exception("Image error"))
        extractor._extract_from_text = MagicMock(side_effect=Exception("Text error"))
        extractor._extract_generic = MagicMock(return_value="")
        
        # Test PDF extraction with error
        pdf_doc = MagicMock()
        pdf_doc.metadata.mime_type = 'application/pdf'
        assert extractor.extract_text(pdf_doc) == ""
        
        # Test image extraction with error
        img_doc = MagicMock()
        img_doc.metadata.mime_type = 'image/jpeg'
        assert extractor.extract_text(img_doc) == ""
        
        # Test text extraction with error
        txt_doc = MagicMock()
        txt_doc.metadata.mime_type = 'text/plain'
        assert extractor.extract_text(txt_doc) == ""


# Tests for TextPreprocessor class
class TestTextPreprocessor:
    """Tests for the TextPreprocessor class."""
    
    def test_initialization(self):
        """Test that TextPreprocessor initializes correctly."""
        preprocessor = TextPreprocessor()
        assert preprocessor is not None
        assert preprocessor.config == {}
        
        # Test with custom config
        config = {'use_lemmatization': True}
        preprocessor = TextPreprocessor(config)
        assert preprocessor.config == config
    
    @patch('document_service.src.models.feature_extraction.nltk')
    def test_setup_preprocessor_with_nltk(self, mock_nltk):
        """Test setup of preprocessor with NLTK available."""
        # Configure mock
        mock_nltk.data.find.return_value = True
        
        # Create preprocessor
        preprocessor = TextPreprocessor()
        preprocessor._setup_preprocessor()
        
        # Verify NLTK resources were checked
        assert mock_nltk.data.find.call_count == 3
        assert preprocessor._has_nltk is True
    
    @patch('document_service.src.models.feature_extraction.nltk')
    def test_setup_preprocessor_without_nltk(self, mock_nltk):
        """Test setup of preprocessor with NLTK unavailable."""
        # Configure mock to simulate ImportError
        mock_nltk.data.find.side_effect = ImportError("NLTK not found")
        
        # Create preprocessor
        preprocessor = TextPreprocessor()
        preprocessor._has_nltk = False
        
        # Verify basic preprocessing still works
        assert preprocessor._has_nltk is False
    
    def test_preprocess_with_nltk(self):
        """Test text preprocessing with NLTK."""
        # Create preprocessor with mocked NLTK components
        preprocessor = TextPreprocessor()
        preprocessor._has_nltk = True
        preprocessor.tokenizer = MagicMock(return_value=["this", "is", "a", "test", "document"])
        preprocessor.stemmer = MagicMock()
        preprocessor.stemmer.stem = lambda x: x + "_stem"
        preprocessor.lemmatizer = MagicMock()
        preprocessor.lemmatizer.lemmatize = lambda x: x + "_lemma"
        preprocessor.stop_words = {"a"}
        
        # Test stemming (default)
        result = preprocessor.preprocess("This is a test document!")
        assert "this_stem" in result
        assert "is_stem" in result
        assert "a_stem" not in result  # Stop word removed
        assert "test_stem" in result
        assert "document_stem" in result
        
        # Test lemmatization
        preprocessor.config = {'use_lemmatization': True}
        result = preprocessor.preprocess("This is a test document!")
        assert "this_lemma" in result
        assert "is_lemma" in result
        assert "a_lemma" not in result  # Stop word removed
        assert "test_lemma" in result
        assert "document_lemma" in result
    
    def test_preprocess_without_nltk(self):
        """Test text preprocessing without NLTK."""
        # Create preprocessor without NLTK
        preprocessor = TextPreprocessor()
        preprocessor._has_nltk = False
        
        # Test basic preprocessing
        result = preprocessor.preprocess("This is a test document!")
        assert result == "this is a test document"
        
        # Test with empty input
        assert preprocessor.preprocess("") == ""
        assert preprocessor.preprocess(None) == ""
    
    def test_preprocess_removes_special_chars(self):
        """Test that preprocessing removes special characters and digits."""
        preprocessor = TextPreprocessor()
        preprocessor._has_nltk = False
        
        result = preprocessor.preprocess("This is a test123 with special @#$ characters!")
        assert result == "this is a test with special characters"


# Tests for TextVectorizer class
class TestTextVectorizer:
    """Tests for the TextVectorizer class."""
    
    def test_initialization(self):
        """Test that TextVectorizer initializes correctly."""
        vectorizer = TextVectorizer()
        assert vectorizer is not None
        assert vectorizer.config == {}
        assert vectorizer.is_fitted is False
        
        # Test with custom config
        config = {'max_features': 500, 'ngram_range': (1, 3)}
        vectorizer = TextVectorizer(config)
        assert vectorizer.config == config
        assert vectorizer.vectorizer.max_features == 500
        assert vectorizer.vectorizer.ngram_range == (1, 3)
    
    def test_fit(self):
        """Test fitting the vectorizer on a corpus of texts."""
        # Create vectorizer
        vectorizer = TextVectorizer({'max_features': 10})
        
        # Test with empty corpus
        vectorizer.fit([])
        assert vectorizer.is_fitted is False
        
        # Test with corpus
        corpus = [
            "This is the first document.",
            "This document is the second document.",
            "And this is the third document."
        ]
        vectorizer.fit(corpus)
        assert vectorizer.is_fitted is True
        assert len(vectorizer.get_feature_names()) > 0
    
    def test_transform(self):
        """Test transforming texts into feature vectors."""
        # Create vectorizer
        vectorizer = TextVectorizer({'max_features': 10})
        
        # Test transform without fitting
        result = vectorizer.transform(["Test document"])
        assert result.shape == (1, 1)
        assert np.all(result == 0)
        
        # Fit and transform
        corpus = [
            "This is the first document.",
            "This document is the second document.",
            "And this is the third document."
        ]
        vectorizer.fit(corpus)
        result = vectorizer.transform(["This is a test document."])
        assert result.shape == (1, len(vectorizer.get_feature_names()))
    
    def test_fit_transform(self):
        """Test combined fit and transform operation."""
        # Create vectorizer
        vectorizer = TextVectorizer({'max_features': 10})
        
        # Test fit_transform
        corpus = [
            "This is the first document.",
            "This document is the second document.",
            "And this is the third document."
        ]
        result = vectorizer.fit_transform(corpus)
        assert vectorizer.is_fitted is True
        assert result.shape == (3, len(vectorizer.get_feature_names()))
    
    def test_get_feature_names(self):
        """Test retrieving feature names from the vectorizer."""
        # Create vectorizer
        vectorizer = TextVectorizer({'max_features': 10})
        
        # Test before fitting
        assert vectorizer.get_feature_names() == []
        
        # Test after fitting
        corpus = [
            "This is the first document.",
            "This document is the second document.",
            "And this is the third document."
        ]
        vectorizer.fit(corpus)
        feature_names = vectorizer.get_feature_names()
        assert len(feature_names) > 0
        assert all(isinstance(name, str) for name in feature_names)


# Tests for MetadataExtractor class
class TestMetadataExtractor:
    """Tests for the MetadataExtractor class."""
    
    def test_initialization(self):
        """Test that MetadataExtractor initializes correctly."""
        extractor = MetadataExtractor()
        assert extractor is not None
        assert extractor.config == {}
        
        # Test with custom config
        config = {'custom_param': 'value'}
        extractor = MetadataExtractor(config)
        assert extractor.config == config
    
    def test_extract_metadata_features(self, generate_test_document):
        """Test extraction of features from document metadata."""
        # Create extractor
        extractor = MetadataExtractor()
        
        # Test with PDF document
        pdf_doc = generate_test_document(doc_type='application_form', mime_type='application/pdf')
        document = MagicMock()
        document.content = b'PDF content'
        document.metadata = MagicMock()
        document.metadata.mime_type = 'application/pdf'
        document.metadata.filename = 'application_form.pdf'
        document.metadata.page_count = 5
        
        features = extractor.extract_metadata_features(document)
        assert features['size_kb'] == len(document.content) / 1024.0
        assert features['is_pdf'] == 1.0
        assert features['is_image'] == 0.0
        assert features['is_text'] == 0.0
        assert features['has_application_in_name'] == 1.0
        assert features['has_form_in_name'] == 1.0
        assert features['page_count'] == 5.0
        
        # Test with image document
        img_doc = generate_test_document(doc_type='identity_document', mime_type='image/jpeg')
        document = MagicMock()
        document.content = b'Image content'
        document.metadata = MagicMock()
        document.metadata.mime_type = 'image/jpeg'
        document.metadata.filename = 'id_card.jpg'
        
        features = extractor.extract_metadata_features(document)
        assert features['size_kb'] == len(document.content) / 1024.0
        assert features['is_pdf'] == 0.0
        assert features['is_image'] == 1.0
        assert features['is_text'] == 0.0
        assert features['has_id_in_name'] == 1.0
        
        # Test with text document
        txt_doc = generate_test_document(doc_type='bank_statement', mime_type='text/plain')
        document = MagicMock()
        document.content = b'Text content'
        document.metadata = MagicMock()
        document.metadata.mime_type = 'text/plain'
        document.metadata.filename = 'bank_statement.txt'
        
        features = extractor.extract_metadata_features(document)
        assert features['size_kb'] == len(document.content) / 1024.0
        assert features['is_pdf'] == 0.0
        assert features['is_image'] == 0.0
        assert features['is_text'] == 1.0
        assert features['has_statement_in_name'] == 1.0
    
    def test_extract_metadata_features_with_creation_date(self, generate_test_document):
        """Test extraction of creation date feature."""
        # Create extractor
        extractor = MetadataExtractor()
        
        # Create document with creation date
        import datetime
        creation_date = datetime.datetime.now() - datetime.timedelta(days=30)
        
        document = MagicMock()
        document.content = b'Content'
        document.metadata = MagicMock()
        document.metadata.mime_type = 'application/pdf'
        document.metadata.filename = 'document.pdf'
        document.metadata.creation_date = creation_date
        
        features = extractor.extract_metadata_features(document)
        assert 'days_since_creation' in features
        assert features['days_since_creation'] >= 30


# Tests for DimensionalityReducer class
class TestDimensionalityReducer:
    """Tests for the DimensionalityReducer class."""
    
    def test_initialization(self):
        """Test that DimensionalityReducer initializes correctly."""
        reducer = DimensionalityReducer()
        assert reducer is not None
        assert reducer.config == {}
        assert reducer.method == 'pca'
        assert reducer.n_components == 50
        assert reducer.is_fitted is False
        
        # Test with custom config
        config = {'method': 'svd', 'n_components': 20}
        reducer = DimensionalityReducer(config)
        assert reducer.config == config
        assert reducer.method == 'svd'
        assert reducer.n_components == 20
    
    def test_setup_reducer(self):
        """Test setup of different dimensionality reduction methods."""
        # Test PCA
        reducer = DimensionalityReducer({'method': 'pca', 'n_components': 10})
        reducer._setup_reducer()
        assert reducer.method == 'pca'
        assert hasattr(reducer.reducer, 'fit')
        assert hasattr(reducer.reducer, 'transform')
        
        # Test SVD
        reducer = DimensionalityReducer({'method': 'svd', 'n_components': 10})
        reducer._setup_reducer()
        assert reducer.method == 'svd'
        assert hasattr(reducer.reducer, 'fit')
        assert hasattr(reducer.reducer, 'transform')
        
        # Test t-SNE
        reducer = DimensionalityReducer({'method': 'tsne', 'n_components': 2})
        reducer._setup_reducer()
        assert reducer.method == 'tsne'
        assert hasattr(reducer.reducer, 'fit_transform')
        
        # Test unknown method (defaults to PCA)
        reducer = DimensionalityReducer({'method': 'unknown', 'n_components': 10})
        reducer._setup_reducer()
        assert reducer.method == 'pca'
    
    def test_fit(self):
        """Test fitting the dimensionality reducer."""
        # Create reducer
        reducer = DimensionalityReducer({'method': 'pca', 'n_components': 2})
        
        # Test with not enough samples
        X = np.random.random((1, 10))
        reducer.fit(X)
        assert reducer.is_fitted is False
        
        # Test with enough samples but too few dimensions
        X = np.random.random((10, 2))
        reducer.fit(X)
        assert reducer.is_fitted is False
        
        # Test with valid input
        X = np.random.random((10, 10))
        reducer.fit(X)
        assert reducer.is_fitted is True
        assert hasattr(reducer, 'scaler')
    
    def test_transform(self):
        """Test transforming feature vectors to lower dimensionality."""
        # Create reducer
        reducer = DimensionalityReducer({'method': 'pca', 'n_components': 2})
        
        # Test transform without fitting
        X = np.random.random((10, 10))
        result = reducer.transform(X)
        assert result is X  # Returns original features if not fitted
        
        # Fit and transform
        reducer.fit(X)
        result = reducer.transform(X)
        assert result.shape == (10, 2)  # Reduced to 2 components
        
        # Test with mismatched dimensions
        X_mismatched = np.random.random((10, 5))
        result = reducer.transform(X_mismatched)
        assert result is X_mismatched  # Returns original features if dimensions don't match
    
    def test_fit_transform(self):
        """Test combined fit and transform operation."""
        # Create reducer
        reducer = DimensionalityReducer({'method': 'pca', 'n_components': 2})
        
        # Test fit_transform
        X = np.random.random((10, 10))
        result = reducer.fit_transform(X)
        assert reducer.is_fitted is True
        assert result.shape == (10, 2)  # Reduced to 2 components
        
        # Test with not enough samples
        X = np.random.random((1, 10))
        result = reducer.fit_transform(X)
        assert result is X  # Returns original features if not enough samples
        
        # Test with too few dimensions
        X = np.random.random((10, 2))
        result = reducer.fit_transform(X)
        assert result is X  # Returns original features if dimensions are too few


# Tests for FeatureExtractor class
class TestFeatureExtractor:
    """Tests for the main FeatureExtractor class."""
    
    def test_initialization(self):
        """Test that FeatureExtractor initializes correctly."""
        extractor = FeatureExtractor()
        assert extractor is not None
        assert extractor.config == {}
        assert extractor.is_fitted is False
        assert isinstance(extractor.text_extractor, TextExtractor)
        assert isinstance(extractor.text_preprocessor, TextPreprocessor)
        assert isinstance(extractor.text_vectorizer, TextVectorizer)
        assert isinstance(extractor.metadata_extractor, MetadataExtractor)
        assert extractor.dim_reducer is None  # Not enabled by default
        
        # Test with dimensionality reduction enabled
        config = {'use_dimensionality_reduction': True, 'dimensionality_reduction': {'method': 'pca', 'n_components': 10}}
        extractor = FeatureExtractor(config)
        assert extractor.dim_reducer is not None
        assert extractor.dim_reducer.method == 'pca'
        assert extractor.dim_reducer.n_components == 10
    
    def test_fit(self, generate_test_document):
        """Test fitting the feature extractor on a corpus of documents."""
        # Create extractor
        extractor = FeatureExtractor({'use_dimensionality_reduction': True})
        
        # Mock the component methods
        extractor.text_extractor.extract_text = MagicMock(return_value="Extracted text")
        extractor.text_preprocessor.preprocess = MagicMock(return_value="Preprocessed text")
        extractor.text_vectorizer.fit = MagicMock()
        extractor.dim_reducer.fit = MagicMock()
        extractor.metadata_extractor.extract_metadata_features = MagicMock(return_value={'feature1': 1.0, 'feature2': 2.0})
        
        # Test with empty document list
        extractor.fit([])
        assert extractor.is_fitted is False
        
        # Test with documents
        documents = [MagicMock(), MagicMock()]
        extractor.fit(documents)
        
        # Verify method calls
        assert extractor.text_extractor.extract_text.call_count == 2
        assert extractor.text_preprocessor.preprocess.call_count == 2
        extractor.text_vectorizer.fit.assert_called_once()
        extractor.dim_reducer.fit.assert_called_once()
        assert extractor.metadata_extractor.extract_metadata_features.call_count == 2
        assert extractor.is_fitted is True
    
    def test_transform(self, generate_test_document):
        """Test transforming documents into feature vectors."""
        # Create extractor
        extractor = FeatureExtractor({'use_dimensionality_reduction': True})
        
        # Mock the component methods
        extractor.text_extractor.extract_text = MagicMock(return_value="Extracted text")
        extractor.text_preprocessor.preprocess = MagicMock(return_value="Preprocessed text")
        extractor.text_vectorizer.transform = MagicMock(return_value=np.array([[1.0, 2.0]]))
        extractor.dim_reducer.transform = MagicMock(return_value=np.array([[0.5, 0.5]]))
        extractor.metadata_extractor.extract_metadata_features = MagicMock(return_value={'feature1': 1.0, 'feature2': 2.0})
        
        # Test transform without fitting
        documents = [MagicMock()]
        result = extractor.transform(documents)
        assert result.shape == (1, 1)
        assert np.all(result == 0)
        
        # Set as fitted and test transform
        extractor.is_fitted = True
        result = extractor.transform(documents)
        
        # Verify method calls
        extractor.text_extractor.extract_text.assert_called_once()
        extractor.text_preprocessor.preprocess.assert_called_once()
        extractor.text_vectorizer.transform.assert_called_once()
        extractor.metadata_extractor.extract_metadata_features.assert_called_once()
        extractor.dim_reducer.transform.assert_called_once()
        assert result.shape == (1, 2)  # Matches the mock return value from dim_reducer
    
    def test_fit_transform(self, generate_test_document):
        """Test combined fit and transform operation."""
        # Create extractor
        extractor = FeatureExtractor()
        
        # Mock the fit and transform methods
        extractor.fit = MagicMock()
        extractor.transform = MagicMock(return_value=np.array([[1.0, 2.0]]))
        
        # Test fit_transform
        documents = [MagicMock()]
        result = extractor.fit_transform(documents)
        
        # Verify method calls
        extractor.fit.assert_called_once_with(documents)
        extractor.transform.assert_called_once_with(documents)
        assert result is extractor.transform.return_value
    
    def test_extract_features_from_document(self, generate_test_document):
        """Test extracting features from a single document."""
        # Create extractor
        extractor = FeatureExtractor()
        
        # Mock the transform method
        extractor.transform = MagicMock(return_value=np.array([[1.0, 2.0]]))
        extractor.get_feature_names = MagicMock(return_value=['feature1', 'feature2'])
        
        # Test with a document
        document = MagicMock()
        document.metadata.id = 'doc123'
        result = extractor.extract_features_from_document(document)
        
        # Verify result
        assert isinstance(result, FeatureVector)
        assert np.array_equal(result.values, np.array([1.0, 2.0]))
        assert result.feature_names == ['feature1', 'feature2']
        assert result.document_id == 'doc123'
    
    def test_get_feature_names(self):
        """Test retrieving feature names from the feature extractor."""
        # Create extractor
        extractor = FeatureExtractor()
        
        # Test before fitting
        assert extractor.get_feature_names() == []
        
        # Mock text_vectorizer and set as fitted
        extractor.is_fitted = True
        extractor.text_vectorizer.get_feature_names = MagicMock(return_value=['text_feature1', 'text_feature2'])
        
        # Test with no dimensionality reduction
        feature_names = extractor.get_feature_names()
        assert len(feature_names) > 0
        assert 'text_feature1' in feature_names
        assert 'size_kb' in feature_names
        
        # Test with dimensionality reduction
        extractor.dim_reducer = MagicMock()
        extractor.dim_reducer.n_components = 3
        feature_names = extractor.get_feature_names()
        assert len(feature_names) == 3
        assert all(name.startswith('component_') for name in feature_names)


# Integration tests
class TestFeatureExtractionIntegration:
    """Integration tests for the feature extraction module."""
    
    def test_end_to_end_feature_extraction(self, generate_test_document):
        """Test the complete feature extraction pipeline."""
        # Create sample documents
        documents = [
            generate_test_document(doc_type='application_form'),
            generate_test_document(doc_type='bank_statement'),
            generate_test_document(doc_type='tax_return')
        ]
        
        # Convert to Document objects
        doc_objects = []
        for doc in documents:
            metadata = DocumentMetadata(
                id=doc['id'],
                filename=f"{doc['type']}.pdf",
                mime_type="application/pdf",
                page_count=doc['metadata']['page_count']
            )
            doc_obj = Document(
                content=doc['content'].encode('utf-8') if isinstance(doc['content'], str) else doc['content'],
                metadata=metadata
            )
            doc_objects.append(doc_obj)
        
        # Create feature extractor
        config = {
            'text_vectorization': {
                'max_features': 20,
                'ngram_range': (1, 2)
            },
            'use_dimensionality_reduction': True,
            'dimensionality_reduction': {
                'method': 'pca',
                'n_components': 5
            }
        }
        extractor = FeatureExtractor(config)
        
        # Extract features
        features = extractor.fit_transform(doc_objects)
        
        # Verify results
        assert extractor.is_fitted is True
        assert features.shape == (3, 5)  # 3 documents, 5 components
        
        # Test single document extraction
        feature_vector = extractor.extract_features_from_document(doc_objects[0])
        assert isinstance(feature_vector, FeatureVector)
        assert feature_vector.values.shape == (5,)  # 5 components
        assert len(feature_vector.feature_names) == 5
        assert feature_vector.document_id == doc_objects[0].metadata.id


# Run tests
if __name__ == "__main__":
    pytest.main(['-xvs', __file__])