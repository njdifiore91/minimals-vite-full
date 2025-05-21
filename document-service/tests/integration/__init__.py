#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Document Service Integration Tests Package

This package contains integration tests for the Document Service, which is responsible
for classifying documents using scikit-learn models (SVM, Random Forest) and routing
them to appropriate OCR processors.

Integration tests verify that components work together correctly in realistic scenarios,
including:
- RabbitMQ message consumption and publishing
- S3 storage operations with encryption
- Document classification with ML models
- API endpoints and responses
- End-to-end document processing flows

These tests ensure the Document Service meets the requirements specified in the
Merchant Cash Advance (MCA) Application Processing System technical specification.
"""

__version__ = '0.1.0'
__author__ = 'Dollar Funding Engineering Team'
__maintainer__ = 'Dollar Funding Engineering Team'
__email__ = 'engineering@dollarfunding.com'
__status__ = 'Development'

# Make commonly used test utilities available at the package level
from pathlib import Path

# Define the integration tests directory for easy access to test resources
INTEGRATION_TESTS_DIR = Path(__file__).parent.absolute()

# Define test constants that may be used across multiple test modules
TEST_EXCHANGE = 'mca.documents.test'
TEST_QUEUE = 'document-processing-test'
TEST_BUCKET = 'mca-documents-test'

# Import common test utilities if needed by multiple test modules
# This allows other test modules to import from tests.integration directly