#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the OCR Service API package initialization.

This module contains tests to verify that the __init__.py file correctly imports and
re-exports all API routers, providing a single entry point for the API surface.
It ensures that the API module structure is correct and that all routers are accessible.
"""

import pytest
import importlib
from fastapi import APIRouter


@pytest.mark.unit
@pytest.mark.api
class TestApiInit:
    """Test suite for the OCR Service API package initialization."""

    def test_api_package_importable(self):
        """Test that the API package can be imported without errors."""
        try:
            import src.api
            assert True, "API package should be importable"
        except ImportError as e:
            pytest.fail(f"Failed to import API package: {e}")

    def test_router_exported(self):
        """Test that the main router is exported from the API package."""
        from src.api import router
        assert isinstance(router, APIRouter), "router should be an instance of APIRouter"

    def test_health_router_exported(self):
        """Test that the health router is exported from the API package."""
        from src.api import health_router
        assert isinstance(health_router, APIRouter), "health_router should be an instance of APIRouter"

    def test_status_router_exported(self):
        """Test that the status router is exported from the API package."""
        from src.api import status_router
        assert isinstance(status_router, APIRouter), "status_router should be an instance of APIRouter"

    def test_diagnostics_router_exported(self):
        """Test that the diagnostics router is exported from the API package."""
        from src.api import diagnostics_router
        assert isinstance(diagnostics_router, APIRouter), "diagnostics_router should be an instance of APIRouter"

    def test_ocr_router_exported(self):
        """Test that the OCR router is exported from the API package."""
        from src.api import ocr_router
        assert isinstance(ocr_router, APIRouter), "ocr_router should be an instance of APIRouter"

    def test_all_variable(self):
        """Test that the __all__ variable contains all expected routers."""
        import src.api
        assert hasattr(src.api, "__all__"), "API package should have __all__ variable"
        
        expected_exports = [
            "router",
            "health_router",
            "status_router",
            "diagnostics_router",
            "ocr_router"
        ]
        
        for export in expected_exports:
            assert export in src.api.__all__, f"{export} should be in __all__"

    def test_version_exported(self):
        """Test that the package version is exported."""
        from src.api import __version__
        assert isinstance(__version__, str), "__version__ should be a string"
        assert __version__, "__version__ should not be empty"


@pytest.mark.unit
@pytest.mark.api
class TestImportOrder:
    """Test suite for verifying proper import order to prevent circular dependencies."""

    def test_no_circular_imports(self):
        """Test that there are no circular imports in the API package."""
        # Reload the module to ensure we're testing the actual import behavior
        importlib.reload(importlib.import_module("src.api"))
        
        # If we got here without an ImportError, there are no circular imports
        assert True, "API package should not have circular imports"

    def test_import_order(self):
        """Test that the import order is correct to prevent circular dependencies."""
        # The main router should be imported first, followed by individual routers
        import inspect
        import src.api
        
        # Get the source code of the __init__.py file
        source = inspect.getsource(src.api)
        
        # Check that router is imported before other routers
        router_import_pos = source.find("from .router import router")
        health_import_pos = source.find("from .health import health_router")
        status_import_pos = source.find("from .status import status_router")
        diagnostics_import_pos = source.find("from .diagnostics import router as diagnostics_router")
        ocr_import_pos = source.find("from .ocr import router as ocr_router")
        
        assert router_import_pos < health_import_pos, "router should be imported before health_router"
        assert router_import_pos < status_import_pos, "router should be imported before status_router"
        assert router_import_pos < diagnostics_import_pos, "router should be imported before diagnostics_router"
        assert router_import_pos < ocr_import_pos, "router should be imported before ocr_router"


@pytest.mark.integration
@pytest.mark.api
class TestApiIntegration:
    """Integration tests for the API package."""

    def test_router_includes_all_subrouters(self):
        """Test that the main router includes all sub-routers."""
        from src.api import router
        
        # The router should have 4 routes (one for each sub-router)
        assert len(router.routes) == 4, "Main router should include 4 sub-routers"
        
        # Check that each sub-router is included with the correct prefix
        prefixes = [getattr(route, "prefix", "") for route in router.routes]
        
        assert "/health" in prefixes, "Main router should include health_router with prefix '/health'"
        assert "/status" in prefixes, "Main router should include status_router with prefix '/status'"
        assert "/diagnostics" in prefixes, "Main router should include diagnostics_router with prefix '/diagnostics'"
        assert "/ocr" in prefixes, "Main router should include ocr_router with prefix '/ocr'"

    def test_api_endpoints_accessible(self, client):
        """Test that all API endpoints are accessible through the main router."""
        # Test health endpoint
        response = client.get("/api/v1/health/liveness")
        assert response.status_code == 200, "Health liveness endpoint should be accessible"
        
        # Test status endpoint
        response = client.get("/api/v1/status")
        assert response.status_code == 200, "Status endpoint should be accessible"
        
        # Test diagnostics endpoint (might require authentication in a real implementation)
        response = client.get("/api/v1/diagnostics/config")
        # We're just testing routing, not authentication, so any response code other than 404 is acceptable
        assert response.status_code != 404, "Diagnostics config endpoint should be routable"
        
        # Test OCR endpoint
        test_document_id = "test-document-id"
        response = client.get(f"/api/v1/ocr/{test_document_id}")
        # We're just testing routing, not the actual processing, so any response code other than 404 is acceptable
        assert response.status_code != 404, "OCR document endpoint should be routable"