"""Request-scoped tenant context for APAAR Core.

The tenant context is set once per request after authentication and holds
the institution ID, subject and roles. Worker tasks set their own context
per job. Missing context denies tenant access.
"""
from __future__ import annotations

import uuid
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from apaar.shared.errors import TenantContextMissing
from apaar.shared.types import InstitutionId, MembershipRole

# ---------------------------------------------------------------------------
# Tenant context dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TenantContext:
    """Immutable per-request tenant context.

    Attributes:
        institution_id: The authenticated institution (None for regulators/service accounts).
        subject_id: OIDC `sub` claim — the authenticated principal.
        roles: Set of roles the principal holds.
        request_id: Unique request correlation ID (injected by middleware).
    """

    subject_id: str
    roles: frozenset[MembershipRole]
    request_id: str
    institution_id: InstitutionId | None = None

    def has_role(self, *roles: MembershipRole) -> bool:
        """Return True if the principal holds any of the given roles."""
        return bool(self.roles.intersection(roles))

    def require_role(self, *roles: MembershipRole) -> None:
        """Raise ForbiddenError if the principal lacks all given roles."""
        from apaar.shared.errors import ForbiddenError

        if not self.has_role(*roles):
            raise ForbiddenError(
                f"Role(s) {[r.value for r in roles]} required; "
                f"principal has {[r.value for r in self.roles]}.",
                request_id=self.request_id,
            )

    def require_institution(self) -> InstitutionId:
        """Return institution_id or raise ForbiddenError if absent."""
        from apaar.shared.errors import ForbiddenError

        if self.institution_id is None:
            raise ForbiddenError(
                "An institution-scoped principal is required for this action.",
                request_id=self.request_id,
            )
        return self.institution_id

    def is_regulator(self) -> bool:
        return MembershipRole.REGULATOR in self.roles

    def is_preparer(self) -> bool:
        return MembershipRole.PREPARER in self.roles

    def is_certifier(self) -> bool:
        return MembershipRole.CERTIFIER in self.roles


# ---------------------------------------------------------------------------
# ContextVar storage
# ---------------------------------------------------------------------------

_tenant_ctx: ContextVar[TenantContext | None] = ContextVar("_tenant_ctx", default=None)


def get_tenant_context() -> TenantContext:
    """Return the current tenant context or raise if not set."""
    ctx = _tenant_ctx.get()
    if ctx is None:
        raise TenantContextMissing(
            "No tenant context is available for this operation. "
            "Authentication middleware must set the context before use cases run.",
        )
    return ctx


def get_optional_tenant_context() -> TenantContext | None:
    """Return the current tenant context or None if not set."""
    return _tenant_ctx.get()


@contextmanager
def tenant_context(
    subject_id: str,
    roles: frozenset[MembershipRole],
    institution_id: InstitutionId | None = None,
    request_id: str | None = None,
) -> Generator[TenantContext, None, None]:
    """Context manager that sets and clears the tenant context."""
    ctx = TenantContext(
        subject_id=subject_id,
        roles=roles,
        institution_id=institution_id,
        request_id=request_id or str(uuid.uuid4()),
    )
    token = _tenant_ctx.set(ctx)
    try:
        yield ctx
    finally:
        _tenant_ctx.reset(token)


def set_tenant_context(
    subject_id: str,
    roles: frozenset[MembershipRole],
    institution_id: InstitutionId | None = None,
    request_id: str | None = None,
) -> TenantContext:
    """Set the tenant context and return it (for use in middleware)."""
    ctx = TenantContext(
        subject_id=subject_id,
        roles=roles,
        institution_id=institution_id,
        request_id=request_id or str(uuid.uuid4()),
    )
    _tenant_ctx.set(ctx)
    return ctx

