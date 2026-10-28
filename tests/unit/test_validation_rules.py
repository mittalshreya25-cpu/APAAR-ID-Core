"""Unit tests for APAAR Core validation rules (VR-001 through VR-014)."""
import pytest

from apaar.shared.types import FindingOutcome, ProviderOutcome
from apaar.validation.rules import (
    evaluate_submission_rows,
    rule_apaar_shape,
    rule_capacity_check,
    rule_category_valid,
    rule_date_format,
    rule_entry_route_valid,
    rule_interval_order,
    rule_local_student_id_present,
    rule_provider_outcome,
    rule_study_year_valid,
    rule_within_file_duplicate_apaar,
    rule_within_file_duplicate_local_id,
    validate_apaar_shape,
)


def test_apaar_shape_validation() -> None:
    """VR-001: 12-digit numeric validation (shape check only)."""
    assert validate_apaar_shape("123456789012") is True
    assert validate_apaar_shape("000000000000") is True
    assert validate_apaar_shape("12345") is False  # Too short
    assert validate_apaar_shape("1234567890123") is False  # Too long
    assert validate_apaar_shape("12345678901A") is False  # Non-digit
    assert validate_apaar_shape("") is False

    f_pass = rule_apaar_shape(1, "123456789012")
    assert f_pass.outcome == FindingOutcome.PASS

    f_fail = rule_apaar_shape(2, "INVALID")
    assert f_fail.outcome == FindingOutcome.FAIL
    assert f_fail.is_blocking is True


def test_local_student_id_present() -> None:
    """VR-002: Local student ID presence."""
    assert rule_local_student_id_present(1, "STU-001").outcome == FindingOutcome.PASS
    assert rule_local_student_id_present(2, "").outcome == FindingOutcome.FAIL
    assert rule_local_student_id_present(3, "   ").outcome == FindingOutcome.FAIL


def test_duplicate_checks() -> None:
    """VR-003 & VR-004: Duplicate detection within a submission."""
    seen_ids = {"STU-001"}
    assert rule_within_file_duplicate_local_id(1, "STU-001", seen_ids).outcome == FindingOutcome.FAIL
    assert rule_within_file_duplicate_local_id(2, "STU-002", seen_ids).outcome == FindingOutcome.PASS

    seen_apaars = {"123456789012"}
    assert rule_within_file_duplicate_apaar(1, "123456789012", seen_apaars).outcome == FindingOutcome.FAIL
    assert rule_within_file_duplicate_apaar(2, "987654321098", seen_apaars).outcome == FindingOutcome.PASS


def test_entry_route_and_category() -> None:
    """VR-005 & VR-006: Recognized routes and categories."""
    assert rule_entry_route_valid(1, "DIRECT").outcome == FindingOutcome.PASS
    assert rule_entry_route_valid(2, "LATERAL").outcome == FindingOutcome.PASS
    assert rule_entry_route_valid(3, "BOGUS_ROUTE").outcome == FindingOutcome.FAIL

    assert rule_category_valid(1, "GENERAL").outcome == FindingOutcome.PASS
    assert rule_category_valid(2, "SUPERNUMERARY").outcome == FindingOutcome.PASS
    assert rule_category_valid(3, "UNKNOWN_CAT").outcome == FindingOutcome.FAIL


def test_dates_and_intervals() -> None:
    """VR-007, VR-008, VR-014: Date format and order validation."""
    assert rule_date_format(1, "interval_start", "2024-08-01").outcome == FindingOutcome.PASS
    assert rule_date_format(2, "interval_start", "not-a-date").outcome == FindingOutcome.FAIL

    # Order check
    assert rule_interval_order(1, "2024-08-01", "2025-05-31").outcome == FindingOutcome.PASS
    assert rule_interval_order(2, "2025-08-01", "2024-05-31").outcome == FindingOutcome.FAIL


def test_provider_outcomes() -> None:
    """VR-009: Action matrix for mock provider outcomes."""
    f_match = rule_provider_outcome(1, ProviderOutcome.MOCK_MATCH.value)
    assert f_match.outcome == FindingOutcome.PASS
    assert f_match.is_blocking is False

    f_not_found = rule_provider_outcome(2, ProviderOutcome.MOCK_NOT_FOUND.value)
    assert f_not_found.outcome == FindingOutcome.FAIL
    assert f_not_found.is_blocking is True

    f_unavail = rule_provider_outcome(3, ProviderOutcome.MOCK_UNAVAILABLE.value)
    assert f_unavail.outcome == FindingOutcome.REVIEW_REQUIRED
    assert f_unavail.is_blocking is True


def test_capacity_checks_boundary() -> None:
    """VR-010 to VR-012: Capacity pool evaluation at cap - 1, exact, and cap + 1."""
    # Under capacity (59 / 60)
    findings_under = rule_capacity_check(59, 60, 4, 6, 0, 0, "DEMO_ONLY")
    assert all(f.outcome == FindingOutcome.PASS for f in findings_under)

    # Exact capacity (60 / 60)
    findings_exact = rule_capacity_check(60, 60, 6, 6, 0, 0, "DEMO_ONLY")
    assert all(f.outcome == FindingOutcome.PASS for f in findings_exact)

    # Excess capacity (61 / 60) -> REVIEW_REQUIRED under demo policy
    findings_excess = rule_capacity_check(61, 60, 4, 6, 0, 0, "DEMO_ONLY")
    ord_finding = next(f for f in findings_excess if f.rule_id == "VR-010")
    assert ord_finding.outcome == FindingOutcome.REVIEW_REQUIRED

