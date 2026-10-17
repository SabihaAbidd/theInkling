"""Archive unused billing, digest, review, and scraper state tables."""

from __future__ import annotations

from alembic import op
from sqlalchemy import inspect

revision = "20261017_0002"
down_revision = "20261017_0001"
branch_labels = None
depends_on = None

RETIRED_TABLES = (
    "digest_items",
    "payment_transactions",
    "payment_subscriptions",
    "site_reviews",
    "source_runs",
)


def _rename_if_present(source_name: str, target_name: str) -> None:
    """Rename one legacy table while preserving all of its rows."""

    tables = set(inspect(op.get_bind()).get_table_names())
    if source_name not in tables:
        return
    if target_name in tables:
        raise RuntimeError(
            f"Cannot archive {source_name}: destination {target_name} already exists"
        )
    op.rename_table(source_name, target_name)


def upgrade() -> None:
    """Move unused tables out of the live schema without deleting their data."""

    for table_name in RETIRED_TABLES:
        _rename_if_present(table_name, f"legacy_{table_name}")


def downgrade() -> None:
    """Restore archived tables to their previous names."""

    for table_name in reversed(RETIRED_TABLES):
        _rename_if_present(f"legacy_{table_name}", table_name)
