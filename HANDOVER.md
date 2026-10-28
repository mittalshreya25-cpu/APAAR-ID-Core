# Handover — 29 October 2026, Prototype Implementation & Verification

## State

Phases P1 through P6 of the APAAR-Core platform are fully implemented and verified. All 16 automated tests in the test suite pass cleanly (16/16 PASSED). Live HTTP server sockets and the complete interactive UI demo workflow have been verified end-to-end against live Uvicorn on port 8000.

## What was fixed and verified

1. **Offerings Dropdown Population**: Reordered `init()` in `static/index.html` so `switchRole("preparer")` obtains the authenticated Bearer token before `loadOfferings()` queries `/api/v1/approvals/offerings`.
2. **Dev Token Institution Resolution**: Updated `/api/v1/access/dev-token` in `src/apaar/access/router.py` to automatically resolve `institution_code` to the internal `institution_id` in the database when omitted in the request.
3. **Tab & Role Synchronization**: Added active refresh hooks to `setTab('ingestion')` and `switchRole()` to guarantee offerings and dashboard capacity metrics remain in sync.
4. **Batch Staging & Error Handling**: Guarded `submitBatch()` to prevent sending null/empty offering IDs, resolving the `422 Unprocessable Entity` alert.
5. **Character Encoding**: Cleaned up corrupted em-dash and bullet artifacts in `static/index.html`.
6. **Live End-to-End Workflow Test**: Added `scripts/test_ui_workflow.py` validating all 12 browser actions sequentially over real HTTP sockets with 100% success.

## Verification evidence

- `pytest tests/`: 16/16 PASSED in 1.87s.
- `scripts/test_ui_workflow.py`: All 12 browser UI steps passed against live Uvicorn on real HTTP sockets.
- `scripts/test_live_server.py`: All 12 API operations verified over HTTP.
- Concurrency test: `tests/integration/test_concurrency_certification.py` passed.
- Overlap review test: `tests/integration/test_overlap_review.py` passed.

## How to run the live application

```powershell
# 1. Run automated test suite
.venv\Scripts\python.exe -m pytest tests/

# 2. Run the live server with hot reload
.venv\Scripts\python.exe -m uvicorn apaar.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Access interactive UI dashboard in your browser
http://127.0.0.1:8000/
```

## Next steps

- Proceed to mentor demonstration and presentation materials.
- All code committed and pushed to `origin/main` (`5bbebda`).
