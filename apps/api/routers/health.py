from __future__ import annotations

from fastapi import APIRouter, Response, status

from licensing.database import check_database_connection

router = APIRouter(tags=["health"])


@router.get("/health/live")
def liveness() -> dict[str, str]:
    """Process is up. Does not touch the database."""
    return {"status": "ok"}


@router.get("/health/ready")
def readiness(response: Response) -> dict[str, str]:
    """Process is up AND its required dependencies (database) are reachable."""
    if not check_database_connection():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unreachable"}
    return {"status": "ready", "database": "ok"}
