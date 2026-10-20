# Project Report: ITI Skill Gap and Job Recommendation System

**Report date:** 20 October 2026  
**Repository:** `D:\git\AI-SkillGap-System`  
**Report basis:** Current local working tree, including uncommitted changes. This report describes what the code currently does; it does not claim that the same state is deployed on Render.

## 1. Executive summary

This project is a web prototype intended to help Industrial Training Institute (ITI) candidates understand how their resume aligns with trade-related job examples. It reads PDF or DOCX resumes, extracts a candidate profile, checks whether the document contains a recognizable ITI trade, compares that profile to a local job dataset, explains matching and missing skills, and suggests learning topics. It also has candidate account features and a separate employer workspace for publishing job posts and handling applications.

The main value is the end-to-end workflow: resume → profile validation and review → ranked job matches → skill-gap explanation and learning suggestions → saved/application tracking. Employers have a separate sign-in role and can publish listings and review applicants. The home page displays posts submitted in this portal and links to official job and training sites.

It is a prototype, not a verified job-market service. The 1,000 bundled job rows have no source or application URLs and are classified in the dataset as unverified examples. Learning recommendations are topic suggestions; all 112 bundled course rows have no resource URL. The home page does not ingest live market news or scrape job sites. It refreshes employer-submitted portal posts and links users out to source websites.

The current working tree includes a restored administrator portal. It is a single-admin design: the configured email is provisioned from deployment environment settings, while its password is hashed in SQLite. The changes are local and uncommitted; the portal will not appear on the Render website until the code is pushed/deployed and the matching environment settings are configured there.

## 2. Purpose and intended users

### Candidate

A candidate can create an account, upload a resume, review extracted ITI details, inspect job matches, see matching and missing skills, save roles, and track applications. A sign-in is required before using the application.

### Employer

An employer can create an employer account, submit an ITI role for administrator review, view and close their own listings, see applications associated with their approved posts, update application progress, and keep private review notes.

### Administrator

The administrator portal supports an overview, employer-job moderation (approve/reject/close), and user account role management. Only the single email configured as `ITI_ADMIN_EMAIL` may sign in as the administrator and pass admin API checks. The corresponding `ITI_ADMIN_PASSWORD` is used to seed/update a user with a salted PBKDF2-HMAC-SHA256 hash. Admin registration is unavailable publicly, role management cannot create another administrator, and password rotation invalidates existing admin sessions. If the environment variables are absent, invalid, or collide with an existing non-admin account, administrator access is disabled.

## 3. What the application does

### 3.1 Authentication and session handling

- The sign-in / registration screen is shown before the protected workspace.
- Registration accepts candidate and employer account types.
- Passwords are stored as PBKDF2-HMAC-SHA256 hashes with per-user random salts.
- Session tokens are random bearer tokens; the database stores token hashes and expiration timestamps.
- Saved jobs and application records are associated with a signed-in user.
- The browser keeps the bearer token in local storage. This is practical for a project prototype, but it requires a security review before public production use.
- The administrator identity is provisioned at backend startup from `ITI_ADMIN_EMAIL`, `ITI_ADMIN_PASSWORD`, and optional `ITI_ADMIN_NAME`; secrets are not embedded in frontend code or committed to Git.

### 3.2 Resume upload, extraction, and validation

Supported resume formats are PDF and DOCX. The parser extracts document text, then heuristic extraction logic attempts to identify a candidate name, ITI trade, skills, experience, qualifications, and certifications. Skills are normalized against a canonical taxonomy and aliases, with fuzzy matching used for likely variants.

The validation flow distinguishes:

- **Valid ITI profile:** a specific supported ITI trade is identified.
- **Trade unclear:** ITI or vocational evidence exists but a specific trade could not be determined; the candidate can select a trade.
- **Not ITI:** there is no specific trade and insufficient ITI evidence.
- **Not a resume:** academic survey/research content or insufficient document content is rejected from matching.

Generic computer-science terms are not intended to classify a candidate as COPA without ITI evidence. The extractor is rule-based and depends on how information is written in the document; it is not a human credential verifier. Scanned/image-only PDFs may not yield readable text because OCR is not part of the described parsing path.

### 3.3 Job matching and recommendation

Matching is restricted to the local job records and compatible trades. Unrelated trades are filtered out by default. The score is composed as follows:

- Skills: **50%** of total score. Its internal score combines **70% weighted skill overlap** and **30% text similarity** using TF-IDF cosine similarity.
- Trade compatibility: **25%**. Exact trade match receives full credit; configured related trades receive partial credit.
- Experience: **15%**. Meeting the minimum gives full credit; below-minimum experience receives a proportional score. Entry-level roles receive full credit on this component.
- Certifications: **10%**. A matching certificate receives full credit; recognized ITI certificates can receive partial credit.

