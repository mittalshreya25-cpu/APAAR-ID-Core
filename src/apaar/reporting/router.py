"""API router for monitoring reports, quality dashboards, and permissioned disclosure."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.approvals.models import IntakeApproval, ProgrammeOffering
from apaar.audit.models import AuditEvent
from apaar.database import get_async_session
from apaar.reporting.models import DisclosureGrant, ReportSnapshot, VerificationRequest
from apaar.shared.context import TenantContext
from apaar.shared.types import (
    ReportAudience,
    VerificationRequestStatus,
)
from apaar.submissions.models import Submission, SubmissionScopeLock
from apaar.validation.models import ValidationFinding, ValidationRun

api_router = APIRouter(tags=["reporting"])


class IntakeReportOut(BaseModel):
    institution_id: UUID | None
    academic_year: str
    offerings: list[dict]
    total_approved_ordinary: int
    total_approved_supernumerary: int
    total_reported: int
    total_certified: int
    as_of: str
    data_freshness_seconds: int = 15
    provenance: str = "SYNTHETIC_DEMO_REPORT"


class QualityReportOut(BaseModel):
    institution_id: UUID | None
    total_submissions: int
    total_findings: int
    blocking_findings: int
    rule_breakdown: dict[str, int]
    findings_by_outcome: dict[str, int]
    as_of: str
    provenance: str = "SYNTHETIC_DEMO_REPORT"


class VerificationRequestCreate(BaseModel):
    episode_id: UUID
    purpose: str
    requested_fields: list[str] = ["enrolment_status", "programme_name", "admission_cohort"]
    requester_org: str | None = None


class VerificationRequestOut(BaseModel):
    id: UUID
    requester_subject: str
    requester_org: str | None
    purpose: str
    episode_id: UUID
    requested_fields: list[str]
    status: str
    created_at: str


class DecisionRequest(BaseModel):
    status: str  # APPROVED | DENIED
    decision_reason: str


class DisclosureResponse(BaseModel):
    request_id: UUID
    purpose: str
    disclosed_data: dict
    expires_at: str
    synthetic: bool = True
    disclaimer: str = "Consent-based purpose-scoped synthetic disclosure."


@api_router.get("/intake", response_model=IntakeReportOut, summary="Intake capacity and reconciliation report")
async def get_intake_report(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    academic_year: str = "2024-25",
) -> IntakeReportOut:
    """Generate reconciled intake report showing approved vs reported vs certified."""
    inst_id = principal.institution_id

    # Offerings query
    off_query = select(ProgrammeOffering)
    if inst_id and not principal.is_regulator():
        off_query = off_query.where(ProgrammeOffering.institution_id == inst_id)

    offerings = (await db.execute(off_query)).scalars().all()
    offering_ids = [o.id for o in offerings]

    # Approvals query
    appr_query = select(IntakeApproval).where(
        IntakeApproval.programme_offering_id.in_(offering_ids),
        IntakeApproval.academic_year == academic_year,
    )
    approvals = (await db.execute(appr_query)).scalars().all()
    approval_map = {a.programme_offering_id: a for a in approvals}

    # Locks query for certified and reported counts
    locks_query = select(SubmissionScopeLock).where(
        SubmissionScopeLock.programme_offering_id.in_(offering_ids),
        SubmissionScopeLock.admission_cohort == academic_year,
    )
    locks = (await db.execute(locks_query)).scalars().all()
    lock_map = {l.programme_offering_id: l for l in locks}

    offering_reports = []
    tot_ord = 0
    tot_sn = 0
    tot_rep = 0
    tot_cert = 0

    for off in offerings:
        appr = approval_map.get(off.id)
        lock = lock_map.get(off.id)

        appr_ord = appr.approved_ordinary if appr else 0
        appr_sn = appr.approved_supernumerary if appr else 0
        rep_v = lock.reported_version if lock else 0
        cert_v = lock.certified_version if lock else 0

        tot_ord += appr_ord
        tot_sn += appr_sn
        tot_rep += rep_v
        tot_cert += cert_v

        offering_reports.append(
            {
                "offering_id": str(off.id),
                "course_name": off.course_name,
                "level": off.level,
                "approved_ordinary": appr_ord,
                "approved_supernumerary": appr_sn,
                "reported_population": rep_v,
                "certified_population": cert_v,
                "utilization_percent": round((cert_v / appr_ord * 100), 1) if appr_ord > 0 else 0,
            }
        )

    return IntakeReportOut(
        institution_id=inst_id,
        academic_year=academic_year,
        offerings=offering_reports,
        total_approved_ordinary=tot_ord,
        total_approved_supernumerary=tot_sn,
        total_reported=tot_rep,
        total_certified=tot_cert,
        as_of=datetime.now(UTC).isoformat(),
        data_freshness_seconds=15,
    )


@api_router.get("/quality", response_model=QualityReportOut, summary="Data quality and validation finding breakdown")
async def get_quality_report(
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> QualityReportOut:
    """Breakdown of data quality findings by rule ID and outcome."""
    inst_id = principal.institution_id

    sub_q = select(Submission)
    if inst_id and not principal.is_regulator():
        sub_q = sub_q.where(Submission.institution_id == inst_id)
    subs = (await db.execute(sub_q)).scalars().all()
    sub_ids = [s.id for s in subs]

    vrun_q = select(ValidationRun).where(ValidationRun.submission_id.in_(sub_ids))
    vruns = (await db.execute(vrun_q)).scalars().all()
    vrun_ids = [v.id for v in vruns]

    tot_findings = sum(v.total_findings for v in vruns)
    tot_blocking = sum(v.blocking_findings for v in vruns)

    finding_q = select(ValidationFinding).where(ValidationFinding.validation_run_id.in_(vrun_ids))
    findings = (await db.execute(finding_q)).scalars().all()

    rule_breakdown: dict[str, int] = {}
    outcome_breakdown: dict[str, int] = {}

    for f in findings:
        rule_breakdown[f.rule_id] = rule_breakdown.get(f.rule_id, 0) + 1
        outcome_breakdown[f.outcome] = outcome_breakdown.get(f.outcome, 0) + 1

    return QualityReportOut(
        institution_id=inst_id,
        total_submissions=len(subs),
        total_findings=tot_findings,
        blocking_findings=tot_blocking,
        rule_breakdown=rule_breakdown,
        findings_by_outcome=outcome_breakdown,
        as_of=datetime.now(UTC).isoformat(),
    )


@api_router.post("/verification-requests", response_model=VerificationRequestOut, summary="Submit a purpose-scoped verification request")
async def create_verification_request(
    body: VerificationRequestCreate,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> VerificationRequestOut:
    """Submit a request to verify an enrolment episode.

    Requires explicit purpose and requested fields.
    """
    now = datetime.now(UTC)
    vr = VerificationRequest(
        requester_subject=principal.subject_id,
        requester_org=body.requester_org,
        purpose=body.purpose,
        episode_id=body.episode_id,
        requested_fields_json=body.requested_fields,
        status=VerificationRequestStatus.PENDING.value,
    )
    db.add(vr)
    await db.commit()
    await db.refresh(vr)

    return VerificationRequestOut(
        id=vr.id,
        requester_subject=vr.requester_subject,
        requester_org=vr.requester_org,
        purpose=vr.purpose,
        episode_id=vr.episode_id,
        requested_fields=vr.requested_fields_json,
        status=vr.status,
        created_at=vr.created_at.isoformat(),
    )


@api_router.post("/verification-requests/{request_id}/decisions", summary="Approve or deny verification request")
async def decide_verification_request(
    request_id: UUID,
    body: DecisionRequest,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict:
    """Decide a verification request.

    If APPROVED, creates a DisclosureGrant bound to an immutable snapshot.
    """
    res = await db.execute(select(VerificationRequest).where(VerificationRequest.id == request_id))
    vr = res.scalar_one_or_none()
    if not vr:
        raise HTTPException(status_code=404, detail="Verification request not found.")

    if body.status not in ("APPROVED", "DENIED"):
        raise HTTPException(status_code=400, detail="Status must be APPROVED or DENIED.")

    now = datetime.now(UTC)
    vr.status = body.status
    vr.decided_by = principal.subject_id
    vr.decided_at = now
    vr.decision_reason = body.decision_reason

    grant_id = None
    if body.status == "APPROVED":
        # Create a ReportSnapshot for binding
        snapshot = ReportSnapshot(
            institution_id=principal.institution_id,
            report_type="VERIFICATION_DISCLOSURE",
            generated_at=now,
            as_of=now,
            snapshot_data_json={
                "enrolment_status": "ACTIVE",
                "programme_name": "B.Tech Computer Science (Synthetic)",
                "admission_cohort": "2024-25",
            },
            audience=ReportAudience.INSTITUTION.value,
        )
        db.add(snapshot)
        await db.flush()

        grant = DisclosureGrant(
            verification_request_id=vr.id,
            requester_subject=vr.requester_subject,
            recipient_subject=vr.requester_subject,
            purpose=vr.purpose,
            allowed_fields_json=vr.requested_fields_json,
            snapshot_id=snapshot.id,
            expires_at=now + timedelta(days=30),
            is_revoked=False,
        )
        db.add(grant)
        await db.flush()
        grant_id = grant.id

    await db.commit()
    return {
        "request_id": str(vr.id),
        "status": vr.status,
        "grant_id": str(grant_id) if grant_id else None,
        "decided_by": vr.decided_by,
        "decided_at": now.isoformat(),
    }


@api_router.post("/verification-requests/{request_id}/disclosures", response_model=DisclosureResponse, summary="Redeem and disclose authorized data")
async def redeem_disclosure(
    request_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> DisclosureResponse:
    """Redeem an approved verification request and disclose permitted fields.

    Rechecks grant, expiration, and revocation status for every redemption.
    """
    res = await db.execute(select(VerificationRequest).where(VerificationRequest.id == request_id))
    vr = res.scalar_one_or_none()
    if not vr or vr.status != "APPROVED":
        raise HTTPException(status_code=403, detail="Verification request is not approved.")

    grant_res = await db.execute(
        select(DisclosureGrant).where(
            DisclosureGrant.verification_request_id == request_id,
            DisclosureGrant.is_revoked == False,  # noqa: E712
        )
    )
    grant = grant_res.scalars().first()
    if not grant:
        raise HTTPException(status_code=403, detail="No active disclosure grant found.")

    now = datetime.now(UTC)
    if grant.expires_at.replace(tzinfo=UTC) < now:
        raise HTTPException(status_code=403, detail="Disclosure grant has expired.")

    # Audit redemption
    audit = AuditEvent(
        event_type="DISCLOSURE_REDEEMED",
        principal=principal.subject_id,
        institution_id=None,
        object_type="disclosure_grant",
        object_id=grant.id,
        action="DISCLOSE",
        outcome="SUCCESS",
        purpose=grant.purpose,
        timestamp=now,
        request_id=principal.request_id,
    )
    db.add(audit)
    await db.commit()

    # Filter disclosed fields strictly to allowed_fields_json
    full_data = {
        "enrolment_status": "ACTIVE",
        "programme_name": "B.Tech Computer Science (Synthetic)",
        "admission_cohort": "2024-25",
        "institution": "Demo Engineering College (Synthetic)",
    }
    filtered = {k: v for k, v in full_data.items() if k in grant.allowed_fields_json}

    return DisclosureResponse(
        request_id=vr.id,
        purpose=grant.purpose,
        disclosed_data=filtered,
        expires_at=grant.expires_at.isoformat(),
    )
