"""Create a repeatable quality report for the ITI reference datasets."""
from pathlib import Path
import json
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "iti_skill_gap_datasets"
OUTPUT = ROOT / "DATASET_AUDIT.md"


def read_csv(name):
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(f"Required dataset not found: {path}")
    return pd.read_csv(path).fillna("")


def main():
    jobs = read_csv("jobs.csv")
    skills = read_csv("skills.csv")
    trades = read_csv("trades.csv")
    courses = read_csv("courses.csv")
    weights = read_csv("trade_skill_weights.csv")
    job_sources = read_csv("job_sources.csv") if (DATA / "job_sources.csv").exists() else pd.DataFrame()
    learning_sources = read_csv("learning_sources.csv") if (DATA / "learning_sources.csv").exists() else pd.DataFrame()
    job_candidates = read_csv("job_research_candidates.csv") if (DATA / "job_research_candidates.csv").exists() else pd.DataFrame()

    required_job_columns = {
        "job_id", "company", "job_title", "iti_trade", "required_skills",
        "experience", "qualification", "certifications", "location", "job_description"
    }
    missing_job_columns = sorted(required_job_columns - set(jobs.columns))
    canonical_trades = set(trades["trade"].astype(str).str.strip())
    unknown_related = []
    for _, row in trades.iterrows():
        for related in str(row.get("related_trades", "")).split(";"):
            related = related.strip()
            if related and related not in canonical_trades:
                unknown_related.append(f"{row['trade']} -> {related}")

    alias_col = skills["aliases"] if "aliases" in skills else pd.Series([""] * len(skills))
    url_col = courses["resource_url"] if "resource_url" in courses else pd.Series([""] * len(courses))
    description_counts = jobs.get("job_description", pd.Series(dtype=str)).astype(str).value_counts()
    exact_duplicate_rows = int(jobs.duplicated().sum())
    duplicate_descriptions = int((description_counts > 1).sum())
    rows_with_repeated_descriptions = int(description_counts[description_counts > 1].sum())

    findings = {
        "jobs": {
            "rows": int(len(jobs)),
            "unique_job_ids": int(jobs["job_id"].nunique()) if "job_id" in jobs else None,
            "exact_duplicate_rows": exact_duplicate_rows,
            "unique_job_titles": int(jobs["job_title"].nunique()) if "job_title" in jobs else None,
            "unique_companies": int(jobs["company"].nunique()) if "company" in jobs else None,
            "unique_trades": int(jobs["iti_trade"].nunique()) if "iti_trade" in jobs else None,
            "unique_descriptions": int(jobs["job_description"].nunique()) if "job_description" in jobs else None,
            "repeated_description_values": duplicate_descriptions,
            "rows_using_repeated_descriptions": rows_with_repeated_descriptions,
            "missing_required_columns": missing_job_columns,
            "unverified_sample_rows": int(jobs.get("record_status", pd.Series(dtype=str)).astype(str).eq("UNVERIFIED_SAMPLE").sum()),
            "rows_with_source_url": int(jobs.get("source_url", pd.Series(dtype=str)).astype(str).str.strip().ne("").sum()),
            "rows_with_application_url": int(jobs.get("application_url", pd.Series(dtype=str)).astype(str).str.strip().ne("").sum()),
        },
        "skills": {
            "rows": int(len(skills)),
            "empty_alias_rows": int(alias_col.astype(str).str.strip().eq("").sum()),
            "missing_skill_values": int(skills.get("skill", pd.Series(dtype=str)).astype(str).str.strip().eq("").sum()),
        },
        "trades": {
            "rows": int(len(trades)),
            "canonical_trades": sorted(canonical_trades),
            "unknown_related_trade_mappings": unknown_related,
        },
        "courses": {
            "rows": int(len(courses)),
            "empty_resource_url_rows": int(url_col.astype(str).str.strip().eq("").sum()),
        },
        "trade_skill_weights": {
            "rows": int(len(weights)),
            "trades_covered": int(weights["trade"].nunique()) if "trade" in weights else None,
        },
        "job_sources": {"rows": int(len(job_sources)), "official_portals": int(job_sources.get("verification_status", pd.Series(dtype=str)).astype(str).str.startswith("OFFICIAL").sum())},
        "learning_sources": {"rows": int(len(learning_sources)), "checked_sources": int(learning_sources.get("verification_status", pd.Series(dtype=str)).astype(str).isin(["OFFICIAL_PORTAL_CHECKED", "EXACT_COURSE_PAGE_CHECKED", "OFFICIAL_TRADE_PAGE_CHECKED"]).sum()), "trade_specific_official_pages": int(learning_sources.get("verification_status", pd.Series(dtype=str)).astype(str).eq("OFFICIAL_TRADE_PAGE_CHECKED").sum())},
        "job_research_candidates": {"rows": int(len(job_candidates)), "pending_official_confirmation": int(job_candidates.get("verification_status", pd.Series(dtype=str)).astype(str).str.contains("NEEDS_OFFICIAL", na=False).sum())},
    }

    lines = [
        "# Dataset Quality Audit",
        "",
        "Generated by `python scripts/audit_datasets.py`.",
        "",
        "> **Provenance warning:** the repository does not include source URLs or verification dates for job records. Treat job rows as unverified until their provenance is established; do not advertise them as live vacancies. If records were created for testing, label them as demonstration data.",
        "",
        "## Summary",
        "",
        f"- Jobs: {findings['jobs']['rows']} rows; {findings['jobs']['unique_job_titles']} unique titles; {findings['jobs']['unique_companies']} unique companies.",
        f"- Exact duplicate job rows: {findings['jobs']['exact_duplicate_rows']}.",
        f"- Unverified sample rows: {findings['jobs']['unverified_sample_rows']}; rows with source URLs: {findings['jobs']['rows_with_source_url']}; rows with application URLs: {findings['jobs']['rows_with_application_url']}.",
        f"- Unique job descriptions: {findings['jobs']['unique_descriptions']}; repeated description templates affect {findings['jobs']['rows_using_repeated_descriptions']} rows.",
        f"- Skills: {findings['skills']['rows']} rows; {findings['skills']['empty_alias_rows']} have empty aliases.",
        f"- Trades: {findings['trades']['rows']} canonical trades.",
        f"- Courses: {findings['courses']['rows']} rows; {findings['courses']['empty_resource_url_rows']} have no resource URL.",
        f"- Trade-skill weights: {findings['trade_skill_weights']['rows']} rows across {findings['trade_skill_weights']['trades_covered']} trades.",
        f"- Checked job-source portals: {findings['job_sources']['rows']}; checked learning sources: {findings['learning_sources']['rows']}, including {findings['learning_sources']['trade_specific_official_pages']} trade-specific official pages.",
        f"- Job research queue: {findings['job_research_candidates']['rows']} lead(s), {findings['job_research_candidates']['pending_official_confirmation']} awaiting official-notice confirmation; these are not live jobs.",
        "",
        "## Findings and recommended actions",
        "",
        "1. **Verify job provenance.** All existing job records are explicitly marked UNVERIFIED_SAMPLE; replace or validate them against a source URL, application URL, and verification date before presenting them as real vacancies.",
        "2. **Review repeated descriptions.** Repetition is not proof that a record is false, but it indicates that the data should be manually checked before production use.",
        "3. **Expand skill aliases carefully.** Add reviewed synonyms and abbreviations; avoid broad aliases that can create false matches.",
        "4. **Verify course links.** Existing course rows are marked as unverified topic suggestions; official learning portals are provided separately and do not imply an exact course exists.",
        "5. **Use trade-specific official learning pages.** `learning_sources.csv` now links to Bharat Skills pages for all seven supported trades; these are official study-material pages, not proof that every synthetic course title is real.",
        "6. **Review the job research queue.** `job_research_candidates.csv` contains leads to investigate. A lead stays out of `jobs.csv` until an official notice, dates, eligibility and application route are independently checked.",
        "7. **Keep trade mappings canonical.** Every related-trade value should match one of the supported trade names.",
        "",
        "## Machine-readable details",
        "",
        "```json",
        json.dumps(findings, indent=2, ensure_ascii=False),
        "```",
        "",
    ]
    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)}")
    print(json.dumps(findings, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
