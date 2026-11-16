"""H-10 owner-run targets: isolated SQLite AuditEvent, redaction and migration.

Legacy modules are deliberately NOT patched in this phase; recording their
mutations atomically is NOT_TESTED pending Manager's hook authorization.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.db.engine import create_sqlite_engine
from app.main import create_app
from app.modules.audit import tables as a
from app.modules.audit.store import record_event
from app.modules.identity import tables as t
from app.modules.identity.provision import provision_initial_owner
from app.modules.identity.security import now_string, password_hash
from app.modules.identity.store import audit_event, locked, new_id

BASE = "/api/v1"
PASSWORD = "ValidOwnerPassword123"
MEMBER_PASSWORD = "AnotherValidPassword123"


def cfg() -> Config:
    return Config(str(Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"))


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    url = f"sqlite:///{(tmp_path / 'h10.db').as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    monkeypatch.setenv("HESABYAR_ALLOWED_ORIGIN", "https://testserver")
    key = "h10-operator-secret-key-32characters-123"
    monkeypatch.setenv("HESABYAR_OPERATOR_KEY", key)
    monkeypatch.setenv("HESABYAR_LOGIN_PEPPER", "h10-pepper-secret-32characters-123")
    command.upgrade(cfg(), "head")
    engine = create_sqlite_engine(url)
    tokens: list[str] = []

    def deliver(email, token):
        tokens.append(token)

    company_id, owner_id = provision_initial_owner(
        engine, operator_key=key, company_name="H10 company",
        email="h10owner@example.test", deliver=deliver,
    )
    app = create_app()
    app.state.identity_engine = engine
    app.state.identity_delivery = deliver
    with TestClient(app, base_url="https://testserver") as client:
        yield {
            "client": client, "engine": engine, "company": company_id,
            "owner": owner_id, "tokens": tokens,
        }
    engine.dispose()


def url(env, company=None):
    return f"{BASE}/companies/{company or env['company']}/audit-events"


def csrf(client):
    result = client.get(f"{BASE}/auth/csrf")
    assert result.status_code == 200, result.text
    return {"Origin": "https://testserver", "X-CSRF-Token": result.json()["csrf_token"]}


def login_owner(env):
    client = env["client"]
    created = client.post(f"{BASE}/auth/activate", headers=csrf(client), json={
        "token": env["tokens"][0], "password": PASSWORD,
    })
    assert created.status_code == 204, created.text
    result = client.post(f"{BASE}/auth/login", headers=csrf(client), json={
        "email": "h10owner@example.test", "password": PASSWORD,
    })
    assert result.status_code == 200, result.text
    return csrf(client)


def add_member(env, role, email):
    uid = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.users.insert().values(
            id=uid, email=email, password_hash=password_hash(MEMBER_PASSWORD), active=True,
        ))
        conn.execute(t.memberships.insert().values(
            user_id=uid, company_id=env["company"], role=role,
        ))
    return uid


def login_member(env, email):
    c = env["client"]
    response = c.post(f"{BASE}/auth/login", headers=csrf(c), json={
        "email": email, "password": MEMBER_PASSWORD,
    })
    assert response.status_code == 200, response.text


def seed(env, action="account_created", safe=None):
    with locked(env["engine"]) as conn:
        return record_event(
            conn, actor_id=env["owner"], company_id=env["company"],
            action=action, safe_changes=safe,
        )


def test_unauthenticated_and_owner_empty_audit_page(env):
    c = env["client"]
    assert c.get(url(env)).status_code == 401
    login_owner(env)
    response = c.get(url(env))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}
    # No public mutation API: GET-only.
    assert c.post(url(env), json={"action": "account_created"}).status_code == 405
    assert c.delete(url(env)).status_code == 405
    assert c.patch(url(env), json={"action": "forged"}).status_code == 405


def test_real_actor_company_utc_and_stable_pagination(env):
    login_owner(env)
    names = ["account_created", "account_updated", "account_deleted"]
    ids = [
        seed(env, name, {"resource_id": new_id(), "active": True, "level": "detail"})
        for name in names
    ]
    first = env["client"].get(url(env), params={"page_size": 2})
    assert first.status_code == 200
    data = first.json()
    assert data["total"] == 3 and data["page"] == 1 and data["page_size"] == 2
    assert len(data["items"]) == 2
    second = env["client"].get(url(env), params={"page_size": 2, "page": 2})
    assert second.status_code == 200
    assert len(second.json()["items"]) == 1
    all_items = data["items"] + second.json()["items"]
    assert {item["id"] for item in all_items} == set(ids)
    assert all_items == sorted(all_items, key=lambda row: (
        row["occurred_at"], row["id"],
    ), reverse=True)
    for item in all_items:
        assert set(item) == {
            "id", "company_id", "actor_id", "action", "occurred_at", "safe_changes",
        }
        assert str(UUID(item["id"])) == item["id"]
        assert item["actor_id"] == env["owner"]
        assert item["company_id"] == env["company"]
        date = datetime.fromisoformat(item["occurred_at"])
        assert date.utcoffset() == timedelta(0)
        assert abs(datetime.now(timezone.utc) - date) < timedelta(minutes=2)
        assert set(item["safe_changes"]) == {"resource_id", "active", "level"}
    beyond = env["client"].get(url(env), params={"page_size": 2, "page": 3})
    assert beyond.status_code == 200 and beyond.json()["items"] == []
    assert beyond.json()["total"] == 3


@pytest.mark.parametrize("query", [
    {"page": 0}, {"page": -1}, {"page_size": 0}, {"page_size": 101},
    {"page": "x"}, {"page_size": "abc"},
])
def test_invalid_pagination_rejected(env, query):
    login_owner(env)
    result = env["client"].get(url(env), params=query)
    assert result.status_code == 422


def test_nonmember_unknown_tenant_and_bad_company_uuid_hidden(env):
    login_owner(env)
    foreign = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.companies.insert().values(id=foreign, name="Hidden company"))
    c = env["client"]
    foreign_resp = c.get(url(env, foreign))
    missing_resp = c.get(url(env, new_id()))
    assert foreign_resp.status_code == missing_resp.status_code == 404
    assert foreign_resp.json()["error"]["code"] == missing_resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert c.get(url(env, "bad-uuid")).status_code == 422


@pytest.mark.parametrize("role,expected", [
    ("owner", 200), ("admin", 200), ("viewer", 403), ("accountant", 403),
])
def test_company_roles_are_rechecked_per_request(env, role, expected):
    c = env["client"]
    owner_headers = login_owner(env)
    seed(env)
    if role != "owner":
        add_member(env, role, f"{role}-h10@example.test")
        assert c.post(f"{BASE}/auth/logout", headers=owner_headers).status_code == 204
        login_member(env, f"{role}-h10@example.test")
    result = c.get(url(env))
    assert result.status_code == expected, result.text
    if role in ("owner", "admin"):
        assert result.json()["total"] == 1
    else:
        assert result.json()["error"]["code"] == "ACCESS_DENIED"


def test_revoked_membership_and_expired_session_are_denied(env):
    c = env["client"]
    login_owner(env)
    with locked(env["engine"]) as conn:
        conn.execute(t.memberships.delete().where(
            t.memberships.c.user_id == env["owner"],
            t.memberships.c.company_id == env["company"],
        ))
    assert c.get(url(env)).status_code == 404
    with locked(env["engine"]) as conn:
        conn.execute(t.memberships.insert().values(
            user_id=env["owner"], company_id=env["company"], role="owner",
        ))
        # Revoke current user sessions to prove per-request H05 auth is live.
        conn.execute(t.sessions.update().where(
            t.sessions.c.user_id == env["owner"],
        ).values(revoked_at=now_string()))
    assert c.get(url(env)).status_code == 401


@pytest.mark.parametrize("bad", [
    {"password": "raw-secret"}, {"token": "private"}, {"email": "private@example.test"},
    {"csrf": "sensitive"}, {"session": "secret"}, {"role": "superadmin"},
    {"status": "posted"}, {"active": 1}, {"level": 123},
    {"resource_id": "forged"}, {"resource_id": "x" * 36},
    {"nested": {"credential": "secret"}},
])
def test_sensitive_or_malformed_safe_changes_fail_closed(env, bad):
    with pytest.raises(ValueError):
        seed(env, safe=bad)
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 0


def test_record_event_requires_real_scoped_actor_and_no_client_time(env):
    with locked(env["engine"]) as conn:
        for actor, company in [
            (new_id(), env["company"]), (env["owner"], new_id()),
            ("not-a-uuid", env["company"]), (env["owner"], "not-a-uuid"),
        ]:
            with pytest.raises(ValueError):
                record_event(conn, actor_id=actor, company_id=company, action="account_created")
        with pytest.raises(ValueError):
            record_event(conn, actor_id=env["owner"], company_id=env["company"],
                         action="login_rejected")
        with pytest.raises(TypeError):
            record_event(conn, actor_id=env["owner"], company_id=env["company"],
                         action="account_created", occurred_at="2000-01-01T00:00:00+00:00")
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 0


def test_update_delete_are_rejected_by_database_and_api(env):
    login_owner(env)
    event_id = seed(env, safe={"role": "admin"})
    c = env["client"]
    assert c.put(url(env), json={"action": "mutated"}).status_code == 405
    with env["engine"].connect() as conn:
        with pytest.raises(IntegrityError):
            conn.exec_driver_sql(
                "UPDATE h10_audit_events SET action = 'modified' WHERE id = ?",
                (event_id,),
            )
        conn.rollback()
        with pytest.raises(IntegrityError):
            conn.exec_driver_sql("DELETE FROM h10_audit_events WHERE id = ?", (event_id,))
        conn.rollback()
    result = c.get(url(env))
    assert result.status_code == 200 and result.json()["total"] == 1
    assert result.json()["items"][0]["action"] == "account_created"


def test_atomic_business_rollback_if_audit_rejects_sensitive_metadata(env):
    new_company = new_id()
    with pytest.raises(ValueError):
        with locked(env["engine"]) as conn:
            conn.execute(t.companies.insert().values(id=new_company, name="Will roll back"))
            conn.execute(t.memberships.insert().values(
                user_id=env["owner"], company_id=new_company, role="owner",
            ))
            record_event(
                conn, actor_id=env["owner"], company_id=new_company,
                action="company_created", safe_changes={"password": "forbidden"},
            )
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.companies).where(
            t.companies.c.id == new_company,
        )).scalar_one() == 0
        assert conn.execute(select(func.count()).select_from(a.events).where(
            a.events.c.company_id == new_company,
        )).scalar_one() == 0


def test_event_write_failure_rolls_back_business_record(env):
    target = new_id()
    def fail_audit(conn, cursor, statement, params, context, many):
        if "INSERT INTO h10_audit_events" in statement:
            raise RuntimeError("Simulated audit write failure")
    event.listen(env["engine"], "before_cursor_execute", fail_audit)
    try:
        with pytest.raises(RuntimeError, match="Simulated"):
            with locked(env["engine"]) as conn:
                conn.execute(t.companies.insert().values(id=target, name="Atomic company"))
                conn.execute(t.memberships.insert().values(
                    user_id=env["owner"], company_id=target, role="owner",
                ))
                record_event(conn, actor_id=env["owner"], company_id=target,
                             action="company_created")
    finally:
        event.remove(env["engine"], "before_cursor_execute", fail_audit)
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.companies).where(
            t.companies.c.id == target,
        )).scalar_one() == 0


def test_legacy_h05_snapshot_excludes_null_attribution_upgrade_down_upgrade(tmp_path, monkeypatch):
    db = tmp_path / "audit_migration.db"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", f"sqlite:///{db.as_posix()}")
    config = cfg()
    command.upgrade(config, "h09_0004")
    engine = create_sqlite_engine()
    user_id, company_id = new_id(), new_id()
    with locked(engine) as conn:
        conn.execute(t.companies.insert().values(id=company_id, name="Migration company"))
        conn.execute(t.users.insert().values(
            id=user_id, email="migration-h10@example.test", active=True, password_hash=None,
        ))
        conn.execute(t.memberships.insert().values(
            user_id=user_id, company_id=company_id, role="owner",
        ))
        audit_event(conn, "membership_invitation_created", user_id, company_id)
        audit_event(conn, "login_success", user_id)  # no company: MUST NOT fake one
        audit_event(conn, "login_rejected")  # anonymous: MUST NOT fake actor/company
    try:
        before = set(inspect(engine).get_table_names())
        assert "h10_audit_events" not in before and "h05_audit" in before
        command.upgrade(config, "h10_0005")
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "h10_0005"
            rows = conn.execute(select(a.events)).mappings().all()
            assert len(rows) == 1
            assert rows[0]["company_id"] == company_id and rows[0]["actor_id"] == user_id
            assert rows[0]["action"] == "membership_invitation_created"
            assert rows[0]["safe_changes"] is None
            assert conn.execute(select(func.count()).select_from(t.audit)).scalar_one() == 3
            triggers = {row[0] for row in conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type = 'trigger' AND name LIKE 'h10_%'"
            )}
            assert {"h10_audit_no_update", "h10_audit_no_delete"} <= triggers
        command.downgrade(config, "h09_0004")
        assert "h10_audit_events" not in set(inspect(engine).get_table_names())
        with engine.connect() as conn:
            assert conn.execute(select(func.count()).select_from(t.audit)).scalar_one() == 3
        command.upgrade(config, "h10_0005")
        with engine.connect() as conn:
            assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 1
    finally:
        engine.dispose()


def test_h10_schema_foreign_keys_and_utc_constraints(env):
    with env["engine"].connect() as conn:
        assert {f["referred_table"] for f in inspect(env["engine"]).get_foreign_keys(
            "h10_audit_events"
        )} == {"h05_users", "h05_companies"}
        valid = {
            "id": new_id(), "company_id": env["company"], "actor_id": env["owner"],
            "action": "account_created", "occurred_at": now_string(),
        }
        for overrides in [
            {"actor_id": new_id()},
            {"company_id": new_id()},
            {"occurred_at": "2026-01-01T00:00:00.000000+03:30"},
            {"safe_changes": "invalid-json"},
        ]:
            with pytest.raises(IntegrityError):
                conn.execute(a.events.insert().values(**{**valid, **overrides}))
            conn.rollback()
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 0


def test_unapproved_legacy_and_post_migration_h05_events_not_faked(env):
    login_owner(env)
    with locked(env["engine"]) as conn:
        audit_event(conn, "fiscal_period_closed", env["owner"], env["company"])
        audit_event(conn, "login_success", env["owner"])  # no company ID
        audit_event(conn, "login_rejected")
    result = env["client"].get(url(env))
    assert result.status_code == 200
    # Existing H05 writes AFTER H10 migration do not magically write H10.
    # Cross-module atomic hooks need explicit Manager authorization.
    assert result.json()["items"] == []
    assert result.json()["total"] == 0
