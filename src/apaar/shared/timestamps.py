"""Timestamp and date helpers for APAAR Core."""
from __future__ import annotations

import re
from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


_ACADEMIC_YEAR_RE = re.compile(r"^(\d{4})-(\d{2})$")


def parse_academic_year(s: str) -> tuple[int, int]:
    """Parse academic year string e.g. '2024-25' -> (2024, 2025).

    Raises ValueError if the format is invalid.
    """
    m = _ACADEMIC_YEAR_RE.match(s.strip())
    if not m:
        raise ValueError(f"Academic year must be in YYYY-YY format, got: {s!r}")
    start_year = int(m.group(1))
    end_suffix = int(m.group(2))
    end_year = (start_year // 100) * 100 + end_suffix
    if end_year <= start_year:
        end_year += 100
    if end_year != start_year + 1:
        raise ValueError(
            f"Academic year must span one year (e.g. 2024-25), got: {s!r}"
        )
    return start_year, end_year


def validate_academic_year(s: str) -> str:
    """Validate and return normalized academic year string."""
    parse_academic_year(s)
    return s.strip()


def academic_year_start(academic_year: str) -> int:
    """Return the starting calendar year for an academic year string."""
    start, _ = parse_academic_year(academic_year)
    return start


def format_timestamp(dt: datetime) -> str:
    """Format a datetime as an ISO 8601 string in UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC).isoformat()

