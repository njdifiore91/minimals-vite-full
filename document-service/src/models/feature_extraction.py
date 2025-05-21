#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Feature extraction utilities for document classification.

This module provides utilities for extracting features from documents for classification
in the Document Service. It implements text extraction, preprocessing, vectorization,
and feature engineering techniques to convert raw documents into feature vectors suitable
for machine learning models.
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

# Import document-specific types
from ..types.documents import Document, DocumentType, DocumentMetadata
from ..types.classification import FeatureVector, ClassificationResult

# Set up logging
logger = logging.getLogger(__name__)


# Text extraction functions for different document formats
class TextExtractor:
    """Extracts text from various document formats."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the text extractor with configuration.
        
        Args:
            config: Configuration dictionary with extraction parameters
        """
        self.config = config or {}
        self._setup_extractors()
        
    def _setup_extractors(self):
        """Set up the document format-specific extractors."""
        # Import specialized extractors only when needed to avoid unnecessary dependencies
        try:
            # PDF extraction libraries
            import pdfminer.high_level
            import pdfminer.layout
            self._has_pdfminer = True
        except ImportError:
            logger.warning("pdfminer.six not installed. PDF text extraction will be limited.")
            self._has_pdfminer = False
            
        try:
            # OCR libraries for image-based documents
            import pytesseract
            from PIL import Image
            self._has_ocr = True
        except ImportError:
            logger.warning("pytesseract or PIL not installed. OCR capabilities will be limited.")
            self._has_ocr = False
    
    def extract_text(self, document: Document) -> str:
        """Extract text from a document based on its format.
        
        Args:
            document: The document to extract text from
            
        Returns:
            Extracted text as a string
        """
        mime_type = document.metadata.mime_type.lower() if document.metadata.mime_type else ""
        
        if "pdf" in mime_type:
            return self._extract_from_pdf(document)
        elif any(img_type in mime_type for img_type in ["image", "jpg", "jpeg", "png", "tiff", "bmp"]):
            return self._extract_from_image(document)
        elif any(txt_type in mime_type for txt_type in ["text", "csv", "json", "xml", "html"]):
            return self._extract_from_text(document)
        else:
            logger.warning(f"Unsupported document format: {mime_type}. Attempting generic extraction.")
            return self._extract_generic(document)
    
    def _extract_from_pdf(self, document: Document) -> str:
        """Extract text from a PDF document.
        
        Args:
            document: PDF document to extract text from
            
        Returns:
            Extracted text as a string
        """
        if not self._has_pdfminer:
            logger.warning("PDF extraction requires pdfminer.six. Using fallback method.")
            return self._extract_generic(document)
        
        try:
            import io
            from pdfminer.high_level import extract_text
            
            # Create a BytesIO object from the document content
            pdf_stream = io.BytesIO(document.content)
            
            # Extract text using pdfminer
            text = extract_text(pdf_stream)
            
            # If text extraction failed or returned empty, try OCR as fallback
            if not text.strip() and self._has_ocr:
                logger.info("PDF appears to be scanned or has no extractable text. Attempting OCR.")
                return self._extract_from_pdf_with_ocr(document)
                
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    
    def _extract_from_pdf_with_ocr(self, document: Document) -> str:
        """Extract text from a PDF document using OCR.
        
        Args:
            document: PDF document to extract text from using OCR
            
        Returns:
            Extracted text as a string
        """
        if not self._has_ocr:
            return ""
            
        try:
            import io
            import tempfile
            import pytesseract
            from PIL import Image
            from pdf2image import convert_from_bytes
            
            # Convert PDF to images
            images = convert_from_bytes(
                document.content,
                dpi=300,
                fmt="jpeg",
                thread_count=os.cpu_count() or 1
            )
            
            # Extract text from each image
            text_parts = []
            for img in images:
                text = pytesseract.image_to_string(img, lang="eng")
                text_parts.append(text)
                
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting text from PDF with OCR: {str(e)}")
            return ""
    
    def _extract_from_image(self, document: Document) -> str:
        """Extract text from an image document using OCR.
        
        Args:
            document: Image document to extract text from
            
        Returns:
            Extracted text as a string
        """
        if not self._has_ocr:
            logger.warning("Image text extraction requires pytesseract. Returning empty string.")
            return ""
            
        try:
            import io
            import pytesseract
            from PIL import Image
            
            # Create an image from the document content
            image = Image.open(io.BytesIO(document.content))
            
            # Extract text using OCR
            text = pytesseract.image_to_string(image, lang="eng")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            return ""
    
    def _extract_from_text(self, document: Document) -> str:
        """Extract text from a text-based document.
        
        Args:
            document: Text document to extract text from
            
        Returns:
            Extracted text as a string
        """
        try:
            # Attempt to decode with UTF-8 first
            return document.content.decode("utf-8")
        except UnicodeDecodeError:
            # Try other common encodings
            for encoding in ["latin-1", "iso-8859-1", "windows-1252"]:
                try:
                    return document.content.decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            logger.error("Failed to decode text document with common encodings")
            return ""
    
    def _extract_generic(self, document: Document) -> str:
        """Generic text extraction fallback method.
        
        Args:
            document: Document to extract text from
            
        Returns:
            Extracted text as a string
        """
        try:
            # Try to decode as text
            return self._extract_from_text(document)
        except Exception:
            # If all else fails, return empty string
            return ""


