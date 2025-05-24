#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service API Package.

This package provides the API endpoints for the Document Service. It serves as the central
entry point for all API routers, enabling clean imports throughout the application.

Example:
    from api import router as api_router  # Import the main API router
    from api import health_router  # Import just the health check router

The package exports the following routers:
    - router: Main API router that aggregates all endpoints
    - health_router: Health check endpoints for Kubernetes probes
    - status_router: Status and metrics endpoints
    - diagnostics_router: Diagnostic endpoints for troubleshooting
    - documents_router: Document operations endpoints
"""

import logging

# Configure logger
logger = logging.getLogger(__name__)

# Import and re-export routers
from .router import router
from .health import health_router
from .status import router as status_router
from .diagnostics import router as diagnostics_router
from .documents import router as documents_router

# Log initialization
logger.info("Document Service API package initialized")

__all__ = [
    "router",
    "health_router",
    "status_router",
    "diagnostics_router",
    "documents_router"
]