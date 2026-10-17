# Data Quality Pass — 2026-10-13 (Round 2)

## Changes
- Added seven trade-specific official Bharat Skills study-material pages for Electrician, Fitter, Welder, Machinist, Electronics Mechanic, Mechanic Motor Vehicle, and COPA. The official pages list trade learning materials; they do not certify synthetic course titles in `courses.csv`.
- Added `job_research_candidates.csv` as a manual verification queue. It includes one reported SAIL Bhilai apprenticeship lead found through a secondary source, with official notice confirmation still pending.
- Kept all candidate leads separate from `jobs.csv`; no unconfirmed lead is represented as a verified or live vacancy.
- Extended `scripts/audit_datasets.py` to report trade-specific learning pages and pending job research leads.

## Research note
- The SAIL Bhilai apprenticeship item is a lead for manual follow-up only. A secondary report states an application deadline of 20 October 2026, but the official SAIL notice was not independently confirmed during this pass. Do not show it as a verified listing until the official notice and application path are confirmed.
- Bharat Skills is an official DGT learning repository. Trade pages were checked on 13 October 2026.

## Continuing limitations
- The original 1,000 jobs remain unverified demonstration data and are not promoted to real vacancies.
- The 112 course-topic rows remain unverified suggestions with empty `resource_url` fields. Official trade learning links are catalogued separately.
