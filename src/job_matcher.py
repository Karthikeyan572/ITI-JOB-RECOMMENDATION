from pathlib import Path
import re
import numpy as np
import pandas as pd
try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib

    class _FuzzFallback:
        @staticmethod
        def ratio(s1, s2):
            return int(difflib.SequenceMatcher(None, str(s1), str(s2)).ratio() * 100)

    fuzz = _FuzzFallback()
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from candidate_extractor import normalize_skill, normalize_text
except ImportError:
    from src.candidate_extractor import normalize_skill, normalize_text


# =========================================================
# PATH RESOLUTION & DATASET LOADING
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "iti_skill_gap_datasets"

JOBS_PATH = DATASET_DIR / "jobs.csv"
SKILLS_PATH = DATASET_DIR / "skills.csv"
TRADES_PATH = DATASET_DIR / "trades.csv"
WEIGHTS_PATH = DATASET_DIR / "trade_skill_weights.csv"


def load_matching_datasets():
    """
    Load all required datasets for job matching with validation.
    Returns:
      (jobs_df, skills_df, trades_df, weights_df)
    """
    for path, name in [
        (JOBS_PATH, "jobs.csv"),
        (SKILLS_PATH, "skills.csv"),
        (TRADES_PATH, "trades.csv"),
        (WEIGHTS_PATH, "trade_skill_weights.csv"),
    ]:
        if not path.exists():
            raise FileNotFoundError(
                f"Required dataset '{name}' not found at {path}. "
                "Please verify the iti_skill_gap_datasets directory."
            )

    jobs_df = pd.read_csv(JOBS_PATH).fillna("")
    skills_df = pd.read_csv(SKILLS_PATH).fillna("")
    trades_df = pd.read_csv(TRADES_PATH).fillna("")
    weights_df = pd.read_csv(WEIGHTS_PATH).fillna("")

    return jobs_df, skills_df, trades_df, weights_df


# =========================================================
# TRADE COMPATIBILITY MATRIX
# =========================================================

def get_trade_compatibility_map(trades_df: pd.DataFrame) -> dict:
    """
    Builds a trade compatibility lookup mapping:
      (candidate_trade, job_trade) -> score (1.0 for exact, 0.5 for related, 0.0 for unrelated).
    Uses the 'related_trades' field in trades.csv.
    """
    comp_map = {}
    all_trades = [str(t).strip() for t in trades_df["trade"].unique() if str(t).strip()]

    # Index related trades per trade
    trade_related = {}
    for _, row in trades_df.iterrows():
        trade = str(row["trade"]).strip()
        related_str = str(row.get("related_trades", ""))
        related_list = [
            r.strip() for r in related_str.split(";") if r.strip()
        ]
        trade_related[trade] = related_list

    for cand_t in all_trades:
        for job_t in all_trades:
            if cand_t.lower() == job_t.lower():
                comp_map[(cand_t, job_t)] = 1.0
            elif job_t in trade_related.get(cand_t, []) or cand_t in trade_related.get(job_t, []):
                comp_map[(cand_t, job_t)] = 0.5
            else:
                comp_map[(cand_t, job_t)] = 0.0

    return comp_map


def compute_trade_compatibility(
    candidate_trade: str,
    job_trade: str,
    comp_map: dict = None
) -> float:
    """
    Determines trade compatibility between candidate trade and job trade.
    Exact trade    -> 1.0
    Related trade  -> 0.5
    Unrelated trade-> 0.0
    """
    if not candidate_trade or not job_trade:
        return 0.0

    cand_clean = candidate_trade.strip()
    job_clean = job_trade.strip()

    if cand_clean.lower() == job_clean.lower():
        return 1.0

    if comp_map:
        score = comp_map.get((cand_clean, job_clean))
        if score is not None:
            return score

    return 0.0


# =========================================================
# EXPERIENCE MATCHING
# =========================================================

def parse_experience_range(exp_str: str) -> tuple[float, float]:
    """
    Parse experience strings like '0-1 years', '1-2 years', '2-3 years'.
    Returns (min_exp, max_exp).
    """
    if not exp_str:
        return (0.0, 0.0)

    match = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", str(exp_str))
    if match:
        return (float(match.group(1)), float(match.group(2)))

    single_match = re.search(r"(\d+(?:\.\d+)?)", str(exp_str))
    if single_match:
        val = float(single_match.group(1))
        return (val, val)

    return (0.0, 0.0)


def compute_experience_score(candidate_exp: float, job_exp_str: str) -> float:
    """
    Calculates experience match score:
      - If candidate_exp >= min_required -> 1.0
      - If candidate_exp < min_required  -> candidate_exp / min_required
    """
    min_exp, max_exp = parse_experience_range(job_exp_str)

    try:
        cand_exp = float(candidate_exp)
    except (ValueError, TypeError):
        cand_exp = 0.0

    if min_exp == 0.0:
        # Fresher/entry level friendly
        return 1.0

    if cand_exp >= min_exp:
        return 1.0

    score = cand_exp / min_exp
    return round(max(0.0, min(1.0, score)), 4)


# =========================================================
# CERTIFICATION MATCHING
# =========================================================

