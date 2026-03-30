"""Database session setup for Kembang AI.

Async SQLAlchemy 2.0 with asyncpg for PostgreSQL connection management.
"""

from collections.abc import AsyncGenerator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from loguru import logger

from app.config import settings


# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.APP_DEBUG,  # Log SQL in debug mode
)

# Create async session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async DB session.

    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...

    Session is automatically committed on success, rolled back on exception.

    Yields:
        AsyncSession instance for database operations.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database connection pool. Call on app startup.

    Verifies that the database connection is working by executing
    a simple SELECT 1 query.
    """
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection established")


async def close_db() -> None:
    """Close database connection pool. Call on app shutdown.

    Disposes of the engine and all pooled connections.
    """
    await engine.dispose()
    logger.info("Database connection closed")
