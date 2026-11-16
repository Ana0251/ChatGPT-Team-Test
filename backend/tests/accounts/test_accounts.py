"""H-09 migrated file-backed SQLite + real FastAPI/TestClient API tests."""
from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import event, func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.db.engine import create_sqlite_engine
from app.main import create_app
from app.modules.accounts import tables as a
from app.modules.identity import tables as t
from app.modules.identity.provision import provision_initial_owner
from app.modules.identity.security import digest, password_hash
from app.modules.identity.store import locked, new_id

BASE = "/api/v1"
OWNER_PASSWORD = "ValidOwnerPassword123"
OTHER_PASSWORD = "AnotherValidPassword123"


def alembic_config() -> Config:
    return Config(str(Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"))


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    url = f"sqlite:///{(tmp_path / 'accounts.db').as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    monkeypatch.setenv("HESABYAR_ALLOWED_ORIGIN", "https://testserver")
    key = "h09-operator-secret-key-32characters-123"
    monkeypatch.setenv("HESABYAR_OPERATOR_KEY", key)
    monkeypatch.setenv("HESABYAR_LOGIN_PEPPER", "h09-login-pepper-secret-32characters-123")
    command.upgrade(alembic_config(), "head")
    engine = create_sqlite_engine(url)
    tokens = []

    def deliver(email, token):
        tokens.append((email, token))

    company, owner = provision_initial_owner(
        engine, operator_key=key, company_name="Owner company",
        email="h09owner@example.test", deliver=deliver,
    )
    app = create_app()
    app.state.identity_engine = engine
    app.state.identity_delivery = deliver
    with TestClient(app, base_url="https://testserver") as client:
        yield {
            "client": client, "engine": engine, "company": company, "owner": owner,
            "tokens": tokens,
        }
    engine.dispose()


def csrf(client: TestClient) -> dict[str, str]:
    result = client.get(f"{BASE}/auth/csrf")
    assert result.status_code == 200, result.text
    return {"Origin": "https://testserver", "X-CSRF-Token": result.json()["csrf_token"]}


def login_owner(env):
    client = env["client"]
    activated = client.post(f"{BASE}/auth/activate", headers=csrf(client),
                            json={"token": env["tokens"][0][1], "password": OWNER_PASSWORD})
    assert activated.status_code == 204, activated.text
    logged = client.post(f"{BASE}/auth/login", headers=csrf(client),
                         json={"email": "h09owner@example.test", "password": OWNER_PASSWORD})
    assert logged.status_code == 200, logged.text
    return csrf(client)


def create_member(env, role, email):
    uid = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.users.insert().values(
            id=uid, email=email, password_hash=password_hash(OTHER_PASSWORD), active=True
        ))
        conn.execute(t.memberships.insert().values(
            user_id=uid, company_id=env["company"], role=role
        ))
    return uid


def login_member(env, email):
    client = env["client"]
    resp = client.post(f"{BASE}/auth/login", headers=csrf(client),
                       json={"email": email, "password": OTHER_PASSWORD})
    assert resp.status_code == 200, resp.text
    return csrf(client)


def root(env):
    return f"{BASE}/companies/{env['company']}/accounts"


def account_url(env, aid):
    return f"{root(env)}/{aid}"


def create(env, headers, code, level, parent=None, name=None, active=True):
    return env["client"].post(root(env), headers=headers, json={
        "code": code, "level": level, "name": name or f"Account {code}",
        "parent_id": parent, "active": active,
    })


def chain(env, headers):
    group = create(env, headers, "01", "group")
    assert group.status_code == 201, group.text
    general = create(env, headers, "002", "general", group.json()["id"])
    assert general.status_code == 201, general.text
    subsidiary = create(env, headers, "0003", "subsidiary", general.json()["id"])
    assert subsidiary.status_code == 201, subsidiary.text
    return group.json(), general.json(), subsidiary.json()


def test_unauthenticated_and_empty_list(env):
    c = env["client"]
    assert c.get(root(env)).status_code == 401
    assert c.post(root(env), json={"code": "01", "name": "A", "level": "group"}).status_code == 401
    assert c.get(account_url(env, uuid4())).status_code == 401
    assert c.patch(account_url(env, uuid4()), json={"active": False}).status_code == 401
    assert c.delete(account_url(env, uuid4())).status_code == 401
    login_owner(env)
    result = c.get(root(env))
    assert result.status_code == 200
    assert result.json() == {"items": [], "page": 1, "page_size": 50, "total": 0}


def test_four_level_hierarchy_leading_zeros_and_postability(env):
    c = env["client"]
    headers = login_owner(env)
    group, general, sub = chain(env, headers)
    assert [v["full_code"] for v in (group, general, sub)] == [
        "01", "01.002", "01.002.0003"
    ]
    assert not group["postable"]
    assert not general["postable"]
    assert sub["postable"]
    detail = create(env, headers, "00004", "detail", sub["id"])
    assert detail.status_code == 201, detail.text
    assert detail.json()["full_code"] == "01.002.0003.00004"
    assert detail.json()["postable"]
    assert not c.get(account_url(env, sub["id"])).json()["postable"]
    assert not c.get(account_url(env, group["id"])).json()["postable"]
    listed = c.get(root(env))
    assert listed.status_code == 200
    assert listed.json()["total"] == 4
    assert all(set(item) == {
        "id", "company_id", "parent_id", "code", "name", "level", "active",
        "full_code", "postable"
    } for item in listed.json()["items"])


def test_duplicate_codes_scope_parent_levels_and_invalid_input(env):
    headers = login_owner(env)
    group, general, sub = chain(env, headers)
    assert create(env, headers, "01", "group").status_code == 409
    assert create(env, headers, "002", "general", group["id"]).status_code == 409
    assert create(env, headers, "002", "general").status_code == 422
    assert create(env, headers, "1", "group", group["id"]).status_code == 422
    assert create(env, headers, "1", "detail", group["id"]).status_code == 422
    assert create(env, headers, "1", "subsidiary", sub["id"]).status_code == 422
    assert create(env, headers, "1", "general", sub["id"]).status_code == 422
    assert create(env, headers, "1", "detail", str(uuid4())).status_code == 404
    assert create(env, headers, "", "group").status_code == 422
    assert create(env, headers, "  ", "group").status_code == 422
    assert create(env, headers, "x" * 65, "group").status_code == 422
    assert create(env, headers, "x", "nonsense").status_code == 422
    assert create(env, headers, "0001", "group", name=" ").status_code == 422
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(a.accounts)).scalar_one() == 3


