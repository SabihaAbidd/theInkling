"""Create the current newspaper schema and mark legacy installations."""

from __future__ import annotations

from alembic import op
from app.database import models as _models  # noqa: F401
from app.database.connection import Base
from app.database.schema_compat import ensure_user_columns

revision = "20261017_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create missing tables; leave existing account and article data in place."""

    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    ensure_user_columns(bind)


def downgrade() -> None:
    """Preserve baseline tables because they may contain user data."""

    pass
