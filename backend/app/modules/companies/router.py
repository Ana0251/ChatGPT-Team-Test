"""H-06 company API. Reuses H-05 identity guards and existing SQLite tables.

Company names are not authorization identities. Tenant visibility is granted
only through the current H-05 membership table, never a caller-supplied user ID.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select

from app.modules.audit.store import record_event
from app.modules.identity import tables as t
from app.modules.identity.router import IdentityError, IdentityRoute, actor_id, engine_for
from app.modules.identity.store import locked, new_id

router = APIRouter(tags=["Companies"], route_class=IdentityRoute)


class CompanyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, name: str) -> str:
        # Reject whitespace-only names rather than persisting unusable tenants.
        if not name.strip():
            raise ValueError("Company name must not be blank")
        return name


@router.get("/companies")
def list_companies(request: Request) -> list[dict[str, str]]:
    engine = engine_for(request)
    with engine.connect() as connection:
        user_id = actor_id(connection, request)
        rows = connection.execute(
            select(t.companies.c.id, t.companies.c.name)
            .join(t.memberships, t.memberships.c.company_id == t.companies.c.id)
            .where(t.memberships.c.user_id == user_id)
            .order_by(t.companies.c.id)
        ).mappings().all()
        return [dict(row) for row in rows]


@router.post("/companies", status_code=201)
def create_company(body: CompanyInput, request: Request) -> dict[str, str]:
    engine = engine_for(request)
    # BEGIN IMMEDIATE ensures company + current principal's owner membership
    # commit together; any insert failure rolls back both.
    with locked(engine) as connection:
        user_id = actor_id(connection, request, csrf=True)
        company_id = new_id()
        connection.execute(t.companies.insert().values(id=company_id, name=body.name))
        connection.execute(t.memberships.insert().values(
            user_id=user_id, company_id=company_id, role="owner"
        ))
        record_event(connection, actor_id=user_id, company_id=company_id,
                     action="company_created", safe_changes={"resource_id": company_id})
    return {"id": company_id, "name": body.name}


@router.get("/companies/{companyId}")
def get_company(companyId: UUID, request: Request) -> dict[str, str]:
    engine = engine_for(request)
    with engine.connect() as connection:
        user_id = actor_id(connection, request)
        row = connection.execute(
            select(t.companies.c.id, t.companies.c.name)
            .join(t.memberships, t.memberships.c.company_id == t.companies.c.id)
            .where(
                t.companies.c.id == str(companyId),
                t.memberships.c.user_id == user_id,
            )
        ).mappings().one_or_none()
        if row is None:
            # Indistinguishable nonexistent vs inaccessible tenant.
            raise IdentityError(404, "RESOURCE_NOT_FOUND")
        return dict(row)
