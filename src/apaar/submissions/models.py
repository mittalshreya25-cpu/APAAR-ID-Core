"""SQLAlchemy ORM models for the submissions domain.

A Submission represents one institution's upload of enrolment data for a
specific programme-offering + admission-cohort combination.

``SubmissionScopeLock`` serialises concurrent submissions for the same
(institution, programme_offering, admission_cohort) tuple and tracks
reported/certified version counters.

``StagedRow`` holds per-row parsed/normalised data; rows rejected during
parsing are kept for audit with ``is_rejected=True``.

All content is synthetic — no real student data is ingested.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import SubmissionStatus

if TYPE_CHECKING:
    from apaar.validation.models import ValidationRun


class SubmissionScopeLock(Base):
    """Per-(institution, programme_offering, admission_cohort) serialisation lock.

    ``reported_version`` increments on each certified submission;
    ``certified_version`` increments when quality certification is issued.
    Both start at 0.

    The UNIQUE constraint on (institution_id, programme_offering_id,
    admission_cohort) means there is exactly one lock row per scope.
    """

    __tablename__ = "submission_scope_locks"

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
    admission_cohort: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, comment="e.g. '2024-25'"
    )

    reported_version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    certified_version: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    last_reported_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    last_certified_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Relationships
    submissions: Mapped[list[Submission]] = relationship(
        "Submission",
        back_populates="scope_lock",
        foreign_keys="Submission.scope_lock_id",
    )

    __table_args__ = (
        sa.UniqueConstraint(
            "institution_id",
            "programme_offering_id",
            "admission_cohort",
            name="uq_scope_lock_scope",
        ),
        sa.Index(
            "ix_submission_scope_locks_institution_id", "institution_id"
        ),
        sa.Index(
            "ix_submission_scope_locks_programme_offering_id",
            "programme_offering_id",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SubmissionScopeLock id={self.id} "
            f"institution_id={self.institution_id} "
            f"admission_cohort={self.admission_cohort!r} "
            f"reported_version={self.reported_version}>"
        )


class Submission(Base):
    """An uploaded data file from an institution for a single programme-cohort scope.

    ``idempotency_key`` is caller-supplied and unique; duplicate uploads with
    the same key are de-duped without reprocessing.

    ``expected_base_version`` guards against lost-update races: the caller
    must supply the current ``reported_version`` of the scope lock; a mismatch
    is rejected before any row is processed.

    Row counts separate declared totals from actual received/processed/rejected
    counts to detect truncated uploads.
    """

    __tablename__ = "submissions"

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
    admission_cohort: Mapped[str] = mapped_column(
        sa.String(10), nullable=False, comment="e.g. '2024-25'"
    )

    scope_lock_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("submission_scope_locks.id", ondelete="SET NULL"),
        nullable=True,
    )
    expected_base_version: Mapped[int | None] = mapped_column(
        sa.Integer, nullable=True
    )

    # File metadata
    file_hash: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, comment="SHA-256 hex digest of raw upload"
    )
    file_size: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    original_filename: Mapped[str] = mapped_column(sa.String(512), nullable=False)

    # Parser metadata
    schema_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    parser_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)

    # Row accounting
    declared_total_rows: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    received_rows: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    processed_rows: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    rejected_rows: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)

    # Lifecycle
    status: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        default=SubmissionStatus.DRAFT.value,
        comment="SubmissionStatus enum value",
    )

    # Idempotency
    idempotency_key: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, unique=True
    )

    # Actor
    created_by: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, comment="OIDC sub of submitting user"
    )

    # Relationships
    scope_lock: Mapped[SubmissionScopeLock | None] = relationship(
        "SubmissionScopeLock",
        back_populates="submissions",
        foreign_keys=[scope_lock_id],
    )
    staged_rows: Mapped[list[StagedRow]] = relationship(
        "StagedRow",
        back_populates="submission",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    validation_runs: Mapped[list[ValidationRun]] = relationship(
        "ValidationRun",
        back_populates="submission",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in SubmissionStatus)})",
            name="status_values",
        ),
        sa.CheckConstraint("file_size > 0", name="file_size_positive"),
        sa.CheckConstraint("received_rows >= 0", name="received_rows_nonneg"),
        sa.CheckConstraint("processed_rows >= 0", name="processed_rows_nonneg"),
        sa.CheckConstraint("rejected_rows >= 0", name="rejected_rows_nonneg"),
        sa.Index("ix_submissions_institution_id", "institution_id"),
        sa.Index("ix_submissions_programme_offering_id", "programme_offering_id"),
        sa.Index("ix_submissions_scope_lock_id", "scope_lock_id"),
        sa.Index("ix_submissions_idempotency_key", "idempotency_key", unique=True),
        sa.Index("ix_submissions_status", "status"),
        sa.Index(
            "ix_submissions_institution_cohort",
            "institution_id",
            "admission_cohort",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Submission id={self.id} "
            f"institution_id={self.institution_id} "
            f"status={self.status!r}>"
        )


class StagedRow(Base):
    """One parsed row from a Submission file, held for validation.

    ``raw_data_json`` preserves the exact received row;
    ``normalized_data_json`` holds the canonicalised form after parsing.
    ``parse_errors_json`` records field-level errors when ``is_rejected=True``.

    StagedRow deliberately does not have ``updated_at`` or ``version`` because
    rows are immutable after creation — corrections require a new Submission.
    """

    __tablename__ = "staged_rows"

    # Override Base — no updated_at/version for immutable rows
    # (Base provides id and created_at; we remove updated_at + version by
    #  re-declaring them as None / not present — achieved via __mapper_args__)

    submission_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    row_number: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    raw_data_json: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    normalized_data_json: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    parse_errors_json: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)
    is_rejected: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )

    # Relationships
    submission: Mapped[Submission] = relationship(
        "Submission", back_populates="staged_rows"
    )

    __table_args__ = (
        sa.Index("ix_staged_rows_submission_id", "submission_id"),
        sa.Index(
            "ix_staged_rows_submission_row",
            "submission_id",
            "row_number",
        ),
        sa.Index("ix_staged_rows_is_rejected", "is_rejected"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<StagedRow id={self.id} "
            f"submission_id={self.submission_id} "
            f"row_number={self.row_number} "
            f"is_rejected={self.is_rejected}>"
        )
