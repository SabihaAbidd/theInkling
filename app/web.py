"""FastAPI API for The Inkling reader application."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator
from redis import asyncio as redis
from sqlalchemy.exc import IntegrityError

from app.database.connection import get_session
from app.database.models import DailyEdition
from app.database.repository import (
    create_reader_feedback,
    get_daily_edition,
    get_daily_edition_for_date,
    get_user,
    get_user_by_email,
    list_daily_editions,
    upsert_daily_edition,
    upsert_user,
)
from app.scrapers.sources import SOURCES
from app.services.auth import create_token, hash_password, parse_token, verify_password
from app.services.paper_pdf import render_edition_pdf
from app.tasks.editions import build_edition_task

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SAFE_TEXT_RE = re.compile(r"^[\w\s.#/+&():,'-]+$")


def configured_cors_origins() -> list[str]:
    """Return only the explicit browser origins trusted by this deployment."""

    return [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]


app = FastAPI(title="The Inkling Newspaper API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=configured_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)
redis_client = None


def redis_rate_limit(times: int, seconds: int, scope: str):
    """Build a distributed fixed-window limit keyed by user or client IP."""

    async def dependency(request: Request) -> None:
        if redis_client is None:
            raise HTTPException(status_code=503, detail="Request limiter unavailable.")

        identity = request.client.host if request.client else "unknown"
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            try:
                identity = f"user:{parse_token(authorization[7:])['user_id']}"
            except (KeyError, ValueError):
                pass

        key = f"rate-limit:{scope}:{identity}"
        count = await redis_client.eval(
            "local count = redis.call('INCR', KEYS[1]); "
            "if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]); end; "
            "return count",
            1,
            key,
            seconds,
        )
        if int(count) > times:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(seconds)},
            )

    return Depends(dependency)


@app.on_event("startup")
async def initialize_rate_limiting() -> None:
    """Initialize shared Redis-backed request limits for web instances."""

    global redis_client
    redis_client = redis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()


@app.on_event("shutdown")
async def close_rate_limit_connection() -> None:
    """Release the web process's Redis connection pool."""

    if redis_client is not None:
        await redis_client.aclose()


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return JSON for unexpected errors so browser clients can display details."""

    detail = "Internal server error. Check backend logs."
    if os.getenv("DEBUG_API_ERRORS", "false").strip().lower() in {"1", "true", "yes"}:
        detail = f"{type(exc).__name__}: {exc}"
    return JSONResponse(status_code=500, content={"detail": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return readable validation errors for browser clients."""

    messages = []
    for error in exc.errors():
        location = ".".join(
            str(part) for part in error.get("loc", []) if part != "body"
        )
        message = error.get("msg", "Invalid value.")
        messages.append(f"{location}: {message}" if location else message)
    return JSONResponse(
        status_code=422,
        content={
            "detail": {
                "message": (
                    "Please fix the highlighted request values before trying again."
                ),
                "errors": messages,
            }
        },
    )


def clean_limited_text(value: str | None, field_name: str, max_length: int) -> str:
    """Normalize short user text and reject risky characters."""

    text_value = (value or "").strip()
    if not text_value:
        raise ValueError(f"{field_name} is required.")
    if len(text_value) > max_length:
        raise ValueError(f"{field_name} must be {max_length} characters or fewer.")
    if not SAFE_TEXT_RE.fullmatch(text_value):
        raise ValueError(f"{field_name} contains unsupported characters.")
    return text_value


def clean_optional_limited_text(
    value: str | None,
    field_name: str,
    max_length: int,
) -> str | None:
    """Normalize optional short user text."""

    if value is None:
        return None
    text_value = value.strip()
    if not text_value:
        return None
    return clean_limited_text(text_value, field_name, max_length)


def clean_email(value: str) -> str:
    """Normalize and validate an email address."""

    email = (value or "").strip().lower()
    if len(email) > 254 or not EMAIL_RE.fullmatch(email):
        raise ValueError("Please enter a valid email address.")
    return email


def clean_text_list(
    values: list[str],
    field_name: str,
    max_items: int,
    max_length: int,
) -> list[str]:
    """Normalize user preference lists while preserving order."""

    if len(values) > max_items:
        raise ValueError(f"{field_name} can contain at most {max_items} items.")
    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        text_value = clean_limited_text(str(value), field_name, max_length)
        key = text_value.lower()
        if key not in seen:
            cleaned.append(text_value)
            seen.add(key)
    return cleaned


class AuthRequest(BaseModel):
    """Request for account registration/login."""

    name: str | None = Field(default=None, max_length=80)
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=128)
    profile_name: str = Field(default="default_ai_reader", max_length=80)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return clean_optional_limited_text(value, "Name", 80)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return clean_email(value)

    @field_validator("profile_name")
    @classmethod
    def validate_profile_name(cls, value: str) -> str:
        return clean_limited_text(value, "Profile name", 80)


