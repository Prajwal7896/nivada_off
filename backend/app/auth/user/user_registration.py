
from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from backend.app.db.db import get_db
from backend.app.db.model import User
from backend.app.security.rate_limit import limiter
from backend.app.security.password import hash_password
import os
import re

router = APIRouter()

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
    )
)

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend", "user")


@router.post("/user/register")
@limiter.limit("3/minute")
def user_register_submit(
    request: Request,
    fullname: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    fullname = fullname.strip()
    email = email.strip().lower()
    phone = phone.strip()

    invalid = (
        not 2 <= len(fullname) <= 80
        or any(ord(ch) < 32 for ch in fullname)
        or len(email) > 254
        or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email)
        or not re.fullmatch(r"\d{10}", phone)
        or not 8 <= len(password) <= 128
        or password != confirm_password
    )

    if invalid:
        return FileResponse(
            os.path.join(FRONTEND_DIR, "user_register.html")
        )

    existing_user = db.query(User).filter(
        User.email == email
    ).first()

    if existing_user:
        return FileResponse(
            os.path.join(FRONTEND_DIR, "user_register.html")
        )

    if password != confirm_password:
        return FileResponse(
            os.path.join(FRONTEND_DIR, "user_register.html")
        )

    user = User(
        username=fullname,
        email=email,
        phone=phone,
        password=hash_password(password),
        role="citizen"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse(
        url="/user/login",
        status_code=303
    )
