"""Health check API routes for Kembang AI."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import engine, get_db
from app.db.redis import get_redis
from app.schemas.common import APIResponse
from app.core.model_config import get_model_info

router = APIRouter(tags=["health"])


@router.get("/health", response_model=APIResponse[dict])
async def health_check() -> APIResponse[dict]:
    """Basic health check endpoint.

    Returns OK if the API is running.
    """
    return APIResponse(
        success=True,
        data={
            "status": "ok",
            "version": "0.1.0",
            "models": get_model_info(),
        },
    )


@router.get("/health/ready", response_model=APIResponse[dict])
async def readiness_check(
    db: AsyncSession = Depends(get_db),
) -> APIResponse[dict]:
    """Readiness check with dependency health.

    Verifies database and Redis connectivity.
    """
    db_status = "ok"
    redis_status = "ok"

    try:
        # Check database
        await db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    try:
        # Check Redis
        redis = await get_redis()
        await redis.ping()
    except Exception:
        redis_status = "error"

    is_ready = db_status == "ok" and redis_status == "ok"

    return APIResponse(
        success=is_ready,
        data={
            "db": db_status,
            "redis": redis_status,
        },
    )
