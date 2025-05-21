#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for the services package initialization file.

This file verifies that the services package correctly exports all service components
through a single, cohesive API surface, ensuring proper module exports and import functionality.
"""

import sys
import importlib
import unittest
import pytest
from unittest.mock import patch, MagicMock


class TestServicesInit(unittest.TestCase):
    """Test suite for the services package initialization."""

    def test_all_services_exported(self):
        """Verify that all service classes are properly exported in __all__."""
        # Import the services package
        from ocr_service.src.services import __all__ as services_all
        
        # Define the expected service classes
        expected_services = [
            'OCRService',
            'QueueService',
            'StorageService',
            'FieldExtractionService',
            'ConfidenceService'
        ]
        
        # Verify that all expected services are in __all__
        for service in expected_services:
            self.assertIn(service, services_all, f"{service} should be exported in __all__")
        
        # Verify that __all__ doesn't contain unexpected items
        self.assertEqual(len(services_all), len(expected_services),
                         "__all__ should only contain the expected services")

    def test_services_importable(self):
        """Verify that all services can be imported directly from the services package."""
        # Import all services from the package
        from ocr_service.src.services import (
            OCRService,
            QueueService,
            StorageService,
            FieldExtractionService,
            ConfidenceService
        )
        
        # Verify that each imported service is the correct type
        self.assertEqual(OCRService.__name__, "OCRService")
        self.assertEqual(QueueService.__name__, "QueueService")
        self.assertEqual(StorageService.__name__, "StorageService")
        self.assertEqual(FieldExtractionService.__name__, "FieldExtractionService")
        self.assertEqual(ConfidenceService.__name__, "ConfidenceService")

    def test_services_imported_from_correct_modules(self):
        """Verify that services are imported from their correct source modules."""
        # Mock the imports to verify the correct source modules
        with patch.dict('sys.modules'):
            # Create mock modules
            mock_ocr_service = MagicMock()
            mock_queue_service = MagicMock()
            mock_storage_service = MagicMock()
            mock_field_extraction_service = MagicMock()
            mock_confidence_service = MagicMock()
            
            # Add mock service classes to the mock modules
            mock_ocr_service.OCRService = type('OCRService', (), {})
            mock_queue_service.QueueService = type('QueueService', (), {})
            mock_storage_service.StorageService = type('StorageService', (), {})
            mock_field_extraction_service.FieldExtractionService = type('FieldExtractionService', (), {})
            mock_confidence_service.ConfidenceService = type('ConfidenceService', (), {})
            
            # Register the mock modules
            sys.modules['ocr_service.src.services.ocr_service'] = mock_ocr_service
            sys.modules['ocr_service.src.services.queue_service'] = mock_queue_service
            sys.modules['ocr_service.src.services.storage_service'] = mock_storage_service
            sys.modules['ocr_service.src.services.field_extraction_service'] = mock_field_extraction_service
            sys.modules['ocr_service.src.services.confidence_service'] = mock_confidence_service
            
            # Clear the services module from sys.modules to force a reload
            if 'ocr_service.src.services' in sys.modules:
                del sys.modules['ocr_service.src.services']
            
            # Import the services module
            import ocr_service.src.services as services
            
            # Verify that the services module imported the classes from the correct modules
            self.assertIs(services.OCRService, mock_ocr_service.OCRService)
            self.assertIs(services.QueueService, mock_queue_service.QueueService)
            self.assertIs(services.StorageService, mock_storage_service.StorageService)
            self.assertIs(services.FieldExtractionService, mock_field_extraction_service.FieldExtractionService)
            self.assertIs(services.ConfidenceService, mock_confidence_service.ConfidenceService)

    def test_import_patterns(self):
        """Verify that different import patterns work correctly."""
        # Test direct import of specific services
        from ocr_service.src.services import OCRService
        self.assertEqual(OCRService.__name__, "OCRService")
        
        # Test import with alias
        from ocr_service.src.services import QueueService as QS
        self.assertEqual(QS.__name__, "QueueService")
        
        # Test import of multiple services
        from ocr_service.src.services import StorageService, FieldExtractionService
        self.assertEqual(StorageService.__name__, "StorageService")
        self.assertEqual(FieldExtractionService.__name__, "FieldExtractionService")

    def test_module_docstring(self):
        """Verify that the services module has a proper docstring."""
        import ocr_service.src.services as services
        
        # Verify that the module has a docstring
        self.assertIsNotNone(services.__doc__)
        self.assertTrue(len(services.__doc__) > 0)
        
        # Verify that the docstring contains expected information
        docstring = services.__doc__.lower()
        self.assertIn("ocr service", docstring)
        self.assertIn("services package", docstring)
        self.assertIn("api surface", docstring)


@pytest.mark.parametrize("service_name", [
    "OCRService",
    "QueueService",
    "StorageService",
    "FieldExtractionService",
    "ConfidenceService"
])
def test_service_importable_individually(service_name):
    """Test that each service can be imported individually using pytest parametrization."""
    # Dynamically import the service
    module = importlib.import_module("ocr_service.src.services")
    service_class = getattr(module, service_name)
    
    # Verify that the service class has the correct name
    assert service_class.__name__ == service_name


def test_services_package_structure():
    """Test the overall structure of the services package."""
    import ocr_service.src.services as services
    
    # Verify that the package has the expected attributes
    expected_attributes = [
        "OCRService",
        "QueueService",
        "StorageService",
        "FieldExtractionService",
        "ConfidenceService",
        "__all__"
    ]
    
    for attr in expected_attributes:
        assert hasattr(services, attr), f"services package should have {attr} attribute"


def test_no_unexpected_exports():
    """Test that the services package doesn't export unexpected items."""
    import ocr_service.src.services as services
    
    # Get all public attributes (those not starting with _)
    public_attrs = [attr for attr in dir(services) if not attr.startswith('_')]
    
    # Define the expected public attributes
    expected_public_attrs = [
        "OCRService",
        "QueueService",
        "StorageService",
        "FieldExtractionService",
        "ConfidenceService"
    ]
    
    # Verify that there are no unexpected public attributes
    for attr in public_attrs:
        assert attr in expected_public_attrs, f"{attr} is an unexpected public attribute"


if __name__ == "__main__":
    unittest.main()