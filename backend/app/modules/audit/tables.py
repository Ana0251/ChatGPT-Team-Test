"""SQLAlchemy Core layout for H-10 append-only audit events."""
from sqlalchemy import (
    CheckConstraint, Column, ForeignKey, Index, MetaData, String, Table, Text,
)

metadata = MetaData()

events = Table(
    "h10_audit_events", metadata,
    Column("id", String(36), primary_key=True),
    Column("company_id", String(36),
           ForeignKey("h05_companies.id", ondelete="RESTRICT"), nullable=False),
    Column("actor_id", String(36),
           ForeignKey("h05_users.id", ondelete="RESTRICT"), nullable=False),
    Column("action", String(80), nullable=False),
    Column("occurred_at", String(32), nullable=False),
    Column("safe_changes", Text()),
    CheckConstraint("length(action) BETWEEN 1 AND 80", name="h10_action_nonempty"),
    CheckConstraint(
        "length(occurred_at) = 32 AND substr(occurred_at, -6) = '+00:00'",
        name="h10_utc_timestamp",
    ),
    CheckConstraint(
        "safe_changes IS NULL OR (json_valid(safe_changes) AND json_type(safe_changes) = 'object')",
        name="h10_changes_json_object",
    ),
    Index("ix_h10_company_time_id", "company_id", "occurred_at", "id"),
    Index("ix_h10_company_actor", "company_id", "actor_id"),
)
