# Guardrails and engineering rules

Extracted from the unchanged [PROJECT_SPEC.md](../PROJECT_SPEC.md), 28 October 2026. Proposed behavior, evidence limits and synthetic-only scope are preserved. Citation numbers refer to [Research and sources](RESEARCH_AND_SOURCES.md). See [documentation index](README.md) for maintenance rules.

## Guardrails and engineering rules

Evidence and flexibility must reinforce each other. A change is welcome when it solves a demonstrated requirement, but it must update the affected contract, rule version and acceptance cases. A new feature does not justify rewriting unrelated modules, adding a distributed system or hiding an unresolved domain question. Keep the smallest implementation that completely handles the authorized behavior, including its security and recovery paths.

The non-negotiable boundaries are: synthetic data and mock identity verification only; no Aadhaar collection; no official integration or government-acceptance claims; no identifier-only disclosure; no automatic fraud verdict from overlaps/anomalies; no editable certified history; no silent policy fallback; no capacity inferred solely from student categories; no self-certification; no cross-tenant access through files/jobs/reports; and no test/benchmark claim without a saved actual result. These are project rules. Specific legal permissions still require appropriate evidence before real deployment.

For every work unit, state the requirement, intended observable behavior, affected trust boundaries and focused checks. Read the current implementation and continuity files first. Make the change, inspect its diff, run the relevant checks, and record actual outcomes. A failed check stays visible. Do not invent a test just to match each line of code; choose tests that could expose a plausible failure. Conversely, authorization, concurrency, policy interpretation and disclosure need explicit adversarial cases because ordinary happy-path checks are insufficient.

Use one decision register inside this file, not an architecture document per feature. When evidence changes, mark a decision superseded with a date and a pointer to its replacement; do not rewrite history to imply the new choice was always established. After a coherent milestone, update the phases/tasks file, durable context and compact handover. These are agent-maintained files, not scheduled processes, self-running hooks or authorization to start unrelated work.

| Decision | Current choice | Revisit trigger |
|---|---|---|
| D1 | Modular monolith plus same-code worker | Measured independent scaling/operational need or separately owned services |
| D2 | Synthetic-only/mock registry | Explicit authorization plus reviewed partner access, purpose, contract and security gates |
| D3 | Complete-scope replacement revisions | A real consumer requires delta semantics and their reconciliation cases |
| D4 | Reviewed demo rules until complete policy evidence | Retrieved amendment chain, course/year approval and independent domain sign-off |
| D5 | Advisory explainable anomalies | Frozen evaluation demonstrates useful incremental statistical/ML performance |
| D6 | Application signed enrolment statements | Interoperability requirement justifies a named credential conformance profile |
| D7 | Backend/report APIs before visual design | Deployed synthetic backend, verified contracts and explicit UI work request |
| D8 | No existing engine assumed | Original archive supplied, audited, reproduced and assessed for reuse |
