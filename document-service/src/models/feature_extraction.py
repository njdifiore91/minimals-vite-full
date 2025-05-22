#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Feature extraction utilities for document classification.

This module provides utilities for extracting features from documents for classification
in the Document Service. It implements text extraction, preprocessing, vectorization,
and feature engineering techniques to convert raw documents into feature vectors suitable
for machine learning models.

Classes:
    TextExtractor: Extracts text content from various document formats.
    TextPreprocessor: Preprocesses text for feature extraction.
    TfidfFeatureExtractor: Extracts TF-IDF features from preprocessed text.
    MetadataFeatureExtractor: Extracts features from document metadata.
    DimensionalityReducer: Reduces the dimensionality of feature vectors.
    FeatureExtractor: Main class that orchestrates the entire feature extraction process.
"""

import os
import re
import logging
from typing import Dict, List, Tuple, Union, Optional, Any

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.pipeline import Pipeline
from sklearn.feature_selection import SelectKBest, chi2

# Import custom modules
from ..utils import file_utils
from ..types.classification import FeatureVector
from ..config.model_config import feature_extraction_config

# Set up logging
logger = logging.getLogger(__name__)


class TextExtractor:
    """
    Extracts text content from various document formats.
    
    This class provides methods to extract text from different document formats
    including PDF, images (via OCR), and plain text files. It serves as the first
    step in the feature extraction pipeline.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the TextExtractor with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters for text extraction
        """
        self.config = config or feature_extraction_config.get('text_extraction', {})
        logger.info("Initialized TextExtractor with config: %s", self.config)
    
    def extract_from_pdf(self, file_path: str) -> str:
        """
        Extract text from a PDF document.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Extracted text content as a string
        """
        try:
            # Use file_utils to handle PDF extraction
            text = file_utils.extract_text_from_pdf(file_path)
            logger.debug("Successfully extracted text from PDF: %s", file_path)
            return text
        except Exception as e:
            logger.error("Failed to extract text from PDF %s: %s", file_path, str(e))
            return ""
    
    def extract_from_image(self, file_path: str) -> str:
        """
        Extract text from an image using OCR.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Extracted text content as a string
        """
        try:
            # Use file_utils to handle image OCR
            text = file_utils.extract_text_from_image(file_path)
            logger.debug("Successfully extracted text from image: %s", file_path)
            return text
        except Exception as e:
            logger.error("Failed to extract text from image %s: %s", file_path, str(e))
            return ""
    
    def extract_from_text(self, file_path: str) -> str:
        """
        Extract text from a plain text file.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Extracted text content as a string
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                text = f.read()
            logger.debug("Successfully extracted text from file: %s", file_path)
            return text
        except Exception as e:
            logger.error("Failed to extract text from file %s: %s", file_path, str(e))
            return ""
    
    def extract(self, file_path: str) -> str:
        """
        Extract text from a document based on its file extension.
        
        Args:
            file_path: Path to the document file
            
        Returns:
            Extracted text content as a string
        """
        _, ext = os.path.splitext(file_path.lower())
        
        if ext in ('.pdf'):
            return self.extract_from_pdf(file_path)
        elif ext in ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'):
            return self.extract_from_image(file_path)
        elif ext in ('.txt', '.csv', '.md', '.html', '.xml', '.json'):
            return self.extract_from_text(file_path)
        else:
            logger.warning("Unsupported file format: %s", ext)
            return ""
    
    def extract_from_buffer(self, buffer: bytes, mime_type: str) -> str:
        """
        Extract text from a binary buffer based on MIME type.
        
        Args:
            buffer: Binary content of the document
            mime_type: MIME type of the document
            
        Returns:
            Extracted text content as a string
        """
        try:
            # Use file_utils to handle buffer extraction based on MIME type
            text = file_utils.extract_text_from_buffer(buffer, mime_type)
            logger.debug("Successfully extracted text from buffer with MIME type: %s", mime_type)
            return text
        except Exception as e:
            logger.error("Failed to extract text from buffer with MIME type %s: %s", mime_type, str(e))
            return ""


