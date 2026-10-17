"""Data structures returned by website scrapers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewsSource:
    """A curated publication feed and the reader interests it can serve."""

    name: str
    url: str
    category: str
    feed_url: str | None = None
    topics: tuple[str, ...] = ()


@dataclass(frozen=True)
class Article:
    """A normalized article discovered from a news source."""

    source: str
    title: str
    url: str
    summary: str = ""
    published_at: datetime | None = None
