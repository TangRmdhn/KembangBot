"""Kembang AI FastAPI application factory.

Wires together all routers, lifecycle events, exception handlers,
middleware, and logging configuration.
"""

import sys
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.config import settings
from app.api import all_routers
from app.core.exceptions import KembangError
from app.db.session import init_db, close_db
from app.db.redis import init_redis, close_redis
from app.dependencies import cleanup_waha_client


# Configure loguru
logger.remove()
logger.add(
    sys.stdout,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
    level="DEBUG" if settings.APP_DEBUG else "INFO",
    serialize=settings.is_production,  # JSON in production
)


def create_app() -> FastAPI:
    """Create and configure FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Kembang AI API",
        description="AI Sales Agent Platform for Indonesian SMEs",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    # For HF Spaces testing - accept all origins (restrict after production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register lifecycle events
    @app.on_event("startup")
    async def startup():
        """Initialize database and Redis connections on startup."""
        await init_db()
        await init_redis()
        logger.info("Kembang AI API started", env=settings.APP_ENV)

    @app.on_event("shutdown")
    async def shutdown():
        """Close connections on shutdown."""
        await close_db()
        await close_redis()
        await cleanup_waha_client()
        logger.info("Kembang AI API shutdown")

    # Register all routers
    for router in all_routers:
        app.include_router(router)

    # Register exception handlers
    @app.exception_handler(KembangError)
    async def kembang_error_handler(request: Request, exc: KembangError):
        """Handle custom KembangError exceptions."""
        logger.warning(
            "KembangError",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.message,
                "code": exc.code,
            },
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        """Handle unhandled exceptions."""
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "code": "INTERNAL_ERROR",
            },
        )

    return app


# Create app instance
app = create_app()
