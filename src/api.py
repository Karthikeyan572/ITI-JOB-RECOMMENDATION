from pathlib import Path
import sys
from fastapi import FastAPI, File, HTTPException, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import re
import secrets


# Ensure src directory is in sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from persistence import (init_db, create_user, authenticate_user, create_session, get_user_for_token,
                         revoke_session, list_saved_jobs, save_job, unsave_job, list_applications,
                         add_application, update_application_status, create_job_post, list_job_posts,
                         set_job_post_status, add_admin_audit, list_users, set_user_role,
                         list_employer_applications, link_application_to_job, update_employer_application)

from candidate_extractor import (
    extract_candidate_profile,
    normalize_skill,
    skills_df,
    trades_df,
    validate_iti_profile,
)
from job_matcher import ITIJobMatcher
from resume_parser import parse_resume
from skill_gap import get_learning_recommendations, load_courses_dataset

# =========================================================
# FASTAPI APP INITIALIZATION
# =========================================================

app = FastAPI(
    title="AI-Driven ITI Employability API",
    description="REST API for ITI candidate resume parsing, trade validation, job matching, and skill gap analysis.",
    version="1.0.0"
)

# Enable CORS for local React/Vite development and external frontends
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global matcher and courses instances
matcher = ITIJobMatcher()
courses_df = load_courses_dataset()
init_db()
bearer_scheme = HTTPBearer(auto_error=False)


# =========================================================
# PYDANTIC MODELS
# =========================================================

class CandidateProfile(BaseModel):
    iti_trade: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: float = 0.0
    certifications: list[str] = Field(default_factory=list)
    qualification: list[str] = Field(default_factory=list)
    is_resume: bool = True
    document_type: str = "RESUME"
    rejection_reason: str | None = None
    validation_status: str | None = None


class MatchRequest(BaseModel):
    profile: CandidateProfile
    min_threshold: float = Field(default=0.60, ge=0.0, le=1.0)
    top_n: int = Field(default=3, ge=1, le=10)


class ValidateRequest(BaseModel):
    profile: CandidateProfile
    text: str = ""


# =========================================================
# PRE-LOADED DEMO SAMPLES
# =========================================================