The API defaults to a 60% threshold and returns up to three top recommendations. When no recommendation reaches the threshold, it falls back to the top ranked matches, so seeing a score does not mean the candidate is qualified or guaranteed an interview. Results also include the skills matched, missing required skills, trade-match type, and match diagnostics.

### 3.4 Skill gaps and learning suggestions

For each recommended role, required skills are normalized and compared with the candidate profile. The system lists the overlap and the missing skills. Missing skills are looked up in the bundled `courses.csv`; the software returns topic/provider fields from that data and does not invent URLs. If nothing maps to a missing skill, it reports that no learning resource was found in the dataset.

Official learning-source links are a separate catalogue. Linking to an official learning portal does not validate a particular synthetic course title.

### 3.5 Candidate activity

Candidates can save matched jobs and mark applications, then revisit saved/applied records in their account area. For employer-submitted listings, the candidate application is linked to the employer's posting so that it can appear in that employer's inbox.

### 3.6 Employer workspace

Employers can submit postings with a title, trade, company, location, skills, experience requirement, and description. New posts start as pending and remain hidden from candidates until the configured administrator approves them. This is a prototype review workflow, not third-party validation of the employer or vacancy. Employers see their own postings and a candidate-application inbox for approved posts. They can update application statuses and add private notes.

### 3.7 Home page and market updates

The home page provides:

- A feed of employer-submitted listings from this application, refreshed periodically and on request.
- A count and trade summary for posts in this portal.
- Links to official job-search / apprenticeship sources for users to check current openings themselves.
- Career-journey guidance content.

It does **not** fetch live news, scrape external job portals, or guarantee current hiring trends. “Live” updates on this page mean updates to this application's employer-post feed, not a live nationwide labour-market feed.

## 4. End-to-end user journeys

### Candidate journey

1. Open the site and sign in or register as a candidate.
2. Upload a PDF/DOCX resume.
3. The backend extracts text and candidate fields, classifies the document, and validates ITI evidence/trade.
4. Review or correct the extracted profile and choose the trade if evidence is unclear.
5. Request matches. A non-valid ITI profile does not receive job recommendations.
6. Review ranked matches and filter/search them.
7. Open a match to inspect score components, matching/missing skills, and course/topic suggestions.
8. Save the role or mark it applied; use Saved & Applied to revisit activity.
9. For posts made by portal employers, the application can appear in that employer's inbox.

### Employer journey

1. Register or sign in as an employer.
2. Open the employer workspace and create a job post.
3. The post becomes visible to candidates when published under the current direct-publishing behavior.
4. Review applications linked to the employer's own posts.
5. Update application status and record a private review note.
6. Close a post when it is no longer available.

### System / deployment journey

1. `run.py` starts Uvicorn and the FastAPI application.
2. On API initialization, matching datasets and the SQLite database are loaded/initialized.
3. In the Docker build, Node builds the React/Vite frontend; the generated frontend assets are copied into the Python runtime image.
4. FastAPI serves the API and the built frontend in the unified deployed service.

## 5. Architecture and important files

| Area | Implementation |
|---|---|
| Frontend | React 19, Vite, Lucide icons; primary app and role-specific screens in `frontend/src/App.jsx`; styles in `frontend/src/index.css` |
| Backend | FastAPI endpoints and request validation in `src/api.py` |
| Resume parsing | PDF/DOCX text extraction in `src/resume_parser.py` |
| Profile extraction | Trade, skills, education, experience, certifications, and document checks in `src/candidate_extractor.py` |
| Matching | Trade compatibility, TF-IDF, scoring, and ranking in `src/job_matcher.py` |
| Skill gaps | Skill comparisons and recommendation lookup in `src/skill_gap.py` |
| Persistence | SQLite accounts, sessions, saved jobs, applications, employer posts, and inbox functions in `src/persistence.py` |
| Data | Reference CSV files in `iti_skill_gap_datasets/` |
| Tests | Unit and workflow tests in `tests/` |
| Deployment | Docker multi-stage frontend/backend image in `Dockerfile`; Render service definition in `render.yaml` |

The frontend is not a second, independently deployed product: the Docker image builds the React app and serves its static assets from the same FastAPI service.

## 6. Data inventory and provenance

The checked-in dataset audit reports:

- **7 canonical ITI trades**: COPA, Electrician, Electronics Mechanic, Fitter, Machinist, Mechanic Motor Vehicle, and Welder.
- **210 trade skills** and corresponding trade-skill weights.
- **1,000 job example rows**, covering 27 titles and 10 company names. All 1,000 are marked unverified; none has a source URL or application URL. Descriptions repeat across the dataset.
- **112 course/topic suggestion rows**, all currently without resource URLs.
- **7 job-source portals** and **10 learning sources**, including 7 trade-specific official learning pages.
- **1 job research lead** pending confirmation; it is not automatically included as a live vacancy.

