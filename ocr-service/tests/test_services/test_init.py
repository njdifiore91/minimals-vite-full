#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the services package initialization file.

This module verifies that the services package correctly imports and re-exports
all service components, presenting a single, cohesive API surface. These tests
ensure that the Python package structure works as expected and that imports
of service components will function correctly throughout the application.
"""

import importlib
import sys
import unittest
from unittest import mock


class TestServicesInit(unittest.TestCase):
    """Test cases for the services package initialization."""

    def setUp(self):
        """Set up test environment before each test."""
        # Clear any cached imports to ensure clean test environment
        if 'services' in sys.modules:
            del sys.modules['services']
        if 'services.ocr_service' in sys.modules:
            del sys.modules['services.ocr_service']
        if 'services.queue_service' in sys.modules:
            del sys.modules['services.queue_service']
        if 'services.storage_service' in sys.modules:
            del sys.modules['services.storage_service']
        if 'services.field_extraction_service' in sys.modules:
            del sys.modules['services.field_extraction_service']
        if 'services.confidence_service' in sys.modules:
            del sys.modules['services.confidence_service']

    def test_all_services_exported(self):
        """Test that __all__ contains all expected service classes."""
        # Mock the service modules to avoid actual imports
        with mock.patch.dict('sys.modules', {
            'services.ocr_service': mock.MagicMock(),
            'services.queue_service': mock.MagicMock(),
            'services.storage_service': mock.MagicMock(),
            'services.field_extraction_service': mock.MagicMock(),
            'services.confidence_service': mock.MagicMock()
        }):
            # Import the services package
            import services
            
            # Check that __all__ contains all expected service classes
            expected_services = [
                'OCRService',
                'QueueService',
                'StorageService',
                'FieldExtractionService',
                'ConfidenceService'
            ]
            
            self.assertListEqual(sorted(services.__all__), sorted(expected_services))

    def test_direct_service_imports(self):
        """Test that services can be imported directly from the package."""
        # Mock the service modules to avoid actual imports
        with mock.patch.dict('sys.modules', {
            'services.ocr_service': mock.MagicMock(OCRService=mock.MagicMock()),
            'services.queue_service': mock.MagicMock(QueueService=mock.MagicMock()),
            'services.storage_service': mock.MagicMock(StorageService=mock.MagicMock()),
            'services.field_extraction_service': mock.MagicMock(FieldExtractionService=mock.MagicMock()),
            'services.confidence_service': mock.MagicMock(ConfidenceService=mock.MagicMock())
        }):
            # Test direct imports
            from services import OCRService
            from services import QueueService
            from services import StorageService
            from services import FieldExtractionService
            from services import ConfidenceService
            
            # If we get here without exceptions, the imports worked
            self.assertTrue(True)

    def test_wildcard_import(self):
        """Test that wildcard import works correctly."""
        # Mock the service modules to avoid actual imports
        with mock.patch.dict('sys.modules', {
            'services.ocr_service': mock.MagicMock(OCRService=mock.MagicMock()),
            'services.queue_service': mock.MagicMock(QueueService=mock.MagicMock()),
            'services.storage_service': mock.MagicMock(StorageService=mock.MagicMock()),
            'services.field_extraction_service': mock.MagicMock(FieldExtractionService=mock.MagicMock()),
            'services.confidence_service': mock.MagicMock(ConfidenceService=mock.MagicMock())
        }):
            # Test wildcard import
            from services import *
            
            # Check that all services are imported
            self.assertTrue('OCRService' in locals())
            self.assertTrue('QueueService' in locals())
            self.assertTrue('StorageService' in locals())
            self.assertTrue('FieldExtractionService' in locals())
            self.assertTrue('ConfidenceService' in locals())

    def test_service_attributes(self):
        """Test that services are attributes of the services package."""
        # Mock the service modules to avoid actual imports
        with mock.patch.dict('sys.modules', {
            'services.ocr_service': mock.MagicMock(OCRService=mock.MagicMock()),
            'services.queue_service': mock.MagicMock(QueueService=mock.MagicMock()),
            'services.storage_service': mock.MagicMock(StorageService=mock.MagicMock()),
            'services.field_extraction_service': mock.MagicMock(FieldExtractionService=mock.MagicMock()),
            'services.confidence_service': mock.MagicMock(ConfidenceService=mock.MagicMock())
        }):
            # Import the services package
            import services
            
            # Check that all services are attributes of the package
            self.assertTrue(hasattr(services, 'OCRService'))
            self.assertTrue(hasattr(services, 'QueueService'))
            self.assertTrue(hasattr(services, 'StorageService'))
            self.assertTrue(hasattr(services, 'FieldExtractionService'))
            self.assertTrue(hasattr(services, 'ConfidenceService'))

    def test_import_from_submodule(self):
        """Test that services can be imported from their original modules."""
        # Mock the service modules to avoid actual imports
        ocr_service_mock = mock.MagicMock()
        ocr_service_mock.OCRService = mock.MagicMock()
        
        queue_service_mock = mock.MagicMock()
        queue_service_mock.QueueService = mock.MagicMock()
        
        storage_service_mock = mock.MagicMock()
        storage_service_mock.StorageService = mock.MagicMock()
        
        field_extraction_service_mock = mock.MagicMock()
        field_extraction_service_mock.FieldExtractionService = mock.MagicMock()
        
        confidence_service_mock = mock.MagicMock()
        confidence_service_mock.ConfidenceService = mock.MagicMock()
        
        with mock.patch.dict('sys.modules', {
            'services.ocr_service': ocr_service_mock,
            'services.queue_service': queue_service_mock,
            'services.storage_service': storage_service_mock,
            'services.field_extraction_service': field_extraction_service_mock,
            'services.confidence_service': confidence_service_mock,
            'services': mock.MagicMock()
        }):
            # Import from submodules
            from services.ocr_service import OCRService
            from services.queue_service import QueueService
            from services.storage_service import StorageService
            from services.field_extraction_service import FieldExtractionService
            from services.confidence_service import ConfidenceService
            
            # If we get here without exceptions, the imports worked
            self.assertTrue(True)

    def test_reimport_consistency(self):
        """Test that reimporting the services package is consistent."""
        # Mock the service modules to avoid actual imports
        with mock.patch.dict('sys.modules', {
            'services.ocr_service': mock.MagicMock(OCRService=mock.MagicMock()),
            'services.queue_service': mock.MagicMock(QueueService=mock.MagicMock()),
            'services.storage_service': mock.MagicMock(StorageService=mock.MagicMock()),
            'services.field_extraction_service': mock.MagicMock(FieldExtractionService=mock.MagicMock()),
            'services.confidence_service': mock.MagicMock(ConfidenceService=mock.MagicMock())
        }):
            # Import the services package
            import services as services1
            # Reimport the services package
            importlib.reload(services1)
            import services as services2
            
            # Check that both imports refer to the same object
            self.assertIs(services1, services2)
            
            # Check that all services are still attributes of the package
            self.assertTrue(hasattr(services2, 'OCRService'))
            self.assertTrue(hasattr(services2, 'QueueService'))
            self.assertTrue(hasattr(services2, 'StorageService'))
            self.assertTrue(hasattr(services2, 'FieldExtractionService'))
            self.assertTrue(hasattr(services2, 'ConfidenceService'))


if __name__ == '__main__':
    unittest.main()