"""Generic website and RSS scraping helpers for curated news sources."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from email.utils import parsedate_to_datetime
from functools import partial
from html import unescape
from urllib.parse import urljoin

import feedparser
import requests
from bs4 import BeautifulSoup

from .models import Article, NewsSource
from .sources import SOURCES

DEFAULT_TIMEOUT = 20
MAX_CONCURRENT_SOURCES = 8
logger = logging.getLogger(__name__)
HEADERS = {
    "User-Agent": "TheInkling/1.0 (personalized news reader)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def scrape_all_sources(
    limit_per_source: int = 10,
    max_sources: int | None = None,
    source_names: list[str] | tuple[str, ...] | None = None,
) -> list[Article]:
    """Scrape every configured curated news source."""

    if limit_per_source <= 0:
        return []

    articles: list[Article] = []
    selected_sources = SOURCES
    if source_names is not None:
        allowed_names = {name.strip().lower() for name in source_names if name.strip()}
        selected_sources = tuple(
            source
            for source in selected_sources
            if source.name.lower() in allowed_names
        )
    if max_sources is not None:
        selected_sources = selected_sources[: max(0, max_sources)]
    if not selected_sources:
        return []

    scrape_selected = partial(_scrape_source_safely, limit=limit_per_source)
    with ThreadPoolExecutor(
        max_workers=min(MAX_CONCURRENT_SOURCES, len(selected_sources)),
        thread_name_prefix="inkling-source",
    ) as executor:
        for source_articles in executor.map(scrape_selected, selected_sources):
            articles.extend(source_articles)
    return dedupe_articles(articles)


def _scrape_source_safely(source: NewsSource, *, limit: int) -> list[Article]:
    """Isolate source failures so concurrent collection can keep partial results."""

    try:
        return scrape_source(source, limit=limit)
    except Exception as exc:
        logger.warning("Skipping source %s: %s", source.name, exc)
        return []


def scrape_source(source: NewsSource, limit: int = 10) -> list[Article]:
    """Scrape one source, preferring RSS/Atom when configured."""

    if limit <= 0:
        return []

    if source.feed_url:
        feed_articles = scrape_feed(source, limit=limit)
        if feed_articles:
            return feed_articles
    return scrape_listing_page(source, limit=limit)


def scrape_feed(source: NewsSource, limit: int = 10) -> list[Article]:
    """Read articles from an RSS or Atom feed."""

    response = requests.get(
        source.feed_url or source.url,
        headers=HEADERS,
        timeout=DEFAULT_TIMEOUT,
    )
    response.raise_for_status()
    parsed = feedparser.parse(response.content)
    articles: list[Article] = []
    for entry in parsed.entries[:limit]:
        title = clean_text(getattr(entry, "title", ""))
        url = getattr(entry, "link", "")
        summary = clean_text(getattr(entry, "summary", ""))
        published_at = parse_entry_date(entry)
        if title and url:
            articles.append(
                Article(
                    source=source.name,
                    title=title,
                    url=url,
                    summary=summary,
                    published_at=published_at,
                )
            )
    return articles


def scrape_listing_page(source: NewsSource, limit: int = 10) -> list[Article]:
    """Find likely article links on a source listing page."""

    response = requests.get(source.url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    articles: list[Article] = []
    seen_urls: set[str] = set()
    for link in soup.select(
        "article a[href], h1 a[href], h2 a[href], h3 a[href], a[href]"
    ):
        title = clean_text(link.get_text(" "))
        url = urljoin(source.url, link.get("href", ""))
        if not is_probable_article(title, url, source.url) or url in seen_urls:
            continue
        seen_urls.add(url)
        articles.append(Article(source=source.name, title=title, url=url))
        if len(articles) >= limit:
            break
    return articles


def dedupe_articles(articles: list[Article]) -> list[Article]:
    """Remove duplicate article URLs while keeping source order."""

    deduped: list[Article] = []
    seen: set[str] = set()
    for article in articles:
        normalized_url = article.url.rstrip("/")
        if normalized_url in seen:
            continue
        seen.add(normalized_url)
        deduped.append(article)
    return deduped


def parse_entry_date(entry: object) -> datetime | None:
    """Parse common feed date fields into a datetime."""

    for field in ("published", "updated", "created"):
        value = getattr(entry, field, None)
        if not value:
            continue
        try:
            return parsedate_to_datetime(value)
        except (TypeError, ValueError):
            continue
    return None


def clean_text(value: str) -> str:
    """Normalize whitespace and strip HTML from a string."""

    text = BeautifulSoup(value or "", "html.parser").get_text(" ")
    return " ".join(unescape(text).split())


def is_probable_article(title: str, url: str, base_url: str) -> bool:
    """Filter navigation links while keeping likely article links."""

    if not title or len(title) < 12 or not url.startswith(("http://", "https://")):
        return False
    ignored = ("#", "mailto:", "javascript:", ".pdf")
    if any(token in url.lower() for token in ignored):
        return False
    nav_titles = {
        "about",
        "advertise",
        "careers",
        "contact",
        "home",
        "login",
        "privacy",
        "subscribe",
        "terms",
        "topics",
        "events",
        "newsletter",
        "podcasts",
        "skip to main content",
    }
    if title.strip().lower() in nav_titles:
        return False
    return True
