"""SQLAlchemy ORM models for the attestations domain.

Attestations are signed records (JWS compact serialisation) that certify the
state of an enrolment episode or submission at a point in time.

IMPORTANT — security contract:
  * ``signed_bytes`` contains a JWS compact token.  Verification requires
    the public key from the referenced ``SigningKey`` — do not trust the
    payload without signature verification.
  * ``subject_ref`` is an internal opaque identifier only — never the raw
    APAAR or Aadhaar value.
  * A printed or QR-encoded attestation ID alone does NOT authorise disclosure.
    Callers must resolve the full grant/verification pipeline.

Key rotation: when a key is ROTATED, existing attestations remain valid until
they expire; when COMPROMISED, all dependent attestations must be REVOKED.
"""
from __future__ import annotations

import datetime
from typing import TYPE_CHECKING
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from apaar.database import Base
from apaar.shared.types import AttestationStatus, KeyStatus

if TYPE_CHECKING:
    pass


class SigningKey(Base):
    """A key pair used to sign attestation JWS tokens.

    Only the public key PEM is stored here; the private key is managed by the
    application's key-management service and never persisted in the database.

    ``issuer_id`` optionally references the institution that owns this key
    (NULL means a system-level key).
    """

    __tablename__ = "signing_keys"

    key_alias: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, unique=True
    )
    algorithm: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        comment="e.g. 'EdDSA', 'ES256'",
    )
    public_key_pem: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="PEM-encoded public key for signature verification",
    )
    key_status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=KeyStatus.ACTIVE.value,
        comment="KeyStatus enum value",
    )
    activated_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    deactivated_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    issuer_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        comment="Owning institution; NULL for system keys",
    )

    # Relationships
    attestations: Mapped[list[Attestation]] = relationship(
        "Attestation",
        back_populates="issuer_key",
        foreign_keys="Attestation.issuer_key_id",
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"key_status IN ({', '.join(repr(k.value) for k in KeyStatus)})",
            name="key_status_values",
        ),
        sa.Index("ix_signing_keys_key_alias", "key_alias", unique=True),
        sa.Index("ix_signing_keys_key_status", "key_status"),
        sa.Index("ix_signing_keys_issuer_id", "issuer_id"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<SigningKey id={self.id} "
            f"key_alias={self.key_alias!r} "
            f"key_status={self.key_status!r}>"
        )


class Attestation(Base):
    """A signed certification record for an enrolment episode or submission.

    ``signed_bytes`` is a JWS compact token.  The payload is also accessible
    via ``payload_hash`` for integrity checks without deserialisation.

    Supersession: when a correction is issued the old attestation has
    ``superseded_by_id`` set and its status transitions to SUPERSEDED.

    ``subject_ref`` is an internal opaque identifier — it must never contain
    the raw synthetic APAAR or any personal attribute.
    """

    __tablename__ = "attestations"

    record_type: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        comment="e.g. 'ENROLMENT_CERTIFICATION', 'SUBMISSION_CERTIFICATION'",
    )
    issuer_key_id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("signing_keys.id", ondelete="RESTRICT"),
        nullable=False,
    )
    submission_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("submissions.id", ondelete="SET NULL"),
        nullable=True,
    )
    episode_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("enrolment_episodes.id", ondelete="SET NULL"),
        nullable=True,
    )
    snapshot_ref_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        comment="Optional reference to a ReportSnapshot UUID (no FK to avoid circular dep)",
    )

    subject_ref: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        comment="Internal opaque reference — NOT the raw APAAR or any PII",
    )
    purpose: Mapped[str] = mapped_column(
        sa.String(128), nullable=False, comment="Why this attestation was issued"
    )
    payload_hash: Mapped[str] = mapped_column(
        sa.String(64), nullable=False, comment="SHA-256 of the JWS payload bytes"
    )
    signed_bytes: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        comment="JWS compact serialisation — must be verified before trust",
    )

    status: Mapped[str] = mapped_column(
        sa.String(16),
        nullable=False,
        default=AttestationStatus.ACTIVE.value,
        comment="AttestationStatus enum value",
    )
    issued_at: Mapped[datetime.datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    expires_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    # Supersession chain (self-referential)
    superseded_by_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("attestations.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Revocation
    revoked_at: Mapped[datetime.datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )
    revocation_reason: Mapped[str | None] = mapped_column(
        sa.String(512), nullable=True
    )

    # Relationships
    issuer_key: Mapped[SigningKey] = relationship(
        "SigningKey",
        back_populates="attestations",
        foreign_keys=[issuer_key_id],
    )
    superseded_by: Mapped[Attestation | None] = relationship(
        "Attestation",
        foreign_keys=[superseded_by_id],
        remote_side="Attestation.id",
    )

    __table_args__ = (
        sa.CheckConstraint(
            f"status IN ({', '.join(repr(s.value) for s in AttestationStatus)})",
            name="status_values",
        ),
        sa.Index("ix_attestations_issuer_key_id", "issuer_key_id"),
        sa.Index("ix_attestations_submission_id", "submission_id"),
        sa.Index("ix_attestations_episode_id", "episode_id"),
        sa.Index("ix_attestations_status", "status"),
        sa.Index("ix_attestations_superseded_by_id", "superseded_by_id"),
        sa.Index("ix_attestations_subject_ref", "subject_ref"),
        sa.Index("ix_attestations_issued_at", "issued_at"),
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Attestation id={self.id} "
            f"record_type={self.record_type!r} "
            f"status={self.status!r}>"
        )
