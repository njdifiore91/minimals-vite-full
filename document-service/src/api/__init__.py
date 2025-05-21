#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Document Service API Package.

This module serves as the central entry point for the Document Service API,
importing and re-exporting all API routers to present a single, cohesive API surface.
This simplifies router imports throughout the application and ensures consistent API usage.

Example:
    from api import router  # Main API router
    from api import health_router  # Health check router
    from api import status_router  # Status monitoring router
    from api import diagnostics_router  # Diagnostics router
    from api import documents_router  # Document operations router
"""

# Import routers from modules
from .router import router
from .health import health_router
from .status import router as status_router
from .diagnostics import diagnostics_router
from .documents import router as documents_router

# Re-export routers for clean imports
__all__ = [
    'router',  # Main API router
    'health_router',  # Health check router
    'status_router',  # Status monitoring router
    'diagnostics_router',  # Diagnostics router
    'documents_router',  # Document operations router
]