# Text preprocessing pipeline
class TextPreprocessor:
    """Preprocesses text for feature extraction."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the text preprocessor with configuration.
        
        Args:
            config: Configuration dictionary with preprocessing parameters
        """
        self.config = config or {}
        self._setup_preprocessor()
        
    def _setup_preprocessor(self):
        """Set up the text preprocessing components."""
        # Import NLP libraries only when needed
        try:
            import nltk
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            from nltk.stem import PorterStemmer, WordNetLemmatizer
            
            # Download required NLTK resources if not already present
            for resource in ["punkt", "stopwords", "wordnet"]:
                try:
                    nltk.data.find(f"tokenizers/{resource}")
                except LookupError:
                    nltk.download(resource, quiet=True)
            
            self.tokenizer = word_tokenize
            self.stemmer = PorterStemmer()
            self.lemmatizer = WordNetLemmatizer()
            self.stop_words = set(stopwords.words("english"))
            self._has_nltk = True
        except ImportError:
            logger.warning("NLTK not installed. Using basic text preprocessing.")
            self._has_nltk = False
    
    def preprocess(self, text: str) -> str:
        """Preprocess text for feature extraction.
        
        Args:
            text: Raw text to preprocess
            
        Returns:
            Preprocessed text as a string
        """
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and digits
        text = re.sub(r"[^a-zA-Z\s]", "", text)
        
        if self._has_nltk:
            # Tokenize
            tokens = self.tokenizer(text)
            
            # Remove stop words
            tokens = [token for token in tokens if token not in self.stop_words]
            
            # Apply stemming or lemmatization based on config
            if self.config.get("use_lemmatization", False):
                tokens = [self.lemmatizer.lemmatize(token) for token in tokens]
            else:
                tokens = [self.stemmer.stem(token) for token in tokens]
                
            # Join tokens back into a string
            return " ".join(tokens)
        else:
            # Basic preprocessing without NLTK
            # Remove extra whitespace
            text = re.sub(r"\s+", " ", text).strip()
            return text


