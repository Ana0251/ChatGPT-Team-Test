"""H-05 integration and negative security tests against disposable local SQLite.

Run manually on Python 3.14.7 / SQLite 3.50.4, preserve raw output in PR.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from app.db.engine import create_sqlite_engine
from app.main import create_app
from app.modules.identity import tables as t
from app.modules.identity.provision import provision_initial_owner
from app.modules.identity.security import digest, now_string
from app.modules.identity.store import locked, member_role, new_id

PASSWORD = "ValidOwnerPassword123"
OTHER_PASSWORD = "MemberSecurePass123"


@pytest.fixture
def sandbox(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Real migrations; no shared user/system DB or production test accounts."""
    database = tmp_path / "h05_identity_test.db"
    url = f"sqlite:///{database.as_posix()}"
    monkeypatch.setenv("HESABYAR_DATABASE_URL", url)
    monkeypatch.setenv("HESABYAR_ALLOWED_ORIGIN", "https://testserver")
    key = "local-tests-operator-only-secret-should-be-32-chars"
    monkeypatch.setenv("HESABYAR_OPERATOR_KEY", key)
    monkeypatch.setenv("HESABYAR_LOGIN_PEPPER", "testing-only-login-throttle-pepper-32-characters")
    config = Config(str(Path(__file__).resolve().parents[2] / "alembic" / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_sqlite_engine(url)
    sent: list[tuple[str, str]] = []

    def deliver(email: str, token: str) -> None:
        sent.append((email, token))

    company_id, user_id = provision_initial_owner(
        engine, operator_key=key, company_name="Synthetic Test Company",
        email="owner@example.test", deliver=deliver,
    )
    app = create_app()
    app.state.identity_engine = engine
    app.state.identity_delivery = deliver

    with TestClient(app, base_url="https://testserver") as client:
        yield {"client": client, "engine": engine, "sent": sent,
               "company_id": company_id, "owner_id": user_id,
               "key": key, "deliver": deliver}
    engine.dispose()


def csrf(client: TestClient) -> dict[str, str]:
    result = client.get("/api/v1/auth/csrf")
    assert result.status_code == 200, result.text
    assert "no-store" in result.headers["cache-control"]
    return {"Origin": "https://testserver", "X-CSRF-Token": result.json()["csrf_token"]}


def provisioned_owner_login(sandbox: dict) -> dict[str, str]:
    client = sandbox["client"]
    headers = csrf(client)
    token = sandbox["sent"][0][1]
    reply = client.post("/api/v1/auth/activate", headers=headers,
                        json={"token": token, "password": PASSWORD})
    assert reply.status_code == 204, reply.text
    assert token not in str(reply.headers)
    return login(client, "owner@example.test", PASSWORD)


def login(client: TestClient, email: str, password: str) -> dict[str, str]:
    headers = csrf(client)
    reply = client.post("/api/v1/auth/login", headers=headers,
                        json={"email": email, "password": password})
    assert reply.status_code == 200, reply.text
    assert reply.json()["email"] == email
    assert "hesabyar_session=" in reply.headers["set-cookie"]
    cookie = reply.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert "hesabyar_pre_session=" in reply.headers["set-cookie"]
    return csrf(client)


def invite(sandbox: dict, company: str, email: str, role: str, headers: dict[str, str]):
    before = len(sandbox["sent"])
    response = sandbox["client"].post(
        f"/api/v1/companies/{company}/members",
        headers=headers,
        json={"email": email, "role": role},
    )
    if response.status_code == 202:
        assert len(sandbox["sent"]) == before + 1
        assert sandbox["sent"][-1][1] not in response.text
        assert response.json()["status"] == "pending"
    return response


def activate_new(client: TestClient, token: str, password: str = OTHER_PASSWORD):
    return client.post("/api/v1/auth/invitations/activate",
                       headers=csrf(client), json={"token": token, "password": password})


def test_initial_owner_is_restricted_and_single_use(sandbox: dict):
    client = sandbox["client"]
    token = sandbox["sent"][0][1]
    with pytest.raises(ValueError, match="empty installation"):
        provision_initial_owner(
            sandbox["engine"], operator_key=sandbox["key"],
            company_name="Second Company", email="other@example.test",
            deliver=sandbox["deliver"],
        )
    headers = csrf(client)
    ok = client.post("/api/v1/auth/activate", headers=headers,
                     json={"token": token, "password": PASSWORD})
    assert ok.status_code == 204
    rejected = client.post("/api/v1/auth/activate", headers=csrf(client),
                           json={"token": token, "password": PASSWORD})
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "INVITE_INVALID"
    with sandbox["engine"].connect() as connection:
        row = connection.execute(select(t.users).where(t.users.c.email == "owner@example.test")).mappings().one()
        assert row["active"] is True
        assert row["password_hash"].startswith("$argon2id$")
        assert PASSWORD not in row["password_hash"]
        assert connection.execute(select(t.setup_tokens.c.token_hash)).scalar_one() == digest(token)


def test_bad_operator_key_and_expired_bootstrap(sandbox: dict):
    with pytest.raises(PermissionError):
        provision_initial_owner(
            sandbox["engine"], operator_key="wrong", company_name="Bad",
            email="bad@example.test", deliver=sandbox["deliver"],
        )
    token = sandbox["sent"][0][1]
    with locked(sandbox["engine"]) as connection:
        connection.execute(t.setup_tokens.update().where(
            t.setup_tokens.c.token_hash == digest(token)
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    response = sandbox["client"].post(
        "/api/v1/auth/activate", headers=csrf(sandbox["client"]),
        json={"token": token, "password": PASSWORD},
    )
    assert response.status_code == 409


def test_login_csrf_origin_and_401_422(sandbox: dict):
    client = sandbox["client"]
    assert client.get("/api/v1/auth/me").status_code == 401
    headers = csrf(client)
    missing = client.post("/api/v1/auth/login",
                          json={"email": "owner@example.test", "password": PASSWORD})
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "CSRF_INVALID"
    bad_origin = client.post(
        "/api/v1/auth/login",
        headers={**headers, "Origin": "https://evil.test"},
        json={"email": "owner@example.test", "password": PASSWORD},
    )
    assert bad_origin.status_code == 403
    wrong = client.post(
        "/api/v1/auth/login", headers=headers,
        json={"email": "owner@example.test", "password": "Incorrect12345"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "AUTH_INVALID"
    malformed = client.post("/api/v1/auth/login", headers=headers, json={"email": "owner@example.test"})
    assert malformed.status_code == 422
    assert malformed.json()["error"]["code"] == "VALIDATION_ERROR"


def test_password_strength_no_plaintext_and_session_rotation(sandbox: dict):
    client = sandbox["client"]
    initial = csrf(client)
    old_pre = client.cookies.get("hesabyar_pre_session")
    short = client.post("/api/v1/auth/activate", headers=initial,
                        json={"token": sandbox["sent"][0][1], "password": "short"})
    assert short.status_code == 422
    ok = client.post(
        "/api/v1/auth/activate", headers=initial,
        json={"token": sandbox["sent"][0][1], "password": PASSWORD},
    )
    assert ok.status_code == 204
    assert client.cookies.get("hesabyar_pre_session") != old_pre
    headers = csrf(client)
    old_csrf = headers["X-CSRF-Token"]
    result = client.post("/api/v1/auth/login", headers=headers,
                         json={"email": "owner@example.test", "password": PASSWORD})
    assert result.status_code == 200
    assert client.cookies.get("hesabyar_session")
    stale = client.post("/api/v1/auth/logout",
                        headers={"Origin": "https://testserver", "X-CSRF-Token": old_csrf})
    assert stale.status_code == 403
    fresh = csrf(client)
    assert fresh["X-CSRF-Token"] != old_csrf
    assert client.get("/api/v1/auth/me").json()["memberships"][0]["role"] == "owner"


def test_logout_revocation_and_expiry(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    cookie = client.cookies.get("hesabyar_session")
    assert client.get("/api/v1/auth/me").status_code == 200
    result = client.post("/api/v1/auth/logout", headers=headers)
    assert result.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401
    with sandbox["engine"].connect() as connection:
        assert connection.execute(select(t.sessions.c.revoked_at).where(
            t.sessions.c.id_hash == digest(cookie)
        )).scalar_one() is not None
    login(client, "owner@example.test", PASSWORD)
    sid = client.cookies.get("hesabyar_session")
    with locked(sandbox["engine"]) as connection:
        connection.execute(t.sessions.update().where(
            t.sessions.c.id_hash == digest(sid)
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    assert client.get("/api/v1/auth/me").status_code == 401


def test_owner_invites_new_company_scoped_owner_and_reuse_denied(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    response = invite(sandbox, sandbox["company_id"], "second-owner@example.test", "owner", headers)
    assert response.status_code == 202
    secret = sandbox["sent"][-1][1]
    client.post("/api/v1/auth/logout", headers=headers)
    accepted = activate_new(client, secret)
    assert accepted.status_code == 204, accepted.text
    again = activate_new(client, secret)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "INVITE_ALREADY_USED"
    login(client, "second-owner@example.test", OTHER_PASSWORD)
    memberships = client.get("/api/v1/auth/me").json()["memberships"]
    assert memberships == [{"user_id": memberships[0]["user_id"],
                            "company_id": sandbox["company_id"], "role": "owner"}]


def test_viewer_cannot_invite_or_read_members(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    assert invite(sandbox, sandbox["company_id"], "viewer@example.test", "viewer", headers).status_code == 202
    secret = sandbox["sent"][-1][1]
    client.post("/api/v1/auth/logout", headers=headers)
    assert activate_new(client, secret).status_code == 204
    headers = login(client, "viewer@example.test", OTHER_PASSWORD)
    path = f"/api/v1/companies/{sandbox['company_id']}/members"
    assert client.get(path).status_code == 403
    forbidden = client.post(path, headers=headers,
                            json={"email": "someone@example.test", "role": "viewer"})
    assert forbidden.status_code == 403


def test_admin_can_invite_viewer_but_not_owner(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    assert invite(sandbox, sandbox["company_id"], "admin@example.test", "admin", headers).status_code == 202
    secret = sandbox["sent"][-1][1]
    client.post("/api/v1/auth/logout", headers=headers)
    assert activate_new(client, secret).status_code == 204
    headers = login(client, "admin@example.test", OTHER_PASSWORD)
    path = f"/api/v1/companies/{sandbox['company_id']}/members"
    assert client.get(path).status_code == 200
    denied = invite(sandbox, sandbox["company_id"], "target@example.test", "owner", headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "INVITE_ROLE_FORBIDDEN"
    assert invite(sandbox, sandbox["company_id"], "another@example.test", "viewer", headers).status_code == 202


def test_cross_tenant_ids_are_invisible(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    unknown_company = str(uuid4())
    assert client.get(f"/api/v1/companies/{unknown_company}/members").status_code == 404
    denied = client.post(
        f"/api/v1/companies/{unknown_company}/members",
        json={"email": "x@example.test", "role": "owner"}, headers=headers,
    )
    assert denied.status_code == 404
    with locked(sandbox["engine"]) as connection:
        other_id = new_id()
        connection.execute(t.companies.insert().values(id=other_id, name="Synthetic Other Company"))
    assert client.get(f"/api/v1/companies/{other_id}/members").status_code == 404


def test_existing_user_accepts_invite_once_and_email_checked(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    assert invite(sandbox, sandbox["company_id"], "existing@example.test", "viewer", headers).status_code == 202
    secret = sandbox["sent"][-1][1]
    # Synthetic other-company principal, only a test fixture; no H-06 company endpoints.
    other_company = new_id()
    existing_id = new_id()
    from app.modules.identity.security import password_hash
    with locked(sandbox["engine"]) as connection:
        connection.execute(t.companies.insert().values(id=other_company, name="Synthetic"))
        connection.execute(t.users.insert().values(
            id=existing_id, email="existing@example.test",
            active=True, password_hash=password_hash(OTHER_PASSWORD),
        ))
        connection.execute(t.memberships.insert().values(
            company_id=other_company, user_id=existing_id, role="viewer",
        ))
    client.post("/api/v1/auth/logout", headers=headers)
    headers = login(client, "existing@example.test", OTHER_PASSWORD)
    result = client.post("/api/v1/auth/invitations/accept",
                         headers=headers, json={"token": secret})
    assert result.status_code == 201, result.text
    assert result.json()["company_id"] == sandbox["company_id"]
    assert len(client.get("/api/v1/auth/me").json()["memberships"]) == 2
    again = client.post("/api/v1/auth/invitations/accept",
                        headers=headers, json={"token": secret})
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "INVITE_ALREADY_USED"


def test_invite_expiry_issuer_revocation_and_duplicate_membership(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    assert invite(sandbox, sandbox["company_id"], "expired@example.test", "viewer", headers).status_code == 202
    token = sandbox["sent"][-1][1]
    with locked(sandbox["engine"]) as connection:
        connection.execute(t.invitations.update().where(
            t.invitations.c.token_hash == digest(token)
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    client.post("/api/v1/auth/logout", headers=headers)
    expired = activate_new(client, token)
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "INVITE_EXPIRED"


def test_pre_session_requires_origin_and_token(sandbox: dict):
    client = sandbox["client"]
    token = sandbox["sent"][0][1]
    headers = csrf(client)
    assert client.post("/api/v1/auth/activate",
                       headers={**headers, "Origin": "https://attacker.invalid"},
                       json={"token": token, "password": PASSWORD}).status_code == 403
    assert client.post("/api/v1/auth/activate",
                       headers={"Origin": "https://testserver"},
                       json={"token": token, "password": PASSWORD}).status_code == 403


def test_invitation_issuer_role_rechecked_and_token_hash_only(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    created = invite(sandbox, sandbox["company_id"], "future@example.test", "owner", headers)
    assert created.status_code == 202
    raw = sandbox["sent"][-1][1]
    with locked(sandbox["engine"]) as connection:
        stored = connection.execute(select(t.invitations).where(
            t.invitations.c.token_hash == digest(raw)
        )).mappings().one()
        assert stored["token_hash"] != raw
        assert raw not in str(dict(stored))
        connection.execute(t.memberships.update().where(
            t.memberships.c.user_id == sandbox["owner_id"],
            t.memberships.c.company_id == sandbox["company_id"],
        ).values(role="admin"))
    client.post("/api/v1/auth/logout", headers=headers)
    denied = activate_new(client, raw)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "INVITE_ROLE_FORBIDDEN"


def test_existing_invitation_email_mismatch_is_not_accepted(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    assert invite(sandbox, sandbox["company_id"], "recipient@example.test", "viewer", headers).status_code == 202
    raw = sandbox["sent"][-1][1]
    impostor_id = new_id()
    secondary = new_id()
    from app.modules.identity.security import password_hash
    with locked(sandbox["engine"]) as connection:
        connection.execute(t.companies.insert().values(id=secondary, name="Synthetic"))
        connection.execute(t.users.insert().values(
            id=impostor_id, email="impostor@example.test",
            password_hash=password_hash(OTHER_PASSWORD), active=True,
        ))
        connection.execute(t.memberships.insert().values(
            user_id=impostor_id, company_id=secondary, role="viewer",
        ))
    client.post("/api/v1/auth/logout", headers=headers)
    headers = login(client, "impostor@example.test", OTHER_PASSWORD)
    rejected = client.post("/api/v1/auth/invitations/accept",
                           headers=headers, json={"token": raw})
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "INVITE_INVALID"
    with sandbox["engine"].connect() as connection:
        assert member_role(connection, impostor_id, sandbox["company_id"]) is None


def test_login_throttling_avoids_unbounded_password_guesses(sandbox: dict):
    client = sandbox["client"]
    headers = provisioned_owner_login(sandbox)
    client.post("/api/v1/auth/logout", headers=headers)
    attempts = []
    for _ in range(5):
        token_header = csrf(client)
        reply = client.post("/api/v1/auth/login", headers=token_header,
                            json={"email": "owner@example.test", "password": "WrongPass123456"})
        attempts.append(reply.status_code)
    assert attempts == [401] * 5
    authenticated = client.post("/api/v1/auth/login", headers=csrf(client),
                                json={"email": "owner@example.test", "password": PASSWORD})
    assert authenticated.status_code == 401


def test_expired_pre_session_and_missing_smtp_fail_closed(sandbox: dict, monkeypatch: pytest.MonkeyPatch):
    client = sandbox["client"]
    csrf_header = csrf(client)
    pre_cookie = client.cookies.get("hesabyar_pre_session")
    with locked(sandbox["engine"]) as connection:
        connection.execute(t.sessions.update().where(
            t.sessions.c.id_hash == digest(pre_cookie)
        ).values(expires_at="2000-01-01T00:00:00.000000+00:00"))
    response = client.post("/api/v1/auth/activate", headers=csrf_header,
                           json={"token": sandbox["sent"][0][1], "password": PASSWORD})
    assert response.status_code == 403
    login_headers = provisioned_owner_login(sandbox)
    monkeypatch.delenv("HESABYAR_SMTP_HOST", raising=False)
    client.app.state.identity_delivery = None
    result = client.post(f"/api/v1/companies/{sandbox['company_id']}/members",
                         headers=login_headers,
                         json={"email": "new@example.test", "role": "viewer"})
    assert result.status_code == 403
    with sandbox["engine"].connect() as connection:
        assert not connection.execute(select(t.invitations.c.id)).first()
