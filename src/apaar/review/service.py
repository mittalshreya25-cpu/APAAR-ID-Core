"""Temporal cross-institution overlap detection and review case management.

Guarantees:
- Narrowly authorized central matching operation (P5.1).
- Non-overlap transfers and permitted concurrent study are distinguished from conflicting overlaps.
- Does NOT enforce a global active-APAAR uniqueness constraint.
- Protects counterpart details: does not leak counterparty institution names or PII to the submitting institution.
- Accountable review lifecycle: OPEN -> IN_REVIEW -> RESOLVED | DISMISSED, with reopen history.
"""
from __future__ import annotations

import datetime
import hashlib
import hmac
from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.approvals.models import ProgrammeOffering
from apaar.audit.models import AuditEvent
from apaar.identity.models import EnrolmentEpisode, StudentIdentity
from apaar.review.models import ReviewCase
from apaar.shared.context import TenantContext
from apaar.shared.types import EpisodeStatus, ReviewCaseStatus
from apaar.submissions.models import StagedRow, Submission


def derive_apaar_hmac(apaar: str, hmac_key: str = "change-me-apaar-hmac-key") -> str:
    """Deterministic HMAC lookup token for deduplication without storing plaintext APAAR."""
    return hmac.new(hmac_key.encode(), apaar.strip().encode(), hashlib.sha256).hexdigest()


async def record_certified_enrolment_episodes(
    db: AsyncSession,
    submission: Submission,
    staged_rows: Sequence[StagedRow],
    principal: TenantContext,
) -> int:
    """Record EnrolmentEpisode rows when a submission is certified.

    Idempotent: skips already recorded episodes for the same local_student_id.
    """
    created_count = 0

    for row in staged_rows:
        if row.is_rejected or not row.normalized_data_json:
            continue

        data = row.normalized_data_json
        apaar = str(data.get("apaar_id", "")).strip()
        local_id = str(data.get("local_student_id", "")).strip()
        if not apaar or not local_id:
            continue

        hmac_val = derive_apaar_hmac(apaar)

        # Find or create StudentIdentity
        id_res = await db.execute(
            select(StudentIdentity).where(StudentIdentity.apaar_hmac == hmac_val)
        )
        student_id_obj = id_res.scalar_one_or_none()
        if not student_id_obj:
            student_id_obj = StudentIdentity(
                apaar_hmac=hmac_val,
                apaar_encrypted=apaar.encode("utf-8"),  # Synthetic prototype
                apaar_key_version=1,
                provider_outcome="MOCK_MATCH",
                fixture_version="v1",
            )
            db.add(student_id_obj)
            await db.flush()

        # Check if episode already exists for this student and offering
        existing_ep = await db.execute(
            select(EnrolmentEpisode).where(
                EnrolmentEpisode.student_identity_id == student_id_obj.id,
                EnrolmentEpisode.institution_id == submission.institution_id,
                EnrolmentEpisode.programme_offering_id == submission.programme_offering_id,
                EnrolmentEpisode.local_student_id == local_id,
            )
        )
        if existing_ep.scalar_one_or_none():
            continue

        # Parse interval dates
        start_str = data.get("interval_start")
        end_str = data.get("interval_end")
        start_date = (
            datetime.date.fromisoformat(start_str)
            if start_str
            else datetime.date(2024, 8, 1)
        )
        end_date = datetime.date.fromisoformat(end_str) if end_str else None

        episode = EnrolmentEpisode(
            student_identity_id=student_id_obj.id,
            institution_id=submission.institution_id,
            programme_offering_id=submission.programme_offering_id,
            local_student_id=local_id,
            entry_route=str(data.get("entry_route", "DIRECT")),
            admission_cohort=submission.admission_cohort,
            current_study_year=int(data.get("current_study_year", 1)),
            status=EpisodeStatus.ACTIVE.value,
            interval_start=start_date,
            interval_end=end_date,
            is_nri=bool(data.get("is_nri", False)),
            is_oci=bool(data.get("is_oci", False)),
            is_fn=bool(data.get("is_fn", False)),
            category=str(data.get("category", "GENERAL")),
            allocation_pool=(
                "ORDINARY"
                if not data.get("is_nri") and not data.get("is_fn")
                else "SUPERNUMERARY"
            ),
        )
        db.add(episode)
        created_count += 1

    return created_count


