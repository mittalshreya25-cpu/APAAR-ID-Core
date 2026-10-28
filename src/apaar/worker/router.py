"""API router for job queue inspection and manual trigger."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.database import get_async_session
from apaar.shared.context import TenantContext
from apaar.worker.models import Job

api_router = APIRouter(tags=["worker"])


class JobOut(BaseModel):
    id: UUID
    job_type: str
    institution_id: UUID | None
    status: str
    attempt_count: int
    max_attempts: int
    effect_key: str | None
    completed_at: str | None
    failed_at: str | None
    failure_reason: str | None
    result_json: dict | None


@api_router.get("/jobs/{job_id}", response_model=JobOut, summary="Get job status")
async def get_job(
    job_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> JobOut:
    """Retrieve status and outcome of an asynchronous background job."""
    res = await db.execute(select(Job).where(Job.id == job_id))
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Job {job_id} not found."},
        )

    if principal.institution_id and job.institution_id and principal.institution_id != job.institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access denied."},
        )

    return JobOut(
        id=job.id,
        job_type=job.job_type,
        institution_id=job.institution_id,
        status=job.status.value,
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        effect_key=job.effect_key,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        failed_at=job.failed_at.isoformat() if job.failed_at else None,
        failure_reason=job.failure_reason,
        result_json=job.result_json,
    )
