#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main router for the Document Service API.

This module aggregates all API endpoints for the Document Service into a single router.
It includes sub-routers for health checks, status monitoring, diagnostics, and document operations
with appropriate prefixes. This router serves as the central routing hub for the Document Service API
and is mounted in the main FastAPI application.
"""

import logging
from fastapi import APIRouter

# Import sub-routers
from .health import health_router
from .status import router as status_router
from .diagnostics import router as diagnostics_router
from .documents import router as documents_router

# Configure logger
logger = logging.getLogger(__name__)

# Create main API router
router = APIRouter(
    prefix="",  # No prefix for the main router as it's mounted with /api in the app
    tags=["api"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Include sub-routers
# Note: health_router routes already include the /health prefix
router.include_router(health_router)

# Include status router with /status prefix
router.include_router(status_router, prefix="/status")

# Include diagnostics router (already has /diagnostics prefix)
router.include_router(diagnostics_router)

# Include documents router (already has /documents prefix)
router.include_router(documents_router)

# Log router initialization
logger.info("Document Service API router initialized with all endpoints")