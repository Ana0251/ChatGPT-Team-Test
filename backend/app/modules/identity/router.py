"""H-05 frozen rc.3 identity API (only the approved identity endpoints).

All state is stored in the local H-05 SQLite tables; no public provisioning,
user registration, company creation or system-wide administrator API is exposed.
"""
from __future__ import annotations

import os
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.modules.identity import tables as t
from app.modules.identity.delivery import smtp_delivery_from_env
from app.modules.identity.security import (
    bound_csrf, csrf_hmac_valid, digest, equal_digest, expiry, login_email_key,
    normalize_email, now_string, password_hash, verify_known_or_dummy,
)
from app.modules.identity.store import (
    audit_event, configured_engine, get_session, locked, member_role,
    new_id, new_session, principal, revoke_session,
)

PRE_COOKIE = "hesabyar_pre_session"
AUTH_COOKIE = "hesabyar_session"
COOKIE_ARGS = {"httponly": True, "secure": True, "samesite": "lax", "path": "/api/v1"}


class IdentityError(Exception):
    def __init__(self, status: int, code: str) -> None:
        self.status = status
        self.code = code


def error_response(status: int, code: str, details: list[dict] | None = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": code, "request_id": new_id()}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(body, status_code=status, headers={"Cache-Control": "no-store"})


class IdentityRoute(APIRoute):
    def get_route_handler(self):
        original = super().get_route_handler()

        async def handler(request: Request):
            try:
                return await original(request)
            except IdentityError as exc:
                return error_response(exc.status, exc.code)
            except RequestValidationError as exc:
                fields = []
                for item in exc.errors():
                    loc = item.get("loc", ())
                    field = "/" + "/".join(str(p).replace("~", "~0").replace("/", "~1") for p in loc if p != "body")
                    fields.append({"field": field, "reason": "INVALID"})
                return error_response(422, "VALIDATION_ERROR", fields)
        return handler


router = APIRouter(tags=["Identity"], route_class=IdentityRoute)


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


class ActivateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32)
    password: str = Field(min_length=12)


class AcceptInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32)


class InviteInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    role: Literal["owner", "admin", "accountant", "viewer"]


def engine_for(request: Request):
    current = getattr(request.app.state, "identity_engine", None)
    if current is None:
        current = configured_engine()  # explicit HESABYAR_DATABASE_URL required
        request.app.state.identity_engine = current
    return current


def expected_origin(request: Request) -> str:
    expected = os.environ.get("HESABYAR_ALLOWED_ORIGIN", "").rstrip("/")
    if not expected.startswith("https://"):
        raise IdentityError(403, "ACCESS_DENIED")  # fail closed without trusted HTTPS origin
    if request.url.scheme != "https" or request.headers.get("origin") != expected:
        raise IdentityError(403, "CSRF_INVALID")
    return expected


def session_for(connection, request: Request, authenticated: bool = False):
    auth_sid = request.cookies.get(AUTH_COOKIE)
    auth = get_session(connection, auth_sid, "auth")
    if auth:
        if authenticated and principal(connection, auth["user_id"]) is None:
            raise IdentityError(401, "SESSION_EXPIRED")
        return auth, auth_sid
    if authenticated:
        raise IdentityError(401, "SESSION_EXPIRED")
    pre_sid = request.cookies.get(PRE_COOKIE)
    pre = get_session(connection, pre_sid, "pre")
    return (pre, pre_sid) if pre else (None, None)


def check_mutation(
    connection, request: Request, authenticated: bool = False, pre_only: bool = False
):
    if pre_only:
        # Anonymous activation/login must never run inside an authenticated session.
        if get_session(connection, request.cookies.get(AUTH_COOKIE), "auth"):
            raise IdentityError(403, "CSRF_INVALID")
        sid = request.cookies.get(PRE_COOKIE)
        session = get_session(connection, sid, "pre")
    else:
        session, sid = session_for(connection, request, authenticated)
    expected_origin(request)
    token = request.headers.get("X-CSRF-Token", "")
    if not session or not token or not equal_digest(digest(token), session["csrf_hash"]) or not csrf_hmac_valid(sid, session["expires_at"], token):
        raise IdentityError(403, "CSRF_INVALID")
    return session, sid


