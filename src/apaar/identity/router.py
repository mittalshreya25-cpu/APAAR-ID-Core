"""API router for identity verification against the mock APAAR registry."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from apaar.access.auth import get_current_principal
from apaar.identity.mock_provider import get_mock_provider
from apaar.shared.context import TenantContext
from apaar.validation.rules import validate_apaar_shape

api_router = APIRouter(tags=["identity"])


class IdentityCheckRequest(BaseModel):
    apaar_id: str


class IdentityCheckResponse(BaseModel):
    apaar_id: str
    shape_valid: bool
    outcome: str
    fixture_version: str
    checked_at: str
    synthetic: bool = True
    detail: str
    disclaimer: str = (
        "MOCK PROVENANCE: This check was performed against synthetic fixture profiles. "
        "It does NOT call an official government registry. "
        "A 12-digit format check proves shape only, not registry membership."
    )


@api_router.post("/check", response_model=IdentityCheckResponse, summary="Check synthetic APAAR with mock provider")
async def check_identity(
    body: IdentityCheckRequest,
    principal: Annotated[TenantContext, Depends(get_current_principal)],
) -> IdentityCheckResponse:
    """Evaluate synthetic APAAR against deterministic mock fixture profiles.

    All results clearly state mock/synthetic provenance.
    No live government API is ever called.
    """
    apaar = body.apaar_id.strip()
    shape_valid = validate_apaar_shape(apaar)

    provider = get_mock_provider()
    result = await provider.check(apaar)

    return IdentityCheckResponse(
        apaar_id=apaar,
        shape_valid=shape_valid,
        outcome=result.outcome.value,
        fixture_version=result.fixture_version,
        checked_at=result.checked_at.isoformat(),
        synthetic=True,
        detail=result.mock_detail,
    )