def test_parent_child_distinction_and_unambiguous_full_codes(env):
    headers = login_owner(env)
    first = create(env, headers, "0.1", "group")
    second = create(env, headers, "0\\.1", "group")
    assert first.status_code == second.status_code == 201
    assert first.json()["full_code"] != second.json()["full_code"]
    child = create(env, headers, "000", "general", first.json()["id"])
    assert child.status_code == 201
    same_child_code_other_parent = create(env, headers, "000", "general", second.json()["id"])
    assert same_child_code_other_parent.status_code == 201
    assert child.json()["full_code"] != same_child_code_other_parent.json()["full_code"]


def test_pagination_and_parent_scope(env):
    c = env["client"]
    headers = login_owner(env)
    group, general, sub = chain(env, headers)
    assert create(env, headers, "02", "group").status_code == 201
    page1 = c.get(root(env), params={"page": 1, "page_size": 2}).json()
    page2 = c.get(root(env), params={"page": 2, "page_size": 2}).json()
    assert page1["total"] == page2["total"] == 4
    assert len(page1["items"]) == len(page2["items"]) == 2
    assert not ({x["id"] for x in page1["items"]} & {x["id"] for x in page2["items"]})
    assert c.get(root(env), params={"page_size": 101}).status_code == 422
    assert c.get(root(env), params={"page": 0}).status_code == 422
    filtered = c.get(root(env), params={"parent_id": group["id"]})
    assert filtered.status_code == 200
    assert [x["id"] for x in filtered.json()["items"]] == [general["id"]]
    assert c.get(root(env), params={"parent_id": uuid4()}).status_code == 404
    assert c.get(account_url(env, sub["id"])).status_code == 200


