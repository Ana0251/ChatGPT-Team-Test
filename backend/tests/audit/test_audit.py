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


def test_unauthenticated_and_owner_bootstrap_events_read_only(env):
    c = env["client"]
    assert c.get(url(env)).status_code == 401
    login_owner(env)
    response = c.get(url(env))
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["total"] == 2
    assert {item["action"] for item in response.json()["items"]} == {
        "operator_initial_owner_provisioned", "initial_owner_activated",
    }
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
    assert data["total"] == 5 and data["page"] == 1 and data["page_size"] == 2
    assert len(data["items"]) == 2
    second = env["client"].get(url(env), params={"page_size": 2, "page": 2})
    assert second.status_code == 200
    assert len(second.json()["items"]) == 2
    third = env["client"].get(url(env), params={"page_size": 2, "page": 3})
    assert third.status_code == 200 and len(third.json()["items"]) == 1
    all_items = data["items"] + second.json()["items"] + third.json()["items"]
    assert set(ids) <= {item["id"] for item in all_items}
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
        if item["id"] in ids:
            assert set(item["safe_changes"]) == {"resource_id", "active", "level"}
    beyond = env["client"].get(url(env), params={"page_size": 2, "page": 4})
    assert beyond.status_code == 200 and beyond.json()["items"] == []
    assert beyond.json()["total"] == 5


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
        assert result.json()["total"] == 3
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
        assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 1


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
        assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 1


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
    assert result.status_code == 200 and result.json()["total"] == 3
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
        assert conn.execute(select(func.count()).select_from(a.events)).scalar_one() == 1


def test_unapproved_legacy_and_post_migration_h05_events_not_faked(env):
    login_owner(env)
    with locked(env["engine"]) as conn:
        audit_event(conn, "fiscal_period_closed", env["owner"], env["company"])
        audit_event(conn, "login_success", env["owner"])  # no company ID
        audit_event(conn, "login_rejected")
    result = env["client"].get(url(env))
    assert result.status_code == 200
    # Direct H05-only writes do not create H10 events without record_event.
    assert result.json()["total"] == 2
    assert {item["action"] for item in result.json()["items"]} == {
        "operator_initial_owner_provisioned", "initial_owner_activated",
    }


def audit_rows(env):
    with env["engine"].connect() as conn:
        return [dict(row) for row in conn.execute(
            select(a.events).order_by(a.events.c.occurred_at, a.events.c.id)
        ).mappings()]


def login_known(env, email, password):
    c = env["client"]
    logged = c.post(f"{BASE}/auth/login", headers=csrf(c), json={
        "email": email, "password": password,
    })
    assert logged.status_code == 200, logged.text
    return csrf(c)


def logout_known(env, headers):
    result = env["client"].post(f"{BASE}/auth/logout", headers=headers)
    assert result.status_code == 204, result.text


def new_action(env, action, request):
    """Assert one matching H-10 event for one successful real endpoint."""
    old = {row["id"] for row in audit_rows(env)}
    response = request()
    assert 200 <= response.status_code < 300, response.text
    added = [row for row in audit_rows(env) if row["id"] not in old]
    assert len(added) == 1, [r["action"] for r in added]
    assert added[0]["action"] == action
    assert str(UUID(added[0]["actor_id"])) == added[0]["actor_id"]
    assert str(UUID(added[0]["company_id"])) == added[0]["company_id"]
    assert datetime.fromisoformat(added[0]["occurred_at"]).utcoffset() == timedelta(0)
    return response, added[0]


