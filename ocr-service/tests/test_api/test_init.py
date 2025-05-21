#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the OCR Service API package initialization.

This module verifies that the __init__.py file correctly imports and re-exports
all API routers, providing a single entry point for the API surface. It ensures
that the API package follows Python package conventions for modularity and
prevents circular dependencies.
"""

import pytest
import importlib
import sys
from unittest.mock import patch


class TestAPIPackageImport:
    """Tests for importing the API package."""

    def test_api_package_import(self):
        """Test that the API package can be imported without errors."""
        # This should not raise any exceptions
        import src.api
        
        # Reload to ensure we're testing a fresh import
        importlib.reload(src.api)

    def test_api_version(self):
        """Test that the API package has a version."""
        import src.api
        assert hasattr(src.api, '__version__')
        assert isinstance(src.api.__version__, str)
        assert src.api.__version__ == '1.0.0'

    def test_api_metadata(self):
        """Test that the API package has metadata."""
        import src.api
        assert hasattr(src.api, '__author__')
        assert hasattr(src.api, '__email__')
        assert hasattr(src.api, '__description__')


class TestRouterExports:
    """Tests for router exports from the API package."""

    def test_main_router_export(self):
        """Test that the main router is exported."""
        import src.api
        assert hasattr(src.api, 'router')
        from src.api import router
        assert router.prefix == "/api/v1"

    def test_health_router_export(self):
        """Test that the health router is exported."""
        import src.api
        assert hasattr(src.api, 'health_router')
        from src.api import health_router
        # Verify it's the correct router by checking a known endpoint
        assert any(route.path == "/health/liveness" for route in health_router.routes)

    def test_status_router_export(self):
        """Test that the status router is exported."""
        import src.api
        assert hasattr(src.api, 'status_router')
        from src.api import status_router
        # Verify it's the correct router by checking a known endpoint
        assert any(route.path == "/status" for route in status_router.routes)

    def test_diagnostics_router_export(self):
        """Test that the diagnostics router is exported."""
        import src.api
        assert hasattr(src.api, 'diagnostics_router')
        from src.api import diagnostics_router
        # Verify it's the correct router by checking a known endpoint
        assert any(route.path == "/diagnostics/config" for route in diagnostics_router.routes)

    def test_ocr_router_export(self):
        """Test that the OCR router is exported."""
        import src.api
        assert hasattr(src.api, 'ocr_router')
        from src.api import ocr_router
        # Verify it's the correct router by checking a known endpoint
        assert any(route.path == "/ocr/{document_id}" for route in ocr_router.routes)

    def test_all_exports(self):
        """Test that __all__ contains all expected exports."""
        import src.api
        assert hasattr(src.api, '__all__')
        assert 'router' in src.api.__all__
        assert 'health_router' in src.api.__all__
        assert 'status_router' in src.api.__all__
        assert 'diagnostics_router' in src.api.__all__
        assert 'ocr_router' in src.api.__all__
        # Ensure no unexpected exports
        assert len(src.api.__all__) == 5


class TestCircularDependencies:
    """Tests for preventing circular dependencies in the API package."""

    def test_import_order(self):
        """Test that the import order prevents circular dependencies."""
        # Clear the module from sys.modules to ensure a fresh import
        for module in list(sys.modules.keys()):
            if module.startswith('src.api'):
                del sys.modules[module]
        
        # This should not raise any exceptions
        import src.api

    def test_router_imports(self):
        """Test that router imports don't cause circular dependencies."""
        # Mock the router imports to check import order
        with patch('src.api.router') as mock_router:
            with patch('src.api.health') as mock_health:
                with patch('src.api.status') as mock_status:
                    with patch('src.api.diagnostics') as mock_diagnostics:
                        with patch('src.api.ocr') as mock_ocr:
                            # Clear the module from sys.modules to ensure a fresh import
                            for module in list(sys.modules.keys()):
                                if module.startswith('src.api'):
                                    del sys.modules[module]
                            
                            # Import the package
                            import src.api
                            
                            # Check that imports happened in the correct order
                            mock_router.assert_called_once()
                            mock_health.assert_called_once()
                            mock_status.assert_called_once()
                            mock_diagnostics.assert_called_once()
                            mock_ocr.assert_called_once()


class TestPackageUsage:
    """Tests for using the API package in a FastAPI application."""

    def test_fastapi_integration(self):
        """Test that the API package can be used in a FastAPI application."""
        from fastapi import FastAPI
        from src.api import router
        
        app = FastAPI()
        # This should not raise any exceptions
        app.include_router(router)

    def test_specific_router_usage(self):
        """Test that specific routers can be used individually."""
        from fastapi import FastAPI
        from src.api import health_router, status_router, diagnostics_router, ocr_router
        
        app = FastAPI()
        # These should not raise any exceptions
        app.include_router(health_router, prefix="/api/v1/health")
        app.include_router(status_router, prefix="/api/v1/status")
        app.include_router(diagnostics_router, prefix="/api/v1/diagnostics")
        app.include_router(ocr_router, prefix="/api/v1/ocr")