"""Redis client setup for Kembang AI.

Redis-py async client for caching and session management.
"""

from redis.asyncio import Redis, from_url
from loguru import logger

from app.config import settings


# Global Redis client instance
redis_client: Redis | None = None


async def init_redis() -> None:
    """Initialize Redis connection. Call on app startup.

    Creates a Redis client and verifies connectivity with a PING command.
    Upstash uses rediss:// (with SSL) - redis-py handles this automatically.
    """
    global redis_client
    redis_client = from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
    )
    try:
        await redis_client.ping()
        logger.info("Redis connection established", url=settings.REDIS_URL[:30] + "...")
    except Exception as e:
        logger.error("Redis connection failed", error=str(e))
        raise


async def close_redis() -> None:
    """Close Redis connection. Call on app shutdown.

    Closes the Redis client connection and sets the global to None.
    """
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
    logger.info("Redis connection closed")


async def get_redis() -> Redis:
    """FastAPI dependency that provides Redis client.

    Usage:
        @app.get("/")
        async def endpoint(redis: Redis = Depends(get_redis)):
            ...

    Returns:
        Redis client instance.

    Raises:
        RuntimeError: If Redis has not been initialized.
    """
    if redis_client is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return redis_client