def actor_id(connection, request: Request, csrf: bool = False) -> str:
    if csrf:
        session, _ = check_mutation(connection, request, authenticated=True)
    else:
        session, _ = session_for(connection, request, authenticated=True)
    return session["user_id"]


def role_for_company(connection, user_id: str, company_id: str, permitted: tuple[str, ...]) -> str:
    role = member_role(connection, user_id, company_id)
    if role is None:
        raise IdentityError(404, "RESOURCE_NOT_FOUND")
    if role not in permitted:
        raise IdentityError(403, "ACCESS_DENIED")
    return role


def invite_valid(connection, token: str):
    row = connection.execute(select(t.invitations).where(t.invitations.c.token_hash == digest(token))).mappings().first()
    if not row:
        raise IdentityError(409, "INVITE_INVALID")
    if row["consumed_at"]:
        raise IdentityError(409, "INVITE_ALREADY_USED")
    if row["expires_at"] <= now_string():
        raise IdentityError(409, "INVITE_EXPIRED")
    inviter_role = member_role(connection, row["inviter_id"], row["company_id"])
    if inviter_role not in ("owner", "admin") or (row["role"] == "owner" and inviter_role != "owner"):
        raise IdentityError(403, "INVITE_ROLE_FORBIDDEN")
    return row


@router.get("/auth/csrf")
def csrf(request: Request):
    engine = engine_for(request)
    with locked(engine) as connection:
        current, sid = session_for(connection, request)
        if current:
            token = bound_csrf(sid, current["expires_at"])
            connection.execute(t.sessions.update().where(t.sessions.c.id_hash == digest(sid)).values(csrf_hash=digest(token)))
        else:
            sid, token = new_session(connection, "pre")
    result = JSONResponse({"csrf_token": token}, headers={"Cache-Control": "no-store"})
    if not current:
        result.set_cookie(PRE_COOKIE, sid, max_age=900, **COOKIE_ARGS)
    return result


@router.post("/auth/login")
def login(body: LoginInput, request: Request):
    engine = engine_for(request)
    with locked(engine) as connection:
        _, old_sid = check_mutation(connection, request, pre_only=True)
        try:
            email = normalize_email(body.email)
        except ValueError:
            raise IdentityError(401, "AUTH_INVALID") from None
        email_key = login_email_key(email)
        attempts = connection.execute(select(t.login_attempts).where(t.login_attempts.c.email_hash == email_key)).mappings().first()
        if attempts and attempts["locked_until"] and attempts["locked_until"] > now_string():
            raise IdentityError(401, "AUTH_INVALID")
        user = connection.execute(select(t.users).where(t.users.c.email == email)).mappings().first()
        valid = verify_known_or_dummy(user["password_hash"] if user and user["active"] else None, body.password) and bool(user and user["active"])
        if not valid:
            failures = int(attempts["failures"]) + 1 if attempts else 1
            lock_until = expiry(15) if failures >= 5 else None
            if attempts:
                connection.execute(t.login_attempts.update().where(t.login_attempts.c.email_hash == email_key).values(
                    failures=failures, locked_until=lock_until,
                ))
            else:
                connection.execute(t.login_attempts.insert().values(
                    email_hash=email_key, failures=failures, locked_until=lock_until,
                ))
            audit_event(connection, "login_rejected")
            # This exception would roll back the counter; return a sentinel below.
            rejected = True
        else:
            rejected = False
            if attempts:
                connection.execute(t.login_attempts.delete().where(t.login_attempts.c.email_hash == email_key))
            revoke_session(connection, old_sid)
            sid, _ = new_session(connection, "auth", user["id"])
            actor = principal(connection, user["id"])
            audit_event(connection, "login_success", user["id"])
    if rejected:
        raise IdentityError(401, "AUTH_INVALID")
    result = JSONResponse(actor, headers={"Cache-Control": "no-store"})
    result.delete_cookie(PRE_COOKIE, path="/api/v1", secure=True, httponly=True, samesite="lax")
    result.set_cookie(AUTH_COOKIE, sid, max_age=3600, **COOKIE_ARGS)
    return result


