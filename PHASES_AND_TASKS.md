# Phases, goals and implementation tasks

Updated: 28 October 2026. **Current delivery: research and project files only.** No application implementation has started. P0 is the research/documentation milestone; P1 is the next implementation phase when authorized.

Use [PROJECT_SPEC.md](PROJECT_SPEC.md) for architecture, rules, contracts and evidence; [CONTEXT.md](CONTEXT.md) for durable decisions; [HANDOVER.md](HANDOVER.md) for the exact frontier; [AGENTS.md](AGENTS.md) for the work loop. Status is evidence-based, not inferred from how detailed this plan looks.

## Goals and scope

- G1: Trace all ten supplied requirements to working, testable behavior.
- G2: Make institutional errors and policy ambiguity actionable without falsely asserting fraud or official identity verification.
- G3: Prove isolation, revision integrity, counting correctness, disclosure limits and recovery before claiming operational quality.
- G4: Deliver a reproducible synthetic backend demonstration and mentor explanation, then a deployed backend; visual UI work follows separately.
- G5: Keep a solo-developer system understandable and adaptable. No complexity, speculative infrastructure or unrelated cleanup for its own sake.

No dated competition promise is assumed. Effort ranges below are rough focused developer hours including learning/debugging; elapsed calendar time depends on availability and external evidence. They are not measured estimates or a fixed deadline. Reestimate after P2.

## Status and dependency rules

Statuses: `PENDING`, `READY`, `IN_PROGRESS`, `BLOCKED`, `DONE`, `DEFERRED`. A task becomes ready when dependencies and authorization are satisfied. Blocked means a concrete missing prerequisite, with a next check; it does not mean abandoned. Do not mark a task done without its named exit evidence.

Core order: P1 → P2 → P3 → P4 → P5 → P6 → P7 → P8. Policy/partner discovery can proceed alongside an authorized mock build, but production enforcement or real integration cannot bypass their gates. Do not auto-start coding from a checked research task.

| Phase | Current state | Dependency | Effort estimate | Outcome |
|---|---|---|---|---|
| P0 Research and blueprint | DONE | Supplied baseline | Completed documentation work; no product hours measured | Corrected specification and continuity pack |
| P1 Foundation and tenant boundary | PENDING; next when authorized | User authorizes implementation | 12–24 h | Locked project, auth actors, real PostgreSQL isolation proof |
| P2 Synthetic ingestion and revision model | PENDING | P1 | 16–28 h | Bounded durable import, mock provider, lossless reconciliation |
| P3 Rules and reproducible evaluation | PENDING | P2 | 18–32 h | Versioned rules, scoped capacity, replayable findings |
| P4 Correction and atomic certification | PENDING | P3 | 18–30 h | Maker/checker and race-safe effective snapshots |
| P5 Review, reports and anomaly reasons | PENDING | P4 | 16–28 h | Restricted overlap review and monitoring/report APIs |
| P6 Sharing, signed records and certificates | PENDING | P4 and P5 access/report policy | 22–38 h | Scoped grants, signed attestations and synthetic certificate support |
| P7 Integration and deployed backend | PENDING | P5–P6 | 20–36 h | Recoverable synthetic hosted API/worker with release evidence |
| P8 Independent challenge and acceptance | PENDING | P7; fixture work starts earlier | 12–24 h plus external review | Reproducible end-to-end evidence and honest limitations |

## P0 — Research and blueprint

- [x] P0.1 Read both exports, inspect screenshot and separate supplied requirements from unseen artifact/build claims. Evidence: extracted baseline files and input hashes in `research/run_manifest.json`.
- [x] P0.2 Conduct five independent research briefs and non-author original-source cross-review. Evidence: five role briefs and five `review_*.md` files; current amendment gaps retained.
- [x] P0.3 Write master specification with architecture, stack, domain/guardrails, operations, evaluation and mentor explanation in one file. Evidence: `PROJECT_SPEC.md` and bibliography/evidence ledger.
- [x] P0.4 Create separate agent instructions, context, phases/tasks and compact handover; validate the delivered pack. Evidence: `research/document_validation.json` and validator outputs. These are documentation checks, not product tests.

Exit: all requested documents exist, local links resolve, bibliography/evidence references reconcile, and no code/deployment success is implied. Policy ambiguities remain explicit rather than being falsely “completed”.

## P1 — Foundation and tenant boundary

**Entry:** implementation authorized; reread current files. First concrete task is **P1.1**.

- [ ] P1.1 Inspect environment and any newly supplied original archive. Select supported compatible dependency versions; create minimal `pyproject.toml`, lockfile, package entry point and developer commands. Do not block a clean build on the missing archive. Record actual versions and reused files, if any.
- [ ] P1.2 Create PostgreSQL migrations for institutions, memberships and the first tenant-owned resource. Separate owner/migration and non-owner runtime roles; explicit grants, tenant-inclusive relationships and forced RLS where appropriate. Review generated migration SQL.
- [ ] P1.3 Configure OIDC local test realm and distinct preparer/checker/regulator/verifier subjects. Verify issuer/audience/time and derive membership server-side. No production keys or real user registration required.
- [ ] P1.4 Add real-PostgreSQL authorization tests: allowed/denied read and write, guessed IDs, missing context, rollback/savepoint, worker transaction and reuse of the same pooled connection across A/B/no tenant. Add a minimal authenticated health/resource contract.

