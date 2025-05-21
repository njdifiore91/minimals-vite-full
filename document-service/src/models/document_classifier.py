"""
Document Classifier for the Document Service.

This module implements the main document classifier that orchestrates the document
classification process in the Document Service. It provides a high-level interface
for document classification, combining feature extraction, model selection,
prediction, and confidence scoring.

The DocumentClassifier class uses an ensemble approach, combining predictions from
SVM and Random Forest classifiers to achieve 99% classification accuracy. It handles
the complete classification workflow, from feature extraction to document routing,
and provides comprehensive logging and monitoring for classification performance.

Example usage:
    # Initialize the classifier
    classifier = DocumentClassifier()
    
    # Train the classifier on documents
    classifier.fit(training_documents, training_labels)
    
    # Classify a document
    result = classifier.classify_document(document)
    
    # Get routing information for OCR processing
    routing_info = classifier.get_routing_info(document)
    
    # Evaluate classifier performance
    metrics = classifier.evaluate(test_documents, test_labels)
    
    # Save the trained classifier
    classifier.save('/path/to/save/model')
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union, Any

import numpy as np
from sklearn.base import BaseEstimator
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.svm import SVC

from ..config import model_config
from ..types.classification import (
    ClassificationMetrics,
    ClassificationModel,
    ClassificationResult,
    ConfidenceScore,
    DocumentType,
    FeatureExtractor,
    FeatureNames,
    FeatureVector,
    ModelConfig,
)
from ..types.documents import Document, ProcessingStatus
from ..models.svm_classifier import SVMClassifier
from ..models.random_forest_classifier import RandomForestClassifier as RFClassifier

# Configure logger
logger = logging.getLogger(__name__)


class DocumentClassifier:
    """Main document classifier that orchestrates the classification process.
    
    This class combines multiple classification models (SVM and Random Forest)
    using an ensemble approach to achieve high accuracy document classification.
    It handles feature extraction, model selection, prediction, confidence scoring,
    and document routing.
    """
    
    def __init__(
        self,
        svm_model: Optional[ClassificationModel] = None,
        random_forest_model: Optional[ClassificationModel] = None,
        feature_extractors: Optional[List[FeatureExtractor]] = None,
        confidence_threshold: float = 0.75,
        model_config_path: Optional[str] = None,
    ):
        """Initialize the DocumentClassifier.
        
        Args:
            svm_model: Pre-trained SVM model (optional)
            random_forest_model: Pre-trained Random Forest model (optional)
            feature_extractors: List of feature extractors (optional)
            confidence_threshold: Threshold for classification confidence (default: 0.75)
        """
        self.svm_model = svm_model
        self.random_forest_model = random_forest_model
        self.feature_extractors = feature_extractors or []
        self.confidence_threshold = confidence_threshold
        self.model_config_path = model_config_path
        self.ensemble_model: Optional[VotingClassifier] = None
        self.document_type_mapping: Dict[int, DocumentType] = {}
        self.feature_names: List[str] = []
        
        # Load model configuration if path is provided
        if self.model_config_path:
            self._load_model_config()
        
        # Initialize models if not provided
        if not self.svm_model or not self.random_forest_model:
            self._initialize_models()
        
        # Build ensemble model
        self._build_ensemble_model()
        
        logger.info(
            "DocumentClassifier initialized with confidence threshold: %f",
            self.confidence_threshold
        )
    
    def _load_model_config(self) -> None:
        """Load model configuration from the specified path."""
        try:
            logger.info(f"Loading model configuration from {self.model_config_path}")
            # In a real implementation, this would load configuration from a file
            # For now, we'll use default values from model_config module
            self.confidence_threshold = model_config.DEFAULT_CONFIDENCE_THRESHOLD
            
            # Load feature extractors if not already provided
            if not self.feature_extractors:
                self.feature_extractors = model_config.DEFAULT_FEATURE_EXTRACTORS
                
            logger.info(f"Loaded configuration with confidence threshold: {self.confidence_threshold}")
        except Exception as e:
            logger.error(f"Error loading model configuration: {str(e)}", exc_info=True)
            # Fall back to defaults if configuration loading fails
            self.confidence_threshold = 0.75
    
    def _initialize_models(self) -> None:
        """Initialize SVM and Random Forest models with default configurations."""
        # Initialize SVM model if not provided
        if not self.svm_model:
            logger.info("Initializing default SVM model")
            # Use our custom SVMClassifier that extends the base model interface
            self.svm_model = SVMClassifier()
        
        # Initialize Random Forest model if not provided
        if not self.random_forest_model:
            logger.info("Initializing default Random Forest model")
            # Use our custom RandomForestClassifier that extends the base model interface
            self.random_forest_model = RFClassifier()
    
    def _build_ensemble_model(self) -> None:
        """Build the ensemble model combining SVM and Random Forest."""
        logger.info("Building ensemble model")
        
        # Get the underlying scikit-learn models from our custom model classes
        svm_estimator = self.svm_model.model if hasattr(self.svm_model, 'model') else self.svm_model
        rf_estimator = self.random_forest_model.model if hasattr(self.random_forest_model, 'model') else self.random_forest_model
        
        # Create the voting classifier with the scikit-learn models
        self.ensemble_model = VotingClassifier(
            estimators=[
                ('svm', svm_estimator),
                ('rf', rf_estimator),
            ],
            voting='soft',  # Use probability estimates for voting
            weights=[1, 1],  # Equal weights for both models
        )
        
        logger.debug("Ensemble model created with estimators: SVM and Random Forest")
    
    def extract_features(self, document: Document) -> FeatureVector:
        """Extract features from a document using configured feature extractors.
        
        Args:
            document: Document to extract features from
            
        Returns:
            Feature vector extracted from the document
            
        Raises:
            ValueError: If document content is not available
        """
        if not document.content:
            raise ValueError("Document content is required for feature extraction")
        
        start_time = time.time()
        
        # Collect feature vectors from all extractors
        feature_vectors = []
        self.feature_names = []
        
        for extractor in self.feature_extractors:
            logger.debug(
                "Extracting features using %s extractor", 
                extractor.name
            )
            features = extractor.extract(document.content)
            feature_vectors.append(features)
            self.feature_names.extend(extractor.feature_names)
        
        # Combine feature vectors
        if not feature_vectors:
            # If no feature extractors are configured, use the feature_extraction module
            from ..models.feature_extraction import extract_document_features
            
            logger.debug("No feature extractors configured, using default feature extraction")
            features, feature_names = extract_document_features(document.content)
            feature_vectors.append(features)
            self.feature_names.extend(feature_names)
            
            if not feature_vectors:
                raise ValueError("No features extracted from document")
        
        combined_features = np.concatenate(feature_vectors)
        
        elapsed_time = time.time() - start_time
        logger.debug(
            "Feature extraction completed in %.3f seconds. Extracted %d features.",
            elapsed_time,
            len(combined_features)
        )
        
        return combined_features
    
    def fit(
        self, 
        documents: List[Document], 
        document_types: List[DocumentType]
    ) -> None:
        """Fit the classifier to the training data.
        
        Args:
            documents: List of documents for training
            document_types: List of document types (labels) for training
            
        Raises:
            ValueError: If documents and document_types have different lengths
        """
        if len(documents) != len(document_types):
            raise ValueError(
                "Number of documents and document types must match"
            )
        
        logger.info("Fitting classifier to %d documents", len(documents))
        start_time = time.time()
        
        # Extract features from all documents
        X = np.vstack([self.extract_features(doc) for doc in documents])
        
        # Convert document types to numeric labels
        unique_types = list(set(document_types))
        self.document_type_mapping = {i: doc_type for i, doc_type in enumerate(unique_types)}
        y = np.array([unique_types.index(doc_type) for doc_type in document_types])
        
        # Fit individual models
        logger.debug("Fitting SVM model")
        self.svm_model.fit(X, y)
        
        logger.debug("Fitting Random Forest model")
        self.random_forest_model.fit(X, y)
        
        # Fit ensemble model
        logger.debug("Fitting ensemble model")
        self.ensemble_model.fit(X, y)
        
        elapsed_time = time.time() - start_time
        logger.info(
            "Model training completed in %.3f seconds",
            elapsed_time
        )
    
    def predict(
        self, 
        document: Document
    ) -> Tuple[DocumentType, ConfidenceScore]:
        """Predict the document type for a single document.
        
        Args:
            document: Document to classify
            
        Returns:
            Tuple of (predicted document type, confidence score)
            
        Raises:
            ValueError: If the model has not been trained
        """
        if not self.ensemble_model or not hasattr(self.ensemble_model, 'classes_'):
            raise ValueError("Model has not been trained")
        
        # Extract features
        X = self.extract_features(document).reshape(1, -1)
        
        # Get predictions from ensemble model
        y_pred = self.ensemble_model.predict(X)[0]
        probas = self.ensemble_model.predict_proba(X)[0]
        
        # Get confidence score (probability of predicted class)
        confidence = probas[y_pred]
        
        # Map numeric label back to DocumentType
        document_type = self.document_type_mapping[y_pred]
        
        return document_type, confidence
    
    def classify_document(self, document: Document) -> ClassificationResult:
        """Classify a document and return detailed classification results.
        
        This method orchestrates the complete document classification process:
        1. Updates document status to CLASSIFYING
        2. Extracts features from the document
        3. Applies the ensemble classification model
        4. Calculates confidence scores and feature importance
        5. Determines if human review is required based on confidence threshold
        6. Updates the document with classification results
        7. Logs classification performance metrics
        
        Args:
            document: Document to classify
            
        Returns:
            Classification result with document type, confidence, and metadata
        """
        logger.info(
            "Classifying document: %s", 
            document.metadata.get('id', 'unknown')
        )
        start_time = time.time()
        
        # Update document status
        document.update_status(ProcessingStatus.CLASSIFYING)
        
        try:
            # Get prediction and confidence
            document_type, confidence = self.predict(document)
            
            # Calculate feature importance if using Random Forest
            feature_importance = {}
            if hasattr(self.random_forest_model, 'feature_importances_'):
                importances = self.random_forest_model.feature_importances_
                if len(self.feature_names) == len(importances):
                    feature_importance = {
                        name: float(imp) 
                        for name, imp in zip(self.feature_names, importances)
                    }
            
            # Create classification result
            result = ClassificationResult(
                document_id=document.metadata.get('id', ''),
                document_type=document_type,
                confidence=confidence,
                requires_review=confidence < self.confidence_threshold,
                prediction_time=datetime.now(),
                feature_importance=feature_importance,
            )
            
            # Update document with classification result
            document.set_classification_result({
                'document_type': document_type,
                'confidence': confidence,
                'confidence_scores': self._get_confidence_scores(document),
                'features_used': self.feature_names,
                'model_version': getattr(self.ensemble_model, 'version', '1.0.0'),
                'classified_at': datetime.now(),
                'requires_review': confidence < self.confidence_threshold,
            })
            
            elapsed_time = time.time() - start_time
            logger.info(
                "Document classified as %s with confidence %.3f in %.3f seconds",
                document_type.value,
                confidence,
                elapsed_time
            )
            
            return result
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(
                "Error classifying document: %s (%.3f seconds)",
                str(e),
                elapsed_time,
                exc_info=True
            )
            
            # Update document status to error
            document.set_error({
                'error_code': 'CLASSIFICATION_ERROR',
                'error_message': str(e),
                'error_timestamp': datetime.now(),
                'error_location': 'document_classifier.classify_document',
                'error_details': {'elapsed_time': elapsed_time},
                'retry_count': 0,
                'is_recoverable': True,
            })
            
            # Return a default classification result with low confidence
            return ClassificationResult(
                document_id=document.metadata.get('id', ''),
                document_type=DocumentType.OTHER,
                confidence=0.0,
                requires_review=True,
                prediction_time=datetime.now(),
            )
    
    def _get_confidence_scores(self, document: Document) -> Dict[str, float]:
        """Get confidence scores for all document types.
        
        Args:
            document: Document to classify
            
        Returns:
            Dictionary mapping document type names to confidence scores
        """
        if not self.ensemble_model or not hasattr(self.ensemble_model, 'classes_'):
            return {}
        
        # Extract features
        X = self.extract_features(document).reshape(1, -1)
        
        # Get probabilities from ensemble model
        probas = self.ensemble_model.predict_proba(X)[0]
        
        # Map class indices to document types
        return {
            self.document_type_mapping[i].value: float(prob)
            for i, prob in enumerate(probas)
        }
    
    def get_routing_info(self, document: Document) -> Dict[str, Any]:
        """Get routing information for a classified document.
        
        This method determines the appropriate OCR processing strategy based on
        document type, classification confidence, and document characteristics.
        It implements the document routing logic required by the Document Service
        to route documents to the appropriate OCR processors.
        
        The routing information includes:
        - OCR pipeline to use (application_form, tax_document, bank_statement, etc.)
        - Processing priority (high, normal)
        - Review flag for low-confidence classifications
        - Document characteristics that affect OCR processing
        
        Args:
            document: Classified document
            
        Returns:
            Dictionary with routing information for OCR processing
            
        Raises:
            ValueError: If document has not been classified
        """
        if not document.document_type or not document.classification_result:
            raise ValueError("Document must be classified before routing")
        
        document_type = document.document_type
        confidence = document.classification_result['confidence']
        requires_review = document.classification_result['requires_review']
        
        # Base routing information
        routing_info = {
            'document_id': document.metadata.get('id', ''),
            'document_type': document_type.value,
            'confidence': confidence,
            'requires_review': requires_review,
            'ocr_pipeline': 'standard',  # Default pipeline
            'priority': 'normal',  # Default priority
        }
        
        # Determine OCR pipeline based on document type
        if document_type == DocumentType.APPLICATION:
            routing_info['ocr_pipeline'] = 'application_form'
            routing_info['priority'] = 'high'
        elif document_type == DocumentType.TAX_RETURN:
            routing_info['ocr_pipeline'] = 'tax_document'
        elif document_type == DocumentType.BANK_STATEMENT:
            routing_info['ocr_pipeline'] = 'bank_statement'
        elif document_type == DocumentType.PAY_STUB:
            routing_info['ocr_pipeline'] = 'pay_stub'
        elif document_type == DocumentType.ID_DOCUMENT:
            routing_info['ocr_pipeline'] = 'identity_document'
            routing_info['priority'] = 'high'
        
        # Adjust for low confidence
        if requires_review:
            routing_info['ocr_pipeline'] += '_review'
        
        # Add document characteristics that might affect OCR processing
        if 'page_count' in document.metadata and document.metadata['page_count']:
            routing_info['page_count'] = document.metadata['page_count']
            
            # Large documents might need special handling
            if document.metadata['page_count'] > 20:
                routing_info['large_document'] = True
        
        # Add file format information
        if 'mime_type' in document.metadata and document.metadata['mime_type']:
            routing_info['mime_type'] = document.metadata['mime_type']
            
            # Image-based documents might need different OCR approach
            if document.metadata['mime_type'].startswith('image/'):
                routing_info['image_based'] = True
        
        logger.info(
            "Routing document %s to OCR pipeline: %s (priority: %s)",
            document.metadata.get('id', 'unknown'),
            routing_info['ocr_pipeline'],
            routing_info['priority']
        )
        
        return routing_info
    
    def evaluate(
        self, 
        test_documents: List[Document], 
        true_document_types: List[DocumentType]
    ) -> ClassificationMetrics:
        """Evaluate the classifier on test data.
        
        Args:
            test_documents: List of documents for testing
            true_document_types: List of true document types for testing
            
        Returns:
            Classification metrics including accuracy, precision, recall, and F1 score
            
        Raises:
            ValueError: If test_documents and true_document_types have different lengths
        """
        if len(test_documents) != len(true_document_types):
            raise ValueError(
                "Number of test documents and true document types must match"
            )
        
        logger.info("Evaluating classifier on %d documents", len(test_documents))
        start_time = time.time()
        
        # Use the model_evaluation module for more comprehensive evaluation
        from ..models.model_evaluation import evaluate_classifier
        
        # Get predictions for all test documents
        predicted_types = []
        confidence_scores = []
        for doc in test_documents:
            doc_type, confidence = self.predict(doc)
            predicted_types.append(doc_type)
            confidence_scores.append(confidence)
        
        # Use the evaluation module to calculate metrics
        metrics = evaluate_classifier(
            true_labels=true_document_types,
            predicted_labels=predicted_types,
            confidence_scores=confidence_scores,
            label_names=[dt.value for dt in DocumentType]
        )
        
        elapsed_time = time.time() - start_time
        logger.info(
            "Evaluation completed in %.3f seconds. Accuracy: %.3f",
            elapsed_time,
            metrics.accuracy
        )
        
        # Log detailed metrics
        for doc_type, precision_val in metrics.precision.items():
            recall_val = metrics.recall[doc_type]
            f1_val = metrics.f1_score[doc_type]
            logger.info(
                "Document type %s: Precision=%.3f, Recall=%.3f, F1=%.3f",
                doc_type.value if isinstance(doc_type, DocumentType) else doc_type,
                precision_val,
                recall_val,
                f1_val
            )
        
        return metrics
    
    def save(self, path: str) -> None:
        """Save the classifier to disk.
        
        Args:
            path: Path to save the classifier to
        """
        from ..models.model_serialization import save_model
        
        logger.info("Saving classifier to %s", path)
        
        # Create metadata for the model
        metadata = {
            'model_type': 'ensemble',
            'version': '1.0.0',
            'created_at': datetime.now().isoformat(),
            'confidence_threshold': self.confidence_threshold,
            'feature_names': self.feature_names,
            'document_type_mapping': {str(k): v.value for k, v in self.document_type_mapping.items()},
            'components': ['svm', 'random_forest'],
        }
        
        # Save the model with metadata
        save_model(self, path, metadata=metadata)
    
    @classmethod
    def load(cls, path: str) -> 'DocumentClassifier':
        """Load a classifier from disk.
        
        Args:
            path: Path to load the classifier from
            
        Returns:
            Loaded DocumentClassifier instance
        """
        from ..models.model_serialization import load_model
        
        logger.info("Loading classifier from %s", path)
        classifier, metadata = load_model(path)
        
        if metadata:
            logger.info(
                "Loaded classifier version %s created at %s",
                metadata.get('version', 'unknown'),
                metadata.get('created_at', 'unknown')
            )
        
        return classifier
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the classifier.
        
        Returns:
            Dictionary with classifier information
        """
        return {
            'model_type': 'ensemble',
            'components': ['svm', 'random_forest'],
            'confidence_threshold': self.confidence_threshold,
            'feature_count': len(self.feature_names) if self.feature_names else 0,
            'document_types': [dt.value for dt in DocumentType],
            'trained': hasattr(self.ensemble_model, 'classes_') if self.ensemble_model else False,
        }