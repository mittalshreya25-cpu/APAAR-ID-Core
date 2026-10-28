# Durable project context

Last reviewed: 29 October 2026. Current stage: Prototype implemented and verified (Phases P1–P6 complete; Phase P7 integration active).

## Purpose and requirements

Build a backend-first APAAR-based institutional enrolment submission, reconciliation and verification prototype for the supplied AICTE problem statement 26263. The complete supplied text has ten requirements: secure upload/update; intake/enrolment/category fields; validation and overlap detection; monitoring; authorized verification; verifiable records; APIs; security/privacy/consent/audit; reports; and APAAR plus local student ID on certificates.

Authoritative design and source citations: [PROJECT_SPEC.md](PROJECT_SPEC.md). Task state: [PHASES_AND_TASKS.md](PHASES_AND_TASKS.md). Current session frontier: [HANDOVER.md](HANDOVER.md). Working instructions: [AGENTS.md](AGENTS.md).

## User preferences and authorization

- User authorized full project implementation on 28/29 October 2026.
- Strict synthetic data and deterministic mock identity verification baseline maintained across all modules and tests.
- Maker/Checker separation enforced: preparers who submit batches cannot certify their own submissions (`SELF_APPROVAL_DENIED`).
- Interactive UI dashboard served directly at root `/` alongside REST API routers.
- Continuity files are maintained by agents at task/milestone/session boundaries.

## What exists

1. **Python 3.12 Core Application**:
   - `pyproject.toml` and `uv.lock` with FastAPI, SQLAlchemy 2.0, Alembic, psycopg 3, python-jose, greenlet, aiosqlite, pytest.
   - 21 ORM models across 10 modules under `src/apaar/`.
   - Seeded database `apaar_dev.db` with synthetic institutions (`DEMO-INST-001`, `DEMO-INST-002`), offerings, approvals, and demo rule bundle.
2. **Domain Logic & Ingestion**:
   - Bounded CSV/JSON ingestion parser preserving leading zeros (`src/apaar/submissions/parser.py`).
   - Deterministic mock APAAR provider with `synthetic=True` provenance (`src/apaar/identity/mock_provider.py`).
   - Validation rules VR-001 through VR-014 and capacity pool checks (`src/apaar/validation/rules.py`).
3. **Certification & Concurrency**:
   - Maker/checker validation (`SELF_APPROVAL_DENIED`).
   - Atomic scope lock increment and racing certifier rejection (`CERTIFICATION_BLOCKED`).
4. **Review & Cross-Tenant Privacy**:
   - Temporal overlap detector (`src/apaar/review/service.py`) distinguishing non-overlap transfers and permitted concurrent study from conflicting collisions. Counterpart details suppressed to prevent membership oracle leakage.
   - Accountable review decisions lifecycle (`OPEN` -> `RESOLVED` / `DISMISSED` -> `REOPENED`) with audit events.
5. **Attestations & Academic Certificates**:
   - JWS compact signed attestations issued and verified across structure, signature, issuer trust, time, and status.
   - Sample certificate record with dual identifiers (APAAR ID + local student ID) and QR payload.
6. **Frontend & Demonstration**:
   - High-fidelity single-page demonstration app at `static/index.html` (served on `/`).
   - 16/16 automated unit and integration tests passing (`tests/unit/`, `tests/integration/`).
   - Live socket suite (`scripts/test_live_server.py`) verified all 12 live operations over HTTP.

## Current design decisions

| Decision | State and rationale |
|---|---|
| Product boundary | Enrolment assurance, correction and certification; complement existing identity/award platforms |
| Architecture | Python modular monolith, FastAPI, PostgreSQL/SQLite, separately restartable same-code worker |
| Ingestion & Schema | Bounded UTF-8 CSV/JSON, leading zeros preserved as strings; scope lock version increments |
| Mock Provider | Deterministic fixture-based outcomes (MOCK_MATCH, MOCK_NOT_FOUND, MOCK_MISMATCH, MOCK_UNAVAILABLE, NOT_CHECKED); synthetic provenance stamped |
| Certification Protocol | Strict maker/checker separation; racing certifiers rejected with 409 Conflict |
| Overlap & Privacy | Temporal cross-institution overlap detection without global uniqueness; counterparty PII suppressed |
| Attestations | JWS compact serialisation with separate structure/signature/issuer/time/status verification |
| Certificates | Dual identifiers (APAAR ID + local student ID) with opaque QR code payload |

## Open assumptions and external dependencies

1. Complete applicable 2026–27 AICTE amendments, rounding, category/entry-route eligibility and institution-specific approval evidence are unresolved. Demo policies remain provisional.
2. Foreign students' identifier eligibility/absence handling needs authorized clarification; do not force a fictional official ID.
3. Live APAAR/ABC/AICTE access, allowed uses, schemas, quotas and integration acceptance are unconfirmed. No live adapter is scheduled before access review.
4. Real operator roles, lawful grounds, issuer authority, guardian assurance, retention and incident obligations need production-specific review. No legal compliance claim is made.
