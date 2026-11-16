"""H-10 append-only, tenant-scoped audit snapshot and future event store.

Revision ID: h10_0005
Revises: h09_0004

Existing H-05 security/rate-limit logs stay untouched. Only eligible historic
events with a REAL actor and company are snapshotted; NULL/unattributed
login/logout records are deliberately not converted into fabricated tenants.
The explicit triggers forbid UPDATE/DELETE of H-10 history, not implicitly
capture mutations in other modules (those require separately approved hooks).
"""
from alembic import op
import sqlalchemy as sa

revision = "h10_0005"
down_revision = "h09_0004"
branch_labels = None
depends_on = None

# All of these are existing H-05 actions whose company/actor provenance is real.
LEGACY_COMPANY_ACTIONS = (
    "operator_initial_owner_provisioned",
    "initial_owner_activated",
    "invitation_new_user_activated",
    "invitation_existing_user_accepted",
    "membership_invitation_created",
    "fiscal_period_closed",
)


def upgrade() -> None:
    op.create_table(
        "h10_audit_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36),
                  sa.ForeignKey("h05_companies.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("actor_id", sa.String(36),
                  sa.ForeignKey("h05_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("occurred_at", sa.String(32), nullable=False),
        sa.Column("safe_changes", sa.Text(), nullable=True),
        sa.CheckConstraint("length(action) BETWEEN 1 AND 80", name="h10_action_nonempty"),
        sa.CheckConstraint(
            "length(occurred_at) = 32 AND substr(occurred_at, -6) = '+00:00'",
            name="h10_utc_timestamp",
        ),
        sa.CheckConstraint(
            "safe_changes IS NULL OR (json_valid(safe_changes) AND json_type(safe_changes) = 'object')",
            name="h10_changes_json_object",
        ),
    )
    op.create_index(
        "ix_h10_company_time_id", "h10_audit_events",
        ["company_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_h10_company_actor", "h10_audit_events", ["company_id", "actor_id"],
    )

    # One-time migration of already existing, attributable H-05 audit history.
    # This is a snapshot, NOT a trigger: subsequent H-05 events require approved
    # same-transaction H-10 hooks before they appear here.
    bind = op.get_bind()
    stmt = sa.text(
        "INSERT INTO h10_audit_events "
        "(id, company_id, actor_id, action, occurred_at, safe_changes) "
        "SELECT id, company_id, actor_id, action, occurred_at, NULL FROM h05_audit "
        "WHERE actor_id IS NOT NULL AND company_id IS NOT NULL "
        "AND length(occurred_at) = 32 AND substr(occurred_at, -6) = '+00:00' "
        "AND action IN (" + ",".join(f":a{i}" for i in range(len(LEGACY_COMPANY_ACTIONS))) + ")"
    )
    bind.execute(stmt, {f"a{i}": action for i, action in enumerate(LEGACY_COMPANY_ACTIONS)})

    # Explicit immutability of the NEW table only; never tamper with H-05 quota
    # data or invent cross-module event capture via hidden triggers.
    op.execute(
        "CREATE TRIGGER h10_audit_no_update BEFORE UPDATE ON h10_audit_events "
        "BEGIN SELECT RAISE(ABORT, 'AUDIT_APPEND_ONLY'); END"
    )
    op.execute(
        "CREATE TRIGGER h10_audit_no_delete BEFORE DELETE ON h10_audit_events "
        "BEGIN SELECT RAISE(ABORT, 'AUDIT_APPEND_ONLY'); END"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER h10_audit_no_delete")
    op.execute("DROP TRIGGER h10_audit_no_update")
    op.drop_index("ix_h10_company_actor", table_name="h10_audit_events")
    op.drop_index("ix_h10_company_time_id", table_name="h10_audit_events")
    op.drop_table("h10_audit_events")
