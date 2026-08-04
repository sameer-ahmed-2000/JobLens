import redis
import redis.asyncio as aioredis
from typing import Optional
from app.config import settings

_redis_sync_client: Optional[redis.Redis] = None
_redis_async_client: Optional[aioredis.Redis] = None

def get_redis_client() -> redis.Redis:
    """
    Returns a shared, thread-safe sync Redis client instance backed by a connection pool.
    """
    global _redis_sync_client
    if _redis_sync_client is None:
        _redis_sync_client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
            socket_timeout=5.0,
            socket_connect_timeout=5.0
        )
    return _redis_sync_client

def get_async_redis_client() -> aioredis.Redis:
    """
    Returns a shared async Redis client instance.
    """
    global _redis_async_client
    if _redis_async_client is None:
        _redis_async_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20
        )
    return _redis_async_client
