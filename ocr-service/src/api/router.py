#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service API Router

This module serves as the central routing hub for the OCR Service API.
It aggregates all API endpoints from various sub-routers and provides
a unified API surface for the OCR Service.

The router includes endpoints for:
- Health checks (liveness and readiness probes for Kubernetes)
- Status monitoring (metrics and performance statistics)
- Diagnostics (logs, configuration, and troubleshooting)
- OCR operations (document processing and data extraction)

This router is mounted in the main FastAPI application.

Example usage:
    from fastapi import FastAPI
    from api import router
    
    app = FastAPI()
    app.include_router(router)
"""

from fastapi import APIRouter

# Import sub-routers
from .health import router as health_router
from .status import router as status_router
from .diagnostics import router as diagnostics_router
from .ocr import router as ocr_router

# Create main router with API metadata
router = APIRouter(
    prefix="/api/v1",
    tags=["ocr-service"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"},
    },
)

# Include all sub-routers with appropriate prefixes
router.include_router(
    health_router,
    prefix="/health",
    tags=["health"],
)

router.include_router(
    status_router,
    prefix="/status",
    tags=["status"],
)

router.include_router(
    diagnostics_router,
    prefix="/diagnostics",
    tags=["diagnostics"],
)

router.include_router(
    ocr_router,
    prefix="/ocr",
    tags=["ocr"],
)

# API metadata
__title__ = "OCR Service API"
__description__ = "API for the OCR Service that extracts data from documents using TensorFlow"
__version__ = "1.0.0"
__docs_url__ = "/api/v1/docs"
__redoc_url__ = "/api/v1/redoc"
__openapi_url__ = "/api/v1/openapi.json"
__openapi_tags__ = [
    {
        "name": "health",
        "description": "Health check endpoints for Kubernetes probes",
    },
    {
        "name": "status",
        "description": "Status endpoints for monitoring service performance and metrics",
    },
    {
        "name": "diagnostics",
        "description": "Diagnostic endpoints for troubleshooting and configuration",
    },
    {
        "name": "ocr",
        "description": "OCR processing endpoints for document data extraction",
    },
]