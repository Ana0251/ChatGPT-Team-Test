"""Minimal SQLite infrastructure baseline; no business or identity tables.

Revision ID: h04_0001
Revises:
Create Date: 2026-11-14
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "h04_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "h04_schema_baseline",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("h04_schema_baseline")
