"""
Health check endpoint router
"""
from datetime import datetime, timezone
from fastapi import APIRouter, status
from app.core.config import settings
from app.core.database import check_db_connection
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service Health Check",
    description="Returns the health status of the API service along with version and runtime metadata.",
    tags=["System"],
)
def get_health() -> HealthResponse:
    db_status = check_db_connection()
    overall_status = "healthy" if db_status.get("connected") else "degraded"

    return HealthResponse(
        status=overall_status,
        project=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        services={
            "api": "online",
            "phase": "2 - Database & Migrations",
            "database": {
                "status": "connected" if db_status.get("connected") else "disconnected",
                "details": db_status,
            },
        },
    )
