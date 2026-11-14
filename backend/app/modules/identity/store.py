"""SQLite identity repository: short immediate transactions and no secret persistence."""
from __future__ import annotations

from contextlib import contextmanager
import os
from typing import Iterator
from uuid import uuid4

from sqlalchemy import Connection, Engine, select

from app.db.engine import create_sqlite_engine
from app.modules.identity import tables as t
from app.modules.identity.security import bound_csrf, digest, expiry, new_secret, now_string


@contextmanager
def locked(engine: Engine) -> Iterator[Connection]:
    """SQLite BEGIN IMMEDIATE serializes token redemption and membership writes."""
    with engine.connect() as connection:
        connection.exec_driver_sql("BEGIN IMMEDIATE")
        try:
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise


def new_id() -> str:
    return str(uuid4())


def audit_event(connection: Connection, action: str, actor: str | None = None, company: str | None = None) -> None:
    connection.execute(t.audit.insert().values(
        id=new_id(), action=action, actor_id=actor,
        company_id=company, occurred_at=now_string(),
    ))


def new_session(connection: Connection, kind: str, user_id: str | None = None) -> tuple[str, str]:
    sid = new_secret()
    expiration = expiry(60 if kind == "auth" else 15)
    csrf = bound_csrf(sid, expiration)
    connection.execute(t.sessions.insert().values(
        id_hash=digest(sid), user_id=user_id, kind=kind, csrf_hash=digest(csrf),
        expires_at=expiration, revoked_at=None,
    ))
    return sid, csrf


def get_session(connection: Connection, sid: str | None, kind: str | None = None) -> dict | None:
    if not sid:
        return None
    row = connection.execute(select(t.sessions).where(t.sessions.c.id_hash == digest(sid))).mappings().first()
    if not row or row["revoked_at"] or row["expires_at"] <= now_string():
        return None
    if kind is not None and row["kind"] != kind:
        return None
    return dict(row)


def revoke_session(connection: Connection, sid: str | None) -> None:
    if sid:
        connection.execute(t.sessions.update().where(t.sessions.c.id_hash == digest(sid)).values(revoked_at=now_string()))


def member_role(connection: Connection, user_id: str, company_id: str) -> str | None:
    return connection.execute(select(t.memberships.c.role).where(
        t.memberships.c.user_id == user_id,
        t.memberships.c.company_id == company_id,
    )).scalar_one_or_none()


def principal(connection: Connection, user_id: str) -> dict | None:
    user = connection.execute(select(t.users.c.id, t.users.c.email, t.users.c.active).where(t.users.c.id == user_id)).mappings().first()
    if not user or not user["active"]:
        return None
    rows = connection.execute(select(t.memberships).where(t.memberships.c.user_id == user_id)).mappings().all()
    return {"id": user["id"], "email": user["email"], "memberships": [
        {"user_id": row["user_id"], "company_id": row["company_id"], "role": row["role"]} for row in rows
    ]}


def configured_engine() -> Engine:
    """Use H-04 engine and its FK hook; fail closed without an explicit SQLite URL."""
    return create_sqlite_engine()
