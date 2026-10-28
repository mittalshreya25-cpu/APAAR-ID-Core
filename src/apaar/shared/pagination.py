"""Pagination utilities for APAAR Core APIs.

Provides a generic cursor-based page model and helper functions for
building paginated responses consistently across all list endpoints.
"""
from __future__ import annotations

import base64
import json
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


# ---------------------------------------------------------------------------
# Request/cursor models
# ---------------------------------------------------------------------------


class PageRequest(BaseModel):
    """Query parameters for paginated list requests."""

    cursor: str | None = Field(default=None, description="Opaque pagination cursor")
    limit: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Items per page")


class PageCursor(BaseModel):
    """Internal cursor data (encoded as opaque string in API responses)."""

    offset: int = 0
    order_by: str = "created_at"
    direction: str = "asc"


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------


class Page(BaseModel, Generic[T]):
    """Generic paginated response."""

    items: list[T]
    total: int
    limit: int
    has_next: bool
    has_prev: bool
    next_cursor: str | None = None
    prev_cursor: str | None = None


# ---------------------------------------------------------------------------
# Cursor encoding helpers
# ---------------------------------------------------------------------------


def encode_cursor(cursor: PageCursor) -> str:
    """Encode a cursor to an opaque base64 string."""
    data = cursor.model_dump()
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def decode_cursor(encoded: str) -> PageCursor:
    """Decode a base64 cursor string back to a PageCursor."""
    try:
        data = json.loads(base64.urlsafe_b64decode(encoded.encode()))
        return PageCursor(**data)
    except Exception as exc:
        from apaar.shared.errors import ValidationError

        raise ValidationError(f"Invalid pagination cursor: {exc}") from exc


# ---------------------------------------------------------------------------
# Page builder helper
# ---------------------------------------------------------------------------


def build_page(
    items: list[T],
    total: int,
    limit: int,
    offset: int,
) -> Page[T]:
    """Build a Page response from a list of items and metadata."""
    has_next = offset + limit < total
    has_prev = offset > 0

    next_cursor = None
    if has_next:
        next_cursor = encode_cursor(PageCursor(offset=offset + limit))

    prev_cursor = None
    if has_prev:
        prev_cursor = encode_cursor(PageCursor(offset=max(0, offset - limit)))

    return Page(
        items=items,
        total=total,
        limit=limit,
        has_next=has_next,
        has_prev=has_prev,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
    )

