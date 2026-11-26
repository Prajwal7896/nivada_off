
from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.db.db import get_db
from backend.app.db.model import Admin
from backend.app.security.rate_limit import limiter
from backend.app.security.password import (
    hash_password,
    verify_password,
    is_hashed_password
)

router = APIRouter()


@router.post("/officer/login")
@limiter.limit("5/minute")
def officer_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: str = Form(""),
    db: Session = Depends(get_db)
):
    admin = db.query(Admin).filter(
        Admin.email == email
    ).first()

    if not admin or not verify_password(password, admin.password):
        return RedirectResponse(
            url="/officer/login?error=invalid",
            status_code=303
        )

    if admin.role != "officer":
        return RedirectResponse(
            url="/officer/login?error=unauthorized",
            status_code=303
        )

    # Migrate existing plaintext passwords after successful login.
    if not is_hashed_password(admin.password):
        admin.password = hash_password(password)
        db.commit()

    request.session.clear()
    request.session["admin_id"] = admin.id

    return RedirectResponse(
        url="/officer/dashboard",
        status_code=303
    )


@router.post("/officer/logout")
def officer_logout(request: Request):
    request.session.clear()

    return RedirectResponse(
        url="/officer/login",
        status_code=303
    )
