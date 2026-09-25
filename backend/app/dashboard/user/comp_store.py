from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.model import (
    Complaint,
    ComplaintCategory,
    Department,
    Country,
    State,
    District,
    Taluka,
    Village,
    Notification,
    CitizenVerification,
    ComplaintHistory,
    AuditLog
)


def get_user_complaints(db: Session, user_id: int):
    complaints = (
        db.query(Complaint)
        .filter(
            Complaint.user_id == user_id,
            Complaint.status != "closed"
        )
        .order_by(desc(Complaint.timestamp))
        .all()
    )

    result = []

    for complaint in complaints:

        category = (
            db.query(ComplaintCategory)
            .filter(
                ComplaintCategory.id == complaint.category_id
            )
            .first()
        )

        department = (
            db.query(Department)
            .filter(
                Department.id == complaint.department_id
            )
            .first()
        )

        country = (
            db.query(Country)
            .filter(
                Country.id == complaint.country_id
            )
            .first()
        )

        state = (
            db.query(State)
            .filter(
                State.id == complaint.state_id
            )
            .first()
        )

        district = (
            db.query(District)
            .filter(
                District.id == complaint.district_id
            )
            .first()
        )

        taluka = (
            db.query(Taluka)
            .filter(
                Taluka.id == complaint.taluka_id
            )
            .first()
        )

        village = (
            db.query(Village)
            .filter(
                Village.id == complaint.village_id
            )
            .first()
        )

        result.append({
            "id": complaint.id,
            "complaint_number": f"CMP-{complaint.id:06d}",
            "title": (
                complaint.complaint_text[:80]
                if complaint.complaint_text
                else "Civic Complaint"
            ),
            "description": complaint.complaint_text,
            "category": category.name if category else None,
            "department": department.name if department else None,
            "status": complaint.status,
            "priority": complaint.priority,
            "ai_confidence": complaint.ai_confidence,
            "address": complaint.address,
            "latitude": complaint.latitude,
            "longitude": complaint.longitude,
            "country": country.name if country else None,
            "state": state.name if state else None,
            "district": district.name if district else None,
            "taluka": taluka.name if taluka else None,
            "village": village.name if village else None,
            "image_path": complaint.image_path,
            "submitted_date": complaint.timestamp,
            "updated_at": complaint.updated_at
        })

    return result


def get_complaint(
    db: Session,
    complaint_id: int,
    user_id: int
):
    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.id == complaint_id,
            Complaint.user_id == user_id
        )
        .first()
    )

    if not complaint:
        return None

    category = (
        db.query(ComplaintCategory)
        .filter(
            ComplaintCategory.id == complaint.category_id
        )
        .first()
    )

    department = (
        db.query(Department)
        .filter(
            Department.id == complaint.department_id
        )
        .first()
    )

    country = (
        db.query(Country)
        .filter(
            Country.id == complaint.country_id
        )
        .first()
    )

    state = (
        db.query(State)
        .filter(
            State.id == complaint.state_id
        )
        .first()
    )

    district = (
        db.query(District)
        .filter(
            District.id == complaint.district_id
        )
        .first()
    )

    taluka = (
        db.query(Taluka)
        .filter(
            Taluka.id == complaint.taluka_id
        )
        .first()
    )

    village = (
        db.query(Village)
        .filter(
            Village.id == complaint.village_id
        )
        .first()
    )

    return {
        "id": complaint.id,
        "complaint_number": f"CMP-{complaint.id:06d}",
        "title": (
            complaint.complaint_text[:80]
            if complaint.complaint_text
            else "Civic Complaint"
        ),
        "description": complaint.complaint_text,
        "category": category.name if category else None,
        "department": department.name if department else None,
        "status": complaint.status,
        "priority": complaint.priority,
        "ai_confidence": complaint.ai_confidence,
        "address": complaint.address,
        "latitude": complaint.latitude,
        "longitude": complaint.longitude,
        "country": country.name if country else None,
        "state": state.name if state else None,
        "district": district.name if district else None,
        "taluka": taluka.name if taluka else None,
        "village": village.name if village else None,
        "image_path": complaint.image_path,
        "timestamp": complaint.timestamp,
        "updated_at": complaint.updated_at
    }


