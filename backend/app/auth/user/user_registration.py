from fastapi import APIRouter, Form, Depends
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.db.db import get_db
from app.db.model import User
import os

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
def user_register_submit(
    fullname: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == email).first()

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
        password=password,
        role="citizen"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return RedirectResponse(
        url="/user/login",
        status_code=303
    )