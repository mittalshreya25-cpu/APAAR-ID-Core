"""Domain type definitions for APAAR Core.

All APAAR identifiers in this codebase are synthetic twelve-digit strings used
for demonstration purposes only. They are not official APAAR registry identifiers.
"""
from __future__ import annotations

import enum
from typing import NewType
from uuid import UUID

# ---------------------------------------------------------------------------
# ID wrapper types (NewType over UUID for type safety)
# ---------------------------------------------------------------------------

InstitutionId = NewType("InstitutionId", UUID)
SubmissionId = NewType("SubmissionId", UUID)
StudentKey = NewType("StudentKey", UUID)  # internal random key — NOT APAAR
EpisodeId = NewType("EpisodeId", UUID)
JobId = NewType("JobId", UUID)
OfferingId = NewType("OfferingId", UUID)
ApprovalId = NewType("ApprovalId", UUID)
AttestationId = NewType("AttestationId", UUID)
ValidationRunId = NewType("ValidationRunId", UUID)
ReviewCaseId = NewType("ReviewCaseId", UUID)
GrantId = NewType("GrantId", UUID)
AuditEventId = NewType("AuditEventId", UUID)

# Academic year string e.g. "2024-25"
AcademicYear = NewType("AcademicYear", str)

# ---------------------------------------------------------------------------
# Provider outcome — result of mock APAAR registry check
# ---------------------------------------------------------------------------


class ProviderOutcome(str, enum.Enum):
    """Outcome of a mock APAAR registry verification.

    These are project-defined labels, NOT official API response codes.
    A provider outage produces MOCK_UNAVAILABLE — not an invalid student.
    """

    MOCK_MATCH = "MOCK_MATCH"
    MOCK_NOT_FOUND = "MOCK_NOT_FOUND"
    MOCK_MISMATCH = "MOCK_MISMATCH"
    MOCK_UNAVAILABLE = "MOCK_UNAVAILABLE"
    NOT_CHECKED = "NOT_CHECKED"

    @property
    def blocks_certification(self) -> bool:
        """True if this outcome prevents quality certification."""
        return self in (
            ProviderOutcome.MOCK_NOT_FOUND,
            ProviderOutcome.MOCK_MISMATCH,
        )

    @property
    def requires_review(self) -> bool:
        """True if this outcome requires manual review before certification."""
        return self in (
            ProviderOutcome.MOCK_UNAVAILABLE,
            ProviderOutcome.NOT_CHECKED,
        )


# ---------------------------------------------------------------------------
# Submission lifecycle
# ---------------------------------------------------------------------------


class SubmissionStatus(str, enum.Enum):
    """Lifecycle state of a submission/revision candidate."""

    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    READY_FOR_CERTIFICATION = "READY_FOR_CERTIFICATION"
    CERTIFIED = "CERTIFIED"
    PROCESSING_FAILED = "PROCESSING_FAILED"

    @property
    def is_terminal(self) -> bool:
        return self in (SubmissionStatus.CERTIFIED, SubmissionStatus.PROCESSING_FAILED)

    @property
    def can_certify(self) -> bool:
        return self == SubmissionStatus.READY_FOR_CERTIFICATION


# ---------------------------------------------------------------------------
# Validation finding outcome
# ---------------------------------------------------------------------------


class FindingOutcome(str, enum.Enum):
    """Outcome of a single rule evaluation against a row/submission."""

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNAVAILABLE = "UNAVAILABLE"

    @property
    def is_blocking(self) -> bool:
        """FAIL and REVIEW_REQUIRED block quality certification."""
        return self in (FindingOutcome.FAIL, FindingOutcome.REVIEW_REQUIRED)


# ---------------------------------------------------------------------------
# Job status
# ---------------------------------------------------------------------------


class JobStatus(str, enum.Enum):
    """State of a durable background job."""

    PENDING = "PENDING"
    CLAIMED = "CLAIMED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ---------------------------------------------------------------------------
# Review case lifecycle
# ---------------------------------------------------------------------------


class ReviewCaseStatus(str, enum.Enum):
    """State of an overlap/anomaly review case."""

    OPEN = "OPEN"
    IN_REVIEW = "IN_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# ---------------------------------------------------------------------------
# Attestation / signed record status
# ---------------------------------------------------------------------------


