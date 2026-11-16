"""Trusted internal H-10 audit writer, for future Manager-approved mutation hooks.

No public HTTP mutation route exists. The caller MUST reuse the very same
active SQLAlchemy transaction as the underlying business change. The helper
does not commit or open a separate transaction. In this stage, old modules
have NOT been changed to call it; coverage is explicitly incomplete.
"""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import Connection, select

from app.modules.audit import tables as a
from app.modules.identity import tables as identity
from app.modules.identity.security import now_string
from app.modules.identity.store import new_id

# Known success actions only. In particular, login failures/successes and
# logout have no unambiguous company attribution and MUST NOT be fabricated.
ACTIONS = frozenset({
    "operator_initial_owner_provisioned",
    "initial_owner_activated",
    "invitation_new_user_activated",
    "invitation_existing_user_accepted",
    "membership_invitation_created",
    "company_created",
    "fiscal_year_created",
    "fiscal_period_created",
    "fiscal_period_closed",
    "account_created",
    "account_updated",
    "account_deleted",
})

LEVELS = frozenset({"group", "general", "subsidiary", "detail"})
ROLES = frozenset({"owner", "admin", "accountant", "viewer"})
STATUSES = frozenset({"open", "closed"})


def canonical_uuid(value: str) -> bool:
    if type(value) is not str:
        return False
    try:
        return str(UUID(value)) == value
    except (ValueError, AttributeError):
        return False


def safe_payload(changes: dict | None) -> str | None:
    """Allow only known non-sensitive typed fields; block secrets by default."""
    if changes is None:
        return None
    if type(changes) is not dict:
        raise ValueError("safe_changes must be an object or absent")
    for key, value in changes.items():
        if type(key) is not str:
            raise ValueError("Invalid safe_changes key")
        valid = (
            (key == "resource_id" and canonical_uuid(value))
            or (key == "level" and type(value) is str and value in LEVELS)
            or (key == "role" and type(value) is str and value in ROLES)
            or (key == "status" and type(value) is str and value in STATUSES)
            or (key == "active" and type(value) is bool)
        )
        if not valid:
            raise ValueError("Unsafe or unsupported audit metadata")
    return json.dumps(changes, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def record_event(
    conn: Connection, *, actor_id: str, company_id: str, action: str,
    safe_changes: dict | None = None,
) -> str:
    """Append exactly one server-attributed audit event to an existing txn.

    A real user and company membership is required at the time of recording.
    Neither actor/company IDs nor timestamps may originate from a client
    payload. A failure propagates to the caller's transaction for rollback.
    """
    if not conn.in_transaction():
        raise ValueError("An existing business transaction is required")
    if not canonical_uuid(actor_id) or not canonical_uuid(company_id):
        raise ValueError("Actual canonical user and company UUIDs are required")
    if type(action) is not str or action not in ACTIONS:
        raise ValueError("Unknown audit action")
    encoded = safe_payload(safe_changes)
    membership = conn.execute(select(identity.memberships.c.user_id).where(
        identity.memberships.c.user_id == actor_id,
        identity.memberships.c.company_id == company_id,
    )).first()
    if membership is None:
        raise ValueError("Actor is not a member of the event's company")
    event_id = new_id()
    conn.execute(a.events.insert().values(
        id=event_id, company_id=company_id, actor_id=actor_id,
        action=action, occurred_at=now_string(), safe_changes=encoded,
    ))
    return event_id
