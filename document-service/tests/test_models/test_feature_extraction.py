#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the feature extraction utilities used in document classification.

This module contains tests for the feature extraction components in the Document Service,
including text extraction, preprocessing, TF-IDF vectorization, metadata feature engineering,
and dimensionality reduction techniques.
"""

import os
import io
import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Tuple
from scipy.sparse import csr_matrix

# Import the module to test
from src.models.feature_extraction import (
    TextExtractor,
    TextPreprocessor,
    TfidfFeatureExtractor,
    MetadataFeatureExtractor,
    DimensionalityReducer,
    FeatureExtractor
)

# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def mock_file_utils():
    """Fixture that provides a mocked file_utils module."""
    with patch("src.utils.file_utils") as mock_utils:
        # Mock text extraction functions
        mock_utils.extract_text_from_pdf = MagicMock(return_value="This is a sample PDF document for testing.")
        mock_utils.extract_text_from_image = MagicMock(return_value="This is a sample image document for testing.")
        mock_utils.extract_text_from_buffer = MagicMock(return_value="This is a sample buffer document for testing.")
        
        yield mock_utils


@pytest.fixture
def sample_texts():
    """Fixture that provides sample texts for testing."""
    return [
        "This is a sample application form for merchant cash advance.",
        "Bank statement showing transactions for the last three months.",
        "Tax return document for fiscal year 2023 with business income details.",
        "Driver's license as proof of identity for the business owner.",
        "Business license document showing registration with local authorities."
    ]


@pytest.fixture
def sample_metadata():
    """Fixture that provides sample document metadata for testing."""
    return [
        {
            "size": 1024,
            "page_count": 3,
            "creation_date": "2023-01-15T10:30:00",
            "modification_date": "2023-01-15T14:45:00",
            "author": "John Doe",
            "title": "Application Form",
            "keywords": "application, merchant, funding"
        },
        {
            "size": 2048,
            "page_count": 5,
            "creation_date": "2023-02-10T09:15:00",
            "modification_date": "2023-02-10T09:15:00",
            "author": "Jane Smith",
            "title": "Bank Statement",
            "keywords": "bank, statement, transactions"
        },
        {
            "size": 3072,
            "page_count": 10,
            "creation_date": "2023-03-20T11:00:00",
            "modification_date": "2023-03-21T16:30:00",
            "author": "Tax Department",
            "title": "Tax Return",
            "keywords": "tax, return, business"
        },
        {
            "size": 512,
            "page_count": 1,
            "creation_date": "2023-04-05T08:45:00",
            "modification_date": "2023-04-05T08:45:00",
            "author": "DMV",
            "title": "Driver's License",
            "keywords": "license, identity, driver"
        },
        {
            "size": 768,
            "page_count": 2,
            "creation_date": "2023-05-12T13:20:00",
            "modification_date": "2023-05-12T13:20:00",
            "author": "City Hall",
            "title": "Business License",
            "keywords": "license, business, registration"
        }
    ]


@pytest.fixture
def feature_extraction_config():
    """Fixture that provides a sample feature extraction configuration."""
    return {
        "text_extraction": {
            "pdf_extraction_method": "pdfminer",
            "ocr_engine": "tesseract",
            "ocr_language": "eng",
            "ocr_timeout": 30
        },
        "text_preprocessing": {
            "lowercase": True,
            "remove_punctuation": True,
            "remove_numbers": False,
            "remove_stopwords": True,
            "stemming": True,
            "lemmatization": False,
            "min_word_length": 2
        },
        "tfidf_vectorization": {
            "ngram_range": (1, 2),
            "max_features": 1000,
            "min_df": 2,
            "max_df": 0.95,
            "use_idf": True,
            "sublinear_tf": True,
            "norm": "l2"
        },
        "metadata_features": {
            "extract_size": True,
            "extract_page_count": True,
            "extract_creation_date": True,
            "extract_modification_date": True,
            "extract_author": True,
            "extract_title": True,
            "extract_keywords": True
        },
        "dimensionality_reduction": {
            "enabled": True,
            "method": "pca",
            "n_components": 50,
            "random_state": 42
        }
    }


@pytest.fixture
def mock_nltk_resources():
    """Fixture that mocks NLTK resources for text preprocessing."""
    with patch("nltk.corpus.stopwords") as mock_stopwords, \
         patch("nltk.stem.porter.PorterStemmer") as mock_stemmer, \
         patch("nltk.stem.WordNetLemmatizer") as mock_lemmatizer:
        
        # Mock stopwords
        mock_stopwords.words.return_value = [
            "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
            "which", "this", "that", "these", "those", "then", "just", "so", "than", "such",
            "when", "while", "where", "how", "why", "is", "are", "was", "were", "be", "been",
            "for", "of", "by", "with", "about", "against", "between", "into", "through", "during",
            "to", "from", "in", "out", "on", "off", "over", "under", "again", "further"
        ]
        
        # Mock stemmer
        stemmer_instance = MagicMock()
        stemmer_instance.stem = lambda word: word[:4] if len(word) > 4 else word
        mock_stemmer.return_value = stemmer_instance
        
        # Mock lemmatizer
        lemmatizer_instance = MagicMock()
        lemmatizer_instance.lemmatize = lambda word: word
        mock_lemmatizer.return_value = lemmatizer_instance
        
        yield


@pytest.fixture
def mock_sklearn_components():
    """Fixture that mocks scikit-learn components for feature extraction."""
    with patch("sklearn.feature_extraction.text.TfidfVectorizer") as mock_tfidf, \
         patch("sklearn.feature_extraction.text.CountVectorizer") as mock_count, \
         patch("sklearn.decomposition.PCA") as mock_pca, \
         patch("sklearn.decomposition.TruncatedSVD") as mock_svd, \
         patch("sklearn.manifold.TSNE") as mock_tsne, \
         patch("sklearn.preprocessing.StandardScaler") as mock_scaler:
        
        # Mock TF-IDF vectorizer
        tfidf_instance = MagicMock()
        tfidf_instance.fit_transform.return_value = csr_matrix(np.array([[0.5, 0.8, 0.0], [0.0, 0.6, 0.9]]))
        tfidf_instance.transform.return_value = csr_matrix(np.array([[0.5, 0.8, 0.0]]))
        tfidf_instance.get_feature_names_out.return_value = ["application", "merchant", "cash"]
        mock_tfidf.return_value = tfidf_instance
        
        # Mock Count vectorizer
        count_instance = MagicMock()
        count_instance.fit_transform.return_value = csr_matrix(np.array([[2, 1, 0], [0, 1, 3]]))
        count_instance.transform.return_value = csr_matrix(np.array([[2, 1, 0]]))
        count_instance.get_feature_names_out.return_value = ["application", "merchant", "cash"]
        mock_count.return_value = count_instance
        
        # Mock PCA
        pca_instance = MagicMock()
        pca_instance.fit_transform.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        pca_instance.transform.return_value = np.array([[0.1, 0.2]])
        pca_instance.explained_variance_ratio_ = [0.7, 0.3]
        mock_pca.return_value = pca_instance
        
        # Mock TruncatedSVD
        svd_instance = MagicMock()
        svd_instance.fit_transform.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        svd_instance.transform.return_value = np.array([[0.1, 0.2]])
        svd_instance.explained_variance_ratio_ = [0.6, 0.4]
        mock_svd.return_value = svd_instance
        
        # Mock t-SNE
        tsne_instance = MagicMock()
        tsne_instance.fit_transform.return_value = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_tsne.return_value = tsne_instance
        
        # Mock StandardScaler
        scaler_instance = MagicMock()
        scaler_instance.fit_transform.return_value = np.array([[0.0, 0.0], [1.0, 1.0]])
        scaler_instance.transform.return_value = np.array([[0.0, 0.0]])
        mock_scaler.return_value = scaler_instance
        
        yield


# ============================================================================
# TextExtractor Tests
# ============================================================================

class TestTextExtractor:
    """Tests for the TextExtractor class."""
    
    def test_init(self, feature_extraction_config):
        """Test initialization of TextExtractor."""
        # Test with config
        extractor = TextExtractor(feature_extraction_config["text_extraction"])
        assert extractor.config == feature_extraction_config["text_extraction"]
        
        # Test without config (should use default from feature_extraction_config)
        with patch("src.config.model_config.feature_extraction_config", 
                  {"text_extraction": feature_extraction_config["text_extraction"]}):
            extractor = TextExtractor()
            assert extractor.config == feature_extraction_config["text_extraction"]
    
    def test_extract_from_pdf(self, mock_file_utils):
        """Test extraction of text from PDF documents."""
        extractor = TextExtractor()
        text = extractor.extract_from_pdf("test.pdf")
        
        # Verify that the file_utils function was called
        mock_file_utils.extract_text_from_pdf.assert_called_once_with("test.pdf")
        
        # Verify the extracted text
        assert text == "This is a sample PDF document for testing."
        
        # Test error handling
        mock_file_utils.extract_text_from_pdf.side_effect = Exception("PDF extraction error")
        text = extractor.extract_from_pdf("test.pdf")
        assert text == ""
    
    def test_extract_from_image(self, mock_file_utils):
        """Test extraction of text from image documents using OCR."""
        extractor = TextExtractor()
        text = extractor.extract_from_image("test.jpg")
        
        # Verify that the file_utils function was called
        mock_file_utils.extract_text_from_image.assert_called_once_with("test.jpg")
        
        # Verify the extracted text
        assert text == "This is a sample image document for testing."
        
        # Test error handling
        mock_file_utils.extract_text_from_image.side_effect = Exception("OCR error")
        text = extractor.extract_from_image("test.jpg")
        assert text == ""
    
    def test_extract_from_text(self):
        """Test extraction of text from plain text files."""
        extractor = TextExtractor()
        
        # Create a temporary text file for testing
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.write("This is a sample text file for testing.")
            temp_file_path = temp_file.name
        
        try:
            # Test text extraction
            text = extractor.extract_from_text(temp_file_path)
            assert text == "This is a sample text file for testing."
            
            # Test error handling with non-existent file
            text = extractor.extract_from_text("nonexistent.txt")
            assert text == ""
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def test_extract(self, mock_file_utils):
        """Test extraction of text based on file extension."""
        extractor = TextExtractor()
        
        # Test PDF extraction
        text = extractor.extract("test.pdf")
        mock_file_utils.extract_text_from_pdf.assert_called_once_with("test.pdf")
        assert text == "This is a sample PDF document for testing."
        
        # Test image extraction
        mock_file_utils.extract_text_from_pdf.reset_mock()
        text = extractor.extract("test.jpg")
        mock_file_utils.extract_text_from_image.assert_called_once_with("test.jpg")
        assert text == "This is a sample image document for testing."
        
        # Test text file extraction (using a mock instead of a real file)
        with patch.object(TextExtractor, "extract_from_text", return_value="This is a sample text file for testing."):
            text = extractor.extract("test.txt")
            assert text == "This is a sample text file for testing."
        
        # Test unsupported file format
        text = extractor.extract("test.xyz")
        assert text == ""
    
    def test_extract_from_buffer(self, mock_file_utils):
        """Test extraction of text from a binary buffer based on MIME type."""
        extractor = TextExtractor()
        buffer = b"Sample buffer content"
        mime_type = "application/pdf"
        
        text = extractor.extract_from_buffer(buffer, mime_type)
        
        # Verify that the file_utils function was called
        mock_file_utils.extract_text_from_buffer.assert_called_once_with(buffer, mime_type)
        
        # Verify the extracted text
        assert text == "This is a sample buffer document for testing."
        
        # Test error handling
        mock_file_utils.extract_text_from_buffer.side_effect = Exception("Buffer extraction error")
        text = extractor.extract_from_buffer(buffer, mime_type)
        assert text == ""


# ============================================================================
# TextPreprocessor Tests
# ============================================================================

class TestTextPreprocessor:
    """Tests for the TextPreprocessor class."""
    
    def test_init(self, feature_extraction_config, mock_nltk_resources):
        """Test initialization of TextPreprocessor."""
        # Test with config
        preprocessor = TextPreprocessor(feature_extraction_config["text_preprocessing"])
        assert preprocessor.config == feature_extraction_config["text_preprocessing"]
        assert preprocessor.lowercase == feature_extraction_config["text_preprocessing"]["lowercase"]
        assert preprocessor.remove_punctuation == feature_extraction_config["text_preprocessing"]["remove_punctuation"]
        assert preprocessor.remove_numbers == feature_extraction_config["text_preprocessing"]["remove_numbers"]
        assert preprocessor.remove_stopwords == feature_extraction_config["text_preprocessing"]["remove_stopwords"]
        assert preprocessor.stemming == feature_extraction_config["text_preprocessing"]["stemming"]
        assert preprocessor.lemmatization == feature_extraction_config["text_preprocessing"]["lemmatization"]
        assert preprocessor.min_word_length == feature_extraction_config["text_preprocessing"]["min_word_length"]
        
        # Test without config (should use default from feature_extraction_config)
        with patch("src.config.model_config.feature_extraction_config", 
                  {"text_preprocessing": feature_extraction_config["text_preprocessing"]}):
            preprocessor = TextPreprocessor()
            assert preprocessor.config == feature_extraction_config["text_preprocessing"]
    
    def test_fit(self, mock_nltk_resources):
        """Test fit method of TextPreprocessor."""
        preprocessor = TextPreprocessor()
        result = preprocessor.fit(["test text"])
        
        # fit should return self
        assert result == preprocessor
    
    def test_transform(self, sample_texts, mock_nltk_resources):
        """Test transform method of TextPreprocessor."""
        preprocessor = TextPreprocessor()
        processed_texts = preprocessor.transform(sample_texts)
        
        # Check that we get the expected number of processed texts
        assert len(processed_texts) == len(sample_texts)
        
        # Check that all texts have been processed
        for text in processed_texts:
            assert isinstance(text, str)
    
    def test_preprocess_text_lowercase(self, mock_nltk_resources):
        """Test text preprocessing with lowercase option."""
        # Test with lowercase=True
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("This IS a TEST Text")
        assert result == "this is a test text"
        
        # Test with lowercase=False
        preprocessor = TextPreprocessor({"lowercase": False, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("This IS a TEST Text")
        assert result == "This IS a TEST Text"
    
    def test_preprocess_text_remove_punctuation(self, mock_nltk_resources):
        """Test text preprocessing with remove_punctuation option."""
        # Test with remove_punctuation=True
        preprocessor = TextPreprocessor({"lowercase": False, "remove_punctuation": True, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("This, is a test! With punctuation.")
        assert "," not in result
        assert "!" not in result
        assert "." not in result
        
        # Test with remove_punctuation=False
        preprocessor = TextPreprocessor({"lowercase": False, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("This, is a test! With punctuation.")
        assert "," in result
        assert "!" in result
        assert "." in result
    
    def test_preprocess_text_remove_numbers(self, mock_nltk_resources):
        """Test text preprocessing with remove_numbers option."""
        # Test with remove_numbers=True
        preprocessor = TextPreprocessor({"lowercase": False, "remove_punctuation": False, 
                                        "remove_numbers": True, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("This has 123 numbers 456")
        assert "123" not in result
        assert "456" not in result
        
        # Test with remove_numbers=False
        preprocessor = TextPreprocessor({"lowercase": False, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("This has 123 numbers 456")
        assert "123" in result
        assert "456" in result
    
    def test_preprocess_text_remove_stopwords(self, mock_nltk_resources):
        """Test text preprocessing with remove_stopwords option."""
        # Test with remove_stopwords=True
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": True,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("this is a test with stopwords")
        assert "this" not in result.split()
        assert "is" not in result.split()
        assert "a" not in result.split()
        assert "with" not in result.split()
        assert "test" in result.split()
        assert "stopwords" in result.split()
        
        # Test with remove_stopwords=False
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("this is a test with stopwords")
        assert "this" in result.split()
        assert "is" in result.split()
        assert "a" in result.split()
        assert "with" in result.split()
        assert "test" in result.split()
        assert "stopwords" in result.split()
    
    def test_preprocess_text_stemming(self, mock_nltk_resources):
        """Test text preprocessing with stemming option."""
        # Test with stemming=True
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": True, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("testing stemming words")
        assert "test" in result.split()  # 'testing' should be stemmed to 'test'
        assert "stem" in result.split()  # 'stemming' should be stemmed to 'stem'
        assert "word" in result.split()  # 'words' should be stemmed to 'word'
        
        # Test with stemming=False
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("testing stemming words")
        assert "testing" in result.split()
        assert "stemming" in result.split()
        assert "words" in result.split()
    
    def test_preprocess_text_min_word_length(self, mock_nltk_resources):
        """Test text preprocessing with min_word_length option."""
        # Test with min_word_length=3
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 3})
        
        result = preprocessor._preprocess_text("a an the test word")
        assert "a" not in result.split()
        assert "an" not in result.split()
        assert "the" in result.split()  # 'the' has length 3
        assert "test" in result.split()
        assert "word" in result.split()
        
        # Test with min_word_length=1
        preprocessor = TextPreprocessor({"lowercase": True, "remove_punctuation": False, 
                                        "remove_numbers": False, "remove_stopwords": False,
                                        "stemming": False, "lemmatization": False,
                                        "min_word_length": 1})
        
        result = preprocessor._preprocess_text("a an the test word")
        assert "a" in result.split()
        assert "an" in result.split()
        assert "the" in result.split()
        assert "test" in result.split()
        assert "word" in result.split()
    
    def test_preprocess_text_empty_input(self, mock_nltk_resources):
        """Test text preprocessing with empty input."""
        preprocessor = TextPreprocessor()
        result = preprocessor._preprocess_text("")
        assert result == ""


# ============================================================================
# TfidfFeatureExtractor Tests
# ============================================================================

class TestTfidfFeatureExtractor:
    """Tests for the TfidfFeatureExtractor class."""
    
    def test_init(self, feature_extraction_config, mock_sklearn_components):
        """Test initialization of TfidfFeatureExtractor."""
        # Test with config
        extractor = TfidfFeatureExtractor(feature_extraction_config["tfidf_vectorization"])
        assert extractor.config == feature_extraction_config["tfidf_vectorization"]
        assert extractor.ngram_range == feature_extraction_config["tfidf_vectorization"]["ngram_range"]
        assert extractor.max_features == feature_extraction_config["tfidf_vectorization"]["max_features"]
        assert extractor.min_df == feature_extraction_config["tfidf_vectorization"]["min_df"]
        assert extractor.max_df == feature_extraction_config["tfidf_vectorization"]["max_df"]
        assert extractor.use_idf == feature_extraction_config["tfidf_vectorization"]["use_idf"]
        assert extractor.sublinear_tf == feature_extraction_config["tfidf_vectorization"]["sublinear_tf"]
        assert extractor.norm == feature_extraction_config["tfidf_vectorization"]["norm"]
        
        # Test without config (should use default from feature_extraction_config)
        with patch("src.config.model_config.feature_extraction_config", 
                  {"tfidf_vectorization": feature_extraction_config["tfidf_vectorization"]}):
            extractor = TfidfFeatureExtractor()
            assert extractor.config == feature_extraction_config["tfidf_vectorization"]
    
    def test_fit(self, sample_texts, mock_sklearn_components):
        """Test fit method of TfidfFeatureExtractor."""
        extractor = TfidfFeatureExtractor()
        result = extractor.fit(sample_texts)
        
        # fit should return self
        assert result == extractor
        
        # Verify that the vectorizer's fit method was called
        extractor.vectorizer.fit.assert_called_once_with(sample_texts)
    
    def test_transform(self, sample_texts, mock_sklearn_components):
        """Test transform method of TfidfFeatureExtractor."""
        extractor = TfidfFeatureExtractor()
        tfidf_matrix = extractor.transform(sample_texts)
        
        # Verify that the vectorizer's transform method was called
        extractor.vectorizer.transform.assert_called_once_with(sample_texts)
        
        # Check that we get a sparse matrix
        assert isinstance(tfidf_matrix, csr_matrix)
    
    def test_get_feature_names(self, mock_sklearn_components):
        """Test get_feature_names method of TfidfFeatureExtractor."""
        extractor = TfidfFeatureExtractor()
        feature_names = extractor.get_feature_names()
        
        # Verify that the vectorizer's get_feature_names_out method was called
        extractor.vectorizer.get_feature_names_out.assert_called_once()
        
        # Check that we get a list of feature names
        assert isinstance(feature_names, list)
        assert len(feature_names) > 0
        assert all(isinstance(name, str) for name in feature_names)
    
    def test_get_top_features(self, mock_sklearn_components):
        """Test get_top_features method of TfidfFeatureExtractor."""
        extractor = TfidfFeatureExtractor()
        
        # Create a mock TF-IDF matrix for a single document
        tfidf_matrix = csr_matrix(np.array([[0.5, 0.8, 0.3]]))
        
        # Get top features
        top_features = extractor.get_top_features(tfidf_matrix, n=2)
        
        # Verify that the vectorizer's get_feature_names_out method was called
        extractor.vectorizer.get_feature_names_out.assert_called_once()
        
        # Check that we get the expected number of top features
        assert len(top_features) == 2
        
        # Check that features are sorted by score in descending order
        assert top_features[0][1] >= top_features[1][1]
        
        # Test with invalid input (matrix with multiple documents)
        tfidf_matrix = csr_matrix(np.array([[0.5, 0.8, 0.3], [0.1, 0.2, 0.9]]))
        with pytest.raises(ValueError):
            extractor.get_top_features(tfidf_matrix)


# ============================================================================
# MetadataFeatureExtractor Tests
# ============================================================================

class TestMetadataFeatureExtractor:
    """Tests for the MetadataFeatureExtractor class."""
    
    def test_init(self, feature_extraction_config, mock_sklearn_components):
        """Test initialization of MetadataFeatureExtractor."""
        # Test with config
        extractor = MetadataFeatureExtractor(feature_extraction_config["metadata_features"])
        assert extractor.config == feature_extraction_config["metadata_features"]
        assert extractor.extract_size == feature_extraction_config["metadata_features"]["extract_size"]
        assert extractor.extract_page_count == feature_extraction_config["metadata_features"]["extract_page_count"]
        assert extractor.extract_creation_date == feature_extraction_config["metadata_features"]["extract_creation_date"]
        assert extractor.extract_modification_date == feature_extraction_config["metadata_features"]["extract_modification_date"]
        assert extractor.extract_author == feature_extraction_config["metadata_features"]["extract_author"]
        assert extractor.extract_title == feature_extraction_config["metadata_features"]["extract_title"]
        assert extractor.extract_keywords == feature_extraction_config["metadata_features"]["extract_keywords"]
        
        # Test without config (should use default from feature_extraction_config)
        with patch("src.config.model_config.feature_extraction_config", 
                  {"metadata_features": feature_extraction_config["metadata_features"]}):
            extractor = MetadataFeatureExtractor()
            assert extractor.config == feature_extraction_config["metadata_features"]
    
    def test_fit(self, sample_metadata, mock_sklearn_components):
        """Test fit method of MetadataFeatureExtractor."""
        extractor = MetadataFeatureExtractor()
        result = extractor.fit(sample_metadata)
        
        # fit should return self
        assert result == extractor
        
        # Verify that the scaler's fit method was called for numerical features
        assert extractor.scaler.fit.called
    
    def test_transform(self, sample_metadata, mock_sklearn_components):
        """Test transform method of MetadataFeatureExtractor."""
        extractor = MetadataFeatureExtractor()
        extractor.fit(sample_metadata)
        features = extractor.transform(sample_metadata)
        
        # Check that we get a numpy array with the right shape
        assert isinstance(features, np.ndarray)
        assert features.shape[0] == len(sample_metadata)
        
        # Verify that the scaler's transform method was called for numerical features
        assert extractor.scaler.transform.called
    
    def test_extract_features(self, sample_metadata):
        """Test _extract_features method of MetadataFeatureExtractor."""
        extractor = MetadataFeatureExtractor()
        features = extractor._extract_features(sample_metadata)
        
        # Check that we get a numpy array with the right shape
        assert isinstance(features, np.ndarray)
        assert features.shape[0] == len(sample_metadata)
        
        # Check that feature names were generated
        assert len(extractor.feature_names) > 0
        
        # Test with empty metadata
        features = extractor._extract_features([])
        assert features.shape[0] == 0
    
    def test_get_numerical_indices(self):
        """Test _get_numerical_indices method of MetadataFeatureExtractor."""
        extractor = MetadataFeatureExtractor()
        extractor.feature_names = ["size", "page_count", "has_author", "creation_date", "has_title"]
        
        numerical_indices = extractor._get_numerical_indices()
        
        # Check that we get the correct indices for numerical features
        assert 0 in numerical_indices  # size
        assert 1 in numerical_indices  # page_count
        assert 3 in numerical_indices  # creation_date
        assert 2 not in numerical_indices  # has_author (not numerical)
        assert 4 not in numerical_indices  # has_title (not numerical)
    
    def test_get_feature_names(self):
        """Test get_feature_names method of MetadataFeatureExtractor."""
        extractor = MetadataFeatureExtractor()
        extractor.feature_names = ["size", "page_count", "has_author", "creation_date", "has_title"]
        
        feature_names = extractor.get_feature_names()
        
        # Check that we get the correct feature names
        assert feature_names == ["size", "page_count", "has_author", "creation_date", "has_title"]


# ============================================================================
# DimensionalityReducer Tests
# ============================================================================

class TestDimensionalityReducer:
    """Tests for the DimensionalityReducer class."""
    
    def test_init(self, feature_extraction_config, mock_sklearn_components):
        """Test initialization of DimensionalityReducer."""
        # Test with config for PCA
        config = feature_extraction_config["dimensionality_reduction"]
        config["method"] = "pca"
        reducer = DimensionalityReducer(config)
        assert reducer.config == config
        assert reducer.method == "pca"
        assert reducer.n_components == config["n_components"]
        assert reducer.random_state == config["random_state"]
        
        # Test with config for TruncatedSVD
        config["method"] = "truncated_svd"
        reducer = DimensionalityReducer(config)
        assert reducer.method == "truncated_svd"
        
        # Test with config for t-SNE
        config["method"] = "tsne"
        reducer = DimensionalityReducer(config)
        assert reducer.method == "tsne"
        
        # Test with invalid method
        config["method"] = "invalid_method"
        with pytest.raises(ValueError):
            DimensionalityReducer(config)
        
        # Test without config (should use default from feature_extraction_config)
        with patch("src.config.model_config.feature_extraction_config", 
                  {"dimensionality_reduction": feature_extraction_config["dimensionality_reduction"]}):
            reducer = DimensionalityReducer()
            assert reducer.config == feature_extraction_config["dimensionality_reduction"]
    
    def test_fit(self, mock_sklearn_components):
        """Test fit method of DimensionalityReducer."""
        reducer = DimensionalityReducer({"method": "pca", "n_components": 2, "random_state": 42})
        
        # Create a feature matrix with more features than n_components
        X = np.random.rand(10, 5)  # 10 samples, 5 features
        result = reducer.fit(X)
        
        # fit should return self
        assert result == reducer
        
        # Verify that the model's fit method was called
        reducer.model.fit.assert_called_once_with(X)
        
        # Test with feature matrix that has fewer features than n_components
        X = np.random.rand(10, 1)  # 10 samples, 1 feature
        result = reducer.fit(X)
        
        # fit should return self without calling model.fit
        assert result == reducer
    
    def test_transform(self, mock_sklearn_components):
        """Test transform method of DimensionalityReducer."""
        reducer = DimensionalityReducer({"method": "pca", "n_components": 2, "random_state": 42})
        
        # Create a feature matrix with more features than n_components
        X = np.random.rand(10, 5)  # 10 samples, 5 features
        X_reduced = reducer.transform(X)
        
        # Verify that the model's transform method was called
        reducer.model.transform.assert_called_once_with(X)
        
        # Check that we get a numpy array with the right shape
        assert isinstance(X_reduced, np.ndarray)
        
        # Test with feature matrix that has fewer features than n_components
        X = np.random.rand(10, 1)  # 10 samples, 1 feature
        X_reduced = reducer.transform(X)
        
        # Should return the original matrix without calling model.transform
        assert X_reduced is X
    
    def test_get_feature_names(self):
        """Test get_feature_names method of DimensionalityReducer."""
        reducer = DimensionalityReducer({"method": "pca", "n_components": 3, "random_state": 42})
        feature_names = reducer.get_feature_names()
        
        # Check that we get the correct feature names
        assert len(feature_names) == 3
        assert feature_names[0] == "pca_component_0"
        assert feature_names[1] == "pca_component_1"
        assert feature_names[2] == "pca_component_2"


# ============================================================================
# FeatureExtractor Tests
# ============================================================================

class TestFeatureExtractor:
    """Tests for the FeatureExtractor class."""
    
    def test_init(self, feature_extraction_config, mock_file_utils, mock_nltk_resources, mock_sklearn_components):
        """Test initialization of FeatureExtractor."""
        # Test with config
        extractor = FeatureExtractor(feature_extraction_config)
        assert extractor.config == feature_extraction_config
        assert isinstance(extractor.text_extractor, TextExtractor)
        assert isinstance(extractor.text_preprocessor, TextPreprocessor)
        assert isinstance(extractor.tfidf_extractor, TfidfFeatureExtractor)
        assert isinstance(extractor.metadata_extractor, MetadataFeatureExtractor)
        assert isinstance(extractor.dimensionality_reducer, DimensionalityReducer)
        assert isinstance(extractor.text_pipeline, Pipeline)
        
        # Test without config (should use default from feature_extraction_config)
        with patch("src.config.model_config.feature_extraction_config", feature_extraction_config):
            extractor = FeatureExtractor()
            assert extractor.config == feature_extraction_config
    
    def test_extract_features(self, mock_file_utils, mock_nltk_resources, mock_sklearn_components):
        """Test extract_features method of FeatureExtractor."""
        extractor = FeatureExtractor()
        
        # Create test file paths and metadata
        file_paths = ["test1.pdf", "test2.jpg", "test3.txt"]
        metadata = [
            {"size": 1024, "page_count": 3},
            {"size": 512, "page_count": 1},
            {"size": 256, "page_count": 2}
        ]
        
        # Mock the text_extractor.extract method
        with patch.object(TextExtractor, "extract", side_effect=["Text 1", "Text 2", "Text 3"]) as mock_extract:
            # Test with metadata
            features = extractor.extract_features(file_paths, metadata)
            
            # Verify that the text_extractor.extract method was called for each file
            assert mock_extract.call_count == 3
            
            # Verify that the text_pipeline.fit_transform method was called
            assert extractor.text_pipeline.fit_transform.called
            
            # Test without metadata
            features = extractor.extract_features(file_paths)
            
            # Verify that the text_extractor.extract method was called for each file again
            assert mock_extract.call_count == 6
    
    def test_extract_features_from_buffer(self, mock_file_utils, mock_nltk_resources, mock_sklearn_components):
        """Test extract_features_from_buffer method of FeatureExtractor."""
        extractor = FeatureExtractor()
        
        # Create test buffer and metadata
        buffer = b"Sample buffer content"
        mime_type = "application/pdf"
        metadata = {"size": 1024, "page_count": 3}
        
        # Mock the text_extractor.extract_from_buffer method
        with patch.object(TextExtractor, "extract_from_buffer", return_value="Extracted text") as mock_extract:
            # Test with metadata
            features = extractor.extract_features_from_buffer(buffer, mime_type, metadata)
            
            # Verify that the text_extractor.extract_from_buffer method was called
            mock_extract.assert_called_once_with(buffer, mime_type)
            
            # Verify that the text_pipeline.fit_transform method was called
            assert extractor.text_pipeline.fit_transform.called
            
            # Test without metadata
            features = extractor.extract_features_from_buffer(buffer, mime_type)
            
            # Verify that the text_extractor.extract_from_buffer method was called again
            assert mock_extract.call_count == 2
    
    def test_get_top_features(self, mock_file_utils, mock_nltk_resources, mock_sklearn_components):
        """Test get_top_features method of FeatureExtractor."""
        extractor = FeatureExtractor()
        
        # Create a mock feature vector for a single document
        feature_vector = csr_matrix(np.array([[0.5, 0.8, 0.3]]))
        
        # Test with dimensionality reduction disabled
        extractor.config["dimensionality_reduction"] = {"enabled": False}
        
        # Mock the tfidf_extractor.get_top_features method
        with patch.object(TfidfFeatureExtractor, "get_top_features", 
                         return_value=[("merchant", 0.8), ("application", 0.5)]) as mock_get_top:
            top_features = extractor.get_top_features(feature_vector, n=2)
            
            # Verify that the tfidf_extractor.get_top_features method was called
            mock_get_top.assert_called_once_with(feature_vector, 2)
            
            # Check that we get the expected top features
            assert len(top_features) == 2
            assert top_features[0][0] == "merchant"
            assert top_features[0][1] == 0.8
            assert top_features[1][0] == "application"
            assert top_features[1][1] == 0.5
        
        # Test with dimensionality reduction enabled
        extractor.config["dimensionality_reduction"] = {"enabled": True, "method": "pca", "n_components": 2}
        
        # Create a dense feature vector for testing
        feature_vector = np.array([[0.1, 0.2]])
        
        # Mock the dimensionality_reducer.get_feature_names method
        with patch.object(DimensionalityReducer, "get_feature_names", 
                         return_value=["pca_component_0", "pca_component_1"]) as mock_get_names:
            top_features = extractor.get_top_features(feature_vector, n=2)
            
            # Verify that the dimensionality_reducer.get_feature_names method was called
            mock_get_names.assert_called_once()
            
            # Check that we get the expected top features
            assert len(top_features) == 2
            assert top_features[0][0] == "pca_component_1"
            assert top_features[0][1] == 0.2
            assert top_features[1][0] == "pca_component_0"
            assert top_features[1][1] == 0.1
        
        # Test with invalid input (feature vector for multiple documents)
        feature_vector = np.array([[0.1, 0.2], [0.3, 0.4]])
        with pytest.raises(ValueError):
            extractor.get_top_features(feature_vector)