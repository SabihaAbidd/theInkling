"""Persistence operations for readers, curated stories, and daily editions."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .models import DailyEdition, NewsItem, ReaderFeedback, User

if TYPE_CHECKING:
    from app.services.models import ProcessedItem

EMAIL_ADDRESS_PATTERN = re.compile(
    r"^[a-z0-9](?:[a-z0-9._%+-]{0,252}[a-z0-9])?@"
    r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$"
)


def upsert_daily_edition(
    session: Session,
    *,
    user_id: int,
    edition_date: date,
    status: str,
    job_id: str | None = None,
    title: str = "The Inkling",
    editorial: str = "",
    items_snapshot: list[dict] | None = None,
    pdf_path: str | None = None,
    error_code: str | None = None,
) -> DailyEdition:
    """Create or update a reader's stable daily edition record."""

    edition = session.scalar(
        select(DailyEdition).where(
            DailyEdition.user_id == user_id,
            DailyEdition.edition_date == edition_date,
        )
    )
    if edition is None:
        edition = DailyEdition(
            user_id=user_id,
            edition_date=edition_date,
            status=status,
        )
        session.add(edition)

    edition.status = status
    edition.job_id = job_id or edition.job_id
    edition.title = title
    edition.editorial = editorial
    if items_snapshot is not None:
        edition.items_snapshot = items_snapshot
    if pdf_path is not None:
        edition.pdf_path = pdf_path
    edition.error_code = error_code
    if status == "ready" and edition.generated_at is None:
        edition.generated_at = datetime.now(UTC)
    session.flush()
    return edition


def get_daily_edition(
    session: Session, user_id: int, edition_id: int
) -> DailyEdition | None:
    """Get one edition while enforcing its reader ownership boundary."""

    return session.scalar(
        select(DailyEdition).where(
            DailyEdition.id == edition_id,
            DailyEdition.user_id == user_id,
        )
    )


def get_daily_edition_for_date(
    session: Session,
    user_id: int,
    edition_date: date,
) -> DailyEdition | None:
    """Get the edition for one reader and UTC edition date."""

    return session.scalar(
        select(DailyEdition).where(
            DailyEdition.user_id == user_id,
            DailyEdition.edition_date == edition_date,
        )
    )


def list_daily_editions(
    session: Session, user_id: int, limit: int = 30
) -> list[DailyEdition]:
    """List a reader's recent editions newest first."""

    return list(
        session.scalars(
            select(DailyEdition)
            .where(DailyEdition.user_id == user_id)
            .order_by(DailyEdition.edition_date.desc())
            .limit(max(1, min(limit, 100)))
        ).all()
    )


