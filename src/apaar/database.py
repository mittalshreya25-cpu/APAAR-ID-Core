"""Database engine, session factory and base model.

All APAAR identifiers and student data in this system are synthetic / mock.
No real Aadhaar numbers, real student records, or live government credentials
are collected or stored.

Architecture notes
------------------
* The runtime application uses an **async** engine (asyncpg driver) via
  ``get_async_session()``.
* Alembic migrations use a **synchronous** URL (``DATABASE_MIGRATION_URL``)
  with a separate migration-owner role — never the runtime role.
* Optimistic locking is implemented via the ``version`` column on ``Base``.
  Use ``StaleVersionError`` in use-case code when a CAS update touches 0 rows.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID, uuid4

import sqlalchemy as sa
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from apaar.config import get_settings

# ---------------------------------------------------------------------------
# Metadata with explicit naming conventions (required for Alembic autogenerate)
# ---------------------------------------------------------------------------

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=NAMING_CONVENTION)


# ---------------------------------------------------------------------------
# Declarative base with shared mixin columns
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all APAAR ORM models.

    Every table automatically inherits:

    * ``id`` — UUID primary key (server-generated).
    * ``created_at`` — timezone-aware UTC timestamp set on INSERT.
    * ``updated_at`` — timezone-aware UTC timestamp updated on every UPDATE.
    * ``version`` — integer counter for optimistic locking (CAS pattern).
    """

    metadata = metadata

    id: Mapped[UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        doc="Surrogate UUID primary key — not exposed as a public APAAR identifier.",
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        doc="UTC timestamp of row creation.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        doc="UTC timestamp of last update.",
    )
    version: Mapped[int] = mapped_column(
        sa.Integer,
        default=0,
        nullable=False,
        doc=(
            "Optimistic locking counter. Use-case code must include "
            "``WHERE version = :expected_version`` and raise StaleVersionError "
            "when the UPDATE touches 0 rows."
        ),
    )


# ---------------------------------------------------------------------------
# Engine and session factory (lazy singletons)
# ---------------------------------------------------------------------------

_engine = None
_async_session_factory = None


def get_engine():
    """Return (or lazily create) the shared async SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        kwargs: dict = {
            "echo": settings.DEBUG,
        }
        if "sqlite" in settings.DATABASE_URL.lower():
            from sqlalchemy.pool import NullPool
            kwargs["connect_args"] = {"check_same_thread": False}
            kwargs["poolclass"] = NullPool
        else:
            kwargs["pool_pre_ping"] = True
            kwargs["pool_size"] = 10
            kwargs["max_overflow"] = 20

        _engine = create_async_engine(
            settings.DATABASE_URL,
            **kwargs,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return (or lazily create) the async session factory."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for use as a FastAPI dependency.

    Usage::

        @router.get("/items")
        async def list_items(db: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with get_session_factory()() as session:
        yield session


# ---------------------------------------------------------------------------
# Context manager for non-request code (workers, scripts)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that provides a database session.

    Use this in background workers, CLIs, and tests where FastAPI's
    dependency injection is not available::

        async with get_db_session() as db:
            result = await db.execute(select(MyModel))
    """
    async with get_session_factory()() as session:
        yield session
