# -*- coding: utf-8 -*-
"""
Test Services Package

This package contains tests for the Document Service's service components.
It enables test discovery and provides shared utilities for service testing.

The Document Service classifies incoming documents using scikit-learn models
and routes them to appropriate OCR processors based on document type and
confidence scores.
"""

import os
import json
import pytest
from unittest.mock import MagicMock, patch
from typing import Dict, List, Any, Tuple, Optional

# Test constants for document classification
DOCUMENT_TYPES = [
    "invoice",
    "bank_statement",
    "tax_return",
    "identity_document",
    "business_license",
    "utility_bill",
    "financial_statement",
    "application_form"
]

# Confidence thresholds for classification and routing
HIGH_CONFIDENCE_THRESHOLD = 0.9
MEDIUM_CONFIDENCE_THRESHOLD = 0.7
LOW_CONFIDENCE_THRESHOLD = 0.5

# Test message templates
def create_test_document_message(document_id: str, document_path: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a test message simulating a document received from the Email Service.
    
    Args:
        document_id: Unique identifier for the document
        document_path: S3 path to the document
        metadata: Optional metadata about the document
        
    Returns:
        Dict containing a properly formatted document message
    """
    return {
        "document_id": document_id,
        "document_path": document_path,
        "received_at": "2025-05-23T10:15:30Z",
        "metadata": metadata or {
            "source": "email",
            "email_id": f"email_{document_id}",
            "sender": "test@example.com",
            "subject": "Test Document Submission",
            "received_timestamp": "2025-05-23T10:15:30Z"
        },
        "processing_status": "received"
    }

def create_classification_result(document_id: str, document_type: str, confidence: float, 
                                 metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a test classification result simulating output from the classification service.
    
    Args:
        document_id: Unique identifier for the document
        document_type: Classified document type
        confidence: Classification confidence score (0.0-1.0)
        metadata: Optional additional metadata
        
    Returns:
        Dict containing a properly formatted classification result
    """
    return {
        "document_id": document_id,
        "document_type": document_type,
        "confidence": confidence,
        "classification_timestamp": "2025-05-23T10:15:35Z",
        "metadata": metadata or {
            "page_count": 2,
            "file_size_bytes": 1024 * 1024,
            "file_type": "application/pdf",
            "alternative_classifications": [
                {"type": "invoice", "confidence": confidence - 0.15},
                {"type": "application_form", "confidence": confidence - 0.25}
            ]
        },
        "processing_status": "classified"
    }

# Utility functions for test data generation
def generate_test_documents(count: int = 5) -> List[Dict[str, Any]]:
    """
    Generate a list of test document messages.
    
    Args:
        count: Number of test documents to generate
        
    Returns:
        List of document message dictionaries
    """
    documents = []
    for i in range(count):
        doc_id = f"doc_{i+1}"
        doc_path = f"s3://mca-documents-staging/incoming/{doc_id}.pdf"
        documents.append(create_test_document_message(doc_id, doc_path))
    return documents

def generate_mixed_confidence_classifications(documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generate classification results with mixed confidence levels for a list of documents.
    
    Args:
        documents: List of document messages to classify
        
    Returns:
        List of classification result dictionaries with varying confidence levels
    """
    import random
    results = []
    
    for i, doc in enumerate(documents):
        # Assign different confidence levels and document types
        confidence_level = random.choice([0.95, 0.85, 0.75, 0.65, 0.55])
        doc_type = random.choice(DOCUMENT_TYPES)
        
        results.append(create_classification_result(
            doc["document_id"], 
            doc_type,
            confidence_level
        ))
    
    return results

# Test environment setup/teardown helpers
def setup_test_environment():
    """
    Set up the test environment with required environment variables.
    This is useful for integration tests that need specific configuration.
    """
    os.environ["DOCUMENT_SERVICE_ENV"] = "test"
    os.environ["RABBITMQ_HOST"] = "localhost"
    os.environ["RABBITMQ_PORT"] = "5672"
    os.environ["RABBITMQ_USERNAME"] = "guest"
    os.environ["RABBITMQ_PASSWORD"] = "guest"
    os.environ["RABBITMQ_EXCHANGE"] = "mca.documents.test"
    os.environ["S3_ENDPOINT"] = "http://localhost:9000"
    os.environ["S3_ACCESS_KEY"] = "minioadmin"
    os.environ["S3_SECRET_KEY"] = "minioadmin"
    os.environ["S3_BUCKET_NAME"] = "mca-documents-test"
    os.environ["CLASSIFICATION_CONFIDENCE_THRESHOLD"] = str(HIGH_CONFIDENCE_THRESHOLD)

def teardown_test_environment():
    """
    Clean up the test environment after tests complete.
    """
    test_env_vars = [
        "DOCUMENT_SERVICE_ENV",
        "RABBITMQ_HOST",
        "RABBITMQ_PORT",
        "RABBITMQ_USERNAME",
        "RABBITMQ_PASSWORD",
        "RABBITMQ_EXCHANGE",
        "S3_ENDPOINT",
        "S3_ACCESS_KEY",
        "S3_SECRET_KEY",
        "S3_BUCKET_NAME",
        "CLASSIFICATION_CONFIDENCE_THRESHOLD"
    ]
    
    for var in test_env_vars:
        if var in os.environ:
            del os.environ[var]