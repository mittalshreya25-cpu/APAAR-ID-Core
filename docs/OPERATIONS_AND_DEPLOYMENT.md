# Operations and deployment

Extracted from the unchanged [PROJECT_SPEC.md](../PROJECT_SPEC.md), 28 October 2026. Proposed behavior, evidence limits and synthetic-only scope are preserved. Citation numbers refer to [Research and sources](RESEARCH_AND_SOURCES.md). See [documentation index](README.md) for maintenance rules.

## Operations, deployment and recovery

Deploy only the synthetic service initially. Select a host, region, budget and operator before provisioning anything. Prefer a simple API/worker deployment with private database networking and managed backups if the chosen budget permits. An India-region choice can help prepare for applicable operational requirements but is not, by itself, proof of legal compliance. Hosting data and OIDC accounts may still contain real operational metadata even with fictional student records.

The CI sequence is dependency installation from lockfile, formatting/lint/type checks, focused unit and property tests, real-PostgreSQL integration tests under runtime credentials, contract snapshot checks and a container build. Security-critical changes also run the relevant permission/concurrency/lifecycle suites. Scan dependencies and protect secrets before a release. Do not run database migrations from every API replica at startup; use one controlled migration step, inspect destructive changes and have a recovery plan.

Observe request errors/latency, job queue age, retries/failures, validation duration, finding rates, certification conflicts, denial rates and report freshness. Use correlation IDs without APAAR, student names, access tokens or sensitive filter values in logs and metric labels. Monitor for stale jobs and unsigned receipts. The audit trail records principal, action, object/version, purpose, before/after references, timestamp and outcome, with sensitive values omitted or separately protected.

An application hash chain can demonstrate that a changed event fails verification relative to a trusted checkpoint. It cannot stop a privileged administrator rewriting both chain and checkpoint in the same database. State that threat limit in the demo. Begin with append-restricted runtime permissions and verifiable exports/checkpoints; stronger independent anchoring or immutable storage needs its own justified requirement. Audit signing keys are not interchangeable with student-record signing keys.

Choose provisional recovery targets of RPO 24 hours and RTO four hours for the synthetic hosted demo, then test and revise them. Back up database, required private artifacts and key-recovery material under separate restricted access. A restore drill must recover into a clean environment, validate schema version and snapshot totals, check key/status availability and replay jobs without duplicated effects. A backup-success message is not a restore test. Restore and delete synthetic datasets independently from operational audit requirements.

Release evidence includes code revision, lockfile, schema/rule/fixture versions, test output, permission matrix, backup/restore result, performance report and known limitations. A deployed API health check alone is not completion of the full product. End-to-end evidence must connect ingestion, validation, correction, certification, reports, disclosure and signature/status checks. Keep UI visual work deferred after this backend milestone; dashboard API correctness still belongs in the evidence.

### Future bootstrap commands

The commands below describe the **Phase 1 developer contract**, after its files and prerequisites have been created. They are not runnable evidence for the current documents-only workspace. No `pyproject.toml`, Compose services, migrations or test suites currently exist. Verify Python/container availability and package compatibility during bootstrap; do not run installs or provision paid services merely because the commands appear here.

```powershell
uv python install 3.13
uv sync --extra dev
docker compose up -d db auth
uv run alembic upgrade head
uv run pytest tests/unit
uv run pytest tests/integration
uv run ruff check .
uv run uvicorn apaar.main:app --host 127.0.0.1 --port 8000
```

The implementation must document separate migration and runtime database identities, local test-actor setup and worker startup when those components exist. Do not copy the migration owner's database URL into the running API. The future first build task is specified in [PHASES_AND_TASKS.md](../PHASES_AND_TASKS.md), with its own artifacts and exit gate.
