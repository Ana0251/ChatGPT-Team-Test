"""H-09 table mapping. Alembic h09_0004 is the schema authority."""
from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, ForeignKeyConstraint,
    MetaData, String, Table, UniqueConstraint,
)

metadata = MetaData()

accounts = Table(
    "h09_accounts", metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36), ForeignKey("h05_companies.id"), nullable=False),
    Column("parent_id", String(36)),
    Column("code", String(64), nullable=False),
    Column("name", String(200), nullable=False),
    Column("level", String(16), nullable=False),
    Column("active", Boolean, nullable=False),
    Column("full_code", String(300), nullable=False),
    CheckConstraint("level IN ('group','general','subsidiary','detail')", name="h09_account_level"),
    CheckConstraint("length(code) BETWEEN 1 AND 64", name="h09_code_length"),
    CheckConstraint("length(name) BETWEEN 1 AND 200", name="h09_name_length"),
    CheckConstraint(
        "(level = 'group' AND parent_id IS NULL) OR "
        "(level <> 'group' AND parent_id IS NOT NULL)",
        name="h09_root_parent_required",
    ),
    UniqueConstraint("company_id", "id", name="uq_h09_company_id"),
    UniqueConstraint("company_id", "full_code", name="uq_h09_company_full_code"),
    ForeignKeyConstraint(
        ["company_id", "parent_id"], ["h09_accounts.company_id", "h09_accounts.id"],
        name="fk_h09_parent_same_company", ondelete="RESTRICT",
    ),
)
