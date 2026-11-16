"""H-09 additive multi-company account hierarchy.

Revision ID: h09_0004
Revises: h07_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "h09_0004"
down_revision = "h07_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "h09_accounts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), nullable=False),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("full_code", sa.String(300), nullable=False),
        sa.CheckConstraint("level IN ('group','general','subsidiary','detail')", name="h09_account_level"),
        sa.CheckConstraint("length(code) BETWEEN 1 AND 64", name="h09_code_length"),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 200", name="h09_name_length"),
        sa.CheckConstraint(
            "(level = 'group' AND parent_id IS NULL) OR "
            "(level <> 'group' AND parent_id IS NOT NULL)",
            name="h09_root_parent_required",
        ),
        sa.UniqueConstraint("company_id", "id", name="uq_h09_company_id"),
        sa.UniqueConstraint("company_id", "full_code", name="uq_h09_company_full_code"),
        sa.ForeignKeyConstraint(
            ["company_id", "parent_id"], ["h09_accounts.company_id", "h09_accounts.id"],
            name="fk_h09_parent_same_company", ondelete="RESTRICT",
        ),
    )
    op.create_index("ix_h09_company_parent", "h09_accounts", ["company_id", "parent_id"])


def downgrade() -> None:
    op.drop_index("ix_h09_company_parent", table_name="h09_accounts")
    op.drop_table("h09_accounts")
