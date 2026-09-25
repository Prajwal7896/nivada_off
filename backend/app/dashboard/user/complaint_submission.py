from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
import os

router = APIRouter()

BASE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../../..")
)

FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")


@router.get("/user/complaint")
def complaint_submission_page(request: Request):

    if not request.session.get("user_id"):
        return FileResponse(
            os.path.join(
                FRONTEND_DIR,
                "user",
                "user_login.html"
            )
        )

    return FileResponse(
        os.path.join(
            FRONTEND_DIR,
            "user",
            "submission.html"
        )
    )