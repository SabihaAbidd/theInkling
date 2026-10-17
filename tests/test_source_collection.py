"""Checks for bounded, partial-failure-safe curated source collection."""

import unittest
from threading import Barrier
from unittest.mock import patch

from app.scrapers.generic import scrape_all_sources
from app.scrapers.models import Article, NewsSource


class SourceCollectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = tuple(
            NewsSource(f"Source {index}", f"https://source{index}.example", "news")
            for index in range(4)
        )

    def test_explicit_empty_filter_and_zero_limit_collect_nothing(self) -> None:
        with (
            patch("app.scrapers.generic.SOURCES", self.sources),
            patch("app.scrapers.generic.scrape_source") as scrape,
        ):
            self.assertEqual(scrape_all_sources(source_names=[]), [])
            self.assertEqual(scrape_all_sources(max_sources=0), [])

        scrape.assert_not_called()

    def test_max_sources_limits_the_selected_source_set(self) -> None:
        def scrape(source: NewsSource, limit: int) -> list[Article]:
            return [Article(source.name, "Headline", f"{source.url}/story")]

        with (
            patch("app.scrapers.generic.SOURCES", self.sources),
            patch("app.scrapers.generic.scrape_source", side_effect=scrape),
        ):
            articles = scrape_all_sources(limit_per_source=2, max_sources=2)

        self.assertEqual([item.source for item in articles], ["Source 0", "Source 1"])

    def test_one_source_failure_preserves_other_source_results(self) -> None:
        def scrape(source: NewsSource, limit: int) -> list[Article]:
            if source.name == "Source 1":
                raise TimeoutError("source timed out")
            return [Article(source.name, "Headline", f"{source.url}/story")]

        with (
            patch("app.scrapers.generic.SOURCES", self.sources),
            patch("app.scrapers.generic.scrape_source", side_effect=scrape),
        ):
            articles = scrape_all_sources(
                source_names=[source.name for source in self.sources]
            )

        self.assertEqual(
            [item.source for item in articles], ["Source 0", "Source 2", "Source 3"]
        )

    def test_sources_are_fetched_concurrently_in_deterministic_order(self) -> None:
        barrier = Barrier(len(self.sources))

        def scrape(source: NewsSource, limit: int) -> list[Article]:
            barrier.wait(timeout=2)
            return [Article(source.name, "Headline", f"{source.url}/story")]

        with (
            patch("app.scrapers.generic.SOURCES", self.sources),
            patch("app.scrapers.generic.scrape_source", side_effect=scrape),
        ):
            articles = scrape_all_sources(max_sources=len(self.sources))

        self.assertEqual(
            [item.source for item in articles], [item.name for item in self.sources]
        )


if __name__ == "__main__":
    unittest.main()
