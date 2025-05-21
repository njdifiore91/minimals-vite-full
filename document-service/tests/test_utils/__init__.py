# -*- coding: utf-8 -*-
"""
Document Service Test Utilities Package

This package provides a comprehensive set of test utilities for the Document Service,
including test fixtures, mocks, factory functions, and helper methods to facilitate
testing of all components of the Document Service.

The test utilities are designed to work with pytest and support both unit and integration
testing approaches. They provide consistent mocking of external dependencies like S3,
RabbitMQ, and machine learning models to ensure tests are reliable and deterministic.

Example:
    from document_service.tests.test_utils import (
        create_test_document,
        mock_s3_client,
        mock_rabbitmq_connection,
        mock_classification_model
    )

    def test_document_processing():
        # Create a test document using the factory function
        test_doc = create_test_document(doc_type='invoice')
        
        # Use the mocked S3 client for testing
        with mock_s3_client() as s3:
            # Test document upload functionality
            result = upload_document(test_doc, s3)
            assert result['status'] == 'success'
"""

__version__ = '1.0.0'

# Import pytest fixtures and configuration
from .conftest import (
    # S3 mocks and fixtures
    mock_s3_client,
    mock_s3_upload,
    mock_s3_download,
    
    # RabbitMQ mocks and fixtures
    mock_rabbitmq_connection,
    mock_rabbitmq_channel,
    mock_rabbitmq_publish,
    mock_rabbitmq_consume,
    
    # ML model mocks and fixtures
    mock_classification_model,
    mock_feature_extraction,
    mock_confidence_scoring,
    
    # Test data factories
    create_test_document,
    create_test_message,
    create_test_application,
    
    # Test environment setup/teardown
    setup_test_environment,
    teardown_test_environment,
    
    # Test helpers
    assert_document_metadata,
    assert_message_structure,
    assert_classification_result,
    assert_processing_time,
    
    # Path fixtures
    test_data_path,
    test_models_path,
    test_configs_path
)

# Import test helper functions
from .test_helpers import (
    # Document testing helpers
    create_document_bytes,
    create_document_file,
    get_test_document_path,
    compare_document_content,
    
    # Message testing helpers
    create_message_payload,
    verify_message_format,
    simulate_message_processing,
    
    # Mock response generators
    generate_mock_s3_response,
    generate_mock_rabbitmq_response,
    generate_mock_classification_response,
    
    # Assertion helpers
    assert_logs_contain,
    assert_error_handled,
    assert_retry_attempted,
    assert_security_applied
)

# Define __all__ to explicitly specify what is exported
__all__ = [
    # Version
    '__version__',
    
    # S3 mocks and fixtures
    'mock_s3_client',
    'mock_s3_upload',
    'mock_s3_download',
    
    # RabbitMQ mocks and fixtures
    'mock_rabbitmq_connection',
    'mock_rabbitmq_channel',
    'mock_rabbitmq_publish',
    'mock_rabbitmq_consume',
    
    # ML model mocks and fixtures
    'mock_classification_model',
    'mock_feature_extraction',
    'mock_confidence_scoring',
    
    # Test data factories
    'create_test_document',
    'create_test_message',
    'create_test_application',
    
    # Test environment setup/teardown
    'setup_test_environment',
    'teardown_test_environment',
    
    # Test helpers
    'assert_document_metadata',
    'assert_message_structure',
    'assert_classification_result',
    'assert_processing_time',
    
    # Path fixtures
    'test_data_path',
    'test_models_path',
    'test_configs_path',
    
    # Document testing helpers
    'create_document_bytes',
    'create_document_file',
    'get_test_document_path',
    'compare_document_content',
    
    # Message testing helpers
    'create_message_payload',
    'verify_message_format',
    'simulate_message_processing',
    
    # Mock response generators
    'generate_mock_s3_response',
    'generate_mock_rabbitmq_response',
    'generate_mock_classification_response',
    
    # Assertion helpers
    'assert_logs_contain',
    'assert_error_handled',
    'assert_retry_attempted',
    'assert_security_applied'
]