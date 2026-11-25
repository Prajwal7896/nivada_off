import secrets

from fastapi import HTTPException, Request


CSRF_SESSION_KEY = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"


def get_or_create_csrf_token(request: Request) -> str:
    token = request.session.get(CSRF_SESSION_KEY)

    if not token:
        token = secrets.token_urlsafe(32)
        request.session[CSRF_SESSION_KEY] = token

    return token


def validate_csrf_token(request: Request) -> None:
    session_token = request.session.get(CSRF_SESSION_KEY)
    request_token = request.headers.get(CSRF_HEADER_NAME)

    if (
        not session_token
        or not request_token
        or not secrets.compare_digest(
            session_token,
            request_token
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing CSRF token"
        )

from fastapi import APIRouter

router = APIRouter(tags=["Security"])


@router.get("/api/csrf-token")
def get_csrf_token(request: Request):
    user_id = request.session.get("user_id")
    officer_id = request.session.get("admin_id")

    if not user_id and not officer_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )

    return {
        "csrf_token": get_or_create_csrf_token(request)
    }