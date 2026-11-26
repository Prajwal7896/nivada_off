import os
import ipaddress

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL")
APP_ENV = os.getenv("APP_ENV", "development").lower()

if APP_ENV == "production" and not REDIS_URL:
    raise RuntimeError(
        "REDIS_URL is required for production rate limiting"
    )


def get_client_ip(request: Request) -> str:
    if APP_ENV == "production":
        forwarded_ip = request.headers.get("cf-connecting-ip")

        if forwarded_ip:
            try:
                return str(ipaddress.ip_address(forwarded_ip.strip()))
            except ValueError:
                pass

    return get_remote_address(request)


limiter = Limiter(
    key_func=get_client_ip,
    storage_uri=REDIS_URL or "memory://",
    default_limits=[]
)
