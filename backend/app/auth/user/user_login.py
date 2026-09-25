from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.db.db import get_db
from app.db.model import User

router = APIRouter()


@router.post("/user/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user or user.password != password:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    request.session["user_name"] = user.username

    return RedirectResponse(
        url="/user/profile",
        status_code=303
    )