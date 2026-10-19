"""Health check endpoint."""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from backend.app.core.config import settings

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str
    gemini_configured: bool
    timestamp: str


@router.get("/health", response_model=HealthResponse)
async def check_health() -> HealthResponse:
    """Return system health status and configuration readiness."""
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        gemini_configured=bool(settings.GEMINI_API_KEY.strip()),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
