"""API router for institutions and memberships."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.database import get_async_session
from apaar.institutions.models import Institution
from apaar.shared.context import TenantContext

api_router = APIRouter(tags=["institutions"])


class InstitutionOut(BaseModel):
    id: UUID
    code: str
    name: str
    status: str
    version: int


class MembershipOut(BaseModel):
    id: UUID
    institution_id: UUID
    subject_id: str
    role: str
    is_active: bool


@api_router.get("", response_model=list[InstitutionOut], summary="List registered institutions")
async def list_institutions(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[InstitutionOut]:
    """List institutions available to the caller."""
    query = select(Institution)
    if principal.institution_id and not principal.is_regulator():
        query = query.where(Institution.id == principal.institution_id)

    res = await db.execute(query)
    insts = res.scalars().all()
    return [
        InstitutionOut(
            id=i.id,
            code=i.code,
            name=i.name,
            status=i.status,
            version=i.version,
        )
        for i in insts
    ]


@api_router.get("/{institution_id}", response_model=InstitutionOut, summary="Get institution by ID")
async def get_institution(
    institution_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> InstitutionOut:
    """Retrieve institution details."""
    if principal.institution_id and principal.institution_id != institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access to foreign institution denied."},
        )

    res = await db.execute(select(Institution).where(Institution.id == institution_id))
    inst = res.scalar_one_or_none()
    if not inst:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Institution {institution_id} not found."},
        )

    return InstitutionOut(
        id=inst.id,
        code=inst.code,
        name=inst.name,
        status=inst.status,
        version=inst.version,
    )
