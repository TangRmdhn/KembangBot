"""Database session setup for Kembang AI.

Async SQLAlchemy 2.0 with asyncpg for PostgreSQL connection management.
"""

from collections.abc import AsyncGenerator
from urllib.parse import urlparse, parse_qs
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
)
from loguru import logger

from app.config import settings


def _prepare_database_url(url: str) -> str:
    """Prepare database URL for asyncpg by removing unsupported parameters.
    
    asyncpg doesn't support sslmode parameter directly.
    SSL is handled via connection args.
    """
    parsed = urlparse(url)
    query_params = parse_qs(parsed.query)
    
    # Remove sslmode as asyncpg handles SSL differently
    if 'sslmode' in query_params:
        # Reconstruct URL without sslmode
        new_query = {k: v for k, v in query_params.items() if k != 'sslmode'}
        new_query_str = '&'.join(f'{k}={v[0]}' for k, v in new_query.items())
        url = f'{parsed.scheme}://{parsed.netloc}{parsed.path}'
        if new_query_str:
            url += f'?{new_query_str}'
    
    return url


# Create async engine
# Neon PostgreSQL requires SSL - connection args handle this
engine = create_async_engine(
    _prepare_database_url(settings.DATABASE_URL),
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    echo=settings.APP_DEBUG,  # Log SQL in debug mode
    # For Neon: connection pre-ping to handle serverless cold start
    pool_pre_ping=True,
    pool_recycle=300,  # recycle connections every 5 minutes
    # SSL is automatically enabled for Neon connections
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
