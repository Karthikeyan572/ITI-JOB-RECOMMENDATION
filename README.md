# AI-Driven Employability Enhancement System for ITI Graduates through Skill Gap Analysis

An intelligent, explainable, and production-ready Python platform designed to enhance the employability of Industrial Training Institute (ITI) graduates. The system extracts candidate profiles from resumes (PDF/DOCX), validates ITI vocational credentials, normalizes trade-specific skills, matches candidates against compatible ITI job roles using a multi-factor scoring model (50% skills, 25% trade, 15% experience, 10% certification), identifies granular skill gaps, and recommends targeted upskilling courses.

---

## Table of Contents
1. [Problem Statement](#problem-statement)
2. [Objective](#objective)
3. [System Architecture](#system-architecture)
4. [Technology Stack](#technology-stack)
5. [Datasets Description & Schema](#datasets-description--schema)
6. [Methodology](#methodology)
   - [Resume Parsing & Information Extraction](#1-resume-parsing--information-extraction)
   - [ITI Trade Detection & Validation Hierarchy](#2-iti-trade-detection--validation-hierarchy)
   - [Skill Normalization & Weights](#3-skill-normalization--trade-skill-weights)
   - [Trade Compatibility & TF-IDF Matching](#4-trade-compatibility--tf-idf-matching)
   - [Multi-Factor Scoring Formula](#5-multi-factor-scoring-formula)
   - [Skill Gap Analysis & Learning Recommendations](#6-skill-gap-analysis--learning-recommendations)
7. [Installation & Setup](#installation--setup)
8. [Running Instructions](#running-instructions)
9. [Example Workflows](#example-workflows)
10. [Evaluation Plan & Automated Tests](#evaluation-plan--automated-tests)
11. [Limitations](#limitations)
12. [Future Scope](#future-scope)

---

## Problem Statement

ITI (Industrial Training Institute) graduates form the backbone of India's technical and vocational workforce, powering manufacturing, electrical utilities, automotive maintenance, and fabrication sectors. However, many ITI graduates face acute employability challenges due to:
- **Informal Resume Formats**: Technical resumes often list vocational skills informally or use non-standard terminology.
- **Trade Mismatch**: Conventional keyword-based job search engines frequently recommend unrelated jobs (e.g., software engineering jobs to ITI trades simply due to overlapping generic terms like "computer" or "programming").
- **Unclear Skill Gaps**: Candidates lack quantitative visibility into why they are rejected for specific job postings and which specific technical proficiencies they must acquire to qualify.

---

## Objective

1. Provide robust text extraction for PDF and DOCX resumes using modern, performant libraries (`PyMuPDF`, `python-docx`).
2. Extract candidate information (ITI trade, canonical skills, years of experience, certifications, educational qualifications) without hallucination.
3. Validate candidate profiles through a strict 3-tier taxonomy (`VALID`, `TRADE_UNCLEAR`, `NOT_ITI`).
4. Prevent false trade inference (e.g., ensuring generic Computer Science resumes are never misclassified as ITI COPA).
5. Filter jobs strictly by trade compatibility (exact, related, unrelated) before scoring.
6. Calculate a multi-factor match score combining TF-IDF cosine similarity and weighted skill overlap.
7. Rank and recommend the **Top 3** most suitable ITI job postings meeting a minimum match threshold (default 60%).
8. Perform job-specific skill gap analysis and map missing skills to curated vocational learning resources from recognized platforms (NPTEL, Skill India Digital, SWAYAM, Coursera, Udemy).
9. Deliver an intuitive, modern React + Tailwind CSS web dashboard with FastAPI REST backend allowing candidates to review and edit extracted attributes, explore vacancies, and analyze skill gaps.

---

## System Architecture

```
                                  +-----------------------+
                                  | Candidate Resume File |
                                  |     (PDF / DOCX)      |
                                  +-----------+-----------+
                                              |
                                              v
                              +-------------------------------+
                              |     Resume Parser Engine      |
                              |   (PyMuPDF / python-docx)     |
                              +---------------+---------------+
                                              |
                                              v
                              +-------------------------------+
                              |  Candidate Profile Extractor  |
                              |   Regex + RapidFuzz + spaCy   |
                              +---------------+---------------+
                                              |
                       +----------------------+----------------------+
                       |                                             |
                       v                                             v
        +-----------------------------+               +-----------------------------+
        |  ITI Profile Validation     |               |    Skill Normalization      |
        |  - VALID                    |               |  - Canonical Skill Mapping  |
        |  - TRADE_UNCLEAR            |               |  - Alias Resolution         |
        |  - NOT_ITI                  |               |  - RapidFuzz Match          |
        +--------------+--------------+               +--------------+--------------+
                       |                                             |
                       +----------------------+----------------------+
                                              |
                                              v
                              +-------------------------------+
                              |    Interactive Review &       |
                              |    Edit Profile (React Web UI)|
                              +---------------+---------------+
                                              |
                                              v
                              +-------------------------------+
                              |    Trade Compatibility Filter |
                              |      (Exact, Related, None)   |
                              +---------------+---------------+
                                              |
                                              v
                              +-------------------------------+
                              |     Multi-Factor Matcher      |
                              |  - 50% Skill (Weighted+TF-IDF)|
                              |  - 25% Trade Compatibility    |
                              |  - 15% Experience Match       |
                              |  - 10% Certification Match    |
                              +---------------+---------------+
                                              |
                                              v
                              +-------------------------------+
                              |    Top 3 Ranked Job Roles     |
                              +---------------+---------------+
                                              |
                       +----------------------+----------------------+
                       |                                             |
                       v                                             v
        +-----------------------------+               +-----------------------------+
        |     Skill Gap Analysis      |               |   Learning Recommendations  |
        |   (Matched vs Missing)      |               |   (Curated Courses from CSV)|
        +-----------------------------+               +-----------------------------+
```

---

## Technology Stack

- **Language**: Python 3.10+
- **PDF Extraction**: `PyMuPDF` (`pymupdf` modern API)
- **DOCX Extraction**: `python-docx`
- **Text Normalization & NLP**: `re` (Regular Expressions), `spaCy` (with fallback to `spacy.blank("en")`), `RapidFuzz` (fuzzy string matching)
- **Data Manipulation**: `pandas`, `NumPy`
- **Vector Space & Similarity**: `scikit-learn` (`TfidfVectorizer`, `cosine_similarity`)
- **Backend API**: `FastAPI`, `Uvicorn`, `python-multipart`
- **Web UI & Dashboard**: `React` (via Vite), `Tailwind CSS`, `Lucide React`
- **Testing**: `unittest` (13 automated test suites)

---

## Datasets Description & Schema

All datasets reside under `iti_skill_gap_datasets/`:

### 1. `trades.csv` (7 Rows)
Contains the primary ITI trades and their related disciplines:
- `trade_id`: Unique identifier (e.g., `T001`).
- `trade`: Canonical trade title (*Electrician*, *Fitter*, *Welder*, *Machinist*, *Electronics Mechanic*, *Mechanic Motor Vehicle*, *COPA*).
- `related_trades`: Semicolon-delimited related trades for cross-skilling compatibility (e.g., `Electronics Mechanic;Instrument Mechanic`).
- `keywords`: Distinctive technical domain terms.

### 2. `skills.csv` (210 Rows)
Master taxonomy of ITI trade skills:
- `skill_id`: Unique identifier (e.g., `S001`).
- `skill`: Canonical skill name (e.g., `Wiring`, `PLC`, `Arc Welding`).
- `trade`: Associated ITI trade.
- `aliases`: Semicolon-delimited common aliases (e.g., `Electrical Wiring;Wiring Work`, `SMAW;Manual Metal Arc Welding`).

### 3. `jobs.csv` (1,000 Rows)
Simulated industrial job vacancies across the 7 ITI trades:
- `job_id`: Unique identifier (e.g., `J0001`).
- `company`: Employing industrial organization.
- `job_title`: Job role title.
- `iti_trade`: Primary required ITI trade.
- `required_skills`: Semicolon-delimited required technical skills.
- `experience`: Required experience range (e.g., `0-1 years`, `1-2 years`, `2-3 years`).
- `qualification`: Required educational certificate (e.g., `ITI Electrician`).
- `certifications`: Mandatory certification (e.g., `Trade Certificate`, `Safety Certificate`, or NaN).
- `location`: Industrial city location.
- `job_description`: Technical duties and workplace responsibilities.

### 4. `trade_skill_weights.csv` (210 Rows)
Empirically-derived trade skill weights:
- `trade`: Associated trade.
- `skill`: Canonical skill.
- `job_count`: Total jobs for that trade in dataset.
- `skill_job_count`: Number of jobs requiring this skill.
- `job_frequency`: Empirical frequency ($count / total$).
- `normalized_weight`: Scaled weight $[0.20, 1.00]$ where core trade skills reach $1.00$.

### 5. `courses.csv` (112 Rows)
Targeted vocational learning courses:
- `course_id`: Unique course ID (e.g., `C001`).
- `course_name`: Official course module name.
- `skill`: Targeted canonical skill.
- `trade`: Associated trade.
- `level`: Difficulty level (*Beginner*, *Intermediate*, *Advanced*).
- `provider`: Accredited platform (*NPTEL*, *Skill India Digital*, *SWAYAM*, *Coursera*, *Udemy*).
- `duration`: Course duration (e.g., `4 hours`, `30 hours`).
- `resource_url`: URL or empty (never fabricated).

---

## Methodology

### 1. Resume Parsing & Information Extraction
- Resumes uploaded as `.pdf` or `.docx` are parsed through unified abstractions.
- `PyMuPDF` extracts text streams from all pages.
- `python-docx` extracts all document paragraphs and embedded table cell contents.
- Text is cleaned: whitespace normalized, duplicate blank lines compressed, and special control characters stripped.
- Heuristic regular expressions and section boundary analyzers parse:
  - Technical skills (checked against `skills.csv`).
  - Work experience (in years).
  - Recognized trade certifications (`NCVT`, `SCVT`, `Trade Certificate`, `Apprenticeship Certificate`, `Safety Certificate`).
  - Educational qualifications (`ITI`, `Diploma`, `B.E`, `B.Tech`, `HSC`, `SSLC`).

### 2. ITI Trade Detection & Validation Hierarchy
Trade detection prioritizes **explicit evidence** over statistical inference:
1. **Explicit Trade Evidence**:
   - `ITI Trade: <Trade>`, `Trade: <Trade>`, `ITI in <Trade>`, `ITI <Trade>`, `NCVT <Trade>`, `SCVT <Trade>`, `NTC <Trade>`.
2. **Profile Validation Status**:
   - `VALID`: A specific ITI trade from `trades.csv` has been explicitly or confidently detected.
   - `TRADE_UNCLEAR`: General ITI / vocational indicators are present (e.g., `Industrial Training Institute`, `NCVT`, `SCVT`, `vocational training`, `craftsmen training scheme`), but the specific trade cannot be identified.
   - `NOT_ITI`: No specific trade and no meaningful ITI indicators detected. Standardized system notice displayed:
     > *"No specific ITI trade or sufficient ITI-related information was detected."*
3. **False COPA Detection Prevention**:
   - Generic Computer Science keywords (`Python`, `programming`, `software`, `java`, `c`, `computer`, `web`, `database`) **never** trigger an ITI trade classification. Resumes without ITI markers remain `NOT_ITI` and do not generate ITI job recommendations.

### 3. Skill Normalization & Trade-Skill Weights
- Every extracted or user-supplied skill is mapped to its canonical name in `skills.csv`.
- Normalization pipeline:
  1. Exact canonical match (lowercase / punctuation-stripped).
  2. Alias mapping (`Electrical Wiring` $\rightarrow$ `Wiring`, `SMAW` $\rightarrow$ `Arc Welding`).
  3. `RapidFuzz` string similarity ($\ge 85\%$).
- Skills are weighted using `trade_skill_weights.csv`:
  - Core trade skills: highest weight ($\approx 1.00$).
  - Secondary/related skills: moderate weight ($\approx 0.50 - 0.80$).
  - Transferable skills: baseline weight ($\ge 0.20$).

### 4. Trade Compatibility & TF-IDF Matching
- **Trade Compatibility Filtering**:
  - Exact Trade: $1.00$
  - Related Trade (from `trades.csv` `related_trades`): $0.50$
  - Unrelated Trade: $0.00$ (filtered out from recommendations).
- **TF-IDF Textual Similarity**:
  - A corpus is constructed from all 1,000 job descriptions, titles, qualifications, and required skills.
  - Candidate profile representation is vectorized using `TfidfVectorizer(stop_words='english')`.
  - Cosine similarity produces an objective textual relevance score.

### 5. Multi-Factor Scoring Formula
The final match score between a candidate and an ITI job vacancy is computed as:

$$\text{final\_score} = 0.50 \times S + 0.25 \times T + 0.15 \times E + 0.10 \times C$$

Where:
- **$S$ (Skill Match Score)**:
  $$S = 0.70 \times \left(\frac{\sum_{s \in S_{\text{matched}}} w_s}{\sum_{s \in S_{\text{required}}} w_s}\right) + 0.30 \times \text{TF-IDF Similarity}$$
- **$T$ (Trade Match Score)**: $1.00$ (exact) or $0.50$ (related trade).
- **$E$ (Experience Match Score)**:
  - $1.00$ if candidate experience $\ge$ minimum required experience.
  - $\frac{\text{candidate\_exp}}{\text{min\_required}}$ if candidate experience $<$ minimum required.
- **$C$ (Certification Match Score)**:
  - $1.00$ if job requires no certification or candidate holds the specified certification.
  - $0.85$ if candidate holds recognized ITI certification (`NCVT`/`SCVT`/`Trade Certificate`).
  - $0.00$ if candidate has no certifications for a certified role.

### 6. Skill Gap Analysis & Learning Recommendations
For each recommended job:
- **Matched Skills**: $S_{\text{candidate}} \cap S_{\text{required}}$
- **Missing Skills (Skill Gap)**: $S_{\text{required}} - S_{\text{candidate}}$
- Missing skills are cross-referenced with `courses.csv`:
  - If a course exists: displays course title, provider, duration, level, and URL (or `"Not provided in dataset"` if null).
  - If no course exists in the dataset: displays `"No learning resource found in the current dataset."` (no hallucination).

---

## Installation & Setup

### Prerequisites
- Windows, Linux, or macOS
- Python 3.10, 3.11, or 3.12

### Step 1: Clone or Navigate to Project
```powershell
cd D:\git\AI-SkillGap-System\
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

Core dependencies verified:
- `pandas`
- `numpy`
- `scikit-learn`
- `spacy`
- `rapidfuzz`
- `PyMuPDF`
- `python-docx`
- `fastapi`
- `uvicorn`
- `python-multipart`

---

## Running Instructions

### Single-Command Unified Launch (Recommended)
You can run the entire system (FastAPI backend + built React frontend) with a single command from the project root:

```powershell
python run.py
```

 **Web Application**: Open the URL provided by your hosting service.
 **Interactive Swagger API Docs**: Add `/docs` to your deployed application URL.

---

---


### Regenerate Trade-Skill Weights (Optional)
```powershell
python src/generate_skill_weights.py
```

### Run the Automated Test Suite
```powershell
python -m unittest tests/test_system.py -v
```


---

## Example Workflows

### Scenario A: Explicit Electrician Resume
1. User uploads a PDF/DOCX resume containing `"ITI Electrician"`, skills (`Wiring`, `PLC`), and `NCVT` certificate.
2. **Trade Validation**: Displays `✅ VALID ITI PROFILE — Detected Trade: Electrician`.
3. **Profile Review**: Candidate confirms or edits extracted skills.
4. **Matching**: System retrieves Electrician and Electronics Mechanic jobs.
5. **Output**: Top 3 Electrician jobs displayed with match scores $\ge 60\%$, missing skills identified, and courses recommended.

### Scenario B: Computer Science (Non-ITI) Resume
1. User uploads sample CSE resume (`test_resume.pdf/RESUME.pdf`).
2. **Extraction**: Detects `Python`, `B.E`, `B.Tech`, no ITI trade.
3. **Trade Validation**: Displays `ℹ️ No specific ITI trade or sufficient ITI-related information was detected.`
4. **Safeguard**: System blocks false COPA recommendations unless the user manually identifies as an ITI candidate.

### Scenario C: ITI Resume with Unclear Trade
1. User uploads resume mentioning `"Industrial Training Institute (ITI)"` and `"NCVT Certificate"`, but omitting trade name.
2. **Trade Validation**: Displays `⚠️ TRADE UNCLEAR — ITI / vocational background indicators were detected, but a specific trade was not identified.`
3. **User Action**: Dropdown enables user to pick their trade (e.g., *Fitter*) and immediately proceed to matching.

---

## Evaluation Plan & Automated Tests

The test suite in [`tests/test_system.py`](file:///D:/git/AI-SkillGap-System/tests/test_system.py) validates 13 critical technical requirements:

| Test ID | Test Name | Purpose | Result |
|---|---|---|---|
| 01 | `test_01_pdf_extraction` | Validates PyMuPDF extraction on actual PDF | ✅ PASSED |
| 02 | `test_02_docx_extraction` | Validates python-docx extraction on DOCX | ✅ PASSED |
| 03 | `test_03_explicit_electrician_detection` | Verifies explicit Electrician trade capture | ✅ PASSED |
| 04 | `test_04_explicit_fitter_detection` | Verifies explicit Fitter trade capture | ✅ PASSED |
| 05 | `test_05_cse_resume_no_iti_evidence` | Ensures CSE resume produces `NOT_ITI` | ✅ PASSED |
| 06 | `test_06_false_copa_prevention` | Prevents generic software terms from inferring COPA | ✅ PASSED |
| 07 | `test_07_skill_normalization` | Verifies canonical aliases mapping | ✅ PASSED |
| 08 | `test_08_trade_compatibility` | Tests exact (1.0), related (0.5), unrelated (0.0) | ✅ PASSED |
| 09 | `test_09_skill_matching` | Tests weighted skill and TF-IDF similarity | ✅ PASSED |
| 10 | `test_10_final_score_calculation` | Validates 50/25/15/10 scoring formula | ✅ PASSED |
| 11 | `test_11_skill_gap_calculation` | Tests set difference for missing skills & courses | ✅ PASSED |
| 12 | `test_12_top_3_ranking` | Confirms descending ranking & threshold check | ✅ PASSED |
| 13 | `test_13_trade_unclear_handling` | Tests `TRADE_UNCLEAR` state on ITI evidence | ✅ PASSED |

---

## Limitations

1. **Dataset Scope**: Currently uses curated local CSV datasets containing 7 ITI trades, 210 skills, and 1,000 job vacancies.
2. **Static Weights**: Trade skill weights are derived from dataset frequencies rather than dynamic industry job feeds.
3. **Course URLs**: The existing `courses.csv` dataset contains null URL values; real clickable links require updated external datasets.
4. **Single-Language Support**: Resume parsing is optimized for English-language resumes.

---

## Future Scope

1. **Database Integration**: Migrate CSV datasets to PostgreSQL / SQLite with indexed full-text search.
2. **Transformer & Contextual Embeddings**: Introduce compact multilingual sentence embeddings (e.g., Sentence-BERT / IndicBERT) for semantic skill matching.
3. **Learned Weighting**: Apply regression or learning-to-rank algorithms trained on employer hiring feedback.
4. **Live Job Aggregators**: Connect with authorized employment portals (e.g., National Career Service, Skill India Portal).
5. **Multilingual Resume Support**: Parse and analyze resumes written in major Indian regional languages (Tamil, Hindi, Telugu, Marathi, Bengali).
6. **Personalized Learning Paths**: Generate progressive week-by-week learning schedules for ITI apprentices.
7. **Employer-Side Portal**: Allow manufacturing employers to post vacancies and automatically score candidate batches.
