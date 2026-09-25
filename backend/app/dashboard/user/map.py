from fastapi import APIRouter, Depends, Request, HTTPException
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import text
from pathlib import Path
import json

from app.db.db import get_db
from app.db.model import (
    Complaint,
    ComplaintCategory,
    Country,
    State,
    District,
    Taluka,
    Village,
    Department
)
router = APIRouter()
BASE_DIR = Path(__file__).resolve().parents[4]
FRONTEND_DIR = BASE_DIR / "frontend"

templates = Jinja2Templates(
    directory=str(FRONTEND_DIR)
)


@router.get("/user/map")
def user_map(request: Request):
    return templates.TemplateResponse(
        request,
        "user/map.html"
    )

def get_current_user(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User not authenticated"
        )

    return user_id


@router.get("/api/user/options")
def get_filter_options(
    request: Request,
    db: Session = Depends(get_db)
):
    get_current_user(request)

    categories = (
        db.query(ComplaintCategory)
        .order_by(ComplaintCategory.name.asc())
        .all()
    )

    statuses = (
        db.query(Complaint.status)
        .filter(Complaint.status.isnot(None))
        .distinct()
        .order_by(Complaint.status.asc())
        .all()
    )

    priorities = (
        db.query(Complaint.priority)
        .filter(Complaint.priority.isnot(None))
        .distinct()
        .order_by(Complaint.priority.asc())
        .all()
    )

    return {
        "categories": [
            {
                "id": category.id,
                "name": category.name
            }
            for category in categories
        ],
        "statuses": [
            row[0]
            for row in statuses
        ],
        "priorities": [
            row[0]
            for row in priorities
        ]
    }
