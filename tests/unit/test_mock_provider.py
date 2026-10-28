"""Unit tests for synthetic MockApaarProvider."""
from apaar.identity.mock_provider import MockApaarProvider
from apaar.shared.types import ProviderOutcome


def test_mock_provider_deterministic_outcomes() -> None:
    provider = MockApaarProvider()

    # Happy path match profile
    res_match = provider.check_sync("123456789012")
    assert res_match.outcome == ProviderOutcome.MOCK_MATCH
    assert res_match.synthetic
    assert res_match.apaar_shape_valid

    # Override profile: not found
    res_nf = provider.check_sync("987654321098")
    assert res_nf.outcome == ProviderOutcome.MOCK_NOT_FOUND

    # Malformed shape
    res_bad = provider.check_sync("SHORT")
    assert res_bad.outcome == ProviderOutcome.MOCK_NOT_FOUND
    assert not res_bad.apaar_shape_valid


def test_mock_provider_bulk_check() -> None:
    provider = MockApaarProvider()
    results = provider.bulk_check_sync(["123456789012", "987654321098"])
    assert len(results) == 2
    assert results["123456789012"].outcome == ProviderOutcome.MOCK_MATCH
    assert results["987654321098"].outcome == ProviderOutcome.MOCK_NOT_FOUND


