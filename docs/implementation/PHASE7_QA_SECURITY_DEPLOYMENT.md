# Phase 7 — QA, Security Review and Deployment Preparation

## Implemented in this phase
- Added candidate-to-employer application linking for administrator-approved employer job posts.
- Added an employer application inbox limited to the authenticated employer's own approved job posts.
- Added employer review status updates and private employer notes.
- Candidate applications can be linked to a job post only when that post is approved.
- Added an end-to-end API integration test covering employer registration, pending job submission, admin approval, candidate application, employer inbox visibility, and employer review.
- Preserved previous resume matching, skill gap, account, moderation and audit features.

## Tests executed
- Python unit/integration suite: 29 passed.
- Python source compilation: passed.
- API workflow smoke test: employer job submission → admin approval → candidate application → employer inbox → status update succeeded.
- Role access check: candidate access to employer inbox was denied (HTTP 403).
- Frontend production build: not completed in this environment because `npm ci` did not finish and Vite was unavailable. Run the frontend build locally.

## Run and verify locally

Backend (project root):

```bash
pip install -r requirements.txt
python run.py
```

Frontend (second terminal):

```bash
cd frontend
npm ci
npm run build
npm run dev
```

If there is no `package-lock.json`, use `npm install` instead of `npm ci`.

## Deployment checklist
- [ ] Build frontend and run manual browser tests for candidate, employer and admin.
- [ ] Use HTTPS in deployment.
- [ ] Replace wildcard CORS origins with the deployed frontend origin.
- [ ] Set a strong `ITI_ADMIN_BOOTSTRAP_KEY` only for initial admin creation; remove it afterwards.
- [ ] Configure a persistent database volume or managed database and test backups/restoration.
- [ ] Add API rate limiting, request-size limits, monitoring and alerting.
- [ ] Review bearer-token storage in localStorage and XSS risks; consider secure HttpOnly SameSite cookies.
- [ ] Validate employer identity and vacancy legitimacy; admin approval is an internal review, not independent proof of authenticity.
- [ ] Add privacy notice, data retention/deletion workflows and employer application handling policy.
- [ ] Test keyboard navigation, screen-reader labels, mobile layout and error states.

## Known limitations
- React production build and browser automation were not verified in this execution environment.
- Existing CSV job listings remain unverified demonstration data.
- Employer job-post approval is a moderation state, not third-party verification of employer or vacancy legitimacy.
- Employer application statuses are shared with the candidate through the application record. Employer notes are kept in a separate field and are not included in candidate application list responses.
