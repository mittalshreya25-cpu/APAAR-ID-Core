"""Validation rule engine for APAAR Core.

Rule bundles are versioned, immutable YAML definitions. Evaluators are
allowlisted Python functions — no eval, no arbitrary expressions.

This module applies structural validation (schema, format, duplicates)
and capacity counting rules against parsed submission rows and approval data.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from apaar.shared.types import (
    AuthorityStatus,
    EntryRoute,
    FindingOutcome,
    ProviderOutcome,
    StudentCategory,
)

# ---------------------------------------------------------------------------
# APAAR 12-digit format check
# This is SHAPE validation only — not registry verification.
# ---------------------------------------------------------------------------

_APAAR_PATTERN = re.compile(r"^\d{12}$")


def validate_apaar_shape(apaar: str) -> bool:
    """Validate the 12-digit format of a synthetic APAAR string.

    This is a FORMAT check only — it does not prove registry membership
    or identity. Twelve digits demonstrate shape; nothing more.
    """
    return bool(_APAAR_PATTERN.match(apaar.strip()))


# ---------------------------------------------------------------------------
# Finding record
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    """A single rule evaluation result for a row or submission."""

    rule_id: str
    rule_version: str
    outcome: FindingOutcome
    row_number: int | None = None
    field_name: str | None = None
    observed_value: str | None = None
    expected_condition: str | None = None
    confidence: str | None = None
    remediation: str | None = None
    is_blocking: bool = False
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "outcome": self.outcome.value,
            "row_number": self.row_number,
            "field_name": self.field_name,
            "observed_value": self.observed_value,
            "expected_condition": self.expected_condition,
            "confidence": self.confidence,
            "remediation": self.remediation,
            "is_blocking": self.is_blocking,
        }


# ---------------------------------------------------------------------------
# Rule evaluators (allowlisted — no eval)
# ---------------------------------------------------------------------------

RULE_VERSION = "1.0.0"


def _make_finding(
    rule_id: str,
    outcome: FindingOutcome,
    row_number: int | None = None,
    field_name: str | None = None,
    observed: str | None = None,
    expected: str | None = None,
    remediation: str | None = None,
    is_blocking: bool | None = None,
) -> Finding:
    auto_blocking = is_blocking if is_blocking is not None else outcome.is_blocking
    return Finding(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        outcome=outcome,
        row_number=row_number,
        field_name=field_name,
        observed_value=observed,
        expected_condition=expected,
        remediation=remediation,
        is_blocking=auto_blocking,
    )


def rule_apaar_shape(
    row_number: int, apaar: str
) -> Finding:
    """VR-001: APAAR value must be exactly 12 digits."""
    if not apaar or not validate_apaar_shape(apaar):
        return _make_finding(
            "VR-001",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="apaar_id",
            observed=apaar,
            expected="12-digit numeric string",
            remediation="Correct the APAAR ID to exactly 12 numeric digits. "
            "Note: format validation only, not registry verification.",
        )
    return _make_finding("VR-001", FindingOutcome.PASS, row_number=row_number)


def rule_local_student_id_present(
    row_number: int, local_student_id: str
) -> Finding:
    """VR-002: Local student ID must be present and non-empty."""
    if not local_student_id or not local_student_id.strip():
        return _make_finding(
            "VR-002",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="local_student_id",
            observed=local_student_id or "(empty)",
            expected="Non-empty institution local student ID",
            remediation="Provide the institution's internal student ID.",
        )
    return _make_finding("VR-002", FindingOutcome.PASS, row_number=row_number)


def rule_within_file_duplicate_local_id(
    row_number: int, local_student_id: str, seen_ids: set[str]
) -> Finding:
    """VR-003: Local student ID must be unique within this submission."""
    if local_student_id in seen_ids:
        return _make_finding(
            "VR-003",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="local_student_id",
            observed=local_student_id,
            expected="Unique within submission",
            remediation="Remove duplicate row or correct the student ID.",
        )
    return _make_finding("VR-003", FindingOutcome.PASS, row_number=row_number)


def rule_within_file_duplicate_apaar(
    row_number: int, apaar: str, seen_apaars: set[str]
) -> Finding:
    """VR-004: APAAR must be unique within submission (shape-valid only)."""
    if apaar and validate_apaar_shape(apaar) and apaar in seen_apaars:
        return _make_finding(
            "VR-004",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="apaar_id",
            observed=apaar,
            expected="Unique APAAR within submission",
            remediation="A single student should appear only once in a submission.",
        )
    return _make_finding("VR-004", FindingOutcome.PASS, row_number=row_number)


def rule_entry_route_valid(
    row_number: int, entry_route: str
) -> Finding:
    """VR-005: Entry route must be a recognized value."""
    valid_routes = {r.value for r in EntryRoute}
    if entry_route not in valid_routes:
        return _make_finding(
            "VR-005",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="entry_route",
            observed=entry_route,
            expected=f"One of: {sorted(valid_routes)}",
            remediation="Use a recognized entry route code.",
        )
    return _make_finding("VR-005", FindingOutcome.PASS, row_number=row_number)


def rule_category_valid(
    row_number: int, category: str
) -> Finding:
    """VR-006: Student category must be a recognized value."""
    valid_cats = {c.value for c in StudentCategory}
    if category not in valid_cats:
        return _make_finding(
            "VR-006",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="category",
            observed=category,
            expected=f"One of: {sorted(valid_cats)}",
            remediation="Use a recognized student category code.",
        )
    return _make_finding("VR-006", FindingOutcome.PASS, row_number=row_number)


def rule_date_format(
    row_number: int, field_name: str, date_str: str, required: bool = True
) -> Finding:
    """VR-007/VR-008: Date fields must be in YYYY-MM-DD format."""
    rule_id = "VR-007" if field_name == "interval_start" else "VR-008"
    if not date_str:
        if required:
            return _make_finding(
                rule_id,
                FindingOutcome.FAIL,
                row_number=row_number,
                field_name=field_name,
                observed="(missing)",
                expected="YYYY-MM-DD",
                remediation=f"Provide a valid date for '{field_name}'.",
            )
        return _make_finding(rule_id, FindingOutcome.NOT_APPLICABLE, row_number=row_number)

    try:
        date.fromisoformat(date_str)
        return _make_finding(rule_id, FindingOutcome.PASS, row_number=row_number)
    except ValueError:
        return _make_finding(
            rule_id,
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name=field_name,
            observed=date_str,
            expected="YYYY-MM-DD (ISO 8601)",
            remediation="Correct date to ISO 8601 format.",
        )


def rule_provider_outcome(
    row_number: int, outcome: str
) -> Finding:
    """VR-009: Validate based on mock APAAR provider outcome.

    MOCK_MATCH: PASS (subject to other rules)
    MOCK_NOT_FOUND / MOCK_MISMATCH: FAIL — blocks certification
    MOCK_UNAVAILABLE / NOT_CHECKED: REVIEW_REQUIRED — blocks certification
    """
    try:
        po = ProviderOutcome(outcome)
    except ValueError:
        return _make_finding(
            "VR-009",
            FindingOutcome.REVIEW_REQUIRED,
            row_number=row_number,
            field_name="provider_outcome",
            observed=outcome,
            remediation="Unknown provider outcome — manual review required.",
        )

    if po == ProviderOutcome.MOCK_MATCH:
        return _make_finding("VR-009", FindingOutcome.PASS, row_number=row_number)
    if po.blocks_certification:
        return _make_finding(
            "VR-009",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="provider_outcome",
            observed=po.value,
            remediation="Correct the APAAR ID or obtain a valid identity verification.",
        )
    # requires_review
    return _make_finding(
        "VR-009",
        FindingOutcome.REVIEW_REQUIRED,
        row_number=row_number,
        field_name="provider_outcome",
        observed=po.value,
        remediation="Provider result requires manual review before certification.",
    )


def rule_capacity_check(
    ordinary_count: int,
    approved_ordinary: int,
    supernumerary_count: int,
    approved_supernumerary: int,
    nri_count: int,
    approved_nri: int,
    authority_status: str,
) -> list[Finding]:
    """VR-010/VR-011/VR-012: Capacity pool checks.

    Each approved pool is checked separately.
    If authority_status is DEMO_ONLY, findings are advisory, not blocking.
    Policy is DEMO ONLY until complete regulatory evidence is established.
    """
    findings: list[Finding] = []
    is_demo = authority_status == AuthorityStatus.DEMO_ONLY.value

    # Ordinary pool
    if ordinary_count > approved_ordinary:
        findings.append(
            _make_finding(
                "VR-010",
                FindingOutcome.REVIEW_REQUIRED if is_demo else FindingOutcome.FAIL,
                observed=str(ordinary_count),
                expected=f"<= {approved_ordinary}",
                remediation=(
                    f"Ordinary admissions ({ordinary_count}) exceed "
                    f"approved ordinary capacity ({approved_ordinary}). "
                    + ("DEMO POLICY — not an official regulatory finding." if is_demo else "")
                ),
                is_blocking=not is_demo,
            )
        )
    else:
        findings.append(_make_finding("VR-010", FindingOutcome.PASS))

    # Supernumerary pool
    if supernumerary_count > approved_supernumerary:
        findings.append(
            _make_finding(
                "VR-011",
                FindingOutcome.REVIEW_REQUIRED if is_demo else FindingOutcome.FAIL,
                observed=str(supernumerary_count),
                expected=f"<= {approved_supernumerary}",
                remediation=(
                    f"Supernumerary admissions ({supernumerary_count}) exceed "
                    f"approved supernumerary capacity ({approved_supernumerary}). "
                    + ("DEMO POLICY — not an official regulatory finding." if is_demo else "")
                ),
                is_blocking=not is_demo,
            )
        )
    else:
        findings.append(_make_finding("VR-011", FindingOutcome.PASS))

    # NRI pool (if applicable)
    if approved_nri > 0:
        if nri_count > approved_nri:
            findings.append(
                _make_finding(
                    "VR-012",
                    FindingOutcome.REVIEW_REQUIRED if is_demo else FindingOutcome.FAIL,
                    observed=str(nri_count),
                    expected=f"<= {approved_nri}",
                    remediation=(
                        f"NRI admissions ({nri_count}) exceed "
                        f"approved NRI capacity ({approved_nri})."
                    ),
                    is_blocking=not is_demo,
                )
            )
        else:
            findings.append(_make_finding("VR-012", FindingOutcome.PASS))

    return findings


def rule_study_year_valid(
    row_number: int, current_study_year: int, entry_route: str
) -> Finding:
    """VR-013: Study year must be a positive integer."""
    if current_study_year < 1 or current_study_year > 6:
        return _make_finding(
            "VR-013",
            FindingOutcome.FAIL,
            row_number=row_number,
            field_name="current_study_year",
            observed=str(current_study_year),
            expected="1-6",
            remediation="Current study year must be between 1 and 6.",
        )
    return _make_finding("VR-013", FindingOutcome.PASS, row_number=row_number)


def rule_interval_order(
    row_number: int, start: str, end: str | None
) -> Finding:
    """VR-014: interval_end must be after interval_start if present."""
    if not end:
        return _make_finding("VR-014", FindingOutcome.NOT_APPLICABLE, row_number=row_number)
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
        if end_date <= start_date:
            return _make_finding(
                "VR-014",
                FindingOutcome.FAIL,
                row_number=row_number,
                field_name="interval_end",
                observed=f"start={start}, end={end}",
                expected="interval_end > interval_start",
                remediation="The enrolment end date must be after the start date.",
            )
    except ValueError:
        return _make_finding("VR-014", FindingOutcome.NOT_APPLICABLE, row_number=row_number)
    return _make_finding("VR-014", FindingOutcome.PASS, row_number=row_number)


# ---------------------------------------------------------------------------
# Batch evaluator
# ---------------------------------------------------------------------------


def evaluate_submission_rows(
    rows: list[dict[str, Any]],
    provider_results: dict[str, str],  # apaar -> outcome string
) -> list[Finding]:
    """Evaluate all per-row rules against a list of normalized rows.

    Args:
        rows: List of normalized row dicts (from parser).
        provider_results: Mapping of apaar_id -> ProviderOutcome.value.

    Returns:
        Flat list of all findings (across all rows and all rules).
    """
    findings: list[Finding] = []
    seen_local_ids: set[str] = set()
    seen_apaars: set[str] = set()

    for row in rows:
        rn = row.get("row_number", 0)
        local_id = str(row.get("local_student_id", "")).strip()
        apaar = str(row.get("apaar_id", "")).strip()

        # VR-001: APAAR shape
        findings.append(rule_apaar_shape(rn, apaar))

        # VR-002: Local student ID present
        findings.append(rule_local_student_id_present(rn, local_id))

        # VR-003: Duplicate local ID within file
        dup_finding = rule_within_file_duplicate_local_id(rn, local_id, seen_local_ids)
        findings.append(dup_finding)
        seen_local_ids.add(local_id)

        # VR-004: Duplicate APAAR within file
        if validate_apaar_shape(apaar):
            dup_apaar = rule_within_file_duplicate_apaar(rn, apaar, seen_apaars)
            findings.append(dup_apaar)
            seen_apaars.add(apaar)

        # VR-005: Entry route
        findings.append(rule_entry_route_valid(rn, str(row.get("entry_route", ""))))

        # VR-006: Category
        findings.append(rule_category_valid(rn, str(row.get("category", ""))))

        # VR-007: interval_start date format
        findings.append(rule_date_format(rn, "interval_start", str(row.get("interval_start", ""))))

        # VR-008: interval_end date format (optional)
        findings.append(
            rule_date_format(rn, "interval_end", str(row.get("interval_end", "")), required=False)
        )

        # VR-009: Provider outcome
        provider_outcome = provider_results.get(apaar, ProviderOutcome.NOT_CHECKED.value)
        findings.append(rule_provider_outcome(rn, provider_outcome))

        # VR-013: Study year
        try:
            study_year = int(row.get("current_study_year", 0))
        except (ValueError, TypeError):
            study_year = 0
        findings.append(rule_study_year_valid(rn, study_year, str(row.get("entry_route", ""))))

        # VR-014: Interval order
        findings.append(
            rule_interval_order(
                rn,
                str(row.get("interval_start", "")),
                row.get("interval_end"),
            )
        )

    return findings

