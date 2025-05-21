# router.py

from fastapi import APIRouter

from .health import router as health_router
from .status import router as status_router
from .diagnostics import router as diagnostics_router
from .documents import router as documents_router

# Create main API router
router = APIRouter(
    # API metadata
    title="Document Service API",
    description="API for document classification and metadata extraction",
    version="1.0.0",
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
    documents_router,
    prefix="/documents",
    tags=["documents"],
)