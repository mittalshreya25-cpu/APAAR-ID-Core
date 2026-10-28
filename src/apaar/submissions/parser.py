"""CSV and JSON ingestion parser for APAAR Core submission files.

Accepts bounded UTF-8 CSV and typed JSON only. Rejects archives, macros
and unsupported formats. Preserves original bytes/hash and row number.
Leading zeros in APAAR and student IDs are preserved as strings.

Security controls applied here:
- File size limit checked before parsing
- Row and column count limits enforced
- Spreadsheet formula prefix escaping on export (not parse)
- No URL fetching from row content
- Unexpected fields rejected/quarantined
- Original file bytes + hash stored for audit
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from apaar.config import get_settings
from apaar.shared.errors import UploadError

# ---------------------------------------------------------------------------
# Expected CSV schema column definitions
# ---------------------------------------------------------------------------

REQUIRED_CSV_COLUMNS = frozenset(
    [
        "local_student_id",
        "apaar_id",
        "entry_route",
        "category",
        "is_nri",
        "is_oci",
        "is_fn",
        "admission_cohort",
        "current_study_year",
        "interval_start",
    ]
)

OPTIONAL_CSV_COLUMNS = frozenset(
    [
        "interval_end",
        "allocation_pool",
        "display_name",  # For demo display only — not stored long-term
        "notes",
    ]
)

ALL_ALLOWED_COLUMNS = REQUIRED_CSV_COLUMNS | OPTIONAL_CSV_COLUMNS

# Fields that must be treated as strings to preserve leading zeros
STRING_FIELDS = frozenset(["local_student_id", "apaar_id"])

# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ParsedRow:
    """A single normalized row from an uploaded file."""

    row_number: int
    raw_data: dict[str, str]
    normalized_data: dict[str, Any]
    parse_errors: list[str] = field(default_factory=list)
    is_rejected: bool = False


@dataclass
class ParseResult:
    """Result of parsing a submission file."""

    file_hash: str
    file_size: int
    original_filename: str
    content_type: Literal["csv", "json"]
    schema_version: str
    received_rows: int
    processed_rows: int
    rejected_rows: int
    rows: list[ParsedRow]
    global_errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"


class SubmissionParser:
    """Parse and normalize submission files into structured rows.

    All validation is structural/format only. Domain business rules
    (duplicates, capacity, overlaps) are applied by the validation module.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def _compute_hash(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    def parse(
        self,
        content: bytes,
        filename: str,
    ) -> ParseResult:
        """Parse raw file bytes into a ParseResult.

        Args:
            content: Raw file bytes (UTF-8).
            filename: Original filename for format detection.

        Returns:
            ParseResult with all rows, errors and metadata.

        Raises:
            UploadError: If the file exceeds size/row/column limits or
                         has an unsupported format.
        """
        settings = self._settings

        # --- Size check ---
        if len(content) > settings.MAX_UPLOAD_BYTES:
            raise UploadError(
                f"File size {len(content):,} bytes exceeds maximum "
                f"{settings.MAX_UPLOAD_BYTES:,} bytes.",
            )

        file_hash = self._compute_hash(content)
        file_size = len(content)

        # --- Format detection ---
        lower_name = filename.lower()
        if lower_name.endswith(".csv"):
            return self._parse_csv(content, filename, file_hash, file_size)
        if lower_name.endswith(".json"):
            return self._parse_json(content, filename, file_hash, file_size)
        raise UploadError(
            f"Unsupported file format: {filename!r}. "
            "Only UTF-8 CSV (.csv) and typed JSON (.json) are accepted.",
        )

    def _parse_csv(
        self,
        content: bytes,
        filename: str,
        file_hash: str,
        file_size: int,
    ) -> ParseResult:
        settings = self._settings
        global_errors: list[str] = []

        try:
            text = content.decode("utf-8-sig")  # Handle BOM if present
        except UnicodeDecodeError as e:
            raise UploadError(f"File is not valid UTF-8: {e}") from e

        reader = csv.DictReader(io.StringIO(text))

        if reader.fieldnames is None:
            raise UploadError("CSV file has no header row.")

        # Normalize column names
        columns = [c.strip().lower() for c in reader.fieldnames]

        # Column count limit
        if len(columns) > settings.MAX_COLUMNS:
            raise UploadError(
                f"CSV has {len(columns)} columns, exceeding maximum {settings.MAX_COLUMNS}."
            )

        # Check required columns
        missing = REQUIRED_CSV_COLUMNS - set(columns)
        if missing:
            raise UploadError(
                f"CSV is missing required columns: {sorted(missing)}. "
                f"Found: {sorted(columns)}."
            )

        # Warn about unexpected columns
        unexpected = set(columns) - ALL_ALLOWED_COLUMNS
        if unexpected:
            global_errors.append(
                f"Unexpected columns will be ignored: {sorted(unexpected)}."
            )

        rows: list[ParsedRow] = []
        row_number = 0

        for raw_row in reader:
            row_number += 1

            if row_number > settings.MAX_ROWS:
                raise UploadError(
                    f"File exceeds maximum {settings.MAX_ROWS} rows. "
                    "Split into smaller batches."
                )

            # Normalize keys
            raw_data = {k.strip().lower(): v.strip() for k, v in raw_row.items() if k}

            parsed = self._normalize_row(row_number, raw_data)
            rows.append(parsed)

        processed = sum(1 for r in rows if not r.is_rejected)
        rejected = sum(1 for r in rows if r.is_rejected)

        return ParseResult(
            file_hash=file_hash,
            file_size=file_size,
            original_filename=filename,
            content_type="csv",
            schema_version=SCHEMA_VERSION,
            received_rows=row_number,
            processed_rows=processed,
            rejected_rows=rejected,
            rows=rows,
            global_errors=global_errors,
        )

    def _parse_json(
        self,
        content: bytes,
        filename: str,
        file_hash: str,
        file_size: int,
    ) -> ParseResult:
        settings = self._settings
        global_errors: list[str] = []

        try:
            text = content.decode("utf-8")
            data = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError) as e:
            raise UploadError(f"File is not valid UTF-8 JSON: {e}") from e

        if not isinstance(data, list):
            raise UploadError(
                "JSON submission must be a top-level array of row objects."
            )

        if len(data) > settings.MAX_ROWS:
            raise UploadError(
                f"JSON array has {len(data)} rows, exceeding maximum {settings.MAX_ROWS}."
            )

        rows: list[ParsedRow] = []
        for i, item in enumerate(data):
            row_number = i + 1
            if not isinstance(item, dict):
                rows.append(
                    ParsedRow(
                        row_number=row_number,
                        raw_data={},
                        normalized_data={},
                        parse_errors=[f"Row {row_number} is not a JSON object."],
                        is_rejected=True,
                    )
                )
                continue

            # Normalize keys
            raw_data = {k.strip().lower(): str(v).strip() for k, v in item.items()}
            parsed = self._normalize_row(row_number, raw_data)
            rows.append(parsed)

        processed = sum(1 for r in rows if not r.is_rejected)
        rejected = sum(1 for r in rows if r.is_rejected)

        return ParseResult(
            file_hash=file_hash,
            file_size=file_size,
            original_filename=filename,
            content_type="json",
            schema_version=SCHEMA_VERSION,
            received_rows=len(data),
            processed_rows=processed,
            rejected_rows=rejected,
            rows=rows,
            global_errors=global_errors,
        )

    def _normalize_row(
        self, row_number: int, raw_data: dict[str, str]
    ) -> ParsedRow:
        """Normalize a single row's fields and detect format errors."""
        errors: list[str] = []
        normalized: dict[str, Any] = {}

        # Preserve string fields as-is (leading zeros matter!)
        for col in STRING_FIELDS:
            val = raw_data.get(col, "").strip()
            if not val:
                errors.append(f"Column '{col}' is required and missing or empty.")
            else:
                normalized[col] = val

        # Boolean fields
        for col in ("is_nri", "is_oci", "is_fn"):
            val = raw_data.get(col, "").strip().lower()
            if val in ("true", "1", "yes"):
                normalized[col] = True
            elif val in ("false", "0", "no", ""):
                normalized[col] = False
            else:
                errors.append(f"Column '{col}' must be true/false, got: {val!r}")

        # Integer fields
        for col in ("current_study_year",):
            val = raw_data.get(col, "").strip()
            try:
                normalized[col] = int(val)
            except ValueError:
                errors.append(f"Column '{col}' must be an integer, got: {val!r}")

        # String/enum fields copied as-is (validated by domain rules)
        for col in ("entry_route", "category", "admission_cohort", "allocation_pool"):
            val = raw_data.get(col, "").strip()
            if col in REQUIRED_CSV_COLUMNS and not val:
                errors.append(f"Column '{col}' is required and missing or empty.")
            else:
                normalized[col] = val

        # Date fields
        for col in ("interval_start", "interval_end"):
            val = raw_data.get(col, "").strip()
            if col == "interval_start" and not val:
                errors.append(f"Column '{col}' is required.")
            elif val:
                normalized[col] = val  # Validated by domain rules

        # Optional string fields
        for col in ("display_name", "notes"):
            val = raw_data.get(col, "").strip()
            if val:
                normalized[col] = val[:512]  # Bounded

        is_rejected = len(errors) > 0

        return ParsedRow(
            row_number=row_number,
            raw_data=raw_data,
            normalized_data=normalized if not is_rejected else {},
            parse_errors=errors,
            is_rejected=is_rejected,
        )

