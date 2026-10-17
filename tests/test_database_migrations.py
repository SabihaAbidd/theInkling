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

    def _upgrade(self, database_path: Path) -> None:
        database_url = f"sqlite:///{database_path.as_posix()}"
        environment = os.environ.copy()
        environment["DATABASE_URL"] = database_url
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        )

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
                version = connection.execute(
                    "SELECT version_num FROM alembic_version"
                ).fetchone()
                self.assertEqual(version[0], "20261017_0001")

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
                connection.commit()

            self._upgrade(database_path)

            with closing(sqlite3.connect(database_path)) as connection:
                reader = connection.execute(
                    "SELECT id, name, email FROM users WHERE id = 7"
                ).fetchone()
                columns = {
                    row[1] for row in connection.execute("PRAGMA table_info(users)")
                }
                self.assertEqual(reader, (7, "Legacy Reader", "reader@example.com"))
                self.assertTrue(
                    {
                        "password_hash",
                        "stripe_customer_id",
                        "plan_name",
                        "subscription_status",
                        "email_verified",
                        "preferences",
                    }.issubset(columns)
                )


if __name__ == "__main__":
    unittest.main()
