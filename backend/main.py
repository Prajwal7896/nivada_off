from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import text
import os
from backend.app.auth.choose import router as choose_router
from backend.app.auth.user.user_login import router as user_login_router
from backend.app.auth.user.user_registration import router as user_registration_router
from backend.app.auth.officer.offiice_registration import router as officer_registration_router
from backend.app.auth.officer.officer_login import router as officer_login_router
from backend.app.db.db import Base, engine
from backend.app.db.metrics import update_db_pool_metrics
from backend.app.db import model
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from backend.app.security.rate_limit import limiter
from backend.app.geo import router as geography_router
from backend.app.complaint.complaints import router as complaints_router
from contextlib import asynccontextmanager
from backend.app.db.redis_client import (
    connect_redis,
    check_redis,
    close_redis,
)
from backend.app.dashboard.user.user_profile import router as user_profile_router
from backend.app.dashboard.user.complaint_submission import router as complaint_submission_router
from backend.app.dashboard.user.user_complaints import router as user_complaints_router
from backend.app.dashboard.user.map import router as map_router
from backend.app.dashboard.user.insights import router as insights_router
from backend.app.dashboard.officer.officer_dashboard import router as officer_dashboard_router

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize database schema and PostGIS.
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(
            text(
                "ALTER TABLE villages ADD COLUMN IF NOT EXISTS geometry geometry(Geometry, 4326)"
            )
        )

    # Connect Redis; application can still start if Redis is unavailable.
    await connect_redis()

    try:
        yield
    finally:
        await close_redis()
app = FastAPI(
    title="NIVADA",
    lifespan=lifespan
)
app.state.limiter = limiter

app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler
)
@app.middleware("http")
async def refresh_database_metrics(request, call_next):
    update_db_pool_metrics()
    response = await call_next(request)
    update_db_pool_metrics()
    return response

@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = (
        "camera=(), microphone=(), geolocation=()"
    )
    if os.getenv("APP_ENV") == "production":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response

Instrumentator().instrument(app).expose(app)
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

if not SESSION_SECRET_KEY:
    raise RuntimeError("SESSION_SECRET_KEY is missing")

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    same_site="lax",
    https_only=os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
)

app.mount(
    "/static",
    StaticFiles(directory=FRONTEND_DIR),
    name="static"
)

app.include_router(user_complaints_router)
app.include_router(officer_login_router)
app.include_router(officer_registration_router)
app.include_router(choose_router)
app.include_router(user_login_router)
app.include_router(user_registration_router)
app.include_router(geography_router)
app.include_router(complaints_router)

app.include_router(user_profile_router)
app.include_router(complaint_submission_router)
app.include_router(officer_dashboard_router)
app.include_router(map_router)
app.include_router(insights_router)


@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/redis")
async def redis_health():
    connected = await check_redis()

    return {
        "redis": "connected" if connected else "disconnected"
    }

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )
