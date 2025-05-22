# -*- coding: utf-8 -*-
"""
Document Service - Integration Tests Package

This package contains integration tests for the Document Service, verifying that
components work together correctly in realistic scenarios. These tests validate
the end-to-end document processing flow, API functionality, classification accuracy,
and integration with external services like RabbitMQ and S3 storage.

The integration tests ensure that the Document Service meets the requirements
specified in the technical specification, including:
- 99% document classification accuracy
- Proper message handling through RabbitMQ
- Secure document storage with AES-256 encryption in S3
- Correct routing of documents to OCR processors
- API contract compliance and error handling

Version: 1.0.0
"""

import os
import sys
import json
import logging
import pytest
from typing import Dict, List, Any, Optional, Tuple, Union, Callable

# Configure logging for integration tests
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Package version
__version__ = '1.0.0'

# Constants for integration test configuration
INTEGRATION_TEST_TIMEOUT = 30  # seconds
MAX_RETRY_ATTEMPTS = 3
DEFAULT_WAIT_TIME = 5  # seconds

# Document types for testing
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

# Classification confidence thresholds
CONFIDENCE_THRESHOLDS = {
    'high': 0.9,
    'medium': 0.7,
    'low': 0.5,
    'minimum': 0.3
}

# RabbitMQ test configuration
RABBITMQ_TEST_CONFIG = {
    'exchange': 'mca.documents.test',
    'queue_in': 'document-processing-test',
    'queue_out': 'data-extraction-test',
    'routing_key': 'document.classify'
}

# S3 test configuration
S3_TEST_CONFIG = {
    'bucket': 'mca-documents-test',
    'prefix': 'integration-tests/',
    'encryption': 'AES256'
}


def create_test_document_message(application_id: str, document_id: str, 
                               document_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a test document message for integration testing.
    
    Args:
        application_id: ID of the application this document belongs to
        document_id: Unique identifier for the document
        document_type: Optional pre-classified document type
        
    Returns:
        Dict containing document message data for testing
    """
    doc_type = document_type or 'unknown'
    storage_path = f'applications/{application_id}/documents/{document_id}.pdf'
    
    return {
        'application_id': application_id,
        'document_id': document_id,
        'document_type': doc_type,
        'storage_path': storage_path,
        'timestamp': '2023-01-01T00:00:00Z',
        'retry_count': 0,
        'metadata': {
            'source': 'email',
            'filename': f'document_{document_id}.pdf',
            'content_type': 'application/pdf'
        }
    }


def create_test_classification_result(document_id: str, document_type: str, 
                                    confidence: float, application_id: str) -> Dict[str, Any]:
    """
    Create a test classification result for integration testing.
    
    Args:
        document_id: Unique identifier for the document
        document_type: Classified document type
        confidence: Classification confidence score (0.0-1.0)
        application_id: ID of the application this document belongs to
        
    Returns:
        Dict containing classification result data for testing
    """
    storage_path = f'applications/{application_id}/documents/{document_id}.pdf'
    
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
        'storage_path': storage_path,
        'processing': {
            'duration_ms': 250,
            'timestamp': '2023-01-01T00:00:05Z',
            'version': __version__
        },
        'routing': {
            'destination': 'ocr_service',
            'queue': 'data-extraction',
            'priority': 'normal'
        }
    }


def setup_integration_test_environment() -> None:
    """
    Set up the environment for integration testing.
    
    This function ensures that the necessary paths are added to sys.path,
    required environment variables are set, and test services are configured.
    """
    # Add the src directory to the Python path if needed
    src_dir = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'src'))
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)
    
    # Set environment variables for integration testing
    os.environ.setdefault('DOCUMENT_SERVICE_ENV', 'test')
    os.environ.setdefault('RABBITMQ_HOST', 'localhost')
    os.environ.setdefault('RABBITMQ_PORT', '5672')
    os.environ.setdefault('RABBITMQ_EXCHANGE', RABBITMQ_TEST_CONFIG['exchange'])
    os.environ.setdefault('RABBITMQ_QUEUE_IN', RABBITMQ_TEST_CONFIG['queue_in'])
    os.environ.setdefault('RABBITMQ_QUEUE_OUT', RABBITMQ_TEST_CONFIG['queue_out'])
    os.environ.setdefault('S3_ENDPOINT', 'http://localhost:9000')
    os.environ.setdefault('S3_BUCKET', S3_TEST_CONFIG['bucket'])
    os.environ.setdefault('MODEL_PATH', './tests/test_models')
    os.environ.setdefault('LOG_LEVEL', 'INFO')
    
    logger.info('Integration test environment setup complete')


def teardown_integration_test_environment() -> None:
    """
    Clean up the integration test environment after tests are complete.
    
    This function restores original environment variables and performs
    any necessary cleanup of test resources.
    """
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
    
    logger.info('Integration test environment teardown complete')


# Initialize the integration test environment when the package is imported
setup_integration_test_environment()

# Register teardown to run when the Python interpreter exits
import atexit
atexit.register(teardown_integration_test_environment)