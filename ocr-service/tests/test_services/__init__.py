#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service - Test Services Package

This module marks the test_services directory as a Python package, enabling pytest
to discover and run all test modules within this directory. The primary purpose of
this file is to ensure proper test discovery and execution within the Python testing
framework.

Test modules in this package validate the functionality of OCR service components:
- test_ocr_service.py: Tests for the core OCR processing service
- test_queue_service.py: Tests for RabbitMQ message handling
- test_storage_service.py: Tests for S3-compatible storage operations
- test_field_extraction_service.py: Tests for structured data extraction
- test_confidence_service.py: Tests for confidence evaluation

This package structure mirrors the source code structure for clarity and maintainability.
"""

# This file intentionally left mostly empty
# Its presence marks this directory as a Python package for test discovery