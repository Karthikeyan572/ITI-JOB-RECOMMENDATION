from pathlib import Path
import re
import pandas as pd


# -----------------------------
# Path Resolution
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "iti_skill_gap_datasets"

JOBS_PATH = DATASET_DIR / "jobs.csv"
SKILLS_PATH = DATASET_DIR / "skills.csv"
TRADES_PATH = DATASET_DIR / "trades.csv"
OUTPUT_PATH = DATASET_DIR / "trade_skill_weights.csv"


def normalize(text):
    """
    Standardize text for matching: lowercase, strip, and alphanumeric + safe chars.
    """
    if pd.isna(text):
        return ""
    text = str(text).lower().strip()
    text = re.sub(r"[^a-z0-9+#. ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def compute_skill_weights():
    """
    Derive trade-skill weights from jobs.csv and skills.csv.
    Weights reflect empirical frequency of skills required for jobs within each trade,
    normalized per trade such that core trade skills have weight up to 1.0,
    secondary skills have moderate weight, and transferable/generic skills lower weight.
    """
    if not JOBS_PATH.exists() or not SKILLS_PATH.exists():
        raise FileNotFoundError(
            f"Dataset files not found in {DATASET_DIR}. Please check the dataset directory."
        )

    jobs = pd.read_csv(JOBS_PATH)
    skills = pd.read_csv(SKILLS_PATH)

    jobs["trade_norm"] = jobs["iti_trade"].apply(normalize)
    # Split required skills into a set of normalized skill tokens per job
    jobs["skills_tokens"] = jobs["required_skills"].apply(
        lambda x: set(normalize(s) for s in str(x).split(";") if s.strip())
    )

    skills["skill_norm"] = skills["skill"].apply(normalize)
    skills["trade_norm"] = skills["trade"].apply(normalize)

    results = []

    for trade in skills["trade_norm"].unique():
        trade_skills = skills[skills["trade_norm"] == trade]
        trade_jobs = jobs[jobs["trade_norm"] == trade]

        total_jobs = len(trade_jobs)
        if total_jobs == 0:
            continue

        for _, skill_row in trade_skills.iterrows():
            skill = skill_row["skill"]
            skill_norm = skill_row["skill_norm"]

            # Match canonical skill and any defined aliases
            aliases = [
                normalize(a)
                for a in str(skill_row.get("aliases", "")).split(";")
                if normalize(a)
            ]
            match_targets = {skill_norm} | set(aliases)

            # Count jobs requiring this skill
            count = trade_jobs["skills_tokens"].apply(
                lambda t_set: bool(t_set & match_targets)
            ).sum()

            # If token match is 0, check substring in normalized required skills string
            if count == 0 and len(skill_norm) > 3:
                count = trade_jobs["required_skills"].apply(
                    lambda s: skill_norm in normalize(s)
                ).sum()

            frequency = count / total_jobs

            results.append({
                "trade": skill_row["trade"],
                "skill": skill,
                "job_count": total_jobs,
                "skill_job_count": int(count),
                "job_frequency": round(frequency, 4),
            })

    weights = pd.DataFrame(results)

    # Normalize frequency within each trade to [0.20, 1.0] so trade skills retain a baseline
    max_freq = weights.groupby("trade")["job_frequency"].transform("max")
    weights["normalized_weight"] = 0.20
    mask = (max_freq > 0) & (weights["job_frequency"] > 0)
    weights.loc[mask, "normalized_weight"] = (
        0.20 + 0.80 * (weights.loc[mask, "job_frequency"] / max_freq[mask])
    ).round(4)

    weights = weights.sort_values(
        ["trade", "normalized_weight"],
        ascending=[True, False]
    )

    weights.to_csv(OUTPUT_PATH, index=False)

    print("Trade-specific skill weights generated successfully.")
    print(f"Total records: {len(weights)}")
    print("\nSample (Electrician top skills):")
    print(weights[weights["trade"] == "Electrician"].head(10))

    return weights


if __name__ == "__main__":
    compute_skill_weights()