#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests for the main router configuration in the OCR Service API.

This module verifies that the main router correctly includes all sub-routers
with appropriate prefixes and that API metadata is properly set. It ensures
the central routing hub for the OCR Service API is correctly configured.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Import the main router and sub-routers to test
from src.api.router import router, __title__, __description__, __version__, __openapi_tags__
from src.api.health import router as health_router
from src.api.status import router as status_router
from src.api.diagnostics import router as diagnostics_router
from src.api.ocr import router as ocr_router


@pytest.fixture
def test_app():
    """Create a test FastAPI app with the main router."""
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def test_client(test_app):
    """Create a TestClient for the test app."""
    return TestClient(test_app)


class TestRouterConfiguration:
    """Tests for the main router configuration."""

    def test_router_prefix(self):
        """Test that the main router has the correct prefix."""
        assert router.prefix == "/api/v1"

    def test_router_tags(self):
        """Test that the main router has the correct tags."""
        assert router.tags == ["ocr-service"]

    def test_router_responses(self):
        """Test that the main router has the correct default responses."""
        assert 404 in router.responses
        assert 500 in router.responses
        assert router.responses[404]["description"] == "Not found"
        assert router.responses[500]["description"] == "Internal server error"


class TestSubRouterInclusion:
    """Tests for the inclusion of sub-routers in the main router."""

    def test_health_router_included(self, test_client):
        """Test that the health router is included with the correct prefix."""
        # Make a request to a health endpoint
        with patch("src.api.health.check_rabbitmq_health", return_value={"status": "ok"}):
            with patch("src.api.health.check_s3_health", return_value={"status": "ok"}):
                with patch("src.api.health.check_gpu_health", return_value={"status": "ok"}):
                    response = test_client.get("/api/v1/health/readiness")
                    assert response.status_code == 200

    def test_status_router_included(self, test_client):
        """Test that the status router is included with the correct prefix."""
        # Mock the status endpoint response
        with patch("src.api.status.get_service_status", return_value={"status": "ok"}):
            response = test_client.get("/api/v1/status")
            assert response.status_code == 200

    def test_diagnostics_router_included(self, test_client):
        """Test that the diagnostics router is included with the correct prefix."""
        # Mock the diagnostics endpoint response
        with patch("src.api.diagnostics.get_service_config", return_value={"config": "test"}):
            # Assuming authentication is required, mock it
            with patch("src.api.diagnostics.verify_admin_access", return_value=True):
                response = test_client.get("/api/v1/diagnostics/config")
                assert response.status_code == 200

    def test_ocr_router_included(self, test_client):
        """Test that the OCR router is included with the correct prefix."""
        # Mock the OCR endpoint response
        with patch("src.api.ocr.get_ocr_result", return_value={"result": "test"}):
            response = test_client.get("/api/v1/ocr/doc-123456")
            assert response.status_code == 200


class TestRouterMetadata:
    """Tests for the API metadata in the main router."""

    def test_api_title(self):
        """Test that the API title is correctly set."""
        assert __title__ == "OCR Service API"

    def test_api_description(self):
        """Test that the API description is correctly set."""
        assert __description__ == "API for the OCR Service that extracts data from documents using TensorFlow"

    def test_api_version(self):
        """Test that the API version is correctly set."""
        assert __version__ == "1.0.0"

    def test_openapi_tags(self):
        """Test that the OpenAPI tags are correctly set."""
        # Check that all required tags are present
        tag_names = [tag["name"] for tag in __openapi_tags__]
        assert "health" in tag_names
        assert "status" in tag_names
        assert "diagnostics" in tag_names
        assert "ocr" in tag_names

        # Check tag descriptions
        for tag in __openapi_tags__:
            if tag["name"] == "health":
                assert "Health check" in tag["description"]
            elif tag["name"] == "status":
                assert "Status" in tag["description"]
            elif tag["name"] == "diagnostics":
                assert "Diagnostic" in tag["description"]
            elif tag["name"] == "ocr":
                assert "OCR processing" in tag["description"]


class TestOpenAPIConfiguration:
    """Tests for the OpenAPI configuration in the main router."""

    def test_docs_url(self):
        """Test that the docs URL is correctly set."""
        assert __docs_url__ == "/api/v1/docs"

    def test_redoc_url(self):
        """Test that the ReDoc URL is correctly set."""
        assert __redoc_url__ == "/api/v1/redoc"

    def test_openapi_url(self):
        """Test that the OpenAPI URL is correctly set."""
        assert __openapi_url__ == "/api/v1/openapi.json"


class TestIntegrationWithFastAPI:
    """Tests for the integration of the router with FastAPI."""

    def test_router_integration(self):
        """Test that the router can be integrated with a FastAPI app."""
        app = FastAPI()
        # This should not raise any exceptions
        app.include_router(router)

    def test_openapi_schema_generation(self, test_app):
        """Test that the OpenAPI schema can be generated from the router."""
        # Get the OpenAPI schema
        openapi_schema = test_app.openapi()
        
        # Check that the schema contains the expected paths
        assert "/api/v1/health/readiness" in openapi_schema["paths"]
        assert "/api/v1/health/liveness" in openapi_schema["paths"]
        assert "/api/v1/status" in openapi_schema["paths"]
        assert "/api/v1/diagnostics/config" in openapi_schema["paths"]
        assert "/api/v1/ocr/{document_id}" in openapi_schema["paths"]