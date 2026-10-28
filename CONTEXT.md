# Durable project context

Last reviewed: 28 October 2026. Current stage: research/specification; implementation has not started.

## Purpose and requirements

Build a backend-first APAAR-based institutional enrolment submission, reconciliation and verification prototype for the supplied AICTE problem statement 26263. The complete supplied text has ten requirements: secure upload/update; intake/enrolment/category fields; validation and overlap detection; monitoring; authorized verification; verifiable records; APIs; security/privacy/consent/audit; reports; and APAAR plus local student ID on certificates.

Authoritative design and source citations: [PROJECT_SPEC.md](PROJECT_SPEC.md). Task state: [PHASES_AND_TASKS.md](PHASES_AND_TASKS.md). Current session frontier: [HANDOVER.md](HANDOVER.md). Working instructions: [AGENTS.md](AGENTS.md). Do not duplicate their contents here.

## User preferences and authorization

- User is a solo developer aiming for a substantial learning/resume project and a convincing mentor explanation. Complexity is acceptable when it helps solve the problem; it is not a goal by itself.
- This session's explicit selection: **research and project files first**. No application scaffold, dependencies, database or deployment was authorized as part of this delivery.
- Synthetic data and mock identity verification are the baseline; real registry access is not expected.
- Architecture, stack, guardrails, workflow and explanations belong inside the one master Markdown file. Separate agent instructions, context, phases/tasks and handover were specifically requested.
- Visual UI work follows backend deployment and verified behavior. APIs and report data for monitoring are still required beforehand.
- Continuity files are maintained by agents at task/milestone/session boundaries; they are not runtime hooks or automatic watchers.

## What exists

The two original Claude exports are preserved. Both were read, the ten-page PDF was extracted, and the embedded screenshot was decoded/inspected. Extracted baseline material, role briefs, non-author reviews and machine-readable evidence are under [research/](research/).

The workspace did not contain a Git repository or application source at initial inspection. The Claude-linked detailed report/playbook could not be read through their links. `apaar-core.zip`, v1/v2 reports, deck and scripts are absent. Historical 32-rule/37-test/perfect-accuracy/21k-row-per-second claims are transcript claims only, not current project achievements. Do not assume a recoverable implementation unless actual files appear.

The screenshot shows AICTE Regulation Bureau, Software, Smart Automation, PS26263. An official current online publication matching that identifier was not independently recovered. The full text supplied in the conversation is the requirements baseline.

## Current design decisions

| Decision | State and rationale |
|---|---|
| Product boundary | Enrolment assurance, correction and certification; complement existing identity/award platforms |
| Architecture | Python modular monolith, FastAPI, PostgreSQL, separately restartable same-code worker |
| Proposed baselines | Python 3.13, PostgreSQL 18, Pydantic 2, SQLAlchemy 2, psycopg 3, Alembic; verify/lock at bootstrap |
| Authentication | OIDC with local test actors; scoped server-side membership; migration/runtime identities separate |
| Import semantics | Bounded CSV/JSON; complete-scope replacement revisions and explicit expected base version |
| Reporting populations | Separate current reported and quality-certified snapshots; an adverse new report stays visible even when certification is blocked |
| Replacement identity | Canonical institution/offering/admission-cohort scopes; explicit atomic moves; demo local student IDs never reused |
| Identity | Random internal identity, protected APAAR link with provenance, many temporal enrolment episodes |
| Capacity | Programme/offering/cohort/approval-specific pools; student category is separate from allocation |
| Rules | Reviewed immutable bundles; demo-only until complete applicable evidence is established |
| Certification | Different maker/checker; stable scope locks, later recount, version recheck and atomic snapshot/audit/job |
| Overlaps/anomalies | Explainable restricted review; no automatic fraud decision or blanket concurrent-enrolment ban |
| Signed records | Application-specific synthetic attestations; issuer/signature/status/purpose/provenance checks separate |
| Sharing actors/grants | Fixture-controlled subject/guardian bindings; immutable-snapshot/recipient-bound grants rechecked at every disclosure/download; supersession requires a new decision |
| Reports | Reproducible committed snapshots, explicit freshness and purpose-specific disclosure controls |
| Operations | Synthetic deployment first; real restore/retry/denial evidence before completion claims |

The master's decision register D1–D8 records revisit triggers. These choices are research recommendations; they have not been implemented or accepted as immutable constraints.

## Evidence that changed the baseline

- UGC's modified 2025 guidance permits specified simultaneous study, subject to conditions and relevant council rules. A global unique active APAAR enrolment rule would be unsafe.
- APAAR format is not registry verification; API catalog entries are not credentials, approved purpose or tested contracts.
- NAD already documents award issuance and consent-based verification; no “first universal verification platform” claim is supported.
- Base AICTE rules distinguish ordinary and supernumerary pools, but later amendment/application reconciliation remains incomplete.
- Cryptographic verifiability does not prove the asserted admission is true. A signed demo receipt cannot claim government acceptance.
- DPDP obligations have staged commencement. Exact day-level publication-trigger calculation remains qualified; substantive applicability must be rechecked for deployment. CERT-In is a separate regime.

See the master's bibliography and the five `review_*.md` files for non-author evidence checks. Agreement alone did not resolve unavailable source text.

## Open assumptions and external dependencies

1. Complete applicable 2026–27 AICTE amendments, rounding, category/entry-route eligibility and institution-specific approval evidence are unresolved. Demo policies must remain visibly provisional.
2. Foreign students' identifier eligibility/absence handling needs authorized clarification; do not force a fictional official ID.
3. Live APAAR/ABC/AICTE access, allowed uses, schemas, quotas and integration acceptance are unconfirmed. No live adapter is scheduled before access review.
4. Real operator roles, lawful grounds, issuer authority, guardian assurance, retention and incident obligations need production-specific review. No legal compliance claim is made.
5. Competition team/deadline/pre-built-code rules are unconfirmed; there is no verified finale date or delivery deadline in this plan.
6. Institutional demand, current template mapping and claimed efficiency gains need external validation using blank templates and invented cases, not real student records.
7. Weekly availability, hosting budget/provider and actual environment/tool compatibility have not been established. Phase effort ranges are planning estimates only.

## Updating this file

Change durable facts/decisions here when evidence or implementation changes them. Keep task checklists in the phase file and ephemeral progress in handover. Replace stale statements rather than accumulating a session log. Documentation never authorizes real data collection, paid services or deployment by itself.

## Documentation split — 28 October 2026

User requested isolated working topic files while preserving PROJECT_SPEC.md unchanged. See [docs/README.md](docs/README.md) for navigation and precedence. GitHub repository is https://github.com/mittalshreya25-cpu/APAAR-ID-Core; requested repository-local email is tushardoesstuff@gmail.com. Application implementation remains unstarted.
