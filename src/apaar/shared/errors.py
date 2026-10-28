"""Domain error hierarchy for APAAR Core.

All errors carry an error_code (stable machine-readable string), a human
message and an optional details dict. HTTP mapping is done in the API layer,
not here.
"""
from __future__ import annotations

from typing import Any


class ApaarError(Exception):
    """Base class for all APAAR domain errors."""

    error_code: str = "APAAR_ERROR"

    def __init__(
        self,
        message: str,
        *,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.request_id = request_id
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "request_id": self.request_id,
            "details": self.details,
        }


class NotFoundError(ApaarError):
    """Resource not found or existence-hiding 404."""

    error_code = "NOT_FOUND"


class ForbiddenError(ApaarError):
    """Principal lacks permission for this action/resource."""

    error_code = "FORBIDDEN"


class UnauthorizedError(ApaarError):
    """Request lacks valid authentication."""

    error_code = "UNAUTHORIZED"


class ConflictError(ApaarError):
    """State conflict — version mismatch, duplicate key, etc."""

    error_code = "CONFLICT"


class StaleVersionError(ConflictError):
    """Optimistic locking failure: the expected version does not match current."""

    error_code = "STALE_VERSION"

    def __init__(
        self,
        expected: int,
        actual: int,
        *,
        resource_type: str = "",
        resource_id: str = "",
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            f"Version conflict on {resource_type} {resource_id}: "
            f"expected {expected}, found {actual}.",
            request_id=request_id,
            details={
                "expected_version": expected,
                "actual_version": actual,
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )


class SelfApprovalError(ForbiddenError):
    """A maker attempted to certify their own submission."""

    error_code = "SELF_APPROVAL_DENIED"

    def __init__(self, subject: str, *, request_id: str | None = None) -> None:
        super().__init__(
            "A preparer cannot certify their own submission. "
            "A separate authorized certifier is required.",
            request_id=request_id,
            details={"subject": subject},
        )


class CrossTenantError(ForbiddenError):
    """Attempt to access another institution's resource."""

    error_code = "CROSS_TENANT_DENIED"


class ValidationError(ApaarError):
    """Input failed domain validation (not an HTTP 422 — use 400 for that)."""

    error_code = "VALIDATION_FAILED"


class UploadError(ApaarError):
    """File upload constraint violated (size, type, encoding)."""

    error_code = "UPLOAD_ERROR"


class ProcessingError(ApaarError):
    """Worker/job processing failure — retryable."""

    error_code = "PROCESSING_ERROR"

    def __init__(
        self,
        message: str,
        *,
        is_retryable: bool = True,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, request_id=request_id, details=details)
        self.is_retryable = is_retryable


class PolicyError(ApaarError):
    """Policy or rule bundle evaluation error."""

    error_code = "POLICY_ERROR"


class CertificationBlockedError(ApaarError):
    """Certification cannot proceed due to unresolved blocking findings."""

    error_code = "CERTIFICATION_BLOCKED"

    def __init__(
        self,
        blocking_count: int,
        *,
        request_id: str | None = None,
    ) -> None:
        super().__init__(
            f"Certification blocked: {blocking_count} unresolved finding(s) must be resolved first.",
            request_id=request_id,
            details={"blocking_finding_count": blocking_count},
        )


class IdempotencyConflictError(ConflictError):
    """Same idempotency key used with a different payload."""

    error_code = "IDEMPOTENCY_CONFLICT"


class SigningError(ApaarError):
    """Attestation signing or verification failure."""

    error_code = "SIGNING_ERROR"


class RevocationError(ApaarError):
    """Attempted operation on a revoked/superseded record."""

    error_code = "REVOCATION_ERROR"


class TenantContextMissing(ApaarError):
    """No tenant context was set for this request."""

    error_code = "TENANT_CONTEXT_MISSING"

