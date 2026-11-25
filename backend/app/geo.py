
import json
import logging

import anyio
from fastapi import APIRouter, Depends
from redis.exceptions import RedisError
from sqlalchemy.orm import Session

from backend.app.db.db import get_db
from backend.app.db.model import (
    Country,
    State,
    District,
    Taluka,
    Village,
    Department,
)
from backend.app.db import redis_client as redis_store


router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

CACHE_TTL = 3600
CACHE_VERSION = "v2"


async def _redis_set(redis, key: str, value: str):
    await redis.set(key, value, ex=CACHE_TTL)


def get_cached_data(cache_key: str, db_loader):
    """
    Read data from Redis first.
    If Redis misses or fails, fetch data from PostgreSQL.
    Cache the PostgreSQL result when Redis is available.
    """

    versioned_key = f"geo:{CACHE_VERSION}:{cache_key}"

    redis = redis_store.redis_client

    if redis is not None:
        try:
            cached_data = anyio.from_thread.run(
                redis.get,
                versioned_key,
            )

            # Check against None so an empty JSON list is also a valid cache hit.
            if cached_data is not None:
                try:
                    return json.loads(cached_data)
                except (json.JSONDecodeError, TypeError):
                    logger.warning(
                        "Invalid Redis cache for key: %s",
                        versioned_key,
                    )

        except RedisError:
            logger.exception(
                "Redis read failed for key: %s",
                versioned_key,
            )
        except RuntimeError:
            logger.exception(
                "Redis read execution failed for key: %s",
                versioned_key,
            )

    # PostgreSQL fallback
    data = db_loader()

    if redis is not None:
        try:
            serialized_data = json.dumps(data)

            anyio.from_thread.run(
                _redis_set,
                redis,
                versioned_key,
                serialized_data,
            )

        except RedisError:
            logger.exception(
                "Redis write failed for key: %s",
                versioned_key,
            )
        except RuntimeError:
            logger.exception(
                "Redis write execution failed for key: %s",
                versioned_key,
            )

    return data


@router.get("/departments")
def get_departments(db: Session = Depends(get_db)):
    return get_cached_data(
        "departments",
        lambda: [
            {"id": item.id, "name": item.name}
            for item in db.query(Department)
            .order_by(Department.name)
            .all()
        ],
    )


@router.get("/countries")
def get_countries(db: Session = Depends(get_db)):
    return get_cached_data(
        "countries",
        lambda: [
            {"id": item.id, "name": item.name}
            for item in db.query(Country)
            .order_by(Country.name)
            .all()
        ],
    )


@router.get("/states/{country_id}")
def get_states(country_id: int, db: Session = Depends(get_db)):
    return get_cached_data(
        f"states:{country_id}",
        lambda: [
            {"id": item.id, "name": item.name}
            for item in db.query(State)
            .filter(State.country_id == country_id)
            .order_by(State.name)
            .all()
        ],
    )


@router.get("/districts/{state_id}")
def get_districts(state_id: int, db: Session = Depends(get_db)):
    return get_cached_data(
        f"districts:{state_id}",
        lambda: [
            {"id": item.id, "name": item.name}
            for item in db.query(District)
            .filter(District.state_id == state_id)
            .order_by(District.name)
            .all()
        ],
    )


@router.get("/talukas/{district_id}")
def get_talukas(district_id: int, db: Session = Depends(get_db)):
    return get_cached_data(
        f"talukas:{district_id}",
        lambda: [
            {"id": item.id, "name": item.name}
            for item in db.query(Taluka)
            .filter(Taluka.district_id == district_id)
            .order_by(Taluka.name)
            .all()
        ],
    )


@router.get("/villages/{taluka_id}")
def get_villages(taluka_id: int, db: Session = Depends(get_db)):
    return get_cached_data(
        f"villages:{taluka_id}",
        lambda: [
            {"id": item.id, "name": item.name}
            for item in db.query(Village)
            .filter(Village.taluka_id == taluka_id)
            .order_by(Village.name)
            .all()
        ],
    )
