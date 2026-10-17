"""Compatibility helpers for upgrading legacy user tables."""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Connection, Engine

USER_COLUMN_DEFINITIONS = {
    "password_hash": "TEXT",
    "preferences": "JSON NOT NULL DEFAULT '{}'",
}


def ensure_user_columns(bind: Engine | Connection) -> None:
    """Add account fields missing from databases created by the old app."""

    inspector = inspect(bind)
    if "users" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("users")}
    missing_columns = [
        (name, definition)
        for name, definition in USER_COLUMN_DEFINITIONS.items()
        if name not in existing_columns
    ]
    if not missing_columns:
        return

    def add_columns(connection: Connection) -> None:
        for name, definition in missing_columns:
            connection.execute(
                text(f"ALTER TABLE users ADD COLUMN {name} {definition}")
            )

    if isinstance(bind, Connection):
        add_columns(bind)
    else:
        with bind.begin() as connection:
            add_columns(connection)
