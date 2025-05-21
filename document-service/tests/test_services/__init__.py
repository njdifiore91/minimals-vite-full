# Document Service - Test Services Module
# This module contains tests for the core service components of the Document Service.
# It provides shared fixtures, utilities, and constants for testing service functionality.

import os
import json
import pytest
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# Configure logging for tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Common test constants
TEST_DOCUMENT_TYPES = [
    'application_form',
    'bank_statement',
    'tax_return',
    'identity_document',
    'business_license',
    'financial_statement',
    'invoice',
    'utility_bill'
]

TEST_CONFIDENCE_THRESHOLDS = {
    'high': 0.9,
    'medium': 0.7,
    'low': 0.5,
    'minimum': 0.3
}

# Utility functions for creating test data
def create_test_document_metadata(
    document_id: str,
    document_type: str,
    confidence: float,
    page_count: int = 1,
    file_type: str = 'pdf'
) -> Dict[str, Any]:
    """
    Create test document metadata for use in tests.
    
    Args:
        document_id: Unique identifier for the document
        document_type: Type of document (from TEST_DOCUMENT_TYPES)
        confidence: Classification confidence score (0.0-1.0)
        page_count: Number of pages in the document
        file_type: File extension/type of the document
        
    Returns:
        Dict containing document metadata
    """
    return {
        'id': document_id,
        'type': document_type,
        'classification': {
            'document_type': document_type,
            'confidence': confidence,
            'alternatives': [
                {
                    'document_type': alt_type,
                    'confidence': max(0.0, confidence - (0.1 * (i + 1)))
                }
                for i, alt_type in enumerate(
                    [t for t in TEST_DOCUMENT_TYPES[:3] if t != document_type]
                )
            ]
        },
        'metadata': {
            'page_count': page_count,
            'file_type': file_type,
            'file_size': page_count * 100 * 1024,  # Approximate size based on pages
            'created_at': '2023-01-01T00:00:00Z',
            'processed_at': '2023-01-01T00:00:05Z'
        },
        'storage_path': f'test-documents/{document_type}/{document_id}.{file_type}'
    }

def create_test_queue_message(
    application_id: str,
    document_id: str,
    document_type: Optional[str] = None,
    storage_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a test message for the document processing queue.
    
    Args:
        application_id: ID of the application this document belongs to
        document_id: Unique identifier for the document
        document_type: Optional pre-classified document type
        storage_path: Optional storage path override
        
    Returns:
        Dict containing queue message data
    """
    doc_type = document_type or 'unknown'
    path = storage_path or f'applications/{application_id}/documents/{document_id}.pdf'
    
    return {
        'application_id': application_id,
        'document_id': document_id,
        'document_type': doc_type,
        'storage_path': path,
        'timestamp': '2023-01-01T00:00:00Z',
        'retry_count': 0,
        'metadata': {
            'source': 'email',
            'filename': f'document_{document_id}.pdf',
            'content_type': 'application/pdf'
        }
    }

def create_test_classification_result(
    document_id: str,
    document_type: str,
    confidence: float,
    application_id: str,
    storage_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a test classification result for a document.
    
    Args:
        document_id: Unique identifier for the document
        document_type: Classified document type
        confidence: Classification confidence score (0.0-1.0)
        application_id: ID of the application this document belongs to
        storage_path: Optional storage path override
        
    Returns:
        Dict containing classification result data
    """
    path = storage_path or f'applications/{application_id}/documents/{document_id}.pdf'
    
    return {
        'document_id': document_id,
        'application_id': application_id,
        'classification': {
            'document_type': document_type,
            'confidence': confidence,
            'alternatives': [
                {
                    'document_type': alt_type,
                    'confidence': max(0.0, confidence - (0.1 * (i + 1)))
                }
                for i, alt_type in enumerate(
                    [t for t in TEST_DOCUMENT_TYPES[:3] if t != document_type]
                )
            ]
        },
        'storage_path': path,
        'processing': {
            'duration_ms': 250,
            'timestamp': '2023-01-01T00:00:05Z',
            'version': '1.0.0'
        },
        'routing': {
            'destination': 'ocr_service',
            'queue': 'data-extraction',
            'priority': 'normal'
        }
    }

# Shared test setup and teardown functions
def setup_test_environment():
    """Set up the test environment with required variables and configurations."""
    # Ensure test environment variables are set
    os.environ.setdefault('RABBITMQ_HOST', 'localhost')
    os.environ.setdefault('RABBITMQ_PORT', '5672')
    os.environ.setdefault('RABBITMQ_EXCHANGE', 'mca.documents.test')
    os.environ.setdefault('RABBITMQ_QUEUE_IN', 'document-processing-test')
    os.environ.setdefault('RABBITMQ_QUEUE_OUT', 'data-extraction-test')
    os.environ.setdefault('S3_ENDPOINT', 'http://localhost:9000')
    os.environ.setdefault('S3_BUCKET', 'mca-documents-test')
    os.environ.setdefault('MODEL_PATH', './tests/test_models')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    logger.info('Test environment setup complete')

def teardown_test_environment():
    """Clean up the test environment after tests are complete."""
    # Clean up any test-specific environment variables if needed
    test_vars = [
        'RABBITMQ_HOST', 'RABBITMQ_PORT', 'RABBITMQ_EXCHANGE',
        'RABBITMQ_QUEUE_IN', 'RABBITMQ_QUEUE_OUT',
        'S3_ENDPOINT', 'S3_BUCKET', 'MODEL_PATH'
    ]
    
    for var in test_vars:
        if f'{var}_ORIGINAL' in os.environ:
            # Restore original value if it was backed up
            original_value = os.environ.pop(f'{var}_ORIGINAL')
            if original_value:
                os.environ[var] = original_value
            else:
                os.environ.pop(var, None)
    
    logger.info('Test environment teardown complete')

# Run setup when the module is imported
setup_test_environment()

# Register teardown to run when the Python interpreter exits
import atexit
atexit.register(teardown_test_environment)