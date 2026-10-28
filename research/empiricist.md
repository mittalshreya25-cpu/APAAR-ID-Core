# Empiricist evidence brief — 2026-10-28

Scope: backend-first prototype for AICTE student enrolment assurance, using only invented identities and synthetic institutions. No official APAAR verification, live institutional records, deployment, or implementation was performed. The local baseline conversation is context, not evidence of working software. The claimed archive, 37 passing tests, perfect accuracy, and roughly 21,000 rows/second have not been reproduced here and must not appear as current achievements.

## Finding

The defensible result is an explainable assurance and review workflow whose limitations are measurable. Synthetic fixtures can demonstrate software behaviour under stated policies; they cannot establish that policies match AICTE rules, identify real students, or estimate real-world fraud-detection accuracy. Keep deterministic validation separate from anomaly prioritisation and from cryptographic verification.

## Atomic sourced claims

All sources were accessed 2026-10-28. Excerpts below total at most 25 quoted words per source. Recommendations and numeric targets later in this brief are proposed project decisions, not requirements asserted by these sources.

### EMP-1 — Evaluation needs documented test conditions and independent assessment

**Claim:** NIST's AI RMF includes independent/non-developer assessment, documented test sets and tools, deployment-like conditions, and explicit limits on generalisation.

**Exact excerpt:** “Test sets, metrics, and details about the tools used during TEVV are documented.”

**Source:** [NIST AI RMF Core, §5.3, MEASURE 1.3 and 2.1–2.5](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/), framework released January 2023; live HTML page. Locators: MEASURE table rows 1.3, 2.1, 2.3, 2.5.

**Implication/inference:** A generator and detector authored from the same rules share an oracle. A perfect score is a consistency check, not independent policy validation. A solo developer can seek mentor-authored challenge cases without adding another service or ML dependency.

### EMP-2 — Cryptographic verifiability does not prove factual truth

**Claim:** W3C explicitly separates verifying a credential from determining whether its claims are true.

**Exact excerpt:** “Verifiability of a credential does not imply the truth of claims encoded therein.”

