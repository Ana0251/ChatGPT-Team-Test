"""H-07 migrated SQLite/TestClient regression tests for year/period integrity."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, select

from app.db.engine import create_sqlite_engine
from app.main import create_app
from app.modules.fiscal import tables as f
from app.modules.identity import tables as t
from app.modules.identity.provision import provision_initial_owner
from app.modules.identity.security import digest, password_hash
from app.modules.identity.store import locked, new_id

BASE = "/api/v1"
PASSWORD = "ValidOwnerPassword123"
MEMBER_PASSWORD = "MemberSecurePass123"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    url = f"sqlite:///{(tmp_path / 'fiscal.db').as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    monkeypatch.setenv("HESABYAR_ALLOWED_ORIGIN", "https://testserver")
    key = "fiscal-only-test-operator-key-123456789"
    monkeypatch.setenv("HESABYAR_OPERATOR_KEY", key)
    monkeypatch.setenv("HESABYAR_LOGIN_PEPPER", "fiscal-only-test-login-pepper-123456789")
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_sqlite_engine(url)
    delivered = []
    def deliver(email, token):
        delivered.append((email, token))
    company, owner = provision_initial_owner(
        engine, operator_key=key, company_name="Fiscal owner",
        email="owner-fiscal@example.test", deliver=deliver,
    )
    app = create_app()
    app.state.identity_engine = engine
    app.state.identity_delivery = deliver
    with TestClient(app, base_url="https://testserver") as client:
        yield {"client": client, "engine": engine, "company": company,
               "owner": owner, "delivered": delivered}
    engine.dispose()


def csrf(client):
    res = client.get(f"{BASE}/auth/csrf")
    assert res.status_code == 200
    return {"Origin": "https://testserver", "X-CSRF-Token": res.json()["csrf_token"]}


def owner_login(env):
    client = env["client"]
    setup = client.post(f"{BASE}/auth/activate", headers=csrf(client),
                        json={"token": env["delivered"][0][1], "password": PASSWORD})
    assert setup.status_code == 204, setup.text
    login = client.post(f"{BASE}/auth/login", headers=csrf(client),
                        json={"email": "owner-fiscal@example.test", "password": PASSWORD})
    assert login.status_code == 200, login.text
    return csrf(client)


def make_member(env, role, email):
    user = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.users.insert().values(
            id=user, email=email, active=True, password_hash=password_hash(MEMBER_PASSWORD),
        ))
        conn.execute(t.memberships.insert().values(
            user_id=user, company_id=env["company"], role=role,
        ))
    return user


def login_as(env, email):
    client = env["client"]
    res = client.post(f"{BASE}/auth/login", headers=csrf(client),
                      json={"email": email, "password": MEMBER_PASSWORD})
    assert res.status_code == 200, res.text
    return csrf(client)


def year_url(env):
    return f"{BASE}/companies/{env['company']}/fiscal-years"


def periods_url(env, year):
    return f"{year_url(env)}/{year}/periods"


def create_year(env, headers, name="FY-2026", start="2026-01-01", end="2027-01-01"):
    return env["client"].post(year_url(env), headers=headers,
                              json={"name": name, "start_date": start, "end_date": end})


def create_period(env, headers, year, name="P1", start="2026-01-01", end="2026-02-01"):
    return env["client"].post(periods_url(env, year), headers=headers,
                              json={"name": name, "start_date": start, "end_date": end})


def close_url(env, year, period):
    return f"{periods_url(env, year)}/{period}/close"


def test_unauthenticated_and_empty_years(env):
    client = env["client"]
    assert client.get(year_url(env)).status_code == 401
    assert client.post(year_url(env), json={
        "name": "Bad", "start_date": "2026-01-01", "end_date": "2027-01-01"
    }).status_code == 401
    headers = owner_login(env)
    assert client.get(year_url(env)).json() == []
    assert client.get(periods_url(env, uuid4())).status_code == 404
    assert client.get(f"{BASE}/companies/{uuid4()}/fiscal-years").status_code == 404


def test_year_adjacency_overlap_and_date_validation(env):
    headers = owner_login(env)
    one = create_year(env, headers)
    assert one.status_code == 201, one.text
    assert set(one.json()) == {"id", "company_id", "name", "start_date", "end_date"}
    assert create_year(env, headers, "FY-2027", "2027-01-01", "2028-01-01").status_code == 201
    conflicting = create_year(env, headers, "Overlap", "2026-12-31", "2027-02-01")
    assert conflicting.status_code == 409
    assert conflicting.json()["error"]["code"] == "PERIOD_OVERLAP"
    for start, end in (("2026-06-01", "2026-06-01"), ("2027-01-01", "2026-01-01"),
                       ("2026-02-30", "2027-01-01")):
        response = create_year(env, headers, "Bad", start, end)
        assert response.status_code == 422, response.text
    assert create_year(env, headers, "", "2030-01-01", "2031-01-01").status_code == 422
    assert create_year(env, headers, "  ", "2030-01-01", "2031-01-01").status_code == 422
    assert len(env["client"].get(year_url(env)).json()) == 2


def test_period_adjacency_overlap_containment_and_close(env):
    client = env["client"]
    headers = owner_login(env)
    year = create_year(env, headers).json()["id"]
    a = create_period(env, headers, year, start="2026-01-01", end="2026-02-01")
    assert a.status_code == 201, a.text
    assert a.json()["status"] == "open"
    b = create_period(env, headers, year, "P2", "2026-02-01", "2027-01-01")
    assert b.status_code == 201, b.text
    assert create_period(env, headers, year, "Overlap", "2026-01-31", "2026-02-03").status_code == 409
    assert create_period(env, headers, year, "Outside", "2025-12-31", "2026-01-05").status_code == 422
    assert create_period(env, headers, year, "Outside", "2026-12-30", "2027-01-02").status_code == 422
    assert create_period(env, headers, year, "Empty", "2026-01-01", "2026-01-01").status_code == 422
    listed = client.get(periods_url(env, year))
    assert listed.status_code == 200 and len(listed.json()) == 2
    closed = client.post(close_url(env, year, a.json()["id"]), headers=headers)
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "closed"
    assert client.post(close_url(env, year, a.json()["id"]), headers=headers).status_code == 409
    with env["engine"].connect() as conn:
        assert conn.execute(select(f.periods.c.status).where(
            f.periods.c.id == a.json()["id"]
        )).scalar_one() == "closed"
        assert conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "fiscal_period_closed"
        )).scalar_one() == 1


def test_no_cross_tenant_or_cross_parent_idor(env):
    client = env["client"]
    headers = owner_login(env)
    first_year = create_year(env, headers).json()["id"]
    first_period = create_period(env, headers, first_year).json()["id"]
    other_company = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.companies.insert().values(id=other_company, name="Foreign"))
    foreign_base = f"{BASE}/companies/{other_company}/fiscal-years"
    assert client.get(foreign_base).status_code == 404
    assert client.post(foreign_base, headers=headers, json={
        "name": "Foreign", "start_date": "2026-01-01", "end_date": "2027-01-01"
    }).status_code == 404
    assert client.get(f"{foreign_base}/{first_year}/periods").status_code == 404
    assert client.get(f"{periods_url(env, uuid4())}").status_code == 404
    assert client.post(close_url(env, uuid4(), first_period), headers=headers).status_code == 404
    assert client.post(close_url(env, first_year, uuid4()), headers=headers).status_code == 404
    second_year = create_year(env, headers, "FY2", "2027-01-01", "2028-01-01").json()["id"]
    assert client.post(close_url(env, second_year, first_period), headers=headers).status_code == 404
    assert client.get(periods_url(env, second_year)).json() == []
    assert client.post(periods_url(env, second_year), headers=headers, json={
        "name": "foreign", "start_date": "2026-01-01", "end_date": "2026-02-01"
    }).status_code == 422


def test_mutation_csrf_origin_expiry_and_roles(env):
    client = env["client"]
    headers = owner_login(env)
    year = create_year(env, headers).json()["id"]
    period = create_period(env, headers, year).json()["id"]
    for url, body in (
        (year_url(env), {"name": "new", "start_date": "2028-01-01", "end_date": "2029-01-01"}),
        (periods_url(env, year), {"name": "new", "start_date": "2026-02-01", "end_date": "2026-03-01"}),
        (close_url(env, year, period), None),
    ):
        for missing in ({}, {"Origin": "https://testserver"},
                        {**headers, "Origin": "https://evil.test"},
                        {"X-CSRF-Token": headers["X-CSRF-Token"]}):
            resp = client.post(url, headers=missing, json=body)
            assert resp.status_code == 403, (url, resp.text)

    make_member(env, "viewer", "viewer-fiscal@example.test")
    make_member(env, "accountant", "accountant-fiscal@example.test")
    make_member(env, "admin", "admin-fiscal@example.test")
    assert client.post(f"{BASE}/auth/logout", headers=headers).status_code == 204
    viewer = login_as(env, "viewer-fiscal@example.test")
    assert client.get(year_url(env)).status_code == 200
    assert client.get(periods_url(env, year)).status_code == 200
    assert create_year(env, viewer, "viewer", "2030-01-01", "2031-01-01").status_code == 403
    assert create_period(env, viewer, year, "viewer", "2026-02-01", "2026-03-01").status_code == 403
    assert client.post(close_url(env, year, period), headers=viewer).status_code == 403
    assert client.post(f"{BASE}/auth/logout", headers=viewer).status_code == 204
    accountant = login_as(env, "accountant-fiscal@example.test")
    assert create_year(env, accountant, "acct", "2030-01-01", "2031-01-01").status_code == 201
    assert create_period(env, accountant, year, "acct", "2026-02-01", "2026-03-01").status_code == 201
    assert client.post(close_url(env, year, period), headers=accountant).status_code == 403
    assert client.post(f"{BASE}/auth/logout", headers=accountant).status_code == 204
    admin = login_as(env, "admin-fiscal@example.test")
    assert client.post(close_url(env, year, period), headers=admin).status_code == 200
    with locked(env["engine"]) as conn:
        conn.execute(t.memberships.delete().where(
            t.memberships.c.company_id == env["company"],
            t.memberships.c.user_id == next(
                row[0] for row in conn.execute(select(t.users.c.id).where(
                    t.users.c.email == "admin-fiscal@example.test"
                ))
            ),
        ))
    assert client.get(year_url(env)).status_code == 404
    assert client.post(close_url(env, year, period), headers=admin).status_code == 404
    with locked(env["engine"]) as conn:
        conn.execute(t.sessions.update().where(
            t.sessions.c.id_hash == digest(client.cookies.get("hesabyar_session"))
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    assert client.get(year_url(env)).status_code == 401


def test_close_rolls_back_on_audit_failure(env):
    headers = owner_login(env)
    year = create_year(env, headers).json()["id"]
    period = create_period(env, headers, year).json()["id"]
    @event.listens_for(env["engine"], "before_cursor_execute")
    def force_failure(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO H05_AUDIT"):
            raise RuntimeError("synthetic audit failure")
    try:
        with pytest.raises(RuntimeError, match="synthetic audit failure"):
            env["client"].post(close_url(env, year, period), headers=headers)
    finally:
        event.remove(env["engine"], "before_cursor_execute", force_failure)
    with env["engine"].connect() as conn:
        assert conn.execute(select(f.periods.c.status).where(
            f.periods.c.id == period
        )).scalar_one() == "open"
        assert conn.execute(select(func.count()).select_from(t.audit).where(
            t.audit.c.action == "fiscal_period_closed"
        )).scalar_one() == 0


def test_migration_is_additive_reversible_and_reappliable(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migrate_h07.db').as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"))
    command.upgrade(config, "h05_0002")
    engine = create_sqlite_engine(url)
    try:
        with engine.connect() as conn:
            names = set(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars())
            assert "h05_companies" in names and "h07_fiscal_years" not in names
        command.upgrade(config, "h07_0003")
        with engine.connect() as conn:
            names = set(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars())
            assert {"h07_fiscal_years", "h07_fiscal_periods"} <= names
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
        command.downgrade(config, "h05_0002")
        with engine.connect() as conn:
            names = set(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars())
            assert "h07_fiscal_periods" not in names and "h07_fiscal_years" not in names
            assert "h05_companies" in names
        command.upgrade(config, "h07_0003")
        with engine.connect() as conn:
            names = set(conn.exec_driver_sql("SELECT name FROM sqlite_master WHERE type='table'").scalars())
            assert {"h07_fiscal_years", "h07_fiscal_periods"} <= names
    finally:
        engine.dispose()
