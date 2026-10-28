"""SQLAlchemy ORM models for the reporting domain.

ReportSnapshot stores a point-in-time computed view of enrolment / validation
data.  Snapshots are immutable once generated; a new snapshot supersedes older
ones for the same scope.

DisclosureGrant authorises a specific recipient to view a specific snapshot's
fields.  A grant is the *only* path to data disclosure — no other mechanism
should bypass this check.

VerificationRequest is the request lifecycle prior to grant creation; a grant
is only created when the request is APPROVED.

IMPORTANT — security contract:
  * A DisclosureGrant MUST be present and non-revoked, and the snapshot must
    not be suppressed, before any field is disclosed to a recipient.
  * A printed snapshot ID, QR code or UUID alone does NOT authorise disclosure.
  * Recipient fields contain OIDC subjects only — no raw APAAR or PII.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import ReportAudience, VerificationRequestStatus

if TYPE_CHECKING:
    pass


class ReportSnapshot(Base):
    """An immutable point-in-time snapshot of computed reporting data.

    ``institution_id`` is NULL for regulator-scope (cross-institution) reports.
    ``snapshot_data_json`` holds the pre-computed fields; field suppression
    based on ``audience`` is applied at read time by the API layer.

    ``is_suppressed`` can be set by a maintainer if a snapshot is later found
    to contain an error; suppressed snapshots are not served to external callers.
    """

    __tablename__ = "report_snapshots"

    institution_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for regulator-scope cross-institution reports",
    )
    report_type: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="e.g. 'ENROLMENT_SUMMARY', 'INTAKE_UTILISATION'",
    )
    generated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    as_of: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        comment="Data timestamp that the snapshot reflects",
    )
    snapshot_data_json: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    rule_bundle_version: Mapped[str | None] = mapped_column(
        sa.String(32), nullable=True
    )
    approval_version_ref: Mapped[str | None] = mapped_column(
        sa.String(64), nullable=True
    )
    freshness_seconds: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    filters_json: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)
    is_suppressed: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    audience: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=ReportAudience.INSTITUTION.value,
        comment="ReportAudience enum value",
    )

    # Relationships
    disclosure_grants: Mapped[list[DisclosureGrant]] = relationship(
        "DisclosureGrant",
        back_populates="snapshot",
        foreign_keys="DisclosureGrant.snapshot_id",
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"audience IN ({', '.join(repr(a.value) for a in ReportAudience)})",
            name="audience_values",
        ),
        sa.Index("ix_report_snapshots_institution_id", "institution_id"),
        sa.Index("ix_report_snapshots_report_type", "report_type"),
        sa.Index("ix_report_snapshots_generated_at", "generated_at"),
        sa.Index("ix_report_snapshots_is_suppressed", "is_suppressed"),
        sa.Index(
            "ix_report_snapshots_institution_type",
            "institution_id",
            "report_type",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ReportSnapshot id={self.id} "
            f"report_type={self.report_type!r} "
            f"audience={self.audience!r}>"
        )


class VerificationRequest(Base):
    """A third-party request to verify an enrolment episode.

    The request captures what fields were requested and who made the request.
    An APPROVED request results in a DisclosureGrant being created.

    ``requester_subject`` and ``decided_by`` are OIDC subjects — opaque
    identifiers, not personal data fields.
    """

    __tablename__ = "verification_requests"

    requester_subject: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, comment="OIDC sub of requesting party"
    )
    requester_org: Mapped[str | None] = mapped_column(
        sa.String(255), nullable=True
    )
    purpose: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    episode_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("enrolment_episodes.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_fields_json: Mapped[list] = mapped_column(
        sa.JSON, nullable=False, default=list
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=VerificationRequestStatus.PENDING.value,
        comment="VerificationRequestStatus enum value",
    )
    decided_by: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    decided_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    decision_reason: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    # Relationships
    disclosure_grants: Mapped[list[DisclosureGrant]] = relationship(
        "DisclosureGrant",
        back_populates="verification_request",
        foreign_keys="DisclosureGrant.verification_request_id",
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in VerificationRequestStatus)})",
            name="status_values",
        ),
        sa.Index(
            "ix_verification_requests_requester_subject", "requester_subject"
        ),
        sa.Index("ix_verification_requests_episode_id", "episode_id"),
        sa.Index("ix_verification_requests_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<VerificationRequest id={self.id} "
            f"requester_subject={self.requester_subject!r} "
            f"status={self.status!r}>"
        )


class DisclosureGrant(Base):
    """Authorises a specific recipient to view specific fields of a snapshot.

    A grant must be present and non-revoked before any data is disclosed.
    ``allowed_fields_json`` is an explicit allowlist — not a wildcard.

    ``verification_request_id`` links back to the approved VerificationRequest
    that resulted in this grant.

    ``expires_at`` is mandatory; grants do not persist indefinitely.
    """

    __tablename__ = "disclosure_grants"

    verification_request_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("verification_requests.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requester_subject: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, comment="OIDC sub of requesting party"
    )
    recipient_subject: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="OIDC sub of the authorised recipient",
    )
    purpose: Mapped[str] = mapped_column(sa.String(512), nullable=False)
    allowed_fields_json: Mapped[list] = mapped_column(
        sa.JSON,
        nullable=False,
        comment="Explicit allowlist of field names — not a wildcard",
    )
    snapshot_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("report_snapshots.id", ondelete="RESTRICT"),
        nullable=False,
    )
    expires_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    is_revoked: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(
        sa.String(512), nullable=True
    )

    # Relationships
    verification_request: Mapped[VerificationRequest] = relationship(
        "VerificationRequest",
        back_populates="disclosure_grants",
        foreign_keys=[verification_request_id],
    )
    snapshot: Mapped[ReportSnapshot] = relationship(
        "ReportSnapshot",
        back_populates="disclosure_grants",
        foreign_keys=[snapshot_id],
    )

    __table_args__ = (
        sa.Index(
            "ix_disclosure_grants_verification_request_id",
            "verification_request_id",
        ),
        sa.Index("ix_disclosure_grants_recipient_subject", "recipient_subject"),
        sa.Index("ix_disclosure_grants_snapshot_id", "snapshot_id"),
        sa.Index("ix_disclosure_grants_is_revoked", "is_revoked"),
        sa.Index("ix_disclosure_grants_expires_at", "expires_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<DisclosureGrant id={self.id} "
            f"recipient_subject={self.recipient_subject!r} "
            f"is_revoked={self.is_revoked}>"
        )