class PaperPreferencesRequest(BaseModel):
    """Topic-first reader profile for the daily paper."""

    topics: list[str] = Field(default_factory=list, max_length=12)
    keywords: list[str] = Field(default_factory=list, max_length=20)
    excluded_keywords: list[str] = Field(default_factory=list, max_length=20)
    preferred_sources: list[str] = Field(default_factory=list, max_length=20)
    top_n: int = Field(default=10, ge=5, le=20)
    use_llm: bool = True

    @field_validator("topics")
    @classmethod
    def validate_topics(cls, values: list[str]) -> list[str]:
        return clean_text_list(values, "Topics", 12, 40)

    @field_validator("keywords", "excluded_keywords")
    @classmethod
    def validate_paper_keywords(cls, values: list[str]) -> list[str]:
        return clean_text_list(values, "Keywords", 20, 40)

    @field_validator("preferred_sources")
    @classmethod
    def validate_paper_sources(cls, values: list[str]) -> list[str]:
        return clean_text_list(values, "Preferred sources", 20, 120)


class ReaderFeedbackRequest(BaseModel):
    """One actionable reader signal for future personalization."""

    news_item_id: int = Field(gt=0)
    action: str = Field(pattern="^(opened|saved|skipped|dismissed)$")
    dwell_seconds: int | None = Field(default=None, ge=0, le=86_400)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    """Resolve the authenticated user from a bearer token."""

    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing auth token.")
    try:
        payload = parse_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    with get_session() as session:
        user = get_user(session, int(payload["user_id"]))
        if user is None:
            raise HTTPException(status_code=401, detail="User not found.")
        session.expunge(user)
        return user


@app.get("/")
def index() -> RedirectResponse:
    """Open the configured reader client from the API root."""

    return RedirectResponse(os.getenv("FRONTEND_URL", "http://localhost:5173"))


@app.get("/api/health")
def health(request: Request) -> dict:
    """Return basic deployment diagnostics for frontend connectivity checks."""

    return {
        "ok": True,
        "service": "the-inkling-api",
        "origin": request.headers.get("origin"),
        "cors_origins_configured": bool(os.getenv("CORS_ORIGINS")),
    }


@app.post("/api/auth/register", dependencies=[redis_rate_limit(5, 60, "register")])
def register(request: AuthRequest) -> dict:
    """Register a user account."""

    if not request.name:
        raise HTTPException(status_code=400, detail="Name is required.")
    with get_session() as session:
        existing = get_user_by_email(session, request.email)
        if existing and existing.password_hash:
            raise HTTPException(status_code=400, detail="Account already exists.")
        user = upsert_user(
            session=session,
            name=request.name,
            email=request.email,
            profile_name=request.profile_name,
            password_hash=hash_password(request.password),
            preferences={},
        )
        return auth_payload(user)


