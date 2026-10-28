"""SQLAlchemy ORM models for the asynchronous worker and job queue.

PostgreSQL SKIP LOCKED-based job claiming with lease tokens and retry tracking.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from apaar.database import Base
from apaar.shared.types import JobStatus


class Job(Base):
    """Durable asynchronous background job.

    Supports lease-based claims, idempotent execution via effect_key,
    and automatic retry backoff.
    """

    __tablename__ = "jobs"

    job_type: Mapped[str] = mapped_column(sa.String(64), nullable=False, index=True)
    institution_id: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("institutions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    payload_json: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON,
        nullable=False,
        default=dict,
    )
    status: Mapped[JobStatus] = mapped_column(
        sa.Enum(JobStatus, name="job_status_enum", native_enum=False),
        nullable=False,
        default=JobStatus.PENDING,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(sa.Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(sa.Integer, default=3, nullable=False)
    effect_key: Mapped[str | None] = mapped_column(
        sa.String(255),
        nullable=True,
        unique=True,
        comment="Idempotency effect key to avoid duplicate execution.",
    )
    lease_token: Mapped[UUID | None] = mapped_column(
        sa.UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    leased_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    failed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
    failure_reason: Mapped[str | None] = mapped_column(
        sa.Text,
        nullable=True,
    )
    result_json: Mapped[dict[str, Any] | None] = mapped_column(
        sa.JSON,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<Job id={self.id} type={self.job_type} status={self.status}>"

