from pathlib import Path

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.db import get_db

from app.dashboard.user.comp_store import (
    get_user_complaints,
    get_complaint,
    delete_user_complaint,
    verify_resolution,
    get_user_notifications,
    mark_notification_read
)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[4]
FRONTEND_USER_DIR = BASE_DIR / "frontend" / "user"


class ResolutionVerification(BaseModel):
    verified: bool
    feedback: str | None = None


@router.get("/user/dashboard")
def user_dashboard(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        return FileResponse(FRONTEND_USER_DIR / "user_login.html")

    return FileResponse(FRONTEND_USER_DIR / "user_dashboard.html")


@router.get("/user/submission")
def user_submission(request: Request):
    user_id = request.session.get("user_id")

    if not user_id:
        return FileResponse(FRONTEND_USER_DIR / "user_login.html")

    return FileResponse(FRONTEND_USER_DIR / "submission.html")


@router.get("/api/user/complaints")
def user_complaints(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    return get_user_complaints(db, user_id)


@router.get("/api/user/complaints/{complaint_id}")
def user_complaint(
    complaint_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    complaint = get_complaint(
        db,
        complaint_id,
        user_id
    )

    if not complaint:
        raise HTTPException(
            status_code=404,
            detail="Complaint not found"
        )

    return complaint


@router.delete("/api/user/complaints/{complaint_id}")
def delete_complaint(
    complaint_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    success, message = delete_user_complaint(
        db,
        complaint_id,
        user_id
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=message
        )

    return {
        "success": True,
        "message": message
    }


@router.post("/api/user/complaints/{complaint_id}/verify")
def verify_complaint(
    complaint_id: int,
    data: ResolutionVerification,
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    success, result = verify_resolution(
        db=db,
        complaint_id=complaint_id,
        user_id=user_id,
        verified=data.verified,
        feedback=data.feedback
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail=result
        )

    return {
        "success": True,
        "status": result
    }


@router.get("/api/user/notifications")
def user_notifications(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    return get_user_notifications(
        db,
        user_id
    )


@router.patch("/api/user/notifications/{notification_id}/read")
def read_notification(
    notification_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    success = mark_notification_read(
        db,
        notification_id,
        user_id
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail="Notification not found"
        )

    return {
        "success": True,
        "message": "Notification marked as read"
    }