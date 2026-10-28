# Data model and ownership

Extracted from the unchanged [PROJECT_SPEC.md](../PROJECT_SPEC.md), 28 October 2026. Proposed behavior, evidence limits and synthetic-only scope are preserved. Citation numbers refer to [Research and sources](RESEARCH_AND_SOURCES.md). See [documentation index](README.md) for maintenance rules.

### Data model and ownership

The table names below define the intended model; no migrations exist yet. Use UUID internal keys, timezone-aware timestamps and explicit version fields. Store academic year/cohort as domain values rather than inferring them from upload time. Count effective snapshots rather than every historical row. All tenant-owned relationships include institution ownership; restricted central identity matching is a separate authorization surface.

| Entity | Essential content and constraints |
|---|---|
| Institution / membership | Synthetic institution reference, active status; authenticated subject, role and authorized scope |
| Programme offering / counting scope | Institution, campus, course, level, mode/shift as relevant; stable lock row for cohort/policy scope |
| Intake approval | Source/authority status, effective dates, institution/offering/year, approved pools, version, supersession |
| Student identity / identity link | Random student key; encrypted APAAR, keyed lookup and key versions; provider evidence; restricted access |
| Enrolment episode | Institution local student ID, student link, offering, entry route, cohort, active interval/status; separate NRI/OCI/FN attributes and allocation evidence |
| Submission / version / staged row | Ownership, scope, expected base, immutable bytes/hash, schema/parser version, row number, declared totals, raw-to-normalized errors |
| Rule bundle / validation run / finding | Immutable policy metadata and parameters; all pinned inputs; operands, outcome, remediation and rule/source references |
| Review case / decision | Authorized case scope, evidence references, state, reviewer, explanation, timestamps and reopen/supersession links |
| Reported / certified snapshot | Separate current pointers for canonical scope; report findings even when certification fails; maker/checker, pinned evidence and receipt state |
| Disclosure request / grant / event | Recipient, purpose, allowed fields, subject/guardian evidence, expiry/revocation and actual disclosure audit |
| Attestation / signing key metadata | Issuer/type, snapshot, signature reference, active/superseded/revoked status; public-key metadata, never private key in a row |
| Job / audit event / export | Lease/retry/effect key; accountable state transitions; private artifact ownership, hash, retention and expiry |

A student can have several episodes, and an institution can have many versions of one episode's representation. Apply the demo's institution-local-ID no-reuse rule without making it globally unique across institutions. Foreign keys and row-local CHECK constraints protect structural integrity; aggregate intake consistency belongs in the certification transaction because PostgreSQL CHECK constraints do not implement arbitrary cross-row invariants. [15](https://www.postgresql.org/docs/18/ddl-constraints.html)

Avoid unnecessary personal fields in the first schema. Use synthetic display name only where the demo needs it; include dates of birth or guardian metadata only for an explicit test purpose. Do not ingest Aadhaar, passports, document images or contact lists. “Foreign passport required by a clause” is not authorization for this prototype to collect passport scans. Keep an evidence reference and an unresolved eligibility state instead.