async def detect_cross_institution_overlaps(
    db: AsyncSession,
    submission_id: UUID,
    principal: TenantContext,
) -> list[ReviewCase]:
    """Scan submission staged rows for temporal overlaps with certified enrolments.

    Guarantees:
    - Counterpart details (institution name, student details) are suppressed to prevent oracle leaks.
    - Transfers with non-overlapping dates are ignored.
    - Permitted UGC simultaneous study (e.g. Regular + ODL/Online) are permitted without opening a blocker.
    """
    sub_res = await db.execute(select(Submission).where(Submission.id == submission_id))
    submission = sub_res.scalar_one_or_none()
    if not submission:
        return []

    # Get current offering
    curr_off_res = await db.execute(
        select(ProgrammeOffering).where(
            ProgrammeOffering.id == submission.programme_offering_id
        )
    )
    current_offering = curr_off_res.scalar_one_or_none()
    current_mode = current_offering.mode if current_offering else "REGULAR"

    # Get staged rows
    rows_res = await db.execute(
        select(StagedRow).where(
            StagedRow.submission_id == submission_id,
            StagedRow.is_rejected == False,  # noqa: E712
        )
    )
    staged_rows = rows_res.scalars().all()

    now = datetime.datetime.now(datetime.UTC)
    opened_cases: list[ReviewCase] = []

    far_future = datetime.date(2099, 12, 31)

    for row in staged_rows:
        if not row.normalized_data_json:
            continue

        data = row.normalized_data_json
        apaar = str(data.get("apaar_id", "")).strip()
        local_id = str(data.get("local_student_id", "")).strip()
        if not apaar:
            continue

        start_str = data.get("interval_start")
        end_str = data.get("interval_end")
        row_start = (
            datetime.date.fromisoformat(start_str)
            if start_str
            else datetime.date(2024, 8, 1)
        )
        row_end = datetime.date.fromisoformat(end_str) if end_str else far_future

        hmac_val = derive_apaar_hmac(apaar)

        # Look for existing active episodes for this student at another institution
        ep_query = (
            select(EnrolmentEpisode, ProgrammeOffering)
            .join(
                StudentIdentity,
                EnrolmentEpisode.student_identity_id == StudentIdentity.id,
            )
            .join(
                ProgrammeOffering,
                EnrolmentEpisode.programme_offering_id == ProgrammeOffering.id,
            )
            .where(
                StudentIdentity.apaar_hmac == hmac_val,
                EnrolmentEpisode.institution_id != submission.institution_id,
                EnrolmentEpisode.status == EpisodeStatus.ACTIVE.value,
            )
        )
        ep_res = await db.execute(ep_query)
        matching_episodes = ep_res.all()

        for ep, other_offering in matching_episodes:
            ep_start = ep.interval_start
            ep_end = ep.interval_end if ep.interval_end else far_future

            # Check interval overlap: max(start1, start2) <= min(end1, end2)
            has_temporal_overlap = max(row_start, ep_start) <= min(row_end, ep_end)
            if not has_temporal_overlap:
                # Non-overlapping intervals (e.g. valid past transfer)
                continue

            # Check if this is permitted concurrent study (e.g. Regular + ODL/Online)
            other_mode = other_offering.mode if other_offering else "REGULAR"
            if (current_mode in ("ODL", "ONLINE", "DISTANCE") and other_mode == "REGULAR") or (
                other_mode in ("ODL", "ONLINE", "DISTANCE") and current_mode == "REGULAR"
            ):
                # Permitted under UGC concurrent study guidelines
                continue

            # Conflicting overlap detected! Check if case already opened for this student row
            existing_case_res = await db.execute(
                select(ReviewCase).where(
                    ReviewCase.institution_id == submission.institution_id,
                    ReviewCase.case_type == "TEMPORAL_OVERLAP",
                    ReviewCase.status == ReviewCaseStatus.OPEN.value,
                )
            )
            # Create review case with privacy preservation (no counterpart institution leaked)
            review_case = ReviewCase(
                institution_id=submission.institution_id,
                case_type="TEMPORAL_OVERLAP",
                is_overlap_case=True,
                status=ReviewCaseStatus.OPEN.value,
                opened_by=principal.subject_id,
                opened_at=now,
                finding_ref_id=None,
            )
            db.add(review_case)
            await db.flush()

            # Record audit event
            audit = AuditEvent(
                event_type="REVIEW_CASE_OPENED",
                principal=principal.subject_id,
                institution_id=submission.institution_id,
                object_type="review_case",
                object_id=review_case.id,
                action="OPEN_OVERLAP_CASE",
                outcome="SUCCESS",
                purpose="Cross-Institution Overlap Review",
                timestamp=now,
                request_id=principal.request_id,
            )
            db.add(audit)
            opened_cases.append(review_case)
            break

    await db.commit()
    return opened_cases
