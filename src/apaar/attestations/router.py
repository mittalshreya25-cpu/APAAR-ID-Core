"""API router for signed attestations, verifications, and verifiable certificates."""
from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apaar.access.auth import get_current_principal
from apaar.attestations.models import Attestation, SigningKey
from apaar.config import get_settings
from apaar.database import get_async_session
from apaar.institutions.models import Institution
from apaar.shared.context import TenantContext
from apaar.shared.types import AttestationStatus, KeyStatus

api_router = APIRouter(tags=["attestations"])


class AttestationIssueRequest(BaseModel):
    record_type: str = "ENROLMENT_ATTESTATION"
    episode_id: UUID | None = None
    submission_id: UUID | None = None
    purpose: str = "EMPLOYMENT_VERIFICATION"
    expires_in_days: int = 90


class AttestationOut(BaseModel):
    id: UUID
    record_type: str
    issuer_key_id: UUID
    subject_ref: str
    purpose: str
    payload_hash: str
    signed_bytes: str
    status: str
    issued_at: str
    expires_at: str | None


class VerificationRequestIn(BaseModel):
    signed_bytes: str


class VerificationResultOut(BaseModel):
    is_valid: bool
    structure_valid: bool
    signature_valid: bool
    issuer_trusted: bool
    time_valid: bool
    status: str
    claims: dict | None
    provenance: str = "SYNTHETIC_MOCK_PROVENANCE"


class CertificateOut(BaseModel):
    certificate_id: UUID
    apaar_id: str
    local_student_id: str
    institution_name: str
    programme_name: str
    admission_cohort: str
    enrolment_status: str
    qr_reference: str
    synthetic: bool = True
    disclaimer: str = (
        "SYNTHETIC CERTIFICATE SAMPLE — for demonstration only. "
        "Contains mock APAAR ID and local student ID. "
        "Does not represent an official degree award or national credential."
    )


async def _get_or_create_system_key(db: AsyncSession) -> SigningKey:
    """Retrieve or create an active system signing key."""
    res = await db.execute(select(SigningKey).where(SigningKey.key_status == KeyStatus.ACTIVE.value))
    key = res.scalars().first()
    if not key:
        now = datetime.now(UTC)
        key = SigningKey(
            key_alias="apaar-core-demo-key-1",
            algorithm="HS256",
            public_key_pem="DEMO_SECRET_KEY_MOCK_PEM",
            key_status=KeyStatus.ACTIVE.value,
            activated_at=now,
        )
        db.add(key)
        await db.flush()
    return key


@api_router.post("/issue", response_model=AttestationOut, summary="Issue a signed attestation token")
async def issue_attestation(
    body: AttestationIssueRequest,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> AttestationOut:
    """Issue an application-specific signed JWS enrolment statement."""
    settings = get_settings()
    signing_key = await _get_or_create_system_key(db)

    now = datetime.now(UTC)
    expires_at = now + timedelta(days=body.expires_in_days)
    subject_ref = f"urn:apaar:subject:{uuid4().hex[:16]}"

    payload = {
        "iss": "apaar-core-platform",
        "sub": subject_ref,
        "aud": "apaar-verifiers",
        "record_type": body.record_type,
        "purpose": body.purpose,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
        "synthetic": True,
        "episode_id": str(body.episode_id) if body.episode_id else None,
        "submission_id": str(body.submission_id) if body.submission_id else None,
    }

    signed_bytes = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    attestation = Attestation(
        record_type=body.record_type,
        issuer_key_id=signing_key.id,
        submission_id=body.submission_id,
        episode_id=body.episode_id,
        subject_ref=subject_ref,
        purpose=body.purpose,
        payload_hash=payload_hash,
        signed_bytes=signed_bytes,
        status=AttestationStatus.ACTIVE.value,
        issued_at=now,
        expires_at=expires_at,
    )
    db.add(attestation)
    await db.commit()
    await db.refresh(attestation)

    return AttestationOut(
        id=attestation.id,
        record_type=attestation.record_type,
        issuer_key_id=attestation.issuer_key_id,
        subject_ref=attestation.subject_ref,
        purpose=attestation.purpose,
        payload_hash=attestation.payload_hash,
        signed_bytes=attestation.signed_bytes,
        status=attestation.status,
        issued_at=attestation.issued_at.isoformat(),
        expires_at=attestation.expires_at.isoformat() if attestation.expires_at else None,
    )


@api_router.post("/verify", response_model=VerificationResultOut, summary="Verify a signed attestation token")
async def verify_attestation(
    body: VerificationRequestIn,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> VerificationResultOut:
    """Separately verify structure, signature, issuer trust, time validity, and status.

    Even if all checks pass, verification confirms only that the configured issuer
    made the statement under demo policy. It does NOT prove government issuance.
    """
    settings = get_settings()
    structure_valid = False
    signature_valid = False
    issuer_trusted = False
    time_valid = False
    claims = None
    record_status = "UNKNOWN"

    try:
        # Decode header and unverified claims
        unverified_claims = jwt.get_unverified_claims(body.signed_bytes)
        structure_valid = True
    except Exception:
        return VerificationResultOut(
            is_valid=False,
            structure_valid=False,
            signature_valid=False,
            issuer_trusted=False,
            time_valid=False,
            status="MALFORMED_STRUCTURE",
            claims=None,
        )

    try:
        claims = jwt.decode(
            body.signed_bytes,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience="apaar-verifiers",
        )
        signature_valid = True
        issuer_trusted = claims.get("iss") == "apaar-core-platform"
        time_valid = True
    except jwt.ExpiredSignatureError:
        signature_valid = True
        time_valid = False
        claims = unverified_claims
    except Exception:
        claims = unverified_claims

    # Check status in database if attestation exists
    payload_hash = hashlib.sha256(json.dumps(unverified_claims, sort_keys=True).encode()).hexdigest()
    att_res = await db.execute(select(Attestation).where(Attestation.signed_bytes == body.signed_bytes))
    att = att_res.scalar_one_or_none()
    if att:
        record_status = att.status
    else:
        record_status = "ACTIVE" if signature_valid and time_valid else "INDETERMINATE"

    is_overall_valid = structure_valid and signature_valid and issuer_trusted and time_valid and (record_status == "ACTIVE")

    return VerificationResultOut(
        is_valid=is_overall_valid,
        structure_valid=structure_valid,
        signature_valid=signature_valid,
        issuer_trusted=issuer_trusted,
        time_valid=time_valid,
        status=record_status,
        claims=claims,
    )


@api_router.get("/certificates/{id}", response_model=CertificateOut, summary="Get certificate record with APAAR and local ID")
async def get_certificate_record(
    id: UUID,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> CertificateOut:
    """Return an authorized certificate sample with APAAR ID and local student ID.

    The QR code reference is an opaque link to verification, NOT a plaintext student file.
    """
    # Look up institution or episode
    inst_res = await db.execute(select(Institution).limit(1))
    inst = inst_res.scalars().first()
    inst_name = inst.name if inst else "Demo Engineering College (Synthetic)"

    return CertificateOut(
        certificate_id=id,
        apaar_id="123456789012",  # Synthetic 12-digit format
        local_student_id="DEMO-2024-0001",
        institution_name=inst_name,
        programme_name="B.Tech Computer Science (Synthetic)",
        admission_cohort="2024-25",
        enrolment_status="ACTIVE",
        qr_reference=f"/api/v1/attestations/certificates/{id}",
        synthetic=True,
    )
