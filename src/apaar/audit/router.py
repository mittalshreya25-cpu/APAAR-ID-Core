"""API router for immutable audit event logs."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.audit.models import AuditEvent
from apaar.database import get_async_session
from apaar.shared.context import TenantContext

api_router = APIRouter(tags=["audit"])


class AuditEventOut(BaseModel):
    id: UUID
    event_type: str
    principal: str
    institution_id: UUID | None
    object_type: str
    object_id: UUID | None
    action: str
    outcome: str
    purpose: str | None
    timestamp: str
    request_id: str


@api_router.get("", response_model=list[AuditEventOut], summary="List audit events")
async def list_audit_events(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    limit: int = 50,
) -> list[AuditEventOut]:
    """Retrieve audit events. Personal identifiers are never recorded in audit entries."""
    query = select(AuditEvent)
    if principal.institution_id and not principal.is_regulator():
        query = query.where(AuditEvent.institution_id == principal.institution_id)

    query = query.order_by(AuditEvent.timestamp.desc()).limit(min(limit, 200))
    events = (await db.execute(query)).scalars().all()

    return [
        AuditEventOut(
            id=e.id,
            event_type=e.event_type,
            principal=e.principal,
            institution_id=e.institution_id,
            object_type=e.object_type,
            object_id=e.object_id,
            action=e.action,
            outcome=e.outcome,
            purpose=e.purpose,
            timestamp=e.timestamp.isoformat(),
            request_id=e.request_id,
        )
        for e in events
    ]