def test_patch_immutable_hierarchy_active_ancestor_and_validations(env):
    c = env["client"]
    headers = login_owner(env)
    group, general, sub = chain(env, headers)
    detail = create(env, headers, "001", "detail", sub["id"]).json()
    response = c.patch(account_url(env, detail["id"]), headers=headers, json={
        "name": "Updated detail", "active": False
    })
    assert response.status_code == 200
    assert response.json()["name"] == "Updated detail"
    assert not response.json()["postable"]
    assert c.patch(account_url(env, detail["id"]), headers=headers, json={"active": True}).status_code == 200
    assert c.patch(account_url(env, group["id"]), headers=headers, json={"active": False}).status_code == 200
    assert not c.get(account_url(env, detail["id"])).json()["postable"]
    assert c.patch(account_url(env, group["id"]), headers=headers, json={"active": True}).status_code == 200
    assert c.get(account_url(env, detail["id"])).json()["postable"]
    for payload in ({}, {"name": ""}, {"name": "  "}, {"active": None}, {"code": "9"},
                    {"level": "detail"}, {"parent_id": None}, {"postable": True}):
        assert c.patch(account_url(env, detail["id"]), headers=headers, json=payload).status_code == 422
    current = c.get(account_url(env, detail["id"])).json()
    assert current["code"] == "001" and current["level"] == "detail"


def test_delete_leaf_only_rollback_and_postable_recalculation(env):
    c = env["client"]
    headers = login_owner(env)
    group, general, sub = chain(env, headers)
    detail = create(env, headers, "D", "detail", sub["id"]).json()
    assert c.delete(account_url(env, sub["id"]), headers=headers).status_code == 409
    assert c.delete(account_url(env, general["id"]), headers=headers).status_code == 409
    assert c.delete(account_url(env, group["id"]), headers=headers).status_code == 409
    assert c.delete(account_url(env, detail["id"]), headers=headers).status_code == 204
    assert c.get(account_url(env, detail["id"])).status_code == 404
    assert c.get(account_url(env, sub["id"])).json()["postable"]
    assert c.delete(account_url(env, sub["id"]), headers=headers).status_code == 204
    assert c.delete(account_url(env, general["id"]), headers=headers).status_code == 204
    assert c.delete(account_url(env, group["id"]), headers=headers).status_code == 204
    assert c.get(root(env)).json()["items"] == []


def test_tenant_isolation_and_unique_code_per_company(env):
    c = env["client"]
    headers = login_owner(env)
    group = create(env, headers, "01", "group").json()
    foreign_company = new_id()
    with locked(env["engine"]) as conn:
        conn.execute(t.companies.insert().values(id=foreign_company, name="Foreign"))
        # Seed a record that is physically in a different tenant without exposing it.
        foreign_id = new_id()
        conn.execute(a.accounts.insert().values(
            id=foreign_id, company_id=foreign_company, parent_id=None,
            code="01", name="Foreign root", level="group", active=True, full_code="01",
        ))
    foreign_url = f"{BASE}/companies/{foreign_company}/accounts"
    assert c.get(foreign_url).status_code == 404
    assert c.post(foreign_url, headers=headers, json={
        "code": "02", "name": "Wrong", "level": "group"
    }).status_code == 404
    for method in ("get", "patch", "delete"):
        url = account_url(env, foreign_id)
        payload = {"name": "Forbidden"} if method == "patch" else None
        res = getattr(c, method)(url, headers=headers, json=payload) if method != "get" else c.get(url)
        assert res.status_code == 404, res.text
    assert c.get(account_url(env, group["id"])).status_code == 200
    assert create(env, headers, "02", "group").status_code == 201
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(a.accounts).where(
            a.accounts.c.company_id == foreign_company
        )).scalar_one() == 1
    with locked(env["engine"]) as conn:
        # Direct DB FK protection: parent from another company must not be accepted.
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(a.accounts.insert().values(
                    id=new_id(), company_id=foreign_company, parent_id=group["id"],
                    code="005", name="Cross FK", level="general", active=True,
                    full_code="01.005",
                ))