DEMO_SAMPLES = {
    "electrician": {
        "title": "ITI Electrician (Valid Profile)",
        "trade": "Electrician",
        "filename": "sample_electrician.pdf",
        "text": (
            "KUMARAGURU M\n"
            "ITI Electrician\n"
            "Government Industrial Training Institute, Coimbatore\n"
            "NCVT Trade Certificate in Electrician\n\n"
            "CAREER OBJECTIVE\n"
            "Skilled ITI Electrician seeking employment in industrial electrical maintenance and installation.\n\n"
            "TECHNICAL SKILLS\n"
            "Wiring, PLC, Motor Maintenance, Electrical Safety, Electrical Testing, Cable Termination, Transformers\n\n"
            "WORK EXPERIENCE\n"
            "2 years experience as Assistant Electrician at Premier Power Systems.\n"
            "- Handled single phase wiring and preventive maintenance of electric motors.\n"
            "- Conducted megger testing and multimeter measurements.\n\n"
            "CERTIFICATIONS\n"
            "- NCVT Trade Certificate\n"
            "- Industrial Safety Certificate\n\n"
            "EDUCATION\n"
            "ITI Electrician (NCVT), 2021\n"
            "SSLC (10th Standard), 2019"
        )
    },
    "fitter": {
        "title": "ITI Fitter (Valid Profile)",
        "trade": "Fitter",
        "filename": "sample_fitter.docx",
        "text": (
            "ARUN PRAKASH\n"
            "Trade: Fitter\n"
            "Govt ITI Chennai\n"
            "NTC Certified\n\n"
            "OBJECTIVE\n"
            "Hardworking ITI Fitter looking to work in machine assembly and fabrication.\n\n"
            "TECHNICAL SKILLS\n"
            "Fitting, Lathe Machine Operation, Assembly, Measurement, Drilling, Grinding\n\n"
            "EXPERIENCE\n"
            "1.5 years experience in Precision Engineering Works.\n\n"
            "CERTIFICATIONS\n"
            "- Trade Certificate\n\n"
            "EDUCATION\n"
            "ITI Fitter, 2022\n"
            "10th SSLC, 2020"
        )
    },
    "cse": {
        "title": "CSE Graduate (Non-ITI Profile)",
        "trade": None,
        "filename": "sample_cse.pdf",
        "text": (
            "KARTHIKEYAN S\n"
            "UNDERGRADUATE COMPUTER SCIENCE STUDENT\n\n"
            "Career Objective\n"
            "Motivated undergraduate computer science student with a strong foundation in programming "
            "and problem-solving. Interested in software development and machine learning.\n\n"
            "TECHNICAL SKILLS\n"
            "Python, Machine Learning, Data Science, Web Development, SQL\n\n"
            "EDUCATION\n"
            "B.E. Computer Science and Engineering\n"
            "HSC (12th)\n"
            "SSLC (10th)\n\n"
            "EXPERIENCE\n"
            "0 years of work experience"
        )
    },
    "unclear": {
        "title": "ITI Unclear Trade Profile",
        "trade": None,
        "filename": "sample_unclear.pdf",
        "text": (
            "SURESH RAO\n"
            "Industrial Training Institute Trainee\n"
            "National Trade Certificate (NCVT) holder\n\n"
            "OBJECTIVE\n"
            "Completed 2-year vocational training at Govt Industrial Training Institute.\n"
            "Seeking technical apprentice position.\n\n"
            "SKILLS\n"
            "Measurement, Safety, Technical Drawing\n\n"
            "EXPERIENCE\n"
            "1 year experience in technical workshop.\n\n"
            "EDUCATION\n"
            "ITI (NCVT), 2022"
        )
    },
    "survey_paper": {
        "title": "Academic Survey Paper (Non-Resume / Rejected)",
        "trade": None,
        "filename": "sample_survey_paper.txt",
        "text": (
            "A Comprehensive Survey on IoT in Industrial Automation and Predictive Maintenance\n"
            "Dr. R. Sharma, Dept. of Electrical Engineering, Indian Institute of Science\n"
            "Email: rsharma@iisc.ac.in | DOI: 10.1109/TII.2023.987654\n\n"
            "ABSTRACT\n"
            "In this survey paper, we present an exhaustive overview of Internet of Things (IoT) "
            "deployment in modern industrial automation. We evaluate sensor networks, wiring protocols, "
            "and electrical motor condition monitoring across automated manufacturing systems.\n\n"
            "KEYWORDS: IoT, Industrial Automation, Sensors, Wiring, Motor Control, Predictive Maintenance\n\n"
            "1. INTRODUCTION\n"
            "Industrial infrastructure has undergone rapid digitalization [1], [2]. Over 10 years of "
            "experience in testing smart edge devices indicates substantial operational benefits [3].\n\n"
            "2. LITERATURE SURVEY & RELATED WORK\n"
            "Smith et al. [4] surveyed wireless sensor networks in harsh manufacturing environments. "
            "Similarly, Kumar et al. [5] examined automated welding and inspection architectures.\n\n"
            "3. METHODOLOGY AND TAXONOMY\n"
            "We classify industrial communications into three distinct tiers...\n\n"
            "4. CONCLUSION AND FUTURE DIRECTIONS\n"
            "Standardization of communication protocols remains an open challenge.\n\n"
            "REFERENCES\n"
            "[1] A. Kumar, 'Smart Industrial Grids,' IEEE Trans. Ind. Inform., vol. 18, pp. 112-120, 2021.\n"
            "[2] B. Patel, 'Sensors and Wiring in Smart Factories,' Springer Journal of Systems, 2022.\n"
            "[3] C. Lee et al., 'Predictive Maintenance for Electric Motors,' IEEE Access, 2023.\n"
            "[4] D. Smith, 'Industrial Sensor Networks Survey,' ACM Computing Surveys, 2021.\n"
            "[5] E. White, 'Automated Inspection in Precision Manufacturing,' 2022."
        )
    }
}


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "AI-Driven ITI Employability System",
        "total_jobs": len(matcher.jobs_df),
        "total_skills": len(skills_df),
        "total_trades": len(trades_df),
    }


@app.get("/api/meta")
def get_metadata():
    """
    Returns available trades and canonical skills taxonomy.
    """
    known_trades = sorted([str(t).strip() for t in trades_df["trade"].unique() if str(t).strip()])
    all_skills = sorted(list(set(
        normalize_skill(str(s)) for s in skills_df["skill"].unique() if str(s).strip()
    )))

    return {
        "trades": known_trades,
        "skills": all_skills,
    }


@app.get("/api/samples")
def get_sample_resumes():
    """
    Returns pre-configured sample resume scenarios for one-click testing.
    """
    return DEMO_SAMPLES


