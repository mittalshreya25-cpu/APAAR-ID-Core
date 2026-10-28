"""API router for programme offerings and intake approvals."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.approvals.models import IntakeApproval, ProgrammeOffering
from apaar.database import get_async_session
from apaar.shared.context import TenantContext

api_router = APIRouter(tags=["approvals"])


class OfferingOut(BaseModel):
    id: UUID
    institution_id: UUID
    campus: str
    course_name: str
    level: str
    mode: str
    shift: str
    is_active: bool


class ApprovalOut(BaseModel):
    id: UUID
    programme_offering_id: UUID
    institution_id: UUID
    academic_year: str
    approved_ordinary: int
    approved_supernumerary: int
    approved_nri: int
    approved_oci: int
    authority_status: str
    effective_from: str
    source_reference: str | None


@api_router.get("/offerings", response_model=list[OfferingOut], summary="List programme offerings")
async def list_offerings(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[OfferingOut]:
    """List programme offerings for the current institution or regulator."""
    query = select(ProgrammeOffering)
    if principal.institution_id and not principal.is_regulator():
        query = query.where(ProgrammeOffering.institution_id == principal.institution_id)

    res = await db.execute(query)
    offerings = res.scalars().all()
    return [
        OfferingOut(
            id=o.id,
            institution_id=o.institution_id,
            campus=o.campus,
            course_name=o.course_name,
            level=o.level,
            mode=o.mode,
            shift=o.shift,
            is_active=o.is_active,
        )
        for o in offerings
    ]


@api_router.get("", response_model=list[ApprovalOut], summary="List intake approvals")
async def list_approvals(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ApprovalOut]:
    """List approved intake capacities by offering and cohort."""
    query = select(IntakeApproval)
    if principal.institution_id and not principal.is_regulator():
        query = query.where(IntakeApproval.institution_id == principal.institution_id)

    res = await db.execute(query)
    approvals = res.scalars().all()
    return [
        ApprovalOut(
            id=a.id,
            programme_offering_id=a.programme_offering_id,
            institution_id=a.institution_id,
            academic_year=a.academic_year,
            approved_ordinary=a.approved_ordinary,
            approved_supernumerary=a.approved_supernumerary,
            approved_nri=a.approved_nri or 0,
            approved_oci=a.approved_oci or 0,
            authority_status=a.authority_status,
            effective_from=a.effective_from.isoformat() if a.effective_from else "",
            source_reference=a.source_reference,
        )
        for a in approvals
    ]
