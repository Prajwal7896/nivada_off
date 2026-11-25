
from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from backend.app.db.db import get_db
from backend.app.db.model import User
from backend.app.security.rate_limit import limiter
from backend.app.security.password import (
    hash_password,
    verify_password,
    is_hashed_password
)

router = APIRouter()


@router.post("/user/login")
@limiter.limit("5/minute")
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

    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    # Automatically migrate legacy plaintext passwords.
    if not is_hashed_password(user.password):
        user.password = hash_password(password)
        db.commit()

    request.session.clear()

    request.session["user_id"] = user.id
    request.session["user_email"] = user.email
    request.session["user_name"] = user.username

    return RedirectResponse(
        url="/user/profile",
        status_code=303
    )
