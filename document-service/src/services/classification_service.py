#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Classification Service Module

This module orchestrates the document classification process in the Document Service microservice.
It coordinates feature extraction, model selection, classification, and confidence scoring to determine
document types with 99% accuracy.

The service uses scikit-learn models (SVM, Random Forest) to classify documents into categories
and provides confidence scores for classification decisions. It also includes logging and monitoring
for classification performance.
"""

import logging
import time
import json
import os
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import asdict

# Import models
from models import DocumentClassifier, feature_extraction
from models.model_evaluation import calculate_metrics
from models.model_serialization import load_model, save_model

# Import types
from types.classification import ClassificationResult, ConfidenceScore, FeatureVector, ModelParameters
from types.documents import Document, DocumentType, ProcessingStatus, DocumentMetadata
from types.errors import ServiceError, Result, ErrorCategory
from types.messages import MessagePayload

# Import configuration
from config import model_config, app_config, rabbitmq_config

# Import utilities
from utils import ml_utils, logging_utils, time_utils, validation_utils, rabbitmq_utils, s3_utils


class ClassificationService:
    """
    Service for orchestrating document classification.
    
    This service coordinates the document classification process, including feature extraction,
    model selection, classification, and confidence scoring. It determines document types with
    high accuracy and provides confidence scores for classification decisions.
    
    The service uses an ensemble approach combining SVM and Random Forest classifiers to achieve
    99% classification accuracy as required by the technical specification.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize the ClassificationService.
        
        Sets up the document classifier, loads models, and initializes logging.
        
        Args:
            model_path: Optional path to pre-trained models. If None, uses default path from config.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing ClassificationService")
        
        # Set model path
        self.model_path = model_path or model_config.MODEL_PATH
        
        # Initialize document classifier
        try:
            self.classifier = self._initialize_classifier()
            self.logger.info("Document classifier initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize document classifier: {str(e)}", exc_info=True)
            raise RuntimeError(f"Failed to initialize document classifier: {str(e)}") from e
        
        # Load model configuration
        self.confidence_thresholds = model_config.CONFIDENCE_THRESHOLDS
        self.feature_config = model_config.FEATURE_EXTRACTION
        self.model_parameters = model_config.MODEL_PARAMETERS
        
        # Initialize metrics
        self.classification_metrics = {
            "total_documents": 0,
            "successful_classifications": 0,
            "low_confidence_classifications": 0,
            "failed_classifications": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0,
            "document_type_counts": {}
        }
        
        # Initialize recent results cache for performance evaluation
        self.recent_results_cache = []
        self.max_cache_size = model_config.RECENT_RESULTS_CACHE_SIZE
        
        self.logger.info("ClassificationService initialized successfully")
    
    def _initialize_classifier(self) -> DocumentClassifier:
        """
        Initialize the document classifier with appropriate models.
        
        Returns:
            Initialized DocumentClassifier instance
        
        Raises:
            RuntimeError: If models cannot be loaded or initialized
        """
        try:
            # Check if models exist at the specified path
            if os.path.exists(self.model_path):
                self.logger.info(f"Loading existing models from {self.model_path}")
                classifier = load_model(self.model_path)
                
                # Validate model version compatibility
                if not self._validate_model_version(classifier):
                    self.logger.warning("Model version incompatible, initializing new classifier")
                    classifier = self._create_new_classifier()
            else:
                self.logger.info("No existing models found, initializing new classifier")
                classifier = self._create_new_classifier()
                
            return classifier
            
        except Exception as e:
            self.logger.error(f"Error initializing classifier: {str(e)}", exc_info=True)
            raise RuntimeError(f"Error initializing classifier: {str(e)}") from e
    
    def _create_new_classifier(self) -> DocumentClassifier:
        """
        Create a new document classifier with default configuration.
        
        Returns:
            New DocumentClassifier instance
        """
        self.logger.info("Creating new document classifier")
        
        # Create classifier with model parameters from config
        classifier = DocumentClassifier(
            svm_params=self.model_parameters.get("svm", {}),
            rf_params=self.model_parameters.get("random_forest", {}),
            feature_config=self.feature_config
        )
        
        # Save the new classifier
        try:
            os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
            save_model(classifier, self.model_path)
            self.logger.info(f"New classifier saved to {self.model_path}")
        except Exception as e:
            self.logger.warning(f"Failed to save new classifier: {str(e)}")
        
        return classifier
    
    def _validate_model_version(self, classifier: DocumentClassifier) -> bool:
        """
        Validate that the loaded model version is compatible with current code.
        
        Args:
            classifier: The loaded classifier to validate
            
        Returns:
            True if model is compatible, False otherwise
        """
        try:
            # Check model version compatibility
            required_version = model_config.REQUIRED_MODEL_VERSION
            model_version = getattr(classifier, "version", "0.0.0")
            
            self.logger.info(f"Model version: {model_version}, required: {required_version}")
            
            # Simple version check - in production would use semantic versioning
            return model_version == required_version
            
        except Exception as e:
            self.logger.error(f"Error validating model version: {str(e)}", exc_info=True)
            return False
    
    async def classify_document(self, document: Document) -> Result[ClassificationResult]:
        """
        Classify a document and determine its type with confidence score.
        
        This method orchestrates the complete classification process:
        1. Validates the document format and content
        2. Extracts features from the document
        3. Performs classification using the document classifier
        4. Creates a classification result with confidence score
        5. Updates metrics and logs the result
        
        Args:
            document: The document to classify
            
        Returns:
            Result containing ClassificationResult or ServiceError
        """
        start_time = time.time()
        self.logger.info(f"Classifying document: {document.metadata.filename} (ID: {document.metadata.document_id})")
        
        # Update metrics
        self.classification_metrics["total_documents"] += 1
        
        # Validate document
        validation_result = validation_utils.validate_document(document)
        if not validation_result.is_success:
            error_msg = f"Invalid document: {validation_result.error.message}"
            self.logger.error(error_msg)
            self.classification_metrics["failed_classifications"] += 1
            return Result.failure(ServiceError(
                category=ErrorCategory.VALIDATION_ERROR,
                message=error_msg,
                details={
                    "document_id": document.metadata.document_id,
                    "filename": document.metadata.filename,
                    "mime_type": document.metadata.mime_type,
                    "validation_error": validation_result.error.message
                }
            ))
        
        try:
            # Extract features
            features_result = await self._extract_features(document)
            if not features_result.is_success:
                self.classification_metrics["failed_classifications"] += 1
                return features_result
            
            features = features_result.value
            
            # Classify document
            classification_result = await self._perform_classification(features, document.metadata)
            if not classification_result.is_success:
                self.classification_metrics["failed_classifications"] += 1
                return classification_result
            
            document_type, confidence = classification_result.value
            
            # Create classification result
            processing_time = time.time() - start_time
            result = ClassificationResult(
                document_id=document.metadata.document_id,
                document_type=document_type,
                confidence=confidence,
                processing_time=processing_time,
                features_used=list(features.keys()),
                timestamp=time_utils.get_current_timestamp(),
                metadata={
                    "filename": document.metadata.filename,
                    "mime_type": document.metadata.mime_type,
                    "size_bytes": document.metadata.size_bytes,
                    "page_count": document.metadata.page_count,
                    "classification_version": model_config.REQUIRED_MODEL_VERSION
                }
            )
            
            # Update metrics
            self._update_metrics(result)
            
            # Log classification result
            self._log_classification_result(document, result)
            
            # Add to recent results cache for performance evaluation
            self._add_to_recent_results(result)
            
            # Check if confidence meets threshold for automatic processing (75% as per section 4.1.7)
            threshold = self.confidence_thresholds.get(document_type, 0.75)
            if confidence.score < threshold:
                self.logger.warning(
                    f"Low confidence classification ({confidence.score:.4f} < {threshold:.4f}) "
                    f"for document {document.metadata.document_id} - flagging for human review"
                )
                result.requires_review = True
            else:
                self.logger.info(
                    f"High confidence classification ({confidence.score:.4f} >= {threshold:.4f}) "
                    f"for document {document.metadata.document_id} - proceeding with automatic processing"
                )
                result.requires_review = False
            
            return Result.success(result)
            
        except Exception as e:
            error_msg = f"Error classifying document: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            self.classification_metrics["failed_classifications"] += 1
            return Result.failure(ServiceError(
                category=ErrorCategory.PROCESSING_ERROR,
                message=error_msg,
                details={
                    "document_id": document.metadata.document_id,
                    "filename": document.metadata.filename,
                    "exception": str(e)
                }
            ))
    
    async def classify_documents_batch(self, documents: List[Document]) -> Dict[str, Result[ClassificationResult]]:
        """
        Classify a batch of documents.
        
        This method processes multiple documents in sequence and returns results for each.
        For production systems, this could be optimized for parallel processing.
        
        Args:
            documents: List of documents to classify
            
        Returns:
            Dictionary mapping document IDs to classification results
        """
        self.logger.info(f"Classifying batch of {len(documents)} documents")
        results = {}
        
        batch_start_time = time.time()
        
        for document in documents:
            result = await self.classify_document(document)
            results[document.metadata.document_id] = result
        
        batch_processing_time = time.time() - batch_start_time
        self.logger.info(f"Batch classification completed in {batch_processing_time:.2f}s for {len(documents)} documents")
        
        # Log batch statistics
        success_count = sum(1 for r in results.values() if r.is_success)
        failure_count = len(documents) - success_count
        self.logger.info(f"Batch results: {success_count} successful, {failure_count} failed")
        
        return results
    
    async def classify_from_message(self, message: MessagePayload) -> Result[ClassificationResult]:
        """
        Classify a document from a RabbitMQ message payload.
        
        This method extracts document information from a message payload,
        retrieves the document from storage if needed, and classifies it.
        
        Args:
            message: The message payload containing document information
            
        Returns:
            Result containing ClassificationResult or ServiceError
        """
        self.logger.info(f"Processing classification request from message: {message.message_id}")
        
        try:
            # Extract document information from message
            document_id = message.document_id
            storage_path = message.storage_path
            
            # Validate message payload
            if not document_id or not storage_path:
                error_msg = "Invalid message payload: missing document_id or storage_path"
                self.logger.error(error_msg)
                return Result.failure(ServiceError(
                    category=ErrorCategory.VALIDATION_ERROR,
                    message=error_msg,
                    details={"message_id": message.message_id}
                ))
            
            # Retrieve document from storage if needed
            if not message.document_content:
                self.logger.info(f"Retrieving document from storage: {storage_path}")
                storage_result = await s3_utils.download_document(storage_path)
                
                if not storage_result.is_success:
                    self.logger.error(f"Failed to retrieve document: {storage_result.error.message}")
                    return Result.failure(storage_result.error)
                
                document_content = storage_result.value
            else:
                document_content = message.document_content
            
            # Create document object
            document = Document(
                metadata=DocumentMetadata(
                    document_id=document_id,
                    filename=message.filename or os.path.basename(storage_path),
                    mime_type=message.mime_type,
                    size_bytes=len(document_content) if document_content else 0,
                    page_count=message.page_count or 1,
                    source=message.source,
                    created_at=message.created_at or time_utils.get_current_timestamp(),
                    storage_path=storage_path
                ),
                content=document_content,
                status=ProcessingStatus.PENDING_CLASSIFICATION
            )
            
            # Classify document
            return await self.classify_document(document)
            
        except Exception as e:
            error_msg = f"Error processing classification message: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.PROCESSING_ERROR,
                message=error_msg,
                details={"message_id": message.message_id}
            ))
    
    async def _extract_features(self, document: Document) -> Result[FeatureVector]:
        """
        Extract features from a document for classification.
        
        This method extracts text and metadata features from the document
        that will be used by the classification models.
        
        Args:
            document: The document to extract features from
            
        Returns:
            Result containing FeatureVector or ServiceError
        """
        try:
            self.logger.debug(f"Extracting features from document: {document.metadata.filename}")
            
            # Use feature extraction module to extract features
            features = feature_extraction.extract_features(
                document.content,
                document.metadata,
                self.feature_config
            )
            
            if not features or len(features) == 0:
                error_msg = f"No features extracted from document: {document.metadata.filename}"
                self.logger.error(error_msg)
                return Result.failure(ServiceError(
                    category=ErrorCategory.PROCESSING_ERROR,
                    message=error_msg,
                    details={"document_id": document.metadata.document_id}
                ))
            
            self.logger.debug(f"Extracted {len(features)} features from document")
            return Result.success(features)
            
        except Exception as e:
            error_msg = f"Error extracting features: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.PROCESSING_ERROR,
                message=error_msg,
                details={
                    "document_id": document.metadata.document_id,
                    "exception": str(e)
                }
            ))
    
    async def _perform_classification(self, features: FeatureVector, metadata: DocumentMetadata) -> Result[Tuple[DocumentType, ConfidenceScore]]:
        """
        Perform document classification using extracted features.
        
        This method uses the document classifier to determine the document type
        and calculate a confidence score for the classification.
        
        Args:
            features: The extracted features from the document
            metadata: Document metadata for context
            
        Returns:
            Result containing Tuple of (DocumentType, ConfidenceScore) or ServiceError
        """
        try:
            self.logger.debug(f"Performing classification for document: {metadata.document_id}")
            
            # Use document classifier to classify document
            document_type, confidence = self.classifier.classify(features)
            
            # Apply business rules for specific document types if needed
            document_type = self._apply_classification_rules(document_type, confidence, metadata)
            
            self.logger.debug(f"Classification result: {document_type} with confidence {confidence.score:.4f}")
            return Result.success((document_type, confidence))
            
        except Exception as e:
            error_msg = f"Error during classification: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.PROCESSING_ERROR,
                message=error_msg,
                details={
                    "document_id": metadata.document_id,
                    "exception": str(e)
                }
            ))
    
    def _apply_classification_rules(self, document_type: DocumentType, confidence: ConfidenceScore, 
                                   metadata: DocumentMetadata) -> DocumentType:
        """
        Apply business rules to refine classification results.
        
        This method applies domain-specific rules to improve classification accuracy
        based on document metadata and classification confidence.
        
        Args:
            document_type: The classified document type
            confidence: The classification confidence score
            metadata: Document metadata for context
            
        Returns:
            Potentially refined document type
        """
        # Rule: If filename contains "bank" or "statement" and type is UNKNOWN with low confidence,
        # consider it a BANK_STATEMENT
        if (document_type == DocumentType.UNKNOWN and 
                confidence.score < 0.75 and 
                metadata.filename and 
                any(term in metadata.filename.lower() for term in ["bank", "statement", "account"])):
            self.logger.info(f"Applied business rule: Changed UNKNOWN to BANK_STATEMENT based on filename")
            return DocumentType.BANK_STATEMENT
        
        # Rule: If page count > 20 and type is APPLICATION with medium confidence,
        # it's more likely to be a TAX_RETURN
        if (document_type == DocumentType.APPLICATION and 
                confidence.score < 0.75 and 
                metadata.page_count and metadata.page_count > 20):
            self.logger.info(f"Applied business rule: Changed APPLICATION to TAX_RETURN based on page count")
            return DocumentType.TAX_RETURN
        
        # Rule: If filename contains "pay" or "stub" and type is UNKNOWN with low confidence,
        # consider it a PAY_STUB
        if (document_type == DocumentType.UNKNOWN and 
                confidence.score < 0.75 and 
                metadata.filename and 
                any(term in metadata.filename.lower() for term in ["pay", "stub", "salary"])):
            self.logger.info(f"Applied business rule: Changed UNKNOWN to PAY_STUB based on filename")
            return DocumentType.PAY_STUB
        
        # Rule: If filename contains "id", "license", "passport" and type is UNKNOWN with low confidence,
        # consider it an ID_DOCUMENT
        if (document_type == DocumentType.UNKNOWN and 
                confidence.score < 0.75 and 
                metadata.filename and 
                any(term in metadata.filename.lower() for term in ["id", "license", "passport", "identification"])):
            self.logger.info(f"Applied business rule: Changed UNKNOWN to ID_DOCUMENT based on filename")
            return DocumentType.ID_DOCUMENT
        
        return document_type
    
    def _update_metrics(self, result: ClassificationResult) -> None:
        """
        Update classification metrics based on classification result.
        
        This method updates various metrics including successful classifications count,
        average confidence, processing time, and document type distribution.
        
        Args:
            result: The classification result
        """
        # Update successful classifications count
        self.classification_metrics["successful_classifications"] += 1
        
        # Update average confidence
        total_confidence = (self.classification_metrics["average_confidence"] * 
                           (self.classification_metrics["successful_classifications"] - 1))
        total_confidence += result.confidence.score
        self.classification_metrics["average_confidence"] = total_confidence / self.classification_metrics["successful_classifications"]
        
        # Update average processing time
        total_time = (self.classification_metrics["average_processing_time"] * 
                     (self.classification_metrics["successful_classifications"] - 1))
        total_time += result.processing_time
        self.classification_metrics["average_processing_time"] = total_time / self.classification_metrics["successful_classifications"]
        
        # Update low confidence count if applicable (below 75% threshold as per section 4.1.7)
        threshold = self.confidence_thresholds.get(result.document_type, 0.75)
        if result.confidence.score < threshold:
            self.classification_metrics["low_confidence_classifications"] += 1
        
        # Update document type distribution
        doc_type_counts = self.classification_metrics["document_type_counts"]
        doc_type_counts[result.document_type] = doc_type_counts.get(result.document_type, 0) + 1
        
        # Log metrics periodically (every 100 documents)
        if self.classification_metrics["total_documents"] % 100 == 0:
            self.logger.info(f"Classification metrics: {json.dumps(self.get_metrics())}")
    
    def _add_to_recent_results(self, result: ClassificationResult) -> None:
        """
        Add classification result to recent results cache for performance evaluation.
        
        Args:
            result: The classification result to add
        """
        # Add to recent results cache
        self.recent_results_cache.append(result)
        
        # Trim cache if it exceeds maximum size
        if len(self.recent_results_cache) > self.max_cache_size:
            self.recent_results_cache.pop(0)
    
    def _log_classification_result(self, document: Document, result: ClassificationResult) -> None:
        """
        Log classification result with appropriate detail level.
        
        This method logs classification results at different log levels based on
        the confidence score and classification outcome.
        
        Args:
            document: The classified document
            result: The classification result
        """
        # Determine if this is a low confidence classification (below 75% threshold as per section 4.1.7)
        threshold = self.confidence_thresholds.get(result.document_type, 0.75)
        is_low_confidence = result.confidence.score < threshold
        
        # Create structured log entry
        log_entry = {
            "document_id": document.metadata.document_id,
            "filename": document.metadata.filename,
            "document_type": result.document_type,
            "confidence": result.confidence.score,
            "threshold": threshold,
            "processing_time": result.processing_time,
            "timestamp": result.timestamp,
            "requires_review": is_low_confidence
        }
        
        # Log at appropriate level
        if is_low_confidence:
            self.logger.warning(
                f"Low confidence classification: {document.metadata.filename} -> "
                f"{result.document_type} (confidence: {result.confidence.score:.4f}, "
                f"threshold: {threshold:.4f})",
                extra={"classification_result": log_entry}
            )
        else:
            self.logger.info(
                f"Successful classification: {document.metadata.filename} -> "
                f"{result.document_type} (confidence: {result.confidence.score:.4f})",
                extra={"classification_result": log_entry}
            )
        
        # Log detailed information at debug level
        self.logger.debug(f"Classification details: {json.dumps(asdict(result))}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current classification metrics.
        
        Returns:
            Dictionary containing classification metrics including accuracy, 
            processing times, and document type distribution.
        """
        # Calculate accuracy if we have processed documents
        if self.classification_metrics["total_documents"] > 0:
            accuracy = (self.classification_metrics["successful_classifications"] / 
                       self.classification_metrics["total_documents"])
        else:
            accuracy = 0.0
        
        # Add accuracy to metrics
        metrics = dict(self.classification_metrics)
        metrics["accuracy"] = accuracy
        
        # Add timestamp
        metrics["timestamp"] = time_utils.get_current_timestamp()
        metrics["service_name"] = app_config.SERVICE_NAME
        metrics["service_version"] = app_config.SERVICE_VERSION
        
        return metrics
    
    def reset_metrics(self) -> None:
        """
        Reset classification metrics.
        
        This method resets all accumulated metrics to their initial values.
        """
        self.classification_metrics = {
            "total_documents": 0,
            "successful_classifications": 0,
            "low_confidence_classifications": 0,
            "failed_classifications": 0,
            "average_confidence": 0.0,
            "average_processing_time": 0.0,
            "document_type_counts": {}
        }
        self.logger.info("Classification metrics reset")
    
    async def evaluate_model_performance(self) -> Dict[str, float]:
        """
        Evaluate model performance using recent classification results.
        
        This method calculates detailed performance metrics including precision,
        recall, F1 score, and accuracy for the classification models.
        
        Returns:
            Dictionary containing performance metrics
        """
        self.logger.info("Evaluating model performance")
        
        # Use recent results cache if available, otherwise get from classifier
        recent_results = self.recent_results_cache
        if not recent_results:
            recent_results = self.classifier.get_recent_results()
        
        if not recent_results:
            self.logger.warning("No recent classification results available for evaluation")
            return {}
        
        # Calculate performance metrics
        metrics = calculate_metrics(recent_results)
        
        # Add timestamp and version information
        metrics["timestamp"] = time_utils.get_current_timestamp()
        metrics["model_version"] = getattr(self.classifier, "version", "unknown")
        metrics["evaluation_sample_size"] = len(recent_results)
        
        self.logger.info(f"Model performance metrics: {json.dumps(metrics)}")
        return metrics
    
    async def get_document_type_distribution(self) -> Dict[str, int]:
        """
        Get distribution of document types from recent classifications.
        
        This method returns the counts of each document type that has been
        classified, which is useful for monitoring and reporting.
        
        Returns:
            Dictionary mapping document types to counts
        """
        self.logger.info("Getting document type distribution")
        
        # Use metrics if available
        if self.classification_metrics["document_type_counts"]:
            distribution = self.classification_metrics["document_type_counts"]
        else:
            # Use recent results cache if available, otherwise get from classifier
            recent_results = self.recent_results_cache
            if not recent_results:
                recent_results = self.classifier.get_recent_results()
            
            if not recent_results:
                self.logger.warning("No recent classification results available")
                return {}
            
            # Count document types
            distribution = {}
            for result in recent_results:
                doc_type = result.document_type
                distribution[doc_type] = distribution.get(doc_type, 0) + 1
        
        # Convert enum keys to strings for JSON serialization
        string_distribution = {str(k): v for k, v in distribution.items()}
        
        self.logger.info(f"Document type distribution: {json.dumps(string_distribution)}")
        return string_distribution
    
    async def publish_classification_result(self, result: ClassificationResult) -> Result[bool]:
        """
        Publish classification result to the data extraction queue.
        
        This method sends the classification result to the OCR Service via RabbitMQ
        for further processing and data extraction.
        
        Args:
            result: The classification result to publish
            
        Returns:
            Result indicating success or failure
        """
        try:
            self.logger.info(f"Publishing classification result for document: {result.document_id}")
            
            # Create message payload
            message = {
                "document_id": result.document_id,
                "document_type": str(result.document_type),
                "confidence": result.confidence.score,
                "requires_review": result.requires_review,
                "classification_timestamp": result.timestamp,
                "metadata": result.metadata,
                "service": {
                    "name": app_config.SERVICE_NAME,
                    "version": app_config.SERVICE_VERSION
                }
            }
            
            # Publish to data extraction queue
            queue_name = rabbitmq_config.QUEUES["data_extraction"]
            publish_result = await rabbitmq_utils.publish_message(
                queue_name=queue_name,
                message=message,
                message_id=f"classification-{result.document_id}",
                correlation_id=result.document_id
            )
            
            if not publish_result.is_success:
                self.logger.error(f"Failed to publish classification result: {publish_result.error.message}")
                return publish_result
            
            self.logger.info(f"Classification result published successfully for document: {result.document_id}")
            return Result.success(True)
            
        except Exception as e:
            error_msg = f"Error publishing classification result: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.MESSAGING_ERROR,
                message=error_msg,
                details={"document_id": result.document_id}
            ))
    
    async def retrain_model(self, training_data_path: str) -> Result[bool]:
        """
        Retrain the classification model with new training data.
        
        This method allows for updating the classification models with new training data
        to improve accuracy or adapt to changing document patterns.
        
        Args:
            training_data_path: Path to the training data
            
        Returns:
            Result indicating success or failure
        """
        self.logger.info(f"Retraining classification model with data from: {training_data_path}")
        
        try:
            # Validate training data path
            if not os.path.exists(training_data_path):
                error_msg = f"Training data path does not exist: {training_data_path}"
                self.logger.error(error_msg)
                return Result.failure(ServiceError(
                    category=ErrorCategory.VALIDATION_ERROR,
                    message=error_msg
                ))
            
            # Retrain the classifier
            retrain_result = await self.classifier.retrain(training_data_path)
            
            if not retrain_result.is_success:
                self.logger.error(f"Model retraining failed: {retrain_result.error.message}")
                return retrain_result
            
            # Save the updated model
            save_model(self.classifier, self.model_path)
            
            # Reset metrics after retraining
            self.reset_metrics()
            
            self.logger.info("Model retraining completed successfully")
            return Result.success(True)
            
        except Exception as e:
            error_msg = f"Error retraining model: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return Result.failure(ServiceError(
                category=ErrorCategory.PROCESSING_ERROR,
                message=error_msg
            ))
    
    async def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the current classification model.
        
        Returns:
            Dictionary containing model information
        """
        self.logger.info("Getting model information")
        
        try:
            # Get model information from classifier
            model_info = {
                "version": getattr(self.classifier, "version", "unknown"),
                "last_trained": getattr(self.classifier, "last_trained", "unknown"),
                "feature_count": getattr(self.classifier, "feature_count", 0),
                "model_type": getattr(self.classifier, "model_type", "ensemble"),
                "supported_document_types": [str(t) for t in DocumentType],
                "confidence_thresholds": self.confidence_thresholds,
                "accuracy": getattr(self.classifier, "accuracy", 0.0),
                "model_path": self.model_path
            }
            
            # Add performance metrics if available
            performance_metrics = await self.evaluate_model_performance()
            if performance_metrics:
                model_info["performance_metrics"] = performance_metrics
            
            return model_info
            
        except Exception as e:
            self.logger.error(f"Error getting model info: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "version": "unknown"
            }
    
    async def process_document_batch_from_storage(self, storage_paths: List[str]) -> Dict[str, Result[ClassificationResult]]:
        """
        Process a batch of documents from storage paths.
        
        This method retrieves documents from storage, classifies them, and returns the results.
        
        Args:
            storage_paths: List of storage paths to documents
            
        Returns:
            Dictionary mapping document IDs to classification results
        """
        self.logger.info(f"Processing batch of {len(storage_paths)} documents from storage")
        results = {}
        
        for storage_path in storage_paths:
            try:
                # Generate document ID from storage path if not provided
                document_id = os.path.basename(storage_path).split(".")[0]
                
                # Retrieve document from storage
                storage_result = await s3_utils.download_document(storage_path)
                
                if not storage_result.is_success:
                    self.logger.error(f"Failed to retrieve document: {storage_result.error.message}")
                    results[document_id] = Result.failure(storage_result.error)
                    continue
                
                document_content = storage_result.value
                
                # Create document object
                document = Document(
                    metadata=DocumentMetadata(
                        document_id=document_id,
                        filename=os.path.basename(storage_path),
                        mime_type=s3_utils.get_mime_type(storage_path),
                        size_bytes=len(document_content) if document_content else 0,
                        page_count=1,  # Will be updated during processing
                        source="batch_processing",
                        created_at=time_utils.get_current_timestamp(),
                        storage_path=storage_path
                    ),
                    content=document_content,
                    status=ProcessingStatus.PENDING_CLASSIFICATION
                )
                
                # Classify document
                result = await self.classify_document(document)
                results[document_id] = result
                
            except Exception as e:
                error_msg = f"Error processing document from storage: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                results[os.path.basename(storage_path)] = Result.failure(ServiceError(
                    category=ErrorCategory.PROCESSING_ERROR,
                    message=error_msg,
                    details={"storage_path": storage_path}
                ))
        
        return results