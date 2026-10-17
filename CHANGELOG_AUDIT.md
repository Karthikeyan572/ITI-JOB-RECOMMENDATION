# Initial Audit Changes

This file records the changes made to the uploaded project during the first implementation pass.

## Code and data changes

- Standardized the frontend job-match request to use the backend's default minimum threshold of `0.60` and request the agreed default of three recommendations.
- Added FastAPI request validation so `min_threshold` must be between `0.0` and `1.0`, and `top_n` must be between `1` and `10`.
- Corrected `trades.csv` related-trade values so every relationship uses a canonical supported trade name. Removed the COPA-to-Electronics-Mechanic relationship because it could broaden job filtering across unrelated vocational pathways.
- Added a regression test that checks all related-trade values are canonical and verifies the COPA relationship is excluded.
- Added `scripts/audit_datasets.py` to generate a repeatable `DATASET_AUDIT.md` report.

## Verification performed

- Python tests: `16 passed`.
- Python compile check: `python -m compileall -q src scripts tests`.
- Backend smoke test: `GET /api/jobs?limit=3` returned HTTP 200.
- Matching smoke test: `POST /api/match-jobs` returned HTTP 200 with three Electrician recommendations for a valid test profile.
- Frontend production build has not yet been verified in this environment because frontend dependencies were not installed during this pass.

## Remaining data work

- Job records do not include source URLs or verification dates. They must be treated as unverified until their provenance is established.
- 420 unique job-description values repeat across the 1,000 records; this warrants manual review but does not, by itself, prove that a record is false.
- 197 of 210 skill records have empty aliases.
- All 112 course records have empty resource URLs. No URLs were invented.
