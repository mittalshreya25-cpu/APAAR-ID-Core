"""Synthetic fixtures for APAAR Core development and testing.

All data in this module is COMPLETELY INVENTED for demonstration purposes.
No real students, institutions, APAAR identifiers or admission data is used.
All fixtures carry synthetic=True provenance markers.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


# ---------------------------------------------------------------------------
# Synthetic institution profiles
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticInstitution:
    """A completely synthetic institution for demo purposes."""

    code: str
    name: str
    city: str
    state: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "name": self.name,
            "city": self.city,
            "state": self.state,
            "synthetic": "true",
        }


SYNTHETIC_INSTITUTIONS = [
    SyntheticInstitution(
        code="DEMO-INST-001",
        name="Demo Engineering College (Synthetic)",
        city="Demo City",
        state="Demo State",
    ),
    SyntheticInstitution(
        code="DEMO-INST-002",
        name="Synthetic Polytechnic Institute",
        city="Synthetic Town",
        state="Mock State",
    ),
]


# ---------------------------------------------------------------------------
# Synthetic programme offerings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticOffering:
    """A completely synthetic programme offering for demo purposes."""

    code: str
    institution_code: str
    course_name: str
    level: str  # UG / PG / DIPLOMA
    mode: str   # FULL_TIME / PART_TIME
    approved_ordinary: int
    approved_supernumerary: int
    approved_nri: int
    academic_year: str


SYNTHETIC_OFFERINGS = [
    SyntheticOffering(
        code="DEMO-OFF-001",
        institution_code="DEMO-INST-001",
        course_name="B.Tech Computer Science (Synthetic)",
        level="UG",
        mode="FULL_TIME",
        approved_ordinary=60,
        approved_supernumerary=6,
        approved_nri=0,
        academic_year="2024-25",
    ),
    SyntheticOffering(
        code="DEMO-OFF-002",
        institution_code="DEMO-INST-001",
        course_name="B.Tech Mechanical Engineering (Synthetic)",
        level="UG",
        mode="FULL_TIME",
        approved_ordinary=60,
        approved_supernumerary=6,
        approved_nri=3,
        academic_year="2024-25",
    ),
    SyntheticOffering(
        code="DEMO-OFF-003",
        institution_code="DEMO-INST-002",
        course_name="Diploma in Computer Technology (Synthetic)",
        level="DIPLOMA",
        mode="FULL_TIME",
        approved_ordinary=40,
        approved_supernumerary=4,
        approved_nri=0,
        academic_year="2024-25",
    ),
]


# ---------------------------------------------------------------------------
# Synthetic student profiles — COMPLETELY INVENTED
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticStudent:
    """A completely invented student for demo purposes.

    APAAR is a 12-digit synthetic string — not a real APAAR identifier.
    local_student_id is institution-specific and must not be reused.
    """

    apaar: str  # Synthetic 12-digit — NOT a real APAAR
    local_student_id: str
    institution_code: str
    offering_code: str
    category: str
    entry_route: str
    is_nri: bool
    is_oci: bool
    is_fn: bool
    admission_cohort: str
    current_study_year: int
    interval_start: str
    interval_end: str | None = None
    display_name: str = "Synthetic Student"

    def to_row(self) -> dict[str, Any]:
        """Return as a submission CSV row dict."""
        return {
            "local_student_id": self.local_student_id,
            "apaar_id": self.apaar,
            "entry_route": self.entry_route,
            "category": self.category,
            "is_nri": str(self.is_nri).lower(),
            "is_oci": str(self.is_oci).lower(),
            "is_fn": str(self.is_fn).lower(),
            "admission_cohort": self.admission_cohort,
            "current_study_year": str(self.current_study_year),
            "interval_start": self.interval_start,
            "interval_end": self.interval_end or "",
            "display_name": self.display_name,
            # Provenance — always present
            "_synthetic": "true",
            "_fixture_version": "v1",
        }


# Synthetic happy-path students for DEMO-INST-001 / DEMO-OFF-001
SYNTHETIC_STUDENTS_INST1_OFF1 = [
    SyntheticStudent(
        apaar=f"1234{i:08d}",
        local_student_id=f"DEMO-2024-{i:04d}",
        institution_code="DEMO-INST-001",
        offering_code="DEMO-OFF-001",
        category="GENERAL",
        entry_route="DIRECT",
        is_nri=False,
        is_oci=False,
        is_fn=False,
        admission_cohort="2024-25",
        current_study_year=1,
        interval_start="2024-08-01",
        display_name=f"Synthetic Student {i:04d}",
    )
    for i in range(1, 51)  # 50 ordinary students
]

# Supernumerary students
SYNTHETIC_SUPERNUMERARY_STUDENTS = [
    SyntheticStudent(
        apaar=f"9876{i:08d}",
        local_student_id=f"DEMO-SN-2024-{i:04d}",
        institution_code="DEMO-INST-001",
        offering_code="DEMO-OFF-001",
        category="SUPERNUMERARY",
        entry_route="DIRECT",
        is_nri=False,
        is_oci=False,
        is_fn=False,
        admission_cohort="2024-25",
        current_study_year=1,
        interval_start="2024-08-01",
        display_name=f"Synthetic Supernumerary Student {i:04d}",
    )
    for i in range(1, 5)  # 4 supernumerary (within 6 limit)
]

# Error-case students for testing validation rules
SYNTHETIC_ERROR_STUDENTS = [
    # Malformed APAAR (VR-001)
    SyntheticStudent(
        apaar="INVALID-APAAR",
        local_student_id="DEMO-ERR-0001",
        institution_code="DEMO-INST-001",
        offering_code="DEMO-OFF-001",
        category="GENERAL",
        entry_route="DIRECT",
        is_nri=False,
        is_oci=False,
        is_fn=False,
        admission_cohort="2024-25",
        current_study_year=1,
        interval_start="2024-08-01",
        display_name="Error Student (Invalid APAAR)",
    ),
    # Mock NOT_FOUND APAAR
    SyntheticStudent(
        apaar="987654321098",  # Override: always NOT_FOUND
        local_student_id="DEMO-ERR-0002",
        institution_code="DEMO-INST-001",
        offering_code="DEMO-OFF-001",
        category="GENERAL",
        entry_route="DIRECT",
        is_nri=False,
        is_oci=False,
        is_fn=False,
        admission_cohort="2024-25",
        current_study_year=1,
        interval_start="2024-08-01",
        display_name="Error Student (Mock NOT_FOUND)",
    ),
]


# ---------------------------------------------------------------------------
# OIDC synthetic test actors
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyntheticActor:
    """A synthetic OIDC test actor for demo/testing."""

    subject: str  # OIDC sub claim
    display_name: str
    roles: list[str]
    institution_code: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "display_name": self.display_name,
            "roles": self.roles,
            "institution_code": self.institution_code,
            "synthetic": True,
        }


SYNTHETIC_ACTORS = [
    SyntheticActor(
        subject="preparer-inst1@demo.synthetic",
        display_name="Synthetic Preparer (Institution 1)",
        roles=["PREPARER"],
        institution_code="DEMO-INST-001",
    ),
    SyntheticActor(
        subject="certifier-inst1@demo.synthetic",
        display_name="Synthetic Certifier (Institution 1)",
        roles=["CERTIFIER"],
        institution_code="DEMO-INST-001",
    ),
    SyntheticActor(
        subject="preparer-inst2@demo.synthetic",
        display_name="Synthetic Preparer (Institution 2)",
        roles=["PREPARER"],
        institution_code="DEMO-INST-002",
    ),
    SyntheticActor(
        subject="regulator@demo.synthetic",
        display_name="Synthetic Regulator",
        roles=["REGULATOR"],
        institution_code=None,
    ),
    SyntheticActor(
        subject="verifier@demo.synthetic",
        display_name="Synthetic External Verifier",
        roles=["VERIFIER"],
        institution_code=None,
    ),
    SyntheticActor(
        subject="student-001@demo.synthetic",
        display_name="Synthetic Student Subject",
        roles=[],
        institution_code=None,
    ),
]


def get_actor(subject: str) -> SyntheticActor | None:
    """Look up a synthetic actor by OIDC subject."""
    return next((a for a in SYNTHETIC_ACTORS if a.subject == subject), None)

