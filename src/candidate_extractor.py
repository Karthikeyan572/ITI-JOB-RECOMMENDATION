import os
from pathlib import Path
import re
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

try:
    from resume_parser import parse_resume
except ImportError:
    from src.resume_parser import parse_resume


# =========================================================
# DATASET PATHS (Robust relative to project root or file location)
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATASETS_DIR = BASE_DIR / "iti_skill_gap_datasets"

SKILLS_PATH = DATASETS_DIR / "skills.csv"
TRADES_PATH = DATASETS_DIR / "trades.csv"

# Safe fallback if loaded from another working directory
if not SKILLS_PATH.exists():
    SKILLS_PATH = Path("iti_skill_gap_datasets/skills.csv")
if not TRADES_PATH.exists():
    TRADES_PATH = Path("iti_skill_gap_datasets/trades.csv")

# =========================================================
# LOAD DATASETS
# =========================================================

skills_df = pd.read_csv(SKILLS_PATH).fillna("")
trades_df = pd.read_csv(TRADES_PATH).fillna("")

# Trade alias mapping for robust matching
TRADE_ALIASES = {
    "Electrician": [
        "electrician",
        "electrical",
        "electrical technician",
        "industrial electrician",
        "wireman",
    ],
    "Fitter": [
        "fitter",
        "mechanical fitter",
        "bench fitter",
        "maintenance fitter",
    ],
    "Welder": [
        "welder",
        "welding",
        "welding technician",
        "arc welder",
        "mig welder",
        "tig welder",
    ],
    "Machinist": [
        "machinist",
        "turner",
        "cnc machinist",
        "machinist grinder",
        "milling machinist",
    ],
    "Electronics Mechanic": [
        "electronics mechanic",
        "electronic mechanic",
        "electronics",
        "electronics technician",
    ],
    "Mechanic Motor Vehicle": [
        "mechanic motor vehicle",
        "motor vehicle mechanic",
        "mmv",
        "motor mechanic",
        "automobile mechanic",
        "auto mechanic",
    ],
    "COPA": [
        "copa",
        "computer operator and programming assistant",
        "computer operator & programming assistant",
        "computer operator",
        "c.o.p.a.",
        "c.o.p.a",
    ],
}

# General ITI Evidence indicators
ITI_EVIDENCE_PATTERNS = [
    r"\biti\b",
    r"\bindustrial\s+training\s+institute\b",
    r"\bncvt\b",
    r"\bscvt\b",
    r"\bntc\b",
    r"\bnac\b",
    r"\bnational\s+trade\s+certificate\b",
    r"\bnational\s+apprenticeship\s+certificate\b",
    r"\bvocational\s+training\b",
    r"\bcraftsmen\s+training\s+scheme\b",
    r"\bcraftsman\s+training\s+scheme\b",
    r"\btrade\s+certificate\b",
    r"\ball\s+india\s+trade\s+test\b",
    r"\baitt\b",
]

# Generic CSE/Software keywords that must NOT trigger COPA on their own
GENERIC_CSE_KEYWORDS = {
    "python", "programming", "computer", "software", "java", "c", "c++",
    "web", "database", "it", "developer", "coding", "machine learning",
    "undergraduate", "b.e", "b.tech", "mca", "bca", "frontend", "backend"
}


# =========================================================
# TEXT NORMALIZATION
# =========================================================

