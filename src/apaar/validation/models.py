"""SQLAlchemy ORM models for the validation domain.

Rule bundles are versioned and immutable once created — corrections are added
as new bundles; the old one is retained for audit of previously evaluated runs.

``rules_yaml_content`` is stored verbatim; no ``eval`` or arbitrary expression
execution occurs here.  Only the YAML hash is used for integrity checking.

A ValidationRun links one Submission to one RuleBundle (and optionally to the
applicable IntakeApproval) and records aggregate finding counts.
Individual ValidationFindings are per-rule per-row results.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import FindingOutcome

if TYPE_CHECKING:
    from apaar.submissions.models import Submission


class RuleBundle(Base):
    """A versioned, immutable set of validation rules.

    ``rules_yaml_content`` holds the raw YAML text; ``rules_yaml_hash`` is the
    SHA-256 digest used for integrity verification.  Rule bundles are
    append-only: never mutate an existing bundle.

    ``authority_status`` records the evidentiary basis for the rules contained;
    DEMO_ONLY bundles must not be used for regulatory reporting without review.
    """

    __tablename__ = "rule_bundles"

    bundle_code: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, unique=True
    )
    display_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    version: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        comment="Semantic version of this bundle e.g. '1.0.0'",
    )
    authority_status: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        comment="AuthorityStatus enum value",
    )
    rules_yaml_hash: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="SHA-256 hex digest of rules_yaml_content",
    )
    rules_yaml_content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="Raw YAML text — never eval'd; interpreter uses a safe loader",
    )
    source_references_json: Mapped[list] = mapped_column(
        sa.JSON, nullable=False, default=list
    )
    reviewed_by: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=True)

    # Relationships
    validation_runs: Mapped[list[ValidationRun]] = relationship(
        "ValidationRun",
        back_populates="rule_bundle",
    )

    __table_args__ = (
        sa.Index("ix_rule_bundles_bundle_code", "bundle_code", unique=True),
        sa.Index("ix_rule_bundles_is_active", "is_active"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RuleBundle id={self.id} "
            f"bundle_code={self.bundle_code!r} "
            f"version={self.version!r}>"
        )


class ValidationRun(Base):
    """One execution of a RuleBundle against a Submission's staged rows.

    ``input_hash`` is a digest of all staged-row content fed into the run,
    ensuring reproducibility checks can detect changed inputs.

    ``blocking_findings`` counts FAIL + REVIEW_REQUIRED outcomes; when
    non-zero the Submission cannot be quality-certified.
    """

    __tablename__ = "validation_runs"

    submission_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("submissions.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_bundle_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("rule_bundles.id", ondelete="RESTRICT"),
        nullable=False,
    )
    intake_approval_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("intake_approvals.id", ondelete="SET NULL"),
        nullable=True,
    )

    input_hash: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="SHA-256 of all staged-row normalized_data_json fed into this run",
    )
    evaluator_code_revision: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="Git revision or release tag of the evaluator",
    )
    fixture_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    evaluated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default="PENDING",
        comment="PENDING | RUNNING | COMPLETED | FAILED",
    )
    total_findings: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )
    blocking_findings: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, default=0
    )

    # Relationships
    submission: Mapped[Submission] = relationship(
        "Submission", back_populates="validation_runs"
    )
    rule_bundle: Mapped[RuleBundle] = relationship(
        "RuleBundle", back_populates="validation_runs"
    )
    findings: Mapped[list[ValidationFinding]] = relationship(
        "ValidationFinding",
        back_populates="validation_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')",
            name="status_values",
        ),
        sa.CheckConstraint("total_findings >= 0", name="total_findings_nonneg"),
        sa.CheckConstraint("blocking_findings >= 0", name="blocking_findings_nonneg"),
        sa.Index("ix_validation_runs_submission_id", "submission_id"),
        sa.Index("ix_validation_runs_rule_bundle_id", "rule_bundle_id"),
        sa.Index("ix_validation_runs_intake_approval_id", "intake_approval_id"),
        sa.Index("ix_validation_runs_status", "status"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ValidationRun id={self.id} "
            f"submission_id={self.submission_id} "
            f"status={self.status!r} "
            f"blocking_findings={self.blocking_findings}>"
        )


class ValidationFinding(Base):
    """One rule evaluation result within a ValidationRun.

    Findings are immutable once created; a new run supersedes old findings
    rather than updating them.

    ``is_blocking`` is derived from ``outcome.is_blocking`` at write time and
    stored for fast query without re-joining to the enum definition.
    """

    __tablename__ = "validation_findings"

    validation_run_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("validation_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    staged_row_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("staged_rows.id", ondelete="SET NULL"),
        nullable=True,
        comment="NULL for submission-level findings that span all rows",
    )

    rule_id: Mapped[str] = mapped_column(sa.String(128), nullable=False)
    rule_version: Mapped[str] = mapped_column(sa.String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(
        sa.String(32),
        nullable=False,
        comment="FindingOutcome enum value",
    )
    observed_value: Mapped[str | None] = mapped_column(
        sa.String(512), nullable=True
    )
    expected_condition: Mapped[str | None] = mapped_column(
        sa.String(512), nullable=True
    )
    confidence: Mapped[str | None] = mapped_column(sa.String(32), nullable=True)
    remediation: Mapped[str | None] = mapped_column(sa.String(1024), nullable=True)
    is_blocking: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, default=False)

    # Relationship
    validation_run: Mapped[ValidationRun] = relationship(
        "ValidationRun", back_populates="findings"
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"outcome IN ({', '.join(repr(o.value) for o in FindingOutcome)})",
            name="outcome_values",
        ),
        sa.Index(
            "ix_validation_findings_validation_run_id", "validation_run_id"
        ),
        sa.Index("ix_validation_findings_staged_row_id", "staged_row_id"),
        sa.Index("ix_validation_findings_outcome", "outcome"),
        sa.Index("ix_validation_findings_is_blocking", "is_blocking"),
        sa.Index("ix_validation_findings_rule_id", "rule_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ValidationFinding id={self.id} "
            f"validation_run_id={self.validation_run_id} "
            f"rule_id={self.rule_id!r} outcome={self.outcome!r}>"
        )