@app.post("/api/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Parses an uploaded PDF or DOCX resume, extracts candidate information,
    and performs ITI validation.
    """
    filename = file.filename or "resume.pdf"
    content = await file.read()

    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        raw_text = parse_resume(content, filename_hint=filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {e}")

    if not raw_text.strip():
        raise HTTPException(
            status_code=400,
            detail="The resume contains no readable text. Please check the file."
        )

    profile = extract_candidate_profile(raw_text)
    val_status = validate_iti_profile(profile, raw_text)

    # Informative status message
    if val_status == "NOT_A_RESUME":
        message = (
            profile.get("rejection_reason")
            or "The uploaded document appears to be an academic survey or research paper, not a candidate resume."
        )
    elif val_status == "VALID":
        message = f"Valid ITI profile detected for trade: {profile.get('iti_trade')}."
    elif val_status == "TRADE_UNCLEAR":
        message = "ITI vocational indicators detected, but specific trade could not be determined. Please select your trade."
    else:
        message = "No specific ITI trade or sufficient ITI-related information was detected."

    return {
        "filename": filename,
        "raw_text": raw_text,
        "char_count": len(raw_text),
        "profile": profile,
        "validation_status": val_status,
        "message": message,
        "is_resume": profile.get("is_resume", True),
        "document_type": profile.get("document_type", "RESUME"),
    }


@app.post("/api/validate-profile")
def validate_profile(req: ValidateRequest):
    """
    Re-validates a profile against ITI criteria after candidate edits.
    """
    status = validate_iti_profile(req.profile.model_dump(), req.text)
    return {
        "validation_status": status,
        "profile": req.profile
    }


@app.post("/api/match-jobs")
def match_jobs(req: MatchRequest):
    """
    Runs multi-factor job matching on a candidate profile.
    Returns Top 3 recommendations, skill gap analysis, and course recommendations.
    """
    profile_dict = req.profile.model_dump()

    # Matching is available only after the uploaded resume passes ITI validation.
    if profile_dict.get("validation_status") != "VALID":
        return {
            "candidate_trade": None,
            "top_recommendations": [],
            "total_matched_jobs": 0,
            "meets_threshold_count": 0,
            "diagnostics": [],
            "message": "Only a valid ITI resume can be matched to jobs."
        }

    # Normalize skills
    profile_dict["skills"] = [
        normalize_skill(s) for s in profile_dict.get("skills", []) if s
    ]

    all_matches = matcher.match_jobs(
        profile_dict,
        min_threshold=req.min_threshold,
        filter_unrelated_trades=True
    )

    qualified = [j for j in all_matches if j["meets_threshold"]]
    top_jobs = qualified[:req.top_n] if qualified else all_matches[:req.top_n]

    # Attach learning recommendations for missing skills to each recommended job
    for job in top_jobs:
        missing = job.get("missing_skills", [])
        if missing:
            job["learning_recommendations"] = get_learning_recommendations(
                missing,
                courses_df=courses_df,
                candidate_trade=profile_dict.get("iti_trade"),
            )
        else:
            job["learning_recommendations"] = []

    return {
        "candidate_trade": profile_dict.get("iti_trade"),
        "top_recommendations": top_jobs,
        "total_matched_jobs": len(all_matches),
        "meets_threshold_count": len(qualified),
        "diagnostics": all_matches[:25],
    }


@app.get("/api/job-sources")
def get_job_sources():
    """Return checked official job portals; these are sources, not imported vacancies."""
    path = SRC_DIR.parent / "iti_skill_gap_datasets" / "job_sources.csv"
    if not path.exists():
        return {"sources": []}
    import pandas as pd
    rows = pd.read_csv(path).fillna("").to_dict(orient="records")
    return {"sources": rows}


@app.get("/api/learning-sources")
def get_learning_sources():
    """Return checked learning portals; portal links do not certify individual course records."""
    path = SRC_DIR.parent / "iti_skill_gap_datasets" / "learning_sources.csv"
    if not path.exists():
        return {"sources": []}
    import pandas as pd
    rows = pd.read_csv(path).fillna("").to_dict(orient="records")
    return {"sources": rows}


@app.get("/api/jobs")
def get_jobs(trade: str = None, limit: int = 50):
    """
    Explore jobs with optional trade filtering.
    """
    df = matcher.jobs_df
    if trade and trade.strip():
        df = df[df["iti_trade"].str.lower() == trade.strip().lower()]

    records = df.head(limit).to_dict(orient="records")
    return {
        "total": len(df),
        "jobs": records
    }


@app.get("/api/courses")
def get_courses(trade: str = None, skill: str = None, limit: int = 100):
    """
    Explore course-topic suggestions. Rows remain unverified until a specific course and URL are checked.
    """
    df = courses_df.copy()
    if trade and trade.strip():
        df = df[df["trade"].str.lower() == trade.strip().lower()]
    if skill and skill.strip():
        df = df[df["skill"].str.lower().str.contains(skill.strip().lower())]

    records = df.head(limit).to_dict(orient="records")
    return {
        "total": len(df),
        "courses": records
    }




# =========================================================
# AUTHENTICATION & PERSISTENT CANDIDATE WORKSPACE
# =========================================================

class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    role: str = "candidate"


class JobPostRequest(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    trade: str = Field(min_length=2, max_length=80)
    company: str = Field(min_length=2, max_length=120)
    location: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=20, max_length=5000)
    required_skills: list[str] = Field(default_factory=list, max_length=50)
    experience_required: float = Field(default=0, ge=0, le=60)


class AdminBootstrapRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=10, max_length=128)
    bootstrap_key: str = Field(min_length=1, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class JobRecordRequest(BaseModel):
    job: dict


class ApplicationStatusRequest(BaseModel):
    status: str


class CandidateApplicationRequest(BaseModel):
    job: dict
    employer_job_post_id: int | None = None


class EmployerApplicationReviewRequest(BaseModel):
    status: str
    note: str = Field(default="", max_length=2000)


def current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Sign in to access your candidate workspace.")
    user = get_user_for_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Session expired or invalid. Please sign in again.")
    return user


def require_role(user: dict, *roles: str):
    if user.get("role") not in roles:
        raise HTTPException(status_code=403, detail="Your account role is not allowed to perform this action.")
    return user


def current_employer(user: dict = Depends(current_user)):
    return require_role(user, "employer", "admin")


def current_admin(user: dict = Depends(current_user)):
    return require_role(user, "admin")


def _valid_email(email: str):
    return bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()))


@app.post("/api/auth/register", status_code=201)
def register(req: RegisterRequest):
    if not _valid_email(req.email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if len(req.password) < 10 or not re.search(r"[A-Za-z]", req.password) or not re.search(r"\d", req.password):
        raise HTTPException(status_code=422, detail="Password must be at least 10 characters and include letters and numbers.")
    if req.role not in {"candidate", "employer"}:
        raise HTTPException(status_code=422, detail="Choose candidate or employer account.")
    user = create_user(req.email, req.password, req.full_name, req.role)
    if not user:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    token = create_session(user["id"])
    return {"user": user, "access_token": token, "token_type": "bearer"}


@app.post("/api/admin/bootstrap", status_code=201)
def bootstrap_admin(req: AdminBootstrapRequest):
    import os
    configured_key = os.getenv("ITI_ADMIN_BOOTSTRAP_KEY", "")
    if not configured_key or not secrets.compare_digest(req.bootstrap_key, configured_key):
        raise HTTPException(status_code=403, detail="Admin bootstrap is not enabled or the key is invalid.")
    if not _valid_email(req.email):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if any(u["role"] == "admin" for u in list_users()):
        raise HTTPException(status_code=409, detail="An administrator account already exists.")
    user = create_user(req.email, req.password, req.full_name, "admin")
    if not user:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    token = create_session(user["id"])
    return {"user": user, "access_token": token, "token_type": "bearer"}


@app.post("/api/auth/login")
def login(req: LoginRequest):
    user = authenticate_user(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    return {"user": user, "access_token": create_session(user["id"]), "token_type": "bearer"}


@app.get("/api/auth/me")
def auth_me(user: dict = Depends(current_user)):
    return {"user": user}


@app.post("/api/auth/logout")
def logout(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), user: dict = Depends(current_user)):
    revoke_session(credentials.credentials)
    return {"message": "Signed out successfully."}


@app.get("/api/account/saved-jobs")
def account_saved_jobs(user: dict = Depends(current_user)):
    return {"jobs": list_saved_jobs(user["id"])}


@app.post("/api/account/saved-jobs")
def account_save_job(req: JobRecordRequest, user: dict = Depends(current_user)):
    job = req.job
    job_id = str(job.get("job_id", "")).strip()
    if not job_id:
        raise HTTPException(status_code=422, detail="Job record must include job_id.")
    save_job(user["id"], job_id, job)
    return {"saved": True, "job_id": job_id}


@app.delete("/api/account/saved-jobs/{job_id}")
def account_unsave_job(job_id: str, user: dict = Depends(current_user)):
    unsave_job(user["id"], job_id)
    return {"saved": False, "job_id": job_id}


@app.get("/api/account/applications")
def account_applications(user: dict = Depends(current_user)):
    return {"applications": list_applications(user["id"])}


@app.post("/api/account/applications")
def account_add_application(req: CandidateApplicationRequest, user: dict = Depends(current_user)):
    require_role(user, "candidate")
    job = req.job
    job_id = str(job.get("job_id", "")).strip()
    if not job_id:
        raise HTTPException(status_code=422, detail="Job record must include job_id.")
    application = add_application(user["id"], job_id, job)
    if req.employer_job_post_id is not None:
        linked = link_application_to_job(user["id"], job_id, req.employer_job_post_id)
        if not linked:
            raise HTTPException(status_code=422, detail="Applications can only be linked to approved employer job posts.")
    return {"application": application}


@app.patch("/api/account/applications/{job_id}")
def account_update_application(job_id: str, req: ApplicationStatusRequest, user: dict = Depends(current_user)):
    application = update_application_status(user["id"], job_id, req.status)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found or status is invalid.")
    return {"application": application}


# =========================================================
# EMPLOYER JOB MANAGEMENT
# =========================================================

@app.post("/api/employer/jobs", status_code=201)
def employer_create_job(req: JobPostRequest, user: dict = Depends(current_employer)):
    post = create_job_post(user["id"], req.model_dump())
    return {"job": post, "message": "Job post published to the candidate portal."}


@app.get("/api/employer/jobs")
def employer_list_jobs(user: dict = Depends(current_employer)):
    return {"jobs": list_job_posts(employer_id=user["id"])}


@app.patch("/api/employer/jobs/{job_id}/close")
def employer_close_job(job_id: int, user: dict = Depends(current_employer)):
    owned = next((j for j in list_job_posts(employer_id=user["id"]) if j["id"] == job_id), None)
    if not owned:
        raise HTTPException(status_code=404, detail="Job post not found for this employer.")
    post = set_job_post_status(job_id, "closed")
    return {"job": post}


@app.get("/api/jobs/approved")
def approved_employer_jobs(trade: str | None = None):
    posts = list_job_posts(status="approved")
    if trade:
        posts = [j for j in posts if j["trade"].casefold() == trade.casefold()]
    return {"total": len(posts), "jobs": posts}


@app.get("/api/employer/applications")
def employer_application_inbox(user: dict = Depends(current_employer)):
    return {"applications": list_employer_applications(user["id"])}


@app.patch("/api/employer/applications/{candidate_user_id}/{job_id}")
def employer_review_application(candidate_user_id: int, job_id: str, req: EmployerApplicationReviewRequest,
                                user: dict = Depends(current_employer)):
    result = update_employer_application(user["id"], candidate_user_id, job_id, req.status, req.note)
    if not result:
        raise HTTPException(status_code=404, detail="Application not found for one of your approved job posts.")
    return {"application": result}


@app.get("/api/admin/jobs")
def admin_list_jobs(user: dict = Depends(current_admin)):
    return {"jobs": list_job_posts()}


@app.patch("/api/admin/jobs/{job_id}/moderate")
def admin_moderate_job(job_id: int, req: ApplicationStatusRequest, user: dict = Depends(current_admin)):
    status_map = {"approve": "approved", "reject": "rejected", "close": "closed"}
    action = req.status.lower()
    if action not in status_map:
        raise HTTPException(status_code=422, detail="Status must be approve, reject, or close.")
    post = set_job_post_status(job_id, status_map[action])
    if not post:
        raise HTTPException(status_code=404, detail="Job post not found.")
    add_admin_audit(user["id"], action, "job_post", job_id, f"status={post['status']}")
    return {"job": post}


@app.get("/api/admin/users")
def admin_list_users(user: dict = Depends(current_admin)):
    return {"users": list_users()}


@app.patch("/api/admin/users/{user_id}/role")
def admin_change_role(user_id: int, req: ApplicationStatusRequest, user: dict = Depends(current_admin)):
    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Administrators cannot change their own role.")
    updated = set_user_role(user_id, req.status)
    if not updated:
        raise HTTPException(status_code=404, detail="User not found or role invalid.")
    add_admin_audit(user["id"], "change_role", "user", user_id, f"role={updated['role']}")
    return {"user": updated}


# =========================================================
# PRODUCTION STATIC FILES & SPA FALLBACK
# =========================================================

PROJECT_ROOT = SRC_DIR.parent
DIST_DIR = PROJECT_ROOT / "frontend" / "dist"

if DIST_DIR.exists() and (DIST_DIR / "index.html").exists():
    assets_dir = DIST_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Do not catch /api routes that were not found
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        target_file = DIST_DIR / full_path
        if target_file.is_file():
            return FileResponse(str(target_file))

        return FileResponse(str(DIST_DIR / "index.html"))

















