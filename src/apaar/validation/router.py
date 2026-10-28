"""API router for validation runs, rule evaluation, and certification."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import Certifier, get_current_principal
from apaar.approvals.models import IntakeApproval
from apaar.audit.models import AuditEvent
from apaar.database import get_async_session
from apaar.identity.mock_provider import get_mock_provider
from apaar.shared.context import TenantContext
from apaar.shared.types import (
    SubmissionStatus,
)
from apaar.submissions.models import StagedRow, Submission, SubmissionScopeLock
from apaar.validation.models import RuleBundle, ValidationFinding, ValidationRun
from apaar.validation.rules import (
    evaluate_submission_rows,
    rule_capacity_check,
)

api_router = APIRouter(tags=["validation"])


class ValidationRunOut(BaseModel):
    id: UUID
    submission_id: UUID
    status: str
    total_findings: int
    blocking_findings: int
    evaluated_at: str
    evaluator_code_revision: str


class FindingOut(BaseModel):
    id: UUID
    rule_id: str
    rule_version: str
    outcome: str
    observed_value: str | None
    expected_condition: str | None
    confidence: str | None
    remediation: str | None
    is_blocking: bool
    staged_row_id: UUID | None


class CertificationOut(BaseModel):
    submission_id: UUID
    status: str
    certified_by: str
    certified_at: str
    reported_version: int
    certified_version: int
    ordinary_count: int
    supernumerary_count: int
    nri_count: int


@api_router.post("/submissions/{submission_id}/validate", response_model=ValidationRunOut, summary="Trigger validation on a submission")
async def trigger_validation(
    submission_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> ValidationRunOut:
    """Run full synthetic validation against all staged rows of a submission.

    Evaluates structural rules, mock APAAR registry provider checks,
    and intake capacity allocation against the active approval.
    """
    sub_res = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = sub_res.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Submission {submission_id} not found."},
        )

    if principal.institution_id and principal.institution_id != submission.institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access denied."},
        )

    submission.status = SubmissionStatus.VALIDATING.value
    await db.flush()

    # Get active rule bundle
    bundle_res = await db.execute(select(RuleBundle).where(RuleBundle.is_active == True))  # noqa: E712
    rule_bundle = bundle_res.scalars().first()
    if not rule_bundle:
        import hashlib
        yaml_content = "name: AICTE Demo Rules\nrules:\n  - VR-001\n  - VR-002\n  - VR-003\n  - VR-004\n  - VR-005\n  - VR-006\n  - VR-007\n  - VR-008\n  - VR-009\n  - VR-010\n  - VR-011\n  - VR-012\n  - VR-013\n  - VR-014\n"
        rule_bundle = RuleBundle(
            bundle_code="AICTE-DEMO-RULES-2024-V1",
            display_name="AICTE Demo Ingestion & Assurance Rules 2024-25",
            version="1.0.0",
            authority_status="DEMO_ONLY",
            rules_yaml_hash=hashlib.sha256(yaml_content.encode()).hexdigest(),
            rules_yaml_content=yaml_content,
            source_references_json=["AICTE Approval Process Handbook 2024-27 (Synthetic demo baseline)"],
            is_active=True,
        )
        db.add(rule_bundle)
        await db.flush()
    bundle_id = rule_bundle.id

    # Get staged rows
    rows_res = await db.execute(
        select(StagedRow)
        .where(StagedRow.submission_id == submission_id)
        .order_by(StagedRow.row_number)
    )
    staged_rows = rows_res.scalars().all()

    # Extract non-rejected rows with APAAR for mock provider check
    apaar_values = [
        str(r.normalized_data_json.get("apaar_id", ""))
        for r in staged_rows
        if r.normalized_data_json and not r.is_rejected
    ]

    mock_provider = get_mock_provider()
    bulk_results = await mock_provider.bulk_check(apaar_values)
    provider_outcomes = {apaar: res.outcome.value for apaar, res in bulk_results.items()}

    # Evaluate per-row rules
    row_dicts = [
        {**r.normalized_data_json, "row_number": r.row_number, "_staged_id": r.id}
        for r in staged_rows
        if r.normalized_data_json and not r.is_rejected
    ]

    findings = evaluate_submission_rows(row_dicts, provider_outcomes)

    # Check capacity rules against intake approval
    appr_res = await db.execute(
        select(IntakeApproval).where(
            IntakeApproval.programme_offering_id == submission.programme_offering_id,
            IntakeApproval.academic_year == submission.admission_cohort,
        )
    )
    approval = appr_res.scalars().first()

    ordinary_count = sum(1 for r in row_dicts if not r.get("is_nri") and not r.get("is_oci") and not r.get("is_fn") and r.get("category") != "SUPERNUMERARY")
    supernumerary_count = sum(1 for r in row_dicts if r.get("category") == "SUPERNUMERARY" or r.get("is_fn"))
    nri_count = sum(1 for r in row_dicts if r.get("is_nri"))

    if approval:
        cap_findings = rule_capacity_check(
            ordinary_count=ordinary_count,
            approved_ordinary=approval.approved_ordinary,
            supernumerary_count=supernumerary_count,
            approved_supernumerary=approval.approved_supernumerary,
            nri_count=nri_count,
            approved_nri=approval.approved_nri or 0,
            authority_status=approval.authority_status,
        )
        findings.extend(cap_findings)

    # Count blocking findings
    blocking_count = sum(1 for f in findings if f.is_blocking)

    # Record ValidationRun
    vrun = ValidationRun(
        submission_id=submission.id,
        rule_bundle_id=bundle_id,
        intake_approval_id=approval.id if approval else None,
        input_hash=submission.file_hash,
        evaluator_code_revision="git-main-rev1",
        fixture_version="v1",
        evaluated_at=datetime.now(UTC),
        status="COMPLETED",
        total_findings=len(findings),
        blocking_findings=blocking_count,
    )
    db.add(vrun)
    await db.flush()

    # Save findings
    row_id_map = {r.row_number: r.id for r in staged_rows}
    for f in findings:
        staged_id = row_id_map.get(f.row_number) if f.row_number else None
        vfinding = ValidationFinding(
            validation_run_id=vrun.id,
            staged_row_id=staged_id,
            rule_id=f.rule_id,
            rule_version=f.rule_version,
            outcome=f.outcome.value,
            observed_value=f.observed_value,
            expected_condition=f.expected_condition,
            confidence=f.confidence,
            remediation=f.remediation,
            is_blocking=f.is_blocking,
        )
        db.add(vfinding)

    # Update submission status
    if blocking_count > 0:
        submission.status = SubmissionStatus.ACTION_REQUIRED.value
    else:
        submission.status = SubmissionStatus.READY_FOR_CERTIFICATION.value

    await db.commit()
    await db.refresh(vrun)

    return ValidationRunOut(
        id=vrun.id,
        submission_id=vrun.submission_id,
        status=vrun.status,
        total_findings=vrun.total_findings,
        blocking_findings=vrun.blocking_findings,
        evaluated_at=vrun.evaluated_at.isoformat(),
        evaluator_code_revision=vrun.evaluator_code_revision,
    )


@api_router.get("/runs/{run_id}/findings", response_model=list[FindingOut], summary="List findings of a validation run")
async def list_findings(
    run_id: UUID,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
    blocking_only: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> list[FindingOut]:
    """Retrieve validation findings with optional filter on blocking status."""
    query = (
        select(ValidationFinding)
        .where(ValidationFinding.validation_run_id == run_id)
    )
    if blocking_only:
        query = query.where(ValidationFinding.is_blocking == True)  # noqa: E712

    query = query.order_by(ValidationFinding.created_at).offset(offset).limit(min(limit, 100))
    findings = (await db.execute(query)).scalars().all()

    return [
        FindingOut(
            id=f.id,
            rule_id=f.rule_id,
            rule_version=f.rule_version,
            outcome=f.outcome,
            observed_value=f.observed_value,
            expected_condition=f.expected_condition,
            confidence=f.confidence,
            remediation=f.remediation,
            is_blocking=f.is_blocking,
            staged_row_id=f.staged_row_id,
        )
        for f in findings
    ]


@api_router.post("/submissions/{submission_id}/certify", response_model=CertificationOut, summary="Certify enrolment submission (maker/checker)")
async def certify_submission(
    submission_id: UUID,
    principal: Certifier,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> CertificationOut:
    """Atomic certification of an enrolment submission.

    Enforces Maker/Checker separation: the checker (current principal)
    cannot be the same person/subject who created the submission.
    """
    institution_id = principal.require_institution()

    sub_res = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = sub_res.scalar_one_or_none()
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error_code": "NOT_FOUND", "message": f"Submission {submission_id} not found."},
        )

    # Cross-tenant check
    if submission.institution_id != institution_id and not principal.is_regulator():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error_code": "CROSS_TENANT_DENIED", "message": "Access denied."},
        )

    # MAKER / CHECKER SEPARATION: maker cannot certify their own submission
    if submission.created_by == principal.subject_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": "SELF_APPROVAL_DENIED",
                "message": (
                    "Maker/checker separation violation: a preparer cannot certify "
                    "their own submission. A separate authorized certifier is required."
                ),
                "details": {"subject": principal.subject_id},
            },
        )

    # Status check
    if submission.status != SubmissionStatus.READY_FOR_CERTIFICATION.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "CERTIFICATION_BLOCKED",
                "message": f"Submission is in status {submission.status}, but must be READY_FOR_CERTIFICATION.",
            },
        )

    # Lock scope lock row
    lock_res = await db.execute(
        select(SubmissionScopeLock).where(
            SubmissionScopeLock.id == submission.scope_lock_id
        ).with_for_update()
    )
    scope_lock = lock_res.scalar_one_or_none()
    if not scope_lock:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error_code": "SCOPE_LOCK_NOT_FOUND", "message": "Scope lock missing."},
        )

    now = datetime.now(UTC)
    scope_lock.reported_version += 1
    scope_lock.certified_version += 1
    scope_lock.last_reported_at = now
    scope_lock.last_certified_at = now

    submission.status = SubmissionStatus.CERTIFIED.value

    # Recount rows
    rows_res = await db.execute(
        select(StagedRow).where(StagedRow.submission_id == submission.id, StagedRow.is_rejected == False)  # noqa: E712
    )
    rows = rows_res.scalars().all()
    ord_c = sum(1 for r in rows if r.normalized_data_json and not r.normalized_data_json.get("is_nri") and not r.normalized_data_json.get("is_fn") and r.normalized_data_json.get("category") != "SUPERNUMERARY")
    sn_c = sum(1 for r in rows if r.normalized_data_json and (r.normalized_data_json.get("category") == "SUPERNUMERARY" or r.normalized_data_json.get("is_fn")))
    nri_c = sum(1 for r in rows if r.normalized_data_json and r.normalized_data_json.get("is_nri"))

    # Audit event
    audit = AuditEvent(
        event_type="CERTIFICATION_ISSUED",
        principal=principal.subject_id,
        institution_id=institution_id,
        object_type="submission",
        object_id=submission.id,
        object_version=scope_lock.certified_version,
        action="CERTIFY",
        outcome="SUCCESS",
        purpose="Enrolment Quality Certification",
        timestamp=now,
        request_id=principal.request_id,
    )
    db.add(audit)

    # Persist certified EnrolmentEpisodes
    from apaar.review.service import record_certified_enrolment_episodes
    await record_certified_enrolment_episodes(db, submission, rows, principal)

    await db.commit()

    return CertificationOut(
        submission_id=submission.id,
        status=submission.status,
        certified_by=principal.subject_id,
        certified_at=now.isoformat(),
        reported_version=scope_lock.reported_version,
        certified_version=scope_lock.certified_version,
        ordinary_count=ord_c,
        supernumerary_count=sn_c,
        nri_count=nri_c,
    )
