"""API router for review cases and accountable decisions."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.audit.models import AuditEvent
from apaar.database import get_async_session
from apaar.review.models import ReviewCase, ReviewDecision
from apaar.shared.context import TenantContext
from apaar.shared.types import ReviewCaseStatus

api_router = APIRouter(tags=["review"])


class ReviewCaseOut(BaseModel):
    id: UUID
    institution_id: UUID
    case_type: str
    finding_ref_id: UUID | None
    status: str
    opened_by: str
    opened_at: str
    resolved_by: str | None
    resolved_at: str | None
    resolution_explanation: str | None
    is_overlap_case: bool


class DecisionCreate(BaseModel):
    decision: str  # RESOLVED | DISMISSED | REOPENED
    explanation: str


class DecisionOut(BaseModel):
    id: UUID
    review_case_id: UUID
    decision: str
    made_by: str
    made_at: str
    explanation: str
    supersedes_decision_id: UUID | None


@api_router.get("/cases", response_model=list[ReviewCaseOut], summary="List review cases")
async def list_cases(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    case_status: str | None = None,
) -> list[ReviewCaseOut]:
    """List review cases for the current institution or regulator."""
    query = select(ReviewCase)
    if principal.institution_id and not principal.is_regulator():
        query = query.where(ReviewCase.institution_id == principal.institution_id)

    if case_status:
        query = query.where(ReviewCase.status == case_status)

    res = await db.execute(query.order_by(ReviewCase.opened_at.desc()))
    cases = res.scalars().all()
    return [
        ReviewCaseOut(
            id=c.id,
            institution_id=c.institution_id,
            case_type=c.case_type,
            finding_ref_id=c.finding_ref_id,
            status=c.status,
            opened_by=c.opened_by,
            opened_at=c.opened_at.isoformat(),
            resolved_by=c.resolved_by,
            resolved_at=c.resolved_at.isoformat() if c.resolved_at else None,
            resolution_explanation=c.resolution_explanation,
            is_overlap_case=c.is_overlap_case,
        )
        for c in cases
    ]


@api_router.post("/cases/{case_id}/decisions", response_model=DecisionOut, summary="Record a review decision")
async def record_decision(
    case_id: UUID,
    body: DecisionCreate,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> DecisionOut:
    """Record an accountable decision on a review case.

    Supports RESOLVED, DISMISSED, or REOPENED.
    An overlap case dismissal does not erase findings or grant future blanket permission.
    """
    if body.decision not in ("RESOLVED", "DISMISSED", "REOPENED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error_code": "INVALID_DECISION", "message": "Decision must be RESOLVED, DISMISSED, or REOPENED."},
        )

    case_res = await db.execute(select(ReviewCase).where(ReviewCase.id == case_id))
    case = case_res.scalar_one_or_none()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"ReviewCase {case_id} not found."},
        )

    if principal.institution_id and principal.institution_id != case.institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access denied."},
        )

    now = datetime.now(UTC)

    # Find previous latest decision to supersede
    prev_dec_res = await db.execute(
        select(ReviewDecision)
        .where(ReviewDecision.review_case_id == case.id)
        .order_by(ReviewDecision.made_at.desc())
    )
    prev_dec = prev_dec_res.scalars().first()

    decision = ReviewDecision(
        review_case_id=case.id,
        decision=body.decision,
        made_by=principal.subject_id,
        made_at=now,
        explanation=body.explanation,
        supersedes_decision_id=prev_dec.id if prev_dec else None,
    )
    db.add(decision)

    # Update case status
    if body.decision == "RESOLVED":
        case.status = ReviewCaseStatus.RESOLVED.value
        case.resolved_by = principal.subject_id
        case.resolved_at = now
        case.resolution_explanation = body.explanation
    elif body.decision == "DISMISSED":
        case.status = ReviewCaseStatus.DISMISSED.value
        case.resolved_by = principal.subject_id
        case.resolved_at = now
        case.resolution_explanation = body.explanation
    elif body.decision == "REOPENED":
        case.status = ReviewCaseStatus.OPEN.value
        case.resolved_by = None
        case.resolved_at = None

    # Audit event
    audit = AuditEvent(
        event_type="REVIEW_DECISION_RECORDED",
        principal=principal.subject_id,
        institution_id=case.institution_id,
        object_type="review_case",
        object_id=case.id,
        action=f"DECISION_{body.decision}",
        outcome="SUCCESS",
        purpose="Accountable Review Resolution",
        timestamp=now,
        request_id=principal.request_id,
    )
    db.add(audit)

    await db.commit()
    await db.refresh(decision)

    return DecisionOut(
        id=decision.id,
        review_case_id=decision.review_case_id,
        decision=decision.decision,
        made_by=decision.made_by,
        made_at=decision.made_at.isoformat(),
        explanation=decision.explanation,
        supersedes_decision_id=decision.supersedes_decision_id,
    )


@api_router.post(
    "/submissions/{submission_id}/check-overlaps",
    response_model=list[ReviewCaseOut],
    summary="Scan submission for cross-institution temporal overlaps",
)
async def check_submission_overlaps(
    submission_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ReviewCaseOut]:
    """Perform central cross-institution temporal overlap check on submission rows.

    Guarantees:
    - Only authorized actors can trigger central review scans.
    - Counterpart details (institution name/student PII) are suppressed.
    - Returns opened or active ReviewCase items.
    """
    from apaar.review.service import detect_cross_institution_overlaps

    cases = await detect_cross_institution_overlaps(db, submission_id, principal)
    return [
        ReviewCaseOut(
            id=c.id,
            institution_id=c.institution_id,
            case_type=c.case_type,
            finding_ref_id=c.finding_ref_id,
            status=c.status,
            opened_by=c.opened_by,
            opened_at=c.opened_at.isoformat(),
            resolved_by=c.resolved_by,
            resolved_at=c.resolved_at.isoformat() if c.resolved_at else None,
            resolution_explanation=c.resolution_explanation,
            is_overlap_case=c.is_overlap_case,
        )
        for c in cases
    ]
