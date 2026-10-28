# Product requirements

Extracted from the unchanged [PROJECT_SPEC.md](../PROJECT_SPEC.md), 28 October 2026. Proposed behavior, evidence limits and synthetic-only scope are preserved. Citation numbers refer to [Research and sources](RESEARCH_AND_SOURCES.md). See [documentation index](README.md) for maintenance rules.

## Executive Summary

Build a backend-first platform that helps an institution submit student enrolment data, understand validation findings, correct mistakes and certify a reproducible admission snapshot. A regulator can examine intake reconciliation and restricted overlap cases; an authorized verifier can obtain a purpose-limited signed enrolment statement. The product's proposed contribution is the quality and traceability of these decisions. APAAR supplies academic identity linkage, while NAD already documents academic award issuance and consent-based verification, so rebuilding a national identity service or certificate locker would create substantial overlap. [1](https://apaar.education.gov.in/faqs) [2](https://nad.digilocker.gov.in/about)

The supplied Claude conversation is a useful requirements baseline, but its linked code archive and detailed report are unavailable here. Claims of 32 rules, 37 tests, perfect synthetic accuracy and roughly 21,000 rows per second have not been reproduced. This specification retains the ten supplied requirements and replaces those implementation claims with explicit acceptance criteria.

Three corrections govern the design. Identifier syntax does not prove registry membership. A second enrolment is a review signal because UGC permits specified simultaneous programmes, subject to relevant restrictions. Capacity evaluation must distinguish admission pools, cohort, programme, approval and policy versions; the older handbook alone cannot establish every current permission. [1](https://apaar.education.gov.in/faqs) [6](https://www.ugc.gov.in/pdfnews/6493421_UGC-Guidelines-pursuing-two-academic-programmes-simultaneously.pdf) [7](https://www.aicte.gov.in/sites/default/files/APH%20Final.pdf)

Use a Python modular monolith, FastAPI, PostgreSQL and one durable worker. Start with synthetic data and a mock registry, deterministic explainable rules, tenant isolation, revision history and a correction workflow. Add scoped verification, signed records, reports and a deployed backend before visual UI work. Policy ambiguity must remain visible rather than becoming an invented cap or silent approval. The separate task plan makes each capability testable and defines when context, tasks and handover must be updated.

## Introduction: scope, provenance and success

### What was actually supplied

The two originals are a Markdown conversation export dated 28 October 2026 and a ten-page PDF of the same exchange. Both were read. The embedded screenshot was decoded and visually inspected: it shows problem statement **26263**, AICTE, Regulation Bureau, Software, Smart Automation. The full ten-requirement text occurs in the user's message at 26 October 2026 13:58:50. Its official online publication was not independently recovered during this research. Treat the supplied text as the requirements baseline, rather than inventing an official website citation.

The original v1/v2 documents, `apaar-core.zip`, detailed Claude artifact report, playbook and presentation were not supplied as local files. Attempts to open the linked research report and playbook did not expose their contents. Consequently, the baseline is the conversation and screenshot, not a recovered source repository. [Extracted conversation](../research/baseline_conversation_text.md) and [PDF extraction](../research/baseline_pdf_text.txt) preserve what was actually available; the originals remain unchanged.

The previous work correctly redirected the project toward student-level admissions, recognized the need for privacy and revision history, and adopted mock identity verification. Those choices remain useful. The weakness was treating unverified rule values and unseen implementation results as a foundation for the next milestone. This specification starts the implementation ledger from zero and separates regulatory evidence, design decisions and measured software behavior.

### Product intent and boundaries

The intended users are an institution data preparer, a separate institutional certifier, a regulator analyst, an authorized degree-awarding-body issuer, a student or representative in a permission workflow, and an approved external verifier. One developer may simulate these as distinct test actors; that does not mean one person supplies operational separation of duties in a real institution. The platform records reported admissions and their quality. It does not allocate admission offers, take fees, cancel students, make legal findings or authorize an institution to exceed its approval.

The first usable outcome is an API and command-driven synthetic demonstration: import a bounded file, identify errors, submit a corrected revision, certify a pinned snapshot, expose a reconciled report and issue a narrowly scoped verifiable statement. Visual design is deferred until the backend is deployed and its contracts are stable. Reporting data and dashboard APIs are still required before that milestone; deferring appearance does not remove requirement 4.

Use no actual student records, Aadhaar numbers, scanned identity documents, real issuer credentials or production government endpoints in development. Synthetic twelve-digit strings are demo identifiers, not a claimed reserved APAAR range. Block external registry calls and attach `synthetic=true`, a dataset version and a mock-provider label to all fixtures and exported demo records. This avoids suggesting that a plausible-looking number was issued by the national registry.

### Observable success

Success means a new developer can execute the phase plan without guessing the trust model or claiming unfinished work. Product success, once implemented, means ten supplied requirements have observable behavior and evidence: isolated tenants; reproducible validation; correct scoped counting; accountable correction; limited disclosure; signed bytes with issuer/status checks; and recoverable operations. It does not mean winning a competition, universal regulatory compliance, national identity coverage or an unmeasured speed improvement.

### Requirements traceability

| ID | Supplied requirement | Designed capability | Implementation evidence required |
|---|---|---|---|
| R1 | Secure student upload/update keyed by APAAR | Authorized CSV/JSON staging; revisioned identity links and enrolments | Cross-tenant denial, idempotent retry and correction tests |
| R2 | Intake, enrolment, supernumerary, NRI, OCI, FN and relevant fields | Versioned approval/seat pools plus separate student attributes | Round-trip schema and reconciled count examples |
| R3 | Duplicate, missing/invalid ID, excess intake, inconsistency and overlap detection | Deterministic rule findings and restricted review cases | Independent challenge set, boundary and concurrency tests |
| R4 | Institution/regulator monitoring dashboards | Authorized aggregate/report APIs with snapshot and freshness metadata | Reconciliation and leakage tests; visual client later |
| R5 | Secure stakeholder verification | Authenticated, purpose-scoped disclosure request and decision | Denied, expired, withdrawn and wrong-audience requests |
| R6 | Verifiable student records | Signed synthetic enrolment attestation, version and status | Tamper, issuer, key, expiry and supersession checks |
| R7 | Integration APIs | OpenAPI, versioned imports/exports; delivery outbox when needed | Consumer contract and replay tests |
| R8 | Security, privacy, auth, RBAC, audit and consent | Trust-boundary controls described below | Negative authorization, audit and permission lifecycle tests |
| R9 | Policy/accreditation/regulatory reports | Reproducible report snapshots and controlled exports | Same snapshot yields same totals; privacy-safe aggregates |
| R10 | APAAR plus student ID on certificates | Issuer-authorized certificate data/stamp contract and synthetic sample | Both identifiers, issuer authority and access-controlled QR flow |

## Synthesis and practical differentiation

The product thesis is **explainable admission-data assurance with reproducible correction and certification**. It links a reported student population to versioned approval evidence, gives institutions actionable fixes and gives regulators a traceable snapshot. Secure verification is a narrow downstream view of that provenance. This is more defensible than claiming a new universal identity registry or the first digital certificate verification platform, functions already documented in the existing ecosystem. [1](https://apaar.education.gov.in/faqs) [2](https://nad.digilocker.gov.in/about)

Its strongest counterargument is institutional duplication: an existing ERP or AICTE workflow could add these checks, and another portal could increase correction effort and privacy exposure. No study in this research establishes market exclusivity, adoption demand or actual time saved. Test the thesis with two admissions/data officers using blank templates and invented records. Ask them to map their current submission process, identify disputed fields and compare correction steps; obtain no student data. A useful API/import integration may matter more than another standalone portal.

For a mentor, use this explanation: “Our project turns institution-reported admissions into a traceable, validated snapshot. It checks data quality and permitted counting pools, explains exceptions, lets an institution correct and separately certify its submission, and shares only an authorized minimal signed statement. We use mock APAAR data and do not claim government API access. We will prove isolation, counting under concurrent changes, revision history and permission withdrawal before polishing the UI.”

The proposed five-minute backend demonstration follows one synthetic institution and one adversarial second tenant. Import a dataset with a malformed ID, repeated row, ambiguous overlap and a demo-pool excess; show the evidence and fixes. Correct the file and show the old version retained. Refuse maker self-certification, certify under a second actor, and show exact report reconciliation. Deny the other tenant's access and an unapproved verifier, then grant a limited disclosure. Modify a signed statement and show verification failure; revoke the grant and show that the next disclosure fails. Display a synthetic certificate sample with both IDs. This is a future acceptance story, not a claim that the demo works today.
