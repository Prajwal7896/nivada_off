from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
import os

from app.db.db import get_db
from app.db.model import User

router = APIRouter()

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../..")
)

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


class ProfileUpdate(BaseModel):
    username: str
    phone: str


@router.get("/user/profile")
def user_profile_page(request: Request):

    if not request.session.get("user_id"):
        return RedirectResponse(
            url="/user/login",
            status_code=303
        )

    return FileResponse(
        os.path.join(
            FRONTEND_DIR,
            "user",
            "user_profile.html"
        )
    )


@router.get("/api/user/profile")
def get_user_profile(
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        request.session.clear()
        raise HTTPException(
            status_code=401,
            detail="User session is invalid"
        )

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        )
    }


@router.put("/api/user/profile")
def update_user_profile(
    data: ProfileUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )

    user = (
        db.query(User)
        .filter(User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    username = data.username.strip()
    phone = data.phone.strip()

    if len(username) < 2:
        raise HTTPException(
            status_code=400,
            detail="Username must contain at least 2 characters"
        )

    if not phone.isdigit() or len(phone) != 10:
        raise HTTPException(
            status_code=400,
            detail="Phone number must contain exactly 10 digits"
        )

    user.username = username
    user.phone = phone

    db.commit()
    db.refresh(user)

    request.session["user_name"] = user.username

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        )
    }


@router.post("/api/user/logout")
def logout(request: Request):
    request.session.clear()

    return {
        "success": True,
        "message": "Logged out successfully"
    }