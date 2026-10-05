import json
import logging
from typing import Optional, Any
import redis.asyncio as aioredis
from app.config import settings

logger = logging.getLogger(__name__)

redis_client: Optional[aioredis.Redis] = None


async def get_redis_client() -> Optional[aioredis.Redis]:
    global redis_client
    if redis_client is None:
        try:
            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0
            )
            # Ping to verify
            await redis_client.ping()
            logger.info("Connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed (running in fallback mode): {e}")
            redis_client = None
    return redis_client


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> bool:
    """Store serialized JSON in cache with TTL."""
    try:
        r = await get_redis_client()
        if r:
            payload = json.dumps(value, default=str)
            await r.setex(key, ttl_seconds, payload)
            return True
    except Exception as e:
        logger.debug(f"Redis cache_set skipped: {e}")
    return False


async def cache_get(key: str) -> Optional[Any]:
    """Retrieve and deserialize JSON from cache."""
    try:
        r = await get_redis_client()
        if r:
            val = await r.get(key)
            if val:
                return json.loads(val)
    except Exception as e:
        logger.debug(f"Redis cache_get skipped: {e}")
    return None


async def cache_delete(pattern: str) -> None:
    """Invalidate cache keys matching a pattern."""
    try:
        r = await get_redis_client()
        if r:
            keys = await r.keys(pattern)
            if keys:
                await r.delete(*keys)
    except Exception as e:
        logger.debug(f"Redis cache_delete skipped: {e}")


async def publish_event(channel: str, message: dict) -> bool:
    """Publish event to Redis pub/sub channel."""
    try:
        r = await get_redis_client()
        if r:
            await r.publish(channel, json.dumps(message, default=str))
            return True
    except Exception as e:
        logger.debug(f"Redis pub/sub publish skipped: {e}")
    return False
