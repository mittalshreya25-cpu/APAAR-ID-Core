"""API router for submissions: upload, staging, status, and candidate revisions."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import Preparer, get_current_principal
from apaar.database import get_async_session
from apaar.shared.context import TenantContext
from apaar.shared.errors import UploadError
from apaar.shared.types import SubmissionStatus
from apaar.submissions.models import StagedRow, Submission, SubmissionScopeLock
from apaar.submissions.parser import SCHEMA_VERSION, SubmissionParser

api_router = APIRouter(tags=["submissions"])


class SubmissionOut(BaseModel):
    id: UUID
    institution_id: UUID
    programme_offering_id: UUID
    admission_cohort: str
    expected_base_version: int | None
    file_hash: str
    file_size: int
    original_filename: str
    declared_total_rows: int
    received_rows: int
    processed_rows: int
    rejected_rows: int
    status: str
    idempotency_key: str
    created_by: str
    version: int


class StagedRowOut(BaseModel):
    id: UUID
    row_number: int
    raw_data_json: dict
    normalized_data_json: dict | None
    parse_errors_json: list | None
    is_rejected: bool


@api_router.post("", response_model=SubmissionOut, status_code=status.HTTP_201_CREATED, summary="Upload and stage an enrolment submission")
async def create_submission(
    principal: Preparer,
    db: Annotated[AsyncSession, Depends(get_async_session)],
    programme_offering_id: Annotated[UUID, Form(...)],
    admission_cohort: Annotated[str, Form(...)],
    file: UploadFile = File(...),
    expected_base_version: Annotated[int | None, Form()] = None,
    declared_total_rows: Annotated[int | None, Form()] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> SubmissionOut:
    """Stage a UTF-8 CSV or JSON enrolment submission file.

    Enforces file size limit, schema constraints, scope lock checks,
    and stores raw and normalized rows.
    """
    institution_id = principal.require_institution()
    actual_idempotency_key = idempotency_key or str(uuid4())

    # Check for existing idempotency key
    existing_sub = (
        await db.execute(
            select(Submission).where(Submission.idempotency_key == actual_idempotency_key)
        )
    ).scalar_one_or_none()

    if existing_sub:
        return _submission_to_out(existing_sub)

    # Find or create scope lock
    lock_query = select(SubmissionScopeLock).where(
        SubmissionScopeLock.institution_id == institution_id,
        SubmissionScopeLock.programme_offering_id == programme_offering_id,
        SubmissionScopeLock.admission_cohort == admission_cohort,
    )
    scope_lock = (await db.execute(lock_query)).scalar_one_or_none()
    if not scope_lock:
        scope_lock = SubmissionScopeLock(
            institution_id=institution_id,
            programme_offering_id=programme_offering_id,
            admission_cohort=admission_cohort,
            reported_version=0,
            certified_version=0,
        )
        db.add(scope_lock)
        await db.flush()

    # Guard against lost-update races
    if expected_base_version is not None and expected_base_version != scope_lock.reported_version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "STALE_VERSION",
                "message": f"Expected version {expected_base_version} does not match current reported version {scope_lock.reported_version}.",
            },
        )

    # Read and parse file content
    content = await file.read()
    parser = SubmissionParser()
    try:
        parse_result = parser.parse(content, file.filename or "upload.csv")
    except UploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": exc.error_code, "message": exc.message},
        ) from exc

    submission = Submission(
        institution_id=institution_id,
        programme_offering_id=programme_offering_id,
        admission_cohort=admission_cohort,
        scope_lock_id=scope_lock.id,
        expected_base_version=expected_base_version,
        file_hash=parse_result.file_hash,
        file_size=parse_result.file_size,
        original_filename=parse_result.original_filename,
        schema_version=SCHEMA_VERSION,
        parser_version="1.0",
        declared_total_rows=declared_total_rows or parse_result.received_rows,
        received_rows=parse_result.received_rows,
        processed_rows=parse_result.processed_rows,
        rejected_rows=parse_result.rejected_rows,
        status=SubmissionStatus.DRAFT.value,
        idempotency_key=actual_idempotency_key,
        created_by=principal.subject_id,
    )
    db.add(submission)
    await db.flush()

    # Create staged rows
    for r in parse_result.rows:
        staged = StagedRow(
            submission_id=submission.id,
            row_number=r.row_number,
            raw_data_json=r.raw_data,
            normalized_data_json=r.normalized_data,
            parse_errors_json=r.parse_errors,
            is_rejected=r.is_rejected,
        )
        db.add(staged)

    await db.commit()
    await db.refresh(submission)
    return _submission_to_out(submission)


@api_router.get("/{submission_id}", response_model=SubmissionOut, summary="Get submission details")
async def get_submission(
    submission_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> SubmissionOut:
    """Get submission status and details."""
    res = await db.execute(select(Submission).where(Submission.id == submission_id))
    sub = res.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Submission {submission_id} not found."},
        )

    if principal.institution_id and principal.institution_id != sub.institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access denied."},
        )

    return _submission_to_out(sub)


@api_router.get("/{submission_id}/rows", response_model=list[StagedRowOut], summary="List staged rows")
async def list_submission_rows(
    submission_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    offset: int = 0,
    limit: int = 50,
) -> list[StagedRowOut]:
    """List staged rows of a submission with pagination."""
    sub = (await db.execute(select(Submission).where(Submission.id == submission_id))).scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Submission {submission_id} not found."},
        )

    if principal.institution_id and principal.institution_id != sub.institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access denied."},
        )

    query = (
        select(StagedRow)
        .where(StagedRow.submission_id == submission_id)
        .order_by(StagedRow.row_number)
        .offset(offset)
        .limit(min(limit, 100))
    )
    rows = (await db.execute(query)).scalars().all()
    return [
        StagedRowOut(
            id=r.id,
            row_number=r.row_number,
            raw_data_json=r.raw_data_json,
            normalized_data_json=r.normalized_data_json,
            parse_errors_json=r.parse_errors_json,
            is_rejected=r.is_rejected,
        )
        for r in rows
    ]


def _submission_to_out(sub: Submission) -> SubmissionOut:
    return SubmissionOut(
        id=sub.id,
        institution_id=sub.institution_id,
        programme_offering_id=sub.programme_offering_id,
        admission_cohort=sub.admission_cohort,
        expected_base_version=sub.expected_base_version,
        file_hash=sub.file_hash,
        file_size=sub.file_size,
        original_filename=sub.original_filename,
        declared_total_rows=sub.declared_total_rows,
        received_rows=sub.received_rows,
        processed_rows=sub.processed_rows,
        rejected_rows=sub.rejected_rows,
        status=sub.status,
        idempotency_key=sub.idempotency_key,
        created_by=sub.created_by,
        version=sub.version,
    )
