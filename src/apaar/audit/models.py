"""SQLAlchemy ORM models for the audit domain.

AuditEvent is an append-only log of all security-relevant actions.

IMPORTANT — data-minimisation contract:
  * ``before_ref`` / ``after_ref`` are opaque references to versioned snapshots
    or diffs stored elsewhere — they do NOT contain raw personal data inline.
  * ``principal`` is an OIDC subject — an opaque identifier, not a name.
  * Secrets and personal data must never appear in audit log fields.

Rows in this table are never updated or deleted within the application.
Retention and archival are infrastructure-level concerns.
"""
from __future__ import annotations

import datetime
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from apaar.database import Base


class AuditEvent(Base):
    """One security-relevant audit log entry.

    Fields:
    - event_type:    coarse category e.g. 'SUBMISSION', 'DISCLOSURE', 'AUTH'
    - principal:     OIDC sub of the actor
    - institution_id: context institution (NULL for system events)
    - object_type:   table/domain name of the affected object
    - object_id:     UUID of the affected object
    - object_version: optimistic-lock version of the object at time of action
    - action:        verb e.g. 'CREATE', 'UPDATE', 'CERTIFY', 'REVOKE'
    - outcome:       'SUCCESS' | 'FAILURE' | 'PARTIAL'
    - purpose:       optional declared business purpose
    - before_ref:    opaque ref to pre-change state snapshot (no inline PII)
    - after_ref:     opaque ref to post-change state snapshot (no inline PII)
    - timestamp:     when the event occurred (set by application)
    - request_id:    correlation ID from the HTTP request or job
    """

    __tablename__ = "audit_events"

    event_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    principal: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="OIDC sub of the actor — opaque identifier",
    )
    institution_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        comment="Context institution (no FK — audit log must not cascade-delete)",
    )
    object_type: Mapped[str] = mapped_column(sa.String(64), nullable=False)
    object_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True), nullable=True
    )
    object_version: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    action: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="e.g. 'CREATE', 'UPDATE', 'CERTIFY', 'REVOKE', 'DISCLOSE'",
    )
    outcome: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        comment="'SUCCESS' | 'FAILURE' | 'PARTIAL'",
    )
    purpose: Mapped[str | None] = mapped_column(sa.String(512), nullable=True)
    before_ref: Mapped[str | None] = mapped_column(
        sa.String(512),
        nullable=True,
        comment="Opaque ref to pre-change state — no inline PII",
    )
    after_ref: Mapped[str | None] = mapped_column(
        sa.String(512),
        nullable=True,
        comment="Opaque ref to post-change state — no inline PII",
    )
    timestamp: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        comment="When the event occurred (application clock)",
    )
    request_id: Mapped[str] = mapped_column(
        sa.String(128),
        nullable=False,
        comment="Correlation ID from HTTP request or background job",
    )

    __table_args__ = (
        sa.CheckConstraint(
            "outcome IN ('SUCCESS', 'FAILURE', 'PARTIAL')",
            name="outcome_values",
        ),
        sa.Index("ix_audit_events_principal", "principal"),
        sa.Index("ix_audit_events_event_type", "event_type"),
        sa.Index("ix_audit_events_institution_id", "institution_id"),
        sa.Index("ix_audit_events_object_type_id", "object_type", "object_id"),
        sa.Index("ix_audit_events_timestamp", "timestamp"),
        sa.Index("ix_audit_events_request_id", "request_id"),
        sa.Index("ix_audit_events_action", "action"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AuditEvent id={self.id} "
            f"event_type={self.event_type!r} "
            f"principal={self.principal!r} "
            f"action={self.action!r} outcome={self.outcome!r}>"
        )