Exit evidence: recorded lockfile/tool versions, successful migration from empty DB, actual-runtime-role negative tests, test-actor setup and exact commands/results. An owner-only or SQLite test does not satisfy isolation. Update context and replace handover.

## P2 — Synthetic ingestion and revision model

- [ ] P2.1 Define the smallest schema for offerings, approval scopes, identity links, enrolment episodes, submission versions and staged rows. Preserve NRI/OCI/FN attributes separately from seat allocation. Use canonical institution/offering/admission-cohort replacements, explicit expected bases, separate reported/certified pointers and stable no-reuse demo episode keys.
- [ ] P2.2 Build a versioned synthetic fixture profile and deterministic mock provider with match/not-found/mismatch/unavailable/not-checked outcomes. All outputs disclose mock/synthetic provenance; no live fallback or reserved-prefix claim.
- [ ] P2.3 Implement bounded UTF-8 CSV/typed JSON ingestion, normalization, row references, private storage ownership and durable job creation. Reject unsupported files and preserve received/rejected/processed reconciliation.
- [ ] P2.4 Implement worker claim/lease/retry/idempotency, submission/job status and paginated errors. Same key/payload yields one logical import; conflicting payload reuse fails. Kill/restart the worker during a fixture import and demonstrate safe recovery.

Exit evidence: one documented import round trip, leading-zero preservation, parser-boundary cases, no dropped rows, repeated-key tests, worker crash/retry result and no cross-tenant artifact access. R1/R2/R7 foundation covered. No 100k-row performance claim before measurement.

## P3 — Rules and reproducible evaluation

- [ ] P3.1 Define rule-bundle schema and allowlisted evaluators. Record authority, applicability, clause/locator, parameters, rounding, severity and remediation. Publish only named demo policies until applicable regulatory evidence is complete.
- [ ] P3.2 Implement schema/ID-shape/within-file duplicates/cross-field/reconciliation checks. Apply the master's mock-outcome action matrix; preserve every reported outcome, distinguish unavailable from invalid and block quality certification appropriately. Test missing-to-added/corrected identity linkage without duplicating the episode.
- [ ] P3.3 Implement approval-linked counting by offering/cohort/entry route and pool. Count each allocated admission once. Keep unknown eligibility/rounding/applicability visible. Include cap −1/exact/+1 and separate-pool examples.
- [ ] P3.4 Pin input/parser/schema/rules/approval/mock/reference-snapshot/code/time evidence for every run. Replay the same evidence and compare structured findings. Rule changes create new runs without rewriting old results.

Exit evidence: source-to-rule table, hand-worked synthetic expected outcomes, boundary and invariance tests, exact replay and explicit unresolved coverage. R3 counting/data-quality foundation covered. Perfect synthetic results must be labelled consistency under the selected demo policy.

## P4 — Correction and atomic certification

- [ ] P4.1 Implement candidate revisions, actionable correction results and preservation of certified history. A complete-scope replacement supersedes the previous population; it never adds its count again.
- [ ] P4.2 Enforce separate authorized maker/checker, current candidate/approval/rule versions and outstanding-blocker policy. Keep reported excess data for review even when certification fails.
- [ ] P4.3 Implement a stable scope lock followed by recount, effective-pointer update, audit and durable receipt job in one short transaction. Route correction, withdrawal and approval changes through the same protocol; document any savepoint/Serializable retry semantics.
- [ ] P4.4 Test concurrent certifications, stale bases, late approval changes, duplicate retries, signing-job failure and withdrawal/correction races. Include certified60/reported61, approval decrease and atomic source/destination episode moves; snapshot certification and receipt readiness are distinct states.

Exit evidence: deterministic concurrency tests with coordinated transactions, self-approval denial, exact supersession totals, preserved failed candidate and safe receipt retry. No “real AICTE acceptance” status is created. R1/R3/R8 certification behavior covered.

## P5 — Review, reporting and explainable anomalies

- [ ] P5.1 Detect temporal cross-institution overlaps through a narrowly authorized central matching operation. Include non-overlap transfers and allowed concurrent-study demo cases; do not add global active-APAAR uniqueness.
- [ ] P5.2 Implement restricted review cases and accountable decisions/reopen history. Protect counterpart details, deny direct membership lookup and test guessed-submission probing/rate boundaries.
- [ ] P5.3 Implement institution/regulator intake, quality and case-status report APIs. Show latest reported versus certified populations, gaps and unallocatable/ambiguous rows; include snapshot/filters/policy versions/as-of/freshness, reconcile totals and control exact vs suppressed data by audience.
- [ ] P5.4 Add advisory anomaly reasons and a small fixed report catalogue. Test complementary totals, overlapping queries, exports and snapshot-difference inference. ML remains deferred unless a frozen challenge comparison justifies it.

