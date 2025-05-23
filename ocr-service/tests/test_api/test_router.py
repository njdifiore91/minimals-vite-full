#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the OCR Service API router configuration.

This module contains tests to verify that the main router correctly includes all sub-routers
with appropriate prefixes and that API metadata is properly set. It ensures the central
routing hub for the OCR Service API is correctly configured.
"""

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

# Import the router to test
from src.api.router import router, tags_metadata

# Import sub-routers to verify they're included
from src.api.health import health_router
from src.api.status import status_router
from src.api.diagnostics import router as diagnostics_router
from src.api.ocr import router as ocr_router


@pytest.mark.unit
@pytest.mark.api
class TestRouter:
    """Test suite for the OCR Service API router configuration."""

    def test_router_prefix(self):
        """Test that the main router has the correct prefix."""
        assert router.prefix == "/api/v1", "Router prefix should be '/api/v1'"

    def test_router_tags(self):
        """Test that the main router has the correct tags."""
        assert router.tags == ["api"], "Router tags should be ['api']"

    def test_router_includes_health_router(self):
        """Test that the health router is included with the correct prefix."""
        # Check if the health router is included in the main router's routes
        health_route_found = False
        for route in router.routes:
            if getattr(route, "prefix", "") == "/health":
                health_route_found = True
                break
        
        assert health_route_found, "Health router should be included with prefix '/health'"

    def test_router_includes_status_router(self):
        """Test that the status router is included with the correct prefix."""
        # Check if the status router is included in the main router's routes
        status_route_found = False
        for route in router.routes:
            if getattr(route, "prefix", "") == "/status":
                status_route_found = True
                break
        
        assert status_route_found, "Status router should be included with prefix '/status'"

    def test_router_includes_diagnostics_router(self):
        """Test that the diagnostics router is included with the correct prefix."""
        # Check if the diagnostics router is included in the main router's routes
        diagnostics_route_found = False
        for route in router.routes:
            if getattr(route, "prefix", "") == "/diagnostics":
                diagnostics_route_found = True
                break
        
        assert diagnostics_route_found, "Diagnostics router should be included with prefix '/diagnostics'"

    def test_router_includes_ocr_router(self):
        """Test that the OCR router is included with the correct prefix."""
        # Check if the OCR router is included in the main router's routes
        ocr_route_found = False
        for route in router.routes:
            if getattr(route, "prefix", "") == "/ocr":
                ocr_route_found = True
                break
        
        assert ocr_route_found, "OCR router should be included with prefix '/ocr'"

    def test_tags_metadata(self):
        """Test that the API metadata is properly set."""
        # Verify that tags_metadata contains entries for all routers
        tag_names = [tag["name"] for tag in tags_metadata]
        
        assert "api" in tag_names, "API metadata should include 'api' tag"
        assert "health" in tag_names, "API metadata should include 'health' tag"
        assert "status" in tag_names, "API metadata should include 'status' tag"
        assert "diagnostics" in tag_names, "API metadata should include 'diagnostics' tag"
        assert "ocr" in tag_names, "API metadata should include 'ocr' tag"
        
        # Verify that each tag has a description
        for tag in tags_metadata:
            assert "description" in tag, f"Tag '{tag['name']}' should have a description"
            assert tag["description"], f"Tag '{tag['name']}' should have a non-empty description"

    def test_router_docstring(self):
        """Test that the router has a proper docstring."""
        assert router.__doc__, "Router should have a docstring"
        assert "OCR Service API" in router.__doc__, "Router docstring should mention 'OCR Service API'"


@pytest.mark.integration
@pytest.mark.api
class TestRouterIntegration:
    """Integration tests for the OCR Service API router."""

    def test_health_endpoint_accessible(self, client: TestClient):
        """Test that the health endpoint is accessible through the main router."""
        response = client.get("/api/v1/health/liveness")
        assert response.status_code == 200, "Health liveness endpoint should be accessible"
        assert "status" in response.json(), "Health response should include status field"

    def test_status_endpoint_accessible(self, client: TestClient):
        """Test that the status endpoint is accessible through the main router."""
        response = client.get("/api/v1/status")
        assert response.status_code == 200, "Status endpoint should be accessible"

    def test_diagnostics_endpoint_accessible(self, client: TestClient):
        """Test that the diagnostics endpoint is accessible through the main router."""
        # Note: This might require authentication in a real implementation
        response = client.get("/api/v1/diagnostics/config")
        # We're just testing routing, not authentication, so any response code other than 404 is acceptable
        assert response.status_code != 404, "Diagnostics config endpoint should be routable"

    def test_ocr_endpoint_accessible(self, client: TestClient):
        """Test that the OCR endpoint is accessible through the main router."""
        # Create a test document ID
        test_document_id = "test-document-id"
        
        # Test the OCR endpoint
        response = client.get(f"/api/v1/ocr/{test_document_id}")
        # We're just testing routing, not the actual processing, so any response code other than 404 is acceptable
        assert response.status_code != 404, "OCR document endpoint should be routable"


@pytest.mark.unit
@pytest.mark.api
def test_router_instance():
    """Test that the router is an instance of APIRouter."""
    assert isinstance(router, APIRouter), "Router should be an instance of APIRouter"


@pytest.mark.unit
@pytest.mark.api
def test_router_routes_count():
    """Test that the router has the correct number of routes."""
    # The router should include 4 sub-routers
    assert len(router.routes) == 4, "Router should include 4 sub-routers"


@pytest.mark.unit
@pytest.mark.api
def test_tags_metadata_count():
    """Test that the tags_metadata has the correct number of entries."""
    # There should be 5 tags: api, health, status, diagnostics, ocr
    assert len(tags_metadata) == 5, "tags_metadata should have 5 entries"