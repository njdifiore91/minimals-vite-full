# OCR Service Test Utilities Package
# Version: 1.0.0
# Python 3.9+ Required
"""
OCR Service Test Utilities

This package contains test utilities and fixtures for testing the OCR Service utility functions.
It makes the test_utils directory a proper Python package, enabling proper imports between
test modules and ensuring test discovery by pytest.

The test modules in this package validate the functionality of utility modules including:

- time_utils: Date and time utilities
- file_utils: File handling utilities
- security_utils: Security utilities for encryption
- retry_utils: Retry logic with exponential backoff
- validation_utils: Validation utilities for documents
- error_utils: Standardized error handling
- logging_utils: Structured logging utilities
- rabbitmq_utils: RabbitMQ integration utilities
- s3_utils: S3-compatible storage utilities
- text_utils: Post-OCR text processing utilities
- image_utils: Image preprocessing utilities
- tensorflow_utils: TensorFlow model utilities

This package follows Python testing best practices and is designed to work with pytest.
"""

# Version information
__version__ = '1.0.0'
__test_package__ = True