# Feature vectorization
class TextVectorizer:
    """Converts preprocessed text into feature vectors."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the text vectorizer with configuration.
        
        Args:
            config: Configuration dictionary with vectorization parameters
        """
        self.config = config or {}
        self._setup_vectorizer()
        
    def _setup_vectorizer(self):
        """Set up the text vectorization components."""
        # Configure TF-IDF vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=self.config.get("max_features", 10000),
            ngram_range=self.config.get("ngram_range", (1, 2)),
            min_df=self.config.get("min_df", 5),
            max_df=self.config.get("max_df", 0.8),
            use_idf=self.config.get("use_idf", True),
            sublinear_tf=self.config.get("sublinear_tf", True)
        )
        self.is_fitted = False
        
    def fit(self, texts: List[str]):
        """Fit the vectorizer on a corpus of texts.
        
        Args:
            texts: List of preprocessed text documents
        """
        if not texts:
            logger.warning("Empty text corpus provided for vectorizer fitting")
            return
            
        self.vectorizer.fit(texts)
        self.is_fitted = True
        logger.info(f"Vectorizer fitted with {len(self.vectorizer.get_feature_names_out())} features")
        
    def transform(self, texts: List[str]) -> np.ndarray:
        """Transform texts into feature vectors.
        
        Args:
            texts: List of preprocessed text documents
            
        Returns:
            Feature vectors as a numpy array
        """
        if not self.is_fitted:
            logger.warning("Vectorizer not fitted. Returning empty feature vectors.")
            return np.zeros((len(texts), 1))
            
        return self.vectorizer.transform(texts).toarray()
    
    def fit_transform(self, texts: List[str]) -> np.ndarray:
        """Fit the vectorizer and transform texts into feature vectors.
        
        Args:
            texts: List of preprocessed text documents
            
        Returns:
            Feature vectors as a numpy array
        """
        self.fit(texts)
        return self.transform(texts)
    
    def get_feature_names(self) -> List[str]:
        """Get the feature names from the vectorizer.
        
        Returns:
            List of feature names
        """
        if not self.is_fitted:
            return []
            
        return self.vectorizer.get_feature_names_out().tolist()


# Document metadata extraction
class MetadataExtractor:
    """Extracts features from document metadata."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the metadata extractor with configuration.
        
        Args:
            config: Configuration dictionary with extraction parameters
        """
        self.config = config or {}
        
    def extract_metadata_features(self, document: Document) -> Dict[str, float]:
        """Extract features from document metadata.
        
        Args:
            document: Document to extract metadata features from
            
        Returns:
            Dictionary of metadata features
        """
        features = {}
        
        # Document size in KB
        features["size_kb"] = len(document.content) / 1024.0 if document.content else 0.0
        
        # MIME type features
        mime_type = document.metadata.mime_type.lower() if document.metadata.mime_type else ""
        features["is_pdf"] = 1.0 if "pdf" in mime_type else 0.0
        features["is_image"] = 1.0 if any(img_type in mime_type for img_type in ["image", "jpg", "jpeg", "png", "tiff", "bmp"]) else 0.0
        features["is_text"] = 1.0 if any(txt_type in mime_type for txt_type in ["text", "csv", "json", "xml", "html"]) else 0.0
        
        # Filename features
        filename = document.metadata.filename.lower() if document.metadata.filename else ""
        features["has_application_in_name"] = 1.0 if "application" in filename else 0.0
        features["has_form_in_name"] = 1.0 if "form" in filename else 0.0
        features["has_statement_in_name"] = 1.0 if "statement" in filename else 0.0
        features["has_invoice_in_name"] = 1.0 if "invoice" in filename else 0.0
        features["has_id_in_name"] = 1.0 if any(id_term in filename for id_term in ["id", "identification", "license", "passport"]) else 0.0
        
        # Additional metadata if available
        if hasattr(document.metadata, "page_count") and document.metadata.page_count is not None:
            features["page_count"] = float(document.metadata.page_count)
        
        if hasattr(document.metadata, "creation_date") and document.metadata.creation_date is not None:
            # Convert date to days since epoch
            import datetime
            epoch = datetime.datetime(1970, 1, 1)
            creation_date = document.metadata.creation_date
            if isinstance(creation_date, datetime.datetime):
                features["days_since_creation"] = (datetime.datetime.now() - creation_date).days
        
        return features


