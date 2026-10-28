# Handover — 29 October 2026, Prototype Implementation & Verification

## State

Phases P1 through P6 of the APAAR-Core platform are implemented and verified. All 16 automated tests in the test suite pass cleanly (unit tests and integration flows). Live HTTP server sockets and the interactive UI dashboard have been verified end-to-end.

## What was built and verified

1. **Core Models & Database**: 21 SQLAlchemy 2.0 ORM models in `src/apaar/`; seeded `apaar_dev.db` with synthetic institutions, offerings, demo approvals, and active rule bundle.
2. **Deterministic Mock Provider**: `MockApaarProvider` simulating match, not-found, mismatch, and unavailable scenarios with explicit `synthetic=True` provenance.
3. **Bounded Ingestion**: CSV/JSON parser with leading-zero preservation and schema validation.
4. **Validation Rules (VR-001–VR-014)**: Rule bundle, per-row checks, date bounds, duplicate detection, and capacity pool reconciliation.
5. **Maker/Checker Certification**: Preparers cannot certify their own submissions (`403 SELF_APPROVAL_DENIED`). Racing certifiers on the same scope lock are rejected with `409 Conflict (CERTIFICATION_BLOCKED)`.
6. **Cross-Institution Overlap Review**: Central temporal overlap matching across institutions with counterparty PII suppression and accountable review decision lifecycle (`OPEN` -> `RESOLVED` / `DISMISSED` -> `REOPENED`).
7. **Cryptographic Attestations & Certificates**: JWS compact token issuance and 5-criterion verification; academic certificate records displaying both synthetic APAAR ID and local student ID.
8. **Interactive UI Dashboard**: Served at `GET /` (`static/index.html`) with role switcher, live capacity meters, staging studio, certificate viewer, and JWS verifier.

## Verification evidence

- `pytest tests/`: 16/16 PASSED in 2.3s.
- `scripts/test_live_server.py`: All 12 live HTTP socket operations passed against uvicorn.
- Concurrency test: `tests/integration/test_concurrency_certification.py` passed.
- Overlap review test: `tests/integration/test_overlap_review.py` passed.

## How to run the live application

```powershell
# 1. Run automated test suite
.venv\Scripts\python.exe -m pytest tests/

# 2. Run the live server
.venv\Scripts\python.exe -m uvicorn apaar.main:app --host 127.0.0.1 --port 8000

# 3. Access interactive UI dashboard in your browser
http://127.0.0.1:8000/
```

## Next steps

- Execute P7/P8 deployment hardening and mentor demonstration scripts.
- Synchronize git commits to remote repository origin/main.
