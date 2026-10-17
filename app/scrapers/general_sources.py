"""Curated non-niche news feeds for broad personal newspapers."""

from __future__ import annotations

from .models import NewsSource

GENERAL_SOURCES: tuple[NewsSource, ...] = (
    NewsSource(
        "BBC World",
        "https://www.bbc.com/news/world",
        "media",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        ("world", "politics"),
    ),
    NewsSource(
        "BBC Business",
        "https://www.bbc.com/news/business",
        "media",
        "https://feeds.bbci.co.uk/news/business/rss.xml",
        ("business", "economy"),
    ),
    NewsSource(
        "BBC Technology",
        "https://www.bbc.com/news/technology",
        "media",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        ("technology", "science"),
    ),
    NewsSource(
        "BBC Science and Environment",
        "https://www.bbc.com/news/science_and_environment",
        "media",
        "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
        ("science", "climate", "environment"),
    ),
    NewsSource(
        "The Guardian World",
        "https://www.theguardian.com/world",
        "media",
        "https://www.theguardian.com/world/rss",
        ("world", "politics"),
    ),
    NewsSource(
        "The Guardian Politics",
        "https://www.theguardian.com/politics",
        "media",
        "https://www.theguardian.com/politics/rss",
        ("politics", "world"),
    ),
    NewsSource(
        "The Guardian Business",
        "https://www.theguardian.com/business",
        "media",
        "https://www.theguardian.com/business/rss",
        ("business", "economy"),
    ),
    NewsSource(
        "The Guardian Technology",
        "https://www.theguardian.com/technology",
        "media",
        "https://www.theguardian.com/technology/rss",
        ("technology", "science"),
    ),
    NewsSource(
        "The Guardian Science",
        "https://www.theguardian.com/science",
        "media",
        "https://www.theguardian.com/science/rss",
        ("science", "health"),
    ),
    NewsSource(
        "The Guardian Environment",
        "https://www.theguardian.com/environment",
        "media",
        "https://www.theguardian.com/environment/rss",
        ("climate", "environment"),
    ),
    NewsSource(
        "The Guardian Culture",
        "https://www.theguardian.com/culture",
        "media",
        "https://www.theguardian.com/culture/rss",
        ("culture", "arts"),
    ),
    NewsSource(
        "NPR News",
        "https://www.npr.org/sections/news/",
        "media",
        "https://feeds.npr.org/1001/rss.xml",
        ("world", "politics", "society"),
    ),
    NewsSource(
        "NPR World",
        "https://www.npr.org/sections/world/",
        "media",
        "https://feeds.npr.org/1004/rss.xml",
        ("world", "politics"),
    ),
    NewsSource(
        "NASA News",
        "https://www.nasa.gov/news/",
        "official",
        "https://www.nasa.gov/news-release/feed/",
        ("science", "space", "technology"),
    ),
    NewsSource(
        "Nature Climate Change",
        "https://www.nature.com/subjects/climate-change",
        "research",
        "https://www.nature.com/subjects/climate-change.rss",
        ("climate", "science", "environment"),
    ),
    NewsSource(
        "Pew Research Center",
        "https://www.pewresearch.org/",
        "research",
        "https://www.pewresearch.org/feed/",
        ("society", "politics", "business", "science"),
    ),
    NewsSource(
        "Our World in Data",
        "https://ourworldindata.org/",
        "research",
        "https://ourworldindata.org/atom.xml",
        ("world", "science", "health", "climate", "society"),
    ),
    NewsSource(
        "The Conversation",
        "https://theconversation.com/global",
        "research",
        "https://theconversation.com/global/articles.atom",
        ("world", "science", "health", "culture", "business", "politics"),
    ),
)
