from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import csv, io
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.db.model import User, Complaint, ComplaintCategory, Department, ComplaintHistory, Country, State, District, Taluka, Village

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
    get_counts = lambda items: {category_lookup.get(i.category_id, "Unknown"): sum(1 for x in items if category_lookup.get(x.category_id, "Unknown") == category_lookup.get(i.category_id, "Unknown")) for i in items}
    
    curr_counts, prev_counts = get_counts(current_complaints), get_counts(previous_complaints)
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
def get_insights(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, category_id: Optional[int] = None, department_id: Optional[int] = None, status: Optional[str] = None, priority: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    days = max(0, days)
    base_query = apply_complaint_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id, category_id, None, status, priority, days)
    complaints = base_query.all()
    category_lookup = {r[0]: r[1] for r in db.query(ComplaintCategory.id, ComplaintCategory.name).all()}
    
    category_rows = base_query.join(ComplaintCategory, Complaint.category_id == ComplaintCategory.id).with_entities(ComplaintCategory.id, ComplaintCategory.name, func.count(Complaint.id)).group_by(ComplaintCategory.id, ComplaintCategory.name).order_by(func.count(Complaint.id).desc()).all()
    category_distribution = [{"id": r[0], "name": r[1], "count": r[2]} for r in category_rows]

    total = len(complaints)
    pending, in_progress, resolved, rejected = sum(1 for c in complaints if c.status == "pending"), sum(1 for c in complaints if c.status == "in_progress"), sum(1 for c in complaints if c.status == "resolved"), sum(1 for c in complaints if c.status == "rejected")
    resolution_rate = round((resolved / total) * 100, 2) if total else 0

    resolved_times = [max(0, ((c.updated_at.replace(tzinfo=None) if c.updated_at.tzinfo else c.updated_at) - (c.timestamp.replace(tzinfo=None) if c.timestamp.tzinfo else c.timestamp)).total_seconds() / 86400) for c in complaints if c.status == "resolved" and c.timestamp and c.updated_at]
    avg_resolution_time = round(sum(resolved_times) / len(resolved_times), 2) if resolved_times else 0

    status_distribution = {"pending": pending, "in_progress": in_progress, "resolved": resolved, "rejected": rejected}
    priority_distribution = {"high": 0, "medium": 0, "low": 0}
    for c in complaints:
        p_val = str(c.priority).lower() if c.priority else "unknown"
        priority_distribution[p_val] = priority_distribution.get(p_val, 0) + 1

    department_rows = apply_complaint_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id, category_id, department_id, status, priority, days).join(Department, Complaint.department_id == Department.id).with_entities(Department.id, Department.name, func.count(Complaint.id)).group_by(Department.id, Department.name).order_by(func.count(Complaint.id).desc()).all()
    department_distribution = [{"id": r[0], "name": r[1], "count": r[2]} for r in department_rows]

    trend_rows = base_query.with_entities(func.date_trunc("day", Complaint.timestamp).label("date"), func.count(Complaint.id)).group_by("date").order_by("date").all()
    monthly_trend = [{"date": r[0].strftime("%Y-%m-%d"), "count": r[1]} for r in trend_rows if r[0]]

    category_status, category_priority = {}, {}
    for c in complaints:
        cat_name = category_lookup.get(c.category_id, "Unknown")
        category_status.setdefault(cat_name, {"pending": 0, "in_progress": 0, "resolved": 0, "rejected": 0})
        c_status = str(c.status).lower() if c.status else ""
        if c_status in category_status[cat_name]: category_status[cat_name][c_status] += 1

        category_priority.setdefault(cat_name, {"high": 0, "medium": 0, "low": 0})
        c_priority = str(c.priority).lower() if c.priority else ""
        if c_priority in category_priority[cat_name]: category_priority[cat_name][c_priority] += 1

    ageing = calculate_ageing([c for c in complaints if c.status == "pending"])
    resolution_time = calculate_resolution_times(complaints, category_lookup)
    confidence_distribution = [round(max(0, min(1, float(c.ai_confidence))) * 100, 2) for c in complaints if c.ai_confidence is not None]

    current_start = datetime.utcnow() - timedelta(days=days)
    previous_query = apply_location_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id)
    if category_id is not None: previous_query = previous_query.filter(Complaint.category_id == category_id)
    if department_id is not None: previous_query = previous_query.filter(Complaint.department_id == department_id)
    previous_complaints = previous_query.filter(Complaint.timestamp >= current_start - timedelta(days=days), Complaint.timestamp < current_start).all()

    ai_insights = build_ai_insights(category_distribution, category_priority, complaints, previous_complaints, category_lookup)

    curr_counts, prev_counts = {}, {}
    for c in complaints: curr_counts[category_lookup.get(c.category_id, "Unknown")] = curr_counts.get(category_lookup.get(c.category_id, "Unknown"), 0) + 1
    for c in previous_complaints: prev_counts[category_lookup.get(c.category_id, "Unknown")] = prev_counts.get(category_lookup.get(c.category_id, "Unknown"), 0) + 1

    emerging_issues = []
    for cat, cur in curr_counts.items():
        prev = prev_counts.get(cat, 0)
        change = ((cur - prev) / prev) * 100 if prev else (100 if cur else 0)
        trend = "Increasing" if change > 0 else ("Declining" if change < 0 else "Stable")
        emerging_issues.append({"issue": cat, "current": cur, "previous": prev, "change": round(change, 2), "trend": trend})
    emerging_issues.sort(key=lambda x: x["change"], reverse=True)

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
def get_map_data(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, category_id: Optional[int] = None, department_id: Optional[int] = None, status: Optional[str] = None, priority: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    query = apply_complaint_filters(db.query(Complaint, ComplaintCategory.name.label("category_name")).outerjoin(ComplaintCategory, Complaint.category_id == ComplaintCategory.id), country_id, state_id, district_id, taluka_id, village_id, category_id, department_id, status, priority, days)
    rows = query.filter(Complaint.latitude.isnot(None), Complaint.longitude.isnot(None)).all()
    markers = [{"id": c.id, "latitude": c.latitude, "longitude": c.longitude, "category": cat_name or "Unknown", "category_id": c.category_id, "status": c.status, "priority": c.priority, "text": c.complaint_text or "", "timestamp": c.timestamp.isoformat() if c.timestamp else None} for c, cat_name in rows]
    return {"markers": markers, "count": len(markers), "location": get_location(db, country_id, state_id, district_id, taluka_id, village_id)}

@router.get("/api/user/insights/category-status")
def category_status_matrix(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    rows = apply_complaint_filters(db.query(Complaint), country_id, state_id, district_id, taluka_id, village_id, days=days).join(ComplaintCategory, Complaint.category_id == ComplaintCategory.id).with_entities(ComplaintCategory.name, Complaint.status, func.count(Complaint.id)).group_by(ComplaintCategory.name, Complaint.status).all()
    result = {}
    for category, status, count in rows:
        result.setdefault(category, {"pending": 0, "in_progress": 0, "resolved": 0, "rejected": 0})
        if status in result[category]: result[category][status] = count
    return result

@router.get("/api/user/insights/export")
def export_insights(request: Request, country_id: Optional[int] = None, state_id: Optional[int] = None, district_id: Optional[int] = None, taluka_id: Optional[int] = None, village_id: Optional[int] = None, category_id: Optional[int] = None, department_id: Optional[int] = None, status: Optional[str] = None, priority: Optional[str] = None, days: int = 30, db: Session = Depends(get_db)):
    get_current_user(request, db)
    query = apply_complaint_filters(db.query(Complaint, ComplaintCategory.name.label("category_name"), Department.name.label("department_name")).outerjoin(ComplaintCategory, Complaint.category_id == ComplaintCategory.id).outerjoin(Department, Complaint.department_id == Department.id), country_id, state_id, district_id, taluka_id, village_id, category_id, department_id, status, priority, days)
    rows = query.order_by(Complaint.timestamp.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Complaint ID", "Complaint", "Category", "Department", "Status", "Priority", "Latitude", "Longitude", "AI Confidence", "Created At"])
    for complaint, category, department in rows:
        writer.writerow([complaint.id, complaint.complaint_text or "", category or "", department or "", complaint.status or "", complaint.priority or "", complaint.latitude, complaint.longitude, complaint.ai_confidence, complaint.timestamp])
    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=nivada_insights.csv"})