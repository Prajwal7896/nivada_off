from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pathlib import Path
from prometheus_fastapi_instrumentator import Instrumentator
from app.auth.choose import router as choose_router
from app.auth.user.user_login import router as user_login_router
from app.auth.user.user_registration import router as user_registration_router
from app.auth.officer.offiice_registration import router as officer_registration_router
from app.auth.officer.officer_login import router as officer_login_router
from app.db.db import Base, engine
from app.db import model
from app.geo import router as geography_router
from app.complaint.complaints import router as complaints_router

from app.dashboard.user.user_profile import router as user_profile_router
from app.dashboard.user.complaint_submission import router as complaint_submission_router
from app.dashboard.user.user_complaints import router as user_complaints_router
from app.dashboard.user.map import router as map_router
from app.dashboard.user.insights import router as insights_router
from app.dashboard.user.user_complaints import router as user_dashboard_router
from app.dashboard.officer.officer_dashboard import router as officer_dashboard_router
from sqlalchemy import text

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="NIVADA")
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text(
            "ALTER TABLE villages ADD COLUMN IF NOT EXISTS geometry geometry(Geometry, 4326)"
        ))
        
@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    SessionMiddleware,
    secret_key="nivada-secret-key"
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
app.include_router(user_dashboard_router)
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000
    )