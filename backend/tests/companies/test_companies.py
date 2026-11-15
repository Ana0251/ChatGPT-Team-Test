"""H-06 real FastAPI + disposable migrated SQLite company API regression tests."""
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
from app.modules.identity import tables as t
from app.modules.identity.provision import provision_initial_owner
from app.modules.identity.security import digest, password_hash
from app.modules.identity.store import locked, new_id

PASSWORD = "ValidOwnerPassword123"
OTHER_PASSWORD = "MemberSecurePass123"
BASE = "/api/v1"


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Each test has a completely independent, migrated on-disk database."""
    url = f"sqlite:///{(tmp_path / 'h06.db').as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    monkeypatch.setenv("HESABYAR_ALLOWED_ORIGIN", "https://testserver")
    monkeypatch.setenv("HESABYAR_OPERATOR_KEY", "h06-local-test-operator-key-only-32characters")
    monkeypatch.setenv("HESABYAR_LOGIN_PEPPER", "h06-local-test-login-pepper-only-32chars")
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_sqlite_engine(url)
    delivered = []
    def deliver(email, token):
        delivered.append((email, token))
    company, owner = provision_initial_owner(
        engine,
        operator_key="h06-local-test-operator-key-only-32characters",
        company_name="Existing Company",
        email="owner-h06@example.test",
        deliver=deliver,
    )
    app = create_app()
    app.state.identity_engine = engine
    app.state.identity_delivery = deliver
    with TestClient(app, base_url="https://testserver") as client:
        yield {"client": client, "engine": engine, "company": company, "owner": owner,
               "delivered": delivered}
    engine.dispose()


def csrf(client):
    response = client.get(f"{BASE}/auth/csrf")
    assert response.status_code == 200, response.text
    return {"Origin": "https://testserver", "X-CSRF-Token": response.json()["csrf_token"]}


def owner_login(env):
    client = env["client"]
    activated = client.post(f"{BASE}/auth/activate", headers=csrf(client),
                            json={"token": env["delivered"][0][1], "password": PASSWORD})
    assert activated.status_code == 204, activated.text
    logged = client.post(f"{BASE}/auth/login", headers=csrf(client),
                         json={"email": "owner-h06@example.test", "password": PASSWORD})
    assert logged.status_code == 200, logged.text
    return csrf(client)


def create_member(env, email="viewer-h06@example.test", role="viewer"):
    user_id = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.users.insert().values(
            id=user_id, email=email, password_hash=password_hash(OTHER_PASSWORD), active=True,
        ))
        conn.execute(t.memberships.insert().values(
            user_id=user_id, company_id=env["company"], role=role,
        ))
    return user_id


def login_as(client, email, password=OTHER_PASSWORD):
    response = client.post(f"{BASE}/auth/login", headers=csrf(client),
                           json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return csrf(client)


def test_company_routes_unauthenticated_and_empty_list(env):
    client = env["client"]
    assert client.get(f"{BASE}/companies").status_code == 401
    assert client.get(f"{BASE}/companies/{env['company']}").status_code == 401
    assert client.post(f"{BASE}/companies", json={"name": "Blocked"}).status_code == 401
    headers = owner_login(env)
    with locked(env["engine"]) as conn:
        conn.execute(t.memberships.delete().where(t.memberships.c.user_id == env["owner"]))
    response = client.get(f"{BASE}/companies")
    assert response.status_code == 200 and response.json() == []
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.companies)).scalar_one() == 1
    assert client.get(f"{BASE}/companies/{env['company']}").status_code == 404


def test_member_only_list_and_owner_atomic_creation(env):
    client = env["client"]
    headers = owner_login(env)
    visible = client.get(f"{BASE}/companies")
    assert visible.status_code == 200
    assert visible.json() == [{"id": env["company"], "name": "Existing Company"}]
    created = client.post(f"{BASE}/companies", headers=headers, json={"name": "Second Company"})
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Second Company"
    new_id_ = created.json()["id"]
    assert new_id_ != env["company"]
    assert str(uuid4()) != new_id_
    with env["engine"].connect() as conn:
        assert conn.execute(select(t.memberships.c.role).where(
            t.memberships.c.user_id == env["owner"],
            t.memberships.c.company_id == new_id_,
        )).scalar_one() == "owner"
        assert conn.execute(select(func.count()).select_from(t.memberships).where(
            t.memberships.c.company_id == new_id_
        )).scalar_one() == 1
    response = client.get(f"{BASE}/companies")
    assert response.status_code == 200
    assert {row["id"] for row in response.json()} == {env["company"], new_id_}
    assert client.get(f"{BASE}/companies/{new_id_}").json() == created.json()


def test_company_create_only_authenticated_user_even_with_untrusted_payload(env):
    client = env["client"]
    headers = owner_login(env)
    # No client-supplied role/user/company authority fields are accepted.
    attempt = client.post(f"{BASE}/companies", headers=headers, json={
        "name": "No impersonation", "owner_id": str(uuid4()), "role": "admin",
    })
    assert attempt.status_code == 422
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.companies)).scalar_one() == 1
    created = client.post(f"{BASE}/companies", headers=headers, json={"name": "Trusted principal"})
    assert created.status_code == 201
    with env["engine"].connect() as conn:
        owner = conn.execute(select(t.memberships.c.user_id).where(
            t.memberships.c.company_id == created.json()["id"]
        )).scalar_one()
        assert owner == env["owner"]


@pytest.mark.parametrize("name", ["", " ", "\t\n", "x" * 201])
def test_company_name_validation_422(env, name):
    headers = owner_login(env)
    response = env["client"].post(f"{BASE}/companies", headers=headers, json={"name": name})
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.companies)).scalar_one() == 1


def test_company_name_max_length_boundary(env):
    headers = owner_login(env)
    client = env["client"]
    created = client.post(f"{BASE}/companies", headers=headers, json={"name": "A" * 200})
    assert created.status_code == 201
    assert created.json()["name"] == "A" * 200


def test_company_create_csrf_origin_and_expired_session(env):
    client = env["client"]
    headers = owner_login(env)
    for bad in (
        {},
        {"Origin": "https://testserver"},
        {**headers, "Origin": "https://attacker.example"},
        {"X-CSRF-Token": headers["X-CSRF-Token"]},
        {**headers, "X-CSRF-Token": "bad"},
    ):
        result = client.post(f"{BASE}/companies", headers=bad, json={"name": "Denied"})
        assert result.status_code == 403, result.text
    with locked(env["engine"]) as conn:
        conn.execute(t.sessions.update().where(
            t.sessions.c.id_hash == digest(client.cookies.get("hesabyar_session"))
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    assert client.get(f"{BASE}/companies").status_code == 401
    assert client.post(f"{BASE}/companies", headers=headers, json={"name": "Expired"}).status_code == 401
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(t.companies)).scalar_one() == 1


def test_nonmember_and_missing_company_have_indistinguishable_404(env):
    client = env["client"]
    headers = owner_login(env)
    owned_by_other = new_id()
    user = create_member(env)
    with locked(env["engine"]) as conn:
        conn.execute(t.companies.insert().values(id=owned_by_other, name="Hidden Company"))
        conn.execute(t.memberships.insert().values(
            user_id=user, company_id=owned_by_other, role="owner"
        ))
    missing_id = str(uuid4())
    hidden = client.get(f"{BASE}/companies/{owned_by_other}")
    missing = client.get(f"{BASE}/companies/{missing_id}")
    assert hidden.status_code == missing.status_code == 404
    assert hidden.json()["error"]["code"] == missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert hidden.json()["error"]["message"] == missing.json()["error"]["message"]
    assert set(hidden.json()) == set(missing.json()) == {"error"}
    assert client.get(f"{BASE}/companies/{env['company']}").status_code == 200
    assert {row["id"] for row in client.get(f"{BASE}/companies").json()} == {env["company"]}
    # On membership revocation, previously visible company becomes invisible.
    with locked(env["engine"]) as conn:
        conn.execute(t.memberships.delete().where(
            t.memberships.c.user_id == env["owner"],
            t.memberships.c.company_id == env["company"],
        ))
    assert client.get(f"{BASE}/companies").json() == []
    assert client.get(f"{BASE}/companies/{env['company']}").status_code == 404
    # Other user can see their company but cannot see any unrelated tenants.
    assert client.post(f"{BASE}/auth/logout", headers=headers).status_code == 204
    login_as(client, "viewer-h06@example.test")
    listed = client.get(f"{BASE}/companies")
    assert {row["id"] for row in listed.json()} == {env["company"], owned_by_other}


def test_company_creation_rolls_back_if_owner_membership_insert_fails(env):
    client = env["client"]
    headers = owner_login(env)
    before = []
    with env["engine"].connect() as conn:
        before = conn.execute(select(t.companies.c.id)).all()
    # Fail precisely after successful company INSERT, before owner membership INSERT.
    @event.listens_for(env["engine"], "before_cursor_execute")
    def deny_member_insert(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO H05_MEMBERSHIPS"):
            raise RuntimeError("synthetic owner-membership insertion failure")
    try:
        with pytest.raises(RuntimeError, match="synthetic owner-membership"):
            client.post(f"{BASE}/companies", headers=headers, json={"name": "Must rollback"})
    finally:
        event.remove(env["engine"], "before_cursor_execute", deny_member_insert)
    with env["engine"].connect() as conn:
        assert conn.execute(select(t.companies.c.id)).all() == before
        assert conn.execute(select(func.count()).select_from(t.memberships)).scalar_one() == 1


def test_unaccepted_member_cannot_select_other_company(env):
    client = env["client"]
    headers = owner_login(env)
    create_member(env)
    response = client.post(f"{BASE}/companies", headers=headers, json={"name": "New Owner Company"})
    assert response.status_code == 201
    fresh_id = response.json()["id"]
    assert client.post(f"{BASE}/auth/logout", headers=headers).status_code == 204
    login_as(client, "viewer-h06@example.test")
    assert fresh_id not in {company["id"] for company in client.get(f"{BASE}/companies").json()}
    assert client.get(f"{BASE}/companies/{fresh_id}").status_code == 404