# Dimensionality reduction
class DimensionalityReducer:
    """Reduces dimensionality of feature vectors."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the dimensionality reducer with configuration.
        
        Args:
            config: Configuration dictionary with reduction parameters
        """
        self.config = config or {}
        self.method = self.config.get("method", "pca")
        self.n_components = self.config.get("n_components", 50)
        self._setup_reducer()
        
    def _setup_reducer(self):
        """Set up the dimensionality reduction component."""
        if self.method == "pca":
            self.reducer = PCA(n_components=self.n_components, random_state=42)
        elif self.method == "svd":
            self.reducer = TruncatedSVD(n_components=self.n_components, random_state=42)
        elif self.method == "tsne":
            self.reducer = TSNE(n_components=self.n_components, random_state=42)
        else:
            logger.warning(f"Unknown dimensionality reduction method: {self.method}. Using PCA.")
            self.method = "pca"
            self.reducer = PCA(n_components=self.n_components, random_state=42)
        
        self.is_fitted = False
        
    def fit(self, X: np.ndarray):
        """Fit the dimensionality reducer on feature vectors.
        
        Args:
            X: Feature vectors as a numpy array
        """
        if X.shape[0] < 2:
            logger.warning("Not enough samples for dimensionality reduction")
            return
            
        if X.shape[1] <= self.n_components:
            logger.warning(f"Input dimension {X.shape[1]} is less than or equal to output dimension {self.n_components}")
            return
            
        # Scale the data for better results
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit the reducer
        if self.method != "tsne":  # t-SNE doesn't have a separate fit method
            self.reducer.fit(X_scaled)
            self.is_fitted = True
            logger.info(f"Dimensionality reducer fitted: {self.method} with {self.n_components} components")
        else:
            self.is_fitted = True
            logger.info(f"t-SNE reducer prepared with {self.n_components} components")
        
    def transform(self, X: np.ndarray) -> np.ndarray:
        """Transform feature vectors to lower dimensionality.
        
        Args:
            X: Feature vectors as a numpy array
            
        Returns:
            Reduced feature vectors as a numpy array
        """
        if not self.is_fitted:
            logger.warning("Dimensionality reducer not fitted. Returning original features.")
            return X
            
        if X.shape[1] != self.scaler.n_features_in_:
            logger.warning(f"Input dimension {X.shape[1]} doesn't match fitted dimension {self.scaler.n_features_in_}")
            return X
            
        # Scale the data
        X_scaled = self.scaler.transform(X)
        
        # Apply dimensionality reduction
        if self.method != "tsne":
            return self.reducer.transform(X_scaled)
        else:
            # t-SNE doesn't have a separate transform method, so we fit_transform each time
            return self.reducer.fit_transform(X_scaled)
    
    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """Fit the reducer and transform feature vectors to lower dimensionality.
        
        Args:
            X: Feature vectors as a numpy array
            
        Returns:
            Reduced feature vectors as a numpy array
        """
        if X.shape[0] < 2:
            logger.warning("Not enough samples for dimensionality reduction")
            return X
            
        if X.shape[1] <= self.n_components:
            logger.warning(f"Input dimension {X.shape[1]} is less than or equal to output dimension {self.n_components}")
            return X
            
        # Scale the data for better results
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Fit and transform
        if self.method != "tsne":
            self.reducer.fit(X_scaled)
            self.is_fitted = True
            return self.reducer.transform(X_scaled)
        else:
            self.is_fitted = True
            return self.reducer.fit_transform(X_scaled)


