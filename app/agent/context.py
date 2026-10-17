"""Typed shared state and per-run context for newspaper agent graphs."""

from __future__ import annotations

from typing import NotRequired, TypedDict


class ArticleRecord(TypedDict, total=False):
    """Article data shared between graph nodes."""

    id: int
    source: str
    kind: str
    title: str
    summary: str
    url: str
    content: str
    published_at: str | None
    score: float
    reasons: list[str]


class ReaderProfile(TypedDict, total=False):
    """Non-identifying preferences used to personalize an edition."""

    topics: list[str]
    keywords: list[str]
    excluded_keywords: list[str]
    preferred_sources: list[str]


class PaperState(TypedDict, total=False):
    """Canonical shared state; agents communicate through these fields."""

    reader_profile: ReaderProfile
    articles: list[ArticleRecord]
    ranked_articles: list[ArticleRecord]
    paper_articles: list[ArticleRecord]
    issues: list[str]
    quality_report: dict[str, int | bool]


class PaperRunContext(TypedDict):
    """Immutable runtime settings, kept separate from shared graph state."""

    model_name: str
    llm_enabled: bool
    max_articles: int
    run_id: NotRequired[str]