Exit evidence: report reconciliation, review lifecycle, object/field authorization matrix, leakage cases and documented freshness measurements. R3/R4/R9 behavior is exposed through APIs; visual UI remains deferred.

## P6 — Permissioned verification, signed records and certificate support

- [ ] P6.1 Implement purpose/recipient/field/immutable-snapshot-limited verification requests, server-controlled synthetic subject/guardian bindings, expiry and withdrawal. Authenticate the named recipient on redemption/download; supersession requires a new decision. Institution approval cannot substitute for student sharing. Log actual disclosures without copying fields into audit logs.
- [ ] P6.2 Implement a documented application-specific signed attestation format, trusted synthetic issuer/key registry and separate structure/signature/issuer/time/status/purpose/provenance results. Choose maintained signing libraries and fixed algorithms; no W3C conformance claim.
- [ ] P6.3 Implement supersession/revocation, status-unavailable behavior, routine key rotation and a compromised-key exercise. Distinguish grant revocation, record revocation, enrolment cancellation and key compromise.
- [ ] P6.4 Implement issuing-body certificate data/stamp contract and an explicitly synthetic sample with APAAR and local student ID. QR uses an opaque reference with access controls, not a plaintext student dossier or identifier password.

Exit evidence: approved/refused/expired/withdrawn/wrong-audience flows; tamper/unknown-issuer/key/status checks; both certificate identifiers and issuing authority tests. Previously downloaded files are not claimed to be recalled. R5/R6/R8/R10 covered.

## P7 — Integration, operations and deployed backend

- [ ] P7.1 Freeze reviewed OpenAPI/import/export contracts and test a synthetic institution adapter. Add an outbox/webhook only for an actual consumer; prove bounded retries and deduplication. No speculative SFTP/ERP/live-government connector.
- [ ] P7.2 Add redacted logs/metrics, queue and receipt monitoring, controlled migrations, dependency checks and CI under real runtime-role PostgreSQL. Document audit threat limits and checkpoint verification.
- [ ] P7.3 Select host/region/operator/budget and deploy the synthetic API/worker with private storage/DB boundaries. Assess operational accounts/logs and incident responsibilities. Do not provision paid resources without authorization.
- [ ] P7.4 Restore into a clean environment; reconcile snapshots, key/status availability and retried effects. Measure provisional RPO/RTO and full-path performance/freshness, including failures and constraints enabled.

Exit evidence: actual deployment identifier, end-to-end synthetic flow, CI output, permission matrix, restart/restore drill, measured resource/latency report and known limitations. Health endpoint success alone does not complete this phase. Backend deployment is the earliest point for a separately requested visual UI phase.

## P8 — Independent challenge and acceptance

- [ ] P8.1 Obtain mentor/domain-reviewer-authored synthetic cases and blank template mapping; freeze expected outcomes before release evaluation. If no reviewer is available, state developer-authored evaluation and retain the independent-validation gap.
- [ ] P8.2 Run deterministic, adversarial and stochastic suites; report per-rule denominators, ambiguous coverage, false alerts and ranking workload. Include legitimate near-misses and representative mutations/faults.
- [ ] P8.3 Execute the master's five-minute demonstration from a clean fixture reset. Save reproducibility metadata, actual commands/results and a ten-requirement evidence map.
- [ ] P8.4 Review unresolved policy/access/legal/competition questions. Keep synthetic-only claims unless gates are separately satisfied. Update context, task state and handover with actual delivered behavior and residual risks.

Exit evidence: reproducible acceptance pack and candid mentor/resume wording. Do not use an aggregate accuracy number, absent baseline benchmarks or national-scale claims as a substitute for this evidence.

## External gates and continuing research

| Gate | Blocks | Required evidence / next check |
|---|---|---|
| Applicable intake policy | Production policy certification | Complete original amendment chain, course/year approval, rounding/eligibility interpretation and non-author domain review |
| National integration | Any live adapter or official acceptance claim | Approved partner use, credentials, contract, schema, purpose and operational responsibilities |
| Real data/issuance | Real student processing or real credential claim | Explicit authorization, appropriate legal/security review, identity/guardian/issuer assurance, retention and incident plan |
| Competition eligibility | Competition-specific claims/submission | Applicable official rulebook, dates, team/pre-built-code permissions confirmed by organizer |
| Visual UI | Visual design work | Deployed, verified backend plus a user request and UI references; no UI framework is mandated yet |

These gates do not block the authorized synthetic prototype. A source becoming available does not itself authorize real data, costs or deployment.

## Maintenance protocol

When a task starts, mark it `IN_PROGRESS` with the exact active unit in handover. On completion, check it only after exit evidence exists and link that evidence beside the task or phase. On a blocker, record what is missing and the smallest next check; continue unaffected authorized tasks. Revise estimates based on measured progress.

At each meaningful milestone/session boundary: update durable decisions in `CONTEXT.md`, statuses/evidence here, and replace `HANDOVER.md` in at most 120 lines. Update the master specification when a contract or consequential design changes. No automatic process updates these files; the active agent performs the maintenance. Current next action is to begin P1.1 only after implementation is authorized.