@router.get("/api/user/geography/location")
def get_geography_location(
    country_id: int | None = None,
    state_id: int | None = None,
    district_id: int | None = None,
    taluka_id: int | None = None,
    village_id: int | None = None,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    if village_id is not None:
        village = db.query(Village).filter(Village.id == village_id).first()

        if not village:
            raise HTTPException(status_code=404, detail="Village not found")

        result = db.execute(
            text("""
                SELECT
                    ST_Y(ST_Centroid(geometry)) AS latitude,
                    ST_X(ST_Centroid(geometry)) AS longitude
                FROM villages
                WHERE id = :id
                  AND geometry IS NOT NULL
            """),
            {"id": village_id}
        ).mappings().first()

        if not result or result["latitude"] is None or result["longitude"] is None:
            raise HTTPException(
                status_code=404,
                detail="Village geometry not available"
            )

        return {
            "latitude": float(result["latitude"]),
            "longitude": float(result["longitude"]),
            "zoom": 13,
            "level": "village",
            "name": village.name
        }

    if taluka_id is not None:
        result = db.execute(
            text("""
                SELECT
                    ST_Y(ST_Centroid(ST_Union(geometry))) AS latitude,
                    ST_X(ST_Centroid(ST_Union(geometry))) AS longitude
                FROM villages
                WHERE taluka_id = :id
                  AND geometry IS NOT NULL
            """),
            {"id": taluka_id}
        ).mappings().first()

        if not result or result["latitude"] is None:
            raise HTTPException(
                status_code=404,
                detail="Taluka geometry not available"
            )

        taluka = db.query(Taluka).filter(Taluka.id == taluka_id).first()

        return {
            "latitude": float(result["latitude"]),
            "longitude": float(result["longitude"]),
            "zoom": 11,
            "level": "taluka",
            "name": taluka.name if taluka else ""
        }

    if district_id is not None:
        result = db.execute(
            text("""
                SELECT
                    ST_Y(ST_Centroid(ST_Union(v.geometry))) AS latitude,
                    ST_X(ST_Centroid(ST_Union(v.geometry))) AS longitude
                FROM villages v
                JOIN talukas t ON v.taluka_id = t.id
                WHERE t.district_id = :id
                  AND v.geometry IS NOT NULL
            """),
            {"id": district_id}
        ).mappings().first()

        if not result or result["latitude"] is None:
            raise HTTPException(
                status_code=404,
                detail="District geometry not available"
            )

        district = db.query(District).filter(
            District.id == district_id
        ).first()

        return {
            "latitude": float(result["latitude"]),
            "longitude": float(result["longitude"]),
            "zoom": 10,
            "level": "district",
            "name": district.name if district else ""
        }

    if state_id is not None:
        result = db.execute(
            text("""
                SELECT
                    ST_Y(ST_Centroid(ST_Union(v.geometry))) AS latitude,
                    ST_X(ST_Centroid(ST_Union(v.geometry))) AS longitude
                FROM villages v
                JOIN talukas t ON v.taluka_id = t.id
                JOIN districts d ON t.district_id = d.id
                WHERE d.state_id = :id
                  AND v.geometry IS NOT NULL
            """),
            {"id": state_id}
        ).mappings().first()

        if not result or result["latitude"] is None:
            raise HTTPException(
                status_code=404,
                detail="State geometry not available"
            )

        state = db.query(State).filter(
            State.id == state_id
        ).first()

        return {
            "latitude": float(result["latitude"]),
            "longitude": float(result["longitude"]),
            "zoom": 7,
            "level": "state",
            "name": state.name if state else ""
        }

    if country_id is not None:
        result = db.execute(
            text("""
                SELECT
                    ST_Y(ST_Centroid(ST_Union(v.geometry))) AS latitude,
                    ST_X(ST_Centroid(ST_Union(v.geometry))) AS longitude
                FROM villages v
                JOIN talukas t ON v.taluka_id = t.id
                JOIN districts d ON t.district_id = d.id
                JOIN states s ON d.state_id = s.id
                WHERE s.country_id = :id
                  AND v.geometry IS NOT NULL
            """),
            {"id": country_id}
        ).mappings().first()

        if not result or result["latitude"] is None:
            raise HTTPException(
                status_code=404,
                detail="Country geometry not available"
            )

        country = db.query(Country).filter(
            Country.id == country_id
        ).first()

        return {
            "latitude": float(result["latitude"]),
            "longitude": float(result["longitude"]),
            "zoom": 5,
            "level": "country",
            "name": country.name if country else ""
        }

    return {
        "latitude": 20.5937,
        "longitude": 78.9629,
        "zoom": 5,
        "level": "world",
        "name": "All Locations"
    }

@router.get("/api/user/geography")
def get_geography(
    request: Request,
    country_id: int | None = None,
    state_id: int | None = None,
    district_id: int | None = None,
    taluka_id: int | None = None,
    db: Session = Depends(get_db)
):
    get_current_user(request)

    if taluka_id:
        villages = (
            db.query(Village)
            .filter(Village.taluka_id == taluka_id)
            .order_by(Village.name.asc())
            .all()
        )

        return {
            "villages": [
                {
                    "id": village.id,
                    "name": village.name
                }
                for village in villages
            ]
        }

    if district_id:
        talukas = (
            db.query(Taluka)
            .filter(Taluka.district_id == district_id)
            .order_by(Taluka.name.asc())
            .all()
        )

        return {
            "talukas": [
                {
                    "id": taluka.id,
                    "name": taluka.name
                }
                for taluka in talukas
            ]
        }

    if state_id:
        districts = (
            db.query(District)
            .filter(District.state_id == state_id)
            .order_by(District.name.asc())
            .all()
        )

        return {
            "districts": [
                {
                    "id": district.id,
                    "name": district.name
                }
                for district in districts
            ]
        }

    if country_id:
        states = (
            db.query(State)
            .filter(State.country_id == country_id)
            .order_by(State.name.asc())
            .all()
        )

        return {
            "states": [
                {
                    "id": state.id,
                    "name": state.name
                }
                for state in states
            ]
        }

    countries = (
        db.query(Country)
        .order_by(Country.name.asc())
        .all()
    )

    return {
        "countries": [
            {
                "id": country.id,
                "name": country.name
            }
            for country in countries
        ]
    }


@router.get("/api/user/map")
def get_map_data(
    request: Request,
    country_id: int | None = None,
    state_id: int | None = None,
    district_id: int | None = None,
    taluka_id: int | None = None,
    village_id: int | None = None,
    category_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    db: Session = Depends(get_db)
):
    get_current_user(request)

    query = db.query(Complaint)

    if country_id:
        query = query.filter(
            Complaint.country_id == country_id
        )

    if state_id:
        query = query.filter(
            Complaint.state_id == state_id
        )

    if district_id:
        query = query.filter(
            Complaint.district_id == district_id
        )

    if taluka_id:
        query = query.filter(
            Complaint.taluka_id == taluka_id
        )

    if village_id:
        query = query.filter(
            Complaint.village_id == village_id
        )

    if category_id:
        query = query.filter(
            Complaint.category_id == category_id
        )

    if status:
        query = query.filter(
            Complaint.status == status
        )

    if priority:
        query = query.filter(
            Complaint.priority == priority
        )

    complaints = query.order_by(
        Complaint.timestamp.desc()
    ).all()

    markers = []

    for complaint in complaints:
        if complaint.latitude is None or complaint.longitude is None:
            continue

        category_name = None

        if complaint.category_id:
            category = (
                db.query(ComplaintCategory)
                .filter(
                    ComplaintCategory.id == complaint.category_id
                )
                .first()
            )

            if category:
                category_name = category.name

        markers.append({
            "id": complaint.id,
            "latitude": complaint.latitude,
            "longitude": complaint.longitude,
            "category": category_name,
            "category_name": category_name,
            "category_id": complaint.category_id,
            "status": complaint.status,
            "priority": complaint.priority,
            "complaint_text": complaint.complaint_text,
            "ai_confidence": complaint.ai_confidence,
            "timestamp": complaint.timestamp.isoformat()
            if complaint.timestamp
            else None,
            "address": complaint.address
        })

    boundaries = None

    if village_id:
        boundary_query = text("""
            SELECT ST_AsGeoJSON(geometry)
            FROM villages
            WHERE id = :id
              AND geometry IS NOT NULL
            LIMIT 1
        """)

        result = db.execute(
            boundary_query,
            {"id": village_id}
        ).scalar()

        if result:
            boundaries = {
                "type": "Feature",
                "properties": {
                    "type": "village",
                    "id": village_id
                },
                "geometry": __import__("json").loads(result)
            }

    elif taluka_id:
        boundary_query = text("""
            SELECT ST_AsGeoJSON(ST_Union(geometry))
            FROM villages
            WHERE taluka_id = :id
              AND geometry IS NOT NULL
        """)

        result = db.execute(
            boundary_query,
            {"id": taluka_id}
        ).scalar()

        if result:
            boundaries = {
                "type": "Feature",
                "properties": {
                    "type": "taluka",
                    "id": taluka_id
                },
                "geometry": __import__("json").loads(result)
            }

    elif district_id:
        boundary_query = text("""
            SELECT ST_AsGeoJSON(ST_Union(geometry))
            FROM villages v
            JOIN talukas t ON t.id = v.taluka_id
            WHERE t.district_id = :id
              AND v.geometry IS NOT NULL
        """)

        result = db.execute(
            boundary_query,
            {"id": district_id}
        ).scalar()

        if result:
            boundaries = {
                "type": "Feature",
                "properties": {
                    "type": "district",
                    "id": district_id
                },
                "geometry": __import__("json").loads(result)
            }

    elif state_id:
        boundary_query = text("""
            SELECT ST_AsGeoJSON(ST_Union(geometry))
            FROM villages v
            JOIN talukas t ON t.id = v.taluka_id
            JOIN districts d ON d.id = t.district_id
            WHERE d.state_id = :id
              AND v.geometry IS NOT NULL
        """)

        result = db.execute(
            boundary_query,
            {"id": state_id}
        ).scalar()

        if result:
            boundaries = {
                "type": "Feature",
                "properties": {
                    "type": "state",
                    "id": state_id
                },
                "geometry": __import__("json").loads(result)
            }

    elif country_id:
        boundary_query = text("""
            SELECT ST_AsGeoJSON(ST_Union(geometry))
            FROM villages v
            JOIN talukas t ON t.id = v.taluka_id
            JOIN districts d ON d.id = t.district_id
            JOIN states s ON s.id = d.state_id
            WHERE s.country_id = :id
              AND v.geometry IS NOT NULL
        """)

        result = db.execute(
            boundary_query,
            {"id": country_id}
        ).scalar()

        if result:
            boundaries = {
                "type": "Feature",
                "properties": {
                    "type": "country",
                    "id": country_id
                },
                "geometry": __import__("json").loads(result)
            }

    location = {}

    if village_id:
        row = (
            db.query(
                Village.id,
                Village.name,
                Taluka.id.label("taluka_id"),
                Taluka.name.label("taluka"),
                District.id.label("district_id"),
                District.name.label("district"),
                State.id.label("state_id"),
                State.name.label("state"),
                Country.id.label("country_id"),
                Country.name.label("country")
            )
            .join(Taluka, Taluka.id == Village.taluka_id)
            .join(District, District.id == Taluka.district_id)
            .join(State, State.id == District.state_id)
            .join(Country, Country.id == State.country_id)
            .filter(Village.id == village_id)
            .first()
        )

        if row:
            location = {
                "village": row.name,
                "village_id": row.id,
                "taluka": row.taluka,
                "taluka_id": row.taluka_id,
                "district": row.district,
                "district_id": row.district_id,
                "state": row.state,
                "state_id": row.state_id,
                "country": row.country,
                "country_id": row.country_id
            }

    return {
        "complaints": markers,
        "markers": markers,
        "boundaries": boundaries,
        "location": location
    }


@router.get("/api/user/insights")
def get_insights(
    request: Request,
    country_id: int | None = None,
    state_id: int | None = None,
    district_id: int | None = None,
    taluka_id: int | None = None,
    village_id: int | None = None,
    category_id: int | None = None,
    status: str | None = None,
    priority: str | None = None,
    db: Session = Depends(get_db)
):
    get_current_user(request)

    query = db.query(Complaint)

    if country_id:
        query = query.filter(Complaint.country_id == country_id)

    if state_id:
        query = query.filter(Complaint.state_id == state_id)

    if district_id:
        query = query.filter(Complaint.district_id == district_id)

    if taluka_id:
        query = query.filter(Complaint.taluka_id == taluka_id)

    if village_id:
        query = query.filter(Complaint.village_id == village_id)

    if category_id:
        query = query.filter(Complaint.category_id == category_id)

    if status:
        query = query.filter(Complaint.status == status)

    if priority:
        query = query.filter(Complaint.priority == priority)

    complaints = query.all()

    total = len(complaints)

    pending = sum(
        1 for c in complaints
        if str(c.status).lower() == "pending"
    )

    in_progress = sum(
        1 for c in complaints
        if str(c.status).lower() in {
            "in progress",
            "in_progress"
        }
    )

    resolved = sum(
        1 for c in complaints
        if str(c.status).lower() == "resolved"
    )

    category_counts = {}

    for complaint in complaints:
        if complaint.category_id:
            category = (
                db.query(ComplaintCategory)
                .filter(
                    ComplaintCategory.id == complaint.category_id
                )
                .first()
            )

            name = category.name if category else "Unknown"
        else:
            name = "Unknown"

        category_counts[name] = (
            category_counts.get(name, 0) + 1
        )

    category_distribution = [
        {
            "name": name,
            "count": count
        }
        for name, count in category_counts.items()
    ]

    category_distribution.sort(
        key=lambda x: x["count"],
        reverse=True
    )

    return {
        "summary": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "resolved": resolved
        },
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "category_distribution": category_distribution
    }