#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pytest configuration file for Document Service type tests.

This module provides common fixtures, mocks, and utilities used across all type test modules.
It centralizes test setup and teardown logic, reducing duplication and ensuring consistent
test environments.

Fixtures defined here are automatically discovered by pytest and can be used in any test
function without explicit imports.
"""

import os
import json
import uuid
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Callable, Iterator, Type
from unittest.mock import MagicMock, patch, PropertyMock

import pytest
import numpy as np
from numpy.typing import NDArray

# Import types from the document service
from document_service.types import (
    # Classification types
    DocumentType,
    ClassificationResult,
    ClassificationModel,
    ClassificationMetrics,
    FeatureVector,
    FeatureMatrix,
    ModelParameters,
    ModelVersion,
    ConfidenceScore,
    
    # Storage types
    S3ClientConfig,
    StorageOptions,
    StorageMetadata,
    BucketConfig,
    StorageResult,
    StorageOperations,
    StorageKey,
    
    # Configuration types
    ServiceConfig,
    ModelConfig,
    RabbitMQConfig,
    S3Config,
    LoggingConfig,
    AppConfig,
    EnvironmentType
)


# Constants for testing
TEST_DOCUMENT_TYPES = [
    DocumentType.LOAN_APPLICATION,
    DocumentType.TAX_RETURN,
    DocumentType.BANK_STATEMENT,
    DocumentType.PAY_STUB,
    DocumentType.IDENTITY_DOCUMENT,
    DocumentType.BUSINESS_LICENSE,
    DocumentType.UTILITY_BILL,
    DocumentType.INSURANCE_DOCUMENT,
    DocumentType.OTHER
]

TEST_CONFIDENCE_THRESHOLDS = {
    "high": 0.95,
    "medium": 0.85,
    "low": 0.75,
    "below_threshold": 0.65,
    "very_low": 0.50
}


# ===== Fixture Utilities =====

def generate_random_feature_vector(size: int = 100) -> FeatureVector:
    """Generate a random feature vector for testing.
    
    Args:
        size: Size of the feature vector
        
    Returns:
        A random feature vector with the specified size
    """
    return np.random.rand(size).astype(np.float64)


def generate_random_feature_matrix(n_samples: int = 10, n_features: int = 100) -> FeatureMatrix:
    """Generate a random feature matrix for testing.
    
    Args:
        n_samples: Number of samples in the matrix
        n_features: Number of features per sample
        
    Returns:
        A random feature matrix with the specified dimensions
    """
    return np.random.rand(n_samples, n_features).astype(np.float64)


def create_classification_result(
    document_type: DocumentType,
    confidence: float,
    needs_review: Optional[bool] = None,
    feature_importance: Optional[Dict[str, float]] = None,
    processing_time_ms: Optional[float] = None
) -> ClassificationResult:
    """Create a ClassificationResult instance for testing.
    
    Args:
        document_type: The document type classification
        confidence: The confidence score (0.0 to 1.0)
        needs_review: Whether the document needs human review
        feature_importance: Optional feature importance dictionary
        processing_time_ms: Optional processing time in milliseconds
        
    Returns:
        A ClassificationResult instance
    """
    # Create probabilities for all document types
    probabilities = {doc_type: 0.0 for doc_type in DocumentType}
    probabilities[document_type] = confidence
    
    # Distribute remaining probability among other types
    remaining_prob = 1.0 - confidence
    other_types = [dt for dt in DocumentType if dt != document_type]
    if other_types:
        prob_per_type = remaining_prob / len(other_types)
        for dt in other_types:
            probabilities[dt] = prob_per_type
    
    # Determine if review is needed based on confidence if not specified
    if needs_review is None:
        needs_review = confidence < TEST_CONFIDENCE_THRESHOLDS["low"]
    
    return ClassificationResult(
        document_type=document_type,
        confidence=confidence,
        probabilities=probabilities,
        needs_review=needs_review,
        feature_importance=feature_importance,
        processing_time_ms=processing_time_ms
    )


def create_storage_metadata(
    document_id: str,
    application_id: str,
    document_type: DocumentType,
    confidence: float,
    file_size: int = 1024,
    content_type: str = "application/pdf"
) -> StorageMetadata:
    """Create a StorageMetadata instance for testing.
    
    Args:
        document_id: Unique document identifier
        application_id: Application identifier
        document_type: Document type classification
        confidence: Classification confidence score
        file_size: Size of the document in bytes
        content_type: MIME type of the document
        
    Returns:
        A StorageMetadata instance
    """
    now = datetime.utcnow()
    
    return {
        "document_id": document_id,
        "application_id": application_id,
        "filename": f"{document_id}.pdf",
        "file_size": file_size,
        "content_type": content_type,
        "classification": {
            "category": document_type.name.lower(),
            "confidence": confidence,
            "model_version": "1.0.0",
            "sub_categories": None,
            "classification_date": now,
            "classifier_id": "test-classifier"
        },
        "upload_timestamp": now,
        "last_modified": now,
        "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
        "processing_status": "processed",
        "tags": {"environment": "test"},
        "custom_metadata": {"test": "true"},
        "ocr_status": "pending",
        "ocr_confidence": None,
        "page_count": 1,
        "encryption_status": "encrypted",
        "encryption_type": "AES256",
        "storage_class": "STANDARD",
        "retention_period": 365,
        "legal_hold": False
    }


def create_model_parameters(model_type: str = "svm") -> ModelParameters:
    """Create ModelParameters for testing.
    
    Args:
        model_type: Type of model ("svm" or "random_forest")
        
    Returns:
        ModelParameters instance with appropriate defaults
    """
    if model_type == "svm":
        return {
            "random_state": 42,
            "n_jobs": -1,
            "verbose": False,
            "C": 1.0,
            "kernel": "rbf",
            "gamma": "scale",
            "probability": True
        }
    elif model_type == "random_forest":
        return {
            "random_state": 42,
            "n_jobs": -1,
            "verbose": False,
            "n_estimators": 100,
            "criterion": "gini",
            "max_depth": None,
            "min_samples_split": 2,
            "min_samples_leaf": 1,
            "max_features": "sqrt",
            "bootstrap": True
        }
    else:
        raise ValueError(f"Unsupported model type: {model_type}")


# ===== Mock Classes =====

class MockClassificationModel(ClassificationModel):
    """Mock implementation of ClassificationModel protocol for testing.
    
    This class provides a predictable implementation of the ClassificationModel
    protocol that can be used in tests without requiring actual ML models.
    """
    
    def __init__(self, 
                 document_type: DocumentType = DocumentType.LOAN_APPLICATION,
                 confidence: float = 0.95,
                 parameters: Optional[Dict[str, Any]] = None):
        self.document_type = document_type
        self.confidence = confidence
        self.parameters = parameters or create_model_parameters()
        self.fitted = False
        self.predict_called = False
        self.predict_proba_called = False
        
    def fit(self, X: FeatureMatrix, y: NDArray[np.int32]) -> 'MockClassificationModel':
        """Mock implementation of fit method.
        
        Args:
            X: Feature matrix
            y: Label vector
            
        Returns:
            Self for method chaining
        """
        self.fitted = True
        self.X_train = X
        self.y_train = y
        return self
    
    def predict(self, X: FeatureMatrix) -> NDArray[np.int32]:
        """Mock implementation of predict method.
        
        Args:
            X: Feature matrix
            
        Returns:
            Predicted labels
        """
        self.predict_called = True
        self.X_test = X
        # Always predict the configured document type
        return np.array([self.document_type.value] * X.shape[0], dtype=np.int32)
    
    def predict_proba(self, X: FeatureMatrix) -> NDArray[np.float64]:
        """Mock implementation of predict_proba method.
        
        Args:
            X: Feature matrix
            
        Returns:
            Probability matrix
        """
        self.predict_proba_called = True
        self.X_test = X
        n_samples = X.shape[0]
        n_classes = len(DocumentType)
        
        # Create a probability matrix with low probabilities
        probas = np.ones((n_samples, n_classes)) * ((1.0 - self.confidence) / (n_classes - 1))
        
        # Set the target class probability to the configured confidence
        target_class_idx = self.document_type.value - 1  # Adjust for 0-indexing
        probas[:, target_class_idx] = self.confidence
        
        return probas
    
    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Mock implementation of get_params method.
        
        Args:
            deep: Whether to return parameters of nested objects
            
        Returns:
            Model parameters
        """
        return self.parameters
    
    def set_params(self, **params: Any) -> 'MockClassificationModel':
        """Mock implementation of set_params method.
        
        Args:
            **params: Parameters to set
            
        Returns:
            Self for method chaining
        """
        self.parameters.update(params)
        return self


