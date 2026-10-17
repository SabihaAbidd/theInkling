"""Background work to build and persist a reader's daily newspaper."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime

from app.agent.edition_graph import create_edition
from app.database.connection import get_session
from app.database.models import User
from app.database.repository import (
    get_daily_edition_for_date,
    upsert_daily_edition,
    upsert_news_items,
)
from app.scrapers.sources import sources_for_topics
from app.services.news_surface import collect_ai_news
from app.worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="the_inkling.build_edition", bind=True, max_retries=2)
def build_edition_task(self, user_id: int, edition_date: str) -> dict:
    """Collect, personalize, and save one date-keyed newspaper edition."""

    target_date = date.fromisoformat(edition_date)
    with get_session() as session:
        user = session.get(User, user_id)
        if user is None or not user.is_active:
            return {"status": "failed", "error": "reader_not_found"}

        preferences = user.preferences or {}
        topics = preferences.get("topics", [])
        sources = sources_for_topics(topics)
        upsert_daily_edition(
            session,
            user_id=user_id,
            edition_date=target_date,
            status="running",
            job_id=self.request.id,
            title=preferences.get("paper_title", "The Inkling"),
        )

    try:
        items = collect_ai_news(
            source_limit=5,
            max_sources=min(len(sources), 30),
            source_names=[source.name for source in sources],
            lookback_hours=48,
            curate=False,
            store=False,
        )
        with get_session() as session:
            saved_items = upsert_news_items(session, items)
            candidates = [
                {
                    "id": item.id,
                    "source": item.source,
                    "kind": item.kind,
                    "title": item.title,
                    "summary": item.summary,
                    "url": item.url,
                    "content": item.content or "",
                    "published_at": (
                        item.published_at.isoformat() if item.published_at else None
                    ),
                }
                for item in saved_items
            ]
            reader = session.get(User, user_id)
            if reader is None:
                raise RuntimeError("reader_not_found")
            reader_preferences = reader.preferences or {}

            graph_result = create_edition(
                reader_profile={
                    "topics": reader_preferences.get("topics", []),
                    "keywords": reader_preferences.get("keywords", []),
                    "excluded_keywords": reader_preferences.get(
                        "excluded_keywords", []
                    ),
                    "preferred_sources": reader_preferences.get(
                        "preferred_sources", []
                    ),
                },
                articles=candidates,
                model_name=reader_preferences.get("model_name", ""),
                llm_enabled=reader_preferences.get("use_llm", True),
                max_articles=min(max(int(reader_preferences.get("top_n", 10)), 1), 20),
                run_id=self.request.id,
            )
            final_items = graph_result.get("paper_articles", [])
            finalized_at = datetime.now(UTC)
            edition = get_daily_edition_for_date(session, user_id, target_date)
            if edition is None:
                raise RuntimeError("edition_record_missing")
            edition.status = "ready"
            edition.editorial = _build_editorial(graph_result, finalized_at)
            edition.items_snapshot = final_items
            edition.generated_at = finalized_at
            edition.error_code = None
            session.flush()
            return {"status": "ready", "edition_id": edition.id}
    except Exception as exc:
        logger.exception("Daily edition generation failed for reader %s", user_id)
        with get_session() as session:
            edition = get_daily_edition_for_date(session, user_id, target_date)
            if edition is not None:
                edition.status = "failed"
                edition.error_code = type(exc).__name__[:80]
        raise self.retry(exc=exc, countdown=15 * (self.request.retries + 1))


def _build_editorial(graph_result: dict, generated_at: datetime) -> str:
    """Create a small machine-readable editorial summary for the edition."""

    report = graph_result.get("quality_report", {})
    issues = graph_result.get("issues", [])
    return (
        f"Prepared {report.get('article_count', 0)} stories at "
        f"{generated_at.isoformat()}. "
        f"Editorial notes: {', '.join(issues) if issues else 'quality checks passed'}."
    )
