# API and event contracts

Extracted from the unchanged [PROJECT_SPEC.md](../PROJECT_SPEC.md), 28 October 2026. Proposed behavior, evidence limits and synthetic-only scope are preserved. Citation numbers refer to [Research and sources](RESEARCH_AND_SOURCES.md). See [documentation index](README.md) for maintenance rules.

### API and event contracts

Version endpoints under `/v1`; the following is the proposed contract catalogue. Generate and freeze OpenAPI when implementation exists. Every resource lookup checks action, ownership and allowed fields, including job status and downloads. Do not expose a `GET /students/{apaar}` enumeration endpoint.

| Operation family | Proposed routes | Key behavior |
|---|---|---|
| Reference data | `GET /v1/offerings`, `GET /v1/approvals` | Scoped current/historical approval views; maintainers alone can propose changes |
| Submission | `POST /v1/submissions`, `GET /v1/submissions/{id}` | Stage bounded CSV/JSON; explicit replacement scope; idempotency key; durable job |
| Validation / correction | `POST /v1/submissions/{id}/validation-runs`, `GET /v1/validation-runs/{id}/findings`, `POST /v1/submissions/{id}/revisions` | Pin evidence, paginate errors, create immutable replacement candidates |
| Certification | `POST /v1/submissions/{id}/certifications` | Separate checker, expected version, recomputation, atomic state/audit/job |
| Review | `GET /v1/review-cases`, `POST /v1/review-cases/{id}/decisions` | Scope-specific evidence and accountable resolution; no public overlap search |
| Reports | `GET /v1/reports/intake`, `GET /v1/reports/quality`, `POST /v1/exports` | Snapshot, filters, audience policy, private artifact and freshness watermark |
| Disclosure | `POST /v1/verification-requests`, `POST /v1/verification-requests/{id}/decisions`, `POST /v1/verification-requests/{id}/disclosures`, `POST /v1/grants/{id}/revocations` | Fixture-bound decision actors; immutable snapshot and recipient; redeem/recheck every disclosure/download |
| Signed records | `GET /v1/attestations/{id}`, `POST /v1/attestation-verifications` | Protected retrieval; issuer/signature/time/status/provenance checks returned separately |
| Certificate support | `GET /v1/certificate-records/{id}` | Authorized issuing-body view; both identifiers and opaque QR reference |
| Processing | `GET /v1/jobs/{id}`, health/readiness endpoints | Tenant-safe progress; readiness checks dependencies without exposing secrets |

Asynchronous creation returns a job/resource reference with `202`; validation findings are domain outcomes, not server exceptions. Use `400/422` for malformed contract input, `401` for missing/invalid authentication, `403` or existence-hiding `404` according to a consistent resource policy, `409` for version/idempotency/state conflicts, and `429` for quotas. Return stable error codes, request ID and safe remediation. Avoid revealing whether a foreign tenant's object exists through a different error shape.

Every paginated response has a stable ordering/cursor. Snapshot reports include `snapshot_id`, `as_of`, `generated_at`, rule/approval version references, filters and `data_freshness`. Dashboard data can initially be polled; “real time” means committed updates with a stated freshness target, not instantaneous national registry synchronization. A proposed local target is report freshness within 60 seconds after processing completes. Measure it before advertising it.

Institution adapters use versioned schema mappings and contract fixtures. Add signed outbound webhooks only after a real consumer requirement, with event ID, timestamp, key version, bounded retries and receiver deduplication. Reject stale/replayed inbound requests according to an agreed contract. SFTP, direct ERP connectors and national portal submission are future adapters with named owners and documented access; do not implement speculative connectors just to make an architecture diagram larger.
