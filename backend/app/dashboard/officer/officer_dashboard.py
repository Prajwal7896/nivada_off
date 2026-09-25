from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.db.model import (
    Admin,
    Department,
    Country,
    State,
    District,
    Taluka,
    Village,
    Complaint,
    User,
    ComplaintCategory,
    Notification,
    ComplaintHistory
)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[4]
FRONTEND_OFFICER_DIR = BASE_DIR / "frontend" / "officer"


def get_current_officer(request: Request, db: Session):
    officer_id = request.session.get("admin_id")

    if not officer_id:
        raise HTTPException(
            status_code=401,
            detail="Officer not authenticated"
        )

    officer = db.query(Admin).filter(
        Admin.id == officer_id,
        Admin.role == "officer"
    ).first()

    if not officer:
        raise HTTPException(
            status_code=401,
            detail="Officer not found"
        )

    return officer


@router.get("/officer/dashboard")
def officer_dashboard(
    request: Request
):
    officer_id = request.session.get("admin_id")

    if not officer_id:
        return FileResponse(
            FRONTEND_OFFICER_DIR / "officer_login.html"
        )

    return FileResponse(
        FRONTEND_OFFICER_DIR / "officer_dashboard.html"
    )


@router.get("/api/officer/profile")
def officer_profile(
    request: Request,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    department = db.query(Department).filter(
        Department.id == officer.department_id
    ).first()

    country = db.query(Country).filter(
        Country.id == officer.country_id
    ).first()

    state = db.query(State).filter(
        State.id == officer.state_id
    ).first()

    district = db.query(District).filter(
        District.id == officer.district_id
    ).first()

    taluka = db.query(Taluka).filter(
        Taluka.id == officer.taluka_id
    ).first()

    village = db.query(Village).filter(
        Village.id == officer.village_id
    ).first()

    return {
        "id": officer.id,
        "name": officer.username,
        "email": officer.email,
        "phone": officer.phone,
        "employee_code": officer.employee_code,
        "designation": officer.designation,
        "role": officer.role,
        "department": {
            "id": department.id if department else None,
            "name": department.name if department else None
        },
        "location": {
            "country_id": country.id if country else None,
            "country": country.name if country else None,
            "state_id": state.id if state else None,
            "state": state.name if state else None,
            "district_id": district.id if district else None,
            "district": district.name if district else None,
            "taluka_id": taluka.id if taluka else None,
            "taluka": taluka.name if taluka else None,
            "village_id": village.id if village else None,
            "village": village.name if village else None
        }
    }


@router.get("/api/officer/complaints")
def officer_complaints(
    request: Request,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    complaints = (
        db.query(Complaint, User, ComplaintCategory)
        .outerjoin(User, Complaint.user_id == User.id)
        .outerjoin(
            ComplaintCategory,
            Complaint.category_id == ComplaintCategory.id
        )
        .filter(
            Complaint.assigned_admin_id == officer.id
        )
        .order_by(Complaint.timestamp.desc())
        .all()
    )

    result = []

    for complaint, user, category in complaints:
        result.append({
            "id": complaint.id,
            "complaint_text": complaint.complaint_text,
            "address": complaint.address,
            "latitude": complaint.latitude,
            "longitude": complaint.longitude,
            "status": complaint.status,
            "priority": complaint.priority,
            "ai_confidence": complaint.ai_confidence,
            "timestamp": complaint.timestamp,
            "updated_at": complaint.updated_at,
            "category": category.name if category else None,
            "user": {
                "id": user.id if user else None,
                "name": user.username if user else None,
                "email": user.email if user else None,
                "phone": user.phone if user else None
            }
        })

    return result


@router.get("/api/officer/complaints/{complaint_id}")
def officer_complaint(
    complaint_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    result = (
        db.query(Complaint, User, ComplaintCategory)
        .outerjoin(User, Complaint.user_id == User.id)
        .outerjoin(
            ComplaintCategory,
            Complaint.category_id == ComplaintCategory.id
        )
        .filter(
            Complaint.id == complaint_id,
            Complaint.assigned_admin_id == officer.id
        )
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    complaint, user, category = result

    return {
        "id": complaint.id,
        "complaint_text": complaint.complaint_text,
        "address": complaint.address,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "status": complaint.status,
        "priority": complaint.priority,
        "ai_confidence": complaint.ai_confidence,
        "image_path": complaint.image_path,
        "timestamp": complaint.timestamp,
        "updated_at": complaint.updated_at,
        "category": category.name if category else None,
        "user": {
            "id": user.id if user else None,
            "name": user.username if user else None,
            "email": user.email if user else None,
            "phone": user.phone if user else None
        }
    }


@router.get("/api/officer/stats")
def officer_stats(
    request: Request,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    complaints = db.query(Complaint).filter(
        Complaint.assigned_admin_id == officer.id
    )

    total = complaints.count()

    pending = complaints.filter(
        Complaint.status == "pending"
    ).count()

    in_progress = complaints.filter(
        Complaint.status == "in_progress"
    ).count()

    resolved = complaints.filter(
        Complaint.status == "resolved"
    ).count()

    rejected = complaints.filter(
        Complaint.status == "rejected"
    ).count()

    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved,
        "rejected": rejected
    }


@router.patch("/api/officer/complaints/{complaint_id}/status")
def update_complaint_status(
    complaint_id: int,
    request: Request,
    status: str,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    allowed_statuses = {
        "pending",
        "in_progress",
        "resolved",
        "rejected"
    }

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    complaint = db.query(Complaint).filter(
        Complaint.id == complaint_id,
        Complaint.assigned_admin_id == officer.id
    ).first()

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    old_status = complaint.status

    complaint.status = status

    history = ComplaintHistory(
        complaint_id=complaint.id,
        performed_by=officer.id,
        old_status=old_status,
        new_status=status,
        action="status_update",
        description=f"Officer changed complaint status from {old_status} to {status}"
    )

    db.add(history)

    db.commit()
    db.refresh(complaint)

    return {
        "success": True,
        "complaint_id": complaint.id,
        "old_status": old_status,
        "new_status": complaint.status
    }


@router.get("/api/officer/notifications")
def officer_notifications(
    request: Request,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    notifications = db.query(Notification).filter(
        Notification.user_id == officer.id
    ).order_by(
        Notification.created_at.desc()
    ).all()

    return [
        {
            "id": notification.id,
            "complaint_id": notification.complaint_id,
            "title": notification.title,
            "message": notification.message,
            "notification_type": notification.notification_type,
            "is_read": notification.is_read,
            "created_at": notification.created_at
        }
        for notification in notifications
    ]


@router.patch("/api/officer/notifications/{notification_id}/read")
def officer_notification_read(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    officer = get_current_officer(request, db)

    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == officer.id
    ).first()

    if not notification:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    notification.is_read = True

    db.commit()

    return {
        "success": True,
        "message": "Notification marked as read"
    }