def test_all_twelve_real_atomic_hooks_and_redacted_safe_metadata(env):
    """Exercise every approved mutation entrypoint (two invites, one per other)."""
    from collections import Counter
    from app.modules.identity.security import password_hash

    c = env["client"]
    assert Counter(r["action"] for r in audit_rows(env)) == {
        "operator_initial_owner_provisioned": 1,
    }
    headers = login_owner(env)
    assert Counter(r["action"] for r in audit_rows(env)) == {
        "operator_initial_owner_provisioned": 1,
        "initial_owner_activated": 1,
    }

    invite_url = f"{BASE}/companies/{env['company']}/members"
    secret_email = "secret-personal-invite-h10@example.test"
    invitation, invitation_event = new_action(
        env, "membership_invitation_created",
        lambda: c.post(invite_url, headers=headers, json={
            "email": secret_email, "role": "viewer",
        }),
    )
    assert invitation_event["actor_id"] == env["owner"]
    assert invitation_event["company_id"] == env["company"]
    assert invitation_event["safe_changes"] is not None
    first_token = env["tokens"][-1]
    logout_known(env, headers)

    activated, activated_event = new_action(
        env, "invitation_new_user_activated",
        lambda: c.post(f"{BASE}/auth/invitations/activate", headers=csrf(c), json={
            "token": first_token, "password": MEMBER_PASSWORD,
        }),
    )
    assert activated.status_code == 204
    with env["engine"].connect() as conn:
        activated_id = conn.execute(select(t.users.c.id).where(
            t.users.c.email == secret_email,
        )).scalar_one()
    assert activated_event["actor_id"] == activated_id

    headers = login_known(env, "h10owner@example.test", PASSWORD)
    existing_email = "existing-personal-h10@example.test"
    with locked(env["engine"]) as conn:
        existing_id = new_id()
        conn.execute(t.users.insert().values(
            id=existing_id, email=existing_email,
            password_hash=password_hash(MEMBER_PASSWORD), active=True,
        ))
    _, event_invitation = new_action(
        env, "membership_invitation_created",
        lambda: c.post(invite_url, headers=headers, json={
            "email": existing_email, "role": "accountant",
        }),
    )
    assert event_invitation["actor_id"] == env["owner"]
    second_token = env["tokens"][-1]
    logout_known(env, headers)
    existing_headers = login_known(env, existing_email, MEMBER_PASSWORD)
    accepted, accepted_event = new_action(
        env, "invitation_existing_user_accepted",
        lambda: c.post(f"{BASE}/auth/invitations/accept",
                       headers=existing_headers, json={"token": second_token}),
    )
    assert accepted.status_code == 201
    assert accepted_event["actor_id"] == existing_id
    logout_known(env, existing_headers)
    headers = login_known(env, "h10owner@example.test", PASSWORD)

    company_name = "SENSITIVE_COMPANY_NAME_DO_NOT_LOG"
    new_company, company_event = new_action(
        env, "company_created",
        lambda: c.post(f"{BASE}/companies", headers=headers,
                       json={"name": company_name}),
    )
    assert company_event["company_id"] == new_company.json()["id"]
    assert company_event["actor_id"] == env["owner"]

    years = f"{BASE}/companies/{env['company']}/fiscal-years"
    year, year_event = new_action(
        env, "fiscal_year_created",
        lambda: c.post(years, headers=headers, json={
            "name": "SENSITIVE_FISCAL_YEAR_NAME",
            "start_date": "2026-01-01", "end_date": "2027-01-01",
        }),
    )
    periods = f"{years}/{year.json()['id']}/periods"
    period, period_event = new_action(
        env, "fiscal_period_created",
        lambda: c.post(periods, headers=headers, json={
            "name": "SENSITIVE_PERIOD_NAME",
            "start_date": "2026-01-01", "end_date": "2026-02-01",
        }),
    )
    closed, closed_event = new_action(
        env, "fiscal_period_closed",
        lambda: c.post(f"{periods}/{period.json()['id']}/close", headers=headers),
    )
    assert closed_event["safe_changes"] is not None

    accounts = f"{BASE}/companies/{env['company']}/accounts"
    account, created_event = new_action(
        env, "account_created",
        lambda: c.post(accounts, headers=headers, json={
            "code": "001", "name": "SENSITIVE_ACCOUNT_NAME",
            "level": "group", "active": True,
        }),
    )
    account_id = account.json()["id"]
    _, updated_event = new_action(
        env, "account_updated",
        lambda: c.patch(f"{accounts}/{account_id}", headers=headers,
                        json={"name": "SENSITIVE_CHANGED_ACCOUNT_NAME"}),
    )
    removed, deleted_event = new_action(
        env, "account_deleted",
        lambda: c.delete(f"{accounts}/{account_id}", headers=headers),
    )
    assert removed.status_code == 204
    for item in (year_event, period_event, closed_event,
                 created_event, updated_event, deleted_event):
        assert item["actor_id"] == env["owner"]
        assert item["company_id"] == env["company"]

    events = audit_rows(env)
    assert Counter(row["action"] for row in events) == {
        "operator_initial_owner_provisioned": 1,
        "initial_owner_activated": 1,
        "membership_invitation_created": 2,
        "invitation_new_user_activated": 1,
        "invitation_existing_user_accepted": 1,
        "company_created": 1,
        "fiscal_year_created": 1,
        "fiscal_period_created": 1,
        "fiscal_period_closed": 1,
        "account_created": 1,
        "account_updated": 1,
        "account_deleted": 1,
    }
    assert len(events) == 13
    for row in events:
        assert str(UUID(row["actor_id"])) == row["actor_id"]
        assert str(UUID(row["company_id"])) == row["company_id"]
        assert datetime.fromisoformat(row["occurred_at"]).utcoffset() == timedelta(0)
        raw = str(row["safe_changes"])
        for secret in (
            secret_email, existing_email, first_token, second_token,
            PASSWORD, MEMBER_PASSWORD, company_name,
            "SENSITIVE_ACCOUNT_NAME", "SENSITIVE_CHANGED_ACCOUNT_NAME",
            "SENSITIVE_FISCAL_YEAR_NAME", "SENSITIVE_PERIOD_NAME",
        ):
            assert secret not in raw

    # Legacy H05 issuance quota still counts exactly two successful invites;
    # it must not count or depend on any of the new H10 records.
    with env["engine"].connect() as conn:
        legacy = conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "membership_invitation_created",
            t.audit.c.actor_id == env["owner"],
            t.audit.c.company_id == env["company"],
        )).scalar_one()
    assert legacy == 2


def test_rejected_real_mutations_never_create_new_h10_event(env):
    c = env["client"]
    headers = login_owner(env)
    accounts = f"{BASE}/companies/{env['company']}/accounts"
    before = {r["id"] for r in audit_rows(env)}
    missing_csrf = c.post(accounts, json={"code": "A", "name": "A", "level": "group"})
    assert missing_csrf.status_code == 403
    invalid = c.post(accounts, headers=headers, json={
        "code": "A", "name": "A", "level": "detail",
    })
    assert invalid.status_code == 422
    assert {r["id"] for r in audit_rows(env)} == before

    created, _ = new_action(env, "account_created", lambda: c.post(
        accounts, headers=headers, json={"code": "001", "name": "Ledger",
                                         "level": "group"},
    ))
    before = {r["id"] for r in audit_rows(env)}
    duplicate = c.post(accounts, headers=headers, json={
        "code": "001", "name": "Duplicate", "level": "group",
    })
    assert duplicate.status_code == 409
    years = f"{BASE}/companies/{env['company']}/fiscal-years"
    bad_year = c.post(years, headers=headers, json={
        "name": "Invalid", "start_date": "2027-01-01", "end_date": "2026-01-01",
    })
    assert bad_year.status_code == 422
    assert {r["id"] for r in audit_rows(env)} == before
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "membership_invitation_created",
        )).scalar_one() == 0


@pytest.mark.parametrize("operation", ["company_create", "account_create", "invitation_issue"])
def test_actual_http_mutation_rolls_back_when_h10_insert_fails(env, operation):
    c = env["client"]
    headers = login_owner(env)
    company_count_before = None
    with env["engine"].connect() as conn:
        company_count_before = conn.execute(select(func.count()).select_from(
            t.companies
        )).scalar_one()
        account_count_before = conn.execute(
            text("SELECT count(*) FROM h09_accounts")
        ).scalar_one()
        invitation_count_before = conn.execute(select(func.count()).select_from(
            t.invitations
        )).scalar_one()
        old_h05_invites = conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "membership_invitation_created",
        )).scalar_one()
    before = {r["id"] for r in audit_rows(env)}

    def fail_h10_insert(conn, cursor, statement, parameters, context, many):
        if "INSERT INTO h10_audit_events" in statement:
            raise RuntimeError("Forced H10 audit failure")

    event.listen(env["engine"], "before_cursor_execute", fail_h10_insert)
    try:
        with pytest.raises(RuntimeError, match="Forced H10 audit failure"):
            if operation == "company_create":
                c.post(f"{BASE}/companies", headers=headers, json={
                    "name": "ROLLBACK_COMPANY",
                })
            elif operation == "account_create":
                c.post(f"{BASE}/companies/{env['company']}/accounts",
                       headers=headers, json={
                           "code": "ROLLBACK_CODE", "name": "ROLLBACK_ACCOUNT",
                           "level": "group",
                       })
            else:
                c.post(f"{BASE}/companies/{env['company']}/members",
                       headers=headers, json={
                           "email": "rollback-invitation@example.test",
                           "role": "viewer",
                       })
    finally:
        event.remove(env["engine"], "before_cursor_execute", fail_h10_insert)

    assert {r["id"] for r in audit_rows(env)} == before
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(
            t.companies
        )).scalar_one() == company_count_before
        assert conn.execute(text("SELECT count(*) FROM h09_accounts")).scalar_one() == account_count_before
        assert conn.execute(select(func.count()).select_from(
            t.invitations
        )).scalar_one() == invitation_count_before
        assert conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "membership_invitation_created",
        )).scalar_one() == old_h05_invites


