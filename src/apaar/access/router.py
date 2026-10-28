"""Access module API router — dev token endpoints and actor info."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from apaar.access.auth import create_dev_token
from apaar.shared.types import MembershipRole

router = APIRouter(tags=["access"])
api_router = router


class DevTokenRequest(BaseModel):
    """Request body for dev token creation."""

    subject: str
    roles: list[str]
    institution_id: str | None = None
    institution_code: str | None = None
    expires_minutes: int = 60


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    subject: str
    roles: list[str]
    synthetic: bool = True


@router.post(
    "/dev-token",
    response_model=DevTokenResponse,
    summary="Create a synthetic dev JWT for testing",
    description=(
        "Development-only endpoint. Creates a mock JWT for a synthetic test actor. "
        "Do not use in production. The token is SYNTHETIC and carries no real authority."
    ),
)
async def create_development_token(body: DevTokenRequest) -> DevTokenResponse:
    """Issue a mock JWT for a synthetic test actor."""
    # Validate roles
    valid_roles = []
    for r in body.roles:
        try:
            MembershipRole(r)
            valid_roles.append(r)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error_code": "VALIDATION_FAILED",
                    "message": f"Unknown role: {r!r}. "
                    f"Valid: {[m.value for m in MembershipRole]}",
                },
            )

    token = create_dev_token(
        subject=body.subject,
        roles=valid_roles,
        institution_id=body.institution_id,
        institution_code=body.institution_code,
        expires_minutes=body.expires_minutes,
    )

    return DevTokenResponse(
        access_token=token,
        expires_in=body.expires_minutes * 60,
        subject=body.subject,
        roles=valid_roles,
    )


@router.get(
    "/actors",
    summary="List synthetic test actors",
    description="Returns the set of pre-defined synthetic OIDC test actors.",
)
async def list_synthetic_actors() -> dict:
    """List synthetic test actors available in dev mode."""
    from fixtures.synthetic_data import SYNTHETIC_ACTORS

    return {
        "actors": [a.to_dict() for a in SYNTHETIC_ACTORS],
        "synthetic": True,
        "note": (
            "These are completely invented synthetic actors for demonstration. "
            "They have no connection to real people, institutions or government identities."
        ),
    }

