"""H-07 SQLAlchemy Core mapping to additive Alembic h07_0003 tables."""
from sqlalchemy import CheckConstraint, Column, ForeignKey, MetaData, String, Table

metadata = MetaData()

years = Table(
    "h07_fiscal_years", metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36), ForeignKey("h05_companies.id"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("start_date", String(10), nullable=False),
    Column("end_date", String(10), nullable=False),
    CheckConstraint("start_date < end_date", name="h07_year_valid_range"),
)

periods = Table(
    "h07_fiscal_periods", metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36), ForeignKey("h05_companies.id"), nullable=False),
    Column("year_id", String(36), ForeignKey("h07_fiscal_years.id"), nullable=False),
    Column("name", String(200), nullable=False),
    Column("start_date", String(10), nullable=False),
    Column("end_date", String(10), nullable=False),
    Column("status", String(8), nullable=False),
    CheckConstraint("start_date < end_date", name="h07_period_valid_range"),
    CheckConstraint("status IN ('open', 'closed')", name="h07_period_status_valid"),
)
