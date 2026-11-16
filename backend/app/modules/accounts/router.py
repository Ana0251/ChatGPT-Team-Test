"""H-09 tenant-scoped chart-of-accounts API (OpenAPI 1.0.0-rc.4).

Only the four approved hierarchy levels exist: group -> general -> subsidiary
-> detail. No accounting journal or Posting endpoints are implemented here.
All writes revalidate H-05 session, company membership, role, CSRF and Origin
inside a SQLite BEGIN IMMEDIATE transaction.
"""
from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.modules.accounts import tables as t
from app.modules.identity.router import (
    IdentityError, IdentityRoute, actor_id, engine_for, role_for_company,
)
from app.modules.identity.store import locked, new_id

router = APIRouter(tags=["Accounts"], route_class=IdentityRoute)

LEVELS = ("group", "general", "subsidiary", "detail")
READERS = ("owner", "admin", "accountant", "viewer")
WRITERS = ("owner", "admin", "accountant")


class AccountInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parent_id: UUID | None = None
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    level: str
    active: bool = True

    @field_validator("level")
    @classmethod
    def valid_level(cls, value: str) -> str:
        if value not in LEVELS:
            raise ValueError("Account level is not one of the four approved levels")
        return value

    @model_validator(mode="after")
    def nonblank(self):
        if not self.code.strip() or not self.name.strip():
            raise ValueError("Account code and name cannot be blank")
        return self


class AccountPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    active: bool | None = None

    @model_validator(mode="after")
    def valid_update(self):
        if not self.model_fields_set or any(
            getattr(self, key) is None for key in self.model_fields_set
        ):
            raise ValueError("Patch requires non-null name or active")
        if self.name is not None and not self.name.strip():
            raise ValueError("Account name cannot be blank")
        return self


def require_member(conn, request: Request, company: str, *,
                   write: bool = False) -> str:
    user_id = actor_id(conn, request, csrf=write)
    role_for_company(conn, user_id, company, WRITERS if write else READERS)
    return user_id


def scoped_account(conn, company: str, account_id: str) -> Mapping:
    row = conn.execute(select(t.accounts).where(
        t.accounts.c.company_id == company,
        t.accounts.c.id == account_id,
    )).mappings().first()
    if row is None:
        raise IdentityError(404, "RESOURCE_NOT_FOUND")
    return row


def all_company_accounts(conn, company: str) -> dict[str, dict]:
    return {row["id"]: dict(row) for row in conn.execute(
        select(t.accounts).where(t.accounts.c.company_id == company)
    ).mappings()}


def escape_segment(code: str) -> str:
    """Keep leading zeros; escape dot and backslash for unambiguous full codes."""
    return code.replace("\\", "\\\\").replace(".", "\\.")


def serializable_account(row: Mapping, rows: Mapping[str, dict]) -> dict:
    children = {item["parent_id"] for item in rows.values() if item["parent_id"]}
    # Postability is computed, not stored or trusted from client input.
    active_lineage = bool(row["active"])
    parent_id = row["parent_id"]
    seen: set[str] = {row["id"]}
    while active_lineage and parent_id is not None:
        if parent_id in seen or parent_id not in rows:
            active_lineage = False  # fail closed on broken lineage
            break
        seen.add(parent_id)
        parent = rows[parent_id]
        active_lineage = bool(parent["active"])
        parent_id = parent["parent_id"]
    postable = active_lineage and (
        row["level"] == "detail"
        or (row["level"] == "subsidiary" and row["id"] not in children)
    )
    result = dict(row)
    result["postable"] = bool(postable)
    return result


@router.get("/companies/{companyId}/accounts")
def list_accounts(
    companyId: UUID, request: Request,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    parent_id: UUID | None = None,
) -> dict:
    company = str(companyId)
    with engine_for(request).connect() as conn:
        require_member(conn, request, company)
        rows = all_company_accounts(conn, company)
        if parent_id is not None and str(parent_id) not in rows:
            # Never expose other company's parent or resource existence.
            raise IdentityError(404, "RESOURCE_NOT_FOUND")
        visible = [
            row for row in rows.values()
            if parent_id is None or row["parent_id"] == str(parent_id)
        ]
        visible.sort(key=lambda row: (row["full_code"], row["id"]))
        total = len(visible)
        start = (page - 1) * page_size
        return {
            "items": [serializable_account(row, rows) for row in visible[start:start + page_size]],
            "page": page, "page_size": page_size, "total": total,
        }


@router.post("/companies/{companyId}/accounts", status_code=201)
def create_account(companyId: UUID, body: AccountInput, request: Request) -> dict:
    company = str(companyId)
    with locked(engine_for(request)) as conn:
        require_member(conn, request, company, write=True)
        parent = None
        if body.parent_id is None:
            if body.level != "group":
                raise IdentityError(422, "VALIDATION_ERROR")
        else:
            parent = scoped_account(conn, company, str(body.parent_id))
            expected = LEVELS[LEVELS.index(body.level) - 1] if body.level != "group" else None
            if not expected or parent["level"] != expected:
                raise IdentityError(422, "VALIDATION_ERROR")
        full_code = (
            f'{parent["full_code"]}.{escape_segment(body.code)}'
            if parent is not None else escape_segment(body.code)
        )
        row = {
            "id": new_id(), "company_id": company,
            "parent_id": str(body.parent_id) if body.parent_id else None,
            "code": body.code, "name": body.name, "level": body.level,
            "active": body.active, "full_code": full_code,
        }
        try:
            with conn.begin_nested():
                conn.execute(t.accounts.insert().values(**row))
        except IntegrityError:
            raise IdentityError(409, "VALIDATION_ERROR") from None
        rows = all_company_accounts(conn, company)
        return serializable_account(row, rows)


@router.get("/companies/{companyId}/accounts/{accountId}")
def get_account(companyId: UUID, accountId: UUID, request: Request) -> dict:
    company = str(companyId)
    with engine_for(request).connect() as conn:
        require_member(conn, request, company)
        row = scoped_account(conn, company, str(accountId))
        return serializable_account(row, all_company_accounts(conn, company))


@router.patch("/companies/{companyId}/accounts/{accountId}")
def patch_account(companyId: UUID, accountId: UUID, body: AccountPatch,
                  request: Request) -> dict:
    company = str(companyId)
    with locked(engine_for(request)) as conn:
        require_member(conn, request, company, write=True)
        row = scoped_account(conn, company, str(accountId))
        updates = body.model_dump(exclude_unset=True)
        conn.execute(t.accounts.update().where(
            t.accounts.c.company_id == company, t.accounts.c.id == str(accountId),
        ).values(**updates))
        changed = {**dict(row), **updates}
        return serializable_account(changed, all_company_accounts(conn, company))


@router.delete("/companies/{companyId}/accounts/{accountId}", status_code=204)
def delete_account(companyId: UUID, accountId: UUID, request: Request) -> None:
    company = str(companyId)
    with locked(engine_for(request)) as conn:
        require_member(conn, request, company, write=True)
        scoped_account(conn, company, str(accountId))
        child = conn.execute(select(t.accounts.c.id).where(
            t.accounts.c.company_id == company, t.accounts.c.parent_id == str(accountId),
        )).first()
        if child:
            raise IdentityError(409, "ACCOUNT_IN_USE")
        # No journal Posting tables exist yet: actual used/posted protection
        # MUST be added and tested by the future authorized Posting owner.
        conn.execute(t.accounts.delete().where(
            t.accounts.c.company_id == company, t.accounts.c.id == str(accountId),
        ))
