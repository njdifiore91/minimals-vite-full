# -*- coding: utf-8 -*-
"""
OCR Service Integration Tests Package

This package contains integration tests for the OCR Service, verifying that
components work together correctly to extract data from documents with high accuracy.

The integration tests in this package validate:
- End-to-end OCR processing pipeline functionality
- Integration between OCR models and services
- RabbitMQ message queue integration
- S3-compatible storage integration
- Confidence scoring across the pipeline
- API and service layer integration

These tests ensure that the OCR Service meets the requirements specified in the
Merchant Cash Advance (MCA) Application Processing System technical specification,
including 99% data extraction accuracy and processing applications in under 5 minutes.
"""

__version__ = '1.0.0'
__author__ = 'Dollar Funding MCA Team'