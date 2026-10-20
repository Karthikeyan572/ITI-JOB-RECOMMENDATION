# Phase 6 — Employer and administrator portals

## Current behavior

- Candidate and employer roles can be selected during public registration. Admin is not a public registration choice.
- Employer job submissions are created as `pending`; they do not appear in the candidate portal until approved.
- Employers can see and close only their own posts, and can review applications linked to their posts.
- The administrator workspace includes platform counts, job submission moderation (approve/reject/close), and user-role management.
- The site supports one configured administrator identity. The configured email is the only admin identity accepted by protected admin APIs. The user-management screen may change accounts between candidate and employer; it cannot create another admin.
- Admin provisioning is automatic from environment configuration at application startup. There is no public admin bootstrap endpoint.

## Configure the single administrator

Set these environment variables for the service before deploying/restarting it:

| Variable | Required | Purpose |
|---|---:|---|
| `ITI_ADMIN_EMAIL` | Yes | The one administrator's sign-in email. |
| `ITI_ADMIN_PASSWORD` | Yes | The administrator's password (10–128 characters). Keep it in the host's secret/environment settings, not in source code or Git. |
| `ITI_ADMIN_NAME` | No | Display name; defaults to `Administrator`. |

For Render, open the existing web service's **Environment** settings and add the variables there. The values are not part of `render.yaml` or the repository. Save the settings and redeploy/restart the service. Use the same email and password on the regular sign-in screen; the backend routes the configured admin account to the administrator workspace.

At startup, the backend creates the admin account if it does not exist. It stores a salted PBKDF2-HMAC-SHA256 password hash in SQLite, not the plain password. If the configured admin password is changed, the stored hash is updated and that administrator's existing sessions are revoked. Candidate/employer accounts at the configured admin email are not silently promoted; a collision is logged and provisioning fails closed. Admin login and protected admin APIs remain disabled unless the configured account is successfully provisioned.

For local development, set the same variables in a local `.env`/process environment using your chosen environment loader. `.env` files are ignored by Git. Never add real credentials to source files, examples, screenshots, or commits.

## API endpoints

- `POST /api/auth/register` — accepts `role: candidate` or `role: employer` only.
- `POST /api/auth/login` — signs in candidates, employers, and the single configured administrator.
- `POST /api/employer/jobs`, `GET /api/employer/jobs`, `PATCH /api/employer/jobs/{id}/close`
- `GET /api/jobs/approved`
- `GET /api/admin/jobs`, `PATCH /api/admin/jobs/{id}/moderate`
- `GET /api/admin/users`, `PATCH /api/admin/users/{id}/role`

Protected routes require `Authorization: Bearer <access_token>`. Every admin endpoint checks both the admin role and the configured admin email on the backend. Hiding admin navigation in React is only a user-interface behavior and is not used as the access-control boundary.

## Data and operational notes

- The admin review status means an administrator reviewed the submitted data; it does not independently prove a company or vacancy is legitimate.
- The bundled CSV job examples remain unverified and are separate from employer submissions.
- SQLite is selected with `ITI_DATABASE_PATH` and defaults to `data/iti_portal.db`. The deployed service must provide persistent storage if accounts, posts, and applications need to survive replacement of its container/filesystem. The admin account can be recreated from the configured environment on startup; that does not restore other database records.
- Back up the database before changing storage or redeploying.

## Verification

Use the project test suite and `npm run build` from `frontend/`. The API role checks should verify that candidates and employers receive `403` for admin-only actions, the configured administrator can access them, and a different admin-role database record cannot.
