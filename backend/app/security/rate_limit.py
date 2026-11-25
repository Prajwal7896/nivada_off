
import os

from slowapi import Limiter
from slowapi.util import get_remote_address

REDIS_URL = os.getenv("REDIS_URL")
APP_ENV = os.getenv("APP_ENV", "development").lower()

if APP_ENV == "production" and not REDIS_URL:
    raise RuntimeError(
        "REDIS_URL is required for production rate limiting"
    )

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL or "memory://",
    default_limits=[]
)