def normalize_text(text):
    """
    Lowercase, remove punctuation except +, #, . and standardize whitespace.
    """
    if text is None:
        return ""

    text = str(text).lower()
    # Keep letters, numbers, +, # and .
    text = re.sub(r"[^a-z0-9+#.\s]", " ", text)
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_matching(text):
    """
    Normalization for skill and trade comparison.
    """
    text = normalize_text(text)
    replacements = {
        "scikit learn": "scikit-learn",
        "scikit learn library": "scikit-learn",
        "machine-learning": "machine learning",
        "data-science": "data science",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


# =========================================================
# SECTION EXTRACTION
# =========================================================

def get_section(text, section_names):
    """
    Extract text belonging to specified section headers.
    """
    if not text:
        return ""

    lines = text.splitlines()
    start = -1

    for i, line in enumerate(lines):
        line_clean = normalize_text(line)
        for section in section_names:
            if section in line_clean:
                start = i
                break
        if start != -1:
            break

    if start == -1:
        return ""

    headings = [
        "career objective",
        "objective",
        "contact",
        "areas of interest",
        "technical skill",
        "technical skills",
        "skills",
        "educational qualification",
        "education",
        "qualification",
        "experience",
        "work experience",
        "certification",
        "certifications",
        "projects",
        "languages known",
        "declaration",
    ]

    section_text = []
    for line in lines[start + 1:]:
        line_clean = normalize_text(line)
        if line_clean in headings:
            break
        if line.strip():
            section_text.append(line)

    return "\n".join(section_text)


# =========================================================
# ITI EVIDENCE & VALIDATION
# =========================================================

def has_iti_evidence(text: str) -> bool:
    """
    Checks whether the text contains explicit indicators of an ITI / vocational education background.
    """
    if not text:
        return False

    text_norm = normalize_text(text)
    for pattern in ITI_EVIDENCE_PATTERNS:
        if re.search(pattern, text_norm, re.IGNORECASE):
            return True

    return False


def validate_iti_profile(profile: dict, text: str) -> str:
    """
    Validates whether the resume contains an identifiable ITI profile.
    Returns:
      - 'VALID': A specific ITI trade has been detected.
      - 'TRADE_UNCLEAR': Evidence of ITI/NCVT/SCVT/vocational training exists, but trade is unclear.
      - 'NOT_ITI': No specific trade and no meaningful ITI evidence.
    """
    trade = profile.get("iti_trade")
    if trade and trade not in ("Not detected", "None", ""):
        return "VALID"

    if has_iti_evidence(text):
        return "TRADE_UNCLEAR"

    return "NOT_ITI"


# =========================================================
# TRADE RESOLUTION HELPER
# =========================================================

def resolve_trade_name(trade_str: str) -> str:
    """
    Maps a candidate trade string or alias to the canonical trade name in trades_df.
    Returns canonical trade name or None.
    """
    if not trade_str:
        return None

    cleaned = normalize_text(trade_str)
    if not cleaned:
        return None

    # Check canonical trades and aliases
    for canonical_trade, aliases in TRADE_ALIASES.items():
        if cleaned == normalize_text(canonical_trade):
            return canonical_trade
        for alias in aliases:
            if cleaned == normalize_text(alias):
                return canonical_trade
            if fuzz.ratio(cleaned, normalize_text(alias)) >= 85:
                return canonical_trade

    # Check trades_df directly
    for _, row in trades_df.iterrows():
        trade = str(row["trade"]).strip()
        if not trade:
            continue
        if fuzz.ratio(cleaned, normalize_text(trade)) >= 80:
            return trade

    return None


# =========================================================
# TRADE EXTRACTION
# =========================================================

def extract_trade(text: str) -> str:
    """
    Extract ITI trade with priority on explicit evidence.
    Prevents false COPA inference on generic CSE/software terms.
    Returns canonical trade name or None.
    """
    if not text:
        return None

    text_normalized = normalize_for_matching(text)
    raw_lines = text.splitlines()

    # -----------------------------------------------------
    # 1. Look for explicitly stated ITI trade patterns
    # -----------------------------------------------------
    explicit_patterns = [
        r"iti\s+trade\s*[:\-]\s*([a-zA-Z &]+)",
        r"trade\s*[:\-]\s*([a-zA-Z &]+)",
        r"iti\s+in\s+([a-zA-Z &]+)",
        r"iti\s*[-–/]\s*([a-zA-Z &]+)",
        r"iti\s*\(\s*([a-zA-Z &]+)\s*\)",
        r"\biti\s+([a-zA-Z &]+)(?:\s+trade|\b)",
        r"\b(ncvt|scvt|ntc|nac)\s+([a-zA-Z &]+)",
    ]

    for pattern in explicit_patterns:
        matches = re.finditer(pattern, text_normalized, re.IGNORECASE)
        for match in matches:
            matched_str = match.group(1).strip() if match.lastindex == 1 else match.group(2).strip()
            # Stop if matched string is too long (likely captured multiple words)
            candidate_tokens = matched_str.split()[:4]
            candidate_phrase = " ".join(candidate_tokens)
            resolved = resolve_trade_name(candidate_phrase)
            if resolved:
                return resolved

    # Check lines mentioning ITI / NCVT / SCVT for co-occurring trade name
    for line in raw_lines:
        line_norm = normalize_text(line)
        if any(re.search(p, line_norm) for p in [r"\biti\b", r"\bncvt\b", r"\bscvt\b"]):
            for canonical_trade, aliases in TRADE_ALIASES.items():
                for alias in [canonical_trade] + aliases:
                    pattern = r"\b" + re.escape(normalize_text(alias)) + r"\b"
                    if re.search(pattern, line_norm):
                        return canonical_trade

    # -----------------------------------------------------
    # 2. Inferred trade detection
    #    CRITICAL RULE: Never infer an ITI trade if there is
    #    NO ITI background evidence at all.
    #    This completely prevents false positives on CSE /
    #    B.E. / B.Tech / generic resumes.
    # -----------------------------------------------------
    if not has_iti_evidence(text):
        return None

    # Resume has ITI evidence, but trade wasn't stated in explicit form.
    # We examine domain-specific trade keywords from trades_df.
    trade_scores = []

    for _, row in trades_df.iterrows():
        trade = str(row["trade"]).strip()
        keywords = str(row.get("keywords", ""))

        if not trade or not keywords:
            continue

        keyword_list = [
            normalize_text(k)
            for k in keywords.split(";")
            if normalize_text(k)
        ]

        matched_keywords = []
        for keyword in keyword_list:
            if len(keyword) < 3:
                continue

            # For COPA: NEVER count generic programming/software/computer terms as evidence
            if trade == "COPA" and keyword in GENERIC_CSE_KEYWORDS:
                continue

            pattern = r"\b" + re.escape(keyword) + r"\b"
            if re.search(pattern, text_normalized):
                matched_keywords.append(keyword)

        # Require at least 3 strong domain keywords
        if len(matched_keywords) >= 3:
            trade_scores.append((trade, len(matched_keywords), matched_keywords))

    if trade_scores:
        trade_scores.sort(key=lambda x: x[1], reverse=True)
        # If top score is strictly higher than second or sole candidate
        if len(trade_scores) == 1 or trade_scores[0][1] > trade_scores[1][1]:
            return trade_scores[0][0]

    return None


# =========================================================
# SKILL EXTRACTION & NORMALIZATION
# =========================================================

# Pre-build skill lookup dictionaries for rapid and canonical resolution
CANONICAL_SKILLS = {}
ALIAS_TO_CANONICAL = {}

for _, row in skills_df.iterrows():
    canonical = str(row["skill"]).strip()
    if not canonical:
        continue
    norm_canonical = normalize_for_matching(canonical)
    CANONICAL_SKILLS[norm_canonical] = canonical

    aliases = str(row.get("aliases", ""))
    if aliases:
        for alias in aliases.split(";"):
            norm_alias = normalize_for_matching(alias)
            if norm_alias:
                ALIAS_TO_CANONICAL[norm_alias] = canonical


def normalize_skill(skill_name: str, fuzzy_threshold: int = 85) -> str:
    """
    Normalizes any given skill name to its canonical name in skills.csv.
    Uses exact lookup, alias mapping, and RapidFuzz fuzzy matching.
    Returns canonical skill name if found, else original cleaned skill name.
    """
    if not skill_name:
        return ""

    cleaned = normalize_for_matching(skill_name)
    if not cleaned:
        return ""

    # 1. Direct canonical match
    if cleaned in CANONICAL_SKILLS:
        return CANONICAL_SKILLS[cleaned]

    # 2. Direct alias match
    if cleaned in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[cleaned]

    # 3. Fuzzy match against canonical skills
    best_match = None
    best_score = 0
    for norm_can, canonical in CANONICAL_SKILLS.items():
        score = fuzz.ratio(cleaned, norm_can)
        if score > best_score:
            best_score = score
            best_match = canonical

    # 4. Fuzzy match against aliases
    for norm_al, canonical in ALIAS_TO_CANONICAL.items():
        score = fuzz.ratio(cleaned, norm_al)
        if score > best_score:
            best_score = score
            best_match = canonical

    if best_score >= fuzzy_threshold:
        return best_match

    return skill_name.strip()


def extract_skills(text: str) -> list:
    """
    Extracts and normalizes ITI-relevant skills from resume text using skills.csv.
    Returns sorted list of unique canonical skill names.
    """
    if not text:
        return []

    text_normalized = normalize_for_matching(text)
    detected_skills = set()

    for _, row in skills_df.iterrows():
        canonical_skill = str(row["skill"]).strip()
        if not canonical_skill:
            continue

        skill_norm = normalize_for_matching(canonical_skill)

        # Word boundary pattern
        pattern = r"(?<!\w)" + re.escape(skill_norm) + r"(?!\w)"
        if re.search(pattern, text_normalized):
            detected_skills.add(canonical_skill)
            continue

        # Alias matching
        aliases = str(row.get("aliases", ""))
        if aliases:
            for alias in aliases.split(";"):
                alias_norm = normalize_for_matching(alias)
                if not alias_norm:
                    continue
                pattern = r"(?<!\w)" + re.escape(alias_norm) + r"(?!\w)"
                if re.search(pattern, text_normalized):
                    detected_skills.add(canonical_skill)
                    break

    return sorted(detected_skills)


# =========================================================
# EXPERIENCE EXTRACTION
# =========================================================

def extract_experience(text: str) -> float:
    """
    Extract total years of experience as a float.
    Returns 0.0 if not detected.
    """
    if not text:
        return 0.0

    text_normalized = normalize_text(text)

    patterns = [
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+of\s+experience",
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+experience",
        r"experience\s*[:\-]?\s*(\d+(?:\.\d+)?)\s*years?",
        r"(\d+(?:\.\d+)?)\s*\+?\s*years?\s+work\s+experience",
        r"total\s+experience\s*[:\-]?\s*(\d+(?:\.\d+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text_normalized)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass

    return 0.0


# =========================================================
# QUALIFICATION EXTRACTION
# =========================================================

def extract_qualification(text: str) -> list:
    """
    Extracts educational qualifications mentioned in the resume.
    """
    if not text:
        return []

    text_normalized = normalize_text(text)
    qualifications = []

    qualification_patterns = {
        "B.E": [r"\bb\.?\s*e\.?\b", r"\bbachelor of engineering\b"],
        "B.Tech": [r"\bb\.?\s*tech\.?\b", r"\bbachelor of technology\b"],
        "M.E": [r"\bm\.?\s*e\.?\b", r"\bmaster of engineering\b"],
        "M.Tech": [r"\bm\.?\s*tech\.?\b", r"\bmaster of technology\b"],
        "Diploma": [r"\bdiploma\b"],
        "ITI": [r"\biti\b", r"\bindustrial training institute\b"],
        "HSC": [r"\bhsc\b", r"\bhigher secondary\b", r"\b12th\b"],
        "SSLC": [r"\bsslc\b", r"\bsecondary school leaving certificate\b", r"\b10th\b"],
    }

    for qual, patterns in qualification_patterns.items():
        for pattern in patterns:
            if re.search(pattern, text_normalized):
                qualifications.append(qual)
                break

    return qualifications


# =========================================================
# CERTIFICATION EXTRACTION
# =========================================================

def extract_certifications(text: str) -> list:
    """
    Extracts certifications from the certification section or ITI-specific credentials in text.
    """
    if not text:
        return []

    certifications = []

    # 1. Look in explicit certification sections
    cert_section = get_section(text, ["certification", "certifications", "certificates"])
    if cert_section:
        for line in cert_section.splitlines():
            line = line.strip()
            if not line:
                continue
            line = re.sub(r"^[•\-*]\s*", "", line)
            if len(line) > 2:
                certifications.append(line)

    # 2. Check for ITI standard certificates in full text
    standard_certs = [
        ("NCVT", r"\bncvt\b"),
        ("SCVT", r"\bscvt\b"),
        ("Trade Certificate", r"\btrade certificate\b|\bntc\b"),
        ("Apprenticeship Certificate", r"\bnac\b|\bapprenticeship certificate\b"),
        ("Safety Certificate", r"\bsafety certificate\b|\bosha\b|\bindustrial safety\b"),
    ]

    text_norm = normalize_text(text)
    for cert_label, cert_regex in standard_certs:
        if re.search(cert_regex, text_norm):
            if not any(cert_label.lower() in c.lower() for c in certifications):
                certifications.append(cert_label)

    return list(dict.fromkeys(certifications))


# =========================================================
# COMPLETE PROFILE EXTRACTION
# =========================================================

def extract_candidate_profile(text: str) -> dict:
    """
    Extract complete candidate profile from resume text.
    """
    return {
        "iti_trade": extract_trade(text),
        "skills": extract_skills(text),
        "experience": extract_experience(text),
        "certifications": extract_certifications(text),
        "qualification": extract_qualification(text),
    }


def display_profile(profile: dict):
    """
    Print candidate profile to stdout.
    """
    print("\n" + "=" * 60)
    print("                 CANDIDATE PROFILE")
    print("=" * 60)
    print("ITI Trade       :", profile.get("iti_trade") or "Not detected")
    print("Skills          :", ", ".join(profile.get("skills", [])) or "None detected")
    print("Experience      :", f"{profile.get('experience', 0.0)} years")
    print("Certifications  :", ", ".join(profile.get("certifications", [])) or "None detected")
    print("Qualification   :", ", ".join(profile.get("qualification", [])) or "Not detected")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    print("ITI Candidate Profile Extractor")
    print("--------------------------------")
    file_path = input("Enter resume file path: ").strip().strip('"')

    try:
        resume_text = parse_resume(file_path)
        print("\nResume text extracted successfully.")
        profile = extract_candidate_profile(resume_text)
        display_profile(profile)
        status = validate_iti_profile(profile, resume_text)
        print(f"ITI Profile Validation Status: {status}")
    except Exception as e:
        print("\nError:", e)