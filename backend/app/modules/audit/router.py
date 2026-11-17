"""H-10 read-only, role- and tenant-scoped AuditEvent GET (OpenAPI rc.4).

Reads only immutable H-10 audit snapshots and future H-10 records. Existing
H-05 events written AFTER migration are not automatically captured until
separately authorized, same-transaction hooks are installed. No public
create/update/delete endpoints for audit history exist.
"""
from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Query, Request, Response
from sqlalchemy import func, select

from app.modules.audit import tables as a
from app.modules.audit.store import ACTIONS, safe_payload
from app.modules.identity.router import IdentityRoute, actor_id, engine_for, role_for_company

router = APIRouter(tags=["Audit"], route_class=IdentityRoute)


@router.get("/companies/{companyId}/audit-events")
def list_audit_events(
    companyId: UUID, request: Request, response: Response,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
) -> dict:
    company = str(companyId)
    response.headers["Cache-Control"] = "no-store"
    with engine_for(request).connect() as conn:
        user_id = actor_id(conn, request)
        # Recheck live membership for every request. Nonmembers are neutral
        # 404, even for a real foreign company's UUID; viewer/accountant 403.
        role_for_company(conn, user_id, company, ("owner", "admin"))
        scope = (
            a.events.c.company_id == company,
            a.events.c.action.in_(ACTIONS),
        )
        total = conn.execute(select(func.count()).select_from(a.events).where(*scope)).scalar_one()
        rows = conn.execute(
            select(a.events).where(*scope)
            .order_by(a.events.c.occurred_at.desc(), a.events.c.id.desc())
            .offset((page - 1) * page_size).limit(page_size)
        ).mappings().all()
        items: list[dict] = []
        for row in rows:
            item = {
                "id": row["id"],
                "company_id": row["company_id"],
                "actor_id": row["actor_id"],
                "action": row["action"],
                "occurred_at": row["occurred_at"],
            }
            if row["safe_changes"] is not None:
                # Fail closed for malformed/unsafe legacy or directly inserted
                # database metadata; never echo raw secrets through HTTP.
                try:
                    decoded = json.loads(row["safe_changes"])
                    if safe_payload(decoded) is not None:
                        item["safe_changes"] = decoded
                except (ValueError, TypeError):
                    pass
            items.append(item)
        return {"items": items, "page": page, "page_size": page_size, "total": total}
