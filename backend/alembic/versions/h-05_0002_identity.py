"""H-05 isolated identity, authorization, invitation and session tables.

Revision ID: h05_0002
Revises: h04_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "h05_0002"
down_revision = "h04_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "h05_companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
    )
    op.create_table(
        "h05_users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_table(
        "h05_memberships",
        sa.Column("user_id", sa.String(36), sa.ForeignKey("h05_users.id"), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False),
        sa.CheckConstraint("role IN ('owner','admin','accountant','viewer')", name="h05_role_valid"),
    )
    op.create_table(
        "h05_setup_tokens",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("h05_users.id"), nullable=False),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), nullable=False),
        sa.Column("expires_at", sa.String(32), nullable=False),
        sa.Column("consumed_at", sa.String(32), nullable=True),
    )
    op.create_table(
        "h05_invitations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("inviter_id", sa.String(36), sa.ForeignKey("h05_users.id"), nullable=False),
        sa.Column("expires_at", sa.String(32), nullable=False),
        sa.Column("consumed_at", sa.String(32), nullable=True),
        sa.CheckConstraint("role IN ('owner','admin','accountant','viewer')", name="h05_invite_role"),
    )
    op.create_index("ix_h05_invitation_pending", "h05_invitations", ["company_id", "email"])
    op.create_table(
        "h05_sessions",
        sa.Column("id_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("h05_users.id"), nullable=True),
        sa.Column("kind", sa.String(8), nullable=False),
        sa.Column("csrf_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.String(32), nullable=False),
        sa.Column("revoked_at", sa.String(32), nullable=True),
        sa.CheckConstraint("kind IN ('pre','auth')", name="h05_session_kind"),
    )
    op.create_index("ix_h05_sessions_user", "h05_sessions", ["user_id"])
    op.create_table(
        "h05_login_attempts",
        sa.Column("email_hash", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.String(32), nullable=True),
    )
    op.create_table(
        "h05_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("actor_id", sa.String(36), sa.ForeignKey("h05_users.id"), nullable=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("h05_companies.id"), nullable=True),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.String(32), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("h05_audit")
    op.drop_table("h05_login_attempts")
    op.drop_index("ix_h05_sessions_user", table_name="h05_sessions")
    op.drop_table("h05_sessions")
    op.drop_index("ix_h05_invitation_pending", table_name="h05_invitations")
    op.drop_table("h05_invitations")
    op.drop_table("h05_setup_tokens")
    op.drop_table("h05_memberships")
    op.drop_table("h05_users")
    op.drop_table("h05_companies")