@router.post("/auth/activate", status_code=204)
def activate_owner(body: ActivateInput, request: Request):
    engine = engine_for(request)
    with locked(engine) as connection:
        _, old_sid = check_mutation(connection, request, pre_only=True)
        row = connection.execute(select(t.setup_tokens).where(
            t.setup_tokens.c.token_hash == digest(body.token)
        )).mappings().first()
        if not row or row["consumed_at"] or row["expires_at"] <= now_string():
            raise IdentityError(409, "INVITE_INVALID")
        user = connection.execute(select(t.users).where(t.users.c.id == row["user_id"])).mappings().one()
        if user["active"] or member_role(connection, row["user_id"], row["company_id"]) != "owner":
            raise IdentityError(409, "INVITE_INVALID")
        try:
            hashed = password_hash(body.password)
        except ValueError:
            raise IdentityError(422, "VALIDATION_ERROR") from None
        connection.execute(t.users.update().where(t.users.c.id == row["user_id"]).values(
            password_hash=hashed, active=True,
        ))
        connection.execute(t.setup_tokens.update().where(t.setup_tokens.c.token_hash == row["token_hash"]).values(consumed_at=now_string()))
        revoke_session(connection, old_sid)
        sid, _ = new_session(connection, "pre")
        audit_event(connection, "initial_owner_activated", row["user_id"], row["company_id"])
    result = Response(status_code=204, headers={"Cache-Control": "no-store"})
    result.set_cookie(PRE_COOKIE, sid, max_age=900, **COOKIE_ARGS)
    return result


@router.post("/auth/invitations/activate", status_code=204)
def activate_invitation(body: ActivateInput, request: Request):
    engine = engine_for(request)
    with locked(engine) as connection:
        _, old_sid = check_mutation(connection, request, pre_only=True)
        invitation = invite_valid(connection, body.token)
        existing = connection.execute(select(t.users.c.id).where(t.users.c.email == invitation["email"])).first()
        if existing:
            raise IdentityError(409, "INVITE_INVALID")
        try:
            hashed = password_hash(body.password)
        except ValueError:
            raise IdentityError(422, "VALIDATION_ERROR") from None
        user_id = new_id()
        connection.execute(t.users.insert().values(id=user_id, email=invitation["email"], password_hash=hashed, active=True))
        connection.execute(t.memberships.insert().values(user_id=user_id, company_id=invitation["company_id"], role=invitation["role"]))
        connection.execute(t.invitations.update().where(t.invitations.c.id == invitation["id"]).values(consumed_at=now_string()))
        revoke_session(connection, old_sid)
        sid, _ = new_session(connection, "pre")
        audit_event(connection, "invitation_new_user_activated", user_id, invitation["company_id"])
    result = Response(status_code=204, headers={"Cache-Control": "no-store"})
    result.set_cookie(PRE_COOKIE, sid, max_age=900, **COOKIE_ARGS)
    return result


@router.post("/auth/invitations/accept", status_code=201)
def accept_invitation(body: AcceptInput, request: Request):
    engine = engine_for(request)
    with locked(engine) as connection:
        user_id = actor_id(connection, request, csrf=True)
        invitation = invite_valid(connection, body.token)
        user = principal(connection, user_id)
        if user["email"] != invitation["email"]:
            raise IdentityError(409, "INVITE_INVALID")
        if member_role(connection, user_id, invitation["company_id"]):
            raise IdentityError(409, "DUPLICATE_MEMBERSHIP")
        connection.execute(t.memberships.insert().values(user_id=user_id, company_id=invitation["company_id"], role=invitation["role"]))
        connection.execute(t.invitations.update().where(t.invitations.c.id == invitation["id"]).values(consumed_at=now_string()))
        audit_event(connection, "invitation_existing_user_accepted", user_id, invitation["company_id"])
    return JSONResponse({"user_id": user_id, "company_id": invitation["company_id"], "role": invitation["role"]}, status_code=201)


