"""H-05 Core tables. The Alembic h-05 revision is the schema authority."""
from sqlalchemy import (
    Boolean, CheckConstraint, Column, ForeignKey, Integer, MetaData,
    String, Table, Text,
)

metadata = MetaData()

companies = Table(
    "h05_companies", metadata,
    Column("id", String(36), primary_key=True),
    Column("name", String(200), nullable=False),
)
users = Table(
    "h05_users", metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(320), nullable=False, unique=True),
    Column("password_hash", Text),
    Column("active", Boolean, nullable=False),
)
memberships = Table(
    "h05_memberships", metadata,
    Column("user_id", String(36), ForeignKey("h05_users.id"), primary_key=True),
    Column("company_id", String(36), ForeignKey("h05_companies.id"), primary_key=True),
    Column("role", String(20), nullable=False),
    CheckConstraint("role IN ('owner','admin','accountant','viewer')", name="h05_role_valid"),
)
setup_tokens = Table(
    "h05_setup_tokens", metadata,
    Column("token_hash", String(64), primary_key=True),
    Column("user_id", String(36), ForeignKey("h05_users.id"), nullable=False),
    Column("company_id", String(36), ForeignKey("h05_companies.id"), nullable=False),
    Column("expires_at", String(32), nullable=False),
    Column("consumed_at", String(32)),
)
invitations = Table(
    "h05_invitations", metadata,
    Column("id", String(36), primary_key=True),
    Column("token_hash", String(64), nullable=False, unique=True),
    Column("company_id", String(36), ForeignKey("h05_companies.id"), nullable=False),
    Column("email", String(320), nullable=False),
    Column("role", String(20), nullable=False),
    Column("inviter_id", String(36), ForeignKey("h05_users.id"), nullable=False),
    Column("expires_at", String(32), nullable=False),
    Column("consumed_at", String(32)),
    CheckConstraint("role IN ('owner','admin','accountant','viewer')", name="h05_invite_role"),
)
sessions = Table(
    "h05_sessions", metadata,
    Column("id_hash", String(64), primary_key=True),
    Column("user_id", String(36), ForeignKey("h05_users.id")),
    Column("kind", String(8), nullable=False),
    Column("csrf_hash", String(64), nullable=False),
    Column("expires_at", String(32), nullable=False),
    Column("revoked_at", String(32)),
    CheckConstraint("kind IN ('pre','auth')", name="h05_session_kind"),
)
login_attempts = Table(
    "h05_login_attempts", metadata,
    Column("email_hash", String(64), primary_key=True),
    Column("failures", Integer, nullable=False),
    Column("locked_until", String(32)),
)
audit = Table(
    "h05_audit", metadata,
    Column("id", String(36), primary_key=True),
    Column("actor_id", String(36), ForeignKey("h05_users.id")),
    Column("company_id", String(36), ForeignKey("h05_companies.id")),
    Column("action", String(80), nullable=False),
    Column("occurred_at", String(32), nullable=False),
)
