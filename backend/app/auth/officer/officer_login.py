from fastapi import APIRouter, Form, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.db.model import Admin

router = APIRouter()


@router.post("/officer/login")
def officer_login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    remember_me: str = Form(""),
    db: Session = Depends(get_db)
):
    print("LOGIN EMAIL:", repr(email))
    print("LOGIN PASSWORD:", repr(password))

    admin = db.query(Admin).filter(
        Admin.email == email
    ).first()

    print("ADMIN FOUND:", admin is not None)

    if admin:
        print("DB EMAIL:", repr(admin.email))
        print("DB PASSWORD:", repr(admin.password))
        print("DB ROLE:", repr(admin.role))
        print("PASSWORD MATCH:", admin.password == password)

    if not admin or admin.password != password:
        return RedirectResponse(
            url="/officer/login?error=invalid",
            status_code=303
        )

    if admin.role != "officer":
        return RedirectResponse(
            url="/officer/login?error=unauthorized",
            status_code=303
        )

    request.session["admin_id"] = admin.id

    print("SESSION ADMIN ID:", request.session.get("admin_id"))

    return RedirectResponse(
        url="/officer/dashboard",
        status_code=303
    )


@router.post("/officer/logout")
def officer_logout(request: Request):
    request.session.pop("admin_id", None)

    return RedirectResponse(
        url="/officer/login",
        status_code=303
    )