# Main feature extraction class
class FeatureExtractor:
    """Main class for extracting features from documents."""
    
    def __init__(self, config: Dict[str, Any] = None):
        """Initialize the feature extractor with configuration.
        
        Args:
            config: Configuration dictionary with extraction parameters
        """
        self.config = config or {}
        
        # Initialize components
        self.text_extractor = TextExtractor(self.config.get("text_extraction", {}))
        self.text_preprocessor = TextPreprocessor(self.config.get("text_preprocessing", {}))
        self.text_vectorizer = TextVectorizer(self.config.get("text_vectorization", {}))
        self.metadata_extractor = MetadataExtractor(self.config.get("metadata_extraction", {}))
        
        # Initialize dimensionality reducer if configured
        if self.config.get("use_dimensionality_reduction", False):
            self.dim_reducer = DimensionalityReducer(self.config.get("dimensionality_reduction", {}))
        else:
            self.dim_reducer = None
        
        self.is_fitted = False
        
    def fit(self, documents: List[Document]):
        """Fit the feature extractor on a corpus of documents.
        
        Args:
            documents: List of documents to fit on
        """
        if not documents:
            logger.warning("Empty document corpus provided for feature extractor fitting")
            return
            
        # Extract and preprocess text from documents
        texts = []
        for doc in documents:
            text = self.text_extractor.extract_text(doc)
            preprocessed_text = self.text_preprocessor.preprocess(text)
            texts.append(preprocessed_text)
        
        # Fit the text vectorizer
        self.text_vectorizer.fit(texts)
        
        # Fit the dimensionality reducer if configured
        if self.dim_reducer is not None:
            # Get text features
            text_features = self.text_vectorizer.transform(texts)
            
            # Get metadata features
            metadata_features_list = []
            for doc in documents:
                metadata_features = self.metadata_extractor.extract_metadata_features(doc)
                metadata_features_list.append(list(metadata_features.values()))
            
            metadata_features_array = np.array(metadata_features_list)
            
            # Combine features
            combined_features = np.hstack((text_features, metadata_features_array))
            
            # Fit the dimensionality reducer
            self.dim_reducer.fit(combined_features)
        
        self.is_fitted = True
        logger.info("Feature extractor fitted successfully")
        
    def transform(self, documents: List[Document]) -> np.ndarray:
        """Transform documents into feature vectors.
        
        Args:
            documents: List of documents to transform
            
        Returns:
            Feature vectors as a numpy array
        """
        if not self.is_fitted:
            logger.warning("Feature extractor not fitted. Returning empty feature vectors.")
            return np.zeros((len(documents), 1))
            
        # Extract and preprocess text from documents
        texts = []
        for doc in documents:
            text = self.text_extractor.extract_text(doc)
            preprocessed_text = self.text_preprocessor.preprocess(text)
            texts.append(preprocessed_text)
        
        # Transform texts to feature vectors
        text_features = self.text_vectorizer.transform(texts)
        
        # Extract metadata features
        metadata_features_list = []
        for doc in documents:
            metadata_features = self.metadata_extractor.extract_metadata_features(doc)
            metadata_features_list.append(list(metadata_features.values()))
        
        metadata_features_array = np.array(metadata_features_list)
        
        # Combine features
        combined_features = np.hstack((text_features, metadata_features_array))
        
        # Apply dimensionality reduction if configured
        if self.dim_reducer is not None:
            return self.dim_reducer.transform(combined_features)
        else:
            return combined_features
    
    def fit_transform(self, documents: List[Document]) -> np.ndarray:
        """Fit the feature extractor and transform documents into feature vectors.
        
        Args:
            documents: List of documents to fit on and transform
            
        Returns:
            Feature vectors as a numpy array
        """
        self.fit(documents)
        return self.transform(documents)
    
    def extract_features_from_document(self, document: Document) -> FeatureVector:
        """Extract features from a single document.
        
        Args:
            document: Document to extract features from
            
        Returns:
            Feature vector for the document
        """
        # Transform the document into a feature vector
        feature_array = self.transform([document])
        
        # Convert to FeatureVector type
        return FeatureVector(
            values=feature_array[0],
            feature_names=self.get_feature_names(),
            document_id=document.metadata.id if hasattr(document.metadata, "id") else None
        )
    
    def get_feature_names(self) -> List[str]:
        """Get the feature names from the feature extractor.
        
        Returns:
            List of feature names
        """
        if not self.is_fitted:
            return []
            
        # Get text feature names
        text_feature_names = self.text_vectorizer.get_feature_names()
        
        # Get metadata feature names
        # Use a sample document to get the metadata feature names
        sample_metadata = {
            "size_kb": 0.0,
            "is_pdf": 0.0,
            "is_image": 0.0,
            "is_text": 0.0,
            "has_application_in_name": 0.0,
            "has_form_in_name": 0.0,
            "has_statement_in_name": 0.0,
            "has_invoice_in_name": 0.0,
            "has_id_in_name": 0.0,
            "page_count": 0.0,
            "days_since_creation": 0.0
        }
        metadata_feature_names = list(sample_metadata.keys())
        
        # Combine feature names
        combined_feature_names = text_feature_names + metadata_feature_names
        
        # If dimensionality reduction is used, feature names are just component indices
        if self.dim_reducer is not None:
            return [f"component_{i}" for i in range(self.dim_reducer.n_components)]
        else:
            return combined_feature_names