#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Main router file for the OCR Service API.

This file creates a FastAPI APIRouter instance and includes all sub-routers
(health, status, diagnostics, ocr) with appropriate prefixes. It serves as the
central routing hub for the OCR Service API and is mounted in the main FastAPI application.

The router aggregates the following endpoints:
- /health/*: Health check endpoints for Kubernetes probes
- /status/*: Status and metrics endpoints for monitoring
- /diagnostics/*: Diagnostic endpoints for troubleshooting
- /ocr/*: OCR processing endpoints for document data extraction
"""

from fastapi import APIRouter
import logging

# Import sub-routers
from .health import health_router
from .status import status_router
from .diagnostics import router as diagnostics_router
from .ocr import router as ocr_router

# Import configuration
from ..config import app_config

# Create a logger for this module
logger = logging.getLogger(__name__)

# Create the main API router with metadata
router = APIRouter(
    prefix="/api/v1",
    tags=["api"],
)

# Add docstring to the router for better code documentation
router.__doc__ = """
Main OCR Service API router.

This router aggregates all OCR Service API endpoints under the /api/v1 prefix.
It includes health checks, status endpoints, diagnostics, and OCR processing endpoints.
"""

# Add API metadata
tags_metadata = [
    {
        "name": "api",
        "description": "Main OCR Service API endpoints"
    },
    {
        "name": "health",
        "description": "Health check endpoints for Kubernetes probes"
    },
    {
        "name": "status",
        "description": "Status and metrics endpoints for monitoring"
    },
    {
        "name": "diagnostics",
        "description": "Diagnostic endpoints for troubleshooting"
    },
    {
        "name": "ocr",
        "description": "OCR processing endpoints for document data extraction"
    }
]

# Include all sub-routers with appropriate prefixes
router.include_router(
    health_router,
    prefix="/health",
    tags=["health"]
)

router.include_router(
    status_router,
    prefix="/status",
    tags=["status"]
)

router.include_router(
    diagnostics_router,
    prefix="/diagnostics",
    tags=["diagnostics"]
)

router.include_router(
    ocr_router,
    prefix="/ocr",
    tags=["ocr"]
)

# Log router initialization
logger.info(
    f"Initialized OCR Service API router with version {app_config.SERVICE_VERSION}"
)