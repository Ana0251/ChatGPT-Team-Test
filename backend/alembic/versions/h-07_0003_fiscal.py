"""H-07 fiscal years and fiscal periods, both company scoped.

Revision ID: h07_0003
Revises: h05_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "h07_0003"
down_revision = "h05_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "h07_fiscal_years",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=False),
        sa.Column("end_date", sa.String(10), nullable=False),
        sa.CheckConstraint("start_date < end_date", name="h07_year_valid_range"),
    )
    op.create_index("ix_h07_year_company_dates", "h07_fiscal_years",
                    ["company_id", "start_date", "end_date"])
    op.create_table(
        "h07_fiscal_periods",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), nullable=False),
        sa.Column("year_id", sa.String(36), sa.ForeignKey("h07_fiscal_years.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("start_date", sa.String(10), nullable=False),
        sa.Column("end_date", sa.String(10), nullable=False),
        sa.Column("status", sa.String(8), nullable=False, server_default="open"),
        sa.CheckConstraint("start_date < end_date", name="h07_period_valid_range"),
        sa.CheckConstraint("status IN ('open', 'closed')", name="h07_period_status_valid"),
    )
    op.create_index("ix_h07_period_year_dates", "h07_fiscal_periods",
                    ["year_id", "start_date", "end_date"])


def downgrade() -> None:
    op.drop_index("ix_h07_period_year_dates", table_name="h07_fiscal_periods")
    op.drop_table("h07_fiscal_periods")
    op.drop_index("ix_h07_year_company_dates", table_name="h07_fiscal_years")
    op.drop_table("h07_fiscal_years")
