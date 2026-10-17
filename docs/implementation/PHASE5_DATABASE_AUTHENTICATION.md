# Phase 5 — SQLite persistence and candidate authentication

## Delivered
- SQLite schema for candidate accounts, sessions, saved jobs and application tracking.
- Password hashing using PBKDF2-HMAC-SHA256 with unique random salts.
- Opaque bearer session tokens, stored as SHA-256 hashes and expiring after 14 days.
- Register, login, current-user and logout endpoints.
- Authenticated saved-job and application endpoints; data is isolated by user ID.
- Application status update endpoint with an allowlist of supported statuses.
- React account form integrated with saved jobs and application tracking APIs.
- Database location configurable using `ITI_DATABASE_PATH`; default `data/iti_portal.db`.
- Database files excluded from version control.

## Verification
- Python unit tests: 26 passed.
- API smoke test: registration (201), `/me` (200), save job (200), list saved jobs, create/list application (200), logout (200).
- Python source compilation passed.
- React production build was not run because frontend dependencies are not installed in the project archive. Run `npm install` (or `npm ci` when a lockfile exists) and `npm run build` from `frontend/`.

## Scope and limitations
- Only the candidate role is enabled. Employer and administrator roles are not implemented.
- SQLite is appropriate for a local prototype; production deployment needs a managed database, backups and a security review.
- The UI stores the bearer token in browser localStorage. Consider an HttpOnly Secure SameSite cookie design and XSS review before public deployment.
- Existing job records are still unverified demonstration data; this phase does not validate live vacancies.