class TextPreprocessor(BaseEstimator, TransformerMixin):
    """
    Preprocesses text for feature extraction.
    
    This class implements a text preprocessing pipeline including tokenization,
    stemming, lemmatization, and stop word removal. It inherits from scikit-learn's
    BaseEstimator and TransformerMixin to be compatible with scikit-learn pipelines.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the TextPreprocessor with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters for text preprocessing
        """
        self.config = config or feature_extraction_config.get('text_preprocessing', {})
        self.lowercase = self.config.get('lowercase', True)
        self.remove_punctuation = self.config.get('remove_punctuation', True)
        self.remove_numbers = self.config.get('remove_numbers', False)
        self.remove_stopwords = self.config.get('remove_stopwords', True)
        self.stemming = self.config.get('stemming', True)
        self.lemmatization = self.config.get('lemmatization', False)
        self.min_word_length = self.config.get('min_word_length', 2)
        
        # Load stop words if needed
        self.stop_words = set()
        if self.remove_stopwords:
            try:
                from nltk.corpus import stopwords
                self.stop_words = set(stopwords.words('english'))
                logger.debug("Loaded %d stop words", len(self.stop_words))
            except Exception as e:
                logger.warning("Failed to load stop words: %s", str(e))
        
        # Initialize stemmer if needed
        self.stemmer = None
        if self.stemming:
            try:
                from nltk.stem.porter import PorterStemmer
                self.stemmer = PorterStemmer()
                logger.debug("Initialized Porter stemmer")
            except Exception as e:
                logger.warning("Failed to initialize stemmer: %s", str(e))
        
        # Initialize lemmatizer if needed
        self.lemmatizer = None
        if self.lemmatization:
            try:
                from nltk.stem import WordNetLemmatizer
                self.lemmatizer = WordNetLemmatizer()
                logger.debug("Initialized WordNet lemmatizer")
            except Exception as e:
                logger.warning("Failed to initialize lemmatizer: %s", str(e))
        
        logger.info("Initialized TextPreprocessor with config: %s", self.config)
    
    def fit(self, X, y=None):
        """
        Fit the preprocessor (no-op for this transformer).
        
        Args:
            X: Input data (list of strings)
            y: Target values (unused)
            
        Returns:
            self
        """
        return self
    
    def transform(self, X: List[str]) -> List[str]:
        """
        Transform the input text data by applying preprocessing steps.
        
        Args:
            X: List of text strings to preprocess
            
        Returns:
            List of preprocessed text strings
        """
        return [self._preprocess_text(text) for text in X]
    
    def _preprocess_text(self, text: str) -> str:
        """
        Apply preprocessing steps to a single text string.
        
        Args:
            text: Input text string
            
        Returns:
            Preprocessed text string
        """
        if not text:
            return ""
        
        # Convert to lowercase if configured
        if self.lowercase:
            text = text.lower()
        
        # Remove punctuation if configured
        if self.remove_punctuation:
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Remove numbers if configured
        if self.remove_numbers:
            text = re.sub(r'\d+', ' ', text)
        
        # Tokenize the text
        tokens = text.split()
        
        # Apply stop word removal, stemming, and lemmatization if configured
        processed_tokens = []
        for token in tokens:
            # Skip short words
            if len(token) < self.min_word_length:
                continue
            
            # Skip stop words
            if self.remove_stopwords and token in self.stop_words:
                continue
            
            # Apply stemming
            if self.stemming and self.stemmer:
                token = self.stemmer.stem(token)
            
            # Apply lemmatization
            if self.lemmatization and self.lemmatizer:
                token = self.lemmatizer.lemmatize(token)
            
            processed_tokens.append(token)
        
        # Join tokens back into a string
        processed_text = ' '.join(processed_tokens)
        
        return processed_text


class TfidfFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts TF-IDF features from preprocessed text.
    
    This class implements TF-IDF vectorization for text features, converting
    preprocessed text into numerical feature vectors suitable for machine learning
    models. It inherits from scikit-learn's BaseEstimator and TransformerMixin
    to be compatible with scikit-learn pipelines.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the TfidfFeatureExtractor with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters for TF-IDF vectorization
        """
        self.config = config or feature_extraction_config.get('tfidf_vectorization', {})
        self.ngram_range = tuple(self.config.get('ngram_range', (1, 2)))
        self.max_features = self.config.get('max_features', 10000)
        self.min_df = self.config.get('min_df', 2)
        self.max_df = self.config.get('max_df', 0.95)
        self.use_idf = self.config.get('use_idf', True)
        self.sublinear_tf = self.config.get('sublinear_tf', True)
        self.norm = self.config.get('norm', 'l2')
        
        # Initialize the TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            ngram_range=self.ngram_range,
            max_features=self.max_features,
            min_df=self.min_df,
            max_df=self.max_df,
            use_idf=self.use_idf,
            sublinear_tf=self.sublinear_tf,
            norm=self.norm
        )
        
        logger.info("Initialized TfidfFeatureExtractor with config: %s", self.config)
    
    def fit(self, X: List[str], y=None):
        """
        Fit the TF-IDF vectorizer on the input data.
        
        Args:
            X: List of preprocessed text strings
            y: Target values (unused)
            
        Returns:
            self
        """
        self.vectorizer.fit(X)
        logger.debug("Fitted TF-IDF vectorizer with vocabulary size: %d", len(self.vectorizer.vocabulary_))
        return self
    
    def transform(self, X: List[str]) -> np.ndarray:
        """
        Transform the input text data into TF-IDF feature vectors.
        
        Args:
            X: List of preprocessed text strings
            
        Returns:
            TF-IDF feature matrix
        """
        tfidf_matrix = self.vectorizer.transform(X)
        logger.debug("Transformed %d documents into TF-IDF matrix with shape: %s", len(X), tfidf_matrix.shape)
        return tfidf_matrix
    
    def get_feature_names(self) -> List[str]:
        """
        Get the feature names (terms) from the TF-IDF vectorizer.
        
        Returns:
            List of feature names
        """
        return self.vectorizer.get_feature_names_out()
    
    def get_top_features(self, tfidf_matrix: np.ndarray, n: int = 10) -> List[Tuple[str, float]]:
        """
        Get the top N features with highest TF-IDF scores for a document.
        
        Args:
            tfidf_matrix: TF-IDF feature matrix for a single document
            n: Number of top features to return
            
        Returns:
            List of (feature_name, score) tuples for the top N features
        """
        if tfidf_matrix.shape[0] != 1:
            raise ValueError("TF-IDF matrix must contain exactly one document")
        
        # Get feature names and scores
        feature_names = self.get_feature_names()
        scores = tfidf_matrix.toarray()[0]
        
        # Sort features by score and get top N
        top_indices = np.argsort(scores)[::-1][:n]
        top_features = [(feature_names[i], scores[i]) for i in top_indices if scores[i] > 0]
        
        return top_features


class MetadataFeatureExtractor(BaseEstimator, TransformerMixin):
    """
    Extracts features from document metadata.
    
    This class implements feature engineering for document metadata such as file size,
    page count, creation date, and other document properties. It inherits from
    scikit-learn's BaseEstimator and TransformerMixin to be compatible with
    scikit-learn pipelines.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the MetadataFeatureExtractor with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters for metadata feature extraction
        """
        self.config = config or feature_extraction_config.get('metadata_features', {})
        self.extract_size = self.config.get('extract_size', True)
        self.extract_page_count = self.config.get('extract_page_count', True)
        self.extract_creation_date = self.config.get('extract_creation_date', True)
        self.extract_modification_date = self.config.get('extract_modification_date', True)
        self.extract_author = self.config.get('extract_author', True)
        self.extract_title = self.config.get('extract_title', True)
        self.extract_keywords = self.config.get('extract_keywords', True)
        
        # Initialize the scaler for numerical features
        self.scaler = StandardScaler()
        self.feature_names = []
        
        logger.info("Initialized MetadataFeatureExtractor with config: %s", self.config)
    
    def fit(self, X: List[Dict[str, Any]], y=None):
        """
        Fit the metadata feature extractor on the input data.
        
        Args:
            X: List of document metadata dictionaries
            y: Target values (unused)
            
        Returns:
            self
        """
        # Extract features from metadata
        features = self._extract_features(X)
        
        # Fit the scaler on numerical features
        numerical_features = features[:, self._get_numerical_indices()]
        if numerical_features.shape[1] > 0:
            self.scaler.fit(numerical_features)
        
        logger.debug("Fitted metadata feature extractor with %d features", len(self.feature_names))
        return self
    
    def transform(self, X: List[Dict[str, Any]]) -> np.ndarray:
        """
        Transform the input metadata into feature vectors.
        
        Args:
            X: List of document metadata dictionaries
            
        Returns:
            Metadata feature matrix
        """
        # Extract features from metadata
        features = self._extract_features(X)
        
        # Scale numerical features
        numerical_indices = self._get_numerical_indices()
        if numerical_indices and features.shape[1] > 0:
            features[:, numerical_indices] = self.scaler.transform(features[:, numerical_indices])
        
        logger.debug("Transformed %d documents into metadata feature matrix with shape: %s", len(X), features.shape)
        return features
    
    def _extract_features(self, X: List[Dict[str, Any]]) -> np.ndarray:
        """
        Extract features from document metadata.
        
        Args:
            X: List of document metadata dictionaries
            
        Returns:
            Metadata feature matrix
        """
        # Initialize feature matrix
        features = []
        self.feature_names = []
        
        for metadata in X:
            document_features = []
            
            # Extract file size
            if self.extract_size and 'size' in metadata:
                document_features.append(float(metadata['size']))
                if not self.feature_names or 'size' not in self.feature_names:
                    self.feature_names.append('size')
            elif self.extract_size:
                document_features.append(0.0)
                if not self.feature_names or 'size' not in self.feature_names:
                    self.feature_names.append('size')
            
            # Extract page count
            if self.extract_page_count and 'page_count' in metadata:
                document_features.append(float(metadata['page_count']))
                if not self.feature_names or 'page_count' not in self.feature_names:
                    self.feature_names.append('page_count')
            elif self.extract_page_count:
                document_features.append(0.0)
                if not self.feature_names or 'page_count' not in self.feature_names:
                    self.feature_names.append('page_count')
            
            # Extract creation date (days since epoch)
            if self.extract_creation_date and 'creation_date' in metadata:
                try:
                    from datetime import datetime
                    creation_date = datetime.fromisoformat(metadata['creation_date'])
                    days_since_epoch = (creation_date - datetime(1970, 1, 1)).days
                    document_features.append(float(days_since_epoch))
                except Exception:
                    document_features.append(0.0)
                if not self.feature_names or 'creation_date' not in self.feature_names:
                    self.feature_names.append('creation_date')
            elif self.extract_creation_date:
                document_features.append(0.0)
                if not self.feature_names or 'creation_date' not in self.feature_names:
                    self.feature_names.append('creation_date')
            
            # Extract modification date (days since epoch)
            if self.extract_modification_date and 'modification_date' in metadata:
                try:
                    from datetime import datetime
                    modification_date = datetime.fromisoformat(metadata['modification_date'])
                    days_since_epoch = (modification_date - datetime(1970, 1, 1)).days
                    document_features.append(float(days_since_epoch))
                except Exception:
                    document_features.append(0.0)
                if not self.feature_names or 'modification_date' not in self.feature_names:
                    self.feature_names.append('modification_date')
            elif self.extract_modification_date:
                document_features.append(0.0)
                if not self.feature_names or 'modification_date' not in self.feature_names:
                    self.feature_names.append('modification_date')
            
            # Extract author presence (binary feature)
            if self.extract_author:
                document_features.append(1.0 if 'author' in metadata and metadata['author'] else 0.0)
                if not self.feature_names or 'has_author' not in self.feature_names:
                    self.feature_names.append('has_author')
            
            # Extract title presence (binary feature)
            if self.extract_title:
                document_features.append(1.0 if 'title' in metadata and metadata['title'] else 0.0)
                if not self.feature_names or 'has_title' not in self.feature_names:
                    self.feature_names.append('has_title')
            
            # Extract keywords presence (binary feature)
            if self.extract_keywords:
                document_features.append(1.0 if 'keywords' in metadata and metadata['keywords'] else 0.0)
                if not self.feature_names or 'has_keywords' not in self.feature_names:
                    self.feature_names.append('has_keywords')
            
            features.append(document_features)
        
        return np.array(features)
    
    def _get_numerical_indices(self) -> List[int]:
        """
        Get the indices of numerical features that need scaling.
        
        Returns:
            List of indices for numerical features
        """
        numerical_features = ['size', 'page_count', 'creation_date', 'modification_date']
        return [i for i, name in enumerate(self.feature_names) if name in numerical_features]
    
    def get_feature_names(self) -> List[str]:
        """
        Get the feature names from the metadata feature extractor.
        
        Returns:
            List of feature names
        """
        return self.feature_names


class DimensionalityReducer(BaseEstimator, TransformerMixin):
    """
    Reduces the dimensionality of feature vectors.
    
    This class implements dimensionality reduction techniques such as PCA and t-SNE
    to reduce the dimensionality of feature vectors while preserving important
    information. It inherits from scikit-learn's BaseEstimator and TransformerMixin
    to be compatible with scikit-learn pipelines.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the DimensionalityReducer with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters for dimensionality reduction
        """
        self.config = config or feature_extraction_config.get('dimensionality_reduction', {})
        self.method = self.config.get('method', 'pca')
        self.n_components = self.config.get('n_components', 100)
        self.random_state = self.config.get('random_state', 42)
        
        # Initialize the dimensionality reduction model based on the method
        if self.method == 'pca':
            self.model = PCA(n_components=self.n_components, random_state=self.random_state)
        elif self.method == 'truncated_svd':
            self.model = TruncatedSVD(n_components=self.n_components, random_state=self.random_state)
        elif self.method == 'tsne':
            self.model = TSNE(n_components=self.n_components, random_state=self.random_state)
        else:
            raise ValueError(f"Unsupported dimensionality reduction method: {self.method}")
        
        logger.info("Initialized DimensionalityReducer with method: %s, n_components: %d", 
                   self.method, self.n_components)
    
    def fit(self, X: np.ndarray, y=None):
        """
        Fit the dimensionality reduction model on the input data.
        
        Args:
            X: Input feature matrix
            y: Target values (unused)
            
        Returns:
            self
        """
        # Check if the input has more features than the number of components
        if X.shape[1] <= self.n_components:
            logger.warning("Input has fewer features (%d) than n_components (%d). Skipping dimensionality reduction.",
                          X.shape[1], self.n_components)
            return self
        
        # Fit the model
        self.model.fit(X)
        
        # Log explained variance ratio for PCA and TruncatedSVD
        if hasattr(self.model, 'explained_variance_ratio_'):
            explained_variance = sum(self.model.explained_variance_ratio_)
            logger.info("Dimensionality reduction explained variance: %.4f", explained_variance)
        
        return self
    
    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        Transform the input feature matrix by reducing its dimensionality.
        
        Args:
            X: Input feature matrix
            
        Returns:
            Reduced feature matrix
        """
        # Check if the input has more features than the number of components
        if X.shape[1] <= self.n_components:
            logger.warning("Input has fewer features (%d) than n_components (%d). Skipping dimensionality reduction.",
                          X.shape[1], self.n_components)
            return X
        
        # Transform the input
        X_reduced = self.model.transform(X)
        
        logger.debug("Reduced feature matrix from shape %s to %s", X.shape, X_reduced.shape)
        return X_reduced
    
    def get_feature_names(self) -> List[str]:
        """
        Get the feature names from the dimensionality reduction model.
        
        Returns:
            List of feature names
        """
        return [f"{self.method}_component_{i}" for i in range(self.n_components)]