class AttestationStatus(str, enum.Enum):
    """Lifecycle state of a signed enrolment attestation."""

    ACTIVE = "ACTIVE"
    SUPERSEDED = "SUPERSEDED"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


# ---------------------------------------------------------------------------
# Student / admission categories
# ---------------------------------------------------------------------------


class EntryRoute(str, enum.Enum):
    """How a student entered a programme."""

    DIRECT = "DIRECT"
    LATERAL = "LATERAL"
    TRANSFER = "TRANSFER"
    READMISSION = "READMISSION"


class StudentCategory(str, enum.Enum):
    """Student admission category for capacity pool evaluation."""

    GENERAL = "GENERAL"
    SC = "SC"
    ST = "ST"
    OBC = "OBC"
    EWS = "EWS"
    NRI = "NRI"
    OCI = "OCI"
    FN = "FN"  # Foreign National
    SUPERNUMERARY = "SUPERNUMERARY"


# ---------------------------------------------------------------------------
# Institution membership roles
# ---------------------------------------------------------------------------


class MembershipRole(str, enum.Enum):
    """Authorized role within an institution."""

    PREPARER = "PREPARER"      # Can stage/correct submissions
    CERTIFIER = "CERTIFIER"    # Can certify (not their own work)
    ANALYST = "ANALYST"        # Read-only reports for this institution
    MAINTAINER = "MAINTAINER"  # Can propose rule bundles
    REGULATOR = "REGULATOR"    # Cross-institution read access (scoped)
    VERIFIER = "VERIFIER"      # External — disclosure view only


# ---------------------------------------------------------------------------
# Allocation pool (which seat pool a student is counted in)
# ---------------------------------------------------------------------------


class AllocationPool(str, enum.Enum):
    """Which approved intake pool an enrolment episode counts toward."""

    ORDINARY = "ORDINARY"
    SUPERNUMERARY = "SUPERNUMERARY"
    NRI = "NRI"
    OCI = "OCI"
    FN = "FN"
    UNRESOLVED = "UNRESOLVED"  # Pool not yet determinable — review required


# ---------------------------------------------------------------------------
# Authority status for rule bundles
# ---------------------------------------------------------------------------


class AuthorityStatus(str, enum.Enum):
    """Evidence status of a rule bundle's regulatory basis."""

    DEMO_ONLY = "DEMO_ONLY"
    PRIMARY_REVIEWED = "PRIMARY_REVIEWED"
    PARTIAL_SOURCE = "PARTIAL_SOURCE"
    UNRESOLVED = "UNRESOLVED"


# ---------------------------------------------------------------------------
# Report audience
# ---------------------------------------------------------------------------


class ReportAudience(str, enum.Enum):
    """Who the report is intended for — controls field suppression."""

    INSTITUTION = "INSTITUTION"
    REGULATOR = "REGULATOR"
    INTERNAL = "INTERNAL"


# ---------------------------------------------------------------------------
# Verification request status
# ---------------------------------------------------------------------------


class VerificationRequestStatus(str, enum.Enum):
    """State of a third-party verification request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    DENIED = "DENIED"
    EXPIRED = "EXPIRED"


# ---------------------------------------------------------------------------
# Programme level and mode
# ---------------------------------------------------------------------------


class ProgrammeLevel(str, enum.Enum):
    UG = "UG"
    PG = "PG"
    DIPLOMA = "DIPLOMA"
    CERTIFICATE = "CERTIFICATE"
    PHD = "PHD"


class ProgrammeMode(str, enum.Enum):
    FULL_TIME = "FULL_TIME"
    PART_TIME = "PART_TIME"
    DISTANCE = "DISTANCE"
    ONLINE = "ONLINE"


class ProgrammeShift(str, enum.Enum):
    MORNING = "MORNING"
    EVENING = "EVENING"
    NA = "NA"


# ---------------------------------------------------------------------------
# Enrolment episode status
# ---------------------------------------------------------------------------


class EpisodeStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    TRANSFERRED = "TRANSFERRED"
    COMPLETED = "COMPLETED"


# ---------------------------------------------------------------------------
# Key status for signing keys
# ---------------------------------------------------------------------------


class KeyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    ROTATED = "ROTATED"
    COMPROMISED = "COMPROMISED"