Therefore the algorithm can be demonstrated and exercised, but its job ranking results are not evidence of current real openings or hiring outcomes. Likewise, course suggestions are not confirmation that an exact course exists or is available.

## 7. API capabilities

The current API includes routes for health, protected metadata and test samples, resume upload, profile validation, job matching, sample job/course lookup, job and learning source catalogues, authentication, saved jobs, candidate applications, employer postings, approved employer listings, employer application inbox, and employer application review. Admin job moderation and user-role-management APIs are available only to a bearer session for the configured administrator email. The former one-time admin bootstrap endpoint is absent.

Protected candidate/employer features require a bearer session. Registration accepts only the candidate and employer roles.

## 8. Results and validation performed

### Verified during this report preparation

- **Frontend production build:** passed with `npm run build` (Vite transformed 1,834 modules and emitted production assets).
- **Python source compilation:** passed for `src/api.py` and `src/persistence.py` using `py -m py_compile`.
- **Persistence/admin/employer tests:** 6 passed across `tests/test_persistence.py` and `tests/test_phase6_roles.py`, covering registration/session persistence, user-scoped saved/application data, pending employer posts and moderation, configured-admin seeding, password rotation/session revocation, protection against taking over a non-admin email, and employer post closure.
- **Python source compilation:** passed for the API, persistence module, and updated Python tests.
- **Not run successfully:** API integration tests require FastAPI and resume/matching tests require pandas; those packages are missing from this Python environment. The updated API integration test for configured-admin access is therefore present but not verified here.

### Full-suite limitation

A full `unittest` discovery was attempted. The persistence/employer tests passed, but two test modules could not be imported in the current Python environment because required packages were missing: `pandas` for `tests/test_system.py` and `fastapi` for `tests/test_phase7_application_flow.py`. This is an environment/dependency limitation, not a reported assertion failure. The test suite is therefore **not fully verified in this environment**. Test execution also emitted SQLite connection `ResourceWarning`s during existing test cleanup.

### Documentation drift

Older quality and deployment notes include results from earlier code and should be treated as historical. The current implementation guide for Phase 6 and the source code describe the configured-admin behavior in this report.

## 9. Current limitations and risks

1. **No verified live job feed:** bundled job rows are examples without provenance; the home page only refreshes portal employer posts and links to external sources.
2. **Employer posts are self-submitted:** direct publishing does not verify company identity, listing truth, or job availability.
3. **Course dataset is incomplete/unverified:** bundled titles/providers are suggestions and none currently has a direct resource URL.
4. **Heuristic extraction:** resumes with unusual layouts, ambiguous trade naming, tables, or scanned pages can be misread or rejected; human review remains necessary.
5. **Matching is dataset-dependent:** weights and ranked results reflect the bundled data and rule-based score, not validated hiring success.
6. **English-centric parsing:** multilingual resumes are not the stated supported workflow.
7. **Prototype security posture:** wildcard CORS, bearer token storage in browser local storage, lack of rate limiting, and missing documented data-retention workflows need review before a public production service.
8. **Persistence on hosting:** the Render definition shown has no configured persistent disk or managed database. SQLite data persistence across redeploys/restarts must be checked for the actual service configuration.
9. **Limited admin operations:** the portal supports employer-job moderation and candidate/employer role assignments, but does not provide system-wide configuration, audit-log browsing, user deletion, or other advanced administration tools.
10. **Browser-level QA:** a successful build is not the same as end-to-end browser testing; no cross-browser, accessibility, or deployed-service verification is claimed here.

## 10. Repository and release state

At report time, the admin portal restoration and related workflow/security changes are local and uncommitted, along with this report and updated implementation documentation. They have not been pushed or deployed; the Render service may still run an earlier revision. The working tree also contains untracked `tmp/` and `report_submission/` directories; they are not part of the Docker build inputs.

## 11. Overall assessment

The project has a coherent prototype workflow and useful explainable components: a controlled ITI trade taxonomy, safeguards against obvious false COPA inference, transparent match factors, explicit skill gaps, candidate activity tracking, and a distinct employer workflow. The strongest demonstrated result is functional integration across the main candidate and employer data paths, supported by a passing frontend build and the four passing persistence/employer tests listed above.

The system should be presented as an **ITI employability prototype using demonstration job data**, not as a live job board or verified recommendation service. Before evaluation or public demonstration, install the full Python dependencies, run the complete suite, perform manual browser checks, align the older guides with the current code, confirm Render is deploying the intended commit, and decide how prototype users should be told that job and course records are not independently verified.
