#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OCR Service API Package

This package provides a centralized API system for the OCR Service.
It imports and re-exports all API routers to present a single,
cohesive API surface, simplifying router imports throughout the application
and ensuring consistent API usage.

The API is organized into several modules:

- router: Main router that aggregates all API endpoints
- health: Health check endpoints for Kubernetes probes
- status: Status endpoints for monitoring
- diagnostics: Diagnostic endpoints for troubleshooting
- ocr: OCR processing endpoints

Example usage:
    from api import router
    
    # In main FastAPI application
    app.include_router(router)
    
    # Or import specific routers if needed
    from api import health_router, ocr_router
"""

# Import and re-export main router
from .router import router

# Import and re-export specific routers
from .health import router as health_router
from .status import router as status_router
from .diagnostics import router as diagnostics_router
from .ocr import router as ocr_router

# Version of the API package
__version__ = '1.0.0'

# Package metadata
__author__ = 'Dollar Funding OCR Team'
__email__ = 'ocr-team@dollarfunding.com'
__description__ = 'API package for the OCR Service'

# Define __all__ to explicitly specify exported names
__all__ = [
    'router',
    'health_router',
    'status_router',
    'diagnostics_router',
    'ocr_router',
]