def delete_user_complaint(
    db: Session,
    complaint_id: int,
    user_id: int
):
    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.id == complaint_id,
            Complaint.user_id == user_id
        )
        .first()
    )

    if not complaint:
        return False, "Complaint not found"

    audit = AuditLog(
        user_id=user_id,
        action="DELETE_COMPLAINT",
        entity_type="complaint",
        entity_id=complaint_id,
        description="Citizen deleted their complaint"
    )

    db.add(audit)

    db.delete(complaint)

    try:
        db.commit()
    except Exception:
        db.rollback()
        return False, "Failed to delete complaint"

    return True, "Complaint deleted successfully"


def verify_resolution(
    db: Session,
    complaint_id: int,
    user_id: int,
    verified: bool,
    feedback: str = None
):
    complaint = (
        db.query(Complaint)
        .filter(
            Complaint.id == complaint_id,
            Complaint.user_id == user_id
        )
        .first()
    )

    if not complaint:
        return False, "Complaint not found"

    if not complaint.status:
        return False, "Invalid complaint status"

    if complaint.status.lower() != "resolved":
        return False, "Complaint is not awaiting verification"

    verification = CitizenVerification(
        complaint_id=complaint_id,
        user_id=user_id,
        verified=verified,
        feedback=feedback
    )

    db.add(verification)

    old_status = complaint.status

    if verified:

        complaint.status = "closed"

        history = ComplaintHistory(
            complaint_id=complaint_id,
            performed_by=None,
            old_status=old_status,
            new_status="closed",
            action="citizen_verified_resolution",
            description="Citizen confirmed that the complaint was resolved"
        )

        notification = Notification(
            user_id=user_id,
            complaint_id=complaint_id,
            title="Complaint Closed",
            message="Your complaint has been successfully closed after resolution verification.",
            notification_type="success"
        )

    else:

        complaint.status = "reopened"

        history = ComplaintHistory(
            complaint_id=complaint_id,
            performed_by=None,
            old_status=old_status,
            new_status="reopened",
            action="citizen_rejected_resolution",
            description="Citizen reported that the complaint was not actually resolved"
        )

        notification = Notification(
            user_id=user_id,
            complaint_id=complaint_id,
            title="Complaint Reopened",
            message="Your complaint has been reopened and returned to the officer workflow.",
            notification_type="warning"
        )

    db.add(history)
    db.add(notification)

    audit = AuditLog(
        user_id=user_id,
        action="VERIFY_RESOLUTION",
        entity_type="complaint",
        entity_id=complaint_id,
        description=(
            "Citizen confirmed resolution"
            if verified
            else "Citizen rejected resolution"
        )
    )

    db.add(audit)

    try:
        db.commit()
        db.refresh(complaint)

    except Exception:
        db.rollback()
        return False, "Failed to process resolution verification"

    return True, complaint.status


def get_user_notifications(
    db: Session,
    user_id: int
):
    notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == user_id
        )
        .order_by(
            desc(Notification.created_at)
        )
        .all()
    )

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


def mark_notification_read(
    db: Session,
    notification_id: int,
    user_id: int
):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        )
        .first()
    )

    if not notification:
        return False

    notification.is_read = True

    try:
        db.commit()
    except Exception:
        db.rollback()
        return False

    return True


def get_active_complaint_count(
    db: Session,
    user_id: int
):
    return (
        db.query(Complaint)
        .filter(
            Complaint.user_id == user_id,
            Complaint.status != "closed"
        )
        .count()
    )


def get_resolved_complaints(
    db: Session,
    user_id: int
):
    return (
        db.query(Complaint)
        .filter(
            Complaint.user_id == user_id,
            Complaint.status == "resolved"
        )
        .order_by(
            desc(Complaint.updated_at)
        )
        .all()
    )