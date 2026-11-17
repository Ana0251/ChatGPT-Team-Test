"""H-07 company-scoped Gregorian half-open fiscal intervals.

All mutations run within H-05's SQLite BEGIN IMMEDIATE transaction, with live
principal, company membership and CSRF/Origin checks. No journal Posting API
exists yet; close-vs-posting concurrency is therefore explicitly NOT_TESTED.
"""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import and_, select

from app.modules.audit.store import record_event
from app.modules.fiscal import tables as f
from app.modules.identity.router import (
    IdentityError, IdentityRoute, actor_id, engine_for, role_for_company,
)
from app.modules.identity.store import audit_event, locked, new_id

router = APIRouter(tags=["Fiscal"], route_class=IdentityRoute)
CREATORS = ("owner", "admin", "accountant")
CLOSERS = ("owner", "admin")


class FiscalInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def valid_interval(self):
        if not self.name.strip() or self.start_date >= self.end_date:
            raise ValueError("Fiscal name must be nonblank and date interval nonempty")
        return self


def input_fields(body: FiscalInput) -> dict[str, str]:
    return {
        "name": body.name,
        "start_date": body.start_date.isoformat(),
        "end_date": body.end_date.isoformat(),
    }


def company_member(conn, request: Request, company: str, *, mutate: bool = False,
                   permitted: tuple[str, ...] | None = None) -> str:
    user_id = actor_id(conn, request, csrf=mutate)
    role_for_company(conn, user_id, company, permitted or ("owner", "admin", "accountant", "viewer"))
    return user_id


def scoped_year(conn, company: str, year_id: str):
    year = conn.execute(select(f.years).where(
        f.years.c.company_id == company, f.years.c.id == year_id
    )).mappings().one_or_none()
    if year is None:
        raise IdentityError(404, "RESOURCE_NOT_FOUND")
    return year


def scoped_period(conn, company: str, year_id: str, period_id: str):
    period = conn.execute(select(f.periods).where(
        f.periods.c.company_id == company,
        f.periods.c.year_id == year_id,
        f.periods.c.id == period_id,
    )).mappings().one_or_none()
    if period is None:
        raise IdentityError(404, "RESOURCE_NOT_FOUND")
    return period


def overlaps(start: str, end: str, other_start, other_end):
    return and_(other_start < end, other_end > start)


@router.get("/companies/{companyId}/fiscal-years")
def list_fiscal_years(companyId: UUID, request: Request) -> list[dict]:
    company = str(companyId)
    with engine_for(request).connect() as conn:
        company_member(conn, request, company)
        return [dict(row) for row in conn.execute(
            select(f.years).where(f.years.c.company_id == company)
            .order_by(f.years.c.start_date, f.years.c.id)
        ).mappings()]


@router.post("/companies/{companyId}/fiscal-years", status_code=201)
def create_fiscal_year(companyId: UUID, body: FiscalInput, request: Request) -> dict:
    company = str(companyId)
    values = input_fields(body)
    with locked(engine_for(request)) as conn:
        company_member(conn, request, company, mutate=True, permitted=CREATORS)
        overlapping = conn.execute(select(f.years.c.id).where(
            f.years.c.company_id == company,
            overlaps(values["start_date"], values["end_date"],
                     f.years.c.start_date, f.years.c.end_date)
        )).first()
        if overlapping:
            raise IdentityError(409, "PERIOD_OVERLAP")
        result = {"id": new_id(), "company_id": company, **values}
        conn.execute(f.years.insert().values(**result))
        record_event(conn, actor_id=actor_id(conn, request), company_id=company,
                     action="fiscal_year_created",
                     safe_changes={"resource_id": result["id"]})
        return result


@router.get("/companies/{companyId}/fiscal-years/{yearId}/periods")
def list_fiscal_periods(companyId: UUID, yearId: UUID, request: Request) -> list[dict]:
    company, year_id = str(companyId), str(yearId)
    with engine_for(request).connect() as conn:
        company_member(conn, request, company)
        scoped_year(conn, company, year_id)
        return [dict(row) for row in conn.execute(
            select(f.periods).where(
                f.periods.c.company_id == company, f.periods.c.year_id == year_id
            ).order_by(f.periods.c.start_date, f.periods.c.id)
        ).mappings()]


@router.post("/companies/{companyId}/fiscal-years/{yearId}/periods", status_code=201)
def create_fiscal_period(companyId: UUID, yearId: UUID, body: FiscalInput,
                         request: Request) -> dict:
    company, year_id = str(companyId), str(yearId)
    values = input_fields(body)
    with locked(engine_for(request)) as conn:
        company_member(conn, request, company, mutate=True, permitted=CREATORS)
        year = scoped_year(conn, company, year_id)
        if values["start_date"] < year["start_date"] or values["end_date"] > year["end_date"]:
            raise IdentityError(422, "INVALID_DATE_RANGE")
        overlapping = conn.execute(select(f.periods.c.id).where(
            f.periods.c.company_id == company, f.periods.c.year_id == year_id,
            overlaps(values["start_date"], values["end_date"],
                     f.periods.c.start_date, f.periods.c.end_date)
        )).first()
        if overlapping:
            raise IdentityError(409, "PERIOD_OVERLAP")
        result = {
            "id": new_id(), "company_id": company, "year_id": year_id,
            "status": "open", **values,
        }
        conn.execute(f.periods.insert().values(**result))
        record_event(conn, actor_id=actor_id(conn, request), company_id=company,
                     action="fiscal_period_created",
                     safe_changes={"resource_id": result["id"], "status": "open"})
        return result


@router.post("/companies/{companyId}/fiscal-years/{yearId}/periods/{periodId}/close")
def close_fiscal_period(companyId: UUID, yearId: UUID, periodId: UUID,
                        request: Request) -> dict:
    company, year_id, period_id = str(companyId), str(yearId), str(periodId)
    with locked(engine_for(request)) as conn:
        user_id = company_member(conn, request, company, mutate=True, permitted=CLOSERS)
        scoped_year(conn, company, year_id)
        period = scoped_period(conn, company, year_id, period_id)
        if period["status"] == "closed":
            # Explicit deterministic non-idempotent second transition.
            raise IdentityError(409, "PERIOD_CLOSED")
        conn.execute(f.periods.update().where(
            f.periods.c.company_id == company, f.periods.c.year_id == year_id,
            f.periods.c.id == period_id, f.periods.c.status == "open",
        ).values(status="closed"))
        audit_event(conn, "fiscal_period_closed", user_id, company)
        record_event(conn, actor_id=user_id, company_id=company,
                     action="fiscal_period_closed",
                     safe_changes={"resource_id": period_id, "status": "closed"})
        return {**dict(period), "status": "closed"}
