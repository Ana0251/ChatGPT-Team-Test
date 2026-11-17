"""Restricted out-of-band operator bootstrap. NOT a public HTTP registration API.

An operator supplies a high-entropy HESABYAR_OPERATOR_KEY through a protected
process environment; an approved private delivery callback receives the one-use
setup token. Neither the database nor standard output receives raw tokens.
"""
from __future__ import annotations

import hmac
import os
from collections.abc import Callable

from sqlalchemy import Engine, select

from app.modules.identity import tables as t
from app.modules.identity.security import digest, expiry, new_secret, normalize_email
from app.modules.identity.store import audit_event, locked, new_id
from app.modules.audit.store import record_event

Delivery = Callable[[str, str], None]


def provision_initial_owner(
    engine: Engine, *, operator_key: str, company_name: str, email: str, deliver: Delivery
) -> tuple[str, str]:
    expected = os.environ.get("HESABYAR_OPERATOR_KEY", "")
    if len(expected) < 32 or not hmac.compare_digest(operator_key, expected):
        raise PermissionError("Restricted operator authorization required")
    normalized = normalize_email(email)
    if not company_name.strip() or len(company_name) > 200:
        raise ValueError("Invalid company name")
    if not callable(deliver):
        raise ValueError("Private delivery callback required")

    company_id, user_id, token = new_id(), new_id(), new_secret()
    with locked(engine) as connection:
        if connection.execute(select(t.companies.c.id).limit(1)).first():
            raise ValueError("Initial owner bootstrap is allowed only for an empty installation")
        connection.execute(t.companies.insert().values(id=company_id, name=company_name.strip()))
        connection.execute(t.users.insert().values(id=user_id, email=normalized, active=False, password_hash=None))
        connection.execute(t.memberships.insert().values(user_id=user_id, company_id=company_id, role="owner"))
        connection.execute(t.setup_tokens.insert().values(
            token_hash=digest(token), user_id=user_id, company_id=company_id,
            expires_at=expiry(15), consumed_at=None,
        ))
        audit_event(connection, "operator_initial_owner_provisioned", user_id, company_id)
        record_event(connection, actor_id=user_id, company_id=company_id,
                     action="operator_initial_owner_provisioned",
                     safe_changes={"resource_id": company_id})
        # Deliver privately before commit: delivery errors roll back the DB transaction.
        # Delivery is trusted integration code; raw token MUST NOT be logged or sent via URL.
        deliver(normalized, token)
    return company_id, user_id