class FeatureExtractor:
    """
    Main feature extraction class that orchestrates the entire feature extraction process.
    
    This class combines text extraction, preprocessing, TF-IDF vectorization, metadata
    feature extraction, and dimensionality reduction into a single pipeline for
    extracting features from documents for classification.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the FeatureExtractor with configuration settings.
        
        Args:
            config: Dictionary containing configuration parameters for feature extraction
        """
        self.config = config or feature_extraction_config
        
        # Initialize components
        self.text_extractor = TextExtractor(self.config.get('text_extraction'))
        self.text_preprocessor = TextPreprocessor(self.config.get('text_preprocessing'))
        self.tfidf_extractor = TfidfFeatureExtractor(self.config.get('tfidf_vectorization'))
        self.metadata_extractor = MetadataFeatureExtractor(self.config.get('metadata_features'))
        self.dimensionality_reducer = DimensionalityReducer(self.config.get('dimensionality_reduction'))
        
        # Create pipelines
        self.text_pipeline = Pipeline([
            ('preprocessor', self.text_preprocessor),
            ('tfidf', self.tfidf_extractor)
        ])
        
        logger.info("Initialized FeatureExtractor with all components")
    
    def extract_features(self, file_paths: List[str], metadata: List[Dict[str, Any]] = None) -> FeatureVector:
        """
        Extract features from a list of document file paths.
        
        Args:
            file_paths: List of paths to document files
            metadata: Optional list of document metadata dictionaries
            
        Returns:
            Feature vector for the documents
        """
        # Extract text from documents
        texts = [self.text_extractor.extract(file_path) for file_path in file_paths]
        logger.debug("Extracted text from %d documents", len(texts))
        
        # Extract text features
        text_features = self.text_pipeline.fit_transform(texts)
        logger.debug("Extracted text features with shape: %s", text_features.shape)
        
        # Extract metadata features if metadata is provided
        if metadata:
            metadata_features = self.metadata_extractor.fit_transform(metadata)
            logger.debug("Extracted metadata features with shape: %s", metadata_features.shape)
            
            # Combine text and metadata features
            # Since text_features is likely a sparse matrix, convert metadata_features to sparse
            from scipy.sparse import hstack, csr_matrix
            metadata_features_sparse = csr_matrix(metadata_features)
            combined_features = hstack([text_features, metadata_features_sparse])
            logger.debug("Combined features with shape: %s", combined_features.shape)
        else:
            combined_features = text_features
        
        # Apply dimensionality reduction if configured
        if self.config.get('dimensionality_reduction', {}).get('enabled', False):
            # Convert to dense if needed for some dimensionality reduction methods
            if self.dimensionality_reducer.method == 'pca' and hasattr(combined_features, 'toarray'):
                combined_features = combined_features.toarray()
            
            reduced_features = self.dimensionality_reducer.fit_transform(combined_features)
            logger.debug("Reduced features with shape: %s", reduced_features.shape)
            return reduced_features
        
        return combined_features
    
    def extract_features_from_buffer(self, buffer: bytes, mime_type: str, metadata: Dict[str, Any] = None) -> FeatureVector:
        """
        Extract features from a document buffer.
        
        Args:
            buffer: Binary content of the document
            mime_type: MIME type of the document
            metadata: Optional document metadata dictionary
            
        Returns:
            Feature vector for the document
        """
        # Extract text from buffer
        text = self.text_extractor.extract_from_buffer(buffer, mime_type)
        logger.debug("Extracted text from buffer with MIME type: %s", mime_type)
        
        # Extract text features
        text_features = self.text_pipeline.fit_transform([text])
        logger.debug("Extracted text features with shape: %s", text_features.shape)
        
        # Extract metadata features if metadata is provided
        if metadata:
            metadata_features = self.metadata_extractor.fit_transform([metadata])
            logger.debug("Extracted metadata features with shape: %s", metadata_features.shape)
            
            # Combine text and metadata features
            from scipy.sparse import hstack, csr_matrix
            metadata_features_sparse = csr_matrix(metadata_features)
            combined_features = hstack([text_features, metadata_features_sparse])
            logger.debug("Combined features with shape: %s", combined_features.shape)
        else:
            combined_features = text_features
        
        # Apply dimensionality reduction if configured
        if self.config.get('dimensionality_reduction', {}).get('enabled', False):
            # Convert to dense if needed for some dimensionality reduction methods
            if self.dimensionality_reducer.method == 'pca' and hasattr(combined_features, 'toarray'):
                combined_features = combined_features.toarray()
            
            reduced_features = self.dimensionality_reducer.fit_transform(combined_features)
            logger.debug("Reduced features with shape: %s", reduced_features.shape)
            return reduced_features
        
        return combined_features
    
    def get_top_features(self, feature_vector: FeatureVector, n: int = 10) -> List[Tuple[str, float]]:
        """
        Get the top N features with highest scores for a document.
        
        Args:
            feature_vector: Feature vector for a single document
            n: Number of top features to return
            
        Returns:
            List of (feature_name, score) tuples for the top N features
        """
        if hasattr(feature_vector, 'shape') and len(feature_vector.shape) > 1 and feature_vector.shape[0] != 1:
            raise ValueError("Feature vector must be for a single document")
        
        # If dimensionality reduction was applied, we can't get the original feature names
        if self.config.get('dimensionality_reduction', {}).get('enabled', False):
            # Return component indices and their values
            if hasattr(feature_vector, 'toarray'):
                feature_vector = feature_vector.toarray()[0]
            else:
                feature_vector = feature_vector.flatten()
            
            # Sort features by score and get top N
            top_indices = np.argsort(feature_vector)[::-1][:n]
            feature_names = self.dimensionality_reducer.get_feature_names()
            top_features = [(feature_names[i], feature_vector[i]) for i in top_indices if feature_vector[i] > 0]
            
            return top_features
        
        # If only TF-IDF features were used, get the top terms
        if not self.config.get('metadata_features', {}).get('enabled', False):
            return self.tfidf_extractor.get_top_features(feature_vector, n)
        
        # If both TF-IDF and metadata features were used, we need to handle them separately
        # This is a simplified implementation that just returns the top TF-IDF features
        tfidf_feature_count = len(self.tfidf_extractor.get_feature_names())
        tfidf_features = feature_vector[:, :tfidf_feature_count]
        return self.tfidf_extractor.get_top_features(tfidf_features, n)