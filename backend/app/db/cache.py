import json
import hashlib
import logging
from functools import wraps

import anyio
from backend.app.db import redis_client as redis_store
from backend.app.db.model import User

logger = logging.getLogger(__name__)
VERSION_KEY = "cache:complaints:version"
CACHE_TTL = 60


async def _set_cache(redis, key, value):
    await redis.set(key, value, ex=CACHE_TTL)


def cache_complaint_response(namespace):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            request = kwargs.get("request")
            db = kwargs.get("db")
            redis = redis_store.redis_client

            if request is None or db is None or redis is None:
                return func(*args, **kwargs)

            user_id = request.session.get("user_id")
            if not user_id:
                return func(*args, **kwargs)

            try:
                user_exists = db.query(User.id).filter(User.id == user_id).first()
            except Exception:
                return func(*args, **kwargs)

            if not user_exists:
                return func(*args, **kwargs)

            cache_key = None
            try:
                version = anyio.from_thread.run(redis.get, VERSION_KEY) or "0"
                filters = sorted(request.query_params.multi_items())
                raw_key = json.dumps(
                    [namespace, str(user_id), filters],
                    separators=(",", ":"),
                )
                digest = hashlib.sha256(raw_key.encode()).hexdigest()
                cache_key = f"cache:complaints:{version}:{namespace}:{digest}"

                cached = anyio.from_thread.run(redis.get, cache_key)
                if cached is not None:
                    try:
                        return json.loads(cached)
                    except (json.JSONDecodeError, TypeError):
                        logger.warning("Invalid dashboard cache entry")

            except Exception:
                logger.exception("Dashboard cache read failed; using database")

            result = func(*args, **kwargs)

            if cache_key:
                try:
                    anyio.from_thread.run(
                        _set_cache, redis, cache_key,
                        json.dumps(result, default=str),
                    )
                except Exception:
                    logger.exception("Dashboard cache write failed")

            return result

        return wrapper
    return decorator


def invalidate_complaint_cache():
    redis = redis_store.redis_client
    if redis is None:
        return
    try:
        anyio.from_thread.run(redis.incr, VERSION_KEY)
    except Exception:
        logger.exception("Complaint cache invalidation failed")


async def invalidate_complaint_cache_async():
    redis = redis_store.redis_client
    if redis is None:
        return
    try:
        await redis.incr(VERSION_KEY)
    except Exception:
        logger.exception("Complaint cache invalidation failed")
