"""Queue concurrency behavior for date-keyed newspaper editions."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app import web
from sqlalchemy.exc import IntegrityError


class PaperQueueConcurrencyTests(TestCase):
    """Concurrent create requests return the unique winning edition row."""

    def test_unique_date_race_returns_existing_queued_edition(self) -> None:
        now = datetime.now(UTC)
        existing_edition = SimpleNamespace(
            id=17,
            edition_date=now.date(),
            status="queued",
            job_id="winner-job",
            title="The Inkling",
            editorial="",
            items_snapshot=[],
            error_code=None,
            created_at=now,
            generated_at=None,
        )
        unique_conflict = IntegrityError("insert", {}, RuntimeError("unique"))

        with (
            patch.object(web, "get_session", side_effect=lambda: nullcontext(object())),
            patch.object(
                web,
                "get_daily_edition_for_date",
                side_effect=[None, existing_edition],
            ),
            patch.object(web, "upsert_daily_edition", side_effect=unique_conflict),
            patch.object(web.build_edition_task, "apply_async") as enqueue,
        ):
            response = web.request_daily_paper(user=SimpleNamespace(id=3))

        self.assertEqual(response["id"], existing_edition.id)
        self.assertEqual(response["status"], "queued")
        self.assertEqual(response["job_id"], "winner-job")
        enqueue.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
