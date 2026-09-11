"""Health check endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings
from app.core.dependencies import settings_dependency

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(
    settings: Annotated[Settings, Depends(settings_dependency)],
) -> dict[str, str]:
    """Return lightweight service health without external dependency checks."""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }
