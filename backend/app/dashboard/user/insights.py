from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import csv, io
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.db.db import get_db
from backend.app.db.model import User, Complaint, ComplaintCategory, Department, ComplaintHistory, Country, State, District, Taluka, Village

from backend.app.db.cache import cache_complaint_response

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parents[4]
FRONTEND_USER_DIR = BASE_DIR / "frontend" / "user"

def get_current_user(request: Request, db: Session):
    user_id = request.session.get("user_id")
    if not user_id: raise HTTPException(status_code=401, detail="User not authenticated")
    user = db.query(User).filter(User.id == user_id).first()
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user

def normalize_filter(value):
    if value is None: return None
    value = str(value).strip()
    return None if not value or value.lower() == "all" else value


def validate_insight_filters(
    country_id=None,
    state_id=None,
    district_id=None,
    taluka_id=None,
    village_id=None,
    category_id=None,
    department_id=None,
    status=None,
    priority=None,
    days=30
):
    if not 0 <= days <= 3650:
        raise HTTPException(
            status_code=400,
            detail="Days must be between 0 and 3650"
        )

    for name, value in (
        ("country_id", country_id),
        ("state_id", state_id),
        ("district_id", district_id),
        ("taluka_id", taluka_id),
        ("village_id", village_id),
        ("category_id", category_id),
        ("department_id", department_id),
    ):
        if value is not None and value < 1:
            raise HTTPException(
                status_code=400,
                detail=f"{name} must be a positive integer"
            )

    normalized_status = normalize_filter(status)
    normalized_priority = normalize_filter(priority)

    if normalized_status is not None and normalized_status.lower() not in {
        "pending", "in_progress", "resolved", "rejected"
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid status filter"
        )

    if normalized_priority is not None and normalized_priority.lower() not in {
        "high", "medium", "low"
    }:
        raise HTTPException(
            status_code=400,
            detail="Invalid priority filter"
        )

def apply_location_filters(query, country_id=None, state_id=None, district_id=None, taluka_id=None, village_id=None):
    if country_id is not None: query = query.filter(Complaint.country_id == country_id)
    if state_id is not None: query = query.filter(Complaint.state_id == state_id)
    if district_id is not None: query = query.filter(Complaint.district_id == district_id)
    if taluka_id is not None: query = query.filter(Complaint.taluka_id == taluka_id)
    if village_id is not None: query = query.filter(Complaint.village_id == village_id)
    return query

def apply_complaint_filters(query, country_id=None, state_id=None, district_id=None, taluka_id=None, village_id=None, category_id=None, department_id=None, status=None, priority=None, days=None):
    query = apply_location_filters(query, country_id, state_id, district_id, taluka_id, village_id)
    if category_id is not None: query = query.filter(Complaint.category_id == category_id)
    if department_id is not None: query = query.filter(Complaint.department_id == department_id)
    status, priority = normalize_filter(status), normalize_filter(priority)
    if status is not None: query = query.filter(func.lower(Complaint.status) == status.lower())
    if priority is not None: query = query.filter(func.lower(Complaint.priority) == priority.lower())
    if days is not None and days > 0: query = query.filter(Complaint.timestamp >= datetime.utcnow() - timedelta(days=days))
    return query

def get_location(db: Session, country_id=None, state_id=None, district_id=None, taluka_id=None, village_id=None):
    for model, v_id, name in [(Village, village_id, "Unknown Village"), (Taluka, taluka_id, "Unknown Taluka"), (District, district_id, "Unknown District"), (State, state_id, "Unknown State"), (Country, country_id, "Unknown Country")]:
        if v_id is not None:
            item = db.query(model).filter(model.id == v_id).first()
            return {"level": model.__name__.lower(), "id": item.id if item else v_id, "name": item.name if item else name}
    return {"level": "all", "id": None, "name": "All Areas"}

def calculate_ageing(complaints):
    result = {"0_3": 0, "4_7": 0, "8_15": 0, "15_plus": 0}
    now = datetime.utcnow()
    for c in complaints:
        if not c.timestamp: continue
        ts = c.timestamp.replace(tzinfo=None) if c.timestamp.tzinfo else c.timestamp
        age = max(0, (now - ts).days)
        key = "0_3" if age <= 3 else ("4_7" if age <= 7 else ("8_15" if age <= 15 else "15_plus"))
        result[key] += 1
    return result

def calculate_resolution_times(complaints, category_lookup):
    grouped = {}
    for c in complaints:
        if c.status != "resolved" or not c.timestamp or not c.updated_at: continue
        start = c.timestamp.replace(tzinfo=None) if c.timestamp.tzinfo else c.timestamp
        end = c.updated_at.replace(tzinfo=None) if c.updated_at.tzinfo else c.updated_at
        days = max(0, (end - start).total_seconds() / 86400)
        grouped.setdefault(category_lookup.get(c.category_id, "Unknown"), []).append(days)
    result = [{"category": cat, "days": round(sum(vals) / len(vals), 2)} for cat, vals in grouped.items()]
    result.sort(key=lambda x: x["days"], reverse=True)
    return result

def build_ai_insights(category_distribution, category_priority, current_complaints, previous_complaints, category_lookup):
    top_issue = category_distribution[0] if category_distribution else None
    def get_counts(items):
        counts = {}
        for item in items:
            category = category_lookup.get(item.category_id, "Unknown")
            counts[category] = counts.get(category, 0) + 1
        return counts
    
    curr_counts = get_counts(current_complaints)
    prev_counts = get_counts(previous_complaints)
    emerging = max([{"category": cat, "current": cur, "previous": prev_counts.get(cat, 0), "growth": round((cur - prev_counts.get(cat, 0)) / prev_counts.get(cat, 0) * 100 if prev_counts.get(cat, 0) > 0 else (100 if cur > 0 else 0), 2)} for cat, cur in curr_counts.items()], key=lambda x: x["growth"], default=None)
    
    high_priority = max([{"category": cat, "high": vals.get("high", 0), "total": sum(vals.values()), "percentage": round(vals.get("high", 0) / sum(vals.values()) * 100, 2)} for cat, vals in category_priority.items() if sum(vals.values()) > 0], key=lambda x: x["percentage"], default=None)

    return {
        "top_issue": {"category": top_issue["name"] if top_issue else "No Data", "count": top_issue["count"] if top_issue else 0},
        "emerging_issue": emerging if emerging else {"category": "No Data", "current": 0, "previous": 0, "growth": 0},
        "high_priority_issue": high_priority if high_priority else {"category": "No Data", "high": 0, "total": 0, "percentage": 0}
    }

@router.get("/user/insights")
def insights_page(request: Request):
    return FileResponse(FRONTEND_USER_DIR / ("insights.html" if request.session.get("user_id") else "user_login.html"))

@router.get("/api/user/insights")
@cache_complaint_response("user_insights")
def get_insights(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, category_id: Optional[int] = None, department_id: Optional[int] = None, status: Optional[str] = None, priority: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    validate_insight_filters(
        country_id, state_id, district_id, taluka_id, village_id,
        category_id, department_id, status, priority, days
    )
    days = max(0, days)
    base_query = apply_complaint_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id, category_id, None, status, priority, days)
    current_time = datetime.utcnow()
    
    category_rows = base_query.outerjoin(ComplaintCategory, Complaint.category_id == ComplaintCategory.id).with_entities(ComplaintCategory.id, func.coalesce(ComplaintCategory.name, "Processing"), func.count(Complaint.id)).group_by(ComplaintCategory.id, ComplaintCategory.name).order_by(func.count(Complaint.id).desc()).all()
    category_distribution = [{"id": r[0], "name": r[1], "count": r[2]} for r in category_rows]

    summary_row = base_query.with_entities(
        func.count(Complaint.id),
        func.count(Complaint.id).filter(Complaint.status == "pending"),
        func.count(Complaint.id).filter(Complaint.status == "in_progress"),
        func.count(Complaint.id).filter(Complaint.status == "resolved"),
        func.count(Complaint.id).filter(Complaint.status == "rejected"),
        func.avg(
            func.greatest(
                0,
                func.extract("epoch", Complaint.updated_at - Complaint.timestamp) / 86400.0
            )
        ).filter(
            Complaint.status == "resolved",
            Complaint.timestamp.isnot(None),
            Complaint.updated_at.isnot(None)
        )
    ).one()

    total, pending, in_progress, resolved, rejected = (
        int(value or 0) for value in summary_row[:5]
    )
    resolution_rate = round((resolved / total) * 100, 2) if total else 0
    avg_resolution_time = round(float(summary_row[5] or 0), 2)

    status_distribution = {
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "rejected": rejected
    }

    priority_rows = base_query.with_entities(
        func.coalesce(func.lower(Complaint.priority), "unknown"),
        func.count(Complaint.id)
    ).group_by(
        func.coalesce(func.lower(Complaint.priority), "unknown")
    ).all()

    priority_distribution = {"high": 0, "medium": 0, "low": 0}
    for priority_name, count in priority_rows:
        priority_distribution[priority_name] = int(count)

    department_rows = apply_complaint_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id, category_id, department_id, status, priority, days).outerjoin(Department, Complaint.department_id == Department.id).with_entities(Department.id, func.coalesce(Department.name, "Processing"), func.count(Complaint.id)).group_by(Department.id, Department.name).order_by(func.count(Complaint.id).desc()).all()
    department_distribution = [{"id": r[0], "name": r[1], "count": r[2]} for r in department_rows]

    trend_rows = base_query.with_entities(func.date_trunc("day", Complaint.timestamp).label("date"), func.count(Complaint.id)).group_by("date").order_by("date").all()
    monthly_trend = [{"date": r[0].strftime("%Y-%m-%d"), "count": r[1]} for r in trend_rows if r[0]]

    category_rows = base_query.outerjoin(
        ComplaintCategory, Complaint.category_id == ComplaintCategory.id
    ).with_entities(
        func.coalesce(ComplaintCategory.name, "Unknown").label("category"),
        func.lower(func.coalesce(Complaint.status, "")).label("status"),
        func.lower(func.coalesce(Complaint.priority, "")).label("priority"),
        func.count(Complaint.id).label("count")
    ).group_by(
        func.coalesce(ComplaintCategory.name, "Unknown"),
        func.lower(func.coalesce(Complaint.status, "")),
        func.lower(func.coalesce(Complaint.priority, ""))
    ).all()

    category_status, category_priority = {}, {}
    for category, status_value, priority_value, count in category_rows:
        category_status.setdefault(
            category, {"pending": 0, "in_progress": 0, "resolved": 0, "rejected": 0}
        )
        category_priority.setdefault(
            category, {"high": 0, "medium": 0, "low": 0}
        )
        if status_value in category_status[category]:
            category_status[category][status_value] += int(count)
        if priority_value in category_priority[category]:
            category_priority[category][priority_value] += int(count)

    age_days = func.greatest(
        0,
        func.floor(
            func.extract("epoch", current_time - Complaint.timestamp) / 86400.0
        )
    )

    ageing_row = base_query.filter(
        Complaint.status == "pending",
        Complaint.timestamp.isnot(None)
    ).with_entities(
        func.count(Complaint.id).filter(age_days <= 3),
        func.count(Complaint.id).filter(age_days > 3, age_days <= 7),
        func.count(Complaint.id).filter(age_days > 7, age_days <= 15),
        func.count(Complaint.id).filter(age_days > 15)
    ).one()

    ageing = {
        "0_3": int(ageing_row[0] or 0),
        "4_7": int(ageing_row[1] or 0),
        "8_15": int(ageing_row[2] or 0),
        "15_plus": int(ageing_row[3] or 0)
    }

    resolution_rows = base_query.outerjoin(
        ComplaintCategory,
        Complaint.category_id == ComplaintCategory.id
    ).filter(
        Complaint.status == "resolved",
        Complaint.timestamp.isnot(None),
        Complaint.updated_at.isnot(None)
    ).with_entities(
        func.coalesce(ComplaintCategory.name, "Unknown"),
        func.avg(
            func.greatest(
                0,
                func.extract(
                    "epoch", Complaint.updated_at - Complaint.timestamp
                ) / 86400.0
            )
        )
    ).group_by(
        func.coalesce(ComplaintCategory.name, "Unknown")
    ).all()

    resolution_time = [
        {"category": category, "days": round(float(avg_days or 0), 2)}
        for category, avg_days in resolution_rows
    ]
    resolution_time.sort(key=lambda item: item["days"], reverse=True)
    confidence_row = base_query.with_entities(
        func.count(Complaint.id).filter(
            Complaint.ai_confidence.isnot(None),
            Complaint.ai_confidence * 100 < 60
        ),
        func.count(Complaint.id).filter(
            Complaint.ai_confidence * 100 >= 60,
            Complaint.ai_confidence * 100 < 70
        ),
        func.count(Complaint.id).filter(
            Complaint.ai_confidence * 100 >= 70,
            Complaint.ai_confidence * 100 < 80
        ),
        func.count(Complaint.id).filter(
            Complaint.ai_confidence * 100 >= 80,
            Complaint.ai_confidence * 100 < 90
        ),
        func.count(Complaint.id).filter(
            Complaint.ai_confidence * 100 >= 90,
            Complaint.ai_confidence * 100 < 95
        ),
        func.count(Complaint.id).filter(
            Complaint.ai_confidence * 100 >= 95
        )
    ).one()

    confidence_distribution = [int(value or 0) for value in confidence_row]

    current_start = datetime.utcnow() - timedelta(days=days)

    previous_query = apply_location_filters(
        db.query(Complaint),
        country_id, state_id, district_id, taluka_id, village_id
    )
    if category_id is not None:
        previous_query = previous_query.filter(Complaint.category_id == category_id)
    if department_id is not None:
        previous_query = previous_query.filter(Complaint.department_id == department_id)

    previous_rows = previous_query.filter(
        Complaint.timestamp >= current_start - timedelta(days=days),
        Complaint.timestamp < current_start
    ).outerjoin(
        ComplaintCategory,
        Complaint.category_id == ComplaintCategory.id
    ).with_entities(
        func.coalesce(ComplaintCategory.name, "Unknown"),
        func.count(Complaint.id)
    ).group_by(
        func.coalesce(ComplaintCategory.name, "Unknown")
    ).all()

    prev_counts = {category: int(count) for category, count in previous_rows}
    curr_counts = {
        row["name"]: int(row["count"])
        for row in category_distribution
    }

    emerging = max(
        [
            {
                "category": category,
                "current": current,
                "previous": prev_counts.get(category, 0),
                "growth": round(
                    (current - prev_counts.get(category, 0))
                    / prev_counts.get(category, 0) * 100
                    if prev_counts.get(category, 0) > 0
                    else (100 if current > 0 else 0),
                    2
                )
            }
            for category, current in curr_counts.items()
        ],
        key=lambda item: item["growth"],
        default=None
    )

    top_issue = category_distribution[0] if category_distribution else None
    high_priority = max(
        [
            {
                "category": category,
                "high": values.get("high", 0),
                "total": sum(values.values()),
                "percentage": round(
                    values.get("high", 0) / sum(values.values()) * 100, 2
                )
            }
            for category, values in category_priority.items()
            if sum(values.values()) > 0
        ],
        key=lambda item: item["percentage"],
        default=None
    )

    ai_insights = {
        "top_issue": {
            "category": top_issue["name"] if top_issue else "No Data",
            "count": top_issue["count"] if top_issue else 0
        },
        "emerging_issue": emerging if emerging else {
            "category": "No Data", "current": 0, "previous": 0, "growth": 0
        },
        "high_priority_issue": high_priority if high_priority else {
            "category": "No Data", "high": 0, "total": 0, "percentage": 0
        }
    }

    emerging_issues = []
    for category, current in curr_counts.items():
        previous = prev_counts.get(category, 0)
        change = (
            ((current - previous) / previous) * 100
            if previous else (100 if current else 0)
        )
        trend = "Increasing" if change > 0 else (
            "Declining" if change < 0 else "Stable"
        )
        emerging_issues.append({
            "issue": category,
            "current": current,
            "previous": previous,
            "change": round(change, 2),
            "trend": trend
        })
    emerging_issues.sort(key=lambda item: item["change"], reverse=True)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "filters": {"country_id": country_id, "state_id": state_id, "district_id": district_id, "taluka_id": taluka_id, "village_id": village_id, "category_id": category_id, "department_id": department_id, "status": status, "priority": priority, "days": days},
        "summary": {"total": total, "pending": pending, "in_progress": in_progress, "resolved": resolved, "rejected": rejected, "resolution_rate": resolution_rate, "avg_resolution_time": avg_resolution_time, "sla_compliance": None},
        "status_distribution": status_distribution, "priority_distribution": priority_distribution, "category_distribution": category_distribution,
        "department_distribution": department_distribution, "monthly_trend": monthly_trend, "category_status": category_status, "category_priority": category_priority,
        "ageing": ageing, "resolution_time": resolution_time, "ai_confidence": confidence_distribution, "ai_insights": ai_insights, "emerging_issues": emerging_issues[:10],
        "location": get_location(db, country_id, state_id, district_id, taluka_id, village_id)
    }

@router.get("/api/user/insights/options")
def get_filter_options(request: Request, db: Session = Depends(get_db)):
    get_current_user(request, db)
    categories = db.query(ComplaintCategory.id, ComplaintCategory.name).order_by(ComplaintCategory.name).all()
    departments = db.query(Department.id, Department.name).order_by(Department.name).all()
    return {"categories": [{"id": r[0], "name": r[1]} for r in categories], "departments": [{"id": r[0], "name": r[1]} for r in departments]}

@router.get("/api/user/insights/geography")
def get_geography(request: Request, level: str, parent_id: Optional[int] = None, db: Session = Depends(get_db)):
    get_current_user(request, db)
    level = level.lower().strip()
    models = {"country": Country, "state": State, "district": District, "taluka": Taluka, "village": Village}
    if level not in models: raise HTTPException(status_code=400, detail="Invalid geography level")
    model = models[level]
    query = db.query(model.id, model.name)
    if parent_id is not None and level != "country":
        foreign_keys = {"state": State.country_id, "district": District.state_id, "taluka": Taluka.district_id, "village": Village.taluka_id}
        query = query.filter(foreign_keys[level] == parent_id)
    return [{"id": r[0], "name": r[1]} for r in query.order_by(model.name).all()]

@router.get("/api/user/insights/map")
@cache_complaint_response("user_insights_map")
def get_map_data(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, category_id: Optional[int] = None, department_id: Optional[int] = None, status: Optional[str] = None, priority: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    validate_insight_filters(
        country_id, state_id, district_id, taluka_id, village_id,
        category_id, department_id, status, priority, days
    )

    query = apply_complaint_filters(
        db.query(Complaint),
        country_id, state_id, district_id, taluka_id, village_id,
        category_id, department_id, status, priority, days
    )
    rows = (
        query.outerjoin(
            ComplaintCategory,
            Complaint.category_id == ComplaintCategory.id
        )
        .with_entities(
            Complaint.latitude,
            Complaint.longitude,
            Complaint.status,
            Complaint.priority,
            ComplaintCategory.name
        )
        .filter(
            Complaint.latitude.isnot(None),
            Complaint.longitude.isnot(None)
        )
        .all()
    )

    cells = {}
    for latitude, longitude, status_value, priority_value, category_name in rows:
        lat = round(float(latitude), 2)
        lng = round(float(longitude), 2)
        key = (lat, lng)

        if key not in cells:
            cells[key] = {
                "latitude": lat,
                "longitude": lng,
                "count": 0,
                "categories": {},
                "statuses": {},
                "priorities": {}
            }

        cell = cells[key]
        cell["count"] += 1

        category = category_name or "Unknown"
        complaint_status = str(status_value or "Unknown")
        complaint_priority = str(priority_value or "Unknown")

        cell["categories"][category] = cell["categories"].get(category, 0) + 1
        cell["statuses"][complaint_status] = cell["statuses"].get(complaint_status, 0) + 1
        cell["priorities"][complaint_priority] = cell["priorities"].get(complaint_priority, 0) + 1

    markers = [
        cell for cell in cells.values()
        if cell["count"] >= 3
    ]

    return {
        "markers": markers,
        "count": sum(cell["count"] for cell in markers),
        "location": get_location(
            db, country_id, state_id, district_id, taluka_id, village_id
        )
    }


@router.get("/api/user/insights/category-status")
def category_status_matrix(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    validate_insight_filters(
        country_id, state_id, district_id, taluka_id, village_id,
        days=days
    )
    rows = apply_complaint_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id, days=days).outerjoin(ComplaintCategory, Complaint.category_id == ComplaintCategory.id).with_entities(func.coalesce(ComplaintCategory.name, "Processing"), Complaint.status, func.count(Complaint.id)).group_by(ComplaintCategory.name, Complaint.status).all()
    result = {}
    for category, status, count in rows:
        result.setdefault(category, {"pending": 0, "in_progress": 0, "resolved": 0, "rejected": 0})
        if status in result[category]: result[category][status] = count
    return result

@router.get("/api/user/insights/export")
def export_insights(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, category_id: Optional[int] = None, department_id: Optional[int] = None, status: Optional[str] = None, priority: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    validate_insight_filters(
        country_id, state_id, district_id, taluka_id, village_id,
        category_id, department_id, status, priority, days
    )

    query = apply_complaint_filters(
        db.query(
            ComplaintCategory.name.label("category_name"),
            Department.name.label("department_name"),
            Complaint.status,
            Complaint.priority,
            func.count(Complaint.id).label("total")
        )
        .outerjoin(ComplaintCategory, Complaint.category_id == ComplaintCategory.id)
        .outerjoin(Department, Complaint.department_id == Department.id),
        country_id, state_id, district_id, taluka_id, village_id,
        category_id, department_id, status, priority, days
    )

    rows = query.group_by(
        ComplaintCategory.name,
        Department.name,
        Complaint.status,
        Complaint.priority
    ).order_by(
        ComplaintCategory.name,
        Department.name,
        Complaint.status,
        Complaint.priority
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Department", "Status", "Priority", "Complaint Count"])

    for category, department, complaint_status, complaint_priority, total in rows:
        writer.writerow([
            category or "Unknown",
            department or "Unknown",
            complaint_status or "Unknown",
            complaint_priority or "Unknown",
            total
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=nivada_aggregated_insights.csv"}
    )
