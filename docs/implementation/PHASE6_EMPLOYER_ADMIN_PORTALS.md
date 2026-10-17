# Phase 6 — Employer and Admin Portals

## Implemented
- Candidate/employer role selection during account registration.
- Employer job-post form and listing view.
- Employer submissions begin in `pending` status and are not publicly listed until approved.
- Employer can close only their own posts.
- Public endpoint lists approved employer job posts: `GET /api/jobs/approved`.
- Admin moderation queue supports approve/reject/close.
- Admin can list registered users and change account roles (cannot change their own role).
- Admin audit log records moderation and role-change actions.
- One-time admin bootstrap endpoint is disabled unless `ITI_ADMIN_BOOTSTRAP_KEY` is configured.
- Existing Phase 5 candidate-only SQLite role constraint is migrated while preserving user rows and foreign keys.

## Admin bootstrap
Set a strong secret in the environment before using the endpoint:

```powershell
$env:ITI_ADMIN_BOOTSTRAP_KEY = "replace-with-a-long-random-secret"
python run.py
```

Then submit `POST /api/admin/bootstrap` with `full_name`, `email`, `password`, and `bootstrap_key`. The endpoint refuses to create an admin if one already exists. Remove the bootstrap secret from the environment after initial provisioning.

## API endpoints
- `POST /api/auth/register` accepts `role: candidate` or `role: employer`.
- `POST /api/admin/bootstrap` creates the initial administrator only when explicitly enabled.
- `POST /api/employer/jobs`, `GET /api/employer/jobs`, `PATCH /api/employer/jobs/{id}/close`
- `GET /api/jobs/approved`
- `GET /api/admin/jobs`, `PATCH /api/admin/jobs/{id}/moderate`
- `GET /api/admin/users`, `PATCH /api/admin/users/{id}/role`

Protected endpoints require `Authorization: Bearer <access_token>` and enforce roles server-side.

## Verification and limitations
- Python test suite and isolated API smoke tests are run for the release.
- React production build should be run locally using `npm install` and `npm run build` in `frontend/`.
- This is a development foundation; perform a security review before public deployment, including CORS, HTTPS, rate limiting, session storage, admin provisioning, audit-log access and backups.
- Employer job posts are separate from the existing unverified sample dataset. Approval means an admin approved the submitted record; it does not independently prove that an employer or vacancy is genuine.
- This phase does not yet provide employer-side candidate applications inbox or full application-to-job-post relationship; current candidate application tracker is built around job IDs.
