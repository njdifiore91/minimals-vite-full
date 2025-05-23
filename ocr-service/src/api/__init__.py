#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service API Package

This package serves as the central entry point for the OCR Service API module.
It imports and re-exports all API routers to present a single, cohesive API surface,
simplifying router imports throughout the application and ensuring consistent API usage.

The package exports the following routers:
- router: The main API router that aggregates all endpoints
- health_router: Router for health check endpoints (liveness and readiness probes)
- status_router: Router for status and metrics endpoints
- diagnostics_router: Router for diagnostic and troubleshooting endpoints
- ocr_router: Router for OCR processing endpoints

Example usage:
    from fastapi import FastAPI
    from api import router
    
    app = FastAPI()
    app.include_router(router)
"""

# Import the main router that aggregates all endpoints
from .router import router

# Import individual routers for direct access if needed
from .health import health_router
from .status import status_router
from .diagnostics import router as diagnostics_router
from .ocr import router as ocr_router

# Re-export all routers with consistent naming
__all__ = [
    'router',           # Main aggregated router
    'health_router',     # Health check endpoints
    'status_router',     # Status and metrics endpoints
    'diagnostics_router', # Diagnostic endpoints
    'ocr_router'         # OCR processing endpoints
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'Dollar Funding'
__description__ = 'OCR Service API for the Merchant Cash Advance Application Processing System'