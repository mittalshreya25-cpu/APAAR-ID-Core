"""SQLAlchemy ORM models for the identity domain.

IMPORTANT — synthetic data contract:
  * ``apaar_encrypted`` stores an AES-GCM encrypted synthetic APAAR-shaped
    string (12 decimal digits).  No real APAAR or Aadhaar number is collected.
  * ``apaar_hmac`` is an HMAC-SHA256 of the synthetic APAAR token and is used
    only for deduplication lookups.
  * ``local_student_id`` is the institution's own opaque enrolment number —
    not a government identifier.

All fixture/synthetic records carry a ``fixture_version`` tag for provenance.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import (
    AllocationPool,
    EntryRoute,
    EpisodeStatus,
    ProviderOutcome,
    StudentCategory,
)

if TYPE_CHECKING:
    pass


class StudentIdentity(Base):
    """Internal identity record for a student whose synthetic APAAR has been verified.

    The APAAR value is stored encrypted; only an HMAC-derived token is held in
    plaintext for deduplication queries.  A ``provider_outcome`` of NOT_CHECKED
    means the mock registry has not yet been queried.

    This table intentionally holds no name, date-of-birth or other personal
    attributes — only the minimum needed for deduplication and audit.
    """

    __tablename__ = "student_identities"

    # APAAR storage — synthetic only
    apaar_hmac: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        unique=True,
        comment="HMAC-SHA256 of synthetic APAAR — used for deduplication lookups",
    )
    apaar_encrypted: Mapped[bytes] = mapped_column(
        sa.LargeBinary,
        nullable=False,
        comment="AES-GCM encrypted synthetic APAAR (12 demo digits)",
    )
    apaar_key_version: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=1,
        comment="Encryption key version to support key rotation",
    )

    # Mock provider outcome
    provider_outcome: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        default=ProviderOutcome.NOT_CHECKED.value,
        comment="ProviderOutcome enum — result of most recent mock registry check",
    )
    provider_checked_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Synthetic provenance
    fixture_version: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        default="v1",
        comment="Synthetic fixture version tag",
    )

    # Relationships
    enrolment_episodes: Mapped[list[EnrolmentEpisode]] = relationship(
        "EnrolmentEpisode",
        back_populates="student_identity",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"provider_outcome IN ({', '.join(repr(p.value) for p in ProviderOutcome)})",
            name="provider_outcome_values",
        ),
        sa.Index("ix_student_identities_apaar_hmac", "apaar_hmac", unique=True),
        sa.Index("ix_student_identities_provider_outcome", "provider_outcome"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<StudentIdentity id={self.id} "
            f"provider_outcome={self.provider_outcome!r}>"
        )


class EnrolmentEpisode(Base):
    """A single continuous enrolment of a student at an institution.

    One student may have multiple non-overlapping episodes (e.g. transfer,
    readmission).  An overlap across institutions is an anomaly signal
    requiring review — it does not automatically indicate fraud.

    ``allocation_pool`` records which approved intake pool this episode counts
    toward; UNRESOLVED means the pool has not yet been determined and review
    is required before certification.
    """

    __tablename__ = "enrolment_episodes"

    student_identity_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("student_identities.id", ondelete="RESTRICT"),
        nullable=False,
    )
    institution_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    programme_offering_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("programme_offerings.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # Institution-assigned ID — opaque, not a government identifier
    local_student_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)

    # Admission metadata
    entry_route: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=EntryRoute.DIRECT.value,
        comment="EntryRoute enum value",
    )
    admission_cohort: Mapped[str] = mapped_column(
        sa.String(10),
        nullable=False,
        comment="Academic year of admission e.g. '2024-25'",
    )
    current_study_year: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=1
    )

    # Lifecycle
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=EpisodeStatus.ACTIVE.value,
        comment="EpisodeStatus enum value",
    )
    interval_start: Mapped[datetime.date] = mapped_column(sa.Date, nullable=False)
    interval_end: Mapped[datetime.date | None] = mapped_column(sa.Date, nullable=True)

    # Special flags
    is_nri: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_oci: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)
    is_fn: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    category: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=StudentCategory.GENERAL.value,
        comment="StudentCategory enum value",
    )
    allocation_pool: Mapped[str | None] = mapped_column(
        sa.String(16),
        nullable=True,
        comment="AllocationPool enum value; NULL means not yet assigned",
    )

    # Relationships
    student_identity: Mapped[StudentIdentity] = relationship(
        "StudentIdentity", back_populates="enrolment_episodes"
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"entry_route IN ({', '.join(repr(r.value) for r in EntryRoute)})",
            name="entry_route_values",
        ),
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in EpisodeStatus)})",
            name="status_values",
        ),
        sa.CheckConstraint(
            f"category IN ({', '.join(repr(c.value) for c in StudentCategory)})",
            name="category_values",
        ),
        sa.CheckConstraint(
            f"allocation_pool IS NULL OR allocation_pool IN ({', '.join(repr(p.value) for p in AllocationPool)})",
            name="allocation_pool_values",
        ),
        sa.CheckConstraint(
            "interval_end IS NULL OR interval_end >= interval_start",
            name="interval_order",
        ),
        sa.CheckConstraint("current_study_year >= 1", name="study_year_positive"),
        sa.Index(
            "ix_enrolment_episodes_student_identity_id", "student_identity_id"
        ),
        sa.Index("ix_enrolment_episodes_institution_id", "institution_id"),
        sa.Index(
            "ix_enrolment_episodes_programme_offering_id", "programme_offering_id"
        ),
        sa.Index("ix_enrolment_episodes_admission_cohort", "admission_cohort"),
        sa.Index("ix_enrolment_episodes_status", "status"),
        sa.Index(
            "ix_enrolment_episodes_institution_cohort",
            "institution_id",
            "admission_cohort",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<EnrolmentEpisode id={self.id} "
            f"student_identity_id={self.student_identity_id} "
            f"institution_id={self.institution_id} "
            f"status={self.status!r}>"
        )
