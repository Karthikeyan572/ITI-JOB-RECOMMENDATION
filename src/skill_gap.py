from pathlib import Path
import pandas as pd

try:
    from candidate_extractor import normalize_skill, normalize_text
except ImportError:
    from src.candidate_extractor import normalize_skill, normalize_text


# =========================================================
# PATH RESOLUTION & DATASET LOADING
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "iti_skill_gap_datasets"
COURSES_PATH = DATASET_DIR / "courses.csv"


def load_courses_dataset() -> pd.DataFrame:
    """
    Loads courses.csv with graceful fallback and error handling.
    """
    if not COURSES_PATH.exists():
        raise FileNotFoundError(
            f"Courses dataset not found at {COURSES_PATH}. "
            "Please check the iti_skill_gap_datasets directory."
        )

    courses_df = pd.read_csv(COURSES_PATH).fillna("")
    return courses_df


# =========================================================
# SKILL GAP ANALYSIS
# =========================================================

def analyze_skill_gap(
    candidate_skills: list,
    job_required_skills: list
) -> dict:
    """
    Performs precise skill gap analysis using canonical normalized skill names.
    Aliases are mapped to canonical names so they are never counted as separate missing skills.

    Returns:
      {
        "required_skills": [...],
        "matched_skills": [...],
        "missing_skills": [...],
        "total_required": int,
        "matched_count": int,
        "missing_count": int,
        "match_percentage": float,
        "gap_percentage": float
      }
    """
    cand_norm_set = set(
        normalize_skill(s) for s in candidate_skills if s and str(s).strip()
    )

    req_norm_list = []
    seen = set()
    for s in job_required_skills:
        if not s or not str(s).strip():
            continue
        norm = normalize_skill(str(s).strip())
        if norm and norm not in seen:
            seen.add(norm)
            req_norm_list.append(norm)

    matched = [s for s in req_norm_list if s in cand_norm_set]
    missing = [s for s in req_norm_list if s not in cand_norm_set]

    total_req = len(req_norm_list)
    matched_cnt = len(matched)
    missing_cnt = len(missing)

    gap_pct = round((missing_cnt / total_req * 100), 1) if total_req > 0 else 0.0
    match_pct = round((matched_cnt / total_req * 100), 1) if total_req > 0 else 100.0

    return {
        "required_skills": req_norm_list,
        "matched_skills": matched,
        "missing_skills": missing,
        "total_required": total_req,
        "matched_count": matched_cnt,
        "missing_count": missing_cnt,
        "match_percentage": match_pct,
        "gap_percentage": gap_pct,
    }


# =========================================================
# LEARNING RECOMMENDATIONS
# =========================================================