class MockStorageOperations(StorageOperations):
    """Mock implementation of StorageOperations protocol for testing.
    
    This class provides a predictable implementation of the StorageOperations
    protocol that can be used in tests without requiring actual S3 access.
    """
    
    def __init__(self, success: bool = True, error: Optional[Dict[str, Any]] = None):
        self.success = success
        self.error = error
        self.files = {}  # In-memory storage for "uploaded" files
        self.metadata = {}  # In-memory storage for file metadata
        self.calls = []  # Track method calls
        
    def upload_file(self, local_path: Union[str, Path], storage_key: str, 
                   options: Optional[StorageOptions] = None) -> StorageResult:
        """Mock implementation of upload_file method.
        
        Args:
            local_path: Path to local file
            storage_key: Key for storage
            options: Storage options
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('upload_file', local_path, storage_key, options))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "InternalError",
                    "message": "Mock upload failure",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": True
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Simulate file upload by storing the path
        self.files[storage_key] = str(local_path)
        
        # Create metadata if not exists
        if storage_key not in self.metadata:
            self.metadata[storage_key] = {
                "content_type": options.get("content_type", "application/octet-stream") if options else "application/octet-stream",
                "metadata": options.get("metadata", {}) if options else {},
                "encryption": options.get("encryption", {"algorithm": "AES256"}) if options else {"algorithm": "AES256"}
            }
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": self.metadata[storage_key]["metadata"],
            "encryption_status": "encrypted"
        }
    
    def upload_fileobj(self, fileobj: Any, storage_key: str,
                      options: Optional[StorageOptions] = None) -> StorageResult:
        """Mock implementation of upload_fileobj method.
        
        Args:
            fileobj: File-like object
            storage_key: Key for storage
            options: Storage options
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('upload_fileobj', fileobj, storage_key, options))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "InternalError",
                    "message": "Mock upload failure",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": True
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Simulate file upload by storing the content
        content = fileobj.read() if hasattr(fileobj, 'read') else str(fileobj)
        self.files[storage_key] = content
        
        # Create metadata if not exists
        if storage_key not in self.metadata:
            self.metadata[storage_key] = {
                "content_type": options.get("content_type", "application/octet-stream") if options else "application/octet-stream",
                "metadata": options.get("metadata", {}) if options else {},
                "encryption": options.get("encryption", {"algorithm": "AES256"}) if options else {"algorithm": "AES256"}
            }
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": self.metadata[storage_key]["metadata"],
            "encryption_status": "encrypted"
        }
    
    def download_file(self, storage_key: str, local_path: Union[str, Path]) -> StorageResult:
        """Mock implementation of download_file method.
        
        Args:
            storage_key: Key for storage
            local_path: Path to save downloaded file
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('download_file', storage_key, local_path))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        if storage_key not in self.files:
            return {
                "success": False,
                "error": {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Simulate file download
        # In a real test, you might want to actually write to local_path
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": self.metadata.get(storage_key, {}).get("metadata", {}),
            "encryption_status": "encrypted"
        }
    
    def download_fileobj(self, storage_key: str, fileobj: Any) -> StorageResult:
        """Mock implementation of download_fileobj method.
        
        Args:
            storage_key: Key for storage
            fileobj: File-like object to write to
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('download_fileobj', storage_key, fileobj))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        if storage_key not in self.files:
            return {
                "success": False,
                "error": {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Simulate file download by writing to fileobj
        if hasattr(fileobj, 'write'):
            content = self.files[storage_key]
            if isinstance(content, bytes):
                fileobj.write(content)
            else:
                fileobj.write(str(content).encode('utf-8'))
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": self.metadata.get(storage_key, {}).get("metadata", {}),
            "encryption_status": "encrypted"
        }
    
    def delete_file(self, storage_key: str) -> StorageResult:
        """Mock implementation of delete_file method.
        
        Args:
            storage_key: Key for storage
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('delete_file', storage_key))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "InternalError",
                    "message": "Mock delete failure",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": True
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Remove file and metadata if exists
        if storage_key in self.files:
            del self.files[storage_key]
        
        if storage_key in self.metadata:
            del self.metadata[storage_key]
        
        return {
            "success": True,
            "error": None,
            "etag": None,
            "version_id": None,
            "storage_class": None,
            "metadata": None,
            "encryption_status": None
        }
    
    def copy_file(self, source_key: str, dest_key: str, 
                 options: Optional[StorageOptions] = None) -> StorageResult:
        """Mock implementation of copy_file method.
        
        Args:
            source_key: Source storage key
            dest_key: Destination storage key
            options: Storage options
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('copy_file', source_key, dest_key, options))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "InternalError",
                    "message": "Mock copy failure",
                    "request_id": str(uuid.uuid4()),
                    "resource": f"{source_key} -> {dest_key}",
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": True
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        if source_key not in self.files:
            return {
                "success": False,
                "error": {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": source_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Copy file and metadata
        self.files[dest_key] = self.files[source_key]
        
        if source_key in self.metadata:
            self.metadata[dest_key] = dict(self.metadata[source_key])
            # Update metadata if provided
            if options and "metadata" in options:
                self.metadata[dest_key]["metadata"] = options["metadata"]
        else:
            self.metadata[dest_key] = {
                "content_type": options.get("content_type", "application/octet-stream") if options else "application/octet-stream",
                "metadata": options.get("metadata", {}) if options else {},
                "encryption": options.get("encryption", {"algorithm": "AES256"}) if options else {"algorithm": "AES256"}
            }
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": self.metadata[dest_key]["metadata"],
            "encryption_status": "encrypted"
        }
    
    def get_metadata(self, storage_key: str) -> Union[StorageMetadata, StorageResult]:
        """Mock implementation of get_metadata method.
        
        Args:
            storage_key: Key for storage
            
        Returns:
            StorageMetadata if successful, StorageResult with error otherwise
        """
        self.calls.append(('get_metadata', storage_key))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "InternalError",
                    "message": "Mock metadata retrieval failure",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": True
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        if storage_key not in self.files:
            return {
                "success": False,
                "error": {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Create a basic metadata structure
        now = datetime.utcnow()
        document_id = storage_key.split('/')[-1].split('.')[0]
        application_id = "test-app-" + document_id[:8]
        
        return {
            "document_id": document_id,
            "application_id": application_id,
            "filename": storage_key.split('/')[-1],
            "file_size": 1024,  # Mock file size
            "content_type": self.metadata.get(storage_key, {}).get("content_type", "application/pdf"),
            "classification": {
                "category": "loan_application",
                "confidence": 0.95,
                "model_version": "1.0.0",
                "sub_categories": None,
                "classification_date": now,
                "classifier_id": "test-classifier"
            },
            "upload_timestamp": now - timedelta(hours=1),
            "last_modified": now,
            "md5_hash": "d41d8cd98f00b204e9800998ecf8427e",
            "processing_status": "processed",
            "tags": {"environment": "test"},
            "custom_metadata": self.metadata.get(storage_key, {}).get("metadata", {}),
            "ocr_status": "complete",
            "ocr_confidence": 0.9,
            "page_count": 1,
            "encryption_status": "encrypted",
            "encryption_type": "AES256",
            "storage_class": "STANDARD",
            "retention_period": 365,
            "legal_hold": False
        }
    
    def update_metadata(self, storage_key: str, metadata: Dict[str, str]) -> StorageResult:
        """Mock implementation of update_metadata method.
        
        Args:
            storage_key: Key for storage
            metadata: Metadata to update
            
        Returns:
            StorageResult with success/error information
        """
        self.calls.append(('update_metadata', storage_key, metadata))
        
        if not self.success:
            return {
                "success": False,
                "error": self.error or {
                    "code": "InternalError",
                    "message": "Mock metadata update failure",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": True
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        if storage_key not in self.files:
            return {
                "success": False,
                "error": {
                    "code": "NoSuchKey",
                    "message": "The specified key does not exist",
                    "request_id": str(uuid.uuid4()),
                    "resource": storage_key,
                    "details": None,
                    "timestamp": datetime.utcnow(),
                    "recoverable": False
                },
                "etag": None,
                "version_id": None,
                "storage_class": None,
                "metadata": None,
                "encryption_status": None
            }
        
        # Update metadata
        if storage_key not in self.metadata:
            self.metadata[storage_key] = {
                "content_type": "application/octet-stream",
                "metadata": {},
                "encryption": {"algorithm": "AES256"}
            }
        
        self.metadata[storage_key]["metadata"] = metadata
        
        return {
            "success": True,
            "error": None,
            "etag": f"\"{uuid.uuid4()}\"",
            "version_id": str(uuid.uuid4()),
            "storage_class": "STANDARD",
            "metadata": metadata,
            "encryption_status": "encrypted"
        }
    
    def generate_presigned_url(self, storage_key: str, expiration: int = 3600) -> str:
        """Mock implementation of generate_presigned_url method.
        
        Args:
            storage_key: Key for storage
            expiration: URL expiration time in seconds
            
        Returns:
            A mock presigned URL
        """
        self.calls.append(('generate_presigned_url', storage_key, expiration))
        
        if not self.success:
            raise Exception("Failed to generate presigned URL")
        
        if storage_key not in self.files:
            raise Exception(f"The specified key does not exist: {storage_key}")
        
        # Generate a mock presigned URL
        expiry_time = int((datetime.utcnow() + timedelta(seconds=expiration)).timestamp())
        return f"https://mock-s3-bucket.example.com/{storage_key}?X-Amz-Expires={expiration}&X-Amz-Date={expiry_time}"


# ===== Pytest Fixtures =====

@pytest.fixture
def temp_dir() -> Iterator[Path]:
    """Create a temporary directory for test files.
    
    Yields:
        Path to the temporary directory
    """
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_document_path(temp_dir: Path) -> Path:
    """Create a sample document file for testing.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Path to the sample document file
    """
    document_path = temp_dir / "sample_document.pdf"
    # Create a dummy PDF file (just a text file with .pdf extension)
    with open(document_path, 'wb') as f:
        f.write(b'%PDF-1.5\n%Mock PDF content for testing')
    return document_path


@pytest.fixture
def mock_classification_model() -> MockClassificationModel:
    """Create a mock classification model for testing.
    
    Returns:
        MockClassificationModel instance
    """
    return MockClassificationModel()


@pytest.fixture
def mock_storage_operations() -> MockStorageOperations:
    """Create a mock storage operations implementation for testing.
    
    Returns:
        MockStorageOperations instance
    """
    return MockStorageOperations()


@pytest.fixture
def classification_result_high_confidence() -> ClassificationResult:
    """Create a classification result with high confidence.
    
    Returns:
        ClassificationResult instance with high confidence
    """
    return create_classification_result(
        document_type=DocumentType.LOAN_APPLICATION,
        confidence=TEST_CONFIDENCE_THRESHOLDS["high"],
        needs_review=False,
        processing_time_ms=150.5
    )


@pytest.fixture
def classification_result_low_confidence() -> ClassificationResult:
    """Create a classification result with low confidence that needs review.
    
    Returns:
        ClassificationResult instance with low confidence
    """
    return create_classification_result(
        document_type=DocumentType.TAX_RETURN,
        confidence=TEST_CONFIDENCE_THRESHOLDS["low"] - 0.05,
        needs_review=True,
        processing_time_ms=200.3
    )


@pytest.fixture
def storage_metadata_loan_application() -> StorageMetadata:
    """Create storage metadata for a loan application document.
    
    Returns:
        StorageMetadata instance for a loan application
    """
    return create_storage_metadata(
        document_id=str(uuid.uuid4()),
        application_id="APP-" + str(uuid.uuid4())[:8],
        document_type=DocumentType.LOAN_APPLICATION,
        confidence=0.95
    )


@pytest.fixture
def storage_metadata_tax_return() -> StorageMetadata:
    """Create storage metadata for a tax return document.
    
    Returns:
        StorageMetadata instance for a tax return
    """
    return create_storage_metadata(
        document_id=str(uuid.uuid4()),
        application_id="APP-" + str(uuid.uuid4())[:8],
        document_type=DocumentType.TAX_RETURN,
        confidence=0.88
    )


@pytest.fixture
def feature_vector() -> FeatureVector:
    """Create a feature vector for testing.
    
    Returns:
        Random feature vector
    """
    return generate_random_feature_vector()


@pytest.fixture
def feature_matrix() -> FeatureMatrix:
    """Create a feature matrix for testing.
    
    Returns:
        Random feature matrix
    """
    return generate_random_feature_matrix()


@pytest.fixture
def model_parameters_svm() -> ModelParameters:
    """Create SVM model parameters for testing.
    
    Returns:
        ModelParameters for SVM
    """
    return create_model_parameters("svm")


@pytest.fixture
def model_parameters_random_forest() -> ModelParameters:
    """Create Random Forest model parameters for testing.
    
    Returns:
        ModelParameters for Random Forest
    """
    return create_model_parameters("random_forest")


@pytest.fixture
def s3_client_config() -> S3ClientConfig:
    """Create S3 client configuration for testing.
    
    Returns:
        S3ClientConfig instance
    """
    return {
        "endpoint_url": "https://s3.amazonaws.com",
        "region_name": "us-east-1",
        "credentials": {
            "access_key": "test-access-key",
            "secret_key": "test-secret-key",
            "session_token": None
        },
        "verify": True
    }


@pytest.fixture
def storage_options() -> StorageOptions:
    """Create storage options for testing.
    
    Returns:
        StorageOptions instance
    """
    return {
        "encryption": {
            "algorithm": "AES256",
            "kms_key_id": None
        },
        "content_type": "application/pdf",
        "metadata": {
            "application-id": "test-app-123",
            "document-type": "loan_application"
        },
        "acl": "private",
        "storage_class": "STANDARD"
    }


@pytest.fixture
def service_config() -> ServiceConfig:
    """Create service configuration for testing.
    
    Returns:
        ServiceConfig instance
    """
    return {
        "name": "document-service",
        "version": "1.0.0",
        "environment": "development",
        "host": "0.0.0.0",
        "port": 8000,
        "debug": True,
        "api_prefix": "/api/v1",
        "allowed_origins": ["http://localhost:3000"]
    }


@pytest.fixture
def model_config() -> ModelConfig:
    """Create model configuration for testing.
    
    Returns:
        ModelConfig instance
    """
    return {
        "model_path": "/models/document_classifier.pkl",
        "vectorizer_path": "/models/document_vectorizer.pkl",
        "min_confidence_threshold": 0.75,
        "supported_document_types": [dt.name.lower() for dt in DocumentType],
        "batch_size": 32,
        "max_document_size_mb": 10,
        "gpu_acceleration": False,
        "memory_limit_mb": 16384  # 16GB as per spec
    }


@pytest.fixture
def rabbitmq_config() -> RabbitMQConfig:
    """Create RabbitMQ configuration for testing.
    
    Returns:
        RabbitMQConfig instance
    """
    return {
        "host": "localhost",
        "port": 5672,
        "username": "guest",
        "password": "guest",
        "vhost": "/",
        "exchange": "mca.documents",
        "queue_document_processing": "document-processing",
        "queue_data_extraction": "data-extraction",
        "routing_key": "document.classify",
        "ssl": False,
        "ssl_cert_path": None,
        "ssl_key_path": None,
        "ssl_ca_certs": None,
        "heartbeat": 60,
        "connection_timeout": 30,
        "prefetch_count": 10
    }


@pytest.fixture
def s3_config() -> S3Config:
    """Create S3 configuration for testing.
    
    Returns:
        S3Config instance
    """
    return {
        "endpoint_url": "https://s3.amazonaws.com",
        "region_name": "us-east-1",
        "access_key_id": "test-access-key",
        "secret_access_key": "test-secret-key",
        "bucket_name": "mca-documents-development",
        "use_ssl": True,
        "verify": True,
        "encryption": "AES256",
        "presigned_url_expiration": 3600,
        "max_pool_connections": 10
    }


@pytest.fixture
def logging_config() -> LoggingConfig:
    """Create logging configuration for testing.
    
    Returns:
        LoggingConfig instance
    """
    return {
        "level": "DEBUG",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "date_format": "%Y-%m-%d %H:%M:%S",
        "file_path": None,
        "max_bytes": 10485760,  # 10MB
        "backup_count": 5,
        "json_format": True,
        "include_correlation_id": True
    }


@pytest.fixture
def app_config(service_config: ServiceConfig, model_config: ModelConfig,
              rabbitmq_config: RabbitMQConfig, s3_config: S3Config,
              logging_config: LoggingConfig) -> AppConfig:
    """Create complete application configuration for testing.
    
    Args:
        service_config: Service configuration fixture
        model_config: Model configuration fixture
        rabbitmq_config: RabbitMQ configuration fixture
        s3_config: S3 configuration fixture
        logging_config: Logging configuration fixture
        
    Returns:
        AppConfig instance
    """
    return {
        "service": service_config,
        "model": model_config,
        "rabbitmq": rabbitmq_config,
        "s3": s3_config,
        "logging": logging_config
    }


# ===== Test Utility Functions =====

def assert_valid_classification_result(result: ClassificationResult) -> None:
    """Assert that a classification result is valid.
    
    Args:
        result: ClassificationResult to validate
        
    Raises:
        AssertionError: If the classification result is invalid
    """
    assert isinstance(result, ClassificationResult), "Result must be a ClassificationResult instance"
    assert isinstance(result.document_type, DocumentType), "document_type must be a DocumentType enum"
    assert isinstance(result.confidence, float), "confidence must be a float"
    assert 0.0 <= result.confidence <= 1.0, "confidence must be between 0.0 and 1.0"
    assert isinstance(result.probabilities, dict), "probabilities must be a dictionary"
    assert all(isinstance(k, DocumentType) for k in result.probabilities.keys()), "probability keys must be DocumentType enums"
    assert all(isinstance(v, float) and 0.0 <= v <= 1.0 for v in result.probabilities.values()), "probability values must be floats between 0.0 and 1.0"
    assert abs(sum(result.probabilities.values()) - 1.0) < 1e-6, "probabilities must sum to 1.0"
    assert isinstance(result.needs_review, bool), "needs_review must be a boolean"
    
    if result.feature_importance is not None:
        assert isinstance(result.feature_importance, dict), "feature_importance must be a dictionary"
        assert all(isinstance(k, str) for k in result.feature_importance.keys()), "feature_importance keys must be strings"
        assert all(isinstance(v, float) for v in result.feature_importance.values()), "feature_importance values must be floats"
    
    if result.processing_time_ms is not None:
        assert isinstance(result.processing_time_ms, float), "processing_time_ms must be a float"
        assert result.processing_time_ms >= 0.0, "processing_time_ms must be non-negative"


def assert_valid_storage_result(result: StorageResult) -> None:
    """Assert that a storage result is valid.
    
    Args:
        result: StorageResult to validate
        
    Raises:
        AssertionError: If the storage result is invalid
    """
    assert isinstance(result, dict), "Result must be a dictionary"
    assert "success" in result, "Result must have a 'success' key"
    assert isinstance(result["success"], bool), "'success' must be a boolean"
    
    if result["success"]:
        assert result["error"] is None, "'error' must be None for successful operations"
    else:
        assert "error" in result, "Failed result must have an 'error' key"
        assert isinstance(result["error"], dict), "'error' must be a dictionary"
        assert "code" in result["error"], "Error must have a 'code' key"
        assert "message" in result["error"], "Error must have a 'message' key"
        assert "timestamp" in result["error"], "Error must have a 'timestamp' key"
        assert "recoverable" in result["error"], "Error must have a 'recoverable' key"


def assert_valid_storage_metadata(metadata: StorageMetadata) -> None:
    """Assert that storage metadata is valid.
    
    Args:
        metadata: StorageMetadata to validate
        
    Raises:
        AssertionError: If the storage metadata is invalid
    """
    assert isinstance(metadata, dict), "Metadata must be a dictionary"
    assert "document_id" in metadata, "Metadata must have a 'document_id' key"
    assert "application_id" in metadata, "Metadata must have an 'application_id' key"
    assert "filename" in metadata, "Metadata must have a 'filename' key"
    assert "file_size" in metadata, "Metadata must have a 'file_size' key"
    assert "content_type" in metadata, "Metadata must have a 'content_type' key"
    assert "classification" in metadata, "Metadata must have a 'classification' key"
    assert "upload_timestamp" in metadata, "Metadata must have an 'upload_timestamp' key"
    assert "last_modified" in metadata, "Metadata must have a 'last_modified' key"
    assert "encryption_status" in metadata, "Metadata must have an 'encryption_status' key"
    assert "encryption_type" in metadata, "Metadata must have an 'encryption_type' key"
    
    # Validate classification
    classification = metadata["classification"]
    assert isinstance(classification, dict), "Classification must be a dictionary"
    assert "category" in classification, "Classification must have a 'category' key"
    assert "confidence" in classification, "Classification must have a 'confidence' key"
    assert "model_version" in classification, "Classification must have a 'model_version' key"
    assert "classification_date" in classification, "Classification must have a 'classification_date' key"
    assert isinstance(classification["confidence"], float), "Confidence must be a float"
    assert 0.0 <= classification["confidence"] <= 1.0, "Confidence must be between 0.0 and 1.0"


def assert_valid_config(config: AppConfig) -> None:
    """Assert that application configuration is valid.
    
    Args:
        config: AppConfig to validate
        
    Raises:
        AssertionError: If the configuration is invalid
    """
    assert isinstance(config, dict), "Config must be a dictionary"
    assert "service" in config, "Config must have a 'service' key"
    assert "model" in config, "Config must have a 'model' key"
    assert "rabbitmq" in config, "Config must have a 'rabbitmq' key"
    assert "s3" in config, "Config must have an 's3' key"
    assert "logging" in config, "Config must have a 'logging' key"
    
    # Validate service config
    service = config["service"]
    assert isinstance(service, dict), "Service config must be a dictionary"
    assert "name" in service, "Service config must have a 'name' key"
    assert "version" in service, "Service config must have a 'version' key"
    assert "environment" in service, "Service config must have an 'environment' key"
    assert service["environment"] in ["development", "staging", "production"], "Environment must be one of 'development', 'staging', or 'production'"
    
    # Validate model config
    model = config["model"]
    assert isinstance(model, dict), "Model config must be a dictionary"
    assert "min_confidence_threshold" in model, "Model config must have a 'min_confidence_threshold' key"
    assert 0.0 <= model["min_confidence_threshold"] <= 1.0, "Confidence threshold must be between 0.0 and 1.0"
    assert "memory_limit_mb" in model, "Model config must have a 'memory_limit_mb' key"
    assert model["memory_limit_mb"] >= 16384, "Memory limit must be at least 16GB (16384MB) as per spec"
    
    # Validate S3 config
    s3 = config["s3"]
    assert isinstance(s3, dict), "S3 config must be a dictionary"
    assert "encryption" in s3, "S3 config must have an 'encryption' key"
    assert s3["encryption"] == "AES256", "S3 encryption must be 'AES256' as per spec"