def create_reader_feedback(
    session: Session,
    *,
    user_id: int,
    news_item_id: int,
    action: str,
    edition_id: int | None = None,
    idempotency_key: str | None = None,
    dwell_seconds: int | None = None,
) -> tuple[ReaderFeedback, bool]:
    """Append a feedback event, deduplicating retried client submissions."""

    if idempotency_key:
        existing = session.scalar(
            select(ReaderFeedback).where(
                ReaderFeedback.user_id == user_id,
                ReaderFeedback.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing, False

    event = ReaderFeedback(
        user_id=user_id,
        news_item_id=news_item_id,
        action=action,
        edition_id=edition_id,
        idempotency_key=idempotency_key,
        dwell_seconds=dwell_seconds,
    )
    session.add(event)
    session.flush()
    return event, True


def list_reader_feedback(
    session: Session, user_id: int, limit: int = 500
) -> list[dict]:
    """Load recent feedback joined to article text for profile learning."""

    rows = session.execute(
        select(ReaderFeedback, NewsItem)
        .join(NewsItem, NewsItem.id == ReaderFeedback.news_item_id)
        .where(ReaderFeedback.user_id == user_id)
        .order_by(ReaderFeedback.created_at.desc())
        .limit(max(1, min(limit, 2000)))
    ).all()
    return [
        {
            "action": event.action,
            "dwell_seconds": event.dwell_seconds,
            "title": item.title,
            "summary": item.summary,
            "source": item.source,
            "created_at": event.created_at,
        }
        for event, item in rows
    ]


def create_user(
    session: Session,
    name: str,
    email: str,
    profile_name: str = "default_ai_reader",
) -> User:
    """Create a user with a valid email address."""

    normalized_email = validate_email_address(email)
    user = User(name=name.strip(), email=normalized_email, profile_name=profile_name)
    session.add(user)
    session.flush()
    return user


def upsert_user(
    session: Session,
    name: str,
    email: str,
    profile_name: str = "default_ai_reader",
    password_hash: str | None = None,
    preferences: dict | None = None,
) -> User:
    """Create or update a reader account by normalized email address."""

    normalized_email = validate_email_address(email)
    user = get_user_by_email(session, normalized_email)
    if user is None:
        user = create_user(session, name, normalized_email, profile_name)
        user.password_hash = password_hash
        user.preferences = preferences or {}
        session.flush()
        return user

    user.name = name.strip()
    user.profile_name = profile_name
    if password_hash is not None:
        user.password_hash = password_hash
    if preferences is not None:
        user.preferences = preferences
    user.is_active = True
    user.updated_at = datetime.now(UTC)
    session.flush()
    return user


def update_user_preferences(
    session: Session,
    user: User,
    profile_name: str,
    preferences: dict,
) -> User:
    """Update the reader's saved paper preferences."""

    user.profile_name = profile_name
    user.preferences = preferences
    user.updated_at = datetime.now(UTC)
    session.flush()
    return user


def get_user(session: Session, user_id: int) -> User | None:
    """Return one reader by id."""

    return session.get(User, user_id)


def get_user_by_email(session: Session, email: str) -> User | None:
    """Return one reader by normalized email."""

    statement = select(User).where(User.email == email.strip().lower())
    return session.execute(statement).scalar_one_or_none()


def list_active_users(session: Session) -> list[User]:
    """List enabled reader accounts in creation order."""

    statement = select(User).where(User.is_active.is_(True)).order_by(User.created_at)
    return list(session.execute(statement).scalars())


def validate_email_address(email: str) -> str:
    """Require a syntactically valid email address."""

    normalized_email = email.strip().lower()
    if not EMAIL_ADDRESS_PATTERN.fullmatch(normalized_email):
        raise ValueError("Email must be a valid email address.")
    return normalized_email


def create_news_item(session: Session, item: ProcessedItem) -> NewsItem:
    """Create a curated news item without duplicate handling."""

    db_item = NewsItem(
        source=item.source,
        kind=item.kind,
        title=item.title,
        url=item.url,
        summary=item.summary,
        published_at=item.published_at,
        item_metadata=item.metadata,
        content=item.content,
    )
    session.add(db_item)
    session.flush()
    return db_item


def upsert_news_item(session: Session, item: ProcessedItem) -> NewsItem:
    """Insert or update an item matched by its publisher URL."""

    existing = get_news_item_by_url(session, item.url)
    if existing is None:
        return create_news_item(session, item)

    existing.source = item.source
    existing.kind = item.kind
    existing.title = item.title
    existing.summary = item.summary
    existing.published_at = item.published_at or existing.published_at
    existing.item_metadata = {**(existing.item_metadata or {}), **item.metadata}
    existing.content = item.content or existing.content
    existing.updated_at = datetime.now(UTC)
    session.flush()
    return existing


def upsert_news_items(
    session: Session,
    items: Iterable[ProcessedItem],
) -> list[NewsItem]:
    """Upsert a batch of normalized curated stories."""

    return [upsert_news_item(session, item) for item in items]


def get_news_item(session: Session, item_id: int) -> NewsItem | None:
    """Return one story by primary key."""

    return session.get(NewsItem, item_id)


def get_news_item_by_url(session: Session, url: str) -> NewsItem | None:
    """Return one story by its publisher URL."""

    statement = select(NewsItem).where(NewsItem.url == url)
    return session.execute(statement).scalar_one_or_none()


def list_news_items(
    session: Session,
    limit: int = 100,
    kind: str | None = None,
    source: str | None = None,
) -> list[NewsItem]:
    """List stored items newest first, with optional kind and source filters."""

    statement = select(NewsItem).order_by(NewsItem.scraped_at.desc()).limit(limit)
    if kind:
        statement = statement.where(NewsItem.kind == kind)
    if source:
        statement = statement.where(NewsItem.source == source)
    return list(session.execute(statement).scalars())


def list_recent_news_items(session: Session, hours: int = 24) -> list[NewsItem]:
    """List stories published or scraped inside a lookback window."""

    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    statement = (
        select(NewsItem)
        .where((NewsItem.published_at >= cutoff) | (NewsItem.scraped_at >= cutoff))
        .order_by(NewsItem.published_at.desc().nullslast(), NewsItem.scraped_at.desc())
    )
    return list(session.execute(statement).scalars())


def delete_news_item(session: Session, item_id: int) -> bool:
    """Delete one stored story by primary key."""

    result = session.execute(delete(NewsItem).where(NewsItem.id == item_id))
    return result.rowcount > 0
