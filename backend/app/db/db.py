
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import time
from sqlalchemy import event
from backend.app.db.metrics import (
    db_query_total,
    db_query_errors_total,
    db_query_duration,
    db_slow_queries_total,
    db_slow_query_duration,
    SLOW_QUERY_THRESHOLD_SECONDS,
)
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is missing")

POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "5"))
POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_recycle=POOL_RECYCLE,
    pool_use_lifo=True,
)
@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(
    conn, cursor, statement, parameters, context, executemany
):
    context._civix_query_start = time.perf_counter()

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(
    conn, cursor, statement, parameters, context, executemany
):
    start = getattr(context, "_civix_query_start", None)

    if start is not None:
        duration = time.perf_counter() - start
        operation = statement.lstrip().split(None, 1)[0].upper()

        db_query_total.labels(operation=operation).inc()
        db_query_duration.labels(operation=operation).observe(duration)

        if duration >= SLOW_QUERY_THRESHOLD_SECONDS:
            db_slow_queries_total.labels(operation=operation).inc()
            db_slow_query_duration.labels(operation=operation).observe(duration)


@event.listens_for(engine, "handle_error")
def handle_query_error(exception_context):
    statement = exception_context.statement or ""
    operation = statement.lstrip().split(None, 1)[0].upper() if statement.strip() else "UNKNOWN"

    db_query_total.labels(operation=operation).inc()
    db_query_errors_total.labels(operation=operation).inc()
    
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
