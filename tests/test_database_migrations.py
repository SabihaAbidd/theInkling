"""Regression checks for fresh and legacy database migrations."""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DatabaseMigrationTests(unittest.TestCase):
    """Run Alembic in isolated SQLite files without touching developer data."""

    def _run_migration(self, database_path: Path, *arguments: str) -> None:
        database_url = f"sqlite:///{database_path.as_posix()}"
        environment = os.environ.copy()
        environment["DATABASE_URL"] = database_url
        subprocess.run(
            [sys.executable, "-m", "alembic", *arguments],
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

    def _upgrade(self, database_path: Path) -> None:
        self._run_migration(database_path, "upgrade", "head")

    def test_fresh_database_receives_newspaper_tables_and_version(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temporary_directory:
            database_path = Path(temporary_directory) / "fresh.db"

            self._upgrade(database_path)
            self._upgrade(database_path)

            with closing(sqlite3.connect(database_path)) as connection:
                tables = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertTrue(
                    {
                        "users",
                        "news_items",
                        "daily_editions",
                        "reader_feedback",
                        "alembic_version",
                    }.issubset(tables)
                )
                self.assertFalse(
                    {
                        "digest_items",
                        "payment_subscriptions",
                        "payment_transactions",
                        "site_reviews",
                        "source_runs",
                    }
                    & tables
                )
                version = connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()
                self.assertEqual(version[0], "20261017_0002")

    def test_existing_user_data_survives_schema_upgrade(self) -> None:
        with tempfile.TemporaryDirectory(dir=PROJECT_ROOT) as temporary_directory:
            database_path = Path(temporary_directory) / "legacy.db"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.execute(
                    "CREATE TABLE users ("
                    "id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                    "email TEXT NOT NULL, profile_name TEXT NOT NULL, "
                    "is_active BOOLEAN NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO users (id, name, email, profile_name, is_active) "
                    "VALUES (7, 'Legacy Reader', 'reader@example.com', 'reader', 1)"
                )
                connection.execute(
                    "CREATE TABLE site_reviews ("
                    "id INTEGER PRIMARY KEY, rating INTEGER NOT NULL)"
                )
                connection.execute(
                    "INSERT INTO site_reviews (id, rating) VALUES (11, 5)"
                )
                connection.commit()

            self._upgrade(database_path)

            with closing(sqlite3.connect(database_path)) as connection:
                reader = connection.execute(
                    "SELECT id, name, email FROM users WHERE id = 7"
                ).fetchone()
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(users)")
                }
                archived_review = connection.execute(
                    "SELECT id, rating FROM legacy_site_reviews WHERE id = 11"
                ).fetchone()
                table_names = {
                    row[0]
                    for row in connection.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                self.assertEqual(reader, (7, "Legacy Reader", "reader@example.com"))
                self.assertTrue({"password_hash", "preferences"}.issubset(columns))
                self.assertEqual(archived_review, (11, 5))
                self.assertNotIn("site_reviews", table_names)

            self._run_migration(database_path, "downgrade", "20261017_0001")
            with closing(sqlite3.connect(database_path)) as connection:
                restored_review = connection.execute(
                    "SELECT id, rating FROM site_reviews WHERE id = 11"
                ).fetchone()
                self.assertEqual(restored_review, (11, 5))

            self._upgrade(database_path)


if __name__ == "__main__":
    unittest.main()
