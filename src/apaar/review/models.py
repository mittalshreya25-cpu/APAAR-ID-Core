"""SQLAlchemy ORM models for the review domain.

A ReviewCase is opened when a ValidationFinding or overlap signal requires
human judgement before certification can proceed.  Cases are never automatically
resolved — a ReviewDecision must be recorded by an authorised reviewer.

An overlap or anomaly is an explainable review signal; cases do not label a
student fraudulent or globally forbid concurrent programme enrolments.

ReviewDecisions are append-only.  A superseded decision is retained for audit.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import ReviewCaseStatus

if TYPE_CHECKING:
    pass


class ReviewCase(Base):
    """A case requiring human review before certification may proceed.

    ``finding_ref_id`` links to the ValidationFinding that triggered the case
    (if applicable).  For overlap cases ``is_overlap_case=True`` and the
    finding_ref_id may be NULL (the overlap is detected across submissions).

    Cases transition: OPEN → IN_REVIEW → RESOLVED | DISMISSED.
    A DISMISSED case may be REOPENED by creating a new ReviewDecision.
    """

    __tablename__ = "review_cases"

    institution_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    case_type: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="Domain-specific case type string e.g. 'OVERLAP', 'INTAKE_EXCESS'",
    )
    finding_ref_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        comment="UUID of a ValidationFinding that opened this case (no FK to allow cross-run refs)",
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=ReviewCaseStatus.OPEN.value,
        comment="ReviewCaseStatus enum value",
    )

    # Actor / timing
    opened_by: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, comment="OIDC sub of user or service that opened the case"
    )
    opened_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    resolved_by: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    resolution_explanation: Mapped[str | None] = mapped_column(
        sa.Text, nullable=True
    )

    is_overlap_case: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, default=False
    )

    # Relationships
    decisions: Mapped[list[ReviewDecision]] = relationship(
        "ReviewDecision",
        back_populates="review_case",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in ReviewCaseStatus)})",
            name="status_values",
        ),
        sa.Index("ix_review_cases_institution_id", "institution_id"),
        sa.Index("ix_review_cases_status", "status"),
        sa.Index("ix_review_cases_is_overlap_case", "is_overlap_case"),
        sa.Index("ix_review_cases_finding_ref_id", "finding_ref_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ReviewCase id={self.id} "
            f"institution_id={self.institution_id} "
            f"case_type={self.case_type!r} status={self.status!r}>"
        )


class ReviewDecision(Base):
    """An authorised decision on a ReviewCase.

    Decisions are append-only.  When a decision supersedes an earlier one
    (e.g. REOPENED after DISMISSED), ``supersedes_decision_id`` links back.

    Valid decision values: RESOLVED | DISMISSED | REOPENED.
    """

    __tablename__ = "review_decisions"

    review_case_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("review_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    decision: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        comment="RESOLVED | DISMISSED | REOPENED",
    )
    made_by: Mapped[str] = mapped_column(
        sa.String(255), nullable=False, comment="OIDC sub of decision maker"
    )
    made_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    explanation: Mapped[str] = mapped_column(sa.Text, nullable=False)

    # Supersession chain (self-referential)
    supersedes_decision_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("review_decisions.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    review_case: Mapped[ReviewCase] = relationship(
        "ReviewCase", back_populates="decisions"
    )
    supersedes: Mapped[ReviewDecision | None] = relationship(
        "ReviewDecision",
        foreign_keys=[supersedes_decision_id],
        remote_side="ReviewDecision.id",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "decision IN ('RESOLVED', 'DISMISSED', 'REOPENED')",
            name="decision_values",
        ),
        sa.Index("ix_review_decisions_review_case_id", "review_case_id"),
        sa.Index("ix_review_decisions_made_by", "made_by"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ReviewDecision id={self.id} "
            f"review_case_id={self.review_case_id} "
            f"decision={self.decision!r}>"
        )