def compute_certification_score(
    candidate_certs: list,
    job_cert_str: str
) -> float:
    """
    Calculates certification match score:
      - If job requires no certification (empty / None) -> 1.0
      - If job requires certification:
        - 1.0 if candidate has matching certificate
        - 0.85 if candidate has a recognized ITI trade certificate (NCVT/SCVT)
        - 0.0 if candidate has no certifications
    """
    if not job_cert_str or job_cert_str.lower() in ("nan", "none", ""):
        return 1.0

    if not candidate_certs:
        return 0.0

    job_cert_clean = normalize_text(job_cert_str)

    # Check for direct match
    for cert in candidate_certs:
        cert_clean = normalize_text(cert)
        if fuzz.ratio(cert_clean, job_cert_clean) >= 80:
            return 1.0
        if job_cert_clean in cert_clean or cert_clean in job_cert_clean:
            return 1.0

    # Recognized standard ITI trade credentials grant high partial credit
    standard_iti_markers = {"ncvt", "scvt", "trade certificate", "ntc", "nac"}
    has_standard = any(
        any(marker in normalize_text(c) for marker in standard_iti_markers)
        for c in candidate_certs
    )
    if has_standard:
        return 0.85

    return 0.50


# =========================================================
# TF-IDF TEXTUAL MODEL
# =========================================================

class JobTFIDFModel:
    """
    Prepares and computes TF-IDF representations and cosine similarities
    between candidate profile and job listings.
    """

    def __init__(self, jobs_df: pd.DataFrame):
        self.jobs_df = jobs_df
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            token_pattern=r"(?u)\b[a-zA-Z0-9+#.]{2,}\b"
        )
        self._build_corpus_and_fit()

    def _build_corpus_and_fit(self):
        corpus = []
        for _, row in self.jobs_df.iterrows():
            skills_text = str(row.get("required_skills", "")).replace(";", " ")
            doc = (
                f"{row.get('job_title', '')} "
                f"{row.get('iti_trade', '')} "
                f"{skills_text} "
                f"{row.get('job_description', '')} "
                f"{row.get('qualification', '')}"
            )
            corpus.append(doc)

        self.job_tfidf = self.vectorizer.fit_transform(corpus)

    def compute_similarity(self, candidate_text: str) -> np.ndarray:
        cand_vec = self.vectorizer.transform([candidate_text])
        sims = cosine_similarity(cand_vec, self.job_tfidf).flatten()
        return sims


# =========================================================
# CORE JOB MATCHER ENGINE
# =========================================================

