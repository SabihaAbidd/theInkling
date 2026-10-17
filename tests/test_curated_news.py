"""Checks for normalizing publisher articles into the newspaper pipeline."""

import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from app.scrapers.models import Article, NewsSource
from app.services.curated_news import collect_curated_news


class CuratedNewsTests(unittest.TestCase):
    def test_collection_uses_selected_sources_and_lookback_window(self) -> None:
        now = datetime.now(UTC)
        sources = (NewsSource("Science Desk", "https://science.example", "science"),)
        articles = [
            Article(
                source="Science Desk",
                title="Recent report",
                url="https://science.example/recent",
                published_at=now - timedelta(hours=2),
            ),
            Article(
                source="Science Desk",
                title="Old report",
                url="https://science.example/old",
                published_at=now - timedelta(days=5),
            ),
            Article(
                source="Science Desk",
                title="Undated report",
                url="https://science.example/undated",
            ),
        ]

        with patch(
            "app.services.curated_news.scrape_all_sources", return_value=articles
        ) as scrape:
            collected = collect_curated_news(
                sources=sources,
                limit_per_source=3,
                max_sources=1,
                lookback_hours=48,
            )

        scrape.assert_called_once_with(
            limit_per_source=3,
            max_sources=1,
            source_names=["Science Desk"],
        )
        self.assertEqual(
            [item.title for item in collected], ["Recent report", "Undated report"]
        )


if __name__ == "__main__":
    unittest.main()