@app.post("/api/auth/login", dependencies=[redis_rate_limit(5, 60, "login")])
def login(request: AuthRequest) -> dict:
    """Login with email and password."""

    with get_session() as session:
        user = get_user_by_email(session, request.email)
        if user is None or not verify_password(request.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")
        return auth_payload(user)


@app.get("/api/auth/me")
def me(user=Depends(current_user)) -> dict:
    """Return the current authenticated user."""

    return user_payload(user)


@app.get("/api/preferences/paper")
def get_paper_preferences(user=Depends(current_user)) -> dict:
    """Return the topic-first profile used to build daily papers."""

    return {
        "preferences": user.preferences or {},
        "topics": sorted({topic for source in SOURCES for topic in source.topics}),
    }


@app.put("/api/preferences/paper")
def save_paper_preferences(
    request: PaperPreferencesRequest,
    user=Depends(current_user),
) -> dict:
    """Save a reader's chosen subjects and editorial controls."""

    preferences = dict(user.preferences or {})
    preferences.update(request.model_dump())
    with get_session() as session:
        stored_user = get_user(session, user.id)
        if stored_user is None:
            raise HTTPException(status_code=404, detail="Reader account not found.")
        stored_user.preferences = preferences
        session.flush()
    return {"preferences": preferences}


@app.post(
    "/api/papers",
    status_code=202,
    dependencies=[redis_rate_limit(3, 3600, "paper-create")],
)
def request_daily_paper(user=Depends(current_user)) -> dict:
    """Queue a date-keyed newspaper build without blocking the API worker."""

    edition_date = datetime.now(UTC).date()
    try:
        with get_session() as session:
            edition = get_daily_edition_for_date(session, user.id, edition_date)
            if edition and edition.status in {"queued", "running", "ready"}:
                return _serialize_edition(edition)

            job_id = uuid4().hex
            edition = upsert_daily_edition(
                session,
                user_id=user.id,
                edition_date=edition_date,
                status="queued",
                job_id=job_id,
                title="The Inkling",
                error_code=None,
            )
            edition_id = edition.id
    except IntegrityError:
        # The unique reader/date constraint arbitrates requests that arrive
        # together. Return the winner's queued row instead of failing one caller.
        with get_session() as session:
            edition = get_daily_edition_for_date(session, user.id, edition_date)
            if edition and edition.status in {"queued", "running", "ready"}:
                return _serialize_edition(edition)
        raise

    try:
        build_edition_task.apply_async(
            args=[user.id, edition_date.isoformat()],
            task_id=job_id,
        )
    except Exception as exc:
        with get_session() as session:
            edition = get_daily_edition(session, user.id, edition_id)
            if edition:
                edition.status = "failed"
                edition.error_code = "queue_unavailable"
        raise HTTPException(
            status_code=503,
            detail="Paper queue is unavailable. Start Redis and the Celery worker.",
        ) from exc

    with get_session() as session:
        edition = get_daily_edition(session, user.id, edition_id)
        return _serialize_edition(edition)


@app.get("/api/papers")
def paper_archive(
    limit: int = 30,
    user=Depends(current_user),
) -> dict:
    """List the reader's saved newspaper editions."""

    with get_session() as session:
        editions = list_daily_editions(session, user.id, limit=limit)
        return {"editions": [_serialize_edition(edition) for edition in editions]}


@app.get("/api/papers/today")
def today_paper(user=Depends(current_user)) -> dict:
    """Return today's edition and its current generation state."""

    with get_session() as session:
        edition = get_daily_edition_for_date(session, user.id, datetime.now(UTC).date())
        return {"edition": _serialize_edition(edition) if edition else None}


@app.get("/api/papers/{edition_id}")
def paper_detail(edition_id: int, user=Depends(current_user)) -> dict:
    """Read a saved edition while enforcing reader ownership."""

    with get_session() as session:
        edition = get_daily_edition(session, user.id, edition_id)
        if edition is None:
            raise HTTPException(status_code=404, detail="Paper edition not found.")
        return {"edition": _serialize_edition(edition)}


@app.get("/api/papers/{edition_id}/pdf")
def paper_pdf(edition_id: int, user=Depends(current_user)) -> Response:
    """Download a private, print-ready PDF for an owned saved edition."""

    with get_session() as session:
        edition = get_daily_edition(session, user.id, edition_id)
        if edition is None:
            raise HTTPException(status_code=404, detail="Paper edition not found.")
        if edition.status != "ready":
            raise HTTPException(status_code=409, detail="This paper is not ready yet.")
        edition_date = edition.edition_date.isoformat()
        pdf_bytes = render_edition_pdf(
            title=edition.title,
            edition_date=edition_date,
            editorial=edition.editorial,
            articles=edition.items_snapshot or [],
        )

    filename = f"the-inkling-{edition_date}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.post(
    "/api/papers/{edition_id}/feedback",
    dependencies=[redis_rate_limit(30, 60, "paper-feedback")],
)
def paper_feedback(
    edition_id: int,
    request: ReaderFeedbackRequest,
    user=Depends(current_user),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    """Record an owned-article action for later ranking improvements."""

    with get_session() as session:
        edition = get_daily_edition(session, user.id, edition_id)
        if edition is None:
            raise HTTPException(status_code=404, detail="Paper edition not found.")
        article_ids = {item.get("id") for item in edition.items_snapshot}
        if request.news_item_id not in article_ids:
            raise HTTPException(
                status_code=404,
                detail="Article is not part of this paper edition.",
            )
        feedback, created = create_reader_feedback(
            session,
            user_id=user.id,
            news_item_id=request.news_item_id,
            edition_id=edition.id,
            action=request.action,
            idempotency_key=idempotency_key,
            dwell_seconds=request.dwell_seconds,
        )
        return {"id": feedback.id, "created": created, "action": feedback.action}


def auth_payload(user) -> dict:
    """Return user data with an auth token."""

    return {"token": create_token(user.id), "user": user_payload(user)}


def user_payload(user) -> dict:
    """Return only the reader fields needed by the web client."""

    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "profile_name": user.profile_name,
        "preferences": user.preferences or {},
    }


def isoformat(value) -> str | None:
    """Serialize an optional date or timestamp for the API response."""

    return value.isoformat() if value else None


def _serialize_edition(edition: DailyEdition) -> dict:
    """Serialize a saved edition without exposing the reader profile."""

    return {
        "id": edition.id,
        "date": edition.edition_date.isoformat(),
        "status": edition.status,
        "job_id": edition.job_id,
        "title": edition.title,
        "editorial": edition.editorial,
        "articles": edition.items_snapshot or [],
        "pdf_ready": edition.status == "ready",
        "pdf_url": f"/api/papers/{edition.id}/pdf"
        if edition.status == "ready"
        else None,
        "error_code": edition.error_code,
        "created_at": isoformat(edition.created_at),
        "generated_at": isoformat(edition.generated_at),
    }
