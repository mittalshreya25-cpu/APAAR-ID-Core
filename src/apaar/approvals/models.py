"""SQLAlchemy ORM models for the approvals domain.

Captures programme offerings and their approved intake figures.
All authority-status values carry a demo/research provenance tag —
no claim of official AICTE regulatory acceptance is made.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import (
    AuthorityStatus,
    ProgrammeLevel,
    ProgrammeMode,
    ProgrammeShift,
)

if TYPE_CHECKING:
    pass


class ProgrammeOffering(Base):
    """A specific programme offered by an institution.

    Uniqueness is modelled at the (institution, campus, course, level, mode,
    shift) level; the ``version`` column tracks optimistic-lock revisions.
    """

    __tablename__ = "programme_offerings"

    institution_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    campus: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    course_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    level: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        comment="ProgrammeLevel enum value",
    )
    mode: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        comment="ProgrammeMode enum value",
    )
    shift: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=ProgrammeShift.NA.value,
        comment="ProgrammeShift enum value",
    )
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    # Relationships
    intake_approvals: Mapped[list[IntakeApproval]] = relationship(
        "IntakeApproval",
        back_populates="programme_offering",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"level IN ({', '.join(repr(l.value) for l in ProgrammeLevel)})",
            name="level_values",
        ),
        sa.CheckConstraint(
            f"mode IN ({', '.join(repr(m.value) for m in ProgrammeMode)})",
            name="mode_values",
        ),
        sa.CheckConstraint(
            f"shift IN ({', '.join(repr(s.value) for s in ProgrammeShift)})",
            name="shift_values",
        ),
        sa.Index("ix_programme_offerings_institution_id", "institution_id"),
        sa.Index("ix_programme_offerings_level", "level"),
        sa.Index(
            "ix_programme_offerings_institution_level",
            "institution_id",
            "level",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ProgrammeOffering id={self.id} "
            f"institution_id={self.institution_id} "
            f"course_name={self.course_name!r} level={self.level!r}>"
        )


class IntakeApproval(Base):
    """Approved intake capacity for a programme offering in a given academic year.

    ``authority_status`` records the evidence quality of this intake figure —
    values of DEMO_ONLY or UNRESOLVED must not be promoted to validated counts
    without explicit review.  Superseded approvals are retained for audit; only
    the row with ``superseded_by_id IS NULL`` is the current effective approval.
    """

    __tablename__ = "intake_approvals"

    programme_offering_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("programme_offerings.id", ondelete="RESTRICT"),
        nullable=False,
    )
    institution_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    academic_year: Mapped[str] = mapped_column(
        sa.String(10),
        nullable=False,
        comment="e.g. '2024-25'",
    )

    # Seat counts
    approved_ordinary: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    approved_supernumerary: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    approved_nri: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    approved_oci: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)

    # Provenance
    authority_status: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        default=AuthorityStatus.DEMO_ONLY.value,
        comment="AuthorityStatus enum — DEMO_ONLY until reviewed",
    )
    effective_from: Mapped[datetime.date] = mapped_column(
        sa.Date, nullable=False
    )
    effective_to: Mapped[datetime.date | None] = mapped_column(
        sa.Date, nullable=True
    )
    source_reference: Mapped[str | None] = mapped_column(
        sa.String(512), nullable=True
    )

    # Supersession chain (self-referential)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("intake_approvals.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    programme_offering: Mapped[ProgrammeOffering] = relationship(
        "ProgrammeOffering", back_populates="intake_approvals"
    )
    superseded_by: Mapped[IntakeApproval | None] = relationship(
        "IntakeApproval",
        foreign_keys=[superseded_by_id],
        remote_side="IntakeApproval.id",
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"authority_status IN ({', '.join(repr(a.value) for a in AuthorityStatus)})",
            name="authority_status_values",
        ),
        sa.CheckConstraint("approved_ordinary >= 0", name="approved_ordinary_nonneg"),
        sa.CheckConstraint(
            "approved_supernumerary >= 0", name="approved_supernumerary_nonneg"
        ),
        sa.Index("ix_intake_approvals_programme_offering_id", "programme_offering_id"),
        sa.Index("ix_intake_approvals_institution_id", "institution_id"),
        sa.Index(
            "ix_intake_approvals_institution_year",
            "institution_id",
            "academic_year",
        ),
        sa.Index("ix_intake_approvals_superseded_by_id", "superseded_by_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<IntakeApproval id={self.id} "
            f"programme_offering_id={self.programme_offering_id} "
            f"academic_year={self.academic_year!r} "
            f"authority_status={self.authority_status!r}>"
        )
