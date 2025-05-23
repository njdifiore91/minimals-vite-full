#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service Integration Test Package

This package contains integration tests for the OCR Service of the Merchant Cash Advance (MCA)
Application Processing System. It validates the interaction between different components of the
OCR Service and its integration with external systems like RabbitMQ and S3-compatible storage.

The integration tests verify that:
- The OCR Service correctly processes documents from RabbitMQ queues
- Extracted data is properly formatted and published to the appropriate queues
- Documents are correctly stored and retrieved from S3-compatible storage
- The service integrates properly with the Document Service for classification
- The service maintains 99% data extraction accuracy in an integrated environment
- Processing time meets the under 5 minutes requirement from receipt to completion

This package follows Python testing best practices and is designed to work with pytest.
It makes the test directory a proper Python package, enabling proper imports between
test modules and ensuring test discovery by pytest.
"""

# Version information
__version__ = '1.0.0'
__author__ = 'Dollar Funding OCR Team'
__description__ = 'Integration tests for the OCR Service'