class ITIJobMatcher:
    """
    Main job matching engine for ITI candidates:
    - Filters by trade compatibility
    - Uses TF-IDF cosine similarity for textual matching
    - Uses trade_skill_weights.csv for weighted skill overlap
    - Calculates 4-factor final match score
    - Ranks and outputs top recommendations
    """

    def __init__(self):
        self.jobs_df, self.skills_df, self.trades_df, self.weights_df = load_matching_datasets()
        self.comp_map = get_trade_compatibility_map(self.trades_df)
        self.tfidf_model = JobTFIDFModel(self.jobs_df)

        # Pre-build weights dictionary: (trade, normalized_skill) -> normalized_weight
        self.weight_lookup = {}
        for _, row in self.weights_df.iterrows():
            trade = str(row["trade"]).strip()
            skill_norm = normalize_skill(str(row["skill"]).strip())
            weight = float(row.get("normalized_weight", 0.50))
            self.weight_lookup[(trade, skill_norm)] = weight

    def get_skill_weight(self, trade: str, skill: str) -> float:
        """
        Look up trade-specific skill weight or return sensible default.
        """
        norm = normalize_skill(skill)
        w = self.weight_lookup.get((trade, norm))
        if w is not None:
            return w
        # Default weight for trade skills
        return 0.50

    def match_jobs(
        self,
        candidate_profile: dict,
        min_threshold: float = 0.60,
        top_n: int = 3,
        filter_unrelated_trades: bool = True
    ) -> list[dict]:
        """
        Matches a candidate profile against the jobs dataset.

        Final Match Formula:
          final_score = 0.50 * skill_score +
                        0.25 * trade_score +
                        0.15 * experience_score +
                        0.10 * certification_score

        Returns:
          List of matched job dicts sorted by final_score descending.
        """
        cand_trade = candidate_profile.get("iti_trade")
        cand_skills = set(
            normalize_skill(s) for s in candidate_profile.get("skills", []) if s
        )
        cand_exp = candidate_profile.get("experience", 0.0)
        cand_certs = candidate_profile.get("certifications", [])

        # Build candidate representation for TF-IDF textual similarity
        skills_str = " ".join(cand_skills)
        certs_str = " ".join(cand_certs)
        quals_str = " ".join(candidate_profile.get("qualification", []))
        cand_text = f"{cand_trade or ''} {skills_str} {certs_str} {quals_str}"

        # TF-IDF textual similarities for all jobs
        tfidf_sims = self.tfidf_model.compute_similarity(cand_text)

        evaluated_jobs = []

        for idx, row in self.jobs_df.iterrows():
            job_id = row["job_id"]
            job_trade = str(row["iti_trade"]).strip()

            # -------------------------------------------------
            # 1. Trade Compatibility
            # -------------------------------------------------
            trade_score = compute_trade_compatibility(
                cand_trade, job_trade, self.comp_map
            )

            # Filter out jobs with zero trade compatibility if requested
            if filter_unrelated_trades and trade_score == 0.0:
                continue

            # -------------------------------------------------
            # 2. Skill Overlap & Weighted Skill Score
            # -------------------------------------------------
            raw_req_skills = [
                s.strip() for s in str(row["required_skills"]).split(";") if s.strip()
            ]
            job_req_skills = [normalize_skill(s) for s in raw_req_skills]

            matched_skills = [s for s in job_req_skills if s in cand_skills]
            missing_skills = [s for s in job_req_skills if s not in cand_skills]

            # Calculate weighted skill match
            if job_req_skills:
                total_weight = sum(
                    self.get_skill_weight(job_trade, s) for s in job_req_skills
                )
                matched_weight = sum(
                    self.get_skill_weight(job_trade, s) for s in matched_skills
                )
                weighted_skill_ratio = (
                    matched_weight / total_weight if total_weight > 0 else 0.0
                )
            else:
                weighted_skill_ratio = 1.0 if cand_skills else 0.0

            # Combined skill score: 70% weighted skill overlap + 30% TF-IDF textual similarity
            tfidf_sim = float(tfidf_sims[idx])
            skill_score = min(
                1.0,
                0.70 * weighted_skill_ratio + 0.30 * min(1.0, tfidf_sim * 1.5)
            )

            # -------------------------------------------------
            # 3. Experience Match
            # -------------------------------------------------
            experience_score = compute_experience_score(
                cand_exp, row.get("experience", "")
            )

            # -------------------------------------------------
            # 4. Certification Match
            # -------------------------------------------------
            certification_score = compute_certification_score(
                cand_certs, row.get("certifications", "")
            )

            # -------------------------------------------------
            # 5. Multi-Factor Final Score
            # -------------------------------------------------
            final_score = (
                0.50 * skill_score +
                0.25 * trade_score +
                0.15 * experience_score +
                0.10 * certification_score
            )
            final_score = round(final_score, 4)
            match_percentage = round(final_score * 100, 1)

            evaluated_jobs.append({
                "job_id": job_id,
                "job_title": row["job_title"],
                "company": row["company"],
                "location": row["location"],
                "iti_trade": job_trade,
                "experience_required": row["experience"],
                "certifications_required": row["certifications"] or "None required",
                "job_description": row["job_description"],
                "required_skills": job_req_skills,
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "skill_score": round(skill_score, 4),
                "weighted_skill_ratio": round(weighted_skill_ratio, 4),
                "tfidf_similarity": round(tfidf_sim, 4),
                "trade_score": round(trade_score, 4),
                "experience_score": round(experience_score, 4),
                "certification_score": round(certification_score, 4),
                "final_score": final_score,
                "match_percentage": match_percentage,
                "meets_threshold": final_score >= min_threshold,
            })

        # Sort all evaluated jobs by final_score descending
        evaluated_jobs.sort(key=lambda x: x["final_score"], reverse=True)

        return evaluated_jobs

    def get_top_recommendations(
        self,
        candidate_profile: dict,
        min_threshold: float = 0.60,
        top_n: int = 3
    ) -> list[dict]:
        """
        Retrieves Top N recommended jobs meeting the minimum threshold.
        """
        all_matches = self.match_jobs(
            candidate_profile,
            min_threshold=min_threshold,
            filter_unrelated_trades=True
        )

        qualified = [j for j in all_matches if j["meets_threshold"]]

        if qualified:
            return qualified[:top_n]

        # If no jobs meet the threshold, return top candidates below threshold with notice
        return all_matches[:top_n]


if __name__ == "__main__":
    print("Testing ITI Job Matcher...")
    matcher = ITIJobMatcher()

    sample_profile = {
        "iti_trade": "Electrician",
        "skills": ["Wiring", "Electrical Testing", "Transformers", "PLC"],
        "experience": 1.5,
        "certifications": ["NCVT", "Trade Certificate"],
        "qualification": ["ITI"],
    }

    top_jobs = matcher.get_top_recommendations(sample_profile, min_threshold=0.60, top_n=3)
    print(f"\nTop {len(top_jobs)} Recommendations for Electrician:")
    for i, job in enumerate(top_jobs, 1):
        print(f"\n[{i}] {job['job_title']} at {job['company']} ({job['location']})")
        print(f"    Match Percentage : {job['match_percentage']}% (Final Score: {job['final_score']})")
        print(f"    Trade Score      : {job['trade_score'] * 100}%")
        print(f"    Skill Score      : {job['skill_score'] * 100}% (TF-IDF Sim: {job['tfidf_similarity']})")
        print(f"    Exp / Cert Score : {job['experience_score'] * 100}% / {job['certification_score'] * 100}%")
        print(f"    Matched Skills   : {job['matched_skills']}")
        print(f"    Missing Skills   : {job['missing_skills']}")