@router.post("/auth/logout", status_code=204)
def logout(request: Request):
    engine = engine_for(request)
    with locked(engine) as connection:
        current, sid = check_mutation(connection, request, authenticated=True)
        revoke_session(connection, sid)
        audit_event(connection, "logout", current["user_id"])
    result = Response(status_code=204, headers={"Cache-Control": "no-store"})
    result.delete_cookie(AUTH_COOKIE, path="/api/v1", secure=True, httponly=True, samesite="lax")
    result.delete_cookie(PRE_COOKIE, path="/api/v1", secure=True, httponly=True, samesite="lax")
    return result


@router.get("/auth/me")
def me(request: Request):
    engine = engine_for(request)
    with engine.connect() as connection:
        user_id = actor_id(connection, request)
        return principal(connection, user_id)


@router.get("/companies/{companyId}/members")
def list_members(companyId: UUID, request: Request):
    engine = engine_for(request)
    with engine.connect() as connection:
        user_id = actor_id(connection, request)
        role_for_company(connection, user_id, str(companyId), ("owner", "admin"))
        result = connection.execute(select(t.memberships).where(t.memberships.c.company_id == str(companyId))).mappings().all()
        return [{"user_id": row["user_id"], "company_id": row["company_id"], "role": row["role"]} for row in result]


@router.post("/companies/{companyId}/members", status_code=202)
def invite_member(companyId: UUID, body: InviteInput, request: Request):
    engine = engine_for(request)
    delivery = getattr(request.app.state, "identity_delivery", None)
    if delivery is None:
        delivery = smtp_delivery_from_env()
    try:
        email = normalize_email(body.email)
    except ValueError:
        raise IdentityError(422, "VALIDATION_ERROR") from None
    with locked(engine) as connection:
        user_id = actor_id(connection, request, csrf=True)
        role = role_for_company(connection, user_id, str(companyId), ("owner", "admin"))
        if not callable(delivery):
            # Fail closed after authorization; never expose transport configuration.
            return error_response(403, "ACCESS_DENIED")
        if body.role == "owner" and role != "owner":
            raise IdentityError(403, "INVITE_ROLE_FORBIDDEN")
        existing = connection.execute(select(t.users.c.id).where(t.users.c.email == email)).scalar_one_or_none()
        if existing and member_role(connection, existing, str(companyId)):
            raise IdentityError(409, "DUPLICATE_MEMBERSHIP")
        pending = connection.execute(select(t.invitations.c.id).where(
            t.invitations.c.company_id == str(companyId),
            t.invitations.c.email == email,
            t.invitations.c.consumed_at.is_(None),
            t.invitations.c.expires_at > now_string(),
        )).first()
        if pending:
            raise IdentityError(409, "INVITE_INVALID")
        raw = new_secret()
        invitation = {
            "id": new_id(), "company_id": str(companyId), "email": email,
            "role": body.role, "status": "pending", "expires_at": expiry(48),
        }
        connection.execute(t.invitations.insert().values(
            id=invitation["id"], token_hash=digest(raw), company_id=str(companyId),
            email=email, role=body.role, inviter_id=user_id,
            expires_at=invitation["expires_at"], consumed_at=None,
        ))
        audit_event(connection, "membership_invitation_created", user_id, str(companyId))
        # Private notifier gets token, API response/DB/audit never do. Failure rolls back.
        delivery(email, raw)
    return JSONResponse(invitation, status_code=202, headers={"Cache-Control": "no-store"})
