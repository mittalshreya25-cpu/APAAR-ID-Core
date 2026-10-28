"""Mock APAAR registry provider.

All interactions with this module produce SYNTHETIC data clearly labelled
with mock provenance. This module NEVER makes live network calls to any
government registry. It is a deterministic fixture-based simulator only.

Every outcome carries `synthetic=True` and the fixture_version so consumers
can distinguish mock assertions from real registry responses.
"""
from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from apaar.config import get_settings
from apaar.shared.types import ProviderOutcome

# ---------------------------------------------------------------------------
# Mock fixture profiles — loaded deterministically from fixture data
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MockProviderResult:
    """Result of a mock APAAR registry check.

    IMPORTANT: This is NOT an official APAAR registry response.
    It is a project-defined synthetic outcome for demonstration purposes.
    """

    outcome: ProviderOutcome
    fixture_version: str
    checked_at: datetime
    synthetic: Literal[True] = True  # Always True — cannot be overridden
    apaar_shape_valid: bool = True
    mock_detail: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "outcome": self.outcome.value,
            "fixture_version": self.fixture_version,
            "checked_at": self.checked_at.isoformat(),
            "synthetic": self.synthetic,
            "apaar_shape_valid": self.apaar_shape_valid,
            "mock_detail": self.mock_detail,
        }


# ---------------------------------------------------------------------------
# Fixture-based deterministic profiles
# The fixture maps a deterministic APAAR prefix bucket to an outcome.
# Using the last 2 digits of the APAAR value to simulate different scenarios.
# NO real APAAR numbers are used or implied.
# ---------------------------------------------------------------------------

_APAAR_SHAPE_RE = __import__("re").compile(r"^\d{12}$")


def _apaar_shape_valid(apaar: str) -> bool:
    """Validate the 12-digit format only — this is NOT registry verification."""
    return bool(_APAAR_SHAPE_RE.match(apaar.strip()))


def _deterministic_outcome(apaar: str, fixture_version: str) -> ProviderOutcome:
    """Determine a reproducible mock outcome for a synthetic APAAR value.

    Distribution (for demo purposes):
    - bucket 0-79  (80%): MOCK_MATCH
    - bucket 80-89 (10%): MOCK_NOT_FOUND
    - bucket 90-94  (5%): MOCK_MISMATCH
    - bucket 95-97  (3%): MOCK_UNAVAILABLE
    - bucket 98-99  (2%): NOT_CHECKED
    """
    # Derive a stable 0-99 bucket from the APAAR+fixture_version hash
    digest = hashlib.sha256(f"{apaar}:{fixture_version}".encode()).hexdigest()
    bucket = int(digest[:4], 16) % 100

    if bucket < 80:
        return ProviderOutcome.MOCK_MATCH
    if bucket < 90:
        return ProviderOutcome.MOCK_NOT_FOUND
    if bucket < 95:
        return ProviderOutcome.MOCK_MISMATCH
    if bucket < 98:
        return ProviderOutcome.MOCK_UNAVAILABLE
    return ProviderOutcome.NOT_CHECKED


# Override profiles: specific APAAR values always return specific outcomes.
# These are invented synthetic identifiers for testing named scenarios.
_OVERRIDE_PROFILES: dict[str, ProviderOutcome] = {
    # All-zeros: always not found (structural edge case demo)
    "000000000000": ProviderOutcome.MOCK_NOT_FOUND,
    # All-nines: always mismatch (data quality error demo)
    "999999999999": ProviderOutcome.MOCK_MISMATCH,
    # Unavailable profile for outage simulation
    "111111111111": ProviderOutcome.MOCK_UNAVAILABLE,
    # Guaranteed match for happy-path testing
    "123456789012": ProviderOutcome.MOCK_MATCH,
    "234567890123": ProviderOutcome.MOCK_MATCH,
    # Guaranteed not-found for ID quality testing
    "987654321098": ProviderOutcome.MOCK_NOT_FOUND,
}


class MockApaarProvider:
    """Synthetic APAAR registry adapter.

    Uses deterministic fixture-based outcomes. No network calls.
    All results are clearly labelled synthetic.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

    def check_sync(self, apaar: str) -> MockProviderResult:
        """Check a synthetic APAAR value against mock fixture profiles synchronously."""
        settings = self._settings
        fixture_version = settings.FIXTURE_VERSION
        checked_at = datetime.now(UTC)
        shape_valid = _apaar_shape_valid(apaar)

        if not shape_valid:
            return MockProviderResult(
                outcome=ProviderOutcome.MOCK_NOT_FOUND,
                fixture_version=fixture_version,
                checked_at=checked_at,
                apaar_shape_valid=False,
                mock_detail="APAAR does not match 12-digit format — shape check only, not registry verification.",
            )

        # Check override profiles first
        if apaar in _OVERRIDE_PROFILES:
            outcome = _OVERRIDE_PROFILES[apaar]
        else:
            outcome = _deterministic_outcome(apaar, fixture_version)

        detail_map = {
            ProviderOutcome.MOCK_MATCH: "Synthetic fixture: identity attributes matched mock profile.",
            ProviderOutcome.MOCK_NOT_FOUND: "Synthetic fixture: APAAR not found in mock profile set.",
            ProviderOutcome.MOCK_MISMATCH: "Synthetic fixture: submitted attributes do not match mock profile.",
            ProviderOutcome.MOCK_UNAVAILABLE: "Synthetic fixture: mock registry unavailable (simulated outage).",
            ProviderOutcome.NOT_CHECKED: "Synthetic fixture: check not attempted for this profile.",
        }

        return MockProviderResult(
            outcome=outcome,
            fixture_version=fixture_version,
            checked_at=checked_at,
            apaar_shape_valid=True,
            mock_detail=detail_map.get(outcome, ""),
        )

    async def check(self, apaar: str) -> MockProviderResult:
        """Check a synthetic APAAR value against mock fixture profiles.

        Args:
            apaar: The 12-digit synthetic APAAR string to check.

        Returns:
            A MockProviderResult with outcome, provenance and timestamps.
        """
        # Simulate configurable artificial delay (for demo realism)
        if self._settings.MOCK_PROVIDER_DELAY_MS > 0:
            await asyncio.sleep(self._settings.MOCK_PROVIDER_DELAY_MS / 1000)

        return self.check_sync(apaar)

    def bulk_check_sync(
        self, apaar_values: list[str]
    ) -> dict[str, MockProviderResult]:
        """Check multiple synthetic APAAR values synchronously."""
        return {apaar: self.check_sync(apaar) for apaar in apaar_values}

    async def bulk_check(
        self, apaar_values: list[str]
    ) -> dict[str, MockProviderResult]:
        """Check multiple synthetic APAAR values.

        Returns a mapping of apaar_value -> result.
        """
        if self._settings.MOCK_PROVIDER_DELAY_MS > 0:
            await asyncio.sleep(self._settings.MOCK_PROVIDER_DELAY_MS / 1000)

        return self.bulk_check_sync(apaar_values)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_provider: MockApaarProvider | None = None


def get_mock_provider() -> MockApaarProvider:
    """Return the module-level MockApaarProvider singleton."""
    global _provider
    if _provider is None:
        _provider = MockApaarProvider()
    return _provider