def get_learning_recommendations(
    missing_skills: list,
    courses_df: pd.DataFrame = None,
    candidate_trade: str = None
) -> list[dict]:
    """
    Finds targeted learning modules from courses.csv for each missing skill.
    Prefers resources for the candidate's trade and general resources when a trade is supplied.
    Never invents course URLs or names.
    If no resource exists for a skill, returns:
      'No learning resource found in the current dataset.'
    """
    if courses_df is None:
        courses_df = load_courses_dataset()

    recommendations = []

    # Map normalized skill name to courses
    courses_by_skill = {}
    for _, row in courses_df.iterrows():
        raw_skill = str(row["skill"]).strip()
        norm_skill = normalize_skill(raw_skill)

        course_item = {
            "course_id": row.get("course_id", ""),
            "course_name": row.get("course_name", ""),
            "skill": norm_skill,
            "trade": row.get("trade", ""),
            "level": row.get("level", "Beginner"),
            "provider": row.get("provider", "N/A"),
            "duration": row.get("duration", "N/A"),
            "resource_url": (
                row.get("resource_url")
                if row.get("resource_url") and str(row.get("resource_url")).strip() and str(row.get("resource_url")).lower() != "nan"
                else ""
            ),
            "record_status": row.get("record_status", "UNVERIFIED_TOPIC_SUGGESTION"),
            "provider_verification_status": row.get("provider_verification_status", "UNVERIFIED"),
            "resource_verification_status": row.get("resource_verification_status", "NO_URL"),
        }

        courses_by_skill.setdefault(norm_skill.lower(), []).append(course_item)

    for skill in missing_skills:
        canonical_s = normalize_skill(skill)
        skill_key = canonical_s.lower()

        matched_courses = courses_by_skill.get(skill_key, [])

        if candidate_trade and matched_courses:
            wanted_trade = normalize_text(candidate_trade)
            trade_specific = [
                course for course in matched_courses
                if normalize_text(course.get("trade", "")) == wanted_trade
            ]
            general_courses = [
                course for course in matched_courses
                if normalize_text(course.get("trade", "")) in {"", "all trades", "general", "n/a", "na"}
            ]
            matched_courses = trade_specific + general_courses

        unique_courses = []
        seen_course_keys = set()
        for course in matched_courses:
            course_key = str(course.get("course_id") or "").strip().lower()
            if not course_key:
                course_key = "|".join([
                    normalize_text(course.get("course_name", "")),
                    normalize_text(course.get("provider", "")),
                    normalize_text(course.get("skill", "")),
                    normalize_text(course.get("trade", "")),
                ])
            if course_key not in seen_course_keys:
                seen_course_keys.add(course_key)
                unique_courses.append(course)

        if unique_courses:
            for course in unique_courses:
                item = dict(course)
                item["recommendation_reason"] = (
                    f"Targets the missing skill '{canonical_s}' for {candidate_trade}."
                    if candidate_trade else f"Targets the missing skill '{canonical_s}'."
                )
                recommendations.append(item)
        else:
            # Explicit standard message when no course exists in dataset
            recommendations.append({
                "course_id": "N/A",
                "course_name": "No learning resource found in the current dataset.",
                "skill": canonical_s,
                "trade": "N/A",
                "level": "N/A",
                "provider": "N/A",
                "duration": "N/A",
                "resource_url": "",
                "record_status": "NO_RESOURCE_FOUND",
                "provider_verification_status": "NOT_APPLICABLE",
                "resource_verification_status": "NO_URL",
            })

    return recommendations


def generate_job_gap_report(
    job: dict,
    candidate_profile: dict,
    courses_df: pd.DataFrame = None
) -> dict:
    """
    Creates an end-to-end skill gap and learning recommendation report for a specific job.
    """
    cand_skills = candidate_profile.get("skills", [])
    job_skills = job.get("required_skills", [])

    gap_analysis = analyze_skill_gap(cand_skills, job_skills)
    learning_resources = get_learning_recommendations(
        gap_analysis["missing_skills"],
        courses_df=courses_df
    )

    return {
        "job_id": job.get("job_id"),
        "job_title": job.get("job_title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "gap_analysis": gap_analysis,
        "learning_recommendations": learning_resources,
    }


if __name__ == "__main__":
    print("Testing Skill Gap Analysis & Learning Recommendations...")
    courses_df = load_courses_dataset()

    sample_req = ["Wiring", "PLC", "Panel Wiring", "AutoCAD Electrical"]
    sample_cand = ["Wiring", "PLC"]

    gap = analyze_skill_gap(sample_cand, sample_req)
    print("\nSkill Gap Analysis Result:")
    print("  Required Skills :", gap["required_skills"])
    print("  Matched Skills  :", gap["matched_skills"])
    print("  Missing Skills  :", gap["missing_skills"])
    print(f"  Gap Percentage  : {gap['gap_percentage']}%")

    recs = get_learning_recommendations(gap["missing_skills"], courses_df)
    print("\nLearning Recommendations for Missing Skills:")
    for r in recs:
        print(f"  - Skill: {r['skill']}")
        print(f"    Course  : {r['course_name']}")
        print(f"    Provider: {r['provider']} | Duration: {r['duration']} | Level: {r['level']}")
        print(f"    URL     : {r['resource_url']}")
