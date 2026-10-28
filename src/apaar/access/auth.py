"""Access and authentication module for APAAR Core.

Provides:
- Dev mock JWT token creation (for testing synthetic actors)
- Token validation middleware
- FastAPI dependencies for authenticated principals
- Role-based access control helpers

IMPORTANT: In development, this module issues simple HS256 JWTs for
synthetic test actors. In production, replace with proper OIDC token
validation against the configured provider's JWKS endpoint.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from apaar.config import get_settings
from apaar.shared.context import TenantContext, set_tenant_context
from apaar.shared.types import InstitutionId, MembershipRole

security = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Dev mock token utilities
# ---------------------------------------------------------------------------


def create_dev_token(
    subject: str,
    roles: list[str],
    institution_id: str | None = None,
    institution_code: str | None = None,
    expires_minutes: int | None = None,
) -> str:
    """Create a development mock JWT for a synthetic test actor.

    This function is for DEVELOPMENT AND TESTING ONLY.
    Production deployments must use the configured OIDC provider.
    """
    try:
        from jose import jwt
    except ImportError as e:
        raise RuntimeError("python-jose is required for dev token creation") from e

    settings = get_settings()
    expires_delta = timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    now = datetime.now(UTC)
    claims: dict = {
        "sub": subject,
        "iss": settings.OIDC_ISSUER,
        "aud": settings.OIDC_AUDIENCE,
        "iat": now,
        "exp": now + expires_delta,
        "roles": roles,
        "synthetic": True,
    }
    if institution_id:
        claims["institution_id"] = institution_id
    if institution_code:
        claims["institution_code"] = institution_code

    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_dev_token(token: str) -> dict:
    """Decode and validate a development mock JWT.

    Validates: issuer, audience, expiry, algorithm.
    """
    try:
        from jose import JWTError, jwt
    except ImportError as e:
        raise RuntimeError("python-jose is required for token validation") from e

    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.OIDC_AUDIENCE,
            issuer=settings.OIDC_ISSUER,
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": f"Invalid token: {e}"},
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ---------------------------------------------------------------------------
# FastAPI dependency: current authenticated principal
# ---------------------------------------------------------------------------


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> TenantContext:
    """FastAPI dependency that validates the Bearer token and returns TenantContext.

    Sets the thread-local tenant context for downstream use cases.
    Raises HTTP 401 if token is missing or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error_code": "UNAUTHORIZED", "message": "Authorization header required."},
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_dev_token(credentials.credentials)

    subject = payload.get("sub", "")
    roles_raw = payload.get("roles", [])
    institution_id_raw = payload.get("institution_id")
    request_id = payload.get("jti", "")

    # Parse roles
    roles: frozenset[MembershipRole] = frozenset()
    valid_roles = set()
    for r in roles_raw:
        try:
            valid_roles.add(MembershipRole(r))
        except ValueError:
            pass  # Unknown roles are dropped silently
    roles = frozenset(valid_roles)

    # Parse institution_id
    institution_id: InstitutionId | None = None
    if institution_id_raw:
        from uuid import UUID
        try:
            institution_id = InstitutionId(UUID(institution_id_raw))
        except ValueError:
            pass

    ctx = set_tenant_context(
        subject_id=subject,
        roles=roles,
        institution_id=institution_id,
        request_id=request_id,
    )
    return ctx


# ---------------------------------------------------------------------------
# Role-based dependency factories
# ---------------------------------------------------------------------------

Principal = Annotated[TenantContext, Depends(get_current_principal)]


def require_roles(*required_roles: MembershipRole):
    """FastAPI dependency factory requiring specific roles."""

    async def _check(principal: Principal) -> TenantContext:
        if not principal.has_role(*required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error_code": "FORBIDDEN",
                    "message": f"Role(s) {[r.value for r in required_roles]} required.",
                },
            )
        return principal

    return _check


Preparer = Annotated[TenantContext, Depends(require_roles(MembershipRole.PREPARER))]
Certifier = Annotated[TenantContext, Depends(require_roles(MembershipRole.CERTIFIER))]
Regulator = Annotated[TenantContext, Depends(require_roles(MembershipRole.REGULATOR))]
Verifier = Annotated[TenantContext, Depends(require_roles(MembershipRole.VERIFIER))]