**Source:** [W3C Verifiable Credentials Data Model v2.0](https://www.w3.org/TR/2025/REC-vc-data-model-2.0-20250515/), Recommendation, 15 May 2025. Locators: §1.1, paragraph beginning “The word ‘verifiable’” immediately before §1.2; §2 definition of verification; §5.1 Trust Model.

**Implication/inference:** A signature can show that a configured mock issuer asserted an enrolment snapshot and it was not changed. It cannot establish actual admission, official APAAR identity, or AICTE endorsement. Issuer authorisation and underlying evidence need separate decisions. A successfully verified signature from an unknown or unauthorised issuer must still fail the relying party's acceptance policy.

### EMP-3 — Object authorisation and property authorisation are distinct controls

**Claim:** OWASP calls for permission checks on operations involving object identifiers, and separately recommends limiting exposed and writable properties.

**Exact excerpts:** “Every API endpoint that receives an ID of an object, and performs any action on the object, should implement object-level authorization checks.” / “Allow changes only to the object's properties that should be updated by the client.”

**Sources:** [OWASP API1:2023 Broken Object Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/), 2023 edition, “Is the API Vulnerable?”; [OWASP API3:2023 Broken Object Property Level Authorization](https://api-security.owasp.org/editions/2023/en/0xa3-broken-object-property-level-authorization/), 2023 edition, “How To Prevent”. Exact page publication days are not provided.

**Implication/inference:** A UUID, masked APAAR, authenticated requester, or consent checkbox alone is insufficient. Check tenant, object, action, recipient, purpose, and returned fields. This applies equally to reports, review findings, export download links, background-job status, and certificate verification.

### EMP-4 — Suppressing one small cell can leave its value recoverable

**Claim:** NIST's de-identification guidance explains secondary suppression because a suppressed cell can be reconstructed using marginal totals.

**Exact excerpt:** “These are referred to as secondary suppressions.”

**Source:** [NIST SP 800-188, De-Identifying Government Datasets: Techniques and Governance](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-188.pdf), final, September 2023. Locators: §4.3.3, printed p.53; glossary “suppression”, printed p.108, PDF page 122. §4.3.8, printed pp.57–58, also addresses snapshot-comparison risk.

**Implication/inference:** A rule such as “hide counts below five” is not an anonymity guarantee. Test complementary totals, adjacent time snapshots, and overlapping category queries. Initially expose a small approved report catalogue to authorised roles rather than an arbitrary demographic query builder.

### EMP-5 — Credential-status checking also creates a privacy boundary

**Claim:** W3C's Bitstring Status List describes revocation/suspension and recommends cached retrieval that hides verifier behaviour from the issuer.

**Exact excerpt:** “Verifiers SHOULD cache the retrieved status list”

**Source:** [W3C Bitstring Status List v1.0](https://www.w3.org/TR/2025/REC-vc-bitstring-status-list-20250515/), Recommendation, 15 May 2025. Locators: §2.1 status purposes; §3.2 Validate Algorithm and following caching guidance; §7.2 Validity Periods.

**Implication/inference:** Signature-valid and currently acceptable are different results. Status freshness and unavailable-status behaviour need an explicit policy. The Recommendation does not provide one universal validity period. Pin v1.0 if adopting it; v1.1 dated 21 October 2026 is a Working Draft. A simple internal signed-record status table is adequate for an initial proprietary prototype, but must not be marketed as Bitstring Status List or W3C VC conformance.

### EMP-6 — JWT verification must bind keys to issuers and constrain algorithms

**Claim:** RFC 8725 requires configured algorithm restrictions and, when an `iss` claim is present, validates that the key belongs to the asserted issuer; audience validation is also required in the multi-recipient situation it describes.

**Exact excerpt:** “each key MUST be used with exactly one algorithm”

**Source:** [IETF RFC 8725, JSON Web Token Best Current Practices](https://www.rfc-editor.org/rfc/rfc8725.html), BCP 225, February 2020. Locators: §§3.1, 3.8, 3.9 and 3.12.

**Implication/inference:** If signed records or consent capabilities use JWT, never trust a token-supplied key or algorithm merely because signature verification succeeds. Use an issuer/key allowlist, explicit token types and purposes, and recipient checks appropriate to that token. This RFC concerns JWT; it does not mandate JWT or define a complete credential rotation policy.

## Falsifiable evaluation design

1. **Policy oracle before fixtures:** make a small decision table for each supported academic year/programme/category rule. Record source, clause, effective dates, interpretation, rounding, and a reviewed expected outcome. Unconfirmed policies remain visibly provisional and cannot justify an official-compliance claim. The engine must not generate its own expected labels.
2. **Four distinct suites:** hand-worked boundary examples; independently authored challenge fixtures; broad stochastic synthetic workloads; adversarial lifecycle/security sequences. Different random seeds from the same generator are useful, but do not make the oracle independent.
3. **Challenge-set separation:** ask the mentor/domain reviewer to write or approve cases without reading detector outputs. Freeze fixture and expectation hashes before a release evaluation; freeze threshold choices on a separate development set. Report who authored/reviewed each case and whether blind review actually occurred. Without that reviewer, label this developer evaluation rather than independent validation.
4. **Counterexamples:** include permitted simultaneous study if policy supports it, cancelled/transferred enrolments, non-overlapping dates, delayed updates, a correction submitted twice, exact cap boundary, cap ±1, category combinations and rounding, registry timeout versus a definite unknown ID. Same identifier across institutions creates a potential overlap case; it does not automatically prove illegality or fraud.
5. **Metamorphic properties:** row-order invariance; pagination/batch-size invariance; idempotent replay; adding one valid row changes the correct scoped count by one; cancelling a record affects the relevant active period only. Check that these properties do not silently encode an unverified admission policy.
6. **Deliberate defects in the implementation:** demonstrate that tests catch representative off-by-one caps, missing tenant filters, removed status checks, and silently dropped rows. Record which mutations survive and investigate. A high mutation score alone does not prove correct policy.
7. **Honest metrics:** report per-rule confusion counts and denominators, false alerts per 1,000 legitimate rows, and case-level overlap metrics; one duplicated person can create many row pairs. For review ranking report precision@K, recall@K and review workload. Separate malformed data, known policy violations, unknown/ambiguous cases, and statistical anomalies. Never turn a single “accuracy” number into a fraud claim.
8. **Reproducibility:** preserve code revision, dependency lock, rule version/hash, fixture hash and seed, hardware, database size/indexes, concurrency, cache condition, workload mix, errors, p50/p95/p99 latency, elapsed time and peak memory. Measure upload → durable processing → report readiness, not only an in-memory loop.

## Anomaly prioritisation without decorative ML

**Recommendation, not sourced factual claim:** begin with transparent review reasons: intake utilisation change, an unusual category ratio within a suitably sized comparison group, bursts of corrections, and unresolved overlap frequency. Use a versioned deterministic ranking with reason contributions and observed denominators; an ordinal priority or score is not a probability of fraud. Require minimum group/sample sizes and return “insufficient comparison data” when appropriate.

Keep ranking advisory. A reviewer can clear, request correction, or escalate with a reason and audit event. Deterministic schema/cap checks and human review remain separately visible. Do not automatically reject a student because a score exceeds a threshold.

Only add a statistical/ML challenger after freezing an independently labelled challenge set and a review budget. Compare it against simple rules on held-out institutions and later synthetic periods, including different anomaly prevalences and legitimate institutional changes. Report ranking improvement, false-alert cost, instability, and subgroup differences. Synthetic gains are evidence about those scenarios only; realistic prevalence, labels and generalisation remain unknown. Lack of credible labels is a valid reason to defer ML, not to fabricate ground truth from model output.

## Proposed acceptance targets — unmeasured

These are engineering targets for the project to adopt or revise, not achieved results, official AICTE thresholds, or a claim that finite tests prove security.

| Area | Proposed measurable release gate |
|---|---|
| Mock boundary | All registry responses and generated records carry mock/synthetic provenance; no Aadhaar collection; no route or report claims national identity verification. Reject imports that do not use the documented demo namespace/profile. A profile cannot mathematically guarantee no accidental collision with a real identifier; no live lookup is attempted. |
| Validation oracle | Every supported rule has reviewed boundary cases including valid near-misses; 100% of frozen expected deterministic decisions pass. Report unsupported and disputed policies explicitly. |
| Ingestion and replay | For a 100,000-row synthetic import, reconcile received, rejected, accepted, and superseded rows exactly. Ten repeated requests using the same idempotency key create one logical submission and stable results; conflicting payload reuse is rejected. |
| Overlap review | All frozen overlap/non-overlap date/lifecycle cases pass; no automatic “fraud” finding. Tests distinguish a legitimate retry from two distinct submissions and cancellation from deletion of history. |
| Isolation/RBAC | Every exposed resource has at least one allowed and denied role/tenant case; zero unauthorised object reads, writes, job metadata, exports, or field changes in the matrix, including alternate IDs and download URLs. |
| Consent | A grant records actor, recipient, purpose, fields, expiry and version. A revoked/expired grant blocks the next new verification request. An audit record exists for each successful disclosure. Previously downloaded material cannot be made unreadable by changing the grant. |
| Lookup leakage | Bare-ID and unauthorised requests reveal no record existence or other institution identity through body, error code, result count or download metadata in the test corpus. Compare known/unknown-ID response-time distributions over at least 1,000 requests each; document residual timing evidence instead of promising constant-time behaviour. |
| Aggregate leakage | With a provisional suppression threshold of five, frozen tests cover totals, complementary cells, overlapping filters and snapshot differences; zero reconstructed protected cells in that corpus. The threshold is a project choice; no universal privacy guarantee is claimed. |
| Signed-record lifecycle | Tests reject tampered, unknown-issuer, wrong-purpose, expired/not-yet-valid, revoked and suspended records as defined by policy. Status outage returns “indeterminate/status unavailable”, never a green current-valid result. Test max status staleness against a documented provisional 60-second freshness target. |
| Rotation and compromise | Routine rotation signs new records with the new key while permitted old records remain checkable using archived public keys. Test compromised-key disablement, affected-record revocation/reissue, cache invalidation, and an unrecognised key ID. A self-asserted old issuance timestamp is not proof that a compromised key signed before compromise. |
| Reports/audit | Each report records snapshot, policy version, filters, role and generation time; totals reconcile with that snapshot. Tamper/deletion tests cover the stated audit threat model. A hash chain in one mutable database does not by itself prevent an administrator rewriting the entire chain. |
| Performance | Initial local target: durably ingest and validate 100,000 rows within five minutes on a named machine; ordinary authorised read API p95 under 500 ms at 20 concurrent clients during the documented workload. Publish error rate and memory; revise from measurements rather than advertise national-scale capacity. |

## Failure modes to demonstrate in the backend demo

- A well-formed mock APAAR can be unknown to the mock registry; a registry outage must not become “invalid identity”.
- A valid signature from an untrusted issuer does not produce accepted enrolment assurance; a trusted issuer can still sign false source data.
- An institution's overlap warning can itself become a membership oracle if attackers submit guesses. Restrict it to authorised submission workflows, limit bulk probing, and return a case reference with minimal detail; full counterpart details belong only in the appropriate regulator review scope.
- Suppressed category counts can reappear through a grand total, export, successive snapshot or alternate endpoint. Controls belong in shared report policy, not only UI rendering.
- A signed but public QR payload can leak every embedded field; signatures provide no confidentiality. Use a minimal opaque high-entropy reference/capability with expiry and explicit recipient access as appropriate; never treat a printed APAAR as a password.
- Revocation of consent, revocation of a signed record, cancellation of enrolment, and compromise of a signing key are different state transitions. Tests must cover each and their races.

## Risks, contrary evidence, and limits

Strong synthetic performance can coexist with incorrect regulatory interpretation, unrealistic distributions, missing adversarial behaviour, and real-world false positives. Independent fixture authorship reduces one source of circularity; it cannot substitute for official policy clarification or an authorised real-world pilot.

ML might improve discovery of patterns that deterministic rules miss; rejecting it categorically would be unjustified. The present recommendation is to require demonstrated incremental value and an honest evaluation before accepting its extra complexity.

Some authorised regulatory reporting may require exact small counts. Suppression should follow audience/purpose policy rather than destroying useful internal data. Minimum disclosure externally and controlled exact data internally are separate access decisions. No Indian legal compliance conclusion is made by applying NIST or OWASP technical guidance.

W3C VC adoption can improve interoperability, but it brings a conformance and issuer-governance obligation. A signed JSON receipt with transparent provenance is a defensible first milestone; claiming a national credential or official integration without access is not.

No backend, benchmark, tests or independent field validation were executed in this investigation. EMP-1–EMP-6 received the non-author source review linked below; that source review is not software or field validation.

## Author response to non-author review — 2026-10-28

Read [Insider's independent review](review_empiricist.md). Accept and correct the EMP-2 source locators: the exact truth quote appears in VCDM §1.1 immediately before §1.2, the verification definition is in §2, and Trust Model is §5.1. EMP-4 now uses the inspected publication month, September 2023, rather than an exact publication day. Added the reviewer-identified §4.3.8 snapshot-risk locator and made EMP-6's `iss` condition explicit.

The core findings and their limits stand. NIST's evaluation framework and the cited technical/privacy guidance are not Indian regulatory mandates; the acceptance table remains unmeasured project targets. W3C conformance requirements and RFC JWT requirements apply within their respective adopted formats and protocols, not automatically to every proprietary signed receipt. Caching alone does not hide retrieval behaviour; EMP-5's independent retrieval/privacy policy remains necessary. No current legal-compliance, test-pass, benchmark or real-world accuracy claim is created by this response. The non-author reviewer retains review authority over the corrections.