def test_real_fiscal_close_rolls_back_both_audit_tables(env):
    c = env["client"]
    headers = login_owner(env)
    years = f"{BASE}/companies/{env['company']}/fiscal-years"
    yr = c.post(years, headers=headers, json={
        "name": "FY", "start_date": "2026-01-01", "end_date": "2027-01-01",
    })
    assert yr.status_code == 201, yr.text
    periods = f"{years}/{yr.json()['id']}/periods"
    per = c.post(periods, headers=headers, json={
        "name": "P", "start_date": "2026-01-01", "end_date": "2026-02-01",
    })
    assert per.status_code == 201, per.text
    before = {r["id"] for r in audit_rows(env)}
    with env["engine"].connect() as conn:
        old_h05_closes = conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "fiscal_period_closed",
        )).scalar_one()

    def fail_h10_close(conn, cursor, statement, params, context, many):
        if "INSERT INTO h10_audit_events" in statement:
            raise RuntimeError("Forced fiscal close audit failure")
    event.listen(env["engine"], "before_cursor_execute", fail_h10_close)
    try:
        with pytest.raises(RuntimeError, match="Forced fiscal close audit failure"):
            c.post(f"{periods}/{per.json()['id']}/close", headers=headers)
    finally:
        event.remove(env["engine"], "before_cursor_execute", fail_h10_close)
    assert {r["id"] for r in audit_rows(env)} == before
    with env["engine"].connect() as conn:
        assert conn.execute(text(
            "SELECT status FROM h07_fiscal_periods WHERE id=:id"
        ), {"id": per.json()["id"]}).scalar_one() == "open"
        assert conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "fiscal_period_closed",
        )).scalar_one() == old_h05_closes


def test_real_owner_activation_rolls_back_on_audit_write_failure(env):
    c = env["client"]
    before = {r["id"] for r in audit_rows(env)}
    h = csrf(c)

    def fail_h10_activation(conn, cursor, statement, params, context, many):
        if "INSERT INTO h10_audit_events" in statement:
            raise RuntimeError("Forced activation audit failure")
    event.listen(env["engine"], "before_cursor_execute", fail_h10_activation)
    try:
        with pytest.raises(RuntimeError, match="Forced activation audit failure"):
            c.post(f"{BASE}/auth/activate", headers=h, json={
                "token": env["tokens"][0], "password": PASSWORD,
            })
    finally:
        event.remove(env["engine"], "before_cursor_execute", fail_h10_activation)
    assert {r["id"] for r in audit_rows(env)} == before
    with env["engine"].connect() as conn:
        assert conn.execute(select(t.users.c.active).where(
            t.users.c.id == env["owner"],
        )).scalar_one() is False
        assert conn.execute(select(t.setup_tokens.c.consumed_at).where(
            t.setup_tokens.c.user_id == env["owner"],
        )).scalar_one() is None
    again = c.post(f"{BASE}/auth/activate", headers=h, json={
        "token": env["tokens"][0], "password": PASSWORD,
    })
    assert again.status_code == 204, again.text
    assert [r["action"] for r in audit_rows(env)].count("initial_owner_activated") == 1


def test_h10_read_contract_is_exact_openapi_rc4_schema(env):
    """Validate against the committed normative contract, not an invented DTO."""
    import yaml

    contract_path = Path(__file__).resolve().parents[3] / "docs" / "contracts" / "openapi.yaml"
    schema = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    assert schema["info"]["version"] == "1.0.0-rc.4"
    endpoint = schema["paths"]["/companies/{companyId}/audit-events"]
    assert set(endpoint) == {"get"}
    assert endpoint["get"]["tags"] == ["Audit"]
    assert endpoint["get"]["responses"]["200"]["content"]["application/json"]["schema"]["required"] == [
        "items", "page", "page_size", "total",
    ]
    event = schema["components"]["schemas"]["AuditEvent"]
    assert set(event["required"]) == {
        "id", "company_id", "actor_id", "action", "occurred_at",
    }
    assert event["properties"]["safe_changes"]["type"] == "object"

    c = env["client"]
    login_owner(env)
    response = c.get(url(env))
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"items", "page", "page_size", "total"}
    for item in body["items"]:
        assert set(event["required"]) <= set(item)
        assert str(UUID(item["id"])) == item["id"]
        assert str(UUID(item["company_id"])) == item["company_id"]
        assert str(UUID(item["actor_id"])) == item["actor_id"]
        assert datetime.fromisoformat(item["occurred_at"]).utcoffset() == timedelta(0)