def test_viewer_401_403_origin_csrf_revocation_and_expiry(env):
    c = env["client"]
    headers = login_owner(env)
    group = create(env, headers, "01", "group").json()
    for url, action, body in (
        (root(env), "post", {"code": "02", "level": "group", "name": "Other"}),
        (account_url(env, group["id"]), "patch", {"name": "changed"}),
        (account_url(env, group["id"]), "delete", None),
    ):
        for bad_headers in (
            {}, {"Origin": "https://testserver"},
            {**headers, "Origin": "https://evil.example"},
            {"X-CSRF-Token": headers["X-CSRF-Token"]},
        ):
            result = getattr(c, action)(url, headers=bad_headers, json=body)
            assert result.status_code == 403, result.text
    viewer_id = create_member(env, "viewer", "viewer-h09@example.test")
    assert c.post(f"{BASE}/auth/logout", headers=headers).status_code == 204
    viewer = login_member(env, "viewer-h09@example.test")
    assert c.get(root(env)).status_code == 200
    assert c.get(account_url(env, group["id"])).status_code == 200
    assert create(env, viewer, "03", "group").status_code == 403
    assert c.patch(account_url(env, group["id"]), headers=viewer, json={"name": "Changed"}).status_code == 403
    assert c.delete(account_url(env, group["id"]), headers=viewer).status_code == 403
    with locked(env["engine"]) as conn:
        conn.execute(t.memberships.delete().where(
            t.memberships.c.user_id == viewer_id, t.memberships.c.company_id == env["company"]
        ))
    assert c.get(root(env)).status_code == 404
    assert c.get(account_url(env, group["id"])).status_code == 404
    assert create(env, viewer, "03", "group").status_code == 404
    with locked(env["engine"]) as conn:
        conn.execute(t.sessions.update().where(
            t.sessions.c.id_hash == digest(c.cookies.get("hesabyar_session"))
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    assert c.get(root(env)).status_code == 401


def test_account_creation_rollback_and_unique_db_constraint(env):
    c = env["client"]
    headers = login_owner(env)
    original = create(env, headers, "01", "group")
    assert original.status_code == 201
    @event.listens_for(env["engine"], "before_cursor_execute")
    def fail_write(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("INSERT INTO H09_ACCOUNTS"):
            raise RuntimeError("synthetic account write failure")
    try:
        with pytest.raises(RuntimeError, match="synthetic"):
            create(env, headers, "02", "group")
    finally:
        event.remove(env["engine"], "before_cursor_execute", fail_write)
    with env["engine"].connect() as conn:
        assert conn.execute(select(func.count()).select_from(a.accounts)).scalar_one() == 1
    assert create(env, headers, "02", "group").status_code == 201
    with locked(env["engine"]) as conn:
        with pytest.raises(IntegrityError):
            with conn.begin_nested():
                conn.execute(a.accounts.insert().values(
                    id=new_id(), company_id=env["company"], parent_id=None, code="01",
                    name="Duplicate DB", level="group", active=True, full_code="01",
                ))


def test_migration_up_down_up_is_reversible_with_fk(tmp_path, monkeypatch):
    url = f"sqlite:///{(tmp_path / 'migrate_h09.db').as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    config = alembic_config()
    command.upgrade(config, "h07_0003")
    engine = create_sqlite_engine(url)
    try:
        before = set(inspect(engine).get_table_names())
        assert "h09_accounts" not in before and "h05_companies" in before
        command.upgrade(config, "h09_0004")
        assert "h09_accounts" in set(inspect(engine).get_table_names())
        with engine.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert conn.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one() == "h09_0004"
        assert {fk["referred_table"] for fk in inspect(engine).get_foreign_keys("h09_accounts")} == {
            "h05_companies", "h09_accounts"
        }
        command.downgrade(config, "h07_0003")
        assert "h09_accounts" not in set(inspect(engine).get_table_names())
        assert "h07_fiscal_years" in set(inspect(engine).get_table_names())
        command.upgrade(config, "h09_0004")
        assert "h09_accounts" in set(inspect(engine).get_table_names())
    finally:
        engine.dispose()
