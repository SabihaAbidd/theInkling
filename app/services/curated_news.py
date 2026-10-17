"""Curated publisher ingestion for personalized newspaper editions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.scrapers.generic import scrape_all_sources
from app.scrapers.models import NewsSource

from .models import ProcessedItem
from .process_articles import process_articles


def collect_curated_news(
    *,
    limit_per_source: int = 5,
    max_sources: int | None = None,
    sources: tuple[NewsSource, ...] | None = None,
    lookback_hours: int | None = 48,
) -> list[ProcessedItem]:
    """Fetch and normalize the selected publishers' recent articles."""

    source_names = [source.name for source in sources] if sources is not None else None
    articles = scrape_all_sources(
        limit_per_source=limit_per_source,
        max_sources=max_sources,
        source_names=source_names,
    )
    processed = process_articles(articles)
    return filter_by_lookback(processed, lookback_hours)


def filter_by_lookback(
    items: list[ProcessedItem], lookback_hours: int | None
) -> list[ProcessedItem]:
    """Keep dated stories in the requested window and retain undated stories."""

    if lookback_hours is None:
        return items

    cutoff = datetime.now(UTC) - timedelta(hours=lookback_hours)
    filtered: list[ProcessedItem] = []
    for item in items:
        published_at = item.published_at
        if published_at is None:
            filtered.append(item)
            continue
        if published_at.tzinfo is None:
            published_at = published_at.replace(tzinfo=UTC)
        if published_at >= cutoff:
            filtered.append(item)
    return filtered
