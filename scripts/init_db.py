"""Initialize the database and seed synthetic fixtures (sync engine for fast startup)."""
import datetime
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import sqlalchemy as sa
from sqlalchemy.orm import Session

from apaar.database import Base
from apaar.config import get_settings
import apaar.institutions.models
import apaar.approvals.models
import apaar.identity.models
import apaar.submissions.models
import apaar.validation.models
import apaar.review.models
import apaar.attestations.models
import apaar.reporting.models
import apaar.audit.models
import apaar.worker.models

from apaar.institutions.models import Institution, InstitutionMembership
from apaar.approvals.models import ProgrammeOffering, IntakeApproval
from apaar.shared.types import MembershipRole, AuthorityStatus
from fixtures.synthetic_data import SYNTHETIC_INSTITUTIONS, SYNTHETIC_OFFERINGS, SYNTHETIC_ACTORS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("init_db")


def init_and_seed():
    settings = get_settings()
    sync_url = settings.DATABASE_MIGRATION_URL or "sqlite:///./apaar_dev.db"
    # Ensure sync sqlite url
    if sync_url.startswith("sqlite+"):
        sync_url = "sqlite:///./apaar_dev.db"

    logger.info(f"Connecting to database via {sync_url}...")
    engine = sa.create_engine(sync_url, echo=False)

    logger.info("Creating database tables...")
    Base.metadata.create_all(engine)
    logger.info("Tables created successfully.")

    with Session(engine) as session:
        # Check if already seeded
        existing = session.query(Institution).first()
        if existing:
            logger.info("Database already seeded with institutions.")
            return

        inst_map = {}
        for s_inst in SYNTHETIC_INSTITUTIONS:
            inst = Institution(
                name=s_inst.name,
                code=s_inst.code,
                status="active",
            )
            session.add(inst)
            session.flush()
            inst_map[s_inst.code] = inst

        # Seed offerings and intake approvals
        for s_off in SYNTHETIC_OFFERINGS:
            inst = inst_map.get(s_off.institution_code)
            if not inst:
                continue
            off = ProgrammeOffering(
                institution_id=inst.id,
                campus="Main Campus",
                course_name=s_off.course_name,
                level=s_off.level,
                mode=s_off.mode,
                shift="NA",
                is_active=True,
            )
            session.add(off)
            session.flush()

            approval = IntakeApproval(
                programme_offering_id=off.id,
                institution_id=inst.id,
                academic_year=s_off.academic_year,
                approved_ordinary=s_off.approved_ordinary,
                approved_supernumerary=s_off.approved_supernumerary,
                approved_nri=s_off.approved_nri,
                approved_oci=0,
                authority_status=AuthorityStatus.DEMO_ONLY.value,
                effective_from=datetime.date(2024, 7, 1),
                source_reference="SYNTHETIC DEMO APPROVAL",
            )
            session.add(approval)

        # Seed memberships for synthetic actors
        for actor in SYNTHETIC_ACTORS:
            if actor.institution_code and actor.institution_code in inst_map:
                inst = inst_map[actor.institution_code]
                for role_str in actor.roles:
                    mem = InstitutionMembership(
                        institution_id=inst.id,
                        subject_id=actor.subject,
                        role=MembershipRole(role_str),
                        is_active=True,
                    )
                    session.add(mem)

        # Seed default active RuleBundle
        import hashlib
        from apaar.validation.models import RuleBundle
        yaml_content = "name: AICTE Demo Rules\nrules:\n  - VR-001\n  - VR-002\n  - VR-003\n  - VR-004\n  - VR-005\n  - VR-006\n  - VR-007\n  - VR-008\n  - VR-009\n  - VR-010\n  - VR-011\n  - VR-012\n  - VR-013\n  - VR-014\n"
        bundle = RuleBundle(
            bundle_code="AICTE-DEMO-RULES-2024-V1",
            display_name="AICTE Demo Ingestion & Assurance Rules 2024-25",
            version="1.0.0",
            authority_status=AuthorityStatus.DEMO_ONLY.value,
            rules_yaml_hash=hashlib.sha256(yaml_content.encode()).hexdigest(),
            rules_yaml_content=yaml_content,
            source_references_json=["AICTE Approval Process Handbook 2024-27 (Synthetic demo baseline)"],
            is_active=True,
        )
        session.add(bundle)

        session.commit()
        logger.info("Database successfully seeded with synthetic institutions, demo approvals, and demo rule bundle!")


if __name__ == "__main__":
    init_and_seed()
