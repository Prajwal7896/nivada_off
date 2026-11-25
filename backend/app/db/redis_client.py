
import os
import logging

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)

redis_client: Redis | None = None


async def connect_redis() -> bool:
    global redis_client

    redis_url = os.getenv("REDIS_URL")

    if not redis_url:
        logger.warning("REDIS_URL is not configured")
        return False

    client = Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        health_check_interval=30,
    )

    try:
        await client.ping()
        redis_client = client
        logger.info("Redis connection established")
        return True

    except RedisError:
        logger.exception("Redis connection failed")
        await client.aclose()
        return False


async def check_redis() -> bool:
    if redis_client is None:
        return False

    try:
        return bool(await redis_client.ping())
    except RedisError:
        logger.exception("Redis health check failed")
        return False


async def close_redis() -> None:
    global redis_client

    if redis_client is not None:
        await redis_client.aclose()
        redis_client = None
        logger.info("Redis connection closed")
