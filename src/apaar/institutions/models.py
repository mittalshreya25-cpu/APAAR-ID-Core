"""SQLAlchemy ORM models for the institutions domain.

Synthetic data only — no real institution credentials are stored.
"""
from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import MembershipRole

if TYPE_CHECKING:
    pass


class Institution(Base):
    """A registered higher-education institution (synthetic demo record).

    The ``code`` column holds a short unique institution identifier such as
    an invented AICTE approval number.  No live government data is stored.
    """

    __tablename__ = "institutions"

    # id / created_at / updated_at / version inherited from Base
    name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    code: Mapped[str] = mapped_column(sa.String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default="active",
        comment="active | inactive",
    )

    # Relationships
    memberships: Mapped[list[InstitutionMembership]] = relationship(
        "InstitutionMembership",
        back_populates="institution",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        sa.CheckConstraint("status IN ('active', 'inactive')", name="status_values"),
        sa.Index("ix_institutions_code", "code"),
        sa.Index("ix_institutions_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Institution id={self.id} code={self.code!r} status={self.status!r}>"


class InstitutionMembership(Base):
    """Maps an OIDC subject to a role within an institution.

    The ``subject_id`` is the ``sub`` claim from the OIDC token — an opaque
    string identifying a user account.  No personal identity documents are
    stored here.

    ``scope_json`` is an optional JSON object restricting which programmes or
    cohorts the membership covers; ``None`` means full-institution access.
    """

    __tablename__ = "institution_memberships"

    institution_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="CASCADE"),
        nullable=False,
    )
    subject_id: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="OIDC sub claim — opaque user identifier",
    )
    role: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        comment="MembershipRole enum value",
    )
    scope_json: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    # Relationships
    institution: Mapped[Institution] = relationship(
        "Institution", back_populates="memberships"
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"role IN ({', '.join(repr(r.value) for r in MembershipRole)})",
            name="role_values",
        ),
        sa.Index("ix_institution_memberships_institution_id", "institution_id"),
        sa.Index("ix_institution_memberships_subject_id", "subject_id"),
        sa.Index(
            "ix_institution_memberships_subject_institution",
            "subject_id",
            "institution_id",
        ),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<InstitutionMembership id={self.id} "
            f"institution_id={self.institution_id} "
            f"subject_id={self.subject_id!r} role={self.role!r}>"
        )
