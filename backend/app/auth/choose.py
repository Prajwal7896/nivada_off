from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, RedirectResponse
import os

router = APIRouter()

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../..")
)

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


@router.get("/")
def choose(request: Request):
    if request.session.get("user_id"):
        return RedirectResponse(
            url="/user/dashboard",
            status_code=303
        )

    if request.session.get("officer_id"):
        return RedirectResponse(
            url="/officer/dashboard",
            status_code=303
        )

    return FileResponse(
        os.path.join(FRONTEND_DIR, "index.html")
    )


@router.get("/user/login")
def user_login():
    return FileResponse(
        os.path.join(FRONTEND_DIR, "user", "user_login.html")
    )


@router.get("/user/register")
def user_register():
    return FileResponse(
        os.path.join(FRONTEND_DIR, "user", "user_register.html")
    )


@router.get("/officer/login")
def officer_login():
    return FileResponse(
        os.path.join(FRONTEND_DIR, "officer", "officer_login.html")
    )


@router.get("/officer/register")
def officer_register():
    return FileResponse(
        os.path.join(FRONTEND_DIR, "officer", "officer_register.html")
    )